import json, datetime, subprocess, os
from pathlib import Path
import pandas as pd, numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import cross_val_predict
from sklearn.preprocessing import LabelEncoder

os.environ["OMP_NUM_THREADS"] = "1"

if __name__ == '__main__':
    BATCH = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
    OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results")
sensor_cols = ["Pressure","CO2 Weld Flow","Feed","Primary Weld Current","Wire Consumed","Secondary Weld Voltage"]

all_csvs = sorted(BATCH.glob("*.csv"))
jpgs = sorted(BATCH.glob("*.jpg"))
samples = []
for csv in all_csvs:
    name = csv.name
    if "burnthrough" in name: label = "burnthrough"
    elif "crater" in name: label = "crater_crack"
    elif "lack" in name and "fusion" in name: label = "lack_of_fusion"
    elif "excessive" in name: label = "excessive"
    elif "overlap" in name: label = "overlap"
    elif "good" in name: label = "good"
    else: continue
    for jpg in jpgs:
        if csv.stem[:20] in jpg.stem:
            samples.append({"csv": str(csv), "jpg": str(jpg), "label": label})
            break

print(f"有效: {len(samples)}样本")
for label in sorted(set(s["label"] for s in samples)):
    n = sum(1 for s in samples if s["label"] == label)
    print(f"  {label}: {n}个")

for s in samples:
    df = pd.read_csv(s["csv"])
    current = pd.to_numeric(df.get("Primary Weld Current", pd.Series([0])), errors='coerce').fillna(0)
    voltage = pd.to_numeric(df.get("Secondary Weld Voltage", pd.Series([0])), errors='coerce').fillna(0)
    s["n_records"] = len(df)
    s["current_mean"] = float(current.mean())
    s["current_std"] = float(current.std())
    s["current_max"] = float(current.max())
    s["voltage_max"] = float(voltage.max())
    s["voltage_std"] = float(voltage.std())

    issues = 0
    for col in sensor_cols:
        if col not in df.columns: issues += 1
    co2 = pd.to_numeric(df.get("CO2 Weld Flow", pd.Series([0])), errors='coerce').fillna(0)
    if (current > 10).any() and (co2[current > 10] <= 0).any(): issues += 1
    s["l1_issues"] = issues
    s["l1_pass"] = issues == 0

    X = df[sensor_cols].apply(pd.to_numeric, errors='coerce').fillna(0).values
    s["n_anomalies"] = int((IsolationForest(contamination=0.1, random_state=42).fit_predict(X) == -1).sum())
    s["event_match"] = (s["n_anomalies"] > 0) == (s["label"] != "good")

    s["fact_conflict"] = False
    if s["label"] == "good" and s["current_std"] > 50: s["fact_conflict"] = True
    elif s["label"] == "burnthrough" and s["current_max"] < 200: s["fact_conflict"] = True
    elif s["label"] == "crater_crack" and s["current_std"] < 40: s["fact_conflict"] = True

    s["l3_violations"] = 0
    if voltage.diff().abs().max() > 20: s["l3_violations"] += 1
    if len(current) > 10 and current.iloc[-1] > 50: s["l3_violations"] += 1
    s["l3_pass"] = s["l3_violations"] == 0
    s["governance_pass"] = s["l1_pass"] and not s["fact_conflict"] and s["l3_pass"]

features = [[s["current_mean"], s["current_std"], s["current_max"], s["voltage_max"], s["voltage_std"], s["n_anomalies"]] for s in samples]
X = np.array(features)
le = LabelEncoder()
y = le.fit_transform([s["label"] for s in samples])
cleanlab_msg = "未运行(样本不足)"
if len(set(y)) > 1 and len(y) >= 10:
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    cv = min(3, len(y) // 2)
    if cv >= 2:
        pred_probs = cross_val_predict(clf, X, y, cv=cv, method='predict_proba')
        from cleanlab.filter import find_label_issues
        from cleanlab.rank import get_label_quality_scores
        issues = find_label_issues(y, pred_probs, return_indices_ranked_by="self_confidence")
        scores = get_label_quality_scores(y, pred_probs)
        cleanlab_msg = f"检出{len(issues)}个标签问题, 均分={scores.mean():.3f}, 最低={scores.min():.3f}"
        for i, s in enumerate(samples):
            s["cleanlab_score"] = float(scores[i])
            s["cleanlab_flagged"] = i in issues
        print(f"\nCleanlab: {cleanlab_msg}")
        for idx in issues[:5]:
            print(f"  样本{idx}: {le.inverse_transform([y[idx]])[0]}, 分数={scores[idx]:.3f}")

g_pass = sum(1 for s in samples if s["governance_pass"])
print(f"\n{'='*60}")
print(f"治理结果: {len(samples)}样本, 通过{g_pass}, 复核{len(samples)-g_pass}")
print(f"{'='*60}")
for label in sorted(set(s["label"] for s in samples)):
    sub = [s for s in samples if s["label"] == label]
    p = sum(1 for s in sub if s["governance_pass"])
    print(f"  {label:20s}: {len(sub)}个(通过{p})")

results = {"total": len(samples), "pass": g_pass, "review": len(samples)-g_pass,
           "cleanlab": cleanlab_msg,
           "label_dist": {l: sum(1 for s in samples if s["label"]==l) for l in set(s["label"] for s in samples)},
           "samples": [{"label": s["label"], "file": Path(s["csv"]).name[:30],
                        "l1": s["l1_pass"], "fact": s["fact_conflict"], "l3": s["l3_pass"],
                        "pass": s["governance_pass"], "current_std": round(s["current_std"],1),
                        "n_anom": s["n_anomalies"], "cleanlab": s.get("cleanlab_score",0)} for s in samples]}
with open(OUT / "batch_results_final.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
print(f"\n已保存: {OUT / 'batch_results_final.json'}")
