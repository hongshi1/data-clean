"""公开中文三态基准上的外部baseline评测矩阵 (一致性校验论文表).

矩阵: 5外部baseline行 × 5数据集列 (每格macro-F1, 三态P/R/F1/混淆矩阵
明细进result.json):

  行: bge_centroid(BGE三元中心法) / erlangshen_zero(Erlangshen-330M零样本)
      / mdeberta_zero(mDeBERTa零样本) / cmnli_finetuned(CMNLI 50k微调,
      公开监督最强外部baseline) / glm_direct(GLM-5.3直推)
      + 对照行 egt_finetuned_v2(我们的L2域数据微调, 支撑"公开数据vs域数据")
  列: xnli_zh(5010→2000) / ocnli官方test(2950全量) / cmnli_test
      (12241→2000) / qa91(自建91条, silver) / crossdoc06(自建30条, sound)

协议 (seed=42, 全量细节落盘result.json):
  模型行: 公开测试集全量, n>3000抽2000(保序); 自建列全量
  LLM行 : 公开集从模型视图抽300; 自建集全量
  自建列适配: premise=冻结证据nli_training.build_premise(每块500/总1500
             字符), hypothesis=answer (B1旧口径走QA模块级联, 新口径直推对)
  BGE中心法fit池: OCNLI train抽2000 + CMNLI train抽3000(seed=42; 与全部
             test列零重叠: OCNLI重叠0对已校验, CMNLI 3个原始重复key已剔除)
             — 公开训练数据拟合, 五列统一套用
  GLM-5.3: 91QA列复用eval_paper_matrix.judge_direct_llm的同prompt同参数
             (磁盘缓存命中, 复核B2=0.6105); 06列同prompt新调用; 公开列走
             public_baselines.judge_public_pair(一pair一调用, 全部缓存)

LLM调用计量: invocations(LlmMeter包装计数) + api_calls(llm_cache行增量)
             + cache_hits(差值), 与eval_paper_matrix同一口径.

回归锚点(result.json.regression):
  qa91×glm_direct 应逐位复现B2=0.6105(缓存); mDeBERTa零样本新口径(直推对)
  与旧口径B1=0.3272(QA模块级联+claim分解+gate)的差异原因如实记录.

用法:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
  python tools/eval_public_matrix.py [--skip-llm] [--rows bge_centroid,...]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
if str(BASE / "tools") not in sys.path:
    sys.path.insert(0, str(BASE / "tools"))

from algorithms.consistency import public_baselines as pb  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    LABELS,
    classification_metrics,
    load_frozen_qa,
    read_jsonl,
)
from eval_paper_matrix import LlmMeter, judge_direct_llm  # noqa: E402
from public_nli_bench import (  # noqa: E402
    CROSSDOC06,
    SEED,
    cmnli_test_keys,
    load_cmnli_test,
    load_cmnli_train,
    load_ocnli_test,
    load_ocnli_train,
    load_selfbuilt_91qa,
    load_selfbuilt_crossdoc06,
    load_xnli_zh,
    llm_view,
    model_view,
    subsample,
)
from tools.run_utils import open_run  # noqa: E402

LLM_CACHE = BASE / "data/gjb_438c/llm_cache/llm_cache.jsonl"
BGE_FIT_OCNLI_N = 2000
BGE_FIT_CMNLI_N = 3000

#: 外部baseline行 (key, kind, 说明); kind ∈ bge / nli / llm
ROWS: tuple[tuple[str, str, str], ...] = (
    ("bge_centroid", "bge", "BGE三元中心法(公开train拟合)"),
    ("erlangshen_zero", "nli", "Erlangshen-Roberta-330M零样本"),
    ("mdeberta_zero", "nli", "mDeBERTa-v3-base-xnli零样本"),
    ("cmnli_finetuned", "nli", "mDeBERTa+CMNLI 50k微调(公开监督)"),
    ("glm_direct", "llm", "GLM-5.3直推(一pair一调用,缓存)"),
)

#: 附加对照行(非外部baseline): 我们的L2域数据微调, 支撑公开/域对照
REFERENCE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("egt_finetuned_v2", "nli", "[对照]mDeBERTa+EGT域数据微调(我们的L2)"),
)

#: 旧口径记录(eval_paper_matrix_c409df7f_20261027_125551, 同批B1/B2)
OLD_B1_MACRO_F1 = 0.3272
OLD_B2_MACRO_F1 = 0.6105

COLUMN_ORDER = ("xnli_zh", "ocnli", "cmnli_test", "qa91", "crossdoc06")


def cache_lines() -> int:
    if not LLM_CACHE.exists():
        return 0
    return sum(1 for line in LLM_CACHE.open(encoding="utf-8") if line.strip())


def verdicts_of(pairs: list[dict]) -> list[str]:
    return [str(pair["label"]) for pair in pairs]


def cell_metrics(pairs: list[dict], preds: list[str]) -> dict[str, Any]:
    if len(preds) != len(pairs):
        raise ValueError(f"pred长度{len(preds)}≠pair长度{len(pairs)}")
    return classification_metrics(verdicts_of(pairs), preds, LABELS)


def build_bge_fit_pool() -> list[dict]:
    """BGE中心法fit池: OCNLI train 2000 + CMNLI train 3000 (seed=42,零泄漏)."""
    ocnli = subsample(load_ocnli_train(), BGE_FIT_OCNLI_N, SEED)
    cmnli = subsample(load_cmnli_train(exclude_keys=cmnli_test_keys()),
                      BGE_FIT_CMNLI_N, SEED)
    return ocnli + cmnli


def qa_rows_for(col_name: str) -> list[dict]:
    """自建列原始QA行(judge_direct_llm需question/answer/evidence; 与
    load_selfbuilt_*的pair顺序同源于同一文件序, 逐位对齐)."""
    if col_name == "qa91":
        return load_frozen_qa()
    if col_name == "crossdoc06":
        return read_jsonl(CROSSDOC06)
    raise ValueError(f"qa_rows_for不支持列: {col_name}")


def fmt_cell(entry: dict) -> str:
    if "error" in entry:
        return "ERR"
    return f"{entry['macro_f1']:.3f}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="公开基准外部baseline矩阵")
    parser.add_argument("--skip-llm", action="store_true",
                        help="跳过GLM行(本地行照跑; 调试用)")
    parser.add_argument("--rows", default="",
                        help="逗号分隔行key子集(默认全部+对照行)")
    args = parser.parse_args()

    started = time.time()
    lines_before = cache_lines()
    row_spec = ROWS + REFERENCE_ROWS
    if args.skip_llm:
        row_spec = tuple(r for r in row_spec if r[1] != "llm")
    if args.rows:
        wanted = {r.strip() for r in args.rows.split(",") if r.strip()}
        row_spec = tuple(r for r in row_spec if r[0] in wanted)

    # ── 列: 公开测试集(模型视图/LLM视图) + 自建集(全量) ───────────────
    print("加载列数据...", flush=True)
    full_sizes: dict[str, int] = {}
    xnli_full = load_xnli_zh()
    full_sizes["xnli_zh"] = len(xnli_full)
    ocnli_full = load_ocnli_test()
    full_sizes["ocnli"] = len(ocnli_full)
    cmnli_full = load_cmnli_test()
    full_sizes["cmnli_test"] = len(cmnli_full)
    qa91_pairs = load_selfbuilt_91qa()
    full_sizes["qa91"] = len(qa91_pairs)
    crossdoc_pairs = load_selfbuilt_crossdoc06()
    full_sizes["crossdoc06"] = len(crossdoc_pairs)

    columns_model: dict[str, list[dict]] = {
        "xnli_zh": model_view(xnli_full),
        "ocnli": model_view(ocnli_full),
        "cmnli_test": model_view(cmnli_full),
        "qa91": qa91_pairs,
        "crossdoc06": crossdoc_pairs,
    }
    columns_llm: dict[str, list[dict]] = {
        "xnli_zh": llm_view(columns_model["xnli_zh"]),
        "ocnli": llm_view(columns_model["ocnli"]),
        "cmnli_test": llm_view(columns_model["cmnli_test"]),
        "qa91": qa91_pairs,
        "crossdoc06": crossdoc_pairs,
    }
    column_meta: dict[str, dict] = {
        name: {
            "n_model": len(columns_model[name]),
            "n_llm": len(columns_llm[name]),
            "full_size": full_sizes[name],
            "label_dist_model": dict(Counter(verdicts_of(columns_model[name]))),
        } for name in COLUMN_ORDER}
    for name in COLUMN_ORDER:
        meta = column_meta[name]
        print(f"  {name}: model={meta['n_model']} llm={meta['n_llm']} "
              f"(full={meta['full_size']}) dist={meta['label_dist_model']}",
              flush=True)

    cells: dict[str, dict[str, Any]] = {row_key: {} for row_key, _, _ in row_spec}

    run = open_run("eval_public_matrix", {
        "rows": [r[0] for r in row_spec],
        "columns": list(COLUMN_ORDER),
        "seed": SEED,
        "skip_llm": args.skip_llm,
        "n_model": {c: len(v) for c, v in columns_model.items()},
        "n_llm": {c: len(v) for c, v in columns_llm.items()},
    })
    print(f"run: {run.path}", flush=True)

    def snapshot() -> None:
        """阶段性落盘(每单元格后), 长跑中断不丢已完成结果(缓存使重跑廉价)."""
        run.save_result({
            "partial": True,
            "rows": [{"key": key, "kind": kind, "desc": desc}
                     for key, kind, desc in row_spec],
            "columns": list(COLUMN_ORDER),
            "column_meta": column_meta,
            "cells": cells,
            "runtime_seconds": round(time.time() - started, 1),
        })

    def run_cell(row_key: str, kind: str,
                 runner: Callable[[str, list[dict]], list[str]]) -> None:
        """一个单元格: 逐列执行+计指标; 异常显式记录为error单元格(不静默)."""
        for col_name in COLUMN_ORDER:
            pairs = (columns_llm if kind == "llm" else columns_model)[col_name]
            t0 = time.time()
            try:
                preds = runner(col_name, pairs)
                entry = cell_metrics(pairs, preds)
                entry["n"] = len(pairs)
                entry["seconds"] = round(time.time() - t0, 1)
            except Exception as exc:  # 单元格级显式记录, 汇总打印error
                entry = {"error": f"{type(exc).__name__}: {exc}",
                         "n": len(pairs),
                         "seconds": round(time.time() - t0, 1)}
            cells[row_key][col_name] = entry
            print(f"  {row_key}×{col_name}: {fmt_cell(entry)} "
                  f"({entry['seconds']}s)", flush=True)
            snapshot()

    meter = LlmMeter()
    meter.install()
    try:
        # ── 行: BGE三元中心法 (fit池→五列套用) ─────────────────────
        if any(r[0] == "bge_centroid" for r in row_spec):
            print(f"BGE中心法: fit池(OCNLI train {BGE_FIT_OCNLI_N} + CMNLI "
                  f"train {BGE_FIT_CMNLI_N}, seed={SEED})...", flush=True)
            from algorithms.common.bge_local import BgeLocal

            bge = BgeLocal()
            if bge.ensure() == "unavailable":

                def bge_failed(_col: str, _pairs: list[dict]) -> list[str]:
                    raise RuntimeError(f"BGE不可用: {bge.last_error}")

                run_cell("bge_centroid", "bge", bge_failed)
            else:
                fit_pool = build_bge_fit_pool()
                print(f"  fit池: {len(fit_pool)}对 "
                      f"dist={dict(Counter(verdicts_of(fit_pool)))}", flush=True)
                t0 = time.time()
                centroids = pb.bge_fit_from_pairs(bge, fit_pool)
                print(f"  三类中心拟合完成({time.time() - t0:.0f}s, "
                      f"mode={bge.mode}, dim={bge.stats['dim']})", flush=True)

                def bge_runner(_col: str, pairs: list[dict]) -> list[str]:
                    return pb.bge_centroid_verdicts(pairs, bge, centroids)

                run_cell("bge_centroid", "bge", bge_runner)
                bge.save()

        # ── 行: 本地NLI直推 (零样本×2 / CMNLI微调 / EGT对照) ─────────
        for row_key, kind, _desc in row_spec:
            if kind != "nli":
                continue
            model_dir = pb.BASELINE_MODEL_DIRS[row_key]
            print(f"{row_key}: {model_dir}", flush=True)

            def nli_runner(_col: str, pairs: list[dict],
                           _dir: str = model_dir) -> list[str]:
                return pb.nli_verdicts(pairs, _dir)

            run_cell(row_key, "nli", nli_runner)

        # ── 行: GLM-5.3直推 (公开列300×3 + 自建列全量) ──────────────
        if any(r[0] == "glm_direct" for r in row_spec):
            print("GLM-5.3直推: 公开列300×3 + 自建列全量"
                  "(91QA复用B2 prompt→缓存命中)...", flush=True)

            def glm_runner(col_name: str, pairs: list[dict]) -> list[str]:
                if col_name in ("qa91", "crossdoc06"):
                    return [judge_direct_llm(row)["verdict"]
                            for row in qa_rows_for(col_name)]
                return pb.glm_public_verdicts(pairs)

            run_cell("glm_direct", "llm", glm_runner)
    finally:
        meter.restore()
    api_calls = cache_lines() - lines_before
    llm_stats_total = {"invocations": meter.invocations, "api_calls": api_calls,
                       "cache_hits": meter.invocations - api_calls}

    # ── 回归锚点 ──────────────────────────────────────────────────
    regression: dict[str, Any] = {}
    glm_qa91 = cells.get("glm_direct", {}).get("qa91")
    if glm_qa91 and "macro_f1" in glm_qa91:
        regression["b2_cache_reproduction"] = {
            "old_run": "eval_paper_matrix_c409df7f_20261027_125551",
            "expected_macro_f1": OLD_B2_MACRO_F1,
            "observed_macro_f1": glm_qa91["macro_f1"],
            "reproduced": glm_qa91["macro_f1"] == OLD_B2_MACRO_F1,
            "note": "同prompt同参数judge_direct_llm, 磁盘缓存命中逐位复现",
        }
    mdeberta_qa91 = cells.get("mdeberta_zero", {}).get("qa91")
    if mdeberta_qa91 and "macro_f1" in mdeberta_qa91:
        regression["b1_direct_vs_module"] = {
            "old_run": "eval_paper_matrix_c409df7f_20261027_125551",
            "old_module_macro_f1": OLD_B1_MACRO_F1,
            "new_direct_macro_f1": mdeberta_qa91["macro_f1"],
            "note": ("旧口径B1走QAConsistencyModule(use_experts=False,"
                     "use_nli_residual=True,零样本mDeBERTa): answer先分解为"
                     "claims, premise走residual_premise(500字符预算, scope/"
                     "bigram重叠选组), softmax gate=0.6, 级联融合; 新口径为"
                     "直推对(premise=冻结证据1500字符拼接, hypothesis=answer, "
                     "无claim分解无gate). 差异=口径差(claim分解+证据选择+置信"
                     "度门控), 非模型差, 不可直接比大小."),
        }

    # ── 汇总与落盘 ────────────────────────────────────────────────
    matrix: dict[str, dict[str, Any]] = {
        row_key: {col: cells[row_key].get(col, {}).get("macro_f1")
                  for col in COLUMN_ORDER}
        for row_key, _, _ in row_spec}
    matrix_table = "\n".join(
        ["| baseline | " + " | ".join(COLUMN_ORDER) + " |",
         "|---" * (len(COLUMN_ORDER) + 1) + "|"] +
        [f"| {row_key} ({desc}) | " + " | ".join(
            fmt_cell(cells[row_key].get(col, {})) for col in COLUMN_ORDER) + " |"
         for row_key, _kind, desc in row_spec])

    result = {
        "partial": False,
        "rows": [{"key": key, "kind": kind, "desc": desc}
                 for key, kind, desc in row_spec],
        "columns": list(COLUMN_ORDER),
        "column_meta": column_meta,
        "matrix_macro_f1": matrix,
        "cells": cells,
        "llm_calls": llm_stats_total,
        "protocol": {
            "seed": SEED,
            "model_view": "公开集全量, n>3000抽2000(seed=42, 保序)",
            "llm_view": "公开集从模型视图抽300(seed=42); 自建集全量",
            "selfbuilt_premise": ("nli_training.build_premise: 剥HTML+滑窗+"
                                  "每块500/总1500字符; hypothesis=answer"),
            "bge_fit": {
                "pool": f"OCNLI train {BGE_FIT_OCNLI_N} + CMNLI train "
                        f"{BGE_FIT_CMNLI_N} (seed={SEED})",
                "leak_check": ("OCNLI train×官方test重叠0对; CMNLI train×"
                               "test 3个原始重复key已剔除"),
                "feature": "[u_p; u_h; u_p⊙u_h; |u_p−u_h|] 各分量+整体L2归一",
                "method": "三类归一化均值中心, test取argmax余弦(近邻中心)",
                "bge_max_len": 256,
            },
            "nli_max_length": 512,
            "ocnli_label_mapping": ("官方test文件实证编码 0=contradiction/"
                                    "1=neutral/2=entailment(文件内prompt文本"
                                    "不可信, 语义锚点对+二值dev子集双重校验, "
                                    "见tools/public_nli_bench.py)"),
            "glm": ("glm-5.3, llm_json cache=True, reasoning_effort=low, "
                    "json_final_content_v2; 91QA列复用B2 prompt(缓存复核)"),
            "metric": "eval_lib.classification_metrics (三态macro-F1, 四位)",
        },
        "regression": regression,
        "matrix_table": matrix_table,
        "runtime_seconds": round(time.time() - started, 1),
    }

    run.save_result(result)

    print()
    print(matrix_table)
    print()
    print(json.dumps({"llm_calls": llm_stats_total,
                      "regression": regression,
                      "run": str(run.path),
                      "runtime_seconds": result["runtime_seconds"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
