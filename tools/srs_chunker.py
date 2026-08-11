#!/usr/bin/env python3
"""SRS结构化切片器 (Chunker)

学习自:
- GraphRAG TokenTextSplitter: token级滑动窗口 + chunk_size + chunk_overlap
- RAPTOR split_text: 句子级边界感知 + max_tokens + overlap
- GraphRAG add_metadata: metadata前缀注入, 保留切片上下文

针对SRS优化:
1. 结构边界优先: 章节/表格/图片作为天然切片边界(不跨边界切)
2. 表格不切分: 表格是完整语义单元(一个表格行=一个需求), 整体为一个chunk
3. metadata注入: 每个chunk带 doc/section/type/anchor, 保证切片可溯源
4. 层级设计: chunk → section聚合 → 章节摘要, 支持层级检索

输出: srs_chunks.json (数据集)
"""
import json
import os
import re
import glob

MINERU = "data/gjb_438c/mineru_standard"
OUT_DIR = "data/gjb_438c/data_assets/chunks"


def num_tokens(text: str) -> int:
    """token估算: 中文按1字≈1token, 英文按4字符≈1token"""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = len(re.sub(r"[\u4e00-\u9fff\s]", "", text))
    return cjk + other // 4


def split_on_tokens(text: str, chunk_size: int = 500, overlap: int = 50):
    """GraphRAG式token滑动窗口切片"""
    if num_tokens(text) <= chunk_size:
        return [text]
    # 句子边界优先(中文标点)
    parts = re.split(r"(?<=[。；;])", text)
    chunks, cur, cur_len = [], [], 0
    for p in parts:
        p_len = num_tokens(p)
        if cur_len + p_len > chunk_size and cur:
            chunks.append("".join(cur))
            # 重叠: 保留尾部句子
            tail = "".join(cur)[-overlap * 4:]
            cur, cur_len = [tail], num_tokens(tail)
        cur.append(p)
        cur_len += p_len
    if cur:
        chunks.append("".join(cur))
    return chunks


def section_of(item, current_section):
    """从text item中跟踪章节号"""
    if item.get("type") == "text":
        m = re.match(r"^(\d+(?:\.\d+)*)\s+", str(item.get("text", "")).strip())
        if m:
            return m.group(1)
    return current_section


def chunk_document(doc_name, content_list):
    """将一个文档的content_list切分为chunks"""
    chunks = []
    current_section = ""
    for i, item in enumerate(content_list):
        if not isinstance(item, dict):
            continue
        itype = item.get("type")
        if itype in ("footer", "index"):
            continue
        current_section = section_of(item, current_section)

        if itype == "table":
            # 表格整体为一个chunk(完整语义单元)
            body = item.get("table_body", "")
            cap = " ".join(item.get("table_caption", []))
            if not body and not cap:
                continue
            chunks.append({
                "doc": doc_name,
                "chunk_id": f"{doc_name}_T{i:04d}",
                "type": "table",
                "section": current_section,
                "text": f"[表格标题: {cap}]\n{body}" if cap else body,
                "table_caption": cap,
                "page": item.get("page_idx"),
                "anchor": item.get("anchor", ""),
                "meta": {"caption": cap, "has_requirement_id": bool(re.search(r"[A-Z]{4,8}(?:-\w+){2,}", body))},
            })
        elif itype == "text":
            text = item.get("text", "")
            level = item.get("text_level", 0)
            if not text.strip():
                continue
            # 长文本按token滑动窗口切
            for j, sub in enumerate(split_on_tokens(text)):
                chunks.append({
                    "doc": doc_name,
                    "chunk_id": f"{doc_name}_T{i:04d}_{j}",
                    "type": "text",
                    "section": current_section,
                    "text": sub,
                    "text_level": level,
                    "page": item.get("page_idx"),
                    "anchor": item.get("anchor", ""),
                    "meta": {"level": level},
                })
        elif itype == "image":
            chunks.append({
                "doc": doc_name,
                "chunk_id": f"{doc_name}_I{i:04d}",
                "type": "image",
                "section": current_section,
                "text": f"[图片] {item.get('caption', '')}",
                "image_path": item.get("image_path", ""),
                "page": item.get("page_idx"),
                "meta": {"caption": item.get("caption", "")},
            })
    return chunks


def build_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_chunks = []
    stats = {"text": 0, "table": 0, "image": 0}
    for cl_path in sorted(glob.glob(os.path.join(MINERU, "*/office/*content_list.json"))):
        doc = os.path.basename(cl_path).replace("_content_list.json", "")[:25]
        cl = json.loads(open(cl_path).read())
        chunks = chunk_document(doc, cl)
        for c in chunks:
            stats[c["type"]] += 1
        all_chunks.extend(chunks)
        print(f"  {doc}: {len(chunks)} chunks")
    with open(os.path.join(OUT_DIR, "srs_chunks.json"), "w") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=1)
    print(f"\n总计: {len(all_chunks)} chunks {stats}")
    return all_chunks


if __name__ == "__main__":
    build_all()
