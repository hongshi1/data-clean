#!/usr/bin/env python3
"""
Batch SRS Constraint Extractor for more_gjb/ and gjb438b/ collections.

Scans markdown SRS documents, filters GJB-format files (containing
"合格性规定" or "CSCI"), splits into sections, and calls GLM-5 to
extract 7 types of constraints per section.

Output: one JSON per document under extracted_constraints/.
"""

import hashlib
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests  # noqa: F401  (kept for compatibility; curl used at runtime)

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTION_DIRS = [
    REPO_ROOT / "data" / "gjb_438c" / "srs_collection" / "more_gjb",
    REPO_ROOT / "data" / "gjb_438c" / "srs_collection" / "gjb438b",
]
OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_constraints"

API_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
API_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
MODEL = "ep-glsztk-1778496696841467392"

MAX_FILES = 15
MAX_SECTION_CHARS = 1500

EXTRACTION_PROMPT = """从以下SRS章节中提取所有约束，分7类:
1. numerical: 数值约束  2. tolerance: 对称容差  3. cumulative: 累积约束
4. temporal: 时序约束  5. conditional: 条件约束  6. default: 默认值  7. design: 设计参数
每条约束输出JSON: {type, original, param, value, unit}
只输出JSON数组。

章节: {title}
内容:
{text}"""


# ---------- file discovery ----------

# Non-SRS keywords in filename -> exclude (companion GJB docs, templates,
# standards, references, READMEs, skill docs).
_NON_SRS_KEYWORDS = (
    "设计说明", "配置管理", "开发计划", "详细设计", "概要设计",
    "reference", "README", "SKILL", "standard", "template", "模板",
)
# SRS keywords in filename -> keep.
_SRS_KEYWORDS = ("需求规格", "需求规则", "SRS", "需求规格说明")


def is_gjb_format(md_path: Path) -> bool:
    """GJB-format marker: contains 合格性规定 or CSCI."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return ("合格性规定" in text) or ("CSCI" in text or "CSCI " in text)


def is_srs_document(md_path: Path) -> bool:
    """True only for real SRS documents.

    Keeps files whose name indicates an SRS (需求规格/SRS) and excludes
    companion GJB docs (SDD/SCMP/dev-plan), templates, standards,
    references, READMEs and skill docs.
    """
    name = md_path.name
    if any(k in name for k in _NON_SRS_KEYWORDS):
        return False
    return any(k in name for k in _SRS_KEYWORDS)


def collect_files():
    """Find .md files, dedup by content hash, filter GJB-format,
    sort by line count desc, return top MAX_FILES."""
    seen_hashes = set()
    candidates = []

    for d in COLLECTION_DIRS:
        if not d.exists():
            continue
        for md_path in sorted(d.rglob("*.md")):
            try:
                raw = md_path.read_bytes()
            except Exception:
                continue
            digest = hashlib.md5(raw).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)

            if not is_gjb_format(md_path):
                continue
            if not is_srs_document(md_path):
                continue

            n_lines = raw.count(b"\n") + 1
            candidates.append((n_lines, md_path))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[:MAX_FILES], len(candidates)


# ---------- section splitting ----------

_HEADING_RE = re.compile(r"^(#+)\s+(.*)$")
_NUM_BOLD_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*[\.\、]\s*\*\*(.+?)\*\*\s*$")
_CN_NUM_RE = re.compile(r"^([一二三四五六七八九十百]+)\s*、\s*(.+)$")
_BOLD_ONLY_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")


def extract_sections(md_path: Path) -> list:
    """Split markdown into sections.

    Handles standard '#'-headings plus fallbacks for GJB docs that use
    bold-only or numbered-bold heading styles (e.g. H2H doc).
    """
    content = md_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    # First pass: try '#' headings.
    sections = _split_by_hash(lines)

    # If too few real sections, fall back to bold/numbered headings.
    if len(sections) < 4:
        sections = _split_by_bold(lines)

    return [s for s in sections if s["text"].strip()]


def _split_by_hash(lines):
    sections = []
    cur = None
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            if cur:
                cur["text"] = "\n".join(cur["lines"]).strip()
                sections.append(cur)
            cur = {
                "level": len(m.group(1)),
                "title": m.group(2).strip(),
                "line_start": i + 1,
                "lines": [],
            }
        elif cur:
            cur["lines"].append(line)
    if cur:
        cur["text"] = "\n".join(cur["lines"]).strip()
        sections.append(cur)
    return sections


def _split_by_bold(lines):
    """Fallback splitter: treat numbered-bold, cn-numbered, or bold-only
    lines as headings."""
    sections = []
    cur = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        title = None
        level = 2

        m = _NUM_BOLD_RE.match(stripped)
        if m:
            title = f"{m.group(1)} {m.group(2)}"
            level = 2
        else:
            m = _CN_NUM_RE.match(stripped)
            if m:
                title = f"{m.group(1)}、{m.group(2)}"
                level = 1
            elif _BOLD_ONLY_RE.match(stripped) and len(stripped) < 40:
                title = _BOLD_ONLY_RE.match(stripped).group(1).strip()
                level = 2

        if title:
            if cur:
                cur["text"] = "\n".join(cur["lines"]).strip()
                sections.append(cur)
            cur = {
                "level": level,
                "title": title,
                "line_start": i + 1,
                "lines": [],
            }
        elif cur:
            cur["lines"].append(line)
    if cur:
        cur["text"] = "\n".join(cur["lines"]).strip()
        sections.append(cur)
    return sections


# ---------- LLM ----------

def call_llm(prompt: str, max_retries: int = 5) -> str:
    """Call GLM-5 via curl subprocess.

    Python's ssl stack intermittently raises SSLEOFError against this
    endpoint on macOS, while curl is reliable, so we shell out to curl.
    Uses exponential backoff to ride out transient DNS/network outages
    to the corporate API host.
    """
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 8192,
    }, ensure_ascii=False)

    backoffs = [2, 5, 10, 20, 30]
    for attempt in range(max_retries):
        try:
            proc = subprocess.run(
                [
                    "curl", "-sS", "-m", "180",
                    "-X", "POST", API_URL,
                    "-H", "Content-Type: application/json",
                    "-H", f"Authorization: Bearer {API_KEY}",
                    "-d", payload,
                ],
                capture_output=True, text=True, timeout=200,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"curl rc={proc.returncode}: {proc.stderr.strip()[:160]}")
            data = json.loads(proc.stdout)
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            wait = backoffs[min(attempt, len(backoffs) - 1)]
            print(f"    API attempt {attempt+1}/{max_retries} failed: {e} "
                  f"(wait {wait}s)")
            if attempt < max_retries - 1:
                time.sleep(wait)
    return ""


def parse_llm_output(content: str) -> list:
    if not content:
        return []
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
        if isinstance(result, dict):
            if "constraints" in result:
                return result["constraints"]
            return [result]
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []


# ---------- per-doc extraction ----------

def extract_constraints_from_doc(md_path: Path, doc_name: str) -> dict:
    sections = extract_sections(md_path)

    all_constraints = []
    stats = {"total_sections": len(sections), "sections_sent": 0,
             "sections_with_constraints": 0, "sections_failed": 0}
    failed_sections = []

    def process_section(section):
        text = section["text"]
        title = section["title"]
        if len(text) < 50:
            return None
        if "目 录" in title or "目次" in title or "目录" in title:
            return None
        if not any(c.isdigit() for c in text):
            return None

        stats["sections_sent"] += 1
        section_num_match = re.match(r"^(\d+(?:\.\d+)*)", title)
        section_number = section_num_match.group(1) if section_num_match else ""

        print(f"    [{stats['sections_sent']}] {title[:40]} ({len(text)} chars)")

        prompt = EXTRACTION_PROMPT.replace("{title}", title).replace(
            "{text}", text[:MAX_SECTION_CHARS]
        )
        content = call_llm(prompt)
        if not content:
            return "FAILED"
        constraints = parse_llm_output(content)

        for con in constraints:
            if not isinstance(con, dict):
                continue
            con["section_number"] = section_number
            con["section_title"] = title
            con["line_start"] = section["line_start"]

        if constraints:
            stats["sections_with_constraints"] += 1
            all_constraints.extend(constraints)
            print(f"        -> {len(constraints)} constraints")
        return "OK"

    for section in sections:
        result = process_section(section)
        if result == "FAILED":
            failed_sections.append(section)

    # Retry sections that failed (e.g. transient network outage) once more.
    if failed_sections:
        print(f"    retrying {len(failed_sections)} failed sections...")
        time.sleep(5)
        retry_failed = []
        for section in failed_sections:
            stats["sections_sent"] -= 1  # don't double-count
            result = process_section(section)
            if result == "FAILED":
                retry_failed.append(section)
        stats["sections_failed"] = len(retry_failed)
    else:
        stats["sections_failed"] = 0

    stats["total_constraints"] = len(all_constraints)
    by_type = {}
    for c in all_constraints:
        t = c.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    stats["by_type"] = by_type

    return {
        "doc_name": doc_name,
        "source_path": str(md_path.relative_to(REPO_ROOT)),
        "n_lines": md_path.read_text(encoding="utf-8", errors="replace").count("\n") + 1,
        "extract_date": datetime.now().isoformat(),
        "stats": stats,
        "constraints": all_constraints,
    }


# ---------- main ----------

def main():
    print("=" * 60)
    print("Batch SRS Constraint Extractor (more_gjb + gjb438b)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selected, total_gjb = collect_files()
    print(f"\nGJB-format files found: {total_gjb}")
    print(f"Processing top {len(selected)} by line count:\n")
    for n, (_, p) in enumerate(selected, 1):
        print(f"  {n:2d}. {p.name}  ({p.relative_to(REPO_ROOT)})")

    all_results = []
    for idx, (n_lines, md_path) in enumerate(selected, 1):
        doc_name = md_path.stem
        print(f"\n[{idx}/{len(selected)}] {doc_name}  ({n_lines} lines)")

        output_path = OUTPUT_DIR / f"{doc_name}_constraints.json"
        if output_path.exists():
            print(f"    already exists, skipping")
            try:
                prev = json.loads(output_path.read_text(encoding="utf-8"))
                all_results.append(prev)
            except Exception:
                pass
            continue

        try:
            result = extract_constraints_from_doc(md_path, doc_name)
        except Exception as e:
            print(f"    ERROR: {e}")
            result = {
                "doc_name": doc_name,
                "source_path": str(md_path.relative_to(REPO_ROOT)),
                "extract_date": datetime.now().isoformat(),
                "stats": {"total_sections": 0, "sections_sent": 0,
                          "sections_with_constraints": 0,
                          "total_constraints": 0, "by_type": {}, "error": str(e)},
                "constraints": [],
            }

        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        all_results.append(result)
        print(f"    SAVED: {result['stats']['total_constraints']} constraints "
              f"-> {output_path.name}")

    # Summary
    summary = {
        "extract_date": datetime.now().isoformat(),
        "total_docs": len(all_results),
        "total_constraints": sum(
            r.get("stats", {}).get("total_constraints", 0) for r in all_results),
        "docs": [
            {
                "doc_name": r.get("doc_name", "?"),
                "source_path": r.get("source_path", "?"),
                "n_lines": r.get("n_lines", 0),
                "total_constraints": r.get("stats", {}).get("total_constraints", 0),
                "sections_sent": r.get("stats", {}).get("sections_sent", 0),
                "by_type": r.get("stats", {}).get("by_type", {}),
            }
            for r in all_results
        ],
    }
    (OUTPUT_DIR / "_summary_more_gjb.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n{'=' * 60}")
    print("EXTRACTION COMPLETE")
    print(f"  Documents: {len(all_results)}")
    print(f"  Total constraints: {summary['total_constraints']}")
    for d in summary["docs"]:
        print(f"  - {d['doc_name']}: {d['total_constraints']} constraints "
              f"({d['by_type']})")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
