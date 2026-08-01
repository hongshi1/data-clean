#!/usr/bin/env python3
"""
Extract constraints from battery SRS using GLM-5.
Saves intermediate results after each section.
"""

import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
SRS_DIR = REPO_ROOT / "data" / "gjb_438c" / "mineru_srs"
OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_constraints"

API_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
API_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
MODEL = "ep-glsztk-1778496696841467392"

EXTRACTION_PROMPT = """你是一个GJB 438C SRS文档分析专家。请从以下SRS章节文本中提取所有约束。

约束分为7种类型：

1. **numerical（数值约束）**: 参数有明确的数值限制
   例: "补偿计算时间不超过0.01ms" → {{"type":"numerical","param":"补偿计算时间","operator":"≤","value":0.01,"unit":"ms"}}

2. **tolerance（对称容差）**: ±形式的误差
   例: "单次定时误差不超过±2ms" → {{"type":"tolerance","param":"定时误差","value":2,"unit":"ms","meaning":"|误差|≤2"}}

3. **cumulative（累积约束）**: 多次执行后的累积限制
   例: "连续运行1000个周期后总时间误差不超过50ms" → {{"type":"cumulative","param":"总时间误差","operator":"≤","value":50,"unit":"ms","iterations":1000,"iteration_unit":"周期"}}

4. **temporal（时序约束）**: 按时间阶段描述的动作序列
   例: "前10秒恒流10A" → {{"type":"temporal","phase":"阶段1","duration":10,"duration_unit":"s","action":"恒流","value":10,"value_unit":"A"}}

5. **conditional（条件约束）**: if-then结构
   例: "执行时间超过25ms时进入超时告警" → {{"type":"conditional","condition":"执行时间>25ms","condition_param":"执行时间","condition_op":">","condition_value":25,"condition_unit":"ms","action":"进入超时告警状态"}}

6. **default（默认值）**: 配置参数的默认值
   例: "定时周期（interval_ms，默认25ms）" → {{"type":"default","param":"定时周期","value":25,"unit":"ms"}}

7. **design（设计参数）**: 不是硬约束，是设计决策
   例: "以25ms固定周期驱动" → {{"type":"design","param":"周期","value":25,"unit":"ms","description":"固定周期"}}

请提取以下文本中的所有约束，输出JSON数组。每条约束必须包含type字段和original（原文句子）。
如果没有约束，返回空数组 []。

章节编号: {section_number}
章节标题: {section_title}
章节内容:
{section_text}

请只输出JSON数组，不要其他文字。"""


def call_llm(prompt: str, max_retries: int = 3) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 8192,
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            print(f"  API attempt {attempt+1} failed: {e}", flush=True)
            if attempt < max_retries - 1:
                time.sleep(2)
    return ""


def parse_llm_output(content: str) -> list:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "constraints" in result:
            return result["constraints"]
        return [result] if result else []
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []


def extract_sections(md_path: Path) -> list:
    content = md_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    sections = []
    current_section = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip()
            if current_section:
                current_section["text"] = "\n".join(current_section["lines"]).strip()
                sections.append(current_section)
            current_section = {
                "level": level,
                "title": title,
                "line_start": i + 1,
                "lines": [],
            }
        elif current_section:
            current_section["lines"].append(line)
    if current_section:
        current_section["text"] = "\n".join(current_section["lines"]).strip()
        sections.append(current_section)
    return [s for s in sections if s["text"]]


def main():
    print("=" * 60, flush=True)
    print("Battery SRS Constraint Extractor", flush=True)
    print("=" * 60, flush=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = SRS_DIR / "battery_srs.pdf" / "auto" / "battery_srs.pdf.md"
    output_path = OUTPUT_DIR / "battery_srs_constraints.json"

    sections = extract_sections(md_path)
    print(f"Total sections: {len(sections)}", flush=True)

    all_constraints = []
    processed = 0
    skipped = 0

    for idx, section in enumerate(sections):
        text = section["text"]
        title = section["title"]

        # Skip short sections
        if len(text) < 50:
            skipped += 1
            continue
        # Skip TOC
        if "目 录" in title or "目次" in title:
            skipped += 1
            continue
        # Skip sections without digits
        if not any(c.isdigit() for c in text):
            skipped += 1
            continue

        section_num_match = re.match(r"^(\d+(?:\.\d+)*)\s+", title)
        section_number = section_num_match.group(1) if section_num_match else ""

        print(f"\n[{idx+1}/{len(sections)}] Section: {title[:50]}... ({len(text)} chars)", flush=True)

        prompt = EXTRACTION_PROMPT.format(
            section_number=section_number,
            section_title=title,
            section_text=text[:2500],
        )

        content = call_llm(prompt)
        constraints = parse_llm_output(content)

        for con in constraints:
            con["section_number"] = section_number
            con["section_title"] = title
            con["line_start"] = section["line_start"]

        if constraints:
            all_constraints.extend(constraints)
            print(f"  -> {len(constraints)} constraints", flush=True)
        else:
            print(f"  -> 0 constraints", flush=True)

        processed += 1

        # Save intermediate results after each section
        by_type = {}
        for c in all_constraints:
            t = c.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        intermediate = {
            "doc_name": "battery_srs",
            "extract_date": datetime.now().isoformat(),
            "stats": {
                "total_sections": len(sections),
                "processed_sections": processed,
                "skipped_sections": skipped,
                "sections_with_constraints": sum(1 for _ in all_constraints),
                "total_constraints": len(all_constraints),
                "by_type": by_type,
            },
            "constraints": all_constraints,
        }
        output_path.write_text(
            json.dumps(intermediate, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # Final save
    by_type = {}
    for c in all_constraints:
        t = c.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    final_result = {
        "doc_name": "battery_srs",
        "extract_date": datetime.now().isoformat(),
        "total": len(all_constraints),
        "stats": {
            "total_sections": len(sections),
            "processed_sections": processed,
            "skipped_sections": skipped,
            "total_constraints": len(all_constraints),
            "by_type": by_type,
        },
        "constraints": all_constraints,
    }
    output_path.write_text(
        json.dumps(final_result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n{'=' * 60}", flush=True)
    print("EXTRACTION COMPLETE", flush=True)
    print(f"  Processed: {processed} sections", flush=True)
    print(f"  Skipped: {skipped} sections", flush=True)
    print(f"  Total constraints: {len(all_constraints)}", flush=True)
    print(f"  By type: {by_type}", flush=True)
    print(f"  Output: {output_path}", flush=True)


if __name__ == "__main__":
    main()
