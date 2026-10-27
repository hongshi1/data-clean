"""MMQA证据原子层内核: 现有资产 → EvidenceAtom(确定性, 无LLM).

按docs/srs_project/mmqa_dataset_design.md §1:
  text句级 / table表头+行 / image整图+VLM分析 / diagram节点+边
  ID规范: EV-{doc_num:02d}-{M}-{seq:05d}, M=T句/R表行/G图/N节点/L边

设计决策(实测依据):
  - MinerU docx管线无bbox(仅page_idx), 原子以page+section定位;
    Visio锚点节点带bbox(唯一几何坐标源)
  - id_graph的E节点不造原子, 作实体注册表
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

_SENT_SPLIT = re.compile(r"[。；;]+")
_TR_PAT = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD_PAT = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_TAG_PAT = re.compile(r"<[^>]+>")


def _clean_html(s: str) -> str:
    return _TAG_PAT.sub("", s).replace("&nbsp;", " ").strip()


def doc_num_of(doc_name: str) -> str:
    """'01数据获取转换分系统需求规格说明-终稿' → '01'."""
    m = re.match(r"^(\d{2})", doc_name or "")
    return m.group(1) if m else "00"


def split_sentences(text: str, min_len: int = 8) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text or "")
            if s.strip() and len(s.strip()) >= min_len]


def table_rows_from_html(html: str) -> list[list[str]]:
    """HTML表格 → 行列表(去标签, 保列序)."""
    rows: list[list[str]] = []
    for m in _TR_PAT.finditer(html or ""):
        cells = [_clean_html(c) for c in _TD_PAT.findall(m.group(1))]
        if any(cells):
            rows.append(cells)
    return rows


def table_rows_from_csv(csv_path: Path) -> list[list[str]]:
    with open(csv_path, encoding="utf-8") as f:
        return [[c.strip() for c in row] for row in csv.reader(f)]


class AtomBuilder:
    """从chunks/锚点/VLM分析构建原子(纯函数式, 输出dict列表)."""

    def __init__(self, chunks: list[dict],
                 image_analyses: list[dict] | None = None) -> None:
        self.chunks = chunks
        self._img_analysis: dict[str, dict] = {}
        if image_analyses:
            for a in image_analyses:
                fm = re.search(r"fig_\d+", a.get("image_path", ""))
                if fm:
                    self._img_analysis[(a.get("doc", ""), fm.group(0))] = a

    def build(self) -> list[dict[str, Any]]:
        atoms: list[dict[str, Any]] = []
        counters: dict[str, int] = {}

        def _atom(mod: str, doc: str, section: str, content: str,
                  page: int, provenance: dict,
                  entities: list[str] | None = None) -> dict[str, Any]:
            dn = doc_num_of(doc)
            key = f"{dn}-{mod}"
            counters[key] = counters.get(key, 0) + 1
            return {
                "evidence_id": f"EV-{dn}-{mod}-{counters[key]:05d}",
                "doc_id": dn, "modality": _MODALITY[mod],
                "section": section, "content": content[:400], "page": page,
                "entities": entities or [],
                "provenance": provenance}

        for c in self.chunks:
            doc = c.get("doc", "")
            sec = c.get("section", "")
            page = c.get("page", 0) or 0
            ctype = c.get("type", "text")
            cid = c.get("chunk_id", "")
            if ctype == "text":
                for sent in split_sentences(c.get("text", "")):
                    atoms.append(_atom("T", doc, sec, sent, page,
                                       {"source_asset": cid}))
            elif ctype == "table":
                caption = " ".join(c.get("table_caption") or [])
                rows = table_rows_from_html(c.get("text", ""))
                header = rows[0] if rows else []
                for i, row in enumerate(rows):
                    content = (caption + " | " + " | ".join(row))[:400]
                    atoms.append(_atom("R", doc, sec, content, page,
                                       {"source_asset": cid, "row_idx": i,
                                        "header": header[:6]}))
            elif ctype == "image":
                img_path = c.get("image_path", "")
                fm = re.search(r"fig_\d+", img_path)
                ana = self._img_analysis.get((doc, fm.group(0))) if fm else None
                entities: list[str] = []
                content = " ".join(c.get("meta", {}).get("caption", "") or "")
                if ana:
                    entities = (ana.get("analysis", {}).get("key_elements", [])
                                or [])[:8]
                    content += " " + (ana.get("analysis", {}).get("summary", "")
                                      or "")
                atoms.append(_atom("G", doc, sec, content.strip(), page,
                                   {"source_asset": cid, "image_path": img_path},
                                   entities))
        return atoms

    def build_diagram_atoms(self, anchors_v2: dict[str, Any]
                            ) -> list[dict[str, Any]]:
        """锚点 → 节点原子(N)+边原子(L)."""
        atoms: list[dict[str, Any]] = []
        n_count = l_count = 0
        for doc, d in (anchors_v2 or {}).items():
            dn = doc_num_of(doc)
            for s in d.get("structures", []):
                embed = s.get("embed_index", "")
                nodes = {n.get("id"): n for n in s.get("nodes", [])}
                for n in s.get("nodes", []):
                    if not n.get("text"):
                        continue
                    n_count += 1
                    atoms.append({
                        "evidence_id": f"EV-{dn}-N-{n_count:05d}",
                        "doc_id": dn, "modality": "diagram-node",
                        "section": "", "content": n["text"][:200],
                        "page": 0,
                        "entities": [n["text"]],
                        "provenance": {"source_asset": embed,
                                       "node_id": n.get("id"),
                                       "bbox": n.get("bbox")}})
                for e in s.get("edges", []):
                    src, dst = nodes.get(e.get("src")), nodes.get(e.get("dst"))
                    if src is None or dst is None:
                        continue
                    label = e.get("label", "")
                    content = f"{src.get('text', '')} --{label}--> {dst.get('text', '')}"
                    if not src.get("text") and not dst.get("text"):
                        continue
                    l_count += 1
                    atoms.append({
                        "evidence_id": f"EV-{dn}-L-{l_count:05d}",
                        "doc_id": dn, "modality": "diagram-edge",
                        "section": "", "content": content[:400], "page": 0,
                        "entities": [x for x in (src.get("text"),
                                                 dst.get("text")) if x],
                        "provenance": {"source_asset": embed,
                                       "src": e.get("src"), "dst": e.get("dst"),
                                       "via": e.get("via", "")}})
        return atoms


_MODALITY = {"T": "text-sentence", "R": "table-row", "G": "image",
             "N": "diagram-node", "L": "diagram-edge"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
