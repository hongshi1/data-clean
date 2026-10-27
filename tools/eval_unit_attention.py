r"""单元子注意力聚合(UAA)评测: 冻结表示+学习聚合 vs 固定聚合.

冻结表示源: BGE(语义) + CMSC投影头(跨模态对齐) + 结构特征(13维)
学习:       注意力MLP(~500参数)聚合子单元信号

协议(与eval_recall_v3一致, 文档级分离):
  每fold: 其余3折的(查询, 候选池)训练, 本折测试. BGE/CMSC全程冻结.

对照:
  FIXED: k=1+IDF MaxSim(现行默认, 零训练)
  UAA:   子注意力聚合(学习, 含CMSC特征)

场景: 图evalset_v3(1007q) 4-fold;
      表docT5 caption级(1532对)训练+测试, 深行(111对)仅测试.

用法: python tools/eval_unit_attention.py [--epochs 15] [--no-cmsc]
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
DEEP_TRAIN = BASE / "data/gjb_438c/data_assets/deep_row_queries_train.json"
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
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--limit", type=int, default=250)
    ap.add_argument("--no-cmsc", action="store_true", help="消融: 去掉CMSC特征")
    ap.add_argument("--reg", type=float, default=50.0,
                    help="信任初始化L2正则(0=无)")
    ap.add_argument("--deep-weight", type=int, default=2,
                    help="深行训练查询重复次数(0=不用)")
    args = ap.parse_args()
    use_cmsc = not args.no_cmsc

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    images = [c for c in chunks if c.get("type") == "image"]
    tables = [c for c in chunks if c.get("type") == "table"]
    with open(DENSE_CACHE, "rb") as f:
        dense: dict[str, list[float]] = pickle.load(f)
    eval_data = json.loads(EVALSET.read_text(encoding="utf-8"))

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    from algorithms.unit_attention import (  # noqa: PLC0415
        CmscProjector,
        SubAttentionAggregator,
        image_units_with_feats,
        table_units_with_feats,
    )

    proj = CmscProjector()
    has_cmsc = use_cmsc and proj.ensure()
    if use_cmsc and not has_cmsc:
        print(f"CMSC不可用({proj.last_error}), 特征置0继续")

    def build(units_with_feats):
        """→ mats/idfs/feats + CMSC投影单元矩阵(对齐保证: 同一提取器)."""
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
        mats, idfs, feats, cmsc = {}, {}, {}, {}
        for cid, (ts, ft) in units_with_feats.items():
            keep = [i for i, t in enumerate(ts) if t in tv]
            if not keep:
                continue
            mat = np.stack([tv[ts[i]] for i in keep])
            mats[cid] = mat / np.maximum(
                np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
            idfs[cid] = np.asarray(
                [np.log(1 + N / df[ts[i]]) for i in keep], dtype=np.float32)
            feats[cid] = ft[keep]
            if has_cmsc:
                pm = proj.project_units(mats[cid])
                cmsc[cid] = pm
        return mats, idfs, feats, cmsc

    img_units = image_units_with_feats(chunks)
    img_mats, img_idfs, img_feats, img_cmsc = build(img_units)
    tab_units = table_units_with_feats(chunks)
    tab_mats, tab_idfs, tab_feats, tab_cmsc = build(tab_units)
    print(f"图: {len(img_mats)}图, 表: {len(tab_mats)}表, "
          f"CMSC: {'on' if has_cmsc else 'off'}")

    fold_map = {}
    for i, d in enumerate(range(1, 17)):
        fold_map[f"{d:02d}"] = i % 4

    def query_vec(q: str) -> np.ndarray | None:
        v = bge.embed([QUERY_PREFIX + q[:200]]).get(QUERY_PREFIX + q[:200])
        if not v:
            return None
        qn = np.asarray(v, dtype=np.float32)
        return qn / np.linalg.norm(qn)

    def make_cands(qn, q_cmsc, pool, mats, idfs, feats, cmsc):
        """候选批: [cid, sims, cmsc_sims, idfs, feats, is_pos]."""
        out = []
        for cid in pool:
            m = mats.get(cid)
            if m is None:
                continue
            sims = m @ qn
            cs = None
            if q_cmsc is not None and cid in cmsc:
                cs = cmsc[cid] @ q_cmsc
            out.append([cid, sims, cs, idfs[cid], feats[cid], False])
        return out

    # ═══ 图: evalset_v3 4-fold ═══
    print(f"\n{'=' * 64}")
    print("图检索: 子注意力(冻结BGE+CMSC+结构特征→学习聚合) vs 固定聚合")
    print(f"{'=' * 64}")
    img_res = defaultdict(lambda: defaultdict(list))
    att = SubAttentionAggregator(use_cmsc=has_cmsc)
    for fold in range(4):
        train_qs = [q for q in eval_data if q["fold"] != fold][:args.limit]
        test_qs = [q for q in eval_data if q["fold"] == fold][:args.limit]
        train_pool = [c["chunk_id"] for c in images
                      if fold_map[c["doc"][:2]] != fold
                      and c["chunk_id"] in dense]
        test_pool = [c["chunk_id"] for c in images
                     if fold_map[c["doc"][:2]] == fold
                     and c["chunk_id"] in dense]
        if not test_qs or not test_pool:
            continue

        batches = []
        for q in train_qs:
            qn = query_vec(q["query"])
            if qn is None:
                continue
            q_cmsc = proj.project_query(qn) if has_cmsc else None
            cands = make_cands(qn, q_cmsc, train_pool,
                               img_mats, img_idfs, img_feats, img_cmsc)
            if not cands:
                continue
            pos = set(q["expected"]["chunk_ids"])
            for c in cands:
                c[5] = c[0] in pos
            if any(c[5] for c in cands):
                batches.append({"cands": cands})
        if len(batches) < 50:
            print(f"  fold{fold}: 训练批不足({len(batches)}), 跳过")
            continue
        loss = att.fit(batches, epochs=args.epochs, reg=args.reg)
        print(f"  fold{fold}: {len(batches)}批, loss={loss:.4f}")

        targets = {q["query"]: set(q["expected"]["chunk_ids"]) for q in test_qs}
        s_fixed, s_att = {}, {}
        for q in test_qs:
            qn = query_vec(q["query"])
            if qn is None:
                continue
            q_cmsc = proj.project_query(qn) if has_cmsc else None
            cands = make_cands(qn, q_cmsc, test_pool,
                               img_mats, img_idfs, img_feats, img_cmsc)
            if not cands:
                continue
            fx = np.full(len(cands), -1.0)
            for i, c in enumerate(cands):
                ws = c[1] * c[3]
                fx[i] = float(ws.max())
            s_fixed[q["query"]] = fx
            s_att[q["query"]] = att.chunk_scores(cands)
        # 对齐cand顺序到test_pool
        R = img_res[fold]
        R["FIXED"].append(metrics_from_scores(s_fixed, targets,
                                              [c[0] for c in cands]))
        R["UAA"].append(metrics_from_scores(s_att, targets,
                                            [c[0] for c in cands]))

    for k in ("FIXED", "UAA"):
        agg = [r for f in range(4) if f in img_res and k in img_res[f]
               for r in img_res[f][k]]
        if agg:
            avg = {m: round(np.mean([r[m] for r in agg]), 4) for m in agg[0]}
            print(f"  图 {k:6s}: R@1={avg['R@1']:.3f} R@5={avg['R@5']:.3f} "
                  f"MRR={avg['MRR@10']:.3f} (n={len(agg)})")

    # ═══ 表: docT5训练, 双场景测试 ═══
    print(f"\n{'=' * 64}")
    print("表格: 子注意力 vs 固定聚合(caption级训练, 双场景测试)")
    print(f"{'=' * 64}")
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

    tab_res = defaultdict(lambda: defaultdict(list))
    deep_train = []
    if DEEP_TRAIN.exists():
        deep_train = [(o["query"], o["cid"])
                      for o in json.loads(DEEP_TRAIN.read_text(encoding="utf-8"))]
    att_t = SubAttentionAggregator(use_cmsc=has_cmsc)
    for fold in range(4):
        # 训练查询: docT5 caption级 + 深行(训练折, 加权) —— 补齐深行分布
        train_pairs = [(q, cid) for q, cid in dq_pairs
                       if fold_map.get(cid2doc.get(cid, "")) != fold]
        for _ in range(args.deep_weight):
            train_pairs.extend(
                (q, cid) for q, cid in deep_train
                if fold_map.get(cid2doc.get(cid, "")) != fold
                and cid in tab_mats)
        train_pool = [t["chunk_id"] for t in tables
                      if fold_map[t["doc"][:2]] != fold
                      and t["chunk_id"] in dense]
        batches = []
        for q, cid in train_pairs:
            if cid not in tab_mats:
                continue
            qn = query_vec(q)
            if qn is None:
                continue
            q_cmsc = proj.project_query(qn) if has_cmsc else None
            cands = make_cands(qn, q_cmsc, train_pool,
                               tab_mats, tab_idfs, tab_feats, tab_cmsc)
            if not cands:
                continue
            for c in cands:
                c[5] = c[0] == cid
            if any(c[5] for c in cands):
                batches.append({"cands": cands})
        if len(batches) < 50:
            continue
        loss = att_t.fit(batches, epochs=args.epochs, reg=args.reg)
        print(f"  fold{fold}: {len(batches)}批, loss={loss:.4f}")

        for scene, pairs in (("caption", dq_pairs), ("deep", deep_pairs)):
            fp = defaultdict(set)
            for q, cid in pairs:
                if fold_map.get(cid2doc.get(cid, "")) == fold:
                    fp[q].add(cid)  # 同文本查询合并目标(与table_late口径一致)
            pool = [t["chunk_id"] for t in tables
                    if fold_map[t["doc"][:2]] == fold
                    and t["chunk_id"] in dense]
            if not fp or not pool:
                continue
            for q, cids_q in fp.items():
                qn = query_vec(q)
                if qn is None:
                    continue
                q_cmsc = proj.project_query(qn) if has_cmsc else None
                cands = make_cands(qn, q_cmsc, pool,
                                   tab_mats, tab_idfs, tab_feats, tab_cmsc)
                if not cands:
                    continue
                fx = np.full(len(cands), -1.0)
                for i, c in enumerate(cands):
                    ws = c[1] * c[3]
                    fx[i] = max(float(ws[0]), float(ws.max()))
                at = att_t.chunk_scores(cands)
                ids_c = [c[0] for c in cands]
                tgt = {q: cids_q}
                R = tab_res[(fold, scene)]
                R["FIXED"].append(metrics_from_scores({q: fx}, tgt, ids_c))
                R["UAA"].append(metrics_from_scores({q: at}, tgt, ids_c))

    for scene in ("caption", "deep"):
        for k in ("FIXED", "UAA"):
            agg = [r for (f, sc), R in tab_res.items()
                   if sc == scene and k in R for r in R[k]]
            if agg:
                avg = {m: round(np.mean([r[m] for r in agg]), 4) for m in agg[0]}
                print(f"  {scene:8s} {k:6s}: R@1={avg['R@1']:.3f} "
                      f"R@5={avg['R@5']:.3f} MRR={avg['MRR@10']:.3f} (n={len(agg)})")

    att.save(BASE / "models/unit_attention_img.pt")
    att_t.save(BASE / "models/unit_attention_tab.pt")
    print("\n模型: models/unit_attention_img.pt / unit_attention_tab.pt")

    out = BASE / "data/gjb_438c/data_assets/unit_attention_eval.json"
    final = {"image": {}, "table_caption": {}, "table_deep": {}}
    for k in ("FIXED", "UAA"):
        agg = [r for f in range(4) if f in img_res and k in img_res[f]
               for r in img_res[f][k]]
        if agg:
            final["image"][k] = {m: round(np.mean([r[m] for r in agg]), 4)
                                 for m in agg[0]}
    for scene, key in (("caption", "table_caption"), ("deep", "table_deep")):
        for k in ("FIXED", "UAA"):
            agg = [r for (f, sc), R in tab_res.items()
                   if sc == scene and k in R for r in R[k]]
            if agg:
                final[key][k] = {m: round(np.mean([r[m] for r in agg]), 4)
                                 for m in agg[0]}
    out.write_text(json.dumps({
        "protocol": (f"4-fold doc-separation, {args.epochs} epochs, reg={args.reg}, BGE+CMSC "
                     f"frozen, cmsc={'on' if has_cmsc else 'off'}, "
                     "attention over sub-units"),
        "results": final}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结果 → {out}")


if __name__ == "__main__":
    main()
