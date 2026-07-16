import json, warnings, re
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.svm import OneClassSVM
from sklearn.covariance import EllipticEnvelope
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

warnings.filterwarnings("ignore")

BATCH_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results/anomaly_comparison.json")

SC = ["Pressure", "CO2 Weld Flow", "Feed", "Primary Weld Current",
      "Wire Consumed", "Secondary Weld Voltage"]

def classify_file(filename):
    fn = filename.lower()
    if "good" in fn:
        return "good_weld"
    m = re.search(r"defect-weld_(\w+)", fn)
    if m:
        return m.group(1)
    return "unlabeled"

def deduplicate(csvs):
    seen = {}
    for csv in csvs:
        try:
            df = pd.read_csv(csv, usecols=["Part No"])
            pn = df["Part No"].iloc[0]
        except Exception:
            pn = csv.name
        if pn not in seen:
            seen[pn] = csv
        else:
            if "defect" in csv.name.lower() and "defect" not in seen[pn].name.lower():
                seen[pn] = csv
    return sorted(seen.values())

csvs_all = sorted(BATCH_DIR.glob("*.csv"))
csvs = deduplicate(csvs_all)
print(f"Found {len(csvs_all)} CSV files, {len(csvs)} unique after dedup")

# Ground truth: good=0 (normal), defect=1 (anomaly)
gt_labels = []
file_features = []
per_file_results = []

methods = ["IsolationForest", "OneClassSVM", "EllipticEnvelope", "LOF"]

for i, csv in enumerate(csvs):
    try:
        df = pd.read_csv(csv)
        X = df[SC].apply(pd.to_numeric, errors="coerce").fillna(0).values
        dt = classify_file(csv.name)
        is_defect = 1 if dt != "good_weld" else 0
        gt_labels.append(is_defect)

        # Per-point anomaly predictions
        anomalies = {}

        iso = IsolationForest(contamination=0.1, random_state=42, n_jobs=1)
        pred_iso = iso.fit_predict(X)
        score_iso = -iso.score_samples(X)  # higher = more anomalous
        anomalies["IsolationForest"] = {
            "point_anomalies": int((pred_iso == -1).sum()),
            "anomaly_ratio": round(float((pred_iso == -1).mean()), 3),
            "mean_score": round(float(score_iso.mean()), 4),
            "max_score": round(float(score_iso.max()), 4),
        }

        svm = OneClassSVM(nu=0.1, kernel="rbf", gamma="scale")
        pred_svm = svm.fit_predict(X)
        score_svm = -svm.score_samples(X)
        anomalies["OneClassSVM"] = {
            "point_anomalies": int((pred_svm == -1).sum()),
            "anomaly_ratio": round(float((pred_svm == -1).mean()), 3),
            "mean_score": round(float(score_svm.mean()), 4),
            "max_score": round(float(score_svm.max()), 4),
        }

        ee = EllipticEnvelope(contamination=0.1, random_state=42)
        ee.fit(X)
        pred_ee = ee.predict(X)
        score_ee = -ee.score_samples(X)
        anomalies["EllipticEnvelope"] = {
            "point_anomalies": int((pred_ee == -1).sum()),
            "anomaly_ratio": round(float((pred_ee == -1).mean()), 3),
            "mean_score": round(float(score_ee.mean()), 4),
            "max_score": round(float(score_ee.max()), 4),
        }

        lof = LocalOutlierFactor(contamination=0.1, n_neighbors=20)
        pred_lof = lof.fit_predict(X)
        score_lof = -lof.negative_outlier_factor_
        anomalies["LOF"] = {
            "point_anomalies": int((pred_lof == -1).sum()),
            "anomaly_ratio": round(float((pred_lof == -1).mean()), 3),
            "mean_score": round(float(score_lof.mean()), 4),
            "max_score": round(float(score_lof.max()), 4),
        }

        # Welding-phase features for file-level anomaly scoring
        c = pd.to_numeric(df["Primary Weld Current"], errors="coerce").fillna(0)
        weld_mask = c > 10
        if weld_mask.sum() >= 5:
            c_weld = c[weld_mask]
            v_weld = pd.to_numeric(df["Secondary Weld Voltage"], errors="coerce").fillna(0)[weld_mask]
            p_weld = pd.to_numeric(df["Pressure"], errors="coerce").fillna(0)[weld_mask]
            co2_weld = pd.to_numeric(df["CO2 Weld Flow"], errors="coerce").fillna(0)[weld_mask]
            feats = {
                "c_mean": float(c_weld.mean()),
                "c_std": float(c_weld.std()),
                "v_mean": float(v_weld.mean()),
                "v_std": float(v_weld.std()),
                "p_mean": float(p_weld.mean()),
                "co2_mean": float(co2_weld.mean()),
                "weld_ratio": float(weld_mask.mean()),
            }
        else:
            feats = {k: 0.0 for k in ["c_mean", "c_std", "v_mean", "v_std", "p_mean", "co2_mean", "weld_ratio"]}
        file_features.append(feats)

        per_file_results.append({
            "file": csv.name,
            "defect_type": dt,
            "is_defect": bool(is_defect),
            "rows": len(df),
            "anomalies": anomalies,
            "features": {k: round(v, 3) for k, v in feats.items()},
        })

        if i < 3:
            print(f"  [{i+1}] {csv.name[:40]} ({dt}): IF_ratio={anomalies['IsolationForest']['anomaly_ratio']}, SVM_ratio={anomalies['OneClassSVM']['anomaly_ratio']}")

    except Exception as e:
        print(f"  [{i+1}] ERROR: {e}")
        per_file_results.append({"file": csv.name, "error": str(e)})
        gt_labels.append(0)
        file_features.append({})

gt_labels = np.array(gt_labels)
n_good = int((gt_labels == 0).sum())
n_defect = int((gt_labels == 1).sum())
print(f"\nGround truth: {n_good} good, {n_defect} defect")

# File-level evaluation: use anomaly_ratio as anomaly score, threshold at median of good welds
evaluation = {}

# Initialize per-type detection with correct totals (counted once)
all_types = set(classify_file(r["file"]) for r in per_file_results if "file" in r)
per_type_detection = {}
for r in per_file_results:
    dt = r.get("defect_type", "unknown")
    if dt not in per_type_detection:
        per_type_detection[dt] = {"total": 0}
    per_type_detection[dt]["total"] += 1

for m in methods:
    # Extract file-level anomaly scores (anomaly ratio = fraction of anomalous points)
    scores = []
    file_preds = []
    for r in per_file_results:
        if "anomalies" in r and m in r["anomalies"]:
            scores.append(r["anomalies"][m]["anomaly_ratio"])
        else:
            scores.append(0.0)

    scores = np.array(scores)

    # Use good weld scores to set threshold (mean + 2*std of good welds)
    good_scores = scores[gt_labels == 0]
    if len(good_scores) > 1:
        threshold = float(good_scores.mean() + 2 * good_scores.std())
    else:
        threshold = float(np.median(scores))

    # File-level prediction: anomaly if score > threshold
    file_preds = (scores > threshold).astype(int)

    # Metrics
    tp = int(((file_preds == 1) & (gt_labels == 1)).sum())
    fp = int(((file_preds == 1) & (gt_labels == 0)).sum())
    tn = int(((file_preds == 0) & (gt_labels == 0)).sum())
    fn = int(((file_preds == 0) & (gt_labels == 1)).sum())

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    # ROC-AUC (using continuous scores)
    try:
        auc = roc_auc_score(gt_labels, scores)
    except Exception:
        auc = 0.5

    evaluation[m] = {
        "threshold": round(threshold, 4),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "auc_roc": round(auc, 3),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
    }

    # Per-defect-type detection (track per method, don't re-count total)
    for dt in per_type_detection:
        per_type_detection[dt][m] = {"detected": 0}
    for j, r in enumerate(per_file_results):
        dt = r.get("defect_type", "unknown")
        if file_preds[j] == 1 and gt_labels[j] == 1:
            per_type_detection[dt][m]["detected"] += 1

    # Attach file-level prediction to results
    for j, r in enumerate(per_file_results):
        if "anomalies" in r and m in r.get("anomalies", {}):
            r["anomalies"][m]["file_level_pred"] = "anomaly" if file_preds[j] == 1 else "normal"
            r["anomalies"][m]["file_level_score"] = round(float(scores[j]), 4)

# Feature-based rule detection (simple threshold rules as baseline)
# Based on PM4Py feature analysis: co2_mean, p_mean, c_std are discriminative
good_feats = [f for f, l in zip(file_features, gt_labels) if l == 0 and f]
defect_feats = [f for f, l in zip(file_features, gt_labels) if l == 1 and f]

if good_feats and defect_feats:
    rule_thresholds = {}
    for feat_name in ["co2_mean", "p_mean", "c_std", "v_std"]:
        g_vals = [f[feat_name] for f in good_feats]
        d_vals = [f[feat_name] for f in defect_feats]
        g_mean, g_std = np.mean(g_vals), np.std(g_vals)
        d_mean = np.mean(d_vals)
        # Threshold: midpoint between good and defect means, biased toward good
        if d_mean < g_mean:
            threshold = g_mean - 1.5 * g_std
            rule_thresholds[feat_name] = {"threshold": round(threshold, 3), "direction": "below"}
        else:
            threshold = g_mean + 1.5 * g_std
            rule_thresholds[feat_name] = {"threshold": round(threshold, 3), "direction": "above"}

    # Rule-based prediction: anomaly if ANY feature violates threshold
    rule_preds = []
    for f in file_features:
        if not f:
            rule_preds.append(0)
            continue
        is_anomaly = False
        for feat_name, th in rule_thresholds.items():
            if th["direction"] == "below" and f[feat_name] < th["threshold"]:
                is_anomaly = True
            elif th["direction"] == "above" and f[feat_name] > th["threshold"]:
                is_anomaly = True
        rule_preds.append(int(is_anomaly))
    rule_preds = np.array(rule_preds)

    tp = int(((rule_preds == 1) & (gt_labels == 1)).sum())
    fp = int(((rule_preds == 1) & (gt_labels == 0)).sum())
    tn = int(((rule_preds == 0) & (gt_labels == 0)).sum())
    fn = int(((rule_preds == 0) & (gt_labels == 1)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    evaluation["RuleBased"] = {
        "thresholds": rule_thresholds,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
    }

    # Per-type detection for rule-based
    for dt in per_type_detection:
        per_type_detection[dt]["RuleBased"] = {"detected": 0}
    for j, r in enumerate(per_file_results):
        dt = r.get("defect_type", "unknown")
        if rule_preds[j] == 1 and gt_labels[j] == 1:
            per_type_detection[dt]["RuleBased"]["detected"] += 1

output = {
    "tool": "Anomaly Detection with Supervised Evaluation (sklearn)",
    "timestamp": datetime.now().isoformat(),
    "dataset": "H4R Welding (deduplicated, ground-truth labeled)",
    "total_samples": len(csvs),
    "ground_truth": {"good": n_good, "defect": n_defect},
    "evaluation_method": "File-level: anomaly_ratio threshold = mean(good) + 2*std(good); Rule-based: welding-phase feature thresholds",
    "methods": [
        {"name": "IsolationForest", "params": "contamination=0.1, random_state=42", "type": "基于隔离"},
        {"name": "OneClassSVM", "params": "nu=0.1, kernel=rbf, gamma=scale", "type": "基于边界"},
        {"name": "EllipticEnvelope", "params": "contamination=0.1, random_state=42", "type": "基于分布"},
        {"name": "LOF", "params": "contamination=0.1, n_neighbors=20", "type": "基于密度"},
        {"name": "RuleBased", "params": "welding-phase feature thresholds", "type": "基于规则(基线)"},
    ],
    "evaluation": evaluation,
    "per_defect_type_detection": per_type_detection,
    "samples": per_file_results,
}

OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"\n{'='*60}")
print(f"异常检测有监督评估完成 ({len(csvs)}样本, {n_good}good/{n_defect}defect)")
print(f"{'='*60}")
print(f"{'Method':<20} {'Precision':<10} {'Recall':<10} {'F1':<10} {'AUC-ROC':<10} {'TP':<5} {'FP':<5} {'TN':<5} {'FN':<5}")
print("-" * 85)
for m in ["IsolationForest", "OneClassSVM", "EllipticEnvelope", "LOF", "RuleBased"]:
    e = evaluation[m]
    print(f"{m:<20} {e['precision']:<10} {e['recall']:<10} {e['f1']:<10} {e.get('auc_roc', '-'):<10} {e['tp']:<5} {e['fp']:<5} {e['tn']:<5} {e['fn']:<5}")
print(f"\n按缺陷类型检测率:")
for dt, s in sorted(per_type_detection.items()):
    if dt == "good_weld":
        continue
    det_if = s.get("IsolationForest", {}).get("detected", 0)
    det_rule = s.get("RuleBased", {}).get("detected", 0)
    print(f"  {dt} (n={s['total']}): IF={det_if}/{s['total']}, Rule={det_rule}/{s['total']}")
print(f"\n结果: {OUT}")
