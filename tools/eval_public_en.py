r"""公开数据集英文编码器评测(语言匹配协议, 外部效度修复).

背景: 早期pilot用bge-large-zh跑英文(WTQ dense仅0.155)——语言错配
对dense伤害大于单元, 增益被放大. 本工具用bge-base-en-v1.5
(models/embedding/bge-base-en-v1.5, 经hf-mirror下载)复跑,
协议等价性经zh复现校验(数字与锁定值逐位一致).

结论(en编码器, 2026-10-06):
  WTQ: O1-unit 0.4095/0.5875/0.4877 **反超BM25-doc(+12.8 R@1)**
  FeTaQA: O1-unit 0.856/0.938/0.891 反超BM25-unit(+6.75)
  ROUTE增益不外推: en下纯O1>ROUTE4——路由降级为"弱/错配
  编码器下的鲁棒机制", 非通用最优.

用法: python tools/eval_public_en.py [--n-queries 2000]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from eval_baselines import BM25, metrics_rows, row_hit, tokenize  # noqa: E402

WTQ_URE = BASE / "data/gjb_438c/data_assets/evalsets/wtq_ure.json"
FETAQA_URE = BASE / "data/gjb_438c/data_assets/evalsets/fetaqa_ure.json"
EN_MODEL = BASE / "models/embedding/bge-base-en-v1.5"
EN_CACHE = BASE / "data/gjb_438c/blackboard/bge_cache_en.pkl"
EN_PREFIX = "Represent this sentence for searching relevant passages: "


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-queries", type=int, default=2000)
    args = ap.parse_args()
    if not (EN_MODEL / "config.json").exists():
        print(f"英文模型缺失: {EN_MODEL}(先经hf-mirror下载)")
        sys.exit(1)

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(model_dir=EN_MODEL, cache_path=EN_CACHE)
    if bge.ensure() != "gpu":
        print(f"英文模型加载: {bge.mode}")

    def run_public(path: Path, label: str, row_gold: bool) -> dict:
        ds = json.loads(path.read_text(encoding="utf-8"))
        corpus = ds["corpus"]
        queries = ds["queries"]
        rng = np.random.default_rng(42)
        sel = rng.permutation(len(queries))[:args.n_queries]
        sel_qs = [queries[i] for i in sel]
        ids = [c["chunk_id"] for c in corpus]
        idx = {cid: i for i, cid in enumerate(ids)}
        print(f"\n[{label}] {len(corpus)}候选×{len(sel_qs)}查询(en)")

        docs = [tokenize(c["title"] + " " + " ".join(c["units"]))
                for c in corpus]
        bm25_doc = BM25(docs)
        raw_units = [[u for u in ([c["title"]] + c["units"]) if u]
                     for c in corpus]
        unit_lists = [[tokenize(u) for u in ru] for ru in raw_units]
        unit_owner = [i for i, ul in enumerate(unit_lists) for _ in ul]
        bm25_unit = BM25([u for ul in unit_lists for u in ul])
        seg_start = np.cumsum([0] + [len(ru) for ru in raw_units])

        unit_texts = [u for ru in raw_units for u in ru]
        vecs = bge.embed(unit_texts)
        U = np.stack([np.asarray(vecs.get(u, [0.0] * 768), dtype=np.float32)
                      for u in unit_texts]).T
        U = U / np.maximum(np.linalg.norm(U, axis=0, keepdims=True), 1e-8)
        df: dict[str, int] = {}
        for ru in raw_units:
            for u in set(ru):
                df[u] = df.get(u, 0) + 1
        idf_u = np.asarray([np.log(1 + len(corpus) / max(df.get(u, 1), 1))
                            for u in unit_texts], dtype=np.float32)
        dense_texts = [(c["title"] + " " + " ".join(c["units"]))[:512]
                       for c in corpus]
        dvecs = bge.embed(dense_texts)
        D = np.stack([np.asarray(dvecs.get(t, [0.0] * 768), dtype=np.float32)
                      for t in dense_texts])
        D = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-8)
        q_texts = [q["query"] for q in sel_qs]
        qvecs = bge.embed([EN_PREFIX + q[:200] for q in q_texts])
        Q = np.stack([np.asarray(qvecs.get(EN_PREFIX + q[:200],
                                           [0.0] * 768), dtype=np.float32)
                      for q in q_texts])
        Q = Q / np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-8)

        sims_u = (Q @ U) * idf_u[None, :]
        sims_d = Q @ D.T

        def seg_max(mat: np.ndarray) -> np.ndarray:
            out = np.full((mat.shape[0], len(raw_units)), -1e9,
                          dtype=np.float32)
            for i in range(len(raw_units)):
                out[:, i] = mat[:, seg_start[i]:seg_start[i + 1]].max(axis=1)
            return out

        s_unit = seg_max(sims_u)

        sc = defaultdict(list)
        golds = []
        rh = {"O1-unit": 0.0, "BM25-unit": 0.0}
        n_rh = 0
        for qi, q in enumerate(sel_qs):
            qt = tokenize(q["query"])
            sd = np.asarray([bm25_doc.score(qt, i) for i in range(len(ids))])
            us = np.asarray([bm25_unit.score(qt, i)
                             for i in range(len(unit_owner))])
            su = np.full(len(ids), -1e9)
            for ui, owner in enumerate(unit_owner):
                if us[ui] > su[owner]:
                    su[owner] = us[ui]
            golds.append({idx[t] for t in q["expected"] if t in idx})
            sc["BM25-doc"].append(sd)
            sc["BM25-unit"].append(su)
            sc["B1-dense"].append(sims_d[qi])
            sc["O1-unit"].append(s_unit[qi])

            def _zs(x):
                sdv = x.std()
                return (x - x.mean()) / (sdv if sdv > 1e-8 else 1.0)
            sc["ROUTE4"].append(np.maximum.reduce([
                _zs(sd), _zs(su), 0.8 * _zs(sims_d[qi]), _zs(s_unit[qi])]))
            if row_gold and q.get("gold_rows"):
                g0 = next(iter(golds[-1]), None)
                if g0 is not None:
                    # RowHit段偏移已修复: 排除title段, 对齐units下标
                    rh["O1-unit"] += row_hit(
                        sims_u[qi][seg_start[g0] + 1:seg_start[g0 + 1]],
                        set(q["gold_rows"]))
                    rh["BM25-unit"] += row_hit(
                        us[seg_start[g0] + 1:seg_start[g0 + 1]],
                        set(q["gold_rows"]))
                    n_rh += 1

        results = {}
        print(f"  {'方法':<12s} R@1    R@5    R@10   MRR@10"
              + ("   RowHit@1" if row_gold else ""))
        for k in ("BM25-doc", "BM25-unit", "B1-dense", "O1-unit", "ROUTE4"):
            m = metrics_rows(sc[k], golds, len(ids))
            if row_gold and k in rh:
                m["RowHit@1"] = round(rh[k] / max(n_rh, 1), 4)
            results[k] = m
            extra = f"  {m['RowHit@1']:.3f}" if "RowHit@1" in m else ""
            print(f"  {k:<10s} {m['R@1']:.4f}  {m['R@5']:.4f}  "
                  f"{m['R@10']:.4f}  {m['MRR@10']:.4f}{extra}")
        return results

    wtq = run_public(WTQ_URE, "WTQ-URE(en)", False)
    fetaqa = run_public(FETAQA_URE, "FeTaQA-URE(en)", True)

    out = BASE / "data/gjb_438c/data_assets/evalsets/public_en_eval.json"
    out.write_text(json.dumps({
        "protocol": ("bge-base-en-v1.5(语言匹配); 查询前缀Represent this "
                     "sentence...; 单元+IDF+k=1 MaxSim; 2000采样(seed42)全候选; "
                     "RowHit段偏移已修复(排除title)"),
        "results": {"wtq": wtq, "fetaqa": fetaqa},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
