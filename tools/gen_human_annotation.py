#!/usr/bin/env python3
"""P4: 生成人工标注包(最小可行版)

从eval_set.json分层抽样100条,输出盲标CSV:
  - 标注者只看到: 标注ID / 检测上下文 / 问题
  - 不看到: label / injection / check_item真实值(防泄漏,标注ID打乱)
  - 标注列: annotator_1 / annotator_2 / annotator_3(留空供填写)

同时生成answer_key.csv(分开存放,标注完成后用于对答案算κ)

用法:
  python tools/gen_human_annotation.py              # 生成100条
  python tools/gen_human_annotation.py --size 60    # 生成60条
  python tools/gen_human_annotation.py --calc-kappa # 标注完成后算Cohen's κ
"""
import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EVAL_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
OUT_DIR = BASE / "data/gjb_438c/data_assets/srs_qa_v3/human_annotation"

SEED = 42


def stratified_sample(entries, size):
    """分层抽样: 按四层(TERM/PARAM/LOGIC/GJB)+正负例分层"""
    rng = random.Random(SEED)
    groups = defaultdict(list)
    for e in entries:
        ci = e.get("check_item", "")
        prefix = ci.split("-")[0] if "-" in ci else ci
        label = e.get("label", "")
        groups[(prefix, label)].append(e)

    # 各层配额(按组大小占比分配,保证正负例都覆盖)
    total = len(entries)
    sampled = []
    for key, group in sorted(groups.items()):
        quota = round(size * len(group) / total)
        quota = min(quota, len(group))
        if quota > 0:
            sampled.extend(rng.sample(group, quota))

    # 补足/裁剪到size
    if len(sampled) > size:
        sampled = rng.sample(sampled, size)
    elif len(sampled) < size:
        rest = [e for e in entries if e not in sampled]
        sampled.extend(rng.sample(rest, size - len(sampled)))

    # 打乱顺序+重编号(防标注者猜规律)
    rng.shuffle(sampled)
    return sampled


def gen_package(size):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(EVAL_PATH) as f:
        data = json.load(f)
    entries = data["entries"]

    sampled = stratified_sample(entries, size)

    # 统计
    stats = defaultdict(int)
    for e in sampled:
        ci = e.get("check_item", "")
        prefix = ci.split("-")[0] if "-" in ci else ci
        stats[f"{prefix}-{e['label']}"] += 1
    print(f"抽样 {len(sampled)} 条,分层分布:")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")

    # 标注文件(盲标:不含任何答案信息)
    anno_path = OUT_DIR / "annotation_task.csv"
    with open(anno_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["标注ID", "检测上下文", "问题", "标注者1判断", "标注者1理由", "标注者2判断", "标注者2理由"])
        for i, e in enumerate(sampled, 1):
            w.writerow([
                f"H{i:03d}",
                e.get("rendered_context", ""),
                e.get("question", ""),
                "", "", "", "",  # 留空
            ])

    # 答案key(分开存放)
    key_path = OUT_DIR / "answer_key.csv"
    with open(key_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["标注ID", "eval_id", "check_item", "label", "method", "confidence"])
        for i, e in enumerate(sampled, 1):
            w.writerow([
                f"H{i:03d}",
                e["eval_id"],
                e.get("check_item", ""),
                e.get("label", ""),
                e.get("injection", {}).get("method", ""),
                e.get("confidence", ""),
            ])

    print(f"\n标注文件: {anno_path}")
    print(f"答案key:  {key_path} (标注完成后才可看)")
    print(f"\n标注指南:")
    print(f"  1. 逐条阅读'检测上下文'(某实体在文档中多个位置的记录)")
    print(f"  2. 结合'问题',独立判断各位置之间是否一致")
    print(f"  3. 判断标准: 同一实体在不同位置用了不同的名称/数值/属性或内容矛盾 → inconsistent")
    print(f"     表述不同但语义等价(如0.2秒=200ms) → consistent")
    print(f"  4. 填'标注者1判断'列: consistent 或 inconsistent")


def calc_kappa():
    """标注完成后计算Cohen's κ"""
    anno_path = OUT_DIR / "annotation_task.csv"
    key_path = OUT_DIR / "answer_key.csv"

    with open(anno_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    with open(key_path, encoding="utf-8-sig") as f:
        keys = {r["标注ID"]: r for r in csv.DictReader(f)}

    def cohen_kappa(a, b):
        pairs = [(x, y) for x, y in zip(a, b) if x and y]
        n = len(pairs)
        if n < 2:
            return 0.0
        from collections import Counter
        labels = set(p[0] for p in pairs) | set(p[1] for p in pairs)
        matrix = Counter(pairs)
        po = sum(matrix[(l, l)] for l in labels) / n
        m1 = Counter(p[0] for p in pairs)
        m2 = Counter(p[1] for p in pairs)
        pe = sum((m1[l] / n) * (m2[l] / n) for l in labels)
        return (po - pe) / (1 - pe) if pe < 1 else 1.0

    # 标注者1 vs gold
    a1 = [r.get("标注者1判断", "").strip().lower() for r in rows]
    gold = [keys[r["标注ID"]]["label"].strip().lower() for r in rows]
    a2 = [r.get("标注者2判断", "").strip().lower() for r in rows]

    valid1 = sum(1 for x in a1 if x)
    print(f"标注者1: {valid1}/{len(rows)} 条已标注")
    if valid1:
        agree = sum(1 for x, g in zip(a1, gold) if x and x == g)
        print(f"  vs gold一致率: {agree}/{valid1} ({agree/valid1*100:.1f}%)")
        print(f"  Cohen κ(vs gold): {cohen_kappa(a1, gold):.4f}")

    valid2 = sum(1 for x in a2 if x)
    if valid2:
        print(f"标注者2: {valid2}/{len(rows)} 条已标注")
        agree = sum(1 for x, g in zip(a2, gold) if x and x == g)
        print(f"  vs gold一致率: {agree}/{valid2} ({agree/valid2*100:.1f}%)")
        print(f"  Cohen κ(vs gold): {cohen_kappa(a2, gold):.4f}")
        both = sum(1 for x, y in zip(a1, a2) if x and y)
        if both:
            print(f"  标注者间: {both} 条双标, Cohen κ(1v2): {cohen_kappa(a1, a2):.4f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--calc-kappa", action="store_true")
    args = parser.parse_args()

    if args.calc_kappa:
        calc_kappa()
    else:
        gen_package(args.size)


if __name__ == "__main__":
    main()
