r"""下载NLI模型到本地: 中文Erlangshen + 多语言mDeBERTa
直连huggingface.co失败自动切hf-mirror.com镜像
用法: .venv-nli\Scripts\python.exe tools\download_nli_models.py
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from torch_dll_fix import preload_torch_dlls  # noqa: E402

preload_torch_dlls()
from huggingface_hub import snapshot_download  # noqa: E402

MODELS = [
    "IDEA-CCNL/Erlangshen-Roberta-110M-NLI",                             # 中文NLI ~450MB
    "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",         # 多语言(含中文) ~560MB
]
TARGET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "models", "nli")


def try_download(repo, use_mirror):
    if use_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    else:
        os.environ.pop("HF_ENDPOINT", None)
    dest = os.path.join(TARGET, repo.split("/")[-1])
    print(f"[{'镜像' if use_mirror else '直连'}] {repo} -> {dest}")
    t0 = time.time()
    p = snapshot_download(repo_id=repo, local_dir=dest,
                          allow_patterns=["*.json", "*.txt", "*.safetensors", "*.bin",
                                          "*.model", "tokenizer*", "vocab*", "merges*"],
                          max_workers=4)
    print(f"  完成 {time.time()-t0:.0f}s: {p}")
    return p


def main():
    os.makedirs(TARGET, exist_ok=True)
    for repo in MODELS:
        done = False
        for use_mirror in (False, True):
            try:
                try_download(repo, use_mirror)
                done = True
                break
            except Exception as e:
                print(f"  失败: {type(e).__name__} {str(e)[:110]}")
        if not done:
            print(f"!! {repo} 两种方式均失败")
    print("\n下载目标目录:", TARGET)
    for d in sorted(os.listdir(TARGET)):
        sub = os.path.join(TARGET, d)
        size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(sub) for f in fs)
        print(f"  {d}: {size/1e6:.0f}MB")


if __name__ == "__main__":
    main()
