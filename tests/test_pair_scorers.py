"""pair_scorers打分器族确定性回归: 68号实验的数字锚点."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_linking.pair_scorers import (  # noqa: E402
    make_bge_scorer, make_nli_scorer, mask_digits,
    score_combined, score_lexical_jaccard, score_rule_scope,
    score_section_proximity, score_template_mask,
)


def test_lexical_jaccard_bounds():
    a = "用户响应时间不大于3秒"
    b = "用户响应时间不大于5秒"
    assert score_lexical_jaccard(a, a) == 1.0
    assert 0.0 < score_lexical_jaccard(a, b) < 1.0
    assert score_lexical_jaccard(a, "部署在服务器上") == 0.0


def test_template_mask_doc02_case():
    """doc02真实案例: 数字掩码后模板完全一致 → 高分."""
    a = "支持首屏加载时间不小于2秒，用户响应时间不小于3秒。"
    b = "支持首屏加载时间不小于3秒，用户响应时间不小于5秒；"
    assert mask_digits(a) == mask_digits(b)
    assert score_template_mask(a, b) > 0.95


def test_template_mask_different_devices_low():
    """不同设备配置行: 掩码后结构同但设备名异 → 显著低于同模板."""
    same = ("支持首屏加载时间不小于2秒，用户响应时间不小于3秒。",
            "支持首屏加载时间不小于3秒，用户响应时间不小于5秒；")
    diff = ("| 轻量化服务器 | 处理器：16核 CPU主频：不低于1.5GHz |",
            "| 便携式计算机 | 处理器：i7双核 CPU主频：不低于2.5GHz |")
    assert score_template_mask(*same) > score_template_mask(*diff)


def test_rule_scope_mapping():
    assert score_rule_scope("conflict_same_scope") == 1.0
    assert score_rule_scope("conflict_scope_unknown") == 0.5
    assert score_rule_scope("conflict_scope_diff") == 0.0
    assert score_rule_scope("redundant") == 0.0


def test_section_proximity():
    assert score_section_proximity("3.9.1", "3.9.1") == 1.0
    near = score_section_proximity("1.8.2.1", "1.8.3.2")
    far = score_section_proximity("1.8.2.1", "3.10.1")
    assert near > far
    assert score_section_proximity("", "3.9.1") == 0.0


def test_make_bge_scorer():
    emb = {"甲": [1.0, 0.0], "乙": [0.0, 1.0], "甲2": [1.0, 0.0]}
    sc = make_bge_scorer(emb)
    assert sc("甲", "甲2") == 1.0
    assert abs(sc("甲", "乙")) < 1e-9
    assert sc("甲", "缺失") == 0.0


def test_make_nli_scorer_bidirectional_max():
    calls: list[list[tuple[str, str]]] = []

    def fake_predict(pairs):
        calls.append(pairs)
        return [{"p_contra": 0.1}, {"p_contra": 0.7}]

    sc = make_nli_scorer(fake_predict)
    assert sc("a", "b") == 0.7  # 双向取max
    assert sc("a", "b") == 0.7  # 缓存生效不再调用
    assert len(calls) == 1


def test_combined_linear():
    feats = {"rule": 1.0, "template": 0.5, "bge": 0.0}
    assert score_combined(feats) == 0.5
    assert score_combined(feats, {"rule": 3.0}) == 1.0
    assert score_combined({}) == 0.0
