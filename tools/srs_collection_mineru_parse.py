#!/usr/bin/env python3
"""
Batch-parse every PDF under data/gjb_438c/srs_collection/ with MinerU.

- MinerU models are loaded ONCE and reused for all PDFs (single process).
- Output goes to <pdf_parent_dir>/mineru_parsed/<pdf_name>/auto/<pdf_name>.md
- Already-parsed PDFs are skipped (resumable).
- Language is auto-detected: CJK chars in filename -> 'ch', else 'en'.
- Results are logged (and incrementally saved) to:
    data/gjb_438c/srs_collection/mineru_parse_log.json

Usage:
    ~/mineru-env/bin/python -u tools/srs_collection_mineru_parse.py [--max N] [--start N] [--dry-run]

Run with MINERU_MODEL_SOURCE=huggingface for first-time model download.
"""

import os
import sys
import json
import time
import re
import traceback
from pathlib import Path
from datetime import datetime

os.environ.setdefault("MINERU_MODEL_SOURCE", "huggingface")

# ── Configuration ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTION_DIR = REPO_ROOT / "data" / "gjb_438c" / "srs_collection"
LOG_FILE = COLLECTION_DIR / "mineru_parse_log.json"

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff]")


def detect_lang(filename: str) -> str:
    """Chinese if CJK chars in filename, else English."""
    return "ch" if CJK_RE.search(filename) else "en"


def count_pages(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return 0


def find_pdfs(root: Path) -> list:
    """All real PDF files, excluding MinerU output dirs (named <name>.pdf) and
    run-log folders. MinerU names its output folder '<pdf>.pdf' which rglob would
    otherwise match as a directory."""
    out = []
    for p in sorted(root.rglob("*.pdf"), key=lambda p: p.stat().st_size):
        if not p.is_file():
            continue
        parts = {x.lower() for x in p.parts}
        if "mineru_parsed" in parts or "_run_logs" in parts:
            continue
        out.append(p)
    return out


def doc_output_dir(pdf_path: Path) -> Path:
    return pdf_path.parent / "mineru_parsed" / pdf_path.name


def is_parsed(pdf_path: Path) -> bool:
    out = doc_output_dir(pdf_path)
    return out.exists() and any(out.rglob("*.md"))


def count_md_features(md_path: Path) -> dict:
    try:
        content = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    return {
        "md_lines": content.count("\n"),
        "num_headers": content.count("\n#"),
        "num_tables": content.count("<table>"),
        "num_leq_geq": content.count("≤") + content.count("≥"),
        "num_images_ref": content.count("!["),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Batch parse srs_collection PDFs with MinerU")
    ap.add_argument("--max", type=int, default=None, help="Max PDFs to process")
    ap.add_argument("--start", type=int, default=0, help="Skip first N pending PDFs")
    ap.add_argument("--dry-run", action="store_true", help="Only list what would be done")
    args = ap.parse_args()

    COLLECTION_DIR.mkdir(parents=True, exist_ok=True)

    all_pdfs = find_pdfs(COLLECTION_DIR)
    print(f"Found {len(all_pdfs)} PDFs under {COLLECTION_DIR}")
    print(f"Python: {sys.executable}")
    print("=" * 70)

    # Resume: load existing log
    log = {
        "collection_dir": str(COLLECTION_DIR),
        "start": datetime.now().isoformat(),
        "results": {},
    }
    if LOG_FILE.exists():
        try:
            old = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            # Prune stale entries whose path is no longer a real PDF file
            # (e.g. leftover directory entries from a previous buggy run).
            log["results"] = {
                k: v for k, v in old.get("results", {}).items()
                if Path(k).is_file() and Path(k).suffix.lower() == ".pdf"
            }
            print(f"Resuming from existing log ({len(log['results'])} entries).")
        except Exception:
            pass

    # Partition into skipped vs todo
    todo = []
    skipped = 0
    for p in all_pdfs:
        key = str(p)
        prev = log["results"].get(key)
        if is_parsed(p):
            if not prev or prev.get("status") not in ("success", "skipped"):
                log["results"][key] = {
                    "file": p.name, "path": key,
                    "parent_dir": str(p.parent),
                    "size_kb": round(p.stat().st_size / 1024, 1),
                    "status": "skipped", "reason": "already parsed",
                    "output_dir": str(doc_output_dir(p)),
                }
            skipped += 1
        else:
            todo.append(p)

    print(f"Already parsed (skipped): {skipped}")
    print(f"To parse: {len(todo)}")

    if args.start:
        todo = todo[args.start:]
        print(f"After --start {args.start}: {len(todo)} to parse")
    if args.max:
        todo = todo[: args.max]
        print(f"After --max {args.max}: {len(todo)} to parse")

    if args.dry_run:
        print("\n--dry-run: pending PDFs:")
        for i, p in enumerate(todo, 1):
            print(f"  [{i}] {p.relative_to(COLLECTION_DIR)}  ({round(p.stat().st_size/1024,1)}KB, lang={detect_lang(p.name)})")
        return 0

    if not todo:
        print("Nothing to do. All PDFs already parsed.")
        _finalize(log, 0, 0.0)
        return 0

    # Silence MinerU's verbose loguru DEBUG/INFO output (keep WARNING+)
    try:
        from loguru import logger as _l
        _l.remove()
        _l.add(sys.stderr, level="WARNING")
    except Exception:
        pass

    print("\nLoading MinerU pipeline models (first time only)...", flush=True)
    from mineru.cli.common import do_parse
    print("Models ready.\n", flush=True)

    start_total = time.time()
    success = failed = 0

    for i, pdf_path in enumerate(todo, 1):
        key = str(pdf_path)
        out_base = pdf_path.parent / "mineru_parsed"
        out_base.mkdir(parents=True, exist_ok=True)
        lang = detect_lang(pdf_path.name)
        pages = count_pages(pdf_path)
        size_kb = round(pdf_path.stat().st_size / 1024, 1)

        rec = {
            "file": pdf_path.name,
            "path": key,
            "parent_dir": str(pdf_path.parent),
            "size_kb": size_kb,
            "pages": pages,
            "lang": lang,
            "output_dir": str(doc_output_dir(pdf_path)),
            "status": "pending",
            "error": None,
            "duration_sec": 0,
            "md_file": None,
        }

        print(f"[{i}/{len(todo)}] {pdf_path.name}  "
              f"({size_kb}KB, {pages}p, lang={lang})", flush=True)
        t0 = time.time()

        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            do_parse(
                output_dir=str(out_base),
                pdf_file_names=[pdf_path.name],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=[lang],
                backend="pipeline",
                parse_method="auto",
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                f_dump_md=True,
                f_dump_middle_json=True,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=False,
            )

            rec["duration_sec"] = round(time.time() - t0, 1)
            doc_out = doc_output_dir(pdf_path)
            mds = list(doc_out.rglob("*.md"))
            if mds:
                rec["status"] = "success"
                rec["md_file"] = str(mds[0])
                rec.update(count_md_features(mds[0]))
                success += 1
                print(f"  OK  ({rec['duration_sec']}s) "
                      f"h={rec.get('num_headers',0)} t={rec.get('num_tables',0)} "
                      f"≤≥={rec.get('num_leq_geq',0)}", flush=True)
            else:
                rec["status"] = "failed"
                rec["error"] = "no markdown output found"
                failed += 1
                print(f"  FAIL: no markdown output ({rec['duration_sec']}s)", flush=True)

        except Exception as e:
            rec["status"] = "error"
            rec["error"] = str(e)[:500]
            rec["duration_sec"] = round(time.time() - t0, 1)
            failed += 1
            print(f"  ERROR: {str(e)[:200]} ({rec['duration_sec']}s)", flush=True)
            traceback.print_exc()

        log["results"][key] = rec
        # Incremental save after every PDF (resumable + monitorable)
        log["processed"] = i
        log["total_todo"] = len(todo)
        log["success"] = success
        log["failed"] = failed
        log["skipped"] = skipped
        log["elapsed_sec"] = round(time.time() - start_total, 1)
        log["last_update"] = datetime.now().isoformat()
        try:
            LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    total = time.time() - start_total
    _finalize(log, success, total, failed=failed, skipped=skipped, total_todo=len(todo))

    print("\n" + "=" * 70)
    print("BATCH PARSE COMPLETE")
    print(f"  Processed: {len(todo)}  Success: {success}  Failed: {failed}  Skipped: {skipped}")
    print(f"  Time: {total:.0f}s ({total/60:.1f} min)  Avg: {total/max(len(todo),1):.1f}s/PDF")
    print(f"  Log: {LOG_FILE}")
    if failed:
        print("\nFailed files:")
        for p in todo:
            r = log["results"].get(str(p), {})
            if r.get("status") in ("failed", "error"):
                print(f"  - {r.get('file')}: {str(r.get('error'))[:120]}")
    return 0 if failed == 0 else 1


def _finalize(log, success, total, failed=0, skipped=0, total_todo=0):
    log["end"] = datetime.now().isoformat()
    log["total_duration_sec"] = round(total, 1)
    log["success"] = success
    log["failed"] = failed
    log["skipped"] = skipped
    log["total_todo"] = total_todo
    counts = {"success": 0, "failed": 0, "error": 0, "skipped": 0, "pending": 0}
    for v in log["results"].values():
        s = v.get("status")
        if s in counts:
            counts[s] += 1
    log["summary"] = counts
    try:
        LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
