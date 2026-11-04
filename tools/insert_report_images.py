"""Insert 5 images into the merged report (葛宣成 合稿.docx) at section 6.6.1.

Images (in order):
  1. scene1_data_structure.png  - 16份SRS块结构分析
  2. scene1_qa_analysis.png     - 91QA质量分析
  3. 上下文关联截图.png           - 系统运行: 上下文关联
  4. 发起一致性校验.png           - 系统运行: 发起校验
  5. 校验报告.png                - 系统运行: 校验报告

Each image gets a caption paragraph with figure number and cross-reference text.
"""
from __future__ import annotations

import copy
from pathlib import Path

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOC_PATH = Path(
    r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
    r"\msg\file\2026-11\葛宣成 合稿.docx")

IMAGES = [
    (Path("docs/srs_project/paper/test_screenshots/scene1_data_structure.png"),
     "图6-6-1-1 场景一原始数据结构分析：16份GJB SRS解析块构成",
     "（a）各文档正文/表格/图片/列表块数堆叠分布；（b）全语料块类型占比。"
     "16份真实GJB 438C格式SRS共形成5,423个解析块，其中正文2,829块、表格1,207张、"
     "图片381张、列表337张，为特征提取与上下文关联提供统一的多模态输入基础。"),
    (Path("docs/srs_project/paper/test_screenshots/scene1_qa_analysis.png"),
     "图6-6-1-2 场景一评测数据质量分析：91条QA的标签分布与证据覆盖",
     "（a）91条QA的silver三态标签分布：support 6条、refute 8条、not_in_evidence 77条；"
     "（b）每条QA的冻结证据块数分布（均值约6.3块）。该分析刻画了评测集的类别不平衡"
     "与证据覆盖密度，为功能验证结果的解读提供数据背景。"),
    (Path(r"C:\Users\12488\Pictures\Screenshots\上下文关联截图.png"),
     "图6-6-1-3 场景一上下文关联功能运行截图",
     "在演示系统中输入查询「修改数据功能支持哪些设备」（04号数据统一访问服务SRS），"
     "系统完成词法与BGE稠密双通路召回，以k-hop扩散从种子节点扩展至TXT/TBL/E等多模态"
     "证据组。中心节点命中04号SRS §3.2.1.1.1.2用例表，关联证据包括正文块、表格行和"
     "实体节点，验证了特征提取与上下文关联智能体的多模态聚合能力。"),
    (Path(r"C:\Users\12488\Pictures\Screenshots\发起一致性校验.png"),
     "图6-6-1-4 场景一一致性校验发起截图",
     "对04号数据统一访问服务SRS发起一致性校验（POST /api/check/04），系统进入异步"
     "校验流程。校验引擎执行52项目录规则与QA-VERDICT三态校验，覆盖术语（TERM）、"
     "参数（PARAM）、逻辑（LOGIC）与国军标合规（GJB）四类检测项，验证了数据一致性"
     "校验智能体的调度与执行能力。"),
    (Path(r"C:\Users\12488\Pictures\Screenshots\校验报告.png"),
     "图6-6-1-5 场景一一致性校验结果报告截图",
     "校验完成后系统输出汇总报告：共执行53项检测（52项目录规则+1项QA-VERDICT），"
     "QA-VERDICT通道检出多条refute结论（如VIO-02数据库关闭用例的项目唯一标识符"
     "冲突——answer使用的标识符与冻结证据中规定的接口标识不一致）。报告同时提供"
     "违例描述、证据位置和判定依据，验证了三层校验的分层结论输出与证据追溯能力。"),
]


def find_section(doc: docx.Document, marker: str) -> int:
    """Find paragraph index containing the marker text."""
    for i, p in enumerate(doc.paragraphs):
        if marker in p.text:
            return i
    return -1


def insert_after(doc: docx.Document, index: int, image_path: Path,
                 caption: str, description: str) -> None:
    """Insert image + caption + description after the given paragraph index."""
    from docx.oxml.ns import qn

    # Get the paragraph to insert after
    target_para = doc.paragraphs[index]
    target_element = target_para._element

    # Create a new paragraph for the image
    img_para = doc.add_paragraph()
    img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = img_para.add_run()
    run.add_picture(str(image_path), width=Inches(5.8))

    # Create caption paragraph
    cap_para = doc.add_paragraph()
    cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_run = cap_para.add_run(caption)
    cap_run.font.size = Pt(9)
    cap_run.font.bold = True

    # Create description paragraph
    desc_para = doc.add_paragraph()
    desc_run = desc_para.add_run(description)
    desc_run.font.size = Pt(9)

    # Move these paragraphs to after the target
    for para in [img_para, cap_para, desc_para]:
        target_element.addnext(para._element)
        target_element = para._element


def main() -> None:
    doc = docx.Document(str(DOC_PATH))

    # Find section 6.6.1 (场景一)
    idx_661 = find_section(doc, "6.6.1")
    if idx_661 < 0:
        idx_661 = find_section(doc, "6.6.1 场景1")
    if idx_661 < 0:
        # Try to find by looking for "场景1" or "场景一"
        for i, p in enumerate(doc.paragraphs):
            if "6.6.1" in p.text and ("场景" in p.text or "场景1" in p.text):
                idx_661 = i
                break

    print(f"6.6.1 found at paragraph index: {idx_661}")
    if idx_661 < 0:
        print("ERROR: Could not find section 6.6.1")
        return

    # Find the paragraph before 6.6.2 (场景2) - this is where we insert
    idx_662 = find_section(doc, "6.6.2")
    if idx_662 < 0:
        idx_662 = find_section(doc, "6.6.2 场景2")
    print(f"6.6.2 found at paragraph index: {idx_662}")

    # We'll insert after paragraph index 69 (the last paragraph of 6.6.1 content,
    # which is the "结果展示材料建议补充三组真实截图" paragraph)
    insert_after_idx = idx_662 - 1 if idx_662 > 0 else idx_661 + 3

    # Verify the insert point
    print(f"Insert after paragraph: {doc.paragraphs[insert_after_idx].text[:60]}")

    # Insert images in reverse order (so they end up in correct order)
    # since insert_after puts things after the target, we need to insert
    # the last one first, then work backwards
    # Actually, let's just insert them sequentially after the last inserted element

    # Find the actual insertion point - after paragraph 69 which is
    # "结果展示材料建议补充三组真实截图..."
    # Let's find that exact paragraph
    insert_target = None
    for i, p in enumerate(doc.paragraphs):
        if "结果展示材料建议补充三组真实截图" in p.text and i > idx_661:
            insert_target = i
            break

    if insert_target is None:
        insert_target = insert_after_idx

    print(f"Inserting after paragraph {insert_target}: "
          f"{doc.paragraphs[insert_target].text[:50]}")

    # Insert all 5 images sequentially
    from docx.oxml.ns import qn

    target_element = doc.paragraphs[insert_target]._element

    for img_path, caption, desc in IMAGES:
        # Image paragraph
        img_para = doc.add_paragraph()
        img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = img_para.add_run()
        run.add_picture(str(img_path), width=Inches(5.5))
        target_element.addnext(img_para._element)
        target_element = img_para._element

        # Caption paragraph
        cap_para = doc.add_paragraph()
        cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_run = cap_para.add_run(caption)
        cap_run.font.size = Pt(9)
        cap_run.font.bold = True
        target_element.addnext(cap_para._element)
        target_element = cap_para._element

        # Description paragraph
        desc_para = doc.add_paragraph()
        desc_run = desc_para.add_run(desc)
        desc_run.font.size = Pt(9)
        target_element.addnext(desc_para._element)
        target_element = desc_para._element

        print(f"  Inserted: {caption}")

    # Save
    output_path = DOC_PATH.parent / "葛宣成 合稿_含截图.docx"
    doc.save(str(output_path))
    print(f"\nSaved: {output_path}")

    # Also save in-place
    doc.save(str(DOC_PATH))
    print(f"Saved (in-place): {DOC_PATH}")


if __name__ == "__main__":
    main()
