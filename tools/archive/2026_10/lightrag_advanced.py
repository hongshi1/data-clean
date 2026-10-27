#!/usr/bin/env python3
"""LightRAG高级接入: 多模态 + 结构化chunks + 5模式查询

复用技术 (全部业界开源/官方API, 非自研):
1. LightRAG 1.5.6: 图+向量混合索引, 实体/关系自动抽取, 5种查询模式
2. GraphRAG思想: 实体-关系图 (NetworkX) + 向量库 (NanoVectorDB) 双通道
3. bge-small-zh-v1.5: 中文语义embedding
4. GLM-5.2: LLM抽取/回答; kimi-k2.6: VLM多模态分析(图片)

高级特性:
- 多模态: VLM分析SRS图片(用例图/接口图) → 图片语义进入图谱
- 结构化chunks: 保留doc/section/type(章节上下文)
- 查询: naive(纯向量) / local(实体邻域) / global(社区摘要) / hybrid / mix(图+向量)
"""
import argparse
import asyncio
import base64
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer

API_URL = "https://api.z.ai/api/paas/v4/chat/completions"
from ai_config import KIMI_KEY as API_KEY
LLM_MODEL = "kimi-k2.6"
VLM_URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY as VLM_KEY
VLM_MODEL = "kimi-k2.6"
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
EMBED_DIM = 512
WORKING_DIR = "data/gjb_438c/data_assets/lightrag_store"
CHUNKS_PATH = "data/gjb_438c/data_assets/chunks/srs_chunks.json"

_embed_model = None


async def llm_model_func(prompt, system_prompt=None, history_messages=None, keyword_extraction=False, **kwargs):
    """GLM-5.2 LLM (LightRAG官方openai adapter)"""
    return await openai_complete_if_cache(
        LLM_MODEL, prompt, system_prompt=system_prompt,
        history_messages=history_messages, base_url=API_URL,
        api_key=API_KEY, **kwargs,
    )


async def vlm_model_func(prompt, image_bytes, system_prompt=None, history_messages=None, **kwargs):
    """kimi-k2.6 VLM: 分析SRS图片 (moonshot API)"""
    import httpx
    b64 = base64.b64encode(image_bytes).decode()
    messages = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": prompt},
    ]}]
    resp = httpx.post(VLM_URL, headers={"Authorization": f"Bearer {VLM_KEY}"},
                      json={"model": VLM_MODEL, "messages": messages,
                            "max_tokens": 1500}, timeout=180)
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def embedding_func(texts):
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model.encode(texts, normalize_embeddings=True)


async def init_rag(enable_vlm=False):
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        llm_model_name=LLM_MODEL,
        embedding_func=EmbeddingFunc(embedding_dim=EMBED_DIM, max_token_size=8192, func=embedding_func),
        addon_params={
            "chunk_token_size": 800,
            "chunk_overlap_token_size": 100,
            "entity_extract_max_gleaning": 2,
            "enable_llm_cache": True,
        },
    )
    if enable_vlm:
        rag.llm_vlm_func = vlm_model_func
        rag.vlm_process_enable = True
        print("✅ VLM多模态已启用 (kimi-k2.6)")
    await rag.initialize_storages()
    return rag


def load_srs_chunks():
    """加载结构化chunks: 按doc分组, 返回[(doc, full_text, chunks)]"""
    chunks = json.loads(open(CHUNKS_PATH, encoding="utf-8").read())
    docs = {}
    for c in chunks:
        docs.setdefault(c["doc"], []).append(c)
    print(f"chunks总: {len(chunks)}, 文档: {len(docs)}")
    return docs


async def index_custom_chunks(rag):
    """用结构化chunks插入(保留doc/section/type)"""
    docs = load_srs_chunks()
    for doc, clist in sorted(docs.items()):
        full_text = "\n".join(c["text"] for c in clist)
        texts = [c["text"] for c in clist]
        await rag.ainsert_custom_chunks(full_text, texts, doc_id=doc)
        print(f"  ✓ {doc}: {len(clist)} chunks")
    print("✅ 结构化chunks索引完成")


async def query_modes(rag, q):
    """5种查询模式对比"""
    for mode in ["naive", "local", "global", "hybrid", "mix"]:
        try:
            param = QueryParam(mode=mode, top_k=15, chunk_top_k=15)
            resp = await rag.aquery(q, param=param)
            print(f"\n{'='*20} mode={mode} {'='*20}")
            print(resp[:300])
        except Exception as e:
            print(f"\n❌ mode={mode}: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--vlm", action="store_true", help="启用VLM多模态")
    ap.add_argument("--query", help="查询")
    ap.add_argument("--mode", default="mix", choices=["naive", "local", "global", "hybrid", "mix", "all"])
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    async def main():
        rag = await init_rag(enable_vlm=args.vlm)
        if args.index:
            await index_custom_chunks(rag)
        if args.query:
            if args.mode == "all":
                await query_modes(rag, args.query)
            else:
                param = QueryParam(mode=args.mode, top_k=15, chunk_top_k=15)
                resp = await rag.aquery(args.query, param=param)
                print(resp)

    asyncio.run(main())
