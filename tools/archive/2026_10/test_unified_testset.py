"""统一测试数据集: schema校验 + 规模/分布快照(论文数字锁定).

规范: docs/srs_project/test_dataset_spec.md
重生成: python tools/build_unified_testset.py (确定性, 无采样)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

UT = BASE / "data/gjb_438c/unified_testset"

# 论文数字快照: 源 → (总条数, inconsistent数)
SNAPSHOT = {
    "xnli_zh": (5010, 1670),
    "cmnli_dev": (12241, 4038),
    "ocnli_test": (10097, 3334),
    "gjb_bench_test": (922, 833),
    "gjb_gold": (23, 6),
    "gjb_gold_v2": (357, 153),
    "md_gold": (577, 255),
}

VALID_SOURCES = set(SNAPSHOT)
VALID_LABELS = {"inconsistent", "consistent"}


def _load(name: str) -> list[dict]:
    return [json.loads(line) for line in open(UT / f"{name}.jsonl", encoding="utf-8") if line.strip()]


def test_files_exist_and_index_matches():
    index = json.loads((UT / "INDEX.json").read_text(encoding="utf-8"))
    assert index["total"] == sum(n for n, _ in SNAPSHOT.values()) == 29227
    for src, (n, _) in SNAPSHOT.items():
        assert index["sources"][src]["n"] == n
        assert (UT / f"{src}.jsonl").exists()


def test_schema_valid():
    for src in VALID_SOURCES:
        for i, it in enumerate(_load(src)):
            assert set(it) == {"id", "source", "domain", "split_origin", "premise",
                               "hypothesis", "label", "label_raw", "type",
                               "contamination", "meta"}, f"{src}[{i}]字段集"
            assert it["label"] in VALID_LABELS
            assert it["source"] == src
            assert it["id"] == f"UT-{src}-{i:05d}"
            assert it["premise"] and it["hypothesis"]
            assert it["domain"] in ("general", "srs_synthetic", "srs_real")


def test_snapshot_counts_and_labels():
    for src, (n, n_inc) in SNAPSHOT.items():
        items = _load(src)
        assert len(items) == n, f"{src}规模变动: {len(items)} != {n}"
        labs = Counter(x["label"] for x in items)
        assert labs["inconsistent"] == n_inc, f"{src}不一致数变动: {labs}"


def test_contamination_matrix():
    """污染标注与行为验证一致(背诵级成绩=实锤), 防评测时误用污染格.

    行为证据(400条分层样本, seed42):
      - ocnli_test: Erlangshen F1=1.000(背诵) → 标注erlangshen ⚠
      - cmnli_dev:  Erlangshen F1=0.890(正常) → 标注干净
      - xnli_zh:    mDeBERTa 0.885 vs 干净OCNLI 0.743(+0.142) → 标注mdeberta ⚠
    """
    for src, expect in [("xnli_zh", "mdeberta"), ("cmnli_dev", ""),
                        ("ocnli_test", "erlangshen"), ("gjb_bench_test", "qlora"),
                        ("gjb_gold", ""), ("gjb_gold_v2", ""), ("md_gold", "")]:
        items = _load(src)
        assert all(x["contamination"] == expect for x in items), f"{src}污染标注漂移"


def test_nli_label_mapping():
    """NLI三分类→二元映射: contradiction才报警, entail/neutral不报警."""
    xnli = _load("xnli_zh")
    by_raw = Counter((x["label_raw"], x["label"]) for x in xnli)
    assert by_raw[("contradiction", "inconsistent")] == 1670
    assert by_raw[("entailment", "consistent")] == 1670
    assert by_raw[("neutral", "consistent")] == 1670
    # 无第三种组合
    assert len(by_raw) == 3


def test_gjb_gold_pairing():
    """金标23条: premise/hypothesis与verbalized资产逐条一致."""
    raw = json.loads((BASE / "data/gjb_438c/gold_verbalized_23.json").read_text(encoding="utf-8"))
    gold = _load("gjb_gold")
    assert len(gold) == len(raw) == 23
    for g, r in zip(gold, raw):
        assert g["premise"] == r["premise"] and g["hypothesis"] == r["hypothesis"]
        assert (g["label"] == "inconsistent") == (r["label"] == 1)
