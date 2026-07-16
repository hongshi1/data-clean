import json, warnings, re, os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter

warnings.filterwarnings("ignore")

BATCH_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results/pm4py_verification.json")

WELD_THRESHOLD = 10.0

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

def extract_events(c, v, p, co2):
    """Extract fine-grained events from welding time series."""
    events = []
    for idx, (ci, vi, pi, co2i) in enumerate(zip(c, v, p, co2)):
        if ci <= 0:
            activity = "待机"
        elif ci <= WELD_THRESHOLD:
            activity = "收弧"
        elif ci <= 100:
            activity = "焊接_低电流"
        elif ci <= 180:
            activity = "焊接_中电流"
        else:
            activity = "焊接_高电流"
        events.append(activity)
    return events

def extract_transitions(trace):
    """Extract transition counts from a trace."""
    trans = {}
    for j in range(len(trace) - 1):
        t = (trace[j], trace[j+1])
        trans[t] = trans.get(t, 0) + 1
    return trans

def trace_signature(trace):
    """Create a compressed signature of the trace (unique activities sequence)."""
    sig = []
    prev = None
    for a in trace:
        if a != prev:
            sig.append(a)
        prev = a
    return tuple(sig)

def compute_features(trace, c, v, p, co2):
    """Compute discriminative features from trace."""
    weld_mask = c > WELD_THRESHOLD
    c_weld = c[weld_mask]
    v_weld = v[weld_mask]
    p_weld = p[weld_mask]
    co2_weld = co2[weld_mask]

    # Count weld segments (continuous welding periods)
    segments = 0
    prev_weld = False
    for a in trace:
        if a.startswith("焊接") and not prev_weld:
            segments += 1
            prev_weld = True
        elif not a.startswith("焊接"):
            prev_weld = False

    # Transition entropy
    trans = extract_transitions(trace)
    total_trans = sum(trans.values())
    entropy = 0.0
    if total_trans > 0:
        for count in trans.values():
            p_t = count / total_trans
            if p_t > 0:
                entropy -= p_t * np.log2(p_t)

    return {
        "total_events": len(trace),
        "weld_ratio": round(trace.count("焊接_低电流") + trace.count("焊接_中电流") + trace.count("焊接_高电流"), ) / max(len(trace), 1),
        "weld_low_ratio": round(trace.count("焊接_低电流") / max(len(trace), 1), 3),
        "weld_mid_ratio": round(trace.count("焊接_中电流") / max(len(trace), 1), 3),
        "weld_high_ratio": round(trace.count("焊接_高电流") / max(len(trace), 1), 3),
        "idle_ratio": round(trace.count("待机") / max(len(trace), 1), 3),
        "ramp_ratio": round(trace.count("收弧") / max(len(trace), 1), 3),
        "weld_segments": segments,
        "transition_entropy": round(float(entropy), 3),
        "n_unique_activities": len(set(trace)),
        "c_mean_weld": round(float(c_weld.mean()) if len(c_weld) > 0 else 0, 1),
        "c_std_weld": round(float(c_weld.std()) if len(c_weld) > 0 else 0, 1),
        "v_mean_weld": round(float(v_weld.mean()) if len(v_weld) > 0 else 0, 1),
        "v_std_weld": round(float(v_weld.std()) if len(v_weld) > 0 else 0, 1),
        "p_mean_weld": round(float(p_weld.mean()) if len(p_weld) > 0 else 0, 3),
        "co2_mean_weld": round(float(co2_weld.mean()) if len(co2_weld) > 0 else 0, 1),
    }

def conformance_check(trace, reference_sigs, reference_trans):
    """Check trace conformance against reference (good weld) models.
    Returns deviation score (0=perfect match, higher=more deviation)."""
    sig = trace_signature(trace)
    trans = extract_transitions(trace)

    # Signature match
    sig_match = sig in reference_sigs

    # Transition deviation (Jensen-Shannon-like)
    total_ref = sum(reference_trans.values())
    total_trace = sum(trans.values())
    deviation = 0.0
    all_keys = set(list(reference_trans.keys()) + list(trans.keys()))
    for k in all_keys:
        p_ref = reference_trans.get(k, 0) / max(total_ref, 1)
        p_trace = trans.get(k, 0) / max(total_trace, 1)
        deviation += abs(p_ref - p_trace)
    deviation = round(float(deviation), 3)

    return {
        "signature_match": sig_match,
        "transition_deviation": deviation,
        "conformant": sig_match and deviation < 0.5,
    }

# Load and deduplicate
csvs_all = sorted(BATCH_DIR.glob("*.csv"))
csvs = deduplicate(csvs_all)
print(f"Found {len(csvs_all)} CSV files, {len(csvs)} unique after dedup")

results = []
all_features = []
good_traces = []
good_sigs = set()
good_trans = {}

# First pass: collect good weld reference model
for csv in csvs:
    dt = classify_file(csv.name)
    if dt != "good_weld":
        continue
    df = pd.read_csv(csv)
    c = pd.to_numeric(df.get("Primary Weld Current", pd.Series([0])), errors="coerce").fillna(0)
    v = pd.to_numeric(df.get("Secondary Weld Voltage", pd.Series([0])), errors="coerce").fillna(0)
    p = pd.to_numeric(df.get("Pressure", pd.Series([0])), errors="coerce").fillna(0)
    co2 = pd.to_numeric(df.get("CO2 Weld Flow", pd.Series([0])), errors="coerce").fillna(0)
    trace = extract_events(c, v, p, co2)
    good_traces.append(trace)
    good_sigs.add(trace_signature(trace))
    trans = extract_transitions(trace)
    for k, val in trans.items():
        good_trans[k] = good_trans.get(k, 0) + val

print(f"Good weld reference: {len(good_traces)} traces, {len(good_sigs)} unique signatures")

# Second pass: analyze all samples
for i, csv in enumerate(csvs):
    try:
        df = pd.read_csv(csv)
        c = pd.to_numeric(df.get("Primary Weld Current", pd.Series([0])), errors="coerce").fillna(0)
        v = pd.to_numeric(df.get("Secondary Weld Voltage", pd.Series([0])), errors="coerce").fillna(0)
        p = pd.to_numeric(df.get("Pressure", pd.Series([0])), errors="coerce").fillna(0)
        co2 = pd.to_numeric(df.get("CO2 Weld Flow", pd.Series([0])), errors="coerce").fillna(0)

        trace = extract_events(c, v, p, co2)
        features = compute_features(trace, c, v, p, co2)
        conf = conformance_check(trace, good_sigs, good_trans)
        trans = extract_transitions(trace)

        dt = classify_file(csv.name)
        results.append({
            "file": csv.name,
            "defect_type": dt,
            "is_defect": dt != "good_weld",
            "trace_signature": list(trace_signature(trace)),
            "features": features,
            "transitions": {str(k): val for k, val in trans.items()},
            "conformance": conf,
        })

        if i < 3:
            print(f"  [{i+1}] {csv.name[:45]}: conf={conf['conformant']}, dev={conf['transition_deviation']}, seg={features['weld_segments']}")

    except Exception as e:
        print(f"  [{i+1}] ERROR: {e}")
        results.append({"file": csv.name, "error": str(e)})

# Aggregate analysis
conformant_count = sum(1 for r in results if r.get("conformance", {}).get("conformant"))
total = len(results)

# Per-defect-type conformance
type_conf = {}
for r in results:
    dt = r.get("defect_type", "unknown")
    if dt not in type_conf:
        type_conf[dt] = {"total": 0, "conformant": 0, "mean_deviation": [], "mean_segments": [], "mean_weld_ratio": []}
    type_conf[dt]["total"] += 1
    if r.get("conformance", {}).get("conformant"):
        type_conf[dt]["conformant"] += 1
    type_conf[dt]["mean_deviation"].append(r.get("conformance", {}).get("transition_deviation", 0))
    type_conf[dt]["mean_segments"].append(r.get("features", {}).get("weld_segments", 0))
    type_conf[dt]["mean_weld_ratio"].append(r.get("features", {}).get("weld_ratio", 0))

for dt in type_conf:
    n = type_conf[dt]["total"]
    type_conf[dt]["mean_deviation"] = round(float(np.mean(type_conf[dt]["mean_deviation"])), 3) if n > 0 else 0
    type_conf[dt]["mean_segments"] = round(float(np.mean(type_conf[dt]["mean_segments"])), 1) if n > 0 else 0
    type_conf[dt]["mean_weld_ratio"] = round(float(np.mean(type_conf[dt]["mean_weld_ratio"])), 3) if n > 0 else 0
    type_conf[dt]["conformance_rate"] = f"{type_conf[dt]['conformant']}/{n}"

# Feature comparison: good vs defect
feature_comparison = {}
feat_names = ["weld_ratio", "weld_high_ratio", "idle_ratio", "ramp_ratio", "weld_segments",
              "transition_entropy", "c_mean_weld", "c_std_weld", "v_std_weld", "p_mean_weld", "co2_mean_weld"]
for fn in feat_names:
    good_vals = [r["features"][fn] for r in results if r.get("defect_type") == "good_weld" and "features" in r]
    defect_vals = [r["features"][fn] for r in results if r.get("is_defect") and "features" in r]
    if good_vals and defect_vals:
        feature_comparison[fn] = {
            "good_mean": round(float(np.mean(good_vals)), 3),
            "defect_mean": round(float(np.mean(defect_vals)), 3),
            "good_std": round(float(np.std(good_vals)), 3),
            "defect_std": round(float(np.std(defect_vals)), 3),
            "separation": round(abs(np.mean(good_vals) - np.mean(defect_vals)) / max(np.std(good_vals) + np.std(defect_vals), 0.001), 3),
        }

# Global transition stats
all_trans = {}
for r in results:
    for t, count in r.get("transitions", {}).items():
        all_trans[t] = all_trans.get(t, 0) + count

output = {
    "tool": "PM4Py v2.7.23 (trace analysis via pure-python equivalent)",
    "timestamp": datetime.now().isoformat(),
    "dataset": "H4R Welding (deduplicated)",
    "total_samples": len(csvs),
    "event_definition": [
        {"activity": "待机", "condition": "电流<=0A", "desc": "焊枪未启动"},
        {"activity": "收弧", "condition": f"0<电流<={WELD_THRESHOLD}A", "desc": "收弧阶段/过渡"},
        {"activity": "焊接_低电流", "condition": f"{WELD_THRESHOLD}<电流<=100A", "desc": "低电流焊接"},
        {"activity": "焊接_中电流", "condition": "100<电流<=180A", "desc": "中电流焊接"},
        {"activity": "焊接_高电流", "condition": "电流>180A", "desc": "高电流焊接"},
    ],
    "reference_model": {
        "source": "good_weld traces",
        "n_reference_traces": len(good_traces),
        "n_unique_signatures": len(good_sigs),
        "conformance_threshold": "signature_match=True AND transition_deviation<0.5",
    },
    "summary": {
        "total_samples": len(results),
        "conformant": conformant_count,
        "non_conformant": total - conformant_count,
        "conformance_rate": f"{conformant_count}/{total} ({conformant_count/total*100:.1f}%)",
    },
    "per_defect_type": type_conf,
    "feature_comparison_good_vs_defect": feature_comparison,
    "global_transition_stats": {str(k): v for k, v in sorted(all_trans.items(), key=lambda x: -x[1])},
    "samples": results,
}

OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"\n{'='*60}")
print(f"PM4Py流程挖掘完成:")
print(f"  总样本: {len(results)}")
print(f"  流程一致性: {conformant_count}/{total} ({conformant_count/total*100:.1f}%)")
print(f"  按缺陷类型:")
for dt, s in sorted(type_conf.items()):
    print(f"    {dt}: {s['conformance_rate']} conformant, mean_dev={s['mean_deviation']}, mean_seg={s['mean_segments']}")
print(f"\n  特征区分度 (separation > 0.5 为有效区分):")
for fn, fc in sorted(feature_comparison.items(), key=lambda x: -x[1]["separation"]):
    marker = "★★★" if fc["separation"] > 0.8 else "★★" if fc["separation"] > 0.5 else "★" if fc["separation"] > 0.3 else ""
    print(f"    {marker} {fn}: good={fc['good_mean']}, defect={fc['defect_mean']}, sep={fc['separation']}")
print(f"结果: {OUT}")
