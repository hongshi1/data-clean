r"""torch Windows DLL修复垫片: 预载torch/lib下全部DLL(ALTERED_SEARCH_PATH)
用法: 在 import torch 之前 `from tools.torch_dll_fix import ensure_torch_imports` 并调用
根因: venv的python.exe继承Anaconda环境, 默认DLL搜索路径下依赖解析被劫持;
      LOAD_WITH_ALTERED_SEARCH_PATH从DLL自身目录解析依赖, 预载后torch正常import
"""
import ctypes
import glob
import os
import sys


def _torch_lib_dir():
    for base in (os.path.dirname(os.path.abspath(__file__)),
                 os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv-nli")):
        for sub in (os.path.join(base, "torch", "lib"),
                    os.path.join(os.path.dirname(base), "torch", "lib")):
            if os.path.isdir(sub):
                return sub
    # 兜底: venv site-packages
    return os.path.join(sys.prefix, "Lib", "site-packages", "torch", "lib")


def preload_torch_dlls(max_rounds: int = 4):
    """按ALTERED_SEARCH_PATH预载torch\lib全部DLL(带依赖重试), 返回(成功数, 失败列表)"""
    torchlib = _torch_lib_dir()
    if not os.path.isdir(torchlib):
        return 0, ["torch lib dir not found: " + torchlib]
    dlls = sorted(glob.glob(os.path.join(torchlib, "*.dll")))
    flags = 0x8  # LOAD_WITH_ALTERED_SEARCH_PATH
    kernel32 = ctypes.windll.kernel32
    remaining = list(dlls)
    for _ in range(max_rounds):
        if not remaining:
            break
        still = []
        for p in remaining:
            if not kernel32.LoadLibraryExW(p, 0, flags):
                still.append(p)
        remaining = still
    ok = len(dlls) - len(remaining)
    if remaining:
        # 打印失败清单便于诊断
        sys.stderr.write("[torch_dll_fix] failed to preload %d/%d DLLs:\n" % (len(remaining), len(dlls)))
        for p in remaining[:8]:
            sys.stderr.write("  " + os.path.basename(p) + "\n")
    return ok, remaining


def ensure_torch_imports():
    """预载DLL后import torch, 返回torch模块(失败抛原异常)"""
    ok, failed = preload_torch_dlls()
    if failed:
        print(f"[torch_dll_fix] preloaded {ok} DLLs, {len(failed)} failed", file=sys.stderr)
    import torch  # noqa: F401  (DLL已在进程内, import走常驻实例)
    return torch


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ok, failed = preload_torch_dlls()
    print(f"预载DLL: {ok}成功 / {len(failed)}失败")
    import torch
    print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available())
    import transformers
    print("transformers:", transformers.__version__)
