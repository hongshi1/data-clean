#!/usr/bin/env python3
"""
章节编号解析 + SectionTemplate 对齐 验证脚本
================================================
验证 v3 方案中 "章节解析带编号 → 对齐GJB模板" 的可行性。

输入: 3 份 Gold Standard GJB SRS 的 MinerU markdown
输出: 对齐效果统计 + 验证报告

用法: python3 tools/srs_kb_section_align_verify.py
"""
import re
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── 路径配置 ──────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
MINERU_SRS = BASE / "data/gjb_438c/mineru_srs"
OUTPUT_DIR = BASE / "data/gjb_438c/section_align_verify"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. 章节编号解析 (增强版, 复用 compliance_scan 逻辑) ──────

# 匹配 markdown ATX 标题: ## 3.2.1 标题 / ### 3.3.X c) 数据元素
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
# 从标题文字提取编号: "3.2.1 信号采集" → "3.2.1"; "3.3.X c) 数据元素" → "3.3.X"
NUMBER_RE = re.compile(r'^(\d+(?:\.\w+)*)\.?\s*(.*)')
# 去除标题中的尾部注释/括号: "验收、交付和包装需求（修改有关内容）" → "验收、交付和包装需求"
TRAILING_PAREN_RE = re.compile(r'[（(].*?[)）]\s*$')


@dataclass
class Section:
    """文档章节实例"""
    id: str
    number: str           # 章节编号, 如 "3.2.1"; 无编号则为 ""
    title: str            # 章节标题
    level: int            # 层级 (# 数)
    line: int             # 行号
    doc: str              # 文档ID
    raw: str = ""         # 原始标题文字


def extract_sections(md_text: str, doc_id: str) -> list[Section]:
    """
    从 MinerU markdown 提取章节, 解析编号.
    改进点 vs 旧 extract_sections_from_md:
      1. 解析章节编号 (不再只数 # 号)
      2. sec_id 用编号而非数组下标
      3. 记录行号
    """
    sections = []
    for m in HEADING_RE.finditer(md_text):
        level = len(m.group(1))
        raw = m.group(2).strip()
        line = md_text[:m.start()].count('\n') + 1

        # 提取编号
        num_m = NUMBER_RE.match(raw)
        if num_m:
            number = num_m.group(1)
            title = num_m.group(2).strip().rstrip('.')
        else:
            number = ""
            title = raw.rstrip('.')

        # 去除尾部括号注释
        title_clean = TRAILING_PAREN_RE.sub('', title).strip()

        # 跳过封面/目录等无编号标题 (level=1 且无编号 且非数字开头)
        # 但保留有编号的标题
        sec_id = f"{doc_id}-SEC-{number}" if number else f"{doc_id}-SEC-L{line}"

        sections.append(Section(
            id=sec_id, number=number, title=title_clean,
            level=level, line=line, doc=doc_id, raw=raw
        ))
    return sections


def filter_content_sections(sections: list[Section]) -> list[Section]:
    """过滤掉封面/目录/更改记录等非正文章节, 只保留有编号的章节"""
    return [s for s in sections if s.number and re.match(r'^\d', s.number)]


# ── 2. SectionTemplate 构建 (GJB 附录J 章节树) ────────────────

@dataclass
class SectionTemplate:
    """GJB 标准章节模板"""
    number: str               # 模板编号, "3.2.X" 表示可变
    title: str                # 标准标题
    title_en: str = ""
    level: int = 1
    required: str = "must"    # must / conditional / optional
    parent: str = ""
    variants: list = field(default_factory=list)  # 已知的编号变体


def build_section_templates() -> list[SectionTemplate]:
    """
    构建 GJB 438C 附录J SRS 模板章节树.
    基于标准 OCR 文本 + 实际文档观察到的变体.
    
    已知变体:
      - 标准OCR: 3.7=保密性, 3.8=安全性, 3.10=其他质量特性, 3.11=计算机资源需求
      - DOCX模板/实际文档: 3.7=安全性, 3.8=保密性, 3.10=计算机资源需求, 3.11=软件质量因素
      - 部分文档: 3.17=验收交付包装(合并3.16+3.17)
    """
    templates = []

    # 第1章 范围
    templates.append(SectionTemplate("1", "范围", "Scope", 1, "must"))
    templates.append(SectionTemplate("1.1", "标识", "Identification", 2, "must", "1"))
    templates.append(SectionTemplate("1.2", "系统概述", "System overview", 2, "must", "1"))
    templates.append(SectionTemplate("1.3", "文档概述", "Document overview", 2, "must", "1"))

    # 第2章 引用文档
    templates.append(SectionTemplate("2", "引用文档", "Referenced documents", 1, "must"))

    # 第3章 需求 (核心)
    templates.append(SectionTemplate("3", "需求", "Requirements", 1, "must"))
    templates.append(SectionTemplate("3.1", "要求的状态和方式", "Required states and modes", 2, "conditional", "3"))
    templates.append(SectionTemplate("3.1.X", "状态定义", "State definition", 3, "conditional", "3.1"))

    templates.append(SectionTemplate("3.2", "CSCI能力需求", "CSCI capability requirements", 2, "must", "3",
                                      variants=["软件能力需求"]))  # 实际文档常用"软件能力需求"
    templates.append(SectionTemplate("3.2.X", "CSCI能力", "CSCI capability", 3, "must", "3.2"))

    templates.append(SectionTemplate("3.3", "CSCI外部接口需求", "CSCI external interface requirements", 2, "conditional", "3",
                                      variants=["软件外部接口需求"]))
    templates.append(SectionTemplate("3.3.1", "接口标识和接口图", "Interface identification and diagrams", 3, "must", "3.3"))
    templates.append(SectionTemplate("3.3.X", "接口唯一标识符", "Interface unique identifier", 3, "conditional", "3.3"))

    templates.append(SectionTemplate("3.4", "CSCI内部接口需求", "CSCI internal interface requirements", 2, "conditional", "3",
                                      variants=["软件内部接口需求"]))
    templates.append(SectionTemplate("3.4.X", "内部接口", "Internal interface", 3, "conditional", "3.4"))

    templates.append(SectionTemplate("3.5", "CSCI内部数据需求", "CSCI internal data requirements", 2, "conditional", "3",
                                      variants=["软件内部数据需求"]))
    templates.append(SectionTemplate("3.6", "适应性需求", "Adaptability requirements", 2, "conditional", "3"))

    # 3.7/3.8 安全性/保密性 (两种变体)
    templates.append(SectionTemplate("3.7", "保密性需求", "Security requirements", 2, "conditional", "3",
                                      variants=["安全性需求"]))  # 标准OCR: 保密性; DOCX模板: 安全性
    templates.append(SectionTemplate("3.8", "安全性需求", "Safety requirements", 2, "conditional", "3",
                                      variants=["保密性需求"]))  # 标准OCR: 安全性; DOCX模板: 保密性

    templates.append(SectionTemplate("3.9", "CSCI环境适应性需求", "CSCI environmental requirements", 2, "conditional", "3",
                                      variants=["软件环境需求", "环境适应性需求"]))

    # 3.10/3.11 两种变体
    templates.append(SectionTemplate("3.10", "其他质量特性", "Other quality characteristics", 2, "conditional", "3",
                                      variants=["计算机资源需求"]))  # 标准OCR: 其他质量特性; DOCX: 计算机资源需求
    templates.append(SectionTemplate("3.10.1", "计算机硬件需求", "Computer hardware requirements", 3, "conditional", "3.10"))
    templates.append(SectionTemplate("3.10.2", "计算机硬件资源使用需求", "Computer hardware resource utilization", 3, "conditional", "3.10"))
    templates.append(SectionTemplate("3.10.3", "计算机软件需求", "Computer software requirements", 3, "conditional", "3.10"))
    templates.append(SectionTemplate("3.10.4", "计算机通信需求", "Computer communications requirements", 3, "conditional", "3.10"))

    templates.append(SectionTemplate("3.11", "计算机资源需求", "Computer resource requirements", 2, "conditional", "3",
                                      variants=["软件质量因素"]))  # 标准OCR: 计算机资源需求; DOCX: 软件质量因素

    templates.append(SectionTemplate("3.12", "设计和实现约束", "Design and implementation constraints", 2, "conditional", "3"))
    templates.append(SectionTemplate("3.13", "人员相关需求", "Personnel-related requirements", 2, "conditional", "3",
                                      variants=["人员需求"]))
    templates.append(SectionTemplate("3.14", "训练相关需求", "Training-related requirements", 2, "conditional", "3",
                                      variants=["培训需求"]))
    templates.append(SectionTemplate("3.15", "软件保障需求", "Software support requirements", 2, "conditional", "3"))
    templates.append(SectionTemplate("3.16", "包装需求", "Packaging requirements", 2, "conditional", "3",
                                      variants=["其他需求"]))
    templates.append(SectionTemplate("3.17", "其他需求", "Other requirements", 2, "conditional", "3",
                                      variants=["验收、交付和包装需求", "验收交付和包装需求"]))
    templates.append(SectionTemplate("3.18", "需求的优先顺序和关键性", "Requirement priority and criticality", 2, "conditional", "3",
                                      variants=["需求的优先顺序和关键程度"]))

    # 第4-6章
    templates.append(SectionTemplate("4", "合格性规定", "Qualification provisions", 1, "must"))
    templates.append(SectionTemplate("5", "需求可追踪性", "Requirement traceability", 1, "must"))
    templates.append(SectionTemplate("6", "注释", "Notes", 1, "optional"))

    return templates


# ── 3. 章节对齐算法 (Section → SectionTemplate) ──────────────

@dataclass
class AlignResult:
    """对齐结果"""
    section_id: str
    section_number: str
    section_title: str
    template_number: str
    template_title: str
    match_type: str       # exact / variant / title_match / none
    match_score: float    # 0-1
    notes: str = ""


def normalize_number(num: str) -> str:
    """归一化编号: "3.2.1" → "3.2.1"; "3.2.X" → "3.2.X" """
    return num.strip()


def number_matches(sec_num: str, tpl_num: str) -> bool:
    """
    编号匹配:
      - 精确: "3.2.1" == "3.2.1"
      - 通配: "3.2.1" matches "3.2.X" (X 为通配)
      - 前缀: "3.2.1" matches "3.2" (子节匹配父模板)
    """
    if sec_num == tpl_num:
        return True
    # 通配匹配: 3.2.1 matches 3.2.X
    if tpl_num.endswith(".X"):
        prefix = tpl_num[:-2]
        if sec_num.startswith(prefix + "."):
            return True
    return False


def title_similarity(t1: str, t2: str) -> float:
    """标题相似度 (基于关键词重叠)"""
    if not t1 or not t2:
        return 0.0
    # 去除常见后缀
    for suffix in ["需求", "规定", "说明"]:
        t1 = t1.replace(suffix, "")
        t2 = t2.replace(suffix, "")
    # 字符级 Jaccard
    s1, s2 = set(t1), set(t2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def align_section(section: Section, templates: list[SectionTemplate],
                  template_index: dict) -> AlignResult:
    """
    将文档章节对齐到标准模板.
    策略:
      1. 精确编号匹配
      2. 通配编号匹配 (3.2.1 → 3.2.X)
      3. 变体标题匹配 (3.7安全性 → 模板3.7保密性的variant)
      4. 标题相似度匹配
    """
    sec_num = section.number
    sec_title = section.title

    # 策略1: 精确编号匹配 (编号相同时直接对齐, 标题用于区分exact/variant)
    if sec_num in template_index:
        tpl = template_index[sec_num]
        sim = title_similarity(sec_title, tpl.title)
        is_variant = sec_title in (tpl.variants or [])
        # 编号精确匹配即对齐; 标题相似度仅用于区分 exact vs variant
        if is_variant or sim < 0.3:
            return AlignResult(
                section.id, sec_num, sec_title,
                tpl.number, tpl.title,
                "variant", 0.85 if is_variant else 0.6,
                "变体标题" if is_variant else "编号精确匹配,标题差异"
            )
        return AlignResult(
            section.id, sec_num, sec_title,
            tpl.number, tpl.title,
            "exact", max(sim, 0.9), ""
        )

    # 策略2: 通配编号匹配 (3.2.1 → 3.2.X)
    parts = sec_num.split('.')
    for n in range(len(parts), 0, -1):
        prefix = '.'.join(parts[:n])
        # 尝试 prefix.X
        wildcard = f"{prefix}.X"
        if wildcard in template_index:
            tpl = template_index[wildcard]
            return AlignResult(
                section.id, sec_num, sec_title,
                tpl.number, tpl.title,
                "exact", 0.9, "通配匹配"
            )

    # 策略3: 变体标题匹配
    # 遍历同层级模板, 检查标题是否在 variants 中
    sec_level = section.level
    for tpl in templates:
        if abs(tpl.level - sec_level) <= 1 and tpl.variants:
            if sec_title in tpl.variants or any(v in sec_title for v in tpl.variants):
                return AlignResult(
                    section.id, sec_num, sec_title,
                    tpl.number, tpl.title,
                    "variant", 0.85, f"标题变体: {sec_title}→{tpl.title}"
                )

    # 策略4: 标题相似度匹配 (仅对2级以上章节)
    if sec_level <= 2:
        best_sim = 0
        best_tpl = None
        for tpl in templates:
            if tpl.level <= 2:
                sim = title_similarity(sec_title, tpl.title)
                if sim > best_sim:
                    best_sim = sim
                    best_tpl = tpl
        if best_tpl and best_sim > 0.4:
            return AlignResult(
                section.id, sec_num, sec_title,
                best_tpl.number, best_tpl.title,
                "title_match", best_sim, "标题相似度匹配"
            )

    return AlignResult(
        section.id, sec_num, sec_title,
        "", "", "none", 0.0, "未匹配"
    )


# ── 4. 验证主流程 ─────────────────────────────────────────────

def verify_document(md_path: Path, doc_id: str, templates: list[SectionTemplate],
                    template_index: dict) -> dict:
    """验证单份文档的章节对齐效果"""
    md_text = md_path.read_text(encoding="utf-8", errors="replace")

    # 提取章节
    all_sections = extract_sections(md_text, doc_id)
    content_sections = filter_content_sections(all_sections)

    # 对齐
    results = []
    for sec in content_sections:
        result = align_section(sec, templates, template_index)
        results.append(result)

    # 统计
    by_type = {}
    for r in results:
        by_type[r.match_type] = by_type.get(r.match_type, 0) + 1

    aligned = sum(1 for r in results if r.match_type != "none")
    total = len(results)
    align_rate = aligned / total if total > 0 else 0

    # 未匹配的章节
    unmatched = [r for r in results if r.match_type == "none"]

    return {
        "doc_id": doc_id,
        "md_path": str(md_path),
        "total_headings": len(all_sections),
        "content_sections": total,
        "aligned": aligned,
        "align_rate": round(align_rate, 4),
        "by_match_type": by_type,
        "results": [asdict(r) for r in results],
        "unmatched": [asdict(r) for r in unmatched],
    }


def main():
    print("=" * 70)
    print("章节编号解析 + SectionTemplate 对齐 验证")
    print("=" * 70)

    # 构建 SectionTemplate
    templates = build_section_templates()
    template_index = {t.number: t for t in templates}
    print(f"\n[1] SectionTemplate 构建: {len(templates)} 个模板节点")
    print(f"    覆盖章节: 1, 2, 3(含3.1~3.18), 4, 5, 6")

    # 验证3份Gold Standard文档
    docs = [
        ("battery_srs", MINERU_SRS / "battery_srs.pdf/auto/battery_srs.pdf.md"),
        ("compiler_srs", MINERU_SRS / "compiler_srs.pdf/auto/compiler_srs.pdf.md"),
        ("scheduler_srs", MINERU_SRS / "scheduler_srs.pdf/auto/scheduler_srs.pdf.md"),
    ]

    all_results = {}
    for doc_id, md_path in docs:
        if not md_path.exists():
            print(f"\n[!] 文档不存在: {md_path}")
            continue
        print(f"\n[2] 验证文档: {doc_id}")
        result = verify_document(md_path, doc_id, templates, template_index)
        all_results[doc_id] = result
        print(f"    总标题数: {result['total_headings']}")
        print(f"    正文章节数: {result['content_sections']}")
        print(f"    对齐成功: {result['aligned']} ({result['align_rate']:.1%})")
        print(f"    匹配类型分布: {result['by_match_type']}")
        if result['unmatched']:
            print(f"    未匹配章节 ({len(result['unmatched'])} 个):")
            for u in result['unmatched'][:10]:
                print(f"      - {u['section_number']} {u['section_title']}")

    # 汇总统计
    print(f"\n{'=' * 70}")
    print(f"[3] 汇总统计")
    print(f"{'=' * 70}")
    total_sections = sum(r['content_sections'] for r in all_results.values())
    total_aligned = sum(r['aligned'] for r in all_results.values())
    overall_rate = total_aligned / total_sections if total_sections > 0 else 0
    print(f"    文档数: {len(all_results)}")
    print(f"    正文章节总数: {total_sections}")
    print(f"    对齐成功总数: {total_aligned}")
    print(f"    整体对齐率: {overall_rate:.1%}")

    # 对齐率评估
    print(f"\n[4] 对齐率评估")
    if overall_rate >= 0.85:
        print(f"    ✓ 达标 (≥85%): 章节对齐方案可行, 可进入全面实施")
    elif overall_rate >= 0.70:
        print(f"    △ 基本达标 (≥70%): 需优化未匹配章节的对齐策略")
    else:
        print(f"    ✗ 未达标 (<70%): 需重新设计对齐算法")

    # 输出详细结果
    output_path = OUTPUT_DIR / "section_align_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "templates": [asdict(t) for t in templates],
            "results": all_results,
            "summary": {
                "total_sections": total_sections,
                "total_aligned": total_aligned,
                "overall_align_rate": round(overall_rate, 4),
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"\n[5] 详细结果已保存: {output_path}")

    return overall_rate


if __name__ == "__main__":
    rate = main()
    exit(0 if rate >= 0.70 else 1)
