r"""Table-Pali行级后期交互评测(两场景, 论文数字复现工具).

场景1 caption级: docT5query假想查询(前800字生成, 1532对)
场景2 深行: LLM构造查询(仅引用>800字位置的行内容, 111对)
  —— 深行场景暴露dense单向量的截断盲区(84%表格超512被截).

方法: B1 dense单向量 | TP行级 | ROUTE(max-zscore路由)

用法: python tools/eval_table_late.py
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
DOC_QUERIES = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
PARAM_V2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"
DEEP_QUERIES = BASE / "data/gjb_438c/data_assets/deep_row_queries.json"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


def metrics_from_scores(scores: dict, targets: dict, ids: list) -> dict:
    r1 = r5 = rr = 0.0
    for qid, mix in scores.items():
        order = np.argsort(-mix)
        rank = {ids[i]: k + 1 for k, i in enumerate(order)}
        first = min((rank[t] for t in targets[qid] if t in rank),
                    default=len(ids) + 1)
        r1 += first <= 1
        r5 += first <= 5
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(scores), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "MRR@10": round(rr / n, 4)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=10)
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    tables = [c for c in chunks if c.get("type") == "table"]
    with open(DENSE_CACHE, "rb") as f:
        dense: dict[str, list[float]] = pickle.load(f)

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    from eval_profile_matrix import run_profile_matrix  # noqa: PLC0415

    hq = json.loads(DOC_QUERIES.read_text(encoding="utf-8"))
    v2 = json.loads(PARAM_V2.read_text(encoding="utf-8"))
    deep_qs = json.loads(DEEP_QUERIES.read_text(encoding="utf-8"))
    cid2type = {c["chunk_id"]: c.get("type") for c in chunks}
    cid2doc = {c["chunk_id"]: c.get("doc", "")[:2] for c in chunks}
    dq_pairs = []
    for cid, rec in hq.items():
        if cid2type.get(cid) != "table":
            continue
        qs = rec if isinstance(rec, list) else rec.get("queries", [])
        dq_pairs.extend((q, cid) for q in qs[:1])
    for cid, rec in v2.items():
        if cid2type.get(cid) != "table":
            continue
        qs = rec if isinstance(rec, list) else [rec.get("query", "")]
        dq_pairs.extend((q, cid) for q in qs if q)
    deep_pairs = [(o["query"], o["cid"]) for o in deep_qs]

    fold_map = {}
    for i, d in enumerate(range(1, 17)):
        fold_map[f"{d:02d}"] = i % 4

    # URE语料(单元与标题)
    ure = json.loads(
        (BASE / "data/gjb_438c/data_assets/evalsets/gjb_ure_v2.json")
        .read_text(encoding="utf-8"))
    corpus = ure["corpus"]

    scenes = {
        "caption": dq_pairs,
        "deep_v1": deep_pairs,
    }
    ds2_queries = [q for q in ure["queries"]
                   if q["scene"] == "table_deep_v2"]
    scenes["deep_v2"] = [(q["query"], q["expected"][0]) for q in ds2_queries]

    final = run_profile_matrix(bge, corpus, scenes, fold_map,
                               dense, cid2doc)
    out = BASE / "data/gjb_438c/data_assets/table_late_eval.json"
    out.write_text(json.dumps({
        "protocol": ("4-fold; 画像矩阵: TP-raw=原始行+精确IDF(词面友好); "
                     "TP-cc=标题拼接+精确IDF(标题级最优); TP-cf=标题拼接+"
                     "池相对模糊IDF@0.9(语义深行最优); R(d,x)=max-z路由"),
        "results": final}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
