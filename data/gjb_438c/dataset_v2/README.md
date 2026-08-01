# SRS一致性检测数据集

> 创建日期: 2026-07-29
> 文档总数: 52 (GJB: 22, 一般: 30)

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
{
  "doc_id": "gjb_001",
  "doc_name": "scheduler_srs",
  "title": "TH-Scheduler-周期任务调度器",
  "language": "zh",
  "is_gjb_format": true,
  "gjb_version": "438C",
  "system_type": "embedded",
  "is_filled": true,
  "stats": {
    "sections": 46,
    "constraints_regex": 18,
    "constraints_llm": 65,
    "tables": 5,
    "images": 7
  },
  "parsing_method": "MinerU pipeline backend"
}
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
| 文档数 | 22 | 30 | 52 |
| 已填写 | 0 | 0 | 0 |
| 总章节 | 1375 | 5432 | 6807 |
| 总表格 | 290 | 1897 | 2187 |
| 总图片 | 95 | 838 | 933 |
| 总约束(LLM) | 948 | 0 | 948 |

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
