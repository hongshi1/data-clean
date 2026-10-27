#!/usr/bin/env python3
"""
M8: 裁决后重标注 + 实验重跑
=============================
用M7双LLM裁决的标签替代Tier1候选代理标签:
  real_bug         → η=1 (真不一致)
  benign_variation → η=0 (合理差异,元素确实不在图里但合法)
  compiler_bug     → η=0 (元素在图里,匹配失败)
  extraction_error → 排除该对
  uncertain        → 排除该元素(待人工)

重跑: 锚遮蔽判决实验(M4逻辑) + 融合实验(M6逻辑), 用修正后的η
输出: data/gjb_438c/anchor_sc2/relabeled_experiment.json
用法: python3 tools/m8_relabel_rerun.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import compile_usecase_table, save_emb_cache
from m4_decoder import as_diagram_view, element_verdicts
from m6_fusion_experiment import ocr_element_verdicts

ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
VLM_PATH = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"
OCR_PATH = BASE / "data/gjb_438c/anchor_sc2/ocr_extractions.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
T1_PATH = BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies_v2.json"
ADJ_PATH = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/relabeled_experiment.json"

EXCLUDE_PAIRS = {'2_084'}


def build_element_adj():
    """三轮最终裁决task_id → (pair, element_id) 映射"""
    t1 = json.loads(T1_PATH.read_text())
    adj_data = json.loads(ADJ_PATH.read_text())
    final_labels = adj_data.get('final_labels', adj_data)
    elem_adj = {}  # (pair, element) -> label
    n_mapped = 0
    for tid, a in final_labels.items():
        label = a['label'] if isinstance(a, dict) else a
        pk, di = tid.rsplit('_', 1)
        v = t1.get(pk, {})
        discs = v.get('discrepancies', [])
        try:
            di = int(di)
        except ValueError:
            continue
        if di >= len(discs):
            continue
        d = discs[di]
        elem = None
        if d['dtype'] == 'STEP_MISSING' and d.get('table_side'):
            sid = d['table_side'].get('id', '')
            m = sid.removeprefix('s')
            if m.isdigit():
                elem = f"step:{m}"
        elif d['dtype'] == 'EXC_MISSING' and d.get('table_side'):
            eid = d['table_side'].get('eid', '')
            if eid:
                elem = f"exc:{eid}"
        elif d['dtype'] == 'ACTOR_MISSING' and d.get('table_side'):
            elem = ('actor_text', d['table_side'].get('text', ''))
        if elem:
            elem_adj[(pk, elem if isinstance(elem, str) else elem)] = label
            n_mapped += 1
    return elem_adj, n_mapped


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


def ece(rows, key, n_bins=10):
    bins = defaultdict(list)
    for r in rows:
        b = min(int(r[key] * n_bins), n_bins - 1)
        bins[b].append(r['eta'])
    total = sum(len(v) for v in bins.values())
    if not total:
        return None
    return sum(len(v)/total * abs(sum(v)/len(v) - (b+0.5)/n_bins)
               for b, v in bins.items())


def main():
    anchors = json.loads(ANCHOR_PATH.read_text())
    vlm = json.loads(VLM_PATH.read_text())
    ocr = json.loads(OCR_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())
    realigned = json.loads(REALIGN_PATH.read_text())

    elem_adj, n_mapped = build_element_adj()
    print(f"{'='*64}")
    print(f"M8: 裁决后重标注重跑 (元素级裁决映射{n_mapped}条)")
    print(f"{'='*64}")

    anchor_idx = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            key = (doc_name, s['embed_index'].split(':')[0])
            text_n = sum(1 for n in s['nodes'] if n['text'])
            if key not in anchor_idx or text_n > anchor_idx[key][0]:
                anchor_idx[key] = (text_n, s)
    anchor_idx = {k: v[1] for k, v in anchor_idx.items()}

    records = []
    n_excl_elem = n_excl_pair = 0
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

        for eid in t1:
            if eid not in t2v or eid not in t2o:
                continue
            eta_raw = 0 if t1[eid]['found'] else 1
            if eta_raw == 1:
                # 裁决修正
                label = elem_adj.get((pk, eid))
                if label is None and eid.startswith('actor:'):
                    # actor按文本匹配裁决
                    idx = int(eid.split(':')[1])
                    if idx < len(X_T['actors']):
                        label = elem_adj.get((pk, ('actor_text', X_T['actors'][idx])))
                if label == 'real_bug':
                    eta = 1
                elif label in ('benign_variation', 'compiler_bug'):
                    eta = 0
                elif label == 'extraction_error':
                    n_excl_elem += 1
                    continue
                else:  # uncertain / None(未裁决)
                    n_excl_elem += 1
                    continue
            else:
                eta = 0  # Tier1找到 → 一致(无分歧无裁决)
            records.append({
                'pair': pk, 'doc': m['doc'], 'element': eid,
                'kind': eid.split(':')[0], 'eta': eta,
                'd_vlm': 0 if t2v[eid]['found'] else 1,
                'd_ocr': 0 if t2o[eid]['found'] else 1,
                'd_or': 0 if (t2v[eid]['found'] or t2o[eid]['found']) else 1,
            })

    n = len(records)
    n_pos = sum(r['eta'] for r in records)
    print(f"\n  重标注后: {n}元素 (排除{n_excl_elem}条uncertain/未裁决), "
          f"真实不一致{n_pos}条 → π={n_pos/n:.3f}")
    print("  (重标注前: π≈0.60 — Tier1候选全当正例)")

    # 文档分块
    docs = sorted({r['doc'] for r in records})
    train_docs = set(docs[::2])
    train = [r for r in records if r['doc'] in train_docs]
    test = [r for r in records if r['doc'] not in train_docs]
    print(f"  训练{len(train_docs)}文档({len(train)}条) / 测试{len(docs)-len(train_docs)}文档({len(test)}条)")

    if n_pos == 0:
        print("  ⚠ 无正例 — 检查裁决结果")
        return

    # θ估计(训练集)
    def est_theta(rows, dkey):
        neg = [r for r in rows if r['eta'] == 0]
        pos = [r for r in rows if r['eta'] == 1]
        if not neg or not pos:
            return None
        return {
            'p_miss': sum(r[dkey] for r in neg) / len(neg),
            'p_halluc': sum(1 - r[dkey] for r in pos) / len(pos),
            'pi': len(pos) / len(rows),
        }

    th_vlm = est_theta(train, 'd_vlm')
    th_ocr = est_theta(train, 'd_ocr')
    th_or = est_theta(train, 'd_or')
    print(f"\n  θ_vlm: {th_vlm}")
    print(f"  θ_ocr: {th_ocr}")
    print(f"  θ_or:  {th_or}")

    if not (th_vlm and th_ocr and th_or):
        print("  ⚠ 训练集正/负例不足, 无法译码")
        return

    # 译码
    def decode(D, pi, p_m, p_h):
        if D == 1:
            return pi * (1 - p_m) / (pi * (1 - p_m) + (1 - pi) * p_m)
        return pi * p_h / (pi * p_h + (1 - pi) * (1 - p_m))

    def logodds_decode(d_v, d_o):
        def llr(D, th):
            if D == 1:
                return (1 - th['p_miss']) / max(th['p_miss'], 1e-9)
            return th['p_halluc'] / max(1 - th['p_miss'], 1e-9)
        pi = th_vlm['pi']
        po = pi / max(1 - pi, 1e-9) * llr(d_v, th_vlm) * llr(d_o, th_ocr)
        return po / (1 + po)

    for r in test:
        r['q_vlm'] = decode(r['d_vlm'], th_vlm['pi'], th_vlm['p_miss'], th_vlm['p_halluc'])
        r['q_ocr'] = decode(r['d_ocr'], th_ocr['pi'], th_ocr['p_miss'], th_ocr['p_halluc'])
        r['q_or'] = decode(r['d_or'], th_or['pi'], th_or['p_miss'], th_or['p_halluc'])
        r['q_ci'] = logodds_decode(r['d_vlm'], r['d_ocr'])
        r['q_vote'] = float(1 if (r['d_vlm'] or r['d_ocr']) else 0)

    labels = [r['eta'] for r in test]
    print(f"\n{'='*64}")
    print(f"重标注后判决实验 (测试{len(test)}条, 裁决η标签)")
    print(f"{'='*64}")
    print(f"  测试集正例: {sum(labels)}条")
    print(f"  {'配置':22s} {'AUROC':>7s} {'ECE':>7s}")
    results_e = {}
    for key, label in [('q_vlm', '单VLM'), ('q_ocr', '单OCR'),
                       ('q_or', 'OR融合校准'), ('q_ci', '条件独立因子化'),
                       ('q_vote', '朴素投票')]:
        a = auroc([r[key] for r in test], labels)
        e = ece(test, key)
        results_e[key] = {'auroc': a, 'ece': e}
        print(f"  {label:22s} {a:7.3f} {e:7.3f}")

    # 分类型π和θ(训练集)
    theta_kind = {}
    for kind in ('step', 'exc', 'actor'):
        tr = [r for r in train if r['kind'] == kind]
        if tr:
            theta_kind[kind] = {
                'pi': sum(r['eta'] for r in tr) / len(tr),
                'n': len(tr), 'n_pos': sum(r['eta'] for r in tr),
            }
    print(f"\n  分类型π: {theta_kind}")

    OUT_PATH.write_text(json.dumps({
        'config': {'train_docs': sorted(train_docs),
                   'n_records': n, 'n_pos': n_pos, 'pi': n_pos / n,
                   'n_excluded': n_excl_elem},
        'theta': {'vlm': th_vlm, 'ocr': th_ocr, 'or': th_or},
        'element_level': results_e,
        'theta_kind': theta_kind,
        'records': records,
    }, ensure_ascii=False, indent=1))
    save_emb_cache()
    print(f"\n  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
