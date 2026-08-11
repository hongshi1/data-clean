"""
fill_agents.py — 在系统技术方案-yjw 副本中补齐智能体文字

补齐位置:
  1. 功能组成: 3.4.3 设计经验结构化建模、3.4.4 数据合成与增强 (占位符替换为 一段话+表)
  2. 运行逻辑: 特征提取与上下文关联 / 设计经验结构化建模 / 数据合成与增强 / 数据一致性校验
     四个智能体标题下补运行逻辑一段话(结合已画时序图)

用法: python fill_agents.py <input.docx> <output.docx>
"""
import sys
from docx import Document
from docx.shared import Pt
from copy import deepcopy


def find_para(doc, text, exact=False):
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if (t == text) if exact else (text in t):
            return i, p
    return None, None


def insert_after(doc, anchor_para, new_text, fmt_para=None):
    """在 anchor_para 之后插入一个与 fmt_para 同格式的段落"""
    new_p = deepcopy(fmt_para) if fmt_para is not None else deepcopy(anchor_para)
    # 清空 runs 只保留第一个 run 的格式
    for r in list(new_p.runs[1:]) if new_p.runs else []:
        r._element.getparent().remove(r._element)
    if new_p.runs:
        new_p.runs[0].text = new_text
    else:
        run = new_p.add_run(new_text)
        if fmt_para is not None and fmt_para.runs:
            src = fmt_para.runs[0]
            run.font.name = src.font.name
            run.font.size = src.font.size
            run.font.bold = src.font.bold
    anchor_para._p.addnext(new_p._p)
    return new_p


def insert_block_after(doc, anchor_para, lines, fmt_body, fmt_head):
    """在 anchor_para 后插入多行: lines 中 ('head'|'body', text)"""
    cur = anchor_para
    for kind, text in lines:
        fmt = fmt_head if kind == "head" else fmt_body
        cur = insert_after(doc, cur, text, fmt)
    return cur


def main(in_path, out_path):
    doc = Document(in_path)

    # 参考格式
    _, fmt_head = find_para(doc, "特征提取与上下文关联智能体", exact=True)  # 加粗标题
    _, fmt_body = find_para(doc, "特征提取与上下文关联智能体面向SRS文档")   # 正文
    _, fmt_tbl_hdr = find_para(doc, "序号")                                  # 表头加粗

    # ============ 1. 功能组成: 3.4.3 设计经验结构化建模智能体 ============
    idx, p_placeholder_343 = find_para(doc, "设计经验结构化建模智能体（一段话")
    if p_placeholder_343 is not None:
        # 替换占位符为标题
        p_placeholder_343.text = ""
        r = p_placeholder_343.add_run("设计经验结构化建模智能体")
        r.font.name = "Times"; r.font.size = Pt(12); r.font.bold = True

        lines_343 = [
            ("body", "设计经验结构化建模智能体面向科研生产领域专家经验利用率低的现状，通过设计准则抽取、经验规则形式化、知识图谱构建与模板化封装，将设计、试验、故障处置中的隐性专家经验转化为可复用、可检索、可推理的结构化知识，支撑垂域大模型微调数据集的专家知识注入。包括设计准则抽取、经验规则形式化、知识图谱构建、模板化封装、知识库管理等组件。"),
            ("body", "表 4 设计经验结构化建模智能体功能划分"),
            ("head", "序号"), ("head", "子功能名称"), ("head", "功能描述"), ("head", "优先级"),
            ("body", "1"), ("body", "设计准则抽取"), ("body", "从设计规范、SRS、评审意见中抽取设计准则与约束规则"), ("body", "高"),
            ("body", "2"), ("body", "经验规则形式化"), ("body", "将专家经验转化为结构化规则（条件-结论/约束表达式）"), ("body", "高"),
            ("body", "3"), ("body", "知识图谱构建"), ("body", "构建实体-属性-关系知识图谱，支撑知识关联与推理"), ("body", "高"),
            ("body", "4"), ("body", "模板化封装"), ("body", "将结构化知识封装为问答对、推理链等微调样本"), ("body", "中"),
            ("body", "5"), ("body", "知识库管理"), ("body", "对结构化知识进行版本管理与统一检索"), ("body", "中"),
        ]
        insert_block_after(doc, p_placeholder_343, lines_343, fmt_body, fmt_tbl_hdr)

    # ============ 2. 功能组成: 3.4.4 数据合成与增强智能体 ============
    idx, p_placeholder_344 = find_para(doc, "数据合成与增强智能体（一段话")
    if p_placeholder_344 is not None:
        p_placeholder_344.text = ""
        r = p_placeholder_344.add_run("数据合成与增强智能体")
        r.font.name = "Times"; r.font.size = Pt(12); r.font.bold = True

        lines_344 = [
            ("body", "数据合成与增强智能体面向稀缺工况、边界条件样本不足、类别不均衡的问题，基于生成式模型与领域规则，通过文本内容合成、样本增强、仿真数据生成与类别均衡化，扩充稀缺样本、增强样本多样性、完善场景覆盖度，形成满足模型泛化要求的均衡化微调数据集。包括文本内容合成、样本增强、仿真数据生成、类别均衡化、质量过滤等组件。"),
            ("body", "表 5 数据合成与增强智能体功能划分"),
            ("head", "序号"), ("head", "子功能名称"), ("head", "功能描述"), ("head", "优先级"),
            ("body", "1"), ("body", "文本内容合成"), ("body", "基于大模型与领域模板生成多样化文本微调样本"), ("body", "高"),
            ("body", "2"), ("body", "样本增强"), ("body", "通过改写、回译、噪声注入等方式增强样本多样性"), ("body", "高"),
            ("body", "3"), ("body", "仿真数据生成"), ("body", "结合仿真推演生成稀缺工况与边界条件数据"), ("body", "高"),
            ("body", "4"), ("body", "类别均衡化"), ("body", "针对类别不均衡进行过采样/欠采样平衡"), ("body", "中"),
            ("body", "5"), ("body", "质量过滤"), ("body", "对合成数据进行去重与质量过滤，剔除低质样本"), ("body", "中"),
        ]
        insert_block_after(doc, p_placeholder_344, lines_344, fmt_body, fmt_tbl_hdr)

    # ============ 3. 运行逻辑: 四个智能体各补一段话 ============
    run_logic_texts = {
        "特征提取与上下文关联智能体": (
            "上下文关联运行模式时，标准化预处理智能体完成数据的标准化转换后，可通过特征提取与上下文关联智能体启动多模态特征提取组件，完成文字、图片、表格等多模态数据的结构化解析与特征提取后，通过语义角色标注组件和跨章节实体链接组件进行语义角色标注与“同一事物”判别，并将关联结果反馈至上下文聚合组件；也可通过条目库管理组件对聚合条目进行统一管理与检索，并将条目列表输出至数据一致性校验智能体，供其发起一致性检测。图X为特征提取与上下文关联智能体信息流交互图。"
        ),
        "设计经验结构化建模智能体": (
            "经验建模运行模式时，完成多源设计文档的接入后，可通过设计经验结构化建模智能体启动设计准则抽取组件，完成设计规范、评审意见中准则与约束的抽取后，通过经验规则形式化组件和知识图谱构建组件进行规则形式化与知识关联建模，并将结构化知识反馈至模板化封装组件；也可通过知识库管理组件对结构化知识进行版本管理，并将封装后的微调样本输出至数据集。图X为设计经验结构化建模智能体信息流交互图。"
        ),
        "数据合成与增强智能体": (
            "数据合成运行模式时，完成基础样本的准备后，可通过数据合成与增强智能体启动文本内容合成组件，基于领域模板与生成模型合成多样化文本后，通过样本增强组件和仿真数据生成组件进行样本多样性增强与稀缺场景扩充，并将增强结果反馈至类别均衡化组件；也可通过质量过滤组件对合成数据进行去重与质量把关，并将均衡化样本输出至微调数据集。图X为数据合成与增强智能体信息流交互图。"
        ),
        "数据一致性校验智能体": (
            "一致性校验运行模式时，上下文关联智能体完成条目聚合后，可通过数据一致性校验智能体并行启动语法层校验组件、语义层校验组件和逻辑层校验组件，完成格式合规性、语义一致性及逻辑可满足性的检测后，通过差异判别组件进行“合理差异”与“真实矛盾”的判别，并将校验结果反馈至不一致性报告生成组件；也可由设计人员对不一致性报告进行确认，确认后发起复检。图X为数据一致性校验智能体信息流交互图。"
        ),
    }

    for title, logic_text in run_logic_texts.items():
        # 在"运行逻辑"部分找该智能体标题段(第二个出现位置)
        positions = [i for i, p in enumerate(doc.paragraphs) if p.text.strip() == title]
        if len(positions) >= 2:
            idx = positions[1]
            anchor = doc.paragraphs[idx]
            # 在该标题后插入一段话
            insert_after(doc, anchor, logic_text, fmt_body)
            print(f"[运行逻辑] {title} 已补齐")

    doc.save(out_path)
    print(f"已保存: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
