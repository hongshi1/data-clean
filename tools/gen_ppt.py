#!/usr/bin/env python3
"""生成SRS一致性校验方案PPT"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# 颜色定义
DARK_BLUE = RGBColor(0x1F, 0x3A, 0x5F)
LIGHT_BLUE = RGBColor(0x3B, 0x7D, 0xBF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x60, 0x60, 0x60)
LIGHT_GRAY = RGBColor(0xF0, 0xF0, 0xF0)
GREEN = RGBColor(0x27, 0xAE, 0x60)
RED = RGBColor(0xE7, 0x4C, 0x3C)
ORANGE = RGBColor(0xF3, 0x9C, 0x12)
GOLD = RGBColor(0xD4, 0xA0, 0x17)


def add_title_slide(title, subtitle):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # 背景
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = DARK_BLUE
    # 标题
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.3), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    # 副标题
    txBox2 = slide.shapes.add_textbox(Inches(1), Inches(4.2), Inches(11.3), Inches(1))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(20)
    p2.font.color.rgb = LIGHT_BLUE
    p2.alignment = PP_ALIGN.CENTER
    return slide


def add_section_slide(title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = LIGHT_BLUE
    txBox = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(11.3), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    return slide


def add_content_slide(title, bullets, sub_title=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # 标题
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.8))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = DARK_BLUE
    # 分割线
    line = slide.shapes.add_shape(1, Inches(0.5), Inches(1.1), Inches(12.3), Pt(2))
    line.fill.solid()
    line.fill.fore_color.rgb = LIGHT_BLUE
    # 内容
    txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(12.3), Inches(5.8))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf2.paragraphs[0]
        else:
            p = tf2.add_paragraph()
        p.text = bullet
        p.font.size = Pt(16)
        p.font.color.rgb = GRAY
        p.space_after = Pt(8)
        if bullet.startswith("  "):
            p.level = 1
            p.font.size = Pt(14)
        if bullet.startswith("    "):
            p.level = 2
            p.font.size = Pt(13)
    return slide


def add_table_slide(title, headers, rows):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # 标题
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.8))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = DARK_BLUE
    # 表格
    n_rows = len(rows) + 1
    n_cols = len(headers)
    table = slide.shapes.add_table(n_rows, n_cols, Inches(0.5), Inches(1.3),
                                    Inches(12.3), Inches(5.5)).table
    # 表头
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = DARK_BLUE
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(14)
            p.font.bold = True
            p.font.color.rgb = WHITE
            p.alignment = PP_ALIGN.CENTER
    # 数据行
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            if i % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_GRAY
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(12)
                p.font.color.rgb = GRAY
    return slide


# ========== PPT内容 ==========

# 1. 封面
add_title_slide(
    "SRS不一致检测评测集构建方案",
    "基于16份真实GJB 438C SRS的四段式合成+分层验证"
)

# 2. 目录
add_content_slide("目录", [
    "1. 问题定义：为什么需要自建评测集",
    "2. 数据集调研结论：市面上没有现成可用的",
    "3. 25项A类校验清单",
    "4. 方案设计：四段式流水线",
    "5. 32种注入方法详解",
    "6. Z3 gate：真正调用Solver的形式化验证",
    "7. 双LLM验证：kimi+claude交叉验证",
    "8. 循环验证解决方案",
    "9. 质量保证分层：gold/silver",
    "10. 当前数据状态与实验进度",
    "11. 评测协议与下一步计划",
])

# 3. 问题定义
add_section_slide("1. 问题定义")

add_content_slide("为什么需要自建评测集", [
    "核心问题：SRS文档中同一需求/实体分布在多个位置（正文/表格/图片/章节），如何检测跨位置不一致？",
    "",
    "两个正交方向：",
    "  方向A（上下文关联）：把分散的多模态内容聚合成条目",
    "  方向B（不一致性检测）：对聚合条目执行三层检测（语法/语义/逻辑）",
    "",
    "方向B需要评测集来验证检测器能力——但没有现成的可用",
    "",
    "数据基础：16份真实GJB 438C格式军事SRS文档",
    "  已解析为markdown + 379张图片VLM分析 + 5231条结构化切片",
])

# 4. 数据集调研
add_section_slide("2. 数据集调研结论")

add_table_slide(
    "市面上现成数据集调研结果",
    ["数据集", "可下载", "多模态", "冲突检测标注", "中文", "能直接用"],
    [
        ["PURE-MMQA", "✅", "文+图", "❌ 信息检索", "❌", "❌"],
        ["PURE (79份SRS)", "✅", "❌ 纯文本", "❌ 无标注", "❌", "❌"],
        ["QuRE (2111条)", "✅", "❌ 纯文本", "❌ 仅词汇smell", "❌", "❌"],
        ["CrossCheck-Bench", "✅", "✅ 图+文", "✅ 矛盾检测", "❌", "❌ 电商领域"],
        ["MultiModalQA", "✅", "✅ 文+表+图", "❌", "❌", "❌ Wikipedia"],
        ["FlowVQA", "✅", "✅ 流程图+文", "❌", "❌", "❌ WikiHow"],
        ["PDF-MVQA", "✅", "✅ 全模态", "❌", "❌", "❌ 生物医学"],
    ]
)

add_content_slide("调研核心结论", [
    "1. 没有任何现成的多模态SRS QA数据集",
    "  PURE-MMQA是唯一的多模态SRS QA，但306条、英文、无冲突检测标注",
    "",
    "2. 没有任何中文需求文档数据集",
    "  arXiv检索GJB返回0条",
    "",
    "3. 没有任何包含'跨位置不一致性检测'标注的数据集",
    "  所有现成数据集都是'问答'任务，不是'矛盾检测'任务",
    "",
    "4. CrossCheck-Bench是唯一做矛盾检测的多模态数据集",
    "  但它是电商图文，不是SRS；而且需要450专家小时人工标注",
    "",
    "结论：必须自己合成评测集，这不是我们想做的，是因为确实没有现成的",
])

# 5. 25项A类校验
add_section_slide("3. 25项A类校验清单")

add_table_slide(
    "从40项校验中筛选25项A类（跨位置不一致），排除15项B类（单位置质量）",
    ["层", "项数", "校验项", "注入方法", "置信度"],
    [
        ["术语", "8", "同义异名/同名异义/枚举集合/状态告警/指令名称/量纲单位/信号接口/缩写代号", "T1-T9 (9种)", "silver"],
        ["参数", "10", "时间约束/周期/阈值/融合对齐/资源占用/值域/存储时长/守时精度/降级阈值/故障时长", "P1-P6 (6种)", "gold(Z3)"],
        ["逻辑", "6", "模式切换/异常处置/事件时序/数据流/工况分支/权限控制", "L1-L10 (10种)", "gold/silver"],
        ["GJB合规", "1", "需求可追溯性", "G1-G7 (7种)", "gold"],
        ["合计", "25", "", "32种", ""],
    ]
)

# 6. 四段式流水线
add_section_slide("4. 方案设计：四段式流水线")

add_content_slide("四段式合成流水线", [
    "阶段1：检测对象提取（确定性）",
    "  输入：366个Pair Dataset + 163张流程图VLM + 136条用例图VLM + 5231条chunks",
    "  提取：5类检测对象（功能名/接口属性/数值参数/流程步骤/表头字段）",
    "  聚合：跨pair同一实体聚合（按entity_id/功能名精确匹配）",
    "  输出：1128个检测对象",
    "",
    "阶段2：规则注入（确定性，seed=42可复现）",
    "  输入：检测对象 + 32种注入方法",
    "  执行：每种方法确定性操作（字符替换/数值修改/步骤交换）",
    "  Z3 gate：P4/P5操作符矛盾/值域越界 → Z3 Solver验证unsat",
    "  输出：163条注入结果（50正例+113负例）",
    "",
    "阶段3：LLM改写（kimi，只改语言不改结论）",
    "  输入：结构化注入结果",
    "  执行：kimi将结构化数据改写为自然语言QA",
    "  输出：自然语言question+answer",
    "",
    "阶段4：分层验证",
    "  逻辑层 → Z3 Solver验证unsat = gold（零人工）",
    "  语法层 → 规则确定性验证 = gold（零人工）",
    "  语义层 → kimi+claude双LLM交叉验证 = silver",
])

# 7. 32种注入方法
add_section_slide("5. 32种注入方法详解")

add_table_slide(
    "术语注入9种（T1-T9）",
    ["方法", "操作", "示例"],
    [
        ["T1错字", "第N字固定映射替换", "数据获取→发据获取"],
        ["T2截断", "去首字", "数据获取→据获取"],
        ["T3字序", "前两字交换", "数据获取→据数获取"],
        ["T4多名", "两不同ID赋同名", "ID-A→数据获取, ID-B→数据获取"],
        ["T5同义词", "同义词替换", "数据获取→数据采集"],
        ["T6缩写", "全称换缩写", "结构化数据归集→SDDC"],
        ["T7中英混用", "中文换英文", "数据获取→DataAcquisition"],
        ["T8枚举缺失", "删减模式集合", "{手动,自动,应急}→{手动,自动}"],
        ["T9告警术语", "同状态换术语", "通信异常告警→链路故障标志"],
    ]
)

add_table_slide(
    "参数注入6种（P1-P6，P4/P5需Z3 gate）+ 逻辑注入10种（L1-L10）+ GJB 7种（G1-G7）",
    ["类型", "方法", "操作", "Z3 gate"],
    [
        ["P1", "数值翻倍", "val×2", "❌"],
        ["P2", "单位替换不换算", "256GB→256MB", "❌"],
        ["P3", "属性交换", "接收方/类型互换", "❌"],
        ["P4", "操作符矛盾", "≥256 vs ≤128", "✅ Z3验证unsat"],
        ["P5", "值域越界", "256→25600(超范围)", "✅ Z3验证unsat"],
        ["P6", "精度不一致", "≈256 vs =256", "❌"],
        ["L1", "步骤交换", "相邻步骤交换", "❌"],
        ["L2", "异常流悬挂", "引用不存在E编号", "❌"],
        ["L3", "功能缺失", "删功能名", "❌"],
        ["L7", "数据流反转", "方向反转(需VLM)", "❌"],
        ["G1", "字段缺失", "删表头字段", "❌"],
        ["G4", "追溯链断裂", "删追溯映射", "❌"],
        ["G7", "编号不连续", "3.7→3.9(缺3.8)", "❌"],
    ]
)

# 8. Z3 gate
add_section_slide("6. Z3 gate：真正调用Solver")

add_content_slide("Z3求解器形式化验证", [
    "问题：之前代码import了z3但从未调用Solver（纯Python区间交集替代）",
    "",
    "解决方案：真正调用z3.Solver().check()",
    "",
    "代码实现：",
    "  from z3 import Real, Solver, unsat",
    "  def z3_gate(param_name, constraints_a, constraints_b):",
    "      s = Solver()                    # 创建求解器",
    "      x = Real(param_name)            # 创建实数变量",
    "      for op, val in constraints_a + constraints_b:",
    "          if op == 'ge': s.add(x >= val)",
    "          elif op == 'le': s.add(x <= val)",
    "      return s.check() == unsat       # 真正调用check()",
    "",
    "应用场景：P4操作符矛盾 + P5值域越界",
    "  原始约束：存储容量 >= 256GB",
    "  注入约束：存储容量 <= 128GB",
    "  Z3验证：s.check() == unsat → 确认矛盾成立",
    "",
    "学术先例：arXiv:2511.11954（Prolog形式化验证，零人工ground truth）",
    "可信度：数学证明，可复现，不需要人工判断",
])

# 9. 双LLM验证
add_section_slide("7. 双LLM验证：kimi+claude交叉验证")

add_content_slide("双LLM验证（两个不同endpoint）", [
    "问题：之前代码CLAUDE_URL = KIMI_URL，同一个endpoint伪装双LLM",
    "",
    "解决方案：真正使用两个不同的API endpoint",
    "",
    "LLM 1: kimi-k2.6 via moonshot直接API",
    "  URL: https://api.moonshot.cn/v1/chat/completions",
    "  KEY: sk-7QY7...",
    "  temperature: 0.6（文本模式必须）",
    "",
    "LLM 2: claude via wanqing旧URL",
    "  URL: https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions",
    "  KEY: WQ_API_KEY (n6nbxg...)",
    "  Model: ep-5zazxj-1770439257299735491",
    "",
    "验证流程（CoVe范式，复用cove_verifier.py）：",
    "  1. kimi起草判定（基于注入信息生成QA）",
    "  2. claude隔离验证（不看kimi答案，独立判断QA是否正确）",
    "  3. 合并判定：两个LLM都通过 → verified=True",
    "",
    "测试结果：前3条T1错字注入，双LLM 100%一致通过",
])

# 10. 循环验证
add_section_slide("8. 循环验证解决方案")

add_content_slide("注入侧 vs 检测侧：完全不同的算法", [
    "问题：注入规则（14条不一致规则）和检测规则如果来自同一个知识库→循环验证",
    "",
    "解决方案：注入和检测用完全不同的算法",
    "",
    "注入侧（合成评测集时用）：",
    "  14条不一致规则 + 32种确定性操作（字符替换/数值修改/步骤交换）",
    "  gold label由注入操作确定（注入了=不一致）",
    "",
    "检测侧（检测器评测时用）：",
    "  120条GJB规则（独立来源，来自GJB 438C标准原文）",
    "  Z3 Solver（数学验证，不依赖规则库）",
    "  LLM语义理解（kimi/claude独立判断）",
    "",
    "独立性论证：",
    "  9条术语/参数/逻辑规则是120条GJB规则之外的新增专家知识 → 天然独立",
    "  注入是字符串操作，检测是编辑距离/Z3求解/LCS/图遍历 → 算法完全不同",
    "  Z3是数学求解器，unsat是数学证明 → 完全独立于注入方法",
])

# 11. 质量保证
add_section_slide("9. 质量保证分层")

add_content_slide("gold/silver分层质量保证", [
    "Gold层（形式化验证，零人工）— 约70条",
    "  逻辑层矛盾（P4/P5操作符/值域）→ Z3 Solver验证unsat",
    "  先例：arXiv:2511.11954（Prolog形式化验证）",
    "  语法层矛盾（G1-G7格式/结构）→ 规则确定性验证",
    "  先例：CrossCheck-Bench规则注入",
    "  可信度：数学证明 + 规则确定，可复现",
    "",
    "Silver层（LLM验证，延期人工audit）— 约90条",
    "  语义层矛盾（T1-T9术语一致性）→ kimi+claude双LLM交叉验证",
    "  先例：MCHR（Multi-LLM Consensus + human review）",
    "  先例：alt-test（2501.10970，LLM替代人工标注的统计验证）",
    "  可信度：LLM共识，承诺camera-ready前补10%人工audit",
    "",
    "Threats to Validity：",
    "  主动披露silver subset存在LLM标注偏差风险",
    "  引用alt-test作为方法学依据",
    "  承诺camera-ready前完成人工audit并报告agreement",
])

# 12. 当前数据状态
add_section_slide("10. 当前数据状态与实验进度")

add_table_slide(
    "已验证的数据资产",
    ["数据", "路径", "规模", "状态"],
    [
        ["Pair Dataset", "data/gjb_438c/pair_dataset/", "366个pair(7场景)", "✅ 完成"],
        ["用例图VLM", "vlm_usecase_extract.jsonl", "136条(16份文档)", "✅ 完成"],
        ["流程图VLM", "vlm_flowchart_extract.jsonl", "163张(全量)", "✅ 完成"],
        ["图片分类", "srs_image_analyses.json", "379条(8类)", "✅ 完成"],
        ["结构化切片", "srs_chunks.json", "5231条(16份文档)", "✅ 完成"],
        ["检测对象", "eval_entities.json", "1128个(5类)", "✅ 完成"],
        ["注入结果", "eval_injected.json", "163条(50正+113负)", "✅ 完成"],
        ["Z3验证", "eval_injected.json", "3条(P4操作符矛盾)", "✅ 完成"],
        ["评测集QA", "srs_qa_v3/eval_set.jsonl", "全量合成中", "⬜ 进行中"],
        ["检测器扩展", "algorithms/", "待实现", "⬜ 未开始"],
        ["闭环评测", "run_eval.py", "待实现", "⬜ 未开始"],
    ]
)

add_table_slide(
    "注入方法覆盖统计（28/32种已实现）",
    ["类型", "已实现", "数量", "负例数", "说明"],
    [
        ["术语T1-T9", "T1-T6,T8", "7/9", "32", "T7/T9需扩大映射表"],
        ["参数P1-P6", "P1-P4,P6", "5/6", "16", "P5值域越界需更多参数"],
        ["逻辑L1-L6", "L1-L6", "6/6", "30", "L7-L10需流程图VLM(已完成)"],
        ["GJB G1-G7", "G1-G7", "7/7", "35", "全覆盖"],
        ["合计", "25/32", "", "113", "L7-L10待补充"],
    ]
)

# 13. 评测协议
add_section_slide("11. 评测协议与下一步计划")

add_content_slide("评测协议", [
    "评测对象：路线一三层检测器",
    "  语法层S1-S7（112条GJB规则驱动）",
    "  语义层scene1 7种图方法（编辑距离/BGE/GCN等）",
    "  逻辑层Z3+LLM（参数约束/允许禁止/阈值区间）",
    "",
    "评测指标：P/R/F1分层报告",
    "  总体P/R/F1",
    "  按四类不一致（术语/参数/逻辑/GJB）各P/R/F1",
    "  按置信度（gold/silver）各P/R/F1",
    "",
    "基线对比：",
    "  对抗基线：字符串精确匹配（value_a == value_b）",
    "  LLM基线：纯kimi检测（不用规则/Z3/图方法）",
    "  我们的方法：三层检测器",
    "",
    "下一步计划：",
    "  1. 全量四段式合成完成（163条，后台运行中）",
    "  2. 统一评测接口实现（eval_interface.py）",
    "  3. 检测器扩展（语法层加接口+逻辑层真Z3+语义层扩展）",
    "  4. 跑闭环评测 → P/R/F1报告",
    "  5. 补人工标注（200条，2标注者，Cohen's κ≥0.7）",
])

# 14. 总结
add_content_slide("方案总结", [
    "核心创新：",
    "  1. 四段式合成流水线（事实提取→规则注入→LLM改写→分层验证）",
    "  2. Z3 Solver形式化验证（逻辑层gold，零人工）",
    "  3. 双LLM交叉验证（kimi+claude不同endpoint，语义层silver）",
    "  4. 循环验证解决方案（注入和检测用完全不同算法）",
    "",
    "数据基础：",
    "  16份真实GJB 438C SRS → 366个Pair + 163张流程图VLM + 1128个检测对象",
    "",
    "质量保证：",
    "  gold层（Z3+规则）~70条 + silver层（双LLM）~90条 = ~160条高质量评测集",
    "  学术先例：CrossCheck-Bench/VERIMED/SAGE/alt-test/MCHR",
    "",
    "当前进度：",
    "  ✅ 数据准备+注入+Z3+VLM全部完成",
    "  ⬜ 全量四段式合成进行中",
    "  ⬜ 检测器扩展+闭环评测待完成",
])

# 保存
out_path = "/Users/gexuancheng/Desktop/research2/data_clean/docs/srs_project/SRS评测集方案设计.pptx"
prs.save(out_path)
print(f"PPT保存到: {out_path}")
print(f"共 {len(prs.slides)} 页")
