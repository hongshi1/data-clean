"""S4: 残差NLI域适配微调 — EGT合成数据 → 本地mDeBERTa (L2语义残差通道).

论文故事: MiniCheck式"小模型(~770M)逼近GPT-4级判定"在军事SRS三态任务上的
实例——用EGT合成样本微调本地mDeBERTa, 让它在成本~1/10下逼近L3 LLM残差
通道(macro-F1 0.7799)的判定质量.

v2(叙事文法升级): 训练数据换成v3_narrative数据集(表格行事实三元组→
真实QA answer风格叙事claim, R=跨行值污染, N=效果性扩展), 修复v1
"近拷贝diff让模型学到找字符差而非叙事性跨行值断言"的负结果.

流程 (transformers Trainer标准流程):
  1. algorithms/consistency/nli_training.py 构造训练对
      (premise=证据线性化文本, hypothesis=claim, 三态label映射到NLI类别)
  2. mDeBERTa序列对分类微调: max_length=512, batch 16, 4 epochs, lr 2e-5,
      fp16(GPU可用时), seed=42
  3. 每epoch在dev(10%, sample_id哈希分割)上评测三态accuracy/macro-F1
  4. 最优checkpoint(按dev macro-F1)落盘到 models/nli/egt_finetuned_v2/
      (路径集中在 algorithms/consistency/nli_local.py 的MODELS注册表);
      config/训练曲线/评测指标走runs协议(open_run)

纯本地训练: 零LLM调用. 用法:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/train_residual_nli.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.nli_training import (  # noqa: E402
    EGT_DATASET,
    NLI_LABELS,
    build_dataset,
)
from tools.run_utils import open_run  # noqa: E402

SEED = 42
MAX_LENGTH = 512
LEARNING_RATE = 2e-5
EPOCHS = 4
BATCH = 16
EVAL_BATCH = 32


def _macro_f1(preds: list[int], golds: list[int], n_labels: int) -> float:
    f1_sum = 0.0
    for label in range(n_labels):
        tp = sum(1 for p, g in zip(preds, golds) if p == label == g)
        fp = sum(1 for p, g in zip(preds, golds) if p == label and g != label)
        fn = sum(1 for p, g in zip(preds, golds) if p != label and g == label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)
        f1_sum += f1
    return f1_sum / n_labels


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="S4 residual NLI finetune")
    parser.add_argument("--base", default="mdeberta", help="基座模型key")
    parser.add_argument("--out-key", default="egt_finetuned_v2",
                        help="MODELS注册表中checkpoint输出key")
    parser.add_argument("--data", type=Path, default=None,
                        help="EGT jsonl路径(默认nli_training.EGT_DATASET)")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch", type=int, default=BATCH)
    parser.add_argument("--lr", type=float, default=LEARNING_RATE)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--no-fp16", action="store_true")
    args = parser.parse_args()

    import torch
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              DataCollatorWithPadding, Trainer, TrainingArguments,
                              set_seed)
    from torch.utils.data import Dataset

    set_seed(args.seed)
    use_fp16 = (not args.no_fp16) and torch.cuda.is_available()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    base_dir = MODELS[args.base]["dir"]
    out_dir = Path(MODELS[args.out_key]["dir"])

    dataset = build_dataset(path=args.data or EGT_DATASET,
                            model_key=args.base)
    label_id = dataset["meta"]["label_id"]
    id2label = {v: k for k, v in label_id.items()}
    n_labels = len(NLI_LABELS)
    print(json.dumps(dataset["meta"], ensure_ascii=False, indent=1))
    print(f"base model: {base_dir}")
    print(f"device={device} fp16={use_fp16}")

    tokenizer = AutoTokenizer.from_pretrained(str(base_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(base_dir), local_files_only=True, torch_dtype=torch.float32,
        num_labels=n_labels, id2label=id2label, label2id=label_id)

    class NliPairDataset(Dataset):
        def __init__(self, examples: list[dict]) -> None:
            self.items = examples

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, index: int) -> dict:
            ex = self.items[index]
            enc = tokenizer(ex["premise"], ex["hypothesis"],
                            truncation="longest_first",
                            max_length=args.max_length)
            return {"input_ids": enc["input_ids"],
                    "attention_mask": enc["attention_mask"],
                    "label": ex["label"]}

    def compute_metrics(eval_pred) -> dict:
        logits, labels = eval_pred
        preds = logits.argmax(axis=-1).tolist()
        golds = labels.tolist()
        acc = sum(1 for p, g in zip(preds, golds) if p == g) / len(golds)
        per_label = {}
        for name, lid in label_id.items():
            tp = sum(1 for p, g in zip(preds, golds) if p == lid == g)
            fp = sum(1 for p, g in zip(preds, golds) if p == lid and g != lid)
            fn = sum(1 for p, g in zip(preds, golds) if p != lid and g == lid)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            per_label[name] = round(
                2 * precision * recall / (precision + recall)
                if precision + recall else 0.0, 4)
        return {"accuracy": round(acc, 4),
                "macro_f1": round(_macro_f1(preds, golds, n_labels), 4),
                **{f"f1_{k}": v for k, v in per_label.items()}}

    run = open_run("train_residual_nli", {
        "base_model": str(base_dir),
        "output": str(out_dir),
        "out_key": args.out_key,
        "egt": dataset["meta"]["source_path"],
        "n_train": dataset["meta"]["n_train"],
        "n_dev": dataset["meta"]["n_dev"],
        "epochs": args.epochs,
        "batch": args.batch,
        "lr": args.lr,
        "max_length": args.max_length,
        "seed": args.seed,
        "fp16": use_fp16,
        "device": device,
    })
    print(f"run: {run.path}")

    warmup_steps = max(1, int(0.1 * len(dataset["train"]) * args.epochs
                             / args.batch))
    training_args = TrainingArguments(
        output_dir=str(run.path / "trainer"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=EVAL_BATCH,
        learning_rate=args.lr,
        lr_scheduler_type="linear",
        warmup_steps=warmup_steps,
        weight_decay=0.01,
        fp16=use_fp16,
        seed=args.seed,
        data_seed=args.seed,
        # 512-token序列的attention激活会让8GB显存溢出到WDDM共享内存
        # (实测16s/step); 梯度检查点以~30%重算换5.6GB峰值, 恢复~1.1s/step
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        save_total_limit=1,
        logging_steps=20,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=NliPairDataset(dataset["train"]),
        eval_dataset=NliPairDataset(dataset["dev"]),
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    import time
    t0 = time.time()
    trainer.train()
    train_seconds = round(time.time() - t0, 1)

    history = [
        {key: value for key, value in log.items() if key != "eval_runtime"
         and not key.endswith("per_sample") and not key.endswith("per_batch")}
        for log in trainer.state.log_history
        if any(k.startswith(("loss", "eval_")) for k in log)
    ]
    final_metrics = trainer.evaluate()
    dev_metrics = {
        "accuracy": final_metrics.get("eval_accuracy"),
        "macro_f1": final_metrics.get("eval_macro_f1"),
        "per_label_f1": {name: final_metrics.get(f"eval_f1_{name}")
                         for name in NLI_LABELS},
    }

    # 最优checkpoint(Trainer已load_best_model_at_end) → models/nli/egt_finetuned/
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    (out_dir / "egt_finetune_meta.json").write_text(
        json.dumps({
            "base_model": str(base_dir),
            "egt_dataset": dataset["meta"]["source_path"],
            "train_seconds": train_seconds,
            "dev_metrics": dev_metrics,
            "seed": args.seed,
            "created_by": f"tools/train_residual_nli.py run {run.path.name}",
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    run.save_result({
        "dev_metrics": dev_metrics,
        "train_seconds": train_seconds,
        "n_train": dataset["meta"]["n_train"],
        "n_dev": dataset["meta"]["n_dev"],
        "checkpoint": str(out_dir),
        "history": history,
    })
    for entry in history:
        run.log(**entry)

    print(json.dumps({
        "dev": dev_metrics,
        "train_seconds": train_seconds,
        "checkpoint": str(out_dir),
        "run": str(run.path),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
