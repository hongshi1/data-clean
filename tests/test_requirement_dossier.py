"""render_requirement_dossier 档案视图内核的确定性测试（合成content_list）.

合成小文档复刻GJB真实结构(需求树3.2.1→3.2.1.1→叶子/能力标识表/用例表/
第4章合格性表/第5章追溯表), 聚焦:
- 需求树标题解析正则(严格+宽松ID, 非ID标题)
- 叶子区间切分(下一同级/上级标题为界)
- 行匹配三重逻辑(ID直接/ID后缀/编号/名称, 上级ID排除)
- 合格性与追溯行的直接匹配+上级回退
- 六路证据齐全度计算
- payload装配与自包含HTML渲染(base64原图/JSON岛)
真实doc04快照数字(57节点/47叶子/六路✓✓✓✓✗✗)单列slow测试, 数据缺失时跳过。
"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

import render_requirement_dossier as rd  # noqa: E402

# 1x1 透明PNG(合法文件, 供base64嵌入测试)
PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
PNG_BYTES = base64.b64decode(PNG_1X1)

CAP_TABLE_DOMAIN = (
    "<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th></tr></thead>"
    "<tbody><tr><td></td><td><p>数据库操作</p></td>"
    "<td><p>TT-GN-SQLFW-SJKCZ</p></td>"
    "<td><p>数据库操作功能包括数据库初始化等</p></td></tr></tbody></table>"
)
CAP_TABLE_PARENT = (
    "<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th></tr></thead>"
    "<tbody>"
    "<tr><td></td><td><p>数据库初始化</p></td><td><p>TT-GN-SJKCZ-SJKCSH</p></td>"
    "<td><p>初始化数据库</p></td></tr>"
    "<tr><td></td><td><p>数据库关闭</p></td><td><p>TT-GN-SQLFW-SJKCZ-BJKGB</p></td>"
    "<td><p>关闭数据库</p></td></tr>"
    "</tbody></table>"
)
UC_TABLE = (
    "<table><tr><td><p>Use Case 名称：数据库初始化</p></td>"
    '<td colspan="2"><p>Actors：应用软件</p></td></tr>'
    '<tr><td colspan="3"><p>概述：描述数据库初始化的过程</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流：如果失败则执行异常流E1</p></td></tr>'
    '<tr><td colspan="3"><p>异常流E1：系统提示初始化失败，用例结束。</p></td></tr>'
    "</table>"
)
QUAL_TABLE = (
    "<table><tr><td><p>需求名称/标识</p></td><td><p>本文档的章节号</p></td>"
    "<td><p>合格性方法</p></td><td><p>合格性级别</p></td></tr>"
    "<tr><td><p>数据库初始化</p></td><td><p>3.2.1.1.1.1</p></td>"
    "<td><p>A</p></td><td><p>a</p></td></tr>"
    "<tr><td><p>SQL访问</p></td><td><p>3.2.1</p></td>"
    "<td><p>B</p></td><td><p>b</p></td></tr></table>"
)
TRACE_TABLE = (
    "<table><thead><tr><th><p>任务书名称/标识</p></th><th><p>任务书章节号</p></th>"
    "<th><p>本文档的名称/标识</p></th><th><p>本文档的章节号</p></th>"
    "<th><p>跟踪说明</p></th></tr></thead><tbody>"
    "<tr><td><p>原生SQL访问</p></td><td><p>4.1.1 b)</p></td>"
    "<td><p>SQL访问</p></td><td><p>3.2.1</p></td><td></td></tr>"
    "<tr><td><p>数据库初始化</p></td><td><p>4.1.1 c)</p></td>"
    "<td><p>数据库初始化</p></td><td><p>3.2.1.1.1.1</p></td><td></td></tr>"
    "</tbody></table>"
)

BLOCKS = [
    {"type": "text", "text": "1 范围", "text_level": 1},
    {"type": "text", "text": "3 需求", "text_level": 1},
    {"type": "text", "text": "3.2 CSCI能力需求", "text_level": 2},
    {"type": "text", "text": "3.2.1 SQL访问（TT-GN-SQLFW）", "text_level": 3},
    {"type": "text", "text": "SQL访问功能包括数据库操作，其用例如图1所示。"},
    {"type": "image", "image_caption": ["图1 SQL访问用例图"], "image_path": "images/fig_001.png"},
    {"type": "table", "table_caption": ["表1 SQL访问所有能力标识"], "table_body": CAP_TABLE_DOMAIN},
    {"type": "text", "text": "3.2.1.1 SQL访问-数据库操作（TT-GN-SQLFW-SJKCZ）", "text_level": 4},
    {"type": "table", "table_caption": ["表2 数据库操作所有能力标识"], "table_body": CAP_TABLE_PARENT},
    {
        "type": "text",
        "text": "3.2.1.1.1.1 数据库操作-数据库初始化（TT-GN-SQLFW-SJKCZ-SJKCSH）",
        "text_level": 6,
    },
    {"type": "text", "text": "数据库初始化用例场景，见表3所示。"},
    {"type": "table", "table_caption": ["表3 数据库初始化用例描述"], "table_body": UC_TABLE},
    {"type": "text", "text": "数据库初始化流程图如图2所示。"},
    {"type": "image", "image_caption": ["图2 数据库初始化流程图"], "image_path": "images/fig_002.png"},
    {
        "type": "text",
        "text": "3.2.1.1.1.2 数据库操作-数据库关闭（TT-GN-SQLFW-SJKCZ- BJKGB）",
        "text_level": 6,
    },
    {"type": "text", "text": "数据库关闭用例场景，见表4所示。"},
    {"type": "text", "text": "4 合格性规定", "text_level": 1},
    {"type": "table", "table_caption": ["表80 合格性规定"], "table_body": QUAL_TABLE},
    {"type": "text", "text": "5 需求可追踪性", "text_level": 1},
    {"type": "table", "table_caption": ["表81 需求的正向追踪性"], "table_body": TRACE_TABLE},
    {"type": "text", "text": "6 注释", "text_level": 1},
    {"type": "text", "text": "无。"},
]

SYNTH_FEATURES = {
    "table_features": [
        {
            "doc_id": "T1",
            "caption": "表3 数据库初始化用例描述",
            "n_rows": 4,
            "n_cols": 3,
            "merged_cells": [{"row_index": 1}],
            "section": "3.2.1.1.1.1",
            "table_id": "TT-T1-0000",
        }
    ],
    "text_features": [
        {
            "doc_id": "T1",
            "text": "数据库初始化用例场景，见表3所示。",
            "quantities": [1],
            "references": ["表3"],
        }
    ],
    "diagrams": {
        "DGM-1": {
            "n_nodes": 5,
            "n_edges": 4,
            "texts": ["数据库初始化"],
            "types": ["start", "process", "end", "state", "process"],
        }
    },
}


def _tree():
    return rd.build_tree(BLOCKS)


def _leaf(num: str) -> dict:
    for node in _tree():
        if node["num"] == num:
            return node
    raise AssertionError(f"节点不存在: {num}")


# ------------------------------------------------------------- 标题解析正则

def test_parse_req_heading_strict():
    parsed = rd.parse_req_heading("3.2.1.1.1.1 数据库操作-数据库初始化（TT-GN-SQLFW-SJKCZ-SJKCSH）")
    assert parsed == ("3.2.1.1.1.1", "数据库操作-数据库初始化", "TT-GN-SQLFW-SJKCZ-SJKCSH")


def test_parse_req_heading_loose_internal_space():
    parsed = rd.parse_req_heading("3.2.1.1.1.2 数据库操作-数据库关闭（TT-GN-SQLFW-SJKCZ- BJKGB）")
    assert parsed is not None
    assert parsed[2] == "TT-GN-SQLFW-SJKCZ-BJKGB"


def test_parse_req_heading_loose_en_dash():
    parsed = rd.parse_req_heading("3.4.2 名录解析接口（TT-NBJK-WDCLFW –WLZY-ZJML）")
    assert parsed is not None
    assert parsed[2] == "TT-NBJK-WDCLFW-WLZY-ZJML"


@pytest.mark.parametrize(
    "text",
    [
        "3.2 CSCI能力需求",
        "3.9 计算机硬件需求（含GPU）",
        "1.1 标识",
        "4 合格性规定",
        "3.2.1 SQL访问（无ID括号内容）",
    ],
)
def test_parse_req_heading_rejects_non_requirement(text):
    assert rd.parse_req_heading(text) is None


# ------------------------------------------------------------- 需求树与叶子区间

def test_build_tree_structure_and_levels():
    nodes = _tree()
    assert [n["num"] for n in nodes] == ["3.2.1", "3.2.1.1", "3.2.1.1.1.1", "3.2.1.1.1.2"]
    by_num = {n["num"]: n for n in nodes}
    assert by_num["3.2.1"]["parent"] is None
    assert by_num["3.2.1"]["children"] == ["3.2.1.1"]
    assert by_num["3.2.1.1"]["parent"] == "3.2.1"
    # 编号跳级(3.2.1.1 → 3.2.1.1.1.1): 父指针逐级上溯到最近的已存在编号
    assert by_num["3.2.1.1.1.1"]["parent"] == "3.2.1.1"
    assert by_num["3.2.1.1.1.2"]["parent"] == "3.2.1.1"
    leaves = [n for n in nodes if not n["children"]]
    assert [n["num"] for n in leaves] == ["3.2.1.1.1.1", "3.2.1.1.1.2"]


def test_leaf_interval_cuts_at_next_same_or_upper_heading():
    leaf = _leaf("3.2.1.1.1.1")
    start, end = rd.leaf_interval(BLOCKS, leaf)
    assert (start, end) == (10, 14)
    kinds = [b["type"] for b in BLOCKS[start:end]]
    assert kinds == ["text", "table", "text", "image"]


def test_leaf_interval_runs_to_chapter_heading():
    leaf = _leaf("3.2.1.1.1.2")
    start, end = rd.leaf_interval(BLOCKS, leaf)
    assert (start, end) == (15, 16)
    assert BLOCKS[start]["text"] == "数据库关闭用例场景，见表4所示。"


# ------------------------------------------------------------- 行三重匹配

def test_match_row_id_direct_and_suffix():
    req = {"num": "3.2.1.1.1.1", "name": "数据库操作-数据库初始化",
           "short": "数据库初始化", "id": "TT-GN-SQLFW-SJKCZ-SJKCSH"}
    rows = rd.split_table_rows(CAP_TABLE_PARENT)
    # 行ID TT-GN-SJKCZ-SJKCSH 与标题ID差一个中段 → 共同后缀段≥2 → ID后缀匹配
    assert rd.match_row_to_req(rows[1], req, set()) == (2, "ID后缀")
    # 兄弟叶子(数据库关闭)的行与本需求无任何匹配
    assert rd.match_row_to_req(rows[2], req, set()) is None
    req2 = {"num": "3.2.1.1.1.2", "name": "数据库操作-数据库关闭",
            "short": "数据库关闭", "id": "TT-GN-SQLFW-SJKCZ-BJKGB"}
    assert rd.match_row_to_req(rows[2], req2, set()) == (3, "ID")


def test_match_row_excludes_ancestor_own_row():
    req = {"num": "3.2.1.1.1.1", "name": "数据库操作-数据库初始化",
           "short": "数据库初始化", "id": "TT-GN-SQLFW-SJKCZ-SJKCSH"}
    ancestor_ids = {"TT-GN-SQLFW-SJKCZ", "TT-GN-SQLFW"}
    row = rd.split_table_rows(CAP_TABLE_DOMAIN)[1]
    # 表1的行是上级3.2.1.1自己的行(其ID=上级ID), 不算本需求的行
    assert rd.match_row_to_req(row, req, ancestor_ids) is None


def test_match_row_by_name_whole_cell():
    req = {"num": "3.2.2.1", "name": "对象化访问-数据插入",
           "short": "数据插入", "id": "TT-GN-DXHFW-SJCR"}
    row = "<tr><td></td><td><p>数据插入</p></td><td><p>无关ID</p></td></tr>"
    assert rd.match_row_to_req(row, req, set()) == (1, "名称")


def test_num_in_text_digit_boundary():
    assert rd.num_in_text("3.2.1", "见3.2.1所示")
    assert rd.num_in_text("3.2.1", "3.2.1、3.2.2")
    assert not rd.num_in_text("3.2.1", "3.2.1.1")  # 更深编号不算
    assert not rd.num_in_text("3.2.1", "13.2.1")  # 前缀数字粘连不算
    assert not rd.num_in_text("3.2.1", "3.2.12")


# ------------------------------------------------------------- 合格性/追溯行

def test_find_qualification_direct_and_fallback():
    leaf1 = _leaf("3.2.1.1.1.1")
    qual1 = rd.find_qualification(BLOCKS, leaf1)
    assert qual1["fallback_of"] is None
    assert len(qual1["entries"]) == 1
    assert "3.2.1.1.1.1" in qual1["entries"][0]["rows"][0]
    assert "<p>A</p>" in qual1["entries"][0]["rows"][0]

    leaf2 = _leaf("3.2.1.1.1.2")
    qual2 = rd.find_qualification(BLOCKS, leaf2)
    assert qual2["fallback_of"] == "3.2.1"
    assert qual2["entries"][0]["fallback_of"] == "3.2.1"
    assert "<p>B</p>" in qual2["entries"][0]["rows"][0]


def test_find_trace_direct_and_fallback():
    leaf1 = _leaf("3.2.1.1.1.1")
    trace1 = rd.find_trace(BLOCKS, leaf1)
    assert trace1["fallback_of"] is None
    assert len(trace1["entries"]) == 1
    assert "4.1.1 c)" in trace1["entries"][0]["rows"][0]

    leaf2 = _leaf("3.2.1.1.1.2")
    trace2 = rd.find_trace(BLOCKS, leaf2)
    assert trace2["fallback_of"] == "3.2.1"
    assert "4.1.1 b)" in trace2["entries"][0]["rows"][0]


def test_find_capability_rows_direct():
    leaf1 = _leaf("3.2.1.1.1.1")
    nodes_by_num = {n["num"]: n for n in _tree()}
    ancestor_ids = {"TT-GN-SQLFW-SJKCZ", "TT-GN-SQLFW"}
    found = rd.find_capability_rows(BLOCKS, leaf1, ancestor_ids, {}, nodes_by_num)
    assert found["fallback_of"] is None
    assert len(found["entries"]) == 1
    entry = found["entries"][0]
    assert entry["label"] == "表2 数据库操作所有能力标识"
    assert entry["match"] == "ID后缀"
    assert "TT-GN-SJKCZ-SJKCSH" in entry["rows"][0]


# ------------------------------------------------------------- 六路证据齐全度

def _leaf_payload_evidence(num: str) -> dict[str, bool]:
    leaf = _leaf(num)
    start, end = rd.leaf_interval(BLOCKS, leaf)
    range_blocks = BLOCKS[start:end]
    fragments, _ = rd.build_fragments(BLOCKS, start, end, leaf, SYNTH_FEATURES)
    nodes_by_num = {n["num"]: n for n in _tree()}
    ancestor_ids = set()
    parent = leaf["parent"]
    while parent:
        ancestor_ids.add(nodes_by_num[parent]["id"])
        parent = nodes_by_num[parent]["parent"]
    capability = rd.find_capability_rows(BLOCKS, leaf, ancestor_ids, {}, nodes_by_num)
    qualification = rd.find_qualification(BLOCKS, leaf)
    trace = rd.find_trace(BLOCKS, leaf)
    evidence = rd.compute_evidence(range_blocks, fragments, capability, qualification, trace)
    return {e["key"]: e["ok"] for e in evidence}


def test_compute_evidence_all_six_routes_present():
    values = _leaf_payload_evidence("3.2.1.1.1.1")
    assert values == {
        "body": True,
        "usecase_table": True,
        "flow_image": True,
        "capability_row": True,
        "qualification_row": True,
        "trace_row": True,
    }


def test_compute_evidence_missing_routes_reported():
    values = _leaf_payload_evidence("3.2.1.1.1.2")
    assert values == {
        "body": True,
        "usecase_table": False,
        "flow_image": False,
        "capability_row": True,
        "qualification_row": False,  # 直接行缺失(有上级回退行)
        "trace_row": False,
    }


def test_evidence_route_labels_and_order():
    leaf = _leaf("3.2.1.1.1.1")
    start, end = rd.leaf_interval(BLOCKS, leaf)
    fragments, _ = rd.build_fragments(BLOCKS, start, end, leaf, SYNTH_FEATURES)
    evidence = rd.compute_evidence(BLOCKS[start:end], fragments,
                                   {"entries": [], "fallback_of": None},
                                   {"entries": [], "fallback_of": None},
                                   {"entries": [], "fallback_of": None})
    assert [e["label"] for e in evidence] == [
        "正文", "用例表", "流程图", "能力表行", "合格性行", "追溯行",
    ]
    assert all(e["detail"] for e in evidence)


# ------------------------------------------------------------- 侧栏注脚

def test_table_note_counts_from_features_and_exception_flows():
    row = SYNTH_FEATURES["table_features"][0]
    note = rd.table_note(row, UC_TABLE, True)
    assert note == "行×列：4×3；合并格：1；异常流条目：1"
    # 主事件流中提到"异常流E1"与异常流行同属一个条目 → 去重计数
    assert rd.table_note(None, UC_TABLE, True) == "异常流条目：1"
    assert rd.table_note(None, "<table><tr><td>x</td></tr></table>", False) == "—"


def test_text_note_from_feature_sentences():
    note = rd.text_note(SYNTH_FEATURES["text_features"], "数据库初始化用例场景，见表3所示。")
    assert note == "语句：1；数量词：1；引用：1"
    assert rd.text_note(SYNTH_FEATURES["text_features"], "完全无关的句子。") == "—"


def test_image_note_diagram_counts():
    note = rd.image_note(SYNTH_FEATURES["diagrams"], "图2 数据库初始化流程图")
    assert note == "图节点：5；连线：4"
    assert rd.image_note(SYNTH_FEATURES["diagrams"], "图3 毫无关联的图") == "—"
    assert rd.image_note({}, "图2 数据库初始化流程图") == "—"


def test_caption_stem_strips_figure_number_and_type():
    assert rd.caption_stem("图 5数据库初始化流程图") == "数据库初始化"
    assert rd.caption_stem("图3 SQL访问用例图") == "SQL访问"
    assert rd.caption_stem("图1") == ""


# ------------------------------------------------------------- payload与HTML

@pytest.fixture()
def office_dir(tmp_path: Path) -> Path:
    images = tmp_path / "office" / "images"
    images.mkdir(parents=True)
    (images / "fig_001.png").write_bytes(PNG_BYTES)
    (images / "fig_002.png").write_bytes(PNG_BYTES)
    return tmp_path / "office"


def _payload(office_dir: Path) -> dict:
    return rd.build_dossier_payload(
        "T1", "T1测试文档", BLOCKS, office_dir, SYNTH_FEATURES,
        [{"id": "T1", "name": "T1测试文档", "file": "requirement_dossier_T1.html"}],
    )


def test_build_dossier_payload_structure(office_dir: Path):
    payload = _payload(office_dir)
    assert payload["doc"]["id"] == "T1"
    assert payload["defaultLeaf"] == "3.2.1.1.1.1"
    assert set(payload["leaves"]) == {"3.2.1.1.1.1", "3.2.1.1.1.2"}
    # 只有叶子区间内引用的图片才嵌入(fig_001属于非叶子区间)
    assert set(payload["images"]) == {"images/fig_002.png"}
    data_uri = payload["images"]["images/fig_002.png"]
    assert data_uri.startswith("data:image/png;base64,")
    assert base64.b64decode(data_uri.split(",", 1)[1]) == PNG_BYTES


def test_build_dossier_default_leaf_content(office_dir: Path):
    leaf = _payload(office_dir)["leaves"]["3.2.1.1.1.1"]
    assert leaf["title"] == "3.2.1.1.1.1 数据库操作-数据库初始化（TT-GN-SQLFW-SJKCZ-SJKCSH）"
    assert leaf["breadcrumb"] == {
        "crumbs": ["3.2.1 SQL访问", "3.2.1.1 SQL访问-数据库操作"],
        "leaf": "数据库初始化",
        "id": "TT-GN-SQLFW-SJKCZ-SJKCSH",
    }
    assert [f["kind"] for f in leaf["fragments"]] == ["text", "table", "text", "image"]
    # 原文一字不改
    assert leaf["fragments"][0]["html"] == "数据库初始化用例场景，见表3所示。"
    assert leaf["fragments"][1]["html"] == UC_TABLE
    # 侧栏注脚
    assert leaf["fragments"][1]["note"] == "行×列：4×3；合并格：1；异常流条目：1"
    assert leaf["fragments"][3]["note"] == "图节点：5；连线：4"
    # 上下游
    assert leaf["upstream"]["parent_heading"] == "3.2.1.1 SQL访问-数据库操作（TT-GN-SQLFW-SJKCZ）"
    assert leaf["upstream"]["entries"][0]["match"] == "ID后缀"
    assert leaf["qualification"]["fallback_of"] is None
    assert leaf["trace"]["fallback_of"] is None


def test_render_html_self_contained_island(office_dir: Path):
    payload = _payload(office_dir)
    html_doc = rd.render_html(payload)
    for marker in ('id="doc-select"', 'id="crumbs"', 'id="chips"', 'id="nav-tree"',
                   'id="dossier"', "dossier-data"):
        assert marker in html_doc
    island = re.search(
        r'<script type="application/json" id="dossier-data">(.*?)</script>',
        html_doc, re.S,
    )
    assert island
    parsed = json.loads(island.group(1).replace("<\\/", "</"))
    assert parsed["defaultLeaf"] == "3.2.1.1.1.1"
    assert parsed["leaves"]["3.2.1.1.1.1"]["fragments"][1]["html"] == UC_TABLE
    assert "data:image/png;base64," in html_doc
    assert "http://" not in html_doc and "https://" not in html_doc
    # 标题无占位残留
    assert "{css}" not in html_doc and "{js}" not in html_doc and "{data}" not in html_doc


# ------------------------------------------------------------- 真实doc04快照

DOC04_CONTENT = (
    BASE / "data/gjb_438c/mineru_standard/04数据统一访问服务软件需求规格说明-终稿/office"
    / "04数据统一访问服务软件需求规格说明-终稿_content_list.json"
)

pytestmark_real = pytest.mark.skipif(
    not DOC04_CONTENT.exists(), reason="doc04 content_list 数据资产缺失"
)


@pytest.mark.slow
@pytestmark_real
def test_doc04_real_snapshot():
    doc_dir, office, content_list_path = rd.find_doc_office("04")
    blocks = rd.read_json(content_list_path)
    payload = rd.build_dossier_payload(
        "04", doc_dir.name, blocks, office, rd.load_features("04"), rd.list_docs()
    )

    def count(nodes):
        return sum(1 + count(n["children"]) for n in nodes)

    def count_leaf(nodes):
        return sum(1 if n["leaf"] else count_leaf(n["children"]) for n in nodes)

    assert count(payload["tree"]) == 57
    assert count_leaf(payload["tree"]) == 47
    assert len(payload["leaves"]) == 47

    leaf = payload["leaves"]["3.2.1.1.1.1"]
    assert leaf["title"] == "3.2.1.1.1.1 数据库操作-数据库初始化（PZXQ-GN-SQLFW-SJKCZ-SJKCSH）"
    assert leaf["breadcrumb"]["crumbs"] == ["3.2.1 SQL访问", "3.2.1.1 SQL访问-数据库操作"]
    assert leaf["breadcrumb"]["leaf"] == "数据库初始化"

    ev = {e["key"]: e["ok"] for e in leaf["evidence"]}
    assert ev == {
        "body": True,
        "usecase_table": True,
        "flow_image": True,
        "capability_row": True,
        "qualification_row": False,
        "trace_row": False,
    }
    qual = leaf["qualification"]
    assert qual["fallback_of"] == "3.2.1"
    assert "A、B、D" in qual["entries"][0]["rows"][0]
    trace = leaf["trace"]
    assert trace["fallback_of"] == "3.2.1"
    assert len(trace["entries"]) == 2
    upstream = leaf["upstream"]["entries"][0]
    assert upstream["label"] == "表4 数据库操作所有能力标识"
    assert upstream["match"] == "ID后缀"
    assert "PZXQ-GN-SJKCZ-SJKCSH" in upstream["rows"][0]

    assert payload["images"]["images/fig_005.png"].startswith("data:image/png;base64,")
    # 原文完整性: 正文/用例表关键片段逐字保留
    frag_html = " ".join(
        f["html"] for f in leaf["fragments"] if f["kind"] in ("text", "table")
    )
    assert "数据库初始化用例场景，见表5所示。" in frag_html
    assert "Use Case 名称：数据库初始化" in frag_html
    assert "异常流E1：系统提示初始化失败，用例结束。" in frag_html
