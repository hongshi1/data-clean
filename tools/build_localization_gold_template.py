r"""S7协议工具: 证据定位gold标注模板生成 + AVeriTeC式"判定∧定位"联合评分.

背景: qa_module的ClaimResult已输出evidence_refs, 但没有gold定位标注来评估
定位质量. AVeriTeC(NeurIPS'23)的结论是"判定正确≠定位正确, 两者弱相关"
(本session调研arXiv 2610.06962再次确认), 论文需要定位维度的评测.

评测对象(见 docs/srs_project/48_localization_gold_protocol.md):
  1. 91条官方QA(scene1_qa_frozen_v1.jsonl, silver标签S=6/R=8/N=77, 非gold);
  2. 17个真实文档违例(taxonomy v3 doc04_violations, 以project_guide §2
     canonical清单为准).

子命令:
  build  (默认) 生成标注模板JSONL(91+17行) + 系统预填输出JSONL + 元数据
  score  对标注完成的gold JSONL评分: VerdictAccuracy / LocalizationP/R /
         AVeriTeCScore / SpanF1 (runs协议落盘)
  kappa  双人标注一致性: 3类verdict Cohen's κ + 定位二值κ (runs协议落盘)

用法:
  python tools/build_localization_gold_template.py
  python tools/build_localization_gold_template.py build --out-dir <dir>
  python tools/build_localization_gold_template.py score \
      --gold <filled_gold.jsonl> --system system_output_v1.jsonl
  python tools/build_localization_gold_template.py kappa \
      --gold-a <A.jsonl> --gold-b <B.jsonl>

设计约束: 模块顶层零I/O(常量路径不读取); 纯函数内核进tests/; open()一律
encoding="utf-8"; 无类型抑制; 无裸except.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# ---------------------------------------------------------------- 路径常量
FROZEN_QA = (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
SILVER_LABELS = (BASE / "data/gjb_438c/runs/"
                 / "review_qa_with_glm53_582b51e5_20261021_145212"
                 / "final_labels.jsonl")
TAXONOMY = BASE / "knowledge/consistency_taxonomy_v3.json"
DOC04_CONTENT_LIST = (
    BASE / "data/gjb_438c/mineru_standard"
    / "04数据统一访问服务软件需求规格说明-终稿" / "office"
    / "04数据统一访问服务软件需求规格说明-终稿_content_list.json")
OUT_DIR = BASE / "data/gjb_438c/localization_gold"
TEMPLATE_OUT = OUT_DIR / "annotation_template_v1.jsonl"
SYSTEM_OUT = OUT_DIR / "system_output_v1.jsonl"
META_OUT = OUT_DIR / "annotation_template_v1_metadata.json"

SCHEMA_VERSION = "s7_localization_gold_v1"
TEMPLATE_VERSION = "annotation_template_v1"
BUILDER_VERSION = "s7_localization_gold_builder_v1"
VERDICTS = ("support", "refute", "not_in_evidence")
EXPECTED_QA_N = 91          # 论文锁定数字(官方QA条数)
DEFAULT_ATEC_THRESHOLD = 0.5
TAU_SWEEP = (0.0, 0.25, 0.5, 0.75, 1.0)
KAPPA_SUFFICIENT = 0.7
KAPPA_REVISE = 0.4
DOC04_ID = "04数据统一访问服务软件需求规格说明-终稿"

_SOURCE_REF_FIELDS = ("doc_id", "section", "page", "block_id", "row_id",
                      "region_id")
_SOURCE_TYPE_MAP = {"text": "text", "list": "text", "table": "table",
                    "image": "figure"}


# ---------------------------------------------------------------- 标注schema
@dataclass(frozen=True)
class GoldClaimAnnotation:
    """单条claim的定位标注(协议§3 schema).

    gold_evidence_refs: 人工标注的支持/反驳证据块ID(判定依据块);
    gold_span: 证据块内最小支撑句/行(可选);
    gold_nie_consulted_refs: NIE时可选记录"检索过但无匹配"的块(不进主指标);
    silver_hint: silver级建议(非gold, 仅供标注员参照).
    """

    claim_id: str
    claim_text: str
    claim_verdict: str
    gold_evidence_refs: tuple[str, ...] = ()
    gold_span: str = ""
    gold_nie_consulted_refs: tuple[str, ...] = ()
    annotation_note: str = ""
    silver_hint: dict[str, Any] | None = None


@dataclass(frozen=True)
class GoldAnnotationRecord:
    """一条定位gold标注记录(协议§3 schema, 与模板JSONL行一一对应)."""

    schema: str
    instance_id: str
    task_type: str
    question: str | None
    answer: str | None
    gold_verdict: str
    claims: tuple[GoldClaimAnnotation, ...]
    annotator: str | None = None
    annotator_confidence: float | None = None
    annotation_status: str = "pending"
    round: int = 1
    gold_verdict_init: str | None = None
    gold_verdict_init_source: str = ""
    category: str = ""
    item_id: str = ""
    taxonomy_ref: str | None = None
    violation_text: str | None = None
    context_freeze_id: str | None = None
    evidence_index: tuple[dict[str, Any], ...] = ()
    system_prefill: dict[str, Any] | None = None


@dataclass(frozen=True)
class CanonicalViolation:
    """canonical 17真实违例的一条(以project_guide §2清单为准)."""

    violation_id: str
    category: str
    item_id: str
    taxonomy_match: str          # 在该item的doc04_violations中唯一定位子串; ""=taxonomy无记录
    blocks: tuple[int, ...]
    label: str
    note: str = ""


# canonical 17(协议§6): 16条可在taxonomy v3 doc04_violations中唯一定位;
# V15(document_name)taxonomy无记录, 依据project_guide §2并独立核验b348.
CANONICAL_DOC04_VIOLATIONS: tuple[CanonicalViolation, ...] = (
    CanonicalViolation(
        "DOC04-VIO-01", "identifier", "TERM-07", "连接池配置/初始化同ID",
        (220, 225), "连接池配置/初始化同ID（PZXQ-GN-LJCGL-LJCCSH）"),
    CanonicalViolation(
        "DOC04-VIO-02", "identifier", "TERM-07", "数据库关闭节标题SJKGB",
        (57, 40), "数据库关闭ID跨位置矛盾（节标题SJKGB vs 表4 SJKGBGN）"),
    CanonicalViolation(
        "DOC04-VIO-03", "identifier", "TERM-07", "表48用SJTBGX前缀",
        (267, 268, 271, 274, 277),
        "表48前缀SJTBGX vs 3.3.x节标题SJTYFW"),
    CanonicalViolation(
        "DOC04-VIO-04", "identifier", "TERM-07", "表53组件顺序颠倒",
        (285, 286), "表53组件顺序颠倒（DMSC-DXHFW vs 节标题DXHFW-DMSC）"),
    CanonicalViolation(
        "DOC04-VIO-05", "identifier", "TERM-07", "表23 BLOB子项ID缺",
        (139, 140, 145, 150), "表23 BLOB子项ID缺BLOBSJCZ段"),
    CanonicalViolation(
        "DOC04-VIO-06", "enumeration", "TERM-03", "3.2.1文本说5项",
        (32, 35), "3.2.1文本5项 vs 表3仅4行"),
    CanonicalViolation(
        "DOC04-VIO-07", "enumeration", "TERM-03", "「缓存修改」",
        (181, 184), "「缓存修改」vs「缓存更新」"),
    CanonicalViolation(
        "DOC04-VIO-08", "enumeration", "TERM-03", "1.2两套分类法",
        (11, 24), "1.2两套分类法与3.2六项分类不一致"),
    CanonicalViolation(
        "DOC04-VIO-09", "enumeration", "LOGIC-05", "表9三行「平版」",
        (67, 87), "表9「平版」错别字（应为「平板」）"),
    CanonicalViolation(
        "DOC04-VIO-10", "traceability", "GJB-05", "表81 row11代码生成",
        (407, 408), "表81/82正逆追踪矛盾（代码生成 4.1.1 c) vs 4.1.1 a)）"),
    CanonicalViolation(
        "DOC04-VIO-11", "traceability", "GJB-05", "表81 row16追踪锚点失效",
        (407,), "追踪锚点失效（指向不存在的3.2.1.7节）"),
    CanonicalViolation(
        "DOC04-VIO-12", "traceability", "GJB-05", "表81 row20同行矛盾",
        (407,), "同行矛盾（映射非空+说明列写「不追踪」）"),
    CanonicalViolation(
        "DOC04-VIO-13", "exception_template", "LOGIC-02", "E1内容与用例主题错位",
        (192, 222, 227), "E1内容与用例主题错位（缓存/连接池的E1均为「系统提示初始化」）"),
    CanonicalViolation(
        "DOC04-VIO-14", "exception_template", "LOGIC-02", "申请/释放句柄概述错误归属",
        (237, 242), "申请/释放句柄错误归属「热点数据缓存的扩展用例」"),
    CanonicalViolation(
        "DOC04-VIO-15", "document_name", "TERM-05", "",
        (348,), "文档名误写「数据同步共享服务」（b348，应为「数据统一访问服务」）",
        "taxonomy v3的TERM-05 doc04_violations为空(04号上退化为用例/接口名称全局"
        "一致性); 依据project_guide §2 canonical清单, b348块内容已独立核验"),
    CanonicalViolation(
        "DOC04-VIO-16", "function_coverage", "GJB-04", "1.2声称「访问审计及日志记录功能」",
        (11,), "1.2声称审计日志但3.2/表2无对应能力——功能声明缺失"),
    CanonicalViolation(
        "DOC04-VIO-17", "qualification_coverage", "GJB-01", "表80合格性覆盖缺口",
        (404,), "表80合格性覆盖缺口（3.3~3.17全部需求无合格性方法）",
        "project_guide §2将表80违例记为GJB-06, taxonomy v3记录在GJB-01; 以taxonomy为准"),
)

VIOLATION_CATEGORY_COUNTS = {
    "identifier": 5, "enumeration": 4, "traceability": 3,
    "exception_template": 2, "document_name": 1,
    "function_coverage": 1, "qualification_coverage": 1,
}

_BLOCK_REF = re.compile(r"b(\d{3})(?!\d)")
_STATEMENT_SUFFIX = re.compile(r"#s\d+$")


def _to_block_ref(ref: str) -> str:
    """语句级引用(如ev-000043#s5)归一到父证据块(gold定位粒度=块级)."""
    return _STATEMENT_SUFFIX.sub("", ref)


def _page_index(raw: Any) -> int | None:
    """content_list的page_idx存在int与数字字符串两种形态, 统一转int."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw or "").strip()
    return int(text) if text.isdigit() else None


# ---------------------------------------------------------------- 纯函数内核
def parse_block_refs(text: str) -> tuple[int, ...]:
    """从违例描述文本解析bXXX形式的块引用(如"b220/225"→(220,))."""
    return tuple(int(m.group(1)) for m in _BLOCK_REF.finditer(text))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(body, encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_source_ref(raw: dict[str, Any] | None) -> dict[str, Any]:
    """把冻结行里的source_ref补齐为SourceRef完整6字段(qa_models约定)."""
    raw = raw or {}
    ref = {key: str(raw.get(key, "") or "") for key in _SOURCE_REF_FIELDS}
    page = raw.get("page")
    ref["page"] = int(page) if page is not None else None
    return ref


def normalize_refs(refs: Any) -> tuple[str, ...]:
    """引用列表→去空白/去重/保序的元组(None元素跳过, 不静默转成"None")."""
    if refs is None:
        return ()
    if isinstance(refs, str):
        refs = [refs]
    out: list[str] = []
    for item in refs:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            out.append(text)
    return tuple(dict.fromkeys(out))


def gold_claim_refs(record: GoldAnnotationRecord) -> tuple[str, ...]:
    """实例级gold定位集合=各claim的gold_evidence_refs并集(保序去重)."""
    merged: list[str] = []
    for claim in record.claims:
        merged.extend(claim.gold_evidence_refs)
    return tuple(dict.fromkeys(merged))


def parse_gold_row(row: dict[str, Any]) -> GoldAnnotationRecord:
    """把一行gold JSONL解析为schema校验过的记录(非法即抛ValueError)."""
    if not isinstance(row, dict):
        raise ValueError("gold row必须是JSON对象")
    required = ("instance_id", "gold_verdict", "claims")
    for key in required:
        if key not in row:
            raise ValueError(f"gold row缺字段 {key}")
    if not str(row["instance_id"]).strip():
        raise ValueError("instance_id不能为空")
    verdict = str(row["gold_verdict"])
    if verdict not in VERDICTS:
        raise ValueError(f"非法gold_verdict: {verdict!r}")
    claims_raw = row["claims"]
    if not isinstance(claims_raw, list) or not claims_raw:
        raise ValueError(f"{row['instance_id']}: claims必须是非空列表")
    claims: list[GoldClaimAnnotation] = []
    for index, claim in enumerate(claims_raw):
        if not isinstance(claim, dict):
            raise ValueError(f"{row['instance_id']}: claim[{index}]不是对象")
        claim_verdict = str(claim.get("claim_verdict", verdict))
        if claim_verdict not in VERDICTS:
            raise ValueError(
                f"{row['instance_id']} claim[{index}]: 非法claim_verdict "
                f"{claim_verdict!r}")
        gold_refs = normalize_refs(claim.get("gold_evidence_refs"))
        for ref in gold_refs:
            if not isinstance(ref, str):
                raise ValueError(f"{row['instance_id']}: gold_evidence_refs含非字符串")
        claims.append(GoldClaimAnnotation(
            claim_id=str(claim.get("claim_id", f"c{index + 1}")),
            claim_text=str(claim.get("claim_text", "")),
            claim_verdict=claim_verdict,
            gold_evidence_refs=gold_refs,
            gold_span=str(claim.get("gold_span", "") or ""),
            gold_nie_consulted_refs=normalize_refs(
                claim.get("gold_nie_consulted_refs")),
            annotation_note=str(claim.get("annotation_note", "") or ""),
            silver_hint=claim.get("silver_hint"),
        ))
    annotator_confidence = row.get("annotator_confidence")
    if annotator_confidence is not None:
        annotator_confidence = float(annotator_confidence)
        if not 0.0 <= annotator_confidence <= 1.0:
            raise ValueError(f"{row['instance_id']}: annotator_confidence须在[0,1]")
    return GoldAnnotationRecord(
        schema=str(row.get("schema", SCHEMA_VERSION)),
        instance_id=str(row["instance_id"]),
        task_type=str(row.get("task_type", "qa_verdict")),
        question=row.get("question"),
        answer=row.get("answer"),
        gold_verdict=verdict,
        claims=tuple(claims),
        annotator=row.get("annotator"),
        annotator_confidence=annotator_confidence,
        annotation_status=str(row.get("annotation_status", "pending")),
        round=int(row.get("round", 1)),
        gold_verdict_init=row.get("gold_verdict_init"),
        gold_verdict_init_source=str(row.get("gold_verdict_init_source", "")),
        category=str(row.get("category", "")),
        item_id=str(row.get("item_id", "")),
        taxonomy_ref=row.get("taxonomy_ref"),
        violation_text=row.get("violation_text"),
        context_freeze_id=row.get("context_freeze_id"),
        evidence_index=tuple(row.get("evidence_index") or ()),
        system_prefill=row.get("system_prefill"),
    )


def parse_gold_rows(rows: Sequence[dict[str, Any]]) -> list[GoldAnnotationRecord]:
    records = [parse_gold_row(row) for row in rows]
    ids = [record.instance_id for record in records]
    duplicated = sorted(
        {iid for iid in ids if ids.count(iid) > 1})
    if duplicated:
        raise ValueError(f"gold行instance_id重复: {duplicated}")
    return records


def system_refs_from_row(row: dict[str, Any]) -> tuple[str, ...]:
    """系统输出行的实例级定位集合(块级).

    约定(协议§7): 优先取行级"evidence_refs"; 否则取claims中判定为
    support/refute(判定性)的claim的evidence_refs并集——NIE claim的
    refs是"检索过未决"的诊断信息, 不是定位主张. 语句级引用(#s后缀)
    归一到父证据块, 与gold的块级粒度对齐.
    """
    if "evidence_refs" in row:
        raw = normalize_refs(row["evidence_refs"])
    else:
        merged: list[str] = []
        for claim in row.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            if str(claim.get("verdict", "")) not in ("support", "refute"):
                continue
            merged.extend(normalize_refs(claim.get("evidence_refs")))
        raw = tuple(dict.fromkeys(merged))
    return tuple(dict.fromkeys(_to_block_ref(ref) for ref in raw))


# ---------------------------------------------------------------- 评分内核
def overlap_ratio(gold_refs: tuple[str, ...],
                  system_refs: tuple[str, ...]) -> float:
    """gold覆盖率=|gold∩sys|/|gold|; AVeriTeC得分的定位项(协议§7).

    约定: gold为空(无可定位证据)时, 系统也未引用任何块=正确定位(1.0),
    引用了任何块=0.0; gold非空而系统为空=0.0.
    """
    if not gold_refs:
        return 1.0 if not system_refs else 0.0
    if not system_refs:
        return 0.0
    inter = len(set(gold_refs) & set(system_refs))
    return inter / len(gold_refs)


def localization_counts(gold_refs: tuple[str, ...],
                        system_refs: tuple[str, ...]) -> tuple[int, int, int]:
    """(|gold∩sys|, |gold|, |sys|)——micro P/R的累加基元."""
    inter = len(set(gold_refs) & set(system_refs))
    return inter, len(gold_refs), len(system_refs)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def span_char_f1(gold_span: str, pred_span: str) -> float:
    """字符级(多重集)重叠F1: 去全部空白后按字符计数求交.

    P = |公共字符|/|pred字符|, R = |公共字符|/|gold字符|; 任一侧为空→0.0.
    """
    gold = re.sub(r"\s+", "", str(gold_span))
    pred = re.sub(r"\s+", "", str(pred_span))
    if not gold or not pred:
        return 0.0
    common = Counter(gold) & Counter(pred)
    n_common = sum(common.values())
    if n_common == 0:
        return 0.0
    precision = n_common / len(pred)
    recall = n_common / len(gold)
    return 2.0 * precision * recall / (precision + recall)


def _best_span_f1(gold_spans: Sequence[str],
                  pred_spans: Sequence[str]) -> float:
    return max((span_char_f1(g, p) for g in gold_spans for p in pred_spans),
               default=0.0)


def cohen_kappa(labels_a: Sequence[str],
                labels_b: Sequence[str]) -> float:
    """Cohen's κ(类别数任意); 空输入/长度不等抛ValueError(不静默)."""
    if len(labels_a) != len(labels_b):
        raise ValueError(
            f"kappa要求两组标签等长, got {len(labels_a)} vs {len(labels_b)}")
    if not labels_a:
        raise ValueError("kappa要求非空标签序列")
    n = len(labels_a)
    categories = sorted(set(labels_a) | set(labels_b))
    observed = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    expected = sum(
        (labels_a.count(c) / n) * (labels_b.count(c) / n)
        for c in categories)
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def score_localization(gold_rows: Sequence[dict[str, Any]],
                       system_rows: Sequence[dict[str, Any]],
                       threshold: float = DEFAULT_ATEC_THRESHOLD,
                       taus: Sequence[float] = TAU_SWEEP) -> dict[str, Any]:
    """AVeriTeC式"判定∧定位"联合评分(协议§7).

    输入: gold行(schema同parse_gold_row) + 系统输出行(instance_id/verdict/
    evidence_refs或claims). 输出指标见协议文档; 未匹配id单独计数不静默丢弃.
    """
    gold_records = parse_gold_rows(gold_rows)
    system_by_id: dict[str, dict[str, Any]] = {}
    for row in system_rows:
        iid = str(row.get("instance_id", "")).strip()
        if not iid:
            raise ValueError("system行缺instance_id")
        if iid in system_by_id:
            raise ValueError(f"system行instance_id重复: {iid}")
        system_by_id[iid] = row
    gold_ids = [r.instance_id for r in gold_records]
    matched = [iid for iid in gold_ids if iid in system_by_id]
    missing_system = sorted(set(gold_ids) - set(system_by_id))
    unknown_system = sorted(set(system_by_id) - set(gold_ids))
    if not matched:
        raise ValueError("gold与system无共同instance_id, 无法评分")

    verdict_correct: list[bool] = []
    overlaps: list[float] = []
    inter_total = gold_total = sys_total = 0
    per_class: dict[str, dict[str, Any]] = {}
    span_scores: list[float] = []
    per_row: list[dict[str, Any]] = []
    for record in gold_records:
        if record.instance_id not in system_by_id:
            continue
        sys_row = system_by_id[record.instance_id]
        sys_verdict = str(sys_row.get("verdict", ""))
        if sys_verdict not in VERDICTS:
            raise ValueError(
                f"{record.instance_id}: 非法system verdict {sys_verdict!r}")
        sys_refs = system_refs_from_row(sys_row)
        gold_refs = gold_claim_refs(record)
        correct = sys_verdict == record.gold_verdict
        ratio = overlap_ratio(gold_refs, sys_refs)
        inter, n_gold, n_sys = localization_counts(gold_refs, sys_refs)
        inter_total += inter
        gold_total += n_gold
        sys_total += n_sys
        verdict_correct.append(correct)
        overlaps.append(ratio)
        cls = per_class.setdefault(record.gold_verdict, {
            "n": 0, "n_verdict_correct": 0, "n_joint": 0, "overlaps": []})
        cls["n"] += 1
        cls["n_verdict_correct"] += int(correct)
        cls["n_joint"] += int(correct and ratio >= threshold)
        cls["overlaps"].append(ratio)
        sys_spans = [str(claim.get("span") or "")
                     for claim in (sys_row.get("claims") or [])
                     if isinstance(claim, dict) and claim.get("span")]
        gold_spans = [claim.gold_span for claim in record.claims
                      if claim.gold_span]
        span_f1 = _best_span_f1(gold_spans, sys_spans) if (
            gold_spans and sys_spans) else None
        if span_f1 is not None:
            span_scores.append(span_f1)
        per_row.append({
            "instance_id": record.instance_id,
            "gold_verdict": record.gold_verdict,
            "system_verdict": sys_verdict,
            "verdict_correct": correct,
            "gold_refs": list(gold_refs),
            "system_refs": list(sys_refs),
            "overlap": round(ratio, 4),
            "joint_correct": bool(correct and ratio >= threshold),
            "span_f1": None if span_f1 is None else round(span_f1, 4),
        })
    n = len(matched)
    accuracy = sum(verdict_correct) / n
    n_correct = sum(verdict_correct)
    averitec_by_tau = {
        f"tau_{tau:.2f}": round(
            sum(1 for ok, ratio in zip(verdict_correct, overlaps)
                if ok and ratio >= tau) / n, 4)
        for tau in taus}
    class_report = {}
    for verdict, cls in sorted(per_class.items()):
        class_report[verdict] = {
            "n": cls["n"],
            "verdict_accuracy": round(cls["n_verdict_correct"] / cls["n"], 4),
            "averitec_score": round(cls["n_joint"] / cls["n"], 4),
            "mean_overlap": round(_mean(cls["overlaps"]), 4),
        }
    return {
        "protocol": "S7 localization gold (AVeriTeC-style joint scoring)",
        "schema": SCHEMA_VERSION,
        "n": n,
        "n_gold": len(gold_rows),
        "n_system": len(system_rows),
        "missing_system_ids": missing_system,
        "unknown_system_ids": unknown_system,
        "verdict_accuracy": round(accuracy, 4),
        "localization_micro_precision": (
            round(inter_total / sys_total, 4) if sys_total else None),
        "localization_micro_recall": (
            round(inter_total / gold_total, 4) if gold_total else None),
        "localization_intersection_total": inter_total,
        "localization_gold_total": gold_total,
        "localization_system_total": sys_total,
        "overlap_convention": (
            "|gold∩sys|/|gold|; gold为空时sys为空=1.0, 否则0.0"),
        "averitec_score": round(
            sum(1 for ok, ratio in zip(verdict_correct, overlaps)
                if ok and ratio >= threshold) / n, 4),
        "averitec_threshold": threshold,
        "averitec_by_threshold": averitec_by_tau,
        "localization_pass_rate_given_verdict_correct": round(
            sum(1 for ok, ratio in zip(verdict_correct, overlaps)
                if ok and ratio >= threshold) / n_correct, 4)
        if n_correct else None,
        "mean_overlap_given_verdict_correct": round(
            sum(ratio for ok, ratio in zip(verdict_correct, overlaps) if ok)
            / n_correct, 4) if n_correct else None,
        "n_verdict_correct": n_correct,
        "span_f1_macro": (round(_mean(span_scores), 4)
                          if span_scores else None),
        "n_span_scored": len(span_scores),
        "by_gold_verdict": class_report,
        "per_row": per_row,
        "notes": [
            "silver初值非gold: gold_verdict须人工确认后才进入本评分",
            "违例条目(DOC04-VIO-*)无系统输出时计入missing_system_ids, 不进指标",
            "localization的gold侧=NIE时gold_evidence_refs为空的约定见协议§4",
            "系统侧引用归一: 语句级#s后缀归一到父块, 定位粒度=块级(协议§7)",
        ],
    }


def jaccard_ratio(refs_a: tuple[str, ...],
                  refs_b: tuple[str, ...]) -> float:
    """对称集合一致率=|A∩B|/|A∪B|; 双方均空=1.0(用于标注者间一致)."""
    union = set(refs_a) | set(refs_b)
    if not union:
        return 1.0
    return len(set(refs_a) & set(refs_b)) / len(union)


def inter_annotator_report(rows_a: Sequence[dict[str, Any]],
                           rows_b: Sequence[dict[str, Any]],
                           threshold: float = DEFAULT_ATEC_THRESHOLD,
                           ) -> dict[str, Any]:
    """双人标注一致性(协议§5).

    - verdict: 3类Cohen's κ(两标注员各自的gold_verdict);
    - 定位: 各自"是否给出定位"(refs非空)的二值κ + 双方均定位实例上的
      Jaccard一致率均值(对称; 评分用的单向覆盖率只面向gold×system);
    - span: 双方都填gold_span的实例上的最佳char-F1一致率.
    """
    records_a = {r.instance_id: r for r in parse_gold_rows(rows_a)}
    records_b = {r.instance_id: r for r in parse_gold_rows(rows_b)}
    common = sorted(set(records_a) & set(records_b))
    if not common:
        raise ValueError("两份标注无共同instance_id")
    only_a = sorted(set(records_a) - set(records_b))
    only_b = sorted(set(records_b) - set(records_a))
    verdicts_a = [records_a[iid].gold_verdict for iid in common]
    verdicts_b = [records_b[iid].gold_verdict for iid in common]
    verdict_kappa = cohen_kappa(verdicts_a, verdicts_b)
    loc_labels_a: list[str] = []
    loc_labels_b: list[str] = []
    jaccards: list[float] = []
    both_empty = 0
    span_scores: list[float] = []
    for iid in common:
        refs_a = gold_claim_refs(records_a[iid])
        refs_b = gold_claim_refs(records_b[iid])
        loc_labels_a.append("located" if refs_a else "not_located")
        loc_labels_b.append("located" if refs_b else "not_located")
        if refs_a and refs_b:
            jaccards.append(jaccard_ratio(refs_a, refs_b))
        if not refs_a and not refs_b:
            both_empty += 1
        spans_a = [c.gold_span for c in records_a[iid].claims if c.gold_span]
        spans_b = [c.gold_span for c in records_b[iid].claims if c.gold_span]
        if spans_a and spans_b:
            span_scores.append(_best_span_f1(spans_a, spans_b))
    verdict_conclusion = (
        "gold效度充分(κ>=0.7)" if verdict_kappa >= KAPPA_SUFFICIENT else
        "需仲裁分歧条目(0.4<=κ<0.7)" if verdict_kappa >= KAPPA_REVISE else
        "gold体系存疑(κ<0.4)")
    return {
        "protocol": "S7 dual-annotation agreement (Cohen's kappa)",
        "threshold": threshold,
        "n_common": len(common),
        "only_in_a": only_a,
        "only_in_b": only_b,
        "verdict_kappa": round(verdict_kappa, 4),
        "verdict_raw_agreement": round(
            sum(1 for a, b in zip(verdicts_a, verdicts_b) if a == b)
            / len(common), 4),
        "verdict_conclusion": verdict_conclusion,
        "localization_kappa": round(
            cohen_kappa(loc_labels_a, loc_labels_b), 4),
        "localization_raw_agreement": round(
            sum(1 for a, b in zip(loc_labels_a, loc_labels_b) if a == b)
            / len(common), 4),
        "localization_mean_jaccard": round(_mean(jaccards), 4)
        if jaccards else None,
        "n_both_located": len(jaccards),
        "localization_both_empty_refs": both_empty,
        "span_agreement_macro": round(_mean(span_scores), 4)
        if span_scores else None,
        "n_span_compared": len(span_scores),
        "notes": [
            "定位κ: 两标注员各自'是否给出定位(refs非空)'的二值一致性",
            "Jaccard只算双方都定位的实例(对称, 不同于评分的单向gold覆盖)",
            "分歧条目进入仲裁流程(协议§5.3), 仲裁结果才是gold",
        ],
    }


# ---------------------------------------------------------------- 模板生成
def qa_template_record(frozen_row: dict[str, Any],
                       label_row: dict[str, Any],
                       system_row: dict[str, Any],
                       ) -> GoldAnnotationRecord:
    """一条QA标注模板记录: silver初值 + 空gold字段 + 系统预填 + 证据索引."""
    evidence_index = tuple({
        "evidence_id": str(ev["evidence_id"]),
        "text": str(ev["text"]),
        "source_type": str(ev.get("source_type", "other")),
        "source_ref": normalize_source_ref(ev.get("source_ref")),
        "scope_id": str(ev.get("scope_id", "")),
        "completeness": str(ev.get("completeness", "unknown")),
        "completeness_proof": str(ev.get("completeness_proof", "")),
    } for ev in frozen_row["evidence"])
    claims = tuple(GoldClaimAnnotation(
        claim_id=str(claim.get("claim_id", "")),
        claim_text=str(claim.get("claim_text", "")),
        claim_verdict=str(claim.get("verdict", "not_in_evidence")),
        gold_evidence_refs=(),
        gold_span="",
        gold_nie_consulted_refs=(),
        annotation_note="",
        silver_hint={
            "verdict": claim.get("verdict"),
            "evidence_refs": list(claim.get("evidence_refs") or []),
            "confidence": claim.get("confidence"),
        },
    ) for claim in (label_row.get("claims") or []))
    if not claims:
        raise ValueError(
            f"{frozen_row['instance_id']}: silver labels缺claims, 无法生成模板")
    return GoldAnnotationRecord(
        schema=SCHEMA_VERSION,
        instance_id=str(frozen_row["instance_id"]),
        task_type="qa_verdict",
        question=str(frozen_row["question"]),
        answer=str(frozen_row["answer"]),
        gold_verdict=str(label_row["final_verdict"]),
        claims=claims,
        annotator=None,
        annotator_confidence=None,
        annotation_status="pending",
        round=1,
        gold_verdict_init=str(label_row["final_verdict"]),
        gold_verdict_init_source=(
            "glm53_silver(final_labels.jsonl, 非gold, 人工须复核)"),
        context_freeze_id=str(frozen_row["context_freeze_id"]),
        evidence_index=evidence_index,
        system_prefill=system_row,
    )


def system_row_from_result(result: Any) -> dict[str, Any]:
    """VerificationResult→评分可用的系统输出行(复用qa_module组装约定)."""
    claims = tuple({
        "claim_id": str(claim.claim_id),
        "claim_text": str(claim.claim_text),
        "verdict": str(claim.verdict),
        "evidence_refs": list(claim.evidence_refs),
        "method": str(claim.method),
        "confidence": float(claim.confidence),
    } for claim in result.claim_results)
    decisive = sorted({
        _to_block_ref(ref) for claim in result.claim_results
        if claim.verdict in ("support", "refute")
        for ref in claim.evidence_refs})
    all_refs = sorted({
        _to_block_ref(ref) for claim in result.claim_results
        for ref in claim.evidence_refs})
    return {
        "instance_id": str(result.instance_id),
        "verdict": str(result.verdict),
        "status": str(result.status),
        "evidence_refs": decisive,
        "evidence_refs_all_claims": all_refs,
        "claims": list(claims),
    }


def violation_evidence_index(
    violation: CanonicalViolation,
    blocks: Sequence[dict[str, Any]],
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """违例→(证据块索引, 预填gold定位refs); 块快照来自04号content_list."""
    evidence: list[dict[str, Any]] = []
    refs: list[str] = []
    for index in violation.blocks:
        if not 0 <= index < len(blocks):
            raise ValueError(
                f"{violation.violation_id}: block索引越界 b{index:03d}")
        block = blocks[index]
        text = str(block.get("text") or block.get("table_body") or "")
        if not text.strip():
            raise ValueError(
                f"{violation.violation_id}: block b{index:03d} 快照为空")
        block_id = f"block-{index:06d}"
        evidence_id = f"{violation.violation_id}-ev-{index:06d}"
        caption = (block.get("table_caption") or block.get("image_caption")
                   or [])
        section = (str(caption[0]) if caption else str(block.get("text") or ""))
        evidence.append({
            "evidence_id": evidence_id,
            "text": text,
            "source_type": _SOURCE_TYPE_MAP.get(
                str(block.get("type")), "other"),
            "source_ref": {
                "doc_id": DOC04_ID, "section": section[:80],
                "page": _page_index(block.get("page_idx")),
                "block_id": block_id, "row_id": "", "region_id": "",
            },
            "scope_id": f"{DOC04_ID}:{block_id}",
            "completeness": "open",
            "completeness_proof": (
                "Violation gold location cites the involved source blocks "
                "only; no exhaustiveness claim."),
        })
        refs.append(evidence_id)
    return tuple(evidence), tuple(refs)


def build_violation_records(
    taxonomy: dict[str, Any],
    blocks: Sequence[dict[str, Any]],
) -> tuple[GoldAnnotationRecord, ...]:
    """从taxonomy v3提取canonical 17真实违例的标注模板记录(协议§6)."""
    if len(CANONICAL_DOC04_VIOLATIONS) != 17:
        raise ValueError("canonical违例清单必须恰好17条")
    items = {str(item["id"]): item for item in taxonomy["items"]}
    summary = taxonomy.get("doc04_summary") or {}
    if summary.get("total_real_violations") != 17:
        raise ValueError(
            "taxonomy doc04_summary.total_real_violations != 17, 数据漂移须重审协议")
    records: list[GoldAnnotationRecord] = []
    for violation in CANONICAL_DOC04_VIOLATIONS:
        taxonomy_ref: str | None = None
        if violation.taxonomy_match:
            item = items.get(violation.item_id)
            if item is None:
                raise ValueError(
                    f"{violation.violation_id}: taxonomy无item {violation.item_id}")
            hits = [str(text) for text in (item.get("doc04_violations") or [])
                    if violation.taxonomy_match in str(text)]
            if len(hits) != 1:
                raise ValueError(
                    f"{violation.violation_id}: taxonomy_match在"
                    f"{violation.item_id}中命中{len(hits)}条(须恰好1条)")
            violation_text = hits[0]
            position = [str(text) for text in item.get("doc04_violations") or []]
            taxonomy_ref = (f"knowledge/consistency_taxonomy_v3.json"
                            f"::items[{violation.item_id}].doc04_violations"
                            f"[{position.index(violation_text)}]")
            parsed = parse_block_refs(violation_text)
            if not set(parsed) <= set(violation.blocks):
                raise ValueError(
                    f"{violation.violation_id}: 违例文本块引用{parsed}"
                    f"不在canonical位置{violation.blocks}内")
        else:
            violation_text = violation.label
        evidence, gold_refs = violation_evidence_index(violation, blocks)
        records.append(GoldAnnotationRecord(
            schema=SCHEMA_VERSION,
            instance_id=violation.violation_id,
            task_type="doc_violation",
            question=None,
            answer=None,
            gold_verdict="refute",
            claims=(GoldClaimAnnotation(
                claim_id="c1",
                claim_text=violation_text,
                claim_verdict="refute",
                gold_evidence_refs=gold_refs,
                gold_span="",
                gold_nie_consulted_refs=(),
                annotation_note=violation.note,
                silver_hint=None,
            ),),
            gold_verdict_init="refute",
            gold_verdict_init_source=(
                "taxonomy_v3 doc04_violations + project_guide §2 canonical 17"
                " (真实违例, 违例位置即gold定位, 人工确认)"),
            category=violation.category,
            item_id=violation.item_id,
            taxonomy_ref=taxonomy_ref,
            violation_text=violation_text,
            evidence_index=evidence,
            system_prefill=None,
        ))
    return tuple(records)


def validate_template_record(record: GoldAnnotationRecord) -> list[str]:
    """模板行完整性检查(返回问题清单, 空=通过)."""
    problems: list[str] = []
    iid = record.instance_id
    if record.schema != SCHEMA_VERSION:
        problems.append(f"{iid}: schema版本不匹配")
    if record.gold_verdict not in VERDICTS:
        problems.append(f"{iid}: 非法gold_verdict")
    if not record.claims:
        problems.append(f"{iid}: claims为空")
    if record.task_type == "doc_violation":
        if record.gold_verdict != "refute":
            problems.append(f"{iid}: 违例条目gold_verdict须为refute")
        if not any(claim.gold_evidence_refs for claim in record.claims):
            problems.append(f"{iid}: 违例条目缺预填gold定位")
    known_refs = {str(ev.get("evidence_id", "")) for ev in record.evidence_index}
    for claim in record.claims:
        if claim.claim_verdict not in VERDICTS:
            problems.append(f"{iid}: 非法claim_verdict")
        unknown = [ref for ref in claim.gold_evidence_refs
                   if ref not in known_refs]
        if unknown:
            problems.append(f"{iid}: gold定位{unknown}不在evidence_index中")
    return problems


def build_template(
    frozen_path: Path = FROZEN_QA,
    labels_path: Path = SILVER_LABELS,
    taxonomy_path: Path = TAXONOMY,
    content_list_path: Path = DOC04_CONTENT_LIST,
    template_path: Path = TEMPLATE_OUT,
    system_path: Path = SYSTEM_OUT,
    meta_path: Path = META_OUT,
    use_experts: bool = True,
) -> dict[str, Any]:
    """生成标注模板(91 QA + 17违例) + 系统预填输出 + 元数据; 返回汇总."""
    from algorithms.consistency.qa_module import QAConsistencyModule
    from tools.build_answer_mutation_candidates import request_from_dict

    frozen_rows = read_jsonl(frozen_path)
    label_rows = read_jsonl(labels_path)
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    blocks = json.loads(content_list_path.read_text(encoding="utf-8"))
    if len(frozen_rows) != EXPECTED_QA_N:
        raise ValueError(f"冻结QA须为{EXPECTED_QA_N}条, got {len(frozen_rows)}")
    if len(label_rows) != len(frozen_rows):
        raise ValueError("silver标签与冻结QA行数不一致")
    if [row["instance_id"] for row in frozen_rows] != [
            row["instance_id"] for row in label_rows]:
        raise ValueError("冻结QA与silver标签instance_id未对齐")

    module = QAConsistencyModule(use_experts=use_experts)
    qa_records: list[GoldAnnotationRecord] = []
    system_rows: list[dict[str, Any]] = []
    for frozen_row, label_row in zip(frozen_rows, label_rows):
        request = request_from_dict(frozen_row)
        result = module.verify(request)
        system_row = system_row_from_result(result)
        system_rows.append(system_row)
        qa_records.append(qa_template_record(frozen_row, label_row, system_row))
    violation_records = build_violation_records(taxonomy, blocks)
    all_records = tuple(qa_records) + violation_records

    problems = [problem for record in all_records
                for problem in validate_template_record(record)]
    if problems:
        raise ValueError(f"模板完整性校验失败: {problems[:5]}")

    template_rows = [asdict(record) for record in all_records]
    write_jsonl(template_path, template_rows)
    write_jsonl(system_path, system_rows)

    silver_distribution = Counter(
        record.gold_verdict for record in qa_records)
    system_distribution = Counter(row["verdict"] for row in system_rows)
    category_distribution = Counter(
        record.category for record in violation_records)
    meta = {
        "schema": SCHEMA_VERSION,
        "template_version": TEMPLATE_VERSION,
        "builder_version": BUILDER_VERSION,
        "inputs": {
            "frozen_qa": {
                "path": str(frozen_path.relative_to(BASE)),
                "sha256": sha256_file(frozen_path)},
            "silver_labels": {
                "path": str(labels_path.relative_to(BASE)),
                "sha256": sha256_file(labels_path)},
            "taxonomy": {
                "path": str(taxonomy_path.relative_to(BASE)),
                "sha256": sha256_file(taxonomy_path)},
            "doc04_content_list": {
                "path": str(content_list_path.relative_to(BASE)),
                "sha256": sha256_file(content_list_path)},
        },
        "counts": {
            "qa": len(qa_records),
            "violations": len(violation_records),
            "total": len(all_records)},
        "silver_label_distribution": dict(sorted(silver_distribution.items())),
        "system_verdict_distribution": dict(sorted(system_distribution.items())),
        "violation_category_distribution": dict(sorted(category_distribution.items())),
        "system_prefill": {
            "module": "QAConsistencyModule",
            "use_experts": use_experts,
            "use_bge_experts": False,
            "semantic_nli": None,
            "verifier_version": "qa_verifier_v1",
            "note": "QA条目预填=系统claim_results建议(非gold); 违例条目无系统预填(S7阶段违例检测未接线)"},
        "notes": [
            "gold_verdict初值=silver(GLM-5.3复核), 非gold, 标注员必须逐条确认或改判",
            "违例条目(DOC04-VIO-*)的gold定位=违例位置预填, 标注员确认/可增删",
            "17违例以project_guide §2 canonical清单为准; taxonomy v3的doc04_violations共34条字符串, 与canonical 17的差异(去重/收录范围)见协议§6",
            "标注完成的gold建议注册进MANIFEST(重跑tools/build_data_manifest.py)",
        ],
    }
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return {
        "template_path": str(template_path),
        "system_path": str(system_path),
        "meta_path": str(meta_path),
        "n_qa": len(qa_records),
        "n_violations": len(violation_records),
        "n_total": len(all_records),
        "silver_label_distribution": dict(sorted(silver_distribution.items())),
        "system_verdict_distribution": dict(sorted(system_distribution.items())),
        "violation_category_distribution": dict(sorted(category_distribution.items())),
    }


# ---------------------------------------------------------------- CLI
def _reconfigure_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="S7定位gold标注协议: 模板生成(build)+评分(score)+κ(kappa)")
    sub = parser.add_subparsers(dest="command")
    build = sub.add_parser("build", help="生成标注模板+系统预填+元数据(默认)")
    build.add_argument("--out-dir", type=Path, default=OUT_DIR,
                       help="输出目录(默认data/gjb_438c/localization_gold)")
    score = sub.add_parser("score", help="gold×system评分(AVeriTeC式联合)")
    score.add_argument("--gold", type=Path, required=True,
                       help="标注完成的gold JSONL")
    score.add_argument("--system", type=Path, required=True,
                       help="系统输出JSONL(如system_output_v1.jsonl)")
    score.add_argument("--threshold", type=float,
                       default=DEFAULT_ATEC_THRESHOLD,
                       help=f"AVeriTeC定位阈值(默认{DEFAULT_ATEC_THRESHOLD})")
    kappa = sub.add_parser("kappa", help="双人标注一致性(κ)")
    kappa.add_argument("--gold-a", type=Path, required=True, help="标注A JSONL")
    kappa.add_argument("--gold-b", type=Path, required=True, help="标注B JSONL")
    kappa.add_argument("--threshold", type=float,
                       default=DEFAULT_ATEC_THRESHOLD,
                       help=f"定位一致判定阈值(默认{DEFAULT_ATEC_THRESHOLD})")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    _reconfigure_stdout()
    args = build_arg_parser().parse_args(argv)
    if args.command in (None, "build"):
        out_dir = getattr(args, "out_dir", OUT_DIR)
        summary = build_template(
            template_path=out_dir / TEMPLATE_OUT.name,
            system_path=out_dir / SYSTEM_OUT.name,
            meta_path=out_dir / META_OUT.name)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    if args.command == "score":
        from tools.run_utils import open_run

        gold_rows = read_jsonl(args.gold)
        system_rows = read_jsonl(args.system)
        metrics = score_localization(gold_rows, system_rows,
                                     threshold=args.threshold)
        run = open_run("score_localization", {
            "gold": str(args.gold), "system": str(args.system),
            "threshold": args.threshold})
        run.save_result(metrics)
        compact = {key: value for key, value in metrics.items()
                   if key != "per_row"}
        print(json.dumps(compact, ensure_ascii=False, indent=2))
        print(f"result.json: {run.path / 'result.json'}")
        return
    if args.command == "kappa":
        from tools.run_utils import open_run

        rows_a = read_jsonl(args.gold_a)
        rows_b = read_jsonl(args.gold_b)
        report = inter_annotator_report(rows_a, rows_b,
                                        threshold=args.threshold)
        run = open_run("kappa_localization", {
            "gold_a": str(args.gold_a), "gold_b": str(args.gold_b),
            "threshold": args.threshold})
        run.save_result(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"result.json: {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
