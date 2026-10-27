#!/usr/bin/env python3
"""
M13: 类型感知的Mermaid导出 + Kimi保真度验证
=============================================
回答两个问题:
  1. mermaid_export.json的373份Mermaid与原图一致吗? → kimi当裁判逐项核查
  2. 其他图类型(用例图/状态图/架构图)如何表示和感知? → 类型特定的导出

验证协议(清单式, 图类型无关):
  给kimi: 原图 + Mermaid代码 + 节点清单 + 边清单
  要求逐项判断: 节点可见性 / 边存在性与方向 / 遗漏元素
  输出: fidelity_score + 逐项verdict

图类型 → Mermaid方言:
  flowchart/hierarchy/mixed/architecture → flowchart TD
  state_diagram → stateDiagram-v2
  usecase_diagram → flowchart TD (actor用[/…/]形, usecase用体育场)

用法: python3 tools/m13_verify_mermaid.py [--limit N] [--types flowchart,state_diagram]
"""
import argparse
import base64
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT_PATH = BASE / "data/gjb_438c/anchor_v2/mermaid_fidelity.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY
KIMI_MODEL = "kimi-k2.6"

SHAPE = {
    'start': ('([', '])'), 'end': ('([', '])'),
    'process': ('[', ']'), 'decision': ('{', '}'),
    'state': ('[', ']'), 'usecase': ('([', '])'),
    'actor': ('[/', '/]'), 'gateway': ('{', '}'),
    'fork': ('{', '}'), 'boundary': ('[', ']'),
    'other': ('[', ']'), 'offpage': ('[[', ']]'),
    'note': ('[/', '/]'),
}


# ═══════════════════════════════════════════════════════════════
# 图类型判定 + 类型特定导出
# ═══════════════════════════════════════════════════════════════

def classify_diagram(s: dict) -> str:
    types = Counter(n['type'] for n in s['nodes'] if n['text'])
    n_text = sum(types.values())
    if n_text == 0:
        return 'empty'
    if types.get('usecase', 0) / n_text >= 0.4:
        return 'usecase_diagram'
    if types.get('state', 0) / n_text >= 0.4:
        return 'state_diagram'
    if types.get('process', 0) / n_text >= 0.5:
        return 'flowchart'
    if types.get('actor', 0) and not types.get('usecase', 0):
        return 'architecture'
    if len(s['edges']) < n_text * 0.3:
        return 'hierarchy_decomposition'
    return 'mixed'


def sanitize(text: str, maxlen: int = 200) -> str:
    """验证模式不截断(kimi需要看到完整文字)"""
    t = text.replace('\n', ' ').replace('"', "'")
    t = t.replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')')
    return t[:maxlen]


def to_mermaid_flowchart(s: dict) -> str:
    lines = ['flowchart TD']
    nodes = {n['id']: n for n in s['nodes']}
    emitted = set()

    # 无文本但有拓扑意义的类型
    TOPO_TYPES = {'start': '开始', 'end': '结束', 'fork': '分叉', 'gateway': '网关', 'decision': '判定'}

    def emit_node(n):
        if n['id'] in emitted:
            return
        # 有文本 或 是拓扑哨兵(fork/gateway等无文本但有结构意义)才导出
        if not n['text'] and n['type'] not in TOPO_TYPES:
            return
        label = sanitize(n['text']) or TOPO_TYPES[n['type']]
        l, r = SHAPE.get(n['type'], ('[', ']'))
        lines.append(f'    N{n["id"]}{l}"{label}"{r}')
        emitted.add(n['id'])

    for n in s['nodes']:
        emit_node(n)
    for e in s['edges']:
        sn, dn = nodes.get(e['src']), nodes.get(e['dst'])
        if not sn or not dn:
            continue
        # 两端都无文本且非拓扑哨兵 → 该边无可视对应物, 跳过
        if not (sn['text'] or sn['type'] in TOPO_TYPES):
            continue
        if not (dn['text'] or dn['type'] in TOPO_TYPES):
            continue
        emit_node(sn)
        emit_node(dn)
        if e.get('label'):
            lines.append(f'    N{e["src"]} -->|"{sanitize(e["label"], 20)}"| N{e["dst"]}')
        else:
            lines.append(f'    N{e["src"]} --> N{e["dst"]}')
    return '\n'.join(lines)


def to_mermaid_state(s: dict) -> str:
    """状态图 → stateDiagram-v2 (全部被引用节点都定义, 哨兵用[*])"""
    lines = ['stateDiagram-v2']
    nodes = {n['id']: n for n in s['nodes']}
    refs = set()
    for e in s['edges']:
        refs.add(e['src'])
        refs.add(e['dst'])
    emitted = set()
    # 1. 定义全部有文本节点 + 被引用节点(start/end哨兵特殊处理)
    for n in s['nodes']:
        if not n['text'] and n['id'] not in refs:
            continue
        if n['type'] == 'start':
            label = sanitize(n['text'], 40)
            if label:
                lines.append(f'    N{n["id"]} : {label}')
            lines.append(f'    [*] --> N{n["id"]}')
        elif n['type'] == 'end':
            label = sanitize(n['text'], 40)
            if label:
                lines.append(f'    N{n["id"]} : {label}')
            lines.append(f'    N{n["id"]} --> [*]')
        else:
            label = sanitize(n['text'], 60) or n['type']
            lines.append(f'    N{n["id"]} : {label}')
        emitted.add(n['id'])
    # 2. 边(只引用已定义节点, 避免undefined)
    for e in s['edges']:
        if e['src'] not in emitted or e['dst'] not in emitted:
            continue
        if e.get('label'):
            lines.append(f'    N{e["src"]} --> {sanitize(e["label"], 16)}: N{e["dst"]}')
        else:
            lines.append(f'    N{e["src"]} --> N{e["dst"]}')
    return '\n'.join(lines)


def to_mermaid(s: dict, dtype: str) -> str:
    if dtype == 'state_diagram':
        return to_mermaid_state(s)
    return to_mermaid_flowchart(s)


# ═══════════════════════════════════════════════════════════════
# Kimi保真度验证
# ═══════════════════════════════════════════════════════════════

JUDGE_PROMPT = """你是图表保真度审查员。给你一张图(来自软件需求文档)和一段据称忠实表示它的Mermaid代码。请以图片为准, 逐项验证。

## Mermaid代码
```mermaid
{mermaid}
```

## 逐项核查(三项都要做)

### 1. 节点存在性核查
下面每个节点文字(来自Mermaid), 图片中是否真实可见该文字?
{node_list}

### 2. 边存在性与方向核查
下面每条连接(来自Mermaid), 图片中是否真实存在"从A指向B"的箭头?
{edge_list}

### 3. 遗漏检查
图片中是否存在带文字的元素没有出现在上面的节点清单里? (连线标签不算)

严格输出JSON:
{{
  "node_checks": [{{"text": "节点文字前12字", "visible": true或false}}],
  "edge_checks": [{{"edge": "A文字前8字→B文字前8字", "exists": true或false, "direction_ok": true或false}}],
  "missed_elements": ["图片里有但清单没有的文字"],
  "fidelity_score": 0到100的整数,
  "notes": "一句话总评"
}}"""


def parse_json_loose(text: str):
    import re
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def kimi_verify(image_path: Path, mermaid: str, nodes: list, edges: list) -> dict:
    node_list = '\n'.join(f'  - 「{t[:16]}」' for t in nodes)
    edge_list = '\n'.join(f'  - 「{s[:10]}」→「{d[:10]}」' for s, d in edges)
    prompt = JUDGE_PROMPT.format(mermaid=mermaid, node_list=node_list, edge_list=edge_list)
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    for _ in range(2):
        try:
            r = httpx.post(KIMI_URL, headers={
                'Authorization': f'Bearer {KIMI_KEY}', 'Content-Type': 'application/json'
            }, json={'model': KIMI_MODEL, 'thinking': {'type': 'disabled'},
                     'messages': [{'role': 'user', 'content': [
                         {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}'}},
                         {'type': 'text', 'text': prompt}]}],
                     'max_tokens': 3000, 'temperature': 0.6,
                     'response_format': {'type': 'json_object'}}, timeout=180)
            if r.status_code == 200:
                d = parse_json_loose(r.json()['choices'][0]['message'].get('content', ''))
                if d:
                    return d
        except Exception:
            time.sleep(3)
    return {'error': 'verify_failed'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()

    anchors = json.loads(ANCHOR_V2.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())
    realigned = json.loads(REALIGN_PATH.read_text())

    v2_idx = {}
    for doc, d in anchors.items():
        for s in d['structures']:
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s['nodes'] if n['text'])
            if key not in v2_idx or tn > v2_idx[key][0]:
                v2_idx[key] = (tn, s)
    v2_idx = {k: v[1] for k, v in v2_idx.items()}

    # 构建验证任务(sc2 89对, 映射已验证)
    tasks = []
    for pk in sorted(mapping.keys()):
        ra = realigned.get(pk, {})
        m = mapping[pk]
        if ra.get('status') not in ('realigned', 'same'):
            continue
        anchor = v2_idx.get((m['doc'], ra.get('new_embed', '').split(':')[0]))
        img = PAIR_DIR / pk / 'image.png'
        if not anchor or not img.exists():
            continue
        dtype = classify_diagram(anchor)
        if dtype == 'empty':
            continue
        text_nodes = [n['text'] for n in anchor['nodes'] if n['text']]
        nodes_map = {n['id']: n for n in anchor['nodes']}
        edges_list = []
        for e in anchor['edges']:
            s_t = nodes_map.get(e['src'], {}).get('text', '?')
            d_t = nodes_map.get(e['dst'], {}).get('text', '?')
            edges_list.append((s_t, d_t))
        tasks.append((pk, dtype, img, anchor, text_nodes, edges_list))
    if args.limit:
        tasks = tasks[:args.limit]

    print(f"{'='*64}")
    print(f"M13: Mermaid保真度验证 ({len(tasks)}对, kimi清单式核查)")
    print(f"{'='*64}")
    type_dist = Counter(t[1] for t in tasks)
    print(f"  类型分布: {dict(type_dist)}")

    results = {}
    if OUT_PATH.exists():
        results = json.loads(OUT_PATH.read_text())
        print(f"  断点续跑: 已有{len(results)}条")

    def run_one(item):
        pk, dtype, img, anchor, text_nodes, edges_list = item
        mermaid = to_mermaid(anchor, dtype)
        v = kimi_verify(img, mermaid, text_nodes, edges_list)
        v.update({'pair': pk, 'dtype': dtype, 'n_nodes': len(text_nodes),
                  'n_edges': len(edges_list), 'mermaid': mermaid[:600]})
        return pk, v

    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(run_one, t) for t in tasks if t[0] not in results]
        for fut in as_completed(futs):
            pk, v = fut.result()
            results[pk] = v
            done += 1
            if done % 10 == 0:
                OUT_PATH.write_text(json.dumps(results, ensure_ascii=False))
                print(f"  [{done}/{len(tasks)}] {time.time()-t0:.0f}s")
    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1))

    # ── 汇总 ──
    ok = [v for v in results.values() if 'error' not in v]
    print(f"\n{'='*64}")
    print(f"验证结果 ({len(ok)}/{len(results)}成功)")
    print(f"{'='*64}")
    # 节点可见率 / 边存在率 / 方向正确率 / 遗漏
    agg = {'node_visible': 0, 'node_total': 0, 'edge_exists': 0, 'edge_total': 0,
           'dir_ok': 0, 'dir_total': 0, 'missed': 0, 'scores': []}
    by_type = {}
    for v in ok:
        nc = v.get('node_checks', [])
        ec = v.get('edge_checks', [])
        me = v.get('missed_elements', [])
        nv = sum(1 for c in nc if c.get('visible'))
        ee = sum(1 for c in ec if c.get('exists'))
        dk = sum(1 for c in ec if c.get('exists') and c.get('direction_ok'))
        agg['node_visible'] += nv; agg['node_total'] += len(nc)
        agg['edge_exists'] += ee; agg['edge_total'] += len(ec)
        agg['dir_ok'] += dk; agg['dir_total'] += len(ec)
        agg['missed'] += len(me)
        agg['scores'].append(v.get('fidelity_score', 0))
        bt = by_type.setdefault(v['dtype'], Counter())
        bt['n'] += 1
        bt['node_visible'] += nv; bt['node_total'] += len(nc)
        bt['edge_exists'] += ee; bt['edge_total'] += len(ec)
        bt['missed'] += len(me)
        bt['score_sum'] += v.get('fidelity_score', 0)

    n = len(ok)
    if n:
        import statistics
        print(f"  节点可见率:    {agg['node_visible']}/{agg['node_total']} = {agg['node_visible']/max(1,agg['node_total']):.1%}")
        print(f"  边存在率:      {agg['edge_exists']}/{agg['edge_total']} = {agg['edge_exists']/max(1,agg['edge_total']):.1%}")
        print(f"  方向正确率:    {agg['dir_ok']}/{agg['dir_total']} = {agg['dir_ok']/max(1,agg['dir_total']):.1%}")
        print(f"  遗漏元素总数:  {agg['missed']}")
        print(f"  fidelity_score: 中位{statistics.median(agg['scores'])} 均值{statistics.mean(agg['scores']):.0f}")
        print("\n  分图类型:")
        for dt, c in sorted(by_type.items()):
            print(f"    {dt:22s}: {c['n']}对, 节点可见{c['node_visible']/max(1,c['node_total']):.0%}, "
                  f"边存在{c['edge_exists']/max(1,c['edge_total']):.0%}, 平均分{c['score_sum']/c['n']:.0f}")

    # 低分案例
    print("\n  低分案例(fidelity<70, 前5):")
    for pk, v in sorted(results.items(), key=lambda x: x[1].get('fidelity_score', 100)):
        if v.get('fidelity_score', 100) < 70:
            print(f"    [{pk}] {v['dtype']} 分{v.get('fidelity_score')} "
                  f"遗漏{v.get('missed_elements', [])[:3]} notes={v.get('notes','')[:50]}")
    print(f"\n  输出: {OUT_PATH}")


if __name__ == '__main__':
    main()
