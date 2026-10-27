"""Coverage matrix: 40 taxonomy items x operator/verifier/router/data status."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

MODULES = (
    "algorithms/consistency/answer_mutations.py",
    "algorithms/consistency/structural_mutations.py",
    "algorithms/consistency/term_mutations.py",
    "algorithms/consistency/param_mutations.py",
    "algorithms/consistency/logic_mutations.py",
    "algorithms/consistency/gjb_mutations.py",
)

TERM_ITEMS = [f"TERM-{i:02d}" for i in range(1, 9)]
PARAM_ITEMS = [f"PARAM-{i:02d}" for i in range(1, 11)]
LOGIC_ITEMS = [f"LOGIC-{i:02d}" for i in range(1, 12)]
GJB_ITEMS = [f"GJB-{i:02d}" for i in range(1, 12)]
ALL_ITEMS = TERM_ITEMS + PARAM_ITEMS + LOGIC_ITEMS + GJB_ITEMS


def operator_check_items() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for path in MODULES:
        text = (BASE / path).read_text(encoding="utf-8")
        operator_positions = [
            (m.start(), m.group(1))
            for m in re.finditer(r'operator_id="?(ANSWER-[A-Z0-9-]+)"?', text)
        ]
        for match in re.finditer(r'check_item[^=\n]*=\s*"([A-Z]+-\d+)"', text):
            check_item = match.group(1)
            center = match.start()
            nearby = [
                op for pos, op in operator_positions
                if abs(pos - center) <= 600
            ]
            if nearby:
                result.setdefault(check_item, set()).update(nearby)
        for check_item, operator_id in re.findall(
                r'\("([A-Z]+-\d+)",\s*"(ANSWER-[^"]+)"', text):
            result.setdefault(check_item, set()).add(operator_id)
    # Dynamically attributed operators (computed/default check_item values).
    result.setdefault("TERM-06", set()).update({
        "ANSWER-NUM-EQUIV-V1", "ANSWER-PARAM-NUM-EQUIV-SUPPORT-V1"})
    return result


def router_items() -> set[str]:
    text = (BASE / "algorithms/consistency/qa_router.py").read_text(encoding="utf-8")
    return set(re.findall(r'\("([A-Z]+-\d+)"', text))


def main() -> None:
    operators = operator_check_items()
    router = router_items()
    rows: list[dict] = []
    for item in ALL_ITEMS:
        ops = sorted(operators.get(item, []))
        rows.append({
            "item": item,
            "n_operators": len(ops),
            "operators": ops,
            "routed": item in router,
            "gap": ("OPERATOR_MISSING" if not ops
                    else "ROUTER_MISSING" if item not in router else "ok"),
        })
    missing_ops = [r["item"] for r in rows if r["n_operators"] == 0]
    missing_router = [r["item"] for r in rows if not r["routed"]]
    report = {
        "total_items": len(ALL_ITEMS),
        "items_with_operators": len(rows) - len(missing_ops),
        "total_operator_instances": sum(r["n_operators"] for r in rows),
        "items_missing_operators": missing_ops,
        "items_missing_router": missing_router,
        "matrix": rows,
    }
    out = BASE / "docs/srs_project/43_operator_coverage_matrix.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "matrix"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
