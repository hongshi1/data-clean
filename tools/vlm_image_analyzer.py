#!/usr/bin/env python3
"""SRS图片批量VLM分析 (多模态增强)

用kimi-k2.6对SRS文档图片(用例图/接口图/流程图/状态图)做视觉理解:
- 识别图类型
- 提取图中的关键元素(参与者/功能/接口/状态)
- 生成结构化描述(可注入RAG图谱)

复用: kimi-k2.6视觉API + 已有mineru图片

输出: data/gjb_438c/data_assets/chunks/srs_image_analyses.json
"""
import argparse
import base64
import glob
import json
import os
import sys
import time

API_KEY = "sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"
URL = "https://api.moonshot.cn/v1/chat/completions"
MODEL = "kimi-k2.6"
IMAGE_DIR = "data/gjb_438c/mineru_standard"
OUT_PATH = "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"

PROMPT = """你是SRS软件需求规格说明文档的图表分析专家。请分析这张图, 输出JSON(不要思考过程, 只输出JSON):
{
  "figure_type": "图类型(用例图/接口图/流程图/状态图/时序图/架构图/数据流图/其他)",
  "key_elements": ["图中的关键元素列表(参与者/功能名称/接口名称/状态名称等)"],
  "summary": "一句话总结图的内容(50字内)"
}"""


def analyze_image(img_path, use_requests=True):
    import requests
    b64 = base64.b64encode(open(img_path, "rb").read()).decode()
    payload = {
        "model": MODEL,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": PROMPT},
        ]}],
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(3):
        try:
            r = requests.post(URL, headers={"Authorization": f"Bearer {API_KEY}"},
                              json=payload, timeout=120)
            if r.ok:
                content = r.json()["choices"][0]["message"].get("content", "")
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"figure_type": "未知", "key_elements": [], "summary": content[:100]}
            time.sleep(5)
        except Exception as e:
            time.sleep(5)
    return {"figure_type": "分析失败", "key_elements": [], "summary": ""}


def find_images():
    """找所有mineru标准解析的图片"""
    images = []
    for cl_path in sorted(glob.glob(os.path.join(IMAGE_DIR, "*/office/*content_list.json"))):
        doc = os.path.basename(cl_path).replace("_content_list.json", "")[:25]
        cl = json.loads(open(cl_path).read())
        office_dir = os.path.dirname(cl_path)
        for item in cl:
            if isinstance(item, dict) and item.get("type") == "image":
                rel = item.get("image_path", "")
                if not rel:
                    continue
                img_path = os.path.join(office_dir, rel)
                if img_path and os.path.exists(img_path):
                    images.append({
                        "doc": doc,
                        "image_path": img_path,
                        "caption": item.get("image_caption", ""),
                    })
    return images


def main(limit=None, resume=True):
    images = find_images()
    print(f"共发现 {len(images)} 张图片")

    # 断点续跑
    analyses = []
    if resume and os.path.exists(OUT_PATH):
        old = json.loads(open(OUT_PATH).read()).get("analyses", [])
        analyses = list(old)  # 保留已有结果
        done = {r["image_path"] for r in old}
        remaining = [i for i in images if i["image_path"] not in done]
        print(f"已分析 {len(done)}, 剩余 {len(remaining)}")
        images = remaining

    if limit:
        images = images[:limit]
    t0 = time.time()
    for idx, img in enumerate(images):
        res = analyze_image(img["image_path"])
        rec = {**img, "analysis": res}
        analyses.append(rec)
        print(f"[{idx+1}/{len(images)}] {img['doc'][:10]} {os.path.basename(img['image_path'])} → {res.get('figure_type', '?')}")
        # 每10个保存一次(断点)
        if (idx + 1) % 10 == 0:
            _save(analyses)
            print(f"  ...已保存{idx+1}, 耗时{time.time()-t0:.0f}s")

    _save(analyses)
    print(f"\n✅ 完成: {len(analyses)}张图片, 总耗时{time.time()-t0:.0f}s")
    # 统计
    types = {}
    for a in analyses:
        t = a["analysis"].get("figure_type", "?")
        types[t] = types.get(t, 0) + 1
    print("图类型分布:", types)


def _save(analyses):
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    # 合并磁盘上已有结果(避免覆盖丢失)
    merged = analyses
    try:
        if os.path.exists(OUT_PATH):
            old = json.loads(open(OUT_PATH).read()).get("analyses", [])
            old_keys = {r["image_path"] for r in old}
            merged = old + [a for a in analyses if a["image_path"] not in old_keys]
    except Exception:
        pass
    json.dump({"analyses": merged}, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()
    main(limit=args.limit, resume=not args.no_resume)
