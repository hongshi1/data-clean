"""L1标注: 对372个表侧复用pair执行LLM裁决(基于原始SRS表格内容,非模板化文本).

数据源: l1_table_reuse_pairs.json中的372对(MinerU解析的真实表格+同章节image)
标注: GLM-5 CoT裁决(基于表格内容+图节点判断一致性)
产出: l1_adjudicated.json(带标签的pair,可用于训练)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

from algorithms.common.llm_client import llm_json  # noqa: E402

PROMPT = """你是SRS需求文档一致性审查专家。基于以下真实表格内容和图节点内容判断一致性。

[表格标题] {title}
[表格内容] {rows}
[该文档中所有图的节点] {nodes}

请判断: 表格中列出的功能/接口/用例是否在图节点中有对应？

规则:
- real_bug: 表格中的核心功能/接口名称在图节点中完全找不到(核心内容缺失)
- benign_variation: 表格中的核心内容在图节点中有对应,仅在粒度/表述上可能有差异
- unsure: 无法判定

只输出JSON: {{"label": "real_bug|benign_variation|unsure", "reason": "引用具体节点或表格内容的一句话理由"}}"""


def main() -> None:
    data = json.loads((BASE / "data/gjb_438c/pair_dataset_items/l1_table_reuse_pairs.json").read_text(encoding="utf-8"))
    pairs = data["pairs"]
    print(f"待标注: {len(pairs)}对")

    # 加载图节点(anchors_v3)
    anchors_v3 = json.loads((BASE / "data/gjb_438c/anchor_v3/anchors_v3.json").read_text(encoding="utf-8"))
    doc_nodes = {}
    for doc, d in anchors_v3.items():
        nodes = []
        for s in d.get("structures", []):
            for n in s.get("nodes", []):
                if n.get("text"):
                    nodes.append(n["text"].strip())
        doc_nodes[doc] = nodes

    out_path = BASE / "data/gjb_438c/pair_dataset_items/l1_adjudicated.json"
    results = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}

    t0 = time.time()
    todo = [p for p in pairs if p["chunk_id"] not in results]
    print(f"实际待处理: {len(todo)}对")

    for i, pair in enumerate(todo):
        chunk_id = pair["chunk_id"]
        rows_str = "\n".join(pair.get("table_rows", [])[:5])[:400]
        nodes = doc_nodes.get(pair.get("doc_full", ""), [])

        prompt = PROMPT.format(
            title=pair.get("table_title", "")[:50],
            rows=rows_str,
            image_sections=str(pair.get("image_sections", ""))[:50],
            doc_full=pair.get("doc_full", "")[:30])

        try:
            parsed, _ = llm_json(prompt, cache=True)
            label = str((parsed or {}).get("label", "?")).lower()
            reason = str((parsed or {}).get("reason", ""))[:120]
        except Exception:
            label, reason = "unsure", ""

        results[chunk_id] = {
            "label": label if label in ("real_bug", "benign_variation", "unsure") else "unsure",
            "reason": reason,
            "pair_info": pair,
        }

        if (i + 1) % 20 == 0:
            out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {i + 1}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)

    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    labels = Counter(v["label"] for v in results.values())
    print(f"\n完成: {len(results)}条 ({time.time() - t0:.0f}s)")
    print(f"标签: {dict(labels)}")


if __name__ == "__main__":
    main()
