"""EGT (Evidence-Grounded Tri-state) 构造性对比数据合成.

首个把构造性对比数据合成(support/refute二元)推广到三态
(support/refute/NIE)的管线, MiniCheck/Auto-GDA/FISCAL均为二元:

  S (support)          已验证support的 (claim, evidence) 对原样保留;
                         语句级路径对种子语句做轻量确定性改写(语序调整/
                         数字格式/应→须/去填充词), 防premise=hypothesis平凡对;
  R (refute)           对S的claim施加确定性翻转算子——算子语义保证claim
                         与原证据矛盾(同实体ID不同值/同参数区间互斥/枚举
                         集误报/时序倒置/E1模板错配), 无需教师标注即sound;
  N (not_in_evidence)  从S的证据删除支持span/块, 或换成同文档另一条QA的
                         证据——与冻结证据协议同构: 开放scope下删除支持后
                         claim不可判定且未矛盾(模块复核verdict==NIE).

种子来源两条:
  QA路径   QAConsistencyModule 已判support且method属于可信白名单的
            claim级结果(标识符精确命中/精确语句/E1模板/时序对齐/TERM-05).
  语句路径 MinerU content_list的16文档块(text按句切分/table线性化/list
            逐条)提取结构化语句种子, 每种子独立合成S/R/N.

叙事文法路径(v2): 从16文档表格行抽取结构化事实三元组, 用真实QA answer
风格的叙事模板生成claim——R翻转值来自同表其他行(跨行绑定: 值真实存在
于文档但绑定到错误主体), N为效果性扩展断言. 修复v1负结果(近拷贝claim
让模型学到"找diff"而非叙事性跨行值断言).

R样本跨用例歧义修复(v2): e1_prompt_swap仅对scope可唯一锚定的种子应用
(matched语句scope唯一), 且翻转claim注入用例锚「在{use_case}用例中，」
——无锚的prompt替换会被证据内其他用例的真实提示重新支持(refute不
sound); 换入提示额外要求与scope模板提示compare_prompts==no(关键词
宽容匹配不残存). term_slot_swap的术语边界修复: 排除跨动词短语的
子句碎片匹配. e1_ending_flip为新增算子: 处置动词翻转(结束↔继续),
scope模板处置矛盾无歧义.

R自检(防翻转无效): 翻转后claim必须真的偏离支持证据——换入token(带左
边界字符, 防『超过』⊂『不超过』式子串误判)不出现在支持语句中, 且字符
重叠率(最长公共子串占比, 顺序敏感)严格下降; 枚举删元用成员消失自检,
步骤重排用顺序变化自检. 语句级数值翻转仅对显式算子(区间互斥)或相等
断言(值互斥)应用, 「在N内」式隐式上界扰动会产生蕴含而非矛盾, 一律
跳过. term_slot_swap/e1_prompt_swap/e1_ending_flip的矛盾非显式或依赖
scope, 额外要求模块复判不再support, 否则该翻转有歧义而跳过. N自检
(防删除无效): 删除后claim的精确匹配内容确实消失, 且模块复判verdict==
not_in_evidence.

本模块全部为纯函数: 无文件I/O、无网络、无模型调用(import期零副作用).
文件读写由 tools/build_egt_dataset.py 承担.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from algorithms.consistency.e1_expert import compare_prompts
from algorithms.consistency.evidence_statements import (
    _CELL,
    _ROW,
    _strip_tags,
    EvidenceStatement,
    linearize_context,
    linearize_evidence,
    table_rows_positional,
)
from algorithms.consistency.qa_models import (
    QAInput,
    RetrievedEvidence,
    SourceRef,
    Verdict,
)
from algorithms.consistency.qa_module import QAConsistencyModule
from algorithms.consistency.qa_router import route_question

EgtLabel = Verdict

EGT_VERSION = "egt_synthesis_v3_narrative"

#: 语句级样本的统一问句(claim与证据一致性的通用询问)
STATEMENT_QUESTION = "该声明是否与文档一致"

#: 种子白名单: 这些method的support判定可追溯到确定性证据命中
SUPPORT_SEED_METHODS: frozenset[str] = frozenset({
    "identifier_exact_match",
    "exact_statement",
    "e1_template_match",
    "sequence_alignment",
    "l0_entity_detector:TERM-05",
})

_PZXQ_ID = re.compile(r"PZXQ-[A-Z0-9]+(?:-[A-Z0-9]+)*")
_ID_ANCHOR = re.compile(
    r"^(?P<subject>.{2,24}?)的项目唯一标识符：(?P<ident>PZXQ-[A-Z0-9-]+)$")
_E1_ROW = re.compile(
    r"(?:异常流)?E\d?\s*[：:]\s*(?:系统提示)?(?P<prompt>[^，,。；;\n]{1,40})")
_CLAIM_PROMPT = re.compile(
    r"(?:提示|显示|给出|弹出|返回)(?:信息|内容)?\s*[：:]?\s*"
    r"[“\"]?(?P<prompt>[^，,。；;”\"「」]{2,40})")
_GENERIC_PROMPT = re.compile(
    r"^(?:相应|相关|对应|适当|合适|具体|详细|的|错误|警告|失败|成功|提示|异常)*"
    r"(?:信息|内容|消息|文本)?$")
_STEP_ENTRY = re.compile(
    r"(?:^|[。；;，,\n\s])\s*(?P<num>\d+)\s*[.、．:：]\s*(?P<text>[^。；;\n]{4,60})")
_TYPED_TERM = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}(?:接口|功能|服务|模块)")
_DATATYPE_TERM = re.compile(r"(?<![A-Za-z])(INT|STRING|FLOAT|LOB|BLOB)(?![A-Za-z])")
_ENUM_MARKER = re.compile(
    r"(?P<marker>分别为|如下|枚举为|清单为|只有|仅有|全部包括|共包括|所有)"
    r"(?P<rest>[：:]?\s*)(?P<items>[^。；\n]{3,120})")
_NUMERIC_CLAIM = re.compile(
    r"(?P<op>不大于|不超过|不高于|小于等于|不小于|不少于|不低于|大于等于"
    r"|至少|最多|至多|大于|超过|小于|低于|少于|等于|为)?"
    r"\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节|%|条|个|次|种|路|小时)")

_LE_OPS = ("不大于", "不超过", "不高于", "小于等于", "至多", "最多")
_GE_OPS = ("不小于", "不少于", "不低于", "大于等于", "至少")
_GT_OPS = ("大于", "超过")
_LT_OPS = ("小于", "低于", "少于")
#: 反义词取qa_module._OPERATOR_PATTERN词表内的算子, 保证模块的数值区间
#: 判定器能识别翻转后的claim(超过/低于不在其词表中)
_OP_ANTONYM = {"le": "大于", "ge": "小于", "gt": "不超过", "lt": "不小于"}

_UNIT_SWAP: dict[str, str] = {
    "ms": "s", "毫秒": "秒", "s": "ms", "秒": "毫秒",
    "min": "小时", "分钟": "小时", "小时": "分钟",
    "KB": "MB", "MB": "GB", "GB": "KB", "B": "KB", "字节": "KB",
}

#: 通用标识符(PZXQ族及其他 XX-YY-ZZ 形态), 与qa_module._IDENTIFIER同构
_GENERIC_ID = re.compile(
    r"(?<![A-Z0-9-])[A-Z]{2,8}(?:-[A-Z0-9]{1,12}){1,6}(?![A-Z0-9-])")

#: 语句级种子候选标记: 含数字/标识符/枚举引导词(任务口径: 数字/ID/枚举/参数)
_SEED_MARKER = re.compile(
    r"\d|[A-Z]{2,}-|分别为|枚举为|清单为|只有|仅有|全部包括|共包括")

#: 处置动词翻转目标(E1行的「用例结束/终止」处置)
_ENDING_VERB = re.compile(r"(?P<verb>结束|终止|中止|继续|恢复|重试)")
_ENDING_TO_OPPOSITE = {"结束": "继续", "终止": "继续", "中止": "继续",
                       "继续": "结束", "恢复": "结束", "重试": "结束"}

#: S样本语序调整: 「{主语}应{动词}{宾语}」→「{宾语}由{主语}{动词}」
_REORDER_CLAIM = re.compile(
    r"^(?P<subj>[\u4e00-\u9fffA-Za-z0-9]{2,24}?)"
    r"(?P<verb>应(?:提供|支持|完成|执行|实现|包括|包含|具备))"
    r"(?P<obj>(?:(?!应)[^。；;]){3,60})[。；;]?$")

#: S样本模态词变换: 需求动词前的「应」→「须」(同强度道义模态); 「对应/
#: 适应/不应」等非模态或否定语境不动(防语义漂移)
_DEONTIC_SWAP = re.compile(r"(?<![对适反供])应(?=[确提支满进完实执达保处遵限包规具])")

#: S样本数字格式: ≥1000的独立整数→千/万(纯格式变换, 保义; 排除
#: 编号/日期语境的数字——点分编码与日期不是数值语义)
_NUM_FORMAT = re.compile(r"(?<![\d.\-_])(?P<value>\d{4,})(?![\d.\-_年月日])")
_FILLER_WORDS = ("的", "了", "进行", "需要")

#: term_slot_swap术语边界: 含过程动词的跨度是子句碎片而非术语(「应用软件
#: 调用数据查询接口」是被动词拉长的子句, 不是可交换的槽位术语)
_TERM_VERB_BLOCK = re.compile(
    r"调用|提供|执行|支持|获取|发起|生成|完成|输出|返回|处理|输入|"
    r"部署|注册|申请|释放|校验|检测|触发|捕捉|避免|确保|发现")

#: MinerU content_list中可作证据的内容块类型
_CONTENT_BLOCK_TYPES = frozenset({"text", "table", "list"})

#: 每条语句级样本的证据窗口大小(seed块+邻近块, 任务口径3-6)
_EVIDENCE_WINDOW_SIZE = 4


# ── 基础工具 ─────────────────────────────────────────────


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _norm_list(text: str) -> str:
    return _norm(text).replace("，", "、").replace(",", "、")


def _bigrams(text: str) -> set[str]:
    compact = _norm(text)
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def bigram_containment(claim: str, reference: str) -> float:
    """claim的字符二元组有多大比例出现在reference中(集合重叠, 无序)."""
    grams = _bigrams(claim)
    if not grams:
        return 0.0
    return len(grams & _bigrams(reference)) / len(grams)


def _lcs_length(a: str, b: str) -> int:
    """最长公共(连续)子串长度, O(len(a)*len(b))滚动数组DP."""
    if not a or not b:
        return 0
    best = 0
    previous = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        current = [0] * (len(b) + 1)
        char = a[i - 1]
        for j in range(1, len(b) + 1):
            if char == b[j - 1]:
                length = previous[j - 1] + 1
                current[j] = length
                if length > best:
                    best = length
        previous = current
    return best


def char_overlap_ratio(claim: str, reference: str) -> float:
    """claim与reference的顺序敏感字符重叠率(最长公共子串/claim长度).

    R自检用『翻转后重叠率严格下降』防翻转无效: 集合型bigram重叠会把
    顺序打乱的重拼claim误判为仍然匹配(证据长文本几乎覆盖所有二元组),
    连续子串比率则要求claim作为证据的连续引用才得高分.
    """
    compact = _norm(claim)
    if not compact:
        return 0.0
    return _lcs_length(compact, _norm(reference)) / len(compact)


def evidence_to_dict(ev: RetrievedEvidence) -> dict[str, Any]:
    return {
        "evidence_id": ev.evidence_id,
        "text": ev.text,
        "source_type": ev.source_type,
        "source_ref": {
            "doc_id": ev.source_ref.doc_id,
            "section": ev.source_ref.section,
            "page": ev.source_ref.page,
            "block_id": ev.source_ref.block_id,
            "row_id": ev.source_ref.row_id,
            "region_id": ev.source_ref.region_id,
        },
        "scope_id": ev.scope_id,
        "completeness": ev.completeness,
        "completeness_proof": ev.completeness_proof,
        "extraction_method": ev.extraction_method,
        "extraction_confidence": ev.extraction_confidence,
    }


def evidence_from_dict(item: Mapping[str, Any]) -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=str(item["evidence_id"]),
        text=str(item["text"]),
        source_type=item["source_type"],
        source_ref=SourceRef(**dict(item["source_ref"])),
        scope_id=str(item["scope_id"]),
        completeness=item.get("completeness", "unknown"),
        completeness_proof=str(item.get("completeness_proof", "")),
        extraction_method=str(item.get("extraction_method", "")),
        extraction_confidence=item.get("extraction_confidence"),
    )


# ── 种子收集 ─────────────────────────────────────────────


@dataclass(frozen=True)
class SupportSeed:
    """一条已验证support的claim级种子(含其完整冻结证据)."""

    instance_id: str
    question: str
    claim_id: str
    claim_text: str
    method: str
    raw_evidence_refs: tuple[str, ...]
    evidence: tuple[RetrievedEvidence, ...]
    context_freeze_id: str

    @property
    def seed_id(self) -> str:
        return f"{self.instance_id}:{self.claim_id}"

    @property
    def ref_blocks(self) -> frozenset[str]:
        return frozenset(ref.split("#", 1)[0] for ref in self.raw_evidence_refs)


def collect_support_seeds(
    requests: Sequence[QAInput],
    module: QAConsistencyModule,
    allowed_methods: frozenset[str] = SUPPORT_SEED_METHODS,
) -> list[SupportSeed]:
    """跑当前验证系统, 收集白名单method的support claim级结果作种子."""
    seeds: list[SupportSeed] = []
    for request in requests:
        result = module.verify(request)
        for claim in result.claim_results:
            if claim.verdict != "support" or claim.method not in allowed_methods:
                continue
            if not claim.evidence_refs:
                continue
            seeds.append(SupportSeed(
                instance_id=request.instance_id,
                question=request.question,
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                method=claim.method,
                raw_evidence_refs=tuple(claim.evidence_refs),
                evidence=request.evidence,
                context_freeze_id=request.context_freeze_id,
            ))
    return seeds


# ── 语句级种子: MinerU content_list块 → 结构化语句 ─────────


_SENTENCE_SPLIT = re.compile(r"(?<=[。；！？\n])")


def _text_statements(text: str) -> list[tuple[int, str]]:
    """text块按句切分; 返回(语句序号0基, 语句), 序号与_delete_sentences的
    1基计数对齐(删除索引 = 序号+1)."""
    out: list[tuple[int, str]] = []
    index = 0
    for part in _SENTENCE_SPLIT.split(text):
        cleaned = part.strip()
        if len(cleaned) >= 8:
            out.append((index, cleaned))
            index += 1
    return out


@dataclass(frozen=True)
class StatementSeed:
    """一条来自MinerU content_list块的结构化语句种子."""

    doc_id: str
    block_idx: int
    statement_id: str
    statement_text: str
    field_name: str
    scope_key: str
    block_type: str
    delete_mode: str      # sentence | row | list_item
    delete_index: int     # sentence: 1基≥8字符句序; row: 表行序; list_item: 条目序

    @property
    def seed_id(self) -> str:
        return f"{self.doc_id}:{self.statement_id}"

    @property
    def context_freeze_id(self) -> str:
        return f"stmt-{self.doc_id}-v1"

    def is_e1_statement(self) -> bool:
        return ("异常流" in self.field_name
                or _E1_ROW.search(self.statement_text) is not None)


def _block_plain_text(block: Mapping[str, Any]) -> str:
    """MinerU块的纯文本形态(表格保留HTML, 与证据构造一致)."""
    btype = str(block.get("type", ""))
    if btype == "table":
        return str(block.get("table_body", ""))
    if btype == "list":
        return "；".join(str(item) for item in block.get("list_items", []))
    return str(block.get("text", ""))


def mineru_block_to_evidence(doc_id: str, block_idx: int,
                             block: Mapping[str, Any],
                             ) -> RetrievedEvidence:
    """MinerU content_list块 → RetrievedEvidence(表格保留原始HTML, 供
    模块的数值/枚举/标识符通道与线性化语句通道共用)."""
    text = _block_plain_text(block)
    source_type = "table" if str(block.get("type", "")) == "table" else "text"
    block_id = f"b{block_idx:03d}"
    page = block.get("page_idx")
    return RetrievedEvidence(
        evidence_id=f"{doc_id}#{block_id}",
        text=text,
        source_type=source_type,
        source_ref=SourceRef(doc_id=doc_id, section="", page=page,
                             block_id=block_id),
        scope_id=f"{doc_id}:{block_id}",
        completeness="open",
        completeness_proof="MinerU content_list block frozen verbatim; open scope.",
        extraction_method="mineru_content_list",
        extraction_confidence=None,
    )


def collect_statement_seeds(
    blocks: Sequence[Mapping[str, Any]],
    doc_id: str,
) -> list[StatementSeed]:
    """从MinerU content_list块提取结构化语句种子.

    - text块: 按句切分(。；！？换行), 含数字/ID/枚举标记且≥12字的句子;
    - table块: evidence_statements线性化逐行成句(≥10字), 保留scope_key;
    - list块: 逐条(含标记且≥12字).
    """
    seeds: list[StatementSeed] = []
    for idx, block in enumerate(blocks):
        btype = str(block.get("type", ""))
        block_id = f"b{idx:03d}"
        if btype == "text":
            for index, sentence in _text_statements(str(block.get("text", ""))):
                if len(sentence) >= 12 and _SEED_MARKER.search(sentence):
                    seeds.append(StatementSeed(
                        doc_id=doc_id, block_idx=idx,
                        statement_id=f"{block_id}#s{index}",
                        statement_text=sentence, field_name="sentence",
                        scope_key="", block_type="text",
                        delete_mode="sentence", delete_index=index + 1))
        elif btype == "table":
            evidence = mineru_block_to_evidence(doc_id, idx, block)
            for stmt in linearize_evidence(evidence):
                if len(stmt.text) < 10:
                    continue
                seeds.append(StatementSeed(
                    doc_id=doc_id, block_idx=idx,
                    statement_id=f"{block_id}#{stmt.statement_id.split('#')[-1]}",
                    statement_text=stmt.text, field_name=stmt.field_name,
                    scope_key=stmt.scope_key, block_type="table",
                    delete_mode="row", delete_index=stmt.row_index))
        elif btype == "list":
            items = [str(item) for item in block.get("list_items", [])]
            for index, item in enumerate(items):
                if len(item.strip()) >= 12 and _SEED_MARKER.search(item):
                    seeds.append(StatementSeed(
                        doc_id=doc_id, block_idx=idx,
                        statement_id=f"{block_id}#i{index}",
                        statement_text=item.strip(), field_name="list_item",
                        scope_key="", block_type="list",
                        delete_mode="list_item", delete_index=index))
    return seeds


def statement_evidence_window(
    seed: StatementSeed,
    blocks: Sequence[Mapping[str, Any]],
    size: int = _EVIDENCE_WINDOW_SIZE,
) -> tuple[RetrievedEvidence, ...]:
    """seed所在块+同doc邻近内容块(模拟检索上下文), 确定性环形外扩."""
    chosen = [seed.block_idx]
    radius = 1
    while (len(chosen) < size
           and (seed.block_idx - radius >= 0
                or seed.block_idx + radius < len(blocks))):
        for offset in (seed.block_idx - radius, seed.block_idx + radius):
            if len(chosen) >= size:
                break
            if (0 <= offset < len(blocks) and offset not in chosen
                    and str(blocks[offset].get("type", ""))
                    in _CONTENT_BLOCK_TYPES):
                chosen.append(offset)
        radius += 1
    return tuple(mineru_block_to_evidence(seed.doc_id, j, blocks[j])
                 for j in sorted(chosen))


def _statement_module_verdict(
    module: QAConsistencyModule | None,
    doc_id: str,
    claim_text: str,
    evidence: tuple[RetrievedEvidence, ...],
    freeze_id: str,
) -> str | None:
    if module is None or not evidence:
        return None
    request = QAInput(
        instance_id=f"{doc_id}-egt-stmt",
        question=STATEMENT_QUESTION,
        answer=claim_text,
        context_freeze_id=freeze_id,
        evidence=tuple(evidence),
    )
    return module.verify(request).verdict


def claim_matches_statement(claim_text: str, statement: EvidenceStatement,
                            method: str) -> bool:
    """claim与单条线性化语句的支持性匹配(用于删除后自检)."""
    if method == "identifier_exact_match":
        ids = _PZXQ_ID.findall(claim_text)
        if ids:
            return any(identifier in statement.text for identifier in ids)
    compact = _norm(claim_text)
    if compact and compact in _norm(statement.text):
        return True
    return bigram_containment(claim_text, statement.text) >= 0.5


def seed_matching_statements(seed: SupportSeed) -> list[EvidenceStatement]:
    """定位种子claim的支持语句(优先显式引用的statement id)."""
    statements = linearize_context(seed.evidence)
    stmt_ids = {ref for ref in seed.raw_evidence_refs if "#" in ref}
    if stmt_ids:
        return [s for s in statements if s.statement_id in stmt_ids]
    pool = [s for s in statements if s.evidence_id in seed.ref_blocks]
    if not pool:
        return []
    if seed.method == "identifier_exact_match":
        ids = _PZXQ_ID.findall(seed.claim_text)
        if ids:
            return [s for s in pool
                    if any(identifier in s.text for identifier in ids)]
    strict = [s for s in pool if claim_matches_statement(
        seed.claim_text, s, "generic")]
    if strict:
        return strict
    if seed.method in ("e1_template_match", "l0_entity_detector:TERM-05"):
        e1_rows = [s for s in pool if "异常流" in s.field_name]
        if e1_rows:
            return e1_rows
    return [s for s in pool
            if bigram_containment(seed.claim_text, s.text) >= 0.35]


def classify_claim(claim_text: str) -> str:
    """按可翻转结构对claim分类(优先级: 标识符>数值>枚举>E1>步骤>通用)."""
    if _PZXQ_ID.search(claim_text):
        return "identifier"
    for match in _NUMERIC_CLAIM.finditer(claim_text):
        if match.group("unit"):
            return "numeric"
    if _ENUM_MARKER.search(claim_text) and _split_enum(claim_text):
        return "enum"
    if _CLAIM_PROMPT.search(claim_text):
        return "e1_prompt"
    if len(_STEP_ENTRY.findall(claim_text)) >= 2:
        return "step"
    return "generic"


# ── R样本: 确定性翻转算子 ──────────────────────────────────


@dataclass(frozen=True)
class FlipPlan:
    """一次翻转的构造结果(算子语义保证与原证据矛盾)."""

    operator: str
    claim_kind: str
    flipped: str
    new_token: str
    old_token: str
    rationale: str = ""


@dataclass(frozen=True)
class EgtSample:
    """一条EGT三态训练样本."""

    sample_id: str
    question: str
    claim_text: str
    evidence: tuple[RetrievedEvidence, ...]
    label: EgtLabel
    source: str
    operator: str
    claim_kind: str
    check_items: tuple[str, ...]
    seed_id: str
    context_freeze_id: str
    self_check: tuple[tuple[str, bool], ...] = ()
    overlap_before: float = 0.0
    overlap_after: float = 0.0
    module_verdict: str | None = None
    rationale: str = ""


@dataclass(frozen=True)
class SynthesisResult:
    samples: list[EgtSample]
    stats: dict[str, Any]


def _id_family(identifier: str) -> str:
    segments = identifier.split("-")
    if len(segments) < 2:
        return identifier
    return "-".join(segments[:-1])


def _mutate_identifier(identifier: str,
                       avoid_texts: Sequence[str]) -> str | None:
    tail = identifier.rsplit("-", 1)[-1]
    if len(tail) < 2:
        candidates = [identifier + "-QZ", identifier + "-X9"]
    else:
        candidates = [identifier[:-2] + "QZ", identifier[:-1] + "X",
                      identifier + "X"]
    for candidate in candidates:
        if candidate != identifier and all(
                candidate not in text for text in avoid_texts):
            return candidate
    return None


def _flip_identifier(seed: SupportSeed, matched_text: str,
                     evidence_texts: Sequence[str]) -> FlipPlan | None:
    ids = _PZXQ_ID.findall(seed.claim_text)
    if not ids:
        return None
    orig = ids[0]
    ev_ids = sorted({i for text in evidence_texts for i in _PZXQ_ID.findall(text)})
    siblings = [i for i in ev_ids
                if _id_family(i) == _id_family(orig)
                and i != orig and i not in seed.claim_text]
    anchor = ""
    for statement in linearize_context(seed.evidence):
        match = _ID_ANCHOR.match(statement.text.strip())
        if match and match.group("ident") == orig:
            anchor = match.group("subject").strip()
            break
    bare = _norm(seed.claim_text) == _norm(orig)
    if anchor and siblings and siblings[0] not in matched_text:
        return FlipPlan(
            "id_sibling_swap", "identifier",
            f"{anchor}的项目唯一标识符：{siblings[0]}",
            siblings[0], orig,
            f"证据锚定{anchor}的标识符为{orig}, 换成同族兄弟{siblings[0]}")
    if not bare and not anchor:
        for sibling in siblings:
            if sibling not in matched_text:
                return FlipPlan(
                    "id_sibling_swap", "identifier",
                    seed.claim_text.replace(orig, sibling, 1),
                    sibling, orig,
                    f"claim内联ID {orig}换成同族兄弟{sibling}, 主体语境错配")
    mutated = _mutate_identifier(orig, evidence_texts)
    if mutated is None:
        return None
    if anchor:
        flipped = f"{anchor}的项目唯一标识符：{mutated}"
    elif bare:
        flipped = mutated
    else:
        flipped = seed.claim_text.replace(orig, mutated, 1)
    return FlipPlan("id_tail_mutation", "identifier", flipped, mutated, orig,
                    f"证据锚定标识符{orig}, claim改写为不存在的{mutated}")


def _op_family(op: str | None) -> str:
    if op in _LE_OPS:
        return "le"
    if op in _GE_OPS:
        return "ge"
    if op in _GT_OPS:
        return "gt"
    if op in _LT_OPS:
        return "lt"
    return "eq"


def _format_double(value: str) -> str:
    if "." in value:
        return f"{float(value) * 2:g}"
    return str(int(value) * 2)


def _flipped_phrase_stated(phrase: str, antonym: str,
                           evidence_texts: Sequence[str]) -> bool:
    """证据是否在非否定语境下显式陈述了翻转后的约束短语.

    『超过65535字节』是『不超过65535字节』的子串, 必须检查出现位置的
    左邻字符不是否定词『不』, 否则会把已陈述的否定约束误判为翻转目标
    已被陈述而错误跳过.
    """
    for text in evidence_texts:
        compact = _norm(text)
        start = compact.find(phrase)
        while start >= 0:
            negated = start > 0 and compact[start - 1] == "不"
            if not negated:
                return True
            start = compact.find(phrase, start + 1)
    return False


def _flip_numeric(seed: SupportSeed, matched_text: str,
                  evidence_texts: Sequence[str]) -> FlipPlan | None:
    for match in _NUMERIC_CLAIM.finditer(seed.claim_text):
        if not match.group("unit"):
            continue
        op, value, unit = (match.group("op"), match.group("value"),
                           match.group("unit"))
        family = _op_family(op)
        if family in ("le", "ge", "gt", "lt") and op:
            antonym = _OP_ANTONYM[family]
            phrase = f"{antonym}{value}{unit}"
            if not _flipped_phrase_stated(phrase, antonym, evidence_texts):
                start, end = match.span("op")
                return FlipPlan(
                    "numeric_operator_flip", "numeric",
                    seed.claim_text[:start] + antonym + seed.claim_text[end:],
                    phrase, f"{op}{value}{unit}",
                    f"证据约束『{op}{value}{unit}』, claim翻转为互斥区间"
                    f"『{phrase}』")
            continue
        if unit in _UNIT_SWAP:
            new_unit = _UNIT_SWAP[unit]
            phrase = f"{value}{new_unit}"
            if not any(phrase in _norm(t) for t in evidence_texts):
                start, end = match.span("unit")
                return FlipPlan(
                    "numeric_unit_swap", "numeric",
                    seed.claim_text[:start] + new_unit + seed.claim_text[end:],
                    phrase, f"{value}{unit}",
                    f"证据数值『{value}{unit}』, claim换单位为『{phrase}』, "
                    f"归一化后数值不同即值冲突")
        for new_value in (_format_double(value),
                          str(int(float(value)) + 1) if "." not in value
                          else f"{float(value) + 1:g}"):
            phrase = f"{new_value}{unit}"
            if new_value != value and not any(phrase in _norm(t)
                                              for t in evidence_texts):
                start, end = match.span("value")
                return FlipPlan(
                    "numeric_value_perturb", "numeric",
                    seed.claim_text[:start] + new_value + seed.claim_text[end:],
                    phrase, f"{value}{unit}",
                    f"证据数值『{value}{unit}』, claim改值为『{phrase}』")
    return None


def _split_enum(claim_text: str) -> list[str] | None:
    match = _ENUM_MARKER.search(claim_text)
    if match is None:
        return None
    items = [item.strip() for item in re.split(r"[、，,]", match.group("items"))]
    items = [item for item in items if 2 <= len(item) <= 40]
    if len(items) < 2:
        return None
    return items


def _flip_enum(seed: SupportSeed,
               evidence_texts: Sequence[str]) -> FlipPlan | None:
    items = _split_enum(seed.claim_text)
    if items is None:
        return None
    joined = "、".join(items)
    if not any(joined in _norm_list(t) for t in evidence_texts):
        return None
    match = _ENUM_MARKER.search(seed.claim_text)
    assert match is not None
    removed = items[-1]
    kept = "、".join(items[:-1])
    flipped = (seed.claim_text[:match.start("items")] + kept
               + seed.claim_text[match.end("items"):])
    if _norm(flipped) == _norm(seed.claim_text):
        return None
    return FlipPlan("enum_member_delete", "enum", flipped, "", removed,
                    f"证据穷举清单『{joined}』, claim删元误报为『{kept}』")


def _e1_anchor(scope: str) -> str:
    """e1类翻转的用例锚前缀: 在「{scope}」用例中，.

    scope取用例名主体(_anchor_scope去编号后缀); 引号形式命中
    answer_structure._SCOPE_HINT的quoted分支, 提取干净的scope_hint
    (无引号时前导「在」会被name分支吸收, 对'名称/ID'式长scope正/反
    包含均失配→模块scope解析失败→e1复判退化为unscoped NIE).
    """
    return f"在「{_anchor_scope(scope)}」用例中，"


def _flip_scope(matched: Sequence[EvidenceStatement]) -> str | None:
    """种子支持语句的唯一scope(用例名); 多scope/无scope返回None.

    R样本跨用例歧义修复的scope锚定门控: 无唯一scope的种子(其claim可被
    证据内多个用例解释)不做e1类翻转——换入的提示在证据其他用例中真实
    存在时, refute标签不sound.
    """
    scopes = {s.scope_key for s in matched if s.scope_key}
    if len(scopes) != 1:
        return None
    return next(iter(scopes))


def _e1_prompt_pool(evidence: Sequence[RetrievedEvidence]) -> list[str]:
    prompts: set[str] = set()
    for ev in evidence:
        for match in _E1_ROW.finditer(ev.text):
            prompt = match.group("prompt").strip().strip("。；;")
            if 2 <= len(prompt) <= 40 and not _GENERIC_PROMPT.match(prompt):
                prompts.add(prompt)
    return sorted(prompts)


def _flip_e1_prompt(seed: SupportSeed, matched_text: str,
                    matched: Sequence[EvidenceStatement]) -> FlipPlan | None:
    match = _CLAIM_PROMPT.search(seed.claim_text)
    if match is None:
        return None
    old_prompt = match.group("prompt").strip().strip("“”\"「」")
    if len(old_prompt) < 2:
        return None
    scope = _flip_scope(matched)
    if scope is None:
        return None
    pool = [p for p in _e1_prompt_pool(seed.evidence)
            if p != old_prompt and p not in seed.claim_text
            and p not in matched_text
            and compare_prompts(p, old_prompt).match_type == "no"]
    if not pool:
        return None
    new_prompt = pool[0]
    start, end = match.span("prompt")
    body = seed.claim_text[:start] + new_prompt + seed.claim_text[end:]
    flipped = _e1_anchor(scope) + body
    if _norm(flipped) == _norm(seed.claim_text):
        return None
    return FlipPlan("e1_prompt_swap", "e1_prompt", flipped, new_prompt,
                    old_prompt,
                    f"证据锚定{scope}用例的E1模板提示『{old_prompt}』, claim"
                    f"注入用例锚后换成他用例模板提示『{new_prompt}』, "
                    f"scope内模板错配无歧义")


def _flip_e1_ending(seed: SupportSeed,
                    matched: Sequence[EvidenceStatement]) -> FlipPlan | None:
    """处置动词翻转: claim的「用例结束/终止」处置改为相反处置.

    scope模板的处置(结束)是证据显式陈述, 翻转后的处置声称与之矛盾,
    与e1_prompt_swap同用scope锚定门控+锚注入, 矛盾无跨用例歧义.
    """
    scope = _flip_scope(matched)
    if scope is None:
        return None
    verb_match = _ENDING_VERB.search(seed.claim_text)
    if verb_match is None:
        return None
    old_verb = verb_match.group("verb")
    new_verb = _ENDING_TO_OPPOSITE.get(old_verb)
    if new_verb is None or new_verb == old_verb:
        return None
    start, end = verb_match.span("verb")
    body = seed.claim_text[:start] + new_verb + seed.claim_text[end:]
    flipped = _e1_anchor(scope) + body
    if _norm(flipped) == _norm(seed.claim_text):
        return None
    return FlipPlan("e1_ending_flip", "e1", flipped, new_verb, old_verb,
                    f"证据{scope}用例E1模板处置为『用例{old_verb}』, claim"
                    f"注入用例锚后声称处置『{new_verb}』, 处置语义矛盾")


def _flip_step(seed: SupportSeed) -> FlipPlan | None:
    matches = list(_STEP_ENTRY.finditer(seed.claim_text))
    if len(matches) < 2:
        return None
    first, second = matches[0], matches[1]
    if _norm(first.group("text")) == _norm(second.group("text")):
        return None
    flipped = (seed.claim_text[:second.start("text")] + first.group("text")
               + seed.claim_text[second.end("text"):])
    flipped = (flipped[:first.start("text")] + second.group("text")
               + flipped[first.end("text"):])
    if _norm(flipped) == _norm(seed.claim_text):
        return None
    return FlipPlan("step_order_swap", "step", flipped,
                    second.group("text"), first.group("text"),
                    "证据主事件流为有序编号步骤, claim交换步骤顺序造成时序倒置")


def _term_pool(evidence: Sequence[RetrievedEvidence]) -> dict[str, set[str]]:
    pools: dict[str, set[str]] = {}
    for ev in evidence:
        for match in _TYPED_TERM.finditer(ev.text):
            if _TERM_VERB_BLOCK.search(match.group(0)):
                continue
            pools.setdefault(match.group(0)[-2:], set()).add(match.group(0))
        for match in _DATATYPE_TERM.finditer(ev.text):
            pools.setdefault("datatype", set()).add(match.group(0))
    return pools


def _flip_term(seed: SupportSeed,
               matched_text: str) -> FlipPlan | None:
    pools = _term_pool(seed.evidence)
    if not pools:
        return None
    seen: set[str] = set()
    for match in _TYPED_TERM.finditer(seed.claim_text):
        term = match.group(0)
        if term in seen or _TERM_VERB_BLOCK.search(term):
            continue
        seen.add(term)
        suffix = term[-2:]
        for alt in sorted(pools.get(suffix, set())):
            if (alt != term and alt not in term and term not in alt
                    and alt not in seed.claim_text and alt not in matched_text):
                return _term_plan(seed, term, alt)
    for match in _DATATYPE_TERM.finditer(seed.claim_text):
        term = match.group(0)
        if term in seen:
            continue
        seen.add(term)
        for alt in sorted(pools.get("datatype", set())):
            if alt != term and alt not in seed.claim_text and alt not in matched_text:
                return _term_plan(seed, term, alt)
    return None


def _term_plan(seed: SupportSeed, term: str, alt: str) -> FlipPlan:
    spans = [m.span() for m in _TYPED_TERM.finditer(seed.claim_text)
             if m.group(0) == term]
    spans += [m.span() for m in _DATATYPE_TERM.finditer(seed.claim_text)
              if m.group(0) == term]
    flipped = seed.claim_text
    for start, end in sorted(set(spans), reverse=True):
        flipped = flipped[:start] + alt + flipped[end:]
    return FlipPlan("term_slot_swap", "generic", flipped, alt, term,
                    f"证据语境下的术语『{term}』, claim换成同类不同术语"
                    f"『{alt}』, 同槽位值冲突")


def plan_claim_flip(seed: SupportSeed, matched_text: str,
                    matched: Sequence[EvidenceStatement] = (),
                    ) -> FlipPlan | None:
    """按算子优先级为种子规划一次确定性翻转; 无可翻转结构返回None.

    e1类翻转(e1_prompt_swap/e1_ending_flip)受scope锚定门控: 无唯一scope
    时返回None并落序到后续算子, 避免产生跨用例歧义的refute.
    """
    evidence_texts = [ev.text for ev in seed.evidence]
    for kind, flip in (
            ("identifier", lambda: _flip_identifier(
                seed, matched_text, evidence_texts)),
            ("numeric", lambda: _flip_numeric(
                seed, matched_text, evidence_texts)),
            ("enum", lambda: _flip_enum(seed, evidence_texts)),
            ("e1_prompt", lambda: _flip_e1_prompt(
                seed, matched_text, matched)),
            ("e1_ending", lambda: _flip_e1_ending(seed, matched)),
            ("step", lambda: _flip_step(seed)),
            ("generic", lambda: _flip_term(seed, matched_text)),
    ):
        plan = flip()
        if plan is not None:
            return plan
    return None


def _module_verdict(module: QAConsistencyModule | None, seed: SupportSeed,
                    claim_text: str, evidence: tuple[RetrievedEvidence, ...],
                    ) -> str | None:
    if module is None or not evidence:
        return None
    request = QAInput(
        instance_id=f"{seed.instance_id}-egt-gate",
        question=seed.question,
        answer=claim_text,
        context_freeze_id=seed.context_freeze_id,
        evidence=tuple(evidence),
    )
    return module.verify(request).verdict


_OVERLAP_GATED_OPERATORS = frozenset({
    "id_sibling_swap", "id_tail_mutation", "numeric_operator_flip",
    "numeric_unit_swap", "numeric_value_perturb", "term_slot_swap",
})

#: 数值/ID翻转的矛盾锚点是证据中显式陈述的约束/标识符(可能不在refs
#: 块内), 重叠率对全证据计算; term交换的换入术语来自同一证据, 只能对
#: 支持语句计算才有效
_FULL_EVIDENCE_OVERLAP_OPS = frozenset({
    "id_sibling_swap", "id_tail_mutation", "numeric_operator_flip",
    "numeric_unit_swap", "numeric_value_perturb",
})

#: 这些算子的矛盾是推断性的(证据无显式排除语句)或依赖scope锚定/穷举
#: 语义, 翻转后若模块仍能从同一证据support该claim, 说明翻转产生了被
#: 蕴含的弱化claim或存在歧义 → 跳过
_MODULE_GATED_OPERATORS = frozenset({
    "term_slot_swap", "e1_prompt_swap", "e1_ending_flip",
    "enum_member_delete",
})


def _flip_token_absent(new_token: str, flipped: str,
                       matched_text: str) -> bool:
    """换入token是否真的不在支持语句中(带左边界字符防子串误判).

    例: le翻转antonym『超过』是『不超过』的子串, 仅查token会误判
    翻转无效; 追加token在flipped claim中的左邻字符后『小超过…』
    便不再匹配『…大小不超过…』.
    """
    if not new_token or new_token not in matched_text:
        return True
    pos = flipped.find(new_token)
    if pos > 0:
        return flipped[pos - 1:pos + len(new_token)] not in matched_text
    return False


def synthesize_refute_samples(
    seeds: Sequence[SupportSeed],
    module: QAConsistencyModule | None = None,
) -> SynthesisResult:
    """对每个种子claim应用确定性翻转算子生成sound refute样本."""
    samples: list[EgtSample] = []
    attempts = Counter()
    kept = Counter()
    module_verdicts = Counter()
    skipped_no_flip = 0
    skipped_self_check = 0
    skipped_module_gate = 0
    for seed in seeds:
        matched = seed_matching_statements(seed)
        matched_text = "；".join(s.text for s in matched)
        plan = plan_claim_flip(seed, matched_text, matched)
        if plan is None:
            skipped_no_flip += 1
            continue
        attempts[plan.operator] += 1
        overlap_reference = (matched_text
                             if plan.operator not in _FULL_EVIDENCE_OVERLAP_OPS
                             else "".join(_norm(ev.text)
                                          for ev in seed.evidence))
        before = char_overlap_ratio(seed.claim_text, overlap_reference)
        after = char_overlap_ratio(plan.flipped, overlap_reference)
        checks: list[tuple[str, bool]] = [
            ("flipped_differs", _norm(plan.flipped) != _norm(seed.claim_text)),
        ]
        if plan.operator == "step_order_swap":
            checks.append(("order_changed", plan.new_token != plan.old_token))
        elif plan.operator == "enum_member_delete":
            checks.append(("removed_member_absent",
                           plan.old_token not in plan.flipped))
        else:
            checks.append(("new_token_absent_from_support",
                           _flip_token_absent(plan.new_token, plan.flipped,
                                              matched_text)))
            if plan.operator in _OVERLAP_GATED_OPERATORS:
                checks.append(("overlap_dropped", after < before))
        if not all(passed for _, passed in checks):
            skipped_self_check += 1
            continue
        verdict = _module_verdict(module, seed, plan.flipped, seed.evidence)
        if plan.operator in _MODULE_GATED_OPERATORS and verdict == "support":
            skipped_module_gate += 1
            continue
        kept[plan.operator] += 1
        if verdict is not None:
            module_verdicts[verdict] += 1
        samples.append(EgtSample(
            sample_id="",
            question=seed.question,
            claim_text=plan.flipped,
            evidence=seed.evidence,
            label="refute",
            source=seed.method,
            operator=plan.operator,
            claim_kind=plan.claim_kind,
            check_items=route_question(seed.question),
            seed_id=seed.seed_id,
            context_freeze_id=seed.context_freeze_id,
            self_check=tuple(checks),
            overlap_before=round(before, 4),
            overlap_after=round(after, 4),
            module_verdict=verdict,
            rationale=plan.rationale,
        ))
    n_kept = sum(kept.values())
    n_attempts = sum(attempts.values())
    n_self_checked = n_kept + skipped_self_check
    n_verdicted = sum(module_verdicts.values())
    stats = {
        "n_seeds": len(seeds),
        "skipped_no_flippable_structure": skipped_no_flip,
        "skipped_self_check": skipped_self_check,
        "skipped_module_gate": skipped_module_gate,
        "attempts_by_operator": dict(attempts),
        "kept_by_operator": dict(kept),
        # 自检通过率: 通过本地自检(翻转有效)的尝试占比; 模块复判门控单列
        "self_check_pass_rate": (
            round(n_kept / n_self_checked, 4) if n_self_checked else None),
        "attempt_yield": round(n_kept / n_attempts, 4) if n_attempts else None,
        "module_verdicts_of_kept": dict(module_verdicts),
        "module_refute_rate_of_kept": (
            round(module_verdicts.get("refute", 0) / n_verdicted, 4)
            if n_verdicted else None),
    }
    return SynthesisResult(samples, stats)


# ── N样本: 支持删除/证据换源 ────────────────────────────────


def _delete_table_rows(text: str, row_indices: set[int]) -> str:
    if not row_indices:
        return text
    pieces: list[str] = []
    pos = 0
    index = 0
    for match in _ROW.finditer(text):
        cells = [_strip_tags(cell) for cell in _CELL.findall(match.group(1))]
        if not [cell for cell in cells if cell]:
            continue
        index += 1
        if index in row_indices:
            pieces.append(text[pos:match.start()])
            pos = match.end()
    pieces.append(text[pos:])
    return "".join(pieces)


def _delete_sentences(text: str, sent_indices: set[int]) -> str:
    if not sent_indices:
        return text
    pieces: list[str] = []
    index = 0
    for part in re.split(r"(?<=[。；！？\n])", text):
        if len(part.strip()) >= 8:
            index += 1
            if index in sent_indices:
                continue
        pieces.append(part)
    return "".join(pieces)


def _remove_support_span(
    evidence: tuple[RetrievedEvidence, ...],
    matched_ids: set[str],
) -> tuple[RetrievedEvidence, ...] | None:
    """删除支持语句所在表格行/文本句; 空块整块移除; 全空或无变化返回None."""
    modified: list[RetrievedEvidence] = []
    changed = False
    for ev in evidence:
        targets = [s for s in linearize_evidence(ev)
                   if s.statement_id in matched_ids]
        if not targets:
            modified.append(ev)
            continue
        row_indices = {s.row_index for s in targets}
        new_text = (_delete_table_rows(ev.text, row_indices)
                    if "<table" in ev.text
                    else _delete_sentences(ev.text, row_indices))
        if _norm(new_text) == _norm(ev.text):
            modified.append(ev)
            continue
        changed = True
        new_ev = replace(ev, text=new_text)
        if linearize_evidence(new_ev):
            modified.append(new_ev)
    if not changed or not modified:
        return None
    return tuple(modified)


def _claim_verbatim_present(seed: SupportSeed,
                            evidence: tuple[RetrievedEvidence, ...]) -> bool:
    """claim的精确匹配内容是否仍留在证据中(删除无效则返回True)."""
    compact = _norm(seed.claim_text)
    if compact and any(compact in _norm(ev.text) for ev in evidence):
        return True
    if seed.method == "identifier_exact_match":
        ids = _PZXQ_ID.findall(seed.claim_text)
        if ids and any(identifier in ev.text
                       for ev in evidence for identifier in ids):
            return True
    return False


def synthesize_nie_samples(
    seeds: Sequence[SupportSeed],
    module: QAConsistencyModule | None = None,
    peer_evidence: Mapping[str, tuple[RetrievedEvidence, ...]] | None = None,
    max_peers: int = 8,
) -> SynthesisResult:
    """删除支持span/块(或换同文档他源证据)生成sound NIE样本."""
    samples: list[EgtSample] = []
    stats: dict[str, Any] = {
        "span": {"attempted": 0, "kept": 0, "skipped_no_support_statement": 0,
                 "skipped_self_check": 0, "skipped_module_support": 0,
                 "skipped_module_refute": 0},
        "block": {"attempted": 0, "kept": 0, "skipped_all_blocks_support": 0,
                  "skipped_self_check": 0, "skipped_module_support": 0,
                  "skipped_module_refute": 0},
        "cross_instance": {"attempted": 0, "kept": 0, "skipped_no_peer": 0},
    }
    for seed in seeds:
        matched = seed_matching_statements(seed)
        matched_text = "；".join(s.text for s in matched)
        before = char_overlap_ratio(seed.claim_text, matched_text)

        if matched:
            stats["span"]["attempted"] += 1
            span_evidence = _remove_support_span(
                seed.evidence, {s.statement_id for s in matched})
            if span_evidence is None:
                stats["span"]["skipped_self_check"] += 1
            else:
                verdict = _module_verdict(
                    module, seed, seed.claim_text, span_evidence)
                checks: list[tuple[str, bool]] = [
                    ("claim_exact_statement_absent",
                     not _claim_verbatim_present(seed, span_evidence)),
                    ("evidence_nonempty", len(span_evidence) >= 1),
                ]
                if verdict is not None:
                    checks.append(("module_verdict_is_nie",
                                   verdict == "not_in_evidence"))
                if all(passed for _, passed in checks):
                    stats["span"]["kept"] += 1
                    after = char_overlap_ratio(
                        seed.claim_text,
                        "；".join(s.text for s in
                                  linearize_context(span_evidence)))
                    samples.append(EgtSample(
                        sample_id="", question=seed.question,
                        claim_text=seed.claim_text, evidence=span_evidence,
                        label="not_in_evidence", source=seed.method,
                        operator="evidence_span_deletion",
                        claim_kind=classify_claim(seed.claim_text),
                        check_items=route_question(seed.question),
                        seed_id=seed.seed_id,
                        context_freeze_id=seed.context_freeze_id,
                        self_check=tuple(checks),
                        overlap_before=round(before, 4),
                        overlap_after=round(after, 4),
                        module_verdict=verdict,
                        rationale=(
                            "从冻结证据删除支持claim的语句/表格行, 开放scope"
                            "下claim不可判定且未矛盾, 与冻结证据协议同构"),
                    ))
                elif verdict == "support":
                    stats["span"]["skipped_module_support"] += 1
                elif verdict == "refute":
                    stats["span"]["skipped_module_refute"] += 1
                else:
                    stats["span"]["skipped_self_check"] += 1

        ref_blocks = seed.ref_blocks
        remaining = tuple(ev for ev in seed.evidence
                          if ev.evidence_id not in ref_blocks)
        if ref_blocks and remaining and len(remaining) < len(seed.evidence):
            stats["block"]["attempted"] += 1
            verdict = _module_verdict(module, seed, seed.claim_text, remaining)
            checks = [
                ("claim_exact_statement_absent", not _claim_verbatim_present(
                    seed, remaining)),
                ("evidence_nonempty", len(remaining) >= 1),
            ]
            if verdict is not None:
                checks.append(("module_verdict_is_nie",
                               verdict == "not_in_evidence"))
            if all(passed for _, passed in checks):
                stats["block"]["kept"] += 1
                after = char_overlap_ratio(
                    seed.claim_text,
                    "；".join(s.text for s in linearize_context(remaining)))
                samples.append(EgtSample(
                    sample_id="", question=seed.question,
                    claim_text=seed.claim_text, evidence=remaining,
                    label="not_in_evidence", source=seed.method,
                    operator="evidence_block_deletion",
                    claim_kind=classify_claim(seed.claim_text),
                    check_items=route_question(seed.question),
                    seed_id=seed.seed_id,
                    context_freeze_id=seed.context_freeze_id,
                    self_check=tuple(checks),
                    overlap_before=round(before, 4),
                    overlap_after=round(after, 4),
                    module_verdict=verdict,
                    rationale="整个删除支持证据块, 剩余开放scope证据无法判定claim",
                ))
            elif verdict == "support":
                stats["block"]["skipped_module_support"] += 1
            elif verdict == "refute":
                stats["block"]["skipped_module_refute"] += 1
            else:
                stats["block"]["skipped_self_check"] += 1
        else:
            stats["block"]["skipped_all_blocks_support"] += 1

        if peer_evidence:
            stats["cross_instance"]["attempted"] += 1
            peer = _first_nie_peer(seed, peer_evidence, module, max_peers)
            if peer is None:
                stats["cross_instance"]["skipped_no_peer"] += 1
            else:
                peer_id, peer_ev, verdict = peer
                stats["cross_instance"]["kept"] += 1
                after = char_overlap_ratio(
                    seed.claim_text,
                    "；".join(s.text for s in linearize_context(peer_ev)))
                samples.append(EgtSample(
                    sample_id="", question=seed.question,
                    claim_text=seed.claim_text, evidence=peer_ev,
                    label="not_in_evidence",
                    source=f"cross_instance:{seed.method}",
                    operator="cross_instance_evidence_swap",
                    claim_kind=classify_claim(seed.claim_text),
                    check_items=route_question(seed.question),
                    seed_id=seed.seed_id,
                    context_freeze_id=seed.context_freeze_id,
                    self_check=(("peer_evidence_differs", True),
                                ("module_verdict_is_nie",
                                 verdict == "not_in_evidence")),
                    overlap_before=round(before, 4),
                    overlap_after=round(after, 4),
                    module_verdict=verdict,
                    rationale=(
                        f"claim引用的信息在seed证据中, 换成同文档另一条"
                        f"QA({peer_id})的证据集后不可判定"),
                ))
    return SynthesisResult(samples, stats)


def _first_nie_peer(
    seed: SupportSeed,
    peer_evidence: Mapping[str, tuple[RetrievedEvidence, ...]],
    module: QAConsistencyModule | None,
    max_peers: int,
) -> tuple[str, tuple[RetrievedEvidence, ...], str | None] | None:
    claim_norm = _norm(seed.claim_text)
    tried = 0
    for peer_id in sorted(peer_evidence):
        if peer_id == seed.instance_id:
            continue
        peer_ev = peer_evidence[peer_id]
        if peer_ev == seed.evidence:
            continue
        tried += 1
        if tried > max_peers:
            break
        if any(claim_norm and claim_norm in _norm(ev.text) for ev in peer_ev):
            continue
        verdict = _module_verdict(module, seed, seed.claim_text, peer_ev)
        if verdict is not None and verdict != "not_in_evidence":
            continue
        return peer_id, peer_ev, verdict
    return None


# ── S样本: 原样保留 ────────────────────────────────────────


def synthesize_support_samples(
    seeds: Sequence[SupportSeed],
) -> SynthesisResult:
    """种子原样保留为S样本; 同QA多条support claim合并为困难S样本."""
    samples: list[EgtSample] = []
    for seed in seeds:
        samples.append(EgtSample(
            sample_id="", question=seed.question, claim_text=seed.claim_text,
            evidence=seed.evidence, label="support", source=seed.method,
            operator="seed_passthrough",
            claim_kind=classify_claim(seed.claim_text),
            check_items=route_question(seed.question),
            seed_id=seed.seed_id,
            context_freeze_id=seed.context_freeze_id,
            self_check=(("seed_verified_by_module", True),),
            module_verdict="support",
            rationale=f"种子method={seed.method}, 当前验证系统已判support, 原样保留",
        ))
    merged = 0
    by_instance: dict[str, list[SupportSeed]] = {}
    for seed in seeds:
        by_instance.setdefault(seed.instance_id, []).append(seed)
    for instance_id in sorted(by_instance):
        group = sorted(by_instance[instance_id], key=lambda s: s.claim_id)
        if len(group) < 2:
            continue
        merged += 1
        claim_text = "；".join(s.claim_text for s in group)
        samples.append(EgtSample(
            sample_id="", question=group[0].question, claim_text=claim_text,
            evidence=group[0].evidence, label="support",
            source="multi_claim_merge", operator="multi_claim_merge",
            claim_kind="multi",
            check_items=route_question(group[0].question),
            seed_id=f"{instance_id}:merged",
            context_freeze_id=group[0].context_freeze_id,
            self_check=(("each_claim_seed_verified", True),),
            module_verdict="support",
            rationale=(f"同QA的{len(group)}条support种子claim合并, "
                       f"每条均被各自种子证据验证"),
        ))
    stats = {"n_seeds": len(seeds), "seed_passthrough": len(seeds),
             "multi_claim_merged": merged}
    return SynthesisResult(samples, stats)


# ── 语句级合成: S改写 / R翻转 / N删除与换源 ────────────────


def _bigram_jaccard(a: str, b: str) -> float:
    """字符二元组Jaccard相似度(S改写的保义门槛)."""
    grams_a, grams_b = _bigrams(a), _bigrams(b)
    if not grams_a or not grams_b:
        return 0.0
    return len(grams_a & grams_b) / len(grams_a | grams_b)


def _plus_one(value: str) -> str:
    return str(int(value) + 1) if "." not in value else f"{float(value) + 1:g}"


def _reorder_variant(text: str) -> str | None:
    match = _REORDER_CLAIM.match(text)
    if match is None:
        return None
    verb_body = match.group("verb")[1:]
    return f"{match.group('obj')}由{match.group('subj')}{verb_body}。"


def _num_format_variant(text: str) -> str | None:
    for match in _NUM_FORMAT.finditer(text):
        value = int(match.group("value"))
        if value % 10000 == 0:
            variant = f"{value // 10000}万"
        elif value % 1000 == 0:
            variant = f"{value // 1000}千"
        else:
            continue
        return text[:match.start()] + variant + text[match.end():]
    return None


_FILLER_SUBS = (
    (re.compile(r"(?<!不)进行"), ""),
    (re.compile(r"(?<!不)需要"), ""),
    (re.compile(r"了"), ""),
    (re.compile(r"(?<![目标])的"), ""),
)


def _filler_variant(text: str) -> str:
    for pattern, repl in _FILLER_SUBS:
        text = pattern.sub(repl, text)
    return text


def _rewrite_support_statement(text: str) -> tuple[str, str] | None:
    """轻量确定性改写: 语序调整/数字格式/应→须/去填充词.

    依次尝试并取第一个满足保义门槛(字符bigram Jaccard≥0.5)且≠原句的
    变体; 全部失败返回None(该语句不可非平凡改写).
    """
    candidates: list[tuple[str, str]] = []
    reorder = _reorder_variant(text)
    if reorder is not None:
        candidates.append((reorder, "reorder"))
    num_format = _num_format_variant(text)
    if num_format is not None:
        candidates.append((num_format, "num_format"))
    if _DEONTIC_SWAP.search(text):
        candidates.append((_DEONTIC_SWAP.sub("须", text, count=1),
                           "deontic_swap"))
    candidates.append((_filler_variant(text), "filler_removal"))
    for rewritten, transform in candidates:
        if (_norm(rewritten) != _norm(text)
                and _bigram_jaccard(rewritten, text) >= 0.5):
            return rewritten, transform
    return None


def synthesize_support_from_statement(
    seed: StatementSeed,
    blocks: Sequence[Mapping[str, Any]],
) -> EgtSample | None:
    """S样本: 种子语句的轻量确定性改写(证据含原句, claim≠原句)."""
    rewrite = _rewrite_support_statement(seed.statement_text)
    if rewrite is None:
        return None
    rewritten, transform = rewrite
    window = statement_evidence_window(seed, blocks)
    jaccard = _bigram_jaccard(rewritten, seed.statement_text)
    return EgtSample(
        sample_id="", question=STATEMENT_QUESTION, claim_text=rewritten,
        evidence=window, label="support",
        source=f"statement:{seed.block_type}",
        operator=f"support_rewrite:{transform}",
        claim_kind=classify_claim(rewritten),
        check_items=route_question(STATEMENT_QUESTION),
        seed_id=seed.seed_id, context_freeze_id=seed.context_freeze_id,
        self_check=(
            ("rewritten_differs",
             _norm(rewritten) != _norm(seed.statement_text)),
            ("bigram_jaccard_ge_0.5", jaccard >= 0.5),
            ("evidence_nonempty", len(window) >= 1),
        ),
        module_verdict=None,
        rationale=(f"种子语句为证据中真实语句(语句级线性化), 经{transform}"
                   f"确定性改写保义且防premise=hypothesis平凡对"),
    )


#: E1行中的纯处置文本(「用例结束」)不是提示内容, 不入prompt池/不可换
_ENDING_ONLY_TEXT = re.compile(
    r"^(?:用例|流程|步骤)?\s*(?:结束|终止|中止|继续|恢复)\s*[。.；;]?\s*$")


def _anchor_scope(scope: str) -> str:
    """锚文本用的scope: 去用例名中的编号/标识符后缀.

    doc 01等把「名称/ZZSJHQZHFW-...」整串作Use Case名称, 模块scope
    解析按14字符窗口且不含连字符, 会截断失配→unscoped→e1复判退化为
    NIE; 取'/'前的名称主体并去括号编号, 锚定仍指向同一用例.
    """
    head = scope.split("/", 1)[0].strip() or scope
    cleaned = re.sub(r"（[^）]*）|\([^)]*\)", "", head).strip()
    return cleaned or head


def _flip_stmt_numeric(text: str,
                       avoid_texts: Sequence[str]) -> FlipPlan | None:
    """语句级数值翻转: 显式算子→区间互斥反义; 相等断言→值/单位互斥.

    「在N内」式隐式上界(无边值扰动只会弱化约束→蕴含)一律跳过.
    """
    for match in _NUMERIC_CLAIM.finditer(text):
        if not match.group("unit"):
            continue
        op, value, unit = (match.group("op"), match.group("value"),
                           match.group("unit"))
        family = _op_family(op)
        head = text[max(0, match.start() - 1):match.start()]
        tail = text[match.end():match.end() + 1]
        if family in ("le", "ge", "gt", "lt") and op:
            antonym = _OP_ANTONYM[family]
            phrase = f"{antonym}{value}{unit}"
            if not _flipped_phrase_stated(phrase, antonym, avoid_texts):
                start = match.start("op")
                return FlipPlan(
                    "numeric_operator_flip", "numeric",
                    text[:start] + antonym + text[start + len(op):],
                    phrase, f"{op}{value}{unit}",
                    f"证据约束『{op}{value}{unit}』, claim翻转为互斥区间"
                    f"『{phrase}』")
            continue
        if not op and (head == "在" or tail in ("内", "以")):
            continue
        if unit in _UNIT_SWAP:
            new_unit = _UNIT_SWAP[unit]
            phrase = f"{value}{new_unit}"
            if not any(phrase in _norm(t) for t in avoid_texts):
                start = match.start("unit")
                return FlipPlan(
                    "numeric_unit_swap", "numeric",
                    text[:start] + new_unit + text[start + len(unit):],
                    phrase, f"{value}{unit}",
                    f"证据相等断言『{value}{unit}』, claim换单位为『{phrase}』, "
                    f"归一化后数值互斥")
        for new_value in (_format_double(value), _plus_one(value)):
            phrase = f"{new_value}{unit}"
            if new_value != value and not any(phrase in _norm(t)
                                              for t in avoid_texts):
                start = match.start("value")
                return FlipPlan(
                    "numeric_value_perturb", "numeric",
                    text[:start] + new_value + text[start + len(value):],
                    phrase, f"{value}{unit}",
                    f"证据数值『{value}{unit}』, claim改值为『{phrase}』")
    return None


def _flip_stmt_identifier(text: str, doc_ids: Sequence[str],
                          avoid_texts: Sequence[str]) -> FlipPlan | None:
    """语句级ID翻转: 同doc同族兄弟交换(须不在证据窗口中)或尾段变异."""
    match = _GENERIC_ID.search(text)
    if match is None:
        return None
    orig = match.group(0)
    for sibling in doc_ids:
        if (_id_family(sibling) == _id_family(orig) and sibling != orig
                and sibling not in text
                and all(sibling not in t for t in avoid_texts)):
            return FlipPlan(
                "id_sibling_swap", "identifier",
                text[:match.start()] + sibling + text[match.end():],
                sibling, orig,
                f"证据把主体绑定到标识符{orig}, claim换成同族兄弟{sibling}, "
                f"绑定值冲突")
    mutated = _mutate_identifier(orig, avoid_texts)
    if mutated is not None:
        return FlipPlan(
            "id_tail_mutation", "identifier",
            text[:match.start()] + mutated + text[match.end():],
            mutated, orig,
            f"证据把主体绑定到标识符{orig}, claim改写为不存在的{mutated}")
    return None


def _flip_stmt_enum(text: str,
                    window_texts: Sequence[str]) -> FlipPlan | None:
    """语句级枚举翻转: 顿号列表删末元(穷举清单误报)."""
    items = _split_enum(text)
    if items is None:
        return None
    joined = "、".join(items)
    if not any(joined in _norm_list(t) for t in window_texts):
        return None
    match = _ENUM_MARKER.search(text)
    assert match is not None
    removed = items[-1]
    kept_items = "、".join(items[:-1])
    flipped = (text[:match.start("items")] + kept_items
               + text[match.end("items"):])
    if _norm(flipped) == _norm(text):
        return None
    return FlipPlan("enum_member_delete", "enum", flipped, "", removed,
                    f"证据穷举清单『{joined}』, claim删元误报为『{kept_items}』")


def _flip_stmt_e1_prompt(seed: StatementSeed,
                         prompt_pool: Sequence[tuple[str, str]],
                         window_texts: Sequence[str],
                         ) -> FlipPlan | None:
    """语句级E1提示翻转: 注入用例锚, 换入提示须来自他scope且不在证据窗口.

    证据窗口外选取保证claim的提示文本在证据prompt span中不存在, 模块
    复判可给出无歧义refute(跨用例引用宽容不触发).
    """
    if not seed.is_e1_statement() or not seed.scope_key:
        return None
    match = _E1_ROW.search(seed.statement_text)
    if match is None:
        return None
    old_prompt = match.group("prompt").strip()
    if len(old_prompt) < 2 or _ENDING_ONLY_TEXT.match(old_prompt):
        return None
    window_norm = _norm("".join(window_texts))
    for new_prompt, prompt_scope in prompt_pool:
        if (new_prompt == old_prompt or new_prompt in seed.statement_text
                or _norm(new_prompt) in window_norm
                or _norm(prompt_scope) == _norm(seed.scope_key)
                or compare_prompts(new_prompt, old_prompt).match_type != "no"):
            continue
        body = (seed.statement_text[:match.start("prompt")] + new_prompt
                + seed.statement_text[match.end("prompt"):])
        flipped = _e1_anchor(seed.scope_key) + body
        return FlipPlan(
            "e1_prompt_swap", "e1_prompt", flipped, new_prompt, old_prompt,
            f"证据{seed.scope_key}用例E1模板提示『{old_prompt}』, claim注入"
            f"用例锚后换成他scope模板提示『{new_prompt}』, scope内模板错配")
    return None


def _flip_stmt_e1_ending(seed: StatementSeed) -> FlipPlan | None:
    """语句级处置翻转: E1行处置动词(结束/终止↔继续), 注入用例锚."""
    if not seed.is_e1_statement() or not seed.scope_key:
        return None
    match = _ENDING_VERB.search(seed.statement_text)
    if match is None:
        return None
    old_verb = match.group("verb")
    new_verb = _ENDING_TO_OPPOSITE.get(old_verb)
    if new_verb is None:
        return None
    body = (seed.statement_text[:match.start("verb")] + new_verb
            + seed.statement_text[match.end("verb"):])
    flipped = _e1_anchor(seed.scope_key) + body
    if _norm(flipped) == _norm(seed.statement_text):
        return None
    return FlipPlan(
        "e1_ending_flip", "e1", flipped, new_verb, old_verb,
        f"证据{seed.scope_key}用例E1处置为『{old_verb}』, claim注入用例锚"
        f"后声称处置『{new_verb}』, 处置语义矛盾")


def plan_statement_flip(
    seed: StatementSeed,
    prompt_pool: Sequence[tuple[str, str]],
    window_texts: Sequence[str],
    doc_ids: Sequence[str],
) -> FlipPlan | None:
    """按算子优先级为语句种子规划一次确定性翻转; 无可翻转结构返回None."""
    text = seed.statement_text
    plan = _flip_stmt_numeric(text, window_texts)
    if plan is None:
        plan = _flip_stmt_e1_prompt(seed, prompt_pool, window_texts)
    if plan is None:
        plan = _flip_stmt_e1_ending(seed)
    if plan is None:
        plan = _flip_stmt_identifier(text, doc_ids, window_texts)
    if plan is None:
        plan = _flip_stmt_enum(text, window_texts)
    return plan


def _refute_from_statement_detail(
    seed: StatementSeed,
    blocks: Sequence[Mapping[str, Any]],
    prompt_pool: Sequence[tuple[str, str]],
    doc_ids: Sequence[str],
    module: QAConsistencyModule | None = None,
) -> tuple[EgtSample | None, str, str]:
    """R样本合成的详细结果: (样本|None, 尝试算子|空, 失败原因|空)."""
    window = statement_evidence_window(seed, blocks)
    window_texts = [ev.text for ev in window]
    plan = plan_statement_flip(seed, prompt_pool, window_texts, doc_ids)
    if plan is None:
        return None, "", ""
    reference = "".join(_norm(t) for t in window_texts)
    before = char_overlap_ratio(seed.statement_text, reference)
    after = char_overlap_ratio(plan.flipped, reference)
    checks: list[tuple[str, bool]] = [
        ("flipped_differs",
         _norm(plan.flipped) != _norm(seed.statement_text)),
    ]
    if plan.operator == "enum_member_delete":
        checks.append(("removed_member_absent",
                       plan.old_token not in plan.flipped))
    else:
        checks.append(("new_token_absent_from_support",
                       _flip_token_absent(plan.new_token, plan.flipped,
                                          reference)))
        if plan.operator in _OVERLAP_GATED_OPERATORS:
            checks.append(("overlap_dropped", after < before))
    if not all(passed for _, passed in checks):
        return None, plan.operator, "self_check"
    verdict = _statement_module_verdict(
        module, seed.doc_id, plan.flipped, window, seed.context_freeze_id)
    if plan.operator in _MODULE_GATED_OPERATORS and verdict == "support":
        return None, plan.operator, "module_gate"
    sample = EgtSample(
        sample_id="", question=STATEMENT_QUESTION,
        claim_text=plan.flipped, evidence=window, label="refute",
        source=f"statement:{seed.block_type}", operator=plan.operator,
        claim_kind=plan.claim_kind,
        check_items=route_question(STATEMENT_QUESTION),
        seed_id=seed.seed_id, context_freeze_id=seed.context_freeze_id,
        self_check=tuple(checks),
        overlap_before=round(before, 4), overlap_after=round(after, 4),
        module_verdict=verdict, rationale=plan.rationale,
    )
    return sample, plan.operator, ""


def synthesize_refute_from_statement(
    seed: StatementSeed,
    blocks: Sequence[Mapping[str, Any]],
    prompt_pool: Sequence[tuple[str, str]],
    doc_ids: Sequence[str],
    module: QAConsistencyModule | None = None,
) -> EgtSample | None:
    """R样本: 语句种子的确定性翻转(自检+模块复判门控), 失败返回None."""
    sample, _, _ = _refute_from_statement_detail(
        seed, blocks, prompt_pool, doc_ids, module=module)
    return sample


def _claim_in_evidence(claim: str,
                       evidence: tuple[RetrievedEvidence, ...]) -> bool:
    """claim的精确内容(原文或线性化语句级)是否仍在证据中."""
    compact = _norm(claim)
    if compact and any(compact in _norm(ev.text) for ev in evidence):
        return True
    return any(compact and (compact == _norm(stmt.text)
                            or compact in _norm(stmt.text))
               for stmt in linearize_context(evidence))


def _cross_block_evidence(
    seed: StatementSeed,
    blocks: Sequence[Mapping[str, Any]],
    size: int = _EVIDENCE_WINDOW_SIZE,
) -> tuple[RetrievedEvidence, ...]:
    """同doc其他内容块(不含seed块, 且不含claim文本), 确定性向后环形选取."""
    claim = _norm(seed.statement_text)
    picked: list[RetrievedEvidence] = []
    for step in range(1, len(blocks)):
        j = (seed.block_idx + step) % len(blocks)
        if j == seed.block_idx:
            continue
        if str(blocks[j].get("type", "")) not in _CONTENT_BLOCK_TYPES:
            continue
        evidence = mineru_block_to_evidence(seed.doc_id, j, blocks[j])
        if claim and claim in _norm(evidence.text):
            continue
        picked.append(evidence)
        if len(picked) >= size:
            break
    return tuple(picked)


def _inblock_deletion_evidence(
    seed: StatementSeed,
    blocks: Sequence[Mapping[str, Any]],
) -> tuple[RetrievedEvidence, ...] | None:
    """删除seed语句所在句/行/条目后的证据(修改块+窗口邻居)."""
    block = blocks[seed.block_idx]
    base_text = _block_plain_text(block)
    if seed.delete_mode == "sentence":
        new_text = _delete_sentences(base_text, {seed.delete_index})
    elif seed.delete_mode == "row":
        new_text = _delete_table_rows(base_text, {seed.delete_index})
    else:
        items = [str(item) for item in block.get("list_items", [])]
        if seed.delete_index >= len(items):
            return None
        new_text = "；".join(
            items[:seed.delete_index] + items[seed.delete_index + 1:])
    if _norm(new_text) == _norm(base_text):
        return None
    window = statement_evidence_window(seed, blocks)
    seed_ev = next((ev for ev in window
                    if ev.evidence_id == f"{seed.doc_id}#b{seed.block_idx:03d}"),
                   None)
    neighbors = tuple(ev for ev in window
                      if ev.evidence_id != f"{seed.doc_id}#b{seed.block_idx:03d}")
    evidence: list[RetrievedEvidence] = list(neighbors)
    if seed_ev is not None:
        modified = replace(seed_ev, text=new_text)
        if linearize_evidence(modified):
            evidence.insert(0, modified)
    return tuple(evidence) if evidence else None


def synthesize_nie_from_statement(
    seed: StatementSeed,
    blocks: Sequence[Mapping[str, Any]],
    module: QAConsistencyModule | None = None,
) -> list[EgtSample]:
    """N样本: 跨块(开放世界NIE) + 块内删除两种构造."""
    samples: list[EgtSample] = []
    check_items = route_question(STATEMENT_QUESTION)
    cross = _cross_block_evidence(seed, blocks)
    if cross:
        verdict = _statement_module_verdict(
            module, seed.doc_id, seed.statement_text, cross,
            seed.context_freeze_id)
        checks = [
            ("claim_exact_statement_absent",
             not _claim_in_evidence(seed.statement_text, cross)),
            ("evidence_nonempty", len(cross) >= 1),
        ]
        if verdict is not None:
            checks.append(("module_verdict_is_nie",
                           verdict == "not_in_evidence"))
        if all(passed for _, passed in checks):
            samples.append(EgtSample(
                sample_id="", question=STATEMENT_QUESTION,
                claim_text=seed.statement_text, evidence=cross,
                label="not_in_evidence",
                source=f"statement:{seed.block_type}",
                operator="cross_block_evidence",
                claim_kind=classify_claim(seed.statement_text),
                check_items=check_items, seed_id=seed.seed_id,
                context_freeze_id=seed.context_freeze_id,
                self_check=tuple(checks),
                module_verdict=verdict,
                rationale=("claim来自文档一块, 证据换成同文档不含该内容的"
                           "其他块, 开放scope下不可判定且未矛盾"),
            ))
    inblock = _inblock_deletion_evidence(seed, blocks)
    if inblock is not None:
        verdict = _statement_module_verdict(
            module, seed.doc_id, seed.statement_text, inblock,
            seed.context_freeze_id)
        checks = [
            ("claim_exact_statement_absent",
             not _claim_in_evidence(seed.statement_text, inblock)),
            ("evidence_nonempty", len(inblock) >= 1),
        ]
        if verdict is not None:
            checks.append(("module_verdict_is_nie",
                           verdict == "not_in_evidence"))
        if all(passed for _, passed in checks):
            samples.append(EgtSample(
                sample_id="", question=STATEMENT_QUESTION,
                claim_text=seed.statement_text, evidence=inblock,
                label="not_in_evidence",
                source=f"statement:{seed.block_type}",
                operator="inblock_span_deletion",
                claim_kind=classify_claim(seed.statement_text),
                check_items=check_items, seed_id=seed.seed_id,
                context_freeze_id=seed.context_freeze_id,
                self_check=tuple(checks),
                module_verdict=verdict,
                rationale=("从seed块删除支持语句所在句/表格行/列表条目, "
                           "剩余开放scope证据无法判定claim"),
            ))
    return samples


def _doc_prompt_pool(
    seeds: Sequence[StatementSeed],
) -> list[tuple[str, str]]:
    """同doc所有E1行的(prompt, scope)池(供e1_prompt_swap选取)."""
    pool: list[tuple[str, str]] = []
    seen: set[str] = set()
    for seed in seeds:
        if not seed.is_e1_statement():
            continue
        for match in _E1_ROW.finditer(seed.statement_text):
            prompt = match.group("prompt").strip()
            if (2 <= len(prompt) <= 40 and prompt not in seen
                    and not _GENERIC_PROMPT.match(prompt)
                    and not _ENDING_ONLY_TEXT.match(prompt)):
                seen.add(prompt)
                pool.append((prompt, seed.scope_key))
    return pool


def _doc_identifier_index(
    blocks: Sequence[Mapping[str, Any]],
) -> list[str]:
    """同doc全部标识符(排序去重, 供id_sibling_swap选取)."""
    found: set[str] = set()
    for block in blocks:
        if str(block.get("type", "")) in _CONTENT_BLOCK_TYPES:
            found.update(_GENERIC_ID.findall(_block_plain_text(block)))
    return sorted(found)


def _refute_batch_stats(
    n_seeds: int, attempts: Counter, kept: Counter, skipped_no_flip: int,
    skipped_self_check: int, skipped_module_gate: int,
    module_verdicts: Counter,
) -> dict[str, Any]:
    n_kept = sum(kept.values())
    n_attempts = sum(attempts.values())
    n_self_checked = n_kept + skipped_self_check
    n_verdicted = sum(module_verdicts.values())
    return {
        "n_seeds": n_seeds,
        "skipped_no_flippable_structure": skipped_no_flip,
        "skipped_self_check": skipped_self_check,
        "skipped_module_gate": skipped_module_gate,
        "attempts_by_operator": dict(attempts),
        "kept_by_operator": dict(kept),
        "self_check_pass_rate": (
            round(n_kept / n_self_checked, 4) if n_self_checked else None),
        "attempt_yield": round(n_kept / n_attempts, 4) if n_attempts else None,
        "module_verdicts_of_kept": dict(module_verdicts),
        "module_refute_rate_of_kept": (
            round(module_verdicts.get("refute", 0) / n_verdicted, 4)
            if n_verdicted else None),
    }


def synthesize_refute_from_statements(
    seeds: Sequence[StatementSeed],
    blocks: Sequence[Mapping[str, Any]],
    module: QAConsistencyModule | None = None,
) -> SynthesisResult:
    """批量: 语句种子的R样本合成(含doc级ID池与prompt池)."""
    doc_ids = _doc_identifier_index(blocks)
    prompt_pool = _doc_prompt_pool(seeds)
    samples: list[EgtSample] = []
    attempts: Counter = Counter()
    kept: Counter = Counter()
    module_verdicts: Counter = Counter()
    skipped_no_flip = skipped_self_check = skipped_module_gate = 0
    for seed in seeds:
        sample, operator, failure = _refute_from_statement_detail(
            seed, blocks, prompt_pool, doc_ids, module=module)
        if not operator:
            skipped_no_flip += 1
            continue
        attempts[operator] += 1
        if sample is None:
            if failure == "module_gate":
                skipped_module_gate += 1
            else:
                skipped_self_check += 1
            continue
        kept[operator] += 1
        if sample.module_verdict is not None:
            module_verdicts[sample.module_verdict] += 1
        samples.append(sample)
    stats = _refute_batch_stats(len(seeds), attempts, kept, skipped_no_flip,
                                skipped_self_check, skipped_module_gate,
                                module_verdicts)
    return SynthesisResult(samples, stats)


def synthesize_support_from_statements(
    seeds: Sequence[StatementSeed],
    blocks: Sequence[Mapping[str, Any]],
) -> SynthesisResult:
    """批量: 语句种子的S样本合成(轻量改写, 无模块依赖)."""
    samples: list[EgtSample] = []
    transforms: Counter = Counter()
    skipped_no_rewrite = 0
    for seed in seeds:
        sample = synthesize_support_from_statement(seed, blocks)
        if sample is None:
            skipped_no_rewrite += 1
            continue
        transforms[sample.operator.split(":", 1)[-1]] += 1
        samples.append(sample)
    total = len(samples) + skipped_no_rewrite
    stats = {
        "n_seeds": len(seeds),
        "skipped_no_rewrite": skipped_no_rewrite,
        "by_transform": dict(transforms),
        "self_check_pass_rate": (
            round(len(samples) / total, 4) if total else None),
    }
    return SynthesisResult(samples, stats)


def synthesize_nie_from_statements(
    seeds: Sequence[StatementSeed],
    blocks: Sequence[Mapping[str, Any]],
    module: QAConsistencyModule | None = None,
) -> SynthesisResult:
    """批量: 语句种子的N样本合成(跨块+块内删除)."""
    samples: list[EgtSample] = []
    stats: dict[str, Any] = {
        "cross_block": {"attempted": 0, "kept": 0, "skipped_no_other_block": 0,
                        "skipped_self_check": 0,
                        "skipped_module_verdict": 0,
                        "module_verdicts_of_kept": {}},
        "inblock_deletion": {"attempted": 0, "kept": 0,
                             "skipped_unremovable": 0,
                             "skipped_self_check": 0,
                             "skipped_module_verdict": 0,
                             "module_verdicts_of_kept": {}},
    }
    cross_verdicts: Counter = Counter()
    inblock_verdicts: Counter = Counter()
    for seed in seeds:
        cross = _cross_block_evidence(seed, blocks)
        if not cross:
            stats["cross_block"]["skipped_no_other_block"] += 1
        else:
            stats["cross_block"]["attempted"] += 1
            verdict = _statement_module_verdict(
                module, seed.doc_id, seed.statement_text, cross,
                seed.context_freeze_id)
            absent = not _claim_in_evidence(seed.statement_text, cross)
            if absent and (verdict is None
                           or verdict == "not_in_evidence"):
                stats["cross_block"]["kept"] += 1
                if verdict is not None:
                    cross_verdicts[verdict] += 1
                samples.append(EgtSample(
                    sample_id="", question=STATEMENT_QUESTION,
                    claim_text=seed.statement_text, evidence=cross,
                    label="not_in_evidence",
                    source=f"statement:{seed.block_type}",
                    operator="cross_block_evidence",
                    claim_kind=classify_claim(seed.statement_text),
                    check_items=route_question(STATEMENT_QUESTION),
                    seed_id=seed.seed_id,
                    context_freeze_id=seed.context_freeze_id,
                    self_check=(
                        ("claim_exact_statement_absent", absent),
                        ("evidence_nonempty", len(cross) >= 1),
                        ("module_verdict_is_nie",
                         verdict == "not_in_evidence" or verdict is None),
                    ),
                    module_verdict=verdict,
                    rationale=("claim来自文档一块, 证据换成同文档不含该内容"
                               "的其他块, 开放scope下不可判定且未矛盾"),
                ))
            elif verdict is not None:
                stats["cross_block"]["skipped_module_verdict"] += 1
            else:
                stats["cross_block"]["skipped_self_check"] += 1
        inblock = _inblock_deletion_evidence(seed, blocks)
        if inblock is None:
            stats["inblock_deletion"]["skipped_unremovable"] += 1
        else:
            stats["inblock_deletion"]["attempted"] += 1
            verdict = _statement_module_verdict(
                module, seed.doc_id, seed.statement_text, inblock,
                seed.context_freeze_id)
            absent = not _claim_in_evidence(seed.statement_text, inblock)
            if absent and (verdict is None
                           or verdict == "not_in_evidence"):
                stats["inblock_deletion"]["kept"] += 1
                if verdict is not None:
                    inblock_verdicts[verdict] += 1
                samples.append(EgtSample(
                    sample_id="", question=STATEMENT_QUESTION,
                    claim_text=seed.statement_text, evidence=inblock,
                    label="not_in_evidence",
                    source=f"statement:{seed.block_type}",
                    operator="inblock_span_deletion",
                    claim_kind=classify_claim(seed.statement_text),
                    check_items=route_question(STATEMENT_QUESTION),
                    seed_id=seed.seed_id,
                    context_freeze_id=seed.context_freeze_id,
                    self_check=(
                        ("claim_exact_statement_absent", absent),
                        ("evidence_nonempty", len(inblock) >= 1),
                        ("module_verdict_is_nie",
                         verdict == "not_in_evidence" or verdict is None),
                    ),
                    module_verdict=verdict,
                    rationale=("从seed块删除支持语句所在句/表格行/列表条目, "
                               "剩余开放scope证据无法判定claim"),
                ))
            elif verdict is not None:
                stats["inblock_deletion"]["skipped_module_verdict"] += 1
            else:
                stats["inblock_deletion"]["skipped_self_check"] += 1
    stats["cross_block"]["module_verdicts_of_kept"] = dict(cross_verdicts)
    stats["inblock_deletion"]["module_verdicts_of_kept"] = dict(
        inblock_verdicts)
    return SynthesisResult(samples, stats)


# ── 叙事文法合成(v2): 表格行事实三元组 → 真实QA风格叙事claim ──
#
# v1负结果根因: statement级翻转产生近拷贝claim(与premise只差几个字符),
# 模型学到"找diff", 而真实gold-refute是叙事性跨行值断言(如S1QA-056
# "修改数据设备列表缺手持含平版"需读能力表设备枚举列比对). v2从16文档
# 表格行抽取结构化事实, 用真实QA answer风格的叙事模板生成claim:
#   R翻转值来自同表其他行(跨行绑定: 值真实存在于文档但绑定到错误主体),
#   证据含完整同表块 → premise含污染值来源行, 模拟真实"值存在但绑定
#   错误"的难度; N为效果性扩展断言(表格行不含这些断言 → sound NIE).


#: 叙事文法模板族: 每族S/R/N变体(模仿91 QA answer的叙事断言风格)
NARRATIVE_TEMPLATES: dict[str, dict[str, str]] = {
    # 能力表行: (功能名, 设备枚举); 主体=功能名+『功能』后缀(去重)
    "capability_device": {
        "S": "{主体}支持在{设备列表}上使用",
        "R_add": "{主体}支持在{污染设备列表}上使用",
        "R_swap": "{主体}支持在{污染设备列表}上使用",
        "R_drop": "{主体}仅在{缩减设备列表}上使用",
        "N": "{主体}确保用户操作体验的一致性",
    },
    # 能力表行: 运行状态(开发↔运行跨行值域交换)
    "capability_state": {
        "S": "{功能}在{状态}提供完整功能",
        "R": "{功能}在{错误状态}提供完整功能",
        "N": "{功能}的功能实现经过单元测试验证",
    },
    # 用例表: (用例名, E1提示, 处置)
    "usecase_e1": {
        "S": "在{用例}过程中发生异常时，系统提示{提示内容}，用例{处置}",
        "R": "在{用例}过程中发生异常时，系统提示{错误提示}，用例{处置}",
        "R2": "在{用例}过程中发生异常时，系统提示{提示内容}，用例{污染处置}",
        "N": "在{用例}异常处理完成后系统自动重试该操作",
    },
    # 接口表: (接口ID, 接口名, 发送方, 接收方)
    "interface_flow": {
        "S": "{接口名}通过接口{接口ID}由{发送方}发送至{接收方}",
        "R": "{接口名}通过接口{接口ID}由{污染发送方}发送至{接收方}",
        "N": "接口{接口ID}采用加密传输保障数据安全",
    },
    # 数据表: (参数, 算子, 值, 单位)
    "param_value": {
        "S": "{参数}的要求是{算子}{值}{单位}",
        "R": "{参数}的要求是{算子}{污染值}{单位}",
        "N": "{参数}的配置在极端负载下保持稳定",
    },
    # 能力表行: 需求ID↔任务书映射
    "trace_binding": {
        "S": "需求{需求ID}追溯至任务书{任务书ID}",
        "R": "需求{需求ID}追溯至任务书{污染任务书ID}",
        "N": "需求{需求ID}已通过评审确认实现完整",
    },
}

#: 叙事样本的问题(值中立): 模仿真实QA问句, 使premise构造的question锚定
#: 在训练/推理两侧一致(推理侧question点名scope对象参与语句组排序)
NARRATIVE_QUESTIONS: dict[str, str] = {
    "capability_device": "{功能}功能支持在哪些设备上使用",
    "capability_state": "{功能}在哪些阶段提供功能",
    "usecase_e1": "在{用例}过程中发生异常时系统如何处理",
    "interface_flow": "{接口名}的接口流向是什么",
    "param_value": "{参数}的要求是什么",
    "trace_binding": "需求{需求ID}追溯至任务书哪一章节",
}

#: N模板的效果性断言标记(自检: 标记必须不在证据中 → sound NIE)
_EFFECT_MARKERS: dict[str, str] = {
    "capability_device": "确保用户操作体验",
    "capability_state": "单元测试",
    "usecase_e1": "自动重试",
    "interface_flow": "加密传输",
    "param_value": "极端负载",
    "trace_binding": "评审",
}

#: N模板的细节性扩展断言(普通措辞的虚构细节, 模仿真实NIE claim的
#: "主体在场+似合理但未陈述细节"形态——修复叙事R训练导致的"未陈述
#: 细节→矛盾"过度refute捷径). 标记必须不在全文档中 → sound NIE
_DETAIL_TEMPLATES: dict[str, dict[str, str]] = {
    "capability_device": {
        "claim": "{主体}支持在设备之间无缝切换",
        "marker": "无缝切换",
    },
    "capability_state": {
        "claim": "{功能}在版本升级期间保持可用",
        "marker": "版本升级",
    },
    "usecase_e1": {
        "claim": "在{用例}执行过程中，系统对输入参数进行合法性校验",
        "marker": "合法性校验",
    },
    "interface_flow": {
        "claim": "接口{接口ID}支持高并发批量调用",
        "marker": "高并发",
    },
    "param_value": {
        "claim": "{参数}的取值支持在线调整",
        "marker": "在线调整",
    },
    "trace_binding": {
        "claim": "需求{需求ID}已完成部署验证",
        "marker": "部署验证",
    },
}

#: member_add模式的虚构设备/阶段池(文档中不存在 → 枚举外值sound)
_FICTIONAL_DEVICES: tuple[str, ...] = ("手机版", "大屏版", "穿戴版", "车载版", "网页版")
_FICTIONAL_PHASES: tuple[str, ...] = ("维护阶段", "验收阶段", "联试阶段", "退役阶段")

#: 叙事样本证据窗口: seed表格块+邻近内容块(含同表完整块 → 污染来源行入premise)
_NARRATIVE_WINDOW_SIZE = 4

_E1_PROMPT_EXTRACT = re.compile(r"提示(?P<prompt>[^，,。；;\n]{2,24})")
_USECASE_ENDING = re.compile(r"用例\s*(?P<verb>结束|终止|中止|继续)")
_NUMERIC_VALUE = re.compile(r"^\d+(?:\.\d+)?$")

#: 各族claim锚定的主体字段(claim与premise绑定的锚)
_NARRATIVE_SUBJECT_KEY: dict[str, str] = {
    "capability_device": "功能",
    "capability_state": "功能",
    "usecase_e1": "用例",
    "interface_flow": "接口ID",
    "param_value": "参数",
    "trace_binding": "需求ID",
}


def _vnorm(text: str) -> str:
    """值级归一化: 去空白与顿号/逗号(『运行阶段  开发阶段』与
    『运行阶段、开发阶段』是同一表格值)."""
    return re.sub(r"[、，,\s]+", "", text)


def _split_members(text: str) -> list[str]:
    """枚举值切分: 顿号/逗号/斜杠/空白均是成员分隔."""
    return [part for part in re.split(r"[、，,/\s]+", text) if part]


def _stable_pick(key: str, options: Sequence[str]) -> str | None:
    """确定性选取: md5(key)对options取模(禁用进程随机hash)."""
    if not options:
        return None
    if len(options) == 1:
        return options[0]
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return options[int(digest, 16) % len(options)]


def _stable_index(key: str, size: int) -> int:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % size


def _numeric_differ(a: str, b: str) -> bool:
    try:
        return float(a) != float(b)
    except ValueError:
        return _vnorm(a) != _vnorm(b)


def _device_subject(name: str) -> str:
    """功能名主体: 补『功能』后缀; 名字已以功能结尾时不重复."""
    return name if name.endswith("功能") else name + "功能"


@dataclass(frozen=True)
class NarrativeFact:
    """一条表格行结构化事实(叙事文法的输入)."""

    doc_id: str
    block_idx: int
    family: str
    row_key: str
    fields: tuple[tuple[str, str], ...]
    #: 同表其他行该列值(跨行污染域, 排序去重)
    siblings: tuple[str, ...] = ()

    @property
    def seed_id(self) -> str:
        return f"{self.doc_id}:narr:{self.family}:{self.row_key}"

    @property
    def context_freeze_id(self) -> str:
        return f"narrative-{self.doc_id}-v1"

    def field(self, key: str) -> str:
        return dict(self.fields).get(key, "")


@dataclass(frozen=True)
class NarrativeDocPools:
    """doc级跨行值域(污染值来源)与全文归一化文本(虚构值排除用)."""

    #: (E1提示, 用例scope)池——usecase_e1的跨用例prompt翻转来源
    prompts: tuple[tuple[str, str], ...]
    doc_text: str
    #: 本doc能力表的需求描述语句(供他doc做跨doc细节性N的内容源)
    descriptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class NarrativePlan:
    """一条叙事claim的构造结果(S/R/N三变体共用)."""

    label: EgtLabel
    operator: str
    claim_text: str
    rationale: str
    new_token: str = ""
    old_token: str = ""


@dataclass(frozen=True)
class NarrativeBundle:
    """一个事实的S/R/N叙事计划(claim互不相同)."""

    fact: NarrativeFact
    support: NarrativePlan | None
    refutes: tuple[NarrativePlan, ...]
    nies: tuple[NarrativePlan, ...]


def _capability_facts(rows: Sequence[Sequence[str]],
                      headers: Sequence[str], doc_id: str,
                      block_idx: int,
                      descriptions: list[str] | None = None,
                      ) -> list[NarrativeFact]:
    lower = [h.lower() for h in headers]
    name_idx = next((i for i, h in enumerate(lower)
                     if "usecase名称" in h or h == "名称"), None)
    ident_idx = next((i for i, h in enumerate(headers) if "标识符" in h), None)
    device_idx = next((i for i, h in enumerate(headers) if "方式名称" in h), None)
    state_idx = next((i for i, h in enumerate(headers)
                      if "运行状态" in h or "运行方式" in h), None)
    task_idx = next((i for i, h in enumerate(headers) if "任务书" in h), None)
    desc_idx = next((i for i, h in enumerate(headers) if "需求描述" in h),
                    None)
    if name_idx is None or device_idx is None:
        return []

    def cell(cells: Sequence[str], index: int | None) -> str:
        if index is None or index >= len(cells):
            return ""
        return cells[index].strip()

    entries: list[tuple[str, str, str, str, str]] = []
    for row_no, cells in enumerate(rows[1:], start=1):
        if len(cells) < len(headers) - 2:
            continue
        name = cell(cells, name_idx)
        if not name:
            continue
        if descriptions is not None and desc_idx is not None:
            description = cell(cells, desc_idx).rstrip("。；;、 ")
            if 8 <= len(description) <= 90:
                descriptions.append(description)
        entries.append((
            name,
            cell(cells, ident_idx),
            "、".join(_split_members(cell(cells, device_idx))),
            "、".join(_split_members(cell(cells, state_idx))),
            cell(cells, task_idx),
        ))
    all_devices = [e[2] for e in entries if e[2]]
    all_states = [e[3] for e in entries if e[3]]
    all_tasks = [e[4] for e in entries if e[4]]
    out: list[NarrativeFact] = []
    for row_no, (name, ident, devices, state, task) in enumerate(
            entries, start=1):
        if devices:
            out.append(NarrativeFact(
                doc_id, block_idx, "capability_device", f"cap{row_no}",
                (("功能", name), ("设备列表", devices)),
                tuple(sorted({d for d in all_devices if d != devices}))))
        if state:
            out.append(NarrativeFact(
                doc_id, block_idx, "capability_state", f"cap{row_no}",
                (("功能", name), ("状态", state)),
                tuple(sorted({s for s in all_states if s != state}))))
        if ident and task:
            out.append(NarrativeFact(
                doc_id, block_idx, "trace_binding", f"cap{row_no}",
                (("需求ID", ident), ("任务书ID", task)),
                tuple(sorted({t for t in all_tasks if t != task}))))
    return out


def _interface_facts(rows: Sequence[Sequence[str]],
                     headers: Sequence[str], doc_id: str,
                     block_idx: int) -> list[NarrativeFact]:
    id_idx = next((i for i, h in enumerate(headers) if "接口需求标识" in h),
                  None)
    name_idx = next((i for i, h in enumerate(headers)
                     if ("接口需求名称" in h or "接口名称" in h)
                     and "标识" not in h), None)
    combined_idx = (next((i for i, h in enumerate(headers)
                          if "接口名称" in h and "标识" in h), None)
                    if id_idx is None else None)
    sender_idx = next((i for i, h in enumerate(headers) if "发送方" in h),
                      None)
    receiver_idx = next((i for i, h in enumerate(headers) if "接收方" in h),
                        None)
    if (id_idx is None and combined_idx is None) or sender_idx is None \
            or receiver_idx is None:
        return []

    def cell(cells: Sequence[str], index: int | None) -> str:
        if index is None or index >= len(cells):
            return ""
        return cells[index].strip()

    entries: list[tuple[str, str, str, str]] = []
    for cells in rows[1:]:
        if len(cells) < len(headers) - 2:
            continue
        ident = cell(cells, id_idx)
        name = cell(cells, name_idx)
        if not ident and not name and combined_idx is not None:
            raw = cell(cells, combined_idx)
            match = _GENERIC_ID.search(raw)
            if match:
                ident = match.group(0)
                name = raw[:match.start()].strip(" /—-")
        sender = cell(cells, sender_idx)
        receiver = cell(cells, receiver_idx)
        if name and ident and sender and receiver:
            entries.append((name, ident, sender, receiver))
    all_senders = [e[2] for e in entries]
    out: list[NarrativeFact] = []
    for row_no, (name, ident, sender, receiver) in enumerate(
            entries, start=1):
        out.append(NarrativeFact(
            doc_id, block_idx, "interface_flow", f"if{row_no}",
            (("接口名", name), ("接口ID", ident),
             ("发送方", sender), ("接收方", receiver)),
            tuple(sorted({s for s in all_senders if s != sender}))))
    return out


def _data_facts(rows: Sequence[Sequence[str]], headers: Sequence[str],
                doc_id: str, block_idx: int) -> list[NarrativeFact]:
    name_idx = next((i for i, h in enumerate(headers)
                     if "数据项" in h or "参数" in h), None)
    max_idx = next((i for i, h in enumerate(headers)
                    if "最大值" in h or h == "最大"), None)
    min_idx = next((i for i, h in enumerate(headers)
                    if "最小值" in h or h == "最小"), None)
    unit_idx = next((i for i, h in enumerate(headers) if "单位" in h), None)
    if name_idx is None or (max_idx is None and min_idx is None):
        return []

    def cell(cells: Sequence[str], index: int | None) -> str:
        if index is None or index >= len(cells):
            return ""
        return cells[index].strip()

    entries: list[tuple[str, str, str, str]] = []
    for cells in rows[1:]:
        if len(cells) < len(headers) - 2:
            continue
        name = cell(cells, name_idx)
        if not name:
            continue
        op = value = ""
        for idx, operator in ((max_idx, "不超过"), (min_idx, "不小于")):
            raw = cell(cells, idx)
            if _NUMERIC_VALUE.match(raw):
                op, value = operator, raw
                break
        if not value:
            continue
        unit = cell(cells, unit_idx)
        if unit in ("-", "—", "无"):
            unit = ""
        entries.append((name, op, value, unit))
    all_values = [e[2] for e in entries]
    out: list[NarrativeFact] = []
    for row_no, (name, op, value, unit) in enumerate(entries, start=1):
        out.append(NarrativeFact(
            doc_id, block_idx, "param_value", f"dv{row_no}",
            (("参数", name), ("算子", op), ("值", value), ("单位", unit)),
            tuple(sorted({v for v in all_values if _numeric_differ(v, value)},
                         key=lambda x: (len(x), x)))))
    return out


def _usecase_e1_facts(block: Mapping[str, Any], doc_id: str, block_idx: int,
                      prompt_pool: list[tuple[str, str]],
                      ) -> list[NarrativeFact]:
    evidence = mineru_block_to_evidence(doc_id, block_idx, block)
    out: list[NarrativeFact] = []
    for stmt in linearize_evidence(evidence):
        if not stmt.field_name.startswith("异常流") or not stmt.scope_key:
            continue
        scope = _anchor_scope(stmt.scope_key)
        if not scope:
            continue
        prompt = ""
        match = _E1_PROMPT_EXTRACT.search(stmt.text)
        if match:
            candidate = match.group("prompt").strip("，。 ；;：:")
            if 2 <= len(candidate) <= 24 and not _GENERIC_PROMPT.match(candidate):
                prompt = candidate
        verb_match = _USECASE_ENDING.search(stmt.text)
        verb = verb_match.group("verb") if verb_match else ""
        out.append(NarrativeFact(
            doc_id, block_idx, "usecase_e1", f"e1r{stmt.row_index}",
            (("用例", scope), ("提示内容", prompt), ("处置", verb))))
        if prompt:
            prompt_pool.append((prompt, scope))
    return out


def extract_narrative_corpus(
        blocks: Sequence[Mapping[str, Any]],
        doc_id: str,
) -> tuple[list[NarrativeFact], NarrativeDocPools]:
    """MinerU content_list表格块 → 叙事事实列表 + doc级prompt/描述池.

    表头签名定位: 能力表含『方式名称+运行状态/运行方式』, 接口表含
    『发送方+接收方+接口』, 数据表含『单位+最大值/最小值』; 其余表
    线性化后取异常流行(用例表E1行).
    """
    facts: list[NarrativeFact] = []
    prompts: list[tuple[str, str]] = []
    descriptions: list[str] = []
    doc_text = "".join(_block_plain_text(block) for block in blocks
                       if str(block.get("type", "")) in _CONTENT_BLOCK_TYPES)
    for idx, block in enumerate(blocks):
        if str(block.get("type", "")) != "table":
            continue
        rows = table_rows_positional(str(block.get("table_body", "")))
        if not rows:
            continue
        headers = [re.sub(r"[\s/]", "", cell) for cell in rows[0]]
        joined = "".join(headers)
        if "方式名称" in joined and ("运行状态" in joined
                                    or "运行方式" in joined):
            facts.extend(_capability_facts(rows, headers, doc_id, idx,
                                           descriptions))
        elif "发送方" in joined and "接收方" in joined and "接口" in joined:
            facts.extend(_interface_facts(rows, headers, doc_id, idx))
        elif "单位" in joined and ("最大值" in joined or "最小值" in joined):
            facts.extend(_data_facts(rows, headers, doc_id, idx))
        else:
            facts.extend(_usecase_e1_facts(block, doc_id, idx, prompts))
    return facts, NarrativeDocPools(
        tuple(sorted(set(prompts))), _vnorm(doc_text),
        tuple(sorted(set(descriptions))))


def narrative_evidence_window(
        doc_id: str, block_idx: int,
        blocks: Sequence[Mapping[str, Any]],
        size: int = _NARRATIVE_WINDOW_SIZE,
) -> tuple[RetrievedEvidence, ...]:
    """seed表格块(完整同表 → 污染值来源行入premise)+邻近内容块,
    确定性先向后再向后环形外扩."""
    chosen = [block_idx]
    radius = 1
    while (len(chosen) < size
           and (block_idx - radius >= 0 or block_idx + radius < len(blocks))):
        for offset in (block_idx + radius, block_idx - radius):
            if len(chosen) >= size:
                break
            if (0 <= offset < len(blocks) and offset not in chosen
                    and str(blocks[offset].get("type", ""))
                    in _CONTENT_BLOCK_TYPES):
                chosen.append(offset)
        radius += 1
    return tuple(mineru_block_to_evidence(doc_id, j, blocks[j])
                 for j in sorted(chosen))


def _nie_plans(family: str, fields: Mapping[str, str],
               pools: NarrativeDocPools,
               n_modes: frozenset[str],
               ) -> tuple[NarrativePlan, ...]:
    """N计划: 效果性扩展(标记不在证据) + 细节性扩展(普通措辞虚构细节,
    标记不在全文档——模仿真实NIE claim的'主体在场+似合理但未陈述'
    形态)."""
    plans: list[NarrativePlan] = []
    if "effect" in n_modes:
        plans.append(NarrativePlan(
            "not_in_evidence", "narrative_effect_claim",
            NARRATIVE_TEMPLATES[family]["N"].format(**fields),
            "效果性断言不出现在表格行, 开放scope不可判定"))
    if "detail" in n_modes:
        detail = _DETAIL_TEMPLATES[family]
        if _vnorm(detail["marker"]) not in pools.doc_text:
            plans.append(NarrativePlan(
                "not_in_evidence", "narrative_detail_claim",
                detail["claim"].format(**fields),
                f"细节性断言({detail['marker']})不出现在全文档, "
                f"开放scope不可判定"))
    return tuple(plans)


def _bundle_capability_device(fact: NarrativeFact,
                              pools: NarrativeDocPools,
                              n_modes: frozenset[str],
                              ) -> NarrativeBundle:
    templates = NARRATIVE_TEMPLATES["capability_device"]
    name = fact.field("功能")
    devices = fact.field("设备列表")
    members = _split_members(devices)
    subject = _device_subject(name)
    support = NarrativePlan(
        "support", "narrative_s",
        templates["S"].format(主体=subject, 设备列表=devices),
        f"能力表把{name}的方式名称穷举绑定为{devices}, 叙事改写保义",
        old_token=devices)
    refutes: list[NarrativePlan] = []
    foreign = sorted({member for sibling in fact.siblings
                      for member in _split_members(sibling)} - set(members))
    # 子串守卫: 换入设备与自身成员互不为子串(『平板』⊂『大屏平板』式
    # 替换会被原值重新支持, refute不sound)
    foreign = [member for member in foreign
               if not any(member in own or own in member
                          for own in members)]
    fictional = [device for device in _FICTIONAL_DEVICES
                 if _vnorm(device) not in pools.doc_text]
    added = _stable_pick(f"{fact.seed_id}:add", fictional or foreign)
    if added and added not in members:
        polluted = "、".join(members + [added])
        refutes.append(NarrativePlan(
            "refute", "narrative_device_member_add",
            templates["R_add"].format(主体=subject, 污染设备列表=polluted),
            f"能力表穷举{name}的设备为{devices}, claim加入不存在的{added}"
            f" → 枚举外设备误报", new_token=added, old_token=devices))
    swapped_in = _stable_pick(f"{fact.seed_id}:swap", foreign)
    if swapped_in and members:
        position = _stable_index(f"{fact.seed_id}:pos", len(members))
        swapped = list(members)
        swapped[position] = swapped_in
        polluted = "、".join(swapped)
        if _vnorm(polluted) != _vnorm(devices):
            refutes.append(NarrativePlan(
                "refute", "narrative_device_member_swap",
                templates["R_swap"].format(主体=subject, 污染设备列表=polluted),
                f"能力表绑定{name}的设备为{devices}, claim换入他行设备"
                f"{swapped_in} → 跨行绑定错误",
                new_token=swapped_in, old_token=devices))
    if len(members) >= 2:
        dropped = _stable_pick(f"{fact.seed_id}:drop", members)
        kept = [member for member in members if member != dropped]
        refutes.append(NarrativePlan(
            "refute", "narrative_device_member_drop",
            templates["R_drop"].format(主体=subject, 缩减设备列表="、".join(kept)),
            f"能力表穷举{name}的设备为{devices}, claim『仅』断言缺{dropped}"
            f"员 → 穷举清单缺员误报",
            new_token="、".join(kept), old_token=devices))
    nies = _nie_plans("capability_device", {"主体": subject}, pools, n_modes)
    return NarrativeBundle(fact, support, tuple(refutes), nies)


def _bundle_capability_state(fact: NarrativeFact,
                             pools: NarrativeDocPools,
                             n_modes: frozenset[str],
                             ) -> NarrativeBundle:
    templates = NARRATIVE_TEMPLATES["capability_state"]
    name = fact.field("功能")
    state = fact.field("状态")
    own = _split_members(state)
    support = NarrativePlan(
        "support", "narrative_s",
        templates["S"].format(功能=name, 状态=state),
        f"能力表把{name}的运行状态绑定为{state}", old_token=state)
    refutes: list[NarrativePlan] = []
    foreign = sorted({phase for sibling in fact.siblings
                      for phase in _split_members(sibling)} - set(own))
    # 子串守卫: 换入阶段与自身状态值互不为子串——『运行阶段』⊂
    # 『运行阶段开发阶段』(无分隔多<p>单元格拼接), 子串换入会被原值
    # 重新支持(子集断言), refute不sound
    foreign = [phase for phase in foreign
               if phase not in state and state not in phase
               and not any(phase in member or member in phase
                           for member in own)]
    if not foreign:
        foreign = [phase for phase in _FICTIONAL_PHASES
                   if _vnorm(phase) not in pools.doc_text]
    phase = _stable_pick(f"{fact.seed_id}:phase", foreign)
    if phase and own:
        position = _stable_index(f"{fact.seed_id}:pos", len(own))
        polluted_members = list(own)
        polluted_members[position] = phase
        polluted = "、".join(polluted_members)
        if _vnorm(polluted) != _vnorm(state):
            refutes.append(NarrativePlan(
                "refute", "narrative_state_swap",
                templates["R"].format(功能=name, 错误状态=polluted),
                f"能力表绑定{name}的运行状态为{state}, claim换入{phase}"
                f" → 跨行值域绑定错误", new_token=phase, old_token=state))
    nies = _nie_plans("capability_state", {"功能": name}, pools, n_modes)
    return NarrativeBundle(fact, support, tuple(refutes), nies)


def _e1_claim(scope: str, prompt: str, verb: str) -> str:
    if verb:
        return NARRATIVE_TEMPLATES["usecase_e1"]["S"].format(
            用例=scope, 提示内容=prompt, 处置=verb)
    return f"在{scope}过程中发生异常时，系统提示{prompt}"


def _foreign_prompts(fact: NarrativeFact,
                     pools: NarrativeDocPools) -> list[str]:
    """跨用例提示候选: 与seed用例全部提示compare_prompts==no(防他用例
    提示恰好匹配seed用例的另一异常流)."""
    scope = fact.field("用例")
    own_prompt = fact.field("提示内容")
    seed_prompts = [prompt for prompt, prompt_scope in pools.prompts
                    if _vnorm(prompt_scope) == _vnorm(scope)]
    candidates: set[str] = set()
    for prompt, prompt_scope in pools.prompts:
        if _vnorm(prompt_scope) == _vnorm(scope):
            continue
        if prompt == own_prompt:
            continue
        if any(compare_prompts(prompt, seed).match_type != "no"
               for seed in seed_prompts):
            continue
        candidates.add(prompt)
    return sorted(candidates)


def _bundle_usecase_e1(fact: NarrativeFact,
                       pools: NarrativeDocPools,
                       n_modes: frozenset[str],
                       ) -> NarrativeBundle:
    templates = NARRATIVE_TEMPLATES["usecase_e1"]
    scope = fact.field("用例")
    prompt = fact.field("提示内容")
    verb = fact.field("处置")
    support: NarrativePlan | None = None
    refutes: list[NarrativePlan] = []
    if prompt:
        support = NarrativePlan(
            "support", "narrative_s", _e1_claim(scope, prompt, verb),
            f"用例表{scope}异常流绑定的提示为{prompt}, 叙事改写保义",
            old_token=prompt)
        new_prompt = _stable_pick(f"{fact.seed_id}:prompt",
                                  _foreign_prompts(fact, pools))
        if new_prompt:
            if verb:
                swapped = templates["R"].format(
                    用例=scope, 错误提示=new_prompt, 处置=verb)
            else:
                swapped = f"在{scope}过程中发生异常时，系统提示{new_prompt}"
            refutes.append(NarrativePlan(
                "refute", "narrative_prompt_swap", swapped,
                f"用例表{scope}异常流绑定的提示为{prompt}, claim换成他"
                f"用例提示{new_prompt} → 跨用例模板错配",
                new_token=new_prompt, old_token=prompt))
        new_verb = _ENDING_TO_OPPOSITE.get(verb)
        if verb and new_verb:
            refutes.append(NarrativePlan(
                "refute", "narrative_ending_flip",
                templates["R2"].format(用例=scope, 提示内容=prompt,
                                       污染处置=new_verb),
                f"用例表{scope}异常流处置为用例{verb}, claim声称用例"
                f"{new_verb} → 处置语义矛盾",
                new_token=new_verb, old_token=verb))
    nies = _nie_plans("usecase_e1", {"用例": scope}, pools, n_modes)
    return NarrativeBundle(fact, support, tuple(refutes), nies)


def _bundle_interface_flow(fact: NarrativeFact,
                           pools: NarrativeDocPools,
                           n_modes: frozenset[str],
                           ) -> NarrativeBundle:
    templates = NARRATIVE_TEMPLATES["interface_flow"]
    name = fact.field("接口名")
    ident = fact.field("接口ID")
    sender = fact.field("发送方")
    receiver = fact.field("接收方")
    support = NarrativePlan(
        "support", "narrative_s",
        templates["S"].format(接口名=name, 接口ID=ident,
                              发送方=sender, 接收方=receiver),
        f"接口表把{ident}的流向绑定为{sender}→{receiver}", old_token=sender)
    refutes: list[NarrativePlan] = []
    candidates = [s for s in fact.siblings
                  if _vnorm(s) not in (_vnorm(sender), _vnorm(receiver))]
    swapped_sender = _stable_pick(f"{fact.seed_id}:sender", candidates)
    if swapped_sender:
        refutes.append(NarrativePlan(
            "refute", "narrative_sender_swap",
            templates["R"].format(接口名=name, 接口ID=ident,
                                  污染发送方=swapped_sender, 接收方=receiver),
            f"接口表绑定{ident}的发送方为{sender}, claim换成"
            f"{swapped_sender} → 跨行发送方绑定错误",
            new_token=swapped_sender, old_token=sender))
    nies = _nie_plans("interface_flow", {"接口ID": ident}, pools, n_modes)
    return NarrativeBundle(fact, support, tuple(refutes), nies)


def _bundle_param_value(fact: NarrativeFact,
                        pools: NarrativeDocPools,
                        n_modes: frozenset[str],
                        ) -> NarrativeBundle:
    templates = NARRATIVE_TEMPLATES["param_value"]
    param = fact.field("参数")
    op = fact.field("算子")
    value = fact.field("值")
    unit = fact.field("单位")
    support = NarrativePlan(
        "support", "narrative_s",
        templates["S"].format(参数=param, 算子=op, 值=value, 单位=unit),
        f"数据表把{param}的约束绑定为{op}{value}{unit}", old_token=value)
    refutes: list[NarrativePlan] = []
    polluted = _stable_pick(f"{fact.seed_id}:value", fact.siblings)
    if polluted and _numeric_differ(polluted, value):
        refutes.append(NarrativePlan(
            "refute", "narrative_value_swap",
            templates["R"].format(参数=param, 算子=op,
                                  污染值=polluted, 单位=unit),
            f"数据表绑定{param}的值为{value}{unit}, claim换成他行值"
            f"{polluted} → 跨参数值绑定错误",
            new_token=polluted, old_token=value))
    nies = _nie_plans("param_value", {"参数": param}, pools, n_modes)
    return NarrativeBundle(fact, support, tuple(refutes), nies)


def _bundle_trace_binding(fact: NarrativeFact,
                          pools: NarrativeDocPools,
                          n_modes: frozenset[str],
                          ) -> NarrativeBundle:
    templates = NARRATIVE_TEMPLATES["trace_binding"]
    ident = fact.field("需求ID")
    task = fact.field("任务书ID")
    support = NarrativePlan(
        "support", "narrative_s",
        templates["S"].format(需求ID=ident, 任务书ID=task),
        f"能力表把{ident}追溯绑定为任务书{task}", old_token=task)
    refutes: list[NarrativePlan] = []
    polluted = _stable_pick(
        f"{fact.seed_id}:task",
        [t for t in fact.siblings if _vnorm(t) != _vnorm(task)])
    if polluted:
        refutes.append(NarrativePlan(
            "refute", "narrative_task_swap",
            templates["R"].format(需求ID=ident, 污染任务书ID=polluted),
            f"能力表绑定{ident}追溯至任务书{task}, claim声称追溯至"
            f"任务书{polluted} → 跨行映射绑定错误",
            new_token=polluted, old_token=task))
    nies = _nie_plans("trace_binding", {"需求ID": ident}, pools, n_modes)
    return NarrativeBundle(fact, support, tuple(refutes), nies)


def _narrative_bundle(fact: NarrativeFact, pools: NarrativeDocPools,
                      n_modes: frozenset[str] = frozenset(
                          {"effect", "detail"}),
                      ) -> NarrativeBundle:
    if fact.family == "capability_device":
        return _bundle_capability_device(fact, pools, n_modes)
    if fact.family == "capability_state":
        return _bundle_capability_state(fact, pools, n_modes)
    if fact.family == "usecase_e1":
        return _bundle_usecase_e1(fact, pools, n_modes)
    if fact.family == "interface_flow":
        return _bundle_interface_flow(fact, pools, n_modes)
    if fact.family == "param_value":
        return _bundle_param_value(fact, pools, n_modes)
    return _bundle_trace_binding(fact, pools, n_modes)


#: 支持自检跳过的模板词字段(算子是模板注入词, 不在证据文本中)
_TEMPLATE_ONLY_FIELDS = frozenset({"算子"})


def _narrative_self_checks(fact: NarrativeFact, plan: NarrativePlan,
                           window: Sequence[RetrievedEvidence],
                           support_claim: str,
                           ) -> tuple[tuple[str, bool], ...]:
    # 自检对线性化语句文本(=premise构造的真实输入)而非原始HTML:
    # 多<p>单元格在原始HTML中会被标签打断, 线性化后才是连续值
    statements = linearize_context(tuple(window))
    evidence_norm = _vnorm("；".join(s.text for s in statements))
    claim_norm = _vnorm(plan.claim_text)
    checks: list[tuple[str, bool]] = [("evidence_nonempty", len(window) >= 1)]
    if plan.label == "support":
        values = [value for key, value in fact.fields
                  if value and key not in _TEMPLATE_ONLY_FIELDS]
        checks.append(("fact_values_in_evidence",
                       all(_vnorm(value) in evidence_norm
                           for value in values)))
        checks.append(("claim_not_verbatim", claim_norm not in evidence_norm))
    elif plan.label == "refute":
        checks.append(("true_binding_in_evidence",
                       not plan.old_token
                       or _vnorm(plan.old_token) in evidence_norm))
        checks.append(("polluted_binding_differs",
                       _vnorm(plan.new_token) != _vnorm(plan.old_token)))
        checks.append(("refute_claim_differs_from_support",
                       not support_claim
                       or claim_norm != _vnorm(support_claim)))
    else:
        if plan.operator == "narrative_detail_claim":
            marker = _DETAIL_TEMPLATES[fact.family]["marker"]
        else:
            marker = _EFFECT_MARKERS[fact.family]
        subject = fact.field(_NARRATIVE_SUBJECT_KEY[fact.family])
        checks.append(("effect_marker_absent",
                       _vnorm(marker) not in evidence_norm))
        checks.append(("subject_in_evidence",
                       _vnorm(subject) in evidence_norm))
    return tuple(checks)


def _bundle_plans(bundle: NarrativeBundle) -> list[NarrativePlan]:
    plans: list[NarrativePlan] = []
    if bundle.support is not None:
        plans.append(bundle.support)
    plans.extend(bundle.refutes)
    plans.extend(bundle.nies)
    return plans


#: 跨doc细节性N模板: 主体在场 + 他doc真实需求语言(本doc全文不含) →
#: 多样化的"主体在场+具体但未陈述细节"N(修复自由叙事claim的过度refute)
_FOREIGN_N_TEMPLATES: dict[str, str] = {
    "capability_device": "{主体}{foreign}",
    "usecase_e1": "在{用例}用例中，{foreign}",
    "interface_flow": "通过{接口名}进行交互时，{foreign}",
}


#: 各族claim断言的核心值(N4值缺席N的自检键): claim断言的绑定值
_NARRATIVE_VALUE_KEY: dict[str, str] = {
    "capability_device": "设备列表",
    "capability_state": "状态",
    "usecase_e1": "提示内容",
    "interface_flow": "接口ID",
    "param_value": "值",
    "trace_binding": "任务书ID",
}


def _value_absent_nie_samples(
        fact: NarrativeFact,
        support_claim: str,
        blocks: Sequence[Mapping[str, Any]],
        question: str,
        check_items: tuple[str, ...],
        max_windows: int = 2,
) -> list[EgtSample]:
    """N4值缺席叙事: claim=真实值叙事, 证据=断言值缺席的他块窗口.

    教『值在场→比对(错配=refute), 值缺席→neutral』: 真实检索常漏掉
    字段绑定行(主体经他表在场而字段行缺席)——此时claim不可判定,
    与按他行值比对产生的伪矛盾(过度refute)相反. 与R样本构成
    值在场/缺席的对照训练.
    """
    value = fact.field(_NARRATIVE_VALUE_KEY[fact.family])
    value_norm = _vnorm(value)
    if not support_claim or not value_norm:
        return []
    samples: list[EgtSample] = []
    used_centers: set[int] = set()
    claim_key = _vnorm(support_claim)
    for step in range(1, len(blocks)):
        if len(samples) >= max_windows:
            break
        center = (fact.block_idx + step) % len(blocks)
        if center in used_centers or str(
                blocks[center].get("type", "")) not in _CONTENT_BLOCK_TYPES:
            continue
        window = narrative_evidence_window(fact.doc_id, center, blocks)
        text = _vnorm("；".join(
            s.text for s in linearize_context(tuple(window))))
        if not text or value_norm in text or claim_key in text:
            continue
        used_centers.add(center)
        checks = (
            ("evidence_nonempty", len(window) >= 1),
            ("asserted_value_absent", value_norm not in text),
            ("claim_not_verbatim", claim_key not in text),
        )
        samples.append(EgtSample(
            sample_id="", question=question,
            claim_text=support_claim, evidence=window,
            label="not_in_evidence",
            source=f"narrative:{fact.family}",
            operator="narrative_value_absent",
            claim_kind=fact.family,
            check_items=check_items, seed_id=fact.seed_id,
            context_freeze_id=fact.context_freeze_id,
            self_check=checks,
            overlap_before=0.0,
            overlap_after=round(
                char_overlap_ratio(support_claim, "".join(
                    ev.text for ev in window)), 4),
            module_verdict=None,
            rationale=("claim断言的绑定值({value})不在该证据窗口中"
                       "(字段绑定行未被检索到), 开放scope下值缺席→不可"
                       "判定, 不与他行值比对").format(value=value),
        ))
    return samples


def synthesize_narrative_samples(
        facts: Sequence[NarrativeFact],
        blocks: Sequence[Mapping[str, Any]],
        pools: NarrativeDocPools,
        foreign_sentences: Sequence[str] = (),
        n_modes: frozenset[str] = frozenset({"effect", "detail"}),
        question_mode: str = "generic",
) -> SynthesisResult:
    """批量: 表格行事实 → 叙事S/R/N样本(证据=seed表块+邻近块, 无模块依赖,
    soundness由构造保证+确定性自检).

    N三种模式: 效果性扩展断言(标记词不在证据) + 细节性扩展断言(普通
    措辞虚构细节, 标记词不在全文档) + 跨doc细节性断言(主体在场+他doc
    真实需求语言, 本doc全文不含——内容多样, 模仿真实NIE claim的
    "主体在场+具体但未陈述细节"形态).
    """
    samples: list[EgtSample] = []
    kept: Counter = Counter()
    skipped: Counter = Counter()
    by_family: Counter = Counter()
    for fact in facts:
        bundle = _narrative_bundle(fact, pools, n_modes)
        if question_mode == "real":
            question = NARRATIVE_QUESTIONS[fact.family].format(
                **{key: value for key, value in fact.fields})
        else:
            # 通用问句: 推理侧question锚定不可靠时claim自绑定是鲁棒信号
            question = STATEMENT_QUESTION
        check_items = route_question(question)
        window = narrative_evidence_window(fact.doc_id, fact.block_idx, blocks)
        reference = "".join(ev.text for ev in window)
        support_claim = (bundle.support.claim_text
                         if bundle.support is not None else "")
        seen_claims: set[str] = set()
        for plan in _bundle_plans(bundle):
            claim_key = _vnorm(plan.claim_text)
            if not claim_key or claim_key in seen_claims:
                continue
            checks = _narrative_self_checks(fact, plan, window, support_claim)
            if not all(passed for _, passed in checks):
                skipped[f"{fact.family}:{plan.operator}"] += 1
                continue
            seen_claims.add(claim_key)
            kept[plan.operator] += 1
            by_family[f"{fact.family}:{plan.label[0]}"] += 1
            before = char_overlap_ratio(support_claim or plan.claim_text,
                                        reference)
            after = char_overlap_ratio(plan.claim_text, reference)
            samples.append(EgtSample(
                sample_id="", question=question,
                claim_text=plan.claim_text, evidence=window,
                label=plan.label, source=f"narrative:{fact.family}",
                operator=plan.operator, claim_kind=fact.family,
                check_items=check_items, seed_id=fact.seed_id,
                context_freeze_id=fact.context_freeze_id,
                self_check=checks,
                overlap_before=round(before, 4),
                overlap_after=round(after, 4),
                module_verdict=None, rationale=plan.rationale,
            ))
        # ── 跨doc细节性N: 主体在场 + 他doc需求语言(本doc全文不含) ──
        template = _FOREIGN_N_TEMPLATES.get(fact.family)
        evidence_norm = _vnorm("；".join(
            s.text for s in linearize_context(tuple(window))))
        if template and foreign_sentences and "foreign" in n_modes:
            foreign = _stable_pick(f"{fact.seed_id}:foreign",
                                   list(foreign_sentences))
            subject = fact.field(_NARRATIVE_SUBJECT_KEY[fact.family])
            if (foreign and subject
                    and _vnorm(foreign) not in pools.doc_text
                    and _vnorm(foreign) not in evidence_norm):
                fields = dict(fact.fields)
                fields["主体"] = _device_subject(fields.get("功能", ""))
                claim_text = template.format(foreign=foreign, **fields)
                claim_key = _vnorm(claim_text)
                if claim_key and claim_key not in seen_claims:
                    checks = (
                        ("evidence_nonempty", len(window) >= 1),
                        ("foreign_absent_from_doc",
                         _vnorm(foreign) not in pools.doc_text),
                        ("subject_in_evidence",
                         _vnorm(subject) in evidence_norm),
                        ("claim_not_verbatim",
                         claim_key not in evidence_norm),
                    )
                    if all(passed for _, passed in checks):
                        seen_claims.add(claim_key)
                        kept["narrative_foreign_content"] += 1
                        by_family[f"{fact.family}:n"] += 1
                        samples.append(EgtSample(
                            sample_id="", question=question,
                            claim_text=claim_text, evidence=window,
                            label="not_in_evidence",
                            source=f"narrative:{fact.family}",
                            operator="narrative_foreign_content",
                            claim_kind=fact.family,
                            check_items=check_items,
                            seed_id=fact.seed_id,
                            context_freeze_id=fact.context_freeze_id,
                            self_check=checks,
                            overlap_before=round(
                                char_overlap_ratio(support_claim, reference),
                                4),
                            overlap_after=round(
                                char_overlap_ratio(claim_text, reference), 4),
                            module_verdict=None,
                            rationale=("主体在证据中, 但断言细节(他doc需求"
                                       "语言)不在本doc任何位置——具体但未"
                                       "陈述, 开放scope下为neutral"),
                        ))
        # ── N4值缺席叙事: claim=真实值叙事, 值缺席的他块窗口 ──
        if support_claim and "value_absent" in n_modes:
            value_samples = _value_absent_nie_samples(
                fact, support_claim, blocks, question, check_items)
            kept["narrative_value_absent"] += len(value_samples)
            by_family[f"{fact.family}:n"] += len(value_samples)
            samples.extend(value_samples)
    stats = {
        "n_facts": len(facts),
        "n_samples": len(samples),
        "kept_by_operator": dict(kept),
        "kept_by_family_label": dict(by_family),
        "skipped_by_family_operator": dict(skipped),
        "window_size": _NARRATIVE_WINDOW_SIZE,
    }
    return SynthesisResult(samples, stats)


# ── 组装与序列化 ──────────────────────────────────────────


_LABEL_ORDER = {"support": 0, "refute": 1, "not_in_evidence": 2}


def assemble_dataset(
    samples: Sequence[EgtSample],
    *,
    cap_per_label: int = 1000,
    balance: bool = True,
) -> tuple[list[EgtSample], dict[str, Any]]:
    """确定性排序→每类封顶(等距采样保doc多样性)→均衡下采样→顺序编号."""
    ranked = sorted(samples, key=lambda s: (
        _LABEL_ORDER[s.label], s.seed_id, s.operator, _norm(s.claim_text)))
    by_label: dict[str, list[EgtSample]] = {}
    for sample in ranked:
        by_label.setdefault(sample.label, []).append(sample)
    capped = {label: _stride_sample(group, cap_per_label)
              for label, group in by_label.items()}
    raw_counts = {label: len(group) for label, group in by_label.items()}
    if balance and capped:
        target = min(len(group) for group in capped.values())
        capped = {label: _stride_sample(group, target)
                  for label, group in capped.items()}
    final: list[EgtSample] = []
    for label in sorted(capped, key=lambda x: _LABEL_ORDER[x]):
        for index, sample in enumerate(capped[label], 1):
            final.append(replace(
                sample, sample_id=f"EGT-{label[0].upper()}-{index:05d}"))
    stats = {
        "raw_counts": raw_counts,
        "final_counts": {label: len(group)
                         for label, group in capped.items()},
        "cap_per_label": cap_per_label,
        "balance": balance,
        "total": len(final),
        "version": EGT_VERSION,
    }
    return final, stats


def _stride_sample(group: list[EgtSample],
                   target: int) -> list[EgtSample]:
    if target <= 0 or len(group) <= target:
        return group[:target] if target == 0 else group
    return [group[index * len(group) // target] for index in range(target)]


def sample_to_dict(sample: EgtSample) -> dict[str, Any]:
    return {
        "sample_id": sample.sample_id,
        "question": sample.question,
        "claim_text": sample.claim_text,
        "evidence": [evidence_to_dict(ev) for ev in sample.evidence],
        "label": sample.label,
        "source": sample.source,
        "operator": sample.operator,
        "claim_kind": sample.claim_kind,
        "check_items": list(sample.check_items),
        "seed_id": sample.seed_id,
        "context_freeze_id": sample.context_freeze_id,
        "self_check": dict(sample.self_check),
        "overlap_before": sample.overlap_before,
        "overlap_after": sample.overlap_after,
        "module_verdict": sample.module_verdict,
        "rationale": sample.rationale,
    }


__all__ = [
    "EGT_VERSION",
    "NARRATIVE_TEMPLATES",
    "SUPPORT_SEED_METHODS",
    "STATEMENT_QUESTION",
    "EgtSample",
    "EgtLabel",
    "FlipPlan",
    "NarrativeBundle",
    "NarrativeDocPools",
    "NarrativeFact",
    "NarrativePlan",
    "SupportSeed",
    "StatementSeed",
    "SynthesisResult",
    "assemble_dataset",
    "bigram_containment",
    "char_overlap_ratio",
    "classify_claim",
    "claim_matches_statement",
    "collect_statement_seeds",
    "collect_support_seeds",
    "evidence_from_dict",
    "evidence_to_dict",
    "extract_narrative_corpus",
    "mineru_block_to_evidence",
    "narrative_evidence_window",
    "plan_claim_flip",
    "plan_statement_flip",
    "sample_to_dict",
    "seed_matching_statements",
    "statement_evidence_window",
    "synthesize_narrative_samples",
    "synthesize_nie_from_statement",
    "synthesize_nie_from_statements",
    "synthesize_nie_samples",
    "synthesize_refute_from_statement",
    "synthesize_refute_from_statements",
    "synthesize_refute_samples",
    "synthesize_support_from_statement",
    "synthesize_support_from_statements",
    "synthesize_support_samples",
]
