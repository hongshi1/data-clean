"""Task 1 v4.1: 域约定领域知识条件化的通道分派一致性判别.

通道(按序):
  1. numeric   领域等价约定数值判定: 操作符族规范化+单位归一(同值异表面=consistent)
  2. quote     引号恒等: 「」引用的约束集合相同 → consistent (T1/T2/T3表面归一)
  3. term      K1术语消解: 同义异名 → TERM-01
  4. enum      枚举集合比对: 集合差 → TERM-03 / 集合等 → consistent
  5. verify    证据核验(evidence_units提供时)
  6. nli       v12模型兜底

v4.1修复(相对v4初版):
  - 负向句式预处理: 剔除「没有/未/不含「X」」的负向引用, 防止负向值误匹配
  - 复合单位fallback: 未知单位(字/秒等)以单位字符串为族名, 同串可比
  - 算子族补全: 不低于/不高于
  - 引号恒等通道: TERM-02/ENUM-02(term_same/enum_same)不再落入NLI被误报
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from algorithms.consistency.templates import (
    get_template,
    normalize_op,
    normalize_unit,
)

BASE = Path(__file__).resolve().parents[2]


@dataclass
class CheckResult:
    verdict: str
    item: str
    type: str
    channel: str    # numeric / quote / term / enum / verify / nli
    evidence: str
    confidence: float
    solver: str
    fallback: bool = False


# ═══ K3: 域约定知识(算子族/单位族/归一 → templates.py单一事实源) ═══

# 同义词表(K1实体消解)
SYNONYMS = {
    "获取": ["采集", "引接"], "传输": ["传送", "转发"],
    "查询": ["检索"], "监控": ["监视"], "存储": ["保存"],
    "处理": ["运算"], "删除": ["移除"], "修改": ["变更"],
    "添加": ["增加"], "导入": ["引入"], "导出": ["输出"],
}
_REV_SYN = {v: k for k, vs in SYNONYMS.items() for v in vs}

# 负向引用模式: 「没有/未/不含「X」」→ 剔除X的引用(防负向值误匹配)
NEG_QUOTE_PAT = re.compile(r"(?:没有|未|不含)[^。；]{0,4}[「]([^「」]+)[」]")

STOP_ATTRS = ("系统", "文档", "该", "本", "功能", "支持", "需要", "要求", "至少", "最多")


def strip_negation(text: str) -> str:
    """剔除负向引用span(「没有「X」」→ ''), 防止负向值进入claims/quotes."""
    return NEG_QUOTE_PAT.sub(" ", text)


class ConsistencyChecker:
    """Legacy pair-level comparison kernels.

    Use ``algorithms.consistency.qa_module.QAConsistencyModule`` for the
    post-retrieval QA task. This class does not consume question or a frozen
    evidence context and its binary NLI result is not a three-state QA verdict.
    """

    DEFAULT_NLI_DIR = "models/nli/roberta-v12-anchor"

    def __init__(self, nli_dir: str | Path | None = None):
        self._nli = None
        self._nli_results: list[CheckResult] = []
        self._nli_dir = Path(nli_dir) if nli_dir else BASE / self.DEFAULT_NLI_DIR

    def check(self, premise: str, hypothesis: str,
              evidence_units: list[str] | None = None) -> CheckResult:
        p = strip_negation(premise)
        h = strip_negation(hypothesis)
        # v4.3次序: numbered(编号条目顺序)在enum前——enum的碎片级比对
        # 无法覆盖条目级顺序对调(ORDER_CONFLICT), 且其consistent判定
        # 是局部证据不能截胡(诊断: B族17/67误判源于此)
        for fn in (self._check_numeric, self._check_quote, self._check_term,
                   self._check_count, self._check_doc_absence,
                   self._check_numbered, self._check_enum, self._check_sequence):
            r = fn(p, h)
            if r:
                return r
        r = self._check_verify(premise, hypothesis, evidence_units)
        if r:
            return r
        return self._check_nli(premise, hypothesis)

    def check_batch(self, pairs: list[tuple[str, str]],
                    evidence: list[list[str] | None] | None = None) -> list[CheckResult]:
        """批量: 确定性通道逐对, NLI兜底批量推理(速度优化)."""
        results: list[CheckResult | None] = [None] * len(pairs)
        nli_idx = []
        if evidence is None:
            evidence = [None] * len(pairs)
        for i, ((prem, hyp), ev) in enumerate(zip(pairs, evidence, strict=True)):
            p, h = strip_negation(prem), strip_negation(hyp)
            for fn in (self._check_numeric, self._check_quote, self._check_term,
                       self._check_count, self._check_doc_absence,
                       self._check_numbered, self._check_enum, self._check_sequence):
                r = fn(p, h)
                if r:
                    results[i] = r
                    break
            else:
                r = self._check_verify(prem, hyp, ev)
                if r:
                    results[i] = r
                else:
                    nli_idx.append(i)
        # NLI批量
        if nli_idx:
            self._nli_batch([(pairs[i][0], pairs[i][1]) for i in nli_idx])
            for j, i in enumerate(nli_idx):
                results[i] = self._nli_results[j]
        return [r for r in results if r is not None]

    # ═══ 通道1: 数值(领域等价约定) ═══
    # K2: 模式由模板库提供(templates.py单一事实源)
    NUM_PAT_PREFIX = get_template("numeric_prefix").pattern
    NUM_PAT_POSTFIX = get_template("numeric_postfix").pattern

    def _check_numeric(self, p: str, h: str) -> CheckResult | None:
        p_claims = self._extract_numeric(p)
        h_claims = self._extract_numeric(h)
        if not p_claims or not h_claims:
            return None

        for pc_attr, pc_op, pc_val, pc_unit in p_claims:
            for hc_attr, hc_op, hc_val, hc_unit in h_claims:
                if not self._attrs_match(pc_attr, hc_attr):
                    continue
                pc_norm = normalize_unit(pc_val, pc_unit)
                hc_norm = normalize_unit(hc_val, hc_unit)
                pc_fam = normalize_op(pc_op)
                hc_fam = normalize_op(hc_op)

                if pc_norm and hc_norm and pc_norm[1] == hc_norm[1]:
                    if abs(pc_norm[0] - hc_norm[0]) < 0.01:
                        # 同值 → 检查操作符族
                        if pc_fam and hc_fam and pc_fam != hc_fam:
                            return CheckResult(
                                "inconsistent",
                                f"操作符矛盾: {pc_op}{pc_val}{pc_unit} vs {hc_op}{hc_val}{hc_unit}",
                                "PARAM-06", "numeric",
                                f"同值({pc_val})但操作符族不同({pc_fam} vs {hc_fam})",
                                0.95, "numeric_kD")
                        # 同值同族 → consistent(领域等价约定: 同值异表面)
                        return CheckResult(
                            "consistent", "", "PARAM-02", "numeric",
                            f"单位归一后同值: {pc_val}{pc_unit} = {hc_val}{hc_unit}",
                            1.0, "numeric_kD")
                    elif pc_fam and hc_fam and pc_fam == hc_fam:
                        # 同参数同族不同值 → PARAM-01
                        return CheckResult(
                            "inconsistent",
                            f"参数「{pc_attr or hc_attr}」: {pc_op}{pc_val}{pc_unit} vs {hc_op}{hc_val}{hc_unit}",
                            "PARAM-01", "numeric",
                            f"同参数不同值: {pc_norm[0]:.1f} vs {hc_norm[0]:.1f}(归一后)",
                            1.0, "numeric_kD")
                elif pc_fam and hc_fam and pc_fam != hc_fam:
                    return CheckResult(
                        "inconsistent",
                        f"操作符矛盾: {pc_op} vs {hc_op}(同参数「{pc_attr or hc_attr}」)",
                        "PARAM-06", "numeric",
                        f"操作符族冲突: {pc_fam} vs {hc_fam}",
                        0.9, "numeric_kD")
        return None

    def _extract_numeric(self, text: str) -> list[tuple[str, str, str, str]]:
        claims = []
        for m in self.NUM_PAT_PREFIX.finditer(text):
            op, val, unit = m.group(1), m.group(2), m.group(3) or ""
            before = text[max(0, m.start() - 20):m.start()]
            attr = self._attr_from_context(before)
            if attr:
                claims.append((attr, op, val, unit))
        for m in self.NUM_PAT_POSTFIX.finditer(text):
            val, unit, post = m.group(1), m.group(2), m.group(3)
            op = "以上" if ("以上" in post or "及以上" in post) else "以下"
            before = text[max(0, m.start() - 20):m.start()]
            attr = self._attr_from_context(before)
            if attr:
                claims.append((attr, op, val, unit))
        return claims

    def _attr_from_context(self, before: str) -> str:
        attr_m = re.search(r"[「]([^「」]{2,15})[」]", before)
        attr = attr_m.group(1).strip() if attr_m else ""
        if not attr:
            attr_m2 = re.search(r"([\u4e00-\u9fa5]{2,8})\s*$", before)
            attr = attr_m2.group().strip() if attr_m2 else ""
        if attr in STOP_ATTRS:
            return ""
        return attr

    def _attrs_match(self, a: str, b: str) -> bool:
        """参数名对齐: 子串包含/同名.

        注意: 词典同义别名不在数值通道对齐——领域约定(TERM-01)要求同一实体
        命名一致, 别名使用本身是术语不一致(由term通道判定), 不能因值相同
        而判consistent(如「内存容量≥20M」vs「缓存大小≥20M」=TERM-01).
        """
        if not a or not b:
            return True
        if a == b or a in b or b in a:
            return True
        ca = _REV_SYN.get(a, a)
        cb = _REV_SYN.get(b, b)
        return ca == cb

    # ═══ 通道2: 引号恒等(表面归一) ═══
    def _check_quote(self, p: str, h: str) -> CheckResult | None:
        p_quotes = set(re.findall(r"[「]([^「」]+)[」]", p))
        h_quotes = set(re.findall(r"[「]([^「」]+)[」]", h))
        if not p_quotes or not h_quotes:
            return None
        if p_quotes == h_quotes:
            # 引用约束集合完全相同 → same claim (领域等价约定: consistent)
            return CheckResult(
                "consistent", "", "P0_QUOTE", "quote",
                f"引号约束集合相同({len(p_quotes)}条): {sorted(p_quotes)[0][:20]}...",
                1.0, "quote_identity")
        return None

    # ═══ 通道3: 术语(K1) ═══
    def _check_term(self, p: str, h: str) -> CheckResult | None:
        """K1实体消解: 声明属性名同义 + 引号术语同指 → TERM-01.

        声明属性检查不依赖引号(数值声明参数名即实体表面).
        """
        from algorithms.consistency.entities import get_lexer
        lexer = get_lexer()
        # 声明属性名同义检测: 数值声明的参数名(如内存容量↔缓存大小)K1同指→TERM-01
        p_claims = self._extract_numeric(p)
        h_claims = self._extract_numeric(h)
        for pc_attr, _, _, _ in p_claims:
            for hc_attr, _, _, _ in h_claims:
                if pc_attr and hc_attr and pc_attr != hc_attr:
                    if pc_attr in hc_attr or hc_attr in pc_attr:
                        continue  # 包含关系=同一参数(宽松)
                    npc = lexer.normalize(pc_attr)
                    nhc = lexer.normalize(hc_attr)
                    if npc == nhc:
                        return CheckResult(
                            "inconsistent",
                            f"参数名「{pc_attr}」vs「{hc_attr}」(同实体异名)",
                            "TERM-01", "term",
                            f"K1词典归一后同为「{npc}」— 命名不一致",
                            0.9, "term_k1_lexicon")
        p_terms = re.findall(r"[「]([^「」]{2,15})[」]", p)
        h_terms = re.findall(r"[「]([^「」]{2,15})[」]", h)
        if not p_terms or not h_terms:
            return None
        for pt in p_terms:
            for ht in h_terms:
                if pt != ht:
                    cp = _REV_SYN.get(pt, pt)
                    ch = _REV_SYN.get(ht, ht)
                    if cp == ch:
                        return CheckResult(
                            "inconsistent",
                            f"术语「{pt}」vs「{ht}」(同义异名)",
                            "TERM-01", "term",
                            f"K1消解后同为「{cp}」但表述不同",
                            0.9, "term_k1")
                    # K1词典: 别名归一后同指(如 RAM↔内存容量)
                    # 护栏: 仅短实体名(≤8字)走词典, 防长引号内容子串误匹配
                    if len(pt) <= 8 and len(ht) <= 8:
                        np_, nh_ = lexer.normalize(pt), lexer.normalize(ht)
                    else:
                        np_, nh_ = pt, ht
                    if np_ == nh_ and pt != ht:
                        return CheckResult(
                            "inconsistent",
                            f"术语「{pt}」vs「{ht}」(词典同指)",
                            "TERM-01", "term",
                            f"K1词典归一后同为「{np_}」",
                            0.9, "term_k1_lexicon")
        return None

    # ═══ 通道4: 枚举集合 ═══
    # 列表模式: 动词(+修饰)(+类别词)(+冒号) 后跟 顿号分隔的列表(至少2项)
    LIST_PAT = re.compile(
        r"(?:包括|包含|涉及)(?:以下|均|都)?(?:元素|功能|节点|内容)?[：:]?\s*"
        r"([^。；、]{2,60}(?:、[^。；、]{2,60})+)")

    # 领域约定无序语境(图元素重排=良性)
    UNORDERED_CTX_PAT = re.compile(r"图|元素|涉及|包含以下")

    def _lists_of(self, text: str) -> list[list[str]]:
        out = []
        for raw in self.LIST_PAT.findall(text):
            cleaned = raw.lstrip("：:、，, ")
            items = [x.strip() for x in cleaned.split("、") if len(x.strip()) >= 2]
            if len(items) >= 2:
                out.append(items)
        return out

    def _check_enum(self, p: str, h: str) -> CheckResult | None:
        p_lists = self._lists_of(p)
        h_lists = self._lists_of(h)
        if not p_lists or not h_lists:
            return None
        # 语境无序约定判定: 图元素/涉及=无序; 功能表/包括=有序(表项次序有语义)
        unordered_ctx = bool(self.UNORDERED_CTX_PAT.search(p) or self.UNORDERED_CTX_PAT.search(h))
        for p_items in p_lists:
            p_set = set(p_items)
            for h_items in h_lists:
                h_set = set(h_items)
                missing = p_set - h_set
                extra = h_set - p_set
                if missing or extra:
                    detail = []
                    if missing:
                        detail.append(f"缺失「{'、'.join(list(missing)[:3])}」")
                    if extra:
                        detail.append(f"多余「{'、'.join(list(extra)[:3])}」")
                    return CheckResult(
                        "inconsistent",
                        f"枚举集合差异: {', '.join(detail)}",
                        "TERM-03", "enum",
                        f"集合差: |P|={len(p_set)}, |H|={len(h_set)}",
                        1.0, "enum_set")
                # 集合相等
                if p_items == h_items or unordered_ctx:
                    # 同序 或 无序语境 → consistent
                    return CheckResult(
                        "consistent", "", "P0_ENUM", "enum",
                        f"枚举集合相等({len(p_set)}项, {'同序' if p_items == h_items else '无序语境'})",
                        1.0, "enum_set")
                # 同集异序 + 有序语境 → 不判, 留给NLI(领域约定: 表项次序有语义)
                return None
        return None

    # ═══ 通道5: 计数声明(v4.2) ═══
    COUNT_PAT = re.compile(r"(\d+)\s*项(?:条目|条|需求)?")

    def _check_count(self, p: str, h: str) -> CheckResult | None:
        p_m = self.COUNT_PAT.search(p)
        h_m = self.COUNT_PAT.search(h)
        if not p_m or not h_m:
            return None
        # 两侧都显式声明条目数且上下文同构(功能表/需求表)
        if "功能表" in p and "功能表" in h and p_m.group(1) != h_m.group(1):
            return CheckResult(
                "inconsistent",
                f"条目计数矛盾: {p_m.group(1)}项 vs {h_m.group(1)}项",
                "GJB-09", "count",
                f"同表条目数声明不同({p_m.group(1)}≠{h_m.group(1)})",
                0.95, "count_decl")
        return None

    # ═══ 通道6: 文档级缺失声明(v4.2) ═══
    # 仅文档元素(条款/条目/章节/表格); 图/节点缺失留给NLI(领域约定: 图省略可为良性)
    DOC_ABSENCE_PAT = get_template("doc_absence").pattern

    def _check_doc_absence(self, p: str, h: str) -> CheckResult | None:
        if not (self.DOC_ABSENCE_PAT.search(p) or self.DOC_ABSENCE_PAT.search(h)):
            return None
        # 另一侧须有实质内容(条款级文本) → 文档级缺失=违规
        other = h if self.DOC_ABSENCE_PAT.search(h) else p
        has_content = len(re.sub(r"[\s\W]", "", other)) >= 15
        if has_content:
            return CheckResult(
                "inconsistent", "文档级条款缺失",
                "GJB-10", "compliance",
                "一侧声明条款缺失, 另一侧含实质条款内容 → 合规违规",
                0.9, "doc_absence")
        return None

    # ═══ 通道7: 编号条目顺序(v4.3) ═══
    # 诊断背景: B族17/67误判源于enum对碎片级"同集同序"判consistent,
    # 而真实突变是条目级对调(ORDER_CONFLICT: "2、主...3、备"↔"3、备...2、主").
    # 本通道只报inconsistent(正证据: 同编号不同内容/公共项相对顺序反转),
    # 不报consistent(局部证据不可证明全pair等价 — 健全化规则).
    NUM_ITEM_ANCHOR = re.compile(r"(?<![\d.表图节章第页卷])(\d{1,2})、")

    def _numbered_items(self, text: str) -> dict[str, str]:
        """提取编号条目 {编号: 首token}, 防误触: 排除小数/表号/章节号后缀."""
        anchors = [(m.start(), m.group(1)) for m in self.NUM_ITEM_ANCHOR.finditer(text)]
        if len(anchors) < 2:
            return {}
        items: dict[str, str] = {}
        for k, (pos, num) in enumerate(anchors):
            end = anchors[k + 1][0] if k + 1 < len(anchors) else min(len(text), pos + 200)
            content = text[pos + len(num) + 1:end]
            first_token = content.split("、")[0].strip("。：，； ")
            if first_token:
                items.setdefault(num, first_token)
        return items

    def _check_numbered(self, p: str, h: str) -> CheckResult | None:
        p_anchors = [(m.start(), m.group(1)) for m in self.NUM_ITEM_ANCHOR.finditer(p)]
        h_anchors = [(m.start(), m.group(1)) for m in self.NUM_ITEM_ANCHOR.finditer(h)]
        if len(p_anchors) < 2 or len(h_anchors) < 2:
            return None
        p_labels = [num for _, num in p_anchors]
        h_labels = [num for _, num in h_anchors]
        # 标签重复(多列表混排) → 结构不明, 不判
        if len(set(p_labels)) != len(p_labels) or len(set(h_labels)) != len(h_labels):
            return None
        if set(p_labels) != set(h_labels):
            return None  # 编号集不同(增删条目) → 留给enum集合比对
        # 1) 标签出现顺序对调(编号随条目走的ORDER_CONFLICT形态)
        if p_labels != h_labels:
            return CheckResult(
                "inconsistent",
                f"编号条目顺序对调: P序{'→'.join(p_labels)} vs H序{'→'.join(h_labels)}",
                "ORDER_CONFLICT", "numbered",
                f"同编号集但出现顺序不同({p_labels} vs {h_labels})",
                0.9, "numbered_order")
        # 2) 同编号不同内容(编号错位形态)
        p_items = self._numbered_items(p)
        h_items = self._numbered_items(h)
        for num, pc in p_items.items():
            hc = h_items.get(num, "")
            if pc != hc:
                return CheckResult(
                    "inconsistent",
                    f"编号条目错位: {num}、{pc[:12]} vs {num}、{hc[:12]}",
                    "ORDER_CONFLICT", "numbered",
                    f"同编号不同内容({num}、): P「{pc[:15]}」H「{hc[:15]}」",
                    0.9, "numbered_order")
        # 编号级全一致 → 不判consistent(健全化), 让位后续通道/NLI
        return None

    # ═══ 通道8: 序列顺序(v4.2) ═══
    SEQ_CONTEXT_PAT = re.compile(r"步骤|流程|顺序|依次|先后|阶段|次序")

    def _check_sequence(self, p: str, h: str) -> CheckResult | None:
        p_lists = self._lists_of(p)
        h_lists = self._lists_of(h)
        if not p_lists or not h_lists:
            return None
        if not (self.SEQ_CONTEXT_PAT.search(p) or self.SEQ_CONTEXT_PAT.search(h)):
            return None  # 无顺序语境 → 枚举重排=consistent(领域等价约定), 不判
        for p_items in p_lists:
            for h_items in h_lists:
                if set(p_items) == set(h_items) and p_items != h_items:
                    return CheckResult(
                        "inconsistent",
                        f"顺序矛盾: {p_items[:3]} vs {h_items[:3]}",
                        "ORDER_CONFLICT", "sequence",
                        f"同集异序(顺序语境): {'→'.join(p_items[:3])} vs {'→'.join(h_items[:3])}",
                        0.9, "seq_order")
        return None

    # ═══ 通道5: 证据核验(对称) ═══
    def _check_verify(self, p: str, h: str, evidence: list[str] | None) -> CheckResult | None:
        if not evidence:
            return None
        missing_items = re.findall(r"[「]([^「」]{2,30})[」]", h if "没有" in h else p)
        for item in missing_items:
            item = item.strip()
            ev_text = " ".join(str(e) for e in evidence)
            if item in ev_text:
                return CheckResult(
                    "consistent", f"「{item}」实际存在于证据中",
                    "DIAGRAM_EXTRA", "verify",
                    f"证据核验通过: {item[:20]}在evidence中找到",
                    1.0, "verify_evidence")
            if item in p and item not in ev_text:
                return CheckResult(
                    "inconsistent", f"「{item}」在premise中但不在证据中",
                    "TABLE_ITEM_MISSING", "verify",
                    f"证据核验: {item[:20]}不在evidence中",
                    0.9, "verify_evidence")
        return None

    # ═══ 通道6: NLI(兜底, 批量) ═══
    def _check_nli(self, p: str, h: str) -> CheckResult:
        self._nli_batch([(p, h)])
        return self._nli_results[0]

    def _nli_batch(self, pairs: list[tuple[str, str]]) -> None:
        if self._nli is None:
            self._load_nli()
        import torch
        tok, model, device = self._nli
        results = []
        bs = 32
        with torch.no_grad():
            for i in range(0, len(pairs), bs):
                batch = pairs[i:i + bs]
                enc = tok([p for p, _ in batch], [h for _, h in batch],
                          padding=True, truncation=True, max_length=128,
                          return_tensors="pt").to(device)
                logits = model(**enc).logits
                probs = torch.softmax(logits.float(), dim=-1)[:, 1]
                for (p, h), inc_p in zip(batch, probs.tolist(), strict=True):
                    results.append(CheckResult(
                        "inconsistent" if inc_p >= 0.5 else "consistent",
                        "", "SEM", "nli",
                        f"P(inconsistent)={inc_p:.3f}",
                        round(max(inc_p, 1 - inc_p), 3),
                        "nli_v12"))
        self._nli_results = results

    def _load_nli(self):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        mdir = str(self._nli_dir)
        tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device).eval()
        self._nli = (tok, model, device)


def check(premise: str, hypothesis: str,
          evidence_units: list[str] | None = None) -> CheckResult:
    return ConsistencyChecker().check(premise, hypothesis, evidence_units)


