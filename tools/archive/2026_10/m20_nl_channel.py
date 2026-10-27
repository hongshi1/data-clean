#!/usr/bin/env python3
"""
M20: NL翻译通道实验 — 确定性翻译能否替代感知?
================================================
问题: 给LLM看"锚点的自然语言描述+表格" vs 看"渲染图+表格",
      一致性判断能力是否相当? 若相当 → 锚定图的感知可被确定性翻译替代
      (成本↓ 可复现↑ 免VLM幻觉)

通道设计(sc2的89对):
  通道A(VLM): kimi看image.png → 结构化提取 → 元素判定 (已有M2数据)
  通道B(NL):  kimi只看NL描述(translations.json) → 元素判定 (本轮)
  金标准:     Tier1锚点判定(无噪层)

指标: 各通道与Tier1的一致率 + 分歧分析
输出: data/gjb_438c/anchor_v2/nl_channel_experiment.json
用法: python3 tools/m20_nl_channel.py [--workers 6]
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import compile_usecase_table

TRANSLATIONS = BASE / "data/gjb_438c/anchor_v2/translations.json"
MAPPING = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
REALIGN = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
VLM_EXT = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT = BASE / "data/gjb_438c/anchor_v2/nl_channel_experiment.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY
KIMI_MODEL = "kimi-k2.6"

PROMPT = """你是软件需求文档一致性审查专家。下面是一张流程图/用例图的【结构化描述】(来自文档内嵌源文件的确定性解析, 可信)和一张用例描述表。请判断表格的每个元素是否在图中有对应表示。

## 图的结构化描述
{nl_description}

## 用例描述表
用例名: {uc_name}
主事件流步骤:
{steps}
异常流:
{exceptions}
Actors: {actors}

## 任务
对下面每个表格元素, 判断图中是否有对应(语义对应即可, 不要求文字完全一致):
{elements}

严格输出JSON:
{{"verdicts": [{{"element": "元素标识", "found": true或false, "match": "图中对应文字(如找到)"}}]}}"""


def parse_json_loose(text):
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def structured_description(anchor):
    """锚点 → 结构化全文本描述(逐节点编号, 不截断——LLM匹配友好)"""
    lines = []
    text_nodes = [n for n in anchor['nodes'] if n['text']]
    lines.append(f"图包含{len(text_nodes)}个带文字节点:")
    for i, n in enumerate(text_nodes, 1):
        lines.append(f"  {i}. [{n['type']}] {n['text']}")
    nodes_map = {n['id']: n for n in anchor['nodes']}
    edges = [e for e in anchor['edges']
             if nodes_map.get(e['src']) and nodes_map.get(e['dst'])]
    lines.append(f"\n图包含{len(edges)}条连接:")
    for i, e in enumerate(edges, 1):
        st = nodes_map[e['src']]['text'][:20] or nodes_map[e['src']]['type']
        dt = nodes_map[e['dst']]['text'][:20] or nodes_map[e['dst']]['type']
        lbl = f" (条件:{e['label'][:10]})" if e.get('label') else ''
        lines.append(f"  {i}. {st} → {dt}{lbl}")
    return '\n'.join(lines)


def kimi_nl_verdicts(nl_desc, X_T, elements):
    steps_str = '\n'.join(f"  {n['num']}. {n['text'][:50]}"
                          for n in X_T['nodes'] if n['type'] == 'process') or '  (无)'
    exc_str = '\n'.join(f"  {k}: {v[:40]}" for k, v in X_T['exceptions'].items()) or '  (无)'
    elem_str = '\n'.join(f"  - {e}: {desc[:40]}" for e, desc in elements)
    prompt = PROMPT.format(nl_description=nl_desc[:1500], uc_name=X_T['uc_name'],
                           steps=steps_str, exceptions=exc_str,
                           actors=', '.join(X_T['actors']), elements=elem_str)
    for _ in range(2):
        try:
            r = httpx.post(KIMI_URL, headers={
                'Authorization': f'Bearer {KIMI_KEY}', 'Content-Type': 'application/json'
            }, json={'model': KIMI_MODEL, 'thinking': {'type': 'disabled'},
                     'messages': [{'role': 'user', 'content': prompt}],
                     'max_tokens': 2000, 'temperature': 0.6,
                     'response_format': {'type': 'json_object'}}, timeout=120)
            if r.status_code == 200:
                d = parse_json_loose(r.json()['choices'][0]['message'].get('content', ''))
                if d:
                    return {v.get('element', ''): v.get('found', False)
                            for v in d.get('verdicts', [])}
        except Exception:
            time.sleep(3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    translations = json.loads(TRANSLATIONS.read_text())
    mapping = json.loads(MAPPING.read_text())
    realigned = json.loads(REALIGN.read_text())
    anchors = json.loads(ANCHOR_V2.read_text())
    vlm = json.loads(VLM_EXT.read_text())

    v2_idx = {}
    for doc, d in anchors.items():
        for s in d['structures']:
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s['nodes'] if n['text'])
            if key not in v2_idx or tn > v2_idx[key][0]:
                v2_idx[key] = (tn, s)
    v2_idx = {k: v[1] for k, v in v2_idx.items()}

    # 翻译索引: (doc, embed) → NL
    tr_idx = {}
    for key, tr in translations.items():
        tr_idx[(tr['doc'], tr['embed'].split(':')[0])] = tr

    # 构建任务
    tasks = []
    for pk in sorted(mapping.keys()):
        ra = realigned.get(pk, {})
        m = mapping[pk]
        if ra.get('status') not in ('realigned', 'same'):
            continue
        embed = ra.get('new_embed', '').split(':')[0]
        anchor = v2_idx.get((m['doc'], embed))
        tr = tr_idx.get((m['doc'], embed))
        v = vlm.get(pk)
        if not anchor or not tr or not v or 'error' in v:
            continue
        X_T = compile_usecase_table(PAIR_DIR / pk / 'table.csv')
        if not X_T:
            continue
        # 元素清单(与M4的元素宇宙一致)
        elements = []
        for n in X_T['nodes']:
            if n['type'] == 'process':
                elements.append((f"step:{n['num']}", f"步骤{n['num']}: {n['text'][:40]}"))
            elif n['type'] == 'exception':
                elements.append((f"exc:{n['eid']}", f"异常流{n['eid']}: {n['text'][:40]}"))
        for i, actor in enumerate(X_T['actors']):
            elements.append((f"actor:{i}", f"参与者: {actor}"))
        if not elements:
            continue
        tasks.append((pk, tr['nl'], X_T, elements, anchor, v))

    print(f"{'='*64}")
    if args.limit:
        tasks = tasks[:args.limit]
    print(f"M20: NL通道实验 ({len(tasks)}对)")
    print(f"{'='*64}")

    results = json.loads(OUT.read_text()) if OUT.exists() else {}

    def run_one(item):
        pk, nl, X_T, elements, anchor, v = item
        nl_struct = structured_description(anchor)
        verdicts = kimi_nl_verdicts(nl_struct, X_T, elements)
        return pk, {'nl_verdicts': verdicts}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(run_one, t) for t in tasks if t[0] not in results]
        done = 0
        for fut in as_completed(futs):
            pk, r = fut.result()
            results[pk] = r
            done += 1
            if done % 15 == 0:
                OUT.write_text(json.dumps(results, ensure_ascii=False))
                print(f"  [{done}/{len(tasks)}]")

    # ── 分析: 三通道对比 ──
    from m4_decoder import as_diagram_view, element_verdicts

    stats = {'nl': Counter(), 'vlm': Counter()}
    records = []
    for pk, nl, X_T, elements, anchor, v in tasks:
        r = results.get(pk, {})
        nl_verdicts = r.get('nl_verdicts') or {}
        # Tier1(金标准)与VLM通道的元素判定
        t1 = element_verdicts(as_diagram_view(anchor, 'anchor'), X_T)
        t2v = element_verdicts(as_diagram_view(v, 'vlm'), X_T)
        for eid, desc in elements:
            if eid not in t1 or eid not in t2v:
                continue
            eta = 0 if t1[eid]['found'] else 1
            d_vlm = 0 if t2v[eid]['found'] else 1
            d_nl = 0 if nl_verdicts.get(eid, True) else 1  # 默认found(保守)
            records.append({'pair': pk, 'element': eid, 'eta': eta,
                            'd_vlm': d_vlm, 'd_nl': d_nl})
            stats['nl']['n'] += 1
            stats['vlm']['n'] += 1
            if d_nl == eta:
                stats['nl']['agree'] += 1
            if d_vlm == eta:
                stats['vlm']['agree'] += 1

    n = stats['nl']['n']
    print(f"\n{'='*64}")
    print(f"NL通道实验结果 ({n}元素)")
    print(f"{'='*64}")
    print(f"  NL通道(文字描述)与Tier1一致率:  {stats['nl']['agree']/max(1,n):.1%}")
    print(f"  VLM通道(看图)与Tier1一致率:     {stats['vlm']['agree']/max(1,n):.1%}")

    # 分歧分析
    both_right = nl_only_right = vlm_only_right = both_wrong = 0
    for r in records:
        nl_ok = r['d_nl'] == r['eta']
        vlm_ok = r['d_vlm'] == r['eta']
        if nl_ok and vlm_ok: both_right += 1
        elif nl_ok: nl_only_right += 1
        elif vlm_ok: vlm_only_right += 1
        else: both_wrong += 1
    print(f"\n  分解: 双对{both_right} 仅NL对{nl_only_right} 仅VLM对{vlm_only_right} 双错{both_wrong}")

    # NL通道的错误模式
    fn_nl = sum(1 for r in records if r['eta'] == 1 and r['d_nl'] == 0)
    fp_nl = sum(1 for r in records if r['eta'] == 0 and r['d_nl'] == 1)
    fn_v = sum(1 for r in records if r['eta'] == 1 and r['d_vlm'] == 0)
    fp_v = sum(1 for r in records if r['eta'] == 0 and r['d_vlm'] == 1)
    print(f"  NL: 漏报{fn_nl} 误报{fp_nl} | VLM: 漏报{fn_v} 误报{fp_v}")

    OUT.write_text(json.dumps({'records': records,
                               'nl_verdicts_raw': {k: v for k, v in results.items()}},
                              ensure_ascii=False, indent=1))
    print(f"\n  输出: {OUT}")
    print(f"\n  ★ 结论: NL通道{'可' if stats['nl']['agree']/max(1,n) >= stats['vlm']['agree']/max(1,n) - 0.05 else '暂不可'}替代VLM感知"
          f"(差距{(stats['vlm']['agree']-stats['nl']['agree'])/max(1,n):+.1%})")


if __name__ == '__main__':
    main()
