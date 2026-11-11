"""Claim decomposition fix evaluation: v1 typed (A) vs v2 fixed (C).

Question under test: the claim extraction audit
(tools/audit_claim_extraction.py) found that v1 ``decompose_claims``
emits colon-fused semantic claims ("X：Y" title+description in one
claim, 37% of 445), framework-sentence noise ("有以下特点", 3%) and
open-list enum claims ("…如…") — S1QA-066/069/077 support failures are
all colon-fusion cases. The ablation
(tools/eval_decomp_ablation.py) additionally attributed A's win over
sentence-split to claim shortness, i.e. shorter atomic claims are what
the NLI residual channel can verify.

Variants (same module config, same frozen evidence, same labels):
  A_typed  current pipeline, ``decompose_claims`` untouched (baseline;
           known numbers to reproduce from
           data/gjb_438c/distillation/decomp_ablation_v1.json)
  C_fix    ``qa_module.decompose_claims`` monkeypatched with
           ``answer_claims_v2.decompose_claims_v2``: v1 typed extraction
           unchanged + colon split + framework filter + subject
           inheritance + open-list enum downgrade

Isolation: L0/L1 experts (id_join / enum_join / e1 / sequence / ...)
consume ``answer_structure.decompose_answer`` directly and are NOT
patched — only the per-claim typed channel is changed. Fix 3 (subject
inheritance) only writes ``AnswerClaim.attr``; under this module config
the semantic judge path is inactive, so C differs from A through fixes
1/2/4 only.

Module config for both variants:
  QAConsistencyModule(use_experts=True, use_nli_residual=True,
                      nli_model_path="models/nli/distilled_v1", nli_gate=0.8)

Datasets:
  test46       91QA held-out (dev_test_split_v1.json "test"), GLM-5.3 silver
  violations17 real injected violations (expected_verdict, all refute)
  crossdoc150  5 documents x 30 constructive-sound instances (sound_label)

Output: data/gjb_438c/distillation/decomp_fix_v1.json + console table.

Usage:
  python tools/eval_decomp_fix.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency import nli_residual  # noqa: E402
from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.answer_claims import (  # noqa: E402
    AnswerClaim,
    decompose_claims as typed_decompose,
)
from algorithms.consistency.answer_claims_v2 import (  # noqa: E402
    decompose_claims_v2,
    fix_trigger_stats,
)
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIOLATIONS = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
CROSSDOC_DOCS = ("05", "06", "07", "08", "10")
CROSSDOC_DIR = BASE / "data/gjb_438c/qa_frozen"
OUT_PATH = BASE / "data/gjb_438c/distillation/decomp_fix_v1.json"

NLI_MODEL_PATH = "models/nli/distilled_v1"
NLI_GATE = 0.8
DATASET_ORDER = ("test46", "violations17", "crossdoc150")
#: known variant-A numbers to reproduce (decomp_ablation_v1.json)
KNOWN_A = {
    "test46": {"accuracy": 0.913, "macro_f1": 0.8047},
    "violations17": {"accuracy": 0.9412, "macro_f1": 0.3232},
    "crossdoc150": {"accuracy": 0.5133, "macro_f1": 0.5109},
}

DecomposeFn = Callable[[str, str], list[AnswerClaim]]


# ── data loading ────────────────────────────────────────────────────────────


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_datasets() -> dict[str, list[dict[str, Any]]]:
    records = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    test_ids = set(split["test"])
    test_recs = [r for r in records if str(r["instance_id"]) in test_ids]
    if len(test_recs) != len(test_ids):
        raise ValueError(f"test切分{len(test_ids)}条, 冻结语料只匹配到{len(test_recs)}条")
    vio_recs = read_jsonl(VIOLATIONS)
    if len(vio_recs) != 17:
        raise ValueError(f"violations评测集应17条, 实际{len(vio_recs)}条")
    cross_recs: list[dict[str, Any]] = []
    for doc in CROSSDOC_DOCS:
        rows = read_jsonl(CROSSDOC_DIR / f"crossdoc{doc}_evalset_v1.jsonl")
        if len(rows) != 30:
            raise ValueError(f"crossdoc{doc}子集应30条, 实际{len(rows)}条")
        cross_recs.extend(rows)
    if len(cross_recs) != 150:
        raise ValueError(f"crossdoc合并集应150条, 实际{len(cross_recs)}条")
    return {"test46": test_recs, "violations17": vio_recs,
            "crossdoc150": cross_recs}


def load_labels(datasets: dict[str, list[dict[str, Any]]]
                ) -> dict[str, dict[str, str]]:
    silver = load_silver_labels(SILVER)
    labels = {
        "test46": silver,
        "violations17": {str(r["instance_id"]): str(r["expected_verdict"])
                         for r in datasets["violations17"]},
        "crossdoc150": {str(r["instance_id"]): str(r["sound_label"])
                        for r in datasets["crossdoc150"]},
    }
    for name, recs in datasets.items():
        missing = [str(r["instance_id"]) for r in recs
                   if str(r["instance_id"]) not in labels[name]]
        if missing:
            raise ValueError(f"{name}缺标签实例: {missing[:5]}")
    return labels


# ── evaluation ──────────────────────────────────────────────────────────────


def eval_dataset(module: QAConsistencyModule, records: list[dict[str, Any]],
                 labels: dict[str, str]) -> tuple[dict[str, Any],
                                                 dict[str, str], bool]:
    """Run module.verify on all records → (metrics, per-instance preds,
    nli_unavailable_flag)."""
    y_true: list[str] = []
    y_pred: list[str] = []
    preds: dict[str, str] = {}
    unavailable = False
    for record in records:
        request = build_qa_input(record)
        result = module.verify(request)
        preds[request.instance_id] = result.verdict
        if any(claim.method == "nli_residual_unavailable"
               for claim in result.claim_results):
            unavailable = True
        y_true.append(labels[request.instance_id])
        y_pred.append(result.verdict)
    return classification_metrics(y_true, y_pred), preds, unavailable


def claim_statistics(decompose: DecomposeFn,
                     records: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic claim stats: count / per-instance / length / kinds."""
    total = 0
    lengths: list[int] = []
    kinds: Counter[str] = Counter()
    for record in records:
        for claim in decompose(str(record["question"]), str(record["answer"])):
            total += 1
            lengths.append(len(claim.text))
            kinds[claim.kind] += 1
    n = len(records)
    return {
        "n_instances": n,
        "n_claims": total,
        "claims_per_instance": round(total / n, 2) if n else 0.0,
        "claim_len_avg": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "claim_len_max": max(lengths) if lengths else 0,
        "kind_distribution": dict(sorted(kinds.items())),
    }


def fix_triggers(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-dataset trigger counts of the four v2 fixes."""
    totals: Counter[str] = Counter()
    triggered_answers = 0
    for record in records:
        stats = fix_trigger_stats(str(record["question"]), str(record["answer"]))
        if any(stats.values()):
            triggered_answers += 1
        totals.update(stats)
    return {
        "answers_touched": triggered_answers,
        "colon_splits": totals["colon_splits"],
        "framework_drops": totals["framework_drops"],
        "enum_open_list_downgrades": totals["enum_open_list_downgrades"],
    }


def run_variant(name: str, decompose: DecomposeFn, patch: bool,
                datasets: dict[str, list[dict[str, Any]]],
                labels: dict[str, dict[str, str]]
                ) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """Run one variant over all datasets (monkeypatch+restore inside)."""
    original = qa_module.decompose_claims
    if patch:
        qa_module.decompose_claims = decompose
    try:
        module = QAConsistencyModule(
            use_experts=True,
            use_nli_residual=True,
            nli_model_path=NLI_MODEL_PATH,
            nli_gate=NLI_GATE,
        )
        per_dataset: dict[str, Any] = {}
        all_preds: dict[str, dict[str, str]] = {}
        for ds_name in DATASET_ORDER:
            records = datasets[ds_name]
            metrics, preds, unavailable = eval_dataset(
                module, records, labels[ds_name])
            if unavailable:
                print(f"WARNING: {name}/{ds_name}: NLI残差模型不可用"
                      "(结果退化为无L2, 检查models/nli/distilled_v1)")
            all_preds[ds_name] = preds
            per_dataset[ds_name] = {
                "metrics": metrics,
                "claim_stats": claim_statistics(decompose, records),
                "per_instance_verdicts": preds,
            }
            support = metrics["per_class"]["support"]
            stats = per_dataset[ds_name]["claim_stats"]
            print(f"[{name}] {ds_name:12s} n={len(records):3d} "
                  f"acc={metrics['accuracy']:.4f} "
                  f"mF1={metrics['macro_f1']:.4f} "
                  f"supF1={support['f1']:.3f} "
                  f"claims={stats['n_claims']} "
                  f"({stats['claims_per_instance']}/inst)")
        return per_dataset, all_preds
    finally:
        if patch:
            qa_module.decompose_claims = original


def flip_analysis(datasets: dict[str, list[dict[str, Any]]],
                  labels: dict[str, dict[str, str]],
                  preds_a: dict[str, dict[str, str]],
                  preds_c: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Per-dataset verdict flips A→C: corrected / regressed / other."""
    out: dict[str, Any] = {}
    for ds_name in DATASET_ORDER:
        gold = labels[ds_name]
        changed = 0
        corrected: list[dict[str, str]] = []
        regressed: list[dict[str, str]] = []
        other: list[dict[str, str]] = []
        for record in datasets[ds_name]:
            iid = str(record["instance_id"])
            before = preds_a[ds_name].get(iid)
            after = preds_c[ds_name].get(iid)
            if before is None or after is None or before == after:
                continue
            changed += 1
            entry = {"instance_id": iid, "a": before, "c": after,
                     "gold": gold[iid]}
            if after == gold[iid]:
                corrected.append(entry)
            elif before == gold[iid]:
                regressed.append(entry)
            else:
                other.append(entry)
        out[ds_name] = {
            "n_changed": changed,
            "corrected_a_wrong_c_right": corrected,
            "regressed_a_right_c_wrong": regressed,
            "moved_both_wrong": other,
        }
    return out


# ── reporting ───────────────────────────────────────────────────────────────


def device_report() -> dict[str, Any]:
    try:
        import torch
        return {"torch_cuda_available": bool(torch.cuda.is_available())}
    except (ImportError, OSError):
        return {"torch_cuda_available": False}


def git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
            text=True, timeout=10, check=False)
        return proc.stdout.strip()[:12] if proc.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def nli_cache_mode() -> str:
    for entry in nli_residual._MODEL_CACHE.values():
        mode = str(entry.get("mode", ""))
        if mode and mode != "unavailable":
            return mode
    return "not_loaded"


def print_report(results: dict[str, Any], flips: dict[str, Any],
                 triggers: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print(f"decomp fix: A=typed v1 vs C=v2 fixed "
          f"({NLI_MODEL_PATH}, gate={NLI_GATE})")
    print("=" * 78)
    header = (f"{'variant':11s} {'dataset':12s} {'n':>4s} {'acc':>7s} "
              f"{'mF1':>7s} {'sF1':>6s} {'sP':>6s} {'sR':>6s} "
              f"{'cl/inst':>8s} {'avglen':>7s}")
    print(header)
    print("-" * len(header))
    for variant in ("A_typed", "C_fix"):
        for ds_name in DATASET_ORDER:
            entry = results[variant][ds_name]
            m = entry["metrics"]
            sc = m["per_class"]["support"]
            st = entry["claim_stats"]
            print(f"{variant:11s} {ds_name:12s} {st['n_instances']:4d} "
                  f"{m['accuracy']:7.4f} {m['macro_f1']:7.4f} "
                  f"{sc['f1']:6.3f} {sc['precision']:6.3f} "
                  f"{sc['recall']:6.3f} "
                  f"{st['claims_per_instance']:8.2f} "
                  f"{st['claim_len_avg']:7.1f}")
    print("\nper-class P/R/F1:")
    for variant in ("A_typed", "C_fix"):
        for ds_name in DATASET_ORDER:
            pc = results[variant][ds_name]["metrics"]["per_class"]
            cells = " | ".join(
                f"{label}: P={pc[label]['precision']:.3f} "
                f"R={pc[label]['recall']:.3f} F1={pc[label]['f1']:.3f}"
                for label in ("support", "refute", "not_in_evidence"))
            print(f"  {variant:11s} {ds_name:12s} {cells}")
    print("\nclaim kind distribution:")
    for variant in ("A_typed", "C_fix"):
        for ds_name in DATASET_ORDER:
            kinds = results[variant][ds_name]["claim_stats"]["kind_distribution"]
            print(f"  {variant:11s} {ds_name:12s} {kinds}")
    print("\nv2 fix triggers (deterministic, pre-run):")
    for ds_name in DATASET_ORDER:
        t = triggers[ds_name]
        print(f"  {ds_name:12s} answers_touched={t['answers_touched']:3d} "
              f"colon_splits={t['colon_splits']:3d} "
              f"framework_drops={t['framework_drops']:3d} "
              f"enum_downgrades={t['enum_open_list_downgrades']:3d}")
    print("\nverdict flips A→C:")
    for ds_name in DATASET_ORDER:
        f = flips[ds_name]
        print(f"  {ds_name:12s} changed={f['n_changed']:3d} "
              f"corrected={len(f['corrected_a_wrong_c_right']):3d} "
              f"regressed={len(f['regressed_a_right_c_wrong']):3d} "
              f"both_wrong={len(f['moved_both_wrong']):3d}")
        for entry in f["corrected_a_wrong_c_right"]:
            print(f"    + {entry['instance_id']}: {entry['a']}"
                  f"→{entry['c']} (gold={entry['gold']})")
        for entry in f["regressed_a_right_c_wrong"]:
            print(f"    - {entry['instance_id']}: {entry['a']}"
                  f"→{entry['c']} (gold={entry['gold']})")


# ── main ────────────────────────────────────────────────────────────────────


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="每个数据集只跑前N条(冒烟测试用)")
    parser.add_argument("--out", type=Path, default=OUT_PATH,
                        help="结果json落盘路径")
    args = parser.parse_args()

    datasets = load_datasets()
    if args.limit:
        datasets = {name: recs[:args.limit]
                    for name, recs in datasets.items()}
    labels = load_labels(datasets)
    print("datasets: " + ", ".join(f"{k}={len(v)}" for k, v in datasets.items()))
    print(f"device: {device_report()}")

    variants: list[tuple[str, DecomposeFn, bool]] = [
        ("A_typed", typed_decompose, False),
        ("C_fix", decompose_claims_v2, True),
    ]
    results: dict[str, Any] = {}
    preds_by_variant: dict[str, dict[str, dict[str, str]]] = {}
    for name, decompose, patch in variants:
        per_dataset, all_preds = run_variant(
            name, decompose, patch, datasets, labels)
        results[name] = per_dataset
        preds_by_variant[name] = all_preds

    flips = flip_analysis(datasets, labels, preds_by_variant["A_typed"],
                          preds_by_variant["C_fix"])
    triggers = {ds_name: fix_triggers(recs)
                for ds_name, recs in datasets.items()}
    baseline_ok = all(
        results["A_typed"][ds]["metrics"]["accuracy"] == known["accuracy"]
        and results["A_typed"][ds]["metrics"]["macro_f1"] == known["macro_f1"]
        for ds, known in KNOWN_A.items())
    if not baseline_ok:
        print("WARNING: variant A 未复现消融实验登记基线"
              f"({ {ds: k for ds, k in KNOWN_A.items()} })")

    report = {
        "experiment": ("decomp_fix_v1: typed claim decomposition v1 (A) "
                       "vs v2 colon-split/framework-filter/subject-"
                       "inheritance/enum-downgrade (C)"),
        "recorded": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "config": {
            "module": ("QAConsistencyModule(use_experts=True, "
                       "use_nli_residual=True)"),
            "nli_model_path": NLI_MODEL_PATH,
            "nli_gate": NLI_GATE,
            "aggregation": "strict",
        },
        "fix_rules": {
            "colon_split": ("semantic claim '题名：描述' (title 2-10 chars, "
                            "description >=8 chars) -> two semantic claims"),
            "framework_filter": ("claim matching (以下|如下)(特点|操作|功能|"
                                 "几类|要求|参数|步骤|内容|方面) and len<30 "
                                 "dropped"),
            "subject_inheritance": ("verb-initial description claim "
                                    "inherits colon title as attr"),
            "enum_open_list_downgrade": ("enum claim containing 如 or "
                                         "包括但不限于 -> kind=semantic"),
        },
        "isolation_note": ("L0/L1 experts use answer_structure.decompose_answer "
                           "(unpatched); only the per-claim typed channel is "
                           "changed; attr (fix 3) is inert under this config "
                           "(semantic judge path inactive), so C differs from "
                           "A through fixes 1/2/4 only"),
        "datasets": {name: len(recs) for name, recs in datasets.items()},
        "device": device_report(),
        "nli_cache_mode": nli_cache_mode(),
        "baseline_reproduced": baseline_ok,
        "known_a_baseline": KNOWN_A,
        "fix_triggers": triggers,
        "variants": results,
        "flips_a_to_c": flips,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    print_report(results, flips, triggers)
    print(f"\nbaseline_reproduced={baseline_ok} "
          f"nli_cache_mode={report['nli_cache_mode']}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
