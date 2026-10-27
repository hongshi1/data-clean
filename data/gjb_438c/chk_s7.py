import json, sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
d = json.loads(Path("C:/Users/12488/Desktop/data_clean/data/gjb_438c/data_assets/evalsets/results/S7_evidence_recall_all.json").read_text(encoding="utf-8"))
for scene, e in d["results"].items():
    print(f"[{scene}] {e['n_queries']}q")
    print(f"  recall: R@1={e['recall']['R@1']:.3f} R@5={e['recall']['R@5']:.3f} MRR={e['recall']['MRR@10']:.3f}")
    if "rerank" in e:
        print(f"  rerank: R@1={e['rerank']['R@1']:.3f} R@5={e['rerank']['R@5']:.3f} MRR={e['rerank']['MRR@10']:.3f} p={e['mcnemar']['p_one_sided']:.1e}")
    if "lexical_only" in e:
        print(f"  lexical: R@1={e['lexical_only']['R@1']:.3f}")
    for k, v in e.get("locked_check", {}).items():
        print(f"  对照{k}: 锁定={v['locked']} 框架={v['framework']} Δ={v['delta']}")
