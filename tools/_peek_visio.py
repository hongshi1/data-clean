import json
from pathlib import Path

d = json.loads(Path(
    "data/gjb_438c/pair_dataset/sc1_usecase_capability/1_001/visio_anchor.json"
).read_text(encoding="utf-8"))
print(json.dumps(d, ensure_ascii=False, indent=1)[:3000])
