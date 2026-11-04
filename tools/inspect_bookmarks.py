"""Inspect bookmark definitions in the merged report."""
from __future__ import annotations

import re

from lxml import etree
import docx

DOC = (r"C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344"
       r"\msg\file\2026-11\葛宣成 合稿.docx")


def main() -> None:
    doc = docx.Document(DOC)
    for i, p in enumerate(doc.paragraphs):
        xml = etree.tostring(p._element).decode()
        marks = re.findall(r'bookmarkStart[^>]*w:name="([^"]+)"', xml)
        if marks:
            print(f"[{i}] bookmarks: {marks} | {p.text.strip()[:50]}")


if __name__ == "__main__":
    main()
