r"""MMQA正例物化+LoRA微调实验: 补齐3分类数据缺口 → 领域适配消融.

按调研结论(docs/srs_project/asset_inventory.md + eval_scheme_v2.md):
  P0: 物化正例(P⁰恒等+P⁺等效) — 3分类微调的数据缺口
  P1: leave-one-doc-out LoRA微调, 评测与训练doc级隔离

数据构造(资产编排式, 不新造):
  负例: mmqa mutations.jsonl的1335条(构造真值gold, doc02)
  P⁰恒等: 原pair未变异的声明(81对) — consistent
  P⁺等效: 单位换算对(20条) — consistent(表面不同语义等价)
  P⁺语义保持: 同义改写(从SYN_MAP确定性生成) — consistent

评测: benchmark四任务(T1-T4), 与零样本对比 — leave-one-doc-out:
  doc02的pair及其全部产物进train, 其余文档的评测条目为test侧
  (T1的非doc02键264条=39.8%是干净评测区; T2的9条docs6/8/11/15干净)

用法: python tools/nli_finetune.py [--model erlangshen-330m] [--epochs 3]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

MMQA = BASE / "data/gjb_438c/mmqa"
TRAIN_OUT = BASE / "data/gjb_438c/mmqa/finetune_data.json"

SYN_MAP = {"获取": "采集", "管理": "管控", "监控": "监测", "处理": "处置",
           "传输": "传送", "存储": "保存", "查询": "检索", "删除": "移除"}


def build_training_data(seed: int = 42) -> dict:
    """负例(1335) + 三族正例 → (premise, hypothesis, label)三元组."""
    rng = random.Random(seed)
    mutations = [json.loads(line) for line in
                 (MMQA / "mutations.jsonl").read_text(
                     encoding="utf-8").strip().splitlines()]
    triples = []

    # 负例: mmqa声明的claim对(全部inconsistent)
    n_neg = 0
    for m in mutations:
        for c in m.get("claims", []):
            triples.append({"premise": c["premise"],
                            "hypothesis": c["hypothesis"],
                            "label": "contradiction",
                            "source": "mmqa_neg"})
            n_neg += 1

    # P⁰恒等: 原pair的声明(用benign的对照——mmqa设计中的恒等正例)
    # 从词法对齐成功的pair提取(复用nli_pair_claims在原pair上的声明)
    n_id = 0
    from algorithms.consistency.nli_pair_claims import load_pair_claims
    pair_root = BASE / "data/gjb_438c/pair_dataset"
    # 只用训练侧pair(doc02的sc2)
    for pd in sorted((pair_root / "sc2_flowchart_usecase").iterdir()):
        if not (pd / "meta.json").exists():
            continue
        pid, claims = load_pair_claims(pd)
        if not claims:
            continue
        # 采1条声明作为恒等正例
        c = rng.choice(claims)
        triples.append({"premise": c.premise, "hypothesis": c.hypothesis,
                        "label": "entailment", "source": "p0_identity"})
        n_id += 1
        if n_id >= 60:
            break

    # P⁺等效: 单位换算(语义等价但表面不同)
    n_eq = 0
    CONV = [("秒", "ms", 1000.0), ("s", "ms", 1000.0), ("分钟", "秒", 60.0),
            ("GB", "MB", 1024.0), ("MB", "KB", 1024.0)]
    vals = [0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 100, 200, 500, 1000]
    for _ in range(40):
        val = rng.choice(vals)
        u1, u2, factor = rng.choice(CONV)
        a, b = f"{val:g}{u1}", f"{val * factor:g}{u2}"
        triples.append({"premise": f"文档规定：『{a}』。",
                        "hypothesis": f"文档另一处规定：『{b}』。",
                        "label": "entailment", "source": "p_plus_equiv"})
        n_eq += 1

    # P⁺语义保持: 同义改写(同义但保持事实)
    n_syn = 0
    for old, new in list(SYN_MAP.items())[:8]:
        for _ in range(5):
            val = rng.choice(vals)
            triples.append({
                "premise": f"文档规定：『{old}{val}条数据』。",
                "hypothesis": f"文档另一处规定：『{new}{val}条数据』。",
                "label": "neutral", "source": "p_plus_synonym"})
            n_syn += 1

    rng.shuffle(triples)
    summary = {"total": len(triples), "neg": n_neg, "identity": n_id,
               "equiv": n_eq, "synonym": n_syn,
               "label_dist": {"contradiction": n_neg,
                              "entailment": n_id + n_eq,
                              "neutral": n_syn}}
    return {"triples": triples, "summary": summary}


def finetune_lora(model_key: str, triples: list[dict],
                  epochs: int = 3, lora_r: int = 8) -> Path:
    """LoRA微调NLI模型(peft库, 冻结基座+低秩适配)."""
    import torch
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer)
    from peft import LoraConfig, get_peft_model
    from algorithms.consistency.nli_local import MODELS

    model_dir = MODELS[model_key]["dir"]
    tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_dir, local_files_only=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    # peft LoRA: 对attention的query/value和FFN注入低秩适配
    config = LoraConfig(
        r=lora_r, lora_alpha=lora_r * 2, lora_dropout=0.1,
        target_modules=["query", "value", "intermediate.dense"],
        task_type="SEQ_CLS")
    model = get_peft_model(model, config)
    model.print_trainable_parameters()

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=2e-4)

    # 标签映射(从模型config取)
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
    print(f"标签映射: {our_to_model} (模型: {id2label})")

    # 类别不均衡: contradiction 2148 vs entailment 100 vs neutral 40
    # → 正类过采样到~800条 + 负类下采样到~1200条(加速+均衡)
    import random as _rnd
    rng = _rnd.Random(42)
    pos = [t for t in triples if t["label"] != "contradiction"]
    neg = [t for t in triples if t["label"] == "contradiction"]
    oversampled_pos = pos * 10  # 140→1400
    neg_sampled = rng.sample(neg, min(1200, len(neg)))
    balanced = neg_sampled + oversampled_pos
    rng.shuffle(balanced)
    print(f"训练集(均衡后): {len(balanced)}条 "
          f"(负{len(neg_sampled)} + 正{len(oversampled_pos)})")

    # 训练循环
    batch_size = 16
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
                [our_to_model.get(t["label"], 1) for t in batch],
                device=device)
            optimizer.zero_grad()
            out = model(**enc, labels=labels)
            out.loss.backward()
            optimizer.step()
            total_loss += out.loss.item()
            n_batches += 1
        print(f"  epoch {epoch + 1}/{epochs}: loss={total_loss / n_batches:.4f}")

    # 保存(合并LoRA权重到基座)
    out_dir = BASE / "models" / "nli" / f"{model_key}-lora-finetuned"
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = model.merge_and_unload()
    merged.save_pretrained(str(out_dir))
    tok.save_pretrained(str(out_dir))
    print(f"微调模型(LoRA合并) → {out_dir}")
    return out_dir


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="erlangshen-330m")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    if args.skip_build and TRAIN_OUT.exists():
        data = json.loads(TRAIN_OUT.read_text(encoding="utf-8"))
    else:
        print("构建训练数据(负例+三族正例)...")
        data = build_training_data()
        TRAIN_OUT.write_text(json.dumps(data, ensure_ascii=False),
                             encoding="utf-8")
    print(f"训练数据: {data['summary']}")

    print(f"\nLoRA微调 {args.model} ({args.epochs} epochs)...")
    finetune_lora(args.model, data["triples"], epochs=args.epochs)

    print("\n完成. 评测:")
    print(f"  python tools/nli_benchmark.py --models {args.model}-lora-finetuned")


if __name__ == "__main__":
    main()
