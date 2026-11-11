"""Contract tests for the v2 claim decomposition fix layer.

Every test pins one audit-driven fix from
algorithms/consistency/answer_claims_v2.py against the audited failure
shapes (tools/audit_claim_extraction.py: S1QA-066/069/077):
colon split, framework filter, subject inheritance, open-list enum
downgrade, typed-extraction preservation, boundary behavior.
"""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import decompose_claims  # noqa: E402
from algorithms.consistency.answer_claims_v2 import (  # noqa: E402
    decompose_claims_v2,
    fix_trigger_stats,
)

OBJECT_ACCESS_ANSWER = (
    "对象化访问功能支持以下操作：\n"
    "1. **添加**：向数据库中插入数据。\n"
    "2. **删除**：从数据库中删除已存在的数据。"
)
CACHE_FEATURE_ANSWER = (
    "热点数据缓存功能有以下特点：\n"
    "1. **查询结果缓存**：提供对查询结果的数据缓存功能，支持将数据库"
    "返回的结果集中缓存在内存中。"
)


def test_colon_split_breaks_title_description_fusion() -> None:
    """审计核心缺陷: "X：Y"题名+描述融合claim拆成两条 (S1QA-069)."""
    claims = decompose_claims_v2("对象化访问功能支持哪些操作？",
                                 OBJECT_ACCESS_ANSWER)
    texts = [claim.text for claim in claims]
    assert "添加" in texts
    assert "向数据库中插入数据" in texts
    assert "删除" in texts
    assert "从数据库中删除已存在的数据" in texts
    assert all("：" not in text for text in texts)
    assert all(claim.kind == "semantic" for claim in claims)


def test_framework_sentence_lead_in_is_filtered() -> None:
    """"有以下特点/以下操作"引导句无断言价值, 不再成为claim (S1QA-066)."""
    claims = decompose_claims_v2("对象化访问功能支持哪些操作？",
                                 OBJECT_ACCESS_ANSWER)
    texts = [claim.text for claim in claims]
    assert "对象化访问功能支持以下操作" not in texts
    cache_claims = decompose_claims_v2("热点数据缓存功能有什么特点？",
                                       CACHE_FEATURE_ANSWER)
    assert "热点数据缓存功能有以下特点" not in [
        claim.text for claim in cache_claims]
    assert cache_claims  # 过滤不能清空claim集


def test_subject_inheritance_verb_initial_description() -> None:
    """动词开头的描述claim继承题名作为attr (供subject匹配)."""
    claims = decompose_claims_v2("热点数据缓存功能有什么特点？",
                                 CACHE_FEATURE_ANSWER)
    description = next(claim for claim in claims
                       if claim.text.startswith("提供"))
    assert description.attr == "查询结果缓存"
    # 非动词开头(名词主语自足)的描述claim保留v1原attr, 不继承
    noun_subject = decompose_claims_v2(
        "获取LOB数据时连接错误如何处理？",
        "连接检查： 系统首先验证数据库连接是否正常")
    description_claim = next(claim for claim in noun_subject
                             if claim.text.startswith("系统"))
    v1 = decompose_claims("获取LOB数据时连接错误如何处理？",
                          "连接检查： 系统首先验证数据库连接是否正常")
    assert description_claim.attr == v1[0].attr


def test_open_list_enum_downgraded_to_semantic() -> None:
    """含"如"的enum是开放列表, 降级为semantic不做闭集比对 (S1QA-077)."""
    answer = "系统支持模块包括数据获取、数据处理，如定时获取和触发获取"
    v1 = decompose_claims("系统包括哪些模块？", answer)
    assert any(claim.kind == "enum" for claim in v1)
    v2 = decompose_claims_v2("系统包括哪些模块？", answer)
    assert all(claim.kind != "enum" for claim in v2)
    downgraded = [claim for claim in v2 if "如定时获取" in claim.text]
    assert [claim.kind for claim in downgraded] == ["semantic"]
    assert downgraded[0].text == v1[0].text  # 文本不动, 只降kind


def test_typed_extraction_claims_pass_through_unchanged() -> None:
    """numeric/quoted/identifier的typed提取逻辑保持不变."""
    answer = "缓存大小不大于2048MB，模块标识为ABC-123，「查询结果缓存」为核心功能"
    question = "系统响应时间要求是多少？"
    v1 = decompose_claims(question, answer)
    v2 = decompose_claims_v2(question, answer)
    assert {claim.kind for claim in v1} >= {"numeric", "quoted", "identifier"}
    assert v2 == v1  # frozen dataclass逐字段相等


def test_colon_split_boundaries() -> None:
    """题名>10字(整句)或描述<8字(残句)不拆."""
    long_title = decompose_claims_v2(
        "X？", "数据库连接异常恢复机制设计：当连接池耗尽时系统应自动重建连接")
    assert [claim.text for claim in long_title] == [
        "数据库连接异常恢复机制设计：当连接池耗尽时系统应自动重建连接"]
    short_desc = decompose_claims_v2("X？", "添加：插入数据")
    assert [claim.text for claim in short_desc] == ["添加：插入数据"]


def test_all_filtered_answer_keeps_v1_claims() -> None:
    """全过滤退化case: claim集永不为空(空集聚合成support), 回退v1."""
    v1 = decompose_claims("X？", "有以下特点")
    v2 = decompose_claims_v2("X？", "有以下特点")
    assert len(v1) == 1
    assert v2 == v1


def test_no_colon_semantic_claim_unchanged() -> None:
    """无冒号的semantic claim原样保留."""
    answer = "系统应支持数据库连接的自动重试机制"
    v1 = decompose_claims("X？", answer)
    v2 = decompose_claims_v2("X？", answer)
    assert len(v1) == 1
    assert v2 == v1


def test_fix_trigger_stats_counts_every_fix() -> None:
    """诊断计数: 冒号拆分/框架句丢弃/如降级各计一次."""
    stats = fix_trigger_stats("对象化访问功能支持哪些操作？",
                              OBJECT_ACCESS_ANSWER)
    assert stats == {"colon_splits": 2, "enum_open_list_downgrades": 0,
                     "framework_drops": 1}
    enum_stats = fix_trigger_stats(
        "系统包括哪些模块？",
        "系统支持模块包括数据获取、数据处理，如定时获取和触发获取")
    assert enum_stats == {"colon_splits": 0, "enum_open_list_downgrades": 1,
                          "framework_drops": 0}
