"""Step3: if-else启发式簇 → 模型替换可行性判定表(登记到distillation).

依据: tools/audit_ifelse_density.py(ifelse_audit_v1.json) +
tools/exp_model_replace.py(model_replace_v1.json, test46基线acc0.9130/
mF1 0.8047/rF1 0.800已复现). 本脚本只做数字登记与判定规则落盘,
不重跑实验.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

AUDIT = BASE / "data/gjb_438c/distillation/ifelse_audit_v1.json"
EXP = BASE / "data/gjb_438c/distillation/model_replace_v1.json"
OUT = BASE / "data/gjb_438c/distillation/ifelse_feasibility_v1.json"


def git_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=BASE, capture_output=True, text=True,
                              timeout=10, check=False)
        return proc.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    exp = json.loads(EXP.read_text(encoding="utf-8"))
    base = exp["variants"]["A0_baseline"]["per_dataset"]["test46"]["metrics"]

    def m(variant: str, ds: str = "test46") -> dict:
        return exp["variants"][variant]["per_dataset"][ds]["metrics"]

    def delta(variant: str, key: str, ds: str = "test46") -> float:
        return round(m(variant, ds)[key] - base[key], 4)

    focus = audit["focus_files"]
    cc = focus["claim_channels.py"]
    qm = focus["qa_module.py"]
    qr = focus["qa_router.py"]
    ce = focus["coverage_expert.py"]

    table = [
        {
            "cluster": "qa_module._verify_claim typed分派 (L604-614)",
            "if_else": 5,
            "audit": qm["top_clusters"][1],
            "model_replace": "A1: verify_numeric/quoted/enum/identifier→"
                             "distilled_v1 NLI(residual_premise+_infer,"
                             "gate0.8)",
            "test46": {"acc": m("A1_typed_nli")["accuracy"],
                       "mF1": m("A1_typed_nli")["macro_f1"],
                       "rF1": m("A1_typed_nli")["per_class"]["refute"]["f1"],
                       "delta_acc": delta("A1_typed_nli", "accuracy"),
                       "delta_mF1": delta("A1_typed_nli", "macro_f1")},
            "verdict": "保留",
            "reason": "mF1 -0.0930(support F1 0.667→0.400, 1实例退化); "
                      "typed通道仅承接25/294 claim(8.5%)但都是高精度"
                      "support(identifier精确匹配/数值区间), NLI@gate0.8"
                      "给不出同级精度的support; 安全侧不受影响"
                      "(violations17 rF1不变)",
        },
        {
            "cluster": "claim_channels.verify_* 正则守卫 "
                       "(subset/disjoint/极性/穷举, 43 if/11三元)",
            "if_else": cc["n_if"],
            "audit": cc["top_clusters"],
            "model_replace": "A1同上(四个verify整体换NLI, 无typed分派)",
            "test46": "见上行(同一实验)",
            "verdict": "保留",
            "reason": "同A1: 区间包含/互斥与显式极性判定是可解释的确定性"
                      "代数, NLI在门控下保守化后丢掉精确support; "
                      "跨域也未获益(crossdoc acc 0.5133→0.5000)",
        },
        {
            "cluster": "claim_segmenter替换正则decompose + 全claim NLI "
                       "(answer_claims.decompose_claims, 17 if全管道型)",
            "if_else": 17,
            "audit": focus["answer_claims.py"],
            "model_replace": "A2: segmenter_v2切分+distilled_v1 NLI",
            "test46": {"acc": m("A2_seg_nli")["accuracy"],
                       "mF1": m("A2_seg_nli")["macro_f1"],
                       "rF1": m("A2_seg_nli")["per_class"]["refute"]["f1"],
                       "delta_acc": delta("A2_seg_nli", "accuracy"),
                       "delta_mF1": delta("A2_seg_nli", "macro_f1")},
            "verdict": "保留",
            "reason": "mF1 0.5789(-0.2258), support预测0条(467条短碎片"
                      "claim在strict∀下被NIE一票否决, M87/M88现象复现); "
                      "且test46推理316s vs 正则8s(40x延迟, 无批处理); "
                      "模型切分需要配套assertive聚合才能用",
        },
        {
            "cluster": "qa_module._aggregate 聚合阶梯 (L699-743, "
                       "strict/dominant_70/no_minor_block/assertive_*)",
            "if_else": 6,
            "audit": qm["top_clusters"][0],
            "model_replace": "B: 置信度加权投票(w=confidence×is_assertive, "
                             "refute×2安全序)",
            "test46": {"acc": m("B_agg_vote")["accuracy"],
                       "mF1": m("B_agg_vote")["macro_f1"],
                       "rF1": m("B_agg_vote")["per_class"]["refute"]["f1"],
                       "delta_acc": delta("B_agg_vote", "accuracy"),
                       "delta_mF1": delta("B_agg_vote", "macro_f1")},
            "crossdoc150": {"acc": m("B_agg_vote", "crossdoc150")["accuracy"],
                            "delta_acc": delta("B_agg_vote", "accuracy",
                                               "crossdoc150"),
                            "delta_mF1": delta("B_agg_vote", "macro_f1",
                                               "crossdoc150")},
            "verdict": "保留(域内) / 可换(跨域)",
            "reason": "test46灾难性退化(acc 0.3913, mF1 0.4758=-0.3289; "
                      "26实例NIE→support误翻, support P=0.103)——91QA"
                      "标签分布NIE重(39/46), strict的'任一NIE阻断'正是域"
                      "先验; 但crossdoc150大涨(acc 0.5133→0.6800, "
                      "mF1 +0.167, 30纠正/5退化)——软聚合在标签均衡的跨域"
                      "场景更优(与M82 dominant_70结论一致). refute安全序"
                      "在两种场景都稳(violations17不变)",
        },
        {
            "cluster": "qa_router.route_question 关键词路由 (40规则/80词, "
                       "0个if语句——纯数据表)",
            "if_else": 0,
            "audit": qr,
            "model_replace": "C: route_question返回() (规则删除, "
                             "非模型化)",
            "test46": {"acc": m("C_route_off")["accuracy"],
                       "mF1": m("C_route_off")["macro_f1"],
                       "rF1": m("C_route_off")["per_class"]["refute"]["f1"],
                       "delta_acc": delta("C_route_off", "accuracy"),
                       "delta_mF1": delta("C_route_off", "macro_f1")},
            "verdict": "删除",
            "reason": "三数据集verdict零翻转(test46/violations17/"
                      "crossdoc150逐实例一致, M73在NLI残差配置下复验"
                      "通过): 路由只产check_item候选标签(纯注记), "
                      "不参与verdict决策; 40规则表+3处消费点是可删的"
                      "惰性代码",
        },
        {
            "cluster": "coverage_expert.verify_coverage claim.kind分派 "
                       "(L721-729)",
            "if_else": 3,
            "audit": ce["top_clusters"][0],
            "model_replace": "未实验(静态判定)",
            "test46": None,
            "verdict": "保留",
            "reason": "3分支kind分派只是选择确定性子检查器(scope/precise/"
                      "gjb_clause), 子检查器各自产verdict; 属管道型路由"
                      "(61 if中仅11决策型), 模型化收益低且会失去覆盖"
                      "完备性检查的可解释性",
        },
    ]

    out = {
        "tool": "tools/exp_model_replace.py(Step3判定登记)",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "evidence": {
            "audit": "data/gjb_438c/distillation/ifelse_audit_v1.json",
            "experiment": "data/gjb_438c/distillation/model_replace_v1.json",
            "baseline_test46": {"acc": base["accuracy"],
                                "mF1": base["macro_f1"],
                                "rF1": base["per_class"]["refute"]["f1"],
                                "reproduced": exp["baseline_reproduced"]},
            "totals": audit["totals"],
        },
        "judgment_rules": {
            "可换": "模型替换后test46 acc/mF1不降(≤0.005)",
            "保留": "模型替换后掉点(登记delta); 或簇为管道型路由",
            "删除": "消融后逐实例verdict零翻转(惰性/纯注记)",
        },
        "table": table,
        "headline": {
            "decision_if_share": "203/1653 ifs(12.3%)为决策型——"
                                 "可模型化的面很窄, 87.7%是管道型",
            "deletable": "qa_router 40规则/80关键词(纯注记, 零verdict影响)",
            "model_replaced_already": "语义决策已由distilled_v1 NLI承担"
                                      "(nli_residual, 29/294 claim)",
            "safe_to_keep": "typed正则verify(高精度support)+strict聚合"
                            "(域先验)",
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"输出: {OUT}")
    for row in table:
        perf = row.get("test46")
        perf_s = ("acc{:+.4f}/mF1{:+.4f}".format(
            perf["delta_acc"], perf["delta_mF1"]) if isinstance(perf, dict)
            else (perf or "—"))
        print(f"  [{row['verdict']:12s}] {row['cluster'][:46]:48s} {perf_s}")


if __name__ == "__main__":
    main()
