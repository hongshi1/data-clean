"""Clean up the repository: remove junk files, organize structure.

Safe cleanup: only removes files that are clearly junk (temp scripts,
debug screenshots, unzipped docx internals, visio temp dirs).
Does NOT touch: algorithms/, tools/, tests/, docs/, knowledge/, config/,
data/, deploy/, models/, server/, frontend/, srs_verify_package/.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files to delete (temp scripts, debug screenshots, unzipped internals)
JUNK_FILES = [
    "addshots.py",
    "check.py",
    "editdoc.py",
    "editdoc2.py",
    "inspect_docs.py",
    "shapes.py",
    "xinspect.py",
    "xoutline.py",
    "outline.txt",
    "modified.docx",
    "content-enhanced.png",
    "dataset-check-final.png",
    "img-vertical-layout.png",
    "mindmap-final.png",
    "platform-open-verify.png",
    "slide1_check.png",
    "slide2_check.png",
    "slide3_check.png",
    "workbench-graph-ok.png",
    "workbench-idquery-pathhighlight.png",
    *[f"v{v}_slide{s}.png" for v in range(2, 7) for s in (1, 2, 3)],
]

# Directories to remove entirely (unzipped docx, visio temp)
JUNK_DIRS = [
    "docx_unzip",
    "outzip",
    "temp",
    "visio_Microsoft_Visio___1",
    "visio_Microsoft_Visio___2",
    "visio_oleObject1",
    "visio_oleObject2",
]


def main() -> None:
    print("=== 仓库清理 ===")
    print()

    # Delete junk files
    deleted_files = 0
    freed_kb = 0
    for name in JUNK_FILES:
        path = ROOT / name
        if path.is_file():
            size = path.stat().st_size
            path.unlink()
            deleted_files += 1
            freed_kb += size // 1024
            print(f"  删除文件: {name} ({size // 1024}KB)")

    # Delete junk directories
    deleted_dirs = 0
    for name in JUNK_DIRS:
        path = ROOT / name
        if path.is_dir():
            count = sum(1 for _ in path.rglob("*") if _.is_file())
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            shutil.rmtree(path)
            deleted_dirs += 1
            freed_kb += size // 1024
            print(f"  删除目录: {name}/ ({count}文件, {size // 1024}KB)")

    print()
    print(f"删除: {deleted_files}个文件 + {deleted_dirs}个目录")
    print(f"释放: {freed_kb}KB ({freed_kb / 1024:.1f}MB)")

    # Move misplaced root-level files to proper locations
    print()
    print("=== 归类散落文件 ===")
    moves = [
        ("南开大学模板-3.pptx", "docs/srs_project/ppt_templates/"),
        ("南开大学模板-4.pptx", "docs/srs_project/ppt_templates/"),
        ("知识融合候选清单.md", "knowledge/"),
    ]
    for src, dst_dir in moves:
        src_path = ROOT / src
        dst_path = ROOT / dst_dir
        if src_path.is_file():
            dst_path.mkdir(parents=True, exist_ok=True)
            dst_file = dst_path / src_path.name
            if not dst_file.exists():
                shutil.move(str(src_path), str(dst_file))
                print(f"  移动: {src} → {dst_dir}")
            else:
                print(f"  已存在: {dst_dir}/{src}")

    print()
    print("=== 清理后状态 ===")
    root_files = [f for f in ROOT.iterdir() if f.is_file()]
    root_dirs = [d for d in ROOT.iterdir() if d.is_dir()]
    print(f"根目录文件: {len(root_files)}个")
    print(f"根目录目录: {len(root_dirs)}个")
    for f in sorted(root_files, key=lambda x: x.name):
        print(f"  {f.name}")
    print()
    for d in sorted(root_dirs, key=lambda x: x.name):
        print(f"  {d.name}/")


if __name__ == "__main__":
    main()
