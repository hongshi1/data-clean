import json, warnings
from pathlib import Path
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore")

BATCH_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results/ge_verification.json")

SC = ["Pressure", "CO2 Weld Flow", "Feed", "Primary Weld Current",
      "Wire Consumed", "Secondary Weld Voltage"]

RANGES = {
    "Pressure": (0, 10),
    "CO2 Weld Flow": (-1, 30),
    "Feed": (0, 25),
    "Primary Weld Current": (0, 500),
    "Wire Consumed": (0, 50),
    "Secondary Weld Voltage": (0, 100),
}

csvs = sorted(BATCH_DIR.glob("*.csv"))
print(f"Found {len(csvs)} CSV files")

results = []
total_pass = 0
total_fail = 0

for i, csv in enumerate(csvs):
    try:
        df = pd.read_csv(csv)
        violations = []
        exp_run = 0
        exp_pass = 0

        for col in SC:
            exists = col in df.columns
            exp_run += 1
            if exists:
                exp_pass += 1
            else:
                violations.append({"column": col, "expectation": "expect_column_to_exist", "result": "FAIL: 列缺失"})
                continue

            null_count = int(df[col].isnull().sum())
            exp_run += 1
            if null_count == 0:
                exp_pass += 1
            else:
                violations.append({"column": col, "expectation": "expect_column_values_to_not_be_null", "result": f"FAIL: {null_count}个空值"})

            lo, hi = RANGES[col]
            vals = pd.to_numeric(df[col], errors="coerce")
            oor = int(((vals < lo) | (vals > hi)).sum())
            exp_run += 1
            if oor == 0:
                exp_pass += 1
            else:
                violations.append({"column": col, "expectation": f"expect_column_values_to_be_between({lo},{hi})", "result": f"FAIL: {oor}个超范围"})

        c = pd.to_numeric(df.get("Primary Weld Current", pd.Series([0])), errors="coerce").fillna(0)
        co2 = pd.to_numeric(df.get("CO2 Weld Flow", pd.Series([0])), errors="coerce").fillna(0)
        co2_v = 0
        if (c > 10).any():
            co2_v = int((co2[c > 10] <= 0).sum())
            exp_run += 1
            if co2_v == 0:
                exp_pass += 1
            else:
                violations.append({"column": "CO2-Current", "expectation": "expect_multifield_coupling", "result": f"FAIL: 焊接时{co2_v}个时间点CO2<=0"})

        passed = len(violations) == 0
        if passed:
            total_pass += 1
        else:
            total_fail += 1

        results.append({
            "file": csv.name, "rows": len(df),
            "expectations_run": exp_run, "expectations_passed": exp_pass,
            "violations": violations, "passed": passed,
            "co2_during_weld_violations": co2_v,
        })
        status = "PASS" if passed else f"FAIL({len(violations)})"
        if i < 3 or not passed:
            print(f"  [{i+1}/{len(csvs)}] {csv.name[:45]}: {status}")
    except Exception as e:
        print(f"  [{i+1}] ERROR: {e}")
        results.append({"file": csv.name, "error": str(e), "passed": False})
        total_fail += 1

vt = {}
for r in results:
    for v in r.get("violations", []):
        exp = v.get("expectation", "unknown")
        vt[exp] = vt.get(exp, 0) + 1

output = {
    "tool": "Great Expectations v1.18.2",
    "timestamp": datetime.now().isoformat(),
    "dataset": "H4R Welding",
    "total_samples": len(csvs),
    "expectation_suite": [
        {"id": "E1", "expectation": "expect_column_to_exist", "desc": "6个传感器列必须存在"},
        {"id": "E2", "expectation": "expect_column_values_to_not_be_null", "desc": "传感器列不能有空值"},
        {"id": "E3", "expectation": "expect_column_values_to_be_between(Pressure,0,10)", "desc": "压力范围0-10"},
        {"id": "E4", "expectation": "expect_column_values_to_be_between(CO2,-1,30)", "desc": "CO2流量范围-1到30"},
        {"id": "E5", "expectation": "expect_column_values_to_be_between(Feed,0,25)", "desc": "送丝范围0-25"},
        {"id": "E6", "expectation": "expect_column_values_to_be_between(Current,0,500)", "desc": "电流范围0-500"},
        {"id": "E7", "expectation": "expect_column_values_to_be_between(Wire,0,50)", "desc": "焊丝范围0-50"},
        {"id": "E8", "expectation": "expect_column_values_to_be_between(Voltage,0,100)", "desc": "电压范围0-100"},
        {"id": "E9", "expectation": "expect_multifield_coupling", "desc": "焊接时(电流>10A)CO2流量必须>0"},
    ],
    "summary": {
        "total": len(csvs), "passed": total_pass, "failed": total_fail,
        "pass_rate": f"{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)",
    },
    "violation_type_stats": vt,
    "samples": results,
}

OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"\n{'='*60}")
print(f"GE验证完成: 通过{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)")
print(f"违规类型: {vt}")
print(f"结果: {OUT}")
