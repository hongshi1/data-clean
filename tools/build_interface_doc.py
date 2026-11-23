"""Build 一致性校验服务接口说明.docx from the markdown spec."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

MD = Path(r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022"
          r"_a344\msg\file\2026-11\一致性校验服务接口说明.md")
OUT = MD.with_name("一致性校验服务接口说明.docx")

doc = Document()
# 全局样式: 宋体小四正文
style = doc.styles["Normal"]
style.font.name = "宋体"
style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
style.font.size = Pt(12)


def add_heading(text: str, level: int) -> None:
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = "黑体"
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "黑体")
        run.font.color.rgb = RGBColor(0, 0, 0)
        run.font.size = Pt(16 if level == 1 else 14)


def add_para(text: str) -> None:
    doc.add_paragraph(text)


def add_code(text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Consolas"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(9)


def add_table(rows: list[list[str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            run = cell.paragraphs[0].add_run(value)
            run.font.name = "宋体"
            run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
            run.font.size = Pt(10.5)
            if i == 0:
                run.bold = True


def main() -> None:
    lines = MD.read_text(encoding="utf-8").splitlines()
    i = 0
    para_buf: list[str] = []
    code_buf: list[str] = []
    table_buf: list[list[str]] = []
    in_code = False
    in_table = False

    def flush_para() -> None:
        if para_buf:
            add_para(" ".join(para_buf))
            para_buf.clear()

    def flush_code() -> None:
        if code_buf:
            add_code("\n".join(code_buf))
            code_buf.clear()

    def flush_table() -> None:
        if table_buf:
            add_table(table_buf)
            table_buf.clear()

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush_para()
            flush_table()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_para()
            in_table = True
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                table_buf.append(cells)
            i += 1
            continue
        if in_table:
            flush_table()
            in_table = False
        if stripped.startswith("#"):
            flush_para()
            level = stripped.count("#")
            add_heading(stripped.lstrip("#").strip(), min(level, 3))
        elif stripped.startswith("> "):
            p = doc.add_paragraph()
            run = p.add_run(stripped[2:])
            run.font.name = "宋体"
            run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
            run.font.size = Pt(10.5)
            run.italic = True
        elif stripped.startswith("- ") or stripped.startswith(("1. ", "2. ", "3. ", "4. ", "5. ")):
            flush_para()
            doc.add_paragraph(stripped[2:] if stripped.startswith("- ") else stripped[3:],
                              style="List Bullet" if stripped.startswith("- ") else "List Number")
        elif stripped == "":
            flush_para()
        else:
            para_buf.append(stripped)
        i += 1
    flush_para()
    flush_code()
    flush_table()

    doc.save(str(OUT))
    check = Document(str(OUT))
    print(f"output={OUT}")
    print(f"paragraphs={len(check.paragraphs)} tables={len(check.tables)}")


if __name__ == "__main__":
    main()
