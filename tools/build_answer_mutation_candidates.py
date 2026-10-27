"""Build proof-backed answer mutations from frozen QA/context JSONL.

Input rows follow QAInput. The builder does not retrieve SRS context; it requires
an upstream freeze id and evidence source refs. Output is a development artifact
with model-visible input separated from private gold/proof metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

BUILDER_VERSION = "answer_mutation_candidates_v1"
OPERATOR_REGISTRY_VERSION = "answer_mutation_operators_v1"

from algorithms.consistency.answer_mutations import (  # noqa: E402
    AnswerMutationProposal,
    propose_enum_explicit_conflict,
    propose_abbreviation_expansion,
    propose_equivalent_numeric_surface,
    propose_explicit_quote_conflict,
    propose_exact_numeric_conflict,
    propose_numeric_identity,
    propose_out_of_range_conflict,
    propose_reversed_data_flow,
)
from algorithms.consistency.eval_lib import build_qa_input  # noqa: E402
from algorithms.consistency.qa_models import QAInput  # noqa: E402
from algorithms.consistency.structural_mutations import (  # noqa: E402
    propose_actor_role_list_mutation,
    propose_closed_list_add,
    propose_closed_list_remove,
    propose_exception_outcome_swap,
    propose_step_delete,
    propose_step_reorder,
)
from algorithms.consistency.term_mutations import (  # noqa: E402
    propose_command_action_swap,
    propose_definition_swap,
    propose_interface_id_conflict,
    propose_status_term_conflict,
)
from algorithms.consistency.param_mutations import (  # noqa: E402
    param_operator_registry,
)
from algorithms.consistency.logic_mutations import (  # noqa: E402
    propose_atomicity_conflict,
    propose_event_order_swap,
    propose_exception_strategy_swap as propose_logic_exception_swap,
    propose_permission_conflict,
    propose_priority_reversal,
    propose_recovery_mode_conflict,
    propose_redundancy_arbitration_swap,
    propose_research_scope_conflict,
)
from algorithms.consistency.qa_router import route_question  # noqa: E402


def request_from_dict(row: dict[str, Any]) -> QAInput:
    """dict→QAInput (委托eval_lib.build_qa_input: SourceRef六字段映射的权威实现)."""
    return build_qa_input(row)


def proposal_record(proposal: AnswerMutationProposal,
                    request: QAInput) -> dict[str, Any]:
    return {
        "operator_id": proposal.operator_id,
        "check_item": proposal.check_item,
        "model_input": {
            "instance_id": proposal.source_instance_id,
            "question": proposal.question,
            "answer": proposal.answer_after,
            "context_freeze_id": proposal.context_freeze_id,
            "retrieved_context": [
                {
                    "evidence_id": ev.evidence_id,
                    "text": ev.text,
                    "source_type": ev.source_type,
                    "source_ref": ev.source_ref.__dict__,
                    "scope_id": ev.scope_id,
                    "completeness": ev.completeness,
                    "completeness_proof": ev.completeness_proof,
                }
                for ev in request.evidence
            ],
        },
        "gold_private": {
            "candidate": proposal.gold_candidate,
            "proof_kind": proposal.proof_kind,
            "proof": proposal.proof,
            "requires_manual_review": proposal.requires_manual_review,
        },
        "mutation_private": {
            "target": proposal.target,
            "answer_before": proposal.answer_before,
            "answer_after": proposal.answer_after,
            "question_sha256": proposal.question_hash,
            "context_sha256": proposal.context_hash,
            "context_refs": [ref.__dict__ for ref in proposal.context_refs],
        },
    }


def sha256_file(path: Path) -> str:
    """Hash the exact input artifact consumed by the builder."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_git_sha() -> str:
    """Return the repository commit, or an explicit value when unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=BASE,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    sha = result.stdout.strip()
    return sha or "unknown"


def build_candidates(requests: list[QAInput]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    seen: set[tuple[str, str, str, str]] = set()

    def record(proposal: AnswerMutationProposal, request: QAInput,
               counter: str | None = None) -> None:
        key = (request.instance_id, proposal.operator_id, proposal.answer_after)
        if key in seen:
            return
        seen.add(key)
        rows.append(proposal_record(proposal, request))
        counts[proposal.operator_id if counter is None else counter] += 1

    for request in requests:
        for evidence in request.evidence:
            for operator, kwargs, counter in (
                (propose_abbreviation_expansion, {}, "term08_not_applicable"),
                (propose_reversed_data_flow, {}, "logic04_not_applicable"),
            ):
                try:
                    proposal = operator(request, evidence_id=evidence.evidence_id, **kwargs)
                except ValueError:
                    counts[counter] += 1
                else:
                    record(proposal, request)
            numeric_answer = re.search(r"=\s*(\d+(?:\.\d+)?)|(?:为|等于)\s*(\d+(?:\.\d+)?)", request.answer)
            if numeric_answer:
                original_value = float(next(value for value in numeric_answer.groups() if value is not None))
                delta = max(abs(original_value) * 0.1, 1.0)
                try:
                    ranged = propose_out_of_range_conflict(
                        request, evidence_id=evidence.evidence_id,
                        mutated_value=original_value + delta)
                except ValueError:
                    counts["param06_not_applicable"] += 1
                else:
                    record(ranged, request)
            try:
                identity = propose_numeric_identity(
                    request, evidence_id=evidence.evidence_id)
            except ValueError:
                counts["no_safe_numeric_operator"] += 1
                identity = None
            if identity is not None:
                record(identity, request)
                unit_match = re.search(
                    r"(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节)",
                    identity.answer_after,
                )
                targets = {
                    "s": "ms", "秒": "毫秒", "ms": "秒", "毫秒": "秒",
                    "GB": "MB", "MB": "KB", "KB": "B",
                }
                target_unit = targets.get(unit_match.group("unit")) if unit_match else None
                if target_unit:
                    try:
                        equiv = propose_equivalent_numeric_surface(
                            request, evidence_id=evidence.evidence_id,
                            target_unit=target_unit)
                    except ValueError:
                        counts["equivalent_operator_not_applicable"] += 1
                    else:
                        record(equiv, request)

                value_match = re.search(r"\d+(?:\.\d+)?", identity.answer_after)
                if value_match:
                    original_value = float(value_match.group())
                    delta = max(abs(original_value) * 0.1, 1.0)
                    try:
                        conflict = propose_exact_numeric_conflict(
                            request, evidence_id=evidence.evidence_id,
                            mutated_value=original_value + delta)
                    except ValueError:
                        counts["conflict_operator_not_applicable"] += 1
                    else:
                        record(conflict, request)

            for term_match in re.finditer(r"(?:不包括|不包含|不支持|禁止|不得)[「\"]?([^，。；、\s「」\"]{2,30})", evidence.text):
                target = term_match.group(1)
                try:
                    quote_conflict = propose_explicit_quote_conflict(
                        request, evidence_id=evidence.evidence_id,
                        contradicted_term=target)
                except ValueError:
                    pass
                else:
                    record(quote_conflict, request)
                try:
                    enum_conflict = propose_enum_explicit_conflict(
                        request, evidence_id=evidence.evidence_id, added_term=target)
                except ValueError:
                    pass
                else:
                    record(enum_conflict, request)

            # Keep extraction literal; structural operators perform the proof gates.
            evidence_enum = re.search(
                r"(?:清单为|枚举为|包括|包含)\s*[:：]?\s*([^。.!！？\n]+)",
                evidence.text,
            )
            answer_enum = re.search(
                r"(?:清单为|枚举为|包括|包含)\s*[:：]?\s*([^。.!！？\n]+)",
                request.answer,
            )
            if evidence_enum and answer_enum:
                evidence_items = re.findall(r"[^、,，;；\s]+", evidence_enum.group(1))
                answer_items = re.findall(r"[^、,，;；\s]+", answer_enum.group(1))
                for member in dict.fromkeys(set(evidence_items) - set(answer_items)):
                    for operator, kwargs, counter in (
                        (propose_closed_list_add, {}, "struct_list_add_not_applicable"),
                        (propose_actor_role_list_mutation, {"remove": False}, "struct_actor_add_not_applicable"),
                    ):
                        try:
                            proposal = operator(request, evidence_id=evidence.evidence_id,
                                                member=member, **kwargs)
                        except ValueError:
                            counts[counter] += 1
                        else:
                            record(proposal, request)
                removable = (answer_items if set(answer_items) == set(evidence_items)
                             else list(set(answer_items) - set(evidence_items)))
                for member in dict.fromkeys(removable):
                    for operator, kwargs, counter in (
                        (propose_closed_list_remove, {}, "struct_list_remove_not_applicable"),
                        (propose_actor_role_list_mutation, {"remove": True}, "struct_actor_remove_not_applicable"),
                    ):
                        try:
                            proposal = operator(request, evidence_id=evidence.evidence_id,
                                                member=member, **kwargs)
                        except ValueError:
                            counts[counter] += 1
                        else:
                            record(proposal, request)

            step_numbers = [int(number) for number in re.findall(
                r"(?:^|[;；\n])\s*(\d+)\s*[.)、:：]", request.answer)]
            if len(step_numbers) >= 2:
                for first in range(1, len(step_numbers) + 1):
                    for second in range(first + 1, len(step_numbers) + 1):
                        try:
                            proposal = propose_step_reorder(
                                request, evidence_id=evidence.evidence_id,
                                first_step=first, second_step=second)
                        except ValueError:
                            counts["struct_step_reorder_not_applicable"] += 1
                        else:
                            record(proposal, request)
                    try:
                        proposal = propose_step_delete(
                            request, evidence_id=evidence.evidence_id, step_number=first)
                    except ValueError:
                        counts["struct_step_delete_not_applicable"] += 1
                    else:
                        record(proposal, request)

            outcome_match = re.search(
                r"(?:不得|禁止|不能|不可|不应|不允许)\s*(?:执行|采取|选择)?\s*([^，,。；;]+)",
                evidence.text,
            )
            if outcome_match:
                try:
                    proposal = propose_exception_outcome_swap(
                        request, evidence_id=evidence.evidence_id,
                        mutated_outcome=outcome_match.group(1).strip())
                except ValueError:
                    counts["struct_exception_swap_not_applicable"] += 1
                else:
                    record(proposal, request)

            # ── TERM / LOGIC / PARAM family operators ──────────────────
            # Each operator carries its own proof gates; a ValueError means the
            # shape is unprovable on this row and is only counted, never guessed.
            family_plan: list[tuple[Any, dict[str, Any], str]] = [
                (propose_definition_swap, {}, "term02_not_applicable"),
                (propose_command_action_swap, {}, "term05_not_applicable"),
                (propose_interface_id_conflict, {}, "term07_not_applicable"),
                (propose_priority_reversal, {}, "logic01_not_applicable"),
                (propose_event_order_swap, {}, "logic03_not_applicable"),
                (propose_atomicity_conflict, {}, "logic07_not_applicable"),
                (propose_redundancy_arbitration_swap, {}, "logic08_not_applicable"),
                (propose_recovery_mode_conflict, {}, "logic10_not_applicable"),
                (propose_research_scope_conflict, {}, "logic11_not_applicable"),
            ]
            for excluded_match in re.finditer(
                    r"(?:不包括|不包含|不支持)[「\"]?([^，。；、\s「」\"]{2,12})",
                    evidence.text):
                family_plan.append((
                    propose_status_term_conflict,
                    {"excluded_status": excluded_match.group(1)},
                    "term04_not_applicable"))
            for prohibited_match in re.finditer(
                    r"(?:不得|禁止|不能|不允许)(?:执行|采取|进行|使用)?([^，。；\s]{2,12})",
                    evidence.text):
                family_plan.append((
                    propose_logic_exception_swap,
                    {"prohibited_action": prohibited_match.group(1)},
                    "logic02_not_applicable"))
            for forbid_pair in re.finditer(
                    r"(?:禁止|不允许|不能)(?P<role>[A-Za-z\u4e00-\u9fff]{2,8})"
                    r"(?:执行|进行|访问|使用|操作)?(?P<action>[A-Za-z\u4e00-\u9fff]{2,10})",
                    evidence.text):
                family_plan.append((
                    propose_permission_conflict,
                    {"role": forbid_pair.group("role"),
                     "action": forbid_pair.group("action")},
                    "logic09_not_applicable"))
            for operator, kwargs, counter in family_plan:
                try:
                    proposal = operator(
                        request, evidence_id=evidence.evidence_id, **kwargs)
                except ValueError:
                    counts[counter] += 1
                else:
                    record(proposal, request)

            # PARAM registry: attempt routed items with evidence-derived values.
            routed = route_question(request.question)
            param_registry = param_operator_registry()
            numeric_evidence = re.search(
                r"(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|毫秒|s|秒|min|分钟|GB|MB|KB|B|字节|%)",
                evidence.text)
            for check_item in routed:
                if check_item not in param_registry:
                    continue
                operator, operator_id, keywords = param_registry[check_item]
                if not numeric_evidence:
                    counts[f"param_{check_item.lower()}_no_numeric_evidence"] += 1
                    continue
                base_value = float(numeric_evidence.group("value"))
                delta = max(abs(base_value) * 0.5, 1.0)
                for mutated_value in (base_value + delta, base_value - delta):
                    try:
                        proposal = operator(
                            request, evidence_id=evidence.evidence_id,
                            mutated_value=mutated_value, check_item=check_item,
                            operator_id=operator_id, subject_keywords=keywords)
                    except ValueError:
                        counts[f"param_{check_item.lower()}_not_applicable"] += 1
                    else:
                        record(proposal, request)
                        break
    return rows, dict(counts)


def split_candidate_records(
    rows: list[dict[str, Any]],
    *,
    input_sha256: str = "unknown",
    builder_version: str = BUILDER_VERSION,
    operator_registry_version: str = OPERATOR_REGISTRY_VERSION,
    git_sha: str = "unknown",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate model-visible examples from labels/proofs to prevent leakage."""
    model_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        candidate_id = f"AMC-{index:06d}"
        model_rows.append({"candidate_id": candidate_id, **row["model_input"]})
        private_rows.append({
            "candidate_id": candidate_id,
            "operator_id": row["operator_id"],
            "check_item": row["check_item"],
            "input_sha256": input_sha256,
            "builder_version": builder_version,
            "operator_registry_version": operator_registry_version,
            "git_sha": git_sha,
            "gold_private": row["gold_private"],
            "mutation_private": row["mutation_private"],
        })
    return model_rows, private_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True,
                        help="upstream-frozen QAInput JSONL; this tool does not retrieve context")
    parser.add_argument("--model-output", required=True,
                        help="model-visible QA/context JSONL; contains no labels/proofs")
    parser.add_argument("--lineage-output", required=True,
                        help="private lineage/gold/proof JSONL; never feed to model")
    parser.add_argument("--builder-version", default=BUILDER_VERSION,
                        help=f"builder identity (default: {BUILDER_VERSION})")
    parser.add_argument("--operator-registry-version",
                        default=OPERATOR_REGISTRY_VERSION,
                        help=("operator registry identity "
                              f"(default: {OPERATOR_REGISTRY_VERSION})"))
    parser.add_argument("--git-sha", default=None,
                        help="override recorded git SHA; defaults to the current repository")
    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    model_path = Path(args.model_output).resolve()
    lineage_path = Path(args.lineage_output).resolve()
    if model_path == lineage_path:
        raise ValueError("model-output and lineage-output must be different files")
    requests = [request_from_dict(json.loads(line))
                for line in input_path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    if not requests:
        raise ValueError("input JSONL has no QA/context records")
    rows, counts = build_candidates(requests)
    model_rows, private_rows = split_candidate_records(
        rows,
        input_sha256=sha256_file(input_path),
        builder_version=args.builder_version,
        operator_registry_version=args.operator_registry_version,
        git_sha=args.git_sha or current_git_sha(),
    )
    model_path.parent.mkdir(parents=True, exist_ok=True)
    lineage_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in model_rows),
        encoding="utf-8")
    lineage_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in private_rows),
        encoding="utf-8")
    print(f"source QA/context rows: {len(requests)}")
    print(f"proof-backed answer candidates: {len(rows)}")
    print(f"operator counts: {counts}")
    print(f"model-visible inputs → {model_path}")
    print(f"private labels/proofs → {lineage_path}")


if __name__ == "__main__":
    main()
