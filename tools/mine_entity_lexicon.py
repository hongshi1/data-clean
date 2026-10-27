r"""K1领域实体词典挖掘: GLM从训练语料抽取实体→冻结资产.

语料(非评测集): canonical train + synth源约束, 分层抽样600条.
产出: knowledge/entity_lexicon.json (param/interface/function/unit 实体+别名)
协议: 4线程, 缓存, 增量保存, 断点续跑.
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

OUT = BASE / "knowledge/entity_lexicon.json"
SEED = 42
N_SAMPLE = 600
BATCH = 15

SYSTEM = "你是GJB军事软件SRS的领域术语专家. 只输出JSON."
PROMPT = """从以下SRS需求文本中抽取领域实体, 用于构建一致性检测的领域词典.

抽取规则:
- param: 参数/性能/资源指标实体(如"响应时间""可用空间"), 给出同义别名(如"响应延迟")
- interface: 接口/服务/系统实体
- function: 功能/条目实体(简短功能名, ≤10字)
- unit: 计量单位(附同义单位, 如G/GB/1024MB)
只抽实体词本身, 不抽完整句子; 同一实体只出现一次.

文本列表:
{texts}

输出JSON:
{{"entities": [{{"canonical": "响应时间", "aliases": ["响应延迟"], "type": "param"}}]}}"""


def parse_entities(text: str) -> list[dict]:
    m = re.search(r"\{.*\}", str(text), re.S)
    if not m:
        return []
    try:
        d = json.loads(m.group())
        return [e for e in d.get("entities", []) if isinstance(e, dict) and e.get("canonical")]
    except json.JSONDecodeError:
        return []


def main() -> None:
    from algorithms.common.llm_client import llm_chat

    # 语料(训练侧, 不含评测集)
    train = [json.loads(line) for line in open(BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl", encoding="utf-8")]
    texts = set()
    for x in train:
        ph = x.get("pair", x)
        texts.add(str(ph.get("premise", "")))
        texts.add(str(ph.get("hypothesis", "")))
    synth = json.loads((BASE / "data/gjb_438c/synth_s1_pairs.json").read_text(encoding="utf-8"))["pairs"]
    for p in synth:
        texts.add(str(p.get("source_constraint", "")))
    texts.discard("")
    rng = random.Random(SEED)
    pool = sorted(texts)
    rng.shuffle(pool)
    sample = pool[:N_SAMPLE]
    batches = [sample[i:i + BATCH] for i in range(0, len(sample), BATCH)]
    print(f"挖掘: {len(sample)}条文本 → {len(batches)}批")

    done_batches = 0
    raw_entities: list[dict] = []
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        if existing.get("meta", {}).get("n_sample") == N_SAMPLE:
            raw_entities = existing.get("raw_entities", [])
            done_batches = existing.get("done_batches", 0)
            print(f"续跑: 已完成{done_batches}批")
    todo = list(enumerate(batches))[done_batches:]

    if todo:

        def work(item):
            bi, batch = item
            body = "\n".join(f"{k + 1}. {t}" for k, t in enumerate(batch))
            try:
                out = llm_chat(PROMPT.format(texts=body), system=SYSTEM, prefer="glm")
                return bi, parse_entities(out)
            except Exception as e:  # noqa: BLE001
                return bi, {"error": f"{type(e).__name__}: {e}"}

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=4) as ex:
            for i, (bi, ents) in enumerate(ex.map(work, todo)):
                if isinstance(ents, list):
                    raw_entities.extend(ents)
                done_batches = bi + 1
                if (i + 1) % 8 == 0:
                    _save(done_batches, raw_entities)
                    print(f"  {done_batches}/{len(batches)}批, 实体{len(raw_entities)}个 ({time.time() - t0:.0f}s)", flush=True)

    # 合并: canonical去重, 别名并入, 排除过短/无意义
    by_canon: dict[str, dict] = {}
    for e in raw_entities:
        canon = str(e.get("canonical", "")).strip()
        typ = str(e.get("type", "param"))
        aliases = [str(a).strip() for a in e.get("aliases", []) if a and str(a).strip() != canon]
        if not canon or len(canon) < 2 or len(canon) > 20:
            continue
        if canon not in by_canon:
            by_canon[canon] = {"canonical": canon, "type": typ, "aliases": set()}
        by_canon[canon]["aliases"].update(aliases)

    # srs_kb种子并入
    kb = json.loads((BASE / "knowledge/srs_kb.json").read_text(encoding="utf-8"))
    for key, entry in kb.get("param_dictionary", {}).items():
        canon = str(entry.get("canonical_cn", key))
        if canon not in by_canon:
            by_canon[canon] = {"canonical": canon, "type": "param", "aliases": set()}
        for syn in entry.get("synonyms_en", []) + entry.get("synonyms_cn", []):
            s = str(syn).strip()
            if 2 <= len(s) <= 20 and s != canon:
                by_canon[canon]["aliases"].add(s)

    out_entities = []
    for canon, e in sorted(by_canon.items(), key=lambda kv: (kv[1]["type"], kv[0])):
        out_entities.append({"canonical": canon, "type": e["type"],
                             "aliases": sorted(e["aliases"])})
    n_alias = sum(len(e["aliases"]) for e in out_entities)
    final = {"meta": {"version": "entity_lexicon_v1", "date": "2026-10-14",
                      "n_sample": N_SAMPLE, "n_batches": len(batches), "done_batches": done_batches,
                      "source": "canonical train+synth源约束(分层抽样600), GLM抽取+srs_kb种子",
                      "stats": {"entities": len(out_entities), "aliases": n_alias}},
             "entities": out_entities,
             "raw_entities": raw_entities}
    OUT.write_text(json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    types = Counter(e["type"] for e in out_entities)
    print(f"\n词典冻结: {len(out_entities)}实体({dict(types)}), {n_alias}别名 → {OUT}")


def _save(done: int, raw: list) -> None:
    OUT.write_text(json.dumps({"meta": {"n_sample": N_SAMPLE}, "done_batches": done,
                               "raw_entities": raw}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
