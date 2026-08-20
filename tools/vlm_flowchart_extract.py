#!/usr/bin/env python3
"""流程图VLM批量提取

用kimi-k2.6对140张流程图做结构化提取:
  - nodes: 节点名称列表
  - edges: 边列表[[源, 目标], ...]
  - branches: 分支条件
  - start_node: 起始节点
  - end_nodes: 结束节点列表
  - data_flow_direction: 单向/双向/分支

输出: data/gjb_438c/data_assets/vlm_flowchart_extract.jsonl
"""
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
IMAGE_ANALYSES = BASE / "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"
OUT_PATH = BASE / "data/gjb_438c/data_assets/vlm_flowchart_extract.jsonl"

PROMPT = """分析这张流程图，提取结构化信息，输出JSON:
{
  "nodes": ["节点名称列表"],
  "edges": [["源节点", "目标节点"]],
  "branches": ["分支条件"],
  "start_node": "起始节点",
  "end_nodes": ["结束节点"],
  "data_flow_direction": "单向/双向/分支"
}"""


def extract_flowchart(img_path):
    """用kimi VLM提取流程图结构化信息"""
    b64 = base64.b64encode(open(img_path, "rb").read()).decode()
    payload = {
        "model": "kimi-k2.6",
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": PROMPT},
        ]}],
        "max_tokens": 1000,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(3):
        try:
            r = requests.post(KIMI_URL,
                headers={"Authorization": f"Bearer {KIMI_KEY}", "Content-Type": "application/json"},
                json=payload, timeout=90)
            if r.ok:
                content = r.json()["choices"][0]["message"].get("content", "")
                if content:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"nodes": [], "edges": [], "branches": [],
                                "start_node": "", "end_nodes": [], "data_flow_direction": "",
                                "raw": content[:200]}
            time.sleep(3)
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
    return None


def main():
    # 加载图片分类
    with open(IMAGE_ANALYSES) as f:
        data = json.load(f)

    # 找流程图
    flowcharts = []
    for a in data["analyses"]:
        ft = a.get("analysis", {}).get("figure_type", "") if isinstance(a.get("analysis"), dict) else ""
        caption = str(a.get("caption", ""))
        if "流程" in ft or "流程" in caption:
            flowcharts.append(a)

    print(f"找到 {len(flowcharts)} 张流程图")

    # 检查已完成的
    done = set()
    if OUT_PATH.exists():
        with open(OUT_PATH) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done.add(rec["image_path"])
                except Exception:
                    pass
    print(f"已完成: {len(done)}, 待处理: {len(flowcharts) - len(done)}")

    # 批量提取
    with open(OUT_PATH, "a") as fout:
        for i, fc in enumerate(flowcharts):
            img_path = fc["image_path"]
            if img_path in done:
                continue

            # 检查文件是否存在
            full_path = BASE / img_path if not os.path.isabs(img_path) else img_path
            if not os.path.exists(full_path):
                full_path = img_path
            if not os.path.exists(full_path):
                print(f"[{i+1}/{len(flowcharts)}] 文件不存在: {img_path}")
                continue

            print(f"[{i+1}/{len(flowcharts)}] {img_path.split('/')[-1]} ...", end=" ", flush=True)
            result = extract_flowchart(full_path)

            if result:
                record = {
                    "image_path": img_path,
                    "doc": fc.get("doc", ""),
                    "section": fc.get("section", ""),
                    "caption": str(fc.get("caption", "")),
                    "nodes": result.get("nodes", []),
                    "edges": result.get("edges", []),
                    "branches": result.get("branches", []),
                    "start_node": result.get("start_node", ""),
                    "end_nodes": result.get("end_nodes", []),
                    "data_flow_direction": result.get("data_flow_direction", ""),
                }
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                fout.flush()
                print(f"OK nodes={len(record['nodes'])} edges={len(record['edges'])}")
                done.add(img_path)
            else:
                print("FAIL")

            time.sleep(1)  # 避免API限速

    print(f"\n完成! 共 {len(done)} 张流程图提取结果在 {OUT_PATH}")


if __name__ == "__main__":
    main()
