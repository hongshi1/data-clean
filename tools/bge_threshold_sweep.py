r"""BGE本地通道阈值扫描: 在真实pair数据上锁定EMB_TH_LOCAL.

协议(与calibrate_embedding同构):
  - 对象: pair_dataset的κ_T表格项 × anchors节点(FACT), 词法银标=MATCH_TH
  - 对每个阈值: greedy一对一消费 → n_emb/n_confirmed/agreement(精度下界)
  - 附加: 词法确认对与未确认对的BGE分数分布(分离点直接可见)

产出: data/gjb_438c/blackboard/bge_threshold_sweep.json
用法: python tools/bge_threshold_sweep.py [--limit 80]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from algorithms.common.bge_local import BgeLocal  # noqa: E402
from algorithms.blackboard.evidence_store import EvidenceStore  # noqa: E402
from algorithms.blackboard.kt_compilers import compile_for_scene  # noqa: E402
from algorithms.blackboard.lexical_kit import MATCH_TH, text_match_score  # noqa: E402

OUT_PATH = BASE / "data/gjb_438c/blackboard/bge_threshold_sweep.json"
TH_GRID = [0.60, 0.65, 0.70, 0.72, 0.75, 0.78, 0.80, 0.85]


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) + 1e-10
    return num / den


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    store = EvidenceStore()
    bge = BgeLocal()
    if bge.ensure() == "unavailable":
        print(f"BGE不可用: {bge.last_error}")
        return 1
    print(f"BGE: mode={bge.mode} dim={bge.stats['dim']}")

    # 收集pair的(表项, 锚点节点)文本对
    pairs_data: list[dict[str, Any]] = []
    for pair_id in sorted(store._pair_index()):
        if len(pairs_data) >= args.limit:
            break
        scene = store.scene_of(pair_id)
        anchor = store.pair_anchor(pair_id)
        pd = store.pair_dir(pair_id)
        if anchor is None or pd is None:
            continue
        x_t = compile_for_scene(scene, pd / "table.csv")
        if not x_t:
            continue
        t_names = [n["text"] for n in x_t.get("nodes", []) if n.get("text")]
        d_names = [n["text"] for n in anchor.get("nodes", []) if n.get("text")]
        if t_names and d_names:
            pairs_data.append({"pair_id": pair_id, "t": t_names, "d": d_names})
    print(f"有效pair: {len(pairs_data)}")

    # 一次性算全部向量+分数矩阵
    all_t = [t for p in pairs_data for t in p["t"]]
    all_d = [d for p in pairs_data for d in p["d"]]
    vecs = bge.embed(list(dict.fromkeys([*all_t, *all_d])))
    scores: list[dict[str, Any]] = []
    for p in pairs_data:
        mat = [[_cosine(vecs[t] or [], vecs[d] or []) for d in p["d"]]
               for t in p["t"]]
        lex = [[text_match_score(t, d) >= MATCH_TH for d in p["d"]]
               for t in p["t"]]
        scores.append({"pair_id": p["pair_id"], "mat": mat, "lex": lex})

    # 词法确认对/未确认对的分数分布(分离点)
    conf_scores: list[float] = []
    unconf_scores: list[float] = []
    for s in scores:
        for i, row in enumerate(s["mat"]):
            for j, c in enumerate(row):
                (conf_scores if s["lex"][i][j] else unconf_scores).append(c)

    def band(xs: list[float]) -> dict[str, float]:
        if not xs:
            return {}
        xs2 = sorted(xs)
        n = len(xs2)
        return {"p10": round(xs2[n // 10], 3), "p50": round(xs2[n // 2], 3),
                "p90": round(xs2[(n * 9) // 10], 3)}

    # 每阈值: greedy一对一消费 → agreement
    rows: list[dict[str, Any]] = []
    n_lex_total = 0
    for s in scores:
        for i, lrow in enumerate(s["lex"]):
            n_lex_total += sum(1 for x in lrow if x)

    for th in TH_GRID:
        n_emb = n_conf = 0
        for s in scores:
            cand = sorted(((s["mat"][i][j], i, j)
                           for i in range(len(s["mat"]))
                           for j in range(len(s["mat"][i]))
                           if s["mat"][i][j] >= th), reverse=True)
            used_i: set[int] = set()
            used_j: set[int] = set()
            for c, i, j in cand:
                if i not in used_i and j not in used_j:
                    used_i.add(i)
                    used_j.add(j)
                    n_emb += 1
                    n_conf += 1 if s["lex"][i][j] else 0
        rows.append({
            "th": th, "n_emb": n_emb, "n_confirmed": n_conf,
            "agreement": round(n_conf / n_emb, 4) if n_emb else None,
            "n_lex_pairs": n_lex_total,
            "emb_vs_lex_ratio": round(n_emb / n_lex_total, 3) if n_lex_total else None,
        })

    out = {
        "model": "bge-large-zh-v1.5", "bge_mode": bge.mode,
        "n_pairs": len(pairs_data), "n_lex_total": n_lex_total,
        "silver": f"text_match_score>={MATCH_TH}",
        "score_dist": {"lex_confirmed": band(conf_scores),
                       "not_confirmed": band(unconf_scores),
                       "n_confirmed": len(conf_scores),
                       "n_not_confirmed": len(unconf_scores)},
        "sweep": rows,
        "stats": bge.stats,
        "note": ("agreement=embedding匹配被词法银标确认的比例(精度下界); "
                 "emb_vs_lex_ratio<1过多=欠召回, >1过多=过匹配"),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    bge.save()
    print(json.dumps({"score_dist": out["score_dist"], "sweep": rows},
                     ensure_ascii=False, indent=1))
    print(f"结果: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
