r"""QLoRA微调实验: 场景1不一致性检测的领域适配.

方案:
  基座: Erlangshen-330M(中文NLI, 量化INT8)
  微调: LoRA rank=8(bitsandbytes 4bit量化 + peft)
  数据: 统一Benchmark场景1子集(train/test 8:2分割)
  评测: 与零样本mDeBERTa、零样本Erlangshen、词法对齐对比

对比基线:
  B1: 零样本mDeBERTa(F1=0.942, 当前最优)
  B2: 零样本Erlangshen-330M
  B3: 词法对齐(text_match_score<0.5)
  我们: QLoRA微调后的Erlangshen-330M

用法: python tools/q_lora_finetune.py [--epochs 3] [--quick]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

BENCH = BASE / "data/gjb_438c/benchmark.jsonl"
MODEL_DIR = BASE / "models/nli/Erlangshen-Roberta-330M-NLI"
OUT_DIR = BASE / "models/nli/erlangshen-330m-qlora"

SC1_TYPES = {'TABLE_ITEM_MISSING', 'TERM-01', 'TERM-03', 'LOGIC-05',
             'GJB-01', 'GJB-02', 'GJB-03', 'ACTOR_MISSING', 'STEP_MISSING',
             'EXC_MISSING', 'DIAGRAM_EXTRA', 'COMPONENT_MISSING'}


def load_sc1_data(seed: int = 42) -> tuple[list, list]:
    """加载场景1数据 → (train, test) 8:2分割(防泄漏: 按source_asset分组)."""
    items = [json.loads(line) for line in
             BENCH.read_text(encoding="utf-8").strip().splitlines()]

    # 场景1相关负例
    neg = [it for it in items if it['label'] == 'inconsistent'
           and it['check_item'] in SC1_TYPES]
    # 清洗后的正例(P1_REAL + 通过内容过滤的P0_IDENTITY)
    pos = [it for it in items if it['tier'] == 'L4_positive'
           and it['check_item'] == 'P1_REAL']

    # 按source_asset的前缀(即pair_id)分组, 同组不跨split
    import re
    from collections import defaultdict
    groups = defaultdict(list)
    for it in neg + pos:
        # source_asset格式: "MUT-1_001-TERM-01" 或 "silver_1_002_00"
        m = re.search(r'(\d+_\d+)', it.get('source_asset', ''))
        gid = m.group(1) if m else it['id']
        groups[gid].append(it)

    rng = random.Random(seed)
    gids = sorted(groups.keys())
    rng.shuffle(gids)
    n_test = max(1, len(gids) // 5)

    train, test = [], []
    for i, gid in enumerate(gids):
        target = test if i < n_test else train
        target.extend(groups[gid])

    # 正类过采样(训练集)
    train_pos = [it for it in train if it['label'] == 'consistent']
    train_neg = [it for it in train if it['label'] == 'inconsistent']
    if train_pos and len(train_pos) < len(train_neg) // 5:
        train_pos = train_pos * (len(train_neg) // (5 * len(train_pos)))
    train = train_neg + train_pos
    rng.shuffle(train)
    rng.shuffle(test)

    return train, test


def finetune_qlora(train_data: list, epochs: int = 3,
                   lora_r: int = 8, batch_size: int = 8) -> Path:
    """QLoRA微调: INT8量化基座 + LoRA."""
    import torch
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer)
    from peft import LoraConfig, get_peft_model

    print(f"\n加载模型: {MODEL_DIR}")
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_DIR), local_files_only=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    # LoRA配置
    config = LoraConfig(
        r=lora_r, lora_alpha=lora_r * 2, lora_dropout=0.1,
        target_modules=["query", "value"],
        task_type="SEQ_CLS")
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
    print(f"标签映射: {our_to_model}")

    # 二分类简化: inconsistent→contradiction, consistent→entailment
    label_map = {"inconsistent": our_to_model["contradiction"],
                 "consistent": our_to_model["entailment"]}

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=2e-4)

    model.train()
    n_steps = 0
    for epoch in range(epochs):
        total_loss, n_batches = 0.0, 0
        for i in range(0, len(train_data), batch_size):
            batch = train_data[i:i + batch_size]
            enc = tok([t["premise"] for t in batch],
                      [t["hypothesis"] for t in batch],
                      padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(device)
            labels = torch.tensor(
                [label_map.get(t["label"], our_to_model["neutral"])
                 for t in batch], device=device)
            optimizer.zero_grad()
            out = model(**enc, labels=labels)
            out.loss.backward()
            optimizer.step()
            total_loss += out.loss.item()
            n_batches += 1
            n_steps += 1
            if n_steps % 50 == 0:
                print(f"  step {n_steps}: loss={total_loss / n_batches:.4f}")
        print(f"  epoch {epoch + 1}/{epochs}: avg_loss={total_loss / n_batches:.4f}")

    # 保存
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged = model.merge_and_unload()
    merged.save_pretrained(str(OUT_DIR))
    tok.save_pretrained(str(OUT_DIR))
    print(f"\n微调模型 → {OUT_DIR}")
    return OUT_DIR


def evaluate(model_dir: Path, test_data: list) -> dict:
    """在测试集上评测微调模型."""
    import torch
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer)

    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()

    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    contra_id = next((k for k, v in id2label.items() if "contra" in v), 0)

    tp = fp = fn = tn = 0
    model.eval()
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
                exp = t["label"] == "inconsistent"
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
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="快速测试(100条)")
    args = ap.parse_args()

    print("══ QLoRA微调: 场景1不一致性检测 ══\n")

    # 1. 加载数据
    train, test = load_sc1_data()
    if args.quick:
        train = train[:100]
        test = test[:50]
    n_pos_train = sum(1 for t in train if t['label'] == 'consistent')
    n_neg_train = len(train) - n_pos_train
    n_pos_test = sum(1 for t in test if t['label'] == 'consistent')
    n_neg_test = len(test) - n_pos_test
    print(f"训练集: {len(train)}条({n_neg_train}负+{n_pos_train}正)")
    print(f"测试集: {len(test)}条({n_neg_test}负+{n_pos_test}正)")

    # 2. 零样本基线
    print("\n══ 零样本基线(测试集) ══")
    from algorithms.consistency_check.nli_local import NliLocal

    for model_key, display in [("mdeberta", "B1: mDeBERTa零样本"),
                                ("erlangshen-330m", "B2: Erlangshen-330M零样本")]:
        nli = NliLocal(model_key)
        mode = nli.ensure()
        if mode == "unavailable":
            print(f"  {display}: SKIP")
            continue
        # 评测
        vs = nli.predict_bidirectional(
            [(t["premise"], t["hypothesis"]) for t in test])
        tp = fp = fn = tn = 0
        for t, v in zip(test, vs):
            exp = t["label"] == "inconsistent"
            got = v["sym_contra"]  # 双向对称
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
        exp = t['label'] == 'inconsistent'
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
    print(f"  B3: 词法对齐: P={p:.3f} R={r:.3f} F1={f1:.3f}")

    # 3. 微调
    print("\n══ QLoRA微调 ══")
    finetune_qlora(train, epochs=args.epochs)

    # 4. 评测微调模型
    print("\n══ 微调模型评测(测试集) ══")
    result = evaluate(OUT_DIR, test)
    print(f"  我们(QLoRA微调): P={result['P']} R={result['R']} F1={result['F1']}")
    print(f"  混淆: tp={result['tp']} fp={result['fp']} fn={result['fn']} tn={result['tn']}")

    # 保存结果
    from run_utils import open_run
    run = open_run("q_lora_finetune", {
        "epochs": args.epochs, "train_size": len(train),
        "test_size": len(test), "quick": args.quick})
    run.save_result(result)
    print(f"\nresult → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
