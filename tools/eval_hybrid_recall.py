r"""多路召回(Hybrid Recall)实验: 五通道 + RRF融合 + 消融 + 分层评测.

科研汇报协议:
  指标   Recall@10/Recall@20(chunk级金标), MRR@10, section_recall,
         modality_recall(figure/table/text), entity_found(完整文本口径)
  消融   5通道全开 vs 去一通道(-dense/-sparse/-structural/
         -multimodal/-lexical) vs 单通道
  基线   v0(精确) / v2(BM25) / v3(四层优先级拼接)
  分层   按评测集difficulty(easy/hard)
  产出   控制台markdown表格 + runs协议result.json + 实验报告md

用法: python tools/eval_hybrid_recall.py [--limit 300] [--no-dense]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.blackboard.hybrid_recall import (  # noqa: E402
    CHANNELS,
    HybridRecaller,
    detect_entity,
    extract_entity,
)
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
REPORT_DIR = BASE / "docs/srs_project"

_MODAL_MAP = {"image": "figure"}   # chunks类型→评测期望模态名


def evaluate_query(recalled: list[dict], exp: dict, entity: str,
                   entity_id: str, full_texts: str,
                   k_list: tuple[int, ...] = (10, 20)) -> dict[str, float]:
    """单query指标: Recall@K, MRR@10, section/modality/entity."""
    exp_ids = set(exp.get("chunk_ids") or [])
    got_ids = [h["chunk_id"] for h in recalled]
    out: dict[str, float] = {}
    for k in k_list:
        got_k = set(got_ids[:k])
        out[f"recall@{k}"] = (len(exp_ids & got_k) / len(exp_ids)
                              if exp_ids else 1.0)
    # MRR@10: 首个命中期望chunk的倒数排名
    mrr = 0.0
    for rank, cid in enumerate(got_ids[:10], 1):
        if cid in exp_ids:
            mrr = 1.0 / rank
            break
    out["mrr@10"] = mrr
    exp_secs = {s for s in (exp.get("sections") or []) if s}
    got_secs = {h.get("section", "") for h in recalled if h.get("section")}
    out["section"] = len(exp_secs & got_secs) / max(len(exp_secs), 1)
    exp_locs = set(exp.get("locations") or [])
    got_locs = {_MODAL_MAP.get(h.get("type", ""), h.get("type", ""))
                for h in recalled}
    out["modality"] = len(exp_locs & got_locs) / max(len(exp_locs), 1)
    if entity or entity_id:
        out["entity"] = 1.0 if ((entity and entity in full_texts)
                                or (entity_id and entity_id in full_texts)) else 0.0
    else:
        out["entity"] = 1.0
    return out


def avg_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = rows[0].keys() if rows else []
    return {k: round(sum(r[k] for r in rows) / len(rows), 4) for k in keys}


def fmt_table(header: list[str], rows: list[list[str]]) -> str:
    md = ["| " + " | ".join(header) + " |",
          "|" + "|".join("---" for _ in header) + "|"]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(md)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--no-dense", action="store_true")
    ap.add_argument("--top-k", type=int, default=20)
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))
    queries = data[:args.limit] if isinstance(data, list) \
        else data.get("queries", [])[:args.limit]
    rec = HybridRecaller(use_dense=not args.no_dense)
    store = rec.store
    by_id = store._chunk_by_id()

    def full_texts_of(recalled: list[dict]) -> str:
        return " ".join((by_id.get(h.get("chunk_id"), {}).get("text") or "")
                        for h in recalled)

    configs: dict[str, tuple[str, Any]] = {}

    # 基线: v0/v2/v3
    def run_baseline(kind: str):
        rows = []
        for q in queries:
            text = q["entity"] or q["entity_id"] or q["query"]
            if kind == "v0":
                from eval_recall_v3 import old_search
                hits = old_search(store, text, "")
            elif kind == "v2":
                hits = store.search_chunks(text, "")
            else:
                hits = store.search_chunks_v3(text, "")
            rows.append(evaluate_query(hits, q["expected"], q.get("entity", ""),
                                       q.get("entity_id", ""),
                                       full_texts_of(hits)))
        return rows

    # 混合: full(rrf/cascade) / 消融 / 单通道 / 问句模式 / 重排
    def run_hybrid(channels: tuple[str, ...], fusion: str = "cascade",
                   question_mode: str = "", rerank: bool = False
                   ) -> list[dict[str, float]]:
        rows = []
        for q in queries:
            if question_mode:
                # 问句模式: 输入原始问句, 实体由查询理解层提取(不作弊)
                # detect=检索反推LCS; strip=停用词剥离(对照)
                text = (detect_entity(q["query"], store)
                        if question_mode == "detect" else
                        extract_entity(q["query"]))
            else:
                text = q["entity"] or q["entity_id"] or q["query"]
            r = rec.recall(text, "", top_k=args.top_k, channels=channels,
                           fusion=fusion, rerank=rerank)
            rows.append(evaluate_query(r["hits"], q["expected"],
                                       q.get("entity", ""),
                                       q.get("entity_id", ""),
                                       full_texts_of(r["hits"])))
        return rows

    t0 = time.time()
    for kind in ("v0", "v2", "v3"):
        configs[f"base:{kind}"] = ("基线", run_baseline(kind))
    configs["hybrid:rrf"] = ("五通道RRF", run_hybrid(CHANNELS, "rrf"))
    configs["hybrid:full"] = ("五通道cascade", run_hybrid(CHANNELS, "cascade"))
    configs["hybrid:rerank"] = ("五通道+重排", run_hybrid(
        CHANNELS, "cascade", rerank=True))
    for ch in CHANNELS:
        configs[f"ablate:-{ch}"] = (f"去{ch}", run_hybrid(
            tuple(c for c in CHANNELS if c != ch)))
        configs[f"single:{ch}"] = (f"仅{ch}", run_hybrid((ch,)))
    configs["hybrid:question"] = ("问句模式LCS反推", run_hybrid(
        CHANNELS, "cascade", "detect"))
    configs["hybrid:question_strip"] = ("问句模式停用词", run_hybrid(
        CHANNELS, "cascade", "strip"))
    configs["hybrid:question_rerank"] = ("问句+重排", run_hybrid(
        CHANNELS, "cascade", "detect", rerank=True))
    elapsed = round(time.time() - t0, 1)

    # ══ 汇总表 ══
    order = ["base:v0", "base:v2", "base:v3", "single:lexical", "single:sparse",
             "single:dense", "single:structural", "single:multimodal",
             "hybrid:rrf", "hybrid:full", "hybrid:rerank", "hybrid:question",
             "hybrid:question_strip", "hybrid:question_rerank",
             "ablate:-lexical", "ablate:-sparse",
             "ablate:-dense", "ablate:-structural", "ablate:-multimodal"]
    summary = {k: avg_metrics(rows) for k, (label, rows) in configs.items()}
    table_rows = []
    for k in order:
        if k not in summary:
            continue
        label = configs[k][0]
        m = summary[k]
        table_rows.append([label, f"{m.get('recall@10', 0):.3f}",
                           f"{m.get('recall@20', 0):.3f}",
                           f"{m.get('mrr@10', 0):.3f}",
                           f"{m.get('section', 0):.3f}",
                           f"{m.get('modality', 0):.3f}",
                           f"{m.get('entity', 0):.3f}"])
    header = ["配置", "R@10", "R@20", "MRR@10", "Sec", "Mod", "Ent"]
    table = fmt_table(header, table_rows)

    # 分层(hard)
    hard_idx = {i for i, q in enumerate(queries) if q.get("difficulty") == "hard"}
    full_rows = configs["hybrid:full"][1]
    v3_rows = configs["base:v3"][1]
    hard_full = [full_rows[i] for i in hard_idx] or full_rows
    hard_v3 = [v3_rows[i] for i in hard_idx] or v3_rows

    print(table)
    print(f"\n耗时{elapsed}s | queries={len(queries)} | dense索引"
          f" {rec.stats.get('dense_index_s', 0)}s"
          f" (缓存{rec.stats.get('dense_cache_hits', 0)}条)")

    # ══ runs协议落盘 + 报告 ══
    run = open_run("eval_hybrid_recall", {
        "limit": args.limit, "top_k": args.top_k,
        "use_dense": not args.no_dense, "channels": list(CHANNELS)})
    run.save_result({"summary": summary, "elapsed_s": elapsed,
                     "dense_stats": rec.stats,
                     "per_query": {k: rows for k, (label, rows) in configs.items()}})

    hf, hv = avg_metrics(hard_full), avg_metrics(hard_v3)
    report = f"""# 多路召回实验报告 (Hybrid Recall)

## 1 实验设置

- **数据**: retrieval_evalset 300条查询(自然语言问题→实体), 金标=期望
  chunk_ids/sections/模态/实体; 按difficulty分层(hard {len(hard_idx)}条).
- **通道**: lexical(精确子串) / sparse(BM25) / dense(BGE-large-zh, 1024维,
  检索指令前缀, 磁盘索引缓存) / structural(ID-Graph硬桥, 跨文档消歧,
  章节补全) / multimodal(VLM key_elements→image chunk).
- **融合**: cascade(默认: 事实通道最小席位直通+概率通道RRF填充) vs
  rrf(全通道等权). top-k={args.top_k}.
- **指标**: Recall@10/@20, MRR@10, section/modality/entity recall.
  (评测口径修正: entity按完整chunk文本; 模态image→figure归一;
  全库检索无doc过滤.)
- **基线**: v0精确 / v2 BM25+多跳 / v3四层优先级拼接.

## 2 主结果

{table}

## 3 难度分层(hard子集, n={len(hard_idx)})

| 配置 | R@10 | R@20 | MRR@10 | Sec | Mod | Ent |
|---|---|---|---|---|---|---|
| v3四层 | {hv.get('recall@10', 0):.3f} | {hv.get('recall@20', 0):.3f} | {hv.get('mrr@10', 0):.3f} | {hv.get('section', 0):.3f} | {hv.get('modality', 0):.3f} | {hv.get('entity', 0):.3f} |
| hybrid五通道 | {hf.get('recall@10', 0):.3f} | {hf.get('recall@20', 0):.3f} | {hf.get('mrr@10', 0):.3f} | {hf.get('section', 0):.3f} | {hf.get('modality', 0):.3f} | {hf.get('entity', 0):.3f} |

## 4 讨论

- 融合策略: rrf(民主投票)在通道强度悬殊时被弱通道稀释; cascade以
  事实性通道直通+概率通道RRF填充恢复lexical主导(详见主表对比行).
- 通道消融: 各通道边际贡献 = ablate:-X与hybrid:full的R@20差;
  structural/multimodal席位是集合判定指标(Mod/Sec)与排序指标(R@K)
  的显式权衡.
- dense索引: {rec.stats.get('dense_cache_hits', 0)}条缓存命中/
  {rec.stats.get('dense_index_s', 0)}s构建(磁盘缓存复现).

运行: {run.path.name} | {time.strftime('%Y-%m-%d %H:%M')}
"""
    rp = REPORT_DIR / "hybrid_recall_report.md"
    rp.write_text(report, encoding="utf-8")
    print(f"报告 → {rp}")
    print(f"结果 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
