#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLM-5.3 LLM客户端: 智谱官网API(优先) + moonshot kimi(回退), 带磁盘响应缓存.

配置(full档): 环境变量优先, 其次运行目录下的.env(KEY=VALUE行, 与研究
仓库tools/ai_config同格式); URL/MODEL有缺省值, KEY缺失只在真正发起
调用时报错(可读指引, import期零I/O/零配置依赖).

  GLM_KEY / GLM_URL / GLM_MODEL
  KIMI_KEY / KIMI_URL / KIMI_MODEL

缓存: llm_chat(cache=True)按(prefer+messages+参数)哈希落盘 → 同prompt
重跑零成本零漂移(注意llm_json_sc多路投票必须cache=False).
缓存目录: 环境变量SRS_VERIFY_LLM_CACHE > 运行目录llm_cache/ >
临时目录回退(无写权限时), 见README.
"""
import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

#: URL/模型缺省值(与研究仓库tools/ai_config一致)
_DEFAULTS: dict[str, str] = {
    "GLM_URL": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    "GLM_MODEL": "glm-5",
    "KIMI_URL": "https://api.moonshot.cn/v1/chat/completions",
    "KIMI_MODEL": "kimi-k2.6",
}

_cache_dir: Path | None = None
_cache_index: dict[str, dict] | None = None
_store_lock = threading.Lock()  # 多线程 adjudication 并发追加缓存时防交错
_config_lock = threading.Lock()
_file_env: dict[str, str] | None = None


def _load_env_file() -> dict[str, str]:
    """运行目录.env解析(KEY=VALUE行; 与研究仓库ai_config同解析规则)."""
    env: dict[str, str] = {}
    path = Path.cwd() / ".env"
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _config(name: str) -> str:
    """取一个配置项: 环境变量 > .env文件 > 缺省值; 皆无则报可读错误."""
    global _file_env
    with _config_lock:
        if _file_env is None:
            try:
                _file_env = _load_env_file()
            except OSError:
                _file_env = {}
    value = (os.environ.get(name) or _file_env.get(name)
             or _DEFAULTS.get(name) or "")
    if value:
        return value
    raise RuntimeError(
        f"缺少配置 {name}: 在运行目录创建 .env(KEY=VALUE) "
        f"或设置环境变量 {name}(full档需要GLM端点, 见README).")


# ═══════════════════════════════════════════════════════════════
# 缓存目录(惰性解析: 环境变量 > 运行目录llm_cache/ > 临时目录回退)
# ═══════════════════════════════════════════════════════════════

def _resolve_cache_dir() -> Path:
    env = os.environ.get("SRS_VERIFY_LLM_CACHE")
    if env:
        return Path(env)
    try:
        candidate = Path.cwd() / "llm_cache"
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "srs_verify_llm_cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def cache_dir() -> Path:
    """llm响应缓存目录(首次调用时解析并缓存)."""
    global _cache_dir
    if _cache_dir is None:
        _cache_dir = _resolve_cache_dir()
    return _cache_dir


def _load_cache() -> dict[str, dict]:
    global _cache_index
    if _cache_index is None:
        _cache_index = {}
        path = cache_dir() / "llm_cache.jsonl"
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
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
    cache_dir().mkdir(parents=True, exist_ok=True)
    with _store_lock:
        with open(cache_dir() / "llm_cache.jsonl", "a",
                  encoding="utf-8") as handle:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════
# 主客户端
# ═══════════════════════════════════════════════════════════════

def llm_chat(prompt, system=None, prefer="glm", max_tokens=3000,
             timeout=120, temperature=0.1, cache=True, allow_fallback=True,
             model_override=None, extra_payload=None):
    """调用GLM-5.3(优先)或kimi(回退), 返回(content, model_used).

    cache=True: 磁盘缓存命中直接返回(可复现); 需要独立采样时传cache=False.
    """
    order = ([prefer] + [m for m in ("glm", "kimi") if m != prefer]
             if allow_fallback else [prefer])
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]

    ck = None
    if cache:
        cache_provider = f"{prefer}|fallback={allow_fallback}|model={model_override}"
        cache_provider += "|extra=" + hashlib.sha256(json.dumps(
            extra_payload or {}, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        ck = _cache_key(cache_provider, msgs, max_tokens, temperature)
        rec = _load_cache().get(ck)
        if rec is not None:
            return rec["content"], rec["model"]

    last_err: Exception | None = None
    for prov in order:
        if prov == "glm":
            url, key, model = (_config("GLM_URL"), _config("GLM_KEY"),
                               _config("GLM_MODEL"))
        else:
            url, key, model = (_config("KIMI_URL"), _config("KIMI_KEY"),
                               _config("KIMI_MODEL"))
        request_model = model_override if model_override and prov == prefer else model
        payload = {"model": request_model, "messages": msgs,
                   "max_tokens": max_tokens, "temperature": temperature}
        if extra_payload:
            payload.update(extra_payload)
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + key})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                j = json.loads(r.read())
            message = j["choices"][0]["message"]
            content = (message.get("content", "")
                       or message.get("reasoning_content", "") or "")
            if content.strip():
                actual_model = j.get("model") or request_model
                if ck:
                    _store(ck, content, actual_model)
                return content, actual_model
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"LLM调用失败(glm+kimi): {last_err}")


def llm_json(prompt, system=None, prefer="glm", cache=True,
             allow_fallback=True, model_override=None, extra_payload=None,
             max_tokens=3000, timeout=120, temperature=0.1):
    """调用LLM并解析JSON输出(容错: 提取```json块或首个{...})"""
    content, model = llm_chat(prompt, system=system, prefer=prefer, cache=cache,
                              allow_fallback=allow_fallback,
                              model_override=model_override,
                              extra_payload=extra_payload,
                              max_tokens=max_tokens, timeout=timeout,
                              temperature=temperature)
    return _parse_json(content), model


def llm_json_sc(prompt, system=None, prefer="glm", n_votes=3):
    """Self-Consistency多路投票: 同一prompt独立调用n次, 取多数判决

    谱系: Wang et al. (2023) Self-Consistency Improves Chain of Thought Reasoning
    注意: 各路必须独立采样 → cache=False(缓存会让n票变成同一票)
    """
    votes = []
    for i in range(n_votes):
        try:
            content, model = llm_chat(prompt, system=system, prefer=prefer,
                                      temperature=0.3 if i > 0 else 0.1,
                                      cache=False)
            votes.append(_parse_json(content))
        except Exception:
            continue
    if not votes:
        return {"_parse_error": "all votes failed"}, "none"
    found_votes = [v.get("found", False) for v in votes if "found" in v]
    if not found_votes:
        return votes[0], "sc"
    majority = sum(found_votes) > len(found_votes) / 2
    for v in votes:
        if v.get("found") == majority:
            v["_sc"] = {
                "votes": len(found_votes),
                "agreement": round(max(sum(found_votes),
                                       len(found_votes) - sum(found_votes))
                                 / len(found_votes), 2)}
            return v, "sc"
    return votes[0], "sc"


def _parse_json(content):
    try:
        return json.loads(content)
    except Exception:
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
            except Exception:
                pass
    return {}


__all__ = ["cache_dir", "llm_chat", "llm_json", "llm_json_sc"]
