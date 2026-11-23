"""v12: revert remarks to normal one-line descriptions.

User feedback: the multi-paragraph JSON examples stretched the table rows
too tall. Keep remarks as short single-line descriptions (like the source
document's own style); the concrete JSON examples live in the chat summary
instead of the DOCX. Everything else from v11 stays: scene naming, flat
source, no evidence_refs/metadata, expert-knowledge placeholder, tables
10/11 identical field lists.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Pt

SRC = Path(r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
           r"\msg\file\2026-11\内部接口及内部数据需求.docx")
OUT = SRC.with_name("内部接口及内部数据需求_南开填写修订_v12_简备注标黄.docx")
HEADER = ["序号", "系统功能", "名称/标识符", "包含数据项",
          "数据类型", "来源", "接收者", "说明"]
A = "全生命周期管理模块"
NK = "研究内容三"
RC2 = "研究内容二"
RC4 = "研究内容四"


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


def rebuild(table, elements: list[tuple[str, str, str, str, str, str, str]]) -> None:
    if [c.text.strip() for c in table.rows[0].cells] != HEADER:
        raise ValueError("目标表头不匹配")
    template = deepcopy(table.rows[1]._tr)
    for row in list(table.rows[1:]):
        table._tbl.remove(row._tr)
    for _ in elements:
        table._tbl.append(deepcopy(template))
    for i, (function, path, meaning, dtype, source, receiver, note) in enumerate(elements, 1):
        row = table.rows[i]
        for col in (1, 2, 5, 6):
            tcpr = row.cells[col]._tc.get_or_add_tcPr()
            vm = tcpr.find(qn("w:vMerge"))
            if vm is not None:
                tcpr.remove(vm)
        put_row(table, i, (str(i), function, path, meaning,
                           dtype, source, receiver, note))


FIELDS = [
    ("批次汇总", "summary.total", "样本总数", "整数", NK, "{RECV}", "批次统计"),
    ("批次汇总", "summary.consistent", "一致样本数", "整数", NK, "{RECV}", "done后统计"),
    ("批次汇总", "summary.inconsistent", "不一致样本数", "整数", NK, "{RECV}", "done后统计"),
    ("批次汇总", "summary.undetermined", "无法判定样本数", "整数", NK, "{RECV}", "证据不足或未定"),
    ("报告信息", "check_id", "任务标识", "字符串", NK, "{RECV}", "对应发起受理响应"),
    ("报告信息", "run_at", "校验执行时间", "日期时间", NK, "{RECV}", "建议ISO 8601"),
    ("规则快照", "rules_snapshot.version", "本次使用的规则版本", "字符串", NK, "{RECV}", "用于结果复现"),
    ("规则快照", "rules_snapshot.n_rules", "规则数量", "整数", NK, "{RECV}", "快照规模"),
    ("样本结果", "samples[].sample_id", "样本外键", "字符串", NK, "{RECV}", "对应输入qa_pairs[].sample_id"),
    ("样本结果", "samples[].question", "原始问题回显", "字符串", NK, "{RECV}", "输入原样返回"),
    ("样本结果", "samples[].answer", "原始答案回显", "字符串", NK, "{RECV}", "输入原样返回"),
    ("样本结果", "samples[].consistency_result", "样本最终结论", "字符串", NK, "{RECV}", "consistent/inconsistent/undetermined"),
    ("样本结果", "samples[].violations", "实际违反条目数组", "对象数组", NK, "{RECV}", "只列实际违反项；一致样本为空数组"),
    ("违反条目", "samples[].violations[].item_id", "违反条目编号", "字符串", NK, "{RECV}", "如TERM-01"),
    ("违反条目", "samples[].violations[].item_name", "违反条目名称", "字符串", NK, "{RECV}", "供展示"),
    ("违反条目", "samples[].violations[].description", "违反原因说明", "字符串", NK, "{RECV}", "简述为何违反"),
    ("违反条目", "samples[].violations[].affected_answer", "相关答案断言或值", "字符串", NK, "{RECV}", "可选；便于定位问题"),
]


def instantiate(elements, receiver: str):
    return [(f, p, m, d, s, receiver, n)
            for (f, p, m, d, s, _, n) in elements]


def main() -> None:
    doc = Document(str(SRC))
    if len(doc.tables) != 14:
        raise ValueError("原文档结构不符，停止填写")

    # ── 表1: 备注恢复为正常一行描述 ──
    t1 = doc.tables[0]
    row8 = t1.rows[8].cells
    put(row8[0], "8")
    put(row8[2], "接收批量问答数据并发起异步一致性校验")
    put(row8[5], "API接口")
    put(row8[7], "POST /api/check；数据集级等价入口POST /api/datasets/{dataset_id}/check；异步受理")
    for ri, desc, note in (
        (9, "返回各样本最终结论及实际违反条目",
            "仅列实际违反项；样本结果结构见数据元素表10"),
        (10, "返回批次统计与逐样本校验结果",
            "任务done后返回完整报告；样本结果结构同表10"),
        (11, "查询校验任务状态及进度",
            "任务done后调用方再展示结论；支持按任务/按数据集两种查询"),
    ):
        cells = t1.rows[ri].cells
        put(cells[0], str(ri))
        put(cells[2], desc)
        put(cells[5], "API接口")
        put(cells[7], note)

    rebuild(doc.tables[8], [
        ("请求", "scene", "校验场景标识（英文）", "字符串", A, NK, "必填；取值scene1/scene2（场景一/场景二），用于规则与算法路由"),
        ("请求", "dataset_id", "数据集标识", "字符串", A, NK, "可选；数据集级调用时提供"),
        ("请求", "qa_pairs", "待校验问答对条目数组", "对象数组", A, NK, "必填且不能为空；缺失/为空返回400"),
        ("问答对", "qa_pairs[].sample_id", "样本唯一标识（结果回查外键）", "字符串", A, NK, "每条必填"),
        ("问答对", "qa_pairs[].question", "原始问题文本", "字符串", A, NK, "报告原样回显"),
        ("问答对", "qa_pairs[].answer", "原始答案文本", "字符串", A, NK, "报告原样回显"),
        ("问答对", "qa_pairs[].source", "来源文档引用", "字符串", A, NK, "必填；该问答引用的来源文档，南开按此解析并召回证据"),
        ("问答对", "qa_pairs[].knowledge_refs", "引用的专家知识外键", "字符串数组", A, NK, "在qa_pair内携带本样本引用的专家知识；逐条解析，缺省时按scene用该场景全部规则"),
        ("专家知识（占位）", "expert_knowledge（待定义）", "随检专家知识载荷（占位符）", "对象", A, NK, "知识内容由上游提供，具体结构暂不显式定义；当前通过qa_pairs[].knowledge_refs引用"),
        ("受理响应", "check_id", "异步任务唯一标识", "字符串", NK, A, "受理成功返回"),
        ("受理响应", "status", "初始任务状态", "字符串", NK, A, "queued或running"),
        ("受理响应", "rules_snapshot.version", "绑定的规则版本", "字符串", NK, A, "后续规则更新不影响本任务"),
        ("受理响应", "rules_snapshot.n_rules", "绑定规则数量", "整数", NK, A, "本次快照规则数"),
    ])

    rebuild(doc.tables[9], instantiate(FIELDS, RC2))
    rebuild(doc.tables[10], instantiate(FIELDS, RC4))

    rebuild(doc.tables[11], [
        ("按任务查询", "check_id", "任务唯一标识（GET /api/check-status/{check_id}）", "字符串", NK, A, "路径参数"),
        ("按任务查询", "status", "任务执行状态", "字符串", NK, A, "queued/running/done/error"),
        ("按任务查询", "progress.total", "任务样本总数", "整数", NK, A, "running期间可选返回"),
        ("按任务查询", "progress.completed", "已处理样本数", "整数", NK, A, "running期间可选返回"),
        ("按任务查询", "summary", "完成后的批次汇总", "对象", NK, A, "done时返回；error时附原因不附汇总"),
        ("按数据集查询", "dataset_id", "数据集标识（GET /api/datasets/{dataset_id}/check-status）", "字符串", NK, A, "路径参数"),
        ("按数据集查询", "check_id", "该数据集最近一次任务标识", "字符串", NK, A, "取最近一次check"),
        ("按数据集查询", "status", "最近一次任务的状态", "字符串", NK, A, "同按任务查询status语义"),
        ("按数据集查询", "summary", "最近一次任务的批次汇总", "对象", NK, A, "done时可附"),
        ("按数据集查询", "samples", "最近一次任务的样本结论聚合", "对象数组", NK, A, "done时可附；结构同表10"),
        ("任务异常", "error.code", "任务级错误代码", "字符串", NK, A, "error时返回"),
        ("任务异常", "error.message", "任务级错误原因", "字符串", NK, A, "异常≠样本不一致"),
    ])

    doc.save(str(OUT))
    check = Document(str(OUT))
    if len(check.tables) != 14:
        raise AssertionError("源表总数变化")
    # 备注必须单段落(不撑表)
    for ri in (8, 9, 10, 11):
        if len(check.tables[0].cell(ri, 7).paragraphs) != 1:
            raise AssertionError(f"表1行{ri}备注多段落")
        if len(check.tables[0].cell(ri, 7).text) > 70:
            raise AssertionError(f"表1行{ri}备注过长")
    t10 = [check.tables[9].rows[r].cells[2].text for r in range(1, len(check.tables[9].rows))]
    t11 = [check.tables[10].rows[r].cells[2].text for r in range(1, len(check.tables[10].rows))]
    if t10 != t11:
        raise AssertionError("表10与表11字段不一致")
    # 原表未动行校验
    original = Document(str(SRC))
    for ri in list(range(1, 8)) + [12, 13]:
        if original.tables[0].cell(ri, 7).text != check.tables[0].cell(ri, 7).text:
            raise AssertionError(f"表1行{ri}原备注被改动")
    expected_rows = {8: 14, 9: 18, 10: 18, 11: 13}
    for ti, expected in expected_rows.items():
        if len(check.tables[ti].rows) != expected:
            raise AssertionError(f"表{ti+1}行数不符")
    print(OUT)
    print("v12: 备注恢复单行简述；表格行高与原文档一致；表10/11字段一致。")


if __name__ == "__main__":
    main()
