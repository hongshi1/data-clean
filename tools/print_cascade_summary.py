"""Print cascade config summary from the latest eval_cascade run."""
from __future__ import annotations

import json
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else (
    "data/gjb_438c/runs/eval_cascade_1e92cdce_20261027_024429/result.json")


def main() -> None:
    res = json.load(open(PATH, encoding="utf-8"))
    for name, cfg in res["configs"].items():
        llm_calls = cfg.get("llm_calls", "?")
        print(f"== {name}: acc={cfg['accuracy']:.4f} "
              f"macroF1={cfg['macro_f1']:.4f} LLM={llm_calls}")
        for cls, m in cfg["per_class"].items():
            print(f"   {cls}: P={m['precision']:.3f} "
                  f"R={m['recall']:.3f} F1={m['f1']:.3f}")
        conf = cfg.get("confusion[predicted, silver]", {})
        print("   confusion:", conf)
        print()


if __name__ == "__main__":
    main()
