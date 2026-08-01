#!/usr/bin/env python3
"""
SRS MinerU Batch Parser (v2 - single process, models loaded once).
Phase 1 of Data Governance Pipeline.

Usage:
    ~/mineru-env/bin/python tools/srs_mineru_parse.py [--start N] [--max N]

Parses all 62 SRS PDFs using MinerU pipeline backend in a single process.
Models are loaded once, then reused for all PDFs.
"""

import os
import sys
import json
import time
import traceback
from pathlib import Path
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = REPO_ROOT / "data" / "srs_requirements" / "req"
OUTPUT_DIR = REPO_ROOT / "data" / "srs_requirements" / "mineru_parsed"

os.environ.setdefault("MINERU_MODEL_SOURCE", "huggingface")


def get_pdf_files(start=0, max_n=None):
    """Get all PDF files sorted by size (smallest first)."""
    pdfs = sorted(PDF_DIR.glob("*.pdf"), key=lambda f: f.stat().st_size)
    if start:
        pdfs = pdfs[start:]
    if max_n:
        pdfs = pdfs[:max_n]
    return pdfs


def count_md_features(md_path: Path) -> dict:
    """Count features in a markdown file."""
    content = md_path.read_text(encoding="utf-8", errors="replace")
    return {
        "md_lines": content.count("\n"),
        "num_headers": content.count("\n#"),
        "num_tables": content.count("<table>"),
        "num_leq_geq": content.count("≤") + content.count("≥"),
        "num_latex_inline": content.count("$"),
        "num_images_ref": content.count("!["),
    }


def parse_all_pdfs(pdfs: list, output_base: Path) -> list:
    """Parse all PDFs using MinerU Python API in a single process."""
    
    # Import MinerU (loads models lazily on first use)
    print("Loading MinerU pipeline models (first time only)...")
    from mineru.cli.common import do_parse
    print("Models ready.\n")
    
    all_results = []
    
    for i, pdf_path in enumerate(pdfs, 1):
        doc_name = pdf_path.stem
        doc_output = output_base / doc_name
        
        result = {
            "file": pdf_path.name,
            "doc_name": doc_name,
            "size_kb": round(pdf_path.stat().st_size / 1024, 1),
            "status": "pending",
            "output_dir": str(doc_output),
            "error": None,
            "duration_sec": 0,
        }
        
        # Skip if already parsed
        md_candidates = list(doc_output.rglob("*.md")) if doc_output.exists() else []
        if md_candidates:
            result["status"] = "skipped"
            result["md_file"] = str(md_candidates[0])
            result.update(count_md_features(md_candidates[0]))
            all_results.append(result)
            print(f"[{i}/{len(pdfs)}] SKIP {pdf_path.name}")
            continue
        
        print(f"[{i}/{len(pdfs)}] Parsing {pdf_path.name} ({result['size_kb']}KB)...")
        start_time = time.time()
        
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            # Use a safe filename for output
            safe_name = pdf_path.name.replace(" ", "_").replace("-", "_")
            
            do_parse(
                output_dir=str(output_base),
                pdf_file_names=[pdf_path.name],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=["en"],
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
            
            result["duration_sec"] = round(time.time() - start_time, 1)
            
            # Find output
            md_candidates = list(doc_output.rglob("*.md"))
            json_candidates = list(doc_output.rglob("*_middle.json"))
            img_candidates = list(doc_output.rglob("images/*.jpg")) + list(doc_output.rglob("images/*.png"))
            
            if md_candidates:
                result["status"] = "success"
                result["md_file"] = str(md_candidates[0])
                result["json_file"] = str(json_candidates[0]) if json_candidates else None
                result["num_images"] = len(img_candidates)
                result.update(count_md_features(md_candidates[0]))
                print(f"  OK  ({result['duration_sec']}s) "
                      f"{result.get('num_headers',0)}h "
                      f"{result.get('num_tables',0)}t "
                      f"{result.get('num_leq_geq',0)}≤≥ "
                      f"{result.get('num_images',0)}img")
            else:
                result["status"] = "failed"
                result["error"] = "No markdown output found"
                print(f"  FAIL: no markdown output")
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:500]
            result["duration_sec"] = round(time.time() - start_time, 1)
            print(f"  ERROR: {str(e)[:200]}")
            traceback.print_exc()
        
        all_results.append(result)
        
        # Save intermediate results
        summary = {
            "parse_date": datetime.now().isoformat(),
            "total_pdfs": len(pdfs),
            "processed": len(all_results),
            "success": sum(1 for r in all_results if r["status"] == "success"),
            "skipped": sum(1 for r in all_results if r["status"] == "skipped"),
            "failed": sum(1 for r in all_results if r["status"] in ("failed", "error")),
            "results": all_results,
        }
        (output_base / "_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    return all_results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch parse SRS PDFs with MinerU")
    parser.add_argument("--start", type=int, default=0, help="Skip first N PDFs")
    parser.add_argument("--max", type=int, default=None, help="Max PDFs to process")
    args = parser.parse_args()
    
    output_base = OUTPUT_DIR
    output_base.mkdir(parents=True, exist_ok=True)
    
    pdfs = get_pdf_files(args.start, args.max)
    print(f"Found {len(pdfs)} PDFs to parse")
    print(f"Output: {output_base}")
    print(f"Python: {sys.executable}")
    print("=" * 70)
    
    start_total = time.time()
    all_results = parse_all_pdfs(pdfs, output_base)
    total_time = time.time() - start_total
    
    # Final summary
    success = sum(1 for r in all_results if r["status"] == "success")
    skipped = sum(1 for r in all_results if r["status"] == "skipped")
    failed = sum(1 for r in all_results if r["status"] in ("failed", "error"))
    
    total_headers = sum(r.get("num_headers", 0) for r in all_results)
    total_tables = sum(r.get("num_tables", 0) for r in all_results)
    total_leq_geq = sum(r.get("num_leq_geq", 0) for r in all_results)
    total_images = sum(r.get("num_images", 0) for r in all_results)
    total_md_lines = sum(r.get("md_lines", 0) for r in all_results)
    
    print("\n" + "=" * 70)
    print("BATCH PARSE COMPLETE")
    print(f"  Total: {len(pdfs)} PDFs")
    print(f"  Success: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  Avg per PDF: {total_time/max(len(pdfs),1):.1f}s")
    print(f"  Total MD lines: {total_md_lines}")
    print(f"  Total headers: {total_headers}")
    print(f"  Total tables: {total_tables}")
    print(f"  Total ≤≥ symbols: {total_leq_geq}")
    print(f"  Total images: {total_images}")
    
    if failed > 0:
        print("\nFailed files:")
        for r in all_results:
            if r["status"] in ("failed", "error"):
                print(f"  - {r['file']}: {r.get('error', 'unknown')[:100]}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
