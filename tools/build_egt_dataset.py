"""构建EGT(Evidence-Grounded Tri-state)三态训练数据集并按runs协议落盘.

三条种子路径合并(v2叙事升级):
  QA路径    冻结QA(91条) → QAConsistencyModule收集support种子 →
            S(原样)/R(确定性翻转, scope锚定+锚注入)/N(支持删除/证据换源);
  语句路径  16文档MinerU content_list块 → 结构化语句种子 →
            S(轻量改写)/R(确定性翻转+模块复判)/N(跨块/块内删除);
  叙事路径  16文档表格行事实三元组 → 真实QA answer风格叙事模板 →
            S(真实值叙事)/R(跨行值污染)/N(效果性扩展断言).

叙事vs近拷贝比例控制: R样本中叙事≥--narrative-share-r(默认60%),
近拷贝(statement/QA路径翻转)确定性等距降采样保留作难例负例; S/N同理
(N以效果性叙事为主, 删除式保留部分). 目标总3000-5000, S:R:N均衡.

流程: 三路径合并 → 比例混合 → 每类封顶(等距采样) → 均衡 →
egt_dataset.jsonl + result.json 落入 data/gjb_438c/runs/.
单文档解析失败时记录原因并继续.

用法:
  python tools/build_egt_dataset.py [--docs all|04|01,04,16]
      [--limit N] [--no-balance] [--cap-per-label 1500] [--max-peers 8]
      [--narrative-share-r 0.6] [--narrative-share-s 0.6]
      [--narrative-share-n 0.6]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.egt_synthesis import (  # noqa: E402
    EGT_VERSION,
    STATEMENT_QUESTION,
    SUPPORT_SEED_METHODS,
    EgtSample,
    assemble_dataset,
    collect_statement_seeds,
    collect_support_seeds,
    evidence_from_dict,
    extract_narrative_corpus,
    sample_to_dict,
    synthesize_narrative_samples,
    synthesize_nie_from_statements,
    synthesize_nie_samples,
    synthesize_refute_from_statements,
    synthesize_refute_samples,
    synthesize_support_from_statements,
    synthesize_support_samples,
)
from algorithms.consistency.qa_models import QAInput  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
MINERU_STANDARD = BASE / "data/gjb_438c/mineru_standard"

_CONTENT_TYPES = ("text", "table", "list")


def load_frozen_qa(path: Path, limit: int | None = None) -> list[QAInput]:
    rows = [json.loads(line) for line
            in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit is not None:
        rows = rows[:limit]
    return [QAInput(
        instance_id=str(row["instance_id"]),
        question=str(row["question"]),
        answer=str(row["answer"]),
        context_freeze_id=str(row["context_freeze_id"]),
        evidence=tuple(evidence_from_dict(item) for item in row["evidence"]),
    ) for row in rows]


def select_doc_dirs(spec: str) -> list[Path]:
    """--docs all|04|01,04,16 → mineru_standard下的文档目录列表(按名排序)."""
    if not MINERU_STANDARD.is_dir():
        return []
    dirs = sorted(d for d in MINERU_STANDARD.iterdir() if d.is_dir())
    if spec.lower() == "all":
        return dirs
    picked: list[Path] = []
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        matches = [d for d in dirs if d.name.startswith(token)]
        if not matches:
            raise SystemExit(f"未找到匹配 --docs '{token}' 的文档目录")
        picked.extend(matches)
    return sorted(set(picked))


def load_content_list(doc_dir: Path) -> list[dict[str, Any]]:
    path = doc_dir / "office" / f"{doc_dir.name}_content_list.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"content_list不是块列表: {path}")
    return data


def _refute_acceptance(
    refute_samples: list[EgtSample],
    skipped_self_check: int,
) -> dict[str, Any]:
    """kept-R样本的验收指标: 自检通过率与模块复判refute率."""
    verdicts = Counter(
        sample.module_verdict for sample in refute_samples
        if sample.module_verdict is not None)
    n_kept = len(refute_samples)
    self_checked = n_kept + skipped_self_check
    n_verdicted = sum(verdicts.values())
    return {
        "kept_refute": n_kept,
        "skipped_self_check": skipped_self_check,
        "self_check_pass_rate": (
            round(n_kept / self_checked, 4) if self_checked else None),
        "module_verdicts_of_kept": dict(verdicts),
        "module_refute_rate_of_kept": (
            round(verdicts.get("refute", 0) / n_verdicted, 4)
            if n_verdicted else None),
    }


def _sample_sort_key(sample: EgtSample) -> tuple[str, str, str]:
    return (sample.seed_id, sample.operator,
            re.sub(r"\s+", "", sample.claim_text))


def _stride_samples(samples: list[EgtSample], target: int) -> list[EgtSample]:
    """确定性等距采样(保序, doc多样性)."""
    if target <= 0:
        return []
    if len(samples) <= target:
        return list(samples)
    step = len(samples) / target
    return [samples[int(i * step)] for i in range(target)]


def _mix_narrative_share(
    label: str,
    all_samples: list[EgtSample],
    share: float,
) -> tuple[list[EgtSample], dict[str, Any]]:
    """单标签池的叙事比例混合: 近拷贝(泛化问句的statement/QA翻转样本)
    等距降采样至叙事占比≥share; QA路径种子(真实question)全部保留.

    share语义: narrative / (narrative + kept_near) ≥ share——quota按
    叙事+全保留QA的总量计算(ceil, 保证≥而非≈).
    """
    label_samples = [s for s in all_samples if s.label == label]
    narrative = sorted(
        (s for s in label_samples if s.source.startswith("narrative:")),
        key=_sample_sort_key)
    near = [s for s in label_samples
            if not s.source.startswith("narrative:")]
    # QA路径样本带真实question(91QA种子), 全保留; 只降权statement级近拷贝
    qa_kept = sorted((s for s in near
                      if s.question != STATEMENT_QUESTION),
                     key=_sample_sort_key)
    near_stmt = sorted((s for s in near if s.question == STATEMENT_QUESTION),
                       key=_sample_sort_key)
    # 份额约束: narr/(narr+qa+quota) ≥ share → near总量 ≤ narr*(1-s)/s
    allowance = (math.floor(len(narrative) * (1.0 - share) / share)
                 if narrative and 0.0 < share < 1.0 else
                 len(near_stmt) if not narrative else 0)
    quota = max(0, allowance - len(qa_kept))
    kept_near = qa_kept + _stride_samples(near_stmt, quota)
    total = len(narrative) + len(kept_near)
    stats = {
        "narrative": len(narrative),
        "near_kept": len(kept_near),
        "near_dropped": len(near_stmt) + len(qa_kept) - len(kept_near),
        "target_share": share,
        "actual_share": (round(len(narrative) / total, 4)
                         if total else None),
    }
    return narrative + kept_near, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=FROZEN)
    parser.add_argument("--docs", type=str, default="all",
                        help="语句级/叙事级种子文档: all|单文档号(04)|逗号列表(01,04)")
    parser.add_argument("--limit", type=int, default=None,
                        help="只跑前N条QA(冒烟测试)")
    parser.add_argument("--cap-per-label", type=int, default=1500)
    parser.add_argument("--no-balance", dest="balance", action="store_false",
                        help="不做类别均衡下采样(只做封顶)")
    parser.add_argument("--max-peers", type=int, default=8,
                        help="cross-instance N最多尝试的同伴证据数")
    parser.add_argument("--narrative-share-r", type=float, default=0.8,
                        help="R样本中叙事占比下限(近拷贝降采样)")
    parser.add_argument("--narrative-share-s", type=float, default=0.6,
                        help="S样本中叙事占比下限")
    parser.add_argument("--narrative-share-n", type=float, default=0.6,
                        help="N样本中叙事(效果性)占比下限")
    parser.add_argument("--narrative-n-modes", type=str,
                        default="effect",
                        help="叙事N模式: effect,detail,foreign,value_absent"
                             "的逗号列表(默认仅效果性——91QA实测最佳)")
    parser.add_argument("--narrative-question", type=str, default="generic",
                        choices=("generic", "real"),
                        help="叙事样本问句: generic=统一声明问句, "
                             "real=族问句(question锚定premise)")
    args = parser.parse_args()
    n_modes = frozenset(token.strip() for token
                        in args.narrative_n_modes.split(",") if token.strip())

    module = QAConsistencyModule(use_experts=True)

    # ── QA路径(91条冻结QA) ───────────────────────────────────
    requests = load_frozen_qa(args.input, args.limit)
    seeds = collect_support_seeds(requests, module)
    peer_evidence = {request.instance_id: request.evidence
                     for request in requests}
    qa_support = synthesize_support_samples(seeds)
    qa_refute = synthesize_refute_samples(seeds, module=module)
    qa_nie = synthesize_nie_samples(seeds, module=module,
                                    peer_evidence=peer_evidence,
                                    max_peers=args.max_peers)

    # ── 语句路径 + 叙事路径(16文档MinerU块) ──────────────────
    doc_dirs = select_doc_dirs(args.docs)
    statement_samples: list[EgtSample] = []
    narrative_samples: list[EgtSample] = []
    stmt_refute_samples: list[EgtSample] = []
    stmt_refute_stats: dict[str, Any] = {
        "n_seeds": 0, "skipped_no_flippable_structure": 0,
        "skipped_self_check": 0, "skipped_module_gate": 0,
        "attempts_by_operator": Counter(), "kept_by_operator": Counter(),
    }
    per_doc: list[dict[str, Any]] = []
    doc_errors: dict[str, str] = {}
    narrative_by_family: Counter = Counter()
    # 第一遍: 加载全部文档块 + 叙事事实抽取(供跨doc foreign池)
    doc_blocks: dict[str, list[dict[str, Any]]] = {}
    doc_facts: dict[str, list[Any]] = {}
    doc_pools: dict[str, Any] = {}
    for doc_dir in doc_dirs:
        try:
            blocks = load_content_list(doc_dir)
        except Exception as exc:
            doc_errors[doc_dir.name] = f"{type(exc).__name__}: {exc}"
            continue
        try:
            facts, pools = extract_narrative_corpus(blocks, doc_dir.name)
        except Exception as exc:
            doc_errors[doc_dir.name] = f"{type(exc).__name__}: {exc}"
            continue
        doc_blocks[doc_dir.name] = blocks
        doc_facts[doc_dir.name] = facts
        doc_pools[doc_dir.name] = pools
    all_descriptions: dict[str, tuple[str, ...]] = {
        name: pools.descriptions for name, pools in doc_pools.items()
    }
    for doc_dir in doc_dirs:
        if doc_dir.name not in doc_blocks:
            continue
        blocks = doc_blocks[doc_dir.name]
        facts, pools = doc_facts[doc_dir.name], doc_pools[doc_dir.name]
        try:
            stmt_seeds = collect_statement_seeds(blocks, doc_dir.name)
            st_support = synthesize_support_from_statements(stmt_seeds, blocks)
            st_refute = synthesize_refute_from_statements(
                stmt_seeds, blocks, module=module)
            st_nie = synthesize_nie_from_statements(
                stmt_seeds, blocks, module=module)
            foreign = sorted({
                desc for name, descs in all_descriptions.items()
                if name != doc_dir.name for desc in descs
            })
            narr = synthesize_narrative_samples(
                facts, blocks, pools, foreign, n_modes,
                question_mode=args.narrative_question)
        except Exception as exc:  # 单文档失败不阻断整体, 原因入result
            doc_errors[doc_dir.name] = f"{type(exc).__name__}: {exc}"
            continue
        statement_samples.extend(
            st_support.samples + st_refute.samples + st_nie.samples)
        stmt_refute_samples.extend(st_refute.samples)
        narrative_samples.extend(narr.samples)
        narrative_by_family.update(
            Counter(s.claim_kind for s in narr.samples))
        stmt_refute_stats["n_seeds"] += st_refute.stats["n_seeds"]
        for key in ("skipped_no_flippable_structure", "skipped_self_check",
                    "skipped_module_gate"):
            stmt_refute_stats[key] += st_refute.stats[key]
        for key in ("attempts_by_operator", "kept_by_operator"):
            counter: Counter = stmt_refute_stats[key]
            counter.update(st_refute.stats[key])
        per_doc.append({
            "doc": doc_dir.name,
            "n_blocks": len(blocks),
            "n_content_blocks": sum(
                1 for b in blocks if str(b.get("type", "")) in _CONTENT_TYPES),
            "n_seeds": len(stmt_seeds),
            "n_narrative_facts": len(facts),
            "kept": {
                "support": len(st_support.samples),
                "refute": len(st_refute.samples),
                "not_in_evidence": len(st_nie.samples),
                "narrative": len(narr.samples),
            },
        })
    stmt_refute_stats["attempts_by_operator"] = dict(
        stmt_refute_stats["attempts_by_operator"])
    stmt_refute_stats["kept_by_operator"] = dict(
        stmt_refute_stats["kept_by_operator"])

    # ── 叙事比例混合(近拷贝降权, QA种子全保留) ────────────────
    qa_samples = (qa_support.samples + qa_refute.samples + qa_nie.samples)
    all_samples = qa_samples + statement_samples + narrative_samples
    shares = {
        "support": args.narrative_share_s,
        "refute": args.narrative_share_r,
        "not_in_evidence": args.narrative_share_n,
    }
    mixed: list[EgtSample] = []
    mix_stats: dict[str, Any] = {}
    for label, share in shares.items():
        label_pool, stats = _mix_narrative_share(label, all_samples, share)
        mixed.extend(label_pool)
        mix_stats[label] = stats

    final, dataset_stats = assemble_dataset(
        mixed, cap_per_label=args.cap_per_label, balance=args.balance)

    acceptance = _refute_acceptance(
        qa_refute.samples + stmt_refute_samples,
        qa_refute.stats["skipped_self_check"]
        + stmt_refute_stats["skipped_self_check"])

    config = {
        "input": str(args.input.relative_to(BASE)),
        "docs": args.docs,
        "n_qa": len(requests),
        "n_doc_dirs": len(doc_dirs),
        "allowed_seed_methods": sorted(SUPPORT_SEED_METHODS),
        "cap_per_label": args.cap_per_label,
        "balance": args.balance,
        "max_peers": args.max_peers,
        "narrative_shares": shares,
        "narrative_n_modes": sorted(n_modes),
        "narrative_question": args.narrative_question,
        "statement_question": STATEMENT_QUESTION,
        "module": "QAConsistencyModule(use_experts=True)",
        "version": EGT_VERSION,
    }
    run = open_run("build_egt_dataset", config)

    payload = "\n".join(json.dumps(sample_to_dict(sample), ensure_ascii=False)
                        for sample in final) + "\n"
    dataset_path = run.path / "egt_dataset.jsonl"
    dataset_path.write_text(payload, encoding="utf-8")
    run.log(event="dataset_written", samples=len(final),
            path=str(dataset_path.relative_to(BASE)))

    result = {
        "n_qa": len(requests),
        "seeds": {
            "total": len(seeds),
            "by_method": dict(Counter(seed.method for seed in seeds)),
        },
        "qa_path": {
            "support": qa_support.stats,
            "refute": qa_refute.stats,
            "nie": qa_nie.stats,
        },
        "statement_path": {
            "per_doc": per_doc,
            "doc_errors": doc_errors,
            "refute": stmt_refute_stats,
        },
        "narrative_path": {
            "n_samples": len(narrative_samples),
            "by_family": dict(narrative_by_family),
        },
        "narrative_mix": mix_stats,
        "dataset": dataset_stats,
        "final_by_source": dict(Counter(
            sample.source.split(":", 1)[0] for sample in final)),
        "final_by_operator": dict(Counter(sample.operator for sample in final)),
        "final_narrative_share_by_label": {
            label: (round(final_narrative_label / label_total, 4)
                    if label_total else None)
            for label, (final_narrative_label, label_total) in {
                label: (
                    sum(1 for s in final
                        if s.label == label
                        and s.source.startswith("narrative:")),
                    sum(1 for s in final if s.label == label),
                ) for label in shares
            }.items()
        },
        "acceptance": acceptance,
        "files": {
            "egt_dataset.jsonl": len(final),
        },
    }
    run.save_result(result)

    print(json.dumps({
        "n_qa": len(requests),
        "n_docs": len(doc_dirs),
        "doc_errors": doc_errors,
        "raw": dataset_stats["raw_counts"],
        "final": dataset_stats["final_counts"],
        "final_by_source": result["final_by_source"],
        "final_narrative_share_by_label":
            result["final_narrative_share_by_label"],
        "narrative_mix": mix_stats,
        "refute_self_check_pass_rate": acceptance["self_check_pass_rate"],
        "refute_module_verdicts_of_kept":
            acceptance["module_verdicts_of_kept"],
        "refute_module_refute_rate_of_kept":
            acceptance["module_refute_rate_of_kept"],
    }, ensure_ascii=False, indent=2))
    print(f"dataset: {dataset_path}")
    print(f"run: {run.path}")


if __name__ == "__main__":
    main()
