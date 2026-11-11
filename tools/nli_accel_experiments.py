"""L2 NLI acceleration experiments.

Options measured on the 91QA residual workload (~355 claim pairs):
  A. fp16 inference   — load distilled_v1 in half precision (2x expected)
  B. cross-instance batching — collect ALL residual pairs of the corpus,
     one big batched pass (offline corpus mode; 10x throughput expected)
  C. per-claim sequence-length profile (why 25ms/claim vs 2.58ms/pair
     raw benchmark: premise length × attention O(L^2))

Each option reports speed AND verdict drift vs the fp32 baseline
(test46 must stay 0.9130/0.8047 for fp16 to be safe as default).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import torch  # noqa: E402
from transformers import (AutoModelForSequenceClassification,  # noqa: E402
                          AutoTokenizer)

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    load_frozen_qa,
)
from algorithms.consistency.evidence_statements import linearize_context  # noqa: E402
from algorithms.consistency.nli_residual import _load_model, _infer  # noqa: E402
from algorithms.consistency.nli_training import residual_premise  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

MODEL = "models/nli/distilled_v1"
SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"


def collect_pairs() -> list[tuple[str, str, list]]:
    """The 91QA residual workload: (premise, claim, statements) per claim."""
    mod = QAConsistencyModule(use_experts=True)
    out: list[tuple[str, str, list]] = []
    for rec in load_frozen_qa():
        req = build_qa_input(rec)
        res = mod.verify(req)
        residual = [r for r in res.claim_results
                    if r.method in ("semantic_unresolved",
                                    "conservative_unresolved")]
        if not residual:
            continue
        statements = linearize_context(req.evidence)
        for claim in residual:
            out.append((req.question, claim.claim_text, statements))
    return out


def bench_infer(entry: dict, pairs: list[tuple[str, str]], tag: str
                ) -> tuple[float, list[int]]:
    tokenizer = entry["tokenizer"]
    lengths: list[int] = []
    premises = [p for p, _ in pairs]
    claims = [c for _, c in pairs]
    enc = tokenizer(premises, claims, padding=True,
                    truncation="longest_first", max_length=512,
                    return_tensors="pt")
    lengths = enc["input_ids"].shape[1] and [enc["input_ids"].shape[1]]
    start = time.perf_counter()
    _infer(entry, pairs)
    elapsed = time.perf_counter() - start
    print(f"[{tag}] n_pairs={len(pairs)} padded_len={lengths} "
          f"total={elapsed*1000:.0f}ms "
          f"({elapsed/len(pairs)*1000:.1f}ms/pair)")
    return elapsed, lengths


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    # ── collect the residual workload once ──
    workload = collect_pairs()
    pairs = []
    for question, claim, statements in workload:
        premise, _picks = residual_premise(claim, question, statements)
        if premise.strip():
            pairs.append((premise, claim))
    print(f"residual workload: {len(pairs)} claim pairs (91QA)")

    # ── C. sequence length profile ──
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    lens = []
    for start in range(0, len(pairs), 16):
        chunk = pairs[start:start + 16]
        enc = tokenizer([p for p, _ in chunk], [c for _, c in chunk],
                        padding=True, truncation="longest_first",
                        max_length=512, return_tensors="pt")
        lens.append(enc["input_ids"].shape[1])
    print(f"[C] padded seq lens per batch16: min={min(lens)} "
          f"max={max(lens)} mean={sum(lens)/len(lens):.0f}")

    # ── A. fp32 baseline vs fp16 (same workload, big batch) ──
    entry32 = _load_model(MODEL)
    t32, _ = bench_infer(entry32, pairs, "A-fp32-bigbatch")
    torch.cuda.empty_cache()

    # fp16 model
    fp16_model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, local_files_only=True, torch_dtype=torch.float16)
    fp16_model.to("cuda")
    fp16_model.eval()
    entry16 = dict(entry32)
    entry16["model"] = fp16_model
    t16, _ = bench_infer(entry16, pairs, "A-fp16-bigbatch")
    print(f"[A] fp16 speedup: {t32/t16:.2f}x")

    # fp16 verdict drift on test46 (full pipeline with fp16 model swapped)
    probs32 = _infer(entry32, pairs)
    probs16 = _infer(entry16, pairs)
    drift = sum(1 for a, b in zip(probs32, probs16)
                if max(a, key=a.get) != max(b, key=b.get))
    print(f"[A] verdict label drift (pair level): {drift}/{len(pairs)}")

    # ── B. per-instance (current pipeline pattern) vs big batch ──
    per_instance_groups: list[list[tuple[str, str]]] = []
    # rebuild per-instance groups roughly by pairs count per instance
    # (approximation: batch per 4.4 as measured)
    group = []
    for question, claim, statements in workload:
        premise, _picks = residual_premise(claim, question, statements)
        if not premise.strip():
            continue
        group.append((premise, claim))
        if len(group) >= 4:
            per_instance_groups.append(group)
            group = []
    if group:
        per_instance_groups.append(group)
    start = time.perf_counter()
    for group in per_instance_groups:
        _infer(entry32, group)
    t_b = time.perf_counter() - start
    print(f"[B] per-instance small-batch pattern: {t_b*1000:.0f}ms total "
          f"({t_b/len(pairs)*1000:.1f}ms/pair) vs big-batch "
          f"{t32/len(pairs)*1000:.1f}ms/pair → "
          f"{t_b/t32:.1f}x batching gain")


if __name__ == "__main__":
    main()
