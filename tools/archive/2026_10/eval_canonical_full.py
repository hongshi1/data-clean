r"""全量算法评测: canonical pair dataset(中间形态) → 所有算法.

采样: SRS test全量(锚点48+变异327+pair变异58) + 外部分层300/源
算法: mDeBERTa/Erlangshen/v6/v8/v9/v10/词法/BGE (全本地)
用法: python tools/eval_canonical_full.py
"""
from __future__ import annotations

import gc
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

PD = BASE / "data/gjb_438c/pair_dataset_canonical"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def prf(ys, ps):
    tp = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p == "inconsistent")
    fp = sum(1 for y, p in zip(ys, ps) if y != "inconsistent" and p == "inconsistent")
    fn = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p != "inconsistent")
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"P": round(prec, 3), "R": round(rec, 3), "F1": round(f1, 3), "flag": f"{tp+fp}/{len(ys)}"}


def load_batch() -> list[dict]:
    test = [json.loads(line) for line in open(PD / "test.jsonl", encoding="utf-8")]
    srs = [x for x in test if x["source"].startswith("srs")]
    ext = [x for x in test if not x["source"].startswith("srs")]
    by = defaultdict(list)
    for x in ext:
        by[x["source"]].append(x)
    sampled = list(srs)
    for src, lst in by.items():
        random.Random(42).shuffle(lst)
        sampled.extend(lst[:300])
    random.Random(42).shuffle(sampled)
    return sampled


def eval_nli(mdir, data, batch=16):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
    model.to(DEVICE).eval()
    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    cid = next((k for k, v in id2label.items() if "contra" in v), 0)
    out = []
    with torch.no_grad():
        for i in range(0, len(data), batch):
            b = data[i:i + batch]
            enc = tok([x["pair"]["premise"] for x in b], [x["pair"]["hypothesis"] for x in b],
                      padding=True, truncation=True, max_length=128, return_tensors="pt").to(DEVICE)
            logits = model(**enc).logits
            out.extend(torch.softmax(logits.float(), dim=-1)[:, cid].cpu().tolist())
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return out


def eval_lexical(data):
    from algorithms.blackboard.lexical_kit import text_match_score

    def _ent(t):
        m = re.search(r"[「]([^「」]{2,20})[」]", str(t))
        return m.group(1) if m else str(t)[:30]

    out = []
    for x in data:
        pe, he = _ent(x["pair"]["premise"]), _ent(x["pair"]["hypothesis"])
        s = text_match_score(pe, he) if pe and he else 0.5
        out.append("inconsistent" if s < 0.5 else "consistent")
    return out


def eval_bge(data, th=0.75):
    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal()
    texts = [x["pair"]["premise"] for x in data] + [x["pair"]["hypothesis"] for x in data]
    vecs = bge.embed(texts)
    out = []
    for x in data:
        vp = np.asarray(vecs[x["pair"]["premise"]], dtype=np.float32)
        vh = np.asarray(vecs[x["pair"]["hypothesis"]], dtype=np.float32)
        sim = float(np.dot(vp, vh) / (np.linalg.norm(vp) * np.linalg.norm(vh) + 1e-9))
        out.append("inconsistent" if sim < th else "consistent")
    return out


def main() -> None:
    data = load_batch()
    ys = [x["label"] for x in data]
    srcs = Counter(x["source"] for x in data)
    print(f"canonical评测批次: {len(data)}条 {dict(srcs)}")

    models = [
        ("mDeBERTa", "models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7", 0.5),
        ("Erlangshen", "models/nli/Erlangshen-Roberta-330M-NLI", 0.5),
        ("QLoRA-v6", "models/nli/erlangshen-330m-qlora-v6", 0.5),
        ("QLoRA-v8", "models/nli/erlangshen-330m-qlora-v8-cct", 0.5),
        ("QLoRA-v9-1.5B", "models/nli/qwen1.5b-qlora-v9-cct", 0.5),
        ("QLoRA-v10-pu", "models/nli/erlangshen-330m-qlora-v10-pu", 0.5),
    ]
    rows = []
    by_src = defaultdict(list)
    for tag, mdir, th in models:
        probs = eval_nli(mdir, data)
        preds = ["inconsistent" if p >= th else "consistent" for p in probs]
        m = prf(ys, preds)
        rows.append({"method": tag, "scope": "ALL", **m})
        print(f"  {tag:<14} ALL: F1={m['F1']} P={m['P']} R={m['R']}")
        for i, (x, p) in enumerate(zip(data, preds)):
            by_src[(tag, x["source"])].append((ys[i], p))
    for tag, fn in [("词法", None), ("BGE", None)]:
        preds = eval_lexical(data) if tag == "词法" else eval_bge(data)
        m = prf(ys, preds)
        rows.append({"method": tag, "scope": "ALL", **m})
        print(f"  {tag:<14} ALL: F1={m['F1']}")
        for i, (x, p) in enumerate(zip(data, preds)):
            by_src[(tag, x["source"])].append((ys[i], p))

    print(f"\n{'方法':<14} " + "".join(f"{s[:12]:>14}" for s in sorted(srcs)))
    print("-" * 100)
    matrix = {}
    for tag, _d, _t in models + [("词法", None, None), ("BGE", None, None)]:
        cells = []
        for s in sorted(srcs):
            pairs = by_src.get((tag, s), [])
            m = prf([y for y, _ in pairs], [p for _, p in pairs]) if pairs else None
            cells.append(f"{m['F1']:>14.3f}" if m else f"{'-':>14}")
            if m:
                matrix.setdefault(tag, {})[s] = m
        print(f"{tag:<14} " + "".join(cells))

    from run_utils import open_run
    run = open_run("canonical_full_eval", {"batch": len(data), "sources": dict(srcs)})
    run.save_result({"rows": rows, "matrix": matrix})
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
