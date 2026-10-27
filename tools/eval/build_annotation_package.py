r"""人工标注包生成(挑战4: gold standard构建).

设计: 50条查询的分层抽样(场景×overlap带×gold大小×标识符型),
每条附gold上下文供人工验证. 三个标注问题:
  Q1 自然度(1-5): 像真实工程师会问的问题吗?
  Q2 答案在gold中(是/部分/否): gold单元确实包含该查询的答案吗?
  Q3 唯一性(是/否): 除gold外, 语料其他位置也含答案吗?

统计协议: 双人独立标注 → Q2的Cohen's κ为主指标(gold效度),
Q3用于多gold完整性审计.

用法: python tools/eval/build_annotation_package.py [--n 50]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"

IDENTIFIER_PAT = re.compile(
    r"图\s*\d|表\s*\d|如图|见图|如下图|如图所示|下图")


def sample_stratified(ds, n_total: int) -> list[dict]:
    """分层抽样: 场景配额 + 场景内协变量分层."""
    corpus = {c["chunk_id"]: c for c in ds["corpus"]}
    pools = {
        "table_deep_v3": [q for q in ds["queries"]
                          if q["scene"] == "table_deep_v3"
                          and q["split"] == "eval"],
        "table_deep_v4": [q for q in ds["queries"]
                          if q["scene"] == "table_deep_v4"
                          and q["split"] == "eval"],
        "image": [q for q in ds["queries"]
                  if q["scene"] == "image" and q["split"] == "eval"],
    }
    quotas = {"table_deep_v3": n_total * 2 // 5,
              "table_deep_v4": n_total * 3 // 10,
              "image": n_total * 3 // 10}

    rng = random.Random(42)
    picked = []
    for scene, quota in quotas.items():
        qs = pools[scene]
        # 场景内分层
        strata: dict[str, list] = defaultdict(list)
        for q in qs:
            ov = q.get("overlap", 0.0)
            if scene == "image":
                key = ("标识符" if IDENTIFIER_PAT.search(q["query"])
                       else "语义")
            else:
                band = "低ov" if ov < 0.1 else (
                    "中ov" if ov < 0.3 else "高ov")
                gkey = "单gold" if len(q["expected"]) == 1 else "多gold"
                key = f"{gkey}-{band}"
            strata[key].append(q)
        # 按层大小比例分配配额(至少1)
        keys = sorted(strata)
        total = sum(len(strata[k]) for k in keys)
        alloc = {}
        for k in keys:
            alloc[k] = max(1, round(quota * len(strata[k]) / total))
        while sum(alloc.values()) > quota and len(keys) > 1:
            biggest = max(keys, key=lambda k: alloc[k])
            if alloc[biggest] > 1:
                alloc[biggest] -= 1
        for k in keys:
            rng.shuffle(strata[k])
            picked.extend(strata[k][:alloc[k]])

    # 附加gold上下文
    out = []
    for q in picked:
        gold_ctx = []
        for cid in q["expected"][:3]:
            c = corpus.get(cid)
            if c:
                gold_ctx.append({
                    "chunk_id": cid,
                    "title": c["title"],
                    "units_sample": c["units"][1:6],
                })
        out.append({
            "query": q["query"],
            "scene": q["scene"],
            "source": q.get("source", ""),
            "overlap": q.get("overlap", 0.0),
            "gold_size": len(q["expected"]),
            "gold_context": gold_ctx,
            "annotations": {"Q1_naturalness": None,
                            "Q2_answer_in_gold": None,
                            "Q3_answer_elsewhere": None},
        })
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    args = ap.parse_args()

    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    package = sample_stratified(ds, args.n)

    outp = V3 / "annotation_package_v1.json"
    outp.write_text(json.dumps({
        "protocol": (f"{len(package)}条分层抽样(seed42); 场景配额 "
                     "v3:40%/v4:30%/image:30%; 场景内按overlap带×gold大小"
                     "×标识符型分层; 双人独立标注; Q2的Cohen κ为主指标"),
        "questions": {
            "Q1_naturalness": "1-5分: 像真实工程师会问的问题吗?",
            "Q2_answer_in_gold": "是/部分/否: gold单元确实包含答案吗?",
            "Q3_answer_elsewhere": "是/否: 除gold外其他位置也含答案吗?",
        },
        "items": package,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # 人类可读标注表
    md_path = (BASE / "docs/srs_project/annotation_sheet_v1.md")
    lines = [
        "# 人工标注表 v1 (50条)",
        "",
        "每条请独立回答: Q1(1-5自然度) / Q2(答案在gold: 是|部分|否)"
        " / Q3(他处也有答案: 是|否)",
        "",
    ]
    for i, it in enumerate(package, 1):
        lines.append(f"## {i}. [{it['scene']}] {it['query']}")
        lines.append(f"- overlap={it['overlap']}, gold={it['gold_size']}个, "
                     f"来源={it['source']}")
        for g in it["gold_context"]:
            lines.append(f"- gold: **{g['title']}** "
                         f"({g['chunk_id'][-12:]})")
            for u in g["units_sample"][:3]:
                lines.append(f"  - {u[:80]}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"标注包: {len(package)}条 → {outp}")
    print(f"标注表: {md_path}")
    from collections import Counter
    dist = Counter(it["scene"] for it in package)
    print(f"场景分布: {dict(dist)}")


if __name__ == "__main__":
    main()
