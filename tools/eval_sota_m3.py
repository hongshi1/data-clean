r"""BGE-M3 SOTA基线(官方FlagEmbedding实现): dense/sparse/colbert三模式.

SOTA对照价值:
  ① M3-dense: **8192 token长上下文**——直接挑战"单元分解修复截断"
     的必要性(长上下文dense能否免分解看到深行?)
  ② M3-colbert: 官方late interaction实现(对照我们的Token-MaxSim近似)
  ③ M3-sparse: 学习式词面(对照字符二元组BM25)
多语言(zh+en)——GJB与WTQ/FeTaQA同一模型, 无语言错配.

用法: python tools/eval_sota_m3.py [--n-queries 2000]
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

from eval_baselines import metrics_rows  # noqa: E402

GJB_URE = BASE / "data/gjb_438c/data_assets/evalsets/gjb_ure_v1.json"
WTQ_URE = BASE / "data/gjb_438c/data_assets/evalsets/wtq_ure.json"
FETAQA_URE = BASE / "data/gjb_438c/data_assets/evalsets/fetaqa_ure.json"
M3_DIR = BASE / "models/embedding/bge-m3"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-queries", type=int, default=2000)
    args = ap.parse_args()
    if not (M3_DIR / "config.json").exists():
        print(f"BGE-M3缺失: {M3_DIR}")
        sys.exit(1)

    from FlagEmbedding import BGEM3FlagModel  # noqa: PLC0415

    model = BGEM3FlagModel(str(M3_DIR), use_fp16=False, devices=["cuda"])

    class M3Scorer:
        """一个池的M3三模式打分器."""

        def __init__(self, doc_texts: list[str]) -> None:
            self.n = len(doc_texts)
            t0 = time.time()
            out = model.encode(doc_texts, batch_size=16, max_length=8192,
                               return_dense=True, return_sparse=True,
                               return_colbert_vecs=True)
            self.dense = np.asarray(out["dense_vecs"], dtype=np.float32)
            self.lex = out["lexical_weights"]
            cv = [np.asarray(v, dtype=np.float32) for v in out["colbert_vecs"]]
            self.offsets = np.cumsum([0] + [len(v) for v in cv])
            big = np.concatenate(cv, axis=0)
            import torch  # noqa: PLC0415
            self._torch = torch
            self.tok = torch.as_tensor(big, device="cuda")
            print(f"    编码{self.n}文档({time.time() - t0:.0f}s, "
                  f"{big.shape[0]}tokens)", flush=True)

        def score(self, query: str) -> dict[str, np.ndarray]:
            q = model.encode([query[:200]], return_dense=True,
                             return_sparse=True, return_colbert_vecs=True)
            qd = np.asarray(q["dense_vecs"][0], dtype=np.float32)
            s_dense = self.dense @ qd
            # sparse: Σ_{t∈q∩d} w_q·w_d (官方公式)
            ql = q["lexical_weights"][0]
            s_sparse = np.zeros(self.n, dtype=np.float32)
            for di, dl in enumerate(self.lex):
                sc = 0.0
                for t, wq in ql.items():
                    wd = dl.get(t)
                    if wd is not None:
                        sc += float(wq) * float(wd)
                s_sparse[di] = sc
            # colbert: Σ_qt max_dt cos (官方MaxSim)
            qv = np.asarray(q["colbert_vecs"][0], dtype=np.float32)
            torch = self._torch
            qt = torch.as_tensor(qv, device="cuda")
            sims = qt @ self.tok.T  # (n_qt, n_tokens)
            out = torch.zeros(self.n, device="cuda")
            seg = torch.as_tensor(
                np.concatenate([np.full(self.offsets[i + 1] - self.offsets[i], i,
                                        dtype=np.int64)
                                for i in range(self.n)]), device="cuda")
            for r in range(sims.shape[0]):
                seg_max = torch.full((self.n,), float("-inf"), device="cuda")
                seg_max.scatter_reduce_(0, seg, sims[r], reduce="amax")
                out += seg_max
            s_colbert = out.cpu().numpy()
            return {"M3-dense": s_dense, "M3-sparse": s_sparse,
                    "M3-colbert": s_colbert}

    def eval_pool(doc_texts: list[str], queries: list[dict],
                  ids: list[str]) -> dict[str, dict]:
        idx = {cid: i for i, cid in enumerate(ids)}
        scorer = M3Scorer(doc_texts)
        sc: dict[str, list] = defaultdict(list)
        golds = []
        for q in queries:
            g = {idx[t] for t in q["expected"] if t in idx}
            golds.append(g)
            for k, s in scorer.score(q["query"]).items():
                sc[k].append(s)
        results = {}
        for k in ("M3-dense", "M3-sparse", "M3-colbert"):
            results[k] = metrics_rows(sc[k], golds, len(ids))
        return results

    all_results: dict[str, dict] = {}

    # ═══ GJB三场景(4-fold) ═══
    gjb = json.loads(GJB_URE.read_text(encoding="utf-8"))
    corpus = gjb["corpus"]
    queries = gjb["queries"]
    ctype = {"image": "image", "table_caption": "table", "table_deep": "table"}
    for scene in ("image", "table_deep", "table_caption"):
        t = ctype[scene]
        scene_qs = [q for q in queries if q["scene"] == scene and
                    (scene != "table_deep" or q["split"] == "eval")]
        pool_by_fold: dict[int, list] = defaultdict(list)
        for c in corpus:
            if c["type"] == t:
                pool_by_fold[c["fold"]].append(c)
        sc = defaultdict(list)
        golds = []
        for fold in range(4):
            pool = pool_by_fold[fold]
            if not pool:
                continue
            fold_qs = [q for q in scene_qs if q["fold"] == fold]
            ids = [c["chunk_id"] for c in pool]
            idx = {cid: i for i, cid in enumerate(ids)}
            texts = [c["title"] + " " + " ".join(c["units"]) for c in pool]
            scorer = M3Scorer(texts)
            for q in fold_qs:
                g = {idx[t] for t in q["expected"] if t in idx}
                golds.append(g)
                for k, s in scorer.score(q["query"]).items():
                    sc[k].append(s)
        results = {}
        print(f"\n[GJB/{scene}] (n={len(golds)})")
        print(f"{'方法':<12s} R@1    R@5    MRR@10")
        for k in ("M3-dense", "M3-sparse", "M3-colbert"):
            results[k] = metrics_rows(sc[k], golds, len(pool))
            m = results[k]
            print(f"  {k:<10s} {m['R@1']:.3f}  {m['R@5']:.3f}  {m['MRR@10']:.3f}")
        all_results[f"gjb_{scene}"] = results

    # ═══ 公开数据集 ═══
    for path, label in ((WTQ_URE, "wtq"), (FETAQA_URE, "fetaqa")):
        ds = json.loads(path.read_text(encoding="utf-8"))
        corpus_p = ds["corpus"]
        rng = np.random.default_rng(42)
        sel = rng.permutation(len(ds["queries"]))[:args.n_queries]
        sel_qs = [ds["queries"][i] for i in sel]
        texts = [c["title"] + " " + " ".join(c["units"]) for c in corpus_p]
        results = eval_pool(texts, sel_qs,
                            [c["chunk_id"] for c in corpus_p])
        print(f"\n[{label}] (n={len(sel_qs)})")
        print(f"{'方法':<12s} R@1    R@5    MRR@10")
        for k in ("M3-dense", "M3-sparse", "M3-colbert"):
            m = results[k]
            print(f"  {k:<10s} {m['R@1']:.3f}  {m['R@5']:.3f}  {m['MRR@10']:.3f}")
        all_results[label] = results

    out = BASE / "data/gjb_438c/data_assets/evalsets/sota_m3_eval.json"
    out.write_text(json.dumps({
        "protocol": ("BGE-M3(官方FlagEmbedding, fp32 GPU)三模式; "
                     "dense 8192token长上下文; colbert=官方MaxSim; "
                     "sparse=学习式词面; 无查询前缀; GJB 4-fold, 公开集全候选采样"),
        "results": all_results,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
