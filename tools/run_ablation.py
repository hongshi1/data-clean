#!/usr/bin/env python3
"""P2: 消融实验 — 每个组件对最终检测的贡献分解.

对应文档: 83号. 在200对GLM标注上, 逐个移除组件测macro F1.

组件(按管线顺序):
  full    = BGE(1024d×2) + 词面Jaccard + 模板掩码 + 章节距离 + 参数类型 + 上下文比 + 表格标记
  w/o BGE = 仅8个启发式特征
  w/o 词面 = BGE + 模板+章节+类型+长度+表格 (去Jaccard)
  w/o 模板 = BGE + 词面+章节+类型+长度+表格 (去模板掩码)
  w/o 章节 = BGE + 词面+模板+类型+长度+表格 (去章节距离)
  w/o 全部启发式 = 仅BGE(1024d×2)
  基线    = 仅scope_hint一致(1个特征)

用法: python tools/run_ablation.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import torch  # noqa: E402,F401

from tools.train_scope_binder import (  # noqa: E402
    LABELS, compute_features, load_data,
)

OUT = BASE / "data/gjb_438c/atom_candidates_v1/ablation_v1.json"


def eval_subset(X, y, feature_mask, label=""):
    """用特征子集训练+5折CV, 返回macro F1."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from sklearn.model_selection import StratifiedKFold

    X_sub = X[:, feature_mask]
    if X_sub.shape[1] == 0:
        return 0.0
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    preds, trues = [], []
    for tr, te in skf.split(X_sub, y):
        clf = LogisticRegression(max_iter=500, C=1.0, random_state=42)
        clf.fit(X_sub[tr], y[tr])
        preds.extend(clf.predict(X_sub[te]))
        trues.extend(y[te])
    return round(f1_score(trues, preds, average="macro"), 4)


def main() -> int:
    print("== 加载数据 ==")
    pairs = load_data()
    print(f"  {len(pairs)}对")

    print("\n== 特征工程(BGE+8启发式) ==")
    t0 = time.perf_counter()
    X, y, dim = compute_features(pairs, use_bge=True)
    n_heur = 8
    print(f"  维度: {X.shape[1]} (BGE {dim * 2} + 启发式 {n_heur})"
          f"  耗时{time.perf_counter() - t0:.1f}s")

    bge_slice = slice(0, dim * 2)
    heur_start = X.shape[1] - n_heur
    # 启发式特征索引: 0=scope_hint, 1=jaccard, 2=template,
    # 3=same_section, 4=section_dist, 5=param_type, 6=len_ratio, 7=table

    # 消融配置
    configs = {
        "full": list(range(X.shape[1])),
        "w/o BGE": list(range(heur_start, X.shape[1])),
        "w/o 词面Jaccard": [i for i in range(X.shape[1])
                           if i != heur_start + 1],
        "w/o 模板掩码": [i for i in range(X.shape[1])
                        if i != heur_start + 2],
        "w/o 章节距离": [i for i in range(X.shape[1])
                       if i != heur_start + 4],
        "w/o 全部启发式": list(range(dim * 2)),
        "基线(仅scope_hint)": [heur_start],
    }

    print("\n== 消融结果 ==")
    print(f"{'配置':<24} {'macro F1':>8} {'ΔF1':>8}")
    print("-" * 44)
    results = {}
    baseline_f1 = None
    for name, mask in configs.items():
        f1 = eval_subset(X, y, mask, name)
        if baseline_f1 is None:
            baseline_f1 = f1
        delta = f1 - baseline_f1
        results[name] = {"macro_f1": f1, "delta": round(delta, 4)}
        print(f"  {name:<22} {f1:>8.4f} {delta:>+8.4f}")

    OUT.write_text(json.dumps({
        "n_pairs": len(pairs), "results": results,
        "feature_dims": {"bge": dim * 2, "heuristic": n_heur},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
