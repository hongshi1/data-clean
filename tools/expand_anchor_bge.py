r"""基于上下文关联技术的Pair扩容 — 使用BGE语义匹配(方向A已有技术).

不自己搞粗糙的section前缀匹配，而是复用已有的上下文关联技术:
  1. anchors_v3: 16文档373图2831节点(图结构已解析)
  2. BGE embedding: 语义相似度匹配(已验证: "数据获取功能划分"vs"数据获取"=0.768)
  3. srs_chunks: 5231个chunks(表格+图片+文本)
  4. scene_tier1: 已有的227个多场景配对(作为参照)

配对逻辑:
  Step 1: 对每个table chunk提取表格标题
  Step 2: 对同文档的所有图节点计算BGE相似度
  Step 3: 相似度>阈值的配对(真实语义关联,非section字符串匹配)
  Step 4: 排除已有的366对
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
ANCHORS_V3 = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset"
OUT = BASE / "data/gjb_438c/pair_dataset_expanded"
SIM_THRESHOLD = 0.60  # BGE相似度阈值


def extract_table_title(text: str) -> str:
    """从table chunk提取表格标题."""
    m = re.search(r"\[表格标题:\s*([^\]]+)\]", text)
    return m.group(1).strip() if m else text[:50]


def extract_image_caption(text: str) -> str:
    """从image chunk提取图标题."""
    m = re.search(r"\[图片\]\s*(.*)", text)
    return m.group(1).strip() if m else text[:50]


def main() -> None:
    # 加载数据
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    anchors_v3 = json.loads(ANCHORS_V3.read_text(encoding="utf-8"))
    table_chunks = [c for c in chunks if c.get("type") == "table"]

    # 构建图节点索引(doc → [node_text, ...])
    doc_nodes = {}
    for doc, data in anchors_v3.items():
        nodes = []
        for s in data.get("structures", []):
            for n in s.get("nodes", []):
                if n.get("text"):
                    nodes.append(n["text"].strip())
        doc_nodes[doc] = nodes

    # 排除已有的pair
    existing = set()
    for scene_dir in PAIR_DIR.iterdir():
        if not scene_dir.is_dir():
            continue
        for pair_dir in scene_dir.iterdir():
            if not pair_dir.is_dir():
                continue
            meta_path = pair_dir / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                existing.add((str(meta.get("doc", "")), str(meta.get("section", ""))))

    print(f"table chunks: {len(table_chunks)}")
    print(f"已有pair: {len(existing)}对")
    print(f"图节点: {sum(len(v) for v in doc_nodes.values())}个(来自{len(doc_nodes)}文档)")

    # BGE匹配: 表格标题 × 同文档图节点
    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal()

    # 收集所有需要编码的文本
    all_texts = set()
    table_titles = {}
    for tc in table_chunks:
        doc = tc.get("doc", "")
        title = extract_table_title(str(tc.get("text", "")))
        if title and doc:
            key = (doc, title)
            if key not in table_titles:
                table_titles[key] = tc
                all_texts.add(title)

    for doc, nodes in doc_nodes.items():
        for n in nodes:
            all_texts.add(n)

    # 批量编码
    print(f"\n编码{len(all_texts)}个文本...")
    text_list = list(all_texts)
    vecs = bge.embed(text_list)
    vec_dict = {t: np.array(vecs[t], dtype=np.float32) for t in text_list if t in vecs}

    # 匹配
    new_pairs = []
    matched_count = 0
    for (doc, title), tc in table_titles.items():
        # 排除已有
        section = str(tc.get("section", ""))
        if (doc, section) in existing:
            continue

        # 与同文档的图节点计算相似度
        nodes = doc_nodes.get(doc, [])
        if not nodes:
            continue

        title_vec = vec_dict.get(title)
        if title_vec is None:
            continue

        best_sim = 0.0
        best_node = None
        for node in nodes:
            node_vec = vec_dict.get(node)
            if node_vec is None:
                continue
            sim = float(np.dot(title_vec, node_vec) /
                        (np.linalg.norm(title_vec) * np.linalg.norm(node_vec) + 1e-9))
            if sim > best_sim:
                best_sim = sim
                best_node = node

        if best_sim >= SIM_THRESHOLD and best_node:
            matched_count += 1
            new_pairs.append({
                "scene": _classify_scene(str(tc.get("text", ""))),
                "doc": doc,
                "section": section,
                "table_title": title,
                "table_text": str(tc.get("text", ""))[:500],
                "matched_node": best_node,
                "similarity": round(best_sim, 3),
                "table_chunk_id": tc.get("chunk_id", ""),
                "match_method": "bge_semantic",
            })

    print(f"\n匹配结果(阈值{SIM_THRESHOLD}):")
    print(f"  新增pair: {len(new_pairs)}对")
    by_scene = Counter(p["scene"] for p in new_pairs)
    print(f"  按场景: {dict(sorted(by_scene.items()))}")
    by_doc = Counter(str(p["doc"])[:2] for p in new_pairs)
    print(f"  按文档: {dict(sorted(by_doc.items()))}")

    # 相似度分布
    sims = [p["similarity"] for p in new_pairs]
    print(f"  相似度: min={min(sims):.3f}, mean={np.mean(sims):.3f}, max={max(sims):.3f}")

    # 保存
    OUT.mkdir(parents=True, exist_ok=True)
    out_file = OUT / "bge_matched_pairs.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"total": len(new_pairs), "threshold": SIM_THRESHOLD,
                    "method": "bge_semantic_matching", "pairs": new_pairs},
                   f, ensure_ascii=False, indent=1)
    print(f"保存 → {out_file}")


def _classify_scene(text: str) -> str:
    head = text[:300]
    if "功能" in head and ("名称" in head or "标识" in head):
        return "sc1_usecase_capability"
    if "接口" in head and ("名称" in head or "标识" in head):
        return "sc3_interface_interface"
    if "用例" in head or "Use case" in head:
        return "sc2_flowchart_usecase"
    return "sc_unknown"


if __name__ == "__main__":
    main()
