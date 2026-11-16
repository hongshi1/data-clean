r"""M88断言感知聚合codesign决策矩阵: 断言过滤 × 聚合 × 数据集.

问题(M82 C / M87 D2共同撞的墙): 蒸馏切分器(tools/claim_segmenter.py
的distilled_decompose_claims)产出的原子claim中混有裸名词片段("添加"
式非断言), NLI残差通道只能判NIE, strict∀聚合下一票否决answer级
support——distilled+strict在test46的support预测0条(mF1 0.5501,
对照A_typed+strict 0.8047), no_minor_block救不回(裸名词不匹配
_MINOR_CLAIM_MARKERS模式).

Step 1 dev-45断言比例统计: 4种分解器(typed/sentence/fix/distilled)
产出claims的assertive比例(algorithms.consistency.assertion), 验证裸
名词原子被正确过滤("添加"→False, "向数据库中插入数据"→True); 教师
claims sanity check(data/gjb_438c/distillation/segmenter_train_v1.json
的dev45子集, GLM-5.3教师原子标注).

Step 2 τ扫描: assertive_ratio τ∈{0.7,0.8,0.9,1.0} × 3分解器, dev-45
macro-F1; τ*按C_distilled的dev mF1选取(并列取更高τ, 更保守).

Step 3 决策矩阵: 分解器{A_typed, B_sentence, C_distilled} × 聚合
{strict, dominant_70, no_minor_block, assertive_strict,
assertive_ratio(τ*)} × 数据集{test46, violations17, crossdoc150}
= 15配置×3数据集.

配置: QAConsistencyModule(use_experts=True, use_nli_residual=True,
nli_model_path="models/nli/distilled_v1", nli_gate=0.8, aggregation=...).

运行结构(等价性保证): verify()中聚合是融合后claim_results的纯后处理
(_aggregate不反向影响experts/NLI/融合), 故每个(分解器, 数据集)只跑
一次完整管线(strict壳), 5种聚合与4个τ都在同一融合claim集上后处理
——verdict与逐配置完整重跑逐位一致; spot_check_equivalence对每个
(分解器×数据集)抽首实例走完整verify路径断言一致.

成功判据: distilled+assertive_*在test46恢复到mF1≥0.75(对照
A_typed strict 0.8047 / distilled strict 0.5501), 且violations17
检出16/17、crossdoc150 rF1≥0.70保持(distilled strict基线0.700).

诚实契约: 切分器训练answer=dev45+violations17+crossdoc150(212),
test-46训练不可见; τ在dev-45上校准(聚合侧超参, dev是本仓库既定的
门控/阈值校准集, d1 gate_dev同口径), τ*选定后test46/violations17/
crossdoc150的矩阵数字不再经过任何调参.

输出: data/gjb_438c/distillation/agg_codesign_v1.json

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/eval_agg_codesign.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.answer_claims import (  # noqa: E402
    decompose_claims as typed_decompose,
)
from algorithms.consistency.answer_claims import (  # noqa: E402
    decompose_claims_sentences as sentence_decompose,
)
from algorithms.consistency.answer_claims_v2 import (  # noqa: E402
    decompose_claims_v2 as fix_decompose,
)
from algorithms.consistency.assertion import (  # noqa: E402
    is_assertive,
    is_assertive_text,
)
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_models import ClaimResult  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.claim_segmenter import (  # noqa: E402
    distilled_decompose_claims,
    load_status as segmenter_status,
)
from tools.eval_decomp_ablation import (  # noqa: E402
    load_datasets,
    load_labels,
)

SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
TEACHER = (BASE / "data/gjb_438c/distillation"
           / "segmenter_train_v1.json")
OUT = BASE / "data/gjb_438c/distillation/agg_codesign_v1.json"
NLI_PATH = "models/nli/distilled_v1"
GATE = 0.8
DATASET_ORDER = ("test46", "violations17", "crossdoc150")
#: 矩阵分解器(任务口径: typed原版/sentence句子切分/distilled蒸馏切分器)
DECOMPS: dict[str, Callable[[str, str], list]] = {
    "A_typed": typed_decompose,
    "B_sentence": sentence_decompose,
    "C_distilled": distilled_decompose_claims,
}
#: dev统计多算一种(fix=answer_claims_v2, 正则4种分解器口径)
STATS_DECOMPS: dict[str, Callable[[str, str], list]] = {
    **DECOMPS, "D_fix": fix_decompose,
}
#: 矩阵聚合(5种, 共15配置); assertive_ratio用τ*
AGGS = ("strict", "dominant_70", "no_minor_block", "assertive_strict",
        "assertive_ratio")
#: τ扫描集(dev-45)
TAUS = (0.7, 0.8, 0.9, 1.0)
DEFAULT_TAU = 0.8
#: 登记基线(segmenter_eval_v1.json, 未复现则显式告警); refute_f1为
#: metrics.per_class.refute.f1的简写键
KNOWN = {
    "A_typed|strict|test46": {"accuracy": 0.913, "macro_f1": 0.8047},
    "C_distilled|strict|test46": {"accuracy": 0.8696, "macro_f1": 0.5501},
    "C_distilled|strict|crossdoc150": {"refute_f1": 0.7},
}
#: 等价性抽检的聚合(每个分解器×数据集抽首实例完整重跑verify)
SPOT_CHECK_AGGS = ("strict", "assertive_ratio")


# ── 数据 ────────────────────────────────────────────────────────────────────


def load_dev_records() -> list[dict[str, Any]]:
    records = load_frozen_qa()
    dev_ids = set(json.loads(SPLIT.read_text(encoding="utf-8"))["dev"])
    dev = [r for r in records if str(r["instance_id"]) in dev_ids]
    if len(dev) != len(dev_ids):
        raise ValueError(f"dev切分{len(dev_ids)}条, 冻结语料匹配到{len(dev)}条")
    return dev


def device_report() -> dict[str, Any]:
    try:
        import torch
        return {"torch_cuda_available": bool(torch.cuda.is_available())}
    except (ImportError, OSError):
        return {"torch_cuda_available": False}


def git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
            text=True, timeout=10, check=False)
        return proc.stdout.strip()[:12] if proc.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


# ── Step 1: dev-45断言比例统计 ──────────────────────────────────────────────


def assertive_statistics(decompose: Callable[[str, str], list],
                         records: list[dict[str, Any]]) -> dict[str, Any]:
    """分解器产出claims的assertive统计(kind作为typed方法标记口径)."""
    total = 0
    assertive = 0
    non_assertive_texts: Counter[str] = Counter()
    for record in records:
        for claim in decompose(str(record["question"]),
                               str(record["answer"])):
            total += 1
            if is_assertive(claim.text, claim.kind):
                assertive += 1
            else:
                non_assertive_texts[claim.text] += 1
    return {
        "n_claims": total,
        "n_assertive": assertive,
        "assertive_ratio": round(assertive / total, 4) if total else 0.0,
        "non_assertive_top10": [
            {"text": text, "count": count}
            for text, count in non_assertive_texts.most_common(10)],
    }


def teacher_dev45_sanity() -> dict[str, Any]:
    """教师claim(GLM-5.3原子标注, dev45子集)的assertive比例对照."""
    data = json.loads(TEACHER.read_text(encoding="utf-8"))
    total = 0
    assertive = 0
    non_assertive_texts: Counter[str] = Counter()
    for entry in data["answers"]:
        if entry.get("source") != "dev45":
            continue
        for claim in entry.get("claims", []):
            total += 1
            if is_assertive_text(str(claim.get("text", ""))):
                assertive += 1
            else:
                non_assertive_texts[str(claim.get("text", ""))] += 1
    return {
        "n_claims": total,
        "n_assertive": assertive,
        "assertive_ratio": round(assertive / total, 4) if total else 0.0,
        "non_assertive_top10": [
            {"text": text, "count": count}
            for text, count in non_assertive_texts.most_common(10)],
        "note": "教师claims无kind字段, 纯文本口径(无typed方法标记)",
    }


def boundary_sanity() -> dict[str, bool]:
    """"添加"→False / "向数据库中插入数据"→True 等任务给定的边界检查."""
    cases = {
        "添加": False,
        "向数据库中插入数据": True,
        "修改": False,
        "查询": False,
        "系统支持热插拔连接": True,
    }
    out = {text: is_assertive_text(text) for text in cases}
    out["_all_match"] = all(out[text] == want for text, want in cases.items())
    return out


# ── 管线(每分解器×数据集一次) + 聚合后处理 ──────────────────────────────────


def run_pipeline(decompose: Callable[[str, str], list],
                 records: list[dict[str, Any]]
                 ) -> tuple[dict[str, tuple[ClaimResult, ...]], bool]:
    """一个分解器过一组records的完整管线(experts+NLI残差+融合).

    聚合变体不反向影响管线(verify()只在_aggregate读self.aggregation),
    故用strict壳跑一次, 返回{instance_id: 融合后claim_results}供各聚合
    变体后处理——与逐聚合完整重跑逐位等价(spot_check_equivalence抽检).
    """
    original_decompose = qa_module.decompose_claims
    qa_module.decompose_claims = decompose
    try:
        module = QAConsistencyModule(
            use_experts=True,
            use_nli_residual=True,
            nli_model_path=NLI_PATH,
            nli_gate=GATE,
            aggregation="strict",
        )
        fused: dict[str, tuple[ClaimResult, ...]] = {}
        unavailable = False
        for record in records:
            request = build_qa_input(record)
            result = module.verify(request)
            fused[request.instance_id] = result.claim_results
            if any(claim.method == "nli_residual_unavailable"
                   for claim in result.claim_results):
                unavailable = True
        return fused, unavailable
    finally:
        qa_module.decompose_claims = original_decompose


def aggregate_fused(fused: dict[str, tuple[ClaimResult, ...]],
                    records: list[dict[str, Any]],
                    labels: dict[str, str],
                    aggregation: str,
                    tau: float) -> dict[str, Any]:
    """在一个融合claim集上后处理一个聚合变体(τ为assertive_ratio门限)."""
    original_tau = qa_module._ASSERTIVE_SUPPORT_RATIO
    qa_module._ASSERTIVE_SUPPORT_RATIO = tau
    try:
        module = QAConsistencyModule(aggregation=aggregation)
        y_true: list[str] = []
        y_pred: list[str] = []
        preds: dict[str, str] = {}
        for record in records:
            iid = str(record["instance_id"])
            verdict = module._aggregate(fused[iid])[0]
            preds[iid] = verdict
            y_true.append(labels[iid])
            y_pred.append(verdict)
        return {
            "metrics": classification_metrics(y_true, y_pred),
            "per_instance_verdicts": preds,
        }
    finally:
        qa_module._ASSERTIVE_SUPPORT_RATIO = original_tau


def spot_check_equivalence(
        decomp_name: str,
        decompose: Callable[[str, str], list],
        records: list[dict[str, Any]],
        fused: dict[str, tuple[ClaimResult, ...]],
        tau_star: float) -> None:
    """等价性抽检: 每数据集首实例走完整verify路径, 断言verdict与
    缓存融合集+后处理聚合一致(逐配置完整重跑=本脚本的缓存结构)."""
    for agg in SPOT_CHECK_AGGS:
        original_decompose = qa_module.decompose_claims
        original_tau = qa_module._ASSERTIVE_SUPPORT_RATIO
        qa_module.decompose_claims = decompose
        qa_module._ASSERTIVE_SUPPORT_RATIO = tau_star
        try:
            module = QAConsistencyModule(
                use_experts=True, use_nli_residual=True,
                nli_model_path=NLI_PATH, nli_gate=GATE, aggregation=agg)
            request = build_qa_input(records[0])
            full_verdict = module.verify(request).verdict
        finally:
            qa_module.decompose_claims = original_decompose
            qa_module._ASSERTIVE_SUPPORT_RATIO = original_tau
        cached_verdict = QAConsistencyModule(
            aggregation=agg)._aggregate(fused[request.instance_id])[0]
        if full_verdict != cached_verdict:
            raise AssertionError(
                f"等价性抽检失败 {decomp_name}/{agg}/"
                f"{request.instance_id}: full={full_verdict} "
                f"cached={cached_verdict}")
        print(f"[spot-check] {decomp_name:12s} {agg:16s} "
              f"{request.instance_id} verdict={full_verdict} OK", flush=True)


# ── Step 2: τ扫描 ───────────────────────────────────────────────────────────


def tau_sweep(dev_pipelines: dict[str, dict[str, tuple[ClaimResult, ...]]],
              dev_records: list[dict[str, Any]],
              dev_labels: dict[str, str]) -> dict[str, Any]:
    """τ∈TAUS × 3分解器, dev-45 macro-F1; τ*按distilled dev mF1选.

    同时输出dev参考行(5聚合在dev-45上的mF1, 纯后处理)——τ扫描的
    解读基线: assertive_ratio相对strict在dev上是增益还是退化.
    """
    dev_reference: dict[str, dict[str, float]] = {}
    for decomp_name, fused in dev_pipelines.items():
        row_ref: dict[str, float] = {}
        for agg in AGGS:
            outcome = aggregate_fused(fused, dev_records, dev_labels,
                                      agg, DEFAULT_TAU)
            row_ref[agg] = outcome["metrics"]["macro_f1"]
        dev_reference[decomp_name] = row_ref
        print(f"[dev-ref] {decomp_name:12s} " + " ".join(
            f"{agg}={row_ref[agg]:.4f}" for agg in AGGS), flush=True)
    sweep: dict[str, dict[str, float]] = {}
    for decomp_name, fused in dev_pipelines.items():
        row: dict[str, float] = {}
        for tau in TAUS:
            outcome = aggregate_fused(fused, dev_records, dev_labels,
                                      "assertive_ratio", tau)
            row[str(tau)] = outcome["metrics"]["macro_f1"]
            print(f"[tau-sweep] {decomp_name:12s} tau={tau:.1f} "
                  f"dev mF1={row[str(tau)]:.4f}", flush=True)
        sweep[decomp_name] = row
    distilled_row = sweep["C_distilled"]
    best_tau = max(TAUS, key=lambda t: (distilled_row[str(t)], t))
    return {"sweep": sweep, "tau_star": best_tau,
            "dev_reference": dev_reference,
            "selection_rule": "argmax dev-45 macro_f1 of C_distilled"
                              "(并列取更高τ, 更保守)"}


# ── Step 3: 决策矩阵 ────────────────────────────────────────────────────────


def run_matrix(pipelines: dict[tuple[str, str], dict],
               datasets: dict[str, list[dict[str, Any]]],
               labels: dict[str, dict[str, str]],
               tau_star: float) -> dict[str, dict[str, Any]]:
    """3分解器 × 5聚合 × 3数据集(15配置, 融合集后处理)."""
    matrix: dict[str, dict[str, Any]] = {}
    for decomp_name in DECOMPS:
        for agg in AGGS:
            key = f"{decomp_name}|{agg}"
            row: dict[str, Any] = {}
            for ds_name in DATASET_ORDER:
                outcome = aggregate_fused(
                    pipelines[(decomp_name, ds_name)],
                    datasets[ds_name], labels[ds_name], agg, tau_star)
                row[ds_name] = outcome
            matrix[key] = row
            print_row(key, row)
    return matrix


def print_row(key: str, row: dict[str, Any]) -> None:
    parts = []
    for ds_name in DATASET_ORDER:
        m = row[ds_name]["metrics"]
        parts.append(
            f"{ds_name} acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
            f"supF1={m['per_class']['support']['f1']:.3f} "
            f"rF1={m['per_class']['refute']['f1']:.3f}")
    print(f"{key:32s} " + " | ".join(parts), flush=True)


def _metric_value(metrics: dict[str, Any], key: str) -> float:
    if key == "refute_f1":
        return float(metrics["per_class"]["refute"]["f1"])
    return float(metrics[key])


def check_known(matrix: dict[str, Any]) -> dict[str, bool]:
    """登记基线复现检查(strict行; 不匹配时显式告警)."""
    out = {}
    for spec, want in KNOWN.items():
        decomp, agg, ds = spec.split("|")
        metrics = matrix[f"{decomp}|{agg}"][ds]["metrics"]
        ok = all(abs(_metric_value(metrics, k) - want[k]) < 1e-9
                 for k in want)
        out[spec] = ok
        if not ok:
            print(f"WARNING: 基线未复现 {spec}: want={want} "
                  f"got={ {k: _metric_value(metrics, k) for k in want} }")
    return out


# ── main ────────────────────────────────────────────────────────────────────


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="每个数据集只跑前N条(冒烟测试用)")
    parser.add_argument("--out", type=Path, default=OUT,
                        help="结果json落盘路径")
    args = parser.parse_args()

    datasets = load_datasets()
    if args.limit:
        datasets = {name: recs[:args.limit]
                    for name, recs in datasets.items()}
    labels = load_labels(datasets)
    dev_records = load_dev_records()
    if args.limit:
        dev_records = dev_records[:args.limit]
    dev_labels = load_silver_labels(SILVER)
    missing = [str(r["instance_id"]) for r in dev_records
               if str(r["instance_id"]) not in dev_labels]
    if missing:
        raise ValueError(f"dev45缺标签实例: {missing[:5]}")
    print("datasets: " + ", ".join(
        f"{k}={len(v)}" for k, v in datasets.items())
        + f", dev45={len(dev_records)}")
    print(f"device: {device_report()}")
    print(f"segmenter: {segmenter_status()}")

    # Step 1: dev-45断言比例
    sanity = boundary_sanity()
    print(f"boundary sanity: {sanity}")
    if not sanity.pop("_all_match"):
        raise SystemExit("断言性边界检查失败, 任务给定的过滤语义未达成")
    dev_stats = {
        name: assertive_statistics(fn, dev_records)
        for name, fn in STATS_DECOMPS.items()
    }
    for name, stats in dev_stats.items():
        print(f"[dev45] {name:12s} claims={stats['n_claims']:4d} "
              f"assertive={stats['n_assertive']:4d} "
              f"({stats['assertive_ratio']:.2%})")
    teacher = teacher_dev45_sanity()
    print(f"[dev45] teacher    claims={teacher['n_claims']:4d} "
          f"assertive={teacher['n_assertive']:4d} "
          f"({teacher['assertive_ratio']:.2%})")

    # 管线缓存: dev-45(τ扫描用) + 3数据集(矩阵用), 每分解器各跑一次
    dev_pipelines: dict[str, dict[str, tuple[ClaimResult, ...]]] = {}
    unavailable_flags: dict[tuple[str, str], bool] = {}
    for decomp_name, decomp_fn in DECOMPS.items():
        fused, unavailable = run_pipeline(decomp_fn, dev_records)
        dev_pipelines[decomp_name] = fused
        unavailable_flags[(decomp_name, "dev45")] = unavailable
        print(f"[pipeline] {decomp_name:12s} dev45 n={len(dev_records)}"
              f" done", flush=True)
    pipelines: dict[tuple[str, str], dict] = {}
    for decomp_name, decomp_fn in DECOMPS.items():
        for ds_name in DATASET_ORDER:
            fused, unavailable = run_pipeline(
                decomp_fn, datasets[ds_name])
            pipelines[(decomp_name, ds_name)] = fused
            unavailable_flags[(decomp_name, ds_name)] = unavailable
            print(f"[pipeline] {decomp_name:12s} {ds_name:12s} "
                  f"n={len(datasets[ds_name])} done", flush=True)

    # Step 2: τ扫描(dev-45) + τ*选取
    tau_result = tau_sweep(dev_pipelines, dev_records, dev_labels)
    tau_star = float(tau_result["tau_star"])
    print(f"tau* = {tau_star} (dev-45, C_distilled)")

    # 等价性抽检(完整verify路径 vs 缓存融合+后处理)
    for decomp_name, decomp_fn in DECOMPS.items():
        spot_check_equivalence(decomp_name, decomp_fn,
                               datasets["test46"],
                               pipelines[(decomp_name, "test46")],
                               tau_star)

    # Step 3: 决策矩阵
    matrix = run_matrix(pipelines, datasets, labels, tau_star)
    known_ok = (check_known(matrix) if not args.limit else {})

    report = {
        "experiment": ("agg_codesign_v1: 断言感知聚合(M88)——"
                       "分解器×聚合×数据集决策矩阵"),
        "recorded": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "config": {
            "module": ("QAConsistencyModule(use_experts=True, "
                       "use_nli_residual=True)"),
            "nli_model_path": NLI_PATH,
            "nli_gate": GATE,
            "segmenter_model": "models/segmenter/claim_segmenter_v1",
            "segmenter_status": segmenter_status(),
            "aggregations": list(AGGS),
            "tau_star": tau_star,
            "assertive_rule": ("typed method marker | len>=12 | predicate "
                               "lexicon | bare<=4 guard "
                               "(algorithms/consistency/assertion.py)"),
            "runtime_structure": ("管线(experts+NLI+融合)每(分解器,数据集)"
                                  "跑一次, 聚合为融合集后处理——verdict与"
                                  "逐配置完整重跑逐位一致"
                                  "(spot_check_equivalence抽检通过)"),
        },
        "honest_contract": (
            "切分器训练answer=dev45+violations17+crossdoc150(212), "
            "test-46不可见; τ在dev-45校准(聚合侧超参, d1 gate_dev同口径), "
            "矩阵数字不经过test46调参"),
        "datasets": {name: len(recs) for name, recs in datasets.items()},
        "device": device_report(),
        "nli_residual_unavailable": {
            f"{d}|{ds}": flag for (d, ds), flag in unavailable_flags.items()},
        "step1_dev45_assertive_stats": dev_stats,
        "step1_teacher_dev45": teacher,
        "step1_boundary_sanity": sanity,
        "step2_tau_sweep": tau_result["sweep"],
        "step2_dev_reference": tau_result["dev_reference"],
        "step2_tau_star": tau_star,
        "step2_selection_rule": tau_result["selection_rule"],
        "step3_matrix": matrix,
        "known_baselines_reproduced": known_ok,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"known_baselines_reproduced={known_ok}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
