"""SRS一致性校验 — 核心方法统一管理入口.

所有核心算法都在这里管理。这是唯一的脚本入口。

用法:
  python tools/run.py build     # 构建数据集(canonical + QA)
  python tools/run.py train     # 训练模型(v12锚点适配)
  python tools/run.py eval      # 评测(真实金标 + 分族)
  python tools/run.py check     # 单条校验(演示)
  python tools/run.py clean     # 清理旧数据/旧模型
"""
from __future__ import annotations

import sys
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

MODELS_TO_KEEP = {
    "chinese-roberta-wwm-ext",     # 基础模型(训练用)
    "roberta-v12-anchor",           # 最终模型(Task 1用)
    "macbert-v13",                  # 类型覆盖模型
    "Erlangshen-Roberta-330M-NLI", # 零样本基线
    "mDeBERTa-v3-base-xnli-multilingual-nli-2mil7", # 零样本基线(多语言)
}

TOOLS_TO_KEEP = {
    "run.py",                       # 本文件
    "build_data_manifest.py",       # 数据资产MANIFEST
}


def cmd_build():
    """构建数据集: canonical pair dataset + QA synthesis."""
    print("═ 构建数据集 ═\n")

    # 1. Canonical pair dataset
    print("Step 1: 构建canonical pair dataset...")
    from tools.build_pair_dataset_canonical import main as build_canonical
    build_canonical()

    # 2. 扩充变异
    print("\nStep 2: 扩充变异...")
    from tools.expand_mutations_full import main as expand_mutations
    expand_mutations()

    # 3. QA合成(使用重构后的qa_synth)
    print("\nStep 3: QA合成(含质控)...")
    _build_qa_dataset()

    print("\n═ 数据集构建完成 ═")


def _build_qa_dataset():
    """使用重构后的qa_synth生成QA数据集(含质控过滤)."""
    import json
    from algorithms.consistency_check.qa_synth import (
        Evidence, Pair, ParamShift, TermSwap, ItemRemove, OrderSwap,
        generate_qa_for_pair, build_semantic_groups, quality_filter)

    # 读取canonical train中的锚点数据
    PD = BASE / "data/gjb_438c/pair_dataset_canonical"
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]
    anchors = [x for x in train if x["source"] == "srs_anchor"
               and not str(x.get("context", {}).get("doc", "")).startswith("02")]

    # 转换为Evidence/Pair格式
    pairs = []
    for x in anchors:
        p_ev = Evidence(
            id=f"E-{x['id']}-p", content=x["pair"]["premise"],
            modality="text", source_doc=str(x.get("provenance", {}).get("doc", "")),
            source_section=str(x.get("provenance", {}).get("origin", ""))[:20])
        h_ev = Evidence(
            id=f"E-{x['id']}-h", content=x["pair"]["hypothesis"],
            modality="text", source_doc=str(x.get("provenance", {}).get("doc", "")),
            source_section=str(x.get("provenance", {}).get("origin", ""))[:20])
        pairs.append(Pair(
            id=x["id"], premise=p_ev, hypothesis=h_ev,
            relation="same_constraint",
            entity_id=x["pair"]["premise"][:15],
            is_consistent=(x["label"] == "consistent"),
            label_source="gold"))

    # 变异+QA生成
    operators = [ParamShift(), TermSwap(), ItemRemove(), OrderSwap()]
    all_samples = []

    # 一致对的QA(原始对,不变异)
    for pair in pairs:
        if pair.is_consistent is True:
            record = type("R", (), {
                "operator": "none", "target_type": "P0_IDENTITY",
                "position": f"{pair.premise.source_doc}",
                "original": pair.premise.content[:30],
                "mutated": pair.hypothesis.content[:30],
                "is_valid": True, "validation_note": "原始一致对",
                "conflict_verified": False})()
            qas = generate_qa_for_pair(pair, record)
            all_samples.extend(qas)

    # 变异对
    n_mutated = 0
    for pair in pairs:
        for op in operators:
            mut_pair, record = op.mutate(pair, {})
            if record.is_valid and record.conflict_verified:
                qas = generate_qa_for_pair(mut_pair, record)
                all_samples.extend(qas)
                n_mutated += 1

    # 语义组
    groups = build_semantic_groups(pairs, theme="SRS一致性")
    # 填充QA的group字段
    group_map = {g.id: g for g in groups}
    for qa in all_samples:
        if qa.pairs:
            eid = qa.pairs[0].entity_id
            for g in groups:
                if eid in g.entity_ids:
                    qa.group = g
                    break

    # 质控
    passed, rejected = quality_filter(all_samples)

    print(f"  锚点Pair: {len(pairs)}条")
    print(f"  变异成功: {n_mutated}个(含冲突验证)")
    print(f"  QA生成: {len(all_samples)}条 → 质控通过{len(passed)}条(拒绝{sum(rejected.values())})")
    print(f"  语义组: {len(groups)}个")
    print(f"  质控详情: {rejected}")

    # 保存
    out = BASE / "data/gjb_438c/qa_dataset_v2.json"
    data = {
        "meta": {"total": len(passed), "rejected": rejected, "pairs": len(pairs),
                  "mutated": n_mutated, "groups": len(groups)},
        "samples": [
            {
                "id": qa.id, "qa_type": qa.qa_type,
                "question": qa.question, "answer": qa.answer,
                "label": qa.label, "type": qa.inconsistency_type,
                "location": qa.location, "explanation": qa.explanation,
                "evidence": [
                    {"content": e.content, "modality": e.modality,
                     "doc": e.source_doc, "section": e.source_section}
                    for e in qa.evidence_chain],
                "group_id": qa.group.id if qa.group else None,
                "provenance": qa.provenance,
            } for qa in passed
        ],
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"  保存 → {out}")


def cmd_train():
    """训练模型(v12: 纯领域微调)."""
    print("═ 训练模型 ═\n")

    import json
    import random
    import torch
    import time
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    PD = BASE / "data/gjb_438c/pair_dataset_canonical"
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]
    anchor = [x for x in train if x["source"] == "srs_anchor"
              and not str(x.get("context", {}).get("doc", "")).startswith("02")]
    inc = [x for x in anchor if x["label"] == "inconsistent"]
    con = [x for x in anchor if x["label"] == "consistent"]
    random.Random(42).shuffle(con)
    con_up = (con * 6)[:len(inc) // 2]
    data = inc + con + con_up
    random.Random(42).shuffle(data)
    print(f"训练数据: {len(data)}条(inc{len(inc)}+con{len(con)}×6→{len(con_up)})")

    MODEL_DIR = str(BASE / "models/nli/chinese-roberta-wwm-ext")
    OUT = BASE / "models/nli/roberta-v12-anchor"
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
        for i in range(0, len(data), 16):
            batch = data[i:i + 16]
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


def cmd_eval():
    """评测: ConsistencyChecker + v12 + 分族."""
    print("═ 评测 ═\n")
    import json
    from algorithms.consistency_check.consistency_checker import ConsistencyChecker

    ck = ConsistencyChecker()
    clean = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md = (json.loads((BASE / "data/gjb_438c/human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
          + json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8")))

    results = {}
    for name, items in [("clean130", clean), ("md166", md)]:
        ys, ps = [], []
        for x in items:
            y = x["label"] if isinstance(x.get("label"), str) else (
                "inconsistent" if x["label"] == 1 else "consistent")
            r = ck.check(x["premise"], x["hypothesis"])
            ys.append(y)
            ps.append(r.verdict)
        tp = sum(1 for a, b in zip(ys, ps) if a == "inconsistent" and b == "inconsistent")
        tn = sum(1 for a, b in zip(ys, ps) if a == "consistent" and b == "consistent")
        n_pos = ys.count("inconsistent")
        n_neg = len(ys) - n_pos
        bacc = (tp / n_pos + tn / n_neg) / 2
        results[name] = {"bAcc": round(bacc, 3), "TPR": round(tp / n_pos, 3), "TNR": round(tn / n_neg, 3)}
        print(f"  {name}: bAcc={bacc:.3f} TPR={tp / n_pos:.3f} TNR={tn / n_neg:.3f}")

    out = BASE / "data/gjb_438c/runs/latest_eval.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"保存 → {out}")


def cmd_check():
    """单条校验演示."""
    from algorithms.consistency_check.consistency_checker import ConsistencyChecker
    ck = ConsistencyChecker()
    examples = [
        ("系统响应时间不大于2秒", "系统响应时间不大于5秒"),
        ("表格规定「数据引接汇聚」功能", "图中规定「数据引接汇渠」功能"),
        ("表格包含「日志管理」条目", "图中没有「日志管理」对应元素"),
    ]
    print("═ 单条校验演示 ═\n")
    for p, h in examples:
        r = ck.check(p, h)
        print(f"P: {p[:40]}")
        print(f"H: {h[:40]}")
        print(f"→ {r.verdict} | {r.item[:40]} | {r.solver}\n")


def cmd_clean():
    """清理旧数据/旧模型/旧脚本."""
    print("═ 清理 ═\n")

    # 1. 清理旧模型
    models_dir = BASE / "models/nli"
    removed_models = []
    for d in models_dir.iterdir():
        if d.is_dir() and d.name not in MODELS_TO_KEEP:
            removed_models.append(d.name)
            shutil.rmtree(d, ignore_errors=True)
    print(f"清理模型: {len(removed_models)}个(保留{len(MODELS_TO_KEEP)}个)")
    for m in removed_models:
        print(f"  ✗ {m}")
    print(f"  ✓ 保留: {MODELS_TO_KEEP}")

    # 2. 清理旧数据
    old_data = [
        "data/gjb_438c/qa_dataset_synthesized.json",  # 旧版QA(无质控)
        "data/gjb_438c/sft_train_v11.jsonl",           # 旧版SFT数据
        "data/gjb_438c/benchmark_train_v3.jsonl",      # 旧版训练集
        "data/gjb_438c/benchmark_train_v4.jsonl",      # 旧版训练集
        "data/gjb_438c/pu_train_v10.jsonl",            # 旧版PU数据
        "data/gjb_438c/cct_train.jsonl",               # 旧版CCT数据
        "data/gjb_438c/expanded_mutations.jsonl",       # 旧版扩充变异
    ]
    removed_data = []
    for f in old_data:
        p = BASE / f
        if p.exists():
            removed_data.append(f)
            p.unlink()
    print(f"\n清理数据: {len(removed_data)}个")
    for f in removed_data:
        print(f"  ✗ {f}")

    # 3. 清理旧脚本(tools/中不在保留列表的)
    removed_tools = []
    for f in (BASE / "tools").glob("*.py"):
        if f.name not in TOOLS_TO_KEEP and f.name.startswith(("train_v", "eval_v", "baseline_",
                "type_family", "per_type", "fill_", "decontam", "ensemble_v", "rlcd",
                "symmetric", "family_matrix", "expand_mutations", "build_sft", "build_external",
                "build_cct", "canonical")):
            removed_tools.append(f.name)
            f.unlink()
    print(f"\n清理脚本: {len(removed_tools)}个")
    for t in removed_tools:
        print(f"  ✗ {t}")

    print("\n═ 清理完成 ═")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "build":
        cmd_build()
    elif cmd == "train":
        cmd_train()
    elif cmd == "eval":
        cmd_eval()
    elif cmd == "check":
        cmd_check()
    elif cmd == "clean":
        cmd_clean()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
