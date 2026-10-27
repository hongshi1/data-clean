from tools.build_structured_corpus import (
    extract_features,
    parse_html_table,
    parse_section,
    section_parent,
    stable_id,
)


def test_section_helpers_preserve_srs_hierarchy() -> None:
    assert parse_section("3.2.1 账户锁定") == ("3.2.1", "账户锁定")
    assert section_parent("3.2.1") == "3.2"
    assert section_parent("3") is None


def test_structured_features_preserve_requirement_constraints_and_references() -> None:
    features = extract_features("用户连续5次输入错误密码后，系统应锁定账户30分钟，见图3。")

    assert features["quantities"][0]["value"] == 5
    assert features["quantities"][1]["unit_raw"] == "分钟"
    assert "应" in features["modal_words"]
    assert features["references"] == ["见图3"]


def test_mineru_table_parser_preserves_rows_and_columns() -> None:
    rows, data_start = parse_html_table(
        "<table><tr><th>编号</th><th>名称</th></tr>"
        "<tr><td>1</td><td>账户锁定</td></tr></table>"
    )

    assert rows == [["编号", "名称"], ["1", "账户锁定"]]
    assert data_start == 1


def test_mineru_table_parser_respects_thead_boundary() -> None:
    rows, data_start = parse_html_table(
        "<table><thead><tr><th>编号</th><th>名称</th></tr>"
        "<tr><th>备注</th><th>说明</th></tr></thead>"
        "<tbody><tr><td>1</td><td>账户锁定</td></tr>"
        "<tr><td>2</td><td>账户解锁</td></tr></tbody></table>"
    )

    assert rows == [["编号", "名称"], ["备注", "说明"],
                    ["1", "账户锁定"], ["2", "账户解锁"]]
    # multi-row thead: data rows start after thead ends, not after rows[0]
    assert data_start == 2


def test_mineru_table_parser_empty_thead_yields_all_data_rows() -> None:
    rows, data_start = parse_html_table(
        "<table><thead></thead><tbody>"
        "<tr><td>1</td><td>账户锁定</td></tr></tbody></table>"
    )

    assert rows == [["1", "账户锁定"]]
    assert data_start == 0


def test_stable_ids_are_deterministic_and_namespaced() -> None:
    assert stable_id("REQ", "doc01", "3.2.1") == stable_id("REQ", "doc01", "3.2.1")
    assert stable_id("REQ", "doc01", "3.2.1") != stable_id("CLM", "doc01", "3.2.1")
