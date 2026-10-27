r"""QLoRA微调 v2: 40种不一致×文档级零泄漏分割(文档级泛化测试).

数据: benchmark_v3(3400条, 文档级分割)
  训练: 文档01+05+06+08-16(2133条)
  验证: 文档03(450条)
  测试: 文档04+07(776条, 35种类型覆盖)
  零重叠: 训练/验证/测试的文档集合互斥

基座: Erlangshen-330M(1.3GB)
微调: LoRA r=8, 5 epochs, <4GB显存

对比基线(同一测试集):
  B1: mDeBERTa零样本
  B2: Erlangshen-330M零样本
  B3: 词法对齐

用法: python tools/q_lora_v2.py [--epochs 5]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

BENCH = BASE / "data/gjb_438c/benchmark_v3.jsonl"
MODEL_DIR = BASE / "models/nli/Erlangshen-Roberta-330M-NLI"
OUT_DIR = BASE / "models/nli/erlangshen-330m-qlora-v2"


def load_data() -> tuple[list, list, list]:
    items = [json.loads(line) for line in
             BENCH.read_text(encoding="utf-8").strip().splitlines()]
    train = [it for it in items if it['split'] == 'train']
    dev = [it for it in items if it['split'] == 'dev']
    test = [it for it in items if it['split'] == 'test']
    return train, dev, test


def finetune(train_data: list, epochs: int = 5, lora_r: int = 8,
             batch_size: int = 16) -> Path:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from peft import LoraConfig, get_peft_model

    print(f"  加载模型: {MODEL_DIR}")
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_DIR), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    config = LoraConfig(r=lora_r, lora_alpha=lora_r * 2, lora_dropout=0.1,
                        target_modules=["query", "value"], task_type="SEQ_CLS")
    model = get_peft_model(model, config)
    model.print_trainable_parameters()

    # 标签映射
    id2label = {int(k): str(v).lower() for k, v in
                model.base_model.config.id2label.items()}
    our_to_model = {}
    for our in ("contradiction", "neutral", "entailment"):
        for mid, mname in id2label.items():
            if our[:4] in mname or (our == "entailment" and "entail" in mname):
                our_to_model[our] = mid
                break
    if len(our_to_model) < 3:
        our_to_model = {"contradiction": 0, "neutral": 1, "entailment": 2}
    print(f"  标签映射: {our_to_model}")

    label_map = {"inconsistent": our_to_model["contradiction"],
                 "consistent": our_to_model["entailment"]}

    # 正类过采样(训练集只有7%正)
    pos = [it for it in train_data if it['expected_label'] == 'consistent']
    neg = [it for it in train_data if it['expected_label'] == 'inconsistent']
    if pos and len(pos) < len(neg) // 5:
        pos = pos * (len(neg) // (5 * len(pos)))
    balanced = neg + pos
    rng = random.Random(42)
    rng.shuffle(balanced)
    print(f"  训练集(均衡后): {len(balanced)}条")

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=2e-4)

    model.train()
    for epoch in range(epochs):
        total_loss, n_batches = 0.0, 0
        for i in range(0, len(balanced), batch_size):
            batch = balanced[i:i + batch_size]
            enc = tok([t["premise"] for t in batch],
                      [t["hypothesis"] for t in batch],
                      padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(device)
            labels = torch.tensor(
                [label_map.get(t["expected_label"], our_to_model["neutral"])
                 for t in batch], device=device)
            optimizer.zero_grad()
            out = model(**enc, labels=labels)
            out.loss.backward()
            optimizer.step()
            total_loss += out.loss.item()
            n_batches += 1
        print(f"  epoch {epoch + 1}/{epochs}: loss={total_loss / n_batches:.4f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged = model.merge_and_unload()
    merged.save_pretrained(str(OUT_DIR))
    tok.save_pretrained(str(OUT_DIR))
    print(f"  模型 → {OUT_DIR}")
    return OUT_DIR


def evaluate(model_dir: Path, test_data: list) -> dict:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()

    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    contra_id = next((k for k, v in id2label.items() if "contra" in v), 0)

    tp = fp = fn = tn = 0
    with torch.no_grad():
        for i in range(0, len(test_data), 32):
            batch = test_data[i:i + 32]
            enc = tok([t["premise"] for t in batch],
                      [t["hypothesis"] for t in batch],
                      padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(device)
            logits = model(**enc).logits
            preds = (logits[:, contra_id] == logits.max(dim=-1).values)
            for t, pred in zip(batch, preds.cpu()):
                exp = t["expected_label"] == "inconsistent"
                got = bool(pred)
                if exp and got:
                    tp += 1
                elif exp and not got:
                    fn += 1
                elif not exp and got:
                    fp += 1
                else:
                    tn += 1

    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * p * r / (p + r) if p + r else 0
    return {"P": round(p, 3), "R": round(r, 3), "F1": round(f1, 3),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=5)
    args = ap.parse_args()

    train, dev, test = load_data()
    n_pos_train = sum(1 for t in train if t['expected_label'] == 'consistent')
    print(f"数据: 训练{len(train)}({len(train)-n_pos_train}负+{n_pos_train}正) "
          f"| 验证{len(dev)} | 测试{len(test)}")

    # 零样本基线
    print(f"\n零样本基线(测试集 {len(test)}条):")
    from algorithms.consistency_check.nli_local import NliLocal

    for model_key, display in [("mdeberta", "B1: mDeBERTa"),
                                ("erlangshen-330m", "B2: Erlangshen-330M")]:
        nli = NliLocal(model_key)
        if nli.ensure() == "unavailable":
            print(f"  {display}: SKIP")
            continue
        vs = nli.predict_bidirectional(
            [(t["premise"], t["hypothesis"]) for t in test])
        tp = fp = fn = tn = 0
        for t, v in zip(test, vs):
            exp = t["expected_label"] == "inconsistent"
            got = v["sym_contra"]
            if exp and got:
                tp += 1
            elif exp and not got:
                fn += 1
            elif not exp and got:
                fp += 1
            else:
                tn += 1
        p = tp / (tp + fp) if tp + fp else 0
        r = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * p * r / (p + r) if p + r else 0
        print(f"  {display}: P={p:.3f} R={r:.3f} F1={f1:.3f}")

    # 词法基线
    from algorithms.blackboard.lexical_kit import text_match_score
    import re as _re

    def extract_entity(text):
        m = _re.search(r'[「]([^「」]{2,20})[」]', str(text))
        if m:
            return m.group(1)
        m2 = _re.search(r'包括：([^、。]{2,20})', str(text))
        return m2.group(1) if m2 else str(text)[:30]

    tp = fp = fn = tn = 0
    for t in test:
        pe = extract_entity(t['premise'])
        he = extract_entity(t['hypothesis'])
        score = text_match_score(pe, he) if pe and he else 0
        got = score < 0.5
        exp = t["expected_label"] == "inconsistent"
        if exp and got:
            tp += 1
        elif exp and not got:
            fn += 1
        elif not exp and got:
            fp += 1
        else:
            tn += 1
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * p * r / (p + r) if p + r else 0
    print(f"  B3: 词法: P={p:.3f} R={r:.3f} F1={f1:.3f}")

    # 微调
    print(f"\nQLoRA微调({args.epochs} epochs):")
    finetune(train, epochs=args.epochs)

    # 评测
    print("\n微调模型评测:")
    result = evaluate(OUT_DIR, test)
    print(f"  我们(QLoRA-v2): P={result['P']} R={result['R']} F1={result['F1']}")
    print(f"  混淆: tp={result['tp']} fp={result['fp']} fn={result['fn']} tn={result['tn']}")

    # 分类型成绩
    from collections import defaultdict
    by_ci = defaultdict(lambda: {"n": 0, "det": 0})
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(OUT_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(OUT_DIR), local_files_only=True)
    model.to("cuda" if torch.cuda.is_available() else "cpu").eval()
    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    contra_id = next((k for k, v in id2label.items() if "contra" in v), 0)

    with torch.no_grad():
        for i in range(0, len(test), 32):
            batch = test[i:i + 32]
            enc = tok([t["premise"] for t in batch],
                      [t["hypothesis"] for t in batch],
                      padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
            logits = model(**enc).logits
            preds = (logits[:, contra_id] == logits.max(dim=-1).values)
            for t, pred in zip(batch, preds.cpu()):
                if t["expected_label"] == "inconsistent":
                    by_ci[t["check_item"]]["n"] += 1
                    if bool(pred):
                        by_ci[t["check_item"]]["det"] += 1

    print("\n分类型成绩(测试集):")
    for ci in sorted(by_ci):
        d = by_ci[ci]
        if d["n"] >= 3:
            print(f"  {ci}: {d['det']}/{d['n']} ({d['det']/d['n']:.0%})")

    # 保存
    from run_utils import open_run
    run = open_run("q_lora_v2", {"epochs": args.epochs,
                                    "train_size": len(train), "test_size": len(test)})
    run.save_result(result)
    print(f"\nresult → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
