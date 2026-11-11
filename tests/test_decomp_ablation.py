"""decomp ablation工具的确定性内核测试 (tools/eval_decomp_ablation.py).

覆盖 variant B (句子切分-only分解) 的行为契约:
  - 按句末标点(。！？；)切分, 每句一条semantic claim
  - 换行是切分符(独立行各自成句)
  - 编号列表项+其续行合并为一条claim(保留列表语义)
  - 小数守卫: "1.5GHz"开头的行不是列表项
  - 无句末标点的answer回退为单条claim
  - claim全部kind=semantic, 其余字段为dataclass默认值
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from tools.eval_decomp_ablation import sentence_only_decompose  # noqa: E402


def test_sentences_split_on_all_enders() -> None:
    answer = "系统支持热插拔。连接方式为TCP！超时时间为3s？无法连接时返回错误；"
    claims = sentence_only_decompose("q", answer)
    assert [c.text for c in claims] == [
        "系统支持热插拔。", "连接方式为TCP！", "超时时间为3s？", "无法连接时返回错误；"]
    assert all(c.kind == "semantic" for c in claims)
    assert all(c.attr == "" and c.operator == "" and c.value == ""
               and c.unit == "" and c.negative is False for c in claims)


def test_newline_is_a_split_boundary() -> None:
    answer = "第一行没有句号\n第二行也没有句号"
    claims = sentence_only_decompose("q", answer)
    assert [c.text for c in claims] == ["第一行没有句号", "第二行也没有句号"]


def test_numbered_item_with_continuation_is_one_claim() -> None:
    answer = ("1. **连接检查**：\n"
              "   系统首先验证连接。如果失败返回错误。\n"
              "\n"
              "2. **资源释放**：确保释放资源。\n")
    claims = sentence_only_decompose("q", answer)
    assert len(claims) == 2
    assert claims[0].text == ("1. **连接检查**： 系统首先验证连接。"
                              "如果失败返回错误。")
    assert claims[1].text == "2. **资源释放**：确保释放资源。"


def test_adjacent_numbered_items_without_blank_line() -> None:
    answer = "1．第一步说明\n2．第二步说明"
    claims = sentence_only_decompose("q", answer)
    assert [c.text for c in claims] == ["1．第一步说明", "2．第二步说明"]


def test_decimal_number_line_is_not_a_list_item() -> None:
    answer = "1.5GHz的频率要求。其余无要求。"
    claims = sentence_only_decompose("q", answer)
    assert [c.text for c in claims] == ["1.5GHz的频率要求。", "其余无要求。"]


def test_no_ender_answer_falls_back_to_single_claim() -> None:
    claims = sentence_only_decompose("q", "短答案没有句末标号")
    assert [c.text for c in claims] == ["短答案没有句末标号"]


def test_question_argument_is_unused() -> None:
    a = sentence_only_decompose("任何问题", "同一句答案。")
    b = sentence_only_decompose("另一个问题", "同一句答案。")
    assert a == b
