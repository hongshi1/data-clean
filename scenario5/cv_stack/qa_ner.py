"""L3: QA文本语义解析 — 基于Qwen2.5-1.5B-Instruct的NER与关系抽取.

替代关键词匹配，用小模型做结构化抽取：
  实体(who) + 属性(what state) + 关系(predicate) + 否定 + 逻辑连接词.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_QWEN_DIR = ROOT / "models" / "qwen2.5-1.5b-instruct"

_MODEL = None
_TOKENIZER = None


def _load_model():
    global _MODEL, _TOKENIZER
    if _MODEL is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        _TOKENIZER = AutoTokenizer.from_pretrained(
            str(_QWEN_DIR), local_files_only=True, trust_remote_code=True
        )
        _MODEL = AutoModelForCausalLM.from_pretrained(
            str(_QWEN_DIR),
            local_files_only=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else "cpu",
        )
    return _MODEL, _TOKENIZER


NER_PROMPT = """从安全监控QA文本中提取实体和关系。

例1：
输入：判断图片中是否有人员未佩戴安全帽
输出：{"entities":[{"name":"人员","type":"person","spatial_ref":"none"},{"name":"安全帽","type":"helmet","spatial_ref":"none"}],"relations":[{"subject":"人员","predicate":"佩戴","object":"安全帽","negated":true}],"person_scope":"specific"}

例2：
输入：画面中所有工人是否都戴着安全帽？
输出：{"entities":[{"name":"工人","type":"person","spatial_ref":"none"},{"name":"安全帽","type":"helmet","spatial_ref":"none"}],"relations":[{"subject":"工人","predicate":"佩戴","object":"安全帽","negated":false}],"person_scope":"all"}

例3：
输入：左侧人员趴在桌上，未戴安全帽
输出：{"entities":[{"name":"左侧人员","type":"person","spatial_ref":"left"},{"name":"安全帽","type":"helmet","spatial_ref":"none"},{"name":"桌上","type":"workstation","spatial_ref":"none"}],"relations":[{"subject":"左侧人员","predicate":"佩戴","object":"安全帽","negated":true},{"subject":"左侧人员","predicate":"趴在","object":"桌上","negated":false}],"person_scope":"specific"}

现在请处理：
指令：{user_text}
回答：{gpt_text}

只输出JSON，格式与上面例子相同。"""


def extract_semantics(user_text: str, gpt_text: str) -> dict[str, Any]:
    """用Qwen2.5-1.5B从QA文本中抽取结构化语义信息."""
    model, tokenizer = _load_model()
    import torch

    prompt = NER_PROMPT.replace("{user_text}", user_text).replace("{gpt_text}", gpt_text)
    messages = [
        {"role": "system", "content": "你只输出JSON格式的实体关系抽取结果。"},
        {"role": "user", "content": prompt},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    # Parse JSON from response
    parsed = _parse_json(response)
    if parsed is None:
        parsed = _fallback_parse(user_text, gpt_text)

    # Post-process: fix negation if NER missed it
    _fix_negation(parsed, user_text + " " + gpt_text)

    return {
        "method": "qwen2.5-1.5b-ner",
        "model_response": response[:500],
        "parsed": parsed,
        "user_text": user_text,
        "gpt_text": gpt_text,
    }


NEGATION_KEYWORDS = ["未佩戴", "没有佩戴", "未戴", "没有戴", "无", "没有"]


def _fix_negation(parsed: dict, source_text: str) -> None:
    """If source text has negation but NER output has negated=False, correct it."""
    has_negation = any(k in source_text for k in NEGATION_KEYWORDS)
    if not has_negation:
        return
    for rel in parsed.get("relations", []):
        if rel.get("negated") is False and rel.get("predicate") in ("佩戴", "穿戴", "戴着"):
            for neg_kw in NEGATION_KEYWORDS:
                if neg_kw in source_text:
                    rel["negated"] = True
                    rel["negation_fixed"] = True
                    break


def _parse_json(text: str) -> dict[str, Any] | None:
    """Try to extract a valid JSON object from the model output."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match is None:
        return None
    try:
        obj = json.loads(match.group())
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    cleaned = match.group().replace("'", '"')
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    return None


def _fallback_parse(user_text: str, gpt_text: str) -> dict[str, Any]:
    """Regex fallback when JSON parsing fails."""
    combined = user_text + " " + gpt_text
    entities = []
    relations = []

    if "人员" in combined or "工人" in combined:
        entities.append({"name": "人员", "type": "person", "spatial_ref": "none"})
    if "安全帽" in combined or "头盔" in combined:
        entities.append({"name": "安全帽", "type": "helmet", "spatial_ref": "none"})
    if "工位" in combined or "工作台" in combined:
        entities.append({"name": "工位", "type": "workstation", "spatial_ref": "none"})

    if "未佩戴" in combined or "没有佩戴" in combined or "未戴" in combined:
        relations.append({"subject": "人员", "predicate": "佩戴", "object": "安全帽", "negated": True})
    elif "佩戴" in combined or "戴着" in combined:
        relations.append({"subject": "人员", "predicate": "佩戴", "object": "安全帽", "negated": False})

    spatial = "none"
    if "左侧" in combined:
        spatial = "left"
    elif "右侧" in combined:
        spatial = "right"

    return {
        "entities": entities,
        "attributes": [],
        "relations": relations,
        "logical_connectives": ["并"] if "并" in combined else [],
        "scene_conditions": ["工位"] if "工位" in combined else [],
        "person_scope": "all" if "所有" in combined or "全员" in combined else "specific",
        "spatial_ref": spatial,
    }
