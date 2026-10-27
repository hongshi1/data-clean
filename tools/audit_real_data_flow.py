"""Trace real data flow through the current pipeline to expose friction points."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402

rows = [json.loads(line) for line in
        (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
        .read_text(encoding="utf-8").splitlines() if line.strip()]
labels = {json.loads(line)["instance_id"]: json.loads(line) for line in
          (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
           / "final_labels.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}

# 1. Evidence modality distribution
evidence_types = Counter(ev["source_type"] for row in rows for ev in row["evidence"])
table_blocks = sum(1 for row in rows for ev in row["evidence"]
                   if ev["source_type"] == "table")
html_tables = sum(1 for row in rows for ev in row["evidence"]
                  if "<table" in ev["text"])
usecase_tables = sum(1 for row in rows for ev in row["evidence"]
                     if "Use Case" in ev["text"] or "Use case" in ev["text"]
                     or "主事件流" in ev["text"])

# 2. What does decomposition actually produce on real answers?
module = QAConsistencyModule()
decomposition_stats = Counter()
semantic_answer_lens = []
structure_markers = Counter()
for row in rows:
    request = request_from_dict(row)
    claims = module._decompose(request.question, request.answer)
    kinds = {claim.kind for claim in claims}
    if kinds == {"semantic"}:
        decomposition_stats["whole_answer_single_claim"] += 1
        semantic_answer_lens.append(len(request.answer))
        answer = request.answer
        if re.search(r"\n\s*\d+[.)、]\s", answer):
            structure_markers["numbered_steps"] += 1
        if "**" in answer:
            structure_markers["markdown_bold_headers"] += 1
        if re.search(r"[。；]\s*\n", answer):
            structure_markers["multiline_sentences"] += 1
    else:
        decomposition_stats["partially_decomposed"] += 1

# 3. Silver refutes: what evidence shape do they cite?
refute_rows = [labels[r["instance_id"]] for r in rows
               if labels[r["instance_id"]]["final_verdict"] == "refute"]
refute_evidence_tables = sum(
    1 for label in refute_rows
    for claim in label["claims"]
    if claim["verdict"] == "refute"
    for ref in claim.get("evidence_refs", [])
    if any(ev["evidence_id"] == ref and ev["source_type"] == "table"
           for row in rows if row["instance_id"] == label["instance_id"]
           for ev in row["evidence"]))
refute_claim_reasons = [claim["rationale"][:60] for label in refute_rows
                         for claim in label["claims"]
                         if claim["verdict"] == "refute"]

# 4. Claim length vs NLI 256-token budget (rough: 1 Chinese char ≈ 1 token)
semantic_len_sorted = sorted(semantic_answer_lens, reverse=True)
long_evidence = sum(1 for row in rows for ev in row["evidence"] if len(ev["text"]) > 500)

print(json.dumps({
    "evidence_types": dict(evidence_types),
    "html_table_blocks": html_tables,
    "usecase_schema_tables": usecase_tables,
    "decomposition": dict(decomposition_stats),
    "semantic_single_claim_answer_len": {
        "n": len(semantic_answer_lens),
        "median": sorted(semantic_answer_lens)[len(semantic_answer_lens) // 2] if semantic_answer_lens else 0,
        "p90": semantic_len_sorted[len(semantic_len_sorted) // 10] if semantic_len_sorted else 0,
        "max": max(semantic_answer_lens) if semantic_answer_lens else 0,
    },
    "structure_markers_in_undecomposed": dict(structure_markers),
    "silver_refutes": len(refute_rows),
    "refute_claims_citing_tables": refute_evidence_tables,
    "evidence_blocks_over_500_chars": long_evidence,
    "refute_reason_samples": refute_claim_reasons[:6],
}, ensure_ascii=False, indent=2))
