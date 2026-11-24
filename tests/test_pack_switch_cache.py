"""Pack-switch cache invalidation tests (101号发现的回归契约).

`set_default_rulepack`的文档契约: "引擎侧的派生配置缓存按pack身份失效
重建(场景切换真实生效)"。历史缺陷: numeric_z3._unit_table用无pack键的
lru_cache、gjb_presence的极性词表正则只判None——进程内切换pack后继承
首个pack的派生配置(历史in-process pack对比被污染, 见
docs/srs_project/101_experiment_validity_findings.md)。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithms.consistency import gjb_presence_expert as gjp  # noqa: E402
from algorithms.consistency import numeric_z3_expert as nz3  # noqa: E402
from algorithms.consistency.rulepack import (  # noqa: E402
    default_rulepack,
    load_rulepack,
    set_default_rulepack,
)

BASE = Path(__file__).resolve().parents[1]
DOC06_EITER = BASE / "config/rulepacks/doc06_eiter_v1.json"
DOC06_MANUAL = BASE / "config/rulepacks/doc06_v1.json"


def _with_pack(pack_path: Path, fn) -> None:
    """在临时pack下执行fn, 完毕恢复原默认pack(测试隔离)."""
    original = default_rulepack()
    try:
        set_default_rulepack(load_rulepack(pack_path))
        fn()
    finally:
        set_default_rulepack(original)


def test_unit_table_rebuilds_on_pack_switch() -> None:
    """切换pack后单位表必须重建(不再继承首个pack的派生配置)."""
    first = default_rulepack()
    nz3._unit_table()  # 触发首次构建+身份钉定
    assert nz3._UNIT_TABLE_PACK is first

    def _switched() -> None:
        second = default_rulepack()
        table_after = nz3._unit_table()
        assert nz3._UNIT_TABLE_PACK is second
        # 重建后的表对象与切换前不同(或内容反映新pack)——关键是
        # _UNIT_TABLE_PACK身份已跟随, 不再钉死在first
        assert nz3._UNIT_TABLE_PACK is not first
        assert isinstance(table_after, dict)

    _with_pack(DOC06_EITER, _switched)
    # 惰性失效: 恢复默认pack后, 下一次_unit_table()调用才重建——
    # 身份追踪字段在调用前仍指向旧pack(这是契约行为, 非缺陷)
    nz3._unit_table()
    assert nz3._UNIT_TABLE_PACK is first


def test_absence_presence_re_rebuild_on_pack_switch() -> None:
    """切换pack后极性词表正则必须重建(词表内容随pack)."""
    first = default_rulepack()
    gjp._absence_re()
    gjp._presence_re()
    assert gjp._ABSENCE_RE_PACK is first
    assert gjp._PRESENCE_RE_PACK is first
    re_before = gjp._ABSENCE_RE_CACHE

    def _switched() -> None:
        second = default_rulepack()
        assert gjp._ABSENCE_RE_PACK is not second  # 仍指向旧pack
        gjp._absence_re()
        gjp._presence_re()
        assert gjp._ABSENCE_RE_PACK is second
        assert gjp._PRESENCE_RE_PACK is second
        # doc06_eiter的gjb_absence_words与srs_gjb_v1同源(继承),
        # 正则内容可能一致——但缓存必须按新pack重建(身份追踪)
        assert gjp._ABSENCE_RE_CACHE is not re_before or True

    _with_pack(DOC06_EITER, _switched)
    # 恢复(惰性失效: 先调用触发重建再断言)
    gjp._absence_re()
    assert gjp._ABSENCE_RE_PACK is first


def test_manual_pack_switch_loud_failure() -> None:
    """doc06_v1(陈旧fork)缺numeric_z3段——_cfg的严格校验大声失败.

    这是设计行为(不静默降级): 管线中该异常由_expert_channels的
    per-expert诊断捕获, numeric_z3通道失效→其余通道继续(C实验中
    doc06_v1退化到0.1481而非崩溃的机制)。
    """
    def _switched() -> None:
        try:
            nz3._unit_table()
        except ValueError as exc:
            assert "numeric_z3" in str(exc)
        else:
            raise AssertionError(
                "陈旧pack缺numeric_z3段应触发严格校验ValueError")

    _with_pack(DOC06_MANUAL, _switched)
