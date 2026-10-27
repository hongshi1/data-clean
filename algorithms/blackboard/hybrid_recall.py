"""多路召回器(Hybrid Recall): 五通道 + RRF融合 (方向A召回的正式化).

通道(每路独立产出ranked list, 统一输出schema):
  lexical     精确子串/双关键词全命中(确定性, 高精度)
  sparse      BM25(k1=1.5, b=0.75; CJK 2字滑窗+ASCII token)
  dense       BGE-large-zh语义向量(1024维, GPU惰性加载, 磁盘索引缓存;
              图片chunk用caption+VLM key_elements富化文本索引)
  structural  ID-Graph硬桥(实体名/ID→mentions→全部出现章节→章节chunks;
              带跨文档同名消歧)
  multimodal  VLM图片分析直查(key_elements匹配→(doc,fig)→image chunk)

融合: 两种策略(消融对比):
  rrf      Reciprocal Rank Fusion (Cormack et al., SIGIR'09)
           score(d) = Σ_c 1/(k + rank_c(d)), k=60; 通道等权民主投票.
           适用于通道强度可比的纯排序场景.
  cascade  级联融合(事实直通+概率填充): 事实性通道(lexical精确子串/
           structural硬桥/multimodal元素命中)的命中是"存在性证据"
           而非排序信号 → 直通top-k; 剩余配额由概率性通道
           (sparse/dense)RRF填充. 异构通道强度悬殊时的标准处理.

可选后处理: 章节配额(每章节≤quota条) — 同章节垄断top-k会损伤
  section覆盖(深层小节被挤出的失败模式).

设计原则(与黑板一致): 通道可独立失效(dense不可用时优雅降级为四路),
  每路结果带provenance(rank字段=通道名+名次).

用法:
    rec = HybridRecaller()            # store复用, dense惰性
    r = rec.recall("结构化数据归集")
    r["hits"]                          # 融合后top-k
    r["per_channel"]["dense"]["n"]     # 各通道命中数
"""
from __future__ import annotations

import pickle
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .evidence_store import EvidenceStore

BASE = Path(__file__).resolve().parents[2]
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"

CHANNELS = ("lexical", "sparse", "dense", "structural", "multimodal", "unit")
_RRF_K = 60                     # RRF标准参数(Cormack 2009)
_DENSE_TOPK = 30                # 概率通道进入融合的深度
_LEXICAL_TOPK = 200             # 事实通道深度(命中全收, 防御上限)
_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："  # BGE检索指令前缀
_LEX_PER_SECTION = 2            # lexical章节分组调度: 每章节代表数

# ── 查询理解: 自然语言问句 → 检索实体词 ────────────────────

_QU_STOP = ("哪些位置", "哪些地方", "哪个章节", "哪个部分", "在文档的",
            "主要是用来", "具体是做什么", "包含哪些", "里面包含",
            "有详细说明", "出现外", "还有哪些", "或者", "这个", "那个",
            "哪些", "什么", "多少", "如何", "是否", "用来", "做的",
            "查询", "功能", "模块", "概念", "说明", "位置", "部分",
            "文档", "系统", "子接口", "支持下", "吗", "呢", "？", "?",
            "的", "了", "在", "和", "与", "中", "下", "或", "和")


def extract_entity(query: str) -> str:
    """问句→实体词: ID正则 > 最长中文段(停用词剥离) > 原句.

    例: "查询收件箱和发件箱接口主要是用来做什么的" → "收件箱和发件箱接口"
        "ZZSJHQZHFW-GN-SJHQ的合格性方法是什么" → "ZZSJHQZHFW-GN-SJHQ"
    """
    import re
    q = (query or "").strip()
    if not q:
        return ""
    from .prose_compiler import ID_PAT
    m = ID_PAT.search(q)
    if m:
        return m.group(0)
    t = q
    for s in _QU_STOP:
        t = t.replace(s, "")
    segs = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,20}", t)
    if segs:
        return max(segs, key=len)
    return q[:20]


def _lcs_cjk(a: str, b: str, min_len: int = 3) -> str:
    """a与b的最长公共子串(限CJK/字母数字, 滑窗DP)."""
    import re

    def _clean(s: str) -> str:
        return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s)

    a, b = _clean(a), _clean(b)
    if len(a) < min_len or len(b) < min_len:
        return ""
    prev = [0] * (len(b) + 1)
    best_len, best_end = 0, 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best_len:
                    best_len, best_end = cur[j], i
        prev = cur
    return a[best_end - best_len:best_end] if best_len >= min_len else ""


def detect_entity(query: str, store: EvidenceStore) -> str:
    """问句→实体: 检索反推法(BM25 top chunk与问句的最长公共子串).

    无词典实体探测: 检索命中的文档片段含实体字面 → LCS即问句中
    实体的最长连续投影. 优于停用词剥离(后者切断"和/或"连接实体).
    例: "查询收件箱和发件箱接口主要是用来做什么的" → "查询收件箱和发件箱接口"
    """
    q = (query or "").strip()
    if not q:
        return ""
    from .prose_compiler import ID_PAT
    m = ID_PAT.search(q)
    if m:
        return m.group(0)
    best = ""
    for h in store.bm25_rank(q, top_k=3):
        c = store._chunk_by_id().get(h.get("chunk_id", ""), {})
        text = (c.get("text") or "")[:2000]
        seg = _lcs_cjk(q, text)
        if len(seg) > len(best):
            best = seg
    return best or extract_entity(q)


@dataclass(slots=True)
class ChannelHit:
    """通道产出的单条命中(统一schema)."""

    chunk_id: str
    type: str
    section: str
    doc: str
    snippet: str
    channel: str
    score: float          # 通道内原始分(仅诊断用, 不参与融合)


@dataclass(slots=True)
class ChannelResult:
    """单通道的ranked list."""

    channel: str
    hits: list[ChannelHit] = field(default_factory=list)
    n: int = 0
    mode: str = "ok"      # ok | degraded | unavailable


class HybridRecaller:
    """五通道混合召回器. dense通道不可用时自动降级为四路.

    rerank: BGE-Reranker-v2-m3精排层(可选)——召回top-K0后逐对打分
    (query, chunk富化文本)重排取top_k, 攻排序质量缺口(R@10).
    """

    def __init__(self, store: EvidenceStore | None = None,
                 use_dense: bool = True, use_unit: bool = True) -> None:
        self.store = store or EvidenceStore()
        self.use_dense = use_dense
        self.use_unit = use_unit
        self._bge: Any = None
        self._dense_ready = False
        self._dense_vecs: dict[str, list[float]] = {}
        self._dense_ids: list[str] = []
        self._reranker: Any = None
        self._id_inverted: dict[str, list[str]] | None = None
        self._unit_ready = False
        self._va: Any = None
        self._tp: Any = None
        self.stats: dict[str, Any] = {"dense_index_s": 0.0,
                                       "dense_queries": 0,
                                       "dense_cache_hits": 0,
                                       "unit_queries": 0,
                                       "rerank_stats": None}

    # ══════════════════════════════════════════════════════
    # 通道实现(每路纯读, 互不依赖)
    # ══════════════════════════════════════════════════════

    def _lexical(self, query: str, doc: str) -> ChannelResult:
        """精确子串 + 双关键词全命中(确定性高精度层).

        深度=_LEXICAL_TOPK(事实性命中全收不引入噪声 — 失败归因:
        30深度截断造成426/2862缺失, 融合层再做配额调度).
        """
        import re
        hits: list[ChannelHit] = []
        if not query:
            return ChannelResult("lexical", hits, 0)
        keywords = [p for p in re.split(r"[的、和与及,，。;；]", query)
                    if len(p) >= 2 and p not in ("这个", "那个", "文档", "系统", "功能")]
        for c in self.store._chunks_data():
            if doc and c.get("doc", "") != doc:
                continue
            ct = c.get("text", "") or ""
            hit = query in ct
            if not hit and len(keywords) >= 2 and all(
                    k in ct for k in keywords[:2]):
                hit = True
            if hit:
                hits.append(ChannelHit(
                    chunk_id=c.get("chunk_id", ""), type=c.get("type", "text"),
                    section=c.get("section", ""), doc=c.get("doc", ""),
                    snippet=ct[:80], channel="lexical", score=1.0))
            if len(hits) >= _LEXICAL_TOPK:
                break
        return ChannelResult("lexical", hits, len(hits))

    def _sparse(self, query: str, doc: str) -> ChannelResult:
        """BM25稀疏检索(部分命中即可参与, 词频-逆文档频率排序)."""
        hits: list[ChannelHit] = []
        for r in self.store.bm25_rank(query, doc=doc, top_k=_DENSE_TOPK):
            hits.append(ChannelHit(
                chunk_id=r["chunk_id"], type=r["type"], section=r["section"],
                doc=r["doc"], snippet=r.get("snippet", "")[:80],
                channel="sparse", score=r.get("score", 0.0)))
        return ChannelResult("sparse", hits, len(hits))

    def _structural(self, query: str, doc: str) -> ChannelResult:
        """ID-Graph硬桥: 实体→mentions→全部出现章节→章节chunks(带doc消歧).

        含ID前缀层级扩展(优先): 父实体ID→全部子ID所在chunks —
        子实体(直接层级关系)排在mention章节chunks之前(更specific).
        (失败归因: 225个盲区全部是'语义子实体'chunk — 子功能
        '服务状态采集'文本不含父名'服务运行控制', 但其ID
        PZXQ-GN-FWYXKZ-FWZTCJ是父ID的前缀延长 → 前缀桥接).
        """
        hits: list[ChannelHit] = []
        rec = self.store.entity_mentions(query, doc=doc)
        parent_id = rec.get("entity_id", "") if rec is not None else ""
        # ① ID前缀层级扩展(子实体, 优先)
        if parent_id:
            for cid, c in self._id_prefix_chunks(parent_id, doc):
                if len(hits) >= _DENSE_TOPK:
                    break
                hits.append(ChannelHit(
                    chunk_id=cid, type=c.get("type", "text"),
                    section=c.get("section", ""), doc=c.get("doc", ""),
                    snippet=(c.get("text") or "")[:80],
                    channel="structural", score=0.85))
        # ② mention章节chunks
        if rec is not None:
            hop_doc = doc or rec.get("doc", "")
            for h in self.store.section_chunks(rec.get("sections", []),
                                               doc=hop_doc,
                                               limit=_DENSE_TOPK - len(hits)):
                hits.append(ChannelHit(
                    chunk_id=h["chunk_id"], type=h["type"], section=h["section"],
                    doc=h["doc"], snippet=h.get("snippet", "")[:80],
                    channel="structural", score=0.9))
        return ChannelResult("structural", hits, len(hits))

    def _id_prefix_chunks(self, parent_id: str,
                          doc: str) -> list[tuple[str, dict]]:
        """父ID→[(chunk_id, chunk)]: 文本含'父ID-…'前缀延长ID的chunks.

        依赖懒构建的ID倒排(全库chunk文本的ID提取, 一次性).
        """
        if self._id_inverted is None:
            inv: dict[str, list[str]] = defaultdict(list)
            from .prose_compiler import ID_PAT
            for c in self.store._chunks_data():
                for m in ID_PAT.finditer((c.get("text") or "")[:3000]):
                    inv[m.group(0)].append(c.get("chunk_id", ""))
            self._id_inverted = {k: list(dict.fromkeys(v))
                                 for k, v in inv.items()}
        prefix = parent_id + "-"
        out: list[tuple[str, dict]] = []
        seen: set[str] = set()
        for full_id, cids in self._id_inverted.items():
            if not full_id.startswith(prefix):
                continue
            for cid in cids:
                if cid in seen:
                    continue
                c = self.store._chunk_by_id().get(cid)
                if c is None or (doc and c.get("doc", "") != doc):
                    continue
                seen.add(cid)
                out.append((cid, c))
        return out

    def _multimodal(self, query: str, doc: str) -> ChannelResult:
        """VLM图片分析直查: key_elements↔query匹配→(doc,fig)→image chunk."""
        import re
        hits: list[ChannelHit] = []
        img_idx = self.store._image_chunk_index()
        for a in self.store.image_hits(query[:30]):
            fm = re.search(r"fig_(\d+)", a.get("image_path", ""))
            if fm is None:
                continue
            c = img_idx.get((a.get("doc", ""), fm.group(1)))
            if c is None or (doc and c.get("doc", "") != doc):
                continue
            caption = " ".join(a.get("caption") or [])
            snippet = (caption + " " + "、".join(a.get("elements") or []))[:80]
            hits.append(ChannelHit(
                chunk_id=c.get("chunk_id", ""), type=c.get("type", "image"),
                section=c.get("section", ""), doc=c.get("doc", ""),
                snippet=snippet, channel="multimodal", score=0.85))
            if len(hits) >= _DENSE_TOPK:
                break
        return ChannelResult("multimodal", hits, len(hits))

    # ── dense通道(BGE, 惰性) ───────────────────────────────

    # ── unit通道(结构单元多向量, 惰性) ─────────────────────

    def _ensure_unit(self) -> str:
        """unit通道初始化: 图/表单元索引(VaColpaliIndex/TablePaliIndex).

        任一模态可用即ok; 索引缓存命中时加载为秒级.
        """
        if self._unit_ready:
            return "ok" if (self._va or self._tp) else "unavailable"
        self._unit_ready = True
        if not self.use_unit:
            return "unavailable"
        try:
            from algorithms.table_late import TablePaliIndex  # noqa: PLC0415
            from algorithms.va_colpali import VaColpaliIndex  # noqa: PLC0415
        except ImportError:
            return "unavailable"
        self._va = VaColpaliIndex()
        self._tp = TablePaliIndex()
        va_ok = self._va.ensure() == "ok"
        tp_ok = self._tp.ensure() == "ok"
        if not (va_ok or tp_ok):
            self._va = self._tp = None
            return "unavailable"
        return "ok"

    def _unit(self, query: str, doc: str) -> ChannelResult:
        """单元通道: 图节点/表行多向量MaxSim+IDF(详见unit_retrieval).

        候选=doc过滤后有单元索引的image+table chunk(text chunk由
        dense/lexical覆盖). 产出概率性排序信号(进cascade Tier2 RRF).
        """
        hits: list[ChannelHit] = []
        mode = self._ensure_unit()
        if mode == "unavailable" or not query:
            return ChannelResult("unit", hits, 0,
                                 "unavailable" if not query else mode)
        self.stats["unit_queries"] += 1
        by_id = self.store._chunk_by_id()
        img_cands: list[str] = []
        tab_cands: list[str] = []
        for cid in (self._va.indexed_ids if self._va else []) + \
                   (self._tp.indexed_ids if self._tp else []):
            c = by_id.get(cid)
            if c is None:
                continue
            if doc and c.get("doc", "") != doc:
                continue
            if c.get("type") == "image":
                img_cands.append(cid)
            elif c.get("type") == "table":
                tab_cands.append(cid)
        scores: dict[str, float] = {}
        if self._va and img_cands:
            scores.update(self._va.score(query, img_cands))
        if self._tp and tab_cands:
            scores.update(self._tp.score(query, tab_cands))
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:_DENSE_TOPK]
        for cid, sc in ranked:
            c = by_id.get(cid, {})
            hits.append(ChannelHit(
                chunk_id=cid, type=c.get("type", "text"),
                section=c.get("section", ""), doc=c.get("doc", ""),
                snippet=(c.get("text") or "")[:80],
                channel="unit", score=round(float(sc), 6)))
        return ChannelResult("unit", hits, len(hits), "ok")

    def _rich_text(self, c: dict) -> str:
        """chunk的检索富化文本: image chunk用caption+VLM key_elements."""
        if c.get("type") != "image":
            return (c.get("text") or "")[:512]
        import re
        caption = c.get("meta", {}).get("caption", "") or ""
        extra = []
        fm = re.search(r"fig_(\d+)", c.get("image_path", ""))
        if fm:
            for a in self.store._images_data():
                if a.get("doc", "") == c.get("doc", "") and \
                        f"fig_{fm.group(1)}" in a.get("image_path", ""):
                    ana = a.get("analysis", {})
                    extra = ana.get("key_elements", [])[:12]
                    extra.append(ana.get("summary", ""))
                    break
        body = " ".join(x for x in [caption] + extra if x)
        return (body or c.get("text") or "")[:512]

    def _ensure_dense(self) -> str:
        """dense通道初始化: BGE模型加载 + chunk向量索引(磁盘缓存). 返回mode."""
        if self._dense_ready:
            return "ok"
        self._dense_ready = True
        if not self.use_dense:
            return "unavailable"
        try:
            from algorithms.common.bge_local import BgeLocal
            self._bge = BgeLocal(cache_path=None)  # 索引缓存独立管理
        except ImportError:
            return "unavailable"
        mode = self._bge.ensure()
        if mode == "unavailable":
            return "unavailable"
        if DENSE_CACHE.exists():
            try:
                with open(DENSE_CACHE, "rb") as f:
                    self._dense_vecs = pickle.load(f)
            except (pickle.UnpicklingError, EOFError, OSError):
                self._dense_vecs = {}
        if self._dense_vecs:
            self._dense_ids = list(self._dense_vecs)
            self.stats["dense_cache_hits"] = len(self._dense_ids)
            return "ok"
        t0 = time.time()
        texts = [self._rich_text(c) for c in self.store._chunks_data()]
        ids = [c.get("chunk_id", "") for c in self.store._chunks_data()]
        vecs = self._bge.embed(texts)
        self._dense_vecs = {i: vecs[t] for i, t in zip(ids, texts) if vecs.get(t)}
        self._dense_ids = [i for i in ids if i in self._dense_vecs]
        self.stats["dense_index_s"] = round(time.time() - t0, 1)
        DENSE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(DENSE_CACHE, "wb") as f:
            pickle.dump(self._dense_vecs, f)
        return "ok"

    def _dense(self, query: str, doc: str) -> ChannelResult:
        """BGE稠密检索: query向量↔chunk向量余弦top-k."""
        hits: list[ChannelHit] = []
        if not query:
            return ChannelResult("dense", hits, 0, "degraded")
        mode = self._ensure_dense()
        if mode != "ok" or self._bge is None:
            return ChannelResult("dense", hits, 0, "unavailable")
        self.stats["dense_queries"] += 1
        qvec = self._bge.embed([_QUERY_PREFIX + query[:200]])
        q = qvec.get(_QUERY_PREFIX + query[:200])
        if not q:
            return ChannelResult("dense", hits, 0, "degraded")
        scored: list[tuple[float, str]] = []
        for cid in self._dense_ids:
            if doc:
                chunk = self.store._chunk_by_id().get(cid, {})
                if chunk.get("doc", "") != doc:
                    continue
            v = self._dense_vecs[cid]
            dot = sum(a * b for a, b in zip(q, v))
            scored.append((dot, cid))
        scored.sort(key=lambda x: -x[0])
        for rank, (s, cid) in enumerate(scored[:_DENSE_TOPK], 1):
            c = self.store._chunk_by_id().get(cid, {})
            hits.append(ChannelHit(
                chunk_id=cid, type=c.get("type", "text"),
                section=c.get("section", ""), doc=c.get("doc", ""),
                snippet=(c.get("text") or "")[:80],
                channel="dense", score=round(s, 4)))
        return ChannelResult("dense", hits, len(hits))

    # ══════════════════════════════════════════════════════
    # 融合与入口
    # ══════════════════════════════════════════════════════

    def recall(self, query: str, doc: str = "", top_k: int = 20,
               channels: tuple[str, ...] = CHANNELS, k_rrf: int = _RRF_K,
               quota: int | None = None,
               fusion: str = "cascade",
               rerank: bool = False) -> dict[str, Any]:
        """多路召回入口: 通道产出 → 融合(rrf|cascade) → (可选)章节配额
        → (可选)reranker精排.

        fusion="rrf":     全通道等权RRF(民主投票).
        fusion="cascade": 事实性通道(lexical/structural/multimodal)直通
                          + 概率性通道(sparse/dense)RRF填充剩余配额.
        rerank: 先召回top-K0(=top_k*2.5)再cross-encoder精排取top_k;
                事实直通席位(tier=factual)保持头部不动摇, 精排作用
                于其余候选(重排不推翻确定性命中).
        返回 {hits, per_channel, fusion, degraded}.
        """
        results: dict[str, ChannelResult] = {}
        for ch in channels:
            fn = getattr(self, f"_{ch}")
            results[ch] = fn(query, doc)

        PROBABILISTIC = ("sparse", "dense", "unit")
        by_id = self.store._chunk_by_id()

        def _hit_dict(cid: str, tag: str, score: float) -> dict[str, Any] | None:
            c = by_id.get(cid)
            if c is None:
                return None
            chs = [ch for ch, r in results.items()
                   if any(h.chunk_id == cid for h in r.hits)]
            return {
                "chunk_id": cid, "type": c.get("type", "text"),
                "section": c.get("section", ""), "doc": c.get("doc", ""),
                "snippet": (c.get("text") or "")[:80],
                "rrf_score": round(score, 6), "channels": chs,
                "rank": 0, "tier": tag}

        out: list[dict[str, Any]] = []
        seen: set[str] = set()

        if fusion == "cascade":
            # Tier1: 事实性通道直通, 最小席位调度
            # 模态/章节召回是集合判定(≥1命中即得分) → 窄通道保底席位;
            # structural通道内含两路命中(ID前缀子实体优先+mention
            # 章节chunks), 融合层统一以"章节补全"调度(只进未覆盖
            # 章节, 4席 — 独立前缀席位实测等价R@20且Sec略降).
            seats = {"structural": 4, "multimodal": 2}
            reserved = sum(v for ch, v in seats.items() if ch in results)
            covered_secs: set[str] = set()

            # lexical: 顺序直通(完整子串命中)到预算位
            if "lexical" in results:
                lex_budget = top_k - reserved
                for h in results["lexical"].hits:
                    if len(out) >= lex_budget:
                        break
                    if h.score < 1.0 or h.chunk_id in seen:
                        continue
                    d = _hit_dict(h.chunk_id, "factual",
                                  1.0 / (1 + len(out)))
                    if d is None:
                        continue
                    seen.add(h.chunk_id)
                    covered_secs.add(h.section)
                    d["rank"] = len(out) + 1
                    out.append(d)
            # structural(前缀子实体+mention章节): 章节补全席位
            if "structural" in results:
                used = 0
                for h in results["structural"].hits:
                    if len(out) >= top_k or used >= seats["structural"]:
                        break
                    if not h.section or h.section in covered_secs:
                        continue
                    if h.chunk_id in seen:
                        continue
                    d = _hit_dict(h.chunk_id, "factual",
                                  1.0 / (1 + len(out)))
                    if d is None:
                        continue
                    seen.add(h.chunk_id)
                    covered_secs.add(h.section)
                    d["rank"] = len(out) + 1
                    out.append(d)
                    used += 1
            # multimodal: figure模态保底席位
            if "multimodal" in results:
                used = 0
                for h in results["multimodal"].hits:
                    if len(out) >= top_k or used >= seats["multimodal"]:
                        break
                    if h.chunk_id in seen:
                        continue
                    d = _hit_dict(h.chunk_id, "factual",
                                  1.0 / (1 + len(out)))
                    if d is None:
                        continue
                    seen.add(h.chunk_id)
                    d["rank"] = len(out) + 1
                    out.append(d)
                    used += 1
            # Tier2: 概率通道RRF填充剩余
            rest = top_k - len(out)
            if rest > 0:
                scores: dict[str, float] = defaultdict(float)
                for ch in PROBABILISTIC:
                    if ch not in results:
                        continue
                    for rank, h in enumerate(results[ch].hits, 1):
                        scores[h.chunk_id] += 1.0 / (k_rrf + rank)
                for cid, s in sorted(scores.items(), key=lambda x: -x[1]):
                    if rest <= 0 or len(out) >= top_k:
                        break
                    if cid in seen:
                        continue
                    d = _hit_dict(cid, "rrf", s)
                    if d is None:
                        continue
                    seen.add(cid)
                    d["rank"] = len(out) + 1
                    out.append(d)
                    rest -= 1
        else:
            # 纯RRF: 全通道等权
            scores = defaultdict(float)
            for ch, res in results.items():
                for rank, h in enumerate(res.hits, 1):
                    scores[h.chunk_id] += 1.0 / (k_rrf + rank)
            for cid, s in sorted(scores.items(), key=lambda x: -x[1]):
                if len(out) >= top_k:
                    break
                d = _hit_dict(cid, "rrf", s)
                if d is None:
                    continue
                d["rank"] = len(out) + 1
                out.append(d)

        # 章节配额后处理(可选)
        if quota is not None:
            kept: list[dict[str, Any]] = []
            sec_count: dict[str, int] = defaultdict(int)
            for d in out:
                sec = d["section"]
                if sec_count[sec] >= quota:
                    continue
                sec_count[sec] += 1
                d["rank"] = len(kept) + 1
                kept.append(d)
            out = kept

        # reranker精排(可选): factual直通位保序在前, 其余按cross-encoder重排
        if rerank and out:
            out = self._apply_rerank(query, out, top_k)
        return {
            "hits": out,
            "per_channel": {ch: {"n": r.n, "mode": r.mode}
                            for ch, r in results.items()},
            "fusion": {"strategy": fusion, "k_rrf": k_rrf,
                       "channels": list(channels), "rerank": rerank},
            "degraded": [ch for ch, r in results.items() if r.mode != "ok"],
        }

    def _apply_rerank(self, query: str, hits: list[dict[str, Any]],
                      top_k: int) -> list[dict[str, Any]]:
        """cross-encoder精排: factual直通位保序在前, 其余按rerank分重排.

        设计: 确定性命中(tier=factual)不被概率重排推翻——重排只解决
        "排序质量"(RRF/bm25候选的相对次序), 不制造新的不确定性来源.
        """
        if self._reranker is None:
            from .reranker import BgeReranker
            self._reranker = BgeReranker()
        mode = self._reranker.ensure()
        self.stats["rerank_stats"] = dict(self._reranker.stats)
        if mode == "unavailable":
            return hits
        by_id = self.store._chunk_by_id()
        factual = [h for h in hits if h.get("tier") == "factual"]
        others = [h for h in hits if h.get("tier") != "factual"]
        if not others:
            return hits
        pairs = [(query, self._rich_text(by_id.get(h["chunk_id"], {}))[:400])
                 for h in others]
        scores = self._reranker.score(pairs)
        ranked = sorted(zip(others, scores), key=lambda x: -x[1])
        keep = top_k - len(factual)
        merged = factual + [
            {**h, "rerank_score": round(s, 4), "rank": 0}
            for h, s in ranked[:max(keep, 0)]]
        for i, h in enumerate(merged, 1):
            h["rank"] = i
        return merged
