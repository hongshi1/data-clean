"""Print latest cascade run summary."""
from __future__ import annotations

import glob
import json
import os
import sys

PATTERN = "data/gjb_438c/runs/eval_cascade_*"


def main() -> None:
    runs = sorted(glob.glob(PATTERN))
    rdir = sys.argv[1] if len(sys.argv) > 1 else runs[-1]
    res = json.load(open(os.path.join(rdir, "result.json"), encoding="utf-8"))
    print("run:", rdir)
    for name, cfg in res["configs"].items():
        m = cfg.get("metrics", cfg)
        print(f"{name}: acc={m['accuracy']:.4f} "
              f"macroF1={m['macro_f1']:.4f}")
        pc = m["per_class"]
        print(f"   refute P={pc['refute']['precision']:.3f} "
              f"R={pc['refute']['recall']:.3f} "
              f"F1={pc['refute']['f1']:.3f}")


if __name__ == "__main__":
    main()
