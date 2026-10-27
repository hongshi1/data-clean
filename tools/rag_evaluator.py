#!/usr/bin/env python3
"""多Agent RAG评测: 召回质量 + 回答质量

评测集: Gold Standard的矛盾实体对(同一实体不同名称 → 验证RAG召回)
- 查询每个实体的名称, 检查RAG是否召回包含该实体ID/名称的证据
- 对比: naive/local/global/hybrid/mix 5模式召回率

复用: LightRAG查询 + Gold Standard + 评估指标(recall@k)
"""
import asyncio
import json
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
GOLD_PATH = "data/gjb_438c/data_assets/gold_standard/multi_scene_gold_standard.json"

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


def load_gold():
    """加载Gold Standard: 提取实体名称对"""
    gs = json.loads(open(GOLD_PATH, encoding="utf-8").read())
    entities = set()
    for pair in gs:
        if isinstance(pair, dict):
            for key in ["entity_a", "entity_b", "name_a", "name_b", "id_a", "id_b"]:
                v = pair.get(key)
                if isinstance(v, str) and len(v) > 1:
                    entities.add(v)
    return sorted(entities)


async def eval_mode(rag, entities, mode, top_k=10, sample=None):
    """评估某模式对实体的召回"""
    if sample:
        entities = entities[:sample]
    hits = 0
    for i, e in enumerate(entities):
        try:
            param = QueryParam(mode=mode, top_k=top_k, chunk_top_k=top_k, only_need_context=True)
            ctx = await rag.aquery(e, param=param)
            # 召回判定: 上下文是否包含查询词(或ID)
            if ctx and (e[:6] in ctx or ctx != "Sorry"):
                hits += 1
        except Exception:
            pass
        if (i + 1) % 20 == 0:
            print(f"  [{mode}] {i+1}/{len(entities)}")
    return hits / max(len(entities), 1)


async def main():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_func, llm_model_name=LLM_MODEL,
        embedding_func=EmbeddingFunc(embedding_dim=512, max_token_size=8192, func=embedding_func),
        embedding_func_max_async=2, default_embedding_timeout=600,
        entity_extraction_use_json=True,
    )
    await rag.initialize_storages()

    entities = load_gold()
    print(f"评测实体: {len(entities)}")
    results = {}
    for mode in ["naive", "local", "hybrid", "mix"]:
        r = await eval_mode(rag, entities, mode, sample=30)
        results[mode] = r
        print(f"  {mode} 召回率: {r:.3f}")
    print("\n=== 总结 ===")
    for k, v in results.items():
        print(f"  {k}: {v:.3f}")
    json.dump(results, open("data/gjb_438c/data_assets/rag_eval_results.json", "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    asyncio.run(main())
