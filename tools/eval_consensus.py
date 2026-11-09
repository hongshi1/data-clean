"""双NLI共识门控实验 (D1 refute精度修复研究).

假设: distilled_v1 @ nli_gate=0.8 的残差refute召回完整但精度不足
(test-46: P=0.67). 用一个独立的第二本地零样本NLI裁判
(Erlangshen-Roberta-330M-NLI, 从未在本语料上训练)复核每个融合后的
``nli_residual`` refute claim, premise走与L2通道完全一致的训练/推理
共用管线(``nli_training.residual_premise`` + ``linearize_context``):

    保留refute  iff  Erlangshen top label == contradiction
                     AND p_contra >= erlang_gate
    否则        claim降级not_in_evidence
                (method ``nli_residual_consensus_vetoed``),
                实例用 _fuse_per_claim + _aggregate 重聚合.

诚实契约: erlang_gate只在dev-45上扫描; test-46用dev选出的门控跑一次.
基线(同模块, 无复核)在同一次运行中重算, 形成配对对比.
产出走runs协议(open_run: config+git_sha+result).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from algorithms.consistency.eval_lib import (
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.evidence_statements import linearize_context
from algorithms.consistency.nli_local import NliLocal
from algorithms.consistency.nli_training import residual_premise
from algorithms.consistency.qa_models import ClaimResult
from algorithms.consistency.qa_module import QAConsistencyModule
from tools.run_utils import open_run

BASE = Path(__file__).resolve().parents[1]
LABELS = BASE / ("data/gjb_438c/runs/"
                 "review_qa_with_glm53_582b51e5_20261021_145212"
                 "/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"

NLI_MODEL_PATH = "models/nli/distilled_v1"
ERLANG_KEY = "erlangshen-330m"
DEFAULT_GATES = (0.4, 0.5, 0.6, 0.7)


def _erl_key(claim: ClaimResult) -> str:
    """复核缓存键: 压缩claim文本(同文本→同premise→同预测)."""
    return re.sub(r"\s+", "", claim.claim_text)


def fmt(m: dict[str, Any]) -> str:
    rc = m["per_class"].get("refute", {"f1": 0.0, "precision": 0.0,
                                       "recall": 0.0})
    return (f"acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
            f"refuteF1={rc['f1']:.3f} (P={rc['precision']:.2f} "
            f"R={rc['recall']:.2f})")


def run_main_judge(module: QAConsistencyModule,
                   records: list[dict]) -> dict[str, dict[str, Any]]:
    """distilled_v1主判定: 每实例缓存 request + fused claims + verdict."""
    state: dict[str, dict[str, Any]] = {}
    for record in records:
        request = build_qa_input(record)
        result = module.verify(request)
        state[request.instance_id] = {
            "request": request,
            "claims": list(result.claim_results),
            "verdict": result.verdict,
        }
    return state


def review_refutes(
        erlang: NliLocal,
        state: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Erlangshen零样本复核每个 nli_residual refute claim.

    premise重算与nli_residual通道内部完全同路:
    linearize_context(evidence) → residual_premise(claim, question, stmts).
    批量单次predict(确定性), 空premise由predict保守返回neutral(→否决).
    """
    reviews: dict[str, dict[str, Any]] = {}
    batch: list[tuple[str, str, str, str]] = []
    for iid, row in state.items():
        statements = linearize_context(row["request"].evidence)
        for claim in row["claims"]:
            if claim.method != "nli_residual" or claim.verdict != "refute":
                continue
            premise, _picks = residual_premise(
                claim.claim_text, row["request"].question, statements)
            batch.append((iid, _erl_key(claim), premise, claim.claim_text))
    if not batch:
        return reviews
    preds = erlang.predict([(premise, hyp) for _, _, premise, hyp in batch])
    for (iid, key, _premise, _hyp), pred in zip(batch, preds):
        reviews.setdefault(iid, {})[key] = {
            "label": pred["label"],
            "p_contra": round(float(pred["p_contra"]), 4),
        }
    return reviews


def apply_consensus(
        module: QAConsistencyModule,
        row: dict[str, Any],
        reviews: dict[str, dict[str, Any]],
        erlang_gate: float) -> tuple[str, list[dict[str, Any]]]:
    """对单个实例执行共识否决并重聚合 (任务协议: 融合结果上改写+重融合).

    仅 method=nli_residual 且 verdict=refute 的claim受门控; 其余claim
    原样保留. 重融合输入已按fusion key去重, 故重融合对该列表幂等.
    返回 (新instance verdict, 否决claim明细).
    """
    new_results: list[ClaimResult] = []
    vetoed: list[dict[str, Any]] = []
    for claim in row["claims"]:
        if claim.method == "nli_residual" and claim.verdict == "refute":
            review = reviews.get(_erl_key(claim))
            keep = (review is not None
                    and review["label"] == "contradiction"
                    and review["p_contra"] >= erlang_gate)
            if keep:
                new_results.append(claim)
                continue
            label = review["label"] if review else "neutral"
            p_contra = float(review["p_contra"]) if review else 0.0
            vetoed.append({
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "erlang_label": label,
                "erlang_p_contra": p_contra,
            })
            new_results.append(replace(
                claim,
                verdict="not_in_evidence",
                method="nli_residual_consensus_vetoed",
                evidence_refs=(),
                rationale=(f"{claim.rationale}；双NLI共识否决：Erlangshen"
                           f"零样本判{label}(p_contra={p_contra:.2f})"
                           f"未达门控{erlang_gate:.2f}，降级NIE"),
            ))
        else:
            new_results.append(claim)
    fused = module._fuse_per_claim(tuple(new_results))
    verdict, _diag = module._aggregate(fused)
    return verdict, vetoed


def eval_split(module: QAConsistencyModule,
               records: list[dict],
               state: dict[str, dict[str, Any]],
               reviews: dict[str, dict[str, Any]],
               silver: dict[str, str],
               erlang_gate: float | None
               ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """一个切分上的评测: erlang_gate=None → 基线(无复核, 直接用原verdict)."""
    y_true: list[str] = []
    y_pred: list[str] = []
    all_vetoed: list[dict[str, Any]] = []
    for record in records:
        iid = record["instance_id"]
        row = state[iid]
        if erlang_gate is None:
            verdict = row["verdict"]
        else:
            verdict, vetoed = apply_consensus(
                module, row, reviews.get(iid, {}), erlang_gate)
            for item in vetoed:
                item["instance_id"] = iid
                item["gold"] = silver[iid]
                item["baseline_verdict"] = row["verdict"]
            all_vetoed.extend(vetoed)
        y_true.append(silver[iid])
        y_pred.append(verdict)
    return classification_metrics(y_true, y_pred), all_vetoed


def refute_profile(state: dict[str, dict[str, Any]],
                   reviews: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """主判定refute的claim/实例计数 + Erlangshen一致率."""
    n_claims = sum(len(per) for per in reviews.values())
    n_contra = sum(1 for per in reviews.values()
                   for r in per.values() if r["label"] == "contradiction")
    p_list = [r["p_contra"] for per in reviews.values() for r in per.values()]
    n_refute_instances = sum(1 for row in state.values()
                             if row["verdict"] == "refute")
    return {
        "n_refute_claims": n_claims,
        "n_refute_instances": n_refute_instances,
        "erlang_contra_agreement": (round(n_contra / n_claims, 4)
                                    if n_claims else None),
        "erlang_p_contra_mean": (round(sum(p_list) / len(p_list), 4)
                                 if p_list else None),
        "erlang_p_contra_values": sorted(p_list, reverse=True),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="双NLI共识门控实验")
    parser.add_argument("--gates", nargs="*", type=float,
                        default=list(DEFAULT_GATES))
    parser.add_argument("--nli-gate", type=float, default=0.8)
    args = parser.parse_args()

    records = load_frozen_qa()
    silver = load_silver_labels(LABELS)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    dev_recs = [r for r in records if r["instance_id"] in dev_ids]
    test_recs = [r for r in records if r["instance_id"] not in dev_ids]
    missing = [r["instance_id"] for r in records if r["instance_id"] not in silver]
    if missing:
        raise SystemExit(f"silver标签缺失(不静默): {missing[:5]}")

    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path=NLI_MODEL_PATH, nli_gate=args.nli_gate)

    print(f"[1/4] distilled_v1 主判定 nli_gate={args.nli_gate} "
          f"(dev={len(dev_recs)} test={len(test_recs)}) ...")
    dev_state = run_main_judge(module, dev_recs)
    test_state = run_main_judge(module, test_recs)

    erlang = NliLocal(ERLANG_KEY)
    mode = erlang.ensure()
    if mode == "unavailable":
        raise SystemExit(f"Erlangshen不可用: {erlang.last_error}")
    print(f"[2/4] Erlangshen-330M 零样本复核 ({mode}) ...")
    dev_reviews = review_refutes(erlang, dev_state)
    test_reviews = review_refutes(erlang, test_state)
    erlang.stats["infer_ms"] = round(erlang.stats["infer_ms"], 1)

    dev_profile = refute_profile(dev_state, dev_reviews)
    test_profile = refute_profile(test_state, test_reviews)
    print(f"  dev  refute: {dev_profile['n_refute_claims']} claims / "
          f"{dev_profile['n_refute_instances']} instances; "
          f"Erlangshen一致率(contradiction)="
          f"{dev_profile['erlang_contra_agreement']}")
    print(f"  test refute: {test_profile['n_refute_claims']} claims / "
          f"{test_profile['n_refute_instances']} instances; "
          f"Erlangshen一致率(contradiction)="
          f"{test_profile['erlang_contra_agreement']}")

    print(f"[3/4] dev-45 扫描 erlang_gate ∈ {args.gates} ...")
    dev_base, _ = eval_split(module, dev_recs, dev_state, dev_reviews,
                             silver, None)
    print(f"  DEV baseline(无复核)  {fmt(dev_base)}")
    sweep: list[dict[str, Any]] = []
    best_gate: float | None = None
    best_mf1 = -1.0
    for gate in args.gates:
        metrics, vetoed = eval_split(module, dev_recs, dev_state,
                                     dev_reviews, silver, gate)
        n_vetoed_inst = len({v["instance_id"] for v in vetoed})
        print(f"  DEV gate={gate:.2f}          {fmt(metrics)}  "
              f"vetoed={len(vetoed)}claims/{n_vetoed_inst}inst")
        sweep.append({
            "erlang_gate": gate,
            "metrics": metrics,
            "n_vetoed_claims": len(vetoed),
            "n_vetoed_instances": n_vetoed_inst,
            "vetoed_on_gold_refute": sum(1 for v in vetoed
                                         if v["gold"] == "refute"),
        })
        if metrics["macro_f1"] > best_mf1:
            best_mf1 = metrics["macro_f1"]
            best_gate = gate
    if best_gate is None:
        raise SystemExit("dev扫描未产生任何门控结果")
    print(f"  dev-best erlang_gate = {best_gate} (macro_f1={best_mf1:.4f})")

    print(f"[4/4] test-46 诚实评测 (erlang_gate={best_gate}) ...")
    test_base, _ = eval_split(module, test_recs, test_state, test_reviews,
                              silver, None)
    test_cons, test_vetoed = eval_split(module, test_recs, test_state,
                                        test_reviews, silver, best_gate)
    print(f"  TEST baseline   {fmt(test_base)}")
    print(f"  TEST consensus  {fmt(test_cons)}")
    n_vetoed_inst = len({v["instance_id"] for v in test_vetoed})
    print(f"  vetoed: {len(test_vetoed)} claims / {n_vetoed_inst} instances; "
          f"其中gold=refute(误伤)="
          f"{sum(1 for v in test_vetoed if v['gold'] == 'refute')}")
    for v in test_vetoed:
        print(f"    veto {v['instance_id']} gold={v['gold']} "
              f"erlang={v['erlang_label']}"
              f"(p={v['erlang_p_contra']:.2f}) "
              f"claim={v['claim_text'][:40]}")

    result = {
        "nli_model_path": NLI_MODEL_PATH,
        "nli_gate": args.nli_gate,
        "erlang_model": ERLANG_KEY,
        "erlang_device": mode,
        "erlang_stats": dict(erlang.stats),
        "dev_baseline": dev_base,
        "dev_sweep": sweep,
        "dev_best_gate": best_gate,
        "test_baseline": test_base,
        "test_consensus": test_cons,
        "test_vetoed_claims": test_vetoed,
        "refute_profile": {"dev": dev_profile, "test": test_profile},
    }
    run = open_run("eval_consensus", {
        "nli_model_path": NLI_MODEL_PATH,
        "nli_gate": args.nli_gate,
        "erlang_model": ERLANG_KEY,
        "erlang_gates": list(args.gates),
        "split": str(SPLIT.relative_to(BASE)),
        "silver_labels": str(LABELS.relative_to(BASE)),
        "n_dev": len(dev_recs),
        "n_test": len(test_recs),
    })
    run.save_result(result)
    print(f"→ {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
