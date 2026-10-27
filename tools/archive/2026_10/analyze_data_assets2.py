# -*- coding: utf-8 -*-
"""第二轮: anchors_v2/lightrag/image_analyses/semantic_modality/stage0细节"""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'data/gjb_438c'

# ===== anchors_v2 per-doc =====
print("=== anchors_v2/anchors_v2.json ===")
av = json.load(open(f'{BASE}/anchor_v2/anchors_v2.json', encoding='utf-8'))
tot_f = tot_n = tot_e = 0
for doc, v in av.items():
    st = v.get('structures', [])
    nn = sum(len(s.get('nodes', [])) for s in st if isinstance(s, dict))
    ne = sum(len(s.get('edges', [])) for s in st if isinstance(s, dict))
    tot_f += len(st)
    tot_n += nn
    tot_e += ne
    print(f"  {doc[:14]}: visio={v.get('visio_count')} structures={len(st)} nodes={nn} edges={ne}")
print(f"  合计: structures={tot_f} nodes={tot_n} edges={tot_e}")
s0 = av[list(av.keys())[0]]['structures'][0]
print(f"  单structure keys: {list(s0.keys())}")

# ===== lightrag =====
print("=== lightrag_store ===")
le = json.load(open(f'{BASE}/data_assets/lightrag_store/kv_store_full_entities.json', encoding='utf-8'))
k0 = list(le.keys())[0]
inner = le[k0]
print(f"  outer keys(16) sample: {list(le.keys())[:2]}")
print(f"  inner[{k0[:20]}] type={type(inner).__name__} len={len(inner) if hasattr(inner,'__len__') else '-'}")
if isinstance(inner, str):
    print(f"  inner str head: {inner[:150]}")
elif isinstance(inner, dict):
    ik = list(inner.keys())[:3]
    print(f"  inner keys: {ik}")
    v = inner[ik[0]]
    print(f"  inner[{ik[0]}] type={type(v).__name__} head: {str(v)[:150]}")
# 实体总数
total_ents = 0
for k, v in le.items():
    if isinstance(v, dict):
        total_ents += len(v)
    elif isinstance(v, list):
        total_ents += len(v)
print(f"  实体总数(所有doc): {total_ents}")

# ===== image_analyses =====
print("=== chunks/srs_image_analyses.json ===")
ia = json.load(open(f'{BASE}/data_assets/chunks/srs_image_analyses.json', encoding='utf-8'))
print(f"  type={type(ia).__name__} keys={list(ia.keys()) if isinstance(ia,dict) else len(ia)}")
if isinstance(ia, dict):
    for k, v in ia.items():
        print(f"  {k}: {type(v).__name__} len={len(v) if hasattr(v,'__len__') else '-'}")
        if isinstance(v, list) and v:
            print(f"    sample keys: {list(v[0].keys()) if isinstance(v[0],dict) else v[0]}")
        elif isinstance(v, dict):
            vk = list(v.keys())[:3]
            print(f"    keys: {vk}")
            vv = v[vk[0]] if vk else None
            print(f"    v[{vk[0]}] head: {str(vv)[:200]}")

# ===== semantic_modality_data =====
print("=== semantic_modality_data.json ===")
sm = json.load(open(f'{BASE}/data_assets/semantic_modality_data.json', encoding='utf-8'))
scs = sm.get('scenarios', {})
print(f"  scenarios keys: {list(scs.keys())}")
for sc, v in scs.items():
    if isinstance(v, dict):
        print(f"  {sc}: keys={list(v.keys())[:8]}")
        insts = v.get('instances', v.get('pairs', []))
        if isinstance(insts, list):
            print(f"    instances: {len(insts)}")
            if insts and isinstance(insts[0], dict):
                print(f"    sample keys: {list(insts[0].keys())[:12]}")
print(f"  stats: {json.dumps(sm.get('stats', {}), ensure_ascii=False)[:300]}")

# ===== stage0 id_registry / section_registry 样例 =====
print("=== stage0_assets 细节 ===")
s0a = json.load(open(f'{BASE}/data_assets/stage0_assets.json', encoding='utf-8'))
idr = s0a['id_registry']
k0 = list(idr.keys())[0]
print(f"  id_registry: {len(idr)}个ID, sample[{k0}]:")
v0 = idr[k0]
if isinstance(v0, list) and v0:
    print(f"    {len(v0)}处出现, 第一处: {json.dumps(v0[0], ensure_ascii=False)[:250]}")
sr = s0a['section_registry']
sk0 = list(sr.keys())[0]
print(f"  section_registry[{sk0[:16]}]: {type(sr[sk0]).__name__} len={len(sr[sk0])}")
if isinstance(sr[sk0], list) and sr[sk0]:
    print(f"    sample: {json.dumps(sr[sk0][0], ensure_ascii=False)[:200]}")
fi = s0a['figure_index']
fk0 = list(fi.keys())[0]
print(f"  figure_index[{fk0[:16]}]: len={len(fi[fk0])}")
if fi[fk0]:
    print(f"    sample: {json.dumps(fi[fk0][0], ensure_ascii=False)[:250]}")
ti = s0a['table_index']
tk0 = list(ti.keys())[0]
print(f"  table_index[{tk0[:16]}]: len={len(ti[tk0])}")
if ti[tk0]:
    print(f"    sample: {json.dumps(ti[tk0][0], ensure_ascii=False)[:250]}")
print(f"  stats: {json.dumps(s0a['stats'], ensure_ascii=False)[:400]}")
