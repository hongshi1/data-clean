r"""v19b实验: 源级切分协议重训(修复gate源泄漏后的真实κ_D泛化).

与v19的区别:
  - 训练: anchor + synth_s1_split.train_sample(源级90%池采样, 1413条)
  - gate: synth_s1_split.gate(71个独立源, 543条, 源100%未见)
  - 若gate仍高 → κ_D学习真实成立; 若骤降 → v19的0.991是记忆源值
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")


def pure_nli_eval(model_dir: str, pairs: list[dict]) -> dict:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True).to(device).eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(pairs), 32):
            batch = pairs[i:i + 32]
            enc = tok([p["premise"] for p in batch], [p["hypothesis"] for p in batch],
                      padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(device)
            probs = torch.softmax(model(**enc).logits.float(), dim=-1)[:, 1]
            preds.extend("inconsistent" if v >= 0.5 else "consistent" for v in probs.tolist())
    golds = [p["label"] for p in pairs]
    acc = sum(1 for a, b in zip(preds, golds) if a == b) / len(pairs)
    by_t = defaultdict(lambda: [0, 0])
    for p, pr in zip(pairs, preds, strict=True):
        by_t[p["type"]][0] += (pr == p["label"])
        by_t[p["type"]][1] += 1
    return {"acc": round(acc, 3),
            "per_type": {t: round(v[0] / v[1], 3) for t, v in sorted(by_t.items())}}


def main() -> None:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    split = json.loads((BASE / "data/gjb_438c/synth_s1_split.json").read_text(encoding="utf-8"))
    train_synth = split["train_sample"]
    gate = split["gate"]
    print(f"协议: 训练synth{len(train_synth)}条(源级池) + gate{len(gate)}条(71独立源)")

    # anchor(v12同款过滤)
    PD = BASE / "data/gjb_438c/pair_dataset_canonical"
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]
    anchor = [x for x in train if x["source"] == "srs_anchor"
              and "evidence_refuted" not in x.get("quality", {}).get("flags", [])
              and not str(x.get("context", {}).get("doc", "")).startswith("02")]
    import random
    rng = random.Random(42)
    inc = [x for x in anchor if x["label"] == "inconsistent"]
    con = [x for x in anchor if x["label"] == "consistent"]
    rng.shuffle(con)
    con_up = (con * 6)[:len(inc) // 2]
    mix = inc + con + con_up
    for p in train_synth:
        mix.append({"pair": {"premise": p["premise"], "hypothesis": p["hypothesis"]},
                    "label": p["label"], "type": p["type"]})
    rng.shuffle(mix)
    print(f"混合训练集: {len(mix)}条(anchor{len(inc) + len(con) + len(con_up)}+synth{len(train_synth)})")

    # 训练(与v12/v19同款超参)
    MODEL_DIR = str(BASE / "models/nli/chinese-roberta-wwm-ext")
    OUT = BASE / "models/nli/roberta-v19b-srcsplit"
    tok = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    torch.manual_seed(42)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR, local_files_only=True, num_labels=2,
        id2label={0: "consistent", 1: "inconsistent"},
        label2id={"consistent": 0, "inconsistent": 1})
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=5, eta_min=1e-6)
    t0 = time.time()
    model.train()
    for ep in range(5):
        tot, nb = 0.0, 0
        for i in range(0, len(mix), 16):
            batch = mix[i:i + 16]
            enc = tok([x["pair"]["premise"] for x in batch],
                      [x["pair"]["hypothesis"] for x in batch],
                      padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(device)
            labels = torch.tensor([1 if x["label"] == "inconsistent" else 0
                                   for x in batch], device=device)
            out = model(**enc, labels=labels)
            if not torch.isfinite(out.loss):
                continue
            opt.zero_grad()
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot += float(out.loss.detach())
            nb += 1
        sch.step()
        print(f"  ep{ep + 1}: loss={tot / max(nb, 1):.4f} ({time.time() - t0:.0f}s)", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT))
    tok.save_pretrained(str(OUT))
    print(f"保存 → {OUT}")

    # gate评测: v12 vs v19b vs v19(旧, 泄漏版)
    print("\n═══ 源级独立gate评测(纯NLI模型) ═══")
    v12_g = pure_nli_eval(str(BASE / "models/nli/roberta-v12-anchor"), gate)
    print(f"v12: acc={v12_g['acc']}")
    print(f"  per_type: {v12_g['per_type']}")
    v19b_g = pure_nli_eval(str(OUT), gate)
    print(f"v19b: acc={v19b_g['acc']}")
    print(f"  per_type: {v19b_g['per_type']}")
    v19_old = pure_nli_eval(str(BASE / "models/nli/roberta-v19-mixed"), gate)
    print(f"v19(旧, 训练含同源): acc={v19_old['acc']}")
    print(f"  per_type: {v19_old['per_type']}")

    # 终点: 金标一次
    clean130 = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md = (json.loads((BASE / "data/gjb_438c/human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
          + json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8")))
    print("\n═══ 终点金标(纯v19b模型, 一次) ═══")
    rc = pure_nli_eval(str(OUT), clean130)
    rm = pure_nli_eval(str(OUT), md)
    print(f"v19b clean130: acc={rc['acc']}")
    print(f"v19b md166: acc={rm['acc']}")

    sys.path.insert(0, str(BASE / "tools"))
    from run_utils import open_run
    run = open_run("v19b_srcsplit_train", {
        "协议": "源级group split修复gate泄漏; gate=71独立源543条",
        "对比": "v12 vs v19b(干净) vs v19(旧泄漏版)"})
    run.save_result({
        "gate_v12": v12_g, "gate_v19b_clean": v19b_g, "gate_v19_old_leaky": v19_old,
        "terminal_clean130": rc["acc"], "terminal_md166": rm["acc"]})
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
