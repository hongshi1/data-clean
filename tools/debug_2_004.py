# -*- coding: utf-8 -*-
"""调试2_004: flowchart解析为何空steps"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = "data/gjb_438c"
av = json.load(open(f"{BASE}/anchor_v2/anchors_v2.json", encoding="utf-8"))
sm = json.load(open(f"{BASE}/anchor_v2/scene_models.json", encoding="utf-8"))
va = json.load(open(f"{BASE}/pair_dataset/sc2_flowchart_usecase/2_004/visio_anchor.json", encoding="utf-8"))
doc = va["doc"]
print("pair doc:", doc[:20], "embed:", va.get("embed_index"))
idx = None
for si, st in enumerate(av[doc]["structures"]):
    if st.get("embed_index") == va.get("embed_index"):
        idx = si
        break
print("structure idx:", idx)
st = av[doc]["structures"][idx]
print("nodes:")
for n in st["nodes"]:
    print("  {:5s} {:9s} cx={:.2f} cy={:.2f} text={!r}".format(
        n["id"], n["type"], n["cx"], n["cy"], n["text"][:16]))
print("edges:")
for e in st["edges"]:
    print("  {} -> {} via={} src={!r} dst={!r}".format(
        e["src"], e["dst"], e["via"], e["src_text"][:8], e["dst_text"][:8]))
m = sm[doc]["models"][idx]
print("model:", m["_classify"], "stats:", m.get("stats"))
print("steps:", m.get("steps"))
print("main_path:", m.get("main_path"))
