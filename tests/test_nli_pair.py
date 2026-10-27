"""NLI pair检测内核测试: 声明编译/对齐/模板渲染/降级路径(全确定性, 无GPU依赖).

锁定内容(论文数字关联):
  - align_score截断子序列规则(0.92) vs 兄弟连续包含(0.9)
  - 父实体→图节点一对一冲突消解(半结构化/结构化歧义案例)
  - 1_001真实pair: 4条enum声明(表/图成员一致) + 1条text声明
  - 闭世界/裸枚举模板渲染
  - NliLocal不可用降级(neutral, 不加载模型)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.consistency.nli_local import NliLocal, normalize_label
from algorithms.consistency.nli_pair_claims import (
    align_score,
    assign_parents_to_nodes,
    build_claim_pairs,
    load_pair_claims,
    render_enum,
    render_flat,
    split_sentences,
)

BASE = Path(__file__).resolve().parents[1]
PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"

HAS_DATA = (PAIR_ROOT / "sc1_usecase_capability" / "1_001"
            / "table.csv").exists()


# ── 对齐分数 ──────────────────────────────────────────────

def test_align_score_truncation_vs_sibling():
    # 截断节点(缺中间'结'): 离散子序列 → 0.92
    assert align_score("半结构化数据归集", "半构化数据归集") == 0.92
    # 兄弟名(连续包含): text_match_score的0.9
    assert align_score("半结构化数据归集", "结构化数据归集") == 0.9
    # 无关: 低分
    assert align_score("半结构化数据归集", "流式数据源管理") < 0.5


def test_assign_parents_resolves_sibling_conflict():
    parents = ["半结构化数据归集", "结构化数据归集"]
    nodes = ["结构化数据归集", "半构化数据归集", "半结构化数据上传"]
    assignment = assign_parents_to_nodes(parents, nodes)
    # 精确者得全名节点; 截断节点归离散子序列对齐者
    assert assignment["结构化数据归集"] == "结构化数据归集"
    assert assignment["半结构化数据归集"] == "半构化数据归集"


# ── 模板渲染 ──────────────────────────────────────────────

def test_render_enum_closed_and_plain():
    closed = render_enum("table", "X", ["A", "B"], "closed", "能力表")
    assert "共2项" in closed
    assert "除此之外没有其他子功能" in closed
    plain = render_enum("table", "X", ["A", "B"], "plain", "能力表")
    assert "除此之外" not in plain
    graph = render_enum("graph", "X", ["A"], "closed")
    assert "直接相连的节点共1个" in graph
    assert "没有其他节点" in graph


def test_render_flat():
    s = render_flat("接口表", ["与X交互接口"], "closed")
    assert s.startswith("接口表规定，本表共包含1项条目")
    assert s.endswith("除此之外没有其他条目。")


def test_split_sentences():
    text = "系统支持结构化数据的归集操作。系统支持半结构化数据上传；系统提供非结构化数据导入功能"
    assert len(split_sentences(text)) == 3
    assert split_sentences("短") == []


# ── NliLocal: 标签归一化 + 不可用降级 ─────────────────────

def test_normalize_label():
    assert normalize_label("ENTAILMENT") == "entailment"
    assert normalize_label("contradiction") == "contradiction"
    assert normalize_label("蕴含") == "entailment"
    assert normalize_label("矛盾") == "contradiction"
    assert normalize_label("NEUTRAL") == "neutral"
    assert normalize_label("无关") == "neutral"


def test_nli_local_unknown_model_raises():
    with pytest.raises(ValueError):
        NliLocal("nonexistent-model")


def test_nli_local_unavailable_degrades_to_neutral():
    nli = NliLocal("mdeberta")
    nli.model_dir = Path("Z:/nonexistent") / "model"
    out = nli.predict([("前提", "假设"), ("", "")])
    assert all(v["label"] == "neutral" for v in out)
    assert out[0]["p_contra"] == 0.0
    bd = nli.predict_bidirectional([("前提", "假设")])
    assert bd[0]["sym_contra"] is False
    assert nli.mode == "unavailable"


# ── 真实pair快照 ──────────────────────────────────────────

@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_claims_on_benign_pair_1_001():
    pid, claims = load_pair_claims(PAIR_ROOT / "sc1_usecase_capability" / "1_001")
    assert pid == "1_001"
    assert len(claims) == 5
    enums = [c for c in claims if c.why == "enum"]
    texts = [c for c in claims if c.why == "text"]
    assert len(enums) == 4 and len(texts) == 1
    # 4个父实体(归集类型)全部对齐, 每组表侧2成员
    parents = sorted(c.entity for c in enums)
    assert parents == ["半结构化数据归集", "流式数据归集",
                       "结构化数据归集", "非结构化数据归集"]
    for c in enums:
        assert len(c.meta["table_members"]) == 2
        # benign pair: 图侧成员=表侧成员(规范化后同集合)
        from algorithms.blackboard.lexical_kit import normalize_text
        assert (sorted(normalize_text(m) for m in c.meta["table_members"])
                == sorted(normalize_text(m) for m in c.meta["graph_members"]))
        assert c.template == "closed"


@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_claims_on_flowchart_pair_2_001():
    pid, claims = load_pair_claims(PAIR_ROOT / "sc2_flowchart_usecase" / "2_001")
    assert pid == "2_001"
    whys = [c.why for c in claims]
    # sc2: 用例名不匹配流程图节点 → aggregate兜底; 无enum
    assert "aggregate" in whys and "enum" not in whys
    agg = next(c for c in claims if c.why == "aggregate")
    assert "用例描述表规定" in agg.premise
    assert "本图共包含" in agg.hypothesis


@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_sc8_excluded(tmp_path: Path):
    d = tmp_path / "sc8_pure_image" / "9_001"
    d.mkdir(parents=True)
    (d / "meta.json").write_text("{}", encoding="utf-8")
    pid, claims = load_pair_claims(d)
    assert pid == "9_001" and claims == []


@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_template_ablation_changes_claims():
    d = PAIR_ROOT / "sc1_usecase_capability" / "1_001"
    _, closed = load_pair_claims(d, template="closed")
    _, plain = load_pair_claims(d, template="plain")
    assert len(closed) == len(plain)
    assert all("除此之外" in c.hypothesis for c in closed)
    assert all("除此之外" not in c.hypothesis for c in plain)


@pytest.mark.skipif(not HAS_DATA, reason="真实pair_dataset缺失")
def test_build_claim_pairs_deterministic():
    d = PAIR_ROOT / "sc1_usecase_capability" / "1_001"
    import json
    anchor = json.loads((d / "visio_anchor.json").read_text(encoding="utf-8"))
    a = build_claim_pairs("sc1_usecase_capability", d / "table.csv",
                          (d / "text.txt").read_text(encoding="utf-8"), anchor)
    b = build_claim_pairs("sc1_usecase_capability", d / "table.csv",
                          (d / "text.txt").read_text(encoding="utf-8"), anchor)
    assert [(c.why, c.premise, c.hypothesis) for c in a] == \
           [(c.why, c.premise, c.hypothesis) for c in b]
