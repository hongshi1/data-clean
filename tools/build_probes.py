r"""P0冻结探针集构建器: 三个外部NLI探针(eval-only, 永不进训练).

定位: docs/srs_project/pair_dataset_augmentation_plan.md §1.4 U1(探针)/§5.1 P0.
  1. paws_shortcut        PAWS-X zh 释义对100 + 非释义对100, 重铸T2 → 量化"词面重叠⇒误报"捷径
                          (shortcut分 = 释义对被判inconsistent的比例)
  2. feverous_table       FEVEROUS 表格蕴含 SUPPORTS100 + REFUTES100 → 表格证据↔文本声明核对能力
  3. ocnli_contradiction  OCNLI contradiction 200条(两侧15-60字), 重铸T2 → "词面相似但语义分歧"漏报

冻结协议: 构建一次即冻结(默认已存在则跳过); 重建有 --force, 须同步MANIFEST与快照测试.
确定性: 每探针独立 random.Random(f"p0probe:{probe_type}") + 输入按行序遍历 → 同输入同输出.

用法:
  python tools/build_probes.py            # 构建 data/gjb_438c/probes/*.json
  python tools/build_probes.py --force    # 强制重建(冻结资产的显式变更)
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PUB = BASE / "data/gjb_438c/public_nli"
OUT_DIR = BASE / "data/gjb_438c/probes"

FREEZE_DECLARATION = (
    "冻结评测资产(eval-only): 本集永不进入任何训练/微调/验证集, 仅允许推理期评测; "
    "任何修改须以--force显式重建并同步MANIFEST与快照测试"
)

ITEM_KEYS = ["id", "premise", "hypothesis", "label", "probe_type"]


def git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def t2_cast(sentence1: str, sentence2: str) -> tuple[str, str]:
    """T2规定式重铸: 两侧各自陈述为文档不同章节的规定."""
    return (f"文档某章节规定：「{sentence1}」",
            f"文档另一章节规定：「{sentence2}」")


def mk_item(item_id: str, premise: str, hypothesis: str, label: str,
            probe_type: str) -> dict:
    return {"id": item_id, "premise": premise, "hypothesis": hypothesis,
            "label": label, "probe_type": probe_type}


def build_paws() -> list[dict]:
    """PAWS-X zh: 释义对(label=1)100 + 非释义对(label=0)100, T2重铸."""
    import pandas as pd

    pools: dict[int, list[tuple[str, str, str]]] = {0: [], 1: []}
    for fname, tag in [("pawsx_validation.parquet", "val"), ("pawsx_test.parquet", "test")]:
        df = pd.read_parquet(PUB / fname)
        for _, row in df.iterrows():
            s1, s2 = str(row["sentence1"]).strip(), str(row["sentence2"]).strip()
            if cjk_count(s1) < 8 or cjk_count(s2) < 8 or not s1 or not s2:
                continue
            pools[int(row["label"])].append((tag, str(row["id"]), s1, s2))
    rng = random.Random("p0probe:paws_shortcut")
    items: list[dict] = []
    for raw_label, n, label in [(1, 100, "consistent"), (0, 100, "inconsistent")]:
        chosen = rng.sample(pools[raw_label], n)
        for tag, raw_id, s1, s2 in chosen:
            p, h = t2_cast(s1, s2)
            items.append(mk_item(f"paws-{tag}-{raw_id}", p, h, label, "paws_shortcut"))
    return items


def build_feverous() -> list[dict]:
    """FEVEROUS: 表格证据对(证据含≥3行=表格态), SUPPORTS100 + REFUTES100."""
    pools: dict[int, list[tuple[int, str, str]]] = {0: [], 1: []}
    with open(PUB / "feverous_train.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            claim, ev = str(d["claim"]).strip(), str(d["evidence"]).strip()
            if d["label"] not in (0, 1) or not claim or not ev:
                continue
            if ev.count("\n") < 2:
                continue
            pools[int(d["label"])].append((int(d["id"]), claim, ev))
    rng = random.Random("p0probe:feverous_table")
    items: list[dict] = []
    for raw_label, n, label in [(0, 100, "consistent"), (1, 100, "inconsistent")]:
        chosen = rng.sample(pools[raw_label], n)
        for raw_id, claim, ev in chosen:
            items.append(mk_item(
                f"feverous-{raw_id}",
                f"文档某节记载：「{claim}」",
                f"证据表格显示：「{ev[:100]}」",
                label, "feverous_table"))
    return items


def build_ocnli() -> list[dict]:
    """OCNLI: 仅contradiction, 两侧各15-60字, 200条全部inconsistent(漏报探针)."""
    pool: list[tuple[int, str, str]] = []
    with open(PUB / "ocnli_3way.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            if d["label"] != "contradiction":
                continue
            s1, s2 = str(d["sentence1"]).strip(), str(d["sentence2"]).strip()
            if not (15 <= len(s1) <= 60 and 15 <= len(s2) <= 60):
                continue
            pool.append((int(d["id"]), s1, s2))
    rng = random.Random("p0probe:ocnli_contradiction")
    items: list[dict] = []
    for raw_id, s1, s2 in rng.sample(pool, 200):
        p, h = t2_cast(s1, s2)
        items.append(mk_item(f"ocnli-{raw_id}", p, h, "inconsistent",
                             "ocnli_contradiction"))
    return items


def write_probe(path: Path, probe_type: str, purpose: str, items: list[dict],
                source: dict, template: str, force: bool) -> bool:
    if path.exists() and not force:
        print(f"  跳过(已冻结): {path.name}  (--force可强制重建)")
        return False
    labels: dict[str, int] = {}
    for it in items:
        labels[it["label"]] = labels.get(it["label"], 0) + 1
    doc = {
        "meta": {
            "probe_type": probe_type,
            "purpose": purpose,
            "source": source,
            "template": template,
            "item_schema": ITEM_KEYS,
            "positive_class": "inconsistent",
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "builder": "tools/build_probes.py",
            "git_sha": git_sha(),
            "frozen": True,
            "freeze_declaration": FREEZE_DECLARATION,
            "n_items": len(items),
            "label_dist": dict(sorted(labels.items())),
        },
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"  写入: {path.name}  n={len(items)}  {dict(sorted(labels.items()))}")
    return True


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="构建P0冻结探针集")
    parser.add_argument("--force", action="store_true",
                        help="强制重建(冻结资产显式变更, 须同步MANIFEST+快照测试)")
    args = parser.parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"探针目录: {OUT_DIR}")

    write_probe(
        OUT_DIR / "paws_shortcut_probe.json", "paws_shortcut",
        "词面重叠捷径探针: 释义对(高词重叠, gold=consistent)被判inconsistent的比例"
        "=误报率, 即'词重叠⇒误报'捷径分(v5全报警病灶的量化)",
        build_paws(),
        source={
            "dataset": "PAWS-X zh (paraphrase adversaries from word scrambling)",
            "files": ["data/gjb_438c/public_nli/pawsx_validation.parquet",
                      "data/gjb_438c/public_nli/pawsx_test.parquet"],
            "raw_label_map": {"1=paraphrase": "consistent", "0=non-paraphrase": "inconsistent"},
            "filter": "两侧各≥8个CJK字符(中文实质内容)",
            "selection": "释义对100 + 非释义对100, random.Random('p0probe:paws_shortcut').sample",
        },
        template="T2规定式: premise=文档某章节规定：「S1」/ hypothesis=文档另一章节规定：「S2」",
        force=args.force,
    )
    write_probe(
        OUT_DIR / "feverous_table_probe.json", "feverous_table",
        "表格蕴含探针: 声明(claim)与结构化表格证据的核对能力"
        "(SUPPORTS→consistent, REFUTES→inconsistent)",
        build_feverous(),
        source={
            "dataset": "FEVEROUS (fact verification against tables+text)",
            "files": ["data/gjb_438c/public_nli/feverous_train.jsonl"],
            "raw_label_map": {"0=SUPPORTS": "consistent", "1=REFUTES": "inconsistent",
                              "2=NEI": "弃用"},
            "filter": "表格证据启发式: evidence含≥3行(≥2个换行); NEI弃用",
            "selection": "SUPPORTS100 + REFUTES100, "
                         "random.Random('p0probe:feverous_table').sample",
            "truncation": "hypothesis取evidence.strip()前100字符",
        },
        template="premise=文档某节记载：「claim」/ hypothesis=证据表格显示：「evidence前100字」",
        force=args.force,
    )
    write_probe(
        OUT_DIR / "ocnli_contradiction_probe.json", "ocnli_contradiction",
        "矛盾漏报探针: 高词面相似的矛盾对(gold全为inconsistent)被判consistent的比例"
        "=漏报率, 即'词相似⇒放行'捷径分(D族TERM-01/02同构)",
        build_ocnli(),
        source={
            "dataset": "OCNLI (Original Chinese NLI)",
            "files": ["data/gjb_438c/public_nli/ocnli_3way.jsonl"],
            "raw_label_map": {"contradiction": "inconsistent"},
            "filter": "仅contradiction类, 两侧各15-60字",
            "selection": "200条, random.Random('p0probe:ocnli_contradiction').sample",
        },
        template="T2规定式: premise=文档某章节规定：「S1」/ hypothesis=文档另一章节规定：「S2」",
        force=args.force,
    )
    print("提示: 首次构建后建议运行 python tools/build_data_manifest.py 将探针纳入MANIFEST保护")


if __name__ == "__main__":
    main()
