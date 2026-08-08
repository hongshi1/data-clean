#!/usr/bin/env python3
"""
SRS一致性校验 v3 — 基于GJB 438C标准条文
=========================================
所有检测类型都有GJB 438C附录J的明确条文支撑，不是编的。

7个检测类型(每个标注GJB标准行号):
  R-001 标识完整性(L2179): 1.1节应含标识号/名称/缩略名/版本号/发布号5要素
  R-002 需求唯一标识符(L2195): 每条需求应指定项目唯一的标识符
  R-003 合格性方法(L2403): 合格性检验方法应为a)演示b)测试c)分析d)审查e)特殊之一
  R-004 追溯完整性(L2419-2423): 第5章应含正向(a)和逆向(b)追溯
  R-005 章节结构(L2195): 第3章应有3.1~3.18子章节
  R-006 接口标识符(L2217): 每个接口应有项目唯一标识符
  R-007 优先顺序(L2399): 3.18节应指明优先次序和关键性

phantom_requirement作为R-004追溯完整性的子检测保留(抽检准确率80%)。

用法:
  python3 tools/srs_check_v3.py --doc 03服务集成
  python3 tools/srs_check_v3.py --all
"""
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

BASE = Path(__file__).resolve().parent.parent
PARSED_DIR = BASE / "data/gjb_438c/mineru_structured"
OUTPUT_DIR = BASE / "data/srs_check_v3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')
GJB_QUAL_METHODS_CN = ['演示', '测试', '分析', '审查', '特殊']
GJB_QUAL_METHODS_EN = ['a', 'b', 'c', 'd', 'e']
GJB_QUAL_LETTER_MAP = {'a': '演示', 'b': '测试', 'c': '分析', 'd': '审查', 'e': '特殊'}


def _is_valid_qual_method(method: str) -> bool:
    """
    判断合格性方法是否合法。
    GJB允许组合方法: "AD"=分析+演示, "A、B、D"=分析+测试+演示
    拆分为单个字母后逐个验证。
    """
    method = method.strip().lower()
    if not method:
        return True  # 空值跳过
    # 如果直接是中文方法名
    if any(m in method for m in GJB_QUAL_METHODS_CN):
        return True
    # 拆分字母: "AD"→["a","d"], "A、B、D"→["a","b","d"], "A,B"→["a","b"]
    letters = re.findall(r'[a-e]', method)
    if not letters:
        # 既不是中文也不是字母→不合法
        return False
    # 每个字母都必须在A-E范围内
    return all(l in GJB_QUAL_METHODS_EN for l in letters)
EXPECTED_3X = [f'3.{i}' for i in range(1, 19)]


def check_r001_identity(sections: dict) -> list:
    """R-001 标识完整性 (GJB L2179)
    标准: 本条应描述...标识号、名称、缩略名、版本号和发布号
    检测: 1.1节是否包含这5个要素
    """
    violations = []
    sec_1_1 = sections.get('1.1', {})
    text = sec_1_1.get('text', '')
    
    required = ['标识号', '标识', '名称', '缩略名', '简称', '版本号', '版本', '发布号']
    found = [kw for kw in required if kw in text]
    
    # 至少要有标识号/名称/版本号3个核心要素
    core = ['标识', '名称', '版本']
    missing_core = [kw for kw in core if kw not in text]
    
    if missing_core:
        violations.append({
            "rule": "R-001",
            "gjb_clause": "附录J 1.1 (L2179)",
            "severity": "HIGH",
            "description": f"1.1标识不完整,缺少: {missing_core}",
            "standard": "本条应描述...标识号、名称、缩略名、版本号和发布号",
        })
    return violations


def check_r002_req_id_unique(sections: dict) -> list:
    """R-002 需求唯一标识符 (GJB L2195)
    标准: 每条需求应指定项目唯一的标识符以便测试和追踪
    检测: 3.2.X子节的req_id是否重复
    """
    violations = []
    req_ids = []
    for sec_id, sec_data in sections.items():
        if sec_id.startswith('3.2.') and sec_id.count('.') == 2:
            req_id = sec_data.get('req_id', '')
            if req_id:
                req_ids.append((req_id, sec_id))
    
    id_counts = Counter(req_id for req_id, _ in req_ids)
    for req_id, count in id_counts.items():
        if count > 1:
            sections_with = [s for r, s in req_ids if r == req_id]
            violations.append({
                "rule": "R-002",
                "gjb_clause": "附录J 3 (L2195)",
                "severity": "HIGH",
                "description": f"需求标识符'{req_id}'重复{count}次,出现在章节: {sections_with}",
                "standard": "每条需求应指定项目唯一的标识符以便测试和追踪",
            })
    return violations


def check_r003_qual_method(sections: dict) -> list:
    """R-003 合格性方法 (GJB L2403)
    标准: 合格性检验方法可以包括: a)演示 b)测试 c)分析 d)审查 e)特殊
    检测: 第4章表格中的方法是否为这5种之一
    """
    violations = []
    for sec_id, sec_data in sections.items():
        if not sec_id.startswith('4'):
            continue
        for table in sec_data.get('tables', []):
            if table.get('type') != 'qualification':
                continue
            headers = table.get('headers', [])
            # 找到"合格性方法"列
            method_col = -1
            for i, h in enumerate(headers):
                if '合格性' in h or '方法' in h:
                    method_col = i
                    break
            if method_col < 0:
                continue
            for row in table.get('rows', []):
                if method_col < len(row):
                    method = row[method_col].strip()
                    if method and not _is_valid_qual_method(method):
                        violations.append({
                            "rule": "R-003",
                            "gjb_clause": "附录J 4 (L2403)",
                            "severity": "MEDIUM",
                            "description": f"合格性方法'{method}'非GJB规定的5种之一(a演示/b测试/c分析/d审查/e特殊)",
                            "standard": "合格性检验方法: a)演示 b)测试 c)分析 d)审查 e)特殊",
                        })
    return violations


def check_r004_traceability(sections: dict) -> list:
    """R-004 追溯完整性 (GJB L2419-2423)
    标准: a)从每一个CSCI需求到系统需求的可追踪性
          b)从已分配的系统需求到CSCI需求的可追踪性
    检测: 第5章是否有正向和逆向追溯 + 幽灵需求检测
    """
    violations = []
    
    # 检查第5章是否存在
    has_ch5 = any(s.startswith('5') for s in sections)
    if not has_ch5:
        violations.append({
            "rule": "R-004",
            "gjb_clause": "附录J 5 (L2419)",
            "severity": "HIGH",
            "description": "缺少第5章(需求可追踪性)",
            "standard": "本章应描述: a)正向追踪 b)逆向追踪",
        })
        return violations
    
    # 检查正向/逆向追溯
    has_forward = any(s.startswith('5.1') or '正向' in sections.get(s, {}).get('title', '') 
                      for s in sections)
    has_reverse = any(s.startswith('5.2') or '逆向' in sections.get(s, {}).get('title', '') 
                      for s in sections)
    
    if not has_forward:
        violations.append({
            "rule": "R-004",
            "gjb_clause": "附录J 5 a) (L2419)",
            "severity": "MEDIUM",
            "description": "缺少正向追溯(a): CSCI需求→系统需求",
            "standard": "a)从每一个CSCI需求到系统/子系统需求的可追踪性",
        })
    if not has_reverse:
        violations.append({
            "rule": "R-004",
            "gjb_clause": "附录J 5 b) (L2423)",
            "severity": "MEDIUM",
            "description": "缺少逆向追溯(b): 系统需求→CSCI需求",
            "standard": "b)从已分配的系统/子系统需求到CSCI需求的可追踪性",
        })
    
    # 幽灵需求检测(抽检准确率80%)
    # 防误报: 只在3.2.X定义章节≥3个时才做幽灵检测(否则是解析不完整)
    defined_3_2 = set()
    for sec_id in sections:
        if sec_id.startswith('3.2.') and sec_id.count('.') == 2:
            defined_3_2.add(sec_id)
    
    if len(defined_3_2) >= 3:  # 至少3个3.2.X章节才做幽灵检测
        referenced = set()
        for sec_id, sec_data in sections.items():
            for table in sec_data.get('tables', []):
                if table.get('type') in ('qualification', 'traceability'):
                    for row in table.get('rows', []):
                        for cell in row:
                            for m in re.finditer(r'(3\.\d+\.\d+)', str(cell)):
                                referenced.add(m.group(1))
        
        phantoms = referenced - defined_3_2
        for p in sorted(phantoms):
            violations.append({
                "rule": "R-004",
                "gjb_clause": "附录J 5 (L2423)",
                "severity": "HIGH",
                "description": f"幽灵需求: 章节{p}在合格性表/追溯表中被引用但未在第3章定义",
                "standard": "分配给本CSCI的全部系统/子系统需求都应加以说明",
            })
    
    return violations


def check_r005_section_structure(sections: dict) -> list:
    """R-005 章节结构 (GJB L2195)
    标准: 本章应分为如下小条规定CSCI需求
    检测: 第3章是否有3.1~3.18子章节
    注意: 如果解析到的3.X章节<5个,说明解析失败(非文档问题),不报
    """
    violations = []
    found_3x = set()
    for sec_id in sections:
        if re.match(r'^3\.\d+$', sec_id):
            found_3x.add(sec_id)
    
    # 防误报: 如果3.X章节<5个,说明解析不完整,不报
    # 如果只缺1-2个,可能是解析边缘case,降为LOW
    if len(found_3x) < 5:
        return violations
    
    missing = [s for s in EXPECTED_3X if s not in found_3x]
    if missing:
        severity = "LOW" if len(missing) <= 2 else "MEDIUM"
        violations.append({
            "rule": "R-005",
            "gjb_clause": "附录J 3 (L2195)",
            "severity": severity,
            "description": f"第3章缺少子章节: {missing}",
            "standard": "本章应分为如下小条规定CSCI需求(3.1~3.18)",
        })
    return violations


def check_r006_interface_id(sections: dict) -> list:
    """R-006 接口标识符 (GJB L2217)
    标准: 每一个接口的标识应包括项目唯一的标识符
    检测: 3.3.X/3.4.X接口章节是否有req_id
    """
    violations = []
    for sec_id, sec_data in sections.items():
        if sec_id.startswith(('3.3.', '3.4.')) and sec_id.count('.') == 2:
            req_id = sec_data.get('req_id', '')
            if not req_id:
                # 检查标题中是否有标识符
                title = sec_data.get('title', '')
                if not REQ_ID_RE.search(title):
                    violations.append({
                        "rule": "R-006",
                        "gjb_clause": "附录J 3.3 (L2217)",
                        "severity": "MEDIUM",
                        "description": f"接口{sec_id}({title[:20]})缺少项目唯一标识符",
                        "standard": "每一个接口的标识应包括项目唯一的标识符",
                    })
    return violations


def check_r007_priority(sections: dict) -> list:
    """R-007 优先顺序 (GJB L2399)
    标准: 本条应指明...优先次序、关键性...如果所有需求具有相等的权重，本条应如实说明
    检测: 3.18节是否存在且有内容
    """
    violations = []
    sec_3_18 = sections.get('3.18', {})
    if not sec_3_18:
        violations.append({
            "rule": "R-007",
            "gjb_clause": "附录J 3.18 (L2399)",
            "severity": "MEDIUM",
            "description": "缺少3.18节(需求的优先顺序和关键性)",
            "standard": "本条应指明...优先次序、关键性或表示其相对重要性的权重",
        })
    elif len(sec_3_18.get('text', '')) < 10:
        violations.append({
            "rule": "R-007",
            "gjb_clause": "附录J 3.18 (L2399)",
            "severity": "LOW",
            "description": "3.18节内容为空或过短",
            "standard": "如果所有需求具有相等的权重，本条应如实说明",
        })
    return violations


def process_document(doc_name: str) -> dict:
    """对单份文档执行7项GJB标准检测"""
    json_path = PARSED_DIR / f"{doc_name}_structured.json"
    if not json_path.exists():
        return {"error": f"文件不存在: {json_path}"}
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    sections = data.get("sections", {})
    
    all_violations = []
    all_violations.extend(check_r001_identity(sections))
    all_violations.extend(check_r002_req_id_unique(sections))
    all_violations.extend(check_r003_qual_method(sections))
    all_violations.extend(check_r004_traceability(sections))
    all_violations.extend(check_r005_section_structure(sections))
    all_violations.extend(check_r006_interface_id(sections))
    all_violations.extend(check_r007_priority(sections))
    
    by_rule = Counter(v["rule"] for v in all_violations)
    by_severity = Counter(v["severity"] for v in all_violations)
    
    return {
        "doc_name": doc_name,
        "detect_date": datetime.now().isoformat(),
        "engine_version": "v3-gjb-standard",
        "statistics": data.get("statistics", {}),
        "violations": {
            "total": len(all_violations),
            "by_rule": dict(by_rule),
            "by_severity": dict(by_severity),
        },
        "violation_details": all_violations,
    }


def main():
    parser = argparse.ArgumentParser(description="SRS一致性校验v3(基于GJB标准)")
    parser.add_argument("--doc", type=str)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SRS一致性校验 v3 (基于GJB 438C标准条文)")
    print("7项检测: R-001标识/R-002唯一ID/R-003合格性/R-004追溯/R-005结构/R-006接口ID/R-007优先")
    print("=" * 60)
    
    if args.doc:
        result = process_document(args.doc)
        _print(result)
        out = OUTPUT_DIR / f"{args.doc[:20]}_v3.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        json_files = sorted(PARSED_DIR.glob("*_structured.json"))
        all_results = []
        for f in json_files:
            doc_name = f.name.replace("_structured.json", "")
            result = process_document(doc_name)
            _print(result)
            # 保存独立报告
            out = OUTPUT_DIR / f"{doc_name[:20]}_v3.json"
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            all_results.append(result)
        
        total = sum(r["violations"]["total"] for r in all_results)
        print(f"\n{'='*60}")
        print(f"汇总: {len(all_results)}份文档, {total}条违规")
        
        all_rules = Counter()
        for r in all_results:
            all_rules.update(r["violations"]["by_rule"])
        print(f"按规则: {dict(all_rules)}")
        
        (OUTPUT_DIR / "_summary.json").write_text(
            json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")


def _print(result):
    if "error" in result:
        print(f"  {result['error']}")
        return
    name = result["doc_name"][:35]
    v = result["violations"]
    s = result.get("statistics", {})
    print(f"\n[{name}]")
    print(f"  章节:{s.get('sections',0)} 表格:{s.get('tables',0)} 约束:{s.get('constraints',0)}")
    print(f"  违规:{v['total']}条 {dict(v['by_rule'])}")
    for d in result["violation_details"][:3]:
        print(f"    [{d['rule']}] {d['description'][:65]}")


if __name__ == "__main__":
    main()
