#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EasyDataset全链路打通: MinerU→Chunk→QA→EasyDataset导入→导出

完整流程:
  1. MinerU content_list → 切分为带元数据的Chunks
  2. 已有QA对(6189+3268 UML) → 合并
  3. 转换为EasyDataset格式
  4. 批量导入EasyDataset(在线) 或导出为标准格式(离线)
  5. 导出Alpaca/ShareGPT格式(可直接训练)
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "data/gjb_438c/easydataset"

# 源数据路径
QA_MAIN = BASE / "data/gjb_438c/data_assets/srs_qa_final.json"
QA_UML = BASE / "data/gjb_438c/anchor_v3/uml_qa_pairs.json"
MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"

# 输出文件
CHUNKS_OUT = OUT_DIR / "chunks.json"
DATASET_OUT = OUT_DIR / "datasets_easydataset.json"
ALPACA_OUT = OUT_DIR / "srs_alpaca.jsonl"
SHAREGPT_OUT = OUT_DIR / "srs_sharegpt.jsonl"
MANIFEST_OUT = OUT_DIR / "manifest.json"

ED_URL = "http://localhost:1717"


# ============================================================================
# Step 1: MinerU → 增强Chunks(带元数据)
# ============================================================================

def build_chunks():
    """从MinerU的content_list切分为带元数据的Chunks

    每个Chunk包含:
    - name: 章节-文档标识
    - content: 正文+表格摘要+图片引用
    - metadata: {doc, section, images, tables, entities}
    """
    import glob

    chunks = []
    all_docs = glob.glob(str(MINERU_DIR / "*/office/*content_list.json"))

    print(f"发现{len(all_docs)}份MinerU解析文档")

    for cl_path in sorted(all_docs):
        doc_name = Path(cl_path).stem.replace("_content_list", "")
        cl = json.load(open(cl_path, encoding="utf-8"))

        # 按章节切分
        sections = defaultdict(list)
        cur_sec = "前言"

        for item in cl:
            if not isinstance(item, dict):
                continue

            if item.get("type") == "text":
                text = item.get("text", "")
                # 章节标题检测
                import re
                m = re.match(r"^(\d+(?:\.\d+)*)\s+(.+)$", text.strip())
                if m and len(m.group(2)) < 50:  # 是章节标题
                    cur_sec = m.group(1)
                    sections[cur_sec].append({"type": "heading", "text": text.strip()})
                elif len(text.strip()) > 10:
                    sections[cur_sec].append({"type": "text", "text": text.strip()})

            elif item.get("type") == "table":
                caps = item.get("table_caption", [])
                cap = caps[0] if caps else f"表@{cur_sec}"
                sections[cur_sec].append({"type": "table", "caption": cap,
                                         "section": cur_sec})

            elif item.get("type") == "image":
                caps = item.get("image_caption", [])
                cap = caps[0] if caps else f"图@{cur_sec}"
                img_path = item.get("img_path", "")
                sections[cur_sec].append({"type": "image", "caption": cap,
                                         "path": img_path})

        # 每个章节 → 一个Chunk
        for sec, items in sections.items():
            if not items:
                continue

            # 构建内容
            text_parts = []
            image_refs = []
            table_refs = []

            for it in items:
                if it["type"] == "heading":
                    text_parts.append(f"## {it['text']}")
                elif it["type"] == "text":
                    text_parts.append(it["text"])
                elif it["type"] == "table":
                    table_refs.append(it["caption"])
                    text_parts.append(f"[表格: {it['caption']}]")
                elif it["type"] == "image":
                    image_refs.append(it["caption"])
                    text_parts.append(f"[图片: {it['caption']}]")

            content = "\n".join(text_parts)

            # 元数据
            meta = {
                "doc": doc_name,
                "section": sec,
                "doc_num": doc_name[:2],
                "images": image_refs[:5],
                "tables": table_refs[:5],
                "n_images": len(image_refs),
                "n_tables": len(table_refs),
                "content_length": len(content),
            }

            chunks.append({
                "name": f"SRS-{doc_name[:8]}-{sec}",
                "content": content[:2000],  # 截断防止过长
                "summary": content[:100],
                "size": len(content),
                "metadata": meta,
            })

    print(f"生成Chunks: {len(chunks)}个")
    return chunks


# ============================================================================
# Step 2: QA对合并 + EasyDataset格式转换
# ============================================================================

def build_datasets():
    """合并所有QA对并转换为EasyDataset格式"""
    datasets = []

    # 2a: 主QA对(6189条)
    if QA_MAIN.exists():
        qa_main = json.load(open(QA_MAIN, encoding="utf-8"))
        for qa in qa_main:
            if not qa.get("question", "").strip() or not qa.get("answer", "").strip():
                continue

            tags = []
            if qa.get("scenario"):
                tags.append(f"场景sc{qa['scenario']}")
            if qa.get("type"):
                tags.append(qa["type"])
            if qa.get("label"):
                tags.append(qa["label"])
            if qa.get("difficulty"):
                tags.append(qa["difficulty"])
            tags.append("注入" if qa.get("is_injected") else "原生")

            other = {
                "doc": qa.get("doc", ""),
                "section": qa.get("section", ""),
                "pair_id": qa.get("pair_id", ""),
                "image_caption": qa.get("image_caption", ""),
                "table_caption": qa.get("table_caption", ""),
            }
            if qa.get("is_injected"):
                other["inconsistency_type"] = qa.get("inconsistency_type", "")
                other["rule_id"] = qa.get("rule_id", "")

            cot = ""
            ev = qa.get("evidence", "")
            if ev:
                cot = f"证据来源: {str(ev)[:100]}"

            datasets.append({
                "question": qa["question"].strip(),
                "answer": qa["answer"].strip(),
                "chunkName": f"SRS-{qa.get('doc', 'unknown')[:8]}",
                "chunkContent": str(ev)[:500] if ev else "SRS文档问答对",
                "model": "srs-pipeline",
                "questionLabel": qa.get("type", qa.get("inconsistency_type", "")),
                "cot": cot,
                "confirmed": True,
                "score": 0.8,
                "tags": tags,
                "other": other,
                "note": "",
            })

        print(f"主QA: {len(qa_main)}条 → 转换后有效: {len(datasets)}条")

    # 2b: UML QA对(3268条)
    base_count = len(datasets)
    if QA_UML.exists():
        qa_uml = json.load(open(QA_UML, encoding="utf-8"))
        for qa in qa_uml:
            if not qa.get("question", "").strip() or not qa.get("answer", "").strip():
                continue

            tags = [f"UML-{qa.get('uml_type', 'ASSOCIATION')}"]
            tags.append(qa.get("label", ""))
            tags.append(qa.get("difficulty", ""))
            tags.append("UML关系")

            ev = qa.get("evidence", {})
            cot = ""
            if ev and isinstance(ev, dict):
                cot = (f"UML关系: {ev.get('uml_type', '')}, "
                       f"线型: {ev.get('line_pattern', '')}, "
                       f"箭头: {ev.get('end_arrow', '')}")

            datasets.append({
                "question": qa["question"].strip(),
                "answer": qa["answer"].strip(),
                "chunkName": f"UML-{qa.get('doc', 'unknown')[:8]}",
                "chunkContent": f"UML关系: {ev.get('uml_type', '')} "
                               f"({ev.get('src', '')} → {ev.get('dst', '')})",
                "model": "uml-pipeline",
                "questionLabel": f"UML-{qa.get('uml_type', '')}",
                "cot": cot,
                "confirmed": True,
                "score": 0.75,
                "tags": tags,
                "other": {
                    "doc": qa.get("doc", ""),
                    "uml_type": qa.get("uml_type", ""),
                    "embed": ev.get("embed", ""),
                },
                "note": qa.get("inject_type", ""),
            })

        print(f"UML QA: {len(qa_uml)}条 → 新增: {len(datasets) - base_count}条")

    print(f"总计: {len(datasets)}条EasyDataset格式数据")
    return datasets


# ============================================================================
# Step 3: 导出Alpaca/ShareGPT格式
# ============================================================================

def export_alpaca(datasets):
    """导出Alpaca格式(标准指令微调格式)"""
    with open(ALPACA_OUT, "w", encoding="utf-8") as f:
        for d in datasets:
            alpaca = {
                "instruction": d["question"],
                "input": d.get("chunkContent", ""),
                "output": d["answer"],
            }
            f.write(json.dumps(alpaca, ensure_ascii=False) + "\n")
    print(f"Alpaca导出: {len(datasets)}条 → {ALPACA_OUT}")


def export_sharegpt(datasets):
    """导出ShareGPT格式(对话微调格式)"""
    with open(SHAREGPT_OUT, "w", encoding="utf-8") as f:
        for d in datasets:
            sharegpt = {
                "conversations": [
                    {"from": "human", "value": d["question"]},
                    {"from": "gpt", "value": d["answer"]},
                ],
                "tags": d.get("tags", []),
            }
            f.write(json.dumps(sharegpt, ensure_ascii=False) + "\n")
    print(f"ShareGPT导出: {len(datasets)}条 → {SHAREGPT_OUT}")


# ============================================================================
# Step 4: 在线导入EasyDataset(如果运行中)
# ============================================================================

def try_online_import(project_name, datasets, chunks):
    """尝试在线导入EasyDataset"""
    import urllib.request
    import urllib.error

    try:
        # 检查EasyDataset是否运行
        urllib.request.urlopen(ED_URL, timeout=3)
    except (urllib.error.URLError, urllib.error.HTTPError):
        print("EasyDataset未运行(离线模式)")
        return False

    try:
        # 创建项目
        body = json.dumps({
            "name": project_name,
            "description": "基于16份GJB 438C SRS的多模态一致性校验微调数据集(含UML关系)"
        }).encode()
        req = urllib.request.Request(
            f"{ED_URL}/api/projects",
            data=body, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=30)
        j = json.loads(resp.read())
        project_id = j.get("id") or j.get("project", {}).get("id")
        print(f"项目创建: {project_id}")

        # 批量导入
        batch_size = 100
        total = 0
        for i in range(0, len(datasets), batch_size):
            chunk = datasets[i:i + batch_size]
            body = json.dumps({"datasets": chunk, "sourceInfo": {"source": "srs-pipeline"}}).encode()
            req = urllib.request.Request(
                f"{ED_URL}/api/projects/{project_id}/datasets/import",
                data=body, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read())
            total += result.get("successCount", 0)
            print(f"  批{i // batch_size + 1}: {len(chunk)}条 (累计{total})")

        print(f"在线导入完成: {total}条 → EasyDataset项目 {project_id}")
        return True

    except Exception as e:
        print(f"在线导入失败: {e}")
        return False


# ============================================================================
# 主流程
# ============================================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 70)
    print("EasyDataset全链路: MinerU→Chunk→QA→导入→导出")
    print("=" * 70)

    # Step 1: Chunks
    print("\n[Step 1] MinerU → 增强Chunks")
    chunks = build_chunks()
    json.dump(chunks, open(CHUNKS_OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # Step 2: QA数据集
    print("\n[Step 2] QA合并 → EasyDataset格式")
    datasets = build_datasets()
    json.dump(datasets, open(DATASET_OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # Step 3: 标准格式导出
    print("\n[Step 3] 导出训练格式")
    export_alpaca(datasets)
    export_sharegpt(datasets)

    # Step 4: 在线导入(可选)
    print("\n[Step 4] 在线导入EasyDataset")
    try_online_import("SRS一致性校验微调数据集v2", datasets, chunks)

    # Manifest
    manifest = {
        "chunks": len(chunks),
        "datasets": len(datasets),
        "by_source": {},
        "by_label": {},
        "export_formats": ["easydataset", "alpaca", "sharegpt"],
        "created": str(Path(CHUNKS_OUT).stat().st_mtime),
    }

    # 统计
    src_dist = defaultdict(int)
    label_dist = defaultdict(int)
    for d in datasets:
        tags = d.get("tags", [])
        for t in tags:
            if "注入" in t or "原生" in t or "UML" in t:
                src_dist[t] += 1
        label = next((t for t in tags if t in ("consistent", "inconsistent")), "未知")
        label_dist[label] += 1

    manifest["by_source"] = dict(src_dist)
    manifest["by_label"] = dict(label_dist)

    json.dump(manifest, open(MANIFEST_OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"\n{'='*70}")
    print("全链路完成!")
    print(f"  Chunks:       {len(chunks)}")
    print(f"  Datasets:     {len(datasets)}")
    print(f"  来源分布:     {dict(src_dist)}")
    print(f"  标签分布:     {dict(label_dist)}")
    print(f"\n输出目录: {OUT_DIR}")
    print(f"  {CHUNKS_OUT.name} (Chunks)")
    print(f"  {DATASET_OUT.name} (EasyDataset格式)")
    print(f"  {ALPACA_OUT.name} (Alpaca训练格式)")
    print(f"  {SHAREGPT_OUT.name} (ShareGPT训练格式)")
    print(f"  {MANIFEST_OUT.name} (清单)")


if __name__ == "__main__":
    main()
