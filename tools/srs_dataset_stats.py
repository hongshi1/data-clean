#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对3份GJB格式SRS文档做详细统计分析，输出 dataset_statistics.json"""
import json, re, os
from collections import Counter, defaultdict

BASE = "/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c"
MD = {
    "scheduler_srs": f"{BASE}/mineru_srs/scheduler_srs.pdf/auto/scheduler_srs.pdf.md",
    "battery_srs":   f"{BASE}/mineru_srs/battery_srs.pdf/auto/battery_srs.pdf.md",
    "compiler_srs":  f"{BASE}/mineru_srs/compiler_srs.pdf/auto/compiler_srs.pdf.md",
}
MID = {
    "scheduler_srs": f"{BASE}/mineru_srs/scheduler_srs.pdf/auto/scheduler_srs.pdf_middle.json",
    "battery_srs":   f"{BASE}/mineru_srs/battery_srs.pdf/auto/battery_srs.pdf_middle.json",
    "compiler_srs":  f"{BASE}/mineru_srs/compiler_srs.pdf/auto/compiler_srs.pdf_middle.json",
}
TBL = {
    "scheduler_srs": f"{BASE}/extracted_tables/scheduler_srs_tables.json",
    "battery_srs":   f"{BASE}/extracted_tables/battery_srs_tables.json",
    "compiler_srs":  f"{BASE}/extracted_tables/compiler_srs_tables.json",
}
CON = f"{BASE}/extracted_constraints/scheduler_srs_constraints.json"
# 源PDF映射 (用于文件大小)
PDF = {
    "scheduler_srs": f"{BASE}/demo/[08]调度器-软件需求规格说明-438C.pdf",
    "battery_srs":   f"{BASE}/demo/[08]电池仿真模型-软件需求规格说明-438C.pdf",
    "compiler_srs":  f"{BASE}/demo/[10][SRS] 软件需求规格说明-438C-2021-filled_20260708180433.pdf",
}
SYS_TYPE = {
    "scheduler_srs": "嵌入式实时调度器 (Embedded Linux, ARM)",
    "battery_srs":   "嵌入式电池仿真模型 (Embedded, ARM Linux)",
    "compiler_srs":  "桌面编译器工具 (Desktop, Windows/Linux)",
}

GJB6 = ["1 范围", "2 引用文档", "3 需求", "4 合格性规定", "5 需求可追踪性", "6 注释"]


def read_text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def basic_info(name):
    md_text = read_text(MD[name])
    md_size = os.path.getsize(MD[name])
    pdf_size = os.path.getsize(PDF[name]) if os.path.exists(PDF[name]) else 0
    with open(MID[name], encoding="utf-8") as f:
        mid = json.load(f)
    pages = len(mid["pdf_info"])
    lines = md_text.split("\n")
    # 去除行号前缀后的真实字符数
    chars = len(md_text)
    return {
        "name": name,
        "source_pdf": os.path.basename(PDF[name]),
        "pdf_size_kb": round(pdf_size / 1024, 1),
        "md_size_kb": round(md_size / 1024, 1),
        "pages": pages,
        "md_lines": len(lines),
        "total_chars": chars,
        "system_type": SYS_TYPE[name],
    }


def section_stats(name):
    md_text = read_text(MD[name])
    lines = md_text.split("\n")
    h2 = h3 = h4 = 0
    h2_titles = []
    for ln in lines:
        s = ln.lstrip()
        if s.startswith("#### "):
            h4 += 1
        elif s.startswith("### "):
            h3 += 1
        elif s.startswith("## "):
            h2 += 1
            h2_titles.append(s[3:].strip())
    # GJB 6 必需章节
    joined = "  ".join(h2_titles)
    present = {}
    for sec in GJB6:
        key = sec.split()[0]
        present[sec] = any(re.match(rf"^{re.escape(key)}\b", t) for t in h2_titles)
    # 3.2.x 能力需求子章节
    cap32 = [t for t in h2_titles if re.match(r"^3\.2\.\d+", t)]
    return {
        "total_sections": h2 + h3 + h4,
        "level_distribution": {"h2": h2, "h3": h3, "h4": h4},
        "gjb6_required_sections": present,
        "all_gjb6_present": all(present.values()),
        "capability_3_2_x_count": len(cap32),
        "capability_3_2_x_titles": cap32,
    }


def table_stats(name):
    with open(TBL[name], encoding="utf-8") as f:
        data = json.load(f)
    tables = data["tables"]
    type_dist = Counter(t["table_type"] for t in tables)
    out_tables = []
    for t in tables:
        ncols = len(t.get("headers", []))
        nrows = t.get("num_rows", len(t.get("rows", [])))
        # 内容摘要: 是否为空模板
        rows = t.get("rows", [])
        non_empty = sum(1 for r in rows for c in (r if isinstance(r, list) else [r]) if str(c).strip())
        if t["table_type"] == "modification":
            summary = "空模板(文件更改记录,无数据)"
        elif t["table_type"] == "reference":
            summary = f"已填充({nrows-0}条引用文档)" if non_empty > 0 else "空模板"
        elif t["table_type"] == "qualification":
            summary = "已填充(合格性方法表)" if non_empty > 5 else "部分填充/模板"
        elif t["table_type"] == "traceability":
            # 判断是否是占位符
            placeholder = all(
                all(str(c).strip() in ("", "指标内容", "章节号", "需求名称") for c in (r if isinstance(r, list) else [r]))
                for r in rows[1:] if isinstance(r, list)
            )
            summary = "占位符模板(未填写)" if placeholder else "已填充(追踪关系)"
        else:
            summary = "其他"
        out_tables.append({
            "type": t["table_type"],
            "section": t.get("section", ""),
            "rows": nrows,
            "cols": ncols,
            "content_summary": summary,
        })
    return {
        "total_tables": len(tables),
        "type_distribution": dict(type_dist),
        "tables_detail": out_tables,
    }


def image_stats(name):
    md_text = read_text(MD[name])
    # 正文图片引用 ![](...) 或 <img
    body_refs = len(re.findall(r"!\[.*?\]\(.*?\)|<img", md_text))
    img_dir = f"{BASE}/mineru_srs/{name}.pdf/auto/images"
    files = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))] if os.path.isdir(img_dir) else []
    return {
        "total_image_files": len(files),
        "body_image_references": body_refs,
        "note": "images目录为MinerU页面渲染图,非文档正文插图" if body_refs == 0 else "正文含图片引用",
    }


def constraint_stats():
    if not os.path.exists(CON):
        return None
    with open(CON, encoding="utf-8") as f:
        data = json.load(f)
    cons = data["constraints"]
    by_type = Counter(c["type"] for c in cons)
    by_section = Counter(c["section"].split(" ")[0] for c in cons)
    # 数值约束参数名
    numerical_params = [c["param"] for c in cons if c["type"] in ("numerical", "tolerance", "cumulative")]
    # 同一参数多处出现
    param_occ = defaultdict(list)
    for c in cons:
        param_occ[c["param"]].append({"value": c.get("value", c.get("max", c.get("condition", ""))), "section": c["section"]})
    multi = {p: locs for p, locs in param_occ.items() if len(locs) > 1}
    # 同值多现 (value维度): 统计"25ms"等值出现次数
    value_occ = Counter()
    for c in cons:
        v = c.get("value", "")
        if v:
            value_occ[v] += 1
    return {
        "total": len(cons),
        "by_type": dict(by_type),
        "by_section": dict(by_section),
        "numerical_param_names": list(set(numerical_params)),
        "same_param_multi_occurrence": {p: len(locs) for p, locs in multi.items()},
        "value_frequency_top": dict(value_occ.most_common(8)),
    }


def potential_conflicts(name):
    md_text = read_text(MD[name])
    conflicts = []
    if name == "scheduler_srs":
        conflicts.append({
            "type": "逻辑冲突",
            "description": "3.4.1允许clock_nanosleep失败时采取降级策略'忙等待',但3.12明确'不使用忙等待或usleep'",
            "locations": ["3.4.1 模块间接口规范", "3.12 设计和实现约束"],
            "severity": "高",
        })
        conflicts.append({
            "type": "文本-表格冲突",
            "description": "4合格性表'降采样输出'合格性方法为'功能 测试'(含空格),其余无空格;且表中REQ-3.2.5后两行为注释行被误解析为数据行",
            "locations": ["4 合格性规定"],
            "severity": "低",
        })
        conflicts.append({
            "type": "格式冲突",
            "description": "3.2.4正文'主循环流程'后断行,MinerU将'主循环流'与'程'拆分为两段",
            "locations": ["3.2.4 主循环调度功能"],
            "severity": "低",
        })
        conflicts.append({
            "type": "同参数多值冲突",
            "description": "'运行周期'在1.1描述为'固定周期'(未给数值),在3.1.1/3.2.1/3.10.2等处为25ms;描述粒度不一致",
            "locations": ["1.1 标识", "3.1.1", "3.2.1", "3.10.2"],
            "severity": "低",
        })
    elif name == "battery_srs":
        conflicts.append({
            "type": "逻辑冲突",
            "description": "3.2.5离散步进'总时间不超过1ms'含SOC(0.1ms)+电压(0.1ms)+功率(0.05ms)=0.25ms,余量大;但3.10.2称CPU占用率低于5%而scheduler侧称含模型计算10%,两文档对电池模型CPU占比描述基准不一致",
            "locations": ["3.2.5", "3.10.2"],
            "severity": "中",
        })
        conflicts.append({
            "type": "文本-表格冲突",
            "description": "4合格性表'SOC状态更新'行被OCR拆成两行('单元测'/'试+对比验证'),合格性方法列断裂",
            "locations": ["4 合格性规定"],
            "severity": "中",
        })
        conflicts.append({
            "type": "格式冲突",
            "description": "1.2系统概述电池参数'B=10.354'与3.2.1'B=10.354'一致,但OCR将3.2.1的参数渲染为LaTeX碎片,数值可读性差",
            "locations": ["1.2 系统概述", "3.2.1"],
            "severity": "低",
        })
        conflicts.append({
            "type": "同参数多值冲突",
            "description": "电池模型参数(E0/Q/R/M/B/A)在1.2、3.2.1、3.5三处重复声明,值一致但分布散落,易产生后续修改遗漏",
            "locations": ["1.2", "3.2.1", "3.5"],
            "severity": "低",
        })
    elif name == "compiler_srs":
        conflicts.append({
            "type": "逻辑冲突",
            "description": "3.1声明'单一状态下运行,不需要区分多种状态',但紧接3.1.1/3.1.2/3.1.3列出正常/维护/调试三种状态,自相矛盾",
            "locations": ["3.1", "3.1.1", "3.1.2", "3.1.3"],
            "severity": "高",
        })
        conflicts.append({
            "type": "逻辑冲突",
            "description": "1.2系统概述列出'代码生成、代码优化、错误处理'功能,但3.2软件能力需求仅有3.2.1词法/3.2.2语法/3.2.3语义分析三个模块,缺失代码生成与优化模块的需求定义",
            "locations": ["1.2 系统概述", "3.2 软件能力需求"],
            "severity": "高",
        })
        conflicts.append({
            "type": "逻辑冲突",
            "description": "3.2.1/3.2.2/3.2.3各要求'分析时间不超过5秒',三者串行合计15秒;但3.11要求'编译时间不超过10秒',若包含全部阶段则15s>10s不可满足",
            "locations": ["3.2.1", "3.2.2", "3.2.3", "3.11 软件质量因素"],
            "severity": "高",
        })
        conflicts.append({
            "type": "文本-表格冲突",
            "description": "4合格性规定表全部填写占位符'《GB/T 0028》''合规性方法''合规性级别',与实际3.2.x需求无关,表格未填写真实数据",
            "locations": ["4 合格性规定"],
            "severity": "高",
        })
        conflicts.append({
            "type": "文本-表格冲突",
            "description": "5可追踪性正/逆向表全部为占位符'指标内容''需求名称''章节号',无实际追踪关系",
            "locations": ["5 需求可追踪性"],
            "severity": "高",
        })
        conflicts.append({
            "type": "格式冲突",
            "description": "目录中'3.2.X（软件能力）''3.3.X（接口）'显示'错误！未定义书签',模板占位符未替换",
            "locations": ["目录"],
            "severity": "中",
        })
        conflicts.append({
            "type": "格式冲突",
            "description": "2引用文档表'《GB/T 0018》'版本字段为'0028'(与《GB/T 0028》相同),疑似版本号填写错误",
            "locations": ["2 引用文档"],
            "severity": "中",
        })
    return conflicts


def main():
    docs = []
    names = ["scheduler_srs", "battery_srs", "compiler_srs"]
    total_pages = total_tables = total_constraints = 0
    all_table_types = Counter()
    all_conflict_types = Counter()
    for nm in names:
        bi = basic_info(nm)
        ss = section_stats(nm)
        ts = table_stats(nm)
        im = image_stats(nm)
        cs = constraint_stats() if nm == "scheduler_srs" else None
        pc = potential_conflicts(nm)
        docs.append({
            "name": nm,
            "basic_info": bi,
            "section_stats": ss,
            "table_stats": ts,
            "image_stats": im,
            "constraint_stats": cs,
            "potential_conflicts": pc,
        })
        total_pages += bi["pages"]
        total_tables += ts["total_tables"]
        if cs:
            total_constraints += cs["total"]
        all_table_types.update(ts["type_distribution"])
        for c in pc:
            all_conflict_types[c["type"]] += 1
    cross = {
        "avg_pages": round(total_pages / len(names), 1),
        "avg_tables": round(total_tables / len(names), 1),
        "avg_constraints": round(total_constraints / 1, 1),  # 仅1份有约束
        "common_table_types": [t for t, _ in all_table_types.most_common()],
        "common_conflict_types": [t for t, _ in all_conflict_types.most_common()],
        "constraint_coverage": "仅scheduler_srs完成约束提取(65条);battery/compiler尚未提取",
    }
    out = {
        "analysis_date": "2026-07-28",
        "total_documents": 3,
        "documents": docs,
        "cross_document_summary": cross,
    }
    outpath = f"{BASE}/dataset_statistics.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"written: {outpath}")
    # 简要打印
    for d in docs:
        bi = d["basic_info"]
        print(f"{d['name']}: {bi['pages']}页/{bi['md_lines']}行/{d['table_stats']['total_tables']}表/{len(d['potential_conflicts'])}冲突")


if __name__ == "__main__":
    main()
