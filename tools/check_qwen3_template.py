"""Check Qwen3 chat template think-block rendering."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transformers import AutoTokenizer  # noqa: E402


def main() -> None:
    tok = AutoTokenizer.from_pretrained("models/llm/qwen3-1.7b")
    target = '{"verdict": "support", "issues": []}'
    msgs = [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "Q"},
        {"role": "assistant", "content": target}]
    full = tok.apply_chat_template(msgs, tokenize=False)
    print("=== full render (assistant tail) ===")
    print(repr(full[-140:]))
    gen = tok.apply_chat_template(
        msgs[:2], tokenize=False, add_generation_prompt=True)
    print("=== generation prompt tail (thinking default) ===")
    print(repr(gen[-80:]))
    gen2 = tok.apply_chat_template(
        msgs[:2], tokenize=False, add_generation_prompt=True,
        enable_thinking=False)
    print("=== generation prompt tail (no-think) ===")
    print(repr(gen2[-120:]))


if __name__ == "__main__":
    main()
