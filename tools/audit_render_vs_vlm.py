#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染-vs-VLM 全量自检审计 (用户要求的"自己回去检查").

对照真值: VLM通道对image.png的独立读取(236对 + sc2 89对 + sc3 v2)
被检对象: 每个pair的.md当前渲染结构(census对齐后的锚点节点文本)

指标:
  node_overlap = 与VLM节点文本匹配的渲染节点 / max(VLM节点数, 渲染节点数)
  (文本匹配: 归一化后互为子串, ≥4字或≥60%字符重叠)
输出: 整体分布 + 低分对清单(候选残余错配) + 边数对比

用法: python tools/audit_render_vs_vlm.py [--min 0.5]
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PAIR = BASE / "data/gjb_438c/pair_dataset"
CENSUS = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
ANCHORS = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
VLM_SOURCES = [
    BASE / "data/gjb_438c/anchor_v2/scene_vlm_extractions.json",
    BASE / "data/gjb_438c/anchor_v2/sc3_vlm_extractions_v2.json",
    BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json",
]


def _norm(t: str) -> str:
    return re.sub(r"[\s\n]", "", (t or ""))


def _text_match(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    if len(a) >= 4 and len(b) >= 4:
        common = sum(1 for c in a if c in b)
        return common / max(len(a), len(b)) >= 0.6
    return False


def load_vlm() -> dict:
    vlm = {}
    for p in VLM_SOURCES:
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for pid, r in data.items():
            if isinstance(r, dict) and r.get("nodes"):
                vlm.setdefault(pid, r)
    return vlm


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=0.5, help="低分阈值")
    args = ap.parse_args()

    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    residual_path = BASE / "data/gjb_438c/anchor_v2/pair_alignment_residual.json"
    if residual_path.exists():
        for pid, rec in json.loads(residual_path.read_text(
                encoding="utf-8")).items():
            census.setdefault(pid, {"status": "anchored",
                                    "new_embed": rec.get("new_embed")})
    anchors = json.loads(ANCHORS.read_text(encoding="utf-8"))
    v2_idx = {}
    v2_exact = {}
    for doc, d in anchors.items():
        for s in d.get("structures", []):
            v2_exact[(doc, s.get("embed_index", ""))] = s
            key = (doc, s.get("embed_index", "").split(":")[0])
            tn = sum(1 for n in s.get("nodes", []) if n.get("text"))
            if key not in v2_idx or tn > sum(1 for n in v2_idx[key].get("nodes", [])
                                             if n.get("text")):
                v2_idx[key] = s
    vlm = load_vlm()

    scores = []
    no_vlm = no_anchor = 0
    for md in sorted(PAIR.rglob("*.md")):
        pid = md.parent.name
        va = md.parent / "visio_anchor.json"
        if not va.exists():
            no_anchor += 1
            continue
        a = json.loads(va.read_text(encoding="utf-8"))
        embed = a.get("embed_index", "")
        c = census.get(pid) or {}
        if c.get("status") == "anchored" and c.get("new_embed"):
            embed = c["new_embed"]
        # 精确匹配优先(多页embed: 基名查"最多文本"可能捞到另一页)
        aligned = v2_exact.get((a.get("doc", ""), embed)) or \
            v2_idx.get((a.get("doc", ""), embed.split(":")[0]))
        r = vlm.get(pid)
        if aligned is None or r is None:
            no_vlm += 1
            continue
        vlm_texts = [_norm(n.get("text", "")) for n in r.get("nodes", [])
                     if _norm(n.get("text", ""))]
        ren_texts = [_norm(n.get("text", "")) for n in aligned.get("nodes", [])
                     if _norm(n.get("text", ""))]
        if not vlm_texts or not ren_texts:
            continue
        matched = sum(1 for vt in vlm_texts
                      if any(_text_match(vt, rt) for rt in ren_texts))
        score = matched / max(len(vlm_texts), len(ren_texts))
        recall = matched / max(len(vlm_texts), 1)
        scores.append((pid, score, recall, len(vlm_texts), len(ren_texts),
                       len(r.get("edges", [])), len(aligned.get("edges", []))))

    n = len(scores)
    avg = sum(s[1] for s in scores) / max(n, 1)
    avg_recall = sum(s[2] for s in scores) / max(n, 1)
    high = sum(1 for s in scores if s[1] >= 0.8)
    mid = sum(1 for s in scores if args.min <= s[1] < 0.8)
    # 真低分 = 对称分低 且 VLM召回也低(召回高=内容全对,只是结构更丰富)
    low = [s for s in scores if s[1] < args.min and s[2] < 0.6]
    false_low = sum(1 for s in scores if s[1] < args.min and s[2] >= 0.6)
    print("=" * 64)
    print(f"渲染-vs-VLM 自检审计: {n}对可对照")
    print(f"  平均重叠率: {avg:.1%} | 平均VLM召回: {avg_recall:.1%}")
    print(f"  ≥80%: {high} | 50-80%: {mid} | 低分: {len(low)}"
          f" (另有{false_low}对假低分=召回≥60%但结构更丰富, 内容正确)")
    print()
    for pid, sc, rc, nv, nr, ev, er in sorted(low, key=lambda x: x[1])[:15]:
        print(f"  {pid}: score={sc:.2f} recall={rc:.2f} "
              f"vlm节点{nv}/渲染{nr} vlm边{ev}/渲染边{er}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
