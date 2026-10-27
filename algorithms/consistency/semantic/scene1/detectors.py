"""场景1(用例图+capability表+正文)名称一致性检测算法

7种方法:
  B1 连通分量      - 规则图
  B2 Louvain      - 无监督图聚类
  B3 谱聚类       - 谱方法
  B4 学习LR       - 监督特征学习
  B5 手写GCN      - 图神经网络
  O1 图注意力     - 学习边权重
  O2 双空间       - 拓扑嵌入+文本(本文方法)
"""
import os
import sys

import networkx as nx
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algorithms.common import (
    build_semantic_graph, build_hetero_graph, metapath_embed,
    load_entity_names, load_gold_conflicts, text_sim, levenshtein,
    evaluate_detection,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
ASSETS = os.path.join(PROJECT_ROOT, "data/gjb_438c/data_assets")
GOLD_DIR = os.path.join(ASSETS, "gold_standard")


class Scene1Detector:
    """场景1名称一致性检测器"""

    def __init__(self, sim_threshold=0.55, seed=42):
        self.entity_names = load_entity_names()
        self.gold_conflicts = load_gold_conflicts('scene1')
        self.sim_threshold = sim_threshold
        self.seed = seed
        self.all_names = sorted(set(n for names in self.entity_names.values() for n in names))
        self.name2idx = {n: i for i, n in enumerate(self.all_names)}
        self.G = build_semantic_graph(self.entity_names, sim_threshold)
        self.results = {}

    # ---------- 方法1: 连通分量 ----------
    def detect_connected_components(self):
        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            comps = list(nx.connected_components(self.G.subgraph(names)))
            if len(comps) > 1:
                detected.add(rid)
        return detected

    # ---------- 方法2: Louvain ----------
    def detect_louvain(self):
        from networkx.algorithms import community
        comms = community.louvain_communities(self.G, weight='weight', seed=self.seed)
        n2c = {}
        for ci, comp in enumerate(comms):
            for n in comp:
                n2c[n] = ci
        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            if len(set(n2c.get(n, -1) for n in names)) > 1:
                detected.add(rid)
        return detected

    # ---------- 方法3: 谱聚类 ----------
    def detect_spectral(self, n_clusters=100):
        from scipy.linalg import eigh
        from scipy.cluster.hierarchy import fcluster, linkage
        from scipy.spatial.distance import pdist, squareform

        n_names = len(self.all_names)
        S = np.zeros((n_names, n_names))
        for i, a in enumerate(self.all_names):
            for j in range(i + 1, n_names):
                b = self.all_names[j]
                sim = text_sim(a, b)
                if sim > 0:
                    S[i, j] = S[j, i] = sim

        D = np.diag(S.sum(axis=1) + 1e-9)
        D_inv_sqrt = np.diag(1 / np.sqrt(np.diag(D)))
        L_norm = np.eye(n_names) - D_inv_sqrt @ S @ D_inv_sqrt

        eigvals, eigvecs = eigh(L_norm)
        embed = eigvecs[:, 1:11]
        dist_matrix = squareform(pdist(embed, metric='cosine'))
        link = linkage(dist_matrix, method='average')
        labels = fcluster(link, n_clusters, criterion='maxclust')

        name2c = {self.all_names[i]: int(labels[i]) for i in range(n_names)}
        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            if len(set(name2c.get(n, -1) for n in names)) > 1:
                detected.add(rid)
        return detected

    # ---------- 方法4: 学习LR ----------
    def detect_learned(self, train_epochs=500):
        import json
        gs = json.loads(open(os.path.join(GOLD_DIR, 'multi_scene_gold_standard.json')).read())
        sc1 = gs['scenes']['scene1']

        train_pairs = []
        for item in sc1['negatives']:
            correct = item.get('correct_name', '')
            for wname_item in item.get('wrong_names', []):
                wname = (wname_item.get('wrong_name', wname_item.get('name', ''))
                         if isinstance(wname_item, dict) else
                         (wname_item if isinstance(wname_item, str) else ''))
                if wname and wname != correct:
                    train_pairs.append((correct, wname, 1))
        for item in sc1['positives']:
            train_pairs.append((item.get('name', ''), item.get('name', ''), 0))

        def feats(a, b):
            d = levenshtein(a, b)
            ml = max(len(a), len(b), 1)
            return np.array([1.0 - d / ml, float(d), float(abs(len(a) - len(b))) / ml,
                             float(len(set(a) & set(b))) / float(max(len(set(a) | set(b)), 1)),
                             1.0 if a[:2] == b[:2] else 0.0], dtype=np.float64)

        X = np.array([feats(a, b) for a, b, _ in train_pairs], dtype=np.float64)
        y = np.array([float(lbl) for _, _, lbl in train_pairs], dtype=np.float64)
        Xm, Xs = X.mean(0), X.std(0) + 1e-9
        Xn = (X - Xm) / Xs

        np.random.seed(self.seed)
        w_model = np.random.randn(5).astype(np.float64) * 0.1
        b_model = np.float64(0.0)
        for _ in range(train_epochs):
            z = Xn @ w_model + b_model
            p = 1 / (1 + np.exp(-z))
            w_model = w_model - 0.1 * (Xn.T @ (p - y) / len(y))
            b_model = b_model - 0.1 * (p - y).mean()

        def make_predictor(weights, bias, x_mean, x_std):
            def predict(a, b):
                if a == b:
                    return False
                x = feats(a, b)
                xn = (x - x_mean) / x_std
                prob = 1 / (1 + np.exp(-(xn @ weights + bias)))
                return bool(prob > 0.5)
            return predict

        predict = make_predictor(w_model, b_model, Xm, Xs)

        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            nl = list(names)
            for i in range(len(nl)):
                for j in range(i + 1, len(nl)):
                    if predict(nl[i], nl[j]):
                        detected.add(rid)
                        break
                if rid in detected:
                    break
        return detected

    # ---------- 方法5: 手写GCN ----------
    def detect_gcn(self):
        n_names = len(self.all_names)
        A = np.zeros((n_names, n_names))
        for i, a in enumerate(self.all_names):
            for j in range(i + 1, n_names):
                b = self.all_names[j]
                sim = text_sim(a, b)
                if sim >= 0.5:
                    A[i, j] = A[j, i] = sim
        A = A + np.eye(n_names)
        D = np.diag(A.sum(axis=1) + 1e-9)
        D_inv_sqrt = np.diag(1 / np.sqrt(np.diag(D)))
        A_hat = D_inv_sqrt @ A @ D_inv_sqrt

        def char_bigram(name):
            bgs = {}
            for k in range(len(name) - 1):
                bg = name[k:k + 2]
                bgs[bg] = bgs.get(bg, 0) + 1
            return bgs

        all_bigrams = set()
        for n in self.all_names:
            all_bigrams.update(char_bigram(n).keys())
        bigram_list = sorted(all_bigrams)

        def name_feat(name):
            bg = char_bigram(name)
            vec = np.zeros(len(bigram_list))
            for k, v in bg.items():
                if k in bigram_list:
                    vec[bigram_list.index(k)] = v
            return vec

        X = np.array([name_feat(n) for n in self.all_names], dtype=np.float64)
        X = X / (X.sum(axis=1, keepdims=True) + 1e-9)

        np.random.seed(self.seed)
        W1 = np.random.randn(len(bigram_list), 64).astype(np.float64) * 0.01
        W2 = np.random.randn(64, 32).astype(np.float64) * 0.01
        H1 = np.maximum(A_hat @ X @ W1, 0)
        H2 = A_hat @ H1 @ W2
        norms = np.linalg.norm(H2, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings = H2 / norms

        def gcn_sim(a, b):
            i, j = self.name2idx.get(a), self.name2idx.get(b)
            if i is not None and j is not None:
                return float(embeddings[i] @ embeddings[j])
            return None

        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            nl = list(names)
            for i in range(len(nl)):
                for j in range(i + 1, len(nl)):
                    a, b = nl[i], nl[j]
                    if a == b:
                        continue
                    topo = gcn_sim(a, b)
                    text = text_sim(a, b)
                    if topo is not None and topo > 0.7 and text < 0.6:
                        detected.add(rid)
                        break
                if rid in detected:
                    break
        return detected

    # ---------- 方法6: 图注意力 ----------
    def detect_graph_attention(self):
        def edge_feats(a, b):
            d = levenshtein(a, b)
            ml = max(len(a), len(b), 1)
            return np.array([1.0 - d / ml, float(d),
                             float(len(set(a) & set(b))) / float(max(len(set(a) | set(b)), 1)),
                             1.0 if a[:2] == b[:2] else 0.0,
                             float(min(len(a), len(b))) / float(ml)], dtype=np.float64)

        pos = []
        for rid, names in self.entity_names.items():
            nl = list(names)
            for i in range(len(nl)):
                for j in range(i + 1, len(nl)):
                    pos.append((nl[i], nl[j], 1))
        neg = []
        rids = list(self.entity_names.keys())
        for i in range(min(200, len(rids))):
            r1, r2 = rids[i], rids[(i + 1) % len(rids)]
            n1, n2 = list(self.entity_names[r1])[0], list(self.entity_names[r2])[0]
            if n1 != n2:
                neg.append((n1, n2, 0))

        pairs = pos + neg
        X = np.array([edge_feats(a, b) for a, b, _ in pairs], dtype=np.float64)
        y = np.array([float(label) for _, _, label in pairs], dtype=np.float64)
        Xm, Xs = X.mean(0), X.std(0) + 1e-9
        Xn = (X - Xm) / Xs

        np.random.seed(self.seed)
        w = np.random.randn(5).astype(np.float64) * 0.1
        b = np.float64(0.0)
        for _ in range(300):
            z = Xn @ w + b
            p = 1 / (1 + np.exp(-z))
            w = w - 0.1 * (Xn.T @ (p - y) / len(y))
            b = b - 0.1 * (p - y).mean()

        def make_edge_predictor(weights, bias, x_mean, x_std):
            def edge_prob(a, b):
                x = edge_feats(a, b)
                xn = (x - x_mean) / x_std
                return float(1 / (1 + np.exp(-(xn @ weights + bias))))
            return edge_prob

        edge_prob = make_edge_predictor(w, b, Xm, Xs)

        G_learn = nx.Graph()
        for n in self.all_names:
            G_learn.add_node(n)
        for i, a in enumerate(self.all_names):
            for j in range(i + 1, len(self.all_names)):
                b = self.all_names[j]
                prob = edge_prob(a, b)
                if prob > 0.5:
                    G_learn.add_edge(a, b, weight=prob)

        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            comps = list(nx.connected_components(G_learn.subgraph(names)))
            if len(comps) > 1:
                detected.add(rid)
        return detected

    # ---------- 方法7: 双空间(本文方法) ----------
    def detect_dual_space(self):
        G_hetero, _ = build_hetero_graph(self.entity_names)
        # 名称-名称相似边
        for i, a in enumerate(self.all_names):
            for j in range(i + 1, len(self.all_names)):
                b = self.all_names[j]
                if abs(len(a) - len(b)) > 4:
                    continue
                sim = text_sim(a, b)
                if sim >= 0.5:
                    G_hetero.add_edge(f'M:{a}', f'M:{b}', type='similar', weight=sim)

        emb = metapath_embed(G_hetero, seed=self.seed)

        def topo_sim(a, b):
            ka, kb = f'M:{a}', f'M:{b}'
            if ka in emb and kb in emb:
                return float(emb[ka] @ emb[kb])
            return None

        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            nl = list(names)
            for i in range(len(nl)):
                for j in range(i + 1, len(nl)):
                    a, b = nl[i], nl[j]
                    if a == b:
                        continue
                    topo = topo_sim(a, b)
                    text = text_sim(a, b)
                    if topo is not None and topo > 0.7 and text < 0.6:
                        detected.add(rid)
                        break
                if rid in detected:
                    break
        return detected

    # ---------- 统一运行 ----------
    def run_all(self):
        methods = {
            'B1_connected_components': self.detect_connected_components,
            'B2_louvain': self.detect_louvain,
            'B3_spectral': self.detect_spectral,
            'B4_learned_lr': self.detect_learned,
            'B5_gcn': self.detect_gcn,
            'O1_graph_attention': self.detect_graph_attention,
            'O2_dual_space': self.detect_dual_space,
        }
        for name, fn in methods.items():
            detected = fn()
            result = evaluate_detection(detected, self.gold_conflicts, self.entity_names)
            self.results[name] = result
            print(f"  {name}: P={result['P']} R={result['R']} F1={result['F1']} "
                  f"(TP{result['TP']} FP{result['FP']} FN{result['FN']})")
        return self.results
