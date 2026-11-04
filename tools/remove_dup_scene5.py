"""Remove duplicate scene-5 figure block (the old one without function demo)."""
from __future__ import annotations

import docx
from docx.oxml.ns import qn

DOC = (r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
       r"\msg\file\2026-11\葛宣成 合稿_含截图v5.docx")


def main() -> None:
    doc = docx.Document(DOC)

    # Find old scene-5 block: starts from the body paragraph containing
    # "672条图片问答对" (old description) up to the caption "冲突检测运行截图"
    # The old block was inserted first (lower paragraph index)
    # The new block contains "功能演示" and "672条"

    # Strategy: find caption "图6-6-5-4 场景五冲突检测运行截图" (old, to delete)
    # and work backwards to delete the entire old block (body + image + caption) × 4

    # Old captions (from v4 insertion):
    old_captions = [
        "场景五原始数据分析",
        "场景五QA字段结构化展示",
        "场景五同类样本结论一致性检测",
        "场景五冲突检测运行截图",  # this one is ONLY in old block
    ]

    # New captions:
    new_captions = [
        "场景五图片问答一致性校验功能演示",  # this one is ONLY in new block
    ]

    # Find all paragraphs with 图6-6-5- captions
    cap_positions = []
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t.startswith("图6-6-5-"):
            cap_positions.append((i, t))
    print("All scene-5 captions:")
    for i, t in cap_positions:
        print(f"  [{i}] {t[:60]}")

    # Find the old "冲突检测运行截图" caption index
    old_demo_idx = None
    for i, t in cap_positions:
        if "冲突检测运行截图" in t:
            old_demo_idx = i
    print(f"\nOld block anchor (冲突检测运行截图): {old_demo_idx}")

    if old_demo_idx is None:
        print("No old block found")
        return

    # The old block consists of 4 (body + image + caption) sets
    # They were inserted sequentially, so the old block spans from
    # approximately (old_demo_idx - 11) to old_demo_idx
    # (4 sets × 3 paragraphs = 12, minus 1 for the last caption = 11 back)

    # More precise: find the start of the old block by looking for
    # the body paragraph before the first old caption
    # The old block's first body paragraph starts with "场景五的原始数据为672条图片问答对"
    old_start = None
    for i in range(old_demo_idx - 1, max(0, old_demo_idx - 20), -1):
        t = doc.paragraphs[i].text.strip()
        if "672条图片问答对" in t:
            old_start = i
            break

    if old_start is None:
        # Try finding by looking for the first paragraph before old captions
        # Old block should start right after "结果展示材料建议补充三组真实截图" (scene-5 version)
        for i in range(old_demo_idx, max(0, old_demo_idx - 30), -1):
            t = doc.paragraphs[i].text.strip()
            if "结果展示材料建议补充三组真实截图" in t:
                old_start = i + 1
                break

    print(f"Old block start: {old_start}")

    if old_start is None:
        print("ERROR: could not find old block start")
        return

    # Delete from old_start to old_demo_idx (inclusive)
    # This should be 12 paragraphs (4 × 3)
    to_delete = list(range(old_start, old_demo_idx + 1))
    print(f"Deleting paragraphs {old_start} to {old_demo_idx} "
          f"({len(to_delete)} paragraphs)")

    # Delete in reverse order to preserve indices
    for idx in reversed(to_delete):
        p = doc.paragraphs[idx]
        p._element.getparent().remove(p._element)

    doc.save(DOC)
    print(f"Saved: {DOC}")

    # Verify
    doc2 = docx.Document(DOC)
    remaining = []
    for p in doc2.paragraphs:
        t = p.text.strip()
        if t.startswith("图6-6-5-"):
            remaining.append(t[:50])
    print(f"\nRemaining scene-5 captions: {len(remaining)}")
    for t in remaining:
        print(f"  {t}")

    s1_count = sum(1 for p in doc2.paragraphs if p.text.strip().startswith("图6-6-1-"))
    print(f"Scene-1 captions: {s1_count}")


if __name__ == "__main__":
    main()
