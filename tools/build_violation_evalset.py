r"""17真实文档违例 → 端到端refute评测集(设计§6.5 real_observed专项).

背景: 论文需要"真实缺陷检测能力"证据(区别于合成变异). 04号SRS深读发现
的17个真实违例(knowledge/consistency_taxonomy_v3.json doc04_violations,
canonical清单见project_guide §2)逐条转化为(question, answer, evidence)
三元组: answer断言违例内容(或违例对应正确内容的错误版本), 系统若正确
应判refute.

answer构造原则(两类, 每条记录answer_pattern):
  assert_violation_content  answer直接断言违例内容(正逆矛盾取一侧/同ID
                            双指/错位E1/错误归属/误写文档名等)→期望refute
  assert_expected_content   违例为缺陷/缺失时, answer断言正确版本, 证据
                            中的缺陷值反对它(错别字/功能声明缺失/合格性
                            覆盖缺口)→期望refute(NIE仅当开放证据无法证明
                            缺失; 本集全部违例在冻结证据内可证伪, 逐条
                            理由见rationale_for_expectation)

证据构造: 违例涉及块(以annotation_template_v1.jsonl预填gold定位为准,
必须⊆证据集) + 邻近块, 每实例3-8块, 复用QA冻结格式
(qa_frozen/scene1_qa_frozen_v1.jsonl的evidence结构),
evidence_id沿用"{instance_id}-ev-{block:06d}"编号, completeness=open.

落盘: data/gjb_438c/localization_gold/violation_evalset_v1.jsonl (17行,
字段instance_id/question/answer/expected_verdict/violation_desc/evidence/
rationale_for_expectation等) + metadata.

用法:
  python tools/build_violation_evalset.py

设计约束: 模块顶层零I/O; open()一律encoding="utf-8"; 无裸except; 无类型
抑制; 证据块快照与04号content_list逐块校验(防漂移).
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

TEMPLATE = (BASE / "data/gjb_438c/localization_gold"
            / "annotation_template_v1.jsonl")
CONTENT_LIST = (
    BASE / "data/gjb_438c/mineru_standard"
    / "04数据统一访问服务软件需求规格说明-终稿" / "office"
    / "04数据统一访问服务软件需求规格说明-终稿_content_list.json")
OUT_DIR = BASE / "data/gjb_438c/localization_gold"
OUT = OUT_DIR / "violation_evalset_v1.jsonl"
META_OUT = OUT_DIR / "violation_evalset_v1_metadata.json"

SCHEMA = "violation_evalset_v1"
BUILDER_VERSION = "build_violation_evalset_v1"
DOC04_ID = "04数据统一访问服务软件需求规格说明-终稿"
FREEZE_ID = "doc04-violation-evalset-v1"
ANSWER_PATTERNS = ("assert_violation_content", "assert_expected_content")
VERDICTS = ("support", "refute", "not_in_evidence")
MIN_EVIDENCE = 3
MAX_EVIDENCE = 8

_SOURCE_TYPE_MAP = {"text": "text", "list": "text", "table": "table",
                    "image": "figure"}


@dataclass(frozen=True)
class ViolationSpec:
    """一条真实违例的QA转化规格(手工逐条构造, 期望verdict附理由)."""

    instance_id: str
    category: str
    item_id: str
    question: str
    answer: str
    answer_pattern: str
    expected_verdict: str
    rationale: str
    blocks: tuple[int, ...]
    target_keywords: tuple[str, ...]


# ═══════════════════════ 17条违例转化规格 ═══════════════════════
# blocks: 违例涉及块(含annotation_template预填gold块) + 邻近块.
# target_keywords: 检出信号定位用——refute理由/claim文本命中即视为
# "命中目标违例本身"(区别于共享证据中的兄弟违例).
VIOLATION_SPECS: tuple[ViolationSpec, ...] = (
    ViolationSpec(
        "DOC04-VIO-01", "identifier", "TERM-07",
        "连接池配置和连接池初始化用例的项目唯一标识符分别是什么？",
        "连接池配置用例和连接池初始化用例的项目唯一标识符均为"
        "PZXQ-GN-LJCGL-LJCCSH。",
        "assert_violation_content", "refute",
        "表39(b219)把连接池配置登记为PZXQ-GN-LJCGL-LJCPZ、连接池初始化"
        "登记为PZXQ-GN-LJCGL-LJCCSH；而节标题3.2.5.1(b220)与3.2.5.2"
        "(b225)两处均写PZXQ-GN-LJCGL-LJCCSH——同一「项目唯一标识符」被"
        "两个用例共用(TERM-07同ID双指真实违例)。answer按违例侧断言两用"
        "例共用同一ID；唯一标识符字段的唯一性语义被违反，正确的校验系统"
        "应判refute。",
        (219, 220, 221, 222, 225, 226, 227),
        ("LJCCSH", "LJCPZ")),
    ViolationSpec(
        "DOC04-VIO-02", "identifier", "TERM-07",
        "数据库关闭用例的项目唯一标识符是什么？",
        "数据库关闭能力的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGB。",
        "assert_violation_content", "refute",
        "同一能力(数据库关闭)在节标题3.2.1.1.1.4(b057)登记为"
        "PZXQ-GN-SJKCZ-SJKGB，在表4所有能力标识(b040)登记为"
        "PZXQ-GN-SJKCZ-SJKGBGN——跨位置ID冲突(TERM-07真实违例)。answer"
        "断言节标题侧的ID，表4一侧的能力登记直接反对它；answer同时被"
        "证据支持与反驳时，自相矛盾的文档应判refute。",
        (39, 40, 57, 58, 60),
        ("SJKGB",)),
    ViolationSpec(
        "DOC04-VIO-03", "identifier", "TERM-07",
        "数据统一访问服务与运行支撑服务接口的接口需求标识是什么？",
        "数据统一访问服务与运行支撑服务接口的接口需求标识为"
        "PZXQ-JK-SJTYFW-YXZCFW。",
        "assert_violation_content", "refute",
        "表48外部接口需求表(b267)把该接口登记为PZXQ-JK-SJTBGX-YXZCFW，"
        "3.3.3节标题(b271)用PZXQ-JK-SJTYFW-YXZCFW——同一接口两套前缀"
        "(TERM-07真实违例)。answer断言节标题侧标识，表48的双登记(SJTBGX"
        "还出现在3.3.4/3.3.5)反对它 → refute。",
        (262, 267, 268, 271, 274, 277),
        ("SJTBGX", "SJTYFW")),
    ViolationSpec(
        "DOC04-VIO-04", "identifier", "TERM-07",
        "代码生成与对象化访问接口的接口需求标识是什么？",
        "代码生成与对象化访问接口的接口需求标识为PZXQ-NBJK-DMSC-DXHFW。",
        "assert_violation_content", "refute",
        "表53内部接口需求表(b285)写PZXQ-NBJK-DMSC-DXHFW，3.4.2节标题"
        "(b286)写PZXQ-NBJK-DXHFW-DMSC——组件段顺序颠倒(TERM-07真实违"
        "例)。answer断言表53侧标识，节标题侧的颠倒写法反对它 → refute。",
        (280, 284, 285, 286),
        ("DMSC-DXHFW", "DXHFW-DMSC")),
    ViolationSpec(
        "DOC04-VIO-05", "identifier", "TERM-07",
        "BLOB数据插入能力的项目唯一标识符是什么？",
        "BLOB数据插入能力的项目唯一标识符为PZXQ-GN-SQLFW-BLOBSJCR。",
        "assert_violation_content", "refute",
        "表23(b139)的三个BLOB子项ID均缺BLOBSJCZ段(如PZXQ-GN-SQLFW-"
        "BLOBSJCR)，而节标题3.2.1.4.1.1(b140)用PZXQ-GN-SQLFW-BLOBSJCZ-"
        "BLOBSJCR、父节3.2.1.4(b135)也含BLOBSJCZ段——表侧ID与节侧ID不"
        "一致(TERM-07真实违例)。answer断言表23侧ID，节标题侧登记反对它"
        " → refute。",
        (135, 138, 139, 140, 145, 150),
        ("BLOBSJCR", "BLOBSJCZ")),
    ViolationSpec(
        "DOC04-VIO-06", "enumeration", "TERM-03",
        "SQL访问功能包括哪些功能？",
        "SQL访问功能包括数据库操作、修改数据、查询数据、逐行获取数据、"
        "BLOB数据操作五项功能。",
        "assert_violation_content", "refute",
        "正文3.2.1(b032)枚举5项功能，表3所有能力能力标识(b035)只有4行"
        "顶层能力——逐行获取数据被并入查询数据行的需求描述而非独立能力"
        "行(TERM-03枚举集合真实违例)。answer断言正文侧5项枚举，表3的顶"
        "层能力集合(4项)反对它 → refute。",
        (24, 30, 32, 35),
        ("逐行获取数据",)),
    ViolationSpec(
        "DOC04-VIO-07", "enumeration", "TERM-03",
        "热点数据缓存包括哪些功能？",
        "热点数据缓存包括缓存添加功能、缓存修改功能、缓存查询功能。",
        "assert_violation_content", "refute",
        "正文3.2.3(b181)枚举「缓存修改」，表32所有能力能力标识(b184)的"
        "成员是「缓存更新」——同义成员名冲突(TERM-03真实违例)。answer断"
        "言正文侧枚举，表32的封闭能力清单(标题为「所有能力能力标识」)"
        "不含「缓存修改」成员 → refute。",
        (180, 181, 183, 184, 185),
        ("缓存修改", "缓存更新")),
    ViolationSpec(
        "DOC04-VIO-08", "enumeration", "TERM-03",
        "数据统一访问服务按功能需求包含哪些功能（3.2节CSCI能力需求）？",
        "数据统一访问服务的CSCI能力需求包括统一访问功能（对象化访问、"
        "原生SQL访问、代码自动生成、数据统一访问）和访问管控功能（数据"
        "源切换、连接池管理、数据缓存、访问审计以及日志记录功能）。",
        "assert_violation_content", "refute",
        "1.2系统概述(b011)用「统一访问4项+访问管控4项」两套分类法，而"
        "3.2节CSCI能力需求(b024)与表2能力标识表(b030)的权威分类是六项："
        "SQL访问、对象化访问、代码生成、数据源适配、热点数据缓存、连接"
        "池管理(TERM-03两套分类法不一致真实违例)。answer把1.2侧分类断言"
        "为3.2的CSCI能力需求，权威清单反对它 → refute。",
        (11, 24, 30, 32),
        ("统一访问功能", "访问管控功能")),
    ViolationSpec(
        "DOC04-VIO-09", "enumeration", "LOGIC-05",
        "修改数据功能以哪些方式名称（终端形态）提供？",
        "修改数据功能的支持方式包括桌面、平板、手持。",
        "assert_expected_content", "refute",
        "表9(b067)修改数据三行与表13(b087)的方式名称列均写「平版」——"
        "错别字，应为「平板」；全文档方式名称值域为{桌面、平板、手持}"
        "(正文b032「桌面版、平板版、手持版」)。answer断言正确成员"
        "「平板」，表9/表13同列的错写值「平版」反对它(同位置值冲突；"
        "错别字是LOGIC-05分类下的真实违例) → refute。",
        (32, 63, 64, 67, 87),
        ("平版", "平板")),
    ViolationSpec(
        "DOC04-VIO-10", "traceability", "GJB-05",
        "代码生成需求追溯到任务书的哪些章节？",
        "代码生成（3.2.4）需求追溯至任务书4.1.1 c)。",
        "assert_violation_content", "refute",
        "表81 row11正向映射：代码生成3.2.4←任务书4.1.1 c)；表82 row12"
        "逆向映射：代码生成3.2.4→任务书4.1.1 a)——同一需求正逆两表目标"
        "不一致(GJB-05正逆矛盾真实违例)。answer断言正向侧映射，逆向表"
        "直接反对它 → refute。",
        (198, 405, 406, 407, 408),
        ("3.2.4",)),
    ViolationSpec(
        "DOC04-VIO-11", "traceability", "GJB-05",
        "获取错误信息需求位于本文档哪一章节？",
        "获取错误信息需求位于文档3.2.1.7章节。",
        "assert_violation_content", "refute",
        "表81 row16(b407)把获取错误信息映射到本文档3.2.1.7章节，但文档"
        "章节清单中不存在3.2.1.7——SQL访问子节从3.2.1.3(查询数据, b083)"
        "直接到3.2.1.4(BLOB数据操作, b135)，获取错误信息实际位于"
        "3.2.1.3.1.2(b093节标题)——追踪锚点失效(GJB-05真实违例)。answer"
        "断言失效锚点3.2.1.7，证据中的实际章节位置反对它 → refute。",
        (83, 87, 93, 135, 405, 406, 407),
        ("3.2.1.7", "3.2.1.3.1.2")),
    ViolationSpec(
        "DOC04-VIO-12", "traceability", "GJB-05",
        "软件研制任务书接口（4.5）章节的需求追踪至本文档的哪些章节？",
        "软件研制任务书接口（4.5）章节的需求追踪至本文档3.3和3.4章节。",
        "assert_violation_content", "refute",
        "表81 row20(b407)映射列写「接口4.5→CSCI外部接口需求/CSCI内部"
        "接口需求@3.3、3.4」，同一行的跟踪说明列却写「不追踪」——行内自"
        "相矛盾(GJB-05同行矛盾真实违例)。answer断言追踪关系成立，同行"
        "的「不追踪」声明反对它 → refute。",
        (262, 280, 405, 406, 407, 408),
        ("不追踪",)),
    ViolationSpec(
        "DOC04-VIO-13", "exception_template", "LOGIC-02",
        "缓存更新用例发生异常时系统提示什么？",
        "缓存更新发生异常时，系统提示初始化。",
        "assert_violation_content", "refute",
        "特殊case：answer断言的是文档真实但有缺陷的内容。表34(b192)缓存"
        "更新的E1字面为「系统提示初始化」，该提示关键词与用例主题(缓存"
        "/更新/sql)无重合，是从其他用例复制的错位内容(LOGIC-02 E1主题错"
        "位真实违例；b222连接池配置、b227连接池初始化的E1同样错位)。"
        "answer与E1字面一致，但判refute需要主题错位检测：E1提示内容应与"
        "所在用例主题相关，「初始化」与缓存更新主题无关——正确的校验系"
        "统应判refute(违例检出)。",
        (180, 181, 190, 191, 192, 193, 222, 227),
        ("主题错位", "初始化")),
    ViolationSpec(
        "DOC04-VIO-14", "exception_template", "LOGIC-02",
        "申请句柄和释放句柄用例属于哪个功能的扩展用例？",
        "申请句柄和释放句柄是热点数据缓存的扩展用例。",
        "assert_violation_content", "refute",
        "表37/38(b237/b242)概述写「本用例是热点数据缓存的扩展用例」，但"
        "热点数据缓存的能力清单(表32/b184)只含缓存添加、缓存更新、缓存"
        "查询，且两用例的主事件流内容(连接句柄数组、空闲句柄、连接类型)"
        "属于连接池管理域(表39/b219)——概述归属错误(LOGIC-02真实违例)。"
        "answer断言错误归属，用例自身的主事件流内容与所属能力域的清单"
        "反对它 → refute。",
        (180, 181, 184, 219, 237, 242),
        ("归属", "热点数据缓存")),
    ViolationSpec(
        "DOC04-VIO-15", "document_name", "TERM-05",
        "本软件需求规格说明对应的软件环境需求在哪个表中描述？",
        "数据同步共享服务软件环境需求见表70。",
        "assert_violation_content", "refute",
        "3.9.1节(b348)把本文档写作「数据同步共享服务」，而本文档全称是"
        "「数据统一访问服务」(b367同类引用句与全文档表caption一致)"
        "——文档名误写(TERM-05真实违例)。answer断言误写名，证据中的正确"
        "文档名反对它 → refute。",
        (347, 348, 349, 367),
        ("数据同步共享服务", "数据统一访问服务")),
    ViolationSpec(
        "DOC04-VIO-16", "function_coverage", "GJB-04",
        "数据统一访问服务是否提供访问审计及日志记录功能？",
        "数据统一访问服务提供访问审计以及日志记录功能。",
        "assert_expected_content", "refute",
        "1.2系统概述(b011)声称该功能存在，但3.2节CSCI能力需求(b024)与"
        "表2能力标识表(b030)均无对应能力条目——功能声明缺失(GJB-04真实"
        "违例：1.2的「访问审计以及日志记录」是概述级提及，非需求条款)。"
        "answer断言功能存在，权威能力清单(表2「所有能力标识」+3.2节六项"
        "分解)中无该项反对它 → refute。",
        (11, 24, 30),
        ("审计",)),
    ViolationSpec(
        "DOC04-VIO-17", "qualification_coverage", "GJB-01",
        "本文档所有章节的需求是否都规定了合格性方法？",
        "本文档3.1至3.17章节的全部需求均规定了合格性方法。",
        "assert_expected_content", "refute",
        "表80合格性规定(b404)仅6行，覆盖3.2.1~3.2.6；3.3~3.17的全部需求"
        "(如b262 CSCI外部接口需求、b280 CSCI内部接口需求——章节存在)无"
        "合格性方法——合格性覆盖缺口(GJB-01真实违例)。answer断言全覆盖"
        "关系，表80的6行封闭覆盖面反对它 → refute。",
        (24, 262, 280, 368, 404),
        ("合格性",)),
)


# ═══════════════════════ 证据构造 ═══════════════════════
def block_text(block: dict[str, Any]) -> str:
    """content_list块 → 证据文本(表块: 表体HTML+caption, 与QA冻结格式一致)."""
    if str(block.get("type")) == "table":
        body = str(block.get("table_body") or "")
        caption = block.get("table_caption") or []
        if not body.strip():
            raise ValueError("表块table_body为空")
        return body + (f"\n{caption[0]}" if caption else "")
    text = str(block.get("text") or "")
    if not text.strip():
        raise ValueError("文本块text为空")
    return text


def build_evidence(spec: ViolationSpec,
                   blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """违例spec → 证据块列表(QA冻结格式, evidence_id含块号定位)."""
    evidence: list[dict[str, Any]] = []
    for index in spec.blocks:
        if not 0 <= index < len(blocks):
            raise ValueError(
                f"{spec.instance_id}: 块索引越界 b{index:03d}")
        block = blocks[index]
        text = block_text(block)
        caption = block.get("table_caption") or block.get("image_caption") or []
        section = (str(caption[0]) if caption
                   else str(block.get("text") or ""))[:80]
        page_raw = block.get("page_idx")
        page = page_raw if isinstance(page_raw, int) else None
        block_id = f"block-{index:06d}"
        evidence.append({
            "evidence_id": f"{spec.instance_id}-ev-{index:06d}",
            "text": text,
            "source_type": _SOURCE_TYPE_MAP.get(
                str(block.get("type")), "other"),
            "source_ref": {
                "doc_id": DOC04_ID, "section": section,
                "page": page, "block_id": block_id,
                "row_id": "", "region_id": "",
            },
            "scope_id": f"{DOC04_ID}:{block_id}",
            "completeness": "open",
            "completeness_proof": (
                "Violation evalset evidence cites the involved source "
                "blocks and close neighbors only; no exhaustiveness "
                "claim."),
            "extraction_method": BUILDER_VERSION,
            "extraction_confidence": 1.0,
        })
    return evidence


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def template_violations() -> dict[str, dict[str, Any]]:
    """annotation_template_v1.jsonl的17条违例记录(instance_id → row)."""
    rows = [row for row in read_jsonl(TEMPLATE)
            if str(row.get("instance_id", "")).startswith("DOC04-VIO-")]
    return {str(row["instance_id"]): row for row in rows}


def gold_refs_from_template(spec: ViolationSpec,
                            template_row: dict[str, Any]) -> list[str]:
    """模板预填gold定位refs(须⊆证据集, 定位评测的gold基准)."""
    refs: list[str] = []
    for claim in template_row.get("claims", []):
        refs.extend(str(ref) for ref in claim.get("gold_evidence_refs", []))
    return sorted(dict.fromkeys(refs))


def build_row(spec: ViolationSpec, blocks: list[dict[str, Any]],
              template_row: dict[str, Any]) -> dict[str, Any]:
    evidence = build_evidence(spec, blocks)
    gold_refs = gold_refs_from_template(spec, template_row)
    evidence_ids = {item["evidence_id"] for item in evidence}
    missing = [ref for ref in gold_refs if ref not in evidence_ids]
    if missing:
        raise ValueError(
            f"{spec.instance_id}: 模板gold定位{missing}未包含在证据集中")
    return {
        "schema": SCHEMA,
        "instance_id": spec.instance_id,
        "task_type": "doc_violation_qa",
        "question": spec.question,
        "answer": spec.answer,
        "expected_verdict": spec.expected_verdict,
        "answer_pattern": spec.answer_pattern,
        "rationale_for_expectation": spec.rationale,
        "violation_category": spec.category,
        "item_id": spec.item_id,
        "taxonomy_ref": template_row.get("taxonomy_ref"),
        "violation_desc": template_row.get("violation_text"),
        "context_freeze_id": FREEZE_ID,
        "evidence": evidence,
        "gold_evidence_refs": gold_refs,
        "target_keywords": list(spec.target_keywords),
        "provenance": {
            "builder": BUILDER_VERSION,
            "content_list": str(CONTENT_LIST.relative_to(BASE)),
            "template": str(TEMPLATE.relative_to(BASE)),
            "gold_verdict_init_source": template_row.get(
                "gold_verdict_init_source"),
        },
    }


def validate_rows(rows: list[dict[str, Any]]) -> None:
    """17条完整性校验(字段/证据数/verdict合法/证据id唯一)."""
    if len(rows) != 17:
        raise ValueError(f"违例评测集必须17条, 实际{len(rows)}")
    ids = [row["instance_id"] for row in rows]
    if len(set(ids)) != 17:
        raise ValueError("instance_id重复")
    for row in rows:
        for field in ("instance_id", "question", "answer",
                      "expected_verdict", "answer_pattern",
                      "rationale_for_expectation", "violation_category",
                      "item_id", "violation_desc", "context_freeze_id",
                      "evidence", "gold_evidence_refs", "target_keywords"):
            if not row.get(field):
                raise ValueError(f"{row['instance_id']}: 字段{field}缺失/为空")
        if row["expected_verdict"] not in VERDICTS:
            raise ValueError(
                f"{row['instance_id']}: expected_verdict非法 "
                f"{row['expected_verdict']}")
        if row["answer_pattern"] not in ANSWER_PATTERNS:
            raise ValueError(
                f"{row['instance_id']}: answer_pattern非法 "
                f"{row['answer_pattern']}")
        n_ev = len(row["evidence"])
        if not MIN_EVIDENCE <= n_ev <= MAX_EVIDENCE:
            raise ValueError(
                f"{row['instance_id']}: 证据块数{n_ev}不在"
                f"[{MIN_EVIDENCE},{MAX_EVIDENCE}]")
        ev_ids = [item["evidence_id"] for item in row["evidence"]]
        if len(set(ev_ids)) != len(ev_ids):
            raise ValueError(f"{row['instance_id']}: evidence_id重复")
        for item in row["evidence"]:
            if not str(item.get("text", "")).strip():
                raise ValueError(
                    f"{row['instance_id']}: 证据{item['evidence_id']}文本为空")
            if not item.get("source_ref", {}).get("doc_id"):
                raise ValueError(
                    f"{row['instance_id']}: 证据{item['evidence_id']}缺doc_id")
            if item.get("completeness") != "open":
                raise ValueError(
                    f"{row['instance_id']}: 证据completeness必须为open")
        evidence_ids = set(ev_ids)
        for ref in row["gold_evidence_refs"]:
            if ref not in evidence_ids:
                raise ValueError(
                    f"{row['instance_id']}: gold定位{ref}不在证据集中")


def build_evalset(content_list_path: Path = CONTENT_LIST,
                  template_path: Path = TEMPLATE,
                  ) -> list[dict[str, Any]]:
    """构建17条违例评测集(纯函数内核, 供测试与脚本共用)."""
    blocks = json.loads(content_list_path.read_text(encoding="utf-8"))
    if len(blocks) != 411:
        raise ValueError(f"04号content_list应为411块, 实际{len(blocks)}")
    template = template_violations()
    if set(template) != {spec.instance_id for spec in VIOLATION_SPECS}:
        raise ValueError("spec与annotation_template的违例ID集不一致")
    rows = []
    for spec in VIOLATION_SPECS:
        template_row = template[spec.instance_id]
        if (str(template_row.get("category")) != spec.category
                or str(template_row.get("item_id")) != spec.item_id):
            raise ValueError(
                f"{spec.instance_id}: category/item_id与模板不一致")
        rows.append(build_row(spec, blocks, template_row))
    validate_rows(rows)
    return rows


def main() -> None:
    rows = build_evalset()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    categories: dict[str, int] = {}
    for row in rows:
        categories[row["violation_category"]] = (
            categories.get(row["violation_category"], 0) + 1)
    metadata = {
        "schema": SCHEMA,
        "builder": BUILDER_VERSION,
        "generated_at": round(time.time(), 1),
        "n_instances": len(rows),
        "expected_verdicts": {
            verdict: sum(1 for row in rows
                         if row["expected_verdict"] == verdict)
            for verdict in VERDICTS},
        "answer_patterns": {
            pattern: sum(1 for row in rows
                         if row["answer_pattern"] == pattern)
            for pattern in ANSWER_PATTERNS},
        "violation_categories": categories,
        "evidence_blocks_total": sum(len(row["evidence"]) for row in rows),
        "out": str(OUT.relative_to(BASE)),
        "notes": (
            "17真实违例→QA转化集(设计§6.5 real_observed); answer断言违例"
            "内容(assert_violation_content)或正确版本(assert_expected_"
            "content), 期望verdict均为refute, 逐条理由见每行"
            "rationale_for_expectation; 证据=违例涉及块(含模板gold定位)"
            "+邻近块, completeness=open."),
    }
    META_OUT.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"违例评测集: {len(rows)}条 → {OUT}")
    print(f"期望verdict分布: {metadata['expected_verdicts']}")
    print(f"answer_pattern分布: {metadata['answer_patterns']}")
    print(f"违例类别分布: {categories}")


if __name__ == "__main__":
    main()
