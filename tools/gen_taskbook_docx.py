#!/usr/bin/env python3
"""Generate taskbook docx batch1."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(__file__).resolve().parent.parent / "docs" / "srs_project" / "50_任务书_南开部分_第一批.docx"


def set_font(run, name="宋体", size=12, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_para(doc, text, font="宋体", size=12, bold=False, indent=True,
             space_after=6, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_after = Pt(space_after)
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    p.alignment = align
    run = p.add_run(text)
    set_font(run, font, size, bold)
    return p


def add_heading(doc, text, level=1):
    sizes = {0: 16, 1: 14, 2: 13, 3: 12}
    fonts = {0: "黑体", 1: "黑体", 2: "黑体", 3: "楷体"}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 0 else WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    set_font(run, fonts[level], sizes[level], bold=True)
    return p


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        set_font(run, "黑体", 10, bold=True)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            set_font(run, "宋体", 10)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    return table


doc = Document()

# 页面设置
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.top_margin = Cm(2.5)
section.bottom_margin = Cm(2.5)
section.left_margin = Cm(3.0)
section.right_margin = Cm(2.5)

# ============ 封面 ============
add_heading(doc, "面向武器装备科研生产垂域模型应用的\n微调数据集增强技术研究", 0)
add_heading(doc, "任务书（南开大学部分）", 0)
add_para(doc, "", indent=False)

# 封面信息表
info_rows = [
    ("项目名称", "面向武器装备科研生产垂域模型应用的微调数据集增强技术研究"),
    ("所属渠道", "国防科技工业‘人工智能+’专项能力提升工程"),
    ("所属专题", "数据治理有关技术方向"),
    ("分承研单位", "南开大学"),
    ("文档类型", "任务书（研究目标与研究内容部分）"),
    ("编制日期", "2026年10月"),
]
table = doc.add_table(rows=len(info_rows), cols=2)
table.style = "Table Grid"
for i, (k, v) in enumerate(info_rows):
    c1, c2 = table.rows[i].cells
    r1 = c1.paragraphs[0].add_run(k)
    set_font(r1, "黑体", 11, bold=True)
    r2 = c2.paragraphs[0].add_run(v)
    set_font(r2, "宋体", 11)
    c1.width = Cm(4)
    c2.width = Cm(11)

doc.add_page_break()

# ============ 二、研究任务 ============
add_heading(doc, "二、研究任务", 1)

# ---- (一) 研究目标 ----
add_heading(doc, "(一) 研究目标", 2)

add_para(doc, (
    "本项目围绕武器装备科研生产领域多模态数据质量管控业务需求，开展面向垂域微调数据集构建的特征提取与上下文关联关键技术研究，"
    "重点突破多源异构数据的跨模态统一表征、类型化关联判定与证据义务驱动的结构化验证等核心技术难题。"
))

add_para(doc, (
    "在特征提取方面，针对武器装备科研生产文档中文本段落、表格行、流程图节点、用例图元素、时序日志等不同模态数据"
    "在信息表达形式与语义粒度上存在显著差异、难以直接进行语义比较的问题，研究基于冻结编码器骨干的多头语义投影方法，"
    "构建覆盖语义单元头、词面头、共享投影头与确定性正交映射头的多通道特征提取体系。"
    "当前跨模态统一表征研究主要面向通用图文对或栅格文档页：CLIP（Radford et al., ICML 2021）与ALIGN（Jia et al., ICML 2021）"
    "采用双塔对比学习构建共享空间，BLIP-2（Li et al., ICML 2023）与Flamingo（Alayrac et al., NeurIPS 2022）"
    "通过桥接模块或门控交叉注意力融合冻结骨干，ColBERT（Khattab & Zaharia, SIGIR 2020）与ColPali（Faysse et al., ICLR 2025）"
    "采用token级或patch级多向量晚交互实现细粒度匹配。然而，上述方法均以栅格化输入或通用领域为前提，"
    "对于以矢量源格式（VSDX节点坐标、表格行列结构、正文语义单元）存在的武器装备科研生产文档，"
    "尚缺乏面向矢量原生多模态数据的统一表征方法。"
    "此外，小样本场景下冻结骨干优于微调的理论依据已由LP-FT（Kumar et al., ICLR 2023）等负结果研究给出"
    "——证明直接微调会扭曲预训练特征空间，线性探测或轻量投影头在低资源条件下更优。"
    "本项目在此基础上，构建首个面向矢量原生三模态SRS的统一语义空间，"
    "以文档天然结构单元（节点/行/条目）而非token/patch为通道粒度，使通道可解释、可单独测试，"
    "并引入身份边界感知损失，将判别目标从‘找相似‘反转为‘找差异‘，直接服务后续不一致性检测。"
))

add_para(doc, (
    "在上下文关联方面，针对同一业务对象的数据分散于文档多个位置、且这些关联关系在原始数据中往往是隐式存在"
    "而缺乏统一上下文结构进行表达的问题，研究基于显式标识符共指锚点的类型化候选链接构建方法。"
    "当前实体链接领域的主流方法——BLINK（Wu et al., ACL 2020）双编码器召回+交叉精排、"
    "SpanBERT（Joshi et al., TACL 2020）span边界建模——优化‘语义相似即链接‘的目标；"
    "知识图谱链接预测方法——R-GCN（Schlichtkrull et al., NeurIPS 2017）关系专属变换、"
    "RotatE（Sun et al., ICLR 2019）关系旋转——在通用KG上做关系推理。"
    "文档级共指消解SOTA（Lee et al., NAACL 2018；Kirstain et al., EMNLP 2021）面向英文新闻/维基纯文本span，"
    "无结构先验。然而，NLP4RE领域最新综述（Zhao et al., 2024）指出，"
    "现有任务分类中尚无‘跨章节聚合/文档内实体链接‘类目，武器装备科研文档中同一业务对象的跨章节关联判定存在明确研究空白。"
    "需求追踪领域（Antoniol et al., TSE 2002；Hayes et al., TSE 2006；Goknil et al., SoSyM 2011）"
    "做跨工件链接恢复但评测止于链接F1，未将关联作为下游检测的前置层。"
    "本项目建立涵盖身份共指、显式引用、结构隶属与语义近邻四类关系的上下文关联体系，"
    "将关系类型限定为SRS结构关系（引用/包含/追溯/接口对应），链接错误即潜在不一致证据，检索与检测证据链统一。"
))

add_para(doc, (
    "在此基础上，引入领域先验知识对关联结果进行证据义务驱动的结构化验证。"
    "形式化验证领域的证明义务（Proof Obligation）概念源自VDM（Jones, 1990）与B方法（Abrial, 1996），"
    "要求程序精化过程中必须证明的定理可机器生成与消解；"
    "数据质量契约领域（Wang & Strong, JMIS 1996；Deequ, PVLDB 2018；TFDV, MLSys 2019）"
    "定义声明式指标约束但止于布尔通过/告警，无‘义务须以何种证据消解‘的语义；"
    "事实验证领域（FEVER, NAACL 2018；AVeriTeC, EMNLP 2024）要求最小充分证据集但面向开放域英文文本。"
    "本项目将三者融合：每条候选不一致性绑定显式证据义务集（证据类型/来源/充分性阈值），"
    "通过六路证据完备性检查确保每条结构化条目均可追溯至源文档位置，"
    "不可消解义务触发弃权而非强行判定，为后续数据一致性校验智能体提供可信的检测对象与可验证的质量基础。"
    "最终形成特征提取与上下文关联智能体，能够有效支撑武器装备科研生产垂域模型应用的微调数据集构建过程中"
    "多模态数据的结构化解析、关键特征提取和语义关联，"
    "并依托项目实施过程中积累的成熟技术体系与示范经验，积极向国防科技工业其他重点行业拓展推广。"
))

# ---- (二) 研究内容 ----
add_heading(doc, "(二) 研究内容", 2)

add_heading(doc, "1 面向武器装备科研生产数据的跨模态统一表征与上下文关联技术研究", 3)

add_para(doc, (
    "面向武器装备科研生产数据的跨模态统一表征与上下文关联技术研究，实现异构数据的高效语义编码、"
    "统一表征空间映射与关联关系显式构建，保障多源数据中同一业务对象的可关联、可追溯与可验证。"
))

add_para(doc, (
    "本研究内容从多模态特征提取与统一语义空间构建、类型化候选链接与上下文关联构建、"
    "证据义务驱动的结构化验证三个方面展开。"
))

# (1) 特征提取
add_para(doc, (
    "（1）多模态特征提取与统一语义空间构建主要针对武器装备科研生产领域文本、表格、图像、时序数据"
    "在信息表达形式与语义粒度上存在显著差异、难以直接进行语义比较的问题，"
    "从基于解析联邦的多模态数据结构化解析、基于冻结编码器骨干的多头语义投影、"
    "基于身份边界感知的关联损失优化三个方面开展研究，"
    "形成从原始文档到统一语义空间的跨模态特征提取技术体系。"
    "其中，解析联邦负责将不同格式来源的原始数据统一转换为结构化观测，"
    "借鉴LayoutLM系列（Xu et al., KDD 2020；MM 2021）文本+二维布局联合预训练的思路"
    "但以矢量源替代栅格输入，避免OCR引入的字符误差；"
    "冻结编码器骨干负责在不微调的前提下提取高质量的语义表征，"
    "援引LP-FT（Kumar et al., ICLR 2023）等研究的负结果结论作为小样本条件下冻结优于微调的理论依据，"
    "以BGE/C-Pack（Xiao et al., SIGIR 2024）中文对比学习编码器为骨干；"
    "多头投影体系负责将异构特征映射到统一语义空间，"
    "语义单元头采用文档结构单元级多向量表示而非ColBERT的token级或ColPali的patch级，"
    "词面头采用BM25实现编号精确召回，"
    "共享投影头采用线性-LN-GELU-线性结构借鉴CLIP-Adapter（Gao et al., ICPR 2024）轻量适配设计，"
    "确定性正交映射头基于Procrustes分析实现无训练跨空间对齐；"
    "身份边界感知损失负责在训练过程中区分语义相似与身份共指，"
    "借鉴实体对齐领域Dual-AMN（Mao et al., TKDE 2022）margin+硬负例对比学习思想，"
    "以‘同条目跨章节为正对、近似异条目为硬负对‘的构造方式，"
    "将判别目标从‘找相似‘反转为‘找差异‘，避免将不同业务对象误合并为同一实体；"
))

# (2) 上下文关联
add_para(doc, (
    "（2）类型化候选链接与上下文关联构建主要针对同一业务对象的数据分散于文档正文、表格行、流程图节点、"
    "用例图元素、追溯表等多个位置、且这些关联关系在原始数据中往往是隐式存在而缺乏统一表达的问题，"
    "从基于显式标识符共指的高置信锚点构建、基于类型化候选链接的多源数据关联判定、"
    "基于结构化聚合的条目生成三个方面开展研究，"
    "实现从观测级、实体级到语义条目级的多粒度上下文关联分析。"
    "其中，显式标识符共指锚点利用文档中已有的唯一标识符建立跨位置的高置信关联，"
    "借鉴BLINK（Wu et al., ACL 2020）两阶段实体链接的召回+精排范式"
    "但以结构化证据替代纯语义相似度；"
    "类型化候选链接体系将关联关系区分为身份共指、显式引用、结构隶属与语义近邻四类"
    "并分别施加不同的确认准则，"
    "借鉴R-GCN（Schlichtkrull et al., NeurIPS 2017）关系专属变换的思想"
    "但将关系类型限定为SRS文档结构关系，使链接错误直接构成不一致性检测的证据；"
    "结构化聚合通过并查集算法将确认的关联关系凝聚为完整的事务级条目，"
    "参考TAPAS（Herzig et al., ACL 2020）行级结构化编码与TableRAG（Chen et al., EMNLP 2024）"
    "cell级检索的粒度选择依据，以文档天然结构单元为聚合单元；"
))

# (3) 结构化验证
add_para(doc, (
    "（3）证据义务驱动的结构化验证主要针对关联结果的可信度保障与可审计性问题，"
    "从基于六路证据完备性检查的条目验证、基于误报全拯救的弃权机制、"
    "基于最小充分证据集的可审计输出三个方面展开，"
    "支撑垂域微调数据在业务逻辑上的自洽与可信。"
    "其中，六路证据完备性检查要求每条结构化条目在正文、用例表、流程图、能力表行、合格性行、"
    "追溯行六类证据来源上满足完备性约束，"
    "借鉴TabFact（Chen et al., EMNLP 2019）表格事实验证的NLI式判证思路"
    "但扩展至六路多模态证据；"
    "弃权机制确保证据不足时不强行判定缺陷而是显式输出不足状态，"
    "参考Chow（IEEE-IT 1970）最优拒绝规则与共形预测（Angelopoulos et al., ICML 2021）"
    "的FDR受控选择性预测理论，以及SQuAD 2.0（Rajpurkar et al., ACL 2018）"
    "证据不足→不可答的充分性判定范式；"
    "最小充分证据集为每条验证结论提供可逐项复核的最小证据集合，"
    "借鉴FEVER（Thorne et al., NAACL 2018）预测充分最小证据集与"
    "EntailmentBank（Dalvi et al., 2021）最小化证明树的思想，"
    "以Z3 unsat core与图约束最小冲突集为技术实现，"
    "从而实现关联结果的可追溯、可审计与可验证。"
))

# ============ 附件：文献支撑摘要 ============
doc.add_page_break()
add_heading(doc, "附件：文献支撑摘要（内部参考）", 1)
add_para(doc, "以下为研究目标与研究内容中引用的关键文献，按主题组织。", indent=False)

add_heading(doc, "A1 多模态文档特征提取", 2)
add_table(doc, ["文献", "出处", "核心方法", "本项目关联"], [
    ("DPR (Karpukhin 2020)", "EMNLP", "双编码器稠密检索", "文本条目召回基线"),
    ("ColBERT (Khattab 2020)", "SIGIR", "token级多向量+MaxSim", "多头多向量先例"),
    ("ColPali (Faysse 2024)", "ICLR'25", "patch级视觉嵌入免OCR", "VSDX矢量原生替代"),
    ("BGE/C-Pack (Xiao 2023)", "SIGIR'24", "中文对比学习embedding", "bge-large-zh骨干"),
    ("LayoutLM v1-3 (Xu 2020-21)", "KDD/MM", "文本+2D布局联合预训练", "布局坐标先验"),
    ("Donut (Kim 2022)", "ECCV", "OCR-free文档理解", "VLM转写桥先例"),
], [3.5, 1.8, 4.0, 4.2])

add_heading(doc, "A2 跨模态统一表征（冻结骨干理论依据）", 2)
add_table(doc, ["文献", "出处", "核心方法", "本项目关联"], [
    ("CLIP (Radford 2021)", "ICML", "双塔对比共享空间", "共享投影范式原型"),
    ("BLIP-2 (Li 2023)", "ICML", "Q-Former桥接冻结骨干", "冻结+轻量投影先例"),
    ("LP-FT (Kumar 2023)", "ICLR", "小样本微调扭曲预训练特征", "冻结优于微调理论依据"),
    ("CLIP-Adapter (Gao 2024)", "ICPR", "残差式轻量adapter", "共享投影头设计"),
    ("VPT (Jia 2022)", "ECCV", "冻结骨干+可学习prompt", "参数高效适配备选"),
], [3.5, 1.8, 4.0, 4.2])

add_heading(doc, "A3 表格与图形特征提取", 2)
add_table(doc, ["文献", "出处", "核心方法", "本项目关联"], [
    ("TAPAS (Herzig 2020)", "ACL", "行列位置编码", "行级结构化编码"),
    ("TabFact (Chen 2019)", "EMNLP", "表格事实验证NLI", "表文矛盾检测"),
    ("TableRAG (Chen 2024)", "EMNLP", "cell级检索优于全表", "行级单元检索依据"),
    ("GAT (Veličković 2018)", "ICLR", "注意力邻接聚合", "拓扑编码基线"),
    ("Graphormer (Ying 2021)", "NeurIPS", "度/中心/距离编码", "节点结构位置编码"),
], [3.5, 1.8, 4.0, 4.2])

add_heading(doc, "A4 身份边界与实体/关系链接", 2)
add_table(doc, ["文献", "出处", "核心方法", "本项目关联"], [
    ("BLINK (Wu 2020)", "ACL", "双编码召回+交叉精排", "两阶段EL范式"),
    ("Dual-AMN (Mao 2022)", "TKDE", "margin+硬负例对比", "身份边界损失先例"),
    ("R-GCN (Schlichtkrull 2017)", "NeurIPS", "关系专属变换GCN", "类型化关系链接先例"),
    ("RotatE (Sun 2019)", "ICLR", "关系=复空间旋转", "relation-aware链接"),
    ("SpanBERT (Joshi 2020)", "TACL", "span掩码边界建模", "span抽取先例"),
    ("DocRED (Yao 2019)", "EMNLP", "文档级实体-关系图", "typed候选边定义"),
], [3.5, 1.8, 4.0, 4.2])

add_heading(doc, "A5 需求工程与文档关联", 2)
add_table(doc, ["文献", "出处", "核心方法", "本项目关联"], [
    ("Antoniol 2002", "TSE", "IR恢复需求↔代码链", "矩阵式TLR起点"),
    ("Hayes 2006", "TSE", "候选链+人工确认两段式", "候选生成↔裁决分工"),
    ("Goknil 2011", "SoSyM", "追溯关系形式语义", "边有语义才能检测"),
    ("LLM4RE综述 (Zhao 2024)", "arXiv", "任务分类无跨章节聚合", "研究空白论证"),
    ("TraceLLM 2026", "arXiv", "LLM+检索混合TLR", "LLM产边范式"),
], [3.5, 1.8, 4.0, 4.2])

add_heading(doc, "A6 证据义务与可验证AI", 2)
add_table(doc, ["文献", "出处", "核心方法", "本项目关联"], [
    ("VDM (Jones 1990)", "书", "精化规则生成PO", "义务概念发源"),
    ("B方法 (Abrial 1996)", "书", "PO自动生成+消解", "义务机械化先例"),
    ("Chow 1970", "IEEE-IT", "最优拒绝规则", "弃权理论基础"),
    ("FEVER (Thorne 2018)", "NAACL", "预测充分最小证据集", "最小证据先例"),
    ("EntailmentBank (Dalvi 2021)", "EMNLP", "蕴含树最小化证明", "最小证明树"),
    ("AVeriTeC 2024", "EMNLP", "判对且证据质量达标", "双评分范式"),
    ("Conformal (Angelopoulos 2021)", "ICML", "FDR≤α选择性推断", "弃权风险控制"),
    ("FActScore (Min 2023)", "EMNLP", "声明→原子事实→证据链", "证据链分解"),
], [3.5, 1.8, 4.0, 4.2])

add_heading(doc, "A7 创新点差异分析", 2)
add_para(doc, (
    "本项目的创新点相对于上述文献的差异体现在五个方面："
    "（a）矢量原生vs栅格输入——ColPali/LayoutLM面向栅格文档页，本项目首个面向矢量原生VSDX+表行+正文段落的统一空间；"
    "（b）冻结骨干的小样本论证——BLIP-2/VPT用海量数据，本项目16文档场景援引LP-FT负结果为理论依据；"
    "（c）通道粒度——ColBERT/ColPali的token/patch级多向量，本项目用文档天然结构单元，可解释可单测；"
    "（d）损失目标反转——EL文献优化'相似即链接'，本项目以'找差异'为目标直接服务不一致性检测；"
    "（e）QualityContract三重差异——对工业数据契约无义务消解语义、对形式化PO放宽为量化风险预算、"
    "对事实验证把最小充分证据集引入数据质量域，三者均无先例组合。"
), indent=False)

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(str(OUT))
print(f"生成完成: {OUT}")
print(f"文件大小: {OUT.stat().st_size} bytes")
