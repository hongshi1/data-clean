#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成数据生成架构图并插入PPT

用Pillow绘制三层架构图 → 插入到PPT新slide
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# Part 1: 用Pillow生成架构图PNG
# ============================================================
from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 1800
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

# 字体
try:
    font_title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 48)
    font_big = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 32)
    font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    font_tiny = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
except Exception:
    font_title = font_big = font_small = font_tiny = ImageFont.load_default()

# 颜色
L1_BG, L1_BD = "#E3F2FD", "#1565C0"
L2_BG, L2_BD = "#FFF3E0", "#E65100"
L3_BG, L3_BD = "#E8F5E9", "#2E7D32"
ARROW = "#424242"
TEXT = "#212121"

def rrect(x1, y1, x2, y2, bg, bd, w=3, r=15):
    """圆角矩形"""
    d.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=bg, outline=bd, width=w)

def arrow(x1, y1, x2, y2, color=ARROW, w=3):
    """箭头"""
    d.line([x1, y1, x2, y2], fill=color, width=w)
    # 箭头头
    import math
    ang = math.atan2(y2-y1, x2-x1)
    alen = 12
    for da in [150, -150]:
        d.line([x2, y2, x2 - alen*math.cos(ang + math.radians(da)),
                y2 - alen*math.sin(ang + math.radians(da))], fill=color, width=w)

def text_center(cx, cy, s, font, fill=TEXT):
    """居中文字"""
    bb = d.textbbox((0, 0), s, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    d.text((cx - tw//2, cy - th//2), s, font=font, fill=fill)

# ---- 标题 ----
text_center(W//2, 50, "数据生成架构 (Data Generation Architecture)", font_title)

# ============================================================
# Layer 1: 文档理解层
# ============================================================
L1_Y = 120
d.line([80, L1_Y, W-80, L1_Y], fill=L1_BD, width=2)
d.text((90, L1_Y+5), "Layer 1: 文档理解层 (Document Understanding)", font=font_big, fill=L1_BD)

# 4个处理框
bw, bh = 500, 130
gap = 60
x0 = 100
y0 = L1_Y + 60

l1_boxes = [
    ("GJB SRS\n16份.doc", "源文档"),
    ("MinerU\n解析", "布局+表格+图片"),
    ("Visio XML\n锚点提取", "born-digital"),
    ("上下文图谱\n构建", "5619节点+23850边"),
]

for i, (title, sub) in enumerate(l1_boxes):
    x = x0 + i * (bw + gap)
    rrect(x, y0, x+bw, y0+bh, L1_BG, L1_BD)
    # 标题
    lines = title.split("\n")
    cy = y0 + 35
    for line in lines:
        text_center(x + bw//2, cy, line, font_small)
        cy += 30
    text_center(x + bw//2, y0 + bh - 20, sub, font_tiny, fill="#757575")
    # 箭头到下一个
    if i < 3:
        arrow(x + bw, y0 + bh//2, x + bw + gap, y0 + bh//2)

# Layer 1 汇总框
y_sum = y0 + bh + 40
rrect(x0, y_sum, x0 + 4*bw + 3*gap, y_sum + 50, "#E8EAF6", "#3F51B5", w=2, r=10)
text_center(W//2, y_sum + 25, "输出: content_list + anchors(373) + mermaid(373) + graph(5619节点)", font_small)

# 分隔线
sep1_y = y_sum + 70
d.line([80, sep1_y, W-80, sep1_y], fill="#BDBDBD", width=2)

# ============================================================
# Layer 2: 领域知识驱动数据合成层 (核心创新 - 更大)
# ============================================================
L2_Y = sep1_y + 20
d.text((90, L2_Y), "Layer 2: 领域知识驱动数据合成层 (Domain-Knowledge-Driven Synthesis)  ← 核心创新", font=font_big, fill=L2_BD)

# 3个主框(更大)
bw2, bh2 = 560, 160
y02 = L2_Y + 50

l2_main = [
    ("40项不一致\n注入引擎", "术语8/参数10/逻辑11\nGJB11/多模态12", "结构级变异"),
    ("变异算子\n(领域知识级)", "图拓扑操作/UML语义\n非字符替换", "数学形式化"),
    ("LLM QA生成\n(GLM-5)", "基于变异上下文\n生成自然语言QA", "CoT推理链"),
]

for i, (title, sub, tag) in enumerate(l2_main):
    x = x0 + i * (bw2 + gap)
    rrect(x, y02, x+bw2, y02+bh2, L2_BG, L2_BD, w=4, r=20)
    lines = title.split("\n")
    cy = y02 + 40
    for line in lines:
        text_center(x + bw2//2, cy, line, font_small)
        cy += 28
    # 子标签
    text_center(x + bw2//2, y02 + 105, sub, font_tiny, fill="#757575")
    # 底部标签
    d.rounded_rectangle([x+bw2//2-80, y02+bh2-32, x+bw2//2+80, y02+bh2-8],
                       radius=8, fill=L2_BD)
    text_center(x + bw2//2, y02+bh2-20, tag, font_tiny, fill="white")
    # 箭头
    if i < 2:
        arrow(x + bw2, y02 + bh2//2, x + bw2 + gap, y02 + bh2//2)

# 正例合成框
y_pos = y02 + bh2 + 40
pw = 400
rrect(x0 + bw2 + gap - pw//2, y_pos, x0 + bw2 + gap + pw//2, y_pos + 80,
      "#E8F5E9", "#2E7D32", w=3, r=15)
text_center(x0 + bw2 + gap, y_pos + 25, "正例合成", font_small)
text_center(x0 + bw2 + gap, y_pos + 55, "语义等效: 0.2s↔200ms", font_tiny, fill="#616161")

# 52项检测器框(重点 - 双线框)
y_qc = y_pos + 100
rrect(x0, y_qc, x0 + 4*bw2 + 3*gap, y_qc + 60, "#FFF8E1", "#FF6F00", w=5, r=12)
d.rounded_rectangle([x0+4, y_qc+4, x0 + 4*bw2 + 3*gap - 4, y_qc + 56],
                   radius=10, outline="#FF6F00", width=2)
text_center(W//2, y_qc + 30, "52项检测器自动标注 (52-Dimensional Auto-Annotation)  →  三阶段分布控制  →  质量验证",
            font_small, fill="#E65100")

# 分隔线
sep2_y = y_qc + 80
d.line([80, sep2_y, W-80, sep2_y], fill="#BDBDBD", width=2)

# ============================================================
# Layer 3: 管理与导出层
# ============================================================
L3_Y = sep2_y + 20
d.text((90, L3_Y), "Layer 3: 管理与导出层 (Management & Export - EasyDataset)", font=font_big, fill=L3_BD)

bw3, bh3 = 500, 100
y03 = L3_Y + 50

l3_boxes = [
    ("项目管理", "项目/Chunk/Question"),
    ("QA审核", "人工审核+AI优化"),
    ("标签树管理", "层级标签+平衡导出"),
    ("LLaMA Factory", "训练导出配置"),
]

for i, (title, sub) in enumerate(l3_boxes):
    x = x0 + i * (bw3 + gap)
    rrect(x, y03, x+bw3, y03+bh3, L3_BG, L3_BD)
    text_center(x + bw3//2, y03 + 35, title, font_small)
    text_center(x + bw3//2, y03 + 70, sub, font_tiny, fill="#757575")
    if i < 3:
        arrow(x + bw3, y03 + bh3//2, x + bw3 + gap, y03 + bh3//2)

# 底部闭环标注
y_close = y03 + bh3 + 40
d.rounded_rectangle([W//2 - 500, y_close, W//2 + 500, y_close + 40],
                   radius=20, outline="#616161", width=2, fill="#FAFAFA")
text_center(W//2, y_close + 20, "闭环: 评估结果 → 调整注入分布 → 下一轮合成", font_tiny, fill="#616161")

# 保存PNG
png_path = os.path.join(BASE, "tools", "output", "data_gen_architecture.png")
os.makedirs(os.path.dirname(png_path), exist_ok=True)
img.save(png_path, "PNG", dpi=(200, 200))
print(f"✅ 架构图已生成: {png_path} ({W}x{H})")

# ============================================================
# Part 2: 插入PPT
# ============================================================
from pptx import Presentation

src = os.path.join(BASE, "南开大学模板-3.pptx")
dst = os.path.join(BASE, "南开大学模板-4.pptx")

prs = Presentation(src)
print(f"原始PPT: {len(prs.slides)}页, 尺寸: {prs.slide_width}x{prs.slide_height}")

# 复制最后一页的layout
last_layout = prs.slides[-1].slide_layout

# 添加新slide
slide = prs.slides.add_slide(last_layout)

# 插入图片(全屏)
slide.shapes.add_picture(png_path, 0, 0,
                        width=prs.slide_width, height=prs.slide_height)

# 保存
prs.save(dst)
print(f"✅ 新PPT: {dst} ({len(prs.slides)}页)")

# 验证
prs2 = Presentation(dst)
print(f"验证: {len(prs2.slides)}页")
