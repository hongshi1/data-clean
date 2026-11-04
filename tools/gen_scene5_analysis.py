"""Generate scene-5 analysis charts + insert 5 figures into 合稿 6.6.5.

Charts generated from real sleep-*.jsonl data:
  1. QA answer distribution + data scale analysis
  2. Conflict detection between before/after variants
Then insert into 合稿 alongside 3 existing screenshots.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/srs_project/paper/test_screenshots"
S5 = Path(r"C:\baidunetdiskdownload\5个场景数据集\20260924-场景5样例数据及需求说明文档")

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
BG_DARK = "#141a24"
CARD = "#252d3d"


def gen_scene5_analysis():
    """Generate 2 analysis charts from real scene-5 data."""
    OUT.mkdir(parents=True, exist_ok=True)

    # Load all data
    files = {
        "before\n(原始)": S5 / "sleep-before-all.jsonl",
        "after\n(4bit量化后)": S5 / "sleep-after-all.jsonl",
    }
    all_data = {}
    for label, path in files.items():
        records = [json.loads(l) for l in path.open(encoding="utf-8")]
        answers = []
        for rec in records:
            try:
                conv = rec.get("conversations", [])
                gpt = json.loads(conv[1].get("value", "{}"))
                answers.append(gpt.get("answer", -1))
            except (json.JSONDecodeError, IndexError):
                answers.append(-1)
        all_data[label] = answers

    # --- Chart 1: QA answer distribution ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG_DARK)

    # left: answer distribution grouped bar
    labels = ["answer=0\n(未检测到)", "answer=1\n(检测到睡岗)"]
    before_0 = all_data["before\n(原始)"].count(0)
    before_1 = all_data["before\n(原始)"].count(1)
    after_0 = all_data["after\n(4bit量化后)"].count(0)
    after_1 = all_data["after\n(4bit量化后)"].count(1)
    x = np.arange(2)
    bars1 = ax1.bar(x - 0.18, [before_0, before_1], 0.35,
                     label="量化前", color="#4472C4")
    bars2 = ax1.bar(x + 0.18, [after_0, after_1], 0.35,
                     label="量化后", color="#ED7D31")
    for bar, v in zip(bars1, [before_0, before_1]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 str(v), ha="center", color="white", fontsize=12)
    for bar, v in zip(bars2, [after_0, after_1]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 str(v), ha="center", color="white", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("样本数", color="white")
    ax1.set_title("场景五QA答案分布（96条×量化前后）",
                   fontsize=14, color="white", fontweight="bold")
    ax1.tick_params(colors="white")
    ax1.legend(facecolor=CARD, labelcolor="white")
    ax1.set_facecolor(BG_DARK)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # right: evidence length distribution
    ev_lens_b = []
    ev_lens_a = []
    for label, path in [("b", S5 / "sleep-before-all.jsonl"),
                          ("a", S5 / "sleep-after-all.jsonl")]:
        for line in path.open(encoding="utf-8"):
            rec = json.loads(line)
            try:
                conv = rec.get("conversations", [])
                gpt = json.loads(conv[1].get("value", "{}"))
                evs = gpt.get("evidence", [])
                if isinstance(evs, list):
                    if label == "b":
                        ev_lens_b.append(len(evs))
                    else:
                        ev_lens_a.append(len(evs))
            except (json.JSONDecodeError, IndexError):
                pass

    ax2.hist([ev_lens_b, ev_lens_a], bins=range(0, 8, 1),
             label=["量化前", "量化后"], color=["#4472C4", "#ED7D31"],
             edgecolor="white")
    ax2.set_xlabel("每条QA的evidence字段条数", color="white")
    ax2.set_ylabel("QA条数", color="white")
    ax2.set_title("场景五QA证据字段长度分布",
                   fontsize=14, color="white", fontweight="bold")
    ax2.tick_params(colors="white")
    ax2.legend(facecolor=CARD, labelcolor="white")
    ax2.set_facecolor(BG_DARK)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(OUT / "scene5_data_analysis.png", dpi=200,
                facecolor=BG_DARK, bbox_inches="tight")
    plt.close()

    # --- Chart 2: Conflict detection ---
    before_map = {}
    for line in (S5 / "sleep-before-4bit.jsonl").open(encoding="utf-8"):
        rec = json.loads(line)
        try:
            conv = rec.get("conversations", [])
            gpt = json.loads(conv[1].get("value", "{}"))
            before_map[rec.get("image", "")] = gpt.get("answer")
        except (json.JSONDecodeError, IndexError):
            pass

    conflicts = []
    agree = 0
    total_compared = 0
    for line in (S5 / "sleep-after-4bit.jsonl").open(encoding="utf-8"):
        rec = json.loads(line)
        img_name = rec.get("image", "")
        if img_name in before_map:
            total_compared += 1
            try:
                conv = rec.get("conversations", [])
                gpt = json.loads(conv[1].get("value", "{}"))
                after_ans = gpt.get("answer")
                if before_map[img_name] != after_ans:
                    conflicts.append((img_name, before_map[img_name], after_ans))
                else:
                    agree += 1
            except (json.JSONDecodeError, IndexError):
                pass

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG_DARK)

    # left: conflict summary pie
    sizes = [agree, len(conflicts)]
    colors_p = ["#70AD47", "#C00000"]
    labels_p = [f"结论一致\n{agree}条", f"结论冲突\n{len(conflicts)}条"]
    ax1.pie(sizes, labels=labels_p, colors=colors_p, autopct="%1.1f%%",
             startangle=90, textprops={"color": "white", "fontsize": 12})
    ax1.set_title(f"场景五量化前后结论一致性\n（对比{total_compared}张图片）",
                   fontsize=14, color="white", fontweight="bold")
    ax1.set_facecolor(BG_DARK)

    # right: conflict detail bar
    if conflicts:
        c_from = [f"{img[:15]}…" for img, _, _ in conflicts[:10]]
        c_vals = [f"{b}→{a}" for _, b, a in conflicts[:10]]
        y = np.arange(len(c_from))
        ax2.barh(y, [1] * len(c_from), color=["#C00000"] * len(c_from))
        ax2.set_yticks(y)
        ax2.set_yticklabels(c_from, fontsize=9, color="white")
        for i, v in enumerate(c_vals):
            ax2.text(1.05, i, v, va="center", color="white", fontsize=10)
        ax2.set_xlim(0, 1.5)
        ax2.set_xlabel("答案变化（量化前→量化后）", color="white")
        ax2.set_title(f"结论冲突明细（前{min(len(conflicts), 10)}张）",
                       fontsize=14, color="white", fontweight="bold")
        ax2.tick_params(colors="white")
        ax2.set_facecolor(BG_DARK)
    else:
        ax2.text(0.5, 0.5, "无冲突", ha="center", va="center",
                  color="white", fontsize=20)
        ax2.set_facecolor(BG_DARK)

    plt.tight_layout()
    plt.savefig(OUT / "scene5_conflict_analysis.png", dpi=200,
                facecolor=BG_DARK, bbox_inches="tight")
    plt.close()

    print(f"场景5分析图已生成")
    print(f"  scene5_data_analysis.png ({(OUT / 'scene5_data_analysis.png').stat().st_size // 1024}KB)")
    print(f"  scene5_conflict_analysis.png ({(OUT / 'scene5_conflict_analysis.png').stat().st_size // 1024}KB)")
    print(f"  对比样本: {total_compared}, 一致: {agree}, 冲突: {len(conflicts)}")


if __name__ == "__main__":
    gen_scene5_analysis()
