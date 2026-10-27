"""DocQueryIndex: docT5query式假想查询索引 (方向A召回的扩展证据源).

谱系: docT5query (Nogueira & Cho 2019) — 离线为每个chunk生成
"假想查询"(它最可能被什么问题问到), 在线将用户查询与假想查询匹配,
命中即召回其宿主chunk. 把"chunk正文↔短实体查询"的词汇失配转化为
"查询↔查询"的同空间匹配.

攻两个瓶颈: 短实体查询信号不足 + ID-Graph未登记的深层小节盲区
(假想查询由tools/gen_hypothetical_queries.py离线生成, 覆盖无ID锚
的深层小节chunk).

双路打分(每条假想查询hq):
  ① 词法: lexical_kit.text_match_score(query, hq)
     (精确>包含>功能词剥离>容错>重叠 — 保留匹配强度信息)
  ② BM25: query词项 vs hq语料, CJK 2字滑窗+ASCII token,
     k1=1.5 b=0.75(与evidence_store.bm25_rank同参数的轻量实现)
融合: score = lex + λ·bm25/bm25_max (λ=0.3) — 查询内最大值归一,
  有界scale-free; 词法强度主导, BM25补词汇重叠.
宿主chunk取其全部hq的最高分; snippet=命中的假想查询.

模块顶层零I/O(全部惰性加载); 文件读取均encoding="utf-8".

用法:
    idx = DocQueryIndex()
    idx.search("收件箱和发件箱接口")   # → [{chunk_id, ..., rank, score}]
    idx.n_chunks                       # 已建索引的chunk数(覆盖度)
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .lexical_kit import text_match_score

BASE = Path(__file__).resolve().parents[2]
DOC_QUERIES_PATH = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
CHUNKS_PATH = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"

_BM25_K1 = 1.5
_BM25_B = 0.75
_BM25_LAMBDA = 0.3            # BM25归一分权重(词法主导, BM25补重叠)
_ASCII_PAT = re.compile(r"[A-Za-z0-9]{2,}")
_CJK_PAT = re.compile(r"[\u4e00-\u9fff]")


def _terms_of(text: str) -> list[str]:
    """检索词: CJK 2字滑窗 + ASCII token(与EvidenceStore._terms_of一致)."""
    t = text or ""
    cjk = _CJK_PAT.findall(t)
    bigrams = {"".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
    ascii_tokens = {w.lower() for w in _ASCII_PAT.findall(t)}
    return sorted(bigrams | ascii_tokens)


def _tf_of(text: str) -> dict[str, int]:
    """词项频次: CJK序列滑窗bigram + ASCII token(小写)."""
    t = text or ""
    tf: dict[str, int] = {}
    cjk = _CJK_PAT.findall(t)
    for i in range(len(cjk) - 1):
        bg = cjk[i] + cjk[i + 1]
        tf[bg] = tf.get(bg, 0) + 1
    for w in _ASCII_PAT.findall(t):
        k = w.lower()
        tf[k] = tf.get(k, 0) + 1
    return tf


class DocQueryIndex:
    """假想查询索引: 查询文本→词法+BM25匹配假想查询→返回其宿主chunk."""

    def __init__(self, queries_path: Path | None = None,
                 chunks_path: Path | None = None) -> None:
        self.queries_path = queries_path or DOC_QUERIES_PATH
        self.chunks_path = chunks_path or CHUNKS_PATH
        self._hqs: list[tuple[str, str]] = []   # (chunk_id, 假想查询)
        self._chunks: dict[str, dict[str, Any]] = {}
        self._tf: list[dict[str, int]] = []     # 每hq词项频次
        self._df: dict[str, int] = {}           # 词项→含该词的hq数
        self._dl: list[int] = []                # 每hq词项数(去重)
        self._avgdl = 1.0
        self._ready = False

    # ── 惰性构建 ─────────────────────────────────────────
    def _ensure(self) -> bool:
        if self._ready:
            return bool(self._hqs)
        self._ready = True
        try:
            data = json.loads(self.queries_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(data, dict):
            return False
        self._load_chunk_meta()
        for cid, qs in data.items():
            if not isinstance(qs, list):
                continue
            for q in qs:
                qt = str(q).strip()
                if not qt or cid not in self._chunks:
                    continue
                self._hqs.append((cid, qt))
                tf = _tf_of(qt)
                self._tf.append(tf)
                self._dl.append(len(tf))
                for t in tf:
                    self._df[t] = self._df.get(t, 0) + 1
        self._avgdl = (sum(self._dl) / len(self._dl)) if self._dl else 1.0
        return bool(self._hqs)

    def _load_chunk_meta(self) -> dict[str, dict[str, Any]]:
        try:
            chunks = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            chunks = []
        self._chunks = {c.get("chunk_id", ""): c
                        for c in chunks if isinstance(c, dict)}
        return self._chunks

    @property
    def n_chunks(self) -> int:
        """已建假想查询索引的chunk数(覆盖度)."""
        self._ensure()
        return len({cid for cid, _ in self._hqs})

    @property
    def indexed_chunk_ids(self) -> set[str]:
        """已索引chunk_id集合(评测覆盖子集判定用)."""
        self._ensure()
        return {cid for cid, _ in self._hqs}

    # ── 检索 ─────────────────────────────────────────────
    def search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """双路匹配假想查询, 返回宿主chunk命中(标准形态).

        ① query与每条假想查询的text_match_score
        ② BM25(query词项 vs 假想查询语料)
        融合: lex + 0.3·bm25/bm25_max; 宿主chunk取其最高hq;
        snippet=命中的假想查询; rank为1-based名次(并列按chunk_id稳定).
        """
        if not query or not self._ensure():
            return []
        q_terms = _terms_of(query)
        n = len(self._hqs)
        idf = {t: max(0.0, math.log(1 + (n - self._df.get(t, 0) + 0.5)
                                    / (self._df.get(t, 0) + 0.5)))
               for t in q_terms}
        bm: list[float] = []
        for i in range(n):
            tf_i = self._tf[i]
            dl = max(self._dl[i], 1)
            s = 0.0
            for t, w in idf.items():
                tf = tf_i.get(t, 0)
                if tf:
                    s += w * tf * (_BM25_K1 + 1) / (
                        tf + _BM25_K1 * (1 - _BM25_B
                                         + _BM25_B * dl / self._avgdl))
            bm.append(s)
        bmax = max(bm) if bm else 0.0
        best: dict[str, tuple[float, str]] = {}
        for i, (cid, qt) in enumerate(self._hqs):
            score = text_match_score(query, qt)
            if bmax > 0 and bm[i] > 0:
                score += _BM25_LAMBDA * bm[i] / bmax
            if score <= 0.0:
                continue
            cur = best.get(cid)
            if cur is None or score > cur[0]:
                best[cid] = (score, qt)
        ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], kv[0]))
        out: list[dict[str, Any]] = []
        for rank, (cid, (score, qt)) in enumerate(ranked[:top_k], 1):
            c = self._chunks.get(cid, {})
            out.append({
                "chunk_id": cid,
                "type": c.get("type", "text"),
                "section": c.get("section", ""),
                "doc": c.get("doc", ""),
                "snippet": qt[:80],
                "rank": rank,
                "score": round(score, 4),
                "channel": "doc_query",
            })
        return out
