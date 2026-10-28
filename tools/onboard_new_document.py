"""新文档一键接入工具: content_list → 归纳 → rulepack+词典草稿 → 校验 → GJB合规审计 → 报告.

把"新SRS文档接入"从手工改配置变成一条命令(迁移复用从文档主张变成可
演示能力):

  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
  python tools/onboard_new_document.py --doc 01 [--output-dir config]

流程(归纳全部确定性; 草稿不假装全自动——不确定项标_needs_review):
  1. 定位content_list.json(按doc号glob, 预期恰好1个);
  2. 归纳引擎(algorithms/consistency/onboarding.py)→归纳报告
     (表格聚类/ID族/值域/域术语), 控制台打印供人工检查草稿;
  3. 生成两份配置草稿: <output-dir>/rulepacks/doc<NN>_onboard_v1.json
     + <output-dir>/ner_lexicons/doc<NN>_scene.json;
  4. 校验: load_rulepack/load_lexicon(schema错误即失败) + 簇映射
     rule_ids全部存在于规则库(缺口#3) + gjb段与基pack逐字一致
     (标准级知识不动——审计引擎按默认pack读簇映射, 不一致即失败);
  5. 用新pack跑GJB合规审计(复用audit_gjb_compliance的load_doc_blocks/
     audit_with_pack, 参数化pack与文档), 并附04号基线对比——同标准
     不同文档的合规差异本身是有意义的输出;
  6. runs协议落盘: onboarding报告+两份配置+审计结果。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from glob import glob
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.gjb_rule_engine import (  # noqa: E402
    CHECK_ITEMS,
    load_rule_library,
)
from algorithms.consistency.ner_lexicon import load_lexicon  # noqa: E402
from algorithms.consistency.onboarding import (  # noqa: E402
    InductionReport,
    build_lexicon_draft,
    build_rulepack_draft,
    induce_report,
    validate_cluster_rule_ids,
    validate_gjb_section_unchanged,
)
from algorithms.consistency.rulepack import (  # noqa: E402
    default_rulepack,
    load_rulepack,
)
from tools.audit_gjb_compliance import (  # noqa: E402
    CONTENT_LIST_GLOB as DOC04_GLOB,
    DOC04_ID,
    audit_with_pack,
    load_doc_blocks,
)
from tools.run_utils import open_run  # noqa: E402

BASE_PACK_PATH = BASE / "config/rulepacks/srs_gjb_v1.json"
BASE_LEXICON_PATH = BASE / "config/ner_lexicons/srs_scene1.json"
MINERU_ROOT = "data/gjb_438c/mineru_standard"
#: 与04号同标准的对比基线(审计口径与audit_gjb_compliance一致)


def locate_content_list(doc: str) -> tuple[Path, str]:
    """按doc号glob定位content_list(预期恰好1个), 返回(路径, 文档目录名)."""
    pattern = f"{MINERU_ROOT}/{doc}*/office/*_content_list.json"
    paths = sorted(glob(str(BASE / pattern)))
    if len(paths) != 1:
        raise SystemExit(
            f"[onboard] 预期1个content_list({pattern})，实际{len(paths)}: "
            + "、".join(str(p) for p in paths))
    return Path(paths[0]), Path(paths[0]).parents[1].name


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _print_induction_report(report: InductionReport) -> None:
    print(f"== 归纳报告: {report.doc_key} "
          f"({report.block_count}块/{report.table_count}表) ==")
    print("-- 表格聚类(按表头集合; matched=基pack签名分类) --")
    for cluster in report.table_clusters:
        headers = "|".join(cluster.header_signature[:4])
        more = "…" if len(cluster.header_signature) > 4 else ""
        review = " [需复核]" if cluster.needs_review else ""
        caption = f"  ({cluster.sample_captions[0]})" \
            if cluster.sample_captions else ""
        print(f"  ×{cluster.occurrences:2d} {cluster.matched_kind:20s}"
              f"{review} {headers}{more}{caption}")
    print()
    own = [f for f in report.id_families if f.own_root]
    external = [f for f in report.id_families if not f.own_root]
    print(f"-- ID族: 根={report.id_root or '(无ID)'} "
          f"自身{sum(f.occurrences for f in own)}次/{len(own)}族, "
          f"外部{sum(f.occurrences for f in external)}次/{len(external)}族 --")
    for family in own[:8]:
        print(f"  自身 {family.family_prefix:28s} ×{family.occurrences:3d}"
              f" (去重{family.distinct_ids}, 样例{family.sample_ids[0]})")
    for family in external[:5]:
        print(f"  外部 {family.family_prefix:28s} ×{family.occurrences:3d}"
              f" (不参与join范围)")
    print()
    print("-- 值域(闭集草稿) --")
    if report.value_domains:
        for field, values in report.value_domains.items():
            print(f"  {field}: {'、'.join(values)}")
    else:
        print("  精确列匹配: 无(该文档无方式名称/运行状态列)")
    for candidate in report.value_domain_candidates:
        print(f"  候选(需人工): {candidate.field}≈列「{candidate.header}」"
              f"值{{{ '、'.join(candidate.values) }}}")
    print()
    terms = "、".join(f"{term}({freq})" for term, freq
                      in report.domain_terms)
    print(f"-- 域术语草稿(≥3次) --\n  {terms}")
    print()


def _print_audit_comparison(audits: dict, audits04: dict,
                            doc_key: str) -> list[dict]:
    print(f"== {doc_key} GJB合规审计(新pack驱动, 分簇verdict) 与04号基线对比 ==")
    rows: list[dict] = []
    same = 0
    for cluster in CHECK_ITEMS:
        verdict = audits[cluster].verdict
        verdict04 = audits04[cluster].verdict
        equal = verdict == verdict04
        same += int(equal)
        marker = "==" if equal else "!="
        print(f"  {cluster} {verdict:9s} {marker} 04号{verdict04:9s}"
              + ("" if equal else "  (文档差异)"))
        rows.append({
            "cluster": cluster,
            "doc_verdict": verdict,
            "doc04_verdict": verdict04,
            "same": equal,
            "matched_patterns": list(audits[cluster].matched_patterns),
            "missed_patterns": list(audits[cluster].missed_patterns),
            "evidence_refs": list(audits[cluster].evidence_refs),
        })
    print(f"  同标准同结论 {same}/11 簇; 差异簇=文档内容差异"
          f"(同规则库同簇映射, 输入文档不同)")
    key_findings = {
        "掉电(GJB-08)": audits["GJB-08"].verdict,
        "追溯(GJB-05)": audits["GJB-05"].verdict,
        "合格性(GJB-01)": audits["GJB-01"].verdict,
        "输入防护(GJB-09)": audits["GJB-09"].verdict,
        "报警要素(GJB-06)": audits["GJB-06"].verdict,
        "降级模式(GJB-11)": audits["GJB-11"].verdict,
    }
    print("  关键发现: " + "、".join(
        f"{k}={v}" for k, v in key_findings.items()))
    print()
    return rows


def _audit_summary(elements: dict, blocks_count: int) -> dict:
    results = elements["results"]
    checks = elements["checks"]
    compiled = [c for c in checks if c.check_type != "manual"]
    manual = [c for c in checks if c.check_type == "manual"]
    return {
        "blocks": blocks_count,
        "statements": len(elements["statements"]),
        "rules_total": len(elements["rules"]),
        "compilable": len(compiled),
        "manual": len(manual),
        "rule_verdicts": dict(Counter(r.verdict for r in results)),
        "cluster_verdicts": {
            cluster: elements["audits"][cluster].verdict
            for cluster in CHECK_ITEMS},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="新文档一键接入: 归纳配置草稿→校验→GJB合规审计→报告")
    parser.add_argument("--doc", required=True,
                        help="文档号(如01, 按mineru_standard/<doc>* glob)")
    parser.add_argument("--output-dir", default="config",
                        help="配置草稿输出目录(默认config, 相对仓库根)")
    args = parser.parse_args()

    digits = re.sub(r"\D", "", args.doc)
    if not digits:
        raise SystemExit(f"[onboard] --doc须含数字文档号, got {args.doc!r}")
    doc_key = f"doc{digits}"
    content_path, doc_id = locate_content_list(args.doc)
    blocks = _load_json(content_path)
    base_pack_raw = _load_json(BASE_PACK_PATH)
    base_lexicon_raw = _load_json(BASE_LEXICON_PATH)

    print(f"[onboard] {doc_key} <- "
          f"{content_path.relative_to(BASE)} ({len(blocks)}块)")
    print()

    # 2. 归纳
    report = induce_report(blocks, doc_key, base_pack_raw)
    _print_induction_report(report)

    # 3. 草稿生成
    pack_draft = build_rulepack_draft(doc_key, blocks, base_pack_raw)
    lexicon_draft = build_lexicon_draft(doc_key, blocks, base_lexicon_raw)
    output_dir = (BASE / args.output_dir).resolve()
    pack_path = output_dir / "rulepacks" / f"{doc_key}_onboard_v1.json"
    lexicon_path = output_dir / "ner_lexicons" / f"{doc_key}_scene.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    lexicon_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(
        json.dumps(pack_draft, ensure_ascii=False, indent=1),
        encoding="utf-8")
    lexicon_path.write_text(
        json.dumps(lexicon_draft, ensure_ascii=False, indent=1),
        encoding="utf-8")
    onboarding = pack_draft["_onboarding"]
    print("== 配置草稿(可检查, 不确定项已标_needs_review) ==")
    print(f"  {pack_path.relative_to(BASE)}")
    print(f"    应用变更{len(onboarding['changes'])}项: "
          + "、".join(change["target"]
                      for change in onboarding["changes"]))
    print(f"    待复核{len(onboarding['needs_review'])}项"
          f"(表头变体/新表型归型, 见_onboarding.needs_review)")
    print(f"  {lexicon_path.relative_to(BASE)}")
    print()

    # 4. 校验(schema + 缺口#3簇映射存在性 + 标准级知识不动)
    pack = load_rulepack(pack_path)
    lexicon = load_lexicon(lexicon_path)
    rules = _load_rules(pack)
    missing = validate_cluster_rule_ids(pack_draft, rules)
    if missing:
        raise SystemExit(
            f"[onboard] 簇映射引用了规则库不存在的rule_ids: {missing}")
    if not validate_gjb_section_unchanged(pack_draft, base_pack_raw):
        raise SystemExit(
            "[onboard] 草稿gjb段与基pack不一致(标准级知识须逐字保留): "
            "审计引擎按默认pack读取簇映射, 分歧会导致裁决失真")
    print("== 校验 ==")
    print(f"  load_rulepack: OK (pack_id={pack.pack_id}, "
          f"表型{len(pack.table_schemas)}、模板{len(pack.extraction_templates)})")
    print(f"  load_lexicon: OK (scene={lexicon.scene}, "
          f"域术语{len(lexicon.domain_terms)}、"
          f"值域{ {k: len(v) for k, v in lexicon.value_domains.items()} })")
    print(f"  簇映射rule_ids: 全部存在于规则库"
          f"({len(rules)}条SRS适用/{len(_all_rule_ids(pack))}条总)")
    print("  gjb段与基pack逐字一致: True (标准级知识未动)")
    print()

    # 5. 用新pack跑GJB合规审计 + 04号基线对比
    doc_glob = f"{MINERU_ROOT}/{args.doc}*/office/*_content_list.json"
    doc_blocks = load_doc_blocks(doc_glob, doc_id)
    elements = audit_with_pack(doc_blocks, pack)
    blocks04 = load_doc_blocks(DOC04_GLOB, DOC04_ID)
    elements04 = audit_with_pack(blocks04, default_rulepack())
    comparison = _print_audit_comparison(
        elements["audits"], elements04["audits"], doc_key)

    # 6. runs协议落盘: 报告+两份配置+审计结果
    run = open_run("onboard_new_document", {
        "doc_key": doc_key,
        "doc_id": doc_id,
        "content_list": str(content_path.relative_to(BASE)),
        "blocks": len(blocks),
        "base_pack": str(BASE_PACK_PATH.relative_to(BASE)),
        "base_lexicon": str(BASE_LEXICON_PATH.relative_to(BASE)),
        "rulepack_draft": str(pack_path.relative_to(BASE)),
        "lexicon_draft": str(lexicon_path.relative_to(BASE)),
        "rule_library": pack.gjb_rule_library_path,
    })
    run.save_result({
        "doc": {
            "doc_key": doc_key, "doc_id": doc_id,
            "content_list": str(content_path.relative_to(BASE)),
            "blocks": len(blocks),
        },
        "induction": report.to_dict(),
        "drafts": {
            "rulepack": str(pack_path.relative_to(BASE)),
            "lexicon": str(lexicon_path.relative_to(BASE)),
        },
        "validation": {
            "rulepack_schema": "OK",
            "lexicon_schema": "OK",
            "cluster_rule_ids_missing": missing,
            "gjb_section_unchanged": True,
        },
        "audit": {
            doc_key: _audit_summary(elements, len(doc_blocks)),
            "doc04_baseline": _audit_summary(elements04, len(blocks04)),
            "comparison": comparison,
        },
    })
    run.write_text(
        f"{doc_key}_onboard_v1.json",
        json.dumps(pack_draft, ensure_ascii=False, indent=1))
    run.write_text(
        f"{doc_key}_scene.json",
        json.dumps(lexicon_draft, ensure_ascii=False, indent=1))
    print(f"runs落盘 -> {run.path}")
    print(f"  result.json(归纳报告+校验+审计+对比) + "
          f"{doc_key}_onboard_v1.json + {doc_key}_scene.json")


def _load_rules(pack) -> list[dict]:
    """规则库加载(pack.gjb_rule_library_path定位, 与审计同一份)."""
    return load_rule_library(str(BASE / pack.gjb_rule_library_path))


def _all_rule_ids(pack) -> list[str]:
    """规则库全量rule_id(总口径; SRS适用子集由_load_rules给出)."""
    library = _load_json(BASE / pack.gjb_rule_library_path)
    return [str(rule.get("rule_id")) for rule in library.get("rules", [])]


if __name__ == "__main__":
    main()
