"""E2-v3: single-stage mixed distillation, no refute oversampling.

The single-stage E2-v1 regression (test46 0.6562 vs D1 0.8047) is
hypothesized to come from refute-prior explosion: crossdoc refute
claims (34/fold) × 3 oversampling = ~120 refute pairs. This variant
trains on qa91-dev + crossdoc-minus-doc with --oversample-refute 1
(no oversampling) in ONE stage.

D1 baseline: crossdoc150 acc 0.5133, test46 mF1 0.8047.
E2-v1 (single, 3x oversample): held-doc 0.5667, test46 0.6562.
E2-v2 (curriculum):            held-doc 0.5600, test46 0.7014.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEACHER_QA = BASE / "data/gjb_438c/distillation/teacher_labels_v1.jsonl"
TEACHER_CD = (BASE / "data/gjb_438c/distillation"
              / "teacher_labels_crossdoc.jsonl")
OUT_ROOT = BASE / "models/nli"
DOCS = ("05", "06", "07", "08", "10")


def _train(cmd_extra: list[str], tag: str) -> None:
    cmd = [sys.executable, "tools/train_distilled_nli.py", *cmd_extra]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          cwd=str(BASE))
    print(f"[{tag}] exit={proc.returncode}")
    if proc.returncode != 0:
        for line in (proc.stderr or "").strip().splitlines()[-8:]:
            print("   ERR", line[:160])
        raise SystemExit(f"{tag} failed")


def run_fold(doc: str) -> Path:
    final = OUT_ROOT / f"distilled_e2c_loo_C{doc}"
    if (final / "config.json").exists():
        print(f"[fold C{doc}] checkpoint exists, skip training")
        return final
    _train([
        "--teacher-data", str(TEACHER_QA), str(TEACHER_CD),
        "--splits", "dev", "train_only",
        "--corpora", "qa91", "crossdoc",
        "--exclude-doc", f"C{doc}",
        "--oversample-refute", "1",
        "--base", "egt_finetuned_v2",
        "--out-dir", str(final),
    ], f"fold C{doc} single-mixed")
    return final


def eval_fold(doc: str, model_dir: Path) -> dict:
    from algorithms.consistency.eval_lib import (
        build_qa_input,
        classification_metrics,
        load_frozen_qa,
        load_silver_labels,
    )
    from algorithms.consistency.qa_module import QAConsistencyModule

    labels = load_silver_labels(
        BASE / ("data/gjb_438c/runs/"
                "review_qa_with_glm53_582b51e5_20261021_145212"
                "/final_labels.jsonl"))
    split = json.loads(
        (BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json")
        .read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    test_recs = [r for r in load_frozen_qa()
                 if r["instance_id"] not in dev_ids]

    cd_path = (BASE / f"data/gjb_438c/qa_frozen/crossdoc{doc}"
               f"_evalset_v1.jsonl")
    cd_recs = [json.loads(line) for line in
               cd_path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    cd_labels = {r["instance_id"]: r["sound_label"] for r in cd_recs}

    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path=str(model_dir), nli_gate=0.8)

    def run(recs, truth):
        y_true = [truth(r["instance_id"]) for r in recs]
        y_pred = [module.verify(build_qa_input(r)).verdict for r in recs]
        return classification_metrics(y_true, y_pred)

    m_cd = run(cd_recs, lambda iid: cd_labels[iid])
    m_t46 = run(test_recs,
                lambda iid: labels.get(iid, "not_in_evidence"))
    return {"crossdoc_held": m_cd, "test46": m_t46}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    results: dict[str, dict] = {}
    for doc in DOCS:
        model_dir = run_fold(doc)
        m = eval_fold(doc, model_dir)
        cd = m["crossdoc_held"]
        t46 = m["test46"]
        print(f"FOLD C{doc}: held-doc acc={cd['accuracy']:.4f} "
              f"mF1={cd['macro_f1']:.4f} | test46 acc={t46['accuracy']:.4f} "
              f"mF1={t46['macro_f1']:.4f}")
        results[f"C{doc}"] = m

    accs = [results[f"C{d}"]["crossdoc_held"]["accuracy"] for d in DOCS]
    mf1s = [results[f"C{d}"]["crossdoc_held"]["macro_f1"] for d in DOCS]
    t46 = [results[f"C{d}"]["test46"]["macro_f1"] for d in DOCS]
    summary = {
        "design": "single-stage mixed (qa91-dev + crossdoc-minus-doc), "
                  "oversample_refute=1",
        "per_fold": results,
        "held_doc_mean_acc": sum(accs) / len(accs),
        "held_doc_mean_mf1": sum(mf1s) / len(mf1s),
        "test46_mean_mf1": sum(t46) / len(t46),
        "baselines": {
            "d1_crossdoc150_acc": 0.5133,
            "d1_test46_mf1": 0.8047,
            "e2_single_stage_3x": {"held_doc_mean_acc": 0.5667,
                                   "test46_mean_mf1": 0.6562},
            "e2_curriculum": {"held_doc_mean_acc": 0.5600,
                              "test46_mean_mf1": 0.7014},
        },
    }
    out = (BASE / "data/gjb_438c/distillation"
           / "e2_loo_mixed_noos_results_v1.json")
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("\nE2-v3 single-mixed no-oversample summary:")
    print(f"  held-doc acc mean: {summary['held_doc_mean_acc']:.4f} "
          f"(v1 0.5667, v2 0.5600, D1 0.5133)")
    print(f"  held-doc mF1 mean: {summary['held_doc_mean_mf1']:.4f}")
    print(f"  test46 mF1 mean:   {summary['test46_mean_mf1']:.4f} "
          f"(D1 0.8047, v1 0.6562, v2 0.7014)")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
