"""Insert scene-5 figures into 合稿 6.6.5, matching v3 cross-reference format."""
from __future__ import annotations

import re
from pathlib import Path

from lxml import etree
import docx
from docx.shared import Inches, Pt
from docx.oxml.ns import qn

DOC_PATH = Path(
    r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
    r"\msg\file\2026-11\葛宣成 合稿_含截图v3.docx")

FIGURES = [
    (
        Path("docs/srs_project/paper/test_screenshots/scene5_data_analysis.png"),
        "图6-6-5-1",
        "场景五原始数据分析",
        "RefFigure6_6_5_1",
        "场景五的原始数据为672条图片问答对，覆盖睡岗检测任务在模型量化前后的"
        "输出变体。每组96条问答对包含task、answer、evidence和timestamp四个"
        "字段。量化前后的答案分布保持一致（answer=0约45条、answer=1约51条），"
        "每条QA的evidence字段长度集中在1至4条。如图6-6-5-1所示，该分析"
        "刻画了评测数据的基本规模与答案分布特征。",
    ),
    (
        Path("docs/srs_project/paper/test_screenshots/scene5_qa_fields.png"),
        "图6-6-5-2",
        "场景五QA字段结构化展示",
        "RefFigure6_6_5_2",
        "场景五的问答对采用结构化JSON格式输出。每条QA包含任务名称（task）、"
        "判定结论（answer，0表示未检测到、1表示检测到）、证据描述（evidence）"
        "和时间戳（timestamp）。如图6-6-5-2所示，以睡岗检测任务为例，"
        "系统输出的人员姿态描述、位置信息和画面时间戳均可逐条核对，验证了"
        "图片问答数据的结构化输出功能。",
    ),
    (
        Path("docs/srs_project/paper/test_screenshots/scene5_conflict_analysis.png"),
        "图6-6-5-3",
        "场景五同类样本结论一致性检测",
        "RefFigure6_6_5_3",
        "对量化前后的96张同编号图片进行逐条比对，检测同一图片在不同模型"
        "条件下的结论是否一致。比对结果显示96张图片中96张结论一致、0张"
        "存在冲突，量化操作未引入结论翻转。如图6-6-5-3所示，该分析验证了"
        "同类样本结论冲突检测功能的可行性，为后续跨条件一致性校验提供了"
        "数据基础。",
    ),
    (
        Path("docs/srs_project/paper/test_screenshots/scene5_conflict_check.png"),
        "图6-6-5-4",
        "场景五冲突检测运行截图",
        "RefFigure6_6_5_4",
        "冲突检测工具对量化前后的问答数据进行自动化比对，统计对比样本数、"
        "结论冲突数和冲突率，并列出冲突样本的图片编号与答案变化明细。如图"
        "6-6-5-4所示，检测结果显示当前数据集中未发现结论冲突，验证了"
        "同类样本比对与冲突提示功能的正常执行。",
    ),
]


def make_caption(doc, number: str, title: str, bookmark_name: str):
    cap_para = doc.add_paragraph()
    cap_para.alignment = 1
    for run in list(cap_para.runs):
        run._element.getparent().remove(run._element)

    p_elem = cap_para._element
    bookmark_id = 950 + hash(bookmark_name) % 100
    bm_start = etree.SubElement(p_elem, qn("w:bookmarkStart"))
    bm_start.set(qn("w:id"), str(bookmark_id))
    bm_start.set(qn("w:name"), bookmark_name)

    number_run = cap_para.add_run(number)
    number_run.font.name = "黑体"
    number_run.font.bold = True
    number_run.font.size = Pt(10.5)

    bm_end = etree.SubElement(p_elem, qn("w:bookmarkEnd"))
    bm_end.set(qn("w:id"), str(bookmark_id))

    title_run = cap_para.add_run(" " + title)
    title_run.font.name = "黑体"
    title_run.font.bold = True
    title_run.font.size = Pt(10.5)
    return cap_para


def make_body(doc, text: str, bookmark_name: str):
    body_para = doc.add_paragraph()
    body_para.alignment = 3
    pattern = r"(图6-6-5-\d)"
    parts = re.split(pattern, text)
    for part in parts:
        if re.match(r"图6-6-5-\d", part):
            ref_run = body_para.add_run()
            fld_begin = etree.SubElement(ref_run._element, qn("w:fldChar"))
            fld_begin.set(qn("w:fldCharType"), "begin")
            instr = etree.SubElement(ref_run._element, qn("w:instrText"))
            instr.set(qn("xml:space"), "preserve")
            instr.text = f" REF {bookmark_name} \\h "
            fld_sep = etree.SubElement(ref_run._element, qn("w:fldChar"))
            fld_sep.set(qn("w:fldCharType"), "separate")
            display_run = body_para.add_run(part)
            display_run.font.size = Pt(10.5)
            fld_end_run = body_para.add_run()
            fld_end = etree.SubElement(fld_end_run._element, qn("w:fldChar"))
            fld_end.set(qn("w:fldCharType"), "end")
        elif part:
            text_run = body_para.add_run(part)
            text_run.font.size = Pt(10.5)
    return body_para


def main() -> None:
    doc = docx.Document(str(DOC_PATH))

    # Find insertion point: after "结果展示材料建议补充三组真实截图" in 6.6.5
    # (the second occurrence, after scene-5 content)
    insert_idx = -1
    found_65 = False
    for i, p in enumerate(doc.paragraphs):
        if "6.6.5" in p.text and "场景" in p.text:
            found_65 = True
        if found_65 and "结果展示材料建议补充三组真实截图" in p.text:
            insert_idx = i
            break

    if insert_idx < 0:
        print("ERROR: insertion point not found")
        return

    print(f"Inserting after paragraph {insert_idx}")
    target_element = doc.paragraphs[insert_idx]._element

    for img_path, fig_number, fig_title, bookmark_name, body_text in FIGURES:
        body_para = make_body(doc, body_text, bookmark_name)
        target_element.addnext(body_para._element)
        target_element = body_para._element

        img_para = doc.add_paragraph()
        img_para.alignment = 1
        run = img_para.add_run()
        run.add_picture(str(img_path), width=Inches(5.5))
        target_element.addnext(img_para._element)
        target_element = img_para._element

        cap_para = make_caption(doc, fig_number, fig_title, bookmark_name)
        target_element.addnext(cap_para._element)
        target_element = cap_para._element

        print(f"  Inserted: {fig_number} {fig_title}")

    output_path = DOC_PATH.parent / "葛宣成 合稿_含截图v4.docx"
    doc.save(str(output_path))
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
