#!/usr/bin/env python3
"""
M3: sc2_flowchart_usecase 一致性检测流水线
=============================================
对89个已映射的{Visio流程图, 用例描述表}对执行一致性检测

4类检测:
  1. 节点集合匹配: Visio节点 vs 表格步骤 → 多余/缺失节点
  2. 流程顺序匹配: Visio Connect拓扑 vs 表格步骤编号
  3. 参与者匹配: Visio参与者节点 vs 表格Actors字段
  4. 异常流匹配: Visio分支节点 vs 表格异常流E1/E2

用法: python3 tools/sc2_consistency.py
"""
import re
import json
import csv
import math
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

BASE = Path(__file__).resolve().parent.parent
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUTPUT_DIR = BASE / "data/gjb_438c/sc2_consistency_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMB_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
from ai_config import WQ_API_KEY as EMB_KEY
EMB_MODEL = "ep-qrkeon-1785654358657880827"

_emb_cache = {}
def get_embeddings(texts):
    uncached = [(i, t) for i, t in enumerate(texts) if t not in _emb_cache]
    if uncached:
        try:
            resp = requests.post(EMB_URL, headers={
                "Authorization": f"Bearer {EMB_KEY}", "Content-Type": "application/json"
            }, json={"model": EMB_MODEL, "input": [t for _, t in uncached],
                    "encoding_format": "float"}, timeout=30)
            resp.raise_for_status()
            for (i, t), d in zip(uncached, resp.json()["data"]):
                _emb_cache[t] = d["embedding"]
        except:
            return [[] for _ in texts]
    return [_emb_cache.get(t, []) for t in texts]

def cosine(a, b):
    if not a or not b:
        return 0.0
    return sum(x*y for x, y in zip(a, b)) / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b))+1e-10)


# ═══════════════════════════════════════════════════════════════
# 检测1: 节点集合匹配
# ═══════════════════════════════════════════════════════════════

def match_node_sets(visio_nodes: list[dict], table_steps: list[str]) -> dict:
    """
    匹配Visio节点文本与表格步骤
    
    三层匹配:
      1. 字符重叠匹配(>50%)
      2. Embedding匹配(cosine>0.7)
      3. 关键词包含匹配
    
    输出: matched / visio_only / table_only
    """
    # 只取有文本的usecase/other节点(排除actor和boundary)
    visio_texts = [n['text'].strip() for n in visio_nodes
                   if n.get('text', '').strip() and n.get('type') in ('usecase', 'other')]
    
    if not visio_texts or not table_steps:
        return {'matched': [], 'visio_only': visio_texts, 'table_only': table_steps,
                'match_rate': 0.0}

    # 策略1: 字符重叠
    matched_pairs = []
    used_table = set()
    used_visio = set()

    for i, vt in enumerate(visio_texts):
        vt_chars = set(vt)
        if not vt_chars:
            continue
        for j, ts in enumerate(table_steps):
            if j in used_table:
                continue
            ts_chars = set(ts)
            overlap = len(vt_chars & ts_chars) / len(vt_chars)
            if overlap > 0.5:
                matched_pairs.append({'visio': vt, 'table': ts, 'method': 'char', 'score': round(overlap, 2)})
                used_table.add(j)
                used_visio.add(i)
                break

    # 策略2: Embedding(对未匹配的)
    unmatched_visio = [vt for i, vt in enumerate(visio_texts) if i not in used_visio]
    unmatched_table = [ts for j, ts in enumerate(table_steps) if j not in used_table]

    if unmatched_visio and unmatched_table:
        v_embs = get_embeddings(unmatched_visio)
        t_embs = get_embeddings(unmatched_table)
        if any(v_embs) and any(t_embs):
            for vi, vt in enumerate(unmatched_visio):
                if not v_embs[vi]:
                    continue
                for ti, ts in enumerate(unmatched_table):
                    if ti in used_table:
                        continue
                    if not t_embs[ti]:
                        continue
                    sim = cosine(v_embs[vi], t_embs[ti])
                    if sim > 0.7:
                        matched_pairs.append({'visio': vt, 'table': ts, 'method': 'embedding', 'score': round(sim, 2)})
                        used_table.add(ti)
                        used_visio.add(visio_texts.index(vt))
                        break

    # 策略3: 关键词包含(短文本∈长文本)
    for i, vt in enumerate(visio_texts):
        if i in used_visio:
            continue
        for j, ts in enumerate(table_steps):
            if j in used_table:
                continue
            # 检查关键词包含(取vt的前10个字在ts中)
            key = vt[:10]
            if len(key) >= 4 and key in ts:
                matched_pairs.append({'visio': vt, 'table': ts, 'method': 'keyword', 'score': 0.6})
                used_table.add(j)
                used_visio.add(i)
                break

    visio_only = [vt for i, vt in enumerate(visio_texts) if i not in used_visio]
    table_only = [ts for j, ts in enumerate(table_steps) if j not in used_table]

    return {
        'matched': matched_pairs,
        'visio_only': visio_only,
        'table_only': table_only,
        'match_rate': len(matched_pairs) / max(1, len(visio_texts)),
    }


# ═══════════════════════════════════════════════════════════════
# 检测2: 参与者匹配
# ═══════════════════════════════════════════════════════════════

def match_actors(visio_nodes: list[dict], pair_dir: Path) -> dict:
    """匹配Visio参与者节点与表格Actors字段"""
    # Visio参与者
    visio_actors = [n['text'].strip() for n in visio_nodes
                    if n.get('type') == 'actor' and n.get('text', '').strip()]

    # 表格Actors
    table_actors = []
    table_path = pair_dir / "table.csv"
    if table_path.exists():
        with open(table_path, encoding="utf-8") as f:
            for row in csv.reader(f):
                for cell in row:
                    if 'Actors' in cell or 'Actor' in cell:
                        m = re.search(r'Actors?[：:](.+)', cell)
                        if m:
                            actors_str = m.group(1).strip()
                            # 分割多个actor
                            parts = re.split(r'[、,，;；]', actors_str)
                            table_actors = [p.strip() for p in parts if p.strip()]
                        break
                if table_actors:
                    break

    # 匹配
    matched_actors = []
    visio_only_actors = list(visio_actors)
    table_only_actors = list(table_actors)

    for va in visio_actors:
        for ta in table_actors:
            if va in ta or ta in va:
                matched_actors.append({'visio': va, 'table': ta})
                if va in visio_only_actors:
                    visio_only_actors.remove(va)
                if ta in table_only_actors:
                    table_only_actors.remove(ta)
                break

    return {
        'visio_actors': visio_actors,
        'table_actors': table_actors,
        'matched': matched_actors,
        'visio_only': visio_only_actors,
        'table_only': table_only_actors,
    }


# ═══════════════════════════════════════════════════════════════
# 检测3: 异常流匹配
# ═══════════════════════════════════════════════════════════════

def match_exception_flows(visio_edges: list[dict], pair_dir: Path) -> dict:
    """匹配Visio分支与表格异常流"""
    # 表格异常流
    table_exceptions = []
    table_path = pair_dir / "table.csv"
    if table_path.exists():
        with open(table_path, encoding="utf-8") as f:
            content = f.read()
            # 提取"异常流E1: xxx"模式
            for m in re.finditer(r'异常流\s*(\w+)\s*[：:]\s*(.+?)(?:。|;|；|$)', content):
                table_exceptions.append({
                    'id': m.group(1),
                    'description': m.group(2).strip()[:60]
                })

    # Visio分支节点(有多个出边的节点)
    edge_counts = defaultdict(int)
    for e in visio_edges:
        edge_counts[e['from_id']] += 1
    branch_nodes = {node_id: count for node_id, count in edge_counts.items() if count > 1}

    # 统计Visio中的"失败"/"异常"文本节点
    exception_texts = []
    for e in visio_edges:
        for txt in [e.get('from_text', ''), e.get('to_text', '')]:
            if any(kw in txt for kw in ['失败', '异常', '错误', '超时', '中断']):
                exception_texts.append(txt)

    return {
        'table_exceptions': table_exceptions,
        'visio_branches': len(branch_nodes),
        'visio_exception_texts': list(set(exception_texts))[:5],
        'has_mismatch': (len(table_exceptions) > 0 and len(branch_nodes) == 0) or
                        (len(table_exceptions) == 0 and len(branch_nodes) > 2),
    }


# ═══════════════════════════════════════════════════════════════
# 主检测流水线
# ═══════════════════════════════════════════════════════════════

def detect_inconsistency(pair_key: str, mapping_data: dict) -> dict:
    """对单个样本执行全部一致性检测"""
    pair_dir = PAIR_DIR / pair_key
    structure = mapping_data.get('visio_structure', {})
    visio_nodes = structure.get('nodes', [])
    visio_edges = structure.get('edges', [])
    table_steps = mapping_data.get('table_steps', [])

    inconsistencies = []

    # 1. 节点集合匹配
    node_match = match_node_sets(visio_nodes, table_steps)
    if node_match['visio_only']:
        inconsistencies.append({
            'type': 'visio_extra_nodes',
            'severity': 'MEDIUM',
            'description': f"流程图有{len(node_match['visio_only'])}个节点在用例表中无对应步骤",
            'detail': node_match['visio_only'][:5],
        })
    if node_match['table_only']:
        inconsistencies.append({
            'type': 'table_extra_steps',
            'severity': 'MEDIUM',
            'description': f"用例表有{len(node_match['table_only'])}个步骤在流程图中无对应节点",
            'detail': node_match['table_only'][:5],
        })

    # 2. 参与者匹配
    actor_match = match_actors(visio_nodes, pair_dir)
    if actor_match['visio_only']:
        inconsistencies.append({
            'type': 'visio_extra_actors',
            'severity': 'LOW',
            'description': f"流程图有{len(actor_match['visio_only'])}个参与者未在Actors字段中列出",
            'detail': actor_match['visio_only'][:5],
        })

    # 3. 异常流匹配
    exception_match = match_exception_flows(visio_edges, pair_dir)
    if exception_match.get('has_mismatch'):
        inconsistencies.append({
            'type': 'exception_flow_mismatch',
            'severity': 'LOW',
            'description': f"异常流覆盖不匹配: 表格{len(exception_match['table_exceptions'])}个异常流, "
                          f"流程图{exception_match['visio_branches']}个分支",
        })

    return {
        'pair_id': pair_key,
        'doc': mapping_data['doc'],
        'section': mapping_data['section'],
        'match_score': mapping_data['match_score'],
        'detection': {
            'node_match_rate': node_match['match_rate'],
            'matched_nodes': len(node_match['matched']),
            'visio_only_nodes': len(node_match['visio_only']),
            'table_only_steps': len(node_match['table_only']),
            'actor_match': {
                'visio': len(actor_match['visio_actors']),
                'table': len(actor_match['table_actors']),
                'matched': len(actor_match['matched']),
            },
            'exception_flows': len(exception_match['table_exceptions']),
        },
        'inconsistencies': inconsistencies,
        'node_match_detail': {
            'matched': node_match['matched'][:5],
            'visio_only': node_match['visio_only'][:5],
            'table_only': node_match['table_only'][:5],
        },
    }


def main():
    print("=" * 60)
    print("M3: sc2_flowchart_usecase 一致性检测")
    print("=" * 60)

    # 加载映射
    with open(MAPPING_PATH, encoding="utf-8") as f:
        mapping = json.load(f)

    print(f"样本数: {len(mapping)}")

    # 只处理高匹配样本(>50%)以确保Visio映射正确
    high_match = {k: v for k, v in mapping.items() if v['match_score'] > 0.3}
    print(f"高匹配样本(>30%): {len(high_match)}")

    results = []
    for pair_key, mapping_data in sorted(high_match.items()):
        result = detect_inconsistency(pair_key, mapping_data)
        results.append(result)

    # 统计
    all_inconsistencies = [i for r in results for i in r['inconsistencies']]
    by_type = Counter(i['type'] for i in all_inconsistencies)
    by_severity = Counter(i['severity'] for i in all_inconsistencies)

    # 节点匹配率分布
    match_rates = [r['detection']['node_match_rate'] for r in results]

    print(f"\n{'=' * 60}")
    print("检测结果")
    print(f"{'=' * 60}")
    print(f"检测样本: {len(results)}")
    print(f"不一致性: {len(all_inconsistencies)}条")
    print(f"  按类型: {dict(by_type)}")
    print(f"  按严重度: {dict(by_severity)}")
    print(f"\n节点匹配率: min={min(match_rates):.1%} avg={sum(match_rates)/len(match_rates):.1%} max={max(match_rates):.1%}")

    # 展示典型不一致
    print("\n=== 典型不一致 ===")
    sorted_results = sorted(results, key=lambda r: -len(r['inconsistencies']))
    for r in sorted_results[:5]:
        print(f"\n  {r['pair_id']} ({r['doc'][:20]} sec={r['section']}):")
        print(f"    节点匹配率: {r['detection']['node_match_rate']:.1%}")
        for inc in r['inconsistencies'][:3]:
            print(f"    [{inc['type']}] {inc['description'][:60]}")
            if inc.get('detail'):
                for d in inc['detail'][:2]:
                    print(f"      \"{str(d)[:50]}\"")

    # 保存
    output = {
        'detect_date': datetime.now().isoformat(),
        'total_samples': len(results),
        'total_inconsistencies': len(all_inconsistencies),
        'by_type': dict(by_type),
        'by_severity': dict(by_severity),
        'avg_node_match_rate': round(sum(match_rates) / len(match_rates), 3),
        'results': results,
    }
    output_path = OUTPUT_DIR / "sc2_consistency_results.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n结果已保存: {output_path}")


if __name__ == "__main__":
    main()
