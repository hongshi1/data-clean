#!/usr/bin/env python3
"""
SRS Knowledge Graph Builder v2
Phase 2 of Data Governance Pipeline.

Builds a unified knowledge graph from:
  1. GJB 438C-2021 rules (structure, content, parameter, interface, format)
  2. Existing knowledge_graph.json (1580 nodes / 4800 edges)
  3. SRS document structure from MinerU parsed data (62 documents)

Output: knowledge/srs_kb_graph_v2.json
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
GJB_RULES = REPO_ROOT / "knowledge" / "gjb_438c_rules.json"
EXISTING_KG = REPO_ROOT / "data" / "srs_requirements" / "knowledge_graph.json"
MINERU_PARSED = REPO_ROOT / "data" / "srs_requirements" / "mineru_parsed"
OUTPUT = REPO_ROOT / "knowledge" / "srs_kb_graph_v2.json"


class KnowledgeGraph:
    """Simple knowledge graph using adjacency lists."""
    
    def __init__(self):
        self.nodes = {}  # id -> node_dict
        self.edges = []  # list of edge_dicts
        self._edge_keys = set()  # for dedup
    
    def add_node(self, node_id: str, node_type: str, **props):
        if node_id not in self.nodes:
            self.nodes[node_id] = {"id": node_id, "type": node_type, **props}
        else:
            self.nodes[node_id].update(props)
    
    def add_edge(self, source: str, target: str, relation: str, **props):
        key = (source, target, relation)
        if key not in self._edge_keys:
            edge = {"source": source, "target": target, "relation": relation}
            edge.update(props)
            self.edges.append(edge)
            self._edge_keys.add(key)
    
    def to_json(self):
        return {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }
    
    def stats(self):
        node_types = defaultdict(int)
        edge_types = defaultdict(int)
        for n in self.nodes.values():
            node_types[n.get("type", "unknown")] += 1
        for e in self.edges:
            edge_types[e.get("relation", "unknown")] += 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
        }


def build_gjb_nodes_and_edges(kg: KnowledgeGraph, gjb_rules: dict):
    """Add GJB 438C standard, sections, requirements, parameters, format rules to the graph."""
    
    standard_id = "GJB-438C-2021"
    kg.add_node(standard_id, "Standard",
                name="GJB 438C-2021",
                name_cn="军用软件开发文档通用要求",
                name_en="General requirements for military software development documentation",
                version="2021",
                replaces="GJB 438B-2009")
    
    # ── Document types ──
    for dt in gjb_rules["document_types"]["types"]:
        dt_id = f"DOCTYPE-{dt['code']}"
        kg.add_node(dt_id, "DocumentType",
                    code=dt["code"],
                    name_cn=dt["name_cn"],
                    name_en=dt["name_en"],
                    appendix=dt["appendix"],
                    is_target=dt.get("is_target", False))
        kg.add_edge(standard_id, dt_id, "DEFINES_TYPE")
    
    # ── Structure rules: chapters and sub-sections ──
    for ch in gjb_rules["structure_rules"]["required_chapters"]:
        ch_id = f"GJB-SEC-{ch['number']}"
        kg.add_node(ch_id, "GJB_Section",
                    number=ch["number"],
                    title=ch["title"],
                    title_en=ch.get("title_en", ""),
                    required=ch["required"])
        kg.add_edge(standard_id, ch_id, "HAS_SECTION")
        
        for sub in ch.get("sub_sections", []):
            sub_id = f"GJB-SEC-{sub['number']}"
            kg.add_node(sub_id, "GJB_Section",
                        number=sub["number"],
                        title=sub["title"],
                        title_en=sub.get("title_en", ""),
                        required=sub["required"])
            kg.add_edge(ch_id, sub_id, "HAS_SUBSECTION")
            
            if "must_contain" in sub:
                for field in sub["must_contain"]:
                    field_id = f"GJB-FIELD-{sub['number']}-{field}"
                    kg.add_node(field_id, "RequiredField",
                                section=sub["number"],
                                field=field)
                    kg.add_edge(sub_id, field_id, "MUST_CONTAIN")
            
            for ssub in sub.get("sub_sections", []):
                ssub_id = f"GJB-SEC-{ssub['number']}"
                kg.add_node(ssub_id, "GJB_Section",
                            number=ssub["number"],
                            title=ssub["title"],
                            required=ssub.get("required", False))
                kg.add_edge(sub_id, ssub_id, "HAS_SUBSECTION")
    
    # ── Content rules ──
    for rule in gjb_rules["content_rules"]["rules"]:
        rule_id = rule["rule_id"]
        kg.add_node(rule_id, "ContentRule",
                    section=rule["section"],
                    description=rule["description"],
                    required_fields=rule.get("required_fields", []),
                    severity=rule.get("severity", "MEDIUM"))
        sec_id = f"GJB-SEC-{rule['section'].split('.')[0]}"
        kg.add_edge(sec_id, rule_id, "HAS_RULE")
    
    # ── Parameter rules ──
    for param in gjb_rules["parameter_rules"]["parameters"]:
        param_id = f"GJB-PARAM-{param['name_en']}"
        kg.add_node(param_id, "Parameter",
                    name_cn=param["name_cn"],
                    name_en=param["name_en"],
                    section=param["section"],
                    description=param["description"],
                    must_specify=param["must_specify"],
                    typical_unit=param.get("typical_unit", ""),
                    value_range=param.get("value_range", {}),
                    category=param.get("category", "general"),
                    severity=param.get("severity", "MEDIUM"))
        sec_id = f"GJB-SEC-{param['section'].split('.')[0]}"
        kg.add_edge(sec_id, param_id, "REQUIRES_PARAMETER")
    
    # ── Interface rules ──
    iface_id = "GJB-INTERFACE-RULES"
    kg.add_node(iface_id, "InterfaceRuleSet",
                description=gjb_rules["interface_rules"]["description"],
                source=gjb_rules["interface_rules"]["source"])
    for field in gjb_rules["interface_rules"]["required_fields"]:
        f_id = f"GJB-IFACE-FIELD-{field['field']}"
        kg.add_node(f_id, "InterfaceField",
                    field=field["field"],
                    description=field["description"],
                    severity=field["severity"])
        kg.add_edge(iface_id, f_id, "REQUIRES_FIELD")
    kg.add_edge(standard_id, iface_id, "HAS_INTERFACE_RULES")
    
    # ── Format rules ──
    for rule in gjb_rules["format_rules"]["rules"]:
        rule_id = rule["rule_id"]
        kg.add_node(rule_id, "FormatRule",
                    category=rule["category"],
                    description=rule["description"],
                    severity=rule.get("severity", "MEDIUM"),
                    required_fields=rule.get("required_fields", []),
                    required_components=rule.get("required_components", []))
        kg.add_edge(standard_id, rule_id, "HAS_FORMAT_RULE")


def merge_existing_kg(kg: KnowledgeGraph, existing_kg: dict):
    """Merge existing knowledge graph nodes and edges."""
    
    for node in existing_kg.get("nodes", []):
        node_id = node.get("id", "")
        if not node_id:
            continue
        node_type = node.get("type", "unknown")
        props = {k: v for k, v in node.items() if k not in ("id", "type")}
        
        if node_id not in kg.nodes:
            kg.add_node(node_id, node_type, **props)
        else:
            kg.nodes[node_id].update(props)
    
    for edge in existing_kg.get("edges", []):
        source = edge.get("source", "")
        target = edge.get("target", "")
        relation = edge.get("relation", edge.get("type", "related"))
        props = {k: v for k, v in edge.items() if k not in ("source", "target", "relation")}
        kg.add_edge(source, target, relation, **props)


def extract_sections_from_md(md_path: Path) -> list:
    """Extract section structure from MinerU markdown output."""
    sections = []
    try:
        content = md_path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip()
                if title:
                    sections.append({"level": level, "title": title})
    except Exception:
        pass
    return sections


def add_srs_documents(kg: KnowledgeGraph):
    """Add SRS document nodes from MinerU parsed data."""
    
    if not MINERU_PARSED.exists():
        return
    
    doc_count = 0
    sec_count = 0
    
    for doc_dir in sorted(MINERU_PARSED.iterdir()):
        if not doc_dir.is_dir() or doc_dir.name.startswith("_"):
            continue
        
        doc_name = doc_dir.name
        if doc_name.endswith(".pdf"):
            doc_name = doc_name[:-4]
        
        doc_id = f"SRS-{doc_name}"
        
        md_files = list(doc_dir.rglob("*.md"))
        if not md_files:
            continue
        
        md_path = md_files[0]
        md_content = md_path.read_text(encoding="utf-8", errors="replace")
        
        md_lines = md_content.count("\n")
        num_tables = md_content.count("<table>")
        num_headers = md_content.count("\n#")
        num_images = len(list(doc_dir.rglob("images/*.jpg"))) + len(list(doc_dir.rglob("images/*.png")))
        
        kg.add_node(doc_id, "SRS_Document",
                    filename=doc_name,
                    md_file=str(md_path),
                    md_lines=md_lines,
                    num_tables=num_tables,
                    num_headers=num_headers,
                    num_images=num_images)
        
        kg.add_edge(doc_id, "GJB-438C-2021", "SHOULD_COMPLY_WITH")
        
        sections = extract_sections_from_md(md_path)
        for i, sec in enumerate(sections):
            sec_id = f"{doc_id}-SEC-{i:04d}"
            kg.add_node(sec_id, "SRS_Section",
                        doc=doc_id,
                        level=sec["level"],
                        title=sec["title"],
                        section_index=i)
            kg.add_edge(doc_id, sec_id, "HAS_SECTION")
            sec_count += 1
        
        doc_count += 1
    
    return doc_count, sec_count


def main():
    print("=" * 60)
    print("Knowledge Graph Builder v2")
    print("=" * 60)
    
    kg = KnowledgeGraph()
    
    # Step 1: GJB 438C rules
    print("\n1. Loading GJB 438C rules...")
    gjb_rules = json.loads(GJB_RULES.read_text(encoding="utf-8"))
    build_gjb_nodes_and_edges(kg, gjb_rules)
    s = kg.stats()
    print(f"   GJB nodes: {s['total_nodes']}, edges: {s['total_edges']}")
    
    # Step 2: Merge existing KG
    print("\n2. Merging existing knowledge graph...")
    if EXISTING_KG.exists():
        existing = json.loads(EXISTING_KG.read_text(encoding="utf-8"))
        before_nodes = len(kg.nodes)
        before_edges = len(kg.edges)
        merge_existing_kg(kg, existing)
        print(f"   Added {len(kg.nodes) - before_nodes} nodes, {len(kg.edges) - before_edges} edges from existing KG")
    else:
        print(f"   Existing KG not found at {EXISTING_KG}")
    
    # Step 3: Add SRS documents
    print("\n3. Adding SRS documents from MinerU parsed data...")
    result = add_srs_documents(kg)
    if result:
        doc_count, sec_count = result
        print(f"   Added {doc_count} SRS documents, {sec_count} sections")
    
    # Final stats
    s = kg.stats()
    print(f"\n{'=' * 60}")
    print(f"Knowledge Graph v2 Complete")
    print(f"  Total nodes: {s['total_nodes']}")
    print(f"  Total edges: {s['total_edges']}")
    print(f"  Node types: {json.dumps(s['node_types'], indent=4)}")
    print(f"  Edge types: {json.dumps(s['edge_types'], indent=4)}")
    
    # Save
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output = kg.to_json()
    output["graph"]["version"] = "2.0"
    output["graph"]["build_date"] = datetime.now().isoformat()
    output["graph"]["sources"] = ["GJB 438C-2021", "existing_knowledge_graph.json", "MinerU parsed SRS documents"]
    
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Output: {OUTPUT}")
    print(f"  File size: {OUTPUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
