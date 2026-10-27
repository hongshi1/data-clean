"""跨文档泛化评测: 06号构造性sound评测集 × (deterministic / cascade)两配置.

P1问题: 91QA(scene1_qa_frozen_v1)全部来自04号文档, 任何配置的指标都
只衡量单文档拟合——泛化能力零验证. 本脚本在06号30条构造性sound QA
(crossdoc06_evalset_v1, 标签由label_proof逐条背书)上重跑同配置:

  deterministic  QAConsistencyModule(use_experts=True)                (0 LLM)
  cascade        use_experts+use_cascade(=NLI残差+LLM升级), gate=0.70
                 (与tools/eval_cascade.py的cascade配置完全一致; LLM走
                 llm_json(cache=True)缓存接口, 可复现)

报告: 三态macro-F1、各类P/R/F1、混淆矩阵、与04号同配置数字的直接对比
(泛化落差)、检出通道归因(哪些专家在06号上工作/失效, 按gold标签与
混淆单元聚合claim method)、失配实例清单(按family/operator定位失效面).

LLM调用计数: 包装llm_json与_store(与eval_cascade同法)——invocations为
进程内调用数(成本口径), api_calls为真实缓存未命中数.

用法: python tools/eval_crossdoc.py [--evalset PATH --reference-run NAME]
产出: data/gjb_438c/runs/eval_crossdoc_<hash>_<ts>/{result.json, report.md}
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE / "tools"), str(BASE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import algorithms.common.llm_client as llm_client  # noqa: E402
from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from run_utils import open_run  # noqa: E402

DEFAULT_EVALSET = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
LABELS = ("support", "refute", "not_in_evidence")
NLI_GATE = 0.70
MODEL_KEY = "egt_finetuned_v2"
#: 04号参照: 同日同管线的eval_cascade运行(91QA silver标签)
CONFIG_NAME_MAP = {"deterministic": "baseline", "cascade": "cascade"}


# ── 装载 ───────────────────────────────────────────────────


def load_evalset(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for key in ("instance_id", "question", "answer",
                        "context_freeze_id", "evidence", "sound_label",
                        "label_proof"):
                if not row.get(key):
                    raise ValueError(f"{path.name}: 行缺字段 {key}")
            if row["sound_label"] not in LABELS:
                raise ValueError(
                    f"{row['instance_id']}: 非法sound_label "
                    f"{row['sound_label']}")
            if not row["evidence"]:
                raise ValueError(f"{row['instance_id']}: evidence为空")
            rows.append(row)
    ids = [r["instance_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"instance_id重复: {path}")
    return rows


# ── 运行与LLM计数(与eval_cascade.py同法) ──────────────────────


def run_with_llm_counting(module: QAConsistencyModule, rows: Sequence[dict],
                          ) -> tuple[dict[str, dict], dict]:
    call_stats = {"invocations": 0, "api_calls": 0}
    original_llm_json = llm_client.llm_json
    original_store = llm_client._store

    def counting_llm_json(prompt, *args, **kwargs):
        call_stats["invocations"] += 1
        return original_llm_json(prompt, *args, **kwargs)

    def counting_store(ck, content, model):
        call_stats["api_calls"] += 1
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
                "status": result.status,
                "diagnostics": list(result.diagnostics),
                "claims": [{
                    "claim_id": claim.claim_id,
                    "claim_text": claim.claim_text,
                    "verdict": claim.verdict,
                    "method": claim.method,
                    "confidence": claim.confidence,
                    "evidence_refs": list(claim.evidence_refs),
                    "rationale": claim.rationale[:200],
                } for claim in result.claim_results],
            }
    finally:
        llm_client.llm_json = original_llm_json
        llm_client._store = original_store
    stats = {
        "invocations": call_stats["invocations"],
        "api_calls": call_stats["api_calls"],
        "cache_hits": call_stats["invocations"] - call_stats["api_calls"],
    }
    return outcomes, stats


# ── 指标(三态macro-F1等) ──────────────────────────────────


def class_metrics(confusion: Counter) -> dict[str, dict]:
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


# ── 通道归因 ───────────────────────────────────────────────


def channel_attribution(outcomes: dict[str, dict],
                        rows: Sequence[dict]) -> dict[str, Any]:
    """按gold标签/混淆单元聚合claim method——哪些专家在06号上工作/失效."""
    methods_by_gold: dict[str, Counter] = {label: Counter() for label in LABELS}
    methods_by_cell: dict[str, Counter] = {}
    decisive_by_gold: dict[str, Counter] = {label: Counter() for label in LABELS}
    misclassified: list[dict[str, Any]] = []
    for row in rows:
        gold = str(row["sound_label"])
        outcome = outcomes[row["instance_id"]]
        pred = outcome["verdict"]
        methods = sorted({claim["method"] for claim in outcome["claims"]})
        decisive = sorted({claim["method"] for claim in outcome["claims"]
                           if claim["verdict"] == pred
                           and claim["verdict"] in ("support", "refute")})
        for method in methods:
            methods_by_gold[gold][method] += 1
        for method in decisive:
            decisive_by_gold[gold][method] += 1
        cell = f"{pred}|{gold}"
        for method in methods:
            methods_by_cell.setdefault(cell, Counter())[method] += 1
        if pred != gold:
            misclassified.append({
                "instance_id": row["instance_id"],
                "family": row.get("family", ""),
                "operator": row.get("operator", ""),
                "gold": gold, "pred": pred,
                "methods": methods,
                "decisive": decisive,
                "claim_summary": [
                    f"{c['verdict']}:{c['method']}:{c['claim_text'][:40]}"
                    for c in outcome["claims"][:6]],
            })
    return {
        "methods_by_gold": {g: dict(c) for g, c in methods_by_gold.items()},
        "decisive_by_gold": {g: dict(c) for g, c in decisive_by_gold.items()},
        "methods_by_confusion_cell": {
            cell: dict(c) for cell, c in methods_by_cell.items()},
        "misclassified": misclassified,
    }


def score_config(outcomes: dict[str, dict], rows: Sequence[dict]) -> dict:
    confusion: Counter = Counter()
    for row in rows:
        confusion[(outcomes[row["instance_id"]]["verdict"],
                   str(row["sound_label"]))] += 1
    return {
        "n": len(rows),
        "accuracy": accuracy(confusion, len(rows)),
        "macro_f1": macro_f1(confusion),
        "per_class": class_metrics(confusion),
        "confusion[predicted, gold]": confusion_dict(confusion),
    }


# ── 04号参照与泛化落差 ────────────────────────────────────


def doc04_reference(reference_run: str | None = None) -> dict[str, Any] | None:
    """读取04号(91QA silver)同配置eval_cascade运行作为泛化对比基线."""
    if reference_run:
        paths = [RUNS_ROOT / reference_run / "result.json"]
    else:
        paths = sorted(RUNS_ROOT.glob("eval_cascade_*/result.json"),
                       key=lambda p: p.stat().st_mtime)
        paths = paths[-1:] if paths else []
    for path in paths:
        if not path.exists():
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        configs = result.get("configs", {})
        picked: dict[str, Any] = {}
        for mine, theirs in CONFIG_NAME_MAP.items():
            if theirs in configs:
                picked[mine] = {
                    "macro_f1": configs[theirs]["macro_f1"],
                    "accuracy": configs[theirs]["accuracy"],
                    "per_class": configs[theirs]["per_class"],
                }
        if picked:
            return {"run": path.parent.name, "label_type":
                    result.get("label_type", "glm53_silver_not_gold"),
                    "n": result.get("n"), "configs": picked}
    return None


def generalization_gap(scores: dict[str, dict],
                       reference: dict[str, Any] | None) -> dict[str, Any]:
    """06号−04号同配置直接对比(泛化落差; 注意04为silver标签口径)."""
    if reference is None:
        return {"available": False,
                "reason": "未找到eval_cascade参照运行"}
    gap: dict[str, Any] = {"available": True, "doc04_run":
                           reference["run"]}
    for config, score in scores.items():
        ref = reference["configs"].get(config)
        if ref is None:
            continue
        per_class_delta = {
            cls: round(score["per_class"][cls]["f1"]
                       - ref["per_class"][cls]["f1"], 4)
            for cls in LABELS}
        gap[config] = {
            "doc04_macro_f1": ref["macro_f1"],
            "doc06_macro_f1": score["macro_f1"],
            "delta_macro_f1": round(score["macro_f1"] - ref["macro_f1"], 4),
            "delta_per_class_f1": per_class_delta,
        }
    return gap


# ── 报告渲染 ───────────────────────────────────────────────


def render_markdown_report(result: dict) -> str:
    lines = [
        "# 跨文档泛化评测 (06号 × 构造性sound标签)", "",
        f"- evalset: `{result['evalset']['path']}` "
        f"({result['evalset']['n']}行, S/R/N各10)",
        f"- label: **{result['label_type']}** (构造性sound, label_proof背书)",
        f"- reference: {(result.get('doc04_reference') or {}).get('run', '无')}",
        "",
    ]
    for config, entry in result["configs"].items():
        m = entry["metrics"]
        lines += [f"## {config}", "",
                  f"- n={m['n']} accuracy={m['accuracy']} "
                  f"macro_f1={m['macro_f1']} "
                  f"llm_invocations={entry['llm_stats']['invocations']} "
                  f"(api_calls={entry['llm_stats']['api_calls']})",
                  "",
                  "| class | precision | recall | f1 |",
                  "|---|---|---|---|"]
        for cls in LABELS:
            pc = m["per_class"][cls]
            lines.append(f"| {cls} | {pc['precision']} | {pc['recall']} "
                         f"| {pc['f1']} |")
        lines += ["", "混淆矩阵 (pred|gold):",
                  f"`{json.dumps(m['confusion[predicted, gold]'], ensure_ascii=False)}`",
                  ""]
    gap = result.get("generalization_gap", {})
    if gap.get("available"):
        lines += ["## 泛化落差 (06号 − 04号同配置)", "",
                  "| config | 04 macro-F1 | 06 macro-F1 | Δ | "
                  "Δsupport-F1 | Δrefute-F1 | ΔNIE-F1 |",
                  "|---|---|---|---|---|---|---|"]
        for config, entry in gap.items():
            if not isinstance(entry, dict) or "delta_macro_f1" not in entry:
                continue
            d = entry["delta_per_class_f1"]
            lines.append(
                f"| {config} | {entry['doc04_macro_f1']} "
                f"| {entry['doc06_macro_f1']} | {entry['delta_macro_f1']} "
                f"| {d['support']} | {d['refute']} "
                f"| {d['not_in_evidence']} |")
        lines.append("")
    attribution = result["configs"].get("deterministic", {}).get(
        "attribution", {})
    if attribution:
        lines += ["## 检出通道归因 (deterministic, 按gold标签)", "",
                  "| gold | 触发的claim methods |",
                  "|---|---|"]
        for gold in LABELS:
            methods = attribution.get("methods_by_gold", {}).get(gold, {})
            lines.append(f"| {gold} | `{json.dumps(methods, ensure_ascii=False)}` |")
        lines += ["", "误判实例 (gold→pred):"]
        for item in attribution.get("misclassified", []):
            lines.append(
                f"- {item['instance_id']} [{item['family']}/"
                f"{item['operator']}] {item['gold']}→{item['pred']} "
                f"methods={item['methods']}")
        lines.append("")
    return "\n".join(lines)


# ── 主流程 ─────────────────────────────────────────────────


def build_modules(configs: Sequence[str]) -> dict[str, QAConsistencyModule]:
    modules: dict[str, QAConsistencyModule] = {}
    if "deterministic" in configs:
        modules["deterministic"] = QAConsistencyModule(use_experts=True)
    if "cascade" in configs:
        checkpoint = MODELS[MODEL_KEY]["dir"]
        if not (Path(checkpoint) / "config.json").exists():
            raise FileNotFoundError(
                f"NLI checkpoint不存在: {checkpoint} "
                f"(先跑 python tools/train_residual_nli.py)")
        modules["cascade"] = QAConsistencyModule(
            use_experts=True, use_nli_residual=True, use_cascade=True,
            nli_model_path=checkpoint, nli_gate=NLI_GATE)
    return modules


def run_evaluation(
        evalset_path: Path = DEFAULT_EVALSET,
        out_root: Path | None = None,
        configs: Sequence[str] = ("deterministic", "cascade"),
        reference_run: str | None = None,
        script_name: str = "eval_crossdoc",
) -> tuple[dict[str, Any], Path]:
    rows = load_evalset(Path(evalset_path))
    modules = build_modules(configs)
    results: dict[str, dict[str, Any]] = {}
    for name, module in modules.items():
        outcomes, llm_stats = run_with_llm_counting(module, rows)
        results[name] = {
            "metrics": score_config(outcomes, rows),
            "llm_stats": llm_stats,
            "attribution": channel_attribution(outcomes, rows),
        }
    reference = doc04_reference(reference_run)
    result = {
        "benchmark": "crossdoc06_generalization",
        "evalset": {"path": str(Path(evalset_path)),
                    "n": len(rows),
                    "label_distribution": dict(
                        Counter(r["sound_label"] for r in rows)),
                    "family_distribution": dict(
                        Counter(r.get("family", "") for r in rows))},
        "label_type": "constructive_sound (label_proof; no LLM silver)",
        "configs": results,
        "doc04_reference": reference,
        "generalization_gap": generalization_gap(
            {name: entry["metrics"] for name, entry in results.items()},
            reference),
        "nli_gate": NLI_GATE,
        "model_key": MODEL_KEY,
    }
    run = open_run(script_name, {
        "evalset": str(Path(evalset_path).relative_to(BASE))
        if Path(evalset_path).is_relative_to(BASE) else str(evalset_path),
        "n": len(rows),
        "configs": list(modules),
        "model_key": MODEL_KEY,
        "nli_gate": NLI_GATE,
        "reference_run": reference["run"] if reference else None,
        "llm": "glm-json-cache",
    }, root=out_root)
    run.save_result(result)
    run.write_text("report.md", render_markdown_report(result))
    run.log(event="eval_done", n=len(rows),
            macro_f1={k: v["metrics"]["macro_f1"]
                      for k, v in results.items()})
    return result, run.path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evalset", type=Path, default=DEFAULT_EVALSET)
    parser.add_argument("--reference-run", default=None,
                        help="04号eval_cascade运行目录名(默认取最新)")
    parser.add_argument("--configs", nargs="+",
                        default=["deterministic", "cascade"],
                        choices=["deterministic", "cascade"])
    args = parser.parse_args()
    result, run_path = run_evaluation(
        evalset_path=args.evalset, configs=args.configs,
        reference_run=args.reference_run)
    print(f"run: {run_path}")
    summary = {
        "n": result["evalset"]["n"],
        "configs": {name: {
            "macro_f1": entry["metrics"]["macro_f1"],
            "accuracy": entry["metrics"]["accuracy"],
            "per_class": entry["metrics"]["per_class"],
            "confusion": entry["metrics"]["confusion[predicted, gold]"],
            "llm_stats": entry["llm_stats"],
        } for name, entry in result["configs"].items()},
        "generalization_gap": result["generalization_gap"],
        "misclassified": {
            name: [f"{m['instance_id']}({m['gold']}->{m['pred']})"
                   for m in entry["attribution"]["misclassified"]]
            for name, entry in result["configs"].items()},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
