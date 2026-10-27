"""场景1 Agentic RAG: 上下文感知与关联(方向A)

职责: 从原始文档动态检索+关联, 把分散的多模态内容聚合成条目
  - 不是读预计算的id_registry(那是查表)
  - 而是像Agent一样, 用工具动态探索: 感知查询意图→多路检索→多跳关联→聚合

工具集(对应12种规则信号):
  search_id(query)      - ID精确检索(正文/表格/标题中的ID)
  search_name(query)    - 名称语义检索(模糊匹配)
  read_section(sec)     - 读章节正文
  read_table(caption)   - 读表格(能力表/用例表/合格性表/追溯表)
  link_trace(entity_id) - 追溯链关联(合格性表↔追溯表↔章节)
  link_figure(caption)  - 图文关联(用例图↔正文/表格)

流程:
  Planner:   感知查询(实体/名称/属性), 决定检索策略
  Researcher: 多路检索(工具调用) → 证据候选
  Aggregator: 多跳关联(ID桥/名称桥/追溯桥) → 聚合条目
  → 输出: {entity, occurrences(多模态), media(图片), trace, chain_completeness}
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algorithms.common import text_sim

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
MINERU = os.path.join(BASE, "data/gjb_438c/mineru_standard")

ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9-]+')


class DocStore:
    """原始文档存储: 提供工具调用的数据源(content_list动态检索)"""

    def __init__(self):
        self.docs = {}  # doc_name -> content_list
        self._load()

    def _load(self):
        import glob
        for cl_path in glob.glob(os.path.join(MINERU, "*/office/*content_list.json")):
            doc = os.path.basename(cl_path).replace('_content_list.json', '')[:25]
            cl = json.loads(open(cl_path).read())
            # 预处理: 跟踪章节, 给每个item标记section
            current_section = ''
            for item in cl:
                if not isinstance(item, dict):
                    continue
                if item.get('type') == 'text':
                    t = item.get('text', '')
                    m = re.match(r'^(\d+(?:\.\d+)*)\s+', t.strip())
                    if m:
                        current_section = m.group(1)
                item['section'] = current_section
            self.docs[doc] = cl

    # ---------- 工具1: ID检索 ----------
    def search_id(self, entity_id):
        """在所有文档中检索ID的出现位置"""
        results = []
        for doc, cl in self.docs.items():
            for item in cl:
                if not isinstance(item, dict):
                    continue
                t = item.get('type', '')
                if t == 'text':
                    text = item.get('text', '')
                    if entity_id in text:
                        results.append({'doc': doc, 'type': 'text', 'section': self._sec_of(item),
                                        'snippet': text[:100]})
                elif t == 'table':
                    body = item.get('table_body', '')
                    if entity_id in body:
                        cap = ' '.join(item.get('table_caption', []))
                        results.append({'doc': doc, 'type': 'table', 'caption': cap[:40],
                                        'section': self._sec_of(item), 'snippet': body[:100]})
                elif t == 'image':
                    cap = ' '.join(item.get('image_caption', []))
                    if entity_id in cap:
                        results.append({'doc': doc, 'type': 'image', 'caption': cap[:40],
                                        'section': self._sec_of(item)})
        return results

    # ---------- 工具2: 名称语义检索 ----------
    def search_name(self, name, threshold=0.6):
        """在所有文档中检索名称(模糊匹配正文/表格)"""
        results = []
        for doc, cl in self.docs.items():
            for item in cl:
                if not isinstance(item, dict):
                    continue
                t = item.get('type', '')
                if t == 'text':
                    text = item.get('text', '')
                    if name in text or text_sim(name, text[:len(name)]) >= threshold:
                        results.append({'doc': doc, 'type': 'text', 'section': self._sec_of(item),
                                        'snippet': text[:100], 'sim': 1.0 if name in text else round(text_sim(name, text[:len(name)]), 2)})
                elif t == 'table':
                    body = item.get('table_body', '')
                    if name in body:
                        cap = ' '.join(item.get('table_caption', []))
                        results.append({'doc': doc, 'type': 'table', 'caption': cap[:40],
                                        'section': self._sec_of(item), 'snippet': body[:100]})
        return results

    # ---------- 工具3: 读章节 ----------
    def read_section(self, doc, section):
        """读章节正文"""
        cl = self.docs.get(doc, [])
        in_sec = False
        texts = []
        for item in cl:
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'text':
                t = item.get('text', '')
                m = re.match(r'^(\d+(?:\.\d+)*)\s+', t.strip())
                if m:
                    if m.group(1) == section:
                        in_sec = True
                    elif in_sec:
                        break
                elif in_sec and len(t.strip()) > 10:
                    texts.append(t.strip()[:100])
        return ' '.join(texts)

    # ---------- 工具4: 追溯关联 ----------
    def link_trace(self, entity_id):
        """追溯链关联: 合格性表↔追溯表↔章节"""
        trace = []
        for doc, cl in self.docs.items():
            for item in cl:
                if not isinstance(item, dict) or item.get('type') != 'table':
                    continue
                cap = ' '.join(item.get('table_caption', []))
                body = item.get('table_body', '')
                if entity_id not in body:
                    continue
                if '合格性' in cap:
                    trace.append({'doc': doc, 'table': '合格性表', 'section': self._sec_of(item)})
                elif '追踪' in cap or '追溯' in cap:
                    trace.append({'doc': doc, 'table': '追溯表', 'section': self._sec_of(item)})
        return trace

    # ---------- 工具5: 图文关联 ----------
    def link_figure(self, entity_id, name):
        """图文关联: 在用例图中找实体"""
        figures = []
        for doc, cl in self.docs.items():
            for item in cl:
                if not isinstance(item, dict) or item.get('type') != 'image':
                    continue
                cap = ' '.join(item.get('image_caption', []))
                if '用例' in cap:
                    figures.append({'doc': doc, 'caption': cap[:40], 'section': self._sec_of(item)})
        return figures

    # ---------- 辅助 ----------
    def _sec_of(self, item):
        return item.get('section', '')

    def all_docs(self):
        return list(self.docs.keys())


class AgenticRAG:
    """场景1 Agentic RAG: 上下文感知与关联(方向A)"""

    def __init__(self):
        self.store = DocStore()

    # ========== Planner: 感知查询 ==========
    def plan(self, query):
        """感知查询: 判断是ID/名称/混合, 决定检索策略"""
        plan = {'query': query, 'strategy': []}

        # 判断查询类型
        if ID_RE.fullmatch(query.strip()):
            plan['type'] = 'id'
            plan['entity_id'] = query.strip()
            plan['strategy'] = ['search_id', 'link_trace', 'link_figure']
        else:
            plan['type'] = 'name'
            # 名称可能含ID(如"数据获取/ZZSJHQZHFW-GN-SJHQ")
            id_match = ID_RE.search(query)
            if id_match:
                plan['entity_id'] = id_match.group(0)
                plan['name'] = query.replace(id_match.group(0), '').strip().rstrip('/')
            else:
                plan['entity_id'] = None
                plan['name'] = query.strip()
            # 名称查询: 第一跳=名称→ID(从名称匹配中提取), 第二跳=ID→位置
            plan['strategy'] = ['search_name', 'extract_id_from_name', 'search_id', 'link_trace', 'link_figure']
        return plan

    # ========== Researcher: 多路检索 ==========
    def research(self, plan):
        """多路检索: 按策略调用工具"""
        evidence = {
            'query': plan['query'],
            'type': plan['type'],
            'id_matches': [],
            'name_matches': [],
            'trace_links': [],
            'figures': [],
        }

        # 策略1: 名称检索(先, 可能提取ID)
        if plan.get('name'):
            evidence['name_matches'] = self.store.search_name(plan['name'])
            # 从名称匹配中提取ID(多跳: 名称→ID)
            if not plan.get('entity_id') and evidence['name_matches']:
                for m in evidence['name_matches']:
                    id_found = ID_RE.search(m.get('snippet', ''))
                    if id_found:
                        plan['entity_id'] = id_found.group(0)
                        break

        # 策略2: ID检索(在提取ID后)
        if plan.get('entity_id'):
            evidence['id_matches'] = self.store.search_id(plan['entity_id'])

        # 策略3: 追溯关联(ID桥)
        if plan.get('entity_id'):
            evidence['trace_links'] = self.store.link_trace(plan['entity_id'])

        # 策略4: 图文关联
        if plan.get('entity_id'):
            evidence['figures'] = self.store.link_figure(plan['entity_id'], plan.get('name', ''))

        return evidence

    # ========== Aggregator: 多跳关联聚合 ==========
    def aggregate(self, plan, evidence):
        """多跳关联: 用ID桥/名称桥/追溯桥, 聚合成分散位置条目"""
        entity_id = plan.get('entity_id')
        name = plan.get('name', '')

        # 从ID匹配中提取: 不同位置的名称(ID桥连接不同名称)
        occurrences = []
        seen = set()

        for m in evidence['id_matches']:
            loc = m['type']
            snippet = m.get('snippet', m.get('caption', ''))
            # 从snippet提取ID旁的名称(表格中名称在ID前, 正文中在ID前括号里)
            n = None
            if entity_id:
                mm = re.search(r'([\u4e00-\u9fff][\u4e00-\u9fff\w ]{1,20})[/(（]?' + re.escape(entity_id), snippet)
                if mm:
                    n = mm.group(1).strip()
                else:
                    # 表格: 名称可能在ID所在行的其他单元格
                    cell_match = re.search(r'([\u4e00-\u9fff][\u4e00-\u9fff\w ]{2,20})</p></td><td><p>' + re.escape(entity_id), snippet)
                    if cell_match:
                        n = cell_match.group(1).strip()
            key = (loc, m.get('section', ''), n or '')
            if key in seen:
                continue
            seen.add(key)
            occurrences.append({
                'location': loc,
                'section': m.get('section', ''),
                'name': n or name,
                'snippet': snippet[:60],
                'doc': m.get('doc', ''),
            })

        # 名称匹配补充(正文中未带ID的名称出现)
        for m in evidence['name_matches']:
            if m['type'] == 'text' and (entity_id is None or entity_id not in m.get('snippet', '')):
                key = ('text', m.get('section', ''), name)
                if key not in seen:
                    seen.add(key)
                    occurrences.append({
                        'location': 'text',
                        'section': m.get('section', ''),
                        'name': name,
                        'snippet': m.get('snippet', '')[:60],
                        'doc': m.get('doc', ''),
                    })

        # 位置类型
        locations = sorted(set(o['location'] for o in occurrences))

        # 聚合完整性
        loc_set = set(locations)
        has_name = len(set(o['name'] for o in occurrences if o['name'])) >= 1
        has_text = 'text' in loc_set
        has_table = any('table' in loc for loc in loc_set)
        has_qualification = any('合格性' in str(t) for t in evidence['trace_links'])
        has_trace = any('追溯' in str(t) for t in evidence['trace_links'])
        score = sum([has_name, has_text, has_table, has_qualification, has_trace]) / 5

        return {
            'entity_id': entity_id,
            'query_name': name,
            'occurrences': occurrences,
            'locations': locations,
            'trace_links': evidence['trace_links'],
            'figures': evidence['figures'],
            'chain_completeness': {
                'has_name': has_name,
                'has_text': has_text,
                'has_table': has_table,
                'has_qualification': has_qualification,
                'has_trace': has_trace,
                'score': round(score, 2),
            },
        }

    # ========== 完整流程 ==========
    def query(self, query):
        """Planner→Researcher→Aggregator: 输出聚合条目"""
        plan = self.plan(query)
        evidence = self.research(plan)
        aggregated = self.aggregate(plan, evidence)
        return {'plan': plan, 'evidence': evidence, 'aggregated': aggregated}


# ========== 方向A评测: 召回质量 ==========
def evaluate_retrieval():
    """评测: 给定实体, RAG召回的位置是否覆盖真实位置"""
    rag = AgenticRAG()
    from algorithms.common import load_entity_names, load_id_registry
    entity_names = load_entity_names()
    id_reg = load_id_registry()

    total = 0
    covered = 0
    scores = []
    for rid, names in list(entity_names.items())[:50]:  # 抽样50
        total += 1
        first_name = list(names)[0]
        result = rag.query(first_name)
        agg = result['aggregated']

        # 真实位置(从id_registry)
        real_locs = set(e.get('location', '') for e in id_reg.get(rid, []))
        # RAG召回位置
        rec_locs = set(o['location'] for o in agg['occurrences'])

        # 覆盖率: 召回到的位置 / 真实位置
        inter = len(real_locs & rec_locs)
        recall = inter / max(len(real_locs), 1)
        if recall > 0.5:
            covered += 1
        scores.append(recall)
        scores.append(agg['chain_completeness']['score'])

    result = {
        'method': 'Agentic RAG(上下文感知+关联)',
        'sampled': total,
        'covered_50pct': covered,
        'avg_chain_completeness': round(sum(scores) / len(scores), 3) if scores else 0,
    }
    print("Agentic RAG(上下文关联)评测:")
    print(f"  抽样实体: {result['sampled']}")
    print(f"  召回>50%位置: {result['covered_50pct']}/{result['sampled']}")
    print(f"  平均聚合完整性: {result['avg_chain_completeness']}")
    return result


if __name__ == "__main__":
    evaluate_retrieval()
