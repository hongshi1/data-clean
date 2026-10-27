"""Build the deterministic frozen QAInput asset for scene 1.

The audit's ``evidence_hits`` are block pointers, not frozen evidence.  This
builder resolves those pointers against the immutable MinerU content list and
copies only source text that can be located by ``idx``.  It deliberately makes
no gold or completeness claims about the retrieved scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
DEFAULT_AUDIT = BASE / "data/gjb_438c/scene1_qa_audit.json"
DEFAULT_OUT = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
BUILDER_VERSION = "scene1_frozen_context_v1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def display_path(path: Path) -> str:
    try:
        return path.relative_to(BASE).as_posix()
    except ValueError:
        return path.as_posix()


def item_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    text = str(item.get("text", "") or "").strip()
    if text:
        parts.append(text)
    list_items = item.get("list_items", [])
    if isinstance(list_items, list):
        parts.extend(str(part).strip() for part in list_items if str(part).strip())
    body = str(item.get("table_body", "") or "").strip()
    if body:
        parts.append(body)
    captions = item.get("table_caption", [])
    if isinstance(captions, list):
        parts.extend(str(part).strip() for part in captions if str(part).strip())
    elif captions:
        parts.append(str(captions).strip())
    image_captions = item.get("image_caption", [])
    if isinstance(image_captions, list):
        parts.extend(str(part).strip() for part in image_captions if str(part).strip())
    elif image_captions:
        parts.append(str(image_captions).strip())
    return "\n".join(parts)


def source_type(item: dict[str, Any]) -> str:
    kind = str(item.get("type", "other"))
    return {"text": "text", "list": "text", "table": "table", "image": "figure"}.get(kind, "other")


def section_for(items: list[dict[str, Any]], index: int) -> str:
    section = ""
    for item in items[: index + 1]:
        text = str(item.get("text", "") or "").strip()
        if item.get("text_level") and re.match(r"^\d+(?:\.\d+)*\b", text):
            section = text
    return section


def load_source_path(audit: dict[str, Any]) -> Path:
    source = BASE / audit["meta"]["source_srs"]
    if not source.exists():
        raise FileNotFoundError(f"source_srs does not exist: {source}")
    return source


def build(audit_path: Path = DEFAULT_AUDIT, output_path: Path = DEFAULT_OUT) -> dict[str, Any]:
    audit_bytes = audit_path.read_bytes()
    audit = json.loads(audit_bytes.decode("utf-8"))
    source_path = load_source_path(audit)
    source_bytes = source_path.read_bytes()
    source_items = json.loads(source_bytes.decode("utf-8"))
    if not isinstance(source_items, list):
        raise ValueError("source_srs must contain a JSON list")

    input_sha256 = sha256_bytes(audit_bytes + b"\n" + source_bytes)
    freeze_seed = canonical_json({
        "builder_version": BUILDER_VERSION,
        "audit_sha256": sha256_bytes(audit_bytes),
        "source_sha256": sha256_bytes(source_bytes),
    })
    context_freeze_id = f"scene1-frozen-v1-{sha256_bytes(freeze_seed)[:16]}"
    rows: list[dict[str, Any]] = []
    evidence_count = 0
    empty_evidence = 0
    for entry in audit["entries"]:
        evidence: list[dict[str, Any]] = []
        seen_indices: set[int] = set()
        for hit in entry.get("evidence_hits", []):
            index = hit.get("idx")
            if not isinstance(index, int) or index in seen_indices:
                continue
            seen_indices.add(index)
            if index < 0 or index >= len(source_items):
                raise ValueError(f"{entry['id']} points outside source_srs: idx={index}")
            item = source_items[index]
            text = item_text(item)
            if not text:
                continue
            ref = {
                "doc_id": source_path.stem.removesuffix("_content_list"),
                "section": section_for(source_items, index),
                "page": item.get("page_idx"),
                "block_id": f"block-{index:06d}",
            }
            scope_id = f"{ref['doc_id']}:{ref['block_id']}"
            evidence_id = f"{entry['id']}-ev-{index:06d}"
            evidence.append({
                "evidence_id": evidence_id,
                "text": text,
                "source_type": source_type(item),
                "source_ref": ref,
                "scope_id": scope_id,
                "completeness": "open",
                "completeness_proof": "Only this source block was frozen; no claim that the block or hit set is exhaustive.",
                "extraction_method": "audit_evidence_hit_idx_to_content_list",
                "extraction_confidence": 1.0,
            })
        if not evidence:
            empty_evidence += 1
        evidence_count += len(evidence)
        rows.append({
            "instance_id": entry["id"],
            "question": entry["question"],
            "answer": entry["answer"],
            "context_freeze_id": context_freeze_id,
            "evidence": evidence,
        })

    output_path = output_path.resolve()
    if output_path == audit_path.resolve() or output_path == source_path.resolve():
        raise ValueError("refusing to overwrite an input source asset")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

    metadata = {
        "version": BUILDER_VERSION,
        "context_freeze_id": context_freeze_id,
        "input_sha256": input_sha256,
        "audit_sha256": sha256_bytes(audit_bytes),
        "source_sha256": sha256_bytes(source_bytes),
        "source_audit": display_path(audit_path),
        "source_srs": display_path(source_path),
        "output": display_path(output_path),
        "total": len(rows),
        "evidence_total": evidence_count,
        "rows_without_resolved_evidence": empty_evidence,
        "completeness_policy": "open for every resolved block; closed is never inferred from evidence_hits",
        "gold_policy": "gold/verdict fields are not generated",
    }
    metadata_path = output_path.with_name(output_path.stem + "_metadata.json")
    report_path = output_path.with_name(output_path.stem + "_report.json")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps({
        "version": BUILDER_VERSION,
        "context_freeze_id": context_freeze_id,
        "checks": {
            "row_count": len(rows) == len(audit["entries"]),
            "expected_91_rows": len(rows) == 91,
            "all_ids_unique": len({row["instance_id"] for row in rows}) == len(rows),
            "all_evidence_located": all(evidence["source_ref"]["block_id"] for row in rows for evidence in row["evidence"]),
            "no_closed_without_proof": all(evidence["completeness"] != "closed" or evidence["completeness_proof"] for row in rows for evidence in row["evidence"]),
        },
        "counts": {"rows": len(rows), "evidence": evidence_count, "rows_without_resolved_evidence": empty_evidence},
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    metadata = build(args.audit, args.output)
    print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
