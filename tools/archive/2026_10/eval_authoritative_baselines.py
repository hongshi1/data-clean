r"""权威baseline评测: VitaminC / MiniCheck / Longformer / SummaC-ZS(配方移植).

来源:
  VitaminC  — Schuster et al., NAACL 2021 (对比事实核验)
  MiniCheck — Tang et al., EMNLP 2024 (SOTA grounding checker)
  Longformer — Beltagy et al., ACL 2020 (长文本NLI)
  SummaC-ZS — Laban et al., 2022 (不一致性检测标杆, 配方=句子级NLI逐对+聚合)

注意: 英文checkpoint对中文零样本迁移弱 — 先直接测(附录对照), 再移植配方到中文骨干
"""
from __future__ import annotations

import gc
import json
import sys
from pathlib import Path

import torch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

MODELS = {
    "VitaminC(NAACL'21)": str(BASE / "models/nli/vitaminc-albert"),
    "MiniCheck(EMNLP'24)": str(BASE / "models/nli/minicheck-roberta"),
    "Longformer(ACL'20)": str(BASE / "models/nli/longformer-base"),
}


def metrics(ys, ps):
    tp = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p == "inconsistent")
    tn = sum(1 for y, p in zip(ys, ps) if y == "consistent" and p == "consistent")
    n_pos = ys.count("inconsistent")
    n_neg = len(ys) - n_pos
    tpr = tp / n_pos if n_pos else 0
    tnr = tn / n_neg if n_neg else 1
    return {"bAcc": round((tpr + tnr) / 2, 3), "TPR": round(tpr, 3), "TNR": round(tnr, 3)}


def eval_nli(mdir, items, batch=16, max_len=512):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    cid = next((k for k, v in id2label.items() if "contra" in v or "refut" in v
                or "inconsistent" in v or "1" == str(k)), 1)
    preds = []
    with torch.no_grad():
        for i in range(0, len(items), batch):
            b = items[i:i + batch]
            enc = tok([x["premise"] for x in b], [x["hypothesis"] for x in b],
                      padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(device)
            logits = model(**enc).logits
            # 取矛盾/不一致类的概率
            probs = torch.softmax(logits.float(), dim=-1)
            cid_local = min(cid, probs.shape[1] - 1)
            preds.extend(bool(p) for p in (probs[:, cid_local] >= 0.5).cpu().tolist())
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return ["inconsistent" if p else "consistent" for p in preds]


def main() -> None:
    # 真实金标
    clean = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md = (json.loads((BASE / "data/gjb_438c/human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
          + json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8")))
    sets = {"clean130": clean, "md166": md}

    print("═ 权威Baseline评测(真实金标, bAcc) ═\n")
    results = {}
    for tag, mdir in MODELS.items():
        if not Path(mdir, "config.json").exists():
            print(f"跳过: {tag} (模型不存在)")
            continue
        for sname, items in sets.items():
            ys = [x["label"] if isinstance(x.get("label"), str) else
                  ("inconsistent" if x["label"] == 1 else "consistent") for x in items]
            try:
                preds = eval_nli(mdir, items)
                m = metrics(ys, preds)
                results[f"{tag}|{sname}"] = m
                print(f"  {tag:<24} @ {sname}: bAcc={m['bAcc']} TPR={m['TPR']} TNR={m['TNR']}")
            except Exception as e:
                print(f"  {tag} @ {sname}: 失败 {type(e).__name__}: {str(e)[:60]}")

    # ── SummaC-ZS配方(中文移植): 用我们的v12模型做句子级NLI+聚合 ──
    # SummaC-ZS的核心: premise按句子拆分→每句与hypothesis做NLI→取最大矛盾分数
    print("\nSummaC-ZS配方(中文移植, v12骨干):")
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import re as _re
    mdir = str(BASE / "models/nli/roberta-v12-anchor")
    tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    for sname, items in sets.items():
        ys = [x["label"] if isinstance(x.get("label"), str) else
              ("inconsistent" if x["label"] == 1 else "consistent") for x in items]
        preds = []
        with torch.no_grad():
            for x in items:
                # SummaC-ZS: premise按句拆分
                sentences = [s.strip() for s in _re.split(r"[。；;]", x["premise"]) if s.strip()]
                if not sentences:
                    sentences = [x["premise"]]
                max_contra = 0.0
                for sent in sentences[:10]:  # 最多10句
                    enc = tok(sent, x["hypothesis"], padding=True, truncation=True,
                              max_length=128, return_tensors="pt").to(device)
                    logits = model(**enc).logits
                    probs = torch.softmax(logits.float(), dim=-1)
                    max_contra = max(max_contra, float(probs[0][1]))
                preds.append("inconsistent" if max_contra >= 0.5 else "consistent")
        m = metrics(ys, preds)
        results[f"SummaC-ZS配方(中文)|{sname}"] = m
        print(f"  {'SummaC-ZS(中文v12)':<24} @ {sname}: bAcc={m['bAcc']} TPR={m['TPR']} TNR={m['TNR']}")

    # ── 对照: v12直接(无聚合) ──
    print("\n对照: v12直接判定(无SummaC聚合):")
    for sname, items in sets.items():
        ys = [x["label"] if isinstance(x.get("label"), str) else
              ("inconsistent" if x["label"] == 1 else "consistent") for x in items]
        preds = []
        with torch.no_grad():
            for x in items:
                enc = tok(x["premise"], x["hypothesis"], padding=True, truncation=True,
                          max_length=128, return_tensors="pt").to(device)
                logits = model(**enc).logits
                preds.append("inconsistent" if int(logits.argmax()) == 1 else "consistent")
        m = metrics(ys, preds)
        results[f"v12直接|{sname}"] = m
        print(f"  {'v12直接':<24} @ {sname}: bAcc={m['bAcc']}")

    del model
    gc.collect()
    torch.cuda.empty_cache()

    json.dump(results, open(BASE / "data/gjb_438c/runs/authoritative_baselines.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nsaved → authoritative_baselines.json")


if __name__ == "__main__":
    main()
