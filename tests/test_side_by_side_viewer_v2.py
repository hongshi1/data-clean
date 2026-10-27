"""side_by_side_viewer_v2 数据组装逻辑的确定性测试（合成数据）.

不加载模型、不读真实大文件——真实资产快照由 tests/test_side_by_side_viewer.py
(v1) 与 MANIFEST 守卫；本文件聚焦 v2 新增的组装内核:
span 定位(多层高亮)/表头树构建/箭头方向渲染标记生成/实体badge映射/SVG 简绘图。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

# 1x1 透明 PNG（合法文件, 供 base64 嵌入测试）
PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

SENT_TEXT = "当系统出现故障时，系统应自动切换，不能中断服务。"
BLOCKS = [
    {"type": "text", "text_level": 1, "text": "3.2 功能需求"},
    {"type": "text", "text": SENT_TEXT},
    {
        "type": "image",
        "image_caption": ["图1 测试用例图"],
        "img_path": "images/fig_001.png",
        "page_idx": 1,
    },
    {"type": "table", "table_caption": ["表1 测试表"]},
]


def _mk_units(blocks):
    import render_side_by_side_viewer_v2 as rv

    unit_data = {}
    for i, block in enumerate(blocks):
        if block["type"] not in ("text", "list"):
            continue
        units = []
        for raw in rv.build_units(block):
            raw_san = rv.sanitize_fragment(raw)
            plain, offsets = rv.plain_with_offsets(raw_san)
            units.append({"raw": raw_san, "plain": plain, "offsets": offsets})
        unit_data[i] = units
    return unit_data


def _render_list(blocks):
    out = []
    for i, block in enumerate(blocks):
        if block["type"] in ("text", "list", "table", "image"):
            out.append({"index": i, "block": block, "kind": block["type"], "sec": "3.2"})
    return out


# ------------------------------------------------------------- span 定位


def test_plain_span_to_raw_with_tags():
    from render_side_by_side_viewer_v2 import plain_with_offsets, plain_span_to_raw

    raw = "速度<sub>100</sub>ms 应不超过"
    plain, offsets = plain_with_offsets(raw)
    assert plain == "速度100ms 应不超过"
    p = plain.find("100")
    rs, re_ = plain_span_to_raw(offsets, p, p + 3)
    assert raw[rs:re_] == "100"


def test_sentence_layer_ranges_raw_domain():
    from render_side_by_side_viewer_v2 import sentence_layer_ranges

    sent = {
        "claim_id": "CLM-x1",
        "text": SENT_TEXT,
        "conditions": [{"raw": "当系统出现故障时", "cond_text": "系统出现故障", "pos": 0}],
        "negations": [{"word": "不能", "pos": 17}],
        "scope_entity": [{"entity": "系统", "raw": "系统", "pos": 9}],
    }
    attach = {"rs": 0, "re": len(SENT_TEXT), "domain": "raw", "offsets": None}
    ranges = sentence_layer_ranges(sent, attach)
    by_cls = {r["cls"]: r for r in ranges}
    assert by_cls["v2-claim"]["rs"] == 0 and by_cls["v2-claim"]["re"] == len(SENT_TEXT)
    assert by_cls["v2-claim"]["claim"] == "CLM-x1"
    assert by_cls["v2-cond"]["rs"] == 0 and by_cls["v2-cond"]["re"] == 8
    assert by_cls["v2-neg"]["rs"] == 17 and by_cls["v2-neg"]["re"] == 19
    assert by_cls["v2-scope"]["rs"] == 9 and by_cls["v2-scope"]["re"] == 11


def test_sentence_layer_ranges_pos_fallback_find():
    from render_side_by_side_viewer_v2 import sentence_layer_ranges

    # pos 漂移(不在词首) -> 回退 find 定位
    sent = {"claim_id": "CLM-x2", "text": "服务不得中断。", "negations": [{"word": "不得", "pos": 99}]}
    attach = {"rs": 4, "re": 10, "domain": "raw", "offsets": None}
    ranges = sentence_layer_ranges(sent, attach)
    neg = next(r for r in ranges if r["cls"] == "v2-neg")
    assert neg["rs"] == 4 + 2 and neg["re"] == 4 + 4


def test_render_segmented_layered_merge():
    from render_side_by_side_viewer_v2 import render_segmented

    raw = "系统应自动切换。"
    ranges = [
        {"rs": 0, "re": 8, "cls": "v2-claim", "claim": "CLM-x1", "title": "CLM-x1"},
        {"rs": 2, "re": 3, "cls": "v2-neg", "title": "否定词: 应"},
        {"rs": 6, "re": 8, "cls": "v2-cond", "title": "条件: 切换。"},
    ]
    html, chosen = render_segmented(raw, ranges)
    # 3 层共存: claim 全段 + neg/cond 子段; 段边界 [0,2,3,6,8]
    assert html.count("<mark") == 4
    assert '<mark class="v2-claim"' in html
    assert 'class="v2-claim v2-neg"' in html  # 否定子段同时被 claim 覆盖
    assert 'class="v2-claim v2-cond"' in html
    assert 'data-claim="CLM-x1"' in html
    assert len(chosen) == 3
    # 纯文本段(无范围)不包裹
    html2, _ = render_segmented(raw, [])
    assert html2 == raw


def test_render_segmented_keeps_light_html_and_dedup():
    from render_side_by_side_viewer_v2 import render_segmented

    raw = "带宽<sub>100</sub>Mbps 以上"
    # 范围覆盖完整标签(不在标签中间截断)
    ranges = [
        {"rs": 0, "re": 16, "cls": "v2-claim", "claim": "CLM-1", "title": "CLM-1"},
        # 完全相同的重复范围(两条 sentence 重叠)只保留一份
        {"rs": 0, "re": 16, "cls": "v2-claim", "claim": "CLM-1", "title": "CLM-1"},
    ]
    html, chosen = render_segmented(raw, ranges)
    assert len(chosen) == 1
    assert "<sub>100</sub>" in html
    assert html.startswith('<mark class="v2-claim"')


def test_locate_sentences_primary_and_fallback():
    from render_side_by_side_viewer_v2 import locate_sentences

    blocks = list(BLOCKS)
    render_list = _render_list(blocks)
    unit_data = _mk_units(blocks)
    sentences = [
        {
            "claim_id": "CLM-a",
            "text": SENT_TEXT,
            "span": {"block_idx": 1, "start": 0, "end": len(SENT_TEXT)},
        },
        {  # span 指向异常块 -> find 回退到块1
            "claim_id": "CLM-b",
            "text": "系统应自动切换",
            "span": {"block_idx": 99, "start": 0, "end": 7},
        },
        {  # span 坐标漂移(切片不等) -> find 回退
            "claim_id": "CLM-c",
            "text": "不能中断服务",
            "span": {"block_idx": 1, "start": 3, "end": 9},
        },
    ]
    block_sents, located = locate_sentences(render_list, blocks, sentences, unit_data)
    assert located == {"CLM-a", "CLM-b", "CLM-c"}
    primary = [a for a in block_sents[1] if a["claim_id"] == "CLM-a"]
    assert primary[0]["domain"] == "raw" and primary[0]["rs"] == 0
    fallback = {a["claim_id"]: a for a in block_sents[1]}
    assert fallback["CLM-b"]["domain"] == "plain"
    assert SENT_TEXT[fallback["CLM-b"]["rs"] : fallback["CLM-b"]["re"]] == "系统应自动切换"
    assert SENT_TEXT[fallback["CLM-c"]["rs"] : fallback["CLM-c"]["re"]] == "不能中断服务"


# ------------------------------------------------------------- 表头树构建


def test_header_tree_lines_nested():
    from render_side_by_side_viewer_v2 import header_tree_lines

    tree = {
        "levels": 2,
        "nodes": [
            {"text": "序号", "rowspan": 2, "colspan": 1, "children": []},
            {
                "text": "重要性与关键性等级",
                "rowspan": 1,
                "colspan": 3,
                "children": [
                    {"text": "高级", "rowspan": 1, "colspan": 1, "children": []},
                    {"text": "中级", "rowspan": 1, "colspan": 1, "children": []},
                ],
            },
        ],
    }
    lines = header_tree_lines(tree["nodes"])
    assert lines == [
        (0, "序号", 2, 1),
        (0, "重要性与关键性等级", 1, 3),
        (1, "高级", 1, 1),
        (1, "中级", 1, 1),
    ]
    assert header_tree_lines(None) == []
    assert header_tree_lines([]) == []


def test_header_tree_html_indent_and_meta():
    from render_side_by_side_viewer_v2 import header_tree_html

    html = header_tree_html(
        {
            "levels": 2,
            "nodes": [
                {"text": "等级", "rowspan": 1, "colspan": 2,
                 "children": [{"text": "高级", "rowspan": 1, "colspan": 1, "children": []}]},
            ],
        }
    )
    assert 'class="v2-htree"' in html and "表头树 · 2级" in html
    assert "r1×c2" in html
    assert 'style="margin-left:18px"' in html  # depth 1 缩进
    assert header_tree_html(None) == ""
    assert header_tree_html({"levels": 1, "nodes": []}) == ""


def test_build_table_html_v2_merged_and_coords():
    from render_side_by_side_viewer_v2 import build_table_html_v2

    table_row = {
        "table_id": "T-04-0000",
        "n_rows": 3,
        "n_cols": 2,
        "cells": [
            {"cell_id": "r0c0", "row": 0, "col": 0, "rowspan": 1, "colspan": 1,
             "text": "序号", "is_merged_origin": False},
            # r0c1 合并源 colspan=2 -> 覆盖 r0c2(covered 缺席于 cells)
            {"cell_id": "r0c1", "row": 0, "col": 1, "rowspan": 1, "colspan": 2,
             "text": "等级", "is_merged_origin": True},
            # r1c0 合并源 rowspan=2 -> 覆盖 r2c0
            {"cell_id": "r1c0", "row": 1, "col": 0, "rowspan": 2, "colspan": 1,
             "text": "项目", "is_merged_origin": True},
            # r1c1 缺失 -> gap 补格; r2c1 空文本 -> empty
            {"cell_id": "r2c1", "row": 2, "col": 1, "rowspan": 1, "colspan": 1,
             "text": "", "is_merged_origin": False},
        ],
    }
    html, stats = build_table_html_v2(table_row)
    # 坐标小字: 渲染格 + gap(r1c1 缺格)
    for coord in ("r0c0", "r0c1", "r1c0", "r2c1"):
        assert f'<span class="v2-cc">{coord}</span>' in html
    assert '<td class="v2-gap"><span class="v2-cc">r1c1</span>' in html
    # 被覆盖格不再渲染(r0c2/r2c0 无独立 td)
    assert '<span class="v2-cc">r0c2</span>' not in html
    assert '<span class="v2-cc">r2c0</span>' not in html
    assert 'colspan="2"' in html and 'rowspan="2"' in html
    assert html.count('v2-merged') == 2
    assert 'class="v2-empty-cell"' in html  # r2c1 空文本
    assert stats["merged_origins"] == 2
    assert stats["covered_cells"] == 2 + 2  # colspan2 覆盖2格 + rowspan2 覆盖2格
    assert stats["empty_cells"] == 1
    # 空输入
    html0, stats0 = build_table_html_v2({"cells": []})
    assert html0 == "" and stats0 == {}


# ------------------------------------------------- 箭头方向渲染标记生成


def test_direction_style_all_statuses():
    from render_side_by_side_viewer_v2 import direction_style

    fwd = direction_style("directed_src_to_dst")
    assert fwd == ("forward", "→", "v2-edge-forward", True, False)
    bwd = direction_style("directed_dst_to_src")
    assert bwd == ("backward", "←", "v2-edge-backward", False, True)
    bi = direction_style("bidirectional")
    assert bi == ("bidirectional", "↔", "v2-edge-bidirectional", True, True)
    none_ = direction_style("undetermined")
    assert none_ == ("none", "—", "v2-edge-none", False, False)
    # 任务口径别名 forward/backward/bidirectional/none
    assert direction_style("forward")[2] == "v2-edge-forward"
    assert direction_style("backward")[2] == "v2-edge-backward"
    assert direction_style("none")[2] == "v2-edge-none"
    # 未知值回退 none(灰线无箭头)
    assert direction_style("weird-status") == none_
    assert direction_style(None) == none_


def _svg_nodes():
    return [
        {"node_id": "NOD-1", "diagram_id": "DGM-t", "doc_id": "04",
         "type_candidate": "process", "text_raw": "处理数据",
         "master_type": "Rectangle.5", "via_master": True,
         "geometry": {"cx": 2.0, "cy": 3.0, "w": 1.0, "h": 0.6}},
        {"node_id": "NOD-2", "diagram_id": "DGM-t", "doc_id": "04",
         "type_candidate": "end", "text_raw": "结束",
         "master_type": "Circle.7", "via_master": True,
         "geometry": {"cx": 4.0, "cy": 1.0, "w": 0.0, "h": 0.0}},
    ]


def _svg_edges():
    return [
        {"edge_id": "E1", "diagram_id": "DGM-t", "doc_id": "04",
         "src_node": "NOD-1", "dst_node": "NOD-2",
         "direction_status": "directed_src_to_dst", "line_pattern": "solid",
         "label_raw": "完成后", "waypoints": [[2.0, 3.0], [2.0, 2.0], [4.0, 2.0]]},
        {"edge_id": "E2", "diagram_id": "DGM-t", "doc_id": "04",
         "src_node": "NOD-2", "dst_node": "NOD-1",
         "direction_status": "directed_dst_to_src", "line_pattern": "dashed",
         "label_raw": "", "waypoints": []},
        {"edge_id": "E3", "diagram_id": "DGM-t", "doc_id": "04",
         "src_node": "NOD-1", "dst_node": "NOD-2",
         "direction_status": "bidirectional", "line_pattern": "solid",
         "label_raw": "", "waypoints": []},
        {"edge_id": "E4", "diagram_id": "DGM-t", "doc_id": "04",
         "src_node": "NOD-1", "dst_node": "NOD-2",
         "direction_status": "undetermined", "line_pattern": "solid",
         "label_raw": "", "waypoints": []},
    ]


def test_svg_direction_markers_and_waypoints():
    from render_side_by_side_viewer_v2 import render_diagram_svg

    svg, stats = render_diagram_svg(_svg_nodes(), _svg_edges(), None, None, seq=7)
    assert svg.startswith('<svg class="v2-svg" viewBox=')
    # 每张图独立的箭头 marker id
    assert 'id="arr-fwd-7"' in svg and 'id="arr-bwd-7"' in svg
    # forward: marker-end + class
    assert 'class="v2-edge-forward"' in svg
    assert 'marker-end="url(#arr-fwd-7)"' in svg
    # backward: marker-start + class
    assert 'class="v2-edge-backward"' in svg
    assert 'marker-start="url(#arr-bwd-7)"' in svg
    # bidirectional: 双端 marker
    assert 'class="v2-edge-bidirectional"' in svg
    assert svg.count('marker-end="url(#arr-fwd-7)"') >= 2  # forward + bidirectional
    # undetermined: 灰线无箭头
    assert 'class="v2-edge-none"' in svg
    assert svg.count('stroke-dasharray="0.14 0.08"') == 1  # E2 dashed
    # waypoints 有则折线(3点), 无则直线(2点: src中心->dst中心)
    polylines = re.findall(r'<polyline points="([^"]+)"', svg)
    assert any(p.count(",") == 3 for p in polylines)  # 折线
    assert any(p.count(",") == 2 for p in polylines)  # 直线
    # 边标签
    assert ">完成后</text>" in svg
    # 统计
    assert stats["svg_nodes"] == 2 and stats["svg_edges"] == 4
    assert stats["arrow_edges"] == 3
    assert stats["arrow_forward"] == 1 and stats["arrow_backward"] == 1
    assert stats["arrow_bidirectional"] == 1
    # 无节点 -> 空 SVG
    empty, estats = render_diagram_svg([], [], None, None, seq=8)
    assert empty == "" and estats == {"svg_nodes": 0}


def test_svg_lanes_loops_forks_master():
    from render_side_by_side_viewer_v2 import render_diagram_svg

    lanes_row = {"lanes_status": "lane_detected", "n_lanes": 1,
                 "lanes": [{"y_min": 2.0, "y_max": 4.0, "lane_index": 0, "nodes": []}]}
    graph_row = {
        "has_loops": True, "has_forks": True,
        "loops": [{"cycle_nodes": ["NOD-1"], "kind": "scc"}],
        "forks": [{"node_id": "NOD-2", "node_type": "fork", "out_degree": 3}],
    }
    svg, stats = render_diagram_svg(_svg_nodes(), [], lanes_row, graph_row, seq=3)
    # 泳道横带 + 标签
    assert svg.count('class="v2-svg-lane"') == 1
    assert "泳道0" in svg
    # 循环红圈(fork 节点是 0 尺寸节点)
    assert svg.count('class="v2-svg-loop"') == 1
    # fork 菱形
    assert svg.count('class="v2-svg-fork"') == 1
    # master_type 小字(仅非零高节点 NOD-1)
    assert svg.count('class="v2-svg-master"') == 1
    assert ">Rectangle.5</text>" in svg
    # 零尺寸节点 -> 圆点
    assert 'class="v2-svg-dot"' in svg
    assert stats["lane_bands"] == 1 and stats["loop_marks"] == 1 and stats["fork_marks"] == 1
    assert stats["loop_cycles"] == 1


def test_svg_wrap_cjk():
    from render_side_by_side_viewer_v2 import _wrap_cjk

    assert _wrap_cjk("短文本") == ["短文本"]
    text18 = "数据统一访问服务将句柄切换到备用节点"
    lines = _wrap_cjk(text18, per_line=8, max_lines=3)
    assert len(lines) == 3
    assert lines[0] == "数据统一访问服务"
    assert lines[2] == "节点"  # 恰好3行, 不截断
    # 超过 max_lines -> 末行截断加省略号
    over = _wrap_cjk(text18 + "并通知管理员切换结果", per_line=8, max_lines=3)
    assert len(over) == 3 and over[-1].endswith("…")
    assert _wrap_cjk("") == []


# ------------------------------------------------------------- 实体badge映射


def test_entity_badge_cls_six_types():
    from render_side_by_side_viewer_v2 import entity_badge_cls

    assert entity_badge_cls("接口") == ("et-iface", "#1d4ed8")
    assert entity_badge_cls("模块") == ("et-module", "#0e7490")
    assert entity_badge_cls("功能") == ("et-func", "#15803d")
    assert entity_badge_cls("参数") == ("et-param", "#c2410c")
    assert entity_badge_cls("数据项") == ("et-data", "#7e22ce")
    assert entity_badge_cls("分系统") == ("et-sys", "#92400e")
    # 未知/空 -> 灰色回退
    assert entity_badge_cls("未知物") == ("et-other", "#5c6b7a")
    assert entity_badge_cls("") == ("et-other", "#5c6b7a")


def test_entity_badge_html_title_basis():
    from render_side_by_side_viewer_v2 import entity_badge_html

    html = entity_badge_html("接口", "dict:接口:含接口")
    assert 'class="ebadge et-iface"' in html
    assert ">接口</span>" in html
    assert "dict:接口:含接口" in html  # basis 进 title
    other = entity_badge_html("", None)
    assert 'class="ebadge et-other"' in other and "未分类" in other


# ------------------------------------------------- 合成数据全链路(build_viewer)


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


@pytest.fixture()
def synthetic_doc(tmp_path, monkeypatch):
    import render_side_by_side_viewer_v2 as rv

    doc_dir = tmp_path / "mineru_standard" / "04测试文档"
    office = doc_dir / "office"
    office.mkdir(parents=True)
    (office / "04测试文档_content_list.json").write_text(
        json.dumps(BLOCKS, ensure_ascii=False), encoding="utf-8"
    )
    img_dir = office / "images"
    img_dir.mkdir()
    import base64

    (img_dir / "fig_001.png").write_bytes(base64.b64decode(PNG_1X1))

    v2 = tmp_path / "feature_matrix_v2"
    _write_jsonl(
        v2 / "sentences.jsonl",
        [
            {
                "claim_id": "CLM-t1", "doc_id": "04", "section": "3.2",
                "text": SENT_TEXT,
                "span": {"block_idx": 1, "start": 0, "end": len(SENT_TEXT)},
                "span_status": "located",
                "conditions": [{"raw": "当系统出现故障时", "cond_text": "系统出现故障", "pos": 0}],
                "negations": [{"word": "不能", "pos": 17}],
                "scope_entity": [{"entity": "系统", "raw": "系统", "pos": 9}],
                "has_condition": True,
            }
        ],
    )
    _write_jsonl(
        v2 / "references_resolved.jsonl",
        [
            {"claim_id": "CLM-t1", "doc_id": "04", "ref": "见图1",
             "status": "resolved", "target_id": "IMG-04-0000"},
            {"claim_id": "CLM-t1", "doc_id": "04", "ref": "见表9",
             "status": "unresolved", "target_id": ""},
        ],
    )
    _write_jsonl(
        v2 / "tables_v2.jsonl",
        [
            {
                "table_id": "T-04-0000", "doc_id": "04", "caption_raw": "表1 测试表",
                "n_rows": 2, "n_cols": 2, "thead_rows": 1, "header_levels": 2,
                "multi_level_header": True,
                "header_tree": {
                    "levels": 2,
                    "nodes": [
                        {"text": "参数", "rowspan": 1, "colspan": 1, "children": []},
                        {"text": "要求", "rowspan": 1, "colspan": 1,
                         "children": [{"text": "上限", "rowspan": 1, "colspan": 1,
                                       "children": []}]},
                    ],
                },
                "cells": [
                    {"cell_id": "r0c0", "row": 0, "col": 0, "rowspan": 1, "colspan": 1,
                     "text": "参数", "is_merged_origin": False},
                    {"cell_id": "r0c1", "row": 0, "col": 1, "rowspan": 1, "colspan": 2,
                     "text": "要求(含上限)", "is_merged_origin": True},
                    {"cell_id": "r1c0", "row": 1, "col": 0, "rowspan": 1, "colspan": 1,
                     "text": "响应时间", "is_merged_origin": False},
                    {"cell_id": "r1c1", "row": 1, "col": 1, "rowspan": 1, "colspan": 2,
                     "text": "", "is_merged_origin": True},
                ],
            }
        ],
    )
    v1 = tmp_path / "feature_matrix_v1"
    _write_jsonl(
        v1 / "claim_slot_features.jsonl",
        [
            {"claim_id": "CLM-t1", "doc_id": "04", "parse_status": "ok",
             "subject_candidate": "系统", "predicate_candidate": "切换",
             "operator": "应", "object_value": "自动", "unit_raw": "",
             "slot_fill_rate": 0.8, "section": "3.2", "raw_text": SENT_TEXT},
        ],
    )
    _write_jsonl(
        v1 / "quality_features.jsonl",
        [{"doc_id": "04", "unit_completeness": 0.05, "claim_slot_fill_rate_avg": 0.8,
          "reference_resolution_rate": 0.5, "table_header_missing_rate": 0.0,
          "empty_text_node_rate": 0.1}],
    )
    visio = tmp_path / "visio_features_v2"
    _write_jsonl(visio / "visio_nodes_v2.jsonl", _svg_nodes())
    _write_jsonl(
        visio / "visio_edges_v2.jsonl",
        [e for e in _svg_edges() if e["edge_id"] in ("E1", "E2")],
    )
    sem = tmp_path / "semantic_features_v2"
    _write_jsonl(
        sem / "lanes.jsonl",
        [{"diagram_id": "DGM-t", "lanes_status": "lane_detected", "n_lanes": 1,
          "lanes": [{"y_min": 2.0, "y_max": 4.0, "lane_index": 0, "nodes": []}]}],
    )
    _write_jsonl(
        sem / "graph_structures.jsonl",
        [{"diagram_id": "DGM-t", "doc_id": "04", "has_loops": True, "loops":
          [{"cycle_nodes": ["NOD-1"], "kind": "scc"}], "has_forks": True,
          "forks": [{"node_id": "NOD-2", "node_type": "fork", "out_degree": 3}],
          "joins": []}],
    )
    _write_jsonl(
        sem / "entity_type_v2.jsonl",
        [{"occurrence_id": "CLM-t1", "kind": "claim", "entity_type": "接口",
          "basis": "dict:接口:含接口", "doc_id": "04", "text": SENT_TEXT},
         {"occurrence_id": "RQ-1", "kind": "requirement", "entity_type": "功能",
          "basis": "default:功能", "doc_id": "04", "text": "数据获取"}],
    )
    _write_jsonl(
        sem / "alignment_status_v2.jsonl",
        [{"node_id": "NOD-1", "alignment_status_v2": "explicit", "doc_id": "04",
          "anchor_id": "ANC-L1-00001", "layer": "L1", "requirement_id": "RQ-1"},
         {"node_id": "NOD-2", "alignment_status_v2": "supported", "doc_id": "04",
          "anchor_id": "ANC-L2-00001", "layer": "L2", "requirement_id": "RQ-1"}],
    )
    _write_jsonl(
        sem / "usecase_relations.jsonl",
        [{"doc_id": "05", "kind": "unknown", "status": "passthrough", "src": "用户",
          "dst": "管理", "model_index": 1, "relation_index": 0}],
    )
    corpus = tmp_path / "structured_corpus_v1"
    _write_jsonl(
        corpus / "diagrams.jsonl",
        [{"diagram_id": "DGM-t", "doc_id": "04", "source": "word/embeddings/oleObject1.bin",
          "embed_index": "oleObject1.bin:page1.xml", "meta": {"n_nodes": 2, "n_edges": 2}}],
    )
    monkeypatch.setattr(rv, "MINERU_STANDARD", tmp_path / "mineru_standard")
    monkeypatch.setattr(rv, "FEATURE_V2_DIR", v2)
    monkeypatch.setattr(rv, "FEATURE_V1_DIR", v1)
    monkeypatch.setattr(rv, "VISIO_DIR", visio)
    monkeypatch.setattr(rv, "SEMANTIC_DIR", sem)
    monkeypatch.setattr(rv, "CORPUS_DIR", corpus)
    return rv


def test_build_viewer_synthetic_end_to_end(synthetic_doc):
    rv = synthetic_doc
    html, stats, payload = rv.build_viewer("04", "3.2", 1)
    # span 定位 + 多层高亮真实渲染(mark 实例)
    assert stats["sentences_located"] == 1 and stats["sentences_unlocated"] == 0
    assert stats["claim_spans"] == 1
    assert stats["cond_highlights"] == 1
    assert stats["neg_word_highlights"] == 1
    assert stats["scope_highlights"] == 1
    for cls in ("v2-claim", "v2-cond", "v2-neg", "v2-scope"):
        assert re.search(r'<mark class="[^"]*\b' + cls, html), cls
    # 五元组联接 + 实体badge + 条件/否定计数 + 引用解析(绿/红)
    assert "主语" in html and "切换" in html and "未提取" in html
    assert 'class="ebadge et-iface"' in html
    assert stats["entity_badges"] == 1
    assert "条件 1" in html and "否定词 1" in html
    assert "✓ IMG-04-0000" in html and "✗ unresolved" in html
    assert stats["refs_rows"] == 2 and stats["refs_resolved"] == 1
    # 表头树 + 合并单元格 + 坐标
    assert stats["header_trees"] == 1
    assert "表头树 · 2级" in html and "└ 上限" in html
    assert stats["coord_labels"] >= 4
    assert '<span class="v2-cc">r1c1</span>' in html
    assert stats["merged_cells"] == 2
    # SVG 简绘图: 泳道/循环/fork/箭头方向
    assert stats["svg_diagrams"] == 1
    assert stats["svg_arrows"] == 2  # E1 forward + E2 backward
    assert stats["lane_bands"] == 1 and 'class="v2-svg-lane"' in html and "泳道0" in html
    assert stats["loop_marks"] == 1 and 'class="v2-svg-loop"' in html
    assert stats["fork_marks"] == 1 and 'class="v2-svg-fork"' in html
    assert 'class="v2-edge-forward"' in html and 'class="v2-edge-backward"' in html
    # 图卡对齐 chips
    assert "显式对齐 1" in html and "支撑对齐 1" in html
    # base64 图嵌入(自包含)
    assert html.count('src="data:image/png;base64,') == 1
    # 顶部 v2 统计(合成数据集口径) + policy 条
    assert "实体类型分布（全数据集 2）" in html
    assert "显式对齐 1" in html and "箭头方向分布" in html
    assert "循环图 1" in html and "泳道图 1" in html
    assert 'id="policybar"' in html
    assert "单位完整率 5.0%" in html  # <30% -> 红色警示
    assert "质量弱点" in html
    assert "include/extend 关系判定: 全unknown（1条, kind=unknown）" in html
    # 数据岛
    m = re.search(
        r'<script type="application/json" id="fm-data">(.*?)</script>', html, re.S
    )
    assert m is not None
    data = json.loads(m.group(1).replace("<\\/", "</"))
    assert data["meta"]["doc_id"] == "04" and data["meta"]["viewer"] == "v2"
    assert data["stats"]["svg_diagrams"] == 1
    assert data["dataset"]["lane_diagrams"] == 1
    # 自包含: 无外链
    assert re.search(r"https?://", html) is None


def test_main_writes_output(synthetic_doc, tmp_path, capsys):
    rv = synthetic_doc
    out = tmp_path / "v2_test.html"
    rc = rv.main(["--doc", "04", "--section", "3.2", "--max-images", "1",
                  "--output", str(out)])
    assert rc == 0 and out.exists()
    assert out.stat().st_size > 10_000
    snapshot = json.loads(capsys.readouterr().out)
    assert snapshot["viewer"] == "v2"
    assert snapshot["sentences_located"] == 1
    assert snapshot["svg_diagrams"] == 1
    assert snapshot["output_bytes"] == out.stat().st_size
    assert snapshot["output"] == str(out)
