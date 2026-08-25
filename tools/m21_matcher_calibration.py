#!/usr/bin/env python3
"""
M21: 匹配器阈值校准 (ACDD θ框架的最后一块)
================================================
把embedding匹配阈值从"拍脑袋的0.62"变成"裁决标签校准的最优点":

方法: 对每个已裁决的分歧项(共702条: M7的417+M17的285),
     计算该项对锚点节点的最佳匹配分(词法+embedding),
     用标签做ROC分析:
       compiler_bug项 → 分数应高(存在对应, 阈值应放它过)
       real_bug项     → 分数应低(真缺失, 阈值应拦住它)
     扫描阈值找分离最优点

输出: 最优阈值 + 匹配器的θ误差模型(p_miss/p_halluc) + 校准后重跑Tier1
用法: python3 tools/m21_matcher_calibration.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import text_match_score, embed_batch, cosine, MATCH_TH

ADJ_SC2 = BASE / "data/gjb_438c/anchor_sc2/llm_adjudication.json"
ADJ_SCENE = BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json"
TIER1_SC2 = BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies_v2.json"
TIER1_SCENE = BASE / "data/gjb_438c/anchor_v2/scene_tier1.json"
CENSUS = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
ANCHOR_SC2 = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
REALIGN = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
MAPPING = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT = BASE / "data/gjb_438c/anchor_v2/matcher_calibration.json"

EMB_TH_CURRENT = 0.62


def build_anchor_idx(anchors_path):
    anchors = json.loads(Path(anchors_path).read_text())
    idx = {}
    for doc, d in anchors.items():
        for s in d['structures']:
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s['nodes'] if n['text'])
            if key not in idx or tn > idx[key][0]:
                idx[key] = (tn, s)
    return {k: v[1] for k, v in idx.items()}


def collect_adjudicated_items():
    """收集全部已裁决项: (pair, item_text, label, anchor)"""
    items = []
    realigned = json.loads(REALIGN.read_text())
    mapping = json.loads(MAPPING.read_text())

    # ── 多场景(M17) ──
    adj_s = json.loads(ADJ_SCENE.read_text())
    census = json.loads(CENSUS.read_text())
    idx_v2 = build_anchor_idx(ANCHOR_V2)
    for tid, r in adj_s.items():
        pk = r['pair']
        label = r.get('final')
        if label not in ('real_bug', 'benign_variation', 'compiler_bug'):
            continue
        evi = r['evidence']
        if '「' not in evi:
            continue
        item_text = evi.split('「')[1].split('」')[0]
        # 截断处理: "接口表receiver「X」"等
        c = census.get(pk, {})
        entry = idx_v2.get((c.get('doc', ''), c.get('new_embed', '').split(':')[0]))
        anchor = entry[1] if isinstance(entry, tuple) else entry
        if anchor is None:
            va = BASE / 'data/gjb_438c/pair_dataset' / r['scene'] / pk / 'visio_anchor.json'
            if va.exists():
                anchor = json.loads(va.read_text())
        if anchor:
            items.append({'pair': pk, 'text': item_text, 'label': label,
                          'anchor': anchor, 'source': 'M17'})

    # ── sc2(M7) ──
    adj_2 = json.loads(ADJ_SC2.read_text())
    t1_sc2 = json.loads(TIER1_SC2.read_text())
    idx_sc2 = build_anchor_idx(ANCHOR_SC2)
    for tid, r in adj_2.items():
        pk, di = tid.rsplit('_', 1)
        label = r.get('final')
        if label not in ('real_bug', 'benign_variation', 'compiler_bug'):
            continue
        v = t1_sc2.get(pk, {})
        discs = v.get('discrepancies', [])
        di = int(di)
        if di >= len(discs):
            continue
        d = discs[di]
        ts = d.get('table_side') or {}
        item_text = ts.get('text', '')
        if not item_text:
            continue
        ra = realigned.get(pk, {})
        if ra.get('status') not in ('realigned', 'same'):
            continue
        anchor = idx_sc2.get((v.get('doc', ''), ra.get('new_embed', '').split(':')[0]))
        if anchor:
            items.append({'pair': pk, 'text': item_text, 'label': label,
                          'anchor': anchor, 'source': 'M7'})
    return items


def best_match_score(item_text, anchor):
    """项对锚点全部节点的最佳匹配分(词法优先, embedding兜底)"""
    a_texts = [n['text'].replace('\n', '') for n in anchor['nodes']
               if n['text'] and n['type'] != 'boundary']
    best_lex = 0
    best_text = None
    for at in a_texts:
        sc = text_match_score(item_text, at)
        if sc > best_lex:
            best_lex, best_text = sc, at
    # embedding(词法未达0.5时)
    best_emb = 0
    if best_lex < 0.5 and a_texts:
        embs = embed_batch([item_text] + a_texts)
        for at, e in zip(a_texts, embs[1:]):
            c = cosine(embs[0], e)
            if c > best_emb:
                best_emb = c
    return best_lex, best_emb, best_text


def main():
    items = collect_adjudicated_items()
    print(f"{'='*64}")
    print(f"M21: 匹配器阈值校准 ({len(items)}条已裁决项)")
    print(f"{'='*64}")
    labels = Counter(i['label'] for i in items)
    print(f"标签分布: {dict(labels)}")

    # ── 计算每项的最佳分数 ──
    scored = []
    for it in items:
        lex, emb, bt = best_match_score(it['text'], it['anchor'])
        scored.append({**it, 'lex': lex, 'emb': emb, 'match_text': bt,
                       'final_score': max(lex, emb)})

    # ── ROC分析: 阈值扫描 ──
    # 目标: compiler_bug项分数高(该匹配), real_bug项分数低(不该匹配)
    # benign: 语义上是"合理差异"——匹配与否取决于类型, 作为中性组
    print(f"\n分数分布(按标签):")
    for label in ('compiler_bug', 'real_bug', 'benign_variation'):
        scores = [s['final_score'] for s in scored if s['label'] == label]
        if scores:
            scores.sort()
            n = len(scores)
            print(f"  {label:18s}: n={n:3d} 中位={scores[n//2]:.2f} "
                  f"P25={scores[n//4]:.2f} P75={scores[3*n//4]:.2f}")

    # ── 阈值扫描: 分离compiler_bug(应>阈值=匹配)与real_bug(应<阈值=不匹配) ──
    print(f"\n阈值扫描 (目标: compiler_bug越过阈值, real_bug留在阈值下):")
    print(f"  {'阈值':>5s} {'compiler修复':>10s} {'real误翻':>8s} {'benign匹配':>9s} {'净收益':>6s}")
    best_th, best_gain = EMB_TH_CURRENT, -999
    for th in [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70, 0.72, 0.75]:
        comp_fixed = sum(1 for s in scored
                         if s['label'] == 'compiler_bug' and s['final_score'] >= th)
        comp_total = sum(1 for s in scored if s['label'] == 'compiler_bug')
        real_flip = sum(1 for s in scored
                        if s['label'] == 'real_bug' and s['final_score'] >= th)
        real_total = sum(1 for s in scored if s['label'] == 'real_bug')
        benign_m = sum(1 for s in scored
                       if s['label'] == 'benign_variation' and s['final_score'] >= th)
        benign_total = sum(1 for s in scored if s['label'] == 'benign_variation')
        # 净收益: 修复compiler - 误翻real*2(real更贵)
        gain = comp_fixed - 2 * real_flip
        print(f"  {th:5.2f} {comp_fixed:4d}/{comp_total:<4d} {real_flip:4d}/{real_total:<3d} "
              f"{benign_m:4d}/{benign_total:<4d} {gain:+5d}")
        if gain > best_gain:
            best_gain, best_th = gain, th

    print(f"\n  ★ 最优阈值: {best_th} (净收益{best_gain:+d}, 当前{EMB_TH_CURRENT})")

    # ── 匹配器θ误差模型(在最优阈值下) ──
    # 视角: "匹配器说匹配" vs "裁决真值(存在对应)"
    # compiler_bug = 真值存在但匹配器说缺失 → 匹配器的漏检(p_miss)
    # real_bug中匹配器说匹配的 = 真值不存在但匹配器说匹配 → 误收(p_halluc)
    th = best_th
    matched = [s for s in scored if s['final_score'] >= th]
    unmatched = [s for s in scored if s['final_score'] < th]
    # 真值存在对应 = compiler_bug类; 真值不存在 = real_bug类(benign中性)
    true_exists = [s for s in scored if s['label'] == 'compiler_bug']
    true_absent = [s for s in scored if s['label'] == 'real_bug']
    p_miss = (sum(1 for s in true_exists if s['final_score'] < th)
              / max(1, len(true_exists)))
    p_hall = (sum(1 for s in true_absent if s['final_score'] >= th)
              / max(1, len(true_absent)))
    print(f"\n  匹配器θ误差模型(阈值{th}):")
    print(f"    p_miss  (存在对应但报缺失) = {p_miss:.3f} ({len(true_exists)}条中)")
    print(f"    p_halluc(不存在但报匹配)   = {p_hall:.3f} ({len(true_absent)}条中)")

    # ── 边界案例展示 ──
    print(f"\n  分数区间[{th-0.05:.2f},{th+0.05:.2f})的边界案例:")
    for s in scored:
        if th - 0.05 <= s['final_score'] < th + 0.05:
            print(f"    [{s['label'][:8]}] {s['final_score']:.3f} 「{s['text'][:18]}」↔「{(s['match_text'] or '?')[:18]}」")

    out = {
        'config': {'current_threshold': EMB_TH_CURRENT, 'optimal_threshold': best_th,
                   'n_items': len(scored), 'gain': best_gain},
        'theta': {'p_miss': round(p_miss, 4), 'p_halluc': round(p_hall, 4),
                  'n_true_exists': len(true_exists), 'n_true_absent': len(true_absent)},
        'threshold_sweep': [{'th': t} for t in [0.50, 0.52, 0.54, 0.56, 0.58, 0.60,
                                                0.62, 0.64, 0.66, 0.68, 0.70, 0.72, 0.75]],
        'scored_items': [{k: v for k, v in s.items() if k != 'anchor'} for s in scored],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n  输出: {OUT}")


if __name__ == '__main__':
    main()
