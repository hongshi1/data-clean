r"""下载本地中文语义embedding模型到 models/embedding/
选型: BAAI/bge-large-zh-v1.5 (C-MTEB领先, 1024维, 326M参数, RTX 4060可推理)
用途: 语义层检测/方向A聚合/term_checker语义增强/embedding_channel本地化
直连huggingface.co失败自动切hf-mirror.com镜像; 自动继承Windows系统代理
用法: python tools/download_embedding_model.py
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from torch_dll_fix import preload_torch_dlls  # noqa: E402


def inherit_windows_proxy():
    r"""Python不读注册表代理: 若IE代理开启, 注入HTTPS_PROXY/HTTP_PROXY环境变量"""
    if os.environ.get("HTTPS_PROXY"):
        return None
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
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


inherit_windows_proxy()
preload_torch_dlls()
from huggingface_hub import snapshot_download  # noqa: E402

MODELS = [
    "BAAI/bge-large-zh-v1.5",  # 中文embedding ~1.3GB
]

TARGET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "models", "embedding")


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
                                          "tokenizer*", "vocab*", "merges*", "*.model"],
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
