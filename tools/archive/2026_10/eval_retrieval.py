#!/usr/bin/env python3
"""检索评测: 5方法对比 (基于LLM生成的检索评测集)

方法:
  M1: LightRAG naive (纯向量)
  M2: LightRAG local (图谱邻域)
  M3: LightRAG mix (图+向量)
  M4: 旧ID-Graph (ID硬桥)
  M5: 双图融合 (Ours, KGContextMatcher 4通道)

指标:
  - recall@k: 期望chunk/位置在检索结果中的命中率
  - location_coverage: 4类位置(text/table/figure/trace)覆盖率
  - 回答质量(LLM判断, 可选)
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer

from algorithms.consistency_check.semantic.scene1.kg_context_matcher import KGContextMatcher

BASE_URL = "https://api.moonshot.cn/v1"
from ai_config import KIMI_KEY as API_KEY
LLM_MODEL = "kimi-k2.6"
WORKING_DIR = "data/gjb_438c/data_assets/lightrag_store"
EVALSET_PATH = "data/gjb_438c/data_assets/retrieval_evalset.json"
OUT_PATH = "data/gjb_438c/data_assets/retrieval_eval_results.json"

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


# ── 方法实现 ──────────────────────────────────────────────
async def m_lightrag(rag, query, mode, top_k=15):
    """M1-M3: LightRAG检索"""
    try:
        param = QueryParam(mode=mode, top_k=top_k, chunk_top_k=top_k, only_need_context=True)
        ctx = await rag.aquery(query, param=param)
        return str(ctx or "")
    except Exception as e:
        return f"ERROR: {e}"


def m_id_graph(matcher, query):
    """M4: 旧ID-Graph"""
    # 提取ID或名称
    idm = re.search(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}", query)
    name = re.sub(r"[?？].*$", "", query).strip()
    results = []
    if idm:
        results.extend(matcher.channel_id_graph(idm.group(0)))
    else:
        # 用名称找mention
        for ent_id, mentions in matcher.entity_mentions.items():
            for m in mentions:
                if name in m.get("context", ""):
                    results.append(m)
    return json.dumps(results, ensure_ascii=False)


def m_fusion(matcher, query):
    """M5: 双图融合"""
    agg = matcher.aggregate(query)
    return json.dumps(agg, ensure_ascii=False)


# ── 评测指标 ──────────────────────────────────────────────
def _try_parse_json(text):
    """尝试解析JSON(兼容fusion/id_graph的结构化输出)"""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _collect_from_occ(occ_list):
    """从occurrences提取(sections, locations, texts)"""
    sections, locs, texts = [], set(), []
    for o in occ_list:
        if o.get("section"):
            sections.append(o["section"])
        locs.add(o.get("location", "text"))
        texts.append(str(o.get("snippet", o.get("content", ""))))
    return sections, locs, texts


def eval_recall(result_text, expected, entity_name=""):
    """计算recall: 期望位置/章节/实体在检索结果中的命中率"""
    if not result_text or result_text.startswith("ERROR") or result_text == "None":
        return {"entity_found": 0.0, "section_recall": 0.0, "loc_recall": 0.0, "avg_recall": 0.0}

    # 解析结构化输出(fusion/id_graph)
    parsed = _try_parse_json(result_text)
    sections, locs, texts = [], set(), []
    if parsed and isinstance(parsed, dict) and "occurrences" in parsed:
        sections, locs, texts = _collect_from_occ(parsed["occurrences"])
        combined = " ".join(texts) + result_text
    elif isinstance(parsed, list):
        sections, locs, texts = _collect_from_occ(parsed)
        combined = " ".join(texts) + result_text
    else:
        combined = result_text
        # 从文本中提取章节号
        sections = re.findall(r"\d+\.\d+(?:\.\d+)*", result_text)
        locs = set()
        if "<table" in result_text or "表格" in result_text:
            locs.add("table")
        if "图" in result_text or "image" in result_text.lower():
            locs.add("figure")
        if any(c.isalpha() for c in result_text[:100]):
            locs.add("text")

    # entity_found: 实体名/ID是否在结果中
    exp = expected
    entity_hit = 0.0
    if entity_name and entity_name in combined:
        entity_hit = 1.0
    if exp.get("entity_id") and exp["entity_id"] in combined:
        entity_hit = 1.0

    # section_recall
    exp_sections = [s for s in exp.get("sections", []) if s]
    sec_hits = sum(1 for s in exp_sections if s in combined)
    n_sec = max(len(exp_sections), 1)

    # loc_recall
    exp_locs = exp.get("locations", [])
    loc_hits = sum(1 for l in exp_locs if l in locs)
    n_loc = max(len(exp_locs), 1)

    avg = (entity_hit + sec_hits / n_sec + loc_hits / n_loc) / 3
    return {
        "entity_found": round(entity_hit, 3),
        "section_recall": round(sec_hits / n_sec, 3),
        "loc_recall": round(loc_hits / n_loc, 3),
        "avg_recall": round(avg, 3),
    }


async def main(sample=None):
    # 加载评测集
    evalset = json.loads(open(EVALSET_PATH).read())
    if sample:
        evalset = evalset[:sample]
    print(f"评测查询: {len(evalset)}")

    # 初始化
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_func, llm_model_name=LLM_MODEL,
        embedding_func=EmbeddingFunc(embedding_dim=512, max_token_size=8192, func=embedding_func),
        embedding_func_max_async=2, default_embedding_timeout=600,
        entity_extraction_use_json=True,
    )
    await rag.initialize_storages()
    matcher = KGContextMatcher()

    methods = {
        "M1_lightrag_naive": lambda q: m_lightrag(rag, q, "naive"),
        "M2_lightrag_local": lambda q: m_lightrag(rag, q, "local"),
        "M3_lightrag_mix": lambda q: m_lightrag(rag, q, "mix"),
        "M4_id_graph": lambda q: asyncio.to_thread(m_id_graph, matcher, q),
        "M5_fusion": lambda q: asyncio.to_thread(m_fusion, matcher, q),
    }

    results = {m: [] for m in methods}
    for i, item in enumerate(evalset):
        q = item["query"]
        exp = item["expected"]
        for mname, fn in methods.items():
            t0 = time.time()
            try:
                text = await fn(q)
            except Exception as e:
                text = f"ERROR: {e}"
            dt = time.time() - t0
            scores = eval_recall(text, exp, entity_name=item.get("entity", ""))
            results[mname].append({**scores, "time": round(dt, 2)})
        if (i + 1) % 20 == 0:
            print(f"  评测 {i+1}/{len(evalset)}")

    # 汇总
    summary = {}
    for mname, scores in results.items():
        avg = {k: round(sum(s[k] for s in scores) / max(len(scores), 1), 3)
               for k in ["entity_found", "section_recall", "loc_recall", "avg_recall"]}
        avg["avg_time"] = round(sum(s["time"] for s in scores) / max(len(scores), 1), 2)
        summary[mname] = avg
        print(f"\n{mname}:")
        for k, v in avg.items():
            print(f"  {k}: {v}")

    json.dump({"summary": summary, "details": results},
              open(OUT_PATH, "w"), ensure_ascii=False, indent=2)
    print(f"\n✅ 评测完成 → {OUT_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None, help="评测样本数")
    args = ap.parse_args()
    asyncio.run(main(sample=args.sample))
