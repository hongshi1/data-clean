"""Re-review QA disagreements and missing GLM labels with GLM-5.3 thinking."""
from __future__ import annotations

import hashlib
import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.common.llm_client import llm_json  # noqa: E402
from tools.annotate_frozen_qa_dual_llm import (  # noqa: E402
    build_prompt,
    validate_annotation,
    validate_evidence_refs,
)
from tools.run_utils import open_run  # noqa: E402

MODEL = "glm-5.3"
THINKING = {"type": "enabled"}
SYSTEM = """You are the final QA-answer evidence adjudicator. Use only the frozen
question, answer, and evidence. Independently reconsider the annotations shown;
do not follow either by default. Return atomic claims in the required JSON shape.
support requires direct evidence for the same scope. refute requires an explicit
contradiction or proven exhaustive closed-scope exclusion. Absence in open
context is not refute. Preserve valid supported/refuted claims in a mixed answer.
Use the rule: any refute => overall refute; else any not_in_evidence => overall
not_in_evidence; else support. Cite only supplied evidence IDs. Return JSON only.
"""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def main() -> None:
    run_path = BASE / "data/gjb_438c/runs/annotate_frozen_qa_dual_llm_72379ff3_20261021_122221"
    frozen_path = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
    report_path = run_path / "comparison_report.json"
    frozen = {row["instance_id"]: row for row in read_jsonl(frozen_path)}
    gpt = {row["instance_id"]: row for row in read_jsonl(run_path / "raw_gpt5_6_sol.jsonl")}
    glm = {row["instance_id"]: row for row in read_jsonl(run_path / "raw_glm.jsonl")}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    disagreements = {row["instance_id"] for row in report["qa_disagreements_for_adjudication"]}
    targets = sorted({
        instance_id for instance_id in frozen
        if instance_id in disagreements
        or glm.get(instance_id, {}).get("status") != "ok"
        or glm.get(instance_id, {}).get("model_id") != MODEL
    })
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-run", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--no-thinking", action="store_true",
                        help="fallback: disable thinking for rows whose thinking review failed")
    args = parser.parse_args()
    thinking = None if args.no_thinking else THINKING
    if args.offset < 0:
        raise ValueError("offset must be non-negative")
    config = {
        "task": "targeted_glm53_re_review",
        "model": MODEL,
        "thinking": THINKING,
        "input_sha256": hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
        "targets": targets,
        "target_count": len(targets),
        "previous_run": str(run_path.relative_to(BASE)),
    }
    if args.resume_run:
        resume_path = args.resume_run.resolve()
        if not resume_path.is_dir():
            raise ValueError(f"resume run does not exist: {resume_path}")

        class ExistingRun:
            path = resume_path

            def save_result(self, value: dict[str, Any]) -> Path:
                target = self.path / "result.json"
                target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
                return target

        run = ExistingRun()
    else:
        run = open_run("review_qa_with_glm53", config)
    out_path = run.path / "glm53_reviews.jsonl"
    results_by_id = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                previous_result = json.loads(line)
                results_by_id[previous_result["instance_id"]] = previous_result
    pending = [instance_id for instance_id in targets
               if instance_id not in results_by_id
               or (args.retry_errors
                   and (results_by_id[instance_id].get("status") != "ok"
                        or results_by_id[instance_id].get("model_id") != MODEL))]
    if args.offset:
        pending = pending[args.offset:]
    if args.limit is not None:
        pending = pending[:args.limit]
    targets = pending
    for instance_id in targets:
        row = frozen[instance_id]
        review_input = {
            "question": row["question"],
            "answer": row["answer"],
            "evidence": row["evidence"],
        }
        previous = {
            "gpt": {
                "overall_verdict": gpt.get(instance_id, {}).get("overall_verdict"),
                "claims": [{key: claim.get(key) for key in
                            ("claim_id", "claim_text", "verdict", "evidence_refs")}
                           for claim in gpt.get(instance_id, {}).get("claims", [])],
            },
            "glm": {
                "overall_verdict": glm.get(instance_id, {}).get("overall_verdict"),
                "claims": [{key: claim.get(key) for key in
                            ("claim_id", "claim_text", "verdict", "evidence_refs")}
                           for claim in glm.get(instance_id, {}).get("claims", [])],
            },
        }
        prompt = (
            build_prompt(review_input, "glm53_final_review")
            + "\n\nPrior annotations (to independently audit, not treat as ground truth):\n"
            + json.dumps(previous, ensure_ascii=False)
        )
        try:
            value, actual_model = llm_json(
                prompt,
                system=SYSTEM,
                prefer="glm",
                cache=True,
                allow_fallback=False,
                model_override=MODEL,
                max_tokens=16000,
                timeout=300,
                extra_payload={
                    "response_contract": "json_final_content_v2",
                    **({"thinking": thinking} if thinking else {"reasoning_effort": "low"}),
                },
            )
            errors = validate_annotation(value) + validate_evidence_refs(value, row)
            if errors:
                errors.append(f"parsed_top_level_keys: {sorted(value) if isinstance(value, dict) else type(value).__name__}")
                if isinstance(value, dict):
                    errors.append(f"parsed_output_preview: {json.dumps(value, ensure_ascii=False)[:800]}")
            if actual_model != MODEL:
                errors.append(f"model identity mismatch: requested {MODEL}, got {actual_model}")
        except (RuntimeError, OSError, ValueError) as exc:
            value, actual_model = {}, "unknown"
            errors = [f"request error: {type(exc).__name__}: {str(exc)[:240]}"]
        result = {
            "instance_id": instance_id,
            "status": "ok" if not errors else "error",
            "model_id": actual_model,
            "thinking": thinking or {"reasoning_effort": "low"},
            "overall_verdict": value.get("overall_verdict") if not errors else None,
            "claims": value.get("claims", []) if not errors else [],
            "diagnostics": value.get("diagnostics", {}) if not errors else {"errors": errors},
            "prior_gpt_verdict": gpt.get(instance_id, {}).get("overall_verdict"),
            "prior_glm_verdict": glm.get(instance_id, {}).get("overall_verdict"),
        }
        results_by_id[instance_id] = result
        temporary = out_path.with_suffix(".jsonl.tmp")
        temporary.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n"
                    for item in results_by_id.values()),
            encoding="utf-8",
        )
        temporary.replace(out_path)

    run.save_result({
        "target_count": len(config["targets"]),
        "completed_or_retried_this_run": len(targets),
        "valid": sum(item["status"] == "ok" and item.get("model_id") == MODEL
                      for item in results_by_id.values()),
        "invalid": sum(item["status"] != "ok" or item.get("model_id") != MODEL
                        for item in results_by_id.values()),
        "model": MODEL,
        "thinking": THINKING,
        "gold_label": None,
    })
    print(run.path)


if __name__ == "__main__":
    main()
