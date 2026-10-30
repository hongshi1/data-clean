"""CMNLI公开监督数据微调mDeBERTa — "公开数据最强外部baseline" (表2外部行).

论文故事: 与L2(EGT域合成数据微调, tools/train_residual_nli.py)构成
"公开数据 vs 域数据"对照——同一基座(mDeBERTa-v3-base-xnli), 同一训练
骨架(transformers Trainer, seed=42, fp16, 线性warmup10%), 数据换成
CMNLI 50k(seed=42抽样), 回答"公开NLI监督能否替代域适配".

流程:
  1. cmnli_train_raw.json(391k) 抽52k(seed=42, random.Random.sample):
     前50k=train, 末2k=dev (dev曲线与best-checkpoint选择用;
     CMNLI的dev_raw与test_raw为同一文件, 故dev从train抽样, 与test零重叠)
  2. label→基座config的label id (entailment=0/neutral=1/contradiction=2,
     预训练头语义保留; 复用nli_training.base_label_ids)
  3. 微调: max_length=256(CMNLI短句), batch 16, lr 2e-5, epochs 2,
     每500步dev评测(load_best=dev macro-F1), fp16(GPU), seed=42
  4. 最优checkpoint→models/nli/cmnli_finetuned_mdeberta/
     (public_baselines.BASELINE_MODEL_DIRS注册的路径);
     dev曲线/耗时/配置走runs协议(open_run)

纯本地训练: 零LLM调用. 用法:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/train_cmnli_nli.py
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.nli_training import (  # noqa: E402
    NLI_LABELS,
    base_label_ids,
)
from tools.public_nli_bench import (  # noqa: E402
    CMNLI_TRAIN_RAW,
    cmnli_test_keys,
    load_cmnli_train,
)
from tools.run_utils import open_run  # noqa: E402

SEED = 42
N_TRAIN = 50000
N_DEV = 2000
MAX_LENGTH = 256
LEARNING_RATE = 2e-5
EPOCHS = 2
BATCH = 16
EVAL_BATCH = 64
EVAL_STEPS = 500
OUT_DIR = BASE / "models" / "nli" / "cmnli_finetuned_mdeberta"


def sample_cmnli(n_train: int = N_TRAIN, n_dev: int = N_DEV,
                 seed: int = SEED) -> tuple[list[dict], list[dict], dict]:
    """CMNLI train → (train, dev, meta): 一次seed=42抽样52k, 前50k/末2k.

    与test的3个原始重复key显式剔除(dev/test零重叠口径可审计).
    """
    exclude = cmnli_test_keys()
    rows = load_cmnli_train(CMNLI_TRAIN_RAW, exclude_keys=exclude)
    total = n_train + n_dev
    if total > len(rows):
        raise ValueError(f"CMNLI可用行{len(rows)}不足抽样量{total}")
    rng = random.Random(seed)
    picked = rng.sample(range(len(rows)), total)
    train = [rows[i] for i in picked[:n_train]]
    dev = [rows[i] for i in picked[n_train:]]
    meta = {
        "source": str(CMNLI_TRAIN_RAW),
        "n_available": len(rows),
        "n_train": len(train),
        "n_dev": len(dev),
        "sample": f"random.Random({seed}).sample(available, {total}); "
                  f"前{n_train}=train, 末{n_dev}=dev",
        "excluded_test_duplicate_keys": 3,
        "train_label_dist": _dist(train),
        "dev_label_dist": _dist(dev),
    }
    return train, dev, meta


def _dist(pairs: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for pair in pairs:
        out[pair["label"]] = out.get(pair["label"], 0) + 1
    return out


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
    parser = argparse.ArgumentParser(description="CMNLI finetune mDeBERTa")
    parser.add_argument("--base", default="mdeberta", help="基座模型key")
    parser.add_argument("--n-train", type=int, default=N_TRAIN)
    parser.add_argument("--n-dev", type=int, default=N_DEV)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch", type=int, default=BATCH)
    parser.add_argument("--lr", type=float, default=LEARNING_RATE)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    parser.add_argument("--eval-steps", type=int, default=EVAL_STEPS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--no-fp16", action="store_true")
    parser.add_argument("--grad-ckpt", action="store_true",
                        help="梯度检查点(短句默认不需要; 兜底开关)")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    import torch
    from torch.utils.data import Dataset
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              DataCollatorWithPadding, Trainer, TrainingArguments,
                              set_seed)

    set_seed(args.seed)
    use_fp16 = (not args.no_fp16) and torch.cuda.is_available()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    base_dir = MODELS[args.base]["dir"]
    label_id = base_label_ids(args.base)
    id2label = {v: k for k, v in label_id.items()}
    n_labels = len(NLI_LABELS)

    train_pairs, dev_pairs, data_meta = sample_cmnli(
        args.n_train, args.n_dev, args.seed)
    print(json.dumps(data_meta, ensure_ascii=False, indent=1))
    print(f"base model: {base_dir}")
    print(f"device={device} fp16={use_fp16}")

    tokenizer = AutoTokenizer.from_pretrained(str(base_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(base_dir), local_files_only=True, torch_dtype=torch.float32,
        num_labels=n_labels, id2label=id2label, label2id=label_id)

    def to_example(pair: dict) -> dict:
        return {"premise": pair["premise"], "hypothesis": pair["hypothesis"],
                "label": label_id[{"support": "entailment",
                                   "refute": "contradiction",
                                   "not_in_evidence": "neutral"}[pair["label"]]]}

    class NliPairDataset(Dataset):
        def __init__(self, pairs: list[dict]) -> None:
            self.items = [to_example(p) for p in pairs]

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

    run = open_run("train_cmnli_nli", {
        "base_model": str(base_dir),
        "output": str(args.out_dir),
        "data": data_meta,
        "n_train": data_meta["n_train"],
        "n_dev": data_meta["n_dev"],
        "epochs": args.epochs,
        "batch": args.batch,
        "lr": args.lr,
        "max_length": args.max_length,
        "eval_steps": args.eval_steps,
        "seed": args.seed,
        "fp16": use_fp16,
        "grad_ckpt": args.grad_ckpt,
        "device": device,
    })
    print(f"run: {run.path}")

    warmup_steps = max(1, int(0.1 * data_meta["n_train"] * args.epochs
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
        gradient_checkpointing=args.grad_ckpt,
        gradient_checkpointing_kwargs={"use_reentrant": False}
        if args.grad_ckpt else None,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.eval_steps,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        save_total_limit=1,
        logging_steps=50,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=NliPairDataset(train_pairs),
        eval_dataset=NliPairDataset(dev_pairs),
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    t0 = time.time()
    trainer.train()
    train_seconds = round(time.time() - t0, 1)

    history = [
        {key: value for key, value in log.items()
         if not key.endswith("per_sample") and not key.endswith("per_batch")}
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

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True)
    trainer.save_model(str(args.out_dir))
    tokenizer.save_pretrained(str(args.out_dir))
    (args.out_dir / "cmnli_finetune_meta.json").write_text(
        json.dumps({
            "base_model": str(base_dir),
            "data": data_meta,
            "train_seconds": train_seconds,
            "dev_metrics": dev_metrics,
            "seed": args.seed,
            "created_by": f"tools/train_cmnli_nli.py run {run.path.name}",
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    run.save_result({
        "dev_metrics": dev_metrics,
        "train_seconds": train_seconds,
        "n_train": data_meta["n_train"],
        "n_dev": data_meta["n_dev"],
        "checkpoint": str(args.out_dir),
        "history": history,
    })
    for entry in history:
        run.log(**entry)

    print(json.dumps({
        "dev": dev_metrics,
        "train_seconds": train_seconds,
        "checkpoint": str(args.out_dir),
        "run": str(run.path),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
