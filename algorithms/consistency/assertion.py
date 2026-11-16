r"""断言性测试(M88): claim是否为可判定的命题单元.

蒸馏切分器(tools/claim_segmenter.py)产出的原子claim中混有裸名词/裸
动词片段(如"添加""修改""查询"), 它们不是可判定的命题——NLI残差通道
判NIE(非断言无法判定), strict∀聚合下一票否决answer级support
(M82 C / M87 D2: distilled+strict在test46的support预测0条). 断言感知
聚合在跨claim聚合前过滤这些非断言claim, 只让真正的命题单元投票.

判定规则(claim_text + method, 按序):
  1. typed通道方法标记(method含identifier/enum/numeric/quote/
     closed_scope): 类型化claim(numeric/enum/identifier/quoted)构造
     上就是断言;
  2. 长描述(去空白后≥12字): 默认含谓词结构;
  3. 中文谓词lexicon命中(支持/提供/包括/为/是/有/使用/插入/...):
     带谓词-论元结构的短句;
  4. 裸词片段(去空白后≤4字): 一律非断言(单个名词/动词不是命题,
     即使该词本身在lexicon中, 如"添加"单独出现).

纯文本判定入口 :func:`is_assertive_text`; ClaimResult判定入口
:func:`is_assertive_claim` (qa_module以 ``_is_assertive_claim`` 导入).
本层是确定性纯函数: 无I/O, 无模型调用. 单字谓词(为/是/有/可/应/无)
可能误命中复合词(应用/行为/可能), 但误命中只发生在真实描述句上,
裸词卫兵保证裸名词片段仍被正确过滤.
"""
from __future__ import annotations

import re

from algorithms.consistency.qa_models import ClaimResult

#: 中文谓词lexicon: 系词/存在/情态 + 常见SRS动作/数据操作谓词.
#: 多字谓词按长度降序排列(对boolean search无影响, 便于维护).
_PREDICATE_LEXICON: tuple[str, ...] = (
    # 任务书给定的谓词集(支持/提供/包括/为/是/有/使用/运行/允许/要求/
    # 应/可/执行/完成/存在/返回/保存/处理/部署/沿用/提供并使用)
    "提供并使用", "支持", "提供", "包括", "包含", "使用", "运行", "允许",
    "要求", "执行", "完成", "存在", "返回", "保存", "处理", "部署", "沿用",
    # 常见SRS声明谓词(扩展)
    "实现", "具备", "采用", "适用于", "用于", "组成", "构成", "分为",
    # 数据操作谓词(裸词出现由长度卫兵排除, 句内出现=带宾语结构)
    "插入", "删除", "添加", "修改", "查询", "存储", "获取", "初始化",
    # 单字系词/存在/情态(误命中风险见模块docstring)
    "为", "是", "有", "无", "可", "应",
)

_ASSERTIVE_PREDICATE_RE = re.compile("|".join(_PREDICATE_LEXICON))

#: typed通道方法标记: method含其一即视为类型化claim(构造上是断言)
_TYPED_METHOD_MARKERS: tuple[str, ...] = (
    "identifier",    # identifier_exact_match
    "enum",          # explicit_enum_exclusion
    "numeric",       # numeric_interval
    "quote",         # explicit_quote_polarity / quoted
    "closed_scope",  # closed_scope_exclusion (quoted通道封闭scope路径)
)

#: 长描述阈值: 去空白≥该长度的claim默认含谓词结构
_LONG_CLAIM_LEN = 12

#: 裸词片段阈值: 去空白≤该长度的是单个名词/动词/编号, 不是命题
_BARE_FRAGMENT_MAX_LEN = 4

_WS_RE = re.compile(r"\s+")


def is_assertive_text(text: str) -> bool:
    """纯文本断言性判定(谓词lexicon / 长句 / 裸词卫兵)."""
    compact = _WS_RE.sub("", text)
    if not compact:
        return False
    if len(compact) >= _LONG_CLAIM_LEN:
        return True
    if len(compact) <= _BARE_FRAGMENT_MAX_LEN:
        return False
    return bool(_ASSERTIVE_PREDICATE_RE.search(compact))


def is_assertive(text: str, method: str = "") -> bool:
    """claim_text+method断言性判定.

    ``method`` 可以是ClaimResult.method(通道方法名)或AnswerClaim.kind
    (typed提取时的kind与通道方法名同词根), 两者共享同一组typed标记.
    """
    if any(marker in method for marker in _TYPED_METHOD_MARKERS):
        return True
    return is_assertive_text(text)


def is_assertive_claim(result: ClaimResult) -> bool:
    """ClaimResult断言性判定(qa_module聚合侧入口)."""
    return is_assertive(result.claim_text, result.method)


__all__ = [
    "is_assertive",
    "is_assertive_claim",
    "is_assertive_text",
]
