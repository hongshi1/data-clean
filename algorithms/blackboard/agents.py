"""五个确定性Agent: 黑板的写手. 每个agent只做"忠实读取+结构化", 不做语义判断.

  table_agent  κ_T编译配对表格            → table_structure (FACT)
  vision_agent 锚点/VLM/OCR三通道同图观测 → diagram_structure (FACT) +
               vlm_extraction / ocr_extraction (HYPOTHESIS)
  entity_agent ID-Graph硬桥/chunks/图片    → entity_mentions/chunk_occurrences/image_hits
  graph_agent  Tier1对应+分歧, drift状态  → element_correspondence/discrepancy_set/drift_status
  prose_agent  κ_P正文编译 + 语义富集      → prose_features/semantic_links

LLM不在其中 —— 这正是设计: 不确定性被压缩到"通道置信度"里, 而不是agent里.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .blackboard import Blackboard
from .confidence import ConfidenceModel
from .embedding_channel import EmbeddingChannel
from .evidence_store import EvidenceStore
from .kt_compilers import compile_for_scene
from .lexical_kit import MATCH_TH, text_match_score
from .prose_compiler import ID_PAT, compile_prose, prose_item_names
from .schemas import (Channel, ConfSource, Epistemic, EvidenceItem,
                      Invocation, Provenance, TaskSpec)

_MAX_LIST = 40  # payload列表截断上限(控制黑板体积)


@dataclass
class AgentContext:
    task: TaskSpec
    store: EvidenceStore
    conf: ConfidenceModel
    bb: Blackboard
    embedding: EmbeddingChannel | None = None


class Agent:
    name: str = "agent"

    def invoke(self, ctx: AgentContext, inv: Invocation) -> list[EvidenceItem]:
        raise NotImplementedError


def _trim_nodes(nodes: list[dict]) -> list[dict]:
    out = []
    for n in nodes[:_MAX_LIST]:
        out.append({"id": n.get("id", ""), "text": (n.get("text") or "")[:60],
                    "type": n.get("type", "")})
    return out


def _trim_edges(edges: list[dict]) -> list[dict]:
    return [{"src": e.get("src", ""), "dst": e.get("dst", ""),
             "label": (e.get("label") or "")[:30], "via": e.get("via", "")}
            for e in edges[:_MAX_LIST]]


# ═══════════════════════════════════════════════════════════════
# Table Agent (κ_T)
# ═══════════════════════════════════════════════════════════════

class TableAgent(Agent):
    name = "table_agent"

    def invoke(self, ctx: AgentContext, inv: Invocation) -> list[EvidenceItem]:
        pair_id = ctx.task.pair_id
        if not pair_id:
            return []
        pd = ctx.store.pair_dir(pair_id)
        if pd is None:
            return []
        scene = ctx.store.scene_of(pair_id)
        x_t = compile_for_scene(scene, pd / "table.csv")
        if not x_t:
            return []
        payload: dict[str, Any] = {
            "scene": scene, "pair_id": pair_id,
            "type": x_t.get("type", ""),
            "n_items": len(x_t.get("nodes", [])),
            "nodes": _trim_nodes(x_t.get("nodes", [])),
        }
        for extra in ("uc_name", "actors", "caps", "interfaces", "subs",
                      "steps", "exceptions"):
            if extra in x_t:
                v = x_t[extra]
                payload[extra] = v[:_MAX_LIST] if isinstance(v, list) else v
        c = ctx.conf.for_channel(Channel.KT)
        return [EvidenceItem(
            subject="table_structure", channel=Channel.KT,
            epistemic=Epistemic.FACT, confidence=c.value,
            conf_source=c.source, payload=payload,
            provenance=Provenance(source=str(pd / "table.csv"), locator=pair_id),
            note=f"κ_T编译({x_t.get('type', '?')}), {payload['n_items']}元素")]


# ═══════════════════════════════════════════════════════════════
# Vision Agent (三通道同图观测)
# ═══════════════════════════════════════════════════════════════

class VisionAgent(Agent):
    name = "vision_agent"

    def invoke(self, ctx: AgentContext, inv: Invocation) -> list[EvidenceItem]:
        pair_id = ctx.task.pair_id
        if not pair_id:
            return []
        items: list[EvidenceItem] = []
        doc = ctx.store.pair_doc(pair_id) or ctx.task.doc
        pd = ctx.store.pair_dir(pair_id)

        # ── 通道A: 锚点(构造性保真; 映射可信度降级) ──
        anchor = ctx.store.pair_anchor(pair_id)
        if anchor is not None:
            census = ctx.store.drift(pair_id) or {}
            mapping_conf = anchor.get("mapping_confidence", "")
            if not mapping_conf:
                mapping_conf = ("census_realigned"
                                if census.get("status") == "anchored"
                                and census.get("new_embed") else "unknown")
            align = census.get("align_score")
            nodes = anchor.get("nodes", [])
            c = ctx.conf.for_channel(Channel.ANCHOR)
            conf, src, note = c.value, c.source, c.note
            if (mapping_conf in ("low", "unknown")
                    or (isinstance(align, (int, float)) and align < 0.75)):
                conf = 0.5
                src = ConfSource.HEURISTIC
                note = (f"锚点XML本身构造性保真, 但锚点-图映射低可信"
                        f"(mapping={mapping_conf}, align={align}; "
                        f"sc2教训: 旧关键词映射67%错位)")
            items.append(EvidenceItem(
                subject="diagram_structure", channel=Channel.ANCHOR,
                epistemic=Epistemic.FACT, confidence=conf, conf_source=src,
                payload={
                    "pair_id": pair_id, "scene": ctx.store.scene_of(pair_id),
                    "n_nodes": len(nodes), "nodes": _trim_nodes(nodes),
                    "n_edges": len(anchor.get("edges", [])),
                    "edges": _trim_edges(anchor.get("edges", [])),
                    "embed_index": anchor.get("embed_index", ""),
                    "mapping_confidence": mapping_conf,
                    "align_score": align,
                    "extraction_tool": anchor.get("extraction", {}).get("tool", ""),
                },
                provenance=Provenance(
                    source=str(pd / "visio_anchor.json") if pd else "anchor_v2",
                    locator=f"{pair_id}:{anchor.get('embed_index', '')}"),
                note=note))

        # ── 通道B: VLM提取(假设, 锚点校准置信度) ──
        vlm = ctx.store.vlm_extraction(pair_id)
        if vlm is not None:
            v_nodes = vlm.get("nodes", [])
            c = ctx.conf.for_channel(Channel.VLM, claim="node",
                                     doc=doc, n_nodes=len(v_nodes))
            subject = "diagram_structure" if anchor is None else "vlm_extraction"
            items.append(EvidenceItem(
                subject=subject, channel=Channel.VLM,
                epistemic=Epistemic.HYPOTHESIS, confidence=c.value,
                conf_source=c.source,
                payload={"pair_id": pair_id, "diagram_type": vlm.get("diagram_type", ""),
                         "n_nodes": len(v_nodes), "nodes": _trim_nodes(v_nodes),
                         "n_edges": len(vlm.get("edges", [])),
                         "edges": _trim_edges(vlm.get("edges", []))},
                provenance=Provenance(source="scene_vlm_extractions/sc2_vlm",
                                      locator=pair_id),
                note=f"VLM通道({c.note}); 与锚点互校"))

        # ── 通道C: OCR(sc2, 独立字符证据) ──
        ocr = ctx.store.ocr_blocks(pair_id)
        if ocr is not None:
            blocks = ocr.get("blocks", [])[:_MAX_LIST]
            c = ctx.conf.for_channel(Channel.OCR)
            items.append(EvidenceItem(
                subject="ocr_extraction", channel=Channel.OCR,
                epistemic=Epistemic.HYPOTHESIS, confidence=c.value,
                conf_source=c.source,
                payload={"pair_id": pair_id, "n_blocks": len(ocr.get("blocks", [])),
                         "block_texts": [b.get("text", "")[:40] for b in blocks]},
                provenance=Provenance(source="anchor_sc2/ocr_extractions.json",
                                      locator=pair_id),
                note=c.note))
        return items


# ═══════════════════════════════════════════════════════════════
# Entity Agent (ID-Graph / chunks / 图片分析)
# ═══════════════════════════════════════════════════════════════

class EntityAgent(Agent):
    name = "entity_agent"

    def invoke(self, ctx: AgentContext, inv: Invocation) -> list[EvidenceItem]:
        task = ctx.task
        items: list[EvidenceItem] = []
        if inv.subject == "entity_mentions":
            key = task.entity_id or task.entity
            if not key and task.query:
                m = ID_PAT.search(task.query)
                key = m.group(0) if m else ""
            rec = ctx.store.entity_mentions(key) if key else None
            if rec is not None:
                c = ctx.conf.for_channel(Channel.ID_GRAPH)
                items.append(EvidenceItem(
                    subject="entity_mentions", channel=Channel.ID_GRAPH,
                    epistemic=Epistemic.FACT, confidence=c.value,
                    conf_source=c.source, payload=rec,
                    provenance=Provenance(source="id_document_graph.json",
                                          locator=rec.get("entity_id", "")),
                    note=f"ID硬桥: {rec.get('n_mentions', 0)}个mention"))
        elif inv.subject == "chunk_occurrences":
            text = task.entity or task.entity_id or task.query
            hits = ctx.store.search_chunks(text, task.doc)
            # 多跳(link-following): ID-mention的章节 → 该章节chunks
            hop_hits = []
            if task.entity_id:
                rec = ctx.store.entity_mentions(task.entity_id)
                if rec:
                    hop_hits = ctx.store.section_chunks(
                        rec.get("sections", []), doc=task.doc or rec.get("doc", ""))
            merged = hits + [h for h in hop_hits
                             if h["chunk_id"] not in {x["chunk_id"] for x in hits}]
            if merged:
                c = ctx.conf.for_channel(Channel.CHUNKS)
                n_hop = len(merged) - len(hits)
                items.append(EvidenceItem(
                    subject="chunk_occurrences", channel=Channel.CHUNKS,
                    epistemic=Epistemic.FACT, confidence=c.value,
                    conf_source=c.source,
                    payload={"n_occurrences": len(merged), "occurrences": merged,
                             "n_section_hop": n_hop,
                             "sections": sorted({h["section"] for h in merged
                                                 if h["section"]})},
                    provenance=Provenance(source="srs_chunks.json", locator=text[:40]),
                    note=f"chunks召回: {len(hits)}处(含BM25)"
                         f"{' + ' + str(n_hop) + '处ID章节多跳' if n_hop else ''}"))
        elif inv.subject == "expanded_recall":
            # 查询扩展(agentic RAG): 从已召回证据提取新词 → 二轮检索
            snippets = []
            for e in ctx.bb.by_subject("chunk_occurrences"):
                snippets.extend(o.get("snippet", "")
                                for o in e.payload.get("occurrences", []))
            if not snippets:
                return []
            # 高频CJK bigram(排除原查询词) → 扩展词
            from collections import Counter as _Counter
            query_terms = set(ctx.store._terms_of(task.entity or task.query))
            freq = _Counter()
            for s in snippets:
                for t in ctx.store._terms_of(s):
                    if t not in query_terms and len(t) >= 2:
                        freq[t] += 1
            top_terms = [t for t, _ in freq.most_common(3)]
            if not top_terms:
                return []
            hits = ctx.store.search_chunks(" ".join(top_terms), task.doc, limit=10)
            new_hits = [h for h in hits
                        if h.get("rank") == "bm25"][:8]
            if not new_hits:
                return []
            c = ctx.conf.for_channel(Channel.CHUNKS)
            items.append(EvidenceItem(
                subject="expanded_recall", channel=Channel.CHUNKS,
                epistemic=Epistemic.HYPOTHESIS, confidence=0.7,
                conf_source=ConfSource.HEURISTIC,
                payload={"expanded_terms": top_terms,
                         "n_new_hits": len(new_hits), "occurrences": new_hits},
                provenance=Provenance(source="srs_chunks.json(扩展轮)",
                                      locator=" ".join(top_terms)),
                note=f"查询扩展: 提取词{top_terms} → 新召回{len(new_hits)}处"))
        elif inv.subject == "image_hits":
            hits = ctx.store.image_hits(task.entity)
            if hits:
                c = ctx.conf.for_channel(Channel.VLM, claim="node", doc=task.doc)
                items.append(EvidenceItem(
                    subject="image_hits", channel=Channel.VLM,
                    epistemic=Epistemic.HYPOTHESIS, confidence=c.value,
                    conf_source=c.source, payload={"n_hits": len(hits), "hits": hits},
                    provenance=Provenance(source="srs_image_analyses.json",
                                          locator=task.entity[:40]),
                    note=f"VLM图片分析命中: {len(hits)}图"))
        return items


# ═══════════════════════════════════════════════════════════════
# Graph Agent (Tier1对应 + drift)
# ═══════════════════════════════════════════════════════════════

class GraphAgent(Agent):
    name = "graph_agent"

    def invoke(self, ctx: AgentContext, inv: Invocation) -> list[EvidenceItem]:
        pair_id = ctx.task.pair_id
        if not pair_id:
            return []
        items: list[EvidenceItem] = []
        if inv.subject in ("element_correspondence", "discrepancy_set"):
            t = ctx.store.tier1(pair_id)
            if t is not None:
                n_table = t.get("n_table", t.get("n_table_steps", 0))
                n_diag = t.get("n_diag", t.get("n_diag_nodes", 0))
                n_matched = t.get("n_matched", 0)
                c = ctx.conf.for_channel(Channel.TIER1)
                items.append(EvidenceItem(
                    subject="element_correspondence", channel=Channel.TIER1,
                    epistemic=Epistemic.FACT, confidence=c.value,
                    conf_source=c.source,
                    payload={"pair_id": pair_id, "scene": t.get("scene", ""),
                             "diagram_mode": t.get("diagram_mode", ""),
                             "n_table": n_table, "n_diag": n_diag,
                             "n_matched": n_matched,
                             "match_rate": round(n_matched / n_table, 3) if n_table else None},
                    provenance=Provenance(source="scene_tier1/tier1_discrepancies_v2",
                                          locator=pair_id),
                    note=c.note))
                discs = t.get("discrepancies", [])
                if discs:
                    items.append(EvidenceItem(
                        subject="discrepancy_set", channel=Channel.TIER1,
                        epistemic=Epistemic.HYPOTHESIS, confidence=0.75,
                        conf_source=ConfSource.HEURISTIC,
                        payload={"pair_id": pair_id,
                                 "n_discrepancies": len(discs),
                                 "discrepancies": discs[:_MAX_LIST]},
                        provenance=Provenance(source="scene_tier1/tier1_discrepancies_v2",
                                              locator=pair_id),
                        note="分歧候选, 待裁决(M7/M17/M22管线)"))
        elif inv.subject == "drift_status":
            d = ctx.store.drift(pair_id)
            if d is not None:
                c = ctx.conf.for_channel(Channel.DRIFT_CENSUS)
                items.append(EvidenceItem(
                    subject="drift_status", channel=Channel.DRIFT_CENSUS,
                    epistemic=Epistemic.FACT, confidence=c.value,
                    conf_source=c.source,
                    payload={"pair_id": pair_id, "status": d.get("status"),
                             "align_score": d.get("align_score"),
                             "n_drift": d.get("n_drift", 0),
                             "diffs": d.get("diffs", [])[:10]},
                    provenance=Provenance(source="scene_drift_census.json",
                                          locator=pair_id),
                    note=f"census: status={d.get('status')}, drift={d.get('n_drift', 0)}"))
        return items


# ═══════════════════════════════════════════════════════════════
# Syntax Agent (GJB语法层, 接入algorithms/syntax)
# ═══════════════════════════════════════════════════════════════

_syntax_checker_cache: Any = None


def _get_syntax_checker() -> Any:
    """SyntaxChecker单例(进程内复用, 加载chunks约1s)."""
    global _syntax_checker_cache
    if _syntax_checker_cache is None:
        from algorithms.consistency.syntax.syntax_checker import SyntaxChecker
        _syntax_checker_cache = SyntaxChecker()
    return _syntax_checker_cache


class SyntaxAgent(Agent):
    name = "syntax_agent"

    def invoke(self, ctx: AgentContext, inv: Invocation) -> list[EvidenceItem]:
        if inv.subject != "syntax_detections":
            return []
        doc = ctx.task.doc
        if not doc and ctx.task.pair_id:
            doc = ctx.store.pair_doc(ctx.task.pair_id)
        if not doc:
            return []
        checker = _get_syntax_checker()
        checker.detections = []
        for check in (checker.check_section_continuity, checker.check_id_unique,
                      checker.check_id_format, checker.check_fig_table_refs,
                      checker.check_structure, checker.check_title_format,
                      checker.check_cross_refs):
            check()
        hits = [d for d in checker.detections if d.get("doc") == doc]
        by_rule: dict[str, int] = {}
        for d in hits:
            by_rule[d["rule_id"]] = by_rule.get(d["rule_id"], 0) + 1
        c = ctx.conf.for_channel(Channel.SYNTAX)
        return [EvidenceItem(
            subject="syntax_detections", channel=Channel.SYNTAX,
            epistemic=Epistemic.FACT, confidence=c.value,
            conf_source=c.source,
            payload={"doc": doc, "n_detections": len(hits),
                     "by_rule": by_rule, "detections": hits[:30]},
            provenance=Provenance(source="algorithms/syntax/syntax_checker.py",
                                  locator=doc),
            note=f"GJB语法层: {len(hits)}条 {by_rule}")]


# ═══════════════════════════════════════════════════════════════
# Prose Agent (κ_P + 语义富集)
# ═══════════════════════════════════════════════════════════════

class ProseAgent(Agent):
    name = "prose_agent"

    def invoke(self, ctx: AgentContext, inv: Invocation) -> list[EvidenceItem]:
        pair_id = ctx.task.pair_id
        pd = ctx.store.pair_dir(pair_id) if pair_id else None
        if inv.subject == "prose_features":
            if pd is None:
                return []
            tp = pd / "text.txt"
            if not tp.exists():
                return []
            text = tp.read_text(encoding="utf-8")
            meta = ctx.store.pair_meta(pair_id)
            compiled = compile_prose(text, meta.get("section_title", ""))
            c = ctx.conf.for_channel(Channel.KP)
            return [EvidenceItem(
                subject="prose_features", channel=Channel.KP,
                epistemic=Epistemic.FACT, confidence=c.value,
                conf_source=c.source, payload=compiled,
                provenance=Provenance(source=str(tp), locator=pair_id),
                note=f"κ_P: {compiled['n_features']}特征/{compiled['n_sentences']}句")]

        if inv.subject == "semantic_links":
            # κ_P枚举项 ↔ κ_T表格项 的语义对齐(embedding通道, 词法互证)
            if ctx.embedding is None or ctx.embedding.mode == "unavailable":
                return []
            prose_items: list[str] = []
            for e in ctx.bb.by_subject("prose_features"):
                prose_items.extend(prose_item_names(e.payload))
            table_names: list[str] = []
            for e in ctx.bb.by_subject("table_structure"):
                table_names.extend(n.get("text", "")
                                   for n in e.payload.get("nodes", []))
            prose_items = prose_items[:_MAX_LIST]
            table_names = table_names[:_MAX_LIST]
            if not prose_items or not table_names:
                return []
            matches = ctx.embedding.match(prose_items, table_names)
            # 消费协议与校准一致: 贪心一对一(分数降序, 双方未占用)
            used_i: set[int] = set()
            used_j: set[int] = set()
            unique: list[tuple[int, int, float]] = []
            for i, j, score in matches:
                if i not in used_i and j not in used_j:
                    used_i.add(i)
                    used_j.add(j)
                    unique.append((i, j, score))
            c = ctx.conf.for_channel(Channel.EMBEDDING)
            records = []
            for i, j, score in unique[:_MAX_LIST]:
                lex = text_match_score(prose_items[i], table_names[j])
                records.append({"prose_item": prose_items[i],
                                "table_item": table_names[j],
                                "emb_score": score, "lexical": round(lex, 3),
                                "lexical_confirmed": lex >= MATCH_TH})
            return [EvidenceItem(
                subject="semantic_links", channel=Channel.EMBEDDING,
                epistemic=Epistemic.HYPOTHESIS, confidence=c.value,
                conf_source=c.source,
                payload={"n_matches": len(records), "matches": records,
                         "n_prose_items": len(prose_items),
                         "n_table_items": len(table_names),
                         "embedding_mode": ctx.embedding.mode,
                         "coverage": ctx.embedding.stats},
                provenance=Provenance(source="embedding_channel",
                                      locator=f"{pair_id}:prose↔table"),
                note=f"κ_P枚举↔κ_T表格项语义对齐({ctx.embedding.mode}模式, {c.note})")]
        return []


AGENTS: dict[str, Agent] = {
    a.name: a for a in (TableAgent(), VisionAgent(), EntityAgent(),
                        GraphAgent(), SyntaxAgent(), ProseAgent())
}
