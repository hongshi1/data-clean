#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在线审核流API验证: confirmed切换(PATCH) + 过滤查询(GET) + 恢复"""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ED = "http://localhost:1717"
PID = "xZb5IZMWfTmO"


def http(method, url, payload=None, timeout=90):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def find(did, status):
    res = http("GET", f"{ED}/api/projects/{PID}/datasets?page=1&size=2000&status={status}")
    items = res.get("datasets", res.get("data", [])) if isinstance(res, dict) else res
    return any(d["id"] == did for d in items), res.get("total") if isinstance(res, dict) else len(items)


def main():
    # 1. 取一条confirmed=true的样本
    page = http("GET", f"{ED}/api/projects/{PID}/datasets?page=1&size=3&status=confirmed")
    total_c = page.get("total")
    items = page.get("datasets", page.get("data", []))
    ds = items[0]
    did = ds["id"]
    print(f"confirmed总数: {total_c} | 样本id: {did}")
    print(f"  question: {ds['question'][:60]}")
    print(f"  confirmed: {ds['confirmed']} | tags: {str(ds.get('tags'))[:70]}")
    print(f"  cot: {str(ds.get('cot'))[:60]} | score: {ds.get('score')}")

    # 2. 审核拒绝: confirmed -> false
    r1 = http("PATCH", f"{ED}/api/projects/{PID}/datasets?id={did}", {"confirmed": False})
    print(f"PATCH拒绝: success={r1.get('success')}")

    # 3. 验证unconfirmed过滤能查到它
    found_un, total_un = find(did, "unconfirmed")
    print(f"unconfirmed池中找到该条: {found_un} (unconfirmed总数: {total_un})")

    # 4. 恢复confirmed=true
    r2 = http("PATCH", f"{ED}/api/projects/{PID}/datasets?id={did}", {"confirmed": True})
    print(f"PATCH恢复: success={r2.get('success')}")
    found_c, total_c2 = find(did, "confirmed")
    print(f"恢复后confirmed总数: {total_c2} (应为18,119)")

    ok = bool(r1.get("success")) and found_un and bool(r2.get("success")) and total_c2 == 18119
    print("REVIEW-FLOW API:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
