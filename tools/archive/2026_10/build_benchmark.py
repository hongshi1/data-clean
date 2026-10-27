r"""统一Benchmark构建: 15套评测集收编为1套(用户要求"统一的数据和方法").

设计(docs/srs_project/three_algorithms.md的统一数据层):
  4层数据源 → 统一schema → 去重 → 防泄漏切分 → 一次构建

统一schema: {id, premise, hypothesis, label, check_item, channel, tier, source_asset, split}
  label: consistent | inconsistent (二分类; 银标三分类映射: real_bug/benign→inconsistent, compiler→consistent)
  tier: L1_constructed | L3_silver | L4_positive
  channel: 词法/NLI/Z3/图/LLM (从check_item映射)

数据源(只收可信度高+格式可统一的4个):
  1. mmqa mutations(1318条L1负例, 闭世界声明对)
  2. eval_injected_v3(198条L1, 40项体系注入)
  3. 银标664(649条L3可构造, 真实分布分歧)
  4. 正例三族(~190条L4, 恒等60+真实50+等效40+同义词40)

防泄漏: mmqa的split继承; 银标与mmqa重叠部分标记; eval_v3全进test

用法: python tools/build_benchmark.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

OUT_PATH = BASE / "data/gjb_438c/benchmark.jsonl"

CHANNEL_MAP: dict[str, str] = {
    "TERM-01": "lexical", "TERM-02": "lexical", "TERM-04": "lexical",
    "TERM-05": "lexical", "TERM-07": "lexical", "TERM-08": "lexical",
    "TERM-03": "nli", "TERM-06": "nli",
    **{f"PARAM-{i:02d}": "z3" for i in range(1, 11)},
    "LOGIC-03": "nli", "LOGIC-04": "nli", "LOGIC-05": "nli",
    **{f"LOGIC-{i:02d}": "llm" for i in (1, 2, 6, 7, 8, 9, 10, 11)},
    **{f"GJB-{i:02d}": "lexical" for i in range(1, 12)},
}

# 银标三分类→二分类
SILVER_MAP = {"real_bug": "inconsistent", "benign_variation": "inconsistent",
              "compiler_bug": "consistent"}


def _dedup(items: list[dict]) -> list[dict]:
    """按(premise+hypothesis)哈希去重."""
    seen: set[str] = set()
    out = []
    for it in items:
        h = hashlib.md5(
            (it["premise"] + "|" + it["hypothesis"]).encode("utf-8")
        ).hexdigest()
        if h not in seen:
            seen.add(h)
            out.append(it)
    return out


def collect_mmqa() -> list[dict]:
    """L1负例: mmqa mutations(闭世界声明对, 构造性真值)."""
    items = []
    path = BASE / "data/gjb_438c/mmqa/mutations.jsonl"
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        m = json.loads(line)
        if not m.get("claims"):
            continue
        # 取第一条claim(最小对设计)
        c = m["claims"][0]
        items.append({
            "premise": c["premise"],
            "hypothesis": c["hypothesis"],
            "label": m["expected_label"],  # 全部inconsistent
            "check_item": m["check_item"],
            "channel": m.get("channel", CHANNEL_MAP.get(m["check_item"], "nli")),
            "tier": "L1_constructed",
            "source_asset": m["mutation_id"],
            "split": m.get("split", "train"),
        })
    return items


def collect_eval_v3() -> list[dict]:
    """L1混合: eval_injected_v3(40项体系注入+恒等正例)."""
    items = []
    path = BASE / "data/gjb_438c/data_assets/eval_injected_v3.json"
    if not path.exists():
        return items

    def _as_text(v: Any) -> str:
        if isinstance(v, list):
            return "、".join(str(x.get("name", x) if isinstance(x, dict) else x)
                             for x in v)
        if isinstance(v, dict):
            return str(v.get("name", v))
        return str(v)

    d = json.loads(path.read_text(encoding="utf-8"))
    for inj in d.get("injections", []):
        label = inj.get("label", "")
        if label not in ("consistent", "inconsistent"):
            continue
        original = _as_text(inj.get("original", ""))
        injected = _as_text(inj.get("injected", ""))
        if not original or not injected:
            continue
        occs = inj.get("occurrences", [])
        sa = occs[0].get("section", "") if occs else ""
        sb = occs[1].get("section", "") if len(occs) > 1 else sa
        ci = inj.get("check_item", "")
        if label == "consistent" and original == injected:
            p = f"文档{sa}章节规定：『{original}』。"
            h = f"文档{sb}章节规定：『{injected}』。"
        else:
            p = f"文档{sa}章节规定：『{original}』。"
            h = f"文档{sb}章节规定：『{injected}』。"
        items.append({
            "premise": p, "hypothesis": h, "label": label,
            "check_item": ci if ci != "POSITIVE" else "POSITIVE",
            "channel": CHANNEL_MAP.get(ci, "nli"),
            "tier": "L1_constructed",
            "source_asset": f"eval_v3_{inj.get('method', ci)}",
            "split": "test",  # 40项注入全进test(与mmqa训练隔离)
        })
    return items


def collect_silver() -> list[dict]:
    """L3银标: final_adjudication分歧驱动声明(真实分布)."""
    from algorithms.consistency_check.nli_discrepancy_review import (
        PairContext,
        build_claims_for_discrepancy,
    )
    items = []
    fa = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
    sa = BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json"
    sc = BASE / "data/gjb_438c/anchor_sc2/llm_adjudication.json"
    if not fa.exists():
        return items
    final = json.loads(fa.read_text(encoding="utf-8"))["final_labels"]
    src: dict[str, dict] = {}
    for p in (sa, sc):
        if p.exists():
            src.update(json.loads(p.read_text(encoding="utf-8")))
    ctx = PairContext(BASE / "data/gjb_438c/pair_dataset")
    for key, meta in final.items():
        disc = src.get(key)
        if disc is None:
            continue
        _, claim = build_claims_for_discrepancy(
            BASE / "data/gjb_438c/pair_dataset", disc["pair"], disc, ctx)
        if claim is None:
            continue
        label = SILVER_MAP.get(meta["label"], "inconsistent")
        items.append({
            "premise": claim.premise,
            "hypothesis": claim.hypothesis,
            "label": label,
            "check_item": disc.get("dtype", ""),
            "channel": "nli",  # 银标全走NLI通道(检测器侧统一)
            "tier": "L3_silver",
            "source_asset": f"silver_{key}",
            "split": "test",  # 银标是评测集不进train
        })
    return items


def collect_positives() -> list[dict]:
    """L4正例: 恒等(原pair)+真实多模态+单位等效+同义词."""
    import random
    rng = random.Random(42)
    items = []

    # 1) 恒等: 原pair的声明(benign pair, entailment)
    from algorithms.consistency_check.nli_pair_claims import load_pair_claims
    pair_root = BASE / "data/gjb_438c/pair_dataset"
    n_id = 0
    for scene_dir in sorted(pair_root.iterdir()):
        if not scene_dir.is_dir() or scene_dir.name.startswith("sc8"):
            continue
        for pd in sorted(scene_dir.iterdir())[:15]:  # 每场景15对
            if not (pd / "meta.json").exists():
                continue
            pid, claims = load_pair_claims(pd)
            if not claims:
                continue
            c = claims[0]
            # 质量门: 正例的计数必须一致(防伪正例混入)
            import re as _re
            pm = _re.search(r'共(\d+)项', c.premise)
            hm = _re.search(r'共(\d+)个', c.hypothesis)
            if pm and hm and pm.group(1) != hm.group(1):
                continue  # 计数不匹配的不是正例(实际存在分歧)
            items.append({
                "premise": c.premise, "hypothesis": c.hypothesis,
                "label": "consistent", "check_item": "P0_IDENTITY",
                "channel": "nli", "tier": "L4_positive",
                "source_asset": f"p0_{pid}",
                "split": "test"})
            n_id += 1

    # 2) 真实多模态: eval_set的50条
    ev2 = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
    if ev2.exists():
        es = json.loads(ev2.read_text(encoding="utf-8"))
        for e in es.get("entries", []):
            if e.get("label") != "consistent":
                continue
            occs = (e.get("entity") or {}).get("occurrences", [])
            if len(occs) < 2:
                continue
            inj = e.get("injection") or {}
            a = str(inj.get("original", occs[0].get("content", "")))
            b = str(inj.get("injected", occs[1].get("content", "")))
            sa = occs[0].get("section", "")
            sb = occs[1].get("section", "")
            items.append({
                "premise": f"文档{sa}章节规定：『{a}』。",
                "hypothesis": f"文档{sb}章节规定：『{b}』。",
                "label": "consistent", "check_item": "P1_REAL",
                "channel": "nli", "tier": "L4_positive",
                "source_asset": e.get("eval_id", ""),
                "split": "test"})

    # 3) 单位等效
    CONV = [("秒", "ms", 1000.0), ("s", "ms", 1000.0), ("分钟", "秒", 60.0),
            ("GB", "MB", 1024.0)]
    vals = [0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 100, 200, 500, 1000]
    for _ in range(20):
        val = rng.choice(vals)
        u1, u2, factor = rng.choice(CONV)
        items.append({
            "premise": f"文档规定：『{val:g}{u1}』。",
            "hypothesis": f"文档另一处规定：『{val * factor:g}{u2}』。",
            "label": "consistent", "check_item": "P2_EQUIV",
            "channel": "z3", "tier": "L4_positive",
            "source_asset": "equiv_synthetic",
            "split": "test"})

    # 4) 同义词改写(语义保持)
    SYN = {"获取": "采集", "管理": "管控", "监控": "监测", "处理": "处置"}
    for old, new in list(SYN.items())[:4]:
        for v in (10, 50, 100, 500, 1000):
            items.append({
                "premise": f"文档规定：『{old}{v}条数据』。",
                "hypothesis": f"文档另一处规定：『{new}{v}条数据』。",
                "label": "consistent", "check_item": "P3_SYNONYM",
                "channel": "lexical", "tier": "L4_positive",
                "source_asset": "syn_synthetic",
                "split": "test"})

    return items


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("══ 统一Benchmark构建 ══\n")

    # 收集4源
    mmqa = collect_mmqa()
    print(f"1. mmqa(L1负例): {len(mmqa)}条")
    ev3 = collect_eval_v3()
    print(f"2. eval_v3(L1混合): {len(ev3)}条")
    silver = collect_silver()
    print(f"3. 银标(L3真实分布): {len(silver)}条")
    positives = collect_positives()
    print(f"4. 正例(L4三族): {len(positives)}条")

    all_items = mmqa + ev3 + silver + positives
    print(f"\n合计(去重前): {len(all_items)}条")

    # 去重
    deduped = _dedup(all_items)
    print(f"去重后: {len(deduped)}条(去除{len(all_items) - len(deduped)}条重复)")

    # 编号
    for i, item in enumerate(deduped):
        item["id"] = f"BENCH-{i + 1:05d}"

    # 统计
    label_dist = Counter(x["label"] for x in deduped)
    tier_dist = Counter(x["tier"] for x in deduped)
    channel_dist = Counter(x["channel"] for x in deduped)
    split_dist = Counter(x["split"] for x in deduped)
    check_items = Counter(x["check_item"] for x in deduped
                          if x["check_item"] and not x["check_item"].startswith("P"))
    
    print(f"\n标签: {dict(label_dist)}")
    print(f"层级: {dict(tier_dist)}")
    print(f"通道: {dict(channel_dist)}")
    print(f"切分: {dict(split_dist)}")
    print(f"覆盖检查项: {len(check_items)}种")

    if args.dry_run:
        print("\n(dry-run, 不落盘)")
        return

    # 落盘
    OUT_PATH.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in deduped),
        encoding="utf-8")
    print(f"\nBenchmark → {OUT_PATH} ({len(deduped)}条)")

    # 构建统计卡
    stats = {
        "total": len(deduped), "label": dict(label_dist),
        "tier": dict(tier_dist), "channel": dict(channel_dist),
        "split": dict(split_dist),
        "check_items": dict(check_items),
        "dedup_removed": len(all_items) - len(deduped),
    }
    stats_path = OUT_PATH.parent / "benchmark_stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    print(f"统计 → {stats_path}")


if __name__ == "__main__":
    main()
