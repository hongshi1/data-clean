"""构建数据资产MANIFEST: 金标资产的 sha256 指纹 + pair_dataset结构.

目的: 防"金标数据被悄悄重生成" — tests/test_manifest.py 重算指纹比对,
不一致即报警(评测基准变了没人知道 = 科研代码最贵的静默bug).

用法:
  python tools/build_data_manifest.py          # 构建/更新 data/gjb_438c/MANIFEST.json
  python -m pytest tests/test_manifest.py      # 验证

注意: 有意重新生成数据后, 重跑本脚本并在同一提交里更新快照测试.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

DATA = BASE / "data/gjb_438c"
OUT = DATA / "MANIFEST.json"

# 金标/评测关键资产(变动 = 评测基准变动)
ASSETS = [
    "anchor_v2/anchors_v2.json",
    "anchor_v2/scene_tier1.json",
    "anchor_v2/scene_drift_census.json",
    "anchor_v2/scene_vlm_extractions.json",
    "anchor_v2/scene_ocr_extractions.json",
    "anchor_sc2/anchors.json",
    "anchor_sc2/vlm_extractions.json",
    "anchor_sc2/ocr_extractions.json",
    "anchor_sc2/calibration.json",
    "anchor_sc2/tier1_discrepancies_v2.json",
    "data_assets/graph/id_document_graph.json",
    "data_assets/chunks/srs_chunks.json",
    "data_assets/chunks/srs_image_analyses.json",
    "data_assets/evalset_v3.json",
    "answer_evidence_evalset_v1.json",
    "family_evalset_v1.json",
    "qa_e2e_a1.json",
    "scene1_qa_audit.json",
    "aee_question_recovery.json",
    "legacy_answer_mutation_audit.json",
    "data_assets/va_colpali_img_anchor_map.json",
    "data_assets/va_colpali_eval.json",
    "data_assets/table_late_eval.json",
    "data_assets/deep_row_queries.json",
    "data_assets/deep_row_queries_train.json",
    "data_assets/unit_attention_eval.json",
    "data_assets/two_stage_eval.json",
    "data_assets/evalsets/gjb_ure_v1.json",
    "data_assets/evalsets/gjb_ure_v2.json",
    "data_assets/evalsets/deep_row_queries_v2.json",
    "data_assets/evalsets/deep_v2_eval.json",
    "data_assets/evalsets/wtq_ure.json",
    "data_assets/evalsets/wtq_pilot_eval.json",
    "data_assets/evalsets/fetaqa_ure.json",
    "data_assets/evalsets/baselines_eval.json",
    "data_assets/evalsets/token_maxsim_eval.json",
    # v4.0新增: NLI不一致检测金标资产(2026-10)
    "human_gold/final_gold_86.json",
    "human_gold/gold_v2_357.json",
    "human_gold/gold_v2_clean_137.json",
    "human_gold/md_cot_adjudication.json",
    "human_gold/md_test_doc047.json",
    "human_gold/md_test_sc3.json",
    "unified_testset/INDEX.json",
    "unified_testset/gjb_gold.jsonl",
    "unified_testset/gjb_gold_v2.jsonl",
    "unified_testset/md_gold.jsonl",
    "unified_testset/gjb_bench_test.jsonl",
    "benchmark_full_v2.jsonl",
    "data_assets/evalsets/public_en_eval.json",
    "data_assets/evalsets/sota_m3_eval.json",
    "data_assets/evalsets/deep_v2_extra_baselines.json",
    "data_assets/evalsets/deep_v2_hyde.json",
    "data_assets/evalsets/unit_channel_ablation.json",
    "data_assets/evalsets/profile_route_matrix.json",
    "data_assets/evalsets/duret_ure.json",
    "data_assets/evalsets/duret_eval.json",
    "data_assets/evalsets/wtq_full_eval.json",
    "data_assets/evalsets/pure_mmqa_blocked.json",
    "data_assets/evalsets/pure_mmqa_ure.json",
    "data_assets/evalsets/pure_mmqa_eval.json",
    "blackboard/embedding_calibration.json",
    # v4.1新增: P0冻结探针集(eval-only, 永不进训练)
    "probes/paws_shortcut_probe.json",
    "probes/feverous_table_probe.json",
    "probes/ocnli_contradiction_probe.json",
    # v5.0新增: 冻结QA输入 + GLM-5.3 silver标签 (2026-10-22)
    "qa_frozen/scene1_qa_frozen_v1.jsonl",
    "qa_frozen/scene1_qa_frozen_v1_metadata.json",
    "qa_frozen/scene1_qa_frozen_v1_report.json",
    "runs/review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl",
    "runs/review_qa_with_glm53_582b51e5_20261021_145212/final_summary.json",
    # v5.1新增: 官方参考数据集(场景1补发包全链整合) (2026-10-22)
    "qa_frozen/scene1_official_reference_v1.jsonl",
    "qa_frozen/scene1_official_reference_v1_metadata.json",
    # v5.2新增: 06号跨文档泛化评测集(构造性sound标签, P1) (2026-10-27)
    "qa_frozen/crossdoc06_evalset_v1.jsonl",
    "qa_frozen/crossdoc06_evalset_v1_metadata.json",
    "qa_frozen/crossdoc06_evalset_v1_report.json",
    # v5.3新增: 跨文档×5扩充集(05/07/08/10各30条+合并150条, P1v2) (2026-10-30)
    "qa_frozen/crossdoc05_evalset_v1.jsonl",
    "qa_frozen/crossdoc05_evalset_v1_metadata.json",
    "qa_frozen/crossdoc05_evalset_v1_report.json",
    "qa_frozen/crossdoc07_evalset_v1.jsonl",
    "qa_frozen/crossdoc07_evalset_v1_metadata.json",
    "qa_frozen/crossdoc07_evalset_v1_report.json",
    "qa_frozen/crossdoc08_evalset_v1.jsonl",
    "qa_frozen/crossdoc08_evalset_v1_metadata.json",
    "qa_frozen/crossdoc08_evalset_v1_report.json",
    "qa_frozen/crossdoc10_evalset_v1.jsonl",
    "qa_frozen/crossdoc10_evalset_v1_metadata.json",
    "qa_frozen/crossdoc10_evalset_v1_report.json",
    "qa_frozen/crossdoc5_evalset_v1.jsonl",
    "qa_frozen/crossdoc5_evalset_v1_metadata.json",
    "qa_frozen/crossdoc5_evalset_v1_report.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _pair_dataset_digest() -> dict:
    pd = DATA / "pair_dataset"
    scene_counts: dict[str, int] = {}
    h = hashlib.sha256()
    n = 0
    for scene_dir in sorted(pd.iterdir()):
        if not scene_dir.is_dir():
            continue
        cnt = 0
        for pair_dir in sorted(scene_dir.iterdir()):
            meta_p = pair_dir / "meta.json"
            if meta_p.exists():
                cnt += 1
                n += 1
                h.update(meta_p.read_bytes())
        scene_counts[scene_dir.name] = cnt
    return {"n_pairs": n, "scene_counts": scene_counts,
            "meta_sha256": h.hexdigest()}


def build() -> dict:
    run = open_run("build_data_manifest", {"n_assets": len(ASSETS)})
    assets: dict[str, dict] = {}
    for rel in ASSETS:
        p = DATA / rel
        if not p.exists():
            print(f"  !! 缺失: {rel}")
            continue
        assets[rel] = {"bytes": p.stat().st_size, "sha256": _sha256(p)}
    manifest = {
        "version": 1,
        "git_sha": run.meta["git_sha"],
        "built_at": run.meta["opened_at"],
        "assets": assets,
        "pair_dataset": _pair_dataset_digest(),
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    run.save_result({"n_assets": len(assets), "out": str(OUT)})
    run.log(action="manifest_built", n_assets=len(assets),
             n_pairs=manifest["pair_dataset"]["n_pairs"])
    return manifest


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace")
    m = build()
    total_mb = sum(a["bytes"] for a in m["assets"].values()) / 1e6
    print(f"MANIFEST: {len(m['assets'])}个资产({total_mb:.1f}MB) + "
          f"{m['pair_dataset']['n_pairs']}对 → {OUT}")
    print("运行记录: data/gjb_438c/runs/ (config含git_sha)")
