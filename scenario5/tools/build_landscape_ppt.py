"""Generate the scenario5 complete landscape PPT (task-data-tech mapping)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from pptx.enum.text import PP_ALIGN  # noqa: E402
from pptx.util import Inches, Pt  # noqa: E402

TEMPLATE = Path(r"C:\Users\12488\Downloads\南开大学模板-3.pptx")
PPT_OUT = ROOT / "scenario5" / "scenario5_landscape_v2.pptx"

# Purple color scheme (white background)
BG = RGBColor(255, 255, 255)
PANEL = RGBColor(247, 243, 252)
PANEL2 = RGBColor(239, 231, 249)
PURPLE = RGBColor(103, 55, 153)
LIGHT_PURPLE = RGBColor(151, 104, 255)
DARK = RGBColor(39, 27, 57)
GRAY = RGBColor(105, 96, 116)
MINT = RGBColor(0, 150, 119)
GOLD = RGBColor(180, 130, 50)
RED = RGBColor(180, 60, 80)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


def add_text(slide, text, x, y, w, h, size=18, color=DARK, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Pt(5)
    tf.margin_top = Pt(2)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = "Microsoft YaHei"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.alignment = align
        p.space_after = Pt(2)
    return box


def rect(slide, x, y, w, h, fill=PANEL, line=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line or fill
    return sh


def card(slide, x, y, w, h, title, body, accent=PURPLE, body_size=14):
    rect(slide, x, y, w, h, PANEL, accent)
    rect(slide, x, y, 0.06, h, accent)
    add_text(slide, title, x + 0.15, y + 0.08, w - 0.3, 0.35, 15, accent, True)
    add_text(slide, body, x + 0.15, y + 0.42, w - 0.3, h - 0.5, body_size, DARK)


def base(title, section=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG
    # Border
    border = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.18), Inches(0.18), Inches(12.97), Inches(7.14))
    border.fill.background()
    border.line.color.rgb = PURPLE
    border.line.width = Pt(1.5)
    # Top bar
    top = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.18), Inches(0.18), Inches(12.97), Inches(0.06))
    top.fill.solid()
    top.fill.fore_color.rgb = PURPLE
    top.line.fill.background()
    # Section + title
    if section:
        add_text(slide, section, 0.5, 0.32, 5, 0.25, 10, LIGHT_PURPLE, True)
    add_text(slide, title, 0.5, 0.55, 12.3, 0.45, 22, PURPLE, True)
    return slide


# ============ SLIDE 1: Cover ============
slide = prs.slides.add_slide(prs.slide_layouts[6])
slide.background.fill.solid()
slide.background.fill.fore_color.rgb = BG
rect(slide, 0.18, 0.18, 12.97, 7.14, PANEL2, PURPLE)
add_text(slide, "场景5 静态图片一致性校验", 1.5, 1.2, 10, 0.8, 36, PURPLE, True, PP_ALIGN.CENTER)
add_text(slide, "任务定位 · 视觉子任务 · 数据映射 · SOTA技术图谱 · 实施路线", 1.5, 2.1, 10, 0.5, 18, DARK, False, PP_ALIGN.CENTER)
add_text(slide, "12个视觉子任务 × 5套数据集 × 6轮Agent调研 × 3轮实测验证", 1.5, 3.0, 10, 0.4, 16, GRAY, False, PP_ALIGN.CENTER)
card(slide, 1.5, 4.2, 3.3, 1.2, "特征提取", "12个原子视觉子任务\n产出ImageEvidenceV2", PURPLE)
card(slide, 5.1, 4.2, 3.3, 1.2, "上下文关联", "四层证据连接\ngrounding / 同源 / 规则域", GOLD)
card(slide, 8.7, 4.2, 3.3, 1.2, "一致性校验", "三方join + 17项\n四态语义判定", MINT)
add_text(slide, "2026-11-17", 1.5, 6.3, 10, 0.3, 12, GRAY, False, PP_ALIGN.CENTER)

# ============ SLIDE 2: Three Module Positioning ============
slide = base("一、三模块在图片场景下的定位", "PART 1 任务定位")
card(slide, 0.5, 1.2, 3.9, 5.5, "特征提取", 
     "从单张监控图片抽取\n可定位、可审计、\n带置信度的原子视觉事实\n\n"
     "做什么：\n  人/物/PPE/姿态/ROI/OCR\n  关系/计数/质量/同源\n\n"
     "不做什么：\n  ✗ 输出'睡岗/违规/隐患等级'\n  ✗ 用模型预测当真值\n\n"
     "产出：ImageEvidenceV2\n(冻结JSON，一次运行)", PURPLE, 13)
card(slide, 4.7, 1.2, 3.9, 5.5, "上下文关联",
     "建立四层证据连接\n让分散信息可join\n\n"
     "① 图内关联\n  scene graph(shapely)\n② 跨模态grounding\n  QA span→ROI(Florence-2)\n"
     "③ 规则适用域\n  场景↔规则条件子句\n④ 跨样本同源\n  SSCD嵌入/增广谱系\n\n"
     "图片≠视频：无tracklet\n上下文=空间+同源\n非时序连续性", GOLD, 13)
card(slide, 8.9, 1.2, 3.9, 5.5, "一致性校验",
     "三方join后判定\nQA数据质量\n\n"
     "视觉事实注册表\n  (image_id, predicate)\nQA claim注册表\n  (qa_id, answer, span)\n"
     "规则注册表\n  (rule_id, premises)\n\n"
     "四态语义：\n  support  证据充分一致\n  refute    确定性矛盾\n  NIE       证据不足\n  suspicious 待人工复核\n\n"
     "校验对象=QA对是否自洽\n不替代任务标签", MINT, 13)

# ============ SLIDE 3: 17项分拣 ============
slide = base("一、17项校验在图片场景的分拣", "PART 1 任务定位")
card(slide, 0.5, 1.2, 5.8, 2.8, "✓ 纯文本/规则（7项，无需图片）",
     "A1 状态术语统一 | A2 同名异义\nA3 阈值边界     | A4 工况条件缺项\nC1 缩写代号     | C2 规则引用不一致\nD1 枚举标签(确定性最强)", MINT, 13)
card(slide, 6.6, 1.2, 6.1, 2.8, "✓ 单图条件可判（8项，需视觉证据）",
     "B1 同义异名跨模态  | B2 对象类别(样本内)\nB3 行为术语(静态)  | B5 实体属性丢失\nB6 值域范围        | B7 数量指标\nB8 场景-行为错配   | D2 判定逻辑(静态规则)", PURPLE, 13)
card(slide, 0.5, 4.2, 5.8, 2.5, "△ 需跨样本（2项）",
     "B2 对象类别全局一致\n  → 跨QA术语聚合\nC3 多样本结论矛盾\n  → 同图/同源QA answer比对\n  → SSCD同源聚组", GOLD, 13)
card(slide, 6.6, 4.2, 6.1, 2.5, "✗ 静态图不可证明 → NIE",
     "睡岗「长时间静止」\n  原文规则: 趴伏∧闭眼∧长时间静止\n  静态图: stationary_duration=UNKNOWN\n  → D2必须输出NIE\n  → 不能用更强模型猜\n\n持续离岗/徘徊/摔倒(动态)\n  → 需视频/连续帧", RED, 13)

# ============ SLIDE 4: 12 Subtasks Overview ============
slide = base("二、12个视觉子任务总览", "PART 2 子任务与数据")
data_rows = [
    ("T0 质量门控", "blur/exposure/usable", "先于所有否定判断", "OpenCV确定性", "部分可评"),
    ("T1 人员检测", "bbox+conf+可见度", "B1/B2/B5/B7", "YOLO11s✓/RF-DETR", "可评"),
    ("T2 通用物体", "类别+bbox", "B1/B2/B5/B6", "YOLO/域内微调", "部分可评"),
    ("T3 PPE实例", "安全帽/工作服框", "B1/B3/B4/B6", "keremberke✓/SH17", "可评(域)"),
    ("T4 穿戴关系", "wearing(p,h)", "B3/B4/B5/B6", "IoA+垂直序规则", "部分可评"),
    ("T5 静态姿态", "head_down/prone", "B3/B5/D2", "RTMO-s✓/RTMPose", "部分可评"),
    ("T6 场景/ROI", "多边形+类型", "B8;B4/B7", "人工标定+shapely", "不可评"),
    ("T7 空间关系", "inside/near/on", "B4/B5/B8/D2", "shapely确定性", "不可评"),
    ("T8 计数", "实例数+单位", "B7", "检测去重+ROI", "可评"),
    ("T9 通道占用", "阻塞比+时长", "B1/B4/B5", "需时序(静态不可)", "不可评"),
    ("T10 OCR", "时间戳/设备号", "C1;时间戳", "PaddleOCR/Rapid", "不可评"),
    ("T11 同源", "near_dup对", "C3", "SSCD✓/dHash✓", "可评"),
]
# Table header
add_text(slide, "子任务          输出             服务项         技术方案         可评性", 0.6, 1.15, 12.1, 0.3, 11, PURPLE, True)
y = 1.45
for row in data_rows:
    color = MINT if row[4] == "可评" else (GOLD if "部分" in row[4] else RED)
    rect(slide, 0.5, y, 12.2, 0.38, PANEL if y % 2 else PANEL2, None)
    text = f"{row[0]:<14} {row[1]:<16} {row[2]:<14} {row[3]:<18} {row[4]}"
    add_text(slide, text, 0.6, y + 0.04, 12.1, 0.3, 10, DARK)
    add_text(slide, row[4], 11.4, y + 0.04, 1.2, 0.3, 10, color, True)
    y += 0.42
add_text(slide, "✓=已下载已验证   可评=有GT可计算指标   部分=有素材缺gold   不可=需标注/需时序", 0.6, 6.6, 12, 0.3, 11, GRAY)

# ============ SLIDE 5: Data Support Status ============
slide = base("二、数据支撑现状：4可评 / 4部分 / 4不可评", "PART 2 子任务与数据")
card(slide, 0.5, 1.2, 3.9, 5.5, "✓ 可评（4个子任务）",
     "T1 人员检测\n  MOT17 GT: mAP@0.5, IDF1\n  已跑通5个run\n\n"
     "T3 PPE实例\n  PPE hardhat test 2001张\n  COCO GT: mAP@0.5:0.95\n\n"
     "T8 计数\n  PPE COCO instance派生\n  MAE, within±1\n\n"
     "T11 同源\n  32图增广谱系=已知gold\n  pair P/R, AUC\n  dHash已产出候选边", MINT, 12)
card(slide, 4.7, 1.2, 3.9, 5.5, "△ 部分可评（4个子任务）",
     "T0 质量门\n  增广类型=已知扰动\n  缺: 真实坏图gold\n\n"
     "T2 通用物体\n  MeVA有限类+Florence-2\n  缺: 场景5语义类标注\n\n"
     "T4 穿戴关系\n  PPE 2类≈head级状态\n  缺: person框+配对ID\n\n"
     "T5 静态姿态\n  已产出(8 head_down/9 prone)\n  缺: 姿态标签gold", GOLD, 12)
card(slide, 8.9, 1.2, 3.9, 5.5, "✗ 不可评（4个子任务）",
     "T6 场景/ROI\n  所有数据集均无ROI标注\n  需: 32图×2-4多边形\n  ≈96个, 2人时\n\n"
     "T7 空间关系\n  依赖T1框+T6 ROI\n  需: (person,ROI,in/out)\n  ≈120条, 1人时\n\n"
     "T9 通道占用\n  本质时序(滞留N秒)\n  需: MeVA轨迹+通道ROI\n\n"
     "T10 OCR\n  无图内文字gold\n  需: 32图OSD标注\n  +模块实现", RED, 12)

# ============ SLIDE 6: Our Data Examples ============
slide = base("二、32张睡岗图与672条QA：具体数据例子", "PART 2 子任务与数据")
card(slide, 0.5, 1.2, 5.9, 2.7, "32张睡岗图（1920×1080, 4种增广）",
     "增广分布: night=7, fog=6, strong_light=7, flip=12\n"
     "人员分布: 2人×25图 + 1人×7图 = 57人\n\n"
     "shuigang_0036_strong_light:\n  p1: head_down=true, prone_like=true\n  → D2规则前两个前件可观测\n\n"
     "shuigang_0615_strong_light (C3唯一冲突):\n  after-4bit-simple: answer=0\n  其余4条件: answer=1\n  → 同图跨条件answer矛盾", PURPLE, 11)
card(slide, 6.7, 1.2, 5.9, 2.7, "672条QA输出（7文件×96条）",
     "default prompt (5文件=480条):\n  JSON: task/answer/evidence\n  → D1: answer∈{0,1,2} 全合法\n  → 477条解析成功\n\n"
     "simpleprompt (2文件=192条):\n  自然语言，非JSON\n  → parse_status=unparsed\n  → D1/B3输出NIE(195条)\n\n"
     "B3 v1 (关键词+否定检测):\n  support=214, NIE=321\n  suspicious=137(20%)\n  → 送人工复核，不自动判错", GOLD, 11)
card(slide, 0.5, 4.1, 5.9, 2.6, "PPE hardhat数据集（已下载）",
     "13782 train / 3962 valid / 2001 test\n"
     "COCO格式: hardhat(28996框) + no-hardhat(9705框)\n\n"
     "可评测：\n  T3 PPE检测: mAP@0.5:0.95\n  T8 计数: COCO instance派生\n  T4 穿戴: 2类≈head级F1\n\n"
     "缺口：缺person框配对\n  需补标300张≈900框", MINT, 11)
card(slide, 6.7, 4.1, 5.9, 2.6, "32图全景标注包（3人时=杠杆资产）",
     "person bbox:  57个   → T1域内sanity  30min\n"
     "物体清单+bbox: ~128框 → T2域内评测    45min\n"
     "姿态标签:      57条   → T5 gold验证   30min\n"
     "ROI多边形:     ~96个  → T6+T7解锁     60min\n"
     "OCR文本:       ~40条  → T10解锁       30min\n\n"
     "→ T2/T5/T6/T7/T10 全部升为可评\n"
     "→ 同源变体提供跨条件不变性检验\n"
     "→ 一次标注，五个子任务受益", RED, 11)

# ============ SLIDE 7: Free Evaluation ============
slide = base("二、免标注可收割的评测（零成本）", "PART 2 子任务与数据")
free_items = [
    ("T1 人员检测", "MOT17 GT", "mAP@0.5, IDF1", "已跑通5个run", MINT),
    ("T3 PPE检测", "PPE hardhat test(2001张)", "mAP@0.5:0.95", "模型推理+GT比对", MINT),
    ("T8 计数", "PPE COCO instance派生", "MAE, within±1", "从GT免费派生", MINT),
    ("T11 同源", "32图增广谱系(7base×2变体)", "pair P/R, AUC", "dHash已产出候选边", MINT),
    ("T0 质量", "增广类型=已知扰动", "分组拒检率", "night/fog应告警,flip=FP", MINT),
]
y = 1.3
for name, source, metric, status, color in free_items:
    rect(slide, 0.5, y, 12.2, 0.85, PANEL, color)
    add_text(slide, name, 0.7, y + 0.1, 2.2, 0.3, 14, color, True)
    add_text(slide, source, 3.0, y + 0.1, 3.5, 0.3, 12, DARK)
    add_text(slide, metric, 6.6, y + 0.1, 2.5, 0.3, 12, DARK)
    add_text(slide, status, 9.2, y + 0.1, 3.4, 0.3, 11, GRAY)
    y += 1.0
add_text(slide, "以上5项评测均无需额外标注，当前即可执行", 0.6, 6.6, 12, 0.3, 14, MINT, True, PP_ALIGN.CENTER)

# ============ SLIDES 8-13: SOTA Technology Landscape ============
slide = base("三、SOTA技术图谱：检测与PPE", "PART 3 技术图谱")
card(slide, 0.5, 1.2, 6.0, 5.5, "通用目标检测",
     "YOLO26 (2026.01, AGPL)\n  COCO 48.6(s)→57.5(x)\n  SAB复测偏差最小(Δ0.6)\n  原生NMS-free端到端\n\n"
     "★ RF-DETR-S (ICLR'26, Apache)\n  53.0 AP / 3.5ms\n  商用友好推荐\n\n"
     "RT-DETRv4 (ECCV'26, Apache)\n  S=49.8, X=57.0\n\n"
     "D-FINE (Apache)\n  X=59.3 AP\n\n"
     "小目标增强:\n  SAHI切片(VisDrone+10~14 AP50)\n  YOLO26-P2架构(官方仅YAML)", PURPLE, 12)
card(slide, 6.7, 1.2, 6.0, 5.5, "PPE专用检测",
     "SH17 (17类PPE, 8099图)\n  YOLOv9e: mAP50=70.9\n  权重可下载(CC BY-NC-SA)\n  17类含helmet/vest/gloves等\n\n"
     "keremberke/YOLOv8 (2类)\n  mAP50=0.836 (hardhat/no-hardhat)\n  权重可下载(HF)\n  ← 配套数据集已下载\n\n"
     "SHWD (7581图, 2类)\n  论文报93+但无权重发布\n  ⚠ 不可引用(不可复现)\n\n"
     "工业方案:\n  Roboflow Universe + RF-DETR微调\n  ✗ Azure/阿里无PPE专用公开API", GOLD, 12)

slide = base("三、SOTA技术图谱：姿态估计", "PART 3 技术图谱")
card(slide, 0.5, 1.2, 6.0, 5.5, "2D姿态估计",
     "★ RTMO-s/m/l (Apache, 一阶段)\n  AP 68.6/72.6/74.8\n  不随人数减速(141FPS@V100)\n  ONNX独立加载(已下载)\n  ← 推荐替换YOLO11n-pose\n\n"
     "RTMPose-m (Apache, top-down)\n  AP 75.8, CPU 90+FPS\n\n"
     "ViTPose-H (Apache)\n  AP 79.1 (精度上限)\n\n"
     "DWPose-l (Apache)\n  Face AP=0.887\n  ← 闭眼检测(睡岗前件)\n\n"
     "Sapiens (CC-BY-NC, 禁商用)\n  AP 82.1 ← 不推荐", PURPLE, 12)
card(slide, 6.7, 1.2, 6.0, 5.5, "骨架动作识别（参考）",
     "PoseC3D (CVPR'22, Apache)\n  NTU60: 94.1%(二流)\n  Kinetics: 49.1%(二流)\n\n"
     "CTR-GCN (ICCV'21)\n  NTU60: 92.1%(四流)\n\n"
     "⚠ 注意:\n  骨架系在Kinetics仅~49%\n  (RGB模型~90%)\n  因K400大量动作依赖外观\n\n"
     "视频行为(参考):\n  VideoMAE v2: K400 88.4%\n  InternVideo2: K400 91.3%\n  ← 静态图片场景不适用", GOLD, 12)

slide = base("三、SOTA技术图谱：视觉Grounding", "PART 3 技术图谱")
card(slide, 0.5, 1.2, 6.0, 5.5, "跨模态Grounding\n(QA evidence → 图片区域)",
     "★ Florence-2-base-ft (MIT, 0.77B)\n  RefCOCOg val: 92.6%\n  专用task token + bbox解析\n  <1GB显存, 已下载已验证\n  ← 当前首选\n\n"
     "Florence-2-large-ft (MIT)\n  RefCOCOg: 93.4%, ~2.5GB\n\n"
     "Qwen2.5-VL-7B (Apache, 8B)\n  RefCOCOg: 89.9%\n  DocVQA: 95.7\n  中文grounding更强\n\n"
     "Moondream2 (Apache, 1.9B)\n  ScreenSpot: 80.4\n  detect()/point() API", PURPLE, 12)
card(slide, 6.7, 1.2, 6.0, 5.5, "开放词汇检测\n(灵活类别召回)",
     "Grounding DINO-T (Apache)\n  COCO zero-shot: 48.4 AP\n  transformers一行调用\n\n"
     "YOLOE-26m (AGPL)\n  LVIS: 35.4 AP\n  文本/视觉/无提示三种模式\n\n"
     "YOLO-World-L (GPL, 商用需联系)\n  LVIS: 26.8 AP\n\n"
     "实测结果(3张睡岗图):\n  Florence-2 \"person\" grounding:\n  [630,288,1172,917] ✓\n  [575,485,1116,914] ✓\n  [615,414,1158,881] ✓\n  全部与frozen bbox高IoU", GOLD, 12)

slide = base("三、SOTA技术图谱：同源与近重复", "PART 3 技术图谱")
card(slide, 0.5, 1.2, 6.0, 5.5, "三级同源漏斗",
     "Level 1: SHA-256 (确定性)\n  完全相同 → same_asset\n  等价关系，可传递\n\n"
     "Level 2: ★ SSCD (MIT, 512维)\n  L2归一化嵌入\n  cos>0.75 → 90%精度\n  已下载(94MB)已验证\n\n"
     "Level 3: dHash (BSD-2, 64bit)\n  粗召回，已实现\n\n"
     "局部特征: XFeat+LighterGlue\n  (CVPR'24, Apache)\n  MegaDepth AUC 56.4\n\n"
     "⚠ DINOv2语义嵌入不能做同源\n  DISC21仅20.0 μAP\n  语义相似≠同源", PURPLE, 12)
card(slide, 6.7, 1.2, 6.0, 5.5, "SSCD实测结果(32图)",
     "阈值cos≥0.60: 328对\n\n"
     "同base增广对全部命中:\n  0324_flip↔0324_fog: 0.9144\n  0219_flip↔0219_fog: 0.8934\n  0018_flip↔0018_fog: 0.8784\n\n"
     "跨base高相似(同场景候选):\n  0145_flip↔0157_flip: 0.9408\n  0011_flip↔0018_flip: 0.9185\n\n"
     "夜间图聚类:\n  0756_night↔1099_night: 0.8328\n  0296_night↔0756_night: 0.8227\n\n"
     "→ 比dHash精确一个量级\n→ 能区分同源/同场景/不同场景\n→ 需校准阈值(可能需0.85+)", GOLD, 12)

slide = base("三、SOTA技术图谱：关系与场景", "PART 3 技术图谱")
card(slide, 0.5, 1.2, 6.0, 5.5, "图内关系(Scene Graph)",
     "★ 确定性几何 (shapely/supervision)\n  inside/near/on: 零训练可审计\n  固定机位完胜学习方法\n  ← 推荐首选\n\n"
     "REACT++ (BMVC'25, Apache)\n  SGDet R@100=34.1\n  17-19ms(ONNX) 最实用\n\n"
     "OvSGTR (ECCV'24 Oral, Apache)\n  R@100=43.4 开放词汇\n\n"
     "HOI(人-物交互):\n  GEN-VLKT: 33.75 mAP (MIT)\n  HOICLIP: 34.69 mAP\n\n"
     "✗ UniHOI (CVPR'23)\n  40.95 mAP但repo空壳\n  代码从未发布,不可用", PURPLE, 12)
card(slide, 6.7, 1.2, 6.0, 5.5, "场景/ROI与OCR",
     "场景/ROI:\n  人工多边形 + shapely\n  + cv2.pointPolygonTest\n  (带符号距离→边界预警)\n  supervision PolygonZone\n  直接接ByteTrack\n\n"
     "深度关系(behind等):\n  Depth Anything V2 (Apache)\n  2D不可判→需深度序\n\n"
     "★ OCR:\n  PaddleOCR PP-OCRv6\n  (Apache, 1.5M-tiny)\n  中英日+46语种\n  工业文字/数字屏专项\n  降级: RapidOCR(onnxruntime)", GOLD, 12)

slide = base("三、SOTA技术图谱：VLM整体方案", "PART 3 技术图谱")
card(slide, 0.5, 1.2, 6.0, 5.5, "8GB GPU可运行VLM",
     "★ Florence-2-base-ft\n  0.77B, MIT, <1GB显存\n  grounding首选\n\n"
     "Qwen2.5-VL-3B-AWQ\n  4B, Apache, ~3GB\n  中文理解更强\n\n"
     "InternVL2.5-2B\n  2.2B, MIT, ~4.5GB\n\n"
     "Moondream2\n  1.9B, Apache, ~4GB\n  detect/point API\n\n"
     "LLaVA-OneVision-0.5B\n  0.5B, Apache, ~1.5GB 最省", PURPLE, 12)
card(slide, 6.7, 1.2, 6.0, 5.5, "学术诚信警示",
     "✗ UniHOI (CVPR'23)\n  repo空壳,代码从未发布\n\n"
     "✗ ComSGT / Pred-HMR\n  查无此文\n\n"
     "✗ SHWD 93+论文数字\n  无权重发布,不可复现\n\n"
     "✗ LAF-YOLOv10 P2头\n  声称35.1,复现仅24.0\n\n"
     "✗ DINOv2做同源判定\n  DISC21仅20.0 μAP\n\n"
     "→ 引用前必须核实:\n  repo有代码+有权重+有指标", RED, 12)

# ============ SLIDE 14: Dependency Graph ============
slide = base("四、技术依赖与关键路径", "PART 4 实施路线")
card(slide, 0.5, 1.2, 5.8, 3.0, "依赖关系（简化）",
     "规则编译器(1周)\n  ↓ schema定稿\nImageEvidenceV2 Schema\n  ↓ 重冻结(32图)\nD2三方join(1周)\n  ↓\n评测\n\n"
     "并行(不在关键路径):\n  RTMO / PPE / Florence-2 / SSCD\n  全部已下载已验证", PURPLE, 12)
card(slide, 6.6, 1.2, 6.1, 3.0, "关键路径（3.5周）",
     "规则编译器(1周)\n  → schema定稿\n  → T6标定(3天,人力)\n  → T7谓词(2天)\n  → 重冻结(0.5天)\n  → D2三方join(1周)\n  → 评测(1周)\n\n"
     "瓶颈不在模型\n在两处人力串行:\n  T6 ROI标定 + 双标", GOLD, 12)
card(slide, 0.5, 4.3, 5.8, 2.4, "五条并行泳道",
     "A 规则/schema: 编译器→三值→D2 (CPU)\n"
     "B 感知模型: RTMO∥PPE∥B3v2∥SSCD (GPU)\n"
     "C 几何/ROI: T6标定→T7→B8 (人力+CPU)\n"
     "D 金标/评测: 双标→协议→消融 (人力)\n"
     "E 环境: PaddleOCR试验(允许失败)", MINT, 11)
card(slide, 6.6, 4.3, 6.1, 2.4, "风险排序",
     "1. PaddleOCR×numpy×Windows(高)\n   →降级RapidOCR\n"
     "2. Florence-2中文grounding(中)\n   →先跑10个span探针\n"
     "3. PPE域差距(中)\n   →先test集mAP,32图预期NIE\n"
     "4. RTMO ONNX解析(中)\n   →与YOLO11-pose交叉验证\n"
     "5. SSCD阈值校准(低)\n   →32图谱系PR曲线", RED, 11)

# ============ SLIDE 15: Three Iterations ============
slide = base("四、三迭代实施计划", "PART 4 实施路线")
card(slide, 0.5, 1.2, 3.9, 5.5, "迭代1（2周）\n集成冲刺",
     "已验证模块全部进管线:\n\n"
     "□ 补PPE权重→test mAP\n□ B3v2集成→672条对照\n□ C3升级SSCD漏斗\n□ RTMO推理+交叉验证\n"
     "□ 规则编译器v1\n□ T6标定+小金标启动\n\n"
     "验收:\n✓ schema v1.0冻结\n✓ 全通道重冻结run\n✓ 四模块通道级数字", PURPLE, 11)
card(slide, 4.7, 1.2, 3.9, 5.5, "迭代2（4周）\n几何谓词+D2联调",
     "关键路径收口:\n\n"
     "□ T6完成→T7 shapely\n□ D2三方join上线\n  (睡岗全部输出NIE\n   false-decisive=0)\n"
     "□ B5覆盖差集+B8错配\n□ B6值域(复用PPE)\n□ T10 PaddleOCR试验\n\n"
     "验收:\n✓ 9项可评verdict矩阵\n✓ oracle消融×3\n  (定位错误归属层)", GOLD, 11)
card(slide, 8.9, 1.2, 3.9, 5.5, "迭代3（8周）\n论文级评测",
     "完整评测与巩固:\n\n"
     "□ 双标96→160条+κ\n□ family切分+聚类bootstrap\n□ 通道级完整评测表\n"
     "□ 端到端五连指标\n  (feature∧grounding\n   ∧scope∧verdict∧定位)\n"
     "□ 可疑队列Recall@budget\n\n"
     "验收:\n✓ 论文数字表全套\n✓ 复现协议+MANIFEST", MINT, 11)

# ============ SLIDE 16: Completed Work Summary ============
slide = base("四、已完成工作总结", "PART 4 实施路线")
card(slide, 0.5, 1.2, 6.0, 5.5, "已实现并验证的模块",
     "Phase A（已运行）:\n  ✓ T0质量门(OpenCV)\n  ✓ T1/T2检测(YOLO11s)\n  ✓ T5姿态(YOLO11n-pose)\n  ✓ T11同源(dHash)\n  ✓ 32图冻结证据(4.67FPS)\n\n"
     "Phase B（已运行）:\n  ✓ QA解析器(672条)\n  ✓ D1枚举(477 support/0 refute)\n  ✓ C3同图冲突(1张: 0615)\n  ✓ B3关键词grounding(否定修复)\n\n"
     "新增模块(本轮):\n  ✓ Florence-2 grounding(3图验证)\n  ✓ SSCD同源(32图328对)", PURPLE, 12)
card(slide, 6.7, 1.2, 6.0, 5.5, "已下载的模型与数据",
     "模型(scenario5/models/):\n  YOLO11n/s (5.4+18.4MB)\n  YOLO11n-pose (6MB)\n  Florence-2-base-ft (441MB, MIT)\n  SSCD (94MB, MIT)\n  RTMO-s ONNX (37.8MB, Apache)\n  VideoMAE (330MB)\n\n"
     "数据(scenario5/data/):\n  PPE hardhat (2.51GB, 13782图)\n  MeVA (8.67GB)\n  MOT17+MOT20 (11.52GB)\n  UCF-Crime (24.07GB)\n  总计: 46.76GB\n\n"
     "代码质量:\n  13项单测全通过\n  ruff check零报错\n  5个runs协议目录", GOLD, 12)

# ============ SLIDE 17: Conclusion ============
slide = base("五、总结", "CONCLUSION")
add_text(slide, "核心论点", 0.5, 1.2, 12, 0.5, 20, PURPLE, True, PP_ALIGN.CENTER)
add_text(slide,
         "视觉模型报告「看见了什么」\n"
         "规则引擎推导「这意味着什么」\n"
         "一致性校验判断「QA是否与可证结论一致」\n"
         "——三层不能合并，否则模型预测被循环当真值",
         0.5, 1.8, 12, 1.5, 16, DARK, False, PP_ALIGN.CENTER)
card(slide, 0.8, 3.6, 3.7, 2.5, "已确立",
     "12个视觉子任务\n4层上下文关联\n17项分拣(8项需视觉)\n四态判定语义\nNIE不是失败而是诚实", PURPLE, 12)
card(slide, 4.8, 3.6, 3.7, 2.5, "已验证",
     "Florence-2 grounding ✓\nSSCD同源检测 ✓\nYOLO+pose管线 ✓\n672条QA校验器 ✓\nC3真实冲突样本 ✓", MINT, 12)
card(slide, 8.8, 3.6, 3.7, 2.5, "下一步",
     "迭代1(2周):集成冲刺\n规则编译器→schema冻结\n→T6标定→D2联调\n→论文级评测", GOLD, 12)
add_text(slide, "谢谢", 0.5, 6.3, 12, 0.5, 24, PURPLE, True, PP_ALIGN.CENTER)

prs.save(str(PPT_OUT))
print(f"Generated: {PPT_OUT} ({len(prs.slides)} slides)")
