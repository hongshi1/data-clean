#!/usr/bin/env python3
"""
Dataset Reorganizer
将散落的数据重新整理为规范的目录结构。

每份文档一个目录:
  dataset/gjb_srs/001_scheduler/
  ├── meta.json          # 文档元数据
  ├── original/          # 原始文件(PDF/MD/DOCX)
  ├── parsed/            # MinerU解析结果(MD+JSON+images)
  └── structured.json    # 结构化数据(章节/约束/表格/图片-文本对)
"""

import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE = REPO_ROOT / "data" / "gjb_438c"
PROC = BASE / "processed_documents"
MINERU_SRS = BASE / "mineru_srs"
COLLECTION = BASE / "srs_collection"
CONSTRAINTS_DIR = BASE / "extracted_constraints"
TABLES_DIR = BASE / "extracted_tables"
OUTPUT = BASE / "dataset_v2"


def find_original_file(doc_name: str, md_path: str) -> Path:
    """找到原始文件(PDF优先，其次MD/DOCX)。"""
    if not md_path:
        return None
    
    md_path = Path(md_path)
    if not md_path.is_absolute():
        md_path = REPO_ROOT / md_path
    
    # If it's a MinerU output MD, find the original PDF
    if "mineru_parsed" in str(md_path) or "mineru_srs" in str(md_path):
        # The original PDF is usually in the parent's parent's parent
        # mineru_parsed/<name>/auto/<name>.md → look for <name>.pdf nearby
        pdf_name = md_path.stem.replace(".pdf", "")
        for candidate in md_path.parents[3].glob(f"{pdf_name}*.pdf"):
            return candidate
        # Try demo directory
        for candidate in (BASE / "demo").glob(f"*{pdf_name}*"):
            return candidate
    
    # If it's a raw MD, check for corresponding PDF
    stem = md_path.stem
    parent = md_path.parent
    for ext in [".pdf", ".docx", ".doc"]:
        candidate = parent / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    
    # Return the MD itself as original
    if md_path.exists():
        return md_path
    return None


def find_mineru_parsed(doc_name: str) -> Path:
    """找到MinerU解析结果目录。"""
    # Check mineru_srs
    for d in MINERU_SRS.iterdir():
        if doc_name in d.name or d.name.startswith(doc_name):
            auto = d / "auto"
            if auto.exists():
                return auto
    
    # Check collection
    for d in COLLECTION.rglob("mineru_parsed/*/auto"):
        if doc_name in d.name or any(doc_name in f.name for f in d.iterdir()):
            return d
    
    return None


def build_meta(doc_data: dict, doc_id: str) -> dict:
    """构建文档元数据。"""
    return {
        "doc_id": doc_id,
        "doc_name": doc_data.get("doc_name", ""),
        "title": doc_data.get("title", ""),
        "source": doc_data.get("source", ""),
        "language": doc_data.get("language", "zh"),
        "is_gjb_format": doc_data.get("is_gjb_format", False),
        "gjb_version": doc_data.get("gjb_version"),
        "system_type": doc_data.get("system_type", "unknown"),
        "is_filled": doc_data.get("is_filled", False),
        "is_template": doc_data.get("is_template", False),
        "stats": {
            "md_lines": doc_data.get("md_lines", 0),
            "md_chars": doc_data.get("md_chars", 0),
            "sections": doc_data.get("section_count", 0),
            "constraints_regex": doc_data.get("constraint_count", 0),
            "constraints_llm": doc_data.get("llm_constraint_count", 0),
            "tables": doc_data.get("table_count", 0),
            "images": doc_data.get("image_count", 0),
            "image_text_pairs": len(doc_data.get("image_text_pairs", [])),
        },
        "parsing_method": "MinerU pipeline backend" if doc_data.get("has_mineru_output") else "raw markdown",
        "processing_date": doc_data.get("processing_date", ""),
    }


def reorganize():
    print("=" * 60)
    print("Dataset Reorganizer v2")
    print("=" * 60)
    
    OUTPUT.mkdir(parents=True, exist_ok=True)
    
    # Load index
    idx = json.load(open(PROC / "_index.json"))
    
    # Filter: unique GJB + unique general SRS with content
    gjb_docs = []
    general_docs = []
    
    for d in idx:
        if d.get("is_duplicate", False):
            continue
        if d.get("is_gjb"):
            gjb_docs.append(d)
        elif d.get("sections", 0) > 10 and d.get("tables", 0) + d.get("images", 0) > 0:
            general_docs.append(d)
    
    print(f"\nGJB SRS: {len(gjb_docs)}份")
    print(f"General SRS(有内容): {len(general_docs)}份")
    
    # Process GJB SRS
    gjb_dir = OUTPUT / "gjb_srs"
    gjb_dir.mkdir(exist_ok=True)
    
    catalog = []
    
    for i, doc_entry in enumerate(sorted(gjb_docs, key=lambda x: -x.get("sections", 0)), 1):
        doc_name = doc_entry["doc_name"]
        doc_id = f"gjb_{i:03d}"
        doc_dir = gjb_dir / f"{doc_id}_{doc_name[:30]}"  # e.g., gjb_001_scheduler_srs
        doc_dir.mkdir(exist_ok=True)
        
        # Load full document data
        proc_path = PROC / f"{doc_name}.json"
        if not proc_path.exists():
            continue
        doc_data = json.loads(proc_path.read_text("utf-8"))
        
        # 1. Save meta.json
        meta = build_meta(doc_data, doc_id)
        (doc_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
        
        # 2. Copy original file
        orig_dir = doc_dir / "original"
        orig_dir.mkdir(exist_ok=True)
        md_path = doc_data.get("md_path", "")
        orig_file = find_original_file(doc_name, md_path)
        if orig_file and orig_file.exists():
            dst = orig_dir / orig_file.name
            if not dst.exists():
                try:
                    shutil.copy2(orig_file, dst)
                except:
                    pass
        
        # 3. Copy/save parsed content (the MinerU MD or raw MD)
        parsed_dir = doc_dir / "parsed"
        parsed_dir.mkdir(exist_ok=True)
        if md_path:
            md_full = Path(md_path) if Path(md_path).is_absolute() else REPO_ROOT / md_path
            if md_full.exists():
                content = md_full.read_text("utf-8")
                (parsed_dir / "document.md").write_text(content, "utf-8")
        
        # 4. Save structured.json (the full processed document)
        structured = {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "sections": doc_data.get("sections", []),
            "constraints_regex": doc_data.get("constraints", []),
            "constraints_llm": doc_data.get("llm_constraints"),
            "tables": doc_data.get("tables", []),
            "images": doc_data.get("images", []),
            "image_text_pairs": doc_data.get("image_text_pairs", []),
        }
        (doc_dir / "structured.json").write_text(
            json.dumps(structured, indent=2, ensure_ascii=False), "utf-8"
        )
        
        catalog.append({
            "doc_id": doc_id,
            "doc_name": doc_name,
            "category": "gjb_srs",
            "path": str(doc_dir.relative_to(OUTPUT)),
            **meta["stats"],
            "is_gjb": True,
            "language": meta["language"],
            "system_type": meta["system_type"],
            "is_filled": meta["is_filled"],
        })
        
        print(f"  [{i:2d}] {doc_id} {doc_name[:40]:42s} sec={meta['stats']['sections']:3d} tbl={meta['stats']['tables']:3d} img={meta['stats']['images']:3d}")
    
    # Process General SRS (top 30 by content)
    gen_dir = OUTPUT / "general_srs"
    gen_dir.mkdir(exist_ok=True)
    
    general_sorted = sorted(general_docs, key=lambda x: -(x.get("sections", 0) + x.get("tables", 0) * 5 + x.get("images", 0) * 3))
    
    for i, doc_entry in enumerate(general_sorted[:30], 1):
        doc_name = doc_entry["doc_name"]
        doc_id = f"gen_{i:03d}"
        safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', doc_name)[:30]
        doc_dir = gen_dir / f"{doc_id}_{safe_name}"
        doc_dir.mkdir(exist_ok=True)
        
        proc_path = PROC / f"{doc_name}.json"
        if not proc_path.exists():
            continue
        doc_data = json.loads(proc_path.read_text("utf-8"))
        
        # meta.json
        meta = build_meta(doc_data, doc_id)
        (doc_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
        
        # original
        orig_dir = doc_dir / "original"
        orig_dir.mkdir(exist_ok=True)
        md_path = doc_data.get("md_path", "")
        orig_file = find_original_file(doc_name, md_path)
        if orig_file and orig_file.exists():
            dst = orig_dir / orig_file.name
            if not dst.exists():
                try:
                    shutil.copy2(orig_file, dst)
                except:
                    pass
        
        # parsed
        parsed_dir = doc_dir / "parsed"
        parsed_dir.mkdir(exist_ok=True)
        if md_path:
            md_full = Path(md_path) if Path(md_path).is_absolute() else REPO_ROOT / md_path
            if md_full.exists():
                content = md_full.read_text("utf-8")
                (parsed_dir / "document.md").write_text(content, "utf-8")
        
        # structured.json
        structured = {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "sections": doc_data.get("sections", []),
            "constraints_regex": doc_data.get("constraints", []),
            "tables": doc_data.get("tables", []),
            "images": doc_data.get("images", []),
            "image_text_pairs": doc_data.get("image_text_pairs", []),
        }
        (doc_dir / "structured.json").write_text(
            json.dumps(structured, indent=2, ensure_ascii=False), "utf-8"
        )
        
        catalog.append({
            "doc_id": doc_id,
            "doc_name": doc_name,
            "category": "general_srs",
            "path": str(doc_dir.relative_to(OUTPUT)),
            **meta["stats"],
            "is_gjb": False,
            "language": meta["language"],
            "system_type": meta["system_type"],
            "is_filled": meta["is_filled"],
        })
    
    # Copy rules and gold standard
    rules_dir = OUTPUT / "rules"
    rules_dir.mkdir(exist_ok=True)
    rules_src = REPO_ROOT / "knowledge" / "gjb_438c_rules_full.json"
    if rules_src.exists():
        shutil.copy2(rules_src, rules_dir / "gjb_438c_rules.json")
    
    gold_dir = OUTPUT / "gold_standard"
    gold_dir.mkdir(exist_ok=True)
    gold_src = BASE / "gold_standard"
    if gold_src.exists():
        for f in gold_src.glob("*.json"):
            shutil.copy2(f, gold_dir / f.name)
    
    # Save catalog
    (OUTPUT / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False), "utf-8"
    )
    
    # Write README
    readme = f"""# SRS一致性检测数据集

> 创建日期: {datetime.now().strftime('%Y-%m-%d')}
> 文档总数: {len(catalog)} (GJB: {len(gjb_docs)}, 一般: {min(30, len(general_docs))})

## 目录结构

```
dataset_v2/
├── README.md                    # 本文件
├── catalog.json                 # 统一目录(所有文档元数据)
├── gjb_srs/                     # GJB格式SRS
│   ├── gjb_001_scheduler_srs/   # 每份文档一个目录
│   │   ├── meta.json            # 文档元数据(语言/系统类型/统计)
│   │   ├── original/            # 原始文件(PDF/MD)
│   │   ├── parsed/              # 解析后Markdown
│   │   └── structured.json      # 结构化数据(章节/约束/表格/图片-文本对)
│   ├── gjb_002_battery_srs/
│   └── ...
├── general_srs/                 # 一般SRS(IEEE 830/NASA等)
│   ├── gen_001_*
│   └── ...
├── rules/                       # GJB规则库
│   └── gjb_438c_rules.json      # 120条规则
└── gold_standard/               # Gold Standard标注
    ├── scheduler_srs_gold.json
    ├── compiler_srs_gold.json
    └── battery_srs_gold.json
```

## 每份文档的目录说明

### meta.json
```json
{{
  "doc_id": "gjb_001",
  "doc_name": "scheduler_srs",
  "title": "TH-Scheduler-周期任务调度器",
  "language": "zh",
  "is_gjb_format": true,
  "gjb_version": "438C",
  "system_type": "embedded",
  "is_filled": true,
  "stats": {{
    "sections": 46,
    "constraints_regex": 18,
    "constraints_llm": 65,
    "tables": 5,
    "images": 7
  }},
  "parsing_method": "MinerU pipeline backend"
}}
```

### original/
原始文件(PDF/MD/DOCX)，未经任何处理。

### parsed/
MinerU解析后的Markdown文件(document.md)。
解析方法: MinerU v3.4.4, pipeline backend, CPU模式。

### structured.json
结构化数据，包含:
- sections: 章节树(编号/标题/层级/文本)
- constraints_regex: 正则提取的数值约束
- constraints_llm: LLM(GLM-5)提取的7类约束
- tables: 表格(类型/表头/行数/章节)
- images: 图片-文本对(图片文件/标题/上下文/章节)

## 解析方法

1. **PDF解析**: MinerU v3.4.4 (pipeline backend, CPU模式)
   - 输入: PDF文件
   - 输出: Markdown + JSON + 提取的图片
   - 特点: 保留版面结构, HTML表格, 图片提取

2. **约束提取**: GLM-5 API (LLM-based)
   - 输入: 章节文本
   - 输出: 7类约束(numerical/tolerance/cumulative/temporal/conditional/default/design)
   - 特点: 中文约束理解, 7种类型分类

3. **表格解析**: HTML表格解析器
   - 输入: MinerU输出的HTML表格
   - 输出: 分类(modification/reference/qualification/traceability) + 表头 + 行数据

4. **图片-文本匹配**: 位置匹配
   - 输入: MinerU Markdown中的图片引用
   - 输出: 图片文件 + caption + context + section
   - 回退: 无引用时扫描images/目录

## 数据集统计

| 指标 | GJB SRS | 一般SRS | 总计 |
|---|:---:|:---:|:---:|
| 文档数 | {len(gjb_docs)} | {min(30, len(general_docs))} | {len(catalog)} |
| 已填写 | {sum(1 for c in catalog if c['is_gjb'] and c['is_filled'])} | {sum(1 for c in catalog if not c['is_gjb'] and c['is_filled'])} | {sum(1 for c in catalog if c['is_filled'])} |
| 总章节 | {sum(c['sections'] for c in catalog if c['is_gjb'])} | {sum(c['sections'] for c in catalog if not c['is_gjb'])} | {sum(c['sections'] for c in catalog)} |
| 总表格 | {sum(c['tables'] for c in catalog if c['is_gjb'])} | {sum(c['tables'] for c in catalog if not c['is_gjb'])} | {sum(c['tables'] for c in catalog)} |
| 总图片 | {sum(c['images'] for c in catalog if c['is_gjb'])} | {sum(c['images'] for c in catalog if not c['is_gjb'])} | {sum(c['images'] for c in catalog)} |
| 总约束(LLM) | {sum(c['constraints_llm'] for c in catalog if c['is_gjb'])} | {sum(c['constraints_llm'] for c in catalog if not c['is_gjb'])} | {sum(c['constraints_llm'] for c in catalog)} |

## Gold Standard

3份GJB SRS的人工标注:
- scheduler_srs: 7个标注(1真矛盾 + 6正值)
- compiler_srs: 7个标注(5真矛盾 + 2正值)
- battery_srs: 8个标注(2真矛盾 + 6正值)
- 总计: 22个标注(8真矛盾 + 14正值)

## 使用方法

```python
import json
from pathlib import Path

# 加载文档
doc_dir = Path("dataset_v2/gjb_srs/gjb_001_scheduler_srs")
meta = json.load(open(doc_dir / "meta.json"))
structured = json.load(open(doc_dir / "structured.json"))

# 获取章节
for sec in structured["sections"]:
    print(sec["number"], sec["title"])

# 获取约束
for con in (structured["constraints_llm"] or []):
    print("  [" + con["type"] + "] " + con.get("param","") + ": " + con.get("original","")[:60])

# 获取表格
for tbl in structured["tables"]:
    print("  [" + tbl["type"] + "] " + str(tbl["row_count"]) + "行 section=" + str(tbl.get("section","")))

# 获取图片-文本对
for pair in structured["image_text_pairs"]:
    print("  " + pair["image_file"] + " caption=" + str(pair.get("caption",""))[:40])
```
"""
    (OUTPUT / "README.md").write_text(readme, "utf-8")
    
    print(f"\n{'=' * 60}")
    print("数据集重组完成")
    print(f"  GJB SRS: {len(gjb_docs)}份")
    print(f"  General SRS: {min(30, len(general_docs))}份")
    print(f"  总计: {len(catalog)}份")
    print(f"  输出: {OUTPUT}")
    print(f"  目录数: {len(list(OUTPUT.rglob('meta.json')))}")


if __name__ == "__main__":
    reorganize()
