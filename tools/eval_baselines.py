r"""对比方法复现: BM25(文档级/单元级) + dense + 单元检索, 统一协议.

新增能力:
  ① BM25基线(此前从未跑过我们的评测!): 中文字符二元组+英文词,
     k1=1.5 b=0.75, 零新依赖
  ② BM25-unit(行级BM25取max)——单元检索的结构对照(同构不同相似度)
  ③ 行级命中精度RowHit@1(FeTaQA行级gold): 检索到gold表后,
     top单元是否命中gold行——"单元检索定位行而非仅定位表"的可测证据

数据集: GJB-URE-v1(图/表caption/表深行) | WTQ-URE | FeTaQA-URE
用法: python tools/eval_baselines.py [--wtq-queries 2000]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

GJB_URE = BASE / "data/gjb_438c/data_assets/evalsets/gjb_ure_v1.json"
WTQ_URE = BASE / "data/gjb_438c/data_assets/evalsets/wtq_ure.json"
FETAQA_URE = BASE / "data/gjb_438c/data_assets/evalsets/fetaqa_ure.json"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："

K1, B = 1.5, 0.75
_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """中文二元组 + 拉丁词(小写). 无分词依赖."""
    text = text or ""
    out: list[str] = []
    # CJK bigrams(连续CJK段)
    for seg in _CJK.findall("".join(_CJK.findall(text)) and text) or []:
        pass
    cjk_segs = re.findall(r"[\u4e00-\u9fff]+", text)
    for seg in cjk_segs:
        out.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    out.extend(_LATIN.findall(text.lower()))
    return out


class BM25:
    """倒排索引BM25. docs: token列表的列表."""

    def __init__(self, docs: list[list[str]]) -> None:
        self.n = len(docs)
        self.dl = [len(d) for d in docs]
        self.avgdl = sum(self.dl) / max(self.n, 1)
        self.tf: list[dict[str, int]] = []
        df: dict[str, int] = defaultdict(int)
        for d in docs:
            tfd: dict[str, int] = defaultdict(int)
            for t in d:
                tfd[t] += 1
            self.tf.append(dict(tfd))
            for t in tfd:
                df[t] += 1
        self.idf = {t: math.log(1 + (self.n - df_t + 0.5) / (df_t + 0.5))
                    for t, df_t in df.items()}

    def score(self, q_tokens: list[str], doc_idx: int) -> float:
        tfd = self.tf[doc_idx]
        dl = self.dl[doc_idx]
        s = 0.0
        for t in set(q_tokens):
            f = tfd.get(t)
            if not f:
                continue
            idf = self.idf.get(t, 0.0)
            s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / self.avgdl))
        return s


def metrics_rows(scores: list[np.ndarray], golds: list[set],
                 n_cands: int) -> dict:
    """scores[i]=查询i的候选分数向量; golds[i]=期望下标集合."""
    r1 = r5 = r10 = rr = 0.0
    for sc, g in zip(scores, golds):
        if not g:
            continue  # 空gold: 计为miss(计入n, 不加命中)
        order = np.argsort(-sc)
        rank = {int(i): k + 1 for k, i in enumerate(order)}
        first = min(rank[gi] for gi in g)
        r1 += first <= 1
        r5 += first <= 5
        r10 += first <= 10
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(scores), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "R@10": round(r10 / n, 4), "MRR@10": round(rr / n, 4)}


def row_hit(units_sims: np.ndarray, gold_rows: set) -> float:
    """行级命中: gold表的单元相似度向量中argmax是否∈gold行集合."""
    if not gold_rows or len(units_sims) == 0:
        return 0.0
    return 1.0 if int(np.argmax(units_sims)) in gold_rows else 0.0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--wtq-queries", type=int, default=2000)
    ap.add_argument("--fetaqa-queries", type=int, default=2000)
    args = ap.parse_args()

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    # ═══ GJB-URE: BM25 on 三场景(4-fold协议与锁定评测一致) ═══
    gjb = json.loads(GJB_URE.read_text(encoding="utf-8"))
    corpus = gjb["corpus"]
    queries = gjb["queries"]
    ctype = {"image": "image", "table_caption": "table", "table_deep": "table"}
    # caption场景评测协议=docT5查询(锁定table_late口径): split=train的table_caption
    eval_scenes = [
        ("image", [q for q in queries if q["scene"] == "image"]),
        ("table_deep", [q for q in queries
                        if q["scene"] == "table_deep" and q["split"] == "eval"]),
        ("table_caption", [q for q in queries
                           if q["scene"] == "table_caption"]),
    ]
    print(f"{'=' * 64}")
    print("GJB-URE: BM25基线(文档级/单元级), 4-fold")
    print(f"{'=' * 64}")
    print(f"{'场景':<14s} {'方法':<12s} R@1    R@5    MRR@10")
    gjb_results: dict[str, dict] = {}
    for scene, scene_qs in eval_scenes:
        t = ctype[scene]
        pool_by_fold: dict[int, list] = defaultdict(list)
        for c in corpus:
            if c["type"] == t:
                pool_by_fold[c["fold"]].append(c)
        # 查询向量(全局一次)
        qmap = {}
        for q in scene_qs:
            v = bge.embed([QUERY_PREFIX + q["query"][:200]]).get(
                QUERY_PREFIX + q["query"][:200])
            if v:
                qmap[q["query"]] = np.asarray(v, dtype=np.float32)
        # 每fold: BM25-doc + BM25-unit
        scores_doc: list[np.ndarray] = []
        scores_unit: list[np.ndarray] = []
        scores_dense: list[np.ndarray] = []
        scores_route: list[np.ndarray] = []
        scores_route4: list[np.ndarray] = []
        golds: list[set] = []
        for fold in range(4):
            pool = pool_by_fold[fold]
            if not pool:
                continue
            ids = [c["chunk_id"] for c in pool]
            idx = {cid: i for i, cid in enumerate(ids)}
            docs = [tokenize(c["title"] + " " + " ".join(c["units"]))
                    for c in pool]
            bm25_doc = BM25(docs)
            unit_lists = [[tokenize(u) for u in
                           ([c["title"]] + c["units"]) if u]
                          for c in pool]
            unit_owner = [i for i, ul in enumerate(unit_lists)
                          for _ in ul]
            bm25_unit = BM25([u for ul in unit_lists for u in ul])
            # dense + unit向量(BGE, 无CMSC——与公开集口径一致)
            dense_texts = [(c["title"] + " " + " ".join(c["units"]))[:512]
                           for c in pool]
            dvecs = bge.embed(dense_texts)
            D = np.stack([np.asarray(dvecs.get(t, [0.0] * 1024),
                                     dtype=np.float32) for t in dense_texts])
            D = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-8)
            raw_units = [[u for u in ([c["title"]] + c["units"]) if u]
                         for c in pool]
            unit_texts = [u for ru in raw_units for u in ru]
            uvecs = bge.embed(unit_texts)
            U = np.stack([np.asarray(uvecs.get(u, [0.0] * 1024),
                                     dtype=np.float32) for u in unit_texts]).T
            U = U / np.maximum(np.linalg.norm(U, axis=0, keepdims=True), 1e-8)
            df: dict[str, int] = {}
            for ru in raw_units:
                for u in set(ru):
                    df[u] = df.get(u, 0) + 1
            idf_u = np.asarray([np.log(1 + len(pool) / max(df.get(u, 1), 1))
                                for u in unit_texts], dtype=np.float32)
            seg_start = np.cumsum([0] + [len(ru) for ru in raw_units])
            for q in scene_qs:
                if q["fold"] != fold:
                    continue
                qt = tokenize(q["query"])
                g = {idx[t] for t in q["expected"] if t in idx}
                sd = np.asarray([bm25_doc.score(qt, i)
                                 for i in range(len(pool))])
                su = np.full(len(pool), -1e9)
                us = np.asarray([bm25_unit.score(qt, i)
                                 for i in range(len(unit_owner))])
                for ui, owner in enumerate(unit_owner):
                    if us[ui] > su[owner]:
                        su[owner] = us[ui]
                qv = qmap.get(q["query"])
                if qv is None:
                    continue
                qn = qv / np.linalg.norm(qv)
                s_dense = D @ qn
                sims_u = (U.T @ qn) * idf_u
                s_unit = np.asarray([
                    sims_u[seg_start[i]:seg_start[i + 1]].max()
                    if seg_start[i] < seg_start[i + 1] else -1e9
                    for i in range(len(pool))])
                # ROUTE3: max(z(bm25), 0.8·z(dense), z(unit))
                def _zs(x):
                    sdv = x.std()
                    return (x - x.mean()) / (sdv if sdv > 1e-8 else 1.0)
                s_route = np.maximum(np.maximum(
                    _zs(sd), 0.8 * _zs(s_dense)), _zs(s_unit))
                s_route4 = np.maximum(np.maximum(np.maximum(
                    _zs(sd), _zs(su)), 0.8 * _zs(s_dense)), _zs(s_unit))
                scores_route4.append(s_route4)
                scores_doc.append(sd)
                scores_unit.append(su)
                scores_dense.append(s_dense)
                scores_route.append(s_route)
                golds.append(g)
        for name, sc_list in (("BM25-doc", scores_doc), ("BM25-unit", scores_unit),
                              ("B1-dense", scores_dense), ("ROUTE3", scores_route),
                              ("ROUTE4", scores_route4)):
            m = metrics_rows(sc_list, golds, len(pool))
            gjb_results[f"{scene}|{name}"] = m
            print(f"  {scene:<12s} {name:<10s} {m['R@1']:.3f}  {m['R@5']:.3f}  "
                  f"{m['MRR@10']:.3f} (n={len(sc_list)})")

    # ═══ 公开数据集: BM25 + dense + O1单元 + RowHit ═══
    def run_public(path: Path, label: str, n_queries: int,
                   row_gold: bool) -> dict:
        ds = json.loads(path.read_text(encoding="utf-8"))
        corpus_p = ds["corpus"]
        queries_p = ds["queries"]
        rng = np.random.default_rng(42)
        sel = rng.permutation(len(queries_p))[:n_queries]
        sel_qs = [queries_p[i] for i in sel]
        ids = [c["chunk_id"] for c in corpus_p]
        idx = {cid: i for i, cid in enumerate(ids)}
        print(f"\n{'=' * 64}")
        print(f"{label}: {len(corpus_p)}候选×{len(sel_qs)}查询"
              f"{' (RowHit@1)' if row_gold else ''}")
        print(f"{'=' * 64}")
        print(f"{'方法':<12s} R@1    R@5    R@10   MRR@10"
              + ("   RowHit@1" if row_gold else ""))

        results: dict[str, dict] = {}
        golds = [{idx[t] for t in q["expected"] if t in idx} for q in sel_qs]

        # BM25-doc / BM25-unit
        docs = [tokenize(c["title"] + " " + " ".join(c["units"]))
                for c in corpus_p]
        bm25_doc = BM25(docs)
        raw_units = [[u for u in ([c["title"]] + c["units"]) if u]
                     for c in corpus_p]
        unit_lists = [[tokenize(u) for u in ru] for ru in raw_units]
        unit_owner = [i for i, ul in enumerate(unit_lists) for _ in ul]
        bm25_unit = BM25([u for ul in unit_lists for u in ul])
        seg_start = np.cumsum([0] + [len(ul) for ul in unit_lists])

        # BGE: dense + 单元(供O1与RowHit)
        unit_texts = [u for ru in raw_units for u in ru]
        vecs = bge.embed(unit_texts)
        U = np.stack([np.asarray(vecs.get(u, [0.0] * 1024), dtype=np.float32)
                      for u in unit_texts]).T
        U = U / np.maximum(np.linalg.norm(U, axis=0, keepdims=True), 1e-8)
        df: dict[str, int] = {}
        for ru in raw_units:
            for u in set(ru):
                df[u] = df.get(u, 0) + 1
        idf_u = np.asarray([np.log(1 + len(corpus_p) /
                                   max(df.get(u, 1), 1))
                            for u in unit_texts], dtype=np.float32)
        dense_texts = [(c["title"] + " " + " ".join(c["units"]))[:512]
                       for c in corpus_p]
        dvecs = bge.embed(dense_texts)
        D = np.stack([np.asarray(dvecs.get(t, [0.0] * 1024), dtype=np.float32)
                      for t in dense_texts])
        D = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-8)
        q_texts = [q["query"] for q in sel_qs]
        qvecs = bge.embed([QUERY_PREFIX + q[:200] for q in q_texts])
        Q = np.stack([np.asarray(qvecs.get(QUERY_PREFIX + q[:200],
                                           [0.0] * 1024), dtype=np.float32)
                      for q in q_texts])
        Q = Q / np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-8)

        sims_u = (Q @ U) * idf_u[None, :]
        sims_d = Q @ D.T

        def seg_max(mat: np.ndarray) -> np.ndarray:
            out = np.full((mat.shape[0], len(unit_lists)), -1e9, dtype=np.float32)
            for i in range(len(unit_lists)):
                out[:, i] = mat[:, seg_start[i]:seg_start[i + 1]].max(axis=1)
            return out

        s_unit = seg_max(sims_u)

        sc_doc, sc_unit_b, sc_dense, sc_unit_d = [], [], [], []
        sc_route, sc_route4 = [], []
        rh_unit, rh_bm25, n_rh = 0.0, 0.0, 0
        for qi, q in enumerate(sel_qs):
            qt = tokenize(q["query"])
            sd = np.asarray([bm25_doc.score(qt, i) for i in range(len(ids))])
            us = np.asarray([bm25_unit.score(qt, i)
                             for i in range(len(unit_owner))])
            su = np.full(len(ids), -1e9)
            for ui, owner in enumerate(unit_owner):
                if us[ui] > su[owner]:
                    su[owner] = us[ui]
            sc_doc.append(sd)
            sc_unit_b.append(su)
            sc_dense.append(sims_d[qi])
            sc_unit_d.append(s_unit[qi])
            # ROUTE3: max(z(bm25), 0.8·z(dense), z(unit))
            def _zs(x):
                sdv = x.std()
                return (x - x.mean()) / (sdv if sdv > 1e-8 else 1.0)
            sc_route.append(np.maximum(np.maximum(
                _zs(sd), 0.8 * _zs(sims_d[qi])), _zs(s_unit[qi])))
            sc_route4.append(np.maximum(np.maximum(np.maximum(
                _zs(sd), _zs(su)), 0.8 * _zs(sims_d[qi])), _zs(s_unit[qi])))
            # RowHit: gold表的单元相似度argmax是否∈gold行
            # (段=[title]+units, gold_rows为units下标→排除title段对齐;
            #  审计修复: 原实现含+1偏移, 数字被title巧合污染)
            if row_gold and q.get("gold_rows"):
                g0 = next(iter(golds[qi]), None)
                if g0 is not None:
                    rh_unit += row_hit(
                        sims_u[qi][seg_start[g0] + 1:seg_start[g0 + 1]],
                        set(q["gold_rows"]))
                    rh_bm25 += row_hit(
                        us[seg_start[g0] + 1:seg_start[g0 + 1]],
                        set(q["gold_rows"]))
                    n_rh += 1
        for name, sc_list in (("BM25-doc", sc_doc), ("BM25-unit", sc_unit_b),
                              ("B1-dense", sc_dense), ("O1-unit", sc_unit_d),
                              ("ROUTE3", sc_route), ("ROUTE4", sc_route4)):
            m = metrics_rows(sc_list, golds, len(ids))
            if row_gold:
                hit = rh_unit / max(n_rh, 1) if name == "O1-unit" else (
                    rh_bm25 / max(n_rh, 1) if name == "BM25-unit" else None)
                if hit is not None:
                    m["RowHit@1"] = round(hit, 4)
            results[name] = m
            extra = f"  {m['RowHit@1']:.3f}" if "RowHit@1" in m else ""
            print(f"  {name:<10s} {m['R@1']:.3f}  {m['R@5']:.3f}  "
                  f"{m['R@10']:.3f}  {m['MRR@10']:.3f}{extra}"
                  f" (n={len(sc_list)}, rh_n={n_rh})")
        return results

    wtq_results = run_public(WTQ_URE, "WTQ-URE", args.wtq_queries, False)
    fetaqa_results = run_public(FETAQA_URE, "FeTaQA-URE",
                                args.fetaqa_queries, True)

    out = BASE / "data/gjb_438c/data_assets/evalsets/baselines_eval.json"
    out.write_text(json.dumps({
        "protocol": ("BM25: 中文字符二元组+拉丁词, k1=1.5 b=0.75; "
                     "BM25-unit=单元级BM25取max(与O1结构同构); "
                     "GJB按4-fold, 公开集全候选; RowHit@1=gold表top单元命中gold行"),
        "gjb": gjb_results, "wtq": wtq_results, "fetaqa": fetaqa_results,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
