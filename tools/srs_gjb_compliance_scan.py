#!/usr/bin/env python3
"""
GJB 438C Format Compliance Scanner

Scans all .md files under srs_collection/ and checks GJB 438C format
compliance across 7 dimensions:

  1. Section completeness      — 6 required chapters (1 范围 … 6 注释)
  2. Requirement IDs           — unique identifiers (REQ-X.Y.Z, R001, etc.)
  3. Qualification methods     — 演示/测试/分析/审查
  4. Traceability              — bidirectional system↔CSCI tracing
  5. Numbering format          — X.Y.Z section numbering
  6. Table completeness        — modification / reference / qualification / trace tables
  7. Content field completeness — required content fields in key sections

Outputs:
  compliance_check.json        — per-document report array
  compliance_statistics.json   — aggregate statistics
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
SRS_COLLECTION = REPO_ROOT / "data" / "gjb_438c" / "srs_collection"
OUTPUT_DIR = SRS_COLLECTION


# ── Heading extraction ────────────────────────────────────────

def extract_headings(text: str) -> list[dict]:
    """Parse markdown ATX headings (## 1.2 Title) into structured records."""
    headings = []
    for m in re.finditer(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE):
        level = len(m.group(1))
        raw = m.group(2).strip()
        # Strip trailing markdown like " Scope." → number=1, title="Scope"
        num_m = re.match(r'^(\d+(?:\.\d+)*)\.?\s*(.*)', raw)
        if num_m:
            number = num_m.group(1)
            title = num_m.group(2).strip().rstrip('.')
        else:
            number = None
            title = raw.rstrip('.')
        headings.append({'level': level, 'number': number, 'title': title, 'raw': raw})
    return headings


# ── GJB version detection ─────────────────────────────────────

def detect_gjb_version(text: str, headings: list[dict]) -> str:
    """Return '438C', '438B', or 'unknown'."""
    tl = text.lower()

    # Explicit version string in document
    if 'gjb 438c' in tl or '438c' in tl or 'gjb438c' in tl:
        return '438C'
    if 'gjb 438b' in tl or '438b' in tl or 'gjb438b' in tl:
        return '438B'

    # Structural inference
    titles = ' '.join(h['title'] for h in headings)
    numbers = {h['number']: h['title'] for h in headings if h['number']}

    # GJB 438B: 3.2=需求概述, 3.3=需求规格, 3.4=CSCI能力需求
    is_438b = (
        ('需求概述' in titles and '需求规格' in titles)
        or numbers.get('3.4', '').startswith('CSCI能力')
        or numbers.get('3.2', '') == '需求概述'
    )
    # GJB 438C: 3.2=CSCI能力需求, 3.3=CSCI外部接口需求
    is_438c = (
        numbers.get('3.2', '').startswith('CSCI能力')
        or numbers.get('3.3', '').startswith('CSCI外部接口')
    )

    if is_438b:
        return '438B'
    if is_438c:
        return '438C'

    # If document has GJB-style top-level structure, default to 438C
    has_gjb_struct = (
        any('范围' in h['title'] for h in headings)
        and any(kw in h['title'] for h in headings for kw in ('引用文档', '引用文件'))
        and any('需求' in h['title'] for h in headings)
        and any(kw in h['title'] for h in headings for kw in ('合格性', '追踪'))
    )
    if has_gjb_struct:
        return '438C'

    return 'unknown'


# ── Document-type heuristic ───────────────────────────────────

def detect_doc_type(filename: str, headings: list[dict], text: str) -> str:
    """Best-effort document type tag for filtering."""
    fn = filename.lower()
    titles = ' '.join(h['title'] for h in headings).lower()

    if fn == 'readme.md' or fn.startswith('readme'):
        return 'readme'
    if any(kw in fn for kw in ('inventory', 'metadata', 'download', 'catalog',
                                'analysis_report', 'new_srs_found', 'progress',
                                'task_plan', 'findings')):
        return 'meta'
    if any(kw in fn for kw in ('sdd', '设计说明', '设计说明书', '概要设计', '详细设计')):
        return 'sdd'
    if any(kw in fn for kw in ('dbdd', '数据库设计')):
        return 'dbdd'
    if any(kw in fn for kw in ('sdp', '开发计划', '开发计划书')):
        return 'sdp'
    if any(kw in fn for kw in ('skill', 'contributing')):
        return 'skill'
    if any(kw in fn for kw in ('irs', '接口需求清单', '接口需求规格')):
        return 'irs'
    if any(kw in fn for kw in ('sss', '系统/子系统规格')):
        return 'sss'
    if any(kw in fn for kw in ('sps', '产品规格')):
        return 'sps'
    if any(kw in fn for kw in ('scmp', '配置管理')):
        return 'scmp'
    if any(kw in fn for kw in ('用例', '场景', 'usecase', 'use_case')):
        return 'usecase'
    if any(kw in fn for kw in ('api', '接口设计')):
        return 'api'
    if any(kw in fn for kw in ('类图', '时序图', '架构设计', 'architecture')):
        return 'design'
    # Check by content
    if any(kw in titles for kw in ('需求规格', 'requirements specification', 'srs')):
        return 'srs'
    if any(kw in titles for kw in ('设计说明', 'design description')):
        return 'sdd'
    if len(headings) < 3:
        return 'fragment'

    return 'srs'


# ── Check 1: Section completeness ─────────────────────────────

REQUIRED_CHAPTERS = [
    {'num': '1', 'kws': ['范围', 'scope', '标识'], 'name': '1 范围',
     'subs': [
         ('1.1', ['标识', 'identification'], '1.1 标识'),
         ('1.2', ['系统概述', 'system overview'], '1.2 系统概述'),
         ('1.3', ['文档概述', 'document overview'], '1.3 文档概述'),
     ]},
    {'num': '2', 'kws': ['引用文档', '引用文件', 'referenced document',
                         'reference'], 'name': '2 引用文档', 'subs': []},
    {'num': '3', 'kws': ['需求', 'requirement'], 'name': '3 需求', 'subs': []},
    {'num': '4', 'kws': ['合格性规定', '合格性', 'qualification'], 'name': '4 合格性规定', 'subs': []},
    {'num': '5', 'kws': ['需求可追踪性', '可追踪性', 'traceability'], 'name': '5 需求可追踪性', 'subs': []},
    {'num': '6', 'kws': ['注释', '注解', 'note'], 'name': '6 注释', 'subs': []},
]


def check_section_completeness(headings: list[dict]) -> dict:
    missing = []
    found = []

    for ch in REQUIRED_CHAPTERS:
        is_found = False
        for h in headings:
            tl = h['title'].lower()
            if h['number'] == ch['num']:
                is_found = True
                break
            for kw in ch['kws']:
                if kw in tl or kw in h['raw'].lower():
                    is_found = True
                    break
            if is_found:
                break

        if is_found:
            found.append(ch['name'])
        else:
            missing.append(ch['name'])
            continue  # skip sub-checks if parent missing

        # Check sub-sections
        for sub_num, sub_kws, sub_name in ch['subs']:
            sub_found = False
            for h in headings:
                tl = h['title'].lower()
                if h['number'] == sub_num:
                    sub_found = True
                    break
                for kw in sub_kws:
                    if kw in tl or kw in h['raw'].lower():
                        sub_found = True
                        break
                if sub_found:
                    break
            if not sub_found:
                missing.append(sub_name)

    return {'pass': len(missing) == 0, 'missing': missing, 'found': found}


# ── Check 2: Requirement IDs ──────────────────────────────────

REQ_ID_PATTERNS = [
    r'\bREQ[-_]\d+(?:\.\d+)*\b',
    r'\bR\d{3,}\b',
    r'\bFR[-_]?\d+\b',
    r'\bNFR[-_]?\d+\b',
    r'\bUR[-_]?\d+\b',
    r'\bSR[-_]?\d+\b',
    r'\bCSCI[-_]\d+\b',
    r'\b[A-Z]{2,5}[-_]\d{2,}\b',
    r'需求[-_]?[\d.]+',
]


def check_requirement_ids(text: str, headings: list[dict]) -> dict:
    all_ids = set()
    for pat in REQ_ID_PATTERNS:
        all_ids.update(re.findall(pat, text))

    # Numbered sub-subsections under chapter 3 (e.g. 3.2.1) act as req IDs
    for h in headings:
        if h['number'] and re.match(r'^3\.\d+\.\d+', h['number']):
            all_ids.add(f"REQ-{h['number']}")

    return {
        'pass': len(all_ids) > 0,
        'count': len(all_ids),
        'ids': sorted(all_ids)[:20],
    }


# ── Check 3: Qualification methods ────────────────────────────

QUAL_METHODS_CN = ['演示', '测试', '分析', '审查', '检验', '特殊合格性']
QUAL_METHODS_EN = ['demonstration', 'test', 'analysis', 'inspection',
                   'review', 'examination']


def check_qualification_methods(text: str) -> dict:
    tl = text.lower()
    found = set()
    for m in QUAL_METHODS_CN:
        if m in text:
            found.add(m)
    for m in QUAL_METHODS_EN:
        if m in tl:
            found.add(m)
    return {
        'pass': len(found) >= 2,
        'methods': sorted(found),
    }


# ── Check 4: Traceability ─────────────────────────────────────

def check_traceability(text: str, headings: list[dict]) -> dict:
    tl = text.lower()

    has_trace_section = any(
        kw in h['title'] or kw in h['raw']
        for h in headings
        for kw in ('可追踪性', '追踪', 'traceability')
    )

    has_trace_kw = any(kw in text for kw in ('可追踪性', '追踪', 'traceability', 'trace'))
    has_system_req = any(
        kw in text for kw in ('系统需求', '系统/子系统需求', 'system requirement', 'system/subsystem')
    )
    has_csci_req = 'CSCI' in text and '需求' in text or 'csci' in tl and 'requirement' in tl

    # Traceability table
    has_trace_table = False
    if has_trace_kw and re.search(r'^\|.*\|.*\|', text, re.MULTILINE):
        has_trace_table = True

    bidirectional = has_system_req and has_csci_req

    passed = has_trace_section or (has_trace_kw and (has_system_req or has_csci_req))

    return {
        'pass': passed,
        'bidirectional': bidirectional,
        'has_trace_section': has_trace_section,
        'has_trace_table': has_trace_table,
    }


# ── Check 5: Numbering format ─────────────────────────────────

def check_numbering_format(headings: list[dict]) -> dict:
    numbered = sum(1 for h in headings if h['number'])
    total = len(headings)
    if total == 0:
        return {'pass': False, 'numbered_sections': 0, 'total_sections': 0}
    ratio = numbered / total
    return {
        'pass': ratio >= 0.5 and numbered >= 3,
        'numbered_sections': numbered,
        'total_sections': total,
        'ratio': round(ratio, 2),
    }


# ── Check 6: Table completeness ───────────────────────────────

TABLE_TYPES = {
    '修改页': ['修改页', '修改历史', '修改记录', '修订历史', 'revision history',
              'change history', '版本历史', '修订记录'],
    '引用文档表': ['引用文档', '引用文件', '参考文档', 'referenced document'],
    '合格性表': ['合格性', 'qualification', '检验方法', '合格性方法'],
    '追踪表': ['追踪', '可追踪性', 'traceability', '追溯'],
}


def check_table_completeness(text: str) -> dict:
    table_lines = re.findall(r'^\|.*\|.*$', text, re.MULTILINE)
    has_tables = len(table_lines) >= 2

    found_types = {}
    for tname, keywords in TABLE_TYPES.items():
        if any(kw in text or kw in text.lower() for kw in keywords) and has_tables:
            found_types[tname] = True
        elif has_tables:
            # Check table cell content
            table_text = '\n'.join(table_lines)
            if any(kw in table_text.lower() for kw in keywords):
                found_types[tname] = True
            else:
                found_types[tname] = False
        else:
            found_types[tname] = False

    missing = [k for k, v in found_types.items() if not v]
    # Pass if at least 2 of 4 table types are present
    return {
        'pass': sum(found_types.values()) >= 2,
        'missing': missing,
        'found': [k for k, v in found_types.items() if v],
        'has_tables': has_tables,
    }


# ── Check 7: Content field completeness ───────────────────────

CONTENT_FIELD_CHECKS = [
    {'section_prefix': '1.1', 'fields': ['标识号', '名称', '版本号', '发布号',
                                          'version', 'identification', '文档编号']},
    {'section_prefix': '1.2', 'fields': ['用途', '一般特性', '运行', 'purpose',
                                          '概述', 'overview', '特性']},
    {'section_prefix': '1.3', 'fields': ['用途', '内容', '安全', 'purpose',
                                          'content', 'security', '概述']},
    {'section_prefix': '3',   'fields': ['标识符', 'identifier', '唯一标识',
                                          '需求', 'requirement', 'CSCI']},
    {'section_prefix': '4',   'fields': ['演示', '测试', '分析', '审查',
                                          'demonstration', 'test', 'analysis',
                                          'inspection', '合格性']},
    {'section_prefix': '5',   'fields': ['CSCI', '系统', '追踪', 'system',
                                          'traceability', '可追踪']},
]


def check_content_fields(headings: list[dict], text: str) -> dict:
    tl = text.lower()
    missing_fields = []

    for chk in CONTENT_FIELD_CHECKS:
        # Does this section exist?
        section_exists = any(
            h['number'] and h['number'].startswith(chk['section_prefix'])
            for h in headings
        )
        if not section_exists:
            continue  # skip field check if the section is absent

        has_any = any(f in text or f in tl for f in chk['fields'])
        if not has_any:
            missing_fields.append(f"{chk['section_prefix']} 缺少内容字段")

    return {
        'pass': len(missing_fields) == 0,
        'missing_fields': missing_fields,
    }


# ── Main per-document check ───────────────────────────────────

def check_document(file_path: Path, source_dir: str) -> dict:
    try:
        text = file_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        text = ''

    headings = extract_headings(text)
    gjb_version = detect_gjb_version(text, headings)
    doc_type = detect_doc_type(file_path.name, headings, text)

    checks = {
        'section_completeness': check_section_completeness(headings),
        'requirement_ids': check_requirement_ids(text, headings),
        'qualification_methods': check_qualification_methods(text),
        'traceability': check_traceability(text, headings),
        'numbering_format': check_numbering_format(headings),
        'table_completeness': check_table_completeness(text),
        'content_fields': check_content_fields(headings, text),
    }

    score = sum(1 for c in checks.values() if c['pass'])

    # Heuristic: is this an actual SRS document (not README/meta)?
    is_srs_like = (
        doc_type in ('srs', 'irs', 'sss')
        and len(headings) >= 5
    )

    rel_path = str(file_path.relative_to(SRS_COLLECTION))

    return {
        'file': file_path.name,
        'relative_path': rel_path,
        'source_dir': source_dir,
        'doc_type': doc_type,
        'is_srs_like': is_srs_like,
        'compliance_score': score,
        'checks': checks,
        'is_gjb_compliant': score >= 5,
        'gjb_version': gjb_version,
        'file_size': file_path.stat().st_size,
        'heading_count': len(headings),
    }


# ── Main ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("GJB 438C Format Compliance Scanner")
    print(f"Scanning: {SRS_COLLECTION}")
    print("=" * 60)

    md_files = sorted(SRS_COLLECTION.rglob("*.md"))
    print(f"Found {len(md_files)} .md files\n")

    all_reports = []

    for i, fp in enumerate(md_files, 1):
        rel = fp.relative_to(SRS_COLLECTION)
        source_dir = str(rel.parts[0]) if len(rel.parts) > 1 else "root"

        report = check_document(fp, source_dir)
        all_reports.append(report)

        if i % 50 == 0 or i == len(md_files):
            print(f"  [{i}/{len(md_files)}] processed")

    # ── Write per-document report ──
    check_path = OUTPUT_DIR / "compliance_check.json"
    check_path.write_text(
        json.dumps(all_reports, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    print(f"\nPer-document report → {check_path}")

    # ── Compute statistics ──
    total = len(all_reports)
    srs_docs = [r for r in all_reports if r['is_srs_like']]
    total_srs = len(srs_docs)

    compliant_all = sum(1 for r in all_reports if r['is_gjb_compliant'])
    compliant_srs = sum(1 for r in srs_docs if r['is_gjb_compliant'])

    avg_all = round(sum(r['compliance_score'] for r in all_reports) / max(total, 1), 2)
    avg_srs = round(sum(r['compliance_score'] for r in srs_docs) / max(total_srs, 1), 2)

    check_names = list(all_reports[0]['checks'].keys()) if all_reports else []
    pass_rates = {}
    pass_rates_srs = {}
    for name in check_names:
        p_all = sum(1 for r in all_reports if r['checks'][name]['pass'])
        p_srs = sum(1 for r in srs_docs if r['checks'][name]['pass'])
        pass_rates[name] = {
            'passed': p_all, 'total': total,
            'rate': round(p_all / max(total, 1) * 100, 1),
        }
        pass_rates_srs[name] = {
            'passed': p_srs, 'total': total_srs,
            'rate': round(p_srs / max(total_srs, 1) * 100, 1),
        }

    # By source directory
    by_source = defaultdict(lambda: {'total': 0, 'srs': 0, 'compliant': 0,
                                      'scores': [], 'srs_scores': []})
    for r in all_reports:
        s = r['source_dir']
        by_source[s]['total'] += 1
        by_source[s]['scores'].append(r['compliance_score'])
        if r['is_srs_like']:
            by_source[s]['srs'] += 1
            by_source[s]['srs_scores'].append(r['compliance_score'])
        if r['is_gjb_compliant']:
            by_source[s]['compliant'] += 1

    source_stats = {}
    for s in sorted(by_source):
        d = by_source[s]
        source_stats[s] = {
            'total_docs': d['total'],
            'srs_docs': d['srs'],
            'compliant_docs': d['compliant'],
            'compliance_rate': round(d['compliant'] / max(d['total'], 1) * 100, 1),
            'avg_score_all': round(sum(d['scores']) / max(len(d['scores']), 1), 2),
            'avg_score_srs': round(sum(d['srs_scores']) / max(len(d['srs_scores']), 1), 2)
                            if d['srs_scores'] else 0,
        }

    # GJB version distribution
    version_dist = defaultdict(int)
    for r in all_reports:
        version_dist[r['gjb_version']] += 1

    # Score distribution
    score_dist = {str(s): sum(1 for r in all_reports if r['compliance_score'] == s)
                  for s in range(8)}
    score_dist_srs = {str(s): sum(1 for r in srs_docs if r['compliance_score'] == s)
                      for s in range(8)}

    # Doc type distribution
    type_dist = defaultdict(int)
    for r in all_reports:
        type_dist[r['doc_type']] += 1

    statistics = {
        'check_date': datetime.now().isoformat(),
        'standard': 'GJB 438C-2021',
        'total_documents': total,
        'total_srs_documents': total_srs,
        'compliant_documents': compliant_all,
        'compliant_srs_documents': compliant_srs,
        'compliance_rate_all': round(compliant_all / max(total, 1) * 100, 1),
        'compliance_rate_srs': round(compliant_srs / max(total_srs, 1) * 100, 1),
        'average_score_all': avg_all,
        'average_score_srs': avg_srs,
        'check_pass_rates_all': pass_rates,
        'check_pass_rates_srs': pass_rates_srs,
        'by_source_directory': source_stats,
        'gjb_version_distribution': dict(sorted(version_dist.items())),
        'doc_type_distribution': dict(sorted(type_dist.items())),
        'score_distribution_all': score_dist,
        'score_distribution_srs': score_dist_srs,
    }

    stats_path = OUTPUT_DIR / "compliance_statistics.json"
    stats_path.write_text(
        json.dumps(statistics, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    print(f"Statistics          → {stats_path}")

    # ── Console summary ──
    print(f"\n{'=' * 60}")
    print("COMPLIANCE SCAN COMPLETE")
    print(f"  Total .md files scanned : {total}")
    print(f"  SRS-like documents      : {total_srs}")
    print(f"  Compliant (score>=5)    : {compliant_all} ({statistics['compliance_rate_all']}%)")
    print(f"  Compliant SRS docs      : {compliant_srs} ({statistics['compliance_rate_srs']}%)")
    print(f"  Avg score (all / SRS)   : {avg_all} / {avg_srs}")
    print(f"  Score dist (all)        : {score_dist}")
    print(f"  GJB versions            : {dict(sorted(version_dist.items()))}")
    print(f"  Doc types               : {dict(sorted(type_dist.items()))}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
