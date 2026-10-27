# -*- coding: utf-8 -*-
"""召回质量诊断: 用真实QA对探测activate()的失败模式"""
import json
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from algorithms.context_association.context_graph import ContextGraph

cg = ContextGraph()
qa = json.load(open(os.path.join(
    BASE, "data/gjb_438c/data_assets/srs_qa_final.json"), encoding="utf-8"))

# 取sc1/sc2/sc4各8条有evidence的问题
probes = []
for sc in ["1", "2", "4"]:
    n = 0
    for e in qa:
        if str(e.get("scenario")) == sc and e.get("evidence") and n < 8:
            ev = e.get("evidence")
            ev_str = ev if isinstance(ev, str) else json.dumps(ev, ensure_ascii=False)
            probes.append({"q": e["question"], "sc": sc, "ev": ev_str[:60]})
            n += 1
    if len(probes) >= 24:
        break

print(f"探测{len(probes)}条真实QA问题:\n")
stats = {"ok": 0, "no_seed": 0, "weak": 0}
fails = []
for p in probes:
    r = cg.activate(p["q"])
    if not r.get("ok"):
        stats["no_seed"] += 1
        fails.append(("NO_SEED", p["q"][:40]))
        continue
    n_content = sum(len(v) for v in (r.get("groups") or {}).values())
    # 证据命中检查: evidence的章节号出现在激活的TXT/TBL section里
    ev_sec = ""
    for pat in [r"章节[:\s]*(\d+\.\d+(?:\.\d+)*)", r"(\d+\.\d+(?:\.\d+)*)\s*章节"]:
        import re
        m = re.search(pat, p["ev"])
        if m:
            ev_sec = m.group(1)
            break
    hit = False
    if ev_sec:
        for mod in ["TXT", "TBL"]:
            for n in (r["groups"].get(mod) or []):
                if n.get("section") == ev_sec or n.get("section", "").startswith(ev_sec) or ev_sec.startswith(n.get("section", "")):
                    hit = True
                    break
            if hit:
                break
    if hit:
        stats["ok"] += 1
    else:
        stats["weak"] += 1
        fails.append(("NO_HIT" if ev_sec else "NO_EVSEC", p["q"][:36] + " ev:" + p["ev"][:30]))

total = len(probes)
print(f"结果: 种子失败 {stats['no_seed']}/{total} | 证据命中 {stats['ok']} | 未命中/无章节 {stats['weak']}")
hit_rate = stats["ok"] / max(total - stats["no_seed"], 1)
print(f"种子成功率: {(total - stats['no_seed']) / total:.0%} | 有种子时证据命中率: {hit_rate:.0%}\n")
print("失败样例:")
for typ, d in fails[:12]:
    print(f"  [{typ}] {d}")
