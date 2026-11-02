"""联调脚本: 真实HTTP链路验证(algo:8400 + backend:8300).

步骤:
  1. 起算法服务(子进程) + 后端(子进程, ALGO_SERVICE_URL指向algo)
  2. GET /api/health (后端探活)
  3. POST /api/verify/04 → job_id → 轮询status → 断言remote引擎+三态
  4. GET /api/qa?doc=04 → 断言attrs落库
  5. 停算法服务 → 再verify → 断言降级local引擎
  6. 输出联调结论
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = "C:/Users/12488/Desktop/data_clean"
PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    print(f"  {'[PASS]' if ok else '[FAIL]'} {name} {detail}")


def get(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(url: str, body: dict | None = None, timeout: int = 300) -> dict:
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_health(url: str, tries: int = 40, gap: float = 2.0) -> bool:
    for _ in range(tries):
        try:
            get(url, timeout=5)
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(gap)
    return False


def main() -> int:
    procs: list[subprocess.Popen] = []
    env_vars = {
        "PYTHONUTF8": "1",
        "DEV_DB": "sqlite",
        "ALGO_SERVICE_URL": "http://127.0.0.1:8400",
    }
    import os
    env = dict(os.environ)
    env.update(env_vars)
    try:
        print("== 启动算法服务(:8400) ==")
        procs.append(subprocess.Popen(
            [sys.executable, "-X", "utf8", "-m", "uvicorn",
             "service.app:app", "--port", "8400", "--host", "127.0.0.1"],
            cwd=f"{ROOT}/srs_verify_package", env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        ok = wait_health("http://127.0.0.1:8400/health")
        check("算法服务探活", ok)
        if not ok:
            return _finish(procs)

        print("== 启动后端(:8300) ==")
        procs.append(subprocess.Popen(
            [sys.executable, "-X", "utf8", "app.py"],
            cwd=f"{ROOT}/deploy/nkuDataProject/backend", env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        ok = wait_health("http://127.0.0.1:8300/api/health")
        check("后端探活(db+场景注册)", ok)
        if not ok:
            return _finish(procs)

        print("== 链路1: POST /api/verify/04 (远程算法服务) ==")
        r = post("http://127.0.0.1:8300/api/verify/04")
        check("发起核验job", r.get("ok") and r["data"].get("job_id"))
        job = r["data"]["job_id"]
        result = None
        for _ in range(60):
            s = get(f"http://127.0.0.1:8300/api/verify/status/{job}")
            if s["data"]["status"] in ("done", "error"):
                result = s["data"]
                break
            time.sleep(3)
        ok = result is not None and result["status"] == "done"
        detail = (result or {}).get("error", "") if result else ""
        check("轮询到done", ok, str(detail)[:80])
        if ok:
            res = result["result"]
            vio = [x for x in res["results"]
                   if x["qa_id"].startswith("DOC04-VIO")]
            hits = sum(1 for x in vio if x["verdict"] == "refute")
            engines = {x.get("engine", "local") for x in res["results"]}
            check("违例refute 16/17", hits == 16, f"实际{hits}")
            check("引擎=remote", engines == {"remote"}, str(engines))
            check("108实例", res["n"] == 108, f"n={res['n']}")
            check("claim明细", bool(vio[0].get("claims")))

        print("== 链路2: GET /api/qa?doc=04 (attrs落库) ==")
        qa = get("http://127.0.0.1:8300/api/qa?doc=04")
        items = qa["data"]["items"]
        check("qa列表108条(doc=04)", len(items) == 108, f"实际{len(items)}")
        fails = [x for x in items
                 if (x.get("check") or {}).get("st") == "fail"]
        warns = [x for x in items
                 if (x.get("check") or {}).get("st") == "warn"]
        check("核验状态回显(fail+warn>0)", bool(fails) or bool(warns),
              f"fail={len(fails)} warn={len(warns)}")

        print("== 链路3: 降级测试(停算法服务→本地兜底) ==")
        procs[0].terminate()
        procs[0].wait(timeout=30)
        time.sleep(2)
        r = post("http://127.0.0.1:8300/api/verify/04")
        job2 = r["data"]["job_id"]
        result2 = None
        for _ in range(90):
            s = get(f"http://127.0.0.1:8300/api/verify/status/{job2}")
            if s["data"]["status"] in ("done", "error"):
                result2 = s["data"]
                break
            time.sleep(3)
        ok = result2 is not None and result2["status"] == "done"
        detail = (result2 or {}).get("error", "") if result2 else ""
        check("降级后仍done", ok, str(detail)[:80])
        if ok:
            res2 = result2["result"]
            vio2 = [x for x in res2["results"]
                    if x["qa_id"].startswith("DOC04-VIO")]
            hits2 = sum(1 for x in vio2 if x["verdict"] == "refute")
            engines2 = {x.get("engine", "local") for x in res2["results"]}
            # fast档安全降级(无NLI): done+local引擎即通过, 违例数仅记录
            check("引擎=local(安全降级)", engines2 == {"local"},
                  str(engines2))
            print(f"    (fast档违例refute: {hits2}/17, 仅记录)")
        return _finish(procs)
    finally:
        for p in procs:
            try:
                p.terminate()
            except OSError:
                pass


def _finish(procs: list[subprocess.Popen]) -> int:
    print()
    print(f"联调结论: {len(PASS)}通过 / {len(FAIL)}失败")
    if FAIL:
        print("失败项:", FAIL)
    for p in procs:
        try:
            p.terminate()
        except OSError:
            pass
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
