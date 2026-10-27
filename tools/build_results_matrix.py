r"""全方法×全数据集汇总表生成器(论文主表).

汇聚所有评测JSON: 8个评测场景×~15个方法×4个指标(R@1/R@5/R@10/MRR@10),
按原生(GJB)与外部(WTQ/FeTaQA/DuRetrieval/PURE-MMQA)分块,
方法按家族分组(词面/稠密/后期交互/单元/路由/重排/学习式/SOTA).

用法: python tools/build_results_matrix.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
E = BASE / "data/gjb_438c/data_assets"
EV = E / "evalsets"
METRICS = ["R@1", "R@5", "R@10", "MRR@10"]

# 方法显示名与家族分组
FAMILIES = [
    ("词面(稀疏)", [
        ("BM25-doc", "BM25-doc"),
        ("BM25-unit", "BM25-unit"),
        ("Cell-BM25", "Cell-BM25"),
    ]),
    ("稠密(单向量)", [
        ("B1-dense", "B1-dense(zh)"),
        ("B1_bridge", "B1-dense(zh)"),
        ("B1_dense", "B1-dense(zh)"),
        ("HyDE-dense", "HyDE-dense"),
        ("E5-dense", "E5-dense(mE5)"),
        ("M3-dense", "M3-dense(SOTA 8192)"),
        ("M3-dense@4096", "M3-dense(4096)"),
    ]),
    ("后期交互(token级)", [
        ("Token-MaxSim", "Token-MaxSim(ColBERT式)"),
        ("M3-colbert", "M3-colbert(SOTA)"),
    ]),
    ("单元级(我们)", [
        ("O1-unit", "O1-unit(行/节点+IDF)"),
        ("O1-unit(对照)", "O1-unit(行+IDF)"),
        ("O1-unit(fixed-serialization)", "O1-unit(修复序列化)"),
        ("O1-unit(框架)", "O1-unit(evidence_recall框架)"),
        ("VA_colpali", "O1-unit(图+CMSC融合)"),
        ("TP-raw", "O1-TP-raw(词面画像)"),
        ("TP-cc", "O1-TP-cc(标题拼接)"),
        ("TP-cf", "O1-TP-cf(池模糊IDF)"),
        ("E5-unit", "O1-unit(E5)"),
        ("HyDE-unit", "O1-unit(HyDE)"),
    ]),
    ("路由融合", [
        ("ROUTE4", "ROUTE4(BM25+unit)"),
        ("ROUTE5", "ROUTE5(+Token)"),
        ("R(d,raw)", "R(d,TP-raw)"),
        ("R(d,cc)", "R(d,TP-cc)"),
        ("R(d,cf)", "R(d,TP-cf)"),
        ("ROUTE(O1+M3)", "R(O1+M3)"),
    ]),
    ("精排(两阶段)", [
        ("O1+rrF", "O1+重排(全文)"),
        ("O1+rrS", "O1+重排(片段)"),
        ("O2a_unit_rrF", "O1+重排(全文)"),
        ("B2_dense_rrF", "B1+重排(全文)"),
        ("M3+rrF", "M3+重排(全文)"),
        ("O1-unit+Rerank@20(full)", "O1+重排(全表dump,负)"),
        ("O1-unit+Rerank(top50,unit2,b0.1)", "O1+重排(单元聚焦)"),
        ("Token-MaxSim+Rerank@50", "TMS+重排(单元聚焦)"),
        ("O1+Rerank(框架)", "O1+重排(单元聚焦,框架)"),
        ("O1-unit(en)", "O1+重排前(en)"),
        ("O1-unit+Rerank(en)", "O1+重排(单元聚焦,en)"),
    ]),
]

# 场景定义: (显示名, JSON路径, 场景key, 方法名key_prefix)
# 注: V3重构后旧评测JSON迁移至results/(_前缀)或保留在evalsets根
SCENES = [
    # 原生(GJB)
    ("GJB图", E / "va_colpali_eval.json", None),
    ("GJB表caption", E / "table_late_eval.json", "caption"),
    ("GJB深行v1", E / "table_late_eval.json", "deep_v1"),
    ("GJB深行v2", E / "table_late_eval.json", "deep_v2"),
    ("GJB深行v2(全法)", EV / "deep_v2_eval.json", None),
    ("GJB深行v2(补充)", EV / "deep_v2_extra_baselines.json", None),
    # 外部(en)
    ("WTQ", EV / "results" / "_public_en_raw.json", "wtq"),
    ("FeTaQA", EV / "results" / "_public_en_raw.json", "fetaqa"),
    ("DuRetrieval", EV / "results" / "_duret_full_raw.json", None),
    # Token-MaxSim
    ("GJB图(token)", EV / "results" / "_token_maxsim_raw.json", "gjb_image"),
    ("GJB深行v1(token)", EV / "results" / "_token_maxsim_raw.json",
     "gjb_table_deep"),
    ("WTQ(token)", EV / "results" / "_token_maxsim_raw.json", "wtq"),
    ("FeTaQA(token)", EV / "results" / "_token_maxsim_raw.json", "fetaqa"),
    # V3统一评测(S1修复后) + 两阶段重排
    ("GJB深行v3", EV / "results" / "S1_deep_v3_all.json", None),
    ("GJB图(v3)", EV / "results" / "S4_image_all.json", None),
    ("GJB深行v1(对照v3)", EV / "results" / "S3_deep_v1_all.json", None),
    ("FeTaQA(重排en)", EV / "results" / "public_rerank.json", "fetaqa"),
    ("WTQ(重排en)", EV / "results" / "public_rerank.json", "wtq"),
    # V4扩展(16文档) — 存在时纳入
    ("GJB深行v4", EV / "results" / "S5_deep_v4_all.json", None),
    ("GJB深行v3+v4", EV / "results" / "S6_deep_v34_all.json", None),
    # evidence_recall框架验证(S7/S8, 单元级家族)
    ("GJB(框架S7)", EV / "results" / "S7_evidence_recall_all.json",
     "combined"),
    ("WTQ(框架S8)", EV / "results" / "S8_evidence_recall_external.json",
     "wtq"),
    ("FeTaQA(框架S8)", EV / "results" / "S8_evidence_recall_external.json",
     "fetaqa"),
    ("DuRetrieval(框架S8)", EV / "results" /
     "S8_evidence_recall_external.json", "duret"),
    ("PURE-MMQA(框架S8)", EV / "results" /
     "S8_evidence_recall_external.json", "pure"),
]


def load_metrics(path: Path, scene_key: str | None) -> dict:
    """→ {method_name: {R@1: val, R@5: val, ...}}"""
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    rs = d.get("results", d)
    if scene_key:
        rs = rs.get(scene_key, {})
        # public_rerank嵌套结构: stage1/stage2 → 方法名
        if "stage1" in rs and isinstance(rs.get("stage1"), dict):
            return {"O1-unit(en)": rs["stage1"],
                    "O1-unit+Rerank(en)": rs["stage2"]}
    # S7/S8框架验证结构: recall/rerank → 方法名
    if (not scene_key and isinstance(rs, dict) and "recall" in rs
            and isinstance(rs.get("recall"), dict)
            and "R@1" in rs.get("recall", {})):
        return {"O1-unit(框架)": rs["recall"],
                "O1+Rerank(框架)": rs.get("rerank", {})}
    if scene_key and "recall" in rs and isinstance(
            rs.get("recall"), dict) and "R@1" in rs.get("recall", {}):
        return {"O1-unit(框架)": rs["recall"],
                "O1+Rerank(框架)": rs.get("rerank", {})}
    out = {}
    for mk, mv in rs.items():
        if isinstance(mv, dict) and "R@1" in mv:
            out[mk] = {m: mv.get(m) for m in METRICS}
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    # 汇聚所有场景
    all_data = {}
    for label, path, sk in SCENES:
        m = load_metrics(path, sk)
        if m:
            all_data[label] = m

    # 场景分组
    native = ["GJB图", "GJB表caption", "GJB深行v1", "GJB深行v2"]
    native_extra = ["GJB深行v2(全法)", "GJB深行v2(补充)",
                    "GJB图(M3)", "GJB深行v2(M3)", "GJB表caption(M3)",
                    "GJB图(token)", "GJB深行v1(token)",
                    "GJB图(v3)", "GJB深行v3", "GJB深行v1(对照v3)",
                    "GJB深行v4", "GJB深行v3+v4"]
    external = ["WTQ", "WTQ(zh)", "FeTaQA", "DuRetrieval", "PURE-MMQA",
                "WTQ(M3)", "FeTaQA(M3)", "WTQ(token)", "FeTaQA(token)",
                "WTQ(重排en)", "FeTaQA(重排en)",
                "WTQ(框架S8)", "FeTaQA(框架S8)", "DuRetrieval(框架S8)",
                "PURE-MMQA(框架S8)"]

    print("=" * 100)
    print("全方法×全数据集结果矩阵(所有锁定数字汇聚)")
    print("=" * 100)

    for scenes, title in [
        (native + native_extra, "原生数据集(GJB-URE-v2)"),
        (external, "外部数据集"),
    ]:
        print(f"\n### {title}")
        # 方法按家族分组
        for fam, methods in FAMILIES:
            rows = []
            for json_key, display in methods:
                row = {"方法": display}
                has = False
                for sc in scenes:
                    sc_data = all_data.get(sc, {})
                    if json_key in sc_data:
                        v = sc_data[json_key]
                        r10 = v.get("R@10") or 0
                        row[sc] = (f'{v["R@1"]:.3f}/{v["R@5"]:.3f}/'
                                   f'{r10:.3f}/{v["MRR@10"]:.3f}')
                        has = True
                if has:
                    rows.append(row)
            if rows:
                print(f"\n**{fam}**")
                cols = ["方法"] + [s for s in scenes
                                  if any(s in r for r in rows)]
                # markdown表
                print("| " + " | ".join(cols) + " |")
                print("|" + "|".join(["---"] * len(cols)) + "|")
                for r in rows:
                    cells = [r.get(c, "—") for c in cols]
                    print("| " + " | ".join(cells) + " |")

    # 保存为JSON
    out = EV / "full_results_matrix.json"
    out.write_text(json.dumps({
        "protocol": "全方法×全数据集汇聚(所有锁定数字); R@1/R@5/R@10/MRR@10",
        "scenes": {k: v for k, v in all_data.items()},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {out}")
    print(f"场景数: {len(all_data)}, 方法数: {len(FAMILIES)}家族")


if __name__ == "__main__":
    main()
