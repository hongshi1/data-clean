"""Compile all experiment results into final paper-level summary table."""
import json
from pathlib import Path

RUNS = Path("data/gjb_438c/runs")

# Find relevant runs
full_pipeline = None
lodo = None
gold_proxy = None
id_masked = None

for run in sorted(RUNS.glob("train_full_pipeline_*")):
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    if "T0" in result and "T3" in result:
        full_pipeline = result
        break

for run in sorted(RUNS.glob("lodo_transfer_*")):
    lodo = json.loads((run / "result.json").read_text(encoding="utf-8"))
    break

for run in sorted(RUNS.glob("gold_proxy_eval_*")):
    gold_proxy = json.loads((run / "result.json").read_text(encoding="utf-8"))
    break

for run in sorted(RUNS.glob("id_masked_eval_*")):
    id_masked = json.loads((run / "result.json").read_text(encoding="utf-8"))
    break

print("=" * 80)
print("FULL EXPERIMENT RESULTS SUMMARY (All RQs)")
print("=" * 80)

# Table 1: Main results (T0-T3)
print("\n### Table 1: Main Results (test fold, n=5372)")
print("| Arm | Config | AUC | F1 | Precision | Recall | FM |")
print("|---|---|---:|---:|---:|---:|---:|")
if full_pipeline:
    for arm in ["T0", "T1", "T2", "T3"]:
        r = full_pipeline[arm]
        t = r["test"]
        config = f"{r['input_mode']}, debias={r['use_debias']}"
        print(f"| {arm} | {config} | {t['auc']} | {t['f1']} | {t['precision']} | {t['recall']} | {t['false_merge']} |")

# Table 2: Gold-proxy evaluation
print("\n### Table 2: Gold-Proxy Evaluation (n=2991, exogenous)")
if gold_proxy:
    gp = gold_proxy["gold_proxy"]
    print("| Model | AUC |")
    print("|---|---:|")
    print(f"| Native BGE | {gp['auc_bge']} |")
    print(f"| Qwen3 | {gp['auc_qwen3']} |")
    print(f"| Ensemble | {gp['auc_ensemble']} |")
    print(f"\nBootstrap BGE-Qwen3: {gold_proxy['bootstrap_bge_vs_qwen3']}")

# Table 3: LODO transfer
print("\n### Table 3: LODO Transfer (16 folds)")
if lodo:
    print("| Metric | Value |")
    print("|---|---:|")
    print(f"| Macro AUC | {lodo['macro_auc']} |")
    print(f"| Std AUC | {lodo['std_auc']} |")
    print(f"| Valid folds | {lodo['n_valid_folds']} |")
    print(f"\nPer-doc AUC range: {min(r['auc'] for r in lodo['lodo_per_doc'] if r['auc']):.4f} "
          f"to {max(r['auc'] for r in lodo['lodo_per_doc'] if r['auc']):.4f}")
    print(f"Learning curve: {lodo['learning_curve']}")

# Table 4: ID stratification
print("\n### Table 4: ID Stratification")
if id_masked:
    print("| Subset | AUC | n |")
    print("|---|---:|---:|")
    for key in ["native_full", "native_both_id", "native_no_id"]:
        if key in id_masked:
            r = id_masked[key]
            print(f"| {key} | {r['auc']} | {r['n']} |")
    if "native_delta_id" in id_masked:
        print(f"\nDelta_ID = {id_masked['native_delta_id']}")

# RQ Answers
print("\n### RQ Summary")
print("| RQ | Question | Answer | Evidence |")
print("|---|---|---|---|")
if full_pipeline:
    t2 = full_pipeline["T2"]["test"]
    t0 = full_pipeline["T0"]["test"]
    print(f"| RQ1 | Residual > raw on no-ID? | Partial (fusion+debias=T2 best) | T2 AUC={t2['auc']} vs T0={t0['auc']} |")
    print(f"| RQ2 | Template reduces variance? | See LODO | LODO std={lodo['std_auc'] if lodo else 'N/A'} |")
    print(f"| RQ3 | Fusion > single? | No (T1<T0 alone) | T1={full_pipeline['T1']['test']['auc']} < T0={t0['auc']} |")
    print(f"| RQ4 | De-bias reduces Delta_ID? | Native Delta_ID minimal | Delta_ID={id_masked.get('native_delta_id', 'N/A') if id_masked else 'N/A'} |")
    print(f"| RQ5 | LODO ≈ inner fold? | No (gap 7.4pt) | LODO={lodo['macro_auc'] if lodo else 'N/A'} vs inner={t0['auc']} |")
    print("| RQ6 | Joint score reveals gap? | Not yet tested | Requires evidence-level gold |")

# Key findings
print("\n### Key Findings")
print("1. De-bias (T2) is the main gain: +1.51pt AUC, +6.81pt F1 vs T1")
print("2. Residual alone (T1) slightly hurts: -0.43pt AUC vs T0")
print("3. Residual + de-bias (T2) synergistic: 0.9851 AUC (best)")
print("4. Gold-proxy BGE achieves perfect AUC (1.0) - proxy may be too easy")
print("5. LODO macro 0.9003 ± 0.1328 - doc02 outlier (0.4754) drags down")
print("6. Native Delta_ID = 0.0076 - minimal shortcut in raw BGE space")
print("7. Learning curve: 8→12→15 docs = 0.8868→0.9428→0.9128 (non-monotonic)")

print("\n" + "=" * 80)
