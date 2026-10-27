#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""残余错配对重对齐 (audit_render_vs_vlm揪出的<census未覆盖低分对).

方法(=M2.5 VLM桥同款, 离线复用已有VLM提取):
  对每个低分且无census记录的pair: 用VLM读图的节点文本对同文档全部
  anchor结构打分(文本重叠率), 最优结构若显著优于当前(score差≥0.3
  且best≥0.5)则重对齐 — 阈值保护防止VLM欠读时误伤正确的丰富锚点.

输出: data/gjb_438c/anchor_v2/pair_alignment_residual.json
  {pid: {old_embed, new_embed, align_score, method: "vlm_text_match"}}
用法: python tools/realign_residual_pairs.py [--min 0.5]
"""
import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from audit_render_vs_vlm import _text_match, load_vlm  # noqa: E402

PAIR = BASE / "data/gjb_438c/pair_dataset"
CENSUS = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
ANCHORS = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
OUT = BASE / "data/gjb_438c/anchor_v2/pair_alignment_residual.json"
FLAG_OUT = BASE / "data/gjb_438c/anchor_v2/pair_mismatch_flags.json"
COMP_OUT = BASE / "data/gjb_438c/anchor_v2/pair_composite.json"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=0.5,
                    help="保留(未用, 阈值硬编码在判据中, 兼容CLI)")
    ap.parse_args()

    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    anchors = json.loads(ANCHORS.read_text(encoding="utf-8"))
    vlm = load_vlm()

    def structure_texts(s):
        return [n.get("text", "") for n in s.get("nodes", [])
                if (n.get("text") or "").strip()]

    def overlap(vlm_texts, s):
        """对称重叠率(审计口径, 分母=max) — 仅供报告."""
        if not vlm_texts:
            return 0.0
        matched = sum(1 for vt in vlm_texts
                      if any(_text_match(vt, rt) for rt in structure_texts(s)))
        return matched / max(len(vlm_texts), len(structure_texts(s)))

    def vlm_recall(vlm_texts, s):
        """VLM召回率(命中/VLM节点数) — 重对齐主判据.

        对称分数会惩罚结构丰富度(3_016: 6/6全命中但分母15 → 0.4);
        召回率专注"图片里的内容是否都在这个结构里", 且天然保护
        VLM欠读的正确锚点(5_001: 当前召回1.0不会被换走).
        """
        if not vlm_texts:
            return 0.0
        matched = sum(1 for vt in vlm_texts
                      if any(_text_match(vt, rt) for rt in structure_texts(s)))
        return matched / len(vlm_texts)

    result = {}
    n_checked = n_realign = 0
    for md in sorted(PAIR.rglob("*.md")):
        pid = md.parent.name
        va = md.parent / "visio_anchor.json"
        if not va.exists():
            continue
        c = census.get(pid)
        if c and c.get("status") == "anchored":
            continue                      # census已覆盖
        r = vlm.get(pid)
        if not r:
            continue
        a = json.loads(va.read_text(encoding="utf-8"))
        doc = a.get("doc", "")
        vlm_texts = [n.get("text", "") for n in r.get("nodes", [])
                     if (n.get("text") or "").strip()]
        if not vlm_texts:
            continue
        n_checked += 1
        cur_embed = a.get("embed_index", "")
        cur_struct = None
        best = (0.0, None, "")
        for s in anchors.get(doc, {}).get("structures", []):
            sc = vlm_recall(vlm_texts, s)
            if s["embed_index"] == cur_embed:
                cur_struct = s
            if sc > best[0]:
                best = (sc, s, s["embed_index"])
        cur_recall = vlm_recall(vlm_texts, cur_struct) if cur_struct else 0.0
        if (best[1] is not None and best[2] != cur_embed
                and best[0] >= 0.6 and best[0] - cur_recall >= 0.3):
            result[pid] = {
                "old_embed": cur_embed,
                "new_embed": best[2],
                "align_score": round(best[0], 3),
                "cur_recall": round(cur_recall, 3),
                "method": "vlm_text_match",
            }
            n_realign += 1
            print(f"  [realign] {pid}: recall {cur_recall:.2f} -> "
                  f"{best[0]:.2f} ({cur_embed} -> {best[2]})")

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    # 真残余标记: 同文档没有任何结构能较好匹配图片(最佳召回<0.6)
    # → 写入flags供.md诚实警示(1_031/1_028类: 图片可能是复合图/非Visio图)
    flags = {}
    for md in sorted(PAIR.rglob("*.md")):
        pid = md.parent.name
        va = md.parent / "visio_anchor.json"
        if not va.exists() or vlm.get(pid) is None:
            continue
        if pid in result:
            continue                      # 已重对齐
        r = vlm[pid]
        a = json.loads(va.read_text(encoding="utf-8"))
        vlm_texts = [n.get("text", "") for n in r.get("nodes", [])
                     if (n.get("text") or "").strip()]
        if not vlm_texts:
            continue
        best_r, best_embed = 0.0, ""
        for s in anchors.get(a.get("doc", ""), {}).get("structures", []):
            sc = vlm_recall(vlm_texts, s)
            if sc > best_r:
                best_r, best_embed = sc, s["embed_index"]
        if best_r < 0.6:
            flags[pid] = {"best_recall": round(best_r, 2),
                          "best_embed": best_embed,
                          "vlm_nodes": len(vlm_texts)}

    # ── 复合图检测: 贪心集覆盖(≤3结构)并集召回≥0.7 → 一图多结构 ──
    # (flags里的对也要检测 — 复合是其修复路径; 命中后从flags移除)
    composites = {}
    for md in sorted(PAIR.rglob("*.md")):
        pid = md.parent.name
        if pid in result:
            continue
        r = vlm.get(pid)
        va_p = md.parent / "visio_anchor.json"
        if not r or not va_p.exists():
            continue
        a = json.loads(va_p.read_text(encoding="utf-8"))
        vlm_texts = [n.get("text", "") for n in r.get("nodes", [])
                     if (n.get("text") or "").strip()]
        if len(vlm_texts) < 3:
            continue
        unmatched = set(range(len(vlm_texts)))
        chosen = []
        while unmatched and len(chosen) < 3:
            best = (0, None)
            for s in anchors.get(a.get("doc", ""), {}).get("structures", []):
                st = [n.get("text", "") for n in s.get("nodes", [])
                      if (n.get("text") or "").strip()]
                hits = sum(1 for i in unmatched
                           if any(_text_match(vlm_texts[i], rt) for rt in st))
                if hits > best[0]:
                    best = (hits, s)
            if best[0] == 0:
                break
            chosen.append(best[1]["embed_index"])
            st = [n.get("text", "") for n in best[1].get("nodes", [])
                  if (n.get("text") or "").strip()]
            unmatched = {i for i in unmatched
                         if not any(_text_match(vlm_texts[i], rt) for rt in st)}
        union_recall = 1 - len(unmatched) / max(len(vlm_texts), 1)
        # 复合判据: ≥2个结构 且 并集召回≥0.7
        if len(chosen) >= 2 and union_recall >= 0.7:
            composites[pid] = {"embeds": chosen,
                               "union_recall": round(union_recall, 2),
                               "method": "greedy_set_cover"}
            print(f"  [composite] {pid}: {chosen} 并集召回={union_recall:.0%}")
    COMP_OUT.write_text(json.dumps(composites, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    # 复合修复的对不再是"错配" → 从flags移除后写flags
    flags = {k: v for k, v in flags.items() if k not in composites}
    FLAG_OUT.write_text(json.dumps(flags, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"残余重对齐: {n_realign}/{n_checked}个无census对 → {OUT}")
    print(f"真残余标记(最佳召回<0.6且非复合, 需人工复核): {len(flags)}对 → {FLAG_OUT}")
    print(f"复合图检测: {len(composites)}对 → {COMP_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
