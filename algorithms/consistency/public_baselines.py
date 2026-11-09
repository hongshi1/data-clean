"""五个代表性外部baseline (一致性校验论文表的真正外部对比行).

设计: 纯函数内核 + 惰性模型加载, 模块顶层零I/O/零重依赖
(torch/transformers/llm_client只在函数内import; llm_client→ai_config
import期读.env, 故必须惰性).

行定义(与tools/eval_public_matrix.py的矩阵一一对应):
  bge_centroid     BGE三元中心法: pair特征=[u_p; u_h; u_p⊙u_h; |u_p−u_h|]
                   (各分量L2归一后拼接再归一), fit集按类求归一化均值中心,
                   test取argmax余弦. 嵌入对称性无法区分矛盾/中立的结构性
                   弱点如实暴露(不做双阈值粉饰), 如实叫"近邻中心分类器".
  erlangshen_zero  Erlangshen-Roberta-330M-NLI(中文NLI代表模型)零样本直推
  mdeberta_zero    mDeBERTa-v3-base-xnli-multilingual-nli-2mil7零样本直推
                   (与nli_local的零样本路径同一checkpoint, 直推不经过级联)
  cmnli_finetuned  mDeBERTa + CMNLI公开监督数据微调
                   (tools/train_cmnli_nli.py产出, "公开数据最强外部baseline",
                   与EGT域数据微调形成公开/域对照)
  glm_direct       GLM-5.3直推: 一pair一prompt三态判定
                   (llm_json cache=True, 参数与llm_residual/B2通道一致)

输入契约: pairs = [{"premise", "hypothesis", ...}, ...] (label由调用方持有),
输出: verdict列表 ∈ {support, refute, not_in_evidence} (与eval_lib.LABELS一致).

本地NLI推理: 惰性加载+模块级缓存(同checkpoint+max_length不重复加载),
失败显式RuntimeError(不静默吞), eval模式+no_grad确定性; 空premise/hypothesis
→ not_in_evidence(不发模型, 与nli_local约定一致).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

from algorithms.consistency.nli_local import MODELS, normalize_label

BASE = Path(__file__).resolve().parents[2]

VERDICTS = ("support", "refute", "not_in_evidence")
NLI_TO_VERDICT = {"entailment": "support", "contradiction": "refute",
                  "neutral": "not_in_evidence"}

# 本地checkpoint目录: erlangshen/mdeberta沿用nli_local注册表;
# cmnli_finetuned = CMNLI公开监督微调产出(新增, 不动nli_local)
CMNLI_FINETUNED_DIR = str(BASE / "models" / "nli" / "cmnli_finetuned_mdeberta")
BASELINE_MODEL_DIRS: dict[str, str] = {
    "erlangshen_zero": MODELS["erlangshen-330m"]["dir"],
    "mdeberta_zero": MODELS["mdeberta"]["dir"],
    "cmnli_finetuned": CMNLI_FINETUNED_DIR,
    "egt_finetuned_v2": MODELS["egt_finetuned_v2"]["dir"],
    "distilled_v1": MODELS["distilled_v1"]["dir"],
}

_MAX_LEN = 512
_BATCH_GPU = 16
_BATCH_CPU = 8


# ═══ BGE三元中心法 ═════════════════════════════════════════════════════════


def _l2norm(vec: list[float]) -> list[float]:
    norm = sum(x * x for x in vec) ** 0.5
    if norm <= 0.0:
        return list(vec)
    return [x / norm for x in vec]


def pair_feature(u_p: list[float], u_h: list[float]) -> list[float]:
    """BGE pair特征: [u_p; u_h; u_p⊙u_h; |u_p−u_h|], 各分量与拼接整体都L2归一.

    u_p/u_h为L2归一的BGE向量(1024维); 逐元素积与差刻画交互(对齐/相反),
    供近邻中心分类器区分三类 (InferSent式pair特征的最小版).
    """
    if not u_p or not u_h or len(u_p) != len(u_h):
        raise ValueError(f"pair_feature输入向量非法: len(u_p)={len(u_p)}, "
                         f"len(u_h)={len(u_h)}")
    p = _l2norm(u_p)
    h = _l2norm(u_h)
    prod = _l2norm([a * b for a, b in zip(p, h)])
    diff = _l2norm([abs(a - b) for a, b in zip(p, h)])
    return _l2norm(p + h + prod + diff)


def fit_centroids(features_by_class: dict[str, list[list[float]]]
                  ) -> dict[str, list[float]]:
    """fit集特征 → 各类归一化均值中心 (纯函数, 类缺失报错不静默)."""
    centroids: dict[str, list[float]] = {}
    dim: int | None = None
    for label in VERDICTS:
        feats = features_by_class.get(label) or []
        if not feats:
            raise ValueError(f"BGE中心法fit集缺类{label!r}(三态须全有)")
        if dim is None:
            dim = len(feats[0])
        if any(len(f) != dim for f in feats):
            raise ValueError("fit集特征维度不一致")
        mean = [sum(f[i] for f in feats) / len(feats) for i in range(dim)]
        centroids[label] = _l2norm(mean)
    return centroids


def nearest_centroid(feature: list[float],
                     centroids: dict[str, list[float]]
                     ) -> tuple[str, dict[str, float]]:
    """特征→(argmax余弦的类, 各类相似度). 特征/中心均为单位向量."""
    scores = {label: sum(a * b for a, b in zip(feature, center))
              for label, center in centroids.items()}
    best = max(VERDICTS, key=lambda label: (scores[label], label))
    return best, {label: round(value, 6) for label, value in scores.items()}


def bge_embed_pairs(bge: Any, pairs: Sequence[dict]) -> dict[str, list[float]]:
    """经注入的BgeLocal实例编码全部非空premise/hypothesis (去重回填).

    空premise/hypothesis不送嵌入(与nli_verdicts的保守NIE约定一致),
    调用方对空输入直接判not_in_evidence; 非空文本向量缺失→显式报错.
    """
    texts: list[str] = []
    for pair in pairs:
        for key in ("premise", "hypothesis"):
            text = str(pair[key]).strip()
            if text:
                texts.append(text)
    vectors = bge.embed(texts)
    empty = [t for t in dict.fromkeys(texts) if not vectors.get(t)]
    if empty:
        raise RuntimeError(f"BGE embedding失败({len(empty)}条空向量, "
                           f"bge.last_error={bge.last_error!r}), 例: "
                           f"{empty[0][:60]!r}")
    return vectors


def _pair_texts(pair: dict) -> tuple[str, str]:
    return (str(pair["premise"]).strip(), str(pair["hypothesis"]).strip())


def bge_centroid_verdicts(pairs: Sequence[dict], bge: Any,
                          centroids: dict[str, list[float]]
                          ) -> list[str]:
    """BGE三元中心法推理: (premise,hypothesis)→三态verdict列表.

    空premise/hypothesis(无证据文本)→保守not_in_evidence, 与本地NLI直推
    同一约定(如91QA的S1QA-062无冻结证据).
    """
    vectors = bge_embed_pairs(bge, pairs)
    out: list[str] = []
    for pair in pairs:
        premise, hypothesis = _pair_texts(pair)
        if not premise or not hypothesis:
            out.append("not_in_evidence")
            continue
        feature = pair_feature(vectors[premise], vectors[hypothesis])
        verdict, _scores = nearest_centroid(feature, centroids)
        out.append(verdict)
    return out


def bge_fit_from_pairs(bge: Any, fit_pairs: Sequence[dict]
                       ) -> dict[str, list[float]]:
    """fit集 → 三类中心 (embed + fit; fit协议由调用方落盘记录).

    空premise/hypothesis的fit样本跳过(无信号不入中心); 某类因此清空时
    由fit_centroids显式报错.
    """
    vectors = bge_embed_pairs(bge, fit_pairs)
    features_by_class: dict[str, list[list[float]]] = {
        label: [] for label in VERDICTS}
    for pair in fit_pairs:
        premise, hypothesis = _pair_texts(pair)
        if not premise or not hypothesis:
            continue
        feature = pair_feature(vectors[premise], vectors[hypothesis])
        features_by_class[str(pair["label"])].append(feature)
    return fit_centroids(features_by_class)


# ═══ 本地NLI直推 (erlangshen/mdeberta零样本, cmnli微调, egt对照) ═════════

_MODEL_CACHE: dict[str, dict[str, Any]] = {}


def _load_nli(model_dir: str, max_length: int) -> dict[str, Any]:
    """惰性加载NLI checkpoint (模块级缓存; 失败显式RuntimeError)."""
    cache_key = f"{model_dir}@{max_length}"
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
    entry: dict[str, Any] = {"error": ""}
    try:
        import torch
        from transformers import (AutoModelForSequenceClassification,
                                  AutoTokenizer)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(model_dir,
                                                  local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_dir, local_files_only=True)
        model.to(device)
        model.eval()
        entry = {"mode": device, "tokenizer": tokenizer, "model": model,
                 "torch": torch, "id2label": {int(k): normalize_label(str(v))
                                              for k, v in
                                              model.config.id2label.items()},
                 "error": ""}
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        entry = {"mode": "unavailable",
                 "error": f"{type(exc).__name__}: {exc}"}
    _MODEL_CACHE[cache_key] = entry
    if entry["error"]:
        raise RuntimeError(f"NLI模型加载失败({model_dir}): {entry['error']}")
    return entry


def _probs_to_verdict(probs: dict[str, float]) -> str:
    label = max(probs, key=lambda k: (probs[k], k))
    return NLI_TO_VERDICT.get(label, "not_in_evidence")


def _infer_probs(entry: dict[str, Any], pairs: list[tuple[str, str]],
                 max_length: int) -> list[dict[str, float]]:
    torch = entry["torch"]
    batch = _BATCH_GPU if entry["mode"] == "cuda" else _BATCH_CPU
    out: list[dict[str, float]] = []
    for start in range(0, len(pairs), batch):
        chunk = pairs[start:start + batch]
        enc = entry["tokenizer"]([p for p, _ in chunk], [h for _, h in chunk],
                                 padding=True, truncation="longest_first",
                                 max_length=max_length, return_tensors="pt")
        enc = {k: v.to(entry["mode"]) for k, v in enc.items()}
        with torch.no_grad():
            logits = entry["model"](**enc).logits
            probs = torch.softmax(logits, dim=-1).float().cpu().tolist()
        for row in probs:
            named = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
            for idx, prob in enumerate(row):
                label = entry["id2label"].get(idx, "neutral")
                named[label] = named.get(label, 0.0) + float(prob)
            out.append(named)
    return out


def nli_verdicts(pairs: Sequence[dict], model_dir: str,
                 *, max_length: int = _MAX_LEN) -> list[str]:
    """(premise, hypothesis)对列表 → 三态verdict列表 (本地NLI直推).

    max_length=512: 公开集短句自然填充, 自建集1500字符premise按512截断
    (与nli_residual推理侧一致). 空premise/hypothesis→NIE(不发模型).
    """
    valid: list[tuple[int, tuple[str, str]]] = [
        (i, (str(pair["premise"]).strip(), str(pair["hypothesis"]).strip()))
        for i, pair in enumerate(pairs)
        if str(pair["premise"]).strip() and str(pair["hypothesis"]).strip()]
    out = ["not_in_evidence"] * len(pairs)
    if not valid:
        return out
    entry = _load_nli(model_dir, max_length)
    probs = _infer_probs(entry, [pair for _, pair in valid], max_length)
    for (index, _), prob in zip(valid, probs):
        out[index] = _probs_to_verdict(prob)
    return out


# ═══ GLM-5直推 (公开pair三态判定) ═════════════════════════════════════════

_SYSTEM_PUBLIC = (
    "你是中文自然语言推理(NLI)三态判定器。给定前提(premise)与假设(hypothesis)，"
    "判定：support（前提蕴含假设：由前提可推出假设为真）/"
    "refute（前提与假设矛盾：由前提可推出假设为假）/"
    "not_in_evidence（中立：前提不足以判定假设真假）。"
    "严格只依据前提文本判定，不引入外部世界知识改写判定方向；"
    "前提与假设话题无关或前提未覆盖假设内容时判not_in_evidence。"
    "只输出JSON。"
)

_SPEC_PUBLIC = (
    '输出JSON：{"verdict": "support|refute|not_in_evidence", '
    '"rationale": "一句话理由", "confidence": 0.9}。'
)

_RETRY_PUBLIC = (
    "\n\n上一次输出无法解析。请严格只输出一个JSON对象，"
    "不要markdown代码块、不要任何多余文字。"
)


def build_public_pair_prompt(premise: str, hypothesis: str) -> str:
    """公开pair直推prompt (纯函数, 可测; 同输入→同prompt→缓存命中)."""
    return "\n".join([
        "【前提premise】", str(premise).strip(), "",
        "【假设hypothesis】", str(hypothesis).strip(), "",
        _SPEC_PUBLIC,
    ])


def parse_public_verdict(payload: Any) -> str:
    """LLM JSON输出→三态verdict; 非法/空→空串(调用方重试)."""
    if not isinstance(payload, dict) or not payload:
        return ""
    verdict = re.sub(r"\s+", "_", str(payload.get("verdict", "")).strip().lower())
    return verdict if verdict in VERDICTS else ""


def _call_llm_json(prompt: str) -> Any:
    """一次缓存JSON调用 (惰性import: ai_config import期读.env)."""
    from tools.llm_teacher import llm_json_teacher

    payload, _model, _hit = llm_json_teacher(
        prompt, _SYSTEM_PUBLIC,
        max_tokens=16000, temperature=0.1,
        extra_payload={
            "response_contract": "json_final_content_v2",
            "reasoning_effort": "low",
        })
    return payload


def judge_public_pair(premise: str, hypothesis: str) -> dict[str, str]:
    """一对(premise, hypothesis)→{verdict, method, rationale}.

    llm_json(cache=True)保证可复现; 失败重试一次(更严格后缀), 再失败
    显式记为glm_direct_failed的保守NIE(不静默吞, rationale带失败原因).
    """
    prompt = build_public_pair_prompt(premise, hypothesis)
    note = ""
    for suffix in ("", _RETRY_PUBLIC):
        try:
            payload = _call_llm_json(prompt + suffix)
        except Exception as exc:  # 重试一次后保守NIE; 失败原因显式记录
            note = f"{type(exc).__name__}: {exc}"
            continue
        verdict = parse_public_verdict(payload)
        if verdict:
            rationale = ""
            if isinstance(payload, dict):
                rationale = str(payload.get("rationale", "")).strip()[:200]
            return {"verdict": verdict, "method": "glm_direct",
                    "rationale": rationale}
        note = "LLM输出无法解析为三态verdict"
    return {"verdict": "not_in_evidence", "method": "glm_direct_failed",
            "rationale": note[:200]}


def glm_public_verdicts(pairs: Sequence[dict]) -> list[str]:
    """公开集LLM直推: 一pair一调用 (缓存)."""
    return [judge_public_pair(str(pair["premise"]),
                              str(pair["hypothesis"]))["verdict"]
            for pair in pairs]


__all__ = [
    "BASELINE_MODEL_DIRS",
    "CMNLI_FINETUNED_DIR",
    "NLI_TO_VERDICT",
    "VERDICTS",
    "bge_centroid_verdicts",
    "bge_embed_pairs",
    "bge_fit_from_pairs",
    "build_public_pair_prompt",
    "fit_centroids",
    "glm_public_verdicts",
    "judge_public_pair",
    "nearest_centroid",
    "nli_verdicts",
    "pair_feature",
    "parse_public_verdict",
]
