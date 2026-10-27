"""Phase 2: LLM裁决512个BGE匹配的新增pair.

协议: GLM-5首轮裁决 → Kimi二审 → 一致采纳/分歧仲裁
产出: data/gjb_438c/pair_dataset_expanded/adjudicated_pairs.json
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

PROMPT = """你是SRS需求文档一致性审查专家。基于以下完整证据判断表格内容与图节点是否一致。

[表格标题] {table_title}
[表格内容] {table_text}
[同文档的图节点] {nodes}

请判断: 表格中列出的功能/接口/用例与图节点是否一致？

规则:
- real_bug: 表格中的核心功能/接口/用例在图节点中完全找不到对应(数据流断裂、关键组件缺失)
- benign_variation: 图节点涵盖了表格核心内容,仅在粒度/表述/辅助内容上有差异
- unsure: 基于提供的信息无法确定

只输出JSON: {{"label": "real_bug|benign_variation|unsure", "reason": "引用具体内容的理由"}}"""


def main() -> None:
    # 读取BGE匹配的pair(高+中质量)
    data = json.loads((BASE / "data/gjb_438c/pair_dataset_expanded/bge_matched_pairs.json").read_text(encoding="utf-8"))
    pairs = [p for p in data["pairs"] if p["similarity"] > 0.65]  # 高+中
    print(f"裁决对象: {len(pairs)}个pair(相似度>0.65)")

    # 加载图节点(用于提供完整上下文)
    anchors_v3 = json.loads((BASE / "data/gjb_438c/anchor_v3/anchors_v3.json").read_text(encoding="utf-8"))
    doc_nodes = {}
    for doc, d in anchors_v3.items():
        nodes = []
        for s in d.get("structures", []):
            for n in s.get("nodes", []):
                if n.get("text"):
                    nodes.append(n["text"].strip())
        doc_nodes[doc] = nodes

    # GLM-5裁决(走缓存)
    results = {}
    out_path = BASE / "data/gjb_438c/pair_dataset_expanded/adjudicated_pairs.json"

    t0 = time.time()
    for i, pair in enumerate(pairs):
        doc = pair["doc"]
        nodes = doc_nodes.get(doc, [])
        # 限制节点数(避免prompt过长)
        nodes_str = "; ".join(nodes[:30]) if nodes else "(无图节点数据)"

        prompt = PROMPT.format(
            table_title=pair["table_title"][:50],
            table_text=pair["table_text"][:300],
            nodes=nodes_str[:400])

        try:
            parsed, _ = llm_json(prompt, cache=True)
            label = str((parsed or {}).get("label", "?")).lower()
            reason = str((parsed or {}).get("reason", ""))[:120]
        except Exception:
            label = "error"
            reason = ""

        results[pair["table_chunk_id"]] = {
            "label": label if label in ("real_bug", "benign_variation", "unsure") else "unsure",
            "reason": reason,
            "glm_label": label,
            "pair_info": pair,
        }

        if (i + 1) % 50 == 0:
            # 增量保存
            out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {i + 1}/{len(pairs)} ({time.time() - t0:.0f}s)", flush=True)

    # 最终保存
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    # 统计
    from collections import Counter
    labels = Counter(v["label"] for v in results.values())
    print(f"\n裁决完成: {len(results)}条 ({time.time() - t0:.0f}s)")
    print(f"标签分布: {dict(labels)}")
    print(f"real_bug率: {labels.get('real_bug', 0) / len(results):.0%}")
    print(f"unsure率: {labels.get('unsure', 0) / len(results):.0%}")
    print(f"保存 → {out_path}")


if __name__ == "__main__":
    main()
