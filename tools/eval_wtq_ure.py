r"""WTQ-URE外部效度pilot: 单元检索 vs 单向量dense(公开数据).

数据: WTQ真实用户问题(英文)→表检索(2100候选, 全corpus无fold隔离).
方法: O1单元(行单元+IDF+k=1 MaxSim) | B1 dense(title+行join[:512]).
诚实声明: bge-large-zh对英文非最优(中文模型), 数字用于机制级
外部效度检验(单元拆分是否在公开数据复现增益), 非SOTA声明.

用法: python tools/eval_wtq_ure.py [--n-queries 2000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

WTQ_URE = BASE / "data/gjb_438c/data_assets/evalsets/wtq_ure.json"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-queries", type=int, default=2000)
    args = ap.parse_args()

    ds = json.loads(WTQ_URE.read_text(encoding="utf-8"))
    corpus = ds["corpus"]
    queries = ds["queries"]
    ids = [c["chunk_id"] for c in corpus]
    id2idx = {cid: i for i, cid in enumerate(ids)}
    print(f"WTQ-URE: {len(corpus)}表/{sum(c['n_units'] for c in corpus)}单元, "
          f"{len(queries)}查询(评测{min(args.n_queries, len(queries))})")

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    # ── 单元矩阵(拼接+段边界) + IDF ──
    unit_texts: list[str] = []
    seg_start, seg_end = [], []
    df: dict[str, int] = {}
    for c in corpus:
        texts = ([c["title"]] if c["title"] else []) + c["units"]
        if not texts:
            texts = ["(empty)"]
        for t in set(texts):
            df[t] = df.get(t, 0) + 1
    for c in corpus:
        texts = ([c["title"]] if c["title"] else []) + c["units"]
        if not texts:
            texts = ["(empty)"]
        seg_start.append(len(unit_texts))
        unit_texts.extend(texts)
        seg_end.append(len(unit_texts))
    N = len(corpus)
    idf_arr = np.asarray([np.log(1 + N / df[t]) for t in unit_texts],
                         dtype=np.float32)
    vecs = bge.embed(unit_texts)
    U = np.stack([np.asarray(vecs[t], dtype=np.float32)
                  for t in unit_texts if vecs.get(t)]).T  # (1024, n_units)
    # 注意: embed的dict键序与unit_texts对齐失败风险——按key查找重排
    U = np.stack([np.asarray(vecs.get(t, [0.0] * 1024), dtype=np.float32)
                  for t in unit_texts]).T
    U = U / np.maximum(np.linalg.norm(U, axis=0, keepdims=True), 1e-8)
    idf_col = idf_arr[None, :]  # (1, n_units)
    starts = np.asarray(seg_start)
    ends = np.asarray(seg_end)

    # ── dense基线矩阵 ──
    dense_texts = [(c["title"] + " " + " ".join(c["units"]))[:512]
                   for c in corpus]
    dense_texts = [t.strip() or "(empty)" for t in dense_texts]
    dvecs = bge.embed(dense_texts)
    D = np.stack([np.asarray(dvecs.get(t, [0.0] * 1024), dtype=np.float32)
                  for t in dense_texts])
    D = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-8)

    # ── 查询 ──
    rng = np.random.default_rng(42)
    sel = rng.permutation(len(queries))[:args.n_queries]
    sel_queries = [queries[i] for i in sel]
    q_texts = [q["query"] for q in sel_queries]
    qvecs = bge.embed([QUERY_PREFIX + q[:200] for q in q_texts])
    Q = np.stack([np.asarray(qvecs.get(QUERY_PREFIX + q[:200],
                                       [0.0] * 1024), dtype=np.float32)
                  for q in q_texts])
    Q = Q / np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-8)
    print(f"编码完成: {U.shape[1]}单元 + {D.shape[0]}dense + {Q.shape[0]}查询")

    # ── 打分(全矩阵一次) ──
    sims_u = (Q @ U) * idf_col  # (n_q, n_units) IDF加权
    sims_d = Q @ D.T              # (n_q, n_tables)

    def seg_max(mat: np.ndarray) -> np.ndarray:
        """段最大: 每表的单元最大分. (n_q, n_units)→(n_q, n_tables)."""
        out = np.full((mat.shape[0], len(starts)), -1e9, dtype=np.float32)
        for i in range(len(starts)):
            out[:, i] = mat[:, starts[i]:ends[i]].max(axis=1)
        return out

    s_unit = seg_max(sims_u)

    # ── 指标 ──
    def metrics(S: np.ndarray) -> dict:
        r1 = r5 = r10 = rr = 0.0
        for qi, q in enumerate(sel_queries):
            golds = [id2idx[t] for t in q["expected"] if t in id2idx]
            if not golds:
                continue
            order = np.argsort(-S[qi])
            rank = {int(i): k + 1 for k, i in enumerate(order)}
            first = min(rank[g] for g in golds)
            r1 += first <= 1
            r5 += first <= 5
            r10 += first <= 10
            rr += 1.0 / first if first <= 10 else 0.0
        n = max(len(sel_queries), 1)
        return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
                "R@10": round(r10 / n, 4), "MRR@10": round(rr / n, 4)}

    m_dense = metrics(sims_d)
    m_unit = metrics(s_unit)
    print(f"\n{'=' * 56}")
    print(f"WTQ外部效度pilot ({args.n_queries}查询×{len(corpus)}候选)")
    print(f"{'=' * 56}")
    print(f"{'方法':<16s} R@1    R@5    R@10   MRR@10")
    print(f"  {'B1 dense':<14s} {m_dense['R@1']:.3f}  {m_dense['R@5']:.3f}  "
          f"{m_dense['R@10']:.3f}  {m_dense['MRR@10']:.3f}")
    print(f"  {'O1 unit(行+IDF)':<14s} {m_unit['R@1']:.3f}  {m_unit['R@5']:.3f}  "
          f"{m_unit['R@10']:.3f}  {m_unit['MRR@10']:.3f}")
    print("\n声明: bge-large-zh为中文模型, 英文查询/文档非其最优域;"
          "本pilot检验的是单元拆分机制的跨数据集一致性.")

    out = BASE / "data/gjb_438c/data_assets/evalsets/wtq_pilot_eval.json"
    out.write_text(json.dumps({
        "protocol": (f"WTQ-URE, {args.n_queries}采样查询(seed42)×"
                     f"{len(corpus)}全候选; O1=行单元+IDF+k=1 MaxSim; "
                     "B1=title+行join[:512]单向量; bge-large-zh(英文非最优)"),
        "results": {"B1_dense": m_dense, "O1_unit": m_unit},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结果 → {out}")


if __name__ == "__main__":
    main()
