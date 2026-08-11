"""
insert_into_doc.py — 把(文字+图+表格)插入 系统技术方案-yjw.doc

目标:在两个占位符段落后面插入内容
  段落[230]: 特征提取与上下文关联智能体 → 插入 描述+图+图题+表题+表
  段落[236]: 数据一致性校验智能体 → 同上

图:用 draw.io 渲染的黑白三层 PNG(模仿范例的 w:binData + v:imagedata 嵌入方式)
表:模仿范例 w:tbl 结构(4列:序号/子功能名称/功能描述/优先级)

文档格式:Word 2003 XML (WordML)
"""

from __future__ import annotations
import os
import base64
import copy
import xml.etree.ElementTree as ET

DOC = '/Users/gexuancheng/Desktop/research2/data_clean/docs/doc11/系统技术方案-yjw.doc'
BACKUP = DOC + '.bak'

W = '{http://schemas.microsoft.com/office/word/2003/wordml}'
V = '{urn:schemas-microsoft-com:vml}'
O = '{urn:schemas-microsoft-com:office:office}'

# 注册命名空间前缀,保持序列化后前缀一致
ET.register_namespace('w', 'http://schemas.microsoft.com/office/word/2003/wordml')
ET.register_namespace('v', 'urn:schemas-microsoft-com:vml')
ET.register_namespace('o', 'urn:schemas-microsoft-com:office:office')
ET.register_namespace('w10', 'urn:schemas-microsoft-com:office:word')
ET.register_namespace('wx', 'http://schemas.microsoft.com/office/word/2003/auxHint')
ET.register_namespace('aml', 'http://schemas.microsoft.com/aml/2001/core')
ET.register_namespace('dt', 'uuid:C2F41010-65B3-11d1-A29F-00AA00C14882')
ET.register_namespace('sl', 'http://schemas.microsoft.com/schemaLibrary/2003/core')
ET.register_namespace('wpsCustomData', 'http://www.wps.cn/officeDocument/2013/wpsCustomData')


def make_para(text: str, style: str = 'a74') -> ET.Element:
    """普通段落"""
    p = ET.Element(f'{W}p')
    pPr = ET.SubElement(p, f'{W}pPr')
    ET.SubElement(pPr, f'{W}pStyle', {'val': style})
    r = ET.SubElement(p, f'{W}r')
    t = ET.SubElement(r, f'{W}t')
    t.text = text
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    return p


def make_image_para(png_path: str, bin_name: str, width_pt: int, height_pt: int) -> ET.Element:
    """图片段落:模仿范例 w:pict + w:binData + v:shape + v:imagedata"""
    with open(png_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    p = ET.Element(f'{W}p')
    pPr = ET.SubElement(p, f'{W}pPr')
    ET.SubElement(pPr, f'{W}pStyle', {'val': 'a74'})
    r = ET.SubElement(p, f'{W}r')
    pict = ET.SubElement(r, f'{W}pict')
    bd = ET.SubElement(pict, f'{W}binData', {'name': bin_name})
    bd.text = b64
    shape = ET.SubElement(pict, f'{V}shape', {
        'id': '_x0000_i1025', 'type': '#_x0000_t75',
        'style': f'width:{width_pt}pt;height:{height_pt}pt'
    })
    ET.SubElement(shape, f'{V}imagedata', {'src': bin_name, 'o:title': ''})
    return p


def make_table(rows: list[list[str]], col_widths: list[int]) -> ET.Element:
    """4列表格,模仿范例结构。rows[0] 为表头"""
    tbl = ET.Element(f'{W}tbl')
    # tblPr
    tblPr = ET.SubElement(tbl, f'{W}tblPr')
    ET.SubElement(tblPr, f'{W}tblW', {'w': '9570', 'type': 'dxa'})
    ET.SubElement(tblPr, f'{W}jc', {'val': 'center'})
    ET.SubElement(tblPr, f'{W}tblInd', {'w': '0', 'type': 'dxa'})
    borders = ET.SubElement(tblPr, f'{W}tblBorders')
    for b in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        ET.SubElement(borders, f'{W}{b}', {'val': 'single', 'sz': '4',
                                            'space': '0', 'color': 'auto'})
    ET.SubElement(tblPr, f'{W}tblLayout', {'type': 'Fixed'})
    cellMar = ET.SubElement(tblPr, f'{W}tblCellMar')
    for s, w in [('top', '0'), ('left', '108'), ('bottom', '0'), ('right', '108')]:
        ET.SubElement(cellMar, f'{W}{s}', {'w': w, 'type': 'dxa'})
    # tblGrid
    grid = ET.SubElement(tbl, f'{W}tblGrid')
    for cw in col_widths:
        ET.SubElement(grid, f'{W}gridCol', {'w': str(cw)})
    # 行
    for row_data in rows:
        tr = ET.SubElement(tbl, f'{W}tr')
        for cell_text in row_data:
            tc = ET.SubElement(tr, f'{W}tc')
            tcPr = ET.SubElement(tc, f'{W}tcPr')
            ET.SubElement(tcPr, f'{W}tcW', {'w': '0', 'type': 'auto'})
            p = ET.SubElement(tc, f'{W}p')
            r = ET.SubElement(p, f'{W}r')
            t = ET.SubElement(r, f'{W}t')
            t.text = cell_text
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    return tbl


# ============ 内容定义 ============

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

COL_WIDTHS = [676, 1418, 2018, 5458]  # 序号/子功能/功能描述/优先级

PNG_CONTEXT = '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_context_drawio.png'
PNG_CONSIST = '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_consistency_drawio.png'


def main():
    # 备份
    import shutil
    if not os.path.exists(BACKUP):
        shutil.copy(DOC, BACKUP)
        print(f"已备份: {BACKUP}")

    tree = ET.parse(DOC)
    root = tree.getroot()
    paras = list(root.iter(f'{W}p'))

    # 建立 parent map
    parent_map = {c: p for p in root.iter() for c in p}

    def insert_after(target_para, new_elements):
        """在 target_para 之后插入多个元素"""
        parent = parent_map.get(target_para)
        if parent is None:
            print("  找不到父元素!")
            return
        children = list(parent)
        idx = children.index(target_para)
        for i, el in enumerate(new_elements):
            parent.insert(idx + 1 + i, el)

    # === 段落[230]: 特征提取与上下文关联智能体 ===
    # 先把占位符文字改成纯标题
    p230 = paras[230]
    for t in p230.iter(f'{W}t'):
        if '一段话' in (t.text or ''):
            t.text = '特征提取与上下文关联智能体'
    # 构造插入内容
    ctx_elements = [
        make_para(CONTEXT_DESC),
        make_image_para(PNG_CONTEXT, 'wordml://101.png', 468, 202),
        make_para('图 2 特征提取与上下文关联智能体组成图'),
        make_para('表 2 特征提取与上下文关联智能体功能划分'),
        make_table(CONTEXT_TABLE, COL_WIDTHS),
    ]
    insert_after(p230, ctx_elements)
    print("已插入: 特征提取与上下文关联智能体 (文字+图+表)")

    # === 重新获取 paras(插入后索引变了),找数据一致性校验 ===
    paras2 = list(root.iter(f'{W}p'))
    for p in paras2:
        txt = ''.join(t.text or '' for t in p.iter(f'{W}t'))
        if '数据一致性校验智能体' in txt and '一段话' in txt:
            # 改标题
            for t in p.iter(f'{W}t'):
                if '一段话' in (t.text or ''):
                    t.text = '数据一致性校验智能体'
            cons_elements = [
                make_para(CONSIST_DESC),
                make_image_para(PNG_CONSIST, 'wordml://102.png', 468, 202),
                make_para('图 3 数据一致性校验智能体组成图'),
                make_para('表 3 数据一致性校验智能体功能划分'),
                make_table(CONSIST_TABLE, COL_WIDTHS),
            ]
            insert_after(p, cons_elements)
            print("已插入: 数据一致性校验智能体 (文字+图+表)")
            break

    # 保存
    tree.write(DOC, xml_declaration=True, encoding='UTF-8', default_namespace=None)
    print(f"\n已保存: {DOC} ({os.path.getsize(DOC)} bytes)")


if __name__ == '__main__':
    main()
