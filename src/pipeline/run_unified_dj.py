#!/usr/bin/env python3
"""
统一Pipeline测试脚本
用Data-Juicer算子方式运行冲突检测
测试: NLMCXR 5条 + MedTVT 10条 + H4R 4条 = 19条
"""
import json, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "data-juicer"))

from data_juicer.utils.constant import Fields
from unified_operators import (
    UnifiedEntityExtractionMapper,
    UnifiedConflictFilter,
    UnifiedReportMapper,
)
import pandas as pd

OUT_DIR = os.path.join(SCRIPT_DIR, "output_unified")
os.makedirs(OUT_DIR, exist_ok=True)

def load_nlmcxr_samples(n=5):
    """NLMCXR → JSONL格式"""
    df = pd.read_parquet(os.path.join(SCRIPT_DIR, "nlmcxr/val.parquet"))
    samples = []
    for idx in range(min(n, len(df))):
        row = df.iloc[idx]
        img_bytes = row["image"]["bytes"]
        # 保存图片到临时文件
        img_path = os.path.join(OUT_DIR, f"nlmcxr_img_{idx}.jpg")
        from PIL import Image
        import io
        Image.open(io.BytesIO(img_bytes)).save(img_path)
        
        sample = {
            "text": str(row["text"]),
            "images": [img_path],
            "meta": {"data_type": "radiology", "idx": idx}
        }
        sample[Fields.stats] = {}
        samples.append(sample)
    return samples

def load_medtvt_samples(n=10):
    """MedTVT → JSONL格式"""
    df = pd.read_csv(os.path.join(SCRIPT_DIR, "medical_data/medtvt/train.csv"))
    samples = []
    # 选5个冲突+5个正常
    conflict_idx, normal_idx = [], []
    for i, row in df.iterrows():
        nf = pd.to_numeric(row.get("No Finding"), errors="coerce")
        if nf != 1.0: continue
        lactate = pd.to_numeric(row.get("50893"), errors="coerce")
        if pd.notna(lactate) and lactate > 5.0 and len(conflict_idx) < 5:
            conflict_idx.append(i)
        elif pd.notna(lactate) and lactate <= 2.0 and len(normal_idx) < 5:
            normal_idx.append(i)
        if len(conflict_idx) >= 5 and len(normal_idx) >= 5: break
    
    for row_idx in conflict_idx + normal_idx:
        row = df.iloc[row_idx]
        labs = {}
        for itemid in ["50893","51237","50931","50971","50820"]:
            v = row.get(itemid)
            if pd.notna(v) and v != "":
                try: labs[itemid] = float(v)
                except: pass
        diagnosis = []
        for col in ["Atelectasis","Cardiomegaly","Edema","Lung Opacity","No Finding","Pleural Effusion"]:
            v = row.get(col)
            if v == 1.0: diagnosis.append(col)
            elif v == -1.0: diagnosis.append(f"{col}(不确定)")
        
        sample = {
            "text": "",
            "images": [],
            "meta": {"data_type": "medical", "row_idx": int(row_idx),
                     "subject_id": int(row["subject_id"]),
                     "labs": labs, "diagnosis": diagnosis}
        }
        sample[Fields.stats] = {}
        samples.append(sample)
    return samples

def load_h4r_samples():
    """H4R → JSONL格式"""
    samples = []
    jsonl_path = os.path.join(SCRIPT_DIR, "h4r_welding.jsonl")
    with open(jsonl_path) as f:
        for idx, line in enumerate(f):
            d = json.loads(line)
            sample = {
                "text": d.get("text", ""),
                "images": d.get("images", []),
                "meta": {"data_type": "welding", "idx": idx,
                         "csv_path": d.get("meta", {}).get("csv_path", ""),
                         "defect_label": d.get("meta", {}).get("defect_label", "")}
            }
            sample[Fields.stats] = {}
            samples.append(sample)
    return samples

def main():
    print("=" * 60)
    print("统一Pipeline测试 (Data-Juicer算子)")
    print("=" * 60)
    
    # 加载数据
    nlmcxr = load_nlmcxr_samples(5)
    medtvt = load_medtvt_samples(10)
    h4r = load_h4r_samples()
    all_samples = nlmcxr + medtvt + h4r
    print(f"加载: NLMCXR={len(nlmcxr)} + MedTVT={len(medtvt)} + H4R={len(h4r)} = {len(all_samples)}条\n")
    
    # 初始化算子
    extractor = UnifiedEntityExtractionMapper()
    extractor._name = "unified_entity_extraction_mapper"
    conflict_detector = UnifiedConflictFilter()
    conflict_detector._name = "unified_conflict_filter"
    reporter = UnifiedReportMapper()
    reporter._name = "unified_report_mapper"
    
    # 运行Pipeline
    results = []
    for i, sample in enumerate(all_samples):
        dt = sample["meta"]["data_type"]
        
        # Phase 1: 信息抽取
        sample = extractor.process_single(sample)
        
        # Phase 2: 冲突检测
        sample = conflict_detector.compute_stats_single(sample)
        _ = conflict_detector.process_single(sample)
        
        # Phase 3: 报告生成
        sample = reporter.process_single(sample)
        
        report = sample["meta"]["conflict_report"]
        results.append(report)
        
        tag = f"⚠{report['conflict_count']}冲突" if report["has_conflict"] else "✓一致" if report["has_conflict"] is False else "?未知"
        print(f"  [{dt:10s}] 样本{i+1} {tag}: {report['explanation'][:60]}")
        for c in report["conflicts"]:
            print(f"    [{c.get('severity','')}] {c.get('type','')}: {c.get('detail','')[:60]}")
    
    # 汇总
    n_conflict = sum(1 for r in results if r["has_conflict"])
    n_normal = sum(1 for r in results if r["has_conflict"] is False)
    print(f"\n{'='*60}")
    print(f"汇总: {len(results)}条 | 冲突={n_conflict} | 一致={n_normal} | 未知={len(results)-n_conflict-n_normal}")
    
    by_type = {}
    for r in results:
        dt = r["data_type"]
        if dt not in by_type:
            by_type[dt] = {"total": 0, "conflict": 0, "normal": 0}
        by_type[dt]["total"] += 1
        if r["has_conflict"]:
            by_type[dt]["conflict"] += 1
        elif r["has_conflict"] is False:
            by_type[dt]["normal"] += 1
    
    for dt, s in by_type.items():
        print(f"  {dt}: {s['conflict']}/{s['total']}冲突, {s['normal']}/{s['total']}一致")
    
    # 保存
    out_path = os.path.join(OUT_DIR, "unified_dj_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {out_path}")

if __name__ == "__main__":
    main()
