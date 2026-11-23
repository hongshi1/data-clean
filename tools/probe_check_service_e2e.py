"""E2E smoke: submit via HTTP, poll to done, verify report shape (agent scenario)."""
from __future__ import annotations

import json
import time
import urllib.request

BASE = "http://127.0.0.1:8300"
body = json.dumps({"scene": "scene1", "qa_pairs": [
    {"sample_id": "q0", "question": "数据库关闭接口的项目唯一标识符是什么？",
     "answer": "数据库关闭接口的标识符为PZXQ-GN-SJKCZ-SJKGB。",
     "source": "04数据统一访问"},
    {"sample_id": "q1", "question": "系统支持哪些操作？",
     "answer": "系统支持查询和修改。", "source": "04数据统一访问"}]}).encode()
req = urllib.request.Request(BASE + "/api/check", data=body,
                             headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
print("受理:", resp["ok"], resp["data"]["check_id"], resp["data"]["status"])
cid = resp["data"]["check_id"]
for _ in range(60):
    time.sleep(2)
    st = json.loads(urllib.request.urlopen(
        BASE + "/api/check-status/" + cid, timeout=30).read())
    if st["data"]["status"] in ("done", "error"):
        break
print("终态:", json.dumps(st["data"], ensure_ascii=False)[:180])
rep = json.loads(urllib.request.urlopen(
    BASE + "/api/check-reports/" + cid, timeout=30).read())["data"]["report"]
print("summary:", json.dumps(rep["summary"], ensure_ascii=False))
s0 = rep["samples"][0]
print("sample0:", s0["sample_id"], s0["consistency_result"],
      "| violations:", json.dumps(s0["violations"], ensure_ascii=False)[:220])
