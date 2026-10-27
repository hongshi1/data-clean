#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SRS QA数据集 → EasyDataset迁移

将我们的6189条QA对(srs_qa_final.json)转换为EasyDataset格式并批量导入。

EasyDataset的Datasets schema:
  question: string (必填)
  answer: string (必填)
  chunkName: string (默认'Imported Data')
  chunkContent: string (默认'Imported from external source')
  model: string (默认'imported')
  questionLabel: string
  cot: string (Chain of Thought)
  confirmed: boolean
  score: float
  tags: JSON数组或字符串
  other: JSON对象
  note: string

迁移策略:
  1. 先启动EasyDataset(npm run start, port 1717)
  2. 创建项目(POST /api/projects)
  3. 批量导入(POST /api/projects/{id}/datasets/import)
"""
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QA_PATH = os.path.join(BASE, "data/gjb_438c/data_assets/srs_qa_final.json")
ED_URL = "http://localhost:1717"


def convert_qa_to_easydataset(qa_entry, is_injected=False):
    """单条QA → EasyDataset格式"""
    tags = []
    if qa_entry.get("scenario"):
        tags.append(f"场景sc{qa_entry['scenario']}")
    if qa_entry.get("type"):
        tags.append(qa_entry["type"])
    if qa_entry.get("label"):
        tags.append(qa_entry["label"])
    if qa_entry.get("difficulty"):
        tags.append(qa_entry["difficulty"])
    if is_injected:
        tags.append("注入")
    else:
        tags.append("原生")

    # CoT: 用evidence构建推理链
    ev = qa_entry.get("evidence", "")
    cot = ""
    if ev:
        if isinstance(ev, str):
            cot = f"证据来源: {ev[:100]}"
        else:
            cot = f"证据来源: {json.dumps(ev, ensure_ascii=False)[:100]}"

    # other: 附加元数据
    other = {
        "doc": qa_entry.get("doc", ""),
        "section": qa_entry.get("section", ""),
        "pair_id": qa_entry.get("pair_id", ""),
        "image_caption": qa_entry.get("image_caption", ""),
        "table_caption": qa_entry.get("table_caption", ""),
    }
    if is_injected:
        other["inconsistency_type"] = qa_entry.get("inconsistency_type", "")
        other["subtype"] = qa_entry.get("subtype", "")
        other["rule_id"] = qa_entry.get("rule_id", "")
        other["inject_detail"] = qa_entry.get("inject_detail", "")

    # chunkContent: 用evidence做上下文
    chunk_content = str(ev)[:500] if ev else "SRS文档问答对"

    return {
        "question": qa_entry.get("question", "").strip(),
        "answer": qa_entry.get("answer", "").strip(),
        "chunkName": f"SRS-{qa_entry.get('doc', 'unknown')[:8]}",
        "chunkContent": chunk_content,
        "model": "srs-pipeline",
        "questionLabel": qa_entry.get("type", qa_entry.get("inconsistency_type", "")),
        "cot": cot,
        "confirmed": True,
        "score": 0.8,
        "tags": tags,
        "other": other,
        "note": qa_entry.get("inject_detail", "")[:100] if is_injected else "",
    }


def create_project(name, description):
    """在EasyDataset中创建项目"""
    body = json.dumps({"name": name, "description": description}).encode()
    req = urllib.request.Request(
        f"{ED_URL}/api/projects",
        data=body,
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=30)
    j = json.loads(resp.read())
    return j.get("id") or j.get("project", {}).get("id")


def import_datasets(project_id, datasets):
    """批量导入数据"""
    body = json.dumps({"datasets": datasets, "sourceInfo": {"source": "srs-pipeline"}}).encode()
    req = urllib.request.Request(
        f"{ED_URL}/api/projects/{project_id}/datasets/import",
        data=body,
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=300)
    return json.loads(resp.read())


def main(sample_size=None):
    qa_all = json.load(open(QA_PATH, encoding="utf-8"))

    # 分离原生和注入
    native = [x for x in qa_all if x.get("source") == "pair_generated"]
    injected = [x for x in qa_all if x.get("is_injected")]
    print(f"总QA: {len(qa_all)} | 原生: {len(native)} | 注入: {len(injected)}")

    if sample_size:
        import random
        rng = random.Random(42)
        native = rng.sample(native, min(len(native), sample_size // 2))
        injected = rng.sample(injected, min(len(injected), sample_size // 2))
        print(f"采样: {len(native)}原生 + {len(injected)}注入")

    # 转换
    datasets = []
    for x in native:
        d = convert_qa_to_easydataset(x, is_injected=False)
        if d["question"] and d["answer"]:
            datasets.append(d)
    for x in injected:
        d = convert_qa_to_easydataset(x, is_injected=True)
        if d["question"] and d["answer"]:
            datasets.append(d)
    print(f"转换后有效: {len(datasets)}条")

    # 保存转换结果(可离线使用)
    out_path = os.path.join(BASE, "data/gjb_438c/data_assets/srs_qa_easydataset.json")
    json.dump(datasets, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"EasyDataset格式已保存: {out_path}")

    # 尝试在线导入
    try:
        project_id = create_project(
            "SRS一致性校验微调数据集",
            "基于16份GJB 438C SRS的多模态QA对(含一致/不一致标注), 用于微调需求一致性校验模型")
        print(f"项目已创建: {project_id}")

        # 分批导入(每批100条)
        batch = 100
        total_imported = 0
        for i in range(0, len(datasets), batch):
            chunk = datasets[i:i + batch]
            result = import_datasets(project_id, chunk)
            if isinstance(result, dict):
                total_imported += result.get("successCount", 0)
            print(f"  批{i // batch + 1}: 导入{len(chunk)}条 (累计{total_imported})")

        print(f"\n✅ 迁移完成: {total_imported}条 → EasyDataset项目{project_id}")
    except Exception as e:
        print(f"\n⚠️ 在线导入失败(EasyDataset未启动?): {str(e)[:100]}")
        print(f"   离线文件已保存: {out_path}")
        print("   启动EasyDataset后重新运行即可在线导入")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, help="采样数量(默认全量)")
    args = ap.parse_args()
    main(sample_size=args.sample)
