"""在dev split上网格重校准QAConsistencyModule可调参数 (P0第二步).

背景: legacy阈值(nli_gate=0.70 / cascade_keep_confidence=None /
llm refute confidence gate=0.8)全部是在91条QA上看着调的(dev-on-test).
本脚本只在冻结dev split(45条, tools/build_dev_test_split.py产出)上扫参:

  nli_gate             ∈ [0.5, 0.6, 0.7, 0.8, 0.9]   (qa_module参数)
  cascade_keep_confidence ∈ [None, 0.90, 0.95]        (qa_module参数)
  llm_refute_gate      ∈ [0.6, 0.7, 0.8, 0.9]        (llm_residual门控,
                          已参数化为QAConsistencyModule(llm_refute_gate=...),
                          默认0.8向后兼容)

固定项(文档声明frozen, 不扫): 序列专家0.28 / BGE 0.60 / 实体0.75等模块
内部常量. LLM调用走llm_json(cache=True); refute gate是LLM返回后的后置
过滤(不改prompt→不产生新调用), nli_gate/keep_confidence会改变升级集合
→新prompt产生新缓存调用(预算: 每配置只跑dev 45条).

选优: dev macro-F1最大; 并列选LLM invocations少者; 再并列选网格序靠前者.
产出: runs协议result.json(全部60行+最优配置+dev每实例判定) +
冻结指针 data/gjb_438c/qa_frozen/dev_tuned_config_v1.json (供
tools/eval_test_honest.py读取).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import algorithms.common.llm_client as llm_client  # noqa: E402
from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.build_dev_test_split import (  # noqa: E402
    load_corpora,
    load_split,
)
from tools.run_utils import open_run  # noqa: E402

LABELS = ("support", "refute", "not_in_evidence")
MODEL_KEY = "egt_finetuned_v2"
TUNED_CONFIG_PATH = BASE / "data/gjb_438c/qa_frozen/dev_tuned_config_v1.json"

NLI_GATES = (0.5, 0.6, 0.7, 0.8, 0.9)
KEEP_CONFIDENCES = (None, 0.90, 0.95)
LLM_REFUTE_GATES = (0.6, 0.7, 0.8, 0.9)


def class_metrics(confusion: Counter) -> dict[str, dict[str, float]]:
    out = {}
    for label in LABELS:
        tp = confusion[(label, label)]
        fp = sum(confusion[(label, gold)] for gold in LABELS if gold != label)
        fn = sum(confusion[(pred, label)] for pred in LABELS if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)
        out[label] = {"precision": round(precision, 4),
                      "recall": round(recall, 4), "f1": round(f1, 4)}
    return out


def macro_f1(confusion: Counter) -> float:
    return round(sum(m["f1"] for m in class_metrics(confusion).values())
                 / len(LABELS), 4)


def accuracy(confusion: Counter, n: int) -> float:
    correct = sum(confusion[(p, g)] for p in LABELS for g in LABELS if p == g)
    return round(correct / n, 4)


def confusion_dict(confusion: Counter) -> dict[str, int]:
    return {f"{p}|{g}": confusion[(p, g)]
            for p in LABELS for g in LABELS if confusion[(p, g)]}


def run_with_llm_counting(module: QAConsistencyModule, rows: list[dict]
                           ) -> tuple[dict[str, dict], dict]:
    """Run verify() per row while counting llm_json invocations / API calls.

    Same instrumentation as tools/eval_cascade.py: ``stores`` counts real
    per-process cache-missing API calls; on a warm cache stores=0 while
    invocations stays the per-instance call count.
    """
    call_stats = {"invocations": 0, "stores": 0}
    original_llm_json = llm_client.llm_json
    original_store = llm_client._store

    def counting_llm_json(prompt, *args, **kwargs):
        call_stats["invocations"] += 1
        return original_llm_json(prompt, *args, **kwargs)

    def counting_store(ck, content, model):
        call_stats["stores"] += 1
        return original_store(ck, content, model)

    llm_client.llm_json = counting_llm_json
    llm_client._store = counting_store
    outcomes: dict[str, dict] = {}
    try:
        for row in rows:
            request = request_from_dict(row)
            result = module.verify(request)
            outcomes[request.instance_id] = {
                "verdict": result.verdict,
                "diagnostics": list(result.diagnostics),
                "claim_methods": [c.method for c in result.claim_results],
            }
    finally:
        llm_client.llm_json = original_llm_json
        llm_client._store = original_store
    stats = {"llm_invocations": call_stats["invocations"],
             "llm_api_calls": call_stats["stores"],
             "llm_cache_hits": (call_stats["invocations"]
                                - call_stats["stores"])}
    return outcomes, stats


def score(outcomes: dict[str, dict], rows: list[dict],
          silver: dict[str, str]) -> dict:
    confusion: Counter = Counter()
    for row in rows:
        iid = row["instance_id"]
        confusion[(outcomes[iid]["verdict"], silver[iid])] += 1
    return {
        "accuracy": accuracy(confusion, len(rows)),
        "macro_f1": macro_f1(confusion),
        "per_class": class_metrics(confusion),
        "confusion[predicted, silver]": confusion_dict(confusion),
    }


def main() -> None:
    split = load_split()
    rows, silver = load_corpora()
    by_id = {row["instance_id"]: row for row in rows}
    dev_rows = [by_id[iid] for iid in split["dev"]]
    checkpoint = MODELS[MODEL_KEY]["dir"]
    if not (Path(checkpoint) / "config.json").exists():
        print(f"checkpoint不存在: {checkpoint}")
        sys.exit(1)
    print(f"dev: {len(dev_rows)} rows, silver "
          f"{split['silver_distribution']['dev']}, checkpoint {checkpoint}")

    grid_rows: list[dict] = []
    best_outcomes: dict[str, dict] | None = None
    for nli_gate in NLI_GATES:
        for keep in KEEP_CONFIDENCES:
            for llm_gate in LLM_REFUTE_GATES:
                module = QAConsistencyModule(
                    use_experts=True, use_cascade=True,
                    nli_model_path=checkpoint, nli_gate=nli_gate,
                    cascade_keep_confidence=keep,
                    llm_refute_gate=llm_gate)
                outcomes, llm_stats = run_with_llm_counting(
                    module, dev_rows)
                row = {
                    "nli_gate": nli_gate,
                    "cascade_keep_confidence": keep,
                    "llm_refute_gate": llm_gate,
                    **score(outcomes, dev_rows, silver),
                    **llm_stats,
                }
                grid_rows.append(row)
                print(f"gate={nli_gate} keep={keep} llm_gate={llm_gate} "
                      f"macro_f1={row['macro_f1']} "
                      f"refute_f1={row['per_class']['refute']['f1']} "
                      f"llm_inv={row['llm_invocations']} "
                      f"api={row['llm_api_calls']}")
                # selection: max macro_f1, tie -> fewer llm invocations,
                # tie -> grid order (first wins, strict >)
                if (best_outcomes is None
                        or row["macro_f1"] > best_outcomes["row"]["macro_f1"]
                        or (row["macro_f1"]
                            == best_outcomes["row"]["macro_f1"]
                            and row["llm_invocations"]
                            < best_outcomes["row"]["llm_invocations"])):
                    best_outcomes = {
                        "row": row,
                        "outcomes": outcomes,
                    }
                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass

    best = best_outcomes["row"]
    best_row_index = grid_rows.index(best)
    per_instance = [{
        "instance_id": iid,
        "silver": silver[iid],
        "predicted": best_outcomes["outcomes"][iid]["verdict"],
        "claim_methods": best_outcomes["outcomes"][iid]["claim_methods"],
        "topic": split["cluster_map"][iid],
    } for iid in split["dev"]]

    tuned_config = {
        "version": "dev_tuned_config_v1",
        "selected_on": "dev split (45 QA, dev_test_split_v1)",
        "selection_rule": "max dev macro-F1; tie -> fewer llm invocations; "
                          "tie -> grid order",
        "nli_gate": best["nli_gate"],
        "cascade_keep_confidence": best["cascade_keep_confidence"],
        "llm_refute_gate": best["llm_refute_gate"],
        "dev_macro_f1": best["macro_f1"],
        "dev_refute_f1": best["per_class"]["refute"]["f1"],
        "dev_llm_invocations": best["llm_invocations"],
        "calibrate_run": "",
    }

    run = open_run("calibrate_on_dev", {
        "split": "data/gjb_438c/qa_frozen/dev_test_split_v1.json",
        "dev_n": len(dev_rows),
        "model_key": MODEL_KEY,
        "checkpoint": checkpoint,
        "grid": {"nli_gate": list(NLI_GATES),
                 "cascade_keep_confidence": [str(k) for k in KEEP_CONFIDENCES],
                 "llm_refute_gate": list(LLM_REFUTE_GATES)},
        "frozen_note": "序列专家0.28/BGE 0.60/实体0.75等模块内部常量"
                       "不在扫参范围(frozen)",
    })
    tuned_config["calibrate_run"] = run.path.name
    run.save_result({
        "grid_rows": grid_rows,
        "best": best,
        "best_row_index": best_row_index,
        "tuned_config": tuned_config,
        "per_instance_best": per_instance,
    })
    TUNED_CONFIG_PATH.write_text(
        json.dumps(tuned_config, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nbest config: nli_gate={best['nli_gate']} "
          f"keep={best['cascade_keep_confidence']} "
          f"llm_refute_gate={best['llm_refute_gate']} "
          f"dev macro_f1={best['macro_f1']} "
          f"llm_invocations={best['llm_invocations']}")
    print(f"tuned config frozen: {TUNED_CONFIG_PATH}")
    print(f"run: {run.path}")


if __name__ == "__main__":
    main()
