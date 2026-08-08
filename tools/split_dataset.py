#!/usr/bin/env python3
"""
数据集划分 — 文档级隔离(8份train/8份test) + 指令分组去重

用法: python tools/split_dataset.py
输出: data/gjb_438c/data_assets/splits/*.json
"""
import json
import random
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ASSETS = BASE / "data/gjb_438c/data_assets"

TRAIN_DOCS = ['01', '02', '03', '04', '05', '06', '07', '08']
TEST_DOCS = ['09', '10', '11', '12', '13', '14', '15', '16']

random.seed(42)


def doc_key(q):
    return (q.get('doc_ref') or '')[:2]


def main():
    native = json.loads((ASSETS / "native_qa_pairs.json").read_text())
    ext = json.loads((ASSETS / "external_qa_pairs.json").read_text())

    # 评测集: 排除extract标记
    eval_native = [q for q in native if q.get('task') != 'extract']

    train = [q for q in eval_native if doc_key(q) in TRAIN_DOCS]
    test = [q for q in eval_native if doc_key(q) in TEST_DOCS]

    # 跨文档的QA(doc_ref缺失)归入test
    orphan = [q for q in eval_native if doc_key(q) not in TRAIN_DOCS + TEST_DOCS]
    test.extend(orphan)

    # 指令分组隔离检查: 同一instruction不应跨split
    train_insts = {q['instruction'] for q in train}
    test_insts = {q['instruction'] for q in test}
    overlap = train_insts & test_insts
    if overlap:
        print(f"⚠️ 指令跨split重叠: {len(overlap)}组")
        for i in list(overlap)[:5]:
            print(f"  {i[:60]}")
    else:
        print("✅ 指令隔离: 无跨split重叠")

    # 按层统计
    def stats(qs, name):
        pos = sum(1 for q in qs if q['label'] == 'positive')
        layers = Counter(q.get('layer') for q in qs)
        sc = Counter(q.get('scenario') for q in qs)
        print(f"{name}: {len(qs)}条 (正{pos}/负{len(qs)-pos})")
        print(f"  layer: {dict(layers)}")
        print(f"  场景: {dict(sorted(sc.items(), key=lambda x: str(x[0])))}")

    stats(train, "TRAIN(01-08)")
    stats(test, "TEST(09-16)")

    # 保存
    out_dir = ASSETS / "splits"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "native_train.json").write_text(json.dumps(train, ensure_ascii=False, indent=2))
    (out_dir / "native_test.json").write_text(json.dumps(test, ensure_ascii=False, indent=2))
    (out_dir / "external_test.json").write_text(json.dumps(ext, ensure_ascii=False, indent=2))
    print(f"\n已保存到 {out_dir}")


if __name__ == "__main__":
    main()
