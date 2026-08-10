"""共享工具模块: 图构建/文本度量/评测"""
import json
import os
import random
import re
from collections import defaultdict

import networkx as nx
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(BASE, "data/gjb_438c/data_assets")
STAGE0 = os.path.join(ASSETS, "stage0_assets.json")


# ========== 文本度量 ==========
def levenshtein(s1, s2):
    """编辑距离"""
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


def text_sim(a, b):
    """文本相似度(编辑距离归一化)"""
    if a == b:
        return 1.0
    ml = max(len(a), len(b))
    return 1 - levenshtein(a, b) / ml if ml > 0 else 0


def extract_name(ctx, rid):
    """从context提取ID前的名称"""
    m = re.search(r'([\u4e00-\u9fff][\u4e00-\u9fff\w ]{1,25})[/(（]?' + re.escape(rid), ctx)
    if m:
        return m.group(1).strip().rstrip(' /（(')
    return None


# ========== 数据加载 ==========
def load_id_registry():
    """加载id_registry"""
    s0 = json.loads(open(STAGE0).read())
    return s0['id_registry']


def load_entity_names(min_occurrences=2):
    """加载实体→名称映射(多位置ID)"""
    id_reg = load_id_registry()
    entity_names = {}
    for rid, entries in id_reg.items():
        if len(entries) < min_occurrences:
            continue
        names = set()
        for e in entries:
            n = extract_name(e.get('context', ''), rid)
            if n and len(n) >= 2:
                names.add(n)
        if names:
            entity_names[rid] = names
    return entity_names


def load_gold_conflicts(scene='scene1'):
    """加载Gold Standard真实矛盾(按场景)"""
    gs_path = os.path.join(ASSETS, "gold_standard/multi_scene_gold_standard.json")
    gs = json.loads(open(gs_path).read())
    if scene not in gs['scenes']:
        return set()
    return set(n.get('entity_id', '') for n in gs['scenes'][scene]['negatives']
               if n.get('source') == 'real')


# ========== 图构建 ==========
def build_semantic_graph(entity_names, sim_threshold=0.55):
    """语义图: 名称按文本相似度连边"""
    all_names = sorted(set(n for names in entity_names.values() for n in names))
    G = nx.Graph()
    for n in all_names:
        G.add_node(n)
    for i, a in enumerate(all_names):
        for j in range(i + 1, len(all_names)):
            b = all_names[j]
            if abs(len(a) - len(b)) > 4:
                continue
            sim = text_sim(a, b)
            if sim >= sim_threshold:
                G.add_edge(a, b, weight=sim)
    return G


def build_hetero_graph(entity_names):
    """异构图: 实体节点+名称节点"""
    G = nx.Graph()
    name_entities = defaultdict(list)
    for rid, names in entity_names.items():
        G.add_node(f'E:{rid}', type='entity')
        for n in names:
            if f'M:{n}' not in G:
                G.add_node(f'M:{n}', type='name')
            G.add_edge(f'E:{rid}', f'M:{n}', type='has_name')
            name_entities[n].append(rid)
    return G, name_entities


def metapath_embed(G_hetero, dim=32, walk_len=12, num_walks=30, seed=42):
    """metapath随机游走嵌入(独立Random实例保证可复现)"""
    rng = random.Random(seed)

    def metapath_walk(start, walk_len=walk_len, rng=rng):
        walk = [start]
        curr = start
        for _ in range(walk_len - 1):
            nbrs = list(G_hetero.neighbors(curr))
            if not nbrs:
                break
            curr_type = G_hetero.nodes[curr]['type']
            candidates = [n for n in nbrs if G_hetero.nodes[n]['type'] != curr_type]
            if not candidates:
                candidates = nbrs
            curr = rng.choice(candidates)
            walk.append(curr)
        return walk

    entity_nodes = [n for n, d in G_hetero.nodes(data=True) if d['type'] == 'entity']
    walks = []
    for _ in range(num_walks):
        rng.shuffle(entity_nodes)
        for e in entity_nodes[:100]:
            walks.append(metapath_walk(e, walk_len))

    # PPMI + SVD
    cooc = defaultdict(lambda: defaultdict(int))
    for walk in walks:
        for i in range(len(walk)):
            for j in range(max(0, i - 3), min(len(walk), i + 4)):
                if i != j:
                    cooc[walk[i]][walk[j]] += 1

    vocab = [n for n in G_hetero.nodes() if n in cooc]
    v2i = {n: i for i, n in enumerate(vocab)}
    n_vocab = len(vocab)
    total_pairs = sum(sum(c.values()) for c in cooc.values())
    row_sum = {n: sum(c.values()) for n, c in cooc.items()}
    col_sum = defaultdict(int)
    for c in cooc.values():
        for w, cnt in c.items():
            col_sum[w] += cnt

    X = np.zeros((n_vocab, n_vocab))
    for i, n in enumerate(vocab):
        for w, cnt in cooc[n].items():
            if w in v2i:
                pmi = max(0, np.log((cnt * total_pairs) / (row_sum[n] * col_sum[w] + 1e-9)))
                X[i, v2i[w]] = pmi

    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    embeddings = U[:, :dim] * np.sqrt(S[:dim])
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return {n: embeddings[i] / norms[i] for i, n in enumerate(vocab)}


# ========== 评测 ==========
def evaluate_detection(detected, gold_conflicts, entity_names):
    """评测: P/R/F1"""
    tp = fp = fn = 0
    for rid in entity_names:
        pred = rid in detected
        gold = rid in gold_conflicts
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif not pred and gold:
            fn += 1
    p = tp / (tp + fp) if (tp + fp) > 0 else 0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
    return {
        'P': round(p, 3), 'R': round(r, 3), 'F1': round(f1, 3),
        'TP': tp, 'FP': fp, 'FN': fn,
        'detected_count': len(detected),
    }
