r"""Step2: if-else启发式 → 本地模型替换实验 (monkeypatch, 不改algorithms/).

背景: 用户核心诉求"代码不要很多的if else 而是应该用模型". Step1审计
(tools/audit_ifelse_density.py)定位的决策型if-else簇, 本脚本逐簇做
"换成模型"的实证: 每个实验只monkeypatch对应入口(模块级函数名或类方法),
其余管线不动, 与正则基线(test46 acc 0.9130 / mF1 0.8047 / rF1 0.800,
d1_paper_summary_v1.json gate_dev)对照. 所有patch在finally中恢复.

实验(模块配置一律: QAConsistencyModule(use_experts=True,
use_nli_residual=True, nli_model_path="models/nli/distilled_v1",
nli_gate=0.8), 聚合默认strict):
  A0_baseline  正则管线不动(复现基线; 数字不匹配→显式告警)
  A1_typed_nli 实验A·隔离形态: 正则decompose不动, 只把四个typed
               verify_*(verify_numeric/quoted/enum/identifier的
               正则+if-else守卫)替换为distilled_v1 NLI逐claim判定
               (premise=nli_training.residual_premise, 推理=
               nli_residual._infer, 同门控0.8, 无typed分派)
  A2_seg_nli   实验A·完整形态: claim_segmenter_v2切分(模型decompose)
               + 同上NLI替换 → 所有claim走模型路径
  B_agg_vote   实验B: qa_module._aggregate的四分支阶梯
               (strict/dominant_70/no_minor_block/assertive_strict)
               → claim置信度加权投票(w = confidence × is_assertive,
               refute权重×2安全序, 平票保守NIE)
  C_route_off  实验C: qa_router.route_question返回() + answer_claims/
               qa_module/deq_pipeline三个消费点空转(M73惰性结论复验,
               代码清理的实证依据)

数据集(抄tools/eval_decomp_ablation.py的load_datasets/load_labels):
  test46(91QA held-out, 主对照) / violations17(真实注入违反, 安全副指标)
  / crossdoc150(跨文档, 泛化副指标).

输出: runs协议(data/gjb_438c/runs/exp_model_replace_*/) +
      固定摘要 data/gjb_438c/distillation/model_replace_v1.json

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/exp_model_replace.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import algorithms.consistency.answer_claims as answer_claims_mod  # noqa: E402
import algorithms.consistency.deq_pipeline as deq_mod  # noqa: E402
import algorithms.consistency.qa_module as qa_module  # noqa: E402
import algorithms.consistency.qa_router as qa_router_mod  # noqa: E402
from algorithms.consistency.assertion import is_assertive_claim  # noqa: E402
from algorithms.consistency.claim_channels import unresolved  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.evidence_statements import linearize_context  # noqa: E402
from algorithms.consistency.nli_residual import (  # noqa: E402
    NLI_TO_VERDICT,
    _infer,
    _load_model,
)
from algorithms.consistency.nli_training import (  # noqa: E402
    PREMISE_BUDGET,
    residual_premise,
)
from algorithms.consistency.qa_models import ClaimResult  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.claim_segmenter import distilled_decompose_claims  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIOLATIONS = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
CROSSDOC_DOCS = ("05", "06", "07", "08", "10")
CROSSDOC_DIR = BASE / "data/gjb_438c/qa_frozen"
OUT_PATH = BASE / "data/gjb_438c/distillation/model_replace_v1.json"

NLI_MODEL_PATH = "models/nli/distilled_v1"
NLI_GATE = 0.8
SEG_V2 = "models/segmenter/claim_segmenter_v2"
#: v2弱B置信度门限(claim_recognition_v2.json τ-sweep选定, 非test46调参)
BOUNDARY_GATE = 0.75
DATASET_ORDER = ("test46", "violations17", "crossdoc150")
#: 已知基线(d1_paper_summary_v1.json gate_dev); 不复现→显式告警
KNOWN_TEST46 = {"accuracy": 0.913, "macro_f1": 0.8047, "refute_f1": 0.800}
#: route_question的消费点模块(M73同口径)
ROUTE_TARGETS = (qa_router_mod, answer_claims_mod, qa_module, deq_mod)

DecomposeFn = Callable[[str, str], list[Any]]
Module = QAConsistencyModule


# ── 数据加载(抄tools/eval_decomp_ablation.py) ───────────────────────────────


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_datasets() -> dict[str, list[dict[str, Any]]]:
    records = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    test_ids = set(split["test"])
    test_recs = [r for r in records if str(r["instance_id"]) in test_ids]
    if len(test_recs) != len(test_ids):
        raise ValueError(f"test切分{len(test_ids)}条, "
                         f"冻结语料只匹配到{len(test_recs)}条")
    vio_recs = read_jsonl(VIOLATIONS)
    if len(vio_recs) != 17:
        raise ValueError(f"violations评测集应17条, 实际{len(vio_recs)}条")
    cross_recs: list[dict[str, Any]] = []
    for doc in CROSSDOC_DOCS:
        rows = read_jsonl(CROSSDOC_DIR / f"crossdoc{doc}_evalset_v1.jsonl")
        if len(rows) != 30:
            raise ValueError(f"crossdoc{doc}子集应30条, 实际{len(rows)}条")
        cross_recs.extend(rows)
    if len(cross_recs) != 150:
        raise ValueError(f"crossdoc合并集应150条, 实际{len(cross_recs)}条")
    return {"test46": test_recs, "violations17": vio_recs,
            "crossdoc150": cross_recs}


def load_labels(datasets: dict[str, list[dict[str, Any]]]
                ) -> dict[str, dict[str, str]]:
    silver = load_silver_labels(SILVER)
    labels = {
        "test46": silver,
        "violations17": {str(r["instance_id"]): str(r["expected_verdict"])
                         for r in datasets["violations17"]},
        "crossdoc150": {str(r["instance_id"]): str(r["sound_label"])
                        for r in datasets["crossdoc150"]},
    }
    for name, recs in datasets.items():
        missing = [str(r["instance_id"]) for r in recs
                   if str(r["instance_id"]) not in labels[name]]
        if missing:
            raise ValueError(f"{name}缺标签实例: {missing[:5]}")
    return labels


# ── 实验A: typed通道 → distilled_v1 NLI (monkeypatch工厂) ──────────────────


def build_nli_typed_verify(entry: dict[str, Any], gate: float
                           ) -> Callable[..., ClaimResult]:
    """claim_channels四个typed verify_*的NLI替换版工厂.

    与正则守卫同签名(request, claim, index, check_items); premise走
    nli_training.residual_premise(训练/推理同分布, S4校准教训),
    推理走nli_residual._infer(批量+fp16+GPU); 门控与L2残差通道同值.
    method="nli_typed_replace"不进RESIDUAL_METHODS → 不会被L2残差
    通道二次判定(每claim恰一次NLI判定).
    """
    stmt_cache: dict[str, list[Any]] = {}

    def nli_verify(request, claim, index, check_items) -> ClaimResult:
        key = request.instance_id
        if key not in stmt_cache:
            stmt_cache[key] = linearize_context(request.evidence)
        statements = stmt_cache[key]
        if not statements:
            return unresolved(request, claim, index, check_items,
                              "NLI替换typed通道: 无证据语句")
        premise, picks = residual_premise(claim.text, request.question,
                                          statements, PREMISE_BUDGET)
        if not premise.strip():
            return unresolved(request, claim, index, check_items,
                              "NLI替换typed通道: premise构造为空"
                              "(无scope/重叠命中)")
        prob = _infer(entry, [(premise, claim.text)])[0]
        label = max(prob, key=lambda k: prob[k])
        confidence = float(prob[label])
        verdict = NLI_TO_VERDICT[label]
        refs = tuple(sorted({statements[idx].evidence_id
                             for idx, _ in picks}))
        notes: list[str] = []
        if confidence < gate:
            notes.append(f"softmax最大概率{confidence:.2f}"
                         f"低于门控{gate:.2f}, 保守NIE")
            verdict = "not_in_evidence"
        if verdict == "not_in_evidence":
            refs = ()
        rationale = (f"NLI替换typed通道: {label}(p={confidence:.2f}), "
                     f"premise含{len(picks)}条证据语句")
        if notes:
            rationale += "（" + "；".join(notes) + "）"
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict=verdict,
            check_item_candidates=check_items,
            evidence_refs=refs,
            span=claim.span,
            rationale=rationale,
            method="nli_typed_replace",
            confidence=round(confidence, 4),
        )

    return nli_verify


# ── 实验B: _aggregate阶梯 → 置信度加权投票 ─────────────────────────────────


def weighted_vote_aggregate(self, results: tuple[ClaimResult, ...]
                            ) -> tuple[str, list[str]]:
    """学习式聚合替换_aggregate四分支阶梯(monkeypatch到类方法).

    规则(任务书口径):
      w(claim) = confidence × is_assertive  (裸名词/非断言碎片零权,
                不能投票——与M88 assertive发现一致);
      refute权重×2安全序: 任何refute claim存在 → 实例refute
                (单条refute的加权票已压过任意support票, 等价实现);
      否则 support票权和 vs NIE票权和: support严格更大 → support,
                否则(含平票)保守NIE;
      无任何有效票(全非断言/全零置信) → 回退strict序(NIE>support).
    """
    labels = {r.verdict for r in results}
    if "refute" in labels:
        return "refute", ["agg_weighted_vote_refute_safety_x2"]
    w_support = 0.0
    w_nie = 0.0
    for result in results:
        if not is_assertive_claim(result):
            continue
        if result.verdict == "support":
            w_support += result.confidence
        elif result.verdict == "not_in_evidence":
            w_nie += result.confidence
    if w_support + w_nie <= 0.0:
        if "not_in_evidence" in labels:
            return "not_in_evidence", [
                "agg_weighted_vote_no_vote_strict_fallback"]
        return "support", ["agg_weighted_vote_no_vote_strict_fallback"]
    diagnostic = (f"agg_weighted_vote_w_support={w_support:.2f}"
                  f"_w_nie={w_nie:.2f}")
    if w_support > w_nie:
        return "support", [diagnostic]
    return "not_in_evidence", [diagnostic]


# ── 变体执行(monkeypatch + finally恢复) ────────────────────────────────────


def eval_dataset(module: Module, records: list[dict[str, Any]],
                 labels: dict[str, str]) -> tuple[dict[str, Any],
                                                 dict[str, str], bool,
                                                 Counter[str]]:
    """单数据集评测 → (metrics, per-instance preds, nli_unavailable,
    claim方法分布)."""
    y_true: list[str] = []
    y_pred: list[str] = []
    preds: dict[str, str] = {}
    unavailable = False
    methods: Counter[str] = Counter()
    for record in records:
        request = build_qa_input(record)
        result = module.verify(request)
        preds[request.instance_id] = result.verdict
        methods.update(claim.method for claim in result.claim_results)
        if any(claim.method == "nli_residual_unavailable"
               for claim in result.claim_results):
            unavailable = True
        y_true.append(labels[request.instance_id])
        y_pred.append(result.verdict)
    return (classification_metrics(y_true, y_pred), preds, unavailable,
            methods)


def claim_statistics(decompose: DecomposeFn,
                     records: list[dict[str, Any]]) -> dict[str, Any]:
    """分解器确定性统计: claim数/每实例/长度/kind分布."""
    total = 0
    lengths: list[int] = []
    kinds: Counter[str] = Counter()
    for record in records:
        for claim in decompose(str(record["question"]), str(record["answer"])):
            total += 1
            lengths.append(len(claim.text))
            kinds[claim.kind] += 1
    n = len(records)
    return {
        "n_claims": total,
        "claims_per_instance": round(total / n, 2) if n else 0.0,
        "claim_len_avg": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "claim_len_max": max(lengths) if lengths else 0,
        "kind_distribution": dict(sorted(kinds.items())),
    }


def run_variant(name: str, nli_entry: dict[str, Any],
                decompose: DecomposeFn | None, *, typed_nli: bool,
                agg_vote: bool, route_off: bool,
                datasets: dict[str, list[dict[str, Any]]],
                labels: dict[str, dict[str, str]]
                ) -> dict[str, Any]:
    """跑一个变体: 打patch → 建模块 → 三个数据集评测 → finally恢复."""
    saved_decompose = qa_module.decompose_claims
    saved_verifies = {fn: getattr(qa_module, fn) for fn in
                      ("verify_numeric", "verify_quoted", "verify_enum",
                       "verify_identifier")}
    saved_aggregate = QAConsistencyModule._aggregate
    saved_routes = [(m, m.route_question) for m in ROUTE_TARGETS]
    try:
        if decompose is not None:
            qa_module.decompose_claims = decompose
        if typed_nli:
            nli_verify = build_nli_typed_verify(nli_entry, NLI_GATE)
            for fn in saved_verifies:
                setattr(qa_module, fn, nli_verify)
        if agg_vote:
            QAConsistencyModule._aggregate = weighted_vote_aggregate
        if route_off:

            def no_route(_question: str) -> tuple[str, ...]:
                return ()

            for module in ROUTE_TARGETS:
                module.route_question = no_route
        module = QAConsistencyModule(
            use_experts=True,
            use_nli_residual=True,
            nli_model_path=NLI_MODEL_PATH,
            nli_gate=NLI_GATE,
        )
        per_dataset: dict[str, Any] = {}
        for ds_name in DATASET_ORDER:
            started = time.perf_counter()
            metrics, preds, unavailable, methods = eval_dataset(
                module, datasets[ds_name], labels[ds_name])
            seconds = round(time.perf_counter() - started, 1)
            if unavailable:
                print(f"WARNING: {name}/{ds_name}: NLI残差模型不可用"
                      "(结果退化为无L2)")
            per_dataset[ds_name] = {
                "metrics": metrics,
                "seconds": seconds,
                "per_instance_verdicts": preds,
                "claim_method_distribution": dict(sorted(methods.items())),
            }
            refute = metrics["per_class"]["refute"]
            print(f"[{name}] {ds_name:12s} n={len(datasets[ds_name]):3d} "
                  f"acc={metrics['accuracy']:.4f} "
                  f"mF1={metrics['macro_f1']:.4f} "
                  f"refuteF1={refute['f1']:.3f} "
                  f"({seconds}s)", flush=True)
        return {
            "per_dataset": per_dataset,
            "claim_stats": claim_statistics(
                decompose or qa_module.decompose_claims,
                datasets["test46"]),
        }
    finally:
        qa_module.decompose_claims = saved_decompose
        for fn, original in saved_verifies.items():
            setattr(qa_module, fn, original)
        QAConsistencyModule._aggregate = saved_aggregate
        for module, original in saved_routes:
            module.route_question = original


# ── 对比分析 ────────────────────────────────────────────────────────────────


def flip_analysis(datasets: dict[str, list[dict[str, Any]]],
                  labels: dict[str, dict[str, str]],
                  preds_base: dict[str, dict[str, str]],
                  preds_var: dict[str, dict[str, str]]) -> dict[str, Any]:
    """各数据集 verdict翻转分析: 纠正/退化/两者皆错."""
    out: dict[str, Any] = {}
    for ds_name in DATASET_ORDER:
        gold = labels[ds_name]
        changed = 0
        corrected: list[str] = []
        regressed: list[str] = []
        other: list[str] = []
        for record in datasets[ds_name]:
            iid = str(record["instance_id"])
            before = preds_base[ds_name].get(iid)
            after = preds_var[ds_name].get(iid)
            if before is None or after is None or before == after:
                continue
            changed += 1
            if after == gold[iid]:
                corrected.append(iid)
            elif before == gold[iid]:
                regressed.append(iid)
            else:
                other.append(iid)
        out[ds_name] = {
            "n_changed": changed,
            "corrected": corrected,
            "regressed": regressed,
            "moved_both_wrong": other,
        }
    return out


def git_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=BASE, capture_output=True, text=True,
                              timeout=10, check=False)
        return proc.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def device_report() -> dict[str, Any]:
    try:
        import torch
        return {"torch_cuda_available": bool(torch.cuda.is_available())}
    except (ImportError, OSError):
        return {"torch_cuda_available": False}


# ── main ───────────────────────────────────────────────────────────────────


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    datasets = load_datasets()
    labels = load_labels(datasets)
    nli_entry = _load_model(NLI_MODEL_PATH)
    if nli_entry["mode"] == "unavailable":
        raise RuntimeError(
            f"NLI模型不可用({NLI_MODEL_PATH}): {nli_entry['error']}")
    print(f"NLI模型: {nli_entry['mode']}; "
          f"数据集: " + ", ".join(f"{k}={len(v)}" for k, v in
                                  datasets.items()))

    def seg_v2_decompose(question: str, answer: str) -> list[Any]:
        return distilled_decompose_claims(question, answer, model_path=SEG_V2,
                                          boundary_gate=BOUNDARY_GATE)

    variants: list[dict[str, Any]] = [
        {"name": "A0_baseline", "decompose": None, "typed_nli": False,
         "agg_vote": False, "route_off": False, "desc": "正则管线基线"},
        {"name": "A1_typed_nli", "decompose": None, "typed_nli": True,
         "agg_vote": False, "route_off": False,
         "desc": "实验A隔离: 四个typed verify_*→distilled_v1 NLI"},
        {"name": "A2_seg_nli", "decompose": seg_v2_decompose,
         "typed_nli": True, "agg_vote": False, "route_off": False,
         "desc": "实验A完整: segmenter_v2切分+NLI, 全claim走模型路径"},
        {"name": "B_agg_vote", "decompose": None, "typed_nli": False,
         "agg_vote": True, "route_off": False,
         "desc": "实验B: _aggregate阶梯→置信度加权投票"},
        {"name": "C_route_off", "decompose": None, "typed_nli": False,
         "agg_vote": False, "route_off": True,
         "desc": "实验C: route_question→() (M73惰性复验)"},
    ]

    results: dict[str, Any] = {}
    for spec in variants:
        print(f"\n=== {spec['name']}: {spec['desc']} ===", flush=True)
        results[spec["name"]] = run_variant(
            spec["name"], nli_entry, spec["decompose"],
            typed_nli=spec["typed_nli"], agg_vote=spec["agg_vote"],
            route_off=spec["route_off"], datasets=datasets, labels=labels)
        results[spec["name"]]["desc"] = spec["desc"]

    # 基线复现检查
    base_m = results["A0_baseline"]["per_dataset"]["test46"]["metrics"]
    baseline_ok = (abs(base_m["accuracy"] - KNOWN_TEST46["accuracy"]) < 5e-4
                   and abs(base_m["macro_f1"] - KNOWN_TEST46["macro_f1"])
                   < 5e-4)
    if not baseline_ok:
        print(f"WARNING: 基线未复现已知数字 "
              f"(acc={base_m['accuracy']:.4f} vs {KNOWN_TEST46['accuracy']}, "
              f"mF1={base_m['macro_f1']:.4f} vs "
              f"{KNOWN_TEST46['macro_f1']})")

    flips = {}
    for name in results:
        if name == "A0_baseline":
            continue
        flips[name] = flip_analysis(
            datasets, labels,
            {ds: results["A0_baseline"]["per_dataset"][ds]
             ["per_instance_verdicts"] for ds in DATASET_ORDER},
            {ds: results[name]["per_dataset"][ds]["per_instance_verdicts"]
             for ds in DATASET_ORDER})

    summary = {
        "tool": "tools/exp_model_replace.py",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "device": device_report(),
        "config": {
            "module": "QAConsistencyModule(use_experts=True, "
                      "use_nli_residual=True, "
                      f"nli_model_path={NLI_MODEL_PATH!r}, "
                      f"nli_gate={NLI_GATE}, aggregation='strict')",
            "nli_model_path": NLI_MODEL_PATH,
            "nli_gate": NLI_GATE,
            "segmenter": f"{SEG_V2}@boundary_gate={BOUNDARY_GATE}",
            "datasets": {k: len(v) for k, v in datasets.items()},
        },
        "baseline_known_test46": KNOWN_TEST46,
        "baseline_reproduced": baseline_ok,
        "variants": results,
        "flips_vs_baseline": flips,
    }

    # runs协议落盘
    sys.path.insert(0, str(BASE / "tools"))
    from run_utils import open_run  # noqa: E402
    run = open_run("exp_model_replace", {
        "nli_model_path": NLI_MODEL_PATH, "nli_gate": NLI_GATE,
        "segmenter": SEG_V2, "boundary_gate": BOUNDARY_GATE,
        "variants": [v["name"] for v in variants],
    })
    run.save_result(summary)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    # 控制台对照表
    print("\n===== test46 对照表 (基线 acc=0.9130 mF1=0.8047 rF1=0.800) =====")
    print(f"{'variant':14s} {'acc':>8s} {'mF1':>8s} {'rF1':>7s} "
          f"{'vio17 refF1':>12s} {'crossdoc acc':>13s}")
    for name in results:
        m = results[name]["per_dataset"]["test46"]["metrics"]
        vio = results[name]["per_dataset"]["violations17"]["metrics"]
        cross = results[name]["per_dataset"]["crossdoc150"]["metrics"]
        print(f"{name:14s} {m['accuracy']:8.4f} {m['macro_f1']:8.4f} "
              f"{m['per_class']['refute']['f1']:7.3f} "
              f"{vio['per_class']['refute']['f1']:12.3f} "
              f"{cross['accuracy']:13.4f}")
    print(f"\nruns: {run.path}")
    print(f"摘要: {OUT_PATH}")


if __name__ == "__main__":
    main()
