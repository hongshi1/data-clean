"""Download the D3 student base model (Qwen3-1.7B, ~3.4GB).

Proxy pattern inherited from tools/download_embedding_model.py
(Windows registry proxy + hf-mirror fallback).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

os.environ.setdefault("PYTHONUTF8", "1")
from download_embedding_model import inherit_windows_proxy  # noqa: E402

inherit_windows_proxy()

from huggingface_hub import snapshot_download  # noqa: E402

REPO = "Qwen/Qwen3-1.7B"
TARGET = BASE / "models" / "llm" / "qwen3-1.7b"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for use_mirror in (False, True):
        try:
            if use_mirror:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                print("trying hf-mirror...", flush=True)
            path = snapshot_download(
                repo_id=REPO,
                local_dir=str(TARGET),
                ignore_patterns=["*.pth", "original/*", "*.gguf"],
            )
            print(f"downloaded → {path}")
            return
        except Exception as exc:
            print(f"download failed{'(mirror)' if use_mirror else ''}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
    raise SystemExit("download failed on both direct and mirror")


if __name__ == "__main__":
    main()
