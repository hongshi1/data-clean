#!/usr/bin/env python3
"""
SRS Constraint Extractor
使用LLM从GJB格式SRS中提取7种类型的约束。

约束类型:
  1. numerical:    数值约束 (参数≤值)
  2. tolerance:    对称容差 (±值)
  3. cumulative:   累积约束 (N次后总误差≤值)
  4. temporal:     时序约束 (阶段+持续时间+动作)
  5. conditional:  条件约束 (if-then)
  6. default:      默认值
  7. design:       设计参数
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
    """Call GLM-5 API."""
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
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            print(f"  API attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return ""


def parse_llm_output(content: str) -> list:
    """Parse LLM output to extract JSON array."""
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
    """Extract sections from markdown file."""
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


def extract_constraints_from_doc(md_path: Path, doc_name: str) -> dict:
    """Extract all constraints from a single SRS document."""
    sections = extract_sections(md_path)

    all_constraints = []
    stats = {"total_sections": len(sections), "sections_with_constraints": 0}

    for section in sections:
        text = section["text"]
        if len(text) < 20:
            continue

        section_title = section["title"]
        section_num_match = re.match(r"^(\d+(?:\.\d+)*)\s+", section_title)
        section_number = section_num_match.group(1) if section_num_match else ""

        if not any(c.isdigit() for c in text):
            continue

        # Skip sections that are just table of contents or very short
        if len(text) < 50:
            continue
        # Skip TOC pages
        if "目 录" in section_title or "目次" in section_title:
            continue

        print(f"  Section: {section_title[:40]}... ({len(text)} chars)")

        prompt = EXTRACTION_PROMPT.format(
            section_number=section_number,
            section_title=section_title,
            section_text=text[:2000],
        )

        content = call_llm(prompt)
        constraints = parse_llm_output(content)

        for con in constraints:
            con["section_number"] = section_number
            con["section_title"] = section_title
            con["line_start"] = section["line_start"]

        if constraints:
            stats["sections_with_constraints"] += 1
            all_constraints.extend(constraints)
            print(f"    → {len(constraints)} constraints")

    stats["total_constraints"] = len(all_constraints)

    by_type = {}
    for c in all_constraints:
        t = c.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    stats["by_type"] = by_type

    return {
        "doc_name": doc_name,
        "extract_date": datetime.now().isoformat(),
        "stats": stats,
        "constraints": all_constraints,
    }


def main():
    print("=" * 60)
    print("SRS Constraint Extractor (LLM-based)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    docs = [
        ("scheduler_srs.pdf", "scheduler_srs"),
        ("battery_srs.pdf", "battery_srs"),
        ("compiler_srs.pdf", "compiler_srs"),
    ]

    all_results = []

    for pdf_name, doc_name in docs:
        md_path = SRS_DIR / pdf_name / "auto" / f"{pdf_name}.md"

        if not md_path.exists():
            md_files = list((SRS_DIR / pdf_name).rglob("*.md"))
            if md_files:
                md_path = md_files[0]
            else:
                print(f"\n[{doc_name}] No markdown found, skipping")
                continue

        print(f"\n[{doc_name}] Processing: {md_path.name}")

        result = extract_constraints_from_doc(md_path, doc_name)

        output_path = OUTPUT_DIR / f"{doc_name}_constraints.json"
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        all_results.append(result)
        print(f"  Total: {result['stats']['total_constraints']} constraints")
        print(f"  By type: {result['stats']['by_type']}")

    # Summary
    summary = {
        "extract_date": datetime.now().isoformat(),
        "total_docs": len(all_results),
        "total_constraints": sum(r["stats"]["total_constraints"] for r in all_results),
        "docs": [
            {
                "doc_name": r["doc_name"],
                "total_constraints": r["stats"]["total_constraints"],
                "by_type": r["stats"]["by_type"],
            }
            for r in all_results
        ],
    }
    (OUTPUT_DIR / "_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n{'=' * 60}")
    print("EXTRACTION COMPLETE")
    print(f"  Documents: {len(all_results)}")
    print(f"  Total constraints: {summary['total_constraints']}")
    for d in summary["docs"]:
        print(f"  {d['doc_name']}: {d['total_constraints']} constraints ({d['by_type']})")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
