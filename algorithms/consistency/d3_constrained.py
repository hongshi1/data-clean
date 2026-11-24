"""D3学生生成端约束解码(X1): 自研trie式LogitsProcessor, 零新依赖.

实证动机(docs/srs_project/102_x1_constrained_decoding_spec.md):
  - tools/eval_d3_student.py的无verdict默认NIE掩盖了JSON结构失败;
    _parse()的三级抢救(strip think→fenced提取→raw_decode扫描)说明
    结构失败是常态而非异常;
  - 环境只有transformers 5.17 + torch 2.11(无outlines/xgrammar/vllm),
    按96号§4的结论(2609.23742: 约束解码消除0.6B-4B模型的结构失败)
    自研token级掩码, 不引入新依赖.

三层设计(102号规格):
  1. verdict枚举trie: "support"|"refute"|"not_in_evidence"三值强制;
  2. JSON骨架约束: 与训练目标(tools/train_d3_student._target_message
     的json.dumps紧凑格式)逐字一致的骨架
       {"verdict": E, "issues": [I, I, ...]}
       I = {"quote": S, "span": [N, N]|null, "rule_id": S,
            "evidence_ref": S, "explanation": S}
     key名与结构token级强制; 字符串值S自由生成, 仅排除会破坏
     json.loads严格合法性的token(含"/含\\/含控制字符/特殊token/
     字节回退token);
  3. 后验对齐: quote⊂answer字面 / span区间 / evidence_ref索引机械
     校验, 不合格issue标诊断flag(不删除, 不默认NIE).

BPE处理(关键决策): FSM按**字符级**推进, 掩码与消费都用"token全文
能否从当前骨架位置逐字符合法走完"判定——这覆盖跨状态边界的BPE
合并token(如Qwen真实词表中' [{'一个token横跨issues数组开括号+
item开括号+引号), 教师标签目标JSON的自然BPE切分全程零强制
(tests/test_d3_constrained.py的真实tokenizer走查锁定该性质).
允许集计算按状态缓存: choice/num用首字符索引收集候选再全文走查
过滤, str状态直接并上预计算的free集; 掩码后合法集恒非空
(byte-level BPE基础字母表保证每个骨架字符有单字符token出口),
无死锁.

数字护栏: 数值未开写时只允许数字token(排除'[,]'); 首数字是
单独的0时锁出口(排除'[01, 2]'); 前导零多位token('05')直接
不入digit集——掩码层面排除json.loads非法形式.

确定性: FSM为纯Python无torch; 处理器状态从input_ids历史增量fold
(纯函数式), 掩码只置-inf不重排——贪心解码下复跑同结果.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # 仅类型标注用, 运行时零重依赖(遵循nli_local惯例)
    from transformers import PreTrainedModel, PreTrainedTokenizerBase

__all__ = [
    "VERDICTS",
    "VocabIndex",
    "SkeletonMachine",
    "build_skeleton_grammar",
    "align_issues",
    "constrained_generate",
    "processor_class",
]

#: verdict三值(与tools/d3_teacher_labels.VERDICTS一致)
VERDICTS: tuple[str, ...] = ("support", "refute", "not_in_evidence")

#: 生成结束的特殊token文本(HF tokenizer缺哪个跳哪个)
_EOS_TOKEN_TEXTS: tuple[str, ...] = ("<|im_end|>", "<|endoftext|>")

_ASCII_DIGITS = frozenset("0123456789")


# ── byte-level BPE文本反解 ──────────────────────────────────────────────


def _bytes_to_unicode() -> dict[int, str]:
    """GPT-2字节→unicode映射(Qwen同款): 33-126/161-172(含¬)/
    174-255直映, 其余字节(0-32/127-160/173)映射到256+n起.
    词表BPE符号经此表反解回真实文本."""
    bs = (list(range(33, 127)) + list(range(161, 173))
          + list(range(174, 256)))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


_UNI_TO_BYTE = {u: b for b, u in _bytes_to_unicode().items()}


def _decode_bpe(bpe: str) -> str | None:
    """单个BPE符号→真实文本; 字节回退/非映射符号返回None(禁止)."""
    try:
        return bytes(_UNI_TO_BYTE[ch] for ch in bpe).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return None


# ── 词表文本倒排索引 ────────────────────────────────────────────────────


class VocabIndex:
    """词表文本索引: 骨架前缀匹配与自由文本合法性判定的唯一依据.

    属性:
      texts: id→真实文本(None=字节回退等无法严格utf-8解码的token)
      by_text: 文本→id列表(等值查询)
      by_first_char: 首字符→id列表(allowed集的候选收集)
      quote_ids: 文本含引号的token(str状态的出口候选)
      free_ids: 可作JSON字符串内容的token(无引号/反斜杠/控制字符,
        且非added特殊token——否则模型可在字符串值里吐<|im_start|>)
      digit_ids: 纯ASCII数字token且为合法JSON数(排除"00"/"05"等
        带前导零的多位形式, json.loads不接受)
      eos_ids: 结束token集合
    """

    __slots__ = ("texts", "by_text", "by_first_char", "quote_ids",
                 "free_ids", "digit_ids", "eos_ids")

    def __init__(self, texts: dict[int, str | None],
                 eos_ids: set[int]) -> None:
        self.texts: dict[int, str | None] = dict(texts)
        self.eos_ids: frozenset[int] = frozenset(eos_ids)
        by_text: dict[str, list[int]] = {}
        by_first: dict[str, list[int]] = {}
        quote_ids: set[int] = set()
        free: set[int] = set()
        digits: set[int] = set()
        for tid, text in self.texts.items():
            if text is None:
                continue
            by_text.setdefault(text, []).append(tid)
            by_first.setdefault(text[0], []).append(tid)
            if '"' in text:
                quote_ids.add(tid)
            if text and all(
                    c not in ('"', "\\") and ord(c) >= 0x20 for c in text):
                free.add(tid)
            if text and text[0] in _ASCII_DIGITS \
                    and all(c in _ASCII_DIGITS for c in text) \
                    and (len(text) == 1 or text[0] != "0"):
                digits.add(tid)
        self.by_text: dict[str, list[int]] = by_text
        self.by_first_char: dict[str, list[int]] = by_first
        self.quote_ids: frozenset[int] = frozenset(quote_ids)
        self.free_ids: frozenset[int] = frozenset(free)
        self.digit_ids: frozenset[int] = frozenset(digits)

    @classmethod
    def from_texts(cls, texts: dict[int, str | None],
                   eos_ids: set[int],
                   added: set[int] = frozenset()) -> VocabIndex:
        """显式文本映射构造(测试注入用, 不触tokenizer).

        added: 特殊token id集合——从texts剔除, 保证其不进free/digit
        (与from_tokenizer的added排除行为一致).
        """
        filtered = {tid: text for tid, text in texts.items()
                    if tid not in added}
        return cls(filtered, eos_ids)

    @classmethod
    def from_tokenizer(cls, tokenizer: PreTrainedTokenizerBase) -> VocabIndex:
        """从HF tokenizer构建: BPE符号反解 + added特殊token排除."""
        vocab: dict[str, int] = tokenizer.get_vocab()
        added = set(tokenizer.get_added_vocab().values())
        texts: dict[int, str | None] = {}
        for bpe, tid in vocab.items():
            if tid in added:
                continue          # 特殊token不参与骨架/自由文本匹配
            texts[tid] = _decode_bpe(bpe)
        eos: set[int] = set()
        for name in _EOS_TOKEN_TEXTS:
            tid = tokenizer.convert_tokens_to_ids(name)
            if tid is not None:
                eos.add(tid)
        if tokenizer.eos_token_id is not None:
            eos.add(int(tokenizer.eos_token_id))
        return cls(texts, eos)


# ── 骨架FSM ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Node:
    """骨架状态节点. kind ∈ choice|str|num|eos.

    choice: cands=((待匹配串, 后继状态名), ...), 随部分消费而收缩;
    str/num: succ=出口choice状态名(自由内容结束后进入其全量模板候选);
    eos: 只允许结束token.
    """
    kind: str
    cands: tuple[tuple[str, str], ...] = ()
    succ: str = ""


def build_skeleton_grammar() -> dict[str, _Node]:
    """D3输出JSON骨架FSM(与训练目标紧凑格式逐字一致).

    状态图: root→verdict枚举→issues数组(arr)→item五字段→
    arr_tail(逗号续写|]}收尾)→eos. 构建时校验两条不变量:
      1. 同一choice状态的候选互不为前缀(消费无歧义);
      2. 所有后继状态存在.
    """
    lit_root = '{"verdict": "'
    lit_after_verdict = '", "issues": ['
    item_open = '{"quote": "'
    item_sep = ', {"quote": "'
    lit_after_quote = '", "span": '
    lit_after_span2 = '], "rule_id": "'
    lit_after_null = ', "rule_id": "'
    lit_after_rule = '", "evidence_ref": "'
    lit_after_eref = '", "explanation": "'
    item_close = '"}'
    grammar: dict[str, _Node] = {
        "root": _Node("choice", ((lit_root, "verdict"),)),
        "verdict": _Node("choice",
                         tuple((v, "after_verdict") for v in VERDICTS)),
        "after_verdict": _Node("choice", ((lit_after_verdict, "arr"),)),
        "arr": _Node("choice", ((item_open, "quote_str"), ("]}", "eos"))),
        "quote_str": _Node("str", succ="after_quote"),
        "after_quote": _Node("choice", ((lit_after_quote, "span_open"),)),
        "span_open": _Node("choice", (("[", "span1"), ("null", "after_null"))),
        "span1": _Node("num", succ="num_comma"),
        "num_comma": _Node("choice", ((", ", "span2"),)),
        "span2": _Node("num", succ="after_span2"),
        "after_span2": _Node("choice", ((lit_after_span2, "rule_str"),)),
        "after_null": _Node("choice", ((lit_after_null, "rule_str"),)),
        "rule_str": _Node("str", succ="after_rule"),
        "after_rule": _Node("choice", ((lit_after_rule, "eref_str"),)),
        "eref_str": _Node("str", succ="after_eref"),
        "after_eref": _Node("choice", ((lit_after_eref, "expl_str"),)),
        "expl_str": _Node("str", succ="item_close"),
        "item_close": _Node("choice", ((item_close, "arr_tail"),)),
        "arr_tail": _Node("choice", ((item_sep, "quote_str"), ("]}", "eos"))),
        "eos": _Node("eos"),
    }
    for name, node in grammar.items():
        cands = [c for c, _ in node.cands]
        for a in cands:
            for b in cands:
                if a != b and b.startswith(a):
                    raise ValueError(f"骨架候选前缀歧义: {name}: {a!r}⊂{b!r}")
        succs = [s for _, s in node.cands] + ([node.succ] if node.succ else [])
        for succ in succs:
            if succ not in grammar:
                raise ValueError(f"未知后继状态: {name}->{succ}")
    return grammar


# 运行时状态: (kind, 名称, choice剩余候选, num子状态标记)
#   choice: (剩余候选, "")  str: ((), "")  num: ((), ""|"d"|"z")
#   num标记: ""=未写数字 | "d"=已写≥1个数字 | "z"=首数字是单独的0
_State = tuple[str, str, tuple[tuple[str, str], ...], str]


class SkeletonMachine:
    """骨架FSM运行时: allowed_ids()/consume(tid)驱动, 纯Python无torch.

    num状态的两条防无效JSON护栏(掩码层面排除json.loads非法形式):
      1. 数值未开写(标记"")时只允许数字token——排除`[,]`;
      2. 首数字是单独的0(标记"z")时只允许出口——排除`[01, 2]`.
    另由VocabIndex.digit_ids排除"05"/"00"等带前导零的整token.
    """

    def __init__(self, index: VocabIndex,
                 grammar: dict[str, _Node] | None = None) -> None:
        self.index = index
        self.grammar = grammar if grammar is not None \
            else build_skeleton_grammar()
        self._allowed_cache: dict[_State, frozenset[int]] = {}
        self.state: _State = ("choice", "root",
                              self.grammar["root"].cands, "")

    def reset(self) -> None:
        self.state = ("choice", "root", self.grammar["root"].cands, "")

    @property
    def finished(self) -> bool:
        return self.state[0] == "eos"

    def snapshot(self) -> str:
        """当前状态的可读快照(日志/测试断言用)."""
        kind, name, cands, numflag = self.state
        if kind == "choice":
            rems = "|".join(c for c, _ in cands)
            return f"choice:{name}:{rems}"
        if kind == "num":
            return f"num:{name}:{numflag or '-'}"
        return f"{kind}:{name}"

    def _init_state(self, name: str) -> _State:
        node = self.grammar[name]
        if node.kind == "choice":
            return ("choice", name, node.cands, "")
        if node.kind == "eos":
            return ("eos", "eos", (), "")
        # str/num: 名称槽存出口choice状态名(allowed_ids/consume按它
        # 取出口候选)
        return (node.kind, node.succ, (), "")

    @staticmethod
    def _match_char(cands: tuple[tuple[str, str], ...],
                    ch: str) -> list[tuple[str, str]] | None:
        """choice候选按单字符过滤: 剩余串去掉首字符; 无匹配→None."""
        matched = [(rem[1:], succ) for rem, succ in cands
                   if rem.startswith(ch)]
        return matched or None

    def _advance_char(self, state: _State, ch: str) -> _State | None:
        """单字符推进(纯函数, 不改self.state); 非法字符→None.

        token可跨多个骨架状态边界: consume按token逐字符调用本函数.
        """
        kind, name, cands, numflag = state
        if kind == "eos":
            return None
        if kind == "str":
            if ch != '"' and ch != "\\" and ord(ch) >= 0x20:
                return state               # 自由内容字符
            matched = self._match_char(self.grammar[name].cands, ch)
        elif kind == "num":
            if ch in _ASCII_DIGITS:
                if numflag == "z":
                    return None            # 前导零后不能再接数字
                return ("num", name, (), "z"
                        if numflag == "" and ch == "0" else "d")
            if numflag == "":
                return None                # 数值未开写, 只有数字合法
            matched = self._match_char(self.grammar[name].cands, ch)
        else:
            matched = self._match_char(cands, ch)
        if matched is None:
            return None
        completed = [m for m in matched if not m[0]]
        if completed:
            # 候选互不为前缀(构建时校验)→完成与部分互斥
            return self._init_state(completed[0][1])
        return ("choice", name, tuple(matched), "")

    def _walk_text(self, state: _State, text: str) -> bool:
        """token全文能否从state逐字符合法走完(纯函数)."""
        st = state
        for ch in text:
            nxt = self._advance_char(st, ch)
            if nxt is None:
                return False
            st = nxt
        return True

    def allowed_ids(self) -> frozenset[int]:
        """当前状态下允许的下一个token集合(按状态缓存, 恒非空).

        允许 = 文本能从当前状态逐字符合法走完的全部token(覆盖跨
        状态边界的BPE合并, 如' [{'横跨issues数组开括号+item开括号).
        候选收集按kind分流: str→free集+含引号token; choice/num→
        首字符合法的token(by_first_char), 逐个全文本走查过滤.
        """
        hit = self._allowed_cache.get(self.state)
        if hit is not None:
            return hit
        frozen = frozenset(self._compute_allowed(self.state))
        self._allowed_cache[self.state] = frozen
        return frozen

    def _compute_allowed(self, state: _State) -> set[int]:
        kind, name, cands, numflag = state
        index = self.index
        if kind == "eos":
            return set(index.eos_ids)
        if kind == "str":
            base = set(index.free_ids)
            candidates: set[int] | frozenset[int] = index.quote_ids
        elif kind == "num":
            if numflag == "":
                return set(index.digit_ids)
            exit_firsts = {rem[0] for rem, _
                           in self.grammar[name].cands}
            if numflag == "z":
                firsts: set[str] = exit_firsts
                base = set()
            else:
                firsts = exit_firsts | set("0123456789")
                base = set(index.digit_ids)
            candidates = {tid for ch in firsts
                          for tid in index.by_first_char.get(ch, ())}
        else:
            firsts = {rem[0] for rem, _ in cands}
            candidates = {tid for ch in firsts
                          for tid in index.by_first_char.get(ch, ())}
            base = set()
        for tid in candidates:
            text = index.texts.get(tid)
            if text is not None and self._walk_text(state, text):
                base.add(tid)
        return base

    def consume(self, tid: int) -> None:
        """消费一个生成token并推进状态(逐字符, 允许跨状态边界);
        非法token显式报错(掩码下不应发生——静默吞错会污染科研结论)."""
        kind, name, cands, numflag = self.state
        if kind == "eos":
            # eos token的文本已被added过滤, 先于文本查找判定
            if tid in self.index.eos_ids:
                return
            raise ValueError(f"eos状态不接受token {tid}")
        text = self.index.texts.get(tid)
        if text is None:
            raise ValueError(
                f"token {tid}无真实文本(字节回退/added), 骨架禁止")
        state = self.state
        for ch in text:
            nxt = self._advance_char(state, ch)
            if nxt is None:
                raise ValueError(
                    f"token {tid}({text!r})在{self.snapshot()}"
                    f"的字符{ch!r}处非法")
            state = nxt
        self.state = state


# ── LogitsProcessor(惰性定义: 顶层零重依赖) ────────────────────────────

_PROCESSOR_CLS: type | None = None


def processor_class() -> type:
    """返回SkeletonLogitsProcessor类; 首次调用时import torch/transformers
    并完成类定义(模块顶层保持零重依赖, 与nli_local同惯例)."""
    global _PROCESSOR_CLS
    if _PROCESSOR_CLS is not None:
        return _PROCESSOR_CLS
    import torch
    from transformers import LogitsProcessor

    class SkeletonLogitsProcessor(LogitsProcessor):
        """generate()每步把非法token的logits置-inf; 贪心解码下即强制.

        状态推进: 从input_ids历史增量fold(纯函数式, 与batch/缓存实现
        解耦); 历史回退(长度变短)时全量重fold. n_interventions =
        掩码改变argmax的步数(约束实际干预率的直接计量).
        """

        def __init__(self, machine: SkeletonMachine,
                     prompt_len: int) -> None:
            self.machine = machine
            self.prompt_len = prompt_len
            self.machine.reset()
            self.folded = 0
            self.n_steps = 0
            self.n_interventions = 0
            self._mask_cache: dict[tuple[frozenset[int], str], object] = {}

        def _history(self, input_ids) -> list[int]:
            if isinstance(input_ids, torch.Tensor):
                return input_ids[0].tolist()
            if (isinstance(input_ids, (tuple, list)) and input_ids
                    and isinstance(input_ids[-1], torch.Tensor)):
                return input_ids[-1][0].tolist()
            raise TypeError(
                f"不支持的input_ids形态: {type(input_ids)!r}")

        def _mask(self, allowed: frozenset[int], scores) -> object:
            key = (allowed, str(scores.device))
            mask = self._mask_cache.get(key)
            if mask is None:
                mask = torch.zeros(
                    (1, scores.shape[-1]), dtype=torch.bool,
                    device=scores.device)
                ids = torch.tensor(sorted(allowed), dtype=torch.long,
                                   device=scores.device)
                mask[0].index_fill_(0, ids, True)
                self._mask_cache[key] = mask
            return mask

        def __call__(self, input_ids, scores):  # noqa: ANN001
            # transformers 5.17契约: (batch, seq)完整历史, (batch, vocab)
            ids = self._history(input_ids)
            generated = ids[self.prompt_len:]
            if len(generated) < self.folded:
                self.machine.reset()
                self.folded = 0
            for tid in generated[self.folded:]:
                self.machine.consume(tid)
            self.folded = len(generated)
            allowed = self.machine.allowed_ids()
            raw_argmax = int(scores[0].argmax())
            mask = self._mask(allowed, scores)
            scores.masked_fill_(~mask, -torch.inf)
            if int(scores[0].argmax()) != raw_argmax:
                self.n_interventions += 1
            self.n_steps += 1
            return scores

    _PROCESSOR_CLS = SkeletonLogitsProcessor
    return _PROCESSOR_CLS


# ── 后验对齐(第三层) ────────────────────────────────────────────────────

_EV_REF = re.compile(r"^ev-(\d+)$")


def align_issues(issues: Sequence[object], answer: str,
                 evidences: Sequence[str] | None = None) -> list[dict]:
    """机械校验每个issue的quote/span/evidence_ref, 不删除不修复.

    每个issue追加诊断flag:
      span_verified: span为合法区间且answer[s:e]==quote(区间精确);
      literal_faithful: quote非空且逐字⊂answer;
      span_find_pos: quote在answer中的find定位(span不精确时的修复
        候选, 供下游选择是否采纳; 本函数不回写span);
      evidence_ref_ok: ev-N且1≤N≤len(evidences)(evidences=None时为None).
    """
    out: list[dict] = []
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue = dict(item)
        quote = str(issue.get("quote", ""))
        span = issue.get("span")
        span_exact = False
        if (isinstance(span, list) and len(span) == 2
                and all(isinstance(v, int) and not isinstance(v, bool)
                        for v in span)):
            start, end = span
            span_exact = (0 <= start < end <= len(answer)
                          and answer[start:end] == quote)
        literal = bool(quote) and quote in answer
        find_pos = None
        if literal and not span_exact:
            pos = answer.find(quote)
            find_pos = pos if pos >= 0 else None
        ref = str(issue.get("evidence_ref", ""))
        match = _EV_REF.match(ref)
        if evidences is None:
            ref_ok: bool | None = None
        else:
            ref_ok = bool(match) and 1 <= int(match.group(1)) <= len(evidences)
        issue["span_verified"] = span_exact
        issue["literal_faithful"] = literal
        issue["span_find_pos"] = find_pos
        issue["evidence_ref_ok"] = ref_ok
        out.append(issue)
    return out


# ── 生成入口 ────────────────────────────────────────────────────────────

_MACHINE_CACHE: dict[int, tuple[object, SkeletonMachine]] = {}


def _machine_for(tokenizer: PreTrainedTokenizerBase) -> SkeletonMachine:
    """每个tokenizer实例构建一次(词表索引构建~0.2s, 结果缓存)."""
    key = id(tokenizer)
    hit = _MACHINE_CACHE.get(key)
    if hit is not None and hit[0] is tokenizer:
        return hit[1]
    if len(_MACHINE_CACHE) >= 8:
        _MACHINE_CACHE.clear()
    machine = SkeletonMachine(VocabIndex.from_tokenizer(tokenizer))
    _MACHINE_CACHE[key] = (tokenizer, machine)
    return machine


def constrained_generate(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    prompt: str,
    answer: str,
    evidences: Sequence[str] | None = None,
    max_new_tokens: int = 512,
) -> dict:
    """约束生成一条D3判定(贪心解码+骨架掩码+后验对齐).

    返回:
      verdict: 三值之一; 骨架未走完(截断)时为None——parse_fail=True,
        绝不默认NIE(与无约束路径"结构失败被NIE掩盖"语义区分);
      issues: 五字段+align_issues诊断flag;
      parse_fail: bool(未完成/JSON非法/verdict无效/issues非列表);
      constraint_log: {steps, interventions, completed, n_new_tokens,
        json_error};
      content/elapsed_s: 原始解码文本与时延(诊断用).
    """
    import torch

    machine = _machine_for(tokenizer)
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
    prompt_len = int(inputs["input_ids"].shape[1])
    proc = processor_class()(machine, prompt_len)
    eos_list = sorted(machine.index.eos_ids)
    started = time.perf_counter()
    with torch.no_grad():
        output = model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            temperature=None, top_p=None, top_k=None,
            pad_token_id=tokenizer.eos_token_id or eos_list[0],
            eos_token_id=eos_list, logits_processor=[proc])
    elapsed = time.perf_counter() - started
    new_ids = [int(t) for t in output[0][prompt_len:].tolist()]
    content = tokenizer.decode(new_ids, skip_special_tokens=True)

    completed = proc.machine.finished
    payload: dict = {}
    json_error: str | None = None
    if content.strip():
        try:
            value = json.loads(content)
            if isinstance(value, dict):
                payload = value
            else:
                json_error = "parsed_non_dict"
        except json.JSONDecodeError as exc:
            json_error = f"json_decode_error: {exc.msg}"
    verdict_raw = str(payload.get("verdict", ""))
    verdict = verdict_raw if verdict_raw in VERDICTS else None
    raw_issues = payload.get("issues")
    issues = align_issues(
        raw_issues if isinstance(raw_issues, list) else [], answer, evidences)
    parse_fail = (not completed) or json_error is not None \
        or verdict is None or not isinstance(raw_issues, list)
    return {
        "verdict": verdict,
        "issues": issues,
        "parse_fail": parse_fail,
        "constraint_log": {
            "steps": proc.n_steps,
            "interventions": proc.n_interventions,
            "completed": completed,
            "n_new_tokens": len(new_ids),
            "json_error": json_error,
        },
        "content": content,
        "elapsed_s": round(elapsed, 3),
    }
