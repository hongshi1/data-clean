"""研究框架总图: 三个方法模块 + 三条定律 + 评测体系 (论文图0)."""
from __future__ import annotations

import pathlib
import warnings

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
DPI = 300
OUT = pathlib.Path("docs/srs_project/paper/figures/fig0_research_framework")

# palette (academic blue-gray)
C_TASK = "#E8EAF0"
C_M2 = "#DCE9F7"
C_M1 = "#FDEBD3"
C_SEM = "#DFF0E2"
C_LAW = "#FFF9C4"
C_EVAL = "#ECEFF1"
C_LINE = "#455A64"
C_HEAD = "#263238"


def box(ax, x, y, w, h, color, title, lines, title_size=11.5,
        line_size=9.5, lw=1.4):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6",
        facecolor=color, edgecolor=C_LINE, linewidth=lw)
    ax.add_patch(patch)
    body = "\n".join(lines)
    if title:
        ax.text(x + w / 2, y + h - 3.2, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=C_HEAD)
        ax.text(x + w / 2, y + (h - 5.6) / 2, body, ha="center",
                va="center", fontsize=line_size, linespacing=1.45,
                color=C_HEAD)
    else:
        ax.text(x + w / 2, y + h / 2, body, ha="center", va="center",
                fontsize=line_size, linespacing=1.45, color=C_HEAD)
    return (x, y, w, h)


def arrow(ax, x1, y1, x2, y2, label="", color=C_LINE, lw=1.8,
          style="-|>", offset=(0, 0), fontsize=9, ha="center"):
    patch = FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
        color=color, linewidth=lw)
    ax.add_patch(patch)
    if label:
        ax.text((x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1],
                label, ha=ha, va="center", fontsize=fontsize, color=C_LINE)


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        fig, ax = plt.subplots(figsize=(16.5, 11.5))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        # ---------- Band 1: task ----------
        box(ax, 20, 90, 60, 8.5, C_TASK, "任务: GJB军事SRS答案一致性校验",
            ["输入 (Question, Answer, 冻结证据E) -> 输出 {support, refute, NIE} + 证据定位",
             "挑战: 开放世界三态 | 目标域零标注 | 矛盾跨位置分布(表格/正文/追踪)"])

        arrow(ax, 50, 90, 50, 85.5)

        # ---------- Band 2: M2 symbolic layer ----------
        box(ax, 3, 68, 52, 17, C_M2, "M2  符号验证层 = 注册表 + 跨位置join",
            ["证据线性化 -> (主体, 值, 位置) 注册表 -> answer声明与注册表join裁决",
             "九种实例化: ID注册表(双登记) | 值域注册表(枚举/错字) | E1模板 | 追踪双向join | Z3数值(unsat core) | 覆盖",
             "已决claim: 免费, refute精确率0.83, 自带单元格级定位  |  17真实违例检出16/17"])

        # law 1 callout
        box(ax, 59, 69.5, 38, 14, C_LAW, "定律① 双登记定律",
            ["证据侧双登记冲突 -> 检出率 1.0 (join可裁决)",
             "answer侧单边破坏 -> 检出率 0.05-0.53 (394注入对照)",
             "符号层专责证据内部冲突; answer-vs-证据归语义层",
             "=> 上下文聚合(方向A)是一致性校验的先决条件"], line_size=9)

        # decided path (right to fusion)
        arrow(ax, 55, 76, 66, 55, "已决claims (C1残差原则: 不下沉)", lw=1.8,
              offset=(4, 4), fontsize=9.5)

        # residual path (down to M1/L2)
        arrow(ax, 29, 68, 29, 61.5, "残差claims (规则不可判定)", lw=1.8,
              offset=(9, 0), fontsize=9.5, ha="left")

        # ---------- Band 3: M1 + L2 ----------
        box(ax, 3, 44, 30, 17, C_M1, "M1  EGT三态构造性合成",
            ["前人合成范式全二元(MiniCheck折叠矛盾)",
             "S <- 已验证种子+改写",
             "R <- 跨行污染(真实值+错误绑定, sound)",
             "N <- 支撑span删除(开放世界, sound)"], line_size=9.5)

        arrow(ax, 33, 52, 44, 52, "训练", lw=2)

        box(ax, 44, 44, 24, 17, C_SEM, "L2 域适配NLI (本地)",
            ["mDeBERTa + EGT 4500样本",
             "refute召回 0.875",
             "精确率 0.37(低)->需升级",
             "零样本0.327 -> 域适配必要"], line_size=9.5)

        # law 2 callout (grammar)
        box(ax, 71, 44, 26, 17, C_LAW, "定律② 文法定律",
            ["v1近拷贝文法: dev 0.965",
             "  但真实迁移 0.50 (负迁移)",
             "v2叙事文法: refute召回",
             "  0.375 -> 0.875",
             "合成数据的claim形态分布",
             "与标签sound性同等重要"], line_size=8.6)

        # ---------- Band 4: M3 routing + L3 ----------
        arrow(ax, 56, 44, 62, 36, "refute候选", lw=1.8, offset=(6, 0),
              fontsize=9.5, ha="left")
        arrow(ax, 56, 47.5, 66, 30.5, "S/N 直通", lw=1.6, offset=(4, -3),
              fontsize=9)

        box(ax, 40, 22, 34, 13, "#D7E3F0", "M3  残差级联路由",
            ["C1残差原则(已决不下沉, 有代价已测量)",
             "refute候选 -> 实例级升级到L3(claim级会漏068/074)",
             "15次调用=18%成本, refute F1 0.800全场最优"], line_size=9.2)

        box(ax, 78, 22, 19, 13, C_SEM, "L3 LLM复核",
            ["glm-5.3(缓存)",
             "精确率~1.0",
             "实例级批量"], line_size=9.2)

        arrow(ax, 74, 28.5, 78, 28.5, "", lw=2)

        # law 3 callout (routing space)
        box(ax, 3, 22, 34, 13, C_LAW, "定律③ 路由空间存在但监督错位",
            ["oracle路由 0.787 @ 2次调用(空间真实存在)",
             "EGT监督学习路由: held-out一致率0.0875(负结果)",
             "归因: 特征外推/通道强度漂移/先验漂移",
             "(RouteLLM 2%域内数据定律的实证)"], line_size=8.6)

        # ---------- Band 5: fusion + output ----------
        box(ax, 40, 6, 38, 12, "#E3F2FD", "per-claim通道融合 + 聚合",
            ["同claim文本: refute > support > NIE (弱通道NIE不否决强通道, 消融-0.152)",
             "实例聚合: 任一refute->refute; 全support->support; 否则NIE (开放世界)"],
            line_size=9.2)

        arrow(ax, 57, 22, 57, 18.5)
        arrow(ax, 88, 22, 78, 14, "复核结果替换L2判定", lw=1.6, offset=(6, 3),
              fontsize=8.8)
        arrow(ax, 20, 22, 40, 12.5, "学习路由负结果记录", lw=1.2, offset=(0, 3),
              fontsize=8.6)

        box(ax, 82, 6, 15, 12, C_TASK, "输出",
            ["verdict",
             "+ 证据定位",
             "+ justification",
             "(rule_id / unsat core)"], line_size=9)
        arrow(ax, 78, 12, 82, 12, "", lw=1.8)

        # ---------- Band 6: evaluation ----------
        box(ax, 3, 0.5, 94, 4.5, C_EVAL, "评测体系(可信度工程)",
            ["91QA(silver)+17真实违例(94.1%)+06号sound跨文档集+394变异注入 | B0-B5六基线+六科学对照(文法/路由/聚合/双登记/dev-on-test/跨文档) | 29簇held-out切分(乐观偏差2%量化) | 负结果集六条如实报告"],
            line_size=9)

        fig.suptitle(
            "CascadeVerify科研框架: 三个方法模块(M1合成/M2符号join/M3残差路由) × 三条实证定律 × 可信评测体系",
            fontsize=13, y=0.985, color=C_HEAD)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUT.with_suffix(".png"), dpi=DPI, bbox_inches="tight",
                    facecolor="white")
        fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        print(f"saved: {OUT}.png / {OUT}.pdf")


if __name__ == "__main__":
    main()
