"""evidence_subtractor确定性回归: 70号三过滤器 + 三bug修复锚点."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_subtractor import (  # noqa: E402
    extract_anchors, normalize_granularity, split_table_rows, subtract,
)


def test_anchor_case_insensitive():
    """bug修复锚点: 英文词小写化后必须能命中大写原文(BLOB)."""
    anchors = extract_anchors("BLOB数据插入能力的标识符是什么？",
                              "标识符为PZXQ-GN-SQLFW-BLOBSJCR。")
    assert "blob" in anchors
    assert "PZXQ-GN-SQLFW-BLOBSJCR" in anchors
    text = "3.2.1.4 SQL访问-BLOB数据操作（PZXQ-GN-SQLFW-BLOBSJCZ）"
    assert any(a in text.lower() for a in anchors)


def test_split_table_rows_nested_p_tags():
    """bug修复锚点: <td><p>嵌套单元格不被截断为空."""
    html = ("<table><thead><tr><th><p>Use case名称</p></th>"
            "<th><p>项目唯一标识符</p></th></tr></thead>"
            "<tbody><tr><td><p>BLOB数据插入</p></td>"
            "<td><p>PZXQ-GN-SQLFW-BLOBSJCR</p></td></tr></tbody></table>")
    rows = split_table_rows(html)
    assert len(rows) == 1
    assert "BLOB数据插入" in rows[0]
    assert "PZXQ-GN-SQLFW-BLOBSJCR" in rows[0]
    assert "Use case名称：BLOB数据插入" in rows[0]


def test_granularity_classes():
    atomic = normalize_granularity("3.2.5.1 连接池管理-连接池配置（PZXQ-GN-LJCGL-LJCCSH）")
    assert atomic["class"] == "atomic"
    table = normalize_granularity("<table><tr><td><p>甲</p></td></tr></table>")
    assert table["class"] == "table_rows"
    long_text = "第一句。第二句。第三句。第四句。" * 10
    sents = normalize_granularity(long_text)
    assert sents["class"] == "sentences" and len(sents["statements"]) > 4


def test_scope_removal_and_id_exemption():
    """F1删无锚点干扰块; ID豁免保标识符比较所需证据."""
    ev = [
        {"evidence_id": "ev1", "text": "数据库初始化配置说明与参数详情"},
        {"evidence_id": "ev2", "text": "3.2.1.4.1.2 BLOB数据操作-BLOB数据修改（PZXQ-GN-SQLFW-BLOBSJCZ-BLOBSJXG）"},
        {"evidence_id": "ev3", "text": "BLOB数据插入功能的详细要求如下"},
    ]
    pack = subtract("BLOB数据插入能力的项目唯一标识符是什么？",
                    "BLOB数据插入能力的项目唯一标识符为PZXQ-GN-SQLFW-BLOBSJCR。",
                    ev)
    reasons = {r["evidence_id"]: r["reason_code"] for r in pack["removed"]}
    assert reasons.get("ev1") == "scope_mismatch"      # 无锚点 → 删
    assert "ev2" not in reasons                         # ID豁免 → 保
    kept_ids = {k["evidence_id"] for k in pack["kept"]}
    assert kept_ids == {"ev2", "ev3"}


def test_pointer_with_anchor_kept():
    """bug修复锚点: 命中锚点的指针(交叉引用型gold)不删; 无锚点指针删."""
    ev = [
        {"evidence_id": "p1",
         "text": "数据同步共享服务软件环境需求见表40。"},
        {"evidence_id": "p2", "text": "数据库备份恢复说明见表99所示。"},
    ]
    pack = subtract("本软件需求规格说明对应的软件环境需求在哪个表中描述？",
                    "数据同步共享服务软件环境需求见表40。", ev)
    reasons = {r["evidence_id"]: r["reason_code"] for r in pack["removed"]}
    assert "p1" not in reasons                          # 锚点命中 → 保
    assert reasons.get("p2") in ("scope_mismatch",
                                 "shape_violation.pointer")


def test_fallback_when_all_removed():
    """护栏: F1删光时回退保留全部."""
    ev = [{"evidence_id": "x1", "text": "完全无关的内容片段"}]
    pack = subtract("BLOB数据插入的标识符？", "标识符为PZXQ-XXX。", ev)
    assert pack["stats"]["fallback"] is True
    assert len(pack["kept"]) == 1


def test_statement_budget_ranks_by_anchor():
    """语句预算: 高锚点命中的语句优先保留."""
    table = ("<table><thead><tr><th><p>名称</p></th></tr></thead>"
             "<tbody>" + "".join(
                 f"<tr><td><p>无关条目{i}</p></td></tr>" for i in range(30)
             ) + "<tr><td><p>BLOB数据插入</p></td></tr></tbody></table>")
    ev = [{"evidence_id": "t1", "text": table}]
    pack = subtract("BLOB数据插入的标识符？", "BLOB数据插入的标识符为PZXQ-X。",
                    ev, max_statements=5)
    stmts = [s for k in pack["kept"] for s in k["statements"]]
    assert len(stmts) <= 5
    assert any("BLOB数据插入" in s for s in stmts)
