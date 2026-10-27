#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量导入 datasets_easydataset.json → EasyDataset (port 1717)

流程:
  1. GET /api/projects 查重（同名则复用，否则 POST 创建）
  2. 分批 POST /api/projects/{id}/datasets/import（batch=500，含重试）
  3. GET /api/projects/{id}/datasets 分页计数核验
对照导出比较由 compare_easydataset_export.py 完成。
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
DATA_PATH = BASE / "data/gjb_438c/easydataset/datasets_easydataset.json"
ED_URL = "http://localhost:1717"
PROJECT_NAME = "SRS一致性校验微调数据集"
PROJECT_DESC = "16份GJB 438C SRS的18,119条QA对（原生/注入/UML，含一致/不一致标注、CoT与tags），用于微调需求一致性校验模型"
BATCH = 500
RETRY = 3


def http(method, url, payload=None, timeout=300):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}


def main():
    records = json.load(open(DATA_PATH, encoding="utf-8"))
    print(f"源数据: {len(records)}条 ({DATA_PATH.name})")

    # 1. 项目查重/创建
    code, projects = http("GET", f"{ED_URL}/api/projects", timeout=30)
    assert code == 200, f"获取项目列表失败: {code}"
    project_id = None
    for p in projects:
        if p.get("name") == PROJECT_NAME:
            project_id = p["id"]
            print(f"复用已有项目: {project_id}")
            break
    if project_id is None:
        code, proj = http("POST", f"{ED_URL}/api/projects",
                          {"name": PROJECT_NAME, "description": PROJECT_DESC}, timeout=30)
        assert code == 201, f"创建项目失败: {code} {proj}"
        project_id = proj["id"]
        print(f"项目已创建: {project_id}")

    # 导入前已有数量（支持断点续跑）
    code, first = http("GET", f"{ED_URL}/api/projects/{project_id}/datasets?page=1&size=1", timeout=60)
    existing = first.get("total") if isinstance(first, dict) else (len(first) if isinstance(first, list) else 0)
    print(f"导入前库内已有: {existing}条")

    # 2. 分批导入
    ok = skipped = failed = 0
    t0 = time.time()
    n_batches = (len(records) + BATCH - 1) // BATCH
    for bi in range(n_batches):
        chunk = records[bi * BATCH:(bi + 1) * BATCH]
        code, resp = None, None
        for attempt in range(1, RETRY + 1):
            code, resp = http("POST", f"{ED_URL}/api/projects/{project_id}/datasets/import",
                              {"datasets": chunk, "sourceInfo": {"source": "srs-pipeline-v2", "file": DATA_PATH.name}})
            if code == 200:
                break
            print(f"  批{bi+1} 第{attempt}次失败: {code} {str(resp)[:120]}，重试…")
            time.sleep(2 * attempt)
        if code != 200:
            print(f"  批{bi+1} 彻底失败，中止（已导入部分保留）")
            failed += len(chunk)
            break
        ok += resp.get("success", 0)
        skipped += resp.get("skipped", 0)
        failed += resp.get("failed", 0)
        if resp.get("errors"):
            print(f"  批{bi+1} errors: {resp['errors'][:2]}")
        done = (bi + 1) * BATCH
        print(f"  批{bi+1}/{n_batches}: +{resp.get('success', 0)} (累计{ok}) [{time.time()-t0:.0f}s]")

    # 3. 计数核验
    code, first = http("GET", f"{ED_URL}/api/projects/{project_id}/datasets?page=1&size=1", timeout=60)
    total = first.get("total") if isinstance(first, dict) else len(first)
    print(f"\n导入完成: 成功{ok} 跳过{skipped} 失败{failed} | 库内total={total} | 预期={existing + ok + skipped}")
    verdict = "PASS" if total == existing + ok + skipped and failed == 0 else "CHECK"
    print(f"核验: {verdict}")
    json.dump({"projectId": project_id, "imported": ok, "skipped": skipped, "failed": failed,
               "totalInDb": total, "sourceCount": len(records), "verdict": verdict},
              open(BASE / "data/gjb_438c/easydataset/import_result.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("结果已保存: data/gjb_438c/easydataset/import_result.json")


if __name__ == "__main__":
    main()
