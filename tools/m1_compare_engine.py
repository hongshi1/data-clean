#!/usr/bin/env python3
"""
M1: 比对引擎 (ACDD Tier 1 核心)
================================
κ_T编译器(用例表→图) + N规范化 + μ节点匹配 + Δ类型化分歧提取

输入: anchors.json (M0修复后的锚点) + 89对sc2映射 + table.csv
输出: data/gjb_438c/anchor_sc2/tier1_discrepancies.json
      每对的类型化分歧列表 = provenance drift候选(真实不一致候选)

元素宇宙(sc2场景):
  exst(step)   — 表格步骤 ↔ 图节点 存在性
  exc(E_k)     — 异常流引用 ↔ 图中分支
  act(actor)   — Actors字段 ↔ 图中参与者节点
  dir(u,v)     — 步骤顺序 ↔ 图边方向 (仅直接矛盾时报)

用法: python3 tools/m1_compare_engine.py
"""
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies.json"

EMB_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
EMB_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
EMB_MODEL = "ep-qrkeon-1785654358657880827"
EMB_CACHE_PATH = BASE / "data/gjb_438c/anchor_sc2/emb_cache.pkl"
EMB_TH = 0.62  # embedding余弦匹配阈值

import pickle

# 兼容旧JSON缓存 → 迁移到pickle
_emb_cache = {}
_old_json = EMB_CACHE_PATH.with_suffix('.json')
if EMB_CACHE_PATH.exists():
    with open(EMB_CACHE_PATH, 'rb') as f:
        _emb_cache = pickle.load(f)
elif _old_json.exists():
    _emb_cache = json.loads(_old_json.read_text())
    with open(EMB_CACHE_PATH, 'wb') as f:
        pickle.dump(_emb_cache, f)
    _old_json.unlink()  # 删除旧的187MB JSON

_emb_dirty = 0


def embed_batch(texts: list[str]) -> list[list[float]]:
    """批量embedding(带pickle缓存, 节流写入)"""
    global _emb_dirty
    uncached = [t for t in texts if t not in _emb_cache]
    for i in range(0, len(uncached), 64):
        chunk = uncached[i:i+64]
        try:
            resp = requests.post(EMB_URL, headers={
                "Authorization": f"Bearer {EMB_KEY}", "Content-Type": "application/json"
            }, json={"model": EMB_MODEL, "input": chunk, "encoding_format": "float"},
                timeout=60)
            resp.raise_for_status()
            for t, d in zip(chunk, resp.json()["data"]):
                _emb_cache[t] = d["embedding"]
            _emb_dirty += 1
        except Exception:
            for t in chunk:
                _emb_cache[t] = []
    # 节流: 每8批写一次
    if _emb_dirty >= 8:
        with open(EMB_CACHE_PATH, 'wb') as f:
            pickle.dump(_emb_cache, f)
        _emb_dirty = 0
    return [_emb_cache.get(t, []) for t in texts]


def save_emb_cache():
    """进程退出前保存"""
    global _emb_dirty
    if _emb_dirty:
        with open(EMB_CACHE_PATH, 'wb') as f:
            pickle.dump(_emb_cache, f)
        _emb_dirty = 0


def cosine(a, b) -> float:
    if not a or not b:
        return 0.0
    num = sum(x*y for x, y in zip(a, b))
    den = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) + 1e-10
    return num / den


# ═══════════════════════════════════════════════════════════════
# N: 规范化 (良性变异商映射的确定性部分)
# ═══════════════════════════════════════════════════════════════

def normalize_text(s: str) -> str:
    """文本规范化: 编号剥离+空白压缩+全角半角统一"""
    if not s:
        return ''
    s = re.sub(r'^\s*\d+\s*[\.．、]\s*', '', s)          # 前导编号
    s = s.replace('（', '(').replace('）', ')')
    s = s.replace('，', ',').replace('。', '.').replace('；', ';')
    s = re.sub(r'\s+', '', s)                              # 全部空白
    return s.strip()


def char_keywords(s: str, k: int = 4) -> set[str]:
    """提取关键词: 中文滑动k字窗口 + 英文/数字token(INT/STRING等必须区分)"""
    cjk = re.findall(r'[\u4e00-\u9fff]', s)
    ascii_tokens = re.findall(r'[A-Za-z0-9]+', s)
    kws = set()
    if len(cjk) >= k:
        kws |= {''.join(cjk[i:i+k]) for i in range(len(cjk) - k + 1)}
    elif cjk:
        kws.add(''.join(cjk))
    kws |= {t.lower() for t in ascii_tokens if len(t) >= 2}
    return kws


# 同义字映射(领域挖掘: 坐↔席等)
SYN_CHARS = {'坐': '席'}  # 单向归一到规范形
# 接口名包裹模式: "与X交互接口"/"与X接口" → 核心X
IFACE_PAT = re.compile(r'^与(.+?)(?:交互)?接口$')


def _lev(a: str, b: str) -> int:
    """编辑距离"""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            cur.append(min(prev[j + 1] + 1, cur[j] + 1, prev[j] + (ca != cb)))
        prev = cur
    return prev[-1]


def _unwrap_interface(s: str) -> str:
    """'与X交互接口' → X"""
    m = IFACE_PAT.match(s)
    return m.group(1) if m else ''


def text_match_score(a: str, b: str) -> float:
    """确定性文本匹配分(0-1): 精确>包含>接口名解包>错字容差>字符重叠"""
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    # 包含关系
    if na in nb or nb in na:
        return 0.9
    # 功能词剥离后包含(修饰词差异: 数据抽取转换↔异构数据抽取与转换)
    FUNC_CHARS = set('与的及和或者对于在中上将下其各该')
    na_f = ''.join(c for c in na if c not in FUNC_CHARS)
    nb_f = ''.join(c for c in nb if c not in FUNC_CHARS)
    if len(na_f) >= 3 and len(nb_f) >= 3 and (na_f in nb_f or nb_f in na_f):
        return 0.87
    # 同义字归一后再试(坐位↔席位)
    na_s = ''.join(SYN_CHARS.get(c, c) for c in na)
    nb_s = ''.join(SYN_CHARS.get(c, c) for c in nb)
    if na_s == nb_s or na_s in nb_s or nb_s in na_s:
        return 0.88
    # 接口名解包: "与X交互接口" vs "X"(或反向)
    for u, other in ((na, nb), (nb, na)):
        core = _unwrap_interface(u)
        if core and (core in other or other in core) and len(core) >= 3:
            return 0.86
    # 错字容差: 编辑距离≤1且长度≥5(数据统一服访问服务↔数据统一访问服务)
    if min(len(na), len(nb)) >= 5 and _lev(na, nb) <= 1:
        return 0.85
    # 字符重叠 (4字窗口Jaccard)
    ka, kb = char_keywords(a), char_keywords(b)
    if ka and kb:
        j = len(ka & kb) / len(ka | kb)
        return round(j, 3)
    return 0.0


MATCH_TH = 0.5  # 匹配阈值


# ═══════════════════════════════════════════════════════════════
# κ_T: 用例表编译器
# ═══════════════════════════════════════════════════════════════

def compile_usecase_table(csv_path: Path) -> dict:
    """GJB用例描述表 → 结构化图 X_T

    节点: 主事件流步骤(process) + 异常流(exception)
    边:   顺序边 s_i→s_{i+1}; 步骤引用"异常流E1" → E1节点
    """
    if not csv_path.exists():
        return None
    rows = []
    with open(csv_path, encoding='utf-8') as f:
        for row in csv.reader(f):
            rows.append([c.strip() for c in row])
    text_all = csv_path.read_text(encoding='utf-8')

    # ── 头部字段 ──
    uc_name, actors = '', []
    for row in rows[:4]:
        for cell in row:
            m = re.search(r'Use\s*Case\s*名称[：:]\s*(.+)', cell)
            if m:
                uc_name = m.group(1).strip()
            m = re.search(r'Actors?[：:]\s*(.+)', cell, re.I)
            if m:
                actors = [a.strip() for a in re.split(r'[、,，;；]', m.group(1)) if a.strip()]

    # ── 主事件流步骤: 仅Actor/系统动作列(排除动作约束列), 按步骤号边界切分 ──
    steps = {}  # num -> text
    in_main = False
    main_zone = []
    for row in rows:
        joined = ''.join(row)
        if re.search(r'主事件流|基本流', joined):
            in_main = True
            continue
        if re.search(r'^\s*(后置条件|异常流|扩展流)', joined) and in_main:
            in_main = False
        if in_main and joined:
            # 只取前两列(Actor动作+系统动作), 排除动作约束列
            main_zone.append(' '.join(c for c in row[:2] if c))
    main_text = ' '.join(main_zone) if main_zone else text_all

    # 步骤号边界: 要求前面有分隔符(防"V10.0.0"误切)
    STEP_BOUND = re.compile(r'(?<![\w.])(\d{1,2})\s*[\.．、]\s*')
    parts = STEP_BOUND.split(main_text)
    # split带捕获组: [pre, num1, content1, num2, content2, ...]
    i = 1
    while i + 1 < len(parts) + 1 and i < len(parts):
        num_s, content = parts[i], parts[i+1] if i+1 < len(parts) else ''
        try:
            num = int(num_s)
        except ValueError:
            i += 2
            continue
        # 截断到下一个步骤号边界(分隔符+数字+点+中文)
        content = re.split(
            r'[\s,，;；]\d{1,2}\s*[\.．、]\s*[\u4e00-\u9fff]', content)[0]
        content = content.strip()
        if len(content) >= 4 and (num not in steps or len(content) > len(steps[num])):
            steps[num] = content
        i += 2

    # ── 异常流 ──
    exceptions = {}  # E1 -> text
    for m in re.finditer(r'异常流\s*(E\d+)\s*[：:]\s*([^\n]{4,})', text_all):
        eid = m.group(1).upper()
        exceptions[eid] = m.group(2).strip()
    # 步骤中的异常流引用
    step_exc_refs = defaultdict(list)  # step_num -> [E1, ...]
    for num, txt in steps.items():
        for m in re.finditer(r'异常流\s*(E\d+)', txt):
            step_exc_refs[num].append(m.group(1).upper())
    for eid in exceptions:
        for m in re.finditer(r'(?:执行|转到|进入)?异常流\s*' + re.escape(eid), text_all):
            pass  # refs already captured per-step

    # ── 编译为图 ──
    nodes = []
    edges = []
    sorted_nums = sorted(steps.keys())
    for num in sorted_nums:
        nodes.append({
            'id': f's{num}', 'num': num, 'text': steps[num],
            'type': 'process', 'exc_refs': step_exc_refs.get(num, []),
        })
    for eid, txt in exceptions.items():
        nodes.append({'id': f'exc_{eid}', 'text': txt, 'type': 'exception', 'eid': eid})
    # 顺序边
    for i in range(len(sorted_nums) - 1):
        edges.append({'src': f's{sorted_nums[i]}', 'dst': f's{sorted_nums[i+1]}',
                      'type': 'sequence'})
    # 异常流引用边
    for num, eids in step_exc_refs.items():
        for eid in eids:
            if eid in exceptions:
                edges.append({'src': f's{num}', 'dst': f'exc_{eid}', 'type': 'exception'})

    return {
        'uc_name': uc_name, 'actors': actors,
        'steps': steps, 'exceptions': exceptions,
        'nodes': nodes, 'edges': edges,
    }


# ═══════════════════════════════════════════════════════════════
# Δ: 类型化分歧提取
# ═══════════════════════════════════════════════════════════════

def classify_diagram(anchor: dict) -> str:
    """锚点图类型: usecase_diagram / flowchart"""
    text_types = [n['type'] for n in anchor['nodes'] if n['text']]
    if 'usecase' in text_types:
        return 'usecase_diagram'
    return 'flowchart'  # state/process/矩形框统一按流程类比对


def extract_discrepancies(anchor: dict, X_T: dict) -> dict:
    """锚点图 vs 编译表 → 类型化分歧列表 (按图类型分流)"""
    disc = []
    # 图侧语义节点: 有文本的非端点节点
    diag_nodes = [n for n in anchor['nodes']
                  if n['text'].strip() and n['type'] not in ('start', 'end')]
    diag_actors = [n for n in anchor['nodes'] if n['type'] == 'actor']
    diag_edges = anchor['edges']
    diagram_mode = classify_diagram(anchor)

    # ═══ 用例图模式: 只比对UC名 + Actors (步骤不映射用例节点) ═══
    if diagram_mode == 'usecase_diagram':
        uc_nodes = [n for n in diag_nodes if n['type'] == 'usecase']
        # UC名称匹配
        if X_T['uc_name']:
            best = max((text_match_score(X_T['uc_name'], un['text'])
                        for un in uc_nodes), default=0.0)
            if best < MATCH_TH:
                disc.append({
                    'etype': 'name', 'dtype': 'UC_NAME_MISMATCH',
                    'table_side': {'text': X_T['uc_name']},
                    'diag_side': {'usecase_texts': [un['text'][:20] for un in uc_nodes]},
                    'evidence': f"表格UC名「{X_T['uc_name']}」与图中用例节点不匹配(best={best:.2f})",
                })
        # Actors匹配
        for actor in X_T['actors']:
            best = max((text_match_score(actor, da['text']) for da in diag_actors),
                       default=0.0)
            if best < MATCH_TH:
                disc.append({
                    'etype': 'act', 'dtype': 'ACTOR_MISSING',
                    'table_side': {'text': actor},
                    'diag_side': {'actor_texts': [da['text'][:20] for da in diag_actors]},
                    'evidence': f"表格Actor「{actor}」在图中无参与者节点",
                })
        return {
            'diagram_mode': diagram_mode,
            'n_table_steps': 0, 'n_diag_nodes': len(uc_nodes),
            'n_matched': 0, 'discrepancies': disc,
        }

    # ═══ 流程图/状态图模式: 全量比对 ═══

    # ── μ: 步骤↔图节点匹配 (四层: 精确/包含/字符重叠/embedding) ──
    table_steps = [n for n in X_T['nodes'] if n['type'] == 'process']
    matched_step, matched_diag = {}, {}
    pairs = []
    for st in table_steps:
        for dn in diag_nodes:
            sc = text_match_score(st['text'], dn['text'])
            pairs.append((sc, st['id'], dn['id'], st, dn, 'lex'))
    # embedding层: 对词法低分配对补充语义分
    low = [p for p in pairs if p[0] < MATCH_TH]
    if low:
        step_texts = [p[3]['text'] for p in low]
        node_texts = [p[4]['text'] for p in low]
        all_texts = list({t for t in step_texts + node_texts if t})
        embs = embed_batch(all_texts)
        emb_map = dict(zip(all_texts, embs))
        for p in low:
            se = emb_map.get(p[3]['text'], [])
            ne = emb_map.get(p[4]['text'], [])
            if se and ne:
                c = cosine(se, ne)
                if c >= EMB_TH:
                    pairs.append((round(c, 3), p[1], p[2], p[3], p[4], 'emb'))
    pairs.sort(key=lambda x: -x[0])
    used_diag = set()
    for sc, sid, did, st, dn, via in pairs:
        if sid not in matched_step and did not in used_diag:
            matched_step[sid] = {'diag_id': did, 'score': sc, 'via': via}
            matched_diag[did] = {'step_id': sid, 'score': sc, 'via': via}
            used_diag.add(did)

    # ── exst(step): 步骤存在性 ──
    for st in table_steps:
        if st['id'] not in matched_step:
            disc.append({
                'etype': 'exst', 'dtype': 'STEP_MISSING',
                'table_side': {'id': st['id'], 'text': st['text'][:60]},
                'diag_side': None,
                'evidence': f"表格步骤{st['num']}「{st['text'][:30]}…」在图中无匹配节点",
            })
    for dn in diag_nodes:
        if dn['id'] not in matched_diag:
            disc.append({
                'etype': 'exst', 'dtype': 'DIAGRAM_EXTRA',
                'table_side': None,
                'diag_side': {'id': dn['id'], 'text': dn['text'][:60], 'type': dn['type']},
                'evidence': f"图节点「{dn['text'][:30]}…」({dn['type']})在表格中无对应步骤",
            })

    # ── act(actor): 参与者 ──
    for actor in X_T['actors']:
        best = max((text_match_score(actor, da['text']) for da in diag_actors),
                   default=0.0)
        if best < MATCH_TH:
            disc.append({
                'etype': 'act', 'dtype': 'ACTOR_MISSING',
                'table_side': {'text': actor},
                'diag_side': {'actor_texts': [da['text'][:20] for da in diag_actors]},
                'evidence': f"表格Actor「{actor}」在图中无参与者节点",
            })

    # ── exc(E_k): 异常流 ──
    for eid, etxt in X_T['exceptions'].items():
        # 异常流文本 vs 图节点(含边标签)
        best_node = max((text_match_score(etxt, dn['text']) for dn in diag_nodes),
                        default=0.0)
        best_edge = max((text_match_score(etxt, e.get('label', ''))
                         for e in diag_edges), default=0.0)
        # 也查"异常"关键词节点
        kw_hit = any('异常' in dn['text'] or '失败' in dn['text'] or '错误' in dn['text']
                     for dn in diag_nodes)
        if max(best_node, best_edge) < MATCH_TH and not kw_hit:
            disc.append({
                'etype': 'exc', 'dtype': 'EXC_MISSING',
                'table_side': {'eid': eid, 'text': etxt[:60]},
                'diag_side': None,
                'evidence': f"表格异常流{eid}「{etxt[:30]}…」在图中无分支表示",
            })

    # ── dir(u,v): 顺序直接矛盾 (保守: 仅直接反向边 + 双侧高置信匹配) ──
    HIGH_CONF = 0.75  # 参与方向比较的最低匹配分(防交叉错配假阳性)
    step_by_id = {n['id']: n for n in table_steps}
    edge_pairs = {}
    for e in diag_edges:
        edge_pairs[(e['src'], e['dst'])] = e
    seq_edges = [e for e in X_T['edges'] if e['type'] == 'sequence']
    for se in seq_edges:
        s1, s2 = se['src'], se['dst']
        m1 = matched_step.get(s1, {})
        m2 = matched_step.get(s2, {})
        d1, d2 = m1.get('diag_id'), m2.get('diag_id')
        if d1 and d2 and m1.get('score', 0) >= HIGH_CONF and m2.get('score', 0) >= HIGH_CONF:
            # 直接反向边 = 矛盾
            if (d2, d1) in edge_pairs and (d1, d2) not in edge_pairs:
                disc.append({
                    'etype': 'dir', 'dtype': 'ORDER_CONFLICT',
                    'table_side': {'seq': f"{step_by_id[s1]['num']}→{step_by_id[s2]['num']}"},
                    'diag_side': {'edge': f"{matched_diag[d2]['step_id']}→{matched_diag[d1]['step_id']}"},
                    'evidence': (f"表格步骤{step_by_id[s1]['num']}在{step_by_id[s2]['num']}之前, "
                                 f"但图中边方向相反"),
                })

    return {
        'diagram_mode': diagram_mode,
        'n_table_steps': len(table_steps),
        'n_diag_nodes': len(diag_nodes),
        'n_matched': len(matched_step),
        'discrepancies': disc,
    }


# ═══════════════════════════════════════════════════════════════
# Tier 1 跑批
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 64)
    print("M1: Tier 1 比对跑批 (锚点 vs κ_T编译表 → provenance drift候选)")
    print("=" * 64)

    anchors = json.loads(ANCHOR_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())

    # 锚点索引(多页Visio取文本节点最多的页)
    anchor_idx = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            key = (doc_name, s['embed_index'].split(':')[0])
            text_n = sum(1 for n in s['nodes'] if n['text'])
            if key not in anchor_idx or text_n > anchor_idx[key][0]:
                anchor_idx[key] = (text_n, s)
    anchor_idx = {k: v[1] for k, v in anchor_idx.items()}

    # 重对齐映射(M2.5, VLM桥修复旧映射错位) — 优先使用
    REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
    realigned = {}
    if REALIGN_PATH.exists():
        realigned = json.loads(REALIGN_PATH.read_text())

    results = {}
    stats = defaultdict(int)
    per_pair_counts = []

    for pair_key in sorted(mapping.keys()):
        m = mapping[pair_key]
        doc = m.get('doc', '')
        # 优先用重对齐的embed (M2.5 VLM桥)
        embed = m.get('visio_embed', '')
        ra = realigned.get(pair_key, {})
        if ra.get('status') in ('realigned', 'same'):
            embed = ra.get('new_embed', '').split(':')[0]
        elif ra.get('status') == 'unanchored':
            results[pair_key] = {'error': 'unanchored', 'reason': '图无Visio源'}
            stats['unanchored'] += 1
            continue
        anchor = anchor_idx.get((doc, embed))
        pair_dir = PAIR_DIR / m.get('pair_dir', pair_key)
        X_T = compile_usecase_table(pair_dir / 'table.csv')

        if anchor is None or X_T is None:
            results[pair_key] = {'error': 'anchor_or_table_missing'}
            stats['error'] += 1
            continue

        cmp_result = extract_discrepancies(anchor, X_T)
        cmp_result['doc'] = doc
        cmp_result['embed'] = embed
        cmp_result['mapping_status'] = ra.get('status', 'old')
        cmp_result['uc_name'] = X_T['uc_name']
        cmp_result['table_actors'] = X_T['actors']
        cmp_result['match_score'] = m.get('match_score', 0)
        results[pair_key] = cmp_result

        per_pair_counts.append(len(cmp_result['discrepancies']))
        for d in cmp_result['discrepancies']:
            stats[d['dtype']] += 1

    # ── 报告 ──
    n_ok = len(per_pair_counts)
    print(f"\n  跑批对数: {len(results)} (有效{n_ok})")
    if n_ok:
        sc = sorted(per_pair_counts)
        print(f"  每对分歧数: min{sc[0]} 中位{sc[n_ok//2]} max{sc[-1]} "
              f"均值{sum(sc)/n_ok:.1f}")
    print(f"\n  分歧类型分布 (drift候选):")
    for dt, c in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"    {dt:18s}: {c}")

    # 高置信子集: match_score>0.3的对(锚点-表格确实相关的)
    hi = {k: v for k, v in results.items()
          if isinstance(v, dict) and v.get('match_score', 0) > 0.3}
    hi_disc = sum(len(v.get('discrepancies', [])) for v in hi.values())
    print(f"\n  高置信子集(match>0.3): {len(hi)}对, {hi_disc}条分歧")

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                        encoding='utf-8')
    print(f"\n  输出: {OUT_PATH}")

    # 展示3个具体drift候选示例
    print(f"\n{'='*64}")
    print("drift候选示例(高置信对, 前6条):")
    print("=" * 64)
    shown = 0
    for k, v in sorted(hi.items(), key=lambda x: -len(x[1].get('discrepancies', []))):
        if shown >= 3 or not v.get('discrepancies'):
            break
        print(f"\n[{k}] {v.get('uc_name','')[:24]} (匹配度{v['match_score']}) "
              f"步骤{v['n_table_steps']}↔图节点{v['n_diag_nodes']} 已配{v['n_matched']}")
        for d in v['discrepancies'][:2]:
            print(f"  [{d['dtype']}] {d['evidence'][:70]}")
        shown += 1


if __name__ == "__main__":
    main()
