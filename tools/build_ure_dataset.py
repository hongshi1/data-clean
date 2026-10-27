r"""构建GJB-URE-v1: 把分散的评测资产固化为标准单元检索数据集.

格式规范: docs/srs_project/20_dataset_spec.md
输出: data/gjb_438c/data_assets/evalsets/gjb_ure_v1.json

校验(构建期强制):
  - chunk_id唯一; expected引用完整; fold∈[0,4)
  - 每fold每scene可评测(eval查询≥1且corpus≥5)
  - 数据集卡stats输出

用法: python tools/build_ure_dataset.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
EVALSET = BASE / "data/gjb_438c/data_assets/evalset_v3.json"
DOC_QUERIES = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
PARAM_V2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"
DEEP_EVAL = BASE / "data/gjb_438c/data_assets/deep_row_queries.json"
DEEP_TRAIN = BASE / "data/gjb_438c/data_assets/deep_row_queries_train.json"
DEEP_V2 = BASE / "data/gjb_438c/data_assets/evalsets/deep_row_queries_v2.json"
OUT = BASE / "data/gjb_438c/data_assets/evalsets/gjb_ure_v2.json"

SCENES = {"image", "table_caption", "table_deep", "table_deep_v2"}


def build_corpus() -> list[dict]:
    """corpus: 全部图+表chunk(检索候选完整性), 单元来自既有提取器.

    无任何单元来源的图(units空)也纳入——它们是合法检索目标,
    单元通道缺失时由单向量通道兜底(与线上行为一致).
    """
    from algorithms.unit_attention import (
        image_units_with_feats,
        table_units_with_feats,
    )
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    img_units = {cid: ts for cid, (ts, _)
                 in image_units_with_feats(chunks).items()}
    tab_units = {cid: ts for cid, (ts, _)
                 in table_units_with_feats(chunks).items()}
    corpus = []
    for c in chunks:
        cid = c.get("chunk_id", "")
        if c.get("type") == "image":
            texts = img_units.get(cid, [])
        elif c.get("type") == "table":
            texts = tab_units.get(cid, [])
        else:
            continue
        title = texts[0] if texts else ""
        units = list(dict.fromkeys(texts[1:]))  # 审计修复S6: 单元精确去重(k=1 MaxSim行为不变)
        corpus.append({
            "doc": c.get("doc", ""), "chunk_id": cid,
            "type": c.get("type"),
            "scene": "diagram" if c.get("type") == "image" else "table",
            "title": title, "units": units,
            "n_units": len(units),
            "section": c.get("section", ""),
            "fold": fold_of_doc(cid[:2]),
            **({"page": c.get("page")} if c.get("page") is not None else {})})
    return corpus


def build_queries() -> list[dict]:
    """queries: eval(image 1007 + table_deep 118) + train(去污染).

    审计修复S2: train池排除与eval的(query, expected)对完全重复项
    (原deep_train 585条逐字包含118条eval).
    image查询保留evalset_v3的fold字段(工具约定), 其余按fold_of_doc.
    """
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    cid2type = {c["chunk_id"]: c.get("type") for c in chunks}
    queries = []
    eval_pairs: set[tuple[str, tuple[str, ...]]] = set()
    for q in json.loads(EVALSET.read_text(encoding="utf-8")):
        queries.append({
            "query": q["query"], "expected": q["expected"]["chunk_ids"],
            "scene": "image", "source": q.get("source", "evalset_v3"),
            "split": "eval", "fold": q["fold"]})
        eval_pairs.add((q["query"], tuple(q["expected"]["chunk_ids"])))
    for o in json.loads(DEEP_EVAL.read_text(encoding="utf-8")):
        queries.append({
            "query": o["query"], "expected": [o["cid"]],
            "scene": "table_deep", "source": "deep_row_llm",
            "split": "eval", "fold": fold_of_doc(o["doc"])})
        eval_pairs.add((o["query"], (o["cid"],)))
    # train池(排除eval重复对)
    n_dropped = 0
    for path, src in ((DOC_QUERIES, "docT5"), (PARAM_V2, "docT5_v2")):
        for cid, rec in json.loads(path.read_text(encoding="utf-8")).items():
            if cid2type.get(cid) != "table":
                continue
            qs = rec if isinstance(rec, list) else rec.get("queries", [])
            for q in qs[:1]:
                if (q, (cid,)) in eval_pairs:
                    n_dropped += 1
                    continue
                queries.append({
                    "query": q, "expected": [cid], "scene": "table_caption",
                    "source": src, "split": "train", "fold": fold_of_doc(cid[:2])})
    for o in json.loads(DEEP_TRAIN.read_text(encoding="utf-8")):
        if (o["query"], (o["cid"],)) in eval_pairs:
            n_dropped += 1
            continue
        queries.append({
            "query": o["query"], "expected": [o["cid"]],
            "scene": "table_deep", "source": "deep_row_llm",
            "split": "train", "fold": fold_of_doc(o["doc"])})
    # 深行v2: 反拷贝约束生成(平均overlap 0.130 vs v1 0.525)
    if DEEP_V2.exists():
        for o in json.loads(DEEP_V2.read_text(encoding="utf-8")):
            queries.append({
                "query": o["query"], "expected": [o["cid"]],
                "scene": "table_deep_v2", "source": "deep_row_llm_v2",
                "split": "eval", "fold": fold_of_doc(o["doc"])})
    print(f"  train去污染: 排除与eval重复对{n_dropped}条")
    # v2: 全部eval查询标注overlap(泄漏协变量入数据集)
    units_by_cid = {c["chunk_id"]: [c["title"]] + c["units"]
                    for c in build_corpus()}
    for q in queries:
        if q["split"] == "eval":
            q["overlap"] = query_gold_overlap(
                q["query"], q["expected"], units_by_cid)
    return queries


def _bigrams(text: str) -> set:
    cs = [ch for ch in text or "" if "\u4e00" <= ch <= "\u9fff"]
    return {cs[j] + cs[j + 1] for j in range(len(cs) - 1)} if len(cs) >= 2 else set()


def query_gold_overlap(query: str, expected: list[str],
                       units_by_cid: dict[str, list[str]]) -> float:
    """泄漏协变量: 查询与gold并集文本的CJK二元组重叠率(审计§六修正1).

    v1数据集查询从语料生成→高重叠(66-84%)使词面方法被高估;
    overlap入数据集供分层报告.
    """
    qb = _bigrams(query)
    if not qb:
        return 0.0
    gb: set = set()
    for cid in expected:
        for u in units_by_cid.get(cid, []):
            gb |= _bigrams(u)
    return round(len(qb & gb) / len(qb), 3)


def fold_of_doc(doc2: str) -> int:
    """fold约定: (doc序号-1) mod 4.

    与全部评测工具(eval_va_colpali/eval_table_late/evalset_v3构建)的
    FOLD_MAP = enumerate(range(1,17)) % 4 一致——doc"01"→fold0.
    审计修复: 原实现int(doc)%4导致doc"01"→fold1, 与image查询的
    fold字段(继承evalset_v3)错位, 按协议跑98.8%查询gold不在候选池.
    """
    return (int(doc2) - 1) % 4


def validate(corpus: list[dict], queries: list[dict]) -> list[str]:
    """构建期硬校验, 返回问题列表(空=通过)."""
    problems = []
    ids = [c["chunk_id"] for c in corpus]
    if len(ids) != len(set(ids)):
        problems.append("chunk_id不唯一")
    idset = set(ids)
    for q in queries:
        if not q["expected"]:
            problems.append(f"空expected: {q['query'][:20]}")
        for t in q["expected"]:
            if t not in idset:
                problems.append(f"悬空expected: {t[-12:]}")
        if q["fold"] not in (0, 1, 2, 3):
            problems.append(f"fold越界: {q['fold']}")
        if q["scene"] not in SCENES:
            problems.append(f"非法scene: {q['scene']}")
    # 每fold每scene可评测性
    by = defaultdict(Counter)
    for q in queries:
        if q["split"] == "eval":
            by[(q["fold"], q["scene"])]["eval"] += 1
    ctype = {"image": "image", "table_caption": "table", "table_deep": "table",
             "table_deep_v2": "table"}
    corpus_by_fold = defaultdict(Counter)
    for c in corpus:
        corpus_by_fold[c["fold"]][c["type"]] += 1
    for (fold, scene), cnt in sorted(by.items()):
        t = ctype[scene]
        if cnt["eval"] < 1:
            problems.append(f"fold{fold}/{scene}: eval查询不足")
        if corpus_by_fold[fold][t] < 5:
            problems.append(f"fold{fold}/{scene}: 候选<5")
    # fold约定一致性(审计修复S1的硬护栏): eval查询的expected必须
    # 绝大多数位于查询fold内(允许少数已知噪声, 大规模错位=约定bug)
    fold_of_cid = {c["chunk_id"]: c["fold"] for c in corpus}
    n_match = n_miss = 0
    miss_examples: list[str] = []
    for q in queries:
        if q["split"] != "eval":
            continue
        folds = {fold_of_cid[t] for t in q["expected"] if t in fold_of_cid}
        if q["fold"] in folds:
            n_match += 1
        else:
            n_miss += 1
            if len(miss_examples) < 3:
                miss_examples.append(f"{q['scene']}: {q['query'][:24]}…")
    miss_rate = n_miss / max(n_match + n_miss, 1)
    if miss_rate > 0.05:
        problems.append(
            f"fold约定错位: {n_miss}/{n_match + n_miss} eval查询gold在"
            f"查询fold外(miss率{miss_rate:.1%}, 示例: {miss_examples})")
    print(f"  fold一致性: {n_match}/{n_match + n_miss} eval查询gold在本fold"
          f"({miss_rate:.1%}为已知噪声: 死块/跨文档legacy锚定)")
    return problems


def stats_card(corpus: list[dict], queries: list[dict]) -> dict:
    n_units = sum(c["n_units"] for c in corpus)
    eval_q = [q for q in queries if q["split"] == "eval"]
    return {
        "n_corpus": len(corpus),
        "n_images": sum(1 for c in corpus if c["type"] == "image"),
        "n_tables": sum(1 for c in corpus if c["type"] == "table"),
        "n_units": n_units,
        "n_queries_eval": len(eval_q),
        "n_queries_train": len(queries) - len(eval_q),
        "eval_by_scene": dict(Counter(q["scene"] for q in eval_q)),
        "n_docs": len({c["doc"] for c in corpus}),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    corpus = build_corpus()
    queries = build_queries()
    problems = validate(corpus, queries)
    if problems:
        print(f"校验失败({len(problems)}):")
        for p in problems[:10]:
            print(f"  - {p}")
        sys.exit(1)
    dataset = {
        "meta": {
            "name": "GJB-URE-v2", "version": "2.0", "language": "zh",
            "task": "unit-level retrieval over structured documents",
            "created": "2026-09-30",
            "description": ("16份GJB 438C SRS; corpus=全部381图+1207表"
                            "(单元去重); 四场景查询(image/table_caption/"
                            "table_deep_v1含泄漏基线/table_deep_v2反拷贝), "
                            "eval查询带overlap泄漏协变量(分层报告依据), "
                            "4-fold文档级隔离; train池已去eval污染"),
            "stats": stats_card(corpus, queries),
        },
        "corpus": corpus,
        "queries": queries,
        "protocol": {
            "n_folds": 4, "fold_rule": "doc序号 mod 4 (文档级隔离)",
            "candidates": "测试fold内全部同type chunk",
            "query_prefix": "为这个句子生成表示以用于检索相关文章：",
            "metrics": ["R@1", "R@5", "MRR@10"],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    st = dataset["meta"]["stats"]
    print(f"GJB-URE-v2 构建完成 → {OUT}")
    print(f"  corpus: {st['n_corpus']} ({st['n_images']}图 + "
          f"{st['n_tables']}表, {st['n_units']}单元)")
    print(f"  queries: eval {st['n_queries_eval']} "
          f"{st['eval_by_scene']} + train {st['n_queries_train']}")
    print("  校验: 通过(chunk_id唯一/expected引用完整/4fold×3scene可评测)")


if __name__ == "__main__":
    main()
