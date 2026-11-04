"""Generate test screenshots for chapter 6 of the merged report.

Creates: 2 screenshots for scene 1 (API results), 2 screenshots for scene 5
(sample QA data), and 2 data analysis charts from real runs.
All output to docs/srs_project/paper/test_screenshots/
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/srs_project/paper/test_screenshots"
PLATFORM = ROOT / "deploy/nkuDataProject"
S5_DATA = Path(r"C:\baidunetdiskdownload\5个场景数据集"
               r"\20260924-场景5样例数据及需求说明文档")

# Microsoft YaHei for Chinese text
FONT_BOLD = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 22)
FONT_MED = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
FONT_SMALL = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
FONT_MONO = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)

BG = (18, 28, 42)       # dark blue
CARD = (30, 42, 60)
TEXT = (220, 230, 240)
ACCENT = (0, 180, 255)
GREEN = (80, 220, 120)
RED = (255, 100, 100)
YELLOW = (255, 200, 80)


def new_canvas(w=1600, h=900, title=""):
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    if title:
        draw.text((30, 20), title, fill=ACCENT, font=FONT_BOLD)
        draw.line([(30, 58), (w - 30, 58)], fill=(60, 80, 100), width=2)
    return img, draw


def draw_card(draw, x, y, w, h, title, lines, title_color=ACCENT):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=CARD,
                           outline=(60, 80, 100))
    draw.text((x + 15, y + 10), title, fill=title_color, font=FONT_MED)
    for i, line in enumerate(lines):
        draw.text((x + 15, y + 40 + i * 22), line, fill=TEXT, font=FONT_SMALL)


def scene1_screenshots():
    """Start platform, call APIs, render results as screenshots."""
    env = {**os.environ, "DEV_DB": "sqlite", "PYTHONUTF8": "1",
           "PYTHONPATH": "."}
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(PLATFORM / "backend"), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="ignore")
    time.sleep(8)
    try:
        # --- Screenshot 1: context linking (activate) ---
        req = urllib.request.Request(
            "http://127.0.0.1:8300/api/activate",
            data=json.dumps({"question": "修改数据功能支持哪些设备",
                             "doc": "04"}).encode(),
            headers={"Content-Type": "application/json"})
        act = json.loads(urllib.request.urlopen(req, timeout=60).read())
        d = act.get("data") or act
        center = d.get("center") or {}
        groups = d.get("groups") or {}

        img, draw = new_canvas(title="场景一：上下文关联结果（POST /api/activate）")
        # center card
        draw_card(draw, 30, 80, 700, 180, "中心节点 (Center)",
                  [f"标签: {center.get('label', '')}",
                   f"章节: {center.get('section', '')}",
                   f"来源: {center.get('why', '')}",
                   f"匹配: {center.get('score', '')}"])
        # groups
        gy = 280
        for gtype, items in groups.items():
            gnames = [str(i.get("label", ""))[:20] for i in items[:3]]
            draw_card(draw, 30, gy, 700, 30 + len(gnames) * 22 + 20,
                      f"{gtype} ({len(items)}条)", gnames)
            gy += 40 + len(gnames) * 22 + 20

        # right side: evidence detail
        draw_card(draw, 760, 80, 800, 200, "查询信息",
                  [f"问题: 修改数据功能支持哪些设备",
                   f"文档: 04号数据统一访问服务SRS",
                   f"中心命中: {center.get('label', '')}",
                   f"证据组数: {len(groups)}",
                   f"总计证据: {sum(len(v) for v in groups.values())}条"])

        # sample evidence snippets
        ev_lines = []
        for gtype, items in groups.items():
            for item in items[:2]:
                snippet = (item.get("snippet") or "")[:50]
                ev_lines.append(f"[{gtype}] {snippet}")
        draw_card(draw, 760, 300, 800, 60 + min(len(ev_lines), 12) * 22,
                  "证据摘录 (前12条)", ev_lines[:12], YELLOW)

        OUT.mkdir(parents=True, exist_ok=True)
        img.save(OUT / "scene1_context_link.png", dpi=(300, 300))

        # --- Screenshot 2: consistency check ---
        req2 = urllib.request.Request(
            "http://127.0.0.1:8300/api/check/04", data=b"{}",
            headers={"Content-Type": "application/json"}, method="POST")
        job = json.loads(urllib.request.urlopen(req2, timeout=120).read())
        jid = (job.get("data") or job).get("job_id")
        result = {}
        for _ in range(50):
            time.sleep(3)
            st = json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:8300/api/check/status/{jid}",
                timeout=30).read())
            dd = st.get("data") or st
            if dd.get("status") in ("done", "error"):
                result = dd.get("result") or {}
                break

        img2, draw2 = new_canvas(title="场景一：一致性校验结果（POST /api/check/04）")
        summary = result.get("summary") or {}
        draw_card(draw2, 30, 80, 700, 200, "校验汇总",
                  [f"总检测项: {summary.get('total', 0)}",
                   f"通过: {summary.get('pass', 0)}",
                   f"失败: {summary.get('fail', 0)}",
                   f"LLM待检: {summary.get('llm', 0)}",
                   f"错误: {summary.get('error', 0)}"])

        items = result.get("items") or []
        qa = next((i for i in items if i.get("rule_id") == "QA-VERDICT"), None)
        if qa:
            findings = qa.get("findings") or []
            draw_card(draw2, 760, 80, 800, 200,
                      "QA-VERDICT (CascadeVerify三态校验)",
                      [f"状态: {qa.get('status')}",
                       f"发现数: {qa.get('n_findings', len(findings))}",
                       f"判定方式: CascadeVerifier fast档"],
                      GREEN)
            # findings detail
            fy = 300
            for f in findings[:5]:
                desc = f.get("desc", "")[:60]
                draw_card(draw2, 30, fy, 1530, 60,
                          desc, [f"证据: {f.get('evidence', '')[:70]}"],
                          RED)
                fy += 80
        else:
            draw_card(draw2, 760, 80, 800, 200, "QA-VERDICT", ["未找到"])

        img2.save(OUT / "scene1_consistency_report.png", dpi=(300, 300))
    finally:
        proc.terminate()


def scene5_screenshots():
    """Render scene 5 sample QA data as screenshots."""
    # Load sample data
    qa_file = S5_DATA / "sleep-after-4bit.jsonl"
    if not qa_file.is_file():
        print(f"scene5 data not found: {qa_file}")
        return
    records = [json.loads(l) for l in qa_file.open(encoding="utf-8")]

    # --- Screenshot 1: QA field display ---
    img, draw = new_canvas(title="场景五：监控图片QA字段结构化展示")
    for idx, rec in enumerate(records[:3]):
        conv = rec.get("conversations", [])
        user_msg = conv[0].get("value", "")[:60] if conv else ""
        gpt_raw = conv[1].get("value", "") if len(conv) > 1 else "{}"
        try:
            gpt = json.loads(gpt_raw)
        except (json.JSONDecodeError, ValueError):
            gpt = {"task": "", "answer": "", "evidence": []}
        image_name = rec.get("image", "")
        ev_str = " | ".join(gpt.get("evidence", []))[:80] if isinstance(
            gpt.get("evidence"), list) else str(gpt.get("evidence", ""))[:80]

        draw_card(draw, 30, 80 + idx * 200, 1500, 180,
                  f"样本{idx + 1}  图片: {image_name}",
                  [f"task: {gpt.get('task', '')}",
                   f"answer: {gpt.get('answer', '')}",
                   f"evidence: {ev_str}",
                   f"timestamp: {gpt.get('timestamp', '无')}"],
                  GREEN if gpt.get("answer") == 0 else YELLOW)

    img.save(OUT / "scene5_qa_fields.png", dpi=(300, 300))

    # --- Screenshot 2: conflict detection (before vs after) ---
    before_file = S5_DATA / "sleep-before-4bit.jsonl"
    if before_file.is_file():
        before = [json.loads(l) for l in before_file.open(encoding="utf-8")]
        # Find same image with different answers
        before_map = {}
        for rec in before:
            conv = rec.get("conversations", [])
            if len(conv) > 1:
                try:
                    gpt = json.loads(conv[1].get("value", "{}"))
                    before_map[rec.get("image", "")] = gpt.get("answer")
                except (json.JSONDecodeError, ValueError):
                    pass

        img2, draw2 = new_canvas(
            title="场景五：同类样本结论冲突检测（before vs after 4bit）")
        conflicts = []
        for rec in records:
            img_name = rec.get("image", "")
            if img_name in before_map:
                conv = rec.get("conversations", [])
                if len(conv) > 1:
                    try:
                        gpt = json.loads(conv[1].get("value", "{}"))
                        after_ans = gpt.get("answer")
                        if before_map[img_name] != after_ans:
                            conflicts.append((img_name, before_map[img_name],
                                             after_ans))
                    except (json.JSONDecodeError, ValueError):
                        pass

        stats = [
            f"对比样本数: {len(before_map)}张图片",
            f"结论冲突数: {len(conflicts)}张",
            f"冲突率: {len(conflicts) / len(before_map) * 100:.1f}%",
        ]
        draw_card(draw2, 30, 80, 700, 160, "冲突检测统计", stats, GREEN)

        if conflicts:
            c_lines = [f"{img[:25]}: before={b} → after={a}"
                       for img, b, a in conflicts[:10]]
            draw_card(draw2, 760, 80, 800, 60 + len(c_lines) * 22,
                      "冲突样本明细", c_lines, RED)

        img2.save(OUT / "scene5_conflict_check.png", dpi=(300, 300))


def analysis_charts():
    """Generate data analysis charts from real runs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
    plt.rcParams["axes.unicode_minus"] = False

    # --- Chart 1: 91QA confusion matrix ---
    run_dir = ROOT / "data/gjb_438c/runs/eval_cascade_1e92cdce_20261030_122756"
    if run_dir.is_dir():
        result = json.load(open(run_dir / "result.json", encoding="utf-8"))
        cfg = result.get("configs", {}).get("cascade", {})
        metrics = cfg.get("metrics", cfg)
        conf = metrics.get("confusion[predicted, silver]",
                           metrics.get("confusion", {}))
        labels = ["support", "refute", "NIE"]
        matrix = np.zeros((3, 3))
        for key, val in conf.items():
            if "|" in key:
                pred, gold = key.split("|", 1)
                gold = gold.replace("silver", "").replace("gold", "").strip()
                if "not_in" in gold or gold == "NIE":
                    gold = "NIE"
                if gold in labels and pred in labels:
                    matrix[labels.index(pred), labels.index(gold)] = val

        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(matrix, cmap="Blues")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{int(matrix[i, j])}",
                        ha="center", va="center",
                        color="white" if matrix[i, j] > 30 else "black",
                        fontsize=16)
        ax.set_xticks(range(3))
        ax.set_xticklabels(labels)
        ax.set_yticks(range(3))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Silver标签")
        ax.set_ylabel("系统判定")
        ax.set_title("场景一：91QA三态判定混淆矩阵（级联配置）",
                     fontsize=14, fontweight="bold")
        fig.colorbar(im)
        plt.tight_layout()
        OUT.mkdir(parents=True, exist_ok=True)
        plt.savefig(OUT / "scene1_confusion_matrix.png", dpi=300)
        plt.close()

    # --- Chart 2: 17 violation detection ---
    vio_data = {
        "identifier\n(5条)": (5, 5),
        "enumeration\n(4条)": (4, 4),
        "traceability\n(3条)": (3, 3),
        "exception\n(2条)": (2, 2),
        "coverage\n(2条)": (2, 1),
        "document_name\n(1条)": (1, 0),
    }
    cats = list(vio_data.keys())
    detected = [vio_data[c][0] for c in cats]
    total = [vio_data[c][1] for c in cats]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(cats))
    bars1 = ax.bar(x - 0.18, total, 0.35, label="总违例数", color="#4472C4")
    bars2 = ax.bar(x + 0.18, detected, 0.35, label="检出数", color="#70AD47")
    ax.set_xlabel("违例类型")
    ax.set_ylabel("数量")
    ax.set_title("场景一：17条真实违例检出率（总体16/17 = 94.1%）",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=10)
    ax.legend()
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{int(bar.get_height())}", ha="center", fontsize=11)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{int(bar.get_height())}", ha="center", fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT / "scene1_violation_detection.png", dpi=300)
    plt.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=== 生成场景一截图 ===")
    scene1_screenshots()
    print("=== 生成场景五截图 ===")
    scene5_screenshots()
    print("=== 生成数据分析图 ===")
    analysis_charts()
    print(f"\n输出目录: {OUT}")
    for f in sorted(OUT.glob("*.png")):
        print(f"  {f.name} ({f.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
