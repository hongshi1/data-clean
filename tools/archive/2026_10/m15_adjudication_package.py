#!/usr/bin/env python3
"""
M1.5: Tier 1 人工裁决包生成器
================================
把376条drift候选整理成分层抽样的人工裁决任务包。

裁决标签体系(4类):
  real_bug          — 真实文档不一致(图/表矛盾)
  benign_variation  — 合理差异(粒度/详略/同义)
  compiler_bug      — κ_T编译器/比对引擎的缺陷(误报)
  extraction_error  — 锚点提取错误(Visio解析问题)

输出:
  data/gjb_438c/anchor_sc2/adjudication/
  ├── adjudication_tasks.json   (机器可读)
  └── adjudication_tasks.md     (人工快速审阅)

用法: python3 tools/m15_adjudication_package.py [--sample 120]
"""
import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
T1_PATH = BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT_DIR = BASE / "data/gjb_438c/anchor_sc2/adjudication"

# 分歧类型的裁决优先级(信息量排序)
PRIORITY = {
    'ORDER_CONFLICT': 1,   # 方向矛盾 — 最强信号
    'UC_NAME_MISMATCH': 2, # UC名不匹配
    'EXC_MISSING': 3,      # 异常流缺失
    'STEP_MISSING': 4,     # 步骤缺失
    'ACTOR_MISSING': 5,    # 参与者缺失
    'DIAGRAM_EXTRA': 6,    # 图多余节点
}


def build_tasks(sample_n: int):
    results = json.loads(T1_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())

    tasks = []
    for pk, v in results.items():
        if not isinstance(v, dict) or 'discrepancies' not in v:
            continue
        if v.get('match_score', 0) <= 0.3:  # 低置信对不进裁决
            continue
        m = mapping.get(pk, {})
        pair_dir = PAIR_DIR / m.get('pair_dir', pk)

        # 读取表格全文(裁决上下文)
        table_text = ''
        if (pair_dir / 'table.csv').exists():
            table_text = (pair_dir / 'table.csv').read_text(encoding='utf-8')[:800]

        for di, d in enumerate(v['discrepancies']):
            tasks.append({
                'task_id': f"{pk}_{di:02d}",
                'pair_key': pk,
                'doc': v.get('doc', ''),
                'section': m.get('section', ''),
                'image_caption': m.get('image_caption', ''),
                'table_caption': m.get('table_caption', ''),
                'uc_name': v.get('uc_name', ''),
                'diagram_mode': v.get('diagram_mode', ''),
                'match_score': v.get('match_score', 0),
                'n_table_steps': v.get('n_table_steps', 0),
                'n_diag_nodes': v.get('n_diag_nodes', 0),
                'n_matched': v.get('n_matched', 0),
                'dtype': d['dtype'],
                'etype': d['etype'],
                'evidence': d['evidence'],
                'table_side': d.get('table_side'),
                'diag_side': d.get('diag_side'),
                'priority': PRIORITY.get(d['dtype'], 9),
                'label': '',          # 人工填写
                'annotator_notes': '',
            })

    # 分层抽样: 按类型 × 匹配度分层, 优先级排序
    by_type = defaultdict(list)
    for t in tasks:
        by_type[t['dtype']].append(t)

    sampled = []
    random.seed(42)
    for dt, items in sorted(by_type.items(), key=lambda x: PRIORITY.get(x[0], 9)):
        items.sort(key=lambda t: (t['priority'], -t['match_score']))
        # 高优先类型全收, 低优先类型抽样
        if dt in ('ORDER_CONFLICT', 'UC_NAME_MISMATCH'):
            sampled.extend(items)
        else:
            take = max(8, min(len(items), sample_n // len(by_type)))
            # 前2/3按优先级取, 后1/3随机(覆盖面)
            head = items[:take * 2 // 3]
            tail = random.sample(items[len(head):] or [], min(take - len(head), len(items) - len(head))) if len(items) > len(head) else []
            sampled.extend(head + tail)

    sampled.sort(key=lambda t: (t['priority'], -t['match_score']))
    return sampled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=120)
    args = ap.parse_args()

    tasks = build_tasks(args.sample)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    out_json = OUT_DIR / 'adjudication_tasks.json'
    out_json.write_text(json.dumps(tasks, ensure_ascii=False, indent=1))

    # Markdown(人工审阅版)
    lines = [
        "# Tier 1 Drift候选人工裁决包",
        f"\n> 共{len(tasks)}条 (按类型×优先级分层抽样, seed=42)",
        "\n## 裁决标签体系",
        "- `real_bug` — 真实文档不一致(图/表矛盾)",
        "- `benign_variation` — 合理差异(粒度/详略/同义改写)",
        "- `compiler_bug` — 比对引擎误报(匹配/编译缺陷)",
        "- `extraction_error` — 锚点提取错误(Visio解析问题)",
        "\n---\n",
    ]
    cur_type = None
    for t in tasks:
        if t['dtype'] != cur_type:
            cur_type = t['dtype']
            lines.append(f"\n## {cur_type} ({sum(1 for x in tasks if x['dtype']==cur_type)}条)\n")
        lines.append(f"### {t['task_id']} [{t['dtype']}] {t['uc_name'][:20]}")
        lines.append(f"- 位置: {t['doc'][:24]} {t['section']} | {t['image_caption'][:26]} vs {t['table_caption'][:26]}")
        lines.append(f"- 规模: 表步骤{t['n_table_steps']} ↔ 图节点{t['n_diag_nodes']} 已配{t['n_matched']} (匹配度{t['match_score']})")
        lines.append(f"- 证据: {t['evidence']}")
        if t.get('table_side'):
            lines.append(f"- 表侧: `{json.dumps(t['table_side'], ensure_ascii=False)[:120]}`")
        if t.get('diag_side'):
            lines.append(f"- 图侧: `{json.dumps(t['diag_side'], ensure_ascii=False)[:120]}`")
        lines.append("- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error")
        lines.append("")

    out_md = OUT_DIR / 'adjudication_tasks.md'
    out_md.write_text('\n'.join(lines), encoding='utf-8')

    # 统计
    print(f"{'='*64}")
    print("M1.5: 裁决包生成")
    print(f"{'='*64}")
    tc = Counter(t['dtype'] for t in tasks)
    for dt, c in tc.most_common():
        print(f"  {dt:18s}: {c}")
    print(f"\n  合计: {len(tasks)}条")
    print(f"  输出: {out_json}")
    print(f"        {out_md}")
    print(f"\n  预计裁决时间: {len(tasks)*1.5:.0f}分钟 (每条约1.5分钟)")


if __name__ == "__main__":
    main()
