r"""claim→typed通道桥接下游评测: D3管线test46, 正则 vs 裸切分器 vs 桥接.

问题(99号方案P1 / 95号§7.1 / Alignment Bottleneck arXiv 2602.10380):
蒸馏切分器v2的claim识别F1 0.7041远超正则typed 0.2427, 但裸接入下游
macro-F1 0.7496 < 正则0.8047(claim_downstream_v2.json). 桥接(claim粒度
typed字段抽取, SRE→SAE)能否把识别优势变现为下游增益?

臂(同模块配置/同冻结证据/同标签, 只换per-claim分解通道):
  A_regex        decomposer="typed"(基线, 应复现0.913/0.8047)
  B_seg_v2_bare  qa_module.decompose_claims monkeypatch为切分器v2
                 (gate=0.75, sanity: 应复现strict 0.5789 / 
                 assertive_strict 0.7496)
  C_bridge       decomposer="distilled_typed"(claim_typed_bridge:
                 切分器claim span上typed字段抽取+语义回退)

隔离: L0/L1专家用answer_structure.decompose_answer(未patch), 只ablate
per-claim分解通道(同tools/eval_claim_downstream_v2.py协议).

claim识别F1(验收第二条): dev45+d3train600教师claims=gold, 口径同
tools/eval_claim_recognition.py(text_ratio>=0.8或span IoU>=0.5,
贪心1-1), 评测桥接claim全集(typed+semantic)对教师金标的识别质量.

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/eval_claim_typed_bridge.py
输出: data/gjb_438c/runs/eval_claim_typed_bridge_<hash>_<ts>/result.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.claim_segmenter_local import (  # noqa: E402
    load_status)
from algorithms.consistency.claim_typed_bridge import (  # noqa: E402
    bridge_decompose_claims)
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.claim_segmenter import distilled_decompose_claims  # noqa: E402
from tools.eval_claim_recognition import eval_variant, load_gold  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
TRAIN_V1 = BASE / "data/gjb_438c/distillation/segmenter_train_v1.json"
TRAIN_V2 = BASE / "data/gjb_438c/distillation/segmenter_train_v2.json"

NLI_MODEL_PATH = "models/nli/distilled_v1"
NLI_GATE = 0.8
SEG_V2 = "models/segmenter/claim_segmenter_v2"
BOUNDARY_GATE = 0.75
#: 当前评测的切分器(默认v2向后兼容; --segmenter覆盖, 103号P1-v2用v3)
SEG_ACTIVE = SEG_V2
#: 已知基线(claim_downstream_v2.json, 复现校验)
KNOWN = {
    "A_regex": {"accuracy": 0.913, "macro_f1": 0.8047},
    "B_seg_v2_strict": {"accuracy": 0.8913, "macro_f1": 0.5789},
    "B_seg_v2_assertive_strict": {"accuracy": 0.913, "macro_f1": 0.7496},
}
#: 已知claim识别F1(claim_recognition_v2.json, 复现校验)
KNOWN_RECOG = {"dev45": 0.7041, "d3train600": 0.7955}

DecomposeFn = Callable[[str, str], list[Any]]
AGGREGATIONS = ("strict", "assertive_strict")


def git_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=BASE, capture_output=True, text=True,
                              timeout=10, check=False)
        return proc.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def load_test46() -> list[dict[str, Any]]:
    records = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    test_ids = set(split["test"])
    test_recs = [r for r in records if str(r["instance_id"]) in test_ids]
    if len(test_recs) != len(test_ids):
        raise ValueError(f"test切分{len(test_ids)}条, "
                         f"冻结语料只匹配到{len(test_recs)}条")
    return test_recs


def eval_dataset(module: QAConsistencyModule,
                 records: list[dict[str, Any]],
                 labels: dict[str, str]) -> dict[str, Any]:
    y_true: list[str] = []
    y_pred: list[str] = []
    preds: dict[str, str] = {}
    unavailable = False
    for record in records:
        request = build_qa_input(record)
        result = module.verify(request)
        preds[request.instance_id] = result.verdict
        if any(claim.method == "nli_residual_unavailable"
               for claim in result.claim_results):
            unavailable = True
        y_true.append(labels[request.instance_id])
        y_pred.append(result.verdict)
    metrics = classification_metrics(y_true, y_pred)
    return {"metrics": metrics, "per_instance_verdicts": preds,
            "nli_unavailable": unavailable}


def claim_statistics(decompose: DecomposeFn,
                     records: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    lengths: list[int] = []
    by_kind: dict[str, int] = {}
    for record in records:
        for claim in decompose(str(record["question"]), str(record["answer"])):
            total += 1
            lengths.append(len(claim.text))
            by_kind[claim.kind] = by_kind.get(claim.kind, 0) + 1
    n = len(records)
    return {
        "n_instances": n,
        "n_claims": total,
        "claims_per_instance": round(total / n, 2) if n else 0.0,
        "claim_len_avg": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "claim_len_max": max(lengths) if lengths else 0,
        "claims_by_kind": dict(sorted(by_kind.items())),
    }


def run_arm(name: str, decompose: DecomposeFn, patch: bool,
            records: list[dict[str, Any]],
            labels: dict[str, str],
            decomposer_mode: str = "typed") -> dict[str, Any]:
    """跑一个臂: 两种聚合各一遍(与v2协议同结构, monkeypatch+恢复内嵌).

    decomposer_mode: 传给QAConsistencyModule的decomposer参数
    (C_bridge走"distilled_typed"注册项; A/B走"typed", B臂靠monkeypatch).
    """
    original = qa_module.decompose_claims
    if patch:
        qa_module.decompose_claims = decompose
    entry: dict[str, Any] = {"claim_stats": claim_statistics(decompose, records)}
    try:
        t0 = time.perf_counter()
        for aggregation in AGGREGATIONS:
            module = QAConsistencyModule(
                use_experts=True,
                use_nli_residual=True,
                nli_model_path=NLI_MODEL_PATH,
                nli_gate=NLI_GATE,
                aggregation=aggregation,
                decomposer=decomposer_mode,
            )
            result = eval_dataset(module, records, labels)
            if result["nli_unavailable"]:
                print(f"WARNING: {name}/{aggregation}: NLI残差模型不可用")
            entry[aggregation] = result
            m = result["metrics"]
            print(f"[{aggregation}/{name}] test46 n={len(records)} "
                  f"acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
                  f"supF1={m['per_class']['support']['f1']:.4f} "
                  f"refF1={m['per_class']['refute']['f1']:.4f} "
                  f"claims={entry['claim_stats']['n_claims']} "
                  f"({entry['claim_stats']['claims_per_instance']}/inst)",
                  flush=True)
        entry["wall_seconds"] = round(time.perf_counter() - t0, 1)
        return entry
    finally:
        if patch:
            qa_module.decompose_claims = original


# ── claim识别F1(桥接claim全集 vs 教师金标, 同eval_claim_recognition口径) ──


def bridge_predict(question: str, answer: str) -> list[dict[str, Any]]:
    """桥接claim全集 → 识别评测预测格式({text, span})."""
    return [{"text": claim.text,
             "span": list(claim.span) if claim.span else None}
            for claim in bridge_decompose_claims(
                question, answer, model_path=SEG_ACTIVE)]


def seg_predict(question: str, answer: str) -> list[dict[str, Any]]:
    """裸切分器claim → 识别评测预测格式(参照, 应复现0.7041/0.7955)."""
    return [{"text": claim.text,
             "span": list(claim.span) if claim.span else None}
            for claim in distilled_decompose_claims(
                question, answer, model_path=SEG_ACTIVE,
                boundary_gate=BOUNDARY_GATE)]


def recognition_eval() -> dict[str, Any]:
    out: dict[str, Any] = {}
    slices = [("dev45", TRAIN_V1, "dev45")]
    if TRAIN_V2.exists():
        slices.append(("d3train600", TRAIN_V2, "d3train"))
    for name, path, source in slices:
        gold = load_gold(path, source)
        out[name] = {
            "bridge": eval_variant(gold, bridge_predict),
            "segmenter_bare": eval_variant(gold, seg_predict),
        }
        for variant in ("bridge", "segmenter_bare"):
            r = out[name][variant]
            print(f"[recog/{name}/{variant}] P={r['claim_precision']:.4f} "
                  f"R={r['claim_recall']:.4f} F1={r['claim_f1']:.4f} "
                  f"pred={r['n_pred_claims']} gold={r['n_gold_claims']}",
                  flush=True)
    return out


def main() -> None:
    global SEG_ACTIVE
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-recognition", action="store_true",
                        help="跳过claim识别F1(仅下游三臂)")
    parser.add_argument("--segmenter", type=str, default=SEG_V2,
                        help="切分器模型路径(默认v2; 103号P1-v2实验用"
                             " models/segmenter/claim_segmenter_v3)")
    args = parser.parse_args()
    SEG_ACTIVE = args.segmenter
    # arm标签从模型路径派生(claim_segmenter_v3/v4/...), 兜底v2
    seg_tag = (SEG_ACTIVE.rstrip("/\\").rsplit("_", 1)[-1]
               if SEG_ACTIVE != SEG_V2 else "v2")
    is_v3 = seg_tag != "v2"

    records = load_test46()
    labels = load_silver_labels(SILVER)
    missing = [str(r["instance_id"]) for r in records
               if str(r["instance_id"]) not in labels]
    if missing:
        raise ValueError(f"test46缺标签实例: {missing[:5]}")
    print(f"test46: {len(records)}条; labels: {len(labels)}")
    print(f"segmenter[{seg_tag}] status:", load_status(SEG_ACTIVE))

    def seg_decompose(question: str, answer: str) -> list[Any]:
        return distilled_decompose_claims(question, answer,
                                          model_path=SEG_ACTIVE,
                                          boundary_gate=BOUNDARY_GATE)

    def bridge_v_decompose(question: str, answer: str) -> list[Any]:
        return bridge_decompose_claims(question, answer,
                                       model_path=SEG_ACTIVE)

    arms: list[tuple[str, DecomposeFn, bool, str]] = [
        ("A_regex", qa_module.decompose_claims, False, "typed"),
        (f"B_seg_{seg_tag}_bare", seg_decompose, True, "typed"),
        (f"C_bridge_{seg_tag}", bridge_v_decompose, False,
         "distilled_typed"),
    ]
    results: dict[str, Any] = {}
    for name, decompose, patch, mode in arms:
        results[name] = run_arm(name, decompose, patch, records, labels,
                                decomposer_mode=mode)

    repro = {
        "A_regex": (results["A_regex"]["strict"]["metrics"]["accuracy"]
                    == KNOWN["A_regex"]["accuracy"]
                    and results["A_regex"]["strict"]["metrics"]["macro_f1"]
                    == KNOWN["A_regex"]["macro_f1"]),
    }
    if not is_v3:
        repro["B_seg_v2_strict"] = (
            results["B_seg_v2_bare"]["strict"]["metrics"]["accuracy"]
            == KNOWN["B_seg_v2_strict"]["accuracy"]
            and results["B_seg_v2_bare"]["strict"]["metrics"]["macro_f1"]
            == KNOWN["B_seg_v2_strict"]["macro_f1"])
        repro["B_seg_v2_assertive_strict"] = (
            results["B_seg_v2_bare"]["assertive_strict"]["metrics"][
                "accuracy"]
            == KNOWN["B_seg_v2_assertive_strict"]["accuracy"]
            and results["B_seg_v2_bare"]["assertive_strict"]["metrics"][
                "macro_f1"]
            == KNOWN["B_seg_v2_assertive_strict"]["macro_f1"])

    recognition: dict[str, Any] = {}
    if not args.skip_recognition:
        recognition = recognition_eval()
        if not is_v3:
            # v2复现校验; v3的识别F1是新口径(混合标签训练)只记录不校验
            for name, expect in KNOWN_RECOG.items():
                if name in recognition:
                    got = recognition[name]["segmenter_bare"]["claim_f1"]
                    repro[f"recog_segmenter_{name}"] = got == expect

    report = {
        "experiment": ("claim→typed通道桥接下游评测(99号P1/103号P1-v2): "
                       "regex vs seg_bare vs bridge on test46 (D3 pipeline)"),
        "recorded": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "config": {
            "module": ("QAConsistencyModule(use_experts=True, "
                        "use_nli_residual=True)"),
            "nli_model_path": NLI_MODEL_PATH,
            "nli_gate": NLI_GATE,
            "aggregations": list(AGGREGATIONS),
            "segmenter": SEG_ACTIVE,
            "boundary_gate": BOUNDARY_GATE,
            "bridge": ("claim_typed_bridge.bridge_decompose_claims "
                       f"(model={SEG_ACTIVE}, gate={BOUNDARY_GATE})"),
            "arms": {
                "A_regex": "decomposer=typed(正则基线)",
                f"B_seg_{seg_tag}_bare": "monkeypatch "
                                         "distilled_decompose_claims"
                                         "(裸切分器, sanity)",
                f"C_bridge_{seg_tag}": "decomposer=distilled_typed(桥接)",
            },
        },
        "isolation_note": ("L0/L1专家用answer_structure.decompose_answer"
                           "(未patch); 只ablate per-claim分解通道"),
        "n": len(records),
        "known_baselines": KNOWN,
        "known_recognition": KNOWN_RECOG,
        "reproduced": repro,
        "results": results,
        "recognition": recognition,
    }
    run = open_run("eval_claim_typed_bridge", {
        "n_test46": len(records),
        "arms": list(results),
        "aggregations": list(AGGREGATIONS),
        "segmenter": SEG_ACTIVE,
        "boundary_gate": BOUNDARY_GATE,
        "skip_recognition": bool(args.skip_recognition),
    })
    run.save_result(report)

    print("\n" + "=" * 78)
    for aggregation in AGGREGATIONS:
        print(f"-- aggregation={aggregation}")
        print(f"{'arm':<16s} {'acc':>7s} {'mF1':>7s} {'supF1':>6s} "
              f"{'refF1':>6s} {'nieF1':>6s} {'cl/inst':>8s} {'sec':>6s}")
        for name in ("A_regex", f"B_seg_{seg_tag}_bare",
                     f"C_bridge_{seg_tag}"):
            m = results[name][aggregation]["metrics"]
            pc = m["per_class"]
            st = results[name]["claim_stats"]
            print(f"{name:<16s} {m['accuracy']:7.4f} {m['macro_f1']:7.4f} "
                  f"{pc['support']['f1']:6.4f} {pc['refute']['f1']:6.4f} "
                  f"{pc['not_in_evidence']['f1']:6.4f} "
                  f"{st['claims_per_instance']:8.2f} "
                  f"{results[name]['wall_seconds']:6.1f}")
        print()
    print("reproduced:", json.dumps(repro, ensure_ascii=False))
    print(f"→ {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
