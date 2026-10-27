r"""S7人工gold标注工作台(任务1): 从pre_annotated生成人类友好的标注视图.

产出两个文件(输入只读, 绝不覆盖pre_annotated_v1.jsonl):
  1. docs/srs_project/gold_annotation_sheet_v1.md
     markdown标注视图: 顶部速查指南(协议§3~§4摘要) + 每实例一节
     (Q/A摘录 + claim表[silver/系统建议/LLM span建议] + 证据块表[可引用编号]);
  2. data/gjb_438c/localization_gold/annotation_form_v1.tsv
     批量填写表单(gold列留空, 电子表格软件可直接编辑), 列见TSV_COLUMNS.

设计要点:
  - 视图只做"建议展示", gold真值由人工在TSV(或JSONL副本)中填写,
    由tools/collect_gold_annotation.py回收校验;
  - 证据块短编号(如43)是evidence_id(如S1QA-001-ev-000043)的可填缩写,
    回收工具负责展开与校验(见resolve_evidence_ref);
  - silver claims与system_suggest_claims是同一answer的两套不同分解(非1:1),
    "系统建议"列按文本相似度(difflib, 阈值MATCH_THRESHOLD)取最佳匹配,
    无匹配显示"—"(只是建议, 不参与任何校验);
  - 重跑保护: 已填写的TSV拒绝覆盖(除非--force), 防止误清空人工标注.

用法:
  python tools/build_annotation_sheet.py
  python tools/build_annotation_sheet.py --force

设计约束: 模块顶层零I/O; open()一律encoding="utf-8"(TSV读取用utf-8-sig
兼容电子表格BOM); 无裸except; 无类型抑制.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.build_localization_gold_template import read_jsonl  # noqa: E402

PRE_ANNOTATED = (BASE / "data/gjb_438c/localization_gold"
                 / "pre_annotated_v1.jsonl")
SHEET_MD = BASE / "docs/srs_project/gold_annotation_sheet_v1.md"
FORM_TSV = BASE / "data/gjb_438c/localization_gold/annotation_form_v1.tsv"
ANNOTATION_TEMPLATE = (BASE / "data/gjb_438c/localization_gold"
                       / "annotation_template_v1.jsonl")

TOOL_VERSION = "s7_annotation_workbench_v1"
QA_TASK_TYPE = "qa_verdict"
DECISIVE_VERDICTS = ("support", "refute")

# TSV列(任务1规范10列 + 2个实用扩展列):
#   evidence_ids  = 本实例可引用的证据块短编号(逗号分隔), 供批量编辑时参照;
#   gold_nie_refs = NIE claim可选的"检索过但无匹配"诊断引用(协议§4.3, 不进主指标).
TSV_COLUMNS = (
    "instance_id", "claim_id", "claim_text", "silver", "system_suggest",
    "llm_span", "evidence_ids", "gold_verdict", "gold_refs", "gold_nie_refs",
    "gold_span", "note",
)
GOLD_TSV_COLUMNS = ("gold_verdict", "gold_refs", "gold_nie_refs",
                    "gold_span", "note")
INSTANCE_ROW_ID = "INSTANCE"
INSTANCE_ROW_TEXT = "【实例级】answer整体三态判定(此行只填gold_verdict)"

MATCH_THRESHOLD = 0.5          # silver claim×system claim文本相似度阈值
Q_TRUNC = 300
A_TRUNC = 300
CLAIM_TRUNC = 100
EVIDENCE_TRUNC = 150
SPAN_TRUNC = 60
SECTION_TRUNC = 28
INSTANCE_TEXT_LABEL = "实例级整体判定"

VERDICT_SHORT = {"support": "S", "refute": "R", "not_in_evidence": "NIE"}
VERDICT_ALIASES = {
    "support": "support", "s": "support", "supp": "support", "支持": "support",
    "refute": "refute", "r": "refute", "ref": "refute", "反驳": "refute",
    "not_in_evidence": "not_in_evidence", "nie": "not_in_evidence",
    "n": "not_in_evidence", "无证据": "not_in_evidence",
}

_TAG_RE = re.compile(r"<[^>]+>")
_EVNUM_RE = re.compile(r"ev-(\d+)$")
_STATEMENT_SUFFIX = re.compile(r"#s\d+$")
_REF_TOKEN_SPLIT = re.compile(r"[,，;；、\s]+")
_SHORT_REF_RE = re.compile(r"(?:ev-?|b)?0*(\d{1,6})", re.IGNORECASE)


# ---------------------------------------------------------------- 纯函数内核
def compact(text: str) -> str:
    """空白归一(子串校验与相似度匹配的公共形态)."""
    return re.sub(r"\s+", "", str(text))


def plain_text(text: str) -> str:
    """证据块显示形态: 去HTML标签+折叠空白(gold span可从中逐字复制)."""
    return re.sub(r"\s+", " ", _TAG_RE.sub("", str(text))).strip()


def truncate(text: str, limit: int) -> str:
    """空白折叠+截断(超长加省略号)."""
    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "…"


def md_cell(text: str, limit: int | None = None) -> str:
    """markdown表格单元格: 空白折叠(+可选截断) + 竖线转义."""
    body = truncate(text, limit) if limit is not None else re.sub(
        r"\s+", " ", str(text)).strip()
    return body.replace("|", "\\|")


def verdict_short(verdict: Any) -> str:
    text = str(verdict or "")
    return VERDICT_SHORT.get(text, text or "—")


def parse_verdict_token(token: Any) -> str | None:
    """标注verdict token→规范三态; 接受全称/缩写/中文; 无法解析返回None.

    空串返回None, 由调用方区分"未填"(空)与"非法"(非空但解析失败).
    """
    if token is None:
        return None
    text = str(token).strip()
    if not text:
        return None
    return VERDICT_ALIASES.get(text.lower())


def evidence_number(evidence_id: str) -> str:
    """evidence_id尾部数字的短编号: S1QA-001-ev-000043→"43"; 无匹配→""."""
    match = _EVNUM_RE.search(str(evidence_id))
    return str(int(match.group(1))) if match else ""


def ref_numbers(refs: Any) -> list[str]:
    """引用列表的短编号展示(无尾部数字的引用原样保留)."""
    out: list[str] = []
    for ref in refs or []:
        if ref is None:
            continue
        number = evidence_number(str(ref))
        out.append(number if number else str(ref))
    return out


def resolve_evidence_ref(token: str, evidence_ids: Sequence[str]
                         ) -> str | None:
    """单个引用token→evidence_id; 解析失败返回None(调用方组织可读报错).

    接受三种形式(语句级#s后缀先归一到父块, 协议§7):
      1. 完整evidence_id(如S1QA-001-ev-000043)——直接命中;
      2. 短编号(43 / 043 / ev43 / ev-000043 / b220)——按尾部数字在本实例
         evidence列表中唯一定位(支持零填充不一致的id格式);
      3. 短编号的规范展开{instance_id}-ev-%06d——兜底(标准QA/违例id格式).
    """
    raw = str(token).strip()
    if not raw:
        return None
    raw = _STATEMENT_SUFFIX.sub("", raw)
    known = list(evidence_ids)
    if raw in known:
        return raw
    match = _SHORT_REF_RE.fullmatch(raw)
    if match:
        number = str(int(match.group(1)))
        hits = [eid for eid in known if evidence_number(eid) == number]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return None
    return None


def match_system_claim(claim_text: str,
                       system_claims: Sequence[dict[str, Any]],
                       threshold: float = MATCH_THRESHOLD,
                       ) -> tuple[dict[str, Any] | None, float]:
    """silver claim→最佳匹配的system_suggest_claim(文本相似度, 确定性).

    silver与system是同一answer的两套分解(claim数常不相等), 该匹配只用于
    "系统建议"展示与预标注质量统计, 不进入任何校验. 返回(匹配项, 相似度);
    低于阈值或无候选返回(None, 最佳相似度).
    """
    needle = compact(claim_text)
    if not needle or not system_claims:
        return None, 0.0
    best: dict[str, Any] | None = None
    best_ratio = 0.0
    for claim in system_claims:
        if not isinstance(claim, dict):
            continue
        ratio = difflib.SequenceMatcher(
            None, needle, compact(str(claim.get("claim_text", "")))).ratio()
        if ratio > best_ratio:
            best, best_ratio = claim, ratio
    if best is not None and best_ratio >= threshold:
        return best, best_ratio
    return None, best_ratio


def suggest_cell(matched: dict[str, Any] | None) -> str:
    """系统建议单元格: "NIE" / "S[43,49]"形式; 无匹配→"—"."""
    if matched is None:
        return "—"
    verdict = verdict_short(matched.get("system_suggest_verdict"))
    numbers = ref_numbers(matched.get("system_suggest_refs"))
    return f"{verdict}[{','.join(numbers)}]" if numbers else verdict


def llm_span_cell(matched: dict[str, Any] | None) -> str:
    """LLM span建议单元格: 截断+是否通过子串校验标记; 无→"—"."""
    if matched is None:
        return "—"
    span = str(matched.get("llm_suggest_span", "") or "").strip()
    if not span:
        return "—"
    mark = "✓" if matched.get("llm_suggest_span_verified") else "?"
    return f"“{md_cell(span, SPAN_TRUNC)}”{mark}"


def silver_cell(claim: dict[str, Any]) -> str:
    """silver单元格: 三态缩写; 判定性verdict附带silver引用块编号."""
    verdict = str(claim.get("claim_verdict", ""))
    hint = claim.get("silver_hint") or {}
    numbers = ref_numbers(hint.get("evidence_refs"))
    if verdict in DECISIVE_VERDICTS and numbers:
        return f"{verdict_short(verdict)}[{','.join(numbers)}]"
    return verdict_short(verdict)


# ---------------------------------------------------------------- 视图生成
@dataclass
class SheetDoc:
    """标注视图的确定性产物(markdown全文 + TSV全文 + 汇总统计)."""

    markdown: str
    tsv: str
    stats: dict[str, Any] = field(default_factory=dict)


GUIDE_MARKDOWN = """## 标注速查指南

> 依据协议 docs/srs_project/48_localization_gold_protocol.md §3~§4 摘要。
> **预填≠gold**：silver（GLM-5.3复核）与系统建议（qa_module）都只是初值/建议，须逐条确认或改判。

### 三态判定（每个claim与实例级各判一次）

| 判定 | 含义 | TSV可填缩写 |
|---|---|---|
| support | 冻结证据中有内容支撑该claim | S / 支持 |
| refute | 冻结证据中有内容与该claim冲突 | R / 反驳 |
| not_in_evidence | 冻结证据中既无支撑也无冲突 | NIE / 无证据 |

### gold refs 填法（判定依据证据块，协议§4.1）

- 判据：**删掉该块，判定依据就受损** → 选；只提供背景/主题相关但不参与判定 → 不选；
- **最小充分集**（通常1~4块），宁缺毋滥；
- refute冲突对：**两处冲突位置都要标**（缺一处冲突关系不成立）；
- 只能引用本实例「证据块」表中的编号——TSV中填短编号（如`43`）或完整evidence_id均可，多个用逗号/分号/空格分隔；
- **NIE的gold refs必须留空**（协议§4.3）：「检索过但无匹配」的诊断可选填TSV的`gold_nie_refs`列（不进主指标）；
- support/refute而refs为空 → 回收工具警告。

### gold span 填法（可选，块内定位，协议§4.2）

- = 所引证据块内足以支撑判定的**最小连续文本**（时间紧可只标块级，span覆盖率单独报告）；
- 文本块取最小支撑句；表格块取该行纯文本（去HTML标签，可直接从下方证据块表复制）；
- 必须逐字摘自所引用的证据块（空白不敏感，回收工具校验子串）；不确定/多句联合时在note说明；
- refute冲突双方摘录用`；`分隔。

### 违例条目（DOC04-VIO-*，17条，协议§4.4）

- gold_verdict=refute（真实存在的不一致）；refs=违例涉及的全部冲突块（各节已给「预填gold refs」，核对后填入，可增删；需补块时在note记块号）；
- 表81/82行级违例（V10~V12）：行级位置（如row11）写进gold_span或note；span=冲突双方原文摘录（`；`分隔）。

### TSV填写与回收

- 每实例`INSTANCE`行只填实例级gold_verdict（refs/span等其余gold列留空）；
- 填完后运行回收校验（逐条报错，不静默）：
  `$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/collect_gold_annotation.py`
  （默认读annotation_form_v1.tsv，产出gold_v1.jsonl+进度/一致率统计；也可`--in-jsonl`读编辑过的pre_annotated副本，此时以`annotation_status=completed`为完成标记）
"""


def instance_header(row: dict[str, Any]) -> str:
    iid = str(row.get("instance_id", ""))
    silver = verdict_short(row.get("gold_verdict_init")
                           or row.get("gold_verdict"))
    if str(row.get("task_type", "")) != QA_TASK_TYPE:
        category = str(row.get("category", "") or "")
        item = str(row.get("item_id", "") or "")
        tag = f"{category}[{item}]" if item else category
        return f"## {iid} (silver={silver}, system=—, 类别={tag})"
    system = verdict_short(row.get("system_suggest_verdict"))
    return f"## {iid} (silver={silver}, system={system})"


def claims_table(row: dict[str, Any]) -> str:
    is_violation = str(row.get("task_type", "")) != QA_TASK_TYPE
    system_claims = row.get("system_suggest_claims") or []
    prefill = (row["claims"][0].get("gold_evidence_refs") or []
               if is_violation and row.get("claims") else [])
    prefill_text = (f"预填:{','.join(ref_numbers(prefill))}"
                    if prefill else "____")
    lines = [
        f"| # | claim(截断{CLAIM_TRUNC}字) | silver | 系统建议 |"
        " LLM span建议 | gold verdict(待填) | gold refs(待填) |",
        "|---|---|---|---|---|---|---|",
    ]
    for claim in row.get("claims") or []:
        matched, _ratio = match_system_claim(
            str(claim.get("claim_text", "")), system_claims)
        lines.append(
            f"| {claim.get('claim_id', '')} "
            f"| {md_cell(claim.get('claim_text', ''), CLAIM_TRUNC)} "
            f"| {silver_cell(claim)} "
            f"| {suggest_cell(matched)} "
            f"| {llm_span_cell(matched)} "
            f"| ____ | {prefill_text} |")
    return "\n".join(lines)


def evidence_table(row: dict[str, Any]) -> str:
    evidence = row.get("evidence_index") or []
    if not evidence:
        return ("**证据块**：本实例冻结证据为空（全部claim只能判NIE，refs留空）。")
    lines = [
        "**证据块**（gold refs只能引用下列编号；短编号可直接填入TSV的"
        "gold_refs列，文本可整句复制为gold_span）：",
        "",
        "| 编号 | evidence_id | 类型 | 位置 | 文本(截断150字,表格已去标签) |",
        "|---|---|---|---|---|",
    ]
    for ev in evidence:
        eid = str(ev.get("evidence_id", ""))
        number = evidence_number(eid) or eid
        source_ref = ev.get("source_ref") or {}
        section = truncate(str(source_ref.get("section", "") or ""),
                           SECTION_TRUNC)
        page = source_ref.get("page")
        location = f"{section} p.{page}" if page is not None else section
        lines.append(
            f"| {number} | {eid} | {str(ev.get('source_type', ''))} "
            f"| {md_cell(location)} | {md_cell(plain_text(ev.get('text', '')), EVIDENCE_TRUNC)} |")
    return "\n".join(lines)


def instance_markdown(row: dict[str, Any]) -> str:
    lines = [instance_header(row), ""]
    if str(row.get("task_type", "")) == QA_TASK_TYPE:
        lines += [
            f"- **Q**: {md_cell(row.get('question', ''), Q_TRUNC)}",
            f"- **A**(截断{A_TRUNC}字): {md_cell(row.get('answer', ''), A_TRUNC)}",
        ]
    else:
        lines += [
            f"- **违例**: {md_cell(row.get('violation_text', ''))}",
            f"- **taxonomy**: {str(row.get('taxonomy_ref') or '—')}"
            "（协议§4.4：违例位置即预填gold定位，人工确认）",
        ]
    lines += [
        "",
        f"- **gold verdict(实例级, 待填)**: ____"
        f" ← TSV中该实例`{INSTANCE_ROW_ID}`行",
        "",
        claims_table(row),
        "",
        evidence_table(row),
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def sheet_row_values(row: dict[str, Any]) -> list[dict[str, str]]:
    """一实例→TSV行组(INSTANCE行在前, 其后c1..cN行; gold列留空)."""
    iid = str(row.get("instance_id", ""))
    is_qa = str(row.get("task_type", "")) == QA_TASK_TYPE
    evidence_numbers = ref_numbers(
        [ev.get("evidence_id") for ev in row.get("evidence_index") or []])
    system_claims = row.get("system_suggest_claims") or []

    if is_qa:
        instance_system = suggest_cell({
            "system_suggest_verdict": row.get("system_suggest_verdict"),
            "system_suggest_refs": row.get("system_suggest_refs"),
        })
    else:
        instance_system = ""
    instance_row = {
        "instance_id": iid,
        "claim_id": INSTANCE_ROW_ID,
        "claim_text": INSTANCE_ROW_TEXT,
        "silver": verdict_short(row.get("gold_verdict_init")
                                or row.get("gold_verdict")),
        "system_suggest": instance_system,
        "llm_span": "",
        "evidence_ids": ",".join(evidence_numbers),
    }
    rows = [instance_row]
    for claim in row.get("claims") or []:
        matched, _ratio = match_system_claim(
            str(claim.get("claim_text", "")), system_claims)
        rows.append({
            "instance_id": iid,
            "claim_id": str(claim.get("claim_id", "")),
            "claim_text": str(claim.get("claim_text", "") or ""),
            "silver": silver_cell(claim),
            "system_suggest": suggest_cell(matched),
            "llm_span": (str(matched.get("llm_suggest_span", "") or "")
                         if matched else ""),
            "evidence_ids": ",".join(evidence_numbers),
        })
    for entry in rows:
        for column in GOLD_TSV_COLUMNS:
            entry[column] = ""
    return rows


def build_sheet(rows: Sequence[dict[str, Any]]) -> SheetDoc:
    """pre_annotated行列表→(markdown标注视图, TSV表单, 汇总统计)."""
    if not rows:
        raise ValueError("pre_annotated为空, 无法生成标注视图")
    seen: set[str] = set()
    n_qa = n_violations = n_claims = n_matched = 0
    silver_dist: dict[str, int] = {}
    system_dist: dict[str, int] = {}
    tsv_rows: list[dict[str, str]] = []
    sections: list[str] = []
    for row in rows:
        iid = str(row.get("instance_id", ""))
        if not iid:
            raise ValueError("pre_annotated行缺instance_id")
        if iid in seen:
            raise ValueError(f"pre_annotated行instance_id重复: {iid}")
        seen.add(iid)
        claims = row.get("claims") or []
        if not claims:
            raise ValueError(f"{iid}: claims为空, 无法生成标注视图")
        is_qa = str(row.get("task_type", "")) == QA_TASK_TYPE
        if is_qa:
            n_qa += 1
            verdict = str(row.get("system_suggest_verdict", "") or "—")
            system_dist[verdict] = system_dist.get(verdict, 0) + 1
        else:
            n_violations += 1
        silver = str(row.get("gold_verdict_init")
                     or row.get("gold_verdict") or "—")
        silver_dist[silver] = silver_dist.get(silver, 0) + 1
        for claim in claims:
            n_claims += 1
            matched, _ratio = match_system_claim(
                str(claim.get("claim_text", "")),
                row.get("system_suggest_claims") or [])
            n_matched += int(matched is not None)
        tsv_rows.extend(sheet_row_values(row))
        sections.append(instance_markdown(row))

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow(TSV_COLUMNS)
    for entry in tsv_rows:
        writer.writerow([entry.get(column, "") for column in TSV_COLUMNS])

    header = [
        "# 证据定位Gold标注工作台 v1",
        "",
        f"- 实例: {len(rows)}（QA {n_qa} + 违例 {n_violations}）｜"
        f"claims: {n_claims}｜输入: data/gjb_438c/localization_gold/"
        "pre_annotated_v1.jsonl（只读）",
        "- 填写表单: data/gjb_438c/localization_gold/annotation_form_v1.tsv"
        "（gold列留空，人工填写）｜协议: docs/srs_project/"
        "48_localization_gold_protocol.md",
        f"- silver分布: {dict(sorted(silver_dist.items()))}"
        f"｜系统verdict分布: {dict(sorted(system_dist.items()))}"
        f"｜claim系统建议匹配率: {n_matched}/{n_claims}"
        f"（阈值{MATCH_THRESHOLD}）",
        "",
        GUIDE_MARKDOWN,
        "",
    ]
    markdown = "\n".join(header + sections)
    stats = {
        "tool_version": TOOL_VERSION,
        "n_instances": len(rows),
        "n_qa": n_qa,
        "n_violations": n_violations,
        "n_claims": n_claims,
        "n_claim_system_matched": n_matched,
        "claim_system_match_rate": round(n_matched / n_claims, 4)
        if n_claims else 0.0,
        "silver_verdict_distribution": dict(sorted(silver_dist.items())),
        "system_verdict_distribution": dict(sorted(system_dist.items())),
    }
    return SheetDoc(markdown=markdown, tsv=buffer.getvalue(), stats=stats)


def tsv_has_filled_gold(path: Path) -> bool:
    """已存在的TSV是否含任何填写过的gold单元格(重跑覆盖保护)."""
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for record in reader:
                for column in GOLD_TSV_COLUMNS:
                    if str(record.get(column) or "").strip():
                        return True
    except csv.Error:
        return True  # 无法解析的既有文件按"已填写"保护, 除非--force
    return False


def write_sheet(doc: SheetDoc, md_path: Path, tsv_path: Path,
                force: bool = False) -> None:
    """落盘markdown视图与TSV表单(TSV含人工填写时拒绝覆盖)."""
    if tsv_has_filled_gold(tsv_path) and not force:
        raise SystemExit(
            f"拒绝覆盖 {tsv_path}: 文件中已有人工填写的gold单元格。\n"
            "  备份后重跑, 或确信可丢弃时加 --force 重新生成空表单。")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    tsv_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(doc.markdown, encoding="utf-8")
    tsv_path.write_text(doc.tsv, encoding="utf-8")


# ---------------------------------------------------------------- CLI
def _reconfigure_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace(
            "-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="S7人工gold标注工作台(任务1): 生成markdown标注视图+TSV表单")
    parser.add_argument("--pre", type=Path, default=PRE_ANNOTATED,
                        help="pre_annotated JSONL(只读, 绝不覆盖)")
    parser.add_argument("--md", type=Path, default=SHEET_MD,
                        help="markdown标注视图输出路径")
    parser.add_argument("--tsv", type=Path, default=FORM_TSV,
                        help="TSV填写表单输出路径")
    parser.add_argument("--force", action="store_true",
                        help="TSV已含填写内容时仍强制重新生成空表单")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    _reconfigure_stdout()
    args = build_arg_parser().parse_args(argv)
    if args.pre.resolve() in {args.tsv.resolve(), args.md.resolve()}:
        raise SystemExit("--pre是只读输入, 不得作为--tsv/--md输出路径")
    if args.pre.resolve() == ANNOTATION_TEMPLATE.resolve():
        raise SystemExit("输入应为pre_annotated(含系统建议), 不是annotation_template")
    rows = read_jsonl(args.pre)
    doc = build_sheet(rows)
    write_sheet(doc, args.md, args.tsv, force=args.force)
    print(json.dumps(doc.stats, ensure_ascii=False, indent=2))
    print(f"markdown视图: {args.md}")
    print(f"TSV表单: {args.tsv}")
    print("下一步: 人工填写TSV的gold列 → python tools/collect_gold_annotation.py")


if __name__ == "__main__":
    main()
