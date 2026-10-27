# -*- coding: utf-8 -*-
"""盘点全量数据资产: 每份资产覆盖哪些文档、规模、结构 —— 服务于全量图谱构建决策"""
import json
import sys
import glob
import os
import collections
sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(rel):
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding='utf-8'))

def doc_key(name):
    """从任意字符串提取文档序号+短名"""
    import re
    m = re.search(r'(\d{2})', name)
    return f"{m.group(1)}" if m else name[:10]

# ===== 1. mineru_standard: 16份文档解析底座 =====
print("=" * 70)
print("1. mineru_standard (解析底座)")
docs = sorted(glob.glob(os.path.join(BASE, 'data/gjb_438c/mineru_standard/*/office/*content_list.json')))
print(f"   文档数: {len(docs)}")
tot_img, tot_tbl = 0, 0
for d in docs:
    name = os.path.basename(d).replace('_content_list.json', '')
    cl = json.load(open(d, encoding='utf-8'))
    types = collections.Counter(i.get('type', '?') for i in cl if isinstance(i, dict))
    tot_img += types.get('image', 0)
    tot_tbl += types.get('table', 0)
    print(f"   doc{doc_key(name)}: items={len(cl):5d} text={types.get('text',0):4d} table={types.get('table',0):3d} image={types.get('image',0):3d}")
print(f"   合计: 图={tot_img} 表={tot_tbl}")

# ===== 2. stage0_assets: 8类结构化资产 =====
print("=" * 70)
print("2. stage0_assets.json (8类资产)")
s0 = load('data/gjb_438c/data_assets/stage0_assets.json')
if s0:
    print(f"   顶层keys: {list(s0.keys())[:12]}")
    for k, v in s0.items():
        if isinstance(v, list):
            print(f"   {k}: {len(v)}条")
            if v and isinstance(v[0], dict):
                print(f"      sample keys: {list(v[0].keys())[:10]}")
        elif isinstance(v, dict):
            print(f"   {k}: dict({len(v)})")

# ===== 3. id_document_graph: 实体图覆盖 =====
print("=" * 70)
print("3. graph/id_document_graph.json (实体+提及)")
g = load('data/gjb_438c/data_assets/graph/id_document_graph.json')
if g:
    docdist = collections.Counter(n.get('doc', '?')[:4] for n in g['nodes'])
    print(f"   节点按文档分布(前8): {dict(docdist.most_common(8))}")
    print(f"   总计: entity={g['entity_nodes']} mention={g['mention_nodes']} edges={g['edge_count']}")

# ===== 4. born_digital_structured: 374图金标准 =====
print("=" * 70)
print("4. born_digital_structured.json (Visio金标准)")
bd = load('data/gjb_438c/data_assets/born_digital_structured.json')
if bd:
    if isinstance(bd, list):
        print(f"   列表{len(bd)}条, sample keys: {list(bd[0].keys()) if bd else '-'}")
        dd = collections.Counter(x.get('doc', x.get('doc_name', '?'))[:6] for x in bd)
        print(f"   按文档: {dict(sorted(dd.items()))}")
        nn = sum(len(x.get('nodes', [])) for x in bd)
        print(f"   总节点数: {nn}")
    elif isinstance(bd, dict):
        print(f"   dict keys: {list(bd.keys())[:10]}")

# ===== 5. anchors_v2: 373图完整锚点 =====
print("=" * 70)
print("5. anchor_v2/anchors_v2.json (M11完整锚点)")
av = load('data/gjb_438c/anchor_v2/anchors_v2.json')
if av:
    if isinstance(av, dict):
        print(f"   dict keys({len(av)}): {list(av.keys())[:6]}...")
        vals = list(av.values())
        if vals and isinstance(vals[0], dict):
            print(f"   单锚点keys: {list(vals[0].keys())}")
            dd = collections.Counter(v.get('doc', '?')[:6] for v in vals if isinstance(v, dict))
            print(f"   按文档: {dict(sorted(dd.items()))}")
    elif isinstance(av, list):
        print(f"   列表{len(av)}条")

# ===== 6. visio_section_mapping =====
print("=" * 70)
print("6. graph/visio_section_mapping.json (图号↔Visio映射)")
vs = load('data/gjb_438c/data_assets/graph/visio_section_mapping.json')
if vs:
    print(f"   类型: {type(vs).__name__}, 规模: {len(vs)}")
    if isinstance(vs, list) and vs:
        print(f"   sample: {json.dumps(vs[0], ensure_ascii=False)[:200]}")
    elif isinstance(vs, dict):
        print(f"   sample: {json.dumps(list(vs.items())[0], ensure_ascii=False)[:200]}")

# ===== 7. chunks + image analyses =====
print("=" * 70)
print("7. chunks/srs_chunks.json + srs_image_analyses.json")
ck = load('data/gjb_438c/data_assets/chunks/srs_chunks.json')
if ck:
    print(f"   chunks: {len(ck)}条, sample keys: {list(ck[0].keys()) if isinstance(ck,list) and ck else '-'}")
ia = load('data/gjb_438c/data_assets/chunks/srs_image_analyses.json')
if ia:
    n = len(ia) if isinstance(ia, list) else len(ia.keys())
    print(f"   image_analyses: {n}条")
    v = ia[0] if isinstance(ia, list) else list(ia.values())[0]
    print(f"   sample keys: {list(v.keys()) if isinstance(v,dict) else '-'}")

# ===== 8. LightRAG =====
print("=" * 70)
print("8. lightrag_store")
le = load('data/gjb_438c/data_assets/lightrag_store/kv_store_full_entities.json')
if le:
    print(f"   实体数: {len(le)}")
lr = load('data/gjb_438c/data_assets/lightrag_store/kv_store_full_relations.json')
if lr:
    print(f"   关系数: {len(lr)}")

# ===== 9. eval_entities: 1011实体5类 =====
print("=" * 70)
print("9. eval_entities.json")
ee = load('data/gjb_438c/data_assets/eval_entities.json')
if ee:
    ents = ee.get('entities', ee) if isinstance(ee, dict) else ee
    print(f"   实体数: {len(ents)}")
    tc = collections.Counter(e.get('entity_type', '?') for e in ents)
    print(f"   类型分布: {dict(tc)}")

# ===== 10. semantic_modality_data =====
print("=" * 70)
print("10. semantic_modality_data.json (8场景模态)")
sm = load('data/gjb_438c/data_assets/semantic_modality_data.json')
if sm:
    if isinstance(sm, dict):
        print(f"   keys: {list(sm.keys())[:12]}")
    elif isinstance(sm, list):
        print(f"   列表{len(sm)}条, sample keys: {list(sm[0].keys())[:12]}")

# ===== 11. pair_dataset per-doc =====
print("=" * 70)
print("11. pair_dataset 按场景(对数)")
pairs = glob.glob(os.path.join(BASE, 'data/gjb_438c/pair_dataset/*/*/meta.json'))
sc = collections.Counter(os.path.basename(os.path.dirname(os.path.dirname(p))) for p in pairs)
for k in sorted(sc):
    print(f"   {k}: {sc[k]}对")

# ===== 12. capability_descriptions + usecase_features =====
print("=" * 70)
print("12. capability_descriptions / usecase_features")
cd = load('data/gjb_438c/data_assets/capability_descriptions.json')
uf = load('data/gjb_438c/data_assets/usecase_features.json')
print(f"   capability_descriptions: {len(cd) if cd else 0}条")
print(f"   usecase_features: {len(uf) if uf else 0}条")
if uf and isinstance(uf, list):
    print(f"   usecase sample keys: {list(uf[0].keys())[:10]}")
