"""框架总图v3: 核心算法=三层检测体系(类型驱动), L3移除, 评测作底座."""
from __future__ import annotations

import pathlib
import warnings

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
DPI = 300
OUT = pathlib.Path("docs/srs_project/paper/figures/fig0_research_framework")

C_OBJ = "#E8EAF0"
C_L0 = "#DCE9F7"
C_L1 = "#D7E3F0"
C_L2 = "#DFF0E2"
C_EGT = "#FDEBD3"
C_LAW = "#FFF9C4"
C_EVAL = "#ECEFF1"
C_OUT = "#F3E5F5"
C_LINE = "#455A64"
C_HEAD = "#263238"
C_SUB = "#FAFCFF"


def rbox(ax, x, y, w, h, color, lw=1.4, dashed=False):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6", facecolor=color,
        edgecolor=C_LINE, linewidth=lw,
        linestyle="--" if dashed else "-"))


def text(ax, x, y, s, size=9.3, bold=False, ha="center", va="center",
         linespacing=1.42):
    ax.text(x, y, s, ha=ha, va=va, fontsize=size, color=C_HEAD,
            fontweight="bold" if bold else "normal", linespacing=linespacing)


def arrow(ax, x1, y1, x2, y2, label="", lw=1.8, offset=(0, 0), fontsize=8.8,
          ha="center"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=15,
        color=C_LINE, linewidth=lw))
    if label:
        ax.text((x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1],
                label, ha=ha, va="center", fontsize=fontsize, color=C_LINE)


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        fig, ax = plt.subplots(figsize=(16, 15))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 112)
        ax.axis("off")

        # ============ 核心算法外框 ============
        rbox(ax, 2, 12, 96, 98, "#FFFFFF", lw=2.6)
        text(ax, 50, 107, "CascadeVerify 核心算法: 面向40项不一致性体系的三层检测",
             size=13.5, bold=True)

        # ---------- 检测对象 ----------
        rbox(ax, 6, 96, 88, 8, C_OBJ)
        text(ax, 50, 102.5, "检测对象: 40项不一致性体系 (taxonomy v3)",
             size=11, bold=True)
        text(ax, 50, 98.5,
             "每个原子claim -> 三态判定 support(证据支持) | refute(证据反对) | "
             "NIE(开放世界不可判定) + 证据定位(块/行/span) + 检测项ID", size=8.8)

        types = [
            ("术语类 TERM\n01~08 共8项", 8, "#BBDEFB"),
            ("参数类 PARAM\n01~10 共10项", 30.5, "#C8E6C9"),
            ("逻辑类 LOGIC\n01~11 共11项", 53, "#FFE0B2"),
            ("合规类 GJB\n01~11 共11项", 75.5, "#F8BBD0"),
        ]
        for label, x, color in types:
            rbox(ax, x, 88, 16.5, 6.5, color, lw=1.1)
            text(ax, x + 8.25, 91.3, label, size=8.8, linespacing=1.3)

        for x in (16, 37, 57, 76):
            arrow(ax, x, 88, x, 84.5)
        text(ax, 50, 86.3, "answer分解为原子claim -> 按检测项特征路由到各层",
             size=8.6)

        # ---------- L0 ----------
        rbox(ax, 6, 68, 66, 13, C_L0, lw=1.6)
        text(ax, 39, 78.5, "第1层  L0 NER实体层  ——  检测: 术语类 (5/8项)",
             size=11, bold=True)
        text(ax, 39, 74.8,
             "机制: 实体抽取(域术语/中文实体/引号术语) -> 文档词典(能力/用例/接口/值域/别名对)\n"
             "-> 实体链接(exact/别名/前缀/NIL) -> 冲突检测", size=8.6)
        text(ax, 39, 70.5,
             "覆盖: TERM-01同义异名 | 02同名异义 | 05用例名错配 | 07接口ID冲突 | 08缩写不一致",
             size=8.6)

        rbox(ax, 74, 68, 20, 13, C_L0, lw=1.1)
        text(ax, 84, 78.5, "L0覆盖范围", size=9, bold=True)
        text(ax, 84, 73, "术语类5项\n(全部为实体级比对:\n名称/ID/缩写/定义)",
             size=8.2, linespacing=1.35)

        arrow(ax, 39, 68, 39, 63.5,
              "术语残差 + 非术语claims", lw=1.8, offset=(12, 0), ha="left")

        # ---------- L1 ----------
        rbox(ax, 6, 38, 66, 24, C_L1, lw=1.8)
        text(ax, 39, 59.5,
             "第2层  L1 符号规则层  ——  检测: 参数+逻辑+合规类 (+术语结构切片)",
             size=11, bold=True)
        text(ax, 39, 56.8,
             "机制: 证据线性化为 (主体, 值, 位置) 注册表 -> answer声明与注册表跨位置join -> "
             "矛盾信号显式浮现", size=8.5)

        sub = [
            ("Z3数值约束", "PARAM-01/03/05/\n06/07\n区间包含/量纲换算\n数值聚合约束\nSMT-LIB+unsat core", 7),
            ("E1模板+序列对齐", "LOGIC-02/03\n异常处置一致性\n事件时序(重排定位)\n主题错位检测", 23.5),
            ("ID join+枚举join", "TERM-03/07\nID双登记冲突\n值域比对/错字\n(编辑距离=1)", 40),
            ("追踪/覆盖/封闭清单", "GJB-01~11\n双向追踪join\n逐章覆盖比对\n条款有无检查", 56.5),
        ]
        for title, body, x in sub:
            rbox(ax, x, 39, 15, 15, C_SUB, lw=1.1)
            text(ax, x + 7.5, 51.3, title, size=8.5, bold=True)
            text(ax, x + 7.5, 45.5, body, size=7.8, linespacing=1.32)
        text(ax, 39, 37.2,
             "性质: 纯确定性(零模型调用) | refute精确率0.83 | 单元格级定位 | 17真实违例检出16/17",
             size=8.3)

        # law 1
        rbox(ax, 74, 38, 20, 24, C_LAW, lw=1.2)
        text(ax, 84, 59.5, "定律① 双登记", size=9.5, bold=True)
        text(ax, 84, 53.5,
             "证据侧双登记冲突\n-> join可裁决(1.0)\nanswer侧单边破坏\n-> 0.05~0.53\n(394注入对照)\n\n"
             "L1专责证据内部\n跨位置冲突\nanswer-vs-证据归L2\n=> 上下文聚合\n是一致性校验的\n先决条件",
             size=7.5, linespacing=1.3)

        arrow(ax, 39, 38, 39, 33.5,
              "仅语义残差进入L3层 (C1残差原则: 上层已决claims直通融合, 不下沉)",
              lw=1.8, offset=(13, 0), ha="left")

        # ---------- L2 row ----------
        rbox(ax, 6, 21, 36, 11.5, C_L2, lw=1.6)
        text(ax, 24, 30.7, "第3层  L2 NLI语义层  ——  检测: 其余语义型",
             size=10.5, bold=True)
        text(ax, 24, 25.5,
             "覆盖: 规则不可形式化的answer-vs-证据语义比对\n"
             "(措辞错配/跨行值断言/效果性声明)\n"
             "机制: mDeBERTa域适配(premise=聚焦证据,\nhypothesis=claim, 概率门控)",
             size=8.1, linespacing=1.32)

        rbox(ax, 46, 21, 26, 11.5, C_EGT, lw=1.4)
        text(ax, 59, 30.7, "EGT三态合成 (L2的训练数据来源)", size=9.2, bold=True)
        text(ax, 59, 25.3,
             "S<-已验证种子改写 | R<-跨行污染\n(sound) | N<-支撑span删除(sound)\n"
             "4500样本叙事文法\n前人合成范式全二元->三态是空白",
             size=7.9, linespacing=1.32)
        arrow(ax, 44, 26.7, 46, 26.7, "训练", lw=2, offset=(0, 1.7),
              fontsize=8.5)

        # law 2
        rbox(ax, 74, 21, 20, 11.5, C_LAW, lw=1.2)
        text(ax, 84, 30.7, "定律② 文法定律", size=9.5, bold=True)
        text(ax, 84, 25.3,
             "v1近拷贝: dev 0.965\n真实迁移仅0.50(负)\nv2叙事: refute召回\n0.375->0.875\n"
             "=> 合成claim形态分布\n与标签sound性同等重要",
             size=7.5, linespacing=1.3)

        # ---------- fusion + output ----------
        arrow(ax, 24, 21, 24, 17.5, "", lw=1.8)
        rbox(ax, 6, 12.5, 66, 5, C_OUT, lw=1.5)
        text(ax, 39, 15,
             "层间输出融合: 汇聚L0/L1/L2全部通道结果, 同claim取 refute>support>NIE "
             "(弱通道NIE不否决强通道, 消融-0.152)\n"
             "实例聚合: 任一refute->R | 全support->S | 否则NIE (开放世界)",
             size=8.4, linespacing=1.4)

        rbox(ax, 74, 12.5, 20, 5, C_OUT, lw=1.5)
        text(ax, 84, 15, "输出: 三态verdict\n+证据定位+检测项ID+justification",
             size=8.2, linespacing=1.35)
        arrow(ax, 72, 15, 74, 15, "", lw=1.8)

        # ============ 评测底座(虚线, 框外) ============
        rbox(ax, 2, 2.5, 96, 6.5, C_EVAL, lw=1.2, dashed=True)
        text(ax, 50, 6.8, "评测体系(底座, 非算法组件)", size=9.5, bold=True)
        text(ax, 50, 4.2,
             "91QA(silver) + 17真实违例(检出16/17) + 06号sound跨文档集 + 394变异注入 | "
             "B0-B5六基线 + 六科学对照 | 29簇held-out切分(乐观偏差2%量化) | 负结果集六条如实报告",
             size=8)

        fig.suptitle(
            "CascadeVerify框架: 不一致性类型驱动的三层检测算法 "
            "(L0术语类 / L1参数+逻辑+合规类 / L2其余语义型) + EGT训练数据合成",
            fontsize=12.5, y=0.987, color=C_HEAD)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUT.with_suffix(".png"), dpi=DPI, bbox_inches="tight",
                    facecolor="white")
        fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        print(f"saved: {OUT}.png / {OUT}.pdf")


if __name__ == "__main__":
    main()
