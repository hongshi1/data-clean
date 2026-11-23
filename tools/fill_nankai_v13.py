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
OUT = SRC.with_name("内部接口及内部数据需求_南开_v3.docx")
HEADER = ["序号", "系统功能", "名称/标识符", "包含数据项",
          "数据类型", "来源", "接收者", "说明"]
A = "全生命周期管理模块"
NK = "研究内容三"
RC2 = "研究内容二"
RC4 = "研究内容四"


def put(cell, text: str) -> None:
    # 彻底清空单元格所有段落的所有run(含残留空run)
    for para in list(cell.paragraphs):
        for child in list(para._p):
            if child.tag != qn("w:pPr"):
                para._p.remove(child)
    # 只保留一个段落, 其余删除
    for para in list(cell.paragraphs[1:]):
        para._p.getparent().remove(para._p)
    run = cell.paragraphs[0].add_run(text)
    run.font.name = "宋体"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(10.5)  # 五号字


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

    # ── 表1: 只填南开三个输出接口行(9/10/11); 行8(待检验数据集接口)保持原文 ──
    t1 = doc.tables[0]
    for ri, desc, note in (
        (9, "返回批次统计与逐样本校验结果",
            "任务完成后（任务状态：done）返回完整报告"),
        (10, "返回批次统计与逐样本校验结果",
            "任务完成后（任务状态：done）返回完整报告"),
        (11, "查询校验任务状态及进度",
            "任务done后调用方再展示结论；支持按任务/按数据集两种查询"),
    ):
        cells = t1.rows[ri].cells
        put(cells[0], str(ri))
        put(cells[2], desc)
        put(cells[5], "API接口")
        put(cells[7], note)

    # ── 表9(index 8)输入表: 恢复原文, 不填 ──
    # (用户指示: 表9相关内容恢复, 不用填)

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
    for ri in (9, 10, 11):
        if len(check.tables[0].cell(ri, 7).paragraphs) != 1:
            raise AssertionError(f"表1行{ri}备注多段落")
        if len(check.tables[0].cell(ri, 7).text) > 70:
            raise AssertionError(f"表1行{ri}备注过长")
    # 行9与行10表述必须完全一致
    if check.tables[0].cell(9, 2).text != check.tables[0].cell(10, 2).text:
        raise AssertionError("表1行9与行10描述不一致")
    if check.tables[0].cell(9, 7).text != check.tables[0].cell(10, 7).text:
        raise AssertionError("表1行9与行10备注不一致")
    # 不得残留黄色高亮
    for ti in (0, 9, 10, 11):
        table = check.tables[ti]
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.font.highlight_color is not None:
                            raise AssertionError("残留黄色高亮")
    t10 = [check.tables[9].rows[r].cells[2].text for r in range(1, len(check.tables[9].rows))]
    t11 = [check.tables[10].rows[r].cells[2].text for r in range(1, len(check.tables[10].rows))]
    if t10 != t11:
        raise AssertionError("表10与表11字段不一致")
    # 原表未动行校验: 行8与表9输入表必须与原文档逐格一致
    original = Document(str(SRC))
    for ri in list(range(1, 9)) + [12, 13]:
        for ci in range(8):
            if original.tables[0].cell(ri, ci).text != check.tables[0].cell(ri, ci).text:
                raise AssertionError(f"表1行{ri}列{ci}原内容被改动")
    # 表9(index 8)整表逐格保持原文
    for ri in range(len(check.tables[8].rows)):
        for ci in range(8):
            if original.tables[8].cell(ri, ci).text != check.tables[8].cell(ri, ci).text:
                raise AssertionError(f"表9行{ri}列{ci}被改动")
    expected_rows = {9: 18, 10: 18, 11: 13}
    for ti, expected in expected_rows.items():
        if len(check.tables[ti].rows) != expected:
            raise AssertionError(f"表{ti+1}行数不符")
    if len(check.tables[8].rows) != len(original.tables[8].rows):
        raise AssertionError("表9行数变化")
    print(OUT)
    print("v13: 表9及表1行8恢复原文不填；行9=行10表述一致；无黄色高亮。")


if __name__ == "__main__":
    main()
