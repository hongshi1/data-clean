r"""B2条目聚合v4: 分类型阈值+规模上限的约束聚类(消解巨分量).

v3遗留问题: 互近邻+单一阈值下巨分量3396(正文链式).
v4设计:
  ① 分类型阈值: prose-prose边0.85(正文语义分布更宽), 其余0.75
  ② 约束单连接: 边按(ID=1.0 > 引用=0.95 > 语义权重)降序处理,
     合并仅当合并后规模<=cap(条目上限, 默认20) — 巨分量被结构性封顶
  ③ 指标: 巨分量(应<=cap) / 条目带(2-20)统计 / 跨类型条目 / ID召回 /
     条目内聚度(平均边权)
用法: python tools/eval/b2_aggregation_v4.py [--cap 20] [--th-prose 0.85] [--th 0.75]
产出: results/_b2_v4.json + runs归档
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
CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
CODE_PAT = re.compile(r"[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}")
NUM_PAT = re.compile(r"^\s*[图表]\s*(\d+)\b")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=20)
    ap.add_argument("--th", type=float, default=0.75)
    ap.add_argument("--th-prose", type=float, default=0.85)
    args = ap.parse_args()

    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))

    units: list[tuple[str, str, str, str]] = []
    for c in ds["corpus"]:
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
    print(f"B2 v4: {n}单元({Counter(kinds)}), cap={args.cap}, "
          f"th={args.th}, th_prose={args.th_prose}")

    # ── 边构造(带权重) ──
    code_map: dict[str, list[int]] = defaultdict(list)
    for i, (text, *_r) in enumerate(units):
        for code in set(CODE_PAT.findall(text)):
            code_map[code].append(i)
    gold_groups = [idxs for idxs in code_map.values() if len(idxs) >= 2]
    weighted = []   # (weight, a, b)
    for idxs in gold_groups:
        for j in range(1, len(idxs)):
            weighted.append((1.0, idxs[0], idxs[j]))

    title_num: dict[tuple[str, str, str], int] = {}
    for i, (text, _o, kind, doc) in enumerate(units):
        if kind in ("image", "table"):
            m = NUM_PAT.match(text)
            if m:
                title_num[(doc, "图" if kind == "image" else "表",
                           m.group(1))] = i
    ref_pat = re.compile(r"[图表]\s*(\d+)(?![\d\.．])")
    n_cite = 0
    for i, (text, _o, kind, doc) in enumerate(units):
        if kind != "prose":
            continue
        for m in ref_pat.finditer(text):
            target = title_num.get((doc, m.group(0)[0], m.group(1)))
            if target is not None:
                weighted.append((0.95, i, target))
                n_cite += 1
    print(f"边: ID={len(gold_groups)}组, 引用={n_cite}")

    # 语义互近邻(分类型阈值)
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

    def edge_th(a: int, b: int) -> float:
        if kinds[a] == "prose" and kinds[b] == "prose":
            return args.th_prose
        return args.th

    n_sem = 0
    for a, nbrs in knn.items():
        for b, s in nbrs[:5]:
            if b <= a:
                continue
            th = edge_th(a, b)
            if s < th:
                continue
            back = {x for x, v in knn[b][:5] if v >= edge_th(b, x)}
            if a in back:
                weighted.append((s, a, b))
                n_sem += 1
    print(f"语义互近邻边: {n_sem} ({time.time()-t0:.0f}s)")

    # ── 约束单连接: 权重降序+规模上限 ──
    parent = list(range(n))
    size = [1] * n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    weighted.sort(key=lambda e: -e[0])
    merged = 0
    for w, a, b in weighted:
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        if size[ra] + size[rb] > args.cap:
            continue
        parent[rb] = ra
        size[ra] += size[rb]
        merged += 1
    comp = [find(i) for i in range(n)]
    print(f"约束合并: {merged}次")

    # ── 指标 ──
    by_comp = defaultdict(list)
    for i, c in enumerate(comp):
        by_comp[c].append(i)
    sizes = Counter(len(v) for v in by_comp.values())
    hit = total = 0
    for g in gold_groups:
        for a in g:
            for b in g:
                if a < b:
                    total += 1
                    if comp[a] == comp[b]:
                        hit += 1
    id_recall = hit / max(total, 1)
    entry_band = [idxs for idxs in by_comp.values()
                  if 2 <= len(idxs) <= args.cap]
    cross_type = sum(1 for idxs in entry_band
                     if len({kinds[i] for i in idxs}) >= 2)
    with_prose = sum(1 for idxs in entry_band
                     if any(kinds[i] == "prose" for i in idxs))
    # 条目内聚度: 条目带内平均语义边权
    edge_lookup = {(a, b): w for w, a, b in weighted}
    coh = []
    for idxs in entry_band:
        ws = [edge_lookup[(min(a, b), max(a, b))]
              for a in idxs for b in idxs if a < b
              and (min(a, b), max(a, b)) in edge_lookup]
        if ws:
            coh.append(sum(ws) / len(ws))
    print(f"\n【v4指标】分量={len(by_comp)} 最大={max(sizes)}(上限{args.cap})")
    print(f"ID召回={id_recall:.3f} | 条目带(2-{args.cap})={len(entry_band)}"
          f" 跨类型={cross_type} 含正文={with_prose}")
    print(f"条目内聚度(均值): {sum(coh)/len(coh):.3f}" if coh else "无内聚度")
    print(f"规模分布: {dict(sorted(sizes.items())[:8])}")

    # 标本: 条目带内跨类型+含正文
    specimen = None
    for c, idxs in sorted(by_comp.items(), key=lambda kv: -len(kv[1])):
        ks = {kinds[i] for i in idxs}
        if "prose" in ks and len(ks) >= 3 and 4 <= len(idxs) <= 8:
            specimen = [{"kind": kinds[i], "owner": owners[i][-16:],
                         "text": units[i][0][:60]} for i in idxs]
            break
    if specimen:
        print("\n【条目标本】")
        for s in specimen:
            print(f"  [{s['kind']:5s}|{s['owner']}] {s['text']}")

    out = {
        "protocol": (f"B2 v4约束聚类: 分类型阈值(prose {args.th_prose}/"
                     f"其他{args.th})+规模上限{args.cap}; "
                     "边优先级ID>引用>语义"),
        "metrics": {
            "n_units": n, "n_components": len(by_comp),
            "largest": max(sizes), "id_recall": round(id_recall, 4),
            "entry_band": len(entry_band), "cross_type": cross_type,
            "with_prose": with_prose,
            "cohesion_mean": round(sum(coh) / len(coh), 4) if coh else None,
            "size_dist": {str(k): v for k, v in sorted(sizes.items())[:10]},
        },
        "specimen": specimen,
    }
    outp = RESULTS / "_b2_v4.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"\n→ {outp}")

    from run_utils import open_run
    handle = open_run("b2_aggregation_v4", {
        "cap": args.cap, "th": args.th, "th_prose": args.th_prose,
        "n_units": n})
    handle.save_result(out["metrics"])
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
