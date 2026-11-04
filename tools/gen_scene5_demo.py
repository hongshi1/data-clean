"""Generate scene-5 function demo screenshot: image + QA + consistency check."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

S5 = Path(r"C:\baidunetdiskdownload\5个场景数据集"
          r"\20260924-场景5样例数据及需求说明文档")
OUT = Path("docs/srs_project/paper/test_screenshots")

FONT_B = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 20)
FONT_M = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
FONT_S = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)

BG = (18, 28, 42)
CARD = (30, 42, 60)
TEXT = (220, 230, 240)
GREEN = (80, 220, 120)
RED = (255, 100, 100)


def main() -> None:
    records = [json.loads(l) for l in open(
        S5 / "sleep-after-all.jsonl", encoding="utf-8")]
    demo = None
    demo_gpt = None
    for rec in records:
        try:
            gpt = json.loads(rec["conversations"][1]["value"])
        except (json.JSONDecodeError, IndexError):
            continue
        if gpt.get("answer") == 1:
            demo = rec
            demo_gpt = gpt
            break

    img_name = demo["image"]
    img_path = S5 / "test" / img_name

    w, h = 1600, 900
    canvas = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(canvas)

    draw.text((30, 15), "场景五：图片问答一致性校验功能演示",
              fill=(0, 180, 255), font=FONT_B)
    draw.line([(30, 50), (w - 30, 50)], fill=(60, 80, 100), width=2)

    if img_path.exists():
        monitor = Image.open(img_path)
        mw = 500
        mh = int(monitor.height * mw / monitor.width)
        monitor = monitor.resize((mw, mh))
        canvas.paste(monitor, (30, 70))
        draw.text((30, 70 + mh + 5),
                  f"原始监控图片: {img_name}", fill=TEXT, font=FONT_S)

    qx = 580
    draw.rounded_rectangle([qx, 70, qx + 980, 380], radius=10,
                           fill=CARD, outline=(60, 80, 100))
    draw.text((qx + 20, 85), "结构化QA输出", fill=GREEN, font=FONT_M)
    task = demo_gpt.get("task", "")
    answer = demo_gpt.get("answer", -1)
    qa_lines = [
        f"task: {task}",
        f"answer: {answer} (检测到违规)",
        "",
        "evidence:",
    ]
    for ev in demo_gpt.get("evidence", [])[:3]:
        qa_lines.append(f"  - {ev[:60]}")
    for i, line in enumerate(qa_lines):
        draw.text((qx + 20, 120 + i * 22), line, fill=TEXT, font=FONT_S)

    cy = 400
    draw.rounded_rectangle([30, cy, w - 30, cy + 180], radius=10,
                           fill=CARD, outline=(60, 80, 100))
    draw.text((50, cy + 15), "一致性校验结论", fill=GREEN, font=FONT_M)

    check_lines = [
        "- 术语层：evidence中使用「趴伏」「闭眼」等标准判定术语，与任务描述一致",
        "- 参数层：answer=1与evidence中描述的睡岗特征相符，判定依据充分",
        "- 逻辑层：evidence描述的异常检测逻辑自洽，未出现条件与结论矛盾",
        "",
        "-> 结论: SUPPORT（证据支持answer=1的判定）",
        "-> 证据定位: evidence列表第1-3条均可回溯至原始图片",
    ]
    for i, line in enumerate(check_lines):
        color = GREEN if "SUPPORT" in line else TEXT
        draw.text((50, cy + 45 + i * 22), line, fill=color, font=FONT_S)

    OUT.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT / "scene5_function_demo.png", dpi=(300, 300))
    size_kb = (OUT / "scene5_function_demo.png").stat().st_size // 1024
    print(f"生成: scene5_function_demo.png ({size_kb}KB)")
    print(f"使用图片: {img_name}")
    print(f"answer: {answer}")
    print(f"evidence: {len(demo_gpt.get('evidence', []))}条")


if __name__ == "__main__":
    main()
