"""校准置信度模型: 每个通道的置信度从哪来 (Calibrated Blackboard的地基).

数据来源:
  - data/gjb_438c/anchor_sc2/calibration.json  (M3: 89对锚点互校θ)
  - data/gjb_438c/blackboard/embedding_calibration.json (本包calibrate_embedding产出)

语义约定 (ACDD两层模型的落地):
  - 感知层写入(VLM/OCR/EMBEDDING): 置信度 = P(该声明为真) ≈ 通道precision(按文档/难度条件化)
  - 确定性写入(ANCHOR/KT/KP/ID_GRAPH/CHUNKS): 置信度 = 1.0 (by construction)
  - LLM写入: 置信度上限0.6 (M17双模型一致率38%的诚实约束)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import Channel, ConfSource

BASE = Path(__file__).resolve().parents[2]
CALIB_PATH = BASE / "data/gjb_438c/anchor_sc2/calibration.json"
EMB_CALIB_PATH = BASE / "data/gjb_438c/blackboard/embedding_calibration.json"


@dataclass(frozen=True)
class Conf:
    """一次置信度评定的完整语义: 数值 + 来源 + 说明."""
    value: float
    source: ConfSource
    note: str


# 确定性通道的固定语义
_DETERMINISTIC: dict[Channel, str] = {
    Channel.ANCHOR: "born-digital XML直读, 构造性保真",
    Channel.KT: "κ_T确定性编译, 解析忠实于表格字面",
    Channel.KP: "κ_P确定性抽取, 忠实于正文字面",
    Channel.ID_GRAPH: "ID正则确定性提取",
    Channel.CHUNKS: "chunk字面内容读取",
    Channel.DRIFT_CENSUS: "源-渲染确定性diff",
    Channel.SYNTAX: "GJB语法规则确定性检测(algorithms/syntax)",
}


class ConfidenceModel:
    """通道→置信度评定. VLM走θ校准(全局/按文档/按φ难度), 其余走固定语义."""

    def __init__(self, calib: dict[str, Any] | None = None,
                 emb_calib: dict[str, Any] | None = None) -> None:
        self.calib = calib or {}
        self.emb_calib = emb_calib or {}

    # ── 加载 ──────────────────────────────────────────────
    @classmethod
    def load(cls, calib_path: Path | None = None,
             emb_calib_path: Path | None = None) -> "ConfidenceModel":
        calib: dict[str, Any] = {}
        emb: dict[str, Any] = {}
        p = calib_path or CALIB_PATH
        if p.exists():
            calib = json.loads(p.read_text(encoding="utf-8"))
        pe = emb_calib_path or EMB_CALIB_PATH
        if pe.exists():
            emb = json.loads(pe.read_text(encoding="utf-8"))
        return cls(calib, emb)

    # ── VLM θ 读取 ────────────────────────────────────────
    def _theta_global(self, key: str) -> float | None:
        node = self.calib.get("theta_global", {}).get(key)
        return float(node["value"]) if isinstance(node, dict) else None

    def _vlm_doc_precision(self, doc: str) -> tuple[float, str] | None:
        """按文档条件化: precision ≈ 1 - node_halluc_rate(θ_by_doc)."""
        by_doc = self.calib.get("theta_by_doc", {}).get(doc)
        if isinstance(by_doc, dict) and "node_halluc_rate" in by_doc:
            return 1.0 - float(by_doc["node_halluc_rate"]), f"by_doc({doc[:12]}...)"
        return None

    def vlm_miss_rate(self, doc: str = "", n_nodes: int | None = None) -> float:
        """VLM漏检率(φ难度条件化): critic判断"VLM证据是否需要补锚点/OCR"用."""
        if n_nodes is not None:
            bucket = "small(≤5)" if n_nodes <= 5 else ("medium(6-10)" if n_nodes <= 10 else "large(>10)")
            phi = self.calib.get("theta_by_phi", {}).get(bucket)
            if isinstance(phi, dict) and "node_miss_rate" in phi:
                return float(phi["node_miss_rate"])
        g = self._theta_global("node_miss_rate")
        return g if g is not None else 0.06

    # ── 主入口 ────────────────────────────────────────────
    def for_channel(self, channel: Channel, claim: str = "node",
                    doc: str = "", n_nodes: int | None = None) -> Conf:
        """评定一次写入的置信度.

        claim: "node"(存在性声明) | "edge" | "text"(逐字性) | "match"(匹配声明)
        """
        if channel in _DETERMINISTIC:
            return Conf(1.0, ConfSource.DETERMINISTIC, _DETERMINISTIC[channel])

        if channel == Channel.VLM:
            return self._vlm(claim, doc, n_nodes)

        if channel == Channel.OCR:
            # calibration.json暂无OCR θ; 论文实测伪发现率高(69%幻报) → 保守启发式
            return Conf(0.5, ConfSource.HEURISTIC,
                        "OCR未校准; 伪发现风险高(69%表相关元素为幻报), 仅作独立证据")

        if channel == Channel.TIER1:
            return Conf(0.9, ConfSource.DETERMINISTIC,
                        "预计算Tier1(M16/M1), 比较逻辑确定性; 内部词法/embedding匹配为启发式")

        if channel == Channel.ADJUDICATION:
            # M22三轮仲裁: 95%自动裁决(664标签/38不确定); 单条置信=投票一致度
            return Conf(0.85, ConfSource.CALIBRATED,
                        "双LLM/五票集成/辩论式三轮仲裁(M22); 单条一致度见payload")

        if channel == Channel.LEXICAL:
            return Conf(0.75, ConfSource.HEURISTIC,
                        "确定性词法匹配(text_match_score); 阈值语义未校准")

        if channel == Channel.EMBEDDING:
            agr = self.emb_calib.get("agreement_rate")
            if isinstance(agr, (int, float)) and self.emb_calib.get("n_emb_matches", 0) >= 20:
                return Conf(float(agr), ConfSource.CALIBRATED,
                            f"embedding匹配经词法银标定校准(agreement={agr:.3f}, "
                            f"n={self.emb_calib.get('n_emb_matches')})")
            return Conf(0.7, ConfSource.HEURISTIC,
                        "embedding通道未校准(跑calibrate_embedding后升级)")

        if channel == Channel.LLM:
            return Conf(0.6, ConfSource.LLM_SELF,
                        "LLM自报上限0.6 (M17双模型一致率38%)")

        return Conf(0.5, ConfSource.HEURISTIC, f"未知通道语义: {channel}")

    # ── VLM细分 ───────────────────────────────────────────
    def _vlm(self, claim: str, doc: str, n_nodes: int | None) -> Conf:
        if not self.calib:
            return Conf(0.9, ConfSource.HEURISTIC,
                        "calibration.json缺失, VLM按节点召回94.4%的经验值")
        if claim == "node":
            got = self._vlm_doc_precision(doc) if doc else None
            if got:
                value, note = got
                return Conf(value, ConfSource.CALIBRATED, f"VLM节点precision {note}")
            g = self._theta_global("node_precision")
            if g is not None:
                return Conf(g, ConfSource.CALIBRATED, "VLM节点precision θ_global")
        if claim == "edge":
            extra = self._theta_global("edge_extra_rate")
            if extra is not None:
                return Conf(1.0 - extra, ConfSource.CALIBRATED,
                            f"VLM边precision=1-edge_extra_rate(={extra:.3f})")
        if claim == "text":
            v = self._theta_global("text_verbatim_rate")
            if v is not None:
                return Conf(v, ConfSource.CALIBRATED, "VLM逐字率 θ_global")
        # 兜底: 节点precision
        g = self._theta_global("node_precision")
        return Conf(g if g is not None else 0.9, ConfSource.CALIBRATED,
                    "VLM θ_global(节点precision兜底)")
