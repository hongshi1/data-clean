# -*- coding: utf-8 -*-
"""接口图结构分析: 从sc3 pair锚点找接口图样例"""
import glob
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

# 1. sc3 pair锚点样例
for p in sorted(glob.glob("data/gjb_438c/pair_dataset/sc3_interface_interface/*/visio_anchor.json"))[:3]:
    a = json.load(open(p, encoding="utf-8"))
    print(f"=== {a['pair_id']} ({a['doc'][:10]}) conf={a.get('mapping_confidence')} ===")
    tc = Counter(n["type"] for n in a.get("nodes", []))
    print("  节点类型:", dict(tc), "| 边:", len(a.get("edges", [])))
    for n in a.get("nodes", [])[:14]:
        print("  node {:5s} {:9s} cx={:.2f} cy={:.2f} w={:.2f} h={:.2f} text={!r}".format(
            n["id"], n["type"], n["cx"], n["cy"], n["w"], n["h"], n["text"][:18]))
    for e in a.get("edges", [])[:14]:
        print("  edge {}({!r}) -> {}({!r}) label={!r}".format(
            e["src"], e["src_text"][:10], e["dst"], e["dst_text"][:10], e["label"][:14]))
    print()

# 2. figure_index中接口图的section分布 → 从anchors_v2找对应结构
s0 = json.load(open("data/gjb_438c/data_assets/stage0_assets.json", encoding="utf-8"))
iface_secs = {}
for doc, figs in s0["figure_index"].items():
    for f in figs:
        if f.get("type") == "interface":
            iface_secs.setdefault(doc, []).append((f["fig_num"], f["section"], f["caption"]))
print("=== 接口图分布(前5文档) ===")
for doc, lst in list(iface_secs.items())[:5]:
    print(f"  {doc[:16]}: {len(lst)}张 如 {lst[:2]}")
