"""本地直部署启动器: 算法服务(8400, HTTP) + 后端(8300) + 前端(8080).

架构(80号): 后端经ALGO_SERVICE_URL以HTTP委托算法服务做三态核验
(完整算法栈: L1专家+L2 NLI); 算法服务不可达时后端降级fast本地引擎.

用法: python tools/serve_local.py [--no-algo]  (Ctrl+C停止)
  --no-algo  不起算法服务(纯fast档, 零模型)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "deploy/nkuDataProject/backend"
FRONTEND = ROOT / "deploy/nkuDataProject/frontend"
ALGO = ROOT / "srs_verify_package"

NO_ALGO = "--no-algo" in sys.argv

env = dict(os.environ)
env.update({
    "PYTHONUTF8": "1",
    "DEV_DB": "sqlite",
})
if not NO_ALGO:
    env["ALGO_SERVICE_URL"] = "http://127.0.0.1:8400"


def main() -> int:
    procs: list[subprocess.Popen] = []
    try:
        if not NO_ALGO:
            print("[1/3] 算法服务 :8400 (uvicorn, mDeBERTa惰性加载~35s)...")
            procs.append(subprocess.Popen(
                [sys.executable, "-X", "utf8", "-m", "uvicorn",
                 "service.app:app", "--host", "127.0.0.1", "--port", "8400"],
                cwd=str(ALGO), env=env))
            time.sleep(4)
        else:
            print("[1/3] 跳过算法服务(--no-algo, fast档直部署)")
        print("[2/3] 后端 :8300 (DEV_DB=sqlite"
              + (", ALGO_SERVICE_URL=8400" if not NO_ALGO else ", fast本地引擎")
              + ")...")
        procs.append(subprocess.Popen(
            [sys.executable, "-X", "utf8", "app.py"],
            cwd=str(BACKEND), env=env))
        print("[3/3] 前端 :8080 (静态托管, 已接真实/api)...")
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "http.server", "8080",
             "--bind", "127.0.0.1"],
            cwd=str(FRONTEND)))
        time.sleep(8)
        import urllib.request
        for url in ("http://127.0.0.1:8300/api/health",
                    "http://127.0.0.1:8080/index.html"):
            try:
                urllib.request.urlopen(url, timeout=5)
                print(f"  就绪: {url}")
            except OSError as e:
                print(f"  未就绪: {url} ({e})")
        print()
        print("前端:      http://127.0.0.1:8080  ←浏览器打开")
        print("后端Swagger: http://127.0.0.1:8300/docs")
        if not NO_ALGO:
            print("算法服务:  http://127.0.0.1:8400/health")
        print("前端流程: 校验总览 → 自动加载真实问答对 → 开始校验 → 三态结果")
        print("Ctrl+C 停止全部")
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\n停止中...")
    finally:
        for p in procs:
            try:
                p.terminate()
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
