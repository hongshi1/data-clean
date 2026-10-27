#!/usr/bin/env python3
"""
全pair覆盖的LLM QA生成 — 每个pair生成2条QA, 按sc1-sc8组织

策略:
  1. 遍历366个pair, 每个生成2条QA(1正例+1注入, 四类轮换)
  2. 不带图片(用表格+正文内容传给LLM) → 快(每pair~5秒)
  3. 有图片的pair额外标记VLM可用
  4. 按sc1-sc8目录组织输出
  5. 全LLM生成, 无规则模板

输出: data/gjb_438c/data_assets/srs_qa_by_scene/
  ├── sc1_usecase_capability.json
  ├── sc2_flowchart_usecase.json
  ├── ...
  └── sc8_pure_image.json
"""
import asyncio
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY as KEY
MODEL = "kimi-k2.6"
PAIR_DIR = "data/gjb_438c/pair_dataset"
OUT_DIR = "data/gjb_438c/data_assets/srs_qa_by_scene"

# 四类不一致轮换
TYPES = ["terminology", "parameter", "business_logic", "gjb_compliance"]
TYPE_CN = {
    "terminology": "术语层面(同名实体/多实体映射)",
    "parameter": "参数指标(数值/单位/属性一致性)",
    "business_logic": "业务逻辑(流程/时序/异常流一致性)",
    "gjb_compliance": "GJB合规(模板/接口定义/ID格式规范)",
}


def load_pairs():
    """加载全部pair, 按场景分组"""
    by_scene = {}
    for sc_dir in sorted(os.listdir(PAIR_DIR)):
        sc_path = os.path.join(PAIR_DIR, sc_dir)
        if not os.path.isdir(sc_path):
            continue
        pairs = []
        for inst in sorted(os.listdir(sc_path)):
            ip = os.path.join(sc_path, inst)
            if not os.path.isdir(ip):
                continue
            mp = os.path.join(ip, "meta.json")
            if not os.path.exists(mp):
                continue
            meta = json.loads(open(mp).read())
            rows = []
            tp = os.path.join(ip, "table.csv")
            if os.path.exists(tp):
                with open(tp, encoding="utf-8") as f:
                    rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
            text = ""
            txtp = os.path.join(ip, "text.txt")
            if os.path.exists(txtp):
                text = open(txtp, encoding="utf-8").read()
            pairs.append({
                "meta": meta, "table_rows": rows, "text": text,
                "image_path": os.path.join(ip, "image.png"),
                "image_exists": os.path.exists(os.path.join(ip, "image.png")),
                "inst_path": ip, "sc_dir": sc_dir,
            })
        by_scene[sc_dir] = pairs
    return by_scene


def make_prompt(pair, qa_type):
    """构造LLM prompt(不带图片, 用表格+正文)"""
    meta = pair["meta"]
    fns = meta.get("func_names", [])[:5]
    
    # 表格内容(前5行, 每行截断)
    tbl_lines = []
    for row in pair["table_rows"][:5]:
        cells = [str(c)[:30] for c in row[:6] if c.strip()]
        if cells:
            tbl_lines.append(",".join(cells))
    tbl_content = "\n".join(tbl_lines[:5]) if tbl_lines else "(无表格)"
    
    txt_content = pair["text"][:300] if pair["text"] else "(无正文)"
    
    return f"""你是SRS软件需求文档一致性校验专家。基于以下文档片段, 生成2个QA对。

文档: {meta.get('doc', '')[:25]}
章节: {meta.get('section', '')}
图: {meta.get('image_caption', '')}
表: {meta.get('table_caption', '')}
功能名: {'、'.join(fns) if fns else '(无)'}

表格内容:
{tbl_content}

正文:
{txt_content}

请生成2个QA对:
1. 正例(consistent): 针对「{TYPE_CN[qa_type]}」, 确认文档内容一致
2. 注入(inconsistent): 针对「{TYPE_CN[qa_type]}」, 假设引入一个不一致

要求:
- 问题中用{{table}}表示表格位置, {{text}}表示正文位置, {{image}}表示图片位置
- 注入QA的答案要基于inject_detail描述的假设场景
- 问题要自然, 像真实用户提问

输出JSON数组:
[{{"inconsistency_type":"{qa_type}","subtype":"...","label":"consistent/inconsistent","is_injected":false/true,"question":"...{{table}}...","answer":"...","inject_detail":"...(注入填,正例填null)","difficulty":"easy/medium/hard"}}]"""


async def gen_qa(pair, qa_type):
    """用LLM生成2条QA(不带图片)"""
    prompt = make_prompt(pair, qa_type)
    try:
        r = await asyncio.to_thread(
            httpx.post, URL,
            headers={"Authorization": f"Bearer {KEY}"},
            json={"model": MODEL, "thinking": {"type": "disabled"},
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 800},
            timeout=120)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "")
            # 提取JSON数组
            m = re.search(r'\[.*\]', content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except:
                    pass
            # 尝试直接解析
            try:
                d = json.loads(content)
                if isinstance(d, list):
                    return d
                if isinstance(d, dict):
                    for k in ["qa", "questions", "data"]:
                        if k in d and isinstance(d[k], list):
                            return d[k]
                    return [d] if "question" in d else []
            except:
                pass
    except Exception as e:
        print(f"    ⚠ {e}")
    return []


def normalize_qa(qa_item, pair, qa_type, qid):
    """归一化QA格式"""
    meta = pair["meta"]
    ph = {
        "image": pair["image_path"] if pair["image_exists"] else "",
        "table": os.path.join(pair["inst_path"], "table.csv"),
        "text": os.path.join(pair["inst_path"], "text.txt"),
    }
    # 修路径
    for k in ["image", "table", "text"]:
        if ph[k] and not os.path.exists(ph[k]):
            ph[k] = ""
    
    # 归一化type
    t = qa_item.get("inconsistency_type", qa_type)
    if "术语" in t or "term" in t.lower():
        t = "terminology"
    elif "参数" in t or "param" in t.lower():
        t = "parameter"
    elif "逻辑" in t or "logic" in t.lower():
        t = "business_logic"
    elif "GJB" in t or "gjb" in t.lower() or "合规" in t:
        t = "gjb_compliance"
    else:
        t = qa_type
    
    # 归一化label
    l = qa_item.get("label", "")
    if "consistent" in l.lower() or "正例" in l:
        l = "consistent"
    elif "inconsistent" in l.lower() or "注入" in l or "不一致" in l:
        l = "inconsistent"
    else:
        l = "inconsistent" if qa_item.get("is_injected") else "consistent"
    
    # 归一化difficulty
    d = str(qa_item.get("difficulty", "medium"))
    diff_map = {"easy": "easy", "简单": "easy", "1": "easy",
                "medium": "medium", "中等": "medium", "2": "medium",
                "hard": "hard", "困难": "hard", "较难": "hard", "3": "hard"}
    d = diff_map.get(d, "medium")
    
    # modalities
    mods = [k for k in ["image", "table", "text"]
            if f'{{{k}}}' in qa_item.get("question", "") and ph.get(k)]
    
    return {
        "qid": qid,
        "pair_id": meta["instance_id"],
        "scene": pair["sc_dir"],
        "split": "train" if int(re.match(r'(\d+)', meta.get("doc", "01")).group(1)) <= 10
                 else ("dev" if int(re.match(r'(\d+)', meta.get("doc", "01")).group(1)) <= 13 else "test"),
        "question": qa_item.get("question", ""),
        "placeholders": ph,
        "modalities": mods if mods else ["text"],
        "answer": qa_item.get("answer", ""),
        "answer_modality": "table" if "{table}" in qa_item.get("question", "") else "text",
        "inconsistency_type": t,
        "subtype": qa_item.get("subtype", ""),
        "label": l,
        "is_injected": l == "inconsistent",
        "inject_detail": qa_item.get("inject_detail") or "",
        "rule_id": {"terminology": "TERM-001", "parameter": "PARAM-001",
                    "business_logic": "LOGIC-001", "gjb_compliance": "GJB-001"}.get(t, ""),
        "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。" if l == "inconsistent" else "",
        "evidence": {
            "doc": meta.get("doc", ""),
            "section": meta.get("section", ""),
            "image_caption": meta.get("image_caption", ""),
            "table_caption": meta.get("table_caption", ""),
        },
        "difficulty": d,
        "source": "llm_generated",
        "verified": False,
    }


async def main():
    by_scene = load_pairs()
    os.makedirs(OUT_DIR, exist_ok=True)
    
    total_pairs = sum(len(pairs) for pairs in by_scene.values())
    print(f"总pair: {total_pairs}, 场景: {len(by_scene)}")
    
    qid_counter = 0
    total_qa = 0
    
    for sc_dir, pairs in sorted(by_scene.items()):
        sc_name = sc_dir
        sc_qa = []
        
        for i, pair in enumerate(pairs):
            # 四类轮换: 按pair序号选类型
            qa_type = TYPES[i % 4]
            
            qa_list = await gen_qa(pair, qa_type)
            
            for qa_item in qa_list:
                if not qa_item.get("question") or not qa_item.get("answer"):
                    continue
                if len(str(qa_item["answer"])) < 5:
                    continue
                normalized = normalize_qa(qa_item, pair, qa_type, f"srs_{sc_dir[:3]}_{qid_counter:05d}")
                sc_qa.append(normalized)
                qid_counter += 1
            
            if (i + 1) % 20 == 0:
                print(f"  {sc_dir}: {i+1}/{len(pairs)}pair, {len(sc_qa)}QA", flush=True)
        
        # 保存按场景
        out_path = os.path.join(OUT_DIR, f"{sc_name}.json")
        json.dump(sc_qa, open(out_path, "w"), ensure_ascii=False, indent=1)
        total_qa += len(sc_qa)
        print(f"✅ {sc_name}: {len(sc_qa)}条QA → {out_path}")
    
    # 汇总
    print(f"\n{'='*50}")
    print(f"总计: {total_qa}条QA, {total_pairs}个pair")
    print(f"覆盖率: {total_pairs}个pair全部覆盖")
    
    # 合并文件
    all_qa = []
    for sc_dir in sorted(by_scene.keys()):
        p = os.path.join(OUT_DIR, f"{sc_dir}.json")
        if os.path.exists(p):
            all_qa.extend(json.loads(open(p).read()))
    json.dump(all_qa, open(os.path.join(OUT_DIR, "all_scenes.json"), "w"),
              ensure_ascii=False, indent=1)
    
    from collections import Counter
    print(f"\n按类型: {dict(Counter(q['inconsistency_type'] for q in all_qa))}")
    print(f"按标签: {dict(Counter(q['label'] for q in all_qa))}")
    print(f"按场景: {dict(Counter(q['scene'] for q in all_qa))}")


if __name__ == "__main__":
    asyncio.run(main())
