#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原型demo数据生成: 从真实引擎提取五类数据 → docs/doc11/原型模板/_demo_data.json

  datasets   16份SRS数据集注册表(graph_store meta)
  graph_demo doc02上下文关联激活子图(ContextGraph.activate)
  checks     doc01/02的52项校验结果(CheckEngine.run)
  std_data   16份SRS标准数据形态(替换原型c1分类占位)
  qa_pairs   12条真实QA对(替换原型问题/答案生成演示)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from algorithms.context_association.context_graph import ContextGraph
from algorithms.consistency_check.check_engine import CheckEngine

cg = ContextGraph()
ce = CheckEngine(cg)

# ---- 1. 数据集注册表 ----
datasets = []
for num, g in sorted(cg.docs.items()):
    m = g["meta"]
    name = m["doc"].replace("需求规格说明-终稿", "").replace("需求规格说明", "")
    datasets.append({"num": num, "name": name, "nodes": m["n_nodes"],
                     "edges": m["n_edges"], "items": m["n_items"],
                     "mods": m.get("node_types", {})})

# ---- 2. 图谱demo(全部16份文档, 每份一个实体召回; 节点细粒度数据) ----
import re as _re
import glob as _glob

# 表格正文与mermaid资产(细粒度数据源)
_TABLE_BODIES = {}
for _p in _glob.glob(os.path.join(
        BASE, "data/gjb_438c/mineru_standard/*/office/*content_list.json")):
    _doc = os.path.basename(_p).replace("_content_list.json", "")
    _cl = json.load(open(_p, encoding="utf-8"))
    _m = {}
    for _it in _cl:
        if isinstance(_it, dict) and _it.get("type") == "table":
            _caps = _it.get("table_caption", [])
            if _caps:
                _m[_caps[0]] = _it.get("table_body", "")
    _TABLE_BODIES[_doc] = _m
_MERMAID = json.load(open(os.path.join(
    BASE, "data/gjb_438c/anchor_v2/mermaid_export.json"), encoding="utf-8"))
_MM_BY_DOC = {}
for _k, _v in _MERMAID.items():
    _MM_BY_DOC[(_v.get("doc", ""), _v.get("embed", ""))] = _v


def _tbl_rows(doc, caption, n_rows=3, n_cols=6):
    """从表格HTML提取前n行×n列数据(细粒度)"""
    body = _TABLE_BODIES.get(doc, {}).get(caption, "")
    if not body:
        # 前缀匹配
        for cap, b in _TABLE_BODIES.get(doc, {}).items():
            if caption[:10] and caption[:10] in cap:
                body = b
                break
    if not body:
        return []
    rows = []
    for tr in _re.findall(r"<tr[^>]*>(.*?)</tr>", body, _re.S)[:n_rows + 1]:
        cells = _re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, _re.S)[:n_cols]
        vals = [_re.sub(r"<[^>]+>", "", c).strip()[:12] for c in cells]
        if any(vals):
            rows.append(vals)
    return rows[:n_rows]


graphs = {}
for num, g in sorted(cg.docs.items()):
    doc_name = g["meta"]["doc"]
    ents = [n for n in g["nodes"] if n["type"] == "E"
            and n["payload"].get("aliases")]
    if not ents:
        continue
    alias = ents[0]["payload"]["aliases"][0]
    q = f"{alias}包含哪些功能?"
    r = cg.activate(q, doc_num=num)
    if not r.get("ok"):
        continue
    n_content = sum(len(v) for v in (r.get("groups") or {}).values())
    if n_content < 4:
        continue

    def slim_node(n, extra=None):
        d = {"id": n["id"], "type": n["type"], "label": n["label"][:24],
             "section": n.get("section", "")}
        p = n.get("payload", {})
        if n["type"] == "TXT":
            d["preview"] = (p.get("text_preview") or "")[:160]
            d["len"] = p.get("text_len", 0)
        elif n["type"] == "TBL":
            cap = p.get("caption") or ""
            d["caption"] = cap[:20]
            d["headers"] = (p.get("headers") or [])[:6]
            d["rows"] = _tbl_rows(doc_name, cap)
            d["row_count"] = p.get("row_count", 0)
        elif n["type"] == "IMG":
            d["caption"] = (p.get("caption") or "")[:20]
            d["img_type"] = p.get("img_type", "")
            # 图片资产: 拷贝到原型images/目录供前端渲染
            fign = n["id"].split(":")[2] if n["id"].count(":") >= 2 else None
            pth = p.get("path")
            if pth and fign:
                d["img"] = f"{num}_{fign}.png"
                src_path = os.path.join(BASE, "data/gjb_438c/mineru_standard",
                                        doc_name, "office", pth)
                dst_dir = os.path.join(BASE, "docs/doc11/原型模板/images")
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(dst_dir, d["img"])
                if os.path.exists(src_path) and not os.path.exists(dst):
                    import shutil
                    shutil.copy(src_path, dst)
            mk = p.get("mermaid_key")
            mv = _MERMAID.get(mk) if mk else None
            if mv:
                mm_lines = (mv.get("mermaid") or "").strip().split("\n")
                d["mermaid"] = "\n".join(mm_lines[:12])
                d["mm_nodes"] = mv.get("n_nodes", 0)
                d["mm_edges"] = mv.get("n_edges", 0)
        elif n["type"] == "SEQ":
            p2 = p or {}
            d["seq"] = (f"{p2.get('n_steps', '?')}步"
                        if p2.get("seq_type") == "anchor_chain" else "异常流")
            d["steps"] = (p2.get("steps") or [])[:6]
            d["dangling"] = (p2.get("dangling") or [])[:3]
        elif n["type"] == "KNW":
            d["rule"] = n["id"].split(":")[1] if ":" in n["id"] else ""
            d["desc"] = (p.get("description") or "")[:60]
        if extra:
            d.update(extra)
        return d

    gd = {
        "question": r["question"],
        "doc": r.get("doc", ""),
        "center": slim_node(r["center"], {"score": r["center"].get("score", 1),
                                          "alias": (r["center"].get("payload", {}).get("aliases") or [""])[0]}),
        "related": [{"name": (x.get("aliases") or [x.get("id_str", "")])[0],
                     "id_str": x.get("id_str", ""), "rel": x.get("rel", ""),
                     "score": round(x.get("score", 0), 2)}
                    for x in (r.get("related_entities") or [])[:6]],
        "groups": {},
    }
    for mod, lst in (r.get("groups") or {}).items():
        gd["groups"][mod] = [
            slim_node(n, {"score": round(n.get("score", 0), 2),
                          "via": (n.get("via_label") or "")[:10]})
            for n in lst[:6]]
    gd["stats"] = r.get("stats", {})
    graphs[num] = gd

graph_demo = graphs.get("02")  # 兼容旧字段

# ---- 3. 校验结果demo(真实跑) ----
checks = {}
for num in ["01", "02"]:
    rc = ce.run(num)
    if rc.get("ok"):
        checks[num] = {
            "ran_at": rc["ran_at"], "summary": rc["summary"],
            "categories": rc["categories"],
            "items": [{"id": i["id"], "category": i["category"], "name": i["name"],
                       "status": i["status"], "n": i["n_findings"], "mode": i["mode"],
                       "modality": i["modality"],
                       "findings": [{"desc": f["desc"], "section": f["section"],
                                     "evidence": f["evidence"]}
                                    for f in i["findings"][:4]]}
                      for i in rc["items"]],
        }

# ---- 4. 标准数据(16份SRS, 替换c1占位) ----
std_data = []
import glob as _glob
for p in sorted(_glob.glob(os.path.join(
        BASE, "data/gjb_438c/mineru_standard/*/office/*content_list.json"))):
    doc = os.path.basename(p).replace("_content_list.json", "")
    cl = json.load(open(p, encoding="utf-8"))
    texts = [i.get("text", "") for i in cl
             if isinstance(i, dict) and i.get("type") == "text"
             and len(i.get("text", "").strip()) > 30]
    first = texts[2] if len(texts) > 2 else (texts[0] if texts else "")
    fname = doc + ".docx"
    std_data.append({"cat": "c1", "src": fname,
                     "txt": first.strip()[:80],
                     "len": sum(len(t) for t in texts)})

# ---- 5. 真实QA对(12条, 替换问题/答案生成演示) ----
qa = json.load(open(os.path.join(
    BASE, "data/gjb_438c/data_assets/srs_qa_final.json"), encoding="utf-8"))
qa_pairs = []
picked = {"sc1": 0, "sc2": 0, "sc4": 0}
want = {"T2_table_factual", "T5_text_understanding", "T7_consistency"}
for e in qa:
    sc = f"sc{e.get('scenario')}"
    if sc in picked and picked[sc] < 4 and e.get("type") in want \
            and len(e.get("answer", "")) > 20:
        qa_pairs.append({
            "cat": "c1", "q": e["question"][:80], "a": e["answer"][:120],
            "ev": str(e.get("evidence", ""))[:60],
            "doc": (e.get("doc") or "").replace("需求规格说明-终稿", "")[:14],
            "typ": e.get("type", ""), "sc": sc, "tid": e.get("type", "")})
        picked[sc] += 1
    if all(v >= 4 for v in picked.values()):
        break

out = {"datasets": datasets, "graph_demo": graph_demo, "graphs": graphs,
       "checks": checks, "std_data": std_data, "qa_pairs": qa_pairs}
path = os.path.join(BASE, "docs/doc11/原型模板/_demo_data.json")
json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"OK → {path}")
print(f"  datasets={len(datasets)} graph_demo={'OK' if graph_demo else 'FAIL'}"
      f" checks={list(checks.keys())} std_data={len(std_data)} qa_pairs={len(qa_pairs)}")
if graph_demo:
    print("  center:", graph_demo["center"]["label"][:20],
          "| related:", len(graph_demo["related"]),
          "| groups:", {k: len(v) for k, v in graph_demo["groups"].items() if v})
