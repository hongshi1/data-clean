"""DEQ-Pipe: Detection-item-aware Evidence Quality Pipeline.

Three-stage progressive evidence filtering for cascade verification:

  E0 Scope Gate: entity+scope matching to reject wrong-scope evidence
     (inspired by Dong 2021: distracting entities mislead retrieval)
  E1 Item-Aware Scoring: rate evidence by what the detection item needs
     (novel: no prior work conditions evidence selection on verification
     task type; 40-item taxonomy maps to evidence form requirements)
  E2 Statement Alignment: select optimal (claim, statement) pairs for L2
     (SummaC-inspired: granularity engineering + pair matrix, but
     detection-item-conditioned rather than generic)

This module is fully deterministic — no model calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from algorithms.consistency.answer_structure import (
    decompose_answer,
)
from algorithms.consistency.evidence_statements import (
    EvidenceStatement,
    linearize_evidence,
)
from algorithms.consistency.qa_models import RetrievedEvidence
from algorithms.consistency.qa_router import route_question

# ---------------------------------------------------------------------------
# Detection-item → evidence-form registry (domain knowledge, not learned)
# ---------------------------------------------------------------------------

DETECTION_EVIDENCE_REGISTRY: dict[str, dict[str, Any]] = {
    "TERM-01": {
        "table_types": {"use_case_table", "capability_table"},
        "content_markers": ("名称", "别名", "称为", "简称", "（"),
        "statement_fields": ("Use Case 名称", "标识符"),
    },
    "TERM-02": {
        "table_types": {"use_case_table", "capability_table"},
        "content_markers": ("定义", "描述", "说明"),
        "statement_fields": ("简要说明", "需求描述", "概述"),
    },
    "TERM-03": {
        "table_types": {"capability_table"},
        "content_markers": ("包括", "包含", "能力标识", "项目唯一标识符"),
        "statement_fields": ("Use case名称", "需求描述", "标识符"),
    },
    "TERM-04": {
        "table_types": {"capability_table", "use_case_table"},
        "content_markers": ("运行状态", "方式名称", "告警", "状态"),
        "statement_fields": ("运行状态", "方式名称"),
    },
    "TERM-05": {
        "table_types": {"use_case_table"},
        "content_markers": ("指令", "命令", "调用"),
        "statement_fields": ("Actor的动作", "系统的动作"),
    },
    "TERM-06": {
        "table_types": {"capability_table", "value_domain_table"},
        "content_markers": ("ms", "秒", "GB", "字节", "单位"),
        "statement_fields": ("需求描述", "单位"),
    },
    "TERM-07": {
        "table_types": {"capability_table", "interface_table"},
        "content_markers": ("PZXQ", "接口", "标识", "发送方"),
        "statement_fields": ("标识符", "项目唯一标识符"),
    },
    "TERM-08": {
        "table_types": set(),
        "content_markers": ("（", "缩写", "简称", "全称"),
        "statement_fields": ("需求描述",),
    },
    "PARAM-01": {
        "table_types": {"use_case_table", "value_domain_table"},
        "content_markers": ("时间", "时延", "延迟", "ms", "秒"),
        "statement_fields": ("动作约束", "单位"),
    },
    "PARAM-02": {
        "table_types": set(),
        "content_markers": ("周期", "频率", "间隔"),
        "statement_fields": ("需求描述",),
    },
    "PARAM-03": {
        "table_types": set(),
        "content_markers": ("阈值", "门限"),
        "statement_fields": ("需求描述",),
    },
    "PARAM-04": {
        "table_types": set(),
        "content_markers": ("对齐", "融合", "误差"),
        "statement_fields": ("需求描述",),
    },
    "PARAM-05": {
        "table_types": {"capability_table"},
        "content_markers": ("CPU", "内存", "资源", "占用", "存储"),
        "statement_fields": ("需求描述", "方式名称"),
    },
    "PARAM-06": {
        "table_types": {"value_domain_table"},
        "content_markers": ("最大", "最小", "精度", "单位"),
        "statement_fields": ("最大差", "最小差", "精度", "单位"),
    },
    "PARAM-07": {
        "table_types": {"capability_table", "value_domain_table"},
        "content_markers": ("容量", "保存", "保留", "存储"),
        "statement_fields": ("需求描述", "最大差"),
    },
    "PARAM-08": {
        "table_types": set(),
        "content_markers": ("精度", "同步", "守时", "漂移"),
        "statement_fields": ("需求描述",),
    },
    "PARAM-09": {
        "table_types": set(),
        "content_markers": ("降级", "触发"),
        "statement_fields": ("需求描述",),
    },
    "PARAM-10": {
        "table_types": {"use_case_table"},
        "content_markers": ("故障", "持续", "重连", "恢复"),
        "statement_fields": ("动作约束", "异常流"),
    },
    "LOGIC-01": {
        "table_types": {"capability_table"},
        "content_markers": ("优先", "切换", "状态"),
        "statement_fields": ("需求描述", "运行状态"),
    },
    "LOGIC-02": {
        "table_types": {"use_case_table"},
        "content_markers": ("异常流", "E1", "动作约束", "前置条件"),
        "statement_fields": ("异常流E1", "动作约束", "前置条件"),
    },
    "LOGIC-03": {
        "table_types": {"use_case_table"},
        "content_markers": ("主事件流", "步骤", "Actor的动作", "系统的动作"),
        "statement_fields": ("Actor的动作", "系统的动作"),
    },
    "LOGIC-04": {
        "table_types": {"use_case_table", "interface_table"},
        "content_markers": ("调用", "发送", "返回", "传输", "接口"),
        "statement_fields": ("Actor的动作", "系统的动作"),
    },
    "LOGIC-05": {
        "table_types": {"capability_table", "use_case_table"},
        "content_markers": ("方式名称", "桌面", "平板", "手持", "分支"),
        "statement_fields": ("方式名称", "运行状态"),
    },
    "LOGIC-06": {
        "table_types": set(),
        "content_markers": ("互斥", "禁止", "并行"),
        "statement_fields": ("需求描述",),
    },
    "LOGIC-07": {
        "table_types": set(),
        "content_markers": ("原子", "回滚", "中断"),
        "statement_fields": ("需求描述",),
    },
    "LOGIC-08": {
        "table_types": {"capability_table", "use_case_table"},
        "content_markers": ("切换", "仲裁", "主备", "冗余"),
        "statement_fields": ("需求描述", "动作约束"),
    },
    "LOGIC-09": {
        "table_types": {"use_case_table"},
        "content_markers": ("Actors", "参与者", "角色", "权限"),
        "statement_fields": ("Actors", "Use Case 名称"),
    },
    "LOGIC-10": {
        "table_types": {"use_case_table"},
        "content_markers": ("恢复", "重启", "重连", "故障后"),
        "statement_fields": ("异常流", "动作约束"),
    },
    "LOGIC-11": {
        "table_types": {"capability_table", "use_case_table"},
        "content_markers": ("缓存", "更新", "重新", "搜索"),
        "statement_fields": ("需求描述", "系统的动作"),
    },
    "GJB-01": {
        "table_types": {"qualification_table"},
        "content_markers": ("合格性", "演示", "测试", "审查"),
        "statement_fields": ("合格性方法", "合格性级别"),
    },
    "GJB-02": {
        "table_types": {"security_table"},
        "content_markers": ("容错", "故障检测", "自检"),
        "statement_fields": ("安全性需求", "详细说明"),
    },
    "GJB-03": {
        "table_types": {"security_table"},
        "content_markers": ("访问控制", "权限", "安全"),
        "statement_fields": ("保密性需求", "详细说明"),
    },
    "GJB-04": {
        "table_types": set(),
        "content_markers": ("审计", "日志"),
        "statement_fields": ("需求描述",),
    },
    "GJB-05": {
        "table_types": {"trace_table"},
        "content_markers": ("追踪", "正向", "逆向", "任务书"),
        "statement_fields": ("需求名称", "章节号"),
    },
    "GJB-06": {
        "table_types": set(),
        "content_markers": ("报警", "告警", "时间戳", "故障位置"),
        "statement_fields": ("异常流",),
    },
    "GJB-07": {
        "table_types": {"security_table"},
        "content_markers": ("自检", "启动自检", "周期"),
        "statement_fields": ("安全性需求",),
    },
    "GJB-08": {
        "table_types": set(),
        "content_markers": ("掉电", "断电", "保护"),
        "statement_fields": ("需求描述",),
    },
    "GJB-09": {
        "table_types": {"value_domain_table"},
        "content_markers": ("输入", "校验", "防护", "值域"),
        "statement_fields": ("最大差", "最小差"),
    },
    "GJB-10": {
        "table_types": set(),
        "content_markers": ("升级", "回滚", "版本"),
        "statement_fields": ("需求描述",),
    },
    "GJB-11": {
        "table_types": set(),
        "content_markers": ("降级", "模式", "运行状态"),
        "statement_fields": ("需求描述",),
    },
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceQualityReport:
    """Per-evidence-block quality assessment from DEQ-Pipe."""

    evidence_id: str
    scope_key: str
    gate_status: str  # PASS | WEAK | REJECT
    gate_reason: str
    scope_score: float
    form_score: float
    density_score: float
    deq_score: float
    item_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class DEQResult:
    """Complete output of the DEQ pipeline."""

    original_count: int
    gated_count: int
    ranked_evidence: tuple[RetrievedEvidence, ...]
    quality_reports: tuple[EvidenceQualityReport, ...]
    active_check_items: tuple[str, ...]
    aligned_pairs: tuple[dict[str, Any], ...]
    diagnostics: dict[str, Any]


# ---------------------------------------------------------------------------
# E0: Scope Gate
# ---------------------------------------------------------------------------

_USECASE_HEADER = re.compile(r"Use\s*[Cc]ase\s*名称\s*[：:]\s*([^：；\s]+)")
_CAPABILITY_HEADER = re.compile(
    r"<th[^>]*>.*?Use\s*case名称.*?</th>|<th[^>]*>.*?项目唯一标识符.*?</th>",
    re.S,
)
_ID_PATTERN = re.compile(r"PZXQ-[A-Z]+(?:-[A-Z0-9]+)+")
_STOP_WORDS = frozenset({
    "系统", "功能", "数据", "进行", "操作", "需要", "哪些", "什么", "如何",
    "是否", "的时候", "过程中", "情况下", "要求", "描述", "说明", "给出",
    "分别", "以及", "还有", "其他", "以下", "如下",
})

# Chinese function words to split on (more aggressive than just 在/的/和)
_SPLIT_CHARS = "的在和与及对从到为并或者是中其被把让使如果因为所以但是"

# Domain-specific term patterns to extract directly
_DOMAIN_TERMS = re.compile(
    r"[A-Z]{2,8}(?:-[A-Z0-9]+)+|BLOB|SQL|JSON|INT|STRING|FLOAT|LOB|DML|API"
)


def _extract_question_entities(question: str) -> set[str]:
    """Extract domain entities from the question (compact, no stop words).

    Chinese text has no spaces, so we split on function words and also
    match domain-specific patterns (IDs, tech terms). Domain terms are
    kept even if they are substrings of longer segments."""
    compact = re.sub(r"[？?。，,；：:\s]", "", question)

    # 1. Domain-specific terms (BLOB, SQL, PZXQ-XX, etc.) — never deduped
    domain_terms: set[str] = set()
    for match in _DOMAIN_TERMS.finditer(compact):
        domain_terms.add(match.group())

    # 2. Split on Chinese function words
    segments: set[str] = set()
    for segment in re.split(f"[{_SPLIT_CHARS}]", compact):
        segment = segment.strip()
        if len(segment) >= 2 and segment not in _STOP_WORDS:
            segments.add(segment)

    # 3. Dedup only within split segments (keep domain terms)
    sorted_segments = sorted(segments, key=len, reverse=True)
    filtered_segments: set[str] = set()
    for segment in sorted_segments:
        if not any(
            segment != other and segment in other
            for other in filtered_segments
        ):
            filtered_segments.add(segment)

    return domain_terms | filtered_segments


def _extract_block_scope(evidence: RetrievedEvidence) -> str:
    """Extract the scope identifier (use-case/capability name) from a block."""
    text = evidence.text
    match = _USECASE_HEADER.search(text)
    if match:
        return match.group(1)
    if "PZXQ" in text or "标识符" in text:
        ids = _ID_PATTERN.findall(text)
        if ids:
            return ids[0]
    first_line = re.sub(r"<[^>]+>", "", text[:200]).strip()
    if len(first_line) >= 4:
        return first_line[:20]
    return evidence.evidence_id


def _entity_in_text(entity: str, text_compact: str) -> bool:
    """Check if an entity appears in text, with core-form fallback.

    Chinese questions add suffixes like 过程/操作/时 that evidence doesn't:
    Q: "二维数组输出过程" vs E: "二维数组输出"
    We strip common suffixes and also try prefix matching for long entities.
    """
    if entity in text_compact:
        return True

    # Strip common verbal suffixes that questions add but evidence omits
    core = entity
    for suffix in ("过程", "操作", "时", "步骤", "方式", "情况", "信息", "提示"):
        if core.endswith(suffix) and len(core) > len(suffix) + 1:
            core = core[: -len(suffix)]
            break
    if core != entity and core in text_compact:
        return True

    # For long entities, try prefix (first 4 chars) matching
    if len(entity) >= 5:
        prefix = entity[:4]
        if prefix in text_compact:
            return True

    return False


def scope_gate(
    question: str,
    answer: str,
    evidence_blocks: tuple[RetrievedEvidence, ...],
) -> list[tuple[RetrievedEvidence, EvidenceQualityReport]]:
    """E0: Reject evidence blocks whose scope does not match the question."""
    q_entities = _extract_question_entities(question)
    a_entities = _extract_question_entities(answer)
    all_entities = q_entities | a_entities

    results: list[tuple[RetrievedEvidence, EvidenceQualityReport]] = []
    for evidence in evidence_blocks:
        block_scope = _extract_block_scope(evidence)
        scope_key = re.sub(r"\s+", "", block_scope)
        block_text_compact = re.sub(r"\s+", "", evidence.text)

        # Count entity hits with core-form fallback matching
        entity_hits = sum(
            1 for entity in all_entities
            if _entity_in_text(entity, block_text_compact)
        )
        total_entities = max(len(all_entities), 1)
        scope_score = entity_hits / total_entities

        # Check scope overlap (block scope vs question entities)
        scope_overlap = any(
            _entity_in_text(entity, scope_key)
            or scope_key in entity
            for entity in all_entities
        )

        if scope_score == 0 and not scope_overlap:
            gate_status = "REJECT"
            gate_reason = (
                f"scope mismatch: block scope='{scope_key}' "
                f"has no overlap with question entities"
            )
        elif scope_score < 0.15 or (not scope_overlap and scope_score < 0.3):
            gate_status = "WEAK"
            gate_reason = (
                f"weak scope match: {entity_hits}/{total_entities} entities "
                f"found, scope_overlap={scope_overlap}"
            )
        else:
            gate_status = "PASS"
            gate_reason = (
                f"scope matched: {entity_hits}/{total_entities} entities, "
                f"scope_overlap={scope_overlap}"
            )

        report = EvidenceQualityReport(
            evidence_id=evidence.evidence_id,
            scope_key=scope_key,
            gate_status=gate_status,
            gate_reason=gate_reason,
            scope_score=scope_score,
            form_score=0.0,
            density_score=0.0,
            deq_score=scope_score,
        )
        results.append((evidence, report))

    return [
        (ev, report) for ev, report in results
        if report.gate_status != "REJECT"
    ]


# ---------------------------------------------------------------------------
# E1: Detection-Item-Aware Scoring
# ---------------------------------------------------------------------------


def _detect_table_type(evidence: RetrievedEvidence) -> str:
    """Classify a table block into its semantic type."""
    text = evidence.text
    if "Use Case" in text or "Use case" in text or "主事件流" in text:
        return "use_case_table"
    if "标识符" in text and "需求描述" in text:
        return "capability_table"
    if "最大" in text and "最小" in text and "精度" in text:
        return "value_domain_table"
    if "追踪" in text or "正向" in text or "逆向" in text:
        return "trace_table"
    if "合格性" in text:
        return "qualification_table"
    if "安全性需求" in text:
        return "security_table"
    if "接口" in text and ("发送方" in text or "接收方" in text):
        return "interface_table"
    if "<table" not in text:
        return "text"
    return "unknown_table"


def detection_aware_scoring(
    question: str,
    answer: str,
    gated_blocks: list[tuple[RetrievedEvidence, EvidenceQualityReport]],
    active_check_items: tuple[str, ...],
) -> list[tuple[RetrievedEvidence, EvidenceQualityReport]]:
    """E1: Score each evidence block by what the detection items need."""

    def score_block(
        evidence: RetrievedEvidence,
        base_report: EvidenceQualityReport,
    ) -> EvidenceQualityReport:
        table_type = _detect_table_type(evidence)
        text_compact = re.sub(r"\s+", "", evidence.text)
        item_scores: dict[str, float] = {}

        for item_id in active_check_items:
            registry = DETECTION_EVIDENCE_REGISTRY.get(item_id)
            if not registry:
                continue

            # Dimension 1: form match (is this the right type of evidence?)
            form_score = 0.0
            needed_types = registry.get("table_types", set())
            if needed_types:
                if table_type in needed_types:
                    form_score += 0.5
                elif table_type == "text":
                    form_score += 0.1  # text can sometimes be useful
            else:
                form_score += 0.3  # no specific table type needed

            # Check content markers
            markers = registry.get("content_markers", ())
            if markers:
                marker_hits = sum(1 for m in markers if m in text_compact)
                form_score += 0.5 * min(marker_hits / max(len(markers), 1), 1.0)

            # Dimension 2: scope match (already computed in E0)
            scope_score = base_report.scope_score

            # Dimension 3: info density (does it contain needed fields?)
            needed_fields = registry.get("statement_fields", ())
            density_score = 0.0
            if needed_fields:
                field_hits = sum(1 for f in needed_fields if f in text_compact)
                density_score = field_hits / max(len(needed_fields), 1)

            # Composite score
            item_scores[item_id] = (
                0.35 * scope_score
                + 0.40 * min(form_score, 1.0)
                + 0.25 * density_score
            )

        best_score = max(item_scores.values()) if item_scores else 0.0

        # Aggregate form/density across items for the summary report
        best_form = 0.0
        best_density = 0.0
        if item_scores:
            best_item = max(item_scores, key=item_scores.get)
            registry = DETECTION_EVIDENCE_REGISTRY.get(best_item, {})
            markers = registry.get("content_markers", ())
            if markers:
                marker_hits = sum(1 for m in markers if m in text_compact)
                best_form = min(marker_hits / max(len(markers), 1), 1.0)
            needed_fields = registry.get("statement_fields", ())
            if needed_fields:
                field_hits = sum(1 for f in needed_fields if f in text_compact)
                best_density = field_hits / max(len(needed_fields), 1)

        return EvidenceQualityReport(
            evidence_id=base_report.evidence_id,
            scope_key=base_report.scope_key,
            gate_status=base_report.gate_status,
            gate_reason=base_report.gate_reason,
            scope_score=base_report.scope_score,
            form_score=best_form,
            density_score=best_density,
            deq_score=best_score,
            item_scores=item_scores,
        )

    scored = [
        (ev, score_block(ev, report)) for ev, report in gated_blocks
    ]
    scored.sort(key=lambda pair: pair[1].deq_score, reverse=True)
    return scored


# ---------------------------------------------------------------------------
# E2: Statement-Level Alignment
# ---------------------------------------------------------------------------


def statement_alignment(
    question: str,
    answer: str,
    ranked_blocks: list[tuple[RetrievedEvidence, EvidenceQualityReport]],
    active_check_items: tuple[str, ...],
    top_k_statements: int = 5,
) -> list[dict[str, Any]]:
    """E2: Select optimal (claim, statement) pairs for downstream L2 NLI."""
    claims = decompose_answer(answer, question)

    all_statements: list[EvidenceStatement] = []
    for evidence, _report in ranked_blocks:
        statements = linearize_evidence(evidence)
        all_statements.extend(statements)

    pairs: list[dict[str, Any]] = []
    for claim in claims:
        claim_compact = re.sub(r"\s+", "", claim.text)

        scored_statements: list[tuple[float, EvidenceStatement, str]] = []
        for stmt in all_statements:
            stmt_compact = re.sub(r"\s+", "", stmt.text)

            # Scope match
            scope_bonus = 0.0
            if claim.scope_hint and stmt.scope_key:
                claim_scope = re.sub(r"\s+", "", claim.scope_hint)
                stmt_scope = re.sub(r"\s+", "", stmt.scope_key)
                if claim_scope in stmt_scope or stmt_scope in claim_scope:
                    scope_bonus = 0.4

            # Token overlap
            claim_chars = set(claim_compact)
            stmt_chars = set(stmt_compact)
            if claim_chars and stmt_chars:
                overlap = len(claim_chars & stmt_chars) / len(
                    claim_chars | stmt_chars
                )
            else:
                overlap = 0.0

            # Field relevance (check if statement field matches any active item)
            field_bonus = 0.0
            for item_id in active_check_items:
                registry = DETECTION_EVIDENCE_REGISTRY.get(item_id, {})
                needed_fields = registry.get("statement_fields", ())
                if stmt.field_name in needed_fields:
                    field_bonus = 0.3
                    break

            total = scope_bonus + overlap + field_bonus
            scored_statements.append((total, stmt, stmt.evidence_id))

        scored_statements.sort(key=lambda x: x[0], reverse=True)

        for score, stmt, ev_id in scored_statements[:top_k_statements]:
            pairs.append({
                "claim_id": claim.claim_id,
                "claim_text": claim.text,
                "claim_scope": claim.scope_hint,
                "statement_id": stmt.statement_id,
                "statement_text": stmt.text,
                "statement_field": stmt.field_name,
                "statement_scope": stmt.scope_key,
                "evidence_id": ev_id,
                "alignment_score": round(score, 4),
                "check_items": list(active_check_items),
            })

    return pairs


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def deq_pipeline(
    question: str,
    answer: str,
    evidence_blocks: tuple[RetrievedEvidence, ...],
    top_k_statements: int = 5,
) -> DEQResult:
    """Run the full Detection-item-aware Evidence Quality Pipeline."""

    # Route to determine active check items
    active_check_items = route_question(question)

    # E0: Scope Gate
    gated = scope_gate(question, answer, evidence_blocks)
    gated_count = len(gated)

    # E1: Detection-Item-Aware Scoring
    ranked = detection_aware_scoring(
        question, answer, gated, active_check_items)

    # E2: Statement-Level Alignment
    pairs = statement_alignment(
        question, answer, ranked, active_check_items,
        top_k_statements=top_k_statements)

    diagnostics = {
        "original_count": len(evidence_blocks),
        "gated_count": gated_count,
        "rejected_count": len(evidence_blocks) - gated_count,
        "active_check_items": list(active_check_items),
        "rejected_blocks": [
            {"evidence_id": report.evidence_id, "reason": report.gate_reason}
            for ev, report in scope_gate(question, answer, evidence_blocks)
            if report.gate_status == "REJECT"
        ],
        "ranking": [
            {
                "evidence_id": report.evidence_id,
                "deq_score": round(report.deq_score, 4),
                "scope_score": round(report.scope_score, 4),
                "item_scores": {
                    k: round(v, 4) for k, v in report.item_scores.items()
                },
            }
            for _ev, report in ranked
        ],
        "n_aligned_pairs": len(pairs),
    }

    return DEQResult(
        original_count=len(evidence_blocks),
        gated_count=gated_count,
        ranked_evidence=tuple(ev for ev, _ in ranked),
        quality_reports=tuple(report for _, report in ranked),
        active_check_items=active_check_items,
        aligned_pairs=tuple(pairs),
        diagnostics=diagnostics,
    )


__all__ = [
    "DETECTION_EVIDENCE_REGISTRY",
    "EvidenceQualityReport",
    "DEQResult",
    "scope_gate",
    "detection_aware_scoring",
    "statement_alignment",
    "deq_pipeline",
]
