"""SRS-Verifier主评测: canonical SRS测试集(我们场景) + 消融(去注意力/去分派/纯NLI)."""
from __future__ import annotations

import gc
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

import torch

PD = BASE / "data/gjb_438c/pair_dataset_canonical"


def prf(ys, ps):
    tp = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p == "inconsistent")
    fp = sum(1 for y, p in zip(ys, ps) if y != "inconsistent" and p == "inconsistent")
    fn = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p != "inconsistent")
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    return {"P": round(prec, 3), "R": round(rec, 3),
            "F1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0}


def eval_pure_nli(mdir, items):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    cid = next((k for k, v in id2label.items() if "contra" in v), 0)
    preds = []
    with torch.no_grad():
        for i in range(0, len(items), 16):
            b = items[i:i + 16]
            enc = tok([x["pair"]["premise"] for x in b], [x["pair"]["hypothesis"] for x in b],
                      padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
            preds.extend(torch.softmax(model(**enc).logits.float(), dim=-1)[:, cid].cpu().tolist())
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return ["inconsistent" if p >= 0.5 else "consistent" for p in preds]


def main() -> None:
    test = [json.loads(line) for line in open(PD / "test.jsonl", encoding="utf-8")]
    srs = [x for x in test if x["source"].startswith("srs")]
    ys = [x["label"] for x in srs]
    print(f"SRS测试集(我们场景): {len(srs)}条 {dict(Counter(x['source'] for x in srs))}")
    print(f"标签: {dict(Counter(ys))}\n")

    from algorithms.consistency_check.srs_verifier import SrsVerifier

    # ── 完整SRS-Verifier ──
    ver = SrsVerifier()
    results = []
    for x in srs:
        r = ver.verify(x["pair"]["premise"], x["pair"]["hypothesis"],
                       x.get("context"), x["angle"]["type"], x["angle"]["scene"])
        results.append(r)
    preds = [r["verdict"] for r in results]
    m_full = prf(ys, preds)
    techs = Counter(r["technique"] for r in results)
    print(f"SRS-Verifier(完整): F1={m_full['F1']} P={m_full['P']} R={m_full['R']}")
    print(f"  求解器使用: {dict(techs)}")

    # ── 消融1: 去确定性分派(全NLI+门控) ──
    ver2 = SrsVerifier()
    preds_a = []
    for x in srs:
        ctx = x.get("context") or {}
        from algorithms.consistency_check.srs_verifier import decompose_context
        units = decompose_context(ctx)
        filt = ver2.recall_and_filter(x["pair"]["premise"], units)
        att = ver2.sub_attention(x["pair"]["premise"], filt)
        r = ver2.solve_nli(x["pair"]["premise"], x["pair"]["hypothesis"], att["coverage"])
        preds_a.append(r["verdict"])
    m_abl1 = prf(ys, preds_a)
    print(f"\n消融1(去确定性分派, NLI+注意力门控): F1={m_abl1['F1']}")

    # ── 消融2: 纯NLI v8(无任何设计) ──
    preds_b = eval_pure_nli(str(BASE / "models/nli/erlangshen-330m-qlora-v8-cct"), srs)
    m_abl2 = prf(ys, preds_b)
    print(f"消融2(纯NLI v8无设计): F1={m_abl2['F1']} P={m_abl2['P']} R={m_abl2['R']}")

    # ── 消融3: 去注意力门控(分派+NLI无门控) ──
    ver3 = SrsVerifier()
    preds_c = []
    for x in srs:
        r_nli = ver3.solve_nli(x["pair"]["premise"], x["pair"]["hypothesis"], 0.0)
        dtype = x["angle"]["type"]
        solved = None
        if dtype.startswith("PARAM"):
            solved = ver3.solve_z3_param(x["pair"]["premise"], x["pair"]["hypothesis"])
        elif "MISSING" in dtype:
            ctx = x.get("context") or {}
            from algorithms.consistency_check.srs_verifier import decompose_context
            units = decompose_context(ctx)
            solved = ver3.solve_structure(x["pair"]["premise"], units, {"coverage": 0, "top": []})
        preds_c.append(solved["verdict"] if solved else r_nli["verdict"])
    m_abl3 = prf(ys, preds_c)
    print(f"消融3(去注意力门控): F1={m_abl3['F1']}")

    # 分源细目
    print("\n分源细目(SRS-Verifier):")
    by = defaultdict(list)
    for x, p in zip(srs, preds):
        by[x["source"]].append((x["label"], p))
    for s, pairs in sorted(by.items()):
        mm = prf([y for y, _ in pairs], [p for _, p in pairs])
        print(f"  {s:<20} n={len(pairs):>3} F1={mm['F1']} P={mm['P']} R={mm['R']}")

    from run_utils import open_run
    run = open_run("srs_verifier_eval", {"n": len(srs), "design": "五模块流水线"})
    run.save_result({"full": m_full, "abl_no_dispatch": m_abl1,
                     "abl_pure_nli": m_abl2, "abl_no_gate": m_abl3,
                     "solver_dist": dict(techs)})
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
