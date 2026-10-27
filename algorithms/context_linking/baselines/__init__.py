"""复现baseline的系统化整理: 与evidence_recall同接口的可插拔对照头.

设计: 每个baseline实现统一头协议 build(store) → score_query(query)
→ per-owner分数向量(np.ndarray, 长度=store.n_owners), 可直接接入
MultiHeadRecall/评测harness与我们的方法同管线对比.

家族:
  词面:     BM25-doc(=evidence_recall.LexicalHead), BM25-unit(本包)
  稠密:     B1-dense(=evidence_recall.DenseHead, 编码器注入:
            zh=bge-large-zh, en=bge-base-en, E5/Contriever同理)
  后期交互: Token-MaxSim(本包, token编码器注入)

模型门控baseline(M3-dense/sparse/colbert, Contriever-MS, ColBERTv2)
留在评测脚本(各自lazy加载+fp16细节), 全景见
docs/srs_project/33_baseline_registry.md.
"""
from __future__ import annotations

from ..evidence_recall.evidence import EvidenceStore
from ..evidence_recall.heads import DenseHead, LexicalHead
from .heads import BM25UnitHead, TokenEncoder, TokenMaxSimHead
from .llm_listwise import LLMListwiseRerank


def make_baseline(name: str, store: EvidenceStore,
                  encoder=None, token_encoder=None,
                  torch_mod=None, device: str = "cpu"):
    """按名构建baseline头(与evidence_recall头同接口).

    词面系无需编码器; 稠密系需encoder; Token-MaxSim需token_encoder.
    """
    if name == "BM25-doc":
        return LexicalHead().build(store)
    if name == "BM25-unit":
        return BM25UnitHead().build(store)
    if name == "B1-dense":
        if encoder is None:
            raise ValueError("B1-dense需要encoder")
        return DenseHead(encoder).build(store)
    if name == "Token-MaxSim":
        if token_encoder is None:
            raise ValueError("Token-MaxSim需要token_encoder")
        return TokenMaxSimHead(token_encoder, torch_mod=torch_mod,
                               device=device).build(store)
    raise KeyError(f"未知baseline: {name}(模型门控系见评测脚本)")


BASELINE_NAMES = ["BM25-doc", "BM25-unit", "B1-dense", "Token-MaxSim",
                  "LLM-listwise"]

__all__ = [
    "BM25UnitHead", "TokenMaxSimHead", "TokenEncoder",
    "make_baseline", "BASELINE_NAMES",
    "LexicalHead", "DenseHead", "LLMListwiseRerank",
]
