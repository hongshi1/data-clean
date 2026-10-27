#!/usr/bin/env python3
"""
M2: VLM感知通道 (ACDD Tier 2 前置)
===================================
用kimi-k2.6对89张sc2图做结构化提取(约束JSON输出),
输出与锚点(M0)同构的图结构 — 供M3校准(通道vs金标准)与M5锚遮蔽评测。

输出: data/gjb_438c/anchor_sc2/vlm_extractions.json
  每对: {pair_key, diagram_type, nodes:[{id,text,type,pos}], edges:[{src,dst,label}], raw}

用法: python3 tools/m2_vlm_channel.py [--limit N]
"""
import argparse
import base64
import json
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/vlm_extractions.json"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
from ai_config import KIMI_KEY
KIMI_MODEL = "kimi-k2.6"

PROMPT = """你是软件需求文档图表解析专家。请精确提取这张SRS文档中的图表结构。

要求:
1. 提取所有带文字的节点, 文字必须与图中完全一致(逐字, 不要改写、不要翻译、不要概括)
2. 判断图的类型: flowchart(流程图/状态图) 或 usecase(用例图)
3. 提取所有箭头连接: src是箭头尾部节点id, dst是箭头头部指向的节点id
4. 边上有文字标签(如"是/否/失败")时填入label, 没有则留空字符串
5. 节点类型: process(过程/任务/状态框), decision(判定), start(开始/初始), end(结束/最终), actor(参与者/小人), usecase(用例椭圆)
6. pos为节点在图中的大致纵向位置: top/middle/bottom

严格输出JSON:
{
  "diagram_type": "flowchart 或 usecase",
  "nodes": [{"id": "n1", "text": "节点文字", "type": "process", "pos": "top"}],
  "edges": [{"src": "n1", "dst": "n2", "label": ""}]
}"""


def extract_one(image_path: Path, pair_key: str) -> dict:
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    messages = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": PROMPT},
    ]}]
    for attempt in range(3):
        try:
            r = httpx.post(KIMI_URL, headers={
                "Authorization": f"Bearer {KIMI_KEY}", "Content-Type": "application/json"
            }, json={
                "model": KIMI_MODEL, "thinking": {"type": "disabled"},
                "messages": messages, "max_tokens": 3000, "temperature": 0.6,
                "response_format": {"type": "json_object"},
            }, timeout=180)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"].get("content", "")
                data = json.loads(content)
                nodes = data.get("nodes", [])
                edges = data.get("edges", [])
                # 规范化: id存在性检查
                ids = {n.get("id") for n in nodes}
                edges = [e for e in edges
                         if e.get("src") in ids and e.get("dst") in ids
                         and e.get('src') != e.get('dst')]
                return {
                    'pair_key': pair_key,
                    'diagram_type': data.get("diagram_type", "unknown"),
                    'nodes': [{'id': n.get('id', ''), 'text': (n.get('text') or '').strip(),
                               'type': n.get('type', 'other'), 'pos': n.get('pos', '')}
                              for n in nodes if (n.get('text') or '').strip()],
                    'edges': [{'src': e.get('src'), 'dst': e.get('dst'),
                               'label': (e.get('label') or '').strip()} for e in edges],
                    'raw': content[:2000],
                }
            else:
                print(f"    HTTP {r.status_code}: {r.text[:100]}")
        except json.JSONDecodeError as e:
            print(f"    JSON解析失败(重试{attempt+1}): {e}")
        except Exception as e:
            print(f"    异常(重试{attempt+1}): {e}")
            time.sleep(5)
    return {'pair_key': pair_key, 'error': 'failed', 'nodes': [], 'edges': []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只跑前N对(0=全部)')
    args = ap.parse_args()

    mapping = json.loads(MAPPING_PATH.read_text())
    pair_keys = sorted(mapping.keys())
    if args.limit:
        pair_keys = pair_keys[:args.limit]

    # 断点续跑
    results = {}
    if OUT_PATH.exists():
        results = json.loads(OUT_PATH.read_text())
        print(f"已有{len(results)}条结果, 断点续跑")

    print(f"{'='*64}")
    print(f"M2: Kimi VLM通道结构化提取 ({len(pair_keys)}对)")
    print(f"{'='*64}")

    for i, pk in enumerate(pair_keys):
        if pk in results and 'error' not in results[pk]:
            continue
        img_path = PAIR_DIR / mapping[pk].get('pair_dir', pk) / 'image.png'
        if not img_path.exists():
            print(f"  [{i+1}/{len(pair_keys)}] {pk}: 无图片")
            continue
        t0 = time.time()
        r = extract_one(img_path, pk)
        results[pk] = r
        dt = time.time() - t0
        ok = '✓' if 'error' not in r else '✗'
        print(f"  [{i+1}/{len(pair_keys)}] {ok} {pk}: "
              f"{len(r.get('nodes', []))}节点 {len(r.get('edges', []))}边 "
              f"({r.get('diagram_type', '?')}, {dt:.0f}s)")
        # 每10条落盘
        if (i + 1) % 10 == 0:
            OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1))

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    ok_n = sum(1 for r in results.values() if 'error' not in r)
    total_nodes = sum(len(r.get('nodes', [])) for r in results.values())
    total_edges = sum(len(r.get('edges', [])) for r in results.values())
    print(f"\n  完成: {ok_n}/{len(results)}成功, 共{total_nodes}节点 {total_edges}边")
    print(f"  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
