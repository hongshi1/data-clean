#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出对照: EasyDataset全量导出 vs 源datasets_easydataset.json vs ground truth srs_alpaca.jsonl

验证:
  1. 分批导出(blatMode)累计条数 = 18,119
  2. 往返完整性: 导出记录的 question/answer/chunkName/cot/score/confirmed 与源文件一致(按qa哈希匹配)
  3. ground truth: srs_alpaca.jsonl 行数 = 18,119, 且instruction/output与导出question/answer一一对应
"""
import json
import sys
import hashlib
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
ED = "http://localhost:1717"
PID = "xZb5IZMWfTmO"
SRC = BASE / "data/gjb_438c/easydataset/datasets_easydataset.json"
ALPACA = BASE / "data/gjb_438c/easydataset/srs_alpaca.jsonl"
OUT = BASE / "data/gjb_438c/easydataset/export_roundtrip.json"


def http(method, url, payload=None, timeout=300):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def qa_key(q, a):
    return hashlib.md5((q.strip() + "\x00" + a.strip()).encode("utf-8")).hexdigest()


def main():
    # 1. 分批导出全部
    exported, offset = [], 0
    batch = 2000
    while True:
        resp = http("POST", f"{ED}/api/projects/{PID}/datasets/export",
                    {"batchMode": True, "offset": offset, "batchSize": batch})
        data = resp.get("data", [])
        exported.extend(data)
        offset = resp.get("offset", offset + len(data))
        print(f"  导出批次: +{len(data)} (累计{len(exported)}) hasMore={resp.get('hasMore')}")
        if not resp.get("hasMore") or not data:
            break
    print(f"导出总计: {len(exported)}条")

    # 2. 与源文件往返比对（导出API只投影5字段: question/answer/chunkName/cot/questionLabel）
    #    用多重集(Counter)比对，天然处理源中3,311条重复qa键+导出顺序差异
    from collections import Counter
    src = json.load(open(SRC, encoding="utf-8"))
    FIELDS = ["question", "answer", "chunkName", "cot", "questionLabel"]

    def tup(r):
        return tuple((r.get(f) or "") if not isinstance(r.get(f), str) else r.get(f).strip() for f in FIELDS)

    src_counter = Counter(tup(r) for r in src)
    exp_counter = Counter(tup(r) for r in exported)
    count_match = len(exported) == len(src)
    missing = src_counter - exp_counter   # 源有导出缺
    extra = exp_counter - src_counter     # 导出多出
    print(f"计数: 导出{len(exported)} vs 源{len(src)} → {'一致' if count_match else '不一致'}")
    print(f"5字段多重集: 源缺{sum(missing.values())}条 | 导出多{sum(extra.values())}条 | 完全匹配: {not missing and not extra}")
    if missing:
        for t, n in list(missing.items())[:3]:
            print(f"  源缺样例x{n}: q={t[0][:40]} chunk={t[2][:20]}")
    if extra:
        for t, n in list(extra.items())[:3]:
            print(f"  导出多样例x{n}: q={t[0][:40]} chunk={t[2][:20]}")

    # qa键集核对（question+answer）
    def qa_key(r):
        return hashlib.md5(((r.get("question") or "").strip() + "\x00" + (r.get("answer") or "").strip()).encode("utf-8")).hexdigest()
    keys_src, keys_exp = {qa_key(r) for r in src}, {qa_key(r) for r in exported}
    print(f"qa键集: 仅源{len(keys_src - keys_exp)} | 仅导出{len(keys_exp - keys_src)}")

    # 3. ground truth对照
    alpaca = [json.loads(line) for line in open(ALPACA, encoding="utf-8")]
    gt_keys = {qa_key({"question": a.get("instruction", ""), "answer": a.get("output", "")}) for a in alpaca}
    gt_match = gt_keys == keys_exp
    print(f"ground truth srs_alpaca.jsonl: {len(alpaca)}行, instruction/output键集与导出一致: {gt_match}")

    verdict = "PASS" if (count_match and not missing and not extra
                         and not (keys_src - keys_exp) and not (keys_exp - keys_src)
                         and gt_match and len(alpaca) == 18119) else "CHECK"
    result = {
        "projectId": PID, "exportedCount": len(exported), "sourceCount": len(src),
        "countMatch": count_match,
        "multisetMissing": sum(missing.values()), "multisetExtra": sum(extra.values()),
        "qaKeyOnlyInSource": len(keys_src - keys_exp), "qaKeyOnlyInExport": len(keys_exp - keys_src),
        "duplicateQaPairsInSource": len(src) - len(keys_src),
        "alpacaLines": len(alpaca), "alpacaKeyMatch": gt_match,
        "verdict": verdict,
    }
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n导出对照: {verdict} | 结果已保存: {OUT}")


if __name__ == "__main__":
    main()
