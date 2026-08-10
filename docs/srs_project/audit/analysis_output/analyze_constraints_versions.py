#!/usr/bin/env python3
"""
SRS约束与版本号深度分析脚本
- 读取16份 mineru_structured/*_structured.json
- 输出: analysis_output/*.json (机器可读中间结果)
- 最终报告由人/LLM汇总
"""
import json, os, re, glob
from collections import Counter, defaultdict
from pathlib import Path

STRUCT_DIR = Path('/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c/mineru_structured')
OUT_DIR = Path('/Users/gexuancheng/Desktop/research2/data_clean/analysis_output')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 加载 ----------
docs = []
for fp in sorted(STRUCT_DIR.glob('*_structured.json')):
    with open(fp, 'r', encoding='utf-8') as f:
        d = json.load(f)
    docs.append(d)
print(f'加载 {len(docs)} 份文档')

all_constraints = []
all_versions = []
for di, d in enumerate(docs):
    for c in d['all_constraints']:
        c2 = dict(c)
        c2['doc_idx'] = di
        c2['doc_name'] = d['doc_name']
        all_constraints.append(c2)
    for v in d['all_versions']:
        v2 = dict(v)
        v2['doc_idx'] = di
        v2['doc_name'] = d['doc_name']
        all_versions.append(v2)

print(f'总约束: {len(all_constraints)}, 总版本号: {len(all_versions)}')

# ---------- 1. 约束分布统计 ----------
def section_group(sec):
    """归一化到一级章节: 3.2 / 3.10 / 3.11 等"""
    if not sec: return '(空)'
    parts = sec.split('.')
    if len(parts) >= 2 and parts[0] == '3':
        return '.'.join(parts[:2])  # 3.2 / 3.10 / 3.11
    return parts[0] if parts else '(空)'

def section_l2(sec):
    """归一化到二级: 3.2.1 / 3.2.2 等"""
    if not sec: return '(空)'
    parts = sec.split('.')
    if parts[0] == '3' and len(parts) >= 3:
        return '.'.join(parts[:3])
    return section_group(sec)

section_dist = Counter()
section_l2_dist = Counter()
param_dist = Counter()
operator_dist = Counter()
unit_dist = Counter()
role_dist = Counter()
value_types = Counter()

for c in all_constraints:
    section_dist[section_group(c['section'])] += 1
    section_l2_dist[section_l2(c['section'])] += 1
    param_dist[c['param']] += 1
    operator_dist[c['operator']] += 1
    unit_dist[c['unit'] if c['unit'] else '(空)'] += 1
    role_dist[c['role']] += 1
    v = c['value']
    if isinstance(v, (int, float)):
        value_types['numeric'] += 1
    else:
        value_types['non-numeric'] += 1

dist_stats = {
    'total_constraints': len(all_constraints),
    'section_l1_dist': dict(section_dist.most_common()),
    'section_l2_dist_top20': dict(section_l2_dist.most_common(20)),
    'param_dist_top30': dict(param_dist.most_common(30)),
    'operator_dist': dict(operator_dist.most_common()),
    'unit_dist': dict(unit_dist.most_common()),
    'role_dist': dict(role_dist.most_common()),
    'value_types': dict(value_types),
}
with open(OUT_DIR/'dist_stats.json','w',encoding='utf-8') as f:
    json.dump(dist_stats, f, ensure_ascii=False, indent=2)

# ---------- 2. 同参数跨章节一致性 ----------
# 按文档+参数名分组
doc_param_groups = defaultdict(list)
for c in all_constraints:
    key = (c['doc_idx'], c['param'])
    doc_param_groups[key].append(c)

# 找出在同一文档内出现在多个section的参数
multi_section_params = {}
for key, cs in doc_param_groups.items():
    secs = set(c['section'] for c in cs)
    if len(secs) > 1:
        multi_section_params[f'{key[0]}|{key[1]}'] = [
            {
                'section': c['section'],
                'operator': c['operator'],
                'value': c['value'],
                'unit': c['unit'],
                'role': c['role'],
                'original': c['original'][:200]
            } for c in cs
        ]

# 找出跨章节值不一致的参数
value_conflicts = {}
for key, items in multi_section_params.items():
    # 比较 (operator, value, unit) 是否一致
    signatures = set()
    for it in items:
        sig = (it['operator'], str(it['value']), it['unit'])
        signatures.add(sig)
    if len(signatures) > 1:
        value_conflicts[key] = items

# 找出跨章节完全一致 (可能重复提取)
duplicates = {}
for key, items in multi_section_params.items():
    signatures = set()
    for it in items:
        sig = (it['operator'], str(it['value']), it['unit'])
        signatures.add(sig)
    if len(signatures) == 1 and len(items) > 1:
        duplicates[key] = items

cross_section_analysis = {
    'multi_section_param_count': len(multi_section_params),
    'multi_section_params': multi_section_params,
    'value_conflict_count': len(value_conflicts),
    'value_conflicts': value_conflicts,
    'duplicate_count': len(duplicates),
    'duplicates_sample': dict(list(duplicates.items())[:10]),
}
with open(OUT_DIR/'cross_section_analysis.json','w',encoding='utf-8') as f:
    json.dump(cross_section_analysis, f, ensure_ascii=False, indent=2)

# ---------- 3. 版本号分析 ----------
sw_dist = Counter()
for v in all_versions:
    sw_dist[v['software']] += 1

# 版本归一化: V8.1.1 -> 8.1.1 ; V8 -> 8 ; 7 -> 7
def normalize_version(ver):
    if not ver: return ''
    s = str(ver).strip()
    # 去 V/v 前缀
    s = re.sub(r'^[Vv]', '', s)
    # 去末尾 build/sp 等非版本字符
    s = re.split(r'[ ,]', s)[0]
    return s

# 按文档+软件分组
doc_sw_groups = defaultdict(list)
for v in all_versions:
    key = (v['doc_idx'], v['software'])
    doc_sw_groups[key].append(v)

# 同文档同软件的版本冲突
version_conflicts_raw = {}     # 原始冲突
version_conflicts_norm = {}    # 归一化后冲突
version_format_variants = {}   # 同软件有不同格式

for key, vs in doc_sw_groups.items():
    if len(set(v['section'] for v in vs)) < 2:
        continue  # 只出现在一个section,不分析跨章节
    raw_vers = set(v['version'] for v in vs)
    norm_vers = set(normalize_version(v['version']) for v in vs)
    
    if len(raw_vers) > 1:
        version_conflicts_raw[f'{key[0]}|{key[1]}'] = [
            {'section': v['section'], 'version': v['version'], 'norm': normalize_version(v['version']), 'original': v['original'][:150]}
            for v in vs
        ]
    if len(norm_vers) > 1:
        version_conflicts_norm[f'{key[0]}|{key[1]}'] = [
            {'section': v['section'], 'version': v['version'], 'norm': normalize_version(v['version']), 'original': v['original'][:150]}
            for v in vs
        ]

# 跨文档同软件版本对比
sw_groups_global = defaultdict(list)
for v in all_versions:
    sw_groups_global[v['software']].append(v)

cross_doc_sw_conflicts = {}
for sw, vs in sw_groups_global.items():
    norm_vers = set(normalize_version(v['version']) for v in vs)
    docs_with = set(v['doc_name'] for v in vs)
    if len(norm_vers) > 1 and len(docs_with) >= 1:
        cross_doc_sw_conflicts[sw] = {
            'total_mentions': len(vs),
            'docs': list(docs_with),
            'versions': [(v['version'], normalize_version(v['version']), v['doc_name'], v['section']) for v in vs]
        }

version_analysis = {
    'total_versions': len(all_versions),
    'software_dist_top25': dict(sw_dist.most_common(25)),
    'raw_version_conflict_count': len(version_conflicts_raw),
    'normalized_version_conflict_count': len(version_conflicts_norm),
    'version_conflicts_normalized': version_conflicts_norm,
    'cross_doc_software_versions': cross_doc_sw_conflicts,
}
with open(OUT_DIR/'version_analysis.json','w',encoding='utf-8') as f:
    json.dump(version_analysis, f, ensure_ascii=False, indent=2)

# ---------- 4. 约束提取质量问题 ----------
quality_issues = {
    'params_with_html': [],
    'params_with_punctuation': [],
    'generic_params': [],
    'non_numeric_values': [],
    'empty_unit_for_likely_unit_param': [],
    'duplicate_constraints_in_same_section': [],
    'suspicious_short_params': [],
}

GENERIC_PARAMS = {'配置', '存储', '内存', '要求', '能力', '时间', '数量', '速度', '性能', '容量', '参数', '值', '状态'}

for c in all_constraints:
    p = c['param']
    # HTML 残留
    if re.search(r'<[a-z/]+>', p) or '&lt;' in p or '&gt;' in p:
        quality_issues['params_with_html'].append({
            'doc': c['doc_name'], 'section': c['section'],
            'param': p, 'original': c['original'][:150]
        })
    # 标点残留
    if re.search(r'^[；;：:，,、（(]+|[；;：:，,、）)]+$', p) or re.search(r'^[①②③④⑤⑥⑦⑧⑨⑩]', p):
        quality_issues['params_with_punctuation'].append({
            'doc': c['doc_name'], 'section': c['section'],
            'param': p, 'original': c['original'][:150]
        })
    # 泛化参数名
    if p in GENERIC_PARAMS:
        quality_issues['generic_params'].append({
            'doc': c['doc_name'], 'section': c['section'],
            'param': p, 'value': c['value'], 'unit': c['unit'],
            'original': c['original'][:150]
        })
    # 非数值
    if not isinstance(c['value'], (int, float)):
        quality_issues['non_numeric_values'].append({
            'doc': c['doc_name'], 'section': c['section'],
            'param': p, 'value': c['value'],
            'original': c['original'][:150]
        })
    # 可能有单位但未提取
    if not c['unit']:
        orig = c['original']
        # 在 original 中查找数值+单位的模式
        m = re.search(r'[\d.]+\s*(条/秒|条/分|次/秒|次/分|ms|Mbps|Gbps|KB|MB|GB|TB|GHz|MHz|字节|bit|bps|帧/秒|路|个|台|核|颗|%)', orig)
        if m:
            quality_issues['empty_unit_for_likely_unit_param'].append({
                'doc': c['doc_name'], 'section': c['section'],
                'param': p, 'value': c['value'],
                'detected_unit': m.group(1),
                'original': c['original'][:200]
            })
    # 过短参数名
    if len(p) <= 2 and p not in {'CPU','IP','MAC','ID'}:
        quality_issues['suspicious_short_params'].append({
            'doc': c['doc_name'], 'section': c['section'],
            'param': p, 'value': c['value'],
            'original': c['original'][:150]
        })

# 同section内重复约束
sec_param_groups = defaultdict(list)
for c in all_constraints:
    key = (c['doc_idx'], c['section'], c['param'], c['operator'], str(c['value']), c['unit'])
    sec_param_groups[key].append(c)
for key, cs in sec_param_groups.items():
    if len(cs) > 1:
        quality_issues['duplicate_constraints_in_same_section'].append({
            'doc': cs[0]['doc_name'], 'section': cs[0]['section'],
            'param': cs[0]['param'], 'operator': cs[0]['operator'],
            'value': cs[0]['value'], 'unit': cs[0]['unit'],
            'count': len(cs),
            'originals': [c['original'][:120] for c in cs]
        })

quality_summary = {
    'params_with_html_count': len(quality_issues['params_with_html']),
    'params_with_punctuation_count': len(quality_issues['params_with_punctuation']),
    'generic_params_count': len(quality_issues['generic_params']),
    'non_numeric_values_count': len(quality_issues['non_numeric_values']),
    'empty_unit_for_likely_unit_param_count': len(quality_issues['empty_unit_for_likely_unit_param']),
    'duplicate_constraints_in_same_section_count': len(quality_issues['duplicate_constraints_in_same_section']),
    'suspicious_short_params_count': len(quality_issues['suspicious_short_params']),
}
quality_issues['_summary'] = quality_summary
with open(OUT_DIR/'quality_issues.json','w',encoding='utf-8') as f:
    json.dump(quality_issues, f, ensure_ascii=False, indent=2)

# ---------- 5. 逻辑约束可行性 ----------
# 按文档+参数分组,检测同参数的多约束是否有矛盾
logical_conflicts = []
for key, cs in doc_param_groups.items():
    if len(cs) < 2: continue
    # 检测 A<=v1 且 A>=v2 且 v2>v1 这种矛盾
    # 先归一化value, unit
    # 假设unit一致
    units = set(c['unit'] for c in cs)
    if len(units) > 1: continue  # 不同单位不直接比较
    
    # 找出 >= 和 <= 对
    ge_vals = [c['value'] for c in cs if c['operator'] in ('≥','>','>=') and isinstance(c['value'],(int,float))]
    le_vals = [c['value'] for c in cs if c['operator'] in ('≤','<','<=') and isinstance(c['value'],(int,float))]
    
    if ge_vals and le_vals:
        max_ge = max(ge_vals)  # A >= max_ge
        min_le = min(le_vals)  # A <= min_le
        if max_ge > min_le:
            logical_conflicts.append({
                'doc_idx': key[0], 'doc_name': cs[0]['doc_name'],
                'param': key[1], 'unit': list(units)[0],
                'max_lower_bound': max_ge,
                'min_upper_bound': min_le,
                'constraints': [
                    {'section': c['section'], 'operator': c['operator'], 'value': c['value'], 'original': c['original'][:150]}
                    for c in cs
                ]
            })

# 检测同参数同操作符但不同值 (A>=5 且 A>=10 — 不是矛盾,而是冗余/不同上下文)
redundant_constraints = []
for key, cs in doc_param_groups.items():
    if len(cs) < 2: continue
    units = set(c['unit'] for c in cs)
    if len(units) > 1: continue
    # 同操作符不同值
    op_vals = defaultdict(set)
    for c in cs:
        if isinstance(c['value'], (int, float)):
            op_vals[c['operator']].add(c['value'])
    for op, vals in op_vals.items():
        if len(vals) > 1:
            redundant_constraints.append({
                'doc_idx': key[0], 'doc_name': cs[0]['doc_name'],
                'param': key[1], 'operator': op, 'values': sorted(vals),
                'unit': list(units)[0],
                'constraints': [
                    {'section': c['section'], 'value': c['value'], 'original': c['original'][:150]}
                    for c in cs if c['operator']==op and isinstance(c['value'],(int,float))
                ]
            })

logical_analysis = {
    'logical_conflict_count': len(logical_conflicts),
    'logical_conflicts': logical_conflicts,
    'redundant_or_context_dependent_count': len(redundant_constraints),
    'redundant_or_context_dependent': redundant_constraints,
}
with open(OUT_DIR/'logical_analysis.json','w',encoding='utf-8') as f:
    json.dump(logical_analysis, f, ensure_ascii=False, indent=2)

# ---------- 6. 汇总打印 ----------
print('\n=== 汇总 ===')
print(f'约束总数: {len(all_constraints)}')
print(f'  章节分布(L1): {dict(section_dist.most_common())}')
print(f'  操作符: {dict(operator_dist.most_common())}')
print(f'  role: {dict(role_dist.most_common())}')
print(f'  单位top10: {dict(unit_dist.most_common(10))}')
print(f'  跨章节多出现的参数: {len(multi_section_params)}')
print(f'  跨章节值冲突: {len(value_conflicts)}')
print(f'  跨章节重复(完全一致): {len(duplicates)}')
print()
print(f'版本号总数: {len(all_versions)}')
print(f'  软件top15: {dict(sw_dist.most_common(15))}')
print(f'  原始版本冲突: {len(version_conflicts_raw)}')
print(f'  归一化后冲突: {len(version_conflicts_norm)}')
print()
print(f'质量问题:')
for k,v in quality_summary.items():
    print(f'  {k}: {v}')
print()
print(f'逻辑冲突: {len(logical_conflicts)}')
print(f'冗余/上下文相关: {len(redundant_constraints)}')
print()
print(f'输出目录: {OUT_DIR}')
