"""确定性内核快照: 词法匹配/约定_T编译/约定_P/双图融合聚合器在固定真实输入上的行为锁定.

科研代码最贵的bug: 重构后论文数字悄悄变了. 这些快照让变化显式报警.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
PAIR = BASE / "data/gjb_438c/pair_dataset"

pytestmark = pytest.mark.skipif(
    not (PAIR / "sc1_usecase_capability" / "1_001" / "table.csv").exists(),
    reason="真实pair_dataset缺失")

sys.path.insert(0, str(BASE / "tools"))
sys.path.insert(0, str(BASE / "algorithms/blackboard"))
from kt_compilers import compile_capability_table, compile_usecase_table  # noqa: E402
from lexical_kit import text_match_score  # noqa: E402
from prose_compiler import compile_prose  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# 词法匹配内核 (m1 text_match_score的vendored版, 与live版同步测试绑定)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("a,b,expected", [
    ("数据获取", "数据获取", 1.0),               # 精确
    ("数据获取", "全域数据获取服务", 0.9),        # 包含
    ("结构化数据归集", "结操化数据归集", 0.85),   # 错字容差(sc1 typo类)
    ("查询收件箱接口", "查询发件箱接口", 0.85),   # 错字容差
    ("数据主动推送", "数据订阅推送", 0.0),        # 语义盲区(M17发现, 需embedding通道)
    ("触摸操控", "快捷操控", 0.0),               # 完全不同名(sc1 gold矛盾对)
    ("与非结构化数据交互接口", "非结构化数据", 0.9),  # 接口名解包
    ("坐位管理", "席位管理", 0.88),              # 同义字归一
])
def test_text_match_score_kernel(a, b, expected):
    assert text_match_score(a, b) == pytest.approx(expected, abs=1e-6)


# ═══════════════════════════════════════════════════════════════
# 约定_T编译器 (真实表格)
# ═══════════════════════════════════════════════════════════════

def test_capability_compiler_1_001():
    x_t = compile_capability_table(
        PAIR / "sc1_usecase_capability/1_001/table.csv")
    assert x_t["type"] == "capability"
    assert len(x_t["caps"]) == 8
    assert x_t["caps"][0]["name"] == "结构化数据归集"
    assert [c["name"] for c in x_t["caps"][:3]] == [
        "结构化数据归集", "结构化数据源引接", "半结构化数据归集"]


def test_usecase_compiler_2_001():
    u = compile_usecase_table(
        PAIR / "sc2_flowchart_usecase/2_001/table.csv")
    assert u["uc_name"] == "开发工程生成"
    assert u["actors"] == ["开发人员"]
    assert sorted(u["steps"].keys()) == [1, 2, 3, 4, 5, 6, 7]
    assert sorted(u["exceptions"].keys()) == ["E1"]
    assert len(u["nodes"]) == 8      # 7步骤 + 1异常流
    assert len(u["edges"]) == 6      # 6条顺序边


# ═══════════════════════════════════════════════════════════════
# 约定_P正文编译器 (真实正文)
# ═══════════════════════════════════════════════════════════════

def test_prose_compiler_1_001():
    text = (PAIR / "sc1_usecase_capability/1_001/text.txt").read_text(
        encoding="utf-8")
    p = compile_prose(text, "所有功能标识")
    assert p["n_sentences"] == 3
    assert p["n_features"] == 5
    items = [it for e in p["enumerations"] for it in e["items"]]
    assert items == ["离线数据报送", "在线数据抽取", "实时数据采集",
                     "结构化数据归集", "半结构化数据归集",
                     "非结构化数据归集", "流式数据归集"]
    assert len(p["behaviors"]) == 3


# ═══════════════════════════════════════════════════════════════
# 双图融合聚合器 (M5轨道, Windows编码修复后的回归锁定)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.slow
class TestMatcherSnapshot:
    """加载~11MB LightRAG资产, 稍慢; 快照锁定aggregate的确定性输出."""

    @pytest.fixture(scope="class")
    def matcher(self):
        sys.path.insert(0, str(BASE / "algorithms/consistency/semantic/scene1"))
        from kg_context_matcher import KGContextMatcher
        m = KGContextMatcher()
        assert m.has_id_graph and m.has_images and m.has_struct, \
            "matcher资产加载失败(编码/路径问题?)"
        return m

    def test_aggregate_shujuhuoqu(self, matcher):
        r = matcher.aggregate("数据获取")
        assert r["entity_id"] == "ZZSJHQZHFW-GN-SJHQ"
        assert r["occurrence_count"] == 64
        assert r["chain_completeness"] == 0.67
        assert set(r["locations"][:3]) == {"figure", "table", "text"}

    def test_aggregate_cjfwgc(self, matcher):
        r = matcher.aggregate("创建服务工程")
        assert r["entity_id"] == "PZXQ-GN-FWKFZC-CJFWGC"
        assert r["occurrence_count"] == 17
        assert r["chain_completeness"] == 0.67
