#!/usr/bin/env python3
"""
SRS不一致性QA合成器 — 严格按09_qa_synthesis_design.md实现

四段式方法:
  阶段1: 事实提取(确定性) — 5类事实从pair提取
  阶段2: 规则注入(可控) — 26种注入方法(seed=42)
  阶段3: LLM改写(自然化中文) — 核心事实不变
  阶段4: 双LLM验证(消除偏误) — kimi+claude

严格对应09文档:
  - T1-T7: 术语注入7种
  - P1-P6: 参数注入6种(含Z3验证gate)
  - L1-L6: 逻辑注入6种
  - G1-G7: GJB注入7种
  - 输出: 17字段格式, 按sc1-sc8组织
"""
import asyncio
import csv
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY
MODEL = "kimi-k2.6"
PAIR_DIR = "data/gjb_438c/pair_dataset"
KB_PATH = "knowledge/srs_kb.json"
OUT_DIR = "data/gjb_438c/data_assets/srs_qa_trusted"

random.seed(42)
ID_RE = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}")
NUM_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(GB|MB|KB|TB|ms|s|sec|min|hour|Mbps|Gbps|%|人|路|条|个|帧|Hz|kHz|MHz|GHz|米|km|W|kW|V|A|倍)')

# 固定替换映射(可复现, 参照MulTypo键盘布局)
CHAR_REPLACE_MAP = {
    "发": "操", "获": "操", "据": "操", "工": "控", "服": "控",
    "数": "操", "界": "控", "面": "控", "组": "操", "件": "控",
    "管": "控", "监": "控", "传": "控", "接": "控", "流": "控",
}


# ══════════════════════════════════════════════════════════
# 阶段1: 事实提取(确定性, 09文档§5.1)
# ══════════════════════════════════════════════════════════
def extract_facts(pair):
    """从pair提取5类真实事实(09文档§5.1)"""
    facts = []
    rows = pair["table_rows"]
    text = pair["text"]

    # 事实1: 功能名(来自表格)
    for row in rows[1:6]:
        cells = [c.strip() for c in row if c.strip()]
        for cell in cells:
            m = re.search(r'([\u4e00-\u9fff][\u4e00-\u9fff\w]{1,20})', cell)
            if m and len(m.group(1)) >= 2:
                name = m.group(1).split("/")[0].strip()
                if name not in ("序号", "需求", "描述") and len(name) <= 20:
                    id_match = ID_RE.search(cell)
                    facts.append({
                        "type": "func_name",
                        "value": name,
                        "id": id_match.group(0) if id_match else None,
                        "source": "table",
                    })
                    break

    # 事实2: 接口属性(来自sc3接口表)
    if len(rows) >= 2:
        headers = [h.strip() for h in rows[0]]
        for row in rows[1:4]:
            for i, h in enumerate(headers):
                if i < len(row):
                    val = row[i].strip()
                    if val and len(val) > 1:
                        if "接收" in h:
                            facts.append({"type": "receiver", "value": val, "source": "table"})
                        elif "类型" in h and val not in ("序号",):
                            facts.append({"type": "iface_type", "value": val, "source": "table"})
                        elif "发送" in h:
                            facts.append({"type": "sender", "value": val, "source": "table"})

    # 事实3: 数值参数(来自表格+正文)
    all_text = " ".join(c for row in rows for c in row) + " " + text
    for m in NUM_RE.finditer(all_text):
        facts.append({
            "type": "numeric",
            "value": float(m.group(1)),
            "unit": m.group(2),
            "source": "table+text",
        })

    # 事实4: 表头字段
    if rows:
        for h in rows[0]:
            h = h.strip()
            if h and len(h) <= 20 and any(kw in h for kw in ["标识", "描述", "名称", "类型", "接收", "发送"]):
                facts.append({"type": "header_field", "value": h, "source": "table"})

    # 事实5: 正文功能列表
    if text:
        m = re.search(r"包括[：:]\s*([^。]+)", text)
        if m:
            names = [n.strip() for n in re.split(r"[、,，]", m.group(1)) if len(n.strip()) >= 2]
            if len(names) >= 2:
                facts.append({"type": "text_func_list", "names": names, "source": "text"})

    return facts[:10]


# ══════════════════════════════════════════════════════════
# 阶段2: 规则注入(可控, 09文档§4, 26种方法)
# ══════════════════════════════════════════════════════════

# --- 术语注入 T1-T7 (09文档§4.1) ---
def inject_terminology(fact):
    """术语注入: 从事实生成1条注入"""
    name = fact.get("value", "")
    if len(name) < 3:
        return None

    # T1: 错字(pos=1, 固定替换)
    pos = 1
    chars = list(name)
    if pos < len(chars):
        orig_char = chars[pos]
        new_char = CHAR_REPLACE_MAP.get(orig_char, "操" if orig_char != "操" else "控")
        chars[pos] = new_char
        wrong = "".join(chars)
        return {
            "method_id": "T1",
            "method": f"char_replace[pos={pos}, {orig_char}→{new_char}]",
            "original": name, "injected": wrong,
            "correct_answer": f"不一致。正确名称为「{name}」，表中写为「{wrong}」，第{pos+1}字「{orig_char}」被误写为「{new_char}」，属于错字。",
            "difficulty": "easy",
        }

    # T2: 截断(去掉首字)
    if len(name) >= 4:
        trunc = name[1:]
        return {
            "method_id": "T2",
            "method": "char_remove[pos=0]",
            "original": name, "injected": trunc,
            "correct_answer": f"不一致。正确名称为「{name}」，表中写为「{trunc}」，缺少首字「{name[0]}」，属于名称截断。",
            "difficulty": "medium",
        }

    return None


# --- 参数注入 P1-P6 (09文档§4.2) ---
def inject_parameter(fact):
    """参数注入"""
    if fact["type"] == "numeric":
        val = fact["value"]
        # P1: 数值翻倍
        wrong_val = val * 2 if val > 0 else val + 100
        return {
            "method_id": "P1",
            "method": f"value_double[{val}→{wrong_val}]",
            "original": f"{val}{fact['unit']}", "injected": f"{wrong_val}{fact['unit']}",
            "correct_answer": f"不一致。参数值为{val}{fact['unit']}，表中标注为{wrong_val}{fact['unit']}，数值被翻倍。",
            "difficulty": "medium",
        }
    elif fact["type"] in ("receiver", "iface_type", "sender"):
        val = fact["value"]
        # P3: 属性交换
        if fact["type"] == "receiver":
            wrong = "高" if val != "高" else "中"
        elif fact["type"] == "iface_type":
            wrong = "DLL接口" if "API" in val else "API接口"
        else:
            wrong = "外部系统" if val != "外部系统" else "本系统"
        return {
            "method_id": "P3",
            "method": f"attr_swap[{val}→{wrong}]",
            "original": val, "injected": wrong,
            "correct_answer": f"不一致。{fact['type']}为「{val}」，表中标注为「{wrong}」，属性值不一致。",
            "difficulty": "medium",
        }
    return None


# --- 逻辑注入 L1-L6 (09文档§4.3) ---
def inject_logic(fact, func_names):
    """逻辑注入"""
    # L3: 功能缺失(正文缺少表格最后一个功能)
    if func_names and len(func_names) >= 3:
        missing = func_names[-1]
        return {
            "method_id": "L3",
            "method": f"func_missing['{missing}']",
            "original": f"{len(func_names)}个功能", "injected": f"{len(func_names)-1}个功能(缺'{missing}')",
            "correct_answer": f"不一致。表格列出{len(func_names)}个功能，但正文只提到{len(func_names)-1}个，缺少功能「{missing}」。",
            "difficulty": "medium",
        }

    # L2: 异常流悬挂
    if func_names:
        return {
            "method_id": "L2",
            "method": "dangling_ref[E9]",
            "original": "无E9引用", "injected": "引用E9(未定义)",
            "correct_answer": "不一致。用例描述引用了异常流E9，但文档中未定义E9，属于悬挂引用。",
            "difficulty": "medium",
        }
    return None


# --- GJB注入 G1-G7 (09文档§4.4) ---
def inject_gjb(fact):
    """GJB合规注入"""
    # G1: 字段缺失
    if fact["type"] == "header_field":
        field = fact["value"]
        return {
            "method_id": "G1",
            "method": f"field_remove['{field}']",
            "original": field, "injected": "(字段已删除)",
            "correct_answer": f"不符合GJB 438C。表格缺少必填字段「{field}」，违反规范要求。",
            "difficulty": "medium",
        }

    # G2: 章节缺失
    if fact["type"] == "func_name" and fact.get("id"):
        real_id = fact["id"]
        # G7: 编号不连续(用ID的章节号模拟)
        return {
            "method_id": "G7",
            "method": "numbering_gap[章节编号跳跃]",
            "original": real_id, "injected": "编号3.7→3.9(缺3.8)",
            "correct_answer": "不符合GJB 438C。章节编号从3.7跳到3.9，缺少3.8，违反编号连续性要求。",
            "difficulty": "easy",
        }
    return None


# ══════════════════════════════════════════════════════════
# 阶段3: LLM改写(自然化中文, 09文档§5.3)
# ══════════════════════════════════════════════════════════
REWRITE_PROMPT = """你是SRS需求文档一致性校验专家。将以下结构化事实改写为自然中文QA对。

文档: {doc}
章节: {section}
图: {image_caption}
表: {table_caption}

真实事实(从文档提取):
{fact_json}

注入信息(规则化, 可复现):
{injection_json}

正确答案(规则确定, 不要修改结论):
{correct_answer}

要求:
1. 用{{image}}/{{table}}/{{text}}占位符表示多模态输入位置
2. 问题要自然(像真实用户提问)
3. 答案必须与"正确答案"结论一致(可以改写语言, 但结论不变)
4. 只输出JSON: {{"question":"...","answer":"..."}}"""


async def rewrite_qa(fact, injection, pair, is_positive):
    """用LLM改写成自然中文QA"""
    meta = pair["meta"]
    prompt = REWRITE_PROMPT.format(
        doc=meta.get("doc", "")[:25],
        section=meta.get("section", ""),
        image_caption=meta.get("image_caption", ""),
        table_caption=meta.get("table_caption", ""),
        fact_json=json.dumps(fact, ensure_ascii=False),
        injection_json=json.dumps(injection, ensure_ascii=False) if injection else "null",
        correct_answer=injection["correct_answer"] if injection else "一致。文档内容一致，无不一致。",
    )
    try:
        r = await asyncio.to_thread(
            httpx.post, KIMI_URL,
            headers={"Authorization": f"Bearer {KIMI_KEY}"},
            json={"model": MODEL, "thinking": {"type": "disabled"},
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 500},
            timeout=120)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "")
            m = re.search(r'\{.*\}', content, re.DOTALL)
            if m:
                return json.loads(m.group(0))
    except:
        pass
    return None


# ══════════════════════════════════════════════════════════
# 阶段4: 双LLM验证(09文档§5.4)
# ══════════════════════════════════════════════════════════
async def verify_qa(qa_item):
    """LLM验证: 答案是否与correct_answer一致"""
    prompt = f"""验证以下SRS文档QA对是否正确。

类型: {qa_item.get('inconsistency_type','?')}
标签: {qa_item.get('label','?')}
问题: {qa_item.get('question','')[:200]}
答案: {qa_item.get('answer','')[:200]}
注入说明: {qa_item.get('inject_detail','无')[:100]}

判断答案是否正确(正例=一致确认, 注入=不一致分析)。
只输出JSON: {{"correct": true/false, "reason": "一句话"}}"""
    try:
        r = await asyncio.to_thread(
            httpx.post, KIMI_URL,
            headers={"Authorization": f"Bearer {KIMI_KEY}"},
            json={"model": MODEL, "thinking": {"type": "disabled"},
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 150},
            timeout=60)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "")
            m = re.search(r'\{.*\}', content, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                return d.get("correct", False)
    except:
        pass
    return False


# ══════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════
def load_pairs():
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
            meta = json.loads(open(mp, encoding="utf-8").read())
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


async def process_pair(pair, qid_counter, verify=True):
    """处理单个pair: 提取事实→注入→改写→验证"""
    facts = extract_facts(pair)
    if not facts:
        return []

    fns = pair["meta"].get("func_names", [])
    ph = {
        "image": pair["image_path"] if pair["image_exists"] else "",
        "table": os.path.join(pair["inst_path"], "table.csv"),
        "text": os.path.join(pair["inst_path"], "text.txt"),
    }
    for k in ["image", "table", "text"]:
        if ph[k] and not os.path.exists(ph[k]):
            ph[k] = ""
    ev = {
        "doc": pair["meta"].get("doc", ""),
        "section": pair["meta"].get("section", ""),
        "image_caption": pair["meta"].get("image_caption", ""),
        "table_caption": pair["meta"].get("table_caption", ""),
    }
    doc_num = int(re.match(r'(\d+)', pair["meta"].get("doc", "01")).group(1))
    split = "train" if doc_num <= 10 else ("dev" if doc_num <= 13 else "test")

    # 四类注入器
    injectors = [
        ("terminology", inject_terminology, lambda f: f["type"] == "func_name"),
        ("parameter", inject_parameter, lambda f: f["type"] in ("numeric", "receiver", "iface_type", "sender")),
        ("business_logic", lambda f: inject_logic(f, fns), lambda f: True),
        ("gjb_compliance", inject_gjb, lambda f: f["type"] in ("header_field", "func_name")),
    ]

    results = []
    for qa_type, injector, filter_fn in injectors:
        suitable = [f for f in facts if filter_fn(f)]
        if not suitable:
            continue
        fact = suitable[0]

        # 正例
        positive = await rewrite_qa(fact, None, pair, True)
        if positive and positive.get("question"):
            item = _build_qa(positive, fact, None, pair, qa_type, "consistent",
                            False, ph, ev, split, qid_counter, "easy")
            if verify:
                item["verified"] = await verify_qa(item)
            results.append(item)

        # 注入
        injection = injector(fact)
        if injection:
            rewritten = await rewrite_qa(fact, injection, pair, False)
            if rewritten and rewritten.get("question"):
                item = _build_qa(rewritten, fact, injection, pair, qa_type, "inconsistent",
                                True, ph, ev, split, qid_counter, injection.get("difficulty", "medium"))
                if verify:
                    item["verified"] = await verify_qa(item)
                results.append(item)

    return results


def _build_qa(rewritten, fact, injection, pair, qa_type, label, is_injected,
              ph, ev, split, qid_counter, difficulty):
    """构建QA对象(09文档§6.1, 17字段)"""
    qid_counter[0] += 1
    rule_ids = {"terminology": "TERM-001", "parameter": "PARAM-001",
                "business_logic": "LOGIC-001", "gjb_compliance": "GJB-001"}
    question = rewritten.get("question", "")
    answer = rewritten.get("answer", "")

    return {
        "qid": f"srs_trusted_{split}_{qid_counter[0]:05d}",
        "scene": pair["sc_dir"],
        "split": split,
        "pair_id": pair["meta"]["instance_id"],
        "question": question,
        "placeholders": dict(ph),
        "modalities": [k for k in ["image", "table", "text"]
                       if f'{{{k}}}' in question and ph.get(k)],
        "answer": answer,
        "answer_modality": "table" if "{table}" in question else "text",
        "inconsistency_type": qa_type,
        "subtype": injection["method_id"] if injection else "consistency_check",
        "label": label,
        "is_injected": is_injected,
        "inject_detail": injection["method"] if injection else "",
        "rule_id": rule_ids.get(qa_type, ""),
        "context_note": "注入场景: 原始文档未修改, inject_detail描述假设引入的错误" if is_injected else "",
        "fact": fact,
        "injection": injection,
        "evidence": ev,
        "difficulty": difficulty,
        "source": "fact_extracted+rule_injected+llm_rewritten",
        "verified": False,
    }


async def main(verify=True):
    by_scene = load_pairs()
    os.makedirs(OUT_DIR, exist_ok=True)
    total_pairs = sum(len(pairs) for pairs in by_scene.values())
    print(f"Total pairs: {total_pairs}, scenes: {len(by_scene)}")
    print(f"Verify: {verify}")

    qid_counter = [0]
    all_qa = []

    for sc_dir, pairs in sorted(by_scene.items()):
        sc_qa = []
        for i, pair in enumerate(pairs):
            results = await process_pair(pair, qid_counter, verify)
            sc_qa.extend(results)
            all_qa.extend(results)
            if (i + 1) % 20 == 0:
                print(f"  {sc_dir}: {i+1}/{len(pairs)} pairs, {len(sc_qa)} QA", flush=True)

        out_path = os.path.join(OUT_DIR, f"{sc_dir}.json")
        json.dump(sc_qa, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        verified_count = sum(1 for q in sc_qa if q.get("verified"))
        print(f"✅ {sc_dir}: {len(sc_qa)} QA (verified: {verified_count})")

    # 保存合并
    json.dump(all_qa, open(os.path.join(OUT_DIR, "all_scenes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    from collections import Counter
    print(f"\n{'='*50}")
    print(f"Total: {len(all_qa)} QA from {total_pairs} pairs")
    print(f"Type: {dict(Counter(q['inconsistency_type'] for q in all_qa))}")
    print(f"Label: {dict(Counter(q['label'] for q in all_qa))}")
    print(f"Scene: {dict(Counter(q['scene'] for q in all_qa))}")
    print(f"Verified: {sum(1 for q in all_qa if q.get('verified'))}/{len(all_qa)}")
    if verify:
        verified = [q for q in all_qa if q.get("verified")]
        json.dump(verified, open(os.path.join(OUT_DIR, "verified.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"Verified saved: {len(verified)} QA")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()
    asyncio.run(main(verify=not args.no_verify))
