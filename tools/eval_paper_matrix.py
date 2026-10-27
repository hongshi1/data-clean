"""Paper evaluation matrix (S6): B0-B5 baselines + component ablations +
paired bootstrap significance on the 91-QA frozen corpus.

Six baselines over the frozen scene1 corpus against GLM-5.3 silver labels
(S=6 / R=8 / N=77):
  B0 majority-NIE      collapse baseline: every instance predicts NIE
  B1 zero-shot NLI     QAConsistencyModule(use_experts=False,
                       use_nli_residual=True) with the RAW zero-shot
                       mDeBERTa (nli_local.MODELS["mdeberta"]); when the
                       checkpoint is unavailable the channel degrades to
                       pure semantic_unresolved NIE (recorded in the entry)
  B2 LLM direct        one cached llm_json call per QA (question + answer +
                       all evidence, three-way verdict) — no cascade
  B3 deterministic     use_experts=True, no residual channel
  B4 full cascade      the strongest L3 configuration (use_experts=True +
                       use_llm_residual=True); the qa_module residual
                       dispatch is mutually exclusive (NLI precedence), so
                       per the S6 matrix spec the L3 configuration is used
  B5 pure LLM residual use_experts=False + use_llm_residual=True

Ten ablations on the strongest configuration (B4/L3):
  -e1_expert / -entity_detector / -sequence_expert / -trace_expert
  -id_join_expert / -enum_join_expert (expert_filter = the full 7-expert
  family minus the named expert), -per_claim_fusion (fuse_per_claim=False,
  direct aggregation), -llm_residual (= B3 configuration), -all_experts
  (= B5 configuration), and the DEQ on/off comparison (use_deq=True vs
  False on B4). An extra "-join_experts" configuration (both join experts
  off) is measured for the bootstrap pair B4_vs_no_join_experts but is not
  part of the ten-row ablation table.

Paired bootstrap (1000 resamples, seed 42) on macro-F1 for the key pairs
B4 vs B3 / B4 vs B5 / B4 vs B2 / B4 vs no-join-experts (strongest = B4):
observed delta, 95% percentile CI and a two-sided sign-flip p-value.

All LLM calls go through llm_json(cache=True); per-config call statistics
count invocations (wrapped llm_json) and real API calls (llm_cache.jsonl
line growth), the rest are disk-cache hits. Results land through the runs
protocol (open_run).
"""
from __future__ import annotations

import random
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import algorithms.common.llm_client as llm_client  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    LABELS,
    build_qa_input,
    confusion_of,
    load_frozen_qa,
    load_silver_labels,
    macro_f1_raw,
    score_outcomes,
)
from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
LLM_CACHE = BASE / "data/gjb_438c/llm_cache/llm_cache.jsonl"
N_BOOT = 1000
BOOT_SEED = 42
ZERO_SHOT_NLI_KEY = "mdeberta"
L3_CONFIG = {"use_experts": True, "use_llm_residual": True}

#: the L0/L1 expert family (qa_module._expert_channels names); every
#: single-expert ablation is "full family minus one", so the removed
#: expert is the only difference to B4
EXPERT_FAMILY: tuple[str, ...] = (
    "entity", "e1", "sequence", "trace", "gjb", "id_join", "enum_join")

#: (pair name, system A, system B) — system names index outcomes_by_name
BOOTSTRAP_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("B4_vs_B3", "B4", "B3"),
    ("B4_vs_B5", "B4", "B5"),
    ("B4_vs_B2", "B4", "B2"),
    ("B4_vs_no_join_experts", "B4", "-join_experts"),
)

Outcome = dict[str, Any]


def _without(*experts: str) -> tuple[str, ...]:
    """expert_filter value = the full expert family minus the named ones."""
    return tuple(name for name in EXPERT_FAMILY if name not in experts)


# ── corpus + metrics ────────────────────────────────────────────────────────

def cache_lines() -> int:
    if not LLM_CACHE.exists():
        return 0
    return sum(1 for line in LLM_CACHE.open(encoding="utf-8") if line.strip())


# ── LLM call metering ───────────────────────────────────────────────────────

class LlmMeter:
    """Wrap llm_client.llm_json to count invocations per configuration."""

    def __init__(self) -> None:
        self.invocations = 0
        self._original = llm_client.llm_json

    def _counting(self, prompt, *args, **kwargs):
        self.invocations += 1
        return self._original(prompt, *args, **kwargs)

    def install(self) -> None:
        llm_client.llm_json = self._counting

    def restore(self) -> None:
        llm_client.llm_json = self._original


def measured_run(runner: Callable[[list[dict]], dict[str, Outcome]],
                 rows: list[dict], meter: LlmMeter) -> tuple[dict[str, Outcome], dict]:
    invocations_before = meter.invocations
    lines_before = cache_lines()
    outcomes = runner(rows)
    invocations = meter.invocations - invocations_before
    api_calls = cache_lines() - lines_before
    stats = {"invocations": invocations, "api_calls": api_calls,
             "cache_hits": invocations - api_calls}
    return outcomes, stats


# ── B0 majority-NIE ─────────────────────────────────────────────────────────

def run_majority_nie(rows: list[dict]) -> dict[str, Outcome]:
    return {row["instance_id"]: {"verdict": "not_in_evidence", "claims": []}
            for row in rows}


# ── B2 direct LLM (no cascade, one cached call per QA) ──────────────────────

_B2_SYSTEM = (
    "你是GJB军事软件需求文档的一致性审查员。给定问题、待判定answer和全部证据，"
    "判定answer属于哪种：support（证据明确支持）/refute（证据明确矛盾）/"
    "not_in_evidence（证据无法判定）。判定规则："
    "1.开放世界：证据中没有≠文档中不存在。缺失的内容（子功能名、前置条件、"
    "效果性表述、解释性扩展）只能判not_in_evidence，绝不能作为refute的依据。"
    "2.锚定：把answer断言锚定到问题所点名对象的具体功能行/用例行，只有锚定行"
    "自身的值与answer断言冲突才refute；把主体换成另一个用例/功能行后发现的"
    "差异不是矛盾。"
    "3.值判定：answer真正断言的是值（参数、设备、阶段、标识符、产物），"
    "锚定行的对应值与answer一致→support；给出不同的值→refute；"
    "没有该值→not_in_evidence。"
    "4.answer中的解释性/效果性扩展（'这意味着''包括但不限于''确保/便于'引出的"
    "内容）本身无证据时判not_in_evidence。"
    "5.拿不准时一律判not_in_evidence。"
    "证据可能包含HTML表格，字段标签可能错位，判定以内容为准。只输出JSON。"
)

_B2_SPEC = (
    '输出JSON：{"verdict": "support|refute|not_in_evidence", '
    '"evidence_refs": ["ev-1"], "rationale": "一句话理由", '
    '"confidence": 0.9}；support/refute必须在evidence_refs中引用证据编号，'
    "not_in_evidence时evidence_refs为[]。"
)

_B2_RETRY = (
    "\n\n上一次输出无法解析。请严格只输出一个JSON对象，"
    "不要markdown代码块、不要任何多余文字。"
)


def _build_direct_prompt(row: dict) -> str:
    lines = [f"【问题】{row['question']}", "", "【待判定answer】",
             str(row["answer"]).strip(), "", "【证据】"]
    for index, evidence in enumerate(row["evidence"], 1):
        text = re.sub(r"\s+", " ", str(evidence["text"])).strip()
        lines.append(f"ev-{index}: {text}")
    lines += ["", _B2_SPEC]
    return "\n".join(lines)


def _parse_direct(payload: Any) -> tuple[str, str]:
    if not isinstance(payload, dict) or not payload:
        return "", ""
    verdict = re.sub(r"\s+", "_", str(payload.get("verdict", "")).strip().lower())
    if verdict not in LABELS:
        return "", ""
    return verdict, str(payload.get("rationale", "")).strip()[:200]


def judge_direct_llm(row: dict) -> dict:
    """One cached llm_json call per QA; the raw LLM verdict is kept (no
    cascade gating) — that is the point of the direct-LLM baseline."""
    prompt = _build_direct_prompt(row)
    note = ""
    for suffix in ("", _B2_RETRY):
        try:
            payload, _model = llm_client.llm_json(
                prompt + suffix, system=_B2_SYSTEM, prefer="glm", cache=True,
                allow_fallback=False, model_override="glm-5.3",
                max_tokens=16000, timeout=300,
                extra_payload={
                    "response_contract": "json_final_content_v2",
                    "reasoning_effort": "low",
                })
        except Exception as exc:  # retried once, then conservative NIE
            note = f"{type(exc).__name__}: {exc}"
            continue
        verdict, rationale = _parse_direct(payload)
        if verdict:
            return {"verdict": verdict, "method": "direct_llm",
                    "rationale": rationale}
        note = "LLM输出无法解析为三态verdict"
    return {"verdict": "not_in_evidence", "method": "direct_llm_failed",
            "rationale": note[:200]}


def run_direct_llm(rows: list[dict]) -> dict[str, Outcome]:
    outcomes: dict[str, Outcome] = {}
    for row in rows:
        detail = judge_direct_llm(row)
        outcomes[str(row["instance_id"])] = {
            "verdict": detail["verdict"],
            "claims": [{"claim_text": str(row["answer"])[:80],
                        "verdict": detail["verdict"],
                        "method": detail["method"]}],
        }
    return outcomes


# ── module-based configurations ─────────────────────────────────────────────

def module_runner(**kwargs: Any) -> Callable[[list[dict]], dict[str, Outcome]]:
    def runner(rows: list[dict]) -> dict[str, Outcome]:
        module = QAConsistencyModule(**kwargs)
        outcomes: dict[str, Outcome] = {}
        for row in rows:
            request = build_qa_input(row)
            result = module.verify(request)
            outcomes[request.instance_id] = {
                "verdict": result.verdict,
                "claims": [{
                    "claim_id": claim.claim_id,
                    "claim_text": claim.claim_text,
                    "verdict": claim.verdict,
                    "method": claim.method,
                } for claim in result.claim_results],
            }
        return outcomes
    return runner


ConfigSpec = tuple[str, str, Callable[[list[dict]], dict[str, Outcome]], dict, str]


def config_specs() -> tuple[ConfigSpec, ...]:
    """(name, description, runner, module-kwargs-for-provenance, note)."""
    zero_shot_path = MODELS[ZERO_SHOT_NLI_KEY]["dir"]
    return (
        ("B0", "majority-NIE (collapse baseline)",
         run_majority_nie, {"mode": "majority_nie"}, ""),
        ("B1", "zero-shot NLI residual (raw mDeBERTa, no experts)",
         module_runner(use_experts=False, use_nli_residual=True,
                       nli_model_path=zero_shot_path),
         {"use_experts": False, "use_nli_residual": True,
          "nli_model_path": zero_shot_path},
         "residual dispatch keeps zero-shot channel; NIE fallback if model "
         "unavailable"),
        ("B2", "LLM direct (one call per QA, no cascade)",
         run_direct_llm, {"mode": "direct_llm", "calls_per_qa": 1}, ""),
        ("B3", "deterministic channels only (use_experts, no residual)",
         module_runner(use_experts=True), {"use_experts": True}, ""),
        ("B4", "full cascade = strongest L3 config",
         module_runner(**L3_CONFIG), dict(L3_CONFIG),
         "NLI/LLM residual dispatch is mutually exclusive; L3 config used"),
        ("B5", "pure LLM residual (no deterministic experts)",
         module_runner(use_experts=False, use_llm_residual=True),
         {"use_experts": False, "use_llm_residual": True}, ""),
    )


def ablation_specs() -> tuple[ConfigSpec, ...]:
    def single(name: str, expert: str, description: str) -> ConfigSpec:
        return (name, description,
                module_runner(**L3_CONFIG, expert_filter=_without(expert)),
                {**L3_CONFIG, "expert_filter": list(_without(expert))}, "")
    return (
        single("-e1_expert", "e1", "B4 without the E1 template expert"),
        single("-entity_detector", "entity", "B4 without the L0 entity detector"),
        single("-sequence_expert", "sequence", "B4 without the sequence expert"),
        single("-trace_expert", "trace", "B4 without the trace expert"),
        single("-id_join_expert", "id_join",
               "B4 without the ID→registry join expert"),
        single("-enum_join_expert", "enum_join",
               "B4 without the enumeration join expert"),
        ("-per_claim_fusion", "B4 without per-claim channel fusion",
         module_runner(**L3_CONFIG, fuse_per_claim=False),
         {**L3_CONFIG, "fuse_per_claim": False}, ""),
        ("-llm_residual", "B4 with the L3 residual off",
         module_runner(use_experts=True), {"use_experts": True},
         "identical configuration to B3"),
        ("-all_experts", "B4 with every deterministic expert off",
         module_runner(use_experts=False, use_llm_residual=True),
         {"use_experts": False, "use_llm_residual": True},
         "identical configuration to B5 (L3 residual working alone)"),
    )


# ── paired bootstrap ────────────────────────────────────────────────────────

def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    position = q * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + fraction * (sorted_values[upper]
                                              - sorted_values[lower])


def paired_bootstrap(pred_a: list[str], pred_b: list[str], golds: list[str],
                     *, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """1000 paired bootstrap resamples of macro-F1(a-b).

    Each comparison uses its own Random(42) stream, so every pair resamples
    the same index multiset and the p-values stay directly comparable.
    """
    n = len(golds)
    delta_obs = macro_f1_raw(confusion_of(pred_a, golds)) - macro_f1_raw(
        confusion_of(pred_b, golds))
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(n_boot):
        indices = [rng.randrange(n) for _ in range(n)]
        resample_a = [pred_a[i] for i in indices]
        resample_b = [pred_b[i] for i in indices]
        resample_g = [golds[i] for i in indices]
        deltas.append(macro_f1_raw(confusion_of(resample_a, resample_g))
                      - macro_f1_raw(confusion_of(resample_b, resample_g)))
    deltas.sort()
    le_zero = sum(1 for d in deltas if d <= 0.0)
    ge_zero = sum(1 for d in deltas if d >= 0.0)
    p_value = min(1.0, 2.0 * min(le_zero, ge_zero) / n_boot)
    return {
        "metric": "macro_f1",
        "delta": round(delta_obs, 4),
        "ci95": [round(_percentile(deltas, 0.025), 4),
                 round(_percentile(deltas, 0.975), 4)],
        "p": round(p_value, 4),
        "n_boot": n_boot,
        "seed": seed,
    }


# ── markdown tables ─────────────────────────────────────────────────────────

def _fmt(value: float) -> str:
    return f"{value:.3f}"


def _fmt_p(value: float) -> str:
    return "<0.001" if value <= 0.0 else f"{value:.3f}"


def _calls_cell(stats: dict) -> str:
    return f"{stats['api_calls']}/{stats['cache_hits']}"


def baseline_table(baselines: dict[str, dict]) -> str:
    lines = ["| system | description | acc | macro-F1 | S-F1 | R-F1 | N-F1 "
             "| LLM api/cache |",
             "|---|---|---|---|---|---|---|---|"]
    for name, entry in baselines.items():
        metrics = entry["metrics"]
        per_class = metrics["per_class"]
        lines.append(
            f"| {name} | {entry['description']} | {_fmt(metrics['accuracy'])} "
            f"| {_fmt(metrics['macro_f1'])} "
            f"| {_fmt(per_class['support']['f1'])} "
            f"| {_fmt(per_class['refute']['f1'])} "
            f"| {_fmt(per_class['not_in_evidence']['f1'])} "
            f"| {_calls_cell(entry['llm_calls'])} |")
    return "\n".join(lines)


def ablation_table(ablations: dict[str, dict], reference: dict) -> str:
    ref_f1 = reference["metrics"]["macro_f1"]
    lines = ["| ablation | description | acc | macro-F1 | Δ macro-F1 | "
             "LLM api/cache |",
             "|---|---|---|---|---|---|"]
    for name, entry in ablations.items():
        if name != "deq_on_off":
            metrics = entry["metrics"]
            lines.append(
                f"| {name} | {entry['description']} "
                f"| {_fmt(metrics['accuracy'])} | {_fmt(metrics['macro_f1'])} "
                f"| {round(metrics['macro_f1'] - ref_f1, 4):+.3f} "
                f"| {_calls_cell(entry['llm_calls'])} |")
    for tag, metrics, stats in (
            ("deq_off (B4)", reference["metrics"], reference["llm_calls"]),
            ("deq_on", ablations["deq_on_off"]["on"]["metrics"],
             ablations["deq_on_off"]["on"]["llm_calls"])):
        lines.append(
            f"| {tag} | DEQ on/off comparison on B4 | {_fmt(metrics['accuracy'])} "
            f"| {_fmt(metrics['macro_f1'])} "
            f"| {round(metrics['macro_f1'] - ref_f1, 4):+.3f} "
            f"| {_calls_cell(stats)} |")
    return "\n".join(lines)


def bootstrap_table(bootstrap: dict[str, dict]) -> str:
    lines = ["| comparison | Δ macro-F1 | 95% CI | p (two-sided) |",
             "|---|---|---|---|"]
    for name, entry in bootstrap.items():
        lines.append(
            f"| {name} | {entry['delta']:+.4f} "
            f"| [{entry['ci95'][0]:+.4f}, {entry['ci95'][1]:+.4f}] "
            f"| {_fmt_p(entry['p'])} |")
    return "\n".join(lines)


# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    started = time.time()
    rows = load_frozen_qa(QA_FROZEN)
    silver = load_silver_labels(SILVER)

    meter = LlmMeter()
    meter.install()
    try:
        baselines: dict[str, dict] = {}
        outcomes_by_name: dict[str, dict[str, Outcome]] = {}
        for name, description, runner, provenance, note in config_specs():
            t0 = time.time()
            outcomes, stats = measured_run(runner, rows, meter)
            metrics = score_outcomes(outcomes, rows, silver)
            outcomes_by_name[name] = outcomes
            baselines[name] = {
                "description": description,
                "config": provenance,
                "metrics": metrics,
                "llm_calls": stats,
                "note": note,
            }
            print(f"{name}: acc={metrics['accuracy']} "
                  f"macro_f1={metrics['macro_f1']} "
                  f"llm(api/cache)={stats['api_calls']}/{stats['cache_hits']} "
                  f"({time.time() - t0:.0f}s)", flush=True)

        ablations: dict[str, dict] = {}
        for name, description, runner, provenance, note in ablation_specs():
            t0 = time.time()
            outcomes, stats = measured_run(runner, rows, meter)
            metrics = score_outcomes(outcomes, rows, silver)
            outcomes_by_name[name] = outcomes
            ablations[name] = {
                "description": description,
                "config": provenance,
                "metrics": metrics,
                "llm_calls": stats,
                "note": note,
            }
            print(f"abl {name}: acc={metrics['accuracy']} "
                  f"macro_f1={metrics['macro_f1']} "
                  f"llm(api/cache)={stats['api_calls']}/{stats['cache_hits']} "
                  f"({time.time() - t0:.0f}s)", flush=True)

        # -join_experts: both join experts off — measured for the
        # B4_vs_no_join_experts bootstrap pair (not an ablation-table row)
        t0 = time.time()
        join_off_outcomes, join_off_stats = measured_run(
            module_runner(**L3_CONFIG,
                          expert_filter=_without("id_join", "enum_join")),
            rows, meter)
        join_off_metrics = score_outcomes(join_off_outcomes, rows, silver)
        outcomes_by_name["-join_experts"] = join_off_outcomes
        join_experts_off = {
            "description": "B4 with both join experts off",
            "config": {**L3_CONFIG,
                       "expert_filter": list(_without("id_join", "enum_join"))},
            "metrics": join_off_metrics,
            "llm_calls": join_off_stats,
            "note": "bootstrap pair B4_vs_no_join_experts; not an "
                    "ablation-table row",
        }
        print(f"abl -join_experts: acc={join_off_metrics['accuracy']} "
              f"macro_f1={join_off_metrics['macro_f1']} "
              f"llm(api/cache)={join_off_stats['api_calls']}/"
              f"{join_off_stats['cache_hits']} "
              f"({time.time() - t0:.0f}s)", flush=True)

        deq_runner = module_runner(**L3_CONFIG, use_deq=True)
        t0 = time.time()
        deq_outcomes, deq_stats = measured_run(deq_runner, rows, meter)
        deq_metrics = score_outcomes(deq_outcomes, rows, silver)
        outcomes_by_name["deq_on"] = deq_outcomes
        ablations["deq_on_off"] = {
            "description": "DEQ evidence pipeline on/off on B4",
            "config": {**L3_CONFIG, "use_deq": True},
            "on": {"metrics": deq_metrics, "llm_calls": deq_stats},
            "off": {"metrics": baselines["B4"]["metrics"],
                    "llm_calls": baselines["B4"]["llm_calls"]},
            "note": "off row reuses the B4 run (use_deq defaults to False)",
        }
        print(f"abl deq_on: acc={deq_metrics['accuracy']} "
              f"macro_f1={deq_metrics['macro_f1']} "
              f"llm(api/cache)={deq_stats['api_calls']}/{deq_stats['cache_hits']} "
              f"({time.time() - t0:.0f}s)", flush=True)
    finally:
        meter.restore()

    zero_shot_available = "nli_residual_unavailable" not in baselines["B1"][
        "metrics"]["claim_methods"]

    def verdicts(name: str) -> list[str]:
        return [outcomes_by_name[name][row["instance_id"]]["verdict"]
                for row in rows]

    golds = [silver[row["instance_id"]] for row in rows]
    bootstrap: dict[str, dict] = {}
    for pair_name, system_a, system_b in BOOTSTRAP_PAIRS:
        bootstrap[pair_name] = paired_bootstrap(
            verdicts(system_a), verdicts(system_b), golds)

    summary_table = "\n\n".join([
        "## Baselines (B0-B5)",
        baseline_table(baselines),
        "",
        "## Component ablations (on B4 = strongest L3)",
        ablation_table(ablations, baselines["B4"]),
        "",
        "## Paired bootstrap on macro-F1 "
        f"({N_BOOT} resamples, seed {BOOT_SEED})",
        bootstrap_table(bootstrap),
    ])

    def report_entry(entry: dict) -> dict:
        metrics = entry["metrics"]
        return {
            "description": entry.get("description", ""),
            "config": entry.get("config", {}),
            "note": entry.get("note", ""),
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
            "per_class": metrics["per_class"],
            "confusion[predicted, silver]": metrics["confusion[predicted, silver]"],
            "claim_methods": metrics["claim_methods"],
            "llm_calls": entry["llm_calls"],
        }

    result = {
        "n": len(rows),
        "label_type": "glm53_silver_not_gold",
        "label_distribution": dict(Counter(golds)),
        "baselines": {name: report_entry(entry)
                      for name, entry in baselines.items()},
        "ablations": {name: report_entry(entry)
                      for name, entry in ablations.items()
                      if name != "deq_on_off"} | {
            "deq_on_off": {
                "description": ablations["deq_on_off"]["description"],
                "config": ablations["deq_on_off"]["config"],
                "note": ablations["deq_on_off"]["note"],
                "on": report_entry(ablations["deq_on_off"]["on"]),
                "off": report_entry(ablations["deq_on_off"]["off"]),
            }},
        "join_experts_off": report_entry(join_experts_off),
        "bootstrap": bootstrap,
        "b1_zero_shot_nli_available": zero_shot_available,
        "strongest": "B4",
        "summary_table": summary_table,
        "runtime_seconds": round(time.time() - started, 1),
    }

    run = open_run("eval_paper_matrix", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(SILVER.relative_to(BASE)),
        "n": len(rows),
        "baselines": {name: entry["config"]
                      for name, entry in baselines.items()},
        "ablations": {name: entry["config"] for name, entry in ablations.items()},
        "bootstrap": {"n_boot": N_BOOT, "seed": BOOT_SEED,
                      "pairs": [name for name, _, _ in BOOTSTRAP_PAIRS]},
        "zero_shot_nli_key": ZERO_SHOT_NLI_KEY,
        "llm": "glm-5.3 json cache",
    })
    run.save_result(result)

    print()
    print(summary_table)
    print()
    print(f"run: {run.path}")


if __name__ == "__main__":
    main()
