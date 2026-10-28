"""Tests for the L1 rule pack layer (algorithms/consistency/rulepack.py).

设计(docs/srs_project/64_rulepack_design.md): 专家域知识从硬编码迁出到
声明式JSON rule pack, 引擎从配置执行。测试覆盖:
- 默认pack加载/校验/访问器(模板编译缓存, 词表两种消费形态);
- 校验器可读报错(坏正则/越界阈值/空签名/未知字段/坏JSON);
- doc06_v1跨场景pack演示: 同一evidence_compiler引擎(零改动)识别06号
  能力表/用例表, 追踪表头变体列名规范化, ID族join范围限定。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_compiler import (  # noqa: E402
    compile_evidence,
    focus_views,
    load_content_list_evidence,
)
from algorithms.consistency.id_join_expert import extract_id_claims  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.rulepack import (  # noqa: E402
    DEFAULT_PACK_PATH,
    default_rulepack,
    load_rulepack,
)

DOC06_PACK = BASE / "config" / "rulepacks" / "doc06_v1.json"


def make_evidence(evidence_id: str, text: str,
                  source_type: str = "table") -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id,
        text=text,
        source_type=source_type,
        source_ref=SourceRef(doc_id="d", section="3.2", block_id=evidence_id),
        scope_id=f"d:{evidence_id}",
    )


# 06号表116(逆向追踪)短表头变体: "本文档名称/标识"无"的"
TRACE06_REVERSE_HTML = (
    "<table><thead><tr>"
    "<th><p><strong>本文档名称/标识</strong></p></th>"
    "<th><p><strong>本文档章节号</strong></p></th>"
    "<th><p><strong>软件研制任务书名称/标识</strong></p></th>"
    "<th><p><strong>软件研制任务书的章节号</strong></p></th>"
    "<th><p><strong>跟踪说明</strong></p></th>"
    "</tr></thead><tbody>"
    "<tr><td><p>故障库维护管理</p></td><td><p>3.4</p></td>"
    "<td><p>故障库管理</p></td><td><p>4.1.2</p></td><td></td></tr>"
    "</tbody></table>"
)

# 06号表31(能力表)形态: 表头与04号逐字相同, ID单元格分两个<p>标签
CAPABILITY06_HTML = (
    "<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th><th><p>运行状态</p></th>"
    "<th><p>对应的任务书功能/性能</p></th></tr></thead><tbody>"
    "<tr><td><p>1</p></td><td><p>故障库信息录入</p></td>"
    "<td><p>PZXQ-YXZCFW-GN-GZYJXF-GZKWHGL</p><p>-GZKXXLR</p></td>"
    "<td><p>支持用户向故障库录入故障信息</p></td><td><p>新增</p></td>"
    "<td><p>桌面</p></td><td><p>开发阶段、运行阶段</p></td>"
    "<td><p>4.1.2 a)</p></td></tr></tbody></table>"
)


# ── 默认pack加载与访问器 ──────────────────────────────────


def test_default_pack_loads_and_validates() -> None:
    pack = default_rulepack()
    assert pack.pack_id == "srs_gjb_v1"
    assert pack.extraction_templates
    assert pack.term_vocabularies
    assert pack.thresholds["seq_pair_det"] == 0.28
    assert pack.thresholds["seq_pair_bge"] == 0.60
    assert pack.thresholds["e1_conf_keyword"] == 0.75
    assert set(pack.classify_order) == set(pack.table_schemas)
    assert pack.classify_order[0] == "capability_table"
    assert pack.gjb_rule_library_path == "knowledge/gjb_438c_rules_full.json"
    assert (BASE / pack.gjb_rule_library_path).exists()
    # 按路径缓存: 同一路径返回同一对象(惰性默认pack, import期零I/O)
    assert default_rulepack() is pack
    assert load_rulepack(DEFAULT_PACK_PATH) is pack


def test_templates_compile_and_carry_source_semantics() -> None:
    pack = default_rulepack()
    parse = pack.template("e1_entry_parse")
    match = parse.search("异常流E1：系统提示连接失败，用例结束。")
    assert match is not None
    assert match.group("id") == "E1"
    assert match.group("prompt") == "连接失败"
    assert match.group("ending") == "用例结束。"
    # 编译缓存: 同一pattern对象复用
    assert pack.template("e1_entry_parse") is parse
    # 词表正则形态: 平铺交替与源码re.compile("A|B|C")逐字等价
    generic = pack.vocabulary_regex("e1_generic_words")
    assert generic.pattern == (
        "系统|用户|提示|失败|错误|信息|无法|不能|异常|用例|结束|终止|中止"
        "|流程|操作|并且")
    assert generic.sub("", "系统提示连接失败") == "连接"
    # 词表元组形态(成员判定)
    assert "平板" in pack.vocabulary("enum_terminal_bases")


def test_missing_pack_keys_raise_readable_errors() -> None:
    pack = default_rulepack()
    with pytest.raises(KeyError, match="缺模板"):
        pack.template("no_such_template")
    with pytest.raises(KeyError, match="缺词表"):
        pack.vocabulary("no_such_vocab")
    with pytest.raises(KeyError, match="缺阈值"):
        pack.threshold("no_such_threshold")
    with pytest.raises(KeyError, match="缺表型"):
        pack.table_spec("no_such_kind")


# ── 校验器可读报错 ────────────────────────────────────────


def _dump_bad_pack(tmp_path: Path, mutate: dict) -> Path:
    data = json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))
    for key, value in mutate.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    path = tmp_path / "bad_pack.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_loader_rejects_bad_regex(tmp_path: Path) -> None:
    path = _dump_bad_pack(tmp_path, {
        "extraction_templates": {"e1_entry_head": {"pattern": "(unclosed["}},
    })
    with pytest.raises(ValueError, match="正则编译失败"):
        load_rulepack(path)


def test_loader_rejects_out_of_range_threshold(tmp_path: Path) -> None:
    path = _dump_bad_pack(tmp_path, {"thresholds": {"seq_pair_det": 1.5}})
    with pytest.raises(ValueError, match="seq_pair_det"):
        load_rulepack(path)


def test_loader_rejects_empty_signature(tmp_path: Path) -> None:
    schemas = json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))[
        "table_schemas"]
    schemas["capability_table"]["signatures"] = []
    path = _dump_bad_pack(tmp_path, {"table_schemas": schemas})
    with pytest.raises(ValueError, match="表头签名不能为空"):
        load_rulepack(path)


def test_loader_rejects_unknown_signature_field(tmp_path: Path) -> None:
    schemas = json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))[
        "table_schemas"]
    schemas["capability_table"]["signatures"] = [
        {"all_headers": ["x"], "bogus_field": 1}]
    path = _dump_bad_pack(tmp_path, {"table_schemas": schemas})
    with pytest.raises(ValueError, match="未知字段"):
        load_rulepack(path)


def test_loader_rejects_missing_pack_id(tmp_path: Path) -> None:
    path = _dump_bad_pack(tmp_path, {"pack_id": None})
    with pytest.raises(ValueError, match="pack_id"):
        load_rulepack(path)


def test_loader_rejects_broken_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON解析失败"):
        load_rulepack(path)


def test_loader_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_rulepack(tmp_path / "nope.json")


def test_loader_requires_trace_direction_config(tmp_path: Path) -> None:
    """追踪表方向判定配置不完整→拒绝加载(不静默回退)."""
    schemas = json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))[
        "table_schemas"]
    schemas["trace_table"].pop("direction_markers")
    path = _dump_bad_pack(tmp_path, {"table_schemas": schemas})
    with pytest.raises(ValueError, match="direction_markers须为"):
        load_rulepack(path)

    schemas = json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))[
        "table_schemas"]
    schemas["trace_table"]["direction_first_column_prefix"] = ""
    path = _dump_bad_pack(tmp_path, {"table_schemas": schemas})
    with pytest.raises(ValueError, match="direction_first_column_prefix"):
        load_rulepack(path)


# ── doc06_v1跨场景pack演示(同一引擎零改动) ─────────────────


def test_doc06_pack_recognizes_capability_and_trace_variants() -> None:
    pack06 = load_rulepack(DOC06_PACK)
    assert pack06.pack_id == "doc06_v1"
    evidence = (
        make_evidence("ev-cap06", CAPABILITY06_HTML),
        make_evidence("ev-tr06", TRACE06_REVERSE_HTML),
    )
    schema06 = compile_evidence(evidence, rulepack=pack06)
    counts = schema06.kind_counts()
    assert counts == {"capability_table": 1, "trace_table": 1}

    # 能力表: ID单元格分两个<p>标签→引擎去标签拼接为完整ID
    capability = schema06.tables_of_kind("capability_table")[0]
    row = next(r for r in capability.rows if r.key == "故障库信息录入")
    assert ("项目唯一标识符", "PZXQ-YXZCFW-GN-GZYJXF-GZKWHGL-GZKXXLR") in row.cells
    assert ("方式名称", "桌面") in row.cells
    assert "对应任务书" in capability.columns

    # 追踪表头变体: doc06 pack把"本文档名称/标识"(无"的")规范化;
    # 默认pack不认识该变体(可观察的配置差异), 方向判定不受影响
    trace06 = schema06.tables_of_kind("trace_table")[0]
    assert trace06.direction == "reverse"
    assert "本文档名称标识" in trace06.columns
    schema_default = compile_evidence(evidence)
    trace_default = schema_default.tables_of_kind("trace_table")[0]
    assert trace_default.direction == "reverse"
    assert "本文档名称/标识" in trace_default.columns
    assert "本文档名称标识" not in trace_default.columns


def test_doc06_pack_compiles_real_document_tables() -> None:
    """同一compile_evidence引擎(零改动)用doc06_v1编译06号真实content_list:
    能力表22张/用例表53张/追踪表2张全部识别, 聚焦列画像命中。"""
    pack06 = load_rulepack(DOC06_PACK)
    evidence = load_content_list_evidence("06*")
    schema = compile_evidence(evidence, rulepack=pack06)
    counts = schema.kind_counts()
    assert counts["capability_table"] == 22
    assert counts["use_case_table"] == 53
    assert counts["trace_table"] == 2
    assert counts["value_domain_table"] == 8

    capability = next(
        t for t in schema.tables_of_kind("capability_table")
        if any(r.key == "故障库信息录入" for r in t.rows))
    row = next(r for r in capability.rows if r.key == "故障库信息录入")
    assert ("项目唯一标识符", "PZXQ-YXZCFW-GN-GZYJXF-GZKWHGL-GZKXXLR") in row.cells
    assert ("方式名称", "桌面") in row.cells

    use_case = next(
        t for t in schema.tables_of_kind("use_case_table")
        if any(r.key == "CPU占用信息" for r in t.rows))
    assert {"Use Case名称", "Actors", "概述", "前置条件",
            "主事件流", "异常流E1", "后置条件"} <= {r.field for r in use_case.rows}

    directions = sorted(
        t.direction for t in schema.tables_of_kind("trace_table"))
    assert directions == ["forward", "reverse"]


def test_doc06_pack_scopes_id_join_to_declared_family() -> None:
    """ID族PZXQ-YXZCFW: doc06 pack限定join范围, 默认pack不过滤(04行为)。"""
    pack06 = load_rulepack(DOC06_PACK)
    answer06 = "故障库信息录入的项目唯一标识符为PZXQ-YXZCFW-GN-GZYJXF-GZKWHGL-GZKXXLR"
    answer04 = "SQL访问功能的项目唯一标识符为PZXQ-GN-SQLFW"

    scoped = extract_id_claims(answer06, rulepack=pack06)
    assert [(c.identifier, c.subject) for c in scoped] == [
        ("PZXQ-YXZCFW-GN-GZYJXF-GZKWHGL-GZKXXLR", "故障库信息录入")]
    # 04号族ID不在doc06 pack声明范围内→不构成join声明
    assert extract_id_claims(answer04, rulepack=pack06) == []
    # 默认pack未声明族前缀→不过滤(所有PZXQ族均提取)
    default_scoped = extract_id_claims(answer04)
    assert [(c.identifier, c.subject) for c in default_scoped] == [
        ("PZXQ-GN-SQLFW", "SQL访问")]


def test_pack_default_behavior_unchanged_for_experts() -> None:
    """默认pack下专家行为与迁移前一致(行为保持铁律的抽样断言)."""
    pack = default_rulepack()
    # e1: 处置词表/通用词表形态
    assert pack.vocabulary_regex("e1_end_words").pattern == "结束|终止|中止"
    assert pack.template("e1_continue_words").pattern == (
        "继续|恢复|重试|重新(?:执行|开始|处理)")
    # id_join: 主体窗口32字符(源码实际值), 族段数2
    assert pack.join_param("id_join", "id_window") == 32
    assert pack.join_param("id_join", "family_segments") == 2
    assert pack.join_param("id_join", "id_family_prefixes") is None
    # enum_join: 错字距离1, 块隔离开启(值域词表为集合语义, 无序)
    assert pack.join_param("enum_join", "typo_distance") == 1
    assert pack.join_param("enum_join", "row_enum_block_isolated") is True
    assert set(pack.vocabulary("enum_terminal_bases")) == {"桌面", "平板", "手持"}
    # trace: 方向标记+非追踪注记(集合语义, 无序)
    assert pack.table_spec("trace_table").direction_markers == ("任务书", "本文档")
    assert set(pack.vocabulary("trace_non_track_notes")) == {
        "不追踪", "不跟踪", "不追溯"}
    # sequence: 适用性门参数
    assert pack.join_param("sequence", "parallel_item_avg_len") == 40
    assert pack.vocabulary("seq_temporal_connectors") == (
        "然后", "随后", "之后", "接着", "下一步", "紧接着", "依次", "重新")


def test_real_focused_views_route_with_doc06_pack() -> None:
    """doc06 pack下聚焦列画像命中(规范化列名与画像一致)。"""
    pack06 = load_rulepack(DOC06_PACK)
    from algorithms.consistency.answer_structure import StructuredClaim

    evidence = load_content_list_evidence("06*")
    schema = compile_evidence(evidence, rulepack=pack06)
    claim = StructuredClaim(
        text="故障库维护管理映射到任务书4.1.2章节",
        scope_hint="故障库维护管理", structure="sentence", claim_id="ac-t06")
    views = focus_views(schema, [claim], rulepack=pack06)
    trace_views = [v for v in views if v.table_kind == "trace_table"]
    assert trace_views
    for view in trace_views:
        assert set(view.columns) == {
            "任务书名称标识", "任务书章节号", "本文档名称标识",
            "本文档章节号", "跟踪说明"}
        assert any(
            column == "任务书章节号" and value == "4.1.2"
            for column, value in view.cells)


def test_gjb_rule_library_path_from_pack() -> None:
    """gjb_rule_engine的默认规则库路径从pack取(120条规则库可加载)。"""
    from algorithms.consistency.gjb_rule_engine import load_rule_library

    rules = load_rule_library()
    assert rules
    assert all("SRS" in (rule.get("applies_to") or []) for rule in rules)
    assert len(load_rule_library()) == len(rules)  # 路径缓存生效


def test_import_has_no_module_level_io() -> None:
    """模块顶层零I/O: import rulepack不触发文件读取(默认pack惰性加载)."""
    import subprocess

    code = (
        "import sys;"
        "sys.path.insert(0, r'%s');"
        "import algorithms.consistency.rulepack as rp;"
        "assert rp._PACK_CACHE == {}, 'pack cache must start empty';"
        "rp.default_rulepack();"
        "assert rp._PACK_CACHE, 'lazy load fills the cache'"
    ) % str(BASE)
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        env={"PYTHONUTF8": "1", "PYTHONPATH": str(BASE)}, timeout=60)
    assert result.returncode == 0, result.stderr


def test_signature_spec_matching_semantics() -> None:
    """SignatureSpec在场条件: 全部成立才命中, 顺序判定取首个命中表型。"""
    pack = default_rulepack()
    headers = ["序号", "Use case名称", "项目唯一标识符", "需求描述",
               "需求重用", "方式名称", "运行状态", "对应的任务书功能/性能"]
    assert pack.classify_table(
        frozenset(headers), headers, "", "") == "capability_table"
    # 值域表需要三个条件同时成立(数据项+min/max组+精度单位组)
    vd_headers = ["序号", "数据项", "最大差", "最小差", "精度", "单位"]
    assert pack.classify_table(
        frozenset(vd_headers), vd_headers, "", "") == "value_domain_table"
    vd_partial = ["序号", "数据项", "最大差"]  # 缺精度/单位组→不命中值域
    assert pack.classify_table(
        frozenset(vd_partial), vd_partial, "", "") != "value_domain_table"
    # 追踪表: caption线索或表头子串组
    assert pack.classify_table(frozenset({"a"}), ["a"], "需求的正向追踪性",
                               "") == "trace_table"
    tr_headers = ["软件研制任务书名称/标识", "软件研制任务书的章节号",
                  "本文档的名称/标识", "本文档的章节号", "跟踪说明"]
    assert pack.classify_table(
        frozenset(tr_headers), tr_headers, "", "") == "trace_table"
    # 用例表: raw_regex或raw包含线索
    assert pack.classify_table(frozenset(), [], "", "Use Case 名称：X") == "use_case_table"
    assert re.compile(
        pack.table_schemas["use_case_table"].signatures[0].raw_regex
    ).search("Use Case 名称：查询数据")


__all__: list[str] = []
