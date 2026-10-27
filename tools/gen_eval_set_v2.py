#!/usr/bin/env python3
"""四段式合成 + 双LLM验证

阶段3: LLM改写（kimi将结构化注入改写为自然语言QA）
阶段4: 双LLM验证（kimi+claude交叉验证）

输入: data/gjb_438c/data_assets/eval_injected_v2.json
输出: data/gjb_438c/data_assets/srs_qa_v3/eval_set_v2.json
"""
import json
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
INJECTED_PATH = BASE / "data/gjb_438c/data_assets/eval_injected_v2.json"
OUT_DIR = BASE / "data/gjb_438c/data_assets/srs_qa_v3"

# API配置（已验证可用）
KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY
KIMI_MODEL = "kimi-k2.6"

WQ_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
from ai_config import WQ_API_KEY as WQ_KEY
CLAUDE_MODEL = "ep-5zazxj-1770439257299735491"

REWRITE_PROMPT = """你是SRS软件需求规格说明文档的质检专家。请根据以下注入信息，生成一个自然语言的检测问答对。

注入信息：
- 实体类型: {entity_type}
- 原始值: {original}
- 注入值: {injected}
- 注入位置: {inject_location}
- 注入方法: {method}
- 检测项: {check_item}
- 标签: {label}

要求：
1. question必须询问"图/表/文之间是否一致"
2. 不要直接说出"注入了什么"，用自然方式呈现
3. 保持军事软件需求文档的术语风格
4. answer必须与标签一致（inconsistent/consistent）
5. 如果是consistent，question应问"是否一致"，answer应说明"一致"
6. 如果是inconsistent，question应问"是否存在不一致"，answer应指出具体不一致

输出JSON格式:
{{"question": "...", "answer": "...", "reason": "简要原因"}}"""

VERIFY_PROMPT = """你是独立的SRS文档审核专家。请判断以下QA对是否正确。

问题: {question}
答案: {answer}
原因: {reason}

注入信息:
- 检测项: {check_item}
- 标签: {label}
- 注入方法: {method}
- 原始值: {original}
- 注入值: {injected}

请判断:
1. 问题是否清晰可回答？
2. 答案是否与标签一致？
3. 原因是否合理？

输出JSON: {{"agree": true/false, "reason": "简要说明"}}"""


def call_kimi(prompt, max_tokens=500, temperature=0.6):
    """调用kimi via moonshot (文本模式temperature必须=0.6)"""
    payload = {
        "model": KIMI_MODEL,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
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
                        return {"raw": content}
            time.sleep(3)
        except Exception:
            time.sleep(3)
    return None


def call_claude(prompt, max_tokens=300):
    """调用claude via wanqing"""
    payload = {
        "model": CLAUDE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
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
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # 尝试提取JSON
                        import re
                        m = re.search(r'\{[^}]+\}', content)
                        if m:
                            return json.loads(m.group())
                        return {"raw": content}
            time.sleep(3)
        except Exception:
            time.sleep(3)
    return None


def rewrite_qa(injection):
    """阶段3: LLM改写"""
    prompt = REWRITE_PROMPT.format(
        entity_type=injection.get("entity_type", ""),
        original=str(injection.get("original", ""))[:100],
        injected=str(injection.get("injected", ""))[:100],
        inject_location=injection.get("inject_location", ""),
        method=injection.get("method", ""),
        check_item=injection.get("check_item", ""),
        label=injection.get("label", ""),
    )
    return call_kimi(prompt, max_tokens=500)


def verify_qa(injection, qa):
    """阶段4: 双LLM验证"""
    # LLM 1: kimi验证
    kimi_prompt = VERIFY_PROMPT.format(
        question=qa.get("question", ""),
        answer=qa.get("answer", ""),
        reason=qa.get("reason", ""),
        check_item=injection.get("check_item", ""),
        label=injection.get("label", ""),
        method=injection.get("method", ""),
        original=str(injection.get("original", ""))[:100],
        injected=str(injection.get("injected", ""))[:100],
    )
    kimi_result = call_kimi(kimi_prompt, max_tokens=200)
    
    # LLM 2: claude验证
    claude_result = call_claude(kimi_prompt, max_tokens=200)
    
    kimi_agree = kimi_result.get("agree", False) if kimi_result else False
    claude_agree = claude_result.get("agree", False) if claude_result else False
    
    return {
        "kimi_agree": kimi_agree,
        "claude_agree": claude_agree,
        "kimi_reason": kimi_result.get("reason", "") if kimi_result else "",
        "claude_reason": claude_result.get("reason", "") if claude_result else "",
        "verified": kimi_agree and claude_agree,
        "verified_by": ["kimi", "claude"] if kimi_agree and claude_agree else [],
    }


def build_eval_entry(injection, qa, verification, idx):
    """构建评测集条目"""
    return {
        "eval_id": f"EVAL-{injection.get('check_item', 'UNKNOWN')}-{idx:04d}",
        "check_item": injection.get("check_item", ""),
        "label": injection.get("label", ""),
        "doc": injection.get("doc", ""),
        "pair_id": injection.get("pair_id", ""),
        "entity": {
            "entity_id": injection.get("entity_id", ""),
            "entity_type": injection.get("entity_type", ""),
            "occurrences": injection.get("occurrences", []),
        },
        "injection": {
            "method": injection.get("method", ""),
            "original": injection.get("original", ""),
            "injected": injection.get("injected", ""),
            "inject_location": injection.get("inject_location", ""),
            "detail": injection.get("detail", ""),
            "seed": injection.get("seed", 42),
        },
        "question": qa.get("question", ""),
        "answer": qa.get("answer", ""),
        "answer_reason": qa.get("reason", ""),
        "confidence": injection.get("confidence", "silver"),
        "verified_by": verification.get("verified_by", []),
        "verified": verification.get("verified", False),
        "z3_verified": injection.get("z3_verified", False),
        "difficulty": "easy" if injection.get("confidence") == "gold" else "medium",
    }


def main():
    print("加载注入数据...")
    with open(INJECTED_PATH, encoding="utf-8") as f:
        data = json.load(f)
    injections = data["injections"]
    print(f"  共 {len(injections)} 条注入")
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 检查已完成的
    done_path = OUT_DIR / "eval_set.jsonl"
    done_count = 0
    if done_path.exists():
        with open(done_path, encoding="utf-8") as f:
            done_count = sum(1 for _ in f)
    print(f"  已完成: {done_count}, 待处理: {len(injections) - done_count}")
    
    stats = {"total": 0, "rewritten": 0, "verified": 0, "both_agree": 0, "kimi_only": 0, "claude_only": 0, "neither": 0}
    
    with open(done_path, "a", encoding="utf-8") as fout:
        for i, injection in enumerate(injections):
            if i < done_count:
                continue
            
            stats["total"] += 1
            print(f"[{i+1}/{len(injections)}] {injection.get('method', '?')} ...", end=" ", flush=True)
            
            # 阶段3: LLM改写
            qa = rewrite_qa(injection)
            if not qa or "question" not in qa:
                print("改写失败")
                continue
            stats["rewritten"] += 1
            
            # 阶段4: 双LLM验证
            verification = verify_qa(injection, qa)
            stats["verified"] += 1
            
            if verification["kimi_agree"] and verification["claude_agree"]:
                stats["both_agree"] += 1
                print("✓ 双LLM一致", end=" ")
            elif verification["kimi_agree"]:
                stats["kimi_only"] += 1
                print("△ kimi仅", end=" ")
            elif verification["claude_agree"]:
                stats["claude_only"] += 1
                print("△ claude仅", end=" ")
            else:
                stats["neither"] += 1
                print("✗ 都不同意", end=" ")
            
            # 构建评测条目
            entry = build_eval_entry(injection, qa, verification, i)
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fout.flush()
            print(f"→ {entry['eval_id']}")
            
            time.sleep(1)  # 避免API限速
    
    print("\n=== 统计 ===")
    print(f"总数: {stats['total']}")
    print(f"改写成功: {stats['rewritten']}")
    print(f"验证完成: {stats['verified']}")
    print(f"双LLM一致: {stats['both_agree']}")
    print(f"kimi仅: {stats['kimi_only']}")
    print(f"claude仅: {stats['claude_only']}")
    print(f"都不同意: {stats['neither']}")
    
    # 汇总输出
    entries = []
    if done_path.exists():
        with open(done_path, encoding="utf-8") as f:
            for line in f:
                entries.append(json.loads(line))
    
    summary_path = OUT_DIR / "eval_set.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(entries),
            "stats": stats,
            "entries": entries,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n保存到 {summary_path} ({len(entries)} 条)")


if __name__ == "__main__":
    main()
