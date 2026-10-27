#!/usr/bin/env python3
"""VLM图片分析结果注入图谱 (多模态联合检索)

把VLM分析出的图片语义(图类型/关键元素/摘要)注入LightRAG:
- 每个图片分析 → 一个特殊chunk(带 [图] 标记)
- 图片中的实体(如"结构化数据归集")与文本图谱实体自然连接
- 实现图文联合检索: 查询"XX功能"既能召回文本也能召回相关图

用法:
  python tools/inject_image_chunks.py [--query "测试"]
"""
import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer

BASE_URL = "https://api.moonshot.cn/v1"
from ai_config import KIMI_KEY as API_KEY
LLM_MODEL = "kimi-k2.6"
WORKING_DIR = "data/gjb_438c/data_assets/lightrag_store"
IMAGE_ANALYSES = "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"

_model = None


async def llm_func(prompt, system_prompt=None, history_messages=None, keyword_extraction=False, **kwargs):
    extra = kwargs.pop("extra_body", {})
    extra["thinking"] = {"type": "disabled"}
    return await openai_complete_if_cache(
        LLM_MODEL, prompt, system_prompt=system_prompt,
        history_messages=history_messages, base_url=BASE_URL, api_key=API_KEY,
        extra_body=extra, **kwargs,
    )


async def embedding_func(texts):
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    return await asyncio.to_thread(lambda t: _model.encode(t, normalize_embeddings=True), texts)


def build_image_chunks(analyses_path=IMAGE_ANALYSES):
    """把图片分析转成chunk文本"""
    data = json.loads(open(analyses_path).read())
    chunks = []
    for a in data["analyses"]:
        ana = a.get("analysis", {})
        fig_type = ana.get("figure_type", "未知")
        elements = "、".join(ana.get("key_elements", []))
        summary = ana.get("summary", "")
        caption = a.get("caption", "")
        text = (
            f"[图片分析] 文档:{a['doc']} 图片:{a['image_path'].split('/')[-1]}\n"
            f"图类型:{fig_type} 图注:{caption}\n"
            f"关键元素:{elements}\n"
            f"内容摘要:{summary}"
        )
        chunks.append({"doc": a["doc"], "text": text, "image_path": a["image_path"]})
    return chunks


async def inject_images(rag, limit=None):
    """注入图片分析chunks"""
    chunks = build_image_chunks()
    if limit:
        chunks = chunks[:limit]
    # 按文档分组注入
    by_doc = {}
    for c in chunks:
        by_doc.setdefault(c["doc"], []).append(c)
    total = 0
    for doc, clist in sorted(by_doc.items()):
        texts = [c["text"] for c in clist]
        try:
            await rag.ainsert_custom_chunks(
                "\n".join(texts), texts, doc_id=f"img-{doc[:20]}"
            )
            total += len(texts)
            print(f"  ✓ {doc[:15]}: {len(texts)} 图片chunks")
        except Exception as e:
            print(f"  ✗ {doc[:15]}: {e}")
    print(f"✅ 注入完成: {total} 图片chunks")
    await rag.finalize_storages()


async def test_query(rag, q):
    """测试图文联合检索"""
    param = QueryParam(mode="mix", top_k=10, chunk_top_k=10)
    resp = await rag.aquery(q, param=param)
    print(f"\n=== 查询: {q} ===")
    print(resp[:500])


async def main():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_func, llm_model_name=LLM_MODEL,
        embedding_func=EmbeddingFunc(embedding_dim=512, max_token_size=8192, func=embedding_func),
        embedding_func_max_async=2, default_embedding_timeout=600,
        entity_extraction_use_json=True,
    )
    await rag.initialize_storages()
    if args.inject:
        await inject_images(rag, limit=args.limit)
    if args.query:
        await test_query(rag, args.query)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject", action="store_true", help="注入图片分析")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--query", help="测试查询")
    args = ap.parse_args()
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())
