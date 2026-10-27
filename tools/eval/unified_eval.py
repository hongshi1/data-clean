r"""S1修复: 在GJB-URE-v3的统一查询集上跑全部方法.

每个场景一个JSON, 所有方法在同一查询集, 带查询集哈希校验.
产出: results/S{N}_{scene}_all.json

用法: python tools/eval/unified_eval.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

E = BASE / "data/gjb_438c/data_assets"
EV = E / "evalsets"
V3 = EV / "V3"
RESULTS = EV / "results"
PREFIX_ZH = "为这个句子生成表示以用于检索相关文章："

from eval_baselines import BM25, metrics_rows, tokenize  # noqa: E402


def zscore(x: np.ndarray) -> np.ndarray:
    sd = float(x.std())
    return (x - x.mean()) / (sd if sd > 1e-8 else 1.0)


def query_set_hash(queries: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(q["query"] for q in queries),
                   ensure_ascii=False).encode()).hexdigest()[:16]


def eval_scene(bge, m3, contriever_enc, corpus, queries, scene_filter,
                scene_name, out_name, cand_type):
    """一个场景的全方法评测. scene_filter可为str或str的集合(联合场景)."""
    if isinstance(scene_filter, str):
        scene_filter = {scene_filter}
    scene_qs = [q for q in queries if q["scene"] in scene_filter
                and q["split"] == "eval"]
    if not scene_qs:
        print(f"  [跳过] {scene_name}: 无eval查询")
        return

    pool = [c for c in corpus if c["type"] == cand_type]
    if not pool:
        print(f"  [跳过] {scene_name}: 无候选")
        return

    ids = [c["chunk_id"] for c in pool]
    idx = {cid: i for i, cid in enumerate(ids)}
    n = len(pool)
    texts = [c["title"] + " " + " ".join(c["units"]) for c in pool]

    print(f"\n  [{scene_name}] {len(scene_qs)}q × {n}候选"
          f"(hash={query_set_hash(scene_qs)})")

    # BM25
    bm25_doc = BM25([tokenize(t) for t in texts])
    raw_units = [[u for u in ([c["title"]] + c["units"]) if u] for c in pool]
    bm25_unit = BM25([tokenize(u) for ru in raw_units for u in ru])
    unit_owner = [i for i, ru in enumerate(raw_units) for _ in ru]

    # Dense
    dense_texts = [t[:512] for t in texts]
    dvecs = bge.embed(dense_texts)
    D = np.stack([np.asarray(dvecs.get(t, [0.0] * 1024),
                              dtype=np.float32) for t in dense_texts])
    D = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-8)

    # Unit
    unit_texts = [u for ru in raw_units for u in ru]
    uvecs = bge.embed(unit_texts)
    U = np.stack([np.asarray(uvecs.get(u, [0.0] * 1024),
                              dtype=np.float32) for u in unit_texts]).T
    U = U / np.maximum(np.linalg.norm(U, axis=0, keepdims=True), 1e-8)
    dfc = {}
    for ru in raw_units:
        for u in set(ru):
            dfc[u] = dfc.get(u, 0) + 1
    idf = np.asarray([np.log(1 + n / max(dfc.get(u, 1), 1))
                      for u in unit_texts], dtype=np.float32)
    seg = np.cumsum([0] + [len(ru) for ru in raw_units])

    # M3 (fp16, 512token)
    m3_out = m3.encode(texts, batch_size=64, max_length=512,
                       return_dense=True, return_sparse=True,
                       return_colbert_vecs=True)
    M3D = np.asarray(m3_out["dense_vecs"], dtype=np.float32)
    m3_lex = m3_out["lexical_weights"]
    cv = [np.asarray(v, dtype=np.float32) for v in m3_out["colbert_vecs"]]
    m3_offsets = np.cumsum([0] + [len(v) for v in cv])

    # Contriever
    D_ct = contriever_enc(texts)

    # 评分
    sc = defaultdict(list)
    golds = []
    t0 = time.time()
    for q in scene_qs:
        g = {idx[t] for t in q["expected"] if t in idx}
        golds.append(g)
        query = q["query"]

        qt = tokenize(query)
        # BM25-doc
        sc["BM25-doc"].append(np.asarray(
            [bm25_doc.score(qt, i) for i in range(n)]))
        # BM25-unit
        us = np.asarray([bm25_unit.score(qt, i)
                         for i in range(len(unit_owner))])
        su = np.full(n, -1e9)
        for ui, owner in enumerate(unit_owner):
            if us[ui] > su[owner]:
                su[owner] = us[ui]
        sc["BM25-unit"].append(su)

        # B1-dense
        v = bge.embed([PREFIX_ZH + query[:200]]).get(PREFIX_ZH + query[:200])
        if not v:
            for k in list(sc.keys()):
                sc[k].pop()
            golds.pop()
            continue
        qn = np.asarray(v, dtype=np.float32)
        qn = qn / np.linalg.norm(qn)
        sc["B1-dense"].append(D @ qn)

        # O1-unit
        sims_u = (U.T @ qn) * idf
        segmax = np.asarray([sims_u[seg[i]:seg[i + 1]].max()
                             if seg[i] < seg[i + 1] else -1e9
                             for i in range(n)])
        sc["O1-unit"].append(segmax)

        # M3-dense
        mq = m3.encode([query[:200]], return_dense=True,
                       return_sparse=True, return_colbert_vecs=True)
        sc["M3-dense"].append(M3D @ np.asarray(
            mq["dense_vecs"][0], dtype=np.float32))

        # M3-sparse
        ql = mq["lexical_weights"][0]
        s_sp = np.zeros(n)
        for di, dl in enumerate(m3_lex):
            s_ = 0.0
            for t, wq in ql.items():
                wd = dl.get(t)
                if wd is not None:
                    s_ += float(wq) * float(wd)
            s_sp[di] = s_
        sc["M3-sparse"].append(s_sp)

        # M3-colbert (逐条MaxSim)
        qv = np.asarray(mq["colbert_vecs"][0], dtype=np.float32)
        # 分段reduceat
        all_tokens = np.concatenate(cv, axis=0) if cv else np.zeros((1, 768))
        # 归一化
        all_n = all_tokens / np.maximum(
            np.linalg.norm(all_tokens, axis=1, keepdims=True), 1e-8)
        qv_n = qv / np.maximum(np.linalg.norm(qv, axis=1, keepdims=True), 1e-8)
        sims_c = qv_n @ all_n.T  # (n_qt, total_tokens)
        seg_starts = m3_offsets[:-1].astype(np.int64)
        seg_max = np.maximum.reduceat(sims_c, seg_starts, axis=1)
        sc["M3-colbert"].append(seg_max.sum(axis=0))

        # Contriever-MS
        q_ct = contriever_enc([query[:200]])[0]
        sc["Contriever-MS"].append(D_ct @ q_ct)

    print(f"  评分完成 ({time.time() - t0:.0f}s)")

    # 汇总
    results = {}
    for k in ("BM25-doc", "BM25-unit", "B1-dense", "Contriever-MS",
              "M3-dense", "M3-sparse", "M3-colbert", "O1-unit"):
        if sc[k]:
            results[k] = metrics_rows(sc[k], golds, n)
            m = results[k]
            print(f"    {k:16s}: R@1={m['R@1']:.3f} R@5={m['R@5']:.3f}"
                  f" MRR={m['MRR@10']:.3f}")

    # 保存
    out = {
        "protocol": {
            "scene": scene_name,
            "n_queries": len(scene_qs),
            "n_candidates": n,
            "query_set_hash": query_set_hash(scene_qs),
            "fold_rule": "(doc-1) mod 4",
        },
        "results": results,
    }
    outp = RESULTS / out_name
    # 合并写入: 查询集哈希一致时保留旧追加条目(重排/域适配), 基线以本次为准;
    # 哈希变化则丢弃旧条目(不同查询集上的数字不可混存).
    if outp.exists():
        old = json.loads(outp.read_text(encoding="utf-8"))
        if (old.get("protocol", {}).get("query_set_hash")
                == out["protocol"]["query_set_hash"]):
            for k, v in old.get("results", {}).items():
                if k not in results:
                    results[k] = v
            out["results"] = results
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"    → {outp}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("S1修复: 统一查询集全方法评测")
    print("=" * 60)

    ure_path = V3 / "gjb_ure_v4.json"
    if not ure_path.exists():
        ure_path = V3 / "gjb_ure_v3.json"
    v3 = json.loads(ure_path.read_text(encoding="utf-8"))
    corpus = v3["corpus"]
    queries = v3["queries"]
    print(f"数据集: {ure_path.name}, corpus: {len(corpus)}, "
          f"queries: {len(queries)}")

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    from FlagEmbedding import BGEM3FlagModel
    m3 = BGEM3FlagModel(str(BASE / "models/embedding/bge-m3"),
                        use_fp16=True, devices=["cuda"])

    from transformers import AutoModel, AutoTokenizer
    import torch
    ct_tok = AutoTokenizer.from_pretrained(
        str(BASE / "models/contriever-ms"), local_files_only=True)
    ct_mdl = AutoModel.from_pretrained(
        str(BASE / "models/contriever-ms"), local_files_only=True).to("cuda").eval()

    def ct_enc(texts, bs=64):
        vecs = []
        for i in range(0, len(texts), bs):
            e = ct_tok(texts[i:i + bs], padding=True, truncation=True,
                       max_length=512, return_tensors="pt")
            e = {k: v.to("cuda") for k, v in e.items()}
            with torch.no_grad():
                out = ct_mdl(**e)
                mask = e["attention_mask"].unsqueeze(-1).float()
                emb = (out.last_hidden_state * mask).sum(1) / mask.sum(1)
                emb = torch.nn.functional.normalize(emb, dim=-1)
            vecs.append(emb.float().cpu().numpy())
        return np.concatenate(vecs)

    # 场景列表 (v4存在时追加deep_v4与联合场景)
    eval_scene(bge, m3, ct_enc, corpus, queries,
               "image", "GJB图", "S4_image_all.json", "image")
    eval_scene(bge, m3, ct_enc, corpus, queries,
               "table_deep_v3", "GJB深行v3", "S1_deep_v3_all.json", "table")
    eval_scene(bge, m3, ct_enc, corpus, queries,
               "table_deep_v1", "GJB深行v1(对照)", "S3_deep_v1_all.json",
               "table")
    if any(q["scene"] == "table_deep_v4" for q in queries):
        eval_scene(bge, m3, ct_enc, corpus, queries,
                   "table_deep_v4", "GJB深行v4(扩展)",
                   "S5_deep_v4_all.json", "table")
        eval_scene(bge, m3, ct_enc, corpus, queries,
                   {"table_deep_v3", "table_deep_v4"}, "GJB深行v3+v4(16文档)",
                   "S6_deep_v34_all.json", "table")
    # caption是train/诊断, 不在S1统一评测内

    print("\n完成.")


if __name__ == "__main__":
    main()
