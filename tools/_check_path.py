from pathlib import Path

p = Path("data") / "gjb_438c" / "runs" / "review_qa_with_glm53_582b51e5_20261021_145212" / "final_labels.jsonl"
print("exists:", p.exists())
if not p.exists():
    # Find the actual run directory
    for d in (Path("data") / "gjb_438c" / "runs").iterdir():
        if "review" in d.name:
            for f in d.iterdir():
                if "final_labels" in f.name:
                    print("actual:", f)
