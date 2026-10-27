#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pair_dataset 全量 .md 档案生成

为366对配对数据各生成 {pair_id}.md 档案:
  - 元信息(meta.json) → frontmatter表格
  - 原始图片 → ![](image.png) 引用
  - Mermaid结构图 → 代码块(born-digital导出, 经embed_index对齐)
  - 表格 → markdown表格渲染(来自table.csv)
  - 正文 → text.txt原样

输出: data/gjb_438c/pair_dataset/{scene}/{pair_id}/{pair_id}.md
用法: python tools/build_pair_md.py [--scene sc4_flowchart_capability]
"""
import csv
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIR_ROOT = os.path.join(BASE, "data/gjb_438c/pair_dataset")


def load(rel):
    p = os.path.join(BASE, rel)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def build_mermaid_index():
    """(doc全名, embed_index) → mermaid导出条目"""
    idx = {}
    exp = load("data/gjb_438c/anchor_v2/mermaid_export.json")
    for key, v in exp.items():
        idx[(v.get("doc", ""), v.get("embed", ""))] = v
    return idx


def build_census_index():
    """pair_id → 对齐记录: census(M14, 315对) ∪ 残余VLM匹配(realign产出)."""
    merged = load("data/gjb_438c/anchor_v2/scene_drift_census.json")
    residual = load("data/gjb_438c/anchor_v2/pair_alignment_residual.json")
    for pid, rec in residual.items():
        if pid not in merged:
            merged[pid] = {
                "status": "anchored",
                "new_embed": rec.get("new_embed"),
                "old_embed": rec.get("old_embed"),
                "align_score": rec.get("align_score"),
                "method": rec.get("method", "vlm_text_match"),
            }
    return merged


def build_mismatch_flags():
    """pair_id → 真残余错配标记(全文档无结构能匹配图片, 需人工复核)."""
    return load("data/gjb_438c/anchor_v2/pair_mismatch_flags.json")


def build_v2_anchor_index():
    """(doc, embed)索引: 精确(全名, 多页embed安全) + 基名(最多文本, 兜底)."""
    data = load("data/gjb_438c/anchor_v2/anchors_v2.json")
    exact, base = {}, {}
    for doc, d in data.items():
        for s in d.get("structures", []):
            exact[(doc, s.get("embed_index", ""))] = s
            key = (doc, s.get("embed_index", "").split(":")[0])
            tn = sum(1 for n in s.get("nodes", []) if n.get("text"))
            if key not in base or tn > sum(1 for n in base[key].get("nodes", [])
                                           if n.get("text")):
                base[key] = s
    return exact, base


def csv_to_md(csv_path):
    if not os.path.exists(csv_path):
        return "(无表格数据)"
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
    except Exception:
        return "(表格读取失败)"
    if not rows:
        return "(空表格)"
    # 过滤超宽表(截断到前8列)
    rows = [r[:8] for r in rows]
    out = ["| " + " | ".join(c.strip().replace("\n", " ")[:20] or " " for c in rows[0]) + " |",
           "|" + "---|" * len(rows[0])]
    for r in rows[1:]:
        out.append("| " + " | ".join(c.strip().replace("\n", " ")[:20] or " " for c in r) + " |")
    return "\n".join(out)


def _emit_structure_block(lines, mm, aligned, anchor):
    """单个结构的完整投影块(来源/图例/plantuml/mermaid/DOT/悬空注记)."""
    if not mm:
        return
    dtype = mm.get("diagram_type", "flowchart")
    lines.append(f"*来源: born-digital导出({dtype}, "
                 f"{mm.get('n_nodes')}节点/{mm.get('n_edges')}边)*")
    if mm.get("type_refined"):
        lines.append("*类型经几何启发式精化(Master类型识别失败的图, "
                     "投影层推断, canonical锚点不变)*")
    lines.append("")
    if mm.get("plantuml"):
        if dtype == "usecase":
            lines.append("*用例图以PlantUML渲染(UML母语): 小人=参与者 | 椭圆=用例 | "
                         "矩形框=系统边界 | 实线=关联 | 虚线=include/extend*")
        else:
            lines.append("*状态图以PlantUML渲染(UML母语): [*]=起止 | 圆角框=状态 | "
                         "箭头标签=迁移事件*")
        lines.append("")
        lines.append("```plantuml")
        lines.append(mm.get("plantuml", "").rstrip())
        lines.append("```")
        lines.append("")
        lines.append("<details><summary>Mermaid兼容投影(通用md渲染器可显示)</summary>")
        lines.append("")
        lines.append("```mermaid")
        lines.append(mm.get("mermaid", "").rstrip())
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    else:
        if dtype == "usecase":
            lines.append("*用例图UML约定: 👤=参与者 | 椭圆=用例 | 子图框=系统边界 | "
                         "实线无箭头=关联 | 虚线=include/extend*")
            lines.append("")
        lines.append("```mermaid")
        lines.append(mm.get("mermaid", "").rstrip())
        lines.append("```")
    if mm.get("dot"):
        lines.append("")
        lines.append("<details><summary>DOT源码(完整语义, "
                     "graphviz可渲染)</summary>")
        lines.append("")
        lines.append("```dot")
        lines.append(mm.get("dot", "").rstrip())
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    # 悬空端点: 恢复边(带证据) vs 未恢复(诚实警示)
    dangle = max(
        mm.get("dangling_ends") or 0,
        ((aligned or {}).get("meta") or {}).get("dangling_ends", 0),
        (anchor.get("meta") or {}).get("dangling_ends", 0),
    )
    n_rec = mm.get("n_recovered") or 0
    if n_rec:
        lines.append("")
        lines.append(f"*锚点Connect重建存在{dangle}个悬空连线端点, "
                     f"已几何恢复{n_rec}条边(连线自由端吸附最近语义节点, "
                     "每条带距离证据, via=dangling_snap; "
                     "canonical锚点不变)*")
    elif dangle:
        lines.append("")
        lines.append(f"*⚠ 锚点Connect重建存在{dangle}个悬空连线端点"
                     "(线端粘在无文本形状上被语义过滤跳过), "
                     "图示边数可能少于原图——渲染只呈现锚点事实, 不编造边; "
                     "独立证据可对照VLM通道提取(scene_vlm_extractions.json)*")


def build_pair_md(pair_dir, mermaid_idx, census, v2_anchor, flags=None,
                  composites=None):
    v2_exact, v2_base = v2_anchor
    flags = flags or {}
    composites = composites or {}
    pid = os.path.basename(pair_dir)
    meta = {}
    mp = os.path.join(pair_dir, "meta.json")
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding="utf-8"))
    doc = meta.get("doc", "")

    lines = []
    lines.append(f"# {pid} 数据对档案")
    lines.append("")
    lines.append("| 字段 | 值 |")
    lines.append("|---|---|")
    for k in ["pair_id", "scene", "doc", "section", "image_caption", "table_caption"]:
        if meta.get(k):
            lines.append(f"| {k} | {str(meta[k])[:60]} |")
    lines.append("")

    # 图片
    img = os.path.join(pair_dir, "image.png")
    if os.path.exists(img):
        lines.append("## 原始图片")
        lines.append("")
        cap = meta.get("image_caption", "")
        lines.append(f"![{cap}]({'image.png'})")
        lines.append(f"*{cap}*" if cap else "")
        lines.append("")

    # 结构图(born-digital导出; usecase主投影=PlantUML, 其余=Mermaid)
    # 结构选择: census重对齐(M14 VLM桥, 117对修对但从未接入) > pair的旧embed
    anchor = {}
    ap = os.path.join(pair_dir, "visio_anchor.json")
    if os.path.exists(ap):
        anchor = json.load(open(ap, encoding="utf-8"))
    embed = anchor.get("embed_index", "")
    c_rec = census.get(pid) or {}
    realigned = False
    if (c_rec.get("status") == "anchored" and c_rec.get("new_embed")
            and c_rec.get("new_embed") != embed):
        embed = c_rec["new_embed"]
        realigned = True
    comp = composites.get(pid)
    lines.append("## 结构图")
    lines.append("")
    if realigned and not comp:
        src = ("VLM文本匹配" if c_rec.get("method") == "vlm_text_match"
               else "census")
        lines.append(f"*⚠ 结构经{src}重对齐: 旧锚点({c_rec.get('old_embed', '')}"
                     f")与图片不符, 已切换到与image.png内容一致的锚点"
                     f"({embed}, align_score={c_rec.get('align_score')})*")
        lines.append("")
    flag = flags.get(pid)
    if flag:
        lines.append(f"*⚠ 该对锚点与图片内容匹配度低(VLM召回仅"
                     f"{flag.get('best_recall', 0):.0%}, 全文档最佳结构亦不匹配)"
                     "——图片可能为复合图或非Visio图, 结构仅供参考, 需人工复核*")
        lines.append("")
    if comp and len(comp.get("embeds", [])) >= 2:
        # 复合图: image.png由多个Visio结构拼成 → 逐组成部分渲染
        embeds = comp["embeds"]
        lines.append(f"*该图为复合图: image.png由{len(embeds)}个Visio结构组成"
                     f"(贪心集覆盖并集召回{comp.get('union_recall', 0):.0%}, "
                     "VLM文本匹配判定)*")
        lines.append("")
        for i, emb in enumerate(embeds, 1):
            mm_i = mermaid_idx.get((doc, emb))
            aligned_i = (v2_exact.get((doc, emb)) or
                         v2_base.get((doc, emb.split(":")[0])))
            lines.append(f"### 组成部分 {i}/{len(embeds)} ({emb})")
            lines.append("")
            _emit_structure_block(lines, mm_i, aligned_i, anchor)
            lines.append("")
        mm = mermaid_idx.get((doc, embeds[0]))
        aligned = (v2_exact.get((doc, embeds[0])) or
                   v2_base.get((doc, embeds[0].split(":")[0])))
    else:
        mm = mermaid_idx.get((doc, embed))
        # 对齐后的锚点结构(节点表/悬空信息用同一来源; 精确匹配优先防多页歧义)
        aligned = (v2_exact.get((doc, embed)) or
                   v2_base.get((doc, embed.split(":")[0]))) if embed else None
        _emit_structure_block(lines, mm, aligned, anchor)
    if not mm and not comp:
        if anchor:
            lines.append("*该对有Visio锚点但无结构导出*")
        else:
            lines.append("*该对无Visio锚点(非Visio图, 无born-digital导出)*")
    lines.append("")

    # 锚点结构摘要(与结构图同源: 对齐后结构优先)
    node_src = aligned or anchor
    if node_src:
        nodes = node_src.get("nodes", [])
        lines.append("### 锚点节点结构")
        lines.append("")
        if nodes:
            lines.append("| # | 文本 | 类型 |")
            lines.append("|---|---|---|")
            for i, n in enumerate(nodes[:15]):
                lines.append(f"| {i+1} | {str(n.get('text', ''))[:24] or ' '} | {n.get('type', '')} |")
            if len(nodes) > 15:
                lines.append(f"| … | 共{len(nodes)}个节点 | |")
        lines.append("")

    # 表格
    lines.append("## 表格内容")
    lines.append("")
    lines.append(csv_to_md(os.path.join(pair_dir, "table.csv")))
    lines.append("")

    # 正文
    tp = os.path.join(pair_dir, "text.txt")
    if os.path.exists(tp):
        lines.append("## 正文")
        lines.append("")
        text = open(tp, encoding="utf-8").read().strip()
        lines.append(text[:2000] if text else "(无正文)")
        lines.append("")

    out_path = os.path.join(pair_dir, f"{pid}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path, bool(mm)


def build_composites():
    """pair_id → 复合图记录(一图多Visio结构, 贪心集覆盖判定)."""
    return load("data/gjb_438c/anchor_v2/pair_composite.json")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", help="只处理指定场景目录")
    args = ap.parse_args()

    mermaid_idx = build_mermaid_index()
    census = build_census_index()
    v2_anchor = build_v2_anchor_index()
    flags = build_mismatch_flags()
    composites = build_composites()
    pairs = sorted(glob.glob(os.path.join(PAIR_ROOT, "*", "*", "meta.json")))
    if args.scene:
        pairs = [p for p in pairs if args.scene in p]
    n_ok = n_mm = n_realign = n_comp = 0
    for mp in pairs:
        pair_dir = os.path.dirname(mp)
        pid = os.path.basename(pair_dir)
        va_p = os.path.join(pair_dir, "visio_anchor.json")
        c = census.get(pid) or {}
        if (c.get("status") == "anchored" and c.get("new_embed")
                and os.path.exists(va_p)):
            old = json.load(open(va_p, encoding="utf-8")).get("embed_index", "")
            if c.get("new_embed") != old:
                n_realign += 1
        if pid in composites:
            n_comp += 1
        out, has_mm = build_pair_md(pair_dir, mermaid_idx, census, v2_anchor,
                                    flags, composites)
        n_ok += 1
        n_mm += 1 if has_mm else 0
    print(f"完成: {n_ok}对 → .md档案, 其中{n_mm}对含结构图 ({n_mm/max(n_ok,1):.0%})")
    print(f"census重对齐接入: {n_realign}对 | 复合图渲染: {n_comp}对 | "
          f"人工复核标记: {len(flags)}对")


if __name__ == "__main__":
    main()
