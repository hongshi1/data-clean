#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM分支声明抽取实验: 模式抽取 vs GLM抽取（100样本）
=====================================================

目的: 声明抽取的自然语言泛化能力评估（当前模式抽取是模板语法敏感的）
协议:
  1. 分层抽样100条UML QA（负例覆盖12注入族+正例）
  2. GLM抽取声明: 输入question+答案断言段（剥离「（实际：…）」） → 结构化claim JSON
  3. 对比: 声明级一致率（kind/实体/关系/方向） + 下游检测一致率（verify()喂LLM声明 vs 模式声明）
  4. 报告: LLM-claim检测F1 vs 模式-claim检测F1

用法: python tools/llm_claim_extraction_test.py [--n 100] [--workers 6]
输出: data/gjb_438c/anchor_v3/llm_claim_extraction.json
"""
import argparse
import json
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_config import KIMI_KEY
from uml_detector_suite import (GraphIndex, extract_claim, strip_correction, verify)

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / "data/gjb_438c/anchor_v3/uml_qa_full.json"
OUT = BASE / "data/gjb_438c/anchor_v3/llm_claim_extraction.json"
WQ_URL = "https://api.moonshot.cn/v1/chat/completions"
MODEL = "kimi-k2.6"

CLAIM_KINDS = "relation|direction|nav|dep|impl|nodetype|label|cycle|lifecycle"

PROMPT = """你是需求文档一致性检测系统的声明抽取器。给定一个关于UML图的问答（问题+答案的断言部分），抽取其中关于图的**声明**（claim），输出严格JSON。

声明种类kind：
- relation: 询问/断言两实体间是什么关系（关联/依赖/包含/继承/聚合/组合/实现/有向）
- direction: 询问/断言关系方向或箭头指向
- nav: 询问/断言A是否可以访问B
- dep: 询问/断言A是否依赖B才能执行
- impl: 询问/断言A是否实现了B
- nodetype: 询问/断言某实体的类型（参与者/用例/状态/模块/组件）
- label: 询问/断言边上的条件/标注文本
- cycle: 询问/断言循环依赖（A依赖B且B依赖A）
- lifecycle: 询问/断言某实体能否独立于另一实体存在

问题: {question}
答案断言: {answer}

严格输出JSON（无值用null，实体名保持原文）:
{{"kind": "上述之一或null", "entities": ["实体1", "实体2"], "relation": "UML类型英文名或null",
  "direction": ["从", "到"] 或 null, "node_type": "类型或null", "condition": "条件文本或null"}}"""


def llm_extract(question, answer, retries=2):
    prompt = PROMPT.format(question=question, answer=answer)
    for _ in range(retries):
        try:
            r = httpx.post(WQ_URL, headers={"Authorization": f"Bearer {KIMI_KEY}",
                                            "Content-Type": "application/json"},
                           json={"model": MODEL,
                                 "messages": [{"role": "user", "content": prompt}],
                                 "temperature": 1, "max_tokens": 400,
                                 "response_format": {"type": "json_object"}}, timeout=90)
            if r.status_code == 200:
                import re
                txt = r.json()['choices'][0]['message'].get('content', '')
                m = re.search(r'\{.*\}', txt, re.DOTALL)
                if m:
                    return json.loads(m.group(0))
        except Exception:
            time.sleep(2)
    return None


def llm_claim_to_dict(lc, question):
    """LLM JSON → verify()兼容的claim dict"""
    c = {'q': question, 'claim_text': '', 'ents': lc.get('entities') or [],
         'kind': lc.get('kind'), 'r_hat': lc.get('relation'),
         'dir_hat': None, 'dep_hat': None, 'type_hat': lc.get('node_type'),
         'label_hat': lc.get('condition'), 'lifecycle_hat': None,
         'cycle_pairs': [], 'subject': None}
    if lc.get('direction') and isinstance(lc['direction'], list) and len(lc['direction']) == 2:
        c['dir_hat'] = (str(lc['direction'][0]), str(lc['direction'][1]))
        if c['kind'] in (None, 'relation'):
            c['kind'] = c['kind'] or 'direction'
    if lc.get('kind') == 'dep' and c['dir_hat']:
        c['dep_hat'] = c['dir_hat']
    if lc.get('kind') == 'lifecycle':
        c['lifecycle_hat'] = 'independent'
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()

    corpus = json.load(open(CORPUS, encoding='utf-8'))
    rng = random.Random(42)
    # 分层: 负例按注入族配额 + 正例
    neg_by_fam = defaultdict(list)
    pos = []
    for q in corpus:
        if q['label'] == 'inconsistent':
            neg_by_fam[q.get('inject_type', '?')].append(q)
        else:
            pos.append(q)
    n_neg = args.n * 3 // 5
    sample = []
    fams = sorted(neg_by_fam, key=lambda k: -len(neg_by_fam[k]))
    quota = {f: max(2, n_neg * len(neg_by_fam[f]) // len(corpus)) for f in fams}
    for f in fams:
        take = min(quota[f], len(neg_by_fam[f]), 12)
        sample += rng.sample(neg_by_fam[f], take)
    sample = sample[:n_neg] + rng.sample(pos, args.n - n_neg)
    print(f"抽样{len(sample)}条 (负{sum(1 for q in sample if q['label']=='inconsistent')}/正{sum(1 for q in sample if q['label']=='consistent')})")

    gidx = GraphIndex()
    t0 = time.time()

    def run_one(qa):
        ans = strip_correction(qa.get('answer', ''))
        lc = llm_extract(qa.get('question', ''), ans)
        return qa, lc

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(run_one, q) for q in sample]
        for i, fut in enumerate(as_completed(futs)):
            qa, lc = fut.result()
            results.append((qa, lc))
            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(sample)}] {time.time()-t0:.0f}s")

    # ── 对比分析 ──
    agree_kind = agree_ents = agree_rel = 0
    det_agree = llm_tp = llm_fn = llm_fp = llm_tn = 0
    pat_tp = pat_fn = pat_fp = pat_tn = 0
    llm_fail = 0
    detail = []
    for qa, lc in results:
        gold = qa['label'] == 'inconsistent'
        pc = extract_claim(qa)
        # 模式抽取检测
        p_inc, p_fired, _ = verify(qa, pc, gidx)
        if p_inc and gold:
            pat_tp += 1
        elif p_inc and not gold:
            pat_fp += 1
        elif not p_inc and gold:
            pat_fn += 1
        else:
            pat_tn += 1
        if lc is None:
            llm_fail += 1
            # LLM失败 → 视为conservative(不触发)
            if gold:
                llm_fn += 1
            else:
                llm_tn += 1
            detail.append({'id': qa['id'], 'llm': 'FAILED'})
            continue
        # 声明级一致
        if (lc.get('kind') or None) == (pc['kind'] or None):
            agree_kind += 1
        lents = [e for e in (lc.get('entities') or []) if e]
        pents = pc['ents']
        if lents and pents and (lents[0] in pents or pents[0] in lents or set(lents) & set(pents)):
            agree_ents += 1
        elif not lents and not pents:
            agree_ents += 1
        if (lc.get('relation') or None) == (pc['r_hat'] or None):
            agree_rel += 1
        # LLM声明检测
        c = llm_claim_to_dict(lc, qa.get('question', ''))
        l_inc, l_fired, _ = verify(qa, c, gidx)
        if l_inc and gold:
            llm_tp += 1
        elif l_inc and not gold:
            llm_fp += 1
        elif not l_inc and gold:
            llm_fn += 1
        else:
            llm_tn += 1
        if l_inc == p_inc:
            det_agree += 1
        detail.append({'id': qa['id'], 'gold': gold, 'pattern': p_inc, 'llm': l_inc,
                       'pat_kind': pc['kind'], 'llm_kind': lc.get('kind'),
                       'llm_entities': lents, 'llm_fired': l_fired[:1]})

    n = len(results)
    n_ok = n - llm_fail
    def f1(tp, fp, fn):
        return 2 * tp / max(2 * tp + fp + fn, 1)
    print(f"\n[声明级一致率] kind {agree_kind}/{n_ok}={agree_kind/max(n_ok,1):.1%} | "
          f"实体 {agree_ents}/{n_ok}={agree_ents/max(n_ok,1):.1%} | 关系 {agree_rel}/{n_ok}={agree_rel/max(n_ok,1):.1%}")
    print(f"[下游检测一致率] LLM vs 模式: {det_agree}/{n_ok}={det_agree/max(n_ok,1):.1%}")
    print(f"[检测F1] 模式claim: {f1(pat_tp, pat_fp, pat_fn):.3f} (tp{pat_tp}/fp{pat_fp}/fn{pat_fn}) | "
          f"LLM claim: {f1(llm_tp, llm_fp, llm_fn):.3f} (tp{llm_tp}/fp{llm_fp}/fn{llm_fn})")
    print(f"[LLM抽取失败] {llm_fail}/{n} | 耗时{time.time()-t0:.0f}s")

    out = {'n': n, 'llm_model': MODEL,
           'agreement': {'kind': agree_kind / max(n_ok, 1), 'entities': agree_ents / max(n_ok, 1),
                         'relation': agree_rel / max(n_ok, 1), 'detection': det_agree / max(n_ok, 1)},
           'f1_pattern': f1(pat_tp, pat_fp, pat_fn), 'f1_llm': f1(llm_tp, llm_fp, llm_fn),
           'confusion': {'pattern': [pat_tp, pat_fp, pat_fn, pat_tn],
                         'llm': [llm_tp, llm_fp, llm_fn, llm_tn]},
           'llm_fail': llm_fail, 'detail': detail}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"结果已保存: {OUT}")


if __name__ == '__main__':
    main()
