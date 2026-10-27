"""Tests for tools/preannotate_localization_gold.py (S7定位gold预标注).

三层测试:
  1. 纯函数: span子串校验/span payload解析/verdict混淆/span prompt;
  2. 小fixture流程(3条手工QA + 1条违例): 系统跑通, suggest字段写入,
     gold字段保持空, 违例条目skipped原样保留;
  3. 预算优先级: 超预算时silver判定性实例优先, NIE实例只填系统建议.

LLM mock: monkeypatch llm_json守卫 + 残差通道(llm_residual._call_llm)
+ span细化(_call_span_llm)双入口替换, 全程零真实调用.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency import llm_residual  # noqa: E402
from tools import preannotate_localization_gold as pag  # noqa: E402
from tools.build_localization_gold_template import (  # noqa: E402
    read_jsonl,
    write_jsonl,
)
from tools.preannotate_localization_gold import (  # noqa: E402
    span_in_block,
    span_in_evidence,
    span_prompt,
    parse_span_payload,
    preannotate,
    verdict_confusion,
)


# ------------------------------------------------------------ 合成fixture

def make_evidence(evidence_id: str, text: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "text": text,
        "source_type": "text",
        "source_ref": {"doc_id": "doc-fixture", "section": "3.2.1",
                        "page": 1, "block_id": f"block-{evidence_id}",
                        "row_id": "", "region_id": ""},
        "scope_id": f"doc-fixture:{evidence_id}",
        "completeness": "open",
        "completeness_proof": "fixture evidence",
    }


def make_frozen(instance_id: str, question: str, answer: str,
                evidence: list[dict]) -> dict:
    return {"instance_id": instance_id, "question": question,
            "answer": answer, "context_freeze_id": f"frozen-{instance_id}",
            "evidence": evidence}


def make_template_qa(instance_id: str, silver: str, question: str,
                     answer: str, evidence: list[dict]) -> dict:
    return {
        "schema": "s7_localization_gold_v1",
        "instance_id": instance_id,
        "task_type": "qa_verdict",
        "question": question,
        "answer": answer,
        "gold_verdict": silver,
        "claims": [{
            "claim_id": "c1",
            "claim_text": answer,
            "claim_verdict": silver,
            "gold_evidence_refs": [],
            "gold_span": "",
            "gold_nie_consulted_refs": [],
            "annotation_note": "",
            "silver_hint": {"verdict": silver, "evidence_refs": [],
                            "confidence": 0.9},
        }],
        "annotator": None,
        "annotator_confidence": None,
        "annotation_status": "pending",
        "round": 1,
        "gold_verdict_init": silver,
        "gold_verdict_init_source": "fixture_silver",
        "context_freeze_id": f"frozen-{instance_id}",
        "evidence_index": evidence,
        "system_prefill": None,
    }


def make_template_violation() -> dict:
    evidence = [make_evidence(
        "DOC04-VIO-01-ev-000220",
        "连接池配置ID与初始化ID同为PZXQ-GN-LJCGL-LJCCSH。")]
    return {
        "schema": "s7_localization_gold_v1",
        "instance_id": "DOC04-VIO-01",
        "task_type": "doc_violation",
        "question": None,
        "answer": None,
        "gold_verdict": "refute",
        "claims": [{
            "claim_id": "c1",
            "claim_text": "连接池配置/初始化同ID",
            "claim_verdict": "refute",
            "gold_evidence_refs": ["DOC04-VIO-01-ev-000220"],
            "gold_span": "",
            "gold_nie_consulted_refs": [],
            "annotation_note": "",
            "silver_hint": None,
        }],
        "annotator": None,
        "annotator_confidence": None,
        "annotation_status": "pending",
        "round": 1,
        "gold_verdict_init": "refute",
        "gold_verdict_init_source": "fixture",
        "category": "identifier",
        "evidence_index": evidence,
        "system_prefill": None,
    }


SUP_EV = [make_evidence("FX-001-ev-1", "系统支持热插拔与双机热备两种连接方式。")]
REF_EV = [make_evidence("FX-002-ev-1", "响应时间不超过200ms。")]
NIE_EV = [make_evidence("FX-003-ev-1", "系统支持热插拔与双机热备两种连接方式。")]


def build_fixture(tmp_path: Path) -> tuple[Path, Path, Path, list[dict]]:
    """3条手工QA(quoted→support / numeric→refute / quoted未命中→NIE)
    + 1条违例; 写模板与冻结QA文件, 返回(模板/冻结/输出路径, 模板行)."""
    frozen = [
        make_frozen("FX-001", "系统支持哪些连接方式？",
                    "系统支持「热插拔」连接方式。", SUP_EV),
        make_frozen("FX-002", "响应时间要求是多少？",
                    "响应时间不小于300ms。", REF_EV),
        make_frozen("FX-003", "系统提供哪些备份策略？",
                    "系统提供「异地容灾」备份策略。", NIE_EV),
    ]
    template = [
        make_template_qa("FX-001", "support", "系统支持哪些连接方式？",
                         "系统支持「热插拔」连接方式。", SUP_EV),
        make_template_qa("FX-002", "refute", "响应时间要求是多少？",
                         "响应时间不小于300ms。", REF_EV),
        make_template_qa("FX-003", "not_in_evidence", "系统提供哪些备份策略？",
                         "系统提供「异地容灾」备份策略。", NIE_EV),
        make_template_violation(),
    ]
    template_path = tmp_path / "annotation_template_v1.jsonl"
    frozen_path = tmp_path / "scene1_qa_frozen_v1.jsonl"
    out_path = tmp_path / "pre_annotated_v1.jsonl"
    write_jsonl(template_path, template)
    write_jsonl(frozen_path, frozen)
    return template_path, frozen_path, out_path, template


@pytest.fixture()
def llm_stub(monkeypatch: pytest.MonkeyPatch) -> dict:
    """LLM双入口mock(残差通道+span细化) + llm_json守卫: 零真实调用."""
    import algorithms.common.llm_client as llm_client

    state: dict = {"residual_prompts": [], "span_prompts": []}

    def guard(*args: object, **kwargs: object) -> object:
        raise AssertionError("测试中禁止真实LLM调用(llm_json)")

    def fake_residual(prompt: str) -> dict:
        state["residual_prompts"].append(prompt)
        claim_ids = re.findall(r"^c(\d+): ", prompt, flags=re.MULTILINE)
        return {"claims": [
            {"claim_id": f"c{i}", "verdict": "not_in_evidence",
             "evidence_refs": [], "rationale": "fixture残差NIE",
             "confidence": 0.5}
            for i in claim_ids]}

    def fake_span(prompt: str) -> dict:
        state["span_prompts"].append(prompt)
        if "热插拔" in prompt:
            return {"span": "系统支持热插拔"}
        if "响应时间" in prompt:
            return {"span": "响应时间不超过200ms"}
        return {"span": "无法定位的span"}

    monkeypatch.setattr(llm_client, "llm_json", guard)
    monkeypatch.setattr(llm_residual, "_call_llm", fake_residual)
    monkeypatch.setattr(pag, "_call_span_llm", fake_span)
    return state


# ------------------------------------------------------------ 纯函数

def test_span_in_block_substring_semantics() -> None:
    block = "异常流E1：系统提示连接失败，用例结束"
    assert span_in_block("系统提示连接失败", block)
    assert span_in_block("系统提示 连接失败", block)     # 空白归一
    assert span_in_block("系统提示连接失败，用例结束", block)
    assert not span_in_block("系统提示初始化失败", block)
    assert not span_in_block("", block)
    assert not span_in_block("   ", block)


def test_span_in_evidence_multi_block_and_conflict_pair() -> None:
    # 整段命中任一块
    assert span_in_evidence("甲行内容", ["乙行内容", "甲行内容"])
    # 冲突对(协议§4.4)；分隔的两段分别命中
    assert span_in_evidence("声明值为甲；声明值为乙",
                            ["配置声明值为甲", "配置声明值为乙"])
    # 只有一段命中不算有效
    assert not span_in_evidence("声明值为甲；声明值为丙",
                                ["配置声明值为甲", "配置声明值为乙"])
    # 半角分号同样切分
    assert span_in_evidence("甲值;乙值", ["字段为甲值", "字段为乙值"])
    # 空块/空span/单段未命中
    assert not span_in_evidence("甲", [])
    assert not span_in_evidence("", ["甲"])
    assert not span_in_evidence("值丙", ["声明值为甲"])


def test_parse_span_payload_strictness() -> None:
    assert parse_span_payload({"span": " abc "}) == "abc"
    assert parse_span_payload({"span": ""}) == ""
    assert parse_span_payload({}) == ""
    assert parse_span_payload({"span": None}) == ""
    assert parse_span_payload({"span": 123}) == ""
    assert parse_span_payload({"span": ["x"]}) == ""
    assert parse_span_payload("not-a-dict") == ""


def test_verdict_confusion_matrix() -> None:
    report = verdict_confusion(
        ["support", "refute", "not_in_evidence", "refute"],
        ["support", "not_in_evidence", "not_in_evidence", "refute"])
    assert report["n"] == 4
    assert report["agreement_rate"] == 0.75
    matrix = report["confusion_silver_x_system"]
    assert matrix["refute"]["refute"] == 1
    assert matrix["refute"]["not_in_evidence"] == 1
    assert matrix["support"]["support"] == 1
    assert matrix["not_in_evidence"]["not_in_evidence"] == 1
    # 全类标签都出现在矩阵中(含零格)
    for silver in ("support", "refute", "not_in_evidence"):
        assert set(matrix[silver]) == {"support", "refute", "not_in_evidence"}
    with pytest.raises(ValueError, match="等长"):
        verdict_confusion(["support"], ["support", "refute"])
    with pytest.raises(ValueError, match="非法verdict"):
        verdict_confusion(["maybe"], ["support"])


def test_span_prompt_contains_claim_verdict_evidence_and_contract() -> None:
    prompt = span_prompt("声明甲", "support", [("ev-1", "证据原文一")])
    assert "【声明】声明甲" in prompt
    assert "【系统判定】support" in prompt
    assert "ev-1: 证据原文一" in prompt
    assert '{"span": "..."}' in prompt


# ------------------------------------------------------------ 流程fixture

def test_preannotate_small_fixture(tmp_path: Path, llm_stub: dict) -> None:
    template_path, frozen_path, out_path, template = build_fixture(tmp_path)
    stats = preannotate(template_path=template_path, frozen_path=frozen_path,
                        out_path=out_path, span_budget=10)
    rows = read_jsonl(out_path)
    assert len(rows) == 4
    by_id = {row["instance_id"]: row for row in rows}

    # 系统跑通: fixture设计(quoted→support, numeric区间互斥→refute, 未命中→NIE)
    assert by_id["FX-001"]["system_suggest_verdict"] == "support"
    assert by_id["FX-002"]["system_suggest_verdict"] == "refute"
    assert by_id["FX-003"]["system_suggest_verdict"] == "not_in_evidence"

    # suggest字段写入(claim级全部来自系统输出)
    for iid in ("FX-001", "FX-002", "FX-003"):
        row = by_id[iid]
        assert row["pre_annotation_status"] == "pre_annotated"
        assert row["system_suggest_claims"]
        assert isinstance(row["system_suggest_refs"], list)
        for claim in row["system_suggest_claims"]:
            assert claim["system_suggest_verdict"] in (
                "support", "refute", "not_in_evidence")
            assert claim["llm_suggest_span"] is not None
            assert isinstance(claim["llm_suggest_span_verified"], bool)

    sup = next(c for c in by_id["FX-001"]["system_suggest_claims"]
               if c["system_suggest_verdict"] == "support")
    assert sup["system_suggest_refs"] == ["FX-001-ev-1"]
    assert sup["system_suggest_rationale"]
    assert sup["llm_suggest_span"] == "系统支持热插拔"
    assert sup["llm_suggest_span_verified"] is True
    ref = next(c for c in by_id["FX-002"]["system_suggest_claims"]
               if c["system_suggest_verdict"] == "refute")
    assert ref["llm_suggest_span"] == "响应时间不超过200ms"
    assert ref["llm_suggest_span_verified"] is True

    # NIE实例: 只填系统建议, 不做span细化
    for claim in by_id["FX-003"]["system_suggest_claims"]:
        assert claim["llm_suggest_span"] == ""
        assert claim["llm_suggest_span_verified"] is False

    # gold字段保持空(人工仍需填); 模板字段保留
    for row in rows:
        if row["task_type"] == "qa_verdict":
            assert row["annotation_status"] == "pending"
            assert row["annotator"] is None
            for claim in row["claims"]:
                assert claim["gold_evidence_refs"] == []
                assert claim["gold_span"] == ""
                assert claim["gold_nie_consulted_refs"] == []
    assert by_id["FX-001"]["question"] == "系统支持哪些连接方式？"
    assert by_id["FX-001"]["evidence_index"] == SUP_EV
    assert by_id["FX-002"]["claims"][0]["silver_hint"]["verdict"] == "refute"

    # 违例条目: skipped, 模板原样(含预填gold定位)不加suggest字段
    vio = by_id["DOC04-VIO-01"]
    assert vio["pre_annotation_status"] == "skipped"
    for key in ("system_suggest_verdict", "system_suggest_refs",
                "system_suggest_claims"):
        assert key not in vio
    assert vio["gold_verdict"] == "refute"
    assert vio["claims"][0]["gold_evidence_refs"] == ["DOC04-VIO-01-ev-000220"]

    # 模板文件未被修改/覆盖
    assert read_jsonl(template_path) == template

    # LLM调用: span细化2次(FX-001/FX-002的判定性claim), FX-003无
    assert len(llm_stub["span_prompts"]) == 2

    # stats自检
    assert stats["counts"]["qa_pre_annotated"] == 3
    assert stats["counts"]["violations_skipped"] == 1
    assert stats["counts"]["system_claims"] >= 3
    assert stats["llm_calls"]["span_calls"] == 2
    assert stats["llm_calls"]["span_budget_skipped_claims"] == 0
    assert stats["span_quality"]["n_span_candidates"] == 2
    assert stats["span_quality"]["n_span_valid"] == 2
    assert stats["span_quality"]["span_valid_rate"] == 1.0
    assert stats["span_quality"]["n_span_strict_block_substring"] == 2
    assert stats["system_vs_silver"]["agreement_rate"] == 1.0
    assert stats["system_vs_silver"]["confusion_silver_x_system"][
        "support"]["support"] == 1
    assert stats["span_call_failures"] == []
    assert stats["paths"]["out"] == str(out_path)


def test_preannotate_refuses_to_overwrite_template(
        tmp_path: Path, llm_stub: dict) -> None:
    template_path, frozen_path, out_path, _ = build_fixture(tmp_path)
    with pytest.raises(ValueError, match="不得指向template_path"):
        preannotate(template_path=template_path, frozen_path=frozen_path,
                    out_path=template_path)
    assert not out_path.exists()


def test_span_budget_prioritizes_silver_decisive_instances(
        tmp_path: Path, llm_stub: dict) -> None:
    """预算=1且silver-NIE实例排在模板前面: silver-support实例优先获得span.

    FX-009(模板序在前): silver=NIE但系统判定support(带引用)→span候选;
    FX-010(模板序在后): silver=support→预算优先; 预算=1只够一次调用.
    """
    ev = [make_evidence("FX-010-ev-1", "系统支持热插拔连接。")]
    frozen = [
        make_frozen("FX-009", "系统提供哪些备份策略？",
                    "系统提供「热插拔」容灾备份策略。", ev),
        make_frozen("FX-010", "系统支持哪些连接方式？",
                    "系统支持「热插拔」连接方式。", ev),
    ]
    template = [
        make_template_qa("FX-009", "not_in_evidence",
                         "系统提供哪些备份策略？",
                         "系统提供「热插拔」容灾备份策略。", ev),
        make_template_qa("FX-010", "support", "系统支持哪些连接方式？",
                         "系统支持「热插拔」连接方式。", ev),
    ]
    template_path = tmp_path / "annotation_template_v1.jsonl"
    frozen_path = tmp_path / "scene1_qa_frozen_v1.jsonl"
    out_path = tmp_path / "pre_annotated_v1.jsonl"
    write_jsonl(template_path, template)
    write_jsonl(frozen_path, frozen)

    stats = preannotate(template_path=template_path, frozen_path=frozen_path,
                        out_path=out_path, span_budget=1)
    rows = {row["instance_id"]: row for row in read_jsonl(out_path)}
    # 预算给了silver-support实例(模板序在后)而非silver-NIE实例(序在前)
    assert stats["llm_calls"]["span_calls"] == 1
    assert len(llm_stub["span_prompts"]) == 1
    support_claim = next(
        c for c in rows["FX-010"]["system_suggest_claims"]
        if c["system_suggest_verdict"] == "support")
    assert support_claim["llm_suggest_span"] == "系统支持热插拔"
    assert support_claim["llm_suggest_span_verified"] is True
    # FX-009(系统support但silver-NIE)被预算跳过: 只有系统建议, 无span
    skipped_claim = next(
        c for c in rows["FX-009"]["system_suggest_claims"]
        if c["system_suggest_verdict"] == "support")
    assert skipped_claim["llm_suggest_span"] == ""
    assert skipped_claim["llm_suggest_span_verified"] is False
    assert stats["llm_calls"]["span_budget_skipped_claims"] == 1


def test_preannotate_rejects_frozen_template_mismatch(
        tmp_path: Path, llm_stub: dict) -> None:
    template_path, frozen_path, out_path, template = build_fixture(tmp_path)
    # 冻结文件删掉FX-003 → 模板实例无系统输入
    frozen_rows = read_jsonl(frozen_path)[:2]
    write_jsonl(frozen_path, frozen_rows)
    with pytest.raises(ValueError, match="缺失模板实例"):
        preannotate(template_path=template_path, frozen_path=frozen_path,
                    out_path=out_path)
    # 模板schema非法(非法gold_verdict)也立即报错
    broken = [dict(row) for row in template]
    broken[0]["gold_verdict"] = "maybe"
    write_jsonl(template_path, broken)
    with pytest.raises(ValueError, match="非法gold_verdict"):
        preannotate(template_path=template_path, frozen_path=frozen_path,
                    out_path=out_path)
