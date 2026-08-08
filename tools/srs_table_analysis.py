#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRS表格深度分析脚本
分析16份GJB 438C SRS文档中所有表格的结构、内容、一致性
输出: analysis_output/table_analysis_report.json
"""
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

STRUCTURED_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c/mineru_structured")
OUTPUT_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/analysis_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_all_docs():
    docs = {}
    for f in sorted(STRUCTURED_DIR.glob("*_structured.json")):
        with open(f) as fh:
            d = json.load(fh)
        docs[d["doc_name"]] = d
    return docs


# ---------- helpers ----------
SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)")


def extract_section_num(s):
    """从字符串中提取开头的章节号, 如 '3.2.1 功能描述' -> '3.2.1'"""
    if not s:
        return None
    s = str(s).strip()
    m = SECTION_RE.match(s)
    return m.group(1) if m else None


def normalize_sec(s):
    """标准化章节号字符串"""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    m = SECTION_RE.match(s)
    return m.group(1) if m else None


def is_chapter3_section(sec_id):
    """判断章节号是否属于第3章"""
    if not sec_id:
        return False
    return sec_id.startswith("3") and sec_id != "3"


# ============================================================
# 1. 表格概览统计
# ============================================================
def analyze_table_overview(doc_name, doc):
    """统计每份文档的表格分布"""
    result = {
        "doc_name": doc_name,
        "total_tables": 0,
        "tables_with_caption": 0,
        "tables_without_caption": 0,
        "empty_caption_count": 0,
        "caption_format_issues": [],
        "table_type_distribution": Counter(),
        "tables_by_section_chapter": Counter(),
        "table_row_count_stats": {"min": None, "max": None, "total": 0},
        "empty_tables": [],  # 只有表头没有数据行
        "tables_list": [],
    }

    all_tables = []
    for sec_id, sec in doc["sections"].items():
        for t in sec.get("tables", []):
            tid = t.get("table_id", "")
            cap = t.get("caption", "") or ""
            headers = t.get("headers", [])
            rows = t.get("rows", [])
            row_count = t.get("row_count", len(rows))
            ttype = t.get("type", "unknown")

            result["total_tables"] += 1
            result["table_type_distribution"][ttype] += 1

            # chapter of section
            ch = sec_id.split(".")[0] if sec_id else "?"
            result["tables_by_section_chapter"][ch] += 1

            # row stats
            result["table_row_count_stats"]["total"] += row_count
            if result["table_row_count_stats"]["min"] is None or row_count < result["table_row_count_stats"]["min"]:
                result["table_row_count_stats"]["min"] = row_count
            if result["table_row_count_stats"]["max"] is None or row_count > result["table_row_count_stats"]["max"]:
                result["table_row_count_stats"]["max"] = row_count

            # caption
            if cap.strip():
                result["tables_with_caption"] += 1
            else:
                result["tables_without_caption"] += 1
                result["empty_caption_count"] += 1

            # caption format: 检查是否含 SEQ / ARABIC 等未渲染字段
            if cap and ("SEQ" in cap or "ARABIC" in cap or "* ARABIC" in cap):
                result["caption_format_issues"].append({
                    "table_id": tid, "section": sec_id, "caption": cap
                })

            # empty table: 只有表头, 没有数据行
            if row_count == 0 or len(rows) == 0:
                result["empty_tables"].append({
                    "table_id": tid, "section": sec_id, "caption": cap,
                    "headers": headers
                })

            all_tables.append({
                "table_id": tid,
                "section": sec_id,
                "caption": cap,
                "type": ttype,
                "row_count": row_count,
                "header_count": len(headers),
            })

    result["tables_list"] = all_tables
    # convert counters
    result["table_type_distribution"] = dict(result["table_type_distribution"])
    result["tables_by_section_chapter"] = dict(result["tables_by_section_chapter"])
    return result


# ============================================================
# 2. 合格性表分析 (section 4)
# ============================================================
def find_qualification_table(doc):
    """定位合格性表 - 通常在section '4' 中"""
    candidates = []
    for sec_id, sec in doc["sections"].items():
        if sec_id == "4" or sec_id.startswith("4."):
            for t in sec.get("tables", []):
                cap = (t.get("caption") or "").lower()
                # 合格性表特征: 表头含"合格性方法" 或 caption含"合格性"
                headers = t.get("headers", [])
                if any("合格性" in h for h in headers) or "合格性" in cap or "合格" in cap:
                    candidates.append((sec_id, t))
    # fallback: 如果没找到, 找section 4的所有表
    if not candidates and "4" in doc["sections"]:
        for t in doc["sections"]["4"].get("tables", []):
            candidates.append(("4", t))
    return candidates


def analyze_qualification_table(doc_name, doc):
    result = {
        "doc_name": doc_name,
        "found": False,
        "section": None,
        "table_id": None,
        "caption": None,
        "headers": None,
        "header_count": None,
        "header_layout": None,     # "v1_name_embeds_sec" 或 "v2_dedicated_sec_col"
        "sec_col_index": None,     # 章节号所在列
        "method_col_index": None,
        "level_col_index": None,
        "testtype_col_index": None,
        "row_count": 0,
        "section_refs": [],
        "method_distribution": Counter(),
        "test_type_distribution": Counter(),
        "level_distribution": Counter(),
        "method_level_matrix": Counter(),
        "non_section_rows": [],
        "ch3_actual_sections": [],
        "ch3_leaf_sections": [],
        "matching_analysis": {
            "matched": 0,
            "ghost_refs": [],
            "ch3_not_in_table": [],
            "ch3_leaf_not_in_table": [],
            "systematic_offset": None,
        },
    }

    cands = find_qualification_table(doc)
    if not cands:
        return result

    sec_id, t = cands[0]
    result["found"] = True
    result["section"] = sec_id
    result["table_id"] = t.get("table_id")
    result["caption"] = t.get("caption")
    result["headers"] = t.get("headers")
    result["header_count"] = len(t.get("headers", []))
    rows = t.get("rows", [])
    result["row_count"] = len(rows)
    headers = t.get("headers", [])

    # ---- 检测列布局 ----
    sec_col_idx = None
    method_col_idx = None
    level_col_idx = None
    testtype_col_idx = None
    for j, h in enumerate(headers):
        h_str = str(h) if h else ""
        if "章节号" in h_str:
            sec_col_idx = j
        if "合格性方法" in h_str:
            method_col_idx = j
        if "合格性级别" in h_str:
            level_col_idx = j
        if "测试类" in h_str:
            testtype_col_idx = j

    # 如果没有明确的"章节号"列, 通过扫描数据找到含章节号的列
    if sec_col_idx is None:
        # 统计每列中能解析为章节号的cell数量
        col_scores = []
        for j in range(len(headers)):
            score = 0
            for row in rows[:20]:  # 取前20行采样
                if j < len(row) and row[j]:
                    if normalize_sec(str(row[j])):
                        score += 1
            col_scores.append((j, score))
        col_scores.sort(key=lambda x: -x[1])
        if col_scores and col_scores[0][1] > 0:
            sec_col_idx = col_scores[0][0]
        result["header_layout"] = "v1_name_embeds_sec"
    else:
        result["header_layout"] = "v2_dedicated_sec_col"

    result["sec_col_index"] = sec_col_idx
    result["method_col_index"] = method_col_idx
    result["level_col_index"] = level_col_idx
    result["testtype_col_index"] = testtype_col_idx

    # 收集第3章实际章节号
    ch3_sections = set()
    for s in doc["sections"].keys():
        if is_chapter3_section(s):
            ch3_sections.add(s)
    result["ch3_actual_sections"] = sorted(ch3_sections)
    ch3_set = set(ch3_sections)

    # ch3叶子节点: 没有其他section以它为前缀的节点
    all_ch3 = sorted(ch3_sections)
    leaf_set = set()
    for s in all_ch3:
        prefix = s + "."
        is_leaf = not any(other.startswith(prefix) for other in all_ch3 if other != s)
        if is_leaf:
            leaf_set.add(s)
    result["ch3_leaf_sections"] = sorted(leaf_set)

    # 解析每行
    refs_in_table = set()
    for i, row in enumerate(rows):
        if not row:
            continue
        # 从检测到的列提取章节号
        sec_num = None
        if sec_col_idx is not None and sec_col_idx < len(row):
            cell = row[sec_col_idx]
            sec_num = normalize_sec(str(cell)) if cell else None

        method = ""
        test_type = ""
        level = ""
        if method_col_idx is not None and method_col_idx < len(row):
            method = str(row[method_col_idx]).strip() if row[method_col_idx] else ""
        if testtype_col_idx is not None and testtype_col_idx < len(row):
            test_type = str(row[testtype_col_idx]).strip() if row[testtype_col_idx] else ""
        if level_col_idx is not None and level_col_idx < len(row):
            level = str(row[level_col_idx]).strip() if row[level_col_idx] else ""

        if sec_num:
            refs_in_table.add(sec_num)
            result["section_refs"].append(sec_num)
            if method and method not in ("—", "", "-"):
                result["method_distribution"][method] += 1
            if test_type and test_type not in ("—", "", "-"):
                result["test_type_distribution"][test_type] += 1
            if level and level not in ("—", "", "-"):
                result["level_distribution"][level] += 1
            if method and level and method not in ("—", "") and level not in ("—", ""):
                result["method_level_matrix"][f"{method}|{level}"] += 1
        else:
            result["non_section_rows"].append({
                "row_index": i,
                "sec_col_value": str(row[sec_col_idx]) if sec_col_idx is not None and sec_col_idx < len(row) else "",
                "row_preview": [str(c)[:30] if c else "" for c in row[:4]],
            })

    result["section_refs"] = sorted(set(result["section_refs"]))

    # 匹配分析
    table_refs = set(refs_in_table)
    ch3_ghost = {r for r in (table_refs - ch3_set) if r.startswith("3")}
    result["matching_analysis"]["ghost_refs"] = sorted(ch3_ghost)

    ch3_missing = ch3_set - table_refs
    result["matching_analysis"]["ch3_not_in_table"] = sorted(ch3_missing)
    # 叶子级别的缺失(更有意义)
    result["matching_analysis"]["ch3_leaf_not_in_table"] = sorted(leaf_set - table_refs)
    result["matching_analysis"]["matched"] = len(table_refs & ch3_set)

    # 系统性偏移检测(只在ghost较多时尝试)
    if len(ch3_ghost) >= 3 and table_refs and ch3_set:
        for offset in [-1, +1, -2, +2]:
            mapped = set()
            for r in table_refs:
                parts = r.split(".")
                try:
                    last = int(parts[-1]) + offset
                    if last < 0:
                        continue
                    mapped_ref = ".".join(parts[:-1] + [str(last)])
                    mapped.add(mapped_ref)
                except (ValueError, IndexError):
                    continue
            overlap = mapped & ch3_set
            if len(overlap) >= len(table_refs) * 0.5 and len(overlap) >= 5:
                result["matching_analysis"]["systematic_offset"] = offset
                break

    result["method_distribution"] = dict(result["method_distribution"])
    result["test_type_distribution"] = dict(result["test_type_distribution"])
    result["level_distribution"] = dict(result["level_distribution"])
    result["method_level_matrix"] = dict(result["method_level_matrix"])
    return result


# ============================================================
# 3. 追溯表分析 (section 5.1 / 5.2)
# ============================================================
def find_traceability_tables(doc):
    """定位追溯表 - 返回 (forward_table, reverse_table, forward_sec, reverse_sec)
    两种模式:
    1. 5.1/5.2 分别有表 (doc01, doc12)
    2. section 5 下有两个表, 第一个正向第二个逆向 (doc03+)
    """
    forward_t, forward_sec = None, None
    reverse_t, reverse_sec = None, None

    # 模式1: 5.1/5.2
    if "5.1" in doc["sections"]:
        for t in doc["sections"]["5.1"].get("tables", []):
            forward_t, forward_sec = t, "5.1"
            break
    if "5.2" in doc["sections"]:
        for t in doc["sections"]["5.2"].get("tables", []):
            reverse_t, reverse_sec = t, "5.2"
            break

    # 模式2: section 5 下两个表
    if forward_t is None and "5" in doc["sections"]:
        tables = doc["sections"]["5"].get("tables", [])
        if len(tables) >= 1:
            forward_t, forward_sec = tables[0], "5"
        if len(tables) >= 2:
            reverse_t, reverse_sec = tables[1], "5"

    return forward_t, reverse_t, forward_sec, reverse_sec


def extract_trace_refs(t, doc_side="this"):
    """从追溯表中提取'本文档'的章节号
    doc_side='this': 提取本文档章节号
    doc_side='upper': 提取上级文档章节号
    """
    if t is None:
        return set(), []
    headers = t.get("headers", [])
    rows = t.get("rows", [])

    # 找"本文档的章节号"列 和 "上级文档的章节号"列
    this_col = None
    upper_col = None
    for j, h in enumerate(headers):
        h_str = str(h) if h else ""
        if "本文档" in h_str and "章节号" in h_str:
            this_col = j
        if ("上级" in h_str or "任务书" in h_str or "研制" in h_str) and "章节号" in h_str:
            upper_col = j

    # 如果没有专门的章节号列, 尝试从名称列提取
    target_col = this_col if doc_side == "this" else upper_col
    if target_col is None:
        # fallback: 找含"本文档"或"上级"的名称列, 从中提取章节号
        name_col = None
        for j, h in enumerate(headers):
            h_str = str(h) if h else ""
            if doc_side == "this" and "本文档" in h_str and ("名称" in h_str or "追踪" in h_str):
                name_col = j
                break
            if doc_side == "upper" and ("上级" in h_str or "任务书" in h_str) and ("名称" in h_str or "追踪" in h_str):
                name_col = j
                break
        target_col = name_col

    if target_col is None:
        return set(), []

    refs = set()
    non_section_rows = []
    for i, row in enumerate(rows):
        if not row or target_col >= len(row):
            continue
        cell = row[target_col]
        if cell is None or str(cell).strip() == "":
            continue
        sec_num = normalize_sec(str(cell))
        if sec_num:
            refs.add(sec_num)
        else:
            non_section_rows.append({"row_index": i, "value": str(cell)[:50]})
    return refs, non_section_rows


def analyze_traceability_table(doc_name, doc):
    result = {
        "doc_name": doc_name,
        "forward": {"found": False, "section": None, "table_id": None,
                    "caption": None, "headers": None, "row_count": 0,
                    "this_doc_refs": [], "upper_doc_refs": [],
                    "non_section_rows": [],
                    "ch3_coverage": [], "ch3_missing": [], "ghost_refs": []},
        "reverse": {"found": False, "section": None, "table_id": None,
                    "caption": None, "headers": None, "row_count": 0,
                    "this_doc_refs": [], "upper_doc_refs": [],
                    "non_section_rows": [],
                    "ch3_coverage": [], "ch3_missing": [], "ghost_refs": []},
        "forward_reverse_consistent": None,
    }

    ch3_set = set(s for s in doc["sections"].keys() if is_chapter3_section(s))

    fwd_t, rev_t, fwd_sec, rev_sec = find_traceability_tables(doc)

    for direction, t, sec_id in [("forward", fwd_t, fwd_sec), ("reverse", rev_t, rev_sec)]:
        if t is None:
            continue
        result[direction]["found"] = True
        result[direction]["section"] = sec_id
        result[direction]["table_id"] = t.get("table_id")
        result[direction]["caption"] = t.get("caption")
        result[direction]["headers"] = t.get("headers")
        result[direction]["row_count"] = len(t.get("rows", []))

        this_refs, non_sec = extract_trace_refs(t, "this")
        upper_refs, _ = extract_trace_refs(t, "upper")
        result[direction]["this_doc_refs"] = sorted(this_refs)
        result[direction]["upper_doc_refs"] = sorted(upper_refs)
        result[direction]["non_section_rows"] = non_sec

        ch3_in_table = this_refs & ch3_set
        result[direction]["ch3_coverage"] = sorted(ch3_in_table)
        result[direction]["ch3_missing"] = sorted(ch3_set - this_refs)
        ghost = {r for r in this_refs - ch3_set if r.startswith("3")}
        result[direction]["ghost_refs"] = sorted(ghost)

    # 正向逆向一致性
    if result["forward"]["found"] and result["reverse"]["found"]:
        fwd_set = set(result["forward"]["this_doc_refs"])
        rev_set = set(result["reverse"]["this_doc_refs"])
        result["forward_reverse_consistent"] = {
            "only_in_forward": sorted(fwd_set - rev_set),
            "only_in_reverse": sorted(rev_set - fwd_set),
            "common": len(fwd_set & rev_set),
            "is_symmetric": fwd_set == rev_set,
        }

    return result


# ============================================================
# 4. Caption连续性分析
# ============================================================
def analyze_caption_continuity(doc_name, doc):
    result = {
        "doc_name": doc_name,
        "total_tables": 0,
        "captions_with_number": [],
        "caption_numbers": [],
        "max_number": None,
        "missing_numbers": [],
        "duplicate_numbers": [],
        "seq_format_count": 0,
        "seq_format_examples": [],
        "no_caption_tables": [],
    }

    CAP_NUM_RE = re.compile(r"表\s*(\d+)")
    all_caps = []
    for sec_id, sec in doc["sections"].items():
        for t in sec.get("tables", []):
            result["total_tables"] += 1
            cap = t.get("caption") or ""
            tid = t.get("table_id", "")
            if not cap.strip():
                result["no_caption_tables"].append({"table_id": tid, "section": sec_id})
                continue
            # 检查SEQ格式
            if "SEQ" in cap or "ARABIC" in cap:
                result["seq_format_count"] += 1
                if len(result["seq_format_examples"]) < 3:
                    result["seq_format_examples"].append({"table_id": tid, "section": sec_id, "caption": cap})
            m = CAP_NUM_RE.search(cap)
            if m:
                num = int(m.group(1))
                result["caption_numbers"].append(num)
                result["captions_with_number"].append({
                    "table_id": tid, "section": sec_id, "number": num, "caption": cap
                })
                all_caps.append(num)

    # 连续性
    if all_caps:
        result["max_number"] = max(all_caps)
        sorted_nums = sorted(set(all_caps))
        full_range = set(range(1, max(all_caps) + 1))
        result["missing_numbers"] = sorted(full_range - set(all_caps))
        # 重复
        cnt = Counter(all_caps)
        result["duplicate_numbers"] = [{"number": n, "count": c} for n, c in cnt.items() if c > 1]

    return result


# ============================================================
# 5. 表格内容质量
# ============================================================
def analyze_table_quality(doc_name, doc):
    result = {
        "doc_name": doc_name,
        "empty_tables": [],
        "single_header_tables": [],
        "row_mismatch": [],   # row_count与实际rows长度不一致
        "ocr_issues": [],
        "tables_with_empty_cells": [],
        "total_empty_cell_count": 0,
    }

    for sec_id, sec in doc["sections"].items():
        for t in sec.get("tables", []):
            tid = t.get("table_id", "")
            cap = t.get("caption") or ""
            headers = t.get("headers", [])
            rows = t.get("rows", [])
            row_count = t.get("row_count", len(rows))

            # 空表
            if len(rows) == 0:
                result["empty_tables"].append({
                    "table_id": tid, "section": sec_id, "caption": cap,
                    "headers": headers
                })
                continue

            # row_count不匹配
            if row_count != len(rows):
                result["row_mismatch"].append({
                    "table_id": tid, "section": sec_id, "caption": cap,
                    "declared_row_count": row_count, "actual_rows": len(rows)
                })

            # 单列表(只有一个header)
            if len(headers) <= 1:
                result["single_header_tables"].append({
                    "table_id": tid, "section": sec_id, "caption": cap,
                    "headers": headers
                })

            # 空cell统计
            empty_cells = 0
            for row in rows:
                for cell in row:
                    if cell is None or str(cell).strip() == "":
                        empty_cells += 1
            if empty_cells > 0:
                result["tables_with_empty_cells"].append({
                    "table_id": tid, "section": sec_id, "caption": cap,
                    "empty_cell_count": empty_cells,
                    "total_cells": sum(len(r) for r in rows)
                })
                result["total_empty_cell_count"] += empty_cells

            # OCR问题: 检测乱码/特殊字符
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    if cell is None:
                        continue
                    s = str(cell)
                    # 检测SEQ残留
                    if "SEQ" in s or "ARABIC" in s:
                        result["ocr_issues"].append({
                            "table_id": tid, "section": sec_id, "row": i, "col": j,
                            "issue": "seq_field_residue", "value": s[:80]
                        })
                    # 检测HTML残留
                    if "<table" in s.lower() or "</td>" in s.lower() or "<td" in s.lower():
                        result["ocr_issues"].append({
                            "table_id": tid, "section": sec_id, "row": i, "col": j,
                            "issue": "html_residue", "value": s[:80]
                        })

    return result


# ============================================================
# 6. 跨表格一致性
# ============================================================
def analyze_cross_table_consistency(doc_name, doc):
    """合格性表 vs 追溯表 vs 第3章"""
    result = {
        "doc_name": doc_name,
        "qualification_refs": [],
        "forward_trace_refs": [],
        "reverse_trace_refs": [],
        "ch3_sections": [],
        "qual_vs_ch3": {"only_in_qual": [], "only_in_ch3": [], "common": 0},
        "trace_vs_ch3": {"only_in_trace": [], "only_in_ch3": [], "common": 0},
        "qual_vs_trace": {"only_in_qual": [], "only_in_trace": [], "common": 0},
        "qual_row_count": 0,
        "ch3_requirement_count": 0,
    }

    ch3_set = set(s for s in doc["sections"].keys() if is_chapter3_section(s))
    result["ch3_sections"] = sorted(ch3_set)

    # qual refs - 使用与qualification分析相同的列检测逻辑
    qual_cands = find_qualification_table(doc)
    if qual_cands:
        _, t = qual_cands[0]
        result["qual_row_count"] = len(t.get("rows", []))
        headers = t.get("headers", [])
        rows = t.get("rows", [])
        # 检测章节号列
        sec_col = None
        for j, h in enumerate(headers):
            if "章节号" in str(h):
                sec_col = j
                break
        if sec_col is None:
            # 扫描数据找到含章节号的列
            best_j, best_score = 0, 0
            for j in range(len(headers)):
                score = sum(1 for row in rows[:20] if j < len(row) and row[j] and normalize_sec(str(row[j])))
                if score > best_score:
                    best_j, best_score = j, score
            sec_col = best_j
        for row in rows:
            if row and sec_col < len(row) and row[sec_col]:
                sn = normalize_sec(str(row[sec_col]))
                if sn:
                    result["qualification_refs"].append(sn)
    qual_set = set(result["qualification_refs"])

    # trace refs (合并5.1+5.2)
    trace_set = set()
    fwd_t, rev_t, _, _ = find_traceability_tables(doc)
    for t in [fwd_t, rev_t]:
        if t is None:
            continue
        this_refs, _ = extract_trace_refs(t, "this")
        trace_set |= this_refs
        if t is fwd_t:
            result["forward_trace_refs"] = sorted(this_refs)
        else:
            result["reverse_trace_refs"] = sorted(this_refs)

    # 比较
    result["qual_vs_ch3"]["only_in_qual"] = sorted(qual_set - ch3_set)
    result["qual_vs_ch3"]["only_in_ch3"] = sorted(ch3_set - qual_set)
    result["qual_vs_ch3"]["common"] = len(qual_set & ch3_set)

    result["trace_vs_ch3"]["only_in_trace"] = sorted(trace_set - ch3_set)
    result["trace_vs_ch3"]["only_in_ch3"] = sorted(ch3_set - trace_set)
    result["trace_vs_ch3"]["common"] = len(trace_set & ch3_set)

    result["qual_vs_trace"]["only_in_qual"] = sorted(qual_set - trace_set)
    result["qual_vs_trace"]["only_in_trace"] = sorted(trace_set - qual_set)
    result["qual_vs_trace"]["common"] = len(qual_set & trace_set)

    # ch3需求数量(只计叶子节点: 3.x.y 形式, 非父章节)
    # 这里简化: 统计所有3章section数
    result["ch3_requirement_count"] = len(ch3_set)
    return result


# ============================================================
# Main
# ============================================================
def main():
    docs = load_all_docs()
    print(f"Loaded {len(docs)} docs")

    full_report = {
        "summary": {},
        "overview": [],
        "qualification": [],
        "traceability": [],
        "caption_continuity": [],
        "table_quality": [],
        "cross_table": [],
    }

    # 汇总统计
    total_tables = 0
    total_qual_tables = 0
    total_forward_trace = 0
    total_reverse_trace = 0
    type_dist = Counter()
    all_method_dist = Counter()
    all_level_dist = Counter()
    all_qual_ghost = 0
    all_qual_missing = 0
    all_trace_ghost = 0
    all_seq_format = 0
    all_empty_caption = 0
    all_empty_tables = 0

    for doc_name, doc in docs.items():
        # 1. overview
        ov = analyze_table_overview(doc_name, doc)
        full_report["overview"].append(ov)
        total_tables += ov["total_tables"]
        for k, v in ov["table_type_distribution"].items():
            type_dist[k] += v
        all_empty_caption += ov["empty_caption_count"]
        all_empty_tables += len(ov["empty_tables"])

        # 2. qualification
        qual = analyze_qualification_table(doc_name, doc)
        full_report["qualification"].append(qual)
        if qual["found"]:
            total_qual_tables += 1
            for k, v in qual["method_distribution"].items():
                all_method_dist[k] += v
            for k, v in qual["level_distribution"].items():
                all_level_dist[k] += v
            all_qual_ghost += len(qual["matching_analysis"]["ghost_refs"])
            all_qual_missing += len(qual["matching_analysis"]["ch3_not_in_table"])

        # 3. traceability
        tr = analyze_traceability_table(doc_name, doc)
        full_report["traceability"].append(tr)
        if tr["forward"]["found"]:
            total_forward_trace += 1
            all_trace_ghost += len(tr["forward"]["ghost_refs"])
        if tr["reverse"]["found"]:
            total_reverse_trace += 1
            all_trace_ghost += len(tr["reverse"]["ghost_refs"])

        # 4. caption
        cc = analyze_caption_continuity(doc_name, doc)
        full_report["caption_continuity"].append(cc)
        all_seq_format += cc["seq_format_count"]

        # 5. quality
        tq = analyze_table_quality(doc_name, doc)
        full_report["table_quality"].append(tq)

        # 6. cross
        cr = analyze_cross_table_consistency(doc_name, doc)
        full_report["cross_table"].append(cr)

    full_report["summary"] = {
        "total_docs": len(docs),
        "total_tables": total_tables,
        "docs_with_qualification_table": total_qual_tables,
        "docs_with_forward_trace": total_forward_trace,
        "docs_with_reverse_trace": total_reverse_trace,
        "global_type_distribution": dict(type_dist),
        "global_method_distribution": dict(all_method_dist),
        "global_level_distribution": dict(all_level_dist),
        "total_qual_ghost_refs": all_qual_ghost,
        "total_qual_missing_ch3": all_qual_missing,
        "total_trace_ghost_refs": all_trace_ghost,
        "total_seq_format_captions": all_seq_format,
        "total_empty_captions": all_empty_caption,
        "total_empty_tables": all_empty_tables,
    }

    out_path = OUTPUT_DIR / "table_analysis_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {out_path}")

    # print summary
    print("\n=== SUMMARY ===")
    for k, v in full_report["summary"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
