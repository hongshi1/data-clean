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


# ── T7 矛盾检测类QA(图文不一致检测) ─────────────────────
def gen_consistency_check_qa(pair):
    """T7: 检查图/表/文之间的功能名是否一致

    3种子类型:
    a) 图文计数对比: 表格功能数 vs 正文提到的功能数
    b) 功能名缺失: 表里有但正文没提到的功能
    c) 功能名匹配: 正文功能名 vs 表格功能名
    """
    qas = []
    func_names = pair["meta"].get("func_names", [])
    text = pair["text"]
    table_rows = pair["table_rows"]

    # a) 计数对比
    if func_names and text:
        text_hits = sum(1 for n in func_names if n in text)
        qas.append({
            "type": "T7_consistency",
            "question": f"表格「{pair['meta'].get('table_caption','')}」列出了{len(func_names)}个功能，"
                        f"正文是否全部提到了这些功能？如有缺失请指出。",
            "answer": (f"正文提到了{text_hits}/{len(func_names)}个功能。"
                       + (f"缺失：{', '.join(n for n in func_names if n not in text)}"
                          if text_hits < len(func_names) else "全部提到，一致。")),
            "evidence": f"表格功能: {', '.join(func_names[:5])}",
        })

    # b) 功能名匹配检查(找表格里和正文不一致的名称)
    if func_names and text and len(func_names) >= 2:
        # 找正文里提到但不在表格功能名里的疑似功能名
        # (简单启发: 正文"包括：A、B、C"格式的A/B/C)
        import re
        m = re.search(r"包括[：:]\s*([^。]+)", text)
        if m:
            text_funcs = [f.strip() for f in re.split(r"[、,，]", m.group(1)) if len(f.strip()) >= 2]
            if text_funcs:
                only_in_text = [f for f in text_funcs if f not in func_names]
                only_in_table = [f for f in func_names if f not in text_funcs]
                if only_in_text or only_in_table:
                    qas.append({
                        "type": "T7_consistency",
                        "question": f"正文和表格的功能名是否完全一致？请对比分析。",
                        "answer": (f"正文提到{len(text_funcs)}个功能，表格列出{len(func_names)}个。"
                                   + (f"仅正文有：{', '.join(only_in_text[:3])}；" if only_in_text else "")
                                   + (f"仅表格有：{', '.join(only_in_table[:3])}。" if only_in_table else "")
                                   + "一致。" if not only_in_text and not only_in_table else ""),
                        "evidence": f"正文: {m.group(1)[:60]}",
                    })

    # c) 表格内部一致性(同一ID是否重复)
    if len(table_rows) >= 3:
        ids = []
        for row in table_rows[1:]:
            for cell in row:
                if len(cell.strip()) > 10 and any(c.isupper() for c in cell):
                    import re
                    m = re.search(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}", cell)
                    if m:
                        ids.append(m.group(0))
                        break
        if ids:
            from collections import Counter
            dup = {k: v for k, v in Counter(ids).items() if v > 1}
            if dup:
                qas.append({
                    "type": "T7_consistency",
                    "question": f"表格「{pair['meta'].get('table_caption','')}」中是否存在重复的需求标识符？",
                    "answer": f"存在重复：{'; '.join(f'{k}出现{v}次' for k, v in dup.items())}",
                    "evidence": f"表格ID列表: {', '.join(ids[:5])}",
                })
    return qas


# ── T8 跨场景/跨文档QA ──────────────────────────────────
def gen_cross_reference_qa(pair, all_pairs):
    """T8: 跨场景/跨文档的关联QA

    找同一文档里其他场景的pair, 生成跨章节关联问题
    """
    qas = []
    meta = pair["meta"]
    doc = meta["doc"]
    func_names = meta.get("func_names", [])
    if not func_names:
        return qas

    # 找同文档的其他pair
    same_doc = [p for p in all_pairs if p["meta"]["doc"] == doc
                and p["meta"]["instance_id"] != meta["instance_id"]]
    if not same_doc:
        return qas

    # 找功能名在其他pair的正文/表格里出现的
    other_sections = []
    for other in same_doc[:20]:  # 限制搜索范围
        other_text = other["text"]
        other_funcs = other["meta"].get("func_names", [])
        for fn in func_names[:2]:  # 只查前2个功能名
            if fn in other_text or fn in other_funcs:
                other_sections.append({
                    "func": fn,
                    "section": other["meta"]["section"],
                    "caption": other["meta"].get("image_caption", "") or other["meta"].get("table_caption", ""),
                })
                break

    if other_sections:
        os_info = other_sections[0]
        qas.append({
            "type": "T8_cross_reference",
            "question": f"{os_info['func']}除了在章节{meta['section']}出现外，"
                        f"还在文档的其他哪些位置有描述？",
            "answer": f"在章节{os_info['section']}的{os_info['caption']}中也有出现。",
            "evidence": f"跨章节: {meta['section']} → {os_info['section']}",
        })
    return qas


# ── 难度自动分级 ────────────────────────────────────────
def assign_difficulty(qa):
    """根据QA类型和内容自动分级难度

    easy:   单一事实检索(T2/T4), 答案在单一位置
    medium: 跨模态/计数/理解(T3/T5/T7), 需要对比或计数
    hard:   VLM视觉推理(T1)/跨文档(T8), 需要看图或跨章节推理
    """
    t = qa.get("type", "")
    if t in ("T2_table_factual", "T4_tracing"):
        return "easy"
    elif t in ("T1_visual_consistency", "T8_cross_reference"):
        return "hard"
    elif t == "T7_consistency":
        # 矛盾检测: 如果发现了不一致 → hard, 否则 medium
        return "hard" if "缺失" in qa.get("answer", "") or "重复" in qa.get("answer", "") else "medium"
    else:
        return "medium"


async def gen_for_pair(pair, all_pairs=None):
    """为单个pair生成全部类型QA"""
    qas = []
    # 确定性QA(T2/T4/T5/T3/T7/T8)
    qas.extend(gen_table_factual_qa(pair))
    qas.extend(gen_tracing_qa(pair))
    qas.extend(gen_text_evidence_qa(pair))
    qas.extend(gen_counting_qa(pair))
    qas.extend(gen_consistency_check_qa(pair))      # T7矛盾检测
    if all_pairs:
        qas.extend(gen_cross_reference_qa(pair, all_pairs))  # T8跨场景
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
            "difficulty": assign_difficulty(qa),
        })
    return result


async def main(limit=None, vlm_limit=50):
    pairs = load_all_pairs()
    print(f"加载pair实例: {len(pairs)}个")
    if limit:
        pairs = pairs[:limit]

    all_pairs = pairs
    all_qa = []
    vlm_count = 0
    for i, pair in enumerate(pairs):
        # VLM调用限流(只对前vlm_limit个pair生成VLM QA)
        if vlm_count >= vlm_limit:
            pair = {**pair, "image_exists": False}  # 关闭VLM
        else:
            vlm_count += 1

        qas = await gen_for_pair(pair, all_pairs)
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
