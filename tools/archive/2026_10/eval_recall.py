# -*- coding: utf-8 -*-
"""召回质量评测: 三通道证据匹配(章节/表格caption/正文内容) + 分场景统计"""
import json
import re
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from algorithms.context_association.context_graph import ContextGraph

cg = ContextGraph()
qa = json.load(open(os.path.join(
    BASE, "data/gjb_438c/data_assets/srs_qa_final.json"), encoding="utf-8"))

SEC_RE = re.compile(r"(\d+\.\d+(?:\.\d+)*\s*[章节])|[章节][:：\s]*(\d+\.\d+(?:\.\d+)*)")
CAP_RE = re.compile(r"表\s*(\d+)")
TXT_RE = re.compile(r"[正文本][文]?\s*[:：]\s*(.{6,40})")


def evidence_keys(ev_str):
    """从evidence提取三类匹配键"""
    keys = {"sec": None, "cap": None, "txt": None}
    m = SEC_RE.search(ev_str)
    if m:
        keys["sec"] = (m.group(1) or m.group(2)).split()[0].rstrip("章节") or \
                      (m.group(1) or m.group(2)).replace("章节", "").strip()
    m = CAP_RE.search(ev_str)
    if m:
        keys["cap"] = m.group(1)
    m = TXT_RE.search(ev_str)
    if m:
        keys["txt"] = re.sub(r"[，。、\s]", "", m.group(1))[:12]
    return keys


def hit_check(r, keys):
    """三通道命中: 章节号 / 表格caption / 正文内容(查全文)"""
    if keys["sec"]:
        for mod in ["TXT", "TBL"]:
            for n in (r["groups"].get(mod) or []):
                s = n.get("section", "")
                if s and (s == keys["sec"] or s.startswith(keys["sec"]) or keys["sec"].startswith(s)):
                    return "sec"
    if keys["cap"]:
        for n in (r["groups"].get("TBL") or []):
            cap = n.get("caption", "") or n.get("label", "")
            m = CAP_RE.match(cap) or CAP_RE.search(cap)
            if m and m.group(1) == keys["cap"]:
                return "cap"
            if keys["cap"] in cap:
                return "cap"
    if keys["txt"]:
        st = cg.sec_texts.get(r.get("doc", ""), {})
        for n in (r["groups"].get("TXT") or []):
            prev = re.sub(r"[，。、\s]", "",
                          ((n.get("payload") or {}).get("text_preview") or "")
                          + (n.get("label") or ""))
            if keys["txt"][:8] in prev:
                return "txt"
            # 全文兜底: 该章节完整正文
            full = st.get(n.get("section", ""), "")
            if keys["txt"][:8] in re.sub(r"[，。、\s]", "", full):
                return "txt"
    return None


def doc_num_of(doc_name):
    """QA的doc全名 → 编号"""
    for num, g in cg.docs.items():
        if g["meta"]["doc"].startswith(doc_name[:6]):
            return num
    return None


def run_eval(label, sample_per_sc=12, use_doc=True):
    probes = []
    for sc in ["1", "2", "4"]:
        n = 0
        for e in qa:
            if str(e.get("scenario")) == sc and e.get("evidence") and n < sample_per_sc:
                ev = e["evidence"]
                ev_str = ev if isinstance(ev, str) else json.dumps(ev, ensure_ascii=False)
                probes.append({"q": e["question"], "sc": sc, "ev": ev_str,
                               "doc": doc_num_of(e.get("doc", ""))})
                n += 1
    stats = {"ok": 0, "no_seed": 0, "no_hit": 0, "no_key": 0}
    ch = {"sec": 0, "cap": 0, "txt": 0}
    miss = []
    for p in probes:
        keys = evidence_keys(p["ev"])
        r = cg.activate(p["q"], doc_num=(p["doc"] if use_doc else None))
        if not r.get("ok"):
            stats["no_seed"] += 1
            continue
        if not (keys["sec"] or keys["cap"] or keys["txt"]):
            stats["no_key"] += 1
            continue
        h = hit_check(r, keys)
        if h:
            stats["ok"] += 1
            ch[h] += 1
        else:
            stats["no_hit"] += 1
            miss.append((p["sc"], p["q"][:30], p["ev"][:40]))
    n = len(probes)
    eff = max(n - stats["no_seed"] - stats["no_key"], 1)
    print(f"[{label}] 样本{n} | 种子失败{stats['no_seed']} 无键{stats['no_key']} | "
          f"命中 {stats['ok']}/{eff} = {stats['ok']/eff:.0%} "
          f"(章节{ch['sec']} 表格{ch['cap']} 正文{ch['txt']})")
    return miss


if __name__ == "__main__":
    miss = run_eval("基线")
    print("\n未命中样例(前10):")
    for sc, q, ev in miss[:10]:
        print(f"  sc{sc} | {q} | ev: {ev}")
