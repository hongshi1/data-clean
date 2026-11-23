r"""claim识别质量评测: 教师claims=gold, 对照正则decompose_claims与蒸馏切分器.

匹配口径(任务定义):
  - 文本重叠: 去空白后 difflib.SequenceMatcher.ratio() >= 0.8;
  - 或 span IoU >= 0.5(双方span可用时);
  - 贪心1-1匹配(按分数降序, 每个gold/pred至多匹配一次);
  - P = 命中pred数/n_pred, R = 命中gold数/n_gold.
过切分: 一个gold被>=2条pred各覆盖自身>=50%(碎片化);
欠切分: 一条pred覆盖>=2个gold各>=50%(合并).

评测切片:
  - dev45     45条教师标注(segmenter_train_v1.json#source=dev45);
              注意v1/v2切分器训练均含dev45(训练内评测, 对比仍同口径);
  - d3train600 600条教师标注(segmenter_train_v2.json#source=d3train);
              v1未见(留出), v2训练含——文件存在时自动加入.

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/eval_claim_recognition.py                     # v1切分器 → claim_recognition_v1.json
  python tools/eval_claim_recognition.py --model models/segmenter/claim_segmenter_v2 --out data/gjb_438c/distillation/claim_recognition_v2.json
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import (  # noqa: E402
    AnswerClaim,
    decompose_claims,
)
from tools.claim_segmenter import load_status, segment_claims  # noqa: E402

TRAIN_V1 = BASE / "data/gjb_438c/distillation/segmenter_train_v1.json"
TRAIN_V2 = BASE / "data/gjb_438c/distillation/segmenter_train_v2.json"
DEFAULT_MODEL = "models/segmenter/claim_segmenter_v1"
OUT_V1 = BASE / "data/gjb_438c/distillation/claim_recognition_v1.json"

TEXT_RATIO_HIT = 0.8
SPAN_IOU_HIT = 0.5
FRAG_CONTAIN = 0.5  # 碎片判定: pred被gold包含比例阈值
MERGE_COVER = 0.5   # 合并判定: pred覆盖gold比例阈值


def git_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=BASE, capture_output=True, text=True,
                              timeout=10, check=False)
        return proc.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def load_gold(path: Path, source: str) -> list[dict[str, Any]]:
    """训练标注JSON → 指定source的gold记录(claims含find_span)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = [rec for rec in doc["answers"]
           if rec.get("source") == source and rec.get("llm_status") == "ok"]
    if not out:
        raise ValueError(f"{path}中source={source}无llm_status=ok记录")
    return out


def _norm(text: str) -> str:
    return "".join(text.split())


def _span_of(claim: AnswerClaim, answer: str) -> list[int] | None:
    """pred claim的有效span(模型span优先, 缺失时find定位)."""
    span = getattr(claim, "span", None)
    if span and 0 <= span[0] < span[1] <= len(answer):
        if answer[span[0]:span[1]] == claim.text:
            return [int(span[0]), int(span[1])]
    pos = answer.find(claim.text) if claim.text else -1
    return [pos, pos + len(claim.text)] if pos != -1 else None


def _iou(a: list[int] | None, b: list[int] | None) -> float:
    if not a or not b:
        return 0.0
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def _contained(inner: list[int] | None, outer: list[int] | None) -> float:
    """inner被outer覆盖的比例(inner/outer均为字符区间)."""
    if not inner or not outer:
        return 0.0
    inter = max(0, min(inner[1], outer[1]) - max(inner[0], outer[0]))
    length = inner[1] - inner[0]
    return inter / length if length > 0 else 0.0


def match_pair(gold_text: str, gold_span: list[int] | None,
               pred_text: str, pred_span: list[int] | None,
               answer: str) -> dict[str, float]:
    """单对(gold, pred)的匹配分数(text_ratio / span_iou / hit)."""
    ratio = difflib.SequenceMatcher(
        None, _norm(gold_text), _norm(pred_text)).ratio()
    if not gold_span and pred_span:
        pos = answer.find(_norm(gold_text)) if _norm(gold_text) else -1
        gold_span = [pos, pos + len(_norm(gold_text))] if pos != -1 else None
    iou = _iou(gold_span, pred_span)
    hit = ratio >= TEXT_RATIO_HIT or iou >= SPAN_IOU_HIT
    return {"text_ratio": round(ratio, 4), "span_iou": round(iou, 4),
            "hit": hit}


def eval_variant(records: list[dict[str, Any]],
                 predict: Any) -> dict[str, Any]:
    """一组记录上的claim识别指标(predict(question, answer) -> list[claim]).

    predict返回list[dict(text, span|None)].
    """
    n_gold = n_pred = n_hit_gold = n_hit_pred = 0
    n_over_seg = n_under_seg = 0
    per_instance: list[dict[str, Any]] = []
    pred_lens: list[int] = []
    for rec in records:
        answer = rec["answer"]
        golds = rec["claims"]
        preds = predict(rec["question"], answer)
        pairs: list[tuple[float, int, int, bool]] = []
        for gi, gold in enumerate(golds):
            for pi, pred in enumerate(preds):
                m = match_pair(gold["text"], gold.get("find_span"),
                               pred["text"], pred.get("span"), answer)
                score = max(m["text_ratio"], m["span_iou"])
                if m["hit"]:
                    pairs.append((score, gi, pi, True))
        pairs.sort(key=lambda x: -x[0])
        used_g: set[int] = set()
        used_p: set[int] = set()
        hit_g: set[int] = set()
        hit_p: set[int] = set()
        for _score, gi, pi, _hit in pairs:
            if gi in used_g or pi in used_p:
                continue
            used_g.add(gi)
            used_p.add(pi)
            hit_g.add(gi)
            hit_p.add(pi)
        n_gold += len(golds)
        n_pred += len(preds)
        n_hit_gold += len(hit_g)
        n_hit_pred += len(hit_p)
        # 过切分: gold被>=2条pred各含自身>=50%地碎片化
        for gold in golds:
            frag = sum(1 for pred in preds
                       if _contained(pred.get("span"), gold.get("find_span"))
                       >= FRAG_CONTAIN)
            if frag >= 2:
                n_over_seg += 1
        # 欠切分: pred覆盖>=2个gold各>=50%
        for pred in preds:
            merged = sum(1 for gold in golds
                         if _contained(gold.get("find_span"), pred.get("span"))
                         >= MERGE_COVER)
            if merged >= 2:
                n_under_seg += 1
        pred_lens.extend(len(p["text"]) for p in preds)
        per_instance.append({
            "instance_id": rec["instance_id"],
            "n_gold": len(golds), "n_pred": len(preds),
            "n_hit_gold": len(hit_g), "n_hit_pred": len(hit_p),
            "over_seg": sum(1 for gold in golds
                            if sum(1 for pred in preds
                                   if _contained(pred.get("span"),
                                                 gold.get("find_span"))
                                   >= FRAG_CONTAIN) >= 2),
            "under_seg": sum(1 for pred in preds
                             if sum(1 for gold in golds
                                    if _contained(gold.get("find_span"),
                                                  pred.get("span"))
                                    >= MERGE_COVER) >= 2),
        })
    precision = n_hit_pred / n_pred if n_pred else 0.0
    recall = n_hit_gold / n_gold if n_gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    n_inst = len(records)
    return {
        "n_instances": n_inst,
        "n_gold_claims": n_gold,
        "n_pred_claims": n_pred,
        "claims_per_instance_pred": round(n_pred / n_inst, 2) if n_inst else 0.0,
        "claims_per_instance_gold": round(n_gold / n_inst, 2) if n_inst else 0.0,
        "claim_precision": round(precision, 4),
        "claim_recall": round(recall, 4),
        "claim_f1": round(f1, 4),
        "over_seg_rate": round(n_over_seg / n_gold, 4) if n_gold else 0.0,
        "under_seg_rate": round(n_under_seg / n_pred, 4) if n_pred else 0.0,
        "over_seg_count": n_over_seg,
        "under_seg_count": n_under_seg,
        "pred_len_avg": round(sum(pred_lens) / len(pred_lens), 2)
        if pred_lens else 0.0,
        "per_instance": per_instance,
    }


def regex_predict(question: str, answer: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for claim in decompose_claims(question, answer):
        out.append({"text": claim.text, "span": _span_of(claim, answer)})
    return out


def make_segmenter_predict(model_path: str,
                           boundary_gate: float = 0.0) -> Any:
    def predict(question: str, answer: str) -> list[dict[str, Any]]:
        del question
        out: list[dict[str, Any]] = []
        for item in segment_claims(answer, model_path=model_path,
                                   boundary_gate=boundary_gate):
            out.append({"text": item["text"], "span": item["span"]})
        return out

    return predict


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", default=str(OUT_V1))
    parser.add_argument("--boundary-gate", type=float, default=0.0,
                        help="弱B置信度门限(argmax=B但P(B)<gate→I, "
                             "v2推荐0.75; 0=关闭)")
    args = parser.parse_args()

    slices: dict[str, list[dict[str, Any]]] = {
        "dev45": load_gold(TRAIN_V1, "dev45")}
    if TRAIN_V2.exists():
        slices["d3train600"] = load_gold(TRAIN_V2, "d3train")

    status = load_status(args.model)
    if status["mode"] == "unavailable":
        raise SystemExit(f"切分器不可用({args.model}): {status['error']}")

    variants = {
        "regex": regex_predict,
        "segmenter": make_segmenter_predict(args.model,
                                            args.boundary_gate),
    }
    # τ-sweep诊断(同模型不同gate, 供报告; 官方数字用--boundary-gate)
    sweep: list[dict[str, Any]] = []
    if args.boundary_gate > 0.0:
        for tau in (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9):
            row: dict[str, Any] = {"boundary_gate": tau}
            for slice_name, records in slices.items():
                entry = eval_variant(
                    records, make_segmenter_predict(args.model, tau))
                row[slice_name] = {k: entry[k] for k in
                                   ("claim_precision", "claim_recall",
                                    "claim_f1", "claims_per_instance_pred")}
            sweep.append(row)
    t0 = time.time()
    results: dict[str, Any] = {}
    for slice_name, records in slices.items():
        results[slice_name] = {}
        print(f"\n=== slice {slice_name} (n={len(records)}) ===")
        header = (f"{'variant':<11s} {'P':>7s} {'R':>7s} {'F1':>7s} "
                  f"{'cl/inst':>8s} {'gold/inst':>10s} {'过切分%':>8s} "
                  f"{'欠切分%':>8s} {'均长':>6s}")
        print(header)
        print("-" * len(header))
        for name, predict in variants.items():
            entry = eval_variant(records, predict)
            results[slice_name][name] = entry
            print(f"{name:<11s} {entry['claim_precision']:7.4f} "
                  f"{entry['claim_recall']:7.4f} {entry['claim_f1']:7.4f} "
                  f"{entry['claims_per_instance_pred']:8.2f} "
                  f"{entry['claims_per_instance_gold']:10.2f} "
                  f"{entry['over_seg_rate'] * 100:7.1f}% "
                  f"{entry['under_seg_rate'] * 100:7.1f}% "
                  f"{entry['pred_len_avg']:6.1f}")

    doc = {
        "experiment": ("claim recognition eval: teacher claims=gold vs "
                       "regex decompose_claims & distilled segmenter"),
        "ts": round(time.time(), 1),
        "git_sha": git_sha(),
        "segmenter_model": args.model,
        "segmenter_status": status,
        "boundary_gate": args.boundary_gate,
        "boundary_gate_rule": ("argmax为B但P(B)<gate → 视为I(弱边界与前"
                               "claim合并); gate=0关闭; 0.75经τ-sweep按"
                               "claim识别F1+教师粒度匹配(cl/inst≈10.3)"
                               "选定, 非test46标签调参"),
        "boundary_gate_sweep": sweep,
        "matching": {
            "text_ratio": "去空白后difflib SequenceMatcher.ratio()",
            "text_ratio_hit": TEXT_RATIO_HIT,
            "span_iou_hit": SPAN_IOU_HIT,
            "rule": "text_ratio>=0.8 OR span_iou>=0.5; 贪心1-1匹配",
            "over_seg": "gold被>=2条pred各覆盖pred自身>=50%(碎片化)",
            "under_seg": "pred覆盖>=2个gold各>=50%(合并)",
        },
        "caveat": ("dev45在v1/v2训练集中(训练内评测, v1/v2同口径可对比); "
                   "d3train600对v1留出、v2训练含; test46见下游评测"),
        "gold_sources": {
            "dev45": str(TRAIN_V1),
            "d3train600": str(TRAIN_V2) if TRAIN_V2.exists() else None,
        },
        "elapsed_seconds": round(time.time() - t0, 1),
        "results": results,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n输出: {out} (elapsed {doc['elapsed_seconds']}s)")


if __name__ == "__main__":
    main()
