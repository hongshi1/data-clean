#!/usr/bin/env python3
"""mermaid_render.py — 渲染 .mmd 为 PNG

优先本地 mmdc (mermaid-cli), 不可用则用 mermaid.ink 在线服务。
用法:
  python mermaid_render.py flow_feature_context.mmd flow_consistency_check.mmd
"""
import base64
import os
import shutil
import subprocess
import sys
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

MMDC = shutil.which("mmdc") or os.path.expanduser("~/node_modules/.bin/mmdc")


def render_local(mmd_path: str, png_path: str) -> bool:
    if not MMDC:
        return False
    cmd = [MMDC, "-i", mmd_path, "-o", png_path, "-b", "white", "-s", "2"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return os.path.exists(png_path)
    except Exception as e:
        print(f"  [mmdc] 渲染失败: {e}")
        return False


def render_online(mmd_path: str, png_path: str) -> bool:
    with open(mmd_path, "r", encoding="utf-8") as f:
        text = f.read()
    # mermaid.ink 接受简单 base64 (实测 pako 前缀返回 400)
    b64 = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{b64}?type=png&width=1200"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) > 1000:
            with open(png_path, "wb") as f:
                f.write(data)
            return True
        return False
    except Exception as e:
        print(f"  [mermaid.ink] 渲染失败: {e}")
        return False


def main(files):
    ok = []
    for mmd in files:
        if not os.path.isabs(mmd):
            mmd = os.path.join(SCRIPT_DIR, mmd)
        base = os.path.splitext(os.path.basename(mmd))[0]
        png = os.path.join(OUT_DIR, f"{base}.png")
        print(f"[{base}]")
        if render_local(mmd, png):
            print(f"  ✓ 本地 mmdc 渲染: {png}")
        elif render_online(mmd, png):
            print(f"  ✓ mermaid.ink 渲染: {png}")
        else:
            print("  ✗ 渲染失败")
            continue
        ok.append(png)
    return ok


if __name__ == "__main__":
    files = sys.argv[1:] or ["flow_feature_context.mmd", "flow_consistency_check.mmd"]
    main(files)
