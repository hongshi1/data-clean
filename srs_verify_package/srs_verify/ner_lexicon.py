"""Scene lexicon configuration module for the L0 gazetteer NER layer.

职责划分(配置/引擎分离, 支持跨场景迁移):

  配置(场景知识, 可替换): config/ner_lexicons/<scene>.json
      srs_scene1.json   04号场景(原entity_detector.py硬编码逐项迁移)
      doc06_scene.json  06号场景(跨场景迁移演示)
  引擎(通用逻辑): srs_verify/entity_detector.py
      消费NerLexicon/NerPatterns, 自身只保留GJB结构通用规则.

业界链路(jieba复用): configure_jieba把配置的domain_terms/值域词/实体
类别词自动add_word(freq调高到2000), 词典匹配+正则+值域闭集 = 无标注域
的标准gazetteer NER. tokenize()提供确定性分词(HMM=False, 排除jieba
隐马模型的不确定性来源), 中文连续段切分由jieba承接.

模块顶层零I/O: JSON只在load_lexicon()调用时读取; jieba惰性导入,
首次分词/加词时才构建词典(~1s), 测试fixture可用configure_jieba预热.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

BASE = Path(__file__).resolve().parent
LEXICON_DIR = BASE / "configs/ner_lexicons"
DEFAULT_SCENE_FILE = LEXICON_DIR / "srs_scene1.json"

#: add_word频率: 高于常规词频, 保证gazetteer词条不被切散
JIEBA_TERM_FREQ = 2000

#: 只对『运行状态』值域做引擎侧消费(status词匹配/方式名称过滤);
#: 其余键(如方式名称)作为闭集知识供jieba词典与上层闭集校验.
STATUS_DOMAIN_KEY = "运行状态"
#: 只对『数据库名』类别做引擎侧证据扫描; 词干约定见_database_pattern.
DATABASE_CATEGORY_KEY = "数据库名"

_LIST_FIELDS = ("domain_terms", "id_patterns", "quote_patterns", "stopwords",
                "alias_patterns", "definition_patterns", "usecase_verbs",
                "usecase_objects", "usecase_fields", "strip_prefix_words")
_DICT_FIELDS = ("value_domains", "entity_categories")
_REGEX_FIELDS = ("id_patterns", "quote_patterns", "alias_patterns",
                 "definition_patterns")
_REQUIRED_FIELDS = _LIST_FIELDS + _DICT_FIELDS + ("scene",)

#: 值域/实体类别dict字段的JSON Schema类型描述(供ner_lexicon_json_schema)
_DICT_ITEM_SCHEMA = {
    "type": "object", "additionalProperties":
        {"type": "array", "items": {"type": "string", "minLength": 1}},
}


@dataclass(frozen=True)
class NerLexicon:
    """One scene's gazetteer knowledge, loaded from a JSON config file.

    所有字段都是"场景知识": 换一份JSON即切换场景, 引擎代码不动.
    """

    scene: str
    """场景标识(唯一, 如 srs_scene1 / doc06_scene)."""

    domain_terms: tuple[str, ...]
    """域术语表(BLOB/SQL/.../CPU): 驱动域词/混合词正则+jieba add_word."""

    id_patterns: tuple[str, ...]
    """标识符正则(如 PZXQ-[A-Z0-9-]+); id_patterns[0]为标识语句主模式."""

    quote_patterns: tuple[str, ...]
    """引号术语模式; 每个模式须含group1=引号内文本."""

    value_domains: dict[str, tuple[str, ...]]
    """值域闭集{字段名:取值...}; 『运行状态』键供引擎, 其余供jieba/闭集."""

    entity_categories: dict[str, tuple[str, ...]]
    """实体类别词表{类别名:词干...}; 『数据库名』键供引擎证据扫描."""

    stopwords: tuple[str, ...]
    """中文停用词表: chinese/quoted实体过滤."""

    alias_patterns: tuple[str, ...]
    """括号别名模式(X(Y)), 2个捕获组(surface, target), 顺序保持."""

    definition_patterns: tuple[str, ...]
    """定义对模式(term(definition)), 2个捕获组, 供TERM-02检测."""

    usecase_verbs: tuple[str, ...]
    """用例动词表: 用例名判定(mention以动词结尾)."""

    usecase_objects: tuple[str, ...]
    """用例宾语表: 用例名判定(mention含宾语)."""

    usecase_fields: tuple[str, ...]
    """用例表格字段名(Use Case表的行级字段)."""

    strip_prefix_words: tuple[str, ...]
    """实体表面前缀剥离词表(提供/支持/... -> 剥离后得到实体核心)."""

    description: str = field(default="")
    """场景说明(可选, 仅文档用途)."""

    def to_dict(self) -> dict[str, Any]:
        """JSON兼容的dict形式(round-trip: load_lexicon(to_dict写出的文件))."""
        out: dict[str, Any] = {
            "scene": self.scene,
            "domain_terms": list(self.domain_terms),
            "id_patterns": list(self.id_patterns),
            "quote_patterns": list(self.quote_patterns),
            "value_domains": {k: list(v) for k, v in self.value_domains.items()},
            "entity_categories": {
                k: list(v) for k, v in self.entity_categories.items()},
            "stopwords": list(self.stopwords),
            "alias_patterns": list(self.alias_patterns),
            "definition_patterns": list(self.definition_patterns),
            "usecase_verbs": list(self.usecase_verbs),
            "usecase_objects": list(self.usecase_objects),
            "usecase_fields": list(self.usecase_fields),
            "strip_prefix_words": list(self.strip_prefix_words),
        }
        if self.description:
            out["description"] = self.description
        return out

    def cache_key(self) -> str:
        """内容指纹(sha1): 模式缓存/等价比较的键, 同名不同内容不碰撞."""
        canon = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(canon.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NerPatterns:
    """Compiled regex bundle derived from one NerLexicon (engine-ready).

    生成规则与旧entity_detector.py硬编码正则一一对应; scene1配置生成的
    pattern与旧版逐串一致(行为等价的来源).
    """

    scene: str
    lexicon: NerLexicon
    domain_terms: frozenset[str]
    stopwords: frozenset[str]
    status_tokens: tuple[str, ...]
    domain_term_re: re.Pattern[str] | None
    mixed_term_re: re.Pattern[str] | None
    id_re: re.Pattern[str]
    identifier_statement_re: re.Pattern[str]
    quote_res: tuple[re.Pattern[str], ...]
    database_re: re.Pattern[str] | None
    alias_res: tuple[re.Pattern[str], ...]
    definition_res: tuple[re.Pattern[str], ...]
    status_filter_re: re.Pattern[str] | None
    usecase_verbs: tuple[str, ...]
    usecase_objects: tuple[str, ...]
    usecase_fields: frozenset[str]
    strip_prefix_words: tuple[str, ...]


def _database_pattern(names: tuple[str, ...]) -> str | None:
    """数据库词干→扫描模式.

    词干约定(与旧版达梦/sqlite模式行为一致):
    - 含中文的词干(达梦)自动扩展 可选『数据库』后缀 + 可选V版本号;
    - 纯ASCII词干(sqlite)自动扩展数字后缀(sqlite\\d*).
    """
    if not names:
        return None
    parts: list[str] = []
    for name in names:
        if re.search(r"[\u4e00-\u9fff]", name):
            parts.append(re.escape(name) + r"(?:数据库)?\s*(?:V[\d.]+)?")
        else:
            parts.append(re.escape(name) + r"\d*")
    return "|".join(parts)


def compile_patterns(lexicon: NerLexicon) -> NerPatterns:
    """Derive the engine regex bundle from a lexicon (cached by content)."""
    key = lexicon.cache_key()
    cached = _PATTERN_CACHE.get(key)
    if cached is not None:
        return cached
    if not lexicon.id_patterns:
        raise ValueError(
            f"lexicon配置错误 {lexicon.scene!r}: 'id_patterns'为空, "
            f"无法编译标识语句模式(请走load_lexicon加载经过校验的配置)")
    domain_terms = tuple(lexicon.domain_terms)
    domain_alt = "|".join(re.escape(t) for t in domain_terms)
    domain_term_re = (re.compile(r"(?<![A-Za-z0-9])(?:" + domain_alt
                                 + r")(?![A-Za-z0-9])")
                      if domain_alt else None)
    mixed_term_re = (re.compile(r"(?:" + domain_alt + r")[\u4e00-\u9fff]{1,8}")
                     if domain_alt else None)
    id_re = re.compile("|".join(lexicon.id_patterns))
    identifier_statement_re = re.compile(
        r"^(?P<name>.+?)的项目唯一标识符[：:](?P<id>"
        + lexicon.id_patterns[0] + r")$")
    quote_res = tuple(re.compile(p) for p in lexicon.quote_patterns)
    db_pattern = _database_pattern(
        lexicon.entity_categories.get(DATABASE_CATEGORY_KEY, ()))
    database_re = (re.compile(db_pattern, re.IGNORECASE)
                   if db_pattern else None)
    alias_res = tuple(re.compile(p) for p in lexicon.alias_patterns)
    definition_res = tuple(re.compile(p) for p in lexicon.definition_patterns)
    status_tokens = tuple(lexicon.value_domains.get(STATUS_DOMAIN_KEY, ()))
    status_filter_re = (
        re.compile("(?:" + "|".join(re.escape(t) for t in status_tokens) + ")+")
        if status_tokens else None)
    patterns = NerPatterns(
        scene=lexicon.scene,
        lexicon=lexicon,
        domain_terms=frozenset(domain_terms),
        stopwords=frozenset(lexicon.stopwords),
        status_tokens=status_tokens,
        domain_term_re=domain_term_re,
        mixed_term_re=mixed_term_re,
        id_re=id_re,
        identifier_statement_re=identifier_statement_re,
        quote_res=quote_res,
        database_re=database_re,
        alias_res=alias_res,
        definition_res=definition_res,
        status_filter_re=status_filter_re,
        usecase_verbs=tuple(lexicon.usecase_verbs),
        usecase_objects=tuple(lexicon.usecase_objects),
        usecase_fields=frozenset(lexicon.usecase_fields),
        strip_prefix_words=tuple(lexicon.strip_prefix_words),
    )
    _PATTERN_CACHE[key] = patterns
    return patterns


_PATTERN_CACHE: dict[str, NerPatterns] = {}


def _field_type_error(path: Path, name: str, expected: str,
                      got: type) -> ValueError:
    return ValueError(
        f"lexicon配置错误 {path}: 字段 '{name}' 期望{expected}, "
        f"实际为 {got.__name__}")


def _validate(path: Path, raw: Any) -> dict[str, Any]:
    """Schema校验: 缺字段/类型错/未知键/坏正则 → 可读ValueError."""
    if not isinstance(raw, dict):
        raise ValueError(
            f"lexicon配置错误 {path}: 顶层期望JSON对象, "
            f"实际为 {type(raw).__name__}")
    missing = [f for f in _REQUIRED_FIELDS if f not in raw]
    if missing:
        raise ValueError(f"lexicon配置错误 {path}: 缺失字段 {missing}")
    unknown = sorted(set(raw) - set(_REQUIRED_FIELDS) - {"description"})
    if unknown:
        raise ValueError(f"lexicon配置错误 {path}: 未知字段 {unknown}")
    if not isinstance(raw["scene"], str):
        raise _field_type_error(path, "scene", "字符串", type(raw["scene"]))
    if not raw["scene"].strip():
        raise ValueError(f"lexicon配置错误 {path}: 'scene'不能为空")
    if not isinstance(raw.get("description", ""), str):
        raise _field_type_error(path, "description", "字符串",
                                type(raw["description"]))
    for name in _LIST_FIELDS:
        value = raw[name]
        if not isinstance(value, list):
            raise _field_type_error(path, name, "字符串数组", type(value))
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    f"lexicon配置错误 {path}: 字段 '{name}' 存在"
                    f"非字符串或空白项 {item!r}")
    for name in _DICT_FIELDS:
        value = raw[name]
        if not isinstance(value, dict):
            raise _field_type_error(path, name, "对象(字符串->字符串数组)",
                                    type(value))
        for key, items in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    f"lexicon配置错误 {path}: 字段 '{name}' 存在"
                    f"空白键 {key!r}")
            if not isinstance(items, list):
                raise ValueError(
                    f"lexicon配置错误 {path}: '{name}.{key}' 期望字符串数组, "
                    f"实际为 {type(items).__name__}")
            for item in items:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError(
                        f"lexicon配置错误 {path}: '{name}.{key}' 存在"
                        f"非字符串或空白项 {item!r}")
    if not raw["domain_terms"]:
        raise ValueError(
            f"lexicon配置错误 {path}: 'domain_terms'不能为空"
            f"(gazetteer场景至少需要域术语)")
    if not raw["id_patterns"]:
        raise ValueError(
            f"lexicon配置错误 {path}: 'id_patterns'不能为空"
            f"(GJB SRS场景需要需求标识符模式)")
    for name in _REGEX_FIELDS:
        for pattern in raw[name]:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"lexicon配置错误 {path}: 字段 '{name}' 的正则"
                    f"{pattern!r}无法编译: {exc}") from exc
    return raw


def load_lexicon(path: str | Path) -> NerLexicon:
    """Load and validate one scene lexicon from a JSON config file."""
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"lexicon配置文件不存在: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"lexicon配置错误 {config_path}: JSON解析失败: {exc}") from exc
    raw = _validate(config_path, raw)
    return NerLexicon(
        scene=raw["scene"],
        domain_terms=tuple(raw["domain_terms"]),
        id_patterns=tuple(raw["id_patterns"]),
        quote_patterns=tuple(raw["quote_patterns"]),
        value_domains={k: tuple(v) for k, v in raw["value_domains"].items()},
        entity_categories={
            k: tuple(v) for k, v in raw["entity_categories"].items()},
        stopwords=tuple(raw["stopwords"]),
        alias_patterns=tuple(raw["alias_patterns"]),
        definition_patterns=tuple(raw["definition_patterns"]),
        usecase_verbs=tuple(raw["usecase_verbs"]),
        usecase_objects=tuple(raw["usecase_objects"]),
        usecase_fields=tuple(raw["usecase_fields"]),
        strip_prefix_words=tuple(raw["strip_prefix_words"]),
        description=raw.get("description", ""),
    )


_DEFAULT_LEXICON: NerLexicon | None = None


def default_lexicon() -> NerLexicon:
    """模块级惰性默认场景(srs_scene1): entity_detector不注入时用它."""
    global _DEFAULT_LEXICON
    if _DEFAULT_LEXICON is None:
        _DEFAULT_LEXICON = load_lexicon(DEFAULT_SCENE_FILE)
    return _DEFAULT_LEXICON


def set_default_lexicon(lexicon: NerLexicon) -> None:
    """切换全局默认场景(一般只在演示/迁移场景时使用)."""
    global _DEFAULT_LEXICON
    _DEFAULT_LEXICON = lexicon


_JIEBA_MODULE: ModuleType | None = None
_JIEBA_CONFIGURED_SCENES: set[str] = set()


def _jieba() -> ModuleType:
    """惰性导入jieba并压低其词典构建日志(首次~1s, 只发生一次)."""
    global _JIEBA_MODULE
    if _JIEBA_MODULE is None:
        import jieba

        jieba.setLogLevel(jieba.logging.WARNING)
        _JIEBA_MODULE = jieba
    return _JIEBA_MODULE


def configure_jieba(lexicon: NerLexicon) -> None:
    """把场景词典add_word进jieba(域词+值域词+实体词, freq=2000).

    模块级标志保证每个场景只配置一次(add_word本身幂等, 标志只省重复调用).
    """
    if lexicon.scene in _JIEBA_CONFIGURED_SCENES:
        return
    jieba = _jieba()
    for term in lexicon.domain_terms:
        jieba.add_word(term, JIEBA_TERM_FREQ)
    for values in lexicon.value_domains.values():
        for value in values:
            jieba.add_word(value, JIEBA_TERM_FREQ)
    for words in lexicon.entity_categories.values():
        for word in words:
            jieba.add_word(word, JIEBA_TERM_FREQ)
    _JIEBA_CONFIGURED_SCENES.add(lexicon.scene)


def tokenize(text: str, lexicon: NerLexicon | None = None) -> list[str]:
    """确定性jieba分词(HMM=False, 排除隐马路径的不确定性风险).

    中文连续段切分由jieba承接: 场景词典已add_word的词条
    (如06号的『运行状态监控』)不会被切散——gazetteer效应.
    """
    scene_lexicon = lexicon or default_lexicon()
    configure_jieba(scene_lexicon)
    return _jieba().lcut(text, HMM=False)


def ner_lexicon_json_schema() -> dict[str, Any]:
    """JSON Schema(draft-07)形式的字段文档, 与NerLexicon双写.

    供配置文件校验(jsonschema)与文档化; 权威实现是_validate/load_lexicon.
    """
    return deepcopy(_JSON_SCHEMA)


_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NerLexicon",
    "description": "L0 gazetteer NER场景词典配置(配置/引擎分离)",
    "type": "object",
    "additionalProperties": False,
    "required": list(_REQUIRED_FIELDS),
    "properties": {
        "scene": {
            "type": "string", "minLength": 1,
            "description": "场景标识(唯一), 如 srs_scene1 / doc06_scene",
        },
        "description": {
            "type": "string",
            "description": "场景说明(可选, 仅文档用途)",
        },
        "domain_terms": {
            "type": "array", "minItems": 1,
            "items": {"type": "string", "minLength": 1},
            "description": "域术语表(BLOB/SQL/...): 域词/混合词正则+jieba"
                           "add_word; 顺序保持(较长词应在前, 避免前缀吞并)",
        },
        "id_patterns": {
            "type": "array", "minItems": 1,
            "items": {"type": "string", "minLength": 1},
            "description": "需求标识符正则; id_patterns[0]为『X的项目唯一"
                           "标识符：ID』语句解析主模式",
        },
        "quote_patterns": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "引号术语模式; 每个模式须含group1=引号内文本",
        },
        "value_domains": {
            **_DICT_ITEM_SCHEMA,
            "description": "值域闭集{字段名:[取值...]}; 『运行状态』键驱动"
                           "status词匹配与方式名称过滤, 其余供jieba/闭集校验",
        },
        "entity_categories": {
            **_DICT_ITEM_SCHEMA,
            "description": "实体类别词表{类别名:[词干...]}; 『数据库名』键驱动"
                           "证据扫描(中文词干自动扩展 数据库/V版本, ASCII词干"
                           "自动扩展数字后缀), 其余供jieba/演示",
        },
        "stopwords": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "中文停用词表: chinese/quoted实体过滤",
        },
        "alias_patterns": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "括号别名模式(X(Y)), 2个捕获组(surface, target)",
        },
        "definition_patterns": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "定义对模式(term(definition)), 2个捕获组, "
                           "供TERM-02同名异义检测",
        },
        "usecase_verbs": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "用例动词表: 用例名判定(mention以动词结尾)",
        },
        "usecase_objects": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "用例宾语表: 用例名判定(mention含宾语)",
        },
        "usecase_fields": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "用例表格字段名(Use Case表的行级字段)",
        },
        "strip_prefix_words": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "实体表面前缀剥离词表(提供/支持/...)",
        },
    },
}

__all__ = [
    "JIEBA_TERM_FREQ",
    "LEXICON_DIR",
    "NerLexicon",
    "NerPatterns",
    "compile_patterns",
    "configure_jieba",
    "default_lexicon",
    "load_lexicon",
    "ner_lexicon_json_schema",
    "set_default_lexicon",
    "tokenize",
]
