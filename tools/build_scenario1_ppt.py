"""Rebuild scenario one PPT with complete per-shape text replacement.

Reads the reference PPT (scene 3, slides 1-9), replaces every non-empty text
shape with scenario-1 content based on the original text (not position
ordering), and replaces content images while preserving the header logo.
"""
from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ROOT = Path(__file__).resolve().parents[1]
REF = Path(os.environ["SCENE34_PPTX"])
OUT = ROOT / "docs/srs_project/paper/scenario1_aligned_to_scene3_4.pptx"

# --- text replacement maps (per slide, old text -> new text) ---

REPLACEMENTS: dict[int, dict[str, str]] = {}

# Slide 1: cover
REPLACEMENTS[1] = {
    "第三章": "第一章",
    "场景三": "场景一\nGJB SRS上下文关联与一致性校验",
}

# Slide 2: data characteristics
REPLACEMENTS[2] = {
    "场景三数据特点": "场景一数据特点",
}

# Slide 2 group content (inside the big group shape)
REPLACEMENTS[2].update({
    "由图文信息向质量问答传递": "由多模态证据向一致性校验传递",
    "源资料载体": "证据载体",
    "图文混合 PDF": "正文 / 表格 / 图片 / 追溯表",
    "语义知识空间": "检测对象空间",
    "对象、关系、条件、约束": "需求、接口、功能、约束",
    "信息碎片化": "证据分散",
    "信息分布在不同文本片段、图片和表格中。": "同一功能出现在正文、能力表、用例表和图中。",
    "对象关联复杂": "主体不明确",
    "对象与属性存在多层嵌套关系。": "同一ID或名称可能绑定不同功能/接口。",
    "参数约束密集": "约束跨位置",
    "数值、单位、范围等约束密集出现。": "数值、枚举、异常处置分散在不同章节和表格。",
    "上下文依赖显著": "缺席≠矛盾",
    "条件和适用范围需要借助上下文判断。": "查不到证据保留NIE，不直接判refute。",
})

# Slide 3: feature extraction (46 text shapes)
REPLACEMENTS[3] = {
    "特征提取": "证据特征提取",
    "将扫描 PDF 中的工序描述、图表和质量要求转换为可核验的结构化特征":
        "将16份GJB SRS解析为可追溯、可比较的证据对象",
    # column 1
    "图像恢复与 OCR": "多模态内容解析",
    "扫描页恢复为可定位文本": "正文、表格、图片统一读取",
    "页面增强": "章节解析",
    "渲染、方向校正、对比度增强": "正文按章节层级结构化",
    "中文识别": "表格解析",
    "PaddleOCR 输出文本、坐标与置信度": "表格保留行列及单元格结构",
    "低置信度复核": "图片解析",
    "异常页单页重跑并保留原始证据": "图片保留原始文件与文档位置",
    # column 2
    "版面与字段定位": "结构与字段抽取",
    "利用标题锚点和相对区域解析": "形成可比较内容单元",
    "工序身份": "对象识别",
    "工序号、名称、图表号、产品图号": "识别需求、接口、功能主体",
    "工艺内容": "字段提取",
    "工步、设备、工装、辅助材料": "提取ID、名称、参数和约束",
    "质量证据": "位置绑定",
    "技术要求、工序略图、来源页": "保留章节、表号、页码来源",
    # column 3
    "跨页融合与校验": "证据对象组织",
    "把分散片段合并为完整工序": "把分散内容归入同一对象",
    "跨页合并": "正文关联",
    "按文档和工序号聚合连续页面": "关联正文描述与对应表格行",
    "序号去重": "图片登记",
    "工步按编号排序并消除重复识别": "登记图片节点和邻接关系",
    "状态控制": "证据归档",
    "机器抽取与 needs_review 分级": "记录实体类型与出现位置",
    # column 4
    "统一特征对象": "来源追溯与核验",
    "面向检索、图谱和缺陷检测": "支持后续关联和校验",
    "语义实体": "原文锚点",
    "工序、工步、材料、工装": "每条事实保留原文引用位置",
    "证据元数据": "来源定位",
    "PDF、页码、坐标、置信度、复核状态": "可回看页码、块、行和span",
    "持久化": "结构化输出",
    "JSON 主数据与 SQLite 查询库": "JSON主数据与查询库",
    # bottom
    "输出特征": "输出特征",
    "字段值 + 实体类型 + 顺序位置 + 来源证据 + 置信度":
        "主体 + 值/约束 + 语义角色 + 原始位置 + 置信度",
    "可直接用于": "可直接用于",
    "完整工序检索\n知识图谱构建": "完整证据检索\n知识图谱构建",
}

# Slide 4: context linking (52 text shapes)
REPLACEMENTS[4] = {
    "上下文关联": "上下文关联",
    "以工序顺序、共享实体和来源证据连接每道工序，形成可回溯的过程上下文":
        "把分散登记聚合成同一个检测对象",
    "工序顺序上下文": "证据来源序列",
    "****涂漆": "需求声明",
    "取**": "接口定义",
    "工作前准备": "功能描述",
    "顺序工序": "更多来源",
    "压药": "接口图",
    "清擦浮药": "追溯表",
    "外观及尺寸检验": "合格性表",
    # central evidence graph
    "工序 9 · 压药的局部证据图谱": "统一条目 · 需求/接口/功能",
    "工序 9\n压药": "需求/接口\n统一条目",
    "工步": "正文",
    "装模、施压、退模": "需求声明与约束条件",
    "设备": "表格",
    "*****压药线": "能力表、接口表、用例表",
    "工装": "接口图",
    "模具、定位垫": "接口节点和邻接关系",
    "材料": "追溯",
    "炸药、纱布": "正向/逆向映射关系",
    "技术要求": "合格性",
    "压力、外观、密度约束": "验证方法与覆盖项",
    # right side traceability
    "缺陷出现后的追溯路径": "聚合后的证据追溯路径",
    "输入缺陷现象": "输入查询或claim",
    "外观、尺寸、密度或装药异常": "需求/接口/功能名称或ID",
    "匹配关键特征": "匹配关联锚点",
    "命中工步、参数和技术要求": "命中ID、章节、表格行和图片节点",
    "定位候选工序": "定位候选条目",
    "结合顺序相邻与共享实体排序": "结合邻接关系和共享实体排序",
    "返回原页证据": "返回原始证据",
    "展示 PDF 页码、区域和复核状态": "展示页码、块号、行和复核状态",
    # bottom
    "关联依据": "关联依据",
    "工序先后关系   共享设备与材料   工步和要求文本相似度":
        "ID匹配 + 章节邻接 + 表格关系 + 语义相似度",
    "当前图谱输出候选路径，缺陷因果关系需结合检测数据和专家规则确认":
        "当前条目为聚合结果，一致性判定需TERM/PARAM/LOGIC/GJB校验",
}

# Slide 5: consistency framework (13 text + 3 groups)
REPLACEMENTS[5] = {
    "一致性校验框架": "一致性校验框架",
    "证据与知识输入": "三态输入",
    "问答内容": "冻结证据",
    "待检回答与业务标签": "正文、表格、图片、追溯与合格性表",
    "上下文信息": "Answer原子claim",
    "对象关系与适用范围": "术语、参数、逻辑和合规声明",
    "专家知识": "40项检测体系",
    "领域概念与适用约束": "TERM×8、PARAM×10、LOGIC×11、GJB×11",
    # group 1: syntax -> L0
    "语法一致性校验": "L0 NER实体层",
    "数值格式": "同义异名",
    "单位术语": "同名异义",
    "编号引用": "枚举集合",
    "缩写代号": "缩写代号",
    # group 2: semantic -> L1
    "语义一致性校验": "L1确定性规则层",
    "实体对应": "ID双登记",
    "程度一致": "参数区间",
    "范围一致": "事件时序",
    "标签对应": "追溯矛盾",
    # group 3: logic -> L2
    "逻辑一致性校验": "L2 NLI语义残差",
    "工序时序一致": "语义比对",
    "因果归因一致": "证据定位",
    "条件处置一致": "三态判定",
    # bottom output
    "输出": "输出",
    "分层、分项结论": "三态判定",
    "问题类型": "证据定位",
    "判断依据": "判定依据",
}

# Slide 6: technical route (51 text shapes)
REPLACEMENTS[6] = {
    "技术路线": "技术路线",
    "针对工序描述中对象、属性与约束交织的特点，以跨度候选抽取为基础，结合大模型核验与纠偏用于结构化一致性判断的核验对象。":
        "分散证据先聚合成可核验上下文，再由确定性规则处理可形式化冲突，L2 NLI处理语义残差",
    "场景驱动": "问题驱动",
    "对象属性嵌套": "证据分散",
    "对象、属性与参数并非独立出现，而是相互嵌套。":
        "同一需求事实出现在正文、表格、图片和追溯关系中。",
    "约束表达密集": "矛盾需跨位置join",
    "包含数值、单位、程度、范围和条件等多种约束形式。":
        "单独看每处都可能没有问题，矛盾发生在聚合之后。",
    "局部信息依赖上下文": "规则与语义并存",
    "对象指代、适用范围和条件需要结合上下文才能确定。":
        "可形式化冲突走确定性规则，无法形式化的交给NLI。",
    "关键技术： UniEX 语义抽取与核验对象构建": "关键技术：证据聚合与分层校验",
    "领域抽取模式": "证据聚合",
    "工序文本与抽取目标": "跨章节表格图片关联",
    "UniEX跨度候选": "确定性规则",
    "面向领域要素的模式化抽取": "面向可形式化冲突的模式化检测",
    "Qwen核验与纠偏": "L2 NLI残差",
    "复核抽取结果，按需补全": "复核规则未决的语义claim",
    "规则判定": "可选外部仲裁",
    "建立对应关系并行规则校验": "refute候选实例级复核",
    "上下文对应": "上下文对应",
    "建立对象间的对应关系": "建立对象间的对应关系",
    "（原文 ↔ 回答）": "（原文 ↔ 回答）",
    "基于领域知识、GJB 规范等专家知识，对数值、单位、范围等约束进行比较与判定":
        "基于领域知识、GJB规范等专家知识，对数值、单位、范围等约束进行比较与判定",
    "标签与内容一致性": "证据聚合",
    "Qwen独立识别内容": "确定性规则检测",
    "保留识别结果": "保留残差claim",
    "与待检标签比较": "与待检答案比较",
}

# Slide 7: real case (5 text + 6 images)
REPLACEMENTS[7] = {
    "相关成果": "真实案例：VIO-01 ID双登记",
}

# Slide 8: real violations (4 text + 4 images)
REPLACEMENTS[8] = {
    "相关成果": "真实违例：三类跨位置冲突",
    "语法一致性校验": "VIO-06枚举冲突 4/4\n正文5项vs表3仅4项",
    "语义一致性校验": "VIO-10追溯断裂 3/3\n表81正向vs表82逆向\nVIO-17覆盖缺口 1/1\n表80仅3.2.1-3.2.6\n真实违例集：16/17=94.1%",
}

# Slide 9: results and boundary (39 text shapes)
REPLACEMENTS[9] = {
    "逻辑一致性部分规划": "成果与边界",
    "问答内容    |    适用依据    |    上下文与领域知识":
        "91QA评测 | 17真实违例 | 06号跨文档",
    "Qwen 逻辑解析与跨文本对齐": "CascadeVerify三态判定结果",
    "分别解析来源与回答": "91QA silver评测",
    "逻辑要素对齐": "17条违例检测",
    "明确核验范围": "跨文档泛化测试",
    "因果关系核验": "确定性检出",
    "对象角色 · 关系方向 · 因果强度": "主体+规则ID+证据位置",
    "条件约束求解": "级联经济学",
    "必要条件 · 动作模态 · 分支覆盖": "成本+质量+召回",
    "工序偏序验证": "跨文档边界",
    "顺序类型 · 事件实例 · 必要先后": "06号det 0.262/cascade 0.605",
    "来源关系": "91QA结果",
    "回答关系": "级联结果",
    "原因节点": "Acc 0.9121",
    "结果节点": "16/17=94.1%",
    "方向 / 强度": "Macro-F1",
    "对应比较": "refute F1",
    "来源条件约束": "LLM调用15/83",
    "回答条件约束": "确定性8ms",
    "约束比较": "级联refute F1",
    "证据关联输出：": "边界说明：",
    "分项结论": "silver标签",
    "逻辑差异": "单文档主评测",
    "原文依据": "跨文档泛化不足",
    "事件对齐": "heldout 0.8286",
    "A": "正则文法",
    "B": "语义匹配",
    "C": "配置迁移",
    "D": "待升级",
    "偏序图验证": "跨文档边界",
    "Z3": "Z3",
}

# --- image replacement per slide ---
IMAGE_MAP: dict[int, list[Path]] = {
    1: [ROOT / "docs/srs_project/paper/figures/fig0_research_framework.png"],
    3: [ROOT / "docs/doc11/visio图/图D_特征提取与上下文关联处理流程图.png"],
    4: [ROOT / "docs/doc11/visio图/图A_特征提取与上下文关联智能体组成图.png"],
    5: [ROOT / "docs/doc11/visio图/图B_数据一致性校验智能体组成图.png"],
    6: [ROOT / "docs/doc11/visio图/图E_数据一致性校验处理流程图.png"],
    7: [ROOT / "docs/srs_project/paper/figures/fig2_violation_evolution.png"],
    8: [ROOT / "docs/srs_project/paper/figures/fig4_mutation_vs_violation.png",
        ROOT / "docs/srs_project/paper/figures/fig5_crossdoc_gap.png",
        ROOT / "docs/srs_project/paper/figures/fig2_violation_evolution.png"],
    9: [ROOT / "docs/srs_project/paper/figures/fig3_cost_quality_pareto.png"],
}


def walk(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(shape.shapes)


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


def is_logo(shape):
    return (shape.shape_type == MSO_SHAPE_TYPE.PICTURE
            and shape.top < 1524000 and shape.left > 11887200)


def replace_pictures(slide, images):
    content_pics = [s for s in walk(slide.shapes)
                    if s.shape_type == MSO_SHAPE_TYPE.PICTURE and not is_logo(s)]
    if not content_pics or not images:
        return
    for pic, img_path in zip(content_pics, images * len(content_pics)):
        if not img_path.is_file():
            continue
        with Image.open(img_path) as img:
            buf = BytesIO()
            img.convert("RGB").save(buf, format="PNG")
        left, top = pic.left, pic.top
        width, height = pic.width, pic.height
        old = pic._element
        parent = old.getparent()
        new_pic = slide.shapes.add_picture(
            BytesIO(buf.getvalue()), left, top, width=width, height=height)
        parent.replace(old, new_pic._element)


def main():
    prs = Presentation(str(REF))
    slides = list(prs.slides)[:9]
    for idx, slide in enumerate(slides, 1):
        mapping = REPLACEMENTS.get(idx, {})
        replaced = 0
        for shape in walk(slide.shapes):
            if not shape.has_text_frame:
                continue
            old = shape.text.strip()
            if old in mapping:
                set_text(shape, mapping[old])
                replaced += 1
        images = IMAGE_MAP.get(idx, [])
        replace_pictures(slide, images)
        print(f"slide {idx}: {replaced} texts replaced")

    sld_ids = prs.slides._sldIdLst
    for sld_id in list(sld_ids)[9:]:
        prs.part.drop_rel(sld_id.rId)
        sld_ids.remove(sld_id)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
