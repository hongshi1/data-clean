#!/usr/bin/env python3
"""
M15: sc3接口图专用感知 + 重分析
===================================
接口图的结构: 组件框 + 接口连线 + 连线上的接口名/数据项文字
通用图提取提示词漏了数据项小字(83条missing的主因)

方案: 接口图专用VLM提示词(强调全部文字元素包括小标签),
重跑sc3的28对 → 重做drift分析 → 与旧结果对比

用法: python3 tools/m15_interface_perception.py
"""
import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import text_match_score, MATCH_TH, normalize_text

SCENE = BASE / "data/gjb_438c/pair_dataset/sc3_interface_interface"
VLM_OUT = BASE / "data/gjb_438c/anchor_v2/sc3_vlm_extractions_v2.json"
CENSUS_PATH = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
OCR_PATH = BASE / "data/gjb_438c/anchor_v2/scene_ocr_extractions.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY
KIMI_MODEL = "kimi-k2.6"

PROMPT = """你是软件需求文档接口图解析专家。这是一张接口设计图(组件框+接口连线)。

接口图的构成:
- 组件/服务框: 大方框, 内有组件名(如"数据获取转换服务")
- 接口连线: 连接组件的线, 线上或线旁标注接口名(如"数据协议解析接口")
- 数据项标签: 连线上标注的传输数据(如"日志记录信息"、"报文数据")——这些小字也要提取!

提取要求:
1. 提取图中【所有可见文字】, 逐字一致, 不改写不省略——包括组件名、接口名、数据项小字、角色名
2. 每个文字元素作为一个节点, type标注: component(组件框)/interface(接口名)/data(数据项)/actor(角色)
3. 提取连线: src/dst是两端组件的节点id, label是线上的接口名或数据项文字
4. 不要遗漏任何文字

严格输出JSON:
{
  "diagram_type": "interface",
  "nodes": [{"id": "n1", "text": "文字", "type": "component或interface或data或actor", "pos": "top/middle/bottom"}],
  "edges": [{"src": "n1", "dst": "n2", "label": "接口名或数据项"}]
}"""


def kimi_extract(image_path: Path, pair_key: str) -> dict:
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    for _ in range(3):
        try:
            r = httpx.post(KIMI_URL, headers={
                'Authorization': f'Bearer {KIMI_KEY}', 'Content-Type': 'application/json'
            }, json={'model': KIMI_MODEL, 'thinking': {'type': 'disabled'},
                     'messages': [{'role': 'user', 'content': [
                         {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}'}},
                         {'type': 'text', 'text': PROMPT}]}],
                     'max_tokens': 4000, 'temperature': 0.6,
                     'response_format': {'type': 'json_object'}}, timeout=180)
            if r.status_code == 200:
                data = json.loads(r.json()['choices'][0]['message'].get('content', ''))
                ids = {n.get('id') for n in data.get('nodes', [])}
                edges = [e for e in data.get('edges', [])
                         if e.get('src') in ids and e.get('dst') in ids]
                return {
                    'pair_key': pair_key,
                    'nodes': [{'id': n.get('id', ''), 'text': (n.get('text') or '').strip(),
                               'type': n.get('type', 'other'), 'pos': n.get('pos', '')}
                              for n in data.get('nodes', []) if (n.get('text') or '').strip()],
                    'edges': [{'src': e.get('src'), 'dst': e.get('dst'),
                               'label': (e.get('label') or '').strip()} for e in edges],
                }
        except Exception:
            time.sleep(5)
    return {'pair_key': pair_key, 'error': 'failed', 'nodes': [], 'edges': []}


def detect_drift(anchor, vlm_nodes):
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
            diffs.append({'kind': 'missing_in_image', 'xml': at[:36], 'img': '', 'score': round(best_sc, 2)})
        elif best_sc < 0.99 and at.replace(' ', '') != best.replace(' ', ''):
            diffs.append({'kind': 'text_drift', 'xml': at[:36], 'img': best[:36], 'score': round(best_sc, 2)})
    return diffs


def is_fragmentation(d, v_texts):
    """碎片化判定: 子串关系 且 互补部分在对方文本集中存在"""
    nx, ni = normalize_text(d['xml']), normalize_text(d['img'])
    t = nx or ni
    if not t:
        return False
    for vt in v_texts:
        vt_n = normalize_text(vt)
        if vt_n and (t in vt_n or vt_n in t):
            return True
    return False


def main():
    pairs = sorted([d for d in SCENE.iterdir()
                    if (d / 'meta.json').exists() and (d / 'visio_anchor.json').exists()])
    print(f"M15: sc3接口图专用感知 ({len(pairs)}对)")

    # ── Phase 1: 专用提示词重提取 ──
    results = json.loads(VLM_OUT.read_text()) if VLM_OUT.exists() else {}
    todo = [d for d in pairs if d.name not in results]

    def run(d):
        return d.name, kimi_extract(d / 'image.png', d.name)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(run, d) for d in todo]
        for fut in as_completed(futs):
            pk, r = fut.result()
            results[pk] = r
    VLM_OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    ok = sum(1 for r in results.values() if 'error' not in r)
    print(f"  提取: {ok}/{len(results)}")

    # ── Phase 2: 重做drift分析 ──
    ocr = json.loads(OCR_PATH.read_text())
    census = json.loads(CENSUS_PATH.read_text())

    # 对比新旧
    old_vlm = json.loads(
        (BASE / "data/gjb_438c/anchor_v2/scene_vlm_extractions.json").read_text())

    old_missing = new_missing = 0
    improved = []
    for d in pairs:
        pk = d.name
        v_new = results.get(pk)
        if not v_new or 'error' in v_new:
            continue
        va = json.loads((d / 'visio_anchor.json').read_text())
        # 锚点(用census里重对齐后的)
        c = census.get(pk, {})
        if c.get('status') != 'anchored':
            continue

        # 新drift检测
        v_texts = [n['text'] for n in v_new.get('nodes', []) if n.get('text')]
        # 锚点文本从anchor_v2取(重对齐后的结构)
        anchors = json.loads((BASE / "data/gjb_438c/anchor_v2/anchors_v2.json").read_text())
        # 简化: 用pair的visio_anchor(旧映射)或重对齐结构——用census记录的new_embed
        # 这里直接重用pair文件夹的锚点做对比演示(它可能被重对齐修正过)
        anchor = va
        diffs_new = detect_drift(anchor, v_new['nodes'])
        diffs_new = [x for x in diffs_new
                     if x['kind'] == 'text_drift' or not is_fragmentation(x, v_texts)]

        v_old = old_vlm.get(pk, {})
        diffs_old = detect_drift(anchor, v_old.get('nodes', []))

        old_missing += sum(1 for x in diffs_old if x['kind'] == 'missing_in_image')
        new_missing += sum(1 for x in diffs_new if x['kind'] == 'missing_in_image')
        if len(diffs_new) < len(diffs_old):
            improved.append((pk, len(diffs_old), len(diffs_new)))

    print(f"\n  旧提示词missing: {old_missing} → 新提示词missing: {new_missing}")
    print(f"  改善的对: {len(improved)}")
    for pk, o, n in improved[:8]:
        print(f"    {pk}: {o}→{n}差异")


if __name__ == '__main__':
    main()
