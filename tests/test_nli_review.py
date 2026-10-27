"""分歧驱动NLI复核器测试: 分歧→声明构造(全确定性, 无GPU依赖).

锁定内容(论文数字关联):
  - 实体提取(table_side优先/evidence「X」fallback)
  - 1_001_00真实分歧的声明构造(误报复核案例: H节点列表含该实体)
  - dtype路由(ACTOR/STEP/EXC/ORDER)
  - 全量664条分歧的构造率97.7%
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from algorithms.consistency.nli_discrepancy_review import (
    PairContext,
    build_claims_for_discrepancy,
    build_review_claim,
    extract_entity,
)

BASE = Path(__file__).resolve().parents[1]
PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
HAS_DATA = (PAIR_ROOT / "sc1_usecase_capability" / "1_001"
            / "table.csv").exists()


def test_extract_entity_priority():
    # table_side.text优先
    d = {"table_side": {"text": "结构化数据归集"}, "evidence": "表格项「X」无匹配"}
    assert extract_entity(d) == "结构化数据归集"
    # 无table_side时从evidence提取
    d = {"evidence": "表格项「半结构化数据源引接」在图中无匹配"}
    assert extract_entity(d) == "半结构化数据源引接"
    # 都没有 → 空
    assert extract_entity({"evidence": "图中3个节点无对应"}) == ""


def test_build_review_claim_actor(tmp_path: Path):
    disc = {"dtype": "ACTOR_MISSING", "evidence": "表格Actor「开发人员」在图中无参与者节点"}
    claim = build_review_claim("sc2_flowchart_usecase", tmp_path / "x.csv",
                               None, disc)
    assert claim is None  # anchor=None → nodes空 → 诚实排除
    anchor = {"nodes": [{"id": "1", "text": "开始"}, {"id": "2", "text": "用户登录"}],
              "edges": []}
    claim = build_review_claim("sc2_flowchart_usecase", tmp_path / "x.csv",
                               anchor, disc)
    assert claim is not None
    assert "参与者(Actor)包括：「开发人员」" in claim.premise
    assert "本图共包含" in claim.hypothesis
    # 停用词节点被滤除
    assert "开始" not in claim.hypothesis


def test_build_review_claim_order():
    disc = {"dtype": "ORDER_CONFLICT", "evidence": "表格步骤3在4之前, 但图中边方向相反",
            "diag_side": {"edge": "s4→s3"}}
    claim = build_review_claim("sc2_flowchart_usecase", Path("x.csv"),
                               None, disc)
    assert claim is not None
    assert "步骤顺序为" in claim.premise
    assert "s4→s3" in claim.hypothesis


@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_review_claim_on_real_compiler_bug_case():
    """1_001_00: Tier1词法误报复核案例(图中实际存在该实体)."""
    sa = json.loads((BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json")
                    .read_text(encoding="utf-8"))
    disc = sa["1_001_00"]
    assert disc["dtype"] == "TABLE_ITEM_MISSING"
    ctx = PairContext(PAIR_ROOT)
    scene, claim = build_claims_for_discrepancy(PAIR_ROOT, "1_001", disc, ctx)
    assert scene == "sc1_usecase_capability"
    assert claim is not None
    # P: 实体是「半结构化数据归集」的子功能
    assert "「半结构化数据源引接」是「半结构化数据归集」的子功能" in claim.premise
    # H: 图节点闭世界列表包含该实体(完整文本) — 误报复核的证据
    assert "半结构化数据源引接" in claim.hypothesis
    assert "13个节点" in claim.hypothesis
    assert claim.why == "review_missing"


@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_construction_rate_full():
    """664条分歧构造率快照: ≥97% (当前649/664)."""
    final = json.loads((BASE / "data/gjb_438c/anchor_v2/final_adjudication.json")
                       .read_text(encoding="utf-8"))["final_labels"]
    sa = json.loads((BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json")
                    .read_text(encoding="utf-8"))
    la = json.loads((BASE / "data/gjb_438c/anchor_sc2/llm_adjudication.json")
                    .read_text(encoding="utf-8"))
    src = {**sa, **la}
    ctx = PairContext(PAIR_ROOT)
    n_ok = 0
    n_total = 0
    for key in final:
        disc = src.get(key)
        if disc is None:
            continue
        n_total += 1
        _, claim = build_claims_for_discrepancy(PAIR_ROOT, disc["pair"],
                                                disc, ctx)
        n_ok += claim is not None
    assert n_total == 664
    assert n_ok == 649


@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_pair_context_cache():
    ctx = PairContext(PAIR_ROOT)
    entry = ctx.get("1_001")
    assert entry is not None
    assert entry[0].parent.name == "1_001"
    assert entry[0].parent.parent.name == "sc1_usecase_capability"
    assert ctx.get("1_001") is entry  # 缓存命中
    assert ctx.get("9_zzz") is None   # 不存在pair → None
