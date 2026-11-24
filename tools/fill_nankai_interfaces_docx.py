"""Fill a copy of the supplied Nankai interface requirements docx.

The source document is outside the repository and is never overwritten.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn

SOURCE = Path(
    r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
    r"\msg\file\2026-11\内部接口及内部数据需求.docx")
OUTPUT = SOURCE.with_name("内部接口及内部数据需求_南开接口方案已填写.docx")


def set_cell(cell, value: str) -> None:
    cell.text = value
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.name = "宋体"
            run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
            run.font.size = Pt(8)


def add_before(anchor, text: str, style: str = "Normal"):
    if style not in {s.name for s in anchor.part.document.styles}:
        style = "Normal"
    paragraph = anchor.insert_paragraph_before(text, style=style)
    for run in paragraph.runs:
        run.font.name = "宋体"
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
        run.font.size = Pt(10.5 if style == "Normal" else 12)
        if text.startswith(("三、", "3.")):
            run.bold = True
    return paragraph


def insert_interface_contract(doc: Document) -> None:
    anchor = next(p for p in doc.paragraphs
                  if p.text.strip() == "表 1 内部接口标识")
    sections = [
        ("Heading 1", "三、南开一致性校验接口需求（新增）"),
        ("Heading 2", "3.1 任务定义"),
        ("Normal", "本任务接收数据集管理模块提交的问答对及其来源证据、专家知识引用和场景信息，按照指定规则版本执行一致性校验。校验结果应包含样本级结论，并对每条不一致给出答案侧断言、证据侧位置、问题类型和判定理由。"),
        ("Normal", "输入：校验场景、qa_pairs数组、每条问答的sample_id/question/answer，以及可选的source、evidence_refs、knowledge_ref和metadata。输出：异步任务check_id、规则快照、任务状态、样本状态及issues定位报告。"),
        ("Normal", "处理流程：调用方POST /api/check发起任务；服务记录规则版本快照并执行校验；调用方通过GET /api/check-status/{check_id}轮询；任务完成后通过GET /api/check-reports/{check_id}获取报告。"),
        ("Heading 2", "3.2 专家知识查询接口（核心接口）"),
        ("Normal", "接口标识：POST /api/knowledge；接口类型：REST/JSON，同步。发送方：一致性校验服务；接收方：专家知识模块。用途：按cat场景和query内容查询相关专家知识。具体知识结构可由上游课题组扩展，但必须保留knowledge_id及source_ref以供报告追溯。"),
        ("Normal", '{"cat":"srs","query":[{"query_id":"q_0001","text":"待查询内容","source_ref":{"doc_id":"doc_01","section":"3.3"}}],"top_k":10}'),
        ("Normal", '响应：{"ok":true,"data":{"items":[{"knowledge_id":"K-001","text":"知识内容","source_ref":{"rule_id":"GJB-RULE-085"},"score":0.93}]}}'),
        ("Heading 2", "3.3 统一校验发起接口（核心接口）"),
        ("Normal", "接口标识：POST /api/check；接口类型：REST/JSON，异步。发送方：数据集管理、质量评估或相关模块；接收方：一致性校验服务。专家知识及参考来源应内嵌在qa_pairs条目中，确保报告生成后仍可追溯原始上下文。"),
        ("Normal", '{"cat":"srs","dataset_id":"dataset_2026_001","qa_pairs":[{"sample_id":"qa_0001_01","question":"问题文本","answer":"答案文本","source":{"source_ref":"需求规格说明.docx","section":"3.2.1","evidence_refs":[{"evidence_id":"ev_01","block_id":"block-000040","text":"参考证据原文"}]},"knowledge":{"knowledge_ref":["GJB-RULE-085"],"items":[]},"metadata":{}}],"options":{"rules_version":"latest"}}'),
        ("Normal", '受理响应：{"ok":true,"data":{"check_id":"chk-20260830-001","status":"queued","rules_snapshot":{"version":"rules-2026-08-28","n_rules":52}}}'),
        ("Heading 2", "3.4 校验报告获取接口（核心接口）"),
        ("Normal", "接口标识：GET /api/check-reports/{check_id}；接口类型：REST/JSON，同步查询。任务done时返回完整报告；queued/running时只返回任务状态，不附完整报告；error时返回错误原因。check_id不存在时返回404。样本状态pass表示通过，warn表示需关注或证据不足，fail表示检出不一致且必须包含issues定位信息。"),
        ("Normal", '{"ok":true,"data":{"check_id":"chk-20260830-001","status":"done","run_at":"2026-08-30T17:36:37Z","rules_snapshot":{"version":"rules-2026-08-28","n_rules":52},"summary":{"total":12,"pass":8,"warn":2,"fail":2},"samples":[{"sample_id":"qa_0001_01","source":{"source_ref":"需求规格说明.docx","knowledge_ref":["GJB-RULE-085"]},"status":"fail","issues":[{"issue_id":"qa_0001_01_issue_01","type":"语义不一致","detail_type":"TERM-07","desc":"答案中的接口标识符与证据中的标识符不一致。","answer_location":{"claim_text":"答案中的断言","start":16,"end":35},"evidence_locations":[{"evidence_id":"ev_01","block_id":"block-000040","section":"3.2.1","row_index":5,"field_name":"标识符","text":"证据原文"}],"rationale":"判定理由","method":"id_join_registry","confidence":0.98}]}]}}'),
        ("Heading 2", "3.5 校验状态查询接口"),
        ("Normal", "按任务查询：GET /api/check-status/{check_id}，返回check_id、status、progress和可选summary。按数据集查询：GET /api/datasets/{dataset_id}/check-status，返回该数据集最近一次check的status、summary及可选samples。任务状态流转：queued→running→done/error。执行异常不得记作样本fail；异常样本不落校验结果。"),
        ("Normal", '状态响应：{"ok":true,"data":{"check_id":"chk-20260830-001","status":"running","progress":{"total":12,"completed":7},"summary":null}}。错误响应：{"ok":false,"error":{"code":"CHECK_NOT_FOUND","message":"指定的check_id不存在"}}。'),
        ("Heading 2", "3.6 接口数据元素说明"),
        ("Normal", "以下数据元素表补充原模板中的占位内容。数据类型按JSON接口类型填写；长度限制、枚举值和时间格式应由接口实现与联调协议共同锁定。"),
    ]
    for style, text in reversed(sections):
        add_before(anchor, text, style)


def fill_table(table, rows: list[tuple[str, ...]]) -> None:
    while len(table.rows) < len(rows) + 1:
        table.add_row()
    while len(table.rows) > len(rows) + 1:
        tr = table.rows[-1]._tr
        tr.getparent().remove(tr)
    for row_index, values in enumerate(rows, start=1):
        for col_index, value in enumerate(values):
            set_cell(table.cell(row_index, col_index), value)


def fill_existing_tables(doc: Document) -> None:
    registry = doc.tables[0]
    registry_rows = {
        9: ("9", "判定及问题说明接口（南开）", "提交待校验问答并接收异步任务标识", "研究内容三", "研究内容二/四", "REST API/JSON（异步）", "高", "POST /api/check；任务由check_id关联"),
        10: ("10", "一致性校验报告接口（南开）", "按check_id获取样本级结论、问题及定位信息", "研究内容三", "研究内容四", "REST API/JSON（查询）", "高", "GET /api/check-reports/{check_id}"),
        11: ("11", "检验状态信息接口（南开）", "查询任务或数据集最近一次校验状态", "研究内容三", "全生命周期管理模块", "REST API/JSON（查询）", "高", "GET /api/check-status/{check_id}；按数据集查询最近一次任务"),
    }
    for row_index, values in registry_rows.items():
        for col_index, value in enumerate(values):
            set_cell(registry.cell(row_index, col_index), value)

    # 表10：一致性校验报告接口的数据元素；表11：状态接口的数据元素。
    fill_table(doc.tables[10], [
        ("1", "报告查询", "CheckReport", "check_id；status；run_at；rules_snapshot；summary；samples", "对象/数组", "一致性校验服务", "研究内容四", "任务完成时返回完整报告"),
        ("2", "样本结果", "SampleResult", "sample_id；source；knowledge；status；issues", "对象", "一致性校验服务", "研究内容四", "保留来源和知识引用"),
        ("3", "问题定位", "IssueLocalization", "issue_id；type；detail_type；desc；answer_location；evidence_locations；rationale；method；confidence", "对象/数组", "一致性校验服务", "研究内容四", "定位到答案claim及证据块/章节/行/字段"),
    ])
    fill_table(doc.tables[11], [
        ("1", "任务状态查询", "CheckStatus", "check_id；status；progress", "对象", "一致性校验服务", "全生命周期管理模块", "queued/running/done/error"),
        ("2", "进度信息", "Progress", "total；completed", "整数对象", "一致性校验服务", "全生命周期管理模块", "任务执行期间可选返回"),
        ("3", "校验统计", "Summary", "total；pass；warn；fail", "整数对象", "一致性校验服务", "全生命周期管理模块", "任务完成后提供"),
    ])


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    doc = Document(str(SOURCE))
    insert_interface_contract(doc)
    fill_existing_tables(doc)
    doc.save(str(OUTPUT))
    check = Document(str(OUTPUT))
    print(f"output={OUTPUT}")
    print(f"paragraphs={len(check.paragraphs)} tables={len(check.tables)}")
    print(f"table1_interfaces={len(check.tables[0].rows) - 1}")
    print(f"table10_report_fields={len(check.tables[10].rows) - 1}")
    print(f"table11_status_fields={len(check.tables[11].rows) - 1}")


if __name__ == "__main__":
    main()
