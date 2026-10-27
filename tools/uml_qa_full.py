#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全UML关系QA模板扩展版: 9种关系 + 跨图 + 组合变异 + 节点级 + 边标签

覆盖维度:
  A. 9种UML关系(ASSOCIATION/DIRECTED/DEPENDENCY/INCLUDE/EXTEND/
     GENERALIZATION/COMPOSITION/AGGREGATION/REALIZATION)
  B. 节点级QA(Actor/UseCase/State/Component/Interface/Package)
  C. 边标签QA(条件/后置条件/转换描述)
  D. 跨图一致性(同一实体在不同图中的UML关系)
  E. 组合变异(多关系复合不一致)
  F. 泛化层级QA(继承链)
  G. 泳道/分区一致性
  H. GJB规范合规QA
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
OUT_PATH = BASE / "data/gjb_438c/anchor_v3/uml_qa_full.json"

rng = random.Random(42)

# ============================================================================
# 全9种UML关系的QA模板
# 每种关系: 3正例(语义等价) + 3负例(不一致)
# ============================================================================

UML_TEMPLATES = {
    # 1. ASSOCIATION (关联: 实线无箭头)
    'ASSOCIATION': {
        'positive': [
            {'q': '图中「{src}」和「{dst}」之间是什么关系？',
             'a': '关联关系(ASSOCIATION)。两者通过实线直接连接，表示它们之间存在语义关联但无方向性依赖。{src}和{dst}可以独立存在。',
             'difficulty': 'easy'},
            {'q': '「{src}」与「{dst}」是否有关联？',
             'a': '是的，图中显示{src}和{dst}之间存在关联关系，用实线表示。这是一种结构性的关系，不表示依赖或包含。',
             'difficulty': 'easy'},
            {'q': '请描述「{src}」和「{dst}」在图中的连接方式及其含义。',
             'a': '{src}和{dst}通过无箭头的实线连接，这是UML中的关联关系(ASSOCIATION)。关联表示两个元素之间的结构关系，两端都没有导航箭头意味着关系是双向的。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '图中「{src}」和「{dst}」之间的关系方向是什么？',
             'a': '图中显示「{dst}」指向「{src}」，即{dst}依赖{src}。（实际是关联关系无方向，不存在指向）',
             'inject': 'direction_fabrication', 'difficulty': 'medium'},
            {'q': '「{src}」和「{dst}」之间是包含关系还是关联关系？',
             'a': '是包含关系(include)，{src}包含{dst}作为其必须执行的子用例。（实际是关联关系，非包含）',
             'inject': 'relationship_type_confusion', 'difficulty': 'hard'},
            {'q': '「{src}」是否依赖「{dst}」才能执行？',
             'a': '是的，{src}必须依赖{dst}的输出才能完成。（实际是关联关系，不存在必然依赖）',
             'inject': 'dependency_fabrication', 'difficulty': 'hard'},
        ],
    },
    # 2. DIRECTED (有向关联: 实线+箭头)
    'DIRECTED': {
        'positive': [
            {'q': '图中「{src}」到「{dst}」的箭头表示什么？',
             'a': '有向关联(DIRECTED ASSOCIATION)。实线箭头表示{src}到{dst}的导航方向，即从{src}可以访问{dst}。',
             'difficulty': 'easy'},
            {'q': '「{src}」能否访问「{dst}」？',
             'a': '可以，图中的箭头方向从{src}指向{dst}，表示可导航性。',
             'difficulty': 'easy'},
            {'q': '描述「{src}」与「{dst}」之间的导航关系。',
             'a': '图中使用实线箭头从{src}指向{dst}，这是有向关联。在UML中，箭头表示导航方向——从{src}端可以引用或访问{dst}端的元素。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '图中箭头是从「{dst}」指向「{src}」的吗？',
             'a': '是的，箭头从{dst}指向{src}。（实际方向相反：{src}→{dst}）',
             'inject': 'direction_reversal', 'difficulty': 'medium'},
            {'q': '「{dst}」可以访问「{src}」吗？',
             'a': '可以。（实际：箭头方向是{src}→{dst}，{dst}不能直接访问{src}）',
             'inject': 'navigation_error', 'difficulty': 'hard'},
        ],
    },
    # 3. DEPENDENCY (依赖: 虚线+开放箭头)
    'DEPENDENCY': {
        'positive': [
            {'q': '「{src}」和「{dst}」之间的虚线箭头表示什么？',
             'a': '依赖关系(DEPENDENCY)。虚线开放箭头表示{src}使用了{dst}提供的服务或信息，但不是结构性关系。修改{dst}可能影响{src}。',
             'difficulty': 'medium'},
            {'q': '如果「{dst}」发生变化，会影响「{src}」吗？',
             'a': '会。图中虚线箭头从{src}指向{dst}，表示依赖关系——{src}依赖{dst}，{dst}的变更会传递影响{src}。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '「{dst}」是否依赖「{src}」？',
             'a': '是的，虚线箭头从{dst}指向{src}。（实际：箭头从{src}指向{dst}，即{src}依赖{dst}）',
             'inject': 'direction_reversal', 'difficulty': 'medium'},
            {'q': '「{src}」和「{dst}」之间是依赖还是实现关系？',
             'a': '是实现关系(realization)。（实际：虚线开放箭头=依赖，虚线实心三角=实现）',
             'inject': 'uml_type_confusion', 'difficulty': 'hard'},
        ],
    },
    # 4. INCLUDE (包含: 虚线+«include»)
    'INCLUDE': {
        'positive': [
            {'q': '「{src}」是否包含「{dst}」？',
             'a': '是的，图中虚线标注«include»从{src}指向{dst}，表示{src}的执行必然包含{dst}的行为。{dst}是{src}的必要组成部分。',
             'difficulty': 'medium'},
            {'q': '描述「{src}」与「{dst}」之间的包含关系。',
             'a': '{src}通过«include»关系包含{dst}。在UML用例图中，include表示基础用例(src)的行为包含被包含用例(dst)的行为，被包含用例总是被执行。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '「{dst}」是否包含「{src}」？',
             'a': '是的，«include»关系从{dst}指向{src}。（实际：从{src}指向{dst}）',
             'inject': 'direction_reversal', 'difficulty': 'medium'},
            {'q': '「{src}」可以选择性地执行「{dst}」吗？',
             'a': '可以，«include»表示可选行为。（实际：include=必须执行，extend才是可选）',
             'inject': 'include_vs_extend', 'difficulty': 'hard'},
        ],
    },
    # 5. EXTEND (扩展: 虚线+«extend»)
    'EXTEND': {
        'positive': [
            {'q': '「{src}」在什么条件下会扩展「{dst}」？',
             'a': '图中«extend»关系表示{src}在满足扩展条件时可以扩展{dst}的行为。这是一种可选行为——只有当条件满足时才触发。',
             'difficulty': 'medium'},
            {'q': '「{src}」是「{dst}」的可选扩展吗？',
             'a': '是的。«extend»表示{src}是{dst}的可选扩展用例，在特定条件下才执行，{dst}本身不知道{src}的存在。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '「{dst}」是否是「{src}」的可选扩展？',
             'a': '是的。（实际：方向反了，{src}是{dst}的扩展）',
             'inject': 'direction_reversal', 'difficulty': 'medium'},
            {'q': '执行「{src}」时是否必须执行「{dst}」？',
             'a': '必须执行。（实际：extend是可选的，include才是必须）',
             'inject': 'extend_vs_include', 'difficulty': 'hard'},
        ],
    },
    # 6. GENERALIZATION (泛化: 实线+空心三角)
    'GENERALIZATION': {
        'positive': [
            {'q': '「{src}」和「{dst}」之间的空心三角箭头表示什么？',
             'a': '泛化关系(GENERALIZATION)。空心三角从{src}(子)指向{dst}(父)，表示{src}是{dst}的特殊化，继承了{dst}的全部行为和属性。',
             'difficulty': 'medium'},
            {'q': '「{src}」是「{dst}」的子类型吗？',
             'a': '是的，泛化箭头从{src}指向{dst}，{src}继承了{dst}的所有特征并可添加特有行为。',
             'difficulty': 'easy'},
        ],
        'negative': [
            {'q': '「{dst}」是「{src}」的子类型吗？',
             'a': '是的。（实际：方向反了，{src}是{dst}的子类型）',
             'inject': 'hierarchy_reversal', 'difficulty': 'hard'},
            {'q': '「{src}」是否实现了「{dst}」定义的接口？',
             'a': '是的，这是实现关系。（实际：空心三角=泛化，虚线实心三角=实现）',
             'inject': 'generalization_vs_realization', 'difficulty': 'hard'},
        ],
    },
    # 7. COMPOSITION (组合: 实线+实心菱形)
    'COMPOSITION': {
        'positive': [
            {'q': '「{src}」和「{dst}」之间实心菱形表示什么关系？',
             'a': '组合关系(COMPOSITION)。实心菱形在{src}端，表示{dst}是{src}的组成部分，两者生命周期一致——{dst}不能独立于{src}存在。',
             'difficulty': 'medium'},
            {'q': '如果删除「{src}」，「{dst}」还能存在吗？',
             'a': '不能。组合关系(实心菱形)表示强拥有——{dst}是{src}的固有部分，删除整体时部分也被删除。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '「{src}」和「{dst}」之间是聚合还是组合？',
             'a': '是聚合关系(aggregation)，空心菱形。（实际：实心菱形=组合）',
             'inject': 'composition_vs_aggregation', 'difficulty': 'hard'},
            {'q': '「{dst}」是否可以独立于「{src}」存在？',
             'a': '可以。（实际：组合关系下{dst}不能独立存在）',
             'inject': 'lifecycle_error', 'difficulty': 'hard'},
        ],
    },
    # 8. AGGREGATION (聚合: 实线+空心菱形)
    'AGGREGATION': {
        'positive': [
            {'q': '「{src}」和「{dst}」之间空心菱形表示什么？',
             'a': '聚合关系(AGGREGATION)。空心菱形在{src}端，表示{dst}是{src}的组成部分但可独立存在，整体和部分有独立的生命周期。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '删除「{src}」时「{dst}」也会被删除吗？',
             'a': '会。（实际：聚合关系下部分可独立存在）',
             'inject': 'lifecycle_error', 'difficulty': 'hard'},
        ],
    },
    # 9. REALIZATION (实现: 虚线+实心三角)
    'REALIZATION': {
        'positive': [
            {'q': '「{src}」如何实现「{dst}」？',
             'a': '图中虚线实心三角箭头从{src}指向{dst}，表示实现关系(REALIZATION)。{src}实现了{dst}定义的规范或接口。',
             'difficulty': 'medium'},
            {'q': '「{src}」是否遵循「{dst}」定义的规范？',
             'a': '是的。虚线实心三角表示{src}实现(realize)了{dst}，在UML中常用于组件实现接口的场景。',
             'difficulty': 'medium'},
        ],
        'negative': [
            {'q': '「{dst}」是否实现了「{src}」？',
             'a': '是的。（实际：方向反了，{src}实现{dst}）',
             'inject': 'direction_reversal', 'difficulty': 'medium'},
            {'q': '「{src}」和「{dst}」之间是继承关系吗？',
             'a': '是继承(generalization)关系。（实际：虚线实心三角=实现，实线空心三角=继承）',
             'inject': 'realization_vs_generalization', 'difficulty': 'hard'},
        ],
    },
}

# ============================================================================
# 节点级QA模板
# ============================================================================

NODE_TEMPLATES = {
    'actor': {
        'positive': [
            {'q': '「{name}」在图中扮演什么角色？',
             'a': '「{name}」是参与者(Actor)，在系统边界之外与系统交互。图中用小人图标表示。',
             'difficulty': 'easy'},
        ],
        'negative': [
            {'q': '「{name}」是系统内部的组件吗？',
             'a': '是的，{name}是系统内部的功能模块。（实际：{name}是外部参与者Actor）',
             'inject': 'actor_vs_component', 'difficulty': 'medium'},
        ],
    },
    'usecase': {
        'positive': [
            {'q': '「{name}」代表什么功能？',
             'a': '「{name}」是用例(Use Case)，表示系统对外提供的一个完整功能单元。图中用椭圆表示。',
             'difficulty': 'easy'},
        ],
        'negative': [
            {'q': '「{name}」是系统的一个状态吗？',
             'a': '是的。（实际：椭圆=用例，圆角矩形=状态）',
             'inject': 'usecase_vs_state', 'difficulty': 'medium'},
        ],
    },
    'state': {
        'positive': [
            {'q': '「{name}」表示什么？',
             'a': '「{name}」是状态(State)，表示对象在生命周期中的某个阶段。图中用圆角矩形表示。',
             'difficulty': 'easy'},
        ],
    },
    'component': {
        'positive': [
            {'q': '「{name}」是什么类型的元素？',
             'a': '「{name}」是组件(Component)，表示系统的模块化单元。图中用组件图标表示。',
             'difficulty': 'easy'},
        ],
    },
    'interface': {
        'positive': [
            {'q': '「{name}」在图中如何表示？',
             'a': '「{name}」是接口(Interface)，定义了组件之间交互的契约。图中用棒棒糖符号(lollipop)或矩形表示。',
             'difficulty': 'medium'},
        ],
    },
    'boundary': {
        'positive': [
            {'q': '「{name}」框表示什么？',
             'a': '「{name}」是系统边界(Boundary)，框定了系统的范围。边界内的用例属于系统功能，边界外的是外部参与者。',
             'difficulty': 'medium'},
        ],
    },
}

# ============================================================================
# 边标签QA模板(条件/后置条件)
# ============================================================================

LABEL_TEMPLATES = {
    'condition': {
        'positive': [
            {'q': '从「{src}」到「{dst}」需要满足什么条件？',
             'a': '需要满足「{label}」条件。图中在转换线上标注了条件「{label}」，只有此条件成立时才发生转换。',
             'difficulty': 'easy'},
        ],
        'negative': [
            {'q': '满足「{wrong_label}」条件时是否可以执行「{dst}」？',
             'a': '可以。（实际：需要的条件是「{label}」，不是「{wrong_label}」）',
             'inject': 'condition_swap', 'difficulty': 'medium'},
        ],
    },
    'postcondition': {
        'positive': [
            {'q': '执行「{src}」后会产生什么效果？',
             'a': '「{label}」。图中在转换线标注了执行后的效果描述。',
             'difficulty': 'easy'},
        ],
    },
}

# ============================================================================
# 跨图一致性模板
# ============================================================================

CROSS_DIAGRAM_TEMPLATES = [
    {
        'q': '「{name}」在图A和图B中的UML关系是否一致？图A显示{rel_a}，图B显示{rel_b}。',
        'a': '不一致。{name}在两个图中表达了不同的关系语义（{rel_a} vs {rel_b}），说明文档可能存在演化遗漏。',
        'inject': 'cross_diagram_inconsistency',
        'difficulty': 'hard',
    },
    {
        'q': '同一功能「{name}」在不同图中被建模为不同类型的关系，这是否正确？',
        'a': '不正确。{name}在图A中是{rel_a}，在图B中变成了{rel_b}。同一实体在不同视图中的关系语义应保持一致或通过明确的映射说明。',
        'inject': 'cross_diagram_type_mismatch',
        'difficulty': 'hard',
    },
]

# ============================================================================
# 组合变异模板(多关系复合)
# ============================================================================

COMPOUND_TEMPLATES = [
    {
        'q': '分析「{src}」的完整依赖关系：它同时{dep1}{dep2}。这两个依赖是否一致？',
        'a': '存在矛盾。{src}同时依赖{dst1}和{dst2}，但图中{dst1}的箭头方向与{dst2}相反，构成循环依赖({src}→{dst1}→{dst2}→{src})，这在设计中应避免。',
        'inject': 'circular_dependency',
        'difficulty': 'hard',
    },
    {
        'q': '「{src}」既组合了「{dst1}」又聚合了「{dst2}」，这两个关系的语义是否正确？',
        'a': '可能存在设计不一致。{dst1}使用组合(实心菱形)表示生命周期绑定，{dst2}使用聚合(空心菱形)表示可独立存在。如果{dst1}和{dst2}是同级概念，这种不一致需要验证是否有意为之。',
        'inject': 'composition_aggregation_mix',
        'difficulty': 'hard',
    },
]

# ============================================================================
# 生成函数
# ============================================================================

def generate_full_qa(anchors):
    """从anchor_v3生成全维度UML QA对

    v2标签噪声修复(2026-09-09, 对应17_uml_detection_eval.md §4.4仲裁发现):
      负例前置校验: 捏造声明必须在配对节点的全部平行边上为假, 否则跳过该负例
        - direction_fabrication: 仅当全部平行边真无箭头(修复67条噪声)
        - direction_reversal/navigation_error: 不得有平行边可导航反向(修复10条双向噪声)
        - dependency_fabrication: 配对间不得存在依赖族边
        - relationship_type_confusion: 配对平行边类型必须同质
      正例箭头声明校验: ASSOCIATION边带箭头时跳过含"无箭头"表述的正例模板
    """
    NAV_END = {'filled_triangle', 'filled_circle_s', 'closed', 'open_60', 'open',
               'filled_diamond_s', 'filled_square', 'block'}
    NAV_BEGIN = {'filled_square', 'filled_circle_s', 'filled_triangle', 'open'}

    def _has_arrow(e):
        return (e.get('end_arrow') not in (None, '', 'none', 'unknown') and e.get('end_arrow') in NAV_END) or \
               (e.get('begin_arrow') not in (None, '', 'none', 'unknown') and e.get('begin_arrow') in NAV_BEGIN)

    def _dir(e):
        fe = e.get('end_arrow') in NAV_END
        fb = e.get('begin_arrow') in NAV_BEGIN
        if fe and fb:
            return 'both'
        if fe:
            return 'fwd'
        if fb:
            return 'bwd'
        return 'none'

    def neg_ok(inject, parallel, e=None):
        if inject == 'direction_fabrication':
            return all(not _has_arrow(pe) for pe in parallel)
        if inject in ('direction_reversal', 'navigation_error'):
            # 反向声明(dst→src)不得被任何平行边支持:
            # 同朝向边需begin箭头(bwd), 反朝向边(src/dst互换)需end箭头(fwd)
            for pe in parallel:
                d = _dir(pe)
                if e is not None and pe['src'] == e['dst'] and pe['dst'] == e['src']:
                    if d in ('fwd', 'both'):
                        return False
                elif d in ('bwd', 'both'):
                    return False
            return True
        if inject == 'dependency_fabrication':
            return not any(pe.get('uml_type') in ('DEPENDENCY', 'INCLUDE', 'EXTEND')
                           for pe in parallel)
        if inject == 'relationship_type_confusion':
            return len({pe.get('uml_type') for pe in parallel}) == 1
        return True

    qa_pairs = []

    for doc_name, doc_data in anchors.items():
        structures = doc_data.get('structures', [])
        doc_short = doc_name[:8]

        for st_idx, st in enumerate(structures):
            edges = st.get('edges', [])
            nodes = {n['id']: n for n in st.get('nodes', [])}
            embed = st.get('embed_index', '')
            # 平行边索引: 无序节点对 → 该结构内全部边(负例前置校验用)
            parallel = defaultdict(list)
            for e in edges:
                key = (min(e['src'], e['dst']), max(e['src'], e['dst']))
                parallel[key].append(e)

            # --- A: UML关系QA ---
            for e in edges:
                uml_type = e.get('uml_type', 'ASSOCIATION')
                src_text = e.get('src_text', '')[:15]
                dst_text = e.get('dst_text', '')[:15]
                if not src_text or not dst_text:
                    continue

                templates = UML_TEMPLATES.get(uml_type, {})
                par = parallel[(min(e['src'], e['dst']), max(e['src'], e['dst']))]

                # 正例(箭头声明校验: 带箭头的边不得生成"无箭头"表述的正例)
                arrow_claim = '无箭头' in ''.join(t['a'] for t in templates.get('positive', []))
                for tmpl in templates.get('positive', []):
                    if arrow_claim and _has_arrow(e) and '无箭头' in tmpl['a']:
                        continue  # 边实际带箭头, "无箭头"表述为假 → 跳过防标签噪声
                    qa_pairs.append({
                        'id': f'uml_{doc_short}_{st_idx}_{e["src"]}_{e["dst"]}_pos',
                        'pair_id': f'{doc_short}_{st_idx}',
                        'doc': doc_name,
                        'uml_type': uml_type,
                        'label': 'consistent',
                        'question': tmpl['q'].format(src=src_text, dst=dst_text),
                        'answer': tmpl['a'].format(src=src_text, dst=dst_text),
                        'difficulty': tmpl['difficulty'],
                        'evidence': {'embed': embed, 'uml_type': uml_type,
                                    'src': src_text, 'dst': dst_text,
                                    'line_pattern': e.get('line_pattern', 'solid'),
                                    'end_arrow': e.get('end_arrow', 'none')},
                        'source': 'uml_positive',
                    })

                # 负例(前置校验: 捏造声明必须在全部平行边上为假)
                for tmpl in templates.get('negative', []):
                    if not neg_ok(tmpl.get('inject', ''), par, e):
                        continue  # 声明在平行边上为真 → 会产生标签噪声, 跳过
                    qa_pairs.append({
                        'id': f'uml_{doc_short}_{st_idx}_{e["src"]}_{e["dst"]}_neg',
                        'pair_id': f'{doc_short}_{st_idx}',
                        'doc': doc_name,
                        'uml_type': uml_type,
                        'label': 'inconsistent',
                        'inject_type': tmpl.get('inject', 'unknown'),
                        'question': tmpl['q'].format(src=src_text, dst=dst_text),
                        'answer': tmpl['a'].format(src=src_text, dst=dst_text),
                        'difficulty': tmpl['difficulty'],
                        'evidence': {'embed': embed, 'uml_type': uml_type,
                                    'src': src_text, 'dst': dst_text,
                                    'line_pattern': e.get('line_pattern', 'solid'),
                                    'end_arrow': e.get('end_arrow', 'none')},
                        'source': 'uml_negative',
                    })

                # --- C: 边标签QA ---
                label = e.get('label', '').strip()
                if label and len(label) >= 2:
                    for tmpl in LABEL_TEMPLATES.get('condition', {}).get('positive', []):
                        qa_pairs.append({
                            'id': f'lbl_{doc_short}_{st_idx}_{e["src"]}_{e["dst"]}_pos',
                            'doc': doc_name, 'uml_type': uml_type,
                            'label': 'consistent',
                            'question': tmpl['q'].format(src=src_text, dst=dst_text,
                                                         label=label),
                            'answer': tmpl['a'].format(src=src_text, dst=dst_text,
                                                        label=label),
                            'difficulty': tmpl['difficulty'],
                            'evidence': {'embed': embed, 'label': label},
                            'source': 'label_positive',
                        })

                    # 负例: 条件替换(对立条件不得存在于平行边标注, 防噪声)
                    for tmpl in LABEL_TEMPLATES.get('condition', {}).get('negative', []):
                        # 用对立条件替换
                        wrong = '正常' if '失败' in label or '异常' in label else '异常'
                        if any(wrong in (pe.get('label') or '') for pe in par):
                            continue
                        qa_pairs.append({
                            'id': f'lbl_{doc_short}_{st_idx}_{e["src"]}_{e["dst"]}_neg',
                            'doc': doc_name, 'uml_type': uml_type,
                            'label': 'inconsistent',
                            'inject_type': 'condition_swap',
                            'question': tmpl['q'].format(src=src_text, dst=dst_text,
                                                         label=label, wrong_label=wrong),
                            'answer': tmpl['a'].format(src=src_text, dst=dst_text,
                                                        label=label, wrong_label=wrong),
                            'difficulty': tmpl['difficulty'],
                            'evidence': {'embed': embed, 'label': label},
                            'source': 'label_negative',
                        })

            # --- B: 节点级QA ---
            for n in nodes.values():
                ntype = n.get('type', 'other')
                ntext = n.get('text', '').strip()[:15]
                if not ntext:
                    continue

                node_tmpls = NODE_TEMPLATES.get(ntype, {})
                for tmpl in node_tmpls.get('positive', []):
                    qa_pairs.append({
                        'id': f'node_{doc_short}_{st_idx}_{n["id"]}_pos',
                        'doc': doc_name, 'node_type': ntype,
                        'label': 'consistent',
                        'question': tmpl['q'].format(name=ntext),
                        'answer': tmpl['a'].format(name=ntext),
                        'difficulty': tmpl['difficulty'],
                        'evidence': {'embed': embed, 'node_type': ntype},
                        'source': 'node_positive',
                    })

                for tmpl in node_tmpls.get('negative', []):
                    qa_pairs.append({
                        'id': f'node_{doc_short}_{st_idx}_{n["id"]}_neg',
                        'doc': doc_name, 'node_type': ntype,
                        'label': 'inconsistent',
                        'inject_type': tmpl.get('inject', 'node_confusion'),
                        'question': tmpl['q'].format(name=ntext),
                        'answer': tmpl['a'].format(name=ntext),
                        'difficulty': tmpl['difficulty'],
                        'evidence': {'embed': embed, 'node_type': ntype},
                        'source': 'node_negative',
                    })

            # --- E: 组合变异QA(每结构最多2条) ---
            if len(edges) >= 3 and st_idx % 10 == 0:
                edge_list = list(edges)
                e1, e2 = edge_list[0], edge_list[1]
                if e1.get('src_text') and e2.get('src_text'):
                    for tmpl in COMPOUND_TEMPLATES[:1]:
                        qa_pairs.append({
                            'id': f'cmp_{doc_short}_{st_idx}_neg',
                            'doc': doc_name,
                            'label': 'inconsistent',
                            'inject_type': tmpl['inject'],
                            'question': tmpl['q'].format(
                                src=e1.get('src_text', '')[:10],
                                dep1=f"依赖{e1.get('dst_text', '')[:10]}",
                                dep2=f"且依赖{e2.get('dst_text', '')[:10]}",
                                dst1=e1.get('dst_text', '')[:10],
                                dst2=e2.get('dst_text', '')[:10]),
                            'answer': tmpl['a'].format(
                                src=e1.get('src_text', '')[:10],
                                dst1=e1.get('dst_text', '')[:10],
                                dst2=e2.get('dst_text', '')[:10]),
                            'difficulty': 'hard',
                            'evidence': {'embed': embed},
                            'source': 'compound_negative',
                        })

    return qa_pairs


# ============================================================================
# 主函数
# ============================================================================

def main():
    print("=" * 70)
    print("全UML关系QA模板扩展版")
    print("=" * 70)

    anchors = json.load(open(V3_PATH, encoding="utf-8"))
    print(f"加载锚点: {len(anchors)}文档")

    qa_pairs = generate_full_qa(anchors)

    # 统计
    pos = sum(1 for q in qa_pairs if q['label'] == 'consistent')
    neg = sum(1 for q in qa_pairs if q['label'] == 'inconsistent')

    by_source = defaultdict(int)
    by_type = defaultdict(int)
    by_diff = defaultdict(int)
    for q in qa_pairs:
        by_source[q.get('source', '?')] += 1
        by_type[q.get('uml_type', q.get('node_type', '?'))] += 1
        by_diff[q.get('difficulty', '?')] += 1

    inject_types = defaultdict(int)
    for q in qa_pairs:
        if q.get('inject_type'):
            inject_types[q['inject_type']] += 1

    # 保存
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    json.dump(qa_pairs, open(OUT_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"\n生成QA: {len(qa_pairs)}条 (正例{pos} / 负例{neg})")
    print("\n来源分布:")
    for k, v in sorted(by_source.items()):
        print(f"  {k:25s}: {v}")
    print("\nUML关系类型分布:")
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {k:25s}: {v}")
    print("\n难度分布:")
    for k, v in sorted(by_diff.items()):
        print(f"  {k:10s}: {v}")
    print(f"\n注入类型分布({len(inject_types)}种):")
    for k, v in sorted(inject_types.items(), key=lambda x: -x[1]):
        print(f"  {k:35s}: {v}")

    print(f"\n输出: {OUT_PATH}")
    return qa_pairs


if __name__ == "__main__":
    main()
