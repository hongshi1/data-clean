from __future__ import annotations
import pytest
pytest.importorskip("mmqa_eval", reason="mmqa_eval.py已归档")
"""MMQA数据集构建测试: 40项注入管线的确定性快照.

锁定内容(mmqa_build全量产物):
  - 1335条MutationRecord / 1318条可编译声明对(2148条claim)
  - GJB 11项×81对全覆盖 / 通道分流分布
  - split的组完整性(同pair变异同split)
  - 物化目录结构与40项ID合法性
"""

import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
MMQA = BASE / "data/gjb_438c/mmqa"

pytestmark = pytest.mark.skipif(
    not (MMQA / "mutations.jsonl").exists(), reason="mmqa数据集未构建")

FORTY = ([f"TERM-{i:02d}" for i in range(1, 9)]
         + [f"PARAM-{i:02d}" for i in range(1, 11)]
         + [f"LOGIC-{i:02d}" for i in range(1, 12)]
         + [f"GJB-{i:02d}" for i in range(1, 12)])


def _mutations() -> list[dict]:
    return [json.loads(line) for line in
            (MMQA / "mutations.jsonl").read_text(
                encoding="utf-8").strip().splitlines()]


def test_mutation_count_and_schema():
    muts = _mutations()
    assert len(muts) == 1335
    for m in muts:
        assert set(m) >= {"mutation_id", "check_item", "source_evidence",
                          "before", "after", "expected_label", "channel",
                          "single_factor", "verify_gate", "split"}
        assert m["expected_label"] == "inconsistent"
        assert m["check_item"] in FORTY, "40项外注入=违规"
        assert m["single_factor"] is True


def test_gjb_full_coverage():
    """GJB 11项×81对全覆盖(删除型注入的高证据源)."""
    muts = _mutations()
    for i in range(1, 12):
        n = sum(1 for m in muts if m["check_item"] == f"GJB-{i:02d}")
        assert n == 81, f"GJB-{i:02d}应81条, 实际{n}"


def test_channel_distribution():
    from collections import Counter
    c = Counter(m["channel"] for m in _mutations())
    assert c == {"syntax": 891, "lexical": 212, "nli-strong": 151,
                 "nli-weak": 81}


def test_split_family_integrity():
    """泄漏门禁: 同pair的全部变异必须同split."""
    pair_split: dict[str, str] = {}
    for m in _mutations():
        pid = m["source_evidence"]["pair_id"]
        if pid in pair_split:
            assert pair_split[pid] == m["split"], f"{pid}跨split泄漏"
        pair_split[pid] = m["split"]


def test_claims_compilable_snapshot():
    muts = _mutations()
    assert sum(1 for m in muts if m.get("n_claims", 0) > 0) == 1318
    assert sum(m.get("n_claims", 0) for m in muts) == 2148


def test_virtual_pairs_layout():
    """物化目录: 虚拟pair保持场景名父目录(声明编译路由依赖)."""
    root = MMQA / "virtual_pairs"
    scenes = [d.name for d in root.iterdir() if d.is_dir()]
    assert scenes, "物化目录为空"
    # 场景目录名必须是pair_dataset的场景名
    from algorithms.blackboard.evidence_store import SCENE_PREFIX
    valid = set(SCENE_PREFIX.values())
    for s in scenes:
        assert s in valid, f"非场景目录: {s}"


# ── Suite-S(声明对形态, inject_rules_v3产物)快照 ──

SUITE_S = BASE / "data/gjb_438c/data_assets/eval_injected_v3.json"


@pytest.mark.skipif(not SUITE_S.exists(), reason="Suite-S未生成")
def test_suite_s_coverage():
    """40项中32项覆盖(198条=158负例+40正例), 8项语料不支持有证据."""
    d = json.loads(SUITE_S.read_text(encoding="utf-8"))
    inj = d["injections"]
    assert len(inj) == 198
    assert sum(1 for i in inj if i["label"] == "inconsistent") == 158
    assert sum(1 for i in inj if i["label"] == "consistent") == 40
    items = {i["check_item"] for i in inj if i["label"] == "inconsistent"}
    assert len(items) == 32
    unsupported = {"PARAM-03", "PARAM-04", "PARAM-08", "PARAM-09",
                   "PARAM-10", "LOGIC-06", "LOGIC-07", "GJB-11"}
    assert unsupported & items == set()


@pytest.mark.skipif(not SUITE_S.exists(), reason="Suite-S未生成")
def test_suite_s_positive_pairs():
    """40条恒等正例的original==injected(对照)."""
    d = json.loads(SUITE_S.read_text(encoding="utf-8"))
    pos = [i for i in d["injections"] if i["label"] == "consistent"]
    assert len(pos) == 40
    for p in pos:
        a, b = p["original"], p["injected"]
        if isinstance(a, str) and isinstance(b, str):
            assert a == b


EVALSET_V2 = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"


@pytest.mark.skipif(not EVALSET_V2.exists(), reason="eval_set缺失")
def test_real_positive_assets():
    """真实多模态一致正例: eval_set的50条(双LLM验证资产)."""
    es = json.loads(EVALSET_V2.read_text(encoding="utf-8"))
    pos = [e for e in es["entries"] if e["label"] == "consistent"]
    assert len(pos) == 50
    for e in pos:
        assert e["check_item"] == "POSITIVE"
        assert (e.get("entity") or {}).get("occurrences")


@pytest.mark.skip(reason="mmqa_eval_suites.py已归档")
def test_equiv_positive_generation():
    """等效正例族(单位换算): 确定性生成与语义等价校验."""
    import sys as _sys
    _sys.path.insert(0, str(BASE / "tools"))
    from mmqa_eval_suites import _build_equiv_positives
    pos = _build_equiv_positives(seed=42, n=20)
    assert len(pos) == 20
    assert all(p["check_item"] == "POSITIVE-EQUIV" for p in pos)
    # 语义等价: 数值×因子换算后一致(0.2秒→200ms)
    a, b = pos[0]["original"], pos[0]["injected"]
    assert a != b  # 表面不同
    # 确定性: 同seed重建一致
    pos2 = _build_equiv_positives(seed=42, n=20)
    assert [p["original"] for p in pos] == [p["original"] for p in pos2]
