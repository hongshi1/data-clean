"""K1/K2真实组件回归锁: EntityLexer(领域词典NER) + templates(声明模板库).

K1: knowledge/entity_lexicon.json(GLM挖掘118实体+120别名, 冻结资产)
K2: algorithms/consistency/templates.py(7模板+算子族+单位族, 单一事实源)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_entity_lexicon_frozen() -> None:
    """词典资产冻结: 规模与关键条目."""
    import json
    base = Path(__file__).resolve().parent.parent
    lex = json.loads((base / "knowledge/entity_lexicon.json").read_text(encoding="utf-8"))
    ents = lex["entities"]
    assert 100 <= len(ents) <= 150  # 清洗后118
    canon = {e["canonical"] for e in ents}
    assert "内存容量" in canon  # 关键参数实体
    mem = next(e for e in ents if e["canonical"] == "内存容量")
    assert "缓存大小" in mem["aliases"]  # 关键同指别名


def test_lexer_normalize_and_align() -> None:
    from algorithms.consistency.entities import get_lexer
    lx = get_lexer()
    # 别名归一(中英)
    assert lx.normalize("缓存大小") == "内存容量"
    assert lx.normalize("RAM") == "内存容量"
    assert lx.normalize("未收录术语XYZ") == "未收录术语XYZ"  # 未知原样返回
    # 对齐
    assert lx.align("内存容量", "缓存大小") is True
    assert lx.align("可用空间", "可用空间") is True
    assert lx.align("响应时间", "吞吐率") is False


def test_lexer_recognize() -> None:
    from algorithms.consistency.entities import get_lexer
    lx = get_lexer()
    ents = lx.recognize("系统可用空间不少于200G, 内存容量不低于1024MB, 局域网接口")
    canons = {e["canonical"] for e in ents}
    assert "内存容量" in canons
    assert "局域网" in canons


def test_term_channel_k1_lexicon() -> None:
    """K1词典→TERM-01: 同实体异名的数值声明(内存容量↔缓存大小)判不一致."""
    from algorithms.consistency.checker import ConsistencyChecker
    ck = ConsistencyChecker()
    r = ck.check("流媒体传输服务的规定：内存容量不小于20M。",
                 "流媒体传输服务的规定：缓存大小不小于20M。")
    assert r.verdict == "inconsistent"
    assert r.type == "TERM-01"
    assert r.solver == "term_k1_lexicon"


def test_templates_registry() -> None:
    """K2模板库: 注册表完整+解析+与checker正则严格一致."""
    from algorithms.consistency.templates import TEMPLATES, get_template, parse_claims
    from algorithms.consistency.checker import ConsistencyChecker
    names = {t.name for t in TEMPLATES}
    assert names >= {"numeric_prefix", "numeric_postfix", "quoted", "enum_list",
                     "numbered_item", "count_decl", "doc_absence"}
    # 规则溯源字段全部非空
    assert all(t.rule_ref for t in TEMPLATES)
    # 与checker行为一致(单一事实源)
    ck = ConsistencyChecker()
    assert get_template("numeric_prefix").pattern.pattern == ck.NUM_PAT_PREFIX.pattern
    assert get_template("numeric_postfix").pattern.pattern == ck.NUM_PAT_POSTFIX.pattern
    # 解析
    claims = parse_claims("功能表规定，9项条目，可用空间200G以上，包含「登录IP不超过24」")
    types = {c.claim_type for c in claims}
    assert "numeric" in types and "count" in types and "quoted" in types


def test_normalize_unit_from_templates() -> None:
    from algorithms.consistency.checker import normalize_unit
    assert normalize_unit("1", "s") == (1000.0, "time")
    assert abs(normalize_unit("204800", "MB")[0] - normalize_unit("200", "G")[0]) < 0.01
    assert normalize_unit("1000", "字/秒") == (1000.0, "字/秒")
