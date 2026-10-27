# -*- coding: utf-8 -*-
"""场景解析质量验证: 语义模型 vs 表格数据交叉对账"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = "data/gjb_438c"

sm = json.load(open(f"{BASE}/anchor_v2/scene_models.json", encoding="utf-8"))
av = json.load(open(f"{BASE}/anchor_v2/anchors_v2.json", encoding="utf-8"))
vmap = json.load(open(f"{BASE}/data_assets/graph/visio_section_mapping.json", encoding="utf-8"))
uf = json.load(open(f"{BASE}/data_assets/usecase_features.json", encoding="utf-8"))

# ── 1. 用例图: 解析的usecase/actors vs usecase_features表 ──
def re_split(s):
    return [x for x in str(s).replace("，", ",").replace("、", ",").split(",") if x.strip()]


def norm_name(x):
    """名称归一: 去虚词/空白"""
    drop = ("的", "用例", "场景", "描述", "功能", " ", "\n")
    y = str(x)
    for d in drop:
        y = y.replace(d, "")
    return y


print("=" * 70)
print("1. 用例图语义 vs 用例表(usecase_features)")
uc_exact, uc_partial, uc_miss = 0, 0, 0
actor_hits, actor_total = 0, 0
samples = []
for doc, entry in sm.items():
    vm = vmap.get(doc, [])
    for i, m in enumerate(entry["models"]):
        if m.get("diagram_type") != "usecase_diagram":
            continue
        sec = (vm[i].get("matched_section") or "") if i < len(vm) else ""
        # 该章节的用例表记录
        feats = [f for f in uf if f["doc"] == doc and f["section"].startswith(sec)]
        if not feats:
            continue
        parsed_ucs = [u["name"] for u in m.get("usecases", []) if u["name"]]
        table_ucs = [f["uc_name"] for f in feats]
        # 名称匹配(归一化去虚词后子串匹配)
        matched = sum(1 for t in table_ucs
                      if any(norm_name(t) in norm_name(p) or norm_name(p) in norm_name(t)
                             or norm_name(t).split("/")[0] in norm_name(p)
                             for p in parsed_ucs))
        if matched == len(table_ucs) and table_ucs:
            uc_exact += 1
        elif matched > 0:
            uc_partial += 1
            if len(samples) < 4:
                samples.append((doc[:8], sec, [t[:12] for t in table_ucs],
                                [p[:12] for p in parsed_ucs]))
        else:
            uc_miss += 1
        # actors对比
        for f in feats:
            table_actors = [a.strip() for a in re_split(f.get("actors", ""))]
            parsed_actors = m.get("primary_actors", []) + m.get("external_systems", [])
            actor_total += len(table_actors)
            actor_hits += sum(1 for ta in table_actors
                              if any(ta in pa or pa in ta for pa in parsed_actors if pa))
print(f"  用例图-表格章节匹配: 完全匹配{uc_exact} 部分{uc_partial} 未匹配{uc_miss}")
print(f"  actors命中率: {actor_hits}/{actor_total} = {actor_hits/max(1,actor_total):.1%}")
for doc, sec, t, p in samples:
    print(f"  部分: {doc}@{sec} 表={t} 图={p}")


def re_split(s):
    return [x for x in str(s).replace("，", ",").replace("、", ",").split(",") if x.strip()]


# ── 2. 流程图: 解析的步骤数 vs sc2/sc4 pair的用例表主事件流 ──
print("=" * 70)
print("2. 流程图步骤 vs 用例表主事件流(pair_dataset)")
import glob
import csv

pair_stats = {"exact": 0, "close": 0, "far": 0}
pair_samples = []
for pd in sorted(glob.glob(f"{BASE}/pair_dataset/sc2_flowchart_usecase/*/table.csv")) + \
             sorted(glob.glob(f"{BASE}/pair_dataset/sc4_flowchart_capability/*/table.csv")):
    pair_id = pd.replace("\\", "/").split("/")[-2]
    # 该pair的锚点对应doc中哪个结构? 用pair的meta/visio_anchor的embed_index匹配
    va_path = pd.replace("table.csv", "visio_anchor.json")
    try:
        va = json.load(open(va_path, encoding="utf-8"))
    except FileNotFoundError:
        continue
    doc = va["doc"]
    # 在该doc的structures里找同embed_index
    idx = None
    for si, st in enumerate(av.get(doc, {}).get("structures", [])):
        if st.get("embed_index") == va.get("embed_index"):
            idx = si
            break
    if idx is None or doc not in sm:
        continue
    model = sm[doc]["models"][idx]
    if model.get("diagram_type") != "flowchart":
        continue
    # 表格主事件流步骤数(从CSV找步骤列)
    try:
        rows = list(csv.reader(open(pd, encoding="utf-8")))
    except Exception:
        continue
    tbl_steps = []
    for r in rows:
        for c in r:
            c = (c or "").strip()
            if c and (c[0].isdigit() and len(c) > 1 and any(
                    ch.isdigit() for ch in c[:3]) is False or True):
                pass
    # 简化: 统计含"步骤"或序号开头的单元格
    for r in rows:
        for c in r:
            c = (c or "").strip()
            if len(c) > 4 and (c.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9"))
                               and ("." in c[:4] or c[1:2].isdigit() is False)):
                tbl_steps.append(c)
    n_tbl = len(tbl_steps)
    n_fig = model.get("stats", {}).get("n_steps", 0)
    if n_tbl == 0:
        continue
    if n_fig == n_tbl:
        pair_stats["exact"] += 1
    elif abs(n_fig - n_tbl) <= 2:
        pair_stats["close"] += 1
    else:
        pair_stats["far"] += 1
        if len(pair_samples) < 4:
            pair_samples.append((pair_id, n_tbl, n_fig,
                                 [t[:10] for t in tbl_steps[:5]],
                                 [s["name"][:10] for s in model.get("steps", [])[:5]]))
print(f"  步骤数对比: 精确{pair_stats['exact']} 接近(±2){pair_stats['close']} 偏差大{pair_stats['far']}")
for pid, nt, nf, tt, ff in pair_samples:
    print(f"  偏差: {pid} 表{nt}步 vs 图{nf}步 | 表头{tt} | 图{ff}")


# ── 3. 接口图: 解析的系统/接口 vs sc3接口表 ──
print("=" * 70)
print("3. 接口图语义 vs 接口表(sc3)")
if_total, if_named = 0, 0
for pd in sorted(glob.glob(f"{BASE}/pair_dataset/sc3_interface_interface/*/table.csv")):
    pair_id = pd.replace("\\", "/").split("/")[-2]
    va_path = pd.replace("table.csv", "visio_anchor.json")
    try:
        va = json.load(open(va_path, encoding="utf-8"))
    except FileNotFoundError:
        continue
    doc = va["doc"]
    idx = None
    for si, st in enumerate(av.get(doc, {}).get("structures", [])):
        if st.get("embed_index") == va.get("embed_index"):
            idx = si
            break
    if idx is None or doc not in sm:
        continue
    model = sm[doc]["models"][idx]
    try:
        rows = list(csv.reader(open(pd, encoding="utf-8")))
    except Exception:
        continue
    tbl_ifaces = [r for r in rows if any("接口" in (c or "") for c in r)]
    if_total += 1
    parsed_ifs = [x["name"] for x in model.get("interfaces", [])]
    # 接口名匹配: 表中接口名是否出现在解析的接口点/系统里
    hits = 0
    for r in tbl_ifaces[:6]:
        for c in r:
            c = (c or "").strip()
            if len(c) > 3 and any(c in p or p in c for p in parsed_ifs if p):
                hits += 1
                break
    if parsed_ifs or hits:
        if_named += 1
        print(f"  {pair_id}: 图类型={model['_classify']['type']} "
              f"解析接口{len(parsed_ifs)}个 表接口行{len(tbl_ifaces)} 命中{hits} "
              f"样例={parsed_ifs[:2]}")
print(f"  接口图pair: {if_named}/{if_total} 有语义产出")
