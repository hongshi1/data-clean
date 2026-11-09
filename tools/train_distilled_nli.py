"""D1: LLM仲裁蒸馏微调 — GLM-5.3教师标签 → 本地mDeBERTa (纯推理时零LLM).

论文故事: 旧CascadeVerify的L3 LLM仲裁通道(Glm-5.3, macro-F1 0.8747)是
性能关键但生产禁用远程API. 本脚本把L3的一次性claim级判定蒸馏进本地
NLI残差通道: 教师标签离线生成一次(tools/distill_teacher_labels.py,
全部缓存可复现), 学生(egt_finetuned_v2)在真实04号SRS证据分布上继续
微调 — 推理时算法保持纯本地三层(L0 NER+L1规则+L2 NLI), 零API调用.

诚实评测契约: 训练数据只取dev split(29主题簇, dev45)的教师标签;
test-46/violations-17/crossdoc-150在训练中不可见.

训练组成:
  - 蒸馏对: (premise=学生推理时实际看到的证据语句拼接, hypothesis=claim,
    label=教师三态判定) — premise与推理管线逐字节同源(residual_premise)
  - EGT回放: 混入EGT合成对防止小样本灾难遗忘(比例可配)
  - refute过采样: 教师refute样本稀少(13/355), 按k倍复制

用法:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/train_distilled_nli.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
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
LEARNING_RATE = 1e-5
EPOCHS = 4
BATCH = 16
EVAL_BATCH = 32
DISTILL_DATA = BASE / "data/gjb_438c/distillation/teacher_labels_v1.jsonl"


def load_distill_pairs(path: Path, splits: set[str], corpora: set[str],
                       covered_only: bool) -> list[dict]:
    """教师标签jsonl → (premise, hypothesis, label)训练对."""
    pairs: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["split"] not in splits or rec["corpus"] not in corpora:
            continue
        premise = str(rec.get("premise", "")).strip()
        claim = str(rec.get("claim_text", "")).strip()
        verdict = str(rec.get("teacher_verdict", ""))
        if not premise or not claim or verdict not in (
                "support", "refute", "not_in_evidence"):
            continue
        if covered_only and verdict in ("support", "refute") \
                and not rec.get("premise_covered"):
            continue
        label = {"support": "entailment",
                 "refute": "contradiction",
                 "not_in_evidence": "neutral"}[verdict]
        pairs.append({
            "premise": premise,
            "hypothesis": claim,
            "label": label,
            "claim_id": rec["claim_id"],
            "instance_id": rec["instance_id"],
        })
    return pairs


def _bucket_split(pairs: list[dict], dev_frac: float,
                  key: str = "claim_id") -> tuple[list[dict], list[dict]]:
    """确定性train/dev分割(claim_id哈希分桶, 无seed依赖)."""
    train: list[dict] = []
    dev: list[dict] = []
    for pair in pairs:
        digest = hashlib.md5(str(pair[key]).encode("utf-8")).hexdigest()
        if int(digest[:8], 16) / 0xFFFFFFFF < dev_frac:
            dev.append(pair)
        else:
            train.append(pair)
    return train, dev


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="D1 LLM distillation finetune")
    parser.add_argument("--teacher-data", type=Path, default=DISTILL_DATA)
    parser.add_argument("--splits", nargs="*", default=["dev"],
                        help="参与训练的教师标签split(dev=诚实契约)")
    parser.add_argument("--corpora", nargs="*", default=["qa91"])
    parser.add_argument("--covered-only", action="store_true",
                        help="剔除教师引用未覆盖premise的support/refute对")
    parser.add_argument("--egt-replay-mult", type=float, default=2.0,
                        help="EGT回放条数=蒸馏train数×mult")
    parser.add_argument("--oversample-refute", type=int, default=3)
    parser.add_argument("--base", default="egt_finetuned_v2")
    parser.add_argument("--out-key", default="distilled_v1")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch", type=int, default=BATCH)
    parser.add_argument("--lr", type=float, default=LEARNING_RATE)
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

    # ── 1. 蒸馏对 (dev split only: 诚实评测契约) ──
    distill = load_distill_pairs(args.teacher_data, set(args.splits),
                                 set(args.corpora), args.covered_only)
    if not distill:
        raise SystemExit("no distillation pairs matched the filters")
    distill_train, distill_dev = _bucket_split(distill, 0.15)

    # refute过采样 (教师refute稀少)
    oversampled = list(distill_train)
    for pair in distill_train:
        if pair["label"] == "contradiction":
            for _ in range(args.oversample_refute - 1):
                oversampled.append(pair)

    # ── 2. EGT回放 (防灾难遗忘) ──
    rng = random.Random(args.seed)
    egt = build_dataset(path=EGT_DATASET, model_key="mdeberta")
    replay_n = int(len(distill_train) * args.egt_replay_mult)
    replay = rng.sample(egt["train"], min(replay_n, len(egt["train"])))
    replay = [{"premise": ex["premise"], "hypothesis": ex["hypothesis"],
               "label": NLI_LABELS[ex["label"]] if isinstance(
                   ex["label"], int) else ex["label"],
               "claim_id": f"egt:{i}",
               "instance_id": "egt"} for i, ex in enumerate(replay)]
    # normalize EGT label ids → names if build_dataset returned ints
    label_id = egt["meta"]["label_id"]
    id2name = {v: k for k, v in label_id.items()}
    for ex in replay:
        if isinstance(ex["label"], int):
            ex["label"] = id2name[ex["label"]]

    train_all = oversampled + replay
    label_counts: dict[str, int] = {}
    for ex in train_all:
        label_counts[ex["label"]] = label_counts.get(ex["label"], 0) + 1
    meta = {
        "n_distill_total": len(distill),
        "n_distill_train": len(distill_train),
        "n_distill_dev": len(distill_dev),
        "n_oversampled_train": len(oversampled),
        "n_egt_replay": len(replay),
        "n_train_total": len(train_all),
        "train_label_counts": label_counts,
        "teacher_data": str(args.teacher_data),
        "splits": args.splits,
        "corpora": args.corpora,
        "covered_only": args.covered_only,
        "oversample_refute": args.oversample_refute,
        "egt_replay_mult": args.egt_replay_mult,
        "base_model": str(base_dir),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"device={device} fp16={use_fp16}")

    # ── 3. 继续微调 ──
    base_config = json.loads(
        (Path(base_dir) / "config.json").read_text(encoding="utf-8"))
    label2id = {k: int(v) for k, v in base_config["label2id"].items()}
    id2label = {v: k for k, v in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(str(base_dir),
                                               local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(base_dir), local_files_only=True, torch_dtype=torch.float32,
        num_labels=len(NLI_LABELS), id2label=id2label, label2id=label2id)

    def to_label_id(name: str) -> int:
        return label2id[name]

    class NliPairDataset(Dataset):
        def __init__(self, examples: list[dict]) -> None:
            self.items = examples

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, index: int) -> dict:
            ex = self.items[index]
            enc = tokenizer(ex["premise"], ex["hypothesis"],
                            truncation="longest_first", max_length=MAX_LENGTH)
            return {"input_ids": enc["input_ids"],
                    "attention_mask": enc["attention_mask"],
                    "label": to_label_id(ex["label"])}

    def _macro_f1(preds: list[int], golds: list[int]) -> float:
        f1_sum = 0.0
        for label in label2id.values():
            tp = sum(1 for p, g in zip(preds, golds) if p == label == g)
            fp = sum(1 for p, g in zip(preds, golds) if p == label and g != label)
            fn = sum(1 for p, g in zip(preds, golds) if p != label and g == label)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1_sum += (2 * precision * recall / (precision + recall)
                       if precision + recall else 0.0)
        return f1_sum / len(label2id)

    def compute_metrics(eval_pred) -> dict:
        logits, labels = eval_pred
        preds = logits.argmax(axis=-1).tolist()
        golds = labels.tolist()
        acc = sum(1 for p, g in zip(preds, golds) if p == g) / len(golds)
        per_label = {}
        for name, lid in label2id.items():
            tp = sum(1 for p, g in zip(preds, golds) if p == lid == g)
            fp = sum(1 for p, g in zip(preds, golds) if p == lid and g != lid)
            fn = sum(1 for p, g in zip(preds, golds) if p != lid and g == lid)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            per_label[name] = round(
                2 * precision * recall / (precision + recall)
                if precision + recall else 0.0, 4)
        return {"accuracy": round(acc, 4),
                "macro_f1": round(_macro_f1(preds, golds), 4),
                **{f"f1_{k}": v for k, v in per_label.items()}}

    run = open_run("train_distilled_nli", {**meta,
                                           "epochs": args.epochs,
                                           "batch": args.batch,
                                           "lr": args.lr,
                                           "seed": args.seed,
                                           "fp16": use_fp16,
                                           "device": device,
                                           "output": str(out_dir)})
    print(f"run: {run.path}")

    warmup_steps = max(1, int(0.1 * len(train_all) * args.epochs
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
        train_dataset=NliPairDataset(train_all),
        eval_dataset=NliPairDataset(distill_dev if distill_dev else train_all),
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    import time
    t0 = time.time()
    trainer.train()
    train_seconds = round(time.time() - t0, 1)

    history = [
        {key: value for key, value in log.items()
         if key != "eval_runtime" and not key.endswith("per_sample")
         and not key.endswith("per_batch")}
        for log in trainer.state.log_history
        if any(k.startswith(("loss", "eval_")) for k in log)
    ]
    final_metrics = trainer.evaluate()

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    (out_dir / "distill_meta.json").write_text(
        json.dumps({**meta,
                    "train_seconds": train_seconds,
                    "dev_metrics": {
                        "accuracy": final_metrics.get("eval_accuracy"),
                        "macro_f1": final_metrics.get("eval_macro_f1"),
                        "per_label_f1": {name: final_metrics.get(
                            f"eval_f1_{name}") for name in NLI_LABELS},
                    },
                    "seed": args.seed,
                    "created_by": f"tools/train_distilled_nli.py run "
                                  f"{run.path.name}",
                    }, ensure_ascii=False, indent=1), encoding="utf-8")

    run.save_result({
        "dev_metrics": {
            "accuracy": final_metrics.get("eval_accuracy"),
            "macro_f1": final_metrics.get("eval_macro_f1"),
            "per_label_f1": {name: final_metrics.get(f"eval_f1_{name}")
                             for name in NLI_LABELS},
        },
        "train_seconds": train_seconds,
        "history": history,
        "checkpoint": str(out_dir),
    })
    print(json.dumps({
        "dev": {"macro_f1": final_metrics.get("eval_macro_f1"),
                "accuracy": final_metrics.get("eval_accuracy")},
        "train_seconds": train_seconds,
        "checkpoint": str(out_dir),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
