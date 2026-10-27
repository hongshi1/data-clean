"""Legacy string-level answer/evidence adapter; new entry is qa_module.py.

This adapter remains for historical AEE regression only. The new QA module does
not call this pair checker for its verdict; use ``QAConsistencyModule.verify``.

世界假设(exhaustive):
  只有调用方显式传 ``exhaustive=True`` 才允许以缺失作refute；证据来源类型
  (text/table/figure)本身不决定闭世界。多个证据块各自按scope判断。

Legacy aggregation is retained for migration tests and is not the new QA-level
composite-answer policy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from algorithms.consistency.checker import ConsistencyChecker
from algorithms.consistency.entities import get_lexer


@dataclass
class Evidence:
    """用于验证 answer 的一组 SRS 声明(模态转换在上游完成).

    ``type`` 仅描述证据来源及其世界假设；它不是被比较的另一端。
    表格、图片和正文之间的关联属于上游上下文聚合，不由 verify() 判定。
    """

    type: str  # "text" | "table" | "figure"
    claims: list[str]
    source_ref: str  # "doc@table_caption" / "doc@image_caption" / "doc@section"
    exhaustive: bool | None = None  # None=unknown/open; never infer from source type
    scope_id: str = ""
    completeness_proof: str = ""

    def is_exhaustive(self) -> bool:
        """只有证据块显式声明完备时才允许闭世界判断。"""
        return self.exhaustive is True and bool(self.completeness_proof.strip())


@dataclass
class ClaimVerdict:
    """answer侧单条声明的判定明细."""

    claim: str
    claim_type: str  # numeric / quoted / enum / semantic
    status: str  # support / refute / not_in_evidence
    matched_ref: str
    channel: str
    detail: str
    confidence: float


@dataclass
class VerdictResult:
    verdict: str  # support / refute / not_in_evidence
    answer: str
    claims: list[ClaimVerdict] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.0
    solver: str = "verify_v1"


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s))


class Verifier:
    """answer vs SRS证据声明集的三态校验器(消费check()内核)."""

    def __init__(self, checker: ConsistencyChecker | None = None):
        self._ck = checker or ConsistencyChecker()

    # ═══ 公开接口 ═══
    def verify(self, answer: str, evidence: Evidence) -> VerdictResult:
        return self.verify_multi(answer, [evidence])

    def verify_multi(self, answer: str, evidences: list[Evidence]) -> VerdictResult:
        # 多个证据块只是同一 answer 的可选支撑来源，不构成证据之间的比较。
        pool: list[tuple[str, str, bool, str]] = []  # text, ref, closed, scope
        for ev in evidences:
            for c in ev.claims:
                pool.append((c, ev.source_ref, ev.is_exhaustive(),
                             ev.scope_id or ev.source_ref))

        # answer声明分解
        claims = self._decompose(answer)
        verdicts: list[ClaimVerdict] = []
        for ctype, claim_text in claims:
            cv = self._ground(claim_text, ctype, pool)
            verdicts.append(cv)
        if not verdicts:
            return VerdictResult("not_in_evidence", answer, [], [], 0.0)

        # 聚合: 矛盾主导
        statuses = [cv.status for cv in verdicts]
        if "refute" in statuses:
            verdict = "refute"
        elif "not_in_evidence" in statuses:
            verdict = "not_in_evidence"
        else:
            verdict = "support"
        refs = sorted({cv.matched_ref for cv in verdicts if cv.matched_ref})
        conf = min(cv.confidence for cv in verdicts)
        return VerdictResult(verdict, answer, verdicts, refs, conf)

    # ═══ answer声明分解(类型路由) ═══
    def _decompose(self, answer: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        # 引号声明
        for q in re.findall(r"[「]([^「」]{2,40})[」]", answer):
            out.append(("quoted", q))
        # 数值声明(checker内核提取器; 空格分隔防破坏再提取)
        for attr, op, val, unit in self._ck._extract_numeric(answer):  # noqa: SLF001
            out.append(("numeric", f"{attr} {op}{val}{unit}"))
        # 枚举声明(顿号列表≥2项; 末项吸收的尾部子句在逗号处截断)
        for items in self._ck._lists_of(answer):  # noqa: SLF001
            cleaned = [re.split(r"[，,]", it)[0].strip() for it in items]
            cleaned = [it for it in cleaned if len(it) >= 2]
            if len(cleaned) >= 2:
                out.append(("enum", "、".join(cleaned)))
        # 语义声明: 仅当无结构化声明时整句兜底(避免同声明双重判定)
        if not out:
            sent = [s.strip() for s in re.split(r"[。；]", answer) if s.strip()]
            if sent:
                out.append(("semantic", max(sent, key=len)))
        return out

    # ═══ 单声明grounding ═══
    def _ground(self, claim: str, ctype: str,
                pool: list[tuple[str, str, bool, str]]) -> ClaimVerdict:
        if ctype == "numeric":
            return self._ground_numeric(claim, pool)
        if ctype == "quoted":
            return self._ground_existence(claim, pool)
        if ctype == "enum":
            return self._ground_enum(claim, pool)
        return self._ground_semantic(claim, pool)

    def _ground_numeric(self, claim: str, pool) -> ClaimVerdict:
        """数值声明: L2属性对齐 → 对齐对喂check()内核."""
        ans_nums = self._ck._extract_numeric(claim)  # noqa: SLF001
        best = None
        for ev_text, ref, _closed, _scope in pool:
            ev_nums = self._ck._extract_numeric(ev_text)  # noqa: SLF001
            for a_attr, a_op, a_val, a_unit in ans_nums:
                for e_attr, e_op, e_val, e_unit in ev_nums:
                    if self._ck._attrs_match(a_attr, e_attr):  # noqa: SLF001
                        r = self._ck.check(claim, ev_text)  # noqa: SLF001
                        if best is None or r.confidence > best[1].confidence:
                            best = (ref, r, ev_text)
        if best:
            ref, r, ev_text = best
            # The checker may fall through to binary NLI when its deterministic
            # numeric rules cannot prove a relation. Neither binary result is a
            # claim-level proof in that case.
            if r.channel == "nli":
                return ClaimVerdict(claim, "numeric", "not_in_evidence", ref,
                                    "nli", "数值内核未匹配；二分类NLI不能证明数值蕴含/反证",
                                    min(r.confidence, 0.5))
            status = "support" if r.verdict == "consistent" else "refute"
            return ClaimVerdict(claim, "numeric", status, ref,
                                r.channel, f"内核判定:{r.evidence[:60]}", r.confidence)
        # 无对齐: 闭世界=表格有该参数行但值不可比→保守NIE
        return ClaimVerdict(claim, "numeric", "not_in_evidence", "",
                            "align", "证据池无同属性数值声明", 0.6)

    @staticmethod
    def _closed_scope_refs(pool: list[tuple[str, str, bool, str]]) -> list[str]:
        """Only a wholly closed, single-scope pool can prove absence.

        This legacy string-only adapter cannot safely align a claim to one of
        several scopes, so mixed or partial pools conservatively stay open.
        """
        if not pool or not all(closed and scope for _text, _ref, closed, scope in pool):
            return []
        scopes = {scope for _text, _ref, _closed, scope in pool}
        if len(scopes) != 1:
            return []
        return sorted({ref for _text, ref, _closed, _scope in pool if ref})

    def _ground_existence(self, claim: str, pool) -> ClaimVerdict:
        """存在性声明「X」: X∈证据池(L0精确/L1同义/子串)."""
        lexer = get_lexer()
        claim_n = _norm(claim)
        for ev_text, ref, _closed, _scope in pool:
            ev_n = _norm(ev_text)
            if claim_n in ev_n:
                return ClaimVerdict(claim, "quoted", "support", ref,
                                    "exact", f"「{claim}」在证据中命中", 1.0)
        # L1同义(K1)
        for ev_text, ref, _closed, _scope in pool:
            ev_n = _norm(ev_text)
            for seg in re.split(r"[、，,。；「」\s]", ev_text):
                seg = seg.strip()
                if len(seg) >= 2 and lexer.align(claim, seg):
                    return ClaimVerdict(claim, "quoted", "support", ref,
                                        "k1_alias", f"K1同指:「{claim}」~「{seg}」", 0.9)
        closed_refs = self._closed_scope_refs(pool)
        if closed_refs:
            return ClaimVerdict(claim, "quoted", "refute", closed_refs[0],
                                "closed_scope", f"「{claim}」在显式封闭证据范围内未命中", 0.7)
        return ClaimVerdict(claim, "quoted", "not_in_evidence", "",
                            "existence", f"「{claim}」未命中；证据范围未声明完备", 0.7)

    def _ground_enum(self, claim: str, pool) -> ClaimVerdict:
        """枚举声明: 逐项grounding, 全命中=support, 缺项按世界假设.

        项切分含逗号(LIST_PAT的项类不排除逗号, 尾部子句会被吸收为末项).
        """
        items = [x.strip() for x in re.split(r"[、，,；。]", claim) if len(x.strip()) >= 2]
        matched_refs: set[str] = set()
        missing: list[str] = []
        for item in items:
            item_norm = _norm(item)
            refs = [ref for text, ref, _closed, _scope in pool
                    if item_norm in _norm(text)]
            if refs:
                matched_refs.update(ref for ref in refs if ref)
            else:
                missing.append(item)
        if not missing:
            return ClaimVerdict(claim, "enum", "support",
                                ",".join(sorted(matched_refs)), "enum",
                                f"枚举{len(items)}项全部命中", 1.0)
        closed_refs = self._closed_scope_refs(pool)
        status = "refute" if closed_refs else "not_in_evidence"
        return ClaimVerdict(claim, "enum", status,
                            ",".join(closed_refs) if closed_refs else "", "enum",
                            f"缺失{len(missing)}项: {'、'.join(missing[:4])}", 0.8)

    def _ground_semantic(self, claim: str, pool) -> ClaimVerdict:
        """语义声明: NLI三态兜底(证据为premise, answer为hypothesis)."""
        if not pool:
            return ClaimVerdict(claim, "semantic", "not_in_evidence", "",
                                "semantic", "证据池为空", 0.5)
        # L3: 词面重合选top-1证据
        def overlap(a: str, b: str) -> float:
            ga = {a[i:i + 2] for i in range(len(a) - 1)}
            gb = {b[i:i + 2] for i in range(len(b) - 1)}
            return len(ga & gb) / max(len(ga | gb), 1)
        best = max(pool, key=lambda t: overlap(claim, t[0]))
        ev_text, ref, _closed, _scope = best
        ov = overlap(claim, ev_text)
        # NLI兜底(证据→answer蕴含)
        r = self._ck._check_nli(ev_text, claim)  # noqa: SLF001
        # The legacy NLI head is binary; neither class distinguishes neutral from entailment/contradiction.
        return ClaimVerdict(claim, "semantic", "not_in_evidence", "",
                            "semantic", f"legacy二分类NLI({r.verdict})不能区分neutral；词面相关度{ov:.2f}也不是反证",
                            min(r.confidence, 0.5))
