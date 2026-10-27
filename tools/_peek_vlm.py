import json
from pathlib import Path

ocr = json.loads(Path("data/gjb_438c/anchor_v2/scene_ocr_extractions.json")
                 .read_text(encoding="utf-8"))
print("OCR keys:", list(ocr.keys())[:5], "total:", len(ocr))
k = list(ocr.keys())[0]
print(json.dumps(ocr[k], ensure_ascii=False, indent=1)[:600])

mm = json.loads(Path("data/gjb_438c/anchor_v2/mermaid_export.json")
                .read_text(encoding="utf-8"))
print("\nMermaid keys:", list(mm.keys())[:5], "total:", len(mm))
k2 = list(mm.keys())[0]
print(json.dumps(mm[k2], ensure_ascii=False, indent=1)[:600])

sm = json.loads(Path("data/gjb_438c/anchor_v2/scene_models.json")
                .read_text(encoding="utf-8"))
print("\nSceneModels keys:", list(sm.keys())[:5], "total:", len(sm))
k3 = list(sm.keys())[0]
val = sm[k3]
if isinstance(val, dict):
    print("val keys:", list(val.keys()))
    print(json.dumps(val, ensure_ascii=False, indent=1)[:800])
