#!/usr/bin/env python3
"""端到端多模态QA对生成 (含真实图片)

从SRS文档中采样图文对:
- 每份文档: 图 + 图注 + 图中实体(VLM分析) + 所在章节文本上下文
- kimi-k2.6生成QA对(问题涉及图片内容, 答案引用图片+文本证据)

输出格式(端到端评测集):
{
  "id": "mm_0001",
  "doc": "01数据获取转换分系统...",
  "image_path": ".../fig_003.png",       ← 真实图片路径
  "figure_type": "用例图",
  "caption": "图 3 数据获取用例图",
  "question": "数据获取用例图中, 参与者是谁? 他可以进行哪些操作?",
  "answer": "图中参与者是数据保障人员, 可进行结构化/半结构化/非结构化/流式数据归集与引接操作...",
  "evidence": {"text": "...", "section": "3.2.1"},  ← 文本证据(可选)
  "difficulty": "medium"
}
"""
import argparse
import asyncio
import base64
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from ai_config import KIMI_KEY as API_KEY
URL = "https://api.moonshot.cn/v1/chat/completions"
MODEL = "kimi-k2.6"
IMAGE_ANALYSES = "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"
CHUNKS_PATH = "data/gjb_438c/data_assets/chunks/srs_chunks.json"
OUT_PATH = "data/gjb_438c/data_assets/multimodal_qa_evalset.json"

QA_PROMPT = """你是SRS软件需求文档专家。基于以下SRS图片及其分析信息, 生成1个端到端问答对。

图片信息:
- 图注: {caption}
- 图类型: {figure_type}
- 图中关键元素: {elements}
- 内容摘要: {summary}

要求:
1. 问题必须**只能通过看图才能回答**(涉及图的元素/结构/参与者关系), 不能仅凭文本回答
2. 答案要具体, 引用图中的元素名称
3. 输出JSON: {{"question": "...", "answer": "..."}}
4. 只输出JSON, 不要其他文字"""


def load_images():
    data = json.loads(open(IMAGE_ANALYSES, encoding="utf-8").read())
    # 过滤有完整分析的
    imgs = [a for a in data["analyses"] if a.get("analysis", {}).get("key_elements")]
    return imgs


def load_chunks():
    return json.loads(open(CHUNKS_PATH, encoding="utf-8").read())


def find_text_context(chunks, doc, section=None):
    """找图片所在章节的文本上下文(作为可选证据)"""
    doc_chunks = [c for c in chunks if c["doc"] == doc and c["type"] == "text"]
    if section:
        # 找同章节或父章节
        for c in doc_chunks:
            if c["section"] == section:
                return c["text"][:300]
    if doc_chunks:
        return doc_chunks[len(doc_chunks) // 2]["text"][:300]
    return ""


async def gen_qa(img, chunks, include_image=True):
    """生成QA对(可选真实图片输入)"""
    ana = img["analysis"]
    caption = " ".join(img.get("caption", [])) if isinstance(img.get("caption"), list) else str(img.get("caption", ""))
    elements = "、".join(ana.get("key_elements", [])[:10])
    summary = ana.get("summary", "")

    prompt = QA_PROMPT.format(
        caption=caption, figure_type=ana.get("figure_type", ""),
        elements=elements, summary=summary)

    messages = []
    if include_image and os.path.exists(img["image_path"]):
        b64 = base64.b64encode(open(img["image_path"], "rb").read()).decode()
        messages.append({"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": prompt},
        ]})
    else:
        messages.append({"role": "user", "content": prompt})

    try:
        r = httpx.post(URL, headers={"Authorization": f"Bearer {API_KEY}"},
                       json={"model": MODEL, "thinking": {"type": "disabled"},
                             "messages": messages, "max_tokens": 400,
                             "response_format": {"type": "json_object"}},
                       timeout=180)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "")
            try:
                qa = json.loads(content)
                return qa.get("question", ""), qa.get("answer", "")
            except json.JSONDecodeError:
                return content[:100], content[:100]
    except Exception as e:
        print(f"  ⚠ {e}")
    return "", ""


async def main(n=50, seed=42, include_image=True):
    imgs = load_images()
    chunks = load_chunks()
    random.seed(seed)
    sampled = random.sample(imgs, min(n, len(imgs)))
    print(f"采样图片: {len(sampled)}张 (of {len(imgs)})")

    results = []
    for i, img in enumerate(sampled):
        q, a = await gen_qa(img, chunks, include_image=include_image)
        if q and a:
            rec = {
                "id": f"mm_{i:04d}",
                "doc": img["doc"],
                "image_path": img["image_path"],
                "figure_type": img["analysis"].get("figure_type", ""),
                "caption": img.get("caption", ""),
                "question": q,
                "answer": a,
                "difficulty": "medium",
            }
            results.append(rec)
            print(f"[{i+1}/{len(sampled)}] {img['doc'][:10]} {os.path.basename(img['image_path'])} → {q[:40]}...")
        else:
            print(f"[{i+1}/{len(sampled)}] ✗ 生成失败")
        if (i + 1) % 10 == 0:
            json.dump(results, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    json.dump(results, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n✅ 多模态QA对完成: {len(results)}条 → {OUT_PATH}")
    # 校验图片存在性
    missing = [r for r in results if not os.path.exists(r["image_path"])]
    print(f"图片存在性校验: {len(results)-len(missing)}/{len(results)} 图片存在")
    if missing:
        print(f"  缺失: {[m['image_path'] for m in missing[:3]]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-image", action="store_true", help="不给LLM看真实图片(仅分析文本)")
    args = ap.parse_args()
    asyncio.run(main(n=args.n, seed=args.seed, include_image=not args.no_image))
