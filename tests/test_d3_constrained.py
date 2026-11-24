"""Tests for algorithms/consistency/d3_constrained.py (X1约束解码).

五层:
  1. 合成词表FSM确定性快照: 骨架关键位置的允许token集合逐项断言
     (verdict枚举trie/字符串自由区/数字护栏/收尾eos), 完整合法序列
     全程走通并逐字还原为可解析JSON, 非法token显式报错, 全状态
     无死锁;
  2. 真实Qwen tokenizer(skipif资产缺失): byte-level反解与decode
     逐id一致, 教师标签真实目标JSON的BPE切分全程走通(骨架与训练
     分布逐字兼容), free集排除added特殊token;
  3. 后验对齐align_issues: span精确/可find/不可寻/evidence_ref边界;
  4. 处理器适配层(需torch): 掩码只置-inf不重排, 干预计数,
     input_ids历史fold(增量/回退重同步);
  5. GPU端到端(slow+skipif): v2b真实模型贪心复跑同结果.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.d3_constrained import (  # noqa: E402
    VERDICTS,
    SkeletonMachine,
    VocabIndex,
    align_issues,
    build_skeleton_grammar,
    constrained_generate,
    processor_class,
)

TOKENIZER_DIR = BASE / "models/llm/qwen3-1.7b"
TEACHER_LABELS = (BASE / "data/gjb_438c/distillation"
                  / "d3_teacher_labels_v1.jsonl")
ADAPTER = BASE / "models/llm/d3_student_v2b"

_EOS = 400


def _mini_vocab() -> dict[int, str | None]:
    """合成词表: 可打印ASCII单字符token(id=ord) + 关键合并token +
    陷阱token(含引号/换行/反斜杠/前导零数字)."""
    texts: dict[int, str | None] = {
        code: chr(code) for code in range(32, 127)}
    texts.update({
        200: '{"', 201: '{"verdict', 202: '": ', 203: '",',
        204: ', ', 205: '],', 206: '"}', 207: ']}',
        208: 'support', 209: 'refute', 210: 'not_in_evidence',
        211: 'null', 212: '12', 213: '05', 214: '00',
        215: '战位', 216: '管理', 217: 'a"b', 218: 'a\nb',
        219: 'a\\b', 220: 'TERM-01', 221: 'ev-1', 222: '004',
        _EOS: '<|im_end|>',
    })
    return texts


def _machine() -> SkeletonMachine:
    return SkeletonMachine(
        VocabIndex.from_texts(_mini_vocab(), {_EOS}, added={_EOS}))


def _char_ids(text: str) -> list[int]:
    """按单字符token编码(合成词表id=ord)."""
    return [ord(c) for c in text]


def _walk(machine: SkeletonMachine, token_ids: list[int]) -> None:
    for tid in token_ids:
        allowed = machine.allowed_ids()
        assert tid in allowed, (
            f"死锁: 状态{machine.snapshot()}不接受token {tid}")
        machine.consume(tid)


def _texts_of(machine: SkeletonMachine,
              token_ids: list[int]) -> str:
    out = []
    for tid in token_ids:
        text = machine.index.texts.get(tid)
        assert text is not None
        out.append(text)
    return "".join(out)


# ── 1. 合成词表FSM确定性快照 ────────────────────────────────────────────


def test_fsm_start_state_mask_snapshot() -> None:
    m = _machine()
    # root候选'{"verdict": "'的前缀token: '{'/'{"'/'{"verdict'
    assert m.allowed_ids() == frozenset({ord('{'), 200, 201})
    assert m.snapshot() == "choice:root:{\"verdict\": \""


def test_fsm_verdict_enum_mask_snapshot() -> None:
    m = _machine()
    _walk(m, [200] + _char_ids('verdict": "'))
    # 枚举trie: 三个完整值token + s/r/n首字符
    assert m.allowed_ids() == frozenset(
        {ord('s'), ord('r'), ord('n'), 208, 209, 210})
    assert 201 not in m.allowed_ids()
    assert ord('x') not in m.allowed_ids()
    # 部分消费收缩: 's'后剩余候选'upport', 只允许其前缀
    # (完整token 'support'已不可用——单字符路径锁定切分, 无死锁)
    m.consume(ord('s'))
    assert m.allowed_ids() == frozenset({ord('u')})


def test_fsm_string_free_zone_masks() -> None:
    m = _machine()
    _walk(m, [200] + _char_ids('verdict": "') + [208]      # support
             + [203] + _char_ids(' "issues": [')
             + [200] + _char_ids('quote": "'))
    assert m.state[0] == "str"
    allowed = m.allowed_ids()
    # 自由内容: 普通文本/字母/数字token都行
    assert 215 in allowed and 220 in allowed and ord('x') in allowed
    # 陷阱token被掩: 含引号/换行/反斜杠/特殊eos
    assert 217 not in allowed
    assert 218 not in allowed
    assert 219 not in allowed
    assert _EOS not in allowed
    # 出口: 后继字面量'", "span": '的前缀('",')
    assert 203 in allowed


def test_fsm_number_guards() -> None:
    def _to_span1() -> SkeletonMachine:
        m = _machine()
        _walk(m, [200] + _char_ids('verdict": "') + [209]
                 + [203] + _char_ids(' "issues": [')
                 + [200] + _char_ids('quote": "') + [215]
                 + [203] + _char_ids(' "span": ') + [ord('[')])
        assert m.state[0] == "num" and m.state[3] == ""
        return m

    m = _to_span1()
    # 护栏1: 数值未开写时只允许数字(排除'[,]')
    assert m.allowed_ids() == frozenset(
        {ord(c) for c in '0123456789'} | {212})
    with pytest.raises(ValueError, match="num:num_comma:-"):
        m.consume(ord(','))

    # 护栏2: 首数字是单独的0→锁出口(排除'[01, 2]')
    m2 = _to_span1()
    m2.consume(ord('0'))
    assert ord('1') not in m2.allowed_ids()
    with pytest.raises(ValueError, match="num:num_comma:z"):
        m2.consume(ord('1'))
    assert ord(',') in m2.allowed_ids()

    # 非首位的0合法: [10 → [100
    m3 = _to_span1()
    m3.consume(ord('1'))
    m3.consume(ord('0'))
    assert ord('0') in m3.allowed_ids()

    # 前导零多位token('05'/'00'/'004')不在digit_ids
    idx = VocabIndex.from_texts(_mini_vocab(), {_EOS})
    assert 213 not in idx.digit_ids
    assert 214 not in idx.digit_ids
    assert 222 not in idx.digit_ids
    assert 212 in idx.digit_ids


def test_fsm_full_walk_support_reconstructs_json() -> None:
    m = _machine()
    target = '{"verdict": "support", "issues": []}'
    ids = _char_ids(target)
    _walk(m, ids)
    assert m.finished
    m.consume(_EOS)                   # eos状态幂等
    assert m.finished
    assert json.loads(_texts_of(m, ids)) == {
        "verdict": "support", "issues": []}


def test_fsm_full_walk_refute_reconstructs_json() -> None:
    m = _machine()
    seq = (
        [200] + _char_ids('verdict": "') + [209]
        + [203] + _char_ids(' "issues": [')
        + [200] + _char_ids('quote": "') + [215, 216]
        + [203] + _char_ids(' "span": ')
        + [ord('['), 212, 204, ord('1'), ord('7')]
        + [205] + _char_ids(' "rule_id": "') + [220]
        + [203] + _char_ids(' "evidence_ref": "') + [221]
        + [203] + _char_ids(' "explanation": "') + [215]
        + [206] + [207])
    _walk(m, seq)
    assert m.finished
    m.consume(_EOS)
    parsed = json.loads(_texts_of(m, seq))
    assert parsed == {
        "verdict": "refute",
        "issues": [{"quote": "战位管理", "span": [12, 17],
                    "rule_id": "TERM-01", "evidence_ref": "ev-1",
                    "explanation": "战位"}]}


def test_fsm_null_span_and_multi_issue_loop() -> None:
    m = _machine()
    _walk(m, [200] + _char_ids('verdict": "') + [209]
             + [203] + _char_ids(' "issues": [')
             + [200] + _char_ids('quote": "') + [216]
             + [203] + _char_ids(' "span": ') + [211])   # null
    assert m.snapshot() == "choice:after_null:, \"rule_id\": \""
    _walk(m, [204] + _char_ids('"rule_id": "') + [220]
             + [203] + _char_ids(' "evidence_ref": "') + [221]
             + [203] + _char_ids(' "explanation": "') + [216]
             + [206])
    # arr_tail: 逗号续写第二个issue | ]}收尾
    assert m.snapshot() == "choice:arr_tail:, {\"quote\": \"|]}"
    _walk(m, [204] + [200] + _char_ids('quote": "') + [215]
             + [203] + _char_ids(' "span": ')
             + [ord('['), ord('0'), ord(','), ord(' '), ord('9')]
             + [205] + _char_ids(' "rule_id": "') + [220]
             + [203] + _char_ids(' "evidence_ref": "') + [221]
             + [203] + _char_ids(' "explanation": "') + [215]
             + [206])
    assert m.snapshot() == "choice:arr_tail:, {\"quote\": \"|]}"
    m.consume(207)                    # ']}'
    assert m.finished


def test_fsm_illegal_tokens_raise() -> None:
    m = _machine()
    with pytest.raises(ValueError, match="choice:root"):
        m.consume(215)                # 中文不能出现在root
    m.consume(200)
    with pytest.raises(ValueError, match="choice:root"):
        m.consume(ord('x'))
    eos_m = _machine()
    _walk(eos_m, _char_ids('{"verdict": "support", "issues": []}'))
    assert eos_m.finished
    with pytest.raises(ValueError, match="eos状态不接受"):
        eos_m.consume(ord('x'))


def test_fsm_no_deadlock_over_all_grammar_states() -> None:
    """静态无死锁: 每个骨架状态(含num三种子状态)允许集非空."""
    m = _machine()
    for name, node in m.grammar.items():
        if node.kind == "num":
            for flag in ("", "d", "z"):
                m.state = ("num", node.succ, (), flag)
                assert m.allowed_ids(), f"num死锁: {name}/{flag}"
            continue
        m.state = m._init_state(name)
        assert m.allowed_ids(), f"死锁: {name}"
    # 动态收缩状态: 每个剩余候选位置仍有合法token
    for rem in ('erdict": "', 'upport', '"issues": [', ' "span": ',
                '], "rule_id": "', ', {"quote": "'):
        m.state = ("choice", "root", ((rem, "verdict"),), "")
        assert m.allowed_ids(), f"收缩死锁: {rem!r}"


def test_fsm_state_cache_returns_consistent_sets() -> None:
    m = _machine()
    first = m.allowed_ids()
    assert m.allowed_ids() == first
    m.consume(200)
    assert 200 not in m.allowed_ids()
    m.reset()
    assert m.allowed_ids() == first
    assert m.snapshot() == "choice:root:{\"verdict\": \""


# ── 2. 真实Qwen tokenizer ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def real_tokenizer():
    if not (TOKENIZER_DIR / "tokenizer.json").exists():
        pytest.skip("models/llm/qwen3-1.7b缺失")
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(str(TOKENIZER_DIR))


@pytest.fixture(scope="module")
def real_index(real_tokenizer) -> VocabIndex:
    return VocabIndex.from_tokenizer(real_tokenizer)


def test_real_byte_decode_matches_hf_decode(
        real_tokenizer, real_index) -> None:
    rng = random.Random(0)
    ids = [i for i, t in real_index.texts.items() if t is not None]
    for tid in rng.sample(ids, 100):
        assert real_index.texts[tid] == \
            real_tokenizer.decode([tid], skip_special_tokens=False)


def test_real_vocab_invariants(real_tokenizer, real_index) -> None:
    added = set(real_tokenizer.get_added_vocab().values())
    assert real_index.eos_ids == {151645, 151643}
    assert not (added & real_index.free_ids), "特殊token漏进自由集"
    assert not (added & real_index.digit_ids)
    for tid in real_index.digit_ids:
        text = real_index.texts[tid]
        assert text is not None and text.isdigit() \
            and (len(text) == 1 or text[0] != "0")
    # 每个骨架候选的起点状态在真实词表下恒有合法token
    m = SkeletonMachine(real_index)
    for name, node in m.grammar.items():
        for cand, succ in node.cands:
            m.state = ("choice", name, ((cand, succ),), "")
            assert m.allowed_ids(), \
                f"真实词表候选起点缺失: {name}:{cand!r}"


def _serialize_target(row: dict) -> str:
    """与tools/train_d3_student._target_message同构的目标序列化."""
    return json.dumps(
        {"verdict": row["verdict"], "issues": [
            {"quote": i["quote"], "span": i["span"],
             "rule_id": i["rule_id"], "evidence_ref": i["evidence_ref"],
             "explanation": i["explanation"]}
            for i in row["issues"]]},
        ensure_ascii=False)


def test_real_walk_teacher_target_bpe(real_tokenizer,
                                      real_index) -> None:
    """教师标签真实目标(=训练分布)的BPE切分全程可走通且收尾——
    骨架与训练分布逐字兼容的直接证据; 不兼容则约束会把模型的
    natural切分掩死(强制切分虽无死锁但分布漂移)."""
    if not TEACHER_LABELS.exists():
        pytest.skip("d3_teacher_labels_v1.jsonl缺失")
    rows = [json.loads(line) for line in
            TEACHER_LABELS.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    picked = ([r for r in rows if r["verdict"] == "refute"
               and len(r["issues"]) >= 2][:2]
              + [r for r in rows if r["verdict"] == "refute"
                 and len(r["issues"]) == 1][:1]
              + [r for r in rows if r["verdict"] != "refute"][:2])
    assert len(picked) >= 4
    for row in picked:
        target = _serialize_target(row)
        m = SkeletonMachine(real_index)
        ids = real_tokenizer(target, add_special_tokens=False)[
            "input_ids"]
        _walk(m, ids)
        assert m.finished, f"未收尾: {row['instance_id']}"
        assert json.loads(_texts_of(m, ids)) == json.loads(target)


def test_real_walk_synthetic_paths(real_tokenizer, real_index) -> None:
    """覆盖教师标签未出现的路径: null span/三值枚举/双issue循环."""
    cases = [
        '{"verdict": "not_in_evidence", "issues": []}',
        json.dumps({"verdict": "support", "issues": [
            {"quote": "战位管理", "span": None, "rule_id": "TERM-07",
             "evidence_ref": "ev-2", "explanation": "同一标识冲突"},
            {"quote": "初始化配置", "span": [0, 5],
             "rule_id": "TERM-01", "evidence_ref": "ev-1",
             "explanation": "值不一致"}]}, ensure_ascii=False),
    ]
    for target in cases:
        m = SkeletonMachine(real_index)
        ids = real_tokenizer(target, add_special_tokens=False)[
            "input_ids"]
        _walk(m, ids)
        assert m.finished
        assert json.loads(_texts_of(m, ids)) == json.loads(target)


def test_real_allowed_sets_at_key_positions(real_tokenizer,
                                            real_index) -> None:
    m = SkeletonMachine(real_index)
    support_id = real_tokenizer.convert_tokens_to_ids("support")
    assert support_id is not None
    assert support_id not in m.allowed_ids()  # 起点只允许root前缀
    for tid in m.allowed_ids():
        text = real_index.texts[tid]
        assert text is not None and '{"verdict": "'.startswith(text)
    # root字面量的真实BPE切分逐步可走
    for tid in real_tokenizer('{"verdict": "',
                              add_special_tokens=False)["input_ids"]:
        m.consume(tid)
    # verdict枚举位: 三值的真实BPE切分全程可走
    # (真实词表只有'support'是整token; 'refute'/'not_in_evidence'
    # 走多token字符路径——trie不依赖整token存在)
    for value in VERDICTS:
        enum_m = SkeletonMachine(real_index)
        for tid in real_tokenizer('{"verdict": "',
                                  add_special_tokens=False)["input_ids"]:
            enum_m.consume(tid)
        for tid in real_tokenizer(value, add_special_tokens=False)[
                "input_ids"]:
            assert tid in enum_m.allowed_ids(), (
                f"枚举值{value}的token {tid}被掩")
            enum_m.consume(tid)
    assert support_id in m.allowed_ids()


# ── 3. 后验对齐 ─────────────────────────────────────────────────────────


def test_align_issues_exact_and_findable() -> None:
    answer = "战位管理与席位管理"
    issues = [
        {"quote": "战位管理", "span": [0, 4], "rule_id": "TERM-01",
         "evidence_ref": "ev-1", "explanation": "a"},
        {"quote": "席位管理", "span": [0, 4], "rule_id": "TERM-01",
         "evidence_ref": "ev-2", "explanation": "b"},
    ]
    out = align_issues(issues, answer, ["e1", "e2"])
    assert out[0]["span_verified"] is True
    assert out[0]["literal_faithful"] is True
    assert out[0]["span_find_pos"] is None
    assert out[0]["evidence_ref_ok"] is True
    # span错但quote可find: 不修复span, 只记录find位置
    assert out[1]["span_verified"] is False
    assert out[1]["literal_faithful"] is True
    assert out[1]["span_find_pos"] == 5
    assert out[1]["span"] == [0, 4]              # 原值不动
    assert out[1]["explanation"] == "b"


def test_align_issues_unfaithful_and_invalid() -> None:
    answer = "战位管理"
    issues = [
        {"quote": "不存在", "span": [0, 3], "evidence_ref": "ev-1"},
        {"quote": "战位管理", "span": [0, 99], "evidence_ref": "ev-9"},
        {"quote": "战位管理", "span": None, "evidence_ref": "ev-0"},
        {"quote": "战位管理", "span": [0.0, 4], "evidence_ref": "block-2"},
        {"quote": "战位管理", "span": [True, 4], "evidence_ref": "ev-x"},
        {"quote": "", "span": [0, 4], "evidence_ref": "ev-1"},
    ]
    out = align_issues(issues, answer, ["e1"])
    assert out[0]["literal_faithful"] is False
    assert out[0]["span_verified"] is False
    assert out[0]["span_find_pos"] is None
    assert out[1]["span_verified"] is False       # 区间越界
    assert out[1]["evidence_ref_ok"] is False     # ev-9超界
    assert out[2]["span_verified"] is False       # span非list
    assert out[2]["evidence_ref_ok"] is False     # ev-0
    assert out[3]["span_verified"] is False       # float非int
    assert out[3]["evidence_ref_ok"] is False     # 非ev前缀
    assert out[4]["span_verified"] is False       # bool冒充int
    assert out[4]["evidence_ref_ok"] is False     # 非数字
    assert out[5]["literal_faithful"] is False    # 空quote


def test_align_issues_no_evidence_and_non_dict() -> None:
    out = align_issues(
        [{"quote": "a", "span": [0, 1], "evidence_ref": "ev-1"}],
        "a", None)
    assert out[0]["evidence_ref_ok"] is None      # 不校验而非误报
    assert align_issues(["非dict", 5], "a") == []


# ── 4. 处理器适配层(需torch) ─────────────────────────────────────────────


def _scores(n_vocab: int = 500):
    import torch
    return torch.zeros(1, n_vocab)


def test_processor_masks_and_counts_intervention() -> None:
    import torch
    proc = processor_class()(_machine(), prompt_len=2)
    assert proc.machine.state[1] == "root"
    # 第一步: 历史无生成token → 掩码反映root状态
    scores = _scores()
    out = proc(torch.tensor([[7, 7]]), scores)
    for tid in (ord('{'), 200, 201):
        assert out[0, tid].item() == 0.0
    for tid in (ord('x'), 215, 208, _EOS):
        assert torch.isinf(out[0, tid]) and out[0, tid] < 0
    assert proc.n_steps == 1
    # 全零logits的argmax=token 0(不在允许集)→被改写→计一次干预
    assert proc.n_interventions == 1
    assert out is scores                      # 原地掩码不重排
    # 第二步: 生成'{"'后 → 掩码反映root剩余'verdict": "'
    out2 = proc(torch.tensor([[7, 7, 200]]), _scores())
    assert out2[0, ord('v')].item() == 0.0
    assert torch.isinf(out2[0, ord('{')])
    assert torch.isinf(out2[0, 200])
    assert torch.isinf(out2[0, 208])
    assert proc.n_steps == 2
    assert proc.n_interventions == 2


def test_processor_history_fold_incremental_and_resync() -> None:
    import torch
    proc = processor_class()(_machine(), prompt_len=1)
    proc(torch.tensor([[7, 200]]), _scores())          # 生成'{"'
    assert proc.machine.state[1] == "root"
    proc(torch.tensor([[7, 200, 118]]), _scores())     # 增量+1: 'v'
    assert proc.machine.state[2] == (('erdict": "', 'verdict'),)
    # 一次跳变+2: 增量fold两条, 状态仍正确
    proc(torch.tensor([[7, 200, 118, 101, 114]]), _scores())
    assert proc.machine.state[1] == "root"
    assert proc.machine.state[2] == (('dict": "', 'verdict'),)
    # 历史变短(不应发生): reset+全量重fold
    proc(torch.tensor([[7, 200, 118]]), _scores())
    assert proc.machine.state[2] == (('erdict": "', 'verdict'),)


def test_processor_mask_deterministic_across_instances() -> None:
    import torch
    outs = []
    for _ in range(2):
        proc = processor_class()(_machine(), prompt_len=1)
        scores = _scores()
        proc(torch.tensor([[7, 200]]), scores)
        proc(torch.tensor([[7, 200, 118]]), scores)
        outs.append(scores.clone())
    assert torch.equal(outs[0], outs[1])


def test_processor_unsupported_input_ids_shape() -> None:
    proc = processor_class()(_machine(), prompt_len=1)
    with pytest.raises(TypeError, match="input_ids形态"):
        proc("not-a-tensor", _scores())


# ── 5. GPU端到端(slow): 贪心复跑同结果 ──────────────────────────────────


@pytest.mark.slow
@pytest.mark.skipif(not (ADAPTER / "adapter_config.json").exists()
                    or not (TOKENIZER_DIR / "tokenizer.json").exists(),
                    reason="d3_student_v2b/qwen3-1.7b缺失")
def test_constrained_generate_deterministic_on_gpu() -> None:
    import torch
    if not torch.cuda.is_available():
        pytest.skip("无CUDA")
    from tools import eval_d3_student
    eval_d3_student._ADAPTER = str(ADAPTER)
    model, tokenizer = eval_d3_student._load()
    row = json.loads(
        (BASE / "data/gjb_438c/localization_gold"
         / "violation_evalset_v1.jsonl").read_text(
             encoding="utf-8").splitlines()[0])
    evidences = [str(e["text"]) for e in row["evidence"]]
    messages = [
        {"role": "system", "content": eval_d3_student._SYSTEM},
        {"role": "user", "content": eval_d3_student._user_message(
            str(row["question"]), str(row["answer"]), evidences)}]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=False)
    results = [constrained_generate(
        model, tokenizer, prompt, str(row["answer"]), evidences)
        for _ in range(2)]
    assert results[0]["verdict"] == results[1]["verdict"]
    assert results[0]["issues"] == results[1]["issues"]
    assert results[0]["content"] == results[1]["content"]
    assert results[0]["verdict"] in VERDICTS
    assert results[0]["parse_fail"] is False
    assert results[0]["constraint_log"]["completed"] is True
    log = results[0]["constraint_log"]
    assert log["steps"] == log["n_new_tokens"]
    assert log["interventions"] <= log["steps"]


# build_skeleton_grammar被直接使用的构建不变量校验
def test_grammar_build_invariants() -> None:
    grammar = build_skeleton_grammar()
    assert set(grammar) == {
        "root", "verdict", "after_verdict", "arr", "quote_str",
        "after_quote", "span_open", "span1", "num_comma", "span2",
        "after_span2", "after_null", "rule_str", "after_rule",
        "eref_str", "after_eref", "expl_str", "item_close",
        "arr_tail", "eos"}
    for name, node in grammar.items():
        succs = [s for _, s in node.cands] + (
            [node.succ] if node.succ else [])
        for succ in succs:
            assert succ in grammar, f"{name}->{succ}悬空"
