"""S1模板-槽位枚举合成数据回归: 结构/对称性/防泄漏/规模快照锁定.

数据: data/gjb_438c/synth_s1_pairs.json (tools/synth_s1_enumeration.py, 确定性可复现)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

DATA = BASE / "data/gjb_438c/synth_s1_pairs.json"

pytestmark = pytest.mark.skipif(not DATA.exists(), reason="S1合成数据未生成(先跑 tools/synth_s1_enumeration.py)")

TRAIN_DOCS = {"01", "02", "05", "06", "08", "09", "10", "11", "12", "13", "14", "15", "16"}
KNOWN_TYPES = {"PARAM-01", "PARAM-02", "PARAM-03", "TERM-01", "TERM-02",
               "ENUM-01", "ENUM-02"}
KNOWN_SURFACES = {"T1", "T2", "T3"}
KNOWN_LABELS = {"inconsistent", "consistent"}
# 快照锁定(论文计数): 有意重生成后需同步更新
SNAPSHOT = {"total": 5418, "inconsistent": 2709, "consistent": 2709,
            "numeric_constraints": 468, "enum_lists": 259, "name_id_pairs": 257}


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_schema_and_fields(payload: dict) -> None:
    assert payload["meta"]["method"] == "S1_enumeration"
    assert payload["meta"]["total"] == len(payload["pairs"])
    required = {"id", "premise", "hypothesis", "label", "type", "surface",
                "doc", "section", "operator", "source_constraint"}
    for e in payload["pairs"]:
        assert required <= set(e)
        assert e["label"] in KNOWN_LABELS
        assert e["type"] in KNOWN_TYPES
        assert e["surface"] in KNOWN_SURFACES
        assert e["premise"] and e["hypothesis"] and e["doc"]


def test_no_degenerate_or_duplicate_pairs(payload: dict) -> None:
    seen: set[tuple[str, str]] = set()
    labels_by_text: dict[tuple[str, str], str] = {}
    for e in payload["pairs"]:
        assert e["premise"] != e["hypothesis"], f"退化对P==H: {e['id']}"
        key = (e["premise"], e["hypothesis"])
        assert key not in labels_by_text or labels_by_text[key] == e["label"], (
            f"同文本对出现冲突标签: {e['id']}")
        labels_by_text[key] = e["label"]
        seen.add((key, e["label"]))
    assert len(seen) == len(payload["pairs"])


def test_symmetric_construction(payload: dict) -> None:
    labs = Counter(e["label"] for e in payload["pairs"])
    assert labs["inconsistent"] == labs["consistent"] == SNAPSHOT["inconsistent"]
    # 表面严格三等分(每概念对恰编译T1/T2/T3)
    surfs = Counter(e["surface"] for e in payload["pairs"])
    assert set(surfs) == KNOWN_SURFACES
    assert len(set(surfs.values())) == 1 and surfs["T1"] * 3 == len(payload["pairs"])


def test_no_leakage_from_excluded_docs(payload: dict) -> None:
    docs = {e["doc"][:2] for e in payload["pairs"]}
    assert docs <= TRAIN_DOCS, f"泄漏文档: {docs - TRAIN_DOCS}"
    assert payload["meta"]["excluded_docs"] == ["03", "04", "07"]


def test_snapshot_counts(payload: dict) -> None:
    m = payload["meta"]
    assert m["total"] == SNAPSHOT["total"]
    assert m["label_balance"]["inconsistent"] == SNAPSHOT["inconsistent"]
    assert m["label_balance"]["consistent"] == SNAPSHOT["consistent"]
    ext = m["extraction"]
    assert ext["numeric_constraints"] == SNAPSHOT["numeric_constraints"]
    assert ext["enum_lists"] == SNAPSHOT["enum_lists"]
    assert ext["name_id_pairs"] == SNAPSHOT["name_id_pairs"]
    assert m["total"] >= 1500


def test_label_operator_agreement(payload: dict) -> None:
    """构造真值一致性: 标签↔类型↔算子严格对应(领域等价约定域约定)."""
    lab_of_type = {"PARAM-01": "inconsistent", "TERM-01": "inconsistent",
                   "ENUM-01": "inconsistent", "PARAM-02": "consistent",
                   "PARAM-03": "consistent", "TERM-02": "consistent",
                   "ENUM-02": "consistent"}
    op_of_type = {"PARAM-01": "param_shift", "PARAM-02": "unit_equiv",
                  "PARAM-03": "op_reword", "TERM-01": "term_swap",
                  "TERM-02": "term_same", "ENUM-01": "enum_swap",
                  "ENUM-02": "enum_same"}
    for e in payload["pairs"]:
        assert e["label"] == lab_of_type[e["type"]], f"标签-类型错配: {e['id']}"
        assert e["operator"] == op_of_type[e["type"]], f"类型-算子错配: {e['id']}"
