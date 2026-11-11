#!/usr/bin/env python3
"""P1: 作用域绑定学习器 — 用200对GLM标注训练, 替换4-gram启发式.

对应文档: 83号. 三步:
  1. 特征工程: BGE上下文向量 + 管线特征(scope_hint/章节距离/参数类型)
  2. 训练: 逻辑回归(3分类: same_scope/different_scope/extraction_error)
  3. 评估: 5折CV + 与启发式基线对比

用法: python tools/train_scope_binder.py [--skip-bge]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import torch  # noqa: E402,F401

from algorithms.context_linking.pair_scorers import (  # noqa: E402
    score_lexical_jaccard, score_template_mask, normalize_context,
)

ANNOT = BASE / "data/gjb_438c/atom_candidates_v1/glm_annotations_v1.jsonl"
CAND = BASE / "data/gjb_438c/atom_candidates_v1/candidates.jsonl"
OUT = BASE / "data/gjb_438c/atom_candidates_v1/scope_binder_v1.json"

# 标签映射: 4类→3类(needs_review合并到多数类)
LABEL_MAP = {
    "true_conflict": "same_scope",
    "needs_review": "same_scope",  # 模糊对倾向冲突
    "legit_variance": "different_scope",
    "extraction_error": "extraction_error",
}
LABELS = ["same_scope", "different_scope", "extraction_error"]


def load_data():
    """加载标注对 + 从源文件恢复原子上下文."""
    ann_rows = [json.loads(line) for line in ANNOT.open(encoding="utf-8")]
    ann_rows = [r for r in ann_rows if r.get("label")]

    # 三个数据源(按pair_id或字段匹配)
    # 1. pairs_to_label.jsonl(人工48对+GLM标注, 有完整左右原子)
    ptl = {r["pair_id"]: r for r in (
        json.loads(line) for line in
        (BASE / "data/gjb_438c/atom_candidates_v1/pairs_to_label.jsonl")
        .open(encoding="utf-8"))}

    # 2. candidates.jsonl(弱候选, 有左右原子)
    cand = [json.loads(line) for line in CAND.open(encoding="utf-8")]
    # 构建键: doc|param|left.value|right.value
    cand_by_key = {}
    for c in cand:
        key = (f"{c['doc_id']}|{c['param']}|"
               f"{c['left']['value']}|{c['right']['value']}")
        cand_by_key[key] = c

    # 3. findings.jsonl(覆盖差异, 结构不同)
    findings = [json.loads(line) for line in
                (BASE / "data/gjb_438c/coverage_findings_v1/findings.jsonl")
                .open(encoding="utf-8")]

    pairs = []
    for r in ann_rows:
        left_ctx = right_ctx = ""
        scope_l = scope_r = ""
        sec_l = sec_r = ""

        # 尝试pair_id匹配(人工48对)
        if r["pair_id"] in ptl:
            p = ptl[r["pair_id"]]
            left_ctx = p["left"]["context"]
            right_ctx = p["right"]["context"]
            scope_l = p["left"]["scope_hint"]
            scope_r = p["right"]["scope_hint"]
            sec_l = p["left"]["section"]
            sec_r = p["right"]["section"]
        else:
            # 尝试candidates键匹配
            # 需要从annotation中恢复left/right value
            # annotation行没有直接的left_value/right_value
            # 用decision+doc+param查找
            matches = [c for c in cand
                       if c["doc_id"] == r["doc_id"]
                       and c["param"] == r["param"]]
            if matches:
                c = matches[0]  # 取第一个匹配
                left_ctx = c["left"]["context"]
                right_ctx = c["right"]["context"]
                scope_l = c["left"]["scope_hint"]
                scope_r = c["right"]["scope_hint"]
                sec_l = c["left"]["section"]
                sec_r = c["right"]["section"]

        # 来自findings的(用findings字段构造上下文)
        if not left_ctx and r["source"] == "findings":
            # 从findings中查找匹配的行
            fm = [f for f in findings
                  if f["doc_id"] == r["doc_id"]
                  and f["type"] in ("value_conflict", "value_subset_gap")]
            if fm:
                # 取第一个匹配的行
                f = fm[0]
                left_ctx = (f"{f['scope']} {f['field']}: {f['value_a']} "
                            f"(章节{f['section_a']})")
                right_ctx = (f"{f['scope']} {f['field']}: {f['value_b']} "
                             f"(章节{f['section_b']})")
                scope_l = f["scope"]
                scope_r = f["scope"]
                sec_l = f["section_a"]
                sec_r = f["section_b"]

        # 兜底: 用doc+param构造简单上下文
        if not left_ctx:
            left_ctx = f"doc{r['doc_id']} {r['param']} left"
            right_ctx = f"doc{r['doc_id']} {r['param']} right"

        pairs.append({
            "pair_id": r["pair_id"],
            "label": LABEL_MAP[r["label"]],
            "doc_id": r["doc_id"],
            "param": r["param"],
            "left_ctx": left_ctx,
            "right_ctx": right_ctx,
            "scope_l": scope_l,
            "scope_r": scope_r,
            "section_l": sec_l,
            "section_r": sec_r,
        })
    return pairs


def compute_features(pairs, use_bge=True):
    """计算特征矩阵: BGE上下文向量 + 管线启发式特征."""
    n = len(pairs)
    # BGE向量
    if use_bge:
        from algorithms.common.bge_local import BgeLocal
        bge = BgeLocal()
        if bge.ensure() not in ("cuda", "gpu", "cpu"):
            raise RuntimeError(f"BGE不可用: {bge.last_error}")
        ctxs = sorted({p["left_ctx"][:200] for p in pairs} |
                      {p["right_ctx"][:200] for p in pairs})
        emb = {}
        for i in range(0, len(ctxs), 8):
            emb.update(bge.embed(ctxs[i:i + 8]))
        dim = 1024
        bge_feats = np.zeros((n, dim * 2), dtype=np.float32)
        for i, p in enumerate(pairs):
            vl = np.array(emb.get(p["left_ctx"][:200], [0.0] * dim))
            vr = np.array(emb.get(p["right_ctx"][:200], [0.0] * dim))
            bge_feats[i, :dim] = vl
            bge_feats[i, dim:] = vr
    else:
        bge_feats = np.zeros((n, 0), dtype=np.float32)
        dim = 0

    # 启发式特征(现有管线的信号)
    heur = np.zeros((n, 8), dtype=np.float32)
    for i, p in enumerate(pairs):
        # 1. scope_hint是否一致
        heur[i, 0] = 1.0 if p["scope_l"] and p["scope_l"] == p["scope_r"] else 0.0
        # 2. 词面Jaccard
        heur[i, 1] = score_lexical_jaccard(p["left_ctx"], p["right_ctx"])
        # 3. 模板相似度(数字掩码)
        heur[i, 2] = score_template_mask(p["left_ctx"], p["right_ctx"])
        # 4. 章节是否相同
        heur[i, 3] = 1.0 if p["section_l"] == p["section_r"] else 0.0
        # 5. 章节层级距离
        try:
            sa = [int(x) for x in p["section_l"].split(".") if x.isdigit()]
            sb = [int(x) for x in p["section_r"].split(".") if x.isdigit()]
            heur[i, 4] = abs(len(sa) - len(sb)) + sum(
                abs(a - b) for a, b in zip(sa, sb)) / max(len(sa), len(sb), 1)
        except (ValueError, ZeroDivisionError):
            heur[i, 4] = 10.0
        # 6. 参数类型(one-hot简化: 数值型=1)
        numeric_params = {"clock_frequency", "resolution", "response_time",
                          "throughput", "memory_size", "timeout",
                          "recovery_time", "jitter", "error_rate"}
        heur[i, 5] = 1.0 if p["param"] in numeric_params else 0.0
        # 7. 上下文长度比
        ll, lr = len(p["left_ctx"]), len(p["right_ctx"])
        heur[i, 6] = min(ll, lr) / max(ll, lr) if max(ll, lr) > 0 else 0.0
        # 8. 上下文是否含表格标记
        heur[i, 7] = 1.0 if ("<table" in p["left_ctx"] or
                             "<table" in p["right_ctx"]) else 0.0

    X = np.hstack([bge_feats, heur]) if use_bge else heur
    y = np.array([LABELS.index(p["label"]) for p in pairs])
    return X, y, dim


def train_and_eval(X, y, n_folds=5):
    """5折交叉验证训练+评估."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, f1_score
    from sklearn.model_selection import StratifiedKFold

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    all_true, all_pred = [], []
    for train_idx, test_idx in skf.split(X, y):
        clf = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
        clf.fit(X[train_idx], y[train_idx])
        pred = clf.predict(X[test_idx])
        all_true.extend(y[test_idx])
        all_pred.extend(pred)

    # 分类报告
    report = classification_report(all_true, all_pred,
                                   target_names=LABELS, output_dict=True)
    macro_f1 = f1_score(all_true, all_pred, average="macro")
    acc = np.mean(np.array(all_true) == np.array(all_pred))

    # 启发式基线: 仅用scope_hint(特征0)
    heur_pred = (X[:, -8] > 0.5).astype(int)  # same_scope if hint match
    heur_f1 = f1_score(y, heur_pred, average="macro") if len(set(y)) > 1 else 0.0

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": {k: {kk: round(vv, 3) for kk, vv in v.items()
                          if isinstance(vv, (int, float))}
                      for k, v in report.items() if k in LABELS},
        "heuristic_f1": round(heur_f1, 4),
        "n_train": len(y),
        "feature_dim": X.shape[1],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-bge", action="store_true")
    args = ap.parse_args()

    print("== 加载数据 ==")
    pairs = load_data()
    label_dist = Counter(p["label"] for p in pairs)
    print(f"  {len(pairs)}对, 标签: {dict(label_dist)}")

    print("\n== 特征工程 ==")
    t0 = time.perf_counter()
    X, y, dim = compute_features(pairs, use_bge=not args.skip_bge)
    print(f"  特征维度: {X.shape[1]} (BGE {dim * 2} + 启发式 8)"
          f"  耗时{time.perf_counter() - t0:.1f}s")

    print("\n== 5折交叉验证 ==")
    results = train_and_eval(X, y)
    print(f"  accuracy: {results['accuracy']}")
    print(f"  macro F1: {results['macro_f1']}")
    print(f"  启发式基线F1: {results['heuristic_f1']}")
    for cls, m in results["per_class"].items():
        print(f"    {cls:20s} P={m.get('precision', 0):.3f} "
              f"R={m.get('recall', 0):.3f} F1={m.get('f1-score', 0):.3f}")

    OUT.write_text(json.dumps({
        "n_pairs": len(pairs), "label_dist": dict(label_dist),
        "results": results,
        "feature_info": {"bge_dim": dim, "heuristic_features": 8},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
