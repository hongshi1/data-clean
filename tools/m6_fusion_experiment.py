#!/usr/bin/env python3
"""
M6: 多通道融合判决实验 (VLM + OCR)
====================================
核心问题: 融合校准译码 vs 单通道 vs 朴素投票 — 谁的AUROC/ECE好?

通道:
  C_vlm: kimi结构化提取 (元素级 found/not)
  C_ocr: RapidOCR文字块 (元素文字存在性 — 部分通道,无结构)

译码配置:
  q_vlm:  单VLM通道 (M4基线)
  q_ocr:  单OCR通道
  q_or:   OR融合(任一通道找到即找到), 端到端校准
  q_ci:   条件独立因子化(对数几率累加) — 理论上界参照
  vote:   朴素投票(未校准: 任一分歧即报)

簇签名译码 (命题2): 对级 — 分歧数k的二项检验
  q_pair = P(对内存在真实不一致 | k, m, θ)

输出: data/gjb_438c/anchor_sc2/fusion_experiment.json
用法: python3 tools/m6_fusion_experiment.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import compile_usecase_table, save_emb_cache
from m4_decoder import as_diagram_view, element_verdicts

ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
VLM_PATH = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"
OCR_PATH = BASE / "data/gjb_438c/anchor_sc2/ocr_extractions.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/fusion_experiment.json"

EXCLUDE_PAIRS = {'2_084'}  # 聚合错配(图片本身配错)


def ocr_pseudo_nodes(ocr_result: dict) -> list[dict]:
    """OCR文字块 → 伪节点(含相邻块合并, 处理节点文字被拆成多块的情况)"""
    blocks = [b for b in ocr_result.get('blocks', []) if b.get('text')]
    nodes = []
    for i, b in enumerate(blocks):
        nodes.append({'id': f'o{i}', 'text': b['text'], 'type': 'other'})
    # 相邻块合并(窗口2-3): 节点文字换行拆分恢复
    for w in (2, 3):
        for i in range(len(blocks) - w + 1):
            merged = ''.join(blocks[j]['text'] for j in range(i, i + w))
            nodes.append({'id': f'm{i}_{w}', 'text': merged, 'type': 'other'})
    # 全文(长节点兜底)
    if blocks:
        nodes.append({'id': 'full', 'text': ocr_result.get('full_text', ''), 'type': 'other'})
    return nodes


def ocr_element_verdicts(ocr_result: dict, X_T: dict) -> dict:
    """OCR通道元素判定: 伪节点(块+合并窗口) 走与VLM相同的匹配管线"""
    pseudo = ocr_pseudo_nodes(ocr_result)
    diagram = {'nodes': pseudo, 'edges': []}
    return element_verdicts(diagram, X_T)


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


def ece(pairs_data, key, n_bins=10):
    bins = defaultdict(list)
    for r in pairs_data:
        b = min(int(r[key] * n_bins), n_bins - 1)
        bins[b].append(r['eta'])
    total = sum(len(v) for v in bins.values())
    if not total:
        return None
    return sum(len(v) / total * abs(sum(v) / len(v) - (b + 0.5) / n_bins)
               for b, v in bins.items())


def main():
    anchors = json.loads(ANCHOR_PATH.read_text())
    vlm = json.loads(VLM_PATH.read_text())
    ocr = json.loads(OCR_PATH.read_text())
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

    # ── 双通道元素级观测 ──
    records = []
    pairs_data = defaultdict(lambda: {'m': 0, 'k_t1': 0, 'k_vlm': 0, 'k_ocr': 0,
                                       'k_or': 0, 'doc': '', 'uc': ''})
    for pk in sorted(mapping.keys()):
        if pk in EXCLUDE_PAIRS:
            continue
        m = mapping[pk]
        ra = realigned.get(pk, {})
        if ra.get('status') not in ('realigned', 'same'):
            continue
        v = vlm.get(pk)
        o = ocr.get(pk)
        if not v or 'error' in v or not o or 'error' in o:
            continue
        anchor = anchor_idx.get((m['doc'], ra.get('new_embed', '').split(':')[0]))
        if not anchor:
            continue
        X_T = compile_usecase_table(
            BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase" / pk / 'table.csv')
        if not X_T:
            continue

        t1 = element_verdicts(as_diagram_view(anchor, 'anchor'), X_T)
        t2v = element_verdicts(as_diagram_view(v, 'vlm'), X_T)
        t2o = ocr_element_verdicts(o, X_T)

        pd = pairs_data[pk]
        pd['doc'], pd['uc'] = m['doc'], X_T['uc_name']
        for eid in t1:
            if eid not in t2v or eid not in t2o:
                continue
            eta = 0 if t1[eid]['found'] else 1
            d_v = 0 if t2v[eid]['found'] else 1
            d_o = 0 if t2o[eid]['found'] else 1
            records.append({
                'pair': pk, 'doc': m['doc'], 'element': eid,
                'kind': eid.split(':')[0], 'eta': eta,
                'd_vlm': d_v, 'd_ocr': d_o,
                'd_or': 0 if (d_v == 0 or d_o == 0) else 1,  # OR: 任一找到
            })
            pd['m'] += 1
            pd['k_t1'] += eta
            pd['k_vlm'] += d_v
            pd['k_ocr'] += d_o
            pd['k_or'] += (0 if (d_v == 0 or d_o == 0) else 1)

    n = len(records)
    print(f"{'='*64}")
    print(f"M6: 多通道融合判决实验 ({len(pairs_data)}对, {n}元素)")
    print(f"{'='*64}")
    print(f"  VLM分歧率: {sum(r['d_vlm'] for r in records)/n:.1%}  "
          f"OCR分歧率: {sum(r['d_ocr'] for r in records)/n:.1%}  "
          f"OR融合分歧率: {sum(r['d_or'] for r in records)/n:.1%}")

    # ── 文档分块 ──
    docs = sorted({r['doc'] for r in records})
    train_docs = set(docs[::2])
    train = [r for r in records if r['doc'] in train_docs]
    test = [r for r in records if r['doc'] not in train_docs]
    print(f"\n  训练{len(train_docs)}文档({len(train)}条) / 测试{len(docs)-len(train_docs)}文档({len(test)}条)")

    # ── 通道θ估计(训练集, 分通道) ──
    def est_theta(rows, dkey):
        neg = [r for r in rows if r['eta'] == 0]
        pos = [r for r in rows if r['eta'] == 1]
        p_miss = (sum(r[dkey] for r in neg) / len(neg)) if neg else 0.1
        p_hall = (sum(1 - r[dkey] for r in pos) / len(pos)) if pos else 0.1
        pi = (sum(r['eta'] for r in rows) / len(rows)) if rows else 0.5
        return {'p_miss': p_miss, 'p_halluc': p_hall, 'pi': pi,
                'n_neg': len(neg), 'n_pos': len(pos)}

    th_vlm = est_theta(train, 'd_vlm')
    th_ocr = est_theta(train, 'd_ocr')
    th_or = est_theta(train, 'd_or')
    print(f"\n  θ_vlm:  p_miss={th_vlm['p_miss']:.3f} p_halluc={th_vlm['p_halluc']:.3f}")
    print(f"  θ_ocr:  p_miss={th_ocr['p_miss']:.3f} p_halluc={th_ocr['p_halluc']:.3f}")
    print(f"  θ_or:   p_miss={th_or['p_miss']:.3f} p_halluc={th_or['p_halluc']:.3f}")
    print("  (OR的p_miss应低于两个单通道 — 互补性检验)")

    # ── 译码(测试集) ──
    def decode(D, pi, p_m, p_h):
        if D == 1:
            return pi * (1 - p_m) / (pi * (1 - p_m) + (1 - pi) * p_m)
        return pi * p_h / (pi * p_h + (1 - pi) * (1 - p_m))

    def logodds_decode(d_v, d_o, th_v, th_o):
        """条件独立因子化: log-odds累加"""
        def llr(D, th):
            if D == 1:
                num, den = (1 - th['p_miss']), th['p_miss']
            else:
                num, den = th['p_halluc'], (1 - th['p_miss'])
            return num / max(den, 1e-9)
        pi = th_v['pi']
        prior_odds = pi / max(1 - pi, 1e-9)
        post_odds = prior_odds * llr(d_v, th_v) * llr(d_o, th_o)
        return post_odds / (1 + post_odds)

    for r in test:
        r['q_vlm'] = decode(r['d_vlm'], th_vlm['pi'], th_vlm['p_miss'], th_vlm['p_halluc'])
        r['q_ocr'] = decode(r['d_ocr'], th_ocr['pi'], th_ocr['p_miss'], th_ocr['p_halluc'])
        r['q_or'] = decode(r['d_or'], th_or['pi'], th_or['p_miss'], th_or['p_halluc'])
        r['q_ci'] = logodds_decode(r['d_vlm'], r['d_ocr'], th_vlm, th_ocr)
        r['q_vote'] = float(1 if (r['d_vlm'] or r['d_ocr']) else 0)

    # ── 元素级判决 ──
    labels = [r['eta'] for r in test]
    print(f"\n{'='*64}")
    print(f"元素级判决实验 (测试{len(test)}条, Tier1标签)")
    print(f"{'='*64}")
    print(f"  {'配置':22s} {'AUROC':>7s} {'ECE':>7s}")
    results_e = {}
    for key, label in [('q_vlm', '单VLM(M4基线)'), ('q_ocr', '单OCR'),
                       ('q_or', 'OR融合端到端校准'), ('q_ci', '条件独立因子化'),
                       ('q_vote', '朴素投票(未校准)')]:
        a = auroc([r[key] for r in test], labels)
        e = ece(test, key)
        results_e[key] = {'auroc': a, 'ece': e}
        print(f"  {label:22s} {a:7.3f} {e:7.3f}")

    # ── 对级簇签名译码 (命题2: 分歧数的二项尾概率) ──
    print(f"\n{'='*64}")
    print("对级簇签名译码 (命题2: k~Bin(m,p)的尾概率)")
    print(f"{'='*64}")
    from math import comb
    pbar = th_or['p_miss']  # H0下单元素分歧率

    pair_rows = []
    for pk, pd in pairs_data.items():
        if pd['m'] < 3 or pd['doc'] not in {r['doc'] for r in test}:
            continue
        m, k = pd['m'], pd['k_vlm']  # 簇译码用VLM通道分歧数(高精确通道)
        # H0尾概率: P(Bin(m,pbar) >= k)
        tail = sum(comb(m, i) * pbar**i * (1-pbar)**(m-i) for i in range(k, m+1))
        pair_rows.append({
            'pair': pk, 'uc': pd['uc'], 'm': m, 'k_t1': pd['k_t1'], 'k_vlm': k,
            'p_value': round(tail, 6),
            'eta_pair': 1 if pd['k_t1'] >= max(2, pd['m']//3) else 0,  # 高drift对
        })
    if pair_rows:
        # 译码: q_pair = 1 - tail 校准为后验(粗)
        pi_pair = sum(r['eta_pair'] for r in pair_rows) / len(pair_rows)
        for r in pair_rows:
            # 贝叶斯: P(H1|k) ∝ pi·P(k|H1) / [(1-pi)·P(k|H0)]
            # P(k|H1)取1(有真矛盾时分歧偏多)
            lr = (1 - r['p_value']) / max(r['p_value'], 1e-9)
            r['q_pair'] = pi_pair * lr / (pi_pair * lr + (1 - pi_pair))
        a_pair = auroc([r['q_pair'] for r in pair_rows],
                       [r['eta_pair'] for r in pair_rows])
        a_count = auroc([r['k_vlm'] for r in pair_rows],
                        [r['eta_pair'] for r in pair_rows])
        print(f"  对数: {len(pair_rows)} (m≥3), 高drift对{sum(r['eta_pair'] for r in pair_rows)}")
        print(f"  AUROC(q_pair簇签名): {a_pair:.3f}")
        print(f"  AUROC(原始分歧数k):  {a_count:.3f}")
        # 命题2实证: k_vlm≥2的对中高drift占比
        hi = [r for r in pair_rows if r['k_vlm'] >= 2]
        if hi:
            rate = sum(r['eta_pair'] for r in hi) / len(hi)
            print(f"  k_vlm≥2的对: {len(hi)}个, 高drift占比{rate:.1%} (基础率{pi_pair:.1%})")
    else:
        a_pair = a_count = None

    out = {
        'config': {'exclude': list(EXCLUDE_PAIRS), 'train_docs': sorted(train_docs),
                   'theta_vlm': th_vlm, 'theta_ocr': th_ocr, 'theta_or': th_or},
        'element_level': results_e,
        'pair_level': {'auc_q_pair': a_pair, 'auc_count': a_count,
                       'n_pairs': len(pair_rows)},
        'records': records,
        'pair_rows': pair_rows,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    save_emb_cache()
    print(f"\n  输出: {OUT_PATH}")

    # 结论
    best = max(results_e.items(), key=lambda x: x[1]['auroc'] or 0)
    print(f"\n  ★ 最优元素级配置: {best[0]} (AUROC={best[1]['auroc']:.3f})")


if __name__ == "__main__":
    main()
