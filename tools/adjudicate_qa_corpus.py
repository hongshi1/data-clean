#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA语料仲裁门（P1升级: oracle确证 + 图事实仲裁 双门）
=====================================================

定位: 合成流水线的最后一道确定性闸门（对应§九P1的修正版）
  注入器oracle确证标签 ≠ 零噪声(17号报告§4.4实测89条噪声)
  → 本工具用born-digital图事实独立复核每条QA的声明-标签一致性

对任意UML QA语料执行:
  1. 逐条抽取声明(问题+答案断言段, 剥离纠正文本)
  2. 图谓词检测器给出独立判定
  3. 判定与语料label比对 → 分歧项仲裁归因:
       label_noise_graph_supported : 语料标inconsistent但图事实支持声明 → 可改判
       detector_suspicious         : 语料标consistent但检测器触发 → 实体解析可疑, 需人工
       ambiguity                   : doc级同名实体歧义(embed限定可解除) → 不动
  4. --fix relabel: 改写label_noise项的label并备份 | --fix quarantine: 隔离到 *_quarantine.json

用法:
  python tools/adjudicate_qa_corpus.py corpus.json                # 只报告
  python tools/adjudicate_qa_corpus.py corpus.json --fix relabel  # 修复并写出
  python tools/adjudicate_qa_corpus.py corpus.json --embed        # RAG定位模式复核
"""
import argparse
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uml_detector_suite import GraphIndex, extract_claim, verify

BASE = Path(__file__).resolve().parent.parent


def adjudicate(corpus_path, embed_mode=False, fix=None, limit=0):
    corpus_path = Path(corpus_path)
    corpus = json.load(open(corpus_path, encoding="utf-8"))
    if limit:
        corpus = corpus[:limit]
    gidx = GraphIndex()
    t0 = time.time()
    flags, stats = [], Counter()
    fixed = []

    for i, qa in enumerate(corpus):
        claim = extract_claim(qa)
        embed = qa.get('evidence', {}).get('embed') if embed_mode else None
        inc, fired, stage = verify(qa, claim, gidx, embed)
        gold_inc = qa.get('label') == 'inconsistent'
        item = dict(qa)
        if inc == gold_inc:
            stats['agree'] += 1
            fixed.append(item)
            continue
        if gold_inc and not inc:
            # 语料标负例但图事实未触发 → 仲裁归因
            reason = 'ambiguity' if stage in ('no_entity', 'edge_unresolved', 'node_unresolved') else 'label_noise_graph_supported'
            # 图事实支持复核(dir_hat/impl/nodetype三种可复核形态)
            if reason == 'label_noise_graph_supported' and claim['kind'] in ('direction', 'impl', 'nodetype'):
                doc = gidx.doc_of(qa)
                k = claim['kind']
                if k in ('direction', 'relation') and claim['dir_hat'] and len(claim['ents']) >= 2:
                    x, _ = claim['dir_hat']
                    cands = gidx.find_all_edges(doc, claim['ents'][0], claim['ents'][1])
                    sup = any((gidx._match(x, {'text': ce.get('src_text', '')}) and gidx.edge_dir(ce) in ('fwd', 'both')) or
                              (gidx._match(x, {'text': ce.get('dst_text', '')}) and gidx.edge_dir(ce) in ('bwd', 'both'))
                              for ce, _ in cands)
                    reason = 'label_noise_graph_supported' if sup else 'unresolved_miss'
                elif k == 'impl' and len(claim['ents']) >= 2:
                    reason = 'label_noise_graph_supported' if gidx.has_directed(doc, claim['ents'][0], claim['ents'][1]) else 'unresolved_miss'
                elif k == 'nodetype':
                    ent = claim['ents'][0] if claim['ents'] else claim['subject']
                    nodes = []
                    for s in gidx.structures(doc):
                        nodes += [n for n in s['nodes'] if gidx._match(ent, n)]
                    reason = 'label_noise_graph_supported' if any(n.get('type') == claim['type_hat'] for n in nodes) else 'unresolved_miss'
            stats[reason] += 1
            flags.append({'idx': i, 'id': qa.get('id'), 'inject': qa.get('inject_type', ''),
                          'kind': claim['kind'], 'stage': stage, 'verdict': 'label_noise_graph_supported',
                          'reason': reason, 'fired': fired[:1]})
            if fix == 'relabel' and reason == 'label_noise_graph_supported':
                item['label'] = 'consistent'
                item['adjudicated'] = {'from': 'inconsistent', 'by': 'graph_facts',
                                       'reason': reason, 'at': 'adjudicate_qa_corpus'}
                item.pop('inject_type', None)
                item['source'] = qa.get('source', '').replace('negative', 'positive')
            fixed.append(item)
        else:
            # 语料标正例但检测器触发 → 检测器侧可疑(实体解析), 需人工, 不自动改
            stats['detector_suspicious'] += 1
            flags.append({'idx': i, 'id': qa.get('id'), 'inject': '',
                          'kind': claim['kind'], 'stage': stage,
                          'verdict': 'detector_suspicious', 'reason': 'fp_review_needed',
                          'fired': fired[:1]})
            fixed.append(item)

    n = len(corpus)
    print(f"仲裁门报告: {corpus_path.name}")
    print(f"  总条数 {n} | 一致 {stats['agree']} ({stats['agree']/max(n,1):.2%}) | 分歧 {sum(v for k2, v in stats.items() if k2 != 'agree')}")
    print(f"  分歧归因: { {k2: v for k2, v in stats.items() if k2 != 'agree'} }")
    for f in flags[:8]:
        print(f"    [{f['verdict']}/{f['reason']}] {f['id'][:40]} inject={f['inject']} kind={f['kind']}")
    print(f"  ({time.time()-t0:.0f}s)")

    out_dir = Path(corpus_path).parent
    stem = Path(corpus_path).stem
    report = {'corpus': str(corpus_path), 'n': n, 'stats': dict(stats), 'flags': flags[:500]}
    json.dump(report, open(out_dir / f"{stem}_adjudication.json", 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"  报告: {out_dir / (stem + '_adjudication.json')}")
    if fix == 'relabel':
        bak = out_dir / f"{stem}_pre_adjudication.json.bak"
        if not bak.exists():
            shutil.copy(corpus_path, bak)
        json.dump(fixed, open(out_dir / f"{stem}_adjudicated.json", 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        n_flip = sum(1 for f in flags if f['reason'] == 'label_noise_graph_supported')
        print(f"  修复: 改判{n_flip}条 → {out_dir / (stem + '_adjudicated.json')} (原文件备份{bak.name})")
    elif fix == 'quarantine':
        keep = [q for q in fixed if not q.get('adjudicated')]
        quar = [q for q in fixed if q.get('adjudicated')]
        json.dump(keep, open(out_dir / f"{stem}_clean.json", 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        json.dump(quar, open(out_dir / f"{stem}_quarantine.json", 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f"  隔离: 保留{len(keep)} / 隔离{len(quar)}")
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('corpus', help='QA语料json路径')
    ap.add_argument('--fix', choices=['relabel', 'quarantine'], default=None)
    ap.add_argument('--embed', action='store_true', help='RAG定位模式(用evidence.embed限定结构)')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    adjudicate(args.corpus, embed_mode=args.embed, fix=args.fix, limit=args.limit)
