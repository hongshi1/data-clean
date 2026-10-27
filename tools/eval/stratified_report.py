r"""分层报告: 协变量控制的评测(挑战4: 评测效度).

背景: 汇总指标混杂了代理构造协变量, 不同方法的比较被污染:
  - LLM生成查询的overlap高于反复制设计 → 词面方法被抬高
  - 多gold(1-10表) → 绝对R@1被抬高
  - 图片场景标识符查询 → 词面方法锁死头部

本工具按分层重算逐查询R@1(与统一评测同协议):
  deep场景: overlap带(<0.1 / 0.1-0.3 / >=0.3) × gold大小(1 vs 2+)
  image场景: 标识符型(含图号/表号词) vs 语义型

方法: O1-unit(BGE+IDF+segmax) / BM25-doc / Token-MaxSim(仅image).

用法: python tools/eval/stratified_report.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
PREFIX = "为这个句子生成表示以用于检索相关文章："

IDENTIFIER_PAT = re.compile(
    r"图\s*\d|表\s*\d|如图|见图|如下图|如图所示|下图")


def hit_at_1(scores: np.ndarray, golds: set) -> int:
    order = np.argsort(-scores)
    return 1 if (len(order) and order[0] in golds) else 0


def strat_table(rows: list[dict], label: str) -> None:
    print(f"\n[{label}]")
    print(f"  {'分层':<24s} {'n':>4s} {'O1-unit':>8s} {'BM25-doc':>9s}"
          f" {'TMS':>7s}")
    for r in rows:
        tms = f"{r['TMS']:.3f}" if r["TMS"] is not None else "—"
        print(f"  {r['stratum']:<24s} {r['n']:>4d} {r['O1-unit']:>8.3f}"
              f" {r['BM25-doc']:>9.3f} {tms:>7s}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    corpus = ds["corpus"]

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    from eval_baselines import BM25, tokenize

    def run_scene(scene_names: set, cand_type: str,
                  with_tms: bool, label: str,
                  strata_fn) -> list[dict]:
        scene_qs = [q for q in ds["queries"]
                    if q["scene"] in scene_names and q["split"] == "eval"]
        pool = [c for c in corpus if c["type"] == cand_type]
        ids = [c["chunk_id"] for c in pool]
        idx = {cid: i for i, cid in enumerate(ids)}
        n = len(pool)
        print(f"\n编码 {label}: {len(scene_qs)}q × {n}候选", flush=True)

        texts = [c["title"] + " " + " ".join(c["units"]) for c in pool]
        bm25_doc = BM25([tokenize(t) for t in texts])

        raw_units = [[u for u in ([c["title"]] + c["units"]) if u]
                     for c in pool]
        unit_texts = [u for ru in raw_units for u in ru]
        seg = np.cumsum([0] + [len(ru) for ru in raw_units])
        uvecs = bge.embed(unit_texts)
        U = np.stack([np.asarray(uvecs.get(u, [0.0] * 1024),
                                 dtype=np.float32) for u in unit_texts])
        U = U / np.maximum(np.linalg.norm(U, axis=1, keepdims=True), 1e-8)
        dfc: dict[str, int] = {}
        for ru in raw_units:
            for u in set(ru):
                dfc[u] = dfc.get(u, 0) + 1
        idf = np.asarray(
            [np.log(1 + n / max(dfc.get(u, 1), 1)) for u in unit_texts],
            dtype=np.float32)

        tms = None
        if with_tms:
            from eval_token_maxsim import TokenMaxSim
            tms = TokenMaxSim(bge)
            tms.build(texts)

        # 逐查询打分与命中
        rows_by_stratum: dict[str, dict] = defaultdict(
            lambda: {"n": 0, "o1": 0, "bm": 0, "tms": 0})
        for q in scene_qs:
            golds = {idx[t] for t in q["expected"] if t in idx}
            if not golds:
                continue
            qt = tokenize(q["query"])
            sd = np.asarray([bm25_doc.score(qt, i) for i in range(n)])
            v = bge.embed([PREFIX + q["query"][:200]]).get(
                PREFIX + q["query"][:200])
            if not v:
                continue
            qn = np.asarray(v, dtype=np.float32)
            qn = qn / max(np.linalg.norm(qn), 1e-8)
            sims_u = (U @ qn) * idf
            s_o1 = np.asarray(
                [sims_u[seg[i]:seg[i + 1]].max()
                 if seg[i] < seg[i + 1] else -1e9 for i in range(n)])
            s_tms = tms.score(q["query"]) if tms else None

            for st in strata_fn(q):
                r = rows_by_stratum[st]
                r["n"] += 1
                r["o1"] += hit_at_1(s_o1, golds)
                r["bm"] += hit_at_1(sd, golds)
                if s_tms is not None:
                    r["tms"] += hit_at_1(s_tms, golds)

        out = []
        for st in sorted(rows_by_stratum):
            r = rows_by_stratum[st]
            tms_v = (r["tms"] / r["n"]) if r["tms"] else None
            out.append({"stratum": st, "n": r["n"],
                        "O1-unit": r["o1"] / r["n"],
                        "BM25-doc": r["bm"] / r["n"], "TMS": tms_v})
        strat_table(out, label)
        return out

    def deep_strata(q):
        ov = q.get("overlap", 0.0)
        band = ("<0.1" if ov < 0.1 else
                "0.1-0.3" if ov < 0.3 else ">=0.3")
        gsize = "gold=1" if len(q["expected"]) == 1 else "gold>=2"
        return [f"overlap {band}", gsize,
                f"{gsize} × ov{band}"]

    def image_strata(q):
        kind = ("标识符型" if IDENTIFIER_PAT.search(q["query"])
                else "语义型")
        return [kind, "全部"]

    report = {}
    report["S6_deep_v34"] = run_scene(
        {"table_deep_v3", "table_deep_v4"}, "table", False,
        "S6 联合深行438q (overlap×gold分层)", deep_strata)
    report["S1_deep_v3"] = run_scene(
        {"table_deep_v3"}, "table", False,
        "S1 深行v3 262q (反复制, 对照)", deep_strata)
    report["S4_image"] = run_scene(
        {"image"}, "image", True,
        "S4 图片899q (标识符/语义分层)", image_strata)

    outp = RESULTS / "_stratified_report.json"
    outp.write_text(json.dumps({
        "protocol": ("协变量分层R@1; O1-unit/BM25-doc与统一评测同协议; "
                     "TMS=Token-MaxSim(仅image); 分层=overlap带×gold大小"
                     "×标识符型"),
        "strata": report,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {outp}")


if __name__ == "__main__":
    main()
