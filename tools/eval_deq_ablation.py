"""Compare QA module performance with DEQ on vs off on 91 QA pairs."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402

FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
           / "final_labels.jsonl")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def macro_f1(confusion: Counter, labels=("support", "refute", "not_in_evidence")) -> float:
    f1s = []
    for label in labels:
        tp = confusion[(label, label)]
        fp = sum(confusion[(pred, label)] for pred in labels if pred != label)
        fn = sum(confusion[(label, gold)] for gold in labels if gold != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)
        f1s.append(f1)
    return sum(f1s) / len(f1s)


def run_eval(use_deq: bool, use_nli: bool = False, label: str = "") -> dict:
    rows = read_jsonl(FROZEN)
    silver = {r["instance_id"]: r for r in read_jsonl(SILVER)}

    semantic_nli = None
    if use_nli:
        from algorithms.consistency.nli_local import NliLocal

        client = NliLocal("mdeberta")
        client.ensure()

        def semantic_nli(pairs):  # noqa: F811
            return client.predict(pairs)

        print(f"  nli ready: mode={client.mode}")

    module = QAConsistencyModule(use_deq=use_deq, semantic_nli=semantic_nli)
    confusion: Counter = Counter()
    methods: Counter = Counter()
    statuses: Counter = Counter()

    for row in rows:
        request = request_from_dict(row)
        result = module.verify(request)
        gold = silver[request.instance_id]["final_verdict"]
        prediction = result.verdict
        confusion[(prediction, gold)] += 1
        methods.update(claim.method for claim in result.claim_results)
        statuses[result.status] += 1

    accuracy = sum(
        confusion[(p, g)] for p in ("support", "refute", "not_in_evidence")
        for g in ("support", "refute", "not_in_evidence") if p == g
    ) / len(rows)
    f1 = macro_f1(confusion)

    confusion_dict = {
        f"{p}|{g}": confusion[(p, g)]
        for p in ("support", "refute", "not_in_evidence")
        for g in ("support", "refute", "not_in_evidence")
        if confusion[(p, g)]
    }
    print(f"\n{'=' * 50}")
    print(f"  {label}")
    print(f"{'=' * 50}")
    print(f"  accuracy:  {accuracy:.4f}")
    print(f"  macro-F1:  {f1:.4f}")
    print(f"  statuses:  {dict(statuses)}")
    print(f"  confusion: {confusion_dict}")
    print(f"  top methods: {dict(methods.most_common(6))}")
    return {"accuracy": round(accuracy, 4), "macro_f1": round(f1, 4),
            "confusion": confusion_dict}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--nli", action="store_true",
                        help="also run with local NLI enabled")
    args = parser.parse_args()

    off = run_eval(use_deq=False, label="DEQ OFF (baseline)")
    on = run_eval(use_deq=True, label="DEQ ON (evidence filtered)")
    delta_f1 = on["macro_f1"] - off["macro_f1"]
    delta_acc = on["accuracy"] - off["accuracy"]
    print(f"\n{'=' * 50}")
    print(f"  DELTA")
    print(f"{'=' * 50}")
    print(f"  macro-F1: {delta_f1:+.4f}")
    print(f"  accuracy: {delta_acc:+.4f}")

    if args.nli:
        off_nli = run_eval(use_deq=False, use_nli=True,
                           label="DEQ OFF + NLI")
        on_nli = run_eval(use_deq=True, use_nli=True,
                          label="DEQ ON + NLI")
        delta_f1_nli = on_nli["macro_f1"] - off_nli["macro_f1"]
        delta_acc_nli = on_nli["accuracy"] - off_nli["accuracy"]
        print(f"\n{'=' * 50}")
        print(f"  DELTA (with NLI)")
        print(f"{'=' * 50}")
        print(f"  macro-F1: {delta_f1_nli:+.4f}")
        print(f"  accuracy: {delta_acc_nli:+.4f}")

    print(f"\n  Verdict: DEQ {'improves' if delta_f1 > 0 else 'degrades' if delta_f1 < 0 else 'neutral'} deterministic-only performance")


if __name__ == "__main__":
    main()
