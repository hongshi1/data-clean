"""
gen_drawio.py — 生成 draw.io 原生格式(.drawio)的 3 层黑白爪子图

draw.io 格式比 vsdx 简单,渲染质量好,可在 draw.io 里直接编辑。
输出:.drawio 文件 + 用 draw.io 导出 PNG
"""

from __future__ import annotations
import os

FIG1 = {
    'root': '特征提取与上下文关联智能体',
    'modules': [
        ('多模态内容抽取', ['正文片段抽取', '图表片段抽取']),
        ('跨章节实体关联', ['语义感知配对', '结构邻接分析']),
        ('条目聚合', ['片段组装', '冲突预检']),
        ('语义角色标注', ['角色识别', '角色赋值']),
        ('聚合力度判定', ['粒度评分', '多粒度选择']),
    ],
    'out': '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_context.drawio',
}

FIG2 = {
    'root': '数据一致性校验',
    'modules': [
        ('语法一致性校验', ['规则引擎推理', '结构模板比对']),
        ('语义一致性校验', ['NLI蕴含判定', '跨模态语义对齐', '实体链接对齐']),
        ('逻辑一致性校验', ['SMT约束求解', '专家知识比对']),
    ],
    'out': '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_consistency.drawio',
}

# 样式(黑白)
STYLE_ROOT = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;strokeWidth=2;fontColor=#000000;fontSize=12;fontStyle=1;'
STYLE_MOD = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;strokeWidth=1.5;fontColor=#000000;fontSize=10;fontStyle=1;'
STYLE_LEAF = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;strokeWidth=1;fontColor=#000000;fontSize=9;'
STYLE_EDGE = 'endArrow=classic;html=1;strokeColor=#000000;strokeWidth=1;'


def build_drawio(root: str, modules: list) -> str:
    """生成 .drawio XML"""
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cid = 2

    # 布局参数
    n = len(modules)
    root_w, root_h = 260, 60
    mod_w, mod_h = 170, 50
    leaf_w, leaf_h = 150, 40
    mod_gap = 30
    leaf_gap_y = 15

    page_w = n * mod_w + (n - 1) * mod_gap
    root_cx = page_w / 2
    root_x = root_cx - root_w / 2
    root_y = 20

    mod_y = 140
    start_mod_x = 0
    leaf_y_start = mod_y + mod_h + 50

    # 父框
    root_id = cid
    cells.append(
        f'<mxCell id="{cid}" value="{root}" style="{STYLE_ROOT}" vertex="1" parent="1">'
        f'<mxGeometry x="{root_x}" y="{root_y}" width="{root_w}" height="{root_h}" as="geometry"/></mxCell>'
    )
    cid += 1

    for i, (mod_name, leaves) in enumerate(modules):
        mcx = start_mod_x + i * (mod_w + mod_gap) + mod_w / 2
        mx = mcx - mod_w / 2
        # 模块框
        mod_id = cid
        cells.append(
            f'<mxCell id="{cid}" value="{mod_name}" style="{STYLE_MOD}" vertex="1" parent="1">'
            f'<mxGeometry x="{mx}" y="{mod_y}" width="{mod_w}" height="{mod_h}" as="geometry"/></mxCell>'
        )
        cid += 1
        # root -> 模块 连线
        cells.append(
            f'<mxCell id="{cid}" style="{STYLE_EDGE}" edge="1" parent="1" source="{root_id}" target="{mod_id}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
        cid += 1
        # 子功能
        prev_leaf_id = None
        for j, leaf_name in enumerate(leaves):
            ly = leaf_y_start + j * (leaf_h + leaf_gap_y)
            lx = mcx - leaf_w / 2
            leaf_id = cid
            cells.append(
                f'<mxCell id="{cid}" value="{leaf_name}" style="{STYLE_LEAF}" vertex="1" parent="1">'
                f'<mxGeometry x="{lx}" y="{ly}" width="{leaf_w}" height="{leaf_h}" as="geometry"/></mxCell>'
            )
            cid += 1
            # 连线:模块->第一个子功能;子功能->下一个
            src = mod_id if j == 0 else prev_leaf_id
            cells.append(
                f'<mxCell id="{cid}" style="{STYLE_EDGE}" edge="1" parent="1" source="{src}" target="{leaf_id}">'
                f'<mxGeometry relative="1" as="geometry"/></mxCell>'
            )
            cid += 1
            prev_leaf_id = leaf_id

    page_h = leaf_y_start + 2 * (leaf_h + leaf_gap_y) + 20
    xml = (f'<mxfile><diagram name="Page-1">'
           f'<mxGraphModel dx="{int(page_w)}" dy="{int(page_h)}" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(page_w+40)}" pageHeight="{int(page_h+40)}" math="0" shadow="0">'
           f'<root>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>')
    return xml


def main():
    for fig in [FIG1, FIG2]:
        xml = build_drawio(fig['root'], fig['modules'])
        with open(fig['out'], 'w', encoding='utf-8') as f:
            f.write(xml)
        print(f"  drawio: {fig['out']} ({os.path.getsize(fig['out'])} bytes)")


if __name__ == '__main__':
    main()
