"""Test Ollama qwen3:8b for L3 local LLM arbiter."""
from __future__ import annotations

import json
import time
import urllib.request

from algorithms.consistency.eval_lib import build_qa_input, load_frozen_qa


def call_ollama(prompt: str, system: str = "") -> str:
    body = {
        "model": "qwen3:8b",
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 100},
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=180).read())
    return resp.get("response", "")


def main() -> None:
    system = (
        "你是GJB军事软件需求文档的一致性审查员。"
        "给定证据和声明，判定：support(证据支持)/refute(证据反对)/"
        "not_in_evidence(证据无法判定)。"
        "只输出JSON格式。"
    )
    prompt = (
        "证据：需求重用=平板、桌面\n"
        "声明：系统支持在桌面和平板设备上运行。\n"
        '请输出：{"verdict": "...", "rationale": "..."}'
    )
    t0 = time.perf_counter()
    result = call_ollama(prompt, system)
    elapsed = time.perf_counter() - t0
    print(f"回复: {result[:200]}")
    print(f"耗时: {elapsed:.1f}秒")

    # 测试refute case
    prompt2 = (
        "证据：需求重用=平板、桌面\n"
        "声明：系统支持在桌面、平版和平板设备上运行。\n"
        '请输出：{"verdict": "...", "rationale": "..."}'
    )
    t0 = time.perf_counter()
    result2 = call_ollama(prompt2, system)
    elapsed2 = time.perf_counter() - t0
    print(f"\nRefute case回复: {result2[:200]}")
    print(f"耗时: {elapsed2:.1f}秒")


if __name__ == "__main__":
    main()
