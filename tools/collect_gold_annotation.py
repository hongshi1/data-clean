r"""S7人工gold标注工作台(任务2): 回收人工标注+校验+合并输出gold_v1.jsonl.

输入(二选一, pre_annotated_v1.jsonl本身只读, 绝不覆盖):
  --tsv (默认annotation_form_v1.tsv): 在TSV表单中填写gold列;
  --in-jsonl: 直接编辑pre_annotated的副本, 完成的实例置
      annotation_status="completed"(初值pending不回收).

校验规则(逐条报错, 不静默; 协议docs/srs_project/48_localization_gold_protocol.md):
  E1 gold_verdict ∈ {support, refute, not_in_evidence}(接受缩写S/R/NIE与中文);
  E2 NIE的gold_evidence_refs必须留空(协议§4.3; "检索过但无匹配"填gold_nie_refs);
  E3 引用的evidence_id必须在本实例evidence_index中(短编号43/ev-000043/完整id
     均可, 工具展开);
  E4 gold_span若填, 必须是所引证据块文本的子串(空白不敏感; 表格块同时接受
     去HTML标签文本; 「；」分隔的refute冲突对形式各段分别命中);
  E5 INSTANCE行只填实例级gold_verdict(填refs/span/nie_refs→报错, note→警告忽略);
  W1 verdict=support/refute但refs为空 → 警告(不阻断);
  W2 判定性claim填了gold_nie_refs → 警告(不进主指标);
  W3 TSV结构错误(未知instance/claim_id、重复行、表头缺列) → 报错.

输出:
  gold_v1.jsonl  只含"完整填写且零错误"的实例; 行=silver标签文件
    (final_labels.jsonl)的兼容超集: 保留instance_id/status/claims外层字段名,
    另写final_verdict/final_model/label_source与claims[].verdict/evidence_refs
    (评测工具tools/eval_qa_module_vs_silver.py可切换标签源直接复用);
  <out>_stats.json  进度(n/108)/verdict分布/与silver及系统建议的一致率
    (预标注质量的直接测量)+全部errors/warnings.

退出码: 有error→1(零错误的实例仍会写出), 否则0.

设计约束: 模块顶层零I/O; open()一律encoding="utf-8"(TSV用utf-8-sig兼容
电子表格BOM); 无裸except; 无类型抑制; 校验失败必须可读报错.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.build_annotation_sheet import (  # noqa: E402
    INSTANCE_ROW_ID,
    TSV_COLUMNS,
    compact,
    match_system_claim,
    parse_verdict_token,
    resolve_evidence_ref,
)
from tools.build_localization_gold_template import (  # noqa: E402
    parse_gold_row,
    read_jsonl,
    write_jsonl,
)

PRE_ANNOTATED = (BASE / "data/gjb_438c/localization_gold"
                 / "pre_annotated_v1.jsonl")
ANNOTATION_TEMPLATE = (BASE / "data/gjb_438c/localization_gold"
                       / "annotation_template_v1.jsonl")
DEFAULT_TSV = (BASE / "data/gjb_438c/localization_gold"
               / "annotation_form_v1.tsv")
DEFAULT_OUT = (BASE / "data/gjb_438c/localization_gold" / "gold_v1.jsonl")

TOOL_VERSION = "s7_collect_gold_annotation_v1"
QA_TASK_TYPE = "qa_verdict"
DECISIVE_VERDICTS = ("support", "refute")
COMPLETED_STATUS = "completed"

_TAG_RE = re.compile(r"<[^>]+>")
_REF_TOKEN_SPLIT = re.compile(r"[,，;；、\s]+")


# ---------------------------------------------------------------- 纯函数内核
def ref_tokens(raw: Any) -> list[str]:
    """引用字段(TSV字符串/JSONL列表)→引用token列表; None元素跳过."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [token for token in _REF_TOKEN_SPLIT.split(raw) if token]
    if isinstance(raw, (list, tuple)):
        tokens: list[str] = []
        for item in raw:
            if item is None:
                continue
            tokens.extend(ref_tokens(str(item)))
        return tokens
    return ref_tokens(str(raw))


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text)


def span_matches_refs(span: str, block_texts: Sequence[str]) -> bool:
    """span是否为所引证据块文本的子串(协议§4.2/任务2校验E4).

    空span/空块列表→False; 整段(空白归一)命中任一块的原文**或去标签文本**
    (表格块gold span按协议取去标签行文本); 「；/;」分段的refute冲突对形式
    (协议§4.4)各段须分别命中某块.
    """
    if not block_texts:
        return False
    variants = [compact(text) for text in block_texts] + [
        compact(_strip_tags(text)) for text in block_texts]
    needle = compact(span)
    if not needle:
        return False
    if any(needle in variant for variant in variants):
        return True
    parts = [compact(part) for part in re.split(r"[；;]", span)
             if compact(part)]
    if len(parts) < 2:
        return False
    return all(any(part in variant for variant in variants)
               for part in parts)


@dataclass
class ClaimCheck:
    """一条claim的gold回收结果(verdict规范化+refs展开+校验结论)."""

    verdict: str | None
    refs: tuple[str, ...] = ()
    nie_refs: tuple[str, ...] = ()
    span: str = ""
    note: str = ""
    filled: bool = False
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _available_numbers(evidence_ids: Sequence[str]) -> str:
    numbers = [number for number in (
        _tail_number(eid) for eid in evidence_ids) if number]
    ordered = sorted(set(numbers), key=int)
    return ", ".join(ordered) if ordered else "(本实例无证据块)"


def _tail_number(evidence_id: str) -> str:
    match = re.search(r"ev-(\d+)$", str(evidence_id))
    return str(int(match.group(1))) if match else ""


def check_claim_gold(iid: str, cid: str, verdict_raw: Any, refs_raw: Any,
                     nie_refs_raw: Any, span_raw: Any, note_raw: Any,
                     evidence_ids: Sequence[str],
                     evidence_texts: dict[str, str]) -> ClaimCheck:
    """单claim校验内核(TSV单元格与JSONL字段共用).

    verdict_raw为空字符串=未填(filled=False, 非错误); 非空但解析失败=E1错误.
    """
    errors: list[str] = []
    warnings: list[str] = []
    verdict_filled = str(verdict_raw if verdict_raw is not None else "").strip()
    verdict = parse_verdict_token(verdict_filled) if verdict_filled else None
    if verdict_filled and verdict is None:
        errors.append(
            f"{iid}/{cid}: 非法gold_verdict {verdict_filled!r}"
            f"(合法: support/refute/not_in_evidence, 缩写S/R/NIE或支持/反驳/无证据)")

    refs: list[str] = []
    for token in ref_tokens(refs_raw):
        resolved = resolve_evidence_ref(token, evidence_ids)
        if resolved is None:
            errors.append(
                f"{iid}/{cid}: 引用的evidence_id必须在实例的evidence列表中: "
                f"{token!r}无法解析(可用短编号: {_available_numbers(evidence_ids)}"
                "或完整evidence_id)")
        elif resolved not in refs:
            refs.append(resolved)
    nie_refs: list[str] = []
    for token in ref_tokens(nie_refs_raw):
        resolved = resolve_evidence_ref(token, evidence_ids)
        if resolved is None:
            errors.append(
                f"{iid}/{cid}: gold_nie_refs引用{token!r}不在实例的"
                f"evidence_index中(可用短编号: {_available_numbers(evidence_ids)})")
        elif resolved not in nie_refs:
            nie_refs.append(resolved)
    if nie_refs and verdict in DECISIVE_VERDICTS:
        warnings.append(
            f"{iid}/{cid}: 判定性verdict={verdict}填了gold_nie_refs"
            "(nie_refs只用于NIE claim诊断, 不进主指标)")

    span = str(span_raw if span_raw is not None else "").strip()
    note = str(note_raw if note_raw is not None else "").strip()

    if verdict == "not_in_evidence" and refs:
        errors.append(
            f"{iid}/{cid}: NIE的gold_evidence_refs必须留空(协议§4.3);"
            " 检索过但无匹配的诊断请填gold_nie_refs")
    if verdict in DECISIVE_VERDICTS and not refs:
        warnings.append(
            f"{iid}/{cid}: verdict={verdict}但gold_refs为空"
            "(判定性verdict应标注证据块)")
    if span:
        if not refs:
            errors.append(
                f"{iid}/{cid}: 填了gold_span但gold_refs为空"
                "(span必须是所引用证据块文本的子串)")
        elif not span_matches_refs(
                span, [evidence_texts[ref] for ref in refs
                       if ref in evidence_texts]):
            errors.append(
                f"{iid}/{cid}: gold_span不是所引证据块文本的子串: {span[:40]!r}"
                "(须逐字摘自gold_refs引用的证据块; 表格块取去标签行文本;"
                " refute冲突对用「；」分隔两处摘录)")

    return ClaimCheck(verdict=verdict, refs=tuple(refs),
                      nie_refs=tuple(nie_refs), span=span, note=note,
                      filled=bool(verdict_filled), errors=tuple(errors),
                      warnings=tuple(warnings))


@dataclass
class RawClaimCells:
    """一份标注输入里一个claim的原始gold字段(未校验)."""

    verdict: str = ""
    refs: Any = ""
    nie_refs: Any = ""
    span: str = ""
    note: str = ""


@dataclass
class RawInstanceCells:
    """一份标注输入里一个实例的原始gold字段(INSTANCE行+claims)."""

    iid: str
    instance: RawClaimCells | None = None
    claims: dict[str, RawClaimCells] = field(default_factory=dict)
    touched: bool = False
    status_gated: bool = False   # JSONL模式: annotation_status=completed门控


def read_form_tsv(path: Path) -> list[dict[str, str]]:
    """读TSV表单→行列表(表头缺列/未知结构立即报错, 不静默)."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames or []
        missing = [column for column in TSV_COLUMNS
                   if column not in fieldnames]
        if missing:
            raise ValueError(
                f"TSV表头缺列: {missing}(期望列: {list(TSV_COLUMNS)}; "
                "请用tools/build_annotation_sheet.py重新生成表单)")
        rows: list[dict[str, str]] = []
        for record in reader:
            row = {column: str(record.get(column) or "")
                   for column in TSV_COLUMNS}
            if any(row.values()):
                rows.append(row)
    return rows


def parse_form_rows(form_rows: Sequence[dict[str, str]],
                    pre_by_id: dict[str, dict[str, Any]],
                    ) -> tuple[dict[str, RawInstanceCells], list[str]]:
    """TSV行→(按实例分组的原始标注, 结构错误清单)."""
    errors: list[str] = []
    instances: dict[str, RawInstanceCells] = {}
    seen: set[tuple[str, str]] = set()
    for record in form_rows:
        iid = record["instance_id"].strip()
        cid = record["claim_id"].strip()
        if not iid:
            errors.append("TSV行缺instance_id")
            continue
        pre = pre_by_id.get(iid)
        if pre is None:
            errors.append(f"未知instance_id: {iid}(不在pre_annotated中)")
            continue
        if not cid:
            errors.append(f"{iid}: TSV行缺claim_id")
            continue
        key = (iid, INSTANCE_ROW_ID if cid.upper() == INSTANCE_ROW_ID else cid)
        if key in seen:
            errors.append(f"{iid}/{cid}: 重复的TSV行(以先出现者为准)")
            continue
        seen.add(key)
        cells = RawClaimCells(
            verdict=record.get("gold_verdict", ""),
            refs=record.get("gold_refs", ""),
            nie_refs=record.get("gold_nie_refs", ""),
            span=record.get("gold_span", ""),
            note=record.get("note", ""),
        )
        instance = instances.setdefault(iid, RawInstanceCells(iid=iid))
        if cells.verdict or cells.refs or cells.nie_refs or cells.span \
                or cells.note:
            instance.touched = True
        if key[1] == INSTANCE_ROW_ID:
            instance.instance = cells
        else:
            known = {str(claim.get("claim_id", "")) for claim in
                     pre.get("claims") or []}
            if key[1] not in known:
                errors.append(
                    f"{iid}/{cid}: 未知claim_id(该实例的claim: "
                    f"{sorted(known)})")
                continue
            instance.claims[key[1]] = cells
    return instances, errors


def parse_filled_jsonl(rows: Sequence[dict[str, Any]],
                       pre_by_id: dict[str, dict[str, Any]],
                       ) -> tuple[dict[str, RawInstanceCells], list[str]]:
    """编辑过的pre_annotated副本→(completed实例的原始标注, 错误清单).

    完成门控=annotation_status=="completed"(gold字段虽预填初值,
    未置completed的实例按pending跳过, 不回收).
    """
    errors: list[str] = []
    instances: dict[str, RawInstanceCells] = {}
    seen: set[str] = set()
    for row in rows:
        iid = str(row.get("instance_id", "") or "").strip()
        if not iid:
            errors.append("JSONL行缺instance_id")
            continue
        if iid in seen:
            errors.append(f"JSONL行instance_id重复: {iid}")
            continue
        seen.add(iid)
        if iid not in pre_by_id:
            errors.append(f"未知instance_id: {iid}(不在pre_annotated中)")
            continue
        if str(row.get("annotation_status", "")) != COMPLETED_STATUS:
            continue  # pending: 人工尚未完成, 不算错误
        claims: dict[str, RawClaimCells] = {}
        for claim in row.get("claims") or []:
            if not isinstance(claim, dict):
                errors.append(f"{iid}: claims含非对象条目")
                continue
            cid = str(claim.get("claim_id", ""))
            if cid in claims:
                errors.append(f"{iid}/{cid}: JSONL行claim_id重复")
                continue
            claims[cid] = RawClaimCells(
                verdict=str(claim.get("claim_verdict", "") or ""),
                refs=claim.get("gold_evidence_refs"),
                nie_refs=claim.get("gold_nie_consulted_refs"),
                span=str(claim.get("gold_span", "") or ""),
                note=str(claim.get("annotation_note", "") or ""),
            )
        known = {str(claim.get("claim_id", "")) for claim in
                 pre_by_id[iid].get("claims") or []}
        unknown = sorted(cid for cid in claims if cid not in known)
        if unknown:
            errors.append(
                f"{iid}: 未知claim_id: {unknown}"
                f"(该实例的claim: {sorted(known)})")
        instances[iid] = RawInstanceCells(
            iid=iid,
            instance=RawClaimCells(
                verdict=str(row.get("gold_verdict", "") or "")),
            claims=claims, touched=True, status_gated=True)
    return instances, errors


@dataclass
class InstanceCheck:
    """一个实例的回收校验结论."""

    iid: str
    verdict: str | None
    claims: dict[str, ClaimCheck]
    complete: bool
    touched: bool
    status_gated: bool
    errors: list[str]
    warnings: list[str]

    @property
    def included(self) -> bool:
        return self.complete and not self.errors


def check_instance(pre_row: dict[str, Any], raw: RawInstanceCells
                   ) -> InstanceCheck:
    """实例级+claim级校验(INSTANCE行约束与完整性判定)."""
    iid = raw.iid
    evidence_ids = [str(ev.get("evidence_id", ""))
                    for ev in pre_row.get("evidence_index") or []]
    evidence_texts = {str(ev.get("evidence_id", "")): str(ev.get("text", ""))
                      for ev in pre_row.get("evidence_index") or []}
    errors: list[str] = []
    warnings: list[str] = []

    verdict: str | None = None
    if raw.instance is not None:
        # INSTANCE行只承载实例级三态判定: refs/span/nie_refs一律拒绝
        # (实例级定位=各claim的gold_evidence_refs并集, 协议§3/§7).
        verdict_filled = raw.instance.verdict.strip()
        verdict = (parse_verdict_token(verdict_filled)
                   if verdict_filled else None)
        if verdict_filled and verdict is None:
            errors.append(
                f"{iid}/{INSTANCE_ROW_ID}: 非法gold_verdict "
                f"{verdict_filled!r}(合法: support/refute/not_in_evidence,"
                " 缩写S/R/NIE或支持/反驳/无证据)")
        if ref_tokens(raw.instance.refs) or ref_tokens(
                raw.instance.nie_refs) or raw.instance.span:
            errors.append(
                f"{iid}/{INSTANCE_ROW_ID}: INSTANCE行只填gold_verdict"
                "(定位refs/span是claim级字段, 实例级定位=各claim refs并集)")
        if raw.instance.note:
            warnings.append(
                f"{iid}/{INSTANCE_ROW_ID}: INSTANCE行的note无对应字段, 已忽略"
                "(实例级理由可写在任一claim的note)")

    claim_checks: dict[str, ClaimCheck] = {}
    for claim in pre_row.get("claims") or []:
        cid = str(claim.get("claim_id", ""))
        cells = raw.claims.get(cid)
        if cells is None:
            if raw.status_gated:
                errors.append(
                    f"{iid}: annotation_status=completed但claim {cid}"
                    "缺claim_verdict")
            continue
        claim_checks[cid] = check_claim_gold(
            iid, cid, cells.verdict, cells.refs, cells.nie_refs, cells.span,
            cells.note, evidence_ids, evidence_texts)
        errors.extend(claim_checks[cid].errors)
        warnings.extend(claim_checks[cid].warnings)

    complete = (verdict is not None
                and len(claim_checks) == len(pre_row.get("claims") or [])
                and all(check.verdict is not None
                        for check in claim_checks.values()))
    return InstanceCheck(iid=iid, verdict=verdict, claims=claim_checks,
                         complete=complete, touched=raw.touched,
                         status_gated=raw.status_gated, errors=errors,
                         warnings=warnings)


def gold_output_row(pre_row: dict[str, Any], check: InstanceCheck,
                    annotator: str | None, round_no: int) -> dict[str, Any]:
    """合并产出gold行: pre_annotated行的字段全保留+人工gold值+silver兼容字段.

    silver兼容(final_labels.jsonl同名外层字段): instance_id/status/claims
    (+final_verdict/final_model/label_source)与claims[].verdict/evidence_refs.
    """
    out = copy.deepcopy(pre_row)
    out["gold_verdict"] = check.verdict
    out["annotation_status"] = COMPLETED_STATUS
    out["status"] = "final_human_gold"
    out["final_verdict"] = check.verdict
    out["final_model"] = "human"
    out["label_source"] = "human_annotation_workbench_v1"
    out["round"] = int(round_no)
    if annotator:
        out["annotator"] = annotator
    for claim in out["claims"]:
        claim_check = check.claims.get(str(claim.get("claim_id", "")))
        if claim_check is None:
            continue
        claim["claim_verdict"] = claim_check.verdict
        claim["gold_evidence_refs"] = list(claim_check.refs)
        claim["gold_nie_consulted_refs"] = list(claim_check.nie_refs)
        claim["gold_span"] = claim_check.span
        claim["annotation_note"] = claim_check.note
        claim["verdict"] = claim_check.verdict        # silver兼容字段
        claim["evidence_refs"] = list(claim_check.refs)  # silver兼容字段
    return out


# ---------------------------------------------------------------- 一致率统计
def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def agreement_counters(pre_row: dict[str, Any], check: InstanceCheck,
                       ) -> dict[str, int]:
    """一个实例对(与silver/与系统建议)一致率的计数贡献."""
    counters = {
        "inst_vs_silver_n": 0, "inst_vs_silver_hit": 0,
        "inst_vs_system_n": 0, "inst_vs_system_hit": 0,
        "claim_vs_silver_n": 0, "claim_vs_silver_hit": 0,
        "claim_vs_system_n": 0, "claim_vs_system_hit": 0,
    }
    silver_init = str(pre_row.get("gold_verdict_init")
                      or pre_row.get("gold_verdict") or "")
    counters["inst_vs_silver_n"] = 1
    counters["inst_vs_silver_hit"] = int(check.verdict == silver_init)
    if str(pre_row.get("task_type", "")) == QA_TASK_TYPE:
        system = str(pre_row.get("system_suggest_verdict", "") or "")
        counters["inst_vs_system_n"] = 1
        counters["inst_vs_system_hit"] = int(check.verdict == system)
    system_claims = pre_row.get("system_suggest_claims") or []
    for claim in pre_row.get("claims") or []:
        cid = str(claim.get("claim_id", ""))
        claim_check = check.claims.get(cid)
        if claim_check is None or claim_check.verdict is None:
            continue
        counters["claim_vs_silver_n"] += 1
        counters["claim_vs_silver_hit"] += int(
            claim_check.verdict == str(claim.get("claim_verdict", "")))
        matched, _ratio = match_system_claim(
            str(claim.get("claim_text", "")), system_claims)
        if matched is not None:
            counters["claim_vs_system_n"] += 1
            counters["claim_vs_system_hit"] += int(
                claim_check.verdict == str(
                    matched.get("system_suggest_verdict", "")))
    return counters


# ---------------------------------------------------------------- gold行终检
def validate_gold_row(row: dict[str, Any]) -> list[str]:
    """gold行(回收产物或外部文件)的协议终检: 返回问题清单(空=通过).

    供tools/finalize_gold.py导出前复用; 覆盖: schema(parse_gold_row)、
    annotation_status、silver兼容字段一致性、NIE refs、refs存在性、span子串.
    """
    iid = str(row.get("instance_id", "") or "<缺instance_id>")
    try:
        record = parse_gold_row(row)
    except ValueError as exc:
        return [f"{iid}: {exc}"]
    errors: list[str] = []
    if record.annotation_status != COMPLETED_STATUS:
        errors.append(f"{iid}: annotation_status={record.annotation_status!r}"
                      f"≠{COMPLETED_STATUS!r}(未完成的标注不得导出)")
    final_verdict = row.get("final_verdict")
    if final_verdict is not None and str(final_verdict) != record.gold_verdict:
        errors.append(
            f"{iid}: final_verdict={final_verdict!r}与gold_verdict="
            f"{record.gold_verdict!r}不一致(评测工具读final_verdict)")
    evidence_ids = [str(ev.get("evidence_id", ""))
                    for ev in row.get("evidence_index") or []]
    evidence_texts = {str(ev.get("evidence_id", "")): str(ev.get("text", ""))
                      for ev in row.get("evidence_index") or []}
    for claim in row.get("claims") or []:
        cid = str(claim.get("claim_id", ""))
        check = check_claim_gold(
            iid, cid, claim.get("claim_verdict"),
            claim.get("gold_evidence_refs"), claim.get(
                "gold_nie_consulted_refs"),
            claim.get("gold_span"), claim.get("annotation_note"),
            evidence_ids, evidence_texts)
        verdict = str(claim.get("verdict", "") or "")
        if verdict and verdict != str(claim.get("claim_verdict", "")):
            errors.append(
                f"{iid}/{cid}: silver兼容字段verdict={verdict!r}与"
                f"claim_verdict={claim.get('claim_verdict')!r}不一致")
        refs_compat = claim.get("evidence_refs")
        if refs_compat is not None and tuple(refs_compat) != tuple(
                claim.get("gold_evidence_refs") or []):
            errors.append(
                f"{iid}/{cid}: silver兼容字段evidence_refs与"
                "gold_evidence_refs不一致")
        errors.extend(check.errors)
    return errors


# ---------------------------------------------------------------- 回收主流程
def collect(pre_path: Path = PRE_ANNOTATED,
            tsv_path: Path | None = None,
            in_jsonl_path: Path | None = None,
            out_path: Path = DEFAULT_OUT,
            annotator: str | None = None,
            round_no: int = 1,
            stats_path: Path | None = None,
            ) -> dict[str, Any]:
    """回收人工标注→校验→写出gold_v1.jsonl+stats; 返回统计(含errors/warnings)."""
    if (tsv_path is None) == (in_jsonl_path is None):
        raise ValueError("必须且只能提供一个输入: --tsv或--in-jsonl")
    if out_path.resolve() == pre_path.resolve():
        raise ValueError("out_path不得指向pre_annotated(只读, 绝不覆盖)")
    if out_path.resolve() == ANNOTATION_TEMPLATE.resolve():
        raise ValueError("out_path不得指向annotation_template(标注模板)")

    pre_rows = read_jsonl(pre_path)
    pre_by_id: dict[str, dict[str, Any]] = {}
    for row in pre_rows:
        iid = str(row.get("instance_id", ""))
        if iid in pre_by_id:
            raise ValueError(f"pre_annotated行instance_id重复: {iid}")
        pre_by_id[iid] = row

    if tsv_path is not None:
        raw_instances, structural_errors = parse_form_rows(
            read_form_tsv(tsv_path), pre_by_id)
        source = {"mode": "tsv", "path": str(tsv_path)}
    else:
        raw_instances, structural_errors = parse_filled_jsonl(
            read_jsonl(in_jsonl_path), pre_by_id)
        source = {"mode": "jsonl", "path": str(in_jsonl_path)}

    checks: list[InstanceCheck] = []
    for row in pre_rows:
        iid = str(row.get("instance_id", ""))
        raw = raw_instances.get(iid)
        if raw is None:
            continue
        checks.append(check_instance(row, raw))

    included = [check for check in checks if check.included]
    excluded = [check for check in checks if not check.included]
    partial_ids = [check.iid for check in excluded
                   if check.touched and not check.status_gated
                   and not check.errors]
    error_ids = [check.iid for check in excluded if check.errors]
    pending_count = (len(pre_rows) - len(included) - len(partial_ids)
                     - len(error_ids))
    errors = list(structural_errors) + [
        error for check in excluded for error in check.errors]
    warnings = [warning for check in checks for warning in check.warnings]

    instance_dist = Counter(str(check.verdict) for check in included)
    claim_dist = Counter(
        str(claim_check.verdict) for check in included
        for claim_check in check.claims.values())
    agreement = Counter()
    for check in included:
        counters = agreement_counters(pre_by_id[check.iid], check)
        agreement.update(counters)

    if stats_path is None:
        stats_path = out_path.with_name(out_path.stem + "_stats.json")
    stats = {
        "tool_version": TOOL_VERSION,
        "source": source,
        "pre": str(pre_path),
        "output": {"gold_path": str(out_path), "stats_path": str(stats_path),
                   "n_written": len(included)},
        "progress": {
            "completed": len(included),
            "total": len(pre_rows),
            "partial": partial_ids,
            "error_excluded": error_ids,
            "pending": pending_count,
        },
        "verdict_distribution": {
            "instance": dict(sorted(instance_dist.items())),
            "claim": dict(sorted(claim_dist.items())),
        },
        "agreement": {
            "instance_vs_silver": {
                "n": agreement["inst_vs_silver_n"],
                "hits": agreement["inst_vs_silver_hit"],
                "rate": _rate(agreement["inst_vs_silver_hit"],
                              agreement["inst_vs_silver_n"])},
            "instance_vs_system_suggest": {
                "n": agreement["inst_vs_system_n"],
                "hits": agreement["inst_vs_system_hit"],
                "rate": _rate(agreement["inst_vs_system_hit"],
                              agreement["inst_vs_system_n"])},
            "claim_vs_silver": {
                "n": agreement["claim_vs_silver_n"],
                "hits": agreement["claim_vs_silver_hit"],
                "rate": _rate(agreement["claim_vs_silver_hit"],
                              agreement["claim_vs_silver_n"])},
            "claim_vs_system_suggest": {
                "n": agreement["claim_vs_system_n"],
                "hits": agreement["claim_vs_system_hit"],
                "rate": _rate(agreement["claim_vs_system_hit"],
                              agreement["claim_vs_system_n"])},
        },
        "errors": errors,
        "warnings": warnings,
        "included_instance_ids": [check.iid for check in included],
    }
    for check in excluded:
        if check.touched and not check.status_gated and not check.errors:
            missing: list[str] = []
            if check.verdict is None:
                missing.append(INSTANCE_ROW_ID)
            for claim in pre_by_id[check.iid].get("claims") or []:
                cid = str(claim.get("claim_id", ""))
                claim_check = check.claims.get(cid)
                if claim_check is None or claim_check.verdict is None:
                    missing.append(cid)
            stats["progress"]["partial_detail"] = stats["progress"].get(
                "partial_detail", []) + [{
                    "instance_id": check.iid,
                    "missing_verdict_cells": missing}]

    if included:
        rows_out = [gold_output_row(pre_by_id[check.iid], check, annotator,
                                    round_no) for check in included]
        write_jsonl(out_path, rows_out)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    return stats


# ---------------------------------------------------------------- CLI
def _reconfigure_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace(
            "-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="S7人工gold标注工作台(任务2): 回收标注+校验+产出gold_v1.jsonl")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--tsv", type=Path, default=None,
                        help=f"填好的TSV表单(默认{DEFAULT_TSV})")
    source.add_argument("--in-jsonl", type=Path, default=None,
                        help="编辑过的pre_annotated副本"
                        "(annotation_status=completed为完成标记)")
    parser.add_argument("--pre", type=Path, default=PRE_ANNOTATED,
                        help="pre_annotated JSONL(只读, 绝不覆盖)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="gold输出JSONL(默认gold_v1.jsonl)")
    parser.add_argument("--annotator", default=None,
                        help="标注员署名(写入annotator字段)")
    parser.add_argument("--round", type=int, default=1,
                        help="标注轮次(写入round字段, 仲裁轮=2)")
    return parser


def print_report(stats: dict[str, Any]) -> None:
    """人类可读回收报告(逐条报错, 不静默)."""
    progress = stats["progress"]
    print(f"标注进度: {progress['completed']}/{progress['total']}"
          f"(partial: {len(progress['partial'])},"
          f" error_excluded: {len(progress['error_excluded'])},"
          f" pending: {progress['pending']})")
    print(f"verdict分布(实例级): {stats['verdict_distribution']['instance']}")
    print(f"verdict分布(claim级): {stats['verdict_distribution']['claim']}")
    for name, key in (("silver", "instance_vs_silver"),
                      ("系统建议", "instance_vs_system_suggest")):
        block = stats["agreement"][key]
        print(f"实例级与{name}一致率: {block['hits']}/{block['n']}"
              f" = {block['rate']}")
    for name, key in (("silver", "claim_vs_silver"),
                      ("系统建议", "claim_vs_system_suggest")):
        block = stats["agreement"][key]
        print(f"claim级与{name}一致率: {block['hits']}/{block['n']}"
              f" = {block['rate']}")
    for error in stats["errors"]:
        print(f"[ERROR] {error}")
    for warning in stats["warnings"]:
        print(f"[WARN] {warning}")
    print(f"errors: {len(stats['errors'])}, warnings: "
          f"{len(stats['warnings'])}")
    print(f"gold输出: {stats['output']['gold_path']}"
          f"({stats['output']['n_written']}实例)")
    print(f"统计: {stats['output']['stats_path']}")
    print("下一步: python tools/finalize_gold.py export")


def main(argv: Sequence[str] | None = None) -> None:
    _reconfigure_stdout()
    args = build_arg_parser().parse_args(argv)
    tsv_path = args.tsv
    if tsv_path is None and args.in_jsonl is None:
        tsv_path = DEFAULT_TSV  # 无参调用: 默认读annotation_form_v1.tsv
    try:
        stats = collect(pre_path=args.pre, tsv_path=tsv_path,
                        in_jsonl_path=args.in_jsonl, out_path=args.out,
                        annotator=args.annotator, round_no=args.round)
    except FileNotFoundError as exc:
        sys.exit(f"输入文件不存在: {exc.filename}"
                 "(先生成表单: python tools/build_annotation_sheet.py)")
    print_report(stats)
    if stats["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
