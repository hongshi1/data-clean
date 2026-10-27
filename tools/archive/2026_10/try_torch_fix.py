import ctypes
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
torchlib = r"D:\study\hengxiang\data_clean\.venv-nli\Lib\site-packages\torch\lib"
os.add_dll_directory(torchlib)

print("== 实验1: 预加载torch自带libiomp后再载c10 ==")
try:
    ctypes.CDLL(os.path.join(torchlib, "libiomp5md.dll"))
    print("  libiomp预加载 OK")
    ctypes.CDLL(os.path.join(torchlib, "c10.dll"))
    print("  c10: OK ✓✓✓")
except OSError as e:
    print("  FAIL:", str(e)[:90])

print("\n== 实验2: ALTERED_SEARCH_PATH载c10 ==")
try:
    h = ctypes.windll.kernel32.LoadLibraryExW(
        os.path.join(torchlib, "c10.dll"), 0, 0x8 | 0x1)  # LOAD_WITH_ALTERED_SEARCH_PATH|SEARCH_DLL
    if h:
        print("  c10 via LoadLibraryEx: OK ✓✓✓ handle=", h)
    else:
        err = ctypes.windll.kernel32.GetLastError()
        print("  GetLastError:", err)
except Exception as e:
    print("  EXC:", str(e)[:90])
