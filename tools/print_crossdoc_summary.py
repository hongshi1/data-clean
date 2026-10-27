"""Print crossdoc eval summary from the latest run."""
from __future__ import annotations

import glob
import json
import os
import sys

PATTERN = "data/gjb_438c/runs/eval_crossdoc_*"


def main() -> None:
    runs = sorted(glob.glob(PATTERN))
    rdir = sys.argv[1] if len(sys.argv) > 1 else runs[-1]
    res = json.load(open(os.path.join(rdir, "result.json"), encoding="utf-8"))
    print("run:", rdir)
    for name, cfg in res["configs"].items():
        m = cfg["metrics"]
        print(f"== {name}: macroF1={m['macro_f1']:.4f} "
              f"acc={m['accuracy']:.4f}")
        for cls in ("support", "refute", "not_in_evidence"):
            c = m["per_class"][cls]
            print(f"   {cls}: P={c['precision']:.3f} "
                  f"R={c['recall']:.3f} F1={c['f1']:.3f}")


if __name__ == "__main__":
    main()
