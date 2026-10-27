"""render_extraction_atlas 提取图谱内核的确定性测试（合成content_list + 合成特征）.

合成小文档复刻GJB真实结构(需求树3.2.1→3.2.1.1→双叶子/能力标识表/用例表/
第4章合格性表/第5章追溯表 + sentences/claim_slot/predicates/refs/tables_v2/
table_features/entity_type), 聚焦:
- 需求树标题解析正则(spec严格版 + 宽松版兜底, 非ID标题拒绝)
- 叶子区间切分(下一同级/上级标题为界)
- 六路证据状态计算(直接/回退/缺失三态)
- tables_v2表 → content_list块 的页号+页内序对齐
- Tab3提取单元按原文块顺序交错组装(句子/表行/图caption)
- 12字段填充逻辑(谓词优先级/操作符/值/单位/模态词/否定/条件/引用/实体/行角色/需求ID)
- payload装配与自包含HTML渲染(三Tab/base64图/零外链)
真实doc04快照数字(47叶子/759单元/六路统计)单列slow测试, 数据缺失时跳过。
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

import render_extraction_atlas as ra  # noqa: E402

PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
PNG_BYTES = base64.b64decode(PNG_1X1)

CAP_TABLE_DOMAIN = (
    "<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th></tr></thead>"
    "<tbody><tr><td><p>1</p></td><td><p>数据库操作</p></td>"
    "<td><p>TT-GN-SQLFW-SJKCZ</p></td>"
    "<td><p>数据库操作功能包括数据库初始化等</p></td></tr></tbody></table>"
)
CAP_TABLE_LEAVES = (
    "<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th></tr></thead>"
    "<tbody>"
    "<tr><td><p>1</p></td><td><p>数据库初始化</p></td><td><p>TT-GN-SJKCZ-SJKCSH</p></td>"
    "<td><p>初始化数据库</p></td></tr>"
    "<tr><td><p>2</p></td><td><p>数据库关闭</p></td><td><p>TT-GN-SJKCZ-BJKGB</p></td>"
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
    {"type": "text", "text": "1 范围", "text_level": 1, "page_idx": 0},
    {"type": "image", "image_caption": [], "image_path": "images/fig_000.png", "page_idx": 0},
    {"type": "text", "text": "2 引用文档", "text_level": 1, "page_idx": 0},
    {"type": "text", "text": "3 需求", "text_level": 1, "page_idx": 0},
    {"type": "text", "text": "3.2 CSCI能力需求", "text_level": 2, "page_idx": 0},
    {"type": "text", "text": "3.2.1 SQL访问（TT-GN-SQLFW）", "text_level": 3, "page_idx": 1},
    {"type": "text", "text": "SQL访问功能应提供数据库操作，见图1。", "page_idx": 1},
    {
        "type": "image",
        "image_caption": ["图1 SQL访问用例图"],
        "image_path": "images/fig_001.png",
        "page_idx": 1,
    },
    {
        "type": "table",
        "table_caption": ["表1 SQL访问所有能力标识"],
        "table_body": CAP_TABLE_DOMAIN,
        "page_idx": 2,
    },
    {
        "type": "text",
        "text": "3.2.1.1 SQL访问-数据库操作（TT-GN-SQLFW-SJKCZ）",
        "text_level": 4,
        "page_idx": 2,
    },
    {
        "type": "table",
        "table_caption": ["表2 数据库操作所有能力标识"],
        "table_body": CAP_TABLE_LEAVES,
        "page_idx": 3,
    },
    {
        "type": "text",
        "text": "3.2.1.1.1.1 数据库操作-数据库初始化（TT-GN-SQLFW-SJKCZ-SJKCSH）",
        "text_level": 6,
        "page_idx": 4,
    },
    {
        "type": "text",
        "text": "系统应支持数据库初始化，初始化时间不大于30s，当系统出现问题时自动回退。",
        "page_idx": 4,
    },
    {
        "type": "table",
        "table_caption": ["表3 数据库初始化用例描述"],
        "table_body": UC_TABLE,
        "page_idx": 5,
    },
    {
        "type": "image",
        "image_caption": ["图2 数据库初始化流程图"],
        "image_path": "images/fig_002.png",
        "page_idx": 5,
    },
    {
        "type": "text",
        "text": "3.2.1.1.1.2 数据库操作-数据库关闭（TT-GN-SQLFW-SJKCZ- BJKGB）",
        "text_level": 6,
        "page_idx": 6,
    },
    {"type": "text", "text": "数据库关闭用例场景见表4，关闭失败时用户不能直接断电。", "page_idx": 6},
    {"type": "text", "text": "4 合格性规定", "text_level": 1, "page_idx": 9},
    {
        "type": "table",
        "table_caption": ["表80 合格性规定"],
        "table_body": QUAL_TABLE,
        "page_idx": 9,
    },
    {"type": "text", "text": "5 需求可追踪性", "text_level": 1, "page_idx": 10},
    {
        "type": "table",
        "table_caption": ["表81 需求的正向追踪性"],
        "table_body": TRACE_TABLE,
        "page_idx": 10,
    },
    {"type": "text", "text": "6 注释", "text_level": 1, "page_idx": 11},
    {"type": "text", "text": "无。", "page_idx": 11},
]


def _cells(rows: list[list[str]]) -> list[dict[str, object]]:
    return [
        {"row": r, "col": c, "text": text}
        for r, row in enumerate(rows)
        for c, text in enumerate(row)
    ]


TABLES_V2 = [
    {
        "table_id": "T-T1-0000",
        "doc_id": "T1",
        "section": "3.2.1",
        "page": 2,
        "caption_raw": "表1 SQL访问所有能力标识",
        "thead_rows": 1,
        "cells": _cells(
            [
                ["序号", "Use case名称", "项目唯一标识符", "需求描述"],
                ["1", "数据库操作", "TT-GN-SQLFW-SJKCZ", "数据库操作功能包括数据库初始化等"],
            ]
        ),
    },
    {
        "table_id": "T-T1-0001",
        "doc_id": "T1",
        "section": "3.2.1.1",
        "page": 3,
        "caption_raw": "表2 数据库操作所有能力标识",
        "thead_rows": 1,
        "cells": _cells(
            [
                ["序号", "Use case名称", "项目唯一标识符", "需求描述"],
                ["1", "数据库初始化", "TT-GN-SJKCZ-SJKCSH", "初始化数据库"],
                ["2", "数据库关闭", "TT-GN-SJKCZ-BJKGB", "关闭数据库"],
            ]
        ),
    },
    {
        "table_id": "T-T1-0002",
        "doc_id": "T1",
        "section": "3.2.1.1.1.1",
        "page": 5,
        "caption_raw": "表3 数据库初始化用例描述",
        "thead_rows": 0,
        "cells": _cells(
            [
                ["Use Case 名称：数据库初始化", "Actors：应用软件"],
                ["概述：描述数据库初始化的过程"],
                ["主事件流：如果失败则执行异常流E1"],
                ["异常流E1：系统提示初始化失败，用例结束。"],
            ]
        ),
    },
    {
        "table_id": "T-T1-0003",
        "doc_id": "T1",
        "section": "4",
        "page": 9,
        "caption_raw": "表80 合格性规定",
        "thead_rows": 1,
        "cells": _cells(
            [
                ["需求名称/标识", "本文档的章节号", "合格性方法", "合格性级别"],
                ["数据库初始化", "3.2.1.1.1.1", "A", "a"],
                ["SQL访问", "3.2.1", "B", "b"],
            ]
        ),
    },
    {
        "table_id": "T-T1-0004",
        "doc_id": "T1",
        "section": "5",
        "page": 10,
        "caption_raw": "表81 需求的正向追踪性",
        "thead_rows": 1,
        "cells": _cells(
            [
                ["任务书名称/标识", "任务书章节号", "本文档的名称/标识", "本文档的章节号", "跟踪说明"],
                ["原生SQL访问", "4.1.1 b)", "SQL访问", "3.2.1", ""],
                ["数据库初始化", "4.1.1 c)", "数据库初始化", "3.2.1.1.1.1", ""],
            ]
        ),
    },
]

TABLE_FEATURES = [
    {
        "doc_id": "T1",
        "table_id": "T-T1-0001",
        "row_roles": [
            {"row_index": 0, "role_candidate": "index_row"},
            {"row_index": 1, "role_candidate": "data_row"},
            {"row_index": 2, "role_candidate": "data_row"},
        ],
        "requirement_id_cells": [
            {"row_index": 1, "col_index": 2, "value": "TT-GN-SJKCZ-SJKCSH"},
            {"row_index": 2, "col_index": 2, "value": "TT-GN-SJKCZ-BJKGB"},
        ],
        "parameter_cells": [
            {"row_index": 1, "col_index": 1, "predicate_key": "availability", "value": "数据库初始化"}
        ],
    },
    {
        "doc_id": "T1",
        "table_id": "T-T1-0002",
        "row_roles": [
            {"row_index": 0, "role_candidate": "usecase_section_row"},
            {"row_index": 1, "role_candidate": "data_row"},
            {"row_index": 2, "role_candidate": "data_row"},
            {"row_index": 3, "role_candidate": "data_row"},
        ],
        "requirement_id_cells": [],
        "parameter_cells": [],
    },
]

SENTENCES = [
    {
        "claim_id": "CLM-A",
        "doc_id": "T1",
        "section": "3.2.1",
        "text": "SQL访问功能应提供数据库操作，见图1。",
        "span": {"block_idx": 6, "start": 0, "end": 14},
        "negations": [],
        "conditions": [],
        "has_condition": False,
        "scope_entity": [{"entity": "数据库操作", "pos": 11, "raw": "数据库操作"}],
    },
    {
        "claim_id": "CLM-B",
        "doc_id": "T1",
        "section": "3.2.1.1.1.1",
        "text": "系统应支持数据库初始化，初始化时间不大于30s，当系统出现问题时自动回退。",
        "span": {"block_idx": 12, "start": 0, "end": 20},
        "negations": [],
        "conditions": [{"cond_text": "系统出现问题", "pattern": "当…时", "pos": 28, "raw": "当系统出现问题时"}],
        "has_condition": True,
        "scope_entity": [],
    },
    {
        "claim_id": "CLM-C",
        "doc_id": "T1",
        "section": "3.2.1.1.1.2",
        "text": "数据库关闭用例场景见表4，关闭失败时用户不能直接断电。",
        "span": {"block_idx": 16, "start": 0, "end": 12},
        "negations": [{"pos": 21, "word": "不能"}],
        "conditions": [],
        "has_condition": False,
        "scope_entity": [],
    },
]

SLOTS = [
    {
        "claim_id": "CLM-A",
        "doc_id": "T1",
        "kind": "text_claim",
        "operator": "",
        "object_value": None,
        "predicate_candidate": "提供",
        "unit_raw": "",
        "section": "3.2.1",
    },
    {
        "claim_id": "CLM-B",
        "doc_id": "T1",
        "kind": "text_claim",
        "operator": "不大于",
        "object_value": 30,
        "predicate_candidate": "",
        "unit_raw": "s",
        "section": "3.2.1.1.1.1",
    },
    {
        "claim_id": "CLM-C",
        "doc_id": "T1",
        "kind": "text_claim",
        "operator": "",
        "object_value": None,
        "predicate_candidate": "提供",
        "unit_raw": "",
        "section": "3.2.1.1.1.2",
    },
]

PREDICATES = [
    {
        "claim_id": "CLM-A",
        "doc_id": "T1",
        "kind": "text_claim",
        "predicate_function": {"verb": "提供", "object_stripped": "数据库操作"},
    },
    {
        "claim_id": "CLM-B",
        "doc_id": "T1",
        "kind": "text_claim",
        "predicate_function": {"verb": "支持", "object_stripped": "数据库初始化"},
    },
]

REFS = [
    {"claim_id": "CLM-A", "doc_id": "T1", "ref": "见图1", "target_id": "IMG-T1-0000", "status": "resolved"},
    {"claim_id": "CLM-B", "doc_id": "T1", "ref": "见表3", "target_id": "T-T1-0002", "status": "resolved"},
    {"claim_id": "CLM-C", "doc_id": "T1", "ref": "见图9", "target_id": "", "status": "unresolved"},
]

ENTITY_ROWS = [
    {"doc_id": "T1", "occurrence_id": "CLM-A", "entity_type": "功能"},
    {"doc_id": "T1", "occurrence_id": "CLM-B", "entity_type": "功能"},
    {"doc_id": "T1", "occurrence_id": "CLM-C", "entity_type": "接口"},
    {"doc_id": "T1", "occurrence_id": "TT-GN-SJKCZ-SJKCSH", "entity_type": "功能"},
]

FEATS = {
    "sentences": SENTENCES,
    "refs": REFS,
    "tables_v2": TABLES_V2,
    "slots": SLOTS,
    "table_features": TABLE_FEATURES,
    "predicates": PREDICATES,
    "entities": {r["occurrence_id"]: r["entity_type"] for r in ENTITY_ROWS},
}


def _tree():
    return ra.build_tree(BLOCKS)


def _leaf(num: str) -> dict:
    for node in _tree():
        if node["num"] == num:
            return node
    raise AssertionError(f"节点不存在: {num}")


# ------------------------------------------------------------- 标题解析正则

def test_parse_req_heading_spec_regex():
    parsed = ra.parse_req_heading("3.2.1.1.1.1 数据库操作-数据库初始化（TT-GN-SQLFW-SJKCZ-SJKCSH）")
    assert parsed == ("3.2.1.1.1.1", "数据库操作-数据库初始化", "TT-GN-SQLFW-SJKCZ-SJKCSH")
    # spec正则为前缀匹配: 括号后允许尾随文字
    parsed2 = ra.parse_req_heading("3.2.1 SQL访问（TT-GN-SQLFW）概述")
    assert parsed2 is not None and parsed2[2] == "TT-GN-SQLFW"


def test_parse_req_heading_loose_internal_space():
    parsed = ra.parse_req_heading("3.2.1.1.1.2 数据库操作-数据库关闭（TT-GN-SQLFW-SJKCZ- BJKGB）")
    assert parsed is not None
    assert parsed[2] == "TT-GN-SQLFW-SJKCZ-BJKGB"


@pytest.mark.parametrize(
    "text",
    [
        "3.2 CSCI能力需求",
        "1.1 标识",
        "4 合格性规定",
        "3.2.1 SQL访问（无ID括号内容）",
        "3.9 计算机硬件需求（含GPU）",
    ],
)
def test_parse_req_heading_rejects_non_requirement(text):
    assert ra.parse_req_heading(text) is None


# ------------------------------------------------------------- 需求树与叶子区间

def test_build_tree_structure():
    nodes = _tree()
    assert [n["num"] for n in nodes] == ["3.2.1", "3.2.1.1", "3.2.1.1.1.1", "3.2.1.1.1.2"]
    by_num = {n["num"]: n for n in nodes}
    assert by_num["3.2.1"]["parent"] is None
    assert by_num["3.2.1"]["children"] == ["3.2.1.1"]
    assert by_num["3.2.1.1.1.1"]["parent"] == "3.2.1.1"
    leaves = [n["num"] for n in nodes if not n["children"]]
    assert leaves == ["3.2.1.1.1.1", "3.2.1.1.1.2"]


def test_leaf_interval_bounds():
    assert ra.leaf_interval(BLOCKS, _leaf("3.2.1.1.1.1")) == (12, 15)
    assert ra.leaf_interval(BLOCKS, _leaf("3.2.1.1.1.2")) == (16, 17)


# ------------------------------------------------------------- 表→块映射

def test_map_tables_to_blocks_page_alignment():
    mapping = ra.map_tables_to_blocks(BLOCKS, TABLES_V2)
    assert {bi: t["table_id"] for bi, t in mapping.items()} == {
        8: "T-T1-0000",
        10: "T-T1-0001",
        13: "T-T1-0002",
        18: "T-T1-0003",
        20: "T-T1-0004",
    }


def test_map_tables_to_blocks_order_fallback():
    tables = [dict(t, page=99) for t in TABLES_V2]
    mapping = ra.map_tables_to_blocks(BLOCKS, tables)
    # 页号无法对齐时退化为全局顺序配对(同为文档序)
    assert list(mapping) == [8, 10, 13, 18, 20]
    assert [t["table_id"] for t in mapping.values()] == [
        "T-T1-0000", "T-T1-0001", "T-T1-0002", "T-T1-0003", "T-T1-0004",
    ]


# ------------------------------------------------------------- 六路状态

def _view(num: str, office_dir: Path | None = None) -> dict:
    payload = _payload(office_dir) if office_dir else _payload_no_images()
    return payload["leaves"][num]


def _payload_no_images() -> dict:
    return ra.build_atlas_payload(
        "T1", "T1测试文档", BLOCKS, Path("nowhere-office"), FEATS
    )


def _payload(office_dir: Path) -> dict:
    return ra.build_atlas_payload("T1", "T1测试文档", BLOCKS, office_dir, FEATS)


@pytest.fixture()
def office_dir(tmp_path: Path) -> Path:
    images = tmp_path / "office" / "images"
    images.mkdir(parents=True)
    (images / "fig_002.png").write_bytes(PNG_BYTES)
    return tmp_path / "office"


def test_route_states_leaf1_all_direct():
    view = _view("3.2.1.1.1.1")
    assert view["states"] == {
        "body": "direct",
        "usecase": "direct",
        "flow": "direct",
        "capability": "direct",
        "qualification": "direct",
        "trace": "direct",
    }


def test_route_states_leaf2_mixed():
    view = _view("3.2.1.1.1.2")
    assert view["states"] == {
        "body": "direct",
        "usecase": "missing",
        "flow": "missing",
        "capability": "direct",
        "qualification": "fallback",
        "trace": "fallback",
    }
    assert view["qualification"]["fallback_of"] == "3.2.1"
    assert view["trace"]["fallback_of"] == "3.2.1"
    entry = view["capability"]["entries"][0]
    assert entry["match"] == "ID后缀"
    assert "TT-GN-SJKCZ-BJKGB" in entry["rows"][0]


def test_matrix_route_stats_and_broken_top():
    payload = _payload_no_images()
    stats = {r["key"]: r for r in payload["matrix"]["routeStats"]}
    assert stats["body"] == {
        "key": "body", "label": "正文", "direct": 2, "fallback": 0, "missing": 0,
    }
    assert stats["usecase"]["direct"] == 1 and stats["usecase"]["missing"] == 1
    assert stats["flow"]["direct"] == 1 and stats["flow"]["missing"] == 1
    assert stats["capability"]["direct"] == 2
    assert stats["qualification"]["direct"] == 1 and stats["qualification"]["fallback"] == 1
    assert stats["trace"]["direct"] == 1 and stats["trace"]["fallback"] == 1
    broken = payload["matrix"]["brokenTop"]
    assert [b["num"] for b in broken] == ["3.2.1.1.1.2"]
    assert broken[0]["missing"] == 2


# ------------------------------------------------------------- Tab3单元组装

def test_build_units_order_and_kinds():
    units = ra.build_units(BLOCKS, FEATS, {n["num"]: n for n in _tree()})
    kinds = [(u["k"], u["src"]) for u in units]
    assert kinds == [
        ("image", "1·fig_000.png"),
        ("sentence", "3.2.1·块6·句0-14"),
        ("image", "3.2.1·图1"),
        ("table_row", "3.2.1·表1·行1"),
        ("table_row", "3.2.1.1·表2·行1"),
        ("table_row", "3.2.1.1·表2·行2"),
        ("sentence", "3.2.1.1.1.1·块12·句0-20"),
        ("table_row", "3.2.1.1.1.1·表3·行0"),
        ("table_row", "3.2.1.1.1.1·表3·行1"),
        ("table_row", "3.2.1.1.1.1·表3·行2"),
        ("table_row", "3.2.1.1.1.1·表3·行3"),
        ("image", "3.2.1.1.1.1·图2"),
        ("sentence", "3.2.1.1.1.2·块16·句0-12"),
        ("table_row", "4·表80·行1"),
        ("table_row", "4·表80·行2"),
        ("table_row", "5·表81·行1"),
        ("table_row", "5·表81·行2"),
    ]


def test_sentence_unit_fields():
    units = ra.build_units(BLOCKS, FEATS, {n["num"]: n for n in _tree()})
    by_src = {u["src"]: u for u in units}

    a = by_src["3.2.1·块6·句0-14"]
    assert a["text"] == "SQL访问功能应提供数据库操作，见图1。"
    assert a["f"]["rid"] == "TT-GN-SQLFW"  # 3.2.1自身即需求树节点
    assert a["f"]["pred"] == "提供｜数据库操作"  # predicates优先
    assert a["f"]["modal"] == "应"
    assert a["f"]["ref"] == "见图1→IMG-T1-0000"
    assert a["f"]["ent"] == "功能"
    assert a["f"]["scope"] == "数据库操作"

    b = by_src["3.2.1.1.1.1·块12·句0-20"]
    assert b["f"]["rid"] == "TT-GN-SQLFW-SJKCZ-SJKCSH"
    assert b["f"]["pred"] == "支持｜数据库初始化"
    assert b["f"]["op"] == "不大于"
    assert b["f"]["val"] == "30"
    assert b["f"]["unit"] == "s"
    assert b["f"]["cond"] == "系统出现问题"
    assert b["f"]["ref"] == "见表3→T-T1-0002"

    c = by_src["3.2.1.1.1.2·块16·句0-12"]
    assert c["f"]["pred"] == "提供"  # 无predicate时回退predicate_candidate
    assert c["f"]["ref"] == "见图9→未解析"
    assert c["f"]["neg"] == "不能"
    assert c["f"]["ent"] == "接口"


def test_table_row_unit_fields():
    units = ra.build_units(BLOCKS, FEATS, {n["num"]: n for n in _tree()})
    by_src = {u["src"]: u for u in units}

    row1 = by_src["3.2.1.1·表2·行1"]
    assert row1["text"] == "1 | 数据库初始化 | TT-GN-SJKCZ-SJKCSH"
    assert row1["f"]["rid"] == "TT-GN-SJKCZ-SJKCSH"  # requirement_id_cells
    assert row1["f"]["role"] == "data_row"
    assert row1["f"]["pred"] == "availability"  # parameter_cells
    assert row1["f"]["val"] == "数据库初始化"
    assert row1["f"]["ent"] == "功能"  # 实体类型经需求ID关联

    uc0 = by_src["3.2.1.1.1.1·表3·行0"]
    assert uc0["f"]["role"] == "usecase_section_row"
    assert uc0["f"]["rid"] == "TT-GN-SQLFW-SJKCZ-SJKCSH"  # 表section上溯到叶子节点

    domain = by_src["3.2.1·表1·行1"]
    assert domain["f"]["rid"] == "TT-GN-SQLFW"  # 无requirement_id_cells时section上溯
    assert domain["f"]["role"] == ""


def test_image_unit_and_no_extraction():
    units = ra.build_units(BLOCKS, FEATS, {n["num"]: n for n in _tree()})
    by_src = {u["src"]: u for u in units}
    head = by_src["1·fig_000.png"]
    assert head["text"] == "（无题注）"
    assert not any(head["f"].values())  # → 右侧显示"（无提取）"
    fig1 = by_src["3.2.1·图1"]
    assert fig1["text"] == "图1 SQL访问用例图"
    assert fig1["f"]["rid"] == "TT-GN-SQLFW"


# ------------------------------------------------------------- 模态词抽取

def test_extract_modals_basic_and_order():
    assert ra.extract_modals("系统应支持数据库初始化。") == ["应"]
    assert ra.extract_modals("必须完成且不能中断，禁止修改。") == ["必须", "不能", "禁止"]
    assert ra.extract_modals("该接口可以扩展，应答时间尽量短。") == ["可以", "尽量"]
    assert ra.extract_modals("价格便宜且适宜部署，不可靠。") == []


def test_extract_modals_filters_compound_words():
    # 应用/适应/对应/可靠/可能等复合词中的单字模态词不算
    assert ra.extract_modals("应用软件应当适应多种环境，确保可靠运行。") == ["应当"]
    assert ra.extract_modals("对应功能可能失效。") == []


# ------------------------------------------------------------- stats与payload

def test_compute_stats_real_numbers():
    units = ra.build_units(BLOCKS, FEATS, {n["num"]: n for n in _tree()})
    stats = ra.compute_stats(units, SENTENCES, REFS)
    assert stats["unitsTotal"] == 17
    assert stats["sentenceUnits"] == 3
    assert stats["tableRowUnits"] == 11
    assert stats["imageUnits"] == 3
    assert stats["predicateFilled"] == 4  # CLM-A/B/C + 表2行1(availability)
    assert stats["valueFilled"] == 2  # CLM-B的30 + 表2行1
    assert stats["valueWithUnit"] == 1
    assert stats["conditionSentences"] == 1
    assert stats["refTotal"] == 3 and stats["refResolved"] == 2
    assert stats["sections"][:5] == ["1", "3.2.1", "3.2.1.1", "3.2.1.1.1.1", "3.2.1.1.1.2"]


def test_build_atlas_payload_structure(office_dir: Path):
    payload = _payload(office_dir)
    assert payload["doc"] == {"id": "T1", "name": "T1测试文档"}
    assert payload["defaultLeaf"] == "3.2.1.1.1.1"
    assert set(payload["leaves"]) == {"3.2.1.1.1.1", "3.2.1.1.1.2"}
    # 只有叶子区间内的图嵌入base64(fig_002), 区间外(fig_000/fig_001)不嵌入
    assert set(payload["images"]) == {"images/fig_002.png"}
    assert payload["images"]["images/fig_002.png"].startswith("data:image/png;base64,")
    assert base64.b64decode(payload["images"]["images/fig_002.png"].split(",", 1)[1]) == PNG_BYTES
    # Tab2六卡: 叶子1区间内正文1段+用例表1张+图1张
    leaf = payload["leaves"]["3.2.1.1.1.1"]
    assert [fr["t"] for fr in leaf["body"]] == ["p"]
    assert leaf["body"][0]["h"] == BLOCKS[12]["text"]
    assert leaf["usecases"][0]["caption"] == "表3 数据库初始化用例描述"
    assert "Use Case 名称：数据库初始化" in leaf["usecases"][0]["html"]
    assert leaf["images"][0]["path"] == "images/fig_002.png"


# ------------------------------------------------------------- HTML渲染与自包含

def test_render_html_three_tabs_and_island(office_dir: Path):
    payload = _payload(office_dir)
    html_doc = ra.render_html(payload)
    for tab in ("tab1", "tab2", "tab3"):
        assert f'id="{tab}"' in html_doc
        assert f'data-tab="{tab}"' in html_doc
    assert "atlas-data" in html_doc and "（无提取）" in html_doc
    island = re.search(
        r'<script type="application/json" id="atlas-data">(.*?)</script>',
        html_doc, re.S,
    )
    assert island
    parsed = json.loads(island.group(1).replace("<\\/", "</"))
    assert len(parsed["units"]) == 17
    assert len(parsed["matrix"]["leaves"]) == 2
    assert "data:image/png;base64," in html_doc
    # 零外链: 无script/link/iframe外引, 无http(s)资源地址
    assert not re.search(r"<script\b[^>]*\bsrc=", html_doc, re.I)
    assert not re.search(r"<link\b", html_doc, re.I)
    assert not re.search(r"(?:src|href)\s*=\s*[\"']?https?://", html_doc, re.I)
    assert "{css}" not in html_doc and "{js}" not in html_doc and "{data}" not in html_doc


def test_verify_html_assertions(office_dir: Path):
    payload = _payload(office_dir)
    html_doc = ra.render_html(payload)
    checks = ra.verify_html(html_doc, payload)
    assert checks == {
        "tabs": 3,
        "matrix_rows": 2,
        "unit_rows": 17,
        "unit_kinds": {"sentence": 3, "table_row": 11, "image": 3},
        "images_embedded": 1,
        "external_refs": 0,
    }


def test_verify_html_rejects_external_resource(office_dir: Path):
    payload = _payload(office_dir)
    html_doc = ra.render_html(payload).replace(
        "</head>", '<script src="https://cdn.example.com/x.js"></script></head>'
    )
    with pytest.raises(AssertionError):
        ra.verify_html(html_doc, payload)


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
    doc_dir, office, content_list_path = ra.find_doc_office("04")
    blocks = ra.read_json(content_list_path)
    feats = ra.load_features("04")
    payload = ra.build_atlas_payload("04", doc_dir.name, blocks, office, feats)

    assert len(payload["matrix"]["leaves"]) == 47
    assert payload["defaultLeaf"] == "3.2.1.1.1.1"
    stats = payload["stats"]
    assert stats["unitsTotal"] == 759
    assert (stats["sentenceUnits"], stats["tableRowUnits"], stats["imageUnits"]) == (152, 559, 48)
    assert stats["predicateFilled"] == 82
    assert stats["valueFilled"] == 165
    assert stats["valueWithUnit"] == 0
    assert stats["conditionSentences"] == 1
    assert (stats["refTotal"], stats["refResolved"]) == (110, 84)
    assert len(payload["images"]) == 34

    route = {r["key"]: r for r in payload["matrix"]["routeStats"]}
    assert (route["body"]["direct"], route["body"]["missing"]) == (47, 0)
    assert (route["usecase"]["direct"], route["usecase"]["missing"]) == (35, 12)
    assert (route["flow"]["direct"], route["flow"]["missing"]) == (34, 13)
    assert (route["capability"]["direct"], route["capability"]["fallback"]) == (33, 14)
    assert (route["qualification"]["direct"], route["qualification"]["fallback"]) == (0, 35)
    assert (route["trace"]["direct"], route["trace"]["fallback"]) == (3, 44)

    leaf = payload["leaves"]["3.2.1.1.1.1"]
    assert leaf["states"] == {
        "body": "direct",
        "usecase": "direct",
        "flow": "direct",
        "capability": "direct",
        "qualification": "fallback",
        "trace": "fallback",
    }
    # 原文完整性: 正文/用例表关键片段逐字保留, 不加高亮涂色
    body_join = " ".join(fr["h"] for fr in leaf["body"])
    assert "数据库初始化用例场景" in body_join
    uc_html = " ".join(u["html"] for u in leaf["usecases"])
    assert "Use Case 名称：数据库初始化" in uc_html

    html_doc = ra.render_html(payload)
    checks = ra.verify_html(html_doc, payload)
    assert checks["matrix_rows"] == 47
    assert checks["unit_rows"] == 759
    assert checks["images_embedded"] == 34
