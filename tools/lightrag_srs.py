#!/usr/bin/env python3
"""LightRAG + SRS 完整接入 (复用业界开源Agentic RAG)

技术栈 (全部复用, 非自研):
- LightRAG 1.5.6 (HKU): 图+向量混合检索, naive/local/global/hybrid/mix 5种模式
  - 自动实体/关系抽取 (GLM-5.2)
  - 知识图谱构建 (NetworkXStorage) + 向量库 (NanoVectorDB)
  - 多模态支持 (VLM分析图片/表格)
- bge-small-zh-v1.5: 中文embedding
- GLM-5.2 (wanqing API): LLM/VLM

用法:
  python tools/lightrag_srs.py --index   # 构建索引(16份SRS)
  python tools/lightrag_srs.py --query "创建服务工程" --mode mix
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer

API_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
API_KEY = os.getenv("WQ_API_KEY", "")
LLM_MODEL = "kimi-k2.6"  # kimi-k2.6
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
EMBED_DIM = 512
WORKING_DIR = "data/gjb_438c/data_assets/lightrag_store"
SRS_DIR = "data/gjb_438c/dual_source"  # .html (textutil双源)
CHUNK_TOKEN_SIZE = 800
CHUNK_OVERLAP = 100

_embed_model = None


async def llm_model_func(prompt, system_prompt=None, history_messages=None, keyword_extraction=False, **kwargs):
    """GLM-5.2 via OpenAI兼容API (LightRAG官方openai_complete_if_cache复用)"""
    return await openai_complete_if_cache(
        LLM_MODEL, prompt, system_prompt=system_prompt,
        history_messages=history_messages, base_url=API_URL,
        api_key=API_KEY, **kwargs,
    )


def embedding_func(texts):
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model.encode(texts, normalize_embeddings=True)


async def init_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        llm_model_name=LLM_MODEL,
        embedding_func=EmbeddingFunc(embedding_dim=EMBED_DIM, max_token_size=8192, func=embedding_func),
        addon_params={
            "chunk_token_size": CHUNK_TOKEN_SIZE,
            "chunk_overlap_token_size": CHUNK_OVERLAP,
        },
    )
    return rag


async def index_srs(rag):
    """构建索引: 16份SRS → 切片→实体/关系抽取→图+向量"""
    print("=== 构建LightRAG索引 ===")
    total = 0
    for fname in sorted(os.listdir(SRS_DIR)):
        if not (fname.endswith(".md") or fname.endswith(".html")):
            continue
        path = os.path.join(SRS_DIR, fname)
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        print(f"  {fname}: {len(text)}字符")
        await rag.ainsert(text)
        total += 1
    print(f"✅ 索引完成: {total}份文档")


async def query_rag(rag, q, mode="mix"):
    param = QueryParam(mode=mode, top_k=20, chunk_top_k=20)
    result = await rag.aquery(q, param=param)
    print(f"\n=== 查询: {q} (mode={mode}) ===")
    print(result)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", action="store_true", help="构建索引")
    ap.add_argument("--query", help="查询文本")
    ap.add_argument("--mode", default="mix", choices=["naive", "local", "global", "hybrid", "mix"])
    args = ap.parse_args()

    async def main():
        rag = await init_rag()
        if args.index:
            await index_srs(rag)
        if args.query:
            await query_rag(rag, args.query, args.mode)

    asyncio.run(main())
