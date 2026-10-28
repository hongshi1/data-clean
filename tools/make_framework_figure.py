"""框架总图(重构版): 以40项不一致性体系为主干, 各层按检测类型分工."""
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
C_L3 = "#E8F5E9"
C_EGT = "#FDEBD3"
C_LAW = "#FFF9C4"
C_EVAL = "#ECEFF1"
C_OUT = "#F3E5F5"
C_TASK = "#E8EAF0"
C_LINE = "#455A64"
C_HEAD = "#263238"


def box(ax, x, y, w, h, color, title, lines, title_size=11.5,
        line_size=9.3, lw=1.4):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6",
        facecolor=color, edgecolor=C_LINE, linewidth=lw))
    body = "\n".join(lines)
    if title:
        ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=C_HEAD)
        ax.text(x + w / 2, y + (h - 4.8) / 2, body, ha="center",
                va="center", fontsize=line_size, linespacing=1.42,
                color=C_HEAD)
    else:
        ax.text(x + w / 2, y + h / 2, body, ha="center", va="center",
                fontsize=line_size, linespacing=1.42, color=C_HEAD)


def arrow(ax, x1, y1, x2, y2, label="", lw=1.8, offset=(0, 0), fontsize=9,
          ha="center", style="-|>"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
        color=C_LINE, linewidth=lw))
    if label:
        ax.text((x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1],
                label, ha=ha, va="center", fontsize=fontsize, color=C_LINE)


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        fig, ax = plt.subplots(figsize=(17, 12.5))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        # ---------- Band 1: 检测对象 ----------
        box(ax, 12, 90, 76, 8, C_OBJ, "检测对象: 40项不一致性体系 + 三态判定语义",
            ["术语类 TERM x8 | 参数类 PARAM x10 | 逻辑类 LOGIC x11 | 合规类 GJB x11",
             "每个claim判定: support(证据支持) / refute(证据反对) / NIE(开放世界不可判定) + 证据定位"])

        # 四类色块（检测对象的具体化）
        types = [
            ("术语类\nTERM-01~08", 14, "#BBDEFB"),
            ("参数类\nPARAM-01~10", 34, "#C8E6C9"),
            ("逻辑类\nLOGIC-01~11", 54, "#FFE0B2"),
            ("合规类\nGJB-01~11", 74, "#F8BBD0"),
        ]
        for label, x, color in types:
            ax.add_patch(FancyBboxPatch(
                (x, 83.2), 12, 4.6, boxstyle="round,pad=0.4",
                facecolor=color, edgecolor=C_LINE, linewidth=1.1))
            ax.text(x + 6, 85.5, label, ha="center", va="center",
                    fontsize=9.5, color=C_HEAD, linespacing=1.3)

        arrow(ax, 30, 83.2, 30, 79.5)
        arrow(ax, 46, 83.2, 46, 79.5, style="-|>")
        arrow(ax, 62, 83.2, 62, 76.5)
        arrow(ax, 78, 83.2, 78, 76.5)

        # ---------- L0 ----------
        box(ax, 3, 66, 36, 13, C_L0, "第1层  L0 NER实体层",
            ["实体抽取(域术语/中文实体/引号术语) -> 文档词典(能力/用例/接口/值域)",
             "实体链接(exact/别名/前缀/NIL) + 定义比对",
             "检测: 同义异名(TERM-01) 同名异义(02) 用例名(05) 缩写(08) 接口ID(07)"])

        # L0 -> L1 残差
        arrow(ax, 21, 66, 21, 61, "术语残差+非术语claims", lw=1.8, offset=(11, 0),
              fontsize=9, ha="left")

        # ---------- L1 (大盒子, 四个类型子块) ----------
        ax.add_patch(FancyBboxPatch(
            (3, 38), 70, 22, boxstyle="round,pad=0.6",
            facecolor=C_L1, edgecolor=C_LINE, linewidth=1.8))
        ax.text(38, 57.2, "第2层  L1 符号规则层 = (主体, 值, 位置)注册表 + 跨位置join",
                ha="center", va="center", fontsize=11.5, fontweight="bold",
                color=C_HEAD)
        ax.text(38, 54.8, "机制: 证据线性化成注册表, answer声明与注册表join裁决 -> 矛盾信号显式浮现 | 免费, refute精确率0.83, 单元格级定位",
                ha="center", va="center", fontsize=8.8, color=C_HEAD)

        sub = [
            ("Z3数值约束专家", "PARAM-01/03/05/06/07\n区间/量纲/聚合约束\nSMT-LIB+unsat core", 4.5),
            ("E1模板+序列对齐专家", "LOGIC-02/03\n异常处置/事件时序\n主题错位/处置矛盾", 22),
            ("ID/枚举join专家", "TERM-03/07\n双登记/值域/错字\n编辑距离=1", 39.5),
            ("追踪/覆盖/封闭清单", "GJB-01~11\n双向追踪/逐章覆盖\n条款有无", 57),
        ]
        for title, body, x in sub:
            ax.add_patch(FancyBboxPatch(
                (x, 39.5), 15.5, 12.5, boxstyle="round,pad=0.4",
                facecolor="#FAFCFF", edgecolor=C_LINE, linewidth=1.1))
            ax.text(x + 7.75, 50.3, title, ha="center", va="center",
                    fontsize=9.3, fontweight="bold", color=C_HEAD)
            ax.text(x + 7.75, 44.6, body, ha="center", va="center",
                    fontsize=8.3, color=C_HEAD, linespacing=1.35)

        # law 1
        box(ax, 76, 40, 21, 20, C_LAW, "定律① 双登记",
            ["证据侧双登记冲突\njoin可裁决 -> 1.0",
             "answer侧单边破坏\n-> 0.05-0.53",
             "(394注入对照)",
             "符号层专责证据\n内部冲突; 语义层\n专责answer-vs-证据",
             "=> 上下文聚合\n是一致性校验\n的先决条件"], line_size=8.4)

        # L1 decided -> fusion
        arrow(ax, 55, 38, 62, 16, "已决claims (C1原则: 不下沉语义层)", lw=1.9,
              offset=(12, 4), fontsize=9.2, ha="left")

        # L1 -> L2 residual
        arrow(ax, 20, 38, 20, 32.5, "规则不可判定的语义残差", lw=1.9,
              offset=(13, 0), fontsize=9.2, ha="left")

        # ---------- L2 ----------
        box(ax, 3, 19.5, 33, 12.5, C_L2, "第3层  L2 NLI语义层",
            ["覆盖: 其余语义型不一致(规则覆盖不到的",
             "answer-vs-证据语义比对)",
             "mDeBERTa域适配; refute召回0.875 精确0.37"])

        # EGT training box
        box(ax, 3, 4.5, 33, 12.5, C_EGT, "EGT三态合成 (L2的训练数据来源)",
            ["S<-已验证种子改写 | R<-跨行污染(sound)", "N<-支撑删除(sound) | 前人范式全二元",
             "4500样本叙事文法"], line_size=8.8)

        arrow(ax, 19.5, 17, 19.5, 19.5, "训练", lw=2, offset=(5, 0), fontsize=9.5)

        # law 2 (grammar) attached to EGT/L2
        box(ax, 38, 4.5, 22, 12.5, C_LAW, "定律② 文法定律",
            ["v1近拷贝: dev 0.965\n真实迁移仅0.50(负)",
             "v2叙事文法:\nrefute召回 0.375->0.875",
             "=> 合成claim形态分布\n与标签sound性同等重要"], line_size=8.4)

        # L2 -> L3 escalation
        arrow(ax, 36, 25.8, 62, 25.8, "refute候选 -> 实例级升级(M3路由)", lw=1.9,
              offset=(0, 2.2), fontsize=9.2)
        arrow(ax, 36, 22.5, 62, 19, "S/N直通融合", lw=1.5, offset=(0, -2), fontsize=9)

        box(ax, 62, 19.5, 19, 12.5, C_L3, "L3 LLM复核",
            ["glm-5.3(缓存)",
             "精确率~1.0, 15次调用",
             "=L3全额的18%成本"], line_size=8.8)

        # law 3 (routing)
        box(ax, 76, 4.5, 21, 12.5, C_LAW, "定律③ 路由空间",
            ["oracle路由 0.787@2次调用\n(空间真实存在)",
             "EGT监督学习路由\n一致率仅0.0875(负)",
             "=> 需域内路由监督\n(三重漂移归因)"], line_size=8.4)

        # ---------- fusion + output ----------
        box(ax, 42, 4.5, 30, 12.5, C_OUT, "per-claim融合 + 聚合",
            ["同claim: refute>support>NIE\n(弱通道NIE不否决强通道, 消融-0.152)",
             "实例: 任一refute->R; 全S->S;\n否则NIE(开放世界)"], line_size=8.8)

        box(ax, 83, 4.5, 14, 12.5, C_TASK, "输出",
            ["三态verdict",
             "+证据定位",
             "+检测项ID",
             "+justification"], line_size=8.8)
        arrow(ax, 81, 10.7, 83, 10.7, "", lw=1.8)

        # L3 -> fusion
        arrow(ax, 81, 19.5, 72, 17, "复核结果替换L2判定", lw=1.6, offset=(6, 2.5),
              fontsize=8.6)

        fig.suptitle(
            "CascadeVerify: 面向40项不一致性体系的分层级联检测 — L0实体层(术语类) / L1符号规则层(参数+逻辑+合规类) / L2 NLI语义层(其余语义型)",
            fontsize=12.5, y=0.982, color=C_HEAD)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUT.with_suffix(".png"), dpi=DPI, bbox_inches="tight",
                    facecolor="white")
        fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        print(f"saved: {OUT}.png / {OUT}.pdf")


if __name__ == "__main__":
    main()
