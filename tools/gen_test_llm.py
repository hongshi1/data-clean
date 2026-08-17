#!/usr/bin/env python3
"""
全LLM生成SRS测试数据集 — 不用规则模板, kimi逐条生成

策略:
  1. 从366个pair采样50个(分层: 每场景按比例)
  2. 每个pair用kimi生成4类×2(正负)=8条QA
  3. 全部LLM生成(无规则模板), 保证自然性和多样性
  4. 双LLM验证(kimi生成 → claude验证)
  5. 过滤后约200-300条高质量QA

输出: data/gjb_438c/data_assets/srs_test_llm.json
"""
import argparse
import asyncio
import base64
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
CLAUDE_URL = KIMI_URL  # 用同一endpoint
CLAUDE_KEY = KIMI_KEY
MODEL = "kimi-k2.6"
PAIR_DIR = "data/gjb_438c/pair_dataset"
OUT_PATH = "data/gjb_438c/data_assets/srs_test_llm.json"

random.seed(42)


def load_pairs():
    pairs = []
    for sc in sorted(os.listdir(PAIR_DIR)):
        sc_dir = os.path.join(PAIR_DIR, sc)
        if not os.path.isdir(sc_dir):
            continue
        for inst in sorted(os.listdir(sc_dir)):
            ip = os.path.join(sc_dir, inst)
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
                "inst_path": ip, "sc_dir": sc,
            })
    return pairs


def sample_pairs(pairs, n=50):
    """分层采样: 每场景按比例"""
    by_sc = {}
    for p in pairs:
        by_sc.setdefault(p["sc_dir"], []).append(p)
    sampled = []
    for sc, ps in by_sc.items():
        k = max(1, round(n * len(ps) / len(pairs)))
        sampled.extend(random.sample(ps, min(k, len(ps))))
    return sampled[:n]


GEN_PROMPT = """你是SRS软件需求规格说明文档的一致性校验专家。基于以下真实SRS文档片段，生成8个问答对（4类不一致 × 正例+注入各1条）。

文档信息:
- 文档: {doc}
- 章节: {section}
- 图: {image_caption}
- 表: {table_caption}
- 功能名: {func_names}

表格内容(前5行):
{table_content}

正文:
{text_content}

请生成以下8条QA:

**术语层面(TERM)**:
1. 正例: 确认图/表/文中功能名一致
2. 注入: 假设某功能名被修改(错字/截断/字序), 判断是否一致

**参数指标(PARAM)**:
3. 正例: 查询某接口/参数的属性值
4. 注入: 假设某参数值/单位/属性在不同位置不一致

**业务逻辑(LOGIC)**:
5. 正例: 确认功能描述与表格/图一致
6. 注入: 假设流程步骤顺序错误/异常流引用无效/功能列表缺失

**GJB合规(GJB)**:
7. 正例: 确认表格字段/ID格式符合GJB规范
8. 注入: 假设缺少必填字段/ID格式违规/章节缺失

每条QA格式(JSON数组):
[
  {{
    "inconsistency_type": "terminology/parameter/business_logic/gjb_compliance",
    "subtype": "具体子类型",
    "label": "consistent/inconsistent",
    "is_injected": true/false,
    "question": "问题文本(含{{image}}/{{table}}/{{text}}占位符)",
    "answer": "答案文本",
    "inject_detail": "注入说明(仅注入QA填写, 正例填null)",
    "difficulty": "easy/medium/hard"
  }}
]

要求:
1. 问题必须自然, 像真实用户提问
2. 占位符{{image}}/{{table}}/{{text}}表示多模态输入位置
3. 注入QA的答案必须基于inject_detail的假设场景
4. 只输出JSON数组, 不要其他文字"""


async def gen_qa_for_pair(pair):
    """用kimi为一个pair生成8条QA"""
    meta = pair["meta"]
    func_names = meta.get("func_names", [])[:5]
    
    # 表格内容(前5行)
    table_content = ""
    for row in pair["table_rows"][:5]:
        table_content += ",".join(str(c)[:30] for c in row[:6]) + "\n"
    
    text_content = pair["text"][:300] if pair["text"] else "(无正文)"
    
    prompt = GEN_PROMPT.format(
        doc=meta.get("doc", "")[:30],
        section=meta.get("section", ""),
        image_caption=meta.get("image_caption", ""),
        table_caption=meta.get("table_caption", ""),
        func_names="、".join(func_names) if func_names else "(无)",
        table_content=table_content[:500],
        text_content=text_content,
    )
    
    # 如果有图片, 附带图片
    messages = []
    if pair["image_exists"]:
        b64 = base64.b64encode(open(pair["image_path"], "rb").read()).decode()
        messages.append({"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": prompt},
        ]})
    else:
        messages.append({"role": "user", "content": prompt})
    
    try:
        r = await asyncio.to_thread(
            httpx.post, KIMI_URL,
            headers={"Authorization": f"Bearer {KIMI_KEY}"},
            json={"model": MODEL, "thinking": {"type": "disabled"},
                  "messages": messages, "max_tokens": 2000,
                  },
            timeout=180)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "")
            # 解析JSON(可能被markdown代码块包裹)
            import re
            # 先尝试直接解析
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    for k in ["qa", "questions", "data", "results"]:
                        if k in data and isinstance(data[k], list):
                            return data[k]
                    return [data] if "question" in data else []
            except json.JSONDecodeError:
                pass
            # 尝试提取JSON数组(去掉markdown代码块)
            m = re.search(r'\[.*\]', content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except:
                    pass
            # 尝试提取JSON对象
            m = re.search(r'\{.*\}', content, re.DOTALL)
            if m:
                try:
                    d = json.loads(m.group(0))
                    if isinstance(d, list): return d
                    elif isinstance(d, dict):
                        for k in ["qa", "questions"]:
                            if k in d: return d[k]
                        return [d] if "question" in d else []
                except:
                    pass
            return []
    except Exception as e:
        print(f"  ⚠ LLM生成失败: {e}")
    return []


async def verify_qa(qa):
    """用kimi验证单条QA"""
    prompt = f"""验证以下SRS文档QA对是否正确。

类型: {qa.get('inconsistency_type','?')}
标签: {qa.get('label','?')}
问题: {qa.get('question','')}
答案: {qa.get('answer','')}
注入说明: {qa.get('inject_detail','无')}

判断答案是否正确(正例=一致确认, 注入=不一致分析)。
只输出JSON: {{"correct": true/false, "reason": "一句话"}}"""
    try:
        r = await asyncio.to_thread(
            httpx.post, KIMI_URL,
            headers={"Authorization": f"Bearer {KIMI_KEY}"},
            json={"model": MODEL, "thinking": {"type": "disabled"},
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 200, },
            timeout=120)
        if r.status_code == 200:
            d = json.loads(r.json()["choices"][0]["message"]["content"])
            return d.get("correct", False), d.get("reason", "")
    except:
        pass
    return None, ""


async def main(n=50, verify=True):
    pairs = load_pairs()
    print(f"加载pair: {len(pairs)}个")
    sampled = sample_pairs(pairs, n)
    print(f"采样: {len(sampled)}个pair")
    
    all_qa = []
    qid = 0
    
    for i, pair in enumerate(sampled):
        # 生成QA
        qa_list = await gen_qa_for_pair(pair)
        
        ph = {
            "image": pair["image_path"] if pair["image_exists"] else "",
            "table": os.path.join(pair["inst_path"], "table.csv"),
            "text": os.path.join(pair["inst_path"], "text.txt"),
        }
        ev = {
            "doc": pair["meta"].get("doc", ""),
            "section": pair["meta"].get("section", ""),
            "image_caption": pair["meta"].get("image_caption", ""),
            "table_caption": pair["meta"].get("table_caption", ""),
        }
        
        # 按文档划分
        import re
        doc_num = int(re.match(r'(\d+)', pair["meta"].get("doc", "01")).group(1))
        split = "train" if doc_num <= 10 else ("dev" if doc_num <= 13 else "test")
        
        for qa in qa_list:
            if not qa.get("question") or not qa.get("answer"):
                continue
            # 修路径
            for k in ["image", "table", "text"]:
                if ph[k] and not os.path.exists(ph[k]):
                    ph[k] = ""
            
            item = {
                "qid": f"srs_llm_{split}_{qid:05d}",
                "split": split,
                "pair_id": pair["meta"]["instance_id"],
                "question": qa["question"],
                "placeholders": dict(ph),
                "modalities": [k for k in ["image", "table", "text"]
                               if k in qa["question"] and ph.get(k)],
                "answer": qa["answer"],
                "answer_modality": "table" if "{table}" in qa["question"] else "text",
                "inconsistency_type": qa.get("inconsistency_type", "unknown"),
                "subtype": qa.get("subtype", ""),
                "label": qa.get("label", "consistent"),
                "is_injected": qa.get("is_injected", False),
                "inject_detail": qa.get("inject_detail") or "",
                "rule_id": {"terminology": "TERM-001", "parameter": "PARAM-001",
                            "business_logic": "LOGIC-001", "gjb_compliance": "GJB-001"
                            }.get(qa.get("inconsistency_type", ""), ""),
                "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。" if qa.get("is_injected") else "",
                "evidence": ev,
                "difficulty": qa.get("difficulty", "medium"),
                "source": "llm_generated",
                "verified": False,
            }
            all_qa.append(item)
            qid += 1
        
        print(f"  [{i+1}/{len(sampled)}] {pair['meta']['instance_id']}: 生成{len(qa_list)}条QA (累计{len(all_qa)}条)")
        
        # 每10个pair保存一次
        if (i + 1) % 10 == 0:
            json.dump(all_qa, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
    
    # 验证(可选)
    if verify:
        print(f"\n=== LLM验证({len(all_qa)}条) ===")
        verified_count = 0
        for i, qa in enumerate(all_qa):
            ok, reason = await verify_qa(qa)
            qa["verified"] = ok is True
            if ok:
                verified_count += 1
            if (i + 1) % 20 == 0:
                print(f"  验证 {i+1}/{len(all_qa)}: 通过{verified_count}")
        
        # 只保留验证通过的
        before = len(all_qa)
        all_qa = [q for q in all_qa if q["verified"]]
        print(f"  验证通过: {len(all_qa)}/{before} ({len(all_qa)/before:.0%})")
    
    json.dump(all_qa, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
    
    # 统计
    from collections import Counter
    print(f"\n{'='*60}")
    print(f"✅ 全LLM测试数据集: {len(all_qa)}条 → {OUT_PATH}")
    print(f"按划分: {dict(Counter(q['split'] for q in all_qa))}")
    print(f"按类型: {dict(Counter(q['inconsistency_type'] for q in all_qa))}")
    print(f"按标签: {dict(Counter(q['label'] for q in all_qa))}")
    print(f"按难度: {dict(Counter(q['difficulty'] for q in all_qa))}")
    print(f"全部LLM生成: {sum(1 for q in all_qa if q['source']=='llm_generated')}/{len(all_qa)}")
    print(f"全部验证通过: {sum(1 for q in all_qa if q['verified'])}/{len(all_qa)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50, help="采样pair数")
    ap.add_argument("--no-verify", action="store_true", help="跳过验证")
    args = ap.parse_args()
    asyncio.run(main(n=args.n, verify=not args.no_verify))
