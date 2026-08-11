"""
gen_fishbone.py — 生成 GJB 部件组成图(3层黑白爪子图) .vsdx

层级:
  第1层:智能体(1个)
  第2层:能力模块(5个)
  第3层:子功能(每模块2个)
共 1+5+10 = 16 框。

样式:黑白(白底黑线黑字),GJB 标准朴素风格。
字体:暂用默认(后续可在 Visio 里全选改黑体10pt)。
命名空间修复:save_vsdx 后自动修复,确保 LibreOffice/Visio 渲染不空白。
"""

from __future__ import annotations
import os
import re
import zipfile
import xml.etree.ElementTree as ET
import vsdx

VISIO_NS = 'http://schemas.microsoft.com/office/visio/2012/main'
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

PAGE_W, PAGE_H = 11.69, 8.27  # 横向 A4

# 黑白颜色(Visio 调色板索引:0=黑,1=白)
C_WHITE = '1'
C_BLACK = '0'


def fix_namespaces(src_vsdx: str, dst_vsdx: str) -> None:
    """修复 vsdx 库 save_vsdx 的命名空间 bug"""
    z = zipfile.ZipFile(src_vsdx)
    with zipfile.ZipFile(dst_vsdx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name in z.namelist():
            data = z.read(name)
            if name.endswith('.xml') or name.endswith('.rels'):
                text = data.decode('utf-8')
                text = text.replace(f'xmlns:ns0="{VISIO_NS}"', f'xmlns="{VISIO_NS}"')
                text = text.replace('ns0:', '')
                if 'r:' in text and f'xmlns:r="{REL_NS}"' not in text:
                    text = re.sub(r'(<\w+\s+xmlns="[^"]*")',
                                  rf'\1 xmlns:r="{REL_NS}"', text, count=1)
                data = text.encode('utf-8')
            zout.writestr(name, data)


def _set_size(shape, w: float, h: float) -> None:
    shape.set_cell_value('Width', str(w))
    shape.set_cell_value('Height', str(h))


def _style_blackwhite(shape) -> None:
    """白底黑线黑字 + 圆角 + 文字居中 + 字号"""
    shape.fill_color = C_WHITE
    shape.line_color = C_BLACK
    shape.text_color = C_BLACK
    _enhance_shape(shape)


def _enhance_shape(shape) -> None:
    """直接操作 XML 加:圆角 Cell / Para(居中) / Character(字号)。
    vsdx 库的 set_cell_value 只能改已有 cell,新属性必须操作 XML。
    元素顺序:Cell → Character → Para → Property → Geometry → Text
    """
    NS = '{http://schemas.microsoft.com/office/visio/2012/main}'
    xml = shape.xml

    def first_section_index():
        """第一个 Section 或 Text 的位置"""
        for i, child in enumerate(xml):
            tag = child.tag
            if tag.endswith('Section') or tag.endswith('Text'):
                return i
        return len(xml)

    # 1) 圆角 Cell(插在第一个 Section 之前)
    if not xml.find(f'{NS}Cell[@N="Rounding"]'):
        rcell = ET.Element(f'{NS}Cell', {'N': 'Rounding', 'V': '0.1'})
        xml.insert(first_section_index(), rcell)

    # 2) Character section(字号 10pt = 0.1389in)—— 插在 Property/Geometry 之前
    if not xml.find(f'{NS}Section[@N="Character"]'):
        sec = ET.Element(f'{NS}Section', {'N': 'Character'})
        row = ET.SubElement(sec, f'{NS}Row', {'T': '9', 'IX': '0'})
        ET.SubElement(row, f'{NS}Cell', {'N': 'Size', 'V': '0.1389'})
        ET.SubElement(row, f'{NS}Cell', {'N': 'Style', 'V': '17'})
        xml.insert(first_section_index(), sec)

    # 3) Para section(水平居中 HorizAlign=1)—— 插在 Character 之后
    if not xml.find(f'{NS}Section[@N="Para"]'):
        sec = ET.Element(f'{NS}Section', {'N': 'Para'})
        row = ET.SubElement(sec, f'{NS}Row', {'IX': '0'})
        ET.SubElement(row, f'{NS}Cell', {'N': 'HorizAlign', 'V': '1'})
        xml.insert(first_section_index(), sec)


def _arrow(connector) -> None:
    """给连线加箭头(EndArrow=1)"""
    try:
        connector.set_cell_value('EndArrow', '1')
        connector.set_cell_value('BeginArrow', '0')
    except Exception:
        pass


def build_fishbone(root: str, modules: list[tuple[str, list[str]]], out_vsdx: str) -> None:
    """生成 3 层黑白爪子图 vsdx。
    modules: [(模块名, [子功能1, 子功能2]), ...]
    """
    template = os.path.join(os.path.dirname(vsdx.__file__), 'media', 'media.vsdx')
    with vsdx.VisioFile(template) as vis:
        page = vis.get_page_by_name('Page-1')
        page.width = PAGE_W
        page.height = PAGE_H

        rect_src = page.find_shape_by_text('RECTANGLE')
        if rect_src is None:
            raise RuntimeError('模板里找不到 RECTANGLE')
        orig_shapes = list(page.child_shapes or [])

        n = len(modules)
        # 布局
        root_w, root_h = 4.8, 0.8
        mod_w, mod_h = 2.0, 0.7
        leaf_w, leaf_h = 1.8, 0.55
        mod_gap = 0.25
        leaf_gap_y = 0.2

        root_cx = PAGE_W / 2
        root_cy = PAGE_H - 1.1
        mod_cy = PAGE_H - 2.9
        leaf_top_y = mod_cy - mod_h / 2 - 0.95

        total_mod_w = n * mod_w + (n - 1) * mod_gap
        start_mod_x = (PAGE_W - total_mod_w) / 2

        # 第1层:root(用源矩形改造)
        rect_src.text = root
        rect_src.move(root_cx - rect_src.x, root_cy - rect_src.y)
        _set_size(rect_src, root_w, root_h)
        _style_blackwhite(rect_src)
        root_shape = rect_src

        # 第2层 + 第3层
        mod_shapes = []
        leaf_shapes = []
        for i, (mod_name, leaves) in enumerate(modules):
            mcx = start_mod_x + i * (mod_w + mod_gap) + mod_w / 2
            # 模块框
            m = root_shape.copy(page)
            m.text = mod_name
            m.move(mcx - m.x, mod_cy - m.y)
            _set_size(m, mod_w, mod_h)
            _style_blackwhite(m)
            mod_shapes.append(m)
            # root -> 模块 连线
            c = vsdx.Connect.create(page, root_shape, m)
            _arrow(c)

            # 子功能框(纵向)
            for j, leaf_name in enumerate(leaves):
                lcy = leaf_top_y - j * (leaf_h + leaf_gap_y)
                lf = m.copy(page)
                lf.text = leaf_name
                lf.move(mcx - lf.x, lcy - lf.y)
                _set_size(lf, leaf_w, leaf_h)
                _style_blackwhite(lf)
                leaf_shapes.append(lf)
                # 连线:模块->第一个子功能;子功能->下一个子功能
                if j == 0:
                    c = vsdx.Connect.create(page, m, lf)
                    _arrow(c)
                else:
                    prev_lf = leaf_shapes[-2]
                    c = vsdx.Connect.create(page, prev_lf, lf)
                    _arrow(c)

        # 清理模板原始形状
        keep_ids = {root_shape.ID} | {s.ID for s in mod_shapes} | {s.ID for s in leaf_shapes}
        for s in orig_shapes:
            if s.ID not in keep_ids:
                try:
                    s.remove()
                except Exception:
                    pass

        tmp = out_vsdx + '.raw'
        vis.save_vsdx(tmp)
    fix_namespaces(tmp, out_vsdx)
    os.remove(tmp)


# ============ 两个图的内容 ============

FIG1 = {
    'root': '特征提取与上下文关联智能体',
    'modules': [
        ('多模态内容抽取', ['正文片段抽取', '图表片段抽取']),
        ('跨章节实体链接', ['语义相似匹配', '结构邻接分析']),
        ('条目聚合', ['片段组装', '冲突预检']),
        ('语义角色标注', ['角色识别', '角色赋值']),
        ('聚合粒度判定', ['粒度评分', '粒度选择']),
    ],
    'out_vsdx': '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_context.vsdx',
}

FIG2 = {
    'root': '数据一致性校验',
    'modules': [
        ('语法层校验', ['章节编号检查', 'ID唯一性检查']),
        ('语义层校验', ['参数值比对', '概念对齐']),
        ('逻辑层校验', ['约束抽取', '可满足性求解']),
        ('矛盾分类与定位', ['差异矛盾分类', '冲突位置定位']),
        ('校验报告生成', ['结果汇总', '修订建议']),
    ],
    'out_vsdx': '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_consistency.vsdx',
}

if __name__ == '__main__':
    for fig in [FIG1, FIG2]:
        print(f"=== {fig['root']} ===")
        build_fishbone(fig['root'], fig['modules'], fig['out_vsdx'])
        print(f"  vsdx: {fig['out_vsdx']} ({os.path.getsize(fig['out_vsdx'])} bytes)")
