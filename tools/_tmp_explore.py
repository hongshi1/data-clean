import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
d = json.load(open("data/gjb_438c/pair_dataset_expanded/adjudicated_pairs.json", encoding="utf-8"))
print("total:", d["total"], "| dist:", d["label_dist"])
r = d["pairs"][0]
print("record keys:", list(r.keys()))
for r in d["pairs"]:
    print(f"[{r['llm_label']}/{r['label']}] {r['figure_caption'][:22]} | {r['reason'][:80]}")
print("meta keys:", list(d["meta"].keys()))
