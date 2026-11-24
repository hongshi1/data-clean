r"""claim→typed桥接设计变体探索(99号P1的迭代臂, 主评测的补充).

背景(主评测eval_claim_typed_bridge.py的C臂=spec忠实桥接): 切分器v2的
claim覆盖与typed字段分布近乎不相交(test46上identifier覆盖率0.0,
typed字段全在O区)——spec式"segment内typed抽取"退化为裸切分器.
本脚本探索补齐typed覆盖的两种合并形态(诊断Alignment Bottleneck的
对齐粒度互补性, 不改qa_module注册面):

  D_bridge_union  整答案typed抽取(SAE字段粒度, 与A_regex同源) +
                  typed span外的切分器叙事claims(原子粒度)——两类
                  粒度并集, span重叠抑制防双重声明;
  E_bridge_gated  镜像decompose_claims的回退门: 有typed字段时只出
                  typed claims(A_regex行为), 无typed字段时切分器
                  claims替代structural回退.

隔离与协议同主评测(L0/L1专家未patch, strict+assertive_strict,
test46+银标). 用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/eval_claim_typed_bridge_variants.py
输出: data/gjb_438c/runs/eval_claim_typed_bridge_variants_<hash>_<ts>/
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import (  # noqa: E402
    AnswerClaim,
    decompose_claims,
)
from algorithms.consistency.claim_segmenter_local import (  # noqa: E402
    segment_claims)
from algorithms.consistency.eval_lib import (  # noqa: E402
    load_silver_labels,
)
from tools.eval_claim_typed_bridge import (  # noqa: E402
    AGGREGATIONS,
    BOUNDARY_GATE,
    NLI_GATE,
    NLI_MODEL_PATH,
    SEG_V2,
    git_sha,
    load_test46,
    run_arm,
)
from tools.eval_claim_recognition import eval_variant, load_gold  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
TRAIN_V1 = BASE / "data/gjb_438c/distillation/segmenter_train_v1.json"
TRAIN_V2 = BASE / "data/gjb_438c/distillation/segmenter_train_v2.json"

_TYPED_KINDS = ("numeric", "quoted", "enum", "identifier")


def _typed_claims(question: str, answer: str) -> list[AnswerClaim]:
    """整答案typed抽取(=decompose_claims的typed部分, 不含semantic回退)."""
    return [c for c in decompose_claims(question, answer)
            if c.kind in _TYPED_KINDS]


def _segment_semantic(answer: str,
                      model_path: str, boundary_gate: float,
                      exclude_spans: list[tuple[int, int]]
                      ) -> list[AnswerClaim]:
    """切分器segments → semantic claims(span与exclude_spans重叠者剔除)."""
    claims: list[AnswerClaim] = []
    for seg in segment_claims(answer, model_path=model_path,
                              boundary_gate=boundary_gate):
        s0, s1 = seg["span"]
        if any(s0 < e and s_ < s1 for s_, e in exclude_spans):
            continue  # 已被typed claim覆盖的文本不再作叙事claim(防双声明)
        claims.append(AnswerClaim(kind="semantic", text=seg["text"],
                                   span=(s0, s1)))
    return claims


def union_decompose(question: str, answer: str) -> list[AnswerClaim]:
    """D臂: 整答案typed ∪ typed span外的切分器叙事claims."""
    typed = _typed_claims(question, answer)
    spans = [c.span for c in typed if c.span]
    semantic = _segment_semantic(answer, SEG_V2, BOUNDARY_GATE, spans)
    claims = typed + semantic
    if not claims:
        return decompose_claims(question, answer)
    return claims


def gated_decompose(question: str, answer: str) -> list[AnswerClaim]:
    """E臂: 有typed字段→只出typed(A_regex门控行为); 无→切分器叙事."""
    typed = _typed_claims(question, answer)
    if typed:
        return typed
    semantic = _segment_semantic(answer, SEG_V2, BOUNDARY_GATE, [])
    if semantic:
        return semantic
    return decompose_claims(question, answer)


def _predict_of(fn) -> Any:
    def predict(question: str, answer: str) -> list[dict[str, Any]]:
        return [{"text": c.text, "span": list(c.span) if c.span else None}
                for c in fn(question, answer)]
    return predict


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-recognition", action="store_true")
    args = parser.parse_args()

    records = load_test46()
    labels = load_silver_labels(SILVER)
    print(f"test46: {len(records)}条; labels: {len(labels)}")

    arms: list[tuple[str, Any, bool, str]] = [
        ("D_bridge_union", union_decompose, True, "typed"),
        ("E_bridge_gated", gated_decompose, True, "typed"),
    ]
    results: dict[str, Any] = {}
    for name, decompose, patch, mode in arms:
        results[name] = run_arm(name, decompose, patch, records, labels,
                                decomposer_mode=mode)

    recognition: dict[str, Any] = {}
    if not args.skip_recognition:
        slices = [("dev45", TRAIN_V1, "dev45")]
        if TRAIN_V2.exists():
            slices.append(("d3train600", TRAIN_V2, "d3train"))
        for name, fn in (("D_bridge_union", union_decompose),
                         ("E_bridge_gated", gated_decompose)):
            for slice_name, path, source in slices:
                gold = load_gold(path, source)
                entry = recognition.setdefault(slice_name, {})
                entry[name] = eval_variant(gold, _predict_of(fn))
                r = entry[name]
                print(f"[recog/{slice_name}/{name}] "
                      f"P={r['claim_precision']:.4f} "
                      f"R={r['claim_recall']:.4f} F1={r['claim_f1']:.4f}",
                      flush=True)

    report = {
        "experiment": ("claim→typed桥接设计变体(99号P1迭代): union vs "
                       "gated on test46"),
        "recorded": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "config": {
            "nli_model_path": NLI_MODEL_PATH,
            "nli_gate": NLI_GATE,
            "aggregations": list(AGGREGATIONS),
            "segmenter_v2": SEG_V2,
            "boundary_gate": BOUNDARY_GATE,
            "arms": {
                "D_bridge_union": ("整答案typed抽取 + typed span外切分器"
                                   "叙事claims(span重叠抑制)"),
                "E_bridge_gated": ("有typed→只出typed; 无typed→切分器叙事"
                                   "(镜像decompose_claims回退门)"),
            },
        },
        "n": len(records),
        "results": results,
        "recognition": recognition,
    }
    run = open_run("eval_claim_typed_bridge_variants", {
        "arms": list(results),
        "aggregations": list(AGGREGATIONS),
        "segmenter": SEG_V2,
        "boundary_gate": BOUNDARY_GATE,
    })
    run.save_result(report)

    print("\n" + "=" * 78)
    for aggregation in AGGREGATIONS:
        print(f"-- aggregation={aggregation}")
        print(f"{'arm':<16s} {'acc':>7s} {'mF1':>7s} {'supF1':>6s} "
              f"{'refF1':>6s} {'nieF1':>6s} {'cl/inst':>8s}")
        for name in ("D_bridge_union", "E_bridge_gated"):
            m = results[name][aggregation]["metrics"]
            pc = m["per_class"]
            st = results[name]["claim_stats"]
            print(f"{name:<16s} {m['accuracy']:7.4f} {m['macro_f1']:7.4f} "
                  f"{pc['support']['f1']:6.4f} {pc['refute']['f1']:6.4f} "
                  f"{pc['not_in_evidence']['f1']:6.4f} "
                  f"{st['claims_per_instance']:8.2f}")
        print()
    print(f"→ {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
