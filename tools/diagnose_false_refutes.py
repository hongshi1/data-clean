"""Diagnose which expert channels produce false refutes on the silver set."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402


def main() -> None:
    frozen = load_frozen_qa()
    labels = load_silver_labels()

    module = QAConsistencyModule()
    false_refutes: list[tuple[str, str, list[str]]] = []
    for rec in frozen:
        result = module.verify(build_qa_input(rec))
        silver = labels.get(rec["instance_id"], "?")
        if result.verdict == "refute" and silver != "refute":
            methods = sorted(
                {r.method for r in result.claim_results if r.verdict == "refute"})
            false_refutes.append((rec["instance_id"], silver, methods))

    print("false refutes:", len(false_refutes))
    method_counts = Counter(
        method for _, _, methods in false_refutes for method in methods)
    for method, count in method_counts.most_common():
        print(f"  {method}: {count}")
    print()
    for qid, silver, methods in false_refutes:
        print(f"  {qid} silver={silver} {methods}")


if __name__ == "__main__":
    main()
