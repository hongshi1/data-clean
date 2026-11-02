#!/usr/bin/env python3
"""违例评测集(17真实违例)导入后端DB作三态演示seed.

对应文档: 76号扩展点#2. 数据: violation_evalset_v1.jsonl
(设计gold=refute, 结构化证据块, 源文档已块级验证).

导入为doc04源下的qa_pairs(qa_id=DOC04-VIO-XX), evidence存
完整冻结格式JSON(verify直接消费, 不走召回). 幂等: 已存在跳过.

用法: python tools/seed_violations_to_db.py [--dev-db]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
BACKEND = BASE / "deploy/nkuDataProject/backend"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"

sys.path.insert(0, str(BACKEND))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dev-db", action="store_true",
                    help="开发SQLite模式(DEV_DB=sqlite)")
    args = ap.parse_args()
    if args.dev_db:
        os.environ.setdefault("DEV_DB", "sqlite")

    from database import SessionLocal, dumps
    from models import QaPair, QaSource

    rows = [json.loads(line) for line in VIO.open(encoding="utf-8")]
    db = SessionLocal()
    try:
        src = db.query(QaSource).filter_by(source_id="04").first()
        if src is None:
            print("数据源04不存在(先运行ingest)")
            return 1
        n_new = n_skip = 0
        for r in rows:
            exists = (db.query(QaPair)
                      .filter_by(qa_id=r["instance_id"]).first())
            if exists is not None:
                n_skip += 1
                continue
            db.add(QaPair(
                source_id=src.id,
                qa_id=r["instance_id"],
                question=r["question"],
                answer=r["answer"],
                evidence=dumps(r["evidence"]),
                scene="srs",
                attrs=dumps({
                    "seed": "violation_evalset_v1",
                    "expected_verdict": r["expected_verdict"],
                    "item_id": r["item_id"],
                }),
                check_status="unchecked",
            ))
            n_new += 1
        db.commit()
        total = (db.query(QaPair)
                 .filter_by(source_id=src.id).count())
        print(f"导入: 新增{n_new}条, 跳过{n_skip}条(已存在); "
              f"doc04现共{total}条qa_pairs")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
