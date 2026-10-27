"""Materialize final labels with GLM-5.3 review precedence and explicit gaps."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "data/gjb_438c/runs"
SOURCE_RUN = ROOT / "annotate_frozen_qa_dual_llm_72379ff3_20261021_122221"
REVIEW_RUN = ROOT / "review_qa_with_glm53_582b51e5_20261021_145212"
OUT = REVIEW_RUN / "final_labels.jsonl"
SUMMARY = REVIEW_RUN / "final_summary.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def aggregate_claims(claims: list[dict[str, Any]]) -> str:
    labels = {claim["verdict"] for claim in claims}
    if "refute" in labels:
        return "refute"
    if "not_in_evidence" in labels:
        return "not_in_evidence"
    return "support"


def main() -> None:
    frozen = load_jsonl(BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
    gpt = {row["instance_id"]: row
           for row in load_jsonl(SOURCE_RUN / "raw_gpt5_6_sol.jsonl")}
    glm = {row["instance_id"]: row for row in load_jsonl(SOURCE_RUN / "raw_glm.jsonl")}
    review_rows = load_jsonl(REVIEW_RUN / "glm53_reviews.jsonl")
    review: dict[str, dict[str, Any]] = {}
    for row in review_rows:
        if row.get("status") == "ok" and row.get("model_id") == "glm-5.3":
            review[row["instance_id"]] = row

    final = []
    status_counts: Counter[str] = Counter()
    aggregation_corrections = []
    for source in frozen:
        instance_id = source["instance_id"]
        review_row = review.get(instance_id)
        old_glm = glm.get(instance_id, {})
        if review_row:
            status = "final_glm53_reviewed"
            verdict = review_row["overall_verdict"]
            claims = review_row["claims"]
            model = "glm-5.3"
            rationale_source = "targeted_glm53_review"
            computed = aggregate_claims(claims)
            if verdict != computed:
                aggregation_corrections.append({
                    "instance_id": instance_id,
                    "recorded": verdict,
                    "computed_from_claims": computed,
                })
                verdict = computed
                rationale_source = "targeted_glm53_review_aggregation_corrected"
        elif old_glm.get("status") == "ok" and old_glm.get("model_id") == "glm-5":
            status = "final_glm5_not_re_reviewed"
            verdict = old_glm["overall_verdict"]
            claims = old_glm["claims"]
            model = "glm-5"
            rationale_source = "original_glm5_annotation"
        else:
            status = "unresolved_glm53_review_failed"
            verdict = None
            claims = []
            model = "glm-5.3"
            rationale_source = "no_valid_schema_output"
        status_counts[status] += 1
        final.append({
            "instance_id": instance_id,
            "status": status,
            "final_verdict": verdict,
            "final_model": model,
            "label_source": rationale_source,
            "claims": claims,
            "prior_gpt_verdict": gpt.get(instance_id, {}).get("overall_verdict"),
            "prior_glm5_verdict": old_glm.get("overall_verdict"),
            "glm53_review_status": review_row.get("status") if review_row else None,
            "review_thinking": review_row.get("thinking") if review_row else None,
        })
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in final),
                   encoding="utf-8")
    SUMMARY.write_text(json.dumps({
        "n_frozen": len(frozen),
        "status_counts": dict(status_counts),
        "final_labels": dict(Counter(row["final_verdict"] for row in final
                                      if row["final_verdict"] is not None)),
        "unresolved_ids": [row["instance_id"] for row in final
                           if row["final_verdict"] is None],
        "aggregation_corrections": aggregation_corrections,
        "policy": "Use valid GLM-5.3 thinking review when available; otherwise retain schema-valid original GLM-5 only when no valid review exists; failed GLM-5.3 review remains unresolved. No GPT majority vote is used.",
        "gold_label": None,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "n": len(final), "status_counts": dict(status_counts),
        "valid_glm53": len(review), "unresolved": status_counts["unresolved_glm53_review_failed"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
