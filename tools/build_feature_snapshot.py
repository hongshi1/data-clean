#!/usr/bin/env python3
"""Build a feature snapshot (dense vectors + structural features) from structured_corpus_v1.

Feature objects are claims, requirements, diagram nodes, and table data rows.
Real mode encodes truncated text with the local frozen BGE encoder
(bge-large-zh-v1.5, CLS+L2). ``--fake`` skips the model entirely and emits
deterministic 32-d pseudo vectors seeded by sha256(text); those are smoke-only
artifacts (policy: fake_vectors_not_for_paper) and land in a separate output
directory so real and fake snapshots never mix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from algorithms.common.bge_local import BgeLocal  # noqa: E402

CORPUS = BASE / "data/gjb_438c/structured_corpus_v1"
DEFAULT_OUT_REAL = BASE / "data/gjb_438c/feature_snapshot_v1"
DEFAULT_OUT_FAKE = BASE / "data/gjb_438c/feature_snapshot_fake_v1"

ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
MODEL_NAME = "bge-large-zh-v1.5"
FAKE_MODEL_NAME = "fake-sha256-32d"
TRUNCATE_CHARS = 200
FAKE_DIM = 32


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cjk_bigrams(text: str) -> list[str]:
    out: list[str] = []
    for segment in CJK_RE.findall(text):
        out.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return out


def _unique_ids(counter: Counter[str], base: str) -> str:
    seen = counter[base]
    counter[base] += 1
    return base if seen == 0 else f"{base}#{seen + 1}"


def collect_features(corpus: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Collect feature objects deterministically; returns (objects, failures, source counts)."""
    claims = read_jsonl(corpus / "claims.jsonl")
    requirements = read_jsonl(corpus / "requirements.jsonl")
    nodes = read_jsonl(corpus / "diagram_nodes.jsonl")
    diagrams = read_jsonl(corpus / "diagrams.jsonl")
    tables = read_jsonl(corpus / "tables.jsonl")
    diagram_docs = {str(row.get("diagram_id", "")): str(row.get("doc_id", "")) for row in diagrams}

    raw: list[dict[str, Any]] = []
    for row in claims:
        raw.append(
            {
                "occurrence_id": f"claim:{row.get('claim_id', '')}",
                "source_kind": "claim",
                "doc_id": str(row.get("doc_id", "")),
                "section": str(row.get("section", "")),
                "text": str(row.get("raw_text", "")),
            }
        )
    for row in requirements:
        raw.append(
            {
                "occurrence_id": f"requirement:{row.get('requirement_id', '')}",
                "source_kind": "requirement",
                "doc_id": str(row.get("doc_id", "")),
                "section": str(row.get("section", "")),
                "text": str(row.get("raw_text", "")),
            }
        )
    for row in nodes:
        raw.append(
            {
                "occurrence_id": f"diagram_node:{row.get('node_id', '')}",
                "source_kind": "diagram_node",
                "doc_id": diagram_docs.get(str(row.get("diagram_id", "")), ""),
                "section": "",
                "text": str(row.get("text_raw", "")),
            }
        )
    for row in tables:
        table_id = str(row.get("table_id", ""))
        doc_id = str(row.get("doc_id", ""))
        section = str(row.get("section", ""))
        # thead-aware: data rows start after header rows (C8); default 1
        # keeps the legacy rows[1:] heuristic for corpora without the field
        header_row_count = int(row.get("header_row_count", 1))
        for index, cells in enumerate(row.get("rows", [])[header_row_count:], start=header_row_count):
            raw.append(
                {
                    "occurrence_id": f"table_row:{table_id}:row={index}",
                    "source_kind": "table_row",
                    "doc_id": doc_id,
                    "section": section,
                    "text": " | ".join(str(cell) for cell in cells),
                }
            )

    id_counter: Counter[str] = Counter()
    objects: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in raw:
        occurrence_id = _unique_ids(id_counter, row["occurrence_id"])
        if not str(row["text"]).strip():
            failures.append(
                {
                    "occurrence_id": occurrence_id,
                    "reason": "empty_text",
                    "source_kind": row["source_kind"],
                    "doc_id": row["doc_id"],
                    "section": row["section"],
                }
            )
            continue
        text = str(row["text"])[:TRUNCATE_CHARS]
        objects.append(
            {
                "occurrence_id": occurrence_id,
                "source_kind": row["source_kind"],
                "doc_id": row["doc_id"],
                "section": row["section"],
                "text": text,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "identifiers": sorted(set(ID_RE.findall(text))),
                "cjk_bigram_count": len(cjk_bigrams(text)),
            }
        )
    source_counts = {
        "claims": len(claims),
        "requirements": len(requirements),
        "diagram_nodes": len(nodes),
        "diagrams": len(diagrams),
        "tables": len(tables),
    }
    return objects, failures, source_counts


def fake_vector(text: str) -> list[float]:
    """Deterministic 32-d pseudo vector: sha256(text)-seeded RNG, L2-normalized."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    values = [rng.random() * 2.0 - 1.0 for _ in range(FAKE_DIM)]
    norm = math.sqrt(sum(value * value for value in values))
    if norm <= 1e-12:
        return [1.0 / math.sqrt(FAKE_DIM)] * FAKE_DIM
    return [value / norm for value in values]


def encode_fake(objects: list[dict[str, Any]]) -> tuple[np.ndarray, list[dict[str, Any]]]:
    matrix = np.zeros((len(objects), FAKE_DIM), dtype=np.float32)
    failed: list[dict[str, Any]] = []
    for index, obj in enumerate(objects):
        matrix[index] = np.asarray(fake_vector(obj["text"]), dtype=np.float32)
    return matrix, failed


def encode_real(
    objects: list[dict[str, Any]], bge: BgeLocal
) -> tuple[np.ndarray, list[dict[str, Any]], int]:
    texts = [obj["text"] for obj in objects]
    vectors = bge.embed(texts)
    dim = 0
    rows: list[list[float]] = []
    failed: list[dict[str, Any]] = []
    for obj, text in zip(objects, texts):
        vector = vectors.get(text, [])
        if not vector:
            failed.append(
                {
                    "occurrence_id": obj["occurrence_id"],
                    "reason": "embed_failed",
                    "source_kind": obj["source_kind"],
                }
            )
            continue
        dim = max(dim, len(vector))
        rows.append(vector)
    matrix = np.zeros((len(rows), dim), dtype=np.float32)
    for index, vector in enumerate(rows):
        matrix[index] = np.asarray(vector, dtype=np.float32)
    return matrix, failed, dim


def build(corpus: Path, out: Path, fake: bool, limit: int | None) -> dict[str, Any]:
    corpus = corpus.resolve()
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    objects, failures, source_counts = collect_features(corpus)
    total_collected = len(objects) + len(failures)
    if limit is not None:
        objects = objects[:limit]

    if fake:
        mode = "fake"
        model = FAKE_MODEL_NAME
        matrix, embed_failed = encode_fake(objects)
        dim = FAKE_DIM
        bge_stats: dict[str, Any] = {}
    else:
        bge = BgeLocal()
        mode = bge.ensure()
        if mode == "unavailable":
            raise RuntimeError(f"BgeLocal unavailable: {bge.last_error}")
        model = MODEL_NAME
        matrix, embed_failed, dim = encode_real(objects, bge)
        bge_stats = {key: bge.stats[key] for key in sorted(bge.stats)}
        bge.save()
    failures = failures + embed_failed
    failed_ids = {row["occurrence_id"] for row in embed_failed}
    encoded = [obj for obj in objects if obj["occurrence_id"] not in failed_ids]

    feature_rows = [
        {
            "occurrence_id": obj["occurrence_id"],
            "text": obj["text"],
            "text_sha256": obj["text_sha256"],
            "model": model,
            "model_mode": mode,
            "dim": dim,
            "doc_id": obj["doc_id"],
            "section": obj["section"],
            "identifiers": obj["identifiers"],
            "cjk_bigram_count": obj["cjk_bigram_count"],
            "source_kind": obj["source_kind"],
        }
        for obj in encoded
    ]

    ids = np.asarray([obj["occurrence_id"] for obj in encoded], dtype=np.str_)
    np.savez(out / "vectors.npz", matrix=matrix, ids=ids)
    counts = {
        "collected": total_collected,
        "encoded": len(feature_rows),
        "skipped_empty": sum(1 for f in failures if f["reason"] == "empty_text"),
        "embed_failed": len(embed_failed),
        "limit": limit,
        "by_source_kind": dict(sorted(Counter(row["source_kind"] for row in feature_rows).items())),
    }
    manifest_path = corpus / "manifest.json"
    summary = {
        "schema_version": "feature_snapshot_v1",
        "mode": mode,
        "model": model,
        "dim": dim,
        "counts": counts,
        "source_counts": source_counts,
        "truncation_chars": TRUNCATE_CHARS,
        "policy": {
            "fake_vectors_not_for_paper": fake,
            "text_truncated_to_chars": TRUNCATE_CHARS,
            "duplicate_occurrence_ids_disambiguated": True,
        },
        "source_corpus": str(corpus.relative_to(BASE)) if corpus.is_relative_to(BASE) else str(corpus),
        "source_manifest_sha256": sha256_file(manifest_path) if manifest_path.exists() else None,
        "bge_stats": bge_stats,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_jsonl(out / "features.jsonl", feature_rows)
    write_jsonl(out / "failures.jsonl", failures)
    manifest = {
        "schema_version": "feature_snapshot_v1",
        "files": {
            name: sha256_file(out / name)
            for name in ("vectors.npz", "features.jsonl", "failures.jsonl", "summary.json")
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output dir (default: feature_snapshot_fake_v1 with --fake, else feature_snapshot_v1)",
    )
    parser.add_argument("--fake", action="store_true", help="deterministic pseudo vectors, no model load")
    parser.add_argument("--limit", type=int, default=None, help="only encode the first N valid objects")
    args = parser.parse_args()
    output = args.output or (DEFAULT_OUT_FAKE if args.fake else DEFAULT_OUT_REAL)
    summary = build(args.corpus, output, args.fake, args.limit)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
