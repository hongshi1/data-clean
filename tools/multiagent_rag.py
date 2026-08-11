#!/usr/bin/env python3
"""多Agent RAG管线: LightRAG引擎 + 多路召回 + 重排 + 融合

架构 (多Agent协同):
┌─────────────────────────────────────────────────────┐
│  Ingestion Agents (16并行):                          │
│    文档Agent_i → 切片 → 实体抽取(GLM) → 图谱+向量    │
├─────────────────────────────────────────────────────┤
│  Retrieval Agents (并行多路召回):                    │
│    Agent-向量:  bge-zh 语义召回 chunks               │
│    Agent-图谱:  实体邻域展开 (local)                 │
│    Agent-全局:  社区摘要 (global)                    │
│    Agent-混合:  图+向量融合 (mix)                    │
├─────────────────────────────────────────────────────┤
│  Rerank Agent:  Cross-encoder 重排 (bge-reranker)   │
├─────────────────────────────────────────────────────┤
│  Synthesis Agent: GLM-5.2 综合回答                   │
└─────────────────────────────────────────────────────┘

复用: LightRAG(图+向量双通道) + bge-zh(向量) + bge-reranker(重排) + GLM-5.2(抽取/综合)
"""
import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functools import partial

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer, CrossEncoder

# ── API配置 ──────────────────────────────────────────────
BASE_URL = "https://api.moonshot.cn/v1"
API_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
LLM_MODEL = "kimi-k2.6"
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
RERANK_MODEL = "data/models/bge-reranker-v2-m3"
EMBED_DIM = 512
WORKING_DIR = "data/gjb_438c/data_assets/lightrag_store"
SRS_DIR = "data/gjb_438c/dual_source"
CHUNKS_PATH = "data/gjb_438c/data_assets/chunks/srs_chunks.json"

# ── 全局单例(避免worker重复加载) ─────────────────────────
_embed_model = None
_rerank_model = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def get_rerank_model():
    global _rerank_model
    if _rerank_model is None:
        # 本地加载(用transformers, 支持safetensors)
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        _tok = AutoTokenizer.from_pretrained(RERANK_MODEL)
        _model = AutoModelForSequenceClassification.from_pretrained(RERANK_MODEL)
        import torch
        _rerank_model = (_tok, _model, torch)
    return _rerank_model


def embedding_func_sync(texts):
    return get_embed_model().encode(texts, normalize_embeddings=True)


async def embedding_func(texts):
    return await asyncio.to_thread(embedding_func_sync, texts)


async def llm_func(prompt, system_prompt=None, history_messages=None, keyword_extraction=False, **kwargs):
    # 禁用thinking模式(加速10x) + JSON结构化输出
    extra = kwargs.pop("extra_body", {})
    extra["thinking"] = {"type": "disabled"}
    return await openai_complete_if_cache(
        LLM_MODEL, prompt, system_prompt=system_prompt,
        history_messages=history_messages, base_url=BASE_URL, api_key=API_KEY,
        extra_body=extra, **kwargs,
    )


def create_rag(working_dir=None):
    # 中文SRS领域实体类型(替换默认英文类型, 提升抽取质量)
    entity_guidance = """使用以下类型对每个实体分类。若无合适类型, 使用`其他`。

- 软件功能: 系统提供的功能/操作/服务(如创建服务工程、数据采集)
- 需求编号: 需求标识符(如PZXQ-GN-FWKFZC-CJFWGC)
- 接口: 系统接口(如数据获取接口、统一访问接口)
- 数据项: 数据/参数/字段(如工程名称、文件大小、波特率)
- 硬件设备: 物理设备(如服务器、终端、采集设备)
- 软件系统: 软件系统/子系统(如服务集成框架、数据获取分系统)
- 单位: 度量单位(如MB、ms、Mbps)"""
    return LightRAG(
        working_dir=working_dir or WORKING_DIR,
        llm_model_func=llm_func,
        llm_model_name=LLM_MODEL,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMBED_DIM, max_token_size=8192, func=embedding_func,
        ),
        embedding_func_max_async=2,          # 并发限制(避免MPS争抢)
        default_embedding_timeout=600,       # 10分钟(embedding慢于默认60s)
        entity_extraction_use_json=True,     # JSON结构化输出(更稳定)
        addon_params={
            "chunk_token_size": 800,
            "chunk_overlap_token_size": 100,
            "entity_extract_max_gleaning": 2,
            "enable_llm_cache": True,
            "entity_types_guidance": entity_guidance,
        },
    )


# ── Ingestion Agents: 16文档并行索引 ─────────────────────
async def index_doc_agent(rag, doc_name, clist, semaphore):
    """文档Agent: 用结构化chunks索引(绕过内置chunking死锁)"""
    async with semaphore:
        try:
            full_text = "\n".join(c["text"] for c in clist)
            texts = [c["text"] for c in clist]
            await rag.ainsert_custom_chunks(full_text, texts, doc_id=doc_name)
            print(f"  ✓ {doc_name}: {len(clist)} chunks")
            return doc_name, True
        except Exception as e:
            print(f"  ✗ {doc_name}: {e}")
            return doc_name, False


async def index_all(rag, limit=None):
    """多Agent并行索引结构化chunks"""
    import json as _json
    chunks = _json.loads(open(CHUNKS_PATH).read())
    docs = {}
    for c in chunks:
        docs.setdefault(c["doc"], []).append(c)
    print(f"chunks总: {len(chunks)}, 文档: {len(docs)}")
    if limit:
        docs = dict(list(docs.items())[:limit])
    semaphore = asyncio.Semaphore(1)  # LightRAG pipeline单飞, 串行
    tasks = [index_doc_agent(rag, d, cl, semaphore) for d, cl in sorted(docs.items())]
    results = await asyncio.gather(*tasks)
    ok = sum(1 for _, s in results if s)
    print(f"✅ 索引完成: {ok}/{len(results)} 文档")
    # 确保所有存储落盘(向量库/图谱)
    await rag.finalize_storages()
    print("✅ 存储已finalize(落盘)")


# ── Retrieval Agents: 多路并行召回 ──────────────────────
async def retrieve_agent_vector(rag, q, top_k=15):
    """Agent-向量: 纯语义向量召回"""
    try:
        param = QueryParam(mode="naive", top_k=top_k, chunk_top_k=top_k)
        return await rag.aquery(q, param=param)
    except Exception as e:
        return f"[vector fail] {e}"


async def retrieve_agent_graph(rag, q, top_k=15):
    """Agent-图谱: 实体邻域展开"""
    try:
        param = QueryParam(mode="local", top_k=top_k, chunk_top_k=top_k)
        return await rag.aquery(q, param=param)
    except Exception as e:
        return f"[graph fail] {e}"


async def retrieve_agent_mix(rag, q, top_k=15):
    """Agent-混合: 图+向量融合"""
    try:
        param = QueryParam(mode="mix", top_k=top_k, chunk_top_k=top_k)
        return await rag.aquery(q, param=param)
    except Exception as e:
        return f"[mix fail] {e}"


# ── Rerank Agent: 交叉编码器重排 ─────────────────────────
def rerank_agent(query, candidates, top_k=8):
    """重排Agent: bge-reranker 对候选取精"""
    if not candidates:
        return []
    tok, model, torch = get_rerank_model()
    pairs = [(query, c[:512]) for c in candidates]
    inputs = tok(pairs, padding=True, truncation=True, max_length=512, return_tensors='pt')
    with torch.no_grad():
        scores = model(**inputs).logits.view(-1).sigmoid()
    ranked = sorted(zip(candidates, scores.tolist()), key=lambda x: x[1], reverse=True)
    print(f"  重排得分: {[round(s, 3) for _, s in ranked[:top_k]]}")
    return [c for c, s in ranked[:top_k]]


# ── Synthesis Agent: 融合回答 ────────────────────────────
async def synthesize_agent(query, contexts):
    """综合Agent: 多路证据融合为回答"""
    if not contexts:
        return "未检索到相关信息"
    evidence = "\n\n---\n\n".join(contexts[:5])
    prompt = f"""你是SRS需求分析专家。基于以下检索到的SRS文档证据, 回答用户问题。
要求: 1) 只使用证据中的信息; 2) 标注信息来源章节; 3) 证据不足时说明。

问题: {query}

检索证据:
{evidence}"""
    return await llm_func(prompt)


# ── 多Agent查询主流程 ───────────────────────────────────
async def multi_agent_query(rag, q, mode="multi"):
    """多Agent查询: 多路召回 → 重排 → 融合"""
    if mode == "multi":
        # 并行3路召回
        results = await asyncio.gather(
            retrieve_agent_vector(rag, q),
            retrieve_agent_graph(rag, q),
            retrieve_agent_mix(rag, q),
        )
        # 提取候选(去掉失败标记)
        candidates = []
        for r in results:
            if r and not r.startswith("[") and r != "None":
                candidates.append(r)
        print(f"  多路召回: 向量[{len(results[0] or '')}字] 图谱[{len(results[1] or '')}字] 混合[{len(results[2] or '')}字]")
        # 重排
        top = rerank_agent(q, candidates, top_k=5)
        print(f"  重排后: {len(top)}路证据")
        # 融合
        answer = await synthesize_agent(q, top)
        return answer
    else:
        param = QueryParam(mode=mode, top_k=15, chunk_top_k=15)
        return await rag.aquery(q, param=param)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="索引文档数限制")
    ap.add_argument("--query", help="查询")
    ap.add_argument("--mode", default="multi", choices=["multi", "naive", "local", "global", "hybrid", "mix"])
    ap.add_argument("--warmup", action="store_true", help="预热embedding模型")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    async def main():
        # 预热embedding(避免索引期超时)
        if args.warmup or args.index:
            print("预热embedding模型...")
            get_embed_model().encode(["预热"])

        rag = create_rag()
        await rag.initialize_storages()

        if args.index:
            await index_all(rag, limit=args.limit)
        if args.query:
            answer = await multi_agent_query(rag, args.query, args.mode)
            print(f"\n{'='*20} 回答 {'='*20}")
            print(answer)

    asyncio.run(main())
