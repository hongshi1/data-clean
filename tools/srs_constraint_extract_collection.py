#!/usr/bin/env python3
"""
SRS Constraint Extractor for buaa/asyncTask collection.
Scans srs_collection/{buaa,asyncTask}/ for GJB-format .md files,
uses GLM-5 LLM to extract 7 types of constraints per section.
"""

import json
import re
import time
import hashlib
import socket
import requests
import urllib3
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MAX_WORKERS = 3

# Resolve API hostname to IP (Clash proxy may intercept by SNI)
_API_HOST = "wanqing-api.corp.kuaishou.com"
try:
    _API_IP = socket.gethostbyname(_API_HOST)
except Exception:
    _API_IP = _API_HOST
API_URL = f"https://{_API_IP}/api/gateway/v1/endpoints/chat/completions"
API_HOST = _API_HOST
API_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
MODEL = "ep-glsztk-1778496696841467392"

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTION_DIR = REPO_ROOT / "data" / "gjb_438c" / "srs_collection"
OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_constraints"

GJB_MARKERS = ["合格性规定", "CSCI"]

EXTRACTION_PROMPT = """从以下SRS章节中提取所有约束，分7类:
1. numerical: 数值约束 (参数有明确数值限制，如 ≤/≥/</> = 值)
2. tolerance: 对称容差 (±形式的误差)
3. cumulative: 累积约束 (N次执行后的累积限制)
4. temporal: 时序约束 (按时间阶段描述的动作序列)
5. conditional: 条件约束 (if-then结构，条件触发动作)
6. default: 默认值 (配置参数的默认取值)
7. design: 设计参数 (设计决策值，非硬约束)

每条约束输出JSON，必须包含字段: type, original(原文句子), param(参数名), value(数值), unit(单位)
可选字段(按类型): operator, tolerance, iterations, iteration_unit, phase, duration, duration_unit, condition, action, description
只输出JSON数组，不要其他文字。如果没有约束返回 []。

示例:
- "响应时间不超过200ms" → {{"type":"numerical","original":"响应时间不超过200ms","param":"响应时间","operator":"≤","value":200,"unit":"ms"}}
- "误差不超过±0.5℃" → {{"type":"tolerance","original":"误差不超过±0.5℃","param":"误差","value":0.5,"unit":"℃"}}
- "连续运行1000次后累计误差≤50ms" → {{"type":"cumulative","original":"连续运行1000次后累计误差≤50ms","param":"累计误差","operator":"≤","value":50,"unit":"ms","iterations":1000,"iteration_unit":"次"}}
- "前10秒恒流5A" → {{"type":"temporal","original":"前10秒恒流5A","param":"电流","phase":"阶段1","duration":10,"duration_unit":"s","value":5,"value_unit":"A"}}
- "超过3次失败则锁定账户" → {{"type":"conditional","original":"超过3次失败则锁定账户","condition":"失败次数>3","action":"锁定账户"}}
- "超时时间默认30s" → {{"type":"default","original":"超时时间默认30s","param":"超时时间","value":30,"unit":"s"}}
- "采用256位AES加密" → {{"type":"design","original":"采用256位AES加密","param":"加密强度","value":256,"unit":"bit","description":"AES加密"}}

章节: {title}
内容:
{text}"""


def call_llm(prompt: str, max_retries: int = 5) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "Host": API_HOST,
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 8192,
    }
    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=120, verify=False)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            wait = min(10 * (attempt + 1), 60)
            print(f"    API attempt {attempt+1}/{max_retries} failed: {type(e).__name__}, waiting {wait}s", flush=True)
            if attempt < max_retries - 1:
                time.sleep(wait)
    return ""


def parse_llm_output(content: str) -> list:
    if not content:
        return []
    content = content.strip()
    for prefix in ("```json", "```"):
        if content.startswith(prefix):
            content = content[len(prefix):]
            break
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            if "constraints" in result:
                return result["constraints"]
            return [result]
        return []
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []


def is_gjb_format(md_path: Path) -> bool:
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return any(marker in text for marker in GJB_MARKERS)


def extract_sections(md_path: Path) -> list:
    content = md_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    sections = []
    current = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip()
            if current:
                current["text"] = "\n".join(current["lines"]).strip()
                sections.append(current)
            current = {"level": level, "title": title, "line_start": i + 1, "lines": []}
        elif current:
            current["lines"].append(line)
    if current:
        current["text"] = "\n".join(current["lines"]).strip()
        sections.append(current)
    return [s for s in sections if s["text"]]


def _process_section(section: dict) -> tuple:
    """Process a single section: call LLM and return (title, char_count, constraints, success)."""
    text = section["text"]
    title = section["title"]
    prompt = EXTRACTION_PROMPT.format(title=title, text=text[:1500])
    content = call_llm(prompt)
    success = bool(content)
    constraints = parse_llm_output(content) if success else []
    result = []
    for con in constraints:
        if isinstance(con, dict):
            con["section_title"] = title
            con["line_start"] = section["line_start"]
            result.append(con)
    return (title, len(text), result, success)


def extract_constraints_from_doc(md_path: Path, doc_name: str, source: str) -> dict:
    sections = extract_sections(md_path)

    # Filter sections that need processing
    to_process = []
    for section in sections:
        text = section["text"]
        title = section["title"]
        if len(text) < 50:
            continue
        if "目 录" in title or "目次" in title or "TOC" in title.upper():
            continue
        if not any(c.isdigit() for c in text):
            continue
        to_process.append(section)

    print(f"  {len(to_process)}/{len(sections)} sections to process (concurrent x{MAX_WORKERS})", flush=True)

    # Check for partial results (resume from crash)
    partial_path = OUTPUT_DIR / f"{doc_name}_partial.json"
    all_constraints = []
    done_titles = set()
    if partial_path.exists():
        try:
            partial = json.loads(partial_path.read_text(encoding="utf-8"))
            all_constraints = partial.get("constraints", [])
            done_titles = set(partial.get("done_titles", []))
            print(f"  Resuming: {len(done_titles)} sections already done, {len(to_process) - len(done_titles)} remaining", flush=True)
        except Exception:
            pass

    remaining = [s for s in to_process if s["title"] not in done_titles]
    done = len(done_titles)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_process_section, s): s for s in remaining}
        for future in as_completed(futures):
            done += 1
            title, char_count, constraints, success = future.result()
            if success:
                done_titles.add(title)
            if constraints:
                all_constraints.extend(constraints)
                print(f"  [{done}/{len(to_process)}] {title[:50]}  -> {len(constraints)} constraints", flush=True)
            elif success:
                print(f"  [{done}/{len(to_process)}] {title[:50]}  -> 0", flush=True)
            else:
                print(f"  [{done}/{len(to_process)}] {title[:50]}  -> API FAILED (will retry on restart)", flush=True)

            # Save intermediate results every 5 sections
            if done % 5 == 0 or done == len(to_process):
                all_constraints.sort(key=lambda c: c.get("line_start", 0))
                partial_path.write_text(json.dumps({
                    "constraints": all_constraints,
                    "done_titles": list(done_titles),
                }, indent=2, ensure_ascii=False), encoding="utf-8")

    # Clean up partial file
    if partial_path.exists():
        partial_path.unlink()

    all_constraints.sort(key=lambda c: c.get("line_start", 0))

    by_type = {}
    for c in all_constraints:
        t = c.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "doc_name": doc_name,
        "source": source,
        "source_file": str(md_path.relative_to(REPO_ROOT)),
        "total": len(all_constraints),
        "by_type": by_type,
        "processed_sections": len(to_process),
        "total_sections": len(sections),
        "extract_date": datetime.now().isoformat(),
        "constraints": all_constraints,
    }


def main():
    print("=" * 70)
    print("SRS Constraint Extractor - buaa/asyncTask collection")
    print(f"API: {API_URL} (Host: {API_HOST}, IP: {_API_IP})")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sources = {"buaa": COLLECTION_DIR / "buaa", "asyncTask": COLLECTION_DIR / "asyncTask"}

    candidates = []
    seen_hashes = set()

    for source_name, src_dir in sources.items():
        if not src_dir.exists():
            print(f"[WARN] {src_dir} not found, skipping")
            continue
        for md_path in sorted(src_dir.rglob("*.md")):
            if not is_gjb_format(md_path):
                print(f"  SKIP (non-GJB): {md_path.name}")
                continue
            file_hash = hashlib.md5(md_path.read_bytes()).hexdigest()
            if file_hash in seen_hashes:
                print(f"  SKIP (duplicate): {md_path.name}")
                continue
            seen_hashes.add(file_hash)
            line_count = len(md_path.read_text(encoding="utf-8", errors="replace").splitlines())
            candidates.append((source_name, md_path, line_count))
            print(f"  GJB: {md_path.name} ({line_count} lines)")

    if len(candidates) > 10:
        candidates.sort(key=lambda x: x[2], reverse=True)
        candidates = candidates[:10]
        print(f"\n>10 GJB files found, using top {len(candidates)} by line count")

    print(f"\nTotal GJB documents to process: {len(candidates)}")
    print("-" * 70)

    all_results = []
    for idx, (source_name, md_path, line_count) in enumerate(candidates, 1):
        doc_name = md_path.stem
        output_path = OUTPUT_DIR / f"{doc_name}_constraints.json"

        if output_path.exists():
            print(f"\n[{idx}/{len(candidates)}] {doc_name}  ALREADY DONE, loading existing result", flush=True)
            result = json.loads(output_path.read_text(encoding="utf-8"))
            all_results.append(result)
            continue

        print(f"\n[{idx}/{len(candidates)}] {doc_name}  ({source_name}, {line_count} lines)", flush=True)

        result = extract_constraints_from_doc(md_path, doc_name, source_name)

        output_path = OUTPUT_DIR / f"{doc_name}_constraints.json"
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        all_results.append(result)
        print(f"  SAVED: {output_path.name}  ({result['total']} constraints, {result['by_type']})", flush=True)

    summary = {
        "extract_date": datetime.now().isoformat(),
        "total_docs": len(all_results),
        "total_constraints": sum(r["total"] for r in all_results),
        "docs": [
            {
                "doc_name": r["doc_name"],
                "source": r["source"],
                "total": r["total"],
                "by_type": r["by_type"],
                "processed_sections": r["processed_sections"],
            }
            for r in all_results
        ],
    }
    (OUTPUT_DIR / "_collection_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n{'=' * 70}")
    print("EXTRACTION COMPLETE")
    print(f"  Documents processed: {len(all_results)}")
    print(f"  Total constraints:   {summary['total_constraints']}")
    print("-" * 70)
    for d in summary["docs"]:
        print(f"  [{d['source']:10s}] {d['doc_name']:45s} {d['total']:4d} constraints  {d['by_type']}")
    print(f"\n  Output dir: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
