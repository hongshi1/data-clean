#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段1: 用 Ollama + Qwen2:7b 替代手写规则做 MedTVT 血检-诊断冲突检测.

方法 (per-lab LLM 判定):
  1. 读取 train.csv, 选取 5 项关键血检 (乳酸/肌酐/血糖/钾/pH).
  2. 预筛 (代码, 非医学判定): 仅保留 "No Finding==1 且 该指标超出正常范围" 的
     (样本, 指标) 候选对. 这只是粗筛, 把 10000 行 × 5 指标压到 ~2900 候选,
     避免对正常值也调 LLM. 是否"严重到构成漏诊冲突"由 LLM 判定.
  3. 对每个候选 (样本, 指标), 构造 per-lab prompt 发给 Qwen2:7b, LLM 依据医学
     知识判断该异常值在 "No Finding" 诊断下是否构成漏诊冲突, 返回 JSON.
  4. 代码做数值校验 (guard): Qwen2:7b 对数字比较不可靠 (会幻觉, 例如把正常肌酐
     报为冲突、或混淆 pH 方向), 因此以行内真实数值重新核对: 只保留 LLM 判定
     is_conflict=true 且真实数值确实达到严重阈值的条目, 丢弃幻觉/越界条目.
     (见 sample_llm_outputs.json 中 llm_dropped 字段.)
  5. 汇总冲突, 与手写规则结果 (1444) 做 (subject_id, conflict_type) 对比.

依赖: requests, pandas. 用系统 python3 运行, 不需要 data-juicer.

用法:
  python3 run_llm_medical_conflict.py --test          # 60 候选分层测试, 看质量
  python3 run_llm_medical_conflict.py --full          # 预筛 + 全量 LLM 判定
  python3 run_llm_medical_conflict.py --full --workers 4
  python3 run_llm_medical_conflict.py --compare       # 仅重算对比
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

# ----------------------------------------------------------------------------
# 路径与常量
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDTVT_DIR = os.path.join(BASE_DIR, "medical_data", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "medical_data", "medtvt"))
TRAIN_CSV = os.path.join(MEDTVT_DIR, "train.csv")
RULES_JSON = os.path.join(MEDTVT_DIR, "results", "medical_conflict_results.json")
OUT_DIR = os.path.join(MEDTVT_DIR, "output_llm")
LLM_RESULTS_JSON = os.path.join(OUT_DIR, "llm_conflict_results.json")
COMPARISON_JSON = os.path.join(OUT_DIR, "llm_vs_rules_comparison.json")
SAMPLE_OUTPUTS_JSON = os.path.join(OUT_DIR, "sample_llm_outputs.json")
CHECKPOINT_JSON = os.path.join(OUT_DIR, "_checkpoint.json")

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2:7b"

DIAG_LABELS = ["Atelectasis", "Cardiomegaly", "Edema", "Lung Opacity",
               "No Finding", "Pleural Effusion"]

# 5 项关键血检 (与手写规则 knowledge_base L2 / 1444 结果对齐)
# normal: 正常范围 (代码粗筛用); sev_op/sev_thr: 严重阈值 (代码 guard 用, 与规则一致)
LABS = [
    {"itemid": "50893", "name_cn": "乳酸", "name_en": "Lactate", "unit": "mmol/L",
     "normal": (0.5, 2.0), "sev_op": ">", "sev_thr": 5.0,
     "sev_desc": "严重标准: 乳酸 > 5.0 mmol/L",
     "conflict_type": "乳酸酸中毒漏诊", "severity": "CRITICAL"},
    {"itemid": "51237", "name_cn": "肌酐", "name_en": "Creatinine", "unit": "mg/dL",
     "normal": (0.6, 1.2), "sev_op": ">", "sev_thr": 2.0,
     "sev_desc": "严重标准: 肌酐 > 2.0 mg/dL",
     "conflict_type": "肾功能异常漏诊", "severity": "HIGH"},
    {"itemid": "50931", "name_cn": "血糖", "name_en": "Glucose", "unit": "mg/dL",
     "normal": (70, 110), "sev_op": ">", "sev_thr": 300.0,
     "sev_desc": "严重标准: 血糖 > 300 mg/dL",
     "conflict_type": "高血糖漏诊", "severity": "MEDIUM"},
    {"itemid": "50971", "name_cn": "钾", "name_en": "Potassium", "unit": "mmol/L",
     "normal": (3.5, 5.0), "sev_op": ">", "sev_thr": 6.0,
     "sev_desc": "严重标准: 钾 > 6.0 mmol/L",
     "conflict_type": "高钾血症漏诊", "severity": "CRITICAL"},
    {"itemid": "50820", "name_cn": "pH", "name_en": "pH", "unit": "",
     "normal": (7.35, 7.45), "sev_op": "<", "sev_thr": 7.20,
     "sev_desc": "严重标准: pH < 7.20 (数值低于7.20为严重酸中毒; 例如7.17低于7.20属严重)",
     "conflict_type": "严重酸中毒漏诊", "severity": "CRITICAL"},
]
LAB_BY_ITEM = {l["itemid"]: l for l in LABS}


def fmt_val(v):
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def crosses_severe(lab, val):
    if val is None or pd.isna(val):
        return False
    try:
        val = float(val)
    except (TypeError, ValueError):
        return False
    if lab["sev_op"] == ">":
        return val > lab["sev_thr"]
    return val < lab["sev_thr"]


def outside_normal(lab, val):
    if val is None or pd.isna(val):
        return False
    try:
        val = float(val)
    except (TypeError, ValueError):
        return False
    lo, hi = lab["normal"]
    return val < lo or val > hi


# ----------------------------------------------------------------------------
# 预筛: 生成 (row_index, lab) 候选对
# ----------------------------------------------------------------------------
def build_candidates(df):
    """候选 = No Finding==1 且 指标超出正常范围的 (row, lab) 对.

    冲突定义要求 No Finding=1; 全正常值不可能构成冲突, 粗筛排除.
    是否严重到漏诊由 LLM 判定.
    """
    cands = []
    nf_idx = df.index[df["No Finding"] == 1].tolist()
    for i in nf_idx:
        row = df.loc[i]
        for lab in LABS:
            v = fmt_val(row[lab["itemid"]])
            if v is None:
                continue
            if outside_normal(lab, v):
                cands.append((int(i), lab["itemid"]))
    return cands


# ----------------------------------------------------------------------------
# per-lab Prompt
# ----------------------------------------------------------------------------
def build_prompt(lab, val):
    lo, hi = lab["normal"]
    unit = f" {lab['unit']}" if lab["unit"] else ""
    return f"""任务是判断单一生化指标是否构成漏诊冲突。患者诊断为"无异常(No Finding)"。
检验项目: {lab['name_cn']}({lab['name_en']}) = {val}{unit}
正常范围: {lo} - {hi}{unit}
{lab['sev_desc']}
判断规则: 若该数值达到"严重标准"则判定为冲突(is_conflict=true); 若仅轻度异常或正常则is_conflict=false。
仅输出JSON: {{"is_conflict":true,"reason":"..."}} 或 {{"is_conflict":false,"reason":"..."}}"""


# ----------------------------------------------------------------------------
# Ollama 调用
# ----------------------------------------------------------------------------
def call_ollama(prompt, max_retries=2, timeout=120):
    last_err = None
    for _ in range(max_retries + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "format": "json",
                      "options": {"temperature": 0.0, "num_predict": 150}},
                timeout=timeout,
            )
            resp.raise_for_status()
            raw = resp.json()["response"].strip()
            return json.loads(raw), raw
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.3)
    return None, f"ERROR: {last_err}"


# ----------------------------------------------------------------------------
# 单候选处理
# ----------------------------------------------------------------------------
def process_candidate(args):
    idx, itemid, df = args
    lab = LAB_BY_ITEM[itemid]
    row = df.loc[idx]
    val = fmt_val(row[lab["itemid"]])
    truth_severe = crosses_severe(lab, val)
    prompt = build_prompt(lab, val)
    data, raw = call_ollama(prompt)
    if data is None:
        return (idx, itemid, val, truth_severe, None, raw, False, "call_failed")
    is_conflict = bool(data.get("is_conflict", False))
    reason = str(data.get("reason", ""))[:200]
    # 代码 guard: 丢弃 LLM 幻觉 (判定冲突但真实值未达严重阈值)
    if is_conflict and not truth_severe:
        return (idx, itemid, val, truth_severe, data, raw, False,
                f"guard_drop: LLM报冲突但真实值{val}未达严重阈值")
    return (idx, itemid, val, truth_severe, data, raw, is_conflict and truth_severe, reason)


# ----------------------------------------------------------------------------
# 全量运行
# ----------------------------------------------------------------------------
def load_checkpoint():
    if os.path.exists(CHECKPOINT_JSON):
        try:
            return json.load(open(CHECKPOINT_JSON))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def save_checkpoint(ck):
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = CHECKPOINT_JSON + ".tmp"
    json.dump(ck, open(tmp, "w"))
    os.replace(tmp, CHECKPOINT_JSON)


def run_full(df, workers=4, limit=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    cands = build_candidates(df)
    print(f"[预筛] 候选 (样本,指标) 对: {len(cands)} (No Finding==1 且 指标超正常范围)")

    ck = load_checkpoint()
    done = ck.get("results", {})
    todo = [(i, it) for (i, it) in cands if f"{i}:{it}" not in done]
    if limit:
        todo = todo[:limit]
    print(f"[续跑] 已完成 {len(done)}, 待处理 {len(todo)}")

    t0 = time.time()
    n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(process_candidate, (i, it, df)) for (i, it) in todo]
        for fut in as_completed(futs):
            idx, itemid, val, truth, data, raw, kept, reason = fut.result()
            done[f"{idx}:{itemid}"] = {
                "val": val, "truth_severe": truth,
                "llm_is_conflict": (data or {}).get("is_conflict"),
                "kept": kept, "note": reason,
            }
            n += 1
            if n % 100 == 0 or n == len(todo):
                el = time.time() - t0
                rate = n / max(el, 1e-6)
                print(f"  进度 {n}/{len(todo)} 速率 {rate:.1f}/s "
                      f"ETA {(len(todo)-n)/max(rate,1e-6)/60:.1f}min")
            if n % 200 == 0:
                save_checkpoint({"results": done})
    save_checkpoint({"results": done})

    # 汇总冲突
    conflicts = []
    for (idx, itemid) in cands:
        rec = done.get(f"{idx}:{itemid}")
        if not rec or not rec["kept"]:
            continue
        lab = LAB_BY_ITEM[itemid]
        row = df.loc[idx]
        conflicts.append({
            "subject_id": int(row["subject_id"]),
            "hadm_id": int(row["hadm_id"]),
            "conflict_type": lab["conflict_type"],
            "detail": f"{lab['name_cn']}={rec['val']} 但诊断为'No Finding'",
            "severity": lab["severity"],
            "lab_value": rec["val"],
            "lab_name": lab["name_cn"],
            "diagnosis": "No Finding",
            "reason": rec["note"],
        })
    by_type = {}
    for c in conflicts:
        by_type[c["conflict_type"]] = by_type.get(c["conflict_type"], 0) + 1
    out = {
        "method": "ollama_qwen2_7b_per_lab",
        "model": OLLAMA_MODEL,
        "total_samples": int(len(df)),
        "n_candidates_sent_to_llm": len(cands),
        "n_conflicts": len(conflicts),
        "conflict_by_type": by_type,
        "conflicts": conflicts,
    }
    json.dump(out, open(LLM_RESULTS_JSON, "w"), ensure_ascii=False, indent=2)
    print(f"[完成] LLM 检出冲突 {len(conflicts)} 条 by_type={by_type}")
    print(f"  写入 {LLM_RESULTS_JSON}")
    return out


# ----------------------------------------------------------------------------
# 测试 (60 候选, 分层抽样)
# ----------------------------------------------------------------------------
def run_test(df, per_lab=12):
    os.makedirs(OUT_DIR, exist_ok=True)
    cands = build_candidates(df)
    print(f"[预筛] 候选总数: {len(cands)}; 分层抽样每指标 {per_lab} 条 (半 severe / 半 mild)")
    # 分层: 每个指标抽 per_lab/2 个 severe + per_lab/2 个 mild
    by_lab = {l["itemid"]: {"severe": [], "mild": []} for l in LABS}
    for (idx, itemid) in cands:
        lab = LAB_BY_ITEM[itemid]
        v = fmt_val(df.loc[idx][itemid])
        bucket = "severe" if crosses_severe(lab, v) else "mild"
        by_lab[itemid][bucket].append((idx, itemid))
    sample = []
    for itemid, b in by_lab.items():
        sev = b["severe"][:per_lab // 2]
        mil = b["mild"][:per_lab - len(sev)]
        sample += sev + mil
    print(f"[测试] 抽样 {len(sample)} 候选")

    samples = []
    t0 = time.time()
    for (idx, itemid) in sample:
        r = process_candidate((idx, itemid, df))
        idx, itemid, val, truth, data, raw, kept, reason = r
        lab = LAB_BY_ITEM[itemid]
        samples.append({
            "row_index": idx,
            "subject_id": int(df.loc[idx]["subject_id"]),
            "lab_name": lab["name_cn"],
            "lab_value": val,
            "truth_severe": truth,
            "llm_is_conflict": (data or {}).get("is_conflict"),
            "kept_after_guard": kept,
            "note": reason,
            "llm_raw": raw,
        })
    print(f"[测试] 耗时 {time.time()-t0:.1f}s")
    # 汇总: per-lab 混淆矩阵
    print("\n[测试] per-lab 混淆矩阵 (truth=severe 时 LLM 应判 conflict):")
    print(f"{'指标':<8} {'sev_total':>9} {'sev_kept(TP)':>12} {'sev_miss(FN)':>12} "
          f"{'mild_total':>10} {'mild_flagged(FP)':>15}")
    summary = {}
    for lab in LABS:
        ss = [s for s in samples if s["lab_name"] == lab["name_cn"]]
        sev = [s for s in ss if s["truth_severe"]]
        mil = [s for s in ss if not s["truth_severe"]]
        tp = sum(1 for s in sev if s["kept_after_guard"])
        fn = len(sev) - tp
        fp = sum(1 for s in mil if s["llm_is_conflict"])  # guard 前的 FP
        fp_kept = sum(1 for s in mil if s["kept_after_guard"])  # guard 后应 0
        summary[lab["name_cn"]] = dict(sev=len(sev), tp=tp, fn=fn,
                                       mil=len(mil), fp=fp, fp_kept=fp_kept)
        print(f"{lab['name_cn']:<8} {len(sev):>9} {tp:>12} {fn:>12} "
              f"{len(mil):>10} {fp:>15} (guard后保留{fp_kept})")
    json.dump({"samples": samples, "summary": summary},
              open(SAMPLE_OUTPUTS_JSON, "w"), ensure_ascii=False, indent=2)
    print(f"\n[测试] 写入 {SAMPLE_OUTPUTS_JSON}")
    return samples, summary


# ----------------------------------------------------------------------------
# 与手写规则对比
# ----------------------------------------------------------------------------
def run_compare():
    if not os.path.exists(LLM_RESULTS_JSON):
        print(f"[错误] 找不到 {LLM_RESULTS_JSON}, 请先 --full", file=sys.stderr)
        sys.exit(1)
    llm = json.load(open(LLM_RESULTS_JSON))
    rules = json.load(open(RULES_JSON))
    rules_tuples = set((c["subject_id"], c["conflict_type"]) for c in rules["conflicts"])
    llm_tuples = set((c["subject_id"], c["conflict_type"]) for c in llm["conflicts"])
    inter = llm_tuples & rules_tuples
    only_llm = llm_tuples - rules_tuples
    only_rules = rules_tuples - llm_tuples
    overlap = len(inter) / len(rules_tuples) if rules_tuples else 0.0
    cmp = {
        "rules_total": len(rules_tuples),
        "llm_total": len(llm_tuples),
        "intersection": len(inter),
        "only_in_llm": len(only_llm),
        "only_in_rules": len(only_rules),
        "overlap_recall": round(overlap, 4),
        "rules_by_type": rules.get("conflict_by_type", {}),
        "llm_by_type": llm.get("conflict_by_type", {}),
        "only_in_llm_examples": sorted(list(only_llm))[:20],
        "only_in_rules_examples": sorted(list(only_rules))[:20],
        "verification": {
            "llm_ge_1444": llm.get("n_conflicts", 0) >= 1444,
            "lactate_approx_1160": abs(
                llm.get("conflict_by_type", {}).get("乳酸酸中毒漏诊", 0) - 1160) <= 100,
            "overlap_gt_90pct": overlap > 0.90,
        },
    }
    json.dump(cmp, open(COMPARISON_JSON, "w"), ensure_ascii=False, indent=2)
    print(f"[对比] 规则={len(rules_tuples)} LLM={len(llm_tuples)} "
          f"交集={len(inter)} 重合度={overlap:.2%}")
    print(f"  only_in_llm={len(only_llm)} only_in_rules={len(only_rules)}")
    print(f"  验证: LLM>=1444={cmp['verification']['llm_ge_1444']} "
          f"乳酸≈1160={cmp['verification']['lactate_approx_1160']} "
          f"重合>90%={cmp['verification']['overlap_gt_90pct']}")
    print(f"  写入 {COMPARISON_JSON}")
    return cmp


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Ollama+Qwen2:7b MedTVT 血检冲突检测")
    ap.add_argument("--test", action="store_true", help="60 候选分层测试")
    ap.add_argument("--full", action="store_true", help="预筛 + 全量 LLM 判定")
    ap.add_argument("--compare", action="store_true", help="对比 LLM 与规则结果")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--csv", default=TRAIN_CSV)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    print(f"[数据] 读取 {args.csv}: {df.shape[0]} 行")
    if args.test:
        run_test(df, per_lab=12)
    if args.full:
        run_full(df, workers=args.workers, limit=args.limit)
    if args.compare:
        run_compare()
    if not (args.test or args.full or args.compare):
        ap.print_help()


if __name__ == "__main__":
    main()
