r"""v19实验: canonical锚点 ∪ synth_s1@族配额 重训NLI(数据点火实验).

协议(扩容计划P1.3):
  - 训练: anchor(v12同款过滤) + synth_s1子集(族配额, 合成:真实≈2:1)
  - 族配额: PARAM-01≤40%, PARAM-03≤25%, TERM/ENUM≈35%(同值异表面族为主)
  - gate集: synth_s1分层留出10%(棘轮门控, 与终点报告集分离)
  - 终点: clean130/md166只测一次
输出: models/nli/roberta-v19-mixed + gate评测结果
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

SEED = 42
SYNTH_TOTAL = 1600
GATE_FRAC = 0.1


def build_mix() -> tuple[list[dict], list[dict], dict]:
    """返回(train_mix, gate_set, 统计)."""
    rng = random.Random(SEED)

    # 1. anchor(与v12完全同款过滤)
    PD = BASE / "data/gjb_438c/pair_dataset_canonical"
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]
    anchor = [x for x in train if x["source"] == "srs_anchor"
              and "evidence_refuted" not in x.get("quality", {}).get("flags", [])
              and not str(x.get("context", {}).get("doc", "")).startswith("02")]
    print(f"anchor: {len(anchor)}条(与v12训练同款过滤)")

    # 2. synth_s1分层切分(gate留出10%)
    s1 = json.loads((BASE / "data/gjb_438c/synth_s1_pairs.json").read_text(encoding="utf-8"))["pairs"]
    by_type = defaultdict(list)
    for p in s1:
        by_type[p["type"]].append(p)
    train_synth, gate = [], []
    for t, pairs in sorted(by_type.items()):
        rng.shuffle(pairs)
        n_gate = max(1, int(len(pairs) * GATE_FRAC))
        gate.extend(pairs[:n_gate])
        train_synth.extend(pairs[n_gate:])
    print(f"synth_s1: 训练池{len(train_synth)} + gate{len(gate)}(分层{GATE_FRAC:.0%})")

    # 3. 族配额采样
    quota = {"PARAM-01": 0.40, "PARAM-03": 0.25}  # 其余(TERM/ENUM/PARAM-02)平分剩余
    rest_types = [t for t in by_type if t not in quota]
    rest_share = (1.0 - sum(quota.values())) / max(len(rest_types), 1)
    for t in rest_types:
        quota[t] = rest_share
    picked = []
    for t, share in sorted(quota.items()):
        want = int(SYNTH_TOTAL * share)
        pool = [p for p in train_synth if p["type"] == t]
        take = pool[:want]  # 已shuffle
        picked.extend(take)
        print(f"  {t}: 配额{share:.0%}→{want}, 池{len(pool)}→取{len(take)}")

    # 4. 混合 + anchor上采样(复用v12协议: con×6→inc//2)
    inc = [x for x in anchor if x["label"] == "inconsistent"]
    con = [x for x in anchor if x["label"] == "consistent"]
    rng.shuffle(con)
    con_up = (con * 6)[:len(inc) // 2]
    mix = inc + con + con_up
    for p in picked:
        mix.append({"pair": {"premise": p["premise"], "hypothesis": p["hypothesis"]},
                    "label": p["label"], "type": p["type"]})
    rng.shuffle(mix)
    print(f"\n混合训练集: {len(mix)}条(anchor{len(inc) + len(con) + len(con_up)}+synth{len(picked)}, "
          f"合成:真实≈{len(picked)}:{len(inc) + len(con)})")
    print(f"标签: {dict(Counter(x['label'] for x in mix))}")
    return mix, gate, {"anchor": len(anchor), "synth": len(picked), "gate": len(gate)}


def train(mix: list[dict], out_name: str) -> Path:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    MODEL_DIR = str(BASE / "models/nli/chinese-roberta-wwm-ext")
    OUT = BASE / f"models/nli/{out_name}"
    tok = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    torch.manual_seed(SEED)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR, local_files_only=True, num_labels=2,
        id2label={0: "consistent", 1: "inconsistent"},
        label2id={"consistent": 0, "inconsistent": 1})
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=5, eta_min=1e-6)
    t0 = time.time()
    model.train()
    for ep in range(5):
        tot, nb = 0.0, 0
        for i in range(0, len(mix), 16):
            batch = mix[i:i + 16]
            enc = tok([x["pair"]["premise"] for x in batch],
                      [x["pair"]["hypothesis"] for x in batch],
                      padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(device)
            labels = torch.tensor([1 if x["label"] == "inconsistent" else 0
                                   for x in batch], device=device)
            out = model(**enc, labels=labels)
            if not torch.isfinite(out.loss):
                continue
            opt.zero_grad()
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot += float(out.loss.detach())
            nb += 1
        sch.step()
        print(f"  ep{ep + 1}: loss={tot / max(nb, 1):.4f} ({time.time() - t0:.0f}s)", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT))
    tok.save_pretrained(str(OUT))
    print(f"保存 → {OUT}")
    return OUT


def main() -> None:
    mix, gate, stats = build_mix()
    out = train(mix, "roberta-v19-mixed")

    # gate评测(棘轮门控: v19 NLI纯模型 vs v12纯模型 on gate)
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"

    def pure_nli_eval(model_dir: str, pairs: list[dict]) -> dict:
        tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True).to(device).eval()
        preds = []
        with torch.no_grad():
            for i in range(0, len(pairs), 32):
                batch = pairs[i:i + 32]
                enc = tok([p["premise"] for p in batch], [p["hypothesis"] for p in batch],
                          padding=True, truncation=True, max_length=128,
                          return_tensors="pt").to(device)
                probs = torch.softmax(model(**enc).logits.float(), dim=-1)[:, 1]
                preds.extend("inconsistent" if v >= 0.5 else "consistent" for v in probs.tolist())
        golds = [p["label"] for p in pairs]
        acc = sum(1 for a, b in zip(preds, golds) if a == b) / len(pairs)
        # per-type
        by_t = defaultdict(lambda: [0, 0])
        for p, pr in zip(pairs, preds, strict=True):
            by_t[p["type"]][0] += (pr == p["label"])
            by_t[p["type"]][1] += 1
        return {"acc": round(acc, 3),
                "per_type": {t: round(v[0] / v[1], 3) for t, v in sorted(by_t.items())}}

    print("\n═══ gate评测(纯NLI模型, 无确定性通道) ═══")
    v12_g = pure_nli_eval(str(BASE / "models/nli/roberta-v12-anchor"), gate)
    v19_g = pure_nli_eval(str(out), gate)
    print(f"v12纯NLI on gate: acc={v12_g['acc']}")
    print(f"  per_type: {v12_g['per_type']}")
    print(f"v19纯NLI on gate: acc={v19_g['acc']}")
    print(f"  per_type: {v19_g['per_type']}")

    # 终点一次性: clean130/md166(纯v19模型)
    clean130 = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md_sc3 = json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8"))
    md_047 = json.loads((BASE / "data/gjb_438c/human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
    md166 = md_sc3 + [x for x in md_047 if x not in md_sc3]
    print("\n═══ 终点(纯v19模型, 一次) ═══")
    r_clean = pure_nli_eval(str(out), clean130)
    r_md = pure_nli_eval(str(out), md166)
    print(f"v19纯NLI clean130: acc={r_clean['acc']}")
    print(f"v19纯NLI md166: acc={r_md['acc']}")

    sys.path.insert(0, str(BASE / "tools"))
    from run_utils import open_run
    run = open_run("v19_mix_train", {
        "协议": "anchor(v12同款)+synth_s1@族配额(合成:真实≈2:1), gate=分层10%留出",
        "目的": "synth_s1作为训练燃料点燃NLI(判定性实验)"})
    run.save_result({
        "训练": stats, "gate_v12_pureNLI": v12_g, "gate_v19_pureNLI": v19_g,
        "terminal_clean130_pureNLI": r_clean["acc"], "terminal_md166_pureNLI": r_md["acc"]})
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
