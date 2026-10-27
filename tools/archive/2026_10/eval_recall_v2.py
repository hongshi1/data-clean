#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""召回能力评测v2: 300条评测集上 新旧召回路径对比(提升的证据).

旧路径(tier1): 精确子串 + "前2关键词全部命中"过滤 — 排版变体直接漏
新路径: tier1 + BM25排序(部分命中即可) + ID-mention章节多跳

指标(与eval_retrieval同口径): entity_found / section_recall / loc_recall / avg
基线: M5双图融合 1.0/0.5/0.926/0.809(历史数字)

用法: python tools/eval_recall_v2.py [--limit 300]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from algorithms.blackboard.evidence_store import EvidenceStore  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"


def old_search(store: EvidenceStore, text: str, doc: str = "",
               limit: int = 20) -> list[dict]:
    """旧路径(tier1): 精确子串 + 双关键词全命中(黑板的v0逻辑)."""
    if not text:
        return []
    hits = []
    keywords = [p for p in re.split(r"[的、和与及,，。;；]", text)
                if len(p) >= 2 and p not in ("这个", "那个", "文档", "系统", "功能")]
    for c in store._chunks_data():
        if doc and c.get("doc", "") != doc:
            continue
        ct = c.get("text", "")
        hit = text in ct
        if not hit and len(keywords) >= 2 and all(k in ct for k in keywords[:2]):
            hit = True
        if hit:
            hits.append({"chunk_id": c.get("chunk_id", ""),
                         "type": c.get("type", "text"),
                         "section": c.get("section", ""),
                         "doc": c.get("doc", ""),
                         "snippet": ct[:80]})
        if len(hits) >= limit:
            break
    return hits


def metrics(recalled: list[dict], exp: dict, entity: str, entity_id: str
            ) -> tuple[float, float, float]:
    """(entity_found, section_recall, loc_recall)."""
    texts = " ".join(o.get("snippet", "") for o in recalled)
    found = 1.0 if ((entity and entity in texts)
                    or (entity_id and entity_id in texts)) else 0.0
    exp_secs = {s for s in exp.get("sections", []) if s}
    got_secs = {o.get("section", "") for o in recalled if o.get("section")}
    sec = len(exp_secs & got_secs) / max(len(exp_secs), 1)
    exp_locs = set(exp.get("locations", []))
    got_locs = {o.get("type", "") for o in recalled}
    loc = len(exp_locs & got_locs) / max(len(exp_locs), 1)
    return found, sec, loc


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))
    queries = data[:args.limit] if isinstance(data, list) else data.get("queries", [])[:args.limit]
    store = EvidenceStore()

    agg = {"old": [0.0, 0.0, 0.0, 0], "new": [0.0, 0.0, 0.0, 0]}
    n = 0
    for q in queries:
        entity = q.get("entity", "")
        entity_id = q.get("entity_id", "") or None
        exp = q.get("expected", {})
        doc = (exp.get("docs") or [""])[0] or ""
        # 旧路径
        old_hits = old_search(store, entity, doc)
        # 新路径: tier1+BM25 + ID章节多跳
        new_hits = store.search_chunks(entity, doc)
        if entity_id:
            rec = store.entity_mentions(entity_id)
            if rec:
                hop = store.section_chunks(rec.get("sections", []), doc=doc)
                seen = {h["chunk_id"] for h in new_hits}
                new_hits = new_hits + [h for h in hop
                                       if h["chunk_id"] not in seen]
        if not new_hits and not old_hits:
            continue                     # 双空不计(评测集已知的循环缺陷)
        for key, hits in (("old", old_hits), ("new", new_hits)):
            f, s, lo = metrics(hits, exp, entity, entity_id or "")
            agg[key][0] += f
            agg[key][1] += s
            agg[key][2] += lo
        agg["old"][3] += 1
        agg["new"][3] += 1
        n += 1

    print("=" * 64)
    print(f"召回评测v2 (retrieval_evalset, {n}条)")
    print(f"{'路径':<12}{'entity_found':>14}{'section_recall':>16}"
          f"{'loc_recall':>12}{'avg_recall':>12}")
    for key, label in (("old", "旧(tier1)"), ("new", "新(BM25+多跳)")):
        f, s, lo, cnt = agg[key]
        k = max(cnt, 1)
        avg = (f / k + s / k + lo / k) / 3
        print(f"{label:<12}{f / k:>14.3f}{s / k:>16.3f}{lo / k:>12.3f}{avg:>12.3f}")
    print("\n历史基线 M5双图融合: entity=1.000 section=0.500 loc=0.926 avg=0.809")
    o_avg = (agg["old"][0] + agg["old"][1] + agg["old"][2]) / max(agg["old"][3] * 3, 1)
    n_avg = (agg["new"][0] + agg["new"][1] + agg["new"][2]) / max(agg["new"][3] * 3, 1)
    print(f"新旧对比: section_recall {agg['old'][1] / max(agg['old'][3], 1):.3f} → "
          f"{agg['new'][1] / max(agg['new'][3], 1):.3f} "
          f"({(agg['new'][1] / max(agg['new'][3], 1)) - (agg['old'][1] / max(agg['old'][3], 1)):+.3f})")
    print(f"          avg_recall    {o_avg:.3f} → {n_avg:.3f} ({n_avg - o_avg:+.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
