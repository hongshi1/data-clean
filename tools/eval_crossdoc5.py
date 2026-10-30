"""跨文档泛化评测(×5): 05/06/07/08/10合并集150条 × 4配置.

P1v2: 06号单文档泛化评测(crossdoc06_evalset_v1, 30条)扩充为5文档合并集
(crossdoc5_evalset_v1, 150条, 每文档30条构造性sound标签S/R/N各10),
形成"自建-跨文档×5"数据集列. 本脚本在合并集上跑:

  b3_deterministic  QAConsistencyModule(use_experts=True)            (0 LLM)
  l2_egt_nli        use_experts+use_nli_residual(egt_finetuned_v2),
                    nli_gate=0.70                                    (0 LLM)
  ours_cascade      use_experts+use_cascade(=NLI残差+LLM升级),
                    gate=0.70 (与eval_cascade/eval_crossdoc完全一致;
                    LLM走llm_json(cache=True)缓存接口, 可复现)
  mdeberta_zeroshot 基座mDeBERTa零样本三态判定(algorithms/consistency/
                    nli_local.NliLocal零样本推理路径): premise与L2共用
                    nli_training.residual_premise(数据准备共用, 模型
                    未微调), argmax直接映射E/S C/R N/NIE (0 LLM)
  bge_centroid      BGE三元中心法(public_baselines.py已有接口复用):
                    fit池=OCNLI train 2000+CMNLI train 3000(seed=42,
                    与评测列零泄漏), test对premise=evidence_premise
                    (与tools/eval_public_matrix.py自建列同口径) (0 LLM)

报告: 分文档×分配置macro-F1矩阵+总体("自建-跨文档×5"列的数字),
06号子集与旧eval_crossdoc运行(06号单文档)的同配置复现对比, 各配置
三态P/R/F1与混淆矩阵, 误判实例(按family/operator定位失效面).

LLM调用计数: 包装llm_json与_store(与eval_cascade/eval_crossdoc同法)
——invocations为进程内调用数(成本口径), api_calls为真实缓存未命中数.

用法: python tools/eval_crossdoc5.py [--evalset PATH --configs ...]
产出: data/gjb_438c/runs/eval_crossdoc5_<hash>_<ts>/{result.json, report.md}
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

from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.egt_synthesis import evidence_from_dict  # noqa: E402
from algorithms.consistency.nli_local import MODELS, NliLocal  # noqa: E402
from algorithms.consistency.nli_residual import NLI_TO_VERDICT  # noqa: E402
from algorithms.consistency.nli_training import (  # noqa: E402
    PREMISE_BUDGET,
    residual_premise,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_crossdoc import (  # noqa: E402
    LABELS,
    NLI_GATE,
    channel_attribution,
    class_metrics,
    confusion_dict,
    load_evalset,
    run_with_llm_counting,
)
from run_utils import open_run  # noqa: E402

DEFAULT_EVALSET = BASE / "data/gjb_438c/qa_frozen/crossdoc5_evalset_v1.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
MODEL_KEY = "egt_finetuned_v2"
DOC_NUMBERS = ("05", "06", "07", "08", "10")
#: 旧eval_crossdoc运行(06号单文档)的同配置名映射(06号应复现)
OLD_RUN_CONFIG_MAP = {
    "b3_deterministic": "deterministic",
    "l2_egt_nli": None,          # 旧运行无L2单独配置
    "ours_cascade": "cascade",
    "mdeberta_zeroshot": None,
    "bge_centroid": None,
}
#: BGE中心法fit池规模(与tools/eval_public_matrix.py同协议, seed=42)
BGE_FIT_OCNLI_N = 2000
BGE_FIT_CMNLI_N = 3000


# ── 指标 ───────────────────────────────────────────────────


def macro_f1(confusion: Counter) -> float:
    return round(sum(m["f1"] for m in class_metrics(confusion).values())
                 / len(LABELS), 4)


def accuracy(confusion: Counter, n: int) -> float:
    correct = sum(confusion[(p, g)] for p in LABELS for g in LABELS if p == g)
    return round(correct / n, 4) if n else 0.0


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


def doc_of(row: dict) -> str:
    """行所属文档号(instance_id前缀C05QA→05)."""
    return str(row["instance_id"])[1:3]


def per_doc_scores(outcomes: dict[str, dict],
                   rows: Sequence[dict]) -> dict[str, dict]:
    by_doc: dict[str, list[dict]] = {d: [] for d in DOC_NUMBERS}
    for row in rows:
        by_doc.setdefault(doc_of(row), []).append(row)
    return {doc: score_config(outcomes, doc_rows)
            for doc, doc_rows in sorted(by_doc.items()) if doc_rows}


# ── mDeBERTa零样本基线 ─────────────────────────────────────


def run_mdeberta_zeroshot(
        rows: Sequence[dict]) -> tuple[dict[str, dict], dict[str, Any]]:
    """基座mDeBERTa零样本: premise=L2同款构造, argmax三态映射.

    premise构造与L2残差通道共用(nli_training.residual_premise)——数据
    准备不属于模型贡献, 模型本身零样本(未微调); 空premise→neutral→NIE.
    """
    client = NliLocal("mdeberta")
    mode = client.ensure()
    pairs: list[tuple[str, str]] = []
    order: list[str] = []
    for row in rows:
        statements = linearize_context(tuple(
            evidence_from_dict(ev) for ev in row["evidence"]))
        premise, _picks = residual_premise(
            row["answer"], row["question"], statements, PREMISE_BUDGET)
        pairs.append((premise, str(row["answer"])))
        order.append(str(row["instance_id"]))
    if mode == "unavailable":
        raise RuntimeError(
            f"mDeBERTa基座不可用: {client.last_error} "
            f"(models/nli/{MODELS['mdeberta']['dir']})")
    predictions = client.predict(pairs)
    outcomes: dict[str, dict] = {}
    for iid, pred in zip(order, predictions):
        verdict = NLI_TO_VERDICT.get(str(pred["label"]), "not_in_evidence")
        outcomes[iid] = {
            "verdict": verdict,
            "status": "ok",
            "diagnostics": [f"mdeberta_zeroshot:{pred['label']}"],
            "claims": [],
        }
    stats = {
        "model": MODELS["mdeberta"]["display"],
        "mode": mode,
        "n_pairs": client.stats["n_pairs"],
        "n_batches": client.stats["n_batches"],
        "infer_ms": client.stats["infer_ms"],
        "llm_stats": {"invocations": 0, "api_calls": 0, "cache_hits": 0},
    }
    return outcomes, stats


# ── BGE三元中心法(public_baselines接口复用) ──────────────────


def run_bge_centroid(
        rows: Sequence[dict],
        fit_pool: Sequence[dict] | None = None,
) -> tuple[dict[str, dict], dict[str, Any]]:
    """BGE三元中心法: fit池=公开NLI train(零泄漏), test=自建pair直推.

    复用algorithms/consistency/public_baselines.py接口与
    tools/eval_public_matrix.py的fit协议(OCNLI train 2000 + CMNLI
    train 3000, subsample seed=42); test对premise=evidence_premise
    (冻结证据build_premise), hypothesis=answer——与公开矩阵自建列
    同口径, 06号子集可与eval_public_matrix的crossdoc06列直接对比.
    fit_pool参数供小fixture冒烟测试注入合成池.
    """
    from algorithms.common.bge_local import BgeLocal
    from algorithms.consistency import public_baselines as pb
    from public_nli_bench import evidence_premise

    bge = BgeLocal()
    if bge.ensure() == "unavailable":
        raise RuntimeError(f"BGE不可用: {bge.last_error}")
    if fit_pool is None:
        from public_nli_bench import (
            SEED as bench_seed,
            cmnli_test_keys,
            load_cmnli_train,
            load_ocnli_train,
            subsample,
        )
        fit_pool = (
            subsample(load_ocnli_train(), BGE_FIT_OCNLI_N, bench_seed)
            + subsample(load_cmnli_train(exclude_keys=cmnli_test_keys()),
                        BGE_FIT_CMNLI_N, bench_seed))
    else:
        bench_seed = 42
    centroids = pb.bge_fit_from_pairs(bge, fit_pool)
    pairs = [{
        "premise": evidence_premise(
            str(row["answer"]), [str(ev.get("text", "")) for ev in
                                 row["evidence"]]),
        "hypothesis": str(row["answer"]),
    } for row in rows]
    verdicts = pb.bge_centroid_verdicts(pairs, bge, centroids)
    bge.save()
    outcomes: dict[str, dict] = {}
    for row, verdict in zip(rows, verdicts):
        outcomes[str(row["instance_id"])] = {
            "verdict": verdict,
            "status": "ok",
            "diagnostics": [f"bge_centroid:{verdict}"],
            "claims": [],
        }
    stats = {
        "method": "bge_centroid (public_baselines接口)",
        "mode": bge.mode,
        "fit_pool": {"ocnli_train": BGE_FIT_OCNLI_N,
                     "cmnli_train": BGE_FIT_CMNLI_N, "seed": bench_seed,
                     "n_fit_pairs": len(fit_pool)},
        "n_pairs": bge.stats.get("n_texts", len(pairs)),
        "llm_stats": {"invocations": 0, "api_calls": 0, "cache_hits": 0},
    }
    return outcomes, stats


# ── 06号复现参照(旧eval_crossdoc运行) ─────────────────────────


def doc06_reference(reference_run: str | None = None) -> dict[str, Any] | None:
    """读取旧eval_crossdoc运行(06号30条单文档)作为06号子集复现参照."""
    if reference_run:
        paths = [RUNS_ROOT / reference_run / "result.json"]
    else:
        paths = sorted(RUNS_ROOT.glob("eval_crossdoc_*/result.json"),
                       key=lambda p: p.stat().st_mtime)[-1:]
    for path in paths:
        if not path.exists():
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        configs = result.get("configs", {})
        picked: dict[str, Any] = {}
        for mine, theirs in OLD_RUN_CONFIG_MAP.items():
            if theirs and theirs in configs:
                picked[mine] = {
                    "macro_f1": configs[theirs]["metrics"]["macro_f1"],
                    "accuracy": configs[theirs]["metrics"]["accuracy"],
                }
        if picked:
            return {"run": path.parent.name, "n": result["evalset"]["n"],
                    "configs": picked}
    return None


def doc06_reproduction(scores: dict[str, dict],
                       reference: dict[str, Any] | None) -> dict[str, Any]:
    """06号子集(30条)指标与旧单文档运行的同配置对比(应逐位复现)."""
    if reference is None:
        return {"available": False,
                "reason": "未找到eval_crossdoc参照运行"}
    out: dict[str, Any] = {"available": True, "reference_run": reference["run"]}
    for config, score in scores.items():
        ref = reference["configs"].get(config)
        if ref is None:
            continue
        subset = score["per_doc"].get("06")
        if not subset:
            continue
        subset_f1 = subset["macro_f1"]
        out[config] = {
            "doc06_subset_macro_f1": subset_f1,
            "reference_macro_f1": ref["macro_f1"],
            "reproduced": subset_f1 == ref["macro_f1"],
        }
    return out


# ── 模块构造 ───────────────────────────────────────────────


def build_modules(configs: Sequence[str]) -> dict[str, Any]:
    modules: dict[str, Any] = {}
    if "b3_deterministic" in configs:
        modules["b3_deterministic"] = QAConsistencyModule(use_experts=True)
    if "l2_egt_nli" in configs or "ours_cascade" in configs:
        checkpoint = MODELS[MODEL_KEY]["dir"]
        if not (Path(checkpoint) / "config.json").exists():
            raise FileNotFoundError(
                f"NLI checkpoint不存在: {checkpoint} "
                f"(先跑 python tools/train_residual_nli.py)")
        if "l2_egt_nli" in configs:
            modules["l2_egt_nli"] = QAConsistencyModule(
                use_experts=True, use_nli_residual=True,
                nli_model_path=checkpoint, nli_gate=NLI_GATE)
        if "ours_cascade" in configs:
            modules["ours_cascade"] = QAConsistencyModule(
                use_experts=True, use_cascade=True,
                nli_model_path=checkpoint, nli_gate=NLI_GATE)
    return modules


# ── 报告渲染 ───────────────────────────────────────────────


def render_markdown_report(result: dict) -> str:
    config_order = [c for c in ("b3_deterministic", "l2_egt_nli",
                                "ours_cascade", "mdeberta_zeroshot",
                                "bge_centroid")
                    if c in result["configs"]]
    lines = [
        "# 跨文档泛化评测 (自建-跨文档×5, 构造性sound标签)", "",
        f"- evalset: `{result['evalset']['path']}` "
        f"({result['evalset']['n']}行 = 5文档×30, S/R/N各50)",
        f"- label: **{result['label_type']}** (label_proof逐条背书, 零LLM silver)",
        "- baseline口径: mdeberta_zeroshot premise与L2共用"
        "residual_premise; bge_centroid复用public_baselines接口"
        "(fit=OCNLI/CMNLI train, test premise=evidence_premise)",
        "",
        "## 分文档 × 分配置 macro-F1 矩阵", "",
        "| doc | " + " | ".join(config_order) + " | n |",
        "|---|" + "---|" * (len(config_order) + 1),
    ]
    for doc in (*DOC_NUMBERS, "overall"):
        cells = []
        for config in config_order:
            entry = result["configs"][config]
            if doc == "overall":
                cells.append(str(entry["metrics"]["macro_f1"]))
            else:
                cells.append(str(
                    entry["per_doc"].get(doc, {}).get("macro_f1", "—")))
        n = (result["evalset"]["n"] if doc == "overall"
             else result["evalset"]["per_doc_counts"].get(doc, 0))
        lines.append(f"| {doc} | " + " | ".join(cells) + f" | {n} |")
    lines.append("")
    for config in config_order:
        entry = result["configs"][config]
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
    repro = result.get("doc06_reproduction", {})
    if repro.get("available"):
        lines += ["## 06号子集复现 (vs 旧eval_crossdoc单文档运行)", "",
                  "| config | 06子集 macro-F1 | 旧运行 macro-F1 | 复现 |",
                  "|---|---|---|---|"]
        for config in config_order:
            entry = repro.get(config)
            if not isinstance(entry, dict):
                continue
            lines.append(
                f"| {config} | {entry['doc06_subset_macro_f1']} "
                f"| {entry['reference_macro_f1']} "
                f"| {'✓' if entry['reproduced'] else '✗'} |")
        lines.append("")
    lines += ["## 误判实例 (按配置)", ""]
    for config in config_order:
        mis = result["configs"][config].get("attribution", {}).get(
            "misclassified", [])
        lines.append(f"### {config} ({len(mis)}条)")
        for item in mis:
            lines.append(
                f"- {item['instance_id']} [{item['family']}/"
                f"{item['operator']}] {item['gold']}→{item['pred']}")
        lines.append("")
    return "\n".join(lines)


# ── 主流程 ─────────────────────────────────────────────────


def validate_benchmark_shape(rows: Sequence[dict]) -> dict[str, int]:
    """合并集形态校验: 5文档各30条(供main/测试调用; 评测内核不绑定)."""
    per_doc_counts = {doc: sum(1 for r in rows if doc_of(r) == doc)
                      for doc in DOC_NUMBERS}
    for doc, count in per_doc_counts.items():
        if count != 30:
            raise ValueError(f"{doc}号子集应30条, 实得{count}")
    return per_doc_counts


def run_evaluation(
        evalset_path: Path = DEFAULT_EVALSET,
        out_root: Path | None = None,
        configs: Sequence[str] = ("b3_deterministic", "l2_egt_nli",
                                  "ours_cascade", "mdeberta_zeroshot",
                                  "bge_centroid"),
        reference_run: str | None = None,
        script_name: str = "eval_crossdoc5",
        validate_shape: bool = False,
) -> tuple[dict[str, Any], Path]:
    rows = load_evalset(Path(evalset_path))
    per_doc_counts = {doc: sum(1 for r in rows if doc_of(r) == doc)
                      for doc in DOC_NUMBERS}
    if validate_shape:
        validate_benchmark_shape(rows)

    modules = build_modules(configs)
    results: dict[str, dict[str, Any]] = {}
    for name, runner in modules.items():
        outcomes, llm_stats = run_with_llm_counting(runner, rows)
        results[name] = {
            "metrics": score_config(outcomes, rows),
            "per_doc": per_doc_scores(outcomes, rows),
            "llm_stats": llm_stats,
            "attribution": channel_attribution(outcomes, rows),
        }
    if "mdeberta_zeroshot" in configs:
        outcomes, zs_stats = run_mdeberta_zeroshot(rows)
        results["mdeberta_zeroshot"] = {
            "metrics": score_config(outcomes, rows),
            "per_doc": per_doc_scores(outcomes, rows),
            "llm_stats": zs_stats["llm_stats"],
            "zeroshot_stats": zs_stats,
            "attribution": channel_attribution(outcomes, rows),
        }
    if "bge_centroid" in configs:
        outcomes, bge_stats = run_bge_centroid(rows)
        results["bge_centroid"] = {
            "metrics": score_config(outcomes, rows),
            "per_doc": per_doc_scores(outcomes, rows),
            "llm_stats": bge_stats["llm_stats"],
            "bge_stats": bge_stats,
            "attribution": channel_attribution(outcomes, rows),
        }

    reference = doc06_reference(reference_run)
    result = {
        "benchmark": "crossdoc5_generalization",
        "evalset": {"path": str(Path(evalset_path)),
                    "n": len(rows),
                    "per_doc_counts": per_doc_counts,
                    "label_distribution": dict(
                        Counter(r["sound_label"] for r in rows)),
                    "family_distribution": dict(
                        Counter(r.get("family", "") for r in rows))},
        "label_type": "constructive_sound (label_proof; no LLM silver)",
        "configs": results,
        "nli_gate": NLI_GATE,
        "model_key": MODEL_KEY,
        "doc06_reference": reference,
        "doc06_reproduction": doc06_reproduction(results, reference),
    }
    run = open_run(script_name, {
        "evalset": str(Path(evalset_path).relative_to(BASE))
        if Path(evalset_path).is_relative_to(BASE) else str(evalset_path),
        "n": len(rows),
        "configs": list(results),
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
                        help="06号旧eval_crossdoc运行目录名(默认取最新)")
    parser.add_argument("--configs", nargs="+",
                        default=["b3_deterministic", "l2_egt_nli",
                                 "ours_cascade", "mdeberta_zeroshot",
                                 "bge_centroid"],
                        choices=["b3_deterministic", "l2_egt_nli",
                                 "ours_cascade", "mdeberta_zeroshot",
                                 "bge_centroid"])
    args = parser.parse_args()
    result, run_path = run_evaluation(
        evalset_path=args.evalset, configs=args.configs,
        reference_run=args.reference_run, validate_shape=True)
    print(f"run: {run_path}")
    matrix: dict[str, Any] = {}
    for config, entry in result["configs"].items():
        matrix[config] = {
            "overall_macro_f1": entry["metrics"]["macro_f1"],
            "per_doc_macro_f1": {doc: m["macro_f1"]
                                 for doc, m in entry["per_doc"].items()},
        }
    print(json.dumps({
        "n": result["evalset"]["n"],
        "matrix": matrix,
        "doc06_reproduction": result["doc06_reproduction"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
