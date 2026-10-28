"""Tests for the config-driven L0 NER lexicon (ner_lexicon + scene transfer).

覆盖: 配置加载/schema校验(双写)/jieba词典/两场景抽取/digest行为锁定.
行为等价的权威锁定是 test_scene1_full_corpus_digest_lock:
91行scene1冻结QA的实体抽取+文档词典+TERM检测结果与重构前硬编码版本
逐行digest一致(tests/fixtures/scene1_l0_legacy_digests_v1.json).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_structure import decompose_answer  # noqa: E402
from algorithms.consistency.entity_detector import (  # noqa: E402
    build_document_lexicon,
    detect_term_conflicts,
    extract_entities,
)
from algorithms.consistency.evidence_statements import (  # noqa: E402
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.ner_lexicon import (  # noqa: E402
    LEXICON_DIR,
    NerLexicon,
    compile_patterns,
    configure_jieba,
    load_lexicon,
    ner_lexicon_json_schema,
    tokenize,
)
from algorithms.consistency.eval_lib import load_frozen_qa  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.demo_lexicon_transfer import l0_row_record  # noqa: E402

SCENE1 = LEXICON_DIR / "srs_scene1.json"
DOC06 = LEXICON_DIR / "doc06_scene.json"
FIXTURE = BASE / "tests/fixtures/scene1_l0_legacy_digests_v1.json"
CROSSDOC06 = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"

LEGACY_DOMAIN_TERMS = ("BLOB", "SQL", "JSON", "INT", "STRING", "FLOAT", "LOB",
                       "DML", "API")
LEGACY_STOPWORDS = (
    "的", "了", "是", "在", "和", "与", "或", "及", "等", "系统", "软件", "服务",
    "进行", "描述", "需要", "可以", "必须", "应当", "提供", "使用", "数据", "信息",
    "接口", "功能", "需求", "规格", "说明", "文档", "项目", "唯一", "标识", "名称",
    "方式", "状态", "阶段", "开发", "运行")
LEGACY_USECASE_VERBS = (
    "插入", "删除", "修改", "查询", "管理", "转换", "绑定", "输出", "获取",
    "变更", "授权", "统计", "审计", "初始化", "连接", "生成", "更新", "配置",
    "释放")
LEGACY_USECASE_OBJECTS = (
    "数据", "对象", "字典", "类型", "数组", "错误", "权限", "用户", "配置",
    "资源", "代码", "缓存", "连接", "池")
LEGACY_USECASE_FIELDS = (
    "前置条件", "后置条件", "简要说明", "参与者", "系统的动作", "Actor的动作",
    "动作约束")
LEGACY_STRIP_PREFIX_WORDS = (
    "提供", "支持", "包括", "包含", "使用", "通过", "采用", "调用", "执行",
    "触发", "发出", "对于", "如果", "例如", "以及", "系统", "软件", "服务",
    "进行", "描述", "需要", "可以", "必须", "应当", "和", "及", "或", "与")


def statement(sid: str, text: str, field_name: str = "sentence",
              scope_key: str = "") -> EvidenceStatement:
    return EvidenceStatement(
        statement_id=sid, evidence_id=sid.split("#")[0], text=text,
        field_name=field_name, scope_key=scope_key, row_index=1)


def _digest(obj) -> str:
    canon = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _write_config(tmp_path: Path, payload) -> Path:
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture(scope="session", autouse=True)
def _preheat():
    """两份场景lexicon加载+jieba词典构建预热(会话级一次, 后续测试零等待)."""
    configure_jieba(load_lexicon(SCENE1))
    configure_jieba(load_lexicon(DOC06))


# ---------------------------------------------------------------- 配置加载

def test_load_scene1_lexicon_matches_legacy_hardcoded() -> None:
    """srs_scene1配置逐项迁移自entity_detector.py v1硬编码(不增不减)."""
    lex = load_lexicon(SCENE1)
    assert lex.scene == "srs_scene1"
    assert lex.domain_terms == LEGACY_DOMAIN_TERMS
    assert lex.id_patterns == ("PZXQ-[A-Z0-9-]+",)
    assert lex.quote_patterns == ('[「"『]([^「」"『』]+)[」"』]',)
    assert lex.value_domains["运行状态"] == ("运行阶段", "开发阶段")
    assert lex.value_domains["方式名称"] == ("桌面", "平板", "手持")
    assert lex.entity_categories["数据库名"] == ("达梦", "sqlite")
    assert lex.stopwords == LEGACY_STOPWORDS
    assert lex.alias_patterns == (
        r"([\u4e00-\u9fffA-Za-z]{2,12})[（(]([A-Za-z0-9]{2,12})[）)]",
        r"([A-Za-z0-9]{1,10})[（(]([\u4e00-\u9fff]{2,10})[）)]")
    assert lex.definition_patterns == (
        r"([A-Za-z\u4e00-\u9fff]{1,12})[（(]([^（）()]{1,24})[）)]",)
    assert lex.usecase_verbs == LEGACY_USECASE_VERBS
    assert lex.usecase_objects == LEGACY_USECASE_OBJECTS
    assert lex.usecase_fields == LEGACY_USECASE_FIELDS
    assert lex.strip_prefix_words == LEGACY_STRIP_PREFIX_WORDS


def test_load_doc06_lexicon_scene_values() -> None:
    lex = load_lexicon(DOC06)
    assert lex.scene == "doc06_scene"
    assert lex.id_patterns == ("PZXQ-YXZCFW-[A-Z0-9-]+",)
    assert lex.domain_terms[:9] == LEGACY_DOMAIN_TERMS
    for extra in ("CPU", "WPS", "运行状态监控", "负载均衡", "数据库连接状态"):
        assert extra in lex.domain_terms
    assert "集成阶段" in lex.value_domains["运行状态"]
    assert lex.value_domains["方式名称"] == ("桌面", "平板", "手持")
    assert lex.entity_categories["数据库名"] == ("达梦",)
    assert "写入" in lex.usecase_verbs and "预警" in lex.usecase_verbs
    assert "日志" in lex.usecase_objects and "故障" in lex.usecase_objects
    assert "能够" in lex.strip_prefix_words


def test_lexicon_to_dict_roundtrip(tmp_path: Path) -> None:
    lex = load_lexicon(DOC06)
    path = _write_config(tmp_path, lex.to_dict())
    assert load_lexicon(path).to_dict() == lex.to_dict()


# ---------------------------------------------------------------- schema校验

def test_load_lexicon_missing_field(tmp_path: Path) -> None:
    payload = json.loads(SCENE1.read_text(encoding="utf-8"))
    del payload["stopwords"]
    with pytest.raises(ValueError, match="缺失字段.*stopwords"):
        load_lexicon(_write_config(tmp_path, payload))


def test_load_lexicon_wrong_type(tmp_path: Path) -> None:
    payload = json.loads(SCENE1.read_text(encoding="utf-8"))
    payload["domain_terms"] = "BLOB"
    with pytest.raises(ValueError, match="domain_terms.*期望字符串数组"):
        load_lexicon(_write_config(tmp_path, payload))


def test_load_lexicon_wrong_dict_value_type(tmp_path: Path) -> None:
    payload = json.loads(SCENE1.read_text(encoding="utf-8"))
    payload["value_domains"]["运行状态"] = "运行阶段"
    with pytest.raises(ValueError, match="value_domains.运行状态.*字符串数组"):
        load_lexicon(_write_config(tmp_path, payload))


def test_load_lexicon_unknown_field(tmp_path: Path) -> None:
    payload = json.loads(SCENE1.read_text(encoding="utf-8"))
    payload["extra_field"] = []
    with pytest.raises(ValueError, match="未知字段.*extra_field"):
        load_lexicon(_write_config(tmp_path, payload))


def test_load_lexicon_bad_regex(tmp_path: Path) -> None:
    payload = json.loads(SCENE1.read_text(encoding="utf-8"))
    payload["id_patterns"] = ["PZXQ-[A-Z0-9-"]  # 未闭合字符类
    with pytest.raises(ValueError, match="无法编译"):
        load_lexicon(_write_config(tmp_path, payload))


def test_load_lexicon_empty_domain_terms(tmp_path: Path) -> None:
    payload = json.loads(SCENE1.read_text(encoding="utf-8"))
    payload["domain_terms"] = []
    with pytest.raises(ValueError, match="domain_terms.*不能为空"):
        load_lexicon(_write_config(tmp_path, payload))


def test_load_lexicon_non_object_top_level(tmp_path: Path) -> None:
    path = tmp_path / "lexicon.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="顶层期望JSON对象"):
        load_lexicon(path)


def test_load_lexicon_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="不存在"):
        load_lexicon(tmp_path / "nope.json")


def test_load_lexicon_broken_json(tmp_path: Path) -> None:
    path = tmp_path / "lexicon.json"
    path.write_text("{scene", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON解析失败"):
        load_lexicon(path)


def test_json_schema_validates_both_configs() -> None:
    """JSON schema(双写)对两份正式配置文件校验通过."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = ner_lexicon_json_schema()
    for path in (SCENE1, DOC06):
        doc = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)


def test_json_schema_documents_all_fields() -> None:
    schema = ner_lexicon_json_schema()
    for name in schema["required"]:
        assert schema["properties"][name].get("description"), name


# ---------------------------------------------------------------- 模式编译

def test_scene1_patterns_reproduce_legacy_regexes() -> None:
    """srs_scene1配置编译出的模式与v1硬编码正则逐串/逐行为一致."""
    p = compile_patterns(load_lexicon(SCENE1))
    assert p.domain_term_re.pattern == (
        r"(?<![A-Za-z0-9])(?:BLOB|SQL|JSON|INT|STRING|FLOAT|LOB|DML|API)"
        r"(?![A-Za-z0-9])")
    assert p.mixed_term_re.pattern == (
        r"(?:BLOB|SQL|JSON|INT|STRING|FLOAT|LOB|DML|API)[\u4e00-\u9fff]{1,8}")
    assert p.id_re.pattern == r"PZXQ-[A-Z0-9-]+"
    assert p.identifier_statement_re.pattern == (
        r"^(?P<name>.+?)的项目唯一标识符[：:](?P<id>PZXQ-[A-Z0-9-]+)$")
    assert p.database_re.pattern == r"达梦(?:数据库)?\s*(?:V[\d.]+)?|sqlite\d*"
    assert p.database_re.flags & re.IGNORECASE
    assert p.status_filter_re.pattern == r"(?:运行阶段|开发阶段)+"
    assert p.database_re.findall("本地数据库（sqlite3）与达梦数据库V7.6") == [
        "sqlite3", "达梦数据库V7.6"]
    assert p.quote_res[0].findall("「大字段」采用『ORM』方式") == ["大字段", "ORM"]


def test_compile_patterns_cached_by_content() -> None:
    lex = load_lexicon(SCENE1)
    assert compile_patterns(lex) is compile_patterns(lex)
    modified = NerLexicon(
        scene=lex.scene, domain_terms=lex.domain_terms + ("XX",),
        id_patterns=lex.id_patterns, quote_patterns=lex.quote_patterns,
        value_domains=dict(lex.value_domains),
        entity_categories=dict(lex.entity_categories), stopwords=lex.stopwords,
        alias_patterns=lex.alias_patterns,
        definition_patterns=lex.definition_patterns,
        usecase_verbs=lex.usecase_verbs,
        usecase_objects=lex.usecase_objects,
        usecase_fields=lex.usecase_fields,
        strip_prefix_words=lex.strip_prefix_words)
    assert compile_patterns(modified) is not compile_patterns(lex)


# ---------------------------------------------------------------- jieba链路

def test_tokenize_deterministic_and_gazetteer_whole_words() -> None:
    lex06 = load_lexicon(DOC06)
    tokens = tokenize("系统运行状态监控", lex06)
    assert tokens == tokenize("系统运行状态监控", lex06)  # HMM=False: 确定性
    assert "运行状态监控" in tokens  # add_word后整词不被切散
    lex1 = load_lexicon(SCENE1)
    assert "SQL" in tokenize("BLOB数据插入SQL访问", lex1)
    assert "运行阶段" in tokenize("开发阶段、运行阶段", lex1)


def test_configure_jieba_idempotent_per_scene() -> None:
    lex = load_lexicon(DOC06)
    configure_jieba(lex)
    configure_jieba(lex)  # 模块级标志: 第二次为no-op, 不报错
    assert tokenize("负载均衡", lex) == ["负载均衡"]


# ---------------------------------------------------------------- 两场景抽取

def test_extract_entities_lexicon_injection_neutral_for_scene1() -> None:
    text = "系统通过SQL语句访问BLOB、JSON，并调用接口PZXQ-GN-SQLFW-BLOBSJCZ。"
    assert extract_entities(text, load_lexicon(SCENE1)) == extract_entities(text)


def test_extract_entities_doc06_scene() -> None:
    lex = load_lexicon(DOC06)
    text = ("系统能够读取数据库连接状态，接口PZXQ-YXZCFW-GN-XTJCXXWH-CSPZJK，"
            "CPU状态与WPS软件状态监控。")
    found = {(e.surface, e.kind) for e in extract_entities(text, lex)}
    assert ("数据库连接状态", "domain_term") in found
    assert ("CPU", "domain_term") in found
    assert ("WPS", "domain_term") in found
    assert ("PZXQ-YXZCFW-GN-XTJCXXWH-CSPZJK", "pzxq_id") in found
    scene1_found = {(e.surface, e.kind)
                    for e in extract_entities(text, load_lexicon(SCENE1))}
    assert ("数据库连接状态", "domain_term") not in scene1_found
    assert ("CPU", "domain_term") not in scene1_found


def test_build_document_lexicon_doc06_scene() -> None:
    rows = [json.loads(line) for line
            in CROSSDOC06.read_text(encoding="utf-8").splitlines()]
    request = request_from_dict(rows[0])
    statements = linearize_context(request.evidence)
    lex = build_document_lexicon(statements, load_lexicon(DOC06))
    assert "PZXQ-YXZCFW-GN-XTJCXXWH-JMJCKJCSPZ" in lex.interface_ids
    assert "界面集成框架参数配置" in lex.usecase_names
    assert {"桌面", "平板", "手持"} <= set(lex.mode_values)
    assert {"开发阶段", "运行阶段"} <= set(lex.status_values)
    all_status: set[str] = set()
    for row in rows:
        row_lex = build_document_lexicon(
            linearize_context(request_from_dict(row).evidence),
            load_lexicon(DOC06))
        all_status.update(row_lex.status_values)
    assert "集成阶段" in all_status  # 06号特有运行状态值


def test_value_domain_status_filter_is_scene_specific() -> None:
    """方式名称过滤/运行状态识别随场景值域变化(换配置的引擎可见效果)."""
    lex1 = load_lexicon(SCENE1)
    lex06 = load_lexicon(DOC06)
    mode_stmts = [statement(
        "e#s0", "X的方式名称：运行阶段、集成阶段", "方式名称", "X")]
    assert build_document_lexicon(mode_stmts, lex1).mode_values == ("集成阶段",)
    assert build_document_lexicon(mode_stmts, lex06).mode_values == ()
    status_stmts = [statement(
        "e#s0", "X的运行状态：开发阶段、集成阶段、运行阶段", "运行状态", "X")]
    assert "集成阶段" not in build_document_lexicon(status_stmts, lex1).status_values
    assert "集成阶段" in build_document_lexicon(status_stmts, lex06).status_values


def test_detect_term_conflicts_lexicon_kwarg_neutral_for_scene1() -> None:
    row = json.loads(
        (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
        .read_text(encoding="utf-8").splitlines()[0])
    request = request_from_dict(row)
    statements = linearize_context(request.evidence)
    claims = decompose_answer(request.answer, request.question)
    default = detect_term_conflicts(request, statements, claims)
    injected = detect_term_conflicts(
        request, statements, claims, load_lexicon(SCENE1))
    assert default == injected


# ---------------------------------------------------------------- 行为锁定

def test_scene1_full_corpus_digest_lock() -> None:
    """91行scene1冻结QA: L0全量结果(抽取+词典+TERM)与重构前硬编码逐行一致."""
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = load_frozen_qa()
    digests: list[str] = []
    mismatches: list[str] = []
    for row in rows:
        digest = _digest(l0_row_record(row))
        digests.append(digest)
        if digest != fixture["row_digests"][row["instance_id"]]:
            mismatches.append(row["instance_id"])
    assert not mismatches, f"行为漂移的实例: {mismatches[:5]}"
    assert _digest(digests) == fixture["global_digest"]
