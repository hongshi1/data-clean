#!/usr/bin/env python3
"""
M4+M5: 译码器 + 锚遮蔽判决实验 (ACDD核心验证)
================================================
命题1: D = η ⊕ ε, 后验 q = π(1-p) / [π(1-p) + (1-π)p]

锚遮蔽协议:
  Tier 1 (η标签): 锚点(Visio金标准) vs 表格 → 无噪标签(仅κ_T/N噪声)
  Tier 2 (D观测): VLM提取 vs 表格 → 含感知噪声的比较
  译码: q_e = P(η=1|D_e, θ)  用M3校准的θ
  判决实验: q能否把Tier1正例排在负例之上 (AUROC)
           q是否校准 (ECE) — 对比原始分歧指示D(未校准)

元素宇宙(每对的表格侧):
  step_i: 主事件流步骤存在性 (exst)
  actor_j: 参与者 (act)
  exc_k: 异常流 (exc)

输出: data/gjb_438c/anchor_sc2/judgment_experiment.json
用法: python3 tools/m4_decoder.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import (
    compile_usecase_table, text_match_score, embed_batch, cosine,
    MATCH_TH, EMB_TH,
)

ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
VLM_PATH = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
CALIB_PATH = BASE / "data/gjb_438c/anchor_sc2/calibration.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/judgment_experiment.json"


# ═══════════════════════════════════════════════════════════════
# 通用图适配器: 锚点/VLM → 统一diagram视图
# ═══════════════════════════════════════════════════════════════

def as_diagram_view(source: dict, kind: str) -> dict:
    """锚点/M2输出 → {nodes:[{id,text,type}], edges:[{src,dst,label}]}"""
    if kind == 'anchor':
        nodes = [{'id': n['id'], 'text': n['text'], 'type': n['type']}
                 for n in source['nodes']]
        edges = [{'src': e['src'], 'dst': e['dst'], 'label': e.get('label', '')}
                 for e in source['edges']]
    else:  # vlm
        nodes = [{'id': n['id'], 'text': n.get('text', ''), 'type': n.get('type', 'other')}
                 for n in source.get('nodes', [])]
        edges = [{'src': e['src'], 'dst': e['dst'], 'label': e.get('label', '')}
                 for e in source.get('edges', [])]
    return {'nodes': nodes, 'edges': edges}


def element_verdicts(diagram: dict, X_T: dict) -> dict:
    """图侧 vs 表侧 → 每个表格元素的"在图中找到"判定

    返回: {element_id: {'found': bool, 'score': float}}
      元素id: step:{num} / actor:{i} / exc:{E1}
    """
    verdicts = {}
    text_nodes = [n for n in diagram['nodes']
                  if n['text'].strip() and n['type'] not in ('start', 'end')]
    diag_actors = [n for n in diagram['nodes'] if n['type'] == 'actor']
    is_usecase_diagram = any(n['type'] == 'usecase' for n in diagram['nodes'])

    # ── step / exc: 词法+embedding匹配 ──
    targets = []
    for n in X_T['nodes']:
        if n['type'] == 'process':
            targets.append(('step', n['num'], n['text']))
        elif n['type'] == 'exception':
            targets.append(('exc', n['eid'], n['text']))

    pairs = []
    for kind, key, text in targets:
        for dn in text_nodes:
            sc = text_match_score(text, dn['text'])
            if sc >= MATCH_TH:
                pairs.append((sc, kind, key, text, dn['id']))
    # embedding补充
    low_targets = [(k, key, t) for k, key, t in targets
                   if not any(p[1] == k and p[2] == key for p in pairs)]
    if low_targets:
        t_texts = [t for _, _, t in low_targets]
        n_texts = [n['text'] for n in text_nodes]
        embs = embed_batch(list({*t_texts, *n_texts}))
        emb_map = dict(zip([*t_texts, *n_texts], embs))
        for kind, key, text in low_targets:
            for dn in text_nodes:
                c = cosine(emb_map.get(text, []), emb_map.get(dn['text'], []))
                if c >= EMB_TH:
                    pairs.append((round(c, 3), kind, key, text, dn['id']))

    pairs.sort(key=lambda x: -x[0])
    used_nodes = set()
    for sc, kind, key, text, nid in pairs:
        eid = f"{kind}:{key}"
        if eid not in verdicts and nid not in used_nodes:
            verdicts[eid] = {'found': True, 'score': sc}
            used_nodes.add(nid)
    for kind, key, text in targets:
        eid = f"{kind}:{key}"
        if eid not in verdicts:
            verdicts[eid] = {'found': False, 'score': 0.0}

    # ── actor: 仅用例图模式比对actor节点(流程图无参与者属良性差异,N商掉) ──
    if is_usecase_diagram:
        for i, actor in enumerate(X_T['actors']):
            best = max((text_match_score(actor, n['text']) for n in diag_actors),
                       default=0.0)
            verdicts[f"actor:{i}"] = {'found': best >= MATCH_TH, 'score': best}
    # 流程图模式: actor元素不进入元素宇宙

    return verdicts


# ═══════════════════════════════════════════════════════════════
# 主流程: 锚遮蔽判决实验
# ═══════════════════════════════════════════════════════════════

def load_all():
    anchors = json.loads(ANCHOR_PATH.read_text())
    vlm = json.loads(VLM_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())
    realigned = json.loads(REALIGN_PATH.read_text())
    calib = json.loads(CALIB_PATH.read_text())

    anchor_idx = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            key = (doc_name, s['embed_index'].split(':')[0])
            text_n = sum(1 for n in s['nodes'] if n['text'])
            if key not in anchor_idx or text_n > anchor_idx[key][0]:
                anchor_idx[key] = (text_n, s)
    anchor_idx = {k: v[1] for k, v in anchor_idx.items()}

    pairs = []
    for pk in sorted(mapping.keys()):
        m = mapping[pk]
        ra = realigned.get(pk, {})
        if ra.get('status') not in ('realigned', 'same'):
            continue
        embed = ra.get('new_embed', '').split(':')[0]
        anchor = anchor_idx.get((m['doc'], embed))
        v = vlm.get(pk)
        if anchor and v and 'error' not in v:
            pairs.append((pk, m, anchor, v))
    return pairs, calib


def main():
    pairs, calib = load_all()
    theta = calib['theta_global']
    p_miss = theta['node_miss_rate']['value']       # P(D=1|η=0)
    p_halluc = theta['node_halluc_rate']['value']   # P(D=0|η=1)近似

    print(f"{'='*64}")
    print(f"M4+M5: 译码器 + 锚遮蔽判决实验 ({len(pairs)}对)")
    print(f"{'='*64}")
    print(f"  θ: p_miss={p_miss:.3f} p_halluc={p_halluc:.3f}")

    # ── 元素级双观测 ──
    records = []  # {pair, doc, element, kind, eta, D, score_t1, score_t2}
    for pk, m, anchor, v in pairs:
        X_T = compile_usecase_table(
            BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase" / pk / 'table.csv')
        if not X_T:
            continue
        t1 = element_verdicts(as_diagram_view(anchor, 'anchor'), X_T)
        t2 = element_verdicts(as_diagram_view(v, 'vlm'), X_T)
        for eid in t1:
            if eid not in t2:
                continue
            records.append({
                'pair': pk, 'doc': m['doc'], 'element': eid,
                'kind': eid.split(':')[0],
                'eta': 0 if t1[eid]['found'] else 1,   # Tier1标签(无噪侧)
                'D': 0 if t2[eid]['found'] else 1,     # Tier2观测(VLM侧)
                'score_t1': t1[eid]['score'],
                'score_t2': t2[eid]['score'],
            })

    n = len(records)
    print(f"\n  元素级记录: {n}条 (Tier1正例{sum(1 for r in records if r['eta']==1 and r['D']==1)}"
          f" / Tier2观测分歧{sum(1 for r in records if r['D']==1)})")

    # ── 混淆矩阵: Tier2观测 vs Tier1标签 ──
    tp = sum(1 for r in records if r['eta'] == 1 and r['D'] == 1)
    fn = sum(1 for r in records if r['eta'] == 1 and r['D'] == 0)
    fp = sum(1 for r in records if r['eta'] == 0 and r['D'] == 1)
    tn = sum(1 for r in records if r['eta'] == 0 and r['D'] == 0)
    print("\n  锚遮蔽混淆矩阵 (D vs η):")
    print("              D=1(分歧)  D=0(一致)")
    print(f"    η=1(真矛盾)  {tp:4d}      {fn:4d}")
    print(f"    η=0(一致)    {fp:4d}      {tn:4d}")
    if tp + fn:
        print(f"  Tier2对Tier1的原始查全率: {tp/(tp+fn):.1%} (漏掉{fn}条)")
    if tp + fp:
        print(f"  Tier2原始查准率: {tp/(tp+fp):.1%}")

    # ── π先验 + 分元素类型θ (按文档分块: 一半估计, 一半评测) ──
    docs = sorted({r['doc'] for r in records})
    train_docs = set(docs[::2])
    train = [r for r in records if r['doc'] in train_docs]
    test = [r for r in records if r['doc'] not in train_docs]
    pi_train = sum(r['eta'] for r in train) / max(1, len(train))
    print(f"\n  文档分块: 训练{len(train_docs)}文档(π={pi_train:.3f}) "
          f"/ 测试{len(docs)-len(train_docs)}文档({len(test)}条)")

    # 分类型θ: 在训练文档上估计 P(D=1|η=0)与P(D=0|η=1) per kind
    theta_kind = {}
    for kind in ('step', 'exc', 'actor'):
        tr = [r for r in train if r['kind'] == kind]
        if not tr:
            continue
        neg = [r for r in tr if r['eta'] == 0]  # η=0: D=1即感知误差
        pos = [r for r in tr if r['eta'] == 1]  # η=1: D=0即漏报
        p_miss_k = (sum(r['D'] for r in neg) / len(neg)) if neg else p_miss
        p_hall_k = (sum(1 - r['D'] for r in pos) / len(pos)) if pos else p_halluc
        pi_k = (sum(r['eta'] for r in tr) / len(tr))
        theta_kind[kind] = {
            'p_miss': round(p_miss_k, 4),   # P(D=1|η=0)
            'p_halluc': round(p_hall_k, 4),  # P(D=0|η=1)
            'pi': round(pi_k, 4), 'n': len(tr),
        }
        print(f"    θ[{kind:5s}]: p_miss={p_miss_k:.3f} p_halluc={p_hall_k:.3f} π={pi_k:.3f} (n={len(tr)})")

    # ── 译码: 命题1后验 (全局θ + 分类型θ两种配置) ──
    def decode(D, pi, p_m, p_h):
        if D == 1:
            return pi * (1 - p_m) / (pi * (1 - p_m) + (1 - pi) * p_m)
        else:
            return pi * p_h / (pi * p_h + (1 - pi) * (1 - p_m))

    for r in test:
        # 全局θ版
        r['q'] = round(decode(r['D'], pi_train, p_miss, p_halluc), 4)
        # 分类型θ版 (异质校准: 不同类型相同观测→不同后验)
        tk = theta_kind.get(r['kind'], {})
        r['q_kind'] = round(decode(r['D'], tk.get('pi', pi_train),
                                   tk.get('p_miss', p_miss),
                                   tk.get('p_halluc', p_halluc)), 4)
        r['q_raw'] = float(r['D'])  # 未校准基线: 分歧指示

    # ── 判决实验: AUROC(q) vs AUROC(D) ──
    def auroc(scores, labels):
        pos = [s for s, lab in zip(scores, labels) if lab == 1]
        neg = [s for s, lab in zip(scores, labels) if lab == 0]
        if not pos or not neg:
            return None
        wins = ties = 0
        for p_ in pos:
            for n_ in neg:
                if p_ > n_:
                    wins += 1
                elif p_ == n_:
                    ties += 1
        return (wins + 0.5 * ties) / (len(pos) * len(neg))

    test_labels = [r['eta'] for r in test]
    auc_q = auroc([r['q'] for r in test], test_labels)
    auc_qk = auroc([r['q_kind'] for r in test], test_labels)
    auc_d = auroc([r['q_raw'] for r in test], test_labels)
    auc_s2 = auroc([r['score_t2'] for r in test], test_labels)  # 匹配分反向

    # ECE(q)
    def ece(recs, key='q', n_bins=10):
        bins = defaultdict(list)
        for r in recs:
            b = min(int(r[key] * n_bins), n_bins - 1)
            bins[b].append(r['eta'])
        total = sum(len(v) for v in bins.values())
        e = sum(len(v) / total * abs(sum(v) / len(v) - (b + 0.5) / n_bins)
                for b, v in bins.items())
        return e

    print(f"\n{'='*64}")
    print(f"判决实验结果 (测试集 {len(test)}条, Tier1标签)")
    print(f"{'='*64}")
    print(f"  AUROC(校准后验q全局):  {auc_q:.3f}")
    print(f"  AUROC(分类型后验q_kind): {auc_qk:.3f}  ← 异质校准")
    print(f"  AUROC(原始分歧D):      {auc_d:.3f}")
    print(f"  AUROC(匹配分score):    {auc_s2:.3f}" if auc_s2 else "")
    print(f"  ECE(q):                {ece(test):.3f}")
    print(f"  ECE(q_kind):           {ece(test, 'q_kind'):.3f}")

    # 分元素类型
    print("\n  分元素类型 (AUROC q | AUROC D | n正例):")
    for kind in ('step', 'exc', 'actor'):
        sub = [r for r in test if r['kind'] == kind]
        if not sub:
            continue
        aq = auroc([r['q'] for r in sub], [r['eta'] for r in sub])
        ad = auroc([r['q_raw'] for r in sub], [r['eta'] for r in sub])
        npos = sum(r['eta'] for r in sub)
        aq_s = f"{aq:.3f}" if aq else "n/a"
        ad_s = f"{ad:.3f}" if ad else "n/a"
        print(f"    {kind:6s}: {aq_s} | {ad_s} | {npos}/{len(sub)}")

    # 风险-覆盖曲线数据
    sorted_by_q = sorted(test, key=lambda r: r['q'])
    coverage, risk = [], []
    for i in range(0, len(sorted_by_q), max(1, len(sorted_by_q)//20)):
        kept = sorted_by_q[i:]
        if kept:
            coverage.append(round(1 - i/len(sorted_by_q), 3))
            risk.append(round(sum(r['eta'] for r in kept) / len(kept), 3)
                        if False else round(sum(min(r['q'], 1-r['q']) for r in kept)/len(kept), 3))

    out = {
        'config': {'p_miss': p_miss, 'p_halluc': p_halluc,
                   'pi_train': pi_train, 'n_pairs': len(pairs),
                   'train_docs': sorted(train_docs), 'test_docs': [d for d in docs if d not in train_docs]},
        'confusion': {'tp': tp, 'fn': fn, 'fp': fp, 'tn': tn},
        'judgment': {'auc_q': auc_q, 'auc_q_kind': auc_qk, 'auc_D': auc_d,
                     'auc_score': auc_s2, 'ece_q': ece(test),
                     'ece_q_kind': ece(test, 'q_kind'), 'n_test': len(test)},
        'theta_kind': theta_kind,
        'records': records,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n  输出: {OUT_PATH}")

    # 判定
    print(f"\n{'='*64}")
    if auc_qk is not None and auc_d is not None:
        delta = auc_qk - auc_d
        verdict = "✓ 方法核心成立" if delta > 0.02 else (
            "≈ 持平(校准增益有限)" if delta > -0.02 else "✗ 校准无增益")
        n_hi = sum(1 for r in test if r['q_kind'] > 0.5)
        pos_hi = sum(r['eta'] for r in test if r['q_kind'] > 0.5)
        print(f"  结论: AUROC(q_kind) - AUROC(D) = {delta:+.3f} → {verdict}")
        print(f"  (q_kind>0.5的元素{n_hi}条, 其中真实矛盾{pos_hi}条, 精度"
              f"{pos_hi/max(1,n_hi):.1%})")
        # 风险-覆盖: q_kind排序下的选择性风险
        srt = sorted(test, key=lambda r: -r['q_kind'])
        for cov in (1.0, 0.8, 0.6, 0.4):
            k = max(1, int(len(srt) * cov))
            kept = srt[:k]
            acc = sum(1 for r in kept if (r['q_kind'] > 0.5) == (r['eta'] == 1)) / len(kept)
            print(f"    覆盖{cov:.0%}: 决策精度{acc:.1%}")


if __name__ == "__main__":
    main()
