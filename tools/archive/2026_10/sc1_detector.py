#!/usr/bin/env python3
"""
SC1 Detector: 场景1(用例图+capability表+正文) 名称一致性检测工具

方法体系(7种):
  B1 字符级(编辑距离/子串)      - 规则基线
  B2 Louvain社区发现            - 无监督图聚类
  B3 谱聚类(拉普拉斯)           - 谱方法
  B4 学习检测器(逻辑回归)        - 监督特征学习
  B5 手写GCN(图传播)            - 图神经网络
  O1 图注意力(学习边权重)        - 可学习图
  O2 双空间(拓扑嵌入+文本)       - 本文方法

统一接口:
  detector = SC1Detector()
  detector.run_all()           # 运行全部7种方法
  detector.evaluate(method)    # 评测单个方法
  detector.report()            # 生成完整报告

用法:
  python tools/sc1_detector.py --all        # 运行全部方法
  python tools/sc1_detector.py --method dual_space  # 单方法
  python tools/sc1_detector.py --report     # 只看报告
"""
import argparse
import json
import os
import re
import random
from collections import defaultdict

import networkx as nx
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "data/gjb_438c/data_assets")
GOLD_DIR = os.path.join(ASSETS, "gold_standard")
GRAPH_DIR = os.path.join(ASSETS, "graph")
STAGE0 = os.path.join(ASSETS, "stage0_assets.json")


# ========== 基础工具 ==========
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


def load_data():
    """加载stage0和sc1 Gold Standard"""
    s0 = json.loads(open(STAGE0, encoding="utf-8").read())
    id_reg = s0['id_registry']
    gs = json.loads(open(os.path.join(GOLD_DIR, 'multi_scene_gold_standard.json'), encoding="utf-8").read())
    sc1 = gs['scenes']['scene1']

    # 实体→名称(多位置ID)
    entity_names = {}
    for rid, entries in id_reg.items():
        if len(entries) < 2:
            continue
        names = set()
        for e in entries:
            n = extract_name(e.get('context', ''), rid)
            if n and len(n) >= 2:
                names.add(n)
        if names:
            entity_names[rid] = names

    # Gold真实矛盾
    gold_conflicts = set(n.get('entity_id', '') for n in sc1['negatives'] if n.get('source') == 'real')

    return entity_names, gold_conflicts


class SC1Detector:
    """场景1名称一致性检测器"""

    def __init__(self, sim_threshold=0.55, seed=42):
        self.entity_names, self.gold_conflicts = load_data()
        self.sim_threshold = sim_threshold
        self.seed = seed
        self.all_names = sorted(set(n for names in self.entity_names.values() for n in names))
        self.name2idx = {n: i for i, n in enumerate(self.all_names)}
        self.G = self._build_semantic_graph()
        self.results = {}

    # ---------- 图构建 ----------
    def _build_semantic_graph(self):
        """语义图: 名称按文本相似度连边"""
        G = nx.Graph()
        for n in self.all_names:
            G.add_node(n)
        for i, a in enumerate(self.all_names):
            for j in range(i + 1, len(self.all_names)):
                b = self.all_names[j]
                if abs(len(a) - len(b)) > 4:
                    continue
                sim = text_sim(a, b)
                if sim >= self.sim_threshold:
                    G.add_edge(a, b, weight=sim)
        return G

    # ---------- 评测 ----------
    def evaluate(self, detected, method_name):
        """评测: P/R/F1 + 分层 + 真实矛盾"""
        tp = fp = fn = 0
        for rid in self.entity_names:
            pred = rid in detected
            gold = rid in self.gold_conflicts
            if pred and gold:
                tp += 1
            elif pred and not gold:
                fp += 1
            elif not pred and gold:
                fn += 1
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        result = {
            'method': method_name,
            'P': round(p, 3),
            'R': round(r, 3),
            'F1': round(f1, 3),
            'TP': tp, 'FP': fp, 'FN': fn,
            'detected_count': len(detected),
        }
        self.results[method_name] = result
        return result

    # ---------- 方法1: 字符级(连通分量) ----------
    def detect_connected_components(self):
        """B1: 实体名称在图上的连通分量, 分裂=矛盾"""
        detected = set()
        for rid, names in self.entity_names.items():
            if len(names) < 2:
                continue
            comps = list(nx.connected_components(self.G.subgraph(names)))
            if len(comps) > 1:
                detected.add(rid)
        return detected

    # ---------- 方法2: Louvain社区 ----------
    def detect_louvain(self):
        """B2: Louvain社区, 实体名称跨社区=矛盾"""
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
        """B3: 谱聚类(拉普拉斯特征映射+层次聚类)"""
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
        embed = eigvecs[:, 1:11]  # 谱嵌入

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

    # ---------- 方法4: 学习检测器(逻辑回归) ----------
    def detect_learned(self, train_epochs=500):
        """B4: 逻辑回归(特征学习), 参数传递避免闭包作用域问题"""
        # 训练数据: Gold Standard的名称对
        gs = json.loads(open(os.path.join(GOLD_DIR, 'multi_scene_gold_standard.json'), encoding="utf-8").read())
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

        # 参数传递的预测器(不依赖闭包)
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
        """B5: 手写GCN(图传播) + 双空间"""
        n_names = len(self.all_names)

        # 邻接矩阵
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

        # 字符bigram特征
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

        # GCN前向(无监督)
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

        # 双空间: GCN拓扑 + 文本
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

    # ---------- 方法6: 图注意力(学习边权重) ----------
    def detect_graph_attention(self):
        """O1: 学习边权重(逻辑回归预测边存在概率)"""
        def edge_feats(a, b):
            d = levenshtein(a, b)
            ml = max(len(a), len(b), 1)
            return np.array([1.0 - d / ml, float(d),
                             float(len(set(a) & set(b))) / float(max(len(set(a) | set(b)), 1)),
                             1.0 if a[:2] == b[:2] else 0.0,
                             float(min(len(a), len(b))) / float(ml)], dtype=np.float64)

        # 训练: 同实体=正边, 不同实体=负边
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
        y = np.array([float(lab) for _, _, lab in pairs], dtype=np.float64)
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

        # 参数传递的边概率预测器
        def make_edge_predictor(weights, bias, x_mean, x_std):
            def edge_prob(a, b):
                x = edge_feats(a, b)
                xn = (x - x_mean) / x_std
                return float(1 / (1 + np.exp(-(xn @ weights + bias))))
            return edge_prob

        edge_prob = make_edge_predictor(w, b, Xm, Xs)

        # 用学习权重构建图
        G_learn = nx.Graph()
        for n in self.all_names:
            G_learn.add_node(n)
        for i, a in enumerate(self.all_names):
            for j in range(i + 1, len(self.all_names)):
                b = self.all_names[j]
                prob = edge_prob(a, b)
                if prob > 0.5:
                    G_learn.add_edge(a, b, weight=prob)

        # 连通分量矛盾
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
        """O2: 异构图嵌入(拓扑) + 文本相似度"""
        # 构建异构图
        G_hetero = nx.Graph()
        name_entities = defaultdict(list)
        for rid, names in self.entity_names.items():
            G_hetero.add_node(f'E:{rid}', type='entity')
            for n in names:
                if f'M:{n}' not in G_hetero:
                    G_hetero.add_node(f'M:{n}', type='name')
                G_hetero.add_edge(f'E:{rid}', f'M:{n}', type='has_name')
                name_entities[n].append(rid)

        # 名称-名称相似边
        for i, a in enumerate(self.all_names):
            for j in range(i + 1, len(self.all_names)):
                b = self.all_names[j]
                if abs(len(a) - len(b)) > 4:
                    continue
                sim = text_sim(a, b)
                if sim >= 0.5:
                    G_hetero.add_edge(f'M:{a}', f'M:{b}', type='similar', weight=sim)

        # 用独立Random实例, 彻底隔离全局state(保证可复现)
        rng = random.Random(self.seed)

        def metapath_walk(start, walk_len=10, rng=rng):
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
        for _ in range(30):
            rng.shuffle(entity_nodes)
            for e in entity_nodes[:100]:
                walks.append(metapath_walk(e, 12))

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
        embeddings = U[:, :32] * np.sqrt(S[:32])
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        emb = {n: embeddings[i] / norms[i] for i, n in enumerate(vocab)}

        def topo_sim(a, b):
            ka, kb = f'M:{a}', f'M:{b}'
            if ka in emb and kb in emb:
                return float(emb[ka] @ emb[kb])
            return None

        # 双空间矛盾: 同实体(topo>0.7) + 文本不相似(text<0.6)
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
        """运行全部7种方法并评测"""
        print("=" * 65)
        print("SC1名称一致性检测: 7种方法评测")
        print(f"实体: {len(self.entity_names)}, Gold真实矛盾: {len(self.gold_conflicts)}")
        print("=" * 65)

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
            print(f"  运行 {name} ...")
            detected = fn()
            result = self.evaluate(detected, name)
            print(f"    P={result['P']} R={result['R']} F1={result['F1']} (TP{result['TP']} FP{result['FP']} FN{result['FN']})")

        self.save_results()
        return self.results

    def save_results(self):
        """保存结果"""
        os.makedirs(GRAPH_DIR, exist_ok=True)
        out = os.path.join(GRAPH_DIR, 'sc1_all_methods_eval.json')
        json.dump(self.results, open(out, 'w', encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n已保存: {out}")


def main():
    parser = argparse.ArgumentParser(description='SC1名称一致性检测')
    parser.add_argument('--method', choices=['connected', 'louvain', 'spectral', 'learned', 'gcn', 'attention', 'dual_space'],
                        help='单方法运行')
    parser.add_argument('--all', action='store_true', help='运行全部方法')
    args = parser.parse_args()

    detector = SC1Detector()

    if args.all:
        detector.run_all()
    elif args.method:
        method_map = {
            'connected': detector.detect_connected_components,
            'louvain': detector.detect_louvain,
            'spectral': detector.detect_spectral,
            'learned': detector.detect_learned,
            'gcn': detector.detect_gcn,
            'attention': detector.detect_graph_attention,
            'dual_space': detector.detect_dual_space,
        }
        fn = method_map.get(args.method)
        if fn:
            detected = fn()
            result = detector.evaluate(detected, args.method)
            print(f"P={result['P']} R={result['R']} F1={result['F1']}")
            detector.save_results()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
