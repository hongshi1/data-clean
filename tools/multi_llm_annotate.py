#!/usr/bin/env python3
"""多LLM独立标注

让3个LLM独立对评测集进行标注:
  - LLM 1: kimi-k2.6 via moonshot
  - LLM 2: claude via wanqing
  - LLM 3: GLM-5 via wanqing

关键: 不告诉LLM注入信息(method/original/injected/label)
只给: question + occurrences(实体多位置内容)
LLM独立判断: consistent/inconsistent

输出:
  1. 每个LLM与gold label的Accuracy
  2. LLM间Cohen's κ(两两)
  3. 多数投票结果
  4. Fleiss' κ(3人一致性)
"""
import json
import time
import re
from pathlib import Path
from collections import Counter

import httpx

BASE = Path(__file__).resolve().parent.parent
EVAL_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
OUT_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/multi_llm_annotations.json"
PROGRESS_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/multi_llm_progress.jsonl"

# API配置
KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
KIMI_MODEL = "kimi-k2.6"

WQ_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
WQ_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
CLAUDE_MODEL = "ep-5zazxj-1770439257299735491"
GLM_MODEL = "ep-glsztk-1778496696841467392"

# 标注prompt（不含注入信息！）
ANNOTATE_PROMPT = """你是SRS软件需求规格说明文档的质检专家。

以下是一个软件功能/实体在文档中多个位置的记录：

功能ID: {entity_id}
实体类型: {entity_type}
位置记录:
{occurrences_text}

问题: {question}

请独立判断这些位置之间是否存在不一致（同一实体在不同位置用了不同的名称/数值/属性）。
注意: 不要受问题中暗示的影响，请基于位置记录的内容独立做出判断。

输出JSON: {{"verdict": "consistent"或"inconsistent", "reason": "简要原因(50字内)"}}"""


def format_occurrences(occurrences, injection=None):
    """格式化occurrences为文本（应用注入修改）"""
    import copy
    occs = copy.deepcopy(occurrences)
    
    # 应用注入：把injected值替换到对应位置
    if injection and injection.get("method", "") != "positive":
        inject_location = injection.get("inject_location", "")
        injected_value = injection.get("injected", "")
        original_value = injection.get("original", "")
        
        # 找到对应位置的occurrence并替换
        replaced = False
        for occ in occs:
            if occ.get("location") == inject_location:
                if isinstance(occ.get("content"), str) and isinstance(injected_value, str):
                    if original_value and original_value in occ["content"]:
                        occ["content"] = occ["content"].replace(str(original_value), str(injected_value), 1)
                    elif str(original_value) == str(occ.get("content")):
                        occ["content"] = injected_value
                elif isinstance(occ.get("content"), list) and isinstance(injected_value, list):
                    occ["content"] = injected_value
                elif isinstance(occ.get("content"), dict) and isinstance(injected_value, dict):
                    occ["content"] = injected_value
                replaced = True
                break
        
        # 如果找不到对应location，替换第一个occurrence
        if not replaced and occs:
            occ = occs[0]
            if isinstance(occ.get("content"), str) and isinstance(injected_value, str):
                if str(original_value) == str(occ.get("content")):
                    occ["content"] = injected_value
                elif original_value and str(original_value) in str(occ.get("content", "")):
                    occ["content"] = str(occ["content"]).replace(str(original_value), str(injected_value), 1)
            elif isinstance(injected_value, list) and isinstance(occ.get("content"), list):
                occ["content"] = injected_value
            elif isinstance(injected_value, dict) and isinstance(occ.get("content"), dict):
                occ["content"] = injected_value
    
    lines = []
    for i, occ in enumerate(occs[:5]):  # 最多5个位置
        location = occ.get("location", "")
        section = occ.get("section", "")
        content = occ.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        elif isinstance(content, list):
            content = " → ".join(str(c) for c in content)
        lines.append(f"  位置{i+1}: [{location}] 章节{section}: {content}")
    return "\n".join(lines)


def call_kimi(prompt):
    """调用kimi via moonshot"""
    payload = {
        "model": KIMI_MODEL,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(3):
        try:
            r = httpx.post(KIMI_URL,
                headers={"Authorization": f"Bearer {KIMI_KEY}", "Content-Type": "application/json"},
                json=payload, timeout=60)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"].get("content", "")
                if content:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        m = re.search(r'"verdict"\s*:\s*"(consistent|inconsistent)"', content)
                        if m:
                            return {"verdict": m.group(1), "reason": content[:100]}
            time.sleep(3)
        except Exception:
            time.sleep(3)
    return None


def call_wanqing(prompt, model):
    """调用wanqing API (claude或glm)"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.1,
    }
    for attempt in range(3):
        try:
            r = httpx.post(WQ_URL,
                headers={"Authorization": f"Bearer {WQ_KEY}", "Content-Type": "application/json"},
                json=payload, timeout=60)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"].get("content", "")
                if content:
                    # 清理markdown标记
                    clean = content.strip()
                    if clean.startswith("```"):
                        # 去掉 ```json 或 ``` 开头
                        lines = clean.split("\n")
                        if len(lines) > 1:
                            clean = "\n".join(lines[1:])
                        if clean.endswith("```"):
                            clean = clean[:-3].strip()
                    try:
                        return json.loads(clean)
                    except json.JSONDecodeError:
                        m = re.search(r'"verdict"\s*:\s*"(consistent|inconsistent)"', content)
                        if m:
                            return {"verdict": m.group(1), "reason": content[:100]}
                        if "inconsistent" in content.lower():
                            return {"verdict": "inconsistent", "reason": content[:100]}
                        elif "consistent" in content.lower():
                            return {"verdict": "consistent", "reason": content[:100]}
            time.sleep(3)
        except Exception:
            time.sleep(3)
    return None


def cohen_kappa(annotations1, annotations2):
    """计算Cohen's κ"""
    # 只比较两个标注者都有标注的条目
    pairs = [(a1, a2) for a1, a2 in zip(annotations1, annotations2) if a1 and a2]
    if len(pairs) < 2:
        return 0.0
    
    n = len(pairs)
    labels = set(p[0] for p in pairs) | set(p[1] for p in pairs)
    
    # 混淆矩阵
    matrix = Counter(pairs)
    
    # 观察一致性
    po = sum(matrix[(l, l)] for l in labels) / n
    
    # 期望一致性
    marg1 = Counter(a1 for a1, a2 in pairs)
    marg2 = Counter(a2 for a1, a2 in pairs)
    pe = sum((marg1[l] / n) * (marg2[l] / n) for l in labels)
    
    if pe == 1.0:
        return 1.0
    
    return (po - pe) / (1 - pe)


def fleiss_kappa(annotations):
    """计算Fleiss' κ (多标注者)
    annotations: list of list, 每个条目有多个标注者的标注
    """
    n = len(annotations)  # 条目数
    if n == 0:
        return 0.0
    
    categories = set()
    for anns in annotations:
        for a in anns:
            if a:
                categories.add(a)
    categories = sorted(categories)
    k = len(categories)
    if k < 2:
        return 1.0
    
    cat_idx = {c: i for i, c in enumerate(categories)}
    
    # 构建矩阵
    matrix = []
    for anns in annotations:
        row = [0] * k
        valid = [a for a in anns if a]
        n_raters = len(valid)
        if n_raters == 0:
            continue
        for a in valid:
            row[cat_idx[a]] += 1
        matrix.append((row, n_raters))
    
    if not matrix:
        return 0.0
    
    N = len(matrix)
    n_raters = matrix[0][1]  # 假设每个条目的标注者数相同
    
    # P_i (每条的标注一致性)
    P_i = []
    for row, n_r in matrix:
        P_i.append((sum(c * c for c in row) - n_r) / (n_r * (n_r - 1))) if n_r > 1 else P_i.append(0)
    
    P_bar = sum(P_i) / N  # 平均标注一致性
    
    # p_j (每个类别的边际比例)
    p_j = []
    for j in range(k):
        total = sum(row[j] for row, n_r in matrix)
        p_j.append(total / (N * n_raters))
    
    Pe = sum(p * p for p in p_j)  # 期望一致性
    
    if Pe == 1.0:
        return 1.0
    
    return (P_bar - Pe) / (1 - Pe)


def main():
    print("加载评测集...")
    with open(EVAL_PATH) as f:
        data = json.load(f)
    entries = data["entries"]
    print(f"  共 {len(entries)} 条")

    # 检查已完成的进度
    done = {}
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done[rec["eval_id"]] = rec
                except Exception:
                    pass
    print(f"  已完成: {len(done)}, 待处理: {len(entries) - len(done)}")

    # 标注
    annotations = []  # 每条: {eval_id, gold, kimi, claude, glm}
    
    with open(PROGRESS_PATH, "a", encoding="utf-8") as fout:
        for i, entry in enumerate(entries):
            eval_id = entry["eval_id"]
            gold = entry["label"]
            
            if eval_id in done:
                annotations.append(done[eval_id])
                continue
            
            # 构建prompt（不含注入信息！但occurrences是注入后的）
            occurrences = entry.get("entity", {}).get("occurrences", [])
            injection = entry.get("injection", {})
            occ_text = format_occurrences(occurrences, injection)
            
            prompt = ANNOTATE_PROMPT.format(
                entity_id=entry.get("entity", {}).get("entity_id", ""),
                entity_type=entry.get("entity", {}).get("entity_type", ""),
                occurrences_text=occ_text,
                question=entry.get("question", ""),
            )
            
            print(f"[{i+1}/{len(entries)}] {eval_id} ...", end=" ", flush=True)
            
            # 3个LLM独立标注（GLM返回空，改用kimi-wanqing作为第三LLM）
            kimi_result = call_kimi(prompt)
            claude_result = call_wanqing(prompt, CLAUDE_MODEL)
            glm_result = call_wanqing(prompt, "ep-0dkcs8-1777515852343838800")  # kimi via wanqing作为第三LLM
            
            kimi_verdict = kimi_result.get("verdict", "") if kimi_result else ""
            claude_verdict = claude_result.get("verdict", "") if claude_result else ""
            glm_verdict = glm_result.get("verdict", "") if glm_result else ""
            
            # 多数投票
            verdicts = [v for v in [kimi_verdict, claude_verdict, glm_verdict] if v]
            if verdicts:
                majority = Counter(verdicts).most_common(1)[0][0]
            else:
                majority = ""
            
            record = {
                "eval_id": eval_id,
                "gold": gold,
                "check_item": entry.get("check_item", ""),
                "kimi": kimi_verdict,
                "claude": claude_verdict,
                "glm": glm_verdict,
                "majority": majority,
                "kimi_reason": kimi_result.get("reason", "") if kimi_result else "",
                "claude_reason": claude_result.get("reason", "") if claude_result else "",
                "glm_reason": glm_result.get("reason", "") if glm_result else "",
            }
            annotations.append(record)
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            fout.flush()
            
            agree = sum(1 for v in [kimi_verdict, claude_verdict, glm_verdict] if v == gold)
            print(f"kimi={kimi_verdict[:4]} claude={claude_verdict[:4]} glm={glm_verdict[:4]} gold={gold[:4]} agree={agree}/3")
            
            time.sleep(1)

    # ========== 统计分析 ==========
    print("\n" + "=" * 60)
    print("多LLM标注结果分析")
    print("=" * 60)

    # 1. 每个LLM与gold的Accuracy
    for llm_name in ["kimi", "claude", "glm", "majority"]:
        correct = sum(1 for a in annotations if a.get(llm_name) and a[llm_name] == a["gold"])
        total = sum(1 for a in annotations if a.get(llm_name))
        acc = correct / total if total > 0 else 0
        print(f"\n{llm_name} vs Gold:")
        print(f"  正确: {correct}/{total} ({acc:.2%})")

    # 2. 混淆矩阵（每个LLM vs gold）
    for llm_name in ["kimi", "claude", "glm"]:
        tp = fp = fn = tn = 0
        for a in annotations:
            if not a.get(llm_name):
                continue
            gold = a["gold"]
            pred = a[llm_name]
            if gold == "inconsistent" and pred == "inconsistent":
                tp += 1
            elif gold == "consistent" and pred == "inconsistent":
                fp += 1
            elif gold == "inconsistent" and pred == "consistent":
                fn += 1
            else:
                tn += 1
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        print(f"\n{llm_name} 检测性能:")
        print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
        print(f"  P={p:.4f} R={r:.4f} F1={f1:.4f}")

    # 3. LLM间Cohen's κ
    kimi_anns = [a.get("kimi", "") for a in annotations]
    claude_anns = [a.get("claude", "") for a in annotations]
    glm_anns = [a.get("glm", "") for a in annotations]
    
    k_c = cohen_kappa(kimi_anns, claude_anns)
    k_g = cohen_kappa(kimi_anns, glm_anns)
    c_g = cohen_kappa(claude_anns, glm_anns)
    
    print(f"\nLLM间Cohen's κ:")
    print(f"  kimi vs claude: κ={k_c:.4f}")
    print(f"  kimi vs glm:    κ={k_g:.4f}")
    print(f"  claude vs glm:  κ={c_g:.4f}")
    print(f"  平均: κ={((k_c + k_g + c_g) / 3):.4f}")

    # 4. Fleiss' κ (3人一致性)
    fleiss_data = [[a.get("kimi", ""), a.get("claude", ""), a.get("glm", "")] for a in annotations]
    fk = fleiss_kappa(fleiss_data)
    print(f"\nFleiss' κ (3人一致性): {fk:.4f}")

    # 5. 多数投票 vs gold
    majority_correct = sum(1 for a in annotations if a.get("majority") and a["majority"] == a["gold"])
    majority_total = sum(1 for a in annotations if a.get("majority"))
    print(f"\n多数投票 vs Gold: {majority_correct}/{majority_total} ({majority_correct/majority_total:.2%})")

    # 6. 三人全一致 vs gold
    all_agree = sum(1 for a in annotations 
                    if a.get("kimi") and a.get("claude") and a.get("glm") 
                    and a["kimi"] == a["claude"] == a["glm"])
    all_agree_correct = sum(1 for a in annotations 
                           if a.get("kimi") and a.get("claude") and a.get("glm") 
                           and a["kimi"] == a["claude"] == a["glm"] == a["gold"])
    print(f"\n三人全一致: {all_agree}/{len(annotations)} ({all_agree/len(annotations):.2%})")
    if all_agree > 0:
        print(f"  其中与gold一致: {all_agree_correct}/{all_agree} ({all_agree_correct/all_agree:.2%})")

    # 保存完整结果
    output = {
        "total": len(annotations),
        "summary": {
            "kimi_accuracy": sum(1 for a in annotations if a.get("kimi") and a["kimi"] == a["gold"]) / max(1, sum(1 for a in annotations if a.get("kimi"))),
            "claude_accuracy": sum(1 for a in annotations if a.get("claude") and a["claude"] == a["gold"]) / max(1, sum(1 for a in annotations if a.get("claude"))),
            "glm_accuracy": sum(1 for a in annotations if a.get("glm") and a["glm"] == a["gold"]) / max(1, sum(1 for a in annotations if a.get("glm"))),
            "majority_accuracy": majority_correct / max(1, majority_total),
            "cohen_kappa_kimi_claude": round(k_c, 4),
            "cohen_kappa_kimi_glm": round(k_g, 4),
            "cohen_kappa_claude_glm": round(c_g, 4),
            "fleiss_kappa": round(fk, 4),
            "all_three_agree": all_agree,
            "all_three_agree_rate": round(all_agree / len(annotations), 4),
        },
        "annotations": annotations,
    }
    
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, ensure_ascii=False, indent=2)
    
    print(f"\n完整结果保存到 {OUT_PATH}")


if __name__ == "__main__":
    main()
