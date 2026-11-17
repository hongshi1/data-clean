"""D3学生+脚手架专家的推理时集成(混合架构, 无需重训).

组合规则(利用各自已证明的优势):
  - 脚手架fast档(L0/L1确定性专家): test46上refute P=1.0
    (零假阳性, R=0.62)——其refute判定可信, 作覆盖(override)
  - D3学生(v2b/v2c): acc 0.8043(NIE判定强), 生成式定位+解释
    ——作主判定
  - 规则: fast档判refute→refute(专家覆盖); 否则取学生verdict
  定位报告: 学生issues(生成式)优先, 专家refute时附带专家定位

对照: 纯学生 0.8043/0.4111/0.333 | 纯脚手架 0.9130/0.8047/0.800
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_d3_student import judge  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
OUT = BASE / "data/gjb_438c/distillation/d3_ensemble_eval_v1.json"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default="models/llm/d3_student_v2b")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rule", default="expert_override",
                        choices=["expert_override", "refute_union"])
    args = parser.parse_args()

    import eval_d3_student  # noqa: F401  (复用judge的模型单例)
    eval_d3_student._ADAPTER = str(BASE / args.adapter)

    silver = load_silver_labels(SILVER)
    qa = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    test = [r for r in qa if r["instance_id"] not in dev_ids]
    if args.limit:
        test = test[:args.limit]
    vio = [json.loads(line) for line in
           VIO.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        vio = vio[:args.limit]

    fast = QAConsistencyModule(use_experts=True)  # L0/L1确定性, ~8ms
    _ = fast.verify(build_qa_input(test[0]))  # warmup

    def run(records, labels, tag):
        y_true: list[str] = []
        y_pred: list[str] = []
        n_expert_refute = 0
        n_student_issue = 0
        started = time.time()
        for rec in records:
            request = build_qa_input(rec)
            fast_result = fast.verify(request)
            expert_refute = fast_result.verdict == "refute"
            if expert_refute:
                n_expert_refute += 1
            verdict, issues, _elapsed = judge(
                str(rec["question"]), str(rec["answer"]),
                [str(e["text"]) for e in rec["evidence"]])
            if issues:
                n_student_issue += 1
            if args.rule == "expert_override":
                final = "refute" if expert_refute else verdict
            else:  # refute_union
                final = ("refute" if (expert_refute or
                                      verdict == "refute") else verdict)
            y_true.append(labels.get(str(rec["instance_id"]),
                                     "not_in_evidence"))
            y_pred.append(final)
        m = classification_metrics(y_true, y_pred)
        elapsed = time.time() - started
        r = m["per_class"].get("refute", {})
        print(f"[{tag}] acc={m['accuracy']:.4f} "
              f"mF1={m['macro_f1']:.4f} "
              f"refuteF1={r.get('f1', 0):.3f} "
              f"(P={r.get('precision', 0):.2f} "
              f"R={r.get('recall', 0):.2f}) | "
              f"专家refute {n_expert_refute}例 "
              f"学生issue {n_student_issue}例 "
              f"| {elapsed / len(records):.1f}s/例")
        return m

    result = {
        "rule": args.rule,
        "adapter": args.adapter,
        "test46": run(test, silver, "test46(集成)"),
        "violations17": run(
            vio, {str(r["instance_id"]): str(r["expected_verdict"])
                  for r in vio}, "violations17(集成)"),
        "baselines": {"student_only": "0.8043/0.4111/0.333",
                      "scaffold": "0.9130/0.8047/0.800"},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
