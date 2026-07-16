#!/Users/gexuancheng/Desktop/research2/data-juicer/.venv/bin/python3
"""测试运行: 5个医疗冲突检测算子 (直接调用 compute_stats_single / process_single).

采用与 run_timeseries_test.py 相同的直接调用方式, 不通过 Data-Juicer CLI.

分3阶段测试:
  阶段1: 5条已知样本 (2个冲突 + 3个正常)
  阶段2: 100条随机
  阶段3: 10000条全量

输出JSON报告到 medical_data/medtvt/output_dj/:
  - lab_range_stats.json
  - lab_diag_conflict_stats.json
  - cross_lab_stats.json
  - diag_consistency_stats.json
  - global_report.json
"""
import json
import os
import sys
from collections import Counter, defaultdict

# 基于脚本位置推导路径，支持从任意目录运行
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 注入 data-juicer 源码路径 (软链接在当前目录)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "data-juicer"))
sys.path.insert(0, SCRIPT_DIR)

from data_juicer.utils.constant import Fields
from medical_operators import (
    CrossLabConsistencyFilter,
    DiagnosisConsistencyFilter,
    LabDiagnosisConflictFilter,
    MedicalLabRangeFilter,
    MedtvtDataMapper,
)

JSONL = os.path.join(SCRIPT_DIR, "medical_data", "medtvt", "medtvt_dj.jsonl")
OUT_DIR = os.path.join(SCRIPT_DIR, "medical_data", "medtvt", "output_dj")
os.makedirs(OUT_DIR, exist_ok=True)

# 阶段1: 5条已知样本 (按 train.csv 行索引选取, 因 subject_id 不唯一)
# 冲突样本: row93 (12468016 乳酸9.0+肌酐2.4 NF=1), row5 (19931382 乳酸7.2+pH7.17 NF=1)
# 正常样本: row24 (19514041 NF=1 labs正常), row55 (12544417 非NF labs正常), row8 (15632977 非NF pH7.36)
PHASE1_ROWS = [93, 5, 24, 55, 8]


def load_samples():
    samples = []
    with open(JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                s = json.loads(line)
                s[Fields.stats] = {}
                samples.append(s)
    return samples


def run_pipeline(samples, kb_path=None):
    """对一批样本依次运行5个算子, 返回处理后的样本列表."""
    from medical_operators import DEFAULT_KB_PATH
    kb = kb_path or DEFAULT_KB_PATH
    mapper = MedtvtDataMapper(key_lab_itemids=["50893", "51237", "50931", "50971", "50820"])
    f_lab = MedicalLabRangeFilter(knowledge_base_path=kb)
    f_l2 = LabDiagnosisConflictFilter(knowledge_base_path=kb)
    f_l3 = CrossLabConsistencyFilter(knowledge_base_path=kb)
    f_diag = DiagnosisConsistencyFilter()
    out = []
    for s in samples:
        s = mapper.process_single(s)
        s = f_lab.compute_stats_single(s)
        s = f_l2.compute_stats_single(s)
        s = f_l3.compute_stats_single(s)
        s = f_diag.compute_stats_single(s)
        # process_single 恒返回 True (仅标记), 这里调用以验证不抛错
        _ = f_lab.process_single(s)
        _ = f_l2.process_single(s)
        _ = f_l3.process_single(s)
        _ = f_diag.process_single(s)
        out.append(s)
    return out


def summarize(samples):
    """汇总各算子检测结果."""
    n = len(samples)
    # L2 冲突分类
    l2_conflict_by_type = Counter()
    l2_severity = Counter()
    l2_conflict_samples = []
    l2_total_entries = 0
    for s in samples:
        stats = s.get(Fields.stats, {})
        clist = stats.get("lab_diag_conflict_list", [])
        if clist:
            sid = s.get("meta", {}).get("subject_id")
            l2_conflict_samples.append({
                "subject_id": sid,
                "conflicts": clist,
            })
            for c in clist:
                l2_conflict_by_type[c["type"]] += 1
                l2_severity[c["severity"]] += 1
                l2_total_entries += 1
    # L1
    l1_abnormal_count = sum(1 for s in samples if s[Fields.stats].get("lab_abnormal_count", 0) > 0)
    l1_by_item = Counter()
    l1_max_sev = Counter()
    for s in samples:
        for d in s[Fields.stats].get("lab_abnormal_list", []):
            l1_by_item[f"{d['itemid']}({d['name']})"] += 1
            if d.get("severity"):
                l1_max_sev[d["severity"]] += 1
    # L3
    l3_hits = Counter()
    l3_samples = 0
    for s in samples:
        clist = s[Fields.stats].get("cross_lab_conflict_list", [])
        if clist:
            l3_samples += 1
            for c in clist:
                l3_hits[c["name"]] += 1
    # D
    d_conflict = sum(1 for s in samples if s[Fields.stats].get("diag_consistency_conflict", False))
    d_by_reason = Counter()
    for s in samples:
        for r in s[Fields.stats].get("diag_conflict_reason", []):
            # 归并原因 (去掉具体标签名)
            if "互斥" in r:
                d_by_reason["No Finding 与阳性诊断互斥"] += 1
            elif "潜在冲突" in r:
                d_by_reason["No Finding 与不确定诊断潜在冲突"] += 1
            elif "编码异常" in r:
                d_by_reason["编码异常"] += 1
            else:
                d_by_reason[r] += 1
    return {
        "n_samples": n,
        "L2": {
            "total_conflict_entries": l2_total_entries,
            "conflict_samples": len(l2_conflict_samples),
            "conflict_by_type": dict(l2_conflict_by_type),
            "severity_distribution": dict(l2_severity),
            "samples": l2_conflict_samples,
        },
        "L1": {
            "abnormal_samples": l1_abnormal_count,
            "by_item": dict(l1_by_item.most_common(20)),
            "severity_distribution": dict(l1_max_sev),
        },
        "L3": {
            "syndrome_samples": l3_samples,
            "by_syndrome": dict(l3_hits),
        },
        "D": {
            "conflict_samples": d_conflict,
            "by_reason": dict(d_by_reason),
        },
    }


def write_report(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def phase1(samples):
    print("=" * 72)
    print("阶段1: 5条已知样本 (2冲突 + 3正常)")
    print("=" * 72)
    import copy
    phase1_samples = []
    for ridx in PHASE1_ROWS:
        if ridx < len(samples):
            s = copy.deepcopy(samples[ridx])
            s[Fields.stats] = {}
            phase1_samples.append(s)
        else:
            print(f"  [WARN] 行索引 {ridx} 越界")
    out = run_pipeline(phase1_samples)
    for i, s in enumerate(out):
        meta = s["meta"]
        stats = s[Fields.stats]
        labs = meta.get("labs", {})
        dx = meta.get("diagnosis", {})
        nf = dx.get("No Finding", 0)
        l2 = stats.get("lab_diag_conflict_list", [])
        l3 = stats.get("cross_lab_conflict_list", [])
        d = stats.get("diag_conflict_reason", [])
        print(f"  [{i+1}] row={PHASE1_ROWS[i]} sid={meta['subject_id']} NF={nf} "
              f"lact={labs.get('50893')} creat={labs.get('51237')} "
              f"gluc={labs.get('50931')} K={labs.get('50971')} pH={labs.get('50820')}")
        print(f"        L1异常={stats.get('lab_abnormal_count',0)} "
              f"L2冲突={stats.get('lab_diag_conflict_count',0)} "
              f"L3={stats.get('cross_lab_conflict_count',0)} "
              f"D={stats.get('diag_conflict_count',0)}")
        for c in l2:
            print(f"        -> L2: {c['type']} val={c['lab_value']} {c['severity']}")
        for c in l3:
            print(f"        -> L3: {c['name']} {c['severity']}")
        for r in d:
            print(f"        -> D: {r}")
    n_conflict = sum(1 for s in out if s[Fields.stats].get("lab_diag_conflict"))
    n_normal = len(out) - n_conflict
    print(f"\n  阶段1结果: 冲突样本={n_conflict} (期望2), 正常样本={n_normal} (期望3)")
    ok = n_conflict == 2 and n_normal == 3
    print(f"  验证: {'PASS' if ok else 'FAIL'}")
    return out, ok


def phase2(samples):
    print("\n" + "=" * 72)
    print("阶段2: 100条随机")
    print("=" * 72)
    import copy
    random.seed(42)
    idx = random.sample(range(len(samples)), 100)
    sub = [copy.deepcopy(samples[i]) for i in idx]
    for s in sub:
        s[Fields.stats] = {}
    out = run_pipeline(sub)
    summ = summarize(out)
    print(f"  样本数: {summ['n_samples']}")
    print(f"  L2冲突样本: {summ['L2']['conflict_samples']}, 冲突条目: {summ['L2']['total_conflict_entries']}")
    print(f"  L2分类: {summ['L2']['conflict_by_type']}")
    print(f"  L1异常样本: {summ['L1']['abnormal_samples']}")
    print(f"  L3综合征样本: {summ['L3']['syndrome_samples']}")
    print(f"  D冲突样本: {summ['D']['conflict_samples']}")
    return out, summ


def phase3(samples):
    print("\n" + "=" * 72)
    print("阶段3: 10000条全量")
    print("=" * 72)
    import copy
    sub = [copy.deepcopy(s) for s in samples]
    for s in sub:
        s[Fields.stats] = {}
    out = run_pipeline(sub)
    summ = summarize(out)
    print(f"  样本数: {summ['n_samples']}")
    print(f"  L2冲突条目总数: {summ['L2']['total_conflict_entries']} (期望~1444)")
    print(f"  L2冲突样本数: {summ['L2']['conflict_samples']}")
    print(f"  L2分类: {summ['L2']['conflict_by_type']}")
    print(f"  L2严重度: {summ['L2']['severity_distribution']}")
    print(f"  L1异常样本: {summ['L1']['abnormal_samples']}")
    print(f"  L3综合征样本: {summ['L3']['syndrome_samples']}")
    print(f"  L3分类: {summ['L3']['by_syndrome']}")
    print(f"  D冲突样本: {summ['D']['conflict_samples']}")
    print(f"  D分类: {summ['D']['by_reason']}")
    return out, summ


def main():
    print("=" * 72)
    print("Data-Juicer 医疗多模态数据冲突检测 — 算子测试")
    print("=" * 72)
    samples = load_samples()
    print(f"加载 {len(samples)} 条样本 (来自 {JSONL})")

    # 阶段1
    _, ok1 = phase1(samples)

    # 阶段2
    _, summ2 = phase2(samples)

    # 阶段3
    out3, summ3 = phase3(samples)

    # ---- 写报告文件 ----
    print("\n" + "=" * 72)
    print("写入报告文件到 output_dj/")
    print("=" * 72)

    # L1 lab_range_stats.json (基于全量)
    lab_range_report = {
        "total_samples": summ3["n_samples"],
        "abnormal_samples": summ3["L1"]["abnormal_samples"],
        "abnormal_rate": round(summ3["L1"]["abnormal_samples"] / summ3["n_samples"], 4),
        "by_item_top20": summ3["L1"]["by_item"],
        "severity_distribution": summ3["L1"]["severity_distribution"],
        "description": "L1 单指标正常范围检测: 血检值超出知识库L1_lab_ranges的样本统计",
    }
    write_report("lab_range_stats.json", lab_range_report)
    print("  -> lab_range_stats.json")

    # L2 lab_diag_conflict_stats.json (基于全量)
    l2_report = {
        "total_samples": summ3["n_samples"],
        "total_conflict_entries": summ3["L2"]["total_conflict_entries"],
        "conflict_samples": summ3["L2"]["conflict_samples"],
        "conflict_rate": round(summ3["L2"]["total_conflict_entries"] / summ3["n_samples"], 4),
        "conflict_by_type": summ3["L2"]["conflict_by_type"],
        "severity_distribution": summ3["L2"]["severity_distribution"],
        "description": "L2 血检异常 vs 诊断标签冲突: 指标超严重阈值且诊断=No Finding",
        "conflict_samples_detail": summ3["L2"]["samples"][:200],  # 前200个样本明细
    }
    write_report("lab_diag_conflict_stats.json", l2_report)
    print("  -> lab_diag_conflict_stats.json")

    # L3 cross_lab_stats.json
    l3_report = {
        "total_samples": summ3["n_samples"],
        "syndrome_samples": summ3["L3"]["syndrome_samples"],
        "by_syndrome": summ3["L3"]["by_syndrome"],
        "description": "L3 多指标协同一致性: 多指标组合同时满足知识库L3规则",
    }
    write_report("cross_lab_stats.json", l3_report)
    print("  -> cross_lab_stats.json")

    # D diag_consistency_stats.json
    d_report = {
        "total_samples": summ3["n_samples"],
        "conflict_samples": summ3["D"]["conflict_samples"],
        "by_reason": summ3["D"]["by_reason"],
        "description": "诊断标签间一致性: No Finding与其他诊断互斥检查",
    }
    write_report("diag_consistency_stats.json", d_report)
    print("  -> diag_consistency_stats.json")

    # global_report.json
    expected = {"乳酸酸中毒漏诊": 1160, "肾功能异常漏诊": 132, "高血糖漏诊": 68,
                "高钾血症漏诊": 50, "严重酸中毒漏诊": 34}
    global_report = {
        "total_samples": summ3["n_samples"],
        "pipeline": ["medtvt_data_mapper", "medical_lab_range_filter",
                     "lab_diagnosis_conflict_filter", "cross_lab_consistency_filter",
                     "diagnosis_consistency_filter"],
        "phase1_test": {
            "samples": len(PHASE1_ROWS),
            "conflicts_detected": 2 if ok1 else "FAIL",
            "normal_detected": 3 if ok1 else "FAIL",
            "passed": ok1,
        },
        "phase2_100random": {
            "l2_conflict_entries": summ2["L2"]["total_conflict_entries"],
            "l2_conflict_samples": summ2["L2"]["conflict_samples"],
            "l2_by_type": summ2["L2"]["conflict_by_type"],
        },
        "phase3_full": {
            "l2_conflict_entries": summ3["L2"]["total_conflict_entries"],
            "l2_conflict_samples": summ3["L2"]["conflict_samples"],
            "l2_by_type": summ3["L2"]["conflict_by_type"],
            "l2_severity": summ3["L2"]["severity_distribution"],
            "expected_l2_by_type": expected,
            "expected_total": 1444,
            "aligned_with_reference": summ3["L2"]["total_conflict_entries"] == 1444,
            "l1_abnormal_samples": summ3["L1"]["abnormal_samples"],
            "l3_syndrome_samples": summ3["L3"]["syndrome_samples"],
            "l3_by_syndrome": summ3["L3"]["by_syndrome"],
            "d_conflict_samples": summ3["D"]["conflict_samples"],
        },
        "summary": {
            "l2_total_conflicts": summ3["L2"]["total_conflict_entries"],
            "reference_conflicts": 1444,
            "alignment": "PASS" if summ3["L2"]["total_conflict_entries"] == 1444 else "CHECK",
        },
    }
    write_report("global_report.json", global_report)
    print("  -> global_report.json")

    print("\n" + "=" * 72)
    print("测试完成!")
    print(f"  阶段1 (5样本): {'PASS' if ok1 else 'FAIL'}")
    print(f"  阶段3 (全量) L2冲突: {summ3['L2']['total_conflict_entries']} / 期望1444 -> "
          f"{'PASS' if summ3['L2']['total_conflict_entries']==1444 else 'CHECK'}")
    print(f"  报告目录: {OUT_DIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()
