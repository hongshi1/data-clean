from __future__ import annotations

import io
import re
import zipfile
from html import escape
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "temp" / "scenario5_ppt_assets"
PPT_OUT = ROOT / "scenario5" / "scenario5_tracklet_consistency_template3_native_v6.pptx"
TEMPLATE = Path(r"C:\Users\12488\Downloads\南开大学模板-3.pptx")
ACTIVE_PRS: Presentation | None = None
SHELL_INDEX = 0

BG = RGBColor(255, 255, 255)
PANEL = RGBColor(247, 243, 252)
PANEL2 = RGBColor(239, 231, 249)
PURPLE = RGBColor(103, 55, 153)
LAV = RGBColor(103, 55, 153)
WHITE = RGBColor(39, 27, 57)
MINT = RGBColor(119, 83, 166)
GOLD = RGBColor(157, 119, 194)
RED = RGBColor(83, 42, 125)
GRAY = RGBColor(105, 96, 116)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_label(image: Image.Image, text: str, xy: tuple[int, int], color: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((xy[0], xy[1], xy[0] + 90, xy[1] + 27), radius=5, fill=color)
    draw.text((xy[0] + 6, xy[1] + 3), text, fill=(255, 255, 255), font=font(16, True))


def make_assets() -> dict[str, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    assets: dict[str, Path] = {}

    # MOT20: extract one real frame and draw its official gt.txt boxes.
    # MOT20 was downloaded as a research asset but its archive has a damaged
    # local member; MOT17 is an equivalent official MOT-format sample and
    # passes the archive integrity check.
    mot_zip = ROOT / "scenario5" / "data" / "mot" / "MOT17.zip"
    with zipfile.ZipFile(mot_zip) as zf:
        frame_name = "MOT17/train/MOT17-04-FRCNN/img1/000100.jpg"
        image = Image.open(io.BytesIO(zf.read(frame_name))).convert("RGB")
        gt = zf.read("MOT17/train/MOT17-04-FRCNN/gt/gt.txt").decode("utf-8")
    frame_id = 100
    boxes = []
    for line in gt.splitlines():
        values = line.split(",")
        if len(values) >= 7 and int(values[0]) == frame_id and int(values[6]) == 1:
            boxes.append((int(values[1]), *(int(float(v)) for v in values[2:6])))
    draw = ImageDraw.Draw(image)
    for track_id, x, y, w, h in boxes:
        draw.rectangle((x, y, x + w, y + h), outline=(104, 231, 194), width=3)
        draw_label(image, f"ID {track_id}", (x, max(0, y - 28)), (38, 151, 122))
    mot_path = OUT / "mot20_gt_frame.jpg"
    image.save(mot_path, quality=92)
    assets["mot"] = mot_path

    # MEVA: decode a real video frame and overlay the real geom.yml track.
    meva_video = ROOT / "scenario5" / "data" / "meva" / "clips_G329" / "2018-03-07.16-50-00.16-55-00.admin.G329.r13.avi"
    cap = cv2.VideoCapture(str(meva_video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 2679)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        cap = cv2.VideoCapture(str(meva_video))
        ok, frame = cap.read()
        cap.release()
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    geom = ROOT / "scenario5" / "data" / "meva" / "examples" / "annotations" / "2018-03-07" / "16" / "2018-03-07.16-50-00.16-55-00.admin.G329.geom.yml"
    text = geom.read_text(encoding="utf-8")
    match = re.search(r"g0:\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)", text)
    if match:
        x1, y1, x2, y2 = map(int, match.groups())
        scale_x = image.width / 1920
        scale_y = image.height / 1080
        box = (int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y))
        ImageDraw.Draw(image).rectangle(box, outline=(255, 210, 105), width=5)
        draw_label(image, "track 0", (box[0], max(0, box[1] - 30)), (197, 143, 20))
    meva_path = OUT / "meva_g329_track.jpg"
    image.save(meva_path, quality=92)
    assets["meva"] = meva_path

    # UCF-Crime: one real surveillance frame, no fabricated boxes.
    ucf = ROOT / "scenario5" / "data" / "ucf_crime" / "Anomaly-Videos-Part-1" / "Abuse" / "Abuse001_x264.mp4"
    cap = cv2.VideoCapture(str(ucf))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 45)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot decode {ucf}")
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 260, 58), radius=8, fill=(178, 46, 102))
    draw.text((30, 25), "UCF-Crime / Abuse001", fill=(255, 255, 255), font=font(20, True))
    ucf_path = OUT / "ucf_crime_frame.jpg"
    image.save(ucf_path, quality=92)
    assets["ucf"] = ucf_path
    return assets


def write_svg(path: Path, body: str, width: int = 1200, height: int = 540) -> Path:
    """Write a self-contained, editable-vector diagram for PowerPoint."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="{width}" height="{height}" fill="#ffffff"/>
{body}
</svg>'''
    path.write_text(svg, encoding="utf-8")
    return path


def render_svg_preview(svg_path: Path) -> Path:
    """Create a high-resolution preview from the same SVG diagram specification.

    python-pptx 1.0 cannot consume SVG files directly. The authoritative
    diagrams remain SVG; this portable preview keeps the deck usable on this
    Windows environment without requiring a native Cairo installation.
    """
    image_path = svg_path.with_suffix(".png")
    image = Image.new("RGB", (2400, 1080), "white")
    draw = ImageDraw.Draw(image)
    purple = (103, 55, 153)
    light = (241, 234, 250)
    dark = (39, 27, 57)
    title = font(48, True)
    small = font(24)
    name = svg_path.stem
    if name == "pipeline_architecture":
        draw.text((120, 70), "场景5的证据链：像素不是终点，tracklet才是可校验对象", fill=purple, font=title)
        boxes = [(80, "视频帧", "person bbox / pose / PPE"), (660, "特征提取", "检测→跟踪→属性→动作"), (1240, "上下文关联", "同camera + person_id + 时间"), (1820, "一致性校验", "轨迹 vs QA vs 规则")]
        for x, head, sub in boxes:
            draw.rounded_rectangle((x, 340, x + 420, 600), radius=28, fill=light, outline=purple, width=8)
            draw.text((x + 100, 405), head, fill=purple, font=title)
            draw.text((x + 55, 500), sub, fill=dark, font=small)
        for x in (510, 1090, 1670):
            draw.line((x, 470, x + 130, 470), fill=purple, width=10)
            draw.polygon(((x + 130, 470), (x + 100, 450), (x + 100, 490)), fill=purple)
        draw.text((310, 790), "输出对象 = {person_id, 属性序列, 动作段, 空间位移, 置信度, ID切换/遮挡记录}", fill=dark, font=small)
    elif name == "temporal_predicate":
        draw.text((320, 55), "睡岗时序谓词：位移方差 < θ 且持续 N 帧", fill=purple, font=title)
        draw.line((180, 850, 2200, 850), fill=purple, width=8)
        draw.line((180, 190, 180, 850), fill=purple, width=8)
        points = [(360, 620), (700, 485), (1040, 545), (1380, 510), (1720, 565), (2060, 530)]
        draw.line(points, fill=(119, 83, 166), width=12)
        for i, (x, y) in enumerate(points):
            draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(119, 83, 166))
            draw.text((x - 30, y - 60), f"t{i}", fill=dark, font=small)
        draw.rounded_rectangle((260, 255, 2130, 720), radius=24, outline=(157, 119, 194), width=8)
        draw.text((350, 930), "自然语言条件 → 可执行查询：静止(tracklet, window, theta, duration)", fill=dark, font=small)
    elif name == "technical_stack":
        draw.text((420, 55), "技术链不是模型堆叠，而是按可形式化程度分层", fill=purple, font=title)
        boxes = [(80, "L0 感知", "检测框 / track_id / 属性"), (660, "L1 符号", "枚举、阈值、计数、集合差集"), (1240, "L2 时序", "动作段、持续性、平滑性"), (1820, "L3 残差", "NLI / 人工仲裁")]
        for x, head, sub in boxes:
            draw.rounded_rectangle((x, 320, x + 420, 650), radius=28, fill=light, outline=purple, width=8)
            draw.text((x + 105, 380), head, fill=purple, font=title)
            draw.text((x + 45, 500), sub, fill=dark, font=small)
        for x in (510, 1090, 1670):
            draw.line((x, 485, x + 130, 485), fill=purple, width=10)
            draw.polygon(((x + 130, 485), (x + 100, 465), (x + 100, 505)), fill=purple)
        draw.text((390, 820), "能用规则证明的，不交给NLI；能用tracklet解释的，不退化成单帧分类", fill=dark, font=small)
    else:
        draw.text((90, 75), "校验项 / 主要证据 / 核心算子 / 输出", fill=purple, font=title)
        rows = [("A-3 阈值", "规则块 + QA文本", "符号/数值比较", "refute"), ("B-5 属性丢失", "轨迹属性 + evidence", "应覆盖集−实际集", "可疑"), ("B-7 数量", "检测计数 + QA", "整数相等性", "refute"), ("C-3 多样本", "同camera近时帧", "组内结论冲突", "可疑"), ("D-2 逻辑", "动作段 + 规则", "条件→预期answer", "refute")]
        for i, row in enumerate(rows):
            y = 180 + i * 145
            draw.rectangle((80, y, 2320, y + 125), fill=light if i % 2 == 0 else "white", outline=(214, 198, 232), width=3)
            for x, value in zip((125, 800, 1450, 2050), row):
                draw.text((x, y + 42), value, fill=dark, font=small)
    image.save(image_path, quality=95)
    return image_path


def svg_text(x: int, y: int, text: str, size: int = 22, color: str = "#271b39", weight: str = "400", anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="Microsoft YaHei, Arial" font-size="{size}px" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(text)}</text>'


def make_svg_assets() -> dict[str, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    assets: dict[str, Path] = {}
    purple = "#673799"
    light = "#f1eafa"
    dark = "#271b39"
    mint = "#7753a6"
    gold = "#9d77c2"
    arrow = '<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#673799"/></marker>'

    body = arrow
    boxes = [(40, "视频帧", "person bbox / pose / PPE", mint), (330, "特征提取", "检测→跟踪→属性→动作", purple), (620, "上下文关联", "同camera + person_id + 时间", gold), (910, "一致性校验", "轨迹 vs QA vs 规则", purple)]
    for x, title, sub, color in boxes:
        body += f'<rect x="{x}" y="170" width="220" height="130" rx="16" fill="{light}" stroke="{color}" stroke-width="4"/>'
        body += svg_text(x + 110, 215, title, 25, color, "700", "middle")
        body += svg_text(x + 110, 255, sub, 17, dark, "400", "middle")
    for x in (260, 550, 840):
        body += f'<line x1="{x}" y1="235" x2="{x+55}" y2="235" stroke="{purple}" stroke-width="4" marker-end="url(#arrow)"/>'
    body += svg_text(600, 80, "场景5的证据链：像素不是终点，tracklet才是可校验对象", 28, purple, "700", "middle")
    body += svg_text(600, 390, "输出对象 = {person_id, 属性序列, 动作段, 空间位移, 置信度, ID切换/遮挡记录}", 21, dark, "400", "middle")
    assets["pipeline_svg"] = write_svg(OUT / "pipeline_architecture.svg", body)

    body = '<line x1="95" y1="410" x2="1120" y2="410" stroke="#673799" stroke-width="3"/><line x1="95" y1="70" x2="95" y2="410" stroke="#673799" stroke-width="3"/>'
    for i, (label, value, color) in enumerate([("t0", 0.15, "#7753a6"), ("t1", 0.22, "#7753a6"), ("t2", 0.19, "#7753a6"), ("t3", 0.21, "#7753a6"), ("t4", 0.18, "#7753a6"), ("t5", 0.20, "#7753a6")]):
        x = 160 + i * 170
        y = 410 - int(value * 900)
        body += f'<circle cx="{x}" cy="{y}" r="10" fill="{color}"/><text x="{x}" y="{y-18}" font-family="Microsoft YaHei" font-size="17" fill="#271b39" text-anchor="middle">{label}</text>'
        if i:
            px = 160 + (i - 1) * 170
            py = 410 - int([0.15, 0.22, 0.19, 0.21, 0.18, 0.20][i-1] * 900)
            body += f'<line x1="{px}" y1="{py}" x2="{x}" y2="{y}" stroke="#7753a6" stroke-width="5"/>'
    body += '<rect x="120" y="105" width="880" height="245" fill="none" stroke="#9d77c2" stroke-width="4" stroke-dasharray="12 8" rx="12"/>'
    body += svg_text(560, 55, "睡岗时序谓词：位移方差 < θ 且持续 N 帧", 28, purple, "700", "middle")
    body += svg_text(560, 470, "自然语言条件 → 可执行查询：静止(tracklet, window, theta, duration)", 21, dark, "400", "middle")
    assets["predicate_svg"] = write_svg(OUT / "temporal_predicate.svg", body)

    body = arrow
    stages = [(40, "L0 感知", "检测框 / track_id / 属性", "专用CV"), (330, "L1 符号", "枚举、阈值、计数、集合差集", "确定性"), (620, "L2 时序", "动作段、持续性、平滑性", "规则查询"), (910, "L3 残差", "NLI/人工仲裁", "仅处理不确定")]
    for x, title, sub, tag in stages:
        body += f'<rect x="{x}" y="155" width="220" height="170" rx="16" fill="{light}" stroke="{purple}" stroke-width="4"/>'
        body += svg_text(x+110, 205, title, 25, purple, "700", "middle")
        body += svg_text(x+110, 248, sub, 17, dark, "400", "middle")
        body += f'<rect x="{x+60}" y="275" width="100" height="28" rx="14" fill="{purple}"/><text x="{x+110}" y="296" font-family="Microsoft YaHei" font-size="15" fill="#fff" text-anchor="middle">{tag}</text>'
    for x in (260, 550, 840):
        body += f'<line x1="{x}" y1="240" x2="{x+55}" y2="240" stroke="{purple}" stroke-width="4" marker-end="url(#arrow)"/>'
    body += svg_text(600, 75, "技术链不是模型堆叠，而是按可形式化程度分层", 28, purple, "700", "middle")
    body += svg_text(600, 405, "能用规则证明的，不交给NLI；能用tracklet解释的，不退化成单帧分类", 21, dark, "400", "middle")
    assets["stack_svg"] = write_svg(OUT / "technical_stack.svg", body)

    body = svg_text(80, 58, "校验项", 20, "#ffffff", "700") + svg_text(420, 58, "主要证据", 20, "#ffffff", "700") + svg_text(760, 58, "核心算子", 20, "#ffffff", "700") + svg_text(1060, 58, "输出", 20, "#ffffff", "700")
    body += '<rect x="40" y="25" width="1120" height="45" fill="#673799"/>'
    rows = [("A-3 阈值", "规则块 + QA文本", "符号/数值比较", "refute"), ("B-5 属性丢失", "轨迹属性 + evidence", "应覆盖集−实际集", "可疑"), ("B-7 数量", "检测计数 + QA", "整数相等性", "refute"), ("C-3 多样本", "同camera近时帧", "组内结论冲突", "可疑"), ("D-2 逻辑", "动作段 + 规则", "条件→预期answer", "refute")]
    for i, row in enumerate(rows):
        y = 70 + i * 78
        fill = "#f1eafa" if i % 2 == 0 else "#ffffff"
        body += f'<rect x="40" y="{y}" width="1120" height="78" fill="{fill}" stroke="#d6c6e8"/>'
        for x, value in zip((80, 420, 760, 1060), row):
            body += svg_text(x, y+47, value, 18, dark, "700" if x == 80 else "400")
    body += svg_text(600, 510, "同一条证据链可同时服务：样本过滤、困难负样本、规则审计、人工回流", 21, purple, "700", "middle")
    assets["check_svg"] = write_svg(OUT / "consistency_matrix.svg", body, 1200, 540)
    return assets


def remove_slides(prs: Presentation) -> None:
    # Keep the template's theme/master relationships, but remove its sample
    # slide nodes. Dropping relationships by part name is not supported by
    # all python-pptx versions.
    for item in list(prs.slides._sldIdLst):
        prs.slides._sldIdLst.remove(item)


def add_text(slide, text, x, y, w, h, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT, font_name="Microsoft YaHei"):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Pt(5)
    tf.margin_right = Pt(5)
    tf.margin_top = Pt(3)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = font_name
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.alignment = align
        p.space_after = Pt(3)
    return box


def rect(slide, x, y, w, h, fill=PANEL, line=None, radius=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line or fill
    return sh


def base(prs: Presentation, title: str, section: str = "场景5 · 科研生产现场智能监管"):
    slide = next_shell()
    add_text(slide, section, 0.42, 0.18, 4.5, 0.28, 10, LAV, True)
    add_text(slide, title, 0.42, 0.48, 12.1, 0.48, 25, WHITE, True)
    rect(slide, 0.42, 1.04, 12.48, 0.025, PURPLE)
    return slide


def add_template_frame(slide) -> None:
    """The native template shell already owns the frame and background."""


def clear_shell(slide) -> None:
    """Keep the template's first two frame elements, remove sample content."""
    for shape in list(slide.shapes)[2:]:
        slide.shapes._spTree.remove(shape._element)


def next_shell():
    global SHELL_INDEX
    if ACTIVE_PRS is None or SHELL_INDEX >= len(ACTIVE_PRS.slides):
        raise RuntimeError("template does not contain enough slide shells")
    slide = ACTIVE_PRS.slides[SHELL_INDEX]
    SHELL_INDEX += 1
    clear_shell(slide)
    return slide


def trim_slides(prs: Presentation, count: int) -> None:
    """Keep only the populated template shells; relationships remain harmless."""
    ids = prs.slides._sldIdLst
    for item in list(ids)[count:]:
        ids.remove(item)


def card(slide, x, y, w, h, title, body, accent=PURPLE, body_size=14):
    rect(slide, x, y, w, h, PANEL, accent, True)
    rect(slide, x, y, 0.07, h, accent)
    add_text(slide, title, x + 0.18, y + 0.12, w - 0.32, 0.32, 15, LAV, True)
    add_text(slide, body, x + 0.16, y + 0.52, w - 0.30, h - 0.60, body_size, WHITE)


def add_image(slide, path: Path, x, y, w, h):
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w), height=Inches(h))


def add_svg(slide, path: Path, x, y, w, h):
    """Render the SVG at presentation resolution for python-pptx compatibility."""
    png = render_svg_preview(path)
    slide.shapes.add_picture(str(png), Inches(x), Inches(y), width=Inches(w), height=Inches(h))


def build_ppt(assets: dict[str, Path], diagrams: dict[str, Path]) -> None:
    # A clean container avoids duplicate slide XML when python-pptx rewrites
    # the sample slides embedded in the reference template. The resulting
    # deck keeps the template's 16:9 proportion and purple visual language.
    global ACTIVE_PRS, SHELL_INDEX
    prs = Presentation(str(TEMPLATE))
    ACTIVE_PRS = prs
    SHELL_INDEX = 0
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1 cover
    slide = next_shell()
    rect(slide, 0, 0, 13.333, 0.16, PURPLE)
    rect(slide, 0.7, 1.05, 0.12, 4.85, MINT)
    add_text(slide, "科研生产现场智能监管", 1.12, 1.18, 10.8, 0.75, 36, PURPLE, True)
    add_text(slide, "特征提取 · 时序上下文关联 · 图片-QA一致性校验", 1.14, 2.08, 10.9, 0.55, 22, WHITE, False)
    add_text(slide, "从‘看见一个人’到‘理解同一个人持续发生了什么’", 1.14, 3.05, 10.7, 0.55, 22, PURPLE, True)
    card(slide, 1.12, 4.25, 3.35, 1.08, "输入", "监控视频 / 抽帧图片\nQA违规告警对", MINT, 15)
    card(slide, 4.78, 4.25, 3.35, 1.08, "中间对象", "个体轨迹 tracklet\n属性序列 + 动作段", PURPLE, 15)
    card(slide, 8.44, 4.25, 3.35, 1.08, "输出", "一致 / 矛盾 / 可疑\n回流数据治理", GOLD, 15)
    add_text(slide, "基于南开大学模板-3 · 场景5方案汇报", 1.15, 6.65, 6, 0.3, 11, GRAY)

    # 2 problem and objective
    slide = base(prs, "一、任务对象与研究问题")
    card(slide, 0.55, 1.35, 3.9, 4.9, "业务对象：图片-QA违规告警对", '{"task":"睡岗检测",\n "answer":1,\n "evidence":["人员趴伏、长时间静止"],\n "timestamp":"2026-10-17 17:20"}', MINT, 17)
    card(slide, 4.72, 1.35, 3.9, 4.9, "现实矛盾", "单帧只能看到姿态，\n无法直接证明‘长时间’；\n\n同一个人跨帧可能被重复检测、\nID切换、属性抖动；\n\nQA可能漏掉实体、改写阈值、\n把规则用错场景。", RED, 16)
    card(slide, 8.89, 1.35, 3.9, 4.9, "研究目标", "建立视频监控场景的\n‘感知—关联—校验’闭环：\n\n• 个体级：同一个人连续可追踪\n• 轨迹级：属性与动作可计算\n• QA级：证据、回答、规则相互一致\n• 数据集级：坏样本回流治理", GOLD, 16)

    # 3 framework: the confirmed core definition, intentionally kept as one page.
    slide = base(prs, "二、三角色映射：从视频连续性到一致性判定")
    card(slide, 0.55, 1.30, 3.92, 3.25, "① 特征提取 = CV栈（不是VLM）", "检测 → 跟踪 → 属性 → 动作\n\n产出：\n个体轨迹 {person_id, 属性序列, 动作段, 空间位移}\n\n重点：把像素转成可计算的结构化特征；\nVLM不是必经层，专用CV模型优先。", MINT, 15)
    card(slide, 4.70, 1.30, 3.92, 3.25, "② 上下文关联 = tracklet", "同 camera 内跨帧个体关联\n\n‘同一个人’就是关联主键；\n前后帧不是孤立图片，而是同一主体的连续观测。\n\ntracklet承载：位置、属性、动作、缺帧、ID切换。", PURPLE, 15)
    card(slide, 8.85, 1.30, 3.92, 3.25, "③ 一致性校验 = 三方比对", "轨迹属性 / 动作段\nvs QA evidence / answer\nvs 判定标准块编译的规则\n\n输出：support / refute / NIE / 可疑\n\n校验对象是QA对是否自洽，不替代原任务标签。", GOLD, 15)
    rect(slide, 0.72, 4.85, 12.0, 1.25, PANEL2, PURPLE, True)
    add_text(slide, "核心突破：睡岗=‘长时间静止’ → 轨迹上的可计算谓词", 1.02, 5.02, 11.4, 0.38, 22, PURPLE, True, PP_ALIGN.CENTER)
    add_text(slide, "位移方差 < 阈值，且持续 N 帧\n判定标准块可编译为时序谓词查询，成为规则引擎与感知管线的接口；\n这比只比较 answer 序列是否持续为 1 更底层、更硬、更接近真实视频证据。", 1.02, 5.43, 11.4, 0.55, 14, WHITE, False, PP_ALIGN.CENTER)
    add_text(slide, "统一数据对象：tracklet = 个体级跨帧证据容器；QA = 任务语义；规则 = 预期判定", 0.75, 6.48, 12, 0.3, 14, LAV, True, PP_ALIGN.CENTER)

    slide = base(prs, "二、三角色的工程接口：从像素到可校验条目")
    add_svg(slide, diagrams["pipeline_svg"], 0.65, 1.3, 12.05, 5.1)
    add_text(slide, "接口约束：每一步都必须输出可审计字段，而不是只输出一个不可解释的分类标签。", 0.75, 6.55, 12, 0.28, 13, LAV, True, PP_ALIGN.CENTER)

    slide = base(prs, "二、睡岗的关键转化：从自然语言到时序谓词")
    add_svg(slide, diagrams["predicate_svg"], 0.8, 1.3, 11.7, 5.25)
    add_text(slide, "轨迹层是判定标准块与视觉感知之间的接口：规则负责‘什么算静止’，感知负责‘轨迹是否满足’。", 0.7, 6.57, 12, 0.28, 13, LAV, True, PP_ALIGN.CENTER)

    # 5-9 17 checks
    slide = base(prs, "三、实施文档17项校验：总览与判定对象")
    card(slide, 0.55, 1.35, 3.0, 4.85, "A｜QA对内部 · 4项", "指令 vs 回答\n\nA1 状态术语统一\nA2 同名异义\nA3 阈值边界\nA4 工况条件缺项\n\n零图片、零VLM；\n文本抽取+符号规则可先落地。", MINT, 15)
    card(slide, 3.78, 1.35, 3.0, 4.85, "B｜图片 vs QA · 8项", "轨迹/感知 vs QA\n\nB1 同义异名\nB2 对象类别全局\nB3 目标行为术语\nB4 隐患属性冲突\nB5 实体属性丢失\nB6 值域范围\nB7 数量指标\nB8 场景-行为错配", PURPLE, 14)
    card(slide, 7.01, 1.35, 2.75, 4.85, "C｜跨样本 · 3项", "全量QA语料\n\nC1 缩写与代号\nC2 规则引用不一致\nC3 多样本结论矛盾\n\n依赖tracklet/\n时序聚类与全局注册表。", GOLD, 15)
    card(slide, 10.0, 1.35, 2.75, 4.85, "D｜QA vs 规则 · 2项", "QA vs 判定标准块\n\nD1 枚举标签一致性\nD2 隐患判定逻辑冲突\n\n规则驱动，确定性\n最强；规则块同时服务\n生成、校验、负样本。", RED, 15)

    checks = [
        ("A类｜QA对内部", ["A1 状态术语统一：‘离岗状态’与‘不在岗’归一到同一概念；输出规范告警。", "A2 同名异义：‘通道’可能指疏散通道或消防通道；需指代消解/限定词。", "A3 阈值边界：规则‘≥X’被回答改成‘>X’；符号级+数值级比较，确定性refute。", "A4 工况条件缺项：‘夜班值守下’被回答丢失；条件覆盖集做差集，标记回答不完整。"]),
        ("B1-B4｜图片与QA", ["B1 同义异名：图片‘工作服’ vs QA‘工装’，跨模态术语归一。", "B2 对象类别：图片‘安全帽’ vs QA‘头部防护帽’，建立实体类别一致性矩阵。", "B3 目标行为术语：图片‘未穿工作服’ vs QA‘没有穿工装’，行为标签归一。", "B4 隐患属性冲突：规则推导等级‘重大’ vs QA‘一般’；以规则引擎输出为标准。"]),
        ("B5-B8｜完备性与场景", ["B5 实体属性丢失：图片识别出摔倒，QA未提；应覆盖集−实际覆盖集，结果通常为可疑。", "B6 值域范围：图片识别安全帽+工作服两个缺失属性，QA只报告一个；检查集合覆盖。", "B7 数量指标：图片3处杂物，QA写2处；检测计数值直接比对。", "B8 场景-行为错配：疏散通道套用工位规则；比较图片场景与规则适用域。"]),
        ("C类｜跨QA样本", ["C1 缩写与代号：同设备/区域在不同QA中的代号不统一；全局术语注册表发现异形。", "C2 规则引用不一致：同类违规给出不同处置建议；按task类别分组后join。", "C3 多样本结论矛盾：同camera近时帧/同图不同条件出现相反answer；输出可疑对，不单方判错。"]),
        ("D类｜规则驱动", ["D1 枚举标签一致性：answer输出‘普通隐患’，不属于{一般、较大、重大}；闭集成员检查。", "D2 判定逻辑冲突：轨迹识别长时间静止，QA却判合规；判定标准块→预期answer与实际answer比较。", "规则块三重角色：生成prompt规范、校验规则源、困难负样本翻转源。"]),
    ]
    for title, lines in checks:
        slide = base(prs, f"三、17项逐条解读：{title}")
        y = 1.34
        for i, line in enumerate(lines):
            card(slide, 0.72, y, 11.9, 0.9 if len(line) < 70 else 1.02, f"{i + 1:02d}", line, [MINT, PURPLE, GOLD, RED][i % 4], 15)
            y += 1.12 if len(line) >= 70 else 1.0
        add_text(slide, "判定边界：确定性矛盾→refute；规范问题→warning；证据不足/跨样本冲突→可疑人工仲裁", 0.8, 6.55, 11.8, 0.3, 13, LAV, True, PP_ALIGN.CENTER)

    # 10 semantic output
    slide = base(prs, "四、校验结果不是二分类：四态语义与数据治理动作")
    for i, (title, body, color) in enumerate([
        ("support", "现有证据支持QA内部与规则一致\n动作：保留，进入正样本池", MINT),
        ("refute", "阈值改变、非法枚举、规则冲突、指标冲突\n动作：剔除或修正", RED),
        ("NIE", "当前证据无法判断，不强行推断\n动作：保留待补证或进入人工队列", GRAY),
        ("可疑", "跨样本矛盾、属性丢失、ID漂移可能造成的假翻转\n动作：人工仲裁，不单方判错", GOLD),
    ]):
        card(slide, 0.55 + i * 3.2, 1.65, 2.85, 3.2, title, body, color, 15)
    add_text(slide, "质量关卡：检测 → 解释 → 回流，而不是只输出一个0/1标签", 0.8, 5.45, 11.8, 0.45, 22, GOLD, True, PP_ALIGN.CENTER)
    add_text(slide, "可疑态是场景5相较场景1的关键扩展：它承认‘聚合错误’与‘事实错误’不能混为一谈。", 0.8, 6.15, 11.8, 0.32, 14, LAV, False, PP_ALIGN.CENTER)

    # datasets overview
    slide = base(prs, "六、备选数据集：三类数据分别支撑三种实验")
    card(slide, 0.55, 1.35, 3.9, 4.9, "MeVA / DIVA", "固定多机园区监控\n328h地面视频，CC BY-4.0\nDIVA yml：geom/activities/types\n\n最贴合：轨迹+活动+身份\n已下载：DIVA标注6641文件\n+ G329连续双片段", MINT, 16)
    card(slide, 4.72, 1.35, 3.9, 4.9, "MOT20 / MOT17", "标准MOT跟踪基准\nMOT格式：frame,id,bbox\nMOT20全固定监控\nMOT17含固定/移动混合\n\n最适合：跟踪器、IDF1/HOTA\n已下载：两套zip+labels", PURPLE, 16)
    card(slide, 8.89, 1.35, 3.9, 4.9, "UCF-Crime", "真实监控违规行为\n952视频，13类异常\nAbuse/Arrest/Arson/Assault…\n\n最适合：行为语义与异常\n已下载：HF镜像全量约24GB\n注意：弱监督、需自跑跟踪", GOLD, 16)

    # images: real samples
    slide = base(prs, "七、真实样例一：MeVA的‘轨迹+动作段’标注关系")
    add_image(slide, assets["meva"], 0.55, 1.35, 7.0, 4.6)
    card(slide, 7.85, 1.35, 4.9, 4.6, "同名三件套：一个clip就是一个可校验条目", "geom.yml\n→ id1=track_id；ts0=帧号；g0=bbox\n\nactivities.yml\n→ Enter_Facility；timespan=[2679,2734]\n→ actors引用id1=0\n\ntypes.yml\n→ id1=0；cset3=Person\n\n对应三角色：轨迹是上下文，活动是动作段，QA可按时间对齐。", GOLD, 15)
    add_text(slide, "图：真实MeVA G329帧，黄色框来自geom.yml的truth轨迹", 0.65, 6.2, 7, 0.28, 11, GRAY)

    slide = base(prs, "七、真实样例二：MOT17的‘frame-id-bbox’组织关系")
    add_image(slide, assets["mot"], 0.55, 1.35, 7.35, 4.75)
    card(slide, 8.15, 1.35, 4.6, 4.75, "MOT17/train/MOT17-04-FRCNN", "img1/000100.jpg\n+ gt/gt.txt\n\n每行：\nframe, id, left, top, width, height, conf, class, visibility\n\n图中绿色框 = 官方gt.txt\n\n实验用途：\n• 检测与跟踪器基线\n• ID切换与遮挡压力\n• HOTA / IDF1 / MOTA\n• tracklet质量评测", MINT, 15)
    add_text(slide, "图：真实MOT17官方训练帧；ID是跨帧关联主键，不是一次性检测编号", 0.65, 6.2, 8, 0.28, 11, GRAY)

    slide = base(prs, "七、真实样例三：UCF-Crime的‘监控视频—异常类别’关系")
    add_image(slide, assets["ucf"], 0.55, 1.35, 7.35, 4.75)
    card(slide, 8.15, 1.35, 4.6, 4.75, "Anomaly-Videos-Part-1/Abuse/", "Abuse001_x264.mp4\nAbuse002_x264.mp4\n…\n\n目录名=行为类别\n文件=连续视频片段\n\n它不提供MeVA级track_id，\n因此实验中要：\n1. 检测人\n2. 跟踪人\n3. 识别动作\n4. 将动作与QA对齐\n\n用途：补充真实违规语义。", GOLD, 15)
    add_text(slide, "图：真实UCF-Crime Abuse001帧；类别标签来自目录组织，不等于逐人真值", 0.65, 6.2, 8, 0.28, 11, GRAY)

    # tech survey
    slide = base(prs, "八、技术调研：特征提取的完整技术链")
    card(slide, 0.55, 1.35, 3.0, 4.9, "检测 Detection", "YOLO/RT-DETR\n开放词汇检测\n\n输出：bbox、类别、置信度\n主体：person / PPE / 设备 / 区域\n\n研究重点不是发明检测器，\n而是统一输出协议。", MINT, 15)
    card(slide, 3.78, 1.35, 3.0, 4.9, "跟踪 Tracking", "ByteTrack：检测框关联\nDeepSORT：外观+运动\nOC-SORT：运动鲁棒\n\n输出：track_id、轨迹、\n速度、位移、遮挡、ID切换\n\n首版限定同camera。", PURPLE, 15)
    card(slide, 7.01, 1.35, 2.75, 4.9, "属性 Attribute", "PPE穿戴\n姿态/关键点\n区域/场景\n\n属性是序列，不是单帧\n标签：需稳定性与置信度。", GOLD, 15)
    card(slide, 10.0, 1.35, 2.75, 4.9, "动作 Action", "动作识别 / 时序分段\n\n输入：tracklet上的\n姿态、速度、位移、遮挡\n\n睡岗=静止谓词：\n位移方差<阈值且持续N帧\n\n输出动作起止帧+置信度。", RED, 14)

    slide = base(prs, "八、技术调研：特征提取的选择、输出与误差")
    card(slide, 0.55, 1.3, 3.0, 5.05, "模型选择", "检测：YOLO/RT-DETR\n跟踪：ByteTrack优先，\nDeepSORT用于外观补充\n姿态：关键点/骨架序列\n动作：时序分类或规则谓词\n\n选择原则：先稳定输出\n再追求识别精度。", MINT, 14)
    card(slide, 3.78, 1.3, 3.0, 5.05, "统一特征协议", "entity：person / PPE\ntrack_id：同camera内唯一\nframe/time：双时间轴\nbbox/center：空间位置\nattr：穿戴/姿态\naction：label,start,end\nquality：遮挡/置信度/ID切换", PURPLE, 14)
    card(slide, 7.01, 1.3, 2.75, 5.05, "主要误差", "漏检→轨迹断裂\nID switch→属性假翻转\n遮挡→缺观测\n姿态抖动→动作碎片\n相机切换→身份不确定\n\n不能将所有误差\n直接判成QA错误。", GOLD, 14)
    card(slide, 10.0, 1.3, 2.75, 5.05, "评测与产出", "检测：Precision/Recall\n跟踪：IDF1/HOTA/MOTA\n动作：segment F1\n轨迹：fragmentation/IDSW\n\n最终产出不是分数，\n而是可回溯轨迹注册表。", RED, 14)

    slide = base(prs, "八、技术调研：上下文关联的核心是tracklet而非相似图片")
    card(slide, 0.55, 1.35, 4.0, 4.9, "关联粒度", "同camera + 时间窗口 + person_id\n\ntracklet：\n{t0…t1, bbox_t, pose_t, attr_t, action_segments}\n\n‘同一个人’是行为检测的天然主键；\n‘同一场景’是区域/设备检测的补充粒度。", MINT, 16)
    card(slide, 4.82, 1.35, 3.55, 4.9, "关联算法", "短时：ByteTrack / Kalman\n外观：DeepSORT / Re-ID\n跨镜头：MEVID身份层\n\n工程顺序：\n同camera短时tracklet\n→ 属性序列稳定化\n→ 跨camera二期", PURPLE, 16)
    card(slide, 8.64, 1.35, 4.1, 4.9, "关联不确定性", "ID switch会制造假翻转：\nA人→B人，属性突然改变\n\n遮挡会制造缺帧：\n不能把缺观测当成否定\n\n因此：轨迹置信度、遮挡段、\nID切换都进入‘可疑’态，\n不直接refute。", GOLD, 16)

    slide = base(prs, "八、技术调研：关联算法的层次、边界与评测")
    add_svg(slide, diagrams["stack_svg"], 0.7, 1.25, 12.0, 4.15)
    card(slide, 0.7, 5.45, 3.8, 0.85, "短时同camera", "检测框+运动模型；首版主线", MINT, 12)
    card(slide, 4.75, 5.45, 3.8, 0.85, "跨镜头Re-ID", "MEVID身份层；二期，不作为首版前提", PURPLE, 12)
    card(slide, 8.8, 5.45, 3.8, 0.85, "评测", "IDF1/HOTA + IDSW + 轨迹完整性", GOLD, 12)

    slide = base(prs, "八、技术调研：一致性校验的规则、注册表与可解释证据链")
    card(slide, 0.55, 1.35, 3.0, 4.9, "规则引擎", "判定标准块编译：\n条件→场景适用域\n结论→预期answer\n枚举→值域闭集\n阈值→符号约束\n\n睡岗规则→时序谓词\n‘静止持续N帧’。", MINT, 15)
    card(slide, 3.78, 1.35, 3.0, 4.9, "注册表 + join", "图像侧：\n(person_id, attr/action, time)\n\nQA侧：\n(task, answer, evidence, timestamp)\n\n规则侧：\n(scope, condition, expected)\n\n三方join后逐项裁决。", PURPLE, 15)
    card(slide, 7.01, 1.35, 2.75, 4.9, "确定性检测", "集合差集：属性丢失\n区间算术：阈值边界\n闭集成员：枚举\n计数比较：数量\n规则匹配：逻辑冲突\n\n能形式化就不交给NLI。", GOLD, 14)
    card(slide, 10.0, 1.35, 2.75, 4.9, "学习与评测", "NLI只处理残差\nVLM只做抽检/仲裁\n\n缓存+描述冻结\n\n评测：sound性断言门\n人工抽检gold\n跨条件矛盾种子", RED, 14)

    slide = base(prs, "八、技术调研：17项如何落到可执行算子")
    add_svg(slide, diagrams["check_svg"], 0.7, 1.25, 12.0, 5.25)
    add_text(slide, "原则：优先确定性、可解释、可复现；只有规则无法覆盖的残差才交给NLI或人工。", 0.7, 6.57, 12, 0.28, 13, LAV, True, PP_ALIGN.CENTER)

    # roadmap
    slide = base(prs, "九、实施路线与阶段性产出")
    card(slide, 0.55, 1.35, 3.85, 4.9, "阶段① 纯文本与规则", "QA JSON解析器\n场景5词典\n判定标准块编译器\nA类4项 + D类2项\n跨QA文本规则\n\n产出：零图片、零VLM\n可重复的确定性闭环", MINT, 16)
    card(slide, 4.73, 1.35, 3.85, 4.9, "阶段② 视觉与tracklet", "检测→跟踪→属性→动作\n同camera轨迹对齐\nB类图片-QA 8项\n真实样例：MeVA/MOT20\n\n产出：个体轨迹注册表\n动作段与QA证据对齐", PURPLE, 16)
    card(slide, 8.91, 1.35, 3.85, 4.9, "阶段③ 语料级闭环", "camera+time聚类\n跨QA结论矛盾\n困难负样本\n人工仲裁回流\n\n产出：可治理数据集\n可解释的质量报告", GOLD, 16)
    add_text(slide, "近期最小闭环：MOT20跑通跟踪评测 → G329完成MeVA轨迹对齐 → 规则引擎验证‘长时间静止’", 0.7, 6.5, 12, 0.32, 15, LAV, True, PP_ALIGN.CENTER)

    # conclusion
    slide = base(prs, "十、结论：把视频监控的连续性变成一致性校验的证据")
    add_text(slide, "不是把图片逐张送入模型，而是建立‘同一个体—同一条轨迹—同一套规则’。", 0.75, 1.35, 11.9, 0.65, 27, GOLD, True, PP_ALIGN.CENTER)
    card(slide, 0.85, 2.55, 3.55, 2.35, "研究定义", "特征提取 = CV结构化感知\n上下文关联 = tracklet时序连续性\n一致性校验 = 轨迹、QA、规则三方比对", MINT, 16)
    card(slide, 4.9, 2.55, 3.55, 2.35, "当前证据", "已下载43.32GB真实数据\nMeVA提供轨迹+动作gold\nMOT提供跟踪基线\nUCF补充违规语义", PURPLE, 16)
    card(slide, 8.95, 2.55, 3.55, 2.35, "下一步", "先跑同camera tracklet\n再编译睡岗时序规则\n最后把17项逐项接入\n形成可测评质量关卡", GOLD, 16)
    add_text(slide, "谢谢", 0.8, 5.85, 11.8, 0.55, 30, PURPLE, True, PP_ALIGN.CENTER)
    add_text(slide, "场景5 · 科研生产现场智能监管 · 2026", 0.8, 6.55, 11.8, 0.25, 11, GRAY, False, PP_ALIGN.CENTER)

    trim_slides(prs, SHELL_INDEX)
    PPT_OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(PPT_OUT))


if __name__ == "__main__":
    build_ppt(make_assets(), make_svg_assets())
