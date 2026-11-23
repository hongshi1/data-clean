"""Root-cause field evaluation on violations-17 (M92).

对violations-17(17条真实文档违例, answer按违例侧断言, gold块全在冻结
证据内)跑QAConsistencyModule(use_experts=True, use_nli_residual=True,
nli_model_path=models/nli/distilled_v1, nli_gate=0.8), 评测每条检出
refute的localization携带的root_cause(根因源×根因操作两层分类):

1. 预测root_cause.source / root_cause.operation分布(逐localization);
2. 与构造gold对齐: GOLD_ROOT_CAUSE把violation_evalset_v1的
   violation_category/item_id/violation_desc映射到两层根因(构造者
   视角: 17条全部是文档侧真实缺陷→document_internal为主, 合规覆盖
   缺口类→document_gap; operation=13条NLI差异类型+4条结构扩展);
3. 根因操作分类准确率: 实例级any-hit(任一localization的operation==
   gold operation; 多通道/附带检出下一个实例可有多条定位)与逐
   localization两种口径;
4. 召回不足混淆检查: 冻结证据模式下gold块必在证据内, 不存在召回
   问题→预期0条source=recall_insufficient, 如实记录;
5. 落盘data/gjb_438c/distillation/root_cause_eval_v1.json(带git_sha
   与配置, 延续distillation评测的固定摘要路径约定).

用法: $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
      python tools/eval_root_cause.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    read_jsonl,
)
from algorithms.consistency.root_cause import (  # noqa: E402
    NLI_DIFFERENCE_OPERATIONS,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
TAXONOMY = BASE / "knowledge/nli_difference_taxonomy.json"
OUT = BASE / "data/gjb_438c/distillation/root_cause_eval_v1.json"

#: 构造gold: violations-17的violation_category/item_id/violation_desc→
#: 两层根因(根因源, 根因操作). 原则: (i)17条全是文档侧真实缺陷, 根因源
#: =document_internal(文档自相矛盾)或document_gap(缺应规定内容);
#: (ii)操作优先对齐knowledge/nli_difference_taxonomy.json的13条
#: difference_type(business_labels桥接item_id), NLI条目不覆盖的注册表/
#: 封闭集/合规结构机制用扩展操作(dual_registration/scope_leakage/
#: compliance_gap); (iii)note记录映射依据, 供误配分析回溯.
GOLD_ROOT_CAUSE: dict[str, dict[str, str]] = {
    "DOC04-VIO-01": {
        "source": "document_internal", "operation": "dual_registration",
        "note": "TERM-07同ID双指: 表39与节标题把同一ID登记给两个用例"
                "(注册表唯一性缺陷, 13条NLI类型外的结构机制)"},
    "DOC04-VIO-02": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "TERM-07 ID截断: 节标题SJKGB vs 表4 SJKGBGN跨位置不一致"
                "(NLI-VAL-01值变形/截断)"},
    "DOC04-VIO-03": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "TERM-07前缀变形: 表48 SJTBGX vs 节标题SJTYFW两套前缀"
                "(值变形)"},
    "DOC04-VIO-04": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "TERM-07段序变形: DMSC-DXHFW vs DXHFW-DMSC组件段序颠倒"
                "(标识符变形)"},
    "DOC04-VIO-05": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "TERM-07段缺失: BLOB子项ID缺BLOBSJCZ段(值截断)"},
    "DOC04-VIO-06": {
        "source": "document_internal", "operation": "scope_leakage",
        "note": "TERM-03枚举范围: 正文枚举5项超出表3封闭4行, answer成员"
                "泄漏出封闭注册集(成员确在文档正文, 非凭空编造)"},
    "DOC04-VIO-07": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "TERM-03成员名替换: 正文「缓存修改」vs表32「缓存更新」——"
                "同一子功能跨位置两名(枚举值变形, 非成员多出)"},
    "DOC04-VIO-08": {
        "source": "document_internal", "operation": "scope_leakage",
        "note": "TERM-03分类法错配: 1.2两套分类与3.2六项封闭分类不一致,"
                "answer的分类项泄漏出3.2封闭分类"},
    "DOC04-VIO-09": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "LOGIC-05错别字: 表9注册值「平版」为「平板」之变形, "
                "answer声明正确值被错值反驳(文档侧值变形)"},
    "DOC04-VIO-10": {
        "source": "document_internal", "operation": "relation_inversion",
        "note": "GJB-05正逆矛盾: 表81/表82对3.2.4的正逆追踪指向不同任务书"
                "章节(方向性关系反转)"},
    "DOC04-VIO-11": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "GJB-05悬空锚点: row16追踪指向不存在的3.2.1.7节(无效"
                "章节值)"},
    "DOC04-VIO-12": {
        "source": "document_internal", "operation": "negation_mismatch",
        "note": "GJB-05同行矛盾: row20映射非空与说明列「不追踪」极性相反"
                "(否定错配)"},
    "DOC04-VIO-13": {
        "source": "document_internal", "operation":
            "exception_flow_mismatch",
        "note": "LOGIC-02 E1错位: 缓存/连接池用例的E1均为「系统提示初始化」"
                "(跨用例复制, 异常流与主题错配)"},
    "DOC04-VIO-14": {
        "source": "document_internal", "operation": "entity_substitution",
        "note": "LOGIC-02归属错配: 概述把申请/释放句柄错误归属为热点数据"
                "缓存的扩展用例(主体张冠李戴, NLI-ENT-01)"},
    "DOC04-VIO-15": {
        "source": "document_internal", "operation": "value_substitution",
        "note": "TERM-05文档名变形: 「数据同步共享服务」≠「数据统一访问"
                "服务」(名称值替换; 本实例系统未检出, 无定位可评)"},
    "DOC04-VIO-16": {
        "source": "document_gap", "operation": "compliance_gap",
        "note": "GJB-04功能声明缺失: 1.2声称访问审计及日志记录功能, 3.2/"
                "表2无对应能力定义(声明-定义覆盖缺口, 文档侧缺内容)"},
    "DOC04-VIO-17": {
        "source": "document_gap", "operation": "compliance_gap",
        "note": "GJB-01合格性缺口: 表80仅覆盖3.2.x, 3.3~3.17全部需求无"
                "合格性方法(GJB合规覆盖缺口)"},
}

#: 预期误配的构造性解释(检测通道附带检出/词汇局限, 非随机错误)
MISMATCH_NOTES: dict[str, str] = {
    "DOC04-VIO-07": "enum_join的rationale对『成员改名』(gold="
                    "value_substitution)与『成员多出』(VIO-06, scope_"
                    "leakage)给出同构描述(『answer成员X见于正文枚举但不在"
                    "封闭集合』), 通道词汇无法区分——需成员级名称相似度信号",
    "DOC04-VIO-08": "coverage_join按GJB-04封闭清单把『审计日志条款缺失』"
                    "判为document_gap/compliance_gap——检出的是文档真实"
                    "缺口(与VIO-16同源), 构造gold是分类法错配; 通道把分类"
                    "法错配归因为合规缺口",
    "DOC04-VIO-11": "trace通道检出row20同行矛盾(VIO-12注入的违例; 对该"
                    "违例negation_mismatch是正确根因), 未检出row16悬空"
                    "锚点——附带检出, 检出对象≠注入违例",
    "DOC04-VIO-14": "e1通道检出E1模板复制错位(对该违例exception_flow_"
                    "mismatch是正确根因), 未检出申请/释放句柄归属错配"
                    "(gold=entity_substitution)——附带检出",
}

#: 评测配置(与measure_localization_baseline/论文D1口径一致)
MODULE_CONFIG: dict[str, object] = {
    "use_experts": True,
    "use_nli_residual": True,
    "nli_model_path": "models/nli/distilled_v1",
    "nli_gate": 0.8,
}


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=BASE,
            capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def _taxonomy_alignment() -> dict[str, object]:
    """root_cause常量表与taxonomy文件的13条差异类型一致性守卫."""
    items = json.loads(TAXONOMY.read_text(encoding="utf-8"))["items"]
    file_ops = {str(it["difference_type"]) for it in items}
    constant_ops = set(NLI_DIFFERENCE_OPERATIONS)
    return {
        "ok": file_ops == constant_ops,
        "n_file": len(file_ops),
        "n_constant": len(constant_ops),
        "only_in_file": sorted(file_ops - constant_ops),
        "only_in_constant": sorted(constant_ops - file_ops),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    records = read_jsonl(VIO)
    module = QAConsistencyModule(
        use_experts=bool(MODULE_CONFIG["use_experts"]),
        use_nli_residual=bool(MODULE_CONFIG["use_nli_residual"]),
        nli_model_path=str(MODULE_CONFIG["nli_model_path"]),
        nli_gate=float(MODULE_CONFIG["nli_gate"]))

    instances: list[dict[str, object]] = []
    source_dist: Counter[str] = Counter()
    operation_dist: Counter[str] = Counter()
    method_cause: dict[str, Counter[str]] = {}
    n_loc_total = 0
    n_op_match_loc = 0
    n_source_match_loc = 0
    n_detected = 0
    n_op_any = 0
    n_source_any = 0
    recall_confusion = 0
    missed: list[str] = []
    mismatches: list[dict[str, object]] = []

    for rec in records:
        iid = str(rec["instance_id"])
        gold = GOLD_ROOT_CAUSE[iid]
        result = module.verify(build_qa_input(rec))
        locs: list[dict[str, object]] = []
        ops: set[str] = set()
        sources: set[str] = set()
        for loc in result.localizations:
            cause = loc.root_cause or {}
            source = str(cause.get("source", ""))
            operation = str(cause.get("operation", ""))
            ops.add(operation)
            sources.add(source)
            source_dist[source] += 1
            operation_dist[operation] += 1
            method_cause.setdefault(loc.method, Counter())[
                f"{source}/{operation}"] += 1
            n_loc_total += 1
            op_match = operation == gold["operation"]
            source_match = source == gold["source"]
            n_op_match_loc += int(op_match)
            n_source_match_loc += int(source_match)
            if source == "recall_insufficient":
                recall_confusion += 1
            locs.append({
                "method": loc.method,
                "claim_text": loc.claim_text[:80],
                "root_cause": {"source": source, "operation": operation},
                "operation_matches_gold": op_match,
                "source_matches_gold": source_match,
            })
        detected = result.verdict == "refute"
        if detected:
            n_detected += 1
        else:
            missed.append(iid)
        op_any = detected and gold["operation"] in ops
        source_any = detected and gold["source"] in sources
        n_op_any += int(op_any)
        n_source_any += int(source_any)
        if detected and not op_any:
            mismatches.append({
                "instance_id": iid,
                "gold": {"source": gold["source"],
                         "operation": gold["operation"]},
                "predicted_operations": sorted(ops),
                "predicted_sources": sorted(sources),
                "note": MISMATCH_NOTES.get(
                    iid, gold["note"] + "(未登记的误配模式, 需人工分析)"),
            })
        instances.append({
            "instance_id": iid,
            "violation_category": str(rec.get("violation_category", "")),
            "item_id": str(rec.get("item_id", "")),
            "verdict": result.verdict,
            "n_localizations": len(locs),
            "gold_root_cause": gold,
            "localizations": locs,
            "operation_any_hit": op_any,
            "source_any_hit": source_any,
        })
        print(f"{iid}: verdict={result.verdict:8s} locs={len(locs)} "
              f"gold={gold['source']}/{gold['operation']} "
              f"pred_ops={sorted(ops) or '-'} "
              f"{'OP✓' if op_any else 'OP✗'}"
              f"{' SRC✓' if source_any else ' SRC✗'}")

    payload = {
        "schema": "root_cause_eval_v1",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "git_sha": _git_sha(),
        "module_config": MODULE_CONFIG,
        "dataset": {"path": str(VIO.relative_to(BASE)), "n_instances":
                    len(records)},
        "detection": {
            "n_refute": n_detected,
            "n_missed": len(missed),
            "missed_instances": missed,
            "note": "DOC04-VIO-15(文档名变形)未检出→无定位可评, "
                    "不计入根因准确率分母(检出率16/17与D1基线一致)",
        },
        "gold_mapping": GOLD_ROOT_CAUSE,
        "predicted": {
            "n_localizations": n_loc_total,
            "source_distribution": dict(sorted(source_dist.items())),
            "operation_distribution": dict(sorted(operation_dist.items())),
            "method_to_root_cause": {
                method: dict(sorted(counter.items()))
                for method, counter in sorted(method_cause.items())},
        },
        "accuracy": {
            "operation_any_hit": round(n_op_any / n_detected, 4),
            "operation_any_hit_fraction": f"{n_op_any}/{n_detected}",
            "operation_per_localization": round(
                n_op_match_loc / n_loc_total, 4),
            "operation_per_localization_fraction":
                f"{n_op_match_loc}/{n_loc_total}",
            "source_any_hit": round(n_source_any / n_detected, 4),
            "source_any_hit_fraction": f"{n_source_any}/{n_detected}",
            "source_per_localization": round(
                n_source_match_loc / n_loc_total, 4),
            "source_per_localization_fraction":
                f"{n_source_match_loc}/{n_loc_total}",
        },
        "recall_insufficient_check": {
            "n_recall_insufficient_predictions": recall_confusion,
            "note": "冻结证据模式下gold块全部在实例证据内(构造协议), 不存在"
                    "召回缺失; 0条recall_insufficient预测=无召回混淆",
        },
        "mismatches": mismatches,
        "taxonomy_alignment": _taxonomy_alignment(),
        "instances": instances,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")

    acc = payload["accuracy"]
    print(f"\n检出 refute {n_detected}/{len(records)} (missed: {missed})")
    print(f"localizations总数: {n_loc_total}")
    print(f"source分布: {dict(sorted(source_dist.items()))}")
    print(f"operation分布: {dict(sorted(operation_dist.items()))}")
    print(f"根因操作准确率(any-hit): {acc['operation_any_hit_fraction']}"
          f" ({acc['operation_any_hit']})")
    print(f"根因操作准确率(逐localization): "
          f"{acc['operation_per_localization_fraction']}"
          f" ({acc['operation_per_localization']})")
    print(f"根因源准确率(any-hit): {acc['source_any_hit_fraction']}"
          f" ({acc['source_any_hit']})")
    print(f"recall_insufficient混淆: {recall_confusion}条(预期0)")
    print(f"误配实例: {[m['instance_id'] for m in mismatches]}")
    print(f"落盘: {OUT}")


if __name__ == "__main__":
    main()
