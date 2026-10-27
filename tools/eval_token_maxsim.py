r"""token级MaxSim(ColBERT式后期交互)对照实验+五通道路由.

论文核心claim的受控检验: 同一BGE骨干下, 结构单元级 vs token级
作为多向量粒度谁更优. token级继承512 token窗口(单向量同款限制),
单元级无总量限制——结构性差异的量化.

通道: BM25-doc | BM25-unit | dense | O1-unit | Token-MaxSim
路由: ROUTE4(前四) | ROUTE5(+token通道)
场景: GJB三场景(4-fold) + WTQ + FeTaQA(全候选)

用法: python tools/eval_token_maxsim.py [--n-queries 2000]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from eval_baselines import BM25, metrics_rows, tokenize  # noqa: E402

GJB_URE = BASE / "data/gjb_438c/data_assets/evalsets/gjb_ure_v1.json"
WTQ_URE = BASE / "data/gjb_438c/data_assets/evalsets/wtq_ure.json"
FETAQA_URE = BASE / "data/gjb_438c/data_assets/evalsets/fetaqa_ure.json"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


def zs(x: np.ndarray) -> np.ndarray:
    sd = float(x.std())
    return (x - x.mean()) / (sd if sd > 1e-8 else 1.0)


class TokenMaxSim:
    """ColBERT式token级后期交互(GPU打分, 骨干=BGE).

    doc表示=全部非pad token向量(512上限, 继承单向量窗口限制);
    score(q, d) = Σ_{qt} max_{dt} cos(qt, dt).
    """

    def __init__(self, bge) -> None:
        self._bge = bge
        self._torch = None
        self._doc_t = None      # (n_tokens, 1024) gpu
        self._seg = None        # (n_tokens,) gpu long
        self._n_chunks = 0

    def build(self, doc_texts: list[str]) -> None:
        torch = self._bge._torch  # noqa: SLF001  自有模块
        self._torch = torch
        mats = []
        segs = []
        for i, t in enumerate(doc_texts):
            v = self._bge.embed_tokens([t])[t]
            mats.append(np.asarray(v, dtype=np.float32))
            segs.append(np.full(len(v), i, dtype=np.int64))
        self._doc_t = torch.as_tensor(np.concatenate(mats),
                                      dtype=torch.float32,
                                      device=self._bge._device)  # noqa: SLF001
        self._seg = torch.as_tensor(np.concatenate(segs), dtype=torch.long,
                                    device=self._bge._device)  # noqa: SLF001
        self._n_chunks = len(doc_texts)

    def score(self, query: str) -> np.ndarray:
        torch = self._torch
        qv = self._bge.embed_tokens([query[:200]], max_length=64)[query[:200]]
        qt = torch.as_tensor(np.asarray(qv, dtype=np.float32),
                             device=self._doc_t.device)
        sims = qt @ self._doc_t.T  # (n_qt, n_tokens)
        out = torch.zeros(self._n_chunks, device=sims.device)
        for r in range(sims.shape[0]):
            seg_max = torch.full((self._n_chunks,), float("-inf"),
                                 device=sims.device)
            seg_max.scatter_reduce_(0, self._seg, sims[r], reduce="amax")
            out += seg_max
        return out.cpu().numpy()


def channel_scores(bge, pool: list[dict], queries: list[dict],
                   with_token: bool = True) -> dict[str, list[np.ndarray]]:
    """单fold/池的全部通道分数(与eval_baselines同口径)."""
    ids = [c["chunk_id"] for c in pool]
    idx = {cid: i for i, cid in enumerate(ids)}
    n = len(pool)
    docs_tok = [tokenize(c["title"] + " " + " ".join(c["units"]))
                for c in pool]
    bm25_doc = BM25(docs_tok)
    raw_units = [[u for u in ([c["title"]] + c["units"]) if u] for c in pool]
    unit_lists = [[tokenize(u) for u in ru] for ru in raw_units]
    unit_owner = [i for i, ul in enumerate(unit_lists) for _ in ul]
    bm25_unit = BM25([u for ul in unit_lists for u in ul])
    # dense
    dense_texts = [(c["title"] + " " + " ".join(c["units"]))[:512] for c in pool]
    dvecs = bge.embed(dense_texts)
    D = np.stack([np.asarray(dvecs.get(t, [0.0] * 1024), dtype=np.float32)
                  for t in dense_texts])
    D = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-8)
    # unit
    unit_texts = [u for ru in raw_units for u in ru]
    uvecs = bge.embed(unit_texts)
    U = np.stack([np.asarray(uvecs.get(u, [0.0] * 1024), dtype=np.float32)
                  for u in unit_texts]).T
    U = U / np.maximum(np.linalg.norm(U, axis=0, keepdims=True), 1e-8)
    df: dict[str, int] = {}
    for ru in raw_units:
        for u in set(ru):
            df[u] = df.get(u, 0) + 1
    idf_u = np.asarray([np.log(1 + n / max(df.get(u, 1), 1))
                        for u in unit_texts], dtype=np.float32)
    seg_start = np.cumsum([0] + [len(ru) for ru in raw_units])
    # token通道
    tms = None
    if with_token:
        tms = TokenMaxSim(bge)
        tms.build([(c["title"] + " " + " ".join(c["units"])) for c in pool])

    out = defaultdict(list)
    for q in queries:
        qt = tokenize(q["query"])
        sd = np.asarray([bm25_doc.score(qt, i) for i in range(n)])
        us = np.asarray([bm25_unit.score(qt, i) for i in range(len(unit_owner))])
        su = np.full(n, -1e9)
        for ui, owner in enumerate(unit_owner):
            if us[ui] > su[owner]:
                su[owner] = us[ui]
        v = bge.embed([QUERY_PREFIX + q["query"][:200]]).get(
            QUERY_PREFIX + q["query"][:200])
        if v is None:
            continue
        qn = np.asarray(v, dtype=np.float32)
        qn = qn / np.linalg.norm(qn)
        s_dense = D @ qn
        sims_u = (U.T @ qn) * idf_u
        s_unit = np.asarray([
            sims_u[seg_start[i]:seg_start[i + 1]].max()
            if seg_start[i] < seg_start[i + 1] else -1e9
            for i in range(n)])
        s_tok = tms.score(q["query"]) if tms else np.zeros(n)
        out["BM25-doc"].append(sd)
        out["BM25-unit"].append(su)
        out["B1-dense"].append(s_dense)
        out["O1-unit"].append(s_unit)
        if tms:
            out["Token-MaxSim"].append(s_tok)
            out["ROUTE5"].append(np.maximum.reduce([
                zs(sd), zs(su), 0.8 * zs(s_dense), zs(s_unit), zs(s_tok)]))
        out["ROUTE4"].append(np.maximum.reduce([
            zs(sd), zs(su), 0.8 * zs(s_dense), zs(s_unit)]))
        # 记录gold(仅池内)
        out["__gold__"].append({idx[t] for t in q["expected"] if t in idx})
    return dict(out)


def report(label: str, chans: dict, golds: list[set],
           n_cands: int) -> dict:
    print(f"\n[{label}] (n={len(golds)}, 候选{n_cands})")
    print(f"{'方法':<14s} R@1    R@5    MRR@10")
    results = {}
    for k in ("BM25-doc", "BM25-unit", "B1-dense", "O1-unit",
              "Token-MaxSim", "ROUTE4", "ROUTE5"):
        if k not in chans:
            continue
        m = metrics_rows(chans[k], golds, n_cands)
        results[k] = m
        print(f"  {k:<12s} {m['R@1']:.3f}  {m['R@5']:.3f}  {m['MRR@10']:.3f}")
    return results


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-queries", type=int, default=2000)
    args = ap.parse_args()

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    all_results: dict[str, dict] = {}

    # ═══ GJB三场景 ═══
    gjb = json.loads(GJB_URE.read_text(encoding="utf-8"))
    corpus = gjb["corpus"]
    queries = gjb["queries"]
    ctype = {"image": "image", "table_caption": "table", "table_deep": "table"}
    scenes = [
        ("image", [q for q in queries if q["scene"] == "image"]),
        ("table_deep", [q for q in queries
                        if q["scene"] == "table_deep" and q["split"] == "eval"]),
        ("table_caption", [q for q in queries
                           if q["scene"] == "table_caption"]),
    ]
    t0 = time.time()
    for scene, scene_qs in scenes:
        t = ctype[scene]
        pool_by_fold: dict[int, list] = defaultdict(list)
        for c in corpus:
            if c["type"] == t:
                pool_by_fold[c["fold"]].append(c)
        chans: dict[str, list] = defaultdict(list)
        golds: list[set] = []
        for fold in range(4):
            pool = pool_by_fold[fold]
            if not pool:
                continue
            fold_qs = [q for q in scene_qs if q["fold"] == fold]
            res = channel_scores(bge, pool, fold_qs, with_token=True)
            for k, v_list in res.items():
                if k == "__gold__":
                    golds.extend(v_list)
                else:
                    chans[k].extend(v_list)
        all_results[f"gjb_{scene}"] = report(
            f"GJB/{scene}", dict(chans), golds, len(pool))
        print(f"  (累计{time.time() - t0:.0f}s)", flush=True)

    # ═══ 公开数据集 ═══
    for path, label in ((WTQ_URE, "wtq"), (FETAQA_URE, "fetaqa")):
        ds = json.loads(path.read_text(encoding="utf-8"))
        corpus_p = ds["corpus"]
        queries_p = ds["queries"]
        rng = np.random.default_rng(42)
        sel = rng.permutation(len(queries_p))[:args.n_queries]
        sel_qs = [queries_p[i] for i in sel]
        res = channel_scores(bge, corpus_p, sel_qs, with_token=True)
        golds = res.pop("__gold__")
        chans = {k: v for k, v in res.items()}
        all_results[label] = report(label, chans, golds, len(corpus_p))
        print(f"  (累计{time.time() - t0:.0f}s)", flush=True)

    out = BASE / "data/gjb_438c/data_assets/evalsets/token_maxsim_eval.json"
    out.write_text(json.dumps({
        "protocol": ("Token-MaxSim=BGE骨干token级后期交互(Σ_qt max_dt cos, "
                     "doc=512token上限继承单向量窗口); ROUTE5=max-z五通道; "
                     "GJB按4-fold, 公开集全候选采样2000"),
        "results": all_results,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
