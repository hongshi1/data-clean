"""
insert_doc_str.py — 字符串操作直接编辑 .doc(Word 2003 XML),插入文字+表格(不插图)

策略:不改原有 XML 结构,只定位占位符段落 <w:p>...</w:p>,替换为
  标题段 + 描述段 + 表题段 + 表格 XML。
避免 ET 序列化破坏命名空间。
"""

from __future__ import annotations
import re

DOC = '/Users/gexuancheng/Desktop/research2/data_clean/docs/doc11/系统技术方案-yjw.doc'

CONTEXT_DESC = ('特征提取与上下文关联智能体面向SRS文档中分散在多章节、多模态（文字、图片、表格）'
                '的需求内容，提供多模态内容抽取、跨章节实体关联、条目聚合与语义角色标注能力，'
                '将同一需求/实体在不同位置的描述聚合为统一条目，为后续一致性校验提供明确的检测对象。'
                '包括多模态内容抽取、跨章节实体关联、条目聚合、语义角色标注、聚合力度判定等组件。')

CONTEXT_TABLE = [
    ['序号', '子功能名称', '功能描述'],
    ['1', '多模态内容抽取', '正文片段抽取、图表片段抽取，保留章节位置与模态信息'],
    ['2', '跨章节实体关联', '语义感知配对与结构邻接分析，判断分散在多处的描述是否指向同一事物'],
    ['3', '条目聚合', '片段组装与冲突预检，将同一实体的文字、图片、表格行聚合成统一条目'],
    ['4', '语义角色标注', '角色识别与角色赋值，标注片段角色（参数值/接口描述/约束条件等）'],
    ['5', '聚合力度判定', '粒度评分与多粒度选择，根据上下文判定聚合粒度（单参数/功能/接口）'],
]

CONSIST_DESC = ('数据一致性校验智能体对聚合后的需求条目执行语法、语义、逻辑三层一致性检测。'
                '语法一致性校验通过规则引擎推理与结构模板比对，检测章节缺失、编号不连续、需求ID重复等结构缺陷；'
                '语义一致性校验基于NLI蕴含判定、跨模态语义对齐与实体链接对齐，检测同一参数/概念在不同位置、'
                '不同模态（文字、图片、表格）描述中的值或含义矛盾；'
                '逻辑一致性校验通过SMT约束求解与专家知识比对，检测子模块时间之和≤总预算、允许与禁止矛盾等'
                '约束不可满足问题，并区分合理差异与真实矛盾，生成可溯源校验报告。')

CONSIST_TABLE = [
    ['序号', '校验层', '技术方法', '功能描述'],
    ['1', '语法一致性校验', '规则引擎推理', '将结构合规规则形式化为规则集，执行推理检测章节缺失、编号不连续、需求ID重复等缺陷'],
    ['2', '语法一致性校验', '结构模板比对', '将文档结构与GJB 438C标准模板比对，检测章节缺失与结构偏差'],
    ['3', '语义一致性校验', 'NLI蕴含判定', '基于自然语言推理判定两处描述的矛盾/蕴含/中立关系'],
    ['4', '语义一致性校验', '跨模态语义对齐', '对齐文字、图片、表格等多模态描述中的同一概念，检测含义矛盾'],
    ['5', '语义一致性校验', '实体链接对齐', '跨章节关联同一实体（参数/接口/功能），比对值或含义一致性'],
    ['6', '逻辑一致性校验', 'SMT约束求解', '将需求约束形式化为SMT公式，求解可满足性并生成反例'],
    ['7', '逻辑一致性校验', '专家知识比对', '借助领域专家知识比对约束间逻辑冲突（如允许与禁止矛盾）'],
]

COL_WIDTHS_CTX = [676, 1418, 7476]     # 特征提取:序号/子功能/功能描述
COL_WIDTHS_CST = [676, 1418, 1418, 6058]  # 一致性:序号/校验层/技术方法/功能描述


def esc(text: str) -> str:
    """XML 转义"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def para_xml(text: str, center: bool = False, bold: bool = False) -> str:
    """生成一个 w:p 段落 XML"""
    align = '<w:jc w:val="center"/>' if center else ''
    b = '<w:b/>' if bold else ''
    return (f'<w:p><w:pPr>{align}</w:pPr>'
            f'<w:r><w:rPr>{b}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def table_xml(rows: list, col_widths: list) -> str:
    """生成 w:tbl 表格 XML — 模仿文档原有表格格式(vAlign/shd/pStyle/trPr)"""
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)

    def tc_xml(text: str, w: int, bold: bool = False) -> str:
        b = '<w:b/>' if bold else ''
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
                f'<w:tcBorders>'
                f'<w:top w:val="single" w:sz="4" wx:bdrwidth="10" w:space="0" w:color="auto"/>'
                f'<w:left w:val="single" w:sz="4" wx:bdrwidth="10" w:space="0" w:color="auto"/>'
                f'<w:bottom w:val="single" w:sz="4" wx:bdrwidth="10" w:space="0" w:color="auto"/>'
                f'<w:right w:val="single" w:sz="4" wx:bdrwidth="10" w:space="0" w:color="auto"/>'
                f'</w:tcBorders>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="auto"/>'
                f'<w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="a89"/><w:rPr>{b}</w:rPr></w:pPr>'
                f'<w:r><w:rPr>{b}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p></w:tc>')

    trs = ''
    for i, row in enumerate(rows):
        tcs = ''.join(tc_xml(cell, col_widths[j], bold=(i == 0))
                      for j, cell in enumerate(row))
        trs += f'<w:tr><w:trPr><w:jc w:val="center"/></w:trPr>{tcs}</w:tr>'

    borders = ''
    for edge in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        borders += (f'<w:{edge} w:val="single" w:sz="4" w:space="0" w:color="auto"/>')
    return (f'<w:tbl><w:tblPr><w:tblW w:w="9570" w:type="dxa"/>'
            f'<w:jc w:val="center"/><w:tblInd w:w="0" w:type="dxa"/>'
            f'<w:tblBorders>{borders}</w:tblBorders>'
            f'<w:tblLayout w:type="Fixed"/><w:tblCellMar>'
            f'<w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
            f'<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/>'
            f'</w:tblCellMar></w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid>{trs}</w:tbl>')


def build_block(title: str, desc: str, table_data: list, tbl_title: str, col_widths: list) -> str:
    """构造 标题段 + 描述段 + 表题段 + 表格 的 XML"""
    return (para_xml(title, bold=True) +
            para_xml(desc) +
            para_xml(tbl_title, center=True, bold=True) +
            table_xml(table_data, col_widths))


def find_placeholder_para(s: str, keyword: str) -> tuple:
    """找含 keyword 且含'一段话'的 <w:p>...</w:p>,返回 (start, end)"""
    # 找 keyword 的所有位置
    for m in re.finditer(re.escape(keyword), s):
        pos = m.start()
        # 往前找最近的 <w:p (段落开始)
        p_start = s.rfind('<w:p>', 0, pos)
        if p_start == -1:
            p_start = s.rfind('<w:p ', 0, pos)
        # 往后找最近的 </w:p> (段落结束)
        p_end = s.find('</w:p>', pos)
        if p_start == -1 or p_end == -1:
            continue
        p_end += len('</w:p>')
        # 确认这个段落含"一段话"
        para_content = s[p_start:p_end]
        if '一段话' in para_content or '爪子图' in para_content:
            return p_start, p_end
    return None, None


def main():
    import shutil
    import os
    if not os.path.exists(DOC + '.orig'):
        shutil.copy(DOC, DOC + '.orig')
        print(f"已备份原始: {DOC}.orig")

    s = open(DOC, encoding='utf-8').read()
    print(f"文档大小: {len(s)} 字符")

    # 从后往前替换(避免位置偏移)
    blocks = [
        ('数据一致性校验智能体', '数据一致性校验智能体', CONSIST_DESC, CONSIST_TABLE,
         '表 3 数据一致性校验智能体功能划分', COL_WIDTHS_CST),
        ('特征提取与上下文关联智能体', '特征提取与上下文关联智能体', CONTEXT_DESC, CONTEXT_TABLE,
         '表 2 特征提取与上下文关联智能体功能划分', COL_WIDTHS_CTX),
    ]

    for keyword, title, desc, table, tbl_title, col_widths in blocks:
        start, end = find_placeholder_para(s, keyword)
        if start is None:
            print(f"  未找到: {keyword}")
            continue
        new_xml = build_block(title, desc, table, tbl_title, col_widths)
        s = s[:start] + new_xml + s[end:]
        print(f"  已替换: {keyword} (原段落 {end-start} 字符 -> 新内容 {len(new_xml)} 字符)")

    open(DOC, 'w', encoding='utf-8').write(s)
    print(f"\n已保存: {DOC} ({len(s)} 字符)")


if __name__ == '__main__':
    main()
