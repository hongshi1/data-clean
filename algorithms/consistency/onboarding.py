"""新文档一键接入的归纳引擎（onboarding, L1配置草稿的确定性归纳层）.

设计动机(docs/srs_project/74_rule_library_construction.md): 把"新SRS文档
接入"从手工改配置变成一条命令——从content_list.json的块归纳场景配置
(表格签名聚类/ID族/值域/域术语), 基于基规则包(srs_gjb_v1)与基词典
(srs_scene1)生成**可检查的草稿**, 草稿经load_rulepack/load_lexicon的
schema校验后即可驱动GJB合规审计与下游一致性管线。

归纳原则(全部确定性, 无LLM/无随机/无网络):
- 纯函数+模块顶层零I/O: 本模块只消费内存中的blocks/配置dict, 落盘由
  tools/onboard_new_document.py负责;
- 只应用"结构性可验证"的变更(ID根族改写/追踪表方向标记/ID族join范围),
  语义性猜测(接口表头canon/新表型归型/值域模糊列)只报告不应用——
  草稿不假装全自动, 不确定项在_onboarding段标_needs_review留人工;
- 标准级知识不动: gjb段(簇映射+库路径)逐字保留, 工具侧校验与基pack
  一致后才跑审计。

与既有层的衔接:
- 表头签名语义与algorithms/consistency/rulepack.py的SignatureSpec.match
  逐条对齐(all_headers/any_header_groups/substring组/caption/raw),
  归纳侧不依赖文件I/O(直接消费基pack的dict形态);
- ID正则与srs_scene1/doc06_scene的id_patterns同构: <根>-[A-Z0-9-]+;
- 06号解析经验全部内化: 表头在thead的th里、单元格双<p>标签(剥标签
  拼接)、colspan/rowspan(按单元格元素计数, 不做跨度展开)。
"""
from __future__ import annotations

import re
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from re import Pattern
from typing import Sequence

#: content_list.json里表格块的table_body是HTML; 文本块在text字段
_TABLE_TYPE = "table"
_TEXT_TYPE = "text"

#: GJB SRS需求标识符形态: >=2个大写字母开头的连字符段(04号PZXQ/01号
#: ZZSJHQZHFW同构), 前后不得紧邻ASCII字母数字或连字符(避免截断/粘连);
#: 段间允许残留空白(01号接口表存在「ZZSJHQZHFW -JK-WB-…」带空格形态,
#: 归纳时按去空白后的token处理)
_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9]{1,}(?:[ \t]*-[ \t]*[A-Z0-9]+)+)"
    r"(?![A-Za-z0-9-])")

#: ID token内的空白归一(带空格形态→紧凑形态)
_ID_WS_RE = re.compile(r"[ \t]+")

#: 值域闭集的已知字段(方式名称=终端形态/运行状态=阶段, 04号scene1口径)
_VALUE_DOMAIN_FIELDS = ("方式名称", "运行状态")

#: 值域列的占位值(闭集不收)
_PLACEHOLDER_VALUES = frozenset({"—", "-", "无", "不适用", "/"})

#: 域术语归纳的最小出现次数(任务口径: 出现>=3次的连续大写/混合词)
_DOMAIN_TERM_MIN_FREQ = 3

#: 结构性噪声词(用例字段词/标准号前缀)——不是域术语
_STRUCTURAL_TERM_STOP = frozenset({"Use", "Case", "Actor", "Actors", "GJB"})

#: 计量单位不是域术语(与knowledge/srs_kb.json的单位族口径一致)
_UNIT_TERM_STOP = frozenset({
    "B", "KB", "MB", "GB", "TB", "K", "M", "G", "T", "P",
    "ms", "s", "min", "h", "Hz", "kHz", "MHz", "GHz",
    "Mbps", "Gbps", "Kbps", "dpi", "px",
})

#: 版本号形态(V10/V8)与用例异常流编号(E1..E9)——结构性编号非术语
_VERSION_RE = re.compile(r"^V\d")
_EXCEPTION_ID_RE = re.compile(r"^E\d*$")

#: 模板正则里的ID字面量形态(基pack的PZXQ-[A-Z0-9-]+), 用于根族改写
_ID_LITERAL_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9]{1,})-\[A-Z0-9-\]\+")

#: 无thead表格的首行列名归一: 取「字段：」前的字段名做聚类键
_COLON_FIELD_RE = re.compile(r"^(.{1,24}?)[：:]")

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[\s　]+")

#: 表型关键词重叠打分的建议阈值(低于此值不给出归型建议)
_MATCH_SUGGEST_THRESHOLD = 0.3


# ── HTML表格解析(06号经验: thead/th + 双<p> + colspan/rowspan) ──


def _cell_text(cell_html: str) -> str:
    """单元格文本: 剥全部标签(双<p>自然拼接)再去空白(跨行拆词复原)."""
    return _WS_RE.sub("", _TAG_RE.sub("", cell_html))


def _table_rows(table_body: str) -> list[list[str]]:
    """全部tr的单元格文本列表(按元素计数, colspan/rowspan不展开)."""
    rows: list[list[str]] = []
    for row_match in _ROW_RE.finditer(table_body or ""):
        cells = [_cell_text(cell) for cell in _CELL_RE.findall(
            row_match.group(1))]
        rows.append(cells)
    return rows


def _caption_text(item: dict) -> str:
    caption = item.get("table_caption") or ""
    if isinstance(caption, list):
        return str(caption[0]) if caption else ""
    return str(caption)


def extract_table_headers(table_body: str) -> tuple[tuple[str, ...], bool]:
    """表头=(thead的th; 无thead则首行td/th), 返回(表头元组, 有无thead).

    空单元格跳过; 双<p>由_cell_text拼接; colspan/rowspan按单元格元素
    计数(签名语义下跨度不影响表头集合)。
    """
    body = table_body or ""
    thead = re.search(r"<thead>(.*?)</thead>", body, re.S)
    if thead:
        cells = re.findall(r"<th[^>]*>(.*?)</th>", thead.group(1), re.S)
        has_thead = True
    else:
        rows = _table_rows(body)
        cells = rows[0] if rows else []
        has_thead = False
    headers = tuple(cell for cell in (_cell_text(c) for c in cells) if cell)
    return headers, has_thead


def table_items(blocks: Sequence[dict]) -> list[tuple[int, dict]]:
    """(块序号, 表格块)列表——content_list遍历的公共入口."""
    return [(index, item) for index, item in enumerate(blocks)
            if str(item.get("type", "")) == _TABLE_TYPE]


def _table_text(item: dict) -> str:
    """表格块的纯文本: 剥标签+空白折叠为单空格, 单元格/行以空格分隔.

    分隔符是ID边界的前提——单元格直接拼接会让后一单元格的字母数字
    破坏前一单元格尾部ID的边界(如…JGHSJGJRWZD紧接Actors), 导致ID
    抽取截断+术语统计混入ID碎片。
    """
    body = str(item.get("table_body") or "")
    lines: list[str] = []
    for row_match in _ROW_RE.finditer(body):
        cells = [
            _WS_RE.sub(" ", _TAG_RE.sub("", cell)).strip()
            for cell in _CELL_RE.findall(row_match.group(1))]
        cells = [cell for cell in cells if cell]
        if cells:
            lines.append(" ".join(cells))
    caption = _caption_text(item)
    if caption:
        lines.append(_WS_RE.sub(" ", caption).strip())
    return "\n".join(lines)


def _block_texts(blocks: Sequence[dict]) -> str:
    """文本块原文 + 表格块纯文本(单元格保持分隔), 供ID/术语归纳."""
    parts: list[str] = []
    for item in blocks:
        kind = str(item.get("type", ""))
        if kind == _TEXT_TYPE:
            parts.append(str(item.get("text") or ""))
        elif kind == _TABLE_TYPE:
            parts.append(_table_text(item))
    return "\n".join(parts)


def _cluster_key(headers: tuple[str, ...]) -> tuple[str, ...]:
    """聚类键: 无thead首行的「字段：值」单元格取字段名, 其余原样."""
    key: list[str] = []
    for header in headers:
        match = _COLON_FIELD_RE.match(header)
        key.append(match.group(1).strip() if match else header)
    return tuple(key)


# ── 归纳数据模型 ──────────────────────────────────────────


@dataclass(frozen=True)
class TableSignatureDraft:
    """一个表头簇的归纳草稿: 出现次数/代表表头/与基pack表型的匹配建议."""

    header_signature: tuple[str, ...]
    occurrences: int
    block_indices: tuple[int, ...]
    sample_captions: tuple[str, ...]
    has_thead: bool
    matched_kind: str
    best_overlap_kind: str
    match_score: float
    needs_review: bool

    def to_dict(self) -> dict:
        return {
            "header_signature": list(self.header_signature),
            "occurrences": self.occurrences,
            "block_indices": list(self.block_indices),
            "sample_captions": list(self.sample_captions),
            "has_thead": self.has_thead,
            "matched_kind": self.matched_kind,
            "best_overlap_kind": self.best_overlap_kind,
            "match_score": round(self.match_score, 3),
            "needs_review": self.needs_review,
        }


@dataclass(frozen=True)
class IdFamilyDraft:
    """一个ID族(按前2段聚类)的归纳草稿."""

    family_prefix: str
    root: str
    occurrences: int
    distinct_ids: int
    sample_ids: tuple[str, ...]
    own_root: bool

    def to_dict(self) -> dict:
        return {
            "family_prefix": self.family_prefix,
            "root": self.root,
            "occurrences": self.occurrences,
            "distinct_ids": self.distinct_ids,
            "sample_ids": list(self.sample_ids),
            "own_root": self.own_root,
        }


@dataclass(frozen=True)
class ValueDomainCandidate:
    """值域模糊候选: 表头与已知字段名互为子串但非精确匹配(需人工裁决)."""

    field: str
    header: str
    values: tuple[str, ...]
    block_indices: tuple[int, ...]

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "header": self.header,
            "values": list(self.values),
            "block_indices": list(self.block_indices),
        }


@dataclass(frozen=True)
class TraceDirectionDraft:
    """追踪表方向配置草稿(归纳自被追踪列的文档侧前缀)."""

    signature: dict
    canon_map: dict[str, str]
    direction_first_column_prefix: str
    direction_markers: tuple[str, ...]
    trace_key_columns: dict[str, list[str]]
    column_profiles_default: list[str]
    verified_both_directions: bool

    def to_dict(self) -> dict:
        return {
            "signature": self.signature,
            "canon_map": dict(self.canon_map),
            "direction_first_column_prefix":
                self.direction_first_column_prefix,
            "direction_markers": list(self.direction_markers),
            "trace_key_columns": {
                k: list(v) for k, v in self.trace_key_columns.items()},
            "column_profiles_default": list(self.column_profiles_default),
            "verified_both_directions": self.verified_both_directions,
        }


@dataclass(frozen=True)
class InductionReport:
    """一份文档的归纳总报告(供CLI展示/runs落盘)."""

    doc_key: str
    block_count: int
    table_count: int
    table_clusters: tuple[TableSignatureDraft, ...] = ()
    id_root: str = ""
    id_families: tuple[IdFamilyDraft, ...] = ()
    value_domains: dict[str, tuple[str, ...]] = field(default_factory=dict)
    value_domain_candidates: tuple[ValueDomainCandidate, ...] = ()
    domain_terms: tuple[tuple[str, int], ...] = ()

    def to_dict(self) -> dict:
        return {
            "doc_key": self.doc_key,
            "block_count": self.block_count,
            "table_count": self.table_count,
            "table_clusters": [c.to_dict() for c in self.table_clusters],
            "id_root": self.id_root,
            "id_families": [f.to_dict() for f in self.id_families],
            "value_domains": {k: list(v)
                              for k, v in self.value_domains.items()},
            "value_domain_candidates": [
                c.to_dict() for c in self.value_domain_candidates],
            "domain_terms": [[term, freq]
                             for term, freq in self.domain_terms],
        }


# ── 基pack的dict形态匹配器(与SignatureSpec.match语义逐条对齐) ──


class _RawPackMatcher:
    """从基pack的dict执行表型分类+关键词重叠打分(零I/O, 无文件依赖)."""

    def __init__(self, base_pack: dict) -> None:
        self._schemas: dict[str, dict] = dict(
            base_pack.get("table_schemas") or {})
        self._order: list[str] = list(base_pack.get("classify_order") or [])
        if not self._order:
            self._order = list(self._schemas)
        self._keywords: dict[str, frozenset[str]] = {
            kind: self._kind_keywords(spec)
            for kind, spec in self._schemas.items() if kind != "generic_table"}

    @staticmethod
    def _kind_keywords(spec: dict) -> frozenset[str]:
        """表型关键词集=签名词+canon键+键列+画像列(打分用, 不含caption线索)."""
        words: set[str] = set()
        for signature in spec.get("signatures") or []:
            words.update(signature.get("all_headers") or [])
            for group in signature.get("any_header_groups") or []:
                words.update(group)
            for group in signature.get("any_header_substring_groups") or []:
                words.update(group)
        words.update((spec.get("canon_map") or {}).keys())
        words.update(spec.get("key_columns") or [])
        for columns in (spec.get("column_profiles") or {}).values():
            words.update(columns)
        for columns in (spec.get("trace_key_columns") or {}).values():
            words.update(columns)
        words.update(spec.get("columns") or [])
        words.update(spec.get("flow_subcolumns") or [])
        return frozenset(word for word in words if len(word) >= 2)

    def classify(self, headers: tuple[str, ...], caption: str,
                 raw_text: str) -> str:
        """按classify_order执行签名判定, 返回首个命中的表型.

        语义同RulePack.classify_table, 区别是直接消费dict形态的基pack
        (归纳引擎不依赖文件I/O)。
        """
        header_set = frozenset(headers)
        for kind in self._order:
            spec = self._schemas.get(kind)
            if spec is None:
                continue
            for signature in spec.get("signatures") or []:
                if self._signature_match(
                        signature, header_set, headers, caption, raw_text):
                    return kind
        return "generic_table"

    @staticmethod
    def _signature_match(signature: dict, header_set: frozenset[str],
                         headers: tuple[str, ...], caption: str,
                         raw_text: str) -> bool:
        if not all(header in header_set
                   for header in signature.get("all_headers") or []):
            return False
        for group in signature.get("any_header_groups") or []:
            if not any(header in header_set for header in group):
                return False
        for group in signature.get("any_header_substring_groups") or []:
            if not any(substring in header
                       for header in headers for substring in group):
                return False
        caption_any = signature.get("caption_contains_any") or []
        if caption_any and not any(sub in caption for sub in caption_any):
            return False
        raw_any = signature.get("raw_contains_any") or []
        if raw_any and not any(sub in raw_text for sub in raw_any):
            return False
        raw_regex = signature.get("raw_regex") or ""
        if raw_regex and not re.search(raw_regex, raw_text):
            return False
        return True

    def score(self, headers: tuple[str, ...]) -> tuple[str, float]:
        """各表型关键词重叠打分(空格不敏感的双向子串命中).

        返回(最佳表型, 分数=命中关键词/表型关键词数); 打分是归型建议,
        分类(classify)才是权威信号。
        """
        normalized = [header.replace(" ", "") for header in headers]
        best_kind, best_score = "", 0.0
        for kind in sorted(self._keywords):
            keywords = self._keywords[kind]
            if not keywords:
                continue
            hits = sum(1 for keyword in keywords
                       if any(keyword.replace(" ", "") in header
                              or header in keyword.replace(" ", "")
                              for header in normalized))
            score = hits / len(keywords)
            if score > best_score:
                best_kind, best_score = kind, score
        return best_kind, best_score


# ── 归纳函数(全部确定性) ─────────────────────────────────


def induce_table_signatures(
        blocks: Sequence[dict],
        base_pack: dict | None = None,
) -> list[TableSignatureDraft]:
    """提取全部表格的表头并按表头集合聚类.

    每簇给出: 出现次数/代表表头/有无thead/与GJB标准表型的匹配建议
    (匹配=基pack签名分类+关键词重叠打分——签名分类是权威信号, 打分
    是归型建议); 未被基pack分类(=generic兜底)的簇标记needs_review。
    """
    matcher = _RawPackMatcher(base_pack) if base_pack else None
    groups: dict[tuple[str, ...], list[dict]] = {}
    for index, item in table_items(blocks):
        body = str(item.get("table_body") or "")
        headers, has_thead = extract_table_headers(body)
        if not headers:
            continue
        caption = _caption_text(item)
        info = {
            "block_index": index,
            "caption": caption,
            "headers": headers,
            "has_thead": has_thead,
            "raw": body + (f"\n{caption}" if caption else ""),
        }
        groups.setdefault(_cluster_key(headers), []).append(info)
    drafts: list[TableSignatureDraft] = []
    for key, infos in sorted(groups.items(),
                             key=lambda kv: (-len(kv[1]), kv[0])):
        representative = infos[0]
        if matcher is not None:
            matched_kind = matcher.classify(
                representative["headers"], representative["caption"],
                representative["raw"])
            best_kind, score = matcher.score(key)
        else:
            matched_kind, best_kind, score = "generic_table", "", 0.0
        drafts.append(TableSignatureDraft(
            header_signature=key,
            occurrences=len(infos),
            block_indices=tuple(int(info["block_index"])
                                for info in infos),
            sample_captions=tuple(
                info["caption"] for info in infos[:3] if info["caption"]),
            has_thead=representative["has_thead"],
            matched_kind=matched_kind,
            best_overlap_kind=best_kind,
            match_score=score,
            needs_review=(matched_kind == "generic_table"),
        ))
    return drafts


def induce_id_families(blocks: Sequence[dict]) -> list[IdFamilyDraft]:
    """提取所有`根-段-段`形态ID, 按前2段聚类.

    文档自身ID族=根(首段)出现次数最多的族; 其余根(外部系统引用, 如
    01号的JCYY-/DXYY-)标记own_root=False供报告区分。
    """
    text = _block_texts(blocks)
    order: list[str] = []
    counts: Counter[str] = Counter()
    distinct: dict[str, dict[str, None]] = {}
    for match in _ID_TOKEN_RE.finditer(text):
        token = _ID_WS_RE.sub("", match.group(1))
        family = "-".join(token.split("-")[:2])
        if family not in counts:
            order.append(family)
            distinct[family] = {}
        counts[family] += 1
        distinct[family].setdefault(token, None)
    root_counts: Counter[str] = Counter()
    for family, count in counts.items():
        root_counts[family.split("-")[0]] += count
    if not root_counts:
        return []
    dominant = sorted(root_counts.items(),
                      key=lambda kv: (-kv[1], kv[0]))[0][0]
    families: list[IdFamilyDraft] = []
    for family in sorted(order, key=lambda f: (-counts[f], f)):
        samples = tuple(distinct[family])
        families.append(IdFamilyDraft(
            family_prefix=family,
            root=family.split("-")[0],
            occurrences=counts[family],
            distinct_ids=len(distinct[family]),
            sample_ids=samples[:3],
            own_root=family.split("-")[0] == dominant,
        ))
    return families


def dominant_id_root(families: Sequence[IdFamilyDraft]) -> str:
    """文档主导ID根(族分析的根级众数; 空文档返回'')."""
    if not families:
        return ""
    root_counts: Counter[str] = Counter()
    for family in families:
        root_counts[family.root] += family.occurrences
    return sorted(root_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def own_id_prefixes(families: Sequence[IdFamilyDraft]) -> list[str]:
    """文档自身ID族的根前缀集合(join_params.id_join.id_family_prefixes)."""
    return sorted({family.root for family in families if family.own_root})


def _table_column_values(
        blocks: Sequence[dict],
        header_predicate,
) -> dict[str, dict[str, dict[str, tuple[int, ...]]]]:
    """按表头谓词收集列值: {字段: {表头: {值: 块序号}}}——去重保序.

    只统计有thead的表格(表头=列名的确定性前提); rowspan/colspan按单元
    格元素计数, 跨度错位风险由去重+人工复核兜底。
    """
    collected: dict[str, dict[str, dict[str, tuple[int, ...]]]] = {}
    for index, item in table_items(blocks):
        body = str(item.get("table_body") or "")
        headers, has_thead = extract_table_headers(body)
        if not has_thead or not headers:
            continue
        rows = _table_rows(body)[1:]
        for column, header in enumerate(headers):
            field = header_predicate(header)
            if field is None:
                continue
            by_header = collected.setdefault(field, {}).setdefault(header, {})
            for row in rows:
                if len(row) <= column:
                    continue
                value = row[column]
                if not value or value in _PLACEHOLDER_VALUES:
                    continue
                block_indices = by_header.setdefault(value, ())
                if index not in block_indices:
                    by_header[value] = block_indices + (index,)
    return collected


def induce_value_domains(blocks: Sequence[dict]) -> dict[str, list[str]]:
    """方式名称/运行状态列(表头**精确**匹配)→ 值域闭集草稿.

    模糊候选(表头与字段名互为子串, 如01号表2的「状态」列)不并入闭集,
    见induce_value_domain_candidates——闭集只收确定性证据。
    """
    exact = _table_column_values(
        blocks, lambda header: header
        if header in _VALUE_DOMAIN_FIELDS else None)
    return {field: list(next(iter(by_header.values())))
            for field, by_header in exact.items()
            if by_header}


def induce_value_domain_candidates(
        blocks: Sequence[dict]) -> list[ValueDomainCandidate]:
    """值域模糊候选: 表头与已知字段互为子串但非精确(需人工裁决)."""
    candidates: list[ValueDomainCandidate] = []

    def fuzzy(header: str) -> str | None:
        for domain_field in _VALUE_DOMAIN_FIELDS:
            if (header != domain_field
                    and (header in domain_field or domain_field in header)):
                return domain_field
        return None

    for domain_field, by_header in sorted(
            _table_column_values(blocks, fuzzy).items()):
        for header, values in sorted(by_header.items()):
            block_indices = tuple(sorted({index
                                          for indices in values.values()
                                          for index in indices}))
            candidates.append(ValueDomainCandidate(
                field=domain_field, header=header, values=tuple(values),
                block_indices=block_indices))
    return candidates


def domain_term_frequencies(blocks: Sequence[dict]) -> dict[str, int]:
    """ASCII术语频次: 剥HTML/去ID后的连续字母数字词计数(词边界内)."""
    text = _ID_TOKEN_RE.sub(" ", _block_texts(blocks))
    counts: Counter[str] = Counter()
    for match in re.finditer(
            r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]{1,}(?![A-Za-z0-9])",
            text):
        counts[match.group(0)] += 1
    return dict(counts)


def induce_domain_terms(blocks: Sequence[dict]) -> list[str]:
    """高频ASCII域术语草稿(出现>=3次, 排除ID/HTML/结构词/单位/版本号)."""
    counts = domain_term_frequencies(blocks)
    terms = [
        term for term, freq in counts.items()
        if freq >= _DOMAIN_TERM_MIN_FREQ
        and term not in _STRUCTURAL_TERM_STOP
        and term not in _UNIT_TERM_STOP
        and not _VERSION_RE.match(term)
        and not _EXCEPTION_ID_RE.match(term)
    ]
    return sorted(terms, key=lambda term: (-counts[term], term))


def induce_report(blocks: Sequence[dict], doc_key: str,
                  base_pack: dict | None = None) -> InductionReport:
    """一次遍历的归纳总报告(CLI展示/runs落盘的统一数据源)."""
    families = induce_id_families(blocks)
    counts = domain_term_frequencies(blocks)
    terms = induce_domain_terms(blocks)
    return InductionReport(
        doc_key=doc_key,
        block_count=len(blocks),
        table_count=len(table_items(blocks)),
        table_clusters=tuple(induce_table_signatures(blocks, base_pack)),
        id_root=dominant_id_root(families),
        id_families=tuple(families),
        value_domains={field: tuple(values) for field, values
                       in induce_value_domains(blocks).items()},
        value_domain_candidates=tuple(induce_value_domain_candidates(blocks)),
        domain_terms=tuple((term, counts[term]) for term in terms),
    )


# ── 追踪表方向归纳(结构性验证: 正/逆向簇均须观测到) ──────────


def _trace_marker(header: str) -> str:
    """方向标记=被追踪列的文档侧前缀.

    「上级文档被追踪内容…」→上级文档; 「本文档中被追踪内容…」→本文档
    (剥尾部方位助词「中/的」)。
    """
    if "被追踪" in header:
        return header.split("被追踪")[0].rstrip("中的")
    if "名称" in header:
        return header.split("名称")[0].rstrip("中的")
    return header


def induce_trace_direction(
        clusters: Sequence[TableSignatureDraft],
        base_pack: dict,
) -> TraceDirectionDraft | None:
    """追踪表方向配置草稿(仅当基pack的canon/方向标记不覆盖时归纳).

    候选簇=匹配trace_table签名, 或caption含追踪/追溯, 或表头含被追踪
    (01号的追踪表无「章节号」列, 基trace签名不命中——caption是第二信
    号)。方向判定用caption的正向/逆向词; 正/逆向两种列序均观测到才
    标verified_both_directions=True, 否则草稿仍生成但留人工复核。
    """
    base_trace = (base_pack.get("table_schemas") or {}).get("trace_table")
    if not base_trace:
        return None
    base_prefix = str(base_trace.get("direction_first_column_prefix") or "")
    base_markers = tuple(base_trace.get("direction_markers") or ())
    base_canon_keys = set((base_trace.get("canon_map") or {}).keys())
    forward_pairs: list[tuple[str, str]] = []
    reverse_pairs: list[tuple[str, str]] = []
    unknown_pairs: list[tuple[str, str]] = []
    canon_sources: list[tuple[str, str]] = []
    for cluster in clusters:
        captions = "".join(cluster.sample_captions)
        traceish = (cluster.matched_kind == "trace_table"
                    or "追踪" in captions or "追溯" in captions
                    or any("被追踪" in header
                           for header in cluster.header_signature))
        if not traceish:
            continue
        directional = [header for header in cluster.header_signature
                       if "被追踪" in header]
        if len(directional) < 2:
            continue
        if all(header in base_canon_keys for header in directional):
            continue  # 04号形态: 基canon已覆盖, 无需变体
        markers = (_trace_marker(directional[0]),
                   _trace_marker(directional[1]))
        if not markers[0] or not markers[1] or markers[0] == markers[1]:
            continue
        canon_sources.extend(
            (header, _trace_marker(header)) for header in directional)
        if "正向" in captions:
            forward_pairs.append(markers)
        elif "逆向" in captions:
            reverse_pairs.append(markers)
        else:
            unknown_pairs.append(markers)
    pairs = forward_pairs or reverse_pairs or unknown_pairs
    if not pairs:
        return None
    forward = forward_pairs[0] if forward_pairs else pairs[0]
    if forward == base_markers[:2] and base_prefix == forward[0]:
        return None  # 与基方向配置等价(如06号短表头形态), 无需变体
    marker_a, marker_b = forward
    reverse = (marker_b, marker_a)
    verified = reverse in reverse_pairs or reverse in unknown_pairs
    canon_map = {header: f"{marker}名称标识"
                 for header, marker in canon_sources}
    return TraceDirectionDraft(
        signature={"any_header_substring_groups": [["被追踪"]]},
        canon_map=canon_map,
        direction_first_column_prefix=marker_a,
        direction_markers=(marker_a, marker_b),
        trace_key_columns={
            "forward": [f"{marker_a}名称标识", f"{marker_b}名称标识"],
            "reverse": [f"{marker_b}名称标识", f"{marker_a}名称标识"],
        },
        column_profiles_default=[
            f"{marker_a}名称标识", f"{marker_b}名称标识", "跟踪说明"],
        verified_both_directions=verified,
    )


# ── 草稿生成(基于base的dict深拷贝, 只应用结构性可验证变更) ──


def _rewrite_id_literals(pattern: str, new_root: str) -> tuple[str, set[str]]:
    """模板正则中的ID字面量根族改写(PZXQ-[A-Z0-9-]+→<root>-[…])."""
    roots: set[str] = set()

    def _sub(match: re.Match[str]) -> str:
        roots.add(match.group(1))
        return f"{new_root}-[A-Z0-9-]+"

    return _ID_LITERAL_RE.sub(_sub, pattern), roots


def build_rulepack_draft(doc_key: str, blocks: Sequence[dict],
                         base_pack: dict) -> dict:
    """基于base_pack生成<doc_key>的规则包草稿(可经load_rulepack校验).

    应用的变更(全部结构性可验证):
    - ID模板根族改写: extraction_templates含`<旧根>-[A-Z0-9-]+`字面量
      的模式替换为归纳根族;
    - ID族join范围: join_params.id_join.id_family_prefixes=文档自身根;
    - 追踪表方向变体: 签名扩展+方向前缀/标记/键列(归纳自被追踪列,
      正逆向双观测验证);
    - gjb段(簇映射+库路径)逐字保留——标准级知识不动, 由工具侧校验。
    语义性候选(接口表头canon/新表型归型)只进_onboarding.needs_review,
    不落schema。
    """
    draft = deepcopy(base_pack)
    draft["pack_id"] = f"{doc_key}_onboard_v1"
    families = induce_id_families(blocks)
    root = dominant_id_root(families)
    root_occurrences = sum(family.occurrences for family in families
                           if family.root == root)
    clusters = induce_table_signatures(blocks, base_pack)
    changes: list[dict] = []
    needs_review: list[dict] = []

    if root:
        for name, template in sorted(
                (base_pack.get("extraction_templates") or {}).items()):
            pattern = str(template.get("pattern") or "")
            new_pattern, roots = _rewrite_id_literals(pattern, root)
            if roots and roots != {root}:
                draft["extraction_templates"][name] = {
                    **template, "pattern": new_pattern}
                changes.append({
                    "target": f"extraction_templates.{name}",
                    "base_value": pattern,
                    "draft_value": new_pattern,
                    "applied": True,
                    "needs_review": False,
                    "evidence": (f"ID根族归纳: {'/'.join(sorted(roots))}"
                                 f"(基pack字面量)→{root}"
                                 f"(文档主导根, {root_occurrences}次)"),
                })
        id_join = (draft.setdefault("join_params", {})
                   .setdefault("id_join", {}))
        prefixes = own_id_prefixes(families)
        base_prefixes = id_join.get("id_family_prefixes") or []
        covers_base = any(str(prefix).startswith(root)
                          for prefix in base_prefixes)
        if (prefixes and prefixes != base_prefixes and not covers_base):
            id_join["id_family_prefixes"] = prefixes
            changes.append({
                "target": "join_params.id_join.id_family_prefixes",
                "base_value": base_prefixes or None,
                "draft_value": prefixes,
                "applied": True,
                "needs_review": False,
                "evidence": (f"文档自身ID族根={root}, 覆盖"
                             f"{root_occurrences}次ID出现"
                             f"(外部族{sum(f.occurrences for f in families
                                           if not f.own_root)}次不参与join)"),
            })

    trace_draft = induce_trace_direction(clusters, base_pack)
    if trace_draft is not None:
        trace = draft["table_schemas"]["trace_table"]
        base_trace = base_pack["table_schemas"]["trace_table"]
        trace["signatures"] = list(trace.get("signatures") or []) + [
            trace_draft.signature]
        trace["canon_map"] = {**(trace.get("canon_map") or {}),
                              **trace_draft.canon_map}
        trace["direction_first_column_prefix"] = (
            trace_draft.direction_first_column_prefix)
        trace["direction_markers"] = list(trace_draft.direction_markers)
        trace["trace_key_columns"] = {
            direction: list(columns) for direction, columns
            in trace_draft.trace_key_columns.items()}
        profiles = dict(trace.get("column_profiles") or {})
        profiles["default"] = list(trace_draft.column_profiles_default)
        trace["column_profiles"] = profiles
        changes.append({
            "target": "table_schemas.trace_table",
            "base_value": {
                "direction_first_column_prefix":
                    base_trace.get("direction_first_column_prefix"),
                "direction_markers": base_trace.get("direction_markers"),
            },
            "draft_value": trace_draft.to_dict(),
            "applied": True,
            "needs_review": not trace_draft.verified_both_directions,
            "evidence": (
                "被追踪列归纳: " + "、".join(trace_draft.canon_map)
                + ("(正逆向列序均观测到)" if
                   trace_draft.verified_both_directions
                   else "(仅单向观测, 需人工确认方向)")),
        })

    base_canons: set[str] = set()
    for spec in (base_pack.get("table_schemas") or {}).values():
        base_canons.update((spec.get("canon_map") or {}).keys())
        base_canons.update(spec.get("key_columns") or [])
        base_canons.update((spec.get("column_profiles") or {}).get(
            "default") or [])
        base_canons.update(spec.get("columns") or [])
        base_canons.update(spec.get("flow_subcolumns") or [])
    base_canons_ns = {canon.replace(" ", "") for canon in base_canons}
    for cluster in clusters:
        if cluster.needs_review:
            suggestion = ("基6表型无对应, 保持generic兜底, 需人工归型"
                          if not (cluster.best_overlap_kind
                                  and cluster.match_score
                                  >= _MATCH_SUGGEST_THRESHOLD)
                          else f"最佳重叠表型{cluster.best_overlap_kind!r}"
                               f"(score={cluster.match_score:.2f})")
            needs_review.append({
                "item": "unclassified_table_type",
                "detail": (f"表头簇{list(cluster.header_signature)}"
                           f"×{cluster.occurrences}未被基pack签名覆盖"),
                "suggestion": suggestion,
                "block_indices": list(cluster.block_indices),
            })
        else:
            uncovered = [header for header in cluster.header_signature
                         if (header.replace(" ", "") not in base_canons_ns
                             and header != "序号")]
            if uncovered:
                needs_review.append({
                    "item": "header_variant",
                    "detail": (f"{cluster.matched_kind}簇"
                               f"{list(cluster.header_signature)}×"
                               f"{cluster.occurrences}含基础canonical外"
                               f"的表头{uncovered}"),
                    "suggestion": "人工裁决是否补canon_map映射",
                    "block_indices": list(cluster.block_indices),
                })

    report = induce_report(blocks, doc_key, base_pack)
    draft["description"] = (
        f"{doc_key} onboarding草稿(基{base_pack.get('pack_id')}): "
        f"ID根={root or '(无ID)'}; "
        f"应用变更{len(changes)}项(ID模板/ID族join范围/追踪方向), "
        f"待复核{len(needs_review)}项——归纳依据见_onboarding段; "
        f"gjb段(簇映射+库路径)标准级知识逐字保留")
    draft["_onboarding"] = {
        "doc_key": doc_key,
        "base_pack": base_pack.get("pack_id"),
        "induction": report.to_dict(),
        "changes": changes,
        "needs_review": needs_review,
    }
    return draft


def build_lexicon_draft(doc_key: str, blocks: Sequence[dict],
                        base_lexicon: dict) -> dict:
    """基于base_lexicon生成<doc_key>场景词典草稿(可经load_lexicon校验).

    诱导字段: id_patterns(文档ID根族)/domain_terms(新增高频ASCII域术语)/
    value_domains(精确列匹配的闭集值); 其余字段逐字继承基场景。
    词典schema不允许携带复核标注(未知字段校验失败), 不确定项落在
    description与onboarding run报告里。
    """
    draft = deepcopy(base_lexicon)
    draft["scene"] = f"{doc_key}_scene"
    families = induce_id_families(blocks)
    root = dominant_id_root(families)
    if root:
        draft["id_patterns"] = [f"{root}-[A-Z0-9-]+"]
    base_terms = list(base_lexicon.get("domain_terms") or [])
    new_terms = [term for term in induce_domain_terms(blocks)
                 if term not in set(base_terms)]
    if new_terms:
        draft["domain_terms"] = base_terms + new_terms
    induced_domains = induce_value_domains(blocks)
    merged: dict[str, list[str]] = {}
    for domain_field, values in (base_lexicon.get("value_domains")
                                 or {}).items():
        extra = [value for value in induced_domains.get(domain_field, [])
                 if value not in set(values)]
        merged[domain_field] = list(values) + extra
    for domain_field, values in induced_domains.items():
        if domain_field not in merged:
            merged[domain_field] = list(values)
    if merged:
        draft["value_domains"] = merged
    domain_stats = {field: len(values)
                    for field, values in merged.items()}
    draft["description"] = (
        f"{doc_key}场景词典onboarding草稿(基{base_lexicon.get('scene')}): "
        f"ID模式={draft['id_patterns'][0] if root else '(继承基场景)'}; "
        f"新增域术语{len(new_terms)}个"
        f"({'、'.join(new_terms) if new_terms else '无'}); "
        f"值域{domain_stats}; "
        f"模糊候选与待复核项见onboarding run报告(词典schema不携带标注)")
    return draft


# ── 校验(缺口#3: 簇映射rule_ids须存在于规则库) ─────────────


def validate_cluster_rule_ids(pack_raw: dict,
                              rule_library: Sequence[dict]) -> list[str]:
    """簇映射的rule_ids中不存在于规则库的ID列表(空=通过).

    rulepack schema校验不交叉核对规则库(缺口#3), 本函数补上:
    load_rulepack通过+本函数返回空 ⇒ 配置引用的规则全部真实存在。
    """
    library_ids = {str(rule.get("rule_id")) for rule in rule_library}
    missing: list[str] = []
    for entry in ((pack_raw.get("gjb") or {}).get("rule_clusters") or []):
        for rule_id in entry.get("rule_ids") or []:
            if str(rule_id) not in library_ids:
                missing.append(str(rule_id))
    return missing


def validate_gjb_section_unchanged(draft_raw: dict,
                                   base_raw: dict) -> bool:
    """标准级知识不动校验: 草稿gjb段+库路径与基pack逐字一致."""
    return (draft_raw.get("gjb") == base_raw.get("gjb")
            and draft_raw.get("gjb_rule_library_path")
            == base_raw.get("gjb_rule_library_path"))


def compile_lexicon_id_pattern(pattern: str) -> Pattern[str]:
    """词典id_pattern编译(草稿自检用, 与load_lexicon同一编译语义)."""
    return re.compile(pattern)


__all__ = [
    "InductionReport",
    "IdFamilyDraft",
    "TableSignatureDraft",
    "TraceDirectionDraft",
    "ValueDomainCandidate",
    "build_lexicon_draft",
    "build_rulepack_draft",
    "compile_lexicon_id_pattern",
    "dominant_id_root",
    "domain_term_frequencies",
    "extract_table_headers",
    "induce_domain_terms",
    "induce_id_families",
    "induce_report",
    "induce_table_signatures",
    "induce_trace_direction",
    "induce_value_domain_candidates",
    "induce_value_domains",
    "own_id_prefixes",
    "table_items",
    "validate_cluster_rule_ids",
    "validate_gjb_section_unchanged",
]
