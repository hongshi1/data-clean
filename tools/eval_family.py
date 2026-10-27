r"""Task 1 最终实验 v3: family_evalset_v1 完整评测体系(六张表).

表1 通用方法主表(全896条×六族): 我方 + 领域训练基线(TSRCDF-SS/v12) + 零样本NLI + 级联 + [GLM抽样]
表2 分族专家全族矩阵: 五族专家+QG-QA在全部族上(单族专家跨族泛化失败证据)
表3 通道消融: full / -numeric / -quote / -enum / -v4.2三通道 / 纯NLI
表4 同义异表细分: A/D/F族 → 同值异表面(consistent) vs 突变(inconsistent)子集
表5 效率与提前检出: 每方法耗时 + 通道命中 + NLI节省
表6 非同任务参考 + GLM变体细析(如有)
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

FAM_ORDER = ["A", "B", "C", "D", "E", "F"]
FAM_NAMES = {"A": "A数值", "B": "B顺序", "C": "C结构", "D": "D术语", "E": "E合规", "F": "F语义"}


def bacc(preds: list[str], golds: list[str]) -> float:
    n_pos = golds.count("inconsistent")
    n_neg = golds.count("consistent")
    if n_pos and n_neg:
        tp = sum(1 for p, g in zip(preds, golds) if p == g == "inconsistent")
        tn = sum(1 for p, g in zip(preds, golds) if p == g == "consistent")
        return (tp / n_pos + tn / n_neg) / 2
    return sum(1 for p, g in zip(preds, golds) if p == g) / max(len(golds), 1)


def metric(preds: list[str], golds: list[str]) -> float:
    return bacc(preds, golds) if len(set(golds)) == 2 else \
        sum(1 for p, g in zip(preds, golds) if p == g) / max(len(golds), 1)


def bootstrap_ci(preds: list[str], golds: list[str], n: int = 2000, seed: int = 42) -> tuple[float, float]:
    rng = random.Random(seed)
    stats = []
    data = list(zip(preds, golds))
    for _ in range(n):
        sample = [data[rng.randrange(len(data))] for _ in range(len(data))]
        stats.append(bacc([x[0] for x in sample], [x[1] for x in sample]))
    stats.sort()
    return stats[int(0.025 * n)], stats[int(0.975 * n)]


def mcnemar_p(b01: int, b10: int) -> float:
    import math
    n = b01 + b10
    if n == 0:
        return 1.0
    z = (abs(b01 - b10) - 1) / math.sqrt(n)
    return math.erfc(z / math.sqrt(2))


# ═══ TSRCDF-SS推理 ═══
def tsrcdfss_predict(data: list[dict]) -> list[str]:
    import torch
    from tools.train_tsrcdfss import DualEncoderClassifier
    from transformers import AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok_p = AutoTokenizer.from_pretrained(str(BASE / "models/embedding/bge-large-zh-v1.5"), local_files_only=True)
    tok_h = AutoTokenizer.from_pretrained(str(BASE / "models/embedding/bge-m3"), local_files_only=True)
    model = DualEncoderClassifier(str(BASE / "models/embedding/bge-large-zh-v1.5"),
                                   str(BASE / "models/embedding/bge-m3")).to(device)
    state = torch.load(str(BASE / "models/nli/tsrcdfss-baseline/model.pt"),
                       map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(data), 16):
            batch = data[i:i + 16]
            logits = model(tok_p, tok_h, [x["premise"] for x in batch],
                           [x["hypothesis"] for x in batch], device)
            preds.extend("inconsistent" if int(r.argmax()) == 1 else "consistent" for r in logits)
    return preds


def main() -> None:
    t0 = time.time()
    data = json.loads((BASE / "data/gjb_438c/family_evalset_v1.json").read_text(encoding="utf-8"))["pairs"]
    golds = [x["label"] for x in data]
    fam_idx = {f: [i for i, x in enumerate(data) if x["family"] == f] for f in FAM_ORDER}
    results: dict[str, list[str]] = {}
    timers: dict[str, float] = {}

    # ── 1. 我方 + 通道记录 ──
    from algorithms.consistency.checker import ConsistencyChecker
    ck = ConsistencyChecker()
    t = time.time()
    chan_records = [ck.check(x["premise"], x["hypothesis"]) for x in data]
    results["Ours(v4.2+领域知识+v12)"] = [r.verdict for r in chan_records]
    timers["Ours"] = time.time() - t
    print(f"Ours done ({time.time() - t0:.0f}s)")

    # ── 2. TSRCDF-SS(领域训练基线) ──
    t = time.time()
    results["TSRCDF-SS(2025复现)"] = tsrcdfss_predict(data)
    timers["TSRCDF-SS"] = time.time() - t
    print(f"TSRCDF-SS done ({time.time() - t0:.0f}s)")

    # ── 3. 零样本NLI ──
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    def zs_nli(model_name: str, key: str, contra_idx: int) -> None:
        t = time.time()
        mdir = str(BASE / f"models/nli/{model_name}")
        tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device).eval()
        preds = []
        with torch.no_grad():
            for i in range(0, len(data), 32):
                batch = data[i:i + 32]
                enc = tok([x["premise"] for x in batch], [x["hypothesis"] for x in batch],
                          padding=True, truncation=True, max_length=128,
                          return_tensors="pt").to(device)
                logits = model(**enc).logits
                preds.extend("inconsistent" if int(r.argmax()) == contra_idx else "consistent"
                             for r in logits)
        results[key] = preds
        timers[key] = time.time() - t
        print(f"{key} done ({time.time() - t0:.0f}s)")

    zs_nli("mDeBERTa-v3-base-xnli-multilingual-nli-2mil7", "mDeBERTa ZS", 2)
    zs_nli("Erlangshen-Roberta-330M-NLI", "Erlangshen ZS", 0)

    # ── 4. v12纯NLI(我方NLI组件) ──
    t = time.time()
    ck12 = ConsistencyChecker()
    results["v12 pure NLI"] = [ck12._check_nli(x["premise"], x["hypothesis"]).verdict for x in data]
    timers["v12 pure"] = time.time() - t
    print(f"v12 pure done ({time.time() - t0:.0f}s)")

    # ── 5. 级联组合(朴素: 形式化/规则先判, NLI兜底) ──
    from algorithms.consistency.baselines import (cascade_rules_nli, cascade_z3_nli)
    nli_fn = lambda p, h: ck12._check_nli(p, h).verdict  # noqa: E731
    t = time.time()
    results["Z3→NLI级联"] = [cascade_z3_nli(x["premise"], x["hypothesis"], nli_fn) for x in data]
    timers["Z3→NLI"] = time.time() - t
    t = time.time()
    results["Rules→NLI级联"] = [cascade_rules_nli(x["premise"], x["hypothesis"], nli_fn) for x in data]
    timers["Rules→NLI"] = time.time() - t
    print(f"级联 done ({time.time() - t0:.0f}s)")

    # ── 6. GLM抽样(如有结果文件) ──
    glm_meta = None
    glm_path = BASE / "data/gjb_438c/glm_baseline_sample.json"
    if glm_path.exists():
        glm = json.loads(glm_path.read_text(encoding="utf-8"))
        glm_meta = glm["meta"]
        sample_ids = glm_meta["sample_ids"]
        for variant, preds in glm["predictions"].items():
            full_preds = []
            sample_pos = {sid: k for k, sid in enumerate(sample_ids)}
            for x in data:
                if x["id"] in sample_pos:
                    full_preds.append(preds[sample_pos[x["id"]]])
                else:
                    full_preds.append("")
            results[f"{variant}(抽样{len(sample_ids)})"] = full_preds
        print(f"GLM抽样合并({len(glm['predictions'])}变体)")

    # ═══ 表1: 通用方法主表 ═══
    print("\n" + "═" * 30 + " 表1 通用方法主表 " + "═" * 30)
    print(f"{'方法':<30}" + "".join(f"{FAM_NAMES[f]:>9}" for f in FAM_ORDER) + f"{'总体':>9}")
    table1 = {}
    glm_rows = {}
    for name, preds in results.items():
        row = {}
        for f in FAM_ORDER:
            idx = fam_idx[f]
            row[f] = round(metric([preds[i] for i in idx], [golds[i] for i in idx]), 3)
        if any(p == "" for p in preds):
            # GLM抽样: 只在抽样子集上报
            sp = [i for i, p in enumerate(preds) if p != ""]
            row = {}
            for f in FAM_ORDER:
                idx = [i for i in fam_idx[f] if i in set(sp)]
                row[f] = round(metric([preds[i] for i in idx], [golds[i] for i in idx]), 3)
            row["overall"] = round(bacc([preds[i] for i in sp], [golds[i] for i in sp]), 3)
            glm_rows[name] = row
            line = f"{name:<30}" + "".join(f"{row[f]:>9.3f}" for f in FAM_ORDER) + f"{row['overall']:>9.3f}*"
            print(line + " (抽样)")
            continue
        overall = bacc(preds, golds)
        row["overall"] = round(overall, 3)
        table1[name] = row
        print(f"{name:<30}" + "".join(f"{row[f]:>9.3f}" for f in FAM_ORDER) + f"{overall:>9.3f}")

    # ═══ 表2: 分族专家全族矩阵(泛化失败证据) ═══
    print("\n" + "═" * 30 + " 表2 专家全族矩阵 " + "═" * 30)
    from algorithms.consistency.baselines import (baseline_editdist_lex, baseline_gjb_engine,
                                                   baseline_lcs, baseline_qg_qa, baseline_set,
                                                   baseline_z3)
    experts = {"Z3-SMT": baseline_z3, "LCS序列": baseline_lcs, "集合比对": baseline_set,
               "编辑距离+词典": baseline_editdist_lex, "GJB规则引擎": baseline_gjb_engine,
               "QG-QA": baseline_qg_qa}
    table2 = {}
    for name, fn in experts.items():
        preds = [fn(x["premise"], x["hypothesis"]) for x in data]
        row = {f: round(metric([preds[i] for i in fam_idx[f]], [golds[i] for i in fam_idx[f]]), 3)
               for f in FAM_ORDER}
        row["overall"] = round(bacc(preds, golds), 3)
        table2[name] = row
        print(f"{name:<14}" + "".join(f"{row[f]:>9.3f}" for f in FAM_ORDER) + f"{row['overall']:>9.3f}")

    # ═══ 表3: 通道消融 ═══
    print("\n" + "═" * 30 + " 表3 通道消融 " + "═" * 30)

    class Abl:
        def __init__(self, disable: set[str]):
            from algorithms.consistency.checker import ConsistencyChecker as CC
            from algorithms.consistency.checker import strip_negation
            self._c = CC()
            self._strip = strip_negation
            # 顺序必须与checker.py check()一致(v4.2.1: count/absence在enum前)
            self._fns = {"numeric": self._c._check_numeric, "quote": self._c._check_quote,
                         "term": self._c._check_term, "count": self._c._check_count,
                         "doc_absence": self._c._check_doc_absence,
                         "numbered": self._c._check_numbered, "enum": self._c._check_enum,
                         "sequence": self._c._check_sequence}
            self._disable = disable

        def check(self, prem: str, hyp: str) -> str:
            p, h = self._strip(prem), self._strip(hyp)
            for name, fn in self._fns.items():
                if name in self._disable:
                    continue
                r = fn(p, h)
                if r:
                    return r.verdict
            return self._c._check_nli(prem, hyp).verdict

    ablations = {
        "full v4.3": set(),
        "−numbered": {"numbered"},
        "−numeric": {"numeric"},
        "−quote": {"quote"},
        "−enum": {"enum"},
        "−v4.2三通道": {"count", "doc_absence", "sequence"},
        "纯NLI(v3形态)": {"numeric", "quote", "term", "enum", "count", "doc_absence", "sequence"},
    }
    table3 = {}
    for cfg, disable in ablations.items():
        ab = Abl(disable)
        preds = [ab.check(x["premise"], x["hypothesis"]) for x in data]
        row = {f: round(metric([preds[i] for i in fam_idx[f]], [golds[i] for i in fam_idx[f]]), 3)
               for f in FAM_ORDER}
        row["overall"] = round(bacc(preds, golds), 3)
        table3[cfg] = row
        print(f"{cfg:<16}" + "".join(f"{row[f]:>9.3f}" for f in FAM_ORDER) + f"{row['overall']:>9.3f}")

    # ═══ 表4: 同义异表细分(A/D/F族: 同值异表面 vs 突变) ═══
    print("\n" + "═" * 30 + " 表4 同义异表细分 " + "═" * 30)
    kd_rows = {}
    for fam in ("A", "D", "F"):
        idx = fam_idx[fam]
        con_idx = [i for i in idx if golds[i] == "consistent"]
        inc_idx = [i for i in idx if golds[i] == "inconsistent"]
        for label_name, sub in (("同值异表面", con_idx), ("突变/缺失", inc_idx)):
            for mname in ("Ours(v4.2+领域知识+v12)", "TSRCDF-SS(2025复现)", "mDeBERTa ZS",
                          "Erlangshen ZS", "v12 pure NLI"):
                preds = results[mname]
                acc = sum(1 for i in sub if preds[i] == golds[i]) / max(len(sub), 1)
                kd_rows[f"{fam}|{label_name}|{mname}"] = round(acc, 3)
    for fam in ("A", "D", "F"):
        idx = fam_idx[fam]
        con_idx = [i for i in idx if golds[i] == "consistent"]
        inc_idx = [i for i in idx if golds[i] == "inconsistent"]
        print(f"  {FAM_NAMES[fam]}: 同值异表面n={len(con_idx)}, 突变n={len(inc_idx)}")
        for mname in ("Ours(v4.2+领域知识+v12)", "TSRCDF-SS(2025复现)", "mDeBERTa ZS", "v12 pure NLI"):
            preds = results[mname]
            a1 = sum(1 for i in con_idx if preds[i] == golds[i]) / max(len(con_idx), 1)
            a2 = sum(1 for i in inc_idx if preds[i] == golds[i]) / max(len(inc_idx), 1)
            print(f"    {mname:<28} 同值异表面={a1:.3f} 突变={a2:.3f}")

    # ═══ 表5: 效率与提前检出 ═══
    print("\n" + "═" * 30 + " 表5 效率与提前检出 " + "═" * 30)
    n_nli_calls = sum(1 for r in chan_records if r.channel == "nli")
    det_hit = sum(1 for r in chan_records if r.channel != "nli")
    depth = defaultdict(Counter)
    DEPTH = {"numeric": 1, "quote": 2, "term": 3, "enum": 4, "count": 5,
             "compliance": 5, "sequence": 5, "verify": 6, "nli": 7}
    for i, x in enumerate(data):
        depth[x["family"]][DEPTH.get(chan_records[i].channel, 7)] += 1
    table5 = {
        "per_method_seconds": {k: round(v, 1) for k, v in timers.items()},
        "channel_hit": dict(Counter(r.channel for r in chan_records)),
        "nli_calls": n_nli_calls, "nli_saved_pct": round(det_hit / len(data) * 100, 1),
        "depth_by_family": {f: dict(sorted(depth[f].items())) for f in FAM_ORDER},
    }
    print(f"  通道命中: {table5['channel_hit']}")
    print(f"  NLI调用量: {n_nli_calls}/{len(data)} (节省{table5['nli_saved_pct']}%)")
    print(f"  各方法耗时(s): {table5['per_method_seconds']}")

    # ═══ 表6: 非同任务参考 ═══
    surface_refs = {}
    for x in data:
        pass

    def char2gram(t: str) -> set[str]:
        t = re.sub(r"\s", "", t)
        return {t[i:i + 2] for i in range(len(t) - 1)}
    tf = []
    for x in data:
        pg, hg = char2gram(x["premise"]), char2gram(x["hypothesis"])
        inter = len(pg & hg) / max(len(pg), len(hg)) if pg and hg else 1.0
        tf.append("inconsistent" if inter < 0.8 else "consistent")
    surface_refs["TF-IDF(非同任务)"] = {f: round(metric([tf[i] for i in fam_idx[f]],
                                                        [golds[i] for i in fam_idx[f]]), 3)
                                       for f in FAM_ORDER}
    surface_refs["TF-IDF(非同任务)"]["overall"] = round(bacc(tf, golds), 3)

    # McNemar + bootstrap
    ours = results["Ours(v4.2+领域知识+v12)"]
    lo, hi = bootstrap_ci(ours, golds)
    print(f"\n总体bAcc 95%CI: [{lo:.3f}, {hi:.3f}]")
    mcn = {}
    for f in FAM_ORDER:
        idx = fam_idx[f]
        ours_f = [ours[i] for i in idx]
        for rival in ("TSRCDF-SS(2025复现)", "v12 pure NLI"):
            rf = [results[rival][i] for i in idx]
            gold_f = [golds[i] for i in idx]
            b01 = sum(1 for a, b, g in zip(ours_f, rf, gold_f) if a == g and b != g)
            b10 = sum(1 for a, b, g in zip(ours_f, rf, gold_f) if a != g and b == g)
            if b01 + b10 > 0:
                mcn[f"{f}|{rival}"] = {"win": b01, "lose": b10, "p": round(mcnemar_p(b01, b10), 4)}
    for k, v in mcn.items():
        print(f"  McNemar {k}: win={v['win']} lose={v['lose']} p={v['p']}")

    # 保存
    from run_utils import open_run
    run = open_run("family_eval_v3", {
        "数据集": "family_evalset_v1(896条六族)",
        "表结构": "表1通用主表/表2专家全族/表3消融/表4κD细分/表5效率/表6参考",
        "基线": "TSRCDF-SS复现+级联+QG-QA+零样本NLI+v12(+GLM抽样如有)"})
    run.save_result({
        "table1_general": table1, "table1_glm_sampled": glm_rows,
        "table2_experts_allfamilies": table2, "table3_ablation": table3,
        "table4_kd_split": kd_rows, "table5_efficiency": table5,
        "table6_nontask_refs": surface_refs,
        "bootstrap_ci": [round(lo, 3), round(hi, 3)],
        "mcnemar": mcn, "timers": timers})
    print(f"\nsaved → {run.path}")



if __name__ == "__main__":
    main()
