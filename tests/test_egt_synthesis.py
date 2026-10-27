"""EGT(Evidence-Grounded Tri-state)三态数据合成管线契约测试.

手工构造的frozen QA fixture覆盖: 种子收集(标识符/E1/精确语句)、
R翻转有效性(翻转后claim不再被支持语句匹配, scope锚定+锚注入)、
N删除有效性(支持语句确实消失且模块复判NIE), 以及直接构造种子的
算子级测试(数值区间翻转/枚举删元/步骤重排/不可翻越跳过)、组装均衡
与序列化往返; 语句级路径覆盖MinerU块种子提取/S保义改写/R确定性翻转
(含「在N内」隐式上界soundness守卫)/N跨块与块内删除; 最后跑真实
冻结QA前10条与04号文档前30个内容块做冒烟回归.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.egt_synthesis import (  # noqa: E402
    NARRATIVE_TEMPLATES,
    STATEMENT_QUESTION,
    SUPPORT_SEED_METHODS,
    SupportSeed,
    assemble_dataset,
    bigram_containment,
    classify_claim,
    collect_statement_seeds,
    collect_support_seeds,
    evidence_from_dict,
    evidence_to_dict,
    extract_narrative_corpus,
    mineru_block_to_evidence,
    narrative_evidence_window,
    plan_claim_flip,
    plan_statement_flip,
    sample_to_dict,
    seed_matching_statements,
    statement_evidence_window,
    synthesize_narrative_samples,
    synthesize_nie_from_statement,
    synthesize_nie_from_statements,
    synthesize_nie_samples,
    synthesize_refute_from_statement,
    synthesize_refute_from_statements,
    synthesize_refute_samples,
    synthesize_support_from_statement,
    synthesize_support_from_statements,
    synthesize_support_samples,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
DOC = "04数据统一访问服务软件需求规格说明-终稿"
FREEZE_ID = "fixture-frozen-v1"

CAP_TABLE_HTML = (
    '<table><thead><tr><th><p>序号</p></th><th><p>Usecase名称</p></th>'
    '<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th></tr></thead>'
    '<tbody>'
    '<tr><td><p>1</p></td><td><p>BLOB数据操作</p></td>'
    '<td><p>PZXQ-GN-SQLFW-BLOBSJCZ</p></td>'
    '<td><p>提供BLOB数据的插入、删除、查询操作功能</p></td></tr>'
    '<tr><td><p>2</p></td><td><p>查询数据</p></td>'
    '<td><p>PZXQ-GN-SQLFW-CXSJ</p></td>'
    '<td><p>提供数据查询功能</p></td></tr>'
    '</tbody></table>')

USECASE_TABLE_HTML = (
    '<table><tr><td><p>Use Case 名称：缓存更新</p></td>'
    '<td colspan="2"><p>Actors：应用软件</p></td></tr>'
    '<tr><td colspan="3"><p>前置条件：缓存服务正常。</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流</p></td></tr>'
    '<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>'
    '<td><p>动作约束</p></td></tr>'
    '<tr><td><p>1.应用软件调用缓存更新接口输入缓存键值；</p></td>'
    '<td><p>2．系统校验缓存条目并刷新缓存数据，'
    '校验失败则执行异常流E1；</p></td>'
    '<td><p>缓存更新应在100ms内完成。</p></td></tr>'
    '<tr><td colspan="2"><p>异常流E1：系统提示校验失败，用例结束。</p></td>'
    '<td></td></tr>'
    '<tr><td colspan="2"><p>后置条件：无。</p></td><td></td></tr></table>')

USECASE_TABLE2_HTML = (
    '<table><tr><td><p>Use Case 名称：连接管理</p></td>'
    '<td colspan="2"><p>Actors：应用软件</p></td></tr>'
    '<tr><td colspan="3"><p>前置条件：数据库连接正常。</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流</p></td></tr>'
    '<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>'
    '<td><p>动作约束</p></td></tr>'
    '<tr><td><p>1.应用软件调用连接管理接口请求连接；</p></td>'
    '<td><p>2．系统建立数据库连接并返回连接句柄，'
    '连接失败则执行异常流E1；</p></td>'
    '<td><p>无法连接到服务端时，提示连接错误。</p></td></tr>'
    '<tr><td colspan="2"><p>异常流E1：系统提示连接失败，用例结束。</p></td>'
    '<td></td></tr>'
    '<tr><td colspan="2"><p>后置条件：无。</p></td><td></td></tr></table>')

TEXT_BLOCK = "统一数据访问服务支持sqlite3数据库存储配置数据。"

NUMERIC_TEXT = ("系统应确保单个BLOB数据的大小不超过65535字节，"
                "不符合规定则提示大小超限并终止流程。")

ENUM_TEXT = "缓存替换策略分别为LRU、LFU、FIFO三种，淘汰时间最久的数据。"

STEP_TABLE_HTML = (
    '<table><tr><td><p>Use Case 名称：缓存刷新</p></td>'
    '<td colspan="2"><p>Actors：应用软件</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流</p></td></tr>'
    '<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>'
    '<td><p>动作约束</p></td></tr>'
    '<tr><td><p>1．应用软件输入缓存键值；</p></td>'
    '<td><p>2．系统校验并刷新缓存数据；</p></td>'
    '<td><p>刷新应在200ms内完成。</p></td></tr>'
    '<tr><td colspan="3"><p>后置条件：缓存已更新。</p></td></tr></table>')


def make_ev(eid: str, text: str, source_type: str = "table",
            section: str = "3.2 CSCI能力需求") -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=eid, text=text, source_type=source_type,
        source_ref=SourceRef(doc_id=DOC, section=section, page=1,
                             block_id=eid),
        scope_id=f"{DOC}:{eid}", completeness="open",
        completeness_proof="Only this source block was frozen.",
        extraction_method="fixture", extraction_confidence=1.0)


MODULE = QAConsistencyModule(use_experts=True)

E1_REQUEST = QAInput(
    instance_id="FIX-E1-001",
    question="缓存更新校验失败时系统如何处理异常情况并提示，用例如何结束",
    answer="校验失败时系统会提示校验失败，用例结束",
    context_freeze_id=FREEZE_ID,
    evidence=(make_ev("FIX-E1-ev-001", USECASE_TABLE_HTML),
              make_ev("FIX-E1-ev-002", USECASE_TABLE2_HTML)))

ID_REQUEST = QAInput(
    instance_id="FIX-ID-001",
    question="BLOB数据操作用例的项目唯一标识符是什么",
    answer="BLOB数据操作的项目唯一标识符是PZXQ-GN-SQLFW-BLOBSJCZ",
    context_freeze_id=FREEZE_ID,
    evidence=(make_ev("FIX-ID-ev-001", CAP_TABLE_HTML),
              make_ev("FIX-ID-ev-002", TEXT_BLOCK, source_type="text")))


def make_seed(instance_id: str, claim_text: str, method: str,
              evidence: tuple[RetrievedEvidence, ...],
              question: str) -> SupportSeed:
    return SupportSeed(
        instance_id=instance_id, question=question, claim_id="c01",
        claim_text=claim_text, method=method,
        raw_evidence_refs=tuple(ev.evidence_id for ev in evidence),
        evidence=evidence, context_freeze_id=FREEZE_ID)


def fixture_seeds() -> list[SupportSeed]:
    return collect_support_seeds([E1_REQUEST, ID_REQUEST], MODULE)


# ── 种子收集 ─────────────────────────────────────────────


def test_collect_support_seeds_from_fixtures() -> None:
    seeds = fixture_seeds()
    by_instance = {seed.instance_id: seed for seed in seeds}
    assert set(by_instance) == {"FIX-E1-001", "FIX-ID-001"}
    e1_seed = by_instance["FIX-E1-001"]
    assert e1_seed.method == "e1_template_match"
    assert e1_seed.method in SUPPORT_SEED_METHODS
    assert "校验失败" in e1_seed.claim_text
    assert e1_seed.raw_evidence_refs == ("FIX-E1-ev-001",)
    id_seed = by_instance["FIX-ID-001"]
    assert id_seed.method == "identifier_exact_match"
    assert id_seed.claim_text == "PZXQ-GN-SQLFW-BLOBSJCZ"
    assert id_seed.raw_evidence_refs == ("FIX-ID-ev-001",)


def test_collect_support_seeds_filters_methods_and_verdicts() -> None:
    request = QAInput(
        instance_id="FIX-NEG-001",
        question="系统运行形态包括哪些",
        answer="系统支持 在桌面版和舰版 部署形态下运行",
        context_freeze_id=FREEZE_ID,
        evidence=(make_ev("FIX-NEG-ev-001", TEXT_BLOCK, source_type="text"),))
    seeds = collect_support_seeds([request], MODULE)
    assert seeds == []


# ── R翻转 ────────────────────────────────────────────────


def test_refute_e1_prompt_swap_breaks_match() -> None:
    result = synthesize_refute_samples(fixture_seeds(), module=MODULE)
    e1_samples = [s for s in result.samples
                  if s.operator == "e1_prompt_swap"]
    assert len(e1_samples) == 1
    sample = e1_samples[0]
    assert sample.label == "refute"
    assert sample.claim_text.startswith("在「缓存更新」用例中，")
    assert "校验失败时系统会提示连接失败" in sample.claim_text
    assert all(passed for _, passed in sample.self_check)
    assert sample.module_verdict == "refute"
    seed = next(s for s in fixture_seeds()
                if s.seed_id == sample.seed_id)
    matched_text = "；".join(s.text for s in seed_matching_statements(seed))
    assert "连接失败" not in matched_text
    assert bigram_containment(sample.claim_text, matched_text) \
        < bigram_containment(seed.claim_text, matched_text)


def test_refute_identifier_sibling_swap_is_module_refute() -> None:
    result = synthesize_refute_samples(fixture_seeds(), module=MODULE)
    id_samples = [s for s in result.samples if s.operator == "id_sibling_swap"]
    assert len(id_samples) == 1
    sample = id_samples[0]
    assert sample.label == "refute"
    assert sample.claim_text == "BLOB数据操作的项目唯一标识符：PZXQ-GN-SQLFW-CXSJ"
    assert sample.module_verdict == "refute"
    assert sample.overlap_after < sample.overlap_before


def test_refute_numeric_operator_flip_disjoint_interval() -> None:
    evidence = (make_ev("FIX-NUM-ev-001", NUMERIC_TEXT, source_type="text"),)
    seed = make_seed("FIX-NUM-001", "单个BLOB数据的大小不超过65535字节",
                     "exact_statement", evidence,
                     "单个BLOB数据的大小上限是多少字节")
    result = synthesize_refute_samples([seed], module=MODULE)
    assert len(result.samples) == 1
    sample = result.samples[0]
    assert sample.operator == "numeric_operator_flip"
    assert sample.label == "refute"
    assert "大于65535字节" in sample.claim_text
    assert "不超过65535字节" not in sample.claim_text
    assert sample.module_verdict == "refute"
    assert all(passed for _, passed in sample.self_check)
    assert sample.overlap_after < sample.overlap_before


def test_refute_enum_member_delete_misreports_closed_list() -> None:
    evidence = (make_ev("FIX-ENUM-ev-001", ENUM_TEXT, source_type="text"),)
    claim = "缓存替换策略分别为LRU、LFU、FIFO三种"
    seed = make_seed("FIX-ENUM-001", claim, "exact_statement", evidence,
                     "缓存替换策略分别为哪几种")
    assert classify_claim(claim) == "enum"
    matched = seed_matching_statements(seed)
    matched_text = "；".join(s.text for s in matched)
    plan = plan_claim_flip(seed, matched_text, matched)
    assert plan is not None
    assert plan.operator == "enum_member_delete"
    assert plan.flipped == "缓存替换策略分别为LRU、LFU"
    assert "FIFO" not in plan.flipped
    # 模块枚举通道是子集宽容(成员全命中即support), 删元弱化claim被复判
    # support → 模块门控拒绝(防被蕴含的refute样本), 该尝试计入module_gate
    result = synthesize_refute_samples([seed], module=MODULE)
    assert result.samples == []
    assert result.stats["attempts_by_operator"].get(
        "enum_member_delete") == 1
    assert result.stats["skipped_module_gate"] == 1


def test_refute_step_order_swap_reverses_steps() -> None:
    evidence = (make_ev("FIX-STEP-ev-001", STEP_TABLE_HTML),)
    claim = "1．应用软件输入缓存键值。2．系统校验并刷新缓存数据。"
    seed = make_seed("FIX-STEP-001", claim, "sequence_alignment", evidence,
                     "描述缓存刷新的主事件流步骤")
    result = synthesize_refute_samples([seed], module=MODULE)
    assert len(result.samples) == 1
    sample = result.samples[0]
    assert sample.operator == "step_order_swap"
    assert sample.claim_text == \
        "1．系统校验并刷新缓存数据。2．应用软件输入缓存键值。"


def test_refute_unflippable_seed_is_skipped() -> None:
    evidence = (make_ev("FIX-PLAIN-ev-001", TEXT_BLOCK, source_type="text"),)
    seed = make_seed("FIX-PLAIN-001",
                     "统一数据访问服务支持sqlite3数据库存储配置数据",
                     "exact_statement", evidence, "系统支持什么数据库")
    result = synthesize_refute_samples([seed], module=MODULE)
    assert result.samples == []
    assert result.stats["skipped_no_flippable_structure"] == 1


# ── N删除 ────────────────────────────────────────────────


def test_nie_span_deletion_removes_support_statement() -> None:
    seeds = fixture_seeds()
    result = synthesize_nie_samples(seeds, module=MODULE)
    span_samples = [s for s in result.samples
                    if s.operator == "evidence_span_deletion"]
    assert len(span_samples) == 1
    sample = span_samples[0]
    assert sample.label == "not_in_evidence"
    assert sample.claim_text == next(
        s for s in seeds if s.instance_id == "FIX-E1-001").claim_text
    assert len(sample.evidence) == len(E1_REQUEST.evidence)
    modified_table = sample.evidence[0].text
    assert "异常流E1：系统提示校验失败" not in modified_table
    assert "Use Case 名称：缓存更新" in modified_table
    assert sample.module_verdict == "not_in_evidence"
    assert all(passed for _, passed in sample.self_check)
    assert sample.overlap_after < sample.overlap_before


def test_nie_block_deletion_keeps_non_support_block() -> None:
    seeds = fixture_seeds()
    result = synthesize_nie_samples(seeds, module=MODULE)
    block_samples = [s for s in result.samples
                     if s.operator == "evidence_block_deletion"
                     and s.seed_id.startswith("FIX-ID-001")]
    assert len(block_samples) == 1
    sample = block_samples[0]
    assert sample.label == "not_in_evidence"
    assert len(sample.evidence) == 1
    assert sample.evidence[0].evidence_id == "FIX-ID-ev-002"
    assert all("PZXQ-GN-SQLFW-BLOBSJCZ" not in ev.text
               for ev in sample.evidence)
    assert sample.module_verdict == "not_in_evidence"


def test_nie_cross_instance_uses_peer_evidence() -> None:
    seeds = fixture_seeds()
    peers = {"FIX-E1-001": E1_REQUEST.evidence,
             "FIX-ID-001": ID_REQUEST.evidence}
    result = synthesize_nie_samples(seeds, module=MODULE,
                                     peer_evidence=peers)
    cross = [s for s in result.samples
             if s.operator == "cross_instance_evidence_swap"]
    assert len(cross) == 2
    for sample in cross:
        assert sample.label == "not_in_evidence"
        assert sample.module_verdict == "not_in_evidence"
        assert sample.evidence in (E1_REQUEST.evidence, ID_REQUEST.evidence)
        assert len(sample.evidence) >= 1
    id_cross = next(s for s in cross
                    if s.seed_id.startswith("FIX-ID-001"))
    assert all("PZXQ-GN-SQLFW-BLOBSJCZ" not in ev.text
               for ev in id_cross.evidence)


# ── S样本 ────────────────────────────────────────────────


def test_support_samples_passthrough_and_multi_claim() -> None:
    evidence = (make_ev(
        "FIX-S-ev-001",
        "统一数据访问服务提供数据缓存功能。缓存数据应在本地磁盘中加密保存。",
        source_type="text"),)
    request = QAInput(
        instance_id="FIX-S-001",
        question="统一数据访问服务提供什么功能，缓存数据如何保存",
        answer="统一数据访问服务提供数据缓存功能。缓存数据应在本地磁盘中加密保存。",
        context_freeze_id=FREEZE_ID, evidence=evidence)
    seeds = collect_support_seeds([request], MODULE)
    assert len(seeds) >= 2
    assert all(seed.method == "exact_statement" for seed in seeds)
    result = synthesize_support_samples(seeds)
    passthrough = [s for s in result.samples
                   if s.operator == "seed_passthrough"]
    merged = [s for s in result.samples
              if s.operator == "multi_claim_merge"]
    assert len(passthrough) == len(seeds)
    assert len(merged) == 1
    assert merged[0].label == "support"
    assert merged[0].claim_kind == "multi"
    assert merged[0].claim_text.count("；") == len(seeds) - 1


# ── 语句级种子提取(16文档扩规模) ──────────────────────────

STMT_TEXT_BLOCK = {
    "type": "text",
    "text": "数据统一访问服务提供数据缓存功能。每个BLOB数据的大小应"
            "不大于65535字节，不符合规定则提示大小超限并终止流程。",
    "page_idx": 10,
}
STMT_TABLE_BLOCK = {
    "type": "table",
    "table_body": USECASE_TABLE_HTML,
    "table_caption": ["表6 读取配置文件连接用例"],
    "page_idx": 11,
}
STMT_TEXT_BLOCK2 = {"type": "text", "text": TEXT_BLOCK, "page_idx": 12}
STMT_LIST_BLOCK = {
    "type": "list",
    "list_items": ["1. 本文档已被批准的标识号：AZ6932.2.15 SRS；",
                   "2. 本文档的版本号为V1.00。"],
    "page_idx": 13,
}
STMT_BLOCKS = [
    STMT_TEXT_BLOCK,
    STMT_TABLE_BLOCK,
    STMT_TEXT_BLOCK2,
    {"type": "image", "img_path": "images/x.jpg", "page_idx": 12},
    STMT_LIST_BLOCK,
]


def test_collect_statement_seeds_from_mineru_blocks() -> None:
    seeds = collect_statement_seeds(STMT_BLOCKS, DOC)
    by_sid = {seed.statement_id: seed for seed in seeds}
    # text块: 无标记句不入种子但占删除序号(与_delete_sentences对齐)
    assert "b000#s0" not in by_sid
    text_seed = by_sid["b000#s1"]
    assert text_seed.statement_text.startswith("每个BLOB数据的大小")
    assert text_seed.block_type == "text"
    assert text_seed.delete_mode == "sentence"
    assert text_seed.delete_index == 2
    assert text_seed.scope_key == ""
    assert text_seed.seed_id == f"{DOC}:b000#s1"
    # table块: 线性化语句带scope与行级删除索引
    e1_seeds = [s for s in seeds if s.field_name.startswith("异常流")]
    assert len(e1_seeds) == 1
    e1_seed = e1_seeds[0]
    assert e1_seed.block_type == "table"
    assert e1_seed.scope_key == "缓存更新"
    assert e1_seed.statement_text == "异常流E1：系统提示校验失败，用例结束。"
    assert e1_seed.delete_mode == "row"
    assert e1_seed.is_e1_statement()
    # 动作约束语句(数值结构)也入种子
    constraint = next(s for s in seeds if "动作约束" in s.field_name)
    assert "100ms" in constraint.statement_text
    assert constraint.scope_key == "缓存更新"
    # list块: 含数字标记的条目入选
    assert "b004#i0" in by_sid
    assert by_sid["b004#i0"].block_type == "list"
    assert by_sid["b004#i0"].delete_mode == "list_item"
    # image块不产生种子
    assert all(seed.block_type in ("text", "table", "list") for seed in seeds)


def test_statement_evidence_window_and_block_evidence() -> None:
    seeds = collect_statement_seeds(STMT_BLOCKS, DOC)
    e1_seed = next(s for s in seeds if s.field_name.startswith("异常流"))
    window = statement_evidence_window(e1_seed, STMT_BLOCKS)
    assert 3 <= len(window) <= 6
    ids = [ev.evidence_id for ev in window]
    assert f"{DOC}#b001" in ids
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
    for ev in window:
        assert ev.source_ref.doc_id == DOC
        assert ev.completeness == "open"
        assert ev.extraction_method == "mineru_content_list"
    evidence = mineru_block_to_evidence(DOC, 4, STMT_LIST_BLOCK)
    assert evidence.text == "；".join(STMT_LIST_BLOCK["list_items"])
    assert evidence.source_ref.block_id == "b004"
    assert evidence.source_ref.page == 13


# ── 语句级S: 轻量改写的保义门槛与非平凡性 ─────────────────


def _stmt_blocks_with_text(text: str) -> list[dict]:
    return [{"type": "text", "text": text, "page_idx": 1}]


def test_support_from_statement_reorder_variant() -> None:
    blocks = _stmt_blocks_with_text(
        "数据统一访问服务应支持sqlite3数据库存储配置数据。")
    seeds = collect_statement_seeds(blocks, DOC)
    assert len(seeds) == 1
    sample = synthesize_support_from_statement(seeds[0], blocks)
    assert sample is not None
    assert sample.label == "support"
    assert sample.operator == "support_rewrite:reorder"
    assert sample.claim_text == \
        "sqlite3数据库存储配置数据由数据统一访问服务支持。"
    assert sample.claim_text != seeds[0].statement_text
    assert all(passed for _, passed in sample.self_check)
    assert sample.module_verdict is None
    assert len(sample.evidence) >= 1


def test_support_from_statement_deontic_and_num_format() -> None:
    blocks = _stmt_blocks_with_text(
        "系统应确保单个BLOB数据的大小不超过65535字节。")
    seed = collect_statement_seeds(blocks, DOC)[0]
    sample = synthesize_support_from_statement(seed, blocks)
    assert sample is not None
    assert sample.operator == "support_rewrite:deontic_swap"
    assert sample.claim_text == \
        "系统须确保单个BLOB数据的大小不超过65535字节。"

    blocks = _stmt_blocks_with_text(
        "统一数据访问服务为热点数据提供的缓存容量为1000GB。")
    seed = collect_statement_seeds(blocks, DOC)[0]
    sample = synthesize_support_from_statement(seed, blocks)
    assert sample is not None
    assert sample.operator == "support_rewrite:num_format"
    assert sample.claim_text == \
        "统一数据访问服务为热点数据提供的缓存容量为1千GB。"


def test_support_from_statement_gate_rejects_unsafe_rewrites() -> None:
    # 否定模态(不应)不动且无其他安全改写; 去填充词损失过大(Jaccard<0.5)
    blocks = _stmt_blocks_with_text("系统响应时间不应超过100ms。")
    seed = collect_statement_seeds(blocks, DOC)[0]
    assert synthesize_support_from_statement(seed, blocks) is None
    blocks = _stmt_blocks_with_text("系统需要对1条数据进行处理。")
    seed = collect_statement_seeds(blocks, DOC)[0]
    assert synthesize_support_from_statement(seed, blocks) is None


# ── 语句级R: 确定性翻转与LCS不匹配自检 ────────────────────


def test_refute_from_statement_numeric_operator_flip() -> None:
    seeds = collect_statement_seeds(STMT_BLOCKS, DOC)
    seed = next(s for s in seeds
                if s.statement_text.startswith("每个BLOB数据"))
    sample = synthesize_refute_from_statement(
        seed, STMT_BLOCKS, [("连接失败", "连接管理")], [], module=MODULE)
    assert sample is not None
    assert sample.label == "refute"
    assert sample.operator == "numeric_operator_flip"
    assert "应大于65535字节" in sample.claim_text
    assert "不大于65535字节" not in sample.claim_text
    assert all(passed for _, passed in sample.self_check)
    assert sample.overlap_after < sample.overlap_before
    assert sample.module_verdict == "refute"


def test_refute_from_statement_implicit_bound_is_skipped() -> None:
    # 「在100ms内」隐式上界: 值/单位扰动只弱化约束(被蕴含), 必须不翻转
    blocks = _stmt_blocks_with_text("缓存更新操作应在100ms内完成，并刷新缓存数据。")
    seeds = collect_statement_seeds(blocks, DOC)
    assert len(seeds) == 1
    plan = plan_statement_flip(seeds[0], [], [blocks[0]["text"]], [])
    assert plan is None
    assert synthesize_refute_from_statement(
        seeds[0], blocks, [], []) is None


def test_refute_from_statement_e1_prompt_flip_anchored() -> None:
    seeds = collect_statement_seeds(STMT_BLOCKS, DOC)
    e1_seed = next(s for s in seeds if s.field_name.startswith("异常流"))
    pool = [("连接失败", "连接管理")]
    sample = synthesize_refute_from_statement(
        e1_seed, STMT_BLOCKS, pool, [], module=MODULE)
    assert sample is not None
    assert sample.operator == "e1_prompt_swap"
    assert sample.claim_text == \
        "在「缓存更新」用例中，异常流E1：系统提示连接失败，用例结束。"
    assert sample.claim_text.startswith("在「缓存更新」用例中，")
    assert all("连接失败" not in ev.text for ev in sample.evidence)
    assert all(passed for _, passed in sample.self_check)
    assert sample.overlap_after < sample.overlap_before
    assert sample.module_verdict == "refute"


def test_refute_from_statement_e1_ending_flip() -> None:
    seeds = collect_statement_seeds(STMT_BLOCKS, DOC)
    e1_seed = next(s for s in seeds if s.field_name.startswith("异常流"))
    sample = synthesize_refute_from_statement(
        e1_seed, STMT_BLOCKS, [], [], module=MODULE)
    assert sample is not None
    assert sample.operator == "e1_ending_flip"
    assert sample.claim_text == \
        "在「缓存更新」用例中，异常流E1：系统提示校验失败，用例继续。"
    assert sample.module_verdict == "refute"
    assert sample.overlap_after < sample.overlap_before


def test_refute_from_statement_identifier_flip() -> None:
    blocks = _stmt_blocks_with_text("3.2.1 SQL访问（PZXQ-GN-SQLFW）")
    blocks.append({"type": "text", "text": TEXT_BLOCK, "page_idx": 2})
    seeds = collect_statement_seeds(blocks, DOC)
    seed = next(s for s in seeds if "SQL访问" in s.statement_text)
    sample = synthesize_refute_from_statement(
        seed, blocks, [], ["PZXQ-GN-DXHFW", "PZXQ-GN-SQLFW"],
        module=MODULE)
    assert sample is not None
    assert sample.operator == "id_sibling_swap"
    assert "PZXQ-GN-DXHFW" in sample.claim_text
    assert "PZXQ-GN-SQLFW" not in sample.claim_text
    assert all("PZXQ-GN-DXHFW" not in ev.text for ev in sample.evidence)
    assert all(passed for _, passed in sample.self_check)
    assert sample.module_verdict != "support"


def test_refute_unscoped_e1_seed_is_scope_gated() -> None:
    # 跨用例歧义守卫: claim的提示关键词与两个用例的E1行都匹配(scope
    # 不唯一)时, e1类翻转不再尝试——换入的prompt在证据另一用例中真实
    # 存在, refute不sound
    evidence = (make_ev("FIX-UNSC-ev-001", USECASE_TABLE_HTML),
                make_ev("FIX-UNSC-ev-002", USECASE_TABLE2_HTML))
    seed = make_seed("FIX-UNSC-001", "系统提示连接失败，用例结束",
                     "e1_template_match", evidence, "系统异常时如何提示")
    matched = seed_matching_statements(seed)
    assert len({s.scope_key for s in matched}) == 2
    result = synthesize_refute_samples([seed], module=MODULE)
    assert result.samples == []
    assert result.stats["skipped_no_flippable_structure"] == 1


# ── 语句级N: 跨块开放世界与块内删除 ────────────────────────


def test_nie_from_statement_cross_and_inblock() -> None:
    seeds = collect_statement_seeds(STMT_BLOCKS, DOC)
    e1_seed = next(s for s in seeds if s.field_name.startswith("异常流"))
    samples = synthesize_nie_from_statement(
        e1_seed, STMT_BLOCKS, module=MODULE)
    by_op = {sample.operator: sample for sample in samples}
    assert set(by_op) == {"cross_block_evidence", "inblock_span_deletion"}
    cross = by_op["cross_block_evidence"]
    assert cross.label == "not_in_evidence"
    assert cross.claim_text == e1_seed.statement_text
    assert all(ev.evidence_id != f"{DOC}#b001" for ev in cross.evidence)
    assert all(passed for _, passed in cross.self_check)
    assert cross.module_verdict == "not_in_evidence"
    inblock = by_op["inblock_span_deletion"]
    assert inblock.label == "not_in_evidence"
    modified = [ev for ev in inblock.evidence
                if ev.evidence_id == f"{DOC}#b001"]
    assert len(modified) == 1
    assert "异常流E1：系统提示校验失败" not in modified[0].text
    assert "Use Case 名称：缓存更新" in modified[0].text
    assert all(passed for _, passed in inblock.self_check)
    assert inblock.module_verdict == "not_in_evidence"


def test_nie_from_statements_batch_stats() -> None:
    seeds = collect_statement_seeds(STMT_BLOCKS, DOC)
    result = synthesize_nie_from_statements(seeds, STMT_BLOCKS, module=MODULE)
    assert result.samples
    assert all(sample.label == "not_in_evidence" for sample in result.samples)
    assert all(sample.module_verdict in (None, "not_in_evidence")
               for sample in result.samples)
    stats = result.stats
    assert stats["cross_block"]["kept"] > 0
    assert stats["inblock_deletion"]["kept"] > 0
    for sample in result.samples:
        assert all(passed for _, passed in sample.self_check)
        assert len(sample.evidence) >= 1


# ── 组装与序列化 ──────────────────────────────────────────


def test_assemble_dataset_balances_and_assigns_ids() -> None:
    seeds = fixture_seeds()
    peers = {"FIX-E1-001": E1_REQUEST.evidence,
             "FIX-ID-001": ID_REQUEST.evidence}
    samples = (synthesize_support_samples(seeds).samples
               + synthesize_refute_samples(seeds, module=MODULE).samples
               + synthesize_nie_samples(seeds, module=MODULE,
                                        peer_evidence=peers).samples)
    final, stats = assemble_dataset(samples, balance=True)
    counts = stats["final_counts"]
    assert set(counts) == {"support", "refute", "not_in_evidence"}
    assert len(set(counts.values())) == 1
    ids = [sample.sample_id for sample in final]
    assert len(set(ids)) == len(ids)
    assert all(sample.sample_id for sample in final)
    capped, capped_stats = assemble_dataset(samples, cap_per_label=1,
                                            balance=False)
    assert sum(capped_stats["final_counts"].values()) == 3


def test_sample_serialization_roundtrip() -> None:
    seeds = fixture_seeds()
    result = synthesize_refute_samples(seeds, module=MODULE)
    sample = next(s for s in result.samples
                  if s.operator == "id_sibling_swap")
    payload = json.loads(json.dumps(sample_to_dict(sample),
                                     ensure_ascii=False))
    assert payload["label"] == "refute"
    assert payload["sample_id"] == sample.sample_id
    assert len(payload["evidence"]) == len(sample.evidence)
    for item, ev in zip(payload["evidence"], sample.evidence):
        assert evidence_from_dict(item) == ev
    assert isinstance(payload["check_items"], list)
    assert all(isinstance(item, str) for item in payload["check_items"])
    assert payload["self_check"] == dict(sample.self_check)


def test_evidence_dict_roundtrip() -> None:
    for ev in E1_REQUEST.evidence:
        assert evidence_from_dict(evidence_to_dict(ev)) == ev


# ── 叙事文法合成: 表格行事实三元组 → 叙事claim (v2) ────────

#: 能力表fixture: 两行不同设备/状态/任务书映射(跨行污染域)
NARR_CAPABILITY_TABLE_HTML = (
    '<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>'
    '<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>'
    '<th><p>需求重用</p></th><th><p>方式名称</p></th>'
    '<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th></tr>'
    '</thead><tbody>'
    '<tr><td><p>1</p></td><td><p>数据查询</p></td>'
    '<td><p>PZXQ-GN-SQLFW-CXSJ</p></td>'
    '<td><p>提供数据查询功能</p></td><td><p>沿用</p></td>'
    '<td><p>平板、桌面、手持</p></td>'
    '<td><p>运行阶段、开发阶段</p></td><td><p>4.1.1</p></td></tr>'
    '<tr><td></td><td><p>SQL文件输出</p></td>'
    '<td><p>PZXQ-GN-SQLFW-DMLSC</p></td>'
    '<td><p>将查询结果以sql文件形式输出</p></td><td><p>沿用</p></td>'
    '<td><p>桌面、平版</p></td>'
    '<td><p>开发阶段</p></td><td><p>4.1.1</p></td></tr>'
    '</tbody></table>')

#: 接口表fixture(独立标识列)
NARR_INTERFACE_TABLE_HTML = (
    '<table><thead><tr><th><p>序号</p></th><th><p>接口需求名称</p></th>'
    '<th><p>接口需求标识</p></th><th><p>接口类型</p></th>'
    '<th><p>发送方</p></th><th><p>接收方</p></th><th><p>接口内容</p></th>'
    '<th><p>接口优先级</p></th></tr></thead><tbody>'
    '<tr><td><p>1</p></td><td><p>与应用软件接口</p></td>'
    '<td><p>PZXQ-JK-SJTYFW-YYRJ</p></td><td><p>API接口</p></td>'
    '<td><p>本系统</p></td><td><p>应用软件</p></td>'
    '<td><p>数据查询信息</p></td><td><p>中</p></td></tr>'
    '<tr><td><p>2</p></td><td><p>与运行支撑接口</p></td>'
    '<td><p>PZXQ-JK-SJTYFW-YXZC</p></td><td><p>API接口</p></td>'
    '<td><p>运行支撑服务</p></td><td><p>本系统</p></td>'
    '<td><p>服务器信息</p></td><td><p>中</p></td></tr>'
    '</tbody></table>')

#: 数据表fixture(单位+最大值/最小值)
NARR_DATA_TABLE_HTML = (
    '<table><thead><tr><th><p>序号</p></th><th><p>数据项</p></th>'
    '<th><p>最大值</p></th><th><p>最小值</p></th><th><p>精度</p></th>'
    '<th><p>单位</p></th><th><p>备注</p></th></tr></thead><tbody>'
    '<tr><td></td><td><p>提示信息</p></td><td><p>256</p></td>'
    '<td><p>5</p></td><td><p>-</p></td><td><p>字节</p></td>'
    '<td><p>-</p></td></tr>'
    '<tr><td></td><td><p>组件名</p></td><td><p>64</p></td>'
    '<td><p>-</p></td><td><p>-</p></td><td><p>字节</p></td>'
    '<td><p>-</p></td></tr>'
    '</tbody></table>')

NARR_TEXT_BLOCK = {"type": "text", "text": TEXT_BLOCK, "page_idx": 1}
NARR_E1_BLOCKS = [
    {"type": "text", "text": TEXT_BLOCK, "page_idx": 9},
    {"type": "table", "table_body": USECASE_TABLE_HTML, "page_idx": 10},
    {"type": "table", "table_body": USECASE_TABLE2_HTML, "page_idx": 11},
    {"type": "text", "text": "统一数据访问服务支持sqlite3数据库。", "page_idx": 12},
]
NARR_CAP_BLOCKS = [
    {"type": "text", "text": TEXT_BLOCK, "page_idx": 20},
    {"type": "table", "table_body": NARR_CAPABILITY_TABLE_HTML, "page_idx": 21},
    {"type": "table", "table_body": NARR_INTERFACE_TABLE_HTML, "page_idx": 22},
    {"type": "table", "table_body": NARR_DATA_TABLE_HTML, "page_idx": 23},
]
#: E1池须含另一用例的提示(缓存更新: 校验失败 / 连接管理: 连接失败)


def test_extract_narrative_corpus_capability_facts() -> None:
    facts, pools = extract_narrative_corpus(NARR_CAP_BLOCKS, DOC)
    by_family: dict[str, list] = {}
    for fact in facts:
        by_family.setdefault(fact.family, []).append(fact)
    assert set(by_family) == {"capability_device", "capability_state",
                              "trace_binding", "interface_flow",
                              "param_value"}
    # 位置保持: 空序号列不左移(SQL文件输出的设备=桌面、平版 而非 沿用)
    sql = next(f for f in by_family["capability_device"]
               if f.field("功能") == "SQL文件输出")
    assert sql.field("设备列表") == "桌面、平版"
    assert sql.siblings == ("平板、桌面、手持",)
    device = next(f for f in by_family["capability_device"]
                  if f.field("功能") == "数据查询")
    assert device.field("设备列表") == "平板、桌面、手持"
    state = next(f for f in by_family["capability_state"]
                 if f.field("功能") == "SQL文件输出")
    assert state.field("状态") == "开发阶段"
    assert state.siblings == ("运行阶段、开发阶段",)
    trace = next(f for f in by_family["trace_binding"]
                 if f.field("需求ID") == "PZXQ-GN-SQLFW-CXSJ")
    assert trace.field("任务书ID") == "4.1.1"
    iface = by_family["interface_flow"][0]
    assert iface.field("接口名") == "与应用软件接口"
    assert iface.field("接口ID") == "PZXQ-JK-SJTYFW-YYRJ"
    assert iface.field("发送方") == "本系统"
    assert iface.siblings == ("运行支撑服务",)
    param = next(f for f in by_family["param_value"]
                 if f.field("参数") == "提示信息")
    assert (param.field("算子"), param.field("值"), param.field("单位")) \
        == ("不超过", "256", "字节")
    assert "64" in param.siblings
    assert pools.doc_text  # 全文归一化文本供虚构值排除


def test_narrative_capability_device_variants() -> None:
    facts, pools = extract_narrative_corpus(NARR_CAP_BLOCKS, DOC)
    result = synthesize_narrative_samples(facts, NARR_CAP_BLOCKS, pools)
    device_samples = [s for s in result.samples
                      if s.claim_kind == "capability_device"]
    support = next(s for s in device_samples if s.label == "support")
    assert support.claim_text == "数据查询功能支持在平板、桌面、手持上使用"
    assert all(passed for _, passed in support.self_check)
    assert support.source == "narrative:capability_device"
    # R加不存在的设备(虚构池, 不在doc): 枚举外误报
    added = next(s for s in device_samples
                 if s.operator == "narrative_device_member_add"
                 and s.seed_id.endswith(":cap1"))
    fictional = ("手机版", "大屏版", "穿戴版", "车载版", "网页版")
    assert any(f"、{device}" in added.claim_text for device in fictional)
    assert all(device not in pools.doc_text for device in fictional)
    # R换其他行设备(跨行绑定: 值真实存在于文档但绑定错误)
    swapped = next(s for s in device_samples
                   if s.operator == "narrative_device_member_swap"
                   and s.seed_id.endswith(":cap2"))
    assert "手持" in swapped.claim_text  # 换入数据查询行的成员
    assert all(passed for _, passed in swapped.self_check)
    # R删一员(穷举清单缺员, 仅断言): 剩n-1个原成员
    dropped = next(s for s in device_samples
                   if s.operator == "narrative_device_member_drop"
                   and s.seed_id.endswith(":cap1"))
    assert dropped.claim_text.startswith("数据查询功能仅在")
    kept_members = dropped.claim_text.replace(
        "数据查询功能仅在", "").replace("上使用", "").split("、")
    assert len(kept_members) == 2
    assert set(kept_members) < {"平板", "桌面", "手持"}
    # N效果性断言
    nie = next(s for s in device_samples
               if s.operator == "narrative_effect_claim"
               and s.seed_id.endswith(":cap1"))
    assert nie.claim_text == "数据查询功能确保用户操作体验的一致性"
    assert nie.label == "not_in_evidence"
    # 证据窗口含seed表块(完整同表 → 污染来源行入premise)
    for sample in device_samples:
        assert any(ev.source_ref.block_id == "b001" for ev in sample.evidence)


def test_narrative_capability_state_and_trace_variants() -> None:
    facts, pools = extract_narrative_corpus(NARR_CAP_BLOCKS, DOC)
    result = synthesize_narrative_samples(facts, NARR_CAP_BLOCKS, pools)
    # SQL文件输出(开发阶段)换入数据查询的运行阶段 → 跨行值域绑定错误
    state = next(s for s in result.samples
                 if s.claim_kind == "capability_state" and s.label == "refute"
                 and s.seed_id.endswith(":cap2"))
    assert state.operator == "narrative_state_swap"
    assert "运行阶段" in state.claim_text
    assert state.claim_text == "SQL文件输出在运行阶段提供完整功能"
    # 数据查询无跨行异值(开发阶段是其子串被排除) → 虚构阶段或跳过
    dq_state = [s for s in result.samples
                if s.claim_kind == "capability_state" and s.label == "refute"
                and s.seed_id.endswith(":cap1")]
    for sample in dq_state:
        assert all(passed for _, passed in sample.self_check)
    # 同表两行任务书相同(均为4.1.1) → 无跨行污染域 → 无trace refute
    # (跨行污染是sound refute的必要条件, 同值映射不可翻转)
    assert not [s for s in result.samples
                if s.claim_kind == "trace_binding" and s.label == "refute"]
    trace_support = next(s for s in result.samples
                         if s.claim_kind == "trace_binding"
                         and s.label == "support"
                         and s.seed_id.endswith(":cap1"))
    assert trace_support.claim_text == \
        "需求PZXQ-GN-SQLFW-CXSJ追溯至任务书4.1.1"


def test_narrative_usecase_e1_variants() -> None:
    facts, pools = extract_narrative_corpus(NARR_E1_BLOCKS, DOC)
    result = synthesize_narrative_samples(facts, NARR_E1_BLOCKS, pools)
    e1_samples = [s for s in result.samples
                  if s.claim_kind == "usecase_e1"]
    support = next(s for s in e1_samples if s.label == "support")
    assert support.claim_text == \
        "在缓存更新过程中发生异常时，系统提示校验失败，用例结束"
    # R换入他用例提示(跨用例模板错配)
    swapped = next(s for s in e1_samples
                   if s.operator == "narrative_prompt_swap")
    assert "连接失败" in swapped.claim_text
    assert "缓存更新" in swapped.claim_text
    assert all(passed for _, passed in swapped.self_check)
    # R2处置翻转
    flipped = next(s for s in e1_samples
                   if s.operator == "narrative_ending_flip")
    assert flipped.claim_text == \
        "在缓存更新过程中发生异常时，系统提示校验失败，用例继续"
    # N虚构处置
    nie = next(s for s in e1_samples
               if s.operator == "narrative_effect_claim")
    assert nie.claim_text == "在缓存更新异常处理完成后系统自动重试该操作"
    assert nie.label == "not_in_evidence"
    assert all("自动重试" not in ev.text for ev in nie.evidence)


def test_narrative_interface_and_param_variants() -> None:
    facts, pools = extract_narrative_corpus(NARR_CAP_BLOCKS, DOC)
    result = synthesize_narrative_samples(facts, NARR_CAP_BLOCKS, pools)
    iface = next(s for s in result.samples
                 if s.claim_kind == "interface_flow" and s.label == "refute")
    assert iface.operator == "narrative_sender_swap"
    # 应用软件接口(本系统→应用软件)换成运行支撑服务 → 跨行发送方
    assert iface.claim_text == \
        "与应用软件接口通过接口PZXQ-JK-SJTYFW-YYRJ由运行支撑服务发送至应用软件"
    iface_nie = next(s for s in result.samples
                     if s.claim_kind == "interface_flow"
                     and s.operator == "narrative_effect_claim")
    assert iface_nie.claim_text == \
        "接口PZXQ-JK-SJTYFW-YYRJ采用加密传输保障数据安全"
    # param跨参数值绑定: 提示信息(256)换成组件名的64
    param = next(s for s in result.samples
                 if s.claim_kind == "param_value" and s.label == "refute")
    assert param.operator == "narrative_value_swap"
    assert param.claim_text == "提示信息的要求是不超过64字节"
    param_support = next(s for s in result.samples
                         if s.claim_kind == "param_value"
                         and s.label == "support")
    assert param_support.claim_text == "提示信息的要求是不超过256字节"


def test_narrative_evidence_window_contains_seed_table() -> None:
    window = narrative_evidence_window(DOC, 1, NARR_CAP_BLOCKS)
    ids = [ev.source_ref.block_id for ev in window]
    assert "b001" in ids
    assert ids == sorted(ids)
    assert 2 <= len(window) <= 4
    assert all(str(NARR_CAP_BLOCKS[int(ev.source_ref.block_id[1:])].get(
        "type")) in ("text", "table", "list") for ev in window)


def test_narrative_n_modes_and_question_knobs() -> None:
    facts, pools = extract_narrative_corpus(NARR_CAP_BLOCKS, DOC)
    all_modes = synthesize_narrative_samples(
        facts, NARR_CAP_BLOCKS, pools, (), frozenset({"effect", "detail"}),
        "generic")
    detail = [s for s in all_modes.samples
              if s.operator == "narrative_detail_claim"]
    assert detail  # fixture文档不含'无缝切换'等标记 → detail模式产出
    effect_only = synthesize_narrative_samples(
        facts, NARR_CAP_BLOCKS, pools, (), frozenset({"effect"}), "generic")
    assert not [s for s in effect_only.samples
                if s.operator == "narrative_detail_claim"]
    real_q = synthesize_narrative_samples(
        facts, NARR_CAP_BLOCKS, pools, (), frozenset({"effect"}), "real")
    support = next(s for s in real_q.samples if s.label == "support")
    assert support.question == "数据查询功能支持在哪些设备上使用"
    assert support.question != STATEMENT_QUESTION


def test_narrative_templates_cover_all_families() -> None:
    assert set(NARRATIVE_TEMPLATES) == {
        "capability_device", "capability_state", "usecase_e1",
        "interface_flow", "param_value", "trace_binding"}
    for family, templates in NARRATIVE_TEMPLATES.items():
        assert "S" in templates and "N" in templates
        assert any(key.startswith("R") for key in templates)




def test_real_data_smoke_first_ten() -> None:
    rows = [json.loads(line) for line
            in FROZEN.read_text(encoding="utf-8").splitlines()
            if line.strip()][:10]
    requests = [QAInput(
        instance_id=str(row["instance_id"]), question=str(row["question"]),
        answer=str(row["answer"]),
        context_freeze_id=str(row["context_freeze_id"]),
        evidence=tuple(evidence_from_dict(item)
                       for item in row["evidence"])) for row in rows]
    seeds = collect_support_seeds(requests, MODULE)
    assert len(seeds) > 0
    peers = {request.instance_id: request.evidence
             for request in requests}
    support = synthesize_support_samples(seeds)
    refute = synthesize_refute_samples(seeds, module=MODULE)
    nie = synthesize_nie_samples(seeds, module=MODULE,
                                 peer_evidence=peers)
    assert len(support.samples) > 0
    assert len(refute.samples) > 0
    assert len(nie.samples) > 0
    for sample in refute.samples + nie.samples:
        assert all(passed for _, passed in sample.self_check)
        assert sample.evidence
    for sample in nie.samples:
        assert sample.label == "not_in_evidence"
        assert sample.module_verdict in (None, "not_in_evidence")


DOC04_CONTENT_LIST = (
    BASE / "data/gjb_438c/mineru_standard" / DOC / "office"
    / f"{DOC}_content_list.json")


def test_real_data_smoke_statement_path_first_thirty_blocks() -> None:
    blocks = [b for b in json.loads(
        DOC04_CONTENT_LIST.read_text(encoding="utf-8"))
        if b.get("type") in ("text", "table", "list")][:30]
    assert len(blocks) == 30
    seeds = collect_statement_seeds(blocks, DOC)
    assert len(seeds) > 0
    support = synthesize_support_from_statements(seeds, blocks)
    refute = synthesize_refute_from_statements(seeds, blocks, module=MODULE)
    nie = synthesize_nie_from_statements(seeds, blocks, module=MODULE)
    assert len(support.samples) > 0
    assert len(refute.samples) > 0
    assert len(nie.samples) > 0
    assert refute.stats["self_check_pass_rate"] is not None
    for sample in refute.samples + nie.samples:
        assert all(passed for _, passed in sample.self_check)
        assert sample.evidence
        assert 3 <= len(sample.evidence) <= 6
    for sample in support.samples:
        assert sample.label == "support"
        assert sample.claim_text != sample.seed_id
    for sample in refute.samples:
        assert sample.module_verdict in (None, "refute", "not_in_evidence")
    for sample in nie.samples:
        assert sample.label == "not_in_evidence"
        assert sample.module_verdict in (None, "not_in_evidence")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
