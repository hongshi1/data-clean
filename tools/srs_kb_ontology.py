#!/usr/bin/env python3
"""
GJB 438C 知识库本体定义
========================
用 Pydantic 定义节点/边的类型注册表和约束表, 替代旧的 **props 自由字段。

设计原则:
  1. 类型注册表: 所有 NodeType/RelationType 枚举化, 不再硬编码字符串
  2. 关系约束: VALID_EDGES 声明哪些 (源类型, 关系, 目标类型) 合法
  3. 溯源强制: 每个标准层节点必须有 ocr_evidence 字段(OCR行号)
  4. 可验证: validate_graph() 能检查任意图谱是否符合本体

用法:
  from srs_kb_ontology import NodeType, RelationType, VALID_EDGES, validate_node
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


# ── 节点类型枚举 (15类, 从旧17类精简统一) ─────────────────────

class NodeType(str, Enum):
    # 标准层 (静态知识, GJB 438C 定义)
    STANDARD = "Standard"                    # GJB标准本身
    DOCUMENT_TYPE = "DocumentType"           # 20种文档类型
    SECTION_TEMPLATE = "SectionTemplate"     # GJB章节模板(附录J)
    RULE = "Rule"                            # 规则(120条, 统一类型, 用type字段区分)
    PARAMETER = "Parameter"                  # 性能参数(23个)
    INTERFACE_TYPE = "InterfaceType"         # 接口类型(13个)
    CONSTRAINT_PATTERN = "ConstraintPattern" # 约束模式(Z3模板)
    UNIT_FAMILY = "UnitFamily"               # 单位族(10个)
    REQUIRED_FIELD = "RequiredField"         # 章节必含字段
    # 文档层 (可变, 来自SRS文档解析)
    DOCUMENT = "Document"                    # SRS文档实例
    SECTION = "Section"                      # 文档章节(带编号)
    REQUIREMENT = "Requirement"              # 需求项
    TABLE = "Table"                          # 表格实例
    CONSTRAINT = "Constraint"                # 约束实例
    FIGURE = "Figure"                        # 图表实例
    # 检测层 (按需生成)
    VIOLATION = "Violation"                  # 违规/冲突


# ── 边关系类型枚举 (16种, 统一大驼峰) ─────────────────────────

class RelationType(str, Enum):
    # 标准层内部
    DEFINES_TYPE = "DEFINES_TYPE"
    HAS_TEMPLATE = "HAS_TEMPLATE"
    MUST_CONTAIN = "MUST_CONTAIN"
    HAS_RULE = "HAS_RULE"
    REQUIRES_PARAMETER = "REQUIRES_PARAMETER"
    HAS_UNIT = "HAS_UNIT"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    ALIGNS_WITH = "ALIGNS_WITH"
    IMPLIES_PATTERN = "IMPLIES_PATTERN"
    # 文档层内部
    HAS_SECTION = "HAS_SECTION"
    CONTAINS_REQUIREMENT = "CONTAINS_REQUIREMENT"
    CONTAINS_TABLE = "CONTAINS_TABLE"
    CONTAINS_FIGURE = "CONTAINS_FIGURE"
    HAS_CONSTRAINT = "HAS_CONSTRAINT"
    # 跨层 (文档↔标准)
    COMPLIES_WITH_TEMPLATE = "COMPLIES_WITH_TEMPLATE"
    SATISFIES_RULE = "SATISFIES_RULE"
    REFERENCES_DOCUMENT = "REFERENCES_DOCUMENT"
    TRACES_TO = "TRACES_TO"
    # 跨层 (检测)
    VIOLATES = "VIOLATES"
    DETECTED_BY = "DETECTED_BY"


# ── 关系约束表: 哪些 (源类型, 关系, 目标类型) 合法 ─────────────

VALID_EDGES: set[tuple[NodeType, RelationType, NodeType]] = {
    # 标准层内部
    (NodeType.STANDARD, RelationType.DEFINES_TYPE, NodeType.DOCUMENT_TYPE),
    (NodeType.STANDARD, RelationType.HAS_TEMPLATE, NodeType.SECTION_TEMPLATE),
    (NodeType.SECTION_TEMPLATE, RelationType.HAS_TEMPLATE, NodeType.SECTION_TEMPLATE),
    (NodeType.SECTION_TEMPLATE, RelationType.MUST_CONTAIN, NodeType.REQUIRED_FIELD),
    (NodeType.SECTION_TEMPLATE, RelationType.HAS_RULE, NodeType.RULE),
    (NodeType.SECTION_TEMPLATE, RelationType.REQUIRES_PARAMETER, NodeType.PARAMETER),
    (NodeType.PARAMETER, RelationType.HAS_UNIT, NodeType.UNIT_FAMILY),
    (NodeType.INTERFACE_TYPE, RelationType.CONFLICTS_WITH, NodeType.INTERFACE_TYPE),
    (NodeType.RULE, RelationType.ALIGNS_WITH, NodeType.RULE),
    (NodeType.RULE, RelationType.IMPLIES_PATTERN, NodeType.CONSTRAINT_PATTERN),
    # 文档层内部
    (NodeType.DOCUMENT, RelationType.HAS_SECTION, NodeType.SECTION),
    (NodeType.SECTION, RelationType.CONTAINS_REQUIREMENT, NodeType.REQUIREMENT),
    (NodeType.SECTION, RelationType.CONTAINS_TABLE, NodeType.TABLE),
    (NodeType.SECTION, RelationType.CONTAINS_FIGURE, NodeType.FIGURE),
    (NodeType.SECTION, RelationType.HAS_CONSTRAINT, NodeType.CONSTRAINT),
    (NodeType.REQUIREMENT, RelationType.HAS_CONSTRAINT, NodeType.CONSTRAINT),
    # 跨层: 文档↔标准
    (NodeType.SECTION, RelationType.COMPLIES_WITH_TEMPLATE, NodeType.SECTION_TEMPLATE),
    (NodeType.DOCUMENT, RelationType.SATISFIES_RULE, NodeType.RULE),
    (NodeType.SECTION, RelationType.SATISFIES_RULE, NodeType.RULE),
    (NodeType.DOCUMENT, RelationType.REFERENCES_DOCUMENT, NodeType.DOCUMENT),
    (NodeType.REQUIREMENT, RelationType.TRACES_TO, NodeType.REQUIREMENT),
    # 跨层: 检测
    (NodeType.DOCUMENT, RelationType.VIOLATES, NodeType.VIOLATION),
    (NodeType.SECTION, RelationType.VIOLATES, NodeType.VIOLATION),
    (NodeType.REQUIREMENT, RelationType.VIOLATES, NodeType.VIOLATION),
    (NodeType.VIOLATION, RelationType.DETECTED_BY, NodeType.RULE),
}


# ── 溯源证据 (所有标准层节点必须包含) ──────────────────────────

class OcrEvidence(BaseModel):
    """OCR溯源证据 — 让每个节点可追溯到标准原文行号"""
    ocr_file: str = Field(description="OCR文件相对路径")
    ocr_line: int = Field(ge=0, description="OCR行号(0=未定位)")
    match_type: str = Field(description="verbatim/normalized/ellipsis/fuzzy_prefix/not_found")
    ocr_snippet: str = Field(default="", description="OCR原文片段(验证用)")
    source_verified: bool = Field(default=False, description="source字段是否经OCR验证")


# ── 节点 Schema 定义 ──────────────────────────────────────────

class NodeBase(BaseModel):
    """节点基类"""
    id: str
    type: NodeType


class StandardNode(NodeBase):
    type: NodeType = NodeType.STANDARD
    name: str
    name_cn: str
    name_en: str
    version: str
    replaces: str = ""
    ocr_evidence: OcrEvidence


class SectionTemplateNode(NodeBase):
    type: NodeType = NodeType.SECTION_TEMPLATE
    number: str                           # 章节编号, 如 "3.2.X"
    title: str
    title_en: str = ""
    level: int = Field(ge=1, le=5)
    required: str = "must"                # must/conditional/optional
    parent: str = ""
    variants: list[str] = Field(default_factory=list)
    gjb_clause: str = ""                  # GJB条款引用
    ocr_evidence: OcrEvidence


class RuleNode(NodeBase):
    type: NodeType = NodeType.RULE
    rule_type: str                        # content/structure/interface/format/parameter/traceability
    source: str                           # GJB来源, 如 "附录J 3.2"
    severity: str = "MEDIUM"             # HIGH/MEDIUM/LOW
    modality: str = ""                   # MUST/SHOULD/MAY
    applies_to: list[str] = Field(default_factory=list)  # 适用文档类型
    description: str
    original_text: str = ""
    detection_method: str = ""           # regex/structure/keyword/nli/z3/field_match
    ocr_evidence: OcrEvidence


class ConstraintPatternNode(NodeBase):
    """约束模式 — 逻辑层常识的Z3求解模板"""
    type: NodeType = NodeType.CONSTRAINT_PATTERN
    name: str
    z3_template: str                     # 如 "{exec_time} <= {period}"
    params: list[str] = Field(default_factory=list)  # 需要的参数名
    relation: str = ""                   # <=/</>=/>/=
    description: str
    gjb_source: str = ""
    basis_category: str = "B"            # A=明确条款/B=隐含推导/C=工程经验
    ocr_evidence: Optional[OcrEvidence] = None


class ParameterNode(NodeBase):
    type: NodeType = NodeType.PARAMETER
    name_cn: str
    name_en: str
    synonyms_cn: list[str] = Field(default_factory=list)
    synonyms_en: list[str] = Field(default_factory=list)
    default_unit: str = ""
    category: str = ""
    value_range: dict = Field(default_factory=dict)
    must_specify: bool = False
    gjb_section: str = ""
    ocr_evidence: Optional[OcrEvidence] = None


# ── 边 Schema ─────────────────────────────────────────────────

class Edge(BaseModel):
    """边 — 支持属性, multigraph"""
    source: str
    target: str
    relation: RelationType
    weight: float = Field(default=1.0, ge=0, le=1)
    evidence: Optional[dict] = None       # {section, line, text_snippet}
    method: str = ""                      # 检测方法(仅SATISFIES_RULE/VIOLATES)


# ── 验证函数 ──────────────────────────────────────────────────

def validate_node(node_dict: dict) -> tuple[bool, str]:
    """验证节点是否符合本体Schema"""
    try:
        ntype = node_dict.get("type", "")
        if ntype == NodeType.STANDARD.value:
            StandardNode(**node_dict)
        elif ntype == NodeType.SECTION_TEMPLATE.value:
            SectionTemplateNode(**node_dict)
        elif ntype == NodeType.RULE.value:
            RuleNode(**node_dict)
        elif ntype == NodeType.CONSTRAINT_PATTERN.value:
            ConstraintPatternNode(**node_dict)
        elif ntype == NodeType.PARAMETER.value:
            ParameterNode(**node_dict)
        else:
            # 其他类型用基类验证
            NodeBase(**node_dict)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def validate_edge(source_type: str, relation: str, target_type: str) -> tuple[bool, str]:
    """验证边是否符合本体约束表"""
    try:
        st = NodeType(source_type)
        rt = RelationType(relation)
        tt = NodeType(target_type)
        if (st, rt, tt) in VALID_EDGES:
            return True, "OK"
        else:
            return False, f"非法边: ({st.value}, {rt.value}, {tt.value}) 不在VALID_EDGES中"
    except ValueError as e:
        return False, f"未知类型: {e}"


def validate_graph(graph: dict) -> dict:
    """验证整个图谱是否符合本体"""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_types = {n["id"]: n.get("type", "") for n in nodes}
    
    node_errors = []
    for n in nodes:
        ok, msg = validate_node(n)
        if not ok:
            node_errors.append({"node_id": n.get("id", ""), "error": msg})
    
    edge_errors = []
    for e in edges:
        st = node_types.get(e.get("source", ""), "")
        tt = node_types.get(e.get("target", ""), "")
        ok, msg = validate_edge(st, e.get("relation", ""), tt)
        if not ok:
            edge_errors.append({"edge": e, "error": msg})
    
    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "node_errors": node_errors,
        "edge_errors": edge_errors,
        "node_pass_rate": 1 - len(node_errors) / max(1, len(nodes)),
        "edge_pass_rate": 1 - len(edge_errors) / max(1, len(edges)),
        "all_pass": len(node_errors) == 0 and len(edge_errors) == 0,
    }


# ── 常识依据分类 (42条常识的A/B/C分类, 审查结果) ──────────────

COMMONSENSE_BASIS = {
    # A类: GJB有明确条款支撑 (23条)
    "S1": ("A", "附录J", "6顶层章节, OCR L2175-2425"),
    "S2": ("A", "附录J 1.1", "5要素, OCR L2179"),
    "S3": ("A", "附录J 1.2", "6要素, OCR L2183"),
    "S4": ("A", "附录J", "3.1~3.18, OCR L2199-2397"),
    "S5": ("A", "4.3.7.2", "X.Y.Z编号, OCR L287"),
    "S6": ("A", "4.4", "剪裁标识, OCR L303"),  # 修正: 非附录J
    "S7": ("A", "4.3.6", "附录引用, OCR L275"),  # 修正: 非附录J
    "S8": ("A", "4.3.6", "大写字母, OCR L275"),
    "S9": ("A", "4.3.2", "封面10项, OCR L237-255"),
    "S10": ("A", "4.3.4", "目录, OCR L265"),
    "S11": ("A", "4.3.3", "修改页, OCR L261"),
    "S12": ("A", "4.3.7.2", "括号替换, OCR L287"),
    "M1": ("A", "附录J 3", "唯一标识符, OCR L2195"),
    "M4": ("A", "附录J 4", "合格性方法, OCR L2403"),
    "M5": ("A", "附录J 4", "5种方法, OCR L2405-2413"),
    "M7": ("A", "附录J 3.3.X", "接口a~g, OCR L2223-2315"),
    "M8": ("A", "附录J 3.3.X c)", "9项特征, OCR L2227-2255"),
    "M9": ("A", "附录J 3.1", "状态覆盖, OCR L2201"),
    "T1": ("A", "附录J 5 a)", "正向追溯, OCR L2419"),
    "T2": ("A", "附录J 5 b)", "反向追溯, OCR L2423"),
    "T6": ("A", "附录K 6", "设计覆盖, OCR L2649-2655"),
    "T7": ("A", "附录D 7", "测试覆盖, OCR L1205-1213"),
    "G1": ("A", "附录J 3.3.1", "接口图, OCR L2217"),
    # B类: 隐含推导 (9条)
    "M6": ("B", "附录J 2", "引用文档, 推导存在性"),
    "T3": ("B", "附录J 5", "由a)+b)推导无孤立"),
    "T4": ("B", "附录J 5+3", "由唯一ID+追溯推导"),
    "T5": ("B", "附录J 5 b)", "可引用IRS推导"),
    "T8": ("B", "附录F/G/J 4", "跨文档推导"),
    "L2": ("B", "附录J 3.2.X", "时限约束推导exec<=period"),
    "L5": ("B", "附录J 3.11", "资源<=硬件推导"),
    "L6": ("B", "附录J 3.18+3.2.X", "优先级覆盖推导"),
    "G4": ("B", "附录J 3.3.X", "表格列模板推导"),
    # C类: 工程经验, 无GJB条款 (10条) — 诚实标注
    "M2": ("C", "", "同参数同值 — 工程经验,非GJB要求"),
    "M3": ("C", "", "正文↔表格一致 — 工程经验,非GJB要求"),
    "M10": ("C", "", "术语一致 — 工程经验,非GJB要求"),
    "L1": ("C", "", "约束不矛盾 — 工程经验,非GJB要求"),
    "L3": ("C", "", "子项之和<=总预算 — 工程经验,非GJB要求"),
    "L4": ("C", "", "设计约束不与需求矛盾 — 工程经验,非GJB要求"),
    "L7": ("C", "", "同值不同语义非矛盾 — NLI工程经验"),
    "G2": ("C", "", "图片引用完整 — 工程经验,非GJB要求"),
    "G3": ("C", "", "图文一致 — VLM工程经验,非GJB要求"),
    "G5": ("C", "", "表格行完整 — 工程经验,非GJB要求"),
}


if __name__ == "__main__":
    # 自测
    print("=== 本体定义自测 ===")
    print(f"节点类型: {len(NodeType)} 种")
    print(f"边关系类型: {len(RelationType)} 种")
    print(f"合法边组合: {len(VALID_EDGES)} 种")
    print(f"常识分类: A类{sum(1 for v in COMMONSENSE_BASIS.values() if v[0]=='A')}条, "
          f"B类{sum(1 for v in COMMONSENSE_BASIS.values() if v[0]=='B')}条, "
          f"C类{sum(1 for v in COMMONSENSE_BASIS.values() if v[0]=='C')}条")
    
    # 测试验证函数
    test_node = {
        "id": "TPL-3.2", "type": "SectionTemplate",
        "number": "3.2", "title": "CSCI能力需求", "level": 2, "required": "must",
        "ocr_evidence": {"ocr_file": "test.md", "ocr_line": 2203, "match_type": "verbatim", "source_verified": True}
    }
    ok, msg = validate_node(test_node)
    print(f"\n节点验证测试: {ok} ({msg})")
    
    ok, msg = validate_edge("Section", "COMPLIES_WITH_TEMPLATE", "SectionTemplate")
    print(f"边验证测试(合法): {ok} ({msg})")
    
    ok, msg = validate_edge("Document", "COMPLIES_WITH_TEMPLATE", "Rule")
    print(f"边验证测试(非法): {ok} ({msg})")
