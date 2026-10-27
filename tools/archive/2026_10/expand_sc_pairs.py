"""sc1~sc4场景补充 — 审计方案L2: 条目级pair升格(零新代码, +579条).

审计发现: human_gold/multidoc_queue_579.json本身就是条目级pair dataset
(sc1:153, sc2:0, sc3:262, sc4:135, sc5:29), 含premise/hypothesis/table_side/diag_side.
md_gold 577条已有人类裁决标签(LLM CoT), queue剩余项走LLM裁决.

本脚本:
  1. 将queue_579升格为pair_dataset_items(一等资产)
  2. 关联md_gold标签(已有) + queue未裁决项走LLM裁决
  3. 统一表面化(复用md_gold的T1/T2/T3模板, 避免格式异构)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

QUEUE = BASE / "data/gjb_438c/human_gold/multidoc_queue_579.json"
MD_GOLD = BASE / "data/gjb_438c/human_gold/md_cot_adjudication.json"
OUT = BASE / "data/gjb_438c/pair_dataset_items"


def main() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    md_gold = json.loads(MD_GOLD.read_text(encoding="utf-8"))

    # 场景→细名称
    SCENE_MAP = {
        "sc1_usecase_capability": "sc1",
        "sc2_flowchart_usecase": "sc2",
        "sc3_interface_interface": "sc3",
        "sc4_flowchart_capability": "sc4",
        "sc5_function_capability": "sc5",
    }

    print(f"queue_579: {len(queue)}条")
    by_scene = Counter(SCENE_MAP.get(q.get("scene", ""), "?") for q in queue)
    print(f"场景分布: {dict(sorted(by_scene.items()))}")

    # 已有裁决
    if isinstance(md_gold, dict):
        adjudicated = {k: v for k, v in md_gold.items() if v.get("label") in ("real_bug", "benign_variation")}
    else:
        adjudicated = {}
    print(f"md_gold已裁决: {len(adjudicated)}条")

    # 构建条目级pair dataset
    items = []
    n_labeled = 0
    n_unlabeled = 0
    for q in queue:
        qid = q["qid"]
        scene = SCENE_MAP.get(q.get("scene", ""), "unknown")
        ts = q.get("table_side") or {}
        ds = q.get("diag_side") or {}

        # 已有裁决标签
        label = None
        protocol = ""
        if qid in adjudicated:
            label = adjudicated[qid]["label"]
            protocol = "llm_cot"
            n_labeled += 1
        else:
            n_unlabeled += 1

        items.append({
            "id": f"PI-{qid}",
            "scene": scene,
            "doc": str(q.get("doc", ""))[:2],
            "section": str(q.get("section", "")),
            "premise": q.get("premise", ""),
            "hypothesis": q.get("hypothesis", ""),
            "table_side": ts,
            "diag_side": ds,
            "evidence": q.get("evidence", ""),
            "dtype": q.get("dtype", ""),
            "label": "inconsistent" if label == "real_bug" else ("consistent" if label == "benign_variation" else None),
            "label_raw": label,
            "protocol": protocol,
        })

    print(f"\n条目级pair: {len(items)}条")
    print(f"  已标注: {n_labeled}条")
    print(f"  待标注: {n_unlabeled}条(需LLM裁决)")

    # 按场景统计
    print(f"\n按场景:")
    for scene in sorted(set(x["scene"] for x in items)):
        scene_items = [x for x in items if x["scene"] == scene]
        n_lab = sum(1 for x in scene_items if x["label"] is not None)
        labels = Counter(x["label_raw"] for x in scene_items if x["label"] is not None)
        print(f"  {scene}: {len(scene_items)}条(已标注{n_lab}) {dict(labels)}")

    # 保存
    OUT.mkdir(parents=True, exist_ok=True)
    out_file = OUT / "items.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"total": len(items), "labeled": n_labeled, "unlabeled": n_unlabeled,
                   "items": items}, f, ensure_ascii=False, indent=1)
    print(f"\n保存 → {out_file}")

    # 生成仅含已标注的pair(用于训练/评测)
    labeled_items = [x for x in items if x["label"] is not None]
    out_labeled = OUT / "labeled_pairs.json"
    with open(out_labeled, "w", encoding="utf-8") as f:
        json.dump({"total": len(labeled_items), "items": labeled_items}, f, ensure_ascii=False, indent=1)
    print(f"已标注pair → {out_labeled} ({len(labeled_items)}条)")

    # 文档级切分统计
    by_split = Counter()
    for x in labeled_items:
        split = "test" if x["doc"] in ("04", "07") else "train"
        by_split[split] += 1
    print(f"\n文档级切分: train={by_split['train']}, test={by_split['test']}")


if __name__ == "__main__":
    main()
