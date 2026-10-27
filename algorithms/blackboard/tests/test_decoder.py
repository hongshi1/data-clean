"""检测闭环测试: 裁决索引/译码数学/判决/弃权带. 依赖真实裁决语料."""
from __future__ import annotations

import pytest

from algorithms.blackboard.adjudication import (FINAL_PATH,
                                                AdjudicationStore)
from algorithms.blackboard.decoder import Decoder, decode_element
from algorithms.blackboard.schemas import Channel

pytestmark = pytest.mark.skipif(
    not FINAL_PATH.exists(), reason="M22裁决语料缺失(final_adjudication.json)")


# ═══════════════════════════════════════════════════════════════
# 裁决语料索引
# ═══════════════════════════════════════════════════════════════

def test_final_corpus_scale():
    st = AdjudicationStore()
    stats = st.stats
    assert stats["n_final_labels"] == 664
    assert stats["dist"] == {"benign_variation": 378, "real_bug": 176,
                             "compiler_bug": 110}
    assert stats["pi"] == pytest.approx(0.2651, abs=1e-3)


def test_verdicts_for_pair_2_001():
    st = AdjudicationStore()
    vs = st.verdicts_for_pair("2_001")
    assert len(vs) >= 3                      # M7裁决过2_001的多条分歧
    labels = {v["label"] for v in vs if v.get("label")}
    assert labels & {"real_bug", "benign_variation"}


def test_match_by_evidence_exact():
    st = AdjudicationStore()
    m = st.match("2_001", "ACTOR_MISSING",
                 "表格Actor「开发人员」在图中无参与者节点")
    assert m is not None
    assert m["label"] == "benign_variation"  # M22五票: 4/5 benign


def test_type_counts_and_scene_pi():
    st = AdjudicationStore()
    tc = st.type_counts("sc2_flowchart_usecase", "EXC_MISSING")
    assert sum(tc.values()) > 0              # sc2异常流缺失有裁决样本
    pi = st.scene_pi("sc2_flowchart_usecase")
    assert 0.1 <= pi <= 0.5                  # sc2最终π=0.265量级
    pi_g = st.scene_pi("sc9_nonexistent")    # 无数据场景→全局π
    assert pi_g == pytest.approx(0.2651, abs=1e-3)


# ═══════════════════════════════════════════════════════════════
# P1译码公式(M4同款数学)
# ═══════════════════════════════════════════════════════════════

def test_decode_element_p1_math():
    # 论文数值示例: π=0.05, p=0.1 → 单条分歧后验仅≈0.32
    q = decode_element(1, pi=0.05, p_miss=0.1, p_hall=0.05)
    assert q == pytest.approx(0.32, abs=0.02)
    # 分离条件: p<1/2时分歧是不一致证据(后验>先验)
    assert q > 0.05
    # 观测一致时后验低于先验
    q0 = decode_element(0, pi=0.05, p_miss=0.1, p_hall=0.05)
    assert q0 < 0.05
    # 完美通道(p→0): 分歧即确证
    assert decode_element(1, pi=0.05, p_miss=0.0, p_hall=0.0) == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════
# Decoder判决(裁决查表+类型先验+弃权带)
# ═══════════════════════════════════════════════════════════════

def test_decoder_adjudicated_lookup():
    d = Decoder(AdjudicationStore())
    v = d._decode_one("2_001", "sc2_flowchart_usecase", {
        "dtype": "ACTOR_MISSING",
        "evidence": "表格Actor「开发人员」在图中无参与者节点"})
    assert v["label_source"] == "adjudicated"
    assert v["action"] == "pass"             # benign→pass
    assert v["confidence"] == pytest.approx(0.8, abs=0.05)  # 4/5票


def test_decoder_prior_and_abstain():
    d = Decoder(AdjudicationStore())
    # 无先验的(dtype, scene) → 弃权(沉默弃权, 不编造)
    v = d._decode_one("9_999", "sc9_nonexistent", {
        "dtype": "SOME_TYPE", "evidence": "whatever"})
    assert v["action"] == "abstain"
    assert v["q"] is None
    assert "无" in v["reason"] or "先验" in v["reason"]


def test_decoder_tau_band():
    lo, hi = 0.3, 0.7
    d = Decoder(AdjudicationStore(), tau_hi=hi, tau_lo=lo)
    assert d.tau_hi == hi and d.tau_lo == lo
    # 带内→abstain语义由类型先验落点决定(结构性检查, 不依赖具体数据)


def test_decoder_channel_semantics():
    d = Decoder(AdjudicationStore())
    assert d.store is not None
    # 通道注册完备性: ADJUDICATION通道存在且语义已定义
    assert Channel.ADJUDICATION.value == "adjudication"
