#!/usr/bin/env python3
"""
统一Pipeline启动脚本 (v3, 调研对齐版)

用法:
  cd /Users/gexuancheng/Desktop/research2/data_clean
  data-juicer/.venv/bin/python3 run_pipeline.py

  # 只跑NLMCXR
  data-juicer/.venv/bin/python3 run_pipeline.py --dataset nlmcxr --n 20

  # 只跑MedTVT
  data-juicer/.venv/bin/python3 run_pipeline.py --dataset medtvt --n 20

  # 只跑H4R
  data-juicer/.venv/bin/python3 run_pipeline.py --dataset h4r

  # 跑全部
  data-juicer/.venv/bin/python3 run_pipeline.py --all
"""
import json, os, sys, argparse, io
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "data-juicer"))

from data_juicer.utils.constant import Fields
from unified_operators import InfoExtractionMapper, ConflictDetectionFilter, ConflictReportMapper
import pandas as pd

OUT_DIR = os.path.join(SCRIPT_DIR, "output_unified")
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# 数据加载
# ============================================================
def load_nlmcxr(n=20):
    """NLMCXR: X光片+报告 → JSONL"""
    df = pd.read_parquet(os.path.join(SCRIPT_DIR, "nlmcxr/val.parquet"))
    samples = []
    for idx in range(min(n, len(df))):
        row = df.iloc[idx]
        img_bytes = row["image"]["bytes"]
        img_path = os.path.join(OUT_DIR, f"nlmcxr_img_{idx}.jpg")
        from PIL import Image
        Image.open(io.BytesIO(img_bytes)).save(img_path)
        sample = {"text": str(row["text"]), "images": [img_path],
                  "meta": {"data_type": "radiology", "idx": idx}}
        sample[Fields.stats] = {}
        samples.append(sample)
    return samples

def load_medtvt(n=20):
    """MedTVT: 血检+标签 → JSONL"""
    df = pd.read_csv(os.path.join(SCRIPT_DIR, "medical_data/medtvt/train.csv"))
    samples = []
    conflict_n, normal_n = 0, 0
    for i, row in df.iterrows():
        nf = pd.to_numeric(row.get("No Finding"), errors="coerce")
        if nf != 1.0: continue
        labs = {}
        for itemid in ["50893","51237","50931","50971","50820"]:
            v = row.get(itemid)
            if pd.notna(v) and v != "":
                try: labs[itemid] = float(v)
                except: pass
        has_abnormal = False
        for itemid in labs:
            if itemid == "50893" and labs[itemid] > 5.0: has_abnormal = True
            if itemid == "51237" and labs[itemid] > 2.0: has_abnormal = True
            if itemid == "50931" and labs[itemid] > 300: has_abnormal = True
            if itemid == "50971" and labs[itemid] > 6.0: has_abnormal = True
            if itemid == "50820" and labs[itemid] < 7.20: has_abnormal = True
        if has_abnormal and conflict_n < n//2:
            diagnosis = [col for col in ["No Finding","Atelectasis","Cardiomegaly","Edema","Lung Opacity","Pleural Effusion"] if row.get(col) == 1.0]
            sample = {"text": "", "images": [],
                      "meta": {"data_type": "medical", "row_idx": int(i),
                               "subject_id": int(row["subject_id"]),
                               "labs": labs, "diagnosis": diagnosis, "expected_conflict": True}}
            sample[Fields.stats] = {}
            samples.append(sample)
            conflict_n += 1
        elif not has_abnormal and normal_n < n//2:
            diagnosis = [col for col in ["No Finding","Atelectasis","Cardiomegaly","Edema","Lung Opacity","Pleural Effusion"] if row.get(col) == 1.0]
            sample = {"text": "", "images": [],
                      "meta": {"data_type": "medical", "row_idx": int(i),
                               "subject_id": int(row["subject_id"]),
                               "labs": labs, "diagnosis": diagnosis, "expected_conflict": False}}
            sample[Fields.stats] = {}
            samples.append(sample)
            normal_n += 1
        if conflict_n >= n//2 and normal_n >= n//2: break
    return samples

def load_h4r():
    """H4R: 时序+文本+标签 → JSONL"""
    samples = []
    with open(os.path.join(SCRIPT_DIR, "h4r_welding.jsonl")) as f:
        for idx, line in enumerate(f):
            d = json.loads(line)
            sample = {"text": d.get("text",""), "images": d.get("images",[]),
                      "meta": {"data_type": "welding", "idx": idx,
                               "csv_path": d.get("meta",{}).get("csv_path",""),
                               "defect_label": d.get("meta",{}).get("defect_label","")}}
            sample[Fields.stats] = {}
            samples.append(sample)
    return samples

# ============================================================
# 运行Pipeline
# ============================================================
def run_pipeline(samples, label=""):
    """运行3个算子: info_extraction_mapper → conflict_detection_filter → conflict_report_mapper"""
    # 初始化算子
    extractor = InfoExtractionMapper()
    extractor._name = "info_extraction_mapper"
    detector = ConflictDetectionFilter()
    detector._name = "conflict_detection_filter"
    reporter = ConflictReportMapper()
    reporter._name = "conflict_report_mapper"

    results = []
    for i, sample in enumerate(samples):
        # Phase 1
        sample = extractor.process_single(sample)
        # Phase 2
        sample = detector.compute_stats_single(sample)
        _ = detector.process_single(sample)
        # Phase 3+4
        sample = reporter.process_single(sample)

        report = sample["meta"]["conflict_report"]
        results.append(report)

        tag = f"⚠{report['conflict_count']}冲突" if report["has_conflict"] else "✓一致"
        conf = report["confidence"]["overall"]
        print(f"  [{label}] 样本{i+1} {tag} [置信度:{conf}] {report.get('explanation','')[:50]}")

    return results

# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="统一多模态冲突检测Pipeline")
    parser.add_argument("--dataset", choices=["nlmcxr","medtvt","h4r"], help="只跑指定数据集")
    parser.add_argument("--n", type=int, default=20, help="样本数(默认20)")
    parser.add_argument("--all", action="store_true", help="跑全部数据集")
    args = parser.parse_args()

    print("=" * 60)
    print("统一多模态冲突检测Pipeline v3 (调研对齐版)")
    print("Phase 1: scispaCy+TorchXRayVision+LOINC+传感器 (信息抽取)")
    print("Phase 2: VDC三段式+LLM直判 (冲突检测, 不用手写规则)")
    print("Phase 3: NER解释 (实体定位冲突)")
    print("Phase 4: 置信度量化 (图片概率+方法佐证+严重度)")
    print("=" * 60)

    all_results = []

    if args.all or args.dataset == "nlmcxr":
        print(f"\n--- NLMCXR (图片+报告) ---")
        samples = load_nlmcxr(args.n)
        results = run_pipeline(samples, "NLMCXR")
        all_results.extend(results)

    if args.all or args.dataset == "medtvt":
        print(f"\n--- MedTVT (血检+标签) ---")
        samples = load_medtvt(args.n)
        results = run_pipeline(samples, "MedTVT")
        # 评估
        tp = sum(1 for r in results if r["has_conflict"] and r.get("expected_conflict", True))
        fp = sum(1 for r in results if r["has_conflict"] and not r.get("expected_conflict", True))
        tn = sum(1 for r in results if not r["has_conflict"] and not r.get("expected_conflict", True))
        fn = sum(1 for r in results if not r["has_conflict"] and r.get("expected_conflict", True))
        if tp+tn > 0:
            print(f"  TP={tp} FN={fn} TN={tn} FP={fp} 准确率={(tp+tn)/len(results)*100:.0f}%")
        all_results.extend(results)

    if args.all or args.dataset == "h4r":
        print(f"\n--- H4R (时序+文本+标签) ---")
        samples = load_h4r()
        results = run_pipeline(samples, "H4R")
        all_results.extend(results)

    # 汇总
    print(f"\n{'='*60}")
    print(f"汇总: {len(all_results)}条")
    by_ds = defaultdict(lambda: {"total":0, "conflict":0})
    by_method = defaultdict(int)
    for r in all_results:
        ds = r["data_type"]
        by_ds[ds]["total"] += 1
        if r["has_conflict"]: by_ds[ds]["conflict"] += 1
        for c in r.get("conflicts", []):
            by_method[c.get("method","unknown")] += 1
    for ds, s in by_ds.items():
        print(f"  {ds}: {s['conflict']}/{s['total']}有冲突")
    print(f"  检测方法: {dict(by_method)}")

    out_path = os.path.join(OUT_DIR, "pipeline_report.json")
    json.dump(all_results, open(out_path, "w"), ensure_ascii=False, indent=2)
    print(f"\n报告: {out_path}")

if __name__ == "__main__":
    main()
