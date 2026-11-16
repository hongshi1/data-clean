"""ConsistencyAgent: 部署级一致性校验agent（真实场景闭环）.

场景: 一个RAG/需求文档问答系统产出了answer, 校验agent负责判定
answer与SRS文档证据的一致性, 并输出**结构化不一致定位报告**:

    (question, answer)
        → [召回前端] hybrid_recall五通道 (doc范围限定, top-k)
        → [验证核] CascadeVerifier (域自适应preset: standard/crossdoc)
        → [定位报告] verdict + per-claim InconsistencyLocalization
           (claim文本+answer span+证据块/行/字段+冲突说明)

用法:
  批量评测模式(E3协议, 违例检出+定位质量):
    $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
    python tools/consistency_agent.py --eval violations
  单实例演示模式(JSON报告):
    python tools/consistency_agent.py --demo <instance_id>
"""
from __future__ import annotations

import argparse
import json
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
_TITLE_PREFIX = __import__("re").compile(r"^\[表格标题[^\]]*\]")
K = 8


def recall_evidence(recaller: HybridRecaller, full: dict,
                    question: str, answer: str, iid: str
                    ) -> tuple[QAInput, list[dict]]:
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
    request = QAInput(
        instance_id=iid, question=question, answer=answer,
        evidence=tuple(evidences),
        context_freeze_id=f"agent-{iid}")
    return request, hits


def build_agent() -> tuple[HybridRecaller, CascadeVerifier, dict]:
    from algorithms.blackboard.evidence_store import EvidenceStore
    recaller = HybridRecaller()
    recaller.recall("数据库访问", doc=DOC, top_k=5)  # warmup
    full = {cid: str(chunk.get("text", ""))
            for cid, chunk in EvidenceStore()._chunk_by_id().items()}
    verifier = CascadeVerifier(preset="standard", scene="srs_scene1")
    return recaller, verifier, full


def agent_report(recaller: HybridRecaller, verifier: CascadeVerifier,
                 full: dict, question: str, answer: str, iid: str) -> dict:
    start = time.perf_counter()
    request, hits = recall_evidence(recaller, full, question, answer, iid)
    result = verifier.verify_qa_input(request)
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "instance_id": iid,
        "verdict": result.verdict,
        "latency_ms": round(elapsed, 1),
        "n_recalled_evidence": len(request.evidence),
        "recalled_sections": sorted({str(h.get("section", ""))[:12]
                                     for h in hits}),
        "inconsistencies": [{
            "claim": loc.claim_text,
            "answer_span": loc.answer_span,
            "check_items": list(loc.check_item_candidates),
            "detector": loc.method,
            "confidence": loc.confidence,
            "evidence": [{
                "block": ev.block_id,
                "section": ev.section,
                "row": ev.row_index,
                "field": ev.field_name,
                "statement": ev.statement_text[:80],
            } for ev in loc.evidence],
            "rationale": loc.rationale[:160],
        } for loc in result.localizations],
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval", default="",
                        choices=["", "violations"])
    parser.add_argument("--demo", default="",
                        help="单实例演示(violation evalset的instance_id)")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    recaller, verifier, full = build_agent()
    vio = [json.loads(line) for line in
           VIO.read_text(encoding="utf-8").splitlines() if line.strip()]

    if args.demo:
        rec = next((r for r in vio if r["instance_id"] == args.demo), vio[0])
        report = agent_report(recaller, verifier, full,
                              str(rec["question"]), str(rec["answer"]),
                              str(rec["instance_id"]))
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return

    if args.eval == "violations":
        detected = 0
        localized = 0
        gold_hit = 0
        reports: list[dict] = []

        def _chunk_to_block(chunk_id: str) -> str:
            pos = chunk_id.rfind("_T")
            if pos < 0:
                return ""
            tail = chunk_id[pos + 2:].split("_")[0]
            if not tail.isdigit():
                return ""
            return f"block-{int(tail):06d}"

        for rec in vio:
            report = agent_report(recaller, verifier, full,
                                  str(rec["question"]),
                                  str(rec["answer"]),
                                  str(rec["instance_id"]))
            reports.append(report)
            if report["verdict"] == "refute":
                detected += 1
            gold_blocks = {str((ev.get("source_ref") or {}).get(
                "block_id", "")) for ev in rec["evidence"]
                if str((ev.get("source_ref") or {}).get(
                    "block_id", "")).startswith("block-")}
            cited = {_chunk_to_block(e["block"])
                     for r in report["inconsistencies"]
                     for e in r["evidence"] if r["evidence"]}
            cited.discard("")
            if report["inconsistencies"]:
                localized += 1
            if gold_blocks and (cited & gold_blocks):
                gold_hit += 1
        out = {
            "protocol": "E3-style: recall→verify→localize (standard preset)",
            "n": len(vio),
            "refute_detected": detected,
            "with_localization": localized,
            "gold_block_hit": gold_hit,
            "reports": reports,
        }
        print(f"一致性agent端到端(violations-17): "
              f"检出 {detected}/17 | 有定位报告 {localized} | "
              f"定位命中gold块 {gold_hit}")
        target = (BASE / "data/gjb_438c/distillation"
                  / "agent_scenario_v1.json")
        target.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        print(f"→ {target}")


if __name__ == "__main__":
    main()
