#!/usr/bin/env python3
"""Analyze IEEE 830 SRS collection: shall statements, tables, numerical
constraints, requirement IDs, system type. Walks ieee830/ and produces
a per-file report + aggregate statistics."""
import os, re, json, csv, sys
from pathlib import Path

ROOT = Path("/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c/srs_collection/ieee830")
OUT_MD = ROOT / "ANALYSIS_REPORT.md"
OUT_CSV = ROOT / "analysis.csv"

EXTS_TEXT = {".md", ".txt", ".tex", ".html", ".lyx", ".rtf"}
EXTS_PDF = {".pdf"}
EXTS_DOCX = {".docx"}

# ---- text extraction -------------------------------------------------------
def extract_pdf(path):
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text += t + "\n"
                # table count via pdfplumber
    except Exception:
        try:
            import PyPDF2
            with open(str(path), "rb") as f:
                r = PyPDF2.PdfReader(f)
                for p in r.pages:
                    text += (p.extract_text() or "") + "\n"
        except Exception:
            pass
    return text

def pdf_table_count(path):
    try:
        import pdfplumber
        n = 0
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                n += len(page.extract_tables() or [])
        return n
    except Exception:
        return 0

def extract_docx(path):
    text = ""
    tbl = 0
    try:
        import docx
        d = docx.Document(str(path))
        for p in d.paragraphs:
            text += p.text + "\n"
        tbl = len(d.tables)
        for t in d.tables:
            for row in t.rows:
                for cell in row.cells:
                    text += cell.text + " "
                text += "\n"
    except Exception:
        pass
    return text, tbl

def read_text_file(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

# ---- metrics ---------------------------------------------------------------
SHALL_RE = re.compile(r'\bshall\b', re.IGNORECASE)
# numerical constraint: number + unit OR comparison/range
NUM_UNIT_RE = re.compile(
    r'\b\d+(?:[.,]\d+)?\s*(?:'
    r'ms|millisecond|s|sec|second|min|minute|h|hr|hour|'
    r'kb|mb|gb|tb|byte|bps|kbps|mbps|gbps|'
    r'hz|khz|mhz|ghz|rpm|dpi|px|pixel|'
    r'%|percent|fps|frame|'
    r'user|users|request|requests|query|queries|transaction|transactions|'
    r'error|errors|retry|retries|session|sessions|connection|connections|'
    r'mb/s|gb/s|ms|ppm|db|decibel|c|°c|f|°f|kg|g|mm|cm|m|km|'
    r'point|points|credit|credits|token|tokens|item|items|order|orders|'
    r'slot|slots|seat|seats|character|characters|char|word|words|line|lines|'
    r'message|messages|notification|notifications|file|files|image|images|'
    r'record|records|entry|entries|field|fields|row|rows|column|columns'
    r')\b', re.IGNORECASE)
NUM_CMP_RE = re.compile(
    r'(?:>=|<=|>|<|=|==|!=|≥|≤|±|~|at least|at most|no (?:more|fewer) than|'
    r'min(?:imum)?(?:\s+of)?|max(?:imum)?(?:\s+of)?|between|within|less than|'
    r'greater than|not exceed|exceed)\s*\d+(?:[.,]\d+)?', re.IGNORECASE)
NUM_RANGE_RE = re.compile(r'\b\d+(?:[.,]\d+)?\s*(?:[-–~]|to|\u2013)\s*\d+(?:[.,]\d+)?')
# requirement IDs: REQ-001, FR1, NFR-02, UC01, SR-3, IF-1, etc.
REQ_ID_RE = re.compile(
    r'\b(?:REQ|FR|NFR|UC|IF|CF|PF|NF|SR|SRS|BR|CR|IR|TR|AR|QR|PR)[-_ ]?\d{1,4}\b|'
    r'\bRFC\s*\d+\b|'
    r'\b[A-Z]{2,5}[-_]\d{1,4}\b')
# Japanese requirement phrasing (IEEE 830 "shall" equivalent): 〜こと, できる, すること, ならない, ものとする
JP_REQ_RE = re.compile(r'こと|できる|すること|ならない|ものとする|とする')
# RTF control-word stripper for readable text
RTF_CTRL_RE = re.compile(r'\\[a-zA-Z]+-?\d* ?|\\[{}\\]|[^\\]\{|\}|\{\\fonttbl.*?\}', re.DOTALL)

def strip_rtf(text):
    if not text.lstrip().startswith('{\\rtf'):
        return text
    return RTF_CTRL_RE.sub(' ', text)

# markdown / html tables
MD_TBL_RE = re.compile(r'\|[^\n]+\|\s*\n\|[\s:|-]+\|', re.IGNORECASE)
HTML_TBL_RE = re.compile(r'<table', re.IGNORECASE)
LATEX_TBL_RE = re.compile(r'\\begin\{(?:tabular|longtable|table)')

def detect_table(text, fmt, docx_tables=0, pdf_tables=0):
    if fmt == "docx":
        return docx_tables > 0
    if fmt == "pdf":
        return pdf_tables > 0
    return bool(MD_TBL_RE.search(text) or HTML_TBL_RE.search(text) or LATEX_TBL_RE.search(text))

SYS_KEYWORDS = [
    ("web/e-commerce", [r'e-?commerce', r'marketplace', r'shop', r'store', r'cart', r'checkout', r'order']),
    ("management system", [r'management system', r'admin', r'inventory', r'attendance', r'pharmacy', r'cinema', r'course registration']),
    ("reservation/booking", [r'reserv', r'book', r'appoint', r'schedul', r'airline', r'flight', r'hotel']),
    ("finance/banking", [r'bank', r'financ', r'payment', r'loan', r'wallet', r'transaction', r'insurance', r'jandhan']),
    ("health/medical", [r'health', r'medical', r'patient', r'clinic', r'pharma', r'diagnos', r'insulin']),
    ("education", [r'education', r'course', r'student', r'exam', r'learning', r'lms', r'universit']),
    ("logistics/transport", [r'logistic', r'delivery', r'transport', r'shipping', r'track', r'fleet', r'gps']),
    ("IoT/embedded", [r'iot', r'embed', r'sensor', r'firmware', r'microcontrol', r'avb', r'bms', r'battery']),
    ("AI/ML", [r'machine learning', r'\bai\b', r'ml\b', r'recommend', r'nlp', r'classif', r'analytics', r'predict']),
    ("communication/network", [r'network', r'protocol', r'communication', r'wireless', r'satellite', r'voip', r'chat']),
    ("game/entertainment", [r'game', r'gaming', r'fps', r'multiplayer', r'entertain']),
    ("developer tool", [r'compiler', r'formatter', r'parser', r'pipeline', r'ci/cd', r'validator', r'workflow engine']),
    ("security/contract", [r'contract', r'smart contract', r'authentication', r'authorization', r'security', r'audit']),
    ("agriculture/environment", [r'farm', r'crop', r'soil', r'environment', r'climate', r'water', r'weather']),
    ("document/utility", [r'template', r'srs template', r'generator', r'documentation']),
]

def detect_system_type(name, text):
    blob = (name + " " + text[:4000]).lower()
    for label, pats in SYS_KEYWORDS:
        for p in pats:
            if re.search(p, blob):
                return label
    return "other/unspecified"

# template vs filled-in heuristic
TEMPLATE_HINTS = [r'this template', r'placeholder', r'\[insert', r'<insert',
                  r'<\.\.\.>', r'\[describe', r'\byour .+ here\b', r'lorem ipsum',
                  r'\bTBD\b', r'to be determined', r'xxx', r'\$\{']
def classify_role(name, text, shall, req_ids, size):
    low = text.lower()
    template_score = sum(1 for p in TEMPLATE_HINTS if re.search(p, low))
    is_std = bool(re.search(r'ieee.*(830|29148)|std 830|srs.*standard', low)) and size < 600000 and shall > 5 and req_ids == 0
    if 'standard' in name.lower() or 'ieee-830' in name.lower() or 'ieee---830' in name.lower():
        return "reference/standard"
    if template_score >= 2 or (shall <= 3 and req_ids == 0 and size < 8000):
        return "template/stub"
    if 'template' in name.lower() and shall <= 8:
        return "template"
    if shall >= 5 or req_ids >= 3:
        return "filled-in SRS"
    return "other/partial"

def analyze_file(path):
    ext = path.suffix.lower()
    name = path.name
    fmt = {".pdf":"PDF", ".docx":"DOCX", ".md":"Markdown", ".tex":"LaTeX",
           ".txt":"Text", ".html":"HTML", ".lyx":"LyX", ".rtf":"RTF"}.get(ext, ext.lstrip("."))
    docx_tables = 0; pdf_tables = 0
    if ext in EXTS_PDF:
        text = extract_pdf(path)
        pdf_tables = pdf_table_count(path)
    elif ext in EXTS_DOCX:
        text, docx_tables = extract_docx(path)
    else:
        text = read_text_file(path)
        text = strip_rtf(text)
    size = path.stat().st_size
    shall = len(SHALL_RE.findall(text))
    jp_req = len(JP_REQ_RE.findall(text))
    num_c = len(NUM_UNIT_RE.findall(text)) + len(NUM_CMP_RE.findall(text)) + len(NUM_RANGE_RE.findall(text))
    req_ids = len(set(REQ_ID_RE.findall(text)))
    has_table = detect_table(text, fmt, docx_tables, pdf_tables)
    sys_type = detect_system_type(name, text)
    role = classify_role(name, text, shall, req_ids, size)
    # Japanese SRS use こと/できる instead of "shall" — recognize as filled-in
    # (only Japanese files in collection are the 4 salab SRS samples)
    if role in ("template/stub", "other/partial") and jp_req >= 2:
        role = "filled-in SRS (JP)"
    # Numerically rich SRS (few "shall" but many constraints) — likely filled-in
    if role in ("template/stub", "other/partial") and num_c >= 15:
        role = "filled-in SRS"
    rel = path.relative_to(ROOT.parent)
    return {
        "path": str(rel), "file": name, "format": fmt, "size_bytes": size,
        "shall_count": shall, "num_constraint_hits": num_c,
        "unique_req_ids": req_ids, "has_table": has_table,
        "system_type": sys_type, "role": role,
    }

def main():
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.name in ("CATALOG.md", "ANALYSIS_REPORT.md", "analysis.csv"):
            continue
        ext = path.suffix.lower()
        if ext in EXTS_TEXT or ext in EXTS_PDF or ext in EXTS_DOCX:
            try:
                rows.append(analyze_file(path))
            except Exception as e:
                print(f"ERR {path}: {e}", file=sys.stderr)
    # write CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # aggregate
    n = len(rows)
    by_fmt = {}
    for r in rows:
        by_fmt[r["format"]] = by_fmt.get(r["format"], 0) + 1
    n_table = sum(1 for r in rows if r["has_table"])
    n_num = sum(1 for r in rows if r["num_constraint_hits"] >= 3)
    n_shall = sum(1 for r in rows if r["shall_count"] >= 5)
    n_reqid = sum(1 for r in rows if r["unique_req_ids"] >= 3)
    by_role = {}
    for r in rows:
        by_role[r["role"]] = by_role.get(r["role"], 0) + 1
    by_sys = {}
    for r in rows:
        by_sys[r["system_type"]] = by_sys.get(r["system_type"], 0) + 1
    filled = [r for r in rows if r["role"] == "filled-in SRS"]
    # write markdown report
    lines = []
    lines.append("# IEEE 830 SRS Collection — Analysis Report\n")
    lines.append(f"**Generated by** `tools/srs_ieee830_analyze.py`  ")
    lines.append(f"**Location** `data/gjb_438c/srs_collection/ieee830/`  ")
    lines.append(f"**Total files analyzed:** {n}\n")
    lines.append("## Aggregate Statistics\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total files | {n} |")
    lines.append(f"| Files with 'shall' statements (>=5) | {n_shall} |")
    lines.append(f"| Files with tables | {n_table} |")
    lines.append(f"| Files with numerical constraints (>=3 hits) | {n_num} |")
    lines.append(f"| Files with requirement IDs (>=3 unique) | {n_reqid} |")
    lines.append("")
    lines.append("### Format Distribution\n")
    lines.append("| Format | Count |")
    lines.append("|--------|-------|")
    for k in sorted(by_fmt, key=lambda x: -by_fmt[x]):
        lines.append(f"| {k} | {by_fmt[k]} |")
    lines.append("")
    lines.append("### Role Distribution\n")
    lines.append("| Role | Count |")
    lines.append("|--------|-------|")
    for k in sorted(by_role, key=lambda x: -by_role[x]):
        lines.append(f"| {k} | {by_role[k]} |")
    lines.append("")
    lines.append("### System Type Distribution (all files)\n")
    lines.append("| System Type | Count |")
    lines.append("|--------|-------|")
    for k in sorted(by_sys, key=lambda x: -by_sys[x]):
        lines.append(f"| {k} | {by_sys[k]} |")
    lines.append("")
    lines.append("## Filled-in SRS Documents (Category A)\n")
    lines.append("| File | Format | Size | shall | num-constraints | req-IDs | table | system type |")
    lines.append("|------|--------|------|-------|-----------------|---------|-------|-------------|")
    for r in sorted(filled, key=lambda x: -x["shall_count"]):
        sz = f'{r["size_bytes"]/1024:.0f}KB' if r["size_bytes"] < 1048576 else f'{r["size_bytes"]/1048576:.1f}MB'
        lines.append(f'| {r["file"]} | {r["format"]} | {sz} | {r["shall_count"]} | {r["num_constraint_hits"]} | {r["unique_req_ids"]} | {"yes" if r["has_table"] else "no"} | {r["system_type"]} |')
    lines.append("")
    lines.append("## All Files (full detail)\n")
    lines.append("| File | Format | Size | shall | num-const | req-IDs | table | role | system type |")
    lines.append("|------|--------|------|-------|-----------|---------|-------|------|-------------|")
    for r in sorted(rows, key=lambda x: (x["role"], -x["shall_count"])):
        sz = f'{r["size_bytes"]/1024:.0f}KB' if r["size_bytes"] < 1048576 else f'{r["size_bytes"]/1048576:.1f}MB'
        lines.append(f'| {r["file"]} | {r["format"]} | {sz} | {r["shall_count"]} | {r["num_constraint_hits"]} | {r["unique_req_ids"]} | {"yes" if r["has_table"] else "no"} | {r["role"]} | {r["system_type"]} |')
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    # console summary
    print(f"Analyzed {n} files")
    print(f"  with shall (>=5): {n_shall}")
    print(f"  with tables: {n_table}")
    print(f"  with num-constraints (>=3): {n_num}")
    print(f"  with req-IDs (>=3): {n_reqid}")
    print("Format dist:", by_fmt)
    print("Role dist:", by_role)
    print("Filled-in SRS:", len(filled))
    print("System types:", dict(sorted(by_sys.items(), key=lambda x:-x[1])))
    print(f"Report -> {OUT_MD}")
    print(f"CSV    -> {OUT_CSV}")

if __name__ == "__main__":
    main()
