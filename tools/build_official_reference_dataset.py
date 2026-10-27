"""Build the official reference dataset: Alpaca QA + frozen evidence + labels.

The scene-1 supplementary package (docs/doc11/场景1-*) is the project's
official reference data: Alpaca-format QA pairs paired with the 04 SRS
source document and GJB-438C templates. This builder integrates that
official package with everything this session derived from it:

  source Alpaca fields  (instruction/input/output/system, verbatim)
  frozen context        (question-conditioned evidence blocks + source_refs)
  linearized statements (field-level table statements with row localization)
  silver labels         (GLM-5.3 reviewed verdicts + claims, NOT gold)
  lineage               (hashes of every input artifact)

Output is a single JSONL where each row is the complete reusable record.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import linearize_context  # noqa: E402
from algorithms.consistency.qa_models import RetrievedEvidence, SourceRef  # noqa: E402

SOURCE_PACKAGE = (
    BASE / "docs/doc11/场景1-软件需求规格辅助生成场景补发数据")
SOURCE_QA = (SOURCE_PACKAGE
             / "高质量问答对（配套样例数据中：04数据统一访问服务软件需求规格说明）.json")
FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
LABELS = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
OUT = BASE / "data/gjb_438c/qa_frozen/scene1_official_reference_v1.jsonl"
OUT_META = BASE / "data/gjb_438c/qa_frozen/scene1_official_reference_v1_metadata.json"
BUILDER_VERSION = "scene1_official_reference_v1"

_OFFICIAL_PACKAGE_FILES = (
    "高质量问答对（配套样例数据中：04数据统一访问服务软件需求规格说明）.json",
    "2-某项目的合同、需归文档/数据服务软件需求规格说明.docx",
    "2-某项目的合同、需归文档/1-某大数据典型应用系统集成支撑合同-20240513.docx",
    "1-438C软件需求规格相关模板/09_软件需求规格说明.docx",
    "1-438C软件需求规格相关模板/06_系统规格说明.docx",
    "1-438C软件需求规格相关模板/04_总体技术方案.docx",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def to_retrieved_evidence(items: list[dict[str, Any]]) -> tuple[RetrievedEvidence, ...]:
    return tuple(
        RetrievedEvidence(
            evidence_id=str(item["evidence_id"]),
            text=str(item["text"]),
            source_type=item["source_type"],
            source_ref=SourceRef(**item["source_ref"]),
            scope_id=str(item["scope_id"]),
            completeness=item.get("completeness", "unknown"),
            completeness_proof=str(item.get("completeness_proof", "")),
            extraction_method=str(item.get("extraction_method", "")),
            extraction_confidence=item.get("extraction_confidence"),
        ) for item in items)


def main() -> None:
    source_rows = json.loads(SOURCE_QA.read_text(encoding="utf-8"))
    frozen_rows = read_jsonl(FROZEN)
    label_rows = read_jsonl(LABELS)
    if not (len(source_rows) == len(frozen_rows) == len(label_rows) == 91):
        raise ValueError("source/frozen/labels row counts must all be 91")
    labels_by_id = {row["instance_id"]: row for row in label_rows}
    frozen_by_id = {row["instance_id"]: row for row in frozen_rows}

    package_files = []
    for relative in _OFFICIAL_PACKAGE_FILES:
        path = SOURCE_PACKAGE / relative
        package_files.append({
            "path": f"docs/doc11/场景1-软件需求规格辅助生成场景补发数据/{relative}",
            "sha256": sha256_file(path) if path.exists() else None,
        })

    records: list[dict[str, Any]] = []
    statement_total = 0
    for index, source in enumerate(source_rows, 1):
        instance_id = f"S1QA-{index:03d}"
        frozen = frozen_by_id[instance_id]
        label = labels_by_id[instance_id]
        evidence = to_retrieved_evidence(frozen["evidence"])
        statements = linearize_context(evidence)
        statement_total += len(statements)
        records.append({
            "instance_id": instance_id,
            "official_alpaca": {
                "instruction": source.get("instruction", ""),
                "input": source.get("input", ""),
                "output": source.get("output", ""),
                "system": source.get("system", ""),
            },
            "field_semantics": {
                "question": "official_alpaca.instruction（与冻结资产的question逐条一致）",
                "answer": "official_alpaca.output",
                "note": "input/system 全部为空：answer 生成时未记录检索上下文与系统指令",
            },
            "context_freeze_id": frozen["context_freeze_id"],
            "evidence": frozen["evidence"],
            "linearized_statements": [
                {
                    "statement_id": statement.statement_id,
                    "evidence_id": statement.evidence_id,
                    "text": statement.text,
                    "field_name": statement.field_name,
                    "scope_key": statement.scope_key,
                    "row_index": statement.row_index,
                } for statement in statements
            ],
            "silver_label": {
                "final_verdict": label["final_verdict"],
                "final_model": label["final_model"],
                "label_source": label["label_source"],
                "review_thinking": label.get("review_thinking"),
                "claims": label["claims"],
                "prior_gpt_verdict": label.get("prior_gpt_verdict"),
                "prior_glm5_verdict": label.get("prior_glm5_verdict"),
                "is_gold": False,
                "note": "GLM-5.3 复核 silver 标签，非人工 gold；升gold需双标+仲裁",
            },
        })

    OUT.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8")
    metadata = {
        "version": BUILDER_VERSION,
        "official_package": {
            "root": "docs/doc11/场景1-软件需求规格辅助生成场景补发数据",
            "files": package_files,
            "status": "项目官方提供的标准参考数据（场景1补发包）",
        },
        "n_rows": len(records),
        "evidence_total": sum(len(r["evidence"]) for r in records),
        "statement_total": statement_total,
        "silver_verdicts": {
            verdict: sum(1 for r in records
                         if r["silver_label"]["final_verdict"] == verdict)
            for verdict in ("support", "refute", "not_in_evidence")
        },
        "input_artifacts": {
            "source_qa_sha256": sha256_file(SOURCE_QA),
            "frozen_sha256": sha256_file(FROZEN),
            "labels_sha256": sha256_file(LABELS),
        },
        "lineage": {
            "context_freeze_id": frozen_rows[0]["context_freeze_id"],
            "labels_run": "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212",
        },
        "field_semantics": {
            "official_alpaca": "官方原始四字段，逐字保留",
            "question=instruction": "91/91 与 scene1_qa_audit 的 question 一致",
            "input/system": "0/91 有内容——answer 非检索式生成的数据事实",
            "silver_label.is_gold": False,
        },
    }
    OUT_META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "n_rows": metadata["n_rows"],
        "evidence_total": metadata["evidence_total"],
        "statement_total": statement_total,
        "silver_verdicts": metadata["silver_verdicts"],
        "output": str(OUT.relative_to(BASE)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
