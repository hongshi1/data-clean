import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
d = json.load(open("data/gjb_438c/data_assets/real_doc_findings.json", encoding="utf-8"))
print("=== enumeration_conflict (gold对应项) ===")
for f in d["findings"]:
    if f["type"] == "enumeration_conflict":
        print("[%s] %s" % (f["severity"], f["where"]))
        print("  %s" % f["desc"])
        for e in f["evidence"]:
            print("    %s" % e[:95])
        print()
print("=== id_segment_anomaly 前6条 ===")
n = 0
for f in d["findings"]:
    if f["type"] == "id_segment_anomaly":
        n += 1
        print("[%s] %s" % (f["where"], f["desc"]))
        print("    %s" % f["evidence"][1][:90])
        if n >= 6:
            break
print()
print("=== text_vs_graph 抽查2条(评估噪声) ===")
n = 0
for f in d["findings"]:
    if f["type"] == "text_vs_graph":
        n += 1
        print("[%s] %s" % (f["where"], f["desc"][:80]))
        if n >= 2:
            break
