r"""D2 Step4: 蒸馏claim切分器评测 (切分质量 + 下游管线 + 定位).

1. 切分质量(test-46的answer, 只推理不训练):
   原子性(融合claim率=含冒号/顿号/多谓词)/claims数/覆盖率/span精确率
   —— 蒸馏切分器 vs 正则decompose_claims对照.
2. 下游管线: qa_module.decompose_claims monkeypatch为切分器版本,
   QAConsistencyModule(use_experts=True, use_nli_residual=True,
   nli_model_path="models/nli/distilled_v1", nli_gate=0.8),
   test46+violations17+crossdoc150(数据加载抄tools/eval_decomp_ablation.py);
   aggregation两个变体(strict + no_minor_block, M82 C实验教训:
   原子化claim在strict∀下NIE一票否决/融合键破坏需聚合侧对照),
   对照A_typed(strict)=test46 mF1 0.8047 / violations检出16/17,
   refute F1 0.970 (d1_paper_summary_v1.json).
3. 定位: violations-17的localizations块级命中gold
   (口径抄tools/measure_localization_baseline.py).

输出: data/gjb_438c/distillation/segmenter_eval_v1.json

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/eval_segmenter.py [--limit N]
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
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.claim_segmenter import (  # noqa: E402
    MODEL_PATH,
    distilled_decompose_claims,
    load_status,
    segment_claims,
)
from tools.eval_decomp_ablation import load_datasets, load_labels  # noqa: E402
from tools.probe_llm_decomposer import _coverage, _fused  # noqa: E402

OUT_PATH = BASE / "data/gjb_438c/distillation/segmenter_eval_v1.json"
PROBE_PATH = (BASE / "data/gjb_438c/distillation"
              / "llm_decomposer_probe_v1.json")
NLI_MODEL_PATH = "models/nli/distilled_v1"
NLI_GATE = 0.8
DATASET_ORDER = ("test46", "violations17", "crossdoc150")
AGGREGATIONS = ("strict", "no_minor_block")
#: 登记基线(d1_paper_summary_v1.json, gate_dev)
KNOWN = {
    "A_typed_strict_test46": {"accuracy": 0.913, "macro_f1": 0.8047},
    "A_typed_strict_violations17": {"detected": 16, "refute_f1": 0.9697},
    "A_typed_strict_crossdoc150_accuracy": 0.5133,
}

DecomposeFn = Callable[[str, str], list]


# ── 1. 切分质量(test-46, 只推理) ────────────────────────────────────────────


def _regex_claim_records(question: str, answer: str) -> list[dict]:
    """正则decompose_claims → claim记录(span由find回收, 同probe口径)."""
    out: list[dict] = []
    for claim in typed_decompose(question, answer):
        text = claim.text
        span: list[int] | None = None
        for probe in (text, text.strip()):
            pos = answer.find(probe)
            if probe and pos != -1:
                span = [pos, pos + len(probe)]
                break
        out.append({"text": text, "span": span, "fused": _fused(text)})
    return out


def _segmenter_claim_records(answer: str) -> list[dict]:
    """蒸馏切分器 → claim记录(span=解码区间本身)."""
    return [{"text": item["text"], "span": item["span"],
             "fused": _fused(item["text"]),
             "boundary_conf": item["boundary_conf"]}
            for item in segment_claims(answer)]


def _seg_stats(answer_len: int, claims: list[dict]) -> dict:
    n = len(claims)
    if not n:
        return {"n": 0, "avg_len": 0.0, "fused_rate": 0.0,
                "span_exact_rate": 0.0, "coverage": 0.0,
                "len_p50": 0, "len_p90": 0}
    lengths = sorted(len(c["text"]) for c in claims)
    spans = [c["span"] for c in claims if c["span"]]
    exact = sum(1 for c in claims if c["span"] is not None)
    return {
        "n": n,
        "avg_len": round(sum(lengths) / n, 2),
        "fused_rate": round(sum(1 for c in claims if c["fused"]) / n, 4),
        "span_exact_rate": round(exact / n, 4),
        "coverage": round(_coverage(answer_len, spans), 4),
        "len_p50": lengths[n // 2],
        "len_p90": lengths[min(n - 1, int(n * 0.9))],
    }


def segmentation_quality(records: list[dict]) -> dict[str, Any]:
    """test-46 answers: 切分器 vs 正则(逐实例聚合 + 3个并排示例)."""
    per: dict[str, list[dict]] = {"regex": [], "distilled": []}
    example_pool: list[dict] = []
    for rec in records:
        answer = str(rec["answer"])
        regex = _regex_claim_records(str(rec["question"]), answer)
        distilled = _segmenter_claim_records(answer)
        per["regex"].append(_seg_stats(len(answer), regex))
        per["distilled"].append(_seg_stats(len(answer), distilled))
        example_pool.append({
            "instance_id": rec["instance_id"], "answer": answer,
            "regex_claims": [{"text": c["text"], "span": c["span"],
                              "fused": c["fused"]} for c in regex],
            "distilled_claims": distilled,
        })
    agg: dict[str, Any] = {}
    for side, stats in per.items():
        pool = [s for s in stats if s["n"]]
        n_claims = sum(s["n"] for s in stats)
        agg[side] = {
            "n_instances": len(stats),
            "n_claims": n_claims,
            "claims_per_instance": round(n_claims / len(stats), 2),
            "avg_claim_len": round(
                sum(s["avg_len"] * s["n"] for s in pool) / max(
                    sum(s["n"] for s in pool), 1), 2),
            "fused_rate": round(
                sum(s["fused_rate"] * s["n"] for s in pool) / max(
                    sum(s["n"] for s in pool), 1), 4),
            "span_exact_rate": round(
                sum(s["span_exact_rate"] * s["n"] for s in pool) / max(
                    sum(s["n"] for s in pool), 1), 4),
            "coverage_mean": round(
                sum(s["coverage"] for s in stats) / len(stats), 4),
            "len_p50_mean": round(
                sum(s["len_p50"] for s in pool) / max(len(pool), 1), 1),
            "len_p90_mean": round(
                sum(s["len_p90"] for s in pool) / max(len(pool), 1), 1),
        }
    # 示例: 正则整段回退型 / 多claim型 / 融合型各一
    fallbacks = [e for e in example_pool
                 if len(e["regex_claims"]) == 1
                 and e["regex_claims"][0]["text"].strip() == e["answer"].strip()]
    multi = [e for e in example_pool if len(e["distilled_claims"]) >= 4]
    fused_heavy = sorted(
        example_pool,
        key=lambda e: -sum(1 for c in e["regex_claims"] if c["fused"]))
    picked: list[dict] = []
    for cand, why in ((fallbacks, "正则整体回退(单semantic=整段answer)"),
                      (multi, "切分器多claim原子化"),
                      (fused_heavy, "正则融合claim最重")):
        if cand:
            chosen = cand[0]
            picked.append({
                "instance_id": chosen["instance_id"], "reason": why,
                "answer": chosen["answer"][:400],
                "regex_claims": chosen["regex_claims"][:12],
                "distilled_claims": chosen["distilled_claims"][:12],
            })
    return {"aggregate": agg, "examples": picked}


# ── 2. 下游管线(2分解器 × 2聚合变体) ───────────────────────────────────────


def _localization_stats(rec: dict, result) -> dict:
    """单violation实例的定位统计(口径抄measure_localization_baseline)."""
    ev_by_id = {ev.evidence_id: ev for ev in
                build_qa_input(rec).evidence}
    gold_blocks: set[str] = set()
    for ref in rec.get("gold_evidence_refs") or []:
        ev = ev_by_id.get(str(ref))
        if ev is not None and ev.source_ref.block_id:
            gold_blocks.add(str(ev.source_ref.block_id))
    if result.verdict != "refute":
        return {"detected": 0}
    cited_blocks: set[str] = set()
    n_statement = 0
    for loc in result.localizations:
        for ev_loc in loc.evidence:
            if ev_loc.block_id:
                cited_blocks.add(ev_loc.block_id)
            if ev_loc.row_index >= 0:
                n_statement += 1
    return {
        "detected": 1,
        "localized": 1 if cited_blocks else 0,
        "block_hit": 1 if gold_blocks and (cited_blocks & gold_blocks) else 0,
        "has_gold": 1 if gold_blocks else 0,
        "n_statement_level": n_statement,
        "n_localizations": len(result.localizations),
    }


def claim_statistics(decompose: DecomposeFn,
                     records: list[dict]) -> dict[str, Any]:
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
        "n_instances": n,
        "n_claims": total,
        "claims_per_instance": round(total / n, 2) if n else 0.0,
        "claim_len_avg": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "claim_len_max": max(lengths) if lengths else 0,
        "kind_distribution": dict(sorted(kinds.items())),
    }


def run_config(name: str, decompose: DecomposeFn, patch: bool,
               aggregation: str,
               datasets: dict[str, list[dict]],
               labels: dict[str, dict[str, str]]
               ) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """一个(分解器, 聚合)配置过3数据集(monkeypatch构造前生效, finally恢复)."""
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
        per_dataset: dict[str, Any] = {}
        all_preds: dict[str, dict[str, str]] = {}
        for ds_name in DATASET_ORDER:
            records = datasets[ds_name]
            y_true: list[str] = []
            y_pred: list[str] = []
            preds: dict[str, str] = {}
            unavailable = False
            loc_rows: list[dict] = []
            for record in records:
                request = build_qa_input(record)
                result = module.verify(request)
                preds[request.instance_id] = result.verdict
                if any(claim.method == "nli_residual_unavailable"
                       for claim in result.claim_results):
                    unavailable = True
                if ds_name == "violations17":
                    loc_rows.append(_localization_stats(record, result))
                y_true.append(labels[ds_name][request.instance_id])
                y_pred.append(result.verdict)
            metrics = classification_metrics(y_true, y_pred)
            entry: dict[str, Any] = {
                "metrics": metrics,
                "claim_stats": claim_statistics(decompose, records),
                "per_instance_verdicts": preds,
                "nli_residual_unavailable": unavailable,
            }
            if ds_name == "violations17":
                n_detected = sum(r["detected"] for r in loc_rows)
                entry["localization"] = {
                    "n_detected": n_detected,
                    "n_localized": sum(r.get("localized", 0) for r in loc_rows),
                    "n_block_hit": sum(r.get("block_hit", 0) for r in loc_rows),
                    "n_with_gold": sum(r.get("has_gold", 0) for r in loc_rows),
                    "n_statement_level_refs": sum(
                        r.get("n_statement_level", 0) for r in loc_rows),
                    "block_hit_rate_of_detected": round(
                        sum(r.get("block_hit", 0) for r in loc_rows)
                        / n_detected, 4)
                    if n_detected else 0.0,
                }
            all_preds[ds_name] = preds
            per_dataset[ds_name] = entry
            refute = metrics["per_class"]["refute"]
            stats = entry["claim_stats"]
            line = (f"[{name}] {ds_name:12s} n={len(records):3d} "
                    f"acc={metrics['accuracy']:.4f} "
                    f"mF1={metrics['macro_f1']:.4f} "
                    f"rF1={refute['f1']:.3f} "
                    f"claims={stats['n_claims']}"
                    f"({stats['claims_per_instance']}/inst)")
            if ds_name == "violations17":
                loc = entry["localization"]
                line += (f" 检出={loc['n_detected']}/17 "
                         f"块命中={loc['n_block_hit']}")
            print(line)
            if unavailable:
                print(f"WARNING: {name}/{ds_name}: NLI残差模型不可用"
                      "(结果退化, 检查models/nli/distilled_v1)")
        return per_dataset, all_preds
    finally:
        if patch:
            qa_module.decompose_claims = original


def flip_analysis(datasets: dict[str, list[dict]],
                  labels: dict[str, dict[str, str]],
                  preds_a: dict[str, dict[str, str]],
                  preds_b: dict[str, dict[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for ds_name in DATASET_ORDER:
        gold = labels[ds_name]
        corrected: list[str] = []
        regressed: list[str] = []
        other: list[str] = []
        for record in datasets[ds_name]:
            iid = str(record["instance_id"])
            before = preds_a[ds_name].get(iid)
            after = preds_b[ds_name].get(iid)
            if before is None or after is None or before == after:
                continue
            if after == gold[iid]:
                corrected.append(iid)
            elif before == gold[iid]:
                regressed.append(iid)
            else:
                other.append(iid)
        out[ds_name] = {
            "n_changed": len(corrected) + len(regressed) + len(other),
            "corrected_a_wrong_b_right": corrected,
            "regressed_a_right_b_wrong": regressed,
            "moved_both_wrong": other,
        }
    return out


# ── 报告 ────────────────────────────────────────────────────────────────────


def git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
            text=True, timeout=10, check=False)
        return proc.stdout.strip()[:12] if proc.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def teacher_reference() -> dict[str, Any]:
    """dev-45教师claim统计(probe JSON, 训练可见分布的参考口径)."""
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    return probe["stats"]["llm"]


def print_report(results: dict[str, Any], seg: dict[str, Any],
                 flips: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print("切分质量 (test-46 answers, 只推理): 正则 vs 蒸馏切分器")
    print("=" * 78)
    teacher = teacher_reference()
    print(f"教师参考(dev-45, 训练分布): cl/inst={teacher['claims_per_instance']} "
          f"avglen={teacher['avg_claim_len']} "
          f"fused={teacher['fused_rate'] * 100:.1f}% "
          f"cov={teacher['coverage_mean'] * 100:.1f}%")
    header = f"{'decomposer':12s} {'cl/inst':>8s} {'avglen':>7s} {'fused%':>8s} {'cov%':>7s} {'spanEx%':>8s} {'p50':>5s} {'p90':>5s}"
    print(header)
    print("-" * len(header))
    for side in ("regex", "distilled"):
        s = seg["aggregate"][side]
        print(f"{side:12s} {s['claims_per_instance']:8.2f} "
              f"{s['avg_claim_len']:7.2f} {s['fused_rate'] * 100:7.1f}% "
              f"{s['coverage_mean'] * 100:6.1f}% "
              f"{s['span_exact_rate'] * 100:7.1f}% "
              f"{s['len_p50_mean']:5.1f} {s['len_p90_mean']:5.1f}")
    print("\n" + "=" * 78)
    print("下游管线 (QAConsistencyModule use_experts+use_nli_residual, "
          f"nli={NLI_MODEL_PATH}, gate={NLI_GATE})")
    print("=" * 78)
    header = (f"{'variant':22s} {'dataset':12s} {'n':>4s} {'acc':>7s} "
              f"{'mF1':>7s} {'rF1':>6s} {'rP':>6s} {'rR':>6s} "
              f"{'cl/inst':>8s} {'avglen':>7s}")
    print(header)
    print("-" * len(header))
    for variant in results:
        for ds_name in DATASET_ORDER:
            entry = results[variant][ds_name]
            m = entry["metrics"]
            rc = m["per_class"]["refute"]
            st = entry["claim_stats"]
            print(f"{variant:22s} {ds_name:12s} {st['n_instances']:4d} "
                  f"{m['accuracy']:7.4f} {m['macro_f1']:7.4f} "
                  f"{rc['f1']:6.3f} {rc['precision']:6.3f} "
                  f"{rc['recall']:6.3f} "
                  f"{st['claims_per_instance']:8.2f} "
                  f"{st['claim_len_avg']:7.1f}")
    print("\nviolations17定位 (块级命中gold):")
    for variant in results:
        loc = results[variant]["violations17"]["localization"]
        print(f"  {variant:22s} 检出={loc['n_detected']}/17 "
              f"有定位={loc['n_localized']} 块命中={loc['n_block_hit']} "
              f"hit/检出={loc['block_hit_rate_of_detected']:.3f} "
              f"语句级引用={loc['n_statement_level_refs']}")
    print("\nverdict flips (A_typed → distilled, 同聚合):")
    for agg, flip in flips.items():
        for ds_name in DATASET_ORDER:
            f = flip[ds_name]
            print(f"  [{agg}] {ds_name:12s} changed={f['n_changed']:3d} "
                  f"corrected={len(f['corrected_a_wrong_b_right']):3d} "
                  f"regressed={len(f['regressed_a_right_b_wrong']):3d} "
                  f"both_wrong={len(f['moved_both_wrong']):3d}")


# ── main ────────────────────────────────────────────────────────────────────


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="每数据集只跑前N条(冒烟)")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    datasets = load_datasets()
    if args.limit:
        datasets = {name: recs[:args.limit] for name, recs in datasets.items()}
    labels = load_labels(datasets)
    print("datasets: " + ", ".join(f"{k}={len(v)}" for k, v in datasets.items()))
    print("segmenter:", load_status())
    print(f"nli: {NLI_MODEL_PATH} gate={NLI_GATE}")

    # 1. 切分质量(test-46)
    seg = segmentation_quality(datasets["test46"])

    # 2. 下游: A_typed对照 + distilled, × strict/no_minor_block
    results: dict[str, Any] = {}
    preds_by: dict[str, dict[str, dict[str, str]]] = {}
    for aggregation in AGGREGATIONS:
        for name, decompose, patch in (
                ("A_typed", typed_decompose, False),
                ("distilled", distilled_decompose_claims, True)):
            key = f"{name}_{aggregation}"
            print(f"\n── {key} ──")
            per_dataset, all_preds = run_config(
                key, decompose, patch, aggregation, datasets, labels)
            results[key] = per_dataset
            preds_by[key] = all_preds

    flips = {agg: flip_analysis(
        datasets, labels,
        preds_by[f"A_typed_{agg}"], preds_by[f"distilled_{agg}"])
        for agg in AGGREGATIONS}

    baseline_ok = (
        results["A_typed_strict"]["test46"]["metrics"]["accuracy"]
        == KNOWN["A_typed_strict_test46"]["accuracy"]
        and results["A_typed_strict"]["test46"]["metrics"]["macro_f1"]
        == KNOWN["A_typed_strict_test46"]["macro_f1"])
    if not baseline_ok:
        print("WARNING: A_typed(strict) test46未复现登记基线 "
              f"{KNOWN['A_typed_strict_test46']}")

    report = {
        "experiment": ("D2 eval: distilled claim segmenter vs typed regex "
                       "decomposer (segmentation + downstream + localization)"),
        "recorded": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "config": {
            "module": ("QAConsistencyModule(use_experts=True, "
                       "use_nli_residual=True)"),
            "nli_model_path": NLI_MODEL_PATH,
            "nli_gate": NLI_GATE,
            "aggregations": AGGREGATIONS,
            "segmenter_model": MODEL_PATH,
            "segmenter_status": load_status(),
            "known_baselines": KNOWN,
            "baseline_reproduced": baseline_ok,
        },
        "datasets": {name: len(recs) for name, recs in datasets.items()},
        "isolation_note": ("L0/L1 experts用answer_structure.decompose_answer"
                           "(未patch); 只ablate per-claim分解通道"),
        "segmentation_quality": seg,
        "teacher_reference_dev45": teacher_reference(),
        "downstream": results,
        "flips_a_to_distilled": flips,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print_report(results, seg, flips)
    print(f"\nbaseline_reproduced={baseline_ok}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
