"""GJB规则库驱动的模板规则引擎（L1组件，取代手编关键词清单）。

设计意图：旧gjb_presence_expert用11条手编关键词清单做GJB合规检查，
knowledge/gjb_438c_rules_full.json的120条规则（87条applies_to含SRS）
几乎没被用上（只在rationale引用rule_id编号）。本引擎把检查逻辑从
规则库的rule原文**系统化推导**，取代手编清单：

1. 编译器（compile_rule/compile_library）：规则原文 -> CompiledCheck。
   句式分析器从description/original_text定位规范句（必须/应/宜，过滤
   词内「应」如适应/对应），对每个情态标记提取主语（跨文档主语判
   manual——单文档审计无法核验其他文档）、支配动词（指明/描述/注明/
   列出/包括...）后的宾语短语与「包括：」「如...等」枚举项，经分词
   清洗（剥功能前缀/动词前缀/的-短语包装/括号注解/ASCII枚举号）得到
   presence检查模式。**检查内容全部来自规则文本**——句式分析器只含
   语言学模板与泛称词表，不含任何GJB检查内容词。编译确定性：同输入
   同输出（无随机、无模型、无I/O）。
2. 文档审计（audit_document）：每条CompiledCheck的模式在冻结证据
   语句上做子串匹配 -> {satisfied/partial/violated/manual}：
   全命中=satisfied（含量词「每条/每个/全部」的规则封顶partial——
   存在性命中不等于逐条覆盖达成，逐条覆盖由coverage_join通道负责）；
   部分命中=partial；零命中=violated。manual=不可编译（无规范句/
   无可提取内容/跨文档规则）——诚实报告覆盖率，不假装可检。
3. 规则簇聚合（aggregate_clusters）：GJB-01~11簇=规则簇映射，外置于
   rule pack（config/rulepacks/srs_gjb_v1.json的gjb.rule_clusters段，
   每簇带rule_ids与映射理由，经rule_clusters()惰性读取）。簇裁决=簇内
   可审计规则的best-of（satisfied>partial>violated，OR语义与旧封闭
   清单一致：簇主题内容任一规则模式命中即存在）。簇内manual规则单列。
4. answer侧校验（verify_gjb_rules）：answer对某簇做出存在性声明
   （segment命中该簇规则推导模式且含存在/缺失语义标记）时，用文档
   审计裁决：簇有内容+称有->support；簇violated+称有->refute；
   簇有内容+称无->refute；簇violated+称无->closed上下文support，
   否则NIE（冻结证据为open子集不保证穷尽）。ClaimResult的
   check_item_candidates=簇id，rationale带rule_id+source_anchor+
   matched/missed模式，可追溯到(rule_id, 标准章节source, 规则原文)。

qa_module的"gjb"专家通道已切换到本引擎（verify_gjb_rules）；
旧gjb_presence_expert保留文件供coverage_expert复用但不再注册。
模块顶层零I/O：规则库加载在load_rule_library内（按路径缓存）；
簇映射与极性词表经rule_clusters()/_absence_re()/_presence_re()惰性
读取默认rule pack。
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from algorithms.consistency.evidence_statements import (
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.qa_models import (
    ClaimResult,
    QAInput,
    Verdict,
)
from algorithms.consistency.rulepack import default_rulepack

METHOD = "gjb_rule_engine"

#: 默认规则库路径已迁入rule pack(RulePack.gjb_rule_library_path,
#: config/rulepacks/srs_gjb_v1.json); load_rule_library/default_checks惰性读取.

CHECK_ITEMS: tuple[str, ...] = tuple(
    f"GJB-{index:02d}" for index in range(1, 12))

#: 规则簇映射（簇id -> (rule_ids, 映射理由)）已迁入rule pack的
#: gjb.rule_clusters段（成员与迁移前源码常量逐字一致）。映射依据=
#: 规则description与taxonomy v3 GJB-01~11项的语义对应；理由随配置
#: 供审计报告引用。簇覆盖GJB-01~11由rule_clusters()校验（缺簇报
#: 可读ValueError，不静默跳过）。
_CLUSTER_CACHE: tuple[tuple[str, tuple[str, ...], str], ...] | None = None
_CLUSTER_RULES_CACHE: dict[str, tuple[str, ...]] | None = None
_CLUSTER_REASONS_CACHE: dict[str, str] | None = None
_RULE_CLUSTER_OF_CACHE: dict[str, str] | None = None


def rule_clusters() -> tuple[tuple[str, tuple[str, ...], str], ...]:
    """簇映射（(簇id, rule_ids, 映射理由)元组，默认pack惰性缓存）.

    一条规则可服务多个簇（多对多，如041同属GJB-02/06/08/09）。
    """
    global _CLUSTER_CACHE, _CLUSTER_RULES_CACHE, _CLUSTER_REASONS_CACHE
    global _RULE_CLUSTER_OF_CACHE
    if _CLUSTER_CACHE is None:
        clusters = default_rulepack().gjb_rule_clusters
        missing = [check for check in CHECK_ITEMS
                   if check not in {c for c, _, _ in clusters}]
        if missing:
            raise ValueError(
                "rulepack gjb.rule_clusters缺簇"
                f"{missing}（aggregate/verify按GJB-01~11全簇口径工作）")
        _CLUSTER_CACHE = clusters
        _CLUSTER_RULES_CACHE = {
            cluster: rule_ids for cluster, rule_ids, _ in clusters}
        _CLUSTER_REASONS_CACHE = {
            cluster: reason for cluster, _, reason in clusters}
        rule_cluster_of: dict[str, str] = {}
        for cluster, rule_ids, _ in clusters:
            for rule_id in rule_ids:
                rule_cluster_of.setdefault(rule_id, cluster)
        _RULE_CLUSTER_OF_CACHE = rule_cluster_of
    return _CLUSTER_CACHE


def _cluster_rules() -> dict[str, tuple[str, ...]]:
    rule_clusters()
    assert _CLUSTER_RULES_CACHE is not None
    return _CLUSTER_RULES_CACHE


def _cluster_reasons() -> dict[str, str]:
    rule_clusters()
    assert _CLUSTER_REASONS_CACHE is not None
    return _CLUSTER_REASONS_CACHE


def _rule_cluster_of() -> dict[str, str]:
    rule_clusters()
    assert _RULE_CLUSTER_OF_CACHE is not None
    return _RULE_CLUSTER_OF_CACHE

_SENT_SPLIT = re.compile(r"(?<=[。；\n])")
_MODAL_RE = re.compile(r"必须|应|宜")
#: 「应」前接这些字时是词内成分(适应/反应/响应/对应...)而非情态动词
_MODAL_PRECEDING_BLACKLIST = frozenset("反适响对应答变激供呼")
_CROSS_DOC_NAMES = ("SSS", "IRS", "SDD", "STP", "IDD", "SSDD", "OCD", "SDP")
_SELF_DOC_MARKERS = ("SRS", "本条", "本章", "本文档", "本规格说明", "规格说明",
                     "文档", "需求", "CSCI")

#: 支配动词（长词优先）：情态动词后构成「应X宾语」的X；「包括/包含」的
#: 宾语取到句末（枚举可跨逗号），其余取到首个小句边界
_GOVERNING_VERBS: tuple[str, ...] = (
    "详细说明", "逐一列出", "概括说明", "指明", "描述", "注明", "列出",
    "标识", "定义", "规定", "概述", "说明", "包括", "包含", "给出",
    "提供", "考虑", "陈述", "指定", "概括", "分解", "引用", "校验",
    "覆盖", "登记", "命名",
)
#: 枚举项句（a)/b)/1)开头）直接整句挖模式（标准条目的a)b)c)子项）
_ENUM_ITEM_SENTENCE_RE = re.compile(r"^(?:[a-eA-E][).．]|[0-9]{1,2}[).．])")

#: 术语切分符：顿号/逗号/分号/冒号/括号 + 连词/举例标记
_TERM_SPLIT = re.compile(
    r"[、，,；;：:（）()/]|以及|或者|例如|如|和|及|或|而|以便|到")
#: 功能前缀（循环剥离）：介词/量词/指代/情态功能词
_FUNCTION_PREFIX_RE = re.compile(
    r"^(?:对|与|在|所|以|包括|若|当|每条|每个|每一|各|本条|本章|本文档|"
    r"该|全部|其他|一[组张个条]|适用时|其中|它们|被|已|均|都|也|还|"
    r"关于|通过|针对|若适用|从|由|为|使)+")
#: 内容前缀（单次剥离，剩余需>=2字）：动词/泛称名词前缀
_CONTENT_PREFIXES: tuple[str, ...] = (
    "计算机", "CSCI", "维护", "防止", "降低", "减少", "确保", "保证",
    "提供", "使用", "采用", "定义", "描述", "指明", "注明", "列出",
    "标识", "引入", "施加", "考虑", "概述", "建立", "保持", "终止",
    "报告", "需要", "要求", "支持", "满足", "遵守", "遵循", "适应",
    "系统", "软件", "数据", "文档", "给出", "得出", "采取", "执行",
    "实施", "完成", "获得", "得到", "标注", "标明", "叙述", "阐述",
)
#: 术语后缀（循环剥离，剩余需>=2字）：的需求/的要求/有关/章等包装
_TERM_SUFFIX_RE = re.compile(
    r"(?:等方面的要求|方面的要求|的影响|的需求|的要求|的行为|的规定|"
    r"的特征|的内容|下所需|的需求|其他|需求|要求|行为|规定|特征|内容|"
    r"有关|等|章)+$")
#: 括号注解（演示(直接运行...)）剥离为分隔符
_PAREN_RE = re.compile(r"[(（][^)）]*[)）]")
#: 术语两端非实体字符（ASCII枚举号a)/1)/标点/空白/列举助词「等」）
_TRIM_RE = re.compile(
    r"^[^（(\u4e00-\u9fff]+|[。；;，,、．.!？?：:\s等]+$|^的+|的+$")
_DE_SPLIT = re.compile(r"的")
_HEAD_SPLIT = re.compile(r"和|及|或")
#: 短语式宾语长度阈值：超过则只取「的」头部的实体（丢弃介词短语残段）
_PHRASE_THRESHOLD = 12
#: 功能残段标记（句式分析器词汇）：含任一即丢弃该候选模式
_JUNK_MARKERS: tuple[str, ...] = (
    "所涉", "派生", "有关", "考虑", "尽可能", "从本", "到所", "说明中",
    "给出", "得到", "确保", "引入", "施加", "采取", "执行", "实施",
    "完成", "遵循", "遵守", "必须", "提供", "采用", "使用", "所述",
    "所指", "所有GJB", "任一", "断裂", "构成", "确立",
)
_ASCII_RE = re.compile(r"[A-Za-z]")

#: 泛称词表（句式分析器的语言学词汇，非GJB检查内容）
_GENERIC_TERMS = frozenset({
    "需求", "系统", "软件", "文档", "数据", "信息", "内容", "方法", "方式",
    "要求", "特征", "规定", "其他", "有关", "方面", "全部", "每个", "每条",
    "行为", "考虑", "名称", "组成", "各个", "一条", "本条", "本章",
    "标识", "条件", "存在", "是否", "一致", "一致性", "途径", "他们",
    "其中", "以及", "适用", "适用时", "若有", "适当时", "如", "均",
})
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_MIN_TERM_CHARS = 2
_MAX_TERM_CHARS = 10
#: 量词标记：「每条/每个/每一/全部/所有」→ 存在性命中也只判partial
_QUANTIFIER_RE = re.compile(r"每[一条个]|全部|所有")

#: answer侧极性词表取自rule pack：缺失词表与gjb_presence_expert共享
#: （gjb_absence_words）；存在词表为引擎专用子集（gjb_rule_presence_words，
#: 不含"应/自动*"——引擎另有治理词门控，行为与迁移前源码逐字一致）。
#: 模块级缓存避免逐segment重建，import期零I/O。
_ABSENCE_RE_CACHE: re.Pattern[str] | None = None
_PRESENCE_RE_CACHE: re.Pattern[str] | None = None


def _absence_re() -> re.Pattern[str]:
    """缺失语义标记词表（规则包gjb_absence_words）。"""
    global _ABSENCE_RE_CACHE
    if _ABSENCE_RE_CACHE is None:
        _ABSENCE_RE_CACHE = default_rulepack().vocabulary_regex(
            "gjb_absence_words")
    return _ABSENCE_RE_CACHE


def _presence_re() -> re.Pattern[str]:
    """存在语义标记词表（规则包gjb_rule_presence_words，引擎子集）。"""
    global _PRESENCE_RE_CACHE
    if _PRESENCE_RE_CACHE is None:
        _PRESENCE_RE_CACHE = default_rulepack().vocabulary_regex(
            "gjb_rule_presence_words")
    return _PRESENCE_RE_CACHE


_SEGMENT_SPLIT = re.compile(r"(?<=[。；！？\n])")
_MIN_SEGMENT_CHARS = 6
#: answer侧触发模式最小长度（3字以下词太泛，易把非存在性提及当声明）
_MIN_TRIGGER_CHARS = 3
#: 条款治理词：answer的存在性声明须是「有X条款/需求/方法/表」形态；
#: 触发词自身含治理词或紧邻±4字含治理词才构成声明（排除「确保可靠性」
#: 类修辞性提及——那不是对文档内容存在的断言）
_GOVERNANCE_RE = re.compile(
    r"方法|需求|功能|条款|规定|措施|策略|模式|要素|机制|能力|日志|"
    r"准则|约束|表|章|节")
_GOVERNANCE_WINDOW = 4


@dataclass(frozen=True)
class CompiledCheck:
    """一条规则的编译产物：规则原文 -> 可执行presence检查。

    patterns为从规则原文推导的检查模式（宾语/枚举项清洗后的内容词）；
    check_type为manual表示该规则不可编译为单文档存在性检查（理由见
    compile_note），诚实报告不假装可检。
    """

    rule_id: str
    check_type: str
    requirement: str
    source_anchor: str
    patterns: tuple[str, ...]
    cluster: str
    quantified: bool = False
    modality: str = ""
    compile_note: str = ""


@dataclass(frozen=True)
class RuleAuditResult:
    """一条CompiledCheck对冻结证据语句的审计结果（文档级）。"""

    rule_id: str
    check_type: str
    verdict: str
    requirement: str
    source_anchor: str
    patterns: tuple[str, ...]
    matched: tuple[str, ...]
    missed: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    cluster: str
    rationale: str


@dataclass(frozen=True)
class ClusterAudit:
    """一个GJB规则簇的聚合审计结果（best-of，OR语义）。"""

    cluster: str
    verdict: str
    rule_ids: tuple[str, ...]
    audited_rule_ids: tuple[str, ...]
    manual_rule_ids: tuple[str, ...]
    matched_patterns: tuple[str, ...]
    missed_patterns: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    note: str = ""


_LIBRARY_CACHE: dict[str, list[dict]] = {}
_COMPILED_CACHE: dict[str, tuple[CompiledCheck, ...]] = {}


def load_rule_library(path: str | Path | None = None) -> list[dict]:
    """加载规则库中applies_to含SRS的规则（函数内I/O，按路径缓存）。

    缺省路径取自rule pack的gjb_rule_library_path（config/rulepacks/
    srs_gjb_v1.json; 相对仓库根解析, 与原CWD相对路径在仓库根运行时等价）。
    """
    if path is None:
        from algorithms.consistency.rulepack import default_rulepack

        resolved = str(
            Path(__file__).resolve().parents[2] / default_rulepack().gjb_rule_library_path)
    else:
        resolved = str(path)
    if resolved not in _LIBRARY_CACHE:
        with open(resolved, encoding="utf-8") as handle:
            data = json.load(handle)
        rules = [rule for rule in data.get("rules", [])
                 if "SRS" in (rule.get("applies_to") or [])]
        rules.sort(key=lambda rule: str(rule.get("rule_id", "")))
        _LIBRARY_CACHE[resolved] = rules
    return _LIBRARY_CACHE[resolved]


def _normative_marks(sentence: str) -> list[tuple[int, str]]:
    """句内情态标记位置（必须/应/宜）；过滤词内「应」（适应/对应...）。"""
    marks: list[tuple[int, str]] = []
    for match in _MODAL_RE.finditer(sentence):
        word = match.group()
        if word == "应" and match.start() > 0:
            previous = sentence[match.start() - 1]
            if previous in _MODAL_PRECEDING_BLACKLIST:
                continue
        marks.append((match.start(), word))
    return marks


def _cross_document_span(sentence: str, modal_pos: int) -> bool:
    """句首到情态标记的跨度是否为其他文档主语（跨文档规则）。

    跨文档名出现在任何自指标记之前（或无自指标记）即判跨文档；
    「SSS/IRS/SRS三类规格说明」这类并列含SRS的主语不算跨文档。
    """
    span = sentence[:modal_pos].replace(" ", "")
    first_self = min((span.find(marker) for marker in _SELF_DOC_MARKERS
                      if marker in span), default=-1)
    for name in _CROSS_DOC_NAMES:
        pos = span.find(name)
        if pos >= 0 and (first_self < 0 or pos < first_self):
            return True
    return False


def _governing_verb(after_modal: str) -> str:
    """情态标记之后的支配动词（长词优先，无则空串）。"""
    for verb in _GOVERNING_VERBS:
        if after_modal.startswith(verb):
            return verb
    return ""


def _normalize_candidate(term: str) -> str:
    """候选术语的规范化：剥内容/功能前缀与后缀包装（可返回空串）。"""
    previous = None
    while previous != term:
        previous = term
        for prefix in _CONTENT_PREFIXES:
            if (term.startswith(prefix)
                    and len(term) - len(prefix) >= _MIN_TERM_CHARS):
                term = term[len(prefix):]
                break
        term = _FUNCTION_PREFIX_RE.sub("", term)
        stripped = _TERM_SUFFIX_RE.sub("", term)
        if stripped and len(stripped) >= _MIN_TERM_CHARS:
            term = stripped
    return _TRIM_RE.sub("", term).strip()


def _valid_pattern(term: str) -> bool:
    """候选术语是否可作为检查模式（长度/CJK/泛称/功能残段过滤）。"""
    return (bool(term)
            and _MIN_TERM_CHARS <= len(term) <= _MAX_TERM_CHARS
            and term not in _GENERIC_TERMS
            and _CJK_RE.search(term) is not None
            and _ASCII_RE.search(term) is None
            and not any(marker in term for marker in _JUNK_MARKERS))


def _clean_terms(raw: str) -> list[str]:
    """一个原始片段 -> 检查模式列表（可为空）。

    流程：剥括号注解/两端非实体字符 -> 规范化（功能/内容前缀与后缀
    包装） -> 短语式宾语(>12字)只取「的」头部实体 -> 的-短语头部按
    和/及/或再分，头部无效时回退取修饰段尾部实体 -> 模式有效性过滤。
    """
    term = _TRIM_RE.sub("", _PAREN_RE.sub("、", raw)).strip()
    if not term:
        return []
    term = _normalize_candidate(term)
    if not term:
        return []
    if len(term) > _PHRASE_THRESHOLD:
        chunks = [chunk for chunk in _DE_SPLIT.split(term) if chunk]
        if chunks:
            head = _normalize_candidate(chunks[-1])
            if _valid_pattern(head):
                return [head]
            for chunk in reversed(chunks[:-1]):
                tail = _normalize_candidate(chunk)[-_MAX_TERM_CHARS:]
                if _valid_pattern(tail):
                    return [tail]
        return []
    if "的" in term:
        chunks = [chunk for chunk in _DE_SPLIT.split(term) if chunk]
        if chunks:
            head = chunks[-1]
            candidates = [_normalize_candidate(part)
                          for part in _HEAD_SPLIT.split(head) if part]
            valid = [part for part in candidates if _valid_pattern(part)]
            if valid:
                return valid
            if len(chunks) > 1:
                tail = _normalize_candidate(chunks[0])[-_MAX_TERM_CHARS:]
                if _valid_pattern(tail):
                    return [tail]
            return []
    return [term] if _valid_pattern(term) else []


def _mine_terms(chunk: str) -> list[str]:
    """一个文本块 -> 检查模式列表（切分+清洗+去重保序）。

    切分前先剥括号注解（演示(直接运行...)的括号内容是解释非要求），
    避免切分符在括号处先行切开导致注解内容泄漏为模式。
    """
    terms: list[str] = []
    for raw in _TERM_SPLIT.split(_PAREN_RE.sub("、", chunk)):
        for cleaned in _clean_terms(raw):
            if cleaned not in terms:
                terms.append(cleaned)
    return terms


def _enumeration_chunks(sentence: str) -> list[str]:
    """句内的枚举内容块：「包括：...」与「如...等」两种形态。"""
    chunks: list[str] = []
    for match in re.finditer(r"包括[：:]?", sentence):
        chunks.append(sentence[match.end():])
    for match in re.finditer(r"例如|如", sentence):
        rest = sentence[match.end():]
        end = re.search(r"等", rest)
        if end is not None and end.start() >= 2:
            chunks.append(rest[:end.start()])
    return chunks


def _object_chunk(sentence: str, modal_pos: int, modal_len: int,
                  verb: str) -> str:
    """支配动词后的宾语短语。

    动词为「包括/包含」时宾语取到句末（枚举项可跨逗号）；否则取到首个
    小句边界（，(）。(）等）。
    """
    start = modal_pos + modal_len + len(verb)
    rest = sentence[start:]
    if verb in ("包括", "包含", "逐一列出"):
        return rest
    cut = re.search(r"[。；，,（(]", rest)
    return rest[:cut.start()] if cut is not None else rest


_CONTINUATION_RE = re.compile(
    r"[，,](?:并|还|且|或|也|同时|此外|再)?(?P<verb>详细说明|逐一列出|"
    r"概括说明|指明|描述|注明|列出|标识|定义|规定|概述|说明|包括|包含|"
    r"给出|提供|考虑|陈述|指定|概括|分解|引用|校验|覆盖|登记|命名)")


def _continuation_objects(sentence: str) -> list[str]:
    """无模态的连续小句（「并描述X」「，还应Y」去情态后的裸动词）宾语。"""
    objects: list[str] = []
    for match in _CONTINUATION_RE.finditer(sentence):
        rest = sentence[match.end():]
        cut = re.search(r"[。；，,（(]", rest)
        chunk = rest[:cut.start()] if cut is not None else rest
        if chunk:
            objects.append(chunk)
    return objects


def compile_rule(rule: dict) -> CompiledCheck:
    """一条规则 -> CompiledCheck（确定性：同输入同输出）。

    content/structure/interface/format/parameter规则统一走规范句式
    分析：主语（跨文档判manual）-> 情态标记 -> 支配动词 -> 宾语短语
    + 枚举项 -> 清洗后的检查模式。推导不出模式判manual（附原因）。
    """
    rule_id = str(rule.get("rule_id", ""))
    rule_type = str(rule.get("type", "content"))
    source_anchor = str(rule.get("source", ""))
    modality = str(rule.get("modality", "") or "")
    description = str(rule.get("description", "") or "")
    original_text = str(rule.get("original_text", "") or "")
    cluster = _rule_cluster_of().get(rule_id, "")
    base = CompiledCheck(
        rule_id=rule_id, check_type=rule_type, requirement="",
        source_anchor=source_anchor, patterns=(), cluster=cluster,
        modality=modality)

    text = description if description.strip() else original_text
    if not text.strip():
        return _manual(base, "规则无description/original_text")

    sentences = [item.strip() for item in _SENT_SPLIT.split(text)
                 if item.strip()]
    requirements: list[str] = []
    terms: list[str] = []
    quantified = False
    has_normative = False
    for sentence in sentences:
        marks = _normative_marks(sentence)
        enum_chunks = _enumeration_chunks(sentence)
        if _ENUM_ITEM_SENTENCE_RE.match(sentence):
            enum_chunks.append(sentence)
        for chunk in enum_chunks:
            for term in _mine_terms(chunk):
                if term not in terms:
                    terms.append(term)
        if not marks:
            continue
        has_normative = True
        requirements.append(sentence)
        if _QUANTIFIER_RE.search(sentence):
            quantified = True
        if _cross_document_span(sentence, marks[0][0]):
            return _manual(base, "规范主语为其他文档类型(跨文档规则)")
        for modal_pos, modal_word in marks:
            modal_len = len(modal_word)
            verb = _governing_verb(sentence[modal_pos + modal_len:])
            if not verb:
                continue
            for term in _mine_terms(_object_chunk(
                    sentence, modal_pos, modal_len, verb)):
                if term not in terms:
                    terms.append(term)
        for chunk in _continuation_objects(sentence):
            for term in _mine_terms(chunk):
                if term not in terms:
                    terms.append(term)
    if not has_normative:
        first = sentences[0]
        if _cross_document_span(first, len(first)):
            return _manual(base, "规范主语为其他文档类型(跨文档规则)")
        terms = _mine_terms(first)
        if not terms:
            return _manual(base, "无规范句且无可提取枚举内容")
        return _compiled(base, first, terms, quantified=False)
    if not terms:
        return _manual(base, "规范句宾语/枚举无可提取内容词")
    requirement = "；".join(requirements)
    return _compiled(base, requirement, terms, quantified)


def _manual(base: CompiledCheck, note: str) -> CompiledCheck:
    return CompiledCheck(
        rule_id=base.rule_id, check_type="manual",
        requirement=base.requirement, source_anchor=base.source_anchor,
        patterns=(), cluster=base.cluster, quantified=False,
        modality=base.modality, compile_note=note)


def _compiled(base: CompiledCheck, requirement: str,
              patterns: tuple[str, ...] | list[str],
              quantified: bool) -> CompiledCheck:
    capped = requirement if len(requirement) <= 160 else requirement[:160]
    return CompiledCheck(
        rule_id=base.rule_id, check_type=base.check_type,
        requirement=capped, source_anchor=base.source_anchor,
        patterns=tuple(patterns), cluster=base.cluster,
        quantified=quantified, modality=base.modality)


def compile_library(
        rules: Iterable[dict] | None = None) -> tuple[CompiledCheck, ...]:
    """规则库 -> CompiledCheck元组（确定性）。"""
    if rules is None:
        return default_checks()
    return tuple(compile_rule(rule) for rule in rules)


def default_checks(path: str | Path | None = None) -> tuple[CompiledCheck, ...]:
    """默认规则库的编译结果（缓存；library路径级的确定性）。"""
    if path is None:
        from algorithms.consistency.rulepack import default_rulepack

        resolved = str(
            Path(__file__).resolve().parents[2]
            / default_rulepack().gjb_rule_library_path)
    else:
        resolved = str(path)
    if resolved not in _COMPILED_CACHE:
        _COMPILED_CACHE[resolved] = tuple(
            compile_rule(rule) for rule in load_rule_library(resolved))
    return _COMPILED_CACHE[resolved]


def audit_document(
        statements: Iterable[EvidenceStatement],
        checks: Iterable[CompiledCheck],
) -> list[RuleAuditResult]:
    """每条CompiledCheck在冻结证据语句上的存在性审计（文档级）。

    模式=子串匹配语句文本；全命中且无量词=satisfied，含量词封顶
    partial（存在性命中但逐条覆盖未核验），部分命中=partial，
    零命中=violated，manual=不可编译。
    """
    texts = [(statement.evidence_id, statement.text)
             for statement in statements]
    results: list[RuleAuditResult] = []
    for check in checks:
        if check.check_type == "manual" or not check.patterns:
            results.append(RuleAuditResult(
                rule_id=check.rule_id, check_type=check.check_type,
                verdict="manual", requirement=check.requirement,
                source_anchor=check.source_anchor, patterns=(),
                matched=(), missed=(), evidence_refs=(), cluster=check.cluster,
                rationale=(f"{check.rule_id}({check.source_anchor})不可编译"
                           f"为单文档检查：{check.compile_note}")))
            continue
        matched: list[str] = []
        missed: list[str] = []
        refs: dict[str, None] = {}
        for pattern in check.patterns:
            hit = False
            for evidence_id, text in texts:
                if pattern in text:
                    refs[evidence_id] = None
                    hit = True
            (matched if hit else missed).append(pattern)
        if not matched:
            verdict = "violated"
            rationale = (f"{check.rule_id}({check.source_anchor})要求"
                         f"[{check.requirement}]，冻结证据全部模式"
                         f"[{'、'.join(check.patterns)}]零命中")
        elif missed or check.quantified:
            verdict = "partial"
            detail = []
            if missed:
                detail.append(f"缺失模式[{('、'.join(missed))}]")
            if check.quantified:
                detail.append("量词要求(每条/每个/全部)的存在性命中"
                              "不等于逐条覆盖达成")
            rationale = (f"{check.rule_id}({check.source_anchor})要求"
                         f"[{check.requirement}]，命中模式"
                         f"[{'、'.join(matched)}]；{'；'.join(detail)}")
        else:
            verdict = "satisfied"
            rationale = (f"{check.rule_id}({check.source_anchor})要求"
                         f"[{check.requirement}]，全部模式"
                         f"[{'、'.join(matched)}]命中")
        results.append(RuleAuditResult(
            rule_id=check.rule_id, check_type=check.check_type,
            verdict=verdict, requirement=check.requirement,
            source_anchor=check.source_anchor, patterns=check.patterns,
            matched=tuple(matched), missed=tuple(missed),
            evidence_refs=tuple(refs), cluster=check.cluster,
            rationale=rationale))
    return results


def aggregate_clusters(
        audit_results: Iterable[RuleAuditResult],
) -> dict[str, ClusterAudit]:
    """GJB-01~11簇聚合：簇内可审计规则best-of（OR语义）。

    簇成员取自rule pack的gjb.rule_clusters映射（一条规则可服务多个簇，
    如041同属GJB-02/06/08/09）；best-of与旧封闭清单一致：簇主题的规则
    任一satisfied即satisfied，任一partial即partial，全部violated才
    violated；manual规则单列（簇内无任何可审计规则时簇verdict=manual）。
    """
    by_rule = {result.rule_id: result for result in audit_results}
    cluster_rules = _cluster_rules()
    cluster_reasons = _cluster_reasons()
    audits: dict[str, ClusterAudit] = {}
    for cluster in CHECK_ITEMS:
        cluster_results = sorted(
            (by_rule[rule_id] for rule_id in cluster_rules[cluster]
             if rule_id in by_rule), key=lambda item: item.rule_id)
        manual_ids = tuple(result.rule_id for result in cluster_results
                           if result.verdict == "manual")
        audited = [result for result in cluster_results
                   if result.verdict != "manual"]
        audited_ids = tuple(result.rule_id for result in audited)
        matched: list[str] = []
        missed: list[str] = []
        refs: dict[str, None] = {}
        for result in audited:
            for pattern in result.matched:
                if pattern not in matched:
                    matched.append(pattern)
            for pattern in result.missed:
                if pattern not in missed:
                    missed.append(pattern)
            for ref in result.evidence_refs:
                refs[ref] = None
        if not audited:
            verdict = "manual" if cluster_results else "unmapped"
        elif any(result.verdict == "satisfied" for result in audited):
            verdict = "satisfied"
        elif any(result.verdict == "partial" for result in audited):
            verdict = "partial"
        else:
            verdict = "violated"
        parts = [cluster_reasons[cluster]]
        if manual_ids:
            parts.append(f"manual规则[{('、'.join(manual_ids))}]不可单文档"
                         "审计，未参与聚合")
        audits[cluster] = ClusterAudit(
            cluster=cluster, verdict=verdict,
            rule_ids=cluster_rules[cluster],
            audited_rule_ids=audited_ids, manual_rule_ids=manual_ids,
            matched_patterns=tuple(matched), missed_patterns=tuple(missed),
            evidence_refs=tuple(refs), note="；".join(parts))
    return audits


def _segment_polarity(segment: str) -> str | None:
    """segment的存在性语义：absent优先于present（语法标记，非检查内容）。"""
    if _absence_re().search(segment):
        return "absent"
    if _presence_re().search(segment):
        return "present"
    return None


def _cluster_triggers(checks: Iterable[CompiledCheck],
                      ) -> dict[str, tuple[str, ...]]:
    """簇 -> answer侧触发模式（簇映射中各规则的推导模式，>=3字）。

    一条规则可服务多个簇（簇映射多对多），触发模式按簇映射收集而非
    单一cluster字段，与aggregate_clusters同一口径。
    """
    by_rule: dict[str, CompiledCheck] = {check.rule_id: check
                                         for check in checks}
    triggers: dict[str, tuple[str, ...]] = {}
    for cluster, rule_ids, _ in rule_clusters():
        items: list[str] = []
        for rule_id in rule_ids:
            check = by_rule.get(rule_id)
            if check is None or check.check_type == "manual":
                continue
            for pattern in check.patterns:
                if (len(pattern) >= _MIN_TRIGGER_CHARS
                        and pattern not in items):
                    items.append(pattern)
        triggers[cluster] = tuple(items)
    return triggers


def _claimable_trigger(segment: str, trigger: str) -> bool:
    """触发词在segment中是否构成存在性声明（治理词门控）。"""
    if _GOVERNANCE_RE.search(trigger):
        return True
    start = segment.find(trigger)
    while start >= 0:
        window = segment[max(0, start - _GOVERNANCE_WINDOW):start + len(
            trigger) + _GOVERNANCE_WINDOW]
        if _GOVERNANCE_RE.search(window):
            return True
        start = segment.find(trigger, start + 1)
    return False


def _answer_rule_claims(
        answer: str, triggers: dict[str, tuple[str, ...]],
) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """提取answer中对规则簇的存在性声明。

    返回(cluster, polarity, segment, 命中触发模式)；同一(簇, 极性)
    只保留首个命中segment（answer内去重，判定确定性）。
    """
    claims: list[tuple[str, str, str, tuple[str, ...]]] = []
    seen: set[tuple[str, str]] = set()
    for raw_segment in _SEGMENT_SPLIT.split(answer):
        segment = raw_segment.strip()
        if len(segment) < _MIN_SEGMENT_CHARS:
            continue
        polarity = _segment_polarity(segment)
        if polarity is None:
            continue
        for cluster in CHECK_ITEMS:
            cluster_triggers = triggers.get(cluster, ())
            hits = tuple(trigger for trigger in cluster_triggers
                         if trigger in segment
                         and _claimable_trigger(segment, trigger))
            if not hits:
                continue
            key = (cluster, polarity)
            if key in seen:
                continue
            seen.add(key)
            claims.append((cluster, polarity, segment, hits))
    return claims


def verify_gjb_rules(
        request: QAInput,
        statements: Iterable[EvidenceStatement] | None = None,
        library: Iterable[CompiledCheck] | None = None,
) -> list[ClaimResult]:
    """校验answer对GJB规则簇的存在性声称（L1确定性）。

    library缺省时编译默认规则库（函数内加载+缓存，顶层零I/O）。
    输出method="gjb_rule_engine"的ClaimResult；answer不涉及规则簇
    推导模式的存在性声明时返回[]（无审计噪音）。
    """
    checks = tuple(library) if library is not None else default_checks()
    if statements is None:
        statement_list = list(linearize_context(tuple(request.evidence)))
    else:
        statement_list = list(statements)
    audit_results = audit_document(statement_list, checks)
    audits = aggregate_clusters(audit_results)
    anchors = {result.rule_id: result.source_anchor
               for result in audit_results}
    triggers = _cluster_triggers(checks)
    context_closed = bool(request.evidence) and all(
        block.completeness == "closed" for block in request.evidence)
    results: list[ClaimResult] = []
    for order, (cluster, polarity, segment, hits) in enumerate(
            _answer_rule_claims(request.answer, triggers), start=1):
        state = audits[cluster]
        rule_ids = "、".join(
            f"{rule_id}({anchors.get(rule_id, '')})"
            for rule_id in (state.audited_rule_ids or state.rule_ids))
        verdict: Verdict
        if polarity == "present":
            if state.verdict in ("satisfied", "partial"):
                verdict = "support"
                refs = state.evidence_refs
                confidence = 0.9
                rationale = (
                    f"{cluster}规则簇[{rule_ids}]：冻结证据命中"
                    f"[{'、'.join(state.matched_patterns)}]"
                    f"（缺失[{('、'.join(state.missed_patterns)) or '无'}]），"
                    f"answer存在性声称（{'、'.join(hits)}）成立；"
                    f"规则依据{state.note}")
            else:
                verdict = "refute"
                refs = ()
                confidence = 0.9
                rationale = (
                    f"{cluster}规则簇[{rule_ids}]要求模式"
                    f"[{'、'.join(state.missed_patterns)}]，冻结证据零命中，"
                    f"answer声称存在（{'、'.join(hits)}）但证据中无该规则"
                    f"要求的内容——存在性声称判refute；规则依据{state.note}")
        else:
            if state.verdict in ("satisfied", "partial"):
                verdict = "refute"
                refs = state.evidence_refs
                confidence = 0.9
                rationale = (
                    f"{cluster}规则簇[{rule_ids}]：冻结证据命中"
                    f"[{'、'.join(state.matched_patterns)}]，answer声称缺失"
                    f"（{'、'.join(hits)}）与证据矛盾；规则依据{state.note}")
            elif context_closed:
                verdict = "support"
                refs = ()
                confidence = 0.9
                rationale = (
                    f"{cluster}规则簇[{rule_ids}]：封闭上下文"
                    f"（completeness=closed）中未见规则要求模式，answer缺失"
                    f"声称（{'、'.join(hits)}）成立；规则依据{state.note}")
            else:
                verdict = "not_in_evidence"
                refs = ()
                confidence = 0.0
                rationale = (
                    f"{cluster}规则簇[{rule_ids}]：冻结证据未见规则要求"
                    f"模式，但上下文非closed（证据为open子集，不保证穷尽），"
                    f"无法证实文档整体缺失——answer缺失声称"
                    f"（{'、'.join(hits)}）判not_in_evidence；"
                    f"规则依据{state.note}")
        results.append(ClaimResult(
            claim_id=f"{request.instance_id}-gjr{order:02d}",
            claim_text=segment,
            verdict=verdict,
            check_item_candidates=(cluster,),
            evidence_refs=refs,
            rationale=rationale,
            method=METHOD,
            confidence=confidence,
        ))
    return results


__all__ = [
    "CHECK_ITEMS",
    "ClusterAudit",
    "CompiledCheck",
    "METHOD",
    "RuleAuditResult",
    "aggregate_clusters",
    "audit_document",
    "compile_library",
    "compile_rule",
    "default_checks",
    "load_rule_library",
    "rule_clusters",
    "verify_gjb_rules",
]
