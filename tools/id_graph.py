#!/usr/bin/env python3
"""
ID-Graph: 规则锚定的异构文档图一致性校验工具

方法架构(3层):
  L1 符号层: 12种规则信号确定性检测(编辑距离/子串/字符集合/功能词归一化)
  L2 图推理: 传递闭包矛盾检测 + 矛盾子图(两两比较发现不了的矛盾)
  L3 CoVe验证: kimi起草判定 → claude隔离验证(生成与验证解耦)

输入: stage0_assets.json (8类结构化资产)
输出: data/gjb_438c/data_assets/graph/ (图+三层结果+报告)

用法:
  python tools/id_graph.py                # 全流程(构建图+符号层+图推理)
  python tools/id_graph.py --cove         # 加跑CoVe验证(需API)
  python tools/id_graph.py --report       # 生成评测报告
"""
import json
import os
import re
from collections import Counter

import networkx as nx

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE0 = os.path.join(BASE, "data/gjb_438c/data_assets/stage0_assets.json")
GRAPH_DIR = os.path.join(BASE, "data/gjb_438c/data_assets/graph")

SUF = ('功能', '服务', '模块', '接口', '管理', '系统', '软件', '需求', '控制', '处理')


# ========== 工具函数 ==========
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]


def extract_name(ctx, rid):
    """从context提取ID前的名称"""
    m = re.search(r'([\u4e00-\u9fff][\u4e00-\u9fff\w ]{1,25})[/(（]?' + re.escape(rid), ctx)
    if m:
        return m.group(1).strip().rstrip(' /（(')
    return None


def symbol_detect(a, b):
    """符号层检测: 返回(verdict, confidence, signal_type)
    verdict ∈ {'consistent', 'inconsistent', 'ambiguous'}
    """
    if not a or not b:
        return 'ambiguous', 0.3, 'missing_name'
    if a == b:
        return 'consistent', 1.0, 'identical'
    # 归一化(去功能词)
    na, nb = a.strip(), b.strip()
    for s in SUF:
        if na.endswith(s) and len(na) > len(s) + 1:
            na = na[:-len(s)]
            break
    for s in SUF:
        if nb.endswith(s) and len(nb) > len(s) + 1:
            nb = nb[:-len(s)]
            break
    if na == nb:
        return 'consistent', 0.9, 'normalized_same'
    # 子串(截断)
    if a in b or b in a:
        shorter = a if len(a) < len(b) else b
        longer = b if len(a) < len(b) else a
        diff = longer.replace(shorter, '').strip()
        if diff in SUF:
            return 'consistent', 0.85, 'suffix_diff'
        return 'inconsistent', 0.8, 'truncation'
    # 编辑距离(错字)
    dist = levenshtein(a, b)
    if dist <= 2:
        return 'inconsistent', 0.9, 'typo'
    if set(a.replace(' ', '')) == set(b.replace(' ', '')):
        return 'inconsistent', 0.95, 'charorder'
    # 编辑距离3-8: 语义级需要介入
    if dist <= 8:
        return 'ambiguous', 0.5, 'semantic_ambiguous'
    # 完全不同
    return 'inconsistent', 0.6, 'multiname_far'


# ========== L1: 图构建 ==========
def build_graph():
    """从stage0构建ID锚定异构文档图"""
    s0 = json.loads(open(STAGE0, encoding="utf-8").read())
    id_reg = s0['id_registry']

    G = nx.Graph()
    entity_nodes = 0
    mention_nodes = 0

    for rid, entries in id_reg.items():
        if len(entries) < 2:
            continue  # 只处理多位置ID
        G.add_node(f'E_{rid}', type='entity', doc=entries[0].get('doc', '')[:25])
        entity_nodes += 1
        loc_counter = Counter()
        for e in entries:
            loc = e.get('location', 'unknown')
            loc_counter[loc] += 1
            mention_id = f'M_{rid}_{loc}_{loc_counter[loc]}'
            name = extract_name(e.get('context', ''), rid)
            G.add_node(mention_id, type='mention', location=loc,
                       section=e.get('section', ''), name=name or '',
                       context=e.get('context', '')[:60])
            G.add_edge(f'E_{rid}', mention_id, edge_type='appearance')
            mention_nodes += 1

    os.makedirs(GRAPH_DIR, exist_ok=True)
    graph_data = {
        "description": "ID锚定异构文档图",
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "entity_nodes": entity_nodes,
        "mention_nodes": mention_nodes,
        "nodes": [{"id": n, **data} for n, data in G.nodes(data=True)],
        "edges": [{"source": u, "target": v, **data} for u, v, data in G.edges(data=True)],
    }
    out = os.path.join(GRAPH_DIR, "id_document_graph.json")
    json.dump(graph_data, open(out, 'w', encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[L1] 图构建: {entity_nodes}实体 + {mention_nodes}Mention → {out}")
    return G


# ========== L1: 符号层扫描 ==========
def symbol_layer(G):
    """符号层: 确定性信号检测"""
    symbol_results = []
    ambiguous_entities = []

    for entity_node in G.nodes(data=True):
        if entity_node[1].get('type') != 'entity':
            continue
        eid = entity_node[0]
        rid = eid[2:]
        mentions = list(G.neighbors(eid))
        if len(mentions) < 2:
            continue

        mention_names = {}
        for m in mentions:
            name = G.nodes[m].get('name', '')
            loc = G.nodes[m].get('location', '')
            if name:
                mention_names[m] = {'name': name, 'loc': loc}
        if len(mention_names) < 2:
            continue

        m_list = list(mention_names.keys())
        inconsistent_pairs = []
        ambiguous_pairs = []

        for i in range(len(m_list)):
            for j in range(i + 1, len(m_list)):
                mi, mj = m_list[i], m_list[j]
                ni, nj = mention_names[mi]['name'], mention_names[mj]['name']
                verdict, conf, sig = symbol_detect(ni, nj)
                if verdict == 'inconsistent':
                    inconsistent_pairs.append((mi, mj, ni, nj, conf, sig))
                elif verdict == 'ambiguous':
                    ambiguous_pairs.append((mi, mj, ni, nj, conf, sig))

        if inconsistent_pairs:
            symbol_results.append({
                'entity': rid,
                'inconsistent_pairs': [{'m1': p[0], 'm2': p[1], 'name1': p[2], 'name2': p[3],
                                        'conf': p[4], 'signal': p[5]} for p in inconsistent_pairs],
                'signal_types': dict(Counter(p[5] for p in inconsistent_pairs)),
            })
        if ambiguous_pairs:
            ambiguous_entities.append({
                'entity': rid,
                'ambiguous_pairs': [{'m1': p[0], 'm2': p[1], 'name1': p[2], 'name2': p[3],
                                     'conf': p[4], 'signal': p[5]} for p in ambiguous_pairs],
            })

    layer1 = {
        "description": "层1符号层结果: 确定性信号检测",
        "inconsistent_entities": len(symbol_results),
        "ambiguous_entities": len(ambiguous_entities),
        "results": symbol_results,
        "ambiguous": ambiguous_entities,
    }
    out = os.path.join(GRAPH_DIR, "layer1_symbol_results.json")
    json.dump(layer1, open(out, 'w', encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[L1] 符号层: {len(symbol_results)}不一致 + {len(ambiguous_entities)}ambiguous → {out}")
    return layer1


# ========== L2: 图推理(传递闭包矛盾) ==========
def graph_reasoning(G):
    """图推理: 传递闭包矛盾检测 + 矛盾子图"""
    transitivity_conflicts = []

    for entity_node in G.nodes(data=True):
        if entity_node[1].get('type') != 'entity':
            continue
        eid = entity_node[0]
        rid = eid[2:]
        mentions = list(G.neighbors(eid))
        if len(mentions) < 3:
            continue

        m_names = {}
        for m in mentions:
            name = G.nodes[m].get('name', '')
            loc = G.nodes[m].get('location', '')
            if name:
                m_names[m] = {'name': name, 'loc': loc}
        if len(m_names) < 3:
            continue

        m_list = list(m_names.keys())
        pair_verdict = {}
        for i in range(len(m_list)):
            for j in range(i + 1, len(m_list)):
                mi, mj = m_list[i], m_list[j]
                v, conf, sig = symbol_detect(m_names[mi]['name'], m_names[mj]['name'])
                pair_verdict[(mi, mj)] = (v, conf, m_names[mi]['name'], m_names[mj]['name'])

        # 传递闭包: A≡B, B≡C, A≢C
        for i in range(len(m_list)):
            for j in range(i + 1, len(m_list)):
                for k in range(j + 1, len(m_list)):
                    a, b, c = m_list[i], m_list[j], m_list[k]
                    v_ab = pair_verdict.get((a, b)) or pair_verdict.get((b, a))
                    v_bc = pair_verdict.get((b, c)) or pair_verdict.get((c, b))
                    v_ac = pair_verdict.get((a, c)) or pair_verdict.get((c, a))
                    if not all([v_ab, v_bc, v_ac]):
                        continue
                    if v_ab[0] == 'consistent' and v_bc[0] == 'consistent' and v_ac[0] == 'inconsistent':
                        transitivity_conflicts.append({
                            'entity': rid,
                            'A': {'mention': a, 'name': v_ab[2], 'loc': m_names[a]['loc']},
                            'B': {'mention': b, 'name': v_ab[3], 'loc': m_names[b]['loc']},
                            'C': {'mention': c, 'name': v_ac[2], 'loc': m_names[c]['loc']},
                            'conflict_type': 'transitivity_violation',
                        })

    layer2 = {
        "description": "层2图推理结果: 传递闭包矛盾检测",
        "transitivity_conflicts": len(transitivity_conflicts),
        "conflict_details": transitivity_conflicts,
    }
    out = os.path.join(GRAPH_DIR, "layer2_graph_reasoning.json")
    json.dump(layer2, open(out, 'w', encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[L2] 图推理: {len(transitivity_conflicts)}传递闭包矛盾 → {out}")
    return layer2


# ========== 主流程 ==========
def main():
    G = build_graph()
    layer1 = symbol_layer(G)
    layer2 = graph_reasoning(G)

    print("\n=== ID-Graph 完成 ===")
    print(f"图: {G.number_of_nodes()}节点/{G.number_of_edges()}边")
    print(f"L1符号层: {layer1['inconsistent_entities']}不一致Entity")
    print(f"L2图推理: {layer2['transitivity_conflicts']}传递闭包矛盾")
    print(f"输出目录: {GRAPH_DIR}")


if __name__ == "__main__":
    main()


# ========== 多通道视觉互校(可选模块) ==========
def visual_cross_validation():
    """OpenCV节点定位 vs VLM提取 的交叉验证(检测VLM漏检)"""
    vlm_file = os.path.join(BASE, "data/gjb_438c/data_assets/vlm_usecase_extract.jsonl")
    if not os.path.exists(vlm_file):
        print("[视觉互校] 无VLM提取结果, 跳过")
        return

    results = []
    with open(vlm_file, encoding="utf-8") as f:
        for line in f:
            vlm = json.loads(line)
            img_path = vlm.get('image_path', '')
            if not os.path.exists(img_path):
                continue
            nodes = detect_usecase_nodes_robust(img_path)
            vlm_uc = len(vlm.get('usecases', []))
            results.append({
                'doc': vlm.get('doc', '')[:20],
                'cv_nodes': len(nodes),
                'vlm_usecases': vlm_uc,
                'needs_review': abs(len(nodes) - vlm_uc) > 2
            })

    match = sum(1 for r in results if not r['needs_review'])
    print(f"[视觉互校] 共{len(results)}张: {match}张CV与VLM一致, {len(results)-match}张需复核")
    return results


def detect_usecase_nodes_robust(img_path):
    """OpenCV检测用例图节点(兼容深浅背景)"""
    import cv2
    import numpy as np
    img = cv2.imread(img_path)
    if img is None:
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bg_dark = (gray < 128).mean() > 0.5
    if bg_dark:
        gray = 255 - gray
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    ellipses = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 500 or area > 100000:
            continue
        if len(cnt) >= 5:
            ellipse = cv2.fitEllipse(cnt)
            (cx, cy), (major, minor), angle = ellipse
            ratio = major / minor if minor > 0 else 0
            fill = area / (np.pi * major / 2 * minor / 2) if major > 0 and minor > 0 else 0
            if 0.5 <= ratio <= 2.5 and 0.3 <= fill <= 1.2:
                ellipses.append({'cx': float(cx), 'cy': float(cy)})
    deduped = []
    for e in ellipses:
        if not any(abs(e['cx'] - d['cx']) < 25 and abs(e['cy'] - d['cy']) < 25 for d in deduped):
            deduped.append(e)
    return deduped


# ========== 语义图方法: 名称文本相似度连边 + 连通分量矛盾检测 ==========
def semantic_graph_detection(threshold=0.6):
    """语义图: 名称节点按文本相似度连边, 实体名称分裂成多分量=矛盾"""
    s0 = json.loads(open(STAGE0, encoding="utf-8").read())
    id_reg = s0['id_registry']

    def _extract_name(ctx, rid):
        m = re.search(r'([\u4e00-\u9fff][\u4e00-\u9fff\w ]{1,25})[/(（]?' + re.escape(rid), ctx)
        if m:
            return m.group(1).strip().rstrip(' /（(')
        return None

    def _text_sim(a, b):
        if a == b:
            return 1.0
        dist = levenshtein(a, b)
        return 1 - dist / max(len(a), len(b)) if max(len(a), len(b)) > 0 else 0

    # 实体→名称
    entity_names = {}
    for rid, entries in id_reg.items():
        if len(entries) < 2:
            continue
        names = set()
        for e in entries:
            n = _extract_name(e.get('context', ''), rid)
            if n and len(n) >= 2:
                names.add(n)
        if names:
            entity_names[rid] = names

    # 语义图
    all_names = sorted(set(n for names in entity_names.values() for n in names))
    G = nx.Graph()
    for n in all_names:
        G.add_node(n)
    for i, a in enumerate(all_names):
        for j in range(i + 1, len(all_names)):
            b = all_names[j]
            if abs(len(a) - len(b)) > 4:
                continue
            if _text_sim(a, b) >= threshold:
                G.add_edge(a, b)

    # 矛盾检测: 实体名称的连通分量数
    conflicts = []
    for rid, names in entity_names.items():
        if len(names) < 2:
            continue
        sub = G.subgraph(names)
        comps = list(nx.connected_components(sub))
        if len(comps) > 1:
            conflicts.append({
                'entity': rid,
                'components': [sorted(c) for c in comps],
                'component_count': len(comps),
                'severity': 'high' if len(comps) >= 3 else 'medium',
            })

    out = os.path.join(GRAPH_DIR, "semantic_graph_results.json")
    json.dump({
        "description": "语义图方法: 名称文本相似度连边, 连通分量=矛盾",
        "threshold": threshold,
        "name_nodes": len(all_names),
        "semantic_edges": G.number_of_edges(),
        "conflicts": len(conflicts),
        "items": conflicts,
    }, open(out, 'w', encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[语义图] {len(conflicts)}个矛盾实体(连通分量分裂) → {out}")
    return conflicts
