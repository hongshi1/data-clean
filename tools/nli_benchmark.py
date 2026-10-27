r"""NLI本地Benchmark: 4任务集 × N方法配置(模型×模板×方向) 统一评测.

任务集(固定数据, 全部来自已有资产 — 资产编排式):
  T1·误报复核    664银标分歧(649可构造) → compiler vs 真差异 (P/R/AUC)
  T2·真实矛盾    real_doc_findings 24条 → 零样本检出率(真实分布)
  T3·合成矛盾    eval_injected_v3 158负例 → 分通道检出率
  T4·正例防捷径  三族(恒等40/真实50/等效20) → 分族误报率

方法配置(可插拔注册表):
  模型: mdeberta / erlangshen / (330M与mnli-xnli下载后自动加入)
  模板: closed(闭世界) / plain(裸声明) — 仅T3声明对模板生效
  方向: bidirectional(双向对称) / unidirectional(单向)

报告: 方法×任务矩阵表 + 分通道明细 + runs协议落盘
用法: python tools/nli_benchmark.py [--models mdeberta,erlangshen] [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.nli_local import MODELS as NLI_MODELS, NliLocal  # noqa: E402
from run_utils import open_run  # noqa: E402

SILVER = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
SCENE_ADJ = BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json"
SC2_ADJ = BASE / "data/gjb_438c/anchor_sc2/llm_adjudication.json"
FINDINGS = BASE / "data/gjb_438c/data_assets/real_doc_findings.json"
INJECTED = BASE / "data/gjb_438c/data_assets/eval_injected_v3.json"
EVALSET_V2 = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"

_CHANNEL = {
    "TERM-01": "lexical", "TERM-02": "lexical", "TERM-04": "lexical",
    "TERM-05": "lexical", "TERM-07": "lexical", "TERM-08": "lexical",
    "TERM-03": "nli-strong", "TERM-06": "nli-strong",
    **{f"PARAM-{i:02d}": "nli-strong" for i in range(1, 11)},
    "LOGIC-03": "nli-weak", "LOGIC-04": "nli-weak", "LOGIC-05": "nli-strong",
    **{f"LOGIC-{i:02d}": "llm" for i in (1, 2, 6, 7, 8, 9, 10, 11)},
    **{f"GJB-{i:02d}": "syntax" for i in range(1, 12)},
}


# ══ 任务集构造(每任务返回 (声明对列表, 期望, 元数据)) ══

def load_t1() -> tuple[list, list, list]:
    """T1误报复核: 银标分歧驱动声明(649条可构造)."""
    from algorithms.consistency.nli_discrepancy_review import (
        PairContext,
        build_claims_for_discrepancy,
    )
    final = json.loads(SILVER.read_text(encoding="utf-8"))["final_labels"]
    src = {**json.loads(SCENE_ADJ.read_text(encoding="utf-8")),
           **json.loads(SC2_ADJ.read_text(encoding="utf-8"))}
    ctx = PairContext(BASE / "data/gjb_438c/pair_dataset")
    pairs, exps, metas = [], [], []
    for key, meta in final.items():
        disc = src.get(key)
        if disc is None:
            continue
        _, claim = build_claims_for_discrepancy(
            BASE / "data/gjb_438c/pair_dataset", disc["pair"], disc, ctx)
        if claim is None:
            continue
        pairs.append((claim.premise, claim.hypothesis))
        exps.append(0 if meta["label"] == "compiler_bug" else 1)  # 1=真差异
        metas.append({"key": key, "dtype": disc.get("dtype", "")})
    return pairs, exps, metas


def load_t2() -> tuple[list, list, list]:
    """T2真实矛盾: real_doc_findings的清单型矛盾(零样本)."""
    import re
    d = json.loads(FINDINGS.read_text(encoding="utf-8"))

    def _lst(ev: str) -> list:
        body = re.sub(r"^[^:：]*[:：]\s*", "", ev)
        return [x.strip().replace("\n", "") for x in re.split(r"[、,，]", body)
                if x.strip() and len(x.strip()) >= 2]
    pairs, exps, metas = [], [], []
    for f in d["findings"]:
        if f["type"] not in ("text_vs_graph", "enumeration_conflict"):
            continue
        ev = f.get("evidence", [])
        if len(ev) < 2:
            continue
        la, lb = _lst(ev[0]), _lst(ev[1])
        if len(la) < 2 or len(lb) < 2:
            continue
        p = f"文档正文规定，共{len(la)}项，包括：{'、'.join(la[:12])}，除此之外没有其他项。"
        h = f"图中显示，共{len(lb)}个节点，包括：{'、'.join(lb[:12])}，除此之外没有其他节点。"
        pairs.append((p, h))
        exps.append(1)
        metas.append({"type": f["type"]})
    return pairs, exps, metas


def load_t3() -> tuple[list, list, list]:
    """T3合成矛盾: eval_injected_v3负例158条(分通道)."""
    d = json.loads(INJECTED.read_text(encoding="utf-8"))

    def _as_text(v):
        if isinstance(v, list):
            return "、".join(str(x.get("name", x) if isinstance(x, dict) else x)
                             for x in v), True
        if isinstance(v, dict):
            return str(v.get("name", v)), False
        return str(v), isinstance(v, list)
    pairs, exps, metas = [], [], []
    for inj in d.get("injections", []):
        if inj.get("label") != "inconsistent":
            continue
        original, injected = inj.get("original"), inj.get("injected")
        if original is None or injected is None:
            continue
        oa, is_enum = _as_text(original)
        ob, _ = _as_text(injected)
        occs = inj.get("occurrences", [])
        sa = occs[0].get("section", "") if occs else ""
        sb = occs[1].get("section", "") if len(occs) > 1 else sa
        if is_enum:
            p = f"文档{sa}章节规定，共{len(oa.split('、'))}项：『{oa}』，除此之外没有其他项。"
            h = f"文档{sb}章节规定，共{len(ob.split('、'))}项：『{ob}』，除此之外没有其他项。"
        else:
            p = f"文档{sa}章节规定：『{oa}』。"
            h = f"文档{sb}章节规定：『{ob}』。"
        pairs.append((p, h))
        exps.append(1)
        metas.append({"channel": _CHANNEL.get(inj.get("check_item", ""), "?"),
                      "item": inj.get("check_item", "")})
    return pairs, exps, metas


def load_t4() -> tuple[list, list, list]:
    """T4正例防捷径: 三族(恒等40+真实50+等效20)."""
    pairs, exps, metas = [], [], []
    d = json.loads(INJECTED.read_text(encoding="utf-8"))
    for inj in d.get("injections", []):
        if inj.get("label") != "consistent":
            continue
        a, b = str(inj.get("original", "")), str(inj.get("injected", ""))
        occs = inj.get("occurrences", [])
        sa = occs[0].get("section", "") if occs else ""
        sb = occs[1].get("section", "") if len(occs) > 1 else sa
        pairs.append((f"文档{sa}章节规定：『{a}』。",
                      f"文档{sb}章节规定：『{b}』。"))
        exps.append(0)
        metas.append({"family": "恒等"})
    if EVALSET_V2.exists():
        es = json.loads(EVALSET_V2.read_text(encoding="utf-8"))
        for e in es.get("entries", []):
            if e.get("label") != "consistent":
                continue
            occs = (e.get("entity") or {}).get("occurrences", [])
            if len(occs) < 2:
                continue
            inj = e.get("injection") or {}
            a = str(inj.get("original", occs[0].get("content", "")))
            b = str(inj.get("injected", occs[1].get("content", "")))
            sa = occs[0].get("section", "")
            sb = occs[1].get("section", "")
            pairs.append((f"文档{sa}章节规定：『{a}』。",
                          f"文档{sb}章节规定：『{b}』。"))
            exps.append(0)
            metas.append({"family": "真实多模态"})
    import random
    rng = random.Random(42)
    CONV = [("秒", "ms", 1000.0), ("s", "ms", 1000.0), ("分钟", "秒", 60.0),
            ("GB", "MB", 1024.0)]
    vals = [0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 100, 200, 500, 1000]
    for _ in range(20):
        val, (u1, u2, factor) = rng.choice(vals), rng.choice(CONV)
        a, b = f"{val:g}{u1}", f"{val * factor:g}{u2}"
        pairs.append((f"文档规定：『{a}』。", f"文档另一处规定：『{b}』。"))
        exps.append(0)
        metas.append({"family": "单位等效"})
    return pairs, exps, metas


# ══ 评测逻辑 ══

def eval_task(verdicts: list[dict], exps: list[int],
              bidirectional: bool) -> dict[str, Any]:
    """一个方法在一个任务上的指标."""
    if bidirectional:
        preds = [1 if v["sym_contra"] else 0 for v in verdicts]
        scores = [v["contra_score"] for v in verdicts]
    else:
        preds = [1 if v["fwd"]["label"] == "contradiction" else 0
                 for v in verdicts]
        scores = [v["fwd"]["p_contra"] for v in verdicts]
    n = len(exps)
    tp = sum(1 for p, e in zip(preds, exps) if p == 1 and e == 1)
    fp = sum(1 for p, e in zip(preds, exps) if p == 1 and e == 0)
    fn = sum(1 for p, e in zip(preds, exps) if p == 0 and e == 1)
    tn = sum(1 for p, e in zip(preds, exps) if p == 0 and e == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    # AUC (rank)
    pos = [s for s, e in zip(scores, exps) if e == 1]
    neg = [s for s, e in zip(scores, exps) if e == 0]
    if pos and neg:
        ranks = sorted((s, i) for i, s in enumerate(scores))
        rank_of = [0.0] * len(scores)
        i = 0
        while i < len(ranks):
            j = i
            while j < len(ranks) and ranks[j][0] == ranks[i][0]:
                j += 1
            avg = (i + j + 1) / 2.0
            for k in range(i, j):
                rank_of[ranks[k][1]] = avg
            i = j
        r_pos = sum(rank_of[i] for i, e in enumerate(exps) if e == 1)
        auc = (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    else:
        auc = 0.5
    return {"n": n, "precision": round(precision, 4),
            "recall": round(recall, 4), "auc": round(auc, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="mdeberta,erlangshen")
    ap.add_argument("--directions", default="bidirectional,unidirectional")
    ap.add_argument("--quick", action="store_true", help="任务集抽样快跑")
    args = ap.parse_args()

    # 可用模型: 注册表内且权重完整(>100MB)
    def _model_ready(key: str) -> bool:
        d = Path(NLI_MODELS[key]["dir"])
        if not d.exists():
            return False
        return any(f.stat().st_size > 100 * 1024 * 1024
                   for f in d.iterdir()
                   if f.suffix in (".bin", ".safetensors"))
    avail = {k: v for k, v in NLI_MODELS.items() if _model_ready(k)}
    models = [m.strip() for m in args.models.split(",") if m.strip() in avail]
    print(f"模型: {models} (可用: {list(avail)}+新下载)")

    tasks = {"T1误报复核": load_t1, "T2真实矛盾": load_t2,
             "T3合成矛盾": load_t3, "T4正例防捷径": load_t4}
    if args.quick:
        for name, loader in list(tasks.items()):
            full = loader()
            k = 60
            tasks[name] = lambda f=full, k=k: (f[0][:k], f[1][:k], f[2][:k])

    results: dict[str, dict] = {}
    nli_cache: dict[str, NliLocal] = {}
    for model in models:
        for direction in args.directions.split(","):
            bidi = direction == "bidirectional"
            tag = f"{model}|{'双向' if bidi else '单向'}"
            print(f"\n══ {tag} ══")
            if model not in nli_cache:
                nli_cache[model] = NliLocal(model)
                mode = nli_cache[model].ensure()
                if mode == "unavailable":
                    print(f"  SKIP: {nli_cache[model].last_error}")
                    continue
            nli = nli_cache[model]
            results[tag] = {}
            for tname, loader in tasks.items():
                pairs, exps, metas = loader()
                if not pairs:
                    results[tag][tname] = {"n": 0}
                    continue
                if bidi:
                    verdicts = nli.predict_bidirectional(pairs)
                else:
                    fwd = nli.predict(pairs)
                    verdicts = [{"fwd": v, "sym_contra":
                                 v["label"] == "contradiction",
                                 "contra_score": v["p_contra"]} for v in fwd]
                m = eval_task(verdicts, exps, bidi)
                results[tag][tname] = m
                print(f"  {tname}: n={m['n']} P={m['precision']:.3f} "
                      f"R={m['recall']:.3f} AUC={m['auc']:.3f}"
                      + (f" fp={m['fp']}" if tname.startswith("T4") else ""))
                # T3分通道/T4分族
                if tname.startswith("T3"):
                    by_ch: dict[str, list[int]] = defaultdict(list)
                    for v, e, meta in zip(verdicts, exps, metas):
                        hit = 1 if (v["sym_contra"] if bidi else
                                    v["fwd"]["label"] == "contradiction") else 0
                        by_ch[meta["channel"]].append(hit)
                    results[tag][tname + "_by_channel"] = {
                        ch: f"{sum(v)}/{len(v)}" for ch, v in by_ch.items()}
                if tname.startswith("T4"):
                    by_fam: dict[str, list[int]] = defaultdict(list)
                    for v, e, meta in zip(verdicts, exps, metas):
                        fp = 1 if (v["sym_contra"] if bidi else
                                   v["fwd"]["label"] == "contradiction") else 0
                        by_fam[meta["family"]].append(fp)
                    results[tag][tname + "_by_family"] = {
                        fam: f"{sum(v)}/{len(v)}" for fam, v in by_fam.items()}

    # 矩阵总表
    print("\n" + "═" * 72)
    print("NLI Benchmark 方法×任务矩阵 (P/R/AUC; T4为误报率)")
    print("═" * 72)
    header = ["方法", "T1误报复核", "T2真实矛盾", "T3合成矛盾", "T4防捷径"]
    print(f"{header[0]:<22} {header[1]:<14} {header[2]:<14} "
          f"{header[3]:<14} {header[4]:<14}")
    for tag, tr in results.items():
        cells = []
        for tname in ("T1误报复核", "T2真实矛盾", "T3合成矛盾", "T4正例防捷径"):
            m = tr.get(tname, {})
            if tname.startswith("T4"):
                fam = tr.get(tname + "_by_family", {})
                fps = sum(int(x.split("/")[0]) for x in fam.values())
                tot = sum(int(x.split("/")[1]) for x in fam.values())
                cells.append(f"{fps/tot:.1%}误报" if tot else "-")
            elif m.get("n"):
                cells.append(f"{m['precision']:.2f}/{m['recall']:.2f}/"
                             f"{m['auc']:.2f}")
            else:
                cells.append("-")
        print(f"{tag:<22} {cells[0]:<14} {cells[1]:<14} {cells[2]:<14} "
              f"{cells[3]:<14}")

    run = open_run("nli_benchmark", {
        "models": models, "directions": args.directions.split(","),
        "quick": args.quick})
    run.save_result(results)
    print(f"\nresult → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
