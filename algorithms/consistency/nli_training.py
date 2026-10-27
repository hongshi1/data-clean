"""EGT合成数据 → NLI残差通道训练对的确定性构造 (S4).

S4 (residual NLI domain adaptation): the L3 LLM residual channel decides the
claims the deterministic channels cannot. This module prepares the training
corpus that teaches a small (~770M-param) local mDeBERTa the same residual
three-way decision — the MiniCheck-style "small model approaches LLM quality"
instance on the military-SRS three-way task.

Domain-adaptation contract (the S4 lesson, calibrated on the 91-QA corpus):
training premises must be built by the SAME pipeline as inference premises —
``linearize_context`` the EGT evidence blocks into field statements, group
them into complete scope rows (one capability/usecase row = one fact unit,
mirroring EGT's whole-block evidence), rank groups per claim (scope hit
first, question-gram overlap second — the question names the anchor
subject, e.g. 修改数据功能 → the 修改数据 row, not the parent SQL访问 row),
cap the total at ``PREMISE_BUDGET`` chars (+``GROUP_TOLERANCE`` so the last
complete group is not truncated) and restore document order. Ranking-by-
claim-overlap alone buys the lexical-coverage shortcut (overlap-selected
pseudo-anchors implying entailment); the question-anchored complete-row
binding is what lets a contradiction verdict bind to the right row.

Pure Python, no torch/transformers import (safe for inference-side reuse of
``build_premise``/``select_statements`` inside ``nli_residual``):

  premise    = 证据语句线性拼接(表格HTML先线性化为字段语句; 超长块按与claim
               的bigram重叠选窗口), 每块≤500字符, 总长≤PREMISE_BUDGET字符
  hypothesis = claim_text (用例名锚保留——它承载scope信息)
  label      = support→entailment / refute→contradiction /
               not_in_evidence→neutral; 类别id沿用基座模型config的label2id
               (mDeBERTa: entailment=0, neutral=1, contradiction=2), 预训练
               头的语义由此保留
  split      = train 90% / dev 10%, 按sample_id的md5哈希分桶(无seed, 复现=
               同一jsonl → 同一分割)
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from algorithms.consistency.evidence_statements import (
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.qa_models import RetrievedEvidence, SourceRef

BASE = Path(__file__).resolve().parents[2]

EGT_DATASET = (BASE / "data/gjb_438c/runs/build_egt_dataset_8a8716bb_20261027_003528"
               / "egt_dataset.jsonl")
BASE_MODEL_KEY = "mdeberta"

# 三态verdict → NLI类别名 (语义映射固定; id取基座config)
VERDICT_TO_NLI = {
    "support": "entailment",
    "refute": "contradiction",
    "not_in_evidence": "neutral",
}
NLI_LABELS = ("entailment", "neutral", "contradiction")

PER_BLOCK_CAP = 500
TOTAL_CAP = 1500
PREMISE_BUDGET = 500
GROUP_TOLERANCE = 250


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def strip_html(text: str) -> str:
    """表格HTML → 纯文本 (剥标签+折叠空白)."""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def bigrams(text: str) -> frozenset[str]:
    compact = re.sub(r"\s+", "", text)
    return frozenset(compact[i:i + 2] for i in range(len(compact) - 1))


def select_statements(claim_text: str, question: str,
                      statements: list[EvidenceStatement],
                      budget: int = PREMISE_BUDGET) -> list[tuple[int, str]]:
    """残差claim的语句组选取 (训练/推理共用, 保证premise分布一致).

    语句按scope_key(空则按证据块)分组, 组=一个功能行/用例表的完整事实
    单元(与EGT证据的整块结构对应); 组排序: scope命中优先, 其次与question
    的bigram重叠(问题点名对象=锚定主体, 如'修改数据功能'→修改数据行),
    再次与claim的重叠(值绑定); 选中组按文档序恢复, 取满budget.
    question参与排序但不进入premise——训练语料的question是泛化问句,
    推理侧把question用作scope锚(与LLM通道prompt锚定规则一致).
    返回 (语句下标, 清洗文本) 列表.
    """
    texts: list[str] = []
    indices: list[int] = []
    seen: set[str] = set()
    for index, statement in enumerate(statements):
        key = _compact(statement.text)
        if not key or key in seen:
            continue
        seen.add(key)
        texts.append(re.sub(r"\s+", " ", statement.text).strip())
        indices.append(index)
    joint = _compact(claim_text + question)
    question_grams = frozenset(_compact(question)[i:i + 2]
                               for i in range(len(_compact(question)) - 1))
    claim_grams = frozenset(_compact(claim_text)[i:i + 2]
                            for i in range(len(_compact(claim_text)) - 1))
    groups: dict[str, list[int]] = {}
    group_order: list[str] = []
    for position in range(len(indices)):
        statement = statements[indices[position]]
        group_key = statement.scope_key or f"ev:{statement.evidence_id}"
        if group_key not in groups:
            group_order.append(group_key)
        groups.setdefault(group_key, []).append(position)

    def group_grams(members: list[int]) -> set[str]:
        grams: set[str] = set()
        for position in members:
            compact = _compact(texts[position])
            grams |= frozenset(compact[i:i + 2]
                               for i in range(len(compact) - 1))
        return grams

    def group_rank(group_key: str) -> tuple[int, int, int, int]:
        members = groups[group_key]
        scope_hit = 0 if any(
            statements[indices[position]].scope_key
            and statements[indices[position]].scope_key in joint
            for position in members) else 1
        grams = group_grams(members)
        return (scope_hit, -len(grams & question_grams),
                -len(grams & claim_grams), group_order.index(group_key))

    chosen: list[int] = []
    used = 0
    for group_key in sorted(groups, key=group_rank):
        if used >= budget:
            break
        members = groups[group_key]
        member_len = sum(len(texts[position]) for position in members)
        if member_len > budget * 2:
            continue  # 单组超预算2倍: 整组跳过(不截半行)
        chosen.extend(members)
        used += member_len
    return [(indices[position], texts[position])
            for position in sorted(chosen)]


def egt_statements(row: dict) -> list[EvidenceStatement]:
    """EGT evidence块 → 线性化语句 (与推理侧linearize_context同一路径)."""
    blocks = []
    for evidence in row.get("evidence") or []:
        source_ref = evidence.get("source_ref") or {}
        blocks.append(RetrievedEvidence(
            evidence_id=str(evidence.get("evidence_id", "")),
            text=str(evidence.get("text", "")),
            source_type=str(evidence.get("source_type", "text")),  # type: ignore[arg-type]
            source_ref=SourceRef(
                doc_id=str(source_ref.get("doc_id", "")),
                section=str(source_ref.get("section", "")),
                page=source_ref.get("page"),
                block_id=str(source_ref.get("block_id", "")),
                row_id=str(source_ref.get("row_id", "")),
                region_id=str(source_ref.get("region_id", ""))),
            scope_id=str(evidence.get("scope_id", "")),
        ))
    return linearize_context(tuple(blocks))


def _window_block(text: str, cap: int, claim_grams: frozenset[str]) -> str:
    """超长块截断: 滑窗选与claim bigram重叠最大的窗口 (锚语句不被截丢)."""
    if len(text) <= cap:
        return text
    best_start, best_overlap = 0, -1
    step = max(1, cap // 4)
    for start in range(0, len(text) - cap + 1, step):
        overlap = len(bigrams(text[start:start + cap]) & claim_grams)
        if overlap > best_overlap:
            best_start, best_overlap = start, overlap
    return text[best_start:best_start + cap]


def build_premise(claim_text: str, block_texts: list[str],
                  per_block: int = PER_BLOCK_CAP,
                  total: int = TOTAL_CAP) -> str:
    """(claim, 文本列表) → premise: 剥标签/窗口截断/定长拼接."""
    claim_grams = bigrams(claim_text)
    parts: list[str] = []
    used = 0
    for raw in block_texts:
        if used >= total:
            break
        block = _window_block(strip_html(raw), per_block, claim_grams)
        block = block[:total - used]
        if block:
            parts.append(block)
            used += len(block)
    return " ".join(parts)[:total]


def residual_premise(claim_text: str, question: str,
                     statements: list[EvidenceStatement],
                     budget: int = PREMISE_BUDGET
                     ) -> tuple[str, list[tuple[int, str]]]:
    """残差claim的完整premise构造 (训练/推理共用入口).

    返回 (premise, 选中语句(下标,文本)); 总长上限budget+GROUP_TOLERANCE,
    保证末尾的完整组不被截断(组=不可截的行级事实单元).
    """
    picks = select_statements(claim_text, question, statements, budget)
    if not picks:
        return "", []
    premise = build_premise(claim_text, [text for _, text in picks],
                            per_block=PER_BLOCK_CAP,
                            total=budget + GROUP_TOLERANCE)
    return premise, picks


def load_egt_rows(path: Path = EGT_DATASET) -> list[dict]:
    """读EGT jsonl (3000样本: S/R/N各1000)."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def example_from_row(row: dict, label_id: dict[str, int]) -> dict | None:
    """EGT样本 → NLI训练对; label非三态或无证据的样本剔除(None).

    premise走与推理侧完全相同的构造: EGT evidence块 → linearize_context
    字段语句 → select_statements(scope/重叠排序+文档序) → build_premise.
    """
    verdict = str(row.get("label", ""))
    nli_name = VERDICT_TO_NLI.get(verdict)
    evidence = row.get("evidence") or []
    claim = str(row.get("claim_text", "")).strip()
    if nli_name is None or not evidence or not claim:
        return None
    question = str(row.get("question", ""))
    statements = egt_statements(row)
    if statements:
        premise, _picks = residual_premise(claim, question, statements)
    else:
        premise = build_premise(
            claim, [str(ev.get("text", "")) for ev in evidence],
            total=PREMISE_BUDGET)
    if not premise.strip():
        return None
    return {
        "sample_id": str(row["sample_id"]),
        "question": question,
        "premise": premise,
        "hypothesis": claim,
        "verdict": verdict,
        "label_name": nli_name,
        "label": label_id[nli_name],
        "source": str(row.get("source", "")),
        "operator": str(row.get("operator", "")),
        "claim_kind": str(row.get("claim_kind", "")),
    }


def is_dev_sample(sample_id: str, buckets: int = 10, dev_bucket: int = 0) -> bool:
    """sample_id的md5哈希分桶 → 是否dev (确定性, 无随机数)."""
    digest = hashlib.md5(sample_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % buckets == dev_bucket


def split_train_dev(examples: list[dict]) -> tuple[list[dict], list[dict]]:
    """90/10确定性分割: 同一jsonl永远产生同一分割."""
    train = [ex for ex in examples if not is_dev_sample(ex["sample_id"])]
    dev = [ex for ex in examples if is_dev_sample(ex["sample_id"])]
    return train, dev


def base_label_ids(model_key: str = BASE_MODEL_KEY) -> dict[str, int]:
    """基座模型config.json的label2id (NLI类别名→id). 集中读取一次."""
    from algorithms.consistency.nli_local import MODELS

    config_path = Path(MODELS[model_key]["dir"]) / "config.json"
    label2id = json.loads(config_path.read_text(encoding="utf-8"))["label2id"]
    mapping = {name: int(label2id[name]) for name in NLI_LABELS
               if name in label2id}
    if len(mapping) != len(NLI_LABELS):
        raise ValueError(f"base model {model_key} label2id缺失NLI类别: {label2id}")
    return mapping


def build_dataset(path: Path = EGT_DATASET,
                  model_key: str = BASE_MODEL_KEY) -> dict:
    """EGT jsonl → {train, dev, meta}: 训练脚本与测试共用的入口."""
    label_id = base_label_ids(model_key)
    rows = load_egt_rows(path)
    examples = [ex for ex in (example_from_row(row, label_id) for row in rows)
                if ex is not None]
    train, dev = split_train_dev(examples)
    return {
        "train": train,
        "dev": dev,
        "meta": {
            "source_path": str(path),
            "n_rows": len(rows),
            "n_examples": len(examples),
            "n_train": len(train),
            "n_dev": len(dev),
            "label_id": label_id,
            "verdict_dist": {
                v: sum(1 for ex in examples if ex["verdict"] == v)
                for v in VERDICT_TO_NLI},
            "per_block_cap": PER_BLOCK_CAP,
            "premise_budget": PREMISE_BUDGET,
            "premise_mode": ("linearize_context + select_statements "
                             "(train/inference-matched)"),
            "split": "md5(sample_id) % 10 == 0 → dev (deterministic)",
        },
    }


__all__ = [
    "EGT_DATASET",
    "NLI_LABELS",
    "PREMISE_BUDGET",
    "TOTAL_CAP",
    "VERDICT_TO_NLI",
    "base_label_ids",
    "bigrams",
    "build_dataset",
    "build_premise",
    "egt_statements",
    "example_from_row",
    "is_dev_sample",
    "load_egt_rows",
    "residual_premise",
    "select_statements",
    "split_train_dev",
    "strip_html",
]
