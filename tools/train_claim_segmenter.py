r"""D2 Step2: 蒸馏本地claim切分器 — GLM-5.3教师claim文本 → 字符级B/I/O.

任务形式: 每个answer字符标 {B=claim首, I=claim内, O=未覆盖}
(教师claims的find()区间→字符标签, M86: 蒸文本切分不蒸索引).
基座models/nli/chinese-roberta-wwm-ext + token分类头; 类不均衡(B≈5%)
用逆频率加权CE. 训练数据=segmenter_train_v1.json的212个answer
(dev45+violations17+crossdoc150, 诚实契约: test-46不可见),
10%哈希分桶做训练内dev(同D1模式).

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/train_claim_segmenter.py
输出: models/segmenter/claim_segmenter_v1/ (tokenizer+model+meta.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.claim_segmenter import (  # noqa: E402
    LABELS,
    LABEL_B,
    char_labels_from_claims,
    decode_char_labels,
)
from tools.run_utils import open_run  # noqa: E402

TRAIN_DATA = BASE / "data/gjb_438c/distillation/segmenter_train_v1.json"
BASE_MODEL = BASE / "models/nli/chinese-roberta-wwm-ext"
OUT_DIR = BASE / "models/segmenter/claim_segmenter_v1"

SEED = 42
MAX_LENGTH = 512
LEARNING_RATE = 2e-5
EPOCHS = 4
BATCH = 8
EVAL_BATCH = 16
DEV_FRAC = 0.1
#: 类权重上限(逆频率加权, B稀有类防爆炸)
_WEIGHT_CAP = 20.0


def load_train_answers(path: Path) -> list[dict]:
    """segmenter_train_v1.json → 训练answer记录(claims含find_span)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    answers = [rec for rec in doc["answers"]
               if rec.get("llm_status") == "ok"]
    if not answers:
        raise ValueError(f"{path}无llm_status=ok的训练answer")
    return answers


def _bucket_split(records: list[dict],
                  dev_frac: float) -> tuple[list[dict], list[dict]]:
    """确定性train/dev分割(instance_id哈希分桶, 同D1模式)."""
    train: list[dict] = []
    dev: list[dict] = []
    for rec in records:
        digest = hashlib.md5(str(rec["instance_id"]).encode("utf-8")).hexdigest()
        if int(digest[:8], 16) / 0xFFFFFFFF < dev_frac:
            dev.append(rec)
        else:
            train.append(rec)
    return train, dev


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-data", type=Path, default=TRAIN_DATA)
    parser.add_argument("--base", type=Path, default=BASE_MODEL)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch", type=int, default=BATCH)
    parser.add_argument("--lr", type=float, default=LEARNING_RATE)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dev-frac", type=float, default=DEV_FRAC)
    parser.add_argument("--weight-cap", type=float, default=_WEIGHT_CAP,
                        help="B类逆频率权重上限(压低→少切, 调召回/精度平衡)")
    parser.add_argument("--no-fp16", action="store_true")
    args = parser.parse_args()

    import torch
    from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                              DataCollatorForTokenClassification, Trainer,
                              TrainingArguments, set_seed)
    from torch.utils.data import Dataset

    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16 = (not args.no_fp16) and torch.cuda.is_available()

    label2id = {name: i for i, name in enumerate(LABELS)}
    id2label = {i: name for i, name in enumerate(LABELS)}

    # ── 1. 训练数据: claims → B/I/O字符标签 → token标签(offset对齐) ──
    answers = load_train_answers(args.train_data)
    train_recs, dev_recs = _bucket_split(answers, args.dev_frac)
    tokenizer = AutoTokenizer.from_pretrained(str(args.base),
                                              local_files_only=True)
    if not tokenizer.is_fast:
        raise RuntimeError("基座tokenizer非fast(无offset_mapping), 无法对齐")

    skipped_long: list[str] = []
    for rec in answers:
        claims = rec.get("claims") or []
        spans = [tuple(c["find_span"]) for c in claims
                 if c.get("in_answer") and c.get("find_span")]
        rec["char_labels"] = char_labels_from_claims(rec["answer"], spans)

    def build_features(recs: list[dict]) -> tuple[list[dict], list[dict]]:
        """records → (features, 对齐后的recs); 超512 token的answer显式跳过."""
        features: list[dict] = []
        aligned: list[dict] = []
        cls_id, sep_id = tokenizer.cls_token_id, tokenizer.sep_token_id
        for rec in recs:
            encoded = tokenizer(rec["answer"], add_special_tokens=False,
                                return_offsets_mapping=True)
            if len(encoded["input_ids"]) > MAX_LENGTH - 2:
                skipped_long.append(rec["instance_id"])  # 显式记录, 不静默
                continue
            input_ids = [cls_id] + list(encoded["input_ids"]) + [sep_id]
            per_token = [
                label2id[rec["char_labels"][s]]
                if s < len(rec["char_labels"]) else label2id["O"]
                for (s, _e) in encoded["offset_mapping"]]
            features.append({
                "input_ids": input_ids,
                "token_type_ids": [0] * len(input_ids),
                "attention_mask": [1] * len(input_ids),
                "labels": [-100] + per_token + [-100],  # [CLS]/[SEP]不进损失
            })
            aligned.append(rec)
        return features, aligned

    train_features, _train_aligned = build_features(train_recs)
    dev_features, dev_answers_aligned = build_features(dev_recs)

    if not train_features or not dev_features:
        raise SystemExit(f"训练/dev特征为空: train={len(train_features)} "
                         f"dev={len(dev_features)}")

    # ── 2. 类权重(B稀有: 逆频率, 截断上限) ──
    counts = {name: 0 for name in LABELS}
    for feat in train_features:
        for lab in feat["labels"]:
            if lab != -100:
                counts[LABELS[lab]] += 1
    total = sum(counts.values())
    weights = torch.tensor(
        [min(total / (len(LABELS) * max(counts[name], 1)), args.weight_cap)
         for name in LABELS], dtype=torch.float32)
    weight_map = {name: round(float(w), 3) for name, w in zip(LABELS, weights)}

    class ClaimDataset(Dataset):
        def __init__(self, features: list[dict]) -> None:
            self.items = features

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, index: int) -> dict:
            return self.items[index]

    class WeightedTrainer(Trainer):
        """逆频率类权重CE(标签-100跳过); 其余Trainer行为不变."""

        def compute_loss(self, model, inputs, return_outputs=False,
                         num_items_in_batch=None):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            loss_fct = torch.nn.CrossEntropyLoss(
                weight=self._class_weights.to(
                    device=logits.device, dtype=torch.float32))
            loss = loss_fct(logits.reshape(-1, logits.size(-1)).float(),
                            labels.reshape(-1))
            return (loss, outputs) if return_outputs else loss

    # ── 3. dev指标: token级B P/R/F1 + 字符级claim区间F1(与推理同解码) ──
    def _span_f1(preds: list[list[int]], golds: list[list[int]],
                 dev_recs_used: list[dict]) -> dict:
        exact_tp = exact_fp = exact_fn = 0
        b_tp = b_fp = b_fn = 0
        for pred_row, gold_row, rec in zip(preds, golds, dev_recs_used):
            answer = rec["answer"]
            gold_labels = rec["char_labels"]
            encoded = tokenizer(answer, add_special_tokens=False,
                                return_offsets_mapping=True)
            pred_labels = ["O"] * len(answer)
            token_index = 1  # 跳过[CLS]
            for (start, end) in encoded["offset_mapping"]:
                lab = LABELS[pred_row[token_index]] if token_index < len(
                    pred_row) else "O"
                token_index += 1
                for pos in range(start, min(end, len(answer))):
                    pred_labels[pos] = lab
            gold_spans = set(decode_char_labels(gold_labels))
            pred_spans = set(decode_char_labels(pred_labels))
            exact_tp += len(pred_spans & gold_spans)
            exact_fp += len(pred_spans - gold_spans)
            exact_fn += len(gold_spans - pred_spans)
            gold_starts = {s for s, _ in gold_spans}
            pred_starts = {s for s, _ in pred_spans}
            b_tp += len(pred_starts & gold_starts)
            b_fp += len(pred_starts - gold_starts)
            b_fn += len(gold_starts - pred_starts)
        out = {}
        for name, tp, fp, fn in (("span", exact_tp, exact_fp, exact_fn),
                                 ("boundary", b_tp, b_fp, b_fn)):
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            out[f"{name}_f1"] = round(
                2 * precision * recall / (precision + recall)
                if precision + recall else 0.0, 4)
            out[f"{name}_precision"] = round(precision, 4)
            out[f"{name}_recall"] = round(recall, 4)
        return out

    def compute_metrics(eval_pred) -> dict:
        logits, label_ids = eval_pred
        preds = logits.argmax(axis=-1).tolist()
        golds = label_ids.tolist()
        correct = compared = 0
        b_tp = b_fp = b_fn = 0
        for pred_row, gold_row in zip(preds, golds):
            for p, g in zip(pred_row, gold_row):
                if g == -100:
                    continue
                compared += 1
                correct += int(p == g)
                if p == label2id[LABEL_B]:
                    if g == label2id[LABEL_B]:
                        b_tp += 1
                    else:
                        b_fp += 1
                elif g == label2id[LABEL_B]:
                    b_fn += 1
        token_b_p = b_tp / (b_tp + b_fp) if b_tp + b_fp else 0.0
        token_b_r = b_tp / (b_tp + b_fn) if b_tp + b_fn else 0.0
        return {
            "char_acc": round(correct / compared, 4) if compared else 0.0,
            "token_b_precision": round(token_b_p, 4),
            "token_b_recall": round(token_b_r, 4),
            "token_b_f1": round(
                2 * token_b_p * token_b_r / (token_b_p + token_b_r)
                if token_b_p + token_b_r else 0.0, 4),
            **_span_f1(preds, golds, dev_answers_aligned),
        }

    meta = {
        "task": "char-level B/I/O claim segmentation (distilled)",
        "train_data": str(args.train_data),
        "n_answers_total": len(answers),
        "n_train_answers": len(train_features),
        "n_dev_answers": len(dev_features),
        "dev_frac": args.dev_frac,
        "skipped_long_answers": skipped_long,
        "char_label_counts": counts,
        "class_weights": weight_map,
        "base_model": str(args.base),
        "max_length": MAX_LENGTH,
        "epochs": args.epochs,
        "batch": args.batch,
        "lr": args.lr,
        "seed": args.seed,
        "fp16": use_fp16,
        "device": device,
        "honest_contract": ("train=dev45+violations17+crossdoc150; "
                            "test-46不可见"),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=1))

    model = AutoModelForTokenClassification.from_pretrained(
        str(args.base), local_files_only=True, torch_dtype=torch.float32,
        num_labels=len(LABELS), id2label=id2label, label2id=label2id)

    run = open_run("train_claim_segmenter", meta)
    print(f"run: {run.path}")

    warmup_steps = max(1, int(0.1 * len(train_features) * args.epochs
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
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="span_f1",
        greater_is_better=True,
        save_total_limit=1,
        logging_steps=20,
        report_to=[],
    )
    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=ClaimDataset(train_features),
        eval_dataset=ClaimDataset(dev_features),
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
    )
    trainer._class_weights = weights

    import time
    t0 = time.time()
    trainer.train()
    train_seconds = round(time.time() - t0, 1)

    final_metrics = trainer.evaluate()
    history = [
        {key: value for key, value in log.items()
         if key != "eval_runtime" and not key.endswith("per_sample")
         and not key.endswith("per_batch")}
        for log in trainer.state.log_history
        if any(k.startswith(("loss", "eval_")) for k in log)
    ]

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    trainer.save_model(str(args.out))
    tokenizer.save_pretrained(str(args.out))
    (args.out / "meta.json").write_text(
        json.dumps({**meta,
                    "train_seconds": train_seconds,
                    "dev_metrics": final_metrics,
                    "created_by": (f"tools/train_claim_segmenter.py run "
                                   f"{run.path.name}"),
                    }, ensure_ascii=False, indent=1), encoding="utf-8")

    run.save_result({
        "dev_metrics": final_metrics,
        "train_seconds": train_seconds,
        "history": history,
        "checkpoint": str(args.out),
    })
    print(json.dumps({
        "dev": final_metrics,
        "train_seconds": train_seconds,
        "checkpoint": str(args.out),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
