#!/usr/bin/env python3
"""
Unified Dataset Builder
将所有SRS文档统一整理为项目数据集，分为GJB格式和一般SRS两类。
对每份文档使用MinerU解析结果(或原始MD)提取元信息字段，做统计分析。
"""

import json
import re
import os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

COLLECTION_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c/srs_collection")
OUTPUT_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c/unified_dataset")


def find_best_text(file_path: Path) -> str:
    """找到文件的最佳文本版本：优先MinerU解析的MD，其次原始MD，最后空。"""
    # 如果是MD文件，直接读取
    if file_path.suffix == ".md":
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except:
            return ""
    
    # 如果是PDF，找MinerU解析结果
    if file_path.suffix == ".pdf":
        # MinerU输出在 mineru_parsed/<pdf_name>/auto/<pdf_name>.md
        pdf_stem = file_path.stem
        parent = file_path.parent
        mineru_md = parent / "mineru_parsed" / file_path.name / "auto" / f"{file_path.name}.md"
        if mineru_md.exists():
            try:
                return mineru_md.read_text(encoding="utf-8", errors="replace")
            except:
                pass
        
        # 搜索同级mineru_parsed目录
        for md_path in parent.rglob("mineru_parsed/**/*.md"):
            if pdf_stem in md_path.name:
                try:
                    return md_path.read_text(encoding="utf-8", errors="replace")
                except:
                    pass
    
    # 如果是DOC/DOCX，尝试找对应的MD
    if file_path.suffix in (".doc", ".docx"):
        stem = file_path.stem
        # 查找同名MD
        md_candidate = file_path.parent / f"{stem}.md"
        if md_candidate.exists():
            try:
                return md_candidate.read_text(encoding="utf-8", errors="replace")
            except:
                pass
    
    return ""


def extract_metadata(filename: str, source: str, text: str, file_path: Path) -> dict:
    """从文本内容提取细粒度元数据。"""
    lines = text.splitlines()
    line_count = len(lines)
    char_count = len(text)
    
    # 标题
    title = ""
    for line in lines[:10]:
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break
    if not title:
        title = filename.rsplit(".", 1)[0]
    
    # 语言检测
    cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    ja_chars = sum(1 for c in text if '\u3040' <= c <= '\u30ff')
    if cjk_chars > 50:
        language = "zh"
    elif ja_chars > 20:
        language = "ja"
    else:
        language = "en"
    
    # GJB格式检测
    has_scope = bool(re.search(r"范围|Scope", text[:2000]))
    has_reference = bool(re.search(r"引用文档|引用文件|Referenced|References", text[:3000]))
    has_requirements = bool(re.search(r"需求|Requirements|能力需求", text[:5000]))
    has_qualification = bool(re.search(r"合格性规定|合格性|Qualification", text))
    has_traceability = bool(re.search(r"需求可追踪性|可追踪性|Traceability", text))
    has_notes = bool(re.search(r"^#+\s*注释|^#+\s*Notes", text, re.MULTILINE))
    has_csci = bool(re.search(r"CSCI|软件配置项", text))
    
    gjb_score = sum([has_scope, has_reference, has_requirements, has_qualification, has_traceability, has_notes])
    is_gjb = gjb_score >= 4 or (has_qualification and has_traceability)
    
    # GJB版本
    gjb_version = "unknown"
    if "438C" in text[:5000] or "438C" in filename:
        gjb_version = "438C"
    elif "438B" in text[:5000] or "438B" in filename:
        gjb_version = "438B"
    
    # 是否填写了实际内容
    is_filled = line_count > 200 and len(re.findall(r"\d+\.?\d*", text)) > 10
    is_template = line_count < 150 or bool(re.search(r"待填写|XXX|占位|placeholder|\{\{", text[:2000]))
    
    # 章节数
    section_count = len(re.findall(r"^#+\s", text, re.MULTILINE))
    
    # 3.2.X子章节数
    sub_32_count = len(re.findall(r"3\.2\.\d+", text))
    
    # 表格
    html_tables = len(re.findall(r"<table>", text, re.IGNORECASE))
    md_tables = len(re.findall(r"^\|.*\|.*\n\|[-:| ]+\|", text, re.MULTILINE))
    table_count = html_tables + md_tables
    
    # 表格类型
    table_types = []
    if re.search(r"序号.*版本号.*标记", text, re.DOTALL):
        table_types.append("modification")
    if re.search(r"序号.*名称.*版本.*日期", text, re.DOTALL):
        table_types.append("reference")
    if re.search(r"需求名称.*标识.*合格性|需求.*方法.*级别", text, re.DOTALL):
        table_types.append("qualification")
    if re.search(r"可行性研究报告|总体目标.*需求名称|追踪", text, re.DOTALL):
        table_types.append("traceability")
    
    # 需求ID
    req_ids = re.findall(r"REQ-[\d.]+|RX[_-][\d]+|R\d{3,}", text)
    req_id_count = len(set(req_ids))
    
    # shall语句
    shall_count = len(re.findall(r"\bshall\b", text, re.IGNORECASE))
    ying_count = len(re.findall(r"应[^应急应用]|不得|不应", text))
    
    # 数值约束
    numerical_values = re.findall(r"\d+\.?\d*\s*(?:ms|秒|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω|hours?|小时)", text, re.IGNORECASE)
    numerical_count = len(numerical_values)
    
    # 系统类型推断
    system_type = "unknown"
    text_lower = text[:3000].lower()
    type_keywords = {
        "embedded": ["嵌入式", "embedded", "mcu", "rtos", "定时器", "中断", "firmware"],
        "web": ["web", "浏览器", "html", "http", "前端", "后端", "api", "数据库"],
        "aerospace": ["nasa", "航空", "航天", "飞行", "orbit", "spacecraft", "satellite"],
        "education": ["教学", "课程", "学生", "成绩", "考试", "university", "school"],
        "defense": ["雷达", "导弹", "武器", "军用", "radar", "missile", "military"],
        "medical": ["医疗", "patient", "hospital", "诊断", "medical"],
        "industrial": ["焊接", "welding", "制造", "工厂", "industrial", "PLC"],
        "communication": ["通信", "网络", "协议", "protocol", "network", "5g"],
        "finance": ["金融", "交易", "支付", "finance", "payment", "bank"],
        "compiler": ["编译器", "compiler", "词法", "语法分析", "lexer", "parser"],
    }
    for stype, keywords in type_keywords.items():
        if any(kw in text_lower for kw in keywords):
            system_type = stype
            break
    
    # 标准类型
    if is_gjb:
        standard = f"GJB {gjb_version}" if gjb_version != "unknown" else "GJB-style"
    elif "IEEE 830" in text[:5000] or "ieee 830" in text_lower:
        standard = "IEEE 830"
    elif "ISO 29148" in text[:5000]:
        standard = "ISO 29148"
    elif "NASA" in text[:5000] or "nasa" in text_lower:
        standard = "NASA"
    elif "MIL-STD" in text[:5000]:
        standard = "MIL-STD"
    else:
        standard = "other"
    
    return {
        "filename": filename,
        "source": source,
        "format": file_path.suffix.lstrip("."),
        "file_size_bytes": file_path.stat().st_size,
        "line_count": line_count,
        "char_count": char_count,
        "language": language,
        "standard": standard,
        "is_gjb_format": is_gjb,
        "gjb_version": gjb_version if is_gjb else None,
        "gjb_compliance_score": gjb_score,
        "is_filled": is_filled,
        "is_template": is_template,
        "title": title[:100],
        "system_type": system_type,
        "section_count": section_count,
        "sub_section_32_count": sub_32_count,
        "table_count": table_count,
        "table_types": table_types,
        "req_id_count": req_id_count,
        "req_ids": list(set(req_ids))[:20],
        "shall_count": shall_count,
        "ying_count": ying_count,
        "numerical_constraint_count": numerical_count,
        "has_mineru_output": file_path.suffix == ".pdf" and bool(text),
        "sections": {
            "has_scope": has_scope,
            "has_reference": has_reference,
            "has_requirements": has_requirements,
            "has_qualification": has_qualification,
            "has_traceability": has_traceability,
            "has_notes": has_notes,
            "has_csci": has_csci,
        },
        "relative_path": str(file_path.relative_to(COLLECTION_DIR)) if file_path.is_relative_to(COLLECTION_DIR) else str(file_path),
    }


def process_all_documents():
    """处理所有文档，构建统一数据集。"""
    print("=" * 60)
    print("Unified Dataset Builder")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 扫描所有文件
    all_files = []
    for ext in ["*.md", "*.pdf", "*.doc", "*.docx", "*.txt"]:
        all_files.extend(COLLECTION_DIR.rglob(ext))
    
    # 过滤掉mineru_parsed目录内的文件(它们是中间产物)
    all_files = [f for f in all_files if "mineru_parsed" not in str(f) and "_run_logs" not in str(f)]
    
    # 按source分类
    source_map = {
        "buaa": "buaa",
        "radar": "radar",
        "asyncTask": "asyncTask",
        "more_gjb": "more_gjb",
        "gjb438b": "gjb438b",
        "nasa": "nasa",
        "ieee830": "ieee830",
        "pure_extended": "pure_extended",
    }
    
    print(f"\n扫描到 {len(all_files)} 个文件")
    
    all_metadata = []
    skipped = 0
    
    for i, file_path in enumerate(sorted(all_files)):
        # 确定source
        rel = file_path.relative_to(COLLECTION_DIR)
        source = rel.parts[0] if rel.parts else "root"
        if source not in source_map:
            continue
        
        # 跳过非文档文件
        if file_path.name.startswith(".") or file_path.name in ("README.md", "CATALOG.md", "ANALYSIS_REPORT.md"):
            continue
        
        # 获取最佳文本
        text = find_best_text(file_path)
        if not text or len(text) < 50:
            skipped += 1
            continue
        
        # 提取元数据
        meta = extract_metadata(file_path.name, source, text, file_path)
        all_metadata.append(meta)
        
        if (i + 1) % 50 == 0:
            print(f"  处理进度: {i+1}/{len(all_files)}")
    
    print(f"\n处理完成: {len(all_metadata)} 份文档 ({skipped} 跳过)")
    
    # 分类: GJB vs 一般
    gjb_docs = [m for m in all_metadata if m["is_gjb_format"]]
    general_docs = [m for m in all_metadata if not m["is_gjb_format"]]
    
    print(f"  GJB格式: {len(gjb_docs)} 份")
    print(f"  一般SRS: {len(general_docs)} 份")
    
    return all_metadata, gjb_docs, general_docs


def generate_statistics(all_docs, gjb_docs, general_docs):
    """生成统计分析。"""
    
    def stats_subset(docs, label):
        if not docs:
            return {"label": label, "count": 0}
        
        return {
            "label": label,
            "count": len(docs),
            "by_source": dict(Counter(d["source"] for d in docs)),
            "by_language": dict(Counter(d["language"] for d in docs)),
            "by_standard": dict(Counter(d["standard"] for d in docs)),
            "by_system_type": dict(Counter(d["system_type"] for d in docs)),
            "by_format": dict(Counter(d["format"] for d in docs)),
            "avg_line_count": round(sum(d["line_count"] for d in docs) / len(docs), 1),
            "avg_char_count": round(sum(d["char_count"] for d in docs) / len(docs), 1),
            "avg_section_count": round(sum(d["section_count"] for d in docs) / len(docs), 1),
            "avg_table_count": round(sum(d["table_count"] for d in docs) / len(docs), 1),
            "total_tables": sum(d["table_count"] for d in docs),
            "avg_req_id_count": round(sum(d["req_id_count"] for d in docs) / len(docs), 1),
            "total_req_ids": sum(d["req_id_count"] for d in docs),
            "avg_numerical_constraints": round(sum(d["numerical_constraint_count"] for d in docs) / len(docs), 1),
            "total_numerical_constraints": sum(d["numerical_constraint_count"] for d in docs),
            "filled_count": sum(1 for d in docs if d["is_filled"]),
            "template_count": sum(1 for d in docs if d["is_template"]),
            "avg_gjb_score": round(sum(d["gjb_compliance_score"] for d in docs) / len(docs), 2),
            "section_completeness": {
                "has_scope": sum(1 for d in docs if d["sections"]["has_scope"]),
                "has_reference": sum(1 for d in docs if d["sections"]["has_reference"]),
                "has_requirements": sum(1 for d in docs if d["sections"]["has_requirements"]),
                "has_qualification": sum(1 for d in docs if d["sections"]["has_qualification"]),
                "has_traceability": sum(1 for d in docs if d["sections"]["has_traceability"]),
                "has_notes": sum(1 for d in docs if d["sections"]["has_notes"]),
                "has_csci": sum(1 for d in docs if d["sections"]["has_csci"]),
            },
            "table_type_distribution": dict(Counter(tt for d in docs for tt in d["table_types"])),
        }
    
    stats = {
        "analysis_date": datetime.now().isoformat(),
        "total_documents": len(all_docs),
        "gjb_documents": len(gjb_docs),
        "general_documents": len(general_docs),
        "gjb_stats": stats_subset(gjb_docs, "GJB格式SRS"),
        "general_stats": stats_subset(general_docs, "一般SRS"),
        "all_stats": stats_subset(all_docs, "全部SRS"),
        "comparison": {
            "gjb_vs_general": {
                "avg_lines": [stats_subset(gjb_docs, "GJB")["avg_line_count"], stats_subset(general_docs, "一般")["avg_line_count"]],
                "avg_tables": [stats_subset(gjb_docs, "GJB")["avg_table_count"], stats_subset(general_docs, "一般")["avg_table_count"]],
                "avg_constraints": [stats_subset(gjb_docs, "GJB")["avg_numerical_constraints"], stats_subset(general_docs, "一般")["avg_numerical_constraints"]],
                "avg_sections": [stats_subset(gjb_docs, "GJB")["avg_section_count"], stats_subset(general_docs, "一般")["avg_section_count"]],
                "avg_req_ids": [stats_subset(gjb_docs, "GJB")["avg_req_id_count"], stats_subset(general_docs, "一般")["avg_req_id_count"]],
            }
        }
    }
    return stats


def generate_report(all_docs, gjb_docs, general_docs, stats):
    """生成人类可读报告。"""
    report = f"""# SRS数据集统一报告

> 生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 总文档数: {len(all_docs)}

## 1. 数据集总览

| 指标 | GJB格式SRS | 一般SRS | 总计 |
|---|:---:|:---:|:---:|
| 文档数 | {len(gjb_docs)} | {len(general_docs)} | {len(all_docs)} |
| 已填写 | {stats['gjb_stats']['filled_count']} | {stats['general_stats']['filled_count']} | {stats['all_stats']['filled_count']} |
| 模板 | {stats['gjb_stats']['template_count']} | {stats['general_stats']['template_count']} | {stats['all_stats']['template_count']} |
| 平均行数 | {stats['gjb_stats']['avg_line_count']} | {stats['general_stats']['avg_line_count']} | {stats['all_stats']['avg_line_count']} |
| 平均表格数 | {stats['gjb_stats']['avg_table_count']} | {stats['general_stats']['avg_table_count']} | {stats['all_stats']['avg_table_count']} |
| 平均数值约束 | {stats['gjb_stats']['avg_numerical_constraints']} | {stats['general_stats']['avg_numerical_constraints']} | {stats['all_stats']['avg_numerical_constraints']} |
| 平均需求ID | {stats['gjb_stats']['avg_req_id_count']} | {stats['general_stats']['avg_req_id_count']} | {stats['all_stats']['avg_req_id_count']} |
| 平均GJB合规分 | {stats['gjb_stats']['avg_gjb_score']} | {stats['general_stats']['avg_gjb_score']} | {stats['all_stats']['avg_gjb_score']} |

## 2. GJB格式SRS按来源分布

| 来源 | 数量 | 平均行数 | 平均表格 | 已填写 |
|---|:---:|:---:|:---:|:---:|
"""
    for source, count in sorted(stats['gjb_stats']['by_source'].items(), key=lambda x: -x[1]):
        subset = [d for d in gjb_docs if d['source'] == source]
        avg_lines = sum(d['line_count'] for d in subset) / max(len(subset), 1)
        avg_tables = sum(d['table_count'] for d in subset) / max(len(subset), 1)
        filled = sum(1 for d in subset if d['is_filled'])
        report += f"| {source} | {count} | {avg_lines:.0f} | {avg_tables:.1f} | {filled} |\n"

    report += f"""
## 3. 一般SRS按来源分布

| 来源 | 数量 | 平均行数 | 平均表格 | 已填写 |
|---|:---:|:---:|:---:|:---:|
"""
    for source, count in sorted(stats['general_stats']['by_source'].items(), key=lambda x: -x[1]):
        subset = [d for d in general_docs if d['source'] == source]
        avg_lines = sum(d['line_count'] for d in subset) / max(len(subset), 1)
        avg_tables = sum(d['table_count'] for d in subset) / max(len(subset), 1)
        filled = sum(1 for d in subset if d['is_filled'])
        report += f"| {source} | {count} | {avg_lines:.0f} | {avg_tables:.1f} | {filled} |\n"

    report += f"""
## 4. 系统类型分布

| 系统类型 | GJB格式 | 一般SRS | 总计 |
|---|:---:|:---:|:---:|
"""
    all_types = set(list(stats['gjb_stats']['by_system_type'].keys()) + list(stats['general_stats']['by_system_type'].keys()))
    for stype in sorted(all_types):
        gjb_c = stats['gjb_stats']['by_system_type'].get(stype, 0)
        gen_c = stats['general_stats']['by_system_type'].get(stype, 0)
        report += f"| {stype} | {gjb_c} | {gen_c} | {gjb_c + gen_c} |\n"

    report += f"""
## 5. 章节完整性统计 (GJB格式SRS)

| 章节 | 包含文档数 | 占比 |
|---|:---:|:---:|
"""
    for sec, label in [("has_scope", "1 范围"), ("has_reference", "2 引用文档"), ("has_requirements", "3 需求"), ("has_qualification", "4 合格性规定"), ("has_traceability", "5 需求可追踪性"), ("has_notes", "6 注释"), ("has_csci", "CSCI标识")]:
        count = stats['gjb_stats']['section_completeness'].get(sec, 0)
        pct = count / max(len(gjb_docs), 1) * 100
        report += f"| {label} | {count} | {pct:.1f}% |\n"

    report += f"""
## 6. 潜在冲突类型分析

基于文档内容分析，以下冲突类型可能存在:

| 冲突类型 | 描述 | 预计影响文档数 |
|---|---|:---:|
| 同参数多值 | 同一参数在不同位置出现不同值 | {sum(1 for d in gjb_docs if d['numerical_constraint_count'] > 10)} |
| 文本-表格矛盾 | 正文描述与表格内容不一致 | {sum(1 for d in gjb_docs if d['table_count'] > 0 and d['numerical_constraint_count'] > 5)} |
| 逻辑不可满足 | 约束之间逻辑上矛盾 | {sum(1 for d in gjb_docs if d['is_filled'] and d['numerical_constraint_count'] > 15)} |
| 章节缺失 | 缺少GJB要求的章节 | {sum(1 for d in gjb_docs if d['gjb_compliance_score'] < 5)} |
| 表格空模板 | 表格存在但未填写 | {sum(1 for d in gjb_docs if d['is_template'] and d['table_count'] > 0)} |

## 7. Top 20推荐文档 (用于一致性检测)

按(行数 + 表格数*10 + 数值约束数*5 + GJB合规分*20)排序:

| 排名 | 文档名 | 来源 | 行数 | 表格 | 约束 | GJB分 | 系统类型 |
|---|---|---|:---:|:---:|:---:|:---:|---|
"""
    # Sort by quality score
    for d in all_docs:
        d['_quality'] = d['line_count'] + d['table_count'] * 10 + d['numerical_constraint_count'] * 5 + d['gjb_compliance_score'] * 20
    
    top20 = sorted(all_docs, key=lambda x: -x['_quality'])[:20]
    for rank, d in enumerate(top20, 1):
        report += f"| {rank} | {d['filename'][:40]} | {d['source']} | {d['line_count']} | {d['table_count']} | {d['numerical_constraint_count']} | {d['gjb_compliance_score']} | {d['system_type']} |\n"

    report += f"""
## 8. 数据质量评估

- **GJB格式文档**: {len(gjb_docs)}份，其中已填写{stats['gjb_stats']['filled_count']}份
- **表格覆盖**: {stats['gjb_stats']['total_tables']}个表格(GJB) + {stats['general_stats']['total_tables']}个(一般)
- **数值约束**: {stats['gjb_stats']['total_numerical_constraints']}个(GJB) + {stats['general_stats']['total_numerical_constraints']}个(一般)
- **需求ID**: {stats['gjb_stats']['total_req_ids']}个(GJB) + {stats['general_stats']['total_req_ids']}个(一般)
- **MinerU解析**: 125份PDF已通过MinerU解析为Markdown

## 9. 数据目录结构

```
data/gjb_438c/
├── srs_collection/              # 原始文档集合
│   ├── buaa/                    # 北航学生GJB SRS
│   ├── radar/                   # 军用雷达项目
│   ├── asyncTask/               # AsyncTask GJB SRS
│   ├── more_gjb/                # 更多GJB SRS
│   ├── gjb438b/                 # GJB 438B格式
│   ├── nasa/                    # NASA SRS
│   ├── ieee830/                 # IEEE 830 SRS
│   └── pure_extended/           # PURE扩展数据集
├── unified_dataset/             # 统一数据集(本脚本输出)
│   ├── gjb_srs_catalog.json     # GJB格式SRS目录
│   ├── general_srs_catalog.json # 一般SRS目录
│   ├── statistics.json          # 统计分析
│   └── DATASET_REPORT.md        # 人类可读报告
├── extracted_constraints/       # 约束提取结果
├── extracted_tables/            # 表格提取结果
└── consistency_reports/         # 一致性检测报告
```
"""
    return report


def main():
    all_docs, gjb_docs, general_docs = process_all_documents()
    
    # 生成统计
    stats = generate_statistics(all_docs, gjb_docs, general_docs)
    
    # 输出
    (OUTPUT_DIR / "gjb_srs_catalog.json").write_text(
        json.dumps(gjb_docs, indent=2, ensure_ascii=False), "utf-8"
    )
    (OUTPUT_DIR / "general_srs_catalog.json").write_text(
        json.dumps(general_docs, indent=2, ensure_ascii=False), "utf-8"
    )
    (OUTPUT_DIR / "all_srs_catalog.json").write_text(
        json.dumps(all_docs, indent=2, ensure_ascii=False), "utf-8"
    )
    (OUTPUT_DIR / "statistics.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), "utf-8"
    )
    
    report = generate_report(all_docs, gjb_docs, general_docs, stats)
    (OUTPUT_DIR / "DATASET_REPORT.md").write_text(report, "utf-8")
    
    print(f"\n{'=' * 60}")
    print("统一数据集构建完成")
    print(f"  GJB格式SRS: {len(gjb_docs)}份 → gjb_srs_catalog.json")
    print(f"  一般SRS: {len(general_docs)}份 → general_srs_catalog.json")
    print(f"  统计分析: → statistics.json")
    print(f"  人类可读报告: → DATASET_REPORT.md")
    print(f"  输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
