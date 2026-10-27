"""verify()三态判定外壳的回归锁: answer vs evidence(文本化声明集).

锁定核心语义:
  - 数值: 对齐→内核值比对 → support(同值异表面)/refute(值突变)
  - 存在性: 「X」命中→support; 闭世界未命中→refute; 开世界→NIE
  - 枚举: 逐项grounding
  - 聚合: 矛盾主导
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.consistency.verify import Evidence, Verifier

_V = Verifier()


def test_numeric_support_unit_equivalence() -> None:
    """同值异表面(单位换算) → support(内核领域等价约定)."""
    ev = Evidence(type="text",
                  claims=["3.10.2节规定：内存容量不小于20M。"],
                  source_ref="doc01@3.10.2")
    r = _V.verify("内存容量要求为不小于20M。", ev)
    assert r.verdict == "support"


def test_numeric_refute_value_conflict() -> None:
    """值突变 → refute."""
    ev = Evidence(type="table",
                  claims=["表24名录文件导入场景描述：节点数应小于等于1500。"],
                  source_ref="doc10@表24")
    r = _V.verify("名录文件导入场景中，节点数应小于等于3000。", ev)
    assert r.verdict == "refute"
    assert any(cv.status == "refute" for cv in r.claims)


def test_existence_closed_world_refute() -> None:
    """只有显式声明穷举的证据未命中 → refute."""
    ev = Evidence(type="table",
                  claims=["用例名称包括：基础数据录入、基础数据查询。"],
                  source_ref="doc08@表40", exhaustive=True,
                  scope_id="doc08:table40", completeness_proof="表题声明为全量用例名单")
    r = _V.verify("表格中的用例名称包含「生物识别验证」。", ev)
    assert r.verdict == "refute"


def test_existence_open_world_nie() -> None:
    """开世界(正文)未命中 → not_in_evidence."""
    ev = Evidence(type="text",
                  claims=["该章节描述了基础数据管理的流程。"],
                  source_ref="doc08@3.2.1")
    r = _V.verify("正文中记载「生物识别验证」。", ev)
    assert r.verdict == "not_in_evidence"


def test_existence_support() -> None:
    ev = Evidence(type="table",
                  claims=["用例名称包括：基础数据录入、基础数据查询。"],
                  source_ref="doc08@表40")
    r = _V.verify("表格的用例名称包含「基础数据查询」。", ev)
    assert r.verdict == "support"
    assert r.claims[0].status == "support"
    assert r.claims[0].channel in ("exact", "k1_alias")


def test_enum_full_support() -> None:
    ev = Evidence(type="table",
                  claims=["功能划分：数据获取、数据转换、数据组织管理。"],
                  source_ref="doc01@表3")
    r = _V.verify("功能包括：数据获取、数据转换、数据组织管理。", ev)
    assert r.verdict == "support"


def test_aggregation_refute_dominant() -> None:
    """现有legacy聚合仍为refute主导；QA级整体策略待独立冻结。"""
    ev = Evidence(type="table",
                  claims=["节点数小于等于1500。"],
                  source_ref="doc10@表24", exhaustive=True,
                  scope_id="doc10:table24", completeness_proof="表格为该场景完整参数表")
    r = _V.verify("节点数应小于等于3000，且超时时间为100ms。", ev)
    assert r.verdict == "refute"


def test_multi_evidence_supports_one_answer() -> None:
    """多个SRS证据块共同验证一个answer，不比较证据块之间的内容。"""
    evs = [
        Evidence(type="figure", claims=["用例图包含：结构化数据归集。"],
                 source_ref="doc01@图3"),
        Evidence(type="text", claims=["正文说明系统支持结构化数据归集。"],
                 source_ref="doc01@3.2.1"),
    ]
    r = _V.verify_multi("图中包含「结构化数据归集」。", evs)
    assert r.verdict == "support"
    assert len(r.evidence_refs) >= 1


def test_exhaustive_override() -> None:
    """调用方显式覆盖世界假设: text设为闭世界."""
    ev = Evidence(type="text", claims=["正文只提及A功能。"],
                  source_ref="d@1.1", exhaustive=True,
                  scope_id="d:1.1", completeness_proof="标注协议声明该段是全部功能枚举")
    r = _V.verify("正文提及「B功能」。", ev)
    assert r.verdict == "refute"


def test_table_is_not_closed_world_by_default() -> None:
    ev = Evidence(type="table", claims=["用例名称包括：A功能、B功能。"],
                  source_ref="d@表1")
    r = _V.verify("用例名称包括「C功能」。", ev)
    assert r.verdict == "not_in_evidence"


def test_one_closed_scope_does_not_close_other_evidence() -> None:
    evs = [
        Evidence(type="table", claims=["用例名称包括「A功能」。"],
                 source_ref="d@表1", exhaustive=True,
                 scope_id="d:table1", completeness_proof="仅该表scope封闭"),
        Evidence(type="text", claims=["正文描述基础功能。"],
                 source_ref="d@3.1"),
    ]
    r = _V.verify_multi("表格包含「B功能」，正文记载「C功能」。", evs)
    assert all(cv.status == "not_in_evidence" for cv in r.claims)
    assert r.verdict == "not_in_evidence"


def test_nli_non_entailment_is_not_automatically_refute() -> None:
    from algorithms.consistency.checker import ConsistencyChecker, CheckResult

    class NeutralChecker(ConsistencyChecker):
        def _check_nli(self, _premise: str, _hypothesis: str):
            return CheckResult("inconsistent", "", "SEM", "nli", "binary non-entailment",
                               0.9, "test")

    verifier = Verifier(checker=NeutralChecker())
    r = verifier.verify("该系统提供接口接入服务。",
                       Evidence(type="text", claims=["该接口提供数据映射功能。"],
                                source_ref="d@1.1"))
    assert r.verdict == "not_in_evidence"
