"""pair视图渲染回归测试: 类型分流 + UML语义约定 (2026-09审计修复的防复发锚).

背景: m12曾对373图100%硬编码flowchart, 121对用例图被错渲染
(actor平行四边形/有向关联/boundary当节点), 无任何测试拦截.
本套测试锁定: 分类正确性 + 用例图UML约定 + 真实数据快照.
再改动导出器(tools/export_pair_views.py)后, 重生成并同步本文件快照.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))
from export_pair_views import classify_diagram  # noqa: E402

PAIR = BASE / "data/gjb_438c/pair_dataset"
EXPORT = BASE / "data/gjb_438c/anchor_v2/mermaid_export.json"

pytestmark = pytest.mark.skipif(
    not EXPORT.exists() or not PAIR.exists(),
    reason="mermaid_export/pair_dataset缺失(先跑 tools/export_pair_views.py)")


# ═══════════════════════════════════════════════════════════════
# 分类器单元(合成结构)
# ═══════════════════════════════════════════════════════════════

def _n(nid, ntype, text="文本"):
    return {"id": nid, "type": ntype, "text": text,
            "cx": 1.0, "cy": 1.0, "w": 1.0, "h": 1.0}


def test_classify_usecase_actor_uc():
    assert classify_diagram(
        [_n(1, "actor", "用户"), _n(2, "usecase", "查询"),
         _n(3, "boundary", "系统")]) == "usecase"


def test_classify_usecase_actor_boundary_process():
    """1_117型: M11把用例typed成process, 但actor+boundary是用例图铁证."""
    nodes = ([_n(1, "actor", "a"), _n(2, "actor", "b"), _n(3, "actor", "c"),
              _n(4, "boundary", "边界"),
              _n(5, "process", "三方传输服务接入"),
              _n(6, "process", "传输服务接入")])
    assert classify_diagram(nodes) == "usecase"


def test_classify_usecase_textless_actor():
    """2_087型: actor/usecase节点可能无文本 → 类型信号必须数全部节点."""
    nodes = [_n(1, "process", "p1"), _n(2, "actor", ""),
             _n(3, "actor", ""), _n(4, "usecase", ""), _n(5, "usecase", "")]
    assert classify_diagram(nodes) == "usecase"


def test_classify_flowchart():
    nodes = [_n(1, "start", ""), _n(2, "process", "步骤"),
             _n(3, "decision", "判断"), _n(4, "end", "")]
    assert classify_diagram(nodes) == "flowchart"


def test_classify_flowchart_with_single_actor():
    """流程图混入1个actor节点(少数) → 仍是流程图."""
    nodes = ([_n(i, "process", f"步骤{i}") for i in range(1, 6)]
             + [_n(9, "actor", "人员")])
    assert classify_diagram(nodes) == "flowchart"


def test_classify_state():
    nodes = [_n(1, "state", "待机"), _n(2, "state", "运行"),
             _n(3, "state", "故障")]
    assert classify_diagram(nodes) == "state"


def test_classify_state_not_killed_by_textless_process():
    """无文本装饰process节点不应翻转状态图类型(全节点计数的教训)."""
    nodes = [_n(1, "state", "待机"), _n(2, "state", "运行"),
             _n(3, "process", "")]
    assert classify_diagram(nodes) == "state"


# ═══════════════════════════════════════════════════════════════
# 真实数据快照
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def export():
    return json.loads(EXPORT.read_text(encoding="utf-8"))


def test_export_type_distribution(export):
    """373图的类型分布快照(改分类器/精化规则必须显式更新这里)."""
    from collections import Counter
    dist = Counter(v["diagram_type"] for v in export.values())
    assert len(export) == 373
    assert dist == {"flowchart": 175, "usecase": 150,
                    "state": 25, "other": 23}


def test_refine_untyped_geometry():
    """几何类型精化: 1_012教训(Master类型识别全败→26节点全other)."""
    sys.path.insert(0, str(BASE / "tools"))
    from export_pair_views import refine_untyped
    # 大空框 + 顶部扁标题 + 框内文本 + 框外文本, 全other
    nodes = [
        {"id": "1", "type": "other", "text": "", "cx": 4.5, "cy": 4.5, "w": 4.6, "h": 9.0},
        {"id": "3", "type": "other", "text": "系统名", "cx": 4.6, "cy": 8.8, "w": 1.7, "h": 0.23},
        {"id": "5", "type": "other", "text": "用户", "cx": 0.5, "cy": 4.6, "w": 1.0, "h": 0.25},
        {"id": "7", "type": "other", "text": "用例A", "cx": 4.6, "cy": 8.0, "w": 1.5, "h": 0.25},
        {"id": "9", "type": "other", "text": "外部系统", "cx": 7.5, "cy": 3.2, "w": 1.0, "h": 0.25},
        {"id": "11", "type": "other", "text": "用例B", "cx": 4.6, "cy": 7.0, "w": 1.5, "h": 0.25},
        {"id": "13", "type": "other", "text": "用例C", "cx": 4.6, "cy": 6.0, "w": 1.5, "h": 0.25},
    ]
    out = refine_untyped(nodes)
    by_type = {}
    for n in out:
        by_type.setdefault(n["type"], []).append(n)
    assert by_type["boundary"][0]["text"] == "系统名"     # 大框→boundary, 标题入框
    assert {n["text"] for n in by_type["usecase"]} == {"用例A", "用例B", "用例C"}
    assert {n["text"] for n in by_type["actor"]} == {"用户", "外部系统"}
    # 有类型信息的结构不精化
    typed = [dict(n, type="process") for n in nodes]
    assert refine_untyped(typed) is typed


def test_1_012_realigned_content():
    """1_012: census重对齐到插件接口用例图(与VLM读图一致).

    旧渲染(创建服务工程等)其实来自错配锚点——那才是1_011的图!
    """
    text = (PAIR / "sc1_usecase_capability/1_012/1_012.md").read_text(
        encoding="utf-8")
    assert "census重对齐" in text
    puml = re.search(r"```plantuml\n(.*?)```", text, re.S).group(1)
    assert 'rectangle "服务开发支撑" {' in puml
    assert 'actor "应用软件"' in puml
    assert 'actor "开发人员"' in puml
    assert 'usecase "插件初始化函数定义"' in puml
    assert 'usecase "调用服务定时器接口"' in puml
    n_assoc = len(re.findall(r"P\d+ -- P\d+", puml))
    assert n_assoc == 7


def test_export_has_dot(export):
    sample = list(export.values())[:20]
    assert sample and all(v.get("dot", "").strip().startswith("digraph")
                          for v in sample)


def test_1_047_usecase_fixed():
    """审计起点用例(经census重对齐到正确锚点后的真内容)."""
    text = (PAIR / "sc1_usecase_capability/1_047/1_047.md").read_text(
        encoding="utf-8")
    assert "born-digital导出(usecase" in text
    assert "census重对齐" in text                 # 旧锚点错配的诚实记录
    puml = re.search(r"```plantuml\n(.*?)```", text, re.S).group(1)
    assert puml.startswith("@startuml")
    assert 'rectangle "系统基础信息查询设置" {' in puml   # 系统边界
    assert 'actor "实施人员"' in puml                  # 4个参与者
    assert 'actor "服务集成框架"' in puml
    assert 'usecase "用户基础信息 查询"' in puml       # 框内用例
    n_assoc = len(re.findall(r"P\d+ -- P\d+", puml))
    assert n_assoc == 5                            # 5条关联
    dot = re.search(r"```dot\n(.*?)```", text, re.S)
    assert dot and "dir=none" in dot.group(1)


def test_1_007_dangling_ends_recovered():
    """1_007: 悬空端点几何恢复 — 4条边(1粘合+3恢复), 与VLM读图一致.

    修复前: M0把3条半粘连连线整条丢弃(且排除在几何恢复之外)→只渲染1条边;
    修复: 连线自由端吸附最近语义节点(距离0.03-0.12英寸, 排除boundary拦截).
    """
    text = (PAIR / "sc1_usecase_capability/1_007/1_007.md").read_text(
        encoding="utf-8")
    puml = re.search(r"```plantuml\n(.*?)```", text, re.S).group(1)
    n_edges = len(re.findall(r"P\d+ -- P\d+", puml))
    assert n_edges == 4                       # 1粘合 + 3恢复 = VLM读图数
    assert "已几何恢复3条边" in text            # 诚实注记
    assert "资源占用监控" in puml


def test_recovered_edges_evidence():
    """恢复边带证据链: via/distance/自由端坐标(可审计)."""
    rec_path = (BASE / "data/gjb_438c/anchor_v2/recovered_edges.json")
    if not rec_path.exists():
        pytest.skip("recovered_edges.json未生成")
    import json
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    total = sum(len(v) for v in rec.values())
    assert total >= 40                        # 实测45条(按export_key去重)
    for edges in rec.values():
        for e in edges:
            assert e["via"] == "dangling_snap"
            assert "distance" in e and 0 <= e["distance"] <= 0.5
            assert "free_end" in e and "connector_id" in e


def test_2_001_flowchart_unchanged():
    text = (PAIR / "sc2_flowchart_usecase/2_001/2_001.md").read_text(
        encoding="utf-8")
    assert "born-digital导出(flowchart" in text
    mm = re.search(r"```mermaid\n(.*?)```", text, re.S).group(1)
    assert "-->" in mm                           # 流程图=有向


def test_1_011_usecase_realigned():
    """1_011: census重对齐后是真正的'服务开发支撑'用例图(VLM读图一致).

    旧渲染(state图)来自错误锚点——1_011的image是服务开发支撑用例图.
    """
    text = (PAIR / "sc1_usecase_capability/1_011/1_011.md").read_text(
        encoding="utf-8")
    assert "census重对齐" in text
    puml = re.search(r"```plantuml\n(.*?)```", text, re.S).group(1)
    assert 'rectangle "服务开发支撑" {' in puml
    assert 'actor "开发人员"' in puml
    assert 'actor "应用软件"' in puml
    assert 'usecase "创建服务工程"' in puml
    n_assoc = len(re.findall(r"P\d+ -- P\d+", puml))
    assert n_assoc == 8


def _mds():
    return sorted(PAIR.rglob("*.md"))


def test_no_usecase_rendered_as_flowchart():
    """全局不变量: md声明类型须与census对齐后锚点的类型组成一致.

    (旧版用pair的stale M0锚点做真值——重对齐后该前提已失效)
    """
    import json
    census = json.loads(
        (BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json").read_text(
            encoding="utf-8"))
    anchors = json.loads(
        (BASE / "data/gjb_438c/anchor_v2/anchors_v2.json").read_text(
            encoding="utf-8"))
    v2_idx = {}
    for doc, d in anchors.items():
        for s in d.get("structures", []):
            key = (doc, s.get("embed_index", "").split(":")[0])
            tn = sum(1 for n in s.get("nodes", []) if n.get("text"))
            if key not in v2_idx or tn > sum(1 for n in v2_idx[key].get("nodes", [])
                                             if n.get("text")):
                v2_idx[key] = s
    mismatch = 0
    for md in _mds():
        text = md.read_text(encoding="utf-8")
        m = re.search(r"born-digital[^\)]*\((\w+),", text)
        if not m:
            continue
        va = md.parent / "visio_anchor.json"
        if not va.exists():
            continue
        a = json.loads(va.read_text(encoding="utf-8"))
        embed = a.get("embed_index", "")
        c = census.get(md.parent.name) or {}
        if c.get("status") == "anchored" and c.get("new_embed"):
            embed = c["new_embed"]
        aligned = v2_idx.get((a.get("doc", ""), embed.split(":")[0]))
        if aligned is None:
            continue
        types = {n["type"] for n in aligned.get("nodes", [])}
        has_uc_signal = bool(types & {"usecase", "actor"})
        if has_uc_signal and m.group(1) == "flowchart":
            mismatch += 1
    assert mismatch == 0


def test_global_no_parallelogram_actor():
    """全局不变量: 任何md的mermaid不得再出现平行四边形actor(修复前=107对)."""
    bad = [md.parent.name for md in _mds()
           if (body := re.search(r"```mermaid\n(.*?)```",
                                 md.read_text(encoding="utf-8"), re.S))
           and re.search(r"N\d+\[/", body.group(1))]
    assert bad == []


def test_global_usecase_undirected():
    """全局不变量: usecase声明的md必须plantuml主投影+无向关联, mermaid兼容版同."""
    missing, directed = [], []
    for md in _mds():
        text = md.read_text(encoding="utf-8")
        m = re.search(r"born-digital[^\)]*\((\w+),", text)
        if not m or m.group(1) != "usecase":
            continue
        puml = re.search(r"```plantuml\n(.*?)```", text, re.S)
        body = re.search(r"```mermaid\n(.*?)```", text, re.S)
        if puml is None:
            missing.append(md.parent.name)
            continue
        if not re.search(r"P\d+ -- P\d+", puml.group(1)) and "rectangle" not in puml.group(1):
            missing.append(md.parent.name)
        if body and re.search(r"N\d+ --> N\d+", body.group(1)):
            directed.append(md.parent.name)
    assert missing == [], f"usecase图缺plantuml/无向关联: {missing[:5]}"
    assert directed == [], f"usecase图mermaid版出现有向箭头: {directed[:5]}"


def test_mermaid_labels_sanitized():
    """标签清洗: mermaid每行的引号数必须为偶数(标签内残留换行=奇数)."""
    dirty = []
    for md in _mds():
        mm = re.search(r"```mermaid\n(.*?)```",
                       md.read_text(encoding="utf-8"), re.S)
        if not mm:
            continue
        for line in mm.group(1).splitlines():
            if line.count('"') % 2 == 1:
                dirty.append(f"{md.parent.name}: {line[:40]}")
                break
    assert dirty == [], f"标签内疑似断行: {dirty[:5]}"
