#!/usr/bin/env python3
"""
M16: 多场景κ_T编译器 + Tier 1比较
====================================
为sc1/sc3/sc4/sc5/sc7开发场景特定比较(sc2已完整):

  sc1 能力表(用例图):   能力名称↔用例节点 + 能力ID匹配
  sc4 能力表(流程图):   能力名称↔流程节点
  sc3 接口表(接口图):   接口名↔图接口标签 + 收发方↔组件节点
  sc5 子功能表:         子功能名↔图节点
  sc7 用例描述表:       复用sc2的compile_usecase_table

锚点: census重对齐后的new_embed(高可信) + pair的visio_anchor(低可信回退)

输出: data/gjb_438c/anchor_v2/scene_tier1.json
用法: python3 tools/m16_scene_tier1.py
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import text_match_score, embed_batch, cosine, MATCH_TH, EMB_TH, save_emb_cache

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
CENSUS = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
OUT = BASE / "data/gjb_438c/anchor_v2/scene_tier1.json"


# ═══════════════════════════════════════════════════════════════
# κ_T编译器(行式表族)
# ═══════════════════════════════════════════════════════════════

def read_rows(csv_path: Path) -> list[list[str]]:
    with open(csv_path, encoding='utf-8') as f:
        return [[c.strip() for c in row] for row in csv.reader(f)]


ID_PAT = re.compile(r'^[A-Z][A-Z0-9-]{5,}$')


def split_name_id(s: str) -> tuple[str, str]:
    """'名称/标识' → ('名称','标识'); 标识须像ID(大写字母数字连字符)"""
    if '/' in s:
        name, _, tid = s.partition('/')
        name, tid = name.strip(), tid.strip()
        if tid and ID_PAT.match(tid):
            return name, tid
        if tid and len(tid) > len(name) and tid.replace('-', '').isalnum():
            return name, tid
    return s.strip(), ''


def compile_capability_table(csv_path: Path) -> dict:
    """能力表(sc1/sc4): 序号|Use case名称|标识|描述|...
    容错: 序号列可为空(按名称列判行); name/ID可能合并"""
    rows = read_rows(csv_path)
    caps = []
    seq = 0
    for r in rows[1:]:
        if not r:
            continue
        name_raw = r[1].strip() if len(r) > 1 else ''
        if not name_raw or '名称' in name_raw[:6] and '标识' in ''.join(r[:3]):
            continue  # 空行或表头
        seq += 1
        name, split_id = split_name_id(name_raw)
        tid = (r[2].strip() if len(r) > 2 else '') or split_id
        caps.append({
            'seq': seq, 'name': name, 'id': tid,
            'desc': r[3].strip() if len(r) > 3 else '',
        })
    return {'type': 'capability', 'caps': caps,
            'nodes': [{'id': f'cap{c["seq"]}', 'text': c['name'], 'type': 'capability'}
                      for c in caps if c['name']]}


def compile_interface_table(csv_path: Path) -> dict:
    """接口表(sc3): 表头驱动编译, 兼容多种列序变体
    已知格式A: 序号|接口需求名称|标识|接口类型|发送方|接收方|接口内容|优先级
    已知格式B: 序号|接口名称/标识|接口描述|发送方|接收方|接口类型|优先级|备注
    """
    rows = read_rows(csv_path)
    if not rows:
        return {'type': 'interface', 'interfaces': [], 'components': [], 'nodes': []}
    header = [h.replace(' ', '') for h in rows[0]]

    def find_col(*keys):
        for i, h in enumerate(header):
            if any(k in h for k in keys):
                return i
        return None

    name_col = find_col('名称')
    desc_col = find_col('描述', '内容')
    sender_col = find_col('发送方')
    receiver_col = find_col('接收方')
    itype_col = find_col('类型')
    id_col = find_col('标识')
    # 名称列若是"名称/标识"合并列, id_col指向同列
    if name_col is not None and '/' in header[name_col]:
        id_col = name_col

    def cell(r, col):
        if col is None or col >= len(r):
            return ''
        return r[col].strip()

    interfaces = []
    cur = None
    seq = 0
    for r in rows[1:]:
        if not r or not any(c.strip() for c in r):
            continue
        name_raw = cell(r, name_col)
        if name_raw and '名称' not in name_raw[:4]:
            seq += 1
            name, split_id = split_name_id(name_raw)
            tid = cell(r, id_col) if id_col != name_col else split_id
            cur = {
                'seq': seq, 'name': name, 'id': tid,
                'itype': cell(r, itype_col),
                'interactions': [],
            }
            interfaces.append(cur)
            sender, receiver = cell(r, sender_col), cell(r, receiver_col)
            if sender or receiver:
                cur['interactions'].append({
                    'sender': sender, 'receiver': receiver,
                    'content': cell(r, desc_col)})
        elif cur is not None:
            # 续行: 名称空但有收发方(列位与主行一致)
            sender, receiver = cell(r, sender_col), cell(r, receiver_col)
            if sender or receiver:
                cur['interactions'].append({
                    'sender': sender, 'receiver': receiver,
                    'content': cell(r, desc_col)})
    GENERIC = {'本系统', '本分系统', '系统', '用户', '外部系统', '高', '中', '低', '—', '-'}
    nodes, seen_comp = [], set()
    for itf in interfaces:
        if itf['name']:
            nodes.append({'id': f'itf{itf["seq"]}', 'text': itf['name'], 'type': 'interface'})
    for itf in interfaces:
        for ia in itf['interactions']:
            for role in ('sender', 'receiver'):
                comp = ia[role]
                if comp and comp not in seen_comp and comp not in GENERIC:
                    seen_comp.add(comp)
                    nodes.append({'id': f'comp{len(nodes)}', 'text': comp, 'type': 'component'})
    return {'type': 'interface', 'interfaces': interfaces, 'components': sorted(seen_comp),
            'nodes': nodes}



def compile_subfunction_table(csv_path: Path) -> dict:
    """子功能表(sc5): 序号|子功能名称/标识|描述|优先级"""
    rows = read_rows(csv_path)
    subs = []
    seq = 0
    for r in rows[1:]:
        if not r:
            continue
        name_raw = r[1].strip() if len(r) > 1 else r[0].strip()
        if not name_raw or '名称' in name_raw[:6]:
            continue
        seq += 1
        name, tid = split_name_id(name_raw)
        subs.append({
            'seq': seq, 'name': name, 'id': tid,
            'desc': r[2].strip() if len(r) > 2 else '',
        })
    return {'type': 'subfunction', 'subs': subs,
            'nodes': [{'id': f'sub{s["seq"]}', 'text': s['name'], 'type': 'subfunction'}
                      for s in subs if s['name']]}


# ═══════════════════════════════════════════════════════════════
# 场景特定比较
# ═══════════════════════════════════════════════════════════════

def match_elements(table_nodes: list[dict], diag_nodes: list[dict]) -> dict:
    """通用元素匹配(词法+embedding), 返回matched/missing/extra
    注意: embedding回退排除boundary类节点(能力项不应匹配到系统边界名)"""
    pairs = []
    for tn in table_nodes:
        for dn in diag_nodes:
            sc = text_match_score(tn['text'], dn['text'])
            if sc >= MATCH_TH:
                pairs.append((sc, tn['id'], dn['id']))
    # embedding补充(排除boundary——语义角色不匹配)
    emb_targets = [dn for dn in diag_nodes if dn.get('type') != 'boundary']
    low_t = [tn for tn in table_nodes
             if not any(p[1] == tn['id'] for p in pairs)]
    if low_t and emb_targets:
        t_texts = [tn['text'] for tn in low_t]
        n_texts = [dn['text'] for dn in emb_targets]
        embs = embed_batch(list({*t_texts, *n_texts}))
        emb_map = dict(zip([*t_texts, *n_texts], embs))
        for tn in low_t:
            for dn in emb_targets:
                c = cosine(emb_map.get(tn['text'], []), emb_map.get(dn['text'], []))
                if c >= EMB_TH:
                    pairs.append((round(c, 3), tn['id'], dn['id']))
    pairs.sort(key=lambda x: -x[0])
    matched_t, matched_d = set(), set()
    for sc, tid, did in pairs:
        if tid not in matched_t and did not in matched_d:
            matched_t.add(tid)
            matched_d.add(did)
    return {'matched_t': matched_t, 'matched_d': matched_d}


def compare_scene(anchor: dict, X_T: dict, scene: str) -> dict:
    """场景特定Tier 1比较: 锚点图 vs 编译表"""
    disc = []
    diag_nodes = [n for n in anchor['nodes']
                  if n['text'].strip() and n['type'] not in ('start', 'end')]
    # 接口图: 边标签也进比较池(接口名常是连线标签而非节点)
    if scene == 'sc3_interface_interface':
        edge_label_nodes = []
        nodes_map = {n['id']: n for n in anchor['nodes']}
        for e in anchor.get('edges', []):
            lbl = (e.get('label') or '').strip()
            if lbl:
                edge_label_nodes.append({'id': f"lbl_{e['src']}_{e['dst']}",
                                         'text': lbl, 'type': 'interface_label'})
        diag_nodes = diag_nodes + edge_label_nodes
    table_nodes = X_T.get('nodes', [])

    if not table_nodes:
        return {'discrepancies': [{'etype': 'table', 'dtype': 'TABLE_EMPTY',
                                   'evidence': '表格编译为空'}]}

    m = match_elements(table_nodes, diag_nodes)

    # 表侧元素缺失
    for tn in table_nodes:
        if tn['id'] not in m['matched_t']:
            disc.append({
                'etype': 'exst', 'dtype': 'TABLE_ITEM_MISSING',
                'table_side': {'id': tn['id'], 'text': tn['text'][:40]},
                'evidence': f"表格项「{tn['text'][:24]}」在图中无匹配",
            })
    # 图侧多余(仅报告, 语义弱——图可能含表外内容)
    n_extra = sum(1 for dn in diag_nodes if dn['id'] not in m['matched_d'])
    if n_extra:
        disc.append({
            'etype': 'exst', 'dtype': 'DIAGRAM_EXTRA_COUNT',
            'table_side': None,
            'evidence': f"图中有{n_extra}个节点无表格对应(粒度差异常见)",
        })

    # 场景特定: sc3接口表的收发方连通性
    if scene == 'sc3_interface_interface' and X_T.get('type') == 'interface':
        comp_texts = set()
        for dn in diag_nodes:
            if dn['type'] != 'interface_label':
                comp_texts.add(dn['text'])
        for itf in X_T['interfaces']:
            for ia in itf['interactions']:
                for role in ('sender', 'receiver'):
                    comp = ia[role]
                    if comp and comp not in ('本系统', ''):
                        best = max((text_match_score(comp, t) for t in comp_texts),
                                   default=0)
                        if best < MATCH_TH:
                            disc.append({
                                'etype': 'exst', 'dtype': 'COMPONENT_MISSING',
                                'table_side': {'text': comp, 'role': role},
                                'evidence': f"接口表{role}「{comp}」在图中无组件节点",
                            })
    return {'n_table': len(table_nodes), 'n_diag': len(diag_nodes),
            'n_matched': len(m['matched_t']), 'discrepancies': disc}


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

SCENE_COMPILER = {
    'sc1_usecase_capability': compile_capability_table,
    'sc3_interface_interface': compile_interface_table,
    'sc4_flowchart_capability': compile_capability_table,
    'sc5_function_capability': compile_subfunction_table,
}


def main():
    census = json.loads(CENSUS.read_text())
    anchors = json.loads(ANCHOR_V2.read_text())
    v2_idx = {}
    for doc, d in anchors.items():
        for s in d['structures']:
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s['nodes'] if n['text'])
            if key not in v2_idx or tn > v2_idx[key][0]:
                v2_idx[key] = (tn, s)

    results = {}
    stats = defaultdict(Counter)
    n_run = n_skip = 0

    for scene, compiler in SCENE_COMPILER.items():
        scene_dir = PAIR_ROOT / scene
        for pd in sorted(scene_dir.iterdir()):
            if not (pd / 'meta.json').exists():
                continue
            pk = pd.name
            table_path = pd / 'table.csv'
            if not table_path.exists():
                continue
            # 锚点: census重对齐 > pair的visio_anchor
            c = census.get(f'{scene}:{pk}'.split(':')[-1] if False else pk, {})
            anchor = None
            if c.get('status') == 'anchored' and c.get('new_embed'):
                entry = v2_idx.get((c['doc'], c['new_embed'].split(':')[0]))
                anchor = entry[1] if isinstance(entry, tuple) else entry
            if anchor is None:
                va = pd / 'visio_anchor.json'
                if va.exists():
                    va_data = json.loads(va.read_text())
                    # 转成anchor结构
                    anchor = va_data
            if anchor is None:
                n_skip += 1
                continue

            X_T = compiler(table_path)
            cmp_result = compare_scene(anchor, X_T, scene)
            cmp_result['scene'] = scene
            cmp_result['doc'] = c.get('doc') or anchor.get('source', '')
            results[pk] = cmp_result
            n_run += 1
            stats[scene]['n'] += 1
            stats[scene]['matched'] += cmp_result.get('n_matched', 0)
            stats[scene]['table'] += cmp_result.get('n_table', 0)
            for d in cmp_result['discrepancies']:
                stats[scene][d['dtype']] += 1

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    save_emb_cache()

    print(f"{'='*64}")
    print(f"M16: 多场景Tier 1比较 ({n_run}对运行, {n_skip}跳过)")
    print(f"{'='*64}")
    for scene, s in stats.items():
        match_rate = s['matched'] / max(1, s['table'])
        print(f"\n  [{scene}] {s['n']}对:")
        print(f"    表元素匹配率: {s['matched']}/{s['table']} = {match_rate:.0%}")
        for dt in ('TABLE_ITEM_MISSING', 'COMPONENT_MISSING', 'DIAGRAM_EXTRA_COUNT', 'TABLE_EMPTY'):
            if s[dt]:
                print(f"    {dt}: {s[dt]}")

    # 抽样drift候选
    print("\n  TABLE_ITEM_MISSING样例(每场景2条):")
    seen_scene = set()
    for pk, v in results.items():
        sc = v['scene']
        if sc in seen_scene:
            continue
        items = [d for d in v['discrepancies'] if d['dtype'] == 'TABLE_ITEM_MISSING']
        for d in items[:2]:
            print(f"    [{pk}]({sc[:6]}) {d['evidence'][:50]}")
        if items:
            seen_scene.add(sc)
    print(f"\n  输出: {OUT}")


if __name__ == '__main__':
    main()
