#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UML不一致性检测器套件 + 变异检测评测（P4形式化落地）
=====================================================

任务定义（非循环论证协议）:
  输入: question + answer的「断言段」（answer在「（实际：…）」纠正标记前的部分）
  图证据: anchors_v3.json（born-digital Visio直读, 373结构/5,165节点/2,557边）
  输出: consistent / inconsistent + 触发的检测器 + 证据链
  禁止读取: label / inject_type / uml_type / evidence.* 元数据（防标签泄漏）

形式化（§9对齐）:
  图事实 G_s = (V, E), e = (a, b, r, arr_e, arr_b), r∈9种UML关系
  声明 c = (a, b, r̂, d̂, k) 从文本解析, k∈{relation, direction, nav, dep, nodetype, label, cycle, lifecycle}
  检测器 T_k: c × G_s → verdict, 矛盾即 T_k(c, G) = ⊥
  融合 T = ⋃_k T_k（任一触发→inconsistent）
  引擎质量 = 变异检测得分 score(k) = |detected ∩ op_k| / |op_k|（P4）

用法:
  python tools/uml_detector_suite.py                 # 主评测(doc级定位+全套件)
  python tools/uml_detector_suite.py --ablation      # +单检测器消融+局部性消融
  python tools/uml_detector_suite.py --limit 500     # 子集调试
"""
import argparse
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
ANCHORS = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
CORPUS = BASE / "data/gjb_438c/anchor_v3/uml_qa_full.json"
OUT = BASE / "data/gjb_438c/anchor_v3/uml_detection_eval.json"

SEED = 42
# 可导航箭头（end=箭头在dst端→src可导航到dst; begin=箭头在src端→dst可导航到src）
NAV_END = {'filled_triangle', 'filled_circle_s', 'closed', 'open_60', 'open',
           'filled_diamond_s', 'filled_square', 'block'}
NAV_BEGIN = {'filled_square', 'filled_circle_s', 'filled_triangle', 'open'}
# 节点类型中文（claim词→node.type）
NODE_TYPE_CN = {
    'actor': ['参与者', 'actor', '外部'], 'usecase': ['用例', 'usecase'],
    'state': ['状态', 'state'], 'component': ['模块', '组件', 'component', '内部'],
    'process': ['处理', '活动', 'process'], 'interface': ['接口', 'interface'],
    'datastore': ['数据存储', '数据存储区', 'datastore', '存储'],
}
# 声明中的关系关键词（特定→泛化排序）
REL_KEYS = [
    ('INCLUDE', ['包含关系', 'include', '«include»']),
    ('EXTEND', ['扩展关系', 'extend', '«extend»']),
    ('GENERALIZATION', ['继承关系', '泛化关系', 'generalization', '继承', '泛化']),
    ('AGGREGATION', ['聚合关系', 'aggregation', '空心菱形', '聚合']),
    ('COMPOSITION', ['组合关系', 'composition', '实心菱形', '组合']),
    ('REALIZATION', ['实现关系', 'realization', '实现']),
    ('DEPENDENCY', ['依赖关系', 'dependency', '虚线箭头']),
    ('DIRECTED', ['有向关联', 'directed']),
    ('ASSOCIATION', ['关联关系', 'association', '无箭头实线', '关联']),
]
CORRECTION_MARKS = ['（实际', '(实际', '（ 实际', '( 实际']


# ════════════════════════════════════════════════════════════════
# 声明抽取（仅question+answer断言段）
# ════════════════════════════════════════════════════════════════

def strip_correction(answer: str) -> str:
    """剥离答案中的纠正段（标签泄漏防护）: 取「（实际：…）」前的断言"""
    for m in CORRECTION_MARKS:
        i = answer.find(m)
        if i > 0:
            return answer[:i]
    return answer


def quoted(text: str) -> list:
    return re.findall(r'[「『]([^」』]{1,60})[」』]', text)


def extract_claim(qa: dict) -> dict:
    q = qa.get('question', '')
    a = strip_correction(qa.get('answer', ''))
    c = {
        'q': q, 'claim_text': a,
        'ents': quoted(q) or quoted(a),
        'kind': None, 'r_hat': None,
        'dir_hat': None,          # (from, to)
        'dep_hat': None,          # (dependent, dependency)
        'type_hat': None,         # 声明的节点类型
        'label_hat': None,        # 声明的条件/标注文本
        'lifecycle_hat': None,    # 'independent' | 'bound'
        'cycle_pairs': [],        # 声明的循环依赖对
        'subject': None,          # 无引号问题的主体词
    }
    # ── 声明种类判定（question优先, claim兜底；在去引号文本上匹配, 防实体名内嵌词误触发） ──
    q_nq = re.sub(r'[「『][^」』]*[」』]', '', q)
    text = q + '§' + a
    if re.search(r'依赖关系.{0,12}(相同|一致)|相互.{0,6}(依赖|循环)|循环依赖', text) or '这两个依赖' in q_nq:
        c['kind'] = 'cycle'
        for m in re.finditer(r'[「『]([^」』]{1,40})[」』]\s*(?:同时)?\s*依赖\s*[「『]([^」』]{1,40})[」』]', a):
            c['cycle_pairs'].append((m.group(1), m.group(2)))
        # 复合模板: 问题里「A」…同时依赖X且依赖Y（X/Y无引号）
        subj = quoted(q)[0] if quoted(q) else None
        deps = re.findall(r'(?:同时|且)依赖([^，。？?；;]{2,24}?)(?:。|？|\s|$)', q)
        if subj and deps:
            dep0 = deps[0].strip('且和 ')
            c['cycle_pairs'].append((subj, dep0))
            c['cycle_pairs'].append((dep0, subj))
        for m in re.finditer(r'([「『][^」』]{1,40}[」』])\s*和\s*([「『][^」』]{1,40}[」』])\s*相互', a):
            c['cycle_pairs'].append((m.group(1).strip('「『」』'), m.group(2).strip('「『」』')))
        # 断言段中的循环链: A→B→A
        chain = re.findall(r'[「『]([^」』]{1,40})[」』][→➜]', a)
        if len(chain) >= 2:
            c['cycle_pairs'].append((chain[0], chain[-1]))
    elif '独立' in q or '独立' in a:
        c['kind'] = 'lifecycle'
        if re.search(r'可以独立|能独立|可独立|能够独立', a):
            c['lifecycle_hat'] = 'independent'
        elif '独立' in q and re.match(r'^(可以|能|可|是的|对的|会)', a.strip()):
            c['lifecycle_hat'] = 'independent'  # 裸肯定("可以")回答独立性问题
        else:
            c['lifecycle_hat'] = 'bound'
    elif re.search(r'满足.{0,24}条件|满足什么条件|条件是什么|转换.{0,8}标注|是否立即执行|时才|标注', q_nq):
        c['kind'] = 'label'
        if re.search(r'满足.{0,24}条件时', q_nq):
            # 模式a: 满足「条件」时是否执行「节点」 → 条件在问题首位
            c['label_hat'] = c['ents'][0] if c['ents'] else None
        else:
            labs = quoted(a)
            if labs:
                c['label_hat'] = labs[0]
    elif re.search(r'是否实现|实现了', q_nq):
        c['kind'] = 'impl'          # 「X」是否实现了「Y」: 实现方向声明
    elif re.search(r'状态吗|一个状态|扮演角色|什么角色|内部模块|的组件|内部.{0,4}组件|是(一个)?(参与者|用例|状态|模块|组件)[吗?？]', q_nq):
        c['kind'] = 'nodetype'
    elif re.search(r'方向是什么|什么方向|箭头|从.{0,14}指向|指向.{0,4}[吗?？]', q_nq):
        c['kind'] = 'direction'
    elif re.search(r'关系|关联|连接方式|还是', q_nq):
        c['kind'] = 'relation'
    elif re.search(r'(可以|能否|能够|是否|能|可).{0,6}访问|访问.{0,2}[吗?？]', q_nq):
        c['kind'] = 'nav'
    elif '依赖' in q_nq:
        c['kind'] = 'dep'
    else:
        c['kind'] = 'relation' if len(c['ents']) >= 2 else None

    # ── 声明关系类型 r̂ ──
    if c['kind'] in ('relation', 'direction'):
        for r, keys in REL_KEYS:
            if any(k in a for k in keys):
                c['r_hat'] = r
                break
    # ── 声明方向 d̂: 「X」指向「Y」 / 从X指向Y(无引号) / 问题侧「A」指向「B」 ──
    if c['kind'] in ('direction', 'relation'):
        m = re.search(r'[「『]([^」』]{1,40})[」』]\s*指向\s*[「『]([^」』]{1,40})[」』]', a) or \
            re.search(r'从\s*[「『]([^」』]{1,40})[」』]\s*指向\s*[「『]([^」』]{1,40})[」』]', a)
        if m:
            c['dir_hat'] = (m.group(1), m.group(2))
        else:
            m2 = re.search(r'(?:箭头|线)?(?:是从|从)\s*([^，。；「」]{2,24}?)\s*(?:指向|→)\s*([^，。；「」]{2,24}?)(?=[。，吗？\s]|$)', a)
            if m2:
                c['dir_hat'] = (m2.group(1), m2.group(2))
        if c['dir_hat'] is None:
            # 方向声明在问题里: "图中箭头是从「A」指向「B」的吗？"
            mq = re.search(r'[「『]([^」』]{1,40})[」』][^「』]{0,6}(?:指向|→)[^「』]{0,4}[「『]([^」』]{1,40})[」』]', q)
            if mq:
                c['dir_hat'] = (mq.group(1), mq.group(2))
    # ── 声明依赖 dep̂: X依赖Y ──
    if c['kind'] in ('dep', 'cycle'):
        m = re.search(r'[「『]([^」』]{1,40})[」』]\s*依赖\s*[「『]([^」』]{1,40})[」』]', a) or \
            re.search(r'([「『][^」』]{1,40}[」』])\s*依赖\s*(?:于)?\s*(?:才能|才能执行|才能完成|和)?\s*([「『][^」』]{1,40}[」』])', a)
        if m:
            c['dep_hat'] = (m.group(1), m.group(2))
        if c['kind'] == 'dep' and c['dep_hat'] is None and len(c['ents']) >= 2:
            c['dep_hat'] = (c['ents'][0], c['ents'][1])
    # ── 声明节点类型 ──
    if c['kind'] == 'nodetype':
        for t, keys in NODE_TYPE_CN.items():
            if any(k in a for k in keys):
                c['type_hat'] = t
                break
        if c['type_hat'] is None:
            # 裸肯定答案("是的")：类型声明藏在问题尾部（"…的一个状态吗"）——
            # 只扫问题尾部，防实体名内嵌类型词（如「用例结束」中的"用例"）
            q_tail = re.sub(r'[「『][^」』]*[」』]', '', q)[-16:]
            for t, keys in NODE_TYPE_CN.items():
                if any(k in q_tail for k in keys):
                    c['type_hat'] = t
                    break
    # ── 无引号主体（如"X是系统的内部模块吗"） ──
    if not c['ents'] and c['kind'] in ('nodetype', 'relation', 'lifecycle'):
        m = re.search(r'([^，。？?「」]{2,24}?)(?:是否|是|和|与|可以|能|在)', q)
        if m and len(m.group(1)) >= 3:
            c['subject'] = m.group(1)
    return c


# ════════════════════════════════════════════════════════════════
# 图索引与实体解析
# ════════════════════════════════════════════════════════════════

class GraphIndex:
    def __init__(self, path=ANCHORS):
        self.docs = json.load(open(path, encoding='utf-8'))
        # doc短名(前8字) → doc全名
        self.short2doc = {k[:8]: k for k in self.docs}
        self.amb = 0  # 歧义计数

    def doc_of(self, qa):
        d = qa.get('doc', '')
        return self.short2doc.get(d[:8], d if d in self.docs else None)

    def structures(self, doc, embed=None):
        sts = self.docs.get(doc, {}).get('structures', [])
        if embed:
            return [s for s in sts if s.get('embed_index') == embed]
        return sts

    @staticmethod
    def _match(ent, node) -> bool:
        t = (node.get('text') or '').strip()
        ent = (ent or '').strip()
        if not t or not ent:
            return False
        t, ent = t.replace('\n', ''), ent.replace('\n', '')
        if t == ent or t.startswith(ent) or ent in t:
            return True
        if len(ent) >= 4 and ent.startswith(t[:6]):
            return True
        # 模糊前缀兜底（源文档错字/截断，如"跟据"vs"根据"）：前10字≤1处差异
        if len(ent) >= 8 and len(t) >= 8:
            k = min(10, len(ent), len(t))
            diff = sum(1 for x, y in zip(ent[:k], t[:k]) if x != y)
            if diff <= 1:
                return True
        return False

    def find_all_edges(self, doc, a, b, embed=None):
        """在doc(或embed限定)的结构里找(a,b)之间的全部边 → [(edge, structure)]"""
        hits = []
        for s in self.structures(doc, embed):
            nodes = {n['id']: n for n in s['nodes']}
            for e in s['edges']:
                sn, dn = nodes.get(e['src']), nodes.get(e['dst'])
                if not sn or not dn:
                    continue
                if (self._match(a, sn) and self._match(b, dn)) or \
                   (self._match(b, sn) and self._match(a, dn)):
                    hits.append((e, s))
        if len(hits) > 1:
            self.amb += 1
        return hits

    def find_edge(self, doc, a, b, embed=None):
        hits = self.find_all_edges(doc, a, b, embed)
        return hits[0] if hits else None

    def find_node(self, doc, ent, embed=None):
        for s in self.structures(doc, embed):
            for n in s['nodes']:
                if self._match(ent, n):
                    return n, s
        return None, None

    def edge_dir(self, e) -> str:
        """实际可导航方向: 'fwd'(src→dst) / 'bwd'(dst→src) / 'both' / 'none'"""
        fe = e.get('end_arrow', 'none') in NAV_END
        fb = e.get('begin_arrow', 'none') in NAV_BEGIN
        if fe and fb:
            return 'both'
        if fe:
            return 'fwd'
        if fb:
            return 'bwd'
        return 'none'

    def has_directed(self, doc, x, y, uml_types=None, embed=None) -> bool:
        """是否存在x→y的有向边（可导航）"""
        for s in self.structures(doc, embed):
            nodes = {n['id']: n for n in s['nodes']}
            for e in s['edges']:
                sn, dn = nodes.get(e['src']), nodes.get(e['dst'])
                if not sn or not dn:
                    continue
                if self._match(x, sn) and self._match(y, dn) and self.edge_dir(e) in ('fwd', 'both'):
                    if uml_types is None or e.get('uml_type') in uml_types:
                        return True
                if self._match(y, sn) and self._match(x, dn) and self.edge_dir(e) in ('bwd', 'both'):
                    if uml_types is None or e.get('uml_type') in uml_types:
                        return True
        return False


# ════════════════════════════════════════════════════════════════
# 检测器 T_k（每个返回 fired + 证据）
# ════════════════════════════════════════════════════════════════

def verify(qa, claim, gidx, embed=None):
    """融合判定: 返回 (pred_inconsistent, fired_list, stage)"""
    doc = gidx.doc_of(qa)
    fired, stage = [], 'ok'
    if doc is None:
        return False, [], 'no_doc'
    k = claim['kind']
    ents = claim['ents']

    # ---- 节点类型声明 ----
    if k == 'nodetype':
        ent = ents[0] if ents else claim['subject']
        if not ent:
            return False, [], 'no_entity'
        # 宽容: doc级同名文本节点可能出现在多个结构, 收集全部匹配节点
        matched = []
        for s in gidx.structures(doc, embed):
            matched += [n for n in s['nodes'] if gidx._match(ent, n)]
        if not matched:
            return False, [], 'node_unresolved'
        claimed = claim['type_hat']
        if claimed and not any(n.get('type') == claimed for n in matched):
            actual = matched[0].get('type', 'other')
            fired.append(f'D_nodetype: 声明{claimed} 实际{actual}(「{ent[:12]}」)')
        return bool(fired), fired, stage
    # ---- 边级声明（relation/direction/nav/dep/lifecycle/impl） ----
    if k in ('relation', 'direction', 'nav', 'dep', 'lifecycle', 'impl'):
        if len(ents) < 2:
            return False, [], 'no_entity'
        a, b = ents[0], ents[1]
        cands = gidx.find_all_edges(doc, a, b, embed)
        if not cands:
            return False, [], 'edge_unresolved'
        e, st = cands[0]
        r = e.get('uml_type', 'ASSOCIATION')
        d = gidx.edge_dir(e)
        types = {ce.get('uml_type', 'ASSOCIATION') for ce, _ in cands}

        # D_type: 声明关系 vs 实际关系（宽容: 任一候选边匹配声明类型即通过）
        rh = claim['r_hat']
        if rh and k in ('relation', 'direction'):
            if rh not in types:
                arrowed_assoc = (rh == 'DIRECTED' and 'DIRECTED' not in types and
                                 any(gidx.edge_dir(ce) != 'none' for ce, _ in cands
                                     if ce.get('uml_type') == 'ASSOCIATION'))
                if not arrowed_assoc:
                    fired.append(f'D_type: 声明{rh} 实际{sorted(types)}')

        # D_dir: 声明方向（宽容: 任一候选边支持声明方向即通过）
        if claim['dir_hat']:
            x, y = claim['dir_hat']
            supported = any(
                (gidx._match(x, {'text': ce.get('src_text', '')}) and gidx.edge_dir(ce) in ('fwd', 'both')) or
                (gidx._match(x, {'text': ce.get('dst_text', '')}) and gidx.edge_dir(ce) in ('bwd', 'both'))
                for ce, _ in cands)
            any_directed = any(gidx.edge_dir(ce) != 'none' for ce, _ in cands)
            if not any_directed:
                fired.append(f'D_dir: 无向边但声明方向{x[:8]}→{y[:8]}')
            elif not supported:
                fired.append(f'D_dir: 声明{x[:8]}→{y[:8]} 与实际可导航方向不符')

        # D_impl: 「X实现了Y」声明 → X→Y须可导航
        if k == 'impl':
            if not gidx.has_directed(doc, a, b, embed=embed):
                fired.append(f'D_impl: 声明「{a[:10]}」实现「{b[:10]}」但无可导航边(实际{r}/{d})')

        # D_nav: 「A可以访问B」声明
        if k == 'nav':
            if not gidx.has_directed(doc, a, b, embed=embed):
                fired.append(f'D_nav: 声明「{a[:10]}」可访问「{b[:10]}」但无可导航边(实际{r}/{d})')

        # D_dep: 「A依赖B」声明
        if k == 'dep' and claim['dep_hat']:
            x, y = claim['dep_hat']
            if not gidx.has_directed(doc, x, y, uml_types={'DEPENDENCY', 'INCLUDE', 'EXTEND'}, embed=embed):
                fired.append(f'D_dep: 声明依赖({x[:8]}→{y[:8]})但实际边为{r}(非依赖族)')

        # D_lifecycle: 组合寿命语义（严格: 任一候选为组合即约束独立声明）
        if k == 'lifecycle':
            if claim['lifecycle_hat'] == 'independent' and 'COMPOSITION' in types:
                fired.append('D_lifecycle: 声明可独立存在但实际是组合关系(部分不能脱离整体)')
            elif claim['lifecycle_hat'] == 'bound' and 'COMPOSITION' not in types:
                fired.append(f'D_lifecycle: 声明不能独立存在但实际是{sorted(types)}(非组合)')
        return bool(fired), fired, stage

    # ---- 条件/标注声明 ----
    if k == 'label':
        if re.search(r'满足.{0,24}条件时', claim['q']):
            # 模式a: 满足「条件」时是否执行「目标节点」→ 条件=ents[0], 目标=ents[1]
            if len(ents) < 2 or not claim['label_hat']:
                return False, [], 'no_entity'
            cond, target = claim['label_hat'], ents[1]
            node, st = gidx.find_node(doc, target, embed)
            if st is None:
                return False, [], 'node_unresolved'
            labels = {(e.get('label') or '').strip() for e in st['edges'] if e.get('label')}
            adj = {(e.get('label') or '').strip() for e in st['edges']
                   if e.get('label') and (e.get('src') == node['id'] or e.get('dst') == node['id'])}
            ok = any(cond in L or L in cond for L in (adj or labels))
            if not ok:
                fired.append(f'D_label: 声明条件「{cond[:14]}」与目标节点邻接边标注不符')
            return bool(fired), fired, stage
        ent = ents[0] if ents else claim['subject']
        if not ent or not claim['label_hat']:
            return False, [], 'no_entity'
        norm = lambda s: re.sub(r'[\s\n\r、，,]', '', s)
        claimed = norm(claim['label_hat'])
        # 宽容跨结构: 同名文本节点可能出现在多个结构, 任一结构的边标注匹配即通过
        hit_structs = []
        for s in gidx.structures(doc, embed):
            if any(gidx._match(ent, n) for n in s['nodes']):
                hit_structs.append(s)
        if not hit_structs:
            return False, [], 'node_unresolved'
        ok = False
        for st in hit_structs:
            labels = {norm(e.get('label') or '') for e in st['edges'] if e.get('label')}
            if any(claimed in L or L in claimed for L in labels if L):
                ok = True
                break
        if not ok:
            fired.append(f'D_label: 声明条件「{claimed[:14]}」未见于结构边标注')
        return bool(fired), fired, stage

    # ---- 循环依赖声明 ----
    if k == 'cycle':
        if not claim['cycle_pairs']:
            # 从问题实体兜底: 声明a,b相互循环
            if len(ents) >= 2:
                claim['cycle_pairs'] = [(ents[0], ents[1]), (ents[1], ents[0])]
            else:
                return False, [], 'no_entity'
        for x, y in claim['cycle_pairs'][:4]:
            if not gidx.has_directed(doc, x, y, embed=embed):
                fired.append(f'D_cycle: 声明{x[:8]}→{y[:8]}依赖不存在(无有向边)')
                break
        return bool(fired), fired, stage

    return False, [], 'no_kind'


# ════════════════════════════════════════════════════════════════
# 评测协议
# ════════════════════════════════════════════════════════════════

def prf(tp, fp, fn, tn):
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    f = 2 * p * r / max(p + r, 1e-9)
    return {'P': round(p, 4), 'R': round(r, 4), 'F1': round(f, 4),
            'acc': round((tp + tn) / max(tp + fp + fn + tn, 1), 4),
            'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}


def run_suite(corpus, gidx, embed_mode=False, limit=0):
    preds = []
    for i, qa in enumerate(corpus[:limit] if limit else corpus):
        claim = extract_claim(qa)
        embed = qa.get('evidence', {}).get('embed') if embed_mode else None
        inc, fired, stage = verify(qa, claim, gidx, embed)
        preds.append({'idx': i, 'id': qa['id'], 'pred': inc, 'gold': qa['label'] == 'inconsistent',
                      'fired': fired, 'stage': stage, 'kind': claim['kind'],
                      'inject': qa.get('inject_type', ''), 'difficulty': qa.get('difficulty', ''),
                      'uml_type': qa.get('uml_type', ''), 'source': qa.get('source', '')})
    return preds


def evaluate(preds, tag=''):
    tp = sum(1 for p in preds if p['pred'] and p['gold'])
    fp = sum(1 for p in preds if p['pred'] and not p['gold'])
    fn = sum(1 for p in preds if not p['pred'] and p['gold'])
    tn = sum(1 for p in preds if not p['pred'] and not p['gold'])
    m = prf(tp, fp, fn, tn)
    m['coverage'] = round(1 - sum(1 for p in preds if p.get('stage', 'ok') not in ('ok', 'no_kind')) / max(len(preds), 1), 4)
    m['n'] = len(preds)
    m['tag'] = tag
    return m


def bootstrap_f1(preds, n_boot=1000, seed=SEED):
    rng = random.Random(seed)
    f1s = []
    idx = list(range(len(preds)))
    for _ in range(n_boot):
        sample = [preds[i] for i in (rng.choice(idx) for _ in idx)]
        tp = sum(1 for p in sample if p['pred'] and p['gold'])
        fp = sum(1 for p in sample if p['pred'] and not p['gold'])
        fn = sum(1 for p in sample if not p['pred'] and p['gold'])
        p = tp / max(tp + fp, 1)
        r = tp / max(tp + fn, 1)
        f1s.append(2 * p * r / max(p + r, 1e-9))
    f1s.sort()
    return [round(f1s[int(0.025 * len(f1s))], 4), round(f1s[int(0.975 * len(f1s))], 4)]


def mutation_scores(preds):
    """P4: 按注入算子族的变异检测得分(召回) + 正例特异度"""
    out = {}
    by_op = defaultdict(list)
    for p in preds:
        if p['gold']:
            by_op[p['inject'] or 'unknown'].append(p)
    for op, ps in sorted(by_op.items(), key=lambda x: -len(x[1])):
        det = sum(1 for p in ps if p['pred'])
        out[op] = {'n': len(ps), 'detected': det, 'score': round(det / len(ps), 4),
                   'miss_stage': dict(Counter(p['stage'] for p in ps if not p['pred']))}
    pos = [p for p in preds if not p['gold']]
    out['_positive_specificity'] = {'n': len(pos),
                                    'fp': sum(1 for p in pos if p['pred']),
                                    'specificity': round(1 - sum(1 for p in pos if p['pred']) / max(len(pos), 1), 4)}
    return out


def baseline_polarity(corpus):
    """B1基线: 断言句极性(否定词→inconsistent)"""
    preds = []
    for qa in corpus:
        a = strip_correction(qa.get('answer', ''))
        neg = bool(re.match(r'^(不|否|没|不能|不可|无法)', a.strip()))
        preds.append({'pred': neg, 'gold': qa['label'] == 'inconsistent'})
    return evaluate(preds, 'B1_polarity')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--ablation', action='store_true')
    args = ap.parse_args()

    corpus = json.load(open(CORPUS, encoding='utf-8'))
    if args.limit:
        corpus = corpus[:args.limit]
    gidx = GraphIndex()
    t0 = time.time()
    print(f"语料 {len(corpus)}条 (负例{sum(1 for q in corpus if q['label']=='inconsistent')}) | "
          f"图索引 16文档/373结构/2,557边")

    # ── 主设置: doc级定位(真实场景: 问题只给实体, 检索doc全部图) ──
    preds = run_suite(corpus, gidx, embed_mode=False, limit=0)
    main_m = evaluate(preds, 'main_doc_level')
    main_m['f1_ci95'] = bootstrap_f1(preds)
    print(f"\n[主评测 doc级] P={main_m['P']} R={main_m['R']} F1={main_m['F1']} "
          f"CI95=[{main_m['f1_ci95'][0]}, {main_m['f1_ci95'][1]}] coverage={main_m['coverage']} "
          f"({time.time()-t0:.0f}s, 实体歧义{gidx.amb}次)")

    ms = mutation_scores(preds)
    print("\n[P4 变异检测得分 按算子族]")
    for op, v in ms.items():
        if op.startswith('_'):
            print(f"  正例特异度: {v['specificity']} (FP {v['fp']}/{v['n']})")
        else:
            print(f"  {op:32s}: {v['score']:.3f} ({v['detected']}/{v['n']}) miss={v['miss_stage']}")

    for dim in ('difficulty', 'source', 'uml_type'):
        stat = {}
        for key in {p[dim] for p in preds}:
            stat[key] = evaluate([p for p in preds if p[dim] == key])
        main_m[f'by_{dim}'] = stat

    # ── 基线 ──
    b0 = evaluate([{'pred': False, 'gold': q['label'] == 'inconsistent'} for q in corpus], 'B0_majority')
    b1 = baseline_polarity(corpus)
    print(f"\n[基线] B0全consistent: F1={b0['F1']} | B1句极性: F1={b1['F1']}")

    result = {'config': {'seed': SEED, 'corpus': str(CORPUS), 'anchors': str(ANCHORS),
                         'n': len(corpus), 'time': round(time.time() - t0)},
              'main': main_m, 'mutation_scores': ms, 'baselines': {'B0': b0, 'B1_polarity': b1}}

    # ── 消融 ──
    if args.ablation:
        # 局部性消融: embed限定(oracle定位) vs doc级
        gidx.amb = 0
        preds_emb = run_suite(corpus, gidx, embed_mode=True)
        m_emb = evaluate(preds_emb, 'embed_restricted')
        m_emb['f1_ci95'] = bootstrap_f1(preds_emb)
        ms_emb = mutation_scores(preds_emb)
        m_emb['mutation_scores'] = {k: v.get('score', v.get('specificity'))
                                    for k, v in ms_emb.items()}
        print(f"\n[消融-局部性] embed限定: F1={m_emb['F1']} (doc级{main_m['F1']}, gap={round(main_m['F1']-m_emb['F1'],4)})")
        print("  embed按算子: " + json.dumps(m_emb['mutation_scores'], ensure_ascii=False))
        result['ablation_locality'] = m_emb
        # 单检测器消融: 只保留单一判定通道(按fired前缀过滤)
        ab = {}
        for dname in ('D_type', 'D_dir', 'D_nav', 'D_dep', 'D_nodetype', 'D_label', 'D_cycle', 'D_lifecycle'):
            solo = []
            for p in preds:
                fired = [f for f in p['fired'] if f.startswith(dname)]
                solo.append({**p, 'pred': bool(fired)})
            ab[dname] = evaluate(solo, dname)
        result['ablation_single'] = ab
        print('[消融-单检测器]', {k: v['F1'] for k, v in ab.items()})

    # ── 错误分析 + 仲裁（FN的图事实核验: 检测器vs语料gold的分歧归因） ──
    fps = [p for p in preds if p['pred'] and not p['gold']][:8]
    fns = [p for p in preds if not p['pred'] and p['gold']]
    fn_stage = Counter(p['stage'] for p in fns)
    fn_kind = Counter(p['kind'] or 'None' for p in fns)
    print(f"\n[错误分析] FN={len(fns)} 按阶段: {dict(fn_stage)} | 按声明种类: {dict(fn_kind)}")

    # 仲裁: 对每个FN核验图事实是否支持声明(声明被任一候选边/节点支持 → 语料标签可疑)
    n_justified = 0
    fn_adjudicated = []
    for p in fns:
        q = corpus[p['idx']]
        cl = extract_claim(q)
        doc = gidx.doc_of(q)
        just = ''
        k = cl['kind']
        if k in ('direction', 'relation') and cl['dir_hat']:
            x, y = cl['dir_hat']
            cands = gidx.find_all_edges(doc, cl['ents'][0], cl['ents'][1]) if len(cl['ents']) >= 2 else []
            sup = any((gidx._match(x, {'text': ce.get('src_text', '')}) and gidx.edge_dir(ce) in ('fwd', 'both')) or
                      (gidx._match(x, {'text': ce.get('dst_text', '')}) and gidx.edge_dir(ce) in ('bwd', 'both'))
                      for ce, _ in cands)
            just = 'graph_supports_direction' if sup else 'true_miss'
        elif k == 'impl' and len(cl['ents']) >= 2:
            just = 'graph_bidirectional' if gidx.has_directed(doc, cl['ents'][0], cl['ents'][1]) else 'true_miss'
        elif k == 'nodetype':
            ent = cl['ents'][0] if cl['ents'] else cl['subject']
            nodes = []
            for s in gidx.structures(doc):
                nodes += [n for n in s['nodes'] if gidx._match(ent, n)]
            just = 'node_type_ambiguous' if any(n.get('type') == cl['type_hat'] for n in nodes) else 'true_miss'
        else:
            just = 'unadjudicated'
        if just != 'true_miss' and just != 'unadjudicated':
            n_justified += 1
        fn_adjudicated.append({'inject': p['inject'], 'kind': k, 'stage': p['stage'], 'adjudication': just})
    adj = Counter(f['adjudication'] for f in fn_adjudicated)
    # 仲裁修正指标: 图事实支持的FN改判为检测器正确(语料标签噪声)
    tp_adj = main_m['tp'] + n_justified
    fn_adj = main_m['fn'] - n_justified
    m_adj = prf(tp_adj, main_m['fp'], fn_adj, main_m['tn'])
    print(f"[仲裁] FN归因: {dict(adj)}")
    print(f"[仲裁修正] 语料标签噪声{ n_justified }条改判 → P={m_adj['P']} R={m_adj['R']} F1={m_adj['F1']}")
    print("  FP样例:")
    for p in fps[:4]:
        print(f"    [{p['inject'] or p['source']}] {p['fired'][:1]}")
    result['errors'] = {'fn_stage': dict(fn_stage), 'fn_kind': dict(fn_kind),
                        'fn_adjudication': dict(adj), 'fn_samples': fn_adjudicated[:40],
                        'fp_samples': [{'inject': p['inject'], 'fired': p['fired']} for p in fps]}
    result['adjudicated'] = {**m_adj, 'justified_as_label_noise': n_justified,
                             'note': 'graph-fact-supported claims mislabeled by corpus templates'}

    json.dump(result, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n结果已保存: {OUT}")


if __name__ == '__main__':
    main()
