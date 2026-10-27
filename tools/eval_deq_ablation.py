"""Compare QA module performance with DEQ on vs off on 91 QA pairs."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    accuracy,
    confusion_dict,
    evaluate_module,
    load_frozen_qa,
    load_silver_labels,
    macro_f1,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
           / "final_labels.jsonl")


def run_eval(use_deq: bool, use_nli: bool = False, label: str = "") -> dict:
    rows = load_frozen_qa(FROZEN)
    silver = load_silver_labels(SILVER)

    semantic_nli = None
    if use_nli:
        from algorithms.consistency.nli_local import NliLocal

        client = NliLocal("mdeberta")
        client.ensure()

        def semantic_nli(pairs):  # noqa: F811
            return client.predict(pairs)

        print(f"  nli ready: mode={client.mode}")

    module = QAConsistencyModule(use_deq=use_deq, semantic_nli=semantic_nli)
    outcome = evaluate_module(module, rows, silver)
    confusion = outcome.confusion

    acc = accuracy(confusion, len(rows))
    f1 = macro_f1(confusion)
    confusion_out = confusion_dict(confusion)
    print(f"\n{'=' * 50}")
    print(f"  {label}")
    print(f"{'=' * 50}")
    print(f"  accuracy:  {acc:.4f}")
    print(f"  macro-F1:  {f1:.4f}")
    print(f"  statuses:  {dict(outcome.statuses)}")
    print(f"  confusion: {confusion_out}")
    print(f"  top methods: {dict(outcome.methods.most_common(6))}")
    return {"accuracy": acc, "macro_f1": f1, "confusion": confusion_out}


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
    print("  DELTA")
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
        print("  DELTA (with NLI)")
        print(f"{'=' * 50}")
        print(f"  macro-F1: {delta_f1_nli:+.4f}")
        print(f"  accuracy: {delta_acc_nli:+.4f}")

    print(f"\n  Verdict: DEQ {'improves' if delta_f1 > 0 else 'degrades' if delta_f1 < 0 else 'neutral'} deterministic-only performance")


if __name__ == "__main__":
    main()
