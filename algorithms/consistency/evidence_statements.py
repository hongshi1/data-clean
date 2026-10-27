"""Deterministic evidence linearization: table blocks -> field-level statements.

Real frozen evidence is 57% raw HTML tables (use-case schema tables and
capability tables) whose text is unusable as an NLI premise. This module
converts every evidence block into short natural-language statements, each
carrying row-level localization and a scope key (use-case/capability name)
for claim pairing.

This layer is deterministic: fixed schema parsing, no model calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from algorithms.consistency.qa_models import RetrievedEvidence

_FIELD_PREFIX = re.compile(
    r"^(?P<field>Use\s*[Cc]ase\s*名称|Actors?|简要说明|前置条件|后置条件"
    r"|异常流E?\d*|参与者)\s*[：:]\s*(?P<value>.+)$")
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_HEADER_LABEL = re.compile(r"^(?:Actor\s*的动作|系统的动作|动作约束|序号|Use\s*case名称|"
                           r"项目唯一标识符|需求描述|需求重用|方式名称|运行状态|"
                           r"对应的任务书功能/性能)$")

_KEY_COLUMNS = ("需求描述", "方式名称", "运行状态", "需求重用", "对应的任务书功能性能")

#: 位置保持线性化时跳过的无信息列(序号/备注)与无信息值
_SKIP_HEADER_COLUMNS = ("序号", "备注")
_EMPTY_CELL_VALUES = ("", "-", "—", "无", "/")


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class EvidenceStatement:
    """One linearized statement with row-level localization and scope key."""

    statement_id: str
    evidence_id: str
    text: str
    field_name: str
    scope_key: str
    row_index: int


def _table_rows(table_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_match in _ROW.finditer(table_text):
        cells = [_strip_tags(cell) for cell in _CELL.findall(row_match.group(1))]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    return rows


def table_rows_positional(table_text: str) -> list[list[str]]:
    """位置保持的表格行解析(空单元格占位, 列与表头对齐).

    ``_table_rows`` 为用例表语义剔除空单元格——但能力/数据/接口表的
    ``序号``列常为空, 剔除后数据行整体左移错位(表头按位置zip时
    『方式名称』读到『运行状态』的值). 本函数保留空占位, 专供表头
    签名对齐的线性化路径使用.
    """
    rows: list[list[str]] = []
    for row_match in _ROW.finditer(table_text):
        cells = [_strip_tags(cell) for cell in _CELL.findall(row_match.group(1))]
        if any(cell for cell in cells):
            rows.append(cells)
    return rows


def _linearize_usecase_table(rows: list[list[str]], evidence_id: str,
                              ) -> list[EvidenceStatement]:
    statements: list[EvidenceStatement] = []
    scope = ""
    row_index = 0
    header_labels: list[str] = []
    for cells in rows:
        row_index += 1
        joined = "；".join(cells)
        name_match = re.search(r"Use\s*[Cc]ase\s*名称\s*[：:]\s*([^：；\s]+)", joined)
        if name_match:
            scope = name_match.group(1)
        field_match = _FIELD_PREFIX.match(cells[0])
        if field_match and len(cells) <= 2:
            field, value = field_match.group("field"), cells[0]
            statements.append(EvidenceStatement(
                statement_id=f"{evidence_id}#s{len(statements)}",
                evidence_id=evidence_id, text=value, field_name=field,
                scope_key=scope, row_index=row_index))
            continue
        if _HEADER_LABEL.match(cells[0]):
            header_labels = cells
            continue
        if header_labels and len(cells) >= 2:
            for label, cell in zip(header_labels, cells):
                if not cell or cell == label:
                    continue
                clean_label = re.sub(r"（[^）]*）", "", label)
                text = (f"{scope}{clean_label}：{cell}" if scope
                        else f"{clean_label}：{cell}")
                statements.append(EvidenceStatement(
                    statement_id=f"{evidence_id}#s{len(statements)}",
                    evidence_id=evidence_id, text=text,
                    field_name=clean_label, scope_key=scope, row_index=row_index))
            continue
        for cell in cells:
            if not _HEADER_LABEL.match(cell):
                statements.append(EvidenceStatement(
                    statement_id=f"{evidence_id}#s{len(statements)}",
                    evidence_id=evidence_id, text=cell,
                    field_name="cell", scope_key=scope, row_index=row_index))
    return statements


def _linearize_capability_table(rows: list[list[str]], evidence_id: str,
                                ) -> list[EvidenceStatement]:
    if not rows:
        return []
    headers = [re.sub(r"[\s/]", "", cell) for cell in rows[0]]
    name_idx = next((i for i, h in enumerate(headers)
                     if "Usecase名称" in h or h == "名称"), None)
    id_idx = next((i for i, h in enumerate(headers) if "标识符" in h), None)
    statements: list[EvidenceStatement] = []
    for row_index, cells in enumerate(rows[1:], start=2):
        if len(cells) < len(headers) - 2:
            continue
        name = cells[name_idx] if name_idx is not None and name_idx < len(cells) else ""
        identifier = (cells[id_idx] if id_idx is not None and id_idx < len(cells)
                      else "")
        scope = name or identifier
        if not scope:
            continue
        if identifier:
            statements.append(EvidenceStatement(
                statement_id=f"{evidence_id}#s{len(statements)}",
                evidence_id=evidence_id,
                text=f"{scope}的项目唯一标识符：{identifier}",
                field_name="标识符", scope_key=scope, row_index=row_index))
        for index, header in enumerate(headers):
            if index in (name_idx, id_idx):
                continue
            if header not in _KEY_COLUMNS or index >= len(cells):
                continue
            if not cells[index]:
                continue
            statements.append(EvidenceStatement(
                statement_id=f"{evidence_id}#s{len(statements)}",
                evidence_id=evidence_id,
                text=f"{scope}的{header}：{cells[index]}",
                field_name=header, scope_key=scope, row_index=row_index))
    return statements


def _linearize_header_table(rows: list[list[str]], evidence_id: str,
                            subject_needles: tuple[str, ...],
                            ) -> list[EvidenceStatement]:
    """表头签名对齐的通用线性化(数据表/接口表): 每行 = 主体列 +
    『主体的{列名}：{值}』语句(空列/无信息值跳过, row_index与
    _delete_table_rows的非空行计数对齐)."""
    if not rows:
        return []
    headers = [re.sub(r"[\s/]", "", cell) for cell in rows[0]]
    subject_idx = next((i for i, h in enumerate(headers)
                        if any(needle in h for needle in subject_needles)),
                       None)
    if subject_idx is None:
        return []
    statements: list[EvidenceStatement] = []
    for row_index, cells in enumerate(rows[1:], start=2):
        if len(cells) < len(headers) - 2:
            continue
        subject = (cells[subject_idx].strip()
                   if subject_idx < len(cells) else "")
        if not subject:
            continue
        for index, header in enumerate(headers):
            if index == subject_idx or header in _SKIP_HEADER_COLUMNS:
                continue
            if index >= len(cells) or cells[index].strip() in _EMPTY_CELL_VALUES:
                continue
            clean_label = re.sub(r"（[^）]*）", "", header)
            statements.append(EvidenceStatement(
                statement_id=f"{evidence_id}#s{len(statements)}",
                evidence_id=evidence_id,
                text=f"{subject}的{clean_label}：{cells[index].strip()}",
                field_name=clean_label, scope_key=subject,
                row_index=row_index))
    return statements


def _linearize_text(text: str, evidence_id: str) -> list[EvidenceStatement]:
    statements: list[EvidenceStatement] = []
    for row_index, sentence in enumerate(
            re.split(r"(?<=[。；！？\n])", text), start=1):
        cleaned = sentence.strip()
        if len(cleaned) >= 8:
            statements.append(EvidenceStatement(
                statement_id=f"{evidence_id}#s{len(statements)}",
                evidence_id=evidence_id, text=cleaned,
                field_name="sentence", scope_key="", row_index=row_index))
    return statements


def linearize_evidence(evidence: RetrievedEvidence,
                       ) -> list[EvidenceStatement]:
    """Convert one frozen evidence block into linearized statements."""
    text = evidence.text
    if "<table" not in text:
        return _linearize_text(text, evidence.evidence_id)
    rows = _table_rows(text)
    if not rows:
        return []
    first = "；".join(rows[0])
    if ("标识符" in first and "需求描述" in first) or (
            "方式名称" in first
            and ("运行状态" in first or "运行方式" in first)):
        # 能力表: 位置保持解析(空序号列不左移错位)
        return _linearize_capability_table(
            table_rows_positional(text), evidence.evidence_id)
    if "单位" in first and ("最大值" in first or "最小值" in first):
        # 数据表: (参数, min/max, 单位)行级事实
        return _linearize_header_table(
            table_rows_positional(text), evidence.evidence_id,
            subject_needles=("数据项", "参数"))
    if "发送方" in first and "接收方" in first:
        # 接口表: (接口, 发送方, 接收方)行级绑定
        return _linearize_header_table(
            table_rows_positional(text), evidence.evidence_id,
            subject_needles=("接口需求名称", "接口名称"))
    if "Use Case" in first or "Use case" in first or "主事件流" in text:
        return _linearize_usecase_table(rows, evidence.evidence_id)
    return _linearize_usecase_table(rows, evidence.evidence_id)


def linearize_context(evidence: tuple[RetrievedEvidence, ...],
                      ) -> list[EvidenceStatement]:
    """Linearize every block of a frozen context."""
    return [statement for block in evidence
            for statement in linearize_evidence(block)]


__all__ = ["EvidenceStatement", "linearize_evidence", "linearize_context",
           "table_rows_positional"]
