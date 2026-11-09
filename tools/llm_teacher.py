"""Training-time LLM teacher client (distillation-only, exact old-cache-key
compatible so historical GLM-5.3 responses are reused without new calls).

This module is for OFFLINE TRAINING DATA GENERATION ONLY. The inference-time
algorithm (algorithms/) stays pure-local — this file lives in tools/ and is
never imported by algorithms/. Cache keys replicate the pre-M66
algorithms/common/llm_client.py formula byte-for-byte so the 12914-entry
historical cache (data/gjb_438c/llm_cache/llm_cache.jsonl) is hit whenever
the same prompt is rebuilt.

Hard rules honored: keys only via tools/ai_config (zero literals), utf-8
everywhere, failures raise (never silent).
"""
from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
_TOOLS = BASE / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from ai_config import GLM_KEY, GLM_URL  # noqa: E402

CACHE_DIR = BASE / "data/gjb_438c/llm_cache"
_cache_index: dict[str, dict] | None = None
_store_lock = threading.Lock()


def _load_cache() -> dict[str, dict]:
    global _cache_index
    if _cache_index is None:
        _cache_index = {}
        p = CACHE_DIR / "llm_cache.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                    _cache_index[rec["k"]] = rec
                except (json.JSONDecodeError, KeyError):
                    continue
    return _cache_index


def _cache_key(prefer: str, msgs: list[dict], max_tokens: int,
               temperature: float) -> str:
    canon = json.dumps({"prefer": prefer, "msgs": msgs,
                        "max_tokens": max_tokens, "temperature": temperature},
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:20]


def _store(ck: str, content: str, model: str) -> None:
    idx = _load_cache()
    rec = {"k": ck, "model": model, "content": content,
           "ts": round(time.time(), 1)}
    idx[ck] = rec
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with _store_lock:
        with open(CACHE_DIR / "llm_cache.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def llm_json_teacher(prompt: str, system: str, *, max_tokens: int,
                     temperature: float, extra_payload: dict | None,
                     cache: bool = True) -> tuple[dict, str, bool]:
    """One GLM call with cache reuse. Returns (payload, model, cache_hit).

    Replicates the old llm_json(prefer="glm", allow_fallback=False,
    model_override="glm-5.3") call shape: same provider string, same key.
    """
    msgs = ([{"role": "system", "content": system}]
            + [{"role": "user", "content": prompt}])
    cache_provider = "glm|fallback=False|model=glm-5.3|extra=" + hashlib.sha256(
        json.dumps(extra_payload or {}, sort_keys=True)
        .encode("utf-8")).hexdigest()[:12]
    ck = _cache_key(cache_provider, msgs, max_tokens, temperature)
    if cache:
        rec = _load_cache().get(ck)
        if rec is not None:
            return _parse_json(rec["content"]), rec["model"], True

    payload = {"model": "glm-5.3", "messages": msgs,
               "max_tokens": max_tokens, "temperature": temperature}
    if extra_payload:
        payload.update(extra_payload)
    body = json.dumps(payload).encode()
    req = urllib.request.Request(GLM_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + GLM_KEY})
    with urllib.request.urlopen(req, timeout=300) as r:
        j = json.loads(r.read())
    message = j["choices"][0]["message"]
    content = (message.get("content", "")
               or message.get("reasoning_content", "") or "")
    if not content.strip():
        raise RuntimeError("empty LLM response content")
    actual_model = j.get("model") or "glm-5.3"
    if cache:
        _store(ck, content, actual_model)
    return _parse_json(content), actual_model, False


def _parse_json(content: str) -> dict:
    try:
        value = json.loads(content)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        import re
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.S)
        candidate = fenced.group(1) if fenced else content
        decoder = json.JSONDecoder()
        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                value, _end = decoder.raw_decode(candidate[index:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
    return {}


if __name__ == "__main__":
    # smoke test: same old default call shape as M65-era llm client
    out, model, hit = llm_json_teacher(
        "判断以下需求是否可测试(可验证): \"软件运行稳定\"。"
        '输出JSON: {"found": true/false, "reason": "一句话"}',
        system="你是GJB 438C军用软件需求规格说明审查专家,只输出JSON。",
        max_tokens=3000, temperature=0.1, extra_payload=None)
    print(f"[{model}] cache_hit={hit} → {json.dumps(out, ensure_ascii=False)}")
