"""claim→typed通道桥接 (SRE→SAE对齐修复, 99号方案P1).

问题(data/gjb_438c/distillation/claim_downstream_v2.json): 蒸馏切分器v2
的claim识别F1 0.7041远超正则typed 0.2427, 但裸接入下游macro-F1
0.7496 < 正则0.8047. 原因=Alignment Bottleneck定律(arXiv 2602.10380,
95号§7.1): typed正则claim天然满足SAE(子claim级证据对齐——numeric/
identifier/enum/quoted通道按typed字段粒度对齐证据), 切分器叙事claim只
配到SRE(整claim级证据重复, verify_semantic只能整串精确匹配).

桥接设计(SRE→SAE):
  1. 切分器v2做粗粒度分解(推理核心=claim_segmenter_local, 本地128M);
  2. 对每个切分器claim span运行typed字段抽取(数值/枚举/标识符/引用,
     复用answer_claims的抽取patterns与helpers)——typed通道由此拿到
     子claim级证据对齐;
  3. 未命中任何typed字段的claim回退语义通道(kind="semantic", 走
     verify_semantic既有路径, 与裸切分器claim行为一致);
  4. 无切分输出(空answer/全O解码)回退typed正则decompose_claims
     (严格优于整段单条semantic兜底).

关键决策——attr/主语在answer坐标系解析而非segment局部: 数值attr用
_attribute_before(answer, base+match.start())(48字符窗口), identifier
主语用answer级24字符前缀, quoted否定用answer级12字符前缀. 理由:
与typed正则管线(A_regex, 0.8047)完全同源的主语解析口径——切分器把
attr与值切进不同claim时segment局部解析会丢主语, typed通道的
same_subject证据匹配随之失效; span契约(claim粒度)与主语解析
(answer坐标系)正交, 前者管对齐粒度, 后者管对齐质量.

span契约: 桥接typed claim的span为answer内字符区间(answer坐标),
与AnswerClaim.span契约一致; segment的span[0]即base,
answer[base+i]==segment_text[i](segment_claims的去空白校准契约).

接入: qa_module.QAConsistencyModule(decomposer="distilled_typed")
(默认"typed"不变, 现有论文数字不动).

实证结论(M119, test-46三臂+两变体, runs/eval_claim_typed_bridge_*):
  - 下游: 桥接=裸切分器逐实例一致(strict 0.5789 / assertive 0.7496,
    46例0判决差异)——**未达≥0.8047验收线**;
  - claim识别F1: dev45 0.6975 / d3train600 0.7880(≥0.60达标, 与裸
    切分器0.7041/0.7955几乎无损);
  - 根因(两层, 桥接前提在这份语料上不成立):
    (1) **覆盖层**: 教师原子claim是叙事粒度, typed字段(表格标识符/
        数值)全在切分器O区——5个含ID实例的identifier span覆盖率为
        0.0, 46例桥接只抽出3条typed claim(2 identifier+1 numeric),
        SAE机制无对象可对齐;
    (2) **NLI层**: 叙事原子是子命题片段("LOB数据修改"类裸名词短语),
        NLI残差通道无法entail→semantic_unresolved NIE→strict/
        assertive_strict下一票否决; A_regex靠句级structural claim被
        NLI整句entail拿到006类support(逐claim取证).
  - 变体探索(runs/eval_claim_typed_bridge_variants_*): union(整答案
    typed∪typed span外原子)=0.7496(原子NIE否决抵消typed增益);
    gated(有typed只出typed, 无typed出原子)=0.7459(006类support丢失,
    换来030/087两个FP refute消除). 桥接spec形态是帕累托最优的
    含切分器设计.
  - 结论: 识别F1≥0.60(原子粒度)与下游≥0.8047(typed+句级claim结构)
    在该语料上互斥——修复路径不在claim集构造, 而在Phase 2重训
    (切分器训练目标需含typed字段覆盖+命题完整单元)或D3叙事化重训.

本模块确定性(除切分器模型推理外零模型调用, typed抽取全正则毫秒级);
模块顶层零I/O(切分器惰性加载于claim_segmenter_local). 推理时延:
桥接版test-46全管线25s vs typed版253s(原子片段跳过NLI premise
配对, 反而更快).
"""
from __future__ import annotations

import re
from typing import Any

from algorithms.consistency.answer_claims import (
    _ANSWER_NUMBER,
    _IDENTIFIER,
    _NEGATIVE,
    _NUMERIC_POSTFIX,
    _NUMERIC_PREFIX,
    _NUMERIC_QUESTION_TERMS,
    _QUOTED,
    _attribute_before,
    decompose_claims,
    extract_enum_claims,
    question_numeric_subject,
)
from algorithms.consistency.answer_claims import AnswerClaim
from algorithms.consistency.claim_segmenter_local import segment_claims

#: 桥接默认checkpoint: v2(812 answer训练, claim识别F1 0.7041@dev45)
BRIDGE_SEGMENTER_PATH = "models/segmenter/claim_segmenter_v2"
#: v2弱B置信度门限(与claim_downstream_v2.json的C臂一致, gate=0.75经
#: tools/eval_claim_recognition.py的τ-sweep校准, 非test46标签调参)
BRIDGE_BOUNDARY_GATE = 0.75


def _numeric_claims_from_segment(question: str, answer: str,
                                  text: str, base: int) -> list[AnswerClaim]:
    """segment内数值typed抽取(attr按answer级窗口解析, 同正则管线口径).

    镜像decompose_claims的数值路径(_NUMERIC_PREFIX→_NUMERIC_POSTFIX→
    裸值问句门控), 但finditer域=segment文本, span按base平移到answer坐标.
    """
    numeric_claims: list[tuple[str, str, str, str]] = []
    occupied: list[tuple[int, int]] = []
    for match in _NUMERIC_PREFIX.finditer(text):
        attr = _attribute_before(answer, base + match.start())
        numeric_claims.append((attr, match.group("op"),
                               match.group("value"),
                               match.group("unit") or ""))
        occupied.append(match.span())
    for match in _NUMERIC_POSTFIX.finditer(text):
        if any(match.start() < end and start < match.end()
               for start, end in occupied):
            continue
        op = "以上" if "以上" in match.group("op") else "以下"
        attr = _attribute_before(answer, base + match.start())
        numeric_claims.append((attr, op, match.group("value"),
                               match.group("unit")))
    numeric_question = any(
        term in re.sub(r"\s+", "", question)
        for term in _NUMERIC_QUESTION_TERMS)
    if numeric_question:
        values = list(_ANSWER_NUMBER.finditer(text))
        subject = question_numeric_subject(question)
        explicit_matches = list(_NUMERIC_PREFIX.finditer(text))
        explicit_matches.extend(_NUMERIC_POSTFIX.finditer(text))
        bare_values = [
            value for value in values
            if not any(
                match.start() <= value.start() and value.end() <= match.end()
                for match in explicit_matches)
        ]
        if len(bare_values) == 1 and subject:
            value = bare_values[0]
            numeric_claims.append(
                (subject, "为", value.group("value"), value.group("unit")))
    claims: list[AnswerClaim] = []
    for attr, operator, value, unit in numeric_claims:
        if not attr:
            attr = question_numeric_subject(question)
        claim_text = f"{attr} {operator}{value}{unit}"
        position = text.find(claim_text)
        claims.append(AnswerClaim(
            "numeric", claim_text, attr, operator, value, unit,
            span=(base + position, base + position + len(claim_text))
            if position >= 0 else None))
    return claims


def _quoted_claims_from_segment(answer: str, text: str,
                                base: int) -> list[AnswerClaim]:
    """segment内「」引用typed抽取(否定前缀按answer级12字符窗口)."""
    claims: list[AnswerClaim] = []
    for match in _QUOTED.finditer(text):
        prefix = answer[max(0, base + match.start() - 12):
                        base + match.start()]
        claims.append(AnswerClaim(
            "quoted", match.group(1),
            negative=bool(_NEGATIVE.search(prefix)),
            span=(base + match.start(1), base + match.end(1))))
    return claims


def _enum_claims_from_segment(text: str, base: int) -> list[AnswerClaim]:
    """segment内枚举typed抽取(枚举标记词必须在segment内, 复用helper)."""
    claims: list[AnswerClaim] = []
    for items in extract_enum_claims(text):
        cleaned = [re.split(r"[，,]", item)[0].strip() for item in items]
        cleaned = [item for item in cleaned if len(item) >= 2]
        if len(cleaned) >= 2:
            claim_text = "、".join(cleaned)
            position = text.find(cleaned[0])
            claims.append(AnswerClaim(
                "enum", claim_text,
                span=(base + position, base + position + len(claim_text))
                if position >= 0 else None))
    return claims


def _identifier_claims_from_segment(answer: str, text: str,
                                    base: int) -> list[AnswerClaim]:
    """segment内标识符typed抽取(主语按answer级24字符前缀解析)."""
    claims: list[AnswerClaim] = []
    for identifier in _IDENTIFIER.findall(text):
        position = text.find(identifier)
        prefix = answer[max(0, base + position - 24):base + position]
        cleaned_prefix = re.sub(
            r"[（(「\",，。：:为是*`_~]+", " ", prefix).rstrip()
        subject_match = re.search(
            r"([\u4e00-\u9fffA-Za-z]{2,16})\s*$", cleaned_prefix)
        subject = subject_match.group(1) if subject_match else ""
        claims.append(AnswerClaim(
            "identifier", identifier, attr=subject,
            span=(base + position, base + position + len(identifier))))
    return claims


def bridge_from_segments(question: str, answer: str,
                         segments: list[dict[str, Any]]) -> list[AnswerClaim]:
    """切分器segments → 桥接AnswerClaim序列(纯函数, 无模型调用).

    每个segment: typed抽取(numeric→quoted→enum→identifier, 顺序镜像
    decompose_claims)命中则产出typed claims(该segment的叙事外壳按
    typed管线同款契约让位于typed字段); 全不命中则回退该segment的
    semantic claim(kind="semantic", 携带segment span).

    span缺失的segment(手工构造/上游契约破坏): 先按answer.find恢复
    (与AnswerClaim.span的find回退约定同口径); 恢复失败则保守只出
    semantic claim(text形式)——typed抽取需要可靠的answer坐标基点,
    坐标未知时不冒险(引用/标识符span会错位).
    """
    claims: list[AnswerClaim] = []
    for segment in segments:
        text = str(segment["text"])
        span = segment.get("span")
        if not span and text:
            position = answer.find(text)
            if position >= 0:
                span = [position, position + len(text)]
        if span:
            base = int(span[0])
            typed = (_numeric_claims_from_segment(question, answer, text,
                                                  base)
                     + _quoted_claims_from_segment(answer, text, base)
                     + _enum_claims_from_segment(text, base)
                     + _identifier_claims_from_segment(answer, text, base))
            if typed:
                claims.extend(typed)
            else:
                claims.append(AnswerClaim(
                    kind="semantic", text=text,
                    span=(int(span[0]), int(span[1]))))
        else:
            claims.append(AnswerClaim(kind="semantic", text=text))
    return claims


def bridge_decompose_claims(question: str, answer: str,
                            model_path: str = BRIDGE_SEGMENTER_PATH,
                            boundary_gate: float = BRIDGE_BOUNDARY_GATE
                            ) -> list[AnswerClaim]:
    """qa_module.decompose_claims的桥接替换(签名兼容, 供decomposer接入).

    切分器v2分解(惰性加载本地模型) → 每claim typed字段抽取(SAE);
    无切分输出时回退typed正则decompose_claims. 切分器模型不可用时
    显式抛RuntimeError(不静默降级).
    """
    segments = segment_claims(answer, model_path=model_path,
                              boundary_gate=boundary_gate)
    claims = bridge_from_segments(question, answer, segments)
    if not claims:
        return decompose_claims(question, answer)
    return claims


__all__ = [
    "BRIDGE_BOUNDARY_GATE",
    "BRIDGE_SEGMENTER_PATH",
    "bridge_decompose_claims",
    "bridge_from_segments",
]
