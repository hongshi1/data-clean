# -*- coding: utf-8 -*-
"""诊断: sc3接口图pair的分类去向 + 流程图空步骤问题"""
import glob
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
BASE = "data/gjb_438c"
sm = json.load(open(f"{BASE}/anchor_v2/scene_models.json", encoding="utf-8"))
av = json.load(open(f"{BASE}/anchor_v2/anchors_v2.json", encoding="utf-8"))

print("=== sc3 pair (28对) 的分类去向 ===")
dist = Counter()
no_match = []
for pd in sorted(glob.glob(f"{BASE}/pair_dataset/sc3_interface_interface/*/visio_anchor.json")):
    pair_id = pd.replace("\\", "/").split("/")[-2]
    va = json.load(open(pd, encoding="utf-8"))
    doc = va["doc"]
    idx = None
    for si, st in enumerate(av.get(doc, {}).get("structures", [])):
        if st.get("embed_index") == va.get("embed_index"):
            idx = si
            break
    if idx is None:
        no_match.append((pair_id, "embed_index未找到结构"))
        continue
    if doc not in sm:
        no_match.append((pair_id, f"doc不在scene_models: {doc[:12]}"))
        continue
    m = sm[doc]["models"][idx]
    dist[m["_classify"]["type"]] += 1
    if m["_classify"]["type"] != "interface_diagram":
        st = av[doc]["structures"][idx]
        tc = Counter(n["type"] for n in st["nodes"])
        texts = [n["text"] for n in st["nodes"] if n["text"]][:6]
        no_match.append((pair_id, f"{m['_classify']['type']} | {dict(tc)} | {texts}"))
print("分类分布:", dict(dist))
for pid, why in no_match[:10]:
    print(f"  {pid}: {why}")

print()
print("=== 流程图空步骤诊断(sc2 pair) ===")
empty_cnt = 0
for pd in sorted(glob.glob(f"{BASE}/pair_dataset/sc2_flowchart_usecase/*/visio_anchor.json")):
    pair_id = pd.replace("\\", "/").split("/")[-2]
    va = json.load(open(pd, encoding="utf-8"))
    doc = va["doc"]
    idx = None
    for si, st in enumerate(av.get(doc, {}).get("structures", [])):
        if st.get("embed_index") == va.get("embed_index"):
            idx = si
            break
    if idx is None or doc not in sm:
        continue
    m = sm[doc]["models"][idx]
    if m["_classify"]["type"] == "flowchart" and m.get("stats", {}).get("n_steps", 0) == 0:
        empty_cnt += 1
        st = av[doc]["structures"][idx]
        tc = Counter(n["type"] for n in st["nodes"])
        if empty_cnt <= 5:
            print(f"  {pair_id}: 节点{len(st['nodes'])} {dict(tc)} "
                  f"steps={m.get('steps', [])[:3]} main_path={m.get('main_path', [])[:4]}")
print(f"流程图空步骤pair数: {empty_cnt}")
