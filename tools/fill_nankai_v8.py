"""v8: Nankai contract with path-style identifiers showing data cascades.

Fixes over v7:
  1. Table 1 row 8 registers the check-launch interface (POST /api/check),
     previously unregistered while its inputs sat in Table 9.
  2. All data-element identifiers use full paths (qa_pairs[].sample_id,
     samples[].violations[].item_id) so nesting is visible per row.
  3. Table 11 no longer duplicates Table 10's violation sub-fields; it
     references Table 10's structure and marks its own consumer.
  4. Table 12 splits fields into per-task and per-dataset query groups.
Only changed cells are yellow-highlighted; the source file is untouched.
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
OUT = SRC.with_name("内部接口及内部数据需求_南开填写修订_v8_级联路径标黄.docx")
HEADER = ["序号", "系统功能", "名称/标识符", "包含数据项",
          "数据类型", "来源", "接收者", "说明"]
A = "全生命周期管理模块"
B = "上游课题组/全生命周期管理模块"
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
    """Rebuild a data-element table; each tuple is one cascading field."""
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


def main() -> None:
    doc = Document(str(SRC))
    if len(doc.tables) != 14:
        raise ValueError("原文档结构不符，停止填写")

    # ── 表1: 登记四个接口行(保留原名称与收发关系, 只填空单元格) ──
    t1 = doc.tables[0]
    row8 = t1.rows[8].cells
    put(row8[0], "8")
    put(row8[2], "接收批量问答数据并发起异步一致性校验")
    put(row8[5], "API接口")
    put(row8[7], "POST /api/check；数据集级等价入口 POST /api/datasets/{dataset_id}/check")
    for ri, desc, note in (
        (9, "返回各样本最终结论及实际违反条目", "仅列实际违反项；样本结果结构见数据元素表10"),
        (10, "返回已完成任务的批次统计与样本级报告", "任务done后报告完整；样本结果结构同表10（消费者为研究内容四）"),
        (11, "查询校验任务状态及进度", "任务done后调用方再展示样本结论；支持按任务和按数据集两种查询"),
    ):
        cells = t1.rows[ri].cells
        put(cells[0], str(ri))
        put(cells[2], desc)
        put(cells[5], "API接口")
        put(cells[7], note)

    # ── 表9(index 8): POST /api/check 请求与受理响应, 路径式级联 ──
    rebuild(doc.tables[8], [
        ("请求", "cat", "校验场景，用于规则与算法路由", "字符串", A, NK, "必填；如srs"),
        ("请求", "dataset_id", "数据集标识", "字符串", A, NK, "可选；数据集级调用时提供"),
        ("请求", "qa_pairs", "待校验问答对条目数组", "对象数组", A, NK, "必填且不能为空；缺失/为空返回400"),
        ("问答对", "qa_pairs[].sample_id", "样本唯一标识（结果回查外键）", "字符串", A, NK, "每条必填"),
        ("问答对", "qa_pairs[].question", "原始问题文本", "字符串", A, NK, "报告原样回显"),
        ("问答对", "qa_pairs[].answer", "原始答案文本", "字符串", A, NK, "报告原样回显"),
        ("问答对", "qa_pairs[].source", "该样本的来源对象", "对象", A, NK, "必填；南开按此解析并召回证据"),
        ("来源对象", "qa_pairs[].source.doc_ref", "来源文档引用", "字符串", A, NK, "指明校验依据的文档"),
        ("来源对象", "qa_pairs[].source.evidence_refs", "样本关联的证据引用列表", "对象数组", A, NK, "可含证据标识及来源位置"),
        ("问答对", "qa_pairs[].knowledge_refs", "专家知识外键", "字符串数组", A, NK, "逐条解析；缺省时按cat用全部规则"),
        ("问答对", "qa_pairs[].metadata", "上游附加元数据", "对象", A, NK, "可选"),
        ("随检知识", "expert_knowledge", "本次请求可选携带的专家知识", "对象", B, NK, "携带时本次校验即用此份；未携带用已同步最新版"),
        ("随检知识", "expert_knowledge.scene", "知识适用场景", "字符串", B, NK, "必须与cat一致，否则400"),
        ("随检知识", "expert_knowledge.rules", "规则条目数组", "对象数组", B, NK, "按rule_id幂等覆盖；重复提交即更新"),
        ("规则条目", "expert_knowledge.rules[].rule_id", "规则唯一标识", "字符串", B, NK, "用于规则对齐与更新"),
        ("规则条目", "expert_knowledge.rules[].content", "规则内容", "字符串", B, NK, "规则正文"),
        ("受理响应", "check_id", "异步任务唯一标识", "字符串", NK, A, "受理成功返回"),
        ("受理响应", "status", "初始任务状态", "字符串", NK, A, "queued或running"),
        ("受理响应", "rules_snapshot.version", "绑定的规则版本", "字符串", NK, A, "后续规则更新不影响本任务"),
        ("受理响应", "rules_snapshot.n_rules", "绑定规则数量", "整数", NK, A, "本次快照规则数"),
    ])

    # ── 表10(index 9): 逐样本最终结论 + violations, 路径式级联 ──
    # 发往研究内容二(判定及问题说明接口的标准消费者)
    rebuild(doc.tables[9], [
        ("样本结果", "samples[].sample_id", "样本外键", "字符串", NK, RC2, "对应输入qa_pairs[].sample_id"),
        ("样本结果", "samples[].question", "原始问题回显", "字符串", NK, RC2, "输入原样返回"),
        ("样本结果", "samples[].answer", "原始答案回显", "字符串", NK, RC2, "输入原样返回"),
        ("样本结果", "samples[].consistency_result", "样本最终结论", "字符串", NK, RC2, "consistent/inconsistent/undetermined"),
        ("样本结果", "samples[].violations", "实际违反条目数组", "对象数组", NK, RC2, "只列实际违反项；一致样本为空数组"),
        ("违反条目", "samples[].violations[].item_id", "违反条目编号", "字符串", NK, RC2, "如TERM-01"),
        ("违反条目", "samples[].violations[].item_name", "违反条目名称", "字符串", NK, RC2, "供展示"),
        ("违反条目", "samples[].violations[].description", "违反原因说明", "字符串", NK, RC2, "简述为何违反"),
        ("违反条目", "samples[].violations[].affected_answer", "相关答案断言或值", "字符串", NK, RC2, "可选；便于定位问题"),
    ])

    # ── 表11(index 10): 批次报告; 不重复violations子字段, 引用表10结构 ──
    rebuild(doc.tables[10], [
        ("报告", "check_id", "任务标识", "字符串", NK, RC4, "对应发起受理响应"),
        ("报告", "run_at", "校验执行时间", "日期时间", NK, RC4, "建议ISO 8601"),
        ("规则快照", "rules_snapshot.version", "本次使用的规则版本", "字符串", NK, RC4, "用于结果复现"),
        ("规则快照", "rules_snapshot.n_rules", "规则数量", "整数", NK, RC4, "快照规模"),
        ("批次汇总", "summary.total", "样本总数", "整数", NK, RC4, "批次统计"),
        ("批次汇总", "summary.consistent", "一致样本数", "整数", NK, RC4, "done后统计"),
        ("批次汇总", "summary.inconsistent", "不一致样本数", "整数", NK, RC4, "done后统计"),
        ("批次汇总", "summary.undetermined", "无法判定样本数", "整数", NK, RC4, "证据不足或未定"),
        ("样本结果", "samples[]", "逐样本结果数组（同表10结构，消费者为研究内容四）", "对象数组", NK, RC4, "字段级联同表10: samples[].sample_id至violations[]，本表不重复罗列"),
    ])

    # ── 表12(index 11): 状态查询; 按任务/按数据集两个分组 ──
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
    if check.tables[8].cell(1, 2).text != "cat":
        raise AssertionError("表9输入未填写")
    if check.tables[0].cell(8, 2).text.strip() == "":
        raise AssertionError("表1第8行未登记发起接口")
    expected_rows = {8: 21, 9: 10, 10: 10, 11: 13}
    for ti, expected in expected_rows.items():
        table = check.tables[ti]
        if len(table.rows) != expected:
            raise AssertionError(f"表{ti+1}: 期望{expected}行, 实际{len(table.rows)}")
        if [c.text.strip() for c in table.rows[0].cells] != HEADER:
            raise AssertionError(f"表{ti+1}表头变化")
        for row in table.rows[1:]:
            if not all(c.text.strip() for c in row.cells):
                raise AssertionError(f"表{ti+1}有空字段")
            if not all(any(r.font.highlight_color == WD_COLOR_INDEX.YELLOW
                           for p in c.paragraphs for r in p.runs)
                       for c in row.cells):
                raise AssertionError(f"表{ti+1}有未标黄行")
    # 级联路径抽查: 子字段必须带[]路径
    cascade_checks = [
        check.tables[8].cell(4, 2).text,   # qa_pairs[].sample_id
        check.tables[9].cell(6, 2).text,   # samples[].violations[].item_id
        check.tables[11].cell(6, 2).text,  # dataset_id (按数据集查询)
    ]
    if not cascade_checks[0].startswith("qa_pairs[]."):
        raise AssertionError("表9级联路径缺失")
    if not cascade_checks[1].startswith("samples[].violations[]."):
        raise AssertionError("表10级联路径缺失")
    if cascade_checks[2] != "dataset_id":
        raise AssertionError("表12按数据集分组缺失")
    print(OUT)
    print("v8: 表1第8行已登记发起接口；全部路径式级联；表11引用表10；表12双查询分组。")


if __name__ == "__main__":
    main()
