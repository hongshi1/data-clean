"""family_evalset_v1 冻结快照测试(论文数字保护).

锁定: 六族配额 / 标签构成 / 零重复 / 来源分布.
再生成协议: tools/build_family_evalset.py(中间依赖见脚本头注),
有意重生成后同步本快照并跑 build_data_manifest.py.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

G = Path(__file__).resolve().parent.parent / "data/gjb_438c"
DATA = json.loads((G / "family_evalset_v1.json").read_text(encoding="utf-8"))
PAIRS = DATA["pairs"]

EXPECTED_FAMILY = {"A": 150, "B": 67, "C": 293, "D": 200, "E": 36, "F": 150}
EXPECTED_TOTAL = 896
EXPECTED_LABEL = {
    "A": {"inconsistent": 75, "consistent": 75},
    "B": {"inconsistent": 67},
    "C": {"consistent": 137, "inconsistent": 156},
    "D": {"inconsistent": 100, "consistent": 100},
    "E": {"inconsistent": 36},
    "F": {"consistent": 82, "inconsistent": 68},
}


def test_total() -> None:
    assert len(PAIRS) == EXPECTED_TOTAL


def test_family_quota() -> None:
    fam = Counter(x["family"] for x in PAIRS)
    assert dict(fam) == EXPECTED_FAMILY


def test_label_composition() -> None:
    for fam, exp in EXPECTED_LABEL.items():
        got = dict(Counter(x["label"] for x in PAIRS if x["family"] == fam))
        assert got == exp, f"族{fam}: {got} != {exp}"


def test_no_duplicate() -> None:
    keys = [(x["premise"], x["hypothesis"]) for x in PAIRS]
    assert len(keys) == len(set(keys))


def test_schema_complete() -> None:
    for x in PAIRS:
        for field in ("id", "family", "type", "label", "premise", "hypothesis", "provenance"):
            assert x.get(field), f"{x['id']}缺{field}"
        assert x["label"] in ("consistent", "inconsistent")
        assert x["family"] in "ABCDEF"


def test_provenance() -> None:
    prov = Counter(x["provenance"] for x in PAIRS)
    assert prov["gold_frozen"] == 280  # 冻结金标(自然去重后)
    assert prov["gjb_bench"] == 103    # B/E族来源
