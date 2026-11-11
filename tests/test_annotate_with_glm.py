"""annotate_with_glm确定性内核测试: 采样/prompt/标签解析/一致率(不触网)."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))
import annotate_with_glm as agl  # noqa: E402
import build_pair_labels  # noqa: E402


def test_parse_label_exact_and_fenced():
    assert agl.parse_label("true_conflict") == "true_conflict"
    assert agl.parse_label("`legit_variance`") == "legit_variance"
    assert agl.parse_label("标签：needs_review。") == "needs_review"


def test_parse_label_ambiguous_or_none():
    assert agl.parse_label("true") is None            # 截断/布尔输出→解析失败
    assert agl.parse_label("") is None
    assert agl.parse_label("true_conflict 或 needs_review") is None  # 多标签歧义


def test_cand_pair_id_byte_compatible_with_build_pair_labels():
    row = {"doc_id": "02", "param": "response_time", "decision": "conflict_same_scope",
           "left": {"claim_id": "CLM-a", "value": 3.0, "section": "1.8.2.1"},
           "right": {"claim_id": "CLM-b", "value": 5.0, "section": "1.8.5.1.1"}}
    assert agl.cand_pair_id(row) == build_pair_labels.pair_id(row)


def test_cache_key_deterministic():
    k1 = agl.cache_key("glm-5.3", agl.SYSTEM_PROMPT, "用户消息")
    k2 = agl.cache_key("glm-5.3", agl.SYSTEM_PROMPT, "用户消息")
    k3 = agl.cache_key("glm-5", agl.SYSTEM_PROMPT, "用户消息")
    assert k1 == k2 and k1 != k3 and len(k1) == 20


def test_build_user_prompt_contains_core_fields():
    item = {"source": "human48", "doc_id": "02", "param": "response_time",
            "left": {"section": "1.8.2.1", "operator": "≥", "value": 3.0,
                     "unit": "秒", "scope_hint": "用户", "context": "上下文L"},
            "right": {"section": "1.8.5.1", "operator": "≥", "value": 5.0,
                      "unit": "秒", "scope_hint": "用户", "context": "上下文R"}}
    p = agl.build_user_prompt(item)
    for frag in ("文档: 02", "参数: response_time", "章节1.8.2.1", "3.0秒",
                 "章节1.8.5.1", "5.0秒", "true_conflict", "legit_variance",
                 "extraction_error", "needs_review"):
        assert frag in p


def test_cohen_kappa_known_values():
    assert agl.cohen_kappa(["a", "a"], ["a", "a"]) == 1.0
    assert agl.cohen_kappa(["a", "b"], ["b", "a"]) == -1.0
    assert agl.cohen_kappa([], []) == 0.0


def test_report_agreement_counts():
    r = agl.report_agreement({"p1": "true_conflict", "p2": "legit_variance"},
                             {"p1": "true_conflict", "p2": "needs_review",
                              "p3": "needs_review"})
    assert r["n_overlap"] == 2
    assert r["exact_agreement"] == 0.5
    assert r["confusion(human→glm)"]["needs_review"]["legit_variance"] == 1


def test_build_sample_composition_and_determinism():
    if not (agl.PAIRS_PATH.exists() and agl.CAND_PATH.exists()
            and agl.FINDINGS_PATH.exists()):
        return  # 数据资产缺失时跳过(快照依赖本地数据集)
    items = agl.build_sample(112, 40, 42)
    items2 = agl.build_sample(112, 40, 42)
    assert len(items) == 200
    assert [i["pair_id"] for i in items] == [i["pair_id"] for i in items2]
    srcs = {i["source"] for i in items}
    assert srcs == {"human48", "cand_weak", "findings"}
    # 强候选(conflict_same_scope)全取: 人工48对里12条强候选均在采样内
    strong = {i["pair_id"] for i in items if i["decision"] == "conflict_same_scope"}
    assert len(strong) >= 12
    # findings项带表格定位且渲染走findings分支
    f = next(i for i in items if i["source"] == "findings")
    assert "表" in agl.build_user_prompt(f)


def test_findings_only_value_conflict():
    if not agl.FINDINGS_PATH.exists():
        return
    items = agl.build_sample(0, 5, 42)
    fitems = [i for i in items if i["source"] == "findings"]
    assert len(fitems) == 5
    assert all(i["decision"] == "value_conflict" for i in fitems)
