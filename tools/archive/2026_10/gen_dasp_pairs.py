r"""DASP: 分布对齐合成训练对(Distribution-Aligned Synthetic Pairs).

根解学习模型失败(R@1≈0.03):
  旧训练: (LLM为chunk生成的假设问题, image) — 训练问句分布≠评测问句分布
  DASP:   (真实评测query, LLM生成的图描述) — 训练问句分布=评测问句分布

流程:
  ① 取评测集v3的755条可解析query(user_sim+param_v2)
  ② 对每条query, LLM生成"回答该查询的图片应该包含什么内容"
     (含图内文字风格+视觉描述风格)
  ③ 构造(query_text, LLM_image_description)训练对
  ④ 用BGE编码query侧, BGE编码LLM描述侧(作为图特征代理)
  ⑤ 对比训练(InfoNCE) MLP投影头

关键差异: query侧分布与评测完全一致; 图侧用LLM描述代替真实图特征
         (分布近似——LLM描述的BGE嵌入与VLM转写的BGE嵌入同空间)

用法: python tools/gen_dasp_pairs.py [--limit 500]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

EVALSET_V3 = BASE / "data/gjb_438c/data_assets/evalset_v3.json"
OUT = BASE / "data/gjb_438c/data_assets/retrieval_train/dasp_pairs.json"
PROMPT_TMPL = (
    "你是需求文档专家。请根据以下查询，写出回答该查询的图片应包含的内容描述"
    "(50-100字，模拟图中会出现的文字标签和元素名称，GJB需求文档风格):\n{query}\n"
    "输出JSON: {{\"description\": \"...\"}}"
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()

    eval_data = json.loads(EVALSET_V3.read_text(encoding="utf-8"))
    # 只取可解析的非legacy查询(与评测分布一致)
    usable = [q for q in eval_data if q["source"] in ("user_sim", "param_v2")]
    usable = usable[:args.limit]
    print(f"评测query: {len(usable)}条(user_sim+param_v2)")

    from algorithms.common.llm_client import llm_json
    results: list[dict] = []
    n_err = 0
    for i, q in enumerate(usable):
        query = q["query"]
        # LLM生成图描述
        prompt = PROMPT_TMPL.format(query=query)
        try:
            j, _ = llm_json(prompt, cache=True, prefer="glm")
        except (RuntimeError, OSError):
            n_err += 1
            continue
        desc = ""
        if isinstance(j, dict):
            desc = str(j.get("description", "")).strip()
        if not desc or len(desc) < 10:
            n_err += 1
            continue
        # 期望图(chunk_id列表)
        exp_ids = q["expected"]["chunk_ids"]
        results.append({
            "query": query,
            "image_description": desc,
            "expected_chunk_ids": exp_ids,
            "source": "dasp",
            "query_type": q.get("query_type", ""),
        })
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(usable)} (err={n_err})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n完成: {len(results)}对 → {OUT} (err={n_err})")
    # 样例
    for r in results[:3]:
        print(f"  Q: {r['query'][:50]}")
        print(f"  D: {r['image_description'][:80]}")


if __name__ == "__main__":
    main()
