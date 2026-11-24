"""场景五"声明分解-接地-校验"回归测试(claim_verify.py: P2管线, 设计文档93号§4).

覆盖三层:
  ① decompose_claim — 声明文本→原子声明(词表规则: 空间/实体/状态/否定/量词/计数);
  ② ground_claims   — 原子声明→图内切片接地(x分位分区/最外侧者/失败原因学);
  ③ verify_qa       — per-fact三态校验+聚合, 以及44条内置数据集全量快照.

快照基于真实数据资产(qa_dataset.jsonl 44条 + visual_chunks_real.json真实YOLO观测,
均受MANIFEST保护): 分解/接地/校验为纯词法与几何规则, 无网络无随机, 结果确定性.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1] / "deploy" / "nkuDataProject" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from scenarios.kg_supervision import claim_verify  # noqa: E402

_DATASET = _BACKEND.parent / "data" / "kg_supervision" / "qa_dataset.jsonl"


def _claim(**kw: object) -> dict[str, object]:
    """测试用原子声明构造(补默认键)."""
    base: dict[str, object] = {"subject": None, "spatial": None, "object": None,
                               "state": None, "negated": False, "scope": None,
                               "count": None, "text": ""}
    base.update(kw)
    return base


# ══════════ ① decompose_claim ══════════

def test_decompose_claim_core_contract() -> None:
    """核心用例: 主体/空间/客体/状态/量词/计数/否定的词表解析."""
    # 主体+空间+客体+状态(未佩戴)
    claims = claim_verify.decompose_claim("画面中右侧人员未佩戴安全帽")
    assert len(claims) == 1
    c = claims[0]
    assert c["subject"] == "person"
    assert c["spatial"] == "right"
    assert c["object"] == "helmet"
    assert c["state"] == "not_wearing"
    assert c["negated"] is False
    assert c["text"] == "画面中右侧人员未佩戴安全帽"
    # 全称量词 + 肯定佩戴("所有/均"→scope=all)
    claims = claim_verify.decompose_claim("所有人员均佩戴")
    assert len(claims) == 1
    assert claims[0]["scope"] == "all"
    assert claims[0]["state"] == "wearing"
    assert claims[0]["subject"] == "person"
    # 存在性否定("无人员"→absent)
    claims = claim_verify.decompose_claim("画面中无人员")
    assert claims[0]["state"] == "absent"
    # 计数("(\d+)人"→count, 与状态共存)
    claims = claim_verify.decompose_claim("画面中有2人未佩戴安全帽")
    assert claims[0]["count"] == 2
    assert claims[0]["state"] == "not_wearing"
    assert claims[0]["object"] == "helmet"


def test_decompose_claim_negation_edges() -> None:
    """否定语义边界: 紧邻客体否定/外层否定/行为否定/省略句不发射."""
    # "无安全帽"(无+客体) → not_wearing而非negated
    claims = claim_verify.decompose_claim("画面左侧人员头部无安全帽")
    assert claims[0]["spatial"] == "left"
    assert claims[0]["state"] == "not_wearing"
    assert claims[0]["negated"] is False
    # "无人员持烟"=否定行为存在性(非absent): negated=True, 客体=香烟
    claims = claim_verify.decompose_claim("画面中无人员持烟或吸烟行为")
    assert claims[0]["state"] is None
    assert claims[0]["negated"] is True
    assert claims[0]["object"] == "cigarette"
    # "未见未佩戴情况"=外层否定翻转(无人未佩戴), 但无主体不独立成claim
    assert claim_verify.decompose_claim("未见未佩戴情况") == []
    # 限值/超出量不是观测计数("限定4人/超出1人"被抑制)
    claims = claim_verify.decompose_claim("画面中检测到5人，限定4人，超出1人")
    assert [c["count"] for c in claims] == [5]
    # 正常姿态词(站立/坐姿) → ¬prone
    claims = claim_verify.decompose_claim("画面中所有人员均保持站立或坐姿")
    assert claims[0]["state"] == "prone"
    assert claims[0]["negated"] is True
    assert claims[0]["scope"] == "all"


# ══════════ ② ground_claims ══════════

def test_ground_claims_right_zone_ppe_001() -> None:
    """空间接地成功: ppe_001"右侧人员"→右区最外侧人员(x=90%>67%)及其关联PPE."""
    g = claim_verify.ground_claims(
        [_claim(subject="person", spatial="right", object="helmet",
                state="not_wearing")], "ppe_001.jpg")
    assert len(g) == 1
    r = g[0]
    assert r["chunk"] is not None
    assert r["chunk"]["chunk_id"] == "ppe_001#p3"
    assert r["chunk"]["x_pct"] == pytest.approx(90.0, abs=0.5)
    assert r["chunk"]["zone"] == "right"  # 中心x/图宽 > 0.67
    assert r["ground_reason"].startswith("空间约束:右侧→人员#3(x=90%")
    # person+helmet → matched_person下标关联的PPE切片
    assert len(r["ppe_chunks"]) == 1
    assert r["ppe_chunks"][0]["ppe_class"] == "Hardhat"
    assert r["ppe_chunks"][0]["state"] == "worn"
    assert r["ppe_chunks"][0]["matched_person"] == 2  # 人员#3 = persons[2]


def test_ground_claims_zone_empty_is_ambiguous() -> None:
    """空间接地失败(ambiguous): 右区/左区无人时空间指代无法接地.

    真实数据注记: ppe_002最右人员x=61.4%<67%(右区空), ppe_003唯一人员x=71.5%(左区空).
    """
    claim = _claim(subject="person", spatial="right", object="helmet",
                   state="not_wearing")
    r = claim_verify.ground_claims([claim], "ppe_002.jpg")[0]
    assert r["chunk"] is None and r["chunks"] == []
    assert r["ground_reason"].startswith("ambiguous:右侧无人员")
    assert "x=61%" in r["ground_reason"]  # 最右人员分位随行(可解释)
    claim = _claim(subject="person", spatial="left", object="helmet",
                   state="not_wearing")
    r = claim_verify.ground_claims([claim], "ppe_003.jpg")[0]
    assert r["ground_reason"].startswith("ambiguous:左侧无人员")


def test_ground_claims_missing_and_no_ppe_channel() -> None:
    """观测缺失接地: 0人员(missing)与无口罩类PPE记录(空ppe_chunks)."""
    claim = _claim(subject="person", object="helmet", state="not_wearing")
    r = claim_verify.ground_claims([claim], "ppe_c1_002.jpg")[0]  # 真实检测0人
    assert r["chunk"] is None
    assert r["ground_reason"] == "missing:该图0人员"
    # 主体存在但该PPE族无检测记录(真实chunks仅Hardhat类)
    r = claim_verify.ground_claims(
        [_claim(subject="person", object="mask", state="not_wearing")],
        "mask_001.jpg")[0]
    assert len(r["chunks"]) == 8  # mask_001检测到8人
    assert r["ppe_chunks"] == []
    assert r["ground_reason"].startswith("无空间约束→全图人员")
    # 非人员主题(通道) → 无检测记录
    r = claim_verify.ground_claims([_claim(subject="corridor")], "corridor_001.jpg")[0]
    assert r["ground_reason"] == "missing:通道无检测记录"


# ══════════ ③ verify_qa(单条) ══════════

def test_verify_qa_absent_claim_matches_zero_persons() -> None:
    """锚点用例: ppe_c1_002真实检测0人, QA称无人员(answer=0) → support.

    (内置数据集中ppe_c1_002的实际记录为answer=1, 见下一条用例;
    本用例按声明极性核验"无人员"↔0人观测的一致性.)
    """
    r = claim_verify.verify_qa({"question": "判断图片中是否有人员佩戴安全帽",
                                "answer": 0, "evidence": ["画面中无人员"],
                                "image": "ppe_c1_002.jpg"})
    assert r["verdict"] == "support"
    assert r["nie_reason"] is None
    f = r["facts"][0]
    assert f["fact_verdict"] == "support"
    assert f["observation"] == "人员检测: 0人 @ppe_c1_002.jpg"
    assert "一致" in f["reason"]


def test_verify_qa_real_records() -> None:
    """真实记录核验: 矛盾(refute)/一致(support)/指代失败(NIE-ambiguous)/观测缺失."""
    if not _DATASET.exists():
        pytest.skip("内置数据集缺失")
    records = claim_verify._load_qa_records(_DATASET)
    assert len(records) == 44
    # #0 ppe_001: "右侧人员未佩戴" vs 右区人员#3佩戴Hardhat → refute(证据链可追溯)
    r = claim_verify.verify_qa(records[0])
    assert r["verdict"] == "refute"
    f = r["facts"][0]
    assert f["grounded_chunk"] == "人员#3(x=90%)"
    assert f["observation"] == "人员#3佩戴Hardhat(conf 0.66)"
    assert f["fact_verdict"] == "refute"
    # #1 ppe_002: "所有人员均佩戴" vs 5条PPE全worn → support
    r = claim_verify.verify_qa(records[1])
    assert r["verdict"] == "support"
    # #2 ppe_003: "左侧人员头部无安全帽" 但左区无人(唯一人员x=71.5%) → NIE(ambiguous)
    r = claim_verify.verify_qa(records[2])
    assert r["verdict"] == "NIE"
    assert r["nie_reason"] == "ambiguous"
    # #4 ppe_005: "画面中无人员" vs 真实检测7人 → refute(per-claim接地新发现的矛盾)
    r = claim_verify.verify_qa(records[4])
    assert r["verdict"] == "refute"
    assert "观测检测到7人" in r["facts"][0]["reason"]
    # #43 ppe_c1_002: "GJB438C区域人员未佩戴安全帽" vs 0人员 → NIE(missing_observation)
    r = claim_verify.verify_qa(records[43])
    assert r["verdict"] == "NIE"
    assert r["nie_reason"] == "missing_observation"
    assert r["facts"][0]["reason"].startswith("该图0人员")


def test_verify_qa_short_circuit_paths() -> None:
    """短路裁决: answer=2与answer非三值 → NIE(answer_unverifiable)."""
    r = claim_verify.verify_qa({"question": "判断图片中是否有人员摔倒或倒地",
                                "answer": 2, "evidence": ["画面模糊，无法确认人员姿态"],
                                "image": "fall_003.jpg"})
    assert r["verdict"] == "NIE"
    assert r["nie_reason"] == "answer_unverifiable"
    assert r["facts"][0]["reason_tag"] == "answer_unverifiable"
    r = claim_verify.verify_qa({"question": "判断图片中是否有人员未佩戴安全帽",
                                "answer": "yes", "evidence": ["有人员未佩戴安全帽"],
                                "image": "ppe_bad_001.jpg"})
    assert r["verdict"] == "NIE"  # answer='yes'非三值, 不可按三态核验
    assert r["nie_reason"] == "answer_unverifiable"


def test_verify_qa_sleep_claim_is_temporal_nie() -> None:
    """时序型声明: 睡岗(趴伏+长时间静止)单帧不可证 → 该fact=NIE(temporal)."""
    r = claim_verify.verify_qa({"question": "判断图片中是否存在人员睡岗行为",
                                "answer": 1, "evidence": ["人员趴伏于工位桌面且闭眼、长时间静止"],
                                "image": "sleep_001.jpg"})
    assert r["verdict"] == "NIE"
    assert r["nie_reason"] == "temporal"
    assert r["facts"][0]["fact_verdict"] == "nie"
    assert r["facts"][0]["reason_tag"] == "temporal"


# ══════════ ④ 44条全量快照 ══════════

def test_dataset_snapshot() -> None:
    """44条全量快照(数据资产受MANIFEST保护, 数字变更须有意为之).

    2026-11-24基线(声明分解-接地-校验P2管线首轮冻结):
      support×3  refute×12  NIE×29
      NIE原因分布: temporal×7 / missing_observation×17 / answer_unverifiable×4 / ambiguous×1

    与C-3 v0(答案极性×全图聚合, refuted=6)的差异来源(均为per-claim接地的有意升级):
      - 新发现矛盾: 无人员声明vs真实检测7人(#4)、倒地vs全员站立(#9/#12)、
        计数声明vs观测8人(#38-41);
      - 空间指代失败显NIE(ambiguous): #2"左侧人员"而唯一人员x=71.5%位于右区;
      - 口罩/防静电/香烟/手机/通道类无真实检测通道 → NIE(missing_observation)
        (v0的demo模拟Chunk按answer自证supported, 已被真实观测替代);
      - 时序门(睡岗/通话时长)优先于answer=2: 睡岗类QA统一NIE(temporal).
    """
    if not _DATASET.exists():
        pytest.skip("内置数据集缺失")
    results = claim_verify.run_dataset()
    assert len(results) == 44
    assert {r["qa_id"] for r in results} == {str(i) for i in range(44)}
    for r in results:
        assert r["image"].endswith(".jpg")
        assert r["verdict"] in ("support", "refute", "NIE")
        if r["verdict"] == "NIE":
            assert r["nie_reason"] in ("temporal", "missing_observation",
                                       "ambiguous", "answer_unverifiable")
        else:
            assert r["nie_reason"] is None
        assert r["facts"], "每条结果须携带per-fact证据链"

    counts = Counter(r["verdict"] for r in results)
    assert dict(counts) == {"support": 3, "refute": 12, "NIE": 29}

    nie = Counter(r["nie_reason"] for r in results if r["verdict"] == "NIE")
    assert dict(nie) == {"missing_observation": 17, "temporal": 7,
                         "answer_unverifiable": 4, "ambiguous": 1}

    # 冻结逐条verdict(qa_id=数据集行号, 按数值序)
    by_id = {r["qa_id"]: r["verdict"] for r in results}
    assert [k for k, v in sorted(by_id.items(), key=lambda kv: int(kv[0]))
            if v == "refute"] == [
        "0", "3", "4", "6", "8", "9", "12", "38", "39", "40", "41", "42"]
    assert [k for k, v in sorted(by_id.items(), key=lambda kv: int(kv[0]))
            if v == "support"] == ["1", "7", "10"]


def test_sleep_qas_are_nie_temporal() -> None:
    """睡岗类QA(question含"睡岗")应NIE(temporal): 判定对象是时序性行为.

    时序门优先于answer=2: sleep_004(answer=2)同样NIE(temporal)
    (其声明"无法确认人员是否处于睡眠状态"本就是时序型不可证).
    """
    if not _DATASET.exists():
        pytest.skip("内置数据集缺失")
    results = claim_verify.run_dataset()
    sleep = [r for r in results if "睡岗" in r["question"]]
    assert len(sleep) == 6
    for r in sleep:
        assert r["verdict"] == "NIE"
        assert r["nie_reason"] == "temporal"
    # 通话时长类(phone_bad_001: "通话时间不低于30秒")同为temporal
    r = next(x for x in results if x["image"] == "phone_bad_001.jpg")
    assert r["nie_reason"] == "temporal"
