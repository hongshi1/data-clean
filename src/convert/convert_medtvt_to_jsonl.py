#!/Users/gexuancheng/Desktop/research2/data-juicer/.venv/bin/python3
"""MedTVT train.csv -> Data-Juicer JSONL 转换脚本.

读取 medical_data/medtvt/train.csv (10000行), 转为 Data-Juicer 兼容的 JSONL:
  {"text":"", "images":["cxr_path"], "meta":{"subject_id":..., "hadm_id":..., "cxr_path":..., "ecg_path":..., "labs":{itemid:val,...}, "diagnosis":{label:1/0/-1,...}}}

- 诊断标签: 1.0->1, -1.0->-1, 0.0->0, 空值->0
- 血检: 数值保留float, 空值跳过
- 输出: medical_data/medtvt/medtvt_dj.jsonl
"""
import json
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "medical_data", "medtvt", "train.csv")
OUT_PATH = os.path.join(BASE, "medical_data", "medtvt", "medtvt_dj.jsonl")

# 50项血检 itemid (来自 labs_means.json)
LAB_ITEMIDS = [
    "51221", "51265", "50912", "50971", "51222", "51301", "51249", "51279",
    "51250", "51248", "51277", "51006", "50983", "50902", "50882", "50868",
    "50931", "50960", "50893", "50970", "51237", "51274", "51275", "51146",
    "51256", "51254", "51200", "51244", "52172", "50934", "51678", "50947",
    "50861", "50878", "50813", "50863", "50885", "50820", "50862", "50802",
    "50821", "50804", "50818", "52075", "52073", "52074", "52069", "51133",
    "50910", "52135",
]

# 5个关键指标 (L2/L3冲突检测核心, 与 medical_conflict_results.json 对齐)
KEY_LAB_ITEMIDS = ["50893", "51237", "50931", "50971", "50820"]

DIAGNOSIS_LABELS = [
    "Atelectasis", "Cardiomegaly", "Edema", "Lung Opacity",
    "No Finding", "Pleural Effusion",
]


def encode_diag(val):
    """诊断标签编码: 1.0->1, -1.0->-1, 0.0->0, 空值->0."""
    if pd.isna(val):
        return 0
    f = float(val)
    if f == 1.0:
        return 1
    if f == -1.0:
        return -1
    return 0


def convert(key_labs_only=True):
    df = pd.read_csv(CSV_PATH)
    itemids = KEY_LAB_ITEMIDS if key_labs_only else LAB_ITEMIDS
    # 校验列存在
    missing = [c for c in itemids + DIAGNOSIS_LABELS if c not in df.columns]
    if missing:
        print(f"[WARN] CSV缺少列: {missing}", file=sys.stderr)

    n_total = 0
    n_skipped = 0
    with open(OUT_PATH, "w", encoding="utf-8") as fout:
        for _, row in df.iterrows():
            # 血检: 数值保留float, 空值跳过
            labs = {}
            for iid in itemids:
                if iid in row.index:
                    v = row[iid]
                    if pd.notna(v):
                        try:
                            labs[iid] = float(v)
                        except (ValueError, TypeError):
                            continue
            # 诊断
            diagnosis = {lbl: encode_diag(row.get(lbl)) for lbl in DIAGNOSIS_LABELS}

            cxr_path = row.get("cxr_path", "")
            ecg_path = row.get("ecg_path", "")
            rec = {
                "text": "",
                "images": [cxr_path] if isinstance(cxr_path, str) and cxr_path else [],
                "meta": {
                    "subject_id": int(row["subject_id"]) if pd.notna(row.get("subject_id")) else None,
                    "hadm_id": int(row["hadm_id"]) if pd.notna(row.get("hadm_id")) else None,
                    "cxr_path": cxr_path if isinstance(cxr_path, str) else "",
                    "ecg_path": ecg_path if isinstance(ecg_path, str) else "",
                    "labs": labs,
                    "diagnosis": diagnosis,
                },
            }
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_total += 1
    return n_total, n_skipped


if __name__ == "__main__":
    key_only = "--all-labs" not in sys.argv
    n, _ = convert(key_labs_only=key_only)
    mode = "5关键指标" if key_only else "全50指标"
    print(f"转换完成: {n} 条 -> {OUT_PATH} (模式: {mode})")
