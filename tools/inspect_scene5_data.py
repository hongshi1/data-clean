"""Inspect scenario-5 sample data files (sleep-*.jsonl + test images)."""
from __future__ import annotations

import json
import os
import re
from collections import Counter

BASE = (r"C:\baidunetdiskdownload\5个场景数据集"
        r"\20260924-场景5样例数据及需求说明文档")


def main() -> None:
    total = 0
    for f in sorted(os.listdir(BASE)):
        path = os.path.join(BASE, f)
        if not f.endswith(".jsonl"):
            continue
        lines = open(path, encoding="utf-8").readlines()
        total += len(lines)
        answers: list[int] = []
        for line in lines:
            rec = json.loads(line)
            try:
                gpt = rec["conversations"][1]["value"]
                m = re.search(r'"answer":\s*(\d)', gpt)
                if m:
                    answers.append(int(m.group(1)))
            except (KeyError, IndexError):
                pass
        print(f"{f}: {len(lines)}条 | answer分布: "
              f"{dict(Counter(answers))}")
    print("总计:", total)
    tdir = os.path.join(BASE, "test")
    jpgs = [f for f in os.listdir(tdir) if f.endswith(".jpg")]
    print("test/图片数:", len(jpgs))
    first = open(os.path.join(BASE, "sleep-after-all.jsonl"),
                 encoding="utf-8").readline()
    rec = json.loads(first)
    print("image字段:", rec.get("image", ""))


if __name__ == "__main__":
    main()
