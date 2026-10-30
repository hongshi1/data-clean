"""Print paper matrix baseline summary from a run directory."""
from __future__ import annotations

import json
import sys

PATH = (sys.argv[1] if len(sys.argv) > 1 else
        "data/gjb_438c/runs/eval_paper_matrix_c409df7f_20261030_122944"
        "/result.json")


def main() -> None:
    res = json.load(open(PATH, encoding="utf-8"))
    for name, cfg in res["baselines"].items():
        pc = cfg["per_class"]
        llm = cfg.get("llm_api_calls", cfg.get("llm_calls", "?"))
        print(f"{name}: acc={cfg['accuracy']:.3f} "
              f"macroF1={cfg['macro_f1']:.3f} "
              f"S-F1={pc['support']['f1']:.3f} "
              f"R-F1={pc['refute']['f1']:.3f} "
              f"R-P={pc['refute']['precision']:.3f} LLM={llm}")


if __name__ == "__main__":
    main()
