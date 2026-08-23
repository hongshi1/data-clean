#!/usr/bin/env python3
"""
M9: 方向元素(dir)译码实验
==========================
元素宇宙扩展: dir:{i}:{j} = 表格连续步骤对(i<j), 双侧匹配到图节点后的边方向比较

观测(三值→二值):
  Tier1(锚点): 边(i→j)=η0(顺序一致) / 边(j→i)=η1(方向矛盾) / 无边=跳过(不比较)
  Tier2(VLM):  D=1(VLM边j→i,反向) / D=0(VLM边i→j,同向) / 无边=跳过

译码: 命题1后验, p = dir_flip_rate (M3校准: 0.9%)

输出: data/gjb_438c/anchor_sc2/direction_decoding.json
用法: python3 tools/m9_direction_decoding.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import compile_usecase_table, text_match_score, embed_batch, cosine, MATCH_TH, EMB_TH, save_emb_cache

ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
VLM_PATH = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/direction_decoding.json"

EXCLUDE_PAIRS = {'2_084'}


def match_steps_to_nodes(node_texts: list[dict], X_T: dict) -> dict:
    """表格步骤 → 图节点id (词法+embedding, 复用M4逻辑的最小版)"""
    steps = [n for n in X_T['nodes'] if n['type'] == 'process']
    pairs = []
    for st in steps:
        for dn in node_texts:
            sc = text_match_score(st['text'], dn['text'])
            if sc >= MATCH_TH:
                pairs.append((sc, st['id'], dn['id']))
    low = [(sc, s, d) for sc, s, d in pairs if sc < 0.75]
    if low:
        all_texts = list({t for t in [x[1] for x in low] + [x[2] for x in low]})
        # 需要原始文本
        pass
    pairs.sort(key=lambda x: -x[0])
    used = set()
    matched = {}
    for sc, sid, did in pairs:
        if sid not in matched and did not in used:
            matched[sid] = {'diag_id': did, 'score': sc}
            used.add(did)
    return matched


def main():
    anchors = json.loads(ANCHOR_PATH.read_text())
    vlm = json.loads(VLM_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())
    realigned = json.loads(REALIGN_PATH.read_text())

    anchor_idx = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            key = (doc_name, s['embed_index'].split(':')[0])
            text_n = sum(1 for n in s['nodes'] if n['text'])
            if key not in anchor_idx or text_n > anchor_idx[key][0]:
                anchor_idx[key] = (text_n, s)
    anchor_idx = {k: v[1] for k, v in anchor_idx.items()}

    records = []
    for pk in sorted(mapping.keys()):
        if pk in EXCLUDE_PAIRS:
            continue
        m = mapping[pk]
        ra = realigned.get(pk, {})
        if ra.get('status') not in ('realigned', 'same'):
            continue
        v = vlm.get(pk)
        if not v or 'error' in v:
            continue
        anchor = anchor_idx.get((m['doc'], ra.get('new_embed', '').split(':')[0]))
        if not anchor:
            continue
        X_T = compile_usecase_table(
            BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase" / pk / 'table.csv')
        if not X_T:
            continue

        # 图侧语义节点
        a_nodes = [{'id': n['id'], 'text': n['text']}
                   for n in anchor['nodes']
                   if n['text'].strip() and n['type'] not in ('start', 'end')]
        v_nodes = [{'id': n['id'], 'text': n.get('text', '')}
                   for n in v.get('nodes', []) if n.get('text', '').strip()]

        m_a = match_steps_to_nodes(a_nodes, X_T)  # step_id → anchor node
        m_v = match_steps_to_nodes(v_nodes, X_T)  # step_id → vlm node

        # 边集合
        a_edges = {(e['src'], e['dst']) for e in anchor['edges']}
        v_edges = {(e['src'], e['dst']) for e in v.get('edges', [])}

        # 连续步骤对
        steps = sorted([n for n in X_T['nodes'] if n['type'] == 'process'],
                       key=lambda n: n['num'])
        for i in range(len(steps) - 1):
            s1, s2 = steps[i], steps[i + 1]
            a1 = m_a.get(s1['id'], {}).get('diag_id')
            a2 = m_a.get(s2['id'], {}).get('diag_id')
            v1 = m_v.get(s1['id'], {}).get('diag_id')
            v2 = m_v.get(s2['id'], {}).get('diag_id')
            if not (a1 and a2 and v1 and v2):
                continue

            # Tier1: 锚点边方向
            if (a2, a1) in a_edges and (a1, a2) not in a_edges:
                eta = 1   # 锚点反向 = 方向矛盾候选
            elif (a1, a2) in a_edges:
                eta = 0   # 锚点同向
            else:
                continue   # 锚点无边 → 不比较
            # Tier2: VLM边方向
            if (v2, v1) in v_edges and (v1, v2) not in v_edges:
                D = 1
            elif (v1, v2) in v_edges:
                D = 0
            else:
                continue   # VLM无边 → 不比较

            records.append({
                'pair': pk, 'doc': m['doc'],
                'element': f"dir:{s1['num']}:{s2['num']}",
                'eta': eta, 'D': D,
                'step_i': s1['text'][:24], 'step_j': s2['text'][:24],
            })

    print(f"{'='*64}")
    print(f"M9: 方向元素译码 ({len(records)}条可比对方向元素)")
    print(f"{'='*64}")
    if not records:
        print("  无可比方向元素")
        return

    # 混淆矩阵
    tp = sum(1 for r in records if r['eta'] == 1 and r['D'] == 1)
    fn = sum(1 for r in records if r['eta'] == 1 and r['D'] == 0)
    fp = sum(1 for r in records if r['eta'] == 0 and r['D'] == 1)
    tn = sum(1 for r in records if r['eta'] == 0 and r['D'] == 0)
    print(f"\n  方向混淆矩阵 (VLM的D vs 锚点的η):")
    print(f"              D=1(VLM反向)  D=0(VLM同向)")
    print(f"    η=1(锚点反向) {tp:4d}          {fn:4d}")
    print(f"    η=0(锚点同向) {fp:4d}          {tn:4d}")

    # p_flip实测(η=0列): P(D=1|η=0)
    p_flip_emp = fp / max(1, fp + tn)
    p_flip_cal = 0.009  # M3校准值
    print(f"\n  方向翻转率: 实测{p_flip_emp:.3f} vs 校准预测{p_flip_cal:.3f}")

    # 命题1译码 (用M3校准的p_flip)
    # π_dir: 方向矛盾的基础率(η=1比例)
    pi = (tp + fn) / len(records)
    for r in records:
        p = p_flip_cal
        if r['D'] == 1:
            r['q'] = round(pi * (1 - p) / (pi * (1 - p) + (1 - pi) * p), 4)
        else:
            r['q'] = round(pi * p / (pi * p + (1 - pi) * (1 - p)), 4)

    # AUROC(q) — 注意: 单通道二元观测下AUROC(q)=AUROC(D), 此处验证q的概率语义
    def auroc(scores, labels):
        pos = [s for s, l in zip(scores, labels) if l == 1]
        neg = [s for s, l in zip(scores, labels) if l == 0]
        if not pos or not neg:
            return None
        wins = ties = 0
        for p_ in pos:
            for n_ in neg:
                if p_ > n_: wins += 1
                elif p_ == n_: ties += 1
        return (wins + 0.5 * ties) / (len(pos) * len(neg))

    auc = auroc([r['q'] for r in records], [r['eta'] for r in records])
    # ECE
    bins = defaultdict(list)
    for r in records:
        b = min(int(r['q'] * 10), 9)
        bins[b].append(r['eta'])
    total = len(records)
    e = sum(len(v)/total * abs(sum(v)/len(v) - (b+0.5)/10) for b, v in bins.items())

    print(f"\n  π(方向矛盾率): {pi:.3f}")
    print(f"  AUROC(q): {auc:.3f}")
    print(f"  ECE(q):   {e:.3f}")

    # 具体案例
    print(f"\n  η=1案例(锚点方向矛盾, VLM是否恢复):")
    for r in records:
        if r['eta'] == 1:
            print(f"    [{r['pair']}] {r['element']}: VLM={'✓恢复' if r['D']==1 else '✗漏报'} "
                  f"| 步骤{r['step_i'][:14]}→{r['step_j'][:14]} q={r['q']}")

    OUT_PATH.write_text(json.dumps({
        'config': {'pi': pi, 'p_flip_cal': p_flip_cal, 'p_flip_emp': p_flip_emp},
        'confusion': {'tp': tp, 'fn': fn, 'fp': fp, 'tn': tn},
        'judgment': {'auroc': auc, 'ece': e, 'n': total},
        'records': records,
    }, ensure_ascii=False, indent=1))
    save_emb_cache()
    print(f"\n  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
