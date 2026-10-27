"""Cross-check script for docs/srs_project/49_cascadeverify_v2_results.md.

Re-reads every result.json cited in the doc and re-derives the table
numbers, comparing them against the doc's claims. Print PASS/FAIL per item.

Wave 5 (2026-10-27 afternoon): all numbers re-anchored to the 7-expert
stack runs — eval_paper_matrix_c409df7f_20261027_125551 (B0-B5 + 10
ablations + 4 bootstrap pairs), eval_cascade_1e92cdce_20261027_124941
(cascade five configs) and the eval_violations_5d5c92a8 series
(113100 -> 120749 -> 124733, the expert-completion loop).

Wave 6 (2026-10-27 evening): added the 9-expert-stack terminal violation
run (eval_violations_5d5c92a8_20261027_165400, 16/17 via coverage_L1),
the learned-router runs (router_train_7a90549c + eval_router_2b76c358:
0.0875 held-out agreement, oracle 0.7867@2), the mutation-injection
matrix (eval_mutation_detection_750b7b7d: 394/41/10.4% + the
evidence-side double-registration cross reference) and the numeric-fact
probes (doc04 92 / 91QA 0 / violation-set 22) re-derived from the
evidence pipeline itself.

Wave 7 (2026-10-27 night, audit-response closing): added the frozen
dev/test split (dev_test_split_v1.json: 29 clusters, dev 45/test 46,
zero cross-side topics), the dev grid sweep (calibrate_on_dev:
60 configs collapse to 3 distinct macro-F1 values), the honest test
evaluations (eval_test_honest 185819 pre-fix 0.704 / 195753 post-fix
0.8286, optimistic_bias +0.0145 vs the mixed-caliber -0.1101), the P1
fix results (eval_qa_module_silver 0.6381->0.7212, eval_qa_dev_split
0.8875, eval_violations 16/17 zero regression with localization
24->23), the crossdoc06 sound evalset (30 items S/R/N=10 each) and the
generalization-gap numbers (det 0.1524 / cascade 0.5309, deltas
-0.4857 / -0.1876, zero improvement from the P1 fixes), plus the gold
annotation workbench asset (108 instances / 525 claims).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUNS = BASE / "data/gjb_438c/runs"
DOC = BASE / "docs/srs_project/49_cascadeverify_v2_results.md"

pm = json.loads((RUNS / "eval_paper_matrix_c409df7f_20261027_125551/result.json").read_text(encoding="utf-8"))
pm_old = json.loads((RUNS / "eval_paper_matrix_0fabaced_20261027_023711/result.json").read_text(encoding="utf-8"))
ec = json.loads((RUNS / "eval_cascade_1e92cdce_20261027_124941/result.json").read_text(encoding="utf-8"))
ec3 = [json.loads((RUNS / f"eval_cascade_1e92cdce_20261027_{t}/result.json").read_text(encoding="utf-8")) for t in ("022407", "023405", "023644")]
l3 = json.loads((RUNS / "eval_llm_residual_5dd69927_20261026_173434/result.json").read_text(encoding="utf-8"))
v0 = json.loads((RUNS / "eval_violations_5d5c92a8_20261027_113100/result.json").read_text(encoding="utf-8"))
v1 = json.loads((RUNS / "eval_violations_5d5c92a8_20261027_120749/result.json").read_text(encoding="utf-8"))
v2 = json.loads((RUNS / "eval_violations_5d5c92a8_20261027_124733/result.json").read_text(encoding="utf-8"))
v3 = json.loads((RUNS / "eval_violations_5d5c92a8_20261027_165400/result.json").read_text(encoding="utf-8"))
rt = json.loads((RUNS / "router_train_7a90549c_20261027_165644/result.json").read_text(encoding="utf-8"))
er = json.loads((RUNS / "eval_router_2b76c358_20261027_170640/result.json").read_text(encoding="utf-8"))
md = json.loads((RUNS / "eval_mutation_detection_750b7b7d_20261027_165008/result.json").read_text(encoding="utf-8"))
b1 = json.loads((RUNS / "build_egt_dataset_3a52cd3f_20261026_154036/result.json").read_text(encoding="utf-8"))
b2 = json.loads((RUNS / "build_egt_dataset_721c8665_20261026_165547/result.json").read_text(encoding="utf-8"))
b3 = json.loads((RUNS / "build_egt_dataset_8a8716bb_20261027_003528/result.json").read_text(encoding="utf-8"))
t1 = json.loads((RUNS / "train_residual_nli_ade325ae_20261026_195906/result.json").read_text(encoding="utf-8"))
t2 = json.loads((RUNS / "train_residual_nli_acfead4b_20261027_013647/result.json").read_text(encoding="utf-8"))
n1 = json.loads((RUNS / "eval_nli_residual_4971ceba_20261026_201247/result.json").read_text(encoding="utf-8"))
evalset = [json.loads(line) for line in
           (BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl")
           .read_text(encoding="utf-8").splitlines() if line.strip()]
mutation_evalset = [json.loads(line) for line in
                     (BASE / "data/gjb_438c/mutation_injection_evalset_v1.jsonl")
                     .read_text(encoding="utf-8").splitlines() if line.strip()]
th_pre = json.loads((RUNS / "eval_test_honest_6740ed5c_20261027_185819/result.json").read_text(encoding="utf-8"))
th_post = json.loads((RUNS / "eval_test_honest_6740ed5c_20261027_195753/result.json").read_text(encoding="utf-8"))
cal = json.loads((RUNS / "calibrate_on_dev_a069227d_20261027_185110/result.json").read_text(encoding="utf-8"))
tuned_cfg = json.loads((BASE / "data/gjb_438c/qa_frozen/dev_tuned_config_v1.json").read_text(encoding="utf-8"))
split_v1 = json.loads((BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json").read_text(encoding="utf-8"))
silver_labels = {json.loads(line)["instance_id"]: json.loads(line)["final_verdict"] for line in
                 (RUNS / "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
                 .read_text(encoding="utf-8").splitlines() if line.strip()}
silver_pre = json.loads((RUNS / "eval_qa_module_silver_f119425e_20261027_190326/result.json").read_text(encoding="utf-8"))
silver_post = json.loads((RUNS / "eval_qa_module_silver_f119425e_20261027_195515/result.json").read_text(encoding="utf-8"))
silver_post2 = json.loads((RUNS / "eval_qa_module_silver_f119425e_20261027_194154/result.json").read_text(encoding="utf-8"))
dev_b4 = json.loads((RUNS / "eval_qa_dev_split_6d4e96bb_20261027_195532/result.json").read_text(encoding="utf-8"))
v4 = json.loads((RUNS / "eval_violations_5d5c92a8_20261027_195407/result.json").read_text(encoding="utf-8"))
v5 = json.loads((RUNS / "eval_violations_5d5c92a8_20261027_195501/result.json").read_text(encoding="utf-8"))
cd_pre = json.loads((RUNS / "eval_crossdoc_27e8ce32_20261027_190259/result.json").read_text(encoding="utf-8"))
cd_post = json.loads((RUNS / "eval_crossdoc_27e8ce32_20261027_195859/result.json").read_text(encoding="utf-8"))
cd_build = json.loads((RUNS / "build_crossdoc_evalset_1a7c8719_20261027_190350/result.json").read_text(encoding="utf-8"))
crossdoc_evalset = [json.loads(line) for line in
                    (BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl")
                    .read_text(encoding="utf-8").splitlines() if line.strip()]
pre_annotated = [json.loads(line) for line in
                 (BASE / "data/gjb_438c/localization_gold/pre_annotated_v1.jsonl")
                 .read_text(encoding="utf-8").splitlines() if line.strip()]
frozen_by_id = {json.loads(line)["instance_id"]: json.loads(line) for line in
                (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
                .read_text(encoding="utf-8").splitlines() if line.strip()}

results: list[tuple[str, bool]] = []


def check(name: str, got, want) -> None:
    ok = got == want
    results.append((name, ok))
    if not ok:
        print(f"FAIL {name}: got={got!r} want={want!r}")


def approx(name: str, got, want, tol=1e-9) -> None:
    ok = abs(got - want) < tol
    results.append((name, ok))
    if not ok:
        print(f"FAIL {name}: got={got!r} want={want!r}")


# --- Section 2: main table (B0-B5 from paper_matrix) ---
want_rows = {
    "B0": (0.8462, 0.3056, 0.0, 0.0, 0.9167, 0, 0),
    "B1": (0.5714, 0.3272, 0.1739, 0.087, 0.7206, 0, 0),
    "B2": (0.7143, 0.6105, 0.3529, 0.6667, 0.812, 91, 0),
    "B3": (0.9011, 0.6381, 0.25, 0.7143, 0.95, 0, 0),
    "B4": (0.9121, 0.7257, 0.4444, 0.7778, 0.9548, 83, 0),
    "B5": (0.8681, 0.7085, 0.5263, 0.6667, 0.9324, 86, 0),
}
for key, (acc, mf1, sf1, rf1, nf1, inv, api) in want_rows.items():
    b = pm["baselines"][key]
    approx(f"主表{key}.acc", round(b["accuracy"], 4), acc)
    approx(f"主表{key}.macro_f1", round(b["macro_f1"], 4), mf1)
    approx(f"主表{key}.S_F1", round(b["per_class"]["support"]["f1"], 4), sf1)
    approx(f"主表{key}.R_F1", round(b["per_class"]["refute"]["f1"], 4), rf1)
    approx(f"主表{key}.N_F1", round(b["per_class"]["not_in_evidence"]["f1"], 4), nf1)
    check(f"主表{key}.llm_invocations", b["llm_calls"]["invocations"], inv)
    check(f"主表{key}.llm_api", b["llm_calls"]["api_calls"], api)
# B3/B4 refute P/R detail cited in the doc
approx("主表B3.R_P", round(pm["baselines"]["B3"]["per_class"]["refute"]["precision"], 4), 0.8333)
approx("主表B3.R_R", round(pm["baselines"]["B3"]["per_class"]["refute"]["recall"], 4), 0.625)
approx("主表B4.R_P", round(pm["baselines"]["B4"]["per_class"]["refute"]["precision"], 4), 0.7)
approx("主表B4.R_R", round(pm["baselines"]["B4"]["per_class"]["refute"]["recall"], 4), 0.875)
approx("主表B5.S_R", round(pm["baselines"]["B5"]["per_class"]["support"]["recall"], 4), 0.8333)

# L2/cascade/conformal rows from eval_cascade (124941)
ec_rows = {
    "l2_nli": (0.8022, 0.5437, 0.2222, 0.5185, 0.8904, 0.3684, 0.875),
    "cascade": (0.9121, 0.7185, 0.4, 0.8, 0.9554, 0.8571, 0.75),
    "cascade_conformal": (0.8462, 0.5836, 0.2222, 0.6087, 0.92, 0.4667, 0.875),
}
for key, (acc, mf1, sf1, rf1, nf1, rp, rr) in ec_rows.items():
    c = ec["configs"][key]
    approx(f"主表{key}.acc", round(c["accuracy"], 4), acc)
    approx(f"主表{key}.macro_f1", round(c["macro_f1"], 4), mf1)
    approx(f"主表{key}.S_F1", round(c["per_class"]["support"]["f1"], 4), sf1)
    approx(f"主表{key}.R_F1", round(c["per_class"]["refute"]["f1"], 4), rf1)
    approx(f"主表{key}.N_F1", round(c["per_class"]["not_in_evidence"]["f1"], 4), nf1)
    approx(f"主表{key}.R_P", round(c["per_class"]["refute"]["precision"], 4), rp)
    approx(f"主表{key}.R_R", round(c["per_class"]["refute"]["recall"], 4), rr)
check("主表cascade.LLM_invocations", ec["llm_stats"]["cascade"]["invocations"], 15)
check("主表l3_llm.LLM_invocations", ec["llm_stats"]["l3_llm"]["invocations"], 83)
check("主表cascade_conformal.LLM_invocations", ec["llm_stats"]["cascade_conformal"]["invocations"], 13)
# baseline/l3_llm configs agree with paper_matrix B3/B4
approx("两run互证.B3", round(ec["configs"]["baseline"]["macro_f1"], 4), round(pm["baselines"]["B3"]["macro_f1"], 4))
approx("两run互证.B4", round(ec["configs"]["l3_llm"]["macro_f1"], 4), round(pm["baselines"]["B4"]["macro_f1"], 4))
# old-stack B3 (the 0.5628 historical baseline cited in §6.7)
approx("历史基线.B3_old", round(pm_old["baselines"]["B3"]["macro_f1"], 4), 0.5628)

# label distribution
check("标签分布", (pm["label_distribution"]["support"], pm["label_distribution"]["refute"], pm["label_distribution"]["not_in_evidence"]), (6, 8, 77))

# --- Section 3: ablations (10 items) ---
abl_want = {
    "-e1_expert": (0.9011, 0.6869, -0.0388),
    "-entity_detector": (0.9121, 0.7257, 0.0),
    "-sequence_expert": (0.8791, 0.729, 0.0033),
    "-trace_expert": (0.9121, 0.7257, 0.0),
    "-id_join_expert": (0.9121, 0.7257, 0.0),
    "-enum_join_expert": (0.9011, 0.6997, -0.026),
    "-per_claim_fusion": (0.8901, 0.5735, -0.1522),
    "-llm_residual": (0.9011, 0.6381, -0.0876),
    "-all_experts": (0.8681, 0.7085, -0.0172),
}
for key, (acc, mf1, delta) in abl_want.items():
    a = pm["ablations"][key]
    approx(f"消融{key}.acc", round(a["accuracy"], 4), acc)
    approx(f"消融{key}.macro_f1", round(a["macro_f1"], 4), mf1)
    approx(f"消融{key}.Δ", round(a["macro_f1"] - pm["baselines"]["B4"]["macro_f1"], 4), delta)
# single-expert filters = full 7-family minus one
family = {"entity", "e1", "sequence", "trace", "gjb", "id_join", "enum_join"}
for key, expert in (("-e1_expert", "e1"), ("-entity_detector", "entity"),
                    ("-sequence_expert", "sequence"), ("-trace_expert", "trace"),
                    ("-id_join_expert", "id_join"), ("-enum_join_expert", "enum_join")):
    got = set(pm["ablations"][key]["config"]["expert_filter"])
    check(f"消融{key}.filter=全族去一", got == family - {expert}, True)
deq = pm["ablations"]["deq_on_off"]
approx("消融DEQ_on.macro_f1", round(deq["on"]["macro_f1"], 4), 0.7329)
approx("消融DEQ_on.Δ", round(deq["on"]["macro_f1"] - deq["off"]["macro_f1"], 4), 0.0072)
approx("消融DEQ_on.refuteF1", round(deq["on"]["per_class"]["refute"]["f1"], 4), 0.8)
approx("消融DEQ_on.refuteR", round(deq["on"]["per_class"]["refute"]["recall"], 4), 1.0)
check("消融DEQ_on.api", deq["on"]["llm_calls"]["api_calls"], 0)
# join_experts_off (bootstrap-pair config)
jf = pm["join_experts_off"]
approx("join_off.macro_f1", round(jf["macro_f1"], 4), 0.6997)
approx("join_off.Δ", round(jf["macro_f1"] - pm["baselines"]["B4"]["macro_f1"], 4), -0.026)
check("join_off.filter", set(jf["config"]["expert_filter"]) == family - {"id_join", "enum_join"}, True)

# --- Section 4: bootstrap (4 pairs) ---
bs_want = {
    "B4_vs_B3": (0.0876, (-0.0511, 0.2666), 0.276),
    "B4_vs_B5": (0.0172, (-0.1641, 0.2094), 0.834),
    "B4_vs_B2": (0.1151, (-0.098, 0.313), 0.314),
    "B4_vs_no_join_experts": (0.026, (0.0, 0.1019), 0.666),
}
for key, (delta, ci, p) in bs_want.items():
    b = pm["bootstrap"][key]
    approx(f"bootstrap{key}.delta", round(b["delta"], 4), delta)
    check(f"bootstrap{key}.ci", (round(b["ci95"][0], 4), round(b["ci95"][1], 4)), ci)
    check(f"bootstrap{key}.p", b["p"], p)
check("bootstrap.n_boot", pm["bootstrap"]["B4_vs_B3"]["n_boot"], 1000)
check("bootstrap.对数", len(pm["bootstrap"]), 4)

# --- Section 5: EGT evolution ---
check("EGTv1.total", b1["dataset"]["total"], 117)
check("EGTv1.final_counts", (b1["dataset"]["final_counts"]["support"], b1["dataset"]["final_counts"]["refute"], b1["dataset"]["final_counts"]["not_in_evidence"]), (39, 39, 39))
check("EGTv2.total", b2["dataset"]["total"], 3000)
check("EGTv3.total", b3["dataset"]["total"], 4500)
check("EGTv3.final_counts", tuple(b3["dataset"]["final_counts"].values()), (1500, 1500, 1500))
check("EGTv3.raw_counts", tuple(b3["dataset"]["raw_counts"].values()), (3631, 2851, 4628))
approx("EGTv3.self_check_pass_rate", round(b3["acceptance"]["self_check_pass_rate"], 4), 0.9052)
approx("EGTv3.module_refute_rate", round(b3["acceptance"]["module_refute_rate_of_kept"], 4), 0.932)
check("EGTv3.kept_refute", b3["acceptance"]["kept_refute"], 2397)
check("EGTv3.refute_seeds", b3["statement_path"]["refute"]["n_seeds"], 17569)
check("EGTv3.narrative_samples", b3["narrative_path"]["n_samples"], 7237)
check("EGTv3.narrative_mix_refute_share", round(b3["narrative_mix"]["refute"]["actual_share"], 4), 0.8001)
check("EGTv3.final_by_source", (b3["final_by_source"]["statement"], b3["final_by_source"]["narrative"]), (1405, 2999))
# v1 model training + real eval
approx("v1模型.dev_acc", round(t1["dev_metrics"]["accuracy"], 4), 0.9645)
approx("v1模型.dev_macroF1", round(t1["dev_metrics"]["macro_f1"], 4), 0.9648)
check("v1模型.n_train", t1["n_train"], 2718)
approx("v1模型.real_macroF1", round(n1["nli_residual"]["macro_f1"], 4), 0.4963)
approx("v1模型.real_acc", round(n1["nli_residual"]["accuracy"], 4), 0.8132)
approx("v1模型.real_refuteR", round(n1["nli_residual"]["per_class"]["refute"]["recall"], 4), 0.375)
# v2 model
approx("v2模型.dev_macroF1", round(t2["dev_metrics"]["macro_f1"], 4), 0.9722)
check("v2模型.n_train", t2["n_train"], 4067)
approx("v2模型.real_macroF1", round(ec["configs"]["l2_nli"]["macro_f1"], 4), 0.5437)
approx("v2模型.real_refuteR", round(ec["configs"]["l2_nli"]["per_class"]["refute"]["recall"], 4), 0.875)

# --- Section 6: findings numbers ---
approx("零样本B1.macroF1", round(pm["baselines"]["B1"]["macro_f1"], 4), 0.3272)
approx("零样本B1.refuteF1", round(pm["baselines"]["B1"]["per_class"]["refute"]["f1"], 4), 0.087)
# L3 reference
approx("L3参照.macroF1", round(l3["residual"]["macro_f1"], 4), 0.7799)
approx("L3参照.acc", round(l3["residual"]["accuracy"], 4), 0.9341)
approx("L3参照.refuteP", round(l3["residual"]["per_class"]["refute"]["precision"], 4), 1.0)
approx("L3参照.refuteR", round(l3["residual"]["per_class"]["refute"]["recall"], 4), 0.875)
# cascade economics
cq = {row["config"]: row for row in ec["cost_quality_table"]}
check("级联.LLM_invocations", cq["cascade"]["llm_invocations"], 15)
check("级联.l3_invocations", cq["l3_llm"]["llm_invocations"], 83)
approx("级联.refuteF1", round(ec["configs"]["cascade"]["per_class"]["refute"]["f1"], 4), 0.8)
check("级联.nli_claims_judged", ec["cascade_escalation"]["nli_claims_judged"], 395)
check("级联.escalated_claims", ec["cascade_escalation"]["escalated_claims"], 75)
check("级联.escalated_instances", len(ec["cascade_escalation"]["escalated_instances"]), 13)
check("级联.corrected", len(ec["l2_to_cascade_flips"]["corrected"]), 11)
check("级联.regressed", len(ec["l2_to_cascade_flips"]["regressed"]), 1)
# targets
check("targets", (ec["targets"]["macro_f1_ge_0.75"], ec["targets"]["refute_precision_ge_0.9"], ec["targets"]["llm_invocations_le_30"]), (False, False, True))
# conformal two tiers
ct = ec["conformal_two_tier"]
check("conformal定稿.kept_n", ct["kept_tier_ge_keep_confidence"]["n_instances"], 1)
check("conformal定稿.kept_P", round(ct["kept_tier_ge_keep_confidence"]["precision"], 4), 0.0)
ct3 = ec3[0]["conformal_two_tier"]
check("conformal三次复现.kept_n", ct3["kept_tier_ge_keep_confidence"]["n_instances"], 7)
approx("conformal三次复现.kept_P", round(ct3["kept_tier_ge_keep_confidence"]["precision"], 4), 0.2857)
# earlier cascade macro_f1 (5-expert stack history)
for i, r in enumerate(ec3):
    approx(f"早期cascade[{i}].macroF1", round(r["configs"]["cascade"]["macro_f1"], 4), 0.6266)
# fp16 fluctuation: 12 eval_nli_residual_2996af6b runs
vals = []
for d in sorted((RUNS).glob("eval_nli_residual_2996af6b_*/result.json")):
    j = json.loads(d.read_text(encoding="utf-8"))
    vals.append(j["nli_residual"]["macro_f1"])
check("fp12波动.run数", len(vals), 12)
approx("fp12波动.min", round(min(vals), 4), 0.4325)
approx("fp12波动.max", round(max(vals), 4), 0.5298)
# 063/074: regressed instances in final cascade
check("063/074.regressed_ids", [r["instance_id"] for r in ec["l2_to_cascade_flips"]["regressed"]], ["S1QA-063"])
# per-claim fusion ablation kills support recall
check("融合消融.S_recall清零", pm["ablations"]["-per_claim_fusion"]["per_class"]["support"]["recall"], 0.0)

# --- Section 7: violation evalset evolution (deterministic config) ---
for run, name, n_det, rate in ((v0, "演进5专家栈", 9, 0.5294),
                               (v1, "演进+id_join", 12, 0.7059),
                               (v2, "演进+enum_join", 15, 0.8824),
                               (v3, "演进+coverage终态", 16, 0.9412)):
    d = run["configs"]["deterministic"]
    check(f"违例{name}.n_detected", d["n_detected"], n_det)
    approx(f"违例{name}.detection_rate", round(d["detection_rate"], 4), rate)
check("违例.cascade同样15/17", v2["configs"]["cascade"]["n_detected"], 15)
check("违例.cascade同样16/17", v3["configs"]["cascade"]["n_detected"], 16)
# final per-category detection (terminal = 165400, 9-expert stack)
d2 = v2["configs"]["deterministic"]
cat_want = {"identifier": 5, "enumeration": 4, "traceability": 3,
            "exception_template": 2, "function_coverage": 1,
            "document_name": 0, "qualification_coverage": 0}
for cat, det in cat_want.items():
    check(f"违例15/17口径.分类.{cat}", d2["by_category"][cat]["detected"], det)
check("违例15/17口径.undetected", d2["undetected_ids"], ["DOC04-VIO-15", "DOC04-VIO-17"])
check("违例15/17口径.refute_channels", d2["refute_channels"],
      {"e1_L1": 3, "id_join_L1": 5, "entity_L0": 2, "enum_join_L1": 3,
       "gjb_L1": 2, "trace_L1": 3})
# Wave 6 terminal state (165400): 16/17 with coverage_L1 closing VIO-17
d3 = v3["configs"]["deterministic"]
cat_want3 = {"identifier": 5, "enumeration": 4, "traceability": 3,
             "exception_template": 2, "function_coverage": 1,
             "document_name": 0, "qualification_coverage": 1}
for cat, det in cat_want3.items():
    check(f"违例16/17口径.分类.{cat}", d3["by_category"][cat]["detected"], det)
check("违例16/17口径.undetected_ids", d3["undetected_ids"], ["DOC04-VIO-15"])
check("违例16/17口径.refute_channels", d3["refute_channels"],
      {"e1_L1": 3, "id_join_L1": 5, "entity_L0": 2, "enum_join_L1": 3,
       "gjb_L1": 2, "trace_L1": 3, "coverage_L1": 1})
approx("违例16/17口径.targeted_rate", round(d3["targeted_detection_rate"], 4), 0.7647)
check("违例16/17口径.false_positives", d3["false_positives"], 0)
loc3 = d3["localization"]
approx("违例16/17口径.定位P", round(loc3["precision"], 4), 0.8)
approx("违例16/17口径.定位R", round(loc3["recall"], 4), 0.7059)
check("违例16/17口径.gold_refs_total", loc3["gold_refs_total"], 34)
check("违例16/17口径.gold_refs_hit", loc3["gold_refs_hit"], 24)
check("违例16/17口径.instances_with_full_gold_hit", loc3["instances_with_full_gold_hit"], 10)
det_by_id3 = {d["instance_id"]: d for d in d3["details"]}
check("违例16/17口径.VIO-15误判support", det_by_id3["DOC04-VIO-15"]["predicted"], "support")
check("违例16/17口径.VIO-17检出", det_by_id3["DOC04-VIO-17"]["predicted"], "refute")
check("违例16/17口径.VIO-17通道coverage", det_by_id3["DOC04-VIO-17"]["refute_channels"], ["coverage_L1"])
check("违例16/17口径.VIO-17目标命中", det_by_id3["DOC04-VIO-17"]["target_hit"], True)
# 15/17-era localization numbers still cited in the reconciliation note
loc2 = d2["localization"]
approx("违例15/17口径.定位P", round(loc2["precision"], 4), 0.8519)
approx("违例15/17口径.定位R", round(loc2["recall"], 4), 0.697)
check("违例15/17口径.gold_refs_total", loc2["gold_refs_total"], 33)
check("违例15/17口径.gold_refs_hit", loc2["gold_refs_hit"], 23)
check("违例15/17口径.instances_with_full_gold_hit", loc2["instances_with_full_gold_hit"], 9)
det_by_id2 = {d["instance_id"]: d for d in d2["details"]}
check("违例15/17口径.VIO-17判NIE", det_by_id2["DOC04-VIO-17"]["predicted"], "not_in_evidence")
# evalset asset facts
check("违例集.n", len(evalset), 17)
check("违例集.期望全refute", all(r["expected_verdict"] == "refute" for r in evalset), True)
check("违例集.类别分布", sorted(r["violation_category"] for r in evalset).count("identifier"), 5)
check("违例集.answer_pattern", (sum(1 for r in evalset if r["answer_pattern"] == "assert_violation_content"),
                                sum(1 for r in evalset if r["answer_pattern"] == "assert_expected_content")), (14, 3))
check("违例集.gold_refs预填35", sum(len(r["gold_evidence_refs"]) for r in evalset), 35)

# --- Section 8.3: learned router (negative result) ---
check("路由.heldout一致率", round(rt["heldout_qa_routing"]["routing_agreement"], 4), 0.0875)
check("路由.heldout_n", rt["heldout_qa_routing"]["n"], 80)
check("路由.heldout_escalate", rt["heldout_qa_routing"]["route_distribution"]["escalate_l3"], 70)
check("路由.heldout_oracle_accept_l1", rt["heldout_qa_routing"]["oracle_distribution"]["accept_l1"], 73)
check("路由.insample一致率", round(rt["train_routing_in_sample"]["routing_agreement"], 4), 0.8233)
check("路由.EGT行数", rt["n"]["egt"], 422)
check("路由.特征行数", rt["training"]["n_train_rows"], 300)
check("路由.排除无决策点", rt["egt"]["excluded"]["no_residual_decision_point"], 122)
check("路由.EGT_oracle分布", (rt["egt"]["oracle_distribution"]["accept_l2"],
                              rt["egt"]["oracle_distribution"]["accept_l1"],
                              rt["egt"]["oracle_distribution"]["escalate_l3"]), (174, 120, 6))
check("路由.QA_oracle分布", (rt["qa_test"]["oracle_distribution"]["accept_l1"],
                             rt["qa_test"]["oracle_distribution"]["accept_l2"],
                             rt["qa_test"]["oracle_distribution"]["escalate_l3"]), (73, 5, 2))
check("路由.CV_macroF1", round(rt["training"]["models"]["gradient_boosting"]["cv_macro_f1"], 4), 0.456)
check("路由.CV_acc", round(rt["training"]["models"]["gradient_boosting"]["cv_accuracy"], 4), 0.6933)
check("路由.防泄漏.qa_ids_in_train", rt["leakage_guards"]["qa_instance_ids_in_train"], 0)
check("路由.防泄漏.qa问题重叠剔除", rt["leakage_guards"]["qa_questions_in_train_pool"], 10)
check("路由.L2_EGT_dev探测acc", round(rt["egt"]["route_outcome_accuracy"]["v_l2"]["accuracy"], 4), 0.9056)
# eval_router: five configs + oracle ceiling
approx("路由评估.baseline_macroF1", round(er["configs"]["baseline"]["macro_f1"], 4), 0.6381)
approx("路由评估.fixed_cascade", round(er["configs"]["fixed_cascade"]["macro_f1"], 4), 0.7185)
check("路由评估.fixed_cascade调用", er["llm_stats"]["fixed_cascade"]["invocations"], 15)
approx("路由评估.learned_macroF1", round(er["configs"]["learned_router"]["macro_f1"], 4), 0.7257)
check("路由评估.learned调用", er["llm_stats"]["learned_router"]["invocations"], 73)
approx("路由评估.L2_refuteP", round(er["configs"]["l2_nli"]["per_class"]["refute"]["precision"], 4), 0.3684)
approx("路由评估.oracle_macroF1", round(er["oracle_router_ceiling"]["macro_f1"], 4), 0.7867)
check("路由评估.oracle调用", er["oracle_router_ceiling"]["llm_invocations"], 2)
approx("路由评估.oracle_refuteP", round(er["oracle_router_ceiling"]["refute_precision"], 4), 0.8889)
check("路由评估.oracle_refuteR", er["oracle_router_ceiling"]["refute_recall"], 1.0)
check("路由评估.l3_llm一致", round(er["configs"]["l3_llm"]["macro_f1"], 4), round(pm["baselines"]["B4"]["macro_f1"], 4))
# feature-distribution drift numbers (doc §8.3 attribution ①, recomputed)
router_rows = [json.loads(line) for line in
               (RUNS / "router_train_7a90549c_20261027_165644/router_dataset.jsonl")
               .read_text(encoding="utf-8").splitlines() if line.strip()]
egt_rows = [r for r in router_rows if r["source"] == "egt" and not r.get("excluded")]
qa_rows = [r for r in router_rows if r["source"] == "qa_frozen" and not r.get("excluded")]


def _feature_mean(rows: list[dict], key: str) -> float:
    return round(sum(r["features"][key] for r in rows) / len(rows), 2)


for key, egt_want, qa_want in (("n_claims", 1.02, 5.01), ("question_len", 10.0, 20.64),
                               ("answer_len", 24.06, 218.34), ("n_evidence", 3.97, 6.45)):
    approx(f"路由特征.EGT.{key}", _feature_mean(egt_rows, key), egt_want, tol=0.005)
    approx(f"路由特征.QA.{key}", _feature_mean(qa_rows, key), qa_want, tol=0.005)
check("路由特征.EGT.n", len(egt_rows), 300)
check("路由特征.QA.n", len(qa_rows), 80)
# zero-trigger: no numeric_z3/coverage claim methods on the 91QA corpus
for cfg in ("baseline", "l2_nli", "l3_llm", "fixed_cascade", "learned_router"):
    methods = er["configs"][cfg]["claim_methods"]
    check(f"路由评估.{cfg}.numeric_z3零触发", "numeric_z3_expert" not in methods, True)
    check(f"路由评估.{cfg}.coverage零触发", "coverage_join" not in methods, True)

# --- Section 8.4: mutation injection miss-rate matrix ---
fm = md["family_matrix"]
check("变异.总数", fm["OVERALL"]["n_injected"], 394)
check("变异.总检出", fm["OVERALL"]["n_detected"], 41)
approx("变异.总检出率", round(fm["OVERALL"]["detection_rate"], 4), 0.1041)
check("变异.漏检NIE", fm["OVERALL"]["miss_kind_counts"]["nie"], 344)
check("变异.漏检support", fm["OVERALL"]["miss_kind_counts"]["support"], 9)
fam_want = {"GJB": (20, 5, 0.25), "TERM": (67, 13, 0.194), "BASE": (64, 6, 0.0938),
            "STRUCT": (148, 12, 0.0811), "LOGIC": (91, 5, 0.0549), "PARAM": (4, 0, 0.0)}
for fam, (n, det, rate) in fam_want.items():
    check(f"变异.{fam}.n", fm[fam]["n_injected"], n)
    check(f"变异.{fam}.detected", fm[fam]["n_detected"], det)
    approx(f"变异.{fam}.rate", round(fm[fam]["detection_rate"], 4), rate)
check("变异.算子表48个", len(md["operator_table"]), 48)
check("变异.注入集行数", len(mutation_evalset), 394)
mr = md["miss_reason_stats"]
check("变异.漏检数", mr["n_missed"], 353)
check("变异.nie_methods.semantic", mr["nie_causing_methods"]["semantic_unresolved"], 607)
check("变异.nie_methods.conservative", mr["nie_causing_methods"]["conservative_unresolved"], 148)
check("变异.false_support.identifier", mr["false_support_causing_methods"]["identifier_exact_match"], 19)
# evidence-side double-registration cross reference (real vs injected)
xr = {r["violation_category"]: r for r in md["violation_cross_reference"]["rows"]}
check("双登记.真实总数", md["violation_cross_reference"]["real_total"], 17)
check("双登记.真实检出", md["violation_cross_reference"]["real_detected"], 16)
approx("双登记.真实检出率", round(md["violation_cross_reference"]["real_detection_rate"], 4), 0.9412)
check("双登记.identifier真实", (xr["identifier"]["real_detected"], xr["identifier"]["n_real"]), (5, 5))
check("双登记.identifier注入", (xr["identifier"]["injection_detected"], xr["identifier"]["injection_n"]), (10, 19))
approx("双登记.identifier注入率", round(xr["identifier"]["injection_detection_rate"], 4), 0.5263)
check("双登记.enumeration真实", (xr["enumeration"]["real_detected"], xr["enumeration"]["n_real"]), (4, 4))
check("双登记.enumeration注入", (xr["enumeration"]["injection_detected"], xr["enumeration"]["injection_n"]), (1, 24))
approx("双登记.enumeration注入率", round(xr["enumeration"]["injection_detection_rate"], 4), 0.0417)
check("双登记.exception真实", (xr["exception_template"]["real_detected"], xr["exception_template"]["n_real"]), (2, 2))
check("双登记.exception注入", (xr["exception_template"]["injection_detected"], xr["exception_template"]["injection_n"]), (5, 91))
check("双登记.traceability无适用算子", xr["traceability"]["injection_applicable"], False)

# --- Section 8.1: numeric-fact probes (re-derived from the evidence pipeline) ---
from algorithms.consistency.evidence_compiler import (  # noqa: E402
    load_content_list_evidence,
    load_figure_evidence,
)
from algorithms.consistency.evidence_statements import linearize_evidence  # noqa: E402
from algorithms.consistency.numeric_z3_expert import extract_numeric_facts  # noqa: E402
from algorithms.consistency.qa_models import RetrievedEvidence, SourceRef  # noqa: E402

doc04_evs = list(load_content_list_evidence("04*")) + list(load_figure_evidence("04"))
n_doc04 = sum(len(extract_numeric_facts(linearize_evidence(ev))) for ev in doc04_evs)
check("数值事实.04全文档92", (len(doc04_evs), n_doc04), (424, 92))


def _frozen_numeric_facts(path: str) -> int:
    from collections import OrderedDict
    blocks: "OrderedDict[str, dict]" = OrderedDict()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        for ev in json.loads(line).get("evidence", []):
            sid = ev.get("evidence_id")
            if sid and sid not in blocks:
                blocks[sid] = ev
    n = 0
    for sid, ev in blocks.items():
        re_ = RetrievedEvidence(
            evidence_id=str(sid), text=str(ev["text"]),
            source_type=ev["source_type"], source_ref=SourceRef(**ev["source_ref"]),
            scope_id=str(ev["scope_id"]))
        n += len(extract_numeric_facts(linearize_evidence(re_)))
    return n


check("数值事实.91QA冻结0", _frozen_numeric_facts("data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"), 0)
check("数值事实.违例集22", _frozen_numeric_facts("data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"), 22)

# --- Section 10.1: frozen dev/test split + honest test evaluation ---
check("切分.seed", split_v1["seed"], 42)
check("切分.n_total", split_v1["n_total"], 91)
check("切分.n_clusters", split_v1["n_clusters"], 29)
check("切分.dev_n", len(split_v1["dev"]), 45)
check("切分.test_n", len(split_v1["test"]), 46)
check("切分.簇数", len(split_v1["cluster_assignment"]), 29)
check("切分.零交集", set(split_v1["dev"]) & set(split_v1["test"]), set())
check("切分.并集=全集", set(split_v1["dev"]) | set(split_v1["test"]), set(frozen_by_id))
dev_dist = {"support": 0, "refute": 0, "not_in_evidence": 0}
test_dist = {"support": 0, "refute": 0, "not_in_evidence": 0}
cross_side = []
for iid in split_v1["dev"]:
    dev_dist[silver_labels[iid]] += 1
    if split_v1["cluster_assignment"][split_v1["cluster_map"][iid]] != "dev":
        cross_side.append(iid)
for iid in split_v1["test"]:
    test_dist[silver_labels[iid]] += 1
    if split_v1["cluster_assignment"][split_v1["cluster_map"][iid]] != "test":
        cross_side.append(iid)
check("切分.dev银分布S3R4N38", (dev_dist["support"], dev_dist["refute"], dev_dist["not_in_evidence"]), (3, 4, 38))
check("切分.test银分布S3R4N39", (test_dist["support"], test_dist["refute"], test_dist["not_in_evidence"]), (3, 4, 39))
check("切分.同主题零跨侧", cross_side, [])
check("切分.银分布自报一致", (split_v1["silver_distribution"]["dev"],
                                split_v1["silver_distribution"]["test"]), (dev_dist, test_dist))
# dev grid sweep: 60 configs collapse onto 3 distinct macro-F1 values
grid = cal["grid_rows"]
check("扫参.配置数", len(grid), 60)
f1_counts: dict[float, int] = {}
for row in grid:
    f1_counts[row["macro_f1"]] = f1_counts.get(row["macro_f1"], 0) + 1
check("扫参.F1值个数", len(f1_counts), 3)
check("扫参.F1分布", (f1_counts[0.6626], f1_counts[0.6678], f1_counts[0.7353]), (40, 5, 15))
check("扫参.最优参数", (cal["best"]["nli_gate"], cal["best"]["cascade_keep_confidence"],
                        cal["best"]["llm_refute_gate"]), (0.9, None, 0.6))
check("扫参.最优dev_macroF1", cal["best"]["macro_f1"], 0.7353)
check("扫参.最优调用数", cal["best"]["llm_invocations"], 4)
check("冻结指针.tuned参数", (tuned_cfg["nli_gate"], tuned_cfg["cascade_keep_confidence"],
                              tuned_cfg["llm_refute_gate"]), (0.9, None, 0.6))
check("冻结指针.dev_macroF1", tuned_cfg["dev_macro_f1"], 0.7353)
# honest test, pre-fix (185819)
c = th_pre["configs"]["current_default"]
approx("诚实test前.macroF1", round(c["macro_f1"], 4), 0.704)
approx("诚实test前.acc", round(c["accuracy"], 4), 0.913)
approx("诚实test前.R_F1", round(c["per_class"]["refute"]["f1"], 4), 0.75)
approx("诚实test前.R_P", round(c["per_class"]["refute"]["precision"], 4), 0.75)
approx("诚实test前.S_F1", round(c["per_class"]["support"]["f1"], 4), 0.4)
check("诚实test前.LLM", (c["llm_invocations"], c["llm_api_calls"]), (10, 0))
check("诚实test前.legacy参照", (th_pre["legacy_reference"]["macro_f1"],
                                  th_pre["legacy_reference"]["refute_f1"],
                                  th_pre["legacy_reference"]["llm_invocations"]), (0.7185, 0.8, 15))
approx("诚实test前.乐观偏差", round(th_pre["optimistic_bias"]["macro_f1"], 4), 0.0145)
approx("诚实test前.乐观偏差R", round(th_pre["optimistic_bias"]["refute_f1"], 4), 0.05)
check("诚实test前.dev调参零分歧", (th_pre["generalization"]["dev_tuned_minus_current_default_on_test"]["macro_f1"],
                                    th_pre["generalization"]["dev_tuned_minus_current_default_on_test"]["refute_f1"]), (0.0, 0.0))
check("诚实test前.053误refute", {r["instance_id"]: r["predicted"] for r in th_pre["per_instance"]["current_default"]}["S1QA-053"], "refute")
# honest test, post-fix (195753)
c2 = th_post["configs"]["current_default"]
approx("诚实test后.macroF1", round(c2["macro_f1"], 4), 0.8286)
approx("诚实test后.acc", round(c2["accuracy"], 4), 0.9348)
approx("诚实test后.R_P", round(c2["per_class"]["refute"]["precision"], 4), 1.0)
approx("诚实test后.R_F1", round(c2["per_class"]["refute"]["f1"], 4), 0.8571)
approx("诚实test后.S_R", round(c2["per_class"]["support"]["recall"], 4), 0.6667)
approx("诚实test后.S_F1", round(c2["per_class"]["support"]["f1"], 4), 0.6667)
approx("诚实test后.N_F1", round(c2["per_class"]["not_in_evidence"]["f1"], 4), 0.962)
check("诚实test后.LLM", (c2["llm_invocations"], c2["llm_api_calls"]), (10, 0))
check("诚实test后.dev_tuned同分", round(th_post["configs"]["dev_tuned"]["macro_f1"], 4), round(c2["macro_f1"], 4))
check("诚实test后.dev_tuned调用", th_post["configs"]["dev_tuned"]["llm_invocations"], 7)
approx("诚实test后.混合口径偏差", round(th_post["optimistic_bias"]["macro_f1"], 4), -0.1101)
check("诚实test后.053翻正", {r["instance_id"]: r["predicted"] for r in th_post["per_instance"]["current_default"]}["S1QA-053"], "support")
check("诚实test后.066仍NIE", {r["instance_id"]: r["predicted"] for r in th_post["per_instance"]["current_default"]}["S1QA-066"], "not_in_evidence")

# --- Section 10.2: P1 deterministic fixes ---
approx("全91确定性前.acc", round(silver_pre["accuracy"], 4), 0.9011)
approx("全91确定性前.macroF1", round(silver_pre["macro_f1"], 4), 0.6381)
approx("全91确定性后.acc", round(silver_post["accuracy"], 4), 0.9121)
approx("全91确定性后.macroF1", round(silver_post["macro_f1"], 4), 0.7212)
approx("全91确定性后.复测一致", round(silver_post2["macro_f1"], 4), round(silver_post["macro_f1"], 4))
check("全91确定性.support命中1→2", (silver_pre["confusion[predicted, label]"]["support|support"],
                                     silver_post["confusion[predicted, label]"]["support|support"]), (1, 2))
check("全91确定性.误refute消除", silver_post["confusion[predicted, label]"].get("refute|support", 0), 0)
# dev-side B4 after fixes (6d4e96bb)
check("dev侧B4.n", dev_b4["n"], 45)
approx("dev侧B4.acc", round(dev_b4["accuracy"], 4), 0.9556)
approx("dev侧B4.macroF1", round(dev_b4["macro_f1"], 4), 0.8875)
approx("dev侧B4.S_P", round(dev_b4["per_class"]["support"]["precision"], 4), 1.0)
approx("dev侧B4.S_R", round(dev_b4["per_class"]["support"]["recall"], 4), 0.6667)
approx("dev侧B4.R_R", round(dev_b4["per_class"]["refute"]["recall"], 4), 1.0)
approx("dev侧B4.R_F1", round(dev_b4["per_class"]["refute"]["f1"], 4), 0.8889)
# violation set zero regression after the P1 fixes
d4 = v4["configs"]["deterministic"]
d5 = v5["configs"]["deterministic"]
check("违例修复后.n_detected", (d4["n_detected"], d5["n_detected"]), (16, 16))
approx("违例修复后.detection_rate", round(d4["detection_rate"], 4), 0.9412)
check("违例修复后.undetected", d4["undetected_ids"], ["DOC04-VIO-15"])
check("违例修复后.cascade同样16", v4["configs"]["cascade"]["n_detected"], 16)
check("违例修复后.通道归因不变", d4["refute_channels"], d3["refute_channels"])
det_by_id4 = {d["instance_id"]: d for d in d4["details"]}
check("违例修复后.VIO-03检出", det_by_id4["DOC04-VIO-03"]["detected"], True)
check("违例修复后.VIO-03目标命中", det_by_id4["DOC04-VIO-03"]["target_hit"], True)
check("违例修复后.VIO-03锚点收窄", det_by_id4["DOC04-VIO-03"]["refute_block_refs"], ["DOC04-VIO-03-ev-000267"])
loc4 = d4["localization"]
check("违例修复后.定位gold命中", (loc4["gold_refs_total"], loc4["gold_refs_hit"]), (34, 23))
approx("违例修复后.定位P", round(loc4["precision"], 4), 0.7931)
approx("违例修复后.定位R", round(loc4["recall"], 4), 0.6765)
check("违例修复后.全gold命中实例数", loc4["instances_with_full_gold_hit"], 10)

# --- Section 10.3: crossdoc06 sound evalset + generalization gap ---
check("跨文档.构建n", cd_build["total"], 30)
from collections import Counter  # noqa: E402

sound_dist = Counter(r["sound_label"] for r in crossdoc_evalset)
check("跨文档.评测集n", len(crossdoc_evalset), 30)
check("跨文档.sound分布S10R10N10", (sound_dist["support"], sound_dist["refute"],
                                     sound_dist["not_in_evidence"]), (10, 10, 10))
check("跨文档.label_proof全覆盖", all(r.get("label_proof") for r in crossdoc_evalset), True)
det_m = cd_post["configs"]["deterministic"]["metrics"]
cas_m = cd_post["configs"]["cascade"]["metrics"]
approx("跨文档.det_macroF1", round(det_m["macro_f1"], 4), 0.1524)
approx("跨文档.det_acc", round(det_m["accuracy"], 4), 0.2667)
approx("跨文档.cascade_macroF1", round(cas_m["macro_f1"], 4), 0.5309)
approx("跨文档.cascade_acc", round(cas_m["accuracy"], 4), 0.5333)
check("跨文档.det支持召回零", det_m["per_class"]["support"]["recall"], 0.0)
check("跨文档.det反驳召回零", det_m["per_class"]["refute"]["recall"], 0.0)
approx("跨文档.cascade_S_R", round(cas_m["per_class"]["support"]["recall"], 4), 0.4)
approx("跨文档.cascade_R_R", round(cas_m["per_class"]["refute"]["recall"], 4), 0.5)
g = cd_post["generalization_gap"]
approx("跨文档.gap_det", round(g["deterministic"]["delta_macro_f1"], 4), -0.4857)
approx("跨文档.gap_det_04侧", round(g["deterministic"]["doc04_macro_f1"], 4), 0.6381)
approx("跨文档.gap_cascade", round(g["cascade"]["delta_macro_f1"], 4), -0.1876)
approx("跨文档.gap_cascade_04侧", round(g["cascade"]["doc04_macro_f1"], 4), 0.7185)
# P1 fixes give zero improvement on doc06: pre-fix run bit-identical
check("跨文档.P1零改善.det", round(cd_pre["configs"]["deterministic"]["metrics"]["macro_f1"], 4),
      round(det_m["macro_f1"], 4))
check("跨文档.P1零改善.cascade", round(cd_pre["configs"]["cascade"]["metrics"]["macro_f1"], 4),
      round(cas_m["macro_f1"], 4))
det_attr = cd_post["configs"]["deterministic"]["attribution"]
cd_by_id = {m["instance_id"]: m for m in det_attr["misclassified"]}
check("跨文档.numeric_z3伪refute", (cd_by_id["C06QA-008"]["gold"], cd_by_id["C06QA-008"]["pred"],
                                     cd_by_id["C06QA-008"]["decisive"]), ("support", "refute", ["numeric_z3_expert"]))
check("跨文档.误support_16", (cd_by_id["C06QA-016"]["gold"], cd_by_id["C06QA-016"]["pred"]), ("refute", "support"))
check("跨文档.误support_17", (cd_by_id["C06QA-017"]["gold"], cd_by_id["C06QA-017"]["pred"]), ("refute", "support"))

# --- Section 10.4: gold annotation workbench asset ---
check("标注工作台.实例数", len(pre_annotated), 108)
check("标注工作台.claim数", sum(len(r.get("claims", [])) for r in pre_annotated), 525)

# --- Run directory existence (Test-Path equivalent) ---
run_dirs = [
    "eval_paper_matrix_c409df7f_20261027_125551",
    "eval_cascade_1e92cdce_20261027_124941",
    "eval_violations_5d5c92a8_20261027_113100",
    "eval_violations_5d5c92a8_20261027_120749",
    "eval_violations_5d5c92a8_20261027_124733",
    "eval_violations_5d5c92a8_20261027_165400",
    "eval_violations_664fe616_20261027_160651",
    "router_train_7a90549c_20261027_165644",
    "eval_router_2b76c358_20261027_170640",
    "eval_mutation_detection_750b7b7d_20261027_165008",
    "eval_mutation_detection_750b7b7d_20261027_164708",
    "eval_paper_matrix_0fabaced_20261027_023711",
    "eval_cascade_1e92cdce_20261027_024429",
    "eval_cascade_1e92cdce_20261027_022407",
    "eval_cascade_1e92cdce_20261027_023405",
    "eval_cascade_1e92cdce_20261027_023644",
    "eval_llm_residual_5dd69927_20261026_173434",
    "build_egt_dataset_3a52cd3f_20261026_154036",
    "build_egt_dataset_2f65089e_20261026_163247",
    "build_egt_dataset_721c8665_20261026_165547",
    "build_egt_dataset_8a8716bb_20261027_003528",
    "train_residual_nli_ade325ae_20261026_195906",
    "train_residual_nli_acfead4b_20261027_013647",
    "train_residual_nli_24ea638f_20261027_005544",
    "train_residual_nli_5e6a315f_20261027_011013",
    "train_residual_nli_acfead4b_20261027_003550",
    "eval_nli_residual_4971ceba_20261026_201247",
    "eval_nli_residual_2996af6b_20261027_015457",
    "eval_test_honest_6740ed5c_20261027_185819",
    "eval_test_honest_6740ed5c_20261027_195753",
    "calibrate_on_dev_a069227d_20261027_185110",
    "eval_qa_module_silver_f119425e_20261027_190326",
    "eval_qa_module_silver_f119425e_20261027_194154",
    "eval_qa_module_silver_f119425e_20261027_195515",
    "eval_qa_dev_split_6d4e96bb_20261027_195532",
    "eval_violations_5d5c92a8_20261027_191329",
    "eval_violations_5d5c92a8_20261027_195407",
    "eval_violations_5d5c92a8_20261027_195501",
    "eval_violations_664fe616_20261027_194204",
    "eval_crossdoc_27e8ce32_20261027_190259",
    "eval_crossdoc_27e8ce32_20261027_195859",
    "build_crossdoc_evalset_1a7c8719_20261027_190350",
    "diagnose_support_misses_159abe4c_20261027_185946",
]
for d in run_dirs:
    check(f"存在 {d}", (RUNS / d / "result.json").exists(), True)
# Wave 6/7 runs' git_sha (config.json, runs protocol)
for d in ("eval_violations_5d5c92a8_20261027_165400",
          "router_train_7a90549c_20261027_165644",
          "eval_router_2b76c358_20261027_170640",
          "eval_mutation_detection_750b7b7d_20261027_165008",
          "eval_test_honest_6740ed5c_20261027_185819",
          "eval_test_honest_6740ed5c_20261027_195753",
          "calibrate_on_dev_a069227d_20261027_185110",
          "eval_qa_module_silver_f119425e_20261027_195515",
          "eval_qa_dev_split_6d4e96bb_20261027_195532",
          "eval_violations_5d5c92a8_20261027_195407",
          "eval_crossdoc_27e8ce32_20261027_195859",
          "build_crossdoc_evalset_1a7c8719_20261027_190350"):
    cfg = json.loads((RUNS / d / "config.json").read_text(encoding="utf-8"))
    check(f"git_sha {d}", cfg.get("git_sha"), "ff0d4950")

# --- Doc contains the key headline numbers ---
text = DOC.read_text(encoding="utf-8")
for token in ["0.6381", "0.7257", "0.8000", "0.7185", "0.857", "15(0/15)",
              "52.9%", "70.6%", "88.2%", "94.1%", "+35.3pp",
              "0.7799", "0.6997", "124/181", "0.2857", "0.9052", "0.932",
              "0.9648", "0.4963", "0.5437", "0.875", "-0.152", "-0.088",
              "-0.039", "-0.026", "-0.017", "0.0260", "0.666",
              "id_join_expert.py", "enum_join_expert.py",
              "numeric_z3_expert.py", "coverage_expert.py", "router.py",
              "violation_evalset_v1.jsonl", "mutation_injection_evalset_v1.jsonl",
              "eval_paper_matrix_c409df7f_20261027_125551",
              "eval_cascade_1e92cdce_20261027_124941",
              "eval_violations_5d5c92a8_20261027_124733",
              "eval_violations_5d5c92a8_20261027_165400",
              "eval_router_2b76c358_20261027_170640",
              "router_train_7a90549c_20261027_165644",
              "eval_mutation_detection_750b7b7d_20261027_165008",
              "VIO-15", "VIO-17", "数字已核对",
              "16/17", "10.4%", "0.0875", "0.7867", "0.526", "0.042",
              "Wave 6", "证据侧双登记", "92条", "0.9056", "0.3684",
              "算法侧完成声明", "coverage_L1", "coverage_join", "numeric_z3_expert",
              # Wave 7 (audit response + honest evaluation)
              "Wave 7", "审计响应与诚实评测", "审计-响应对照表",
              "dev_test_split_v1.json", "crossdoc06_evalset_v1.jsonl",
              "eval_test_honest_6740ed5c_20261027_185819",
              "eval_test_honest_6740ed5c_20261027_195753",
              "calibrate_on_dev_a069227d_20261027_185110",
              "eval_qa_module_silver_f119425e_20261027_190326",
              "eval_qa_module_silver_f119425e_20261027_195515",
              "eval_qa_dev_split_6d4e96bb_20261027_195532",
              "eval_violations_5d5c92a8_20261027_195407",
              "eval_crossdoc_27e8ce32_20261027_195859",
              "build_crossdoc_evalset_1a7c8719_20261027_190350",
              "0.704", "0.8286", "0.9348", "0.7212", "0.8875",
              "0.0145", "-0.1101", "2.0%", "+0.0145",
              "5/6", "2/6", "16/17零回退", "23/34", "0.7931", "0.6765",
              "0.1524", "0.5309", "-0.4857", "-0.1876", "S/R/N各10",
              "60配置", "0.6626", "0.6678", "0.7353",
              "C06QA-008", "C06QA-016", "numeric_z3跨行误join", "运行支撑服务",
              "build_annotation_sheet.py", "collect_gold_annotation.py",
              "finalize_gold.py", "525", "6-9",
              "S1QA-066", "S1QA-053", "077留P2",
              "口径警告", "零改善", "同主题零跨侧", "S3/R4/N38", "S3/R4/N39"]:
    check(f"文档含 {token}", token in text, True)

n_pass = sum(1 for _, ok in results if ok)
print(f"PASS {n_pass}/{len(results)}")
sys.exit(0 if n_pass == len(results) else 1)
