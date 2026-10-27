"""Independent dual-provider annotation for frozen QA answers.

This module deliberately defines a new contract.  It does not import legacy
annotation, mutation, pair, or multimodal tooling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.common.llm_client import llm_json
from ai_config import GLM_MODEL, KIMI_MODEL
from tools.run_utils import open_run

LABELS = {"support", "refute", "not_in_evidence"}
CLAIM_KEYS = {
    "claim_id", "claim_text", "verdict", "evidence_refs", "check_items",
    "rationale", "confidence",
}
EVIDENCE_KEYS = {
    "evidence_id", "text", "source_ref", "scope_id", "completeness",
    "completeness_proof",
}
EXPECTED_MODELS = {"kimi": KIMI_MODEL, "glm": GLM_MODEL}

SYSTEM_PROMPT = """You are an independent evidence auditor. Return JSON only.
Judge only whether the answer's claims are supported by the frozen evidence.
Do not infer from world knowledge or from the question alone. GJB rules may be
used only when an evidence passage explicitly states that rule.
"""


def build_prompt(row: dict[str, Any], annotator_id: str) -> str:
    """Create the only model-visible input; no hidden or peer fields are copied."""
    visible = {
        "instance_id": row.get("instance_id", ""),
        "question": row.get("question", ""),
        "answer": row.get("answer", ""),
        "evidence": [
            {key: evidence.get(key) for key in EVIDENCE_KEYS if key in evidence}
            for evidence in row.get("evidence", [])
        ],
    }
    return (
        f"Annotator id: {annotator_id}\n"
        "Annotator ids are not peer outputs and must not be discussed.\n"
        "Rules:\n"
        "- support requires explicit evidence for the claim.\n"
        "- refute requires an explicit contradiction or a proven closed-scope "
        "exclusion.\n"
        "- absence in an open or incomplete context is not_in_evidence, never "
        "refute.\n"
        "- a closed scope permits exclusion only when the evidence proves the "
        "scope is exhaustive for the question.\n"
        "- cite only evidence_id values from the supplied evidence.\n"
        "- split the answer into atomic claims; do not silently repair it.\n"
        "Return exactly this JSON shape (no markdown):\n"
        '{"overall_verdict":"support|refute|not_in_evidence",'
        '"claims":[{"claim_id":"c1","claim_text":"...",'
        '"verdict":"support|refute|not_in_evidence",'
        '"evidence_refs":["evidence_id"],"check_items":["..."],'
        '"rationale":"...","confidence":0.0}],'
        '"diagnostics":{"...":"..."}}\n\n'
        + json.dumps(visible, ensure_ascii=False, indent=2)
    )


def validate_input(row: dict[str, Any]) -> list[str]:
    errors = []
    for key in ("instance_id", "question", "answer", "evidence"):
        if key not in row:
            errors.append(f"missing input field: {key}")
    if not isinstance(row.get("evidence"), list):
        errors.append("evidence must be a list")
    else:
        for index, evidence in enumerate(row["evidence"]):
            if not isinstance(evidence, dict):
                errors.append(f"evidence[{index}] must be an object")
                continue
            for key in ("source_ref", "scope_id", "completeness"):
                if key not in evidence:
                    errors.append(f"evidence[{index}] missing {key}")
    return errors


def validate_annotation(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["output must be an object"]
    required = {"overall_verdict", "claims", "diagnostics"}
    errors = [f"missing output field: {key}" for key in required - value.keys()]
    if value.get("overall_verdict") not in LABELS:
        errors.append("invalid overall_verdict")
    if not isinstance(value.get("claims"), list):
        errors.append("claims must be a list")
    else:
        for index, claim in enumerate(value["claims"]):
            if not isinstance(claim, dict):
                errors.append(f"claims[{index}] must be an object")
                continue
            errors.extend(
                f"claims[{index}] missing {key}"
                for key in CLAIM_KEYS - claim.keys()
            )
            if claim.get("verdict") not in LABELS:
                errors.append(f"claims[{index}] invalid verdict")
            if not isinstance(claim.get("evidence_refs"), list):
                errors.append(f"claims[{index}] evidence_refs must be a list")
            if not isinstance(claim.get("check_items"), list):
                errors.append(f"claims[{index}] check_items must be a list")
            if not isinstance(claim.get("claim_id"), str) or not claim.get("claim_id", "").strip():
                errors.append(f"claims[{index}] claim_id must be a non-empty string")
            if not isinstance(claim.get("claim_text"), str) or not claim.get("claim_text", "").strip():
                errors.append(f"claims[{index}] claim_text must be a non-empty string")
            if not isinstance(claim.get("rationale"), str):
                errors.append(f"claims[{index}] rationale must be a string")
            if not isinstance(claim.get("confidence"), (int, float)) or not 0 <= claim.get("confidence", -1) <= 1:
                errors.append(f"claims[{index}] invalid confidence")
    if not isinstance(value.get("diagnostics"), (dict, list)):
        errors.append("diagnostics must be an object or list")
    return errors


def validate_evidence_refs(value: dict[str, Any], row: dict[str, Any]) -> list[str]:
    """Reject citations that are not present in this frozen QA input."""
    evidence_ids = {
        evidence.get("evidence_id") for evidence in row.get("evidence", [])
    }
    errors: list[str] = []
    for index, claim in enumerate(value.get("claims", [])):
        for evidence_id in claim.get("evidence_refs", []):
            if not isinstance(evidence_id, str) or evidence_id not in evidence_ids:
                errors.append(
                    f"claims[{index}] evidence_refs contains unknown evidence_id"
                )
    return errors


def error_annotation(errors: list[str], annotator_id: str, model_id: str) -> dict[str, Any]:
    return {
        "status": "error",
        "overall_verdict": None,
        "claims": [],
        "diagnostics": {"errors": errors, "abstain": True},
        "annotator_id": annotator_id,
        "model_id": model_id,
    }


def annotate_row(row: dict[str, Any], annotator_id: str, model: str, dry_run: bool = False) -> dict[str, Any]:
    errors = validate_input(row)
    if errors:
        return error_annotation(errors, annotator_id, model)
    prompt = build_prompt(row, annotator_id)
    if dry_run:
        return {"status": "dry_run", "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "annotator_id": annotator_id, "model_id": model}
    try:
        result, used_model = llm_json(
            prompt, system=SYSTEM_PROMPT, prefer=model, cache=True,
            allow_fallback=False,
        )
    except Exception as exc:
        return error_annotation([f"llm error: {exc}"], annotator_id, model)
    errors = validate_annotation(result) + validate_evidence_refs(result, row)
    expected_model = EXPECTED_MODELS.get(model)
    if expected_model and used_model != expected_model:
        errors.append(
            f"provider identity mismatch: requested {model}, received {used_model}"
        )
    if errors:
        return error_annotation(errors, annotator_id, used_model)
    return {"status": "ok", **result, "annotator_id": annotator_id, "model_id": used_model}


def cohen_kappa(left: list[str], right: list[str]) -> float | None:
    if not left or len(left) != len(right):
        return None
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    counts_a, counts_b = Counter(left), Counter(right)
    expected = sum(counts_a[label] * counts_b[label] for label in LABELS) / len(left) ** 2
    if math.isclose(1 - expected, 0):
        return None
    return (observed - expected) / (1 - expected)


def compare_annotations(rows_by_model: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    models = list(rows_by_model)
    if len(models) < 2:
        return {"models": models, "per_label_agreement": {}, "cohen_kappa": None, "disagreements": [], "invalid_error_counts": {model: sum(row.get("status") != "ok" for row in values.values()) for model, values in rows_by_model.items()}, "gold_label": None}
    left, right = (rows_by_model[models[0]], rows_by_model[models[1]])
    common = sorted(set(left) & set(right))
    valid = [key for key in common if left[key].get("status") == right[key].get("status") == "ok"]
    labels_a = [left[key]["overall_verdict"] for key in valid]
    labels_b = [right[key]["overall_verdict"] for key in valid]
    disagreements = [{"instance_id": key, "labels": [left[key]["overall_verdict"], right[key]["overall_verdict"]]} for key in valid if left[key]["overall_verdict"] != right[key]["overall_verdict"]]
    return {"models": models, "n_common": len(common), "n_valid_pairs": len(valid), "per_label_agreement": {label: sum(a == b == label for a, b in zip(labels_a, labels_b)) for label in LABELS}, "cohen_kappa": cohen_kappa(labels_a, labels_b), "disagreements": disagreements, "invalid_error_counts": {model: sum(row.get("status") != "ok" for row in rows_by_model[model].values()) for model in models}, "gold_label": None}


def load_rows(path: Path, limit: int | None) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def load_existing_annotations(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        instance_id = value.get("instance_id")
        if isinstance(instance_id, str) and instance_id:
            result[instance_id] = value
    return result


def write_annotations(path: Path, rows: list[dict[str, Any]],
                      annotations: dict[str, dict[str, Any]]) -> None:
    ordered = [annotations[row["instance_id"]] for row in rows
               if row["instance_id"] in annotations]
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in ordered),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--models", default="kimi,glm")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume-run", type=Path,
                        help="resume an existing run directory without repeating completed rows")
    parser.add_argument("--retry-errors", action="store_true",
                        help="retry rows recorded with invalid/error annotations")
    args = parser.parse_args()
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    rows = load_rows(args.input, args.limit)
    config = {"input": str(args.input), "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(), "models": models, "limit": args.limit, "dry_run": args.dry_run}
    if args.resume_run:
        run_path = args.resume_run.resolve()
        if not run_path.is_dir():
            raise ValueError(f"resume run directory does not exist: {run_path}")
        class ExistingRun:
            path = run_path

            def write_text(self, name: str, text: str) -> Path:
                target = self.path / name
                target.write_text(text, encoding="utf-8")
                return target

            def save_result(self, obj: Any) -> Path:
                return self.write_text("result.json", json.dumps(
                    obj, ensure_ascii=False, indent=1))

        run = ExistingRun()
    else:
        run = open_run("annotate_frozen_qa_dual_llm", config, root=args.output_root)
    by_model = {}
    for model in models:
        path = run.path / f"raw_{model}.jsonl"
        annotations = load_existing_annotations(path)
        expected_model = EXPECTED_MODELS.get(model)
        annotations = {
            instance_id: annotation
            for instance_id, annotation in annotations.items()
            if annotation.get("status") == "ok"
            and (expected_model is None or annotation.get("model_id") == expected_model)
        }
        if args.retry_errors:
            previous = load_existing_annotations(path)
            for instance_id, annotation in previous.items():
                if (annotation.get("status") != "ok"
                        or (expected_model is not None
                            and annotation.get("model_id") != expected_model)):
                    annotations.pop(instance_id, None)
        pending = [row for row in rows if row.get("instance_id") not in annotations]
        write_annotations(path, rows, annotations)
        for row in pending:
            annotation = annotate_row(row, f"dual_qa_{model}", model, args.dry_run)
            annotation["instance_id"] = row.get("instance_id", f"line-{len(annotations) + 1}")
            annotations[annotation["instance_id"]] = annotation
            write_annotations(path, rows, annotations)
        by_model[model] = annotations
    report = compare_annotations(by_model)
    run.write_text("comparison_report.json", json.dumps(report, ensure_ascii=False, indent=2))
    run.save_result({"n_input": len(rows), "models": models, "comparison_report": "comparison_report.json", "gold_label": None})
    print(run.path)


if __name__ == "__main__":
    main()
