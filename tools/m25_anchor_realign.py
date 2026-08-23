#!/usr/bin/env python3
"""
M2.5: 锚点-pair重对齐 (跨通道实体对齐)
=======================================
旧映射(sc2_visio_mapping_v2)按关键词挑选Visio嵌入 → 系统性错位
(如 2_007"用户登录流程图"被配到"生命周期监控"的Visio)

修复: VLM提取(M2)读的是pair的真实image.png → 用它做桥,
在同一文档的全部锚点结构中找节点文本重叠最高的锚点 = 正确对齐。

对齐分数低的pair → 该图无Visio源(截图) → 标记为unanchored。

输出: data/gjb_438c/anchor_sc2/realigned_mapping.json
用法: python3 tools/m25_anchor_realign.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import text_match_score

ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
VLM_PATH = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"

ALIGN_TH = 0.4   # 对齐分数阈值(低于→unanchored)


def main():
    anchors = json.loads(ANCHOR_PATH.read_text())
    vlm = json.loads(VLM_PATH.read_text())
    old_mapping = json.loads(MAPPING_PATH.read_text())

    # 文档 → [锚点结构]
    doc_anchors = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            text_nodes = [n for n in s['nodes']
                          if n['text'].strip() and n['type'] not in ('start', 'end')]
            if len(text_nodes) >= 2:
                doc_anchors.setdefault(doc_name, []).append((s, text_nodes))

    results = {}
    n_changed = n_same = n_unanchored = 0

    for pk in sorted(old_mapping.keys()):
        m = old_mapping[pk]
        v = vlm.get(pk)
        if not v or 'error' in v or not v.get('nodes'):
            results[pk] = {'status': 'vlm_pending', 'old_embed': m.get('visio_embed', '')}
            continue

        vlm_nodes = [n for n in v['nodes'] if n.get('text', '').strip()]
        doc = m['doc']

        # 每个锚点: 与VLM节点的双向匹配率(贪心)
        best = None
        for s, text_nodes in doc_anchors.get(doc, []):
            pairs = []
            for vn in vlm_nodes:
                for an in text_nodes:
                    sc = text_match_score(vn['text'], an['text'])
                    if sc >= 0.5:
                        pairs.append((sc, vn['id'], an['id']))
            pairs.sort(key=lambda x: -x[0])
            used_v, used_a = set(), set()
            for sc, vid, aid in pairs:
                if vid not in used_v and aid not in used_a:
                    used_v.add(vid)
                    used_a.add(aid)
            n_match = len(used_a)
            # 对齐分数 = 匹配数 / max(两侧节点数)
            score = n_match / max(len(vlm_nodes), len(text_nodes))
            if best is None or score > best['score']:
                best = {'score': score, 'embed': s['embed_index'],
                        'n_match': n_match, 'n_vlm': len(vlm_nodes),
                        'n_anchor': len(text_nodes)}

        old_embed = m.get('visio_embed', '')
        if best is None or best['score'] < ALIGN_TH:
            status = 'unanchored'
            n_unanchored += 1
        elif best['embed'].split(':')[0] != old_embed:
            status = 'realigned'
            n_changed += 1
        else:
            status = 'same'
            n_same += 1

        results[pk] = {
            'status': status,
            'old_embed': old_embed,
            'new_embed': best['embed'] if best else '',
            'align_score': round(best['score'], 3) if best else 0,
            'n_match': best['n_match'] if best else 0,
            'n_vlm_nodes': best['n_vlm'] if best else 0,
            'n_anchor_nodes': best['n_anchor'] if best else 0,
            'doc': doc,
            'match_score_old': m.get('match_score', 0),
        }

    done = [r for r in results.values() if r['status'] != 'vlm_pending']
    print(f"{'='*64}")
    print(f"M2.5: 锚点重对齐 (VLM桥, 已完成{len(done)}/{len(results)}对)")
    print(f"{'='*64}")
    for st, label in [('same', '原对齐正确'), ('realigned', '重对齐(修复错位)'),
                      ('unanchored', '无Visio源(unanchored)')]:
        n = sum(1 for r in done if r['status'] == st)
        if n:
            print(f"  {label:24s}: {n}")
    # 修复明细
    if n_changed:
        print(f"\n  重对齐明细(前12):")
        for pk, r in results.items():
            if r['status'] == 'realigned':
                print(f"    {pk}: score={r.get('align_score')} "
                      f"match {r.get('n_match')}/{r.get('n_vlm_nodes')}↔{r.get('n_anchor_nodes')} "
                      f"({r.get('old_embed','')[:22]} → {r.get('new_embed','')[:22]})")

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"\n  输出: {OUT_PATH}")

    # 旧映射质量: 有多少对被VLM桥证实/证伪
    if done:
        acc = n_same / len(done)
        print(f"\n  旧映射正确率: {acc:.1%} (被VLM桥证实{n_same}, 证伪{n_changed}, "
              f"无源{n_unanchored})")


if __name__ == "__main__":
    main()
