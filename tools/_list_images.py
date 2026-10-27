import json
from pathlib import Path

items = json.loads(Path(
    "data/gjb_438c/mineru_standard/04数据统一访问服务软件需求规格说明-终稿/office/"
    "04数据统一访问服务软件需求规格说明-终稿_content_list.json"
).read_text(encoding="utf-8"))
images = [(i, item) for i, item in enumerate(items) if item.get("type") == "image"]
print("total images:", len(images))
for idx, item in images:
    captions = item.get("image_caption", [])
    caption = captions[0] if captions else "(无标题)"
    print(f"b{idx:03d} | {caption}")
