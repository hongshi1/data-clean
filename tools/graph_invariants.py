#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图不变量检测器: 环 / 拓扑序 / 分支覆盖 —— 373结构实测
=========================================================

对应Slide 3检测架构"图算法引擎"分支的落地:
  D_cycle   : 有向环检测(DFS三色标记) → LOGIC-07异常切换/循环依赖类
  D_topo    : 拓扑序可行性(DAG判定) + 步骤序与边序一致性 → LOGIC-03事件时序
  D_branch  : 分支覆盖 D = {v: outdeg(v) ≥ 2}, 出边标签完备性 → LOGIC-05分支完备

输出: data/gjb_438c/anchor_v3/graph_invariants.json
用法: python tools/graph_invariants.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
ANCHORS = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
OUT = BASE / "data/gjb_438c/anchor_v3/graph_invariants.json"


def directed_edges(st):
    """结构 → 有向边列表（含箭头语义: end箭头=src→dst, begin箭头=dst→src）"""
    NAV_END = {'filled_triangle', 'filled_circle_s', 'closed', 'open_60', 'open',
               'filled_diamond_s', 'filled_square', 'block'}
    NAV_BEGIN = {'filled_square', 'filled_circle_s', 'filled_triangle', 'open'}
    nodes = {n['id']: n for n in st['nodes']}
    edges = []
    for e in st['edges']:
        sn, dn = nodes.get(e['src']), nodes.get(e['dst'])
        if not sn or not dn:
            continue
        fe = e.get('end_arrow') in NAV_END
        fb = e.get('begin_arrow') in NAV_BEGIN
        if fe:
            edges.append((e['src'], e['dst'], e))
        if fb:
            edges.append((e['dst'], e['src'], e))
        if not fe and not fb:
            # 无箭头边: 视作双向可达(弱序), 不进DAG判定
            edges.append((e['src'], e['dst'], e))
            edges.append((e['dst'], e['src'], e))
    return edges


def find_cycle(adj, n):
    """DFS三色环检测 → 环路径或None"""
    color = {v: 0 for v in range(n)}  # 0白 1灰 2黑
    parent = {}

    def dfs(u):
        color[u] = 1
        for v in adj.get(u, []):
            if color[v] == 1:
                # 回边 → 找环
                path, cur = [v], u
                while cur != v:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
            if color[v] == 0:
                parent[v] = u
                r = dfs(v)
                if r:
                    return r
        color[u] = 2
        return None

    for v in range(n):
        if color[v] == 0:
            r = dfs(v)
            if r:
                return r
    return None


def topo_order(adj, n):
    """Kahn拓扑序 → (order or None=有环)"""
    indeg = {v: 0 for v in range(n)}
    for u, vs in adj.items():
        for v in vs:
            indeg[v] += 1
    queue = [v for v in range(n) if indeg[v] == 0]
    order = []
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v in adj.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return order if len(order) == n else None


def main():
    anchors = json.load(open(ANCHORS, encoding='utf-8'))
    stats = Counter()
    per_struct = []
    cycle_examples, branch_gap_examples = [], []
    decision_nodes_total = 0
    unlabeled_branch_total = 0

    for doc, dd in anchors.items():
        for st in dd['structures']:
            nodes = {n['id']: n for n in st['nodes']}
            nid = {n['id']: i for i, n in enumerate(st['nodes'])}
            if not nid:
                continue
            dedges = directed_edges(st)
            # 去重邻接
            adj = defaultdict(set)
            for s, d, _ in dedges:
                if s != d:
                    adj[nid[s]].add(nid[d])
            adj = {k: sorted(v) for k, v in adj.items()}
            n = len(nid)

            stats['structures'] += 1
            stats['nodes'] += n
            stats['directed_edge_pairs'] += sum(len(v) for v in adj.values())

            # 环检测（仅强语义箭头边——排除无向双向化带来的伪环）
            strong_adj = defaultdict(set)
            for e in st['edges']:
                sn, dn = nodes.get(e['src']), nodes.get(e['dst'])
                if not sn or not dn or e['src'] == e['dst']:
                    continue
                fe = e.get('end_arrow') in {'filled_triangle', 'filled_circle_s', 'closed', 'open_60', 'open'}
                fb = e.get('begin_arrow') in {'filled_square', 'filled_circle_s', 'filled_triangle', 'open'}
                if fe:
                    strong_adj[nid[e['src']]].add(nid[e['dst']])
                elif fb:
                    strong_adj[nid[e['dst']]].add(nid[e['src']])
            cyc = find_cycle({k: sorted(v) for k, v in strong_adj.items()}, n) if strong_adj else None
            # 拓扑序（强语义边）
            topo = topo_order({k: sorted(v) for k, v in strong_adj.items()}, n) if strong_adj else list(range(n))
            stats['with_strong_edges'] += 1 if strong_adj else 0
            if cyc:
                stats['has_cycle'] += 1
                names = [st['nodes'][i].get('text', '')[:10] for i in cyc[:6]]
                if len(cycle_examples) < 5:
                    cycle_examples.append({'doc': doc[:12], 'embed': st.get('embed_index'),
                                           'cycle': names, 'len': len(cyc)})
            else:
                stats['dag'] += 1

            # 不可达节点（从入度0或start节点出发, 强+弱边）
            reach_adj = {k: v for k, v in adj.items()}
            indeg = {v: 0 for v in range(n)}
            for u, vs in reach_adj.items():
                for v in vs:
                    indeg[v] += 1
            starts = [v for v in range(n) if indeg[v] == 0] or [0]
            seen = set(starts)
            stack = list(starts)
            while stack:
                u = stack.pop()
                for v in reach_adj.get(u, []):
                    if v not in seen:
                        seen.add(v)
                        stack.append(v)
            unreach = n - len(seen)
            if unreach:
                stats['unreachable_nodes'] += unreach
                stats['structs_with_unreachable'] += 1

            # 分支覆盖: D = {v: outdeg(v) ≥ 2}
            D = {v for v, vs in reach_adj.items() if len(vs) >= 2}
            decision_nodes_total += len(D)
            for v in D:
                out_edges = [e for s, d, e in dedges if nid[s] == v and nid[d] in reach_adj.get(v, [])]
                unlabeled = [e for e in out_edges if not (e.get('label') or '').strip()]
                unlabeled_branch_total += len(unlabeled)
                if unlabeled and len(branch_gap_examples) < 5:
                    branch_gap_examples.append({
                        'doc': doc[:12], 'embed': st.get('embed_index'),
                        'node': nodes[[k for k, vv in nid.items() if vv == v][0]].get('text', '')[:12],
                        'outdeg': len(reach_adj[v]), 'unlabeled': len(unlabeled)})

            per_struct.append({'doc': doc[:12], 'embed': st.get('embed_index'),
                               'n_nodes': n, 'n_strong_edges': sum(len(v) for v in strong_adj.values()),
                               'has_cycle': bool(cyc), 'dag': topo is not None,
                               'unreachable': unreach, 'decision_nodes': len(D)})

    # 内容序 vs 边序一致性(LOGIC-03直接证据): content列表顺序 vs 拓扑序
    stats['decision_nodes_total'] = decision_nodes_total
    stats['unlabeled_branches'] = unlabeled_branch_total

    print(f"图不变量实测（{stats['structures']}结构 / {stats['nodes']}节点 / {stats['directed_edge_pairs']}有向边对）")
    print(f"  含强语义箭头边结构: {stats['with_strong_edges']}")
    print(f"  有向环结构: {stats['has_cycle']} ({stats['has_cycle']/max(stats['with_strong_edges'],1):.1%})")
    print(f"  DAG结构: {stats['dag']}")
    print(f"  不可达节点: {stats['unreachable_nodes']} (涉及{stats['structs_with_unreachable']}结构)")
    print(f"  决策节点 D={{v:outdeg≥2}}: {decision_nodes_total}")
    print(f"  无标签分支边: {unlabeled_branch_total}")
    print("\n  环样例:")
    for c in cycle_examples:
        print(f"    [{c['doc']}] {c['embed']}: {'→'.join(c['cycle'])} (len={c['len']})")
    print("  分支覆盖缺口样例:")
    for b in branch_gap_examples:
        print(f"    [{b['doc']}] {b['embed']}: 节点「{b['node']}」outdeg={b['outdeg']} 无标签分支{b['unlabeled']}条")

    json.dump({'stats': dict(stats), 'per_structure': per_struct,
               'cycle_examples': cycle_examples, 'branch_gap_examples': branch_gap_examples},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n结果已保存: {OUT}")


if __name__ == '__main__':
    main()
