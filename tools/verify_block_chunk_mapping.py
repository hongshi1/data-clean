"""Verify frozen-evidence block → chunk_id mapping coverage (04号)."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
QA = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DOC = "04数据统一访问服务软件需求规格说明-终稿"


def main() -> None:
    recs = [json.loads(line) for line in
            QA.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    c04 = [c for c in chunks if c["doc"] == DOC]
    by_prefix: dict[str, list[str]] = {}
    for chunk in c04:
        cid = chunk["chunk_id"]
        # '..._T0030' or '..._T0030_1' → prefix '..._T0030'
        marker = "_T"
        pos = cid.rfind(marker)
        if pos < 0:
            continue
        tail = cid[pos + 2:]
        head = tail.split("_")[0]
        prefix = cid[:pos] + "_T" + head
        by_prefix.setdefault(prefix, []).append(cid)

    gold_blocks: set[str] = set()
    for rec in recs:
        for ev in rec["evidence"]:
            block = str(ev["source_ref"].get("block_id", ""))
            if block.startswith("block-"):
                gold_blocks.add(block)
    print(f"gold distinct blocks: {len(gold_blocks)}")

    mapped = 0
    unmatched: list[str] = []
    for block in sorted(gold_blocks):
        num = block.replace("block-", "")
        prefix = f"{DOC}_T{int(num):04d}"
        if prefix in by_prefix:
            mapped += 1
        else:
            unmatched.append(block)
    print(f"mapped to chunks: {mapped}/{len(gold_blocks)}")
    if unmatched:
        print("unmatched:", unmatched[:10])
    suffix_counts = sum(1 for cid in by_prefix if len(by_prefix[cid]) > 1)
    print(f"prefixes with multiple sub-chunks: {suffix_counts}")


if __name__ == "__main__":
    main()
