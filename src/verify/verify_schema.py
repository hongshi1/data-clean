import json, warnings
from pathlib import Path
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore")

BATCH_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results/schema_verification.json")

SC = ["Pressure", "CO2 Weld Flow", "Feed", "Primary Weld Current",
      "Wire Consumed", "Secondary Weld Voltage"]

SCHEMA = {
    "Pressure": {"dtype": "float64", "range": (0, 10), "nullable": False},
    "CO2 Weld Flow": {"dtype": "float64", "range": (-1, 30), "nullable": False},
    "Feed": {"dtype": "float64", "range": (0, 25), "nullable": False},
    "Primary Weld Current": {"dtype": "float64", "range": (0, 500), "nullable": False},
    "Wire Consumed": {"dtype": "float64", "range": (0, 50), "nullable": False},
    "Secondary Weld Voltage": {"dtype": "float64", "range": (0, 100), "nullable": False},
}

MULTIFIELD_RULES = [
    {"id": "MF1", "name": "CO2-电流耦合", "rule": "电流>10A时CO2必须>0",
     "check": lambda df: int((pd.to_numeric(df["CO2 Weld Flow"], errors="coerce").fillna(0)[pd.to_numeric(df["Primary Weld Current"], errors="coerce").fillna(0) > 10] <= 0).sum())},
    {"id": "MF2", "name": "焊丝递增", "rule": "Wire Consumed应单调递增",
     "check": lambda df: int((pd.to_numeric(df["Wire Consumed"], errors="coerce").diff().fillna(0) < 0).sum())},
    {"id": "MF3", "name": "电流-电压正相关", "rule": "电流>50A时电压应>10V",
     "check": lambda df: int((pd.to_numeric(df["Secondary Weld Voltage"], errors="coerce").fillna(0)[pd.to_numeric(df["Primary Weld Current"], errors="coerce").fillna(0) > 50] < 10).sum())},
]

csvs = sorted(BATCH_DIR.glob("*.csv"))
results = []
total_pass = 0

for i, csv in enumerate(csvs):
    try:
        df = pd.read_csv(csv)
        checks = []

        for col, spec in SCHEMA.items():
            exists = col in df.columns
            if not exists:
                checks.append({"column": col, "check": "column_exists", "passed": False, "detail": "列缺失"})
                continue
            checks.append({"column": col, "check": "column_exists", "passed": True, "detail": ""})

            null_count = int(df[col].isnull().sum())
            checks.append({"column": col, "check": "not_null", "passed": null_count == 0,
                           "detail": f"{null_count}个空值" if null_count > 0 else ""})

            vals = pd.to_numeric(df[col], errors="coerce")
            lo, hi = spec["range"]
            oor = int(((vals < lo) | (vals > hi)).sum())
            checks.append({"column": col, "check": f"range({lo},{hi})", "passed": oor == 0,
                           "detail": f"{oor}个超范围" if oor > 0 else ""})

        for rule in MULTIFIELD_RULES:
            try:
                violations = rule["check"](df)
                checks.append({"column": rule["name"], "check": rule["rule"],
                               "passed": violations == 0,
                               "detail": f"{violations}个违规" if violations > 0 else ""})
            except Exception as e:
                checks.append({"column": rule["name"], "check": rule["rule"],
                               "passed": False, "detail": f"检查异常: {e}"})

        failed = [c for c in checks if not c["passed"]]
        passed = len(failed) == 0
        if passed:
            total_pass += 1

        results.append({
            "file": csv.name, "total_checks": len(checks),
            "passed_checks": len(checks) - len(failed),
            "failed_checks": len(failed),
            "passed": passed,
            "failures": failed,
        })
    except Exception as e:
        results.append({"file": csv.name, "error": str(e), "passed": False})

check_stats = {}
for r in results:
    for f in r.get("failures", []):
        key = f["check"]
        check_stats[key] = check_stats.get(key, 0) + 1

output = {
    "tool": "DataFrame Schema Validation (Pandera-style)",
    "timestamp": datetime.now().isoformat(),
    "dataset": "H4R Welding",
    "total_samples": len(csvs),
    "schema_definition": {
        "column_specs": {col: spec for col, spec in SCHEMA.items()},
        "multifield_rules": [{"id": r["id"], "rule": r["rule"]} for r in MULTIFIELD_RULES],
    },
    "summary": {
        "total": len(csvs), "passed": total_pass,
        "failed": len(csvs) - total_pass,
        "pass_rate": f"{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)",
    },
    "check_failure_stats": check_stats,
    "samples": results,
}

OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"Schema验证: 通过{total_pass}/{len(csvs)} ({total_pass/len(csvs)*100:.1f}%)")
print(f"失败统计: {check_stats}")
print(f"结果: {OUT}")
