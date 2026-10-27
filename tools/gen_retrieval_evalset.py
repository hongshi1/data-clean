#!/usr/bin/env python3
"""LLM生成检索评测集 (查询→期望召回)

流程:
1. 从LightRAG图谱采样100个实体(覆盖: 软件功能/接口/数据项/系统)
2. kimi-k2.6为每个实体生成3种问法查询(功能定义/结构/溯源)
3. 自动标注期望召回: 实体在chunks中出现的所有位置
4. 输出: retrieval_evalset.json

期望召回标注(确定性方法):
- 实体名在text_chunks/struct_chunks中字符串匹配的chunk
- ID-Graph中该实体的所有mention位置
- VLM图片分析中key_elements含该实体的图片
"""
import argparse
import asyncio
import json
import os
import re
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.consistency.semantic.scene1.kg_context_matcher import KGContextMatcher

from ai_config import KIMI_KEY as API_KEY
URL = "https://api.moonshot.cn/v1/chat/completions"
MODEL = "kimi-k2.6"
OUT_PATH = "data/gjb_438c/data_assets/retrieval_evalset.json"

QUERY_TEMPLATES = [
    "{entity}是什么功能？",
    "{entity}有哪些子功能或组成部分？",
    "{entity}在文档哪些位置被提到？",
]


def sample_entities(matcher, n=100, seed=42):
    """从图谱采样实体(优先有ID的, 保证期望召回标注可靠)"""
    random.seed(seed)
    # 1. 有ID的实体(ID-Graph的entity, 期望召回最可靠)
    id_entities = []
    for ent_id in matcher.entity_mentions:
        # 从mention context找名称
        for m in matcher.entity_mentions[ent_id]:
            ctx = m.get("context", "")
            m_name = re.search(r"<p>([^<]{2,30})</p>", ctx)
            if m_name and any('\u4e00' <= c <= '\u9fff' for c in m_name.group(1)):
                id_entities.append((ent_id, m_name.group(1)))
                break
    # 去重
    seen = set()
    unique_id = []
    for eid, nm in id_entities:
        if eid not in seen:
            seen.add(eid)
            unique_id.append((eid, nm))

    # 2. 无ID但中文名实体(LightRAG图谱, 语义召回)
    cn_entities = []
    for name in matcher.lr_entity_chunks:
        if any('\u4e00' <= c <= '\u9fff' for c in name) and 3 <= len(name) <= 20:
            if name not in {"数据获取", "分系统", "系统"}:
                cn_entities.append(name)

    # 混合: 60%有ID + 40%语义
    n_id = min(int(n * 0.6), len(unique_id))
    n_cn = min(n - n_id, len(cn_entities))
    sampled = random.sample(unique_id, n_id) + [(None, e) for e in random.sample(cn_entities, n_cn)]
    # 返回 (entity_id, name) 对
    return sampled[:n]


async def gen_query_llm(entity, matcher):
    """用kimi生成3种问法(带实体上下文, 更自然)"""
    import httpx
    prompt = f"""你是SRS软件需求文档专家。请为实体"{entity}"生成3个不同的中文检索查询问题, 覆盖:
1. 功能定义型(问它是什么)
2. 结构型(问它的子功能/组成)
3. 溯源型(问它在文档哪里出现)

要求: 自然口语化, 不用引号, 每个一行, 不要编号。

输出:"""
    try:
        r = httpx.post(URL, headers={"Authorization": f"Bearer {API_KEY}"},
                       json={"model": MODEL, "thinking": {"type": "disabled"},
                             "messages": [{"role": "user", "content": prompt}],
                             "max_tokens": 200}, timeout=120)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "")
            # 清洗: 去掉编号/前缀/类型标签
            lines = []
            for line in content.split("\n"):
                line = re.sub(r"^\d+[\.\、\)]\s*", "", line.strip())
                line = re.sub(r"^(功能定义型|结构型|溯源型)[:：]\s*", "", line)
                line = line.strip().strip('"').strip("'")
                if line and len(line) > 4:
                    lines.append(line)
            if len(lines) >= 3:
                return lines[:3]
    except Exception:
        pass
    # fallback: 模板生成
    return [t.format(entity=entity) for t in QUERY_TEMPLATES]


async def annotate_expected(matcher, entity, entity_id):
    """标注期望召回位置(确定性)"""
    expected = {"chunks": [], "sections": [], "locations": set(), "docs": set()}

    # 1. 结构化chunks中字符串匹配
    for c in matcher.struct_chunks:
        text = c.get("text", "")
        if entity in text or (entity_id and entity_id in text):
            expected["chunks"].append(c.get("chunk_id", ""))
            expected["sections"].append(c.get("section", ""))
            expected["locations"].add(c.get("type", "text"))
            expected["docs"].add(c.get("doc", ""))

    # 2. ID-Graph mentions
    if entity_id:
        for m in matcher.channel_id_graph(entity_id):
            expected["sections"].append(m.get("section", ""))
            expected["locations"].add("table" if "table" in m.get("location", "") else "text")
            expected["docs"].add(m.get("doc", ""))

    # 3. VLM图片
    for img in matcher.channel_images(entity):
        expected["locations"].add("figure")
        expected["docs"].add(img.get("doc", ""))

    return {
        "chunk_ids": list(dict.fromkeys(expected["chunks"])),
        "sections": list(dict.fromkeys(expected["sections"])),
        "locations": sorted(expected["locations"]),
        "docs": sorted(expected["docs"]),
    }


async def main(n=100):
    matcher = KGContextMatcher()
    pairs = sample_entities(matcher, n)
    print(f"采样实体: {len(pairs)} (有ID: {sum(1 for eid, _ in pairs if eid)})")

    evalset = []
    for i, (entity_id, ent) in enumerate(pairs):
        queries = await gen_query_llm(ent, matcher)
        expected = await annotate_expected(matcher, ent, entity_id)
        for q in queries:
            evalset.append({
                "id": f"q_{i:04d}",
                "query": q,
                "entity": ent,
                "entity_id": entity_id,
                "expected": expected,
                "difficulty": "easy" if len(expected["sections"]) <= 2 else "hard",
            })
        if (i + 1) % 20 == 0:
            print(f"  已生成 {i+1}/{len(pairs)} 实体 ({len(evalset)} 查询)")
            json.dump(evalset, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    json.dump(evalset, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✅ 评测集完成: {len(evalset)} 查询对 → {OUT_PATH}")
    # 统计
    diff = {}
    for e in evalset:
        diff[e["difficulty"]] = diff.get(e["difficulty"], 0) + 1
    print("难度分布:", diff)
    locs = {}
    for e in evalset:
        for loc in e["expected"]["locations"]:
            locs[loc] = locs.get(loc, 0) + 1
    print("期望位置类型:", locs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    asyncio.run(main(args.n))
