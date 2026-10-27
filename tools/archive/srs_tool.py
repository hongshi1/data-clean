#!/usr/bin/env python3
"""
SRS一致性检测工具集
===================
5个工具函数, 纯Python实现(标准库+z3), 不依赖DataFlow/AgentFlow。
后续可包装为AgentFlow的BaseApiTool或DataFlow的Operator。

工具:
  1. srs_search       — 全局检索SRS内容 (改自DocDancer doc_tool.py:436)
  2. srs_read_section — 读取章节内容 (改自DocDancer doc_tool.py:575)
  3. srs_read_table   — 读取表格行
  4. srs_z3_check     — Z3约束可满足性校验 (独创)
  5. srs_lint         — 语法层规则检测 (独创)

用法: 被srs_detect.py调用
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict


# ── 工具1: srs_search (改自DocDancer doc_tool.py:436 single_search) ──────

def srs_search(query: str, content_xml_path: str) -> list[dict]:
    """
    全局检索SRS内容。
    
    改自 DocDancer sandbox/server/backends/tools/doc_tool.py:436 single_search
    改动: 数据源从PDF的all_content.xml改为SRS的content.xml
    
    输入: query(关键词), content_xml_path
    输出: [{section_id, type, snippet, table_id?, row_index?}]
    """
    content = ET.parse(content_xml_path).getroot()
    results = []
    
    for section in content.findall('.//Section'):
        section_id = section.get('section_id', '')
        title = section.get('title', '')
        
        # 搜索标题
        if query in title:
            results.append({
                "section_id": section_id,
                "type": "section_title",
                "snippet": title
            })
        
        # 搜索段落 (复用doc_tool.py:451-456的遍历逻辑)
        for para in section.findall('Paragraph'):
            text = para.text or ''
            if query in text:
                # 截取上下文 (复用doc_tool.py:81 make_snippet)
                idx = text.find(query)
                start = max(0, idx - 30)
                end = min(len(text), idx + len(query) + 50)
                snippet = text[start:end]
                results.append({
                    "section_id": section_id,
                    "type": "paragraph",
                    "line": para.get('line', ''),
                    "snippet": snippet
                })
        
        # 搜索表格行 (SRS特有)
        for table in section.findall('Table'):
            table_id = table.get('table_id', '')
            table_type = table.get('type', '')
            for row_idx, row in enumerate(table.findall('Row')):
                cells = [c.text or '' for c in row.findall('Cell')]
                row_text = ' '.join(cells)
                if query in row_text:
                    results.append({
                        "section_id": section_id,
                        "type": "table_row",
                        "table_id": table_id,
                        "table_type": table_type,
                        "row_index": row_idx,
                        "snippet": row_text[:100]
                    })
    
    # 搜索全局表格 (不在章节内的表格)
    for table in content.findall('Table'):
        if table.get('section_id'):
            continue  # 已在章节内处理
        table_id = table.get('table_id', '')
        table_type = table.get('type', '')
        for row_idx, row in enumerate(table.findall('Row')):
            cells = [c.text or '' for c in row.findall('Cell')]
            row_text = ' '.join(cells)
            if query in row_text:
                results.append({
                    "section_id": "",
                    "type": "table_row",
                    "table_id": table_id,
                    "table_type": table_type,
                    "row_index": row_idx,
                    "snippet": row_text[:100]
                })
    
    return results


# ── 工具2: srs_read_section (改自DocDancer doc_tool.py:575 _single_read) ──

def srs_read_section(section_id: str, content_xml_path: str) -> dict:
    """
    读取指定章节的完整内容。
    
    改自 DocDancer doc_tool.py:575 _single_read
    改动: 去掉VLM多模态处理,改为纯文本+表格输出
    
    输入: section_id(如"3.2.1"), content_xml_path
    输出: {section_id, title, text, tables:[...], images:[...], req_id?}
    """
    content = ET.parse(content_xml_path).getroot()
    
    # 查找章节 (复用doc_tool.py:580)
    section = content.find(f'.//Section[@section_id="{section_id}"]')
    if section is None:
        return {"error": f"Section {section_id} not found"}
    
    # 提取文本 (复用doc_tool.py:585-590)
    paragraphs = [p.text for p in section.findall('Paragraph') if p.text]
    text = '\n'.join(paragraphs)
    
    # 提取表格
    tables = []
    for table in section.findall('Table'):
        headers = [c.text or '' for c in table.find('Headers').findall('Cell')] if table.find('Headers') is not None else []
        rows = [[c.text or '' for c in row.findall('Cell')] for row in table.findall('Row')]
        tables.append({
            "table_id": table.get('table_id', ''),
            "type": table.get('type', ''),
            "headers": headers,
            "rows": rows
        })
    
    # 提取图片引用 (复用doc_tool.py:139 extract_image_and_table_items)
    images = [{"image_id": img.get('image_id', ''), 
               "caption": img.get('caption', ''),
               "figure_number": img.get('figure_number', '')}
              for img in section.findall('Image')]
    
    result = {
        "section_id": section_id,
        "title": section.get('title', ''),
        "text": text,
        "tables": tables,
        "images": images,
    }
    
    req_id = section.get('req_id')
    if req_id:
        result["req_id"] = req_id
    
    return result


# ── 工具3: srs_read_table ─────────────────────────────────────

def srs_read_table(table_type: str, content_xml_path: str) -> list[dict]:
    """
    读取指定类型的表格行(合格性表/追溯表等)。
    
    输入: table_type(qualification/traceability/reference/interface/other)
    输出: [{section, table_id, headers, rows}]
    """
    content = ET.parse(content_xml_path).getroot()
    results = []
    
    for table in content.findall(f'.//Table[@type="{table_type}"]'):
        headers = [c.text or '' for c in table.find('Headers').findall('Cell')] if table.find('Headers') is not None else []
        rows = [[c.text or '' for c in row.findall('Cell')] for row in table.findall('Row')]
        results.append({
            "section": table.get('section', ''),
            "table_id": table.get('table_id', ''),
            "table_type": table_type,
            "headers": headers,
            "rows": rows
        })
    
    return results


# ── 工具4: srs_z3_check (独创,AgentFlow/DataFlow无此功能) ──────

def srs_z3_check(constraints: list[dict]) -> dict:
    """
    Z3约束可满足性校验。
    
    输入: [{"param":"执行时间","operator":"≤","value":5,"unit":"ms"}, ...]
    输出: {"result":"sat"|"unsat"|"unknown", "unsat_core":"...", "constraints_count":N}
    """
    try:
        from z3 import Solver, Real, sat, unsat
    except ImportError:
        return {"error": "z3-solver not installed. Run: pip install z3-solver"}
    
    solver = Solver()
    var_map = {}
    added = 0
    
    for c in constraints:
        param = c.get("param", "")
        if not param:
            continue
        if param not in var_map:
            var_map[param] = Real(param)
        var = var_map[param]
        
        try:
            val = float(c["value"])
        except (ValueError, TypeError, KeyError):
            continue
        
        op = c.get("operator", "")
        if op == "≤" or op == "<=":
            solver.add(var <= val); added += 1
        elif op == "≥" or op == ">=":
            solver.add(var >= val); added += 1
        elif op == "=":
            solver.add(var == val); added += 1
        elif op == "<":
            solver.add(var < val); added += 1
        elif op == ">":
            solver.add(var > val); added += 1
    
    result = solver.check()
    if result == unsat:
        return {"result": "unsat", "unsat_core": str(solver.unsat_core()),
                "constraints_count": added}
    elif result == sat:
        return {"result": "sat", "constraints_count": added}
    else:
        return {"result": "unknown", "constraints_count": added}


# ── 工具5: srs_lint (独创,语法层规则检测) ─────────────────────

def srs_lint(check_type: str, content_xml_path: str, **kwargs) -> dict:
    """
    语法层规则检测。
    
    check_type:
      - duplicate_section: 章节编号重复
      - id_split: 需求ID分裂
      - phantom_requirement: 幽灵需求(被引用未定义)
      - systematic_offset: 章节号系统性偏移
      - coverage: 合格性/追溯覆盖完整性
      - section_completeness: GJB必需章节完整性
    """
    content = ET.parse(content_xml_path).getroot()
    
    if check_type == "duplicate_section":
        return _lint_duplicate_section(content)
    elif check_type == "id_split":
        return _lint_id_split(content)
    elif check_type == "phantom_requirement":
        return _lint_phantom(content)
    elif check_type == "systematic_offset":
        return _lint_systematic_offset(content)
    elif check_type == "coverage":
        return _lint_coverage(content)
    elif check_type == "section_completeness":
        return _lint_section_completeness(content)
    else:
        return {"error": f"Unknown check_type: {check_type}"}


def _lint_duplicate_section(content: ET.Element) -> dict:
    """检测章节编号重复(目录+正文=2次正常,≥3次才报违规)"""
    section_ids = [s.get('section_id', '') for s in content.findall('.//Section')]
    counts = Counter(section_ids)
    # 阈值3: 目录+正文=2次正常,第3次起为真实重复
    dups = {s: c for s, c in counts.items() if c >= 3 and s}
    return {
        "check": "duplicate_section",
        "duplicates": dups,
        "total_duplicates": sum(dups.values()),
        "is_violation": len(dups) > 0
    }


def _lint_id_split(content: ET.Element) -> dict:
    """检测需求ID分裂(同一实体多个ID)"""
    # 收集所有需求ID
    all_ids = []
    for section in content.findall('.//Section'):
        req_id = section.get('req_id', '')
        if req_id:
            all_ids.append((req_id, section.get('section_id', ''), section.get('title', '')))
    
    # 归一化: 取ID的缩写词前缀(前2段)
    def normalize_id(raw_id: str) -> str:
        parts = raw_id.split('-')
        if len(parts) >= 2:
            return parts[0] + '-' + parts[1]
        return raw_id
    
    # 按归一化ID分组
    id_groups = defaultdict(list)
    for raw_id, sec, title in all_ids:
        normalized = normalize_id(raw_id)
        id_groups[normalized].append({"raw_id": raw_id, "section": sec, "title": title})
    
    # 找分裂(归一化后相同但原始不同)
    splits = {}
    for norm, group in id_groups.items():
        raw_ids = set(g["raw_id"] for g in group)
        if len(raw_ids) > 1:
            splits[norm] = group
    
    return {
        "check": "id_split",
        "splits": splits,
        "total_splits": len(splits),
        "is_violation": len(splits) > 0
    }


def _lint_phantom(content: ET.Element) -> dict:
    """检测幽灵需求(被引用但未定义)"""
    # 定义: 3.2.X节的功能
    defined = set()
    for section in content.findall('.//Section'):
        sec_id = section.get('section_id', '')
        if sec_id.startswith('3.2.') and section.get('req_id'):
            defined.add(sec_id)
    
    # 引用: 第4章合格性表和第5章追溯表中的章节号
    referenced = set()
    for table in content.findall('.//Table[@type="qualification"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                # 找3.2.X格式的章节号
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    referenced.add(m.group(1))
    
    for table in content.findall('.//Table[@type="traceability"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    referenced.add(m.group(1))
    
    phantoms = referenced - defined
    return {
        "check": "phantom_requirement",
        "defined_sections": sorted(defined),
        "referenced_sections": sorted(referenced),
        "phantoms": sorted(phantoms),
        "total_phantoms": len(phantoms),
        "is_violation": len(phantoms) > 0
    }


def _lint_systematic_offset(content: ET.Element) -> dict:
    """检测合格性表(第4章)与第3章的章节号系统性偏移"""
    # 第3章的3.2.X章节
    ch3_sections = [s.get('section_id', '') for s in content.findall('.//Section')
                    if s.get('section_id', '').startswith('3.2.')]
    
    # 第4章合格性表中引用的章节号
    ch4_refs = []
    for table in content.findall('.//Table[@type="qualification"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    ch4_refs.append(m.group(1))
    
    if not ch3_sections or not ch4_refs:
        return {"check": "systematic_offset", "is_systematic": False, "reason": "数据不足"}
    
    # 尝试不同偏移
    def adjust(sec: str, offset: int) -> str:
        parts = sec.split('.')
        if len(parts) >= 3:
            try:
                parts[-1] = str(int(parts[-1]) + offset)
                return '.'.join(parts)
            except ValueError:
                return sec
        return sec
    
    best_offset, best_rate = 0, 0
    for offset in range(-2, 3):
        matched = sum(1 for ref in ch4_refs if adjust(ref, offset) in ch3_sections)
        rate = matched / len(ch4_refs)
        if rate > best_rate:
            best_offset, best_rate = offset, rate
    
    return {
        "check": "systematic_offset",
        "ch3_sections": sorted(set(ch3_sections)),
        "ch4_refs": sorted(set(ch4_refs)),
        "best_offset": best_offset,
        "match_rate": round(best_rate, 2),
        "is_systematic": best_offset != 0 and best_rate > 0.8
    }


def _lint_coverage(content: ET.Element) -> dict:
    """检测合格性表/追溯表是否覆盖第3章所有需求"""
    # 第3章的需求
    ch3_reqs = set()
    for section in content.findall('.//Section'):
        sec_id = section.get('section_id', '')
        if sec_id.startswith('3.2.') and section.get('req_id'):
            ch3_reqs.add(sec_id)
    
    # 第4章合格性表覆盖的章节号
    ch4_covered = set()
    for table in content.findall('.//Table[@type="qualification"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    ch4_covered.add(m.group(1))
    
    # 第5章追溯表覆盖的章节号
    ch5_covered = set()
    for table in content.findall('.//Table[@type="traceability"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    ch5_covered.add(m.group(1))
    
    uncovered_ch4 = ch3_reqs - ch4_covered
    uncovered_ch5 = ch3_reqs - ch5_covered
    
    return {
        "check": "coverage",
        "ch3_requirements": sorted(ch3_reqs),
        "ch4_covered": sorted(ch4_covered),
        "ch5_covered": sorted(ch5_covered),
        "uncovered_by_ch4": sorted(uncovered_ch4),
        "uncovered_by_ch5": sorted(uncovered_ch5),
        "ch4_coverage_rate": len(ch4_covered) / max(1, len(ch3_reqs)),
        "ch5_coverage_rate": len(ch5_covered) / max(1, len(ch3_reqs)),
        "is_violation": len(uncovered_ch4) > 0 or len(uncovered_ch5) > 0
    }


def _lint_section_completeness(content: ET.Element) -> dict:
    """检测GJB必需章节完整性(6个顶层章+3.2能力需求)"""
    section_ids = set(s.get('section_id', '') for s in content.findall('.//Section'))
    
    must_chapters = ['1', '2', '3', '4', '5', '6']
    missing = [ch for ch in must_chapters if ch not in section_ids]
    
    has_3_2 = any(s.startswith('3.2') for s in section_ids)
    if not has_3_2:
        missing.append('3.2')
    
    return {
        "check": "section_completeness",
        "found_chapters": sorted([ch for ch in must_chapters if ch in section_ids]),
        "missing_chapters": missing,
        "is_violation": len(missing) > 0
    }


# ── 测试 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    # 快速自测
    import sys
    
    # 找一份content.xml测试
    outline_dir = Path(__file__).resolve().parent.parent / "data/srs_outline"
    test_files = list(outline_dir.glob("*_content.xml"))
    if not test_files:
        print("[!] 没有找到content.xml,请先运行srs_to_xml.py")
        sys.exit(1)
    
    test_file = str(test_files[0])
    print(f"测试文件: {Path(test_file).name}")
    
    # 测试search
    print("\n=== srs_search('数据获取') ===")
    results = srs_search("数据获取", test_file)
    print(f"  结果: {len(results)}条")
    for r in results[:3]:
        print(f"    {r}")
    
    # 测试read_section
    print("\n=== srs_read_section('3.2.1') ===")
    result = srs_read_section("3.2.1", test_file)
    if "error" not in result:
        print(f"  title: {result['title']}")
        print(f"  text长度: {len(result['text'])}")
        print(f"  tables: {len(result['tables'])}")
    else:
        print(f"  {result['error']}")
    
    # 测试lint
    print("\n=== srs_lint('duplicate_section') ===")
    result = srs_lint("duplicate_section", test_file)
    print(f"  duplicates: {result.get('duplicates', {})}")
    
    print("\n=== srs_lint('section_completeness') ===")
    result = srs_lint("section_completeness", test_file)
    print(f"  missing: {result.get('missing_chapters', [])}")
    
    print("\n=== srs_z3_check ===")
    result = srs_z3_check([
        {"param": "A", "operator": "≤", "value": 5},
        {"param": "A", "operator": "≥", "value": 10},
    ])
    print(f"  result: {result}")
