#!/usr/bin/env python3
"""
Image-Text Matcher v3
从MinerU Markdown中提取图片引用，匹配图片与文字描述。

匹配策略:
  1. 在MD中搜索 ![](images/xxx.jpg) 引用
  2. 下一行通常是 "Figure N. 标题" 或 "图N 标题" (caption)
  3. 上一段是引用该图的文字 (context)
  4. 对无引用的图片，用VLM描述
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent


def match_images_in_md(md_path: Path) -> list:
    """从MinerU Markdown中提取图片-文字匹配。"""
    content = md_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    
    matches = []
    
    # Find all ![](images/xxx.jpg) references
    img_pattern = re.compile(r'!\[([^\]]*)\]\((images/[^)]+)\)')
    
    for i, line in enumerate(lines):
        match = img_pattern.search(line)
        if not match:
            continue
        
        alt_text = match.group(1).strip()
        img_path = match.group(2).strip()
        
        # Extract caption (next non-empty line)
        caption = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            next_line = lines[j].strip()
            if next_line and not next_line.startswith("!"):
                caption = next_line
                break
        
        # Extract figure number from caption
        fig_num = None
        fig_patterns = [
            r"Figure\s+(\d+)",
            r"Fig\.\s*(\d+)",
            r"^图\s*(\d+)",
            r"^(\d+)\.",
        ]
        for pattern in fig_patterns:
            m = re.search(pattern, caption)
            if m:
                fig_num = int(m.group(1))
                break
        
        # Extract context (previous non-empty paragraphs, up to 5 lines)
        context_before = []
        for j in range(i - 1, max(i - 10, -1), -1):
            prev_line = lines[j].strip()
            if prev_line:
                context_before.insert(0, prev_line)
                if len(context_before) >= 3:
                    break
        
        context_text = "\n".join(context_before)
        
        # Extract context after (up to 3 lines)
        context_after = []
        for j in range(i + 1, min(i + 6, len(lines))):
            next_line = lines[j].strip()
            if next_line and not next_line.startswith("!["):
                context_after.append(next_line)
                if len(context_after) >= 2:
                    break
        
        # Determine image type from caption
        img_type = "unknown"
        caption_lower = caption.lower()
        if any(kw in caption_lower for kw in ["block diagram", "architecture", "框图", "架构"]):
            img_type = "architecture_diagram"
        elif any(kw in caption_lower for kw in ["flow", "流程", "sequence", "时序"]):
            img_type = "flowchart"
        elif any(kw in caption_lower for kw in ["state", "状态"]):
            img_type = "state_diagram"
        elif any(kw in caption_lower for kw in ["interface", "接口"]):
            img_type = "interface_diagram"
        elif any(kw in caption_lower for kw in ["data", "数据"]):
            img_type = "data_diagram"
        elif any(kw in caption_lower for kw in ["context", "上下文"]):
            img_type = "context_diagram"
        elif caption:
            img_type = "figure"
        else:
            img_type = "unnamed"
        
        # Get full image file path
        full_img_path = md_path.parent / img_path
        
        matches.append({
            "image_index": len(matches) + 1,
            "image_file": os.path.basename(img_path),
            "image_path": str(full_img_path),
            "image_exists": full_img_path.exists(),
            "alt_text": alt_text if alt_text else None,
            "caption": caption[:200] if caption else None,
            "figure_number": fig_num,
            "image_type": img_type,
            "context_before": context_text[:300] if context_text else None,
            "context_after": "\n".join(context_after)[:200] if context_after else None,
            "md_line": i + 1,
            "has_caption": bool(caption),
            "has_context": bool(context_text),
        })
    
    return matches


def process_all_documents():
    """处理所有有MinerU MD的文档。"""
    print("=" * 60)
    print("Image-Text Matcher v3")
    print("=" * 60)
    
    OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "image_text_matches"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all MinerU MD files
    search_dirs = [
        REPO_ROOT / "data" / "gjb_438c" / "mineru_srs",
        REPO_ROOT / "data" / "gjb_438c" / "srs_collection",
    ]
    
    all_md_files = []
    for search_dir in search_dirs:
        if search_dir.exists():
            # Find all .md files in auto/ directories (MinerU output)
            for md in search_dir.rglob("auto/*.md"):
                # Skip if no images directory
                img_dir = md.parent / "images"
                if img_dir.exists() and any(img_dir.glob("*.jpg")):
                    all_md_files.append(md)
    
    # Also find original student MDs with image references
    collection = REPO_ROOT / "data" / "gjb_438c" / "srs_collection"
    for md in collection.rglob("*.md"):
        if "mineru_parsed" not in str(md):
            try:
                content = md.read_text("utf-8")
                if "![" in content:
                    all_md_files.append(md)
            except:
                pass
    
    # Deduplicate
    all_md_files = list(set(all_md_files))
    
    print(f"\nFound {len(all_md_files)} MD files with potential images\n")
    
    all_results = []
    total_images = 0
    total_with_caption = 0
    total_with_context = 0
    total_with_fig_num = 0
    
    for i, md_path in enumerate(sorted(all_md_files)):
        matches = match_images_in_md(md_path)
        
        if not matches:
            continue
        
        # Determine document info
        rel_path = md_path.relative_to(REPO_ROOT) if md_path.is_relative_to(REPO_ROOT) else md_path
        doc_name = md_path.stem[:50]
        is_mineru = "mineru_parsed" in str(md_path) or "mineru_srs" in str(md_path)
        
        result = {
            "doc_name": doc_name,
            "md_path": str(rel_path),
            "is_mineru_output": is_mineru,
            "total_images": len(matches),
            "images_with_caption": sum(1 for m in matches if m["has_caption"]),
            "images_with_context": sum(1 for m in matches if m["has_context"]),
            "images_with_fig_num": sum(1 for m in matches if m["figure_number"]),
            "image_types": {},
            "matches": matches,
        }
        
        # Count image types
        for m in matches:
            t = m["image_type"]
            result["image_types"][t] = result["image_types"].get(t, 0) + 1
        
        all_results.append(result)
        total_images += len(matches)
        total_with_caption += result["images_with_caption"]
        total_with_context += result["images_with_context"]
        total_with_fig_num += result["images_with_fig_num"]
        
        print(f"  [{len(all_results):3d}] {doc_name[:50]:52s} {len(matches):>3} imgs, {result['images_with_caption']:>3} captions")
        
        # Save individual result
        (OUTPUT_DIR / f"{doc_name[:50]}_matches.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), "utf-8"
        )
    
    # Summary
    summary = {
        "analysis_date": datetime.now().isoformat(),
        "total_documents": len(all_results),
        "total_images": total_images,
        "images_with_caption": total_with_caption,
        "images_with_context": total_with_context,
        "images_with_figure_number": total_with_fig_num,
        "caption_rate": round(total_with_caption / max(total_images, 1), 2),
        "context_rate": round(total_with_context / max(total_images, 1), 2),
        "documents": [
            {
                "doc_name": r["doc_name"],
                "total_images": r["total_images"],
                "images_with_caption": r["images_with_caption"],
                "images_with_context": r["images_with_context"],
                "image_types": r["image_types"],
                "is_mineru": r["is_mineru_output"],
            }
            for r in all_results
        ],
    }
    
    (OUTPUT_DIR / "_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), "utf-8"
    )
    
    print(f"\n{'=' * 60}")
    print("IMAGE-TEXT MATCHING COMPLETE")
    print(f"  Documents with images: {len(all_results)}")
    print(f"  Total images: {total_images}")
    print(f"  With caption: {total_with_caption} ({summary['caption_rate']:.0%})")
    print(f"  With context: {total_with_context} ({summary['context_rate']:.0%})")
    print(f"  With figure number: {total_with_fig_num}")
    print(f"  Output: {OUTPUT_DIR}")
    
    # Print top documents
    print(f"\nTop 10 documents by image count:")
    sorted_results = sorted(all_results, key=lambda x: -x["total_images"])
    for r in sorted_results[:10]:
        print(f"  {r['doc_name'][:50]:52s} {r['total_images']:>3} imgs, {r['images_with_caption']:>3} captions, types={r['image_types']}")
    
    return all_results


if __name__ == "__main__":
    process_all_documents()
