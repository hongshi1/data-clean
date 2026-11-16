"""D3训练集扩容: crossdoc构造协议×16文档×4x配额.

复用build_crossdoc_evalset的确定性构造机械(候选生成/自检/
配额选择), 扩容维度:
  - 文档: 全16份(04号含dev-45已是同域训练, 04的构造实例
    属同域训练, test-46为91QA管线构造无碰撞)
  - 配额: 每标签×4(10→40/标签/文档, 120/文档, 池不足时自适应)
  - id前缀: D3TR-{doc}-N(与冻结crossdoc C{doc}QA-*及91QA
    S1QA-*零碰撞; 按question+answer哈希去重)

产出: data/gjb_438c/distillation/d3_train_instances_v1.jsonl
(QAInput格式行+sound_label, 供d3_teacher_labels标注)
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE / "tools"), str(BASE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from build_crossdoc_evalset import (  # noqa: E402
    build_evalset,
    derive_build_config,
    extract_narrative_corpus,
    resolve_doc_spec,
)
from build_crossdoc_evalset import SOURCE_GLOB_TEMPLATE  # noqa: E402
import glob  # noqa: E402

OUT = BASE / "data/gjb_438c/distillation/d3_train_instances_v1.jsonl"
SCALE = 4
ALL_DOCS = ("01", "02", "03", "04", "05", "06", "07", "08",
            "09", "10", "11", "12", "13", "14", "15", "16")


def _scale_quotas(cfg):
    scaled = {}
    for label, quota_list in cfg.quotas.items():
        scaled[label] = [(family, n * SCALE)
                         for family, n in quota_list]
    return replace(cfg, quotas=scaled)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []
    seen: set[str] = set()
    label_counts: Counter = Counter()
    for doc_no in ALL_DOCS:
        matches = glob.glob(SOURCE_GLOB_TEMPLATE.format(doc=doc_no))
        if not matches:
            print(f"{doc_no}号: 无content_list, 跳过")
            continue
        source = Path(matches[0])
        try:
            spec = resolve_doc_spec(doc_no, source)
            blocks = json.loads(source.read_text(encoding="utf-8"))
            facts_probe, pools_probe = extract_narrative_corpus(
                blocks, spec.doc_id)
            cfg = derive_build_config(
                spec, [f.family for f in facts_probe],
                pools_probe.doc_text)
            cfg = _scale_quotas(cfg)
            rows, stats = build_evalset(source, cfg, doc_no)
        except (ValueError, RuntimeError, LookupError) as exc:
            print(f"{doc_no}号: 构造失败 {type(exc).__name__}: "
                  f"{str(exc)[:100]}")
            continue
        n_added = 0
        for row in rows:
            digest = hashlib.md5(
                (row["question"] + "|" + row["answer"])
                .encode("utf-8")).hexdigest()[:12]
            if digest in seen:
                continue
            seen.add(digest)
            row = dict(row)
            row["instance_id"] = f"D3TR-{doc_no}-{digest[:6]}"
            label_counts[row["sound_label"]] += 1
            rows_out.append(row)
            n_added += 1
        print(f"{doc_no}号: 生成{len(rows)} 新增{n_added} "
              f"(累计{len(rows_out)})", flush=True)

    with open(OUT, "w", encoding="utf-8") as fout:
        for row in rows_out:
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"总计 {len(rows_out)} 条 → {OUT}")
    print(f"标签分布: {dict(label_counts)}")


if __name__ == "__main__":
    main()
