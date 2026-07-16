#!/Users/gexuancheng/Desktop/research2/data-juicer/.venv/bin/python3
"""NLMCXR val.parquet -> Data-Juicer JSONL 转换脚本.

读取 nlmcxr/val.parquet (1505条X光片+报告), 转为 Data-Juicer 兼容的 JSONL:
  {"text":"放射报告原文...", "images":["nlmcxr/images/image_0.jpg"], "meta":{"idx":0}}

- 从parquet的image列提取bytes(bytes字段为PNG), 保存为JPG文件到 nlmcxr/images/ 目录
- text字段放报告原文
- 默认只处理前20条(测试用), 可通过 --all 处理全量
- 输出: nlmcxr/nlmcxr_dj.jsonl
"""
import io
import json
import os
import sys

import pandas as pd
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
PARQUET_PATH = os.path.join(BASE, "nlmcxr", "val.parquet")
OUT_PATH = os.path.join(BASE, "nlmcxr", "nlmcxr_dj.jsonl")
IMG_DIR = os.path.join(BASE, "nlmcxr", "images")

DEFAULT_N = 20


def convert(n=DEFAULT_N):
    df = pd.read_parquet(PARQUET_PATH)
    os.makedirs(IMG_DIR, exist_ok=True)
    total = min(n, len(df))
    with open(OUT_PATH, "w", encoding="utf-8") as fout:
        for i in range(total):
            row = df.iloc[i]
            report = str(row["text"]) if pd.notna(row["text"]) else ""
            img_field = row["image"]
            img_bytes = img_field["bytes"] if isinstance(img_field, dict) else img_field
            img_name = f"image_{i}.jpg"
            img_path = os.path.join(IMG_DIR, img_name)
            if not os.path.isfile(img_path):
                pil = Image.open(io.BytesIO(img_bytes)).convert("L")
                pil.save(img_path, "JPEG")
            rel_path = os.path.join("nlmcxr", "images", img_name)
            rec = {
                "text": report,
                "images": [rel_path],
                "meta": {"idx": i},
            }
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return total


if __name__ == "__main__":
    n = DEFAULT_N
    if "--all" in sys.argv:
        n = 1505
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        n = int(sys.argv[1])
    total = convert(n=n)
    print(f"转换完成: {total} 条 -> {OUT_PATH}")
    print(f"图片目录: {IMG_DIR}")
