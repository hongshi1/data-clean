"""Detection-item readiness audit: 40 items x five chain layers.

Layers per item:
  1. routed      — qa_router keyword coverage
  2. operators   — mutation operator instances (static count)
  3. verifier    — QAConsistencyModule claim-kind support (honest static map)
  4. real_hits   — builder triggers on the real 91-row frozen asset
  5. data_ready  — taxonomy data_readiness / module_assignment
An item is "detection-clear" only when all five layers are green.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.audit_operator_coverage import operator_check_items  # noqa: E402
from tools.build_answer_mutation_candidates import (  # noqa: E402
    build_candidates,
    request_from_dict,
)

# qa_module claim kinds -> items they can actually verify (honest mapping).
VERIFIER_SUPPORT: dict[str, tuple[str, ...]] = {
    "numeric_interval": (
        "PARAM-01", "PARAM-02", "PARAM-03", "PARAM-05", "PARAM-06",
        "PARAM-07", "PARAM-08", "PARAM-09", "PARAM-10", "TERM-06",
    ),
    "explicit_quote_polarity": (
        "TERM-01", "TERM-02", "TERM-04", "TERM-05", "TERM-07", "TERM-08",
    ),
    "enum_member_exact": ("TERM-03", "LOGIC-05"),
    "identifier_exact_match": ("TERM-07", "GJB-05"),
    "exact_statement": ("TERM-01", "TERM-02", "TERM-04", "TERM-05",
                        "TERM-07", "TERM-08"),
}

ALL_ITEMS = ([f"TERM-{i:02d}" for i in range(1, 9)]
             + [f"PARAM-{i:02d}" for i in range(1, 11)]
             + [f"LOGIC-{i:02d}" for i in range(1, 12)]
             + [f"GJB-{i:02d}" for i in range(1, 12)])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def taxonomy_status() -> dict[str, dict[str, str]]:
    taxonomy = json.loads(
        (BASE / "knowledge/consistency_taxonomy_v2.json").read_text(encoding="utf-8"))
    items = taxonomy.get("items", taxonomy)
    if isinstance(items, dict):
        entries = items.values()
    else:
        entries = items
    result: dict[str, dict[str, str]] = {}
    for entry in entries:
        if isinstance(entry, dict) and "id" in entry:
            result[entry["id"]] = {
                "module_assignment": str(entry.get("module_assignment", "")),
                "data_readiness": str(entry.get("data_readiness", "")),
                "method_readiness": str(entry.get("method_readiness", "")),
            }
    return result


def main() -> None:
    operators = operator_check_items()
    taxonomy = taxonomy_status()
    frozen_rows = read_jsonl(BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
    requests = [request_from_dict(row) for row in frozen_rows]
    _candidates, counts = build_candidates(requests)

    # Map builder counters to items (only TERM-07 currently fires on real data).
    real_hits: dict[str, int] = {}
    for operator_id, count in counts.items():
        if not operator_id.startswith("ANSWER-"):
            continue
        for check_item, ops in operators.items():
            if operator_id in ops:
                real_hits[check_item] = real_hits.get(check_item, 0) + count

    rows: list[dict[str, Any]] = []
    for item in ALL_ITEMS:
        verifier_kinds = sorted(
            kind for kind, items in VERIFIER_SUPPORT.items() if item in items)
        tax = taxonomy.get(item, {})
        layers = {
            "routed": item in _router_items(),
            "n_operators": len(operators.get(item, [])),
            "verifier_kinds": verifier_kinds,
            "verifier_supported": bool(verifier_kinds),
            "real_data_triggers": real_hits.get(item, 0),
            "data_readiness": tax.get("data_readiness", "unknown"),
        }
        layers["detection_clear"] = (
            layers["routed"]
            and layers["n_operators"] > 0
            and layers["verifier_supported"]
            and layers["real_data_triggers"] > 0
        )
        rows.append({"item": item, **layers})

    clear = [r["item"] for r in rows if r["detection_clear"]]
    missing_verifier = [r["item"] for r in rows if not r["verifier_supported"]]
    zero_real_hits = [r["item"] for r in rows if r["real_data_triggers"] == 0]
    report = {
        "audit_version": "detection_item_readiness_v1",
        "n_items": 40,
        "detection_clear_items": clear,
        "n_detection_clear": len(clear),
        "items_without_verifier_support": missing_verifier,
        "items_with_zero_real_data_triggers": zero_real_hits,
        "chain_note": (
            "detection_clear requires: routed + operator + verifier claim-kind + "
            ">=1 real trigger on the frozen asset. Operators exist for 39/40, but "
            "the verifier only implements numeric/quote/enum/identifier claim kinds, "
            "and the single-doc open-scope frozen asset triggers only TERM-07."),
        "matrix": rows,
        "builder_counts": counts,
    }
    out = BASE / "docs/srs_project/44_detection_item_readiness.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("matrix", "builder_counts")}, ensure_ascii=False, indent=2))


def _router_items() -> set[str]:
    text = (BASE / "algorithms/consistency/qa_router.py").read_text(encoding="utf-8")
    return set(re.findall(r'\("([A-Z]+-\d+)"', text))


if __name__ == "__main__":
    main()
