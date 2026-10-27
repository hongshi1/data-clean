"""Feature matrix v2: span location, negation/condition extraction,
reference resolution, header tree expansion and cell coordinates
( synthetic data only )."""
from tools.build_feature_matrix import parse_grid_table
from tools.build_feature_matrix_v2 import (
    build_caption_index,
    build_header_tree,
    build_sentence_row,
    build_table_cells,
    build_table_row_v2,
    count_thead_rows,
    find_conditions,
    find_negations,
    find_scope_entities,
    find_sentence_span,
    resolve_reference,
)

SYNTH_BLOCKS = [
    (0, "系统由数据获取、数据转换两部分组成。"),
    (1, "c）\t禁止在系统所使用的配置文件中存储敏感数据。"),
    (2, "当网络中断时，传输服务不得丢失报文。"),
]

MULTI_HEADER_HTML = (
    '<table><thead><tr><th rowspan="2">序号</th><th rowspan="2">需求类型</th>'
    '<th colspan="3">重要性与关键性等级</th></tr>'
    "<tr><th>高级</th><th>中级</th><th>低级</th></tr></thead>"
    "<tbody><tr><td>1</td><td>功能</td><td>是</td><td>否</td><td>是</td></tr></tbody></table>"
)

NO_THEAD_ROWSPAN_HTML = (
    '<table><tr><td rowspan="2">序号</td><td rowspan="2">需求类型</td>'
    '<td colspan="3">等级</td></tr>'
    "<tr><td>高</td><td>中</td><td>低</td></tr>"
    "<tr><td>1</td><td>功能</td><td>是</td><td>否</td><td>是</td></tr></table>"
)


def test_sentence_span_exact_located() -> None:
    raw = "系统由数据获取、数据转换两部分组成。"
    span = find_sentence_span(SYNTH_BLOCKS, raw)

    assert span["status"] == "located"
    assert span["block_idx"] == 0
    assert SYNTH_BLOCKS[0][1][span["start"] : span["end"]] == raw


def test_sentence_span_prefers_observation_pinned_block() -> None:
    blocks = [(3, "重复句子。"), (7, "重复句子。")]
    span = find_sentence_span(blocks, "重复句子。", preferred_block=7)

    assert span["block_idx"] == 7


def test_sentence_span_normalized_fallback_for_tab() -> None:
    raw = "c） 禁止在系统所使用的配置文件中存储敏感数据。"
    span = find_sentence_span(SYNTH_BLOCKS, raw)

    assert span["status"] == "located_normalized"
    assert span["block_idx"] == 1
    original = SYNTH_BLOCKS[1][1]
    assert original[span["start"] : span["end"]] == "c）\t禁止在系统所使用的配置文件中存储敏感数据。"


def test_sentence_span_unlocated_reports_status() -> None:
    span = find_sentence_span(SYNTH_BLOCKS, "本句在原文块中不存在。")

    assert span["status"] == "unlocated"
    assert span["block_idx"] is None
    assert span["start"] is None
    assert span["end"] is None


def test_negation_positions_are_char_offsets() -> None:
    text = "不得存储敏感数据，禁止外发；无法访问时应告警。"
    hits = find_negations(text)

    assert [hit["word"] for hit in hits] == ["不得", "禁止", "无法"]
    for hit in hits:
        assert text[hit["pos"] : hit["pos"] + len(hit["word"])] == hit["word"]
    assert hits[0]["pos"] == 0
    assert find_negations("系统应稳定运行。") == []


def test_condition_patterns_extract_dang_and_ruo() -> None:
    text = "当网络中断时应自动重传，若校验失败则丢弃该报文。"
    hits = find_conditions(text)
    by_pattern = {hit["pattern"]: hit for hit in hits}

    assert by_pattern["当…时"]["cond_text"] == "网络中断"
    assert by_pattern["当…时"]["raw"] == "当网络中断时"
    assert text[by_pattern["当…时"]["pos"] :].startswith("当网络中断时")
    assert by_pattern["若…则"]["cond_text"] == "校验失败"
    assert by_pattern["若…则"]["raw"] == "若校验失败则"


def test_condition_patterns_extract_ruguo_and_zai() -> None:
    text = "如果校验失败则执行异常流，在网络故障情况下应告警。"
    hits = find_conditions(text)
    by_pattern = {hit["pattern"]: hit for hit in hits}

    assert by_pattern["如果…则"]["cond_text"] == "校验失败"
    zai = by_pattern["在…下"]
    assert zai["raw"] == "在网络故障情况下"
    assert zai["cond_text"] == "网络故障情况"
    assert find_conditions("系统应稳定运行。") == []


def test_build_sentence_row_composes_all_fields() -> None:
    claim = {
        "claim_id": "CLM-synth-1",
        "doc_id": "01",
        "section": "3.4.2",
        "kind": "text_claim",
        "raw_text": "当网络中断时，传输服务不得丢失报文。",
        "source_observation_ids": ["OBS-synth-1"],
        "features": {},
    }
    row = build_sentence_row(claim, SYNTH_BLOCKS, {"OBS-synth-1": 2})

    assert row["span_status"] == "located"
    assert row["span"] == {"block_idx": 2, "start": 0, "end": 18}
    assert [hit["word"] for hit in row["negations"]] == ["不得"]
    assert row["has_condition"] is True
    assert row["conditions"][0]["cond_text"] == "网络中断"
    assert row["scope_candidate"] == "3.4.2"
    assert [item["entity"] for item in row["scope_entity"]] == ["传输服务"]


def test_scope_entity_strips_function_prefix_and_possessive_tail() -> None:
    hits = find_scope_entities("与运行支撑服务分系统互联，数据获取服务应支持采集。")

    assert [item["entity"] for item in hits] == ["运行支撑服务分系统", "数据获取服务"]
    assert hits[0]["raw"] == "与运行支撑服务分系统"

    possessive = find_scope_entities("用户的接口应加密。")
    assert [item["entity"] for item in possessive] == ["用户接口"]


def test_scope_entity_filters_shallow_prefixes() -> None:
    assert find_scope_entities("任何服务均不得中断。") == []
    assert find_scope_entities("系统应稳定运行。") == []


def test_reference_resolution_matches_caption_prefix() -> None:
    images = [{"doc_id": "01", "image_id": "IMG-01-0000", "caption_raw": "图 1 某分系统组成图"}]
    tables = [{"doc_id": "01", "table_id": "T-01-0003", "caption_raw": "表3 合格性规定"}]
    index, duplicates = build_caption_index(images, tables, {"01"})

    assert duplicates == 0
    assert resolve_reference("如图 1", "01", index) == {
        "ref": "如图 1",
        "target_id": "IMG-01-0000",
        "status": "resolved",
    }
    assert resolve_reference("见表3", "01", index)["target_id"] == "T-01-0003"
    miss = resolve_reference("见表9", "01", index)
    assert miss["status"] == "unresolved"
    assert miss["target_id"] is None
    assert resolve_reference("见表3", "02", index)["status"] == "unresolved"


def test_reference_resolution_counts_ambiguous_caption_keys() -> None:
    tables = [
        {"doc_id": "01", "table_id": "T-01-0000", "caption_raw": "表3 合格性规定"},
        {"doc_id": "01", "table_id": "T-01-0009", "caption_raw": "表3 重复标题"},
    ]
    index, duplicates = build_caption_index([], tables, {"01"})

    assert duplicates == 1
    assert index[("01", "表", "3")] == "T-01-0000"


def test_count_thead_rows() -> None:
    assert count_thead_rows(MULTI_HEADER_HTML) == 2
    assert count_thead_rows("<table><tr><td>仅一行</td></tr></table>") == 0
    assert count_thead_rows("") == 0


def test_header_tree_expands_rowspan_colspan() -> None:
    grid = parse_grid_table(MULTI_HEADER_HTML)
    tree = build_header_tree(grid, count_thead_rows(MULTI_HEADER_HTML))

    assert tree["multi_level"] is True
    assert tree["levels"] == 2
    assert [node["text"] for node in tree["nodes"]] == ["序号", "需求类型", "重要性与关键性等级"]
    by_text = {node["text"]: node for node in tree["nodes"]}
    assert by_text["序号"]["rowspan"] == 2
    assert by_text["序号"]["children"] == []
    assert by_text["需求类型"]["children"] == []
    assert by_text["重要性与关键性等级"]["colspan"] == 3
    assert [child["text"] for child in by_text["重要性与关键性等级"]["children"]] == [
        "高级",
        "中级",
        "低级",
    ]


def test_header_tree_rowspan_without_thead() -> None:
    tree = build_header_tree(
        parse_grid_table(NO_THEAD_ROWSPAN_HTML), count_thead_rows(NO_THEAD_ROWSPAN_HTML)
    )

    assert tree["multi_level"] is True
    by_text = {node["text"]: node for node in tree["nodes"]}
    assert [child["text"] for child in by_text["等级"]["children"]] == ["高", "中", "低"]
    assert by_text["序号"]["children"] == []


def test_header_tree_single_level_without_merge() -> None:
    html = (
        "<table><thead><tr><th>序号</th><th>名称</th></tr></thead>"
        "<tbody><tr><td>1</td><td>x</td></tr></tbody></table>"
    )
    tree = build_header_tree(parse_grid_table(html), count_thead_rows(html))

    assert tree["multi_level"] is False
    assert tree["levels"] == 1
    assert [node["text"] for node in tree["nodes"]] == ["序号", "名称"]
    assert all(node["children"] == [] for node in tree["nodes"])


def test_table_cells_coordinates_and_merge_flags() -> None:
    grid = parse_grid_table(MULTI_HEADER_HTML)
    cells = build_table_cells("T-01-0000", grid)
    lookup = {cell["cell_id"]: cell for cell in cells}

    assert len(cells) == 11
    assert lookup["T-01-0000:r0c0"]["text"] == "序号"
    assert lookup["T-01-0000:r0c0"]["row"] == 0
    assert lookup["T-01-0000:r0c0"]["col"] == 0
    assert lookup["T-01-0000:r0c0"]["is_merged_origin"] is True
    assert lookup["T-01-0000:r0c0"]["rowspan"] == 2
    assert lookup["T-01-0000:r0c2"]["colspan"] == 3
    assert lookup["T-01-0000:r1c2"]["text"] == "高级"
    assert lookup["T-01-0000:r1c2"]["is_merged_origin"] is False
    assert lookup["T-01-0000:r2c4"]["text"] == "是"
    assert lookup["T-01-0000:r2c4"]["cell_id"] == "T-01-0000:r2c4"


def test_build_table_row_v2_composes_table_features() -> None:
    table = {
        "table_id": "T-01-0000",
        "doc_id": "01",
        "section": "3.3",
        "caption_raw": "表3 重要性与关键性等级表",
        "page": 5,
        "rows": [["序号", "需求类型", "重要性与关键性等级", "", ""]],
    }
    row = build_table_row_v2(table, MULTI_HEADER_HTML)

    assert row["source"] == "content_list_html"
    assert row["n_rows"] == 3
    assert row["n_cols"] == 5
    assert row["thead_rows"] == 2
    assert row["header_levels"] == 2
    assert row["multi_level_header"] is True
    assert row["n_cells"] == 11
    assert row["cells"][0]["cell_id"] == "T-01-0000:r0c0"


def test_build_table_row_v2_falls_back_to_plain_rows() -> None:
    table = {
        "table_id": "T-02-0001",
        "doc_id": "02",
        "section": "2",
        "caption_raw": "表1 引用文档一览表",
        "rows": [["序号", "名称"], ["1", "x"]],
    }
    row = build_table_row_v2(table, "")

    assert row["source"] == "rows_fallback"
    assert row["n_rows"] == 2
    assert row["n_cols"] == 2
    assert row["multi_level_header"] is False
    assert row["n_cells"] == 4
    assert all(cell["is_merged_origin"] is False for cell in row["cells"])
