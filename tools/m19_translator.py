#!/usr/bin/env python3
"""
M19: 多目标翻译器
==================
锚点结构 → 多种目标表示(按图类型路由):

  usecase_diagram → PlantUML usecase (原生参与者/用例/关联——修复Mermaid不适配)
  state_diagram   → Mermaid stateDiagram-v2 (已验证88分)
  flowchart/其他  → Mermaid flowchart TD (已验证85分)
  全部类型        → Graphviz DOT (精确通用)
  全部类型        → 自然语言结构化描述 (LLM消费)

输出: data/gjb_438c/anchor_v2/translations.json
用法: python3 tools/m19_translator.py
"""
import json
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
OUT = BASE / "data/gjb_438c/anchor_v2/translations.json"


def classify_diagram(s: dict) -> str:
    types = Counter(n['type'] for n in s['nodes'] if n['text'])
    n_text = sum(types.values())
    if n_text == 0:
        return 'empty'
    if types.get('usecase', 0) / n_text >= 0.4:
        return 'usecase_diagram'
    if types.get('state', 0) / n_text >= 0.4:
        return 'state_diagram'
    if types.get('process', 0) / n_text >= 0.5:
        return 'flowchart'
    if types.get('actor', 0) and not types.get('usecase', 0):
        return 'architecture'
    if len(s['edges']) < n_text * 0.3:
        return 'hierarchy_decomposition'
    return 'mixed'


def sanitize(text: str, maxlen: int = 200) -> str:
    t = (text or '').replace('\n', ' ').replace('"', "'")
    t = t.replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')')
    return t[:maxlen]


# ═══════════════════════════════════════════════════════════════
# 目标1: PlantUML用例图
# ═══════════════════════════════════════════════════════════════

def to_plantuml_usecase(s: dict) -> str:
    """用例图 → PlantUML (actor/usecase/rectangle边界/关联)"""
    lines = ['@startuml', 'left to right direction', 'skinparam packageStyle rectangle']
    actors = [n for n in s['nodes'] if n['type'] == 'actor' and n['text']]
    usecases = [n for n in s['nodes'] if n['type'] in ('usecase',) and n['text']]
    others = [n for n in s['nodes']
              if n['type'] not in ('actor', 'usecase', 'start', 'end') and n['text']]
    boundaries = [n for n in s['nodes'] if n['type'] == 'boundary' and n['text']]

    # 参与者
    for a in actors:
        lines.append(f'actor "{sanitize(a["text"], 40)}" as A{a["id"]}')
    # 边界容器
    if boundaries:
        b = boundaries[0]
        lines.append(f'rectangle "{sanitize(b["text"], 40)}" {{')
        indent = '  '
    else:
        lines.append('rectangle {')
        indent = '  '
    # 用例
    for u in usecases:
        lines.append(f'{indent}usecase ({sanitize(u["text"], 60)}) as U{u["id"]}')
    # 其他节点作为用例兜底
    for o in others:
        lines.append(f'{indent}usecase ({sanitize(o["text"], 60)}) as U{o["id"]}')
    lines.append('}')
    # 关联边
    nodes_map = {n['id']: n for n in s['nodes']}
    for e in s['edges']:
        sn, dn = nodes_map.get(e['src']), nodes_map.get(e['dst'])
        if not sn or not dn or not (sn['text'] or dn['text']):
            continue
        # actor↔usecase: A-->U; usecase↔usecase: U-->U
        def ref(n):
            return f'A{n["id"]}' if n['type'] == 'actor' else f'U{n["id"]}'
        lbl = sanitize(e.get('label', ''), 20)
        arrow = f' --> {lbl}' if lbl else ' --> '
        # 去重
        key = (ref(sn), ref(dn))
        lines.append(f'{ref(sn)}{arrow}{ref(dn)}')
    # 去重相邻重复行
    seen, dedup = set(), []
    for l in lines:
        norm = re.sub(r'\s+', ' ', l).strip()
        if ' --> ' in l:
            if norm in seen:
                continue
            seen.add(norm)
        dedup.append(l)
    return '\n'.join(dedup + ['@enduml'])


# ═══════════════════════════════════════════════════════════════
# 目标2: Mermaid flowchart / state (复用M13逻辑)
# ═══════════════════════════════════════════════════════════════

SHAPE = {
    'start': ('([', '])'), 'end': ('([', '])'),
    'process': ('[', ']'), 'decision': ('{', '}'),
    'state': ('[', ']'), 'usecase': ('([', '])'),
    'actor': ('[/', '/]'), 'gateway': ('{', '}'),
    'fork': ('{', '}'), 'boundary': ('[', ']'),
    'other': ('[', ']'), 'offpage': ('[[', ']]'),
}
TOPO_TYPES = {'start': '开始', 'end': '结束', 'fork': '分叉', 'gateway': '网关', 'decision': '判定'}


def to_mermaid_flowchart(s: dict) -> str:
    lines = ['flowchart TD']
    nodes = {n['id']: n for n in s['nodes']}
    emitted = set()

    def emit(n):
        if n['id'] in emitted:
            return
        if not n['text'] and n['type'] not in TOPO_TYPES:
            return
        label = sanitize(n['text']) or TOPO_TYPES.get(n['type'], n['type'])
        l, r = SHAPE.get(n['type'], ('[', ']'))
        lines.append(f'    N{n["id"]}{l}"{label}"{r}')
        emitted.add(n['id'])

    for n in s['nodes']:
        emit(n)
    for e in s['edges']:
        sn, dn = nodes.get(e['src']), nodes.get(e['dst'])
        if not sn or not dn:
            continue
        if not (sn['text'] or sn['type'] in TOPO_TYPES):
            continue
        if not (dn['text'] or dn['type'] in TOPO_TYPES):
            continue
        emit(sn)
        emit(dn)
        if e.get('label'):
            lines.append(f'    N{e["src"]} -->|"{sanitize(e["label"], 20)}"| N{e["dst"]}')
        else:
            lines.append(f'    N{e["src"]} --> N{e["dst"]}')
    return '\n'.join(lines)


def to_mermaid_state(s: dict) -> str:
    lines = ['stateDiagram-v2']
    nodes = {n['id']: n for n in s['nodes']}
    refs = set()
    for e in s['edges']:
        refs.add(e['src'])
        refs.add(e['dst'])
    emitted = set()
    for n in s['nodes']:
        if not n['text'] and n['id'] not in refs:
            continue
        if n['type'] == 'start':
            if n['text']:
                lines.append(f'    N{n["id"]} : {sanitize(n["text"], 40)}')
            lines.append(f'    [*] --> N{n["id"]}')
        elif n['type'] == 'end':
            if n['text']:
                lines.append(f'    N{n["id"]} : {sanitize(n["text"], 40)}')
            lines.append(f'    N{n["id"]} --> [*]')
        else:
            label = sanitize(n['text'], 60) or n['type']
            lines.append(f'    N{n["id"]} : {label}')
        emitted.add(n['id'])
    for e in s['edges']:
        if e['src'] not in emitted or e['dst'] not in emitted:
            continue
        if e.get('label'):
            lines.append(f'    N{e["src"]} --> {sanitize(e["label"], 16)}: N{e["dst"]}')
        else:
            lines.append(f'    N{e["src"]} --> N{e["dst"]}')
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════
# 目标3: Graphviz DOT
# ═══════════════════════════════════════════════════════════════

DOT_SHAPE = {
    'process': 'box', 'decision': 'diamond', 'start': 'circle',
    'end': 'doublecircle', 'state': 'box', 'usecase': 'ellipse',
    'actor': 'box,style=filled,fillcolor=lightyellow',
    'gateway': 'diamond', 'fork': 'box,style=bold',
    'boundary': 'box,style=dashed', 'other': 'box',
}


def to_dot(s: dict) -> str:
    lines = ['digraph G {', '  rankdir=TB;']
    for n in s['nodes']:
        if not n['text']:
            continue
        shape = DOT_SHAPE.get(n['type'], 'box')
        label = sanitize(n['text'], 60).replace('\\', '\\\\')
        lines.append(f'  N{n["id"]} [label="{label}", shape={shape}];')
    nodes_map = {n['id']: n for n in s['nodes']}
    for e in s['edges']:
        sn, dn = nodes_map.get(e['src']), nodes_map.get(e['dst'])
        if not sn or not dn or not (sn['text'] or dn['text']):
            continue
        lbl = sanitize(e.get('label', ''), 20)
        if lbl:
            lines.append(f'  N{e["src"]} -> N{e["dst"]} [label="{lbl}"];')
        else:
            lines.append(f'  N{e["src"]} -> N{e["dst"]};')
    lines.append('}')
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════
# 目标4: 自然语言结构化描述
# ═══════════════════════════════════════════════════════════════

TYPE_CN = {'process': '过程', 'decision': '判定', 'start': '开始', 'end': '结束',
           'state': '状态', 'usecase': '用例', 'actor': '参与者', 'gateway': '网关',
           'fork': '分叉', 'boundary': '系统边界', 'other': '节点', 'offpage': '页引用'}


def to_natural_language(s: dict, dtype: str) -> str:
    """锚点 → 中文结构化描述(LLM消费友好)"""
    text_nodes = [n for n in s['nodes'] if n['text']]
    by_type = {}
    for n in text_nodes:
        by_type.setdefault(TYPE_CN.get(n['type'], '节点'), []).append(n['text'][:30])
    nodes_map = {n['id']: n for n in s['nodes']}

    parts = []
    type_name = {'usecase_diagram': '用例图', 'state_diagram': '状态图',
                 'flowchart': '流程图', 'architecture': '架构图',
                 'hierarchy_decomposition': '功能分解图', 'mixed': '混合图'}.get(dtype, '图')
    parts.append(f"这是一张{type_name}。")
    for t, texts in by_type.items():
        parts.append(f"{t}共{len(texts)}个: " + '、'.join(texts))
    # 边描述(有文本端点的)
    edges_desc = []
    for e in s['edges']:
        sn, dn = nodes_map.get(e['src']), nodes_map.get(e['dst'])
        if not sn or not dn:
            continue
        st = sn['text'][:15] if sn['text'] else TYPE_CN.get(sn['type'], '?')
        dt = dn['text'][:15] if dn['text'] else TYPE_CN.get(dn['type'], '?')
        lbl = f"(条件:{e['label'][:10]})" if e.get('label') else ''
        edges_desc.append(f"{st}→{dt}{lbl}")
    if edges_desc:
        parts.append(f"连接关系共{len(edges_desc)}条: " + '; '.join(edges_desc[:20]))
    return '\n'.join(parts)


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def translate(s: dict) -> dict:
    dtype = classify_diagram(s)
    if dtype == 'usecase_diagram':
        primary, primary_lang = to_plantuml_usecase(s), 'plantuml'
    elif dtype == 'state_diagram':
        primary, primary_lang = to_mermaid_state(s), 'mermaid-state'
    else:
        primary, primary_lang = to_mermaid_flowchart(s), 'mermaid-flowchart'
    return {
        'diagram_type': dtype,
        'primary': {'lang': primary_lang, 'code': primary},
        'dot': to_dot(s),
        'nl': to_natural_language(s, dtype),
    }


def main():
    anchors = json.loads(ANCHOR_V2.read_text())
    translations = {}
    type_dist = Counter()
    for doc, d in anchors.items():
        for s in d['structures']:
            key = f"{doc[:8]}:{s['embed_index']}"
            tr = translate(s)
            tr['doc'] = doc
            tr['embed'] = s['embed_index']
            translations[key] = tr
            type_dist[tr['diagram_type']] += 1
    OUT.write_text(json.dumps(translations, ensure_ascii=False, indent=1))
    print(f"M19多目标翻译: {len(translations)}图 → {OUT}")
    print(f"类型路由: {dict(type_dist)}")

    # 展示用例图的PlantUML样例(2_083之前28分的那个)
    sample_key = None
    for k, tr in translations.items():
        if tr['diagram_type'] == 'usecase_diagram' and '2_083' in str(tr.get('embed', '')):
            sample_key = k
            break
    if not sample_key:
        for k, tr in translations.items():
            if tr['diagram_type'] == 'usecase_diagram':
                sample_key = k
                break
    if sample_key:
        tr = translations[sample_key]
        print(f"\n─── PlantUML用例图样例({sample_key}) ───")
        print(tr['primary']['code'][:600])
        print(f"\n─── 自然语言样例 ───")
        print(tr['nl'][:400])


if __name__ == '__main__':
    main()
