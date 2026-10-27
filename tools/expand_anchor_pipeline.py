"""锚点管线扩容: 从MinerU解析的chunks中提取更多pair_dataset.

数据源: 5231个chunks(1207 table + 381 image + 3643 text)
当前pair_dataset: 366对(仅覆盖部分chunks)
扩容目标: 覆盖所有功能表/接口表/用例表与对应图的配对

方法(路径1: 扩大锚点管线):
  1. 遍历所有table chunks,识别表格类型(功能表/接口表/用例表)
  2. 对每个表格chunk,在同文档中搜索关联的image chunk
  3. 用BGE embedding计算表格内容与图caption的相似度,确定配对
  4. 输出新的pair_dataset条目(表格+图+上下文)
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset"
OUT = BASE / "data/gjb_438c/pair_dataset_expanded"


def classify_table(text: str) -> str:
    """识别表格类型."""
    head = text[:300]
    if "功能" in head and ("名称" in head or "标识" in head or "子功能" in head):
        return "sc1_usecase_capability"
    if "接口" in head and ("名称" in head or "标识" in head or "发送" in head):
        return "sc3_interface_interface"
    if "用例" in head or "Use case" in head or "use case" in head.lower():
        return "sc2_flowchart_usecase"
    if "序号" in head and "步骤" in head:
        return "sc2_flowchart_usecase"
    return "unknown"


def find_matching_images(table_chunk: dict, image_chunks: list[dict],
                         same_doc: bool = True) -> list[dict]:
    """找到与table chunk可能配对的image chunks.
    
    匹配策略(宽松): 同文档 + section前缀匹配(而非精确相等)
    因为table的section通常比image的section更深层(如3.2.1.3.2 vs 3.2.1.3.1)
    """
    doc = table_chunk.get("doc", "")
    section = str(table_chunk.get("section", ""))
    if not section:
        return []
    # 取table section的前3级(如3.2.1.3.2 → 3.2.1)
    parts = section.split(".")
    prefix = ".".join(parts[:3]) if len(parts) >= 3 else section
    candidates = []
    for img in image_chunks:
        if same_doc and img.get("doc") != doc:
            continue
        img_section = str(img.get("section", ""))
        if not img_section:
            continue
        # 前缀匹配: image section是table section的前缀,或前3级相同
        img_parts = img_section.split(".")
        img_prefix = ".".join(img_parts[:3]) if len(img_parts) >= 3 else img_section
        if img_prefix == prefix or section.startswith(img_section) or img_section.startswith(section):
            candidates.append(img)
    return candidates


def main() -> None:
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    table_chunks = [c for c in chunks if c.get("type") == "table"]
    image_chunks = [c for c in chunks if c.get("type") == "image"]

    print(f"chunks: table={len(table_chunks)}, image={len(image_chunks)}")

    # 分类table chunks
    classified = defaultdict(list)
    for tc in table_chunks:
        scene = classify_table(str(tc.get("text", "")))
        if scene != "unknown":
            classified[scene].append(tc)

    print("\n可用的表格chunks(按场景):")
    for scene, tcs in sorted(classified.items()):
        docs = set(str(tc.get("doc", ""))[:2] for tc in tcs)
        print(f"  {scene}: {len(tcs)}个 (来自{len(docs)}份文档)")

    # 与当前pair_dataset对比
    existing = set()
    for scene_dir in PAIR_DIR.iterdir():
        if not scene_dir.is_dir():
            continue
        for pair_dir in scene_dir.iterdir():
            if pair_dir.is_dir():
                meta_path = pair_dir / "meta.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    existing.add((str(meta.get("doc", ""))[:2], str(meta.get("section", ""))))
    print(f"\n当前pair_dataset: {len(existing)}对")

    # 生成新pair(排除已有的)
    new_pairs = []
    for scene, tcs in sorted(classified.items()):
        for tc in tcs:
            doc = str(tc.get("doc", ""))
            section = str(tc.get("section", ""))
            key = (doc[:2], section)
            if key in existing:
                continue  # 跳过已有的

            # 找配对的image
            matched_images = find_matching_images(tc, image_chunks)
            if not matched_images:
                continue

            # 提取表格内容(前500字)
            table_text = str(tc.get("text", ""))[:500]

            for img in matched_images[:1]:  # 每个表格取最近的1个图
                new_pairs.append({
                    "scene": scene,
                    "doc": doc,
                    "section": section,
                    "table_chunk_id": tc.get("chunk_id", ""),
                    "table_text": table_text,
                    "image_chunk_id": img.get("chunk_id", ""),
                    "image_caption": str(img.get("text", ""))[:100],
                    "image_path": str(img.get("image_path", img.get("meta", {}).get("image_path", ""))),
                })

    print(f"\n新增pair: {len(new_pairs)}对")
    by_scene = Counter(p["scene"] for p in new_pairs)
    print(f"按场景: {dict(sorted(by_scene.items()))}")
    by_doc = Counter(str(p["doc"])[:2] for p in new_pairs)
    print(f"按文档: {dict(sorted(by_doc.items()))}")

    # 保存
    OUT.mkdir(parents=True, exist_ok=True)
    out_file = OUT / "expanded_pairs.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"total": len(new_pairs), "pairs": new_pairs}, f, ensure_ascii=False, indent=1)
    print(f"保存 → {out_file}")


if __name__ == "__main__":
    main()
