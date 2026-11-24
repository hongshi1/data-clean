"""answer侧逐字锚点(字面忠实修复, 99号Phase 0-E1弱点#1).

e1_template_match/trace_bidirectional_join两通道的文档侧违例(主题错位/
正逆矛盾/锚点失效/同行矛盾)原先把合成断言(拼接文本)当claim_text——不是
answer的逐字子串, E1字面忠实契约answer[span]==text失败(violations-17上
13/23≈0.5652, 10条全部集中于这两个通道), 用户看不到"answer里哪句话被
判定", 可解释性断裂.

本模块把文档侧违例claim锚定到answer关联片段(判定锚点变逐字, 判定逻辑
零变更):

- anchor_span(answer, keys): 违例标识词元(用例名/E1提示文本/追踪章节号)
  在answer中的逐字出现区间——全部命中词元的最小覆盖span(首个命中起点到
  最末命中结尾); 任一词元命中即有锚点, 零命中→None(该违例与answer无
  关联文本, 调用方保持合成断言并如实计入字面不忠实残余——96号§5"定位
  不可逐字锚定"的诚实口径).
- anchor_claim(claim, answer, keys): 锚点改写ClaimResult——claim_text=
  answer[start:end]逐字引用, span=(start, end); 原合成断言移入rationale
  尾部(解释信息不丢弃). verdict/method/confidence/evidence_refs/
  check_item_candidates全部不动.

锚定语义: 文档侧违例本身不依赖answer; 锚点回答"answer里哪句话与该违例
相关"——answer对违例实体(用例/章节/提示文本)的逐字提及. 多个词元命中
同一answer时取最小覆盖span(如trace正逆矛盾的两侧章节号之间的映射断言).

纯函数, 零I/O, import期零副作用.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from algorithms.consistency.qa_models import ClaimResult

__all__ = ["anchor_claim", "anchor_span"]


def anchor_span(answer: str,
                keys: Sequence[str]) -> tuple[int, int] | None:
    """keys在answer中的逐字出现区间(全部命中词元的最小覆盖span).

    每个key取answer中的首次逐字出现(精确find, 不做宽度/空白归一——
    span切片天然满足answer[start:end]逐字契约); 空answer/空key/纯空白
    key跳过; 零命中返回None.
    """
    hits: list[tuple[int, int]] = []
    for key in keys:
        text = str(key).strip()
        if not text:
            continue
        position = answer.find(text)
        if position >= 0:
            hits.append((position, position + len(text)))
    if not hits:
        return None
    return (min(start for start, _ in hits),
            max(end for _, end in hits))


def anchor_claim(claim: ClaimResult, answer: str,
                 keys: Sequence[str]) -> ClaimResult:
    """文档侧违例claim → answer逐字锚点(判定锚点变逐字, 信息不丢弃).

    命中锚点: claim_text=answer[start:end], span=(start, end), 原合成
    断言移入rationale尾部(模板匹配详情/双向join实体对等解释信息保留).
    零命中: 原样返回同一claim(违例与answer无关联文本, 保持合成断言,
    由E1评测如实计入字面不忠实残余).
    """
    span = anchor_span(answer, keys)
    if span is None:
        return claim
    start, end = span
    return replace(
        claim,
        claim_text=answer[start:end],
        span=(start, end),
        rationale=(f"{claim.rationale}；文档侧断言(原合成claim_text, "
                   f"判定锚点已移至answer原文)：{claim.claim_text}"),
    )
