#!/usr/bin/env python3
"""
M7: 双LLM自动裁决 (Tier 1 drift候选分类)
==========================================
用户暂不参与 → 用双异族LLM替代人工裁决:
  - kimi-k2.6 (vision): 看真实图片 + 全上下文
  - GLM (wanqing, text): 看锚点结构 + 表格 (不看图,独立意见)

标签体系(4类):
  real_bug          — 真实文档不一致(图/表矛盾, 需求缺陷)
  benign_variation  — 合理差异(粒度/详略/视角)
  compiler_bug      — 比对引擎误报(两侧实际对应)
  extraction_error  — 提取错误(锚点解析问题)

一致 → 采纳; 分歧 → uncertain(待人工)
输出: data/gjb_438c/anchor_sc2/llm_adjudication.json
用法: python3 tools/m7_llm_adjudication.py [--limit N]
"""
import argparse
import base64
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(BASE / "tools"))
from m1_compare_engine import compile_usecase_table

T1_PATH = BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies.json"
ANCHOR_PATH = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
REALIGN_PATH = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/llm_adjudication.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
KIMI_MODEL = "kimi-k2.6"

GLM_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
GLM_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
GLM_MODEL = "ep-glsztk-1778496696841467392"

PROMPT = """你是军事软件需求文档(GJB 438C SRS)质量审查专家。审查以下"流程图vs用例描述表"的分歧, 判断其类别。

## 文档信息
- 文档: {doc} | 章节: {section}
- 用例名: {uc_name}
- 图: {image_caption}
- 表: {table_caption}

## 表格侧内容
{table_content}

## 图侧内容(节点与连接)
{diagram_content}
{image_section}

## 被审查的分歧
{evidence}

## 判断标准(四选一)
- real_bug: 图与表真实矛盾 — 内容/顺序/参与者/异常流确实对不上, 属于需求文档缺陷, 需求工程师应该修
- benign_variation: 合理差异 — 粒度不同(图粗表细)、视角不同(图是运行时/表是开发流程)、详略取舍, 不是缺陷
- compiler_bug: 比对引擎误报 — 两侧内容实际是对应的, 只是文字表述差异较大导致自动匹配没认出来
- extraction_error: 提取错误 — 锚点(VLSio XML解析)或图片内容本身有问题, 比对前提不成立

严格输出JSON:
{{"label": "real_bug|benign_variation|compiler_bug|extraction_error",
  "reason": "一句话理由",
  "confidence": "high|low"}}"""


def build_contexts():
    """预构建每对的上下文(表格内容+图结构+图路径)"""
    t1 = json.loads(T1_PATH.read_text())
    anchors = json.loads(ANCHOR_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())
    realigned = json.loads(REALIGN_PATH.read_text())

    anchor_idx = {}
    for doc_name, doc in anchors.items():
        for s in doc['structures']:
            key = (doc_name, s['embed_index'].split(':')[0])
            text_n = sum(1 for n in s['nodes'] if n['text'])
            if key not in anchor_idx or text_n > anchor_idx[key][0]:
                anchor_idx[key] = (text_n, s)
    anchor_idx = {k: v[1] for k, v in anchor_idx.items()}

    ctx = {}
    for pk, v in t1.items():
        if not isinstance(v, dict) or 'discrepancies' not in v:
            continue
        m = mapping.get(pk, {})
        ra = realigned.get(pk, {})
        if ra.get('status') not in ('realigned', 'same'):
            continue
        anchor = anchor_idx.get((m.get('doc', ''), ra.get('new_embed', '').split(':')[0]))
        X_T = compile_usecase_table(PAIR_DIR / pk / 'table.csv')
        if not anchor or not X_T:
            continue
        # 表格侧
        steps = '\n'.join(f"  {n['num']}. {n['text'][:60]}" for n in X_T['nodes']
                          if n['type'] == 'process')
        excs = '\n'.join(f"  {k}: {v2[:50]}" for k, v2 in X_T['exceptions'].items())
        table_content = f"主事件流步骤:\n{steps or '  (无)'}\n异常流:\n{excs or '  (无)'}\nActors: {', '.join(X_T['actors'])}"
        # 图侧
        nodes_str = '\n'.join(f"  [{n['type']}] {n['text'][:50]}"
                              for n in anchor['nodes'] if n['text'])
        nodes_map = {n['id']: n for n in anchor['nodes']}
        edges_str = '\n'.join(
            f"  {nodes_map[e['src']]['text'][:20]} → {nodes_map[e['dst']]['text'][:20]}"
            + (f" [{e['label']}]" if e.get('label') else '')
            for e in anchor['edges']
            if e['src'] in nodes_map and e['dst'] in nodes_map
            and (nodes_map[e['src']].get('text') or nodes_map[e['dst']].get('text')))
        diagram_content = f"节点:\n{nodes_str}\n边:\n{edges_str}"
        img_path = PAIR_DIR / pk / 'image.png'

        ctx[pk] = {
            'doc': v.get('doc', ''), 'section': m.get('section', ''),
            'uc_name': v.get('uc_name', ''),
            'image_caption': m.get('image_caption', ''),
            'table_caption': m.get('table_caption', ''),
            'table_content': table_content,
            'diagram_content': diagram_content,
            'img_path': str(img_path) if img_path.exists() else '',
            'mapping_status': ra.get('status', ''),
        }
    return t1, ctx


def call_kimi(task_prompt: str, img_path: str) -> dict:
    content = [{"type": "text", "text": task_prompt}]
    if img_path:
        b64 = base64.b64encode(open(img_path, 'rb').read()).decode()
        content.insert(0, {"type": "image_url",
                           "image_url": {"url": f"data:image/png;base64,{b64}"}})
    for _ in range(2):
        try:
            r = httpx.post(KIMI_URL, headers={
                "Authorization": f"Bearer {KIMI_KEY}", "Content-Type": "application/json"
            }, json={"model": KIMI_MODEL, "thinking": {"type": "disabled"},
                     "messages": [{"role": "user", "content": content}],
                     "max_tokens": 400, "temperature": 0.6,
                     "response_format": {"type": "json_object"}}, timeout=120)
            if r.status_code == 200:
                return parse_label(r.json()["choices"][0]["message"].get("content", ""))
        except Exception:
            time.sleep(3)
    return {'label': 'error', 'reason': 'call_failed', 'confidence': 'low'}


def call_glm(task_prompt: str) -> dict:
    for _ in range(2):
        try:
            r = httpx.post(GLM_URL, headers={
                "Authorization": f"Bearer {GLM_KEY}", "Content-Type": "application/json"
            }, json={"model": GLM_MODEL,
                     "messages": [{"role": "user",
                                   "content": task_prompt + "\n\n注意: 你看不到图片。请快速判断(思考限3步内), 直接输出JSON。"}],
                     "max_tokens": 6000, "temperature": 0.6}, timeout=240)
            if r.status_code == 200:
                return parse_label(r.json()["choices"][0]["message"].get("content", ''))
        except Exception:
            time.sleep(3)
    return {'label': 'error', 'reason': 'call_failed', 'confidence': 'low'}


def parse_label(text: str) -> dict:
    """解析LLM输出(容忍markdown围栏)"""
    try:
        m = re.search(r'\{[^{}]*\}', text.replace('\n', ' '), re.DOTALL)
        if m:
            d = json.loads(m.group(0))
            label = d.get('label', '')
            if label in ('real_bug', 'benign_variation', 'compiler_bug', 'extraction_error'):
                return {'label': label, 'reason': str(d.get('reason', ''))[:120],
                        'confidence': d.get('confidence', 'low')}
        # 宽松匹配
        for lb in ('real_bug', 'benign_variation', 'compiler_bug', 'extraction_error'):
            if lb in text:
                return {'label': lb, 'reason': text[:100], 'confidence': 'low'}
    except Exception:
        pass
    return {'label': 'parse_error', 'reason': text[:100], 'confidence': 'low'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()

    t1, ctx = build_contexts()
    tasks = []
    for pk, v in t1.items():
        if pk not in ctx or v.get('match_score', 0) <= 0.3:
            continue
        for di, d in enumerate(v['discrepancies']):
            tasks.append((f"{pk}_{di:02d}", pk, d))
    if args.limit:
        tasks = tasks[:args.limit]

    results = {}
    if OUT_PATH.exists():
        results = json.loads(OUT_PATH.read_text())
        print(f"断点续跑: 已有{len(results)}条")

    print(f"{'='*64}")
    print(f"M7: 双LLM裁决 ({len(tasks)}条分歧, kimi看图+GLM看结构)")
    print(f"{'='*64}")

    def run_one(item):
        tid, pk, d = item
        c = ctx[pk]
        prompt = PROMPT.format(
            doc=c['doc'], section=c['section'], uc_name=c['uc_name'],
            image_caption=c['image_caption'], table_caption=c['table_caption'],
            table_content=c['table_content'], diagram_content=c['diagram_content'],
            image_section="\n(图片见上)" if c['img_path'] else "\n(无图片)",
            evidence=d['evidence'])
        kimi_r = call_kimi(prompt, c['img_path'])
        glm_r = call_glm(prompt)
        return tid, {
            'pair': pk, 'dtype': d['dtype'], 'evidence': d['evidence'],
            'kimi': kimi_r, 'glm': glm_r,
            'final': kimi_r['label'] if kimi_r['label'] == glm_r['label'] else 'uncertain',
        }

    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, t): t for t in tasks}
        for fut in as_completed(futs):
            tid, res = fut.result()
            results[tid] = res
            done += 1
            if done % 20 == 0:
                OUT_PATH.write_text(json.dumps(results, ensure_ascii=False))
                print(f"  [{done}/{len(tasks)}] {time.time()-t0:.0f}s "
                      f"(一致率{sum(1 for r in results.values() if r['final']!='uncertain')/len(results):.0%})")

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1))

    # 统计
    from collections import Counter
    final = Counter(r['final'] for r in results.values())
    kimi_only = Counter(r['kimi']['label'] for r in results.values())
    glm_only = Counter(r['glm']['label'] for r in results.values())
    agree = sum(1 for r in results.values() if r['final'] != 'uncertain')

    print(f"\n  完成: {len(results)}条, 双模型一致率{agree/len(results):.0%}")
    print(f"\n  最终标签分布: {dict(final)}")
    print(f"  kimi标签分布: {dict(kimi_only)}")
    print(f"  GLM标签分布: {dict(glm_only)}")

    # 分歧类型×标签
    print(f"\n  分歧类型×最终标签:")
    cross = Counter((r['dtype'], r['final']) for r in results.values())
    for (dt, lb), c in sorted(cross.items()):
        print(f"    {dt:18s} × {lb:16s}: {c}")

    # 真实bug清单
    print(f"\n  real_bug清单(前10):")
    n = 0
    for tid, r in results.items():
        if r['final'] == 'real_bug' and n < 10:
            print(f"    [{tid}] [{r['dtype']}] {r['evidence'][:56]}")
            print(f"       kimi: {r['kimi']['reason'][:50]} | glm: {r['glm']['reason'][:50]}")
            n += 1
    print(f"\n  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
