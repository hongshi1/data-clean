"""L5: 一致性校验 — 基于Erlangshen-Roberta-330M-NLI的模型裁决.

替代规则if-else，用NLI模型做最终一致性判定：
  premise(视觉事实) + hypothesis(QA声称) → entailment/neutral/contradiction
  映射: entailment→support, contradiction→refute, neutral→NIE
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_NLI_DIR = ROOT / "models" / "nli" / "Erlangshen-Roberta-330M-NLI"

_MODEL = None
_TOKENIZER = None


def _load_model():
    global _MODEL, _TOKENIZER
    if _MODEL is None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        _TOKENIZER = AutoTokenizer.from_pretrained(str(_NLI_DIR), local_files_only=True)
        _MODEL = AutoModelForSequenceClassification.from_pretrained(
            str(_NLI_DIR),
            local_files_only=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else "cpu",
        )
    return _MODEL, _TOKENIZER


def verify_claim(premise: str, hypothesis: str) -> dict[str, Any]:
    """用NLI模型判断视觉事实(premise)是否支持QA声称(hypothesis).

    Returns:
        {
            "label": "entailment|neutral|contradiction",
            "scores": {"entailment": 0.85, "neutral": 0.10, "contradiction": 0.05},
            "verdict": "support|NIE|refute",
            "confidence": 0.85,
        }
    """
    model, tokenizer = _load_model()
    import torch

    inputs = tokenizer(
        premise,
        hypothesis,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    ).to(model.device)

    with torch.inference_mode():
        logits = model(**inputs).logits[0]
        probs = torch.softmax(logits, dim=-1).cpu()

    # Erlangshen NLI: 0=CONTRADICTION, 1=NEUTRAL, 2=ENTAILMENT (verified from config.json)
    label_map = {0: "contradiction", 1: "neutral", 2: "entailment"}
    verdict_map = {"entailment": "support", "neutral": "NIE", "contradiction": "refute"}

    pred_idx = int(probs.argmax())
    label = label_map.get(pred_idx, "neutral")
    verdict = verdict_map.get(label, "NIE")

    return {
        "premise": premise,
        "hypothesis": hypothesis,
        "label": label,
        "scores": {
            "contradiction": round(float(probs[0]), 4),
            "neutral": round(float(probs[1]), 4),
            "entailment": round(float(probs[2]), 4),
        },
        "verdict": verdict,
        "confidence": round(float(probs[pred_idx]), 4),
    }


def build_premise_from_visual(visual_summary: dict[str, Any]) -> str:
    """将视觉检测结果转化为NLI的premise文本."""
    parts = []
    person_count = visual_summary.get("person_count", 0)
    if person_count:
        parts.append(f"画面中有{person_count}人")

    ppe_count = visual_summary.get("ppe_detections", 0)
    if ppe_count:
        wearing = visual_summary.get("wearing_count", 0)
        not_wearing = visual_summary.get("not_wearing_count", 0)
        if wearing:
            parts.append(f"其中{wearing}人佩戴了安全帽")
        if not_wearing:
            parts.append(f"{not_wearing}人未佩戴安全帽")
        if wearing and not_wearing:
            parts.append("存在部分人员佩戴、部分人员未佩戴的情况")
        elif wearing and not not_wearing:
            parts.append("所有检测到的人员均佩戴了安全帽")
        elif not_wearing and not wearing:
            parts.append("所有检测到的人员均未佩戴安全帽")

    pose_summary = visual_summary.get("pose_summary", "")
    if pose_summary:
        parts.append(pose_summary)

    return "。".join(parts) + "。" if parts else "画面信息不足。"


def run_nli_verification(
    visual_summary: dict[str, Any],
    qa_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """对每个QA claim运行NLI验证，汇总最终verdict.

    Args:
        visual_summary: 视觉检测汇总 (person_count, ppe_detections, wearing_count, etc.)
        qa_claims: QA语义命题列表，每个包含 hypothesis 文本
    """
    premise = build_premise_from_visual(visual_summary)
    results = []

    for claim in qa_claims:
        hypothesis = claim.get("hypothesis", "")
        if not hypothesis:
            continue
        nli_result = verify_claim(premise, hypothesis)
        nli_result["claim_id"] = claim.get("claim_id", "unknown")
        results.append(nli_result)

    # Overall verdict: worst case across all claims
    if any(r["verdict"] == "refute" for r in results):
        overall = "refute"
    elif any(r["verdict"] == "NIE" for r in results):
        overall = "NIE"
    elif results and all(r["verdict"] == "support" for r in results):
        overall = "support"
    else:
        overall = "NIE"

    return {
        "premise": premise,
        "per_claim_results": results,
        "overall_verdict": overall,
        "method": "erlangshen-roberta-330m-nli",
        "model": str(_NLI_DIR),
    }
