"""Lexicon transfer demo: one engine, two scene configs (换配置不换代码).

用法:
    python tools/demo_lexicon_transfer.py

内容:
1. 行为等价(04号): srs_scene1配置跑scene1冻结QA(91行), 与重构前硬编码
   基线逐实体digest对比(tests/fixtures/scene1_l0_legacy_digests_v1.json
   + runs/demo_lexicon_legacy_baseline_*/result.json).
2. 迁移演示(06号): doc06_scene配置跑crossdoc06冻结评测集(30行)——
   同一entity_detector引擎, 仅换config/ner_lexicons/doc06_scene.json.
3. 对比表: 两场景的实体数/类型分布/文档词典规模/TERM检测结果/样例.
4. 场景消融: 06号证据分别用两份lexicon抽取, 展示配置差异的可见效果
   (域词命中/jieba gazetteer整词/运行状态值域含集成阶段).
5. jieba链路: configure_jieba自动add_word后的确定性分词(HMM=False).

产出走runs协议(open_run: config+git_sha+result, 不覆盖写).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_structure import decompose_answer
from algorithms.consistency.entity_detector import (
    build_document_lexicon,
    detect_term_conflicts,
    extract_entities,
)
from algorithms.consistency.evidence_statements import (
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.ner_lexicon import (
    LEXICON_DIR,
    NerLexicon,
    load_lexicon,
    tokenize,
)
from algorithms.consistency.eval_lib import load_frozen_qa
from tools.build_answer_mutation_candidates import request_from_dict
from tools.run_utils import open_run

CROSSDOC06_PATH = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"
LEGACY_FIXTURE = BASE / "tests/fixtures/scene1_l0_legacy_digests_v1.json"
LEGACY_RUN_GLOB = "demo_lexicon_legacy_baseline_*/result.json"

#: 每类实体/词典字段展示的样例数
SAMPLE_N = 5


def _digest(obj: Any) -> str:
    import hashlib

    canon = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def l0_row_record(row: dict[str, Any],
                  lexicon: NerLexicon | None = None) -> dict[str, Any]:
    """跑一遍L0(抽取+冻结+TERM检测)并返回可digest的记录.

    tests/test_ner_lexicon.py的91行digest锁定与legacy基线dump用同一
    记录结构(instance_id/n_statements/statement_entities/answer_entities/
    question_entities/document_lexicon/term_conflicts).
    """
    request = request_from_dict(row)
    statements = linearize_context(request.evidence)
    claims = decompose_answer(request.answer, request.question)
    stmt_entities = [
        {"sid": s.statement_id,
         "entities": [[e.surface, e.kind] for e in extract_entities(s.text)]}
        for s in statements
    ]
    answer_entities = [[e.surface, e.kind] for e in extract_entities(request.answer)]
    question_entities = [[e.surface, e.kind]
                         for e in extract_entities(request.question)]
    lex = build_document_lexicon(statements, lexicon)
    term_results = [
        {"claim_id": r.claim_id, "verdict": r.verdict,
         "check_item_candidates": list(r.check_item_candidates),
         "evidence_refs": list(r.evidence_refs), "rationale": r.rationale,
         "method": r.method, "confidence": r.confidence}
        for r in detect_term_conflicts(request, statements, claims, lexicon)
    ]
    return {
        "instance_id": row["instance_id"],
        "n_statements": len(statements),
        "statement_entities": stmt_entities,
        "answer_entities": answer_entities,
        "question_entities": question_entities,
        "document_lexicon": {
            "capability_names": list(lex.capability_names),
            "usecase_names": list(lex.usecase_names),
            "interface_ids": list(lex.interface_ids),
            "mode_values": list(lex.mode_values),
            "status_values": list(lex.status_values),
            "database_names": list(lex.database_names),
            "alias_pairs": [[p.surface, p.target] for p in lex.alias_pairs],
        },
        "term_conflicts": term_results,
    }


def load_crossdoc06_rows() -> list[dict[str, Any]]:
    """06号冻结评测集(与scene1同schema, 走同一request_from_dict入口)."""
    return [json.loads(line) for line
            in CROSSDOC06_PATH.read_text(encoding="utf-8").splitlines()]


def _statement_texts(rows: list[dict[str, Any]], limit: int = 40) -> list[str]:
    """jieba演示用的语句文本(每行前若干条, 避免全量分词耗时)."""
    texts: list[str] = []
    for row in rows[:limit]:
        request = request_from_dict(row)
        statements: list[EvidenceStatement] = linearize_context(request.evidence)
        texts.extend(s.text for s in statements[:8])
    return texts


def scene_stats(rows: list[dict[str, Any]], lexicon: NerLexicon) -> dict[str, Any]:
    """一个场景的全量L0统计(记录复用l0_row_record)."""
    records = [l0_row_record(row, lexicon) for row in rows]
    kind_counts: Counter[str] = Counter()
    answer_kind_counts: Counter[str] = Counter()
    surface_by_kind: dict[str, Counter[str]] = {}
    for record in records:
        for stmt in record["statement_entities"]:
            for surface, kind in stmt["entities"]:
                kind_counts[kind] += 1
                surface_by_kind.setdefault(kind, Counter())[surface] += 1
        for surface, kind in record["answer_entities"]:
            answer_kind_counts[kind] += 1
    interface_ids: set[str] = set()
    capability: set[str] = set()
    usecase: set[str] = set()
    mode_values: set[str] = set()
    status_values: set[str] = set()
    database_names: set[str] = set()
    alias_pairs: set[tuple[str, str]] = set()
    for record in records:
        lex = record["document_lexicon"]
        interface_ids.update(lex["interface_ids"])
        capability.update(lex["capability_names"])
        usecase.update(lex["usecase_names"])
        mode_values.update(lex["mode_values"])
        status_values.update(lex["status_values"])
        database_names.update(lex["database_names"])
        alias_pairs.update((s, t) for s, t in lex["alias_pairs"])
    method_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    for record in records:
        for result in record["term_conflicts"]:
            method_counts[result["method"]] += 1
            verdict_counts[result["verdict"]] += 1
    samples = {kind: [s for s, _ in counter.most_common(SAMPLE_N)]
               for kind, counter in surface_by_kind.items()}
    return {
        "scene": lexicon.scene,
        "n_rows": len(records),
        "n_statements_total": sum(r["n_statements"] for r in records),
        "statement_entity_total": sum(kind_counts.values()),
        "statement_entity_kinds": dict(sorted(kind_counts.items())),
        "answer_entity_total": sum(answer_kind_counts.values()),
        "answer_entity_kinds": dict(sorted(answer_kind_counts.items())),
        "entity_samples": samples,
        "document_lexicon": {
            "capability_names": len(capability),
            "usecase_names": len(usecase),
            "interface_ids": len(interface_ids),
            "mode_values": sorted(mode_values),
            "status_values": sorted(status_values),
            "database_names": sorted(database_names),
            "alias_pairs": len(alias_pairs),
            "capability_samples": sorted(capability)[:SAMPLE_N],
            "usecase_samples": sorted(usecase)[:SAMPLE_N],
            "interface_id_samples": sorted(interface_ids)[:SAMPLE_N],
            "alias_pair_samples": [list(p) for p in sorted(alias_pairs)[:SAMPLE_N]],
        },
        "term_conflicts": {
            "total": sum(method_counts.values()),
            "by_method": dict(sorted(method_counts.items())),
            "by_verdict": dict(sorted(verdict_counts.items())),
        },
        "_records": records,
    }


def check_legacy_equivalence(scene1_stats: dict[str, Any]) -> dict[str, Any]:
    """srs_scene1配置 vs 重构前硬编码: 逐实体digest对比."""
    fixture = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
    rows = load_frozen_qa()
    row_digests = [_digest(record) for record in scene1_stats["_records"]]
    mismatches = [
        rows[i]["instance_id"] for i, got in enumerate(row_digests)
        if got != fixture["row_digests"][rows[i]["instance_id"]]
    ]
    global_digest = _digest(row_digests)
    legacy_runs = sorted((BASE / "data/gjb_438c/runs").glob(LEGACY_RUN_GLOB))
    legacy_run = legacy_runs[-1] if legacy_runs else None
    return {
        "fixture": str(LEGACY_FIXTURE.relative_to(BASE)),
        "n_rows": len(rows),
        "n_digest_equal": len(rows) - len(mismatches),
        "mismatched_instance_ids": mismatches,
        "global_digest": global_digest,
        "legacy_global_digest": fixture["global_digest"],
        "all_equal": global_digest == fixture["global_digest"]
        and not mismatches,
        "legacy_run_dump": str(legacy_run.relative_to(BASE)) if legacy_run else "",
        "aggregate_equivalence": {
            "statement_entities": (
                scene1_stats["statement_entity_total"],
                _legacy_aggregate(legacy_run, "n_entities_total")),
            "answer_entities": (
                scene1_stats["answer_entity_total"],
                _legacy_aggregate(legacy_run, "n_answer_entities_total")),
            "term_results": (
                scene1_stats["term_conflicts"]["total"],
                _legacy_aggregate(legacy_run, "n_term_results_total")),
        },
    }


def _legacy_aggregate(legacy_run: Path | None, key: str) -> int | None:
    if legacy_run is None:
        return None
    summary = json.loads(legacy_run.read_text(encoding="utf-8"))["summary"]
    return summary.get(key)


def jieba_gazetteer_demo(rows: list[dict[str, Any]],
                          lexicon: NerLexicon) -> dict[str, Any]:
    """configure_jieba自动add_word后的整词命中(gazetteer效应)."""
    lexicon_words = set(lexicon.domain_terms)
    for values in lexicon.value_domains.values():
        lexicon_words.update(values)
    for words in lexicon.entity_categories.values():
        lexicon_words.update(words)
    texts = _statement_texts(rows)
    hits: Counter[str] = Counter()
    n_tokens = 0
    for text in texts:
        tokens = tokenize(text, lexicon)
        n_tokens += len(tokens)
        for token in tokens:
            if token in lexicon_words:
                hits[token] += 1
    sample_text = texts[0] if texts else ""
    return {
        "n_texts": len(texts),
        "n_tokens": n_tokens,
        "gazetteer_hit_total": sum(hits.values()),
        "gazetteer_hit_types": len(hits),
        "gazetteer_hits_top": [[w, c] for w, c in hits.most_common(SAMPLE_N)],
        "tokenize_sample": tokenize(sample_text, lexicon)[:12] if sample_text else [],
    }


def _isolated_tokenize(text: str, lexicon_path: Path) -> list[str]:
    """隔离子进程分词: jieba词典是进程级累积的, 场景对比必须各自新进程."""
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(BASE)!r})\n"
        "from algorithms.consistency.ner_lexicon import load_lexicon, tokenize\n"
        f"lex = load_lexicon({str(lexicon_path)!r})\n"
        "print(json.dumps(tokenize(sys.argv[1], lex), ensure_ascii=False))\n"
    )
    env = dict(os.environ, PYTHONUTF8="1")
    result = subprocess.run(
        [sys.executable, "-c", code, text], capture_output=True,
        text=True, encoding="utf-8", cwd=BASE, env=env, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(
            f"隔离子进程分词失败(rc={result.returncode}): "
            f"{result.stderr[-500:]}")
    return json.loads(result.stdout)


def scene_ablation_doc06(rows: list[dict[str, Any]],
                         scene1: NerLexicon,
                         doc06: NerLexicon) -> dict[str, Any]:
    """06号证据×两份lexicon: 配置差异的可见效果(同一引擎)."""
    def domain_hits(lexicon: NerLexicon) -> Counter[str]:
        terms = set(lexicon.domain_terms)
        hits: Counter[str] = Counter()
        for row in rows:
            request = request_from_dict(row)
            for statement in linearize_context(request.evidence):
                for entity in extract_entities(statement.text, lexicon):
                    if entity.kind == "domain_term" and entity.surface in terms:
                        hits[entity.surface] += 1
        return hits

    scene1_hits = domain_hits(scene1)
    doc06_hits = domain_hits(doc06)
    shared_text = "系统能够读取数据库连接状态并监控系统运行状态监控指标"
    return {
        "doc06_only_terms": sorted(set(doc06_hits) - set(scene1_hits)),
        "doc06_domain_term_hits": sum(doc06_hits.values()),
        "scene1_domain_term_hits": sum(scene1_hits.values()),
        "doc06_hit_samples": [[w, c] for w, c in doc06_hits.most_common(SAMPLE_N)],
        "jieba_tokens_scene1_lexicon": _isolated_tokenize(
            shared_text, LEXICON_DIR / "srs_scene1.json"),
        "jieba_tokens_doc06_lexicon": _isolated_tokenize(
            shared_text, LEXICON_DIR / "doc06_scene.json"),
    }


def _print_table(header: list[str], rows: list[list[str]]) -> None:
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
              for i, h in enumerate(header)]
    line = "  ".join(h.ljust(w) for h, w in zip(header, widths))
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))


def _fmt_counter(counts: dict[str, int]) -> str:
    return ", ".join(f"{k}:{v}" for k, v in counts.items()) or "-"


def main() -> None:
    scene1_lex = load_lexicon(LEXICON_DIR / "srs_scene1.json")
    doc06_lex = load_lexicon(LEXICON_DIR / "doc06_scene.json")
    scene1_rows = load_frozen_qa()
    doc06_rows = load_crossdoc06_rows()

    print("== L0 NER词典配置化: 跨场景迁移演示(同一引擎, 两份配置) ==")
    print("engine : algorithms/consistency/entity_detector.py (逻辑通用化)")
    print(f"scene1 : {LEXICON_DIR / 'srs_scene1.json'} -> 04号 scene1_qa_frozen_v1"
          f"({len(scene1_rows)}行)")
    print(f"doc06  : {LEXICON_DIR / 'doc06_scene.json'} -> 06号 crossdoc06_evalset_v1"
          f"({len(doc06_rows)}行)")

    scene1_stats = scene_stats(scene1_rows, scene1_lex)
    doc06_stats = scene_stats(doc06_rows, doc06_lex)
    equivalence = check_legacy_equivalence(scene1_stats)
    jieba_scene1 = jieba_gazetteer_demo(scene1_rows, scene1_lex)
    jieba_doc06 = jieba_gazetteer_demo(doc06_rows, doc06_lex)
    ablation = scene_ablation_doc06(doc06_rows, scene1_lex, doc06_lex)

    print()
    print("== 行为等价(04号): srs_scene1配置 vs 旧硬编码基线 ==")
    agg = equivalence["aggregate_equivalence"]
    print(f"逐实体digest: {equivalence['n_digest_equal']}/{equivalence['n_rows']}"
          f"行一致, mismatch={equivalence['mismatched_instance_ids'] or '无'}")
    print(f"全局digest  : {equivalence['global_digest'][:16]}... == "
          f"{equivalence['legacy_global_digest'][:16]}... "
          f"({equivalence['all_equal']})")
    print(f"实体总数    : 语句{agg['statement_entities'][0]} (legacy "
          f"{agg['statement_entities'][1]}), answer"
          f"{agg['answer_entities'][0]} (legacy {agg['answer_entities'][1]})")
    print(f"TERM结果    : {agg['term_results'][0]} (legacy "
          f"{agg['term_results'][1]})")
    print(f"基线dump    : {equivalence['legacy_run_dump'] or '(fixture only)'}")

    print()
    print("== 两场景对比表(同一引擎, 换配置) ==")
    s1, d6 = scene1_stats, doc06_stats
    _print_table(
        ["指标", f"srs_scene1(04号,{s1['n_rows']}行)",
         f"doc06_scene(06号,{d6['n_rows']}行)"],
        [
            ["语句实体总数", str(s1["statement_entity_total"]),
             str(d6["statement_entity_total"])],
            ["  domain_term", str(s1["statement_entity_kinds"].get(
                "domain_term", 0)), str(d6["statement_entity_kinds"].get(
                "domain_term", 0))],
            ["  pzxq_id", str(s1["statement_entity_kinds"].get("pzxq_id", 0)),
             str(d6["statement_entity_kinds"].get("pzxq_id", 0))],
            ["  chinese", str(s1["statement_entity_kinds"].get("chinese", 0)),
             str(d6["statement_entity_kinds"].get("chinese", 0))],
            ["  quoted", str(s1["statement_entity_kinds"].get("quoted", 0)),
             str(d6["statement_entity_kinds"].get("quoted", 0))],
            ["  mixed", str(s1["statement_entity_kinds"].get("mixed", 0)),
             str(d6["statement_entity_kinds"].get("mixed", 0))],
            ["answer实体总数", str(s1["answer_entity_total"]),
             str(d6["answer_entity_total"])],
            ["能力名(唯一)", str(s1["document_lexicon"]["capability_names"]),
             str(d6["document_lexicon"]["capability_names"])],
            ["用例名(唯一)", str(s1["document_lexicon"]["usecase_names"]),
             str(d6["document_lexicon"]["usecase_names"])],
            ["接口ID(唯一)", str(s1["document_lexicon"]["interface_ids"]),
             str(d6["document_lexicon"]["interface_ids"])],
            ["方式名称值域", "/".join(s1["document_lexicon"]["mode_values"]) or "-",
             "/".join(d6["document_lexicon"]["mode_values"]) or "-"],
            ["运行状态值域", "/".join(s1["document_lexicon"]["status_values"]) or "-",
             "/".join(d6["document_lexicon"]["status_values"]) or "-"],
            ["数据库(唯一)", "/".join(s1["document_lexicon"]["database_names"]) or "-",
             "/".join(d6["document_lexicon"]["database_names"]) or "-"],
            ["别名对(唯一)", str(s1["document_lexicon"]["alias_pairs"]),
             str(d6["document_lexicon"]["alias_pairs"])],
            ["TERM检测总数", str(s1["term_conflicts"]["total"]),
             str(d6["term_conflicts"]["total"])],
        ])

    print()
    print("== 样例 ==")
    print("scene1 实体:", json.dumps(s1["entity_samples"], ensure_ascii=False))
    print("doc06  实体:", json.dumps(d6["entity_samples"], ensure_ascii=False))
    print("scene1 词典:", json.dumps(
        {k: v for k, v in s1["document_lexicon"].items()
         if k.endswith(("samples", "values", "names"))}, ensure_ascii=False))
    print("doc06  词典:", json.dumps(
        {k: v for k, v in d6["document_lexicon"].items()
         if k.endswith(("samples", "values", "names"))}, ensure_ascii=False))
    print("scene1 TERM:", _fmt_counter(s1["term_conflicts"]["by_method"]))
    print("doc06  TERM:", _fmt_counter(d6["term_conflicts"]["by_method"]))

    print()
    print("== jieba gazetteer链路(configure_jieba自动add_word, HMM=False) ==")
    print(f"scene1: {jieba_scene1['gazetteer_hit_total']}次整词命中"
          f"({jieba_scene1['gazetteer_hit_types']}类) "
          f"top={jieba_scene1['gazetteer_hits_top']}")
    print(f"doc06 : {jieba_doc06['gazetteer_hit_total']}次整词命中"
          f"({jieba_doc06['gazetteer_hit_types']}类) "
          f"top={jieba_doc06['gazetteer_hits_top']}")

    print()
    print("== 场景消融: 06号证据 × 两份lexicon(证明换配置不换代码) ==")
    print(f"domain_term命中: scene1配置={ablation['scene1_domain_term_hits']}, "
          f"doc06配置={ablation['doc06_domain_term_hits']} "
          f"(06号特有词: {ablation['doc06_only_terms']})")
    print(f"同句分词对比: '{'系统能够读取数据库连接状态并监控系统运行状态监控指标'}'")
    print(f"  scene1词典: {ablation['jieba_tokens_scene1_lexicon']}")
    print(f"  doc06 词典: {ablation['jieba_tokens_doc06_lexicon']}")

    run = open_run("demo_lexicon_transfer", {
        "engine": "algorithms/consistency/entity_detector.py",
        "lexicons": [str((LEXICON_DIR / "srs_scene1.json").relative_to(BASE)),
                     str((LEXICON_DIR / "doc06_scene.json").relative_to(BASE))],
        "datasets": [
            "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
            "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"],
        "legacy_baseline": {
            "fixture": str(LEGACY_FIXTURE.relative_to(BASE)),
            "global_digest": equivalence["legacy_global_digest"],
            "run_dump": equivalence["legacy_run_dump"]},
    })
    result = {
        "equivalence": {k: v for k, v in equivalence.items()},
        "scene1": {k: v for k, v in scene1_stats.items() if k != "_records"},
        "doc06": {k: v for k, v in doc06_stats.items() if k != "_records"},
        "jieba": {"scene1": jieba_scene1, "doc06": jieba_doc06},
        "ablation_doc06": ablation,
    }
    run.save_result(result)
    print()
    print(f"run: {run.path}")
    ok = equivalence["all_equal"]
    print(f"RESULT: {'EQUIVALENT' if ok else 'MISMATCH'} "
          f"(scene1 91行逐实体一致={ok})")


if __name__ == "__main__":
    main()
