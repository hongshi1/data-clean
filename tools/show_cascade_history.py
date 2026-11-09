"""Summarize historical cascade eval results."""
from __future__ import annotations

import json
from pathlib import Path

RUN = Path("data/gjb_438c/runs/eval_cascade_1e92cdce_20261030_122756"
           "/result.json")


def main() -> None:
    r = json.loads(RUN.read_text(encoding="utf-8"))
    for name, cfg in r["configs"].items():
        if "macro_f1" in cfg:
            rc = cfg["per_class"].get(
                "refute", {"f1": 0.0, "precision": 0.0, "recall": 0.0})
            print(f"{name:25s} acc={cfg['accuracy']:.4f} "
                  f"mF1={cfg['macro_f1']:.4f} "
                  f"refuteF1={rc['f1']:.3f} "
                  f"(P={rc['precision']:.2f} R={rc['recall']:.2f})")


if __name__ == "__main__":
    main()
