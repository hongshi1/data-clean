"""L1 rule pack: 规则包配置层（"检查什么、匹配什么"的声明式载体）.

设计(docs/srs_project/64_rulepack_design.md): L1专家的硬编码域知识
（表格签名/列映射/模板正则/词表/窗口/阈值）迁出到JSON rule pack, 专家
引擎保留算法能力（join/对齐/裁决）, 从配置执行。分层原则:

- 进配置: 表头签名、列名规范映射、键列、列画像、E1/步骤/追踪行等模板
  正则、词表、封闭值域、配对阈值、主体窗口、错字距离、族段数、置信度;
- 留引擎: 注册表join、主体聚簇、精确优先分层、NW对齐、Z3、HTML/Mermaid
  解析、claim路由、三态聚合。

本模块: Template/TableSchemaSpec/SignatureSpec/UseCaseFields/RulePack
数据类 + load_rulepack(path)（schema校验+可读报错+按路径缓存） +
default_rulepack()（惰性加载默认srs_gjb_v1, 模块顶层零I/O——import期
不读任何文件, 首次调用时加载） + set_default_rulepack(pack)（切换全局
默认pack, 与ner_lexicon.set_default_lexicon对称, 场景迁移入口）.

词表两种消费形态: (a)vocabulary() 原词元组——成员/子串/剥离判定;
(b)vocabulary_regex() 平铺交替正则——原源码中形如re.compile("A|B|C")
的词表, 引擎用"|".join(map(re.escape, words))编译, 词均纯CJK/ASCII
无元字符, 与源码正则逐字等价。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DEFAULT_PACK_PATH = BASE / "config" / "rulepacks" / "srs_gjb_v1.json"

#: 表型分类的判定顺序(语义敏感: 能力→接口→值域→合格性→追踪→用例→兜底)
_CLASSIFY_ORDER_KEYS = "classify_order"

#: 非兜底表型必须携带至少一个分类签名(校验器用)
_KINDS_WITH_SIGNATURE = (
    "capability_table", "use_case_table", "interface_table",
    "value_domain_table", "qualification_table", "trace_table",
)

_PATTERN_CACHE: dict[tuple[str, int], re.Pattern[str]] = {}
_PACK_CACHE: dict[str, RulePack] = {}

#: 模块级默认pack(惰性; set_default_rulepack切换场景用, 见verifier.py)
_DEFAULT_PACK: RulePack | None = None


def compile_pattern(pattern: str, flags: int = 0) -> re.Pattern[str]:
    """编译一个正则模板(按(pattern, flags)缓存, 跨专家共享)."""
    key = (pattern, flags)
    compiled = _PATTERN_CACHE.get(key)
    if compiled is None:
        compiled = re.compile(pattern, flags)
        _PATTERN_CACHE[key] = compiled
    return compiled


@dataclass(frozen=True)
class Template:
    """一个正则模板(带命名组), 模式字符串逐字迁移自专家源码."""

    name: str
    pattern: str
    flags: int = 0

    def compile(self) -> re.Pattern[str]:
        return compile_pattern(self.pattern, self.flags)


@dataclass(frozen=True)
class SignatureSpec:
    """一个表型分类签名——在场条件全部成立才命中.

    all_headers: 每个列名都是规范化表头集合的精确成员;
    any_header_groups: 每组内至少一个列名在表头集合中;
    any_header_substring_groups: 每组内至少有一个表头包含组内某子串;
    caption_contains_any: 表标题含任一子串;
    raw_contains_any: 原始表格文本含任一子串;
    raw_regex: 原始表格文本命中正则。
    """

    all_headers: tuple[str, ...] = ()
    any_header_groups: tuple[tuple[str, ...], ...] = ()
    any_header_substring_groups: tuple[tuple[str, ...], ...] = ()
    caption_contains_any: tuple[str, ...] = ()
    raw_contains_any: tuple[str, ...] = ()
    raw_regex: str = ""

    def match(self, header_set: frozenset[str], headers: list[str],
              caption: str, raw_text: str) -> bool:
        if not all(header in header_set for header in self.all_headers):
            return False
        for group in self.any_header_groups:
            if not any(header in header_set for header in group):
                return False
        for group in self.any_header_substring_groups:
            if not any(
                    substring in header
                    for header in headers for substring in group):
                return False
        if self.caption_contains_any and not any(
                substring in caption for substring in self.caption_contains_any):
            return False
        if self.raw_contains_any and not any(
                substring in raw_text for substring in self.raw_contains_any):
            return False
        if self.raw_regex and not compile_pattern(
                self.raw_regex).search(raw_text):
            return False
        return True


@dataclass(frozen=True)
class UseCaseFields:
    """用例表(行式schema)的字段模式与列语义映射."""

    name_pattern: str
    actors_pattern: str
    field_pattern: str
    flow_header_pattern: str
    subheader_pattern: str
    field_canon: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TableSchemaSpec:
    """一种表型的完整签名+列语义配置."""

    kind: str
    signatures: tuple[SignatureSpec, ...] = ()
    canon_map: dict[str, str] = field(default_factory=dict)
    key_columns: tuple[str, ...] = ()
    column_profiles: dict[str, tuple[str, ...]] = field(default_factory=dict)
    direction_first_column_prefix: str = ""
    direction_markers: tuple[str, ...] = ()
    trace_key_columns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    columns: tuple[str, ...] = ()
    flow_subcolumns: tuple[str, ...] = ()
    use_case_fields: UseCaseFields | None = None

    def profile(self, claim_type: str) -> tuple[str, ...]:
        return (
            self.column_profiles.get(claim_type)
            or self.column_profiles.get("default")
            or ()
        )


@dataclass(frozen=True)
class RulePack:
    """一份完整的规则包: 专家引擎的全部域知识配置."""

    pack_id: str
    table_schemas: dict[str, TableSchemaSpec]
    extraction_templates: dict[str, Template]
    term_vocabularies: dict[str, tuple[str, ...]]
    join_params: dict[str, dict[str, object]]
    thresholds: dict[str, float]
    gjb_rule_library_path: str
    classify_order: tuple[str, ...] = ()
    description: str = ""
    gjb_rule_clusters: tuple[tuple[str, tuple[str, ...], str], ...] = ()

    # ── 访问器(缺键时报可读错误, 不静默) ─────────────────────
    def template(self, name: str) -> re.Pattern[str]:
        try:
            return self.extraction_templates[name].compile()
        except KeyError:
            raise KeyError(
                f"rulepack {self.pack_id!r} 缺模板 {name!r}"
                f"(可用: {sorted(self.extraction_templates)})") from None

    def vocabulary(self, name: str) -> tuple[str, ...]:
        try:
            return self.term_vocabularies[name]
        except KeyError:
            raise KeyError(
                f"rulepack {self.pack_id!r} 缺词表 {name!r}"
                f"(可用: {sorted(self.term_vocabularies)})") from None

    def vocabulary_regex(self, name: str) -> re.Pattern[str]:
        """平铺交替正则: 与源码re.compile("A|B|C")词表逐字等价."""
        words = self.vocabulary(name)
        return compile_pattern("|".join(re.escape(word) for word in words))

    def join_param(self, expert: str, key: str,
                   default: object = None) -> object:
        return self.join_params.get(expert, {}).get(key, default)

    def threshold(self, key: str, default: float | None = None) -> float:
        value = self.thresholds.get(key, default)
        if value is None:
            raise KeyError(
                f"rulepack {self.pack_id!r} 缺阈值 {key!r}且无默认值"
                f"(可用: {sorted(self.thresholds)})")
        return value

    def table_spec(self, kind: str) -> TableSchemaSpec:
        try:
            return self.table_schemas[kind]
        except KeyError:
            raise KeyError(
                f"rulepack {self.pack_id!r} 缺表型 {kind!r}"
                f"(可用: {sorted(self.table_schemas)})") from None

    def classify_table(self, header_set: frozenset[str], headers: list[str],
                       caption: str, raw_text: str) -> str:
        """按classify_order对表头/原始文本执行签名判定, 返回首个命中的表型."""
        for kind in self.classify_order:
            spec = self.table_schemas.get(kind)
            if spec is None:
                continue
            if any(signature.match(header_set, headers, caption, raw_text)
                   for signature in spec.signatures):
                return kind
        return "generic_table"


# ── 装载与校验 ────────────────────────────────────────────


def _expect(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def _load_signature(raw: object, where: str) -> SignatureSpec:
    _expect(isinstance(raw, dict), f"{where}: 签名必须是对象")
    allowed = {
        "all_headers", "any_header_groups", "any_header_substring_groups",
        "caption_contains_any", "raw_contains_any", "raw_regex",
    }
    unknown = set(raw) - allowed
    _expect(not unknown, f"{where}: 签名含未知字段{sorted(unknown)}")
    groups: list[tuple[str, ...]] = []
    for group in raw.get("any_header_groups", []):
        _expect(isinstance(group, list) and group
                and all(isinstance(h, str) and h for h in group),
                f"{where}: any_header_groups组须为非空字符串列表")
        groups.append(tuple(group))
    sub_groups: list[tuple[str, ...]] = []
    for group in raw.get("any_header_substring_groups", []):
        _expect(isinstance(group, list) and group
                and all(isinstance(s, str) and s for s in group),
                f"{where}: any_header_substring_groups组须为非空字符串列表")
        sub_groups.append(tuple(group))
    all_headers = raw.get("all_headers", [])
    _expect(isinstance(all_headers, list)
            and all(isinstance(h, str) and h for h in all_headers),
            f"{where}: all_headers须为非空字符串列表")
    caption_any = raw.get("caption_contains_any", [])
    _expect(isinstance(caption_any, list)
            and all(isinstance(s, str) and s for s in caption_any),
            f"{where}: caption_contains_any须为非空字符串列表")
    raw_any = raw.get("raw_contains_any", [])
    _expect(isinstance(raw_any, list)
            and all(isinstance(s, str) and s for s in raw_any),
            f"{where}: raw_contains_any须为非空字符串列表")
    raw_regex = raw.get("raw_regex", "")
    _expect(isinstance(raw_regex, str), f"{where}: raw_regex须为字符串")
    if raw_regex:
        try:
            compile_pattern(raw_regex)
        except re.error as error:
            raise ValueError(
                f"{where}: raw_regex编译失败: {error}") from error
    return SignatureSpec(
        all_headers=tuple(all_headers),
        any_header_groups=tuple(groups),
        any_header_substring_groups=tuple(sub_groups),
        caption_contains_any=tuple(caption_any),
        raw_contains_any=tuple(raw_any),
        raw_regex=raw_regex,
    )


def _load_use_case_fields(raw: object, where: str) -> UseCaseFields:
    _expect(isinstance(raw, dict), f"{where}: use_case_fields须为对象")
    patterns: dict[str, str] = {}
    for key in ("name_pattern", "actors_pattern", "field_pattern",
                "flow_header_pattern", "subheader_pattern"):
        value = raw.get(key)
        _expect(isinstance(value, str) and value,
                f"{where}: use_case_fields.{key}缺失或为空")
        try:
            compile_pattern(value)
        except re.error as error:
            raise ValueError(
                f"{where}: use_case_fields.{key}编译失败: {error}") from error
        patterns[key] = value
    canon = raw.get("field_canon", {})
    _expect(isinstance(canon, dict)
            and all(isinstance(k, str) and isinstance(v, str)
                    for k, v in canon.items()),
            f"{where}: field_canon须为字符串映射")
    return UseCaseFields(
        name_pattern=patterns["name_pattern"],
        actors_pattern=patterns["actors_pattern"],
        field_pattern=patterns["field_pattern"],
        flow_header_pattern=patterns["flow_header_pattern"],
        subheader_pattern=patterns["subheader_pattern"],
        field_canon=dict(canon),
    )


def _load_table_schema(kind: str, raw: object) -> TableSchemaSpec:
    where = f"table_schemas.{kind}"
    _expect(isinstance(raw, dict), f"{where}: 表型配置须为对象")
    signatures = tuple(
        _load_signature(item, f"{where}.signatures[{index}]")
        for index, item in enumerate(raw.get("signatures", [])))
    if kind in _KINDS_WITH_SIGNATURE:
        _expect(signatures, f"{where}: 非兜底表型的表头签名不能为空")
    canon_map = raw.get("canon_map", {})
    _expect(isinstance(canon_map, dict)
            and all(isinstance(k, str) and isinstance(v, str) and k and v
                    for k, v in canon_map.items()),
            f"{where}: canon_map须为非空字符串映射")
    key_columns = raw.get("key_columns", [])
    _expect(isinstance(key_columns, list)
            and all(isinstance(c, str) for c in key_columns),
            f"{where}: key_columns须为字符串列表")
    profiles_raw = raw.get("column_profiles", {})
    _expect(isinstance(profiles_raw, dict), f"{where}: column_profiles须为对象")
    profiles: dict[str, tuple[str, ...]] = {}
    for claim_type, columns in profiles_raw.items():
        _expect(isinstance(columns, list) and columns
                and all(isinstance(c, str) for c in columns),
                f"{where}: column_profiles.{claim_type}须为非空字符串列表")
        profiles[claim_type] = tuple(columns)
    trace_keys_raw = raw.get("trace_key_columns", {})
    _expect(isinstance(trace_keys_raw, dict), f"{where}: trace_key_columns须为对象")
    trace_keys: dict[str, tuple[str, ...]] = {}
    for direction, columns in trace_keys_raw.items():
        _expect(isinstance(columns, list)
                and all(isinstance(c, str) for c in columns),
                f"{where}: trace_key_columns.{direction}须为字符串列表")
        trace_keys[direction] = tuple(columns)
    columns = raw.get("columns", [])
    _expect(isinstance(columns, list)
            and all(isinstance(c, str) for c in columns),
            f"{where}: columns须为字符串列表")
    flow_subcolumns = raw.get("flow_subcolumns", [])
    _expect(isinstance(flow_subcolumns, list)
            and all(isinstance(c, str) for c in flow_subcolumns),
            f"{where}: flow_subcolumns须为字符串列表")
    use_case_fields = None
    if "use_case_fields" in raw:
        use_case_fields = _load_use_case_fields(
            raw["use_case_fields"], where)
    prefix = raw.get("direction_first_column_prefix", "")
    _expect(isinstance(prefix, str), f"{where}: direction_first_column_prefix须为字符串")
    markers = raw.get("direction_markers", [])
    _expect(isinstance(markers, list) and all(isinstance(m, str) for m in markers),
            f"{where}: direction_markers须为字符串列表")
    if kind == "trace_table":
        # 方向判定是trace join的必要配置: 缺失/不完整直接拒绝加载,
        # 不做静默回退(空前缀会让startswith恒真→方向全部误判forward)
        _expect(prefix, f"{where}: 追踪表须声明direction_first_column_prefix")
        _expect(len(markers) == 2,
                f"{where}: direction_markers须为[正向标记, 逆向标记]两个元素")
        _expect(set(trace_keys) == {"forward", "reverse"},
                f"{where}: trace_key_columns须同时声明forward与reverse键列")
    return TableSchemaSpec(
        kind=kind, signatures=signatures,
        canon_map=dict(canon_map), key_columns=tuple(key_columns),
        column_profiles=profiles,
        direction_first_column_prefix=prefix,
        direction_markers=tuple(markers),
        trace_key_columns=trace_keys,
        columns=tuple(columns), flow_subcolumns=tuple(flow_subcolumns),
        use_case_fields=use_case_fields,
    )


def _load_gjb_section(raw: object, where: str
                      ) -> tuple[tuple[str, tuple[str, ...], str], ...]:
    """可选gjb段: 规则簇映射(cluster, rule_ids, 映射理由)."""
    _expect(isinstance(raw, dict), f"{where}: gjb段须为对象")
    unknown = set(raw) - {"rule_clusters"}
    _expect(not unknown, f"{where}: gjb段含未知字段{sorted(unknown)}")
    entries_raw = raw.get("rule_clusters", [])
    _expect(isinstance(entries_raw, list),
            f"{where}: gjb.rule_clusters须为列表")
    entries: list[tuple[str, tuple[str, ...], str]] = []
    seen: set[str] = set()
    for index, item in enumerate(entries_raw):
        item_where = f"{where}.rule_clusters[{index}]"
        _expect(isinstance(item, dict), f"{item_where}: 簇映射须为对象")
        unknown = set(item) - {"cluster", "rule_ids", "reason"}
        _expect(not unknown, f"{item_where}: 簇映射含未知字段{sorted(unknown)}")
        cluster = item.get("cluster")
        _expect(isinstance(cluster, str) and cluster,
                f"{item_where}: cluster缺失或为空")
        _expect(re.fullmatch(r"GJB-\d+", cluster) is not None,
                f"{item_where}: cluster须为GJB-XX形态, got {cluster!r}")
        _expect(cluster not in seen,
                f"{item_where}: 簇{cluster!r}重复声明")
        seen.add(cluster)
        rule_ids = item.get("rule_ids")
        _expect(isinstance(rule_ids, list) and rule_ids
                and all(isinstance(rule_id, str) and rule_id
                        for rule_id in rule_ids),
                f"{item_where}: rule_ids须为非空字符串列表")
        _expect(len(set(rule_ids)) == len(rule_ids),
                f"{item_where}: rule_ids含重复规则号")
        reason = item.get("reason")
        _expect(isinstance(reason, str) and reason.strip(),
                f"{item_where}: 映射理由reason缺失或为空")
        entries.append((cluster, tuple(rule_ids), reason))
    return tuple(entries)


def _load_rulepack_data(path: Path) -> RulePack:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"rulepack {path}: JSON解析失败: {error}") from error
    _expect(isinstance(data, dict), f"rulepack {path}: 顶层须为对象")
    pack_id = data.get("pack_id")
    _expect(isinstance(pack_id, str) and pack_id,
            f"rulepack {path}: pack_id缺失或为空")
    where = f"rulepack {pack_id!r}"

    gjb_path = data.get("gjb_rule_library_path")
    _expect(isinstance(gjb_path, str) and gjb_path,
            f"{where}: gjb_rule_library_path缺失或为空")
    _expect((BASE / gjb_path).exists(),
            f"{where}: gjb_rule_library_path指向不存在的文件: {gjb_path}")

    schemas_raw = data.get("table_schemas")
    _expect(isinstance(schemas_raw, dict) and schemas_raw,
            f"{where}: table_schemas缺失或为空")
    schemas = {kind: _load_table_schema(kind, raw)
               for kind, raw in schemas_raw.items()}
    _expect("generic_table" in schemas, f"{where}: 缺兜底表型generic_table")

    order_raw = data.get(_CLASSIFY_ORDER_KEYS,
                         ["capability_table", "interface_table",
                          "value_domain_table", "qualification_table",
                          "trace_table", "use_case_table", "generic_table"])
    _expect(isinstance(order_raw, list) and order_raw
            and all(isinstance(k, str) for k in order_raw),
            f"{where}: classify_order须为非空字符串列表")
    missing = [kind for kind in order_raw if kind not in schemas]
    _expect(not missing, f"{where}: classify_order引用未定义表型{missing}")
    _expect(set(order_raw) == set(schemas),
            f"{where}: classify_order须覆盖全部表型"
            f"(缺{sorted(set(schemas) - set(order_raw))})")

    templates_raw = data.get("extraction_templates")
    _expect(isinstance(templates_raw, dict),
            f"{where}: extraction_templates须为对象")
    templates: dict[str, Template] = {}
    for name, item in templates_raw.items():
        _expect(isinstance(item, dict), f"{where}: 模板{name!r}须为对象")
        pattern = item.get("pattern")
        _expect(isinstance(pattern, str) and pattern,
                f"{where}: 模板{name!r}缺pattern")
        flags = item.get("flags", 0)
        _expect(isinstance(flags, int), f"{where}: 模板{name!r}flags须为整数")
        try:
            compile_pattern(pattern, flags)
        except re.error as error:
            raise ValueError(
                f"{where}: 模板{name!r}正则编译失败: {error}") from error
        templates[name] = Template(name=name, pattern=pattern, flags=flags)

    vocabs_raw = data.get("term_vocabularies")
    _expect(isinstance(vocabs_raw, dict), f"{where}: term_vocabularies须为对象")
    vocabs: dict[str, tuple[str, ...]] = {}
    for name, words in vocabs_raw.items():
        _expect(isinstance(words, list) and words
                and all(isinstance(w, str) and w for w in words),
                f"{where}: 词表{name!r}须为非空字符串列表")
        vocabs[name] = tuple(words)

    join_raw = data.get("join_params")
    _expect(isinstance(join_raw, dict), f"{where}: join_params须为对象")
    for expert, params in join_raw.items():
        _expect(isinstance(params, dict),
                f"{where}: join_params.{expert}须为对象")

    thresholds_raw = data.get("thresholds")
    _expect(isinstance(thresholds_raw, dict), f"{where}: thresholds须为对象")
    thresholds: dict[str, float] = {}
    for name, value in thresholds_raw.items():
        _expect(isinstance(value, (int, float)) and not isinstance(value, bool)
                and 0.0 <= float(value) <= 1.0,
                f"{where}: 阈值{name!r}={value!r}须为[0,1]内的数")
        thresholds[name] = float(value)

    description = data.get("description", "")
    _expect(isinstance(description, str), f"{where}: description须为字符串")

    gjb_section = data.get("gjb")
    _expect(gjb_section is None or isinstance(gjb_section, dict),
            f"{where}: gjb须为对象")
    gjb_clusters = (_load_gjb_section(gjb_section, f"{where}.gjb")
                    if gjb_section is not None else ())

    return RulePack(
        pack_id=pack_id, table_schemas=schemas,
        extraction_templates=templates, term_vocabularies=vocabs,
        join_params={k: dict(v) for k, v in join_raw.items()},
        thresholds=thresholds, gjb_rule_library_path=gjb_path,
        classify_order=tuple(order_raw), description=description,
        gjb_rule_clusters=gjb_clusters,
    )


def load_rulepack(path: str | Path) -> RulePack:
    """加载并校验一份rule pack(按解析路径缓存; 校验失败报可读ValueError)."""
    resolved = Path(path).resolve()
    key = str(resolved)
    cached = _PACK_CACHE.get(key)
    if cached is not None:
        return cached
    if not resolved.exists():
        raise FileNotFoundError(f"rulepack文件不存在: {resolved}")
    pack = _load_rulepack_data(resolved)
    _PACK_CACHE[key] = pack
    return pack


def default_rulepack() -> RulePack:
    """惰性加载默认srs_gjb_v1规则包(首次调用时读文件, import期零I/O)."""
    global _DEFAULT_PACK
    if _DEFAULT_PACK is None:
        _DEFAULT_PACK = load_rulepack(DEFAULT_PACK_PATH)
    return _DEFAULT_PACK


def set_default_rulepack(pack: RulePack) -> None:
    """切换全局默认规则包(与ner_lexicon.set_default_lexicon对称).

    引擎侧的派生配置缓存按pack身份失效重建(场景切换真实生效);
    一般只在场景迁移/演示时使用.
    """
    global _DEFAULT_PACK
    _DEFAULT_PACK = pack


__all__ = [
    "DEFAULT_PACK_PATH",
    "RulePack",
    "SignatureSpec",
    "TableSchemaSpec",
    "Template",
    "UseCaseFields",
    "compile_pattern",
    "default_rulepack",
    "load_rulepack",
    "set_default_rulepack",
]
