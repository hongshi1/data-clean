#!/usr/bin/env python3
"""双图融合聚合器 (KG + 上下文关联匹配 → 聚合条目)

方向A核心: 给定实体名/ID, 召回它在文档中所有出现位置(正文+表格+图片+追溯),
输出聚合条目供方向B检测。

4通道并行召回:
  ① ID-Graph硬桥:   ID → 所有mention位置(正文/表格/追溯表)
  ② LightRAG语义图: 实体 → 所在chunks + 关系邻居
  ③ VLM图片匹配:    实体名 ∈ 图片key_elements
  ④ 向量检索:       实体名 → 语义相似chunks

输出: 聚合条目 = {
  entity, entity_id,
  occurrences: [{location, section, doc, snippet, ...}],
  graph_neighbors: [...],
  chain_completeness: 0-1 (4类位置覆盖率)
}
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, BASE)

ID_GRAPH_PATH = os.path.join(BASE, "data/gjb_438c/data_assets/graph/id_document_graph.json")
LIGHTRAG_STORE = os.path.join(BASE, "data/gjb_438c/data_assets/lightrag_store")
IMAGE_ANALYSES = os.path.join(BASE, "data/gjb_438c/data_assets/chunks/srs_image_analyses.json")
CHUNKS_PATH = os.path.join(BASE, "data/gjb_438c/data_assets/chunks/srs_chunks.json")

ID_RE = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}")


class KGContextMatcher:
    """双图融合聚合器"""

    def __init__(self, lightrag_store=None, id_graph_path=None):
        self.lightrag_store = lightrag_store or LIGHTRAG_STORE
        self.id_graph_path = id_graph_path or ID_GRAPH_PATH
        self._load_all()

    # ── 数据加载 ──────────────────────────────────────────
    def _load_all(self):
        # 1. ID-Graph
        try:
            with open(self.id_graph_path, encoding="utf-8") as f:
                g = json.loads(f.read())
            self.id_nodes = {n["id"]: n for n in g["nodes"]}
            self.id_edges = g["edges"]
            self.entity_mentions = {}   # entity_id -> [mention节点]
            self.entity_ids = {}        # entity_id -> 原始ID
            self._build_id_graph_index()
            self.has_id_graph = True
        except Exception as e:
            print(f"⚠ ID-Graph加载失败: {e}")
            self.has_id_graph = False

        # 2. LightRAG图谱
        try:
            def _j(name):
                with open(os.path.join(self.lightrag_store, name), encoding="utf-8") as f:
                    return json.loads(f.read())
            self.lr_entity_chunks = _j("kv_store_entity_chunks.json")
            self.lr_text_chunks = _j("kv_store_text_chunks.json")
            self.lr_full_entities = _j("kv_store_full_entities.json")
            self.lr_full_relations = _j("kv_store_full_relations.json")
            self.has_lightrag = True
        except Exception as e:
            print(f"⚠ LightRAG加载失败: {e}")
            self.has_lightrag = False

        # 3. VLM图片分析
        try:
            with open(IMAGE_ANALYSES, encoding="utf-8") as f:
                self.img_analyses = json.loads(f.read())["analyses"]
            self.has_images = True
        except Exception:
            self.img_analyses = []
            self.has_images = False

        # 4. 结构化chunks(带section)
        try:
            with open(CHUNKS_PATH, encoding="utf-8") as f:
                self.struct_chunks = json.loads(f.read())
            self.has_struct = True
        except Exception:
            self.struct_chunks = []
            self.has_struct = False

    def _build_id_graph_index(self):
        """ID-Graph: entity节点 → mention节点"""
        for e in self.id_edges:
            src, tgt = e["source"], e["target"]
            if src.startswith("E_") and tgt.startswith("M_"):
                ent_id = src[2:]
                self.entity_mentions.setdefault(ent_id, []).append(self.id_nodes.get(tgt, {}))
                # 从mention context提取原始ID
                m = self.id_nodes.get(tgt, {})
                ctx = m.get("context", "")
                idm = ID_RE.search(ctx)
                if idm:
                    self.entity_ids[ent_id] = idm.group(0)

    # ── 通道①: ID-Graph硬桥 ───────────────────────────────
    def channel_id_graph(self, entity_id):
        """ID → 所有mention位置"""
        mentions = self.entity_mentions.get(entity_id, [])
        results = []
        for m in mentions:
            results.append({
                "location": m.get("location", "unknown"),
                "section": m.get("section", ""),
                "snippet": m.get("context", "")[:120],
                "doc": m.get("doc", ""),
            })
        return results

    # ── 通道②: LightRAG语义图 ─────────────────────────────
    def channel_lightrag(self, name):
        """实体名 → 所在chunks + 关系邻居"""
        chunk_ids = []
        for ent_name, ent_data in self.lr_entity_chunks.items():
            if name.lower() in ent_name.lower() or ent_name.lower() in name.lower():
                chunk_ids.extend(ent_data.get("chunk_ids", []))
        # 去重
        chunk_ids = list(dict.fromkeys(chunk_ids))

        chunks = []
        for cid in chunk_ids[:20]:
            c = self.lr_text_chunks.get(cid, {})
            chunks.append({
                "chunk_id": cid,
                "content": c.get("content", "")[:150],
                "doc": c.get("file_path", c.get("full_doc_id", "")),
            })

        # 关系邻居
        neighbors = []
        for rel_key, rel_data in self.lr_full_relations.items():
            if isinstance(rel_data, dict):
                rl = rel_data.get("relation_list", [])
                if isinstance(rl, list):
                    for r in rl:
                        if isinstance(r, dict):
                            if name in str(r.get("src_id", "")) or name in str(r.get("tgt_id", "")):
                                neighbors.append({
                                    "relation": r.get("description", ""),
                                    "src": r.get("src_id", ""),
                                    "tgt": r.get("tgt_id", ""),
                                })
        return chunks, neighbors[:20]

    # ── 通道③: VLM图片匹配 ────────────────────────────────
    def channel_images(self, name):
        """实体名 ∈ 图片key_elements"""
        results = []
        for a in self.img_analyses:  # 加载失败时为空列表(has_images=False)
            elements = a.get("analysis", {}).get("key_elements", [])
            if any(name.lower() in str(e).lower() or str(e).lower() in name.lower() for e in elements):
                results.append({
                    "image_path": a.get("image_path", ""),
                    "figure_type": a.get("analysis", {}).get("figure_type", ""),
                    "caption": a.get("caption", ""),
                    "elements": elements[:8],
                    "doc": a.get("doc", ""),
                })
        return results[:10]

    # ── 融合: 聚合条目 ────────────────────────────────────
    def aggregate(self, query, entity_id=None):
        """主入口: 给定实体名/ID → 聚合条目"""
        # 从查询中提取实体名(去掉问句)
        name = query.strip()
        name = re.sub(r"[?？].*$", "", name)
        name = re.sub(r"^(什么是|有哪些|介绍一下|请描述|请问|帮我查一下)", "", name).strip()
        # 去掉问句尾巴(多轮清洗)
        for _ in range(4):
            cleaned = re.sub(
                r"(主要)?(是)?(用来|用于)?(做什么的|干什么的|做什么|干什么|干什么用|干嘛的|有什么功能|的功能是什么|是什么意思|"
                r"包含哪些|有哪些|是什么|这个功能在文档的哪个章节有详细说明|在文档的哪个部分能找到详细说明|"
                r"在文档哪些位置被提到|在需求文档的哪个章节或者哪个部分有详细描述|"
                r"在文档的哪个章节或者哪个部分有详细描述|在文档中哪些地方提到|在文档的哪些部分被提到|"
                r"在需求文档中哪些章节提到|在哪个章节|在文档哪里|在哪里|包含哪些子功能或者模块|这个概念|这个功能|这些功能|"
                r"包含哪些具体的功能模块或者子接口|里面包含哪些具体的功能模块|有哪些子功能或组成部分|"
                r"有哪些子功能或者组成部分|有哪些具体的功能模块)$", "", name).strip()
            if cleaned == name:
                break
            name = cleaned
        if not name:
            name = query

        # 提取关键词(用于回退匹配): 去掉常见停用词, 取2字以上的词
        keywords = []
        for part in re.split(r"[的、和与及,，。;；]", name):
            part = part.strip()
            if len(part) >= 2 and part not in ("这个", "那个", "文档", "系统", "功能", "相关", "主要"):
                keywords.append(part)
        # 若关键词提取失败, 用原始名称本身
        if not keywords and name:
            keywords = [name]
        self._last_keywords = keywords[:5]

        # 从查询中提取ID(若有)
        idm = ID_RE.search(query)
        if idm and not entity_id:
            entity_id = idm.group(0)

        # 4通道召回
        occurrences = []

        # ① ID-Graph
        if entity_id:
            for m in self.channel_id_graph(entity_id):
                occurrences.append({**m, "source": "id_graph"})

        # ② LightRAG
        if self.has_lightrag:
            chunks, neighbors = self.channel_lightrag(name)
            for c in chunks:
                content = c.get("content", "")
                # 判断类型: 含表格标题标记 → table
                loc = "table" if "[表格标题" in content or "<table" in content else "text"
                occurrences.append({
                    "location": loc,
                    "section": self._section_of_chunk(c.get("chunk_id", "")),
                    "snippet": content,
                    "doc": c.get("doc", ""),
                    "source": "lightrag",
                })
        # ③ VLM图片
        for img in self.channel_images(name):
            occurrences.append({
                "location": "figure",
                "section": "",
                "snippet": f"[{img['figure_type']}] {img['caption']}",
                "image_path": img["image_path"],
                "doc": img["doc"],
                "source": "vlm",
            })

        # ④ 结构化chunks匹配(带section的文本+表格)
        if self.has_struct:
            kw = getattr(self, "_last_keywords", [])
            for c in self.struct_chunks:
                c_text = c.get("text", "")
                hit = False
                if name in c_text or (entity_id and entity_id in c_text):
                    hit = True
                elif kw and len(kw) >= 2 and all(k in c_text for k in kw[:2]):
                    hit = True  # 关键词回退: 前2个关键词都在
                if hit:
                    occurrences.append({
                        "location": c.get("type", "text"),  # text/table
                        "section": c.get("section", ""),
                        "snippet": c.get("text", "")[:120],
                        "doc": c.get("doc", ""),
                        "source": "struct",
                    })

        # 去重(按 location+section+snippet前30字)
        seen = set()
        unique_occ = []
        for o in occurrences:
            key = (o.get("location"), o.get("section"), o.get("snippet", "")[:30])
            if key in seen:
                continue
            seen.add(key)
            unique_occ.append(o)

        # 完整性评分: 4类位置覆盖率
        loc_types = {o.get("location", "?") for o in unique_occ}
        loc_set = set()
        for lt in loc_types:
            if lt in ("text", "table"):
                loc_set.add("text_table")
            elif lt in ("figure", "image"):
                loc_set.add("figure")
            elif lt in ("trace", "traceability"):
                loc_set.add("trace")
            else:
                loc_set.add("other")
        # 期待位置: text/table(正文), figure(图), trace(追溯), id(表格能力表)
        expected = {"text_table", "figure", "trace"}
        hit = len(expected & loc_set)
        chain = round(hit / len(expected), 2)

        return {
            "query": query,
            "entity": name,
            "entity_id": entity_id or self._find_id_by_name(name),
            "occurrences": unique_occ,
            "occurrence_count": len(unique_occ),
            "locations": sorted(loc_types),
            "chain_completeness": chain,
            "has_text": "text_table" in loc_set,
            "has_figure": "figure" in loc_set,
            "has_trace": "trace" in loc_set,
        }

    def _section_of_chunk(self, chunk_id):
        """chunk_id → 章节(优先从结构chunks反查, 否则从content提取)"""
        # 1. 结构chunks: 用内容匹配反查section
        c = self.lr_text_chunks.get(chunk_id, {})
        content = c.get("content", "")
        if self.has_struct:
            # 找与content重叠的结构chunk
            for sc in self.struct_chunks:
                sc_text = sc.get("text", "")
                if sc_text and (sc_text[:50] in content or content[:50] in sc_text):
                    return sc.get("section", "")
        # 2. 从content开头提取章节号
        m = re.match(r"^(\d+(?:\.\d+)*)\s", content)
        return m.group(1) if m else ""

    def _find_id_by_name(self, name):
        """实体名 → 实体ID(反向查找)"""
        for ent_id, mentions in self.entity_mentions.items():
            for m in mentions:
                ctx = m.get("context", "")
                if name in ctx:
                    return ent_id
        return None


if __name__ == "__main__":
    matcher = KGContextMatcher()
    print("=== 双图融合聚合器测试 ===")
    for q in ["数据获取", "创建服务工程", "PZXQ-GN-JMJCKJ-JMJC-KJCK"]:
        result = matcher.aggregate(q)
        print(f"\n查询: {q}")
        print(f"  实体ID: {result['entity_id']}")
        print(f"  出现位置: {result['occurrence_count']}处 {result['locations']}")
        print(f"  完整性: {result['chain_completeness']}")
        for o in result['occurrences'][:6]:
            print(f"    [{o.get('location')}@{o.get('section')}] ({o.get('source')}) {o.get('snippet','')[:50]}")
