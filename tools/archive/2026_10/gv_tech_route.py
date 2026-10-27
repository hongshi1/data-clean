#!/usr/bin/env python3
"""
gv_tech_route.py — 3.2.2.3.3 跨模态统一表征与上下文关联技术路线图

基于文档原文描述:
  多模态特征提取(文本/图像/时序) -> 共享语义投影(统一语义空间)
  -> 上下文关联建模(时间序列建模 + 事件锚点对齐)
  -> 领域先验规则注入 -> 自动化一致性检测

输出: output/05_跨模态统一表征与上下文关联技术路线图.png
"""
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def dot_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    out_stem = os.path.join(OUT_DIR, "05_跨模态统一表征与上下文关联技术路线图")
    dot = r'''
digraph route {
  graph [rankdir=LR, fontname="Heiti SC", dpi=150, bgcolor="white", nodesep=0.5, ranksep=0.7];
  node [shape=box, style=filled, fontname="Heiti SC", fontsize=11];

  subgraph cluster_in {
    label="多模态数据输入"; fontname="Heiti SC"; fontsize=12;
    style=dashed; color=gray;
    t [label="文本数据\n(设计文档/规范)", fillcolor=lightyellow];
    i [label="图像数据\n(图纸/状态标识)", fillcolor=lightyellow];
    s [label="时序数据\n(运行参数)", fillcolor=lightyellow];
  }

  fe [label="多模态特征提取\n(语言模型/视觉网络/时序建模)", fillcolor=lightcyan];
  proj [label="共享语义投影\n(映射到统一语义空间)", fillcolor=lightcyan];
  ctx [label="上下文关联建模\n(时间序列建模/事件锚点对齐)", fillcolor=lightgreen];
  rule [label="领域先验规则注入\n(规则约束/语义关系映射)", fillcolor=lightgreen];
  check [label="自动化一致性检测\n(跨模态比对/事实核查)", fillcolor=orange];

  t -> fe; i -> fe; s -> fe;
  fe -> proj -> ctx -> rule -> check;
}
'''
    dot_path = out_stem + ".dot"
    with open(dot_path, "w", encoding="utf-8") as f:
        f.write(dot)
    r = subprocess.run(["dot", "-Tpng", dot_path, "-o", out_stem + ".png"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"✗ 失败: {r.stderr[-300:]}")
        return
    print(f"[✓] {out_stem}.png")


if __name__ == "__main__":
    main()
