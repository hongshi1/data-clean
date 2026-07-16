#!/Users/gexuancheng/Desktop/research2/data-juicer/.venv/bin/python3
"""测试运行: 4个NLMCXR胸片报告冲突检测算子 (直接调用 compute_stats_single / process_single).

采用与 run_medical_dj.py 相同的直接调用方式, 不通过 Data-Juicer CLI.

测试20条NLMCXR样本, 输出JSON报告到 nlmcxr/output_dj/:
  - xray_analysis_stats.json   (X光片疾病推理结果)
  - report_ner_stats.json      (报告NER三态标注)
  - conflict_stats.json        (图片-报告冲突检测)
  - global_report.json         (全局汇总)
"""
import json
import os
import sys
from collections import Counter

# 基于脚本位置推导路径，支持从任意目录运行
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "data-juicer"))
sys.path.insert(0, SCRIPT_DIR)

from data_juicer.utils.constant import Fields
from nlmcxr_operators import (
    ImageReportConflictFilter,
    NlmcxrDataMapper,
    ReportNerFilter,
    XrayImageAnalysisFilter,
    DISEASES,
)

JSONL = os.path.join(SCRIPT_DIR, "nlmcxr", "nlmcxr_dj.jsonl")
OUT_DIR = os.path.join(SCRIPT_DIR, "nlmcxr", "output_dj")
os.makedirs(OUT_DIR, exist_ok=True)


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


def run_pipeline(samples):
    """对一批样本依次运行4个算子, 返回处理后的样本列表."""
    mapper = NlmcxrDataMapper()
    f_xray = XrayImageAnalysisFilter()
    f_ner = ReportNerFilter(window=30)
    f_conflict = ImageReportConflictFilter()
    out = []
    for i, s in enumerate(samples):
        s = mapper.process_single(s)
        s = f_xray.compute_stats_single(s)
        s = f_ner.compute_stats_single(s)
        s = f_conflict.compute_stats_single(s)
        # process_single 恒返回 True (仅标记), 调用以验证不抛错
        _ = f_xray.process_single(s)
        _ = f_ner.process_single(s)
        _ = f_conflict.process_single(s)
        out.append(s)
        meta = s.get("meta", {})
        stats = s.get(Fields.stats, {})
        n_conf = stats.get("conflict_count", 0)
        print(f"  [{i+1:2d}/{len(samples)}] idx={meta.get('idx')} "
              f"conflicts={n_conf}")
    return out


def write_report(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def build_xray_report(samples):
    """X光片疾病推理报告."""
    per_sample = []
    disease_positive = Counter()
    for s in samples:
        stats = s.get(Fields.stats, {})
        meta = s.get("meta", {})
        preds = stats.get("xray_predictions", {})
        sample_entry = {"idx": meta.get("idx"), "predictions": preds}
        per_sample.append(sample_entry)
        for d in DISEASES:
            if preds.get(d, {}).get("positive", False):
                disease_positive[d] += 1
    return {
        "total_samples": len(samples),
        "description": "TorchXRayVision DenseNet121 (densenet121-res224-mimic_ch) "
                       "X光片疾病推理, raw output > 0.5 判断阳性 (CPU运行)",
        "positive_count_by_disease": dict(disease_positive),
        "per_sample": per_sample,
    }


def build_ner_report(samples):
    """报告NER标注报告."""
    per_sample = []
    state_count = {d: Counter() for d in DISEASES}
    normal_count = 0
    for s in samples:
        stats = s.get(Fields.stats, {})
        meta = s.get("meta", {})
        findings = stats.get("report_findings", {})
        rn = stats.get("report_normal", False)
        if rn:
            normal_count += 1
        sample_entry = {"idx": meta.get("idx"), "report_findings": findings,
                        "report_normal": rn}
        per_sample.append(sample_entry)
        for d in DISEASES:
            state = findings.get(d, {}).get("state", "unmentioned")
            state_count[d][state] += 1
    return {
        "total_samples": len(samples),
        "description": "报告文本NER: 正则匹配6种疾病关键词, 30字符窗口否定/不确定检测, "
                       "三态标注(positive/negative/uncertain/unmentioned)",
        "report_normal_count": normal_count,
        "state_distribution_by_disease": {d: dict(c) for d, c in state_count.items()},
        "per_sample": per_sample,
    }


def build_conflict_report(samples):
    """冲突检测报告."""
    per_sample = []
    conflict_by_type = Counter()
    conflict_by_severity = Counter()
    total_conflicts = 0
    conflict_samples = 0
    for s in samples:
        stats = s.get(Fields.stats, {})
        meta = s.get("meta", {})
        conflicts = stats.get("conflicts", [])
        n = len(conflicts)
        total_conflicts += n
        if n > 0:
            conflict_samples += 1
        for c in conflicts:
            conflict_by_type[c["type"]] += 1
            conflict_by_severity[c["severity"]] += 1
        per_sample.append({
            "idx": meta.get("idx"),
            "conflict_count": n,
            "conflicts": conflicts,
        })
    return {
        "total_samples": len(samples),
        "total_conflicts": total_conflicts,
        "conflict_samples": conflict_samples,
        "conflict_by_type": dict(conflict_by_type),
        "conflict_by_severity": dict(conflict_by_severity),
        "description": "图片-报告三态冲突矩阵: 图片↔报告否定 / 图片↔报告不确定 / "
                       "图片↔报告结论 / 报告↔图片 / 报告内部",
        "per_sample": per_sample,
    }


def main():
    print("=" * 72)
    print("Data-Juicer NLMCXR 胸片报告冲突检测 — 算子测试")
    print("=" * 72)
    samples = load_samples()
    print(f"加载 {len(samples)} 条样本 (来自 {JSONL})")

    print("\n运行4个算子 (nlmcxr_data_mapper -> xray_image_analysis_filter "
          "-> report_ner_filter -> image_report_conflict_filter):")
    out = run_pipeline(samples)

    # ---- 写报告文件 ----
    print("\n" + "=" * 72)
    print("写入报告文件到 output_dj/")
    print("=" * 72)

    xray_report = build_xray_report(out)
    write_report("xray_analysis_stats.json", xray_report)
    print("  -> xray_analysis_stats.json")
    print(f"     阳性统计: {xray_report['positive_count_by_disease']}")

    ner_report = build_ner_report(out)
    write_report("report_ner_stats.json", ner_report)
    print("  -> report_ner_stats.json")
    print(f"     报告称正常: {ner_report['report_normal_count']}/{len(out)}")

    conflict_report = build_conflict_report(out)
    write_report("conflict_stats.json", conflict_report)
    print("  -> conflict_stats.json")
    print(f"     冲突样本: {conflict_report['conflict_samples']}/{len(out)}, "
          f"冲突总数: {conflict_report['total_conflicts']}")
    print(f"     冲突分类: {conflict_report['conflict_by_type']}")
    print(f"     严重度: {conflict_report['conflict_by_severity']}")

    global_report = {
        "total_samples": len(out),
        "pipeline": ["nlmcxr_data_mapper", "xray_image_analysis_filter",
                     "report_ner_filter", "image_report_conflict_filter"],
        "xray_positive_by_disease": xray_report["positive_count_by_disease"],
        "report_normal_count": ner_report["report_normal_count"],
        "ner_state_distribution": ner_report["state_distribution_by_disease"],
        "conflict_summary": {
            "total_conflicts": conflict_report["total_conflicts"],
            "conflict_samples": conflict_report["conflict_samples"],
            "by_type": conflict_report["conflict_by_type"],
            "by_severity": conflict_report["conflict_by_severity"],
        },
        "model_info": {
            "name": "TorchXRayVision DenseNet121",
            "weights": "densenet121-res224-mimic_ch",
            "device": "cpu",
            "positive_threshold": 0.5,
            "diseases": DISEASES,
        },
    }
    write_report("global_report.json", global_report)
    print("  -> global_report.json")

    print("\n" + "=" * 72)
    print("测试完成!")
    print(f"  样本数: {len(out)}")
    print(f"  冲突样本: {conflict_report['conflict_samples']}")
    print(f"  冲突总数: {conflict_report['total_conflicts']}")
    print(f"  报告目录: {OUT_DIR}")
    print("=" * 72)


if __name__ == "__main__":
    main()
