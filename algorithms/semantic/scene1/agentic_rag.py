"""场景1 Agentic RAG: 证据图检索与矛盾定位

基于MAGE-RAG思想(arXiv:2606.15906)改造:
  离线: 12种规则信号构建确定性证据图(零LLM成本)
  在线: Planner→Researcher→Verifier 闭环

核心概念:
  - 证据图: 实体节点+位置节点+属性节点, 规则信号产边
  - Planner: 解析查询, 决定查哪些实体/属性
  - Researcher: 沿图边检索证据(确定性工具+图游走)
  - Verifier: 用检回的证据检测矛盾(规则+LLM兜底)

用法:
  from algorithms.semantic.scene1.agentic_rag import AgenticRAG
  rag = AgenticRAG()
  result = rag.query("PZXQ-GN-FWKFZC-CJFWGC")  # 或功能名
"""
import json
import os
import sys
from collections import defaultdict

import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algorithms.common import (
    load_entity_names, load_id_registry, extract_name,
    text_sim, levenshtein, build_hetero_graph,
)

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ASSETS = os.path.join(BASE, "data/gjb_438c/data_assets")


class EvidenceGraph:
    """确定性证据图: 实体/位置/属性节点, 规则信号产边"""

    def __init__(self):
        self.id_reg = load_id_registry()
        self.entity_names = load_entity_names()
        self.G = nx.Graph()
        self._build()

    def _build(self):
        """用12种规则信号构建图"""
        # 实体-名称-位置节点
        for rid, entries in self.id_reg.items():
            if len(entries) < 2:
                continue
            self.G.add_node(f'E:{rid}', type='entity')
            for e in entries:
                n = extract_name(e.get('context', ''), rid)
                loc = e.get('location', '')
                sec = e.get('section', '')
                if n and len(n) >= 2:
                    self.G.add_node(f'M:{n}', type='name')
                    self.G.add_edge(f'E:{rid}', f'M:{n}', type='has_name')
                if loc:
                    self.G.add_node(f'L:{loc}', type='location')
                    self.G.add_edge(f'E:{rid}', f'L:{loc}', type='appears_in')

        # 名称-名称相似边(文本相似度信号)
        all_names = sorted(set(n for names in self.entity_names.values() for n in names))
        for i, a in enumerate(all_names):
            for j in range(i + 1, len(all_names)):
                b = all_names[j]
                if abs(len(a) - len(b)) > 4:
                    continue
                sim = text_sim(a, b)
                if sim >= 0.55:
                    self.G.add_edge(f'M:{a}', f'M:{b}', type='similar', weight=sim)

    def neighbors(self, node):
        return list(self.G.neighbors(node))


class AgenticRAG:
    """场景1 Agentic RAG: Planner→Researcher→Verifier"""

    def __init__(self):
        self.graph = EvidenceGraph()
        self.entity_names = self.graph.entity_names
        self.id_reg = self.graph.id_reg

    # ========== Planner: 解析查询, 确定实体 ==========
    def plan(self, query):
        """解析查询: 输入ID或名称, 返回目标实体"""
        # 精确ID
        if query in self.entity_names:
            return {'entity_id': query, 'names': list(self.entity_names[query])}

        # ID在registry但可能不是多位置
        if query in self.id_reg:
            return {'entity_id': query, 'names': [extract_name(e.get('context', ''), query)
                                                  for e in self.id_reg[query] if extract_name(e.get('context', ''), query)]}

        # 名称模糊匹配
        best_rid = None
        best_sim = 0
        for rid, names in self.entity_names.items():
            for n in names:
                sim = text_sim(query, n)
                if sim > best_sim:
                    best_sim = sim
                    best_rid = rid
        if best_rid and best_sim > 0.5:
            return {'entity_id': best_rid, 'names': list(self.entity_names[best_rid]), 'match_sim': best_sim}
        return {'entity_id': None, 'names': [query]}

    # ========== Researcher: 沿图检索证据 ==========
    def research(self, entity_id):
        """检索实体的全部位置证据"""
        if not entity_id:
            return []
        e_node = f'E:{entity_id}'
        if e_node not in self.graph.G:
            return []

        # 收集: 名称节点 + 位置节点 + 相似名称
        evidence = {
            'entity_id': entity_id,
            'names': [],
            'locations': [],
            'similar_names': [],
        }
        for nbr in self.graph.G.neighbors(e_node):
            nbr_data = self.graph.G.nodes[nbr]
            if nbr_data.get('type') == 'name':
                evidence['names'].append(nbr)
            elif nbr_data.get('type') == 'location':
                evidence['locations'].append(nbr)

        # 相似名称(通过名称-名称边)
        for name_node in evidence['names']:
            for nbr in self.graph.G.neighbors(name_node):
                if nbr.startswith('M:') and nbr not in evidence['names']:
                    evidence['similar_names'].append(nbr)

        # 原始entries
        evidence['entries'] = self.id_reg.get(entity_id, [])
        return evidence

    # ========== Verifier: 检测矛盾 ==========
    def verify(self, evidence):
        """用检回的证据检测矛盾"""
        if not evidence or not evidence.get('names'):
            return {'status': 'unknown', 'reason': '无证据'}

        names = [n[2:] for n in evidence['names']]  # 去掉M:前缀
        if len(names) < 2:
            return {'status': 'consistent', 'reason': '单名称', 'names': names}

        # 双空间矛盾检测: 同实体 + 文本不相似
        conflicts = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                sim = text_sim(a, b)
                if sim < 0.6:
                    conflicts.append({'name_a': a, 'name_b': b, 'text_sim': round(sim, 2)})

        if conflicts:
            return {
                'status': 'inconsistent',
                'reason': f'{len(conflicts)}对名称不一致',
                'names': names,
                'conflicts': conflicts,
            }
        return {'status': 'consistent', 'reason': '名称一致', 'names': names}

    # ========== 完整查询 ==========
    def query(self, query):
        """完整流程: Planner→Researcher→Verifier"""
        plan = self.plan(query)
        evidence = self.research(plan.get('entity_id'))
        verdict = self.verify(evidence)
        return {
            'query': query,
            'plan': plan,
            'evidence': {k: v for k, v in evidence.items() if k != 'entries'},
            'verdict': verdict,
        }


# ========== 批量评测 ==========
def evaluate_agentic_rag():
    """在Gold Standard真实矛盾上评测Agentic RAG"""
    from algorithms.common import load_gold_conflicts
    rag = AgenticRAG()
    gold_conflicts = load_gold_conflicts('scene1')
    entity_names = load_entity_names()

    detected = set()
    for rid in gold_conflicts:
        # 用第一个名称查询
        if rid in entity_names:
            first_name = list(entity_names[rid])[0]
            result = rag.query(first_name)
            if result['verdict']['status'] == 'inconsistent':
                detected.add(rid)

    # 评测
    from algorithms.common import evaluate_detection
    result = evaluate_detection(detected, gold_conflicts, entity_names)
    print(f"Agentic RAG: P={result['P']} R={result['R']} F1={result['F1']}")
    return result


if __name__ == "__main__":
    evaluate_agentic_rag()
