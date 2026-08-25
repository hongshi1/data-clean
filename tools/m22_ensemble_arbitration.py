#!/usr/bin/env python3
"""
M22: 多模型集成仲裁 — 337条uncertain的自动化解决
=====================================================
第一轮(kimi+GLM)分歧模式: kimi宽松(225 benign) vs GLM严格(147 real/compiler)

五路投票设计(复用第一轮2票 + 新增3票):
  票1 kimi-vision    (第一轮, 已有)
  票2 GLM-standard   (第一轮, 已有)
  票3 kimi-enhanced  (图+粒度判定规则+正文上下文 —— 证据升级)
  票4 GLM-check      (对应性检查框架: "图中哪个节点对应它?" —— 更简单的问题)
  票5 kimi-text     (纯文本无图视角 —— 视觉独立性)

多数(≥3/5)→裁决; 否则保持uncertain
sc3惯例问题: 对sc3的条目附加惯例前置问题(GJB接口图是否惯例只画子集)

输出: data/gjb_438c/anchor_v2/ensemble_arbitration.json
用法: python3 tools/m22_ensemble_arbitration.py [--workers 6] [--limit N]
"""
import argparse
import base64
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))

ADJ_SC2 = BASE / "data/gjb_438c/anchor_sc2/llm_adjudication.json"
ADJ_SCENE = BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json"
T1_SC2 = BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies_v2.json"
T1_SCENE = BASE / "data/gjb_438c/anchor_v2/scene_tier1.json"
CENSUS = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
ANCHOR_SC2 = BASE / "data/gjb_438c/anchor_sc2/anchors.json"
REALIGN = BASE / "data/gjb_438c/anchor_sc2/realigned_mapping.json"
PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
OUT = BASE / "data/gjb_438c/anchor_v2/ensemble_arbitration.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
KIMI_MODEL = "kimi-k2.6"
GLM_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
GLM_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
GLM_MODEL = "ep-glsztk-1778496696841467392"

VALID = ('real_bug', 'benign_variation', 'compiler_bug')

RULES = """判定细则(按优先级):
1. 若图中存在与该项语义对应的元素(表述不同但同一事物) → compiler_bug(匹配失败)
2. 若图按文档惯例本就不画此类内容(如: 用例图的图不画异常流分支/表格是完整registry而图只画主要接口/流程图只画核心路径) → benign_variation
3. 若文档声称图覆盖该项所属类别(如"图描述全部用例"/表格明确要求图示)而图确实缺失 → real_bug
4. 拿不准时倾向 benign_variation(差异不构成缺陷的举证责任在"报bug"方)"""

V3_PROMPT = """你是GJB 438C军事软件需求文档审查专家。判断以下分歧。

{scene_ctx}

## 表格侧(被审查项)
{table_ctx}

## 图侧节点(来自Visio源, 逐字可信)
{diag_nodes}

## 正文上下文(该功能在正文中的描述)
{body_text}
{image_note}

## 被审查分歧
{evidence}

{rules}

严格输出JSON: {{"label": "real_bug|benign_variation|compiler_bug", "reason": "一句话", "confidence": "high|low"}}"""

V4_PROMPT = """你是文档一致性审核员。回答两个具体问题:

{scene_ctx}

## 任务A(对应性检查)
表格项「{item}」在下面图节点清单中是否有对应元素?
图节点: {diag_nodes}
若有, 指出哪个节点; 若无, 说"无"。

## 任务B(惯例判断)
图不画此类内容是否是GJB文档惯例?(如接口图只画主要接口/流程图不画异常分支是惯例)
{evidence}

综合A和B输出JSON:
{{"corresponds": "对应节点文字或无",
  "conventional_omission": true或false,
  "label": "real_bug(真缺失且非惯例)|benign_variation(惯例性省略或合理差异)|compiler_bug(有对应但没匹配上)",
  "reason": "一句话"}}"""

V5_PROMPT = V3_PROMPT  # 同结构但无图(纯文本视角)


def parse_label(text):
    try:
        m = re.search(r'\{[^{}]*\}', text.replace('\n', ' '), re.DOTALL)
        if m:
            d = json.loads(m.group(0))
            label = d.get('label', '')
            if label in VALID:
                return label
        for lb in VALID:
            if lb in text:
                return lb
    except Exception:
        pass
    return 'parse_error'


def call_kimi(prompt, img_path=None, temperature=0.6):
    content = [{"type": "text", "text": prompt}]
    if img_path and Path(img_path).exists():
        b64 = base64.b64encode(Path(img_path).read_bytes()).decode()
        content.insert(0, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    for _ in range(2):
        try:
            r = httpx.post(KIMI_URL, headers={
                'Authorization': f'Bearer {KIMI_KEY}', 'Content-Type': 'application/json'
            }, json={'model': KIMI_MODEL, 'thinking': {'type': 'disabled'},
                     'messages': [{'role': 'user', 'content': content}],
                     'max_tokens': 400, 'temperature': temperature,
                     'response_format': {'type': 'json_object'}}, timeout=120)
            if r.status_code == 200:
                return parse_label(r.json()['choices'][0]['message'].get('content', ''))
        except Exception:
            time.sleep(3)
    return 'error'


def call_glm(prompt):
    for _ in range(2):
        try:
            r = httpx.post(GLM_URL, headers={
                'Authorization': f'Bearer {GLM_KEY}', 'Content-Type': 'application/json'
            }, json={'model': GLM_MODEL,
                     'messages': [{'role': 'user', 'content': prompt + "\n\n注意: 你看不到图片。快速判断(思考限3步), 直接输出JSON。"}],
                     'max_tokens': 6000, 'temperature': 0.6}, timeout=240)
            if r.status_code == 200:
                return parse_label(r.json()['choices'][0]['message'].get('content', ''))
        except Exception:
            time.sleep(3)
    return 'error'


def build_contexts():
    """预构建每对的上下文(图节点/正文/图路径)"""
    ctx = {}
    # sc2
    realigned = json.loads(REALIGN.read_text())
    t1_2 = json.loads(T1_SC2.read_text())
    idx_sc2 = {}
    anchors2 = json.loads(ANCHOR_SC2.read_text())
    for doc, d in anchors2.items():
        for s in d['structures']:
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s['nodes'] if n['text'])
            if key not in idx_sc2 or tn > idx_sc2[key][0]:
                idx_sc2[key] = (tn, s)
    for pk, v in t1_2.items():
        ra = realigned.get(pk, {})
        if ra.get('status') not in ('realigned', 'same'):
            continue
        entry2 = idx_sc2.get((v.get('doc', ''), ra.get('new_embed', '').split(':')[0]))
        anchor = entry2[1] if isinstance(entry2, tuple) else entry2
        if not anchor:
            continue
        pd = PAIR_ROOT / 'sc2_flowchart_usecase' / pk
        body = (pd / 'text.txt').read_text(encoding='utf-8')[:400] if (pd / 'text.txt').exists() else ''
        ctx[pk] = {
            'anchor': anchor, 'body': body,
            'img': str(pd / 'image.png') if (pd / 'image.png').exists() else '',
            'scene': 'sc2_flowchart_usecase',
        }
    # 多场景
    census = json.loads(CENSUS.read_text())
    anchors_v2 = json.loads(ANCHOR_V2.read_text())
    idx_v2 = {}
    for doc, d in anchors_v2.items():
        for s in d['structures']:
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s['nodes'] if n['text'])
            if key not in idx_v2 or tn > idx_v2[key][0]:
                idx_v2[key] = (tn, s)
    for pk, c in census.items():
        if c.get('status') != 'anchored':
            continue
        entry = idx_v2.get((c.get('doc', ''), c.get('new_embed', '').split(':')[0]))
        anchor = entry[1] if isinstance(entry, tuple) else entry
        if anchor is None:
            continue
        scene = c.get('scene', '')
        pd = PAIR_ROOT / scene / pk
        body = (pd / 'text.txt').read_text(encoding='utf-8')[:400] if (pd / 'text.txt').exists() else ''
        ctx[pk] = {
            'anchor': anchor, 'body': body,
            'img': str(pd / 'image.png') if (pd / 'image.png').exists() else '',
            'scene': scene,
        }
    return ctx


SCENE_NOTES = {
    'sc2_flowchart_usecase': '流程图 vs 用例描述表(主事件流/异常流/Actors)',
    'sc1_usecase_capability': '用例图 vs 能力需求表(表格是全部能力的registry)',
    'sc3_interface_interface': '接口图 vs 接口需求表(表格是全部接口的registry, 图通常只画主要接口——GJB惯例待判断)',
    'sc4_flowchart_capability': '流程图 vs 能力需求表(表格是全部能力, 图画某一能力流程)',
    'sc5_function_capability': '功能结构图 vs 子功能表',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    # 收集uncertain项
    items = []
    for adj_path, source in [(ADJ_SC2, 'M7'), (ADJ_SCENE, 'M17')]:
        adj = json.loads(adj_path.read_text())
        for tid, r in adj.items():
            if r.get('final') == 'uncertain':
                items.append({'tid': tid, 'pair': r['pair'], 'evidence': r['evidence'],
                              'dtype': r.get('dtype', ''), 'source': source,
                              'vote1': r['kimi']['label'], 'vote2': r['glm']['label']})
    if args.limit:
        items = items[:args.limit]

    print(f"{'='*64}")
    print(f"M22: 多模型集成仲裁 ({len(items)}条uncertain, 5路投票)")
    print(f"{'='*64}")

    ctx = build_contexts()
    results = json.loads(OUT.read_text()) if OUT.exists() else {}

    def run_one(it):
        pk = it['pair']
        c = ctx.get(pk)
        if not c:
            return it['tid'], {**it, 'final': 'no_context'}
        anchor = c['anchor']
        node_strs = [f"- [{n['type']}] {n['text'][:40]}" for n in anchor['nodes'] if n['text']]
        diag_nodes = '\n'.join(node_strs[:22])
        scene_note = SCENE_NOTES.get(c['scene'], '')
        scene_ctx = f"场景: {scene_note}\n图类型节点清单见下。"
        item_text = it['evidence'].split('「')[1].split('」')[0] if '「' in it['evidence'] else it['evidence'][:30]

        # 票3: kimi-enhanced(图+规则+正文)
        p3 = V3_PROMPT.format(scene_ctx=scene_ctx, table_ctx=it['evidence'],
                              diag_nodes=diag_nodes, body_text=c['body'] or '(无正文)',
                              image_note="\n(图片见上)", evidence=it['evidence'], rules=RULES)
        v3 = call_kimi(p3, c['img'])
        # 票4: GLM对应性检查
        p4 = V4_PROMPT.format(scene_ctx=scene_ctx, item=item_text[:40],
                              diag_nodes=diag_nodes[:600], evidence=it['evidence'])
        v4 = call_glm(p4)
        # 票5: kimi纯文本
        p5 = V5_PROMPT.format(scene_ctx=scene_ctx, table_ctx=it['evidence'],
                              diag_nodes=diag_nodes, body_text=c['body'] or '(无正文)',
                              image_note="", evidence=it['evidence'], rules=RULES)
        v5 = call_kimi(p5)

        votes = [it['vote1'], it['vote2'], v3, v4, v5]
        votes_valid = [v for v in votes if v in VALID]
        cnt = Counter(votes_valid)
        winner, top = cnt.most_common(1)[0] if cnt else (None, 0)
        final = winner if top >= 3 else 'uncertain'
        return it['tid'], {**{k: v for k, v in it.items() if k != 'anchor'},
                           'votes': votes, 'final': final,
                           'vote_dist': dict(cnt)}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(run_one, it) for it in items if it['tid'] not in results]
        done = 0
        for fut in as_completed(futs):
            tid, r = fut.result()
            results[tid] = r
            done += 1
            if done % 20 == 0:
                OUT.write_text(json.dumps(results, ensure_ascii=False))
                print(f"  [{done}/{len(items)}] {time.time()-t0:.0f}s")
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))

    # ── 汇总 ──
    ok = [r for r in results.values() if 'votes' in r]
    resolved = [r for r in ok if r['final'] in VALID]
    still = [r for r in ok if r['final'] == 'uncertain']
    print(f"\n{'='*64}")
    print(f"集成仲裁结果 ({len(ok)}条处理)")
    print(f"{'='*64}")
    print(f"  解决(≥3/5多数): {len(resolved)} ({len(resolved)/max(1,len(ok)):.0%})")
    print(f"  仍不确定: {len(still)}")
    print(f"\n  解决后的标签分布: {dict(Counter(r['final'] for r in resolved))}")

    # 与第一轮的变化
    print(f"\n  按来源:")
    for src in ('M7', 'M17'):
        sub = [r for r in ok if r.get('source') == src]
        res = sum(1 for r in sub if r['final'] in VALID)
        print(f"    {src}: {res}/{len(sub)} 解决")

    # 投票一致性分析
    full_agree = sum(1 for r in ok if len(set(v for v in r['votes'] if v in VALID)) == 1)
    print(f"\n  5票全一致: {full_agree}/{len(ok)}")
    print(f"  输出: {OUT}")


if __name__ == '__main__':
    main()
