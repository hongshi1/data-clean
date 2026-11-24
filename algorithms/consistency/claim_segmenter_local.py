r"""D2蒸馏claim切分器推理核心: 字符级B/I/O边界分类 → 原子claim解码.

M119迁移(99号方案P1): 本模块自``tools/claim_segmenter.py``原样迁入
(行为逐字保持), tools侧改为re-export shim保持向后兼容——algorithms/
侧的claim_typed_bridge需要切分器推理核心, 而algorithms/不import tools/.

推理端切分器(GLM-5.3教师标注蒸馏, 基座chinese-roberta-wwm-ext):
  - 任务: 每个answer字符标 {B=claim首字符, I=claim内部, O=未覆盖};
  - 解码: B起claim, I续claim, O断claim; claim文本=answer[起:止].strip(),
    span=解码区间本身(非find, M86: 不蒸索引);
  - 长answer(>512 token)滑窗推理(取各窗口中部覆盖, 确定性);
  - 模型惰性加载+模块级缓存(模式抄algorithms/consistency/nli_residual.py),
    import期零I/O; 加载失败显式抛错(不静默).

诚实契约: 训练数据=dev45+violations17+crossdoc150(212 answer,
tools/distill_segmenter_labels.py); test-46训练不可见.

接口:
  segment_claims(answer) -> list[dict]  每条{text, span, boundary_conf}
  distilled_decompose_claims(question, answer) -> list[AnswerClaim]
    (签名兼容qa_module.decompose_claims以便monkeypatch; question忽略;
     kind一律"semantic"——M82 C实验: typed通道跨域为负资产)
"""
from __future__ import annotations

from dataclasses import fields
from typing import Any

#: 字符标签体系(与tools/distill_segmenter_labels.py共享)
LABEL_B, LABEL_I, LABEL_O = "B", "I", "O"
LABELS = (LABEL_B, LABEL_I, LABEL_O)

#: 默认checkpoint(相对repo根; 与nli_residual同风格; v1=迁移前默认)
MODEL_PATH = "models/segmenter/claim_segmenter_v1"
_MAX_LENGTH = 512
#: 滑窗: 窗口token数(含specials)=512, 步进384 token(重叠≈126)
_WINDOW_STRIDE = 384
#: 边界置信度口径: claim起点(去空白后)字符的P(B)
_BOUNDARY_CONF_DIGITS = 4

_MODEL_CACHE: dict[str, dict[str, Any]] = {}


# ── 纯函数(训练端复用, 无模型依赖) ───────────────────────────────────────────


def char_labels_from_claims(answer: str,
                            find_spans: list[tuple[int, int]]) -> list[str]:
    """claim的find()区间序列 → B/I/O字符标签(重叠按起点序, B不被I覆盖)."""
    labels = [LABEL_O] * len(answer)
    for start, end in sorted(find_spans):
        if 0 <= start < end <= len(answer):
            labels[start] = LABEL_B
            for i in range(start + 1, min(end, len(answer))):
                if labels[i] != LABEL_B:
                    labels[i] = LABEL_I
    return labels


def decode_char_labels(labels: list[str]) -> list[tuple[int, int]]:
    """B/I/O字符标签 → claim区间列表(B起, I续, O/B断).

    孤儿I(前为O的I)按O处理: 训练标签构造(char_labels_from_claims)中
    I只存在于claim内部, 不存在孤儿I; 推理中的孤儿I是多字符token标签
    映射/模型噪声, 不容错为claim起点.
    """
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for index, label in enumerate(labels):
        if label == LABEL_B:
            if start is not None:
                spans.append((start, index))
            start = index
        elif label == LABEL_I:
            if start is not None:
                continue  # claim内部继续
            # 孤儿I: 视为O(见docstring)
        else:
            if start is not None:
                spans.append((start, index))
                start = None
    if start is not None:
        spans.append((start, len(labels)))
    return [(s, e) for s, e in spans if e > s]


# ── 模型加载(惰性+缓存; 失败显式, 不静默) ───────────────────────────────────


def _load_model(model_path: str) -> dict[str, Any]:
    if model_path in _MODEL_CACHE:
        return _MODEL_CACHE[model_path]
    entry: dict[str, Any] = {"mode": "unavailable", "error": ""}
    try:
        import torch
        from transformers import (AutoModelForTokenClassification,
                                  AutoTokenizer)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = (torch.float16 if device == "cuda" else torch.float32)
        tokenizer = AutoTokenizer.from_pretrained(model_path,
                                                  local_files_only=True)
        model = AutoModelForTokenClassification.from_pretrained(
            model_path, local_files_only=True, torch_dtype=dtype)
        model.to(device)
        model.eval()
        entry = {
            "mode": device,
            "tokenizer": tokenizer,
            "model": model,
            "torch": torch,
            "id2label": {int(k): str(v).upper() for k, v in
                         model.config.id2label.items()},
            "error": "",
        }
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"
    _MODEL_CACHE[model_path] = entry
    return entry


def load_status(model_path: str = MODEL_PATH) -> dict[str, str]:
    """加载状态诊断(评测端显式记录用; 触发惰性加载)."""
    entry = _load_model(model_path)
    return {"mode": entry["mode"], "error": entry["error"]}


# ── 推理 ────────────────────────────────────────────────────────────────────


def _window_char_probs(entry: dict[str, Any],
                       answer: str) -> list[dict[str, float]]:
    """滑窗推理 → 每字符{B,I,O}概率(各窗口取中部覆盖, 确定性).

    全answer一次性编码(含offset), 窗口在token空间切片; 窗内token i的
    概率取logits[i+1](跳过[CLS], 窗长≤510保证窗内无截断).
    """
    torch = entry["torch"]
    tokenizer = entry["tokenizer"]
    id2label = entry["id2label"]
    device = entry["mode"]
    encoded_full = tokenizer(answer, add_special_tokens=False,
                             return_offsets_mapping=True)
    ids = encoded_full["input_ids"]
    offsets = encoded_full["offset_mapping"]
    span = _MAX_LENGTH - 2  # [CLS]/[SEP]
    step = _WINDOW_STRIDE - 2
    probs: list[dict[str, float] | None] = [None] * len(answer)
    centers: list[int] = [-1] * len(answer)
    cls_id, sep_id = tokenizer.cls_token_id, tokenizer.sep_token_id
    for w_start in range(0, max(len(ids), 1), step):
        w_end = min(w_start + span, len(ids))
        if w_end <= w_start:
            break
        window_ids = ids[w_start:w_end]
        # [CLS] w [SEP] 手工拼装(transformers 5移除prepare_for_model)
        input_ids = [cls_id] + list(window_ids) + [sep_id]
        model_input = {
            "input_ids": torch.tensor([input_ids], dtype=torch.long),
            "token_type_ids": torch.tensor(
                [[0] * len(input_ids)], dtype=torch.long),
            "attention_mask": torch.tensor(
                [[1] * len(input_ids)], dtype=torch.long),
        }
        model_input = {k: v.to(device) for k, v in model_input.items()}
        with torch.no_grad():
            logits = entry["model"](**model_input).logits
        window_probs = torch.softmax(
            logits[0, 1:1 + len(window_ids)].float(), dim=-1).cpu().tolist()
        # 本窗实际覆盖的字符区间(由非空offset给出)
        covered = [(int(offsets[t][0]), int(offsets[t][1]))
                   for t in range(w_start, w_end)
                   if offsets[t][0] < offsets[t][1]]
        if not covered:
            continue
        first, last = covered[0][0], covered[-1][1]
        for token_index, (s, e) in enumerate(covered):
            row = window_probs[token_index]
            named = {LABEL_B: 0.0, LABEL_I: 0.0, LABEL_O: 0.0}
            for li, prob in enumerate(row):
                label = id2label.get(li, LABEL_O)
                if label in named:
                    named[label] += float(prob)
            for pos in range(s, min(e, len(answer))):
                # 覆盖冲突时取"距窗口边缘更远"的窗口(边缘token上下文不足)
                center = min(pos - first, last - pos)
                if center > centers[pos]:
                    centers[pos] = center
                    probs[pos] = named
        if w_end >= len(ids):
            break
    # 兜底: 无token覆盖的字符(纯空白等) → 确定O
    return [p if p is not None else {LABEL_B: 0.0, LABEL_I: 0.0,
                                     LABEL_O: 1.0} for p in probs]


def segment_claims(answer: str,
                   model_path: str = MODEL_PATH,
                   boundary_gate: float = 0.0) -> list[dict[str, Any]]:
    """answer → 原子claim列表[{text, span, boundary_conf}].

    span=解码边界区间本身(去空白后校准, answer[span[0]:span[1]]==text);
    boundary_conf=起点字符的P(B). 模型不可用时显式抛RuntimeError.
    boundary_gate>0时弱B降级(argmax为B但P(B)<gate → 视为I, 与前claim
    合并): 抑制d3train短answer训练带来的过切分(v2, gate=0.75经
    tools/eval_claim_recognition.py的τ-sweep校准, 非test46标签调参).
    """
    if not answer.strip():
        return []
    entry = _load_model(model_path)
    if entry["mode"] == "unavailable":
        raise RuntimeError(
            f"claim切分器不可用({model_path}): {entry['error']}")
    char_probs = _window_char_probs(entry, answer)
    if boundary_gate > 0.0:
        labels = []
        for p in char_probs:
            top = max(p, key=lambda k: p[k])
            if top == LABEL_B and p[LABEL_B] < boundary_gate:
                labels.append(LABEL_I)
            else:
                labels.append(top)
    else:
        labels = [max(p, key=lambda k: p[k]) for p in char_probs]
    out: list[dict[str, Any]] = []
    for start, end in decode_char_labels(labels):
        raw = answer[start:end]
        text = raw.strip()
        if not text:
            continue
        lead = len(raw) - len(raw.lstrip())
        span = [start + lead, start + lead + len(text)]
        out.append({
            "text": text,
            "span": span,
            "boundary_conf": round(
                char_probs[span[0]].get(LABEL_B, 0.0), _BOUNDARY_CONF_DIGITS),
        })
    return out


def distilled_decompose_claims(question: str,
                               answer: str,
                               model_path: str = MODEL_PATH,
                               boundary_gate: float = 0.0) -> list[Any]:
    """qa_module.decompose_claims的蒸馏切分器替换(monkeypatch入口).

    question忽略; kind一律"semantic"(M82 C实验: typed通道跨域负资产);
    AnswerClaim有span字段则携带(M87主线), 无则text形式;
    model_path可指定v2等其它checkpoint, boundary_gate透传segment_claims
    (v2建议0.75, 下游评测用).
    """
    del question
    from algorithms.consistency.answer_claims import AnswerClaim
    has_span = "span" in {f.name for f in fields(AnswerClaim)}
    claims: list[Any] = []
    for item in segment_claims(answer, model_path=model_path,
                               boundary_gate=boundary_gate):
        if has_span:
            claims.append(AnswerClaim(kind="semantic", text=item["text"],
                                      span=item["span"]))
        else:
            claims.append(AnswerClaim(kind="semantic", text=item["text"]))
    if not claims:
        text = answer.strip()
        if text:  # 整段兜底(与decompose_claims回退契约一致)
            claims.append(AnswerClaim(kind="semantic", text=text))
    return claims


__all__ = [
    "LABELS",
    "LABEL_B",
    "LABEL_I",
    "LABEL_O",
    "MODEL_PATH",
    "char_labels_from_claims",
    "decode_char_labels",
    "distilled_decompose_claims",
    "load_status",
    "segment_claims",
]
