"""ConfidenceModel单元测试: 校准语义的真实数据验证(依赖M3 calibration.json)."""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.blackboard.confidence import CALIB_PATH, ConfidenceModel
from algorithms.blackboard.schemas import Channel, ConfSource

pytestmark = pytest.mark.skipif(
    not CALIB_PATH.exists(), reason="M3 calibration.json缺失(真实数据未就绪)")


def test_deterministic_channels_are_construction_faithful():
    model = ConfidenceModel.load()
    for ch in (Channel.ANCHOR, Channel.KT, Channel.KP, Channel.ID_GRAPH,
               Channel.CHUNKS, Channel.DRIFT_CENSUS):
        c = model.for_channel(ch)
        assert c.value == 1.0
        assert c.source == ConfSource.DETERMINISTIC


def test_vlm_node_confidence_from_theta_global():
    model = ConfidenceModel.load()
    c = model.for_channel(Channel.VLM, claim="node")
    # θ_global node_precision = 0.9898
    assert c.source == ConfSource.CALIBRATED
    assert 0.98 <= c.value <= 1.0


def test_vlm_doc_conditioning():
    model = ConfidenceModel.load()
    doc = "07报文处理服务软件需求规格说明-终稿"
    c_doc = model.for_channel(Channel.VLM, claim="node", doc=doc)
    c_glb = model.for_channel(Channel.VLM, claim="node")
    # 07文档halluc_rate=0.0 → precision 1.0 > global 0.9898
    assert c_doc.value >= c_glb.value
    assert c_doc.source == ConfSource.CALIBRATED


def test_vlm_edge_confidence_uses_extra_rate():
    model = ConfidenceModel.load()
    c = model.for_channel(Channel.VLM, claim="edge")
    # 1 - edge_extra_rate(0.2406) = 0.759
    assert 0.75 <= c.value <= 0.76


def test_vlm_miss_rate_phi_conditioning():
    model = ConfidenceModel.load()
    small = model.vlm_miss_rate(n_nodes=3)    # small(≤5): 0.02
    large = model.vlm_miss_rate(n_nodes=15)   # large(>10): 0.113
    assert small < large
    assert small == pytest.approx(0.02, abs=1e-6)
    assert large == pytest.approx(0.113, abs=1e-6)


def test_ocr_heuristic_and_llm_cap():
    model = ConfidenceModel.load()
    c = model.for_channel(Channel.OCR)
    assert c.value == 0.5 and c.source == ConfSource.HEURISTIC
    c = model.for_channel(Channel.LLM)
    assert c.value <= 0.6 and c.source == ConfSource.LLM_SELF


def test_embedding_uncalibrated_falls_back_heuristic(tmp_path: Path):
    model = ConfidenceModel.load(emb_calib_path=tmp_path / "nope.json")
    c = model.for_channel(Channel.EMBEDDING)
    assert c.source == ConfSource.HEURISTIC
    assert c.value == 0.7


def test_embedding_calibrated_when_file_exists(tmp_path: Path):
    p = tmp_path / "emb.json"
    p.write_text('{"agreement_rate": 0.91, "n_emb_matches": 50}',
                 encoding="utf-8")
    model = ConfidenceModel(emb_calib={"agreement_rate": 0.91, "n_emb_matches": 50})
    c = model.for_channel(Channel.EMBEDDING)
    assert c.source == ConfSource.CALIBRATED
    assert c.value == pytest.approx(0.91)
