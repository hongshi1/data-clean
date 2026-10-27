r"""B2条目聚合v3: 正文扩展+四类边(引用语法边解锁).

新增(相对v2原型):
  ① 正文节点: srs_chunks的1343个长正文块(>30字符)进入单元池
  ② E2引用语法边: 正文"图N/表N"引用 ↔ 同文档同编号的图/表归属
     (366处图引用+867处表引用, 编号体系已双向验证)
  ③ 语义互近邻覆盖正文单元
消融: 仅旧三边(ID+mutual) vs +引用边 vs +正文全部

用法: python tools/eval/b2_aggregation_v3.py [--th 0.75] [--k 5]
产出: results/_b2_v3.json + runs归档
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
CHUNKS = (BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json")
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
CODE_PAT = re.compile(r"[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}")
NUM_PAT = re.compile(r"^\s*[图表]\s*(\d+)\b")


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--th", type=float, default=0.75)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    corpus = ds["corpus"]

    # ── 节点池: 表行+图元素+正文块 ──
    units: list[tuple[str, str, str, str]] = []   # (text, owner, kind, doc)
    for c in corpus:
        for u in c["units"]:
            if u:
                units.append((u, c["chunk_id"], c["type"], c["doc"]))
    prose = [c for c in chunks if c["type"] == "text"
             and len(c["text"].strip()) > 30]
    for c in prose:
        units.append((c["text"].strip(), c["chunk_id"], "prose", c["doc"]))
    n = len(units)
    owners = [u[1] for u in units]
    kinds = [u[2] for u in units]
    print(f"B2 v3: {n}单元 "
          f"({Counter(kinds)})")

    # ── E1: ID共指(含正文) ──
    code_map: dict[str, list[int]] = defaultdict(list)
    for i, (text, *_rest) in enumerate(units):
        for code in set(CODE_PAT.findall(text)):
            code_map[code].append(i)
    gold_groups = [idxs for idxs in code_map.values() if len(idxs) >= 2]
    id_edges = []
    for idxs in gold_groups:
        for j in range(1, len(idxs)):
            id_edges.append((idxs[0], idxs[j]))
    print(f"E1 ID共指: {len(gold_groups)}组/{len(id_edges)}边")

    # ── E2: 引用语法边(正文→图/表, 同文档同编号) ──
    title_num: dict[tuple[str, str, str], int] = {}
    for i, (text, owner, kind, doc) in enumerate(units):
        if kind in ("image", "table"):
            m = NUM_PAT.match(text)
            if m:
                title_num[(doc, "图" if kind == "image" else "表",
                           m.group(1))] = i
    ref_pat = re.compile(r"[图表]\s*(\d+)(?![\d\.．])")
    cite_edges = []
    for i, (text, owner, kind, doc) in enumerate(units):
        if kind != "prose":
            continue
        for m in ref_pat.finditer(text):
            key = (doc, m.group(0)[0], m.group(1))
            target = title_num.get(key)
            if target is not None:
                cite_edges.append((i, target))
    print(f"E2 引用语法: {len(cite_edges)}边 (图+表引用合并)")

    # ── E3: 互近邻语义(覆盖含正文全部单元) ──
    t0 = time.time()
    from algorithms.common import bge_local
    enc = bge_local.BgeLocal(cache_path=None)
    enc.ensure()
    vecs = enc.embed([u[0] for u in units])
    import torch
    U = torch.as_tensor(
        np.stack([np.asarray(vecs.get(u[0], [0.0] * 1024),
                             dtype=np.float32) for u in units]),
        dtype=torch.float16).cuda()
    U = U / torch.clamp(U.norm(dim=-1, keepdim=True), min=1e-8)
    owner_ids = {o: i for i, o in enumerate(dict.fromkeys(owners))}
    owner_idx = torch.as_tensor([owner_ids[o] for o in owners],
                                device="cuda", dtype=torch.long)
    knn: dict[int, list] = {}
    block = 2048
    for i0 in range(0, n, block):
        sims = U[i0:i0 + block] @ U.T
        sims.scatter_(1, (i0 + torch.arange(
            min(block, n - i0), device="cuda")).unsqueeze(1), -1.0)
        sims[owner_idx[None, :] == owner_idx[i0:i0 + block, None]] = -1.0
        vals, idxs = torch.topk(sims, 10, dim=1)
        for r in range(idxs.shape[0]):
            knn[i0 + r] = [(int(idxs[r, c]), float(vals[r, c]))
                           for c in range(10) if float(vals[r, c]) > 0]
    mutual = []
    for a, nbrs in knn.items():
        top_a = {b for b, s in nbrs[:args.k] if s >= args.th}
        for b in top_a:
            if b > a and a in {x for x, s in knn[b][:args.k]
                               if s >= args.th}:
                mutual.append((a, b))
    print(f"E3 互近邻(k={args.k}, th={args.th:.2f}): {len(mutual)}边 "
          f"({time.time()-t0:.0f}s)")

    # ── 消融组合 ──
    def components(edges):
        uf = UnionFind(n)
        for e in edges:
            uf.union(e[0], e[1])
        return [uf.find(i) for i in range(n)]

    def id_recall(comp):
        hit = total = 0
        for g in gold_groups:
            for a in g:
                for b in g:
                    if a < b:
                        total += 1
                        if comp[a] == comp[b]:
                            hit += 1
        return hit / max(total, 1)

    report = {}
    combos = [
        ("旧三边(ID+语义)", id_edges + mutual),
        ("+引用边", id_edges + mutual + cite_edges),
    ]
    for label, edges in combos:
        comp = components(edges)
        sizes = Counter(comp)
        rec = id_recall(comp)
        # 跨类型分量统计(条目应跨类型)
        by_comp = defaultdict(list)
        for i, c in enumerate(comp):
            by_comp[c].append(i)
        cross_type = sum(1 for idxs in by_comp.values()
                         if len({kinds[i] for i in idxs}) >= 2
                         and len(idxs) >= 2)
        prose_linked = sum(1 for idxs in by_comp.values()
                           if any(kinds[i] == "prose" for i in idxs)
                           and len(idxs) >= 2)
        report[label] = {
            "edges": len(edges), "n_components": len(sizes),
            "largest": max(sizes.values()), "singletons": sizes.get(1, 0),
            "id_recall": round(rec, 4),
            "cross_type_components": cross_type,
            "components_with_prose": prose_linked,
        }
        r = report[label]
        print(f"\n[{label}] 边={r['edges']} 分量={r['n_components']} "
              f"最大={r['largest']} 孤点={r['singletons']}")
        print(f"  ID召回={r['id_recall']:.3f} 跨类型分量="
              f"{r['cross_type_components']} 含正文分量={r['components_with_prose']}")

    # ── 标本: 含正文+跨类型的条目 ──
    comp = components(id_edges + mutual + cite_edges)
    by_comp = defaultdict(list)
    for i, c in enumerate(comp):
        by_comp[c].append(i)
    specimen = None
    for c, idxs in sorted(by_comp.items(), key=lambda kv: -len(kv[1])):
        ks = {kinds[i] for i in idxs}
        if ("prose" in ks and len(ks) >= 3 and 3 <= len(idxs) <= 10):
            specimen = [{
                "kind": kinds[i], "owner": owners[i][-18:],
                "text": units[i][0][:70]} for i in idxs]
            break
    if specimen:
        print("\n【条目标本(正文+表+图跨类型)】")
        for s in specimen:
            print(f"  [{s['kind']:5s}|{s['owner']}] {s['text']}")

    out = {
        "protocol": (f"B2 v3: {n}单元(含正文{len(prose)}); "
                     f"E1=ID共指, E2=引用语法({len(cite_edges)}边), "
                     f"E3=互近邻(k={args.k}, th={args.th})"),
        "ablation": report, "specimen": specimen,
        "cite_edges_sample": [
            {"prose": units[a][0][:50], "target": units[b][0][:50]}
            for a, b in cite_edges[:10]],
    }
    outp = RESULTS / "_b2_v3.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"\n→ {outp}")

    from run_utils import open_run
    handle = open_run("b2_aggregation_v3", {
        "n_units": n, "n_prose": len(prose), "k": args.k, "th": args.th,
        "edges": ["ID共指", "引用语法", "互近邻语义"]})
    handle.save_result({"ablation": report})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
