#!/usr/bin/env python3
"""
M14: 全场景Provenance Drift普查
================================
把drift检测从sc2(89对)扩展到全部场景(325对锚点):

  Phase 1  VLM结构化提取(非sc2的244对, kimi) — 断点续跑
  Phase 2  OCR提取(RapidOCR)
  Phase 3  VLM桥重对齐(修复低可信关键词映射, 同sc2方法)
  Phase 4  Drift检测(锚点XML文本 vs VLM渲染图文本, 含英文token的matcher)
  Phase 5  OCR仲裁(drift候选→ 真drift / VLM误读 / 存疑)

输出: data/gjb_438c/anchor_v2/scene_drift_census.json
用法: python3 tools/m14_scene_drift_census.py [--phase all|vlm|analyze] [--workers 6]
"""
import argparse
import base64
import json
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import text_match_score, MATCH_TH

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
VLM_OUT = BASE / "data/gjb_438c/anchor_v2/scene_vlm_extractions.json"
OCR_OUT = BASE / "data/gjb_438c/anchor_v2/scene_ocr_extractions.json"
CENSUS_OUT = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
KIMI_MODEL = "kimi-k2.6"

EXTRACT_PROMPT = """你是软件需求文档图表解析专家。请精确提取这张SRS文档中的图表结构。

要求:
1. 提取所有带文字的节点, 文字必须与图中完全一致(逐字, 不要改写)
2. 判断图的类型: flowchart(流程图/状态图) 或 usecase(用例图) 或 architecture(组件/架构图)
3. 提取所有箭头连接: src是箭头尾部节点id, dst是箭头头部指向的节点id
4. 边上有文字标签时填入label
5. 节点类型: process/decision/start/end/actor/usecase/component
6. pos为节点纵向位置: top/middle/bottom

严格输出JSON:
{
  "diagram_type": "flowchart 或 usecase 或 architecture",
  "nodes": [{"id": "n1", "text": "节点文字", "type": "process", "pos": "top"}],
  "edges": [{"src": "n1", "dst": "n2", "label": ""}]
}"""


# ═══════════════════════════════════════════════════════════════
# Phase 1: VLM提取
# ═══════════════════════════════════════════════════════════════

def kimi_extract(image_path: Path, pair_key: str) -> dict:
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    for _ in range(3):
        try:
            r = httpx.post(KIMI_URL, headers={
                'Authorization': f'Bearer {KIMI_KEY}', 'Content-Type': 'application/json'
            }, json={'model': KIMI_MODEL, 'thinking': {'type': 'disabled'},
                     'messages': [{'role': 'user', 'content': [
                         {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}'}},
                         {'type': 'text', 'text': EXTRACT_PROMPT}]}],
                     'max_tokens': 3000, 'temperature': 0.6,
                     'response_format': {'type': 'json_object'}}, timeout=180)
            if r.status_code == 200:
                data = json.loads(r.json()['choices'][0]['message'].get('content', ''))
                ids = {n.get('id') for n in data.get('nodes', [])}
                edges = [e for e in data.get('edges', [])
                         if e.get('src') in ids and e.get('dst') in ids and e.get('src') != e.get('dst')]
                return {
                    'pair_key': pair_key,
                    'diagram_type': data.get('diagram_type', 'unknown'),
                    'nodes': [{'id': n.get('id', ''), 'text': (n.get('text') or '').strip(),
                               'type': n.get('type', 'other'), 'pos': n.get('pos', '')}
                              for n in data.get('nodes', []) if (n.get('text') or '').strip()],
                    'edges': [{'src': e.get('src'), 'dst': e.get('dst'),
                               'label': (e.get('label') or '').strip()} for e in edges],
                }
        except Exception:
            time.sleep(5)
    return {'pair_key': pair_key, 'error': 'failed', 'nodes': [], 'edges': []}


def phase_vlm(pairs, workers):
    results = json.loads(VLM_OUT.read_text()) if VLM_OUT.exists() else {}
    todo = [(pk, img) for pk, img in pairs if pk not in results]
    print(f"Phase 1 VLM提取: 待跑{len(todo)}/{len(pairs)}")
    t0 = time.time()

    def run(item):
        pk, img = item
        return pk, kimi_extract(img, pk)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run, t): t for t in todo}
        done = 0
        for fut in as_completed(futs):
            pk, r = fut.result()
            results[pk] = r
            done += 1
            if done % 20 == 0:
                VLM_OUT.write_text(json.dumps(results, ensure_ascii=False))
                print(f"  [{done}/{len(todo)}] {time.time()-t0:.0f}s")
    VLM_OUT.write_text(json.dumps(results, ensure_ascii=False))
    ok = sum(1 for r in results.values() if 'error' not in r)
    print(f"  完成: {ok}/{len(results)}")
    return results


# ═══════════════════════════════════════════════════════════════
# Phase 2: OCR提取
# ═══════════════════════════════════════════════════════════════

def phase_ocr(pairs):
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    results = json.loads(OCR_OUT.read_text()) if OCR_OUT.exists() else {}
    t0 = time.time()
    for i, (pk, img) in enumerate(pairs):
        if pk in results:
            continue
        try:
            ocr_result, _ = ocr(str(img))
            blocks = []
            if ocr_result:
                for box, text, score in ocr_result:
                    if text and float(score) > 0.4:
                        blocks.append({'text': text.strip(), 'score': round(float(score), 3)})
            results[pk] = {'blocks': blocks,
                           'full_text': ' '.join(b['text'] for b in blocks)}
        except Exception as e:
            results[pk] = {'error': str(e)[:80]}
        if (i + 1) % 50 == 0:
            OCR_OUT.write_text(json.dumps(results, ensure_ascii=False))
            print(f"  OCR [{i+1}/{len(pairs)}] {time.time()-t0:.0f}s")
    OCR_OUT.write_text(json.dumps(results, ensure_ascii=False))
    ok = sum(1 for r in results.values() if 'error' not in r)
    print(f"Phase 2 OCR: {ok}/{len(results)}")
    return results


# ═══════════════════════════════════════════════════════════════
# Phase 3-5: 重对齐 + drift检测 + 仲裁
# ═══════════════════════════════════════════════════════════════

def build_anchor_index():
    anchors = json.loads(ANCHOR_V2.read_text())
    doc_anchors = defaultdict(list)
    for doc, d in anchors.items():
        for s in d['structures']:
            text_nodes = [n for n in s['nodes'] if n['text']]
            if len(text_nodes) >= 2:
                doc_anchors[doc].append((s, text_nodes))
    return doc_anchors


def realign(pair_key, doc, vlm_nodes, doc_anchors):
    """VLM桥重对齐: 与文档全部锚点匹配, 返回(最佳锚点, 分数)"""
    best = None
    for s, text_nodes in doc_anchors.get(doc, []):
        pairs_list = []
        for vn in vlm_nodes:
            for an in text_nodes:
                sc = text_match_score(vn['text'], an['text'])
                if sc >= 0.5:
                    pairs_list.append((sc, vn['id'], an['id']))
        pairs_list.sort(key=lambda x: -x[0])
        used_v, used_a = set(), set()
        for sc, vid, aid in pairs_list:
            if vid not in used_v and aid not in used_a:
                used_v.add(vid)
                used_a.add(aid)
        score = len(used_a) / max(len(vlm_nodes), len(text_nodes))
        if best is None or score > best['score']:
            best = {'score': round(score, 3), 'structure': s,
                    'n_match': len(used_a), 'n_vlm': len(vlm_nodes),
                    'n_anchor': len(text_nodes)}
    return best


def detect_drift(anchor, vlm_nodes):
    """锚点XML文本 vs VLM渲染图文本 → 差异列表"""
    a_texts = [n['text'].replace('\n', '') for n in anchor['nodes'] if n['text']]
    v_texts = [n['text'].replace('\n', '') for n in vlm_nodes if n.get('text')]
    if not a_texts or not v_texts:
        return []
    diffs = []
    for at in a_texts:
        best, best_sc = None, 0
        for vt in v_texts:
            sc = text_match_score(at, vt)
            if sc > best_sc:
                best_sc, best = sc, vt
        if best is None or best_sc < MATCH_TH:
            diffs.append({'kind': 'missing_in_image', 'xml': at[:36], 'img': '', 'score': best_sc})
        elif best_sc < 0.99 and at.replace(' ', '') != best.replace(' ', ''):
            diffs.append({'kind': 'text_drift', 'xml': at[:36], 'img': best[:36], 'score': best_sc})
    for vt in v_texts:
        best_sc = max((text_match_score(vt, at) for at in a_texts), default=0)
        if best_sc < MATCH_TH:
            diffs.append({'kind': 'extra_in_image', 'xml': '', 'img': vt[:36], 'score': best_sc})
    return diffs


def arbitrate(diff, ocr_full_text):
    """OCR仲裁: 关键词在OCR(渲染图)全文中的存在性"""
    xml_kw = re.findall(r'[A-Za-z0-9]{2,}', diff['xml'])
    img_kw = re.findall(r'[A-Za-z0-9]{2,}', diff['img'])
    if not xml_kw and not img_kw:
        return 'inconclusive'  # 纯中文差异, OCR存在性难判
    ocr_up = (ocr_full_text or '').upper().replace(' ', '')
    xml_in = any(k.upper() in ocr_up for k in xml_kw) if xml_kw else None
    img_in = any(k.upper() in ocr_up for k in img_kw) if img_kw else None
    if xml_in and not img_in:
        return 'vlm_misread'      # OCR支持XML版 → VLM看错
    if img_in and not xml_in:
        return 'real_drift'       # OCR支持图版 → 真漂移
    if xml_in and img_in:
        return 'ambiguous_both'
    return 'inconclusive'


def phase_analyze(pairs_by_scene, vlm, ocr):
    doc_anchors = build_anchor_index()
    census = {}
    stats = Counter()

    for scene, pairs in pairs_by_scene.items():
        for pk, img in pairs:
            v = vlm.get(pk)
            o = ocr.get(pk)
            if not v or 'error' in v or not v.get('nodes'):
                continue
            # 旧锚点(pair文件夹里的visio_anchor.json)
            va_path = PAIR_ROOT / scene / pk / 'visio_anchor.json'
            if not va_path.exists():
                continue
            va = json.loads(va_path.read_text())
            doc = va['doc']

            # Phase 3: 重对齐
            best = realign(pk, doc, v['nodes'], doc_anchors)
            if best is None or best['score'] < 0.4:
                census[pk] = {'scene': scene, 'status': 'unanchored',
                              'align_score': best['score'] if best else 0}
                stats['unanchored'] += 1
                continue

            realigned = best['score'] >= 0.75
            anchor = best['structure']
            old_embed = va.get('embed_index', '')
            new_embed = anchor['embed_index']
            remapped = old_embed != new_embed

            # Phase 4: drift检测
            diffs = detect_drift(anchor, v['nodes'])

            # Phase 5: 仲裁
            ocr_text = o.get('full_text', '') if o and 'error' not in o else ''
            for d in diffs:
                if d['kind'] == 'text_drift':
                    d['verdict'] = arbitrate(d, ocr_text)

            census[pk] = {
                'scene': scene, 'doc': doc,
                'status': 'anchored',
                'align_score': best['score'],
                'realigned': realigned, 'remapped': remapped,
                'old_embed': old_embed, 'new_embed': new_embed,
                'n_drift': len(diffs), 'diffs': diffs,
            }
            stats['anchored'] += 1
            if remapped:
                stats['remapped'] += 1
            if diffs:
                stats['pairs_with_diff'] += 1
            for d in diffs:
                stats[d['kind']] += 1
                if d.get('verdict'):
                    stats[d['verdict']] += 1

    CENSUS_OUT.write_text(json.dumps(census, ensure_ascii=False, indent=1))
    return census, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', default='all', choices=['all', 'vlm', 'analyze'])
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()

    # 收集全部有锚点的对
    pairs_by_scene = {}
    all_pairs = []
    for scene in sorted(PAIR_ROOT.iterdir()):
        if not scene.is_dir() or scene.name == 'sc2_flowchart_usecase':
            continue  # sc2已有全套
        pairs = []
        for d in sorted(scene.iterdir()):
            if (d / 'meta.json').exists() and (d / 'image.png').exists() \
                    and (d / 'visio_anchor.json').exists():
                pairs.append((d.name, d / 'image.png'))
        if pairs:
            pairs_by_scene[scene.name] = pairs
            all_pairs.extend(pairs)

    print(f"{'='*64}")
    print(f"M14: 全场景Drift普查 (非sc2的{len(all_pairs)}对)")
    print(f"{'='*64}")
    for scene, pairs in pairs_by_scene.items():
        print(f"  {scene:28s}: {len(pairs)}对")

    if args.phase in ('all', 'vlm'):
        vlm = phase_vlm(all_pairs, args.workers)
        ocr = phase_ocr(all_pairs)
    else:
        vlm = json.loads(VLM_OUT.read_text()) if VLM_OUT.exists() else {}
        ocr = json.loads(OCR_OUT.read_text()) if OCR_OUT.exists() else {}

    if args.phase in ('all', 'analyze'):
        census, stats = phase_analyze(pairs_by_scene, vlm, ocr)
        print(f"\n{'='*64}")
        print(f"Drift普查结果")
        print(f"{'='*64}")
        print(f"  锚定: {stats['anchored']}对 (重对齐修复映射: {stats['remapped']}, "
              f"无锚: {stats['unanchored']})")
        print(f"  存在差异的对: {stats['pairs_with_diff']}")
        print(f"  差异类型: 文字漂移{stats['text_drift']} 图缺失{stats['missing_in_image']} "
              f"图多出{stats['extra_in_image']}")
        print(f"  仲裁verdict: 真drift={stats['real_drift']} VLM误读={stats['vlm_misread']} "
              f"两者都有={stats['ambiguous_both']} 存疑={stats['inconclusive']}")

        # 真drift明细
        print(f"\n  ★ 确认的真drift(text_drift且OCR支持图版):")
        for pk, c in sorted(census.items()):
            for d in c.get('diffs', []):
                if d.get('verdict') == 'real_drift':
                    print(f"    [{pk}]({c['scene'][:10]}) XML「{d['xml'][:24]}」 vs 图「{d['img'][:24]}」")

        # 按场景汇总
        scene_stats = defaultdict(Counter)
        for pk, c in census.items():
            scene_stats[c['scene']]['n'] += 1
            if c.get('n_drift'):
                scene_stats[c['scene']]['drift'] += 1
        print(f"\n  按场景: " + " ".join(
            f"{s[:8]}:{v['drift']}/{v['n']}" for s, v in scene_stats.items()))
        print(f"\n  输出: {CENSUS_OUT}")


if __name__ == '__main__':
    main()
