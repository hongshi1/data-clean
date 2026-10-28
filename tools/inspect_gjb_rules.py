"""Inspect the GJB rules knowledge base structure."""
from __future__ import annotations

import json
from collections import Counter

PATH = "knowledge/gjb_438c_rules_full.json"


def main() -> None:
    rules = json.load(open(PATH, encoding="utf-8"))
    items = rules["rules"]
    print("total:", rules["total_rules"])
    print("by type:", Counter(r["type"] for r in items))
    srs_rules = [r for r in items if "SRS" in r.get("applies_to", [])]
    print("applies_to SRS:", len(srs_rules))
    print("SRS规则样例:")
    for r in srs_rules[5:11]:
        print(f"  {r['rule_id']} [{r['type']}] src={r['source']}"
              f" {r['description'][:66]}")
    print()
    print("结构类(format/structure)规则样例:")
    struct = [r for r in items if r["type"] in ("format", "structure")]
    print("  count:", len(struct))
    for r in struct[:8]:
        print(f"  {r['rule_id']} [{r['type']}] {r['description'][:66]}")


if __name__ == "__main__":
    main()
