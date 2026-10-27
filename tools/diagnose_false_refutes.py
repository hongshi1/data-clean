"""Diagnose which expert channels produce false refutes on the silver set."""
from __future__ import annotations

import json
from collections import Counter

from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef
from algorithms.consistency.qa_module import QAConsistencyModule


def main() -> None:
    frozen = [
        json.loads(line)
        for line in open(
            "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl", encoding="utf-8")
    ]
    labels: dict[str, str] = {}
    for line in open(
        "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
        "/final_labels.jsonl", encoding="utf-8"):
        rec = json.loads(line)
        labels[rec["instance_id"]] = rec["final_verdict"]

    module = QAConsistencyModule()
    false_refutes: list[tuple[str, str, list[str]]] = []
    for rec in frozen:
        evidence = []
        for ev in rec["evidence"]:
            sr = ev.get("source_ref", {})
            evidence.append(RetrievedEvidence(
                evidence_id=ev["evidence_id"],
                text=ev["text"],
                source_type=ev.get("source_type", "text"),
                source_ref=SourceRef(
                    doc_id=sr.get("doc_id", "04"),
                    section=sr.get("section", ""),
                    page=sr.get("page"),
                    block_id=sr.get("block_id", ""),
                ),
                scope_id=ev.get("scope_id", ""),
                completeness=ev.get("completeness", "open"),
                completeness_proof=ev.get("completeness_proof", ""),
            ))
        request = QAInput(
            instance_id=rec["instance_id"],
            question=rec["question"],
            answer=rec["answer"],
            evidence=tuple(evidence),
            context_freeze_id=rec.get("context_freeze_id", "scene1_v1"),
        )
        result = module.verify(request)
        silver = labels.get(rec["instance_id"], "?")
        if result.verdict == "refute" and silver != "refute":
            methods = sorted(
                {r.method for r in result.claim_results if r.verdict == "refute"})
            false_refutes.append((rec["instance_id"], silver, methods))

    print("false refutes:", len(false_refutes))
    method_counts = Counter(
        method for _, _, methods in false_refutes for method in methods)
    for method, count in method_counts.most_common():
        print(f"  {method}: {count}")
    print()
    for qid, silver, methods in false_refutes:
        print(f"  {qid} silver={silver} {methods}")


if __name__ == "__main__":
    main()
