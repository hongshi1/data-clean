"""Write the agreed Nankai interface contract into the original table layout."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Pt

SRC = Path(r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\内部接口及内部数据需求.docx")
OUT = SRC.with_name("内部接口及内部数据需求_南开填写修订_v7_接口契约标黄.docx")
HEADER = ["序号", "系统功能", "名称/标识符", "包含数据项", "数据类型", "来源", "接收者", "说明"]


def put(cell, text: str) -> None:
    cell.text = ""
    run = cell.paragraphs[0].add_run(text)
    run.font.name = "宋体"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(8)
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def put_row(table, row_index: int, values: tuple[str, ...]) -> None:
    cells = table.rows[row_index].cells
    if len(cells) != 8 or len(values) != 8:
        raise ValueError("目标表必须是8列")
    for cell, value in zip(cells, values):
        put(cell, value)


def rebuild_data_table(table, elements: list[tuple[str, str, str, str, str, str, str]]) -> None:
    if [c.text.strip() for c in table.rows[0].cells] != HEADER:
        raise ValueError("目标表头不匹配")
    template = deepcopy(table.rows[1]._tr)
    for row in list(table.rows[1:]):
        table._tbl.remove(row._tr)
    for _ in elements:
        table._tbl.append(deepcopy(template))
    for i, (function, name, meaning, dtype, source, receiver, note) in enumerate(elements, 1):
        row = table.rows[i]
        # These columns are row-level in the rewritten data-element tables.
        for col in (1, 2, 5, 6):
            tcpr = row.cells[col]._tc.get_or_add_tcPr()
            vm = tcpr.find(qn("w:vMerge"))
            if vm is not None:
                tcpr.remove(vm)
        put_row(table, i, (str(i), function, name, meaning, dtype,
                           source, receiver, note))


def main() -> None:
    original = Document(str(SRC))
    doc = Document(str(SRC))
    if len(doc.tables) != 14:
        raise ValueError("原文档结构不符，停止填写")

    # Table 1: fill the existing Nankai-owned rows only; don't rename interfaces
    # or change the sender/receiver defined by the source document.
    t1 = doc.tables[0]
    for ri, desc, note in (
        (9, "接收校验判定及实际违反项，供研究内容二处理", "按样本返回违反条目及简要描述"),
        (10, "提供已完成校验任务的批次报告", "done后报告完整；保留输入qa_pairs引用"),
        (11, "提供校验任务执行状态和进度", "任务done后调用方再展示样本结论"),
    ):
        cells = t1.rows[ri].cells
        # Only fill the existing blank description/remark cells.
        put(cells[2], desc)
        put(cells[7], note)

    # Document Table 9 / python-docx index 8: POST /api/check request contract.
    rebuild_data_table(doc.tables[8], [
        ("统一校验发起", "cat", "校验场景，用于规则与算法路由", "字符串", "全生命周期管理模块", "研究内容三", "必填；如srs"),
        ("统一校验发起", "dataset_id", "数据集标识", "字符串", "全生命周期管理模块", "研究内容三", "数据集级调用时提供"),
        ("统一校验发起", "qa_pairs", "待校验问答条目数组", "对象数组", "全生命周期管理模块", "研究内容三", "必填且不能为空"),
        ("问答对", "sample_id", "样本唯一标识及结果外键", "字符串", "全生命周期管理模块", "研究内容三", "每条qa_pair必填"),
        ("问答对", "question", "原始问题文本", "字符串", "全生命周期管理模块", "研究内容三", "报告中原样返回"),
        ("问答对", "answer", "原始答案文本", "字符串", "全生命周期管理模块", "研究内容三", "报告中原样返回"),
        ("问答对", "source", "该样本的来源对象", "对象", "全生命周期管理模块", "研究内容三", "必填；南开按source解析/召回证据"),
        ("来源对象", "doc_ref", "来源文档引用", "字符串", "全生命周期管理模块", "研究内容三", "指明校验所依据的来源"),
        ("来源对象", "evidence_refs", "样本关联的参考数据引用", "对象数组", "全生命周期管理模块", "研究内容三", "可带来源块或证据标识"),
        ("问答对引用", "knowledge_refs", "专家知识外键", "字符串数组", "全生命周期管理模块", "研究内容三", "缺省时按cat使用该场景全部规则"),
        ("问答对扩展", "metadata", "上游附加元数据", "对象", "全生命周期管理模块", "研究内容三", "可选"),
        ("可选知识携带", "expert_knowledge", "本次校验可携带的专家知识对象", "对象", "全生命周期管理模块/上游课题组", "研究内容三", "可选；沿用上游2.1契约"),
        ("可选知识携带", "scene", "知识适用场景", "字符串", "全生命周期管理模块/上游课题组", "研究内容三", "必须与cat一致；不一致返回400"),
        ("可选知识携带", "rules", "本次提交的规则条目", "对象数组", "全生命周期管理模块/上游课题组", "研究内容三", "按rule_id幂等覆盖；重复提交即更新"),
        ("规则条目", "rule_id", "规则唯一标识", "字符串", "全生命周期管理模块/上游课题组", "研究内容三", "用于规则对齐和更新"),
        ("规则条目", "content", "规则内容", "字符串", "全生命周期管理模块/上游课题组", "研究内容三", "规则正文"),
        ("受理响应", "check_id", "异步任务标识", "字符串", "研究内容三", "全生命周期管理模块", "受理成功返回"),
        ("受理响应", "status", "初始任务状态", "字符串", "研究内容三", "全生命周期管理模块", "queued或running"),
        ("受理响应", "rules_snapshot", "本次绑定的规则快照", "对象", "研究内容三", "全生命周期管理模块", "规则后续变化不影响本任务"),
    ])

    # Document Table 10 / index 9: report samples; only actual violations listed.
    rebuild_data_table(doc.tables[9], [
        ("样本结果", "sample_id", "问答样本外键", "字符串", "研究内容三", "研究内容二", "对应输入qa_pairs[].sample_id"),
        ("样本结果", "question", "原始问题文本", "字符串", "研究内容三", "研究内容二", "输入原文回显"),
        ("样本结果", "answer", "原始答案文本", "字符串", "研究内容三", "研究内容二", "输入原文回显"),
        ("样本结果", "consistency_result", "样本最终结论", "字符串", "研究内容三", "研究内容二", "consistent/inconsistent/undetermined"),
        ("样本结果", "violations", "实际违反条目数组", "对象数组", "研究内容三", "研究内容二", "不列通过项；一致样本为空数组"),
        ("违反条目", "item_id", "违反条目编号", "字符串", "研究内容三", "研究内容二", "如TERM-01"),
        ("违反条目", "item_name", "违反条目名称", "字符串", "研究内容三", "研究内容二", "展示条目名称"),
        ("违反条目", "description", "违反原因说明", "字符串", "研究内容三", "研究内容二", "说明具体违反内容"),
        ("违反条目", "affected_answer", "相关答案断言或值", "字符串", "研究内容三", "研究内容二", "可选；便于查看问题"),
    ])

    # Document Table 11 / index 10: batch report for Research Content IV.
    rebuild_data_table(doc.tables[10], [
        ("报告", "check_id", "任务标识", "字符串", "研究内容三", "研究内容四", "对应发起响应"),
        ("报告", "run_at", "执行时间", "日期时间", "研究内容三", "研究内容四", "建议ISO 8601"),
        ("规则快照", "version", "本次规则版本", "字符串", "研究内容三", "研究内容四", "用于复现"),
        ("规则快照", "n_rules", "本次规则数量", "整数", "研究内容三", "研究内容四", "规则快照规模"),
        ("汇总", "total", "样本总数", "整数", "研究内容三", "研究内容四", "批次统计"),
        ("汇总", "consistent", "一致样本数", "整数", "研究内容三", "研究内容四", "done后统计"),
        ("汇总", "inconsistent", "不一致样本数", "整数", "研究内容三", "研究内容四", "done后统计"),
        ("汇总", "undetermined", "无法判定样本数", "整数", "研究内容三", "研究内容四", "证据不足或未能判定"),
        ("样本结果", "sample_id", "样本外键", "字符串", "研究内容三", "研究内容四", "对应输入qa_pairs[].sample_id"),
        ("样本结果", "question", "原始问题文本", "字符串", "研究内容三", "研究内容四", "输入原文回显"),
        ("样本结果", "answer", "原始答案文本", "字符串", "研究内容三", "研究内容四", "输入原文回显"),
        ("样本结果", "consistency_result", "样本最终结论", "字符串", "研究内容三", "研究内容四", "consistent/inconsistent/undetermined"),
        ("样本结果", "violations", "实际违反条目数组", "对象数组", "研究内容三", "研究内容四", "只返回实际违反项"),
        ("违反条目", "item_id", "违反条目编号", "字符串", "研究内容三", "研究内容四", "如TERM-01"),
        ("违反条目", "item_name", "违反条目名称", "字符串", "研究内容三", "研究内容四", "供报告展示"),
        ("违反条目", "description", "违反原因说明", "字符串", "研究内容三", "研究内容四", "简明说明违反内容"),
        ("违反条目", "affected_answer", "相关答案内容", "字符串", "研究内容三", "研究内容四", "可选"),
    ])

    # Document Table 12 / index 11: task lifecycle only.
    rebuild_data_table(doc.tables[11], [
        ("任务", "check_id", "异步任务标识", "字符串", "研究内容三", "全生命周期管理模块", "用于轮询"),
        ("任务", "status", "任务执行状态", "字符串", "研究内容三", "全生命周期管理模块", "queued/running/done/error"),
        ("进度", "total", "样本总数", "整数", "研究内容三", "全生命周期管理模块", "运行中可选返回"),
        ("进度", "completed", "已处理数", "整数", "研究内容三", "全生命周期管理模块", "运行中可选返回"),
        ("完成汇总", "summary", "完成后的批次汇总", "对象", "研究内容三", "全生命周期管理模块", "done时可附；不是逐条检查状态"),
        ("任务错误", "error.code", "任务级错误代码", "字符串", "研究内容三", "全生命周期管理模块", "error时返回"),
        ("任务错误", "error.message", "任务级错误说明", "字符串", "研究内容三", "全生命周期管理模块", "error不记作样本不一致"),
    ])

    doc.save(str(OUT))
    check = Document(str(OUT))
    if len(check.tables) != 14:
        raise AssertionError("源表数量变化")
    if check.tables[8].cell(1, 2).text != "cat":
        raise AssertionError("表9输入字段未按接口契约填写")
    expected_rows = {8: 20, 9: 10, 10: 18, 11: 8}
    for ti, expected in expected_rows.items():
        table = check.tables[ti]
        if len(table.rows) != expected:
            raise AssertionError(f"表{ti + 1}: expected {expected}, got {len(table.rows)}")
        if [c.text.strip() for c in table.rows[0].cells] != HEADER:
            raise AssertionError("原数据元素表头变化")
        for row in table.rows[1:]:
            if not all(c.text.strip() for c in row.cells):
                raise AssertionError(f"表{ti + 1}有空字段")
            if not all(any(r.font.highlight_color == WD_COLOR_INDEX.YELLOW
                           for p in c.paragraphs for r in p.runs)
                       for c in row.cells):
                raise AssertionError(f"表{ti + 1}有未标黄行")
    print(OUT)
    print("Contract v7 validated; input table unchanged; every output field is one row.")


if __name__ == "__main__":
    main()
