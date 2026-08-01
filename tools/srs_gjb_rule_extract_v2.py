#!/usr/bin/env python3
"""
GJB 438C 规则自动提取管线 v2
================================
从 MinerU OCR markdown 自动提取 GJB 438C-2021 标准中的规范性条款。

提取策略:
  1. 逐行扫描 OCR markdown, 跟踪当前章节/附录归属
  2. 识别句子级别的模态词 (应/宜/可/不应/不得) 作为条款标志
  3. 过滤非条款上下文 (引用文件列表、术语定义、注释)
  4. 输出带 OCR 行号的规则列表, 可与人工 curated 的 120 条交叉验证

这是可复现的提取管线 —— 别人重新运行能得到相同结果。

用法:
  python3 tools/srs_gjb_rule_extract_v2.py              # 提取+交叉验证
  python3 tools/srs_gjb_rule_extract_v2.py --extract-only # 仅提取
  python3 tools/srs_gjb_rule_extract_v2.py --verify-only  # 仅交叉验证
"""
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import Counter, defaultdict

BASE = Path(__file__).resolve().parent.parent
OCR_PATH = BASE / "data/gjb_438c/ocr/GJB_438C_2021.pdf/auto/GJB_438C_2021.pdf.md"
MANUAL_RULES_PATH = BASE / "knowledge/gjb_438c_rules_full.json"
OUTPUT_DIR = BASE / "data/gjb_438c/rule_extract_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 模态词识别 ────────────────────────────────────────────────

# 模态词作为独立语法成分出现(前接标点/空格/行首, 后接动词)
# 排除词内"应"(如"应用"、"反应"、"供应"、"适应"、"响应"、"对应")
MODAL_PATTERNS = {
    "MUST": re.compile(r'(?:^|[，。；：、\s])应(?:该|当|对|由|有|能|为|是|予|将|按|先|在|于|确|使|包|提|定|列|描|说|满|遵|给|分|考|确|包|含|给|出|识|标|定|说明|描述|包括|满足|遵循|提供|列出|标识|定义|指定|规定|概述|逐一|通过|采用|参考|说明|采用)'),  # noqa
    "SHOULD": re.compile(r'(?:^|[，。；：、\s])宜(?:包括|采用|包含|有|为|在|对|由)'),
    "MAY": re.compile(r'(?:^|[，。；：、\s])可(?:以|能|采用|包含|为|在|对|由|不|参考|作为|采用|包含|包括|采用)'),
    "MUST_NOT": re.compile(r'(?:^|[，。；：、\s])不(?:应|得)'),
}

# 简化版: 模态词在句首或标点后出现即可(更宽松, 用后续过滤)
MODAL_SENTENCE_RE = re.compile(
    r'(?:^|[，。；：、\n])\s*(应|宜|可|不应|不得)(?:该|当|对|由|有|能|为|是|予|将|按|先|在|于|确|使|包|提|定|列|描|说|满|遵|给|分|考|包|含|给|出|识|标|说|描|包|满|遵|提|列|标|定|指|规|概|通|采|参|作|以|能|采|包|包|采)'
)

# 排除的区域(非规范性内容)
EXCLUDE_SECTIONS = {
    "2",           # 引用文件(列出的标准编号含"应"但不构成规则)
    "3.1",         # 术语和定义
    "3.2",         # 缩略语(标准正文的3.2, 非附录J的3.2)
}

# 章节标题正则
CHAPTER_RE = re.compile(r'^#+\s+(\d+(?:\.\w+)*)\s*(.*)')
APPENDIX_RE = re.compile(r'^#+\s+附录([A-Z])\b')


@dataclass
class ExtractedRule:
    """从OCR自动提取的规则"""
    auto_id: str               # 自动编号 AUTO-001
    ocr_line: int              # OCR行号(1-based)
    ocr_file: str              # OCR文件路径
    source_section: str        # 所属章节编号(如 "4.3.2", "附录J 3.2")
    source_appendix: str       # 所属附录(如 "J", "" 表示正文)
    modality: str              # MUST / SHOULD / MAY / MUST_NOT
    original_text: str         # OCR原文(逐字, 不修改)
    sentence_start: int        # 条款在行中的字符偏移
    context_before: str        # 前文上下文(用于消歧)


def load_ocr() -> tuple[str, list[str]]:
    """加载OCR markdown"""
    text = OCR_PATH.read_text(encoding="utf-8", errors="replace")
    return text, text.split("\n")


def is_excluded(section: str, appendix: str) -> bool:
    """判断是否在排除区域(引用文件/术语定义等)"""
    # 正文第2章(引用文件)和3.1/3.2(术语缩略语)排除
    if appendix == "" and section in EXCLUDE_SECTIONS:
        return True
    # 前言/目次排除
    if section in ("", "前言", "目次"):
        return True
    return False


def find_modal_sentences(text: str) -> list[tuple[int, str, str, int]]:
    """
    在文本中找模态句, 提取完整句子(含主语).
    返回: [(模态词, 句子起始偏移, 完整句子, 模态词在句中偏移), ...]

    策略: 按句号/分号/换行分句, 若句子含模态词则提取整个句子(含主语).
    """
    results = []
    # 按句号/分号/换行分句, 保留分隔符
    sentences = re.split(r'(?<=[。；\n])', text)
    offset = 0
    for sent in sentences:
        sent_stripped = sent.strip()
        if len(sent_stripped) < 8:
            offset += len(sent)
            continue
        # 检查句子中是否含模态词(作为独立词, 非词内)
        modal_found = None
        modal_pos = -1
        for modal, pattern in [
            ("MUST_NOT", re.compile(r'不应|不得')),
            ("MUST", re.compile(r'(?:^|[，。；：、\s（）\(\)])应(?![用反应供应适应响对应])')),
            ("SHOULD", re.compile(r'(?:^|[，。；：、\s（）\(\)])宜(?![兴昌盛隆])')),
            ("MAY", re.compile(r'(?:^|[，。；：、\s（）\(\)])可(?![能行机以靠虑持续续能行知见得是])')),
        ]:
            m = pattern.search(sent)
            if m:
                modal_found = modal
                modal_pos = m.start()
                break
        if modal_found:
            # 提取整个句子(含主语), 去除首尾空白
            clause = sent_stripped
            # 去除开头的标点
            clause = re.sub(r'^[，。；：、\s]+', '', clause)
            if len(clause) >= 8:
                results.append((modal_found, offset, clause, modal_pos))
        offset += len(sent)
    return results


def extract_rules_from_ocr() -> list[ExtractedRule]:
    """
    主提取函数: 从OCR markdown自动提取规范性条款.
    
    流程:
      1. 逐行扫描, 跟踪当前章节和附录
      2. 对每行(或段落)找模态句
      3. 过滤排除区域
      4. 去重(同一条款可能跨行)
    """
    text, lines = load_ocr()
    rules = []
    current_section = ""
    current_appendix = ""
    current_appendix_name = ""
    seen_texts = set()  # 去重
    
    # 预处理: 将连续非标题行合并为段落(OCR中一个条款可能跨多行)
    # 但保留行号信息(用第一行)
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # 跟踪章节标题
        chap_m = CHAPTER_RE.match(line)
        if chap_m:
            current_section = chap_m.group(1)
            current_section_title = chap_m.group(2).strip()
            # 检查是否是附录内章节
            # 附录J的"3 需求"应记为"附录J 3"
            if current_appendix:
                full_section = f"附录{current_appendix} {current_section}"
            else:
                full_section = current_section
            i += 1
            continue
        
        # 跟踪附录标题
        app_m = APPENDIX_RE.match(line)
        if app_m:
            current_appendix = app_m.group(1)
            # 读取下一行获取附录名称
            if i + 1 < len(lines):
                current_appendix_name = lines[i + 1].strip().strip('#').strip()
            i += 1
            continue
        
        # 跳过空行和表格
        if not line_stripped or line_stripped.startswith("<table") or line_stripped.startswith("|"):
            i += 1
            continue
        
        # 构建完整段落(合并连续非标题非空行)
        para_lines = [line_stripped]
        para_start_line = i + 1  # 1-based
        j = i + 1
        while j < len(lines):
            next_line = lines[j].strip()
            if not next_line:
                break
            if CHAPTER_RE.match(lines[j]) or APPENDIX_RE.match(lines[j]):
                break
            if next_line.startswith("<table") or next_line.startswith("|"):
                break
            para_lines.append(next_line)
            j += 1
        
        paragraph = " ".join(para_lines)
        
        # 构建完整章节路径
        if current_appendix:
            full_section = f"附录{current_appendix} {current_section}"
        else:
            full_section = current_section
        
        # 过滤排除区域
        if is_excluded(current_section, current_appendix):
            i = j
            continue
        
        # 在段落中找模态句
        modal_sentences = find_modal_sentences(paragraph)
        
        for modal, char_offset, clause, modal_pos in modal_sentences:
            # 去重(基于前20字)
            dedup_key = clause[:20]
            if dedup_key in seen_texts:
                continue
            seen_texts.add(dedup_key)
            
            auto_id = f"AUTO-{len(rules) + 1:03d}"
            rules.append(ExtractedRule(
                auto_id=auto_id,
                ocr_line=para_start_line,
                ocr_file=str(OCR_PATH.relative_to(BASE)),
                source_section=full_section,
                source_appendix=current_appendix,
                modality=modal,
                original_text=clause,
                sentence_start=char_offset,
                context_before=paragraph[:char_offset][-50:] if char_offset > 0 else ""
            ))
        
        i = j
    
    return rules


# ── 交叉验证: 自动提取 vs 人工120条 ──────────────────────────

def _text_match(auto_text: str, manual_text: str) -> bool:
    """
    判断自动提取文本与人工文本是否匹配.
    策略: 双向包含(取较长者的连续15字片段在另一者中查找).
    对人工规则中的省略号(…/...)做分片匹配.
    """
    if len(auto_text) < 8 or len(manual_text) < 8:
        return False
    # 去除省略号, 分片
    manual_fragments = [f.strip() for f in re.split(r'[…\.]{2,}', manual_text) if len(f.strip()) >= 8]
    auto_fragments = [f.strip() for f in re.split(r'[…\.]{2,}', auto_text) if len(f.strip()) >= 8]
    
    # 如果人工文本有省略号分片, 检查每个分片是否在自动文本中
    if len(manual_fragments) > 1:
        matched_count = sum(1 for f in manual_fragments if f[:12] in auto_text)
        if matched_count >= max(1, len(manual_fragments) // 2):
            return True
    
    # 双向15字包含
    for longer, shorter in [(auto_text, manual_text), (manual_text, auto_text)]:
        # 取较短者的中间15字片段
        if len(shorter) >= 15:
            mid = len(shorter) // 2
            frag = shorter[max(0, mid-7):mid+8]
            if frag in longer:
                return True
        # 取较短者前12字
        if shorter[:12] in longer:
            return True
    return False


def cross_verify(auto_rules: list[ExtractedRule], manual_rules: list[dict]) -> dict:
    """
    交叉验证: 自动提取的规则 vs 人工curated的120条.
    """
    manual_coverage = []
    for mr in manual_rules:
        mr_text = mr.get("original_text", "")
        mr_source = mr.get("source", "")
        # 在自动规则中找文本匹配
        matched_auto = []
        for ar in auto_rules:
            if _text_match(ar.original_text, mr_text):
                matched_auto.append(ar)
        
        manual_coverage.append({
            "rule_id": mr.get("rule_id", ""),
            "source": mr_source,
            "manual_text_preview": mr_text[:60],
            "auto_matched": len(matched_auto) > 0,
            "matched_auto_ids": [ar.auto_id for ar in matched_auto[:3]],
            "matched_auto_lines": [ar.ocr_line for ar in matched_auto[:3]],
        })
    
    # 自动规则中未被人工收录的
    auto_only = []
    for ar in auto_rules:
        covered = False
        for mr in manual_rules:
            if _text_match(ar.original_text, mr.get("original_text", "")):
                covered = True
                break
        if not covered:
            auto_only.append(ar)
    
    # 统计
    manual_covered = sum(1 for c in manual_coverage if c["auto_matched"])
    manual_total = len(manual_coverage)
    
    auto_by_source = Counter(r.source_section.split()[0] if r.source_section else "unknown" for r in auto_rules)
    
    return {
        "summary": {
            "auto_extracted_count": len(auto_rules),
            "manual_curated_count": len(manual_rules),
            "manual_covered_by_auto": manual_covered,
            "manual_coverage_rate": round(manual_covered / manual_total, 4) if manual_total > 0 else 0,
            "auto_only_count": len(auto_only),
            "auto_only_rate": round(len(auto_only) / len(auto_rules), 4) if auto_rules else 0,
        },
        "auto_by_modality": dict(Counter(r.modality for r in auto_rules)),
        "auto_by_appendix": dict(Counter(r.source_appendix or "正文" for r in auto_rules)),
        "manual_coverage_detail": manual_coverage,
        "auto_only_rules": [
            {
                "auto_id": r.auto_id,
                "ocr_line": r.ocr_line,
                "source_section": r.source_section,
                "modality": r.modality,
                "text_preview": r.original_text[:80],
            } for r in auto_only[:50]
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="GJB 438C 规则自动提取管线 v2")
    parser.add_argument("--extract-only", action="store_true", help="仅提取,不交叉验证")
    parser.add_argument("--verify-only", action="store_true", help="仅交叉验证(需已有提取结果)")
    args = parser.parse_args()
    
    print("=" * 70)
    print("GJB 438C 规则自动提取管线 v2")
    print("=" * 70)
    print(f"OCR源文件: {OCR_PATH.relative_to(BASE)}")
    
    if not args.verify_only:
        print(f"\n[1] 从OCR自动提取规范性条款...")
        auto_rules = extract_rules_from_ocr()
        print(f"    提取到 {len(auto_rules)} 条规则")
        print(f"    模态分布: {dict(Counter(r.modality for r in auto_rules))}")
        print(f"    附录分布: {dict(Counter(r.source_appendix or '正文' for r in auto_rules))}")
        
        # 保存提取结果
        extract_path = OUTPUT_DIR / "auto_extracted_rules.json"
        with open(extract_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in auto_rules], f, ensure_ascii=False, indent=2)
        print(f"    提取结果已保存: {extract_path.relative_to(BASE)}")
        
        # 输出抽样
        print(f"\n    抽样(前5条):")
        for r in auto_rules[:5]:
            print(f"      {r.auto_id} L{r.ocr_line} [{r.modality}] {r.source_section}: {r.original_text[:60]}")
    
    if args.extract_only:
        return
    
    if not args.verify_only:
        # 加载人工规则
        print(f"\n[2] 加载人工curated规则: {MANUAL_RULES_PATH.relative_to(BASE)}")
    
    manual_rules = json.loads(MANUAL_RULES_PATH.read_text(encoding="utf-8")).get("rules", [])
    print(f"    人工规则数: {len(manual_rules)}")
    
    # 交叉验证
    print(f"\n[3] 交叉验证: 自动提取 vs 人工curated")
    if 'auto_rules' not in dir():
        # verify-only模式, 从文件加载
        extract_path = OUTPUT_DIR / "auto_extracted_rules.json"
        auto_rules = [ExtractedRule(**r) for r in json.loads(extract_path.read_text(encoding="utf-8"))]
    
    result = cross_verify(auto_rules, manual_rules)
    
    print(f"\n    === 交叉验证结果 ===")
    print(f"    自动提取规则数: {result['summary']['auto_extracted_count']}")
    print(f"    人工curated规则数: {result['summary']['manual_curated_count']}")
    print(f"    人工规则被自动提取覆盖: {result['summary']['manual_covered_by_auto']}/{result['summary']['manual_curated_count']} ({result['summary']['manual_coverage_rate']:.1%})")
    print(f"    自动提取独有(人工未收录): {result['summary']['auto_only_count']} ({result['summary']['auto_only_rate']:.1%})")
    
    print(f"\n    自动提取按模态: {result['auto_by_modality']}")
    print(f"    自动提取按附录: {result['auto_by_appendix']}")
    
    # 人工规则未被覆盖的
    uncovered = [c for c in result['manual_coverage_detail'] if not c['auto_matched']]
    if uncovered:
        print(f"\n    人工规则未被自动提取覆盖 ({len(uncovered)} 条):")
        for c in uncovered[:15]:
            print(f"      {c['rule_id']} [{c['source']}]: {c['manual_text_preview']}")
    
    # 自动提取独有
    if result['auto_only_rules']:
        print(f"\n    自动提取独有规则 (前15条, 人工未收录):")
        for r in result['auto_only_rules'][:15]:
            print(f"      {r['auto_id']} L{r['ocr_line']} [{r['modality']}] {r['source_section']}: {r['text_preview']}")
    
    # 保存验证结果
    verify_path = OUTPUT_DIR / "cross_verify_report.json"
    with open(verify_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n    验证报告已保存: {verify_path.relative_to(BASE)}")
    
    # 评估
    print(f"\n[4] 评估")
    cov_rate = result['summary']['manual_coverage_rate']
    if cov_rate >= 0.80:
        print(f"    ✓ 人工规则覆盖率 {cov_rate:.1%} ≥ 80%: 提取管线有效覆盖人工规则")
    elif cov_rate >= 0.60:
        print(f"    △ 人工规则覆盖率 {cov_rate:.1%} ∈ [60%,80%): 部分覆盖,需分析未覆盖原因")
    else:
        print(f"    ✗ 人工规则覆盖率 {cov_rate:.1%} < 60%: 提取策略需优化")


if __name__ == "__main__":
    main()
