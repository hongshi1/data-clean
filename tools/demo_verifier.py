"""CascadeVerifier使用演示: 三行代码完成SRS一致性校验.

用法:
    $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/demo_verifier.py

三行代码(写进verifier.py docstring的同一示例):
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    result = verifier.verify(question, answer, evidence)
    print(result.verdict, result.evidence_refs)

内容:
1. fast preset跑S1QA-056(91QA冻结语料, 预期refute展示)
2. scene切换到doc01(onboarding生成的词典/规则包生效验证——01号证据
   跑一条support+一条错误ID refute)
3. batch跑前10条(带延迟统计)
4. preset档位表(fast/standard/full的通道/延迟/成本差异)

产出走runs协议(open_run: config+git_sha+result, 不覆盖写).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import load_frozen_qa  # noqa: E402
from algorithms.consistency.verifier import CascadeVerifier  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

#: 演示1/3使用的实例
TARGET_INSTANCE = "S1QA-056"
BATCH_N = 10


def _load_doc01_blocks() -> list[dict]:
    """01号content_list(onboarding场景资产的原始来源文档)."""
    import glob

    paths = sorted(glob.glob(
        str(BASE / "data/gjb_438c/mineru_standard/01*/office/*_content_list.json")))
    if len(paths) != 1:
        raise RuntimeError(f"预期1个01号content_list, 实际{len(paths)}")
    return json.loads(Path(paths[0]).read_text(encoding="utf-8"))


def doc01_records() -> list[dict[str, Any]]:
    """01号证据构造的两条冻结QA记录(正确ID/错误ID)."""
    blocks = _load_doc01_blocks()
    doc_id = "01数据获取转换分系统需求规格说明-终稿"
    evidence = [
        {
            "evidence_id": "doc01-ev-000046",
            "text": blocks[46]["table_body"],
            "source_type": "table",
            "source_ref": {"doc_id": doc_id, "section": "3.2.1", "page": 1,
                           "block_id": "block-000046"},
            "scope_id": f"{doc_id}:block-000046",
            "completeness": "open",
            "completeness_proof": "Only this source block was frozen.",
        },
        {
            "evidence_id": "doc01-ev-000047",
            "text": blocks[47]["text"],
            "source_type": "text",
            "source_ref": {"doc_id": doc_id, "section": "3.2.1.3", "page": 1,
                           "block_id": "block-000047"},
            "scope_id": f"{doc_id}:block-000047",
            "completeness": "open",
            "completeness_proof": "Only this source block was frozen.",
        },
    ]
    question = "结构化数据归集的项目唯一标识符是什么？"
    return [
        {
            "instance_id": "doc01-demo-001",
            "question": question,
            "answer": "结构化数据归集的项目唯一标识符为"
                      "ZZSJHQZHFW-GN-SJHQ-JGHSJGJ。",
            "context_freeze_id": "doc01-demo-frozen-v1",
            "evidence": evidence,
        },
        {
            "instance_id": "doc01-demo-002",
            "question": question,
            "answer": "结构化数据归集的项目唯一标识符为"
                      "ZZSJHQZHFW-GN-SJHQ-XXYYZZ。",
            "context_freeze_id": "doc01-demo-frozen-v1",
            "evidence": evidence,
        },
    ]


def _show(result, prefix: str = "") -> None:
    print(f"{prefix}verdict      : {result.verdict}")
    print(f"{prefix}evidence_refs: {result.evidence_refs}")
    print(f"{prefix}check_items  : {result.check_items}")
    print(f"{prefix}rationale    : {result.rationale[:160]}"
          f"{'…' if len(result.rationale) > 160 else ''}")
    print(f"{prefix}latency_ms   : {result.latency_ms:.1f}")


def demo_single() -> dict[str, Any]:
    """演示1: fast preset跑S1QA-056(预期refute)."""
    rows = load_frozen_qa()
    record = next(row for row in rows
                  if row["instance_id"] == TARGET_INSTANCE)
    print("== [1] fast preset · 单条校验(silver标签=refute的注入实例) ==")
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    result = verifier.verify_record(record)
    print(f"instance_id  : {record['instance_id']} "
          f"(question: {record['question'][:40]}…)")
    _show(result, prefix="  ")
    print("  (预期输出: refute, 与silver一致)")
    return {"instance_id": TARGET_INSTANCE, "verdict": result.verdict,
            "latency_ms": result.latency_ms,
            "evidence_refs": list(result.evidence_refs)}


def demo_scene_switch() -> dict[str, Any]:
    """演示2: scene切换到doc01(onboarding配置生效验证)."""
    print()
    print("== [2] scene切换: srs_scene1 → doc01(01号onboarding配置) ==")
    verifier = CascadeVerifier(preset="fast", scene="doc01")
    print(f"facade查询: lexicon.scene={verifier.lexicon.scene} "
          f"id_patterns={verifier.lexicon.id_patterns}")
    print(f"facade查询: rulepack.pack_id={verifier.rulepack.pack_id} "
          f"(04号默认为srs_gjb_v1, 已真实切换)")
    correct, wrong = doc01_records()
    out: dict[str, Any] = {
        "scene": "doc01",
        "lexicon_scene": verifier.lexicon.scene,
        "rulepack_id": verifier.rulepack.pack_id,
    }
    for record, expect in ((correct, "support"), (wrong, "refute")):
        print(f"  -- {record['instance_id']} (预期{expect})")
        result = verifier.verify_record(record)
        _show(result, prefix="    ")
        out[record["instance_id"]] = {
            "verdict": result.verdict, "expected": expect,
            "latency_ms": result.latency_ms,
        }
    return out


def demo_batch() -> dict[str, Any]:
    """演示3: batch跑前10条(内部复用引擎, 带延迟统计)."""
    print()
    print(f"== [3] batch · 91QA前{BATCH_N}条(延迟统计) ==")
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    rows = load_frozen_qa()[:BATCH_N]
    results = verifier.verify_batch(rows)
    latencies = [r.latency_ms for r in results]
    verdict_counts: dict[str, int] = {}
    for r in results:
        verdict_counts[r.verdict] = verdict_counts.get(r.verdict, 0) + 1
    print(f"  n={len(results)}  verdict分布={verdict_counts}")
    print(f"  latency_ms: total={sum(latencies):.1f} "
          f"mean={sum(latencies) / len(latencies):.1f} "
          f"min={min(latencies):.1f} max={max(latencies):.1f} "
          f"(fast档稳态≈8ms/条, 首条含jieba/规则包预热)")
    return {
        "n": len(results),
        "verdict_counts": verdict_counts,
        "latency_ms_total": round(sum(latencies), 3),
        "latency_ms_mean": round(sum(latencies) / len(latencies), 3),
        "latency_ms_min": round(min(latencies), 3),
        "latency_ms_max": round(max(latencies), 3),
        "per_instance": [{"instance_id": rows[i]["instance_id"],
                          "verdict": r.verdict,
                          "latency_ms": r.latency_ms}
                         for i, r in enumerate(results)],
    }


def print_preset_table() -> None:
    """演示4: preset档位表(通道/延迟/成本)."""
    print()
    print("== [4] preset档位表 ==")
    header = ["preset", "通道", "延迟(条)", "成本"]
    rows = [
        ["fast", "L0/L1确定性专家(entity/e1/sequence/trace/gjb/join/z3)",
         "≈8ms", "零模型加载, 可复现"],
        ["standard", "+L2本地NLI残差(微调mDeBERTa)",
         "首次≈35s模型加载, 稳态≈120ms", "本地推理, 无LLM"],
        ["full", "+L3级联仲裁(L2 refute候选→LLM复核替换)",
         "级联(仅refute候选付LLM成本)", "LLM调用(走llm缓存接口)"],
    ]
    widths = [max(len(header[i]), *(len(r[i]) for r in rows))
              for i in range(len(header))]
    print("  " + "  ".join(h.ljust(w) for h, w in zip(header, widths)))
    print("  " + "-" * (sum(widths) + 2 * (len(widths) - 1)))
    for row in rows:
        print("  " + "  ".join(c.ljust(w) for c, w in zip(row, widths)))


def main() -> None:
    print("CascadeVerifier: 三行代码完成SRS一致性校验(facade)")
    print("  verifier = CascadeVerifier(preset='fast', scene='srs_scene1')")
    print("  result = verifier.verify(question, answer, evidence)")
    print("  print(result.verdict, result.evidence_refs)")
    single = demo_single()
    scene = demo_scene_switch()
    batch = demo_batch()
    print_preset_table()

    run = open_run("demo_verifier", {
        "facade": "algorithms/consistency/verifier.py",
        "presets": "fast(演示跑全三段; standard/full构造见tests)",
        "scenes": ["srs_scene1", "doc01"],
        "datasets": ["data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
                     "doc01 blocks(data/gjb_438c/mineru_standard/01*)"],
    })
    run.save_result({"single": single, "scene_switch": scene,
                     "batch": batch})
    print()
    print(f"run: {run.path}")
    print("RESULT: OK (三段演示全部跑通)")


if __name__ == "__main__":
    main()
