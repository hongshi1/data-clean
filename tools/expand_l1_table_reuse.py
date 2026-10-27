"""L1: 表侧复用 — 将未配对的table chunks与同章节image配对, 补充sc1~sc4.

审计方案L1: 当前build_pair_dataset只取同章节第一个匹配表,
改为取所有未用的table+同章节image配对.
预计新增: ~500对(覆盖sc1~sc5全部场景)
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
OUT = BASE / "data/gjb_438c/pair_dataset_items"


def classify_table(text: str) -> str:
    head = text[:300]
    if "功能" in head and ("名称" in head or "标识" in head or "子功能" in head):
        return "sc1"
    if "接口" in head and ("名称" in head or "标识" in head or "发送" in head):
        return "sc3"
    if "用例" in head or "Use case" in head or "use case" in head.lower():
        return "sc2"
    if "步骤" in head or "流程" in head:
        return "sc4"
    if "功能需求" in head or "性能" in head:
        return "sc5"
    return "unknown"


def main() -> None:
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    table_chunks = [c for c in chunks if c.get("type") == "table"]
    image_chunks = [c for c in chunks if c.get("type") == "image"]

    # 当前已用的位置
    used = set()
    for scene_dir in PAIR_DIR.iterdir():
        if not scene_dir.is_dir():
            continue
        for pair_dir in scene_dir.iterdir():
            if not pair_dir.is_dir():
                continue
            meta_p = pair_dir / "meta.json"
            if meta_p.exists():
                meta = json.loads(meta_p.read_text(encoding="utf-8"))
                used.add((meta.get("doc", ""), str(meta.get("section", ""))))

    # 构建doc→sections的image索引
    doc_image_sections = defaultdict(list)
    for ic in image_chunks:
        doc = ic.get("doc", "")
        section = str(ic.get("section", ""))
        doc_image_sections[doc].append(section)

    # 生成新配对
    new_pairs = []
    for tc in table_chunks:
        doc = tc.get("doc", "")
        section = str(tc.get("section", ""))
        if (doc, section) in used:
            continue
        if not doc or not section:
            continue

        # 找同文档、section前缀匹配的image
        candidates = []
        for img_sec in doc_image_sections.get(doc, []):
            # 前缀匹配: table的section和image的section至少前3级相同
            t_parts = section.split(".")
            i_parts = img_sec.split(".")
            t_prefix = ".".join(t_parts[:3]) if len(t_parts) >= 3 else section
            i_prefix = ".".join(i_parts[:3]) if len(i_parts) >= 3 else img_sec
            if t_prefix == i_prefix or section.startswith(img_sec) or img_sec.startswith(section):
                candidates.append(img_sec)

        if not candidates:
            continue

        scene = classify_table(str(tc.get("text", "")))
        if scene == "unknown":
            continue

        # 提取表格标题和内容
        text = str(tc.get("text", ""))
        import re
        title_m = re.search(r"\[表格标题:\s*([^\]]+)\]", text)
        title = title_m.group(1).strip() if title_m else text[:40]

        # 提取表格行(从HTML中)
        rows = re.findall(r"<tr><td[^>]*><p>([^<]+)</p></td>", text)
        # 如果没有HTML行,尝试纯文本行
        if not rows:
            rows = [line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 5][:10]

        new_pairs.append({
            "scene": scene,
            "doc": str(doc)[:2],
            "doc_full": str(doc)[:30],
            "section": section,
            "table_title": title,
            "table_text": text[:500],
            "table_rows": rows[:10],
            "image_sections": candidates[:2],
            "chunk_id": tc.get("chunk_id", ""),
            "source": "L1_table_reuse",
        })

    print(f"原始table chunks: {len(table_chunks)}")
    print(f"已配对位置: {len(used)}")
    print(f"新增配对: {len(new_pairs)}")

    by_scene = Counter(p["scene"] for p in new_pairs)
    print(f"\n按场景: {dict(sorted(by_scene.items()))}")
    by_doc = Counter(p["doc"] for p in new_pairs)
    print(f"按文档: {dict(sorted(by_doc.items()))}")

    # 保存
    OUT.mkdir(parents=True, exist_ok=True)
    out_file = OUT / "l1_table_reuse_pairs.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"total": len(new_pairs), "pairs": new_pairs}, f, ensure_ascii=False, indent=1)
    print(f"\n保存 → {out_file}")

    # 样本
    print("\n样本(各场景):")
    for scene in sorted(by_scene):
        sample = next((p for p in new_pairs if p["scene"] == scene), None)
        if sample:
            print(f"  [{scene}] doc={sample['doc']} section={sample['section']}")
            print(f"    标题: {sample['table_title'][:40]}")
            print(f"    行数: {len(sample['table_rows'])}")
            print(f"    配对图: {sample['image_sections']}")


if __name__ == "__main__":
    main()
