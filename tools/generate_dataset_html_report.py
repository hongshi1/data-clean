#!/usr/bin/env python3
"""生成数据集深度分析HTML报告"""
import json
from pathlib import Path
from datetime import datetime

def generate_html():
    examples = json.loads(Path('docs/srs_project/dataset_examples.json').read_text())
    
    # ===== 文档概览表 =====
    docs = examples['doc_overview']
    layer_colors = {
        '数据获取与处理层': '#e3f2fd',
        '集成框架层': '#e8f5e9',
        '运行支撑层': '#fff3e0',
        '传输通信层': '#fce4ec',
        '业务应用层': '#f3e5f5',
    }
    
    docs_rows = ''
    for d in docs:
        color = layer_colors.get(d['layer'], '#fafafa')
        docs_rows += f'''<tr style="background:{color}">
            <td>{d['doc']}</td>
            <td><span class="badge" style="background:{color}">{d['layer']}</span></td>
            <td><code>{d['prefix']}</code></td>
            <td class="num">{d['sections']}</td>
            <td class="num">{d['tables']}</td>
            <td class="num">{d['images']}</td>
            <td class="num">{d['constraints']}</td>
            <td class="num">{d['versions']}</td>
            <td class="num">{d['req_ids']}</td>
        </tr>'''
    
    totals = {
        'sections': sum(d['sections'] for d in docs),
        'tables': sum(d['tables'] for d in docs),
        'images': sum(d['images'] for d in docs),
        'constraints': sum(d['constraints'] for d in docs),
        'versions': sum(d['versions'] for d in docs),
        'req_ids': sum(d['req_ids'] for d in docs),
    }
    
    # ===== 系统架构图 =====
    layers = {}
    for d in docs:
        if d['layer'] not in layers:
            layers[d['layer']] = []
        layers[d['layer']].append(d)
    
    arch_diagram = '<div class="arch-stack">'
    layer_order = ['业务应用层', '传输通信层', '运行支撑层', '集成框架层', '数据获取与处理层']
    for layer in layer_order:
        if layer not in layers:
            continue
        color = layer_colors.get(layer, '#fafafa')
        doc_items = ''.join(
            f'<div class="arch-doc" style="border-color:{color}">{d["doc"][:15]}<br><small>{d["prefix"]}</small></div>'
            for d in layers[layer]
        )
        arch_diagram += f'''<div class="arch-layer" style="background:{color}">
            <div class="arch-layer-label">{layer}</div>
            <div class="arch-docs">{doc_items}</div>
        </div>'''
    arch_diagram += '</div>'
    
    # ===== 章节结构问题 =====
    struct_issues = examples.get('structure_issues', [])
    struct_html = ''
    for s in struct_issues:
        struct_html += f'''<div class="issue-card">
            <div class="issue-header">
                <span class="issue-doc">{s['doc']}</span>
                <span class="issue-type">{s['type']}</span>
            </div>
            <div class="issue-detail">{s['detail']}</div>
            <div class="issue-example"><code>{s.get('example','')}</code></div>
        </div>'''
    
    # 章节完整性
    sec_completeness = examples.get('section_completeness', [])
    sec_html = ''
    for s in sec_completeness:
        missing = ', '.join(s['missing_sections'])
        titles_html = ''
        for sec, title in sorted(s['present_titles'].items()):
            titles_html += f'<tr><td><code>{sec}</code></td><td>{title}</td></tr>'
        sec_html += f'''<div class="issue-card">
            <div class="issue-header"><span class="issue-doc">{s['doc']}</span></div>
            <div class="issue-detail">缺失章节: <strong>{missing}</strong></div>
            <table class="detail-table"><thead><tr><th>章节号</th><th>标题</th></tr></thead>
            <tbody>{titles_html}</tbody></table>
        </div>'''
    
    # ===== ID问题 =====
    id_issues = examples.get('id_issues', [])
    id_html = ''
    for i in id_issues[:10]:
        id_html += f'''<div class="issue-card">
            <div class="issue-header">
                <span class="issue-doc">{i['doc']}</span>
                <span class="issue-type">{i['type']}</span>
            </div>
            <div class="issue-detail">ID: <code>{i['id']}</code></div>
            <div class="issue-example">{i['detail']} → 修正: <code>{i.get('fix','')}</code></div>
        </div>'''
    
    # ID层级
    id_hierarchy = examples.get('req_id_hierarchy', [])
    hierarchy_html = ''
    for h in id_hierarchy:
        parts_html = ' → '.join(f'<span class="id-part">{p}</span>' for p in h['parts'])
        hierarchy_html += f'''<tr>
            <td>{h['doc']}</td>
            <td><code>{h['id']}</code></td>
            <td>{parts_html}</td>
            <td>{h.get('prefix','')}</td>
            <td>{h.get('category','')}</td>
            <td>{h.get('subsystem','')}</td>
        </tr>'''
    
    # ===== Ghost引用 =====
    ghosts = examples.get('ghost_refs', [])
    # 去重并按文档分组
    ghost_by_doc = {}
    seen = set()
    for g in ghosts:
        key = (g['doc'], g['ghost_ref'])
        if key not in seen:
            seen.add(key)
            if g['doc'] not in ghost_by_doc:
                ghost_by_doc[g['doc']] = []
            ghost_by_doc[g['doc']].append(g)
    
    ghost_html = ''
    for doc, items in sorted(ghost_by_doc.items()):
        rows = ''
        for g in items[:8]:
            rows += f'''<tr>
                <td><code class="ghost">{g['ghost_ref']}</code></td>
                <td>{g['section']}</td>
                <td class="truncate">{g['context']}</td>
            </tr>'''
        ghost_html += f'''<div class="issue-card">
            <div class="issue-header">
                <span class="issue-doc">{doc}</span>
                <span class="issue-type">{len(items)}个ghost引用</span>
            </div>
            <table class="detail-table"><thead><tr><th>引用章节号</th><th>来源章节</th><th>上下文</th></tr></thead>
            <tbody>{rows}</tbody></table>
        </div>'''
    
    # ===== 合格性表结构 =====
    qual_tables = examples.get('qualification_table_structure', [])
    qual_html = ''
    for q in qual_tables:
        headers_html = ''.join(f'<th>{h}</th>' for h in q['headers'])
        qual_html += f'''<tr>
            <td>{q['doc']}</td>
            <td>{q['section']}</td>
            <td class="num">{q['columns']}</td>
            <td class="num">{q['row_count']}</td>
            <td><div class="headers-list">{headers_html}</div></td>
        </tr>'''
    
    # ===== 追踪表结构 =====
    trace_tables = examples.get('traceability_table_structure', [])
    trace_html = ''
    for t in trace_tables[:15]:
        headers_html = ''.join(f'<th>{h}</th>' for h in t['headers'])
        trace_html += f'''<tr>
            <td>{t['doc']}</td>
            <td>{t['section']}</td>
            <td class="num">{t['columns']}</td>
            <td class="num">{t['row_count']}</td>
            <td><div class="headers-list">{headers_html}</div></td>
        </tr>'''
    
    # ===== 约束矛盾 =====
    conflicts = examples.get('constraint_conflicts', [])
    conflict_html = ''
    for c in conflicts[:12]:
        values_html = ''
        for v in c['values']:
            values_html += f'''<tr>
                <td><code>{v['op']} {v['val']} {v.get('unit','')}</code></td>
                <td>{v['section']}</td>
                <td class="truncate">{v['original']}</td>
            </tr>'''
        conflict_html += f'''<div class="issue-card conflict">
            <div class="issue-header">
                <span class="issue-doc">{c['doc']}</span>
                <span class="issue-type">参数: {c['param']}</span>
            </div>
            <table class="detail-table"><thead><tr><th>约束值</th><th>章节</th><th>原文</th></tr></thead>
            <tbody>{values_html}</tbody></table>
        </div>'''
    
    # ===== 版本冲突 =====
    version_conflicts = examples.get('version_conflicts', [])
    version_detail = examples.get('cross_doc_version_detail', [])
    
    version_html = ''
    for v in version_detail:
        rows = ''
        for ver in v['versions']:
            docs_str = ', '.join(ver['docs'])
            rows += f'''<tr>
                <td><code>{ver['version']}</code></td>
                <td class="num">{ver['doc_count']}</td>
                <td>{docs_str}</td>
            </tr>'''
        version_html += f'''<div class="issue-card">
            <div class="issue-header">
                <span class="issue-type">{v['software']}</span>
            </div>
            <table class="detail-table"><thead><tr><th>版本</th><th>文档数</th><th>使用文档</th></tr></thead>
            <tbody>{rows}</tbody></table>
        </div>'''
    
    # ===== 跨文档关系 =====
    cross_doc = examples.get('cross_doc_relations', [])
    cross_html = ''
    for c in cross_doc:
        cross_html += f'''<tr>
            <td>{c['doc1']}</td>
            <td>{c['doc2']}</td>
            <td><code>{c['shared_id']}</code></td>
            <td>{c['type']}</td>
        </tr>'''
    
    # ===== 图片问题 =====
    image_issues = examples.get('image_issues', [])
    image_html = ''
    for i in image_issues:
        image_html += f'''<tr>
            <td>{i['doc']}</td>
            <td class="num">{i['img_count']}</td>
            <td class="num">{i['unique_paths']}</td>
            <td>{i['issue']}</td>
            <td class="truncate">{i['root_cause']}</td>
        </tr>'''
    
    # ===== 解析质量 =====
    parse_issues = examples.get('parse_quality', [])
    parse_html = ''
    for p in parse_issues[:15]:
        if p['type'] == '版本号噪声':
            parse_html += f'''<tr>
                <td>{p['doc']}</td>
                <td>版本号噪声</td>
                <td>{p['software']}</td>
                <td><code class="error">{p['wrong_version']}</code></td>
                <td class="truncate">{p['original']}</td>
            </tr>'''
        else:
            parse_html += f'''<tr>
                <td>{p['doc']}</td>
                <td>unit缺失</td>
                <td>{p['param']}</td>
                <td><code>{p['value']}</code></td>
                <td class="truncate">{p['original']}</td>
            </tr>'''
    
    # ===== 用例表示例 =====
    usecases = examples.get('usecase_table_examples', [])
    usecase_html = ''
    # 每文档取1个
    seen_docs = set()
    for u in usecases:
        if u['doc'] in seen_docs:
            continue
        seen_docs.add(u['doc'])
        constraints_html = ''
        if u.get('action_constraints'):
            for ac in u['action_constraints']:
                constraints_html += f'<div class="action-constraint">{ac}</div>'
        else:
            constraints_html = '<em>(未提取到动作约束)</em>'
        
        usecase_html += f'''<tr>
            <td>{u['doc']}</td>
            <td>{u['section']}</td>
            <td>{u['usecase_name']}</td>
            <td><code>{u['usecase_id']}</code></td>
            <td class="num">{u['row_count']}</td>
            <td>{constraints_html}</td>
        </tr>'''
    
    # ===== MinerU完整性评估 =====
    mineru_issues = [
        {'severity': '严重', 'issue': '图片提取失败', 'detail': '16份文档的原始.docx均使用EMF格式图片，MinerU无法正确裁切，导致14份文档的所有图片(共370张)指向同一个jpg文件', 'impact': '图片内容完全丢失，无法进行图文关联分析', 'fix': '需用LibreOffice将EMF转为PNG后重新提取'},
        {'severity': '中等', 'issue': '约束重复提取', 'detail': '同一约束在多个子章节被重复提取。文档02: 56条→35条去重(21条重复)，文档03: 52条→38条(14条重复)', 'impact': '约束数量虚高，可能产生重复的矛盾检测', 'fix': '在提取后增加去重步骤'},
        {'severity': '中等', 'issue': '约束unit缺失', 'detail': '763条约束中239条(31.3%)的unit字段为空，主要集中在"存储""主频""内存"等参数', 'impact': '单位对齐困难，影响语义层矛盾检测', 'fix': '从原文中补充提取单位'},
        {'severity': '中等', 'issue': '用例表动作约束未提取', 'detail': '472个用例描述表中的"动作约束"列内容未被提取为结构化约束。用例表以键值对形式存储(非标准表格)，导致约束提取器遗漏', 'impact': '约束覆盖率降低约74.6%', 'fix': '增加用例表专用解析器'},
        {'severity': '低', 'issue': 'req_id无位置信息', 'detail': 'all_req_ids仅为字符串列表，不包含每个ID出现的具体位置(章节标题/合格性表/追踪表)', 'impact': 'ID一致性校验需要重新扫描全文', 'fix': '在提取时记录location字段'},
        {'severity': '低', 'issue': '版本号噪声', 'detail': '52处版本号提取错误，如"达梦3"(行号误识别)、"Windows 7/Windows 10"(双版本拆分)', 'impact': '版本冲突检测产生假阳性', 'fix': '增加版本号格式校验'},
        {'severity': '低', 'issue': '图片caption格式不统一', 'detail': '三种格式并存: "图 1 XXX"(空格分隔)、"图1 XXX"(无空格)、"图1XXX"(无分隔)', 'impact': 'caption解析需要多种正则', 'fix': '统一caption格式'},
    ]
    
    mineru_html = ''
    for m in mineru_issues:
        sev_class = 'sev-critical' if m['severity'] == '严重' else ('sev-medium' if m['severity'] == '中等' else 'sev-low')
        mineru_html += f'''<tr>
            <td><span class="severity {sev_class}">{m['severity']}</span></td>
            <td><strong>{m['issue']}</strong></td>
            <td>{m['detail']}</td>
            <td>{m['impact']}</td>
            <td>{m['fix']}</td>
        </tr>'''
    
    # ===== 组装HTML =====
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GJB 438C SRS数据集深度分析报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; 
       background: #f5f5f5; color: #333; line-height: 1.6; padding: 20px; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
h1 {{ color: #1a237e; margin: 20px 0 10px; font-size: 28px; }}
h2 {{ color: #283593; margin: 30px 0 15px; font-size: 22px; border-bottom: 2px solid #283593; padding-bottom: 5px; }}
h3 {{ color: #37474f; margin: 20px 0 10px; font-size: 18px; }}
.meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}

/* 表格 */
table {{ width: 100%; border-collapse: collapse; background: white; margin: 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th {{ background: #283593; color: white; padding: 10px 12px; text-align: left; font-weight: 500; font-size: 14px; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; }}
tr:hover {{ background: #f5f5f5; }}
.num {{ text-align: right; font-family: monospace; }}
tr.total {{ background: #e8eaf6; font-weight: bold; }}

/* 架构图 */
.arch-stack {{ display: flex; flex-direction: column-reverse; gap: 2px; margin: 20px 0; }}
.arch-layer {{ padding: 10px 15px; border-radius: 8px; display: flex; align-items: center; gap: 15px; }}
.arch-layer-label {{ min-width: 150px; font-weight: bold; font-size: 14px; }}
.arch-docs {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.arch-doc {{ background: white; border: 2px solid; border-radius: 6px; padding: 8px 12px; font-size: 13px; text-align: center; min-width: 120px; }}
.arch-doc small {{ color: #666; font-size: 11px; }}

/* 问题卡片 */
.issue-card {{ background: white; border-left: 4px solid #e53935; border-radius: 4px; padding: 15px; margin: 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.issue-card.conflict {{ border-left-color: #ff9800; }}
.issue-header {{ display: flex; gap: 15px; margin-bottom: 8px; align-items: center; }}
.issue-doc {{ font-weight: bold; color: #1a237e; }}
.issue-type {{ background: #ffe0b2; color: #e65100; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
.issue-detail {{ margin: 5px 0; font-size: 14px; }}
.issue-example {{ background: #f5f5f5; padding: 8px; border-radius: 4px; font-size: 13px; margin-top: 5px; }}
.issue-example code {{ color: #c62828; }}

/* detail-table */
.detail-table {{ margin: 8px 0; font-size: 13px; }}
.detail-table th {{ background: #455a64; font-size: 12px; padding: 6px 10px; }}
.detail-table td {{ padding: 6px 10px; }}

/* badges */
.badge {{ padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
.headers-list {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.headers-list th {{ background: #78909c; font-size: 12px; padding: 4px 8px; border-radius: 4px; }}

/* ghost */
code.ghost {{ background: #ffcdd2; color: #b71c1c; padding: 2px 6px; border-radius: 3px; font-weight: bold; }}
code.error {{ background: #ffcdd2; color: #b71c1c; }}

/* severity */
.severity {{ padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
.sev-critical {{ background: #ffcdd2; color: #b71c1c; }}
.sev-medium {{ background: #fff9c4; color: #f57f17; }}
.sev-low {{ background: #c8e6c9; color: #2e7d32; }}

/* misc */
.truncate {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.id-part {{ background: #e3f2fd; padding: 2px 6px; border-radius: 3px; margin: 0 2px; font-family: monospace; font-size: 12px; }}
.action-constraint {{ background: #fff3e0; padding: 4px 8px; border-radius: 3px; margin: 2px 0; font-size: 12px; }}
.summary-box {{ background: white; padding: 20px; border-radius: 8px; margin: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.summary-box ul {{ padding-left: 20px; }}
.summary-box li {{ margin: 5px 0; }}
.callout {{ background: #e3f2fd; border-left: 4px solid #1976d2; padding: 15px; border-radius: 4px; margin: 15px 0; }}
.callout strong {{ color: #1565c0; }}
</style>
</head>
<body>
<div class="container">

<h1>GJB 438C SRS数据集深度分析报告</h1>
<div class="meta">分析对象：16份真实GJB格式软件需求规格说明 | 生成日期：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据路径：<code>data/gjb_438c/mineru_structured/</code></div>

<!-- ===== 概况 ===== -->
<h2>一、数据集概况</h2>
<div class="summary-box">
<p>本数据集包含16份来自某军事信息系统的软件需求规格说明（SRS），均遵循GJB 438C军用软件文档标准格式。
数据集总体量为<strong>{totals['sections']:,}个章节、{totals['tables']:,}个表格、{totals['images']:,}张图片、{totals['constraints']:,}条约束、{totals['versions']:,}条版本号、{totals['req_ids']:,}个需求ID</strong>。</p>
<p>15份文档（02~16）共享<code>PZXQ</code>项目前缀，属于同一大型工程项目；文档01使用独立的<code>ZZSJHQZHFW</code>前缀，来自不同项目批次。
这一特征意味着<strong>上下文关联与一致性校验需要同时考虑文档内部和文档之间两个层面</strong>。</p>
</div>

<h3>1.1 系统架构分层</h3>
<div class="callout">
<strong>关键发现：</strong>16份文档覆盖了一个完整军事信息体系的5个子系统层。上层依赖下层提供的服务，同层文档之间存在接口关联。
15份共享PZXQ前缀的文档构成同一项目的子系统集群，文档间的接口关联是跨文档一致性校验的重点。
</div>
{arch_diagram}

<h3>1.2 文档规模总表</h3>
<table>
<thead><tr>
    <th>文档名称</th><th>系统层</th><th>ID前缀</th>
    <th>章节</th><th>表格</th><th>图片</th><th>约束</th><th>版本</th><th>需求ID</th>
</tr></thead>
<tbody>
{docs_rows}
<tr class="total">
    <td colspan="3">合计</td>
    <td class="num">{totals['sections']}</td>
    <td class="num">{totals['tables']}</td>
    <td class="num">{totals['images']}</td>
    <td class="num">{totals['constraints']}</td>
    <td class="num">{totals['versions']}</td>
    <td class="num">{totals['req_ids']}</td>
</tr>
</tbody>
</table>

<!-- ===== MinerU完整性 ===== -->
<h2>二、MinerU结构化JSON完整性评估</h2>
<div class="callout">
<strong>结论：MinerU结构化JSON存在7个已知问题，其中1个严重（图片提取失败），3个中等，3个低风险。
文字和表格提取基本完整，但图片、约束、版本号存在不同质量损失，需要在一致性校验前进行数据修复。</strong>
</div>
<table>
<thead><tr><th>严重度</th><th>问题</th><th>详细描述</th><th>影响</th><th>修复方案</th></tr></thead>
<tbody>
{mineru_html}
</tbody>
</table>

<!-- ===== 章节结构 ===== -->
<h2>三、章节结构分析</h2>
<h3>3.1 章节结构异常</h3>
{struct_html}
{sec_html}

<h3>3.2 章节编号体系差异</h3>
<div class="callout">
<strong>文档02使用扁平编号（1.x）vs 其他15份使用标准编号（3.x）</strong><br>
文档02的1.8 = 标准的3.2（能力需求），1.14 = 3.8（安全性），1.26 = 第4章（合格性规定）。
这种编号差异导致跨文档章节比对需要建立映射表，且文档02的追踪表引用标准章节号（如3.2、3.10）会产生ghost引用。
</div>

<!-- ===== ID体系 ===== -->
<h2>四、需求ID体系分析</h2>
<h3>4.1 ID层级结构示例</h3>
<table>
<thead><tr><th>文档</th><th>ID</th><th>层级分解</th><th>项目前缀</th><th>类别码</th><th>子系统码</th></tr></thead>
<tbody>
{hierarchy_html}
</tbody>
</table>

<h3>4.2 ID缺陷</h3>
{id_html}

<h3>4.3 跨文档共享ID</h3>
<div class="callout">
<strong>10个PZXQ ID在多份文档中共享</strong>，这些共享ID代表同一接口/功能在不同子系统SRS中的双向描述。
文档A的3.3.x（外部接口）中描述的接口，恰好对应文档B的3.2.x（功能需求）。
这种跨文档的"接口-功能"对应关系是跨文档上下文关联的天然锚点。
</div>
<table>
<thead><tr><th>文档A</th><th>文档B</th><th>共享ID</th><th>关联类型</th></tr></thead>
<tbody>
{cross_html}
</tbody>
</table>

<!-- ===== 表格 ===== -->
<h2>五、表格结构分析</h2>
<h3>5.1 合格性表（第4章）结构对比</h3>
<div class="callout">
<strong>文档01使用5列结构（含"测试类"列），其他15份使用4列结构（含"章节号"列）</strong>。
文档01缺少"章节号"列，使得ID到章节的映射只能依赖文本匹配。
</div>
<table>
<thead><tr><th>文档</th><th>章节</th><th>列数</th><th>行数</th><th>表头结构</th></tr></thead>
<tbody>
{qual_html}
</tbody>
</table>

<h3>5.2 追溯表（第5章）结构对比</h3>
<table>
<thead><tr><th>文档</th><th>章节</th><th>列数</th><th>行数</th><th>表头结构</th></tr></thead>
<tbody>
{trace_html}
</tbody>
</table>

<h3>5.3 Ghost引用（追踪表引用不存在的章节号）</h3>
<div class="callout">
<strong>10份文档的追踪表中引用了不存在的章节号</strong>，共计{len(seen)}个唯一ghost引用。
这些ghost引用可能是文档修订过程中章节号变更但追踪表未同步更新的结果。
</div>
{ghost_html}

<!-- ===== 约束 ===== -->
<h2>六、约束矛盾分析</h2>
<div class="callout">
<strong>{len(conflicts)}组同参数不同值的约束对</strong>。其中部分是真实矛盾（如网络适配器4vs40），
部分是"合理差异"（不同模块的差异化要求），需要语义角色理解来区分。
</div>
{conflict_html}

<!-- ===== 版本 ===== -->
<h2>七、版本号跨文档一致性</h2>
<div class="callout">
<strong>文档01在所有基础软件版本上都与群体不同</strong>（V8/V10/V11 vs V7.6/V4.0.2/V10.1），
与其独立的ZZSJHQZHFW前缀相互印证，属于合理的项目间差异。
但同一PZXQ项目内若出现不同版本，则更可能是真实矛盾。
</div>
{version_html}

<!-- ===== 用例表 ===== -->
<h2>八、用例描述表分析</h2>
<div class="callout">
<strong>472个用例描述表中的"动作约束"列未被提取为结构化约束</strong>。
用例表以键值对形式存储（非标准表格），导致约束提取器遗漏。
这是约束覆盖率的最大缺口（约74.6%的约束被遗漏）。
</div>
<table>
<thead><tr><th>文档</th><th>章节</th><th>用例名称</th><th>用例ID</th><th>行数</th><th>动作约束</th></tr></thead>
<tbody>
{usecase_html}
</tbody>
</table>

<!-- ===== 图片与解析质量 ===== -->
<h2>九、图片与解析质量</h2>
<h3>9.1 图片提取问题</h3>
<table>
<thead><tr><th>文档</th><th>图片引用数</th><th>唯一路径数</th><th>问题</th><th>根因</th></tr></thead>
<tbody>
{image_html}
</tbody>
</table>

<h3>9.2 解析质量问题</h3>
<table>
<thead><tr><th>文档</th><th>类型</th><th>参数/软件</th><th>错误值</th><th>原文</th></tr></thead>
<tbody>
{parse_html}
</tbody>
</table>

<!-- ===== 总结 ===== -->
<h2>十、总结：文档内 vs 文档间 不一致性</h2>
<div class="summary-box">
<h3 style="margin-top:0">文档内不一致性（单文档内部）</h3>
<ul>
<li><strong>语法层</strong>：章节编号异常（3.7缺失/安全保密顺序颠倒）、ID重复/拼写错误、表格caption缺失、ghost引用</li>
<li><strong>语义层</strong>：同参数不同值（如网络适配器4vs40）、同软件不同版本（文档01内部多个银河麒麟版本）</li>
<li><strong>逻辑层</strong>：当前数据集中尚未发现明确的逻辑可满足性矛盾</li>
</ul>
<h3>文档间不一致性（跨文档）</h3>
<ul>
<li><strong>语法层</strong>：编号体系差异（文档02的1.x vs 其他3.x）、合格性表/追踪表列结构差异（4列vs5列）</li>
<li><strong>语义层</strong>：跨文档版本冲突（达梦V7.6 vs V8、银河麒麟V4.0.2 vs V10）、跨文档同参数不同值</li>
<li><strong>关联层</strong>：10个跨文档共享ID定义的接口规格是否一致、文档A接口描述与文档B功能描述是否匹配</li>
</ul>
</div>

<div class="callout">
<strong>方法设计启示：</strong>
<ul style="margin:10px 0; padding-left:20px;">
<li>上下文关联需要支持<strong>文档内聚合</strong>（同ID在标题/合格性表/追踪表的多位置出现）和<strong>跨文档关联</strong>（共享PZXQ ID的接口-功能对应）两个层面</li>
<li>不一致性校验需要区分<strong>文档内矛盾</strong>（同参数同章节不同值）和<strong>文档间差异</strong>（不同项目前缀的版本差异是合理的）</li>
<li>MinerU JSON的图片提取失败(EMF格式)和约束遗漏(用例表)是当前数据质量的两大瓶颈，需在方法评测前修复</li>
</ul>
</div>

</div>
</body>
</html>'''
    
    output = Path('docs/srs_project/dataset_analysis_report.html')
    output.write_text(html)
    print(f'HTML报告已生成: {output}')
    print(f'文件大小: {output.stat().st_size / 1024:.1f} KB')

if __name__ == '__main__':
    generate_html()
