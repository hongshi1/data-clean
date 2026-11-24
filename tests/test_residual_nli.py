"""场景五"NLI残差层"回归测试(nli_residual.py: P3第二项, 设计文档93号§4.3).

NLI判定结果的不确定性来源(模型权重/设备浮点)已被磁盘缓存消除:
nli_cache.json(46条)随数据资产交付, 缓存命中时不加载模型(pytest秒回);
缓存未命中时才加载Erlangshen-330M推理并写回(首跑约20s, GPU/CPU均可,
label由模型决定, 缓存保证后续运行确定).

冻结基线(2026-11-24, Erlangshen-Roberta-330M-NLI首轮, 44条内置数据集):
  verdict分布: refute×27  support×3  NIE×14
  与规则层claim_verify(12 refute/3 support/29 NIE)对照: agree×26  disagree×18
  数字变更须有意为之(换NLI模型/改观测序列化模板/改聚合规则时须同步更新).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _REPO_ROOT / "deploy" / "nkuDataProject" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_MODEL_DIR = (_REPO_ROOT / "models" / "nli" /
              "Erlangshen-Roberta-330M-NLI")
if not (_MODEL_DIR / "config.json").exists():
    pytest.skip("NLI模型目录缺失: models/nli/Erlangshen-Roberta-330M-NLI",
                allow_module_level=True)

from scenarios.kg_supervision import nli_residual  # noqa: E402

_DATA = _BACKEND.parent / "data" / "kg_supervision"
_DATASET = _DATA / "qa_dataset.jsonl"
_CACHE = _DATA / "nli_cache.json"


# ════════ ① serialize_observations(观测→自然语言premise) ════════

def test_serialize_observations_snapshot() -> None:
    """快照: 人数计数/空间分区词/姿态/PPE佩戴与族汇总/0人图.

    真实数据锚点: ppe_002检测5人(分区中间+左侧, 无右侧); ppe_001人员#3
    x=90%右区佩戴Hardhat(conf 0.66); ppe_c1_002真实检测0人0 PPE.
    """
    # ppe_002: 5人, 全佩戴 → 计数与汇总
    p = nli_residual.serialize_observations("ppe_002.jpg")
    assert p.startswith("检测到5人；")
    assert "人员#1位于中间(中心x=38%)，姿态站立，佩戴安全帽(state=worn,置信0.72)" in p
    assert "人员#2位于左侧(中心x=26%)" in p
    assert "左侧" in p and "中间" in p
    assert "右侧" not in p  # 该图最右人员x=61%<67%, 右区无人
    assert p.endswith("共检测到5个安全帽(5佩戴0未佩戴)。")
    # ppe_001: 4人(全右区), 人员#3关联佩戴
    p = nli_residual.serialize_observations("ppe_001.jpg")
    assert p.startswith("检测到4人；")
    assert "人员#3位于右侧(中心x=90%)，姿态站立，佩戴安全帽(state=worn,置信0.66)" in p
    assert "右侧" in p and "左侧" not in p
    assert "共检测到2个安全帽(2佩戴0未佩戴)。" in p
    # ppe_c1_002: 0人0 PPE
    assert nli_residual.serialize_observations("ppe_c1_002.jpg") == "未检测到人员。"


def test_serialize_observations_unmatched_person_has_no_ppe_phrase() -> None:
    """无关联PPE的人员只有位置+姿态段(matched_person未关联不猜测)."""
    p = nli_residual.serialize_observations("ppe_001.jpg")
    assert "人员#2位于右侧(中心x=88%)，姿态站立；" in p  # 无佩戴短语, 直接分句
    segs = p.rstrip("。").split("；")
    assert len(segs) == 4 + 1 + 1  # 人数头 + 4人员 + 安全帽汇总
    assert sum(1 for s in segs if "人员#" in s) == 4


# ════════ ② nli_verify(三态判定 + 磁盘缓存) ════════

def test_nli_verify_fixed_pairs_frozen() -> None:
    """固定对判定冻结: 0人premise的全称佩戴声明/无人员声明.

    ("未检测到人员。", "画面中所有人员均佩戴安全帽"): 语义上neutral或
    contradiction均可接受(空集全称命题), 实际冻结为contradiction→refute.
    ("未检测到人员。", "画面中无人员"): entailment→support.
    """
    r = nli_residual.nli_verify("未检测到人员。", "画面中所有人员均佩戴安全帽")
    assert r["label"] in ("neutral", "contradiction")  # 语义可接受域
    assert r["label"] == "contradiction"               # 冻结实际label
    assert r["verdict"] == "refute"
    assert set(r["proba"]) == set(nli_residual.LABELS)
    assert sum(r["proba"].values()) == pytest.approx(1.0, abs=1e-3)

    r = nli_residual.nli_verify("未检测到人员。", "画面中无人员")
    assert r["label"] == "entailment"                  # 冻结
    assert r["verdict"] == "support"


def test_nli_verify_deterministic_and_cached() -> None:
    """确定性+缓存: 二次调用cached=True且结果一致; 键落盘."""
    premise = "未检测到人员。"
    hypothesis = "画面中所有人员均佩戴安全帽"
    r1 = nli_residual.nli_verify(premise, hypothesis)
    r2 = nli_residual.nli_verify(premise, hypothesis)
    assert r2["cached"] is True  # 首跑写入缓存后必命中
    assert (r2["label"], r2["proba"], r2["verdict"]) == (
        r1["label"], r1["proba"], r1["verdict"])
    key = nli_residual._cache_key(premise, hypothesis)
    assert key in nli_residual._ensure_cache()
    if _CACHE.exists():
        disk = json.loads(_CACHE.read_text(encoding="utf-8"))
        assert disk[key]["label"] == r1["label"]


def test_nli_cache_rebuild_on_corruption(tmp_path: Path) -> None:
    """缓存容错: 缺失/损坏/条目畸形 → 重建(空或过滤), 合法条目保留."""
    # 缺失 → 空
    assert nli_residual._load_cache(tmp_path / "nope.json") == {}
    # JSON损坏 → 空(重建)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert nli_residual._load_cache(bad) == {}
    # 顶层非dict → 空
    bad2 = tmp_path / "bad2.json"
    bad2.write_text("[1, 2]", encoding="utf-8")
    assert nli_residual._load_cache(bad2) == {}
    # 条目畸形(label越界)被过滤, 合法条目保留
    good = tmp_path / "good.json"
    good.write_text(json.dumps({
        "k1": {"label": "entailment", "proba": {"entailment": 0.9,
                                                "neutral": 0.1,
                                                "contradiction": 0.0}},
        "k2": {"label": "weird", "proba": {}},
        "k3": "not-a-dict",
    }), encoding="utf-8")
    got = nli_residual._load_cache(good)
    assert set(got) == {"k1"}


# ════════ ③ residual_verify_qa(单条) ════════

def test_residual_verify_qa_sleep_claim_frozen() -> None:
    """睡岗QA: premise为8人站立观测 vs 声明趴伏 → 冻结contradiction/refute.

    规则层claim_verify对该QA判NIE(temporal, 单帧不可证)——NLI残差层从
    观测直接给出矛盾判定, 故agreement=disagree(级联两层的分歧样本).
    """
    rec = {"question": "判断图片中是否存在人员睡岗行为",
           "answer": 1,
           "evidence": ["人员趴伏于工位桌面且闭眼、长时间静止"],
           "task": "睡岗检测", "image": "sleep_001.jpg"}
    r = nli_residual.residual_verify_qa(rec)
    assert set(r) >= {"verdict", "label", "premise", "hypothesis", "proba",
                      "agreement"}
    assert r["premise"].startswith("检测到8人；")
    assert "姿态站立" in r["premise"]  # 真实观测: 全员站立
    assert r["hypothesis"] == "人员趴伏于工位桌面且闭眼、长时间静止"
    assert r["label"] == "contradiction"  # 冻结实际label
    assert r["verdict"] == "refute"
    assert r["agreement"] == "disagree"
    assert r["details"][0]["cached"] is True
    assert r["details"][0]["verdict"] == "refute"


def test_residual_verify_qa_multi_evidence_aggregation() -> None:
    """多条evidence聚合: 任一contradiction→refute(驱动条), 否则entailment."""
    # 混合: 一条entailment + 一条contradiction → refute, label取驱动条
    rec = {"question": "q", "answer": 1,
           "evidence": ["画面中无人员", "画面中所有人员均佩戴安全帽"],
           "image": "ppe_c1_002.jpg"}
    r = nli_residual.residual_verify_qa(rec)
    labels = [d["label"] for d in r["details"]]
    assert labels == ["entailment", "contradiction"]
    assert r["verdict"] == "refute"
    assert r["label"] == "contradiction"
    assert r["hypothesis"] == "画面中无人员"  # hypothesis取首条
    # 全neutral → NIE(香烟声明与人员/安全帽观测无关, 冻结自数据集#28)
    rec2 = {"question": "判断图片中是否有人员抽烟", "answer": 1,
            "evidence": ["画面中人员手持香烟，嘴部有烟雾"],
            "image": "smoke_001.jpg"}
    r2 = nli_residual.residual_verify_qa(rec2)
    assert r2["verdict"] == "NIE"
    assert r2["label"] == "neutral"


def test_residual_verify_qa_empty_evidence() -> None:
    """空evidence → 保守NIE(neutral), agreement仍与规则层对照."""
    rec = {"question": "q", "answer": 0, "evidence": [],
           "image": "ppe_c1_002.jpg"}
    r = nli_residual.residual_verify_qa(rec)
    assert r["verdict"] == "NIE"
    assert r["label"] == "neutral"
    assert r["hypothesis"] == ""
    assert r["details"] == []
    assert r["agreement"] in ("agree", "disagree", None)


# ════════ ④ 44条全量快照 ════════

def test_run_residual_dataset_snapshot() -> None:
    """44条全量verdict分布快照(数字变更须有意为之).

    2026-11-24基线(Erlangshen-Roberta-330M-NLI + 观测序列化premise首轮):
      refute×27  support×3  NIE×14;  agree×26  disagree×18
    与规则层(claim_verify: refute×12 support×3 NIE×29)的差异来源:
      NLI层把"观测中无此通道/全员站立vs倒地声明/无人员vs佩戴声明"直接判为
      contradiction(refute 27 vs 规则层12)——闭世界序列化premise使NLI更激进;
      规则层因时序门/观测缺失输出的大量NIE被残差层收窄(29→14).
    """
    if not _DATASET.exists():
        pytest.skip("内置数据集缺失")
    results = nli_residual.run_residual_dataset()
    assert len(results) == 44
    assert {r["qa_id"] for r in results} == {str(i) for i in range(44)}

    for r in results:
        assert r["image"].endswith(".jpg")
        assert r["verdict"] in ("support", "refute", "NIE")
        assert r["label"] in nli_residual.LABELS
        # label↔verdict映射一致(接反则全盘颠倒)
        assert nli_residual.NLI_TO_VERDICT[r["label"]] == r["verdict"]
        assert r["agreement"] in ("agree", "disagree")
        assert r["details"], "每条结果须携带逐evidence判定链"
        assert r["premise"], "每条结果须携带观测premise"

    counts = Counter(r["verdict"] for r in results)
    assert dict(counts) == {"refute": 27, "support": 3, "NIE": 14}

    agree = Counter(r["agreement"] for r in results)
    assert dict(agree) == {"agree": 26, "disagree": 18}

    by_id = {r["qa_id"]: r["verdict"] for r in results}
    order = sorted(by_id, key=int)
    assert [k for k in order if by_id[k] == "refute"] == [
        "0", "2", "3", "4", "5", "6", "8", "9", "10", "11", "12", "13",
        "15", "16", "19", "22", "23", "25", "26", "27", "29", "32",
        "38", "39", "40", "41", "42"]
    assert [k for k in order if by_id[k] == "support"] == ["1", "24", "34"]
    assert [k for k in order if by_id[k] == "NIE"] == [
        "7", "14", "17", "18", "20", "21", "28", "30", "31", "33",
        "35", "36", "37", "43"]


def test_run_residual_dataset_uses_cache_no_model_load() -> None:
    """交付缓存后全量运行纯缓存命中: 不加载模型(测试时长控制的保障)."""
    if not _DATASET.exists() or not _CACHE.exists():
        pytest.skip("内置数据集或交付缓存缺失")
    nli_residual._MODEL_STATE = None  # 重置惰性模型状态
    results = nli_residual.run_residual_dataset()
    assert all(d["cached"] for r in results for d in r["details"])
    assert nli_residual._MODEL_STATE is None  # 全程未加载模型
