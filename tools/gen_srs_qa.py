#!/usr/bin/env python3
"""
SRS多模态QA对生成器 — 基于pair dataset

借鉴FlowVQA的4类问题设计(事实检索/应用场景/引用推理/拓扑推理),
针对SRS的3模态(图/表/文)生成6类QA对:

QA类型设计(参考FlowVQA + SRS特性):
  T1 图文一致性: 图里的功能名 vs 正文/表里的功能名是否对齐
     Q: "界面开发功能包含哪些子功能?" A: "开发工程生成、组件配置填写..."(图+文交叉)
  T2 表格事实检索: 表格里的事实(功能名/ID/需求描述)
     Q: "组件配置填写的需求标识符是什么?" A: "PZXQ-GN-JMJCKJ-JMKF-ZJPZTX"
  T3 跨模态计数: 图里有几个用例 vs 表里有几行功能
     Q: "界面开发用例图中有多少个子功能?" A: "6个"(图计数, 表验证)
  T4 功能溯源: 某功能在哪个章节/图/表出现
     Q: "公共组件管理在文档哪里有描述?" A: "表3第3行, 正文第1段, 图4用例"
  T5 需求描述理解: 表格里的需求描述文本理解
     Q: "组件下载管理提供什么功能?" A: "提供组件包管理功能，支持下载安装..."
  T6 图类型识别: 图片是什么类型(用例图/流程图/接口图)
     Q: "图4是什么类型的图?" A: "用例图"

生成策略:
  - T1/T3: 需要看图(kimi VLM) + 表/文交叉验证
  - T2/T4/T5: 从表格/正文确定性提取(不需看图)
  - T6: VLM分析结果直接转QA
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

API_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
URL = "https://api.moonshot.cn/v1/chat/completions"
MODEL = "kimi-k2.6"
PAIR_DIR = "data/gjb_438c/pair_dataset"
OUT_PATH = "data/gjb_438c/data_assets/srs_multimodal_qa.json"

random.seed(42)


def load_all_pairs():
    """加载所有pair实例"""
    pairs = []
    for sc_dir in sorted(os.listdir(PAIR_DIR)):
        sc_path = os.path.join(PAIR_DIR, sc_dir)
        if not os.path.isdir(sc_path):
            continue
        for inst_dir_name in sorted(os.listdir(sc_path)):
            inst_path = os.path.join(sc_path, inst_dir_name)
            if not os.path.isdir(inst_path):
                continue
            meta_path = os.path.join(inst_path, "meta.json")
            if not os.path.exists(meta_path):
                continue
            meta = json.loads(open(meta_path).read())
            # 加载表格和正文
            table_rows = []
            tbl_path = os.path.join(inst_path, "table.csv")
            if os.path.exists(tbl_path):
                with open(tbl_path, encoding="utf-8") as f:
                    reader = csv.reader(f)
                    table_rows = [r for r in reader if any(c.strip() for c in r)]
            text = ""
            txt_path = os.path.join(inst_path, "text.txt")
            if os.path.exists(txt_path):
                text = open(txt_path, encoding="utf-8").read()
            img_path = os.path.join(inst_path, "image.png")
            pairs.append({
                "meta": meta,
                "table_rows": table_rows,
                "text": text,
                "image_path": img_path,
                "image_exists": os.path.exists(img_path),
                "sc_dir": sc_dir,
            })
    return pairs


# ── 确定性QA生成(不需VLM) ────────────────────────────────
def gen_table_factual_qa(pair):
    """T2 表格事实检索: 从表格行生成QA"""
    qas = []
    rows = pair["table_rows"]
    if len(rows) < 2:
        return qas
    headers = rows[0]
    for row in rows[1:]:
        cells = [c.strip() for c in row if c.strip()]
        if len(cells) < 2:
            continue
        # 找功能名和ID
        func_name = None
        func_id = None
        desc = None
        for i, cell in enumerate(cells):
            if i < len(headers):
                h = headers[i].lower() if i < len(headers) else ""
            else:
                h = ""
            if any(kw in h for kw in ["use case", "功能", "名称"]):
                if not func_name and len(cell) > 1:
                    func_name = cell
            elif "标识" in h or "id" in h:
                if not func_id and len(cell) > 5:
                    func_id = cell
            elif "描述" in h:
                if not desc and len(cell) > 10:
                    desc = cell
        if func_name and func_id:
            qas.append({
                "type": "T2_table_factual",
                "question": f"{func_name}的需求标识符是什么？",
                "answer": func_id,
                "evidence": f"表格: {pair['meta']['table_caption']}",
            })
        if func_name and desc:
            qas.append({
                "type": "T2_table_factual",
                "question": f"{func_name}提供什么功能？",
                "answer": desc[:150],
                "evidence": f"表格: {pair['meta']['table_caption']}",
            })
    return qas


def gen_text_evidence_qa(pair):
    """T5 正文理解: 从正文生成QA"""
    qas = []
    text = pair["text"]
    func_names = pair["meta"].get("func_names", [])
    if not text or len(text) < 30:
        return qas
    # 正文里列出功能名的句子
    if func_names and len(func_names) >= 2:
        qas.append({
            "type": "T5_text_understanding",
            "question": f"{pair['meta'].get('section_title', '该功能')}包含哪些子功能？",
            "answer": "、".join(func_names),
            "evidence": f"正文: {text[:100]}",
        })
    return qas


def gen_tracing_qa(pair):
    """T4 功能溯源: 某功能在哪"""
    qas = []
    func_names = pair["meta"].get("func_names", [])
    if not func_names:
        return qas
    name = func_names[0]
    locations = []
    if pair["meta"].get("table_caption"):
        locations.append(f"表格「{pair['meta']['table_caption']}」")
    if pair["meta"].get("image_caption"):
        locations.append(f"图片「{pair['meta']['image_caption']}」")
    if pair["text"]:
        locations.append(f"正文（章节{pair['meta']['section']}）")
    qas.append({
        "type": "T4_tracing",
        "question": f"{name}在文档的哪些位置有描述？",
        "answer": "、".join(locations),
        "evidence": f"章节: {pair['meta']['section']}",
    })
    return qas


def gen_counting_qa(pair):
    """T3 跨模态计数: 表格行数 vs 功能名数"""
    qas = []
    func_names = pair["meta"].get("func_names", [])
    if len(func_names) >= 2:
        qas.append({
            "type": "T3_counting",
            "question": f"{pair['meta'].get('section_title', '该功能')}下有多少个子功能？",
            "answer": f"{len(func_names)}个：" + "、".join(func_names),
            "evidence": f"表格: {pair['meta']['table_caption']}",
        })
    return qas


# ── VLM QA生成(需看图) ──────────────────────────────────
VLM_PROMPT = """你是SRS软件需求规格说明文档的专家。基于以下图片和元数据，生成2个问答对。

图片信息:
- 图注: {caption}
- 图类型: {fig_type}
- 所在章节: {section}

表格功能名(用于交叉验证):
{func_names}

要求:
1. 问题必须**只能通过看图才能回答**(涉及图中的参与者/用例/连线/结构)
2. 答案要具体, 引用图中的元素
3. 生成2个不同角度的问题(如: 参与者是谁/有几个用例/某用例的关联关系)
4. 输出JSON数组: [{{"question": "...", "answer": "...", "type": "T1_visual_consistency"或"T6_image_type"}}]
5. 只输出JSON, 不要其他文字"""


async def gen_vlm_qa(pair):
    """T1/T6: 需要看图的QA"""
    if not pair["image_exists"]:
        return []
    meta = pair["meta"]
    caption = meta.get("image_caption", "")
    # 从sc_dir提取图类型
    sc_name = pair["sc_dir"]
    fig_type_map = {
        "sc1": "用例图", "sc2": "流程图", "sc3": "接口图",
        "sc4": "流程图", "sc5": "功能图", "sc7": "用例图", "sc8": "其他图",
    }
    fig_type = fig_type_map.get(sc_name[:3], "图")
    func_names = meta.get("func_names", [])[:6]

    prompt = VLM_PROMPT.format(
        caption=caption, fig_type=fig_type, section=meta.get("section", ""),
        func_names="、".join(func_names) if func_names else "(无)")

    b64 = base64.b64encode(open(pair["image_path"], "rb").read()).decode()
    messages = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": prompt},
    ]}]

    try:
        r = httpx.post(URL, headers={"Authorization": f"Bearer {API_KEY}"},
                       json={"model": MODEL, "thinking": {"type": "disabled"},
                             "messages": messages, "max_tokens": 600,
                             "response_format": {"type": "json_object"}},
                       timeout=180)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "")
            # 解析JSON(可能被包在数组里)
            try:
                qa_list = json.loads(content)
                if isinstance(qa_list, list):
                    return qa_list[:2]
                elif isinstance(qa_list, dict) and "question" in qa_list:
                    return [qa_list]
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"  ⚠ VLM失败: {e}")
    return []


async def gen_for_pair(pair):
    """为单个pair生成全部类型QA"""
    qas = []
    # 确定性QA(T2/T4/T5/T3)
    qas.extend(gen_table_factual_qa(pair))
    qas.extend(gen_tracing_qa(pair))
    qas.extend(gen_text_evidence_qa(pair))
    qas.extend(gen_counting_qa(pair))
    # VLM QA(T1/T6)
    vlm_qas = await gen_vlm_qa(pair)
    qas.extend(vlm_qas)

    # 统一格式
    result = []
    for qa in qas:
        result.append({
            "id": f"{pair['meta']['instance_id']}_{len(result):02d}",
            "pair_id": pair["meta"]["instance_id"],
            "scenario": pair["meta"]["scenario"],
            "doc": pair["meta"]["doc"],
            "section": pair["meta"]["section"],
            "image_path": pair["image_path"] if pair["image_exists"] else "",
            "image_caption": pair["meta"].get("image_caption", ""),
            "table_caption": pair["meta"].get("table_caption", ""),
            "type": qa.get("type", "unknown"),
            "question": qa["question"],
            "answer": qa["answer"],
            "evidence": qa.get("evidence", ""),
            "difficulty": "easy" if qa.get("type") in ("T2", "T4") else "medium",
        })
    return result


async def main(limit=None, vlm_limit=50):
    pairs = load_all_pairs()
    print(f"加载pair实例: {len(pairs)}个")
    if limit:
        pairs = pairs[:limit]

    all_qa = []
    vlm_count = 0
    for i, pair in enumerate(pairs):
        # VLM调用限流(只对前vlm_limit个pair生成VLM QA)
        if vlm_count >= vlm_limit:
            pair = {**pair, "image_exists": False}  # 关闭VLM
        else:
            vlm_count += 1

        qas = await gen_for_pair(pair)
        all_qa.extend(qas)
        if (i + 1) % 20 == 0:
            print(f"  已处理 {i+1}/{len(pairs)} pair, 生成{len(all_qa)}个QA")
            json.dump(all_qa, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)

    json.dump(all_qa, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
    # 统计
    from collections import Counter
    by_type = Counter(q["type"] for q in all_qa)
    by_diff = Counter(q["difficulty"] for q in all_qa)
    has_img = sum(1 for q in all_qa if q["image_path"])
    print(f"\n✅ QA对生成完成: {len(all_qa)}条 → {OUT_PATH}")
    print(f"按类型: {dict(by_type)}")
    print(f"按难度: {dict(by_diff)}")
    print(f"含图片: {has_img}/{len(all_qa)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="处理pair数(默认全部)")
    ap.add_argument("--vlm-limit", type=int, default=50, help="VLM QA生成数(成本控制)")
    args = ap.parse_args()
    asyncio.run(main(limit=args.limit, vlm_limit=args.vlm_limit))
