"""Compare scenario-1 implementation doc vs scenario-5 doc structures."""
from __future__ import annotations

import sys
from pathlib import Path

import docx

BASE = Path("docs/srs_project")
S1 = BASE / "软件需求规格说明辅助生成场景微调数据应用设计与落地实施文档.docx"
S5 = BASE / "场景5-科研生产现场智能监管微调数据应用设计与落地实施文档.docx"


def paragraphs(path: Path) -> list[str]:
    doc = docx.Document(str(path))
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "s5"
    if which == "s1":
        paras = paragraphs(S1)
    else:
        paras = paragraphs(S5)
    print(f"{which}: {len(paras)} paragraphs")
    # print outline: short lines that look like headings or numbered items
    for i, p in enumerate(paras):
        looks_heading = (
            p.startswith(("一", "二", "三", "四", "五", "六", "七", "八"))
            or p.startswith(("1.", "2.", "3.", "4.", "5.", "6."))
            or (len(p) < 45 and any(
                p.startswith(f"{n}") is False and f"{n}）" in p[:6]
                for n in "12345"))
            or (len(p) < 60 and p.endswith(("技术", "校验", "识别", "需求",
                                            "设计", "内容", "方案")))
        )
        if looks_heading:
            print(f"[{i}] {p}")


if __name__ == "__main__":
    main()
