import json, warnings
from pathlib import Path
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore")

BATCH_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results/declare_verification.json")

csvs = sorted(BATCH_DIR.glob("*.csv"))

DECLARE_RULES = [
    {"id": "D1", "type": "precedence", "name": "焊接前必须待机",
     "formula": "待机 BEFORE 焊接中",
     "check": lambda trace: not (len(trace) > 0 and trace[0] == "焊接中")},
    {"id": "D2", "type": "response", "name": "焊接后必须收弧",
     "formula": "焊接中 -> 收弧 (eventually)",
     "check": lambda trace: not ("焊接中" in trace and "收弧" not in trace)},
    {"id": "D3", "type": "not_coexistence", "name": "收弧后不能再焊接",
     "formula": "NOT(收弧 -> 焊接中)",
     "check": lambda trace: _check_no_weld_after_ramp(trace)},
    {"id": "D4", "type": "alternate_response", "name": "待机和焊接必须交替",
     "formula": "待机 -> 焊接中 -> 待机 (alternate)",
     "check": lambda trace: _check_alternate(trace)},
    {"id": "D5", "type": "chain_precedence", "name": "完整焊接流程链",
     "formula": "待机 -> 焊接中 -> 收弧 -> 待机",
     "check": lambda trace: _check_complete_chain(trace)},
    {"id": "D6", "type": "absence", "name": "不能只有待机(空焊)",
     "formula": "ABSENCE(only 待机)",
     "check": lambda trace: "焊接中" in trace},
]

def _check_no_weld_after_ramp(trace):
    ramp_found = False
    for a in trace:
        if a == "收弧":
            ramp_found = True
        if ramp_found and a == "焊接中":
            return False
    return True

def _check_alternate(trace):
    filtered = [a for a in trace if a in ["待机", "焊接中"]]
    for i in range(len(filtered)-1):
        if filtered[i] == filtered[i+1]:
            return False
    return True

def _check_complete_chain(trace):
    has_idle = "待机" in trace
    has_weld = "焊接中" in trace
    has_ramp = "收弧" in trace
    return has_idle and has_weld and has_ramp

def trace_from_csv(csv):
    df = pd.read_csv(csv)
    c = pd.to_numeric(df.get("Primary Weld Current", pd.Series([0])), errors="coerce").fillna(0)
    trace = []
    for val in c:
        if val > 10:
            trace.append("焊接中")
        elif val > 0:
            trace.append("收弧")
        else:
            trace.append("待机")
    return trace

results = []
rule_stats = {r["id"]: 0 for r in DECLARE_RULES}

for i, csv in enumerate(csvs):
    try:
        trace = trace_from_csv(csv)
        violations = []

        for rule in DECLARE_RULES:
            passed = rule["check"](trace)
            if not passed:
                violations.append({"rule": rule["id"], "rule_name": rule["name"],
                                   "type": rule["type"], "formula": rule["formula"],
                                   "detail": "违反" + rule["name"]})
                rule_stats[rule["id"]] += 1

        passed_all = len(violations) == 0
        results.append({
            "file": csv.name, "trace_length": len(trace),
            "weld_count": trace.count("焊接中"),
            "idle_count": trace.count("待机"),
            "ramp_count": trace.count("收弧"),
            "violations": violations,
            "violation_count": len(violations),
            "passed": passed_all,
        })

        if i < 3 or not passed_all:
            status = "PASS" if passed_all else f"FAIL({len(violations)})"
            print(f"  [{i+1}] {csv.name[:40]}: {status}")

    except Exception as e:
        print(f"  [{i+1}] ERROR: {e}")
        results.append({"file": csv.name, "error": str(e), "passed": False})

total_pass = sum(1 for r in results if r.get("passed"))

output = {
    "tool": "Declare-style Temporal Logic Rules",
    "timestamp": datetime.now().isoformat(),
    "dataset": "H4R Welding",
    "total_samples": len(csvs),
    "rules": [{"id": r["id"], "type": r["type"], "name": r["name"], "formula": r["formula"]} for r in DECLARE_RULES],
    "summary": {
        "total": len(csvs), "passed": total_pass,
        "failed": len(csvs) - total_pass,
        "pass_rate": f"{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)",
    },
    "rule_violation_stats": rule_stats,
    "samples": results,
}

OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"\n{'='*60}")
print(f"Declare时序规则验证: 通过{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)")
print(f"规则违规统计: {rule_stats}")
print(f"结果: {OUT}")
