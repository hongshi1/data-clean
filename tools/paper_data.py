r"""CascadeVerify论文资产的数据提取层: 全部数字从runs的result.json程序化读取.

单一事实源: make_paper_figures.py 与 make_paper_tables.py 共享本模块,
保证图/表数字一致且可复现(禁止手抄数字). 每个提取函数标注源run目录,
关键run用checkpoint/规模断言保护, 防止run目录错配.
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
