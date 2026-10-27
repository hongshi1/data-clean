#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B方案落地: EasyDataset四级链同步 + 标签树 + Pool B导入 + Question链接

对应文档: docs/srs_project/easydataset_landing_design.md §8

流程(幂等,可重复执行):
  A. 直写DB: UploadFiles(16 SRS + unknown + 外部池B) + Chunks(1,413真实 + 33域内聚合 + 5 EXT聚合)
  B. Question链接: LEFT JOIN找无Question的Datasets → 建Question(尽量链真实章节块) → 更新questionId
  C. 标签树: GET已有 → PUT补缺(PoolA/PoolB四层)
  D. Pool B导入: external_alpaca ⊕ external_sharegpt(tags) → REST分批导入10,642
  E. 再次Question链接(为新导入的Pool B记录)
  F. 验证报告 → data/gjb_438c/easydataset/sync_result.json

DB格式注意: Prisma SQLite DateTime = epoch毫秒整数; id = nanoid风格字符串
"""
import json
import random
import string
import sqlite3
import sys
import time
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
ED = "http://localhost:1717"
PROJECT_NAME = "SRS一致性校验微调数据集"
DB_PATH = BASE / "easy-dataset/prisma/db.sqlite"
CHUNKS_JSON = BASE / "data/gjb_438c/easydataset/chunks.json"
EXT_ALPACA = BASE / "data/gjb_438c/easydataset/external_alpaca.jsonl"
EXT_SHAREGPT = BASE / "data/gjb_438c/easydataset/external_sharegpt.jsonl"
RESULT_OUT = BASE / "data/gjb_438c/easydataset/sync_result.json"
ALPHABET = string.ascii_letters + string.digits
rng = random.Random(20260909)


def nid():
    return "".join(rng.choice(ALPHABET) for _ in range(21))


def now_ms():
    return int(time.time() * 1000)


def http(method, url, payload=None, timeout=300):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.getcode(), json.loads(r.read().decode("utf-8"))


def get_project_id():
    code, projects = http("GET", f"{ED}/api/projects", timeout=30)
    assert code == 200, f"获取项目失败: {code}"
    for p in projects:
        if p.get("name") == PROJECT_NAME:
            return p["id"]
    raise SystemExit(f"项目[{PROJECT_NAME}]不存在, 请先运行 import_easydataset_full.py")


# ---------------------------------------------------------------- A. 文件与文本块

def sync_files_chunks(db, pid):
    cur = db.cursor()
    chunks = json.load(open(CHUNKS_JSON, encoding="utf-8"))
    # 文档分组
    docs = {}
    for c in chunks:
        m = c.get("metadata", {}) or {}
        doc = m.get("doc", "unknown")
        docs.setdefault(doc, {"doc_num": m.get("doc_num", ""), "chunks": []})["chunks"].append(c)
    print(f"A. 源chunks: {len(chunks)}块 / {len(docs)}文档")

    # 已有文件/块(幂等)
    have_files = {r[0] for r in cur.execute(
        "SELECT fileName FROM UploadFiles WHERE projectId=?", (pid,))}
    have_chunk_names = {r[0] for r in cur.execute(
        "SELECT name FROM Chunks WHERE projectId=?", (pid,))}

    t = now_ms()
    file_ids = {r[1]: r[0] for r in cur.execute(
        "SELECT id, fileName FROM UploadFiles WHERE projectId=?", (pid,))}

    n_files = n_chunks = 0
    for doc, info in sorted(docs.items()):
        doc_num = info["doc_num"] or ""
        fname = f"{doc_num}{doc[len(doc_num):] if doc.startswith(doc_num) else doc}.md"
        if len(fname) > 180 or not fname.strip(".md"):
            fname = f"{doc_num or 'doc'}_parsed.md"
        if fname not in have_files:
            content_all = "\n".join(c.get("content", "") for c in info["chunks"])
            md5 = hashlib.md5(content_all.encode("utf-8")).hexdigest()
            fid = nid()
            cur.execute(
                "INSERT INTO UploadFiles (id, projectId, fileName, fileExt, path, size, md5, createAt, updateAt)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (fid, pid, fname, ".md", f"data/软件需归样例数据集/{doc}.doc",
                 len(content_all.encode("utf-8")), md5, t, t))
            file_ids[fname] = fid
            n_files += 1
        fid = file_ids[fname]
        # 真实章节块
        for c in info["chunks"]:
            if c["name"] in have_chunk_names:
                continue
            cur.execute(
                "INSERT INTO Chunks (id, name, projectId, fileId, fileName, content, summary, size, createAt, updateAt)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (nid(), c["name"], pid, fid, fname, c.get("content", ""),
                 c.get("summary", "")[:200], c.get("size", len(c.get("content", ""))), t, t))
            n_chunks += 1

    # 聚合块: 数据集chunkName(33个) + EXT(5个)
    ds_names = [r[0] for r in cur.execute(
        "SELECT DISTINCT chunkName FROM Datasets WHERE projectId=?", (pid,))]
    ext_names = [f"EXT-{s}" for s in
                 ["外部-PURE", "外部-NLIRE", "外部-歧义类", "外部-FlowVQA", "外部-LLMGen"]]

    # 未知来源文件 + 外部池文件(按需)
    def ensure_file(fname, path):
        if fname in file_ids:
            return file_ids[fname]
        fid = nid()
        cur.execute(
            "INSERT INTO UploadFiles (id, projectId, fileName, fileExt, path, size, md5, createAt, updateAt)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (fid, pid, fname, ".md", path, 0, hashlib.md5(fname.encode()).hexdigest(), t, t))
        file_ids[fname] = fid
        return fid

    unknown_fid = ensure_file("SRS-unknown_未溯源聚合.md", "data/gjb_438c/")
    ext_fid = ensure_file("PoolB_外部公开数据集.md", "data/gjb_438c/easydataset/")

    # doc_num → 文件名映射(聚合块挂到对应文档)
    docnum2fname = {}
    for doc, info in docs.items():
        dn = info["doc_num"] or ""
        if dn:
            docnum2fname[dn] = f"{dn}{doc[len(dn):] if doc.startswith(dn) else doc}.md"

    n_virtual = 0
    chunk_ids = {r[1]: r[0] for r in cur.execute(
        "SELECT id, name FROM Chunks WHERE projectId=?", (pid,))}
    doc_chunk_counts = {}
    for c in chunks:
        dn = (c.get("metadata", {}) or {}).get("doc_num", "")
        doc_chunk_counts[dn] = doc_chunk_counts.get(dn, 0) + 1

    def ensure_chunk(name, fid, content):
        nonlocal n_virtual
        if name in chunk_ids:
            return
        cid = nid()
        cur.execute(
            "INSERT INTO Chunks (id, name, projectId, fileId, fileName, content, summary, size, createAt, updateAt)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, name, pid, fid, "聚合块", content, content[:100], len(content), t, t))
        chunk_ids[name] = cid
        n_virtual += 1

    for name in ds_names:
        if name in chunk_ids:
            continue
        dn = name[4:6] if (name.startswith("SRS-") or name.startswith("UML-")) and len(name) > 6 else ""
        if dn.isdigit() and dn in docnum2fname:
            fid = file_ids[docnum2fname[dn]]
            if name.startswith("UML-"):
                content = f"[UML图锚点源] {name}：Visio XML直读的结构图证据聚合入口。关联QA的chunkContent携带节点/边证据（born-digital，零OCR幻觉）。"
            else:
                content = f"[聚合入口块] {name}：文档级聚合。章节级文本块共{doc_chunk_counts.get(dn, 0)}个（见同文件下），关联QA按other.section可溯源至章节块。"
        elif name == "SRS-unknown":
            fid = unknown_fid
            content = "[未溯源聚合块] 早期生成批次中未保留文档来源的QA聚合（2,708条）。"
        else:
            fid = unknown_fid
            content = f"[聚合块] {name}"
        ensure_chunk(name, fid, content)

    for name in ext_names:
        src = name[4:]
        ensure_chunk(name, ext_fid,
                     f"[Pool B外部源] {src}：经外部适配算子转换的英文QA聚合入口。各记录chunkContent为英文原文证据。")

    db.commit()
    counts = cur.execute("SELECT COUNT(*) FROM Chunks WHERE projectId=?", (pid,)).fetchone()[0]
    print(f"   新增文件{n_files} 真实块{n_chunks} 聚合块{n_virtual} → 库内chunks共{counts}")
    return chunk_ids


# ---------------------------------------------------------------- B. Question链接

def link_questions(db, pid, chunk_ids):
    cur = db.cursor()
    rows = cur.execute(
        "SELECT d.id, d.chunkName, d.question, d.questionLabel, d.other FROM Datasets d"
        " LEFT JOIN Questions q ON d.questionId = q.id"
        " WHERE d.projectId=? AND q.id IS NULL", (pid,)).fetchall()
    print(f"B. 待链接QA记录: {len(rows)}")
    if not rows:
        return 0
    t = now_ms()
    qins, dupd = [], []
    for did, cname, question, qlabel, other in rows:
        # 优先真实章节块: chunkName + '-' + section
        chunk_id = None
        try:
            o = json.loads(other) if other else {}
        except Exception:
            o = {}
        sec = (o or {}).get("section") if isinstance(o, dict) else None
        if sec:
            cand = f"{cname}-{sec}"
            if cand in chunk_ids:
                chunk_id = chunk_ids[cand]
        if chunk_id is None:
            chunk_id = chunk_ids.get(cname) or chunk_ids.get("SRS-unknown")
        if chunk_id is None and chunk_ids:
            chunk_id = next(iter(chunk_ids.values()))
        qid = nid()
        qins.append((qid, pid, chunk_id, question, qlabel or "imported", 1, t, t))
        dupd.append((qid, t, did))
    cur.executemany(
        "INSERT INTO Questions (id, projectId, chunkId, gaPairId, question, label, answered, imageId, imageName, templateId, createAt, updateAt)"
        " VALUES (?,?,?,NULL,?,?,?,NULL,NULL,NULL,?,?)", qins)
    cur.executemany("UPDATE Datasets SET questionId=?, updateAt=? WHERE id=?", dupd)
    db.commit()
    total_q = cur.execute("SELECT COUNT(*) FROM Questions WHERE projectId=?", (pid,)).fetchone()[0]
    total_d = cur.execute("SELECT COUNT(*) FROM Datasets WHERE projectId=?", (pid,)).fetchone()[0]
    print(f"   新建Question {len(qins)} → Questions共{total_q} / Datasets共{total_d}")
    return len(qins)


# ---------------------------------------------------------------- C. 标签树

def sync_tag_tree(pid):
    code, resp = http("GET", f"{ED}/api/projects/{pid}/tags", timeout=30)
    existing = resp.get("tags", []) if isinstance(resp, dict) else []
    flat = {}

    def walk(nodes, parent=None):
        for n in nodes or []:
            flat[n["label"]] = n["id"]
            walk(n.get("children"), n["id"])

    walk(existing)
    tree = {
        "PoolA-域内真实SRS": {
            "consistent-正例": {}, "inconsistent-负例": {}, "原生": {}, "注入": {},
            "UML族": {}, "章节QA族": {}, "easy": {}, "medium": {}, "hard": {},
        },
        "PoolB-域外公开数据": {
            "外部-PURE": {}, "外部-NLIRE": {}, "外部-歧义类": {}, "外部-FlowVQA": {},
            "外部-LLMGen": {}, "easy": {}, "medium": {}, "hard": {},
        },
    }
    n = 0
    for root, children in tree.items():
        rid = flat.get(root)
        if rid is None:
            code, resp = http("PUT", f"{ED}/api/projects/{pid}/tags",
                              {"tags": {"label": root, "parentId": None}}, timeout=30)
            assert code == 200, f"建根标签失败: {root} {resp}"
            rid = resp.get("tags", {}).get("id")
            flat[root] = rid
            n += 1
        for child in children:
            if child not in flat:
                code, resp = http("PUT", f"{ED}/api/projects/{pid}/tags",
                                  {"tags": {"label": child, "parentId": rid}}, timeout=30)
                assert code == 200, f"建子标签失败: {child} {resp}"
                flat[child] = resp.get("tags", {}).get("id")
                n += 1
    print(f"C. 标签树: 新建{n}个节点（已有{len(flat)}命中）")


# ---------------------------------------------------------------- D. Pool B导入

def import_pool_b(pid):
    code, resp = http("GET", f"{ED}/api/projects/{pid}/datasets?page=1&size=1", timeout=60)
    total_before = resp.get("total", 0)
    _db = sqlite3.connect(str(DB_PATH), timeout=30)
    _db.execute("PRAGMA busy_timeout=30000")
    ext_existing = _db.execute(
        "SELECT COUNT(*) FROM Datasets WHERE projectId=? AND model='external-adapt'", (pid,)).fetchone()[0]
    _db.close()
    if ext_existing > 0:
        print(f"D. Pool B已存在({ext_existing}条), 跳过导入")
        return 0
    alpaca = [json.loads(line) for line in open(EXT_ALPACA, encoding="utf-8")]
    sgpt = [json.loads(line) for line in open(EXT_SHAREGPT, encoding="utf-8")]
    assert len(alpaca) == len(sgpt) == 10642, f"外部文件行数异常: {len(alpaca)}/{len(sgpt)}"
    # 校验对齐(同序)
    mismatch = sum(1 for a, s in zip(alpaca, sgpt)
                   if not s["conversations"][0]["value"].startswith(a["instruction"][:30]))
    assert mismatch < 10, f"alpaca/sharegpt行序不匹配({mismatch})"

    records = []
    for a, s in zip(alpaca, sgpt):
        tags = s.get("tags", [])
        source = tags[0] if tags else "外部-未知"
        qtype = tags[1] if len(tags) > 1 else ""
        diff = tags[2] if len(tags) > 2 else "medium"
        records.append({
            "question": a.get("instruction", "").strip(),
            "answer": a.get("output", "").strip(),
            "chunkName": f"EXT-{source}",
            "chunkContent": a.get("input", "") or "[外部英文原文证据见instruction]",
            "model": "external-adapt",
            "questionLabel": qtype,
            "cot": f"来源: {source}｜题型: {qtype}｜难度: {diff}｜语言: 英文",
            "confirmed": True,
            "score": 0.75,
            "tags": ["pool_B", source, qtype, diff, "英文"],
            "other": {"pool": "B", "source": source, "qtype": qtype,
                      "difficulty": diff, "language": "en"},
        })
    ok = 0
    BATCH = 500
    t0 = time.time()
    for bi in range(0, len(records), BATCH):
        chunk = records[bi:bi + BATCH]
        code, resp = http("POST", f"{ED}/api/projects/{pid}/datasets/import",
                          {"datasets": chunk, "sourceInfo": {"source": "pool-B-external", "file": "external_alpaca.jsonl"}})
        assert code == 200, f"Pool B批导入失败: {code} {str(resp)[:150]}"
        ok += resp.get("success", 0)
        print(f"   Pool B批{bi // BATCH + 1}/{(len(records) + BATCH - 1) // BATCH}: +{resp.get('success', 0)} (累计{ok}) [{time.time() - t0:.0f}s]")
    print(f"D. Pool B导入: {ok}条 (库内total {total_before} → {total_before + ok})")
    return ok


# ---------------------------------------------------------------- main

def main():
    pid = get_project_id()
    print(f"项目: {pid}")
    db = sqlite3.connect(str(DB_PATH), timeout=30)
    db.execute("PRAGMA busy_timeout=30000")
    stats = {"projectId": pid}
    try:
        chunk_ids = sync_files_chunks(db, pid)
        stats["phaseA"] = "done"
        stats["linkedA"] = link_questions(db, pid, chunk_ids)
        sync_tag_tree(pid)
        stats["poolBImported"] = import_pool_b(pid)
        # 重新读chunk_ids(EXT块已在A建)并链接Pool B的问题
        cur = db.cursor()
        chunk_ids = {r[1]: r[0] for r in cur.execute(
            "SELECT id, name FROM Chunks WHERE projectId=?", (pid,))}
        stats["linkedB"] = link_questions(db, pid, chunk_ids)
        # F. 验证
        def q(sql):
            return cur.execute(sql, (pid,)).fetchone()[0]
        stats["files"] = q("SELECT COUNT(*) FROM UploadFiles WHERE projectId=?")
        stats["chunks"] = q("SELECT COUNT(*) FROM Chunks WHERE projectId=?")
        stats["questions"] = q("SELECT COUNT(*) FROM Questions WHERE projectId=?")
        stats["datasets"] = q("SELECT COUNT(*) FROM Datasets WHERE projectId=?")
        stats["poolA"] = q("SELECT COUNT(*) FROM Datasets WHERE projectId=? AND model<>'external-adapt'")
        stats["poolB"] = q("SELECT COUNT(*) FROM Datasets WHERE projectId=? AND model='external-adapt'")
        stats["unlinked"] = q("SELECT COUNT(*) FROM Datasets d LEFT JOIN Questions q2 ON d.questionId=q2.id"
                              " WHERE d.projectId=? AND q2.id IS NULL")
        stats["realChunkLinks"] = q("SELECT COUNT(*) FROM Questions qs JOIN Chunks c ON qs.chunkId=c.id"
                                    " WHERE qs.projectId=? AND c.fileName<>'聚合块' AND c.name NOT LIKE 'EXT-%'"
                                    " AND c.name NOT LIKE 'SRS-unknown%' AND c.name NOT LIKE 'UML-%'"
                                    " AND c.name NOT LIKE 'SRS-0%'")  # 章节块名形如 SRS-01xx-3.2.1
        # 简化: 真实章节块=fileName非聚合块
        stats["realChunkLinks"] = q("SELECT COUNT(*) FROM Questions qs JOIN Chunks c ON qs.chunkId=c.id"
                                    " WHERE qs.projectId=? AND c.fileName<>'聚合块'")
        stats["verdict"] = "PASS" if (stats["datasets"] == 28761 and stats["questions"] == 28761
                                      and stats["unlinked"] == 0 and stats["poolB"] == 10642) else "CHECK"
    finally:
        db.close()
    json.dump(stats, open(RESULT_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"结果已保存: {RESULT_OUT}")


if __name__ == "__main__":
    main()
