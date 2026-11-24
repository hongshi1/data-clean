"""E1字面忠实修复的验收对比: 基线run vs 修复run 逐实例diff + 字面契约验证.

只读对比脚本(验收工具, 不进tests): 验证三件事——
1. 判定无回归: 逐实例verdict/detected/n_localizations/citation/
   anchor_overlap/root_cause逐位一致(唯一允许差异=literal字段);
2. 字面契约: 修复后全部23条定位 answer[span]==claim_text 逐条验证;
3. 汇总字段对比: citation/root_cause/by_category一致, literal提升.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    read_jsonl,
)
from algorithms.consistency.qa_module import (  # noqa: E402
    QAConsistencyModule,
)

BASE_RUN = (BASE_DIR / "data/gjb_438c/runs/"
            "eval_span_faithfulness_2609361e_20261124_152714/result.json")
POST_RUN = (BASE_DIR / "data/gjb_438c/runs/"
            "eval_span_faithfulness_add8863a_20261124_163132/result.json")
EVALSET = (BASE_DIR / "data/gjb_438c/localization_gold"
           / "violation_evalset_v1.jsonl")


def main() -> None:
    base = json.loads(BASE_RUN.read_text(encoding="utf-8"))
    post = json.loads(POST_RUN.read_text(encoding="utf-8"))
    base_d = {d["instance_id"]: d
              for d in base["configs"]["expert"]["details"]}
    post_d = {d["instance_id"]: d
              for d in post["configs"]["expert"]["details"]}
    assert set(base_d) == set(post_d), "实例集不一致"

    print("=== 1. 判定无回归: 逐实例(允许差异仅literal字段) ===")
    regress = 0
    for iid in sorted(base_d):
        b, p = base_d[iid], post_d[iid]
        stable_fields = (
            b["predicted_verdict"] == p["predicted_verdict"]
            and b["detected"] == p["detected"]
            and b["n_localizations"] == p["n_localizations"]
            and b["citation"] == p["citation"]
            and b["anchor_overlap"] == p["anchor_overlap"]
            and b["root_cause"]["predicted_operations"]
            == p["root_cause"]["predicted_operations"]
            and b["root_cause"]["predicted_sources"]
            == p["root_cause"]["predicted_sources"])
        if not stable_fields:
            regress += 1
            print(f"  DIFF(回归): {iid}")
        elif b["literal"] != p["literal"]:
            before = b["literal"]["answer_side_states"]
            after = p["literal"]["answer_side_states"]
            print(f"  {iid}: verdict={p['predicted_verdict']}"
                  f" n_loc={p['n_localizations']}"
                  f" faithful {b['literal']['n_literal_faithful']}"
                  f"->{p['literal']['n_literal_faithful']}"
                  f" states {before} -> {after}")
    print(f"回归实例数={regress} (0=判定无回归)")

    print()
    print("=== 2. 字面契约逐条验证(修复后真实推理) ===")
    rows = read_jsonl(EVALSET)
    module = QAConsistencyModule(use_experts=True)
    n_total = n_ok = 0
    for row in rows:
        result = module.verify(build_qa_input(row))
        for loc in result.localizations:
            n_total += 1
            span = loc.answer_span
            if (span is not None
                    and row["answer"][span[0]:span[1]] == loc.claim_text):
                n_ok += 1
            else:
                print(f"  无span/非逐字: {loc.claim_id} {loc.method}"
                      f" text={loc.claim_text[:30]!r}")
    print(f"answer[span]==claim_text: {n_ok}/{n_total}")

    print()
    print("=== 3. 汇总字段对比(基线 -> 修复) ===")
    bs = base["configs"]["expert"]["summary"]
    ps = post["configs"]["expert"]["summary"]
    bl, pl = bs["literal"], ps["literal"]
    for key in ("n_units", "n_literal_faithful", "literal_faithful_rate",
                "n_answer_faithful", "answer_faithful_rate", "n_span_exact",
                "span_exact_rate", "n_evidence_refs_ok",
                "evidence_refs_ok_rate"):
        print(f"  {key}: {bl[key]} -> {pl[key]}")
    print(f"  citation一致: {bs['citation'] == ps['citation']}")
    print(f"  root_cause一致: {bs['root_cause'] == ps['root_cause']}")
    print(f"  by_category一致: "
          f"{bs['by_category'] == ps['by_category']}")
    print(f"  undetected: {bs['undetected_ids']}")


if __name__ == "__main__":
    main()
