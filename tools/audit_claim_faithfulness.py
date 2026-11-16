"""Claim faithfulness audit: are claims faithful propositions of the answer?"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import decompose_claims  # noqa: E402
from algorithms.consistency.eval_lib import load_frozen_qa  # noqa: E402

SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    qa = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    dev = [r for r in qa if r["instance_id"] in dev_ids]

    stats = {"total": 0, "verbatim": 0, "kinds": {}}
    covered_chars = 0
    total_chars = 0
    for rec in dev:
        answer = str(rec["answer"])
        total_chars += len(answer)
        claims = decompose_claims(str(rec["question"]), answer)
        spans: list[tuple[int, int]] = []
        for c in claims:
            stats["total"] += 1
            kind = stats["kinds"].setdefault(
                c.kind, {"n": 0, "verbatim": 0})
            kind["n"] += 1
            pos = answer.find(c.text)
            if pos >= 0:
                stats["verbatim"] += 1
                kind["verbatim"] += 1
                spans.append((pos, pos + len(c.text)))
        spans.sort()
        last = 0
        for start, end in spans:
            covered_chars += max(0, min(end, len(answer)) - max(start, last))
            last = max(last, end)
    print("=== claim忠实度(dev-45) ===")
    print(f"总claims: {stats['total']}")
    pct = stats["verbatim"] / max(1, stats["total"]) * 100
    print(f"逐字忠实(claim.text是answer原文子串): "
          f"{stats['verbatim']}/{stats['total']} ({pct:.0f}%)")
    for kind, info in stats["kinds"].items():
        ratio = info["verbatim"] / max(1, info["n"]) * 100
        print(f"  {kind:11s}: 逐字 {info['verbatim']}/{info['n']} "
              f"({ratio:.0f}%)")
    print(f"answer字符覆盖率(并集): "
          f"{covered_chars / max(1, total_chars) * 100:.0f}%")


if __name__ == "__main__":
    main()
