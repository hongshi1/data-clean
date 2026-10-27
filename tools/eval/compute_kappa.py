r"""人工标注的Cohen's κ计算(gold效度闭环, 修复A7的配套工具).

输入: 两份已填写的标注JSON(基于V3/annotation_package_v1.json的结构,
annotations字段填入Q1/Q2/Q3).
统计:
  - Q2(答案在gold: 是/部分/否)的Cohen's κ(加权, 部分计半对)与裸一致率
  - Q1自然度均值, Q3唯一性比例
判定: κ>=0.7 gold效度充分; 0.4-0.7需修订分歧条目; <0.4 gold体系存疑.

用法:
    python tools/eval/compute_kappa.py 标注A.json 标注B.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def kappa(labels_a: list, labels_b: list) -> float:
    """Cohen's κ(类别数任意)."""
    cats = sorted(set(labels_a) | set(labels_b))
    n = len(labels_a)
    if n == 0:
        return 0.0
    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    pa = {c: labels_a.count(c) / n for c in cats}
    pb = {c: labels_b.count(c) / n for c in cats}
    pe = sum(pa[c] * pb[c] for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sys.stdout.reconfigure(encoding="utf-8")
    a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    b = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    items_a = {it["query"]: it.get("annotations", {}) for it in a["items"]}
    items_b = {it["query"]: it.get("annotations", {}) for it in b["items"]}
    common = [q for q in items_a if q in items_b
              and items_a[q].get("Q2_answer_in_gold")
              and items_b[q].get("Q2_answer_in_gold")]
    if not common:
        print("无共同已标注条目(检查两文件的annotations字段)")
        sys.exit(1)
    qa = [items_a[q]["Q2_answer_in_gold"] for q in common]
    qb = [items_b[q]["Q2_answer_in_gold"] for q in common]
    k = kappa(qa, qb)
    agree = sum(1 for x, y in zip(qa, qb) if x == y) / len(common)
    print(f"共同条目: {len(common)}")
    print(f"Q2(答案在gold) Cohen's κ = {k:.3f}")
    print(f"裸一致率 = {agree:.3f}")
    # 部分计半对的加权κ(是=2, 部分=1, 否=0)
    wm = {"是": 2, "部分": 1, "否": 0}
    if all(x in wm and y in wm for x, y in zip(qa, qb)):
        va = [wm[x] for x in qa]
        vb = [wm[y] for y in qb]
        # 二次加权κ
        n = len(va)
        num = sum((va[i] - vb[i]) ** 2 for i in range(n))
        ma = sum(va) / n
        mb = sum(vb) / n
        den = 2 * ((ma - mb) ** 2 + (sum((v - ma) ** 2 for v in va) / n
                                     + sum((v - mb) ** 2 for v in vb) / n) / 2)
        qk = 1 - num / den if den > 0 else 1.0
        print(f"Q2二次加权κ = {qk:.3f}")
    # Q1/Q3概览
    q1s = [items_a[q].get("Q1_naturalness") for q in common
           if items_a[q].get("Q1_naturalness")]
    if q1s:
        print(f"Q1自然度均值(A) = {sum(q1s)/len(q1s):.2f}/5")
    q3s = [items_a[q].get("Q3_answer_elsewhere") for q in common
           if items_a[q].get("Q3_answer_elsewhere")]
    if q3s:
        yes = sum(1 for x in q3s if x == "是")
        print(f"Q3他处也有答案 = {yes}/{len(q3s)} ({yes/len(q3s):.0%})"
              f" — 多gold完整性的旁证")
    verdict = ("gold效度充分(κ>=0.7)" if k >= 0.7 else
               "需修订分歧条目(0.4<=κ<0.7)" if k >= 0.4 else
               "gold体系存疑(κ<0.4)")
    print(f"\n判定: {verdict}")


if __name__ == "__main__":
    main()
