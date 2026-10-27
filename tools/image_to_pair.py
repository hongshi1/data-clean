r"""主线: 图片→Pair转化 — 利用VLM图分析(379张)生成结构化pair.

v2修复(审计P0.2):
  1. doc归属: 从img["doc"]读取(此前迭代顶层key=analyses, 全部误标为"an")
  2. 测试文档排除: 03/04/07(泄漏防护, 与synth_s1同协议)
  3. 一致对措辞去捷径: 不用"相同元素"字样, 用与不一致对同构的句式

方法(全部来自真实图片内容):
  P1: 图内元素存在性(完整列表 vs 删除一项)
  P2: 同文档同类型图交叉比对
  P3: caption声称 vs 图实际元素
  P4: Visio结构节点比对(anchors_v3, L1真值)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

TEST_DOCS = {"03", "04", "07"}  # md166泄漏防护


def _doc_id(doc_name: str) -> str:
    return str(doc_name)[:2]


def _fmt_elements(els: list[str], n: int = 6) -> str:
    return "、".join(els[:n])


def load_images(sia_path: Path) -> list[dict]:
    sia = json.loads(sia_path.read_text(encoding="utf-8"))
    analyses = sia["analyses"] if isinstance(sia, dict) and "analyses" in sia else sia
    images = []
    for img in analyses:
        analysis = img.get("analysis", {})
        elements = analysis.get("key_elements", [])
        fig_type = analysis.get("figure_type", "")
        caption = img.get("caption", [""])[0] if img.get("caption") else ""
        doc = _doc_id(img.get("doc", ""))
        if elements and len(elements) >= 2:
            images.append({
                "doc": doc, "image_path": img.get("image_path", ""),
                "fig_type": fig_type, "caption": caption,
                "elements": elements, "n_elements": len(elements),
            })
    return images


def main() -> None:
    images_all = load_images(BASE / "data/gjb_438c/data_assets/chunks/srs_image_analyses.json")
    # 泄漏防护: 排除测试文档
    images = [img for img in images_all if img["doc"] not in TEST_DOCS]
    print(f"可用图片: {len(images)}/{len(images_all)}张(排除测试文档{sorted(TEST_DOCS)})")

    # ── P1: 图内元素存在性(删除一个元素 → 不一致) ──
    p1_pairs = []
    for img in images:
        els = img["elements"]
        if len(els) < 3:
            continue
        # 先截取显示集, 再在集内做变换(保证一致对集合相等)
        shown = els[:6]
        for target_idx in range(1, min(len(shown), 4)):
            target = shown[target_idx]
            remaining = [e for e in shown if e != target]
            # 不一致对: 完整列表 vs 删除一项(同构句式)
            p1_pairs.append({
                "premise": f"该图中包含以下元素：{_fmt_elements(shown)}。",
                "hypothesis": f"该图中包含以下元素：{_fmt_elements(remaining)}。",
                "label": "inconsistent", "type": "DIAGRAM_EXTRA",
                "doc": img["doc"], "fig_type": img["fig_type"],
                "method": "P1_element_removal",
                "removed": target,
            })
            # 一致对(对称): 同一显示集内轮转(集合严格相等)
            rotated = shown[1:] + shown[:1]
            p1_pairs.append({
                "premise": f"该图中包含以下元素：{_fmt_elements(shown)}。",
                "hypothesis": f"该图中包含以下元素：{_fmt_elements(rotated)}。",
                "label": "consistent", "type": "P0_IDENTITY",
                "doc": img["doc"], "fig_type": img["fig_type"],
                "method": "P1_identity",
            })

    # ── P2: 同文档同类型图交叉(元素不在另一图中) ──
    p2_pairs = []
    by_doc_type = defaultdict(list)
    for img in images:
        by_doc_type[(img["doc"], img["fig_type"])].append(img)
    for (doc, ft), imgs in by_doc_type.items():
        if len(imgs) < 2:
            continue
        img_a, img_b = imgs[0], imgs[1]
        els_a = set(img_a["elements"])
        els_b = set(img_b["elements"])
        diff_a = els_a - els_b
        if diff_a and len(els_b) >= 2:
            shown_a = list(els_a)[:5]
            shown_b = list(els_b)[:5]
            p2_pairs.append({
                "premise": f"图A包含元素：{_fmt_elements(shown_a)}。",
                "hypothesis": f"图B包含元素：{_fmt_elements(shown_b)}。",
                "label": "inconsistent", "type": "DIAGRAM_EXTRA",
                "doc": doc, "fig_type": ft,
                "method": "P2_cross_image",
            })
            common = list(els_a & els_b)[:5]
            if len(common) >= 2:
                p2_pairs.append({
                    "premise": f"图A和图B都涉及以下元素：{_fmt_elements(common)}。",
                    "hypothesis": f"两个图均涉及元素：{_fmt_elements(common[::-1])}。",
                    "label": "consistent", "type": "P0_IDENTITY",
                    "doc": doc, "fig_type": ft,
                    "method": "P2_common_elements",
                })

    # ── P3: Caption声称 vs 实际元素 ──
    p3_pairs = []
    for img in images:
        caption = img["caption"]
        els = img["elements"]
        if not caption or not els:
            continue
        func_m = re.search(r"[\u4e00-\u9fa5]{2,8}(?=的流程图|用例图|架构图|数据流图|活动图)", caption)
        func_name = func_m.group() if func_m else ""
        if not func_name:
            continue
        in_elements = func_name in str(els)
        if in_elements:
            shown = els[:6]
            p3_pairs.append({
                "premise": f"文档图标题为「{func_name}」的{img['fig_type']}，图中所含元素包括：{_fmt_elements(shown)}。",
                "hypothesis": f"该{img['fig_type']}围绕「{func_name}」展开，涉及元素包括：{_fmt_elements(shown[::-1])}。",
                "label": "consistent", "type": "P0_IDENTITY",
                "doc": img["doc"], "fig_type": img["fig_type"],
                "method": "P3_caption_match",
            })

    # ── P4: anchors_v3的Visio节点结构pair(L1真值) ──
    p4_pairs = []
    anchors_v3 = json.loads((BASE / "data/gjb_438c/anchor_v3/anchors_v3.json").read_text(encoding="utf-8"))
    for doc_key, d in anchors_v3.items():
        doc_id = _doc_id(doc_key)
        if doc_id in TEST_DOCS:
            continue
        for s in d.get("structures", []):
            nodes = [n.get("text", "") for n in s.get("nodes", []) if n.get("text")]
            if len(nodes) < 3:
                continue
            shown = nodes[:6]
            p4_pairs.append({
                "premise": f"该Visio图中包含节点：{_fmt_elements(shown)}。",
                "hypothesis": f"该Visio图中包含节点：{_fmt_elements(shown[1:] + shown[:1])}。",
                "label": "consistent", "type": "P0_IDENTITY",
                "doc": doc_id, "method": "P4_visco_structure",
            })
            removed = shown[-1]
            remaining = shown[:-1]
            if len(remaining) >= 2:
                p4_pairs.append({
                    "premise": f"该Visio图中包含节点：{_fmt_elements(shown)}。",
                    "hypothesis": f"该Visio图中包含节点：{_fmt_elements(remaining)}。",
                    "label": "inconsistent", "type": "DIAGRAM_EXTRA",
                    "doc": doc_id, "method": "P4_node_removal",
                    "removed_node": removed,
                })

    # ── 汇总 ──
    all_pairs = p1_pairs + p2_pairs + p3_pairs + p4_pairs
    labels = Counter(p["label"] for p in all_pairs)
    methods = Counter(p["method"] for p in all_pairs)
    docs = Counter(p["doc"] for p in all_pairs)

    print(f"\n{'═' * 30}")
    print("图片→Pair转化v2(修复doc归属+防泄漏)")
    print(f"{'═' * 30}")
    print(f"总pair: {len(all_pairs)}条")
    print(f"标签: {dict(labels)}")
    print(f"方法: {dict(sorted(methods.items()))}")
    print(f"文档分布: {dict(sorted(docs.items()))}")
    assert not (docs.keys() & TEST_DOCS), "测试文档泄漏!"

    out = BASE / "data/gjb_438c/image_pairs.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"total": len(all_pairs),
                   "meta": {"excluded_docs": sorted(TEST_DOCS),
                            "fix": "doc归属从img.doc读取; 一致对去捷径措辞"},
                   "pairs": all_pairs}, f, ensure_ascii=False, indent=1)
    print(f"\n保存 → {out}")


if __name__ == "__main__":
    main()
