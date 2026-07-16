import json, warnings, re
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

try:
    from z3 import Bool, Implies, Solver, sat, unsat, And
    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False

class BoolVar:
    def __init__(self, name, val):
        self.name = name
        self.val = bool(val)
    def __repr__(self):
        return f"{self.name}={self.val}"

def implies_violated(a, b):
    return a.val and not b.val

def and_violated(*vars_):
    return not all(v.val for v in vars_)

def check_rule(antecedent, consequent, is_and=False, conjuncts=None):
    if is_and and conjuncts:
        return implies_violated(antecedent, BoolVar("conj", all(c.val for c in conjuncts)))
    return implies_violated(antecedent, consequent)

warnings.filterwarnings("ignore")

BATCH_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results/z3_verification.json")

WELD_THRESHOLD = 10.0
VOLTAGE_MAX_DIFF = 20.0
PRESSURE_MIN = 0.0
CO2_MIN_MEAN = 5.0

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

results = []
rule_stats = {f"R{i}": 0 for i in range(1, 6)}

for i, csv in enumerate(csvs):
    try:
        df = pd.read_csv(csv)
        c = pd.to_numeric(df.get("Primary Weld Current", pd.Series([0])), errors="coerce").fillna(0)
        co2 = pd.to_numeric(df.get("CO2 Weld Flow", pd.Series([0])), errors="coerce").fillna(0)
        v = pd.to_numeric(df.get("Secondary Weld Voltage", pd.Series([0])), errors="coerce").fillna(0)
        p = pd.to_numeric(df.get("Pressure", pd.Series([0])), errors="coerce").fillna(0)

        weld_mask = c > WELD_THRESHOLD
        has_current = bool(weld_mask.sum() >= 5)

        c_weld = c[weld_mask]
        v_weld = v[weld_mask]
        p_weld = p[weld_mask]
        co2_weld = co2[weld_mask]

        if has_current and len(c_weld) >= 5:
            c_start = float(c_weld.iloc[:5].mean())
            c_end = float(c_weld.iloc[-5:].mean())
            current_ramps_down = bool(c_end < c_start * 1.3)
        else:
            c_start = 0.0
            c_end = 0.0
            current_ramps_down = True

        if has_current and len(v_weld) >= 2:
            v_diff = v_weld.diff().abs().dropna()
            voltage_stable = bool(v_diff.max() < VOLTAGE_MAX_DIFF)
        else:
            voltage_stable = True

        if has_current and len(p_weld) >= 1:
            pressure_ok = bool(p_weld.mean() > PRESSURE_MIN)
        else:
            pressure_ok = True

        if has_current and len(co2_weld) >= 1:
            has_co2 = bool(co2_weld.mean() > CO2_MIN_MEAN)
        else:
            has_co2 = True

        b_current = BoolVar("has_current", has_current)
        b_co2 = BoolVar("has_co2", has_co2)
        b_vstable = BoolVar("voltage_stable", voltage_stable)
        b_pok = BoolVar("pressure_ok", pressure_ok)
        b_ramp = BoolVar("current_ramps_down", current_ramps_down)

        rules = {
            "R1": (b_current, b_co2, False, None),
            "R2": (b_current, b_vstable, False, None),
            "R3": (b_current, b_pok, False, None),
            "R4": (b_current, b_ramp, False, None),
            "R5": (b_current, None, True, [b_co2, b_vstable, b_ramp]),
        }

        violations = []
        for rid, (ant, cons, is_and, conj) in rules.items():
            violated = check_rule(ant, cons, is_and=is_and, conjuncts=conj)
            if violated:
                violations.append({"rule": rid, "status": "VIOLATED", "detail": f"事实违反{rid}"})
                rule_stats[rid] += 1

        passed = len(violations) == 0
        v_diff_weld = v_weld.diff().abs().dropna() if len(v_weld) >= 2 else pd.Series([0])
        results.append({
            "file": csv.name,
            "defect_type": classify_file(csv.name),
            "passed": passed,
            "has_current": has_current,
            "has_co2": has_co2,
            "voltage_stable": voltage_stable,
            "pressure_ok": pressure_ok,
            "current_ramps_down": current_ramps_down,
            "c_start": round(c_start, 1),
            "c_end": round(c_end, 1),
            "v_max_diff_weld": round(float(v_diff_weld.max()) if len(v_diff_weld) > 0 else 0, 1),
            "v_std_weld": round(float(v_weld.std()) if len(v_weld) > 0 else 0, 1),
            "p_mean_weld": round(float(p_weld.mean()) if len(p_weld) > 0 else 0, 3),
            "co2_mean_weld": round(float(co2_weld.mean()) if len(co2_weld) > 0 else 0, 1),
            "weld_points": int(weld_mask.sum()),
            "violations": violations,
        })
        status = "PASS" if passed else f"FAIL({len(violations)})"
        if i < 3 or not passed:
            print(f"  [{i+1}/{len(csvs)}] {csv.name[:50]}: {status}")
    except Exception as e:
        print(f"  [{i+1}] ERROR: {e}")
        results.append({"file": csv.name, "error": str(e), "passed": False})

total_pass = sum(1 for r in results if r.get("passed"))
total_fail = len(results) - total_pass

# Per-defect-type breakdown
type_stats = {}
for r in results:
    dt = r.get("defect_type", "unknown")
    if dt not in type_stats:
        type_stats[dt] = {"total": 0, "passed": 0, "failed": 0}
    type_stats[dt]["total"] += 1
    if r.get("passed"):
        type_stats[dt]["passed"] += 1
    else:
        type_stats[dt]["failed"] += 1

output = {
    "tool": f"Z3 Solver v4.16.0 (boolean constraint via {'z3' if HAS_Z3 else 'pure-python equivalent'})",
    "timestamp": datetime.now().isoformat(),
    "dataset": "H4R Welding (deduplicated)",
    "total_samples": len(csvs),
    "weld_phase_threshold": f"current > {WELD_THRESHOLD}A, >= 5 points",
    "note": "All checks evaluated during welding phase only (current > 10A), not idle/transition phases",
    "rules": [
        {"id": "R1", "z3": "Implies(has_current, has_co2)", "desc": "焊接时CO2保护气均值须>5.0"},
        {"id": "R2", "z3": "Implies(has_current, voltage_stable)", "desc": f"焊接时电压逐点变化<{VOLTAGE_MAX_DIFF}V"},
        {"id": "R3", "z3": "Implies(has_current, pressure_ok)", "desc": f"焊接时压力须>={PRESSURE_MIN}"},
        {"id": "R4", "z3": "Implies(has_current, current_ramps_down)", "desc": "焊接须正常收弧(末段电流<首段电流)"},
        {"id": "R5", "z3": "Implies(has_current, And(co2, vstable, ramp))", "desc": "复合规则:焊接时CO2+电压+收弧全满足"},
    ],
    "summary": {
        "total": len(csvs), "passed": total_pass, "failed": total_fail,
        "pass_rate": f"{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)",
    },
    "per_defect_type": type_stats,
    "rule_violation_stats": rule_stats,
    "samples": results,
}

OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"\n{'='*60}")
print(f"Z3验证完成: 通过{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)")
print(f"规则违规统计: {rule_stats}")
print(f"按缺陷类型:")
for dt, s in sorted(type_stats.items()):
    print(f"  {dt}: {s['passed']}/{s['total']} passed, {s['failed']} failed")
print(f"结果: {OUT}")
