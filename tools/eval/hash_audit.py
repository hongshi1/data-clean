r"""评测结果文件的查询集哈希审计(出处验证).

背景: S4考古发现(28号文档) — 旧结果文件的query_set_hash可能
生成于早期数据状态, 与当前数据集实际哈希不一致, 导致"锁定数字"
与数据漂移脱钩. 本工具系统性核验全部S*.json:

  S1: table_deep_v3     S3: table_deep_v1
  S4: image             S5: table_deep_v4
  S6: {v3, v4}联合

用法: python tools/eval/hash_audit.py [--dataset gjb_ure_v4.json]
退出码: 0=全部PASS, 1=存在FAIL
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"

# 结果文件 → 场景集合的映射(协议登记处)
SCENE_REGISTRY = {
    "S1_deep_v3_all.json": {"table_deep_v3"},
    "S3_deep_v1_all.json": {"table_deep_v1"},
    "S4_image_all.json": {"image"},
    "S5_deep_v4_all.json": {"table_deep_v4"},
    "S6_deep_v34_all.json": {"table_deep_v3", "table_deep_v4"},
}


def query_set_hash(queries: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(q["query"] for q in queries),
                   ensure_ascii=False).encode()).hexdigest()[:16]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="gjb_ure_v4.json")
    args = ap.parse_args()

    ds = json.loads((V3 / args.dataset).read_text(encoding="utf-8"))
    queries = ds["queries"]

    n_fail = 0
    print(f"哈希审计 (数据集: {args.dataset})\n" + "=" * 56)
    for fname, scenes in sorted(SCENE_REGISTRY.items()):
        path = RESULTS / fname
        if not path.exists():
            print(f"  [缺失] {fname}")
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        stored = d.get("protocol", {}).get("query_set_hash")
        scene_qs = [q for q in queries
                    if q["scene"] in scenes and q["split"] == "eval"]
        if not scene_qs:
            print(f"  [跳过] {fname}: 数据集无对应场景查询")
            continue
        actual = query_set_hash(scene_qs)
        status = "PASS" if stored == actual else "FAIL"
        if status == "FAIL":
            n_fail += 1
        print(f"  [{status}] {fname}: {len(scene_qs)}q "
              f"stored={str(stored)[:10]} actual={actual[:10]}")

    print("=" * 56)
    print(f"结果: {'全部PASS' if n_fail == 0 else f'{n_fail}个FAIL'}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
