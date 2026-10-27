"""side_by_side_viewer 渲染内核的确定性回归测试。

数据资产受 MANIFEST 保护(见 tests/test_manifest.py)，因此 doc04 的
快照数字(span计数/卡片数/claim定位数/锚点计数)是稳定的论文级数字。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

DOC04_OFFICE = (
    BASE / "data/gjb_438c/mineru_standard/04数据统一访问服务软件需求规格说明-终稿/office"
)
FEATURE_DIR = BASE / "data/gjb_438c/feature_matrix_v1"

pytestmark = pytest.mark.skipif(
    not DOC04_OFFICE.exists() or not (FEATURE_DIR / "claim_slot_features.jsonl").exists(),
    reason="SRS数据资产缺失(mineru_standard/feature_matrix_v1)",
)

GOLDEN_SPANS = {
    "fm-modal": 19,
    "fm-neg": 17,
    "fm-num": 3,
    "fm-pred": 64,
    "fm-ref": 175,
}


def test_plain_with_offsets_keeps_tag_map():
    from render_side_by_side_viewer import plain_with_offsets

    raw = "速度<sub>100</sub>ms 应不超过"
    plain, offsets = plain_with_offsets(raw)
    assert plain == "速度100ms 应不超过"
    assert len(offsets) == len(plain)
    # plain 偏移 -> raw 偏移: '<sub>'/'</sub>' 共 11 个字符被跳过
    p = plain.find("100")
    assert raw[offsets[p]:offsets[p] + 3] == "100"


def test_resolve_overlaps_priority():
    from render_side_by_side_viewer import resolve_overlaps

    # 模态(优先级高) 与 否定 重叠时保留模态
    ms = [
        {"s": 0, "e": 2, "cls": "fm-neg"},
        {"s": 1, "e": 3, "cls": "fm-modal"},
    ]
    chosen = resolve_overlaps(ms)
    assert len(chosen) == 1 and chosen[0]["cls"] == "fm-modal"
    # 不重叠的全部保留, 按位置排序
    ms2 = [
        {"s": 5, "e": 6, "cls": "fm-modal"},
        {"s": 0, "e": 1, "cls": "fm-neg"},
    ]
    chosen2 = resolve_overlaps(ms2)
    assert [m["s"] for m in chosen2] == [0, 5]


def test_render_table_body_injects_overlays():
    from render_side_by_side_viewer import render_table_body

    body = (
        '<table><tr><td>a</td><td colspan="2">b</td></tr>'
        '<tr><td colspan="3">c</td><td></td></tr></table>'
    )
    feat = {
        "merged_cells": [{"row_index": 0, "col_index": 1, "colspan": 2, "rowspan": 1}],
        "empty_cells": [
            {"row_index": 1, "col_index": 0, "state": "empty"},
            {"row_index": 1, "col_index": 1, "state": "dash"},
        ],
        "row_roles": [
            {"row_index": 0, "role_candidate": "usecase_section_row"},
            {"row_index": 1, "role_candidate": "data_row"},
        ],
    }
    html = render_table_body(body, feat)
    assert html.count("<tr") == 2
    assert 'class="fm-role-usecase_section_row"' in html
    assert 'class="fm-role-data_row"' in html
    assert 'class="fm-merged"' in html
    assert 'class="fm-empty"' in html
    assert 'class="fm-dash"' in html
    assert '<table class="fmtbl">' in html


def test_build_viewer_doc04_snapshot():
    from render_side_by_side_viewer import build_viewer

    html, stats, _payload = build_viewer("04", "3.2", 0)
    assert stats["doc_id"] == "04"
    assert stats["blocks_total"] == 411
    assert stats["blocks_rendered"] == 408
    assert stats["cards"] == 408
    assert stats["span_rows"] == 278
    assert stats["spans_by_type"] == GOLDEN_SPANS
    assert stats["claims_located"] == 154
    assert stats["claims_unlocated"] == 380
    assert stats["images_embedded"] == 0
    assert stats["table_feature_count"] == 82
    assert stats["table_block_count"] == 82
    assert stats["section_default"] == "3.2"


def test_build_viewer_doc04_html_invariants():
    from render_side_by_side_viewer import build_viewer

    html, _stats, _payload = build_viewer("04", "3.2", 0)
    # 自包含: 无外链、数据岛、左右栏、base64 由 max_images 控制为 0
    assert re.search(r"https?://", html) is None
    assert re.search(r'(?:src|href)\s*=\s*["\'](?!data:|#)[^"\']+', html) is None
    assert 'id="fm-data"' in html
    assert 'id="leftPane"' in html and 'id="rightPane"' in html
    assert html.count('class="vbtn vy"') == 278
    assert html.count('class="vbtn vn"') == 278
    assert html.count('src="data:') == 0
    marks = set(re.findall(r'<mark class="(fm-[a-z]+)"', html))
    assert len(marks) >= 5
    # span id / localStorage key 唯一(列表块多 item 不串号)
    ids = re.findall(r'id="(sr-[0-9]+-[0-9]+)"', html)
    keys = re.findall(r'data-key="([0-9]+:[0-9]+)"', html)
    assert len(ids) == len(set(ids)) == 278
    assert len(keys) == len(set(keys)) == 278
    # 数据岛可解析且锚点计数正确
    m = re.search(r'<script type="application/json" id="fm-data">(.*?)</script>', html, re.S)
    assert m is not None
    data = json.loads(m.group(1).replace("<\\/", "</"))
    assert data["meta"]["doc_id"] == "04"
    assert data["meta"]["section_default"] == "3.2"
    assert data["anchors"] == {"L1": 55, "L2": 1558}
    assert data["stats"]["span_rows"] == 278


def test_main_end_to_end(tmp_path, capsys):
    from render_side_by_side_viewer import main

    out = tmp_path / "side_by_side_test.html"
    rc = main(["--doc", "04", "--section", "3.2", "--max-images", "0", "--output", str(out)])
    assert rc == 0
    assert out.exists()
    assert out.stat().st_size > 100_000
    snapshot = json.loads(capsys.readouterr().out)
    assert snapshot["spans_by_type"] == GOLDEN_SPANS
    assert snapshot["output_bytes"] == out.stat().st_size
    # 默认输出名约定
    assert snapshot["output"] == str(out)


# ------------------------------------------------ GJB契约面板 / 表型badge 单元


def test_gjb_panel_states_and_chips():
    from render_side_by_side_viewer import build_gjb_panel

    missing = build_gjb_panel("04", None, "missing")
    assert "build_gjb_conformance.py" in missing
    assert 'id="gjbpanel" class="degraded"' in missing
    no_row = build_gjb_panel("04", None, "no-row")
    assert "degraded" in no_row and "04" in no_row

    contract = {
        "sections_present": ["3.1", "3.2", "3.3"],
        "sections_missing": ["3.9", "3.10"],
        "conformance_score": 0.5,
        "anomalies": ["编号断档 3.4"],
    }
    panel = build_gjb_panel("04", contract, "ok")
    assert '<b class="confnum">3/18</b>' in panel
    assert '<span class="schip miss" title="缺失">3.9</span>' in panel
    assert '<span class="schip miss" title="缺失">3.10</span>' in panel
    assert '<span class="schip" title="已具备">3.2</span>' in panel
    assert "conformance 0.500" in panel
    assert "⚠ 异常 1" in panel and "编号断档 3.4" in panel


def test_gjb_table_badge_confidence_colors():
    from render_side_by_side_viewer import gjb_table_badge_html

    hi = gjb_table_badge_html({"gjb_table_type": "usecase_table", "confidence": 0.95})
    assert "用例表" in hi and 'class="ttbadge g"' in hi
    lo = gjb_table_badge_html({"gjb_table_type": "trace_table", "confidence": 0.55})
    assert "追踪表" in lo and 'class="ttbadge a"' in lo
    no_conf = gjb_table_badge_html({"gjb_table_type": "index_table"})
    assert "索引表" in no_conf and 'class="ttbadge a"' in no_conf
    assert gjb_table_badge_html(None) == ""


# ------------------------------------------------ 质量诚实标注（field_quality）


def test_parse_field_quality_schema_variants():
    from render_side_by_side_viewer import parse_field_quality

    # schema A: hallucinated_fields 列表 + subject_verified
    fq = parse_field_quality(
        {"claim_id": "c1", "subject_verified": True, "hallucinated_fields": ["unit", "unit_raw"]}
    )
    assert fq == {"subject": "verified", "unit": "hallucinated"}
    # schema B: field_verdicts 字典 + 顶层 hallucinated（作用于主语）
    fq2 = parse_field_quality(
        {"claim_id": "c2", "hallucinated": True,
         "field_verdicts": {"predicate": "verified", "值": "幻觉"}}
    )
    assert fq2["subject"] == "hallucinated"
    assert fq2["predicate"] == "verified"
    assert fq2["value"] == "hallucinated"
    # schema C: 逐字段键
    fq3 = parse_field_quality({"claim_id": "c3", "unit_status": "empty"})
    assert fq3 == {"unit": "empty"}
    # schema D: hallucinated 为字段名列表
    fq4 = parse_field_quality({"claim_id": "c4", "hallucinated": ["operator"]})
    assert fq4 == {"operator": "hallucinated"}
    assert parse_field_quality(None) == {}


def test_claim_field_dd_honest_marks():
    from render_side_by_side_viewer import claim_field_dd

    audit = {"subject": "hallucinated", "unit": "verified"}
    hall = claim_field_dd("主语", "某系统", audit)
    assert '<dd class="fh-hall"><s>某系统</s>' in hall
    assert 'class="fhmark hall"' in hall and "幻觉" in hall
    ok = claim_field_dd("单位", "ms", audit)
    assert '<dd class="fh-ok">ms' in ok and 'class="fhmark ok"' in ok
    empty = claim_field_dd("算子", None, audit)
    assert 'class="fh-empty"' in empty and "未提取" in empty
    # 无审计信息: 原样展示，不冒充质量结论
    plain = claim_field_dd("主语", "某系统", None)
    assert plain == "<dt>主语</dt><dd>某系统</dd>"
    # 空值优先于幻觉标注（无内容可删除线）; 章节非五元组仍显示 —
    hall_empty = claim_field_dd("主语", "", audit)
    assert "fh-empty" in hall_empty and "fh-hall" not in hall_empty
    sec = claim_field_dd("章节", None, audit)
    assert "<dd>—</dd>" in sec


def test_claim_card_meta_metric_rename():
    from render_side_by_side_viewer import claim_card_html

    html = claim_card_html(
        {"claim_id": "c1", "raw_text": "应提供数据获取能力", "slot_fill_rate": 0.5,
         "parse_status": "ok", "subject_candidate": "某系统"},
        None,
        None,
        audit={"subject": "hallucinated"},
    )
    # 元指标改名且降权, 不再冒充内容特征
    assert "解析完整度(过程指标)" in html
    assert "<span>槽位填充</span>" not in html
    assert "元指标" in html and "不代表提取正确性" in html
    # 幻觉标记出现
    assert html.count('class="fhmark hall"') == 1


def test_quality_audit_bar_states_and_summary():
    from render_side_by_side_viewer import audit_summary, build_quality_audit_bar, parse_field_quality

    bar_missing = build_quality_audit_bar("04", {}, "missing")
    assert "audit_feature_quality.py" in bar_missing
    assert 'id="qualpanel" class="degraded"' in bar_missing
    bar_no_row = build_quality_audit_bar("04", {}, "no-row")
    assert "field_quality.jsonl" in bar_no_row and "degraded" in bar_no_row

    rows = [
        {"claim_id": "c1", "hallucinated": True},
        {"claim_id": "c2", "subject_verified": True},
    ]
    fqi = {str(r["claim_id"]): parse_field_quality(r) for r in rows}
    claims = [{"unit_raw": ""}, {"unit_raw": "ms"}]
    summ = audit_summary(rows, fqi, claims)
    assert summ["claims_audited"] == 2
    assert summ["subject_hallucinated"] == 1
    assert summ["subject_hallucination_rate"] == 0.5
    assert summ["unit_empty_rate_local"] == 0.5
    bar = build_quality_audit_bar("04", summ, "ok")
    assert "subject幻觉率 50.0%" in bar
    assert "单位空缺率 50.0%" in bar and "本地重算" in bar
    assert "degraded" not in bar


# ------------------------------------------------- 全链路（合成数据注入）


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _doc04_rows(name, doc_key):
    lines = (FEATURE_DIR / name).read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    return [r for r in rows if r.get("doc_id") == doc_key]


def test_build_viewer_with_gjb_and_audit_layers(tmp_path, monkeypatch):
    import render_side_by_side_viewer as rv

    gjb_dir = tmp_path / "gjb_conformance_v1"
    _write_jsonl(
        gjb_dir / "section_contract.jsonl",
        [{
            "doc_id": "04",
            "sections_present": ["3.1", "3.2", "3.3"],
            "sections_missing": ["3.9", "3.10"],
            "section_semantics": {"3.2": "CSCI能力需求"},
            "anomalies": ["编号断档 3.4"],
            "conformance_score": 0.5,
        }],
    )
    tables = _doc04_rows("table_features.jsonl", "04")
    _write_jsonl(
        gjb_dir / "table_taxonomy.jsonl",
        [
            {"table_id": tables[0]["table_id"], "gjb_table_type": "usecase_table",
             "confidence": 0.95},
            {"table_id": tables[1]["table_id"], "gjb_table_type": "trace_table",
             "confidence": 0.55},
        ],
    )
    claims = _doc04_rows("claim_slot_features.jsonl", "04")
    audit_rows = [
        # 无 doc_id: 按 claim_id 归属
        {"claim_id": claims[0]["claim_id"], "subject_verified": True,
         "hallucinated_fields": ["unit"]},
        {"claim_id": claims[1]["claim_id"], "hallucinated": True},
        # 带 doc_id: 按 doc_id 过滤
        {"doc_id": "04", "claim_id": claims[2]["claim_id"],
         "hallucinated_fields": ["subject"]},
        # 干扰行: 其他文档, 必须被排除
        {"doc_id": "99", "claim_id": "CLM-xxxx", "hallucinated": True},
    ]
    _write_jsonl(tmp_path / "feature_quality_audit_v1" / "field_quality.jsonl", audit_rows)
    monkeypatch.setattr(rv, "GJB_CONFORMANCE_DIR", gjb_dir)
    monkeypatch.setattr(rv, "FIELD_QUALITY_PATH",
                        tmp_path / "feature_quality_audit_v1" / "field_quality.jsonl")

    html, stats, payload = rv.build_viewer("04", "3.2", 0)
    # GJB 契约面板: conformance 数字 + missing chip + anomaly
    assert stats["gjb_layer"] == "ok"
    assert '<b class="confnum">3/18</b>' in html
    assert 'class="schip miss" title="缺失">3.9' in html
    assert "conformance 0.500" in html and "⚠ 异常 1" in html
    # 表型 badge: 2 个, 绿/琥珀按 confidence
    assert stats["gjb_table_badges"] == 2
    assert "用例表" in html and "追踪表" in html
    assert 'class="ttbadge g"' in html and 'class="ttbadge a"' in html
    # 节语义标签
    assert 'class="secsem">CSCI能力需求' in html
    # 质量审计层: 汇总条 + 幻觉标记
    assert stats["quality_audit_layer"] == "ok"
    assert stats["claims_audited"] == 3
    assert stats["subject_hallucination_rate"] == pytest.approx(2 / 3)
    assert stats["unit_empty_rate_local"] == pytest.approx(523 / 534)
    assert stats["hallucination_marks"] == 2
    assert stats["verified_marks"] == 1
    assert 'id="qualpanel"' in html and "degraded" not in html.split('id="qualpanel"')[1][:200]
    assert "subject幻觉率 66.7%" in html
    assert html.count('class="fhmark hall"') == 2
    assert html.count('class="fhmark ok"') == 1
    assert payload["quality_audit"]["hallucination_marks"] == 2
    assert payload["quality_audit"]["subject_hallucination_rate"] == pytest.approx(2 / 3)
    # 元指标改名
    assert "解析完整度(过程指标)" in html
    # 既有 span 快照不被破坏
    assert stats["spans_by_type"] == GOLDEN_SPANS
    assert stats["span_rows"] == 278


def test_build_viewer_degraded_layers(tmp_path, monkeypatch):
    import render_side_by_side_viewer as rv

    monkeypatch.setattr(rv, "GJB_CONFORMANCE_DIR", tmp_path / "nope")
    monkeypatch.setattr(rv, "FIELD_QUALITY_PATH", tmp_path / "nope" / "field_quality.jsonl")
    html, stats, payload = rv.build_viewer("04", "3.2", 0)
    # 双层缺失: 优雅降级提示, 不崩溃
    assert stats["gjb_layer"] == "missing"
    assert stats["quality_audit_layer"] == "missing"
    assert stats["hallucination_marks"] == 0
    assert "build_gjb_conformance.py" in html
    assert "audit_feature_quality.py" in html
    assert html.count('class="fhmark hall"') == 0
    assert 'id="gjbpanel" class="degraded"' in html
    assert 'id="qualpanel" class="degraded"' in html
    # 空字段"未提取"是本地诚实信息, 不依赖审计层
    assert stats["empty_field_marks"] > 0
    assert html.count('class="fh-empty"') == stats["empty_field_marks"]
    # span 快照不因降级改变
    assert stats["spans_by_type"] == GOLDEN_SPANS
    assert stats["span_rows"] == 278
    assert payload["quality_audit"]["layer_state"] == "missing"
