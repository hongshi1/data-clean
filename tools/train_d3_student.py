"""D3学生训练: LoRA微调Qwen3-1.7B直产完整任务(verdict+定位+解释).

训练对(输入=教师同款prompt, 目标=教师JSON标签):
  user   = 【问题】/【answer】/【证据ev-N】/输出spec
  target = {"verdict":..., "issues":[{quote,span,rule_id,
            evidence_ref,explanation}]}

这正是"模型优先"架构: 无claim分解/无启发式中间层, 定位能力
(quote逐字+span)直接训进模型. 训练数据=212条D3教师标签
(dev45+violations17+crossdoc150; test-46 held-out).

训练: LoRA r=16 α=32, lr=1e-4, 3 epochs, 90/10哈希分桶dev,
fp16, 梯度检查点(8GB显存).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.d3_teacher_labels import (  # noqa: E402
    _SPEC,
    _SYSTEM,
)

LABELS = BASE / "data/gjb_438c/distillation/d3_teacher_labels_v1.jsonl"
BASE_MODEL = BASE / "models/llm/qwen3-1.7b"
OUT_DIR = BASE / "models/llm/d3_student_v1"


def _user_message(row: dict) -> str:
    lines = [f"【问题】{row['question']}", "",
             "【待校验answer】", row["answer"], "", "【证据】"]
    for index, text in enumerate(row["evidence"], 1):
        import re
        cleaned = re.sub(r"\s+", " ", str(text)).strip()
        lines.append(f"ev-{index}: {cleaned}")
    lines += ["", _SPEC]
    return "\n".join(lines)


def _target_message(row: dict) -> str:
    issues = [{
        "quote": i["quote"],
        "span": i["span"],
        "rule_id": i["rule_id"],
        "evidence_ref": i["evidence_ref"],
        "explanation": i["explanation"],
    } for i in row["issues"]]
    return json.dumps({"verdict": row["verdict"], "issues": issues},
                      ensure_ascii=False)


def _split(rows: list[dict], dev_frac: float = 0.1
           ) -> tuple[list[dict], list[dict]]:
    train: list[dict] = []
    dev: list[dict] = []
    for row in rows:
        digest = hashlib.md5(row["instance_id"].encode()).hexdigest()
        if int(digest[:8], 16) / 0xFFFFFFFF < dev_frac:
            dev.append(row)
        else:
            train.append(row)
    return train, dev


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--max-len", type=int, default=3072)
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              Trainer,
                              TrainingArguments, set_seed)

    set_seed(42)
    use_fp16 = torch.cuda.is_available()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device} fp16={use_fp16}")

    rows = [json.loads(line) for line in
            LABELS.read_text(encoding="utf-8").splitlines() if line.strip()]
    train_rows, dev_rows = _split(rows)
    print(f"训练对: {len(train_rows)} | dev: {len(dev_rows)}")

    tokenizer = AutoTokenizer.from_pretrained(str(BASE_MODEL))
    model = AutoModelForCausalLM.from_pretrained(
        str(BASE_MODEL), torch_dtype=torch.float16
        if use_fp16 else torch.float32)
    model.to(device)
    model.config.use_cache = False

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    def encode(row: dict) -> dict:
        messages = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _user_message(row)},
            {"role": "assistant", "content": _target_message(row)}]
        # 版本稳健路径: 模板渲染成字符串再分词(transformers 5.x的
        # tokenize=True返回结构不保证是id列表)
        prompt_text = tokenizer.apply_chat_template(
            messages[:2], tokenize=False, add_generation_prompt=True)
        full_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False)
        prompt_ids = tokenizer(prompt_text, add_special_tokens=False
                               )["input_ids"]
        full_ids = tokenizer(full_text, add_special_tokens=False
                             )["input_ids"]
        labels = list(full_ids)
        for i in range(len(prompt_ids)):
            labels[i] = -100
        full_ids = full_ids[:args.max_len]
        labels = labels[:args.max_len]
        return {"input_ids": full_ids, "labels": labels,
                "attention_mask": [1] * len(full_ids)}

    import torch.utils.data as torch_data

    class D3Dataset(torch_data.Dataset):
        def __init__(self, items: list[dict]) -> None:
            self.items = [encode(r) for r in items]
            self.items = [x for x in self.items if len(x["input_ids"]) > 10]

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, index: int) -> dict:
            return self.items[index]

    train_ds = D3Dataset(train_rows)
    dev_ds = D3Dataset(dev_rows)
    print(f"编码后: train={len(train_ds)} dev={len(dev_ds)} "
          f"(max_len={args.max_len})")

    from tools.run_utils import open_run  # noqa: PLC0415

    run = open_run("train_d3_student", {
        "base": str(BASE_MODEL), "n_train": len(train_ds),
        "n_dev": len(dev_ds), "epochs": args.epochs, "lr": args.lr,
        "batch": args.batch, "grad_accum": args.grad_accum,
        "max_len": args.max_len, "lora": "r16a32drop0.05", "seed": 42,
    })

    training_args = TrainingArguments(
        output_dir=str(run.path / "trainer"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=5,
        weight_decay=0.01,
        fp16=use_fp16,
        seed=42,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        logging_steps=5,
        report_to=[],
        remove_unused_columns=False,
    )

    def collate(batch: list[dict]) -> dict:
        maxlen = max(len(x["input_ids"]) for x in batch)
        pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id
        input_ids, labels, attention = [], [], []
        for x in batch:
            n = maxlen - len(x["input_ids"])
            input_ids.append(x["input_ids"] + [pad_id] * n)
            labels.append(x["labels"] + [-100] * n)
            attention.append(x["attention_mask"] + [0] * n)
        import torch as _torch
        return {
            "input_ids": _torch.tensor(input_ids),
            "labels": _torch.tensor(labels),
            "attention_mask": _torch.tensor(attention),
        }

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=dev_ds,
        data_collator=collate,
    )
    started = time.time()
    trainer.train()
    elapsed = round(time.time() - started, 1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT_DIR))
    tokenizer.save_pretrained(str(OUT_DIR))
    (OUT_DIR / "d3_meta.json").write_text(json.dumps({
        "base": str(BASE_MODEL), "n_train": len(train_ds),
        "n_dev": len(dev_ds), "epochs": args.epochs,
        "train_seconds": elapsed, "labels": str(LABELS),
        "created_by": f"tools/train_d3_student.py run {run.path.name}",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    run.save_result({"train_seconds": elapsed,
                     "adapter": str(OUT_DIR),
                     "history": [dict(h) for h in trainer.state.log_history
                                 if "loss" in h or "eval_loss" in h]})
    print(json.dumps({"adapter": str(OUT_DIR),
                      "train_seconds": elapsed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
