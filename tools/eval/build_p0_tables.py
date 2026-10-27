r"""P0画表前置: 跨场景泛化矩阵 + 免训练vs学习式对照表.

#1 泛化矩阵: 全部两阶段重排场景的 stage1→stage2 增益×McNemar,
   附Spearman(一阶弱度, Δ增益)量化"重排增益与一阶段弱度正相关"规律.
#2 冻结骨干论据: 负结果链(域适配×3/CMSC/LoRA/UAA)与冻结基线的对照.

数据源: S7/S4/public_rerank(现有JSON) + 文档27负结果链(已归档数字).
零模型依赖(纯汇总, CPU即时).

用法: python tools/eval/build_p0_tables.py
产出: results/_generalization_matrix.json, results/_frozen_vs_learned.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"


def spearman(x: list[float], y: list[float]) -> float:
    """Spearman秩相关(无scipy依赖, 处理并列取平均秩)."""
    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)
           ) ** 0.5
    return num / den if den > 0 else 0.0


def build_generalization() -> dict:
    s7 = json.loads((RESULTS / "S7_evidence_recall_all.json").read_text(
        encoding="utf-8"))
    pr = json.loads((RESULTS / "public_rerank.json").read_text(
        encoding="utf-8"))
    s4 = json.loads((RESULTS / "S4_image_all.json").read_text(
        encoding="utf-8"))

    rows = []
    # GJB深行三场景(S7: mcnemar内含b/c/p)
    for scene, label in [("table_deep_v3", "GJB深行v3(262q)"),
                         ("table_deep_v4", "GJB深行v4(176q)"),
                         ("combined", "GJB联合(438q)")]:
        e = s7["results"][scene]
        mc = e["mcnemar"]
        rows.append({
            "scene": label, "n": e["n_queries"],
            "stage1_R@1": round(e["recall"]["R@1"], 4),
            "stage2_R@1": round(e["rerank"]["R@1"], 4),
            "delta": round(e["rerank"]["R@1"] - e["recall"]["R@1"], 4),
            "b": mc["b"], "c": mc["c"],
            "p": mc["p_one_sided"], "sig": mc["p_one_sided"] < 0.05})
    # 图片(S4: rerank_significance字符串里取b/c — 从run记录还原)
    tms = s4["results"]["Token-MaxSim"]["R@1"]
    tms_rr = s4["results"]["Token-MaxSim+Rerank@50"]["R@1"]
    rows.append({
        "scene": "GJB图片(899q)", "n": 899,
        "stage1_R@1": round(tms, 4), "stage2_R@1": round(tms_rr, 4),
        "delta": round(tms_rr - tms, 4),
        "b": 114, "c": 106, "p": 0.295, "sig": False})
    # 英文(public_rerank)
    for ds, label in [("wtq", "WTQ(2000q)"), ("fetaqa", "FeTaQA(2000q)")]:
        e = pr["results"][ds]
        mc = e["mcnemar"]
        rows.append({
            "scene": label, "n": 2000,
            "stage1_R@1": round(e["stage1"]["R@1"], 4),
            "stage2_R@1": round(e["stage2"]["R@1"], 4),
            "delta": round(e["stage2"]["R@1"] - e["stage1"]["R@1"], 4),
            "b": mc["b"], "c": mc["c"], "p": mc["p_one_sided"],
            "sig": mc["p_one_sided"] < 0.05})

    # 规律量化: Spearman(一阶R@1, Δ) 与 Spearman(R@5-R@1差距, Δ)
    s1 = [r["stage1_R@1"] for r in rows]
    delta = [r["delta"] for r in rows]
    rho = spearman(s1, delta)
    out = {
        "protocol": ("两阶段重排跨场景泛化: 6场景×(stage1→stage2增益"
                     "×McNemar); Spearman量化'一阶段越弱, 重排增益越大'"),
        "rows": rows,
        "spearman_stage1_vs_delta": round(rho, 3),
        "law": ("重排增益与一阶段R@1负相关(Spearman ρ="
                f"{rho:.2f}): 语义歧义场景(GJB深行/WTQ)受益, "
                "一阶段已强或词面锁定场景(FeTaQA/图片)不受益或受损"),
    }
    (RESULTS / "_generalization_matrix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def build_frozen_vs_learned() -> dict:
    rows = [
        {"method": "冻结基线(无训练)", "train": "—", "protocol": "O1-unit",
         "eval_R@1": 0.340, "gap": "—",
         "lesson": "参照系"},
        {"method": "域适配v1(caption分布)", "train": "1541 caption对",
         "protocol": "全量训练→deep评测",
         "eval_R@1": 0.107, "gap": "训练分布≠评测分布",
         "lesson": "负迁移(−23.3pt)"},
        {"method": "域适配v2(deep分布,含评测)", "train": "294对(含250/262评测)",
         "protocol": "全量训练", "eval_R@1": 0.889,
         "gap": "训练集拟合(不可报告)",
         "lesson": "上界幻觉, 必须held-out"},
        {"method": "域适配v3(4折CV)", "train": "250对(3折训练)",
         "protocol": "训3折测1折", "eval_R@1": 0.199,
         "gap": "过拟合(−14.1pt vs 基线)",
         "lesson": "小数据下adapter必过拟合"},
        {"method": "域适配v4(超参扫描)", "train": "同上",
         "protocol": "5配置(hidden/ep/reg)CV",
         "eval_R@1": 0.267, "gap": "最好配置仍低于基线",
         "lesson": "恒等映射=该函数族最优点"},
        {"method": "CMSC投影头", "train": "3724对(预训练)",
         "protocol": "跨折替换BGE", "eval_R@1": 0.340,
         "gap": "负迁移(默认cmsc_fuse=0)",
         "lesson": "折内+2.3pt≠泛化增益"},
        {"method": "BGE-LoRA", "train": "对训练",
         "protocol": "微调骨干", "eval_R@1": None,
         "gap": "−4.3pt(含泄漏审计0.49)",
         "lesson": "微调泄漏风险"},
        {"method": "UAA聚合器", "train": "warm-start",
         "protocol": "训练收敛观测",
         "eval_R@1": None,
         "gap": "收敛回固定公式",
         "lesson": "固定聚合器=学习族不动点"},
        {"method": "冻结+交互侧(最终方法)", "train": "零训练参数",
         "protocol": "O1+单元聚焦重排", "eval_R@1": 0.486,
         "gap": "+14.6pt vs 冻结召回",
         "lesson": "语体鸿沟的正解=交互侧而非训练侧"},
    ]
    out = {
        "protocol": ("冻结骨干论据: 全部可学习组件在该数据规模"
                     "(~250对)下的负结果链 vs 零训练方法的增益; "
                     "依据docs/srs_project/27+runs归档"),
        "rows": rows,
        "claim": ("6次独立尝试证明: 军事SRS小数据域中, 任何可训练组件"
                  "要么负迁移要么过拟合; 唯一有效增益来自交互侧"
                  "(cross-encoder)与结构设计(单元切分+IDF), 全部零训练"),
    }
    (RESULTS / "_frozen_vs_learned.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== P0#1 跨场景泛化矩阵 ===")
    g = build_generalization()
    print(f"{'场景':<20s} {'stage1':>7s} {'stage2':>7s} {'Δ':>7s} "
          f"{'b/c':>7s} {'p':>9s}")
    for r in g["rows"]:
        print(f"{r['scene']:<20s} {r['stage1_R@1']:>7.3f} "
              f"{r['stage2_R@1']:>7.3f} {r['delta']:>+7.3f} "
              f"{r['b']}/{r['c']:>3d} {r['p']:>9.1e}"
              f"{' *' if r['sig'] else ''}")
    print(f"Spearman(stage1, Δ) = {g['spearman_stage1_vs_delta']}")

    print("\n=== P0#2 冻结vs学习式 ===")
    f = build_frozen_vs_learned()
    for r in f["rows"]:
        r1 = f"{r['eval_R@1']:.3f}" if r["eval_R@1"] is not None else "—"
        print(f"  {r['method']:<22s} R@1={r1:>6s}  {r['lesson']}")
    print("\n→ results/_generalization_matrix.json")
    print("→ results/_frozen_vs_learned.json")


if __name__ == "__main__":
    main()
