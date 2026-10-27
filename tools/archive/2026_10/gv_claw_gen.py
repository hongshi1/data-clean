#!/usr/bin/env python3
"""
gv_claw_gen.py — 用 graphviz(dot CLI) 画爪子图(部件组成图) PNG

设计: 中心智能体节点 + 3 个部件环绕 + 连线, 黑体(Heiti SC), 清晰渲染
输出: output/0X_XXX_部件组成图.png

用法: python gv_claw_gen.py
"""
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def dot_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def gen_claw(title, parts, out_stem):
    lines = [
        "graph claw {",
        '  graph [overlap=false, splines=true, fontname="Heiti SC", size="6,4", dpi=150, bgcolor="white"];',
        '  node [shape=box, fontname="Heiti SC"];',
        f'  center [label="{dot_escape(title)}", style=filled, fillcolor=lightyellow, fontsize=13, width=2.2, height=0.8];',
    ]
    for i, part in enumerate(parts):
        lines.append(f'  p{i} [label="{dot_escape(part)}", fontsize=11, width=1.9, height=0.7];')
        lines.append(f"  center -- p{i};")
    lines.append("}")
    dot = "\n".join(lines)

    dot_path = out_stem + ".dot"
    png_path = out_stem + ".png"
    with open(dot_path, "w", encoding="utf-8") as f:
        f.write(dot)
    r = subprocess.run(["dot", "-Tpng", dot_path, "-o", png_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ 失败: {r.stderr[-300:]}")
        return False
    print(f"[✓] {png_path}")
    return True


def main():
    builds = [
        ("特征提取与上下文关联智能体",
         ["多模态特征提取", "跨源实体关联", "条目汇聚管理"],
         os.path.join(OUT_DIR, "01_特征提取与上下文关联智能体_部件组成图")),
        ("数据一致性校验智能体",
         ["语法层校验", "语义层校验", "逻辑层校验"],
         os.path.join(OUT_DIR, "02_数据一致性校验智能体_部件组成图")),
        ("设计经验结构化建模智能体",
         ["经验知识抽取", "知识形式化", "知识图谱构建"],
         os.path.join(OUT_DIR, "03_设计经验结构化建模智能体_部件组成图")),
        ("数据合成与增强智能体",
         ["数据合成", "样本增强", "类别均衡"],
         os.path.join(OUT_DIR, "04_数据合成与增强智能体_部件组成图")),
    ]
    for title, parts, out in builds:
        gen_claw(title, parts, out)


if __name__ == "__main__":
    main()
