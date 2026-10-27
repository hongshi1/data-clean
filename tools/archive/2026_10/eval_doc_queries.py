r"""A6 docT5query扩展评测: 假想查询通道 vs 纯lexical召回.

数据: retrieval_evalset 300条(entity作query, chunk级金标).
融合架构(级联, 与hybrid_recall同哲学 — 纯RRF在通道强度悬殊时被
弱通道稀释, 消融行实证):
  tier1  词法事实直通(确定性命中不被概率通道推翻)
  tier2  假想查询盲区席位(dq命中且lex池完全没有的证据源; 默认0席
         — 600覆盖期per-hit精度~2%, 位移式席位净负, 校准见DQ_SEATS)
  tier3  RRF填充(lex池尾+dq[+bm25], k=60; 仅填lex填不满的空位)

条件:
  lex            纯lexical(精确子串+双关键词, v0口径)
  lex+dq         lexical + 假想查询通道(级联)      ← 主线对比
  lex+dq(rrf)    消融: 纯RRF(展示稀释效应)
  lex+bm25       对照: +BM25通道(排除"加通道即有增益")
  lex+bm25+dq    全开(最强词法基线上的净贡献)
指标: Recall@10 / Recall@20.

净增分析(covered子集 = 期望chunk∩已生成假想查询集合 ≠ ∅ 的query,
覆盖比例在输出注明):
  净增案例数(R@20提升, 其中0→非0), 回退数;
  净增chunk按tier分类(盲区席位/RRF提升), 深层小节(章节深度≥4)计数
  与示例。

结果落盘runs协议(tools/run_utils.py).

用法: python tools/eval_doc_queries.py [--limit 300] [--top-k 20]
前置: python tools/gen_hypothetical_queries.py --limit 600
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.blackboard.doc_query_index import DocQueryIndex  # noqa: E402
from algorithms.blackboard.evidence_store import EvidenceStore  # noqa: E402
from eval_recall_v3 import old_search  # noqa: E402
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
RRF_K = 60              # RRF标准参数(Cormack 2009, 与hybrid_recall一致)
LEX_DEPTH = 200         # 词法通道池深(命中全收, 与hybrid_recall一致)
BM25_DEPTH = 30         # BM25通道深度(与hybrid_recall概率通道一致)
# 盲区席位校准(covered子集sweep): seats=0 → ΔR@20=+0.004, 回退0
# (纯填充语义: dq只进lex词法池填不满的空位, 严格不减); seats≥1 →
# 系统性挤掉lex池ranks17-20, 回退42/138. 600/3208覆盖期精度不足
# (~2%)支撑位移式席位; 全量覆盖后可复评(机制保留, 见cascade_fuse).
DQ_SEATS = 0
DEEP_LEVEL = 4          # 章节深度≥4 = 深层小节(盲区口径)


def rrf_fuse(channels: list[list[dict]], top_k: int,
             seen: set[str] | None = None) -> list[dict]:
    """多通道ranked list → RRF融合(RRF_K=60), 追加在seen之外的候选."""
    scores: dict[str, float] = {}
    first: dict[str, dict] = {}
    skip = seen or set()
    for ch in channels:
        for rank, h in enumerate(ch, 1):
            cid = h["chunk_id"]
            if cid in skip:
                continue
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank)
            first.setdefault(cid, h)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{**first[cid], "rrf_score": round(s, 6)}
            for cid, s in ranked[:top_k]]


def cascade_fuse(lex: list[dict], dq: list[dict], bm25: list[dict] | None,
                 top_k: int, dq_seats: int) -> list[dict]:
    """级联融合: ①lex事实直通 ②dq盲区席位 ③RRF填充.

    tier1: 词法确定性命中直通(top_k-dq_seats位), 不被概率通道推翻.
    tier2: 假想查询盲区席位 — dq命中且lex池完全没有的chunk, 这是
           docT5query作为"新证据源"的独有贡献(lex永远看不见).
    tier3: 剩余配额按RRF(lex池尾+dq[+bm25])填充.
    """
    out: list[dict] = []
    seen: set[str] = set()

    def _add(h: dict, tier: str) -> None:
        cid = h["chunk_id"]
        if cid in seen or len(out) >= top_k:
            return
        d = dict(h)
        d["rank"] = len(out) + 1
        d["tier"] = tier
        out.append(d)
        seen.add(cid)

    for h in lex[:top_k - dq_seats]:
        _add(h, "lex_factual")
    lex_pool = {h["chunk_id"] for h in lex}
    used = 0
    for h in dq:
        if used >= dq_seats or len(out) >= top_k:
            break
        if h["chunk_id"] in lex_pool:
            continue
        n0 = len(out)
        _add(h, "dq_blind")
        used += len(out) - n0
    if len(out) < top_k:
        channels = [lex[top_k - dq_seats:], dq]
        if bm25:
            channels.append(bm25)
        for h in rrf_fuse(channels, top_k, seen=seen):
            _add(h, "rrf_fill")
    return out


def recall_at(recalled: list[dict], exp_ids: set[str], k: int) -> float:
    got = {h["chunk_id"] for h in recalled[:k]}
    return len(exp_ids & got) / len(exp_ids) if exp_ids else 1.0


def _depth(section: str) -> int:
    return len([p for p in (section or "").split(".") if p])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--top-k", type=int, default=20)
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))
    queries = data[:args.limit] if isinstance(data, list) \
        else data.get("queries", [])[:args.limit]

    idx = DocQueryIndex()
    if idx.n_chunks == 0:
        print("✗ 假想查询索引为空/缺失 — 先运行: "
              "python tools/gen_hypothetical_queries.py --limit 600")
        return 1
    store = EvidenceStore()
    by_id = store._chunk_by_id()
    indexed = idx.indexed_chunk_ids
    n_total_chunks = len(store._chunks_data())
    print(f"评测: {len(queries)}条(entity作query) | 假想查询索引: "
          f"{idx.n_chunks}/{n_total_chunks} chunks")

    is_cov = [bool(set(q["expected"].get("chunk_ids") or []) & indexed)
              for q in queries]
    n_cov = sum(is_cov)
    print(f"covered子集(期望chunk∈已生成集合): {n_cov}/{len(queries)} "
          f"= {n_cov / len(queries):.0%}")

    conds = ("lex", "lex+dq", "lex+dq(rrf)", "lex+bm25", "lex+bm25+dq")
    recalls: dict[str, list[tuple[float, float]]] = {k: [] for k in conds}
    hits_lex: list[list[dict]] = []
    hits_fused: list[list[dict]] = []
    t0 = time.time()

    for q in queries:
        text = q["entity"] or q["entity_id"] or q["query"]
        lex = old_search(store, text, "", limit=LEX_DEPTH)
        bm25 = store.bm25_rank(text, top_k=BM25_DEPTH)
        dq = idx.search(text, top_k=args.top_k)
        exp_ids = set(q["expected"].get("chunk_ids") or [])
        got: dict[str, list[dict]] = {
            "lex": lex[:args.top_k],
            "lex+dq": cascade_fuse(lex, dq, None, args.top_k, DQ_SEATS),
            "lex+dq(rrf)": rrf_fuse([lex, dq], args.top_k),
            "lex+bm25": cascade_fuse(lex, [], bm25, args.top_k, 0),
            "lex+bm25+dq": cascade_fuse(lex, dq, bm25, args.top_k, DQ_SEATS),
        }
        for name in conds:
            hits = got[name]
            recalls[name].append((recall_at(hits, exp_ids, 10),
                                  recall_at(hits, exp_ids, args.top_k)))
        hits_lex.append(got["lex"])
        hits_fused.append(got["lex+dq"])

    elapsed = round(time.time() - t0, 1)

    def _avg(rows: list[tuple[float, float]]) -> dict[str, float]:
        if not rows:
            return {"recall@10": 0.0, "recall@20": 0.0}
        return {"recall@10": round(sum(r[0] for r in rows) / len(rows), 4),
                "recall@20": round(sum(r[1] for r in rows) / len(rows), 4)}

    summary_full = {k: _avg(recalls[k]) for k in conds}
    cov_rows = {k: [recalls[k][i] for i, c in enumerate(is_cov) if c]
                for k in conds}
    summary_cov = {k: _avg(cov_rows[k]) for k in conds}

    # ── 净增分析: lex vs lex+dq (covered子集) ──
    net = {"gain": 0, "zero_to_hit": 0, "regress": 0}
    gained: list[dict[str, Any]] = []
    shown: set[tuple[str, str]] = set()
    for i, q in enumerate(queries):
        if not is_cov[i]:
            continue
        r_lex, r_fused = recalls["lex"][i][1], recalls["lex+dq"][i][1]
        if r_fused > r_lex:
            net["gain"] += 1
        if r_lex == 0.0 and r_fused > 0.0:
            net["zero_to_hit"] += 1
        if r_fused < r_lex:
            net["regress"] += 1
        exp_ids = set(q["expected"].get("chunk_ids") or [])
        lex_ids = {h["chunk_id"] for h in hits_lex[i][:args.top_k]}
        for h in hits_fused[i][:args.top_k]:
            cid = h["chunk_id"]
            if cid not in exp_ids or cid in lex_ids:
                continue
            key = (q["id"], cid)
            if key in shown:
                continue
            shown.add(key)
            c = by_id.get(cid, {})
            sec = h.get("section") or c.get("section", "")
            gained.append({
                "qid": q["id"],
                "query": q.get("entity") or q.get("entity_id") or q["query"],
                "chunk_id": cid, "section": sec,
                "doc": (c.get("doc", "") or "")[:12],
                "depth": _depth(sec), "tier": h.get("tier", ""),
                "snippet": (h.get("snippet") or "")[:40],
            })
    deep = [g for g in gained if g["depth"] >= DEEP_LEVEL]
    tier_dist = Counter(g["tier"] for g in gained)
    depth_dist = Counter(g["depth"] for g in gained)

    def _table(title: str, summ: dict[str, dict[str, float]]) -> str:
        rows = [
            "| 条件 | R@10 | R@20 |",
            "|---|---|---|",
            "| 纯lexical | {:.3f} | {:.3f} |".format(
                summ["lex"]["recall@10"], summ["lex"]["recall@20"]),
            "| **lexical+假想查询(级联)** | {:.3f} | {:.3f} |".format(
                summ["lex+dq"]["recall@10"], summ["lex+dq"]["recall@20"]),
            "| lexical+假想查询(纯RRF, 消融) | {:.3f} | {:.3f} |".format(
                summ["lex+dq(rrf)"]["recall@10"],
                summ["lex+dq(rrf)"]["recall@20"]),
            "| lexical+BM25(对照) | {:.3f} | {:.3f} |".format(
                summ["lex+bm25"]["recall@10"], summ["lex+bm25"]["recall@20"]),
            "| lexical+BM25+假想查询 | {:.3f} | {:.3f} |".format(
                summ["lex+bm25+dq"]["recall@10"],
                summ["lex+bm25+dq"]["recall@20"]),
        ]
        return f"### {title}\n\n" + "\n".join(rows) + "\n"

    print()
    print(_table(f"全量{len(queries)}条", summary_full))
    print(_table(f"covered子集({n_cov}/{len(queries)}"
                 f"={n_cov / len(queries):.0%}, 期望chunk∈已生成集合)",
                 summary_cov))
    print("净增分析(lex → lex+假想查询级联, covered子集):")
    print(f"  净增query数: {net['gain']}/{n_cov}"
          f"(其中lex完全未召回→召回: {net['zero_to_hit']})")
    print(f"  回退query数: {net['regress']}/{n_cov}")
    print(f"  净增期望chunk数: {len(gained)} "
          f"(tier分布: {dict(tier_dist)}), "
          f"其中深层小节(深度≥{DEEP_LEVEL}): {len(deep)}")
    print(f"  净增chunk章节深度分布: {dict(sorted(depth_dist.items()))}")
    for g in deep[:8]:
        print(f"    · [{g['doc']} §{g['section']}(d{g['depth']}) "
              f"{g['tier']}] q=「{g['query'][:24]}」 "
              f"证据=「{g['snippet'][:30]}」")
    print(f"\n耗时{elapsed}s | top_k={args.top_k} | 盲区席位={DQ_SEATS}")

    run = open_run("eval_doc_queries", {
        "limit": args.limit, "top_k": args.top_k, "rrf_k": RRF_K,
        "lex_depth": LEX_DEPTH, "bm25_depth": BM25_DEPTH, "dq_seats": DQ_SEATS,
        "deep_level": DEEP_LEVEL, "n_indexed_chunks": idx.n_chunks,
        "n_queries": len(queries), "n_covered": n_cov,
        "coverage_ratio": round(n_cov / len(queries), 4)})
    run.save_result({
        "summary_full": summary_full, "summary_covered": summary_cov,
        "net_gain": net, "n_gained_chunks": len(gained),
        "n_gained_deep": len(deep), "gained_chunks": gained,
        "per_query": {k: [list(r) for r in recalls[k]] for k in conds},
        "elapsed_s": elapsed,
        "note": f"covered子集覆盖比例 {n_cov}/{len(queries)}"
                f"={n_cov / len(queries):.0%}; 假想查询索引 "
                f"{idx.n_chunks}/{n_total_chunks} chunks(--limit 600阶段); "
                "融合=级联(lex直通+dq盲区席位+RRF填充), 纯RRF为消融行",
    })
    print(f"结果 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
