#!/usr/bin/env python3
"""用matplotlib画3个架构图"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.font_manager as fm
import numpy as np

# 中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'PingFang SC', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 颜色
C_TEAL = '#2A9D8F'
C_GOLD = '#E9C46A'
C_ORANGE = '#F4A261'
C_CORAL = '#E76F51'
C_PURPLE = '#7C3AED'
C_DARK = '#264653'
C_GRAY = '#6B7280'
C_WHITE = '#FFFFFF'

BG = {
    'teal': '#E8F5F3', 'gold': '#FFFBF0', 'orange': '#FFF8F0',
    'coral': '#FDF2F0', 'purple': '#F3F0FD', 'dark': '#E8EDF2'
}


def draw_box(ax, x, y, w, h, text, color, bg_color=None, fontsize=9, fontweight='normal'):
    """画圆角矩形+文字"""
    if bg_color is None:
        bg_color = color + '20'
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", 
                          facecolor=bg_color, edgecolor=color, linewidth=1.5)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=fontweight, color=C_DARK, wrap=True)


def draw_layer(ax, y, title, boxes, accent_color, bg_color):
    """画一层"""
    # 背景条
    ax.fill_between([0.02, 0.98], y, y + 0.13, color=bg_color, alpha=0.5)
    # 标题
    ax.text(0.05, y + 0.065, title, fontsize=10, fontweight='bold', color=accent_color, va='center')
    # 组件框
    n = len(boxes)
    box_w = 0.85 / n
    for i, (text, fs) in enumerate(boxes):
        bx = 0.12 + i * (box_w + 0.02)
        draw_box(ax, bx, y + 0.02, box_w, 0.09, text, accent_color, fontsize=fs)


def draw_arrow(ax, x1, y1, x2, y2, color=C_GRAY):
    """画箭头"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))


# ===== Figure 1: SRS技术路线架构图 =====
def fig1_srs_architecture():
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    # 标题
    ax.text(0.5, 0.97, 'SRS不一致检测技术路线架构', fontsize=18, fontweight='bold',
            ha='center', color=C_DARK)
    
    # L5
    draw_layer(ax, 0.80, 'L5 评测与应用层', [
        ('P/R/F1\n报告', 8), ('多LLM\n标注', 8), ('人类\n基线', 8), ('论文\n产出', 8)
    ], C_PURPLE, BG['purple'])
    
    # L4
    draw_layer(ax, 0.64, 'L4 三层不一致检测', [
        ('语法层 S1-S7\nGJB规则驱动', 8), ('语义层 7种方法\nBGE/GCN/注意力', 8), ('逻辑层 Z3+LLM\nSolver验证unsat', 8)
    ], C_CORAL, BG['coral'])
    
    # L3
    draw_layer(ax, 0.48, 'L3 上下文关联层', [
        ('双图融合4通道\nrecall=0.809', 8), ('ID-Graph\n2181节点', 8), ('语义图\n508实体', 8), ('VLM分析\n163张流程图', 8)
    ], C_ORANGE, BG['orange'])
    
    # L2
    draw_layer(ax, 0.32, 'L2 数据资产工厂', [
        ('Pair Dataset\n366个配对', 8), ('切片 5231条\n16份文档', 8), ('GJB规则\n120条', 8), ('词典\n11参数', 8)
    ], C_GOLD, BG['gold'])
    
    # L1
    draw_layer(ax, 0.16, 'L1 数据入口层', [
        ('16份\nGJB SRS', 8), ('MinerU\n解析', 8), ('textutil\n双源', 8), ('VLM分类\n379张', 8)
    ], C_TEAL, BG['teal'])
    
    # 底座
    ax.fill_between([0.02, 0.98], 0.01, 0.10, color=BG['dark'], alpha=0.6)
    ax.text(0.05, 0.055, '底座', fontsize=10, fontweight='bold', color=C_DARK, va='center')
    base_items = ['LightRAG\n11872实体', 'BGE-zh\n512维', 'Z3\nSolver', 'kimi-k2.6\nmoonshot', 'claude\nwanqing', 'CoVe\n验证']
    for i, item in enumerate(base_items):
        draw_box(ax, 0.12 + i * 0.14, 0.02, 0.12, 0.07, item, C_DARK, fontsize=7)
    
    # 箭头
    for y in [0.14, 0.30, 0.46, 0.62, 0.78]:
        draw_arrow(ax, 0.5, y, 0.5, y + 0.02, C_GRAY)
    draw_arrow(ax, 0.5, 0.10, 0.5, 0.16, C_GRAY)
    
    plt.tight_layout()
    plt.savefig('figures/fig_srs_architecture.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print('✓ fig_srs_architecture.png')


# ===== Figure 2: 通用五场景应用架构图 =====
def fig2_unified_platform():
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    ax.text(0.5, 0.97, '通用五场景应用架构', fontsize=18, fontweight='bold', ha='center', color=C_DARK)
    
    # 5个场景
    scenarios = [
        ('技术文档\n一致性校验', 'SRS/标准/规范', C_TEAL),
        ('多模态文档\n理解与QA', '图+表+文', C_GOLD),
        ('需求工程\n辅助生成', '生成/检测/追溯', C_ORANGE),
        ('知识图谱\n构建与推理', '实体/关系/推理', C_CORAL),
        ('合规性\n检测', 'GJB/IEEE/国标', C_PURPLE),
    ]
    for i, (title, sub, color) in enumerate(scenarios):
        x = 0.05 + i * 0.19
        draw_box(ax, x, 0.78, 0.16, 0.12, f'{title}\n{sub}', color, fontsize=8, fontweight='bold')
    
    # 统一技术中台
    ax.fill_between([0.03, 0.97], 0.30, 0.70, color='#F8FAFC', alpha=0.8)
    ax.text(0.5, 0.66, '统一技术中台 (Unified Platform)', fontsize=13, fontweight='bold', ha='center', color=C_DARK)
    
    modules = [
        ('上下文关联', '双图融合4通道\n跨位置聚合', '#2563EB'),
        ('三层检测', '语法/语义/逻辑\nZ3 Solver验证', '#059669'),
        ('评测集合成', '四段式流水线\n40种注入方法', '#D97706'),
        ('检测器评测', 'P/R/F1分层报告\n多LLM标注', '#E11D48'),
    ]
    for i, (title, sub, color) in enumerate(modules):
        x = 0.08 + i * 0.22
        draw_box(ax, x, 0.40, 0.18, 0.18, f'{title}\n\n{sub}', color, fontsize=8, fontweight='bold')
    
    # 底座
    ax.fill_between([0.03, 0.97], 0.08, 0.22, color=C_DARK, alpha=0.9)
    ax.text(0.5, 0.15, '底座: RAG | VLM | Z3 | LLM(kimi+claude) | BGE向量 | LightRAG', 
            fontsize=11, ha='center', va='center', color='white', fontweight='bold')
    
    # 箭头
    for i in range(5):
        x = 0.05 + i * 0.19 + 0.08
        draw_arrow(ax, x, 0.78, x, 0.70, C_GRAY)
    draw_arrow(ax, 0.5, 0.30, 0.5, 0.22, C_GRAY)
    
    plt.tight_layout()
    plt.savefig('figures/fig_unified_platform.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print('✓ fig_unified_platform.png')


# ===== Figure 3: 数据集合成流程图 =====
def fig3_synthesis_pipeline():
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    ax.text(0.5, 0.97, '评测集合成流程（四段式流水线）', fontsize=18, fontweight='bold', ha='center', color=C_DARK)
    
    # 4个阶段
    stages = [
        {
            'x': 0.02, 'color': C_TEAL, 'bg': BG['teal'],
            'title': '阶段1\n检测对象提取',
            'sub': '确定性, 可复现',
            'items': ['Pair Dataset 366个', 'VLM用例图 136条', 'VLM流程图 163张', 'chunks 5231条'],
            'output': '→ 5类检测对象\n1128个'
        },
        {
            'x': 0.27, 'color': C_GOLD, 'bg': BG['gold'],
            'title': '阶段2\n40种规则注入',
            'sub': 'seed=42, Z3 gate',
            'items': ['术语 8种', '参数 10种', '逻辑 11种', 'GJB 11种'],
            'output': '→ 注入结果\n200条'
        },
        {
            'x': 0.52, 'color': C_ORANGE, 'bg': BG['orange'],
            'title': '阶段3\nLLM改写',
            'sub': 'kimi-k2.6 moonshot',
            'items': ['thinking=disabled', 'temperature=0.6', 'response=json', '只改语言不改结论'],
            'output': '→ 自然语言QA\n200条'
        },
        {
            'x': 0.77, 'color': C_CORAL, 'bg': BG['coral'],
            'title': '阶段4\n分层验证',
            'sub': 'Gold + Silver',
            'items': ['Gold: Z3 Solver验证unsat', 'Gold: 规则确定性验证', 'Silver: kimi+claude双LLM', 'Silver: 不同endpoint'],
            'output': '→ 评测集\n400条'
        },
    ]
    
    for s in stages:
        # 背景框
        ax.fill_between([s['x'], s['x'] + 0.22], 0.25, 0.88, color=s['bg'], alpha=0.5)
        # 标题
        ax.text(s['x'] + 0.11, 0.83, s['title'], fontsize=11, fontweight='bold', ha='center', color=s['color'])
        ax.text(s['x'] + 0.11, 0.78, s['sub'], fontsize=8, ha='center', color=C_GRAY, style='italic')
        # 组件
        for j, item in enumerate(s['items']):
            draw_box(ax, s['x'] + 0.01, 0.68 - j * 0.10, 0.20, 0.08, item, s['color'], fontsize=7)
        # 输出
        draw_box(ax, s['x'] + 0.03, 0.27, 0.16, 0.06, s['output'], s['color'], fontsize=7, fontweight='bold')
    
    # 流程箭头
    for i in range(3):
        x1 = 0.24 + i * 0.25
        draw_arrow(ax, x1, 0.55, x1 + 0.03, 0.55, C_DARK)
    
    # 底部验证结果
    ax.fill_between([0.02, 0.98], 0.05, 0.18, color=BG['purple'], alpha=0.5)
    ax.text(0.5, 0.14, '多LLM独立标注验证', fontsize=10, fontweight='bold', ha='center', color=C_PURPLE)
    ax.text(0.5, 0.09, 'kimi 79.9%  |  claude 65.8%  |  glm 78.9%  |  Cohen κ=0.57-0.78  |  三人一致率 67.3%', 
            fontsize=9, ha='center', color=C_DARK)
    
    plt.tight_layout()
    plt.savefig('figures/fig_synthesis_pipeline.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print('✓ fig_synthesis_pipeline.png')


if __name__ == '__main__':
    import os
    os.makedirs('figures', exist_ok=True)
    fig1_srs_architecture()
    fig2_unified_platform()
    fig3_synthesis_pipeline()
    print('\n所有图片生成完成！')
