r"""CascadeVerify论文LaTeX表格生成: booktabs三线表 → docs/srs_project/paper/tables.tex.

9张表(tab:main/ablation/bootstrap/violation/mutation/negative/test_honest/crossdoc/experts),
数字全部经tools/paper_data.py从runs程序化提取(单一事实源, 与图共享);
tab:experts为系统设计描述(非实验数字), 按论文§4.3定稿文案登记.
用法: python tools/make_paper_tables.py [--out docs/srs_project/paper/tables.tex]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as pdata  # noqa: E402

OUT_DEFAULT = pdata.BASE / "docs/srs_project/paper/tables.tex"

RUN_SOURCES = [
    f"{pdata.RUN_PAPER_MATRIX}  (B0-B5基线/消融/bootstrap)",
    f"{pdata.RUN_CASCADE}  (五配置级联+conformal+LLM统计)",
    f"{pdata.RUN_VIOLATION_BASELINE} / {pdata.RUN_VIOLATION_ID_JOIN} /",
    f"    {pdata.RUN_VIOLATION_ENUM_JOIN} / {pdata.RUN_VIOLATION_COVERAGE}  (违例演进四阶段)",
    f"{pdata.RUN_MUTATION}  (变异注入矩阵+真实违例交叉对照)",
    f"{pdata.RUN_CROSSDOC}  (跨文档gap)",
    f"{pdata.RUN_ROUTER} / {pdata.RUN_ROUTER_TRAIN}  (路由α扫描/oracle/held-out一致率)",
    f"{pdata.RUN_TEST_HONEST_PREFIX} / {pdata.RUN_TEST_HONEST_POSTFIX}  (test诚实评测修复前后)",
    f"{pdata.RUN_EGT_NEAR_TRAIN} / {pdata.RUN_EGT_NEAR_EVAL}  (EGT近拷贝文法dev+真实)",
    f"{pdata.RUN_EGT_NARR_TRAIN} + {pdata.RUN_CASCADE}#l2_nli  (EGT叙事文法dev+真实)",
    f"{pdata.RUN_FP16_MIN} / {pdata.RUN_FP16_MAX}  (fp16波动端点)",
]


def fmt(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"


def fmt_signed(x: float, nd: int = 3) -> str:
    return f"$ {x:+.{nd}f} $"


def bold(txt: str) -> str:
    return r"\textbf{" + txt + "}"


def header(caption: str, label: str, section: str, colspec: str, *, small: str = "\\small") -> str:
    return (
        f"% {section}\n"
        "\\begin{table}[t]\n\\centering\n"
        f"{small}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        f"\\begin{{tabular}}{{{colspec}}}\n\\toprule\n"
    )


def footer() -> str:
    return "\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"


# ═══════════════════════════════════════════════════════════════════
# tab:main 主结果
# ═══════════════════════════════════════════════════════════════════

def table_main() -> str:
    pm = pdata.get_paper_matrix()
    cas = pdata.get_cascade_run()
    rows: list[dict[str, Any]] = []

    def add(label: str, cfg: dict[str, Any], llm: int, desc: str) -> None:
        pc = cfg["per_class"]
        rows.append({
            "label": label, "desc": desc, "acc": cfg["accuracy"], "macro": cfg["macro_f1"],
            "s": pc["support"]["f1"], "r": pc["refute"]["f1"], "n": pc["not_in_evidence"]["f1"],
            "rp": pc["refute"]["precision"], "rr": pc["refute"]["recall"], "llm": llm,
        })

    desc_b = {
        "B0": "多数类NIE坍缩基线", "B1": "零样本NLI残差（raw mDeBERTa，无专家）",
        "B2": "LLM直推（每QA一次调用，无级联）", "B3": "确定性通道（专家族，无残差）",
        "B4": "全级联（专家+L3直连，最强L3配置）", "B5": "纯LLM残差（无确定性专家）",
    }
    for name in ("B0", "B1", "B2", "B3", "B4", "B5"):
        b = pm["baselines"][name]
        add(name, b, b["llm_calls"]["invocations"], desc_b[name])
    add("L2 NLI", cas["configs"]["l2_nli"], cas["llm_stats"]["l2_nli"]["invocations"],
        "EGT叙事文法微调残差NLI（单独）")
    add("cascade", cas["configs"]["cascade"], cas["llm_stats"]["cascade"]["invocations"],
        "L2→L3升级路由（本文系统）")
    add("cascade\\_conformal", cas["configs"]["cascade_conformal"],
        cas["llm_stats"]["cascade_conformal"]["invocations"], "conformal高置信档（keep=0.95）")

    best = {k: max(r[k] for r in rows) for k in ("acc", "macro", "s", "r", "n", "rp")}
    out = header(
        "主结果（91条官方QA vs GLM-5.3 silver标签；S/R/N = support/refute/not-in-evidence）。"
        "级联以15次LLM调用（全量L3为83次）取得最优refute F1。数字源："
        "eval\\_paper\\_matrix\\_c409df7f 与 eval\\_cascade\\_1e92cdce。",
        "tab:main", "对应论文章节 §5.2 主结果（论文表1）", "lcccccccc")
    out += "系统 & acc & macro-F1 & S-F1 & R-F1 & N-F1 & R-P & R-R & LLM调用 \\\\\n\\midrule\n"
    for r in rows:
        cells = [
            r["label"], fmt(r["acc"]), fmt(r["macro"]),
            fmt(r["s"]), fmt(r["r"]), fmt(r["n"]), fmt(r["rp"]), fmt(r["rr"]),
            str(r["llm"]),
        ]
        if r["macro"] == best["macro"]:
            cells[2] = bold(cells[2])
        if r["r"] == best["r"]:
            cells[4] = bold(cells[4])
        if r["label"] == "cascade":
            cells[0] = bold(cells[0])
            cells[8] = bold(cells[8])
        out += " & ".join(cells) + " \\\\\n"
        out += f"\\multicolumn{{9}}{{l}}{{\\scriptsize {r['desc']}}} \\\\\n"
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:ablation 消融
# ═══════════════════════════════════════════════════════════════════

def table_ablation() -> str:
    pm = pdata.get_paper_matrix()
    b4 = pm["baselines"]["B4"]
    ab = pm["ablations"]
    order = ["-e1_expert", "-entity_detector", "-sequence_expert", "-trace_expert",
             "-id_join_expert", "-enum_join_expert", "-per_claim_fusion", "-llm_residual",
             "-all_experts"]
    out = header(
        "组件消融（基于B4 = 最强L3配置；Δ为相对B4的macro-F1变化）。"
        "四项实质损失：per-claim融合、L3残差、E1专家、enum\\_join专家。"
        "数字源：eval\\_paper\\_matrix\\_c409df7f。",
        "tab:ablation", "对应论文章节 §5.3 消融（论文表4）", "lcccc")
    out += "消融 & acc & macro-F1 & $\\Delta$ macro-F1 & LLM调用 \\\\\n\\midrule\n"
    out += f"B4（基准） & {fmt(b4['accuracy'])} & {bold(fmt(b4['macro_f1']))} & — & " \
           f"{b4['llm_calls']['invocations']} \\\\\n\\midrule\n"
    for key in order:
        a = ab[key]
        delta = a["macro_f1"] - b4["macro_f1"]
        d_str = fmt_signed(delta)
        if delta < -0.01:
            d_str = bold(d_str)
        out += (f"{key.replace('_', '\\_')} & {fmt(a['accuracy'])} & {fmt(a['macro_f1'])} & "
                f"{d_str} & {a['llm_calls']['invocations']} \\\\\n")
    deq_on = ab["deq_on_off"]["on"]
    delta = deq_on["macro_f1"] - b4["macro_f1"]
    out += (f"DEQ\\ on & {fmt(deq_on['accuracy'])} & {fmt(deq_on['macro_f1'])} & "
            f"{fmt_signed(delta)} & {deq_on['llm_calls']['invocations']} \\\\\n")
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:bootstrap 显著性
# ═══════════════════════════════════════════════════════════════════

def table_bootstrap() -> str:
    pm = pdata.get_paper_matrix()
    out = header(
        "配对bootstrap显著性（macro-F1，1000次重采样，seed=42，双侧p）。"
        "n=91且refute仅8条正类，检验功效不足——四对比较在p<0.05下均不显著，"
        "表述使用consistent improvement。数字源：eval\\_paper\\_matrix\\_c409df7f。",
        "tab:bootstrap", "对应论文章节 §5.2 统计显著性（论文表3）", "lcccc")
    out += "对比 & $\\Delta$ macro-F1 & 95\\% CI & $p$ & 重采样 \\\\\n\\midrule\n"
    for key, b in pm["bootstrap"].items():
        lo, hi = b["ci95"]
        out += (f"{key.replace('_', '\\_')} & {fmt_signed(b['delta'], 4)} & "
                f"$[{fmt(lo, 4)}, {fmt(hi, 4)}]$ & {b['p']:.3f} & {b['n_boot']} \\\\\n")
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:violation 违例演进
# ═══════════════════════════════════════════════════════════════════

def table_violation() -> str:
    stages = pdata.get_violation_evolution()
    out = header(
        "17条真实违例的检出演进（deterministic配置；评测驱动的专家补全闭环）。"
        "每阶段一个run；终态16/17，唯一未检出为VIO-15（document\\_name）。"
        "数字源：eval\\_violations\\_5d5c92a8\\_系列（见文件头）。",
        "tab:violation", "对应论文章节 §5.4 真实违例检测（论文表5）",
        "lccccc p{3.1cm}", small="\\footnotesize")
    out += "阶段 & 检出 & 检出率 & identifier & enumeration & traceability & 未检出 \\\\\n\\midrule\n"
    for s in stages:
        und = ", ".join(i.replace("DOC04-VIO-", "") for i in s["undetected"]) or "—"
        rate = bold(fmt(s["rate"], 4)) if s is stages[-1] else fmt(s["rate"], 4)
        out += (f"{s['stage']} & {s['detected']}/{s['n']} & {rate} & "
                f"{s['identifier'][0]}/{s['identifier'][1]} & "
                f"{s['enumeration'][0]}/{s['enumeration'][1]} & "
                f"{s['traceability'][0]}/{s['traceability'][1]} & {und} \\\\\n")
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:mutation 变异注入矩阵
# ═══════════════════════════════════════════════════════════════════

def table_mutation() -> str:
    fam = pdata.get_mutation_run()["family_matrix"]
    order = ["GJB", "TERM", "BASE", "STRUCT", "LOGIC", "PARAM", "OVERALL"]
    out = header(
        "变异注入漏检率矩阵（纯确定性符号层，9专家，0次LLM调用；注入破坏answer对冻结证据的"
        "grounding，期望verdict=refute）。总检出率10.4\\%与真实违例94.1\\%的对照构成"
        "证据侧双登记发现。数字源：eval\\_mutation\\_detection\\_750b7b7d。",
        "tab:mutation", "对应论文章节 §5.5 稳健性（论文表7）", "lcccp{3.6cm}")
    out += "族 & 注入 & 检出 & 检出率 & 主检出通道 \\\\\n\\midrule\n"
    for key in order:
        f = fam[key]
        label = bold("总计") if key == "OVERALL" else key
        chan = f.get("main_detection_channel") or "—"
        if key == "OVERALL":
            chan = "—"
        if key == "PARAM":
            chan = "—（91QA冻结证据无数值事实）"
        rate = f"{f['detection_rate'] * 100:.1f}\\%"
        if key == "OVERALL":
            rate = bold(rate)
        out += f"{label} & {f['n_injected']} & {f['n_detected']} & {rate} & {chan} \\\\\n"
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:negative 负结果集
# ═══════════════════════════════════════════════════════════════════

def table_negative() -> str:
    pm = pdata.get_paper_matrix()
    cas = pdata.get_cascade_run()
    b1 = pm["baselines"]["B1"]
    l2 = cas["configs"]["l2_nli"]
    b3 = cas["configs"]["baseline"]
    n_pred, n_false = pdata.get_l2_false_refute()
    conf_tier = pdata.get_conformal_two_tier()
    kept = conf_tier["kept_tier_ge_keep_confidence"]
    fp_lo, fp_hi = pdata.get_fp16_range()
    held = pdata.get_router_heldout()
    oracle = pdata.get_router_run()["oracle_router_ceiling"]
    egt = pdata.get_egt_grammar()
    n_agree = round(held["routing_agreement"] * held["n"])

    rows = [
        ("零样本NLI坍缩",
         f"B1 macro-F1 {fmt(b1['macro_f1'])}，refute F1 {fmt(b1['per_class']['refute']['f1'])}",
         "域适配必要性的直接证据"),
        ("L2单独不成系统",
         f"{fmt(l2['macro_f1'])} < 确定性基线 {fmt(b3['macro_f1'])}；"
         f"{n_pred}个预测refute中{n_false}伪",
         "NLI是召回引擎不是裁决器——必须配升级路由"),
        ("conformal高置信档不可信",
         f"kept档refute P={fmt(kept['precision'])}（n={kept['n_instances']}）；"
         f"整体 {fmt(cas['configs']['cascade_conformal']['macro_f1'])} < "
         f"{fmt(cas['configs']['cascade']['macro_f1'])}",
         "NLI的softmax置信度不承载refute精度信息"),
        ("fp16训练波动",
         f"同日重训评测macro-F1 {fmt(fp_lo, 4)}–{fmt(fp_hi, 4)}（极差≈0.10）",
         "单checkpoint数字不可复现到±0.05"),
        ("学习路由器学不出",
         f"held-out路由一致率 {held['routing_agreement']:.4f}（{n_agree}/{held['n']}）",
         f"oracle上限存在（{fmt(oracle['macro_f1'], 4)}@{oracle['llm_invocations']}次调用）"
         "但EGT监督学不出"),
        ("EGT近拷贝文法迁移失败",
         f"dev {fmt(egt['near_copy']['dev_macro_f1'], 4)} vs "
         f"真实 {fmt(egt['near_copy']['real_macro_f1'], 4)}",
         "合成文法定律的反面例证（dev对迁移零预测力）"),
    ]
    out = header(
        "负结果集一览（诚实科学）。六个负结果的数字分别取自：B1/L2/conformal"
        "（eval\\_paper\\_matrix + eval\\_cascade）、fp16波动端点（两个eval\\_nli\\_residual run）、"
        "路由held-out一致率（router\\_train\\_7a90549c）、EGT近拷贝（train\\_ade325ae + eval\\_4971ceba）。",
        "tab:negative", "对应论文章节 §6.1 负结果集（论文表11）", "p{2.9cm}p{4.4cm}p{4.6cm}")
    out += "负结果 & 关键数字 & 归因与科学价值 \\\\\n\\midrule\n"
    for i, (name, nums, value) in enumerate(rows, 1):
        out += f"{i}. {name} & {nums} & {value} \\\\\n"
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:test_honest 诚实评测
# ═══════════════════════════════════════════════════════════════════

def table_test_honest() -> str:
    rows = pdata.get_test_honest_rows()
    out = header(
        "test侧诚实评测（持久dev/test切分，test只在评测时整批运行一次）。"
        "修复=融合键剥离编号前缀/序列专家适用性门/id\\_join精确绑定三项确定性修复；"
        "legacy口径为全91自评（同配置fixed\\_cascade）。"
        "数字源：eval\\_test\\_honest\\_6740ed5c（修复前后两run）+ eval\\_router\\_2b76c358。",
        "tab:test_honest", "对应论文章节 §5.7 诚实评测（论文表10）", "p{3.4cm}ccccccc")
    out += "口径 & macro-F1 & acc & R-P & R-R & R-F1 & S-F1 & LLM调用 \\\\\n\\midrule\n"
    for r in rows:
        cfg = r["cfg"]
        pc = cfg["per_class"]
        macro = fmt(cfg["macro_f1"], 4)
        if "修复后" in r["label"]:
            macro = bold(macro)
        out += (f"{r['label']} & {macro} & {fmt(cfg['accuracy'], 4)} & "
                f"{fmt(pc['refute']['precision'])} & {fmt(pc['refute']['recall'])} & "
                f"{fmt(pc['refute']['f1'])} & {fmt(pc['support']['f1'])} & {r['llm']} \\\\\n")
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:crossdoc 跨文档泛化
# ═══════════════════════════════════════════════════════════════════

def table_crossdoc() -> str:
    cd = pdata.get_crossdoc_run()
    gap = cd["generalization_gap"]
    out = header(
        "跨文档泛化gap（04号训练/评测 → 06号自然复述文法；06号为30条构造性sound标签，"
        "S/R/N各10，不依赖LLM silver）。Δ per-class为06号−04号的各类F1差。"
        "数字源：eval\\_crossdoc\\_27e8ce32。",
        "tab:crossdoc", "对应论文章节 §5.6 跨文档泛化（论文表9）", "p{3.5cm}ccccc")
    out += "配置 & 04号macro-F1 & 06号macro-F1 & $\\Delta$ macro-F1 & $\\Delta$ R-F1 & $\\Delta$ S-F1 \\\\\n\\midrule\n"
    for c in ("deterministic", "cascade"):
        g = gap[c]
        dpc = g["delta_per_class_f1"]
        d_macro = bold(fmt_signed(g["delta_macro_f1"], 4))
        out += (f"{c} & {fmt(g['doc04_macro_f1'], 4)} & {fmt(g['doc06_macro_f1'], 4)} & "
                f"{d_macro} & {fmt_signed(dpc['refute'], 4)} & {fmt_signed(dpc['support'], 4)} \\\\\n")
    out += footer()
    return out


# ═══════════════════════════════════════════════════════════════════
# tab:experts L1九专家（系统设计描述，非实验数字）
# ═══════════════════════════════════════════════════════════════════

def table_experts() -> str:
    rows = [
        ("entity\\_detector", "L0", "TERM-05/07/08", "实体冲突检测（含ID在场护栏）"),
        ("e1\\_expert", "L1", "LOGIC-02",
         "E1模板文法：异常编号+触发条件+处置动作+终止/返回步骤；四项检查"
         "（锚点join/主题连贯/处置覆盖/接口存在）"),
        ("sequence\\_expert", "L1", "LOGIC-03", "步骤序列对齐（含适用性门：仅处理事件时序形态）"),
        ("trace\\_expert", "L1", "GJB-05", "追溯表双向join"),
        ("gjb\\_presence\\_expert", "L1", "GJB-01~11", "封闭清单有无检查（120条GJB规则库锚定OCR行号）"),
        ("id\\_join\\_expert", "L1", "TERM-07",
         "ID注册表join：四项检查（双登记冲突/subject-ID错配/组件段比对/裸ID匹配）"),
        ("enum\\_join\\_expert", "L1", "TERM-03",
         "枚举主体值域join：三来源注册表+封闭集合比对+错字归因（编辑距离1）"),
        ("numeric\\_z3\\_expert", "L1", "PARAM-01/03/05/06/07",
         "Z3数值约束：量纲换算+区间三态判定+跨参数聚合（附SMT-LIB+unsat core）"),
        ("coverage\\_expert", "L1", "GJB-01/04/06",
         "覆盖完备join：合格性覆盖图×章节能力清单×章节存在性三方join"),
    ]
    out = header(
        "L0/L1确定性专家族（九个符号通道，零LLM调用；本表为系统设计描述，"
        "检出效果的量化证据见tab:violation与tab:mutation）。",
        "tab:experts", "对应论文章节 §4.3 专家族（论文§6.3组件B）", "llp{2.6cm}p{6.2cm}")
    out += "专家 & 层级 & 检测项 & 机制要点 \\\\\n\\midrule\n"
    for name, layer, items, mech in rows:
        out += f"{name} & {layer} & {items} & {mech} \\\\\n"
    out += footer()
    return out


def build_tables() -> str:
    parts = [
        "% !TeX encoding = UTF-8\n",
        "% ============================================================\n"
        "% CascadeVerify论文表格（booktabs三线表）\n"
        "% 自动生成: python tools/make_paper_tables.py （请勿手改，重跑即覆盖）\n"
        "% 全部实验数字程序化提取自 data/gjb_438c/runs/ 的 result.json：\n",
    ]
    for line in RUN_SOURCES:
        parts.append(f"%   {line}\n")
    parts.append("% ============================================================\n"
                 "\\usepackage{booktabs}  % 若主文档已加载可删除本行\n\n")
    parts.append(table_main())
    parts.append(table_ablation())
    parts.append(table_bootstrap())
    parts.append(table_violation())
    parts.append(table_mutation())
    parts.append(table_negative())
    parts.append(table_test_honest())
    parts.append(table_crossdoc())
    parts.append(table_experts())
    return "".join(parts)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(OUT_DEFAULT))
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = build_tables()
    out.write_text(text, encoding="utf-8")
    n_tables = text.count("\\begin{table}")
    print(f"[OK] {out}  ({out.stat().st_size / 1024:.1f} KB, {n_tables}张表)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
