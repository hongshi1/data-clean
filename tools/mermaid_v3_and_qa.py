#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强版Mermaid导出 + UML关系QA合成

Part A: 将anchor_v3(含UML关系)导出为语义丰富的mermaid
Part B: 基于UML关系生成新的QA对(正例+负例)
Part C: 新的不一致检测项(基于UML关系)

UML → Mermaid映射:
  ASSOCIATION   → A --- B              (无箭头实线)
  DIRECTED      → A --- B              (有箭头实线: -->)
  DEPENDENCY    → A -.-> B             (虚线箭头)
  INCLUDE       → A -.-> B : <<include>>
  EXTEND        → A -.-> B : <<extend>>
  GENERALIZATION→ A --|> B             (空心三角)
  COMPOSITION   → A --* B              (实心菱形)
  AGGREGATION   → A --o B              (空心菱形)
  REALIZATION   → A ..|> B             (虚线+实心三角)
"""
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
V3_PATH = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
MM_OUT = BASE / "data/gjb_438c/anchor_v3/mermaid_v3.json"
QA_OUT = BASE / "data/gjb_438c/anchor_v3/uml_qa_pairs.json"

# Mermaid UML关系渲染模板
UML_MERMAID = {
    'ASSOCIATION': '{a} --- {b}',
    'DIRECTED': '{a} --> {b}',
    'DEPENDENCY': '{a} -.-> {b}',
    'INCLUDE': '{a} -.-> {b} : <<include>>',
    'EXTEND': '{a} -.-> {b} : <<extend>>',
    'GENERALIZATION': '{a} --|> {b}',
    'COMPOSITION': '{a} --* {b}',
    'AGGREGATION': '{a} --o {b}',
    'REALIZATION': '{a} ..|> {b}',
}

# UML关系→业务语义描述
UML_SEMANTICS = {
    'ASSOCIATION': '关联',
    'DIRECTED': '有向关联',
    'DEPENDENCY': '依赖',
    'INCLUDE': '包含',
    'EXTEND': '扩展',
    'GENERALIZATION': '泛化',
    'COMPOSITION': '组合',
    'AGGREGATION': '聚合',
    'REALIZATION': '实现',
}

# Mermaid节点形状
NODE_SHAPES = {
    'actor': '{id}([\"{text}\"])',
    'usecase': '{id}(\"{text}\")',
    'process': '{id}[\"{text}\"]',
    'decision': '{id}{{\"{text}\"}}',
    'start': '{id}([start])',
    'end': '{id}([end])',
    'state': '{id}(\"{text}\")',
    'boundary': '{id}[\"{text}\"]',
    'fork': '{id}{{\"{text}\"}}',
    'component': '{id}[\"{text}\"]',
    'interface': '{id}(\"{text}\")',
    'class': '{id}[\"{text}\"]',
    'note': '{id}(\"{text}\")',
    'other': '{id}[\"{text}\"]',
}


def node_label(node):
    text = node.get('text', '')
    return text.replace('\n', ' ').replace('"', "'")[:30] if text else node['id']


def structure_to_mermaid_v3(structure):
    """将增强版锚点结构转为带UML语义的mermaid"""
    nodes = structure.get('nodes', [])
    edges = structure.get('edges', [])

    if not nodes:
        return None

    lines = []
    node_ids = set()
    uml_types = defaultdict(int)

    # 确定图类型(根据节点类型分布)
    node_types = defaultdict(int)
    for n in nodes:
        node_types[n.get('type', 'other')] += 1

    has_usecase = node_types.get('usecase', 0) > 0
    has_actor = node_types.get('actor', 0) > 0
    has_state = node_types.get('state', 0) > 0

    if has_usecase and has_actor:
        diagram_type = 'usecase'
        lines.append('graph TD')
    elif has_state:
        diagram_type = 'state'
        lines.append('graph TD')
    else:
        diagram_type = 'flowchart'
        lines.append('flowchart TD')

    # 节点声明
    for n in nodes:
        nid = n['id']
        text = node_label(n)
        lines.append(f'    {nid}["{text}"]')
        node_ids.add(nid)

    # 边(UML语义)
    for e in edges:
        src, dst = e.get('src', ''), e.get('dst', '')
        if src not in node_ids or dst not in node_ids:
            # 添加缺失的节点
            for nid, n in [(src, e), (dst, e)]:
                if nid and nid not in node_ids:
                    stext = e.get('src_text', '') if nid == src else e.get('dst_text', '')
                    lines.append(f'    {nid}["{stext[:20] if stext else nid}"]')
                    node_ids.add(nid)

        uml_type = e.get('uml_type', 'ASSOCIATION')
        uml_types[uml_type] += 1


        # 根据UML关系类型选择mermaid语法
        if uml_type == 'ASSOCIATION':
            lines.append(f'    {src} --- {dst}')
        elif uml_type == 'DIRECTED':
            lines.append(f'    {src} --> {dst}')
        elif uml_type in ('DEPENDENCY', 'INCLUDE', 'EXTEND'):
            label = e.get('label', '')
            stereotype = e.get('stereotype', '')
            if stereotype:
                lines.append(f'    {src} -.-> {dst} : {stereotype}')
            elif label:
                lines.append(f'    {src} -.-> {dst} : {label[:20]}')
            else:
                lines.append(f'    {src} -.-> {dst}')
        elif uml_type == 'REALIZATION':
            lines.append(f'    {src} ..|> {dst}')
        elif uml_type == 'COMPOSITION':
            lines.append(f'    {src} --* {dst}')
        elif uml_type == 'AGGREGATION':
            lines.append(f'    {src} --o {dst}')
        elif uml_type == 'GENERALIZATION':
            lines.append(f'    {src} --|> {dst}')
        else:
            lines.append(f'    {src} --> {dst}')

    mermaid_code = '\n'.join(lines)

    return {
        'mermaid': mermaid_code,
        'diagram_type': diagram_type,
        'n_nodes': len(nodes),
        'n_edges': len(edges),
        'uml_types': dict(uml_types),
        'embed_index': structure.get('embed_index', ''),
    }


# ============================================================================
# Part B: UML关系QA合成
# ============================================================================

# UML关系问答模板
UML_QA_TEMPLATES = {
    # 正例模板(语义等价变换)
    'positive': {
        'ASSOCIATION': [
            {
                'q': '图中「{src}」和「{dst}」之间是什么关系？',
                'a': '关联关系。两者直接相关，无方向性依赖。',
                'difficulty': 'easy',
            },
            {
                'q': '「{src}」与「{dst}」是否有关联？',
                'a': '是的，图中通过实线连接表示关联关系。',
                'difficulty': 'easy',
            },
        ],
        'REALIZATION': [
            {
                'q': '图中「{src}」如何实现「{dst}」？',
                'a': '「{src}」通过虚线实心三角箭头实现(realize)「{dst}」，表示前者实现了后者定义的接口或规范。',
                'difficulty': 'medium',
            },
        ],
        'COMPOSITION': [
            {
                'q': '「{src}」和「{dst}」是什么关系？组合还是聚合？',
                'a': '组合关系(composition)。实心菱形表示强拥有关系，{dst}是{src}的组成部分，生命周期一致。',
                'difficulty': 'medium',
            },
        ],
        'DEPENDENCY': [
            {
                'q': '「{src}」是否依赖「{dst}」？',
                'a': '是的，虚线箭头表示依赖关系，{src}依赖{dst}提供的功能或服务。',
                'difficulty': 'easy',
            },
        ],
    },
    # 负例模板(不一致注入)
    'negative': {
        'ASSOCIATION': [
            {
                'q': '图中「{src}」和「{dst}」之间的关系方向是什么？',
                'a': '图中显示「{dst}」指向「{src}」，即{dst}关联{src}。（实际方向相反，图中是{src}关联{dst}）',
                'inject': 'direction_reversal',
                'difficulty': 'medium',
            },
            {
                'q': '「{src}」和「{dst}」之间是包含关系还是关联关系？',
                'a': '是包含关系(include)，{src}包含{dst}。（实际是关联，非包含）',
                'inject': 'relationship_type_confusion',
                'difficulty': 'hard',
            },
        ],
        'REALIZATION': [
            {
                'q': '图中「{src}」与「{dst}」是泛化关系还是实现关系？',
                'a': '是泛化关系(generalization)，{src}是{dst}的子类型。（实际是实现关系realization）',
                'inject': 'uml_type_confusion',
                'difficulty': 'hard',
            },
            {
                'q': '「{src}」是否实现了「{dst}」？',
                'a': '没有，图中显示「{dst}」实现了「{src}」。（方向反了）',
                'inject': 'direction_reversal',
                'difficulty': 'medium',
            },
        ],
        'DEPENDENCY': [
            {
                'q': '「{src}」和「{dst}」之间的依赖方向是什么？',
                'a': '「{dst}」依赖「{src}」。（实际是{src}依赖{dst}）',
                'inject': 'direction_reversal',
                'difficulty': 'medium',
            },
        ],
        'COMPOSITION': [
            {
                'q': '「{src}」和「{dst}」之间是组合还是聚合？',
                'a': '是聚合关系(aggregation)，空心菱形。（实际是组合，实心菱形）',
                'inject': 'composition_vs_aggregation',
                'difficulty': 'hard',
            },
        ],
    },
}


def generate_uml_qa(anchors_v3):
    """基于UML关系生成QA对"""
    qa_pairs = []
    rng = random.Random(42)

    for doc_name, doc_data in anchors_v3.items():
        structures = doc_data.get('structures', [])
        doc_short = doc_name[:8]

        for st_idx, st in enumerate(structures):
            edges = st.get('edges', [])
            embed = st.get('embed_index', '')

            for e in edges:
                uml_type = e.get('uml_type', 'ASSOCIATION')
                src_text = e.get('src_text', '')[:15]
                dst_text = e.get('dst_text', '')[:15]
                if not src_text or not dst_text:
                    continue

                # 生成正例
                pos_templates = UML_QA_TEMPLATES['positive'].get(uml_type, [])
                if pos_templates:
                    tmpl = rng.choice(pos_templates)
                    qa_pairs.append({
                        'id': f'uml_{doc_short}_{st_idx}_{e["src"]}_{e["dst"]}_pos',
                        'pair_id': f'{doc_short}_{st_idx}',
                        'doc': doc_name,
                        'uml_type': uml_type,
                        'uml_semantic': UML_SEMANTICS.get(uml_type, '关联'),
                        'label': 'consistent',
                        'question': tmpl['q'].format(src=src_text, dst=dst_text),
                        'answer': tmpl['a'].format(src=src_text, dst=dst_text),
                        'difficulty': tmpl['difficulty'],
                        'evidence': {
                            'embed': embed,
                            'uml_type': uml_type,
                            'src': src_text,
                            'dst': dst_text,
                            'line_pattern': e.get('line_pattern', 'solid'),
                            'end_arrow': e.get('end_arrow', 'none'),
                        },
                        'source': 'uml_positive',
                    })

                # 生成负例
                neg_templates = UML_QA_TEMPLATES['negative'].get(uml_type, [])
                if neg_templates:
                    tmpl = rng.choice(neg_templates)
                    qa_pairs.append({
                        'id': f'uml_{doc_short}_{st_idx}_{e["src"]}_{e["dst"]}_neg',
                        'pair_id': f'{doc_short}_{st_idx}',
                        'doc': doc_name,
                        'uml_type': uml_type,
                        'uml_semantic': UML_SEMANTICS.get(uml_type, '关联'),
                        'label': 'inconsistent',
                        'inject_type': tmpl.get('inject', 'unknown'),
                        'question': tmpl['q'].format(src=src_text, dst=dst_text),
                        'answer': tmpl['a'].format(src=src_text, dst=dst_text),
                        'difficulty': tmpl['difficulty'],
                        'evidence': {
                            'embed': embed,
                            'uml_type': uml_type,
                            'src': src_text,
                            'dst': dst_text,
                            'line_pattern': e.get('line_pattern', 'solid'),
                            'end_arrow': e.get('end_arrow', 'none'),
                            'original_relation': uml_type,
                        },
                        'source': 'uml_negative',
                    })

    return qa_pairs


# ============================================================================
# Part C: 新的不一致检测项(基于UML关系)
# ============================================================================

def define_new_check_items():
    """定义基于UML关系的新检测项(扩展52项)"""

    new_items = [
        # UML语义层 (新增)
        _reg("UML-01", "UML语义层", "关联方向一致性",
             "图中A→B与表格/正文中A依赖B的方向是否一致",
             "用例图/接口图", "auto"),
        _reg("UML-02", "UML语义层", "实现关系方向",
             "虚线实心三角(realization)的方向是否与文档描述一致",
             "用例图/组件图", "auto"),
        _reg("UML-03", "UML语义层", "组合vs聚合",
             "实心菱形(组合)与空心菱形(聚合)是否正确使用",
             "类图/组件图", "auto"),
        _reg("UML-04", "UML语义层", "依赖关系完备性",
             "图中虚线箭头表示的依赖关系在表格/正文中是否有对应描述",
             "用例图/接口图", "auto"),
        _reg("UML-05", "UML语义层", "UML关系类型正确性",
             "图中使用的关系类型(关联/依赖/实现/组合)是否语义正确",
             "所有图", "llm"),
        _reg("UML-06", "UML语义层", "多模态UML一致性",
             "图中UML关系与表格行数据(发送方/接收方)是否一致",
             "用例图/接口图", "auto"),
        _reg("UML-07", "UML语义层", "构造型规范",
             "«include»/«extend»等构造型是否正确使用",
             "用例图", "auto"),
        _reg("UML-08", "UML语义层", "泳道一致性",
             "活动图中泳道/分区与正文角色分配是否一致",
             "活动图", "llm"),
    ]
    return new_items


def _reg(id, category, name, desc, modality, mode):
    return {"id": id, "category": category, "name": name,
            "desc": desc, "modality": modality, "mode": mode}


# ============================================================================
# 主流程
# ============================================================================

def main():
    print("=" * 70)
    print("增强版Mermaid导出 + UML关系QA合成")
    print("=" * 70)

    # 加载增强锚点
    anchors = json.load(open(V3_PATH, encoding="utf-8"))
    print(f"加载锚点: {len(anchors)}文档")

    # Part A: Mermaid导出
    mermaid_exports = {}
    uml_total = defaultdict(int)

    for doc_name, doc_data in anchors.items():
        for st in doc_data.get('structures', []):
            mm = structure_to_mermaid_v3(st)
            if mm and mm['n_nodes'] > 0:
                key = f"{doc_name[:8]}:{st['embed_index']}"
                mermaid_exports[key] = mm
                for ut, cnt in mm['uml_types'].items():
                    uml_total[ut] += cnt

    # 保存mermaid
    os.makedirs(os.path.dirname(MM_OUT), exist_ok=True)
    json.dump(mermaid_exports, open(MM_OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nMermaid导出: {len(mermaid_exports)}图")
    print(f"UML关系分布: {dict(uml_total)}")

    # Part B: UML QA合成
    qa_pairs = generate_uml_qa(anchors)
    pos = sum(1 for q in qa_pairs if q['label'] == 'consistent')
    neg = sum(1 for q in qa_pairs if q['label'] == 'inconsistent')

    os.makedirs(os.path.dirname(QA_OUT), exist_ok=True)
    json.dump(qa_pairs, open(QA_OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nUML QA合成: {len(qa_pairs)}条 (正例{pos} / 负例{neg})")

    # 按UML类型统计
    by_type = defaultdict(lambda: {'pos': 0, 'neg': 0})
    for q in qa_pairs:
        t = q['uml_type']
        by_type[t]['pos' if q['label'] == 'consistent' else 'neg'] += 1
    print("按UML关系类型:")
    for t, counts in sorted(by_type.items()):
        print(f"  {t:15s}: 正{counts['pos']:4d} 负{counts['neg']:4d}")

    # Part C: 新检测项定义
    new_items = define_new_check_items()
    print(f"\n新增检测项: {len(new_items)}项 (UML-01~08)")
    for it in new_items:
        print(f"  [{it['id']}] {it['name']} ({it['mode']})")

    # 保存
    items_out = BASE / "data/gjb_438c/anchor_v3/uml_check_items.json"
    json.dump(new_items, open(items_out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"\n{'='*60}")
    print("完成! 输出文件:")
    print(f"  Mermaid: {MM_OUT}")
    print(f"  QA对:   {QA_OUT}")
    print(f"  检测项: {items_out}")


if __name__ == "__main__":
    main()
