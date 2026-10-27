r"""synth_s1源级切分 + 评测集精简(修复源级泄漏).

问题(v2026-10-13诊断):
  - 5418条仅702唯一源约束, 每源7.7次(T1/T2/T3×标签全枚举)
  - 旧gate按type分层切 → 100%源级泄漏(gate同源变体在训练集)
  - v19 gate 0.991被污染(可能只是记住源值)

本工具:
  1. 源级group split: 702源 → train_pool(90%) + gate(10%), 源完全独立
  2. 训练池: 保留表面变体对(领域等价约定监督信号), 按族配额采样1600条
  3. gate: 70源全部变体(~540条), 新源领域等价约定泛化测试
  4. 评测集精简: 每源每标签1条(表面随机) ≈1400条
输出: data/gjb_438c/synth_s1_split.json
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

SEED = 42
TRAIN_FRAC = 0.9
SYNTH_QUOTA_TOTAL = 1600


def main() -> None:
    rng = random.Random(SEED)
    s1 = json.loads((BASE / "data/gjb_438c/synth_s1_pairs.json").read_text(encoding="utf-8"))["pairs"]

    # 1. 按源约束分组
    by_src = defaultdict(list)
    for p in s1:
        src = str(p.get("source_constraint", ""))[:50]
        by_src[src].append(p)
    n_src = len(by_src)
    print(f"源约束: {n_src}个, 总条目{len(s1)}(每源均{len(s1) / n_src:.1f}条)")

    # 2. 源级group split
    srcs = sorted(by_src.keys())
    rng.shuffle(srcs)
    n_train_src = int(n_src * TRAIN_FRAC)
    train_srcs = set(srcs[:n_train_src])
    gate_srcs = set(srcs[n_train_src:])
    gate = [p for p in s1 if str(p.get("source_constraint", ""))[:50] in gate_srcs]
    pool = [p for p in s1 if str(p.get("source_constraint", ""))[:50] in train_srcs]
    print(f"源级切分: 训练池{len(train_srcs)}源({len(pool)}条) + gate{len(gate_srcs)}源({len(gate)}条)")
    print(f"源重叠: {len(train_srcs & gate_srcs)} (必须为0)")

    # 3. 训练采样: 族配额1600条(保留领域等价约定表面信号: 同源T1/T2变体可在同一训练集)
    quota = {"PARAM-01": 0.40, "PARAM-03": 0.25}
    rest = [t for t in {p["type"] for p in pool} if t not in quota]
    for t in rest:
        quota[t] = (1.0 - sum(quota.values())) / len(rest)
    picked = []
    for t, share in sorted(quota.items()):
        tp = [p for p in pool if p["type"] == t]
        rng.shuffle(tp)
        take = tp[:int(SYNTH_QUOTA_TOTAL * share)]
        picked.extend(take)
        print(f"  {t}: 配额{share:.0%}→取{len(take)}/{len(tp)}")
    print(f"训练采样: {len(picked)}条")

    # 4. 评测集精简: 每源每标签1条(表面随机)
    eval_set = []
    for src, pairs in by_src.items():
        by_label = defaultdict(list)
        for p in pairs:
            by_label[p["label"]].append(p)
        for label, lp in by_label.items():
            eval_set.append(rng.choice(lp))
    print(f"评测精简集: {len(eval_set)}条(每源每标签1条)")
    print(f"  标签: {dict(Counter(p['label'] for p in eval_set))}")
    print(f"  类型: {dict(Counter(p['type'] for p in eval_set))}")

    out = {
        "meta": {
            "fix": "源级group split(修复gate源泄漏); 评测集每源每标签1条",
            "seed": SEED, "n_sources": n_src,
            "train_srcs": len(train_srcs), "gate_srcs": len(gate_srcs),
            "note": "gate的源约束从未出现在训练池; 训练采样保留同源表面变体(领域等价约定信号)"},
        "train_sample": picked,
        "gate": gate,
        "eval_minimal": eval_set,
    }
    out_path = BASE / "data/gjb_438c/synth_s1_split.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存 → {out_path}")


if __name__ == "__main__":
    main()
