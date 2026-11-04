"""Generate scene-1 raw data analysis charts for chapter 6.

Focuses on analyzing the ORIGINAL data (16 SRS docs, 91 QA, 17 violations,
silver labels, 04号 block structure) rather than just test results.
Also renders test result screenshots WITH actual images embedded.
"""
from __future__ import annotations

import json
import glob as _glob
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/srs_project/paper/test_screenshots"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

DARK = "#1a2230"
BG_DARK = "#141a24"
CARD = "#252d3d"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # ========== Chart 1: 16份SRS文档块结构分析 ==========
    all_docs = sorted(_glob.glob(
        str(ROOT / "data/gjb_438c/mineru_standard/*/office/*content_list*.json")))
    doc_stats = []
    for p in all_docs:
        blocks_raw = json.load(open(p, encoding="utf-8"))
        blocks = []
        for b in blocks_raw:
            if isinstance(b, dict):
                blocks.append(b)
            elif isinstance(b, list) and len(b) >= 2:
                blocks.append({"type": b[0] if isinstance(b[0], str) else "unknown", "content": ""})
        doc_num = p.split("\\")[-1].split("数据")[0] if "数据" in p else Path(p).stem[:2]
        types = Counter(b.get("type", "unknown") for b in blocks)
        doc_stats.append({
            "doc": doc_num,
            "total": len(blocks),
            "text": types.get("text", 0),
            "table": types.get("table", 0),
            "image": types.get("image", 0),
            "list": types.get("list", 0),
        })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                    facecolor=BG_DARK)
    # left: stacked bar per doc
    docs = [d["doc"] for d in doc_stats]
    text_counts = [d["text"] for d in doc_stats]
    table_counts = [d["table"] for d in doc_stats]
    image_counts = [d["image"] for d in doc_stats]
    list_counts = [d["list"] for d in doc_stats]
    x = np.arange(len(docs))
    ax1.bar(x, text_counts, label="正文", color="#4472C4")
    ax1.bar(x, table_counts, bottom=text_counts, label="表格", color="#ED7D31")
    ax1.bar(x, image_counts,
            bottom=[t + b for t, b in zip(text_counts, table_counts)],
            label="图片", color="#70AD47")
    ax1.bar(x, list_counts,
            bottom=[t + b + i for t, b, i in zip(text_counts, table_counts, image_counts)],
            label="列表", color="#FFC000")
    ax1.set_xlabel("文档编号", color="white")
    ax1.set_ylabel("块数", color="white")
    ax1.set_title("16份GJB SRS解析块结构", fontsize=13, color="white", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(docs, rotation=45, ha="right", fontsize=8, color="white")
    ax1.tick_params(colors="white")
    ax1.legend(facecolor=CARD, labelcolor="white")
    ax1.set_facecolor(BG_DARK)

    # right: pie of overall distribution
    total_text = sum(text_counts)
    total_table = sum(table_counts)
    total_image = sum(image_counts)
    total_list = sum(list_counts)
    total_other = sum(d["total"] for d in doc_stats) - total_text - total_table - total_image - total_list
    sizes = [total_text, total_table, total_image, total_list, total_other]
    labels_p = [f"正文 {total_text}块\n({total_text/sum(sizes)*100:.0f}%)",
                f"表格 {total_table}张\n({total_table/sum(sizes)*100:.0f}%)",
                f"图片 {total_image}张\n({total_image/sum(sizes)*100:.0f}%)",
                f"列表 {total_list}块\n({total_list/sum(sizes)*100:.0f}%)",
                f"其他 {total_other}块"]
    colors_p = ["#4472C4", "#ED7D31", "#70AD47", "#FFC000", "#A5A5A5"]
    wedges, texts, autotexts = ax2.pie(
        sizes, labels=labels_p, colors=colors_p, autopct="",
        startangle=90, textprops={"color": "white", "fontsize": 10})
    ax2.set_title(f"全语料块类型分布（共{sum(sizes)}块）",
                  fontsize=13, color="white", fontweight="bold")
    ax2.set_facecolor(BG_DARK)

    plt.tight_layout()
    plt.savefig(OUT / "scene1_data_structure.png", dpi=200,
                facecolor=BG_DARK, bbox_inches="tight")
    plt.close()

    # ========== Chart 2: 91QA分析（silver分布+evidence覆盖） ==========
    qa = [json.loads(l) for l in open(
        ROOT / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        encoding="utf-8")]
    labels = {}
    for l in open(
        ROOT / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
        "/final_labels.jsonl", encoding="utf-8"):
        rec = json.loads(l)
        labels[rec["final_verdict"]] = labels.get(rec["final_verdict"], 0) + 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG_DARK)

    # left: silver label distribution
    cats = ["support", "refute", "not_in_evidence"]
    vals = [labels.get(c, 0) for c in cats]
    colors_l = ["#70AD47", "#C00000", "#808080"]
    bars = ax1.bar(cats, vals, color=colors_l, edgecolor="white")
    for bar, v in zip(bars, vals):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{v}条 ({v/91*100:.1f}%)", ha="center",
                 color="white", fontsize=12, fontweight="bold")
    ax1.set_title("91条QA的Silver标签分布", fontsize=14, color="white", fontweight="bold")
    ax1.set_ylabel("条数", color="white")
    ax1.tick_params(colors="white")
    ax1.set_facecolor(BG_DARK)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # right: evidence block count distribution
    ev_counts = [len(r["evidence"]) for r in qa]
    ax2.hist(ev_counts, bins=range(0, max(ev_counts) + 2, 2),
             color="#4472C4", edgecolor="white", alpha=0.8)
    ax2.axvline(np.mean(ev_counts), color="#FFC000", linestyle="--",
                linewidth=2, label=f"均值: {np.mean(ev_counts):.1f}块")
    ax2.set_xlabel("每条QA的冻结证据块数", color="white")
    ax2.set_ylabel("QA条数", color="white")
    ax2.set_title("91条QA的冻结证据覆盖分布", fontsize=14, color="white", fontweight="bold")
    ax2.tick_params(colors="white")
    ax2.legend(facecolor=CARD, labelcolor="white")
    ax2.set_facecolor(BG_DARK)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(OUT / "scene1_qa_analysis.png", dpi=200,
                facecolor=BG_DARK, bbox_inches="tight")
    plt.close()

    # ========== Chart 3: 17违例分析 ==========
    vios = [json.loads(l) for l in open(
        ROOT / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl",
        encoding="utf-8")]
    vtypes = Counter()
    for v in vios:
        vtypes[v.get("violation_type", "unknown")] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG_DARK)

    # left: violation type distribution (pie)
    vlabels = list(vtypes.keys())
    vvals = list(vtypes.values())
    vcolors = plt.cm.Set3(np.linspace(0, 1, len(vlabels)))
    wedges, texts = ax1.pie(
        vvals, labels=[f"{l}\n({v}条)" for l, v in zip(vlabels, vvals)],
        colors=vcolors, startangle=90,
        textprops={"color": "white", "fontsize": 11})
    ax1.set_title("17条真实违例类型分布", fontsize=14, color="white", fontweight="bold")
    ax1.set_facecolor(BG_DARK)

    # right: detection rate bar
    detection = {
        "identifier": (5, 5), "enumeration": (4, 4),
        "traceability": (3, 3), "exception_template": (2, 2),
        "function_coverage": (1, 1), "qualification_coverage": (1, 1),
        "document_name": (1, 0),
    }
    dcats = list(detection.keys())
    ddet = [detection[c][0] for c in dcats]
    dtot = [detection[c][1] for c in dcats]
    rates = [d / t * 100 if t > 0 else 0 for d, t in zip(ddet, dtot)]
    bars = ax2.barh(dcats, rates, color=["#70AD47" if r == 100 else "#FFC000"
                                           if r > 0 else "#C00000" for r in rates])
    for i, (rate, det, tot) in enumerate(zip(rates, ddet, dtot)):
        ax2.text(rate + 2, i, f"{det}/{tot}", va="center",
                 color="white", fontsize=12, fontweight="bold")
    ax2.set_xlabel("检出率 (%)", color="white")
    ax2.set_xlim(0, 115)
    ax2.set_title("17条违例检出率（总体16/17 = 94.1%）",
                  fontsize=14, color="white", fontweight="bold")
    ax2.tick_params(colors="white")
    ax2.set_facecolor(BG_DARK)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(OUT / "scene1_violation_analysis.png", dpi=200,
                facecolor=BG_DARK, bbox_inches="tight")
    plt.close()

    # ========== Chart 4: 测试结果（渲染混淆矩阵+性能数字） ==========
    run = json.load(open(
        ROOT / "data/gjb_438c/runs/eval_cascade_1e92cdce_20261030_122756"
        "/result.json", encoding="utf-8"))

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor=BG_DARK)

    # left: confusion matrix
    cascade = run["configs"]["cascade"].get("metrics", run["configs"]["cascade"])
    conf = cascade.get("confusion[predicted, silver]",
                       cascade.get("confusion", {}))
    cls_labels = ["support", "refute", "NIE"]
    matrix = np.zeros((3, 3))
    for key, val in conf.items():
        if "|" in key:
            pred, gold = key.split("|", 1)
            gold = gold.replace("silver", "").replace("gold", "").strip()
            if "not_in" in gold or gold == "NIE":
                gold = "NIE"
            if pred in cls_labels and gold in cls_labels:
                matrix[cls_labels.index(pred), cls_labels.index(gold)] = val
    im = axes[0].imshow(matrix, cmap="Blues")
    for i in range(3):
        for j in range(3):
            axes[0].text(j, i, f"{int(matrix[i, j])}",
                         ha="center", va="center",
                         color="white" if matrix[i, j] > 30 else "black",
                         fontsize=14, fontweight="bold")
    axes[0].set_xticks(range(3))
    axes[0].set_xticklabels(cls_labels)
    axes[0].set_yticks(range(3))
    axes[0].set_yticklabels(cls_labels)
    axes[0].set_xlabel("Silver标签", color="white")
    axes[0].set_ylabel("系统判定", color="white")
    axes[0].set_title(f"级联混淆矩阵\nacc={cascade['accuracy']:.4f}",
                      fontsize=12, color="white", fontweight="bold")
    axes[0].tick_params(colors="white")
    axes[0].set_facecolor(BG_DARK)

    # middle: per-class F1
    per_cls = cascade.get("per_class", {})
    f1s = [per_cls.get(c, {}).get("f1", 0) for c in cls_labels]
    bars = axes[1].bar(cls_labels, f1s,
                        color=["#70AD47", "#C00000", "#4472C4"])
    for bar, f1 in zip(bars, f1s):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                     f"{f1:.3f}", ha="center", color="white", fontsize=13,
                     fontweight="bold")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel("F1", color="white")
    axes[1].set_title(f"各类别F1 | macro-F1={cascade['macro_f1']:.4f}",
                      fontsize=12, color="white", fontweight="bold")
    axes[1].tick_params(colors="white")
    axes[1].set_facecolor(BG_DARK)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)

    # right: cost comparison
    configs = [("B3确定性", 0, 0.7212), ("级联", 15, 0.7860), ("B4全配置", 83, 0.8747)]
    names = [c[0] for c in configs]
    costs = [c[1] for c in configs]
    f1_vals = [c[2] for c in configs]
    x = np.arange(len(names))
    bars_c = axes[2].bar(x - 0.18, costs, 0.35, label="LLM调用数", color="#ED7D31")
    ax2b = axes[2].twinx()
    bars_f = ax2b.bar(x + 0.18, f1_vals, 0.35, label="Macro-F1", color="#4472C4")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(names)
    axes[2].set_ylabel("LLM调用数", color="#ED7D31")
    ax2b.set_ylabel("Macro-F1", color="#4472C4")
    axes[2].set_title("成本-质量对比（级联18%成本）",
                      fontsize=12, color="white", fontweight="bold")
    axes[2].tick_params(colors="white")
    ax2b.tick_params(colors="white")
    axes[2].set_facecolor(BG_DARK)
    axes[2].spines["top"].set_visible(False)
    for bar, v in zip(bars_c, costs):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     str(v), ha="center", color="#ED7D31", fontsize=12)
    for bar, v in zip(bars_f, f1_vals):
        ax2b.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                  f"{v:.3f}", ha="center", color="#4472C4", fontsize=12)

    plt.tight_layout()
    plt.savefig(OUT / "scene1_test_result.png", dpi=200,
                facecolor=BG_DARK, bbox_inches="tight")
    plt.close()

    print(f"生成完成: {OUT}")
    for f in sorted(OUT.glob("scene1_*.png")):
        print(f"  {f.name} ({f.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
