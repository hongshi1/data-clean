r"""探针评测监控: v12模型在冻结探针集上推理, 报告bAcc+误报率.

用途: P0护栏(docs/srs_project/pair_dataset_augmentation_plan.md §5.1) —
  每次训完新模型在本探针集上复跑, 监控捷径行为(词重叠误报/矛盾漏报/表格蕴含).

用法:
  python tools/probe_eval.py                              # v12基线 → runs/probe_baseline.json
  python tools/probe_eval.py --model-dir models/nli/xxx   # 对照模型
  python tools/probe_eval.py --out runs/probe_v18.json    # 自定义固定输出名

输出:
  data/gjb_438c/runs/probe_baseline.json  (固定名, 最新结果)
  data/gjb_438c/runs/probe_eval_<hash>_<ts>/ (runs协议审计副本, 不覆盖)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

PROBE_DIR = BASE / "data/gjb_438c/probes"
RUNS_DIR = BASE / "data/gjb_438c/runs"
DEFAULT_MODEL = BASE / "models/nli/roberta-v12-anchor"
DEFAULT_OUT = RUNS_DIR / "probe_baseline.json"

PROBE_FILES = [
    ("paws_shortcut_probe.json", "paws_shortcut", "fpr_误报率",
     "词重叠捷径分=误报率(释义对被判inconsistent比例)"),
    ("feverous_table_probe.json", "feverous_table", "fpr_误报率",
     "表格蕴含误报率(SUPPORTS被判inconsistent比例)"),
    ("ocnli_contradiction_probe.json", "ocnli_contradiction", "fnr_漏报率",
     "矛盾漏报率(contradiction被判consistent比例)"),
]


def git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def load_probe(path: Path) -> tuple[dict, list[dict]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not doc.get("meta", {}).get("frozen"):
        raise ValueError(f"探针未冻结声明: {path}")
    items = doc["items"]
    for it in items:
        missing = {"id", "premise", "hypothesis", "label", "probe_type"} - set(it)
        if missing:
            raise ValueError(f"探针条目缺字段{sorted(missing)}: {path}:{it.get('id')}")
    return doc["meta"], items


def run_model(model_dir: Path, items: list[dict], batch_size: int = 32) -> list[dict]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir),
                                                               local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    pairs = [(it["premise"], it["hypothesis"]) for it in items]
    out: list[dict] = []
    with torch.no_grad():
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            enc = tok([p for p, _ in batch], [h for _, h in batch], padding=True,
                      truncation=True, max_length=128, return_tensors="pt").to(device)
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().tolist()
            for it, pr in zip(items[i:i + len(batch)], probs):
                out.append({"id": it["id"],
                            "pred": "inconsistent" if pr[1] >= 0.5 else "consistent",
                            "prob_inc": round(pr[1], 4)})
    return out


def metrics(labels: list[str], preds: list[str]) -> dict:
    tp = sum(1 for lb, p in zip(labels, preds) if lb == "inconsistent" and p == "inconsistent")
    fn = sum(1 for lb, p in zip(labels, preds) if lb == "inconsistent" and p == "consistent")
    tn = sum(1 for lb, p in zip(labels, preds) if lb == "consistent" and p == "consistent")
    fp = sum(1 for lb, p in zip(labels, preds) if lb == "consistent" and p == "inconsistent")
    tpr = tp / (tp + fn) if tp + fn else None
    tnr = tn / (tn + fp) if tn + fp else None
    bacc = (tpr + tnr) / 2 if tpr is not None and tnr is not None else None
    return {
        "n": len(labels), "n_pos": tp + fn, "n_neg": tn + fp,
        "tp": tp, "fn": fn, "tn": tn, "fp": fp,
        "tpr": round(tpr, 4) if tpr is not None else None,
        "tnr": round(tnr, 4) if tnr is not None else None,
        "bacc": round(bacc, 4) if bacc is not None else None,
        "fpr_误报率": round(fp / (fp + tn), 4) if fp + tn else None,
        "fnr_漏报率": round(fn / (fn + tp), 4) if fn + tp else None,
        "acc": round((tp + tn) / len(labels), 4) if labels else None,
    }


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="冻结探针集评测(v12捷径监控)")
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args(argv)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        sys.exit(f"模型目录不存在: {model_dir}")
    if not PROBE_DIR.exists():
        sys.exit(f"探针目录不存在: {PROBE_DIR}  (先运行 python tools/build_probes.py)")

    result: dict = {
        "meta": {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "git_sha": git_sha(),
            "model_dir": model_dir.relative_to(BASE).as_posix(),
            "positive_class": "inconsistent",
            "probe_dir": PROBE_DIR.relative_to(BASE).as_posix(),
            "note": "探针为冻结eval-only资产; 结果含每条预测供翻转分析",
        },
        "probes": {},
    }
    all_labels: list[str] = []
    all_preds: list[str] = []

    for fname, name, score_key, score_desc in PROBE_FILES:
        meta, items = load_probe(PROBE_DIR / fname)
        preds = run_model(model_dir, items, batch_size=args.batch_size)
        labels = [it["label"] for it in items]
        pred_list = [p["pred"] for p in preds]
        m = metrics(labels, pred_list)
        result["probes"][name] = {
            "file": f"probes/{fname}",
            "probe_meta": {k: meta[k] for k in
                           ("probe_type", "purpose", "n_items", "label_dist", "built_at")},
            "metrics": m,
            "shortcut_score": {"metric": score_key, "desc": score_desc,
                               "value": m[score_key]},
            "rows": [{"id": it["id"], "label": it["label"], "pred": p["pred"],
                      "prob_inc": p["prob_inc"]} for it, p in zip(items, preds)],
        }
        all_labels.extend(labels)
        all_preds.extend(pred_list)
        print(f"[{name}] n={m['n']} pos={m['n_pos']} neg={m['n_neg']}  "
              f"bAcc={m['bacc'] if m['bacc'] is not None else 'N/A(单类)'}  "
              f"TPR={m['tpr']} TNR={m['tnr']}  "
              f"误报率={m['fpr_误报率']} 漏报率={m['fnr_漏报率']}  "
              f"| {score_desc}={m[score_key]}")

    result["pooled"] = metrics(all_labels, all_preds)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    run = open_run("probe_eval", {
        "model_dir": result["meta"]["model_dir"],
        "out": out_path.relative_to(BASE).as_posix(),
        "probes": [n for _, n, _, _ in PROBE_FILES],
    })
    run.save_result({k: v for k, v in result.items() if k != "probes"} | {
        "probes": {n: {kk: vv for kk, vv in v.items() if kk != "rows"}
                   for n, v in result["probes"].items()}})
    run.log(action="probe_eval_done", model=result["meta"]["model_dir"],
             n_total=len(all_labels))

    pm = result["pooled"]
    print(f"\n[pooled] n={pm['n']}  bAcc={pm['bacc']}  误报率={pm['fpr_误报率']}  "
          f"漏报率={pm['fnr_漏报率']}")
    print(f"已保存: {out_path}")
    print(f"审计副本: {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
