"""tests for tools/e5_minimal_pairs.py (修复算子/安全中止/行级装配/终检)."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE), str(BASE / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from e5_minimal_pairs import (  # noqa: E402
    build_minimal_pair,
    load_candidates,
    member_runs,
    member_tokens,
    parse_table,
    repair_chapter_number,
    repair_enum_member,
    repair_id_binding,
    repair_numeric_value,
    repair_party_binding,
    _final_sweeps,
)

_Q = {"faithful": 3, "truthful": 3, "useful": 3, "gate_reason": "",
      "scored_by": "teacher"}


def _issue(quote: str, span: list[int], rule: str, ref: str = "ev-1",
           explanation: str = "与证据矛盾") -> dict:
    return {"quote": quote, "span": span, "rule_id": rule,
            "evidence_ref": ref, "explanation": explanation,
            "span_verified": True, "quality": dict(_Q)}


def _row(question: str, answer: str, evidence: list[str], issues: list[dict],
         sid: str = "T-001", verdict: str = "refute") -> dict:
    return {"corpus": "test", "instance_id": sid, "question": question,
            "answer": answer, "evidence": evidence, "verdict": verdict,
            "issues": issues}


# ── 表格解析 ─────────────────────────────────────────────────

_TABLE = """
<table><thead><tr><th>序号</th><th>Use case名称</th><th>项目唯一标识符</th>
<th>需求描述</th><th>需求重用</th><th>方式名称</th><th>运行状态</th>
<th>对应的任务书功能/性能</th></tr></thead><tbody><tr><td>1</td>
<td>布局控制</td><td>PZXQ-GN-BJKZ</td><td>提供布局显示控制功能</td>
<td>改进</td><td>平板、桌面、手持</td><td>集成阶段、运行阶段</td>
<td>4.1.3a)</td></tr></tbody></table>
"""


def test_parse_table_joins_split_cells():
    html = ("<table><tr><td><p>PZXQ-NBJK-YXZCFW-</p>"
            "<p>JCXXFWXTYXJKJK</p></td><td><p>用户</p><p>管理</p></td></tr>"
            "</table>")
    rows = parse_table(html)
    assert rows == [["PZXQ-NBJK-YXZCFW-JCXXFWXTYXJKJK", "用户管理"]]


def test_parse_table_full_fixture():
    rows = parse_table(_TABLE)
    assert rows[1][1] == "布局控制"
    assert rows[1][5] == "平板、桌面、手持"
    assert rows[1][7] == "4.1.3a)"


# ── 成员工具 ─────────────────────────────────────────────────

def test_member_tokens_device_and_stage():
    text = "仅在桌面、手持设备上使用，运行阶段不提供"
    assert member_tokens(text) == ["桌面", "手持", "运行阶段"]


def test_member_runs_detection():
    runs = member_runs("支持桌面、平板和手持终端；在开发阶段和集成阶段提供")
    assert [r[2] for r in runs] == [["桌面", "平板", "手持"],
                                    ["开发阶段", "集成阶段"]]


# ── 章节号修复(GJB-05) ───────────────────────────────────────

def test_repair_chapter_number():
    answer = "需求PZXQ-GN-JMKFKJ-JMKF追溯至任务书4.1.4章节，其内容对应4.1.4的功能要求。"
    ev = ("<table><thead><tr><th>序号</th><th>Use case名称</th>"
          "<th>项目唯一标识符</th><th>对应的任务书功能/性能</th></tr></thead>"
          "<tbody><tr><td>1</td><td>界面开发功能</td>"
          "<td>PZXQ-GN-JMKFKJ-JMKF</td><td>4.1.1</td></tr></tbody></table>")
    pos = answer.find("追溯至任务书4.1.4章节")
    row = _row("需求PZXQ-GN-JMKFKJ-JMKF追溯到任务书的哪一章节？", answer, [ev],
               [_issue("追溯至任务书4.1.4章节", [pos, pos + 13], "GJB-05")])
    fixed, outcome = repair_chapter_number(row, row["issues"][0], answer)
    assert outcome.ok and outcome.operator == "chapter_number"
    assert "4.1.4" not in fixed
    assert fixed == ("需求PZXQ-GN-JMKFKJ-JMKF追溯至任务书4.1.1章节，"
                     "其内容对应4.1.1的功能要求。")
    assert outcome.records[0] == {"old": "4.1.4", "new": "4.1.1",
                                  "note": "任务书章节号对齐证据行"}


def test_repair_chapter_composite_repeated_suffix():
    """回归: 证据单元格含重复字母后缀(4.2a)b)), 完整token替换不残留尾巴."""
    answer = ("需求PZXQ-GN-JRTYCS追溯至任务书4.1.1 a) /4.2 a)b)，"
              "对应任务书4.1.1 a) /4.2 a)b)的功能/性能要求。")
    ev = ("<table><thead><tr><th>序号</th><th>Use case名称</th>"
          "<th>项目唯一标识符</th><th>对应的任务书功能/性能</th></tr></thead>"
          "<tbody><tr><td>1</td><td>接入通用测试</td>"
          "<td>PZXQ-GN-JRTYCS</td><td><p>4.1.1b) /4.2a)b)</p></td></tr>"
          "</tbody></table>")
    pos = answer.find("追溯至任务书4.1.1 a) /4.2 a)b)")
    row = _row("需求PZXQ-GN-JRTYCS追溯到任务书的哪一章节？", answer, [ev],
               [_issue("追溯至任务书4.1.1 a) /4.2 a)b)",
                       [pos, pos + 20], "GJB-05")])
    fixed, outcome = repair_chapter_number(row, row["issues"][0], answer)
    assert outcome.ok
    assert fixed == ("需求PZXQ-GN-JRTYCS追溯至任务书4.1.1b)/4.2a)b)，"
                     "对应任务书4.1.1b)/4.2a)b)的功能/性能要求。")
    assert "b)b)" not in fixed.replace("a)b)", "")


def test_repair_chapter_ambiguous_quote_fails():
    answer = "需求PZXQ-GN-JMKFKJ-JMKF追溯至任务书4.1.4章节，另见4.2条。"
    ev = ("<table><tr><td>标识符</td><td>任务书</td></tr>"
          "<tr><td>PZXQ-GN-JMKFKJ-JMKF</td><td>4.1.1</td></tr></table>")
    row = _row("需求PZXQ-GN-JMKFKJ-JMKF追溯到任务书的哪一章节？", answer, [ev],
               [_issue("追溯至任务书4.1.4章节，另见4.2条", [0, 20], "GJB-05")])
    _fixed, outcome = repair_chapter_number(row, row["issues"][0], answer)
    assert not outcome.ok
    assert outcome.reason == "chapter_ambiguous_or_absent"


# ── 数值修复(PARAM-06) ───────────────────────────────────────

_PARAM_EV = ("<table><tr><td>序号</td><td>数据项</td><td>最大值</td>"
             "<td>最小值</td><td>精度</td><td>单位</td><td>备注</td></tr>"
             "<tr><td>1</td><td>组件名</td><td>1</td><td>-</td><td>-</td>"
             "<td>字节</td><td>-</td></tr></table>")


def test_repair_numeric_value():
    answer = "组件名的最大值为1024字节，该数据项的取值不能超过1024字节。"
    pos = answer.find("组件名的最大值为1024字节")
    row = _row("组件名的最大值是多少？", answer, [_PARAM_EV],
               [_issue("组件名的最大值为1024字节", [pos, pos + 16], "PARAM-06")])
    fixed, outcome = repair_numeric_value(row, row["issues"][0], answer)
    assert outcome.ok and outcome.operator == "numeric_value"
    assert fixed == "组件名的最大值为1字节，该数据项的取值不能超过1字节。"
    assert outcome.records[0]["old"] == "1024字节"


def test_repair_numeric_unit_incompatible_fails():
    answer = "组件名的最大值为100ms。"
    pos = answer.find("组件名的最大值为100ms")
    row = _row("组件名的最大值是多少？", answer, [_PARAM_EV],
               [_issue("组件名的最大值为100ms", [pos, pos + 14], "PARAM-06")])
    _fixed, outcome = repair_numeric_value(row, row["issues"][0], answer)
    assert not outcome.ok
    assert outcome.reason == "unit_incompatible"


def test_repair_numeric_ambiguous_fails():
    answer = "最大值为1024字节，最小值为10字节。"
    row = _row("组件名的最大值是多少？", answer, [_PARAM_EV],
               [_issue(answer, [0, len(answer)], "PARAM-06")])
    _fixed, outcome = repair_numeric_value(row, row["issues"][0], answer)
    assert not outcome.ok
    assert outcome.reason == "numeric_ambiguous_or_absent"


# ── 枚举修复(TERM-03) ────────────────────────────────────────

def test_repair_enum_member_add_text_evidence():
    answer = ("界面开发功能在设备支持方面包括以下内容：\n\n"
              "1. **桌面设备**：界面开发功能支持在桌面设备上使用，"
              "满足固定办公场景下的开发需求。\n"
              "2. **平板设备**：界面开发功能同样支持在平板设备上使用，"
              "便于在移动或便携场景下进行界面开发操作。\n\n"
              "综上所述，用户在桌面、平板终端上均可以使用界面开发功能。")
    ev = ("界面开发功能包括：开发工程生成、组件配置填写、公共组件管理、"
          "组件下载管理、组件打包发布、组件开发接口功能，"
          "此功能只在桌面版提供并使用，其功能用例如图4所示。")
    quote = "界面开发功能同样支持在平板设备上使用，便于在移动或便携场景下进行界面开发操作。"
    pos = answer.find(quote)
    row = _row("界面开发功能支持在哪些设备上使用？", answer, [ev],
               [_issue(quote, [pos, pos + len(quote)], "TERM-03")])
    fixed, outcome = repair_enum_member(row, row["issues"][0], answer)
    assert outcome.ok and outcome.operator == "enum_member"
    assert "平板" not in fixed
    assert "2. **平板设备**" not in fixed
    assert "用户在桌面终端上" in fixed
    assert "1. **桌面设备**" in fixed


def test_repair_enum_member_drop_with_negation():
    answer = ("布局控制功能仅在桌面、手持设备上使用，"
              "平板设备不在此功能的支持之列。综上，"
              "布局控制功能不支持在平板设备上使用。")
    pos = answer.find("布局控制功能仅在桌面、手持设备上使用")
    row = _row("布局控制功能支持在哪些设备上使用？", answer, [_TABLE],
               [_issue("布局控制功能仅在桌面、手持设备上使用，"
                       "平板设备不在此功能的支持之列。",
                       [pos, pos + 31], "TERM-03")])
    fixed, outcome = repair_enum_member(row, row["issues"][0], answer)
    assert outcome.ok
    assert fixed == ("布局控制功能仅在平板、桌面、手持设备上使用，"
                     "平板设备在此功能的支持之列。综上，"
                     "布局控制功能支持在平板设备上使用。")


def test_repair_enum_stage_swap():
    ev = ("<table><tr><td>序号</td><td>Use case名称</td><td>运行状态</td></tr>"
          "<tr><td>1</td><td>元数据管理</td><td>开发阶段</td></tr></table>")
    answer = "元数据管理功能在运行阶段提供，该功能的运行状态绑定为运行阶段。"
    pos = answer.find("元数据管理功能在运行阶段提供")
    row = _row("元数据管理功能在哪些运行阶段提供？", answer, [ev],
               [_issue("元数据管理功能在运行阶段提供，该功能的运行状态绑定为运行阶段",
                       [pos, pos + 34], "TERM-03")])
    fixed, outcome = repair_enum_member(row, row["issues"][0], answer)
    assert outcome.ok
    assert "运行阶段" not in fixed
    assert fixed == "元数据管理功能在开发阶段提供，该功能的运行状态绑定为开发阶段。"


def test_repair_enum_unremovable_excess_fails():
    answer = "该功能支持平板设备使用。"
    pos = answer.find("该功能支持平板设备使用")
    row = _row("界面开发功能支持在哪些设备上使用？", answer,
               ["界面开发功能只在桌面版提供并使用"],
               [_issue("该功能支持平板设备使用", [pos, pos + 11], "TERM-03")])
    _fixed, outcome = repair_enum_member(row, row["issues"][0], answer)
    # 平板 token被替换为证据集合 → ok(成员替换路径覆盖无条目场景)
    assert outcome.ok
    assert "平板" not in _fixed


# ── 标识符修复(TERM-07/08) ───────────────────────────────────

_ID_EV = ("<table><thead><tr><th>序号</th><th>Use case名称</th>"
          "<th>项目唯一标识符</th><th>方式名称</th></tr></thead><tbody>"
          "<tr><td></td><td>数据库初始化</td><td>PZXQ-GN-SJKCZ-SJKCSH</td>"
          "<td>平板、桌面、手持</td></tr></tbody></table>")


def test_repair_id_binding():
    answer = "数据库初始化用例的项目唯一标识符为PZXQ-GN-SQLFW-SJKCZ-SJKCSH。"
    pos = answer.find("PZXQ-GN-SQLFW-SJKCZ-SJKCSH")
    row = _row("数据库初始化用例的名称是什么？", answer, [_ID_EV],
               [_issue("PZXQ-GN-SQLFW-SJKCZ-SJKCSH",
                       [pos, pos + 26], "TERM-08")])
    fixed, outcome = repair_id_binding(row, row["issues"][0], answer)
    assert outcome.ok and outcome.operator == "id_binding"
    assert fixed == "数据库初始化用例的项目唯一标识符为PZXQ-GN-SJKCZ-SJKCSH。"


# ── 交互方修复(LOGIC-04) ─────────────────────────────────────

_PARTY_EV = ("<table><thead><tr><th>序号</th><th>接口需求名称</th>"
             "<th>接口需求标识</th><th>接口类型</th><th>发送方</th>"
             "<th>接收方</th><th>接口内容</th><th>接口优先级</th></tr></thead>"
             "<tbody><tr><td rowspan=\"2\">1</td>"
             "<td rowspan=\"2\">与用户的接口</td>"
             "<td rowspan=\"2\">PZXQ-WBJK-YH</td>"
             "<td rowspan=\"2\">人机接口</td><td>用户</td><td>本软件</td>"
             "<td rowspan=\"2\">菜单功能</td><td rowspan=\"2\">高</td></tr>"
             "<tr><td>本软件</td><td>用户</td></tr></tbody></table>")


def test_repair_party_binding_rowspan_group():
    answer = ("该接口通过接口PZXQ-WBJK-YH实现，"
              "是软件部署管理与本软件之间进行信息交互的正式通道。")
    quote = "是软件部署管理与本软件之间进行信息交互的正式通道"
    pos = answer.find(quote)
    row = _row("与用户的接口的接口流向是什么？", answer, [_PARTY_EV],
               [_issue(quote, [pos, pos + len(quote)], "LOGIC-04")])
    fixed, outcome = repair_party_binding(row, row["issues"][0], answer)
    assert outcome.ok and outcome.operator == "party_binding"
    assert "软件部署管理" not in fixed
    assert fixed == ("该接口通过接口PZXQ-WBJK-YH实现，"
                     "是用户与本软件之间进行信息交互的正式通道。")


def test_repair_party_direction_swap():
    ev = ("<table><tr><td>序号</td><td>接口需求名称</td><td>接口需求标识</td>"
          "<td>接口类型</td><td>发送方</td><td>接收方</td></tr>"
          "<tr><td>1</td><td>与应用软件的接口</td><td>PZXQ-WBJK-YYRJ</td>"
          "<td>API</td><td>本软件</td><td>应用软件</td></tr></table>")
    answer = "与应用软件的接口由应用软件发送至本软件，用于传输数据。"
    pos = answer.find("由应用软件发送至本软件")
    row = _row("与应用软件的接口的接口流向是什么？", answer, [ev],
               [_issue("由应用软件发送至本软件", [pos, pos + 12], "LOGIC-04")])
    fixed, outcome = repair_party_binding(row, row["issues"][0], answer)
    assert outcome.ok
    assert fixed == "与应用软件的接口由本软件发送至应用软件，用于传输数据。"


def test_repair_party_bidirectional_claim_no_change():
    answer = "接口信息由用户单向发送至本软件，确保信息传入。"
    row = _row("与用户的接口的接口流向是什么？", answer, [_PARTY_EV],
               [_issue("信息由用户单向发送至本软件", [2, 2 + 14], "LOGIC-04")])
    fixed, outcome = repair_party_binding(row, row["issues"][0], answer)
    # 双向接口: 双方均在证据双方集合内 → 流向声称一致(不可修单向性主张)
    # → 幂等成功但无修复记录; 行级no_change兜底(见下)
    assert outcome.ok
    assert outcome.records == []
    assert fixed == answer


def test_build_minimal_pair_bidirectional_row_skipped_via_no_change():
    answer = "接口信息由用户单向发送至本软件，确保信息传入。"
    row = _row("与用户的接口的接口流向是什么？", answer, [_PARTY_EV],
               [_issue("信息由用户单向发送至本软件", [2, 2 + 14], "LOGIC-04")])
    pair, reason = build_minimal_pair(row)
    assert pair is None and reason == "no_change"


# ── 行级装配 + 终检 ──────────────────────────────────────────

def test_build_minimal_pair_single_issue():
    answer = "组件名的最大值为1024字节，该数据项的取值不能超过1024字节。"
    pos = answer.find("组件名的最大值为1024字节")
    row = _row("组件名的最大值是多少？", answer, [_PARAM_EV],
               [_issue("组件名的最大值为1024字节", [pos, pos + 16], "PARAM-06")])
    pair, reason = build_minimal_pair(row)
    assert reason == "" and pair is not None
    assert pair["expected_flip"] == "refute→support"
    assert pair["repair_type"] == "numeric_value"
    assert pair["fixed_answer"] == \
        "组件名的最大值为1字节，该数据项的取值不能超过1字节。"
    assert pair["quality"] == {"min_faithful": 3, "min_truthful": 3,
                               "min_useful": 3}
    assert pair["repairs"][0]["rule_id"] == "PARAM-06"


def test_build_minimal_pair_requires_all_issues_repaired():
    answer = "组件名的最大值为1024字节。系统应运行稳定。"
    pos = answer.find("组件名的最大值为1024字节")
    issues = [
        _issue("组件名的最大值为1024字节", [pos, pos + 16], "PARAM-06"),
        _issue("系统应运行稳定", [pos + 17, pos + 23], "LOGIC-02"),
    ]
    row = _row("组件名的最大值是多少？", answer, [_PARAM_EV], issues)
    pair, reason = build_minimal_pair(row)
    assert pair is None
    assert reason.startswith("issue1:no_operator_for_rule:LOGIC-02")


def test_build_minimal_pair_faithful_gate():
    answer = "组件名的最大值为1024字节。"
    pos = answer.find("组件名的最大值为1024字节")
    issue = _issue("组件名的最大值为1024字节", [pos, pos + 16], "PARAM-06")
    issue["quality"]["faithful"] = 1
    row = _row("组件名的最大值是多少？", answer, [_PARAM_EV], [issue])
    pair, reason = build_minimal_pair(row)
    assert pair is None and reason == "faithful_lt2:issue0"


def test_final_sweeps_catches_fabricated_id():
    ev = ("<table><tr><td>标识符</td></tr><tr><td>PZXQ-GN-SJKCZ-SJKCSH</td>"
          "</tr></table>")
    row = _row("数据库初始化用例的名称是什么？", "x", [ev], [])
    bad = "标识符为PZXQ-GN-XXXX-YYYY。"
    reason = _final_sweeps(row, bad)
    assert reason.startswith("id_residual_out_of_evidence")


def test_final_sweeps_catches_residual_party():
    answer = "该接口是软件部署管理与本软件之间的正式通道。"
    row = _row("与用户的接口的接口流向是什么？", answer, [_PARTY_EV],
               [_issue("该接口是软件部署管理与本软件之间的正式通道",
                       [0, len(answer)], "LOGIC-04")])
    reason = _final_sweeps(row, answer)
    assert reason.startswith("party_residual_mismatch")


# ── 候选加载(faithful门 + 去重) ───────────────────────────────

def test_load_candidates_faithful_filter_and_dedup(tmp_path: Path):
    ok_row = {"instance_id": "A", "verdict": "refute", "corpus": "c",
              "question": "q", "answer": "a", "evidence": ["e"],
              "issues": [_issue("x", [0, 1], "GJB-05")]}
    low_row = {"instance_id": "B", "verdict": "refute", "corpus": "c",
               "question": "q", "answer": "a", "evidence": ["e"],
               "issues": [_issue("x", [0, 1], "GJB-05")]}
    low_row["issues"][0]["quality"]["faithful"] = 1
    no_issue = {"instance_id": "C", "verdict": "refute", "corpus": "c",
                "question": "q", "answer": "a", "evidence": ["e"],
                "issues": []}
    dup = dict(ok_row)
    dup["answer"] = "dup-answer"
    lp = tmp_path / "labels.jsonl"
    ep = tmp_path / "extra.jsonl"
    lp.write_text("".join(json_dumps(r) + "\n" for r in
                          (ok_row, low_row, no_issue)), encoding="utf-8")
    ep.write_text(json_dumps(dup) + "\n", encoding="utf-8")
    candidates, stats = load_candidates(lp, ep)
    assert [c["instance_id"] for c in candidates] == ["A"]
    assert stats["rows_faithful_lt2"] == 1
    assert candidates[0]["answer"] == "a"      # labels优先, extra同id不覆盖


def json_dumps(obj) -> str:  # noqa: ANN001 - 测试辅助
    import json
    return json.dumps(obj, ensure_ascii=False)
