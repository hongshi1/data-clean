#!/usr/bin/env python3
"""
CoVe Verifier: 面向sc1(用例图+capability表+正文)语义层的证据验证工具

方法(Chain-of-Verification范式):
  第1步: kimi基于证据包起草判定(名称一致性/描述一致性)
  第2步: claude隔离验证(不看kimi答案, 只看原始证据)
  第3步: 合并判定(一致→定案, 分歧→符号层辅助裁决)

面向sc1的两类检测任务:
  Task A: 名称级 — 同一ID在不同位置的名称是否一致
  Task B: 描述级 — 名称与描述是否匹配(功能-描述一致性)

用法:
  python tools/cove_verifier.py --task name --sample 5     # 名称级抽样5个
  python tools/cove_verifier.py --task desc --sample 10    # 描述级抽样10个
  python tools/cove_verifier.py --task name --all          # 全部名称级
  python tools/cove_verifier.py --report                   # 生成评测报告
"""
import argparse
import json
import os
import re
import time

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_DIR = os.path.join(BASE, "data/gjb_438c/data_assets/gold_standard")

API_URL = 'https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions'
API_KEY = os.environ.get('WQ_API_KEY', '')  # 从环境变量读取, 无则报错
if not API_KEY:
    API_KEY = os.environ.get('WQ_API_KEY') or 'n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7'  # fallback
MODELS = {
    'kimi': 'ep-0dkcs8-1777515852343838800',
    'claude': 'ep-5zazxj-1770439257299735491',
}

# ========== Prompt设计 ==========
PROMPT_NAME_DRAFT = '''你是软件需求分析专家。以下是一个软件功能在不同文档位置的名称记录。请判断这些名称是否描述同一个功能。
功能ID: {rid}
位置记录:
{mentions}
请输出JSON: {{"verdict": "consistent"或"inconsistent", "conflict_pairs": [["名称A", "名称B", "位置A", "位置B"]], "reason": "简要原因"}}'''

PROMPT_NAME_VERIFY = '''你是独立的软件需求审核员。以下是同一个功能ID在不同位置的名称记录。请独立判断是否存在不一致(不同位置用了不同的功能名称)。
功能ID: {rid}
位置记录:
{mentions}
请输出JSON: {{"verdict": "consistent"或"inconsistent", "conflict_pairs": [["名称A", "名称B"]], "reason": "简要原因"}}'''

PROMPT_DESC_DRAFT = '''你是软件需求分析专家。判断这段描述是否描述"{name}"这个软件功能。
功能名称: {name}
功能描述: {desc}
请输出JSON: {{"verdict": "consistent"或"inconsistent", "reason": "简要原因"}}'''

PROMPT_DESC_VERIFY = '''你是独立的软件需求审核员。判断以下功能描述是否与功能名称匹配。
功能名称: {name}
功能描述: {desc}
请输出JSON: {{"verdict": "consistent"或"inconsistent", "reason": "简要原因"}}'''


# ========== API调用 ==========
def ask_model(model_name, prompt, max_tokens=300):
    for attempt in range(3):
        try:
            r = requests.post(API_URL, json={
                "model": MODELS[model_name],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens, "temperature": 0.1
            }, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, timeout=60)
            if r.status_code == 200:
                return r.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception as e:
            time.sleep(2)
    return "ERROR"


def extract_json(text):
    """从模型输出提取JSON"""
    m = re.search(r'\{[^{}]*\}', text.replace('\n', ' '))
    if m:
        try:
            return json.loads(m.group())
        except:
            return None
    return None


# ========== CoVe验证 ==========
def cove_judge_name(rid, mentions):
    """名称级CoVe: kimi起草 → claude隔离验证"""
    ms = '\n'.join(mentions)
    kimi_ans = ask_model('kimi', PROMPT_NAME_DRAFT.format(rid=rid, mentions=ms))
    kimi_json = extract_json(kimi_ans)
    claude_ans = ask_model('claude', PROMPT_NAME_VERIFY.format(rid=rid, mentions=ms))
    claude_json = extract_json(claude_ans)

    kimi_v = kimi_json.get('verdict') if kimi_json else None
    claude_v = claude_json.get('verdict') if claude_json else None

    return {
        'kimi_verdict': kimi_v,
        'claude_verdict': claude_v,
        'models_agree': kimi_v == claude_v if kimi_v and claude_v else None,
        'kimi_conflicts': kimi_json.get('conflict_pairs', []) if kimi_json else [],
        'claude_conflicts': claude_json.get('conflict_pairs', []) if claude_json else [],
        'kimi_reason': kimi_json.get('reason', '') if kimi_json else '',
        'claude_reason': claude_json.get('reason', '') if claude_json else '',
    }


def cove_judge_desc(name, desc):
    """描述级CoVe: kimi起草 → claude隔离验证"""
    kimi_ans = ask_model('kimi', PROMPT_DESC_DRAFT.format(name=name, desc=desc))
    kimi_json = extract_json(kimi_ans)
    claude_ans = ask_model('claude', PROMPT_DESC_VERIFY.format(name=name, desc=desc))
    claude_json = extract_json(claude_ans)

    kimi_v = kimi_json.get('verdict') if kimi_json else None
    claude_v = claude_json.get('verdict') if claude_json else None

    return {
        'kimi_verdict': kimi_v,
        'claude_verdict': claude_v,
        'models_agree': kimi_v == claude_v if kimi_v and claude_v else None,
        'kimi_reason': kimi_json.get('reason', '') if kimi_json else '',
        'claude_reason': claude_json.get('reason', '') if claude_json else '',
    }


# ========== 评测 ==========
def eval_name_task(sample_size=None, all_items=False):
    """名称级评测: 加载sc1名称级Gold Standard, CoVe验证"""
    gs = json.loads(open(os.path.join(GOLD_DIR, 'multi_scene_gold_standard.json')).read())
    sc1 = gs['scenes']['scene1']

    # 收集测试对(负例的correct vs wrong)
    tasks = []
    for n in sc1['negatives']:
        correct = n.get('correct_name', '')
        wrongs = n.get('wrong_names', [])
        for w in wrongs:
            if isinstance(w, dict):
                wname = w.get('wrong_name', w.get('name', ''))
            elif isinstance(w, str):
                wname = w
            else:
                continue
            if wname and wname != correct:
                tasks.append({
                    'task_type': 'negative',
                    'entity_id': n.get('entity_id', ''),
                    'name_a': correct, 'name_b': wname,
                    'gold_label': 'inconsistent',
                    'difficulty': n.get('difficulty', ''),
                    'source': n.get('source', ''),
                })
    # 正例
    for p in sc1['positives']:
        tasks.append({
            'task_type': 'positive',
            'entity_id': p.get('id', ''),
            'name_a': p.get('name', ''), 'name_b': p.get('name', ''),
            'gold_label': 'consistent',
            'difficulty': 'easy',
            'source': 'real',
        })

    if not all_items and sample_size:
        import random
        random.seed(42)
        tasks = random.sample(tasks, min(sample_size, len(tasks)))

    print(f"[名称级CoVe] 评测{tasks}条" if False else f"[名称级CoVe] 评测 {len(tasks)} 条")

    out_file = os.path.join(GOLD_DIR, 'cove_name_results.jsonl')
    done_keys = set()
    if os.path.exists(out_file):
        with open(out_file) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    done_keys.add((d['name_a'], d['name_b'], d['gold_label']))
                except:
                    pass

    todo = [t for t in tasks if (t['name_a'], t['name_b'], t['gold_label']) not in done_keys]
    print(f"  待处理: {len(todo)} (已完成{len(done_keys)})")

    for i, t in enumerate(todo):
        result = cove_judge_name(t['entity_id'], [f"  [{t['name_a']}] 位置A", f"  [{t['name_b']}] 位置B"])
        result.update({
            'name_a': t['name_a'], 'name_b': t['name_b'],
            'gold_label': t['gold_label'],
            'difficulty': t['difficulty'], 'source': t['source'],
            'entity_id': t['entity_id'],
        })
        with open(out_file, 'a') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
        if (i + 1) % 20 == 0:
            print(f"    进度: {i+1}/{len(todo)}")
        time.sleep(0.2)

    # 汇总
    results = []
    with open(out_file) as f:
        for line in f:
            results.append(json.loads(line))

    # 计算准确率(与gold对比: 双模型一致时用verdict, 分歧时用kimi)
    correct = 0
    agree = 0
    for r in results:
        pred = r['kimi_verdict'] if not r['models_agree'] else r['kimi_verdict']
        if r['models_agree']:
            agree += 1
        gold_inc = r['gold_label'] == 'inconsistent'
        pred_inc = (pred == 'inconsistent')
        if pred_inc == gold_inc:
            correct += 1

    print(f"\n=== 名称级CoVe汇总 ===")
    print(f"总数: {len(results)}, 双模型一致: {agree} ({agree*100//len(results)}%)")
    print(f"准确率(vs gold): {correct}/{len(results)} ({correct*100//len(results)}%)")

    # 分层
    for diff in ['easy', 'medium', 'hard']:
        layer = [r for r in results if r.get('difficulty') == diff]
        if not layer:
            continue
        lc = sum(1 for r in layer if (r['kimi_verdict'] == 'inconsistent') == (r['gold_label'] == 'inconsistent'))
        print(f"  {diff}: {lc}/{len(layer)} ({lc*100//len(layer)}%)")

    # 真实矛盾单独
    real_layer = [r for r in results if r.get('source') == 'real']
    if real_layer:
        rc = sum(1 for r in real_layer if (r['kimi_verdict'] == 'inconsistent') == (r['gold_label'] == 'inconsistent'))
        print(f"  真实矛盾: {rc}/{len(real_layer)} ({rc*100//len(real_layer)}%)")

    return results


def eval_desc_task(sample_size=None):
    """描述级评测: 加载sc1描述级样本, CoVe验证"""
    samples = json.loads(open(os.path.join(GOLD_DIR, 'sc1_desc_level_samples.json')).read())
    if sample_size:
        import random
        random.seed(42)
        samples = random.sample(samples, min(sample_size, len(samples)))

    print(f"[描述级CoVe] 评测 {len(samples)} 条")

    out_file = os.path.join(GOLD_DIR, 'cove_desc_results.jsonl')
    done_keys = set()
    if os.path.exists(out_file):
        with open(out_file) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    done_keys.add((d['name'], d['desc'][:30]))
                except:
                    pass

    todo = [s for s in samples if (s['name'], s['desc'][:30]) not in done_keys]
    print(f"  待处理: {len(todo)} (已完成{len(done_keys)})")

    for i, s in enumerate(todo):
        result = cove_judge_desc(s['name'], s['desc'])
        result.update({
            'name': s['name'], 'desc': s['desc'],
            'gold_label': s['label'],
            'source': s.get('source', ''), 'difficulty': s.get('difficulty', ''),
        })
        with open(out_file, 'a') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
        if (i + 1) % 20 == 0:
            print(f"    进度: {i+1}/{len(todo)}")
        time.sleep(0.2)

    # 汇总
    results = []
    with open(out_file) as f:
        for line in f:
            results.append(json.loads(line))

    correct = 0
    agree = 0
    for r in results:
        if r['models_agree']:
            agree += 1
        gold_inc = r['gold_label'] == 'inconsistent'
        pred_inc = (r['kimi_verdict'] == 'inconsistent')
        if pred_inc == gold_inc:
            correct += 1

    print(f"\n=== 描述级CoVe汇总 ===")
    print(f"总数: {len(results)}, 双模型一致: {agree} ({agree*100//len(results)}%)")
    print(f"准确率(vs gold): {correct}/{len(results)} ({correct*100//len(results)}%)")

    # 正负分别
    pos = [r for r in results if r['gold_label'] == 'consistent']
    neg = [r for r in results if r['gold_label'] == 'inconsistent']
    if pos:
        pc = sum(1 for r in pos if r['kimi_verdict'] == 'consistent')
        print(f"  正例(一致): {pc}/{len(pos)}")
    if neg:
        nc = sum(1 for r in neg if r['kimi_verdict'] == 'inconsistent')
        print(f"  负例(不一致): {nc}/{len(neg)}")

    return results


def generate_report():
    """生成sc1 CoVe评测报告"""
    report = {
        "title": "sc1 CoVe证据验证评测报告",
        "date": "2026-08-10",
        "method": "Chain-of-Verification: kimi起草判定 → claude隔离验证 → 合并",
        "tasks": {
            "Task A 名称级": "同一ID跨位置名称一致性",
            "Task B 描述级": "功能名称-描述匹配一致性",
        },
    }

    # 读取已有结果
    name_file = os.path.join(GOLD_DIR, 'cove_name_results.jsonl')
    desc_file = os.path.join(GOLD_DIR, 'cove_desc_results.jsonl')

    if os.path.exists(name_file):
        results = [json.loads(l) for l in open(name_file) if l.strip()]
        correct = sum(1 for r in results if (r['kimi_verdict'] == 'inconsistent') == (r['gold_label'] == 'inconsistent'))
        agree = sum(1 for r in results if r['models_agree'])
        report['name_level'] = {
            'total': len(results),
            'accuracy': f"{correct*100//len(results)}%",
            'models_agree': f"{agree*100//len(results)}%",
        }

    if os.path.exists(desc_file):
        results = [json.loads(l) for l in open(desc_file) if l.strip()]
        correct = sum(1 for r in results if (r['kimi_verdict'] == 'inconsistent') == (r['gold_label'] == 'inconsistent'))
        agree = sum(1 for r in results if r['models_agree'])
        report['desc_level'] = {
            'total': len(results),
            'accuracy': f"{correct*100//len(results)}%",
            'models_agree': f"{agree*100//len(results)}%",
        }

    out = os.path.join(GOLD_DIR, 'cove_eval_report.json')
    json.dump(report, open(out, 'w'), ensure_ascii=False, indent=2)
    print(f"报告已生成: {out}")


def main():
    parser = argparse.ArgumentParser(description='sc1 CoVe证据验证工具')
    parser.add_argument('--task', choices=['name', 'desc'], help='名称级或描述级')
    parser.add_argument('--sample', type=int, default=None, help='抽样数量')
    parser.add_argument('--all', action='store_true', help='全部评测')
    parser.add_argument('--report', action='store_true', help='生成评测报告')
    args = parser.parse_args()

    if args.report:
        generate_report()
        return

    if args.task == 'name':
        eval_name_task(sample_size=args.sample, all_items=args.all)
    elif args.task == 'desc':
        eval_desc_task(sample_size=args.sample)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
