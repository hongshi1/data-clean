import json
from pathlib import Path

# 读取mermaid导出和04号content_list，建立图→表/正文的对应关系
mm = json.loads(Path("data/gjb_438c/anchor_v2/mermaid_export.json")
                .read_text(encoding="utf-8"))
doc04_mm = {k: v for k, v in mm.items() if "04" in k}

# 读取04号content_list获取图标题和对应表格
items = json.loads(Path(
    "data/gjb_438c/mineru_standard/04数据统一访问服务软件需求规格说明-终稿/office/"
    "04数据统一访问服务软件需求规格说明-终稿_content_list.json"
).read_text(encoding="utf-8"))

# 找image块及其邻接的table/text块
print("=== 04号图→邻接表对应关系 ===")
for i, item in enumerate(items):
    if item.get("type") != "image":
        continue
    captions = item.get("image_caption", [])
    caption = captions[0] if captions else "(无标题)"
    # 找前后5个块内的table和text
    context = []
    for j in range(max(0, i-3), min(len(items), i+6)):
        if j == i:
            continue
        other = items[j]
        if other.get("type") == "table":
            tcaps = other.get("table_caption", [])
            tc = tcaps[0] if tcaps else "(表)"
            context.append(f"TABLE[{tc[:30]}]")
        elif other.get("type") == "text":
            t = str(other.get("text", ""))[:50]
            if t.strip():
                context.append(f"TEXT[{t[:30]}]")
    print(f"b{i:03d} | {caption}")
    if context:
        print(f"       邻接: {'; '.join(context[:4])}")
