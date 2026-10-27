#!/usr/bin/env python3
"""
M1-改进版: 基于内容匹配的Visio→pair_dataset映射
================================================
核心改进: 不用顺序映射(错误), 用内容匹配(table步骤 vs Visio节点文本)

策略:
  1. 从pair_dataset的table.csv提取主事件流步骤
  2. 对每个Visio结构提取有文本的节点
  3. 计算匹配度(字符重叠率>50%的节点比例)
  4. 选最佳匹配(每个pair匹配唯一的Visio, 不重复)

用法: python3 tools/sc2_visio_map.py
"""
import re
import json
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
VISIO_STRUCTURES_PATH = BASE / "data/gjb_438c/visio_extracted/visio_structures.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUTPUT_DIR = BASE / "data/gjb_438c/visio_extracted"


def extract_table_steps(table_csv_path: Path) -> list[str]:
    """从用例描述表提取主事件流步骤"""
    if not table_csv_path.exists():
        return []
    with open(table_csv_path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    steps = []
    for r in rows:
        for cell in r[:2]:  # Actor动作 + 系统动作
            if cell and len(cell.strip()) > 5:
                # 去掉编号前缀
                clean = re.sub(r'^\d+[\.．]\s*', '', cell.strip())
                if clean:
                    steps.append(clean)
    return steps


def extract_visio_texts(structure: dict) -> list[str]:
    """从Visio结构提取有意义的节点文本"""
    texts = []
    for node in structure.get('nodes', []):
        t = node.get('text', '').strip()
        if t and len(t) > 3:  # 过滤太短的
            texts.append(t)
    return texts


def score_match(visio_texts: list[str], table_steps: list[str]) -> float:
    """计算匹配度: Visio节点能匹配到表格步骤的比例"""
    if not visio_texts or not table_steps:
        return 0.0
    matched = 0
    for vt in visio_texts:
        vt_chars = set(vt)
        if not vt_chars:
            continue
        for ts in table_steps:
            ts_chars = set(ts)
            overlap = len(vt_chars & ts_chars) / len(vt_chars)
            if overlap > 0.5:
                matched += 1
                break
    return matched / len(visio_texts)


def main():
    print("=" * 60)
    print("M1-改进: 基于内容匹配的Visio→pair映射")
    print("=" * 60)

    # 加载Visio结构
    with open(VISIO_STRUCTURES_PATH, encoding="utf-8") as f:
        all_visio = json.load(f)

    # 加载pair_dataset
    pairs = []
    for d in sorted(PAIR_DIR.iterdir()):
        meta_p = d / "meta.json"
        if meta_p.exists():
            meta = json.loads(meta_p.read_text())
            meta['_dir'] = d.name
            # 提取table步骤
            meta['_table_steps'] = extract_table_steps(d / "table.csv")
            pairs.append(meta)

    print(f"pair_dataset样本: {len(pairs)}")

    # 内容匹配
    mapping = {}
    used_visio = set()  # 防止一个Visio被多个pair匹配

    for pair in pairs:
        doc_name = pair['doc']
        table_steps = pair['_table_steps']

        if doc_name not in all_visio:
            continue

        structures = all_visio[doc_name]['structures']

        best_score = 0
        best_struct = None

        for i, struct in enumerate(structures):
            embed_key = f"{doc_name}:{struct['embed_index']}"
            if embed_key in used_visio:
                continue

            visio_texts = extract_visio_texts(struct)
            score = score_match(visio_texts, table_steps)

            if score > best_score:
                best_score = score
                best_struct = struct

        if best_struct and best_score > 0.15:  # 最低阈值
            used_visio.add(f"{doc_name}:{best_struct['embed_index']}")

            visio_texts = extract_visio_texts(best_struct)
            visio_nodes = best_struct.get('nodes', [])
            visio_edges = best_struct.get('edges', [])

            # 统计各类节点
            node_types = {}
            for n in visio_nodes:
                nt = n.get('type', 'other')
                node_types[nt] = node_types.get(nt, 0) + 1

            mapping[pair['_dir']] = {
                'pair_id': pair['instance_id'],
                'doc': doc_name,
                'section': pair.get('section', ''),
                'image_caption': pair.get('image_caption', ''),
                'table_caption': pair.get('table_caption', ''),
                'visio_embed': best_struct['embed_index'],
                'match_score': round(best_score, 3),
                'table_steps_count': len(table_steps),
                'visio_text_nodes': len(visio_texts),
                'visio_total_nodes': len(visio_nodes),
                'visio_edges': len(visio_edges),
                'node_types': node_types,
                # 完整结构(用于后续一致性检测)
                'visio_structure': {
                    'nodes': visio_nodes,
                    'edges': visio_edges,
                },
                # 表格步骤(用于后续一致性检测)
                'table_steps': table_steps,
            }

    # 统计
    print(f"\n映射结果: {len(mapping)}/{len(pairs)}")

    scores = [m['match_score'] for m in mapping.values()]
    if scores:
        print(f"  匹配度: min={min(scores):.1%} max={max(scores):.1%} "
              f"avg={sum(scores)/len(scores):.1%}")

    high = sum(1 for s in scores if s > 0.5)
    medium = sum(1 for s in scores if 0.2 < s <= 0.5)
    low = sum(1 for s in scores if s <= 0.2)
    print(f"  高匹配(>50%): {high}")
    print(f"  中匹配(20-50%): {medium}")
    print(f"  低匹配(<20%): {low}")

    # 按文档统计
    print("\n按文档:")
    for doc_name in all_visio:
        doc_pairs = {k: v for k, v in mapping.items() if v['doc'] == doc_name}
        doc_structs = all_visio[doc_name]['structures']
        if doc_pairs:
            avg = sum(v['match_score'] for v in doc_pairs.values()) / len(doc_pairs)
            print(f"  {doc_name[:25]}: {len(doc_structs)}Visio → {len(doc_pairs)}pair "
                  f"(avg={avg:.1%})")

    # 保存
    output_path = OUTPUT_DIR / "sc2_visio_mapping_v2.json"
    output_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n保存: {output_path}")

    # 保存摘要(不含完整结构)
    summary = {}
    for k, v in mapping.items():
        summary[k] = {kk: vv for kk, vv in v.items()
                      if kk not in ('visio_structure', 'table_steps')}
    summary_path = OUTPUT_DIR / "sc2_visio_mapping_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"摘要: {summary_path}")

    # 详细展示几个高匹配样本
    print("\n=== 高匹配样本示例 ===")
    sorted_pairs = sorted(mapping.items(), key=lambda x: -x[1]['match_score'])
    for pair_key, m in sorted_pairs[:3]:
        print(f"\n  {pair_key} (score={m['match_score']:.1%}):")
        print(f"    doc: {m['doc'][:25]}")
        print(f"    section: {m['section']}")
        print(f"    visio: {m['visio_embed']} ({m['visio_text_nodes']}文本节点, "
              f"{m['visio_edges']}边)")
        print(f"    table: {m['table_steps_count']}步骤")
        # 显示几个匹配
        visio_texts = extract_visio_texts(m['visio_structure'])
        for vt in visio_texts[:3]:
            for ts in m['table_steps']:
                vt_chars, ts_chars = set(vt), set(ts)
                if vt_chars and len(vt_chars & ts_chars) / len(vt_chars) > 0.5:
                    print(f"    ✓ \"{vt[:35]}\" ↔ \"{ts[:35]}\"")
                    break


if __name__ == "__main__":
    main()
