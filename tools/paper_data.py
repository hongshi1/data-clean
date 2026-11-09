r"""CascadeVerify论文资产的数据提取层: 全部数字从runs的result.json程序化读取.

单一事实源: make_paper_figures.py 与 make_paper_tables.py 共享本模块,
保证图/表数字一致且可复现(禁止手抄数字). 每个提取函数标注源run目录,
关键run用checkpoint/规模断言保护, 防止run目录错配.

D1蒸馏(2026-11-09): gate=0.7口径读eval_distilled_v1.json交叉校验,
gate=0.8(dev校准)读distillation/d1_paper_summary_v1.json(session数字登记).
E2跨文档蒸馏+共识门控(2026-11-10): get_e2_loo()/get_consensus_ablation()
读distillation/e2_loo_*_results_v1.json与runs/eval_consensus_*,
与distillation/e2_paper_summary_v1.json交叉校验(D1数字回链d1_paper_summary).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
RUNS = BASE / "data/gjb_438c/runs"

RUN_PAPER_MATRIX = "eval_paper_matrix_c409df7f_20261027_125551"
RUN_CASCADE = "eval_cascade_1e92cdce_20261027_124941"
RUN_TEST_HONEST_POSTFIX = "eval_test_honest_6740ed5c_20261027_195753"
RUN_TEST_HONEST_PREFIX = "eval_test_honest_6740ed5c_20261027_185819"
RUN_MUTATION = "eval_mutation_detection_750b7b7d_20261027_165008"
RUN_CROSSDOC = "eval_crossdoc_27e8ce32_20261027_195859"
RUN_ROUTER = "eval_router_2b76c358_20261027_170640"
RUN_ROUTER_TRAIN = "router_train_7a90549c_20261027_165644"
RUN_VIOLATION_BASELINE = "eval_violations_5d5c92a8_20261027_113100"
RUN_VIOLATION_ID_JOIN = "eval_violations_5d5c92a8_20261027_120749"
RUN_VIOLATION_ENUM_JOIN = "eval_violations_5d5c92a8_20261027_124733"
RUN_VIOLATION_COVERAGE = "eval_violations_5d5c92a8_20261027_165400"
RUN_EGT_NEAR_TRAIN = "train_residual_nli_ade325ae_20261026_195906"
RUN_EGT_NEAR_EVAL = "eval_nli_residual_4971ceba_20261026_201247"
RUN_EGT_NARR_TRAIN = "train_residual_nli_acfead4b_20261027_013647"
RUN_FP16_MIN = "eval_nli_residual_2996af6b_20261027_003240"
RUN_FP16_MAX = "eval_nli_residual_2996af6b_20261026_212915"
RUN_D1_TRAIN = "train_distilled_nli_b3838652_20261109_200219"
RUN_CONSENSUS = "eval_consensus_8624d45a_20261109_225618"

D1_DIR = BASE / "data/gjb_438c/distillation"
D1_SUMMARY = D1_DIR / "d1_paper_summary_v1.json"
E2_LOO_V1 = D1_DIR / "e2_loo_results_v1.json"
E2_LOO_V2 = D1_DIR / "e2_loo_curriculum_results_v1.json"
E2_LOO_V3 = D1_DIR / "e2_loo_mixed_noos_results_v1.json"
E2_SUMMARY = D1_DIR / "e2_paper_summary_v1.json"
E2_TEACHER_CROSSDOC = D1_DIR / "teacher_labels_crossdoc.jsonl"


def load_run(name: str) -> dict[str, Any]:
    """读取一个run的result.json(UTF-8), 缺失即报错(不静默)."""
    p = RUNS / name / "result.json"
    if not p.exists():
        raise FileNotFoundError(f"run缺失: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def get_paper_matrix() -> dict[str, Any]:
    """B0-B5基线/10项消融/bootstrap: eval_paper_matrix_c409df7f_20261027_125551."""
    d = load_run(RUN_PAPER_MATRIX)
    assert d["n"] == 91 and set(d["baselines"]) == {"B0", "B1", "B2", "B3", "B4", "B5"}
    return d


def get_cascade_run() -> dict[str, Any]:
    """五配置级联+conformal+LLM调用统计: eval_cascade_1e92cdce_20261027_124941.

    checkpoint=egt_finetuned_v2(叙事文法), nli_gate=0.7.
    """
    d = load_run(RUN_CASCADE)
    assert d["n"] == 91 and d["checkpoint"].endswith("egt_finetuned_v2")
    assert set(d["configs"]) >= {"baseline", "l2_nli", "l3_llm", "cascade", "cascade_conformal"}
    return d


def get_violation_evolution() -> list[dict[str, Any]]:
    """17真实违例检出演进四阶段(deterministic配置), 每阶段一个run.

    源: eval_violations_5d5c92a8_20261027_{113100,120749,124733,165400}.
    """
    stages = [
        ("5专家栈(基线)", RUN_VIOLATION_BASELINE),
        ("+id_join", RUN_VIOLATION_ID_JOIN),
        ("+enum_join", RUN_VIOLATION_ENUM_JOIN),
        ("+coverage(终态)", RUN_VIOLATION_COVERAGE),
    ]
    out: list[dict[str, Any]] = []
    for label, run in stages:
        det = load_run(run)["configs"]["deterministic"]
        assert det["n"] == 17
        cat = det["by_category"]
        out.append({
            "stage": label,
            "run": run,
            "n": det["n"],
            "detected": det["n_detected"],
            "rate": det["detection_rate"],
            "identifier": (cat["identifier"]["detected"], cat["identifier"]["n"]),
            "enumeration": (cat["enumeration"]["detected"], cat["enumeration"]["n"]),
            "traceability": (cat["traceability"]["detected"], cat["traceability"]["n"]),
            "undetected": det["undetected_ids"],
        })
    assert [r["detected"] for r in out] == [9, 12, 15, 16]
    return out


def get_mutation_run() -> dict[str, Any]:
    """变异注入矩阵(6族×394注入)+真实违例交叉对照: 750b7b7d_20261027_165008."""
    d = load_run(RUN_MUTATION)
    assert d["family_matrix"]["OVERALL"]["n_injected"] == 394
    return d


def get_crossdoc_run() -> dict[str, Any]:
    """跨文档泛化gap(04号→06号, sound标签): eval_crossdoc_27e8ce32_20261027_195859."""
    d = load_run(RUN_CROSSDOC)
    assert d["evalset"]["n"] == 30 and d["generalization_gap"]["available"]
    return d


def get_router_run() -> dict[str, Any]:
    """路由α扫描Pareto点+cost_quality表+oracle上限: eval_router_2b76c358_20261027_170640."""
    d = load_run(RUN_ROUTER)
    assert d["n"] == 91 and len(d["pareto_points"]) >= 8
    return d


def get_router_heldout() -> dict[str, Any]:
    """学习路由器held-out路由一致率: router_train_7a90549c_20261027_165644."""
    d = load_run(RUN_ROUTER_TRAIN)
    h = d["heldout_qa_routing"]
    assert h["n"] == 80 and h["routing_agreement"] == 0.0875
    return h


def get_test_honest_rows() -> list[dict[str, Any]]:
    """test诚实评测四口径: 修复前(185819)/修复后(195753)/dev-tuned/legacy全91自评.

    legacy口径取eval_router fixed_cascade(同配置全91自评, 含acc与per_class).
    """
    pre = load_run(RUN_TEST_HONEST_PREFIX)["configs"]["current_default"]
    post_run = load_run(RUN_TEST_HONEST_POSTFIX)
    post = post_run["configs"]["current_default"]
    dev = post_run["configs"]["dev_tuned"]
    legacy = load_run(RUN_ROUTER)["configs"]["fixed_cascade"]
    assert post["macro_f1"] == 0.8286 and pre["macro_f1"] == 0.704
    rows = [
        {"label": "legacy全91自评(fixed_cascade)", "run": RUN_ROUTER, "cfg": legacy,
         "llm": load_run(RUN_ROUTER)["llm_stats"]["fixed_cascade"]["invocations"]},
        {"label": "test修复前(current-default)", "run": RUN_TEST_HONEST_PREFIX, "cfg": pre,
         "llm": pre["llm_invocations"]},
        {"label": "test修复后(current-default)", "run": RUN_TEST_HONEST_POSTFIX, "cfg": post,
         "llm": post["llm_invocations"]},
        {"label": "test(dev-tuned)", "run": RUN_TEST_HONEST_POSTFIX, "cfg": dev,
         "llm": dev["llm_invocations"]},
    ]
    return rows


def get_egt_grammar() -> dict[str, dict[str, float]]:
    """EGT两种训练文法的dev与91QA真实迁移数字(文法定律的源数据).

    近拷贝文法: train=ade325ae(ckpt egt_finetuned, dev 0.9648)
                real=eval_nli_residual_4971ceba(nli_residual口径)
    叙事文法:   train=acfead4b(ckpt egt_finetuned_v2, dev 0.9722)
                real=eval_cascade l2_nli(checkpoint egt_finetuned_v2)
    """
    near_tr = load_run(RUN_EGT_NEAR_TRAIN)
    narr_tr = load_run(RUN_EGT_NARR_TRAIN)
    assert near_tr["checkpoint"].endswith("egt_finetuned")
    assert narr_tr["checkpoint"].endswith("egt_finetuned_v2")
    near_ev = load_run(RUN_EGT_NEAR_EVAL)
    assert near_ev["checkpoint"].endswith("egt_finetuned")
    cascade = load_run(RUN_CASCADE)
    l2 = cascade["configs"]["l2_nli"]
    return {
        "near_copy": {
            "dev_macro_f1": near_tr["dev_metrics"]["macro_f1"],
            "real_macro_f1": near_ev["nli_residual"]["macro_f1"],
            "real_refute_recall": near_ev["nli_residual"]["per_class"]["refute"]["recall"],
        },
        "narrative": {
            "dev_macro_f1": narr_tr["dev_metrics"]["macro_f1"],
            "real_macro_f1": l2["macro_f1"],
            "real_refute_recall": l2["per_class"]["refute"]["recall"],
        },
    }


def get_fp16_range() -> tuple[float, float]:
    """fp16训练波动: 同日两次独立评测的macro-F1端点(0.4325 / 0.5298)."""
    lo = load_run(RUN_FP16_MIN)["nli_residual"]["macro_f1"]
    hi = load_run(RUN_FP16_MAX)["nli_residual"]["macro_f1"]
    assert (lo, hi) == (0.4325, 0.5298)
    return lo, hi


def get_conformal_two_tier() -> dict[str, Any]:
    """conformal两档(kept高置信/escalated)的refute精度: eval_cascade conformal_two_tier."""
    d = load_run(RUN_CASCADE)["conformal_two_tier"]
    assert d["kept_tier_ge_keep_confidence"]["precision"] == 0.0
    return d


def get_l2_false_refute() -> tuple[int, int]:
    """L2单独运行的预测refute总数与其中错误数(19个预测里12伪).

    从l2_nli混淆矩阵[predicted|silver]行加总.
    """
    conf = load_run(RUN_CASCADE)["configs"]["l2_nli"]["confusion[predicted, silver]"]
    n_pred = sum(v for k, v in conf.items() if k.startswith("refute|"))
    n_correct = conf.get("refute|refute", 0)
    assert (n_pred, n_correct) == (19, 7)
    return n_pred, n_pred - n_correct


def get_d1_distillation() -> dict[str, Any]:
    """D1 LLM仲裁蒸馏(GLM-5.3教师→本地NLI残差, 推理零API)全部数字.

    源: data/gjb_438c/distillation/d1_paper_summary_v1.json(2026-11-09登记).
    gate=0.7口径与eval_distilled_v1.json逐位交叉校验(防誊抄漂移);
    gate=0.8(dev-45校准)来自tools/calibrate_distilled_gate.py的session
    stdout(该脚本未落run, 登记文件即数字来源). 训练run:
    train_distilled_nli_b3838652_20261109_200219(只吃dev-45教师标签,
    test-46/violations-17/crossdoc-150训练不可见).
    """
    if not D1_SUMMARY.exists():
        raise FileNotFoundError(f"D1登记缺失: {D1_SUMMARY}")
    d = json.loads(D1_SUMMARY.read_text(encoding="utf-8"))
    t = d["test46"]
    dev = t["distilled_v1_gate_dev"]
    assert dev["accuracy"] == 0.9130 and dev["macro_f1"] == 0.8047
    assert dev["refute"]["precision"] == 0.67 and dev["refute"]["f1"] == 0.8
    assert t["egt_finetuned_v2"]["macro_f1"] == 0.5911
    assert t["distilled_v1_gate07"]["macro_f1"] == 0.7758
    # gate=0.7口径与工具产物逐位交叉校验
    ev = json.loads((D1_DIR / "eval_distilled_v1.json").read_text(encoding="utf-8"))
    for key, src in (("egt_finetuned_v2", "egt_finetuned_v2|gate=0.7|test46"),
                     ("distilled_v1_gate07", "distilled_v1|gate=0.7|test46")):
        row = t[key]
        assert row["accuracy"] == ev[src]["accuracy"], f"{key} accuracy漂移"
        assert row["macro_f1"] == ev[src]["macro_f1"], f"{key} macro_f1漂移"
        assert row["refute"]["f1"] == ev[src]["per_class"]["refute"]["f1"]
    vio = d["violations17"]["distilled_v1"]
    vio_src = ev["distilled_v1|gate=0.7|violations"]["per_class"]["refute"]
    assert (vio["detected"], vio["n"]) == (16, 17)
    assert vio["refute"]["f1"] == vio_src["f1"] == 0.9697
    assert d["crossdoc150"]["distilled_v1"]["accuracy"] == 0.5133
    assert d["setup"]["gate"] == 0.8
    assert d["setup"]["teacher"]["label_dist"] == {
        "not_in_evidence": 239, "support": 103, "refute": 13}
    tr = load_run(RUN_D1_TRAIN)
    assert tr["checkpoint"].endswith("distilled_v1")
    assert d["setup"]["train"]["run"] == RUN_D1_TRAIN
    return d


def get_e2_loo() -> dict[str, Any]:
    """E2 leave-one-doc-out跨文档蒸馏迁移分析(诚实负结果)全部数字.

    源: data/gjb_438c/distillation/e2_loo_results_v1.json(v1单阶段+3x refute
    过采样)/e2_loo_curriculum_results_v1.json(v2两阶段课程: crossdoc泛化→
    qa91-dev域内退火)/e2_loo_mixed_noos_results_v1.json(v3单阶段无过采样);
    训练工具tools/train_distilled_nli.py(--base-dir/--exclude-doc, 每fold
    训练于qa91-dev-45教师标签+crossdoc教师标签减去1个文档, 评测held-out
    文档30实例+test-46域内回归). 登记文件e2_paper_summary_v1.json另含
    D1在crossdoc-150的gate扫描(session数字, 无run文件, 登记即来源)与
    crossdoc-150平衡构造集性质; 其变体数字与结果文件全精度值round(4)
    交叉校验, D1基线回链d1_paper_summary_v1.json.
    """
    if not E2_SUMMARY.exists():
        raise FileNotFoundError(f"E2登记缺失: {E2_SUMMARY}")
    reg = json.loads(E2_SUMMARY.read_text(encoding="utf-8"))
    files = {
        "v1_single_stage_oversample3x": E2_LOO_V1,
        "v2_curriculum_two_stage": E2_LOO_V2,
        "v3_single_stage_no_oversample": E2_LOO_V3,
    }
    variants: dict[str, Any] = {}
    for key, path in files.items():
        if not path.exists():
            raise FileNotFoundError(f"E2结果缺失: {path}")
        d = json.loads(path.read_text(encoding="utf-8"))
        assert set(d["per_fold"]) == {"C05", "C06", "C07", "C08", "C10"}
        row = {
            "held_doc_acc": d["held_doc_mean_acc"],
            "test46_macro_f1": d["test46_mean_mf1"],
            "per_fold": d["per_fold"],
        }
        # 登记文件为4位舍入数字, 与结果文件全精度值交叉校验(防誊抄漂移)
        assert round(row["held_doc_acc"], 4) == reg["loo_variants"][key]["held_doc_acc"]
        assert round(row["test46_macro_f1"], 4) == reg["loo_variants"][key]["test46_macro_f1"]
        variants[key] = row
    assert (round(variants["v1_single_stage_oversample3x"]["held_doc_acc"], 4),
            round(variants["v1_single_stage_oversample3x"]["test46_macro_f1"], 4)) == (
                0.5667, 0.6562)
    assert (round(variants["v2_curriculum_two_stage"]["held_doc_acc"], 4),
            round(variants["v2_curriculum_two_stage"]["test46_macro_f1"], 4)) == (
                0.56, 0.7014)
    assert (round(variants["v3_single_stage_no_oversample"]["held_doc_acc"], 4),
            round(variants["v3_single_stage_no_oversample"]["test46_macro_f1"], 4)) == (
                0.5667, 0.6921)
    # D1基线(无crossdoc训练)回链D1登记: crossdoc-150整集acc / test-46 macroF1
    if not D1_SUMMARY.exists():
        raise FileNotFoundError(f"D1登记缺失: {D1_SUMMARY}")
    d1 = json.loads(D1_SUMMARY.read_text(encoding="utf-8"))
    base = reg["loo_variants"]["d1_baseline"]
    assert base["held_doc_acc"] == d1["crossdoc150"]["distilled_v1"]["accuracy"] == 0.5133
    assert base["test46_macro_f1"] == d1["test46"]["distilled_v1_gate_dev"]["macro_f1"] == 0.8047
    # D1在crossdoc-150的gate扫描(session登记): acc平坦→弱项是premise分布漂移
    scan = reg["d1_gate_scan_crossdoc150"]
    assert scan["gates"] == [0.5, 0.6, 0.7, 0.8]
    assert scan["accuracy"] == [0.52, 0.5133, 0.52, 0.5133]
    # crossdoc-150性质: 教师标签156条claim, 其中refute 42(抽查验证正确)
    nature = reg["crossdoc150_nature"]
    claims = [json.loads(line) for line in
              E2_TEACHER_CROSSDOC.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_refute = sum(1 for c in claims if c["teacher_verdict"] == "refute")
    assert (len(claims), n_refute) == (156, 42)
    assert nature["teacher_refute_labeled"] == n_refute
    return {
        "registry": reg,
        "variants": variants,
        "d1_baseline": {"held_doc_acc": 0.5133, "test46_macro_f1": 0.8047},
        "gate_scan": scan,
        "crossdoc150_nature": nature,
    }


def get_consensus_ablation() -> dict[str, Any]:
    """双NLI共识门控消融(负结果): eval_consensus_8624d45a_20261109_225618.

    设计: distilled_v1判refute(gate>=0.8)且零样本Erlangshen-330M也判
    contradiction(erlang_p_contra>=erlang_gate)才保留refute. dev-45扫
    erlang_gate∈{0.4,0.5,0.6,0.7}全并列(0.7056, 基线0.6694), dev-best=0.4;
    test-46诚实结果macroF1 0.7885 vs 基线0.8047(净降-0.0162, 误杀S1QA-063).
    与e2_paper_summary_v1.json的consensus_ablation子结构交叉校验.
    """
    d = load_run(RUN_CONSENSUS)
    assert d["nli_model_path"].endswith("distilled_v1") and d["nli_gate"] == 0.8
    assert d["erlang_model"] == "erlangshen-330m"
    sweep = d["dev_sweep"]
    assert [s["erlang_gate"] for s in sweep] == [0.4, 0.5, 0.6, 0.7]
    assert all(s["metrics"]["macro_f1"] == 0.7056 for s in sweep)  # 全并列
    assert d["dev_best_gate"] == 0.4
    assert d["dev_baseline"]["macro_f1"] == 0.6694
    base, cons = d["test_baseline"], d["test_consensus"]
    assert base["macro_f1"] == 0.8047 and cons["macro_f1"] == 0.7885
    assert round(cons["macro_f1"] - base["macro_f1"], 4) == -0.0162
    assert (base["per_class"]["refute"]["precision"],
            base["per_class"]["refute"]["recall"]) == (0.6667, 1.0)
    assert (cons["per_class"]["refute"]["precision"],
            cons["per_class"]["refute"]["recall"]) == (0.75, 0.75)
    # 误杀断言: 被否决的2条claim中唯一gold=refute即S1QA-063-c01(真refute)
    killed = [v for v in d["test_vetoed_claims"] if v["gold"] == "refute"]
    assert [v["claim_id"] for v in killed] == ["S1QA-063-c01"]
    # 根因: 零样本Erlangshen与distilled一致率仅33%(dev 0%)
    prof = d["refute_profile"]
    assert prof["dev"]["erlang_contra_agreement"] == 0.0
    assert round(prof["test"]["erlang_contra_agreement"], 4) == 0.3333
    # 共识基线与D1登记交叉校验(同一checkpoint+gate的test-46数字)
    if not D1_SUMMARY.exists():
        raise FileNotFoundError(f"D1登记缺失: {D1_SUMMARY}")
    d1 = json.loads(D1_SUMMARY.read_text(encoding="utf-8"))
    assert base["macro_f1"] == d1["test46"]["distilled_v1_gate_dev"]["macro_f1"]
    # 与E2登记文件交叉校验(refute P/R为2位舍入)
    if not E2_SUMMARY.exists():
        raise FileNotFoundError(f"E2登记缺失: {E2_SUMMARY}")
    t46 = json.loads(E2_SUMMARY.read_text(encoding="utf-8"))["consensus_ablation"]["test46"]
    assert (t46["baseline_macro_f1"], t46["consensus_macro_f1"]) == (0.8047, 0.7885)
    assert [round(base["per_class"]["refute"]["precision"], 2),
            round(cons["per_class"]["refute"]["precision"], 2)] == t46["refute_precision"]
    assert [base["per_class"]["refute"]["recall"],
            cons["per_class"]["refute"]["recall"]] == t46["refute_recall"]
    return d
