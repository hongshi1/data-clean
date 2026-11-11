"""E2E: recall front-end + verification core (E3, redesigned).

The first design (recall vs frozen-blocks as gold) was invalidated:
silver labels are EVIDENCE-RELATIVE (defined w.r.t. the frozen context),
and the recall front-end legitimately returns more specific evidence
(use case tables with E1 rows) than the frozen parent tables — an
NIE(frozen) instance can become refute(recalled) legitimately, not an
error. Three defensible sub-experiments instead:

  E3a violation detection: violations-17 (answers contain REAL
      contradictions; gold_evidence_refs marks the blocks where the
      violation evidence lives). recall → verify → refute rate, vs the
      frozen-evidence baseline 16/17. gold-block recall@k is a REAL
      recall metric here (the contradiction lives in those blocks).
  E3b S/R agreement: the 13 91QA instances whose silver label is
      support/refute (the evidence deciding them exists in the doc) —
      E2E should reproduce those verdicts.
  E3c NIE-flip audit: how many NIE instances flip under recalled
      evidence + 5 samples manually inspected for legitimacy.

Usage:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/e2e_recall_verify.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

DOC = "04数据统一访问服务软件需求规格说明-终稿"
SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
VIO = (BASE / "data/gjb_438c/localization_gold"
       / "violation_evalset_v1.jsonl")
_TITLE_PREFIX = re.compile(r"^\[表格标题[^\]]*\]")


def build_request(rec: dict, iid: str, question: str, answer: str,
                  hits: list[dict], full: dict[str, str]) -> QAInput:
    evidences: list[RetrievedEvidence] = []
    for rank, hit in enumerate(hits, 1):
        text = full.get(str(hit.get("chunk_id", "")), "")
        text = _TITLE_PREFIX.sub("", text).strip()
        if not text:
            continue
        evidences.append(RetrievedEvidence(
            evidence_id=f"{iid}-rec-{rank:02d}",
            text=text,
            source_type=str(hit.get("type", "text")),
            source_ref=SourceRef(
                doc_id=str(hit.get("doc", "")),
                section=str(hit.get("section", "")),
                page=hit.get("page"),
                block_id=str(hit.get("chunk_id", ""))),
            scope_id="",
            completeness="open"))
    return QAInput(
        instance_id=iid, question=question, answer=answer,
        evidence=tuple(evidences),
        context_freeze_id=f"recall-e2e-{iid}")


def gold_blocks_of(rec: dict, field: str) -> set[str]:
    """gold_evidence_refs是evidence_id — 经实例自身evidence表映射到block."""
    ev_by_id = {str(ev.get("evidence_id")): ev
                for ev in rec.get("evidence") or []}
    blocks: set[str] = set()
    for ref in rec.get(field) or []:
        ev = ev_by_id.get(str(ref))
        if ev is None:
            continue
        raw = str((ev.get("source_ref") or {}).get("block_id", ""))
        if raw.startswith("block-"):
            blocks.add(raw)
    return blocks


def hit_blocks(hit: dict) -> set[str]:
    cid = str(hit.get("chunk_id", ""))
    pos = cid.rfind("_T")
    if pos < 0:
        return set()
    tail = cid[pos + 2:].split("_")[0]
    if not tail.isdigit():
        return set()
    return {f"block-{int(tail):06d}"}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--flip-samples", type=int, default=5)
    args = parser.parse_args()

    from algorithms.blackboard.evidence_store import EvidenceStore
    from algorithms.blackboard.hybrid_recall import HybridRecaller

    t0 = time.perf_counter()
    recaller = HybridRecaller()
    recaller.recall("数据库访问", doc=DOC, top_k=5)
    full = {cid: str(chunk.get("text", ""))
            for cid, chunk in EvidenceStore()._chunk_by_id().items()}
    print(f"recaller ready ({time.perf_counter() - t0:.0f}s)", flush=True)

    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path="models/nli/distilled_v1", nli_gate=0.8)

    def recall_and_verify(iid: str, question: str, answer: str,
                          k: int) -> tuple[list[dict], object]:
        query = f"{question} {answer[:400]}"
        result = recaller.recall(query, doc=DOC, top_k=max(10, k))
        hits = [h for h in result.get("hits", [])
                if h.get("type") in ("text", "table")][:k]
        request = build_request(rec={}, iid=iid, question=question,
                                answer=answer, hits=hits, full=full)
        return hits, module.verify(request)

    # ── E3a: violations-17 (real contradictions, real gold blocks) ──
    vio_recs = [json.loads(line) for line in
                VIO.read_text(encoding="utf-8").splitlines() if line.strip()]
    recalls: list[float] = []
    detected = 0
    for rec in vio_recs:
        iid = str(rec["instance_id"])
        gold = gold_blocks_of(rec, "gold_evidence_refs")
        hits, res = recall_and_verify(
            iid, str(rec["question"]), str(rec["answer"]), args.k)
        if gold:
            hit_set: set[str] = set()
            for hit in hits:
                hit_set |= hit_blocks(hit)
            recalls.append(len(hit_set & gold) / len(gold))
        if res.verdict == "refute":
            detected += 1
    print(f"E3a violations-17: gold-block recall@{args.k}="
          f"{sum(recalls) / max(1, len(recalls)):.3f} | "
          f"refute detection {detected}/17 (frozen baseline 16/17)")

    # ── E3b: 91QA support/refute instances ──
    silver = load_silver_labels(SILVER)
    qa = load_frozen_qa()
    sr_recs = [r for r in qa
               if silver.get(r["instance_id"], "not_in_evidence")
               in ("support", "refute")]
    agree = 0
    for rec in sr_recs:
        iid = str(rec["instance_id"])
        _, res = recall_and_verify(
            iid, str(rec["question"]), str(rec["answer"]), args.k)
        if res.verdict == silver.get(iid):
            agree += 1
    print(f"E3b SR-{len(sr_recs)}: agreement {agree}/{len(sr_recs)} "
          f"({agree / len(sr_recs) * 100:.0f}%)")

    # ── E3c: NIE-flip audit (with channel attribution) ──
    nie_recs = [r for r in qa
                if silver.get(r["instance_id"], "not_in_evidence")
                == "not_in_evidence"]
    flips = 0
    samples: list[str] = []
    attribution: dict[str, int] = {}
    for rec in nie_recs:
        iid = str(rec["instance_id"])
        _, res = recall_and_verify(
            iid, str(rec["question"]), str(rec["answer"]), args.k)
        if res.verdict != "not_in_evidence":
            flips += 1
            # 归因: 哪个通道贡献了决定性(非NIE)claim
            methods = {c.method for c in res.claim_results
                       if c.verdict == res.verdict}
            for method in methods or {"unknown"}:
                attribution[method] = attribution.get(method, 0) + 1
            if len(samples) < args.flip_samples:
                samples.append(f"{iid}→{res.verdict}")
    print(f"E3c NIE-{len(nie_recs)}: flips {flips} "
          f"({flips / len(nie_recs) * 100:.0f}%) — 证据相对标签的已知"
          f"歧义区(冻结证据无该信息, 召回证据更特异)")
    for method, count in sorted(attribution.items(),
                                key=lambda x: -x[1]):
        print(f"   归因 {method}: {count}")
    for s in samples:
        print(f"   flip: {s}")

    from tools.run_utils import open_run  # noqa: PLC0415
    run = open_run("e2e_recall_verify", {
        "design": "E3a/b/c redesigned (labels are evidence-relative)",
        "k": args.k,
        "e3a": {"gold_recall_at_k": round(sum(recalls) / max(1, len(recalls)), 4),
                "refute_detection": detected, "n": len(vio_recs)},
        "e3b": {"agreement": agree, "n": len(sr_recs)},
        "e3c": {"flips": flips, "n": len(nie_recs), "samples": samples,
                "attribution": attribution},
        "baselines": {"violations_frozen": "16/17",
                      "sr_frozen_macro_f1": None},
    })
    print(f"→ {run.path}")


if __name__ == "__main__":
    main()
