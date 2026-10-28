"""Inspect taxonomy v3 GJB items vs the 120-rule knowledge base usage."""
from __future__ import annotations

import json
from collections import Counter

TAX = "knowledge/consistency_taxonomy_v3.json"
RULES = "knowledge/gjb_438c_rules_full.json"


def main() -> None:
    tax = json.load(open(TAX, encoding="utf-8"))
    items = tax.get("items", tax)
    if isinstance(items, dict):
        entries = [items[k] for k in items if k.startswith("GJB")]
    else:
        entries = [i for i in items if str(i.get("id", "")).startswith("GJB")]
    print(f"GJB items in taxonomy v3: {len(entries)}")
    for e in entries[:12]:
        print(f"\n== {e.get('id')}: {e.get('name', e.get('title', ''))}")
        desc = e.get("description", "")
        print("  desc:", desc[:110])
        ex = e.get("original_example", "")
        print("  example:", str(ex)[:110])
        ev = e.get("doc04_evidence", "")
        print("  doc04:", str(ev)[:70])

    rules = json.load(open(RULES, encoding="utf-8"))["rules"]
    print("\n\n120条规则库的类型/来源分布:")
    print(Counter(r["type"] for r in rules))
    print("来源是附录J(SRS模板)的规则数:",
          sum(1 for r in rules if "附录J" in r.get("source", "")))


if __name__ == "__main__":
    main()
