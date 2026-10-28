r"""CascadeVerify论文图生成: 出版级matplotlib (300dpi, PDF+PNG双格式, 中文字体).

六张图(数字全部经tools/paper_data.py从runs程序化提取):
  fig1 级联架构图   — 静态设计图(模块名来自系统实现), 经济学数字取eval_cascade
  fig2 违例演演进   — 17真实违例检出四阶段(4个eval_violations run)
  fig3 成本-质量Pareto — eval_cascade五配置 + eval_paper_matrix基线 + eval_router α扫描
  fig4 双登记洞察   — 真实违例 vs 变异注入检出率对照(eval_mutation交叉引用)
  fig5 跨文档gap    — 04号 vs 06号(eval_crossdoc)
  fig6 EGT文法定律  — 近拷贝 vs 叙事文法(2个train run + 2个eval run)

用法: python tools/make_paper_figures.py [--outdir docs/srs_project/paper/figures]
字体缺失(中文乱码)在save时即fail-fast(捕获Glyph missing警告).
"""
from __future__ import annotations

import argparse
import random
import sys
import warnings
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as pdata  # noqa: E402

BASE = pdata.BASE
OUT_DIR_DEFAULT = BASE / "docs/srs_project/paper/figures"
DPI = 300
SEED = 42

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10.5,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 9.5,
    "axes.linewidth": 0.9,
    "axes.edgecolor": "#444444",
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

C_BLUE_FILL = "#e7eef6"
C_BLUE_EDGE = "#3d6a99"
C_BLUE_MID = "#6f95b8"
C_BLUE_DARK = "#2c4f73"
C_ORANGE_FILL = "#fdf0e2"
C_ORANGE_EDGE = "#c07a3a"
C_GREEN_FILL = "#e3ede2"
C_GREEN_EDGE = "#4e7a55"
C_GRAY = "#666666"
C_ROUTER = "#9db3c8"


def save_fig(fig: plt.Figure, outdir: Path, name: str) -> list[Path]:
    """保存PDF+PNG(300dpi); 捕获Glyph missing警告→中文渲染失败即抛错(fail-fast)."""
    outdir.mkdir(parents=True, exist_ok=True)
    paths = [outdir / f"{name}.pdf", outdir / f"{name}.png"]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(paths[0], dpi=DPI)
        fig.savefig(paths[1], dpi=DPI)
    glyph_msgs = [str(w.message) for w in caught if "missing from font" in str(w.message)]
    if glyph_msgs:
        raise RuntimeError(f"{name}: 中文字体渲染缺失 → {glyph_msgs[:3]}")
    plt.close(fig)
    return paths


def draw_box(ax: plt.Axes, x: float, y: float, w: float, h: float, title: str,
              lines: list[str], fc: str, ec: str, *, ls: str = "-", lw: float = 1.3,
              title_fs: float = 10, body_fs: float = 9, title_dy: float = 0.34) -> None:
    """圆角框: 顶部加粗标题 + 居中正文(出版字号>=9pt)."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.10",
                                fc=fc, ec=ec, ls=ls, lw=lw, zorder=2))
    if title:
        ax.text(x + w / 2, y + h - title_dy, title, ha="center", va="center",
                fontsize=title_fs, fontweight="bold", color="#1a1a1a", zorder=3)
    if lines:
        body_h = h - (title_dy * 1.7 if title else 0)
        ax.text(x + w / 2, y + body_h / 2, "\n".join(lines), ha="center", va="center",
                fontsize=body_fs, color="#222222", zorder=3, linespacing=1.45)


def draw_diamond(ax: plt.Axes, cx: float, cy: float, hw: float, hh: float, label: str,
                 fc: str, ec: str, *, fs: float = 10) -> None:
    pts = [(cx - hw, cy), (cx, cy + hh), (cx + hw, cy), (cx, cy - hh)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=1.4, zorder=2))
    ax.text(cx, cy, label, ha="center", va="center", fontsize=fs,
            fontweight="bold", color="#1a1a1a", zorder=3)


def arrow(ax: plt.Axes, x1: float, y1: float, x2: float, y2: float, *,
          color: str = "#4a4a4a", lw: float = 1.4, style: str = "-|>") -> None:
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=1,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                mutation_scale=13, shrinkA=0, shrinkB=0))


def elbow_arrow(ax: plt.Axes, pts: list[tuple[float, float]], *,
                color: str = "#4a4a4a", lw: float = 1.4) -> None:
    """折线箭头: 中间段为直线, 最后一段带箭头."""
    for (xa, ya), (xb, yb) in zip(pts[:-2], pts[1:-1]):
        ax.plot([xa, xb], [ya, yb], color=color, lw=lw, zorder=1,
                solid_capstyle="round")
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    arrow(ax, xa, ya, xb, yb, color=color, lw=lw)


# ═══════════════════════════════════════════════════════════════════
# fig1 级联架构图
# ═══════════════════════════════════════════════════════════════════

def fig1_cascade_architecture(outdir: Path) -> list[Path]:
    cas = pdata.get_cascade_run()
    cq = {r["config"]: r for r in cas["cost_quality_table"]}
    n_cascade = cq["cascade"]["llm_invocations"]
    n_l3 = cq["l3_llm"]["llm_invocations"]
    cost_ratio = n_cascade / n_l3
    r_f1 = cas["configs"]["cascade"]["per_class"]["refute"]["f1"]
    r_p = cas["configs"]["cascade"]["per_class"]["refute"]["precision"]

    fig, ax = plt.subplots(figsize=(13.6, 8.4))
    ax.set_xlim(0, 17.6)
    ax.set_ylim(0, 10.4)
    ax.axis("off")

    ax.text(8.8, 10.05, "CascadeVerify：异构验证器级联架构", ha="center", va="center",
            fontsize=14, fontweight="bold")
    ax.text(8.8, 9.62, "（确定性符号层裁决可形式化claim，LLM只为残差claim付费）",
            ha="center", va="center", fontsize=10, color=C_GRAY)

    ax.add_patch(plt.Rectangle((0.35, 9.06), 0.42, 0.26, fc=C_BLUE_FILL, ec=C_BLUE_EDGE, lw=1))
    ax.text(0.92, 9.19, "确定性符号层（零LLM调用）", ha="left", va="center", fontsize=9)
    ax.add_patch(plt.Rectangle((0.35, 8.66), 0.42, 0.26, fc=C_ORANGE_FILL, ec=C_ORANGE_EDGE, lw=1))
    ax.text(0.92, 8.79, "神经残差层（L2 NLI / L3 LLM）", ha="left", va="center", fontsize=9)

    draw_box(ax, 0.3, 6.8, 2.5, 1.9, "输入", ["Question", "待核 Answer", "冻结证据块 E"],
             C_BLUE_FILL, C_BLUE_EDGE)
    arrow(ax, 2.88, 7.75, 3.24, 7.75)
    draw_box(ax, 3.3, 6.8, 2.7, 1.9, "DEQ 证据质量（可选）",
             ["E0 scope门·拒错域证据", "E1 检测项感知评分", "E2 语句对齐"],
             "#f4f7fa", C_BLUE_MID, ls="--", lw=1.1, title_fs=9.5)
    arrow(ax, 6.04, 7.75, 6.36, 7.75)

    ax.add_patch(FancyBboxPatch((6.4, 5.1), 4.6, 4.7,
                                boxstyle="round,pad=0.04,rounding_size=0.12",
                                fc="#dfe9f3", ec=C_BLUE_DARK, lw=1.6, zorder=2))
    ax.text(8.7, 9.42, "确定性专家族（L0 + L1 × 9）", ha="center", va="center",
            fontsize=11, fontweight="bold", zorder=3)
    draw_box(ax, 6.62, 8.6, 4.16, 0.62, "", ["L0 entity_detector · 实体/ID在场（TERM-05/07/08）"],
             "#cfdff0", C_BLUE_EDGE, body_fs=9)
    chips = [
        ("id_join · TERM-07", "enum_join · TERM-03"),
        ("numeric_z3 · PARAM", "sequence · LOGIC-03"),
        ("e1模板 · LOGIC-02", "trace · GJB-05"),
        ("coverage · GJB-01/04", "gjb_presence · GJB-01~11"),
    ]
    for r, (left, right) in enumerate(chips):
        y = 7.90 - r * 0.68
        for c, label in enumerate((left, right)):
            x = 6.62 + c * 2.14
            ax.add_patch(FancyBboxPatch((x, y), 2.02, 0.6,
                                        boxstyle="round,pad=0.03,rounding_size=0.08",
                                        fc="#eef4fa", ec=C_BLUE_MID, lw=1.0, zorder=3))
            ax.text(x + 1.01, y + 0.3, label, ha="center", va="center",
                    fontsize=9, zorder=4)
    ax.text(8.7, 5.4, "L1输出协议：Z3附SMT-LIB + unsat core（防scope laundering）",
            ha="center", va="center", fontsize=9, color=C_BLUE_DARK, zorder=3)

    arrow(ax, 11.04, 7.75, 11.36, 7.75)
    draw_box(ax, 11.4, 6.8, 2.6, 1.9, "per-claim 融合",
             ["refute > support > NIE", "无能力判定不否决", "已验证判定"],
             C_BLUE_FILL, C_BLUE_EDGE)
    arrow(ax, 14.04, 7.75, 14.3, 7.75)
    draw_diamond(ax, 15.3, 7.75, 0.98, 1.05, "已决？", "#dbe7f3", C_BLUE_EDGE)

    elbow_arrow(ax, [(16.28, 7.75), (17.02, 7.75), (17.02, 4.4)])
    ax.text(17.22, 6.0, "已决 · 硬判定", ha="center", va="center", fontsize=9,
            rotation=90, color=C_BLUE_DARK)

    elbow_arrow(ax, [(15.3, 6.7), (15.3, 4.78), (1.9, 4.78), (1.9, 4.42)],
                color="#8a5a2e")
    ax.text(8.4, 4.96, "未决（残差claim）", ha="center", va="center", fontsize=9.5,
            color="#8a5a2e")

    draw_box(ax, 0.3, 2.6, 3.3, 1.82, "残差派发（C1残差原则）",
             ["仅 semantic / conservative", "unresolved 且当前无refute；", "确定性refute短路残差通道"],
             C_ORANGE_FILL, C_ORANGE_EDGE, title_fs=9.5)
    arrow(ax, 3.64, 3.51, 4.96, 3.51, color="#8a5a2e")
    draw_box(ax, 5.0, 2.6, 3.3, 1.82, "L2 残差 NLI",
             ["EGT叙事文法微调", "mDeBERTa · gate=0.7"],
             C_ORANGE_FILL, C_ORANGE_EDGE, title_fs=9.5)
    arrow(ax, 8.34, 3.51, 9.26, 3.51, color="#8a5a2e")
    draw_diamond(ax, 10.15, 3.5, 0.85, 0.92, "refute\n候选？", "#fae8d4", C_ORANGE_EDGE, fs=9.5)
    arrow(ax, 11.0, 3.5, 11.66, 3.5, color="#8a5a2e")
    ax.text(11.33, 3.78, "是·升级", ha="center", va="bottom", fontsize=9, color="#8a5a2e")
    draw_box(ax, 11.7, 2.6, 2.7, 1.82, "L3 LLM 复检",
             ["聚焦prompt·批量残差claim", "缓存接口（可复现）"],
             C_ORANGE_FILL, C_ORANGE_EDGE, title_fs=9.5)
    elbow_arrow(ax, [(10.15, 2.58), (10.15, 1.62), (15.9, 1.62), (15.9, 2.1)],
                color="#8a5a2e")
    ax.text(12.9, 1.84, "否 · S/N直通", ha="center", va="bottom", fontsize=9, color="#8a5a2e")
    arrow(ax, 14.44, 3.51, 14.86, 3.51, color="#8a5a2e")

    draw_box(ax, 14.9, 2.1, 2.5, 2.3, "跨claim聚合 → 输出",
             ["任一refute → refute", "全部support → support", "否则 → NIE", "判定+定位ℓ+理由j"],
             C_GREEN_FILL, C_GREEN_EDGE, title_fs=9.5, lw=1.6)

    ax.add_patch(FancyBboxPatch((0.3, 0.15), 9.2, 1.15,
                                boxstyle="round,pad=0.04,rounding_size=0.10",
                                fc="#f7f7f4", ec="#999999", ls="--", lw=1.0, zorder=2))
    ax.text(4.9, 0.72,
            f"级联经济学（91QA实测）：cascade = {n_cascade}次LLM调用（{cost_ratio:.0%}全量L3成本，"
            f"全量{n_l3}次） → 五配置最优 refute F1 = {r_f1:.3f}（P = {r_p:.3f}）",
            ha="center", va="center", fontsize=9.5, color="#333333", zorder=3)

    return save_fig(fig, outdir, "fig1_cascade_architecture")


# ═══════════════════════════════════════════════════════════════════
# fig2 违例检出演进
# ═══════════════════════════════════════════════════════════════════

def fig2_violation_evolution(outdir: Path) -> list[Path]:
    stages = pdata.get_violation_evolution()
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    x = np.arange(len(stages))
    rates = [s["rate"] * 100 for s in stages]
    colors = ["#b9cde3", "#8fb0d1", "#5e8cb8", "#2f5e8c"]
    bars = ax.bar(x, rates, width=0.56, color=colors, edgecolor="#274a6d", lw=0.8, zorder=3)
    for xi, s, b in zip(x, stages, bars):
        ax.text(xi, s["rate"] * 100 + 1.6, f"{s['detected']}/{s['n']}",
                ha="center", va="bottom", fontsize=11, fontweight="bold", color="#1a1a1a")
    notes = [
        ("", ""),
        ("+id_join专家", f"identifier {stages[0]['identifier'][0]}/5 → {stages[1]['identifier'][0]}/5"),
        ("+enum_join专家", f"enumeration {stages[1]['enumeration'][0]}/4 → {stages[2]['enumeration'][0]}/4"),
        ("+coverage专家", "VIO-17合格性覆盖闭合"),
    ]
    for xi, (n1, n2) in zip(x, notes):
        if n1:
            y0 = stages[int(xi)]["rate"] * 100 + 6.6
            ax.text(xi, y0 + 4.6, n1, ha="center", va="bottom", fontsize=9,
                    fontweight="bold", color="#274a6d")
            ax.text(xi, y0, n2, ha="center", va="bottom", fontsize=9, color="#444444")
    ax.set_xticks(x)
    ax.set_xticklabels([s["stage"] for s in stages], fontsize=10)
    ax.set_ylabel("检出率（%）")
    ax.set_ylim(0, 112)
    ax.set_title("17条真实违例的检出演进：失败归因 → 定向补专家 → 复测", fontsize=12.5)
    ax.grid(axis="y", ls=":", color="#bbbbbb", lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    undetected_final = ", ".join(i.replace("DOC04-VIO-", "VIO-") for i in stages[3]["undetected"])
    ax.text(0.985, 0.035, f"终态唯一未检出：{undetected_final}（document_name）",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=C_GRAY)
    return save_fig(fig, outdir, "fig2_violation_evolution")


# ═══════════════════════════════════════════════════════════════════
# fig3 成本-质量Pareto
# ═══════════════════════════════════════════════════════════════════

def fig3_cost_quality_pareto(outdir: Path) -> list[Path]:
    pm = pdata.get_paper_matrix()
    cas = pdata.get_cascade_run()
    router = pdata.get_router_run()
    cq = {r["config"]: r for r in cas["cost_quality_table"]}

    def r_f1(cfg: dict[str, Any]) -> float:
        return cfg["per_class"]["refute"]["f1"]

    sys_pts: list[tuple[str, float, float, float]] = []
    for name in ("B0", "B3"):
        b = pm["baselines"][name]
        sys_pts.append((name, b["llm_calls"]["invocations"], b["macro_f1"], r_f1(b)))
    for name, label in (("l2_nli", "L2 NLI"), ("cascade_conformal", "conformal"), ("cascade", "cascade")):
        sys_pts.append((label, cq[name]["llm_invocations"], cq[name]["macro_f1"],
                        r_f1(cas["configs"][name])))
    for name in ("B4", "B5", "B2"):
        b = pm["baselines"][name]
        sys_pts.append((name, b["llm_calls"]["invocations"], b["macro_f1"], r_f1(b)))

    sweep = sorted(router["pareto_points"], key=lambda p: p["llm_invocations"])
    sweep_x = [p["llm_invocations"] for p in sweep]
    sweep_macro = [p["macro_f1"] for p in sweep]
    sweep_rf1 = [p["refute_f1"] for p in sweep]
    oracle = router["oracle_router_ceiling"]

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.6))
    label_offsets = {
        "macro-F1": {
            "B0": (0.7, -0.012, "left"), "B3": (0.7, 0.010, "left"),
            "L2 NLI": (0.7, 0.006, "left"), "conformal": (-1.2, -0.034, "right"),
            "B4": (0.9, 0.012, "left"), "B5": (0.9, -0.038, "left"),
            "B2": (0.9, -0.044, "left"),
        },
        "refute F1": {
            "B0": (0.7, 0.008, "left"), "B3": (0.7, 0.012, "left"),
            "L2 NLI": (0.7, 0.010, "left"), "conformal": (-1.2, -0.038, "right"),
            "B4": (0.9, 0.012, "left"), "B5": (0.9, -0.048, "left"),
            "B2": (0.9, 0.028, "left"),
        },
    }
    panels = [("macro-F1", sweep_macro, 2, (0.20, 1.02), "macro_f1"),
              ("refute F1", sweep_rf1, 3, (-0.02, 1.02), "refute_f1")]
    for ax, (ylab, sweep_y, vi, ylim, key) in zip(axes, panels):
        ax.plot(sweep_x, sweep_y, "-o", color=C_ROUTER, lw=1.2, ms=3.5, zorder=2,
                label="学习路由 α扫描")
        ax.plot([oracle["llm_invocations"]], [oracle[key]], "*", ms=13, mfc="none",
                mec="#555555", mew=1.3, zorder=4, label="oracle路由上限（分析用）")
        for name, n_calls, macro, rf1 in sys_pts:
            val = (macro, rf1)[vi - 2]
            if name == "cascade":
                ax.plot([n_calls], [val], "*", ms=17, mfc="#e8a33d",
                        mec="#8a5a10", mew=1.1, zorder=6)
                continue
            ax.plot([n_calls], [val], "o", ms=6.5,
                    mfc="#4a76a8" if name != "conformal" else "#b0b0b0",
                    mec="#274a6d", mew=0.7, zorder=5)
            dx, dy, ha = label_offsets[ylab][name]
            ax.text(n_calls + dx, val + dy, name, fontsize=9, ha=ha, color="#333333")
        ax.set_xlabel("LLM调用数（invocations）")
        ax.set_ylabel(ylab)
        ax.set_xlim(-3, 97)
        ax.set_ylim(*ylim)
        ax.grid(ls=":", color="#bbbbbb", lw=0.6, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)

    cas_pt = next(p for p in sys_pts if p[0] == "cascade")
    n_l3_full = cq["l3_llm"]["llm_invocations"]
    axes[1].annotate(
        f"cascade（L2→L3升级）\n{cas_pt[1]}次调用 = {cas_pt[1] / n_l3_full:.0%}成本\n"
        f"最优refute F1 = {cas_pt[3]:.3f}",
        xy=(cas_pt[1], cas_pt[3]), xytext=(28, 0.94),
        fontsize=9.5, fontweight="bold", color="#8a5a10", ha="left",
        arrowprops=dict(arrowstyle="->", color="#8a5a10", lw=1.1,
                        connectionstyle="arc3,rad=-0.25"))
    axes[0].set_title("(a) macro-F1 vs LLM成本", fontsize=11.5)
    axes[1].set_title("(b) refute F1 vs LLM成本", fontsize=11.5)
    axes[1].legend(loc="lower right", frameon=False, fontsize=9)
    fig.suptitle("成本-质量Pareto：级联以18%成本达最优refute F1（91QA vs silver）",
                 fontsize=12.5, y=1.02)
    return save_fig(fig, outdir, "fig3_cost_quality_pareto")


# ═══════════════════════════════════════════════════════════════════
# fig4 双登记洞察：真实违例 vs 变异注入
# ═══════════════════════════════════════════════════════════════════

def fig4_mutation_vs_violation(outdir: Path) -> list[Path]:
    mut = pdata.get_mutation_run()
    rows = mut["violation_cross_reference"]["rows"]
    cats = ["identifier", "enumeration", "exception_template", "traceability"]
    by_cat = {r["violation_category"]: r for r in rows}
    real = [by_cat[c]["real_detection_rate"] for c in cats]
    inj = [by_cat[c]["injection_detection_rate"] for c in cats]
    real_cnt = [(by_cat[c]["real_detected"], by_cat[c]["n_real"]) for c in cats]
    inj_cnt = [(by_cat[c]["injection_detected"], by_cat[c]["injection_n"]) for c in cats]

    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    x = np.arange(len(cats))
    w = 0.36
    ax.bar(x - w / 2, real, w, color="#2f5e8c", ec="#1d3f61", lw=0.8,
           label="真实违例（证据侧双登记）", zorder=3)
    inj_plot = [v if v is not None else 0.0 for v in inj]
    ax.bar(x + w / 2, inj_plot, w, color="#e8b075", ec="#b0722e", lw=0.8,
           label="注入变异（answer侧单边破坏）", zorder=3)
    for xi, (rate, (d, n)) in zip(x, zip(real, real_cnt)):
        ax.text(xi - w / 2, rate + 0.02, f"{d}/{n}", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color="#1d3f61")
    for xi, (rate, (d, n)) in zip(x, zip(inj, inj_cnt)):
        if rate is None:
            ax.text(xi + w / 2, 0.035, "无适用\n算子", ha="center", va="bottom",
                    fontsize=8.8, color=C_GRAY)
            continue
        ax.text(xi + w / 2, rate + 0.02, f"{d}/{n}", ha="center", va="bottom",
                fontsize=9.5, color="#8a5210")
        delta = (rate - 1.0) * 100
        ax.text(xi + w / 2, rate + 0.085, f"Δ={delta:.1f}pp", ha="center", va="bottom",
                fontsize=9, color="#8a5210")
    ax.set_xticks(x)
    labels = {"identifier": "identifier\n(TERM-07)", "enumeration": "enumeration\n(TERM-03)",
              "exception_template": "exception_template\n(LOGIC-02)", "traceability": "traceability\n(GJB-05)"}
    ax.set_xticklabels([labels[c] for c in cats], fontsize=10)
    ax.set_ylabel("检出率")
    ax.set_ylim(0, 1.24)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_title("证据侧双登记 vs answer侧单边破坏：同通道两类检出率", fontsize=12.5)
    ax.legend(loc="upper right", frameon=False, fontsize=9.5)
    ax.grid(axis="y", ls=":", color="#bbbbbb", lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(0.985, 0.80,
            "真实违例：矛盾在证据侧多处登记（表·节标题·正文互相冲突）\n→ join专家可锚定发起比对\n"
            "注入变异：仅破坏answer侧，证据侧无冲突登记\n→ 同一通道近乎失明",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.8, color="#444444",
            bbox=dict(fc="#f7f7f4", ec="#bbbbbb", ls="--", lw=0.7, pad=4.0))
    return save_fig(fig, outdir, "fig4_mutation_vs_violation")


# ═══════════════════════════════════════════════════════════════════
# fig5 跨文档泛化gap
# ═══════════════════════════════════════════════════════════════════

def fig5_crossdoc_gap(outdir: Path) -> list[Path]:
    cd = pdata.get_crossdoc_run()
    gap = cd["generalization_gap"]
    configs = ["deterministic", "cascade"]
    titles = {"deterministic": "deterministic（9专家栈）", "cascade": "cascade（L2→L3升级）"}
    doc04 = [gap[c]["doc04_macro_f1"] for c in configs]
    doc06 = [gap[c]["doc06_macro_f1"] for c in configs]
    deltas = [gap[c]["delta_macro_f1"] for c in configs]

    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    x = np.arange(len(configs))
    w = 0.32
    ax.bar(x - w / 2, doc04, w, color="#2f5e8c", ec="#1d3f61", lw=0.8,
           label="04号（91QA, silver, 训练文法同源）", zorder=3)
    ax.bar(x + w / 2, doc06, w, color="#e8b075", ec="#b0722e", lw=0.8,
           label="06号（30条, sound, 自然复述文法）", zorder=3)
    for xi, (v04, v06, d) in enumerate(zip(doc04, doc06, deltas)):
        ax.text(xi - w / 2, v04 + 0.015, f"{v04:.4f}", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color="#1d3f61")
        ax.text(xi + w / 2, v06 + 0.015, f"{v06:.4f}", ha="center", va="bottom",
                fontsize=9.5, color="#8a5210")
        ax.annotate("", xy=(xi + w / 2, v06 + 0.06), xytext=(xi - w / 2, v04 + 0.06),
                    arrowprops=dict(arrowstyle="->", color="#a03030", lw=1.2,
                                    connectionstyle="arc3,rad=0.25"))
        ax.text(xi, max(v04, v06) + 0.085, f"Δ = {d:.4f}", ha="center", va="bottom",
                fontsize=10.5, fontweight="bold", color="#a03030")
    ax.set_xticks(x)
    ax.set_xticklabels([titles[c] for c in configs], fontsize=10)
    ax.set_ylabel("macro-F1")
    ax.set_ylim(0, 1.02)
    ax.set_title("跨文档泛化gap（04号 → 06号）：正则文法层的结构性缺口", fontsize=12.5)
    ax.legend(loc="upper right", frameon=False, fontsize=9.5)
    ax.grid(axis="y", ls=":", color="#bbbbbb", lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    return save_fig(fig, outdir, "fig5_crossdoc_gap")


# ═══════════════════════════════════════════════════════════════════
# fig6 EGT合成文法定律
# ═══════════════════════════════════════════════════════════════════

def fig6_egt_grammar(outdir: Path) -> list[Path]:
    g = pdata.get_egt_grammar()
    metrics = ["dev_macro_f1", "real_macro_f1", "real_refute_recall"]
    metric_labels = ["dev macro-F1\n（合成分布内）", "91QA真实 macro-F1\n（vs silver）",
                     "91QA真实 refute召回"]
    near = [g["near_copy"][m] for m in metrics]
    narr = [g["narrative"][m] for m in metrics]

    fig, ax = plt.subplots(figsize=(7.6, 4.7))
    x = np.arange(len(metrics))
    w = 0.34
    ax.bar(x - w / 2, near, w, color="#b9cde3", ec="#5b7fa6", lw=0.8,
           label="近拷贝文法（EGT-v2, 3000样本）", zorder=3)
    ax.bar(x + w / 2, narr, w, color="#2f5e8c", ec="#1d3f61", lw=0.8,
           label="叙事文法（EGT-v3, 4500样本）", zorder=3)
    for xi, (vn, vv) in enumerate(zip(near, narr)):
        ax.text(xi - w / 2, vn + 0.015, f"{vn:.4f}", ha="center", va="bottom",
                fontsize=9.5, color="#3d6a99")
        ax.text(xi + w / 2, vv + 0.015, f"{vv:.4f}", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color="#1d3f61")
    ax.annotate("", xy=(2 + w / 2 - 0.03, g["narrative"]["real_refute_recall"] - 0.06),
                xytext=(2 - w / 2 + 0.03, g["near_copy"]["real_refute_recall"] + 0.06),
                arrowprops=dict(arrowstyle="->", color="#a03030", lw=1.3,
                                connectionstyle="arc3,rad=-0.25"))
    ax.text(1.98, 0.62, "0.375 → 0.875", ha="center", va="bottom", fontsize=10.5,
            fontweight="bold", color="#a03030")
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontsize=10)
    ax.set_ylabel("分数")
    ax.set_ylim(0, 1.12)
    ax.set_title("EGT合成文法定律：dev分数≈持平，真实refute召回翻倍", fontsize=12.5)
    ax.legend(loc="lower left", frameon=False, fontsize=9.5)
    ax.grid(axis="y", ls=":", color="#bbbbbb", lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(0.985, 0.03, "dev分数对真实迁移零预测力：合成文法必须匹配真实claim形态",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=C_GRAY)
    return save_fig(fig, outdir, "fig6_egt_grammar")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(OUT_DIR_DEFAULT))
    parser.add_argument("--only", default=None,
                        help="只生成指定图（fig1..fig6的函数名或编号）")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    random.seed(SEED)
    np.random.seed(SEED)

    builders = {
        "fig1": fig1_cascade_architecture,
        "fig2": fig2_violation_evolution,
        "fig3": fig3_cost_quality_pareto,
        "fig4": fig4_mutation_vs_violation,
        "fig5": fig5_crossdoc_gap,
        "fig6": fig6_egt_grammar,
    }
    todo = builders.items()
    if args.only:
        keys = {args.only, args.only.replace("fig", "fig" + "_")}
        todo = [(k, fn) for k, fn in builders.items() if k in keys or fn.__name__ == args.only]

    written: list[Path] = []
    for key, fn in todo:
        paths = fn(outdir)
        written.extend(paths)
        for p in paths:
            kb = p.stat().st_size / 1024
            print(f"[OK] {p.name:36s} {kb:8.1f} KB")
    print(f"共生成 {len(written)} 个文件 → {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
