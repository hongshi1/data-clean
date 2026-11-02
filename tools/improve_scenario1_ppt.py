"""Improve scenario-1 PPT: inject core tech & achievement chain into existing slides.

Strategy: modify specific text shapes on slides 3-9 to add missing core
technology concepts (registry, EGT, cascade escalation, Pareto, per-claim
fusion, open world semantics, id/enum/trace join, BGE, held-out, violation
detection rate). Also enrich slide 7 (VIO-01 case) with full evidence chain.
"""
from __future__ import annotations

import os
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/srs_project/paper/scenario1_aligned_to_scene3_4.pptx"


def walk(shapes):
    for s in shapes:
        yield s
        if s.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(s.shapes)


def find_and_replace(slide, old_text, new_text):
    for sh in walk(slide.shapes):
        t = getattr(sh, 'text', '').strip()
        if t == old_text:
            set_text(sh, new_text)
            return True
    return False


def set_text(shape, new_text):
    if not shape.has_text_frame:
        return
    frame = shape.text_frame
    paragraphs = frame.paragraphs
    if paragraphs and paragraphs[0].runs:
        paragraphs[0].runs[0].text = new_text
        for run in paragraphs[0].runs[1:]:
            run.text = ""
        for p in paragraphs[1:]:
            for run in p.runs:
                run.text = ""


def add_textbox(slide, left, top, width, height, text, size=14, bold=True, color=(230, 240, 255)):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    box.text_frame.word_wrap = True
    run = box.text_frame.paragraphs[0].add_run()
    run.text = text
    run.font.name = "Microsoft YaHei"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(*color)
    return box


def main():
    prs = Presentation(str(OUT))
    slides = list(prs.slides)

    # === Slide 3: Feature extraction → add "注册表" concept ===
    s3 = slides[2]
    find_and_replace(s3, "证据对象组织", "证据注册表构建")
    find_and_replace(s3, "把分散内容归入同一对象", "构建(主体,值,位置)注册表")
    find_and_replace(s3, "正文关联", "ID注册表")
    find_and_replace(s3, "关联正文描述与对应表格行", "ID→主体绑定→跨位置冲突检测")
    find_and_replace(s3, "图片登记", "枚举值域")
    find_and_replace(s3, "登记图片节点和邻接关系", "主体→闭集成员→集合级比对")
    find_and_replace(s3, "证据归档", "追溯映射")
    find_and_replace(s3, "记录实体类型与出现位置", "正向/逆向join→映射矛盾检测")
    # bottom output
    find_and_replace(s3, "主体 + 值/约束 + 语义角色 + 原始位置 + 置信度",
                     "注册表 = 主体 + 值 + 位置 + 语义角色 → 支持跨位置join")

    # === Slide 4: Context linking → add BGE and 聚合 ===
    s4 = slides[3]
    find_and_replace(s4, "匹配关联锚点", "BGE嵌入 + 词法锚点")
    find_and_replace(s4, "命中ID、章节、表格行和图片节点",
                     "BGE余弦相似度 + ID精确匹配 → 候选证据集")
    find_and_replace(s4, "ID匹配 + 章节邻接 + 表格关系 + 语义相似度",
                     "ID精确匹配 + BGE语义相似 + 章节邻接 + 表格关系")

    # === Slide 5: Consistency framework → add cascade & open world ===
    s5 = slides[4]
    find_and_replace(s5, "三态输入", "残差派发：已决claim不下沉")
    find_and_replace(s5, "正文、表格、图片、追溯与合格性表",
                     "L0/L1已判定的claim直接输出\n无法形式化的进入L2残差")
    find_and_replace(s5, "术语、参数、逻辑和合规声明",
                     "support/refute直接判定\nper-claim融合：refute>support>NIE")
    find_and_replace(s5, "三态判定", "三态判定\n开放世界：NIE≠矛盾")
    find_and_replace(s5, "证据定位", "证据定位\n块/行/span级")

    # === Slide 6: Tech route → add EGT, cascade, Pareto ===
    s6 = slides[5]
    find_and_replace(s6, "复核规则未决的语义claim",
                     "EGT三态构造性合成训练\nS←改写|R←跨行污染|N←删除")
    find_and_replace(s6, "refute候选实例级复核",
                     "级联升级：L2 refute→L3 LLM\n18%成本达最优refute F1")
    find_and_replace(s6, "基于领域知识、GJB规范等专家知识，对数值、单位、范围等约束进行比较与判定",
                     "级联经济学：B3(0调用)→级联(15次)→B4(83次)\nPareto点：18%成本→refute F1=0.857")

    # === Slide 7: VIO-01 case → enrich with full chain ===
    s7 = slides[6]
    find_and_replace(s7, "输入问答", "VIO-01证据链")
    find_and_replace(s7, "实体抽取", "ID注册表join")
    find_and_replace(s7, "上下文对齐", "refute + TERM-07")
    # add detail text
    add_textbox(s7, 2.0, 2.5, 8.0, 0.5,
                "表39: 连接池配置 → PZXQ-GN-LJCGL-LJCPZ", 14, True, (255, 200, 200))
    add_textbox(s7, 2.0, 3.0, 8.0, 0.5,
                "章节标题: 连接池配置 → PZXQ-GN-LJCGL-LJCCSH", 14, True, (255, 200, 200))
    add_textbox(s7, 2.0, 3.5, 8.0, 0.5,
                "章节标题: 连接池初始化 → PZXQ-GN-LJCGL-LJCCSH (同一ID!)", 14, True, (255, 160, 160))
    add_textbox(s7, 2.0, 4.2, 8.0, 0.5,
                "ID注册表: LJCCSH → {连接池配置, 连接池初始化}", 14, True, (200, 230, 255))
    add_textbox(s7, 2.0, 4.7, 8.0, 0.5,
                "→ 同一ID绑定两个主体 → TERM-07 → refute", 16, True, (255, 255, 200))
    add_textbox(s7, 2.0, 5.4, 8.0, 0.4,
                "检出通道: id_join_L1 | 定位: b220 + b225 | 违例检出: 5/5", 13, False, (180, 220, 255))

    # === Slide 8: Three violations → enrich with detection channel ===
    s8 = slides[7]
    # Replace the two main text boxes
    for sh in walk(s8.shapes):
        t = getattr(sh, 'text', '').strip()
        if 'VIO-06' in t:
            set_text(sh, "VIO-06 枚举冲突 4/4\n正文5项 vs 表3仅4项\n检出: enum_join_L1")
        elif 'VIO-10' in t and 'VIO-17' in t:
            set_text(sh, "VIO-10 追溯断裂 3/3\n表81正向 vs 表82逆向\n检出: trace_L1\n\n"
                        "VIO-17 覆盖缺口 1/1\n表80仅3.2.1-3.2.6\n检出: coverage_L1\n\n"
                        "真实违例集: 16/17 = 94.1%\nidentifier 5/5 | enum 4/4 | trace 3/3")

    # === Slide 9: Results → add held-out, Pareto, ablation ===
    s9 = slides[8]
    find_and_replace(s9, "91QA评测 | 17真实违例 | 06号跨文档",
                     "91QA(silver) | 17真实违例 | held-out(46条) | 06号跨文档")
    find_and_replace(s9, "CascadeVerify三态判定结果",
                     "评测矩阵: B0-B5基线 + 10消融 + bootstrap + 变异注入")
    find_and_replace(s9, "主体+规则ID+证据位置",
                     "16/17=94.1% | refute P=1.0\nAcc 0.9121 | Macro-F1 0.7212")
    find_and_replace(s9, "成本+质量+召回",
                     "级联: 15/83=18% LLM调用\nrefute F1=0.857 | 8ms确定性")
    find_and_replace(s9, "06号det 0.262/cascade 0.605",
                     "det 0.262 | cascade 0.605\n正则文法不迁移→语义匹配升级")
    # Add held-out and ablation numbers
    find_and_replace(s9, "Acc 0.9121", "91QA: 0.9121")
    find_and_replace(s9, "Macro-F1", "held-out: 0.8286")
    find_and_replace(s9, "refute F1", "消融: 融合-0.152")
    find_and_replace(s9, "LLM调用15/83", "Pareto: 18%→0.857")
    find_and_replace(s9, "确定性8ms", "fast: 8ms/条")
    find_and_replace(s9, "级联refute F1", "标准: 120ms/条")
    find_and_replace(s9, "heldout 0.8286", "refute P=1.0")

    # Save
    prs.save(str(OUT))
    print(f"saved: {OUT}")

    # Verify
    result = Presentation(str(OUT))
    all_text = ' '.join(getattr(sh, 'text', '') for s in result.slides for sh in walk(s.shapes))
    tech = ['注册表', 'EGT', 'Pareto', '残差', '开放世界', 'id_join', 'enum_join',
            'BGE', 'held-out', '94.1%', '0.8286', '0.857', 'per-claim', '级联升级']
    for kw in tech:
        print(f"  {kw}: {'✓' if kw in all_text else '✗ MISSING'}")


if __name__ == "__main__":
    main()
