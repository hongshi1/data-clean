"""Extract section outlines of both scenario implementation docs for comparison."""
from __future__ import annotations

import re
from pathlib import Path

import docx

BASE = Path("docs/srs_project")
DOCS = {
    "s1": BASE / "软件需求规格说明辅助生成场景微调数据应用设计与落地实施文档.docx",
    "s5": BASE / "场景5-科研生产现场智能监管微调数据应用设计与落地实施文档.docx",
}

HEADING = re.compile(
    r"^(\d+(\.\d+)*)\s*[\u4e00-\u9fff（(]")


def outline(paras: list[str]) -> list[tuple[int, str, int]]:
    out: list[tuple[int, str, int]] = []
    for i, p in enumerate(paras):
        m = HEADING.match(p)
        if m and len(p) < 45:
            depth = m.group(1).count(".") + 1
            out.append((i, p, depth))
        elif (len(p) < 40 and re.match(r"^\d+[\.、）)]", p)
              and any(k in p for k in (
                  "构建", "赋能", "校验", "评估", "需求", "设计",
                  "经验", "背景", "目标", "分析"))):
            out.append((i, p, 2))
    return out


def main() -> None:
    for key in ("s1", "s5"):
        doc = docx.Document(str(DOCS[key]))
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        print(f"===== {key} ({len(paras)} paragraphs) =====")
        for i, p, depth in outline(paras):
            indent = "  " * (depth - 1)
            print(f"{indent}[{i}] {p}")
        print()


if __name__ == "__main__":
    main()
