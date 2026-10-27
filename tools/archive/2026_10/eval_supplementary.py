"""补充数据集外部泛化评测: WANLI/ContractNLI/DocNLI × 主要方法.

诚实设计: 英文集上中文专用模型预期受限(这正是特化-泛化权衡的外部证据)
"""
from __future__ import annotations

import gc
import json
import random
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import torch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

OUT = BASE / "data/gjb_438c/public_nli"
NLI_MAP = {"contradiction": "inconsistent", "entailment": "consistent", "neutral": "consistent"}


def bacc_metrics(ys, ps):
    tp = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p == "inconsistent")
    tn = sum(1 for y, p in zip(ys, ps) if y == "consistent" and p == "consistent")
    n_pos = ys.count("inconsistent")
    n_neg = len(ys) - n_pos
    tpr = tp / n_pos if n_pos else 0
    tnr = tn / n_neg if n_neg else 1
    prec = tp / (tp + (len(ps) - tp)) if tp else 0
    f1 = 2 * prec * tpr / (prec + tpr) if prec + tpr else 0
    return {"bAcc": round((tpr + tnr) / 2, 3), "P": round(prec, 3), "R": round(tpr, 3),
            "TNR": round(tnr, 3), "F1": round(f1, 3)}


def load_sets(n=300):
    rng = random.Random(42)
    sets = {}
    # WANLI
    wanli = [json.loads(line) for line in open(OUT / "wanli_test.jsonl", encoding="utf-8")]
    wanli = [x for x in wanli if x["gold"] in NLI_MAP]
    rng.shuffle(wanli)
    sets["WANLI"] = [(x["premise"], x["hypothesis"], NLI_MAP[x["gold"]]) for x in wanli[:n]]
    # ContractNLI
    cnli = [json.loads(line) for line in open(OUT / "contractnli_v1.jsonl", encoding="utf-8")]
    cnli = [x for x in cnli if x["label"] in NLI_MAP]
    rng.shuffle(cnli)
    sets["ContractNLI"] = [(x["premise"], x["hypothesis"], NLI_MAP[x["label"]]) for x in cnli[:n]]
    # DocNLI
    df = pd.read_parquet(OUT / "docnli_test_0.parquet")
    col_p = "premise" if "premise" in df.columns else df.columns[1]
    col_h = "hypothesis" if "hypothesis" in df.columns else df.columns[2]
    col_l = "label" if "label" in df.columns else df.columns[-1]
    lab_map = {"entailment": "consistent", "contradiction": "inconsistent", "neutral": "consistent"}
    rows = []
    for _, r in df.iterrows():
        raw = str(r[col_l]).lower()
        if raw in lab_map:
            rows.append((str(r[col_p]), str(r[col_h]), lab_map[raw]))
    rng.shuffle(rows)
    sets["DocNLI"] = rows[:n]
    return sets


def eval_cls(mdir, items, batch=16):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
    model.to("cuda" if torch.cuda.is_available() else "cpu").eval()
    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    cid = next((k for k, v in id2label.items() if "contra" in v), 0)
    device = next(model.parameters()).device
    preds = []
    with torch.no_grad():
        for i in range(0, len(items), batch):
            b = items[i:i + batch]
            enc = tok([x[0] for x in b], [x[1] for x in b], padding=True, truncation=True,
                      max_length=256, return_tensors="pt").to(device)
            logits = model(**enc).logits
            preds.extend(["inconsistent" if bool(j) else "consistent"
                          for j in (logits[:, cid] >= 0.5).cpu().tolist()])
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return preds


def main() -> None:
    sets = load_sets(300)
    for k, v in sets.items():
        print(f"{k}: {len(v)}条 {dict(Counter(x[2] for x in v))}")

    methods = [
        ("mDeBERTa(多语言)", "models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"),
        ("roberta-FT(中文专用)", "models/nli/roberta-ft-baseline"),
        ("QLoRA-v8(中文专用)", "models/nli/erlangshen-330m-qlora-v8-cct"),
        ("QLoRA-v9(双语1.5B)", "models/nli/qwen1.5b-qlora-v9-cct"),
    ]
    results = {}
    print(f"\n{'方法':<20} {'WANLI bAcc':>10} {'ContrNLI bAcc':>13} {'DocNLI bAcc':>11}")
    print("-" * 60)
    for tag, mdir in methods:
        cells = []
        for sname, items in sets.items():
            ys = [x[2] for x in items]
            preds = eval_cls(mdir, items)
            m = bacc_metrics(ys, preds)
            results[f"{tag}|{sname}"] = m
            cells.append(f"{m['bAcc']:>10.3f}" if sname == "WANLI"
                         else f"{m['bAcc']:>13.3f}" if sname == "ContractNLI"
                         else f"{m['bAcc']:>11.3f}")
        print(f"{tag:<20} " + "".join(cells))

    from run_utils import open_run
    run = open_run("supplementary_external_eval", {"sets": ["WANLI", "ContractNLI", "DocNLI"], "n": 300})
    run.save_result(results)
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
