"""Phase B: QA consistency checking on frozen image evidence.

Implements D1 (enum check), C3 (same-image cross-condition conflicts),
and B3 (static evidence grounding) on the 672 sleep QA runs.
Consumes frozen evidence from build_image_evidence.py.

Usage:
  python scenario5/tools/qa_consistency_check.py --qa-dir <dir> --evidence-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.run_utils import open_run  # noqa: E402

VALID_ANSWERS = {0, 1, 2}
QA_FILE_RE = re.compile(r"sleep-(?P<phase>before|after)-(?P<quant>all|4bit)(?P<prompt>-simpleprompt)?\.jsonl")

# B3 grounding keywords: static pose evidence terms
POSE_KEYWORDS_PRONE = ["趴伏", "趴在", "趴于", "伏案", "横卧", "趴卧"]
POSE_KEYWORDS_HEAD_DOWN = ["低头", "头部下垂", "闭眼", "头部贴近"]
POSE_KEYWORDS_AWAKE = ["清醒", "坐姿端正", "身体直立", "正常办公"]
POSE_KEYWORDS_SLEEP_MENTION = ["睡", "睡眠"]
NEGATION_PREFIXES = ["未见", "未发现", "未出现", "未观察", "无", "没有", "不", "非", "排除", "毫无", "并无", "未"]
CONJUNCTIONS = ["或", "和", "及"]


def _mentions_with_negation(text: str, keywords: list[str]) -> tuple[bool, bool]:
    """Check keyword mentions with negation-prefix detection.

    Returns (positive_mention, negated_mention).
    "未见趴伏" → (False, True); "人员趴伏" → (True, False).
    "未出现趴伏或低头" → both keywords negated (conjunction propagation).
    """
    positive = False
    negated = False
    for keyword in keywords:
        start = 0
        while True:
            idx = text.find(keyword, start)
            if idx < 0:
                break
            prefix = text[max(0, idx - 6) : idx]
            is_negated = any(neg in prefix for neg in NEGATION_PREFIXES)
            if not is_negated:
                # Conjunction propagation: "未出现A或B" negates B too
                for conj in CONJUNCTIONS:
                    conj_idx = prefix.rfind(conj)
                    if conj_idx >= 0:
                        before_conj = prefix[:conj_idx]
                        if any(neg in before_conj for neg in NEGATION_PREFIXES):
                            is_negated = True
                            break
            if is_negated:
                negated = True
            else:
                positive = True
            start = idx + len(keyword)
    return positive, negated


def parse_condition(filename: str) -> dict:
    match = QA_FILE_RE.match(filename)
    if match is None:
        return {"phase": "unknown", "quant": "unknown", "prompt": "unknown"}
    return {
        "phase": match.group("phase"),
        "quant": match.group("quant"),
        "prompt": "simple" if match.group("prompt") else "default",
    }


def parse_qa_row(row: dict, condition: dict, source_file: str, row_index: int) -> dict:
    conversations = row.get("conversations", [])
    user_text = conversations[0]["value"] if conversations else ""
    gpt_raw = conversations[1]["value"] if len(conversations) > 1 else ""
    image = row.get("image", "")

    record: dict[str, Any] = {
        "run_id": f"{source_file}:{row_index}",
        "condition": condition,
        "image": image,
        "user_text": user_text,
        "gpt_raw": gpt_raw,
        "parse_status": "unparsed",
        "task": None,
        "answer": None,
        "evidence": None,
    }

    # Try JSON parse (default prompt format)
    try:
        parsed = json.loads(gpt_raw)
        if isinstance(parsed, dict):
            record["parse_status"] = "parsed"
            record["task"] = parsed.get("task")
            answer = parsed.get("answer")
            # Normalize: accept int or string digit
            if isinstance(answer, str) and answer.strip().isdigit():
                answer = int(answer.strip())
            record["answer"] = answer
            record["evidence"] = parsed.get("evidence", [])
    except (json.JSONDecodeError, TypeError):
        pass

    return record


def check_d1_enum(record: dict) -> dict:
    """D1: answer must be in {0, 1, 2}."""
    if record["parse_status"] != "parsed":
        return {"item": "D1", "verdict": "NIE", "reason": "unparsed_natural_language"}
    answer = record["answer"]
    if answer in VALID_ANSWERS and isinstance(answer, int):
        return {"item": "D1", "verdict": "support", "answer": answer}
    return {
        "item": "D1",
        "verdict": "refute",
        "answer": answer,
        "reason": f"answer={answer!r} not in closed set {{0,1,2}}",
    }


def check_c3_conflicts(records: list[dict]) -> list[dict]:
    """C3: same image + same task + different answer across conditions → suspicious."""
    by_image: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if record["parse_status"] == "parsed" and record["answer"] is not None:
            by_image[record["image"]].append(record)

    conflicts: list[dict] = []
    for image, group in sorted(by_image.items()):
        answers = {}
        for record in group:
            key = f"{record['condition']['phase']}|{record['condition']['quant']}|{record['condition']['prompt']}"
            answers[key] = record["answer"]
        unique_answers = set(answers.values())
        if len(unique_answers) > 1:
            conflicts.append(
                {
                    "image": image,
                    "answers_by_condition": answers,
                    "conflicting_answers": sorted(unique_answers),
                    "verdict": "suspicious",
                    "reason": f"same image, {len(unique_answers)} different answers across conditions",
                }
            )
    return conflicts


def check_b3_grounding(record: dict, frozen: dict | None) -> dict:
    """B3 v1: keyword-based grounding of evidence to frozen static pose facts."""
    if record["parse_status"] != "parsed" or record["evidence"] is None:
        return {"item": "B3", "verdict": "NIE", "reason": "no structured evidence"}
    if frozen is None:
        return {"item": "B3", "verdict": "NIE", "reason": "no frozen evidence for image"}

    evidence_text = " ".join(record["evidence"]) if isinstance(record["evidence"], list) else str(record["evidence"])
    persons = frozen.get("persons", [])
    has_prone_person = any(p.get("pose_proxy", {}) and p["pose_proxy"].get("prone_like") for p in persons)
    has_head_down_person = any(p.get("pose_proxy", {}) and p["pose_proxy"].get("head_down") for p in persons)
    person_count = len(persons)

    prone_pos, prone_neg = _mentions_with_negation(evidence_text, POSE_KEYWORDS_PRONE)
    head_down_pos, head_down_neg = _mentions_with_negation(evidence_text, POSE_KEYWORDS_HEAD_DOWN)
    awake_pos, _ = _mentions_with_negation(evidence_text, POSE_KEYWORDS_AWAKE)
    sleep_pos, _ = _mentions_with_negation(evidence_text, POSE_KEYWORDS_SLEEP_MENTION)

    grounding_edges: list[str] = []
    if prone_pos or prone_neg:
        grounding_edges.append(f"prone(mention={prone_pos},negated={prone_neg}) → frozen prone_like={has_prone_person}")
    if head_down_pos or head_down_neg:
        grounding_edges.append(f"head_down(mention={head_down_pos},negated={head_down_neg}) → frozen head_down={has_head_down_person}")

    # Positive claim of prone but frozen pose doesn't support it
    if prone_pos and not has_prone_person:
        return {
            "item": "B3",
            "verdict": "suspicious",
            "reason": "evidence claims prone behavior but frozen pose does not support",
            "grounding_edges": grounding_edges,
        }
    # Negated claim ("未见趴伏") but frozen pose shows prone person
    if prone_neg and has_prone_person:
        return {
            "item": "B3",
            "verdict": "suspicious",
            "reason": "evidence denies prone behavior but frozen pose shows prone-like person",
            "grounding_edges": grounding_edges,
        }
    # Claims awake but frozen shows prone
    if awake_pos and has_prone_person:
        return {
            "item": "B3",
            "verdict": "suspicious",
            "reason": "evidence claims awake/normal but frozen pose shows prone-like person",
            "grounding_edges": grounding_edges,
        }
    # Claims sleep behavior but frozen shows no prone
    if sleep_pos and not has_prone_person and not has_head_down_person:
        return {
            "item": "B3",
            "verdict": "NIE",
            "reason": "evidence mentions sleep but static image cannot verify temporal 'prolonged stillness'",
            "grounding_edges": grounding_edges,
        }
    if grounding_edges or awake_pos or sleep_pos:
        return {
            "item": "B3",
            "verdict": "support",
            "reason": "keyword-level grounding consistent with frozen pose (or NIE-bound temporal claim)",
            "grounding_edges": grounding_edges,
            "frozen_person_count": person_count,
        }
    return {"item": "B3", "verdict": "NIE", "reason": "no pose-related keywords in evidence"}


def load_frozen_evidence(evidence_dir: Path) -> dict[str, dict]:
    """Load frozen evidence records, keyed by image filename."""
    frozen: dict[str, dict] = {}
    for path in sorted(evidence_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        frozen[path.stem + ".jpg"] = record
    return frozen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-dir", required=True, help="directory containing sleep-*.jsonl files")
    parser.add_argument("--evidence-dir", required=True, help="directory of frozen evidence JSON files")
    args = parser.parse_args()

    qa_dir = Path(args.qa_dir)
    evidence_dir = Path(args.evidence_dir)
    if not qa_dir.is_dir():
        raise FileNotFoundError(qa_dir)
    if not evidence_dir.is_dir():
        raise FileNotFoundError(evidence_dir)

    # Load frozen evidence
    frozen_by_image = load_frozen_evidence(evidence_dir)
    print(f"frozen evidence: {len(frozen_by_image)} images")

    # Parse all QA records
    all_records: list[dict] = []
    for jsonl_path in sorted(qa_dir.glob("sleep-*.jsonl")):
        condition = parse_condition(jsonl_path.name)
        with jsonl_path.open(encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                row = json.loads(line)
                record = parse_qa_row(row, condition, jsonl_path.stem, i)
                all_records.append(record)
    print(f"QA records: {len(all_records)}")

    # Run checks
    d1_results = [check_d1_enum(r) for r in all_records]
    c3_conflicts = check_c3_conflicts(all_records)
    b3_results = []
    for record in all_records:
        frozen = frozen_by_image.get(record["image"])
        b3_results.append(check_b3_grounding(record, frozen))

    # Aggregate
    def verdict_counts(results: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for r in results:
            counts[r["verdict"]] += 1
        return dict(counts)

    d1_counts = verdict_counts(d1_results)
    b3_counts = verdict_counts(b3_results)

    # Answer distribution by condition
    answer_by_condition: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in all_records:
        if record["parse_status"] == "parsed" and record["answer"] is not None:
            cond = f"{record['condition']['phase']}-{record['condition']['quant']}-{record['condition']['prompt']}"
            answer_by_condition[cond][str(record["answer"])] += 1

    run = open_run(
        "scenario5_qa_consistency",
        {
            "qa_dir": str(qa_dir),
            "evidence_dir": str(evidence_dir),
            "n_qa_records": len(all_records),
            "n_frozen_images": len(frozen_by_image),
            "checks": ["D1-enum", "C3-cross-condition-conflict", "B3-static-grounding-v1"],
        },
        ROOT / "scenario5" / "runs",
    )

    result = {
        "schema_version": "scenario5_qa_consistency_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "n_qa_records": len(all_records),
        "n_frozen_images": len(frozen_by_image),
        "d1_enum_check": {
            "verdict_counts": d1_counts,
            "total": len(d1_results),
        },
        "c3_cross_condition_conflicts": {
            "n_conflict_images": len(c3_conflicts),
            "conflicts": c3_conflicts,
        },
        "b3_static_grounding": {
            "verdict_counts": b3_counts,
            "total": len(b3_results),
            "method": "keyword-v1",
        },
        "answer_distribution_by_condition": {k: dict(v) for k, v in answer_by_condition.items()},
        "parse_status": {
            "parsed": sum(1 for r in all_records if r["parse_status"] == "parsed"),
            "unparsed": sum(1 for r in all_records if r["parse_status"] == "unparsed"),
        },
        "interpretation": "D1 checks closed-set membership. C3 flags same-image cross-condition answer conflicts as suspicious (not refute). B3 is keyword-level grounding v1; NLP grounding comes later. Static images cannot prove 'prolonged stillness' for sleep.",
    }
    run.save_result(result)

    print("\n=== D1 Enum Check ===")
    print(f"  {dict(d1_counts)}")
    print("\n=== C3 Cross-Condition Conflicts ===")
    print(f"  {len(c3_conflicts)} images with conflicting answers")
    for c in c3_conflicts[:5]:
        print(f"  {c['image']}: answers={c['answers_by_condition']}")
    print("\n=== B3 Static Grounding ===")
    print(f"  {dict(b3_counts)}")
    print("\n=== Parse Status ===")
    print(f"  parsed={result['parse_status']['parsed']}, unparsed={result['parse_status']['unparsed']}")
    print(f"\nrun: {run.path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
