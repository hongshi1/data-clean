"""Assemble scenario-one copy using scene-three slides 1-9 as the template."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import zipfile

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

ROOT = Path(__file__).resolve().parents[1]
REF = Path(os.environ["SCENE34_PPTX"])
OUT = ROOT / "docs/srs_project/paper/scenario1_aligned_to_scene3_4.pptx"
MAP = OUT.parent / "scenario1_ppt_asset_map.md"
REPORT = OUT.parent / "scenario1_ppt_text_dump.md"
FORBIDDEN = ["工序", "压药", "炸药", "PaddleOCR", "UniEX", "Qwen", "发动机", "航空", "维护保障", "填写标题", "场景三", "场景四"]
REPLACEMENTS = []
CURRENT_PAGE = 0

ASSETS = {
    1: ["docs/srs_project/paper/figures/fig0_research_framework.png"],
    3: ["docs/doc11/visio图/图D_特征提取与上下文关联处理流程图.png"],
    4: ["docs/doc11/visio图/图A_特征提取与上下文关联智能体组成图.png"],
    5: ["docs/doc11/visio图/图B_数据一致性校验智能体组成图.png"],
    6: ["docs/doc11/visio图/图E_数据一致性校验处理流程图.png"],
    7: ["docs/srs_project/paper/figures/fig2_violation_evolution.png"],
    9: ["docs/srs_project/paper/figures/fig3_cost_quality_pareto.png", "docs/srs_project/paper/figures/fig5_crossdoc_gap.png"],
}

TITLES = {
    2: "场景一数据特点",
    3: "证据特征提取",
    4: "上下文关联",
    5: "一致性校验框架",
    6: "技术路线",
    7: "真实案例：VIO-01 ID双登记",
    8: "真实违例：三类跨位置冲突",
    9: "场景一成果、下一步与边界",
}
ORIGINAL_TITLES = {
    2: "场景三数据特点",
    3: "特征提取",
    4: "上下文关联",
    5: "一致性校验框架",
    6: "技术路线",
    7: "相关成果",
    8: "相关成果",
    9: "逻辑一致性部分规划",
}

PAGE_CONTENT = {
    2: [
        "16份真实GJB 438C SRS", "正文 / 表格 / 接口图 / 追溯与合格性表", "同一需求、接口或约束的跨位置证据",
        "证据分散", "正文、表格与图示记录同一对象的不同侧面",
        "对象难对齐", "ID、章节与表格行共同确定主体身份",
        "约束需联合比较", "枚举、追溯与覆盖关系要跨位置核对",
        "缺证不等于冲突", "未找到证据时保留NIE，不直接判矛盾",
    ],
    3: [
        "将16份GJB SRS解析为可追溯、可比较的证据对象",
        "多模态内容解析", "正文、表格、图片统一读取", "正文按章节解析", "表格保留行列及单元格", "图片保留原始位置",
        "结构与字段抽取", "形成可比较内容单元", "识别需求、接口、功能", "提取ID、名称、参数约束", "保留章节表号",
        "事实对象组织", "把分散内容归入同一对象", "关联正文与表格行", "登记图片节点和关系", "记录实体类型与位置",
        "来源追溯与核验", "支持后续关联和校验", "每条事实保留原文锚点", "可回看页码/块/行", "输出结构化证据",
    ],
    4: [
        "把分散登记聚合成同一个检测对象",
        "需求", "接口", "功能", "正文证据", "表格行", "接口图节点", "正向追溯", "逆向追溯", "合格性表",
        "统一条目：需求/接口/功能", "主体 + 值/约束 + 语义角色 + 原始位置", "支持后续TERM / PARAM / LOGIC / GJB校验",
    ],
    5: [
        "冻结证据", "Answer原子claim", "40项检测体系",
        "TERM 术语与标识", "PARAM 参数与取值", "LOGIC 逻辑约束", "GJB 规范符合性",
        "L0 NER实体层", "L1确定性规则层", "L2 NLI语义残差",
        "三态判定 / 证据定位 / 检测项ID / 判定理由",
    ],
    6: [
        "分散证据先聚合成可核验上下文，再由确定性规则处理可形式化冲突，L2 NLI处理语义残差",
        "证据聚合", "正文 / 表格 / 图片 / 追溯 → 统一证据单元",
        "确定性规则", "L0实体 + L1 ID/枚举/数值/逻辑/GJB规则",
        "L2残差NLI", "EGT三态训练；仅处理规则未决claim",
        "可选外部仲裁", "refute候选实例级复核；不是核心算法层",
    ],
    7: [
        "同一ID：PZXQ-GN-LJCGL-LJCCSH",
        "登记A：连接池配置 · DOC04 b220",
        "登记B：连接池初始化 · DOC04 b225",
        "同一ID绑定两个主体",
        "TERM-07", "id_join_registry", "refute",
        "不是ID字面命中，而是结构化注册表join发现绑定冲突",
    ],
    8: [
        "VIO-06 枚举冲突", "正文5项 vs 表3仅4项", "4/4检出",
        "VIO-10 追溯断裂", "表81正向 vs 表82逆向章节不一致", "3/3检出",
        "VIO-17 合格性覆盖缺口", "声明3.1-3.17；表80仅3.2.1-3.2.6", "1/1检出",
        "真实违例集：16/17 = 94.1%",
    ],
    9: [
        "16份真实GJB SRS · 40项校验",
        "17条真实违例中检出16条：16/17=94.1%",
        "91QA silver：Acc 0.9121 / Macro-F1 0.7212",
        "held-out test：Macro-F1 0.8286",
        "06号跨文档sound集：det 0.2619 / cascade 0.6052",
        "下一步：补人工gold · 升级跨文档语义匹配 · 证据线性化层配置化",
        "边界：silver非人工gold；真实违例集参与专家迭代；跨文档泛化仍不足",
    ],
}


def recursive_shapes(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from recursive_shapes(shape.shapes)


def text_of(shape):
    return shape.text if shape.has_text_frame else ""


def set_text(shape, value):
    if not shape.has_text_frame:
        return
    previous = shape.text
    frame = shape.text_frame
    paragraph = frame.paragraphs[0]
    if paragraph.runs:
        paragraph.runs[0].text = value
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.text = value
    for other in frame.paragraphs[1:]:
        for run in other.runs:
            run.text = ""
    if previous.strip() != value.strip():
        REPLACEMENTS.append((CURRENT_PAGE, shape.name, previous.strip(), value.strip()))


def logo(shape):
    return shape.shape_type == MSO_SHAPE_TYPE.PICTURE and shape.top < Inches(1.5) and shape.left > Inches(13)


def group_position(shape):
    x, y = shape.left, shape.top
    parent = shape._element.getparent()
    while parent is not None:
        if parent.tag.endswith("}grpSp"):
            try:
                transform = parent.grpSpPr.xfrm
                off, ext = transform.off, transform.ext
                child_off, child_ext = transform.chOff, transform.chExt
                if child_ext.cx and child_ext.cy:
                    x = off.x + (x - child_off.x) * ext.cx / child_ext.cx
                    y = off.y + (y - child_off.y) * ext.cy / child_ext.cy
            except AttributeError:
                pass
        parent = parent.getparent()
    return x, y


def replace_picture(slide, shape, path):
    buffer = BytesIO(Path(path).read_bytes())
    image_part, rid = shape.part.get_or_add_image_part(buffer)
    shape._element.blipFill.blip.rEmbed = rid


def make_evidence_card(path, title, left_label, right_label):
    image = Image.new("RGB", (1200, 620), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    title_font = ImageFont.truetype(str(font_path), 46)
    body_font = ImageFont.truetype(str(font_path), 38)
    small_font = ImageFont.truetype(str(font_path), 30)
    draw.rounded_rectangle((18, 18, 1182, 602), radius=18, outline="#175A75", width=5)
    draw.text((58, 48), title, font=title_font, fill="#12344A")
    draw.rounded_rectangle((62, 170, 535, 390), radius=12, fill="#E8F2F5", outline="#5D8999", width=3)
    draw.rounded_rectangle((665, 170, 1138, 390), radius=12, fill="#F5F0E8", outline="#9B8060", width=3)
    draw.text((95, 235), left_label, font=body_font, fill="#12344A")
    draw.text((700, 235), right_label, font=body_font, fill="#12344A")
    draw.line((540, 280, 660, 280), fill="#BD573E", width=8)
    draw.polygon([(660, 280), (630, 260), (630, 300)], fill="#BD573E")
    draw.text((65, 465), "来源位置保留 · 双侧证据join · 可回溯判定", font=small_font, fill="#385663")
    image.save(path)


def fit_text(slide, shape, value, font_pt=12):
    set_text(shape, value)
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.name = "Microsoft YaHei"
            run.font.size = Pt(font_pt)
    shape.text_frame.word_wrap = True


def new_text(slide, box, value, font_pt=12, bold=False):
    x, y, w, h = box
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    shape.text_frame.word_wrap = True
    shape.text_frame.margin_left = Inches(0.05)
    shape.text_frame.margin_right = Inches(0.05)
    run = shape.text_frame.paragraphs[0].add_run()
    run.text = value
    run.font.name = "Microsoft YaHei"
    run.font.size = Pt(font_pt)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(25, 49, 73)
    return shape


def replace_content(slide, page, values):
    shapes = [s for s in recursive_shapes(slide.shapes) if s.has_text_frame and text_of(s).strip()]
    if page == 1:
        cover = sorted(shapes, key=lambda s: group_position(s)[1])
        for shape in cover:
            set_text(shape, "")
        if len(cover) >= 2:
            fit_text(slide, cover[0], "第一章", 28)
            fit_text(slide, cover[1], "场景一\nGJB SRS上下文关联与一致性校验", 32)
        return

    title = next((s for s in shapes if text_of(s).strip() == ORIGINAL_TITLES.get(page)), None)
    nav = next((s for s in shapes if text_of(s).strip() in {"01", "02", "03", "04", "05", "06", "07"} and group_position(s)[1] < Inches(1.5)), None)
    if title:
        fit_text(slide, title, TITLES[page], 22)
    if nav and page < 9:
        set_text(nav, f"{page - 1:02d}")

    body = [s for s in shapes if s is not title and s is not nav]
    body = [s for s in body if text_of(s).strip() not in {"›", "1", "2", "3", "4", "…"}]
    if page == 4:
        for shape in shapes:
            if text_of(shape).strip() in {"1", "2", "3", "9", "10", "11", "…"}:
                set_text(shape, "")
    for shape in body:
        set_text(shape, "")

    if page == 2:
        assign_fixed(slide, body, values, [
            (1.4, 1.9, 4.2, 0.35), (5.5, 1.9, 5.2, 0.35), (2.3, 2.38, 11.0, 0.32),
            (1.25, 4.5, 3.5, 0.34), (1.25, 4.88, 3.5, 0.72), (5.15, 4.5, 3.5, 0.34), (5.15, 4.88, 3.5, 0.72),
            (9.1, 4.5, 3.5, 0.34), (9.1, 4.88, 3.5, 0.72), (12.8, 4.5, 2.9, 0.34), (12.8, 4.88, 2.9, 0.72),
        ], font_pt=14)
        return

    if page == 3:
        assign_fixed(slide, body, values, [
            (1.6,1.9,13.5,.42),
            (1.6,3.1,2.45,.35),(1.6,3.48,2.45,.45),(1.0,4.05,2.9,.34),(1.0,4.48,2.9,.45),(1.0,5.0,2.9,.4),
            (4.9,3.1,2.45,.35),(4.9,3.48,2.45,.45),(4.5,4.05,2.9,.34),(4.5,4.48,2.9,.45),(4.5,5.0,2.9,.4),
            (8.9,3.1,2.45,.35),(8.9,3.48,2.45,.45),(8.5,4.05,2.9,.34),(8.5,4.48,2.9,.45),(8.5,5.0,2.9,.4),
            (12.8,3.1,2.7,.35),(12.8,3.48,2.7,.45),(12.3,4.05,3.0,.34),(12.3,4.48,3.0,.45),(12.3,5.0,3.0,.4),
        ], font_pt=12)
        return

    if page == 4:
        assign_fixed(slide, body, values, [
            (1.6,1.9,13.5,.4),(1.5,2.8,1.55,.4),(3.4,2.8,1.55,.4),(5.3,2.8,1.55,.4),
            (1.2,4.0,1.9,.35),(3.1,4.0,1.8,.35),(5.0,4.0,2.2,.35),(7.3,4.0,1.8,.35),(9.3,4.0,1.8,.35),(11.2,4.0,2.0,.35),
            (2.0,5.3,11.8,.38),(2.0,5.75,11.8,.38),(2.0,6.2,11.8,.38),
        ], font_pt=14)
        return

    if page == 5:
        assign_fixed(slide, body, values, [
            (2.1,2.2,3.1,.35),(6.2,2.2,3.1,.35),(10.2,2.2,3.2,.35),
            (1.7,3.2,3.1,.45),(5.4,3.2,3.1,.45),(9.0,3.2,3.1,.45),(12.5,3.2,3.1,.45),
            (1.6,5.5,3.1,.4),(5.3,5.5,3.1,.4),(9.0,5.5,3.1,.4),(1.8,7.2,12.0,.42),
        ], font_pt=14)
        return

    if page == 6:
        assign_fixed(slide, body, values, [
            (1.6,1.9,13.8,.48),
            (4.8,3.3,2.4,.38),(4.5,3.8,2.9,.65),
            (7.9,3.3,2.4,.38),(7.6,3.8,2.9,.65),
            (10.9,3.3,2.4,.38),(10.6,3.8,2.9,.65),
            (13.4,3.3,2.2,.38),(13.1,3.8,2.5,.65),
        ], font_pt=13)
        return

    if page == 7:
        assign_fixed(slide, body, values, [
            (2.0,3.0,6.8,.42),(2.0,3.55,7.2,.38),(2.0,4.0,7.2,.38),(2.0,4.45,7.2,.38),
            (10.6,2.5,2.8,.4),(10.6,3.2,3.0,.4),(10.6,3.9,2.2,.4),(2.8,7.0,10.5,.5),
        ], font_pt=14)
        return

    if page == 8:
        cards = [
            [(1.65,2.1,2.55,.4),(1.65,2.6,2.55,.68),(1.65,3.35,2.55,.38)],
            [(6.5,2.1,2.6,.4),(6.5,2.6,2.6,.68),(6.5,3.35,2.6,.38)],
            [(11.2,2.1,3.45,.4),(11.2,2.6,3.45,.68),(11.2,3.35,3.45,.38)],
        ]
        for index, shape in enumerate(body):
            if index < 9:
                value = values[index]
                box = cards[index // 3][index % 3]
                fit_text(slide, shape, value, 12)
                shape.left, shape.top = Inches(box[0]), Inches(box[1])
                shape.width, shape.height = Inches(box[2]), Inches(box[3])
        for index in range(len(body), 9):
            box = cards[index // 3][index % 3]
            new_text(slide, box, values[index], 12, index % 3 == 0)
        new_text(slide, (3.0,7.9,10.0,.4), values[9], 17, True)
        return

    if page == 9:
        assign_fixed(slide, body, values, [
            (5.0,2.05,7.0,.42),(1.8,2.75,13.0,.42),(1.6,3.55,4.5,.42),(6.2,3.55,4.6,.42),(11.0,3.55,4.5,.42),
            (1.8,4.3,13.5,.42),(1.8,5.25,13.5,.58),
        ], font_pt=14)


def assign_fixed(slide, shapes, values, boxes, font_pt=12):
    for index, value in enumerate(values):
        if index < len(shapes):
            fit_text(slide, shapes[index], value, font_pt)
        elif index < len(boxes):
            new_text(slide, boxes[index], value, font_pt, index % 3 == 0)


def content_pictures(slide):
    return [s for s in recursive_shapes(slide.shapes) if s.shape_type == MSO_SHAPE_TYPE.PICTURE and not logo(s)]


def replace_assets(slide, page, generated):
    slots = content_pictures(slide)
    if page == 8:
        evidence = [
            ("VIO-06 枚举冲突", "正文 5 项", "表3 4 行"),
            ("VIO-10 追溯断裂", "表81 正向", "表82 逆向"),
            ("VIO-17 覆盖缺口", "声明 3.1-3.17", "表80 3.2.1-3.2.6"),
        ]
        for index, (slot, labels) in enumerate(zip(slots, evidence)):
            path = generated / f"vio_{index}.png"
            make_evidence_card(path, *labels)
            replace_picture(slide, slot, path)
        return
    paths = [ROOT / item for item in ASSETS.get(page, [])]
    paths = [path for path in paths if path.is_file()]
    for index, slot in enumerate(slots):
        if paths:
            replace_picture(slide, slot, paths[index % len(paths)])
    if page == 1 and slots and paths:
        replace_picture(slide, slots[0], paths[0])


def make_asset_map(template_counts, output_counts):
    lines = ["# 场景一PPT逐页素材与槽位映射", "", "模板：参考PPT场景三第1-9页；保持原页面尺寸、背景、分组和原有shape版式。", ""]
    for page in range(1, 10):
        asset_names = ASSETS.get(page, [])
        if page == 8:
            asset_names = ["生成证据卡：正文5项vs表3 4行", "生成证据卡：表81正向vs表82逆向", "生成证据卡：声明3.1-3.17 vs 表80 3.2.1-3.2.6"]
        actual = [f"{name}: {old or '[空shape]'} → {new}" for changed_page, name, old, new in REPLACEMENTS if new and page == changed_page]
        lines.extend([
            f"## 第{page}页", "- 替换shape文本：按模板页标题、导航shape与原文shape位置映射；分组shape递归遍历。",
            f"- 正文图片槽：模板 {template_counts[page]}，输出 {output_counts[page]}。",
            f"- 实际替换shape：{'；'.join(actual) if actual else '无'}",
            f"- 素材：{'；'.join(asset_names) if asset_names else '保留模板原图'}", "",
        ])
    MAP.write_text("\n".join(lines), encoding="utf-8")


def validate(prs, reference):
    assert len(prs.slides) == 9
    assert (prs.slide_width, prs.slide_height) == (reference.slide_width, reference.slide_height)
    texts = [[text_of(s) for s in recursive_shapes(slide.shapes) if s.has_text_frame] for slide in prs.slides]
    full_text = "\n".join(value for page in texts for value in page)
    assert not [term for term in FORBIDDEN if term in full_text]
    must = ["第一章", "场景一", "GJB", "上下文", "一致性", "TERM", "PARAM", "LOGIC", "16", "17"]
    assert not [term for term in must if term not in full_text]
    page_words = {
        1: ["第一章", "场景一", "GJB SRS上下文关联与一致性校验"],
        2: ["16份真实GJB 438C SRS", "证据分散", "对象难对齐", "约束需联合比较", "缺证不等于冲突"],
        3: ["多模态内容解析", "结构与字段抽取", "事实对象组织", "来源追溯与核验"],
        4: ["需求", "接口", "功能", "正文证据", "表格行", "接口图节点", "正向追溯", "逆向追溯", "合格性表"],
        5: ["冻结证据", "Answer原子claim", "40项检测体系", "TERM", "PARAM", "LOGIC", "GJB", "L0", "L1", "L2"],
        6: ["证据聚合", "确定性规则", "L2残差NLI", "可选外部仲裁"],
        7: ["PZXQ-GN-LJCGL-LJCCSH", "DOC04 b220", "DOC04 b225", "TERM-07", "id_join_registry", "refute"],
        8: ["VIO-06", "4/4检出", "VIO-10", "3/3检出", "VIO-17", "1/1检出", "16/17", "94.1%"],
        9: ["40项校验", "16/17=94.1%", "0.9121", "0.7212", "0.8286", "0.2619", "0.6052", "补人工gold", "边界"],
    }
    for page, tokens in page_words.items():
        text = "\n".join(texts[page - 1])
        assert not [token for token in tokens if token not in text], f"page {page} text incomplete"
    counts = {}
    original_counts = {}
    for page in range(1, 10):
        counts[page] = len(content_pictures(prs.slides[page - 1]))
        original_counts[page] = len(content_pictures(reference.slides[page - 1]))
        assert counts[page] >= original_counts[page]
    assert counts[8] >= 3 and len(content_pictures(prs.slides[7])) == 3
    return texts, original_counts, counts


def write_text_dump(texts, original_counts, output_counts):
    lines = ["# PPT递归文本Dump", "", f"页面尺寸：{Presentation(str(OUT)).slide_width} × {Presentation(str(OUT)).slide_height} EMU", ""]
    for page, values in enumerate(texts, 1):
        lines.append(f"## 第{page}页（图片槽：模板{original_counts[page]} / 输出{output_counts[page]}）")
        lines.extend(f"- {value.replace(chr(10), ' / ')}" for value in values if value.strip())
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main():
    global CURRENT_PAGE
    reference = Presentation(str(REF))
    prs = Presentation(str(REF))
    generated = OUT.parent / ".scenario1_generated_evidence"
    generated.mkdir(exist_ok=True)
    for page, slide in enumerate(list(prs.slides)[:9], 1):
        CURRENT_PAGE = page
        replace_content(slide, page, PAGE_CONTENT.get(page, []))
        replace_assets(slide, page, generated)
    for slide_id in list(prs.slides._sldIdLst)[9:]:
        prs.part.drop_rel(slide_id.rId)
        prs.slides._sldIdLst.remove(slide_id)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    result = Presentation(str(OUT))
    texts, originals, outputs = validate(result, reference)
    make_asset_map(originals, outputs)
    write_text_dump(texts, originals, outputs)
    with zipfile.ZipFile(OUT) as package:
        assert any(name.startswith("ppt/media/") for name in package.namelist())


if __name__ == "__main__":
    main()
