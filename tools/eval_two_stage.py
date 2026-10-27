r"""两阶段检索评测: 单元召回×cross-encoder重排(对比矩阵, R@1/R@5/MRR).

方法矩阵:
  B1  dense            单向量基线(无重排)
  B2  dense→rerank(F)  dense top-20→cross-encoder全文重排(标准两阶段)
  O1  unit             单元检索(本方法, stage-1)
  O2a unit→rerank(F)   单元top-20→全文重排(隔离"通道"因素)
  O2b unit→rerank(S)   单元top-20→单元片段重排(本方法完整版)

单元片段重排(S)的动机: cross-encoder窗口512 token同样截断
(longest_first从尾部切)——深行内容在char 800+对全文重排也不可见.
S把stage-1命中的top-3单元(sim·idf)前置为证据片段,
cross-encoder才真正"看到"深行内容: stage-1选证据, stage-2验证.

表格的单元召回源=ROUTE(max(0.8·z(dense), z(TP))); 图=VA(k=1+IDF).

场景: 图evalset_v3(1007q); 表caption级(1532q)+深行(111q).
指标: R@1/R@5/MRR@10 + stage-1 R@20(重排上限).

用法: python tools/eval_two_stage.py [--topk 20]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
EVALSET = BASE / "data/gjb_438c/data_assets/evalset_v3.json"
DOC_QUERIES = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
PARAM_V2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"
DEEP_QUERIES = BASE / "data/gjb_438c/data_assets/deep_row_queries.json"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："

FULL_TEXT_LEN = 1500   # 全文重排的passage截断(字符)
N_SNIPPET = 3          # 单元片段重排: 前置top-3命中单元


def metrics_from_scores(scores: dict, targets: dict, ids: list) -> dict:
    r1 = r5 = r10 = rr = 0.0
    for qid, mix in scores.items():
        order = np.argsort(-mix)
        rank = {ids[i]: k + 1 for k, i in enumerate(order)}
        first = min((rank[t] for t in targets[qid] if t in rank),
                    default=len(ids) + 1)
        r1 += first <= 1
        r5 += first <= 5
        r10 += first <= 10
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(scores), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "R@10": round(r10 / n, 4), "MRR@10": round(rr / n, 4)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=10)
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    images = [c for c in chunks if c.get("type") == "image"]
    tables = [c for c in chunks if c.get("type") == "table"]
    with open(DENSE_CACHE, "rb") as f:
        dense: dict[str, list[float]] = pickle.load(f)
    eval_data = json.loads(EVALSET.read_text(encoding="utf-8"))

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()
    import algorithms.blackboard.reranker as _rrmod
    _rrmod._BATCH_GPU = 32  # 8GB GPU: 2.3GB模型+32对512token安全
    from algorithms.blackboard.reranker import BgeReranker
    rr_model = BgeReranker()
    if rr_model.ensure() != "gpu":
        print(f"重排器: {rr_model.mode} ({rr_model.last_error})")

    from algorithms.unit_attention import (  # noqa: PLC0415
        CmscProjector,
        image_units_with_feats,
        table_units_with_feats,
    )
    proj = CmscProjector()
    has_cmsc = proj.ensure()
    from algorithms.unit_retrieval import route_combine  # noqa: PLC0415

    # ── 单元索引(矩阵+idf, 与既有口径一致) ──
    def build(units_with_feats):
        texts_all = list({t for ts, _ in units_with_feats.values()
                          for t in ts if t})
        vecs = bge.embed(texts_all)
        tv = {t: np.asarray(v, dtype=np.float32)
              for t, v in vecs.items() if v}
        df: dict[str, int] = {}
        for ts, _ in units_with_feats.values():
            for t in set(ts):
                if t:
                    df[t] = df.get(t, 0) + 1
        N = len(units_with_feats)
        mats, idfs, cmsc = {}, {}, {}
        for cid, (ts, _) in units_with_feats.items():
            keep = [i for i, t in enumerate(ts) if t in tv]
            if not keep:
                continue
            mat = np.stack([tv[ts[i]] for i in keep])
            mats[cid] = mat / np.maximum(
                np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
            idfs[cid] = np.asarray(
                [np.log(1 + N / df[ts[i]]) for i in keep], dtype=np.float32)
            if has_cmsc:
                pm = proj.project_units(mats[cid])
                if pm is not None:
                    cmsc[cid] = pm
        return mats, idfs, cmsc

    img_units = image_units_with_feats(chunks)
    img_mats, img_idfs, img_cmsc = build(img_units)
    tab_units = table_units_with_feats(chunks)
    tab_mats, tab_idfs, tab_cmsc = build(tab_units)
    # 单元文本表(供片段重排)
    img_texts = {cid: ts for cid, (ts, _) in img_units.items()}
    tab_texts = {cid: ts for cid, (ts, _) in tab_units.items()}

    # ── 全文passage(标准两阶段的通道) ──
    vlm_path = BASE / "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"
    vlm = json.loads(vlm_path.read_text(encoding="utf-8"))
    import re  # noqa: PLC0415
    by_doc_fig = {}
    for c in images:
        by_doc_fig[(c.get("doc", ""), c.get("image_path", ""))] = c
    img_full: dict[str, str] = {}
    for a in vlm.get("analyses", []):
        m = re.search(r"(fig_\d+\.png)$", a.get("image_path", ""))
        if not m:
            continue
        c = by_doc_fig.get((a.get("doc", ""), "images/" + m.group(1)))
        if not c:
            continue
        ana = a.get("analysis", {})
        cap = a.get("caption", [])
        cap_s = " ".join(cap) if isinstance(cap, list) else str(cap)
        parts = [cap_s] + ana.get("key_elements", [])[:12]
        if ana.get("summary"):
            parts.append(str(ana["summary"]))
        img_full[c["chunk_id"]] = " ".join(p for p in parts if p)[:FULL_TEXT_LEN]

    tab_full: dict[str, str] = {}
    for cid, ts in tab_texts.items():
        tab_full[cid] = " ".join(ts)[:FULL_TEXT_LEN]

    def snippet(cid: str, sims: np.ndarray, idfs: np.ndarray,
                texts: list[str]) -> str:
        """单元片段passage: caption(首单元) + top-N命中单元前置."""
        order = np.argsort(-(sims * idfs))[:N_SNIPPET]
        parts = [texts[0]] if texts else []
        parts.extend(texts[i] for i in order if i > 0)
        return " ".join(p for p in parts if p)[:FULL_TEXT_LEN]

    fold_map = {}
    for i, d in enumerate(range(1, 17)):
        fold_map[f"{d:02d}"] = i % 4

    def query_vec(q: str) -> np.ndarray | None:
        v = bge.embed([QUERY_PREFIX + q[:200]]).get(QUERY_PREFIX + q[:200])
        if not v:
            return None
        qn = np.asarray(v, dtype=np.float32)
        return qn / np.linalg.norm(qn)

    def run_scene(name: str, qs: list[dict], pool_chunks: list[dict],
                  mats, idfs, texts_map, full_map, use_route: bool,
                  cmsc_map: dict | None = None, cmsc_fuse: float = 0.0):
        """一个场景×一个fold: 5方法对比. qs含query/targets."""
        ids = [c["chunk_id"] for c in pool_chunks]
        if not qs or not ids:
            return {}
        mat = np.stack([np.asarray(dense[cid], dtype=np.float32) for cid in ids])
        matn = mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
        targets = {q["query"]: set(q["targets"]) for q in qs}

        res = defaultdict(dict)
        for q in qs:
            qn = query_vec(q["query"])
            if qn is None:
                continue
            # stage-1分数
            s_dense = matn @ qn
            s_unit = np.full(len(ids), -1.0)
            unit_sims = {}
            qc = None
            if cmsc_fuse > 0 and cmsc_map and has_cmsc:
                qc = proj.project_query(qn)
            for i, cid in enumerate(ids):
                m = mats.get(cid)
                if m is None:
                    continue
                sims = m @ qn
                if qc is not None and cid in cmsc_map:
                    sims = sims + cmsc_fuse * (cmsc_map[cid] @ qc)
                unit_sims[i] = (sims, idfs[cid])
                s_unit[i] = float((sims * idfs[cid]).max())
            if use_route:
                s_unit = route_combine(s_dense, s_unit)
            k = args.topk
            top_dense = list(np.argsort(-s_dense)[:k])
            top_unit = list(np.argsort(-s_unit)[:k])

            # stage-1指标(R@20=重排上限)
            res["B1_dense"][q["query"]] = s_dense
            res["O1_unit"][q["query"]] = s_unit
            # 重排
            for label, top, ptype in (
                    ("B2_dense_rrF", top_dense, "full"),
                    ("O2a_unit_rrF", top_unit, "full"),
                    ("O2b_unit_rrS", top_unit, "snippet")):
                pairs = []
                for i in top:
                    cid = ids[i]
                    if ptype == "full":
                        pairs.append((q["query"], full_map.get(cid, "")))
                    else:
                        sims, idf = unit_sims.get(i, (np.zeros(1), np.zeros(1)))
                        pairs.append((q["query"], snippet(
                            cid, sims, idf, texts_map.get(cid, []))))
                scores = rr_model.score(pairs)
                mix = np.full(len(ids), -1e9)
                for i, sc in zip(top, scores):
                    mix[i] = sc
                res[label][q["query"]] = mix
        return {k: metrics_from_scores(v, targets, ids)
                for k, v in res.items()}

    # ═══ 图 ═══
    print(f"\n{'=' * 64}")
    print(f"图检索两阶段 (top-{args.topk}重排, evalset_v3 4-fold)")
    print(f"{'=' * 64}")
    img_all = defaultdict(list)
    for fold in range(4):
        test_qs = []
        for q in eval_data:
            if q["fold"] != fold:
                continue
            tgts = [t for t in q["expected"]["chunk_ids"]]
            if tgts:
                test_qs.append({"query": q["query"], "targets": tgts})
        test_qs = test_qs[:250]
        pool = [c for c in images
                if fold_map[c["doc"][:2]] == fold and c["chunk_id"] in dense]
        r = run_scene(f"img{fold}", test_qs, pool, img_mats, img_idfs,
                      img_texts, img_full, use_route=False,
                      cmsc_map=img_cmsc, cmsc_fuse=0.3)
        for k, m in r.items():
            img_all[k].append(m)
        if r:
            print(f"  fold{fold}: " + " ".join(
                f"{k}={m['R@1']:.3f}" for k, m in list(r.items())[:2]), flush=True)

    print(f"\n{'方法':<14s} R@1    R@5    R@10   MRR")
    for k in ("B1_dense", "B2_dense_rrF", "O1_unit", "O2a_unit_rrF",
              "O2b_unit_rrS"):
        agg = img_all[k]
        if agg:
            avg = {m: round(np.mean([r[m] for r in agg]), 4) for m in agg[0]}
            print(f"  {k:<12s} {avg['R@1']:.3f}  {avg['R@5']:.3f}  "
                  f"{avg['R@10']:.3f}  {avg['MRR@10']:.3f}")

    # ═══ 表 ═══
    print(f"\n{'=' * 64}")
    print(f"表格两阶段 (top-{args.topk}重排, ROUTE召回源)")
    print(f"{'=' * 64}")
    hq = json.loads(DOC_QUERIES.read_text(encoding="utf-8"))
    v2 = json.loads(PARAM_V2.read_text(encoding="utf-8"))
    deep_qs = json.loads(DEEP_QUERIES.read_text(encoding="utf-8"))
    cid2type = {c["chunk_id"]: c.get("type") for c in chunks}
    cid2doc = {c["chunk_id"]: c.get("doc", "")[:2] for c in chunks}
    dq = defaultdict(set)
    for cid, rec in hq.items():
        if cid2type.get(cid) != "table":
            continue
        qs = rec if isinstance(rec, list) else rec.get("queries", [])
        for q in qs[:1]:
            dq[q].add(cid)
    for cid, rec in v2.items():
        if cid2type.get(cid) != "table":
            continue
        qs = rec if isinstance(rec, list) else [rec.get("query", "")]
        for q in qs:
            if q:
                dq[q].add(cid)
    deep = defaultdict(set)
    for o in deep_qs:
        deep[o["query"]].add(o["cid"])

    tab_all = defaultdict(list)
    for scene, qmap in (("caption", dq), ("deep", deep)):
        for fold in range(4):
            test_qs = [{"query": q, "targets": list(tgts)}
                       for q, tgts in qmap.items()
                       if any(fold_map.get(cid2doc.get(c, "")) == fold
                              for c in tgts)]
            pool = [t for t in tables
                    if fold_map[t["doc"][:2]] == fold
                    and t["chunk_id"] in dense]
            r = run_scene(f"{scene}{fold}", test_qs, pool, tab_mats, tab_idfs,
                          tab_texts, tab_full, use_route=True)
            for k, m in r.items():
                tab_all[(scene, k)].append(m)

    for scene in ("caption", "deep"):
        print(f"\n[{scene}]")
        print(f"{'方法':<14s} R@1    R@5    R@10   MRR")
        for k in ("B1_dense", "B2_dense_rrF", "O1_unit", "O2a_unit_rrF",
                  "O2b_unit_rrS"):
            agg = tab_all[(scene, k)]
            if agg:
                avg = {m: round(np.mean([r[m] for r in agg]), 4)
                       for m in agg[0]}
                print(f"  {k:<12s} {avg['R@1']:.3f}  {avg['R@5']:.3f}  "
                      f"{avg['R@10']:.3f}  {avg['MRR@10']:.3f} (n={len(agg)})")

    out = BASE / "data/gjb_438c/data_assets/two_stage_eval.json"
    final = {"image": {}, "table_caption": {}, "table_deep": {}}
    for k in ("B1_dense", "B2_dense_rrF", "O1_unit", "O2a_unit_rrF",
              "O2b_unit_rrS"):
        if img_all[k]:
            final["image"][k] = {m: round(np.mean([r[m] for r in img_all[k]]), 4)
                                 for m in img_all[k][0]}
    for scene, key in (("caption", "table_caption"), ("deep", "table_deep")):
        for k in ("B1_dense", "B2_dense_rrF", "O1_unit", "O2a_unit_rrF",
                  "O2b_unit_rrS"):
            agg = tab_all[(scene, k)]
            if agg:
                final[key][k] = {m: round(np.mean([r[m] for r in agg]), 4)
                                 for m in agg[0]}
    out.write_text(json.dumps({
        "protocol": (f"4-fold; rerank top-{args.topk} BGE-Reranker-v2-m3; "
                     "S=caption+top3命中单元, F=全文[:1500]; 图单元含CMSC融合l=0.3"),
        "results": final}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
