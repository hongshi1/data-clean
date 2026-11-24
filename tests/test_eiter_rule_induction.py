"""Tests for tools/eiter_rule_induction.py (P3 Eiter loop pilot).

Unit-level only: change-op validation/application, pack round-trip through
load_rulepack, failure harvesting, prompt determinism, gate decisions and
greedy/backward-prune logic with an injected fake evaluator. No LLM call,
no subprocess, no GPU (the recorded runs cover the end-to-end loop).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.eiter_rule_induction import (
    GateBaseline,
    RuleChange,
    batch_failures,
    build_pack_raw,
    build_system_prompt,
    build_user_prompt,
    gate_check,
    greedy_accept,
    backward_prune,
    harvest_failures,
    merge_changes,
    pack_diff_targets,
    pack_known_names,
    parse_teacher_changes,
    write_and_validate_pack,
)

BASE = Path(__file__).resolve().parents[1]
GENERIC = BASE / "config/rulepacks/srs_gjb_v1.json"


@pytest.fixture()
def generic_raw() -> dict:
    return json.loads(GENERIC.read_text(encoding="utf-8"))


@pytest.fixture()
def known(generic_raw: dict) -> dict:
    return pack_known_names(generic_raw)


# ── 1. 教师JSON解析与白名单校验 ─────────────────────────────


def test_parse_rejects_unknown_op(known: dict) -> None:
    payload = {"diagnosis": "x", "changes": [
        {"op": "delete_everything", "reason": "bad"}]}
    changes, errors = parse_teacher_changes(payload, known, ["C06QA-001"])
    assert changes == []
    assert len(errors) == 1 and "非法op" in errors[0]["error"]


def test_parse_rejects_missing_reason(known: dict) -> None:
    payload = {"changes": [
        {"op": "set_threshold", "key": "id_join_support_conf",
         "value": 0.9}]}
    with pytest.raises(ValueError, match="changes"):
        parse_teacher_changes({}, known, [])
    changes, errors = parse_teacher_changes(payload, known, [])
    assert changes == [] and "reason" in errors[0]["error"]


def test_parse_rejects_nonexistent_names(known: dict) -> None:
    cases = [
        {"op": "replace_extraction_template", "name": "no_such_template",
         "pattern": "a+", "flags": 0, "reason": "r"},
        {"op": "add_canon_map", "kind": "no_such_kind",
         "entries": {"a": "b"}, "reason": "r"},
        {"op": "add_vocabulary_words", "vocab": "no_such_vocab",
         "words": ["x"], "reason": "r"},
        {"op": "set_threshold", "key": "no_such_threshold",
         "value": 0.5, "reason": "r"},
        {"op": "set_join_param", "expert": "no_such_expert",
         "key": "k", "value": 1, "reason": "r"},
    ]
    for item in cases:
        changes, errors = parse_teacher_changes(
            {"changes": [item]}, known, [])
        assert changes == []
        assert "不存在" in errors[0]["error"] or "非法" in errors[0]["error"]


def test_parse_rejects_bad_regex_and_range(known: dict) -> None:
    changes, errors = parse_teacher_changes({"changes": [
        {"op": "replace_extraction_template", "name": "id_pattern",
         "pattern": "([", "flags": 0, "reason": "r"}]}, known, [])
    assert changes == [] and "正则编译失败" in errors[0]["error"]
    changes, errors = parse_teacher_changes({"changes": [
        {"op": "set_threshold", "key": "id_join_support_conf",
         "value": 1.5, "reason": "r"}]}, known, [])
    assert changes == [] and "阈值" in errors[0]["error"]


def test_parse_accepts_valid_ops_and_mixed_batch(known: dict) -> None:
    payload = {"diagnosis": "ok", "changes": [
        {"op": "add_vocabulary_words", "vocab": "enum_terminal_bases",
         "words": ["车载"], "reason": "06号出现新终端形态"},
        {"op": "set_threshold", "key": "id_join_support_conf",
         "value": 0.85, "reason": "降低join支持阈值"},
        {"op": "add_vocabulary_words", "vocab": "不存在的词表",
         "words": ["x"], "reason": "坏条目"},
    ]}
    changes, errors = parse_teacher_changes(payload, known, ["C06QA-001"])
    assert [c.op for c in changes] == ["add_vocabulary_words",
                                       "set_threshold"]
    assert len(errors) == 1 and "不存在" in errors[0]["error"]
    assert changes[0].source_failures == ("C06QA-001",)


# ── 2. 变更应用与pack往返(load_rulepack符号验证) ──────────────


def test_apply_ops_and_pack_roundtrip(generic_raw: dict,
                                      tmp_path: Path) -> None:
    changes = [
        RuleChange(op="add_canon_map",
                   params={"kind": "trace_table",
                           "entries": {"本文档名称/标识": "本文档名称标识"}},
                   reason="06号逆向表头无'的'"),
        RuleChange(op="add_vocabulary_words",
                   params={"vocab": "enum_terminal_bases", "words": ["车载"]},
                   reason="06号新终端形态"),
        RuleChange(op="set_id_family_prefixes",
                   params={"prefixes": ["PZXQ-YXZCFW"]},
                   reason="06号ID族限定"),
        RuleChange(op="replace_extraction_template",
                   params={"name": "id_pattern",
                           "pattern": r"(?P<root>PZXQ)-[A-Z0-9-]+",
                           "flags": 32},
                   reason="06号ID根族"),
    ]
    raw = build_pack_raw(generic_raw, changes, "test_pack",
                         "test", {"round": 1})
    # 应用生效
    assert (raw["table_schemas"]["trace_table"]["canon_map"]
            ["本文档名称/标识"] == "本文档名称标识")
    assert "车载" in raw["term_vocabularies"]["enum_terminal_bases"]
    assert (raw["join_params"]["id_join"]["id_family_prefixes"]
            == ["PZXQ-YXZCFW"])
    assert (raw["extraction_templates"]["id_pattern"]["pattern"]
            == r"(?P<root>PZXQ)-[A-Z0-9-]+")
    # 基线不被污染(深拷贝)
    assert "车载" not in generic_raw["term_vocabularies"][
        "enum_terminal_bases"]
    # 符号验证: load_rulepack全schema校验通过
    info = write_and_validate_pack(raw, tmp_path / "test_pack.json")
    assert info["pack_id"] == "test_pack"
    # 溯源段
    assert len(raw["_eiter"]["changes"]) == 4


def test_apply_rejects_group_dropping_replace(generic_raw: dict) -> None:
    # enum_device原模板含命名组items; 丢组的替换必须被拒
    change = RuleChange(op="replace_extraction_template",
                        params={"name": "enum_device", "pattern": "无组正则",
                                "flags": 32},
                        reason="r")
    with pytest.raises(ValueError, match="丢失命名组"):
        change.apply(json.loads(json.dumps(generic_raw)))


def test_write_and_validate_rejects_bad_pack(generic_raw: dict,
                                             tmp_path: Path) -> None:
    from algorithms.consistency.rulepack import load_rulepack  # noqa: F401

    raw = build_pack_raw(generic_raw, [], "bad_pack", "", {})
    raw["thresholds"]["id_join_support_conf"] = 2.0  # 非法阈值
    with pytest.raises(ValueError):
        write_and_validate_pack(raw, tmp_path / "bad.json")


# ── 3. 合并与冲突 ───────────────────────────────────────────


def test_merge_changes_unions_and_keeps_conflicts() -> None:
    a = RuleChange(op="add_canon_map",
                   params={"kind": "trace_table",
                           "entries": {"A": "a"}},
                   reason="r1", source_failures=("F1",))
    b = RuleChange(op="add_canon_map",
                   params={"kind": "trace_table",
                           "entries": {"B": "b"}},
                   reason="r1", source_failures=("F2",))
    merged = merge_changes([a, b])
    assert len(merged) == 1
    assert merged[0].params["entries"] == {"A": "a", "B": "b"}
    assert merged[0].source_failures == ("F1", "F2")

    # v2语义: 同落点冲突(非并集op)不丢弃——两个候选都进贪心验证回路
    c = RuleChange(op="set_threshold",
                   params={"key": "k", "value": 0.5}, reason="r1")
    d = RuleChange(op="set_threshold",
                   params={"key": "k", "value": 0.7}, reason="r2")
    merged = merge_changes([c, d])
    assert len(merged) == 2
    assert [m.params["value"] for m in merged] == [0.5, 0.7]

    # 精确重复(op+params相同): 去重并合并来源失败例
    e = RuleChange(op="set_threshold",
                   params={"key": "k", "value": 0.5}, reason="r1",
                   source_failures=("F1",))
    f = RuleChange(op="set_threshold",
                   params={"key": "k", "value": 0.5}, reason="r1",
                   source_failures=("F2",))
    merged = merge_changes([e, f])
    assert len(merged) == 1
    assert merged[0].source_failures == ("F1", "F2")


# ── 4. 失败例采集与分批 ──────────────────────────────────────


def _row(iid: str, family: str, label: str) -> dict:
    return {
        "instance_id": iid, "family": family, "operator": "op",
        "sound_label": label, "label_proof": "proof",
        "question": "q", "answer": "a",
        "evidence": [{"evidence_id": f"{iid}-ev", "text": "证据文本",
                      "source_type": "text",
                      "source_ref": {"section": "3.2"}}],
    }


def test_harvest_and_batch() -> None:
    rows = [_row("C06QA-001", "trace_binding", "support"),
            _row("C06QA-002", "trace_binding", "refute"),
            _row("C06QA-003", "capability_device", "support"),
            _row("C06QA-004", "enum_family_x", "not_in_evidence")]
    outcome = {
        "verdicts": {"C06QA-001": "not_in_evidence",
                     "C06QA-002": "not_in_evidence",
                     "C06QA-003": "support",
                     "C06QA-004": "not_in_evidence"},
        "wrong": ["C06QA-001", "C06QA-002", "C06QA-004"],
        "failure_claims": {"C06QA-001": {
            "claims": [{
                "claim_text": "claim", "verdict": "not_in_evidence",
                "method": "semantic_unresolved", "rationale": "r"}],
            "trace": {"statements": ["[ev-1#s0] 语句A"],
                      "enum_registry": ["X/方式名称={桌面}"],
                      "enum_assertions": ["subjects=[X], members=[平板],"
                                          " kind=terminal"],
                      "id_registry": [], "id_claims": []}}},
    }
    failures = harvest_failures(rows, outcome)
    assert [f["instance_id"] for f in failures] == [
        "C06QA-004", "C06QA-001", "C06QA-002"]  # family排序
    with_claims = next(f for f in failures if f["misfiring_claims"])
    assert with_claims["instance_id"] == "C06QA-001"
    assert with_claims["misfiring_claims"][0]["method"] == (
        "semantic_unresolved")
    assert with_claims["gold"] == "support"
    assert with_claims["engine_trace"]["statements"] == ["[ev-1#s0] 语句A"]

    batches = batch_failures(failures, batch_size=1)
    assert [b[0]["family"] for b in batches] == [
        "enum_family_x", "trace_binding", "trace_binding"]


# ── 5. prompt构造(确定性+内容) ───────────────────────────────


def test_prompts_deterministic_and_contentful(generic_raw: dict) -> None:
    failures = harvest_failures(
        [_row("C06QA-001", "trace_binding", "support")],
        {"verdicts": {"C06QA-001": "not_in_evidence"},
         "wrong": ["C06QA-001"],
         "failure_claims": {"C06QA-001": {
             "claims": [], "trace": {"statements": ["[ev#s0] 语句A"],
                                     "enum_registry": ["X/方式名称={桌面}"],
                                     "enum_assertions": [], "id_registry": [],
                                     "id_claims": []}}}})
    system = build_system_prompt()
    assert "只输出一个JSON对象" in system
    assert "replace_extraction_template" in system
    assert "引擎实际视图" in system

    user1 = build_user_prompt(failures, generic_raw, [], 1)
    user2 = build_user_prompt(failures, generic_raw, [], 1)
    assert user1 == user2
    assert "C06QA-001" in user1
    assert "证据文本" in user1
    assert "语句A" in user1          # trace渲染
    assert "X/方式名称={桌面}" in user1
    assert generic_raw["pack_id"] in user1

    prev = [RuleChange(op="set_threshold",
                       params={"key": "k", "value": 0.5}, reason="上轮")]
    user3 = build_user_prompt(failures, generic_raw, prev, 2)
    assert "已接受的上一轮变更" in user3
    assert "第2轮" in user3


# ── 6. 闸门决策 ─────────────────────────────────────────────


def _outcome(wrong: list[str], macro: float = 0.7212, acc: float = 0.9121,
             expert_failures: dict | None = None) -> dict:
    return {"wrong": wrong,
            "metrics": {"macro_f1": macro, "accuracy": acc},
            "expert_failures": expert_failures or {}}


def _baseline() -> GateBaseline:
    return GateBaseline(
        qa91=_outcome(["S1QA-001"]),
        crossdoc=_outcome(["C06QA-001", "C06QA-002", "C06QA-003"]))


def test_gate_pass_and_instance_regression() -> None:
    baseline = _baseline()
    ok, _ = gate_check(_outcome(["C06QA-001"]), _outcome(["S1QA-001"]),
                       baseline)
    assert ok
    # 91QA新增错例→拒
    ok, why = gate_check(_outcome(["C06QA-001"]),
                         _outcome(["S1QA-001", "S1QA-002"]), baseline)
    assert not ok and "91QA新增错例" in why
    # crossdoc新增错例→拒(基线wrong={001,002,003})
    ok, why = gate_check(_outcome(["C06QA-001", "C06QA-999"]),
                         _outcome(["S1QA-001"]), baseline)
    assert not ok and "crossdoc06新增错例" in why


def test_gate_aggregate_and_expert_veto() -> None:
    baseline = _baseline()
    ok, why = gate_check(None, _outcome(["S1QA-001"], macro=0.70),
                         baseline)
    assert not ok and "聚合回退" in why
    ok, why = gate_check(_outcome(["C06QA-001"],
                                  expert_failures={"expert_x_failed": 1}),
                         None, baseline)
    assert not ok and "专家运行时异常" in why


# ── 7. 贪心接受与逆向剪枝(注入假评测器) ───────────────────────


class _FakeEval:
    """eval_trial桩: 按trial pack内变更集签名返回闸门剧本."""

    def __init__(self, baseline: GateBaseline,
                 behavior: dict[tuple[str, ...],
                                tuple[bool, str, int]]) -> None:
        self.baseline = baseline
        self.behavior = behavior
        self.calls: list[Path] = []

    def _name(self, change: dict) -> str:
        params = change["params"]
        tag = (params.get("key") or params.get("kind")
               or params.get("vocab") or params.get("name") or "?")
        return f"{change['op']}:{tag}"

    def __call__(self, path: Path) -> tuple[bool, str, dict]:
        self.calls.append(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        signature = tuple(self._name(c) for c in raw["_eiter"]["changes"])
        ok, reason, wrong_n = self.behavior.get(
            signature, (True, "ok", len(self.baseline.crossdoc["wrong"])))
        wrong = list(self.baseline.crossdoc["wrong"])[:wrong_n]
        return ok, reason, _outcome(wrong)


def _mini_raw() -> dict:
    return {
        "pack_id": "mini", "description": "",
        "gjb_rule_library_path": "knowledge/gjb_438c_rules_full.json",
        "table_schemas": {"trace_table": {
            "signatures": [{"caption_contains_any": ["追踪性"]}],
            "canon_map": {"a": "b"}, "key_columns": ["k"],
            "column_profiles": {"default": ["k"]},
            "direction_first_column_prefix": "任务书",
            "direction_markers": ["任务书", "本文档"],
            "trace_key_columns": {"forward": ["f"], "reverse": ["r"]}},
            "generic_table": {"signatures": []}},
        "classify_order": ["trace_table", "generic_table"],
        "extraction_templates": {"id_pattern": {"pattern": "A+", "flags": 0}},
        "term_vocabularies": {"enum_terminal_bases": ["桌面"]},
        "join_params": {"id_join": {}},
        "thresholds": {"id_join_support_conf": 0.9},
    }


def test_greedy_accept_rejects_gate_failures(tmp_path: Path) -> None:
    baseline = _baseline()
    behavior = {
        ("set_threshold:id_join_support_conf",): (False, "91QA新增错例", 1),
        ("add_vocabulary_words:enum_terminal_bases",): (True, "ok", 0),
    }
    fake = _FakeEval(baseline, behavior)
    changes = [
        RuleChange(op="set_threshold",
                   params={"key": "id_join_support_conf", "value": 0.5},
                   reason="r"),
        RuleChange(op="add_vocabulary_words",
                   params={"vocab": "enum_terminal_bases", "words": ["车载"]},
                   reason="r"),
    ]
    accepted, rejected, outcome = greedy_accept(
        changes, _mini_raw(), "t", tmp_path, 1, fake)
    assert [c.op for c in accepted] == ["add_vocabulary_words"]
    assert rejected[0]["stage"] == "gate"
    assert outcome is not None and outcome["wrong"] == []


def test_greedy_accept_rejects_count_regression(tmp_path: Path) -> None:
    baseline = _baseline()
    # 闸门全过但crossdoc错例数从1回退到2 → 拒
    behavior = {("set_threshold:id_join_support_conf",): (True, "ok", 2)}
    fake = _FakeEval(baseline, behavior)
    changes = [RuleChange(op="set_threshold",
                          params={"key": "id_join_support_conf",
                                  "value": 0.5}, reason="r")]
    accepted, rejected, _ = greedy_accept(
        changes, _mini_raw(), "t", tmp_path, 1, fake)
    assert not accepted
    assert rejected[0]["stage"] == "crossdoc06_count"


def test_backward_prune_removes_inert_changes(tmp_path: Path) -> None:
    baseline = _baseline()
    canon = ("add_canon_map:trace_table",)
    vocab = ("add_vocabulary_words:enum_terminal_bases",)
    # 剧本: 空集错例1; +canon惰性(仍1); +vocab有效(0)
    behavior = {
        (): (True, "ok", 1),
        canon: (True, "ok", 1),
        canon + vocab: (True, "ok", 0),
        vocab: (True, "ok", 0),
    }
    fake = _FakeEval(baseline, behavior)
    changes = [
        RuleChange(op="add_canon_map",
                   params={"kind": "trace_table", "entries": {"x": "y"}},
                   reason="r"),
        RuleChange(op="add_vocabulary_words",
                   params={"vocab": "enum_terminal_bases", "words": ["车载"]},
                   reason="r"),
    ]
    # greedy: 两条全接受(先惰性后有效, wrong 1->1->0)
    accepted, _rejected, outcome = greedy_accept(
        changes, _mini_raw(), "g", tmp_path, 1, fake)
    assert len(accepted) == 2
    assert outcome is not None and len(outcome["wrong"]) == 0
    # prune: canon移除后wrong仍0(惰性) → 剪掉; vocab移除后wrong回1 → 保留
    kept, outcome = backward_prune(accepted, _mini_raw(), "p", tmp_path, 0,
                                   fake)
    assert [c.op for c in kept] == ["add_vocabulary_words"]
    assert outcome is not None and len(outcome["wrong"]) == 0


def test_backward_prune_can_prune_to_empty(tmp_path: Path) -> None:
    """v1缺陷回归: 全部变更惰性时, 最小pack=空集(基线)."""
    baseline = _baseline()
    canon = ("add_canon_map:trace_table",)
    vocab = ("add_vocabulary_words:enum_terminal_bases",)
    behavior = {(): (True, "ok", 1), canon: (True, "ok", 1),
                canon + vocab: (True, "ok", 1), vocab: (True, "ok", 1)}
    fake = _FakeEval(baseline, behavior)
    changes = [
        RuleChange(op="add_canon_map",
                   params={"kind": "trace_table", "entries": {"x": "y"}},
                   reason="r"),
        RuleChange(op="add_vocabulary_words",
                   params={"vocab": "enum_terminal_bases", "words": ["车载"]},
                   reason="r"),
    ]
    accepted, _rejected, _outcome = greedy_accept(
        changes, _mini_raw(), "g", tmp_path, 1, fake)
    assert len(accepted) == 2
    kept, outcome = backward_prune(accepted, _mini_raw(), "p", tmp_path, 1,
                                   fake)
    assert kept == []
    assert outcome is not None and len(outcome["wrong"]) == 1


# ── 8. 人工pack diff(重叠度分析的口径) ────────────────────────


def test_pack_diff_targets_real_packs(generic_raw: dict) -> None:
    manual = json.loads(
        (BASE / "config/rulepacks/doc06_v1.json").read_text(encoding="utf-8"))
    targets = pack_diff_targets(generic_raw, manual)
    assert any("id_family_prefixes" in t for t in targets)
    assert any("trace_table.canon_map" in t for t in targets)
    # 方向性: generic vs manual 只报manual独有/差异; 描述类字段跳过
    assert not any("description" in t or "pack_id" in t for t in targets)


def test_final_eiter_pack_loads_and_keeps_standard_knowledge() -> None:
    """最终教师pack(交付物)的守卫: schema校验通过+标准级知识不动."""
    path = BASE / "config/rulepacks/doc06_eiter_v1.json"
    if not path.exists():
        pytest.skip("doc06_eiter_v1.json未产出(负面结果run, 见报告)")
    from algorithms.consistency.rulepack import load_rulepack

    pack = load_rulepack(str(path))
    assert pack.pack_id == "doc06_eiter_v1"
    raw = json.loads(path.read_text(encoding="utf-8"))
    generic = json.loads(GENERIC.read_text(encoding="utf-8"))
    # 教师不可触达的标准级/全局键逐字保留
    assert raw["gjb"] == generic["gjb"]
    assert raw["gjb_rule_library_path"] == generic["gjb_rule_library_path"]
    assert raw["classify_order"] == generic["classify_order"]
    # 溯源段: 每条接受变更带op/target/reason/source_failures
    assert raw["_eiter"]["changes"]
    for change in raw["_eiter"]["changes"]:
        assert change["op"] and change["target"] and change["reason"]


def test_change_target_paths() -> None:
    cases = [
        (RuleChange(op="replace_extraction_template",
                    params={"name": "id_pattern", "pattern": "A",
                            "flags": 0}), "extraction_templates.id_pattern"),
        (RuleChange(op="add_canon_map",
                    params={"kind": "trace_table", "entries": {}}),
         "table_schemas.trace_table.canon_map"),
        (RuleChange(op="set_id_family_prefixes",
                    params={"prefixes": ["P"]}),
         "join_params.id_join.id_family_prefixes"),
        (RuleChange(op="set_join_param",
                    params={"expert": "e", "key": "k", "value": 1}),
         "join_params.e.k"),
        (RuleChange(op="add_vocabulary_words",
                    params={"vocab": "v", "words": []}),
         "term_vocabularies.v"),
        (RuleChange(op="set_threshold",
                    params={"key": "t", "value": 0.5}), "thresholds.t"),
    ]
    for change, expected in cases:
        assert change.target_path() == expected
