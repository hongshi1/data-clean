#!/usr/bin/env python3
"""
SRS 关联对发现模块
===================
从 SRS 文档的 sections/constraints/tables/images 中自动发现
"应该被配对检测不一致"的内容对 (Pair)。

这是两步流水线的 Step 1: 配对与判定解耦, pair 是一等数据结构。

6种关联对类型:
  1. same_param    — 同参数多处出现
  2. text_table    — 正文值↔表格值
  3. logic         — 约束间逻辑矛盾(串行/累积/时序)
  4. cross_section — 跨章节语义矛盾(3.12↔3.2.X)
  5. image_text    — 图文配对
  6. cross_doc     — 跨文档同实体

用法:
  python3 tools/srs_pair_discovery.py                    # 发现3份Gold Standard文档的pairs
  python3 tools/srs_pair_discovery.py --doc scheduler_srs # 单文档
  python3 tools/srs_pair_discovery.py --evaluate          # 发现+对齐GT评估
"""
import json
import re
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict, Counter
from itertools import combinations

BASE = Path(__file__).resolve().parent.parent
CONSTRAINTS_DIR = BASE / "data/gjb_438c/extracted_constraints"
TABLES_DIR = BASE / "data/gjb_438c/extracted_tables"
PROCESSED_DIR = BASE / "data/gjb_438c/processed_documents"
GOLD_STANDARD_DIR = BASE / "data/gjb_438c/gold_standard"
OUTPUT_DIR = BASE / "data/gjb_438c/pair_discovery"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 同义词典 (从标准化后约束数据扩展, 覆盖全部20+变体)
PARAM_SYNONYMS = {
    "周期": ["周期", "运行周期", "执行周期", "步进函数调用周期", "步长", "离散时间步长",
             "时间步长", "调度周期", "调用周期", "定时器周期", "主循环周期", "驱动周期",
             "内部数据周期", "平均周期", "interval_ms", "打印周期", "脉冲切换周期",
             "输出降采样间隔", "DT"],
    "执行时间": ["单循环执行时间", "单步执行总时间", "单步计算时间", "计算时间",
                "补偿计算时间", "查询时间", "打印阻塞时间", "分析时间", "任务执行时间",
                "循环执行时间", "编译时间"],
    "定时误差": ["单次定时误差", "定时误差", "总时间误差", "时间漂移", "漂移误差"],
    "CPU占用率": ["CPU占用率", "CPU使用率", "处理机占用率", "处理器使用率"],
    "内存占用": ["内存占用", "运行时内存占用"],
    "SOC": ["SOC", "SOC_init", "SOC值", "SOC计算范围", "soc_init", "荷电状态 soc", "荷电状态soc"],
    "容量Q": ["Q", "容量Q"],
    "开路电压E0": ["E0", "开路电压常数E0"],
    "内阻R": ["R", "内阻R"],
    "极化系数M": ["M", "极化系数M"],
    "指数区时间常数B": ["B", "指数区时间常数B"],
    "指数区幅值A": ["A", "指数区幅值A"],
    "主频": ["主频"],
    "响应时间": ["响应时间", "延迟", "时延", "RTT"],
    "吞吐量": ["吞吐量", "吞吐时间", "吞吐率"],
}

# 反向映射: param_name → canonical
_PARAM_CANONICAL = {}
for canonical, syns in PARAM_SYNONYMS.items():
    for s in syns:
        _PARAM_CANONICAL[s] = canonical
    _PARAM_CANONICAL[canonical] = canonical


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class Ref:
    """内容引用 — 指向文档中的具体位置"""
    doc: str
    section: str             # 章节号 "3.2.1"
    section_title: str = ""
    line: int = 0
    text: str = ""
    ref_type: str = "constraint"  # constraint/table_cell/section_text/image/requirement

@dataclass
class Pair:
    """关联对"""
    pair_id: str
    pair_type: str           # same_param/text_table/logic/cross_section/image_text/cross_doc
    source: Ref
    target: Ref
    discovery_method: str    # param_group/section_match/serial_relation/llm/reference_extract
    confidence: float = 1.0
    context: dict = field(default_factory=dict)  # {param_name, table_type, relation_type, ...}


# ── 工具函数 ──────────────────────────────────────────────────

def parse_section_number(section_str: str) -> str:
    """从 '3.2.1 标识' 提取 '3.2.1'"""
    if not section_str:
        return ""
    m = re.match(r'(\d+(?:\.\w+)*)', section_str.strip())
    return m.group(1) if m else ""


def parse_section_title(section_str: str) -> str:
    """从 '3.2.1 标识' 提取 '标识'"""
    if not section_str:
        return ""
    m = re.match(r'\d+(?:\.\w+)*\s*(.*)', section_str.strip())
    return m.group(1).strip() if m else section_str.strip()


def canonical_param(param_name: str) -> str:
    """参数名归一化到canonical"""
    if not param_name:
        return ""
    # 精确匹配
    if param_name in _PARAM_CANONICAL:
        return _PARAM_CANONICAL[param_name]
    # 模糊匹配(包含关系)
    for canonical, syns in PARAM_SYNONYMS.items():
        for s in syns:
            if s in param_name or param_name in s:
                return canonical
    return param_name  # 无法归一化则原样返回


def load_constraints(doc: str) -> list[dict]:
    """加载约束, 统一字段名 (section_number → section)"""
    path = CONSTRAINTS_DIR / f"{doc}_constraints.json"
    if not path.exists():
        return []
    constraints = json.loads(path.read_text(encoding="utf-8")).get("constraints", [])
    # 字段名统一: section_number/section_title/line_start → section/line
    for c in constraints:
        if not c.get("section"):
            c["section"] = c.get("section_number", "") or c.get("section_title", "")
        if not c.get("line"):
            c["line"] = c.get("line_start", 0)
        if not c.get("original"):
            c["original"] = c.get("sentence", "")
    return constraints


def load_tables(doc: str) -> list[dict]:
    """加载表格"""
    path = TABLES_DIR / f"{doc}_tables.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("tables", [])


def load_sections(doc: str) -> list[dict]:
    """加载章节"""
    path = PROCESSED_DIR / f"{doc}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("sections", [])


def constraint_to_ref(c: dict, doc: str) -> Ref:
    """约束dict → Ref (兼容 section / section_number 两种字段名)"""
    sec = c.get("section_number") or c.get("section", "")
    return Ref(
        doc=doc,
        section=parse_section_number(sec),
        section_title=parse_section_title(sec),
        line=c.get("line_start", c.get("line", 0)),
        text=c.get("original", c.get("sentence", "")),
        ref_type="constraint",
    )


# ── 发现器1: 同参数对 (same_param) ────────────────────────────

def discover_same_param_pairs(constraints: list[dict], doc: str) -> list[Pair]:
    """
    发现同参数多处出现的配对.
    策略: 按canonical_param分组, 同组内两两配对.
    """
    pairs = []
    # 按canonical param分组
    param_groups = defaultdict(list)
    for c in constraints:
        param_raw = c.get("param", "")
        if not param_raw:
            continue
        canonical = canonical_param(param_raw)
        # 只对有数值的约束分组
        if c.get("value") is not None and str(c.get("value", "")).strip():
            param_groups[canonical].append(c)
    
    seq = 0
    for param, group in param_groups.items():
        if len(group) < 2:
            continue
        # 同组内两两配对
        for c1, c2 in combinations(group, 2):
            seq += 1
            pairs.append(Pair(
                pair_id=f"PAIR-{doc}-{seq:04d}",
                pair_type="same_param",
                source=constraint_to_ref(c1, doc),
                target=constraint_to_ref(c2, doc),
                discovery_method="param_group",
                confidence=1.0,
                context={
                    "param_name": param,
                    "source_value": c1.get("value"),
                    "target_value": c2.get("value"),
                    "source_unit": c1.get("unit", ""),
                    "target_unit": c2.get("unit", ""),
                }
            ))
    
    return pairs


# ── 发现器2: 文本-表格对 (text_table) ─────────────────────────

def discover_text_table_pairs(constraints: list[dict], tables: list[dict], doc: str) -> list[Pair]:
    """
    发现正文值↔表格值的配对.
    策略: 约束section ↔ 表格section按章节号匹配, 在表格中找param.
    """
    pairs = []
    seq = 0
    
    for c in constraints:
        c_sec = parse_section_number(c.get("section", ""))
        c_param = canonical_param(c.get("param", ""))
        if not c_sec or not c_param:
            continue
        
        for t in tables:
            t_sec = parse_section_number(t.get("section", ""))
            t_type = t.get("table_type", "")
            
            # 策略1: 合格性表(qualification) — 按章节号匹配constraint
            if t_type == "qualification":
                # 在qualification表的行中找包含c_sec的行
                for row in t.get("rows", []):
                    row_text = " ".join(str(cell) for cell in row)
                    # 检查行中是否包含约束的章节号
                    if c_sec in row_text:
                        seq += 1
                        pairs.append(Pair(
                            pair_id=f"PAIR-{doc}-{seq:04d}",
                            pair_type="text_table",
                            source=constraint_to_ref(c, doc),
                            target=Ref(
                                doc=doc, section=t_sec, section_title=t_type,
                                line=t.get("line", 0),
                                text=row_text[:200], ref_type="table_cell"
                            ),
                            discovery_method="section_match",
                            confidence=0.8,
                            context={
                                "param_name": c_param,
                                "table_type": t_type,
                                "constraint_value": c.get("value"),
                            }
                        ))
                        break  # 一个约束匹配一行即可
            
            # 策略2: 追溯表(traceability) — 约束值在表格中搜索
            elif t_type == "traceability":
                for row in t.get("rows", []):
                    row_text = " ".join(str(cell) for cell in row)
                    c_value = str(c.get("value", ""))
                    if c_value and len(c_value) > 2 and c_value in row_text:
                        seq += 1
                        pairs.append(Pair(
                            pair_id=f"PAIR-{doc}-{seq:04d}",
                            pair_type="text_table",
                            source=constraint_to_ref(c, doc),
                            target=Ref(
                                doc=doc, section=t_sec, section_title=t_type,
                                line=t.get("line", 0),
                                text=row_text[:200], ref_type="table_cell"
                            ),
                            discovery_method="value_match",
                            confidence=0.7,
                            context={
                                "param_name": c_param,
                                "table_type": t_type,
                                "matched_value": c_value,
                            }
                        ))
                        break
    
    return pairs


# ── 发现器3: 逻辑约束对 (logic) ───────────────────────────────

def discover_logic_pairs(constraints: list[dict], doc: str) -> list[Pair]:
    """
    发现可能存在逻辑矛盾的约束配对.
    策略:
      1. 同param约束对(继承same_param)
      2. 串行关系: 同一3.2.X子节内的执行时间 → Sum<=总预算
      3. 资源约束: 3.11.x硬件能力 vs 3.11.x使用上限
      4. 时序关系: 周期/频率相关约束
    """
    pairs = []
    seq = 0
    
    # 策略1: 同param逻辑对 (只对有operator的约束)
    param_groups = defaultdict(list)
    for c in constraints:
        param = canonical_param(c.get("param", ""))
        if param and c.get("value") is not None:
            param_groups[param].append(c)
    
    for param, group in param_groups.items():
        if len(group) < 2:
            continue
        for c1, c2 in combinations(group, 2):
            seq += 1
            pairs.append(Pair(
                pair_id=f"PAIR-{doc}-{seq:04d}",
                pair_type="logic",
                source=constraint_to_ref(c1, doc),
                target=constraint_to_ref(c2, doc),
                discovery_method="same_param_logic",
                confidence=0.8,
                context={
                    "param_name": param,
                    "relation_type": "same_param_constraint",
                    "source_value": c1.get("value"),
                    "target_value": c2.get("value"),
                }
            ))
    
    # 策略2: 串行关系 (3.2.X子节的执行时间 vs 总预算)
    exec_time_params = PARAM_SYNONYMS.get("执行时间", [])
    exec_constraints = [c for c in constraints
                        if any(p in c.get("param", "") for p in exec_time_params)
                        or "执行时间" in c.get("original", "")]
    # 找总预算约束(含"总"/"不超过"/"上限"的约束)
    budget_constraints = [c for c in constraints
                          if any(kw in c.get("original", "") for kw in ["总", "不超过", "上限", "最多", "至多"])
                          and c not in exec_constraints]
    
    for ec in exec_constraints:
        for bc in budget_constraints:
            # 避免同section重复
            if parse_section_number(ec.get("section","")) == parse_section_number(bc.get("section","")):
                continue
            seq += 1
            pairs.append(Pair(
                pair_id=f"PAIR-{doc}-{seq:04d}",
                pair_type="logic",
                source=constraint_to_ref(ec, doc),
                target=constraint_to_ref(bc, doc),
                discovery_method="serial_relation",
                confidence=0.7,
                context={
                    "relation_type": "serial_sum_vs_budget",
                    "exec_param": ec.get("param"),
                    "budget_text": bc.get("original", "")[:60],
                }
            ))
    
    # 策略3: 资源约束 (3.11.x)
    resource_constraints = [c for c in constraints
                            if parse_section_number(c.get("section", "")).startswith("3.11")]
    if len(resource_constraints) >= 2:
        for c1, c2 in combinations(resource_constraints, 2):
            # 硬件能力 vs 使用上限
            s1 = c1.get("section", "")
            s2 = c2.get("section", "")
            if "3.11.1" in s1 and "3.11.2" in s2 or "3.11.1" in s2 and "3.11.1" in s1:
                seq += 1
                pairs.append(Pair(
                    pair_id=f"PAIR-{doc}-{seq:04d}",
                    pair_type="logic",
                    source=constraint_to_ref(c1, doc),
                    target=constraint_to_ref(c2, doc),
                    discovery_method="resource_relation",
                    confidence=0.8,
                    context={"relation_type": "hw_capacity_vs_usage"}
                ))
    
    # 策略4: 周期↔执行时间 (时序关系)
    period_params = PARAM_SYNONYMS.get("周期", [])
    period_constraints = [c for c in constraints
                          if any(p in c.get("param", "") for p in period_params)]
    for pc in period_constraints:
        for ec in exec_constraints:
            if parse_section_number(pc.get("section","")) != parse_section_number(ec.get("section","")):
                seq += 1
                pairs.append(Pair(
                    pair_id=f"PAIR-{doc}-{seq:04d}",
                    pair_type="logic",
                    source=constraint_to_ref(pc, doc),
                    target=constraint_to_ref(ec, doc),
                    discovery_method="temporal_relation",
                    confidence=0.7,
                    context={"relation_type": "period_vs_exec_time"}
                ))
    
    return pairs


# ── 发现器4: 跨章节语义对 (cross_section) ─────────────────────

def discover_cross_section_pairs(constraints: list[dict], sections: list[dict], doc: str) -> list[Pair]:
    """
    发现跨章节语义矛盾配对.
    策略:
      1. 设计约束(3.12) vs 能力需求(3.2.X) — 章节依赖
      2. 同param出现在不同层章节
    """
    pairs = []
    seq = 0
    
    # 策略1: 3.12设计约束 vs 3.2.X能力需求
    design_constraints = [c for c in constraints
                          if parse_section_number(c.get("section", "")).startswith("3.12")]
    capability_constraints = [c for c in constraints
                              if parse_section_number(c.get("section", "")).startswith("3.2")]
    
    for dc in design_constraints:
        for cc in capability_constraints:
            seq += 1
            pairs.append(Pair(
                pair_id=f"PAIR-{doc}-{seq:04d}",
                pair_type="cross_section",
                source=constraint_to_ref(dc, doc),
                target=constraint_to_ref(cc, doc),
                discovery_method="section_dependency",
                confidence=0.6,
                context={
                    "relation_type": "design_constraint_vs_capability",
                    "design_section": parse_section_number(dc.get("section", "")),
                    "capability_section": parse_section_number(cc.get("section", "")),
                }
            ))
    
    # 策略2: 同param跨章节 (非3.12 vs 3.2的已覆盖)
    param_sections = defaultdict(list)
    for c in constraints:
        param = canonical_param(c.get("param", ""))
        sec = parse_section_number(c.get("section", ""))
        if param and sec:
            param_sections[param].append((sec, c))
    
    for param, locations in param_sections.items():
        if len(locations) < 2:
            continue
        loc_list = locations  # 已经是list
        for (s1, c1), (s2, c2) in combinations(loc_list, 2):
            # 跳过同section的(已被same_param覆盖)
            if s1 == s2:
                continue
            # 跳过3.12 vs 3.2的(已被策略1覆盖)
            if s1.startswith("3.12") and s2.startswith("3.2"):
                continue
            if s2.startswith("3.12") and s1.startswith("3.2"):
                continue
            seq += 1
            pairs.append(Pair(
                pair_id=f"PAIR-{doc}-{seq:04d}",
                pair_type="cross_section",
                source=constraint_to_ref(c1, doc),
                target=constraint_to_ref(c2, doc),
                discovery_method="param_cross_section",
                confidence=0.7,
                context={
                    "param_name": param,
                    "source_section": s1,
                    "target_section": s2,
                }
            ))
    
    return pairs


# ── 发现器5: 图文对 (image_text) ──────────────────────────────

def discover_image_text_pairs(doc: str) -> list[Pair]:
    """
    发现图文配对.
    策略: 从processed_documents或mineru解析中提取图片引用.
    """
    pairs = []
    seq = 0
    
    # 从processed_documents加载sections (含text_preview)
    sections = load_sections(doc)
    
    # 搜索"如图X所示"模式
    fig_ref_re = re.compile(r'(?:如|见)?图\s*(\d+[\.\-]?\d*)\s*(?:所示|中)')
    
    for sec in sections:
        text = sec.get("text_preview", "") + " " + sec.get("text", "")
        refs = fig_ref_re.findall(text)
        for fig_num in refs:
            seq += 1
            pairs.append(Pair(
                pair_id=f"PAIR-{doc}-{seq:04d}",
                pair_type="image_text",
                source=Ref(
                    doc=doc,
                    section=sec.get("number", ""),
                    section_title=sec.get("title", ""),
                    line=sec.get("line_start", 0),
                    text=text[:200],
                    ref_type="section_text",
                ),
                target=Ref(
                    doc=doc,
                    section=sec.get("number", ""),
                    section_title=f"图{fig_num}",
                    line=0,
                    text=f"图{fig_num}",
                    ref_type="image",
                ),
                discovery_method="reference_extract",
                confidence=0.9,
                context={"figure_number": fig_num}
            ))
    
    return pairs


# ── 发现器6: 跨文档对 (cross_doc) ─────────────────────────────

def discover_cross_doc_pairs(all_docs_constraints: dict[str, list[dict]]) -> list[Pair]:
    """
    发现跨文档同实体配对.
    策略: 同canonical param在不同文档中的约束配对.
    """
    pairs = []
    seq = 0
    
    # 按canonical param分组, 跨文档
    param_by_doc = defaultdict(lambda: defaultdict(list))
    for doc, constraints in all_docs_constraints.items():
        for c in constraints:
            param = canonical_param(c.get("param", ""))
            if param and c.get("value") is not None:
                param_by_doc[param][doc].append(c)
    
    for param, doc_groups in param_by_doc.items():
        if len(doc_groups) < 2:
            continue
        docs = list(doc_groups.keys())
        for d1, d2 in combinations(docs, 2):
            for c1 in doc_groups[d1]:
                for c2 in doc_groups[d2]:
                    seq += 1
                    pairs.append(Pair(
                        pair_id=f"PAIR-CROSSDOC-{seq:04d}",
                        pair_type="cross_doc",
                        source=constraint_to_ref(c1, d1),
                        target=constraint_to_ref(c2, d2),
                        discovery_method="cross_doc_param",
                        confidence=0.8,
                        context={
                            "param_name": param,
                            "source_doc": d1,
                            "target_doc": d2,
                        }
                    ))
    
    return pairs


# ── 主流程 ────────────────────────────────────────────────────

def discover_all_pairs(doc: str) -> list[Pair]:
    """发现单文档的所有关联对"""
    constraints = load_constraints(doc)
    tables = load_tables(doc)
    sections = load_sections(doc)
    
    pairs = []
    pairs += discover_same_param_pairs(constraints, doc)
    pairs += discover_text_table_pairs(constraints, tables, doc)
    pairs += discover_logic_pairs(constraints, doc)
    pairs += discover_cross_section_pairs(constraints, sections, doc)
    pairs += discover_image_text_pairs(doc)
    
    return pairs


def evaluate_against_gt(doc: str, pairs: list[Pair]) -> dict:
    """将发现的pairs与Gold Standard对齐评估"""
    gt_path = GOLD_STANDARD_DIR / f"{doc}_gold.json"
    if not gt_path.exists():
        return {}
    
    gt_data = json.loads(gt_path.read_text(encoding="utf-8"))
    ground_truths = gt_data.get("ground_truths", [])
    
    # 从GT提取期望配对
    expected_pairs = []
    for gt in ground_truths:
        sections = gt.get("location", {}).get("sections", [])
        gt_type = gt.get("type", "")
        is_conflict = gt.get("is_conflict", False)
        
        # GT type → pair_type映射
        pair_type_map = {
            "same_param_same_value": "same_param",
            "same_value_diff_semantics": "same_param",
            "text_table_conflict": "text_table",
            "logic_contradiction": "cross_section",
            "logic_unsatisfiable": "logic",
            "logic_satisfiable": "logic",
            "logic_incomplete": "logic",
            "cross_document_conflict": "cross_doc",
        }
        expected_pair_type = pair_type_map.get(gt_type, "")
        
        # GT的sections列表隐含配对: 所有section两两组合
        for s1, s2 in combinations(sections, 2):
            expected_pairs.append({
                "gt_id": gt.get("gt_id", ""),
                "source_section": s1,
                "target_section": s2,
                "pair_type": expected_pair_type,
                "is_conflict": is_conflict,
                "gt_type": gt_type,
            })
    
    # 匹配: 发现的pair vs 期望pair
    matched_expected = set()
    matched_discovered = set()
    
    for i, ep in enumerate(expected_pairs):
        for j, p in enumerate(pairs):
            # section匹配(双向)
            src_match = (p.source.section == ep["source_section"] and p.target.section == ep["target_section"])
            rev_match = (p.source.section == ep["target_section"] and p.target.section == ep["source_section"])
            # pair_type匹配(宽松: logic可匹配cross_section)
            type_match = (p.pair_type == ep["pair_type"] or
                          (p.pair_type in ("logic", "cross_section") and ep["pair_type"] in ("logic", "cross_section")))
            
            if (src_match or rev_match) and type_match:
                matched_expected.add(i)
                matched_discovered.add(j)
                break
    
    # 统计
    tp = len(matched_expected)  # 期望pair被发现
    fn = len(expected_pairs) - tp  # 期望pair未被发现
    fp = len(pairs) - len(matched_discovered)  # 发现的pair不在期望中(可能额外发现)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "doc": doc,
        "total_gt_pairs": len(expected_pairs),
        "total_discovered_pairs": len(pairs),
        "matched": tp,
        "fn": fn,
        "extra_discovered": fp,
        "pair_precision": round(precision, 4),
        "pair_recall": round(recall, 4),
        "pair_f1": round(f1, 4),
        "unmatched_gt": [expected_pairs[i] for i in range(len(expected_pairs)) if i not in matched_expected],
    }


def main():
    parser = argparse.ArgumentParser(description="SRS关联对发现模块")
    parser.add_argument("--doc", type=str, help="单文档")
    parser.add_argument("--evaluate", action="store_true", help="对齐GT评估")
    args = parser.parse_args()
    
    print("=" * 70)
    print("SRS 关联对发现模块")
    print("=" * 70)
    
    docs = [args.doc] if args.doc else ["battery_srs", "compiler_srs", "scheduler_srs"]
    
    all_pairs_by_doc = {}
    for doc in docs:
        print(f"\n[{doc}]")
        pairs = discover_all_pairs(doc)
        all_pairs_by_doc[doc] = pairs
        
        # 按type统计
        by_type = Counter(p.pair_type for p in pairs)
        print(f"  发现pairs: {len(pairs)}")
        print(f"  按类型: {dict(by_type)}")
        
        # 抽样
        for ptype in ["same_param", "text_table", "logic", "cross_section"]:
            sample = next((p for p in pairs if p.pair_type == ptype), None)
            if sample:
                print(f"  [{ptype}] {sample.source.section}↔{sample.target.section} "
                      f"(method={sample.discovery_method}, conf={sample.confidence})")
        
        if args.evaluate:
            eval_result = evaluate_against_gt(doc, pairs)
            if eval_result:
                print(f"  GT对齐: P={eval_result['pair_precision']:.1%} R={eval_result['pair_recall']:.1%} "
                      f"F1={eval_result['pair_f1']:.1%} (GT期望{eval_result['total_gt_pairs']}对, 发现{eval_result['total_discovered_pairs']}对)")
                if eval_result["unmatched_gt"]:
                    print(f"  未匹配GT ({len(eval_result['unmatched_gt'])} 对):")
                    for ug in eval_result["unmatched_gt"][:5]:
                        print(f"    {ug['gt_id']} {ug['source_section']}↔{ug['target_section']} type={ug['pair_type']}")
    
    # 跨文档对
    if len(docs) >= 2:
        print(f"\n[跨文档对]")
        all_constraints = {doc: load_constraints(doc) for doc in docs}
        cross_pairs = discover_cross_doc_pairs(all_constraints)
        print(f"  跨文档pairs: {len(cross_pairs)}")
        if cross_pairs:
            sample = cross_pairs[0]
            print(f"  示例: {sample.source.doc}:{sample.source.section} ↔ {sample.target.doc}:{sample.target.section}")
    
    # 保存
    output = {
        doc: [asdict(p) for p in pairs]
        for doc, pairs in all_pairs_by_doc.items()
    }
    output_path = OUTPUT_DIR / "discovered_pairs.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已保存: {output_path.relative_to(BASE)}")


if __name__ == "__main__":
    main()
