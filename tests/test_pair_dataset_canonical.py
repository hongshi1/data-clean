"""统一Pair Dataset规范校验: schema+形态+模板受控性(论文数据集方案锁定).

规范: docs/srs_project/pair_dataset_spec.md
重建: python tools/build_pair_dataset_canonical.py (确定性)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

PD = BASE / "data/gjb_438c/pair_dataset_canonical"

pytestmark = pytest.mark.skipif(not PD.exists(), reason="pair_dataset_c已归档")

REQUIRED = {"id", "source", "pair", "label", "angle", "provenance", "split", "quality"}
OPTIONAL = {"context"}  # 锚点/pair变异项携带多模态上下文
ANGLES = {"scene", "modality", "type"}
PROV = {"doc", "origin", "surface", "protocol"}


def _load(split: str) -> list[dict]:
    p = PD / f"{split}.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]


def test_schema_uniform_all_sources():
    """全源同一形态: 字段集/角度键/溯源键完全一致."""
    for split in ("train", "dev", "test"):
        items = _load(split)
        if not items:
            continue
        for x in items:
            assert set(x) - OPTIONAL == REQUIRED, f"{split}/{x['id']}字段漂移"
            assert set(x["angle"]) == ANGLES
            assert set(x["provenance"]) == PROV
            assert x["label"] in ("inconsistent", "consistent")
            assert x["pair"]["premise"] and x["pair"]["hypothesis"]
            assert x["source"] in ("srs_anchor", "srs_mutation", "srs_pair_mutation", "nli_external", "nli_anli", "paws_external")
            assert x["provenance"]["surface"] in ("T1", "T2", "T3")


def test_surface_templates_controlled():
    """表面模板受控: 锚点源的T1/T2/T3三变体存在且成组(同origin)."""
    train = _load("train")
    anchors = [x for x in train if x["source"] == "srs_anchor"]
    surfs = Counter(x["provenance"]["surface"] for x in anchors)
    assert set(surfs) == {"T1", "T2", "T3"}, f"模板变体缺失: {surfs}"
    # T1/T2同源成对(同origin不同模板)
    by_origin = Counter(x["provenance"]["origin"] for x in anchors)
    paired = sum(1 for o, n in by_origin.items() if n >= 2)
    assert paired > len(by_origin) * 0.5, "表面变体未按origin成组"


def test_split_isolation():
    """划分隔离: train与test零文本重叠(同内容不同模板的CF除外按组隔离)."""
    train = _load("train")
    test = _load("test")
    train_origins = {x["provenance"]["origin"] for x in train if x["source"] != "nli_external"}
    test_origins = {x["provenance"]["origin"] for x in test if x["source"] != "nli_external"}
    overlap = train_origins & test_origins
    assert not overlap, f"origin泄漏: {list(overlap)[:5]}"
    train_text = {(x["pair"]["premise"], x["pair"]["hypothesis"]) for x in train}
    test_text = {(x["pair"]["premise"], x["pair"]["hypothesis"]) for x in test}
    assert not (train_text & test_text), "文本级泄漏"


def test_snapshot_scale():
    """论文数字锁定: 规模与构成快照."""
    index = json.loads((PD / "INDEX.json").read_text(encoding="utf-8"))
    assert index["total"] == 22402
    assert index["splits"]["train"]["n"] == 2813
    assert index["splits"]["test"]["n"] == 19589
    assert index["splits"]["train"]["sources"]["srs_anchor"] == 1216
    # 外部转换协议: 3类全映射
    test = _load("test")
    ext = [x for x in test if x["source"] == "nli_external"]
    types = Counter(x["angle"]["type"] for x in ext)
    assert set(types) >= {"NLI-CONTR", "NLI-ENTAI", "NLI-NEUTR"}


def test_id_unique():
    all_ids = [x["id"] for s in ("train", "dev", "test") for x in _load(s)]
    assert len(all_ids) == len(set(all_ids)), "id重复"


def test_no_degenerate_pairs():
    """防退化: P==H且标inconsistent的对不存在(教坏模型); 外部NLI恒等蕴含(P==H, consistent)合法."""
    n = 0
    for s in ("train", "dev", "test"):
        for x in _load(s):
            if x["pair"]["premise"] == x["pair"]["hypothesis"] and x["label"] == "inconsistent":
                n += 1
    assert n == 0, f"{n}条退化对(P==H却标inconsistent)"


def test_relation_aware_templates():
    """关系感知: 缺失类的H必须表达否定/缺失语义."""
    train = _load("train")
    missing = [x for x in train if x["source"] == "srs_anchor"
               and "MISSING" in x["angle"]["type"]]
    assert missing, "缺失类样本缺失"
    neg_marks = ("没有", "未体现", "未出现")
    ok = sum(1 for x in missing if any(m in x["pair"]["hypothesis"] for m in neg_marks))
    assert ok == len(missing), f"{len(missing) - ok}条缺失类H未表达缺失语义"


def test_quality_flags_preserved():
    """质量标记继承: 锚点项保留协议信息."""
    train = _load("train")
    protos = Counter(x["provenance"]["protocol"] for x in train if x["source"] == "srs_anchor")
    assert "cot-1" in protos
    assert "dual-llm" in protos or "cot" in protos
