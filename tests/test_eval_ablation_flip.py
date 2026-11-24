"""Tests for tools/eval_ablation_flip.py (99号Phase 0-E2, FAE/EviScope口径).

三层:
  1. 扰动算子纯函数: remove_cited/replace_cited/remove_irrelevant/
     add_distractor的证据集变换语义(移除恰为cited/原位替换计数/保留
     cited∪gold/追加预算);
  2. 干扰池与四条件: 确定性+文本不重叠; 合成original/variants→
     (a)-(d)布尔与n/a语义(未检出实例b/d=None);
  3. 集成快照: 确定性module跑DOC04-VIO-01全5次真实verify——
     remove_cited/replace_cited翻转(refute→NIE), 无关扰动verdict与
     定位签名稳定; 复跑确定性.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    read_jsonl,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_ablation_flip import (  # noqa: E402
    ADD_DISTRACTOR_BUDGET,
    DISTRACTOR_POOL_SIZE,
    OPERATOR_EXPECTATION,
    PERTURBATION_OPERATORS,
    aggregate_conditions,
    block_ref,
    cited_blocks,
    distractor_pool,
    four_conditions,
    normalize_text,
    result_signature,
)
from tools.eval_ablation_flip import (  # noqa: E402
    op_add_distractor,
    op_remove_cited,
    op_remove_irrelevant,
    op_replace_cited,
    run_ablation,
)

EVALSET = (BASE / "data/gjb_438c/localization_gold"
           / "violation_evalset_v1.jsonl")
ROWS = read_jsonl(EVALSET)


def _ev(evidence_id: str, text: str) -> dict:
    return {"evidence_id": evidence_id, "text": text}


def _row() -> dict:
    return {
        "instance_id": "T-VIO-01",
        "question": "q",
        "answer": "a",
        "context_freeze_id": "freeze",
        "evidence": [
            _ev("T-VIO-01-ev-000001", "块甲"),
            _ev("T-VIO-01-ev-000002", "块乙"),
            _ev("T-VIO-01-ev-000003", "块丙"),
            _ev("T-VIO-01-ev-000004", "块丁"),
        ],
        "gold_evidence_refs": ["T-VIO-01-ev-000002"],
    }


def _pool() -> list[dict]:
    return [_ev("DOC04-VIO-09-ev-000001", "干扰一"),
            _ev("DOC04-VIO-09-ev-000002", "干扰二"),
            _ev("DOC04-VIO-09-ev-000003", "干扰三")]


# ------------------------------------------------------------ 基础纯函数


def test_block_ref_and_normalize() -> None:
    assert block_ref("ev-000222#s7") == "ev-000222"
    assert normalize_text("块 甲 \n 乙") == "块甲乙"


def test_operator_registry_matches_expectation_table() -> None:
    assert set(PERTURBATION_OPERATORS) == set(OPERATOR_EXPECTATION)
    assert len(PERTURBATION_OPERATORS) == 4  # 17×4=68变体的算子面


def test_remove_cited_removes_exactly_cited() -> None:
    row = _row()
    cited = {"T-VIO-01-ev-000001", "T-VIO-01-ev-000003"}
    kept, meta = op_remove_cited(row, cited, [])
    assert [e["evidence_id"] for e in kept] == [
        "T-VIO-01-ev-000002", "T-VIO-01-ev-000004"]
    assert meta["n_removed"] == 2
    assert meta["removed_ids"] == sorted(cited)
    # 空cited(未检出)→无操作
    kept_none, meta_none = op_remove_cited(row, set(), [])
    assert len(kept_none) == 4
    assert meta_none["n_removed"] == 0


def test_replace_cited_position_preserving() -> None:
    row = _row()
    cited = {"T-VIO-01-ev-000002", "T-VIO-01-ev-000004"}
    new_evidence, meta = op_replace_cited(row, cited, _pool())
    ids = [e["evidence_id"] for e in new_evidence]
    # 原位替换: 位置1和3换干扰块, 位置0/2保留原块
    assert ids == ["T-VIO-01-ev-000001", "DOC04-VIO-09-ev-000001",
                   "T-VIO-01-ev-000003", "DOC04-VIO-09-ev-000002"]
    assert meta["n_replaced"] == 2
    assert meta["n_cited"] == 2
    assert meta["pool_exhausted"] is False
    # 池耗尽: cited多于池→只换前n_pool个, 如实记录
    big_cited = {f"T-VIO-01-ev-00000{i}" for i in (1, 2, 3, 4)}
    partial, meta_partial = op_replace_cited(row, big_cited, _pool()[:1])
    assert meta_partial["n_replaced"] == 1
    assert meta_partial["pool_exhausted"] is True
    assert [e["evidence_id"] for e in partial] == [
        "DOC04-VIO-09-ev-000001", "T-VIO-01-ev-000002",
        "T-VIO-01-ev-000003", "T-VIO-01-ev-000004"]


def test_remove_irrelevant_keeps_cited_and_gold() -> None:
    row = _row()
    cited = {"T-VIO-01-ev-000001"}
    kept, meta = op_remove_irrelevant(row, cited, [])
    # keep = cited(1) ∪ gold(2) → 只删块丙/块丁
    assert [e["evidence_id"] for e in kept] == [
        "T-VIO-01-ev-000001", "T-VIO-01-ev-000002"]
    assert meta["n_removed"] == 2
    assert meta["no_irrelevant_blocks"] is False
    # 全保留(无无关块)→no-op标记
    keep_all, meta_all = op_remove_irrelevant(
        row, {"T-VIO-01-ev-000001", "T-VIO-01-ev-000002",
              "T-VIO-01-ev-000003", "T-VIO-01-ev-000004"}, [])
    assert meta_all["no_irrelevant_blocks"] is True
    assert len(keep_all) == 4


def test_add_distractor_appends_budget() -> None:
    row = _row()
    combined, meta = op_add_distractor(row, set(), _pool())
    assert len(combined) == 4 + min(ADD_DISTRACTOR_BUDGET, 3)
    assert [e["evidence_id"] for e in combined[:4]] == \
        [e["evidence_id"] for e in row["evidence"]]
    assert meta["n_added"] == 3
    assert meta["added_ids"] == ["DOC04-VIO-09-ev-000001",
                                 "DOC04-VIO-09-ev-000002",
                                 "DOC04-VIO-09-ev-000003"]


def test_distractor_pool_deterministic_and_non_overlapping() -> None:
    first = distractor_pool(ROWS, 0, pool_size=5)
    again = distractor_pool(ROWS, 0, pool_size=5)
    assert [e["evidence_id"] for e in first] == \
        [e["evidence_id"] for e in again]
    own_texts = {normalize_text(e["text"]) for e in ROWS[0]["evidence"]}
    assert all(normalize_text(e["text"]) not in own_texts
               for e in first)
    own_ids = {e["evidence_id"] for e in ROWS[0]["evidence"]}
    assert not (own_ids & {e["evidence_id"] for e in first})
    # 默认预算
    assert len(distractor_pool(ROWS, 0)) <= DISTRACTOR_POOL_SIZE


# ------------------------------------------------------------ 四条件


def _outcome(verdict: str, blocks: list[str]) -> dict:
    return {"verdict": verdict,
            "signature": {"cited_blocks": blocks,
                          "answer_spans": [], "n_localizations":
                          len(blocks)}}


def test_four_conditions_full_matrix() -> None:
    original = _outcome("refute", ["b1", "b2"])
    variants = {
        "remove_cited": _outcome("not_in_evidence", []),
        "replace_cited": _outcome("not_in_evidence", []),
        "remove_irrelevant": _outcome("refute", ["b1", "b2"]),
        "add_distractor": _outcome("refute", ["b1", "b2"]),
    }
    conditions = four_conditions(original, variants)
    assert conditions["a_verdict_stable_irrelevant"] is True
    assert conditions["b_key_removal_flips"] is True
    assert conditions["c_localization_stable_irrelevant"] is True
    assert conditions["d_localization_follows_replacement"] is True
    assert conditions["d_status"] == "flipped"

    # migrated: 换关键证据后仍refute但引用迁移(干扰诱发)
    migrated = dict(variants,
                    replace_cited=_outcome("refute", ["d1"]))
    cond_m = four_conditions(original, migrated)
    assert cond_m["d_localization_follows_replacement"] is True
    assert cond_m["d_status"] == "migrated"

    # unchanged_fail: 换关键证据后仍refute且引用不变
    unchanged = dict(variants,
                     replace_cited=_outcome("refute", ["b1", "b2"]))
    cond_u = four_conditions(original, unchanged)
    assert cond_u["d_localization_follows_replacement"] is False
    assert cond_u["d_status"] == "unchanged_fail"

    # b失败: 移除关键证据仍refute(证据依赖不足)
    sticky = dict(variants,
                  remove_cited=_outcome("refute", ["b9"]))
    cond_b = four_conditions(original, sticky)
    assert cond_b["b_key_removal_flips"] is False

    # a/c失败: 无关扰动改变判定/定位
    unstable = dict(variants,
                    remove_irrelevant=_outcome("not_in_evidence", []),
                    add_distractor=_outcome("refute", ["d1", "d2"]))
    cond_a = four_conditions(original, unstable)
    assert cond_a["a_verdict_stable_irrelevant"] is False
    assert cond_a["c_localization_stable_irrelevant"] is False


def test_four_conditions_undetected_instance_na() -> None:
    original = _outcome("not_in_evidence", [])
    variants = {op: _outcome("not_in_evidence", [])
                for op in PERTURBATION_OPERATORS}
    conditions = four_conditions(original, variants)
    assert conditions["b_key_removal_flips"] is None
    assert conditions["d_localization_follows_replacement"] is None
    assert conditions["d_status"] == "n/a_undetected"
    # 无关扰动下原判定保持仍适用(a=True)
    assert conditions["a_verdict_stable_irrelevant"] is True


def test_aggregate_conditions_counts_and_na_denominators() -> None:
    details = [
        {  # 检出+四条件全成
            "instance_id": "i1", "violation_category": "identifier",
            "original": {"verdict": "refute"},
            "variants": {op: {"verdict": ("not_in_evidence"
                                          if op in ("remove_cited",
                                                    "replace_cited")
                                          else "refute")}
                         for op in PERTURBATION_OPERATORS},
            "conditions": {"a_verdict_stable_irrelevant": True,
                           "b_key_removal_flips": True,
                           "c_localization_stable_irrelevant": True,
                           "d_localization_follows_replacement": True,
                           "d_status": "flipped"},
        },
        {  # 检出但b失败(移除关键证据仍refute)
            "instance_id": "i2", "violation_category": "identifier",
            "original": {"verdict": "refute"},
            "variants": {op: {"verdict": "refute"}
                         for op in PERTURBATION_OPERATORS},
            "conditions": {"a_verdict_stable_irrelevant": True,
                           "b_key_removal_flips": False,
                           "c_localization_stable_irrelevant": True,
                           "d_localization_follows_replacement": False,
                           "d_status": "unchanged_fail"},
        },
        {  # 未检出: b/d n/a
            "instance_id": "i3", "violation_category": "document_name",
            "original": {"verdict": "not_in_evidence"},
            "variants": {op: {"verdict": "not_in_evidence"}
                         for op in PERTURBATION_OPERATORS},
            "conditions": {"a_verdict_stable_irrelevant": True,
                           "b_key_removal_flips": None,
                           "c_localization_stable_irrelevant": True,
                           "d_localization_follows_replacement": None,
                           "d_status": "n/a_undetected"},
        },
    ]
    summary = aggregate_conditions(details)
    assert summary["n_detected"] == 2
    assert summary["n_variants"] == 12  # 3实例×4算子
    # (b)(d)分母=detected(2); (a)(c)分母=全部(3)
    assert summary["four_conditions"]["b_key_removal_flips"] == {
        "n_satisfied": 1, "n_applicable": 2, "rate": 0.5}
    assert summary["four_conditions"]["a_verdict_stable_irrelevant"] == {
        "n_satisfied": 3, "n_applicable": 3, "rate": 1.0}
    assert summary["d_status_distribution"] == {"flipped": 1,
                                                "unchanged_fail": 1}
    # remove_cited翻转率: detected中1/2翻转到非refute
    assert summary["flip_rates"]["remove_cited"]["flip_rate"] == 0.5
    assert summary["flip_rates"]["remove_cited"]["n_applicable"] == 2
    # 无关算子: 全部实例(3)都应保持, i1/i2/i3都未变→0翻转
    assert summary["flip_rates"]["remove_irrelevant"]["flip_rate"] == 0.0
    assert summary["flip_rates"]["add_distractor"]["n_applicable"] == 3
    # 类别分组: document_name的b/d口径显式n/a
    assert summary["by_category"]["document_name"][
        "b_key_removal_flips"] == "0/0"


# ------------------------------------------------------------ 集成快照


def test_ablation_vio01_full_pipeline_deterministic() -> None:
    """DOC04-VIO-01全5次真实verify: 关键证据消融翻转, 无关扰动稳定.

    用前3行(干扰池需≥2实例: 单实例无兄弟证据可借); VIO-01的干扰池
    取VIO-02/VIO-03的前10个不重叠块, 与17条全量运行同序同内容.  """
    row = ROWS[0]
    assert row["instance_id"] == "DOC04-VIO-01"
    module = QAConsistencyModule(use_experts=True)
    details = run_ablation(ROWS[:3], module)
    detail = details[0]
    original = detail["original"]
    assert original["verdict"] == "refute"
    assert original["cited_blocks"] == [
        "DOC04-VIO-01-ev-000219", "DOC04-VIO-01-ev-000220",
        "DOC04-VIO-01-ev-000222", "DOC04-VIO-01-ev-000225"]
    variants = detail["variants"]
    # (b)移除4个关键证据块→refute翻转(证据依赖成立)
    assert variants["remove_cited"]["verdict"] == "not_in_evidence"
    assert variants["remove_cited"]["meta"]["n_removed"] == 4
    assert variants["remove_cited"]["n_evidence"] == 3
    # (d)关键证据原位替换为干扰块→翻转(flipped)
    assert variants["replace_cited"]["verdict"] == "not_in_evidence"
    assert variants["replace_cited"]["meta"]["n_replaced"] == 4
    # (a)(c)无关扰动: verdict保持refute, 定位签名不变
    assert variants["remove_irrelevant"]["verdict"] == "refute"
    assert variants["add_distractor"]["verdict"] == "refute"
    assert variants["remove_irrelevant"]["signature"] == \
        original["signature"]
    assert variants["add_distractor"]["signature"] == \
        original["signature"]
    conditions = detail["conditions"]
    assert conditions["a_verdict_stable_irrelevant"] is True
    assert conditions["b_key_removal_flips"] is True
    assert conditions["c_localization_stable_irrelevant"] is True
    assert conditions["d_localization_follows_replacement"] is True
    assert conditions["d_status"] == "flipped"
    # 确定性: 复跑同verdict同签名(真实推理可复现)
    again = run_ablation(ROWS[:3], module)[0]
    assert again["variants"]["remove_cited"]["verdict"] == \
        variants["remove_cited"]["verdict"]
    assert again["variants"]["add_distractor"]["signature"] == \
        variants["add_distractor"]["signature"]


def test_cited_blocks_and_signature_on_real_result() -> None:
    module = QAConsistencyModule(use_experts=True)
    result = module.verify(build_qa_input(ROWS[0]))
    assert cited_blocks(result) == {
        "DOC04-VIO-01-ev-000219", "DOC04-VIO-01-ev-000220",
        "DOC04-VIO-01-ev-000222", "DOC04-VIO-01-ev-000225"}
    signature = result_signature(result)
    assert signature["cited_blocks"] == sorted(cited_blocks(result))
    assert signature["n_localizations"] == 2
    # id_join定位的answer span=(26,46)在签名内(e1定位span缺失不入)
    assert signature["answer_spans"] == [[26, 46]]
