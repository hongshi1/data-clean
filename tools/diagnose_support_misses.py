"""P1 diagnosis: why 4 of the 6 silver=support QA instances are missed
(support recall 2/6 = 0.333, the largest macro-F1 gap on 91QA).

Task 1  per-claim failure analysis of the 4 missed instances
        (S1QA-053/066/069/077) under QAConsistencyModule(
        use_experts=True, use_llm_residual=True) — every claim's
        verdict/method/rationale/evidence_refs plus a blocking-reason
        classification:
          a  聚合语义错配 — the claim content is supported at silver
             (GLM judged support on matching content) but our channel/
             rule judged NIE (or a false refute, flagged refute级)
          b  能力缺口 — the residual L3 was asked and judged NIE
             (the LLM also cannot decide)
          c  分解粒度 — our decomposition produced a fragment GLM does
             not assert as its own claim: a numbered-prefix duplicate of
             an already-verified claim, or a table-header/cell artifact
        plus the GLM-vs-our claim granularity comparison (mean claims
        per instance, corpus-wide and on the 6 support instances).

Task 2  aggregation-variant experiment on the dev split only
        (strict-∀ / dominant_70 / no_minor_block; the qa_module default
        stays strict). Variant selection happens on dev; test-side
        numbers are reserved for the later honest evaluation. The
        variants' direct effect on the 4 missed instances is reported
        separately as a rule-level diagnosis (aggregating the already
        fused claim tuples — no test-set metric claim).

LLM traffic: only the cached L3 residual channel (llm_json cache=True);
raw L3 per-claim verdicts and pre-fusion claim counts are captured by
wrapping llm_residual.verify_residual_claims and
QAConsistencyModule._fuse_per_claim (same cached prompts — no new API
calls; wrappers are restored in finally, nothing is swallowed).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import algorithms.consistency.llm_residual as llm_residual_mod  # noqa: E402
from algorithms.consistency.qa_models import ClaimResult  # noqa: E402
from algorithms.consistency.qa_module import (  # noqa: E402
    AGGREGATION_VARIANTS,
    QAConsistencyModule,
)
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.build_dev_test_split import SPLIT_PATH, load_split  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")

MISSED = ("S1QA-053", "S1QA-066", "S1QA-069", "S1QA-077")
DETECTED = ("S1QA-006", "S1QA-021")
SUPPORT_ALL = ("S1QA-006", "S1QA-021", "S1QA-053", "S1QA-066", "S1QA-069",
               "S1QA-077")
LABELS = ("support", "refute", "not_in_evidence")

_ENUM_PREFIX = re.compile(r"^\s*(?:\d{1,2}|[一二三四五六七八九十])[.．、]\s*")
#: pure numbering/table-cell fragments ("4．1.1 |", "|----|")
_ARTIFACT_RE = re.compile(r"^[|.．\d\s\-]+$")
#: table-header rows pasted into claims ("... | 序号 | Use case名称 |...")
_TABLE_HEADER_RE = re.compile(r"\|\s*序号\s*\|")
_SILVER_SIM_THRESHOLD = 0.5


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _strip_enum(text: str) -> str:
    return _compact(_ENUM_PREFIX.sub("", text))


def _bigrams(text: str) -> frozenset[str]:
    return frozenset(text[i:i + 2] for i in range(len(text) - 1))


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    grams_a, grams_b = _bigrams(a), _bigrams(b)
    union = len(grams_a | grams_b)
    return len(grams_a & grams_b) / union if union else 0.0


def _is_artifact(claim_text: str) -> bool:
    compact = _compact(claim_text)
    if compact and _ARTIFACT_RE.fullmatch(compact):
        return True
    return bool(_TABLE_HEADER_RE.search(claim_text))


def _silver_support_match(claim_text: str,
                          silver_claims: list[dict]) -> dict | None:
    """Match a blocking claim against silver support claims.

    Three match modes (needle = our claim with enumeration prefix
    stripped, hay = compact silver claim text):
    - needle containment in a silver claim (bare-ID claims)
    - bigram Jaccard >= 0.5 (rewrites of the same assertion)
    - reverse coverage: >= 0.6 of a silver claim's bigrams appear in our
      claim — our decomposition merged several silver claims into one
      long answer item (S1QA-077 "查询数据：...如逐行拷贝..." merges
      silver claims 3+4), so a single silver claim is covered by ours
    """
    needle = _strip_enum(claim_text)
    needle_grams = _bigrams(needle)
    for claim in silver_claims:
        if claim.get("verdict") != "support":
            continue
        hay = _compact(str(claim.get("claim_text", "")))
        if len(needle) >= 4 and needle in hay:
            return claim
        if _similarity(needle, hay) >= _SILVER_SIM_THRESHOLD:
            return claim
        hay_grams = _bigrams(hay)
        if hay_grams and needle_grams and len(
                hay_grams & needle_grams) / len(hay_grams) >= 0.6:
            return claim
    return None


def classify_blocking(claim: ClaimResult, fused_claims: list[ClaimResult],
                      silver_claims: list[dict],
                      llm_verdicts: dict[str, str]
                      ) -> tuple[str, str, str | None]:
    """Return (class, note, matched_silver_claim_text) for a blocking claim.

    Order: (c) fragment tests first — a fragment blocks regardless of
    silver semantics; then (b) — the residual L3 was asked and said NIE;
    then (a) — silver supports the content but our channel vetoed.
    """
    text = _compact(claim.claim_text)
    stripped = _strip_enum(claim.claim_text)
    support_texts = {_compact(c.claim_text) for c in fused_claims
                     if c.verdict == "support"}
    level = "refute级" if claim.verdict == "refute" else "NIE级"
    if _is_artifact(claim.claim_text):
        return "c", "分解粒度-表格残片claim", None
    if stripped != text and stripped in support_texts:
        return "c", "分解粒度-编号前缀重复claim(同内容已判support)", None
    llm_verdict = llm_verdicts.get(text) or llm_verdicts.get(stripped)
    if llm_verdict == "not_in_evidence":
        return "b", "能力缺口-残差L3判NIE", None
    matched = _silver_support_match(claim.claim_text, silver_claims)
    if matched is not None:
        return "a", f"聚合语义错配-{level}", matched.get("claim_text", "")
    if llm_verdict is not None:
        return "b", f"能力缺口-L3判{llm_verdict}且无silver对应", None
    return "b", "未归类-无L3判定且无silver对应(需人工复核)", None


def _claim_result_of(entry: dict) -> ClaimResult:
    return ClaimResult(
        claim_id=str(entry["claim_id"]),
        claim_text=str(entry["claim_text"]),
        verdict=str(entry["verdict"]),
        check_item_candidates=(),
        evidence_refs=tuple(entry.get("evidence_refs", ())),
        rationale=str(entry.get("rationale", "")),
        method=str(entry.get("method", "")),
        confidence=float(entry.get("confidence", 0.0)),
    )


def prf(confusion: Counter, label: str) -> tuple[float, float, float]:
    """confusion keys are (predicted, gold) — same convention as
    tools/eval_paper_matrix.py."""
    tp = confusion[(label, label)]
    fp = sum(confusion[(label, gold)] for gold in LABELS if gold != label)
    fn = sum(confusion[(pred, label)] for pred in LABELS if pred != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return precision, recall, f1


def metrics(confusion: Counter, n: int) -> dict:
    per_class = {}
    for label in LABELS:
        precision, recall, f1 = prf(confusion, label)
        per_class[label] = {"precision": round(precision, 4),
                            "recall": round(recall, 4),
                            "f1": round(f1, 4)}
    accuracy = (sum(confusion[(p, g)] for p in LABELS for g in LABELS
                    if p == g) / n) if n else 0.0
    return {
        "n": n,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(sum(per_class[label]["f1"]
                              for label in LABELS) / len(LABELS), 4),
        "per_class": per_class,
        "confusion[predicted, silver]": {
            f"{p}|{g}": confusion[(p, g)]
            for p in LABELS for g in LABELS if confusion[(p, g)]},
    }


def _run_strict(rows: dict, silver: dict) -> tuple[dict, dict]:
    """One cached B4 pass over the corpus; instrument the L3 channel.

    The wrapper records the raw L3 per-claim verdicts (the fused result can
    keep the underlying conservative_unresolved ClaimResult when the L3
    also judged NIE, so the raw verdicts are captured here). Same cached
    prompts — no new API calls; restored in finally.
    """
    llm_capture: dict[str, dict[str, str]] = {}
    original_verify_residual = llm_residual_mod.verify_residual_claims

    def _capturing_residual(request, residual, statements, **kwargs):
        results = original_verify_residual(request, residual, statements,
                                           **kwargs)
        per_instance = llm_capture.setdefault(request.instance_id, {})
        for result in results:
            per_instance.setdefault(_compact(result.claim_text),
                                    result.verdict)
        return results

    llm_residual_mod.verify_residual_claims = _capturing_residual
    try:
        module = QAConsistencyModule(use_experts=True, use_llm_residual=True)
        outcomes: dict[str, dict] = {}
        for iid in sorted(rows):
            result = module.verify(request_from_dict(rows[iid]))
            outcomes[iid] = {
                "verdict": result.verdict,
                "claims": [{
                    "claim_id": c.claim_id,
                    "claim_text": c.claim_text,
                    "verdict": c.verdict,
                    "method": c.method,
                    "confidence": c.confidence,
                    "evidence_refs": list(c.evidence_refs),
                    "rationale": c.rationale,
                } for c in result.claim_results],
                "diagnostics": list(result.diagnostics),
            }
        return outcomes, llm_capture
    finally:
        llm_residual_mod.verify_residual_claims = original_verify_residual


def _cfix_probe(strict_outcomes: dict) -> dict:
    """Simulate the (c)-class deterministic fix: per-claim channel fusion
    keyed on the enumeration-prefix-stripped claim text ("1．X" fragments
    currently fail to fuse with their "X" twins because the fusion key is
    the exact text). Re-group the fused claims by the stripped key, apply
    the same refute>support>NIE per-claim rule, then strict aggregation.
    Mechanism diagnosis only (includes test-side instances — a failure
    analysis, not an evaluation/selection run)."""
    module = QAConsistencyModule(aggregation="strict")
    changes: dict[str, dict] = {}
    for iid, outcome in strict_outcomes.items():
        groups: dict[str, list[dict]] = {}
        for entry in outcome["claims"]:
            groups.setdefault(_strip_enum(entry["claim_text"]),
                              []).append(entry)
        regrouped: list[dict] = []
        for group in groups.values():
            labels = {e["verdict"] for e in group}
            if "refute" in labels:
                pick = next(e for e in group if e["verdict"] == "refute")
            elif "support" in labels:
                pick = next(e for e in group if e["verdict"] == "support")
            else:
                pick = group[0]
            regrouped.append(pick)
        verdict, _diag = module._aggregate(
            tuple(_claim_result_of(e) for e in regrouped))
        if verdict != outcome["verdict"]:
            changes[iid] = {"strict": outcome["verdict"], "cfix": verdict}
    return changes


def main() -> None:
    rows = {row["instance_id"]: row for row in read_jsonl(QA_FROZEN)}
    silver = {row["instance_id"]: row for row in read_jsonl(SILVER)}

    strict_outcomes, llm_capture = _run_strict(rows, silver)

    # ── Task 1: per-claim diagnosis on the 4 missed (+2 detected) ─────────
    diagnosis: dict[str, dict] = {}
    for iid in MISSED + DETECTED:
        outcome = strict_outcomes[iid]
        silver_claims = silver[iid].get("claims", [])
        llm_verdicts = llm_capture.get(iid, {})
        fused = [_claim_result_of(c) for c in outcome["claims"]]
        claim_rows = []
        blocking_counter: Counter = Counter()
        for claim, claim_obj in zip(outcome["claims"], fused):
            entry = dict(claim)
            entry["llm_residual_verdict"] = llm_verdicts.get(
                _compact(claim["claim_text"]))
            if claim["verdict"] == "support":
                entry["blocking"] = False
                entry["class"] = ""
                entry["class_note"] = ""
                entry["matched_silver_claim"] = ""
            else:
                cls, note, matched = classify_blocking(
                    claim_obj, fused, silver_claims, llm_verdicts)
                entry["blocking"] = True
                entry["class"] = cls
                entry["class_note"] = note
                entry["matched_silver_claim"] = (matched or "")[:80]
                blocking_counter[cls] += 1
            claim_rows.append(entry)
        diagnosis[iid] = {
            "question": rows[iid]["question"],
            "silver": silver[iid]["final_verdict"],
            "predicted_strict": outcome["verdict"],
            "silver_claim_count": len(silver_claims),
            "our_fused_claim_count": len(outcome["claims"]),
            "claims": claim_rows,
            "blocking_distribution": dict(blocking_counter),
        }

    blocking_distribution: Counter = Counter()
    for iid in MISSED:
        blocking_distribution.update(diagnosis[iid]["blocking_distribution"])

    # ── granularity comparison ────────────────────────────────────────────
    granularity = {
        "corpus": {
            "n": len(rows),
            "glm_mean_claims": round(sum(
                len(silver[iid].get("claims", []))
                for iid in rows) / len(rows), 2),
            "our_mean_fused_claims": round(sum(
                len(strict_outcomes[iid]["claims"])
                for iid in rows) / len(rows), 2),
        },
        "support6": {
            "glm_mean_claims": round(sum(
                len(silver[iid].get("claims", []))
                for iid in SUPPORT_ALL) / len(SUPPORT_ALL), 2),
            "our_mean_fused_claims": round(sum(
                len(strict_outcomes[iid]["claims"])
                for iid in SUPPORT_ALL) / len(SUPPORT_ALL), 2),
        },
        "per_instance": {
            iid: {
                "glm_claims": len(silver[iid].get("claims", [])),
                "our_fused_claims": len(strict_outcomes[iid]["claims"]),
            } for iid in SUPPORT_ALL},
    }

    # ── dev split: reuse the frozen split of tools/build_dev_test_split.py
    # (the shared P0 asset — seed 42, stratified S=3/3 R=4/4, 45/46, whole
    # topic clusters never span sides). Build it only if the file is absent.
    if SPLIT_PATH.exists():
        split = load_split(SPLIT_PATH)
        split_source = str(SPLIT_PATH.relative_to(BASE))
    else:
        from tools.build_dev_test_split import build_split
        split = build_split(
            list(rows.values()),
            {iid: silver[iid]["final_verdict"] for iid in rows})
        SPLIT_PATH.write_text(json.dumps(split, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        split_source = "built-by-this-run"
    dev_ids = list(split["dev"])

    # ── Task 2: aggregation variants on dev (real verify path) ────────────
    dev_variants: dict[str, dict] = {}
    for variant in AGGREGATION_VARIANTS:
        module = QAConsistencyModule(use_experts=True, use_llm_residual=True,
                                     aggregation=variant)
        confusion: Counter = Counter()
        flips = []
        for iid in dev_ids:
            result = module.verify(request_from_dict(rows[iid]))
            gold = silver[iid]["final_verdict"]
            confusion[(result.verdict, gold)] += 1
            if result.verdict != strict_outcomes[iid]["verdict"]:
                flips.append({
                    "instance_id": iid,
                    "strict": strict_outcomes[iid]["verdict"],
                    "variant": result.verdict,
                    "silver": gold,
                })
        entry = metrics(confusion, len(dev_ids))
        entry["false_support"] = sum(
            confusion[("support", gold)] for gold in LABELS
            if gold != "support")
        entry["flips_vs_strict"] = flips
        dev_variants[variant] = entry

    # ── rule-level effect of the variants on the 4 missed instances ───────
    # (aggregating the already-fused claim tuples from the strict run —
    # mechanism diagnosis, NOT a test-set metric)
    variant_effect_on_missed: dict[str, dict] = {}
    for iid in MISSED:
        fused = tuple(_claim_result_of(c)
                      for c in strict_outcomes[iid]["claims"])
        effects = {}
        for variant in AGGREGATION_VARIANTS:
            module = QAConsistencyModule(aggregation=variant)
            verdict, _diag = module._aggregate(fused)
            effects[variant] = verdict
        variant_effect_on_missed[iid] = effects

    # ── (c)-class deterministic-fix oracle probe (fusion-key prefix strip) ─
    cfix_changes = _cfix_probe(strict_outcomes)

    result_payload = {
        "focus_missed": list(MISSED),
        "detected_reference": list(DETECTED),
        "module_config": {"use_experts": True, "use_llm_residual": True},
        "diagnosis": diagnosis,
        "blocking_distribution_missed4": dict(blocking_distribution),
        "granularity": granularity,
        "split": {
            "source": split_source,
            "seed": split["seed"],
            "method": split.get("rationale", ""),
            "dev_n": len(dev_ids),
            "dev_label_counts": split["silver_distribution"]["dev"],
            "test_label_counts": split["silver_distribution"]["test"],
        },
        "dev_variants": dev_variants,
        "variant_effect_on_missed_diagnosis": variant_effect_on_missed,
        "cfix_fusion_prefix_strip_probe": cfix_changes,
        "notes": [
            "variant selection on dev only; test numbers reserved for the "
            "later honest evaluation",
            "variant_effect_on_missed_diagnosis aggregates the strict run's "
            "fused claims under each rule — a mechanism diagnosis, not a "
            "test-set metric",
            "cfix_fusion_prefix_strip_probe likewise spans the full corpus "
            "(failure analysis of the known misses, not an evaluation)",
            "llm calls all served from the llm_json disk cache",
        ],
    }

    run = open_run("diagnose_support_misses", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(SILVER.relative_to(BASE)),
        "focus": list(MISSED),
        "variants": list(AGGREGATION_VARIANTS),
        "split": split_source,
    })
    run.save_result(result_payload)

    # ── console summary ───────────────────────────────────────────────────
    print("=" * 96)
    print("P1 support-recall diagnosis — silver=support 6 instances, "
          "strict-∀ detects 2/6")
    print("=" * 96)
    for iid in MISSED:
        d = diagnosis[iid]
        print(f"\n## {iid} silver={d['silver']} "
              f"predicted={d['predicted_strict']} "
              f"claims(ours/GLM)={d['our_fused_claim_count']}/"
              f"{d['silver_claim_count']}")
        for entry in d["claims"]:
            mark = "BLOCK" if entry["blocking"] else "  ok "
            cls = f"[{entry['class']}]" if entry["blocking"] else "      "
            print(f"  {mark} {entry['verdict']:16s} {cls} "
                  f"{entry['method']:30s} {entry['claim_text'][:44]}")
            if entry["blocking"]:
                print(f"         -> {entry['class_note']} "
                      f"| L3={entry['llm_residual_verdict']} "
                      f"| silverMatch={entry['matched_silver_claim'][:40]}")
    print("\n-- blocking-reason distribution (4 missed, blocking claims) --")
    for cls in ("a", "b", "c"):
        print(f"   {cls}: {blocking_distribution.get(cls, 0)}")
    print("\n-- granularity (mean claims per instance) --")
    print(f"   corpus  GLM={granularity['corpus']['glm_mean_claims']} "
          f"ours(fused)={granularity['corpus']['our_mean_fused_claims']}")
    print(f"   support GLM={granularity['support6']['glm_mean_claims']} "
          f"ours(fused)={granularity['support6']['our_mean_fused_claims']}")
    print(f"\n-- dev split: n={len(dev_ids)} "
          f"labels={split['silver_distribution']['dev']} "
          f"(frozen split of tools/build_dev_test_split.py, "
          f"seed={split['seed']})")
    print("\n-- aggregation variants on dev --")
    print(f"{'variant':16s} {'acc':>7s} {'macroF1':>8s} {'S-F1':>7s} "
          f"{'S-R':>6s} {'R-F1':>7s} {'N-F1':>7s} {'falseS':>7s}")
    for variant, entry in dev_variants.items():
        per = entry["per_class"]
        print(f"{variant:16s} {entry['accuracy']:>7.4f} "
              f"{entry['macro_f1']:>8.4f} "
              f"{per['support']['f1']:>7.4f} "
              f"{per['support']['recall']:>6.2f} "
              f"{per['refute']['f1']:>7.4f} "
              f"{per['not_in_evidence']['f1']:>7.4f} "
              f"{entry['false_support']:>7d}")
    print("\n   dev flips vs strict:")
    for variant, entry in dev_variants.items():
        for flip in entry["flips_vs_strict"]:
            print(f"     {variant:16s} {flip['instance_id']} "
                  f"{flip['strict']} -> {flip['variant']} "
                  f"(silver={flip['silver']})")
    print("\n-- variant rule effect on the 4 missed (mechanism diagnosis) --")
    for iid, effects in variant_effect_on_missed.items():
        print(f"   {iid}: " + "  ".join(
            f"{v}={effects[v]}" for v in AGGREGATION_VARIANTS))
    print("\n-- (c)-fix oracle probe: fusion key strips enumeration prefixes "
          "(full-corpus diagnosis) --")
    for iid, change in cfix_changes.items():
        silver_verdict = silver[iid]["final_verdict"]
        print(f"   {iid}: {change['strict']} -> {change['cfix']} "
              f"(silver={silver_verdict})")
    if not cfix_changes:
        print("   (no verdict changes)")
    print(f"\nrun: {run.path}")


if __name__ == "__main__":
    main()
