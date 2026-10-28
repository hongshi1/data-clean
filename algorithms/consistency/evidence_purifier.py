"""证据提纯器: 70-73号实验收敛的统一减法/提纯模块.

定位(实验教训的固化):
  statement模式(默认) — F1 scope删除 + F2粒度归一 + F3指针删除,
      kept为句/行级语句. 供NLI直判类消费方.
      依据71号: NLI直入原始表格HTML失效(35.3%), 行级化后64.7%.
  evidence模式 — 只删块不改写, kept为原证据块. 供结构化消费方
      (专家通道/类型感知linearize). 依据73号: 证据级文本重写会破坏
      linearize_evidence的表格类型检测(违例查全0.94→0.41的教训).
      可选叠加DEQ的E0无损门(73号: 删17.8%块判决零变化).

审计: 每次删除带{stage, reason_code, detail}; stats.by_reason汇总.

用法:
    from algorithms.consistency.evidence_purifier import PurifyConfig, purify
    pack = purify(question, answer, evidence_dicts)          # 语句级
    pack = purify(question, answer, evs,
                  PurifyConfig(mode="evidence"))              # 块级(原文本)
    pack = purify(question, answer, evs,
                  PurifyConfig(mode="evidence", use_deq_gate=True))
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from algorithms.consistency.evidence_subtractor import (
    _anchor_hits,
    _is_pointer,
    extract_anchors,
    normalize_granularity,
)

MODES = ("statement", "evidence")


@dataclass(frozen=True)
class PurificationConfig:
    """提纯配置(全部为实验校准默认值).

    mode:           "statement"(句/行级, NLI前提净化) | "evidence"(块级,
                    结构化消费方) — 73号: 两种消费方不可混用改写.
    use_deq_gate:   evidence模式下叠加DEQ E0 scope门(无损提纯基线;
                    73号实测删17.8%块判决零变化). statement模式忽略.
    max_statements: statement模式的语句预算(超限按锚点命中排序保留).
    id_exemption:   标识符类检测项(问题/答案含PZXQ式ID)的含ID证据
                    不做scope删除(多实体ID比对必需, 71号救回5实例gold).
    fallback:       F1删光全部时回退保留全部(防误删光).
    """

    mode: str = "statement"
    use_deq_gate: bool = False
    max_statements: int = 25
    id_exemption: bool = True
    fallback: bool = True

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(
                f"mode须为{MODES}之一, got {self.mode!r}")


def _scope_and_pointer_filter(
        question: str, answer: str,
        evidence: Sequence[Mapping],
        config: PurificationConfig,
) -> tuple[list[Mapping], list[dict], bool]:
    """F1(scope)+F3(指针)块级删除(共用核心, 不做F2改写).

    返回(存活块, 删除台账, 是否触发回退). 与evidence_subtractor.
    subtract的F1/F3规则逐条一致(含ID豁免/指针豁免/回退护栏),
    但保留原文本.
    """
    anchors = extract_anchors(question, answer)
    q_has_id = _has_id_pattern(question) or _has_id_pattern(answer)
    kept: list[Mapping] = []
    removed: list[dict] = []
    for ev in evidence:
        text = str(ev.get("text", ""))
        hits = _anchor_hits(text, anchors)
        id_exempt = (config.id_exemption and q_has_id
                     and _has_id_pattern(text))
        if anchors and hits == 0 and not id_exempt:
            removed.append({
                "evidence_id": str(ev.get("evidence_id", "")),
                "stage": "F1", "reason_code": "scope_mismatch",
                "detail": f"与问题/答案无共享锚点(锚点{len(anchors)}个)",
            })
        elif _is_pointer(text) and hits == 0:
            removed.append({
                "evidence_id": str(ev.get("evidence_id", "")),
                "stage": "F3",
                "reason_code": "shape_violation.pointer",
                "detail": f"纯指针文本且无锚点命中({len(text)}字)",
            })
        else:
            kept.append(ev)
    fallback = False
    if config.fallback and evidence and not kept:
        kept = list(evidence)
        removed = [r for r in removed if r["stage"] == "F1"]
        fallback = True
    return kept, removed, fallback


def _has_id_pattern(text: str) -> bool:
    from algorithms.consistency.evidence_subtractor import _ID_PATTERN
    return bool(_ID_PATTERN.search(text))


def _deq_gate_filter(question: str, answer: str,
                     evidence: Sequence[Mapping],
                     ) -> tuple[list[Mapping], list[dict]]:
    """DEQ E0门(无损提纯基线的组合接入): 需完整RetrievedEvidence字段.

    字段缺失时显式报错(不静默降级); 调用方保证输入为asdict格式.
    """
    from algorithms.consistency.deq_pipeline import scope_gate
    from algorithms.consistency.qa_models import RetrievedEvidence

    blocks = []
    for ev in evidence:
        blocks.append(RetrievedEvidence(
            evidence_id=str(ev["evidence_id"]),
            text=str(ev["text"]),
            source_type=ev["source_type"],
            source_ref=ev["source_ref"],
            scope_id=str(ev["scope_id"]),
            completeness=ev.get("completeness", "unknown"),
        ))
    gated = scope_gate(question, answer, tuple(blocks))
    removed_ids = {ev.evidence_id for ev, rep in gated
                   if rep.gate_status == "REJECT"}
    kept = [ev for ev in evidence
            if str(ev.get("evidence_id", "")) not in removed_ids]
    removed = [{
        "evidence_id": str(ev.get("evidence_id", "")),
        "stage": "deq_gate", "reason_code": "deq_scope_mismatch",
        "detail": "DEQ E0门拒绝(scope与问题实体无重叠)",
    } for ev in evidence
        if str(ev.get("evidence_id", "")) in removed_ids]
    return kept, removed


def purify(question: str, answer: str,
           evidence: Sequence[Mapping],
           config: PurificationConfig | None = None) -> dict:
    """统一提纯入口: (question, answer, 证据块) → PurificationPack.

    PurificationPack = {
      mode: "statement"|"evidence",
      kept:    statement模式→[{evidence_id, statements, granularity_class,
               anchor_hits, provenance}](句/行级语句);
               evidence模式→原证据块映射列表(文本原样),
               附kept_statements统计.
      removed: [{evidence_id, stage: F1|F3|deq_gate, reason_code, detail}],
      stats:   {n_in, n_kept, n_removed, by_reason, n_statements, fallback}
    }
    """
    cfg = config or PurificationConfig()
    if cfg.mode == "statement":
        from algorithms.consistency.evidence_subtractor import subtract
        pack = subtract(question, answer, evidence,
                        max_statements=cfg.max_statements)
        pack["mode"] = "statement"
        return pack

    # evidence模式: 块级过滤(不改写文本)
    kept, removed, fallback = _scope_and_pointer_filter(
        question, answer, evidence, cfg)
    if cfg.use_deq_gate and kept:
        pre_deq_kept = kept
        kept, deq_removed = _deq_gate_filter(question, answer, kept)
        if not kept:  # DEQ门全拒 → 回退到门前的F1/F3存活集(防删光)
            kept = pre_deq_kept
        else:
            removed.extend(deq_removed)
    n_statements = sum(len(normalize_granularity(
        str(ev.get("text", "")))["statements"]) for ev in kept)
    by_reason: dict[str, int] = {}
    for r in removed:
        by_reason[r["reason_code"]] = by_reason.get(r["reason_code"], 0) + 1
    return {
        "mode": "evidence",
        "kept": list(kept),
        "removed": removed,
        "stats": {
            "n_in": len(evidence), "n_kept": len(kept),
            "n_removed": len(removed), "n_statements": n_statements,
            "by_reason": by_reason,
            "fallback": fallback,
        },
    }


__all__ = ["PurificationConfig", "purify", "MODES"]
