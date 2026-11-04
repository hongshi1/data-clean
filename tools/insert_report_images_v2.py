"""Insert 5 images into 葛宣成 合稿.docx 6.6.1, matching scene-3/4 doc format.

Format rules (from 场景三试验/场景4实验):
  - Figure number: 图6-6-1-1 to 图6-6-1-5
  - Caption below image, single line: "图6-6-1-X 标题"
  - In-text reference: "如图6-6-1-X所示"
  - No (a)(b) sub-labels
  - Functional description flows naturally, no meaningless IDs
  - Image width ~5.5 inches, centered
"""
from __future__ import annotations

from pathlib import Path

import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOC_PATH = Path(
    r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
    r"\msg\file\2026-11\葛宣成 合稿_含截图.docx")

# (image_path, caption, description_paragraph_text)
# description goes BEFORE the image, referencing it naturally
FIGURES = [
    (
        Path("docs/srs_project/paper/test_screenshots/scene1_data_structure.png"),
        "图6-6-1-1 场景一原始数据结构分析（16份GJB SRS解析块构成）",
        "场景一的原始数据为16份真实GJB 438C格式软件需求规格说明书。解析后共形成"
        "5,423个结构化块，其中正文块2,829个、表格1,207张、图片381张、列表337个，"
        "覆盖正文、表格、图片、追溯与合格性等多模态证据形态。各文档的块构成存在"
        "明显差异，部分文档以正文为主，部分文档表格占比较高，如图6-6-1-1所示。"
        "这一结构特征决定了特征提取与上下文关联必须同时处理不同模态的内容单元。",
    ),
    (
        Path("docs/srs_project/paper/test_screenshots/scene1_qa_analysis.png"),
        "图6-6-1-2 场景一评测数据质量分析（91条QA标签分布与证据覆盖）",
        "场景一的评测数据集由91条官方问答对构成。经过GLM-5.3复核的参考标签"
        "分布为support 6条、refute 8条、not_in_evidence 77条，呈现出明显的类别"
        "不平衡特征。每条问答对平均冻结6.3个证据块，但分布不均匀，部分问答仅关联"
        "2至3块证据，部分关联超过10块，如图6-6-2所示。该分析为后续功能验证"
        "结果的解读提供了数据背景。",
    ),
    (
        Path(r"C:\Users\12488\Pictures\Screenshots\上下文关联截图.png"),
        "图6-6-1-3 场景一上下文关联功能运行截图",
        "在演示系统的上下文关联界面输入查询后，系统完成词法与稠密双通路召回，"
        "以k-hop扩散从种子节点扩展至正文、表格、实体等多模态证据组。中心节点"
        "命中对应的用例表，关联证据包括正文块、表格行和实体节点。如图6-6-1-3"
        "所示，界面展示了中心节点、证据分组和关联路径，验证了特征提取与上下文"
        "关联智能体的多模态聚合功能能够正常调用、执行并输出可查看的结果。",
    ),
    (
        Path(r"C:\Users\12488\Pictures\Screenshots\发起一致性校验.png"),
        "图6-6-1-4 场景一一致性校验发起截图",
        "对选定的软件需求规格说明发起一致性校验后，系统进入异步校验流程。"
        "校验引擎执行目录规则与问答三态校验，覆盖术语、参数、逻辑与国军标合规"
        "四类检测项。如图6-6-4所示，系统展示了校验的执行状态与进度，验证了"
        "数据一致性校验智能体的调度与执行功能能够正常触发并运行。",
    ),
    (
        Path(r"C:\Users\12488\Pictures\Screenshots\校验报告.png"),
        "图6-6-1-5 场景一一致性校验结果报告截图",
        "校验完成后系统输出汇总报告，包含检测项执行状态、发现的问题描述、"
        "证据位置与判定依据。报告中的问答校验结论检出多条矛盾，例如数据库关闭"
        "用例的项目唯一标识符与冻结证据中规定的接口标识不一致。如图6-6-1-5"
        "所示，校验报告展示了分层结论与证据溯源路径，验证了一致性校验的结论"
        "输出与来源回查功能能够正常展示并可追溯。",
    ),
]


def main() -> None:
    doc = docx.Document(str(DOC_PATH))

    # Find the "结果展示材料建议补充三组真实截图" paragraph in 6.6.1
    insert_idx = -1
    for i, p in enumerate(doc.paragraphs):
        if "结果展示材料建议补充三组真实截图" in p.text and i > 60:
            insert_idx = i
            break

    if insert_idx < 0:
        print("ERROR: insertion point not found")
        return

    print(f"Inserting after paragraph {insert_idx}: "
          f"{doc.paragraphs[insert_idx].text[:50]}...")

    target_element = doc.paragraphs[insert_idx]._element

    for img_path, caption, desc_text in FIGURES:
        # Description paragraph (before image)
        desc_para = doc.add_paragraph()
        desc_run = desc_para.add_run(desc_text)
        desc_run.font.size = Pt(10)
        desc_para.paragraph_format.first_line_indent = Pt(20)
        target_element.addnext(desc_para._element)
        target_element = desc_para._element

        # Image paragraph (centered)
        img_para = doc.add_paragraph()
        img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = img_para.add_run()
        run.add_picture(str(img_path), width=Inches(5.5))
        target_element.addnext(img_para._element)
        target_element = img_para._element

        # Caption paragraph (below image, centered, small bold)
        cap_para = doc.add_paragraph()
        cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_run = cap_para.add_run(caption)
        cap_run.font.size = Pt(9)
        cap_run.font.bold = True
        target_element.addnext(cap_para._element)
        target_element = cap_para._element

        print(f"  Inserted: {caption}")

    # Save
    output_path = DOC_PATH.parent / "葛宣成 合稿_含截图v2.docx"
    doc.save(str(output_path))
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
