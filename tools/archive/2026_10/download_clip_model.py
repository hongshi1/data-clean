r"""下载Chinese-CLIP图文编码器到本地(双模态对齐的图像侧底座).

模型: OFA-Sys/chinese-clip-vit-base-patch16 (~600MB)
  - 图像编码器: ViT-B/16 (768维) — 图像native embedding
  - 文本编码器: RoBERTa-wwm (512维池化) — CLIP图文先验(文本桥)
直连huggingface失败自动切hf-mirror镜像(与download_embedding_model同模式).

用法: python tools/download_clip_model.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TARGET = BASE / "models" / "clip" / "chinese-clip-vit-base-patch16"
REPO = "OFA-Sys/chinese-clip-vit-base-patch16"


def inherit_windows_proxy() -> str | None:
    """Python不读注册表代理, 若IE代理开启则注入环境变量(同BGE下载脚本)."""
    if os.environ.get("HTTPS_PROXY"):
        return None
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
        server, _ = winreg.QueryValueEx(key, "ProxyServer")
        winreg.CloseKey(key)
        if enable and server:
            server = server if "://" in server else f"http://{server}"
            os.environ["HTTPS_PROXY"] = server
            os.environ["HTTP_PROXY"] = server
            return server
    except OSError:
        pass
    return None


def try_download(use_mirror: bool) -> str:
    if use_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    else:
        os.environ.pop("HF_ENDPOINT", None)
    from huggingface_hub import snapshot_download
    print(f"[{'镜像' if use_mirror else '直连'}] {REPO} -> {TARGET}")
    t0 = time.time()
    p = snapshot_download(
        repo_id=REPO, local_dir=str(TARGET),
        allow_patterns=["*.json", "*.txt", "*.bin", "*.model",
                        "tokenizer*", "vocab*", "merges*", "*.safetensors"],
        max_workers=4)
    print(f"  完成 {time.time() - t0:.0f}s: {p}")
    return p


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    proxy = inherit_windows_proxy()
    print(f"系统代理: {proxy or '未检测到'}")
    TARGET.mkdir(parents=True, exist_ok=True)
    if (TARGET / "config.json").exists() and any(
            TARGET.glob("pytorch_model.bin")) or any(
            TARGET.glob("*.safetensors")):
        print(f"已存在: {TARGET}")
        return
    for use_mirror in (False, True):
        try:
            try_download(use_mirror)
            break
        except Exception as e:  # noqa: BLE001 — 网络错误需全部回退镜像
            print(f"  失败: {type(e).__name__} {str(e)[:110]}")
    size = sum(f.stat().st_size for r, _, fs in os.walk(TARGET) for f in
               [Path(r) / x for x in fs])
    print(f"模型目录: {TARGET} ({size / 1e6:.0f}MB)")


if __name__ == "__main__":
    main()
