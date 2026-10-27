#!/usr/bin/env python3
"""Render a self-contained HTML dashboard for the feature_matrix_v1 asset.

Reads the 8 feature jsonl files plus summary.json from the feature matrix
directory, aggregates them into a compact JSON payload, and writes a single
zero-dependency HTML file: inline CSS, inline JS, inline SVG charts, data
embedded via a ``<script type="application/json" id="fm-data">`` block.
Missing input files are tolerated: available sections render normally and
missing ones are flagged with a "missing" badge.

Usage:
  python tools/render_feature_dashboard.py [--input DIR] [--output FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = BASE / "data/gjb_438c/feature_matrix_v1"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/feature_matrix_v1/dashboard.html"

JSONL_FILES = (
    "document_features.jsonl",
    "text_features.jsonl",
    "table_features.jsonl",
    "visio_features.jsonl",
    "diagram_semantic_features.jsonl",
    "claim_slot_features.jsonl",
    "quality_features.jsonl",
    "alignment_features.jsonl",
)
ALL_FILES = JSONL_FILES + ("summary.json",)

MATCHED_STATUSES = ("matched", "match", "aligned", "ok", "accepted")
PARSE_OK_STATUSES = ("ok", "parsed", "success", "complete", "full")
SECTION_TYPE_MAP = (
    ("3.2", "功能需求"),
    ("3.3", "接口需求"),
    ("3.9", "环境资源"),
    ("3.10", "环境资源"),
    ("3.11", "性能需求"),
)
MAX_POOL_PER_DOC = 40
MAX_POOL_TOTAL = 600
REQ_SAMPLE_COUNT = 5
SUMMARY_EMBED_LIMIT = 100_000


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip().rstrip("%")
        if not value:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if 1.0 < number <= 100.0:
        number = number / 100.0
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def to_int(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def to_text(value: Any) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    return str(value).strip()


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return bool(value)


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def fmt_pct(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}%"


def section_type(section: str) -> str:
    parts = to_text(section).split(".")
    prefix = ".".join(parts[:2])
    for key, label in SECTION_TYPE_MAP:
        if prefix == key:
            return label
    return "其他需求"


def count_or_len(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (list, tuple, dict)):
        return len(value)
    return 0


def item_label(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("role_candidate", "role", "state", "type", "name"):
            value = to_text(item.get(key))
            if value:
                return value
        return "unknown"
    return to_text(item) or "unknown"


def bump_counter(counter: Counter[str], value: Any) -> None:
    if isinstance(value, dict):
        for key, cnt in value.items():
            if isinstance(cnt, (int, float)) and not isinstance(cnt, bool):
                counter[str(key)] += int(cnt)
            else:
                counter[str(key)] += 1
    elif isinstance(value, (list, tuple)):
        for item in value:
            counter[item_label(item)] += 1


def sanitize_strings(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("http", "HTTP")
    if isinstance(value, list):
        return [sanitize_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_strings(item) for key, item in value.items()}
    return value


def section_compatible(a: str, b: str) -> bool:
    if not a or not b:
        return True
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")


def build_req_samples(
    documents: list[dict[str, Any]],
    texts: list[dict[str, Any]],
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims_by_doc: dict[str, list[dict[str, Any]]] = {}
    claims_by_id: dict[str, dict[str, Any]] = {}
    for row in claims:
        claims_by_doc.setdefault(to_text(row.get("doc_id")), []).append(row)
        claim_id = to_text(row.get("claim_id"))
        if claim_id:
            claims_by_id[claim_id] = row
    texts_by_doc: dict[str, list[dict[str, Any]]] = {}
    for row in texts:
        if has_value(row.get("requirement_ids")):
            texts_by_doc.setdefault(to_text(row.get("doc_id")), []).append(row)
    doc_names = {to_text(d.get("doc_id")): to_text(d.get("doc_name")) for d in documents}
    doc_order = [to_text(d.get("doc_id")) for d in documents]
    known_docs = set(doc_order)
    for extra_doc in texts_by_doc:
        if extra_doc and extra_doc not in known_docs:
            doc_order.append(extra_doc)

    def best_claim(doc_id: str, section: str, sentence_id: str) -> dict[str, Any] | None:
        exact = claims_by_id.get(sentence_id)
        if exact is not None and to_text(exact.get("doc_id")) == doc_id:
            return exact
        best: dict[str, Any] | None = None
        best_key: tuple[int, float] | None = None
        for row in claims_by_doc.get(doc_id, []):
            if not section_compatible(to_text(row.get("section")), section):
                continue
            parse_ok = to_text(row.get("parse_status")).lower() in PARSE_OK_STATUSES
            rate = to_float(row.get("slot_fill_rate")) or 0.0
            key = (1 if parse_ok else 0, rate)
            if best_key is None or key > best_key:
                best, best_key = row, key
        return best

    def req_card(text_row: dict[str, Any], claim_row: dict[str, Any] | None, doc_name: str) -> dict[str, Any]:
        content = to_text(text_row.get("text"))
        section = to_text(text_row.get("section"))
        subject = to_text(claim_row.get("subject_candidate")) if claim_row else ""
        claim_raw = to_text(claim_row.get("raw_text")) if claim_row else ""
        title = content[:16].rstrip("，。；、：: ") or claim_raw[:16].rstrip("，。；、：: ")
        return {
            "section_label": subject or doc_name,
            "title": title or "（无标题）",
            "type": section_type(section),
            "source": f"{section}节" if section else "—",
            "content": content[:300] or claim_raw[:300] or "—",
        }

    samples: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()

    def try_doc(doc_id: str, skip: int) -> bool:
        candidates = texts_by_doc.get(doc_id, [])
        picks = [row for row in candidates if (doc_id, to_text(row.get("sentence_id"))) not in used]
        if len(picks) <= skip:
            return False
        pick = picks[skip]
        used.add((doc_id, to_text(pick.get("sentence_id"))))
        doc_name = doc_names.get(doc_id) or doc_id or "（未知文档）"
        samples.append(
            req_card(
                pick,
                best_claim(doc_id, to_text(pick.get("section")), to_text(pick.get("sentence_id"))),
                doc_name,
            )
        )
        return True

    for doc_id in doc_order:
        if len(samples) >= REQ_SAMPLE_COUNT:
            break
        try_doc(doc_id, 0)
    if len(samples) < REQ_SAMPLE_COUNT:
        for skip in range(1, 10):
            if len(samples) >= REQ_SAMPLE_COUNT:
                break
            for doc_id in doc_order:
                if len(samples) >= REQ_SAMPLE_COUNT:
                    break
                try_doc(doc_id, skip)
    return samples


def build_payload(input_dir: Path) -> dict[str, Any]:
    paths = {name: input_dir / name for name in ALL_FILES}
    missing = [name for name, path in paths.items() if not path.exists()]
    documents = read_jsonl(paths["document_features.jsonl"])
    texts = read_jsonl(paths["text_features.jsonl"])
    tables = read_jsonl(paths["table_features.jsonl"])
    visio = read_jsonl(paths["visio_features.jsonl"])
    semantics = read_jsonl(paths["diagram_semantic_features.jsonl"])
    claims = read_jsonl(paths["claim_slot_features.jsonl"])
    quality = read_jsonl(paths["quality_features.jsonl"])
    alignment = read_jsonl(paths["alignment_features.jsonl"])
    summary = read_json(paths["summary.json"])

    quality_by_doc: dict[str, dict[str, Any]] = {}
    for row in quality:
        doc_id = to_text(row.get("doc_id"))
        if doc_id:
            quality_by_doc[doc_id] = row

    sent_by_doc: Counter[str] = Counter()
    modal_by_doc: Counter[str] = Counter()
    for row in texts:
        doc_id = to_text(row.get("doc_id"))
        sent_by_doc[doc_id] += 1
        if has_value(row.get("modal_words")):
            modal_by_doc[doc_id] += 1
    claims_by_doc: Counter[str] = Counter()
    for row in claims:
        claims_by_doc[to_text(row.get("doc_id"))] += 1

    docs: list[dict[str, Any]] = []
    for doc in documents:
        doc_id = to_text(doc.get("doc_id"))
        q = quality_by_doc.get(doc_id)
        rates = None
        if q is not None:
            rates = {
                "empty_text_node_rate": to_float(q.get("empty_text_node_rate")),
                "dangling_edge_rate": to_float(q.get("dangling_edge_rate")),
                "unit_completeness": to_float(q.get("unit_completeness")),
                "reference_resolution_rate": to_float(q.get("reference_resolution_rate")),
                "claim_slot_fill_rate": to_float(q.get("claim_slot_fill_rate_avg")),
            }
        docs.append(
            {
                "doc_id": doc_id,
                "doc_name": to_text(doc.get("doc_name")) or doc_id,
                "n_sections": to_int(doc.get("n_sections")),
                "n_requirements_explicit": to_int(doc.get("n_requirements_explicit")),
                "n_requirements_synthetic": to_int(doc.get("n_requirements_synthetic")),
                "n_sentences": sent_by_doc.get(doc_id, 0),
                "n_claims": claims_by_doc.get(doc_id, 0),
                "n_tables": to_int(doc.get("n_tables")),
                "n_table_rows": to_int(doc.get("n_table_rows")),
                "n_images": to_int(doc.get("n_images")),
                "n_diagrams": to_int(doc.get("n_diagrams")),
                "rates": rates,
            }
        )

    n_explicit = sum(to_int(d.get("n_requirements_explicit")) for d in documents)
    n_synthetic = sum(to_int(d.get("n_requirements_synthetic")) for d in documents)
    modal_rate = sum(modal_by_doc.values()) / len(texts) if texts else None
    continuation_rate = (
        sum(1 for t in tables if has_value(t.get("continuation_candidate"))) / len(tables) if tables else None
    )
    total_edges = sum(to_int(v.get("n_edges")) for v in visio)
    total_dangling = sum(to_int(v.get("dangling_ends")) for v in visio)
    dangling_rate = total_dangling / total_edges if total_edges else None
    conf_values = [v for v in (to_float(s.get("confidence")) for s in semantics) if v is not None]
    avg_conf = mean(conf_values)
    sem_matched_rate = (
        sum(1 for s in semantics if has_value(s.get("diagram_id_matched"))) / len(semantics) if semantics else None
    )
    slot_values = [v for v in (to_float(c.get("slot_fill_rate")) for c in claims) if v is not None]
    avg_slot = mean(slot_values)
    unit_values = [v for v in (to_float(q.get("unit_completeness")) for q in quality) if v is not None]
    avg_unit = mean(unit_values)
    matched_links = sum(1 for a in alignment if to_text(a.get("status")).lower() in MATCHED_STATUSES)
    matched_link_rate = matched_links / len(alignment) if alignment else None

    cards = [
        {
            "title": "文档特征",
            "total": len(documents),
            "sub_label": "显式/合成需求",
            "sub_value": f"{n_explicit:,} / {n_synthetic:,}",
            "missing": "document_features.jsonl" in missing,
        },
        {
            "title": "正文特征",
            "total": len(texts),
            "sub_label": "情态句率",
            "sub_value": fmt_pct(modal_rate, 1),
            "missing": "text_features.jsonl" in missing,
        },
        {
            "title": "表格特征",
            "total": len(tables),
            "sub_label": "续表候选率",
            "sub_value": fmt_pct(continuation_rate, 1),
            "missing": "table_features.jsonl" in missing,
        },
        {
            "title": "Visio特征",
            "total": len(visio),
            "sub_label": "悬空边率",
            "sub_value": fmt_pct(dangling_rate, 1),
            "missing": "visio_features.jsonl" in missing,
        },
        {
            "title": "图语义特征",
            "total": len(semantics),
            "sub_label": "置信度均值｜diagram匹配率",
            "sub_value": f"{fmt_pct(avg_conf, 1)}｜{fmt_pct(sem_matched_rate, 1)}",
            "missing": "diagram_semantic_features.jsonl" in missing,
        },
        {
            "title": "五元组特征",
            "total": len(claims),
            "sub_label": "平均槽位填充率",
            "sub_value": fmt_pct(avg_slot, 1),
            "missing": "claim_slot_features.jsonl" in missing,
        },
        {
            "title": "质量信号",
            "total": len(quality),
            "sub_label": "单位完整率均值",
            "sub_value": fmt_pct(avg_unit, 1),
            "missing": "quality_features.jsonl" in missing,
        },
        {
            "title": "对齐特征",
            "total": len(alignment),
            "sub_label": "matched率",
            "sub_value": fmt_pct(matched_link_rate, 1),
            "missing": "alignment_features.jsonl" in missing,
        },
    ]

    type_counts: Counter[str] = Counter()
    conf_by_type: dict[str, list[float]] = {}
    for row in semantics:
        dtype = to_text(row.get("diagram_type")) or "unknown"
        type_counts[dtype] += 1
        conf = to_float(row.get("confidence"))
        if conf is not None:
            conf_by_type.setdefault(dtype, []).append(conf)
    diagram_types = [
        {
            "type": dtype,
            "count": count,
            "avg_conf": mean(conf_by_type[dtype]) if dtype in conf_by_type else None,
        }
        for dtype, count in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    relation_status: dict[str, Counter[str]] = {}
    for row in alignment:
        relation = to_text(row.get("relation_type")) or "unknown"
        status = to_text(row.get("status")).lower() or "unknown"
        relation_status.setdefault(relation, Counter())[status] += 1
    by_relation = [
        {
            "relation_type": rel,
            "total": sum(cnt.values()),
            "statuses": dict(sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))),
        }
        for rel, cnt in sorted(relation_status.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))
    ]
    tier_counts = Counter(to_text(a.get("quality_tier")) or "unknown" for a in alignment)
    tiers = [{"tier": tier, "count": n} for tier, n in sorted(tier_counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    predicate_counts: Counter[str] = Counter()
    with_predicate = 0
    for row in claims:
        predicate = to_text(row.get("predicate_candidate"))
        if predicate:
            predicate_counts[predicate] += 1
            with_predicate += 1
    filled_claims = [
        row for row in claims if to_text(row.get("subject_candidate")) and to_text(row.get("predicate_candidate"))
    ]
    claims_stats = {
        "total": len(claims),
        "filled": len(filled_claims),
        "with_predicate": with_predicate,
        "hit_rate": (with_predicate / len(claims)) if claims else None,
    }
    predicate_top = [
        {"predicate": p, "count": n}
        for p, n in sorted(predicate_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    ]

    filled_sorted = sorted(
        filled_claims,
        key=lambda r: (-(to_float(r.get("slot_fill_rate")) or 0.0), to_text(r.get("claim_id"))),
    )
    pool: list[dict[str, Any]] = []
    pool_per_doc: Counter[str] = Counter()
    for row in filled_sorted:
        doc_id = to_text(row.get("doc_id"))
        if len(pool) >= MAX_POOL_TOTAL or pool_per_doc[doc_id] >= MAX_POOL_PER_DOC:
            continue
        pool_per_doc[doc_id] += 1
        pool.append(
            {
                "claim_id": to_text(row.get("claim_id")),
                "doc_id": doc_id,
                "section": to_text(row.get("section")),
                "kind": to_text(row.get("kind")),
                "raw_text": to_text(row.get("raw_text"))[:200],
                "subject_candidate": to_text(row.get("subject_candidate")),
                "predicate_candidate": to_text(row.get("predicate_candidate")),
                "operator": to_text(row.get("operator")),
                "object_value": to_text(row.get("object_value")),
                "unit": to_text(row.get("unit_canonical")) or to_text(row.get("unit_raw")),
                "slot_fill_rate": to_float(row.get("slot_fill_rate")),
                "parse_status": to_text(row.get("parse_status")),
            }
        )

    merged_total = sum(count_or_len(t.get("merged_cells")) for t in tables)
    empty_per_table = [count_or_len(t.get("empty_cells")) for t in tables]
    empty_state_counter: Counter[str] = Counter()
    for row in tables:
        bump_counter(empty_state_counter, row.get("empty_cells"))
    empty_states = [
        {"state": state, "count": n}
        for state, n in sorted(empty_state_counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    empty_buckets = [
        {"label": "0 个空单元格", "value": sum(1 for n in empty_per_table if n == 0)},
        {"label": "1-5 个空单元格", "value": sum(1 for n in empty_per_table if 1 <= n <= 5)},
        {"label": "6-20 个空单元格", "value": sum(1 for n in empty_per_table if 6 <= n <= 20)},
        {"label": ">20 个空单元格", "value": sum(1 for n in empty_per_table if n > 20)},
    ]
    role_counter: Counter[str] = Counter()
    for row in tables:
        bump_counter(role_counter, row.get("row_roles"))
    row_roles = [
        {"role": role, "count": n} for role, n in sorted(role_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
    ]
    table_stats = {
        "n_tables": len(tables),
        "total_rows": sum(to_int(t.get("n_rows")) for t in tables),
        "merged_total": merged_total,
        "empty_total": sum(empty_per_table),
        "empty_states": empty_states,
        "empty_buckets": empty_buckets,
        "row_roles": row_roles,
    }

    req_samples = build_req_samples(documents, texts, claims)

    if summary is None:
        summary_view = None if "summary.json" in missing else {"error": "summary.json 无法解析"}
    elif len(json.dumps(summary, ensure_ascii=False)) <= SUMMARY_EMBED_LIMIT:
        summary_view = summary
    else:
        summary_view = {
            key: value
            for key, value in summary.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }

    file_hashes = {name: sha256_file(path) for name, path in paths.items() if path.exists()}
    combined = hashlib.sha256()
    for name in ALL_FILES:
        if name in file_hashes:
            combined.update(f"{name}:{file_hashes[name]}\n".encode("utf-8"))
    meta = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "missing": missing,
        "row_counts": {
            "document_features.jsonl": len(documents),
            "text_features.jsonl": len(texts),
            "table_features.jsonl": len(tables),
            "visio_features.jsonl": len(visio),
            "diagram_semantic_features.jsonl": len(semantics),
            "claim_slot_features.jsonl": len(claims),
            "quality_features.jsonl": len(quality),
            "alignment_features.jsonl": len(alignment),
        },
        "summary_hash": file_hashes.get("summary.json", "missing"),
        "combined_hash": combined.hexdigest(),
    }
    payload = {
        "meta": meta,
        "cards": cards,
        "docs": docs,
        "diagram_types": diagram_types,
        "alignment": {"by_relation": by_relation, "tiers": tiers},
        "claims_stats": claims_stats,
        "predicate_top": predicate_top,
        "claims_pool": pool,
        "table_stats": table_stats,
        "req_samples": req_samples,
        "summary": summary_view,
    }
    return sanitize_strings(payload)


HTML_TEMPLATE = (
    """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SRS 特征矩阵 v1 Dashboard</title>
<style>
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { background: #f2f5f9; color: #1a2332; font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", system-ui, sans-serif; font-size: 14px; line-height: 1.5; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 24px 20px 40px; }
header { background: #ffffff; border: 1px solid #e3e8ee; border-radius: 12px; padding: 18px 22px; }
header h1 { margin: 0 0 6px; font-size: 20px; letter-spacing: 0.5px; }
header .meta { color: #5c6b7a; font-size: 12px; }
section { background: #ffffff; border: 1px solid #e3e8ee; border-radius: 12px; padding: 16px 20px; margin: 16px 0; }
section h2 { margin: 0 0 12px; font-size: 16px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
section h3 { margin: 14px 0 8px; font-size: 13px; color: #33404d; }
.badge { font-size: 11px; font-weight: 600; padding: 1px 10px; border-radius: 999px; background: #fde3e5; color: #b02a36; white-space: nowrap; }
.badge.ok { background: #e3f2e6; color: #256b2c; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
.card { border: 1px solid #e3e8ee; border-radius: 10px; padding: 12px 14px; background: #fbfcfe; }
.card.miss { opacity: 0.55; }
.card .t { color: #5c6b7a; font-size: 12px; display: flex; align-items: center; gap: 6px; }
.card .n { font-size: 26px; font-weight: 700; margin-top: 2px; font-variant-numeric: tabular-nums; }
.card .s { color: #5c6b7a; font-size: 12px; margin-top: 4px; }
.tbl-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 12px; }
th, td { border: 1px solid #e3e8ee; padding: 4px 9px; text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
th { background: #eef2f7; color: #33404d; font-weight: 600; }
th.l, td.l { text-align: left; }
td.name, td.content { white-space: normal; }
td.name { min-width: 150px; max-width: 230px; }
td.content { min-width: 240px; max-width: 380px; }
tbody tr:hover td { background: #f6f9fc; }
td.q { font-weight: 600; }
.legend { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #5c6b7a; margin-bottom: 10px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
svg { display: block; }
.stats { font-size: 13px; color: #33404d; margin: 6px 0 12px; }
.stats b { color: #1a2332; font-variant-numeric: tabular-nums; }
.toolbar { display: flex; align-items: center; gap: 10px; margin: 12px 0 8px; font-size: 13px; flex-wrap: wrap; }
select { padding: 4px 10px; border: 1px solid #cdd6e0; border-radius: 6px; background: #ffffff; font: inherit; color: inherit; }
select:focus { outline: 2px solid #8fb8ff; outline-offset: 1px; }
.muted { color: #5c6b7a; font-size: 12px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.chip { border: 1px solid #cdd6e0; border-radius: 999px; padding: 2px 12px; font-size: 12px; background: #fbfcfe; font-variant-numeric: tabular-nums; }
.req-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 12px; }
.req { border: 1px solid #e3e8ee; border-left: 4px solid #2f6fed; border-radius: 10px; padding: 10px 14px; background: #fbfcfe; }
.req dl { margin: 0; display: grid; grid-template-columns: 52px 1fr; gap: 3px 10px; font-size: 12px; }
.req dt { color: #5c6b7a; white-space: nowrap; }
.req dd { margin: 0; color: #1a2332; }
.req dd.content { white-space: normal; line-height: 1.6; }
.empty { color: #8a94a3; font-style: italic; font-size: 13px; margin: 6px 0; }
footer { margin-top: 20px; padding: 16px 20px; background: #ffffff; border: 1px solid #e3e8ee; border-radius: 12px; font-size: 12px; color: #5c6b7a; line-height: 1.8; }
footer .policy { background: #fdf6e3; border: 1px solid #eadfae; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; color: #7a5c00; }
footer code { background: #eef2f7; border-radius: 4px; padding: 1px 6px; font-family: Consolas, "Courier New", monospace; font-size: 11px; color: #33404d; word-break: break-all; }
footer details { margin-top: 8px; }
footer pre { background: #f6f9fc; border: 1px solid #e3e8ee; border-radius: 8px; padding: 10px 12px; overflow: auto; max-height: 300px; font-size: 11px; font-family: Consolas, "Courier New", monospace; margin: 8px 0 0; }
@media print { body { background: #ffffff; } section, header, footer { border: 1px solid #cccccc; break-inside: avoid; } .tbl-wrap { overflow: visible; } }
@media (max-width: 720px) { .wrap { padding: 12px 10px 24px; } .card .n { font-size: 22px; } }
</style>
</head>
<body>
"""
    """<div class="wrap">
<header>
<h1>SRS 特征矩阵 v1 — 可视化 Dashboard</h1>
<div class="meta" id="head-meta"></div>
</header>
<section>
<h2>① 特征总览</h2>
<div class="cards" id="cards"></div>
</section>
<section>
<h2>② 文档级特征矩阵 <span id="doc-badge"></span></h2>
<p class="muted">计数来自 document_features / 正文 / 五元组；质量率来自 quality_features。红黄绿背景阈值：&gt;0.66 绿 / 0.33-0.66 黄 / &lt;0.33 红；空文本率与悬空边率为反向指标（低=好），计分反转。</p>
<div id="doc-table"></div>
</section>
<section>
<h2>③ 质量信号 — 每文档 5 项质量率 <span id="q-badge"></span></h2>
<div id="quality-chart"></div>
</section>
<section>
<h2>④ 图语义 — diagram_type 分布（计数 + 置信度均值）<span id="dt-badge"></span></h2>
<div id="diagram-types"></div>
</section>
<section>
<h2>⑤ 对齐状态 — relation_type × status + quality_tier <span id="al-badge"></span></h2>
<div id="align-chart"></div>
<div class="chips" id="align-tiers"></div>
</section>
<section>
<h2>⑥ Claim 五元组浏览 <span id="cl-badge"></span></h2>
<div class="stats" id="claims-stats"></div>
<h3>谓词命中率 Top15</h3>
<div id="predicate-bars"></div>
<h3>已填充 claim 抽样（主语+谓词齐全，按槽位填充率降序，展示前 20 条）</h3>
<div class="toolbar">
<label for="claim-doc-select">按文档过滤：</label>
<select id="claim-doc-select"></select>
<span class="muted" id="claim-count"></span>
</div>
<div class="tbl-wrap">
<table>
<thead><tr><th class="l content">原文（截断80字）</th><th class="l">主语 subject</th><th class="l">谓词 predicate</th><th class="l">算子+值+单位</th><th>槽位填充率</th></tr></thead>
<tbody id="claim-rows"></tbody>
</table>
</div>
</section>
<section>
<h2>⑦ 表格细粒度统计 <span id="tb-badge"></span></h2>
<div class="stats" id="table-totals"></div>
<h3>空值状态分布（empty_cells 的 state 计数）</h3>
<div id="empty-states"></div>
<h3>空单元格数量分布（按表分桶）</h3>
<div id="empty-dist"></div>
<h3>行角色分布（row_roles 的 role_candidate 计数）</h3>
<div id="role-dist"></div>
</section>
<section>
<h2>⑧ REQ 示例卡片（requirements + claim_slot 拼装）</h2>
<p class="muted">类型由章节号前缀映射：3.2→功能需求 / 3.3→接口需求 / 3.9-3.10→环境资源 / 3.11→性能需求 / 其他→其他需求。</p>
<div class="req-grid" id="req-cards"></div>
</section>
<footer>
<div class="policy">使用声明：质量信号=风险非缺陷；槽位=候选非gold；图语义对齐可能unmatched。本页全部数据来自特征矩阵提取结果，仅用于数据质量概览，不构成对文档本身的判定。</div>
<div>生成时间：<code id="gen-time"></code></div>
<div>输入目录：<code id="input-dir"></code></div>
<div>缺失输入：<code id="missing-files"></code></div>
<div>summary.json sha256：<code id="summary-hash"></code></div>
<div>全部输入 combined sha256：<code id="combined-hash"></code></div>
<details><summary>summary.json 原始内容</summary><pre id="summary-view"></pre></details>
</footer>
</div>
"""
    """<script type="application/json" id="fm-data">__PAYLOAD__</script>
<script>
(function () {
"use strict";
var D = JSON.parse(document.getElementById("fm-data").textContent);
var MISSING = D.meta.missing || [];
var METRICS = [
  { key: "empty_text_node_rate", label: "空文本率", color: "#e53935", inverted: true },
  { key: "dangling_edge_rate", label: "悬空边率", color: "#fb8c00", inverted: true },
  { key: "unit_completeness", label: "单位完整率", color: "#43a047", inverted: false },
  { key: "reference_resolution_rate", label: "引用解析率", color: "#1e88e5", inverted: false },
  { key: "claim_slot_fill_rate", label: "槽位填充率", color: "#8e24aa", inverted: false }
];
function miss(name) { return MISSING.indexOf(name) >= 0; }
function esc(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function fmtNum(value) {
  if (value === null || value === undefined || value === "") return "—";
  var n = Number(value);
  return isNaN(n) ? String(value) : n.toLocaleString("en-US");
}
function pct(value) { return value === null || value === undefined ? "—" : Math.round(value * 100) + "%"; }
function pct1(value) { return value === null || value === undefined ? "—" : (value * 100).toFixed(1) + "%"; }
function trunc(value, n) {
  var s = String(value === null || value === undefined ? "" : value);
  return s.length > n ? s.slice(0, n) + "…" : s;
}
function empty(msg) { return '<p class="empty">' + esc(msg) + "</p>"; }
function svgWrap(w, h, inner) {
  return '<svg width="100%" viewBox="0 0 ' + w + " " + h + '" preserveAspectRatio="xMinYMin meet">' + inner + "</svg>";
}
function badge(el, name, okText) {
  var host = document.getElementById(el);
  if (!host) return;
  host.innerHTML = miss(name) ? '<span class="badge">missing</span>' : '<span class="badge ok">' + esc(okText) + "</span>";
}
function qPair(value, inverted) {
  if (value === null || value === undefined) return ["#f2f4f7", "#8a94a3"];
  var score = inverted ? 1 - value : value;
  if (score > 0.66) return ["#e3f2e6", "#256b2c"];
  if (score >= 0.33) return ["#fdf3d7", "#8a6a00"];
  return ["#fde3e5", "#b02a36"];
}
function renderCards() {
  var host = document.getElementById("cards");
  host.innerHTML = (D.cards || []).map(function (c) {
    return '<div class="card' + (c.missing ? " miss" : "") + '">' +
      '<div class="t">' + esc(c.title) + (c.missing ? ' <span class="badge">missing</span>' : "") + "</div>" +
      '<div class="n">' + fmtNum(c.total) + "</div>" +
      '<div class="s">' + esc(c.sub_label) + "：" + esc(c.sub_value) + "</div></div>";
  }).join("");
}
function renderDocs() {
  var host = document.getElementById("doc-table");
  var docs = D.docs || [];
  badge("doc-badge", "document_features.jsonl", fmtNum(docs.length) + " 文档");
  if (!docs.length) { host.innerHTML = empty(miss("document_features.jsonl") ? "document_features.jsonl missing" : "无文档数据"); return; }
  var cols = [
    ["doc_id", "文档", "l"],
    ["doc_name", "名称", "l name"],
    ["n_sections", "章节"],
    ["n_requirements_explicit", "显式需求"],
    ["n_requirements_synthetic", "合成需求"],
    ["n_sentences", "句子"],
    ["n_claims", "claim"],
    ["n_tables", "表格"],
    ["n_table_rows", "表格行"],
    ["n_images", "图片"],
    ["n_diagrams", "图表"]
  ];
  var head = "<tr>" + cols.map(function (c) { return '<th class="' + (c[2] || "") + '">' + esc(c[1]) + "</th>"; }).join("") +
    METRICS.map(function (m) { return "<th>" + esc(m.label) + "</th>"; }).join("") + "</tr>";
  var body = docs.map(function (d) {
    var cells = cols.map(function (c) {
      var v = d[c[0]];
      return '<td class="' + (c[2] || "") + '">' + (v === null || v === undefined ? "—" : fmtNum(v)) + "</td>";
    }).join("");
    var qcells = METRICS.map(function (m) {
      var v = d.rates ? d.rates[m.key] : null;
      var pair = qPair(v, m.inverted);
      return '<td class="q" style="background:' + pair[0] + ";color:" + pair[1] + '">' + pct(v) + "</td>";
    }).join("");
    return "<tr>" + cells + qcells + "</tr>";
  }).join("");
  host.innerHTML = '<div class="tbl-wrap"><table><thead>' + head + "</thead><tbody>" + body + "</tbody></table></div>";
}
"""
    """function renderQuality() {
  var host = document.getElementById("quality-chart");
  var docs = (D.docs || []).filter(function (d) { return d.rates; });
  badge("q-badge", "quality_features.jsonl", fmtNum(docs.length) + " 文档");
  if (!docs.length) { host.innerHTML = empty(miss("quality_features.jsonl") ? "quality_features.jsonl missing" : "无质量信号数据"); return; }
  var W = 940, labelW = 130, valW = 46, top = 8, rowH = 76, barH = 9, step = 12;
  var barW = W - labelW - valW;
  var parts = [];
  docs.forEach(function (d, i) {
    var y0 = top + i * rowH;
    parts.push('<text x="' + (labelW - 8) + '" y="' + (y0 + 12) + '" text-anchor="end" font-size="11" font-weight="600" fill="#1a2332">' + esc(d.doc_id) + "</text>");
    METRICS.forEach(function (m, j) {
      var y = y0 + 18 + j * step;
      var v = d.rates[m.key];
      parts.push('<rect x="' + labelW + '" y="' + y + '" width="' + barW + '" height="' + barH + '" rx="2" fill="#edf1f5"/>');
      if (v !== null && v !== undefined) {
        var w = Math.max(0, Math.min(1, v)) * barW;
        parts.push('<rect x="' + labelW + '" y="' + y + '" width="' + w.toFixed(1) + '" height="' + barH + '" rx="2" fill="' + m.color + '"/>');
      }
      parts.push('<text x="' + (labelW + barW + 6) + '" y="' + (y + barH - 1) + '" font-size="10" fill="#5c6b7a">' + pct(v) + "</text>");
    });
  });
  var legend = '<div class="legend">' + METRICS.map(function (m) {
    return '<span><i style="background:' + m.color + '"></i>' + esc(m.label) + (m.inverted ? "（反向：低=好）" : "") + "</span>";
  }).join("") + "</div>";
  host.innerHTML = legend + svgWrap(W, top + docs.length * rowH + 6, parts.join(""));
}
function hbars(hostId, items, opts) {
  var host = document.getElementById(hostId);
  if (!host) return;
  opts = opts || {};
  if (!items || !items.length) { host.innerHTML = empty(opts.missingText || "暂无数据"); return; }
  var W = 940, labelW = opts.labelW || 170, valW = opts.valW || 130, top = 6, rowH = opts.rowH || 26, barH = 15;
  var barW = W - labelW - valW;
  var max = 0;
  items.forEach(function (it) { if (it.value > max) max = it.value; });
  if (max < 1) max = 1;
  var parts = items.map(function (it, i) {
    var y = top + i * rowH + (rowH - barH) / 2;
    var w = (it.value / max) * barW;
    var s = '<text x="' + (labelW - 10) + '" y="' + (y + barH - 3) + '" text-anchor="end" font-size="12" fill="#33404d">' + esc(trunc(it.label, 26)) + "</text>";
    s += '<rect x="' + labelW + '" y="' + y + '" width="' + barW + '" height="' + barH + '" rx="3" fill="#edf1f5"/>';
    if (w > 0) s += '<rect x="' + labelW + '" y="' + y + '" width="' + w.toFixed(1) + '" height="' + barH + '" rx="3" fill="' + (it.color || opts.color || "#1e88e5") + '"/>';
    s += '<text x="' + (labelW + barW + 8) + '" y="' + (y + barH - 3) + '" font-size="12" fill="#33404d">' + esc(it.text !== undefined && it.text !== null ? it.text : fmtNum(it.value)) + "</text>";
    return s;
  }).join("");
  host.innerHTML = svgWrap(W, top + items.length * rowH + 6, parts);
}
function renderDiagramTypes() {
  var rows = (D.diagram_types || []).map(function (t) {
    return { label: t.type, value: t.count, text: fmtNum(t.count) + " ｜ conf均值 " + pct1(t.avg_conf), color: "#00897b" };
  });
  badge("dt-badge", "diagram_semantic_features.jsonl", fmtNum((D.diagram_types || []).length) + " 类型");
  hbars("diagram-types", rows, { labelW: 210, missingText: miss("diagram_semantic_features.jsonl") ? "diagram_semantic_features.jsonl missing" : "暂无图语义数据" });
}
function renderAlignment() {
  var host = document.getElementById("align-chart");
  var data = D.alignment || {};
  var rows = data.by_relation || [];
  badge("al-badge", "alignment_features.jsonl", fmtNum(rows.length) + " relation_type");
  if (!rows.length) {
    host.innerHTML = empty(miss("alignment_features.jsonl") ? "alignment_features.jsonl missing" : "暂无对齐数据");
    document.getElementById("align-tiers").innerHTML = "";
    return;
  }
  var statuses = [];
  rows.forEach(function (r) { Object.keys(r.statuses).forEach(function (s) { if (statuses.indexOf(s) < 0) statuses.push(s); }); });
  statuses.sort();
  var palette = ["#1e88e5", "#43a047", "#e53935", "#fb8c00", "#8e24aa", "#00897b", "#546e7a", "#d81b60"];
  var colorOf = {};
  statuses.forEach(function (s, i) { colorOf[s] = palette[i % palette.length]; });
  var W = 940, labelW = 200, valW = 100, top = 8, rowH = 28, barH = 16;
  var barW = W - labelW - valW;
  var max = 0;
  rows.forEach(function (r) { if (r.total > max) max = r.total; });
  if (max < 1) max = 1;
  var parts = rows.map(function (r, i) {
    var y = top + i * rowH + (rowH - barH) / 2;
    var s = '<text x="' + (labelW - 10) + '" y="' + (y + barH - 4) + '" text-anchor="end" font-size="12" fill="#33404d">' + esc(trunc(r.relation_type, 26)) + "</text>";
    s += '<rect x="' + labelW + '" y="' + y + '" width="' + barW + '" height="' + barH + '" rx="3" fill="#edf1f5"/>';
    var x = labelW;
    statuses.forEach(function (st) {
      var v = r.statuses[st] || 0;
      if (!v) return;
      var w = (v / max) * barW;
      s += '<rect x="' + x.toFixed(1) + '" y="' + y + '" width="' + Math.max(w - 0.5, 0).toFixed(1) + '" height="' + barH + '" fill="' + colorOf[st] + '"/>';
      x += w;
    });
    s += '<text x="' + (labelW + barW + 8) + '" y="' + (y + barH - 4) + '" font-size="12" fill="#33404d">' + fmtNum(r.total) + "</text>";
    return s;
  }).join("");
  var legend = '<div class="legend">' + statuses.map(function (st) {
    return '<span><i style="background:' + colorOf[st] + '"></i>' + esc(st) + "</span>";
  }).join("") + "</div>";
  host.innerHTML = legend + svgWrap(W, top + rows.length * rowH + 6, parts);
  var tiers = data.tiers || [];
  document.getElementById("align-tiers").innerHTML = tiers.length
    ? tiers.map(function (t) { return '<span class="chip">tier ' + esc(t.tier) + "：" + fmtNum(t.count) + "</span>"; }).join("")
    : '<span class="empty">无 quality_tier 记录</span>';
}
"""
    """function renderClaims() {
  var stats = D.claims_stats || {};
  badge("cl-badge", "claim_slot_features.jsonl", fmtNum(stats.total) + " claim");
  document.getElementById("claims-stats").innerHTML =
    "claim 总数 <b>" + fmtNum(stats.total) + "</b>｜已填充（主语+谓词） <b>" + fmtNum(stats.filled) + "</b>｜谓词覆盖率 <b>" + pct(stats.hit_rate) + "</b>";
  var top = (D.predicate_top || []).map(function (p) {
    return { label: p.predicate, value: p.count, text: fmtNum(p.count), color: "#8e24aa" };
  });
  hbars("predicate-bars", top, { labelW: 170, missingText: miss("claim_slot_features.jsonl") ? "claim_slot_features.jsonl missing" : "暂无谓词数据" });
  var pool = D.claims_pool || [];
  var select = document.getElementById("claim-doc-select");
  var tbody = document.getElementById("claim-rows");
  var counter = document.getElementById("claim-count");
  if (!pool.length) {
    select.style.display = "none";
    tbody.innerHTML = '<tr><td colspan="5" class="empty">' + esc(miss("claim_slot_features.jsonl") ? "claim_slot_features.jsonl missing" : "无已填充claim样本") + "</td></tr>";
    counter.textContent = "";
    return;
  }
  var docs = [];
  pool.forEach(function (c) { if (docs.indexOf(c.doc_id) < 0) docs.push(c.doc_id); });
  docs.sort();
  select.innerHTML = '<option value="">全部文档（' + pool.length + " 条）</option>" + docs.map(function (d) {
    return '<option value="' + esc(d) + '">' + esc(d) + "</option>";
  }).join("");
  function renderRows() {
    var filtered = select.value ? pool.filter(function (c) { return c.doc_id === select.value; }) : pool;
    var rows = filtered.slice(0, 20).map(function (c) {
      var ov = [c.operator, c.object_value, c.unit].filter(function (x) { return x !== undefined && x !== null && String(x) !== ""; }).join(" ");
      return "<tr>" +
        '<td class="l content">' + esc(trunc(c.raw_text, 80)) + "</td>" +
        '<td class="l">' + esc(c.subject_candidate || "—") + "</td>" +
        '<td class="l">' + esc(c.predicate_candidate || "—") + "</td>" +
        '<td class="l">' + esc(ov || "—") + "</td>" +
        "<td>" + pct(c.slot_fill_rate) + "</td></tr>";
    }).join("");
    tbody.innerHTML = rows || '<tr><td colspan="5" class="empty">该文档无已填充claim</td></tr>';
    counter.textContent = "展示前 " + Math.min(20, filtered.length) + " / " + filtered.length + " 条（按槽位填充率降序）";
  }
  select.onchange = renderRows;
  renderRows();
}
function renderTableStats() {
  var st = D.table_stats || {};
  badge("tb-badge", "table_features.jsonl", fmtNum(st.n_tables) + " 表格");
  document.getElementById("table-totals").innerHTML =
    "表格数 <b>" + fmtNum(st.n_tables) + "</b>｜总行数 <b>" + fmtNum(st.total_rows) + "</b>｜合并单元格总数 <b>" + fmtNum(st.merged_total) + "</b>｜空单元格总数 <b>" + fmtNum(st.empty_total) + "</b>";
  hbars("empty-states", (st.empty_states || []).map(function (e) {
    return { label: e.state, value: e.count, text: fmtNum(e.count), color: "#e53935" };
  }), { labelW: 170, missingText: miss("table_features.jsonl") ? "table_features.jsonl missing" : "暂无空值状态数据" });
  hbars("empty-dist", (st.empty_buckets || []).map(function (b) {
    return { label: b.label, value: b.value, text: fmtNum(b.value) + " 张表", color: "#fb8c00" };
  }), { labelW: 170, missingText: miss("table_features.jsonl") ? "table_features.jsonl missing" : "暂无表格数据" });
  hbars("role-dist", (st.row_roles || []).map(function (r) {
    return { label: r.role, value: r.count, text: fmtNum(r.count), color: "#1e88e5" };
  }), { labelW: 170, missingText: miss("table_features.jsonl") ? "table_features.jsonl missing" : "暂无行角色数据" });
}
function renderReq() {
  var host = document.getElementById("req-cards");
  var samples = D.req_samples || [];
  if (!samples.length) { host.innerHTML = empty(miss("text_features.jsonl") ? "text_features.jsonl missing" : "无带需求编号的句子可供拼装REQ示例"); return; }
  host.innerHTML = samples.map(function (s) {
    return '<div class="req"><dl>' +
      "<dt>章节</dt><dd>" + esc(s.section_label || "—") + "</dd>" +
      "<dt>标题</dt><dd>" + esc(s.title || "—") + "</dd>" +
      "<dt>类型</dt><dd>" + esc(s.type || "—") + "</dd>" +
      "<dt>来源</dt><dd>" + esc(s.source || "—") + "</dd>" +
      '<dt>内容</dt><dd class="content">' + esc(s.content || "—") + "</dd>" +
      "</dl></div>";
  }).join("");
}
function renderFooter() {
  document.getElementById("gen-time").textContent = D.meta.generated_at || "—";
  document.getElementById("input-dir").textContent = D.meta.input_dir || "—";
  document.getElementById("missing-files").textContent = MISSING.length ? MISSING.join(", ") : "无（输入齐全）";
  document.getElementById("summary-hash").textContent = D.meta.summary_hash || "—";
  document.getElementById("combined-hash").textContent = D.meta.combined_hash || "—";
  document.getElementById("head-meta").textContent = "输入：" + (D.meta.input_dir || "") + "｜生成：" + (D.meta.generated_at || "") + "｜缺失输入 " + MISSING.length + " 项";
  var view = document.getElementById("summary-view");
  view.textContent = D.summary === null || D.summary === undefined ? "summary.json 缺失或不可解析" : JSON.stringify(D.summary, null, 2);
}
renderCards();
renderDocs();
renderQuality();
renderDiagramTypes();
renderAlignment();
renderClaims();
renderTableStats();
renderReq();
renderFooter();
})();
</script>
</body>
</html>
"""
)


def write_dashboard(payload: dict[str, Any], output: Path) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__PAYLOAD__", payload_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(html)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render feature_matrix_v1 self-contained HTML dashboard")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="feature matrix directory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output HTML path")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    input_dir = args.input if args.input.is_absolute() else BASE / args.input
    output = args.output if args.output.is_absolute() else BASE / args.output
    if not input_dir.exists():
        print(f"[warn] input directory missing: {input_dir} -> rendering all-missing dashboard")
    payload = build_payload(input_dir)
    write_dashboard(payload, output)
    size = output.stat().st_size if output.exists() else 0
    snapshot = {
        "input_dir": str(input_dir),
        "output": str(output),
        "output_bytes": size,
        "missing_inputs": payload["meta"]["missing"],
        "row_counts": payload["meta"]["row_counts"],
        "cards": {card["title"]: card["total"] for card in payload["cards"]},
        "req_samples": len(payload["req_samples"]),
        "claims_pool": len(payload["claims_pool"]),
    }
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
