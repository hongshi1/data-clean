r"""LLM零样本基线: 在公开NLI集/合成基准/人工金标上跑GLM-5判定(全程cache).

用途: 论文对比实验的基线3(zero-shot LLM)
  batch=xnli    XNLI-zh 300条(100/类, seed42)
  batch=ocnli   OCNLI 300条(100/类, seed42)
  batch=bench   合成基准test分层采样300条(seed42)
  batch=gold    人工金标23条
  batch=table   汇总输出对比表(不调LLM)

用法: python tools/llm_baseline_eval.py xnli
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

from algorithms.common.llm_client import llm_json  # noqa: E402

PUB = BASE / "data/gjb_438c/public_nli"
OUT = BASE / "data/gjb_438c/public_nli/llm_baseline"
OUT.mkdir(parents=True, exist_ok=True)

NLI_PROMPT = """你是自然语言推理(NLI)判定器。判断前提(P)与假设(H)的关系, 只输出JSON。
规则: H与P矛盾 → {{"label": "contradiction"}}
      H能从P推出 → {{"label": "entailment"}}
      其余/无法确定 → {{"label": "neutral"}}

前提: {p}
假设: {h}"""

INC_PROMPT = """你是软件需求文档(SRS)一致性审查员。判断两个陈述是否一致, 只输出JSON。
规则: 两者对同一事物给出矛盾描述(值/顺序/术语/范围/组成不同, 或一方缺失关键内容) → {{"label": "inconsistent"}}
      两者一致或可共存 → {{"label": "consistent"}}

陈述1: {p}
陈述2: {h}"""


def _load_pub(name: str, n_per_class: int = 100) -> list[dict]:
    items = [json.loads(line) for line in open(PUB / f"{name}_std.jsonl", encoding="utf-8") if line.strip()]
    items = [x for x in items if x["gold"] in ("entailment", "neutral", "contradiction") and x["premise"] and x["hypothesis"]]
    by = defaultdict(list)
    for x in items:
        by[x["gold"]].append(x)
    sample = []
    for lab in ("entailment", "neutral", "contradiction"):
        random.Random(42).shuffle(by[lab])
        sample.extend(by[lab][:n_per_class])
    random.Random(42).shuffle(sample)
    return sample


def _bench_sample(n: int = 300) -> list[dict]:
    items = [json.loads(line) for line in open(BASE / "data/gjb_438c/benchmark_full_v2.jsonl", encoding="utf-8")]
    test = [it for it in items if it["split"] == "test"]
    neg = [it for it in test if it["expected_label"] == "inconsistent"]
    pos = [it for it in test if it["expected_label"] == "consistent"]
    # 按类型分层(保持全集比例), 正例全取后不足按比例补
    by_ci = defaultdict(list)
    for it in neg:
        by_ci[it["check_item"]].append(it)
    random.Random(42).shuffle(pos)
    n_neg = min(len(neg), int(n * len(neg) / len(test)))
    sample = pos[: n - n_neg] if n_neg < n else pos[: max(n - n_neg, 1)]
    random.Random(42).shuffle(neg)
    # 分层: 每类型按比例取
    taken = 0
    for ci, lst in sorted(by_ci.items()):
        k = max(1, round(len(lst) * n_neg / len(neg)))
        k = min(k, len(lst), n_neg - taken if n_neg - taken > 0 else 0)
        if k <= 0:
            continue
        random.Random(42).shuffle(lst)
        sample.extend(lst[:k])
        taken += k
    random.Random(42).shuffle(sample)
    return sample


def _gold_items() -> list[dict]:
    tasks = json.loads((BASE / "data/gjb_438c/anchor_sc2/adjudication/adjudication_tasks.json").read_text(encoding="utf-8"))
    gold = json.loads((BASE / "data/gjb_438c/human_gold/final_gold_86.json").read_text(encoding="utf-8"))["labels"]
    tier1 = json.loads((BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies_v2.json").read_text(encoding="utf-8"))
    out = []
    for t in tasks:
        lab = gold.get(t["task_id"], {}).get("label", "")
        if lab not in ("real_bug", "benign_variation"):
            continue
        ds_list = tier1.get(t["pair_key"], {}).get("discrepancies", [])
        ts, dside = t.get("table_side"), t.get("diag_side")
        for d in ds_list:
            if d["evidence"] == t["evidence"]:
                ts = d.get("table_side") or ts
                dside = d.get("diag_side") or dside
                break
        uc, dt = t.get("uc_name", ""), t["dtype"]
        if dt == "ORDER_CONFLICT":
            p = f"表格规定{uc}用例的执行顺序为{(ts or {}).get('seq', '依次执行')}。"
            h = f"流程图规定的执行顺序为{(dside or {}).get('edge', '相反方向')}，与表格不一致。"
        elif dt == "STEP_MISSING":
            p = f"{uc}用例的表格规定步骤「{str((ts or {}).get('text', ''))[:80]}」。"
            h = "流程图中没有与该步骤对应的节点。"
        elif dt == "ACTOR_MISSING":
            p = f"{uc}用例的表格规定参与者为「{str((ts or {}).get('text', ''))[:30]}」。"
            h = "流程图中没有绘制参与者节点。"
        elif dt == "EXC_MISSING":
            p = f"{uc}用例的表格规定异常流{(ts or {}).get('eid', 'E1')}「{str((ts or {}).get('text', ''))[:80]}」。"
            h = "流程图中没有该异常分支。"
        else:
            p = f"流程图中包含节点「{str((dside or {}).get('text', ''))[:80]}」。"
            h = f"{uc}用例的表格中没有对应的步骤描述。"
        out.append({"premise": p, "hypothesis": h,
                    "gold": "inconsistent" if lab == "real_bug" else "consistent"})
    return out


def run_llm(items: list[dict], mode: str, batch: str) -> list[dict]:
    """mode: 'nli'(三分类) 或 'inc'(一致/不一致)."""
    results = []
    for i, x in enumerate(items):
        prompt = (NLI_PROMPT if mode == "nli" else INC_PROMPT).format(p=x["premise"], h=x["hypothesis"])
        try:
            parsed, _model = llm_json(prompt, cache=True)
            lab = str((parsed or {}).get("label", "?")).lower()
        except Exception as e:  # 网络等异常: 记录不中断
            lab = f"error:{type(e).__name__}"
        results.append({"gold": x["gold"], "pred": lab, "i": i})
        if (i + 1) % 50 == 0:
            print(f"  {batch} {i + 1}/{len(items)}")
    return results


def prf(ys, ps, positive):
    tp = sum(1 for y, p in zip(ys, ps) if y == positive and p == positive)
    fp = sum(1 for y, p in zip(ys, ps) if y != positive and p == positive)
    fn = sum(1 for y, p in zip(ys, ps) if y == positive and p != positive)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"P": round(prec, 3), "R": round(rec, 3), "F1": round(f1, 3), "tp": tp, "fp": fp, "fn": fn}


def main() -> None:
    batch = sys.argv[1] if len(sys.argv) > 1 else "table"

    if batch == "xnli":
        items = _load_pub("xnli_zh")
        res = run_llm(items, "nli", batch)
        json.dump(res, open(OUT / "xnli_llm.json", "w", encoding="utf-8"), ensure_ascii=False)
        ys = [r["gold"] for r in res]
        ps = [r["pred"] for r in res]
        acc = sum(1 for y, p in zip(ys, ps) if y == p) / len(res)
        print(f"XNLI-zh LLM: acc={acc:.3f}, 矛盾F1={prf(ys, ps, 'contradiction')}")
    elif batch == "ocnli":
        items = _load_pub("ocnli")
        res = run_llm(items, "nli", batch)
        json.dump(res, open(OUT / "ocnli_llm.json", "w", encoding="utf-8"), ensure_ascii=False)
        ys = [r["gold"] for r in res]
        ps = [r["pred"] for r in res]
        acc = sum(1 for y, p in zip(ys, ps) if y == p) / len(res)
        print(f"OCNLI LLM: acc={acc:.3f}, 矛盾F1={prf(ys, ps, 'contradiction')}")
    elif batch == "bench":
        items = _bench_sample(300)
        json.dump([{k: it[k] for k in ("premise", "hypothesis", "expected_label", "check_item")}
                   for it in items], open(OUT / "bench_sample_300.json", "w", encoding="utf-8"),
                  ensure_ascii=False)
        norm = [{"premise": it["premise"], "hypothesis": it["hypothesis"], "gold": it["expected_label"]} for it in items]
        res = run_llm(norm, "inc", batch)
        json.dump(res, open(OUT / "bench_llm.json", "w", encoding="utf-8"), ensure_ascii=False)
        ys = [r["gold"] for r in res]
        ps = [r["pred"] for r in res]
        print(f"基准300 LLM: 不一致F1={prf(ys, ps, 'inconsistent')}, 预测分布={dict(Counter(ps))}")
    elif batch == "gold":
        items = _gold_items()
        res = run_llm(items, "inc", batch)
        json.dump(res, open(OUT / "gold_llm.json", "w", encoding="utf-8"), ensure_ascii=False)
        ys = [r["gold"] for r in res]
        ps = [r["pred"] for r in res]
        print(f"金标23 LLM: 矛盾F1={prf(ys, ps, 'inconsistent')}, 预测分布={dict(Counter(ps))}")
    elif batch == "table":
        _print_table()
    else:
        raise SystemExit(f"未知batch: {batch}")


def _print_table() -> None:
    print("已保存的LLM基线结果:")
    for f in sorted(OUT.glob("*_llm.json")):
        res = json.load(open(f, encoding="utf-8"))
        ys = [r["gold"] for r in res]
        ps = [r["pred"] for r in res]
        acc = sum(1 for y, p in zip(ys, ps) if y == p) / len(res)
        positive = "contradiction" if res and res[0]["gold"] == "contradiction" or (res and res[0]["gold"] in ("entailment", "neutral")) else "inconsistent"
        m = prf(ys, ps, positive)
        print(f"  {f.stem}: n={len(res)}, acc={acc:.3f}, {positive}F1={m}")


if __name__ == "__main__":
    main()
