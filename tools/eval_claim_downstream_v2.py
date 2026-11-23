r"""claim切分器v2下游评测: D3管线test46一致性, 正则 vs 切分器v1 vs v2.

问题: 蒸馏切分器替换正则decompose_claims后, 下游QA一致性是否保持/提升?
(M87: v1切分器test46 acc=0.8696/mF1=0.5501 vs 正则acc=0.913/mF1=0.8047)

变体(同模块配置/同冻结证据/同标签, 只换per-claim分解通道):
  A_regex   decompose_claims不动(基线)
  B_seg_v1  qa_module.decompose_claims monkeypatch为
            claim_segmenter_v1的distilled_decompose_claims
  C_seg_v2  同上但model_path=claim_segmenter_v2

隔离: L0/L1专家用answer_structure.decompose_answer(未patch), 只ablate
per-claim分解通道(同tools/eval_decomp_ablation.py).

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/eval_claim_downstream_v2.py
输出: data/gjb_438c/distillation/claim_downstream_v2.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.claim_segmenter import distilled_decompose_claims  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
OUT_PATH = BASE / "data/gjb_438c/distillation/claim_downstream_v2.json"

NLI_MODEL_PATH = "models/nli/distilled_v1"
NLI_GATE = 0.8
SEG_V1 = "models/segmenter/claim_segmenter_v1"
SEG_V2 = "models/segmenter/claim_segmenter_v2"
#: v2弱B置信度门限(claim_recognition_v2.json的τ-sweep选定, 非test46调参)
BOUNDARY_GATE = 0.75
#: 已知正则基线(d1_paper_summary_v1.json, gate_dev)
KNOWN_REGEX = {"accuracy": 0.913, "macro_f1": 0.8047}
#: M87登记的v1切分器test46基线(segmenter_eval_v1.json)
KNOWN_SEG_V1 = {"accuracy": 0.8696, "macro_f1": 0.5501}

DecomposeFn = Callable[[str, str], list[Any]]


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
    for record in records:
        for claim in decompose(str(record["question"]), str(record["answer"])):
            total += 1
            lengths.append(len(claim.text))
    n = len(records)
    return {
        "n_instances": n,
        "n_claims": total,
        "claims_per_instance": round(total / n, 2) if n else 0.0,
        "claim_len_avg": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "claim_len_max": max(lengths) if lengths else 0,
    }


def run_variant(name: str, decompose: DecomposeFn, patch: bool,
                records: list[dict[str, Any]],
                labels: dict[str, str],
                aggregation: str) -> dict[str, Any]:
    """跑一个变体(monkeypatch+恢复内嵌)."""
    original = qa_module.decompose_claims
    if patch:
        qa_module.decompose_claims = decompose
    try:
        module = QAConsistencyModule(
            use_experts=True,
            use_nli_residual=True,
            nli_model_path=NLI_MODEL_PATH,
            nli_gate=NLI_GATE,
            aggregation=aggregation,
        )
        entry = eval_dataset(module, records, labels)
        if entry["nli_unavailable"]:
            print(f"WARNING: {name}: NLI残差模型不可用(结果退化为无L2)")
        entry["claim_stats"] = claim_statistics(decompose, records)
        m = entry["metrics"]
        print(f"[{aggregation}/{name}] test46 n={len(records)} "
              f"acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
              f"claims={entry['claim_stats']['n_claims']} "
              f"({entry['claim_stats']['claims_per_instance']}/inst)",
              flush=True)
        return entry
    finally:
        if patch:
            qa_module.decompose_claims = original


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    records = load_test46()
    labels = load_silver_labels(SILVER)
    missing = [str(r["instance_id"]) for r in records
               if str(r["instance_id"]) not in labels]
    if missing:
        raise ValueError(f"test46缺标签实例: {missing[:5]}")
    print(f"test46: {len(records)}条; labels: {len(labels)}")

    def seg_v1_decompose(question: str, answer: str) -> list[Any]:
        return distilled_decompose_claims(question, answer, model_path=SEG_V1)

    def seg_v1_gated_decompose(question: str, answer: str) -> list[Any]:
        return distilled_decompose_claims(question, answer, model_path=SEG_V1,
                                          boundary_gate=BOUNDARY_GATE)

    def seg_v2_decompose(question: str, answer: str) -> list[Any]:
        return distilled_decompose_claims(question, answer, model_path=SEG_V2,
                                          boundary_gate=BOUNDARY_GATE)

    def seg_v2_argmax_decompose(question: str, answer: str) -> list[Any]:
        return distilled_decompose_claims(question, answer, model_path=SEG_V2)

    variants: list[tuple[str, DecomposeFn, bool]] = [
        ("A_regex", qa_module.decompose_claims, False),
        ("B_seg_v1", seg_v1_decompose, True),
        ("C_seg_v2", seg_v2_decompose, True),
        ("D_seg_v1_gated", seg_v1_gated_decompose, True),
        ("E_seg_v2_argmax", seg_v2_argmax_decompose, True),
    ]
    # 两种聚合: strict(M87口径) + assertive_strict(M88: 裸碎片不能否决support)
    results: dict[str, Any] = {}
    for aggregation in ("strict", "assertive_strict"):
        results[aggregation] = {}
        for name, decompose, patch in variants:
            results[aggregation][name] = run_variant(
                name, decompose, patch, records, labels, aggregation)

    baseline_ok = (
        results["strict"]["A_regex"]["metrics"]["accuracy"]
        == KNOWN_REGEX["accuracy"]
        and results["strict"]["A_regex"]["metrics"]["macro_f1"]
        == KNOWN_REGEX["macro_f1"])
    seg_v1_repro = (
        results["strict"]["B_seg_v1"]["metrics"]["accuracy"]
        == KNOWN_SEG_V1["accuracy"]
        and results["strict"]["B_seg_v1"]["metrics"]["macro_f1"]
        == KNOWN_SEG_V1["macro_f1"])

    report = {
        "experiment": ("claim segmenter v2 downstream: regex vs seg_v1 vs "
                       "seg_v2 on test46 (D3 pipeline)"),
        "recorded": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "config": {
            "module": ("QAConsistencyModule(use_experts=True, "
                        "use_nli_residual=True)"),
            "nli_model_path": NLI_MODEL_PATH,
            "nli_gate": NLI_GATE,
            "aggregations": ["strict", "assertive_strict"],
            "aggregation_note": ("strict=M87口径(任一NIE claim否决support); "
                                 "assertive_strict=M88(非命题性裸碎片不能"
                                 "否决support)"),
            "segmenter_v1": SEG_V1,
            "segmenter_v2": SEG_V2,
            "boundary_gate_C_D": BOUNDARY_GATE,
        },
        "isolation_note": ("L0/L1专家用answer_structure.decompose_answer"
                           "(未patch); 只ablate per-claim分解通道"),
        "n": len(records),
        "known_baselines": {"A_regex": KNOWN_REGEX, "B_seg_v1_M87": KNOWN_SEG_V1},
        "baseline_regex_reproduced": baseline_ok,
        "seg_v1_M87_reproduced": seg_v1_repro,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    print("\n" + "=" * 78)
    for aggregation in ("strict", "assertive_strict"):
        print(f"-- aggregation={aggregation}")
        print(f"{'variant':<16s} {'acc':>7s} {'mF1':>7s} {'rF1':>6s} "
              f"{'cl/inst':>8s} {'avglen':>7s}")
        for name in ("A_regex", "B_seg_v1", "C_seg_v2", "D_seg_v1_gated",
                     "E_seg_v2_argmax"):
            m = results[aggregation][name]["metrics"]
            rc = m["per_class"]["refute"]
            st = results[aggregation][name]["claim_stats"]
            print(f"{name:<16s} {m['accuracy']:7.4f} {m['macro_f1']:7.4f} "
                  f"{rc['f1']:6.3f} {st['claims_per_instance']:8.2f} "
                  f"{st['claim_len_avg']:7.1f}")
        print()
    print(f"\nbaseline_regex_reproduced={baseline_ok} "
          f"seg_v1_M87_reproduced={seg_v1_repro}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
