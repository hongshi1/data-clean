r"""MMQA数据集构建主管线: 40项注入×pair级物化→声明编译→门禁→切分.

按docs/srs_project/mmqa_dataset_design.md(算子对齐14_strict_40_design):
  1. 加载锚定可信pair(第一阶段: anchor_mapping_confidence=high, 81对)
  2. 40项check_item×pair 注入(不适用诚实跳过) → MutationRecord
  3. 虚拟pair物化 → load_pair_claims编译声明对(现有管线零改动)
  4. 门禁: G1结构/G3标签/G5泄漏(确定性检查)
  5. pair级split(同pair全部变异同split, 70/10/20)
  6. 产出: mutations.jsonl/consistency.jsonl/splits.json/
     check_report.json/DATASET_CARD.md

用法: python tools/mmqa_build.py [--limit-pairs N] [--per-item 1]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency_check.mmqa.mutation import (  # noqa: E402
    CHANNEL_MAP,
    MutationEngine40,
    materialize,
)
from algorithms.consistency_check.nli_pair_claims import load_pair_claims  # noqa: E402
from run_utils import open_run  # noqa: E402

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
OUT_ROOT = BASE / "data/gjb_438c/mmqa"

FORTY_ITEMS = [f"TERM-{i:02d}" for i in range(1, 9)] + \
              [f"PARAM-{i:02d}" for i in range(1, 11)] + \
              [f"LOGIC-{i:02d}" for i in range(1, 12)] + \
              [f"GJB-{i:02d}" for i in range(1, 12)]

# LOGIC层的llm通道项(01/02/06~11)第一阶段不注入文本级编辑——
# 其证据源需要chunks级业务约束提取(inject_rules_v3已有, 后续接);
# 第一阶段物化管线先覆盖有pair级编辑原语的项
PHASE1_ITEMS = [c for c in FORTY_ITEMS if CHANNEL_MAP.get(c) != "llm"]


def load_high_pairs() -> list[Path]:
    """锚定可信pair: meta.json的anchor_mapping_confidence=high."""
    out: list[Path] = []
    for scene_dir in sorted(PAIR_ROOT.iterdir()):
        if not scene_dir.is_dir() or scene_dir.name.startswith("sc8"):
            continue
        for pd in sorted(scene_dir.iterdir()):
            meta_p = pd / "meta.json"
            if not meta_p.exists():
                continue
            try:
                meta = json.loads(meta_p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if meta.get("anchor_mapping_confidence") == "high":
                out.append(pd)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-pairs", type=int, default=None)
    ap.add_argument("--per-item", type=int, default=1,
                    help="每pair每check_item注入条数")
    args = ap.parse_args()

    run = open_run("mmqa_build", {
        "phase": "1", "per_item": args.per_item,
        "limit_pairs": args.limit_pairs, "items": PHASE1_ITEMS})
    pairs = load_high_pairs()
    if args.limit_pairs:
        pairs = pairs[:args.limit_pairs]
    print(f"锚定high pair: {len(pairs)}对 | 注入项: {len(PHASE1_ITEMS)}/40"
          f" (第一阶段, llm通道项后接)")

    engine = MutationEngine40(seed=42)
    mutations: list[dict[str, Any]] = []
    virtual_root = OUT_ROOT / "virtual_pairs"
    n_attempt = 0
    for pd in pairs:
        for item in PHASE1_ITEMS:
            for _ in range(args.per_item):
                n_attempt += 1
                rec = engine.mutate(pd, item)
                if rec is None:
                    continue
                # 物化(场景子目录保持parent.name=场景名, 声明编译路由依赖)
                vdir = materialize(rec, virtual_root / pd.parent.name, pd)
                # 声明编译: 虚拟pair的parent目录需带场景名以路由编译器
                _, claims = load_pair_claims(vdir)
                rec["verify_gate"]["claim_compilable"] = bool(claims)
                rec["n_claims"] = len(claims)
                if claims:
                    rec["claims"] = [
                        {"why": c.why, "entity": c.entity,
                         "premise": c.premise, "hypothesis": c.hypothesis,
                         "template": c.template} for c in claims]
                mutations.append(rec)

    # ── 门禁 ──
    issues: list[dict[str, str]] = []

    def g1_structure() -> None:
        ids = [m["mutation_id"] for m in mutations]
        dup = len(ids) - len(set(ids))
        if dup:
            issues.append({"gate": "G1", "status": "fail",
                           "desc": f"mutation_id重复{dup}"})
        for m in mutations:
            if m["check_item"] not in FORTY_ITEMS:
                issues.append({"gate": "G1", "status": "fail",
                               "sample": m["mutation_id"],
                               "desc": f"非40项: {m['check_item']}"})

    def g3_label() -> None:
        for m in mutations:
            if m["expected_label"] != "inconsistent":
                issues.append({"gate": "G3", "status": "fail",
                               "sample": m["mutation_id"],
                               "desc": "注入负例标签异常"})

    def g5_leakage() -> None:
        # 构造期保证: 同pair全部变异继承pair的split(下面切分时统一)
        pass

    g1_structure()
    g3_label()
    g5_leakage()

    # ── 切分(pair级, 同pair变异同split) ──
    by_pair: dict[str, list[int]] = defaultdict(list)
    for i, m in enumerate(mutations):
        by_pair[m["source_evidence"]["pair_id"]].append(i)
    pair_ids = sorted(by_pair)
    rng = __import__("random").Random(42)
    rng.shuffle(pair_ids)
    n_dev = max(1, len(pair_ids) // 10)
    n_test = max(1, len(pair_ids) // 5)
    split_map = {}
    for pid in pair_ids[:n_dev]:
        split_map[pid] = "dev"
    for pid in pair_ids[n_dev:n_dev + n_test]:
        split_map[pid] = "test"
    for pid in pair_ids[n_dev + n_test:]:
        split_map[pid] = "train"
    for i, m in enumerate(mutations):
        m["split"] = split_map[m["source_evidence"]["pair_id"]]

    # ── 落盘 ──
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "mutations.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in mutations),
        encoding="utf-8")
    (OUT_ROOT / "splits.json").write_text(json.dumps(
        {"version": "v0.1", "seed": 42, "unit": "pair",
         "pair_to_split": split_map,
         "known_limitation": "阶段1全部high pair来自文档02, "
                             "仅测文档内泛化(doc级split待P2)"},
        ensure_ascii=False, indent=1), encoding="utf-8")

    n_claims_total = sum(m.get("n_claims", 0) for m in mutations)
    report = {
        "check_id": "mmqa-gate-v0.1",
        "summary": {"total_mutations": len(mutations),
                    "n_attempts": n_attempt,
                    "applicable_rate": round(len(mutations) / n_attempt, 3),
                    "n_claims_compilable": sum(
                        1 for m in mutations if m["n_claims"] > 0),
                    "n_claims_total": n_claims_total,
                    "pass": 0 if issues else len(mutations),
                    "warn": 0, "fail": len(issues)},
        "by_item": dict(Counter(m["check_item"] for m in mutations)),
        "by_channel": dict(Counter(m["channel"] for m in mutations)),
        "by_split": dict(Counter(m["split"] for m in mutations)),
        "issues": issues,
    }
    (OUT_ROOT / "check_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    card = f"""# MMQA数据集卡片 v0.1(阶段1)

- **构建**: 40项校验体系对齐注入(不自创算子), {len(PHASE1_ITEMS)}项启用
  (llm通道{40 - len(PHASE1_ITEMS)}项待接chunks级证据)
- **候选池**: {len(pairs)}对锚定high pair(全部来自文档02 — 已知限制)
- **注入**: {len(mutations)}条MutationRecord(适用率
  {len(mutations)/n_attempt:.1%}), 每条含before/after/single_factor
- **声明编译**: {sum(1 for m in mutations if m['n_claims'] > 0)}条
  可编译NLI声明对(共{n_claims_total}条claim)
- **通道分流**: {dict(Counter(m['channel'] for m in mutations))}
- **切分**: pair级70/10/20(同pair变异同split); 阶段1仅测文档内泛化
- **门禁**: fail={len(issues)} (G1结构/G3标签)
- **敏感性**: 16份真实军事文档, 仅内部使用
- 复现: python tools/mmqa_build.py | runs: {run.path.name}
"""
    (OUT_ROOT / "DATASET_CARD.md").write_text(card, encoding="utf-8")
    run.save_result(report)
    run.log(n_pairs=len(pairs), n_mutations=len(mutations))

    print(f"\n注入: {len(mutations)}/{n_attempt} 适用"
          f"({len(mutations)/n_attempt:.1%})")
    print(f"  按项: {dict(Counter(m['check_item'] for m in mutations))}")
    print(f"  按通道: {dict(Counter(m['channel'] for m in mutations))}")
    print(f"  按split: {dict(Counter(m['split'] for m in mutations))}")
    print(f"声明可编译: {sum(1 for m in mutations if m['n_claims'] > 0)}"
          f"条mutation / 共{n_claims_total}条claim")
    print(f"门禁fail: {len(issues)}")
    print(f"产出 → {OUT_ROOT}")


if __name__ == "__main__":
    main()
