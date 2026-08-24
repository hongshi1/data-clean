#!/usr/bin/env python3
"""
M17: 多场景双LLM裁决
======================
裁决sc1/sc3/sc4/sc5的高置信Tier1缺失候选(对齐分≥0.5的层):
  kimi(看图) + GLM(看锚点结构) 独立分类:
    real_bug         — 文档缺陷(该表格项应在图中有表示)
    benign_variation — 合理差异(图只画部分/registry超集/粒度不同)
    compiler_bug     — 匹配引擎误报(图里实际有,没匹配上)

输出: data/gjb_438c/anchor_v2/scene_adjudication.json
用法: python3 tools/m17_scene_adjudication.py [--workers 6]
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

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
TIER1 = BASE / "data/gjb_438c/anchor_v2/scene_tier1.json"
CENSUS = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
OUT = BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
KIMI_MODEL = "kimi-k2.6"
GLM_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
GLM_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
GLM_MODEL = "ep-glsztk-1778496696841467392"

SCENE_DESC = {
    'sc1_usecase_capability': ('能力需求表', '用例图',
        '表格列出全部能力需求(Use case), 图是用例图(用例椭圆+参与者)'),
    'sc3_interface_interface': ('接口需求表', '接口设计图',
        '表格是接口需求registry(全部接口+收发方), 图是接口设计图(组件框+接口连线)'),
    'sc4_flowchart_capability': ('能力需求表', '流程图',
        '表格列出全部能力需求, 图是某一能力的实现流程图'),
    'sc5_function_capability': ('子功能表', '功能结构图',
        '表格列出子功能, 图是功能结构/分解图'),
}

PROMPT = """你是军事软件需求文档(GJB 438C)质量审查专家。判断以下"表格项在图中无对应"的分歧类别。

## 文档背景
- 表格类型: {table_kind}
- 图类型: {diagram_kind}
- 说明: {scene_note}

## 表格侧内容(被审查项所在表的相关行)
{table_context}

## 图侧内容(节点与连线)
{diagram_content}
{image_note}

## 被审查的分歧
{evidence}

## 判断标准(三选一)
- real_bug: 真实文档缺陷 — 按文档惯例该表格项【应该】在图中有表示却没有(如图声称覆盖全部能力但漏画了某能力)
- benign_variation: 合理差异 — 图本来就不需要表示该项(如图只画核心流程、表格是完整registry、粒度/视角不同是GJB文档惯例)
- compiler_bug: 比对引擎误报 — 图中实际有对应元素, 只是文字表述差异大导致自动匹配没认出来

严格输出JSON:
{{"label": "real_bug|benign_variation|compiler_bug",
  "reason": "一句话理由",
  "confidence": "high|low"}}"""


def parse_label(text: str) -> dict:
    try:
        m = re.search(r'\{[^{}]*\}', text.replace('\n', ' '), re.DOTALL)
        if m:
            d = json.loads(m.group(0))
            label = d.get('label', '')
            if label in ('real_bug', 'benign_variation', 'compiler_bug'):
                return {'label': label, 'reason': str(d.get('reason', ''))[:100],
                        'confidence': d.get('confidence', 'low')}
        for lb in ('real_bug', 'benign_variation', 'compiler_bug'):
            if lb in text:
                return {'label': lb, 'reason': text[:80], 'confidence': 'low'}
    except Exception:
        pass
    return {'label': 'parse_error', 'reason': text[:80], 'confidence': 'low'}


def call_kimi(prompt: str, img_path: Path | None) -> dict:
    content = [{"type": "text", "text": prompt}]
    if img_path and img_path.exists():
        b64 = base64.b64encode(img_path.read_bytes()).decode()
        content.insert(0, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    for _ in range(2):
        try:
            r = httpx.post(KIMI_URL, headers={
                'Authorization': f'Bearer {KIMI_KEY}', 'Content-Type': 'application/json'
            }, json={'model': KIMI_MODEL, 'thinking': {'type': 'disabled'},
                     'messages': [{'role': 'user', 'content': content}],
                     'max_tokens': 400, 'temperature': 0.6,
                     'response_format': {'type': 'json_object'}}, timeout=120)
            if r.status_code == 200:
                return parse_label(r.json()['choices'][0]['message'].get('content', ''))
        except Exception:
            time.sleep(3)
    return {'label': 'error', 'reason': 'call_failed', 'confidence': 'low'}


def call_glm(prompt: str) -> dict:
    for _ in range(2):
        try:
            r = httpx.post(GLM_URL, headers={
                'Authorization': f'Bearer {GLM_KEY}', 'Content-Type': 'application/json'
            }, json={'model': GLM_MODEL,
                     'messages': [{'role': 'user',
                                   'content': prompt + "\n\n注意: 你看不到图片, 凭上述图的结构化描述(来自Visio源,可信)判断。请快速判断(思考限3步), 直接输出JSON。"}],
                     'max_tokens': 6000, 'temperature': 0.6}, timeout=240)
            if r.status_code == 200:
                return parse_label(r.json()['choices'][0]['message'].get('content', ''))
        except Exception:
            time.sleep(3)
    return {'label': 'error', 'reason': 'call_failed', 'confidence': 'low'}


def build_tasks():
    """构建裁决任务(高置信层的缺失候选)"""
    tier1 = json.loads(TIER1.read_text())
    census = json.loads(CENSUS.read_text())
    anchors = json.loads(ANCHOR_V2.read_text())
    v2_idx = {}
    for doc, d in anchors.items():
        for s in d['structures']:
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s['nodes'] if n['text'])
            if key not in v2_idx or tn > v2_idx[key][0]:
                v2_idx[key] = (tn, s)

    tasks = []
    for pk, v in tier1.items():
        scene = v.get('scene', '')
        if scene not in SCENE_DESC:
            continue
        c = census.get(pk, {})
        if c.get('align_score', 0) < 0.5:
            continue  # 低置信层的缺失是锚点覆盖问题, 不裁决
        # 图内容
        anchor = None
        if c.get('new_embed'):
            entry = v2_idx.get((c.get('doc', ''), c['new_embed'].split(':')[0]))
            anchor = entry[1] if isinstance(entry, tuple) else entry
        if anchor is None:
            va = PAIR_ROOT / scene / pk / 'visio_anchor.json'
            if va.exists():
                anchor = json.loads(va.read_text())
        if not anchor:
            continue
        node_strs = [f"  [{n['type']}] {n['text'][:40]}" for n in anchor['nodes'] if n['text']]
        diagram_content = "节点:\n" + "\n".join(node_strs[:25])
        # 表格上下文
        table_path = PAIR_ROOT / scene / pk / 'table.csv'
        table_text = table_path.read_text(encoding='utf-8')[:600] if table_path.exists() else ''
        img_path = PAIR_ROOT / scene / pk / 'image.png'
        table_kind, diagram_kind, scene_note = SCENE_DESC[scene]

        for di, d in enumerate(v.get('discrepancies', [])):
            if d['dtype'] not in ('TABLE_ITEM_MISSING', 'COMPONENT_MISSING'):
                continue
            tasks.append({
                'task_id': f"{pk}_{di:02d}", 'pair': pk, 'scene': scene,
                'dtype': d['dtype'], 'evidence': d['evidence'],
                'table_kind': table_kind, 'diagram_kind': diagram_kind,
                'scene_note': scene_note,
                'table_context': table_text, 'diagram_content': diagram_content,
                'img_path': str(img_path) if img_path.exists() else '',
            })
    return tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    tasks = build_tasks()
    if args.limit:
        tasks = tasks[:args.limit]
    print(f"{'='*64}")
    print(f"M17: 多场景双LLM裁决 ({len(tasks)}条候选)")
    print(f"{'='*64}")
    by_scene = Counter(t['scene'] for t in tasks)
    for s, n in by_scene.items():
        print(f"  {s:28s}: {n}")

    results = json.loads(OUT.read_text()) if OUT.exists() else {}

    def run_one(t):
        prompt = PROMPT.format(
            table_kind=t['table_kind'], diagram_kind=t['diagram_kind'],
            scene_note=t['scene_note'], table_context=t['table_context'][:500],
            diagram_content=t['diagram_content'][:900],
            image_note="\n(图片见上)" if t['img_path'] else "",
            evidence=t['evidence'])
        kimi_r = call_kimi(prompt, Path(t['img_path']) if t['img_path'] else None)
        glm_r = call_glm(prompt)
        return t['task_id'], {
            'pair': t['pair'], 'scene': t['scene'], 'dtype': t['dtype'],
            'evidence': t['evidence'],
            'kimi': kimi_r, 'glm': glm_r,
            'final': kimi_r['label'] if kimi_r['label'] == glm_r['label'] else 'uncertain',
        }

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(run_one, t) for t in tasks if t['task_id'] not in results]
        done = 0
        for fut in as_completed(futs):
            tid, res = fut.result()
            results[tid] = res
            done += 1
            if done % 20 == 0:
                OUT.write_text(json.dumps(results, ensure_ascii=False))
                print(f"  [{done}/{len(tasks)}] {time.time()-t0:.0f}s")
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))

    # ── 汇总 ──
    ok = [r for r in results.values() if r.get('final')]
    agree = sum(1 for r in ok if r['final'] != 'uncertain')
    print(f"\n{'='*64}")
    print(f"裁决结果 ({len(results)}条, 双模型一致率{agree/max(1,len(ok)):.0%})")
    print(f"{'='*64}")
    final = Counter(r['final'] for r in ok)
    print(f"  总标签: {dict(final)}")

    # 分场景×标签 + π
    print(f"\n  分场景(π=real_bug率):")
    scene_pi = {}
    cross = defaultdict(Counter)
    for r in ok:
        cross[r['scene']][r['final']] += 1
    for scene, c in sorted(cross.items()):
        n = sum(c.values())
        pi = c['real_bug'] / max(1, n)
        scene_pi[scene] = {'n': n, 'real_bug': c['real_bug'], 'benign': c['benign_variation'],
                           'compiler_bug': c['compiler_bug'], 'uncertain': c['uncertain'],
                           'pi': round(pi, 3)}
        print(f"    {scene:28s}: n={n:3d} real={c['real_bug']:3d} benign={c['benign_variation']:3d} "
              f"compiler={c['compiler_bug']:2d} uncertain={c['uncertain']:3d} → π={pi:.2f}")

    # real_bug样例
    print(f"\n  real_bug样例(前6):")
    n = 0
    for tid, r in results.items():
        if r.get('final') == 'real_bug' and n < 6:
            print(f"    [{tid}] ({r['scene'][:6]}) {r['evidence'][:44]}")
            print(f"       kimi: {r['kimi']['reason'][:40]} | glm: {r['glm']['reason'][:40]}")
            n += 1
    print(f"\n  输出: {OUT}")


if __name__ == '__main__':
    main()
