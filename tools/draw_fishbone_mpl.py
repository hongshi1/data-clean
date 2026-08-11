"""
draw_fishbone_mpl.py — matplotlib 画 GJB 部件组成图(3层爪子图)

层级(参考数据集真实组成图):
  第1层:智能体(1个,深蓝填充白字)
  第2层:能力模块(5个,中蓝填充)
  第3层:子功能(每模块2个,浅蓝填充)
共 1+5+10 = 16 个框,3 层连线带箭头。

字体:Heiti SC(黑体-简),父12pt粗体 / 子10pt / 孙9pt
"""

from __future__ import annotations
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams['font.family'] = 'Heiti SC'
plt.rcParams['axes.unicode_minus'] = False

PAGE_W, PAGE_H = 11.69, 8.27  # 横向 A4


def draw_fishbone(root: str, modules: list[tuple[str, list[str]]], out_png: str) -> None:
    """
    root: 顶层名称
    modules: [(模块名, [子功能1, 子功能2]), ...]
    """
    n = len(modules)
    fig, ax = plt.subplots(figsize=(PAGE_W, PAGE_H))
    ax.set_xlim(0, PAGE_W)
    ax.set_ylim(0, PAGE_H)
    ax.set_aspect('equal')
    ax.axis('off')

    # 布局参数
    root_w, root_h = 4.8, 0.85
    mod_w, mod_h = 2.05, 0.75
    leaf_w, leaf_h = 1.85, 0.6
    mod_gap = 0.22
    leaf_gap_y = 0.18  # 孙框之间纵向间隔

    root_cx = PAGE_W / 2
    root_cy = PAGE_H - 1.1
    mod_cy = PAGE_H - 2.9
    # 孙框从 mod_cy 往下排
    leaf_top_y = mod_cy - mod_h / 2 - 0.9

    total_mod_w = n * mod_w + (n - 1) * mod_gap
    start_mod_x = (PAGE_W - total_mod_w) / 2  # 第一个模块左边

    # 颜色
    C_ROOT_FACE = '#2F5597'
    C_ROOT_EDGE = '#1F3864'
    C_MOD_FACE = '#8EAADB'
    C_MOD_EDGE = '#2F5597'
    C_LEAF_FACE = '#D9E2F3'
    C_LEAF_EDGE = '#8EAADB'
    C_LINE = '#4472C4'
    C_TEXT_DARK = '#1F3864'

    def add_box(cx, cy, w, h, text, face, edge, fontsize, textcolor='white', bold=False):
        box = FancyBboxPatch(
            (cx - w / 2, cy - h / 2), w, h,
            boxstyle='round,pad=0.04,rounding_size=0.12',
            facecolor=face, edgecolor=edge, linewidth=1.5
        )
        ax.add_patch(box)
        ax.text(cx, cy, text, ha='center', va='center',
                fontsize=fontsize, color=textcolor,
                fontweight='bold' if bold else 'normal')

    def add_arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle='-|>', mutation_scale=12,
            color=C_LINE, linewidth=1.2,
            connectionstyle='arc3,rad=0'
        ))

    # 第1层:root
    add_box(root_cx, root_cy, root_w, root_h, root,
            C_ROOT_FACE, C_ROOT_EDGE, 12, 'white', bold=True)

    mod_centers = []
    for i, (mod_name, leaves) in enumerate(modules):
        mcx = start_mod_x + i * (mod_w + mod_gap) + mod_w / 2
        mod_centers.append(mcx)

        # 第2层:模块
        add_box(mcx, mod_cy, mod_w, mod_h, mod_name,
                C_MOD_FACE, C_MOD_EDGE, 10, C_TEXT_DARK, bold=True)
        # root -> 模块 连线
        add_arrow(root_cx, root_cy - root_h / 2,
                  mcx, mod_cy + mod_h / 2)

        # 第3层:子功能(纵向排列)
        n_leaf = len(leaves)
        for j, leaf in enumerate(leaves):
            lcy = leaf_top_y - j * (leaf_h + leaf_gap_y)
            add_box(mcx, lcy, leaf_w, leaf_h, leaf,
                    C_LEAF_FACE, C_LEAF_EDGE, 9, C_TEXT_DARK)
            # 连线:模块 -> 第一个子功能;子功能之间也连
            if j == 0:
                add_arrow(mcx, mod_cy - mod_h / 2,
                          mcx, lcy + leaf_h / 2)
            else:
                prev_y = leaf_top_y - (j - 1) * (leaf_h + leaf_gap_y)
                add_arrow(mcx, prev_y - leaf_h / 2,
                          mcx, lcy + leaf_h / 2)

    plt.tight_layout(pad=0.3)
    plt.savefig(out_png, dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"  png: {out_png}")


FIG1 = {
    'root': '特征提取与上下文关联智能体',
    'modules': [
        ('多模态内容抽取', ['正文片段抽取', '图表片段抽取']),
        ('跨章节实体链接', ['语义相似匹配', '结构邻接分析']),
        ('条目聚合', ['片段组装', '冲突预检']),
        ('语义角色标注', ['角色识别', '角色赋值']),
        ('聚合粒度判定', ['粒度评分', '粒度选择']),
    ],
    'out': '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_context_mpl.png',
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
    'out': '/Users/gexuancheng/Desktop/research2/data_clean/tools/fig_consistency_mpl.png',
}

if __name__ == '__main__':
    for fig in [FIG1, FIG2]:
        print(f"=== {fig['root']} ===")
        draw_fishbone(fig['root'], fig['modules'], fig['out'])
