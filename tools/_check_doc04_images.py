import json
from pathlib import Path

mm = json.loads(Path("data/gjb_438c/anchor_v2/mermaid_export.json")
                .read_text(encoding="utf-8"))
doc04 = {k: v for k, v in mm.items() if "04" in k or "数据统一" in k}
print("=== 04号: 64张Visio图全部已解析为Mermaid ===")
for k, v in sorted(doc04.items()):
    print(f"  {v['diagram_type']:15s} | {v['n_nodes']:3d} nodes | {k.split(':')[-1]}")

vlm = json.loads(Path("data/gjb_438c/anchor_v2/scene_vlm_extractions.json")
                 .read_text(encoding="utf-8"))
print(f"\nVLM提取: {len(vlm)} 对(覆盖全文档)")

ocr = json.loads(Path("data/gjb_438c/anchor_v2/scene_ocr_extractions.json")
                 .read_text(encoding="utf-8"))
print(f"OCR提取: {len(ocr)} 对")

sm = json.loads(Path("data/gjb_438c/anchor_v2/scene_models.json")
                .read_text(encoding="utf-8"))
k04 = [k for k in sm if "04" in k][0]
print(f"\n04号 Scene Models: visio_count={sm[k04]['visio_count']}")
for i, m in enumerate(sm[k04]["models"][:3]):
    print(f"  model[{i}] type={m['diagram_type']}")

translations = json.loads(Path("data/gjb_438c/anchor_v2/translations.json")
                          .read_text(encoding="utf-8"))
print(f"\nTranslations: {len(translations)} entries")
k04t = [k for k in translations if "04" in k]
print(f"04号 translations: {len(k04t)} entries")
if k04t:
    print(json.dumps(translations[k04t[0]], ensure_ascii=False, indent=1)[:600])
