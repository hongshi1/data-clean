"""test split上报告held-out诚实数字 (P0第三步: 测量乐观偏差).

test split (46条, 冻结) 只在此脚本运行, 每配置各跑一次:
  1. current-default: legacy默认阈值 nli_gate=0.70 / cascade_keep_confidence
     =None / llm_refute_gate=0.8 —— 与legacy全91自评同配置, 测它的真实
     held-out表现.
  2. dev-tuned: tools/calibrate_on_dev.py 在dev上选出的配置
     (data/gjb_438c/qa_frozen/dev_tuned_config_v1.json) —— 调参是否真泛化.
  3. 参照行 legacy: 全91QA的既有数字(0.7185/0.800, 直接从既有runs读取,
     不重跑) —— dev-on-test自评数.

乐观偏差 = legacy(全91) - test(同配置current-default):
  legacy在同一批91条(含这46条test)上自评, 差值即dev-on-test过拟合量.
数字如实报告 —— test显著低于legacy本身就是本任务的核心发现.

runs协议落盘result.json(切分明细+每实例判定, 便于复查).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    accuracy,
    confusion_dict,
    macro_f1,
    per_class_metrics,
)
from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_dev_test_split import (  # noqa: E402
    load_corpora,
    load_split,
)
from tools.calibrate_on_dev import run_with_llm_counting  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

MODEL_KEY = "egt_finetuned_v2"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
TUNED_CONFIG_PATH = BASE / "data/gjb_438c/qa_frozen/dev_tuned_config_v1.json"

CURRENT_DEFAULT = {"nli_gate": 0.70, "cascade_keep_confidence": None,
                   "llm_refute_gate": 0.8}
# legacy参照: 全91QA既有run(fixed_cascade行, macro-F1 0.7185 / refute F1
# 0.800, git ff0d4950, 与current-default同配置), 只读不重跑.
LEGACY_RUNS = ("eval_router_2b76c358_20261027_170640",
               "eval_cascade_1e92cdce_20261027_124941")


def load_tuned_config() -> dict:
    if not TUNED_CONFIG_PATH.exists():
        print(f"dev-tuned配置缺失: {TUNED_CONFIG_PATH} "
              f"(先跑 python tools/calibrate_on_dev.py)")
        sys.exit(1)
    return json.loads(TUNED_CONFIG_PATH.read_text(encoding="utf-8"))


def load_legacy_reference() -> dict:
    """Read the legacy all-91 numbers from existing runs (no rerun)."""
    for run_name in LEGACY_RUNS:
        path = RUNS_ROOT / run_name / "result.json"
        if not path.exists():
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        if "cost_quality_table" in result:
            for row in result["cost_quality_table"]:
                if row["config"] in ("fixed_cascade", "cascade"):
                    return {"run": run_name, "n": result.get("n"),
                            "macro_f1": row["macro_f1"],
                            "refute_f1": row.get("refute_f1"),
                            "refute_precision": row.get("refute_precision"),
                            "refute_recall": row.get("refute_recall"),
                            "llm_invocations": row.get("llm_invocations")}
        cascade = result.get("configs", {}).get("cascade")
        if cascade:
            return {"run": run_name, "n": result.get("n"),
                    "macro_f1": cascade["macro_f1"],
                    "refute_f1": cascade["per_class"]["refute"]["f1"],
                    "refute_precision":
                        cascade["per_class"]["refute"]["precision"],
                    "refute_recall":
                        cascade["per_class"]["refute"]["recall"],
                    "llm_invocations": None}
    raise FileNotFoundError(f"legacy参照runs不存在: {LEGACY_RUNS}")


def score(outcomes: dict[str, dict], rows: list[dict],
          silver: dict[str, str]) -> dict:
    confusion: Counter = Counter()
    for row in rows:
        iid = row["instance_id"]
        confusion[(outcomes[iid]["verdict"], silver[iid])] += 1
    return {
        "accuracy": accuracy(confusion, len(rows)),
        "macro_f1": macro_f1(confusion),
        "per_class": per_class_metrics(confusion),
        "confusion[predicted, silver]": confusion_dict(confusion),
    }


def build_module(params: dict, checkpoint: str) -> QAConsistencyModule:
    return QAConsistencyModule(
        use_experts=True, use_cascade=True,
        nli_model_path=checkpoint,
        nli_gate=params["nli_gate"],
        cascade_keep_confidence=params["cascade_keep_confidence"],
        llm_refute_gate=params["llm_refute_gate"])


def per_instance_records(outcomes: dict[str, dict], split: dict,
                         silver: dict[str, str]) -> list[dict]:
    return [{
        "instance_id": iid,
        "topic": split["cluster_map"][iid],
        "silver": silver[iid],
        "predicted": outcomes[iid]["verdict"],
        "claim_methods": outcomes[iid]["claim_methods"],
        "diagnostics": outcomes[iid]["diagnostics"],
    } for iid in split["test"]]


def main() -> None:
    split = load_split()
    rows, silver = load_corpora()
    by_id = {row["instance_id"]: row for row in rows}
    test_rows = [by_id[iid] for iid in split["test"]]
    checkpoint = MODELS[MODEL_KEY]["dir"]
    if not (Path(checkpoint) / "config.json").exists():
        print(f"checkpoint不存在: {checkpoint}")
        sys.exit(1)
    tuned = load_tuned_config()
    legacy = load_legacy_reference()
    tuned_params = {"nli_gate": tuned["nli_gate"],
                    "cascade_keep_confidence": tuned["cascade_keep_confidence"],
                    "llm_refute_gate": tuned["llm_refute_gate"]}
    print(f"test: {len(test_rows)} rows, silver "
          f"{split['silver_distribution']['test']}")
    print(f"current-default: {CURRENT_DEFAULT}")
    print(f"dev-tuned: {tuned_params} (dev macro_f1 {tuned['dev_macro_f1']})")
    print(f"legacy reference: {legacy}")

    configs: dict[str, dict] = {
        "current_default": CURRENT_DEFAULT,
        "dev_tuned": tuned_params,
    }
    results: dict[str, dict] = {}
    per_instance: dict[str, list[dict]] = {}
    for name, params in configs.items():
        module = build_module(params, checkpoint)
        outcomes, llm_stats = run_with_llm_counting(module, test_rows)
        results[name] = {**score(outcomes, test_rows, silver),
                         **llm_stats, "params": params}
        per_instance[name] = per_instance_records(outcomes, split, silver)
        print(f"{name}: macro_f1={results[name]['macro_f1']} "
              f"refute_f1={results[name]['per_class']['refute']['f1']} "
              f"llm_inv={results[name]['llm_invocations']} "
              f"api={results[name]['llm_api_calls']}")

    current = results["current_default"]
    dev_tuned = results["dev_tuned"]
    bias_macro = round(legacy["macro_f1"] - current["macro_f1"], 4)
    bias_share = round(bias_macro / legacy["macro_f1"] * 100, 1)
    optimistic_bias = {
        "macro_f1": bias_macro,
        "refute_f1": round(legacy["refute_f1"]
                           - current["per_class"]["refute"]["f1"], 4),
        "definition": "legacy(全91自评) - test(held-out 46, 同配置"
                      "current-default) = dev-on-test过拟合量(乐观偏差)",
        "interpretation": (
            f"legacy {legacy['macro_f1']} 中, {bias_macro} "
            f"({bias_share}%) 来自在同批数据上调参的自评增益"
            "(held-out不可兑现)"),
    }
    generalization = {
        "dev_tuned_minus_current_default_on_test": {
            "macro_f1": round(dev_tuned["macro_f1"]
                              - current["macro_f1"], 4),
            "refute_f1": round(
                dev_tuned["per_class"]["refute"]["f1"]
                - current["per_class"]["refute"]["f1"], 4),
        },
        "note": "正值=dev调参在held-out上真泛化; 负值=dev最优配置过拟合dev",
    }

    run = open_run("eval_test_honest", {
        "split": "data/gjb_438c/qa_frozen/dev_test_split_v1.json",
        "test_n": len(test_rows),
        "model_key": MODEL_KEY,
        "checkpoint": checkpoint,
        "configs": {name: cfg["params"] for name, cfg in results.items()},
        "legacy_run": legacy["run"],
        "rule": "test split每配置只跑一次; 扫参只在dev",
    })
    run.save_result({
        "test_n": len(test_rows),
        "silver_distribution_test": split["silver_distribution"]["test"],
        "dev_split": split["dev"],
        "test_split": split["test"],
        "cluster_assignment": split["cluster_assignment"],
        "configs": results,
        "per_instance": per_instance,
        "legacy_reference": legacy,
        "optimistic_bias": optimistic_bias,
        "generalization": generalization,
    })

    table = []
    for name in ("current_default", "dev_tuned"):
        r = results[name]
        table.append({
            "config": name,
            "macro_f1": r["macro_f1"],
            "refute_f1": r["per_class"]["refute"]["f1"],
            "support_recall": r["per_class"]["support"]["recall"],
            "nie_f1": r["per_class"]["not_in_evidence"]["f1"],
            "llm_invocations": r["llm_invocations"],
            "llm_api_calls": r["llm_api_calls"],
        })
    table.append({
        "config": f"legacy_all91({legacy['run']})",
        "macro_f1": legacy["macro_f1"],
        "refute_f1": legacy["refute_f1"],
        "support_recall": None,
        "nie_f1": None,
        "llm_invocations": legacy["llm_invocations"],
        "llm_api_calls": 0,
    })
    print(json.dumps({
        "test_n": len(test_rows),
        "table": table,
        "optimistic_bias": optimistic_bias,
        "generalization": generalization,
        "run": str(run.path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
