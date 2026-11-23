"""ConsistencyAgent: 一致性校验agent(两级API: 总报告 + 按sample id详情).

设计:
  默认(无--ids)      → 总报告: 整个语料的总体结果 + 不一致条目聚合
  --ids ID1,ID2      → 样本详情: 每个sample的question/answer/result/
                       失败条目 + 逐条不一致明细(可钻取)

所有40项校验条目都会执行; 报告只展示不一致的条目(通过的条目
不产生噪音). 样本id即violation evalset的instance_id.

用法:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
  python tools/consistency_agent.py                        # 总报告
  python tools/consistency_agent.py --ids DOC04-VIO-02     # 单样本详情
  python tools/consistency_agent.py --ids DOC04-VIO-02,DOC04-VIO-08
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.blackboard.hybrid_recall import HybridRecaller  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.verifier import CascadeVerifier  # noqa: E402

DOC = "04数据统一访问服务软件需求规格说明-终稿"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
STORE = BASE / "data/gjb_438c/distillation/agent_scenario_v1.json"
_TITLE_PREFIX = re.compile(r"^\[表格标题[^\]]*\]")
_SENT_BOUNDARY = re.compile(r"(?<=[。！？；\n])")
K = 8
_RESULT_ZH = {"support": "一致", "refute": "不一致",
              "not_in_evidence": "无法判定"}

_TAX_NAMES: dict[str, str] | None = None


def _taxonomy_names() -> dict[str, str]:
    global _TAX_NAMES
    if _TAX_NAMES is None:
        tax = json.loads(
            (BASE / "knowledge/consistency_taxonomy_v3.json")
            .read_text(encoding="utf-8"))
        _TAX_NAMES = {str(it.get("id", "")): str(it.get("name", ""))
                      for it in tax.get("items", [])}
    return _TAX_NAMES


def _sentence_of_span(answer: str, span: tuple[int, int] | None) -> str:
    if span is None:
        return answer[:120]
    mid = (span[0] + span[1]) // 2
    parts = [p for p in _SENT_BOUNDARY.split(answer) if span[0] < len(p)]
    for part in _SENT_BOUNDARY.split(answer):
        position = answer.find(part)
        if position <= span[0] <= position + len(part):
            return part.strip()[:160]
    return answer[max(0, span[0] - 40):span[1] + 40].strip()


def recall_evidence(recaller: HybridRecaller, full: dict,
                    question: str, answer: str, iid: str) -> QAInput:
    query = f"{question} {answer[:400]}"
    result = recaller.recall(query, doc=DOC, top_k=max(10, K))
    hits = [h for h in result.get("hits", [])
            if h.get("type") in ("text", "table")][:K]
    evidences: list[RetrievedEvidence] = []
    for rank, hit in enumerate(hits, 1):
        text = _TITLE_PREFIX.sub("", full.get(
            str(hit.get("chunk_id", "")), "")).strip()
        if not text:
            continue
        evidences.append(RetrievedEvidence(
            evidence_id=f"{iid}-rec-{rank:02d}",
            text=text,
            source_type=str(hit.get("type", "text")),
            source_ref=SourceRef(
                doc_id=str(hit.get("doc", "")),
                section=str(hit.get("section", "")),
                block_id=str(hit.get("chunk_id", ""))),
            scope_id="",
            completeness="open"))
    return QAInput(
        instance_id=iid, question=question, answer=answer,
        evidence=tuple(evidences), context_freeze_id=f"agent-{iid}")


def run_sample(recaller: HybridRecaller, verifier: CascadeVerifier,
               full: dict, rec: dict) -> dict:
    """一个sample的完整三层数据: 总判定 + 失败条目 + 逐条明细."""
    iid = str(rec["instance_id"])
    start = time.perf_counter()
    request = recall_evidence(
        recaller, full, str(rec["question"]), str(rec["answer"]), iid)
    result = verifier.verify_qa_input(request)
    elapsed = (time.perf_counter() - start) * 1000
    answer = str(rec["answer"])

    names = _taxonomy_names()
    failed: dict[str, int] = {}
    details: list[dict] = []
    for loc in result.localizations:
        for item in loc.check_item_candidates or ("未分类",):
            failed[item] = failed.get(item, 0) + 1
        detail = {
            "answer_context": _sentence_of_span(answer, loc.answer_span),
            "answer_span": list(loc.answer_span) if loc.answer_span else None,
            "answer_assertion": loc.claim_text,
            "explanation": loc.rationale[:200],
        }
        if loc.evidence:
            ev = loc.evidence[0]
            detail["doc_location"] = (
                f"{ev.section}节" + (f" 第{ev.row_index}行"
                                     if ev.row_index >= 0 else ""))
            detail["doc_statement"] = ev.statement_text[:120]
        details.append(detail)

    if result.verdict == "refute":
        summary = (f"共{len(result.localizations)}处不一致，"
                   f"涉及{len(failed)}个校验条目")
    elif result.verdict == "support":
        summary = "全部校验条目通过，与文档证据一致"
    else:
        summary = "现有证据无法判定"
    return {
        "sample_id": iid,
        "question": str(rec["question"]),
        "answer": answer,
        "result": _RESULT_ZH.get(result.verdict, result.verdict),
        "summary": summary,
        "failed_checks": [{
            "item": item,
            "name": names.get(item, ""),
            "count": count,
        } for item, count in sorted(failed.items())],
        "details": details,
        "latency_ms": round(elapsed, 1),
    }


def total_report(samples: list[dict]) -> dict:
    """语料级总报告: 总体结果 + 不一致条目跨样本聚合."""
    verdicts = [s["result"] for s in samples]
    n_inconsistent = verdicts.count("不一致")
    n_consistent = verdicts.count("一致")
    n_undecidable = verdicts.count("无法判定")
    items: dict[str, dict] = {}
    for s in samples:
        for check in s["failed_checks"]:
            entry = items.setdefault(check["item"], {
                "item": check["item"], "name": check["name"], "count": 0})
            entry["count"] += check["count"]
    return {
        "n_samples": len(samples),
        "n_consistent": n_consistent,
        "n_inconsistent": n_inconsistent,
        "n_undecidable": n_undecidable,
        "result": ("不一致" if n_inconsistent else
                   "一致" if n_consistent == len(samples) else "无法判定"),
        "summary": (f"校验{len(samples)}个样本: "
                    f"{n_consistent}一致 / {n_inconsistent}不一致 / "
                    f"{n_undecidable}无法判定; "
                    f"不一致集中在{len(items)}个校验条目"),
        "failing_items": sorted(items.values(),
                                key=lambda x: -x["count"]),
        "sample_ids": [s["sample_id"] for s in samples],
    }


def build_agent() -> tuple[HybridRecaller, CascadeVerifier, dict]:
    from algorithms.blackboard.evidence_store import EvidenceStore
    recaller = HybridRecaller()
    recaller.recall("数据库访问", doc=DOC, top_k=5)
    full = {cid: str(chunk.get("text", ""))
            for cid, chunk in EvidenceStore()._chunk_by_id().items()}
    verifier = CascadeVerifier(preset="standard", scene="srs_scene1")
    return recaller, verifier, full


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="",
                        help="逗号分隔sample id(空=总报告)")
    args = parser.parse_args()

    vio = [json.loads(line) for line in
           VIO.read_text(encoding="utf-8").splitlines() if line.strip()]
    recaller, verifier, full = build_agent()

    if args.ids:
        wanted = {s.strip() for s in args.ids.split(",") if s.strip()}
        selected = [r for r in vio if str(r["instance_id"]) in wanted]
        missing = wanted - {str(r["instance_id"]) for r in selected}
        if missing:
            raise SystemExit(f"未知sample id: {sorted(missing)}")
        for rec in selected:
            sample = run_sample(recaller, verifier, full, rec)
            print(json.dumps(sample, ensure_ascii=False, indent=1))
        return

    samples = [run_sample(recaller, verifier, full, rec) for rec in vio]
    report = total_report(samples)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps({"total": report, "samples": samples},
                                ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"→ 明细已存 {STORE}", file=sys.stderr)


if __name__ == "__main__":
    main()
