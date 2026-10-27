"""SRS一致性校验 — 核心方法统一管理入口.

用法:
  python tools/run.py build     # 构建数据集(canonical + QA)
  python tools/run.py train     # 训练模型(v12锚点适配)
  python tools/run.py eval      # 评测(真实金标)
  python tools/run.py check     # 单条校验(演示)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")


def cmd_build():
    """构建数据集: canonical pair dataset + QA synthesis."""
    print("═ 构建数据集 ═\n")

    # 1. 重建canonical(修复doc02污染+证据核验)
    print("Step 1: 重建canonical pair dataset(修复污染+证据核验)...")
    _rebuild_canonical()

    # 2. QA合成(含质控)
    print("\nStep 2: QA合成(含质控)...")
    _build_qa()

    print("\n═ 数据集构建完成 ═")


def _rebuild_canonical():
    """重建canonical数据集 — 修复两个已知问题:
    1. doc02锚点污染(训练集含clean130的45条)
    2. 证据核验标记丢失(0条标记,应有~279条)
    """
    import re
    from collections import Counter

    PD = BASE / "data/gjb_438c/pair_dataset_canonical"

    # 读取现有train
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]

    # 修复1: 排除clean130对应的doc02锚点
    clean = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    clean_keys = set()
    for x in clean:
        m = re.search(r"[「]([^「」]+)[」]", x["premise"])
        if m:
            clean_keys.add(m.group(1))
        else:
            clean_keys.add(x["premise"][:30])

    def is_clean130_leak(x):
        if x["source"] != "srs_anchor":
            return False
        if not str(x.get("context", {}).get("doc", "")).startswith("02"):
            return False
        m = re.search(r"[「]([^「」]+)[」]", x["pair"]["premise"])
        k = m.group(1) if m else x["pair"]["premise"][:30]
        return k in clean_keys

    n_before = len(train)
    train_fixed = [x for x in train if not is_clean130_leak(x)]
    n_removed = n_before - len(train_fixed)
    print(f"  修复1: 排除clean130泄漏 {n_removed}条({n_before}→{len(train_fixed)})")

    # 修复2: 重新运行证据核验
    n_refuted = 0
    for x in train_fixed:
        if (x["source"] == "srs_anchor" and "MISSING" in x["angle"]["type"]
                and x.get("context", {}).get("diagram")):
            m = re.search(r"[「]([^「」]+)[」]", x["pair"]["premise"])
            if m and len(m.group(1).strip()) >= 3:
                claim = m.group(1).strip()
                diag = x["context"]["diagram"]
                if claim in diag or claim.replace(" ", "") in diag.replace(" ", ""):
                    x["quality"]["flags"].append("evidence_refuted")
                    n_refuted += 1
    print(f"  修复2: 证据核验标记 {n_refuted}条")

    # 保存修复后的train
    with open(PD / "train.jsonl", "w", encoding="utf-8") as f:
        for x in train_fixed:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    # 更新INDEX
    index = {"spec": "docs/srs_project/pair_dataset_spec.md", "total": 0, "splits": {}}
    sources = Counter(x["source"] for x in train_fixed)
    labels = Counter(x["label"] for x in train_fixed)
    index["splits"]["train"] = {"n": len(train_fixed), "sources": dict(sources), "labels": dict(labels)}
    test = [json.loads(line) for line in open(PD / "test.jsonl", encoding="utf-8")]
    index["splits"]["test"] = {"n": len(test)}
    index["total"] = len(train_fixed) + len(test)
    with open(PD / "INDEX.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"  canonical修复后: train={len(train_fixed)}, test={len(test)}")


def _build_qa():
    """QA合成(使用qa_synth v2含质控)."""
    from algorithms.qa_synth import (
        Evidence, Pair, ParamShift, TermSwap, ItemRemove, OrderSwap,
        generate_qa_for_pair, build_semantic_groups, quality_filter)

    PD = BASE / "data/gjb_438c/pair_dataset_canonical"
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]
    anchors = [x for x in train if x["source"] == "srs_anchor"
               and "evidence_refuted" not in x.get("quality", {}).get("flags", [])]

    # 转换为Evidence/Pair
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
            relation="same_constraint", entity_id=x["pair"]["premise"][:15],
            is_consistent=(x["label"] == "consistent"), label_source="gold"))

    # 变异+QA
    operators = [ParamShift(), TermSwap(), ItemRemove(), OrderSwap()]
    all_samples = []

    for pair in pairs:
        if pair.is_consistent is True:
            record = type("R", (), {
                "operator": "none", "target_type": "P0_IDENTITY",
                "position": f"{pair.premise.source_doc}",
                "original": pair.premise.content[:30],
                "mutated": pair.hypothesis.content[:30],
                "is_valid": True, "validation_note": "原始一致对",
                "conflict_verified": False})()
            all_samples.extend(generate_qa_for_pair(pair, record))

    n_mutated = 0
    for pair in pairs:
        for op in operators:
            mut_pair, record = op.mutate(pair, {})
            if record.is_valid and record.conflict_verified:
                all_samples.extend(generate_qa_for_pair(mut_pair, record))
                n_mutated += 1

    # 语义组
    groups = build_semantic_groups(pairs)
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
    print(f"  QA: {len(all_samples)}→质控通过{len(passed)}(拒绝{sum(rejected.values())})")
    print(f"  质控: {rejected}")

    # 保存
    out = BASE / "data/gjb_438c/qa_dataset_v2.json"
    data = {"meta": {"total": len(passed), "pairs": len(pairs), "mutated": n_mutated,
                      "groups": len(groups), "rejected": rejected},
             "samples": [
                 {"id": qa.id, "qa_type": qa.qa_type, "question": qa.question,
                  "answer": qa.answer, "label": qa.label, "type": qa.inconsistency_type,
                  "location": qa.location, "explanation": qa.explanation,
                  "evidence": [{"content": e.content, "modality": e.modality,
                                 "doc": e.source_doc, "section": e.source_section}
                                for e in qa.evidence_chain],
                  "group_id": qa.group.id if qa.group else None,
                  "provenance": qa.provenance}
                 for qa in passed]}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"  保存 → {out}")


def cmd_train():
    """训练模型(v12)."""
    print("═ 训练模型 ═\n")
    import random
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    PD = BASE / "data/gjb_438c/pair_dataset_canonical"
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]
    anchor = [x for x in train if x["source"] == "srs_anchor"
              and "evidence_refuted" not in x.get("quality", {}).get("flags", [])
              and not str(x.get("context", {}).get("doc", "")).startswith("02")]
    inc = [x for x in anchor if x["label"] == "inconsistent"]
    con = [x for x in anchor if x["label"] == "consistent"]
    random.Random(42).shuffle(con)
    con_up = (con * 6)[:len(inc) // 2]
    data = inc + con + con_up
    random.Random(42).shuffle(data)
    print(f"训练: {len(data)}条(inc{len(inc)}+con{len(con)}×6→{len(con_up)})")

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
    """评测."""
    print("═ 评测 ═\n")
    from algorithms.consistency.checker import ConsistencyChecker

    ck = ConsistencyChecker()
    clean = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md = (json.loads((BASE / "data/gjb_438c/human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
          + json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8")))

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
        print(f"  {name}: bAcc={bacc:.3f} TPR={tp / n_pos:.3f} TNR={tn / n_neg:.3f}")


def cmd_check():
    """单条校验演示."""
    from algorithms.consistency.checker import ConsistencyChecker
    ck = ConsistencyChecker()
    examples = [
        ("系统响应时间不大于2秒", "系统响应时间不大于5秒"),
        ("表格规定「数据引接汇聚」功能", "图中规定「数据引接汇渠」功能"),
    ]
    print("═ 单条校验 ═\n")
    for p, h in examples:
        r = ck.check(p, h)
        print(f"P: {p}")
        print(f"H: {h}")
        print(f"→ {r.verdict} | {r.item} | {r.solver}\n")


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
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
