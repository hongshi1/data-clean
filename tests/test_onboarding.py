"""Tests for the onboarding induction engine (algorithms/consistency/onboarding.py).

覆盖(设计见docs/srs_project/74_rule_library_construction.md§3):
- HTML表头解析: thead的th+双<p>拼接+colspan按元素计数; 无thead首行;
- 归纳函数: 表格聚类(无thead「字段：值」首行按字段名归一)/ID族(根+
  own_root标记)/值域(精确列+模糊候选)/域术语(频次+结构噪声过滤);
- 追踪表方向归纳: 上级文档/本文档标记+正逆向双观测验证;
- 草稿生成: ID模板根族改写/trace方向覆盖/gjb段逐字保留, 草稿经
  load_rulepack/load_lexicon的schema校验(写临时文件加载);
- 校验工具: 簇映射rule_ids存在性(缺口#3)/gjb段不动校验;
- 01号真实数据冒烟: 归纳非空+草稿可加载+审计跑通(11簇verdict)。
"""
from __future__ import annotations

import json
import sys
from glob import glob
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.ner_lexicon import load_lexicon  # noqa: E402
from algorithms.consistency.onboarding import (  # noqa: E402
    build_lexicon_draft,
    build_rulepack_draft,
    dominant_id_root,
    domain_term_frequencies,
    extract_table_headers,
    induce_domain_terms,
    induce_id_families,
    induce_report,
    induce_table_signatures,
    induce_trace_direction,
    induce_value_domain_candidates,
    induce_value_domains,
    own_id_prefixes,
    validate_cluster_rule_ids,
    validate_gjb_section_unchanged,
)
from algorithms.consistency.rulepack import load_rulepack  # noqa: E402


# ── fixture构造 ─────────────────────────────────────────


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def _table_block(body: str, caption: str | None = None) -> dict:
    return {
        "type": "table",
        "table_body": body,
        "table_caption": [caption] if caption else [],
    }


def _minimal_base_pack() -> dict:
    """最小可用基pack(dict形态): 表型/模板/簇映射均为真实子集."""
    return {
        "pack_id": "test_base_v1",
        "description": "测试用最小基pack",
        "gjb_rule_library_path": "knowledge/gjb_438c_rules_full.json",
        "table_schemas": {
            "capability_table": {
                "signatures": [
                    {"all_headers": ["项目唯一标识符", "需求描述"]}],
                "column_profiles": {"default": [
                    "项目唯一标识符", "需求描述", "方式名称", "运行状态"]},
            },
            "interface_table": {
                "signatures": [{"all_headers": ["发送方", "接收方"]}],
                "key_columns": ["接口需求名称", "接口需求标识"],
            },
            "qualification_table": {
                "signatures": [
                    {"any_header_groups": [["合格性方法", "合格性级别"]]}],
                "canon_map": {"需求名称/标识": "需求名称标识"},
                "column_profiles": {"default": [
                    "需求名称标识", "章节号", "合格性方法", "合格性级别"]},
            },
            "trace_table": {
                "signatures": [
                    {"caption_contains_any": ["追踪性"]},
                    {"any_header_substring_groups": [
                        ["章节号"], ["名称/标识"]]},
                ],
                "canon_map": {
                    "软件研制任务书名称/标识": "任务书名称标识",
                    "本文档的名称/标识": "本文档名称标识",
                },
                "column_profiles": {"default": [
                    "任务书名称标识", "本文档名称标识", "跟踪说明"]},
                "direction_first_column_prefix": "任务书",
                "direction_markers": ["任务书", "本文档"],
                "trace_key_columns": {
                    "forward": ["任务书名称标识", "本文档名称标识"],
                    "reverse": ["本文档名称标识", "任务书名称标识"],
                },
            },
            "generic_table": {"signatures": []},
        },
        "classify_order": [
            "capability_table", "interface_table", "qualification_table",
            "trace_table", "generic_table"],
        "extraction_templates": {
            "id_pattern": {"pattern": "PZXQ-[A-Z0-9-]+", "flags": 32},
            "id_binding": {
                "pattern": "(?P<name>.{2,20}?)的标识符[：:]"
                           "(?P<id>PZXQ-[A-Z0-9-]+)",
                "flags": 0},
        },
        "term_vocabularies": {"gjb_presence_words": ["提供", "具备"]},
        "join_params": {"id_join": {"family_segments": 2}},
        "thresholds": {"id_join_support_conf": 0.9},
        "gjb": {"rule_clusters": [
            {"cluster": "GJB-01", "rule_ids": ["GJB-RULE-037"],
             "reason": "测试簇: 合格性方法"},
        ]},
    }


def _minimal_base_lexicon() -> dict:
    """最小可用基词典(全部必填字段的真实子集)."""
    return {
        "scene": "test_scene",
        "description": "测试用基词典",
        "domain_terms": ["BLOB", "SQL"],
        "id_patterns": ["PZXQ-[A-Z0-9-]+"],
        "quote_patterns": ["[「\"]([^「」\"]+)[」\"]"],
        "value_domains": {"运行状态": ["开发阶段", "运行阶段"]},
        "entity_categories": {"数据库名": ["达梦"]},
        "stopwords": ["的", "了", "系统"],
        "alias_patterns": [
            "([\\u4e00-\\u9fffA-Za-z]{2,12})[（(]([A-Za-z0-9]{2,12})[）)]"],
        "definition_patterns": [
            "([A-Za-z\\u4e00-\\u9fff]{1,12})[（(]([^（）()]{1,24})[）)]"],
        "usecase_verbs": ["查询", "管理"],
        "usecase_objects": ["数据", "配置"],
        "usecase_fields": ["前置条件", "后置条件"],
        "strip_prefix_words": ["提供", "支持"],
    }


def _trace_table(forward: bool) -> dict:
    first, second = ("上级文档被追踪内容的名称/标识",
                     "本文档中被追踪内容的名称/标识") if forward else (
        "本文档中被追踪内容的名称/标识", "上级文档被追踪内容的名称/标识")
    caption = "表70 正向追踪表" if forward else "表71 逆向追踪表"
    return _table_block(
        "<table><thead><tr><th><p>序号</p></th>"
        f"<th><p>{first}</p></th><th><p>{second}</p></th>"
        "<th><p>备注</p></th></tr></thead>"
        "<tbody><tr><td><p>1</p></td><td><p>1 范围</p></td>"
        "<td><p>1 范围</p></td><td><p>追踪</p></td></tr></tbody></table>",
        caption)


# ── HTML表头解析(06号经验) ───────────────────────────────


def test_extract_headers_thead_double_p_and_colspan() -> None:
    html = ("<table><thead><tr>"
            "<th><p>项目</p><p>唯一标识符</p></th>"
            '<th colspan="2"><p>需求描述</p></th>'
            "</tr></thead><tbody><tr><td><p>x</p></td></tr></tbody></table>")
    headers, has_thead = extract_table_headers(html)
    assert headers == ("项目唯一标识符", "需求描述")
    assert has_thead is True


def test_extract_headers_no_thead_first_row() -> None:
    html = ("<table><tbody>"
            "<tr><td>Use Case 名称：数据获取/PZXQ-A-B</td>"
            "<td>Actors：参谋</td></tr>"
            "<tr><td>前置条件：已登录</td><td></td></tr></tbody></table>")
    headers, has_thead = extract_table_headers(html)
    # 单元格文本去全部空白(双<p>拆词复原), 字段名随剥空白归一
    assert headers == ("UseCase名称：数据获取/PZXQ-A-B", "Actors：参谋")
    assert has_thead is False


# ── 归纳函数 ─────────────────────────────────────────────


def test_induce_table_signatures_cluster_and_classify() -> None:
    interface_body = ("<table><thead><tr><th><p>序号</p></th>"
                      "<th><p>接口名称/标识</p></th><th><p>接口描述</p></th>"
                      "<th><p>发送方</p></th><th><p>接收方</p></th>"
                      "</tr></thead><tbody><tr><td><p>1</p></td></tr>"
                      "</tbody></table>")
    use_case_body = ("<table><tbody><tr>"
                     "<td>Use Case 名称：数据获取/ABCFW-GN-01</td>"
                     "<td>Actors：参谋</td></tr></tbody></table>")
    blocks = [
        _table_block(interface_body, "表1 接口需求表"),
        _table_block(interface_body, "表2 接口需求表"),
        _table_block(use_case_body),
        _table_block(use_case_body.replace("数据获取", "数据转换")),
        _table_block("<table><thead><tr><th><p>序号</p></th>"
                     "<th><p>约束类型</p></th></tr></thead></table>",
                     "表3 约束"),
    ]
    clusters = induce_table_signatures(blocks, _minimal_base_pack())
    by_key = {c.header_signature: c for c in clusters}
    interface = by_key[("序号", "接口名称/标识", "接口描述", "发送方", "接收方")]
    assert interface.occurrences == 2
    assert interface.matched_kind == "interface_table"
    assert interface.needs_review is False
    use_case = by_key[("UseCase名称", "Actors")]
    assert use_case.occurrences == 2  # 「字段：值」首行按字段名归一聚成同簇
    constraint = by_key[("序号", "约束类型")]
    assert constraint.matched_kind == "generic_table"
    assert constraint.needs_review is True


def test_induce_id_families_root_and_own() -> None:
    blocks = [
        _text_block("数据获取的标识符：PZXQ-SJFWT-GN-01。"),
        _text_block("数据转换的标识符：PZXQ-SJFWT-JK-02，复用PZXQ-SJFWT-GN-01。"),
        _text_block("外部系统JCYY-GN-TYZNYY与DXYY-ZBZQ-JK-WB对接。"),
    ]
    families = induce_id_families(blocks)
    by_prefix = {f.family_prefix: f for f in families}
    assert set(by_prefix) == {"PZXQ-SJFWT", "JCYY-GN", "DXYY-ZBZQ"}
    assert by_prefix["PZXQ-SJFWT"].occurrences == 3
    assert by_prefix["PZXQ-SJFWT"].distinct_ids == 2
    assert by_prefix["PZXQ-SJFWT"].own_root is True
    assert by_prefix["JCYY-GN"].own_root is False
    assert dominant_id_root(families) == "PZXQ"
    assert own_id_prefixes(families) == ["PZXQ"]


def test_induce_id_families_space_inside_id() -> None:
    """01号接口表的真实形态: 根段后带空格「ZZSJHQZHFW -JK-WB-X」."""
    blocks = [_table_block(
        "<table><thead><tr><th><p>接口名称/标识</p></th></tr></thead>"
        "<tbody><tr><td><p>与外部交互接口/ ZZSJHQZHFW -JK-WB-ZHXXXT</p>"
        "</td></tr></tbody></table>")]
    families = induce_id_families(blocks)
    assert [f.family_prefix for f in families] == ["ZZSJHQZHFW-JK"]
    assert "ZZSJHQZHFW" not in domain_term_frequencies(blocks)


def test_induce_value_domains_exact_and_candidates() -> None:
    capability = _table_block(
        "<table><thead><tr><th><p>项目唯一标识符</p></th>"
        "<th><p>需求描述</p></th><th><p>方式名称</p></th>"
        "<th><p>运行状态</p></th></tr></thead><tbody>"
        "<tr><td><p>PZXQ-1</p></td><td><p>d1</p></td>"
        "<td><p>桌面</p></td><td><p>运行阶段</p></td></tr>"
        "<tr><td><p>PZXQ-2</p></td><td><p>d2</p></td>"
        "<td><p>平板</p></td><td><p>开发阶段</p></td></tr>"
        "<tr><td><p>PZXQ-3</p></td><td><p>d3</p></td>"
        "<td><p>桌面</p></td><td><p>—</p></td></tr></tbody></table>")
    joint = _table_block(
        "<table><thead><tr><th><p>序号</p></th>"
        "<th><p>联合研制开发服务</p></th><th><p>标识符</p></th>"
        "<th><p>开发类型</p></th><th><p>状态</p></th></tr></thead>"
        "<tbody><tr><td><p>1</p></td><td><p>数据获取</p></td>"
        "<td><p>ABCFW-GN</p></td><td><p>新开发</p></td>"
        "<td><p>活动</p></td></tr></tbody></table>")
    domains = induce_value_domains([capability, joint])
    assert domains == {"方式名称": ["桌面", "平板"],
                       "运行状态": ["运行阶段", "开发阶段"]}
    candidates = induce_value_domain_candidates([capability, joint])
    assert [(c.field, c.header, c.values) for c in candidates] == [
        ("运行状态", "状态", ("活动",))]  # 模糊候选不并入闭集


def test_induce_domain_terms_filters() -> None:
    blocks = [
        _text_block("系统提供API接口，API支持批量，API返回JSON。"),
        _text_block("JSON校验与JSON解析、JSON导出各一次。"),
        _text_block("E1触发、E1恢复、E1结束。容量GB、GB、GB。"),
        _text_block("版本V10与V10兼容。标识PZXQ-SJFWT-GN-01。"),
        _table_block("<table><thead><tr><th><p>Use Case 名称</p></th>"
                     "</tr></thead><tbody><tr><td><p>Actors</p></td></tr>"
                     "</tbody></table>"),
    ]
    terms = induce_domain_terms(blocks)
    assert "API" in terms
    assert "JSON" in terms
    for noise in ("E1", "GB", "V10", "PZXQ", "SJFWT", "Actors", "GJB", "td"):
        assert noise not in terms
    freqs = domain_term_frequencies(blocks)
    assert freqs["API"] == 3
    assert freqs["JSON"] == 4


def test_induce_trace_direction_markers() -> None:
    clusters = induce_table_signatures(
        [_trace_table(True), _trace_table(False)], _minimal_base_pack())
    draft = induce_trace_direction(clusters, _minimal_base_pack())
    assert draft is not None
    assert draft.direction_markers == ("上级文档", "本文档")
    assert draft.direction_first_column_prefix == "上级文档"
    assert draft.verified_both_directions is True
    assert draft.canon_map == {
        "上级文档被追踪内容的名称/标识": "上级文档名称标识",
        "本文档中被追踪内容的名称/标识": "本文档名称标识",
    }
    assert draft.trace_key_columns["forward"] == [
        "上级文档名称标识", "本文档名称标识"]
    assert draft.trace_key_columns["reverse"] == [
        "本文档名称标识", "上级文档名称标识"]


def test_induce_trace_direction_base_covered_returns_none() -> None:
    """04号形态(基canon已覆盖的任务书表头)不触发方向变体."""
    covered = _table_block(
        "<table><thead><tr><th><p>序号</p></th>"
        "<th><p>软件研制任务书名称/标识</p></th>"
        "<th><p>本文档的名称/标识</p></th><th><p>备注</p></th></tr></thead>"
        "<tbody><tr><td></td><td><p>1</p></td><td><p>1</p></td>"
        "<td><p>追踪</p></td></tr></tbody></table>",
        "表80 追踪性")
    clusters = induce_table_signatures([covered], _minimal_base_pack())
    assert induce_trace_direction(clusters, _minimal_base_pack()) is None


# ── 草稿生成 + schema校验 ────────────────────────────────


def _onboarding_fixture_blocks() -> list[dict]:
    capability = _table_block(
        "<table><thead><tr><th><p>项目唯一标识符</p></th>"
        "<th><p>需求描述</p></th><th><p>方式名称</p></th>"
        "<th><p>运行状态</p></th></tr></thead><tbody>"
        "<tr><td><p>ABCFW-GN-01</p></td><td><p>d</p></td>"
        "<td><p>桌面</p></td><td><p>运行阶段</p></td></tr></tbody></table>")
    ids = _text_block("数据获取的标识符：ABCFW-GN-01，转换的标识符："
                      "ABCFW-JK-02，复用ABCFW-GN-01。")
    api = _text_block("提供API接口，API支持批量，API返回JSON。")
    return [capability, ids, api, _trace_table(True), _trace_table(False)]


def test_build_rulepack_draft_and_schema(tmp_path: Path) -> None:
    base_pack = _minimal_base_pack()
    draft = build_rulepack_draft(
        "doc99", _onboarding_fixture_blocks(), base_pack)
    assert draft["pack_id"] == "doc99_onboard_v1"
    # ID模板根族改写
    assert draft["extraction_templates"]["id_pattern"]["pattern"] \
        == "ABCFW-[A-Z0-9-]+"
    assert "ABCFW-[A-Z0-9-]+" in \
        draft["extraction_templates"]["id_binding"]["pattern"]
    # ID族join范围
    assert draft["join_params"]["id_join"]["id_family_prefixes"] == ["ABCFW"]
    # 追踪方向覆盖(签名扩展+canon+方向)
    trace = draft["table_schemas"]["trace_table"]
    assert trace["direction_first_column_prefix"] == "上级文档"
    assert trace["direction_markers"] == ["上级文档", "本文档"]
    assert trace["canon_map"]["上级文档被追踪内容的名称/标识"] \
        == "上级文档名称标识"
    assert {"any_header_substring_groups": [["被追踪"]]} in trace["signatures"]
    # 标准级知识不动
    assert draft["gjb"] == base_pack["gjb"]
    assert draft["gjb_rule_library_path"] == base_pack["gjb_rule_library_path"]
    # 归纳依据随草稿携带
    assert draft["_onboarding"]["doc_key"] == "doc99"
    assert draft["_onboarding"]["changes"]
    # 草稿通过load_rulepack schema校验(写临时文件)
    path = tmp_path / "doc99_onboard_v1.json"
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    pack = load_rulepack(path)
    assert pack.pack_id == "doc99_onboard_v1"
    assert pack.template("id_pattern").pattern == "ABCFW-[A-Z0-9-]+"


def test_build_lexicon_draft_and_schema(tmp_path: Path) -> None:
    draft = build_lexicon_draft(
        "doc99", _onboarding_fixture_blocks(), _minimal_base_lexicon())
    assert draft["scene"] == "doc99_scene"
    assert draft["id_patterns"] == ["ABCFW-[A-Z0-9-]+"]
    assert "API" in draft["domain_terms"]
    assert "BLOB" in draft["domain_terms"]  # 基术语保留
    assert draft["value_domains"]["运行状态"] == ["开发阶段", "运行阶段"]
    assert draft["value_domains"]["方式名称"] == ["桌面"]
    path = tmp_path / "doc99_scene.json"
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    lexicon = load_lexicon(path)
    assert lexicon.scene == "doc99_scene"
    assert "API" in lexicon.domain_terms


# ── 校验工具(缺口#3) ────────────────────────────────────


def test_validate_cluster_rule_ids_detects_missing() -> None:
    base_pack = _minimal_base_pack()
    draft = build_rulepack_draft(
        "doc99", _onboarding_fixture_blocks(), base_pack)
    library = [{"rule_id": "GJB-RULE-037"}, {"rule_id": "GJB-RULE-038"}]
    assert validate_cluster_rule_ids(draft, library) == []
    broken = json.loads(json.dumps(draft))
    broken["gjb"]["rule_clusters"][0]["rule_ids"].append("GJB-RULE-999")
    assert validate_cluster_rule_ids(broken, library) == ["GJB-RULE-999"]


def test_validate_gjb_section_unchanged_detects_mutation() -> None:
    base_pack = _minimal_base_pack()
    draft = build_rulepack_draft(
        "doc99", _onboarding_fixture_blocks(), base_pack)
    assert validate_gjb_section_unchanged(draft, base_pack) is True
    mutated = json.loads(json.dumps(draft))
    mutated["gjb"]["rule_clusters"][0]["rule_ids"] = ["GJB-RULE-038"]
    assert validate_gjb_section_unchanged(mutated, base_pack) is False


# ── 01号真实数据冒烟 ────────────────────────────────────


def _doc01_blocks() -> list[dict]:
    paths = sorted(glob(str(
        BASE / "data/gjb_438c/mineru_standard/01*/office/*_content_list.json")))
    assert len(paths) == 1, f"预期1个01号content_list, 实际{len(paths)}"
    return json.loads(Path(paths[0]).read_text(encoding="utf-8"))


def test_doc01_induction_smoke() -> None:
    base_pack = json.loads(
        (BASE / "config/rulepacks/srs_gjb_v1.json").read_text(
            encoding="utf-8"))
    report = induce_report(_doc01_blocks(), "doc01", base_pack)
    assert report.block_count == 344
    assert report.table_count == 71
    assert report.id_root == "ZZSJHQZHFW"
    assert len(report.table_clusters) >= 20
    kinds = {c.matched_kind for c in report.table_clusters}
    assert {"use_case_table", "interface_table",
            "qualification_table"} <= kinds
    assert any("被追踪" in header
               for c in report.table_clusters for header in c.header_signature)
    assert ("API", 40) in report.domain_terms


def test_doc01_draft_and_audit_smoke(tmp_path: Path) -> None:
    from tools.audit_gjb_compliance import audit_with_pack, load_doc_blocks

    base_pack = json.loads(
        (BASE / "config/rulepacks/srs_gjb_v1.json").read_text(
            encoding="utf-8"))
    draft = build_rulepack_draft("doc01", _doc01_blocks(), base_pack)
    path = tmp_path / "doc01_onboard_v1.json"
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    pack = load_rulepack(path)
    assert pack.template("id_pattern").pattern == "ZZSJHQZHFW-[A-Z0-9-]+"
    assert pack.table_spec("trace_table").direction_markers == (
        "上级文档", "本文档")
    rules = [{"rule_id": f"GJB-RULE-{index:03d}"}
             for index in range(1, 121)]
    assert validate_cluster_rule_ids(draft, rules) == []
    blocks = load_doc_blocks(
        "data/gjb_438c/mineru_standard/01*/office/*_content_list.json",
        "01数据获取转换分系统需求规格说明-终稿")
    elements = audit_with_pack(blocks, pack)
    audits = elements["audits"]
    assert set(audits) == {f"GJB-{index:02d}" for index in range(1, 12)}
    assert all(state.verdict in {"satisfied", "partial", "violated", "manual"}
               for state in audits.values())
