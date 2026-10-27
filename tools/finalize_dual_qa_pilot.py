"""Validate and merge GPT-in-session and GLM frozen-QA pilot annotations."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
RUN = BASE / "data/gjb_438c/runs/annotate_frozen_qa_dual_llm_72379ff3_20261021_122221"
GPT_RUN = BASE / "data/gjb_438c/runs/annotate_frozen_qa_dual_llm_a10b1812_20261021_114625"
FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
GPT_BATCHES = (
    GPT_RUN / "raw_gpt_batch_001_030.jsonl",
    GPT_RUN / "raw_gpt_batch_031_060.jsonl",
    GPT_RUN / "raw_gpt_batch_061_091.jsonl",
)
GPT_OUT = RUN / "raw_gpt5_6_sol.jsonl"
GLM_IN = RUN / "raw_glm.jsonl"
REPORT_OUT = RUN / "comparison_report.json"
VALID_VERDICTS = {"support", "refute", "not_in_evidence"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def aggregate_claims(claims: list[dict[str, Any]]) -> str:
    labels = {claim["verdict"] for claim in claims}
    if "refute" in labels:
        return "refute"
    if "not_in_evidence" in labels:
        return "not_in_evidence"
    return "support"


def cohen_kappa(left: list[str], right: list[str]) -> float | None:
    if not left or len(left) != len(right):
        return None
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    counts_left, counts_right = Counter(left), Counter(right)
    expected = sum(counts_left[label] * counts_right[label]
                   for label in VALID_VERDICTS) / len(left) ** 2
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def validate_rows(rows: list[dict[str, Any]],
                  frozen: dict[str, dict[str, Any]], *, expected_model: str) -> None:
    ids: list[str] = []
    for row in rows:
        instance_id = row.get("instance_id")
        if instance_id not in frozen:
            raise ValueError(f"unknown instance_id: {instance_id}")
        ids.append(instance_id)
        if row.get("status") != "ok" or row.get("overall_verdict") not in VALID_VERDICTS:
            raise ValueError(f"invalid annotation status/verdict: {instance_id}")
        if row.get("model_id") != expected_model:
            raise ValueError(f"unexpected annotator model for {instance_id}: {row.get('model_id')}")
        claims = row.get("claims")
        if not isinstance(claims, list) or not claims:
            raise ValueError(f"missing atomic claims: {instance_id}")
        for claim in claims:
            if claim.get("verdict") not in VALID_VERDICTS:
                raise ValueError(f"invalid claim verdict: {instance_id}")
            if not isinstance(claim.get("claim_text"), str) or not claim["claim_text"].strip():
                raise ValueError(f"empty claim text: {instance_id}")
            refs = claim.get("evidence_refs")
            if not isinstance(refs, list):
                raise ValueError(f"evidence_refs must be a list: {instance_id}")
            allowed = {evidence["evidence_id"] for evidence in frozen[instance_id]["evidence"]}
            if not set(refs) <= allowed:
                raise ValueError(f"unknown evidence reference: {instance_id}")
        if aggregate_claims(claims) != row["overall_verdict"]:
            raise ValueError(f"QA verdict does not match frozen aggregation rule: {instance_id}")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate annotation instance_id")


def main() -> None:
    frozen_rows = read_jsonl(FROZEN)
    frozen = {row["instance_id"]: row for row in frozen_rows}
    gpt = [row for path in GPT_BATCHES for row in read_jsonl(path)]
    glm = read_jsonl(GLM_IN)
    aggregation_corrections = []
    for row in gpt + glm:
        if row.get("status") != "ok":
            continue
        computed = aggregate_claims(row["claims"])
        if row.get("overall_verdict") != computed:
            aggregation_corrections.append({
                "instance_id": row["instance_id"],
                "annotator_id": row.get("annotator_id"),
                "recorded": row.get("overall_verdict"),
                "computed_from_claims": computed,
            })
            row["overall_verdict"] = computed
            row.setdefault("diagnostics", {})["aggregation_corrected_deterministically"] = True
    validate_rows(gpt, frozen, expected_model="gpt-5.6-sol (in-session)")
    valid_glm = [row for row in glm
                 if row.get("status") == "ok" and row.get("model_id") == "glm-5"]
    validate_rows(valid_glm, frozen, expected_model="glm-5")
    if {row["instance_id"] for row in gpt} != set(frozen):
        raise ValueError("GPT annotation coverage does not match frozen asset")
    if len({row["instance_id"] for row in valid_glm}) != len(valid_glm):
        raise ValueError("duplicate valid GLM instance")

    gpt_by_id = {row["instance_id"]: row for row in gpt}
    glm_by_id = {row["instance_id"]: row for row in valid_glm}
    common = sorted(set(gpt_by_id) & set(glm_by_id))
    agree = [instance_id for instance_id in common
             if gpt_by_id[instance_id]["overall_verdict"]
             == glm_by_id[instance_id]["overall_verdict"]]
    disagreements = []
    claim_review = []
    for instance_id in common:
        left, right = gpt_by_id[instance_id], glm_by_id[instance_id]
        if left["overall_verdict"] != right["overall_verdict"]:
            disagreements.append({
                "instance_id": instance_id,
                "gpt_verdict": left["overall_verdict"],
                "glm_verdict": right["overall_verdict"],
                "gpt_claims": left["claims"],
                "glm_claims": right["claims"],
            })
        left_claims = {claim["claim_text"]: claim for claim in left["claims"]}
        right_claims = {claim["claim_text"]: claim for claim in right["claims"]}
        differing = [text for text in left_claims.keys() & right_claims.keys()
                     if left_claims[text]["verdict"] != right_claims[text]["verdict"]
                     or set(left_claims[text]["evidence_refs"])
                     != set(right_claims[text]["evidence_refs"])]
        only_gpt = sorted(left_claims.keys() - right_claims.keys())
        only_glm = sorted(right_claims.keys() - left_claims.keys())
        if differing or only_gpt or only_glm:
            claim_review.append({
                "instance_id": instance_id,
                "exact_text_verdict_or_ref_mismatches": differing,
                "claims_only_in_gpt_segmentation": only_gpt,
                "claims_only_in_glm_segmentation": only_glm,
            })

    gpt_dist = Counter(row["overall_verdict"] for row in gpt)
    glm_dist = Counter(row["overall_verdict"] for row in valid_glm)
    per_label = {
        label: sum(gpt_by_id[i]["overall_verdict"] == label
                   and glm_by_id[i]["overall_verdict"] == label for i in common)
        for label in sorted(VALID_VERDICTS)
    }
    gpt_labels = [gpt_by_id[i]["overall_verdict"] for i in common]
    glm_labels = [glm_by_id[i]["overall_verdict"] for i in common]
    report = {
        "pilot": True,
        "gold_label": None,
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "n_frozen": len(frozen),
        "annotators": {
            "gpt": {"model": "gpt-5.6-sol (in-session)", "valid": len(gpt),
                    "distribution": dict(gpt_dist)},
            "glm": {"model": "glm-5", "valid": len(valid_glm),
                    "invalid_or_wrong_model": len(glm) - len(valid_glm),
                    "distribution": dict(glm_dist)},
        },
        "n_valid_pairs": len(common),
        "qa_agreement": {"agree": len(agree), "disagree": len(common) - len(agree),
                         "rate": len(agree) / len(common) if common else None,
                         "same_label_pair_counts": per_label,
                         "cohen_kappa": cohen_kappa(gpt_labels, glm_labels),
                         "kappa_note": "Undefined when expected agreement equals one."},
        "qa_disagreements_for_adjudication": disagreements,
        "claim_alignment_review": claim_review,
        "aggregation_corrections": aggregation_corrections,
        "gpt_rows": str(GPT_OUT.relative_to(BASE)).replace("\\", "/"),
        "glm_rows": str(GLM_IN.relative_to(BASE)).replace("\\", "/"),
        "protocol": {
            "claim_first": True,
            "aggregation": "any refute -> refute; otherwise any not_in_evidence -> not_in_evidence; otherwise support",
            "open_context_absence_is_refute": False,
            "invalid_rows_are_guessed": False,
            "claim_text_alignment": "exact string only; segmentation differences are separately queued, not silently aligned",
            "warning": "GPT is an in-session annotator, not an independent API run. GLM invalid rows are excluded. This is not gold until manual adjudication.",
        },
    }
    GPT_OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in gpt),
                       encoding="utf-8")
    GLM_IN.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in glm),
                       encoding="utf-8")
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(json.dumps({
        "frozen": len(frozen), "gpt": len(gpt), "glm_valid": len(valid_glm),
        "valid_pairs": len(common), "qa_agreement": report["qa_agreement"]["rate"],
        "qa_disagreements": len(disagreements), "claim_alignment_review": len(claim_review),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
