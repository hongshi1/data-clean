"""表检索画像矩阵共享实现(eval_table_late与复用方共用).

画像定义(错误分析驱动, 2026-10-07):
  TP-raw: 原始行单元+精确IDF——复述式查询(拷贝行文本)最优
  TP-cc:  标题拼接单元+精确IDF——标题级查询最优(caption +8.6)
  TP-cf:  标题拼接+池相对模糊IDF@0.9——语义深行最优(+6.5)
路由: R(d,profile)=max-z(dense, 画像...)
"""
from __future__ import annotations

import numpy as np

PREFIX = "为这个句子生成表示以用于检索相关文章："


def metrics_rows(scores: list, targets: list, ids: list) -> dict:
    from eval_baselines import metrics_rows as _m  # noqa: PLC0415
    return _m(scores, targets, ids)


def zs(x: np.ndarray) -> np.ndarray:
    sd = float(x.std())
    return (x - x.mean()) / (sd if sd > 1e-8 else 1.0)


def run_profile_matrix(bge, corpus: list, scenes: dict, fold_map: dict,
                       dense: dict, cid2doc: dict) -> dict:
    """三场景×三画像×路由矩阵. 返回{scene: {method: metrics}}."""
    from collections import defaultdict

    final: dict = {}
    for scene, pairs in scenes.items():
        sc: dict = defaultdict(list)
        golds: list = []
        for fold in range(4):
            pool = [c for c in corpus if c.get("type") == "table"
                    and c.get("fold") == fold]
            fold_pairs = [(q, cid) for q, cid in pairs
                          if fold_map.get(cid2doc.get(cid, "")) == fold]
            if not pool or not fold_pairs:
                continue
            ids = [c["chunk_id"] for c in pool]
            idx = {cid: i for i, cid in enumerate(ids)}
            n = len(pool)
            raw = [[u for u in ([c.get("title", "")] + c.get("units", []))
                    if u] for c in pool]
            concat = [[raw[i][0]] + [raw[i][0] + "。" + u
                                     for u in raw[i][1:]]
                      for i in range(n)]

            def build(ul):
                texts = [u for l in ul for u in l]
                vecs = bge.embed(texts)
                U = np.stack([np.asarray(vecs.get(u, [0.0] * 1024),
                                         dtype=np.float32) for u in texts]).T
                U = U / np.maximum(np.linalg.norm(U, axis=0,
                                                  keepdims=True), 1e-8)
                seg = np.cumsum([0] + [len(l) for l in ul])
                df: dict = {}
                for l in ul:
                    for u in set(l):
                        df[u] = df.get(u, 0) + 1
                idf = np.asarray([np.log(1 + n / max(df.get(u, 1), 1))
                                  for u in texts], dtype=np.float32)
                return U, seg, idf

            Ur, segr, idfr = build(raw)
            Uc, segc, idfc = build(concat)
            # 池相对模糊IDF(raw向量, th=0.9)
            Urt = Ur.T
            sims = Urt @ Ur
            np.fill_diagonal(sims, -1.0)
            owner = np.concatenate([np.full(len(l), i, dtype=np.int64)
                                    for i, l in enumerate(raw)])
            near = sims > 0.90
            del sims
            fuzzy = np.empty(Urt.shape[0], dtype=np.float32)
            for r in range(Urt.shape[0]):
                ch = set(int(owner[j]) for j in np.nonzero(near[r])[0])
                ch.add(int(owner[r]))
                fuzzy[r] = np.log(1 + n / len(ch))
            del near
            dense_texts = [(c.get("title", "") + " "
                            + " ".join(c.get("units", [])))[:512]
                           for c in pool]
            dvecs = bge.embed(dense_texts)
            D = np.stack([np.asarray(dvecs.get(t, [0.0] * 1024),
                                     dtype=np.float32) for t in dense_texts])
            D = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-8)
            for q, _cid in fold_pairs:
                g = {idx[t] for t in [_cid] if t in idx}
                golds.append(g)
                v = bge.embed([PREFIX + q[:200]]).get(PREFIX + q[:200])
                if not v:
                    continue
                qn = np.asarray(v, dtype=np.float32)
                qn = qn / np.linalg.norm(qn)
                s_dense = D @ qn

                def segmax(Um, seg, w):
                    sv = (Um.T @ qn) * w
                    return np.asarray([sv[seg[i]:seg[i + 1]].max()
                                       for i in range(n)])

                s_raw = segmax(Ur, segr, idfr)
                s_cc = segmax(Uc, segc, idfc)
                s_cf = segmax(Uc, segc, fuzzy)
                sc["B1_dense"].append(s_dense)
                sc["TP-raw"].append(s_raw)
                sc["TP-cc"].append(s_cc)
                sc["TP-cf"].append(s_cf)
                sc["R(d,raw)"].append(np.maximum(
                    0.8 * zs(s_dense), zs(s_raw)))
                sc["R(d,cc)"].append(np.maximum(
                    0.8 * zs(s_dense), zs(s_cc)))
                sc["R(d,cf)"].append(np.maximum(
                    0.8 * zs(s_dense), zs(s_cf)))
        results = {}
        print(f"\n[{scene}] (n={len(golds)})")
        print(f"{'方法':<12s} R@1    R@5    MRR@10")
        for k in ("B1_dense", "TP-raw", "TP-cc", "TP-cf",
                  "R(d,raw)", "R(d,cc)", "R(d,cf)"):
            if sc[k]:
                m = metrics_rows(sc[k], golds, ids)
                results[k] = m
                print(f"  {k:<10s} {m['R@1']:.3f}  {m['R@5']:.3f}  "
                      f"{m['MRR@10']:.3f}")
        final[scene] = results
    return final
