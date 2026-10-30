"""公开baseline确定性内核测试 (BGE三元中心法/映射/子采样/prompt/加载器).

不触网/不加载torch: 只测纯函数内核与数据加载器; 数据依赖用例以
数据文件存在为前提(skipif, 与test_crossdoc_evalset同一约定).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.consistency import public_baselines as pb  # noqa: E402
from public_nli_bench import (  # noqa: E402
    CROSSDOC06,
    parse_ocnli_prompt,
    subsample,
)
from tools import public_nli_bench as bench  # noqa: E402

XNLI = BASE / "data/gjb_438c/public_nli/xnli_zh_test.parquet"
OCNLI = BASE / "data/gjb_438c/public_nli/ocnli_official_test.json"
CMNLI = BASE / "data/gjb_438c/public_nli/cmnli_test_std.jsonl"
QA91 = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")


# ── 纯函数: BGE三元中心法 ──────────────────────────────────────────────────


def _norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def test_pair_feature_unit_norm_and_determinism():
    u_p = [1.0, 0.0, 0.5, 0.0]
    u_h = [0.0, 1.0, 0.0, 0.5]
    feature = pb.pair_feature(u_p, u_h)
    assert len(feature) == 4 * len(u_p)
    assert _norm(feature) == pytest.approx(1.0, abs=1e-9)
    assert pb.pair_feature(u_p, u_h) == feature


def test_pair_feature_aligned_vs_opposite():
    aligned = pb.pair_feature([1.0, 0.0], [1.0, 0.0])
    opposite = pb.pair_feature([1.0, 0.0], [-1.0, 0.0])
    # 对齐对与相反对的特征应可分(逐元素积分量方向不同)
    assert aligned != opposite
    assert _norm(aligned) == pytest.approx(1.0, abs=1e-9)
    assert _norm(opposite) == pytest.approx(1.0, abs=1e-9)


def test_pair_feature_rejects_bad_input():
    with pytest.raises(ValueError):
        pb.pair_feature([], [1.0])
    with pytest.raises(ValueError):
        pb.pair_feature([1.0, 0.0], [1.0])


def test_fit_centroids_requires_all_classes():
    with pytest.raises(ValueError):
        pb.fit_centroids({"support": [[1.0, 0.0]]})


def test_nearest_centroid_classifies_synthetic_clusters():
    support_c = [1.0, 0.0, 0.0, 0.0]
    refute_c = [0.0, 1.0, 0.0, 0.0]
    nie_c = [0.0, 0.0, 1.0, 0.0]
    centroids = pb.fit_centroids({
        "support": [support_c, support_c],
        "refute": [refute_c, refute_c],
        "not_in_evidence": [nie_c, nie_c],
    })
    assert set(centroids) == set(pb.VERDICTS)
    for vector, expected in ((support_c, "support"), (refute_c, "refute"),
                             (nie_c, "not_in_evidence")):
        verdict, scores = pb.nearest_centroid(vector, centroids)
        assert verdict == expected
        assert set(scores) == set(pb.VERDICTS)
        assert scores[expected] == pytest.approx(max(scores.values()), abs=1e-9)


class _StubBge:
    """BgeLocal桩: 固定向量规则(无模型/无IO), 测纯内核链路."""

    def __init__(self) -> None:
        self.last_error = ""
        self.calls = 0

    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        self.calls += 1
        table = {"P_S": [1.0, 0.0, 0.0, 0.0], "H_S": [1.0, 0.0, 0.0, 0.0],
                 "P_R": [1.0, 0.0, 0.0, 0.0], "H_R": [-1.0, 0.0, 0.0, 0.0],
                 "P_N": [1.0, 0.0, 0.0, 0.0], "H_N": [0.0, 1.0, 0.0, 0.0]}
        return {t: table.get(t, [0.5, 0.5, 0.5, 0.5]) for t in texts}


def test_bge_fit_and_verdicts_with_stub_embedder():
    stub = _StubBge()
    fit_pairs = [
        {"premise": "P_S", "hypothesis": "H_S", "label": "support"},
        {"premise": "P_R", "hypothesis": "H_R", "label": "refute"},
        {"premise": "P_N", "hypothesis": "H_N", "label": "not_in_evidence"},
    ]
    centroids = pb.bge_fit_from_pairs(stub, fit_pairs)
    test_pairs = [
        {"premise": "P_S", "hypothesis": "H_S", "label": "support"},
        {"premise": "P_R", "hypothesis": "H_R", "label": "refute"},
        {"premise": "P_N", "hypothesis": "H_N", "label": "not_in_evidence"},
        # 空premise(如91QA-S1QA-062无冻结证据)→保守NIE, 不送嵌入
        {"premise": "", "hypothesis": "H_S", "label": "not_in_evidence"},
    ]
    assert pb.bge_centroid_verdicts(test_pairs, stub, centroids) == [
        "support", "refute", "not_in_evidence", "not_in_evidence"]


def test_bge_embed_pairs_raises_on_missing_vector():
    class _Broken:
        last_error = "stub failure"

        def embed(self, texts: list[str]) -> dict[str, list[float]]:
            return {t: [] for t in texts}

    with pytest.raises(RuntimeError, match="BGE embedding失败"):
        pb.bge_embed_pairs(_Broken(), [{"premise": "x", "hypothesis": "y"}])


# ── 纯函数: GLM直推prompt与解析 ────────────────────────────────────────────


def test_build_public_pair_prompt_deterministic():
    prompt_a = pb.build_public_pair_prompt("前提甲", "假设乙")
    prompt_b = pb.build_public_pair_prompt("前提甲", "假设乙")
    assert prompt_a == prompt_b
    assert "前提甲" in prompt_a and "假设乙" in prompt_a
    assert prompt_a.endswith("}") or "verdict" in prompt_a


def test_parse_public_verdict():
    assert pb.parse_public_verdict({"verdict": "support"}) == "support"
    assert pb.parse_public_verdict({"verdict": "Refute "}) == "refute"
    assert pb.parse_public_verdict({"verdict": "not in evidence"}) == \
        "not_in_evidence"
    assert pb.parse_public_verdict({"verdict": "unknown"}) == ""
    assert pb.parse_public_verdict("not a dict") == ""
    assert pb.parse_public_verdict({}) == ""


# ── 纯函数: 子采样/OCNLI prompt解析 ────────────────────────────────────────


def test_subsample_deterministic_and_order_preserving():
    items = [{"id": i} for i in range(100)]
    first = subsample(items, 30, 42)
    second = subsample(items, 30, 42)
    assert first == second
    assert len(first) == 30
    indices = [item["id"] for item in first]
    assert indices == sorted(indices)
    assert subsample(items, 200, 42) == items
    assert subsample(items, 30, 43) != first


def test_parse_ocnli_prompt():
    prompt = ("任务说明...\n句子1：身上裹一件棉大衣\n句子2：身上至少一件衣服")
    assert parse_ocnli_prompt(prompt) == ("身上裹一件棉大衣", "身上至少一件衣服")
    with pytest.raises(ValueError):
        parse_ocnli_prompt("无句子对的内容")


# ── 本地NLI直推内核 ────────────────────────────────────────────────────────


def test_nli_verdicts_empty_pairs_never_load_model():
    pairs = [{"premise": "", "hypothesis": "非空"}, {"premise": "非空", "hypothesis": ""}]
    assert pb.nli_verdicts(pairs, "C:/nonexistent/nli/model") == \
        ["not_in_evidence", "not_in_evidence"]


def test_nli_verdicts_missing_checkpoint_raises():
    bogus = str(BASE / "models/nli/__no_such_checkpoint__")
    with pytest.raises(RuntimeError, match="NLI模型加载失败"):
        pb.nli_verdicts([{"premise": "a", "hypothesis": "b"}], bogus)


# ── 数据加载器 (依赖真实数据文件, skipif) ──────────────────────────────────


@pytest.mark.skipif(not XNLI.exists(), reason="XNLI-zh测试集缺失")
def test_load_xnli_zh():
    pairs = bench.load_xnli_zh()
    assert len(pairs) == 5010
    assert pairs[0]["label"] in pb.VERDICTS
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair["label"]] = counts.get(pair["label"], 0) + 1
    assert counts == {"support": 1670, "refute": 1670, "not_in_evidence": 1670}


@pytest.mark.skipif(not OCNLI.exists(), reason="OCNLI官方test缺失")
def test_load_ocnli_test_empirical_label_mapping():
    """OCNLI官方test实证映射: 锚点对(裹棉大衣→至少一件衣服, 明显蕴含)
    必须落在support; 分布947/900/1103与官方label计数{2:947,0:900,1:1103}
    按 2→support/0→refute/1→NIE 对齐(文件内prompt文本不可信, 见loader)."""
    pairs = bench.load_ocnli_test()
    assert len(pairs) == 2950
    anchor = pairs[0]
    assert anchor["premise"].startswith("身上裹一件")
    assert anchor["hypothesis"] == "身上至少一件衣服"
    assert anchor["label"] == "support"
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair["label"]] = counts.get(pair["label"], 0) + 1
    assert counts == {"support": 947, "refute": 900, "not_in_evidence": 1103}


@pytest.mark.skipif(not CMNLI.exists(), reason="CMNLI测试集缺失")
def test_load_cmnli_test():
    pairs = bench.load_cmnli_test()
    assert len(pairs) == 12241
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair["label"]] = counts.get(pair["label"], 0) + 1
    assert counts == {"support": 4277, "refute": 4038, "not_in_evidence": 3926}


@pytest.mark.skipif(not (QA91.exists() and SILVER.exists()),
                    reason="91QA冻结语料/silver标签缺失")
def test_load_selfbuilt_91qa():
    pairs = bench.load_selfbuilt_91qa()
    assert len(pairs) == 91
    counts: dict[str, int] = {}
    for pair in pairs:
        assert len(pair["premise"]) <= 1500
        assert pair["hypothesis"]  # answer非空
        counts[pair["label"]] = counts.get(pair["label"], 0) + 1
    assert counts == {"support": 6, "refute": 8, "not_in_evidence": 77}
    # id与冻结语料行序对齐(GLM列judge_direct_llm按同文件序逐位对齐的前提)
    frozen_ids = [str(row["instance_id"])
                  for row in bench.load_frozen_qa()]
    assert [p["id"] for p in pairs] == [f"qa91-{i}" for i in frozen_ids]


@pytest.mark.skipif(not CROSSDOC06.exists(), reason="crossdoc06评测集缺失")
def test_load_selfbuilt_crossdoc06():
    pairs = bench.load_selfbuilt_crossdoc06()
    assert len(pairs) == 30
    counts: dict[str, int] = {}
    for pair in pairs:
        assert len(pair["premise"]) <= 1500
        counts[pair["label"]] = counts.get(pair["label"], 0) + 1
    assert counts == {"support": 10, "refute": 10, "not_in_evidence": 10}
