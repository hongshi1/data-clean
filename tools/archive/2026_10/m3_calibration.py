#!/usr/bin/env python3
"""
M3: 感知通道校准器 (ACDD核心 — Tier 2前置)
=============================================
元素级误差测量: VLM提取(M2) vs 锚点金标准(M0) → 误差模型θ

测量维度(元素宇宙):
  exst: 节点存在性 — 漏检率(VLM missed) / 幻觉率(VLM extra)
  lab : 文本保真   — 逐字一致率(编辑距离)
  dir : 边方向     — 方向翻转率(在双侧匹配的节点对上)
  edge: 边存在性   — 漏边率 / 多余边率

输出θ = {
  per-aspect误差率 + Wilson 95% CI,
  按文档分层(经验贝叶斯收缩用),
  按难度特征φ分箱(节点数/文本长度/边密度)
} → data/gjb_438c/anchor_sc2/calibration.json

用法: python3 tools/m3_calibration.py
"""
import json
import math
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
VLM_PATH = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/calibration.json"

import sys
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import text_match_score, MATCH_TH  # 复用匹配器


def wilson_ci(success: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson置信区间"""
    if n == 0:
        return (0.0, 1.0)
    p = success / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, center-half), min(1, center+half))


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a):
        cur = [i+1]
        for j, cb in enumerate(b):
            cur.append(min(prev[j+1]+1, cur[j]+1, prev[j] + (ca != cb)))
        prev = cur
    return prev[-1]


def load_pairs():
    anchors = json.loads(ANCHOR_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())
    vlm = json.loads(VLM_PATH.read_text()) if VLM_PATH.exists() else {}

    # 锚点索引(多页取文本最多)
    anchor_idx = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            key = (doc_name, s['embed_index'].split(':')[0])
            text_n = sum(1 for n in s['nodes'] if n['text'])
            if key not in anchor_idx or text_n > anchor_idx[key][0]:
                anchor_idx[key] = (text_n, s)
    anchor_idx = {k: v[1] for k, v in anchor_idx.items()}

    # 重对齐映射(M2.5)优先
    REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
    realigned = json.loads(REALIGN_PATH.read_text()) if REALIGN_PATH.exists() else {}

    pairs = []
    for pk in sorted(mapping.keys()):
        m = mapping[pk]
        v = vlm.get(pk)
        if not v or 'error' in v:
            continue
        embed = m.get('visio_embed', '')
        ra = realigned.get(pk, {})
        if ra.get('status') in ('realigned', 'same'):
            embed = ra.get('new_embed', '').split(':')[0]
        elif ra.get('status') == 'unanchored':
            continue  # 无锚点对不参与校准
        anchor = anchor_idx.get((m['doc'], embed))
        if anchor:
            pairs.append((pk, m, anchor, v))
    return pairs


def calibrate_pair(anchor: dict, vlm: dict) -> dict:
    """单对元素级误差测量"""
    # 语义节点: 有文本, 排除start/end
    a_nodes = [n for n in anchor['nodes']
               if n['text'].strip() and n['type'] not in ('start', 'end')]
    v_nodes = [n for n in vlm.get('nodes', []) if n.get('text', '').strip()]

    # ── exst: 节点匹配(锚点↔VLM, 贪心最高分) ──
    pairs_list = []
    for an in a_nodes:
        for vn in v_nodes:
            sc = text_match_score(an['text'], vn['text'])
            if sc >= MATCH_TH:
                pairs_list.append((sc, an, vn))
    pairs_list.sort(key=lambda x: -x[0])
    matched_a, matched_v = {}, {}
    for sc, an, vn in pairs_list:
        if an['id'] not in matched_a and vn['id'] not in matched_v:
            matched_a[an['id']] = (vn, sc)
            matched_v[vn['id']] = (an, sc)

    n_missed = len(a_nodes) - len(matched_a)      # VLM漏检
    n_halluc = len(v_nodes) - len(matched_v)      # VLM幻觉/严重改写

    # ── lab: 文本保真(匹配对上的编辑距离) ──
    edit_dists = []
    verbatim = 0
    for aid, (vn, sc) in matched_a.items():
        an_text = next(n['text'] for n in a_nodes if n['id'] == aid)
        d = levenshtein(an_text, vn['text'])
        edit_dists.append(d)
        if d == 0:
            verbatim += 1

    # ── dir/edge: 统一到锚点ID空间比较 ──
    a_edges = anchor['edges']
    v_edges = vlm.get('edges', [])

    # id映射
    a2v = {aid: vn['id'] for aid, (vn, sc) in matched_a.items()}
    v2a = {vid: an['id'] for vid, (an, sc) in matched_v.items()}

    # 锚点边(两端都在匹配集中) — 保持锚点ID空间
    a_edges_mapped = []
    for e in a_edges:
        if e['src'] in a2v and e['dst'] in a2v:
            a_edges_mapped.append((e['src'], e['dst'], e))
    # VLM边 → 映射到锚点ID空间
    v_edges_mapped = []
    for e in v_edges:
        if e.get('src') in v2a and e.get('dst') in v2a:
            v_edges_mapped.append((v2a[e['src']], v2a[e['dst']], e))

    v_edge_set = {(e[0], e[1]) for e in v_edges_mapped}
    a_edge_set = {(e[0], e[1]) for e in a_edges_mapped}

    # 边漏检(锚点有,VLM无) / 边幻觉(VLM有,锚点无) / 方向翻转
    edge_missed = sum(1 for ae in a_edges_mapped if (ae[0], ae[1]) not in v_edge_set)
    edge_extra = sum(1 for ve in v_edges_mapped if (ve[0], ve[1]) not in a_edge_set)
    # 方向翻转: (u,v)锚点有且(u,v)VLM无但(v,u)VLM有
    dir_flipped = sum(1 for ae in a_edges_mapped
                      if (ae[0], ae[1]) not in v_edge_set
                      and (ae[1], ae[0]) in v_edge_set)

    return {
        'n_anchor_nodes': len(a_nodes),
        'n_vlm_nodes': len(v_nodes),
        'n_matched': len(matched_a),
        'node_missed': n_missed,
        'node_halluc': n_halluc,
        'verbatim': verbatim,
        'edit_dists': edit_dists,
        'n_anchor_edges_comparable': len(a_edges_mapped),
        'n_vlm_edges_comparable': len(v_edges_mapped),
        'edge_missed': edge_missed,
        'edge_extra': edge_extra,
        'dir_flipped': dir_flipped,
    }


def main():
    pairs = load_pairs()
    print(f"{'='*64}")
    print(f"M3: 感知通道校准 (VLM vs 锚点, {len(pairs)}对)")
    print(f"{'='*64}")

    if len(pairs) < 10:
        print("  ⚠ 样本不足(M2未完成?), 仅输出当前结果")

    # 全局累计
    agg = defaultdict(int)
    per_doc = defaultdict(lambda: defaultdict(int))
    per_pair = {}

    for pk, m, anchor, vlm in pairs:
        r = calibrate_pair(anchor, vlm)
        r['doc'] = m['doc']
        per_pair[pk] = r
        for k in ('n_anchor_nodes', 'n_vlm_nodes', 'n_matched', 'node_missed',
                  'node_halluc', 'verbatim', 'n_anchor_edges_comparable',
                  'n_vlm_edges_comparable', 'edge_missed', 'edge_extra', 'dir_flipped'):
            agg[k] += r[k]
            per_doc[m['doc']][k] += r[k]

    # ── θ计算(全局) ──
    def rates(a):
        n_an, n_vn = a['n_anchor_nodes'], a['n_vlm_nodes']
        return {
            'node_recall': (a['n_matched'] / n_an, n_an),          # 节点召回
            'node_precision': (a['n_matched'] / n_vn, n_vn),       # 节点精确率
            'node_miss_rate': (a['node_missed'] / n_an, n_an),     # 漏检率(ε-exst)
            'node_halluc_rate': (a['node_halluc'] / n_vn, n_vn),   # 幻觉率
            'text_verbatim_rate': (a['verbatim'] / a['n_matched'], a['n_matched']),
            'edge_recall': ((a['n_anchor_edges_comparable'] - a['edge_missed'] + a['dir_flipped'])
                            / max(1, a['n_anchor_edges_comparable']),
                            a['n_anchor_edges_comparable']),
            'edge_miss_rate': (a['edge_missed'] / a['n_anchor_edges_comparable'],
                               a['n_anchor_edges_comparable']),
            'edge_extra_rate': (a['edge_extra'] / a['n_vlm_edges_comparable'],
                                a['n_vlm_edges_comparable']),
            'dir_flip_rate': (a['dir_flipped'] / a['n_anchor_edges_comparable'],
                              a['n_anchor_edges_comparable']),
        }

    theta_global = {}
    print("\n  全局θ (Wilson 95% CI):")
    for name, (val, n) in rates(agg).items():
        lo, hi = wilson_ci(int(val * n), n)
        theta_global[name] = {'value': round(val, 4), 'n': n,
                              'ci95': [round(lo, 4), round(hi, 4)]}
        print(f"    {name:22s}: {val:.3f}  [{lo:.3f}, {hi:.3f}]  (n={n})")

    # ── 按文档分层(经验贝叶斯收缩的输入) ──
    theta_docs = {}
    print("\n  按文档分层:")
    for doc, a in sorted(per_doc.items()):
        if a['n_anchor_nodes'] < 5:
            continue
        mr = a['node_missed'] / a['n_anchor_nodes']
        hr = a['node_halluc'] / max(1, a['n_vlm_nodes'])
        vr = a['verbatim'] / max(1, a['n_matched'])
        theta_docs[doc] = {
            'n_anchor_nodes': a['n_anchor_nodes'],
            'node_miss_rate': round(mr, 3),
            'node_halluc_rate': round(hr, 3),
            'text_verbatim_rate': round(vr, 3),
        }
        print(f"    {doc[:26]:28s}: miss={mr:.2f} halluc={hr:.2f} verbatim={vr:.2f} (n={a['n_anchor_nodes']})")

    # ── 难度特征φ分箱(节点数) ──
    phi_bins = defaultdict(lambda: defaultdict(int))
    for pk, r in per_pair.items():
        size = 'small(≤5)' if r['n_anchor_nodes'] <= 5 else \
               ('medium(6-10)' if r['n_anchor_nodes'] <= 10 else 'large(>10)')
        for k in ('n_anchor_nodes', 'n_vlm_nodes', 'n_matched', 'node_missed',
                  'node_halluc', 'verbatim', 'n_anchor_edges_comparable',
                  'n_vlm_edges_comparable', 'edge_missed', 'edge_extra', 'dir_flipped'):
            phi_bins[size][k] += r[k]
    theta_phi = {}
    print("\n  按难度φ分箱(锚点节点数):")
    for size, a in sorted(phi_bins.items()):
        if a['n_anchor_nodes'] == 0:
            continue
        mr = a['node_missed'] / a['n_anchor_nodes']
        vr = a['verbatim'] / max(1, a['n_matched'])
        er = a['edge_missed'] / max(1, a['n_anchor_edges_comparable'])
        theta_phi[size] = {'node_miss_rate': round(mr, 3),
                           'text_verbatim_rate': round(vr, 3),
                           'edge_miss_rate': round(er, 3),
                           'n_pairs': sum(1 for r in per_pair.values()
                                          if (r['n_anchor_nodes'] <= 5) == (size == 'small(≤5)'))}
        print(f"    {size:12s}: node_miss={mr:.2f} verbatim={vr:.2f} edge_miss={er:.2f}")

    out = {
        'n_pairs': len(pairs),
        'theta_global': theta_global,
        'theta_by_doc': theta_docs,
        'theta_by_phi': theta_phi,
        'per_pair': {pk: {k: v for k, v in r.items() if k != 'edit_dists'}
                     for pk, r in per_pair.items()},
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n  输出: {OUT_PATH}")

    # 命题1可行性检查: π > p ?
    print("\n  ── 命题1可行性预检 (分离条件 π > p) ──")
    p_eff = agg['node_missed'] / max(1, agg['n_anchor_nodes'])
    print(f"  节点漏检率 p_miss = {p_eff:.3f}")
    print(f"  → 若元素级不一致率 π > {p_eff:.3f}, 单分歧才可译码(否则依赖簇签名/融合)")
    print("  → Tier1实测drift率: 待人工裁决(裁决包M1.5)")


if __name__ == "__main__":
    main()
