#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上下文图谱激活算法 — 动态多模态召回(方向A核心)

在预建图谱(graph_store)上做「查询驱动的k-hop径向激活」:
  ① 种子识别: ID正则 + 精确匹配 + 模糊匹配(text_sim) — question实体落到图上
  ② k-hop扩展: 最大权重路径BFS(Dijkstra变体, score=Π(边权)), 记录hop与路径
  ③ 模态平衡: 每模态独立top-k, 保证TXT/TBL/IMG/SEQ/KNW扇区饱满
  ④ 输出: 激活子图(节点带hop/score/path) → 前端径向渲染

设计对齐: agentic_rag的Planner(意图路由)→Researcher(多通道)→Aggregator(条目聚合)
  本模块=Researcher的图谱版(快两个数量级+路径可解释); 条目聚合直接读预计算items。

用法:
    from algorithms.context_graph import ContextGraph
    cg = ContextGraph()                       # 加载graph_store
    r = cg.activate("结构化数据归集出现在哪些位置?")   # → 激活子图
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(BASE, "data/gjb_438c/graph_store")

ID_RE = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}")
MODALITIES = ["TXT", "TBL", "IMG", "SEQ", "KNW"]


def _load(path):
    return json.load(open(path, encoding="utf-8"))


class ContextGraph:
    """预建上下文图谱 + 激活召回"""

    def __init__(self, store=STORE):
        self.store = store
        self.docs = {}          # doc_num -> graph dict
        self.adj = {}           # doc_num -> {node_id: [(nbr, edge), ...]}
        self.node_index = {}    # (doc_num, node_id) -> node
        self.global_g = None
        self.items = {}         # (doc_num, entity_id) -> item
        self.sec_texts = {}     # doc_num -> {section: 全文}
        self.sec_node = {}      # doc_num -> {section: TXT节点id}
        self._load_all()
        self._load_fulltext()

    def _load_fulltext(self):
        """章节全文索引(正文+表格内容, 供非实体词全文检索)"""
        import glob as _glob
        import re as _re
        for num, g in self.docs.items():
            doc_name = g["meta"]["doc"]
            st, sn, cur = {}, {}, ""
            for p in _glob.glob(os.path.join(
                    BASE, "data/gjb_438c/mineru_standard/*/office/*content_list.json")):
                if os.path.basename(p).replace("_content_list.json", "") != doc_name:
                    continue
                cl = json.load(open(p, encoding="utf-8"))
                cur = ""
                for it in cl:
                    if not isinstance(it, dict):
                        continue
                    t = it.get("type", "")
                    if t == "text":
                        txt = it.get("text", "")
                        m = _re.match(r"^(\d+(?:\.\d+)*)\s+", txt.strip())
                        if m:
                            cur = m.group(1)
                        if len(txt.strip()) > 10:
                            st[cur] = st.get(cur, "") + " " + txt.strip()
                    elif t == "table":
                        # 表格内容(去HTML标签)计入当前章节索引
                        body = _re.sub(r"<[^>]+>", " ", it.get("table_body", ""))
                        caps = " ".join(it.get("table_caption", []))
                        if len(body.strip()) > 5:
                            st[cur] = st.get(cur, "") + " " + caps + " " + body
                break
            for n in g["nodes"]:
                if n["type"] == "TXT":
                    sn[n["section"]] = n["id"]
            self.sec_texts[num] = st
            self.sec_node[num] = sn

    # ------------------------------------------------------------------
    def _load_all(self):
        for p in sorted(glob.glob(os.path.join(self.store, "[0-9][0-9].json"))):
            num = os.path.basename(p).split(".")[0]
            g = _load(p)
            self.docs[num] = g
            adj = defaultdict(list)
            for e in g["edges"]:
                adj[e["s"]].append((e["t"], e))
                adj[e["t"]].append((e["s"], e))  # 无向激活
            self.adj[num] = adj
            for n in g["nodes"]:
                self.node_index[(num, n["id"])] = n
            for it in g["items"]:
                self.items[(num, it["entity_id"])] = it
        gp = os.path.join(self.store, "global.json")
        if os.path.exists(gp):
            self.global_g = _load(gp)

    # ------------------------------------------------------------------
    # ① 种子识别
    # ------------------------------------------------------------------
    def find_seeds(self, question, doc_num=None):
        """question → 图上种子节点 [(node, score, why)]"""
        seeds = []
        q = question.strip()
        nums = [doc_num] if doc_num else sorted(self.docs.keys())
        # 1. ID精确命中(最强)
        for m in ID_RE.finditer(q):
            for num in nums:
                nid = f"e:{m.group(0)}"
                if (num, nid) in self.node_index:
                    seeds.append((self.node_index[(num, nid)], 1.0, f"ID精确:{m.group(0)}"))
        # 2. 图号/表号引用("图5"/"表3")
        for m in re.finditer(r"图\s*(\d+)", q):
            for num in nums:
                nid = f"img:{num}:{m.group(1)}"
                if (num, nid) in self.node_index:
                    seeds.append((self.node_index[(num, nid)], 0.95, f"图号命中:图{m.group(1)}"))
        # 3. 文本匹配: E/TXT/TBL/IMG/KNW的label与question的n-gram比对
        max_gram = 14
        qgrams = set()
        for L in range(2, max_gram + 1):
            for i in range(len(q) - L + 1):
                qgrams.add(q[i:i + L])
        for num in nums:
            for n in self.docs[num]["nodes"]:
                label = n["label"]
                if not label or len(label) < 2:
                    continue
                # 候选文本: label + E节点aliases
                cands = [(label, 1.0)]
                for a in n.get("payload", {}).get("aliases", []):
                    cands.append((a, 0.97))  # 别名命中略降权
                best, why = 0.0, ""
                for cand, bonus in cands:
                    if len(cand) < 2:
                        continue
                    if cand in q:
                        s = bonus
                        if s > best:
                            best, why = s, f"名称完整出现:{cand[:16]}"
                        continue
                    # 别名做n-gram模糊(label太长不做, ID不模糊)
                    if cand is not label and n["type"] != "E":
                        continue
                    if n["type"] == "E" or len(cand) <= 16:
                        for g in qgrams:
                            if len(g) >= 4 and (g in cand or cand in g):
                                s = (0.55 + 0.3 * min(len(g), len(cand)) /
                                     max(len(g), len(cand))) * bonus
                                if s > best:
                                    best, why = s, f"模糊匹配({cand[:12]} {s:.2f})"
                if best >= 0.55:
                    seeds.append((n, best, why))
        # 去重(同节点取最高分), 每文档最多8个种子, 总数上限16
        by_node = {}
        for n, s, w in seeds:
            key = (n["doc"], n["id"])
            if key not in by_node or s > by_node[key][1]:
                by_node[key] = (n, s, w)
        ranked = sorted(by_node.values(), key=lambda x: -x[1])
        per_doc = defaultdict(int)
        out = []
        for n, s, w in ranked:
            dn = n["doc"][:2]
            if per_doc[dn] >= 8:
                continue
            per_doc[dn] += 1
            out.append((n, s, w))
            if len(out) >= 16:
                break
        return out

    # ------------------------------------------------------------------
    # 意图识别与定向增强
    # ------------------------------------------------------------------
    INTENT_KW = {
        "location": ["哪些位置", "哪些地方", "位置有描述", "在文档的哪些", "出现在", "还有哪些位置", "其他哪些位置"],
        "list": ["包含哪些", "有哪些", "多少个", "多少子", "子功能", "列出了", "功能划分"],
        "table_ref": ["表格「", "表「"],
    }

    @classmethod
    def _intent(cls, q):
        for k, kws in cls.INTENT_KW.items():
            if any(w in q for w in kws):
                return k
        return ""

    def _fulltext_nodes(self, focus_doc, term, limit=10):
        """非实体词全文检索: 章节全文搜词, 按词频密度排序(短章节高频优先)"""
        out = []
        st = self.sec_texts.get(focus_doc, {})
        sn = self.sec_node.get(focus_doc, {})
        g = self.docs[focus_doc]
        node_by_id = {n["id"]: n for n in g["nodes"]}
        for sec, text in st.items():
            cnt = text.count(term)
            if cnt == 0:
                continue
            nid = sn.get(sec)
            node = node_by_id.get(nid) if nid else None
            if node is None:
                continue
            # 词频密度: 出现次数 / sqrt(章节长度) — 短章节高频优先, 长表体不霸榜
            density = cnt / max(len(text) ** 0.5, 1)
            sc = min(0.85, 0.5 + density * 2)
            out.append((node, sc))
        out.sort(key=lambda x: -x[1])
        return out[:limit]

    @staticmethod
    def _main_term(q):
        """提取问题主体词(去意图词/疑问词, 取最长中文段)"""
        import re as _re
        stop = ("哪些位置", "哪些地方", "位置有描述", "在文档的", "还", "除了", "在章节", "出现外",
                "有描述", "吗", "呢", "？", "?", "哪些", "什么", "多少", "如何", "是否", "全部",
                "提到", "了", "的", "在", "和", "与", "中", "下", "外", "包含", "支持")
        t = q
        for s in stop:
            t = t.replace(s, "")
        segs = _re.findall(r"[\u4e00-\u9fff]{2,10}", t)
        return max(segs, key=len) if segs else ""

    # ------------------------------------------------------------------
    # ②③ 思维导图式激活: 中心实体 → 相关实体 → 模态分组
    # ------------------------------------------------------------------
    def activate(self, question, doc_num=None, k=2, top_k=8, min_w=0.4,
                 n_related=8):
        """question → 思维导图结构

        返回: center(输入实体) + related_entities(实体间召回) +
              groups(按模态分组的召回内容, 每节点带via来源实体)
        """
        seeds = self.find_seeds(question, doc_num)
        if not seeds:
            # 全文检索兜底: 非实体词(如人名/角色)也能激活
            term = self._main_term(question)
            if term and len(term) >= 2:
                cand_docs = [doc_num] if doc_num else sorted(self.docs.keys())
                for d in cand_docs:
                    fts = self._fulltext_nodes(d, term, limit=1)
                    if fts:
                        seeds = [(fts[0][0], 0.6, "全文检索:" + term)]
                        if not doc_num:
                            doc_num = d
                        break
        if not seeds:
            return {"ok": False, "question": question,
                    "message": "未找到种子实体, 尝试包含功能名/ID/图表号"}
        # 只取种子最集中的文档
        doc_count = defaultdict(float)
        for n, s, _ in seeds:
            doc_count[n["doc"][:2]] += s
        focus_doc = max(doc_count, key=doc_count.get) if not doc_num else doc_num
        seeds = [(n, s, w) for n, s, w in seeds if n["doc"][:2] == focus_doc]
        adj = self.adj[focus_doc]

        # ---- 中心实体: 最高分种子(E优先作tie-break) ----
        ranked = sorted(seeds, key=lambda x: (-x[1], x[0]["type"] != "E"))
        center_node, center_score, center_why = ranked[0]

        # ---- 相关实体: 中心的1跳E邻居 + 问题直接命中的其他E种子 ----
        related = {}  # id -> {node, score, rel, ev, direct}
        for nid, s, w in seeds[1:]:
            if nid["type"] == "E":
                related[nid["id"]] = {"node": nid, "score": s,
                                      "rel": "问题直接命中", "ev": w, "direct": True}
        for nbr, e in adj.get(center_node["id"], []):
            nn = self.node_index.get((focus_doc, nbr))
            if nn is None or nn["type"] != "E" or e["w"] < min_w:
                continue
            cur = related.get(nbr)
            if cur is None or e["w"] > cur["score"]:
                related[nbr] = {"node": nn, "score": e["w"], "rel": e["type"],
                                "ev": e["ev"], "direct": False}
        related_list = sorted(related.values(),
                              key=lambda r: (not r["direct"], -r["score"]))[:n_related]

        # ---- 模态内容扩展: 从中心+相关实体出发BFS ----
        frontier = [(center_node["id"], 1.0, center_node["id"])]
        for r in related_list:
            frontier.append((r["node"]["id"], r["score"], r["node"]["id"]))
        best = {}  # nid -> {score, hop, via}
        for start, s0, via in frontier:
            # 1跳: via=source entity
            for nbr, e in adj.get(start, []):
                if e["w"] < min_w:
                    continue
                cur = best.get(nbr)
                if cur is None or s0 * e["w"] > cur["score"]:
                    best[nbr] = {"score": s0 * e["w"], "hop": 1, "via": start}
            # 2跳(仅从中心/权重高的实体): via保持首跳来源
        # 2跳扩展(弱中心只走1跳, 防止发散)
        weak_center = center_node["type"] != "E" or center_score < 0.8
        if k >= 2 and not weak_center:
            hop1 = [(nid, v["score"]) for nid, v in best.items() if v["hop"] == 1]
            for nid, s in hop1:
                via = best[nid]["via"]
                for nbr, e in adj.get(nid, []):
                    if e["w"] < min_w:
                        continue
                    ns = s * e["w"]
                    cur = best.get(nbr)
                    if cur is None or ns > cur["score"]:
                        best[nbr] = {"score": ns, "hop": 2, "via": via}

        # ---- 意图定向增强 ----
        intent = self._intent(question)
        if intent == "location":
            # 位置类: 中心实体的全部出现位置全量召回(不受top_k优先截断)
            for nbr, e in adj.get(center_node["id"], []):
                if e["type"].startswith("ent_appear") and e["w"] >= min_w:
                    cur = best.get(nbr)
                    if cur is None:
                        best[nbr] = {"score": e["w"], "hop": 1, "via": center_node["id"]}
                    elif e["w"] > cur["score"]:
                        best[nbr] = {"score": e["w"], "hop": 1, "via": center_node["id"]}
            # 非实体主体词: 全文检索召回含词章节
            term = self._main_term(question)
            if term and len(term) >= 2 and (center_score < 0.85 or center_node["type"] != "E"):
                for n, sc in self._fulltext_nodes(focus_doc, term):
                    cur = best.get(n["id"])
                    if cur is None or sc > cur["score"]:
                        best[n["id"]] = {"score": sc, "hop": 1, "via": center_node["id"], "ft": 1}
        elif intent == "table_ref":
            # 表格引用: 问题中的「表N」直接召回对应TBL
            import re as _re
            for m in _re.finditer(r"[表「」\s]*(\d+)", question):
                continue  # 主匹配在下方caption通道
            for n in self.docs[focus_doc]["nodes"]:
                if n["type"] != "TBL":
                    continue
                cap = n.get("payload", {}).get("caption", "") or n.get("label", "")
                cm = _re.match(r"表\s*(\d+)", cap) or _re.search(r"表\s*(\d+)", cap)
                if cm and ("表" + cm.group(1)) in question.replace("「", "").replace("」", ""):
                    cur = best.get(n["id"])
                    if cur is None:
                        best[n["id"]] = {"score": 0.95, "hop": 1, "via": center_node["id"]}
        elif intent == "list" and center_node["type"] != "E":
            # 泛指列表问题(如"所有功能标识包含哪些子功能"): 召回全部功能划分/能力表 + 其所在章节
            seen_secs = set()
            for n in self.docs[focus_doc]["nodes"]:
                if n["type"] == "TBL":
                    cap = (n.get("payload", {}).get("caption") or "")
                    if any(kw in cap for kw in ["功能划分", "能力标识", "功能标识", "功能列表"]):
                        if n["id"] not in best:
                            best[n["id"]] = {"score": 0.85, "hop": 1,
                                             "via": center_node["id"], "ft": 1}
                        sec = n.get("section", "")
                        if sec and sec not in seen_secs:
                            seen_secs.add(sec)
                            # 表所在节 → 上溯到父节, 召回父节的全部直接子节(整个功能族的子功能概述)
                            parts = sec.split(".")
                            parent_sec = ".".join(parts[:-1]) if len(parts) > 1 else sec
                            added = 0
                            for t in self.docs[focus_doc]["nodes"]:
                                if t["type"] != "TXT" or added >= 10:
                                    continue
                                ts = t.get("section", "")
                                is_target = (ts == parent_sec) or (
                                    ts.startswith(parent_sec + ".")
                                    and ts.count(".") == parent_sec.count(".") + 1)
                                if is_target:
                                    cur = best.get(t["id"])
                                    if cur is None or 0.78 > cur["score"]:
                                        best[t["id"]] = {"score": 0.78, "hop": 1,
                                                         "via": center_node["id"], "ft": 1}
                                        added += 1
                elif n["type"] == "TXT":
                    sec = n.get("section", "")
                    if sec in ("1.2", "3.1", "3.2") and n["id"] not in best:
                        best[n["id"]] = {"score": 0.7, "hop": 1, "via": center_node["id"]}

        # ---- 按模态分组 ----
        groups = defaultdict(list)
        exclude = {center_node["id"]} | {r["node"]["id"] for r in related_list}
        for nid, v in best.items():
            if nid in exclude:
                continue
            node = self.node_index.get((focus_doc, nid))
            if node is None:
                continue
            via_node = self.node_index.get((focus_doc, v["via"]))
            entry = dict(node)
            entry["score"] = round(v["score"], 3)
            entry["hop"] = v["hop"]
            entry["via"] = v["via"]
            entry["via_label"] = ((via_node["payload"].get("aliases") or [""])[0]
                                  or via_node["label"][:12]) if via_node else ""
            entry["ft"] = v.get("ft", 0)
            groups[node["type"]].append(entry)
        # ---- 精度优化: 相关性重排 + 低相关剔除 + TXT父子折叠 ----
        for mod in list(groups.keys()):
            lst = groups[mod]
            for n in lst:
                rel = self._relevance(question, n)
                if n.get("ft"):
                    # 全文检索命中项: 相关性保底(词频命中本身即证据)
                    rel = max(rel, 0.65)
                n["_rel"] = round(rel, 3)
            # 综合分 = 0.45*路径分 + 0.55*问题相关性
            lst.sort(key=lambda n: -(0.45 * n["score"] + 0.55 * n["_rel"]))
            lst = lst[:top_k]
            lst = [n for n in lst if 0.45 * n["score"] + 0.55 * n["_rel"] >= 0.30]
            if mod == "TXT":
                # 父子折叠: 子章节在场则去父(留更具体的)
                lst = [n for n in lst
                       if not any(o is not n and o["section"].startswith(n["section"] + ".")
                                  for o in lst)]
            groups[mod] = lst

        # ---- 边集(激活节点之间, 供tooltip) ----
        active_ids = exclude | {n["id"] for lst in groups.values() for n in lst}
        out_edges = [e for e in self.docs[focus_doc]["edges"]
                     if e["s"] in active_ids and e["t"] in active_ids]

        # ---- 聚合条目 ----
        rel_items = []
        seen = set()
        for ent in [center_node] + [r["node"] for r in related_list]:
            eid = ent["id"].split(":", 1)[1]
            it = self.items.get((focus_doc, eid))
            if it and eid not in seen:
                seen.add(eid)
                rel_items.append(it)

        center_out = dict(center_node)
        center_out["score"] = center_score
        center_out["why"] = center_why
        return {
            "ok": True, "question": question, "doc": focus_doc,
            "doc_name": self.docs[focus_doc]["meta"]["doc"],
            "center": center_out,
            "related_entities": [
                {"id": r["node"]["id"], "label": r["node"]["label"],
                 "aliases": r["node"]["payload"].get("aliases", []),
                 "id_str": r["node"]["payload"].get("id_str", ""),
                 "score": round(r["score"], 3), "rel": r["rel"], "ev": r["ev"],
                 "node": r["node"]}
                for r in related_list],
            "groups": {m: groups.get(m, []) for m in MODALITIES},
            "edges": out_edges,
            "items": rel_items[:8],
            "stats": {
                "n_related": len(related_list),
                "n_content": sum(len(v) for v in groups.values()),
                "by_modality": {m: len(groups.get(m, [])) for m in MODALITIES},
            },
        }

    @staticmethod
    def _relevance(question, node):
        """问题与节点的文本相关性: 字符二元组重叠率"""
        import re as _re

        def clean(s):
            return _re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", str(s or ""))

        q = clean(question)
        if len(q) < 2:
            return 0.0
        qg = set(q[i:i + 2] for i in range(len(q) - 1))
        p = node.get("payload", {}) or {}
        txt = " ".join([str(node.get("label", "")),
                        str(p.get("caption", "") or ""),
                        str(p.get("title", "") or ""),
                        str(p.get("text_preview", "") or "")])
        t = clean(txt)
        if len(t) < 2:
            return 0.0
        tg = set(t[i:i + 2] for i in range(len(t) - 1))
        return len(qg & tg) / len(qg)


if __name__ == "__main__":
    import time
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    cg = ContextGraph()
    print(f"图谱加载: {time.time()-t0:.2f}s, {len(cg.docs)}文档, "
          f"{sum(g['meta']['n_nodes'] for g in cg.docs.values())}节点")
    for q in ["结构化数据归集出现在文档的哪些位置有描述?",
              "表3 界面开发能力标识列出了6个功能,正文是否全部提到?",
              "ZZSJHQZHFW-GN-SJHQ 的合格性方法是什么?",
              "开发工程生成的需求标识符是什么?"]:
        t0 = time.time()
        r = cg.activate(q)
        ms = (time.time() - t0) * 1000
        if r["ok"]:
            c = r["center"]
            print(f"\nQ: {q[:38]}  [{ms:.0f}ms, doc{r['doc']}]")
            print(f"   中心: {c['type']} {c['label'][:22]} ({c['why'][:14]})")
            print(f"   相关实体({r['stats']['n_related']}): " +
                  ", ".join(f"{x['aliases'][0] if x['aliases'] else x['id_str'][-10:]}({x['rel'][:6]})"
                            for x in r["related_entities"][:4]))
            print("   分组: " + " ".join(f"{m}:{n}" for m, n in r["stats"]["by_modality"].items() if n))
            print(f"   条目: {[it['entity_id'][-16:] for it in r['items'][:3]]}")
        else:
            print(f"\nQ: {q[:38]} → {r['message']} [{ms:.0f}ms]")
