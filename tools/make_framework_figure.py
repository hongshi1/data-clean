"""Regenerate the canonical framework figure for the consistency system.

v4: incorporates post-audit fixes (gate alignment, enum channel downgrade,
L3 budget expansion) and makes the algorithm flow crystal clear.
"""
from __future__ import annotations

import pathlib
import warnings

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
DPI = 300
OUT = pathlib.Path("docs/srs_project/paper/figures/fig0_research_framework")

C_TASK = "#E8EAF0"
C_L0 = "#DCE9F7"
C_L1 = "#D7E3F0"
C_L2 = "#DFF0E2"
C_L3 = "#E8F5E9"
C_EGT = "#FDEBD3"
C_LAW = "#FFF9C4"
C_EVAL = "#ECEFF1"
C_OUT = "#F3E5F5"
C_FUSION = "#E1F5FE"
C_LINE = "#455A64"
C_HEAD = "#263238"


def rbox(ax, x, y, w, h, color, lw=1.4, dashed=False):
    style = "--" if dashed else "-"
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6", facecolor=color,
        edgecolor=C_LINE, linewidth=lw, linestyle=style))


def text(ax, x, y, s, size=9.3, bold=False, ha="center", va="center",
         linespacing=1.42):
    ax.text(x, y, s, ha=ha, va=va, fontsize=size, color=C_HEAD,
            fontweight="bold" if bold else "normal", linespacing=linespacing)


def arrow(ax, x1, y1, x2, y2, label="", lw=1.8, offset=(0, 0), fontsize=8.8):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=15,
        color=C_LINE, linewidth=lw))
    if label:
        ax.text((x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1],
                label, ha="center", va="center", fontsize=fontsize,
                color=C_LINE)


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        fig, ax = plt.subplots(figsize=(17, 14))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 112)
        ax.axis("off")

        # ============ Title ============
        text(ax, 50, 109, "CascadeVerify: 面向40项不一致性体系的级联式一致性校验算法框架",
             size=14, bold=True)

        # ============ Input ============
        rbox(ax, 25, 98, 50, 8, C_TASK, lw=1.6)
        text(ax, 50, 103.5, "输入: (Question, Answer, 冻结证据E)", size=12, bold=True)
        text(ax, 50, 100, "E = {evidence_id, text, source_type, scope_id, completeness(open), source_ref}",
             size=8.5)

        arrow(ax, 50, 98, 50, 94)

        # ============ Claim Decomposition ============
        rbox(ax, 15, 86, 70, 7, C_TASK, lw=1.4)
        text(ax, 50, 92, "Answer → 原子Claim分解", size=11, bold=True)
        text(ax, 50, 89,
             "numeric(算子+数值+单位) | quoted(引号) | enum(顿号列表) | identifier(PZXQ-ID) | semantic(兜底)",
             size=8.5)

        arrow(ax, 50, 86, 50, 82)

        # ============ L0 NER Entity Layer ============
        rbox(ax, 3, 72, 94, 9, C_L0, lw=1.8)
        text(ax, 50, 79, "L0  NER实体层  ——  检测: 术语类 (TERM-01/02/05/07/08)", size=12, bold=True)
        text(ax, 50, 74.5,
             "词典gazetteer + 运行时文档词典归纳(能力名/用例名/接口ID/值域/别名对) + 实体链接(exact/别名/前缀/NIL)",
             size=8.5)
        # Side: results
        text(ax, 50, 76, "已决claim → 直通融合", size=8)

        # ============ Residual arrow ============
        arrow(ax, 50, 72, 50, 68,
               "残差claims (C1原则: 已决claim不下沉)", lw=2, offset=(12, 0), fontsize=9.5)

        # ============ L1 Symbolic Rule Layer ============
        rbox(ax, 3, 42, 94, 25, C_L1, lw=2.2)
        text(ax, 50, 64.5,
             "L1  符号规则层  ——  检测: 参数+逻辑+合规类 + 术语结构切片",
             size=12.5, bold=True)
        text(ax, 50, 61,
             "机制: 证据线性化 → (主体, 值, 位置)注册表 → answer声明与注册表跨位置join → 矛盾信号显式浮现",
             size=8.8)

        # L1 experts grid (3x3)
        experts = [
            ("ID注册表\n(TERM-07)", "同ID双登记\n父子绑定/段序"),
            ("枚举值域\n(TERM-03)", "闭集比对\n错字(编辑距离1)"),
            ("E1模板\n(LOGIC-02)", "异常处置比对\n主题错位检测"),
            ("序列对齐\n(LOGIC-03)", "步骤配对+单调性\nJaccard+BGE"),
            ("Z3数值约束\n(PARAM-01~07)", "区间/量纲/聚合\nSMT-LIB+unsat core"),
            ("GJB规则引擎\n(GJB-01~11)", "120条规则编译\n55条可自动执行"),
            ("追踪join\n(GJB-05)", "正逆双向比对\n锚点有效性"),
            ("覆盖join\n(GJB-01/04/06)", "合格性逐章覆盖\n报警要素比对"),
            ("实体护栏\n(TERM-01/02/08)", "同义异名/同名异义\n缩写与代号"),
        ]
        for i, (title, desc) in enumerate(experts):
            row, col = divmod(i, 3)
            ex = 5 + col * 31
            ey = 58.5 - row * 6.5
            ax.add_patch(FancyBboxPatch(
                (ex, ey), 28, 5.5, boxstyle="round,pad=0.3",
                facecolor="#FAFCFF", edgecolor=C_LINE, linewidth=0.8))
            text(ax, ex + 14, ey + 3.8, title, size=8.2, bold=True)
            text(ax, ex + 14, ey + 1.5, desc, size=7.2)

        text(ax, 50, 44,
             "性质: 纯确定性(零模型调用) | refute精确率0.83 | 单元格级定位 | 17真实违例检出16/17",
             size=8.8)

        # Residual arrow to L2
        arrow(ax, 50, 42, 50, 38,
               "语义残差 (规则不可形式化的answer-vs-证据比对)", lw=2, offset=(10, 0), fontsize=9.5)

        # ============ L2 NLI Semantic Layer ============
        rbox(ax, 3, 27, 45, 10, C_L2, lw=1.8)
        text(ax, 25, 34.5, "L2  NLI语义层", size=12, bold=True)
        text(ax, 25, 31,
             "mDeBERTa + EGT三态合成训练\n"
             "gate=0.7 (dev扫参60配置最优)\n"
             "refute召回0.875 / 精确率0.37",
             size=8.5, linespacing=1.5)

        # EGT box
        rbox(ax, 52, 27, 45, 10, C_EGT, lw=1.4)
        text(ax, 74, 34.5, "EGT三态构造性合成", size=10.5, bold=True)
        text(ax, 74, 30.5,
             "S ← 已验证种子+改写\n"
             "R ← 跨行污染(sound)\n"
             "N ← 支撑span删除(sound)",
             size=8.2, linespacing=1.4)
        arrow(ax, 52, 32, 48, 32, "训练", lw=2, offset=(0, 1.5), fontsize=8.5)

        # Cascade escalation
        arrow(ax, 25, 27, 25, 23,
               "refute候选 → 实例级升级", lw=2.5, offset=(-8, 0), fontsize=10)

        # L3 box
        rbox(ax, 3, 15, 30, 7, C_L3, lw=1.6)
        text(ax, 18, 21, "L3  LLM仲裁 (工程旁路)", size=10.5, bold=True)
        text(ax, 18, 17.5,
             "glm-5.3(缓存) | gate=0.6\n"
             "15次调用=18% L3成本",
             size=8.2)

        # S/N direct path
        arrow(ax, 25, 27, 68, 13, "S/N直通", lw=1.5, offset=(4, -2), fontsize=9)

        # ============ Fusion ============
        rbox(ax, 40, 11, 57, 6, C_FUSION, lw=1.6)
        text(ax, 68, 16,
             "per-claim融合 + 实例聚合",
             size=11, bold=True)
        text(ax, 68, 12.5,
             "同claim: refute>support>NIE (弱通道NIE不否决强通道)\n"
             "实例: 任一refute→R | 全support→S | 否则NIE (开放世界)",
             size=8.2, linespacing=1.4)

        arrow(ax, 18, 15, 40, 14)
        arrow(ax, 68, 11, 68, 7)

        # ============ Output ============
        rbox(ax, 40, 1, 57, 5, C_OUT, lw=1.5)
        text(ax, 68, 5.5,
             "输出: verdict + 证据定位(块/行/span) + 检测项ID + justification",
             size=10, bold=True)

        # ============ Key Laws (right margin) ============
        rbox(ax, 70, 42, 28, 10, C_LAW, lw=1.2)
        text(ax, 84, 50, "双登记定律", size=9.5, bold=True)
        text(ax, 84, 45,
             "证据侧双登记冲突\n→join可裁决(1.0)\n"
             "answer侧单边破坏\n→0.05-0.53\n"
             "(394注入对照)\n"
             "符号层管证据内部\n语义层管answer比对",
             size=7.2, linespacing=1.3)

        # ============ Calibration note ============
        rbox(ax, 70, 27, 28, 8, C_LAW, lw=1.2)
        text(ax, 84, 33.5, "启发式标定", size=9.5, bold=True)
        text(ax, 84, 30,
             "nli_gate=0.7\ndeV扫参60配置\n"
             "llm_refute_gate=0.6\n同扫参最优\n"
             "旧enum通道已降级\n(seq阈值未扫参\n附录声明)",
             size=7.2, linespacing=1.3)

        # ============ Evaluation (bottom) ============
        rbox(ax, 3, 1, 34, 7, C_EVAL, lw=1.2, dashed=True)
        text(ax, 20, 6.5, "评测体系(底座)", size=9.5, bold=True)
        text(ax, 20, 3,
             "91QA(silver)+17违例(94.1%)\n"
             "+06号sound(跨文档gap)\n"
             "+394变异注入(双登记验证)\n"
             "+B0-B5六基线+六科学对照",
             size=7.5, linespacing=1.3)

        fig.suptitle(
            "CascadeVerify算法框架 v4 (审计修复后): "
            "三层级联 + per-claim融合 + 40项不一致性类型驱动",
            fontsize=12, y=0.985, color=C_HEAD)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUT.with_suffix(".png"), dpi=DPI, bbox_inches="tight",
                    facecolor="white")
        fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        print(f"saved: {OUT}.png / {OUT}.pdf")


if __name__ == "__main__":
    main()
