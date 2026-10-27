"""Decoder: ACDD译码器 — 观测分歧 → P(真实不一致) 判决 + 弃权带.

两级译码(权威度降序):
  L1 裁决查表: pair的分歧已在M7/M17/M22语料中裁决 → 直接引用标签
     (置信 = vote_dist一致度; 664标签/148对覆盖)
  L2 类型先验: 未裁决分歧 → q = P(real | scene, dtype) = n_real/n_decided
     (从裁决语料学出的类型先验 — 论文claim "learnable from type priors"的落地)
  覆盖不足(n_decided=0 或 标签uncertain) → 弃权(ACDD P3: 沉默弃权 > 自信报错)

判决带: q >= τ_hi → report / q <= τ_lo → pass / 其间 → abstain

另含 P1 公式(M4锚遮蔽实验同款): q = π(1-p)/[π(1-p)+(1-π)p]
(元素级感知噪声译码, 供VLM通道比较使用; Tier1分歧的噪声是匹配器噪声,
用类型先验而非P1 — 这是两层的诚实分工).
"""
from __future__ import annotations

from typing import Any

from .adjudication import AdjudicationStore, scene_num
from .blackboard import Blackboard
from .schemas import Channel, ConfSource, Epistemic, EvidenceItem, Provenance

# 标签 → 行动: 检测目标是"文档真实不一致(real_bug)"
_LABEL_ACTION = {
    "real_bug": "report",
    "benign_variation": "pass",
    "compiler_bug": "tool_issue",      # 工具/匹配器问题, 非文档缺陷
    "extraction_error": "abstain",
    "uncertain": "abstain",
}

TAU_HI = 0.7   # report带
TAU_LO = 0.3   # pass带


def decode_element(d_obs: int, pi: float, p_miss: float,
                   p_hall: float) -> float:
    """P1后验(M4同款): q = P(η=1 | D, θ).

    d_obs=1(观测到分歧): q = π(1-p_miss) / [π(1-p_miss) + (1-π)·p_miss]
    d_obs=0(观测一致):   q = π·p_hall / [π·p_hall + (1-π)·(1-p_miss)]
    """
    if d_obs == 1:
        num = pi * (1.0 - p_miss)
        return num / (num + (1.0 - pi) * p_miss + 1e-12)
    num = pi * p_hall
    return num / (num + (1.0 - pi) * (1.0 - p_miss) + 1e-12)


class Decoder:
    """Tier1分歧集合 → 检测判决(带证据链与弃权带)."""

    def __init__(self, store: AdjudicationStore | None = None,
                 tau_hi: float = TAU_HI, tau_lo: float = TAU_LO) -> None:
        self.store = store or AdjudicationStore()
        self.tau_hi = tau_hi
        self.tau_lo = tau_lo

    # ── 单条分歧译码 ──────────────────────────────────────
    def _decode_one(self, pair_id: str, scene: str, disc: dict) -> dict:
        dtype = disc.get("dtype", "")
        evidence = disc.get("evidence", "")
        verdict: dict[str, Any] = {
            "dtype": dtype, "evidence": evidence[:80],
            "label_source": "prior", "q": None, "action": "abstain",
            "confidence": 0.0, "reason": "",
        }

        # L1 裁决查表
        m = self.store.match(pair_id, dtype, evidence)
        if m is not None and m.get("label"):
            label = m["label"]
            verdict.update({
                "label_source": "adjudicated", "label": label,
                "task_id": m.get("task_id", ""),
                "action": _LABEL_ACTION.get(label, "abstain"),
            })
            vd = m.get("vote_dist") or {}
            total_votes = sum(vd.values()) if vd else 0
            if total_votes:
                top = max(vd.values())
                verdict["confidence"] = round(top / total_votes, 3)
                verdict["reason"] = (f"M22仲裁({m.get('task_id')}): "
                                     f"{label} (votes {vd})")
            else:
                verdict["confidence"] = 0.85
                verdict["reason"] = f"双LLM一致裁决: {label}"
            # q语义: report→高, pass/tool→低, abstain→中间
            if verdict["action"] == "report":
                verdict["q"] = verdict["confidence"]
            elif verdict["action"] in ("pass", "tool_issue"):
                verdict["q"] = round(1 - verdict["confidence"], 3)
            else:
                verdict["q"] = 0.5
            return verdict

        # L2 类型先验
        counts = self.store.type_counts(scene, dtype)
        n_decided = sum(counts.get(k, 0) for k in
                        ("real_bug", "benign_variation", "compiler_bug",
                         "extraction_error"))
        n_total = n_decided + counts.get("uncertain", 0)
        if n_decided == 0:
            verdict["reason"] = f"无(scene={scene}, dtype={dtype})先验数据 → 弃权"
            verdict["q"] = None
            return verdict
        q_real = counts.get("real_bug", 0) / n_decided
        verdict["q"] = round(q_real, 4)
        verdict["action"] = ("report" if q_real >= self.tau_hi
                             else "pass" if q_real <= self.tau_lo else "abstain")
        verdict["confidence"] = round(n_decided / max(n_total, 1), 3)
        verdict["reason"] = (f"类型先验: real={counts.get('real_bug', 0)}/"
                             f"{n_decided} (scene={scene_num(scene)}, "
                             f"dtype={dtype})")
        return verdict

    # ── 整黑板译码 ────────────────────────────────────────
    def decode(self, bb: Blackboard) -> EvidenceItem | None:
        """discrepancy_set证据 → detection_verdicts证据项(append-only审计)."""
        discs: list[dict] = []
        prov_pair = bb.task.pair_id or "-"
        for e in bb.by_subject("discrepancy_set"):
            discs.extend(e.payload.get("discrepancies", []))
        if not discs:
            return None
        scene = bb.task.scene or (prov_pair.split("_")[0] if bb.task.pair_id else "")
        verdicts = [self._decode_one(bb.task.pair_id, scene, d) for d in discs]

        n_adj = sum(1 for v in verdicts if v["label_source"] == "adjudicated")
        summary = {
            "n_verdicts": len(verdicts),
            "n_report": sum(1 for v in verdicts if v["action"] == "report"),
            "n_pass": sum(1 for v in verdicts if v["action"] == "pass"),
            "n_abstain": sum(1 for v in verdicts if v["action"] == "abstain"),
            "n_tool_issue": sum(1 for v in verdicts if v["action"] == "tool_issue"),
            "n_adjudicated": n_adj,
            "coverage": round(n_adj / len(verdicts), 3),
            "pi_scene": self.store.scene_pi(scene),
            "tau": [self.tau_lo, self.tau_hi],
        }
        payload = {"pair_id": bb.task.pair_id, "scene": scene,
                   "summary": summary, "verdicts": verdicts[:40]}
        conf = 0.85 if n_adj == len(verdicts) else summary["coverage"]
        return EvidenceItem(
            subject="detection_verdicts", channel=Channel.ADJUDICATION,
            epistemic=(Epistemic.VERIFIED if n_adj == len(verdicts)
                       else Epistemic.HYPOTHESIS),
            confidence=conf, conf_source=ConfSource.CALIBRATED,
            payload=payload,
            provenance=Provenance(source="final_adjudication.json (M22)",
                                  locator=bb.task.pair_id),
            note=f"译码: {summary['n_report']}report/"
                 f"{summary['n_pass']}pass/{summary['n_abstain']}abstain"
                 f" (裁决覆盖{summary['coverage']:.0%})")
