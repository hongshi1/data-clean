"""Rewrite Nankai-owned interface tables from the agreed contract.

One data element per row. The original source is preserved; the output is a
new DOCX copy. Only changed/new cells are highlighted yellow.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Pt

SRC = Path(
    r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
    r"\msg\file\2026-11\内部接口及内部数据需求.docx")
OUT = SRC.with_name("内部接口及内部数据需求_南开填写修订_v7_按契约逐项标黄.docx")
HEADER = ["序号", "系统功能", "名称/标识符", "包含数据项",
          "数据类型", "来源", "接收者", "说明"]


def write_cell(cell, text: str) -> None:
    cell.text = ""
    run = cell.paragraphs[0].add_run(text)
    run.font.name = "宋体"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(8)
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def write_row(table, row_index: int, values: tuple[str, ...]) -> None:
    cells = table.rows[row_index].cells
    if len(cells) != 8 or len(values) != 8:
        raise ValueError("目标表必须是8列")
    for cell, value in zip(cells, values):
        write_cell(cell, value)


def append_styled_row(table, template_row_index: int = 1):
    cloned = deepcopy(table.rows[template_row_index]._tr)
    table._tbl.append(cloned)
    return table.rows[-1]


def rebuild_table(table, elements: list[tuple[str, str, str, str, str, str, str]],
                  *, expected_owner: tuple[str, str]) -> None:
    if [c.text.strip() for c in table.rows[0].cells] != HEADER:
        raise ValueError("目标表头不匹配，拒绝写入")
    if len(table.rows) != 4:
        raise ValueError(f"原表预期表头+3行，实际{len(table.rows)}行")
    template = deepcopy(table.rows[1]._tr)
    tbl = table._tbl
    for row in list(table.rows[1:]):
        tbl.remove(row._tr)
    for _ in elements:
        tbl.append(deepcopy(template))
    for index, (function, identifier, meaning, dtype, source, receiver, note) in enumerate(elements, 1):
        row = table.rows[index]
        # Unmerge the source template's vertical cells for per-field rows.
        for col in (1, 2, 5, 6):
            tc_pr = row.cells[col]._tc.get_or_add_tcPr()
            vm = tc_pr.find(qn("w:vMerge"))
            if vm is not None:
                tc_pr.remove(vm)
        write_row(table, index, (str(index), function, identifier, meaning,
                                dtype, source, receiver, note))
        if (source, receiver) != expected_owner:
            raise ValueError(f"表格责任关系发生变化: {source} -> {receiver}")


def main() -> None:
    doc = Document(str(SRC))
    if len(doc.tables) != 14:
        raise ValueError("原文档表格数不是14，停止修改")

    # Table 1: only the three original Nankai-owned interfaces; flow unchanged.
    registry = doc.tables[0]
    write_row(registry, 9, ("9", "判定及问题说明接口（南开）",
        "返回批次中各问答样本的一致性结论及实际违反条目",
        "研究内容三", "研究内容二", "内部接口", "高",
        "报告保留原question/answer；仅列出实际违反项"))
    write_row(registry, 10, ("10", "一致性校验报告接口（南开）",
        "返回批次统计及逐样本校验结果",
        "研究内容三", "研究内容四", "内部接口", "高",
        "任务done后返回完整报告"))
    write_row(registry, 11, ("11", "检验状态信息接口（南开）",
        "查询校验任务执行状态及进度",
        "研究内容三", "全生命周期管理模块", "内部接口", "高",
        "任务态与样本结论分离；仅done后展示校验结果"))

    # Table 9 / index 8 is the upstream input. Keep it entirely unchanged.

    # Table 10 / index 9: POST /api/check request and acceptance data.
    rebuild_table(doc.tables[9], [
        ("统一校验发起", "cat", "校验场景标识", "字符串", "全生命周期管理模块", "研究内容三", "场景须已接入，如srs"),
        ("统一校验发起", "dataset_id", "数据集标识", "字符串", "全生命周期管理模块", "研究内容三", "数据集级调用使用"),
        ("统一校验发起", "qa_pairs", "待校验问答对数组", "对象数组", "全生命周期管理模块", "研究内容三", "必填且不能为空"),
        ("问答对", "sample_id", "问答样本唯一标识", "字符串", "全生命周期管理模块", "研究内容三", "每条qa_pair必填；结果外键"),
        ("问答对", "question", "原始问题文本", "字符串", "全生命周期管理模块", "研究内容三", "报告中原样返回"),
        ("问答对", "answer", "原始答案文本", "字符串", "全生命周期管理模块", "研究内容三", "报告中原样返回"),
        ("问答对", "source", "该样本参考来源对象", "对象", "全生命周期管理模块", "研究内容三", "必填；包含来源引用"),
        ("样本引用", "source.doc_ref", "来源文档标识", "字符串", "全生命周期管理模块", "研究内容三", "用于追溯原始材料"),
        ("样本引用", "source.evidence_refs", "该样本引用的来源证据", "对象数组", "全生命周期管理模块", "研究内容三", "由南开按source解析和召回证据源"),
        ("样本引用", "knowledge_refs", "该样本使用的专家知识外键", "字符串数组", "全生命周期管理模块/上游课题组", "研究内容三", "缺省时按cat使用全部规则"),
        ("样本扩展信息", "metadata", "上游提供的附加样本元数据", "对象", "全生命周期管理模块", "研究内容三", "可选"),
        ("本次知识携带", "expert_knowledge", "本次请求可选携带的专家知识集合", "对象", "上游课题组", "研究内容三", "可选；其scene须与cat一致；按rule_id幂等覆盖并用于本次校验"),
        ("本次知识携带", "expert_knowledge.scene", "知识适用场景", "字符串", "上游课题组", "研究内容三", "必须与请求cat一致"),
        ("本次知识携带", "expert_knowledge.rules", "本次提交的规则条目", "对象数组", "上游课题组", "研究内容三", "rule_id对齐；重复提交为更新"),
        ("任务受理响应", "check_id", "异步校验任务标识", "字符串", "研究内容三", "全生命周期管理模块", "受理成功后返回"),
        ("任务受理响应", "status", "任务初始状态", "字符串", "研究内容三", "全生命周期管理模块", "queued或running"),
        ("任务受理响应", "rules_snapshot", "本次校验绑定的规则快照", "对象", "研究内容三", "全生命周期管理模块", "任务后续不受规则更新影响"),
    ], expected_owner=("全生命周期管理模块", "研究内容三"))

    # Table 11 / index 10: report. Only actual violating items are returned.
    rebuild_table(doc.tables[10], [
        ("校验报告", "check_id", "本次校验任务标识", "字符串", "研究内容三", "研究内容四", "与发起响应中的check_id一致"),
        ("校验报告", "run_at", "本次校验执行时间", "日期时间", "研究内容三", "研究内容四", "建议ISO 8601格式"),
        ("规则快照", "rules_snapshot.version", "本次实际使用的规则版本", "字符串", "研究内容三", "研究内容四", "供结果复现"),
        ("规则快照", "rules_snapshot.n_rules", "本次规则数量", "整数", "研究内容三", "研究内容四", "记录规则快照规模"),
        ("批次汇总", "summary.total", "问答样本总数", "整数", "研究内容三", "研究内容四", "批次统计"),
        ("批次汇总", "summary.pass", "一致样本数", "整数", "研究内容三", "研究内容四", "仅统计done后的样本结论"),
        ("批次汇总", "summary.fail", "不一致样本数", "整数", "研究内容三", "研究内容四", "仅统计实际违反样本"),
        ("批次汇总", "summary.undetermined", "无法判定样本数", "整数", "研究内容三", "研究内容四", "证据不足时计入"),
        ("样本结果", "samples.sample_id", "问答样本标识", "字符串", "研究内容三", "研究内容四", "对应输入qa_pairs.sample_id"),
        ("样本结果", "samples.question", "原始问题文本", "字符串", "研究内容三", "研究内容四", "原样返回"),
        ("样本结果", "samples.answer", "原始答案文本", "字符串", "研究内容三", "研究内容四", "原样返回"),
        ("样本结果", "samples.consistency_result", "样本最终一致性结论", "字符串", "研究内容三", "研究内容四", "consistent/inconsistent/undetermined"),
        ("样本结果", "samples.violations", "实际违反的校验条目列表", "对象数组", "研究内容三", "研究内容四", "不返回通过或未违反的校验条目；一致样本为空数组"),
        ("违反条目", "violations.item_id", "违反条目编号", "字符串", "研究内容三", "研究内容四", "如TERM-01"),
        ("违反条目", "violations.item_name", "违反条目名称", "字符串", "研究内容三", "研究内容四", "供界面展示"),
        ("违反条目", "violations.description", "违反原因简述", "字符串", "研究内容三", "研究内容四", "描述具体不一致，不包含证据定位对象"),
        ("违反条目", "violations.affected_answer", "相关答案断言或值", "字符串", "研究内容三", "研究内容四", "可选；辅助识别问题"),
    ], expected_owner=("研究内容三", "研究内容四"))

    # Table 12 / index 11: task-level state, orthogonal to sample result.
    rebuild_table(doc.tables[11], [
        ("任务状态", "check_id", "异步校验任务标识", "字符串", "研究内容三", "全生命周期管理模块", "用于轮询任务"),
        ("任务状态", "status", "任务执行状态", "字符串", "研究内容三", "全生命周期管理模块", "queued/running/done/error"),
        ("任务进度", "progress.total", "任务样本总数", "整数", "研究内容三", "全生命周期管理模块", "queued/running时可选返回"),
        ("任务进度", "progress.completed", "已处理样本数", "整数", "研究内容三", "全生命周期管理模块", "queued/running时可选返回"),
        ("任务状态", "summary", "任务完成后的批次汇总", "对象", "研究内容三", "全生命周期管理模块", "done时可返回；不是逐条check item状态"),
        ("任务异常", "error.code", "任务级错误代码", "字符串", "研究内容三", "全生命周期管理模块", "error时返回"),
        ("任务异常", "error.message", "任务级错误原因", "字符串", "研究内容三", "全生命周期管理模块", "error不是样本不一致"),
    ], expected_owner=("研究内容三", "全生命周期管理模块"))

    doc.save(str(OUT))
    check = Document(str(OUT))
    if len(check.tables) != 14:
        raise AssertionError("原表总数变化")
    if check.tables[8].cell(1, 2).text != "待检验数据集/XXX":
        raise AssertionError("表9上游输入被修改")
    expected_counts = {9: 17, 10: 17, 11: 7}
    for table_index, expected_count in expected_counts.items():
        table = check.tables[table_index]
        if len(table.rows) != expected_count:
            raise AssertionError(
                f"表{table_index + 1}期望{expected_count}行，实际{len(table.rows)}")
        for row in table.rows[1:]:
            if not all(cell.text.strip() for cell in row.cells):
                raise AssertionError(f"表{table_index + 1}存在空单元格")
            if not all(any(run.font.highlight_color == WD_COLOR_INDEX.YELLOW
                           for p in cell.paragraphs for run in p.runs)
                       for cell in row.cells):
                raise AssertionError(f"表{table_index + 1}存在未标黄行")
    print(OUT)
    print("qa_pairs输入关系、done后报告、仅violations输出、任务/样本状态分离已写入原表结构。")
    print("表9输入保持原样；每个数据元素独立成行并标黄。")


if __name__ == "__main__":
    main()
