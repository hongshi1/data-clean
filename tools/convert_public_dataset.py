r"""公开数据集→URE格式转换器(外部效度检验入口).

格式规范: docs/srs_project/20_dataset_spec.md §三
映射实现: WTQ(WikiTableQuestions)——真实用户问题→表检索.

用法:
  # 离线夹具(3表6问, 验证转换管线, 无网络依赖)
  python tools/convert_public_dataset.py --source wtq-fixture --out wtq_fixture_ure.json
  # 真实WTQ(需pip install datasets + HuggingFace可达)
  python tools/convert_public_dataset.py --source wtq --out wtq_ure.json

映射规则(代码即规范, 见spec §3.2):
  表→corpus: chunk_id=wtq_{tid}, title=page_title, units=行"header=value"序列化
  问→queries: expected=[wtq_{tid}](WTQ每问绑定gold表), scene=table_deep,
              split=eval, fold=查询hash mod 4(无文档级分组, protocol注明)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

ROW_TEXT_LEN = 150
N_FOLDS = 4

# ── WTQ离线夹具(3表6问, 结构对齐HF wikitablequestions字段) ──

WTQ_FIXTURE = {
    "tables": [
        {"name": "1-10015132-11", "page_title": "List of Olympic medalists in athletics (men)",
         "header": ["Games", "Gold", "Silver", "Bronze"],
         "rows": [
             ["1896 Athens", "Thomas Burke", "Fritz Hofmann", "Eduard Taublitz"],
             ["1900 Paris", "Alvin Kraenzlein", "Walter Tewksbury", "Stan Rowley"],
             ["1904 St. Louis", "Archie Hahn", "Nate Cartmell", "William Hogenson"]]},
        {"name": "2-10015132-8", "page_title": "List of world records in athletics",
         "header": ["Event", "Record", "Athlete", "Date"],
         "rows": [
             ["100 m", "9.58", "Usain Bolt", "16 August 2009"],
             ["200 m", "19.19", "Usain Bolt", "20 August 2009"],
             ["Marathon", "2:01:39", "Eliud Kipchoge", "16 September 2018"]]},
        {"name": "3-11589235-2", "page_title": "Piano Sonata No. 14 (Beethoven)",
         "header": ["Movement", "Tempo", "Key", "Form"],
         "rows": [
             ["I", "Adagio sostenuto", "C-sharp minor", "Sonata form"],
             ["II", "Allegretto", "D-flat major", "Minuet and trio"],
             ["III", "Presto agitato", "C-sharp minor", "Sonata rondo"]]},
    ],
    "questions": [
        {"question": "who won the gold medal in 100m at the 1896 Games?",
         "table": "1-10015132-11", "answers": ["Thomas Burke"]},
        {"question": "which athlete took bronze in the 1904 100 m?",
         "question_note": "real WTQ questions ask row content, not titles",
         "table": "1-10015132-11", "answers": ["William Hogenson"]},
        {"question": "how fast was the world record in the 200m when it was set on 20 August 2009?",
         "table": "2-10015132-8", "answers": ["19.19"]},
        {"question": "who held the marathon world record before September 2018 ended?",
         "table": "2-10015132-8", "answers": ["Eliud Kipchoge"]},
        {"question": "what tempo marking does the second movement of the Moonlight Sonata use?",
         "table": "3-11589235-2", "answers": ["Allegretto"]},
        {"question": "in what key is the final movement of Beethoven's Piano Sonata No. 14?",
         "table": "3-11589235-2", "answers": ["C-sharp minor"]},
    ],
}


def fold_of_query(query: str) -> int:
    """无文档级分组的公开数据集: 查询hash分折(spec §3.3第4步)."""
    return int(hashlib.md5(query.encode("utf-8")).hexdigest(), 16) % N_FOLDS


def wtq_table_to_corpus(t: dict) -> dict:
    """WTQ表→URE corpus entry(与GJB表同序列化: 'header=value')."""
    headers = t.get("header") or t.get("headers") or []
    units = []
    for r in t.get("rows", [])[:50]:
        if len(r) == len(headers) and headers:
            units.append(" ".join(f"{h}={v}" for h, v in zip(headers, r))[:ROW_TEXT_LEN])
        else:
            units.append(" ".join(r)[:ROW_TEXT_LEN])
    title = str(t.get("page_title") or t.get("pgTitle") or "")[:100]
    return {
        "doc": f"wtq_{t['name']}", "chunk_id": f"wtq_{t['name']}",
        "type": "table", "scene": "table", "title": title,
        "units": units, "n_units": len(units), "section": "",
    }


def wtq_question_to_query(q: dict) -> dict:
    """WTQ问题→URE query(gold表直接给定期望)."""
    return {
        "query": q["question"], "expected": [f"wtq_{q['table']}"],
        "scene": "table_deep", "source": "wtq",
        "split": "eval", "fold": fold_of_query(q["question"]),
    }


def load_wtq_fixture() -> tuple[list[dict], list[dict]]:
    corpus = [wtq_table_to_corpus(t) for t in WTQ_FIXTURE["tables"]]
    queries = [wtq_question_to_query(q)
               for q in WTQ_FIXTURE["questions"] if "question" in q]
    return corpus, queries


def fetaqa_entry_to_corpus(ex: dict) -> dict:
    """FeTaQA样例→corpus entry(table_array第0行=表头, 行序列化同GJB/WTQ)."""
    arr = ex.get("table_array") or []
    if not arr:
        return {}
    headers = arr[0]
    units = []
    for r in arr[1:]:
        if len(r) == len(headers) and headers:
            units.append(" ".join(f"{h}={v}" for h, v in zip(headers, r))[:ROW_TEXT_LEN])
        else:
            units.append(" ".join(r)[:ROW_TEXT_LEN])
    title = str(ex.get("table_page_title") or "")[:100]
    return {
        "doc": f"fetaqa_{ex['feta_id']}", "chunk_id": f"fetaqa_{ex['feta_id']}",
        "type": "table", "scene": "table", "title": title,
        "units": units, "n_units": len(units), "section": "",
    }


def fetaqa_entry_to_query(ex: dict) -> dict:
    """FeTaQA问题→query(带行级gold: gold_rows=units下标, 供单元精度评测)."""
    arr = ex.get("table_array") or []
    gold_rows = sorted({r - 1 for r, _c in
                        (tuple(hc) for hc in ex.get("highlighted_cell_ids", []))
                        if 0 < r < len(arr)})
    return {
        "query": ex["question"], "expected": [f"fetaqa_{ex['feta_id']}"],
        "scene": "table_deep", "source": "fetaqa",
        "split": "eval", "fold": fold_of_query(ex["question"]),
        "gold_rows": gold_rows,
    }


def load_fetaqa() -> tuple[list[dict], list[dict]]:
    """真实FeTaQA(DongfuJiang/FeTaQA镜像, test=2003条).

    行级gold(highlighted_cell_ids)使单元级命中精度可评——
    检索到gold表后, top单元是否命中gold行.
    """
    import os

    if not os.environ.get("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from datasets import load_dataset  # noqa: PLC0415

    ds = load_dataset("DongfuJiang/FeTaQA", split="test")
    corpus_map: dict[str, dict] = {}
    queries = []
    for ex in ds:
        c = fetaqa_entry_to_corpus(ex)
        if not c:
            continue
        corpus_map[c["chunk_id"]] = c
        queries.append(fetaqa_entry_to_query(ex))
    return list(corpus_map.values()), queries


def load_wtq_hf() -> tuple[list[dict], list[dict]]:
    """真实WTQ(lighteval parquet版, 经hf-mirror镜像).

    调研结论: 原stanfordnlp/wikitablequestions为script型repo,
    datasets 5.x已不支持; lighteval/wikitablequestions为parquet,
    test split=18,486条(≈全量合并). 无page_title字段(title置空或
    用table_md首行——本实现置空, 保持纯字段映射).
    """
    import os

    if not os.environ.get("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from datasets import load_dataset  # noqa: PLC0415

    ds = load_dataset("lighteval/wikitablequestions", split="test")
    tables: dict[str, dict] = {}
    queries = []
    for ex in ds:
        t = ex["table"]
        name = t.get("name") or str(ex.get("id", len(tables)))
        if name not in tables:
            tables[name] = {"name": name, "header": t.get("header"),
                            "rows": t.get("rows"),
                            "page_title": t.get("page_title", "")}
        queries.append({"question": ex["question"], "table": name,
                        "answers": ex.get("answers", [])})
    corpus = [wtq_table_to_corpus(t) for t in tables.values()]
    queries = [wtq_question_to_query(q) for q in queries]
    return corpus, queries


def validate(corpus: list[dict], queries: list[dict]) -> list[str]:
    problems = []
    ids = [c["chunk_id"] for c in corpus]
    if len(ids) != len(set(ids)):
        problems.append("chunk_id不唯一")
    idset = set(ids)
    for q in queries:
        if not all(t in idset for t in q["expected"]):
            problems.append(f"悬空expected: {q['expected']}")
        if q["fold"] not in range(N_FOLDS):
            problems.append(f"fold越界: {q['fold']}")
    return problems


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=("wtq", "wtq-fixture", "fetaqa"),
                    required=True)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    if args.source == "wtq-fixture":
        corpus, queries = load_wtq_fixture()
        name, note = "WTQ-fixture-URE", "离线夹具(转换管线验证用)"
    elif args.source == "fetaqa":
        try:
            corpus, queries = load_fetaqa()
            name, note = "FeTaQA-URE", "真实FeTaQA test split(带行级gold)"
        except (ImportError, OSError, ValueError) as e:
            print(f"FeTaQA加载失败({str(e)[:100]})")
            sys.exit(1)
    else:
        try:
            corpus, queries = load_wtq_hf()
            name, note = "WTQ-URE", "真实WTQ test split"
        except (ImportError, OSError, ValueError) as e:
            print(f"WTQ加载失败({str(e)[:100]}); 用--source wtq-fixture离线验证")
            sys.exit(1)

    problems = validate(corpus, queries)
    if problems:
        print(f"校验失败: {problems[:5]}")
        sys.exit(1)
    dataset = {
        "meta": {
            "name": name, "version": "1.0", "language": "en",
            "task": "unit-level retrieval over structured documents",
            "created": "2026-09-30", "description": note,
            "stats": {"n_corpus": len(corpus), "n_units": sum(c["n_units"] for c in corpus),
                      "n_queries_eval": len(queries),
                      "n_queries_train": 0},
        },
        "corpus": corpus, "queries": queries,
        "protocol": {
            "n_folds": N_FOLDS, "fold_rule": "查询hash(md5) mod 4(无文档级分组)",
            "candidates": "全部corpus(表检索, 无fold隔离的公开源)",
            "query_prefix": "为这个句子生成表示以用于检索相关文章：",
            "metrics": ["R@1", "R@5", "MRR@10"],
            "note": "英文源; bge-large-zh对英文非最优(见spec §3.1英文注意)",
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dataset, ensure_ascii=False, indent=1), encoding="utf-8")
    st = dataset["meta"]["stats"]
    print(f"{name} 转换完成 → {out}")
    print(f"  corpus: {st['n_corpus']}表/{st['n_units']}单元, "
          f"queries: {st['n_queries_eval']}")
    print(f"  fold分布: {dict(Counter(q['fold'] for q in queries))}")


if __name__ == "__main__":
    main()
