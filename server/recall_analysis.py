"""Recall analysis API: query → per-channel analysis (NER/BM25/ID-Graph)."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

BASE = Path(__file__).resolve().parents[1]

router = APIRouter()


def _bm25_tokens(text: str) -> list[str]:
    """CJK 2字滑窗 + ASCII token (与evidence_store.BM25同口径)."""
    tokens = []
    # ASCII words
    for m in re.finditer(r"[A-Za-z0-9]+", text):
        tokens.append(m.group().lower())
    # CJK 2-char sliding window
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", text)
    for i in range(len(cjk) - 1):
        tokens.append(cjk[i:i + 2])
    if len(cjk) == 1:
        tokens.append(cjk)
    return tokens


def _id_graph_matches(text: str) -> list[dict]:
    """PZXQ ID → graph node lookup (if ID graph is loaded)."""
    ids = re.findall(r"PZXQ-[A-Z0-9-]+", text)
    if not ids:
        return []
    graph_path = BASE / "data/gjb_438c/data_assets/graph/id_document_graph.json"
    if not graph_path.exists():
        return []
    import json
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    by_id = {n["id"]: n for n in graph.get("nodes", [])
             if n.get("type") == "entity"}
    out = []
    for pid in ids:
        entity = by_id.get(f"E_{pid}")
        if entity:
            mentions = [n for n in graph.get("nodes", [])
                        if n.get("type") == "mention"
                        and n.get("id", "").startswith(f"M_{pid}")]
            out.append({
                "id": pid,
                "entity_node": entity["id"],
                "n_mentions": len(mentions),
                "sections": sorted({m.get("section", "")[:16]
                                    for m in mentions})[:5],
            })
    return out


@router.post("/api/recall-analysis")
def recall_analysis(body: dict) -> dict:
    """POST /api/recall-analysis: query → 各召回通道的预处理分析.

    返回 {entities, bm25_tokens, id_graph} — 前端动态渲染.
    """
    text = str(body.get("text", "")).strip()
    if not text:
        return {"ok": True, "data": {"entities": [], "bm25_tokens": [],
                                     "id_graph": []}}

    # NER entities (L0 entity detector)
    from algorithms.consistency.entity_detector import extract_entities
    from algorithms.consistency.ner_lexicon import load_lexicon
    lex_path = BASE / "config/ner_lexicons/srs_scene1.json"
    if (BASE / "data/agent_knowledge/scene1/lexicon.json").exists():
        lex_path = BASE / "data/agent_knowledge/scene1/lexicon.json"
    lexicon = load_lexicon(lex_path)
    entities = extract_entities(text, lexicon)
    kind_meta = {
        "pzxq_id": ("项目唯一标识符", "ID-Graph硬桥", "#6366f1"),
        "domain_term": ("领域术语", "Lexical/BM25", "#059669"),
        "chinese": ("中文实体", "BM25/Dense", "#d97706"),
        "mixed": ("混合实体", "BM25/Dense", "#0891b2"),
    }
    entity_out = []
    for e in entities:
        meta = kind_meta.get(e.kind, ("其他", "多通道", "#64748b"))
        entity_out.append({
            "text": e.surface, "kind": e.kind, "kind_zh": meta[0],
            "channel": meta[1], "color": meta[2],
            "start": e.start, "end": e.end,
        })

    # BM25 tokens
    tokens = _bm25_tokens(text)

    # ID-Graph matches
    id_matches = _id_graph_matches(text)

    return {"ok": True, "data": {
        "entities": entity_out,
        "bm25_tokens": tokens,
        "bm25_token_count": len(tokens),
        "id_graph": id_matches,
        "query": text,
    }}
