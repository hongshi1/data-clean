#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict-40 真检测器套件：证据核验层（替换run_eval的oracle自检）
==============================================================

任务（CoVe式证据验证）:
  输入   = question + rendered_context（QA呈现的证据视图, 位置N [loc] 章节X: 内容）
  事实库 = entity.occurrences（文档事实, born-digital/MinerU提取）
  输出   = 呈现视图与事实库是否分歧 → inconsistent/consistent
  禁读   = answer / injection.* / occurrences_injected / z3_verified / label
           （answer以"存在不一致/一致"开头即判决, 读取=标签泄漏）

按40项分族的比对算法（全部确定性, 无LLM）:
  列表型(TERM-03/LOGIC-01..05/GJB表头): 集合差(缺失/多余) + 顺序比对(流程步骤)
  参数型(PARAM-01~10/TERM-06): (op,value,unit)解析 → 量纲归一 → 区间冲突(Z3-LIA)
  字符串型(TERM-01/02/05/07/08等): 归一化等值(剥HTML/空白)
  顺序型(LOGIC-03): 同集异序 → 步骤倒置

用法: python tools/strict40_detector_suite.py [--z3]
输出: data/gjb_438c/data_assets/srs_qa_v3/strict40_eval.json
"""
import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
EVAL_SET = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
OUT = BASE / "data/gjb_438c/data_assets/srs_qa_v3/strict40_eval.json"

# ── 量纲归一表（→ 基本单位） ──
UNIT_TO_BASE = {
    # 时间 → 秒
    'ms': ('s', 1e-3), '毫秒': ('s', 1e-3), 's': ('s', 1), '秒': ('s', 1),
    'min': ('s', 60), '分': ('s', 60), '分钟': ('s', 60),
    'h': ('s', 3600), '小时': ('s', 3600), '时': ('s', 3600), 'd': ('s', 86400), '天': ('s', 86400),
    # 存储 → GB
    'kb': ('GB', 1 / 1024 ** 2), 'mb': ('GB', 1 / 1024), 'gb': ('GB', 1), 'tb': ('GB', 1024),
    # 频率 → Hz
    'hz': ('Hz', 1), 'khz': ('Hz', 1e3), 'mhz': ('Hz', 1e6), 'ghz': ('Hz', 1e9),
    # 带宽 → Mbps
    'mbps': ('Mbps', 1), 'kbps': ('Mbps', 1 / 1000), 'gbps': ('Mbps', 1000),
}
OP_MAP = {'gt': 'gt', 'lt': 'lt', 'ge': 'ge', 'le': 'le', 'eq': 'eq',
          '>': 'gt', '<': 'lt', '>=': 'ge', '<=': 'le', '=': 'eq',
          '大于': 'gt', '小于': 'lt', '不超过': 'le', '不低于': 'ge', '超过': 'gt',
          '至多': 'le', '至少': 'ge', '最多': 'le', '最少': 'ge'}


def norm_text(s: str) -> str:
    """字符串归一: 去HTML标签/空白/全角差异/引号风格(渲染器JSON单双引号伪影)"""
    s = re.sub(r'<[^>]+>', ' ', str(s))
    s = re.sub(r'[\s\u3000\u00a0]+', '', s)
    s = s.replace('"', "'").replace('“', "'").replace('”', "'")
    return s


def strip_render_artifacts(text: str) -> str:
    """剥离渲染器截断注记: '...共14个位置(仅展示前6个)'（ASCII/Unicode省略号）"""
    return re.sub(r'[\.\u2026]{2,}\s*共\d+个?个?位?置?[（(]仅展示前\d+个?[）)]?\s*', '', text)


def norm_unit(value: float, unit: str):
    """量纲归一 → (base_unit, base_value); 未知单位原样返回"""
    u = (unit or '').strip().lower()
    if u in UNIT_TO_BASE:
        base, k = UNIT_TO_BASE[u]
        return base, value * k
    return (unit or '').strip(), value


def parse_rendered(rc: str):
    """rendered_context → [(location, section, text)]"""
    out = []
    for m in re.finditer(r'位置\d+\s*\[(\w+)\]\s*章节?([^:：]*)[:：]\s*(.*?)(?=位置\d+\s*\[|$)',
                         rc, re.DOTALL):
        out.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    return out


def parse_list(text: str):
    """呈现文本 → 元素列表（→ 或 、 分隔）"""
    if ('→' in text or '、' in text or '，' in text) and len(text) > 8:
        parts = re.split(r'\s*[→➜、]\s*', text)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            return parts
    return None


PARAM_RE = re.compile(r'\s*([<>≤≥=]|大于|小于|超过|不超过|不低于|至少|至多)?\s*([\d.]+)\s*([A-Za-zμΩ]+|秒|分|时|天|毫秒|分钟|小时)?\s*$')


def parse_param(text: str):
    """呈现文本 → (op, value, unit)（表格式参数呈现: '<128.0GB' / '>10ms'）"""
    t = norm_text(text)
    m = PARAM_RE.search(t)
    if not m or not m.group(2):
        return None
    op = OP_MAP.get(m.group(1) or '=', 'eq')
    try:
        val = float(m.group(2))
    except ValueError:
        return None
    return (op, val, m.group(3) or '')


def fact_param(occ: dict):
    """事实occurrence → (op, value, unit)"""
    if not isinstance(occ, dict) or 'op' not in occ:
        return None
    try:
        val = float(str(occ.get('content', '')).strip())
    except (ValueError, TypeError):
        return None
    op = OP_MAP.get(str(occ.get('op', '')).strip().lower(), 'eq')
    return (op, val, occ.get('unit', '') or '')


def interval_conflict(a, b):
    """两个(op,value)约束在同一量纲基单位下是否矛盾（Z3-LIA语义, 纯区间实现）"""
    OPS = {
        'gt': lambda x, v: x > v, 'ge': lambda x, v: x >= v,
        'lt': lambda x, v: x < v, 'le': lambda x, v: x <= v,
        'eq': lambda x, v: x == v,
    }
    # 采样判定: 在min/max锚点+边界±ε上找共同满足点（值域有限扫描）
    cands = sorted({a[1], b[1], a[1] - 1, a[1] + 1, b[1] - 1, b[1] + 1,
                    (a[1] + b[1]) / 2, 0.0})
    for x in cands:
        if OPS[a[0]](x, a[1]) and OPS[b[0]](x, b[1]):
            return False
    # 外延检查（无穷方向）
    if a[0] in ('gt', 'ge') and b[0] in ('gt', 'ge'):
        return False  # 同向必然可同时满足
    if a[0] in ('lt', 'le') and b[0] in ('lt', 'le'):
        return False
    if a[0] == 'eq' and b[0] == 'eq':
        return True
    # 混向: 采样已覆盖关键点, 再试大值
    for x in (a[1] * 2 + 1, b[1] * 2 + 1, abs(a[1]) * 10 + 1):
        if OPS[a[0]](x, a[1]) and OPS[b[0]](x, b[1]):
            return False
    return True


# ════════════════════════════════════════════════════════════════
# 检测器
# ════════════════════════════════════════════════════════════════

def detect_entry(entry) -> dict:
    """呈现证据 vs 文档事实 → (inconsistent, reasons)"""
    facts = entry.get('entity', {}).get('occurrences', [])
    presented = parse_rendered(entry.get('rendered_context', ''))
    fired = []
    if not facts or not presented:
        return {'pred': False, 'fired': fired, 'stage': 'empty'}

    for i, (loc, sec, text) in enumerate(presented):
        text = strip_render_artifacts(text)
        fact = facts[i] if i < len(facts) else None
        if fact is None:
            fired.append(f'pos{i}: 呈现位置数超出事实数')
            break
        floc = fact.get('location', '')
        # ── 参数型事实 ──
        fp = fact_param(fact)
        if fp:
            pp = parse_param(text)
            if pp:
                f_base, f_val = norm_unit(fp[1], fp[2])
                p_base, p_val = norm_unit(pp[1], pp[2])
                if f_base == p_base:
                    if abs(f_val - p_val) > max(abs(f_val), 1e-9) * 1e-6 and \
                       interval_conflict((pp[0], p_val), (fp[0], f_val)):
                        fired.append(f'pos{i}: 参数冲突 呈现{pp[0]}{p_val}{p_base} vs 事实{fp[0]}{f_val}{f_base}')
                    elif abs(f_val - p_val) > max(abs(f_val), 1e-9) * 1e-6:
                        # 值不同但区间不矛盾(如gt 10 vs gt 5) → 仍是不同约束, 报分歧
                        fired.append(f'pos{i}: 参数值不同 呈现{pp[0]}{p_val}{p_base} vs 事实{fp[0]}{f_val}{f_base}')
                else:
                    fired.append(f'pos{i}: 量纲族不同 呈现{p_base} vs 事实{f_base}')
            else:
                # 呈现非参数形态 → 字符串比对
                if norm_text(text) != norm_text(str(fact.get('content', ''))):
                    fired.append(f'pos{i}: 字符串分歧')
            continue
        # ── 列表型事实 ──
        fcontent = fact.get('content')
        if isinstance(fcontent, list):
            f_list = [norm_text(str(x)) for x in fcontent if str(x).strip()]
            p_whole = norm_text(text)
            # 整串优先: 渲染器可能用与元素内含相同的分隔符(如元素含"、") → 整体归一比对
            f_whole_variants = {norm_text(sep.join(f_list)) for sep in ('、', '→', '，', '')}
            if p_whole in f_whole_variants:
                continue  # 整串等值 → 无分歧
            p_list = parse_list(text)
            if p_list is None:
                p_list = [norm_text(text)] if norm_text(text) else []
            p_norm = [norm_text(x) for x in p_list if norm_text(x)]
            f_set, p_set = set(f_list), set(p_norm)
            miss, extra = f_set - p_set, p_set - f_set
            if miss:
                fired.append(f'pos{i}: 缺失元素{sorted(miss)[:3]}')
            elif extra:
                fired.append(f'pos{i}: 多余元素{sorted(extra)[:3]}')
            elif len(f_list) == len(p_norm) and f_list != p_norm:
                fired.append(f'pos{i}: 顺序不一致(步骤倒置) 前2项 呈现{p_norm[:2]} vs 事实{f_list[:2]}')
            continue
        # ── 字符串型事实 ──
        f_str = norm_text(str(fcontent or ''))
        p_str = norm_text(text)
        if f_str and p_str and f_str != p_str:
            # 容忍呈现含事实(加注释)? 注入是在事实上加后缀/前缀 → 不容忍, 直接分歧
            fired.append(f'pos{i}: 文本分歧 呈现「{p_str[:24]}」 vs 事实「{f_str[:24]}」')
    return {'pred': bool(fired), 'fired': fired, 'stage': 'ok'}


# ════════════════════════════════════════════════════════════════
# 评测
# ════════════════════════════════════════════════════════════════

def prf(tp, fp, fn, tn):
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    return {'P': round(p, 4), 'R': round(r, 4), 'F1': round(2 * p * r / max(p + r, 1e-9), 4),
            'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump-errors', type=int, default=8)
    args = ap.parse_args()
    es = json.load(open(EVAL_SET, encoding='utf-8'))
    entries = es['entries']
    print(f"strict-40真检测器（证据核验层）: {len(entries)}条")
    print("禁读: answer/injection/occ_injected/z3_verified/label | 输入: question+rendered_context+事实库")

    t0 = time.time()
    preds = []
    for e in entries:
        d = detect_entry(e)
        preds.append({'eval_id': e.get('eval_id'), 'check_item': e['check_item'],
                      'label': e['label'], 'confidence': e.get('confidence', ''),
                      'pred': d['pred'], 'fired': d['fired'][:2], 'stage': d['stage'],
                      'difficulty': e.get('difficulty', '')})

    tp = sum(1 for p in preds if p['pred'] and p['label'] == 'inconsistent')
    fp = sum(1 for p in preds if p['pred'] and p['label'] == 'consistent')
    fn = sum(1 for p in preds if not p['pred'] and p['label'] == 'inconsistent')
    tn = sum(1 for p in preds if not p['pred'] and p['label'] == 'consistent')
    m = prf(tp, fp, fn, tn)
    print(f"\n[总体] P={m['P']} R={m['R']} F1={m['F1']} (tp={tp} fp={fp} fn={fn} tn={tn}) [{time.time()-t0:.0f}s]")

    # 分族
    fam = defaultdict(list)
    for p in preds:
        fam[p['check_item'].split('-')[0]].append(p)
    by_fam = {}
    print("\n[分族] vs 旧oracle评测(run_eval, 15号报告):")
    OLD = {'TERM': 0.8372, 'PARAM': 1.0, 'LOGIC': 1.0, 'GJB': 1.0, 'POSITIVE': 0.98}
    for f, ps in fam.items():
        t = sum(1 for p in ps if p['pred'] and p['label'] == 'inconsistent')
        fp2 = sum(1 for p in ps if p['pred'] and p['label'] == 'consistent')
        fn2 = sum(1 for p in ps if not p['pred'] and p['label'] == 'inconsistent')
        tn2 = sum(1 for p in ps if not p['pred'] and p['label'] == 'consistent')
        fm = prf(t, fp2, fn2, tn2)
        by_fam[f] = fm
        old = OLD.get(f, '-')
        print(f"  {f:9s}: F1={fm['F1']:.4f} (R={fm['R']})  | 旧oracle F1={old}")

    # 分项(check_item)
    by_item = defaultdict(list)
    for p in preds:
        by_item[p['check_item']].append(p)
    item_scores = {}
    print("\n[分项] (旧: TERM-03=0.00 / TERM-06=0.75 / TERM-04未实现):")
    for ci, ps in sorted(by_item.items()):
        det = sum(1 for p in ps if p['pred'] and p['label'] == 'inconsistent')
        miss = sum(1 for p in ps if not p['pred'] and p['label'] == 'inconsistent')
        fp2 = sum(1 for p in ps if p['pred'] and p['label'] == 'consistent')
        item_scores[ci] = {'n': len(ps), 'detected': det, 'miss': miss, 'fp': fp2,
                           'score': round(det / max(det + miss, 1), 3)}
    for ci, s in item_scores.items():
        flag = ' ⚠' if s['miss'] or s['fp'] else ''
        print(f"  {ci:10s}: {s['detected']}/{s['detected']+s['miss']} (FP {s['fp']}){flag}")

    # 置信度分层
    by_conf = defaultdict(list)
    for p in preds:
        by_conf[p['confidence'] or '?'].append(p)
    conf_stats = {}
    for c, ps in by_conf.items():
        t = sum(1 for p in ps if p['pred'] and p['label'] == 'inconsistent')
        fp2 = sum(1 for p in ps if p['pred'] and p['label'] == 'consistent')
        fn2 = sum(1 for p in ps if not p['pred'] and p['label'] == 'inconsistent')
        tn2 = sum(1 for p in ps if not p['pred'] and p['label'] == 'consistent')
        conf_stats[c] = prf(t, fp2, fn2, tn2)
    print("\n[置信度分层]", {c: v['F1'] for c, v in conf_stats.items()})

    # 错误样例
    errs = [p for p in preds if p['pred'] != (p['label'] == 'inconsistent')]
    print(f"\n[错误] {len(errs)}条:")
    for p in errs[:args.dump_errors]:
        print(f"  [{p['check_item']}/{p['label']}] fired={p['fired'][:1]}")

    result = {'config': {'corpus': str(EVAL_SET), 'oracle_fields_read': 'NONE',
                         'note': '证据核验层: rendered_context(呈现) vs entity.occurrences(事实)'},
              'overall': m, 'by_family': by_fam, 'by_item': item_scores,
              'by_confidence': conf_stats,
              'errors': [{'check_item': p['check_item'], 'label': p['label'],
                          'fired': p['fired']} for p in errs[:30]]}
    json.dump(result, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n结果已保存: {OUT}")


if __name__ == '__main__':
    main()
