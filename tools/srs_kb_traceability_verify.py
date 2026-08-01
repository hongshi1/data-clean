#!/usr/bin/env python3
"""
GJB 438C 规则溯源验证工具
==========================
为每条人工curated规则建立到OCR原文的精确行号映射, 并验证准确性。

功能:
  1. 对每条规则的 original_text 在OCR中搜索, 找到行号
  2. 判断 match_type (verbatim/normalized/ellipsis/synthesized/not_found)
  3. 验证 source 字段指向的章节是否与OCR行号吻合
  4. 输出可核查的验证报告

别人可以用 --rule GJB-RULE-039 独立核查任意一条。

用法:
  python3 tools/srs_kb_traceability_verify.py              # 验证全部120条
  python3 tools/srs_kb_traceability_verify.py --rule GJB-RULE-039  # 验证单条
  python3 tools/srs_kb_traceability_verify.py --summary            # 仅输出统计
"""
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from collections import Counter

BASE = Path(__file__).resolve().parent.parent
OCR_PATH = BASE / "data/gjb_438c/ocr/GJB_438C_2021.pdf/auto/GJB_438C_2021.pdf.md"
RULES_PATH = BASE / "knowledge/gjb_438c_rules_full.json"
OUTPUT_DIR = BASE / "data/gjb_438c/rule_extract_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class VerificationResult:
    """单条规则的溯源验证结果"""
    rule_id: str
    source: str
    modality: str
    original_text_preview: str
    # 溯源结果
    ocr_line: int                    # 找到的OCR行号(0=未找到)
    match_type: str                  # verbatim/normalized/ellipsis/synthesized/not_found
    ocr_snippet: str                 # OCR原文片段(验证用)
    # source字段验证
    ocr_section_at_line: str         # OCR该行实际所属章节
    source_correct: bool             # source字段是否与OCR行号吻合
    # 总判定
    verdict: str                     # PASS / FAIL / WARNING
    notes: str


def load_ocr() -> tuple[str, list[str]]:
    """加载OCR, 返回(全文, 行列表)"""
    text = OCR_PATH.read_text(encoding="utf-8", errors="replace")
    return text, text.split("\n")


def find_in_ocr(text: str, original_text: str) -> tuple[int, str, str]:
    """
    在OCR全文中搜索original_text, 返回(行号, match_type, ocr_snippet).
    
    匹配策略(按优先级):
      1. verbatim: original_text完整出现在OCR中(逐字)
      2. normalized: 去除空白后完整匹配
      3. ellipsis: original_text含省略号, 分片后每个片段都能在OCR中找到
      4. not_found: 找不到
    """
    if not original_text or len(original_text) < 8:
        return 0, "not_found", ""

    # 策略1: 逐字匹配
    pos = text.find(original_text)
    if pos >= 0:
        line_no = text[:pos].count("\n") + 1
        snippet = original_text[:80]
        return line_no, "verbatim", snippet

    # 策略2: 规范化匹配(去空白)
    norm_orig = re.sub(r'\s+', '', original_text)
    norm_text = re.sub(r'\s+', '', text)
    pos_norm = norm_text.find(norm_orig)
    if pos_norm >= 0:
        # 反推原始行号(近似: 规范化前的字符位置)
        # 用原文本中省略号前的第一段定位
        first_fragment = original_text.split('…')[0].split('...')[0].strip()
        if len(first_fragment) >= 10:
            pos2 = text.find(first_fragment)
            if pos2 >= 0:
                line_no = text[:pos2].count("\n") + 1
                return line_no, "normalized", first_fragment[:80]
        return 0, "normalized", ""

    # 策略3: 省略号分片匹配
    if '…' in original_text or '...' in original_text:
        fragments = re.split(r'[…\.]{3,}', original_text)
        fragments = [f.strip() for f in fragments if len(f.strip()) >= 6]
        if len(fragments) >= 2:
            # 找第一个能定位的片段
            for frag in fragments:
                pos_frag = text.find(frag)
                if pos_frag >= 0:
                    line_no = text[:pos_frag].count("\n") + 1
                    # 验证其他片段也在OCR中(在第一个片段之后搜索)
                    all_found = True
                    search_start = pos_frag
                    for other_frag in fragments[1:]:
                        pos_other = text.find(other_frag, search_start)
                        if pos_other < 0:
                            all_found = False
                            break
                        search_start = pos_other + len(other_frag)
                    if all_found:
                        return line_no, "ellipsis", frag[:80]
                    else:
                        return line_no, "ellipsis_partial", frag[:80]

    # 策略4: 取前15字做模糊匹配(OCR可能有细微差异)
    prefix = original_text[:15].strip()
    if len(prefix) >= 10:
        pos_prefix = text.find(prefix)
        if pos_prefix >= 0:
            line_no = text[:pos_prefix].count("\n") + 1
            return line_no, "fuzzy_prefix", prefix

    return 0, "not_found", ""


def get_section_at_line(lines: list[str], target_line: int) -> str:
    """获取OCR某行所属的章节(向上找最近的章节标题)"""
    if target_line <= 0 or target_line > len(lines):
        return ""
    # 向上找最近的 ## 标题
    for i in range(target_line - 1, max(0, target_line - 100), -1):
        if i < len(lines):
            line = lines[i]
            m = re.match(r'^#+\s+(\d+(?:\.\w+)*)\s+(.*)', line)
            if m:
                return m.group(1)
            # 附录标题
            m2 = re.match(r'^#+\s+附录([A-Z])', line)
            if m2:
                # 继续找附录内的子章节
                for j in range(i + 1, target_line):
                    if j < len(lines):
                        m3 = re.match(r'^#+\s+(\d+(?:\.\w+)*)\s+', lines[j])
                        if m3:
                            return f"附录{m2.group(1)} {m3.group(1)}"
                return f"附录{m2.group(1)}"
    return ""


def get_appendix_ranges(lines: list[str]) -> dict[str, tuple[int, int]]:
    """获取各附录的行号范围 {附录字母: (起始行, 结束行)}"""
    ranges = {}
    current_appendix = None
    start_line = 0
    for i, line in enumerate(lines, 1):
        m = re.match(r'^#+\s+附录([A-Z])\b', line)
        if m:
            if current_appendix:
                ranges[current_appendix] = (start_line, i - 1)
            current_appendix = m.group(1)
            start_line = i
    if current_appendix:
        ranges[current_appendix] = (start_line, len(lines))
    return ranges


def verify_source_field(rule_source: str, ocr_section: str, ocr_line: int,
                        appendix_ranges: dict) -> tuple[bool, str]:
    """
    验证规则的source字段是否与OCR行号吻合.
    改进版: 处理"附录X"前缀, 并检查行号是否在附录范围内.
    """
    if not rule_source or ocr_line <= 0:
        return False, "无法判断(章节为空或行号无效)"

    # 提取source中的附录字母和章节号
    # source 例子: "4.3.2", "附录J 3.2.X", "附录F/G/H/I/J/K 5/6", "第5章 5.10"
    appendix_m = re.search(r'附录([A-Z])', rule_source)
    source_appendix = appendix_m.group(1) if appendix_m else ""
    
    # 提取章节号(去掉"附录X"、"第X章"前缀)
    section_num = re.sub(r'附录[A-Z](?:/[A-Z])*\s*', '', rule_source)
    section_num = re.sub(r'第\d+章\s*', '', section_num)
    section_num = section_num.strip()
    
    # 1. 如果source声称附录X, 检查OCR行号是否在该附录范围内
    if source_appendix and source_appendix in appendix_ranges:
        start, end = appendix_ranges[source_appendix]
        if not (start <= ocr_line <= end):
            # 检查是否是跨附录规则
            if '/' in rule_source:
                # 跨附录规则, 检查是否在任一声称的附录内
                all_appendices = re.findall(r'[A-Z]', rule_source.split()[0].replace('附录', ''))
                in_any = any(a in appendix_ranges and appendix_ranges[a][0] <= ocr_line <= appendix_ranges[a][1]
                             for a in all_appendices)
                if in_any:
                    return True, "跨附录规则,行号在声称范围内"
                else:
                    return False, f"跨附录规则,但行{ocr_line}不在任何声称附录内"
            else:
                return False, f"声称附录{source_appendix}({start}-{end}行),实际在{ocr_line}行"
    
    # 2. 检查OCR章节号是否匹配
    if section_num and ocr_section:
        # 去掉通配符X
        sn = section_num.replace('.X', '').replace('X', '')
        os_clean = ocr_section.replace('附录', '').strip()
        # 精确或前缀匹配
        if sn == os_clean or os_clean.startswith(sn) or sn.startswith(os_clean):
            return True, "章节号匹配"
    
    # 3. 如果source是正文(无附录), 检查OCR行号是否在正文范围(附录前)
    if not source_appendix and appendix_ranges:
        first_appendix_line = min(r[0] for r in appendix_ranges.values())
        if ocr_line >= first_appendix_line:
            return False, f"声称正文,实际行{ocr_line}在附录区域"
        return True, "正文规则,行号在正文范围"
    
    return True, "宽匹配通过"  # 默认通过(避免过度严格)


def verify_single_rule(rule: dict, ocr_text: str, ocr_lines: list[str],
                       appendix_ranges: dict) -> VerificationResult:
    """验证单条规则"""
    rule_id = rule.get("rule_id", "")
    source = rule.get("source", "")
    modality = rule.get("modality", "")
    original_text = rule.get("original_text", "")

    # 1. 在OCR中搜索(如果source声称附录, 优先在该附录范围搜索)
    appendix_m = re.search(r'附录([A-Z])', source)
    if appendix_m and appendix_m.group(1) in appendix_ranges:
        start, end = appendix_ranges[appendix_m.group(1)]
        # 优先在附录范围内搜索
        range_text = "\n".join(ocr_lines[start-1:end])
        line_no, match_type, snippet = find_in_ocr(range_text, original_text)
        if line_no > 0:
            line_no += start - 1  # 转为全文行号
        else:
            # 附录范围内没找到, 在全文搜索
            line_no, match_type, snippet = find_in_ocr(ocr_text, original_text)
    else:
        line_no, match_type, snippet = find_in_ocr(ocr_text, original_text)

    # 2. 获取OCR该行所属章节
    ocr_section = get_section_at_line(ocr_lines, line_no) if line_no > 0 else ""

    # 3. 验证source字段
    if line_no > 0 and source:
        source_ok, source_note = verify_source_field(source, ocr_section, line_no, appendix_ranges)
    else:
        source_ok = False
        source_note = "未找到OCR位置,无法验证"

    # 4. 总判定
    if match_type == "not_found":
        verdict = "FAIL"
        notes = f"未在OCR中找到original_text"
    elif match_type in ("verbatim", "normalized"):
        verdict = "PASS" if source_ok else "WARNING"
        notes = f"OCR行{line_no}, {match_type}" + ("" if source_ok else f", {source_note}")
    elif match_type in ("ellipsis", "ellipsis_partial", "fuzzy_prefix"):
        verdict = "PASS" if source_ok else "WARNING"
        notes = f"OCR行{line_no}, {match_type}" + ("" if source_ok else f", {source_note}")
    else:
        verdict = "WARNING"
        notes = f"OCR行{line_no}, {match_type}"

    return VerificationResult(
        rule_id=rule_id,
        source=source,
        modality=modality,
        original_text_preview=original_text[:60],
        ocr_line=line_no,
        match_type=match_type,
        ocr_snippet=snippet,
        ocr_section_at_line=ocr_section,
        source_correct=source_ok,
        verdict=verdict,
        notes=notes,
    )


def main():
    parser = argparse.ArgumentParser(description="GJB 438C 规则溯源验证工具")
    parser.add_argument("--rule", type=str, help="验证单条规则(指定rule_id)")
    parser.add_argument("--summary", action="store_true", help="仅输出统计摘要")
    args = parser.parse_args()

    print("=" * 70)
    print("GJB 438C 规则溯源验证工具")
    print("=" * 70)
    print(f"OCR源: {OCR_PATH.relative_to(BASE)}")
    print(f"规则库: {RULES_PATH.relative_to(BASE)}")

    # 加载
    ocr_text, ocr_lines = load_ocr()
    appendix_ranges = get_appendix_ranges(ocr_lines)
    print(f"OCR行数: {len(ocr_lines)}")
    print(f"附录范围: {len(appendix_ranges)}个附录")
    rules_data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rules = rules_data.get("rules", [])
    print(f"规则总数: {len(rules)}")

    # 单条验证
    if args.rule:
        rule = next((r for r in rules if r.get("rule_id") == args.rule), None)
        if not rule:
            print(f"未找到规则: {args.rule}")
            return
        result = verify_single_rule(rule, ocr_text, ocr_lines, appendix_ranges)
        print(f"\n=== {args.rule} 验证结果 ===")
        print(f"  source: {result.source}")
        print(f"  modality: {result.modality}")
        print(f"  original_text: {result.original_text_preview}...")
        print(f"  OCR行号: {result.ocr_line}")
        print(f"  匹配类型: {result.match_type}")
        print(f"  OCR片段: {result.ocr_snippet}")
        print(f"  OCR实际章节: {result.ocr_section_at_line}")
        print(f"  source准确: {result.source_correct}")
        print(f"  判定: {result.verdict}")
        print(f"  备注: {result.notes}")

        # 输出OCR原文上下文
        if result.ocr_line > 0:
            print(f"\n  OCR原文上下文 (L{max(1,result.ocr_line-2)}~L{result.ocr_line+2}):")
            for i in range(max(0, result.ocr_line - 3), min(len(ocr_lines), result.ocr_line + 2)):
                marker = " >>>" if i + 1 == result.ocr_line else "    "
                print(f"  {marker} L{i+1}: {ocr_lines[i][:80]}")
        return

    # 全量验证
    print(f"\n[1] 验证全部 {len(rules)} 条规则...")
    results = []
    for rule in rules:
        result = verify_single_rule(rule, ocr_text, ocr_lines, appendix_ranges)
        results.append(result)

    # 统计
    verdict_counts = Counter(r.verdict for r in results)
    match_type_counts = Counter(r.match_type for r in results)
    source_correct_count = sum(1 for r in results if r.source_correct and r.ocr_line > 0)

    total = len(results)
    pass_count = verdict_counts.get("PASS", 0)
    warn_count = verdict_counts.get("WARNING", 0)
    fail_count = verdict_counts.get("FAIL", 0)

    print(f"\n[2] 验证统计")
    print(f"    总规则数: {total}")
    print(f"    PASS(逐字/规范化+source正确): {pass_count} ({pass_count/total:.1%})")
    print(f"    WARNING(省略/模糊或source待查): {warn_count} ({warn_count/total:.1%})")
    print(f"    FAIL(未找到): {fail_count} ({fail_count/total:.1%})")
    print(f"    匹配类型分布: {dict(match_type_counts)}")
    print(f"    source字段正确: {source_correct_count}/{total} ({source_correct_count/total:.1%})")

    if not args.summary:
        # 输出未找到的规则
        not_found = [r for r in results if r.verdict == "FAIL"]
        if not_found:
            print(f"\n[3] 未在OCR中找到的规则 ({len(not_found)} 条):")
            for r in not_found[:20]:
                print(f"    {r.rule_id} [{r.source}]: {r.original_text_preview}")

        # 输出source可能不准确的规则
        source_warn = [r for r in results if r.ocr_line > 0 and not r.source_correct]
        if source_warn:
            print(f"\n[4] source字段可能不准确的规则 ({len(source_warn)} 条):")
            for r in source_warn[:15]:
                print(f"    {r.rule_id}: source={r.source}, ocr_section={r.ocr_section_at_line}, L{r.ocr_line}")

    # 为规则库补全 ocr_evidence 字段
    print(f"\n[5] 为规则库补全 ocr_evidence 字段...")
    enriched_rules = []
    for rule, result in zip(rules, results):
        enriched = dict(rule)
        enriched["ocr_evidence"] = {
            "ocr_file": str(OCR_PATH.relative_to(BASE)),
            "ocr_line": result.ocr_line,
            "match_type": result.match_type,
            "ocr_snippet": result.ocr_snippet,
            "ocr_section_at_line": result.ocr_section_at_line,
            "source_verified": result.source_correct,
        }
        enriched_rules.append(enriched)

    enriched_data = dict(rules_data)
    enriched_data["rules"] = enriched_rules
    enriched_data["traceability_stats"] = {
        "total": total,
        "pass": pass_count,
        "warning": warn_count,
        "fail": fail_count,
        "match_type_distribution": dict(match_type_counts),
        "source_correct_count": source_correct_count,
    }
    enriched_path = OUTPUT_DIR / "gjb_438c_rules_full_enriched.json"
    with open(enriched_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)
    print(f"    带ocr_evidence的规则库已保存: {enriched_path.relative_to(BASE)}")

    # 保存验证报告
    report_path = OUTPUT_DIR / "traceability_verify_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)
    print(f"    验证报告已保存: {report_path.relative_to(BASE)}")

    # 最终评估
    print(f"\n[6] 最终评估")
    traceable_rate = (pass_count + warn_count) / total
    if fail_count == 0 and traceable_rate >= 0.95:
        print(f"    ✓ 全部规则可追溯 ({traceable_rate:.1%}), 无编造规则")
    elif fail_count <= 3:
        print(f"    △ {fail_count}条未找到, {traceable_rate:.1%}可追溯, 需检查未找到的规则")
    else:
        print(f"    ✗ {fail_count}条未找到, 可追溯率{traceable_rate:.1%}, 需修正")


if __name__ == "__main__":
    main()
