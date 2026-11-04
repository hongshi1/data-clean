"""Insert 5 figures into 合稿 6.6.1 with proper Word cross-references.

Replicates the exact format used in the merged report:
  - Figure caption: "图表名称" style, centered, bold, 黑体 10.5pt
  - Caption text: "图6-6-1-X 标题" (number is inside bookmark)
  - Bookmark on number: RefFigure6_6_1_X
  - Body text: REF field cross-referencing the bookmark
  - Body paragraph: Normal style, justified, first-line indent
  - Image: centered, 5.5 inches wide
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree
import docx
from docx.shared import Inches, Pt
from docx.oxml.ns import qn

DOC_PATH = Path(
    r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
    r"\msg\file\2026-11\葛宣成 合稿.docx")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

FIGURES = [
    (
        Path("docs/srs_project/paper/test_screenshots/scene1_data_structure.png"),
        "图6-6-1-1",
        "场景一原始数据结构分析",
        RefFigure6_6_1_1 := "RefFigure6_6_1_1",
        "场景一的原始数据为16份真实GJB 438C格式软件需求规格说明书。解析后共形成"
        "5,423个结构化块，其中正文块2,829个、表格1,207张、图片381张、列表337个。"
        "各文档的模态构成存在明显差异，部分文档以正文为主，部分文档表格占比较高，"
        "如图6-6-1-1所示。这一结构特征决定了特征提取与上下文关联必须同时处理"
        "不同模态的内容单元，为后续功能验证提供了数据基础。",
    ),
    (
        Path("docs/srs_project/paper/test_screenshots/scene1_qa_analysis.png"),
        "图6-6-1-2",
        "场景一评测数据质量分析",
        RefFigure6_6_1_2 := "RefFigure6_6_1_2",
        "场景一的评测数据集由91条官方问答对构成。经过GLM-5.3复核的参考标签"
        "分布为support 6条、refute 8条、not_in_evidence 77条。每条问答对平均"
        "冻结6.3个证据块，但分布不均匀，如图6-6-1-2所示。该分析刻画了评测集"
        "的类别不平衡与证据覆盖密度，为功能验证结果的解读提供了数据背景。",
    ),
    (
        Path(r"C:\Users\12488\Pictures\Screenshots\上下文关联截图.png"),
        "图6-6-1-3",
        "场景一上下文关联功能运行截图",
        RefFigure6_6_1_3 := "RefFigure6_6_1_3",
        "在演示系统的上下文关联界面输入查询后，系统完成词法与稠密双通路召回，"
        "以k-hop扩散从种子节点扩展至正文、表格、实体等多模态证据组。中心节点"
        "命中对应的用例表，关联证据包括正文块、表格行和实体节点。如图6-6-1-3"
        "所示，界面展示了中心节点、证据分组和关联路径，验证了特征提取与上下文"
        "关联智能体的多模态聚合功能能够正常调用、执行并输出可查看的结果。",
    ),
    (
        Path(r"C:\Users\12488\Pictures\Screenshots\发起一致性校验.png"),
        "图6-6-1-4",
        "场景一一致性校验发起截图",
        RefFigure6_6_1_4 := "RefFigure6_6_1_4",
        "对选定的软件需求规格说明发起一致性校验后，系统进入异步校验流程。"
        "校验引擎执行目录规则与问答三态校验，覆盖术语、参数、逻辑与国军标"
        "合规四类检测项。如图6-6-1-4所示，系统展示了校验的执行状态与进度，"
        "验证了数据一致性校验智能体的调度与执行功能能够正常触发并运行。",
    ),
    (
        Path(r"C:\Users\12488\Pictures\Screenshots\校验报告.png"),
        "图6-6-1-5",
        "场景一一致性校验结果报告截图",
        RefFigure6_6_1_5 := "RefFigure6_6_1_5",
        "校验完成后系统输出汇总报告，包含检测项执行状态、发现的问题描述、"
        "证据位置与判定依据。报告中的问答校验结论检出多条矛盾，例如数据库"
        "关闭用例的项目唯一标识符与冻结证据中规定的接口标识不一致。如图"
        "6-6-1-5所示，校验报告展示了分层结论与证据溯源路径，验证了一致性"
        "校验的结论输出与来源回查功能能够正常展示并可追溯。",
    ),
]


def make_caption_paragraph(doc, number: str, title: str, bookmark_name: str):
    """Create a caption paragraph with bookmark on the number, matching 图2-1 format."""
    # Create a new paragraph
    cap_para = doc.add_paragraph()

    # Set alignment to center
    cap_para.alignment = 1  # CENTER

    # Clear existing content
    for run in list(cap_para.runs):
        run._element.getparent().remove(run._element)

    # Build the XML manually to match 图2-1's structure
    p_elem = cap_para._element

    # Add bookmarkStart before the number run
    bookmark_id = 900 + hash(bookmark_name) % 100  # unique-ish ID
    bookmark_start = etree.SubElement(p_elem, qn("w:bookmarkStart"))
    bookmark_start.set(qn("w:id"), str(bookmark_id))
    bookmark_start.set(qn("w:name"), bookmark_name)

    # Add the number run (bold, 黑体, 10.5pt = sz 21)
    number_run = cap_para.add_run(number)
    number_run.font.name = "黑体"
    number_run.font.bold = True
    number_run.font.size = Pt(10.5)

    # Add bookmarkEnd
    bookmark_end = etree.SubElement(p_elem, qn("w:bookmarkEnd"))
    bookmark_end.set(qn("w:id"), str(bookmark_id))

    # Add the title run
    title_run = cap_para.add_run(" " + title)
    title_run.font.name = "黑体"
    title_run.font.bold = True
    title_run.font.size = Pt(10.5)

    return cap_para


def make_body_paragraph(doc, text_with_marker: str, bookmark_name: str):
    """Create a body paragraph with REF cross-reference field.

    text_with_marker contains '如图6-6-1-X所示' style text.
    We split it to insert REF fields around the figure reference.
    """
    body_para = doc.add_paragraph()
    body_para.alignment = 3  # JUSTIFY

    # Find the figure reference in the text (e.g., "如图6-6-1-3")
    # and replace it with a REF field
    import re
    # Match patterns like 图6-6-1-3
    pattern = r'(图6-6-1-\d)'
    parts = re.split(pattern, text_with_marker)

    for part in parts:
        if re.match(r'图6-6-1-\d', part):
            # This is the figure reference - insert REF field
            ref_run = body_para.add_run()
            fld_begin = etree.SubElement(ref_run._element, qn("w:fldChar"))
            fld_begin.set(qn("w:fldCharType"), "begin")
            instr = etree.SubElement(ref_run._element, qn("w:instrText"))
            instr.set(qn("xml:space"), "preserve")
            instr.text = f" REF {bookmark_name} \\h "
            fld_sep = etree.SubElement(ref_run._element, qn("w:fldChar"))
            fld_sep.set(qn("w:fldCharType"), "separate")
            # Display text (placeholder until Word updates it)
            display_run = body_para.add_run(part)
            display_run.font.size = Pt(10.5)
            # Add fldEnd
            fld_end_run = body_para.add_run()
            fld_end = etree.SubElement(fld_end_run._element, qn("w:fldChar"))
            fld_end.set(qn("w:fldCharType"), "end")
        elif part:
            # Normal text
            text_run = body_para.add_run(part)
            text_run.font.size = Pt(10.5)

    return body_para


def main() -> None:
    doc = docx.Document(str(DOC_PATH))

    # Find insertion point: after "结果展示材料建议补充三组真实截图" paragraph
    insert_idx = -1
    for i, p in enumerate(doc.paragraphs):
        if "结果展示材料建议补充三组真实截图" in p.text and i > 60:
            insert_idx = i
            break

    if insert_idx < 0:
        print("ERROR: insertion point not found")
        return

    print(f"Inserting after paragraph {insert_idx}")

    target_element = doc.paragraphs[insert_idx]._element

    for img_path, fig_number, fig_title, bookmark_name, body_text in FIGURES:
        # 1. Body paragraph (with REF cross-reference)
        body_para = make_body_paragraph(doc, body_text, bookmark_name)
        target_element.addnext(body_para._element)
        target_element = body_para._element

        # 2. Image paragraph (centered)
        img_para = doc.add_paragraph()
        img_para.alignment = 1  # CENTER
        run = img_para.add_run()
        run.add_picture(str(img_path), width=Inches(5.5))
        target_element.addnext(img_para._element)
        target_element = img_para._element

        # 3. Caption paragraph (with bookmark)
        cap_para = make_caption_paragraph(doc, fig_number, fig_title, bookmark_name)
        target_element.addnext(cap_para._element)
        target_element = cap_para._element

        print(f"  Inserted: {fig_number} {fig_title}")

    # Save
    output_path = DOC_PATH.parent / "葛宣成 合稿_含截图v3.docx"
    doc.save(str(output_path))
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
