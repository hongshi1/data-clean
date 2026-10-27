#!/usr/bin/env python3
"""
M10: 批量补充pair_dataset的Visio锚点结构
==========================================
把修复后的锚点解析结果(M0)写进每个pair文件夹:

  pair_dataset/<scene>/<pair_id>/
    ├── image.png          (原有)
    ├── table.csv          (原有)
    ├── text.txt           (原有)
    ├── meta.json          (更新: 增加anchor_*字段)
    └── visio_anchor.json  (新增: 修复后的锚点结构)

映射来源(两级可信度):
  sc2: realigned_mapping.json (VLM桥验证, 高可信)
  其他场景: all_scene_visio_mapping.json (关键词映射, 低可信 —
           sc2的经验是这种映射仅约1/3正确, 用confidence字段标注)

用法: python3 tools/m10_batch_anchor_supplement.py
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
ANCHOR_SC2 = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
ANCHOR_ALL = BASE / "data/gjb_438c/anchor_all/anchors.json"
REALIGN = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
SCENE_MAP = BASE / "data/gjb_438c/visio_extracted/all_scene_visio_mapping.json"


def build_anchor_index(anchors: dict) -> dict:
    """(doc, embed) → 最佳结构(多页取文本最多)"""
    idx = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            key = (doc_name, s['embed_index'].split(':')[0])
            text_n = sum(1 for n in s['nodes'] if n['text'])
            if key not in idx or text_n > idx[key][0]:
                idx[key] = (text_n, s)
    return {k: v[1] for k, v in idx.items()}


def main():
    a_sc2 = json.loads(ANCHOR_SC2.read_text())
    a_all = json.loads(ANCHOR_ALL.read_text())
    realigned = json.loads(REALIGN.read_text())
    scene_map = json.loads(SCENE_MAP.read_text())

    idx_sc2 = build_anchor_index(a_sc2)
    idx_all = build_anchor_index(a_all)

    stats = {'sc2_high': 0, 'sc2_unanchored': 0, 'other_linked': 0,
             'other_no_match': 0, 'missing_dir': 0}

    for scene, pairs in scene_map.items():
        for pk, m in pairs.items():
            pair_dir = PAIR_ROOT / scene / pk
            if not pair_dir.exists():
                stats['missing_dir'] += 1
                continue

            doc = m.get('doc', '')
            embed = m.get('visio_embed', '')

            if scene == 'sc2_flowchart_usecase':
                # 高可信路径: VLM桥重对齐
                ra = realigned.get(pk, {})
                if ra.get('status') in ('realigned', 'same'):
                    embed_new = ra.get('new_embed', '').split(':')[0]
                    anchor = idx_sc2.get((doc, embed_new)) or idx_all.get((doc, embed_new))
                    confidence = 'high' if ra.get('align_score', 0) >= 0.75 else \
                                 ('medium' if ra.get('align_score', 0) >= 0.5 else 'low')
                elif ra.get('status') == 'unanchored':
                    stats['sc2_unanchored'] += 1
                    anchor, confidence = None, 'none'
                else:
                    anchor = idx_sc2.get((doc, embed)) or idx_all.get((doc, embed))
                    confidence = 'medium'
                if anchor:
                    stats['sc2_high'] += 1
            else:
                # 其他场景: 关键词映射(低可信 — sc2经验: ~1/3正确)
                anchor = idx_all.get((doc, embed))
                confidence = 'low' if anchor else 'none'
                if anchor:
                    stats['other_linked'] += 1
                else:
                    stats['other_no_match'] += 1

            # 写visio_anchor.json
            if anchor:
                out = {
                    'pair_id': pk,
                    'scene': scene,
                    'doc': doc,
                    'embed_index': anchor['embed_index'],
                    'mapping_confidence': confidence,
                    'mapping_source': 'vlm_bridge_realigned' if scene == 'sc2_flowchart_usecase' else 'keyword_mapping',
                    'page': anchor['page'],
                    'nodes': anchor['nodes'],
                    'edges': anchor['edges'],
                    'meta': anchor.get('meta', {}),
                    'extraction': {
                        'tool': 'm0_anchor_extract (Cell坐标/子Shape文本合并/Connect边重建+几何恢复)',
                        'known_limits': [
                            '未粘合连线仅几何恢复(SNAP_TH=0.35in)',
                            '嵌套组内坐标为父局部系(未变换)',
                            '边标签依赖连接线Shape自身文本'
                        ],
                    },
                }
                (pair_dir / 'visio_anchor.json').write_text(
                    json.dumps(out, ensure_ascii=False, indent=1))

            # 更新meta.json
            meta_path = pair_dir / 'meta.json'
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                meta['has_visio_anchor'] = anchor is not None
                meta['anchor_mapping_confidence'] = confidence
                meta['anchor_embed'] = anchor['embed_index'] if anchor else None
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    # 汇总
    print(f"{'='*64}")
    print("M10: pair_dataset批量补充Visio锚点")
    print(f"{'='*64}")
    print(f"  sc2(高可信VLM桥映射): {stats['sc2_high']}对补充, {stats['sc2_unanchored']}无锚")
    print(f"  其他场景(关键词映射,低可信): {stats['other_linked']}对补充, {stats['other_no_match']}未匹配")
    print(f"  缺目录: {stats['missing_dir']}")

    # 验证: 抽查文件
    n_written = sum(1 for p in PAIR_ROOT.glob('*/**/visio_anchor.json'))
    print(f"\n  实际写入visio_anchor.json: {n_written}个")
    sample = sorted(PAIR_ROOT.glob('*/**/visio_anchor.json'))[:2]
    for s in sample:
        d = json.loads(s.read_text())
        print(f"  示例 {s.parent.name}: {len(d['nodes'])}节点 {len(d['edges'])}边 "
              f"confidence={d['mapping_confidence']} doc={d['doc'][:16]}")


if __name__ == "__main__":
    main()
