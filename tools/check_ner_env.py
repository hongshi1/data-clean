"""Check available NER toolchains and 06号 table headers."""
from __future__ import annotations

import glob
import importlib.util
import json
import re

MODS = ["jieba", "hanlp", "lac", "spacy", "pkuseg", "thulac", "fnlp",
        "transformers"]


def main() -> None:
    for m in MODS:
        spec = importlib.util.find_spec(m)
        status = "INSTALLED" if spec else "-"
        print(f"{m}: {status}")
    paths = glob.glob(
        "data/gjb_438c/mineru_standard/06*/office/*content_list*.json")
    blocks = json.load(open(paths[0], encoding="utf-8"))
    tables = [b for b in blocks if b.get("type") == "table"]
    print("\n06号表格数:", len(tables))
    shown = 0
    for t in tables:
        html = str(t.get("table_body", ""))
        heads = re.findall(r"<td[^>]*>([^<]{2,20})</td>", html)[:10]
        heads = [h.strip() for h in heads if h.strip()]
        if len(heads) >= 4 and shown < 5:
            print("  headers:", heads)
            shown += 1


if __name__ == "__main__":
    main()
