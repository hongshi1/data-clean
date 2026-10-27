r"""池内判别失败的因果归因探针(oracle ladder第一级).

问题: 186条"gold∈top-50但未登顶"——因果断在哪一环?
  环节1 文档选择: CE看到的是gold表的top-2单元(stage-1单元序),
                  若答案行不在其中→CE根本没读到能赢的行
  环节2 CE判别力: 即使给gold表最优单元(oracle-doc), CE分数
                  仍输给当前赢家→判别器本身不行

探针设计(对全部池内失败查询):
  s_cur(gold)  = CE(query, gold表当前top-2单元doc)   [现行行为]
  s_ora(gold)  = max over gold表全部单元 CE(query, unit) [oracle文档]
  s_win        = CE(query, 赢家表top-2单元doc)        [现行行为]
归因:
  unit-selection失败: s_ora > s_win >= s_cur  (换对行就能赢)
  CE判别失败:        s_win >= s_ora           (最好行也赢不了)
用法: python tools/eval/rerank_causal_probe.py
产出: results/_causal_probe.json + runs归档
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    pool = [c for c in ds["corpus"] if c["type"] == "table"]
    corpus = {c["chunk_id"]: c for c in ds["corpus"]}
    queries = [q for q in ds["queries"]
               if q["scene"] in ("table_deep_v3", "table_deep_v4")
               and q["split"] == "eval"]

    from algorithms.context_linking.evidence_recall import (
        EvidenceStore,
        MultiHeadRecall,
    )
    from algorithms.common import bge_local
    from algorithms.blackboard.reranker import BgeReranker

    enc = bge_local.BgeLocal(cache_path=None)
    enc.ensure()
    store = EvidenceStore.from_ure(pool)
    rc = MultiHeadRecall(store, enc)
    rr = BgeReranker()
    rr.ensure()
    print("因果归因探针: 池内失败(gold∈top50且未登顶)")

    def ce(query: str, doc: str) -> float:
        doc = doc[:2000]
        return rr.score([(query, doc)])[0]

    n_sel = n_ce = 0
    per_q = []
    t0 = time.time()
    for qi, q in enumerate(queries):
        golds = set(q["expected"])
        r50 = rc.recall(q["query"], pool="table", topk=50)
        hits = r50.hits
        winner = hits[0].owner if hits else None
        # 跳过: 赢家即gold / gold不在top50
        if winner in golds:
            continue
        gold_hit = next((h for h in hits if h.owner in golds), None)
        if gold_hit is None:
            continue
        # 现行分数
        s_cur = ce(q["query"], " ; ".join(gold_hit.best_units))
        # 赢家分数
        s_win = ce(q["query"], " ; ".join(hits[0].best_units))
        # oracle文档: gold表全部单元逐一打分取max
        gold_cid = gold_hit.owner
        gold_units = [u for u in corpus[gold_cid]["units"] if u]
        oracle_scores = [ce(q["query"], u) for u in gold_units]
        s_ora = max(oracle_scores) if oracle_scores else -1e9
        # 归因
        if s_ora > s_win:
            verdict = "unit_selection"   # 换对行就能赢
            n_sel += 1
        else:
            verdict = "ce_discrimination"  # 最优行也赢不了
            n_ce += 1
        per_q.append({
            "query": q["query"][:40], "verdict": verdict,
            "s_cur": round(s_cur, 4), "s_ora": round(s_ora, 4),
            "s_win": round(s_win, 4),
            "gold_rank": next(
                (i for i, h in enumerate(hits, 1) if h.owner in golds), -1),
        })
        if (qi + 1) % 100 == 0:
            print(f"  {qi+1}/{len(queries)} ({time.time()-t0:.0f}s)",
                  flush=True)

    total = n_sel + n_ce
    print(f"\n【归因结果】池内失败={total}条")
    print(f"  文档选择失败(答案行没进CE视野, 换对行即赢): {n_sel} "
          f"({n_sel/max(total,1):.0%})")
    print(f"  CE判别失败(最优行也输给赢家): {n_ce} "
          f"({n_ce/max(total,1):.0%})")

    out = {
        "protocol": ("池内判别失败因果归因: s_cur=现行gold doc分, "
                     "s_ora=gold表全单元CE最大分, s_win=赢家doc分; "
                     "s_ora>s_win=文档选择失败, 否则=CE判别失败"),
        "summary": {"within_pool_failures": total,
                    "unit_selection_fail": n_sel,
                    "ce_discrimination_fail": n_ce},
        "per_query": per_q,
    }
    outp = RESULTS / "_causal_probe.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"→ {outp}")

    from run_utils import open_run
    handle = open_run("rerank_causal_probe", {
        "probe": "oracle-doc CE vs winner-doc CE", "n": total})
    handle.save_result(out["summary"])
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
