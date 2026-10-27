"""EvidenceStore: 现有数据资产的统一读取层 (确定性预计算层).

适配的资产(全部懒加载, 缺失时优雅返回空):
  pair_dataset(366对) / anchors_v2(373图) / scene_drift_census(315对) /
  scene_tier1 + anchor_sc2/tier1_v2 / scene_vlm + anchor_sc2/vlm /
  anchor_sc2/ocr / id_document_graph(2181节点) / srs_chunks(5231) /
  srs_image_analyses(379图)

锚点优先级(与M16一致): census重对齐后的new_embed(高可信) > pair的visio_anchor.
ID正则使用修复版(前缀≤16字符, 修复旧8字符限制).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .prose_compiler import ID_PAT

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data/gjb_438c"
PAIR_ROOT = DATA / "pair_dataset"
ANCHOR_V2 = DATA / "anchor_v2/anchors_v2.json"
CENSUS = DATA / "anchor_v2/scene_drift_census.json"
SCENE_TIER1 = DATA / "anchor_v2/scene_tier1.json"
SC2_TIER1 = DATA / "anchor_sc2/tier1_discrepancies_v2.json"
SCENE_VLM = DATA / "anchor_v2/scene_vlm_extractions.json"
SC2_VLM = DATA / "anchor_sc2/vlm_extractions.json"
SC2_OCR = DATA / "anchor_sc2/ocr_extractions.json"
ID_GRAPH = DATA / "data_assets/graph/id_document_graph.json"
CHUNKS = DATA / "data_assets/chunks/srs_chunks.json"
IMAGE_ANALYSES = DATA / "data_assets/chunks/srs_image_analyses.json"

SCENE_PREFIX = {
    "1": "sc1_usecase_capability", "2": "sc2_flowchart_usecase",
    "3": "sc3_interface_interface", "4": "sc4_flowchart_capability",
    "5": "sc5_function_capability", "7": "sc7_usecase_usecase",
    "8": "sc8_pure_image",
}

_CTX_NAME = re.compile(r'<p>([^<]{2,30})</p>')


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


class EvidenceStore:
    """黑板的确定性证据仓储. 所有方法纯读, 无副作用."""

    def __init__(self, base: Path | None = None) -> None:
        self.base = base or BASE
        self._pairs: dict[str, Path] | None = None
        self._v2_idx: dict[tuple[str, str], dict] | None = None
        self._census: dict[str, Any] | None = None
        self._scene_tier1: dict[str, Any] | None = None
        self._sc2_tier1: dict[str, Any] | None = None
        self._scene_vlm: dict[str, Any] | None = None
        self._sc2_vlm: dict[str, Any] | None = None
        self._sc2_ocr: dict[str, Any] | None = None
        self._chunks: list[dict] | None = None
        self._images: list[dict] | None = None
        self._id_index: dict[str, dict] | None = None
        self._chunk_idx: dict[str, dict] | None = None
        self._img_chunk_idx: dict[tuple[str, str], dict] | None = None

    # ── pair_dataset ──────────────────────────────────────
    def _pair_index(self) -> dict[str, Path]:
        if self._pairs is None:
            idx: dict[str, Path] = {}
            if self.base and PAIR_ROOT.exists():
                for scene_dir in sorted(PAIR_ROOT.iterdir()):
                    if not scene_dir.is_dir():
                        continue
                    for pd in scene_dir.iterdir():
                        if pd.is_dir() and (pd / "meta.json").exists():
                            idx[pd.name] = pd
            self._pairs = idx
        return self._pairs

    def pair_dir(self, pair_id: str) -> Path | None:
        return self._pair_index().get(pair_id)

    def pair_meta(self, pair_id: str) -> dict[str, Any]:
        pd = self.pair_dir(pair_id)
        if pd is None:
            return {}
        meta = _load_json(pd / "meta.json")
        return meta if isinstance(meta, dict) else {}

    @staticmethod
    def scene_of(pair_id: str) -> str:
        return SCENE_PREFIX.get(pair_id.split("_")[0], "")

    def pair_doc(self, pair_id: str) -> str:
        return self.pair_meta(pair_id).get("doc", "")

    # ── 锚点(census重对齐 > visio_anchor) ─────────────────
    def _anchor_v2_index(self) -> dict[tuple[str, str], dict]:
        if self._v2_idx is None:
            idx: dict[tuple[str, str], dict] = {}
            data = _load_json(ANCHOR_V2)
            if isinstance(data, dict):
                for doc, d in data.items():
                    for s in d.get("structures", []):
                        key = (doc, s.get("embed_index", "").split(":")[0])
                        n_text = sum(1 for n in s.get("nodes", []) if n.get("text"))
                        if key not in idx or n_text > sum(
                                1 for n in idx[key].get("nodes", []) if n.get("text")):
                            idx[key] = s
            self._v2_idx = idx
        return self._v2_idx

    def _census_data(self) -> dict[str, Any]:
        if self._census is None:
            data = _load_json(CENSUS)
            self._census = data if isinstance(data, dict) else {}
        return self._census

    def pair_anchor(self, pair_id: str) -> dict[str, Any] | None:
        """锚点结构: census重对齐(高可信) > pair的visio_anchor.json."""
        c = self._census_data().get(pair_id, {})
        if c.get("status") == "anchored" and c.get("new_embed"):
            entry = self._anchor_v2_index().get((c.get("doc", ""),
                                                  c["new_embed"].split(":")[0]))
            if entry is not None:
                return entry
        pd = self.pair_dir(pair_id)
        if pd is not None:
            va = _load_json(pd / "visio_anchor.json")
            if isinstance(va, dict) and va.get("nodes") is not None:
                return va
        return None

    def drift(self, pair_id: str) -> dict[str, Any] | None:
        d = self._census_data().get(pair_id)
        return d if isinstance(d, dict) else None

    # ── 感知通道提取结果 ──────────────────────────────────
    def vlm_extraction(self, pair_id: str) -> dict[str, Any] | None:
        if self._scene_vlm is None:
            data = _load_json(SCENE_VLM)
            self._scene_vlm = data if isinstance(data, dict) else {}
        if self._sc2_vlm is None:
            data = _load_json(SC2_VLM)
            self._sc2_vlm = data if isinstance(data, dict) else {}
        got = self._scene_vlm.get(pair_id) or self._sc2_vlm.get(pair_id)
        return got if isinstance(got, dict) else None

    def ocr_blocks(self, pair_id: str) -> dict[str, Any] | None:
        if self._sc2_ocr is None:
            data = _load_json(SC2_OCR)
            self._sc2_ocr = data if isinstance(data, dict) else {}
        got = self._sc2_ocr.get(pair_id)
        return got if isinstance(got, dict) else None

    # ── Tier1预计算比较 ───────────────────────────────────
    def tier1(self, pair_id: str) -> dict[str, Any] | None:
        if pair_id.startswith("2_"):
            if self._sc2_tier1 is None:
                data = _load_json(SC2_TIER1)
                self._sc2_tier1 = data if isinstance(data, dict) else {}
            got = self._sc2_tier1.get(pair_id)
        else:
            if self._scene_tier1 is None:
                data = _load_json(SCENE_TIER1)
                self._scene_tier1 = data if isinstance(data, dict) else {}
            got = self._scene_tier1.get(pair_id)
        return got if isinstance(got, dict) else None

    # ── ID-Graph实体索引 ──────────────────────────────────
    def _id_graph_index(self) -> dict[str, dict]:
        if self._id_index is None:
            idx: dict[str, dict] = {}
            g = _load_json(ID_GRAPH)
            if isinstance(g, dict):
                nodes = {n["id"]: n for n in g.get("nodes", [])}
                for e in g.get("edges", []):
                    src, tgt = e.get("source", ""), e.get("target", "")
                    if not (src.startswith("E_") and tgt.startswith("M_")):
                        continue
                    ent_key = src[2:]
                    m = nodes.get(tgt, {})
                    ctx = m.get("context", "")
                    full = ID_PAT.search(ctx)
                    rec = idx.setdefault(ent_key, {
                        "entity_key": ent_key, "doc": m.get("doc", ""),
                        "full_id": full.group(0) if full else ent_key,
                        "mentions": [],
                    })
                    if full and not rec["full_id"]:
                        rec["full_id"] = full.group(0)
                    nm = _CTX_NAME.search(ctx)
                    rec["mentions"].append({
                        "location": m.get("location", ""),
                        "section": m.get("section", ""),
                        "doc": m.get("doc", ""),
                        "name": nm.group(1).strip() if nm else "",
                        "context": ctx[:120],
                    })
            self._id_index = idx
        return self._id_index

    def entity_mentions(self, id_or_name: str, doc: str = "") -> dict[str, Any] | None:
        """ID或名称 → {entity_id, doc, mentions, sections}.

        doc非空时优先返回该文档的同名实体(消解跨文档同名歧义:
        '修改数据'在01/04文档各有一套mention, 用04的节号拉01的
        chunk会全部错配).
        """
        if not id_or_name:
            return None
        idx = self._id_graph_index()
        is_id = bool(ID_PAT.fullmatch(id_or_name.strip()))
        rec = None
        if is_id:
            key = id_or_name.strip()
            rec = idx.get(key)
            if rec is None:
                for v in idx.values():
                    if v["full_id"] == key:
                        rec = v
                        break
        else:
            name = id_or_name.strip()
            for v in idx.values():
                if any(name in (m["name"] or "") or name in m["context"]
                       for m in v["mentions"]):
                    rec = v
                    break
        if rec is None:
            return None
        if doc and rec.get("doc", "") != doc:
            # 跨文档歧义: 找同doc的同名实体
            alt = None
            for v in idx.values():
                if v.get("doc", "") != doc:
                    continue
                if any(id_or_name.strip() in (m["name"] or "")
                       or id_or_name.strip() in m["context"]
                       for m in v["mentions"]):
                    alt = v
                    break
            if alt is not None:
                rec = alt
        return {
            "entity_id": rec["full_id"], "entity_key": rec["entity_key"],
            "doc": rec["doc"], "n_mentions": len(rec["mentions"]),
            "mentions": rec["mentions"][:30],
            "sections": sorted({m["section"] for m in rec["mentions"] if m["section"]}),
            "names": sorted({m["name"] for m in rec["mentions"] if m["name"]}),
        }

    # ── 结构化chunks ──────────────────────────────────────
    def _chunks_data(self) -> list[dict]:
        if self._chunks is None:
            data = _load_json(CHUNKS)
            self._chunks = data if isinstance(data, list) else []
        return self._chunks

    # ── BM25-lite索引(中文2字滑窗+ASCII token, 离线确定性) ──
    _BM25_K1 = 1.5
    _BM25_B = 0.75

    @staticmethod
    def _terms_of(text: str) -> list[str]:
        """文本 → 检索词: CJK 2字滑窗 + ASCII token(≥2字符)."""
        t = text or ""
        cjk = re.findall(r"[\u4e00-\u9fff]", t)
        bigrams = {"".join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
        ascii_tokens = {w.lower() for w in re.findall(r"[A-Za-z0-9]{2,}", t)}
        return sorted(bigrams | ascii_tokens)

    def _bm25_stats(self) -> tuple[dict[str, int], list[int], float]:
        """(df, 每chunk词数, 平均词数) — 懒构建一次."""
        if getattr(self, "_bm25_cache", None) is None:
            df: dict[str, int] = {}
            lens: list[int] = []
            for c in self._chunks_data():
                terms = set(self._terms_of(c.get("text", "")))
                lens.append(len(terms))
                for t in terms:
                    df[t] = df.get(t, 0) + 1
            avg = sum(lens) / max(len(lens), 1)
            self._bm25_cache = (df, lens, avg)
        return self._bm25_cache

    def bm25_rank(self, query: str, doc: str = "", top_k: int = 20
                  ) -> list[dict[str, Any]]:
        """BM25排序chunks(召回层: 查询词部分命中即可, 替代'双关键词全命中')."""
        chunks = self._chunks_data()
        if not chunks:
            return []
        df, lens, avgdl = self._bm25_stats()
        n = len(chunks)
        q_terms = set(self._terms_of(query))
        if not q_terms:
            return []
        idf = {t: max(0.0, __import__("math").log(
            1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)))
            for t in q_terms}
        scored = []
        for i, c in enumerate(chunks):
            if doc and c.get("doc", "") != doc:
                continue
            text = c.get("text", "")
            tf_raw = {}
            for t in q_terms:
                cnt = text.count(t) if re.fullmatch(r"[\u4e00-\u9fff]{2}", t) \
                    else len(re.findall(re.escape(t), text, re.I))
                if cnt:
                    tf_raw[t] = cnt
            if not tf_raw:
                continue
            dl = max(lens[i], 1)
            score = 0.0
            for t, tf in tf_raw.items():
                score += idf.get(t, 0.0) * tf * (self._BM25_K1 + 1) / (
                    tf + self._BM25_K1 * (1 - self._BM25_B + self._BM25_B * dl / avgdl))
            scored.append((score, c))
        scored.sort(key=lambda x: -x[0])
        return [{"chunk_id": c.get("chunk_id", ""), "type": c.get("type", "text"),
                 "section": c.get("section", ""), "doc": c.get("doc", ""),
                 "snippet": c.get("text", "")[:80],
                 "score": round(s, 3), "rank": "bm25"}
                for s, c in scored[:top_k]]

    def section_chunks(self, sections: list[str], doc: str = "",
                       limit: int = 30) -> list[dict[str, Any]]:
        """章节 → 该章节的chunks(ID-mention多跳: link-following)."""
        if not sections:
            return []
        sec_set = {s for s in sections if s}
        out = []
        for c in self._chunks_data():
            if doc and c.get("doc", "") != doc:
                continue
            if c.get("section", "") in sec_set:
                out.append({"chunk_id": c.get("chunk_id", ""),
                            "type": c.get("type", "text"),
                            "section": c.get("section", ""),
                            "doc": c.get("doc", ""),
                            "snippet": c.get("text", "")[:80],
                            "rank": "section_hop"})
            if len(out) >= limit:
                break
        return out

    def search_chunks(self, text: str, doc: str = "",
                      limit: int = 20) -> list[dict[str, Any]]:
        """两层召回: ①精确/关键词(高精度) ②BM25补充(召回).

        旧版要求"前2关键词全部子串命中"——排版变体直接漏;
        BM25层按词频-逆文档频率排序, 部分命中即可参与.
        """
        if not text:
            return []
        hits: list[dict[str, Any]] = []
        keywords = [p for p in re.split(r"[的、和与及,，。;；]", text)
                    if len(p) >= 2 and p not in ("这个", "那个", "文档", "系统", "功能")]
        for c in self._chunks_data():
            if doc and c.get("doc", "") != doc:
                continue
            ct = c.get("text", "")
            hit = text in ct
            if not hit and len(keywords) >= 2 and all(k in ct for k in keywords[:2]):
                hit = True
            if hit:
                hits.append({
                    "chunk_id": c.get("chunk_id", ""),
                    "type": c.get("type", "text"),
                    "section": c.get("section", ""),
                    "doc": c.get("doc", ""),
                    "snippet": ct[:80],
                    "rank": "exact",
                })
            if len(hits) >= limit:
                break
        if len(hits) < limit:
            seen_ids = {h["chunk_id"] for h in hits}
            for r in self.bm25_rank(text, doc=doc, top_k=limit * 2):
                if r["chunk_id"] in seen_ids:
                    continue
                hits.append(r)
                seen_ids.add(r["chunk_id"])
                if len(hits) >= limit:
                    break
        return hits

    # ── VLM图片分析(379图, 旧M5轨道资产) ──────────────────
    def _images_data(self) -> list[dict]:
        if self._images is None:
            data = _load_json(IMAGE_ANALYSES)
            analyses = data.get("analyses", []) if isinstance(data, dict) else []
            self._images = analyses if isinstance(analyses, list) else []
        return self._images

    def image_hits(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        if not name:
            return []
        low = name.lower()
        results = []
        for a in self._images_data():
            elements = a.get("analysis", {}).get("key_elements", [])
            if any(low in str(e).lower() or str(e).lower() in low for e in elements):
                results.append({
                    "image_path": a.get("image_path", ""),
                    "figure_type": a.get("analysis", {}).get("figure_type", ""),
                    "caption": a.get("caption", ""),
                    "elements": elements[:8],
                    "doc": a.get("doc", ""),
                })
            if len(results) >= limit:
                break
        return results

    # ── 召回v3: 四层融合(方向A召回升级) ────────────────────

    def _chunk_by_id(self) -> dict[str, dict]:
        """chunk_id → chunk 懒索引(v3融合层用)."""
        if self._chunk_idx is None:
            self._chunk_idx = {c.get("chunk_id", ""): c
                               for c in self._chunks_data()}
        return self._chunk_idx

    def _image_chunk_index(self) -> dict[tuple[str, str], dict]:
        """(doc, fig号) → image chunk (VLM分析反查章节锚)."""
        if self._img_chunk_idx is None:
            idx: dict[tuple[str, str], dict] = {}
            for c in self._chunks_data():
                if c.get("type") != "image":
                    continue
                m = re.search(r"fig_(\d+)", c.get("image_path", ""))
                if m:
                    idx[(c.get("doc", ""), m.group(1))] = c
            self._img_chunk_idx = idx
        return self._img_chunk_idx

    def search_chunks_v3(self, text: str, doc: str = "", limit: int = 20,
                         per_section: int = 2) -> list[dict[str, Any]]:
        """四层召回+图片富化+章节多样性.

        层级(优先级递减): ①精确/词法 ②ID-mention硬桥多跳
        ③VLM图片分析直查(key_elements匹配, 映射回image chunk带章节)
        ④BM25(每章节配额per_section, 保证多章节覆盖).

        解决的三个失败模式(eval_recall错误分析):
          - 图片chunk text全为"[图片]": 层③绕过BM25直查VLM分析
          - 短实体BM25 bigram噪声: 层①精确优先
          - 多章节覆盖不足: 层②硬桥全sections + 层④章节配额
        """
        if not text:
            return []
        hits: list[dict[str, Any]] = []
        seen: set[str] = set()
        by_id = self._chunk_by_id()

        def _add(chunk: dict, rank: str, snippet: str = "") -> bool:
            cid = chunk.get("chunk_id", "")
            if not cid or cid in seen:
                return False
            seen.add(cid)
            hits.append({
                "chunk_id": cid,
                "type": chunk.get("type", "text"),
                "section": chunk.get("section", ""),
                "doc": chunk.get("doc", ""),
                "snippet": (snippet or chunk.get("text", "") or "")[:80],
                "rank": rank,
            })
            return True

        # ① 精确/词法(高精度层, 与v2同逻辑) + 章节配额
        #    (精确命中是稀缺信号全扫描, 配额防同章节多命中挤掉
        #    深层小节——section残留失败的主因: 3-4级小节被先到者填满)
        keywords = [p for p in re.split(r"[的、和与及,，。;；]", text)
                    if len(p) >= 2 and p not in ("这个", "那个", "文档", "系统", "功能")]
        exact_sec: dict[str, int] = {}
        exact_pool: list[dict] = []
        for c in self._chunks_data():
            if doc and c.get("doc", "") != doc:
                continue
            ct = c.get("text", "")
            hit = text in ct
            if not hit and len(keywords) >= 2 and all(k in ct for k in keywords[:2]):
                hit = True
            if hit:
                exact_pool.append(c)
        for c in exact_pool:
            s = c.get("section", "")
            if exact_sec.get(s, 0) >= per_section and len(exact_pool) > limit:
                continue
            exact_sec[s] = exact_sec.get(s, 0) + 1
            _add(c, "exact")
            if len(hits) >= limit:
                break

        # ② ID-mention硬桥多跳: ID或实体名→全部出现章节→各章节chunk
        #    (带doc消歧: 优先同文档的同名实体)
        rec = self.entity_mentions(text, doc=doc)
        if rec is not None:
            hop_doc = doc or rec.get("doc", "")
            for h in self.section_chunks(rec.get("sections", []), doc=hop_doc):
                c = by_id.get(h.get("chunk_id", ""))
                if c is not None:
                    _add(c, "id_hop")

        # ③ VLM图片分析直查: key_elements命中→(doc,fig)→image chunk(带章节)
        for a in self.image_hits(text[:30]):
            fm = re.search(r"fig_(\d+)", a.get("image_path", ""))
            if fm is None:
                continue
            c = self._image_chunk_index().get((a.get("doc", ""), fm.group(1)))
            if c is None or (doc and c.get("doc", "") != doc):
                continue
            caption = " ".join(a.get("caption") or [])
            snippet = (caption + " " + "、".join(a.get("elements") or []))[:80]
            _add(c, "image_vlm", snippet=snippet)

        # ④ BM25补充 + 章节配额(多样性)
        if len(hits) < limit:
            sec_count: dict[str, int] = {}
            for r in self.bm25_rank(text, doc=doc, top_k=limit * 3):
                if len(hits) >= limit:
                    break
                if r["chunk_id"] in seen:
                    continue
                s = r.get("section", "")
                if sec_count.get(s, 0) >= per_section:
                    continue
                sec_count[s] = sec_count.get(s, 0) + 1
                c = by_id.get(r["chunk_id"])
                if c is not None:
                    _add(c, r.get("rank", "bm25"))
        return hits
