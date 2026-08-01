#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
srs_metadata_collector.py
=========================
扫描 GJB 格式 SRS 文档集合，为每份 .md 文件收集细粒度元数据。

扫描子目录:
  - buaa/
  - radar/        (仅扫描 SRS/需求相关 .md)
  - asyncTask/
  - more_gjb/
  - gjb438b/

输出:
  1. data/gjb_438c/srs_collection/gjb_metadata.json         (逐文件元数据)
  2. data/gjb_438c/srs_collection/gjb_metadata_summary.json  (统计汇总)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
COLLECTION_ROOT = Path(
    "/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c/srs_collection"
)
SCAN_DIRS = ["buaa", "radar", "asyncTask", "more_gjb", "gjb438b"]

METADATA_OUT = COLLECTION_ROOT / "gjb_metadata.json"
SUMMARY_OUT = COLLECTION_ROOT / "gjb_metadata_summary.json"


# ---------------------------------------------------------------------------
# radar 子目录过滤：仅保留 SRS / 需求相关 .md
# ---------------------------------------------------------------------------
RADAR_REQ_KEYWORDS = [
    "需求", "规格说明", "研制任务书", "srs", "requirement", "软件需求",
]
# radar 中这些文件名前缀明确属于设计/上下文/协议类，即便命中关键词也排除
RADAR_EXCLUDE_NAMES = {
    "README.md",
    "SKILL.md",
    "format-lock.md",
    "template-structure.md",
    "writing-prompts.md",
}


def _is_radar_srs_related(path: Path, text: str) -> bool:
    """判断 radar 目录下的 .md 是否属于 SRS/需求相关文档。

    判定优先级:
      1) 文件名关键词命中 (需求/规格说明/研制任务书/SRS/requirement)
      2) H1 标题含 SRS/需求规格说明/研制任务书/需求清单 (排除"关于SRS的指南"类元文档)
    """
    name = path.name.lower()
    if name in RADAR_EXCLUDE_NAMES:
        return False
    # 1) 文件名关键词
    for kw in RADAR_REQ_KEYWORDS:
        if kw.lower() in name:
            return True
    # 2) H1 标题内容判定
    title = ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            title = s[2:].strip()
            break
    title_kws = ["需求规格说明", "软件需求", "研制任务书", "需求清单", "SRS", "需求文档"]
    for kw in title_kws:
        if kw in title:
            return True
    return False


# ---------------------------------------------------------------------------
# 语言检测
# ---------------------------------------------------------------------------
def detect_language(text: str) -> str:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    kana = len(re.findall(r"[\u3040-\u30ff]", text))
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    if kana > 0 and kana >= cjk * 0.3:
        return "ja"
    if cjk > ascii_letters:
        return "zh"
    return "en"


# ---------------------------------------------------------------------------
# 标题提取
# ---------------------------------------------------------------------------
def extract_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    # 退而求其次: 第一个非空行
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s[:120]
    return ""


# ---------------------------------------------------------------------------
# GJB 格式 / 版本判定
# ---------------------------------------------------------------------------
def detect_gjb(text: str, has_qualification: bool, has_traceability: bool,
               has_scope: bool, has_requirements: bool) -> Tuple[bool, str]:
    has_csci = "CSCI" in text
    mentions_438c = bool(re.search(r"438\s*C", text, re.IGNORECASE))
    mentions_438b = bool(re.search(r"438\s*B", text, re.IGNORECASE))
    mentions_gjb438 = bool(re.search(r"GJB\s*438", text, re.IGNORECASE))

    strong = has_qualification and has_traceability
    csci_signal = has_csci and (has_qualification or has_traceability or mentions_gjb438 or has_scope and has_requirements)

    is_gjb = strong or csci_signal

    version = "unknown"
    if mentions_438c:
        version = "438C"
    elif mentions_438b:
        version = "438B"
    elif is_gjb and mentions_gjb438:
        version = "438C"
    return is_gjb, version


# ---------------------------------------------------------------------------
# 章节检测
# ---------------------------------------------------------------------------
SECTION_PATTERNS = {
    # 兼容 "## 1 范围" / "## 1. 范围" / "## 1、范围" / "## 范围" / "## Scope"
    "has_scope": re.compile(r"^\s*#{1,4}\s*(?:\d+[.、: ]+)?范围\b|^\s*#{1,4}\s*(?:\d+[.、: ]+)?Scope\b", re.MULTILINE | re.IGNORECASE),
    "has_reference": re.compile(r"^\s*#{1,4}\s*(?:\d+[.、: ]+)?引用(?:文档|文件)\b|^\s*#{1,4}\s*(?:\d+[.、: ]+)?(?:Referenced?\s+Documents?|References)\b", re.MULTILINE | re.IGNORECASE),
    "has_requirements": re.compile(r"^\s*#{1,4}\s*(?:\d+[.、: ]+)?需求\b|^\s*#{1,4}\s*(?:\d+[.、: ]+)?Requirements?\b", re.MULTILINE | re.IGNORECASE),
    "has_qualification": re.compile(r"^\s*#{1,4}\s*(?:\d+[.、: ]+)?合格性规定\b|^\s*#{1,4}\s*(?:\d+[.、: ]+)?Qualification\b", re.MULTILINE | re.IGNORECASE),
    "has_traceability": re.compile(r"^\s*#{1,4}\s*(?:\d+[.、: ]+)?需求?可追踪性\b|^\s*#{1,4}\s*(?:\d+[.、: ]+)?Traceabilit", re.MULTILINE | re.IGNORECASE),
    "has_notes": re.compile(r"^\s*#{1,4}\s*(?:\d+[.、: ]+)?注释\b|^\s*#{1,4}\s*(?:\d+[.、: ]+)?Notes\b", re.MULTILINE | re.IGNORECASE),
}


def detect_sections(text: str) -> Dict:
    flags = {name: bool(pat.search(text)) for name, pat in SECTION_PATTERNS.items()}
    # 引用文档也可能以表格/正文出现而无线上标题，补充正文检测
    if not flags["has_reference"] and re.search(r"引用(?:文档|文件)", text):
        flags["has_reference"] = True
    if not flags["has_qualification"] and "合格性规定" in text:
        flags["has_qualification"] = True
    if not flags["has_traceability"] and ("需求可追踪性" in text or "可追踪性" in text):
        flags["has_traceability"] = True

    # ## 标题数 (level-2 headings)
    section_count = len(re.findall(r"^##\s+", text, re.MULTILINE))
    # 3.2.X 子章节数
    sub_section_32_count = len(re.findall(r"^\s*#{3,5}\s*3\.2\.\d+", text, re.MULTILINE))

    flags["section_count"] = section_count
    flags["sub_section_32_count"] = sub_section_32_count
    return flags


# ---------------------------------------------------------------------------
# 表格检测
# ---------------------------------------------------------------------------
TABLE_TYPE_PATTERNS = [
    ("modification", re.compile(r"修改记录|修订记录|版本历史|修改序号|修订|版本|日期.*修改", re.IGNORECASE)),
    ("reference", re.compile(r"引用(?:文档|文件)|编号.*标题|文献|参考文献|Referenced", re.IGNORECASE)),
    ("qualification", re.compile(r"合格性|测试|验证|确认|方法|Qualification|Test", re.IGNORECASE)),
    ("traceability", re.compile(r"可追踪|追踪|需求ID|需求编号|Traceab", re.IGNORECASE)),
]


def _markdown_table_header_line(block_start_idx: int, lines: List[str]) -> str:
    """返回 markdown 表格的表头行内容。"""
    if block_start_idx + 1 < len(lines):
        return lines[block_start_idx]
    return ""


def detect_tables(text: str) -> Dict:
    lines = text.splitlines()

    html_table_count = len(re.findall(r"<table", text, re.IGNORECASE))

    # markdown 表格: 以 | 开头的连续块 (含分隔行 |---|)
    md_table_count = 0
    md_header_lines: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith("|"):
            # 找分隔行
            if i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
                md_table_count += 1
                md_header_lines.append(line)
                i += 2
                # 跳过表格体
                while i < n and lines[i].strip().startswith("|"):
                    i += 1
                continue
        i += 1

    total_tables = html_table_count + md_table_count
    has_tables = total_tables > 0

    # 推断 table_types: 从表格表头文本判断
    table_types_set = set()
    # 收集所有表头文本(HTML <th> 与 markdown 表头行)
    header_texts = md_header_lines[:]
    th_matches = re.findall(r"<th[^>]*>(.*?)</th>", text, re.IGNORECASE | re.DOTALL)
    header_texts.extend(th_matches)
    # 也扫描表格附近 5 行的标题文本以辅助判断
    header_blob = "\n".join(header_texts)
    # 额外: 扫描每个 "## N 标题" 后紧跟的表格上下文
    for m in re.finditer(r"^#{1,4}\s+.*$", text, re.MULTILINE):
        ctx = text[m.start(): m.start() + 400]
        header_blob += "\n" + ctx

    for ttype, pat in TABLE_TYPE_PATTERNS:
        if pat.search(header_blob):
            table_types_set.add(ttype)

    return {
        "has_tables": has_tables,
        "table_count": total_tables,
        "html_table_count": html_table_count,
        "markdown_table_count": md_table_count,
        "table_types": sorted(table_types_set),
    }


# ---------------------------------------------------------------------------
# 约束检测
# ---------------------------------------------------------------------------
# 带单位的数值 (含比较运算符)
NUMERIC_WITH_UNIT = re.compile(
    r"(?:[≥≤><=±]?\s*\d+(?:\.\d+)?\s*"
    r"(?:ms|µs|us|ns|s|kg|g|km|m|cm|mm|Hz|MHz|GHz|kHz|V|A|W|dB|°C|℃|%|"
    r"MB|GB|KB|TB|字节|次|个|条|项|道|秒|分钟|小时|天|周|月|年|ppm|rpm|"
    r"bps|Kbps|Mbps|Gbps|dpi|fps|Hz|bit|byte|字|帧|包|路|通道|维))"
)
# 比较表达式中的纯数字: >= 10, <= 100, 不少于 5 等
NUMERIC_COMPARE = re.compile(r"(?:[≥≤><=]|不(?:少于|超过|大于|小于)|至少|最多|不超过|不少于)\s*\d+(?:\.\d+)?")


def detect_constraints(text: str) -> Dict:
    nums = NUMERIC_WITH_UNIT.findall(text)
    nums2 = NUMERIC_COMPARE.findall(text)
    numerical_value_count = len(nums) + len(nums2)
    has_numerical_values = numerical_value_count > 0

    # shall 语句: 中文"应" + 英文 "shall"
    # "应" 在 GJB 中表示强制需求; 统计行首/句中 "应" 出现次数(排除"应用"/"应急"等噪声略难, 此处取全部"应"作为近似)
    shall_zh = len(re.findall(r"应(?:提供|能够|可以|支持|满足|保证|实现|具备|包含|包括|描述|给出|允许|确保|限制|符合|执行|输出|输入|接收|响应|显示|保存|记录|处理|检测|判断|返回|调用|创建|删除|修改|查询|生成|发送|接收|启动|停止|重启|校验|加密|验证|测试|统计|导出|导入|上传|下载|配置|设置|切换|具备|为|按|根据|对|在|当|若|如|以)", text))
    shall_en = len(re.findall(r"\bshall\b", text, re.IGNORECASE))
    shall_count = shall_zh + shall_en
    has_shall_statements = shall_count > 0

    csci_count = len(re.findall(r"\bCSCI\b", text))
    has_csci = csci_count > 0

    return {
        "has_numerical_values": has_numerical_values,
        "numerical_value_count": numerical_value_count,
        "has_shall_statements": has_shall_statements,
        "shall_count": shall_count,
        "has_csci": has_csci,
        "csci_count": csci_count,
    }


# ---------------------------------------------------------------------------
# 系统类型推断
# ---------------------------------------------------------------------------
SYSTEM_KEYWORDS = [
    ("aerospace", re.compile(r"雷达|飞行|飞机|航空|航天|卫星|导弹|火箭|阵面|信号处理| FPGA |北斗|GNSS|惯导|雷达检测|相控阵", re.IGNORECASE)),
    ("embedded", re.compile(r"嵌入式|单片机|STM32|ARM|MCU|固件|firmware|bootloader|DSP|实时系统|RTOS|嵌入式系统", re.IGNORECASE)),
    ("web", re.compile(r"Web|前端|后端|Vue|React|Angular|Spring\s*Boot|Springboot|HTTP|网页|网站|浏览器|API|RESTful|Node\.js|Django|Flask|JSP|Servlet|Tomcat|Nginx|前端|后端|客户端/服务器|B/S|C/S", re.IGNORECASE)),
    ("education", re.compile(r"教学|课程|学习|教育|学校|学生|教师|助教|在线学习|课堂|作业|考试|练习|训练|题库|校园|教务|学院|大学|中学|小学", re.IGNORECASE)),
    ("desktop", re.compile(r"桌面|Qt|WPF|WinForm|Electron|GUI|窗口|桌面应用", re.IGNORECASE)),
    ("mobile", re.compile(r"移动|手机|Android|iOS|APP|小程序|移动端", re.IGNORECASE)),
    ("database", re.compile(r"数据库|MySQL|Oracle|PostgreSQL|Redis|MongoDB|数据仓库|DBMS", re.IGNORECASE)),
]


def detect_system_type(title: str, text: str) -> str:
    # 优先用标题 + 前 1500 字符
    blob = (title + "\n" + text[:1500]).lower()
    full = text.lower()
    scores = {}
    for stype, pat in SYSTEM_KEYWORDS:
        c_title = len(pat.findall(blob))
        c_full = len(pat.findall(full))
        scores[stype] = c_title * 3 + c_full
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "unknown"
    return best


# ---------------------------------------------------------------------------
# 需求 ID 提取
# ---------------------------------------------------------------------------
REQ_ID_PATTERNS = [
    re.compile(r"\bREQ[-_][A-Z0-9][A-Z0-9_-]*\b"),
    re.compile(r"\bRX[-_][A-Z][A-Z0-9_]*\b"),
    re.compile(r"\bREQ-\d+(?:\.\d+)*\b"),
]


def extract_req_ids(text: str) -> List[str]:
    ids = []
    seen = set()
    for pat in REQ_ID_PATTERNS:
        for m in pat.findall(text):
            if m not in seen:
                seen.add(m)
                ids.append(m)
    # GJB 3.2.X.Y 子章节 → REQ-3.2.X
    for m in re.findall(r"(?m)^\s*#{3,5}\s+(3\.2\.\d+(?:\.\d+)?)", text):
        rid = "REQ-" + m
        if rid not in seen:
            seen.add(rid)
            ids.append(rid)
    return ids


# ---------------------------------------------------------------------------
# is_filled / is_template 判定
# ---------------------------------------------------------------------------
PLACEHOLDER_PATTERNS = [
    r"\bXXX\b", r"\bxxx\b", r"×××", r"待填写", r"待填", r"〈[^>]*?〉",
    r"\[待", r"【待", r"<<[^>]*?>>", r"\bTBD\b", r"\bTODO\b", r"（待", r"\(\s*待",
    r"占位", r"此处填写", r"请填写", r"〈〈", r"【请填写",
]
# 注意: 不将《...》视为占位符 (中文书名/引用括号); 不将 ___ 视为占位符 (markdown 分隔线噪声)
PLACEHOLDER_RE = re.compile("|".join(PLACEHOLDER_PATTERNS))


def detect_filled_template(text: str, line_count: int, has_numerical: bool) -> Tuple[bool, bool]:
    placeholder_count = len(PLACEHOLDER_RE.findall(text))
    is_template = (line_count < 300) or (placeholder_count >= 8)
    is_filled = (line_count > 500) and has_numerical and (placeholder_count < 8)
    # 模板与填写互斥调整: 若是模板则不算已填写
    if is_template:
        is_filled = False
    return is_filled, is_template


# ---------------------------------------------------------------------------
# 单文件元数据收集
# ---------------------------------------------------------------------------
def collect_metadata(file_path: Path, source_dir: str) -> Dict:
    try:
        raw = file_path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
    except Exception as e:
        return {"file_path": str(file_path), "error": str(e)}

    rel_path = str(file_path.relative_to(COLLECTION_ROOT))
    file_size = len(raw)
    line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
    char_count = len(text)
    # word_count: 中英文混合; 英文按空白分词 + 中文按字符计
    en_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    word_count = en_words + zh_chars

    title = extract_title(text)
    sections = detect_sections(text)
    tables = detect_tables(text)
    constraints = detect_constraints(text)
    is_gjb, gjb_version = detect_gjb(
        text,
        sections["has_qualification"],
        sections["has_traceability"],
        sections["has_scope"],
        sections["has_requirements"],
    )
    system_type = detect_system_type(title, text)
    req_ids = extract_req_ids(text)
    is_filled, is_template = detect_filled_template(
        text, line_count, constraints["has_numerical_values"]
    )
    language = detect_language(text)

    return {
        "file_path": rel_path,
        "filename": file_path.name,
        "source_dir": source_dir,
        "file_size_bytes": file_size,
        "line_count": line_count,
        "word_count": word_count,
        "char_count": char_count,
        "format": "MD",
        "language": language,
        "is_gjb_format": is_gjb,
        "gjb_version": gjb_version,
        "is_filled": is_filled,
        "is_template": is_template,
        "sections": sections,
        "tables": tables,
        "constraints": constraints,
        "system_type": system_type,
        "title": title,
        "req_ids": req_ids,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def scan_directory(subdir: str) -> List[Path]:
    root = COLLECTION_ROOT / subdir
    if not root.exists():
        return []
    return sorted(root.rglob("*.md"))


def main() -> None:
    all_metadata: List[Dict] = []

    for subdir in SCAN_DIRS:
        md_files = scan_directory(subdir)
        for fp in md_files:
            # radar 过滤
            if subdir == "radar":
                try:
                    text = fp.read_bytes().decode("utf-8", errors="replace")
                except Exception:
                    continue
                if not _is_radar_srs_related(fp, text):
                    continue
            meta = collect_metadata(fp, subdir)
            all_metadata.append(meta)

    # 写入逐文件元数据
    METADATA_OUT.write_text(
        json.dumps(all_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] 写入 {len(all_metadata)} 条元数据 -> {METADATA_OUT}")

    # ------------------------------------------------------------------
    # 统计汇总
    # ------------------------------------------------------------------
    total = len(all_metadata)
    gjb_docs = [m for m in all_metadata if m.get("is_gjb_format")]
    filled_docs = [m for m in all_metadata if m.get("is_filled")]
    template_docs = [m for m in all_metadata if m.get("is_template")]

    by_system: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    by_version: Dict[str, int] = {}
    for m in all_metadata:
        st = m.get("system_type", "unknown")
        by_system[st] = by_system.get(st, 0) + 1
        sd = m.get("source_dir", "unknown")
        by_source[sd] = by_source.get(sd, 0) + 1
        ver = m.get("gjb_version", "unknown")
        by_version[ver] = by_version.get(ver, 0) + 1

    avg_lines = (sum(m["line_count"] for m in all_metadata) / total) if total else 0
    avg_words = (sum(m["word_count"] for m in all_metadata) / total) if total else 0
    total_tables = sum(m["tables"]["table_count"] for m in all_metadata)

    all_req_ids = set()
    for m in all_metadata:
        all_req_ids.update(m.get("req_ids", []))

    # 章节完整性: 6 章齐全
    six_section_keys = [
        "has_scope", "has_reference", "has_requirements",
        "has_qualification", "has_traceability", "has_notes",
    ]
    complete_section_docs = [
        m for m in all_metadata
        if all(m["sections"].get(k) for k in six_section_keys)
    ]
    # GJB 核心 5 章 (无 notes)
    core_section_keys = [
        "has_scope", "has_reference", "has_requirements",
        "has_qualification", "has_traceability",
    ]
    core_complete_docs = [
        m for m in all_metadata
        if all(m["sections"].get(k) for k in core_section_keys)
    ]

    # 章节出现频次
    section_freq = {k: 0 for k in six_section_keys}
    for m in all_metadata:
        for k in six_section_keys:
            if m["sections"].get(k):
                section_freq[k] += 1

    summary = {
        "total_documents": total,
        "gjb_format_documents": len(gjb_docs),
        "filled_documents": len(filled_docs),
        "template_documents": len(template_docs),
        "by_system_type": by_system,
        "by_source_dir": by_source,
        "by_gjb_version": by_version,
        "avg_line_count": round(avg_lines, 1),
        "avg_word_count": round(avg_words, 1),
        "total_tables": total_tables,
        "total_req_ids": len(all_req_ids),
        "section_completeness": {
            "six_sections_complete_docs": len(complete_section_docs),
            "core_five_sections_complete_docs": len(core_complete_docs),
            "section_frequency": section_freq,
        },
        "constraints_stats": {
            "docs_with_numerical_values": sum(1 for m in all_metadata if m["constraints"]["has_numerical_values"]),
            "docs_with_shall_statements": sum(1 for m in all_metadata if m["constraints"]["has_shall_statements"]),
            "docs_with_csci": sum(1 for m in all_metadata if m["constraints"]["has_csci"]),
            "total_numerical_values": sum(m["constraints"]["numerical_value_count"] for m in all_metadata),
            "total_shall_statements": sum(m["constraints"]["shall_count"] for m in all_metadata),
            "total_csci_mentions": sum(m["constraints"]["csci_count"] for m in all_metadata),
        },
    }

    SUMMARY_OUT.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] 写入统计汇总 -> {SUMMARY_OUT}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
