r"""B2条目聚合原型: ID共指+kNN语义边 → 连通分量 → 结构化gold评估.

边设计(v1原型):
  E1 需求ID共指: 同一需求代码(XX-XX-XX模式)出现的单元互连
     (195组/582单元 — 结构化gold的种子)
  E2 kNN语义: 每单元的跨表top-5最相似单元(排除同表, BGE余弦)
评估gold代理: ID共指组(同代码=同条目, 定义性真值)
指标:
  - ID组召回: 同代码单元对落在同连通分量的比例
  - 分量规模分布 / 巨型分量检测
  - 边组合消融: 仅ID / 仅kNN / ID+kNN
用法: python tools/eval/b2_aggregation_prototype.py [--k 5] [--save-edges]
产出: results/_b2_prototype.json + runs归档
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
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
CODE_PAT = re.compile(r"[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}")


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
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--save-edges", action="store_true")
    args = ap.parse_args()

    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    corpus = ds["corpus"]
    units = []          # (text, owner)
    for c in corpus:
        for u in c["units"]:
            if u:
                units.append((u, c["chunk_id"]))
    n = len(units)
    owners = [u[1] for u in units]
    print(f"B2聚合原型: {n}单元, {len(set(owners))}归属")

    # ── E1: ID共指边 + gold组 ──
    code_map: dict[str, list[int]] = defaultdict(list)
    for i, (text, _) in enumerate(units):
        for code in set(CODE_PAT.findall(text)):
            code_map[code].append(i)
    gold_groups = [idxs for idxs in code_map.values() if len(idxs) >= 2]
    id_edges = []
    for idxs in gold_groups:
        for j in range(1, len(idxs)):
            id_edges.append((idxs[0], idxs[j]))
    print(f"E1 ID共指: {len(gold_groups)}组, {len(id_edges)}条边, "
          f"覆盖{sum(len(g) for g in gold_groups)}单元")

    # ── E2: 互近邻语义边(GPU分块topk, 排除同归属, 双向+阈值过滤) ──
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
    # top-K邻接表(供mutual判定)
    knn = {}
    block = 2048
    for i0 in range(0, n, block):
        sims = U[i0:i0 + block] @ U.T
        sims.scatter_(1, (i0 + torch.arange(
            min(block, n - i0), device="cuda")).unsqueeze(1), -1.0)
        mask = owner_idx[None, :] == owner_idx[i0:i0 + block, None]
        sims[mask] = -1.0
        vals, idxs = torch.topk(sims, 10, dim=1)  # 取10供阈值扫描
        for r in range(idxs.shape[0]):
            a = i0 + r
            knn[a] = [(int(idxs[r, c]), float(vals[r, c]))
                      for c in range(10) if float(vals[r, c]) > 0]

    def mutual_edges(th: float, k: int) -> list:
        """互近邻+阈值: (a,b)双向在对方top-k内且cos>=th."""
        edges = []
        for a, nbrs in knn.items():
            top_a = {b for b, s in nbrs[:k] if s >= th}
            for b in top_a:
                if b > a and a in {x for x, s in knn[b][:k] if s >= th}:
                    s_ab = next(s for x, s in knn[a] if x == b)
                    edges.append((a, b, s_ab))
        return edges

    print(f"E2邻接计算完成({time.time()-t0:.0f}s)")
    knn_edge_cache = {}
    for th in (0.70, 0.75, 0.80, 0.85):
        knn_edge_cache[th] = mutual_edges(th, args.k)
        print(f"  mutual(k={args.k}, th={th:.2f}): "
              f"{len(knn_edge_cache[th])}条边")

    # ── 连通分量(三种边组合消融) ──
    def components(edges):
        uf = UnionFind(n)
        for e in edges:
            uf.union(e[0], e[1])
        comp = [uf.find(i) for i in range(n)]
        sizes = Counter(comp)
        return comp, sizes

    def id_recall(comp):
        """同代码单元对落在同分量的比例(gold代理召回)."""
        hit = total = 0
        for g in gold_groups:
            for a in g:
                for b in g:
                    if a < b:
                        total += 1
                        if comp[a] == comp[b]:
                            hit += 1
        return hit / max(total, 1), total

    report = {}
    combos = [("仅ID边", id_edges, None)]
    for th in (0.70, 0.75, 0.80, 0.85):
        edges = knn_edge_cache[th]
        combos.append((f"mutual@{th:.2f}",
                        [(a, b) for a, b, _ in edges], th))
        combos.append((f"ID+mutual@{th:.2f}",
                        id_edges + [(a, b) for a, b, _ in edges], th))
    for label, edges, th in combos:
        comp, sizes = components(edges)
        rec, npairs = id_recall(comp)
        size_dist = Counter(sizes.values())
        big = max(sizes.values())
        key = label
        report[key] = {
            "n_components": len(sizes),
            "id_group_recall": round(rec, 4),
            "id_pairs": npairs,
            "largest_component": big,
            "size_dist_top": dict(sorted(size_dist.items())[:6]),
            "singletons": size_dist.get(1, 0),
        }
        r = report[key]
        print(f"\n[{label}] 边={len(edges)} 分量数={r['n_components']} "
              f"最大={big} 孤点={r['singletons']}")
        print(f"  ID组召回={rec:.3f} (gold对{npairs})")
        print(f"  规模分布: {r['size_dist_top']}")

    # 标本: ID+mutual@0.75下取一个跨表多单元分量
    best_th = 0.75
    comp, _ = components(
        id_edges + [(a, b) for a, b, _ in knn_edge_cache[best_th]])
    by_comp = defaultdict(list)
    for i, c in enumerate(comp):
        by_comp[c].append(i)
    spec = None
    for c, idxs in by_comp.items():
        if 3 <= len(idxs) <= 8 and len({owners[i] for i in idxs}) >= 2:
            has_code = any(CODE_PAT.search(units[i][0]) for i in idxs)
            if has_code:
                spec = idxs
                break
    specimen = None
    if spec:
        specimen = [{
            "owner": owners[i][-20:], "text": units[i][0][:80]
        } for i in spec]
        print(f"\n【聚合标本(ID+mutual@{best_th}跨表分量)】")
        for s in specimen:
            print(f"  [{s['owner']}] {s['text']}")

    out = {
        "protocol": (f"B2聚合原型: {n}单元; E1=ID共指({len(id_edges)}边/"
                     f"{len(gold_groups)}组gold), E2=互近邻语义"
                     f"(k={args.k}, 阈值扫描)"),
        "edges": {"id": len(id_edges),
                  "mutual_counts": {str(th): len(knn_edge_cache[th])
                                    for th in knn_edge_cache}},
        "ablation": report,
        "specimen": specimen,
    }
    if args.save_edges:
        th = 0.75
        out["knn_edges_sample"] = [
            {"a": units[a][0][:40], "b": units[b][0][:40], "cos": round(s, 3)}
            for a, b, s in knn_edge_cache[th][:200]]
    outp = RESULTS / "_b2_prototype.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"\n→ {outp}")

    from run_utils import open_run
    handle = open_run("b2_aggregation_prototype", {
        "n_units": n, "k": args.k,
        "edges": ["ID共指", "kNN跨表语义"]})
    handle.save_result({"ablation": report})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
