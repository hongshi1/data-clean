"""QA训练数据批量合成: srs_anchor真实对 × 4变异算子 × 4型QA.

流程:
  1. 读取 pair_dataset_canonical/train.jsonl 中 source=srs_anchor 的真实锚点对
  2. 每条转换为 Evidence + Pair
  3. 原始Pair(未变异)生成4型QA, 标签沿用真实标注(一致对 → consistent)
  4. 每对应用 {ParamShift, TermSwap, ItemRemove, OrderSwap}: 成功 → 4型QA(inconsistent);
     失败 → 跳过并按算子记录原因
  5. 统计并保存 data/gjb_438c/qa_dataset_synthesized.json

用法: python tools/qa_synth_generate.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from algorithms.qa_synth import (  # noqa: E402
    Evidence,
    ItemRemove,
    MutationOperator,
    MutationRecord,
    OrderSwap,
    Pair,
    ParamShift,
    QASample,
    TermSwap,
    generate_qa,
)

TRAIN_JSONL = BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl"
OUT_JSON = BASE / "data/gjb_438c/qa_dataset_synthesized.json"

QA_TYPES = ["判别型", "定位型", "解释型", "修复型"]
MUTATION_OPERATORS: list[tuple[str, MutationOperator]] = [
    ("param_shift", ParamShift()),
    ("term_swap", TermSwap()),
    ("item_remove", ItemRemove()),
    ("order_swap", OrderSwap()),
]
MUTATION_PARAMS = {"factor": 2.0}

ANGLE_TO_TEMPLATE = {
    "TABLE_ITEM_MISSING": "TABLE_ITEM_MISSING",
    "COMPONENT_MISSING": "TABLE_ITEM_MISSING",
    "ACTOR_MISSING": "TABLE_ITEM_MISSING",
    "STEP_MISSING": "TABLE_ITEM_MISSING",
    "EXC_MISSING": "TABLE_ITEM_MISSING",
    "DIAGRAM_EXTRA": "TABLE_ITEM_MISSING",
    "DIAGRAM_EXTRA_COUNT": "TABLE_ITEM_MISSING",
    "UC_NAME_MISMATCH": "TERM-01",
    "ORDER_CONFLICT": "ORDER_CONFLICT",
}


def angle_to_template(angle_type: str) -> str:
    if angle_type in ANGLE_TO_TEMPLATE:
        return ANGLE_TO_TEMPLATE[angle_type]
    if angle_type.startswith("PARAM"):
        return "PARAM-01"
    if angle_type.startswith("TERM"):
        return "TERM-01"
    return angle_type


def load_anchor_records(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("source") == "srs_anchor":
                records.append(rec)
    return records


def quoted_item(text: str) -> str:
    m = re.search(r"「([^「」]+)」", text)
    return m.group(1) if m else ""


def build_pair(rec: dict[str, Any]) -> tuple[Pair, dict[str, Any]]:
    ctx = rec["context"]
    premise = Evidence(
        id=f"{rec['id']}-A",
        content=rec["pair"]["premise"],
        modality="table",
        source_doc=ctx.get("doc", ""),
        source_section=ctx.get("section", ""),
        metadata={"caption": ctx.get("table_caption", "")},
    )
    hypothesis = Evidence(
        id=f"{rec['id']}-B",
        content=rec["pair"]["hypothesis"],
        modality="diagram",
        source_doc=ctx.get("doc", ""),
        source_section=ctx.get("section", ""),
        metadata={"caption": ctx.get("image_caption", "")},
    )
    pair = Pair(
        id=rec["id"],
        premise=premise,
        hypothesis=hypothesis,
        relation="same_entity",
        entity_id=ctx.get("pair_id", ""),
        is_consistent=(rec["label"] == "consistent"),
        label_source="annotation:srs_anchor",
    )
    return pair, ctx


def original_record(pair: Pair, rec: dict[str, Any], item: str) -> MutationRecord:
    ctx, angle = rec["context"], rec["angle"]
    if pair.is_consistent:
        position = "无不一致位置(一致对)"
        note = "一致对(未变异): 陈述A(表侧)与陈述B(图侧)关于同一实体的描述语义一致"
    else:
        position = (
            f"{ctx.get('doc', '')} §{ctx.get('section', '')}"
            f"(图: {ctx.get('image_caption', '')}; 表: {ctx.get('table_caption', '')})"
        )
        note = f"真实标注[{angle['type']}]: 表侧与图侧内容冲突"
        if item:
            note += f"(涉及「{item}」)"
    return MutationRecord(
        operator="original",
        target_type=angle_to_template(angle["type"]),
        position=position,
        original=pair.hypothesis.content,
        mutated=pair.hypothesis.content,
        is_valid=True,
        validation_note=note,
    )


def refine_question(qa: QASample, record: MutationRecord, pair: Pair) -> str:
    q = qa.question
    if "「」" not in q:
        return q
    if record.operator == "item_remove":
        item = record.original
    else:
        item = quoted_item(pair.premise.content) or quoted_item(pair.hypothesis.content)
    if item:
        q = q.replace("「」", f"「{item}」", 1)
    return q


def refine_locate_answer(qa: QASample, record: MutationRecord) -> str:
    m = re.fullmatch(r"(?:hypothesis)?位置(\d+)", (record.position or "").strip())
    if not m:
        return qa.answer
    h = qa.pairs[0].hypothesis.content
    if not h:
        return qa.answer
    off = min(int(m.group(1)), max(len(h) - 1, 0))
    lo, hi = max(0, off - 12), min(len(h), off + 18)
    return f"陈述B(hypothesis)偏移{off}附近: 「…{h[lo:hi]}…」"


def refine_repair_answer_original(pair: Pair, item: str) -> str:
    if pair.is_consistent:
        return "无需修复: 一致对, 两处描述语义一致"
    target = f"「{item}」" if item else "冲突内容"
    return f"修复方向: 在图侧补充{target}对应元素(或同步修订表侧), 使陈述B与陈述A一致"


def provenance_fields(rec: dict[str, Any], pair_kind: str) -> dict[str, str]:
    ctx, angle, prov = rec["context"], rec["angle"], rec["provenance"]
    return {
        "pair_kind": pair_kind,
        "source": "srs_anchor",
        "anchor_record_id": str(rec["id"]),
        "origin_label": str(rec["label"]),
        "doc": str(ctx.get("doc", "")),
        "section": str(ctx.get("section", "")),
        "scene": str(angle.get("scene", "")),
        "angle_type": str(angle.get("type", "")),
        "surface": str(prov.get("surface", "")),
        "origin": str(prov.get("origin", "")),
        "context_key": str(ctx.get("pair_id", "")),
    }


def context_dict(ctx: dict[str, Any]) -> dict[str, Any]:
    keys = ("scene_dir", "doc", "section", "image_caption", "table_caption", "table", "diagram", "text")
    d = {k: ctx.get(k, "") for k in keys}
    if "table_rows_full" in ctx:
        d["table_rows_full"] = ctx["table_rows_full"]
    if isinstance(ctx.get("image"), str):
        d["image"] = ctx["image"]
    return d


def evidence_dict(e: Evidence) -> dict[str, Any]:
    return {
        "id": e.id,
        "content": e.content,
        "modality": e.modality,
        "source_doc": e.source_doc,
        "source_section": e.source_section,
        "metadata": e.metadata,
    }


def pair_dict(p: Pair) -> dict[str, Any]:
    return {
        "id": p.id,
        "relation": p.relation,
        "entity_id": p.entity_id,
        "is_consistent": p.is_consistent,
        "label_source": p.label_source,
        "premise": evidence_dict(p.premise),
        "hypothesis": evidence_dict(p.hypothesis),
    }


def qa_dict(qa: QASample) -> dict[str, Any]:
    return {
        "id": qa.id,
        "qa_type": qa.qa_type,
        "question": qa.question,
        "answer": qa.answer,
        "label": qa.label,
        "inconsistency_type": qa.inconsistency_type,
        "location": qa.location,
        "explanation": qa.explanation,
        "pair": pair_dict(qa.pairs[0]),
        "provenance": qa.provenance,
    }


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=BASE, check=True,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def synthesize() -> tuple[list[QASample], dict[str, dict[str, Any]], dict[str, Any]]:
    records = load_anchor_records(TRAIN_JSONL)
    samples: list[QASample] = []
    contexts: dict[str, dict[str, Any]] = {}
    fail_reasons: dict[str, Counter[str]] = {name: Counter() for name, _ in MUTATION_OPERATORS}
    op_success: Counter[str] = Counter()

    for rec in records:
        pair, ctx = build_pair(rec)
        contexts.setdefault(str(ctx.get("pair_id", "")), context_dict(ctx))
        item = quoted_item(pair.premise.content)

        rec_o = original_record(pair, rec, item)
        for qt in QA_TYPES:
            qa = generate_qa(pair, rec_o, qt)
            qa.question = refine_question(qa, rec_o, pair)
            if qt == "修复型":
                qa.answer = refine_repair_answer_original(pair, item)
            qa.inconsistency_type = str(rec["angle"]["type"])
            qa.provenance.update(provenance_fields(rec, "original"))
            samples.append(qa)

        for op_name, op in MUTATION_OPERATORS:
            new_pair, mrec = op.mutate(pair, dict(MUTATION_PARAMS))
            if not mrec.is_valid:
                fail_reasons[op_name][mrec.validation_note] += 1
                continue
            op_success[op_name] += 1
            new_pair.id = f"{pair.id}::{op_name}"
            new_pair.hypothesis.metadata = dict(pair.hypothesis.metadata) | {"mutated_by": op_name}
            for qt in QA_TYPES:
                qa = generate_qa(new_pair, mrec, qt)
                qa.question = refine_question(qa, mrec, new_pair)
                if qt == "定位型":
                    qa.answer = refine_locate_answer(qa, mrec)
                qa.provenance.update(provenance_fields(rec, "mutated"))
                samples.append(qa)

    n = len(records)
    mutated_pairs = int(sum(op_success.values()))
    stats = {
        "total_qa": len(samples),
        "target_min_qa": 500,
        "target_met": len(samples) >= 500,
        "anchor_pairs_input": n,
        "original_qa": n * len(QA_TYPES),
        "mutated_pairs": mutated_pairs,
        "mutated_qa": mutated_pairs * len(QA_TYPES),
        "qa_type_distribution": dict(Counter(s.qa_type for s in samples)),
        "label_distribution": dict(Counter(s.label for s in samples)),
        "pair_kind_distribution": dict(Counter(s.provenance["pair_kind"] for s in samples)),
        "inconsistency_type_distribution": dict(Counter(s.inconsistency_type for s in samples)),
        "mutation": {
            "params": MUTATION_PARAMS,
            "attempts_per_operator": n,
            "success": dict(op_success),
            "failed": {name: n - op_success[name] for name, _ in MUTATION_OPERATORS},
            "success_rate_pct": {
                name: round(100.0 * op_success[name] / n, 2) for name, _ in MUTATION_OPERATORS
            },
            "failure_reasons": {name: dict(cnt) for name, cnt in fail_reasons.items()},
        },
    }
    return samples, contexts, stats


def main() -> None:
    samples, contexts, stats = synthesize()
    ids = [s.id for s in samples]
    if len(set(ids)) != len(ids):
        dup = [i for i, c in Counter(ids).items() if c > 1]
        raise ValueError(f"QA id重复: {dup[:5]}")

    payload = {
        "meta": {
            "generator": "tools/qa_synth_generate.py",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "git_sha": git_sha(),
            "source_dataset": "data/gjb_438c/pair_dataset_canonical/train.jsonl",
            "source_filter": {"source": "srs_anchor"},
            "components": "algorithms/qa_synth.py",
            "config": {
                "mutation_params": MUTATION_PARAMS,
                "qa_types": QA_TYPES,
                "operators": [name for name, _ in MUTATION_OPERATORS],
            },
            "postprocess": [
                "question空槽「」回填(premise引号条目/被删条目)",
                "变异对定位型answer: 字符偏移→hypothesis文本片段",
                "原始对修复型answer覆盖(一致=无需修复; 不一致=修复方向)",
                "原始对inconsistency_type回填真实angle.type",
            ],
        },
        "stats": stats,
        "contexts": contexts,
        "samples": [qa_dict(s) for s in samples],
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    mut = stats["mutation"]
    print(f"输入: {stats['anchor_pairs_input']} 个 srs_anchor 真实Pair")
    for name, _ in MUTATION_OPERATORS:
        print(
            f"  {name}: 成功 {mut['success'].get(name, 0)}/{mut['attempts_per_operator']}"
            f" ({mut['success_rate_pct'][name]}%), 失败原因: {mut['failure_reasons'][name]}"
        )
    print(f"总QA: {stats['total_qa']} 条 (目标>=500: {'达成' if stats['target_met'] else '未达成'})")
    print(f"  原始对QA: {stats['original_qa']} | 变异对QA: {stats['mutated_qa']}")
    print(f"  QA类型分布: {stats['qa_type_distribution']}")
    print(f"  标签分布: {stats['label_distribution']}")
    print(f"  pair_kind分布: {stats['pair_kind_distribution']}")
    print(f"  inconsistency_type分布: {stats['inconsistency_type_distribution']}")
    print(f"已保存: {OUT_JSON} ({OUT_JSON.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
