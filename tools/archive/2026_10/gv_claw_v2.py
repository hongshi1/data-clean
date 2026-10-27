#!/usr/bin/env python3
"""
gv_claw_v2.py — 分层爪子图(中心→3部件→每部件2子节点) graphviz 版

结构:
  中心智能体
  ├── 部件1
  │   ├── 子节点1a
  │   └── 子节点1b
  ├── 部件2
  │   ├── 子节点2a
  │   └── 子节点2b
  └── 部件3
      ├── 子节点3a
      └── 子节点3b

用法: python gv_claw_v2.py
"""
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def dot_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def gen_layered_claw(title, parts_and_children, out_stem):
    """
    parts_and_children: List[(part_name, [child1, child2])]
    """
    lines = [
        "digraph claw {",
        '  graph [rankdir=TB, fontname="Heiti SC", dpi=150, bgcolor="white", nodesep=0.35, ranksep=0.6];',
        '  node [shape=box, fontname="Heiti SC", style=filled];',
        '  edge [arrowhead=none];',
        f'  center [label="{dot_escape(title)}", fillcolor=lightyellow, fontsize=14, width=2.4, height=0.7];',
    ]
    for i, (part, children) in enumerate(parts_and_children):
        pid = f"p{i}"
        lines.append(f'  {pid} [label="{dot_escape(part)}", fillcolor=lightcyan, fontsize=12, width=1.8, height=0.6];')
        lines.append(f"  center -> {pid};")
        for j, child in enumerate(children):
            cid = f"{pid}_c{j}"
            lines.append(f'  {cid} [label="{dot_escape(child)}", fillcolor=white, fontsize=10, width=1.6, height=0.5];')
            lines.append(f"  {pid} -> {cid};")
    lines.append("}")

    dot_path = out_stem + ".dot"
    png_path = out_stem + ".png"
    with open(dot_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    r = subprocess.run(["dot", "-Tpng", dot_path, "-o", png_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ {r.stderr[-300:]}")
        return False
    print(f"[✓] {png_path}")
    return True


def main():
    # 图01: 特征提取与上下文关联智能体
    gen_layered_claw(
        "特征提取与上下文关联智能体",
        [
            ("多模态特征提取", ["语义编码与特征表示", "跨模态特征对齐"]),
            ("跨源实体关联", ["语义相似度计算", "结构邻接分析"]),
            ("条目汇聚管理", ["条目构建与组装", "去重与冲突预检"]),
        ],
        os.path.join(OUT_DIR, "01_特征提取与上下文关联智能体_部件组成图"),
    )

    # 图02: 数据一致性校验智能体
    gen_layered_claw(
        "数据一致性校验智能体",
        [
            ("语法层校验", ["规则引擎推理", "结构模板比对"]),
            ("语义层校验", ["语义对齐与关联比对", "蕴含矛盾判定"]),
            ("逻辑层校验", ["约束求解验证", "专家知识比对"]),
        ],
        os.path.join(OUT_DIR, "02_数据一致性校验智能体_部件组成图"),
    )


if __name__ == "__main__":
    main()
