"""
insert_docx.py — 用 python-docx 在 .docx 占位符后插入 文字+图+表格

比操作 Word 2003 XML 稳妥:python-docx 的图片插入是标准 API,Word/LibreOffice 都能正确显示。
"""

from __future__ import annotations
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

DOCX = '/Users/gexuancheng/Desktop/research2/data_clean/docs/doc11/系统技术方案-yjw.docx'
BACKUP = DOCX + '.bak'

PNG_CONTEXT = '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_context_drawio.png'
PNG_CONSIST = '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_consistency_drawio.png'

CONTEXT_DESC = ('特征提取与上下文关联智能体面向SRS文档中分散在多章节、多模态（文字、图片、表格）'
                '的需求内容，提供多模态内容抽取、跨章节实体链接、条目聚合与语义角色标注能力，'
                '将同一需求/实体在不同位置的描述聚合为统一条目，为后续一致性校验提供明确的检测对象。'
                '包括多模态内容抽取、跨章节实体链接、条目聚合、语义角色标注、聚合粒度判定等组件。')

CONTEXT_TABLE = [
    ['序号', '子功能名称', '功能描述', '优先级'],
    ['1', '多模态内容抽取', '从markdown正文、接口图片、合格性表、追溯表中抽取需求片段', '高'],
    ['2', '跨章节实体链接', '基于语义相似与结构邻接，判断分散在多处的描述是否指向同一事物', '高'],
    ['3', '条目聚合', '将同一实体的文字片段、关联图片、表格行聚合成统一条目', '高'],
    ['4', '语义角色标注', '标注每个片段的角色（参数值/接口描述/约束条件等）', '中'],
    ['5', '聚合粒度判定', '根据上下文判定聚合粒度（单参数/功能/接口）', '中'],
]

CONSIST_DESC = ('数据一致性校验智能体对聚合后的需求条目执行语法、语义、逻辑三层一致性检测，'
                '识别SRS文档中存在的不一致问题，并对矛盾进行分类定位与报告生成。'
                '包括语法层校验、语义层校验、逻辑层校验、矛盾分类与定位、校验报告生成等组件。')

CONSIST_TABLE = [
    ['序号', '子功能名称', '功能描述', '优先级'],
    ['1', '语法层校验', '检测格式、编号、结构合规性，如章节缺失、编号不连续、ID重复', '高'],
    ['2', '语义层校验', '检测同一参数/概念在不同位置的值或含义是否一致', '高'],
    ['3', '逻辑层校验', '检测约束之间逻辑可满足性，如子模块时间之和≤总预算', '高'],
    ['4', '矛盾分类与定位', '区分合理差异与真实矛盾，定位冲突位置', '中'],
    ['5', '校验报告生成', '汇总检测结果，产出不一致类型、位置、建议修订', '中'],
]


def insert_para_after(prev: Paragraph, text: str = '', center: bool = False) -> Paragraph:
    """在 prev 段落后插入新段落"""
    new_p = OxmlElement('w:p')
    prev._element.addnext(new_p)
    para = Paragraph(new_p, prev._parent)
    if text:
        para.add_run(text)
    if center:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return para


def insert_image_after(prev: Paragraph, img_path: str, width_in: float = 6.0) -> Paragraph:
    """在 prev 段落后插入图片段落(居中)"""
    para = insert_para_after(prev)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    run.add_picture(img_path, width=Inches(width_in))
    return para


def _set_table_borders(tbl):
    """手动给表格加全边框(不依赖 Table Grid 样式)"""
    from docx.oxml.ns import qn
    tblPr = tbl._element.tblPr
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl._element.insert(0, tblPr)
    borders = OxmlElement('w:tblBorders')
    for edge in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), 'auto')
        borders.append(el)
    tblPr.append(borders)


def insert_table_after(prev: Paragraph, doc: Document, rows_data: list) -> Paragraph:
    """在 prev 段落后插入表格,返回表格后的锚点段落"""
    nrows = len(rows_data)
    ncols = len(rows_data[0])
    tbl = doc.add_table(rows=nrows, cols=ncols)
    tbl.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_table_borders(tbl)
    for i, row_data in enumerate(rows_data):
        for j, cell_text in enumerate(row_data):
            cell = tbl.cell(i, j)
            cell.text = cell_text
            if i == 0:
                for run in cell.paragraphs[0].runs:
                    run.bold = True
    prev._element.addnext(tbl._element)
    return insert_para_after(Paragraph(tbl._element, prev._parent))


def fill_placeholder(doc: Document, keyword: str, desc: str, table_data: list,
                     tbl_title: str):
    """找到含 keyword 的占位符段落,改标题,在其后插入 描述+表题+表格(不插图)"""
    target = None
    for p in doc.paragraphs:
        if keyword in p.text and '一段话' in p.text:
            target = p
            break
    if target is None:
        print(f"  未找到占位符: {keyword}")
        return
    for run in target.runs:
        run.text = ''
    target.runs[0].text = keyword
    print(f"  改标题: {keyword}")
    # 插入:描述 + 表题 + 表格
    p1 = insert_para_after(target, desc)
    p2 = insert_para_after(p1, tbl_title, center=True)
    insert_table_after(p2, doc, table_data)
    print(f"  已插入: 描述+{tbl_title}+表")


def main():
    import shutil
    if not __import__('os').path.exists(BACKUP):
        shutil.copy(DOCX, BACKUP)
    doc = Document(DOCX)

    # 从后往前填(避免索引/位置干扰)
    fill_placeholder(doc, '数据一致性校验智能体', CONSIST_DESC, CONSIST_TABLE,
                     '表 3 数据一致性校验智能体功能划分')
    fill_placeholder(doc, '特征提取与上下文关联智能体', CONTEXT_DESC, CONTEXT_TABLE,
                     '表 2 特征提取与上下文关联智能体功能划分')

    doc.save(DOCX)
    import os
    print(f"\n已保存: {DOCX} ({os.path.getsize(DOCX)} bytes)")


if __name__ == '__main__':
    main()
