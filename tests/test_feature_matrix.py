from tools.build_feature_matrix import (
    build_claim_slot_row,
    build_empty_cells,
    build_param_index,
    build_row_roles,
    build_unit_families,
    caption_key,
    classify_empty_text,
    classify_row_role,
    grid_from_rows,
    match_predicate,
    merged_cells,
    nearest_subject_before,
    normalize_operator,
    parse_grid_table,
    reference_key,
    scan_requirement_id_cells,
    subject_from_row_cells,
    units_convertible,
)

PARAM_DICTIONARY = {
    "response_time": {
        "canonical_cn": "响应时间",
        "synonyms_cn": ["响应时间", "时延", "往返时延"],
        "default_unit": "ms",
    },
    "memory_size": {
        "canonical_cn": "内存容量",
        "synonyms_cn": ["内存容量"],
        "default_unit": "MB",
    },
}
UNIT_DICTIONARY = {
    "time": {"units": ["ms", "s"], "conversions": {"ms": 0.001, "s": 1}},
    "storage": {"units": ["byte", "KB", "MB"], "conversions": {"byte": 1, "KB": 1024, "MB": 1048576}},
}
PARAM_INDEX = build_param_index(PARAM_DICTIONARY)
UNIT_FAMILIES = build_unit_families(UNIT_DICTIONARY)

SPAN_HTML = (
    "<table><thead><tr><th>序号</th><th>功能</th><th>备注</th></tr></thead><tbody>"
    "<tr><td>1</td><td rowspan=2>数据归集</td><td>—</td></tr>"
    "<tr><td>2</td><td>源引接</td></tr>"
    '<tr><td colspan="2">汇总</td><td>可用</td></tr>'
    "</tbody></table>"
)


def test_grid_parser_extracts_merged_cells_and_grid_coordinates() -> None:
    grid = parse_grid_table(SPAN_HTML)

    assert grid["n_rows"] == 4
    assert grid["n_cols"] == 3
    assert merged_cells(grid) == [
        {"row_index": 1, "col_index": 1, "rowspan": 2, "colspan": 1},
        {"row_index": 3, "col_index": 0, "rowspan": 1, "colspan": 2},
    ]
    texts = {(cell["row"], cell["col"]): cell["text"] for cell in grid["cells"]}
    assert texts[(1, 1)] == "数据归集"
    assert texts[(2, 0)] == "2"
    assert texts[(2, 2)] == "源引接"
    assert texts[(3, 0)] == "汇总"
    assert texts[(3, 2)] == "可用"


def test_empty_cell_classification_covers_empty_dash_and_inherit() -> None:
    grid = parse_grid_table(SPAN_HTML)
    states = {
        (cell["row_index"], cell["col_index"]): cell["state"]
        for cell in build_empty_cells(grid)
    }

    assert states[(1, 2)] == "dash"
    assert states[(2, 1)] == "inherit_candidate"
    assert (0, 0) not in states
    assert (3, 2) not in states

    plain = grid_from_rows([["", "—", "-"], ["有效", "—", ""]])
    plain_states = {
        (cell["row_index"], cell["col_index"]): cell["state"]
        for cell in build_empty_cells(plain)
    }
    assert plain_states[(0, 0)] == "empty"
    assert plain_states[(0, 1)] == "dash"
    assert plain_states[(0, 2)] == "dash"
    assert (1, 0) not in plain_states

    assert classify_empty_text("") == "empty"
    assert classify_empty_text("—") == "dash"
    assert classify_empty_text("-") == "dash"
    assert classify_empty_text("有效值") is None


def test_row_role_classification_by_first_column_content() -> None:
    assert classify_row_role("ZZSJHQZHFW-GN-SJHQ") == "requirement_row"
    assert classify_row_role("12") == "index_row"
    assert classify_row_role("概述") == "usecase_section_row"
    assert classify_row_role("主事件流") == "usecase_section_row"
    assert classify_row_role("Actor") == "usecase_section_row"
    assert classify_row_role("数据获取") == "data_row"

    roles = {
        cell["row_index"]: cell["role_candidate"] for cell in build_row_roles(
            grid_from_rows([["3.1", "说明"], ["1", "说明"], ["后置条件", "说明"]])
        )
    }
    assert roles[0] == "data_row"
    assert roles[1] == "index_row"
    assert roles[2] == "usecase_section_row"

    grid = parse_grid_table(SPAN_HTML)
    grid_roles = {cell["row_index"]: cell["role_candidate"] for cell in build_row_roles(grid)}
    assert grid_roles[0] == "data_row"
    assert grid_roles[1] == "index_row"
    assert grid_roles[2] == "index_row"
    assert grid_roles[3] == "data_row"


def test_requirement_id_cells_scan_hits_identifier_regex() -> None:
    grid = grid_from_rows([["序号", "标识"], ["1", "ZZSJHQZHFW-GN-SJHQ"]])
    hits = scan_requirement_id_cells(grid)

    assert hits == [{"row_index": 1, "col_index": 1, "value": "ZZSJHQZHFW-GN-SJHQ"}]


def test_claim_slot_row_fills_five_tuple_from_predicate() -> None:
    claim = {
        "claim_id": "CLM-test-1",
        "doc_id": "01",
        "section": "3.3.1",
        "kind": "text_claim",
        "raw_text": "数据获取服务的响应时间应不超过500毫秒。",
        "features": {
            "quantities": [
                {"raw": "不超过500毫秒", "operator_raw": "不超过", "value": 500, "unit_raw": "毫秒"}
            ]
        },
    }
    row = build_claim_slot_row(claim, PARAM_INDEX, UNIT_FAMILIES, "性能需求", [])

    assert row["subject_candidate"] == "数据获取服务"
    assert row["predicate_candidate"] == "响应时间"
    assert row["predicate_key"] == "response_time"
    assert row["operator"] == "<="
    assert row["object_value"] == 500
    assert row["unit_raw"] == "毫秒"
    assert row["unit_canonical"] == "ms"
    assert row["unit_convertible"] is True
    assert row["scope_candidate"] == "3.3.1"
    assert row["slot_fill_fields"] == [
        "subject_candidate",
        "predicate_candidate",
        "operator",
        "object_value",
        "unit_raw",
        "scope_candidate",
    ]
    assert row["slot_fill_rate"] == 1.0
    assert row["parse_status"] == "parsed"


def test_claim_slot_row_selects_quantity_after_predicate() -> None:
    claim = {
        "claim_id": "CLM-test-2",
        "doc_id": "02",
        "section": "1.8.5.1.1",
        "kind": "table_claim",
        "raw_text": "支持首屏加载时间不小于2秒，用户响应时间不小于3秒。",
        "features": {
            "quantities": [
                {"raw": "不小于2秒", "operator_raw": "不小于", "value": 2, "unit_raw": "秒"},
                {"raw": "不小于3秒", "operator_raw": "不小于", "value": 3, "unit_raw": "秒"},
            ]
        },
    }
    row = build_claim_slot_row(claim, PARAM_INDEX, UNIT_FAMILIES, "界面需求", [])

    assert row["object_value"] == 3
    assert row["operator"] == ">="
    assert row["unit_convertible"] is True


def test_claim_slot_row_falls_back_to_row_cells_then_section_title() -> None:
    claim = {
        "claim_id": "CLM-test-3",
        "doc_id": "01",
        "section": "3.10.2",
        "kind": "table_claim",
        "raw_text": "2 | 内存容量 | ≤20M | 保证传输服务正常收发数据时，内存容量不小于20M",
        "features": {
            "quantities": [
                {"raw": "2", "operator_raw": "", "value": 2, "unit_raw": ""},
                {"raw": "≤20", "operator_raw": "≤", "value": 20, "unit_raw": ""},
            ]
        },
    }
    row = build_claim_slot_row(claim, PARAM_INDEX, UNIT_FAMILIES, "内存需求", ["2", "内存容量", "≤20M"])

    assert row["subject_candidate"] == "内存容量"
    assert row["predicate_key"] == "memory_size"
    assert row["unit_canonical"] == "MB"
    assert row["object_value"] == 20
    assert row["operator"] == "<="
    assert row["unit_convertible"] is False

    bare = {
        "claim_id": "CLM-test-4",
        "doc_id": "01",
        "section": "1.1",
        "kind": "text_claim",
        "raw_text": "系统应支持稳定运行。",
        "features": {},
    }
    bare_row = build_claim_slot_row(bare, PARAM_INDEX, UNIT_FAMILIES, "概述", [])
    assert bare_row["subject_candidate"] == "概述"
    assert bare_row["slot_fill_fields"] == ["subject_candidate", "scope_candidate"]
    assert bare_row["slot_fill_rate"] == 0.3333
    assert bare_row["parse_status"] == "partial"
    assert bare_row["object_value"] is None


def test_operator_normalization_maps_raw_tokens_to_canonical() -> None:
    assert normalize_operator("不超过") == "<="
    assert normalize_operator("不大于") == "<="
    assert normalize_operator("小于等于") == "<="
    assert normalize_operator("≤") == "<="
    assert normalize_operator("不小于") == ">="
    assert normalize_operator("不低于") == ">="
    assert normalize_operator("≥") == ">="
    assert normalize_operator("=") == "="
    assert normalize_operator("至少") == ">="
    assert normalize_operator("") == ""
    assert normalize_operator("未知词") == ""


def test_unit_conversion_marks_family_membership() -> None:
    assert units_convertible("秒", "ms", UNIT_FAMILIES) is True
    assert units_convertible("毫秒", "s", UNIT_FAMILIES) is True
    assert units_convertible("ms", "ms", UNIT_FAMILIES) is True
    assert units_convertible("MB", "MB", UNIT_FAMILIES) is True
    assert units_convertible("MB", "ms", UNIT_FAMILIES) is False
    assert units_convertible("", "ms", UNIT_FAMILIES) is False
    assert units_convertible("MB", "", UNIT_FAMILIES) is False
    assert units_convertible("KB", "byte", UNIT_FAMILIES) is True


def test_predicate_matching_prefers_longest_synonym() -> None:
    hit = match_predicate("端到端往返时延应小于等于100ms", PARAM_INDEX)
    assert hit is not None
    assert hit["predicate_key"] == "response_time"
    assert hit["synonym"] == "往返时延"

    assert match_predicate("系统内存容量不小于20M", PARAM_INDEX)["predicate_key"] == "memory_size"
    assert match_predicate("无参数句子", PARAM_INDEX) is None


def test_reference_and_caption_key_resolution() -> None:
    assert reference_key("见表3") == ("表", "3")
    assert reference_key("如图 1") == ("图", "1")
    assert reference_key("表3-1") == ("表", "3-1")
    assert reference_key("参见GJB 438C") is None

    assert caption_key("表 3 合格性规定") == ("表", "3")
    assert caption_key("图1 系统组成图") == ("图", "1")
    assert caption_key("续表2") is None
    assert caption_key("") is None

    assert reference_key("见表3") in {caption_key("表 3 合格性规定")}
    assert reference_key("如图 1") in {caption_key("图 1 某分系统组成图")}
    assert reference_key("见表41") not in {caption_key("表 3 合格性规定")}


def test_subject_heuristics_before_predicate_and_from_row_cells() -> None:
    assert nearest_subject_before("某系统的响应时间", 4) == "某系统"
    assert nearest_subject_before("传输服务的时延", 5) == "传输服务"
    assert nearest_subject_before("响应时间", 0) == ""
    assert nearest_subject_before("；响应时间", 1) == ""
    assert nearest_subject_before("应满足要求，响应时间", 6) == "应满足要求"

    assert subject_from_row_cells(["1", "数据获取/ZZSJHQZHFW-GN-SJHQ"]) == (
        "数据获取/ZZSJHQZHFW-GN-SJHQ"
    )
    assert subject_from_row_cells(["", "内存容量"]) == "内存容量"
    assert subject_from_row_cells(["—", ""]) == ""
    assert subject_from_row_cells(["3"]) == "3"
