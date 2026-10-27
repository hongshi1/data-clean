r"""构建统一测试数据集: 公开NLI集+GJB资产 → 统一二元格式.

规范: docs/srs_project/test_dataset_spec.md
产出: data/gjb_438c/unified_testset/{五源jsonl + INDEX.json}

用法: python tools/build_unified_testset.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

PUB = BASE / "data/gjb_438c/public_nli"
OUT = BASE / "data/gjb_438c/unified_testset"
OUT.mkdir(parents=True, exist_ok=True)

# NLI三分类 → 统一二元 + 细类型
NLI_TO_UNIFIED = {
    "contradiction": ("inconsistent", "NLI-CONTRA"),
    "entailment": ("consistent", "NLI-ENTAIL"),
    "neutral": ("consistent", "NLI-NEUTRAL"),
}


def _write(items: list[dict], name: str) -> dict:
    path = OUT / name
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    return {"file": name, "n": len(items),
            "labels": dict(Counter(x["label"] for x in items))}


def _mk(i: int, source: str, domain: str, split_origin: str, p: str, h: str,
        label: str, label_raw: str, typ: str, contamination: str, meta: dict) -> dict:
    return {"id": f"UT-{source}-{i:05d}", "source": source, "domain": domain,
            "split_origin": split_origin, "premise": p, "hypothesis": h,
            "label": label, "label_raw": label_raw, "type": typ,
            "contamination": contamination, "meta": meta}


def convert_xnli() -> list[dict]:
    items = [json.loads(line) for line in open(PUB / "xnli_zh_std.jsonl", encoding="utf-8") if line.strip()]
    out = []
    for i, x in enumerate(items):
        lab, typ = NLI_TO_UNIFIED[x["gold"]]
        out.append(_mk(i, "xnli_zh", "general", "test", x["premise"], x["hypothesis"],
                       lab, x["gold"], typ, "mdeberta", {}))
    return out


def convert_cmnli() -> list[dict]:
    items = [json.loads(line) for line in open(PUB / "cmnli_std.jsonl", encoding="utf-8") if line.strip()]
    out = []
    for x in items:
        if x["gold"] not in NLI_TO_UNIFIED or not x["premise"] or not x["hypothesis"]:
            continue
        lab, typ = NLI_TO_UNIFIED[x["gold"]]
        out.append(_mk(len(out), "cmnli_dev", "general", "dev", x["premise"], x["hypothesis"],
                       lab, x["gold"], typ, "", {}))
    return out


def convert_ocnli() -> list[dict]:
    num2lab = {0: "entailment", 1: "neutral", 2: "contradiction"}
    out = []
    with open(PUB / "ocnli_test_std.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                raw = num2lab[int(row["label"])]
            except (KeyError, ValueError):
                continue
            if not row["premise"] or not row["hypothesis"]:
                continue
            lab, typ = NLI_TO_UNIFIED[raw]
            out.append(_mk(len(out), "ocnli_test", "general", "test",
                           row["premise"], row["hypothesis"], lab, raw, typ, "erlangshen", {}))
    return out


def convert_gjb_bench() -> list[dict]:
    items = [json.loads(line) for line in open(BASE / "data/gjb_438c/benchmark_full_v2.jsonl", encoding="utf-8")]
    out = []
    for it in (x for x in items if x["split"] == "test"):
        out.append(_mk(len(out), "gjb_bench", "srs_synthetic", "held-out",
                       it["premise"], it["hypothesis"], it["expected_label"],
                       it["expected_label"], it["check_item"], "qlora",
                       {"doc_id": it.get("doc_id"), "scene": it.get("scene"),
                        "mutation_id": it.get("mutation_id")}))
    return out


def convert_gold() -> list[dict]:
    raw = json.loads((BASE / "data/gjb_438c/gold_verbalized_23.json").read_text(encoding="utf-8"))
    tasks = json.loads((BASE / "data/gjb_438c/anchor_sc2/adjudication/adjudication_tasks.json").read_text(encoding="utf-8"))
    gold_tasks = json.loads((BASE / "data/gjb_438c/human_gold/final_gold_86.json").read_text(encoding="utf-8"))["labels"]
    # 重建类型对齐: gold_verbalized按同一过滤顺序生成
    seq = [t for t in tasks if gold_tasks.get(t["task_id"], {}).get("label", "") in ("real_bug", "benign_variation")]
    out = []
    for i, (x, t) in enumerate(zip(raw, seq)):
        real = x["label"] == 1
        out.append(_mk(i, "gjb_gold", "srs_real", "held-out", x["premise"], x["hypothesis"],
                       "inconsistent" if real else "consistent",
                       "real_bug" if real else "benign_variation",
                       t["dtype"], "", {"uc_name": t.get("uc_name"), "task_id": t.get("task_id")}))
    return out


def convert_gold_v2() -> list[dict]:
    """金标v2(357条): 双LLM一致250 + CoT裁决107, 协议见gold_v2_357.json."""
    v2 = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_357.json").read_text(encoding="utf-8"))
    tier1 = json.loads((BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies_v2.json").read_text(encoding="utf-8"))
    out = []
    for i, x in enumerate(v2):
        meta = tier1.get(x["pair"], {})
        uc = meta.get("uc_name", "")
        ts, ds = {}, {}
        for d in meta.get("discrepancies", []):
            if d["evidence"] == x["evidence"]:
                ts, ds = d.get("table_side") or {}, d.get("diag_side") or {}
                break
        p, h = _verbalize(uc, x["dtype"], ts, ds)
        real = x["label"] == "real_bug"
        out.append(_mk(i, "gjb_gold_v2", "srs_real", "held-out", p, h,
                       "inconsistent" if real else "consistent", x["label"],
                       x["dtype"], "",
                       {"uc_name": uc, "task_id": x["tid"], "protocol": x["protocol"]}))
    return out


def _verbalize(uc: str, dtype: str, ts: dict, ds: dict) -> tuple[str, str]:
    if dtype == "ORDER_CONFLICT":
        return (f"表格规定{uc}用例的执行顺序为{ts.get('seq', '依次执行')}。",
                f"流程图规定的执行顺序为{ds.get('edge', '相反方向')}，与表格不一致。")
    if dtype == "STEP_MISSING":
        return (f"{uc}用例的表格规定步骤「{str(ts.get('text', ''))[:80]}」。",
                "流程图中没有与该步骤对应的节点。")
    if dtype == "ACTOR_MISSING":
        return (f"{uc}用例的表格规定参与者为「{str(ts.get('text', ''))[:30]}」。",
                "流程图中没有绘制参与者节点。")
    if dtype == "EXC_MISSING":
        return (f"{uc}用例的表格规定异常流{ts.get('eid', 'E1')}「{str(ts.get('text', ''))[:80]}」。",
                "流程图中没有该异常分支。")
    return (f"流程图中包含节点「{str(ds.get('text', ''))[:80]}」。",
            f"{uc}用例的表格中没有对应的步骤描述。")


def convert_md_gold() -> list[dict]:
    """多文档金标(577条): scene_tier1的579条差异, CoT裁决, 16文档4场景."""
    res = json.loads((BASE / "data/gjb_438c/human_gold/md_cot_adjudication.json").read_text(encoding="utf-8"))
    out = []
    i = 0
    for qid, v in sorted(res.items()):
        if v["label"] not in ("real_bug", "benign_variation"):
            continue
        real = v["label"] == "real_bug"
        out.append(_mk(i, "md_gold", "srs_real", "held-out", v["premise"], v["hypothesis"],
                       "inconsistent" if real else "consistent", v["label"], v["dtype"], "",
                       {"doc": v["doc"], "scene": v["scene"], "protocol": "cot-1", "qid": qid}))
        i += 1
    return out


def main() -> None:
    index = {"spec": "docs/srs_project/test_dataset_spec.md", "sources": {}}
    for name, fn in [("xnli_zh.jsonl", convert_xnli), ("cmnli_dev.jsonl", convert_cmnli),
                     ("ocnli_test.jsonl", convert_ocnli), ("gjb_bench_test.jsonl", convert_gjb_bench),
                     ("gjb_gold.jsonl", convert_gold), ("gjb_gold_v2.jsonl", convert_gold_v2),
                     ("md_gold.jsonl", convert_md_gold)]:
        src_name = name.replace(".jsonl", "")
        items = [dict(it, source=src_name, id=f"UT-{src_name}-{i:05d}")
                 for i, it in enumerate(fn())]
        info = _write(items, name)
        index["sources"][name.replace(".jsonl", "")] = info
        print(f"{name}: {info['n']}条 {info['labels']}")
    index["total"] = sum(s["n"] for s in index["sources"].values())
    with open(OUT / "INDEX.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"合计: {index['total']}条 → {OUT}")


if __name__ == "__main__":
    main()
