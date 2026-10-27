#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上下文关联图谱构建管道（离线批处理）

把16份GJB SRS的全量数据资产处理成「上下文关联图谱」:
  6类节点: E实体 / TXT文本 / TBL表格 / IMG图片 / SEQ时序 / KNW知识
  两类边:  同模态边(文-文/表-表/图-图/实体-实体/时序-时序)
           跨模态边(E为枢纽 + 引用/邻接/映射)
  三档权重: 确定性信号(固定高权) / 计算信号(0.4-0.8) / 对齐置信(比例)

数据源(全部已有资产, 无需新采):
  stage0_assets.json     id_registry(971ID/2016处) section_registry(1444节)
                        table_index(1207表) figure_index(381图)
                        traceability_map(1022) interface_topology(1414)
                        version_pairs(25) exception_flows(426)
  anchors_v2.json        373结构/3759节点/2680边 (born-digital锚点步骤链)
  visio_section_mapping  373条 图-章节映射
  usecase_features       406条用例表特征
  knowledge/             GJB 120规则 + srs_kb词典 + 14条不一致规则
  mineru_standard/       16份content_list (交叉引用解析)

输出: data/gjb_438c/graph_store/
  {NN}.json    每文档图谱 {meta, nodes, edges, items}
  global.json  跨文档层 {cross_doc_edges, doc_registry, knw_nodes}
  _summary.json 数据体检报告

用法: python tools/build_context_graph.py [--doc 01] [--out data/gjb_438c/graph_store]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "data/gjb_438c/data_assets")
OUT_DIR = os.path.join(BASE, "data/gjb_438c/graph_store")

ID_RE = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}")
REF_FIG_RE = re.compile(r"[如见]?图\s*(\d+)")
REF_TBL_RE = re.compile(r"[如见]?表\s*(\d+)")


def load(rel):
    return json.load(open(os.path.join(BASE, rel), encoding="utf-8"))


def doc_num(doc_name):
    m = re.search(r"^(\d{2})", doc_name)
    return m.group(1) if m else "00"


# ---------------------------------------------------------------------------
# 节点构造
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self):
        self.stage0 = load("data/gjb_438c/data_assets/stage0_assets.json")
        self.anchors = load("data/gjb_438c/anchor_v2/anchors_v2.json")
        self.visio_map = load("data/gjb_438c/data_assets/graph/visio_section_mapping.json")
        self.usecase_feats = load("data/gjb_438c/data_assets/usecase_features.json")
        # 场景语义模型(与anchors_v2的structures按索引对齐)
        try:
            self.scene_models = load("data/gjb_438c/anchor_v2/scene_models.json")
        except FileNotFoundError:
            self.scene_models = {}
        gjb = load("knowledge/gjb_438c_rules_full.json")
        self.gjb_rules = gjb.get("rules", [])
        kb = load("knowledge/srs_kb.json")
        self.kb = kb
        inc = load("knowledge/inconsistency_rules.json")
        self.inc_rules = inc.get("rules", [])
        # content_list 加载(交叉引用解析 + 正文预览/表头提取)
        self.content_lists = {}
        self.section_texts = {}     # doc -> {section: 正文聚合}
        self.table_bodies = {}      # doc -> {caption: table_body HTML}
        for p in glob.glob(os.path.join(BASE, "data/gjb_438c/mineru_standard/*/office/*content_list.json")):
            name = os.path.basename(p).replace("_content_list.json", "")
            cl = json.load(open(p, encoding="utf-8"))
            self.content_lists[name] = cl
            self._extract_content(name, cl)
        # mermaid索引: doc全名 -> {embed_index: key}
        self.mermaid_by_doc = defaultdict(dict)
        try:
            mexp = load("data/gjb_438c/anchor_v2/mermaid_export.json")
            for key, v in mexp.items():
                self.mermaid_by_doc[v["doc"]][v["embed"]] = key
        except FileNotFoundError:
            pass
        # id_registry 反查表: doc -> [(ID, occurrence)]
        self.id_by_doc = defaultdict(list)
        for rid, occs in self.stage0["id_registry"].items():
            for o in occs:
                self.id_by_doc[o["doc"]].append((rid, o))
        # table_index / figure_index 按doc
        self.tables_by_doc = self.stage0["table_index"]
        self.figures_by_doc = self.stage0["figure_index"]
        # section->tables / section->figures 索引(每文档)
        self._sec_tables = {}
        self._sec_figures = {}
        for doc, tbls in self.tables_by_doc.items():
            idx = defaultdict(list)
            for i, t in enumerate(tbls):
                idx[t.get("section", "")].append(i)
            self._sec_tables[doc] = idx
        for doc, figs in self.figures_by_doc.items():
            idx = defaultdict(list)
            for i, f in enumerate(figs):
                idx[f.get("section", "")].append(i)
            self._sec_figures[doc] = idx

    # ---------- 节点ID规范 ----------
    @staticmethod
    def nid_txt(doc, section):
        return f"t:{doc_num(doc)}:{section}"

    @staticmethod
    def nid_tbl(doc, section, caption):
        return f"tbl:{doc_num(doc)}:{section}:{caption[:20]}"

    @staticmethod
    def nid_img(doc, fig_num):
        return f"img:{doc_num(doc)}:{fig_num}"

    @staticmethod
    def nid_ent(entity_id):
        return f"e:{entity_id}"

    @staticmethod
    def nid_seq(doc, key):
        return f"seq:{doc_num(doc)}:{key}"

    @staticmethod
    def nid_knw(rule_id):
        return f"knw:{rule_id}"

    def _extract_content(self, doc, cl):
        """从content_list提取: 按章节聚合正文 + caption→表格HTML"""
        sec_texts = defaultdict(list)
        cur_sec = ""
        for item in cl:
            if not isinstance(item, dict):
                continue
            t = item.get("type", "")
            if t == "text":
                text = item.get("text", "")
                m = re.match(r"^(\d+(?:\.\d+)*)\s+", text.strip())
                if m:
                    cur_sec = m.group(1)
                if len(text.strip()) > 15:
                    sec_texts[cur_sec].append(text.strip())
            elif t == "table":
                caps = item.get("table_caption", [])
                cap = caps[0] if caps else ""
                if cap:
                    self.table_bodies.setdefault(doc, {})[cap] = item.get("table_body", "")
        self.section_texts[doc] = {s: " ".join(ts) for s, ts in sec_texts.items()}

    @staticmethod
    def _tbl_headers(body_html, n=6):
        """从表格HTML提取前n个表头单元格(去标签)"""
        cells = re.findall(r"<th[^>]*>(.*?)</th>", body_html or "", re.S)
        heads = [re.sub(r"<[^>]+>", "", c).strip()[:10] for c in cells if c.strip()]
        return heads[:n]

    def _mermaid_key_for(self, doc, section, caption):
        """IMG节点 → mermaid导出key: 同section的visio页中选caption与节点文本重叠最高者"""
        vmap = self.visio_map.get(doc, [])
        structs = self.anchors.get(doc, {}).get("structures", [])
        mbd = self.mermaid_by_doc.get(doc, {})
        if not vmap or not mbd:
            return None
        best, best_score = None, 0.0
        cap_grams = set(caption[i:i+2] for i in range(len(caption) - 1)) if caption else set()
        for pi, m in enumerate(vmap):
            if m.get("matched_section") != section:
                continue
            embed = structs[pi].get("embed_index") if pi < len(structs) else None
            if not embed or embed not in mbd:
                continue
            node_texts = "".join(m.get("node_texts", []))
            nt_grams = set(node_texts[i:i+2] for i in range(len(node_texts) - 1))
            overlap = len(cap_grams & nt_grams) / max(len(cap_grams), 1)
            score = overlap + (m.get("match_score", 0) or 0)
            if score > best_score:
                best, best_score = mbd[embed], score
        return best

    # ------------------------------------------------------------------
    # 单文档构建
    # ------------------------------------------------------------------
    def build_doc(self, doc):
        num = doc_num(doc)
        nodes, edges = [], []
        node_ids = set()

        def add_node(nid, ntype, label, section="", payload=None):
            if nid in node_ids:
                return
            node_ids.add(nid)
            nodes.append({
                "id": nid, "type": ntype, "label": label[:40],
                "doc": doc, "section": section, "payload": payload or {},
            })

        def add_edge(s, t, etype, w, ev=""):
            if s == t or s not in node_ids or t not in node_ids:
                return
            edges.append({"s": s, "t": t, "type": etype, "w": round(w, 3), "ev": ev[:160]})

        # ============ TXT 节点: section_registry ============
        sections = self.stage0["section_registry"].get(doc, {})
        sec_text_map = self.section_texts.get(doc, {})
        for sec, info in sections.items():
            full_text = sec_text_map.get(sec, "")
            add_node(self.nid_txt(doc, sec), "TXT", f"{sec} {info.get('title', '')}", sec,
                     {"title": info.get("title", ""), "level": info.get("level", 1),
                      "text_preview": full_text[:120],
                      "text_len": len(full_text)})

        # TXT-TXT 层级边(父子) + 顺序邻接
        sec_nums = sorted(sections.keys(), key=lambda s: [int(x) for x in s.split(".") if x.isdigit()])
        for sec in sec_nums:
            parts = sec.split(".")
            if len(parts) > 1:
                parent = ".".join(parts[:-1])
                if parent in sections:
                    add_edge(self.nid_txt(doc, sec), self.nid_txt(doc, parent), "section_hierarchy", 0.7,
                             f"{sec}⊂{parent}")
        for a, b in zip(sec_nums, sec_nums[1:]):
            add_edge(self.nid_txt(doc, a), self.nid_txt(doc, b), "section_adjacent", 0.5,
                     f"相邻章节 {a}→{b}")

        # ============ TBL 节点: table_index ============
        for t in self.tables_by_doc.get(doc, []):
            cap, sec = t.get("caption", ""), t.get("section", "")
            if not cap:
                cap = f"表@{sec or '未知章节'}"
                t["caption"] = cap
            body = self.table_bodies.get(doc, {}).get(cap, "")
            add_node(self.nid_tbl(doc, sec, cap), "TBL", cap, sec,
                     {"caption": cap, "table_type": t.get("type", "unknown"),
                      "row_count": t.get("row_count", 0),
                      "headers": self._tbl_headers(body)})
            # TBL→TXT 位置邻接(所有表挂到所属章节)
            if sec in sections:
                add_edge(self.nid_tbl(doc, sec, cap), self.nid_txt(doc, sec),
                         "located_in", 0.6, f"表格位于章节{sec}")
        # TBL-TBL 同章节共现
        for sec, idxs in self._sec_tables.get(doc, {}).items():
            tbl_nodes = [self.nid_tbl(doc, sec, self.tables_by_doc[doc][i].get("caption", "")) for i in idxs]
            for i in range(len(tbl_nodes)):
                for j in range(i + 1, len(tbl_nodes)):
                    add_edge(tbl_nodes[i], tbl_nodes[j], "same_section_tbl", 0.5, f"同章节{sec}")

        # TBL-TBL 版本对齐边 (version_pairs: 同doc同software跨section)
        vp_groups = defaultdict(list)
        for v in self.stage0.get("version_pairs", []):
            if v.get("doc") == doc:
                vp_groups[v.get("software", "")].append(v)
        for sw, recs in vp_groups.items():
            if len(recs) >= 2:
                secs = sorted(set(r.get("section", "") for r in recs))
                for i in range(len(secs)):
                    for j in range(i + 1, len(secs)):
                        for ti in self._sec_tables.get(doc, {}).get(secs[i], []):
                            for tj in self._sec_tables.get(doc, {}).get(secs[j], []):
                                cap_i = self.tables_by_doc[doc][ti].get("caption", "")
                                cap_j = self.tables_by_doc[doc][tj].get("caption", "")
                                add_edge(self.nid_tbl(doc, secs[i], cap_i),
                                         self.nid_tbl(doc, secs[j], cap_j),
                                         "version_alignment", 0.9, f"版本对齐:{sw}")

        # ============ IMG 节点: figure_index ============
        for f in self.figures_by_doc.get(doc, []):
            fnum, cap, sec = f.get("fig_num"), f.get("caption", ""), f.get("section", "")
            add_node(self.nid_img(doc, fnum), "IMG", cap, sec,
                     {"caption": cap, "img_type": f.get("type", "unknown"),
                      "path": f.get("path", ""), "exists": f.get("exists", False),
                      "mermaid_key": self._mermaid_key_for(doc, sec, cap)})
            # IMG→TXT 位置邻接(所有图挂到所属章节)
            if sec in sections:
                add_edge(self.nid_img(doc, fnum), self.nid_txt(doc, sec),
                         "located_in", 0.6, f"图片位于章节{sec}")
        # IMG-IMG 同章节共现
        for sec, idxs in self._sec_figures.get(doc, {}).items():
            img_nodes = [self.nid_img(doc, self.figures_by_doc[doc][i].get("fig_num")) for i in idxs]
            for i in range(len(img_nodes)):
                for j in range(i + 1, len(img_nodes)):
                    add_edge(img_nodes[i], img_nodes[j], "same_section_img", 0.5, f"同章节{sec}")

        # ============ E 节点 + E-M 边: id_registry ============
        # 先收集每个ID在该doc的中文别名(从context提取: 名称在ID前后)
        ent_aliases = defaultdict(set)
        for rid, occ in self.id_by_doc.get(doc, []):
            ctx = occ.get("context", "")
            for mm in re.finditer(
                    r"([\u4e00-\u9fff][\u4e00-\u9fff\w（）]{1,24})[/(（:：]?\s*(?:<[^>]+>\s*)*"
                    + re.escape(rid), ctx):
                name = mm.group(1).strip()
                # 去掉尾巴上的标点/括号/空白(如"开发工程生成（")
                name = name.rstrip("（）()、。，,;；:：丶—-· 　")
                # 去掉成对括号包裹的后缀(如"界面开发功能（桌面版）"→保留主干也存全名)
                core = re.sub(r"[（(][^）)]{1,12}[）)]$", "", name).strip()
                if 2 <= len(core) <= 24:
                    ent_aliases[rid].add(core)
                if 2 <= len(name) <= 24 and name != core:
                    ent_aliases[rid].add(name)
        for rid, occ in self.id_by_doc.get(doc, []):
            sec, loc, ctx = occ.get("section", ""), occ.get("location", ""), occ.get("context", "")
            add_node(self.nid_ent(rid), "E", rid, sec,
                     {"id_str": rid, "n_occ": 0,
                      "aliases": sorted(ent_aliases.get(rid, []))[:8]})
            # E→TXT (出现章节)
            if sec in sections:
                add_edge(self.nid_ent(rid), self.nid_txt(doc, sec), "ent_appear_txt", 0.9,
                         f"位置:{loc} | {ctx[:80]}")
            # E→TBL (表格式位置 → 该章节的表; 单表精确0.95, 多表0.8)
            if "table" in loc or "qualification" in loc or "trace" in loc:
                tbl_idxs = self._sec_tables.get(doc, {}).get(sec, [])
                w = 0.95 if len(tbl_idxs) == 1 else 0.8
                for ti in tbl_idxs:
                    cap = self.tables_by_doc[doc][ti].get("caption", "")
                    add_edge(self.nid_ent(rid), self.nid_tbl(doc, sec, cap), "ent_appear_tbl", w,
                             f"位置:{loc} | {ctx[:80]}")

        # ============ SEQ 节点(锚点步骤链) + SEQ-IMG/TXT 边 ============
        anchor_structs = self.anchors.get(doc, {}).get("structures", [])
        vmap = self.visio_map.get(doc, [])
        scene_models = (self.scene_models.get(doc, {}) or {}).get("models", [])
        for pi, st in enumerate(anchor_structs):
            a_nodes, a_edges = st.get("nodes", []), st.get("edges", [])
            steps = [n.get("text", "") for n in a_nodes if n.get("text")]
            if not steps:
                continue
            # 场景语义增强: 若该结构有场景模型, 用语义化步骤/用例替代原始文本
            payload = {"seq_type": "anchor_chain", "n_steps": len(steps),
                       "steps": steps[:20], "n_edges": len(a_edges),
                       "embed_index": st.get("embed_index", "")}
            smodel = scene_models[pi] if pi < len(scene_models) else None
            if smodel and smodel.get("_classify", {}).get("type") == "flowchart" \
                    and smodel.get("steps"):
                payload["seq_type"] = "flowchart_steps"
                payload["steps"] = [s["name"] or f"#{s['order']}"
                                    for s in smodel["steps"][:25] if s.get("name")]
                payload["n_steps"] = len(payload["steps"])
                payload["direction"] = smodel.get("direction")
                payload["main_path"] = smodel.get("main_path", [])[:15]
                payload["exception_flows"] = smodel.get("exception_flows", [])[:6]
            elif smodel and smodel.get("_classify", {}).get("type") == "usecase_diagram":
                payload["seq_type"] = "usecase_diagram"
                payload["usecases"] = [u["name"] for u in smodel.get("usecases", []) if u["name"]][:15]
                payload["primary_actors"] = smodel.get("primary_actors", [])[:8]
                payload["external_systems"] = smodel.get("external_systems", [])[:8]
                payload["n_steps"] = len(payload["usecases"])
            elif smodel and smodel.get("_classify", {}).get("type") == "interface_diagram":
                payload["seq_type"] = "interface_structure"
                payload["systems"] = smodel.get("systems", [])[:12]
                payload["interfaces"] = [i["name"] for i in smodel.get("interfaces", [])][:12]
                payload["n_steps"] = len(payload.get("interfaces", []))
            sid = self.nid_seq(doc, f"anchor{pi}")
            label_src = payload["steps"] or steps
            add_node(sid, "SEQ",
                     f"步骤链[{label_src[0][:8]}…]" if len(label_src) > 1 else (label_src[0] if label_src else "步骤链"),
                     "", payload)
            # SEQ→TXT: visio_section_mapping 按页号对齐
            if pi < len(vmap):
                m = vmap[pi]
                msec, score = m.get("matched_section", ""), m.get("match_score", 0)
                if msec in sections:
                    add_edge(sid, self.nid_txt(doc, msec), "anchor_section_map", 0.9 * score,
                             f"图-章节映射 score={score}")

        # ============ SEQ 节点(异常流) + SEQ-TBL 边 ============
        for ef in self.stage0.get("exception_flows", []):
            if ef.get("doc") != doc:
                continue
            sec, ucn = ef.get("section", ""), ef.get("uc_name", "")
            defined, referenced = ef.get("defined_exceptions", []), ef.get("referenced_exceptions", [])
            dangling = ef.get("dangling_refs", [])
            sid = self.nid_seq(doc, f"exc:{sec}:{ucn[:12]}")
            if sid in node_ids:
                continue
            add_node(sid, "SEQ", f"异常流:{ucn[:14]}", sec,
                     {"seq_type": "exception_flow", "uc_name": ucn,
                      "defined": defined, "referenced": referenced, "dangling": dangling})
            # SEQ→TBL: 同章节用例表
            for ti in self._sec_tables.get(doc, {}).get(sec, []):
                cap = self.tables_by_doc[doc][ti].get("caption", "")
                if "用例" in cap or "usecase" in cap:
                    add_edge(sid, self.nid_tbl(doc, sec, cap), "exc_belong_tbl", 0.9, "异常流属于用例表")

        # ============ TXT→IMG/TBL 交叉引用边 ============
        cl = self.content_lists.get(doc, [])
        cur_sec = ""
        fig_caps = {f.get("fig_num"): f.get("caption", "") for f in self.figures_by_doc.get(doc, [])}
        for item in cl:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            text = item.get("text", "")
            m = re.match(r"^(\d+(?:\.\d+)*)\s+", text.strip())
            if m:
                cur_sec = m.group(1)
            if cur_sec not in sections:
                continue
            for fm in REF_FIG_RE.finditer(text):
                fnum = int(fm.group(1))
                if fnum in fig_caps:
                    add_edge(self.nid_txt(doc, cur_sec), self.nid_img(doc, fnum),
                             "cross_ref_img", 0.85, f"正文引用图{fnum}")
            for tm in REF_TBL_RE.finditer(text):
                tnum = int(tm.group(1))
                for t in self.tables_by_doc.get(doc, []):
                    cap = t.get("caption", "")
                    cm = re.match(r"^表\s*(\d+)", cap)
                    if cm and int(cm.group(1)) == tnum:
                        add_edge(self.nid_txt(doc, cur_sec), self.nid_tbl(doc, t.get("section", ""), cap),
                                 "cross_ref_tbl", 0.85, f"正文引用表{tnum}")

        # ============ KNW 节点 + KNW→M 边 ============
        # 14条不一致规则: applies_to 映射到表型/图型
        APPLIES_MAP = {
            "capability_table": ("TBL", ["capability", "能力"]),
            "usecase_table": ("TBL", ["用例", "usecase"]),
            "interface_table": ("TBL", ["接口", "interface"]),
            "usecase_diagram": ("IMG", ["usecase", "用例"]),
            "flowchart": ("IMG", ["flow", "流程"]),
            "interface_diagram": ("IMG", ["接口", "interface"]),
            "text": ("TXT", []),
        }
        for rule in self.inc_rules:
            rid = rule.get("rule_id", "")
            knid = self.nid_knw(rid)
            add_node(knid, "KNW", f"{rid} {rule.get('description', '')[:20]}", "",
                     {"rule_type": rule.get("type", ""), "description": rule.get("description", ""),
                      "severity": rule.get("severity", ""), "source": "inconsistency_rules"})
            targets = rule.get("applies_to", [])
            mtype_kw = None
            for a in targets:
                if a in APPLIES_MAP:
                    mtype_kw = APPLIES_MAP[a]
                    break
            if not mtype_kw:
                continue
            mtype, kws = mtype_kw
            if mtype == "TBL":
                for t in self.tables_by_doc.get(doc, []):
                    tt, cap = t.get("type", ""), t.get("caption", "")
                    if any(k in tt for k in kws) or any(k in cap for k in kws):
                        add_edge(knid, self.nid_tbl(doc, t.get("section", ""), cap),
                                 "rule_applies", 0.7, f"规则适用于{cap[:20]}")
            elif mtype == "IMG":
                for f in self.figures_by_doc.get(doc, []):
                    ft = f.get("type", "")
                    if any(k in ft for k in kws):
                        add_edge(knid, self.nid_img(doc, f.get("fig_num")),
                                 "rule_applies", 0.7, f"规则适用于图{f.get('fig_num')}")

        # GJB规则: 描述含特定表型关键词的挂到对应表
        TBL_KW = {"用例": ["用例"], "追踪": ["追踪", "追溯"], "合格性": ["合格"], "接口": ["接口"]}
        for rule in self.gjb_rules:
            rid = rule.get("rule_id", "")
            desc = rule.get("description", "")
            knid = self.nid_knw(rid)
            add_node(knid, "KNW", f"{rid} {desc[:20]}", "",
                     {"rule_type": rule.get("type", ""), "description": desc,
                      "severity": rule.get("severity", ""), "source": "gjb_438c"})
            for kw, hits in TBL_KW.items():
                if kw in desc:
                    for t in self.tables_by_doc.get(doc, []):
                        cap = t.get("caption", "")
                        if any(h in cap for h in hits):
                            add_edge(knid, self.nid_tbl(doc, t.get("section", ""), cap),
                                     "rule_applies", 0.6, f"GJB规则涉及{kw}表")

        # ============ E-E 边: 实体间关联(思维导图实体层) ============
        doc_ents = sorted(set(r for r, _ in self.id_by_doc.get(doc, [])))
        ent_set = set(doc_ents)
        # 1. ID层级: 前缀包含(父功能-子功能), 如 PZXQ-GN-JMJCKJ ⊃ PZXQ-GN-JMJCKJ-JMKF
        for rid in doc_ents:
            parts = rid.split("-")
            for L in range(len(parts) - 1, 0, -1):
                prefix = "-".join(parts[:L])
                if prefix in ent_set:
                    add_edge(self.nid_ent(rid), self.nid_ent(prefix), "ent_hierarchy",
                             0.85, f"ID层级: {prefix} 的子功能")
                    break
        # 2. 同章节共现: 同一章节出现的实体(限定数量防爆边)
        sec_ents = defaultdict(set)
        for rid, occ in self.id_by_doc.get(doc, []):
            sec_ents[occ.get("section", "")].add(rid)
        from itertools import combinations
        for sec, rids in sec_ents.items():
            rids = sorted(rids)
            if 1 < len(rids) <= 8:
                for a, b in combinations(rids, 2):
                    add_edge(self.nid_ent(a), self.nid_ent(b), "ent_cooccur",
                             0.55, f"同章节共现: {sec}")
        # 3. 同表共现: 同一表格位置出现的实体(能力表兄弟功能)
        tblloc_ents = defaultdict(set)
        for rid, occ in self.id_by_doc.get(doc, []):
            loc = occ.get("location", "")
            if "table" in loc:
                tblloc_ents[(occ.get("section", ""), loc)].add(rid)
        for (sec, loc), rids in tblloc_ents.items():
            rids = sorted(rids)
            if 1 < len(rids) <= 10:
                for a, b in combinations(rids, 2):
                    add_edge(self.nid_ent(a), self.nid_ent(b), "ent_same_table",
                             0.7, f"同表共现: {sec}")

        # ============ 聚合条目 RequirementItems ============
        # 先补挂孤立锚点SEQ → 文档根章节(诚实弱权重)
        linked = set()
        for e in edges:
            linked.add(e["s"]); linked.add(e["t"])
        root_sec = next((s for s in sec_nums if "." not in s), None) \
            or (sec_nums[0] if sec_nums else None)
        for n in nodes:
            if n["type"] == "SEQ" and n["id"] not in linked \
                    and n["payload"].get("seq_type") == "anchor_chain" and root_sec:
                add_edge(n["id"], self.nid_txt(doc, root_sec), "anchor_root_fallback",
                         0.4, "锚点未精确定位章节,挂文档根")
                linked.add(n["id"])

        items = []
        for rid in sorted(set(r for r, _ in self.id_by_doc.get(doc, []))):
            occs = [(r, o) for r, o in self.id_by_doc.get(doc, []) if r == rid]
            secs = sorted(set(o.get("section", "") for _, o in occs))
            locs = [o.get("location", "") for _, o in occs]
            has_title = any("title" in l for l in locs)
            has_func = any(("func" in l or "capability" in l) for l in locs)
            has_qual = any(("qualification" in l or "合格" in l) for l in locs)
            has_trace = any(("trace" in l or "追踪" in l or "追溯" in l) for l in locs)
            media = []
            for sec in secs:
                for ti in self._sec_tables.get(doc, {}).get(sec, []):
                    media.append({"modality": "table",
                                  "caption": self.tables_by_doc[doc][ti].get("caption", "")})
                for fi in self._sec_figures.get(doc, {}).get(sec, []):
                    media.append({"modality": "image",
                                  "caption": self.figures_by_doc[doc][fi].get("caption", "")})
            items.append({
                "entity_id": rid, "doc": doc, "sections": secs,
                "n_occurrences": len(occs),
                "occurrence_sections": secs,
                "media": media[:12],
                "chain_completeness": {
                    "has_title": has_title, "has_func_table": has_func,
                    "has_qualification": has_qual, "has_trace": has_trace,
                    "score": round((has_title + has_func + has_qual + has_trace) / 4, 2),
                },
            })

        meta = {
            "doc": doc, "doc_num": num,
            "n_nodes": len(nodes), "n_edges": len(edges), "n_items": len(items),
            "node_types": dict(Counter(n["type"] for n in nodes)),
            "edge_types": dict(Counter(e["type"] for e in edges)),
        }
        return {"meta": meta, "nodes": nodes, "edges": edges, "items": items}

    @staticmethod
    def prune_isolated_knw(graph):
        """删除无边KNW节点(保留在全局registry), 保持文档图连通密度"""
        linked = set()
        for e in graph["edges"]:
            linked.add(e["s"]); linked.add(e["t"])
        before = len(graph["nodes"])
        graph["nodes"] = [n for n in graph["nodes"]
                          if n["type"] != "KNW" or n["id"] in linked]
        pruned = before - len(graph["nodes"])
        if pruned:
            graph["meta"]["n_nodes"] = len(graph["nodes"])
            graph["meta"]["node_types"]["KNW"] -= pruned
        return pruned

    # ------------------------------------------------------------------
    # 全局层: 跨文档边
    # ------------------------------------------------------------------
    def build_global(self, doc_graphs):
        cross_edges = []
        # KNW全量registry(文档图只保留有边的)
        knw_registry = []
        for rule in self.inc_rules:
            knw_registry.append({"rule_id": rule.get("rule_id", ""),
                                 "source": "inconsistency_rules",
                                 "type": rule.get("type", ""),
                                 "description": rule.get("description", "")})
        for rule in self.gjb_rules:
            knw_registry.append({"rule_id": rule.get("rule_id", ""),
                                 "source": "gjb_438c",
                                 "type": rule.get("type", ""),
                                 "description": rule.get("description", "")})
        for pname, pd in self.kb.get("param_dictionary", {}).items():
            knw_registry.append({"rule_id": f"PARAM-{pname}",
                                 "source": "srs_kb", "type": "param",
                                 "description": pd.get("canonical_cn", pname),
                                 "synonyms": pd.get("synonyms_en", [])[:6]})
        for fam, ud in self.kb.get("unit_dictionary", {}).items():
            knw_registry.append({"rule_id": f"UNIT-{fam}",
                                 "source": "srs_kb", "type": "unit_family",
                                 "description": f"{fam}: {','.join(ud.get('units', [])[:8])}"})
        id_docs = defaultdict(set)
        for rid, occs in self.stage0["id_registry"].items():
            for o in occs:
                id_docs[rid].add(o["doc"])
        # 跨文档共享ID
        for rid, docs in id_docs.items():
            if len(docs) > 1:
                ds = sorted(docs)
                for i in range(len(ds)):
                    for j in range(i + 1, len(ds)):
                        cross_edges.append({
                            "s": self.nid_ent(rid), "t": self.nid_ent(rid),
                            "type": "xdoc_shared_id", "w": 0.85,
                            "ev": f"ID {rid} 同时出现于 {ds[i][:12]} 与 {ds[j][:12]}",
                            "doc_s": ds[i], "doc_t": ds[j],
                        })
        # 接口拓扑: 同接口ID跨文档
        if_map = defaultdict(list)
        for it in self.stage0.get("interface_topology", []):
            if it.get("id"):
                if_map[it["id"]].append(it)
        for ifid, recs in if_map.items():
            docs = sorted(set(r.get("doc", "") for r in recs))
            if len(docs) > 1:
                for i in range(len(docs)):
                    for j in range(i + 1, len(docs)):
                        cross_edges.append({
                            "s": self.nid_ent(ifid), "t": self.nid_ent(ifid),
                            "type": "xdoc_interface", "w": 0.9,
                            "ev": f"接口 {ifid} 定义于多份文档",
                            "doc_s": docs[i], "doc_t": docs[j],
                        })
        doc_registry = []
        for g in doc_graphs:
            m = g["meta"]
            doc_registry.append({"doc": m["doc"], "doc_num": m["doc_num"],
                                 "n_nodes": m["n_nodes"], "n_edges": m["n_edges"]})
        return {"cross_doc_edges": cross_edges, "doc_registry": doc_registry,
                "knw_registry": knw_registry, "n_cross": len(cross_edges)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", help="只构建指定文档(如 01)")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    builder = GraphBuilder()
    docs = sorted(builder.stage0["section_registry"].keys(), key=doc_num)
    if args.doc:
        docs = [d for d in docs if doc_num(d) == args.doc]
        if not docs:
            print(f"未找到文档 {args.doc}")
            return

    all_graphs = []
    total = Counter()
    for doc in docs:
        g = builder.build_doc(doc)
        pruned = builder.prune_isolated_knw(g)
        num = doc_num(doc)
        out_path = os.path.join(args.out, f"{num}.json")
        json.dump(g, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
        all_graphs.append(g)
        m = g["meta"]
        total.update(m["node_types"])
        print(f"[{num}] {doc[:24]:26s} 节点={m['n_nodes']:4d} 边={m['n_edges']:4d} "
              f"条目={m['n_items']:3d} (剪除孤立KNW {pruned}) | " +
              " ".join(f"{k}:{v}" for k, v in sorted(m["node_types"].items())))
        # 环体检: 孤立节点
        linked = set()
        for e in g["edges"]:
            linked.add(e["s"]); linked.add(e["t"])
        iso = [n for n in g["nodes"] if n["id"] not in linked]
        if iso:
            print(f"      ⚠ 孤立节点 {len(iso)}: " +
                  ", ".join(f"{n['type']}:{n['label'][:10]}" for n in iso[:5]))

    if not args.doc:
        glob_g = builder.build_global(all_graphs)
        json.dump(glob_g, open(os.path.join(args.out, "global.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        total_edges = sum(g["meta"]["n_edges"] for g in all_graphs)
        summary = {
            "docs": len(all_graphs),
            "total_nodes": sum(g["meta"]["n_nodes"] for g in all_graphs),
            "total_edges": total_edges,
            "total_items": sum(g["meta"]["n_items"] for g in all_graphs),
            "cross_doc_edges": glob_g["n_cross"],
            "node_types_total": dict(total),
        }
        json.dump(summary, open(os.path.join(args.out, "_summary.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("=" * 60)
        print(f"全量构建完成: {summary['docs']}文档 {summary['total_nodes']}节点 "
              f"{summary['total_edges']}边 {summary['total_items']}条目 "
              f"{summary['cross_doc_edges']}跨文档边")
        print(f"节点类型分布: {dict(total)}")


if __name__ == "__main__":
    main()
