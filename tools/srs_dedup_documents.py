#!/usr/bin/env python3
"""基于内容指纹对 processed_documents 目录中的文档去重。

指纹 = (md_chars, section_count, title.strip()[:30])
对每组重复文档，保留约束最多的版本，其余在 _index.json 中标记
is_duplicate=true / duplicate_of=<keeper>。不删除任何文件。

用法:
    python3 tools/srs_dedup_documents.py
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime

# ── 路径 ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(BASE_DIR, "data", "gjb_438c", "processed_documents")
INDEX_PATH = os.path.join(DOC_DIR, "_index.json")
SUMMARY_PATH = os.path.join(DOC_DIR, "_summary.json")
REPORT_PATH = os.path.join(DOC_DIR, "_dedup_report.json")


# ── 文件查找（处理 macOS 长文件名被截断 + 文件名 Unicode 归一化） ─────────
def build_stem_index(doc_dir: str) -> dict[str, str]:
    """返回 {文件名(无后缀): 完整路径} 的映射 (基于 listdir 真实文件名)。"""
    stem_map: dict[str, str] = {}
    for fn in os.listdir(doc_dir):
        if fn.endswith(".json") and not fn.startswith("_"):
            stem_map[fn[:-5]] = os.path.join(doc_dir, fn)
    return stem_map


def find_file(doc_name: str, doc_dir: str, stem_map: dict[str, str]) -> str | None:
    """按 doc_name 定位 JSON 文件。

    优先用 os.path.exists (依赖 FS 大小写/Unicode 归一化, 能匹配 listdir
    字符串比较漏掉的文件, 如 'srs.json'); 仅当精确路径不存在时, 才回退到
    “文件名 stem 是 doc_name 的前缀”匹配 (仅此方向, 处理被截断的长文件名,
    同时避免短名 'srs' 误匹配到 'srs-template-bare')。
    """
    primary = os.path.join(doc_dir, doc_name + ".json")
    if os.path.exists(primary):
        return primary
    best_stem = None
    for stem, path in stem_map.items():
        if doc_name.startswith(stem):
            if best_stem is None or len(stem) > len(best_stem):
                best_stem = stem
    return stem_map[best_stem] if best_stem else None


# ── 读取文档关键字段 ─────────────────────────────────────────────────────
def read_doc_fields(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {
        "doc_name": data.get("doc_name"),
        "md_chars": data.get("md_chars", 0) or 0,
        "section_count": data.get("section_count", 0) or 0,
        "title": (data.get("title") or "").strip(),
        "table_count": data.get("table_count", 0) or 0,
        "image_count": data.get("image_count", 0) or 0,
        "constraint_count": data.get("constraint_count", 0) or 0,
        "llm_constraint_count": data.get("llm_constraint_count", 0) or 0,
    }


def content_fingerprint(f: dict) -> tuple:
    """指纹 = (md_chars, section_count, title前30字符)。"""
    return (f["md_chars"], f["section_count"], f["title"][:30])


def keeper_sort_key(f: dict) -> tuple:
    """排序键 (升序, 排序后取 [0] 即为 keeper)。

    优先级: 约束总数 > llm约束 > 普通约束 > 表格数 > 图片数
            > 非括号名 > 短名 > 字母序
    """
    total_constraints = f["constraint_count"] + f["llm_constraint_count"]
    name = f["doc_name"] or ""
    starts_with_bracket = 1 if name.startswith("[") else 0
    return (
        -total_constraints,
        -f["llm_constraint_count"],
        -f["constraint_count"],
        -f["table_count"],
        -f["image_count"],
        starts_with_bracket,
        len(name),
        name,
    )


# ── 主流程 ───────────────────────────────────────────────────────────────
def main() -> None:
    with open(INDEX_PATH, "r", encoding="utf-8") as fh:
        index = json.load(fh)
    total_before = len(index)

    stem_map = build_stem_index(DOC_DIR)

    # 1. 读取每个文档字段并计算指纹
    fields_by_name: dict[str, dict] = {}
    missing: list[str] = []
    for entry in index:
        name = entry["doc_name"]
        path = find_file(name, DOC_DIR, stem_map)
        if path is None:
            missing.append(name)
            continue
        fields_by_name[name] = read_doc_fields(path)

    # 2. 按指纹分组
    groups: dict[tuple, list[str]] = defaultdict(list)
    for name, f in fields_by_name.items():
        groups[content_fingerprint(f)].append(name)

    # 3. 找出重复组 (>1 个成员)
    duplicate_groups_raw = [
        members for members in groups.values() if len(members) > 1
    ]

    # 4. 每组挑选 keeper
    duplicate_groups: list[dict] = []
    removed_set: set[str] = set()
    duplicate_of: dict[str, str] = {}

    for members in duplicate_groups_raw:
        sorted_members = sorted(members, key=lambda n: keeper_sort_key(fields_by_name[n]))
        keeper = sorted_members[0]
        removed = sorted_members[1:]
        for r in removed:
            removed_set.add(r)
            duplicate_of[r] = keeper
        duplicate_groups.append(
            {
                "kept": keeper,
                "removed": removed,
                "fingerprint": {
                    "md_chars": fields_by_name[keeper]["md_chars"],
                    "section_count": fields_by_name[keeper]["section_count"],
                    "title_prefix": fields_by_name[keeper]["title"][:30],
                },
                "reason": "same content fingerprint",
            }
        )

    # 按 keeper 名排序，便于阅读
    duplicate_groups.sort(key=lambda g: g["kept"])

    total_after = total_before - len(removed_set)

    # 5. 写 _dedup_report.json
    report = {
        "total_before": total_before,
        "total_after": total_after,
        "duplicates_removed": len(removed_set),
        "duplicate_group_count": len(duplicate_groups),
        "missing_files": missing,
        "duplicate_groups": duplicate_groups,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 写入去重报告: {REPORT_PATH}")

    # 6. 更新 _index.json: 给重复文档加 is_duplicate / duplicate_of
    for entry in index:
        name = entry["doc_name"]
        if name in removed_set:
            entry["is_duplicate"] = True
            entry["duplicate_of"] = duplicate_of[name]
        else:
            entry["is_duplicate"] = False
            entry.pop("duplicate_of", None)
    with open(INDEX_PATH, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 更新索引 (标记重复): {INDEX_PATH}")

    # 7. 更新 _summary.json (基于非重复文档重新统计)
    with open(SUMMARY_PATH, "r", encoding="utf-8") as fh:
        summary = json.load(fh)
    active = [e for e in index if not e.get("is_duplicate")]
    summary["total_docs"] = len(active)
    summary["gjb_docs"] = sum(1 for e in active if e.get("is_gjb"))
    summary["general_docs"] = sum(1 for e in active if not e.get("is_gjb"))
    summary["total_sections"] = sum(e.get("sections", 0) for e in active)
    summary["total_constraints"] = sum(e.get("constraints", 0) for e in active)
    summary["total_llm_constraints"] = sum(e.get("llm_constraints", 0) for e in active)
    summary["total_tables"] = sum(e.get("tables", 0) for e in active)
    summary["total_images"] = sum(e.get("images", 0) for e in active)
    summary["total_image_text_pairs"] = sum(e.get("image_text_pairs", 0) for e in active)

    by_source: dict[str, int] = defaultdict(int)
    by_system_type: dict[str, int] = defaultdict(int)
    by_language: dict[str, int] = defaultdict(int)
    for e in active:
        by_source[e.get("source", "unknown")] += 1
        by_system_type[e.get("system_type", "unknown")] += 1
        by_language[e.get("language", "unknown")] += 1
    summary["by_source"] = dict(by_source)
    summary["by_system_type"] = dict(by_system_type)
    summary["by_language"] = dict(by_language)
    summary["dedup_info"] = {
        "duplicates_removed": len(removed_set),
        "duplicate_group_count": len(duplicate_groups),
        "total_before_dedup": total_before,
    }
    summary["analysis_date"] = datetime.now().isoformat(timespec="seconds")
    with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 更新统计: {SUMMARY_PATH}")

    # ── 控制台汇总 ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("去重统计")
    print("=" * 60)
    print(f"去重前文档数 : {total_before}")
    print(f"去重后文档数 : {total_after}")
    print(f"移除重复文档 : {len(removed_set)}")
    print(f"重复组数量   : {len(duplicate_groups)}")
    if missing:
        print(f"缺失文件     : {len(missing)}  {missing}")
    print("\n重复组明细 (kept <- removed):")
    for g in duplicate_groups:
        print(f"  • {g['kept']}")
        for r in g["removed"]:
            print(f"      └─ {r}")


if __name__ == "__main__":
    main()
