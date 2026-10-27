"""SRS-Verifier: 证据召回-子注意力重排-场景分派求解的一致性校验算法.

架构(五模块): docs/srs_project/algorithm_design.md
  M1 证据召回(稠密⊕词法⊕结构) → M2 筛选 → M3 子注意力重排
  → M4 场景分派(Z3/规则/结构/词典/NLI残差) → M5 融合裁决

设计原则: 确定性求解器优先(短路), NLI只处理语义残差且受注意力门控调制.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
_STOP = set("的了和与及或是在为对从被把按根据通过包括应由应需" + "，。；：、！？（）")

_NUM_PAT = re.compile(r"(\d+\.?\d*)\s*(ms|毫秒|s|秒|min|分钟|h|小时|天|日|月|年|GB|MB|KB|TB|条|路|个|%|Hz)")


def _tok(s: str) -> list[str]:
    return [t for t in re.split(r"[\s，。；：、,.;:!?（）()「」]", str(s)) if t and t not in _STOP and len(t) > 1]


class EvidenceUnit:
    """证据子单元(表格行/图节点/正文条款)."""

    __slots__ = ("text", "kind", "source", "vec")

    def __init__(self, text: str, kind: str, source: str) -> None:
        self.text = text
        self.kind = kind  # table_row / diagram_node / text_clause / context
        self.source = source
        self.vec: np.ndarray | None = None


def decompose_context(ctx: dict) -> list[EvidenceUnit]:
    """将canonical context分解为证据子单元(M3的输入)."""
    units = []
    for row in str(ctx.get("table", "")).split("\n"):
        if row.strip():
            units.append(EvidenceUnit(row.strip()[:80], "table_row", ctx.get("pair_id", "")))
    for node in str(ctx.get("diagram", "")).split(";"):
        if node.strip():
            units.append(EvidenceUnit(node.strip()[:60], "diagram_node", ctx.get("pair_id", "")))
    for clause in re.split(r"[。；]", str(ctx.get("text", ""))):
        if len(clause.strip()) >= 8:
            units.append(EvidenceUnit(clause.strip()[:80], "text_clause", ""))
    return units


class SrsVerifier:
    """SRS一致性校验器: 证据召回+子注意力重排+场景分派求解."""

    def __init__(self, nli_model: str | None = None) -> None:
        self._nli_dir = nli_model or str(BASE / "models/nli/erlangshen-330m-qlora-v8-cct")
        self._bge = None
        self._nli = None

    # ── 惰性加载(AGENTS.md: 顶层零I/O) ──
    def _bge_embed(self, texts: list[str]) -> list[np.ndarray]:
        if self._bge is None:
            from algorithms.common.bge_local import BgeLocal
            self._bge = BgeLocal()
        vecs = self._bge.embed(texts)
        return [np.asarray(v, dtype=np.float32) for v in vecs.values()] if isinstance(vecs, dict) else \
            [np.asarray(vecs[i], dtype=np.float32) for i in range(len(texts))]

    # ═══ M1+M2: 证据召回与筛选(稠密⊕词法) ═══
    def recall_and_filter(self, claim: str, units: list[EvidenceUnit], k: int = 8) -> list[EvidenceUnit]:
        if not units:
            return []
        q_tok = set(_tok(claim))
        # 词法通道
        lex = []
        for u in units:
            ut = set(_tok(u.text))
            overlap = len(q_tok & ut) / (len(q_tok | ut) + 1e-9)
            lex.append(overlap)
        # 稠密通道
        q_vec = self._bge_embed([claim])[0]
        if u_vecs_missing := [i for i, u in enumerate(units) if u.vec is None]:
            vs = self._bge_embed([units[i].text for i in u_vecs_missing])
            for idx, v in zip(u_vecs_missing, vs):
                units[idx].vec = v
        dense = [float(np.dot(u.vec, q_vec) / (np.linalg.norm(u.vec) * np.linalg.norm(q_vec) + 1e-9))
                 if u.vec is not None else 0.0 for u in units]
        # M2: 几何平均融合(防单通道主导) + 表格/图优先0.05
        fused = [(np.sqrt(max(lex[i], 1e-9) * max(dense[i], 1e-9))
                  + (0.05 if units[i].kind in ("table_row", "diagram_node") else 0.0), i)
                 for i in range(len(units))]
        fused.sort(reverse=True)
        return [units[i] for _, i in fused[:k]]

    # ═══ M3: 子注意力重排 ═══
    def sub_attention(self, claim: str, units: list[EvidenceUnit], tau: float = 0.05) -> dict[str, Any]:
        if not units:
            return {"alphas": [], "coverage": 0.0, "top": []}
        q_vec = self._bge_embed([claim])[0]
        sims = []
        for u in units:
            if u.vec is None:
                u.vec = self._bge_embed([u.text])[0]
            sims.append(float(np.dot(u.vec, q_vec) / (np.linalg.norm(u.vec) * np.linalg.norm(q_vec) + 1e-9)))
        sims_arr = np.array(sims)
        alphas = np.exp(sims_arr / tau)
        alphas = alphas / alphas.sum()
        coverage = float(sims_arr.max())
        order = np.argsort(-sims_arr)
        return {"alphas": alphas.tolist(), "coverage": coverage,
                "top": [(units[i].text[:40], units[i].kind, round(sims[i], 3)) for i in order[:3]]}

    # ═══ M4: 确定性求解器 ═══
    @staticmethod
    def solve_z3_param(premise: str, hypothesis: str) -> dict[str, Any] | None:
        """PARAM类: 数值单位抽取→区间约束→Z3判定(带证明)."""
        p_vals = [(m.group(1), m.group(2)) for m in _NUM_PAT.finditer(premise)]
        h_vals = [(m.group(1), m.group(2)) for m in _NUM_PAT.finditer(hypothesis)]
        if not p_vals or not h_vals:
            return None
        # 同单位数值冲突 → 区间交集为空 → Z3 unsat
        for pv, pu in p_vals:
            for hv, hu in h_vals:
                if pu == hu and pv != hv:
                    try:
                        from z3 import Real, Solver, unsat
                        x = Real("x")
                        s = Solver()
                        s.add(x == float(pv))
                        s.add(x == float(hv))
                        if s.check() == unsat:
                            return {"verdict": "inconsistent", "technique": "z3",
                                    "evidence": f"同单位[{pu}]约束 x=={pv} ∧ x=={hv} → unsat(矛盾证明)"}
                    except ImportError:
                        return {"verdict": "inconsistent", "technique": "z3_fallback",
                                "evidence": f"同单位[{pu}]数值 {pv}≠{hv}"}
        return None

    @staticmethod
    def solve_structure(claim: str, units: list[EvidenceUnit], attention: dict) -> dict[str, Any] | None:
        """结构类: 缺失声称 vs 证据池核验(精确+语义注意力软核验)."""
        m = re.search(r"[「]([^「」]+)[」]", claim)
        if not m:
            return None
        item = m.group(1).strip()
        if len(item) < 3:
            return None
        # 确定性精确核验
        for u in units:
            if item in u.text or item.replace(" ", "") in u.text.replace(" ", ""):
                return {"verdict": "consistent", "technique": "structure_verify",
                        "evidence": f"声称缺失的「{item}」实际存在于{u.kind}: {u.text[:40]}"}
        # 语义级软核验: 注意力coverage高(证据池有高相似子单元) → 缺失声称可疑
        if attention["coverage"] >= 0.90:
            top = attention["top"][0] if attention["top"] else ("", "", 0)
            return {"verdict": "consistent", "technique": "attention_soft_verify",
                    "evidence": f"高注意力证据存在({top[0][:30]}, sim={top[2]}), 缺失声称可疑"}
        return None

    @staticmethod
    def solve_term(premise: str, hypothesis: str) -> dict[str, Any] | None:
        """TERM类: 词典+编辑距离(同义异名判定)."""
        p_q = re.findall(r"[「]([^「」]+)[」]", premise)
        h_q = re.findall(r"[「]([^「」]+)[」]", hypothesis)

        def edit(a: str, b: str) -> int:
            if abs(len(a) - len(b)) > 2:
                return 9
            dp = list(range(len(b) + 1))
            for i, ca in enumerate(a, 1):
                nd = [i]
                for j, cb in enumerate(b, 1):
                    nd.append(min(dp[j] + 1, nd[j - 1] + 1, dp[j - 1] + (ca != cb)))
                dp = nd
            return dp[-1]

        for a in p_q:
            for b in h_q:
                d = edit(a, b)
                if 0 < d <= 2 and len(a) >= 4:
                    return {"verdict": "inconsistent", "technique": "term_edit",
                            "evidence": f"术语「{a}」vs「{b}」编辑距离{d}(近似但非同)"}
        return None

    # ═══ M4残差+M5: NLI(注意力门控调制) ═══
    def solve_nli(self, premise: str, hypothesis: str, coverage: float, lam: float = 0.5) -> dict[str, Any]:
        if self._nli is None:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            tok = AutoTokenizer.from_pretrained(self._nli_dir, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(self._nli_dir, local_files_only=True)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device).eval()
            id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
            cid = next((k for k, v in id2label.items() if "contra" in v), 0)
            self._nli = (tok, model, cid, device)
        import torch
        tok, model, cid, device = self._nli
        enc = tok(premise, hypothesis, padding=True, truncation=True, max_length=128,
                  return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits
        p = float(torch.softmax(logits.float(), dim=-1)[0, cid])
        # 注意力门控: 证据覆盖越高 → 对NLI"矛盾"判断越谨慎(证据可能支持一致)
        p_modulated = p * (1 - lam * max(0.0, coverage - 0.85))
        verdict = "inconsistent" if p_modulated >= 0.5 else "consistent"
        return {"verdict": verdict, "technique": "nli_attention_gated",
                "evidence": f"NLI p={p:.3f}, coverage={coverage:.2f}, 门控后p={p_modulated:.3f}"}

    # ═══ 主入口: 五模块流水线 ═══
    def verify(self, premise: str, hypothesis: str, context: dict | None = None,
               dtype: str = "", scene: str = "") -> dict[str, Any]:
        claim = premise
        # M1: 分解证据子单元
        units = decompose_context(context or {})
        # M2: 召回+筛选
        filtered = self.recall_and_filter(claim, units)
        # M3: 子注意力重排
        attention = self.sub_attention(claim, filtered)
        # M4: 场景分派(确定性优先短路)
        solver_result = None
        if dtype.startswith("PARAM") or _NUM_PAT.search(premise) and _NUM_PAT.search(hypothesis):
            solver_result = self.solve_z3_param(premise, hypothesis)
        if solver_result is None and ("MISSING" in dtype or "EXTRA" in dtype or "COMPONENT" in dtype):
            solver_result = self.solve_structure(claim, filtered or units, attention)
        if solver_result is None and dtype.startswith("TERM"):
            solver_result = self.solve_term(premise, hypothesis)
        # M5: 融合(确定性短路 / NLI注意力门控)
        if solver_result and solver_result["verdict"] in ("inconsistent", "consistent"):
            result = solver_result
        else:
            result = self.solve_nli(premise, hypothesis, attention["coverage"])
        result["attention"] = {"coverage": round(attention["coverage"], 3), "top": attention["top"]}
        result["n_evidence"] = len(filtered)
        return result


def verify_batch(items: list[dict], nli_model: str | None = None) -> list[dict]:
    """批量校验: 输入canonical条目(pair+context+angle), 输出判定+求解器链."""
    ver = SrsVerifier(nli_model=nli_model)
    out = []
    for x in items:
        r = ver.verify(x["pair"]["premise"], x["pair"]["hypothesis"],
                       x.get("context"), x["angle"]["type"], x["angle"]["scene"])
        out.append({"id": x["id"], "gold": x["label"], **{k: r[k] for k in
                                                          ("verdict", "technique", "evidence", "attention")}})
    return out
