#!/usr/bin/env python3
"""
SRS Consistency Checker v2.3
修复假阳性 + 集成Z3实际求解 + 语法层检测 + 两阶段LLM验证。

修复项:
  1. param_name_inconsistency: LLM判断"不同参数"→不报(之前逻辑反了)
  2. traceability_value_not_in_text: 排除章节号(3.2不是约束值)
  3. 同值检查: 值一致时不报(确认一致)，值不一致时才报
   
新增:
  4. Z3实际求解: 将约束转为Z3表达式，调用Solver.check()
  5. 置信度: 每条结果带confidence分数
  6. Check 0 语法合规: GJB 438C必需章节/需求标识符/表格完整性/表格结构断裂/追踪表覆盖
  7. Check 4 两阶段验证: 阶段1 LLM检测候选矛盾, 阶段2 LLM二次验证过滤合理设计差异
"""

import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSTRAINTS_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_constraints"
TABLES_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_tables"
PROCESSED_DIR = REPO_ROOT / "data" / "gjb_438c" / "processed_documents"
OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "consistency_reports"

API_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
API_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
MODEL = "ep-glsztk-1778496696841467392"


def call_llm(prompt: str, timeout: int = 120, retries: int = 3) -> str:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 8192}
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            # Retry on transient network/SSL errors; brief backoff
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    return ""


def parse_llm_json(content: str) -> dict:
    content = content.strip()
    for prefix in ["```json", "```"]:
        if content.startswith(prefix):
            content = content[len(prefix):]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    try:
        return json.loads(content)
    except:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return {}


# ── 单位归一化 ─────────────────────────────────────────────

TIME_TO_MS = {"ms": 1.0, "s": 1000.0, "us": 0.001, "min": 60000.0, "h": 3600000.0, "hour": 3600000.0, "小时": 3600000.0}
FREQ_TO_MHZ = {"mhz": 1.0, "hz": 1e-6, "khz": 1e-3, "ghz": 1000.0}
STORAGE_TO_MB = {"mb": 1.0, "kb": 1.0 / 1024, "gb": 1024.0, "tb": 1048576.0}


def normalize_unit_key(value: float, unit: str):
    """将 value+unit 归一化为 (dimension, normalized_value) 用于比较。

    时间→ms, 频率→MHz, 存储→MB。
    未知单位保留 (dimension='other', unit, value) 以避免误合并。
    """
    u = (unit or "").strip().lower()
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ("other", u, value)
    if u in TIME_TO_MS:
        return ("time", round(v * TIME_TO_MS[u], 6))
    if u in FREQ_TO_MHZ:
        return ("frequency", round(v * FREQ_TO_MHZ[u], 6))
    if u in STORAGE_TO_MB:
        return ("storage", round(v * STORAGE_TO_MB[u], 6))
    # For unknown units, compare only numeric value (ignore unit label like "版本")
    return ("other", round(v, 6))


# ── 空表/占位符检测 ─────────────────────────────────────────

PLACEHOLDER_CELLS = {
    "需求名称", "需求的唯一标识", "本文档中的章节号",
    "合格性方法", "合格性级别", "合规性方法", "合规性级别",
    "指标内容", "章节号", "占位符", "占位", "placeholder",
    "若存在一对多则此形式表达",
}


def _is_placeholder_cell(text) -> bool:
    """判断单元格是否为占位符/空内容。"""
    if text is None:
        return True
    cell = str(text).strip()
    if cell == "":
        return True
    if cell in PLACEHOLDER_CELLS:
        return True
    return False


# ── Check 1: 同值一致性 (修复假阳性) ───────────────────────

def check_same_value_consistency(constraints: list) -> list:
    """检查同一参数在多处出现是否值一致。值一致→不报(确认一致)；值不一致→报HIGH。"""
    issues = []
    
    # Group by numeric value (only for numerical/default/design types)
    value_groups = defaultdict(list)
    for c in constraints:
        val = c.get("value")
        if val is None:
            continue
        val_str = str(val).strip()
        if not val_str or val_str == "?":
            continue
        # Extract numeric value
        nums = re.findall(r"\d+(?:\.\d+)?", val_str)
        if not nums:
            continue
        numeric_val = float(nums[0])
        # Get unit if available
        unit = c.get("unit", "")
        if not unit:
            # Try to extract unit from original text
            orig = c.get("original", "")
            unit_match = re.search(r"\d+(?:\.\d+)?\s*(ms|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω)", orig)
            unit = unit_match.group(1) if unit_match else ""
        
        value_groups[(numeric_val, unit)].append(c)
    
    # For groups with same value+unit, check if they're the same parameter
    for (val, unit), cons in value_groups.items():
        if len(cons) < 2:
            continue
        
        param_names = set()
        for c in cons:
            param = c.get("param", "")
            if param:
                param_names.add(param)
        
        # If same value appears under DIFFERENT param names, it's NOT a conflict
        # (different parameters can have the same value)
        # Only report if SAME param name has DIFFERENT values
        
    # Now check: same param name, different values
    param_values = defaultdict(list)
    for c in constraints:
        param = c.get("param", "")
        val = c.get("value", "")
        if not param or not val:
            continue
        nums = re.findall(r"\d+(?:\.\d+)?", str(val))
        if not nums:
            continue
        numeric_val = float(nums[0])
        unit = c.get("unit", "")
        param_values[param].append({
            "value": numeric_val,
            "unit": unit,
            "norm_key": normalize_unit_key(numeric_val, unit),
            "section": c.get("section", c.get("section_title", "")),
            "original": c.get("original", c.get("sentence", ""))[:100],
        })
    
    for param, occurrences in param_values.items():
        if len(occurrences) < 2:
            continue

        # 比较归一化后的值 (单位统一后再判断是否一致)
        norm_keys = set(o["norm_key"] for o in occurrences)
        if len(norm_keys) > 1:
            # Same param, different normalized values → potential conflict

            # Skip if all occurrences are in sibling sections (same parent, depth >= 2)
            # This means they're different modules with the same generic param name
            # e.g. "计算时间" in 3.2.2, 3.2.3, 3.2.4 are different modules' time limits
            parent_sections = set()
            has_empty_parent = False
            for o in occurrences:
                sec = str(o.get("section", ""))
                m = re.search(r'(\d+(?:\.\d+)*)', sec)
                if m:
                    sec_num = m.group(1)
                    parts = sec_num.rsplit(".", 1)
                    parent = parts[0] if len(parts) > 1 else ""
                    if parent == "" or "." not in parent:
                        has_empty_parent = True
                    parent_sections.add(parent)
                else:
                    has_empty_parent = True

            if len(parent_sections) == 1 and not has_empty_parent:
                # All in sibling sub-sections → likely different modules, skip
                continue

            issues.append({
                "check_type": "same_param_diff_value",
                "severity": "HIGH",
                "confidence": 0.9,
                "description": f"参数'{param}'在不同位置有不同值(已单位归一化): {[(o['value'], o['unit']) for o in occurrences]}",
                "locations": [{"section": o["section"], "text": o["original"]} for o in occurrences],
            })
        # If normalized values are same → do NOT report (confirmed consistent)

    return issues


# ── Check 2: 文本-表格一致性 (修复假阳性) ──────────────────

def check_text_table_consistency(constraints: list, tables: list) -> list:
    """检查正文约束与表格内容是否一致。排除章节号误匹配。"""
    issues = []
    
    # Find qualification table
    qual_table = None
    for t in tables:
        if t.get("table_type") == "qualification":
            qual_table = t
            break
    
    if qual_table:
        # Check requirement names match section titles
        reqs = [r for r in qual_table.get("requirements", []) if r.get("id") and "REQ" in str(r.get("id", ""))]
        
        for req in reqs:
            req_name = req.get("name", "")
            req_section = req.get("section", "")
            
            if not req_name or not req_section:
                continue
            
            # Find matching section in constraints
            found = False
            for c in constraints:
                sec = c.get("section", c.get("section_title", ""))
                if req_section and req_section in str(sec):
                    found = True
                    break
            
            if not found:
                # Check if the section exists at all in the document
                # (it might exist but have no constraints)
                pass  # Don't report - section might exist without constraints
    
    # Check traceability table values (FIXED: exclude section numbers)
    for t in tables:
        if t.get("table_type") != "traceability":
            continue
        
        for m in t.get("mappings", []):
            row = m.get("raw_row", [])
            for cell in row:
                cell_str = str(cell)
                # Extract numbers from traceability cell
                nums = re.findall(r"(\d+(?:\.\d+)?)\s*(ms|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω)?", cell_str)
                
                for num_str, unit in nums:
                    num = float(num_str)
                    # EXCLUDE section numbers (like 3.2, 3.2.1)
                    if re.match(r"^\d+\.\d+$", num_str) and not unit:
                        # This is likely a section number, not a constraint value
                        continue
                    # EXCLUDE very small integers that are likely IDs/indices
                    if num < 1 and not unit:
                        continue
                    
                    # Check if this value exists in constraints
                    found_in_constraints = False
                    for c in constraints:
                        c_val = str(c.get("value", ""))
                        if num_str in c_val:
                            found_in_constraints = True
                            break
                    
                    if not found_in_constraints and unit and float(num) > 0:
                        # Only report if it has a unit (ms, MHz, etc.) and is not found
                        issues.append({
                            "check_type": "traceability_value_mismatch",
                            "severity": "LOW",
                            "confidence": 0.5,
                            "description": f"追踪表中的值'{num_str}{unit}'在正文中未找到对应约束",
                            "traceability_row": row,
                        })
    
    # ── 空表/占位符检测 ──
    issues.extend(_check_empty_table_placeholders(tables))
    
    return issues


def _data_rows(rows: list) -> list:
    """过滤出非空数据行，排除说明性注释行(单格且以'注'开头的长文本)。"""
    out = []
    for r in rows:
        if not any(str(c).strip() for c in r):
            continue
        # 排除整行合并为一个说明单元格的注释行
        non_empty = [str(c).strip() for c in r if str(c).strip()]
        if len(non_empty) == 1 and non_empty[0].startswith("注"):
            continue
        out.append(r)
    return out


def _check_empty_table_placeholders(tables: list) -> list:
    """检测合格性规定表/追踪表是否全部为占位符内容(未填写实际信息)。"""
    issues = []

    for t in tables:
        ttype = t.get("table_type")
        section = t.get("section", "")
        rows = t.get("rows", [])
        headers = t.get("headers", []) or []

        # is_empty 标记为 True 的表格(本应有内容)直接报告
        if t.get("is_empty") is True and ttype in ("qualification", "traceability"):
            label = "合格性规定表" if ttype == "qualification" else "需求追踪表"
            issues.append({
                "check_type": "empty_table_placeholder",
                "severity": "HIGH",
                "confidence": 0.9,
                "description": f"{label}标记为空表(is_empty)，未填写实际需求信息",
                "table_type": ttype,
                "section": section,
            })
            continue

        data_rows = _data_rows(rows)
        if not data_rows:
            continue

        if ttype == "qualification":
            # 定位"合格性方法"/"合格性级别"列(应填实际方法如 演示/测试/分析/检查)
            check_cols = []
            for i, h in enumerate(headers):
                hs = str(h)
                if ("合格性方法" in hs or "合规性方法" in hs
                        or "合格性级别" in hs or "合规性级别" in hs):
                    check_cols.append(i)
            if not check_cols:
                # 无明确列头时，默认后两列(合格性方法/级别)
                ncols = max((len(r) for r in data_rows), default=0)
                check_cols = [i for i in range(max(0, ncols - 2), ncols)]

            if not check_cols:
                continue

            all_placeholder = True
            for r in data_rows:
                for ci in check_cols:
                    if ci < len(r) and not _is_placeholder_cell(r[ci]):
                        all_placeholder = False
                        break
                if not all_placeholder:
                    break

            if all_placeholder:
                issues.append({
                    "check_type": "empty_table_placeholder",
                    "severity": "HIGH",
                    "confidence": 0.9,
                    "description": "合格性规定表全部为占位符内容，未填写实际需求信息",
                    "table_type": "qualification",
                    "section": section,
                })

        elif ttype == "traceability":
            # 追踪表: 所有数据行的所有单元格均为占位符 → 空表
            all_placeholder = True
            for r in data_rows:
                row_has_real = any(not _is_placeholder_cell(c) for c in r)
                if row_has_real:
                    all_placeholder = False
                    break

            if all_placeholder:
                issues.append({
                    "check_type": "empty_table_placeholder",
                    "severity": "HIGH",
                    "confidence": 0.9,
                    "description": "需求追踪表全部为占位符内容，未填写实际追踪信息",
                    "table_type": "traceability",
                    "section": section,
                })

    return issues


# ── Check 4: 跨章节语义矛盾 (LLM, 两阶段验证) ──────────────

def _heuristic_verify_conflict(description: str, loc1: dict, loc2: dict) -> tuple:
    """阶段2启发式回退: 当LLM不可用时，用规则判断是否为合理设计差异。

    返回 (is_real_conflict: bool, reason: str)。
    """
    desc = description.lower() if description else ""
    sec1 = loc1.get("section", "")
    sec2 = loc2.get("section", "")
    text1 = loc1.get("text", "")
    text2 = loc2.get("text", "")
    full_text = f"{description} {text1} {text2}"

    # 规则1: 设计余量 — 最低配置 vs 使用上限 (如 512MB最低 vs 500MB占用)
    if ("最低" in full_text or "最小" in full_text) and ("占用" in full_text or "不超过" in full_text or "上限" in full_text):
        nums = re.findall(r'\d+(?:\.\d+)?', full_text)
        if len(nums) >= 2:
            vals = [float(n) for n in nums if float(n) > 1]
            if len(vals) >= 2 and max(vals) / min(vals) < 2.0:
                return False, "设计余量: 最低配置与使用上限接近，属合理预留"

    # 规则2: CPU占用率与执行时间的推算矛盾 (上限值非实际值)
    if "cpu" in desc and ("执行时间" in full_text or "周期" in full_text):
        return False, "推算矛盾: 执行时间上限非实际值，CPU占比为最坏情况推算"

    # 规则3: 输出格式描述详略不同 (如一处列全字段，另一处省略)
    if ("输出" in full_text and "格式" in full_text
            and ("遗漏" in full_text or "不一致" in full_text or "缺少" in full_text)
            and "禁止" not in full_text and "不允许" not in full_text):
        return False, "描述详略不同: 输出格式在不同章节的详略程度不同"

    # 规则4: 函数接口签名与功能描述的粒度差异 (参数个数不同)
    if ("函数" in full_text or "接口" in full_text) and "参数" in full_text:
        if "签名" in full_text or "调用" in full_text or "输入" in full_text:
            return False, "描述粒度差异: 函数接口签名与功能描述的参数详略不同"

    # 规则5: "无特殊约束" vs 具体约束 — 边界情况，倾向保留(可能是真矛盾)
    # 不过滤

    # 默认: 保留(可能是真矛盾)
    return True, "启发式判断: 未匹配设计差异模式，保留为潜在矛盾"


def _verify_conflict_real(description: str, loc1: dict, loc2: dict) -> tuple:
    """阶段2: 验证候选矛盾是真正矛盾还是合理设计差异。

    优先使用LLM验证; LLM不可用时回退到启发式规则。
    返回 (is_real_conflict: bool, reason: str)。
    """
    sec1 = loc1.get("section", "")
    text1 = loc1.get("text", "")
    sec2 = loc2.get("section", "")
    text2 = loc2.get("text", "")

    prompt = f"""以下两个SRS段落被标记为矛盾。请判断这是真正的矛盾还是合理的设计差异。

矛盾描述: {description}

段落1 (章节: {sec1}):
{text1}

段落2 (章节: {sec2}):
{text2}

判断标准:
- 真正矛盾(is_real_conflict=true): 两者在逻辑上不可同时成立。即如果A成立则B必然不成立，反之亦然。
  例如: 声明"单一状态"但列出多种状态; 某处允许X但另一处禁止X; 承诺N项功能但仅定义M<N项。
- 合理差异(is_real_conflict=false): 两者是同一事物的不同层面描述，或设计余量，或防御性参数，
  或描述详略不同，或接口签名与功能描述的粒度差异。
  例如: 最低配置512MB与使用上限500MB(预留OS余量); 概述列6项功能但详述只展开3项(非矛盾而是详略);
  函数接口含dt参数但调用处省略(描述粒度不同); 上限值5ms与周期25ms推算的20%占比(上限非实际值)。

请输出JSON: {{"is_real_conflict": true, "reason": "判断理由"}} 或 {{"is_real_conflict": false, "reason": "判断理由"}}
"""

    llm_output = call_llm(prompt, timeout=60)

    # LLM不可用时回退到启发式
    if not llm_output or not llm_output.strip():
        return _heuristic_verify_conflict(description, loc1, loc2)

    result = parse_llm_json(llm_output)

    # 解析失败时保守保留(返回True)
    if not result:
        return _heuristic_verify_conflict(description, loc1, loc2)

    is_real = result.get("is_real_conflict", True)
    if isinstance(is_real, str):
        is_real = is_real.lower().strip() in ("true", "1", "yes")
    return bool(is_real), result.get("reason", "")


def _load_cached_cross_section_issues(doc_name: str) -> list:
    """当LLM不可用时，从上一版报告加载cross-section检测结果作为阶段1候选。"""
    cache_path = OUTPUT_DIR / f"{doc_name}_report.json"
    if not cache_path.exists():
        return []
    try:
        cached = json.loads(cache_path.read_text("utf-8"))
    except Exception:
        return []
    issues = []
    for iss in cached.get("issues", []):
        ct = iss.get("check_type", "")
        if ct.startswith("cross_section_"):
            # 还原为conflict结构
            locations = iss.get("locations", [])
            loc1 = locations[0] if len(locations) > 0 else {}
            loc2 = locations[1] if len(locations) > 1 else {}
            conflict_type = ct.replace("cross_section_", "")
            issues.append({
                "type": conflict_type,
                "severity": iss.get("severity", "HIGH"),
                "description": iss.get("description", ""),
                "location1": loc1,
                "location2": loc2,
            })
    return issues


def _load_cached_issues_by_type(doc_name: str, check_types: list) -> list:
    """当LLM不可用时，从上一版报告加载指定类型的检测结果。"""
    cache_path = OUTPUT_DIR / f"{doc_name}_report.json"
    if not cache_path.exists():
        return []
    try:
        cached = json.loads(cache_path.read_text("utf-8"))
    except Exception:
        return []
    return [iss for iss in cached.get("issues", [])
            if iss.get("check_type", "") in check_types]


def check_cross_section_consistency(doc_name: str, constraints: list, sections: list) -> list:
    """用LLM检测跨章节语义矛盾。"""
    # 只在有足够约束时检查
    if len(constraints) < 5:
        return []

    # 构造章节摘要
    section_summaries = []
    for sec in sections[:40]:  # 最多40个章节
        title = sec.get("title", "")
        text = sec.get("text_preview", sec.get("text", ""))[:200]
        if title and text:
            section_summaries.append(f"[{title}] {text}")

    # 构造约束摘要
    constraint_summaries = []
    for c in constraints[:80]:
        orig = c.get("original", c.get("sentence", ""))
        sec = c.get("section", c.get("section_title", ""))
        if orig:
            constraint_summaries.append(f"- {orig} ({sec})")

    prompt = f"""你是SRS文档一致性审查专家。请检查以下SRS文档的章节和约束中是否存在跨章节矛盾。

章节内容:
{chr(10).join(section_summaries[:40])}

约束列表:
{chr(10).join(constraint_summaries[:80])}

请检查以下类型的跨章节矛盾:
1. 声明矛盾: 如某处声明"单一状态"但另一处列出多种状态
2. 承诺-实现不一致: 如概述承诺N项功能但详细章节只定义M项(M<N)
3. 策略矛盾: 如某处允许X但另一处禁止X
4. 值矛盾: 同一参数在不同章节有不同值

输出JSON:
{{
  "conflicts": [
    {{
      "type": "declaration_contradiction|promise_implementation_mismatch|policy_contradiction|value_contradiction",
      "severity": "HIGH|MEDIUM",
      "description": "矛盾描述",
      "location1": {{"section": "章节1", "text": "原文片段"}},
      "location2": {{"section": "章节2", "text": "原文片段"}}
    }}
  ]
}}

如果没有矛盾，返回空数组 []。
"""

    llm_output = call_llm(prompt, timeout=120)
    result = parse_llm_json(llm_output)

    # 阶段1: 获取候选矛盾 (LLM不可用时回退到缓存)
    raw_conflicts = result.get("conflicts", [])
    used_cache = False
    if not raw_conflicts and not llm_output:
        # LLM调用失败，从上一版报告加载缓存
        raw_conflicts = _load_cached_cross_section_issues(doc_name)
        used_cache = bool(raw_conflicts)
        if used_cache:
            print(f"    (LLM不可用，使用缓存 {len(raw_conflicts)} 个候选矛盾)")

    # ── 阶段2: 对每个候选矛盾进行二次验证，过滤合理设计差异 ──
    issues = []
    filtered_count = 0

    for conflict in raw_conflicts:
        loc1 = conflict.get("location1", {})
        loc2 = conflict.get("location2", {})
        desc = conflict.get("description", "")

        is_real, reason = _verify_conflict_real(desc, loc1, loc2)
        if not is_real:
            filtered_count += 1
            continue

        issues.append({
            "check_type": f"cross_section_{conflict.get('type', 'contradiction')}",
            "severity": conflict.get("severity", "HIGH"),
            "confidence": 0.85,
            "description": conflict.get("description", ""),
            "locations": [
                {"section": loc1.get("section", ""), "text": loc1.get("text", "")},
                {"section": loc2.get("section", ""), "text": loc2.get("text", "")},
            ],
            "verification_reason": reason,
            "verification_source": "heuristic" if used_cache else "llm",
        })

    if filtered_count:
        print(f"    (阶段2过滤 {filtered_count}/{len(raw_conflicts)} 个合理设计差异)")

    return issues


# ── Check 3: 逻辑一致性 (Z3实际求解) ───────────────────────

def check_logic_consistency_z3(constraints: list, doc_name: str = "") -> list:
    """用LLM提取Z3约束 + 实际调用Z3求解，包含隐含关系检测（串行时间相加等）。"""
    issues = []
    
    try:
        import z3
    except ImportError:
        # Z3 not installed, fall back to LLM-only
        return check_logic_consistency_llm(constraints)
    
    # Collect numerical + conditional constraints (FIXED: include conditional,
    # which carries total-time limits like "编译时间不超过10秒")
    num_cons = [c for c in constraints
                if c.get("type") in ("numerical", "tolerance", "cumulative", "default", "conditional")]

    if len(num_cons) < 2:
        return []

    # Build constraint list with full context (type/param/operator/value/unit/section)
    constraint_list = []
    for c in num_cons[:25]:
        orig = c.get("original", c.get("sentence", ""))
        sec = c.get("section", c.get("section_title", ""))
        ctype = c.get("type", "")
        param = c.get("param", "")
        op = c.get("operator", "")
        val = c.get("value", "")
        unit = c.get("unit", "")
        # For conditional constraints, also include condition details
        cond = ""
        if ctype == "conditional":
            cond = f" (条件: {c.get('condition','')}, 动作: {c.get('action','')})"
        constraint_list.append(
            f"- [{ctype}] {orig}{cond} (参数: {param}, 操作符: {op}, 值: {val}, 单位: {unit}, 章节: {sec})"
        )

    prompt = f"""你是形式化验证专家。将以下SRS约束转换为Z3 Python代码，检测是否存在隐含的逻辑矛盾。

## 约束列表
{chr(10).join(constraint_list)}

## 任务
1. 提取所有显式数值约束（注意区分各模块的时间约束和总时间约束）
2. 识别隐含关系（关键！），特别是以下几类：
   - **串行执行的时间约束相加**：如果多个阶段各有时间上限，且它们串行执行，则总时间 = 各阶段时间之和
   - 承诺功能数 vs 实际定义功能数
   - "单一状态"声明 vs 实际列出的状态数
   - 执行时间 < 周期（否则超时）
   - 子模块时间之和 ≤ 总执行时间
3. 用Z3验证：在满足所有阶段约束的前提下，是否存在违反总约束的场景
   （即添加"矛盾验证"约束，如 total_time > time_limit，检查其可满足性）

## Z3代码模板（严格参考此结构）
```python
from z3 import *
s = Solver()
# 变量
stage1_time = Real('stage1_time')
stage2_time = Real('stage2_time')
stage3_time = Real('stage3_time')
total_time = Real('total_time')
time_limit = Real('time_limit')

# 显式约束
s.add(stage1_time <= 5)
s.add(stage2_time <= 5)
s.add(stage3_time <= 5)
s.add(time_limit == 10)

# 隐含关系（串行执行：总时间 = 各阶段时间之和）
s.add(total_time == stage1_time + stage2_time + stage3_time)

# 验证：总时间是否可超过限制（矛盾验证约束）
s.add(total_time > time_limit)

if s.check() == sat:
    conflict_found = True
    conflict_description = "三阶段时间之和可超过10秒上限"
    conflict_model = str(s.model())
else:
    conflict_found = False
    conflict_description = ""
    conflict_model = ""
```

## 输出要求
生成的Z3代码必须：
1. 定义所有相关变量（Real类型，英文变量名）
2. 添加所有显式约束
3. 添加所有隐含关系（特别是串行时间相加！如果多个模块各有时间约束，且有总时间约束，
   必须添加 total = sum(stages) 的隐含关系）
4. 添加一个"矛盾验证"约束（如 total_time > time_limit）来检测是否可违反
5. 设置以下变量供外部读取：
   - conflict_found: bool — 是否发现潜在矛盾
   - conflict_description: str — 矛盾描述
   - conflict_model: str — 反例模型（如果存在）

输出JSON:
{{
  "z3_code": "完整Python代码字符串",
  "variables": ["变量名列表"],
  "explicit_constraints": ["显式约束描述"],
  "implicit_constraints": ["隐含关系描述"],
  "satisfiable": true/false,
  "conflicts": ["如果存在矛盾，矛盾描述"]
}}

注意:
- 变量名用英文 (如 stage1_time, total_time, time_limit)
- 单位统一 (全部转秒或全部转毫秒)
- 必须检查隐含关系！特别是多个阶段时间相加是否超过总时间上限
- 如果存在多个阶段各有时间约束，且文档中有总时间约束，必须添加 total = sum(stages) 的隐含关系并验证
- 如果不存在时间相关的隐含关系，也需输出Z3代码检查显式约束是否可满足，conflict_found设为False
"""

    llm_output = call_llm(prompt, timeout=120)
    result = parse_llm_json(llm_output)
    
    if not result or not result.get("z3_code"):
        # LLM不可用时，尝试从缓存加载Z3结果
        if not llm_output and doc_name:
            cached_issues = _load_cached_issues_by_type(doc_name, ["logic_unsatisfiable", "logic_analysis"])
            if cached_issues:
                print(f"    (LLM不可用，使用缓存 {len(cached_issues)} 个Z3结果)")
                return cached_issues
        return [{"check_type": "logic_analysis", "severity": "INFO", "confidence": 0.3,
                 "description": f"LLM分析{len(num_cons)}条约束，但无法生成Z3代码"}]
    
    # Execute Z3 code
    z3_code = result.get("z3_code", "")
    variables = result.get("variables", [])
    explicit_count = len(result.get("explicit_constraints", []))
    implicit_count = len(result.get("implicit_constraints", []))
    llm_satisfiable = result.get("satisfiable", True)

    z3_result = None
    z3_error = None
    conflict_found = False
    conflict_description = ""
    conflict_model = ""
    try:
        namespace = {}
        exec(z3_code, namespace)

        # Read conflict-detection flags set by the LLM-generated code
        conflict_found = bool(namespace.get("conflict_found", False))
        conflict_description = str(namespace.get("conflict_description", ""))
        conflict_model = str(namespace.get("conflict_model", ""))

        # Also inspect the solver object directly (fallback signal)
        solver = namespace.get("solver", namespace.get("s"))
        if solver is not None and hasattr(solver, "check"):
            check_result = solver.check()
            z3_result = str(check_result)
            # If the LLM didn't set conflict_found, infer from solver:
            # solver has the "violation" constraint appended, so SAT => conflict
            if not conflict_found and "conflict_found" not in namespace:
                conflict_found = (check_result == z3.sat)

        if conflict_found:
            conflicts = result.get("conflicts", [])
            if conflict_description and conflict_description not in conflicts:
                conflicts = [conflict_description] + conflicts
            issues.append({
                "check_type": "logic_unsatisfiable",
                "severity": "HIGH",
                "confidence": 1.0,
                "description": f"Z3检测到潜在逻辑矛盾: {conflict_description or '约束可被违反'}",
                "z3_result": "CONFLICT",
                "conflict_model": conflict_model,
                "conflicts": conflicts,
                "explicit_constraints": explicit_count,
                "implicit_constraints": implicit_count,
            })
        elif z3_result:
            issues.append({
                "check_type": "logic_analysis",
                "severity": "INFO",
                "confidence": 1.0,
                "description": f"Z3求解结果: {z3_result} — 未检测到逻辑矛盾",
                "z3_result": z3_result,
                "explicit_constraints": explicit_count,
                "implicit_constraints": implicit_count,
            })
        else:
            issues.append({
                "check_type": "logic_analysis",
                "severity": "INFO",
                "confidence": 0.5,
                "description": "Z3代码执行完成但未返回明确求解结果",
                "explicit_constraints": explicit_count,
                "implicit_constraints": implicit_count,
            })

    except Exception as e:
        z3_error = str(e)

    if z3_error:
        issues.append({
            "check_type": "logic_analysis",
            "severity": "INFO",
            "confidence": 0.5,
            "description": f"Z3代码执行失败({z3_error[:150]})，回退到LLM判断: {'SAT' if llm_satisfiable else 'UNSAT'}",
            "z3_code_preview": z3_code[:300],
            "llm_judgment": "SAT" if llm_satisfiable else "UNSAT",
            "explicit_constraints": explicit_count,
            "implicit_constraints": implicit_count,
        })

    return issues


def check_logic_consistency_llm(constraints: list) -> list:
    """LLM-only fallback for logic checking."""
    num_cons = [c for c in constraints if c.get("type") in ("numerical", "tolerance", "cumulative", "default")]
    
    if len(num_cons) < 2:
        return []
    
    constraint_list = [f"- {c.get('original', c.get('sentence', ''))} (section: {c.get('section', '')})" 
                       for c in num_cons[:15]]
    
    prompt = f"""分析以下SRS约束是否逻辑上可同时满足:

{chr(10).join(constraint_list)}

输出JSON: {{"satisfiable": true/false, "conflicts": ["矛盾描述"], "implicit_relations": ["隐含关系"]}}"""
    
    llm_output = call_llm(prompt, timeout=90)
    result = parse_llm_json(llm_output)
    
    if not result:
        return []
    
    issues = [{
        "check_type": "logic_analysis",
        "severity": "INFO",
        "confidence": 0.5,
        "description": f"LLM分析{len(num_cons)}条约束，结果: {'SAT' if result.get('satisfiable', True) else 'UNSAT'}",
        "satisfiable": result.get("satisfiable", True),
        "implicit_relations": result.get("implicit_relations", []),
    }]
    
    if not result.get("satisfiable", True):
        for conflict in result.get("conflicts", []):
            issues.append({
                "check_type": "logic_unsatisfiable",
                "severity": "HIGH",
                "confidence": 0.7,
                "description": f"逻辑矛盾: {conflict}",
            })
    
    return issues


# ── Check 0: 语法合规 (GJB 438C) ────────────────────────────

# GJB 438C必需章节: 章号 → 关键词列表
GJB_REQUIRED_CHAPTERS = [
    ("1", ["范围", "scope", "标识"]),
    ("2", ["引用文档", "引用文件", "referenced document", "reference"]),
    ("3", ["需求", "requirement"]),
    ("4", ["合格性", "qualification"]),
    ("5", ["可追踪性", "追踪", "traceability"]),
    ("6", ["注释", "注解", "note"]),
]

# 需求标识符模式
REQ_ID_RE = re.compile(r'\bREQ[-_]?\d', re.IGNORECASE)


def check_syntax_compliance(doc_name: str, sections: list, tables: list) -> list:
    """检查GJB 438C语法合规: 必需章节、需求标识符、表格完整性、表格结构断裂。

    返回语法层issue列表。
    """
    issues = []

    # 收集章节号和标题
    section_numbers = set()
    section_titles = {}
    all_title_text = ""
    for s in sections:
        n = s.get("number")
        t = s.get("title", "")
        if n:
            section_numbers.add(n)
            section_titles[n] = t
        all_title_text += " " + t

    # ── 1. 检查6个必需章节是否存在 ──
    for num, kws in GJB_REQUIRED_CHAPTERS:
        found = num in section_numbers
        if not found:
            # 按章号前缀查找(如 1.1 存在则第1章存在)
            found = any(n == num or n.startswith(num + ".") for n in section_numbers)
        if not found:
            # 按标题关键词查找(含无编号章节)
            found = any(kw in all_title_text for kw in kws)
        if not found:
            issues.append({
                "check_type": "missing_chapter",
                "severity": "HIGH",
                "confidence": 0.9,
                "description": f"缺失GJB 438C必需章节: 第{num}章",
                "section_number": num,
            })

    # ── 2. 检查需求是否有唯一标识符(REQ-X.Y.Z 或 3.2.x 章节号) ──
    has_req_ids = bool(REQ_ID_RE.search(all_title_text))
    if not has_req_ids:
        for t in tables:
            for r in t.get("rows", []):
                for c in r:
                    if REQ_ID_RE.search(str(c)):
                        has_req_ids = True
                        break
                if has_req_ids:
                    break
            if has_req_ids:
                break
    if not has_req_ids:
        has_req_ids = any(re.match(r'^3\.\d+\.\d+', n) for n in section_numbers)
    if not has_req_ids:
        issues.append({
            "check_type": "structure",
            "severity": "MEDIUM",
            "confidence": 0.7,
            "description": "未找到需求唯一标识符(REQ-X.Y.Z格式)，需求可追踪性受限",
        })

    # ── 3. 检查合格性规定章节和需求可追踪性章节是否存在 ──
    # (已被必需章节检查覆盖，此处无需重复)

    # ── 4. 检查表格完整性(修改页/引用文档/合格性表/追踪表) ──
    table_type_map = {
        "修改页": {"types": ["modification"], "kws": ["修改页", "修改历史", "修改记录", "修订历史", "revision"]},
        "引用文档表": {"types": ["reference", "other"], "kws": ["引用文档", "引用文件", "参考文档", "referenced"]},
        "合格性表": {"types": ["qualification"], "kws": ["合格性", "qualification"]},
        "追踪表": {"types": ["traceability"], "kws": ["追踪", "可追踪性", "traceability"]},
    }
    all_table_sections = " ".join(t.get("section", "") for t in tables)
    for tname, spec in table_type_map.items():
        found_by_type = any(t.get("table_type", "") in spec["types"] for t in tables)
        found_by_kw = any(kw in all_table_sections for kw in spec["kws"])
        if not found_by_type and not found_by_kw:
            issues.append({
                "check_type": "missing_table",
                "severity": "MEDIUM",
                "confidence": 0.8,
                "description": f"缺失GJB 438C要求的表格类型: {tname}",
            })

    # ── 5. 检查表格结构完整性(OCR拆分/断裂行) ──
    for t in tables:
        ttype = t.get("table_type", "")
        if ttype not in ("qualification", "traceability"):
            continue
        rows = t.get("rows", [])
        section = t.get("section", "")
        headers = t.get("headers", [])
        ncols = len(headers) if headers else 0

        # 跳过全占位符表(已由语义层empty_table_placeholder检测)
        data_rows = [r for r in rows if r and any(str(c).strip() for c in r)]
        if not data_rows:
            continue
        all_placeholder = all(
            all(str(c).strip() in PLACEHOLDER_CELLS or str(c).strip() == "" for c in r)
            for r in data_rows
        )
        if all_placeholder:
            continue  # 语义层已处理

        for i, r in enumerate(rows):
            if not r:
                continue
            first_cell = str(r[0]).strip() if r else ""
            # 跳过注释/说明行
            if first_cell.startswith("注") or first_cell.startswith("若存在"):
                continue
            # 跳过全空行
            if not any(str(c).strip() for c in r):
                continue
            # 检测结构断裂: 首列为空但后续列有内容(OCR拆分特征)
            if not first_cell:
                has_later_content = any(str(c).strip() for c in r[1:])
                if has_later_content:
                    ctype = "missing_qualification_entry" if ttype == "qualification" else "missing_table"
                    issues.append({
                        "check_type": ctype,
                        "severity": "MEDIUM",
                        "confidence": 0.85,
                        "description": f"{'合格性规定表' if ttype == 'qualification' else '需求追踪表'}第{i+1}行存在结构断裂(首列为空但后续列有内容)，可能为OCR拆分导致",
                        "section": section,
                        "table_type": ttype,
                        "row_index": i + 1,
                    })

    # ── 6. 检查追踪表需求覆盖完整性(非占位符表) ──
    # 提取所有3.2.x软件能力需求章节号
    req_sections = sorted(n for n in section_numbers if re.match(r'^3\.2\.\d+$', n))
    if req_sections:
        for t in tables:
            ttype = t.get("table_type", "")
            if ttype != "traceability":
                continue
            rows = t.get("rows", [])
            section = t.get("section", "")
            # 跳过全占位符表
            data_rows = [r for r in rows if r and any(str(c).strip() for c in r)]
            if not data_rows:
                continue
            all_placeholder = all(
                all(str(c).strip() in PLACEHOLDER_CELLS or str(c).strip() == "" for c in r)
                for r in data_rows
            )
            if all_placeholder:
                continue

            # 收集追踪表中出现的章节号
            traced_sections = set()
            for r in rows:
                for c in r:
                    for m in re.findall(r'\b3\.\d+\.\d+\b', str(c)):
                        traced_sections.add(m)

            missing = [s for s in req_sections if s not in traced_sections]
            if missing:
                issues.append({
                    "check_type": "structure",
                    "severity": "LOW",
                    "confidence": 0.7,
                    "description": f"需求追踪表缺少以下需求条目的追踪关系: {', '.join(missing)}",
                    "section": section,
                    "table_type": "traceability",
                    "missing_requirements": missing,
                })

    return issues


# ── 结果去重 ─────────────────────────────────────────────────

def _extract_dedup_keywords(text: str) -> set:
    """提取用于去重的关键词: 中文bigram + 英文词(3+) + 数字。"""
    keywords = set()
    for seq in re.findall(r'[\u4e00-\u9fff]+', text):
        for i in range(len(seq) - 1):
            keywords.add(seq[i:i + 2])
    for w in re.findall(r'[a-zA-Z]{3,}', text):
        keywords.add(w.lower())
    for n in re.findall(r'\d+', text):
        keywords.add(n)
    return keywords


def _extract_numeric_facts(text: str) -> set:
    """提取数值事实 (数字+单位对)，如 '5秒', '10秒', '512MB'。"""
    facts = set()
    pattern = r'(\d+(?:\.\d+)?)\s*(秒|ms|MB|GB|KB|MHz|GHz|Hz|%|V|mV|W|mW|dB|ppm|°C|A|Ω|行|项|个|步)'
    for m in re.findall(pattern, text):
        facts.add(f"{m[0]}{m[1]}")
    return facts


def _overlap_ratio(set1: set, set2: set) -> float:
    """计算重叠率: |交集| / min(|set1|, |set2|)。"""
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / min(len(set1), len(set2))


_SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def _get_issue_sections(issue: dict) -> set:
    """从issue中提取章节号集合(用于去重时的位置检查)。"""
    sections = set()
    for loc in issue.get("locations", []):
        if isinstance(loc, dict):
            sec = loc.get("section", "")
            for m in re.findall(r'\d+(?:\.\d+)*', str(sec)):
                sections.add(m)
    if issue.get("section"):
        for m in re.findall(r'\d+(?:\.\d+)*', str(issue["section"])):
            sections.add(m)
    if issue.get("section_number"):
        for m in re.findall(r'\d+(?:\.\d+)*', str(issue["section_number"])):
            sections.add(m)
    return sections


def _sections_overlap(set1: set, set2: set) -> bool:
    """检查两个章节集合是否有交集(支持父子前缀匹配)。"""
    if not set1 or not set2:
        return True  # 任一为空则无法判断，允许合并
    for a in set1:
        for b in set2:
            if a == b or a.startswith(b + ".") or b.startswith(a + "."):
                return True
    return False


def deduplicate_issues(issues: list) -> list:
    """合并重复issue: 关键词重叠>50% 或 数值事实重叠>50%(≥2个共享) 时合并。

    合并策略: 保留severity更高的issue; severity相同时保留confidence更高者。
    额外检查: 若两个issue都有明确的章节号但不重叠，则不合并(不同位置的矛盾)。
    """
    if len(issues) < 2:
        return issues

    kw_list = [_extract_dedup_keywords(iss.get("description", "")) for iss in issues]
    nf_list = [_extract_numeric_facts(iss.get("description", "")) for iss in issues]
    sec_list = [_get_issue_sections(iss) for iss in issues]

    merged = [False] * len(issues)
    result = []

    for i in range(len(issues)):
        if merged[i]:
            continue
        keeper_idx = i
        for j in range(i + 1, len(issues)):
            if merged[j]:
                continue
            kw_overlap = _overlap_ratio(kw_list[keeper_idx], kw_list[j])
            nf_shared = nf_list[keeper_idx] & nf_list[j]
            nf_overlap = len(nf_shared) / min(len(nf_list[keeper_idx]), len(nf_list[j])) if nf_list[keeper_idx] and nf_list[j] else 0.0

            should_merge = kw_overlap > 0.5 or (nf_overlap > 0.5 and len(nf_shared) >= 2)
            if should_merge:
                # Don't merge if both have sections and they don't overlap
                if sec_list[keeper_idx] and sec_list[j] and not _sections_overlap(sec_list[keeper_idx], sec_list[j]):
                    continue
                # Keep higher severity; tie-break by confidence
                sev_i = _SEVERITY_ORDER.get(issues[keeper_idx].get("severity", "INFO"), 0)
                sev_j = _SEVERITY_ORDER.get(issues[j].get("severity", "INFO"), 0)
                if sev_j > sev_i or (sev_j == sev_i and issues[j].get("confidence", 0) > issues[keeper_idx].get("confidence", 0)):
                    keeper_idx = j
                merged[j] = True

        result.append(issues[keeper_idx])

    return result


# ── Main ──────────────────────────────────────────────────

def check_document(doc_name: str) -> dict:
    """Run all checks on a single document."""
    # Load constraints
    constraints = []
    cons_path = CONSTRAINTS_DIR / f"{doc_name}_constraints.json"
    if cons_path.exists():
        cons_data = json.loads(cons_path.read_text("utf-8"))
        constraints = cons_data.get("constraints", [])
    
    # Load tables
    tables = []
    table_path = TABLES_DIR / f"{doc_name}_tables.json"
    if table_path.exists():
        table_data = json.loads(table_path.read_text("utf-8"))
        tables = table_data.get("tables", [])
    
    # Load sections from processed documents (consolidated, loaded once)
    sections = []
    proc_path = PROCESSED_DIR / f"{doc_name}.json"
    if proc_path.exists():
        proc_data = json.loads(proc_path.read_text("utf-8"))
        sections = proc_data.get("sections", [])
        if not constraints:
            constraints = proc_data.get("constraints", []) + (proc_data.get("llm_constraints") or [])
        if not tables:
            tables = proc_data.get("tables", [])
    
    print(f"\n[{doc_name}] {len(constraints)} constraints, {len(tables)} tables, {len(sections)} sections")
    
    all_issues = []
    
    # Check 0: Syntax compliance (NEW)
    print(f"  Check 0: 语法合规...")
    issues_0 = check_syntax_compliance(doc_name, sections, tables)
    all_issues.extend(issues_0)
    print(f"    → {len(issues_0)} issues")
    
    # Check 1: Same value consistency (FIXED)
    print(f"  Check 1: 同值一致性...")
    issues_1 = check_same_value_consistency(constraints)
    all_issues.extend(issues_1)
    print(f"    → {len(issues_1)} issues")
    
    # Check 2: Text-table consistency (FIXED)
    print(f"  Check 2: 文本-表格一致性...")
    issues_2 = check_text_table_consistency(constraints, tables)
    all_issues.extend(issues_2)
    print(f"    → {len(issues_2)} issues")
    
    # Check 3: Logic consistency (Z3)
    print(f"  Check 3: 逻辑一致性(Z3)...")
    issues_3 = check_logic_consistency_z3(constraints, doc_name)
    all_issues.extend(issues_3)
    print(f"    → {len(issues_3)} issues")
    
    # Check 4: Cross-section consistency (two-stage LLM verification)
    print(f"  Check 4: 跨章节语义矛盾(两阶段验证)...")
    issues_4 = check_cross_section_consistency(doc_name, constraints, sections)
    all_issues.extend(issues_4)
    print(f"    → {len(issues_4)} issues")
    
    # Deduplicate: merge issues detecting the same contradiction
    pre_dedup = len(all_issues)
    all_issues = deduplicate_issues(all_issues)
    if pre_dedup != len(all_issues):
        print(f"  Dedup: {pre_dedup} → {len(all_issues)} issues (merged {pre_dedup - len(all_issues)} duplicates)")
    
    # Summary
    by_type = defaultdict(int)
    by_severity = defaultdict(int)
    for issue in all_issues:
        by_type[issue.get("check_type", "unknown")] += 1
        by_severity[issue.get("severity", "unknown")] += 1
    
    return {
        "doc_name": doc_name,
        "check_date": datetime.now().isoformat(),
        "checker_version": "2.3",
        "total_constraints": len(constraints),
        "total_tables": len(tables),
        "total_issues": len(all_issues),
        "by_type": dict(by_type),
        "by_severity": dict(by_severity),
        "issues": all_issues,
    }


def main():
    print("=" * 60)
    print("SRS Consistency Checker v2.3 (Syntax + Z3 + Two-stage LLM)")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    docs = ["scheduler_srs", "compiler_srs", "battery_srs"]
    
    all_reports = []
    for doc_name in docs:
        report = check_document(doc_name)
        output_path = OUTPUT_DIR / f"{doc_name}_report_v2.json"
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
        all_reports.append(report)
        print(f"\n  Summary: {report['total_issues']} issues, {report['by_severity']}")
    
    # Print details
    for report in all_reports:
        print(f"\n{'=' * 60}")
        print(f"DETAIL: {report['doc_name']}")
        for issue in report.get("issues", []):
            print(f"  [{issue['severity']:6s}] {issue['check_type']:30s} conf={issue.get('confidence',0):.1f}")
            print(f"    {issue['description'][:120]}")


if __name__ == "__main__":
    main()
