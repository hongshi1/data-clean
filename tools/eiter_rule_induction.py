"""P3 Eiter回路试点: 教师从06号crossdoc失败例归纳rulepack变体 (99号Phase 3).

任务来源: docs/srs_project/99_unified_action_plan.md (P3) +
docs/srs_project/97_regex_replacement_survey.md §3.4 + 98号D类判定.

范式: "谁写规则"从人工onboard升级为 Eiter式回路——

    失败例(generic pack跑crossdoc06)
      → GLM-5.3教师归纳规则包条目变更 (llm_json_teacher cache=True, 可复现)
      → 符号验证 (load_rulepack全schema校验 = 正则编译+结构+阈值范围)
      → 回归约束 (CLIPR式"修订不回退": 91QA主评测逐实例零回退+聚合不降,
                  crossdoc06错例数单调不增, 专家运行时异常一票否决)
      → 修补回路 (round N: 剩余失败例回流教师, 在已接受变更基础上修补)
      → 逆向剪枝 (RIMRULE式最小化: 移除无效果的已接受变更)
      → 最终pack config/rulepacks/doc06_eiter_v1.json + 与人工doc06_v1对比

评测方法学(关键): 每个pack的评测都在**全新子进程**中执行——
numeric_z3_expert._unit_table是@lru_cache(maxsize=1)且无pack身份键,
gjb_presence_expert的词表正则缓存同样身份盲: 进程内切换pack会继承首个
pack的派生配置(历史eval_crossdoc5_onboard的in-process切换因此被缓存
污染), 子进程隔离是唯一可靠口径(见报告负面发现).

用法:
  python tools/eiter_rule_induction.py run [--rounds 2] [--skip-teacher]
  python tools/eiter_rule_induction.py baseline           # 仅基线对照表
  python tools/eiter_rule_induction.py --worker PACK EVALSET LABELS  # 内部

产出: data/gjb_438c/runs/eiter_rule_induction_*/{result.json, report.md}
      config/rulepacks/doc06_eiter_v1.json (最终接受变更合成)
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE / "tools"), str(BASE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from run_utils import open_run  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CROSSDOC06 = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"
QA91 = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
GENERIC_PACK = BASE / "config/rulepacks/srs_gjb_v1.json"
MANUAL_PACK = BASE / "config/rulepacks/doc06_v1.json"
EITER_PACK = BASE / "config/rulepacks/doc06_eiter_v1.json"
LABELS = ("support", "refute", "not_in_evidence")

#: 教师变更操作白名单(每个op映射到rulepack的一个受控schema位置)
OP_NAMES = (
    "replace_extraction_template",
    "add_canon_map",
    "add_table_signature",
    "set_id_family_prefixes",
    "set_join_param",
    "add_vocabulary_words",
    "set_threshold",
)

#: 教师不可触达的标准级/全局键(由op词表结构性保证, 此处为文档性声明)
PROTECTED_KEYS = ("gjb", "gjb_rule_library_path", "classify_order", "pack_id")

#: 每批失败例的最大条数(教师prompt按family聚簇分批)
BATCH_SIZE = 5

#: 教师调用解析失败的重试次数(追加严格后缀=新缓存键)
TEACHER_MAX_ATTEMPTS = 3

_EVAL_SENTINEL = "EVALJSONBEGIN"


# ═══════════════════════════════════════════════════════════════
# 1. 变更模型: 教师输出的受控操作 → rulepack dict的确定性修改
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class RuleChange:
    """一条教师归纳的规则包变更(受控op + 归纳理由 + 来源失败例)."""

    op: str
    params: dict[str, Any]
    reason: str = ""
    source_failures: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            **dict(self.params),
            "reason": self.reason,
            "source_failures": list(self.source_failures),
        }

    def target_path(self) -> str:
        """变更落点(与人工pack diff做重叠度分析的口径)."""
        if self.op == "replace_extraction_template":
            return f"extraction_templates.{self.params['name']}"
        if self.op == "add_canon_map":
            return f"table_schemas.{self.params['kind']}.canon_map"
        if self.op == "add_table_signature":
            return f"table_schemas.{self.params['kind']}.signatures"
        if self.op == "set_id_family_prefixes":
            return "join_params.id_join.id_family_prefixes"
        if self.op == "set_join_param":
            return (f"join_params.{self.params['expert']}."
                    f"{self.params['key']}")
        if self.op == "add_vocabulary_words":
            return f"term_vocabularies.{self.params['vocab']}"
        if self.op == "set_threshold":
            return f"thresholds.{self.params['key']}"
        return "unknown"

    def apply(self, pack_raw: dict[str, Any]) -> list[str]:
        """确定性应用本变更(就地修改pack dict), 返回应用日志.

        结构性守卫(正则编译/命名组保持)失败抛ValueError(可读消息,
        不静默)。
        """
        logs: list[str] = []
        if self.op == "replace_extraction_template":
            name = self.params["name"]
            pattern = self.params["pattern"]
            flags = int(self.params.get("flags", 0))
            old_groups = _named_groups(
                str(pack_raw["extraction_templates"][name].get(
                    "pattern", "")))
            new_groups = _named_groups(pattern)
            missing = sorted(old_groups - new_groups)
            if missing:
                raise ValueError(
                    f"模板{name!r}替换丢失命名组{missing}(引擎消费方"
                    f"需要这些组)")
            pack_raw["extraction_templates"][name] = {
                "pattern": pattern, "flags": flags}
            logs.append(f"extraction_templates.{name}: pattern替换"
                        f"(命名组{sorted(new_groups)})")
        elif self.op == "add_canon_map":
            kind = self.params["kind"]
            canon = pack_raw["table_schemas"][kind].setdefault(
                "canon_map", {})
            added = 0
            for raw_header, canonical in dict(self.params["entries"]).items():
                if raw_header not in canon:
                    canon[raw_header] = canonical
                    added += 1
            logs.append(f"table_schemas.{kind}.canon_map: +{added}项")
        elif self.op == "add_table_signature":
            kind = self.params["kind"]
            pack_raw["table_schemas"][kind].setdefault(
                "signatures", []).append(dict(self.params["signature"]))
            logs.append(f"table_schemas.{kind}.signatures: +1签名")
        elif self.op == "set_id_family_prefixes":
            prefixes = list(self.params["prefixes"])
            pack_raw.setdefault("join_params", {}).setdefault(
                "id_join", {})["id_family_prefixes"] = prefixes
            logs.append("join_params.id_join.id_family_prefixes="
                        f"{prefixes}")
        elif self.op == "set_join_param":
            expert, key = self.params["expert"], self.params["key"]
            pack_raw.setdefault("join_params", {}).setdefault(
                expert, {})[key] = self.params["value"]
            logs.append(f"join_params.{expert}.{key}="
                        f"{self.params['value']!r}")
        elif self.op == "add_vocabulary_words":
            vocab = self.params["vocab"]
            existing = list(pack_raw["term_vocabularies"][vocab])
            known = set(existing)
            fresh = [w for w in self.params["words"] if w not in known]
            pack_raw["term_vocabularies"][vocab] = existing + fresh
            logs.append(f"term_vocabularies.{vocab}: +{len(fresh)}词")
        elif self.op == "set_threshold":
            key = self.params["key"]
            pack_raw["thresholds"][key] = float(self.params["value"])
            logs.append(f"thresholds.{key}={self.params['value']}")
        else:  # pragma: no cover - parse_teacher_changes已过滤
            raise ValueError(f"未知操作: {self.op!r}")
        return logs


def _named_groups(pattern: str) -> set[str]:
    import re

    try:
        return set(re.compile(pattern).groupindex)
    except re.error as exc:
        raise ValueError(
            f"正则编译失败: {exc}: {pattern[:80]}") from exc


def parse_teacher_changes(
        payload: dict[str, Any],
        known: dict[str, set[str]],
        source_failures: Sequence[str],
) -> tuple[list[RuleChange], list[dict[str, str]]]:
    """教师JSON → (合法RuleChange列表, 非法项错误记录).

    结构性失败(缺changes数组)抛ValueError; 逐项校验(名字白名单/
    值契约/正则编译)失败的条目记入errors返回——教师的个别坏条目
    不作废整批有效归纳, 且坏条目原样上报(不静默)。
    known = pack_known_names(当前基线pack)。
    """
    raw_changes = payload.get("changes")
    if not isinstance(raw_changes, list):
        raise ValueError("教师输出缺合法的'changes'数组")
    changes: list[RuleChange] = []
    errors: list[dict[str, str]] = []
    for index, item in enumerate(raw_changes):
        where = f"changes[{index}]"
        try:
            if not isinstance(item, dict):
                raise ValueError(f"{where}: 须为对象")
            op = item.get("op")
            if op not in OP_NAMES:
                raise ValueError(
                    f"{where}: 非法op {op!r}(合法: {OP_NAMES})")
            reason = str(item.get("reason", "")).strip()
            if not reason:
                raise ValueError(f"{where}: 缺reason(归纳依据)")
            params = _validated_params(op, item, known)
            changes.append(RuleChange(
                op=op, params=params, reason=reason,
                source_failures=tuple(source_failures)))
        except ValueError as exc:
            errors.append({"where": where, "error": str(exc)[:200],
                           "raw": json.dumps(item, ensure_ascii=False)[:200]})
    return changes, errors


def _validated_params(op: str, item: dict[str, Any],
                      known: dict[str, set[str]]) -> dict[str, Any]:
    """逐op白名单校验(名字存在于基线pack + 值类型契约)."""
    if op == "replace_extraction_template":
        name = item.get("name")
        if name not in known["templates"]:
            raise ValueError(f"模板名不存在于基线pack: {name!r}")
        pattern = item.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("pattern须为非空字符串")
        flags = item.get("flags", 0)
        if flags not in (0, 32):
            raise ValueError(f"flags只允许0或32, got {flags!r}")
        _named_groups(pattern)
        return {"name": name, "pattern": pattern, "flags": int(flags)}
    if op == "add_canon_map":
        return _validated_canon(item, known)
    if op == "add_table_signature":
        kind = item.get("kind")
        if kind not in known["kinds"] or kind == "generic_table":
            raise ValueError(f"表型非法: {kind!r}")
        signature = item.get("signature")
        if not isinstance(signature, dict) or not signature:
            raise ValueError("signature须为非空对象")
        allowed = {"all_headers", "any_header_groups",
                   "any_header_substring_groups", "caption_contains_any",
                   "raw_contains_any", "raw_regex"}
        unknown = set(signature) - allowed
        if unknown:
            raise ValueError(f"签名含未知字段: {sorted(unknown)}")
        return {"kind": kind, "signature": dict(signature)}
    if op == "set_id_family_prefixes":
        prefixes = item.get("prefixes")
        if (not isinstance(prefixes, list) or not prefixes
                or not all(isinstance(p, str) and p for p in prefixes)):
            raise ValueError("prefixes须为非空字符串列表")
        return {"prefixes": list(prefixes)}
    if op == "set_join_param":
        expert = item.get("expert")
        if expert not in known["experts"]:
            raise ValueError(f"join_params专家不存在: {expert!r}")
        key = item.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError("key须为非空字符串")
        value = item.get("value")
        if isinstance(value, bool) or not isinstance(
                value, (str, int, float, list)):
            raise ValueError(
                f"join参数值须为标量或列表, got {type(value).__name__}")
        return {"expert": expert, "key": key, "value": value}
    if op == "add_vocabulary_words":
        vocab = item.get("vocab")
        if vocab not in known["vocabs"]:
            raise ValueError(f"词表名不存在于基线pack: {vocab!r}")
        words = item.get("words")
        if (not isinstance(words, list) or not words
                or not all(isinstance(w, str) and w for w in words)):
            raise ValueError("words须为非空字符串列表")
        return {"vocab": vocab, "words": list(words)}
    if op == "set_threshold":
        key = item.get("key")
        if key not in known["thresholds"]:
            raise ValueError(f"阈值名不存在于基线pack: {key!r}")
        value = item.get("value")
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not 0.0 <= float(value) <= 1.0):
            raise ValueError(f"阈值{key!r}须为[0,1]内的数")
        return {"key": key, "value": float(value)}
    raise ValueError(f"未知操作: {op!r}")  # pragma: no cover


def _validated_canon(item: dict[str, Any],
                     known: dict[str, set[str]]) -> dict[str, Any]:
    kind = item.get("kind")
    if kind not in known["kinds"] or kind == "generic_table":
        raise ValueError(f"表型非法: {kind!r}")
    entries = item.get("entries")
    if (not isinstance(entries, dict) or not entries
            or not all(isinstance(k, str) and k and isinstance(v, str) and v
                       for k, v in entries.items())):
        raise ValueError("entries须为非空字符串映射")
    return {"kind": kind, "entries": dict(entries)}


def pack_known_names(pack_raw: dict[str, Any]) -> dict[str, set[str]]:
    """当前基线pack的合法名字集(op白名单校验的依据)."""
    return {
        "templates": set(pack_raw.get("extraction_templates", {})),
        "vocabs": set(pack_raw.get("term_vocabularies", {})),
        "thresholds": set(pack_raw.get("thresholds", {})),
        "kinds": set(pack_raw.get("table_schemas", {})),
        "experts": set(pack_raw.get("join_params", {})),
    }


def merge_changes(changes: Sequence[RuleChange]) -> list[RuleChange]:
    """合并重复变更: canon/词表同落点并集; 其余同落点候选全部保留.

    v1教训: 同落点replace冲突时保留首个会丢弃关键修复(教师对enum_device
    提出两个互补修复, 弃用其一导致双输)。v2把同落点冲突候选全部交给
    贪心验证回路逐个试——效果差的会被闸门拒绝或被逆向剪枝清除。
    精确重复(op+params相同)仍去重(保留首个, 合并来源失败例)。
    """
    merged: list[RuleChange] = []
    union_index: dict[str, int] = {}
    exact_keys: set[tuple[str, str]] = set()
    for change in changes:
        exact = (change.op, json.dumps(change.params, ensure_ascii=False,
                                       sort_keys=True))
        if exact in exact_keys:
            index = next(i for i, c in enumerate(merged)
                         if (c.op, json.dumps(c.params, ensure_ascii=False,
                                              sort_keys=True)) == exact)
            merged[index] = RuleChange(
                op=change.op, params=change.params,
                reason=merged[index].reason,
                source_failures=tuple(dict.fromkeys(
                    merged[index].source_failures
                    + change.source_failures)))
            continue
        exact_keys.add(exact)
        if change.op in ("add_canon_map", "add_vocabulary_words"):
            target = change.target_path()
            if target in union_index:
                index = union_index[target]
                existing = merged[index]
                params = dict(existing.params)
                if change.op == "add_canon_map":
                    entries = dict(params["entries"])
                    entries.update(change.params["entries"])
                    params["entries"] = entries
                else:
                    words = list(dict.fromkeys(
                        list(params["words"]) + list(change.params["words"])))
                    params["words"] = words
                merged[index] = RuleChange(
                    op=existing.op, params=params,
                    reason=existing.reason,
                    source_failures=tuple(dict.fromkeys(
                        existing.source_failures
                        + change.source_failures)))
                continue
            union_index[target] = len(merged)
        merged.append(change)
    return merged


# ═══════════════════════════════════════════════════════════════
# 2. pack构建与符号验证
# ═══════════════════════════════════════════════════════════════


def build_pack_raw(base_raw: dict[str, Any], changes: Sequence[RuleChange],
                   pack_id: str, description: str,
                   provenance: dict[str, Any]) -> dict[str, Any]:
    """基线pack深拷贝 + 顺序应用变更 → 新pack dict(未校验)."""
    draft = copy.deepcopy(base_raw)
    draft["pack_id"] = pack_id
    draft["description"] = description
    applied: list[dict[str, Any]] = []
    for change in changes:
        logs = change.apply(draft)
        applied.append({
            "op": change.op, "target": change.target_path(),
            "params": dict(change.params), "reason": change.reason,
            "source_failures": list(change.source_failures),
            "apply_logs": logs})
    draft["_eiter"] = {"provenance": provenance, "changes": applied}
    return draft


def write_and_validate_pack(pack_raw: dict[str, Any],
                            path: Path) -> dict[str, Any]:
    """写盘 + load_rulepack全schema校验(Eiter回路的符号验证闸门).

    校验失败抛ValueError/FileNotFoundError——教师规则必须先通过引擎
    schema契约(正则编译/结构/阈值范围)才进评测。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack_raw, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    from algorithms.consistency.rulepack import load_rulepack

    pack = load_rulepack(str(path))
    return {"pack_id": pack.pack_id,
            "n_templates": len(pack.extraction_templates),
            "n_vocabs": len(pack.term_vocabularies),
            "n_thresholds": len(pack.thresholds)}


# ═══════════════════════════════════════════════════════════════
# 3. 评测子进程(每pack一全新进程: 派生配置缓存零污染)
# ═══════════════════════════════════════════════════════════════


def run_eval_worker(pack_path: Path, evalset: Path,
                    labels_mode: str) -> dict[str, Any]:
    """全新子进程评测一个pack(契约见_worker_main).

    返回 {metrics, verdicts, wrong, failure_claims, expert_failures};
    子进程失败/输出损坏抛RuntimeError(不静默)。
    """
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker",
           str(pack_path), str(evalset), labels_mode]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", timeout=1800, cwd=str(BASE))
    if proc.returncode != 0:
        raise RuntimeError(
            f"评测子进程失败({pack_path.name} x {evalset.name}): "
            f"rc={proc.returncode}: {proc.stderr[-500:]}")
    if _EVAL_SENTINEL not in proc.stdout:
        raise RuntimeError(
            f"评测子进程输出缺哨兵({pack_path.name}): "
            f"{proc.stdout[-300:]}")
    try:
        return json.loads(proc.stdout.split(_EVAL_SENTINEL, 1)[1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"评测子进程输出损坏({pack_path.name}): {exc}") from exc


def _worker_main(pack_path: str, evalset: str, labels_mode: str) -> None:
    """子进程入口: 干净加载pack → deterministic评测 → stdout输出JSON.

    失败实例除claim归因外还附**引擎实际视图trace**(线性化语句+enum/id
    专家的真实提取输出, 见_engine_trace)——教师归纳的反馈通道: 规则模板
    运行在这些文本上, trace是模板行为的ground truth(v1教训: 只给原始
    证据时教师会对线性化格式产生空白幻觉)。
    """
    from algorithms.consistency.eval_lib import (
        build_qa_input,
        classification_metrics,
        load_silver_labels,
        read_jsonl,
    )
    from algorithms.consistency.qa_module import QAConsistencyModule
    from algorithms.consistency.rulepack import (
        load_rulepack,
        set_default_rulepack,
    )

    rows = read_jsonl(Path(evalset))
    if labels_mode == "sound":
        labels = {str(row["instance_id"]): str(row["sound_label"])
                  for row in rows}
    elif labels_mode == "silver":
        labels = load_silver_labels()
    else:
        raise ValueError(f"labels_mode非法: {labels_mode!r}")
    set_default_rulepack(load_rulepack(pack_path))
    module = QAConsistencyModule(use_experts=True)
    y_true: list[str] = []
    y_pred: list[str] = []
    verdicts: dict[str, str] = {}
    wrong: list[str] = []
    failure_claims: dict[str, dict[str, Any]] = {}
    expert_failures: Counter[str] = Counter()
    for row in rows:
        iid = str(row["instance_id"])
        result = module.verify(build_qa_input(row))
        gold = labels[iid]
        verdicts[iid] = result.verdict
        y_true.append(gold)
        y_pred.append(result.verdict)
        for diagnostic in result.diagnostics:
            if diagnostic.startswith("expert_") and "failed" in diagnostic:
                expert_failures[diagnostic] += 1
        if result.verdict != gold:
            wrong.append(iid)
            failure_claims[iid] = {
                "claims": [{
                    "claim_text": claim.claim_text,
                    "verdict": claim.verdict,
                    "method": claim.method,
                    "rationale": claim.rationale[:120],
                } for claim in result.claim_results],
                "trace": _engine_trace(row),
            }
    sys.stdout.write(_EVAL_SENTINEL + json.dumps({
        "metrics": classification_metrics(y_true, y_pred),
        "verdicts": verdicts,
        "wrong": wrong,
        "failure_claims": failure_claims,
        "expert_failures": dict(expert_failures),
    }, ensure_ascii=False))
    sys.stdout.flush()


def _engine_trace(row: dict[str, Any]) -> dict[str, Any]:
    """失败实例的引擎实际视图: 规则模板真正消费的文本与提取输出.

    全部确定性(与推理路径同一函数); 提取异常时如实记录错误字符串
    (不静默)——trace本身就是反馈信号。
    """
    import re as _re

    from algorithms.consistency.evidence_statements import linearize_context
    from algorithms.consistency.eval_lib import build_qa_input
    from algorithms.consistency.enum_join_expert import (
        build_domain_registry,
        extract_enum_assertions,
    )
    from algorithms.consistency.id_join_expert import (
        build_id_registry,
        extract_id_claims,
    )

    request = build_qa_input(row)
    trace: dict[str, Any] = {}
    compact = _re.compile(r"\s+")
    statements = linearize_context(request.evidence)
    trace["statements"] = [
        f"[{s.statement_id}] {compact.sub('', s.text)[:120]}"
        for s in statements[:14]]
    trace["n_statements"] = len(statements)
    try:
        registry = build_domain_registry(statements)
        trace["enum_registry"] = [
            f"{e.subject}/{e.source_field}={{{'、'.join(e.members)}}}"
            for e in registry[:10]]
        assertions = extract_enum_assertions(request.answer,
                                             request.question)
        trace["enum_assertions"] = [
            f"subjects={list(a.subjects)}, members={list(a.raw_members)},"
            f" kind={a.kind}, closed={a.closed}"
            for a in assertions[:5]]
    except Exception as exc:  # trace失败如实记录, 不吞
        trace["enum_error"] = f"{type(exc).__name__}: {exc}"
    try:
        id_registry = build_id_registry(statements)
        trace["id_registry"] = [
            f"{identifier} -> {[r.subject for r in regs]}"
            for identifier, regs in list(id_registry.items())[:12]]
        claims = extract_id_claims(request.answer)
        trace["id_claims"] = [
            f"(id={c.identifier}, subject={c.subject})" for c in claims[:6]]
    except Exception as exc:  # trace失败如实记录, 不吞
        trace["id_error"] = f"{type(exc).__name__}: {exc}"
    return trace


# ═══════════════════════════════════════════════════════════════
# 4. 失败例采集(教师输入)
# ═══════════════════════════════════════════════════════════════


def harvest_failures(rows: Sequence[dict[str, Any]],
                     outcome: dict[str, Any]) -> list[dict[str, Any]]:
    """评测outcome + 原始行 → 教师可读的失败例(claim归因+引擎trace)."""
    failures: list[dict[str, Any]] = []
    claims_by_iid = outcome.get("failure_claims", {})
    for row in rows:
        iid = str(row["instance_id"])
        if iid not in outcome["wrong"]:
            continue
        evidence = []
        for ev in row.get("evidence", [])[:6]:
            text = str(ev.get("text", ""))
            evidence.append({
                "evidence_id": str(ev.get("evidence_id", "")),
                "source_type": str(ev.get("source_type", "")),
                "section": str((ev.get("source_ref") or {}).get(
                    "section", "")),
                "text": text[:1000] + ("…[截断]" if len(text) > 1000 else ""),
            })
        entry = claims_by_iid.get(iid, {})
        claims = entry.get("claims", []) if isinstance(entry, dict) else entry
        trace = (entry.get("trace", {})
                 if isinstance(entry, dict) else None) or {}
        failures.append({
            "instance_id": iid,
            "family": str(row.get("family", "")),
            "operator": str(row.get("operator", "")),
            "gold": str(row["sound_label"]),
            "predicted": str(outcome["verdicts"][iid]),
            "label_proof": str(row.get("label_proof", "")),
            "question": str(row["question"]),
            "answer": str(row["answer"]),
            "misfiring_claims": claims,
            "engine_trace": trace,
            "evidence": evidence,
        })
    failures.sort(key=lambda f: (f["family"], f["instance_id"]))
    return failures


def batch_failures(failures: Sequence[dict[str, Any]],
                   batch_size: int = BATCH_SIZE,
                   ) -> list[list[dict[str, Any]]]:
    """按family聚簇分批(批内同族 → 教师可归纳同族规则)."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for failure in failures:
        groups.setdefault(failure["family"], []).append(failure)
    batches: list[list[dict[str, Any]]] = []
    for family in sorted(groups):
        group = groups[family]
        for start in range(0, len(group), batch_size):
            batches.append(group[start:start + batch_size])
    return batches


# ═══════════════════════════════════════════════════════════════
# 5. 教师接口(GLM-5.3, llm_json_teacher cache=True, 全缓存可复现)
# ═══════════════════════════════════════════════════════════════


def build_system_prompt() -> str:
    return """你是GJB 438C军用软件需求规格说明(SRS)一致性校验系统的L1规则包工程师。

L1层是纯确定性符号规则引擎, 由JSON规则包(rulepack)驱动。配置面与引擎专家的对应:
- enum_join_registry(枚举值域join, 检测"answer的成员集合 vs 证据注册表封闭集合"): extraction_templates.enum_*(enum_sentence/enum_device/enum_field_value/enum_question_subject/enum_member_valid/enum_member_split/enum_member_split_device/enum_subject_role_suffix/enum_generic_subject等; 同时用于证据侧注册表构建与answer侧声明提取), term_vocabularies.enum_*(enum_terminal_bases=终端形态值域如桌面/平板/手持, enum_phase_bases=阶段值域, enum_generic_subjects=泛指主体黑名单, enum_subject_garbage_infixes等), join_params.enum_join
- id_join_registry(ID注册表join, 检测"answer声称的(主体,ID)绑定 vs 证据ID注册表"): extraction_templates.id_*(id_pattern/id_binding/id_section_title/id_role_tail/id_bracket_subject等), term_vocabularies.id_subject_stopwords, join_params.id_join(id_window=ID前主体窗口字符数, id_family_prefixes=参与join的ID族前缀, family_segments)
- e1_template_match(E1异常流模板): extraction_templates.e1_*, term_vocabularies.e1_*, join_params.e1
- sequence_alignment(用例步骤序列对齐): extraction_templates.seq_*, term_vocabularies.seq_*, join_params.sequence
- trace_bidirectional_join(正/逆向追溯映射): extraction_templates.trace_*, table_schemas.trace_table(canon_map/direction_first_column_prefix/direction_markers), join_params.trace
- gjb_presence_check/gjb_rule_engine: term_vocabularies.gjb_*(标准级, 勿动)
- numeric_z3_expert(数值区间Z3): join_params.numeric_z3(cn_unit_aliases中文单位别名/extra_unit_factors), thresholds
- coverage_join(合格性覆盖): join_params.coverage, term_vocabularies.coverage_*
- 表格分类(证据线性化路由): table_schemas.<表型>.signatures + canon_map + key_columns

配置语义精确说明(每个词表/模板的真实消费位置——归纳必须落在正确的旋钮上):
- enum_terminal_bases: 终端形态**值域**。answer侧设备枚举成员与证据侧方式名称成员的**分类与归一都以成员∈值域为判定**(_classify_members: 全部成员在值域内或与值域词编辑距离1→kind=terminal; 任一成员不在→kind=functional, kind不匹配则join不发生)。成员带"设备/终端/版"等尾缀时引擎只自动剥"版"尾, 其他尾缀形态不会被剥离——不在值域的尾缀形态成员会改变kind或被判为多余成员。
- enum_phase_bases: 阶段值域(分类与归一同上)。
- enum_dev_tail_strip: 仅作用于answer侧设备枚举的**主体候选窗口**尾缀剥离(_strip_tail), **不作用于成员**。
- enum_subject_role_suffix: 主体候选的角色尾缀剥离正则(作用于subject, 不作用于成员)。
- id_subject_stopwords: ID前主体窗口提取(_claimed_subject)的停用词表——连接词(如"通过接口")被并入主体时加此表使主体归一。
- enum_member_split/enum_member_valid: answer侧枚举成员的切分与合法性。
- enum_field_value: **证据侧**字段语句提取("X的<字段>：值", 只用于build_domain_registry), 不用于answer侧声明提取。
- enum_sentence/enum_device: **answer侧**枚举声明提取(enum_sentence=显式主体"X包括A、B、C"; enum_device="在A、B、C[设备]上运行/使用"形态, 需"在…上"锚)。
- id_pattern/id_binding/id_section_title: ID字面/绑定/节标题提取; id_binding与build_id_registry运行于**空白折叠后**的语句文本(不存在空白形态)。
- trace_taskbook_section: 任务书章节token提取(^锚只匹配行首)。
- join_params.id_join.id_window: ID前取主体的窗口字符数; id_family_prefixes: 参与join的ID族前缀(留空=全族)。

当前基线规则包srs_gjb_v1按04号文档文法调校, 在06号文档上跨文档失效。你的任务:
分析给出的失败实例(失败QA+引擎实际视图+错判claim归因), 归纳**最小**规则包变更修复它们。

可用变更操作(输出到changes数组, 每项一个op):
1. {"op":"replace_extraction_template","name":"<基线pack已有模板名>","pattern":"<合法Python re正则; 命名组须保留原模板全部命名组>","flags":0或32,"reason":"一句话归纳依据"}
2. {"op":"add_canon_map","kind":"<表型>","entries":{"<原文表头>":"<规范列名>"},"reason":"..."}
3. {"op":"add_table_signature","kind":"<表型>","signature":{"all_headers":[...]|"any_header_groups":[[...]]|"any_header_substring_groups":[[...]]|"caption_contains_any":[...]|"raw_contains_any":[...]|"raw_regex":"..."},"reason":"..."}
4. {"op":"set_id_family_prefixes","prefixes":["<族前缀>"],"reason":"..."}
5. {"op":"set_join_param","expert":"<专家名>","key":"<参数名>","value":<标量或列表>,"reason":"..."}
6. {"op":"add_vocabulary_words","vocab":"<基线pack已有词表名>","words":["<词>"],"reason":"..."}
7. {"op":"set_threshold","key":"<基线pack已有阈值名>","value":<0-1的数>,"reason":"..."}

硬约束:
- 只输出以上7种op; name/vocab/threshold引用基线pack中不存在的名字会被拒绝。
- 不修改gjb段/gjb_rule_library_path/classify_order(标准级知识)。
- 变更将被回归验证: 在04号主评测集上造成任何回退的变更会被丢弃——修改共享模板(如enum_device)时保持04号形态兼容, 优先用增量手段(新增canon/词表词/签名)而非重写。
- **引擎实际视图是ground truth**: 每个失败实例附线性化语句(全部空白已折叠——模板正则运行在无空白文本上, 不要假设任何空白/换行形态)与enum/id专家的实际提取输出(注册表+answer侧声明)。归纳必须解释trace里的真实提取结果: 声明没提取出来→模板没匹配上answer文本; 提取出来但主体/成员形态与注册表不一致→词表/归一化问题; kind/分类不匹配→值域词表问题。
- **引擎输出契约**: enum_join/id_join专家只对"集合冲突/绑定冲突"输出refute; 注册表与声明完全一致时输出空(该claim交回旧通道, 不输出support)。因此gold=support且旧通道无判定能力的失败, 规则层无能为力——在diagnosis如实说明, changes留空, 不要硬凑规则。
- 失败原因超出L1规则层能力时, changes输出空数组, 在diagnosis说明。

只输出一个JSON对象(无其他文本):
{"diagnosis":"<本批失败机理归纳, 2-5句>","changes":[{...}]}"""


def build_user_prompt(batch: Sequence[dict[str, Any]],
                      pack_raw: dict[str, Any],
                      previous_changes: Sequence[RuleChange],
                      round_id: int,
                      pruned_changes: Sequence[RuleChange] = (),
                      ) -> str:
    """组装失败批次prompt(确定性: 固定字段序 + sort_keys的pack JSON)."""
    prompt_pack = {k: v for k, v in pack_raw.items() if k != "_eiter"}
    parts: list[str] = [f"# 第{round_id}轮: 失败实例批次 "
                        f"[{batch[0]['family']}] x{len(batch)}", ""]
    if previous_changes:
        parts.append("## 已接受的上一轮变更(在其基础上修补, 不要重复提出):")
        for change in previous_changes:
            parts.append(f"- {change.target_path()}: {change.reason}")
        parts.append("")
    if pruned_changes:
        parts.append(
            "## 上一轮被验证剪枝的变更(在crossdoc06上零失败修复, 已从"
            "pack中移除——不要重复提出同类方案, 重新诊断):")
        for change in pruned_changes:
            parts.append(f"- {change.target_path()}: {change.reason}")
        parts.append("")
    for failure in batch:
        parts.extend([
            f"## 失败实例 {failure['instance_id']}",
            f"- family/operator: {failure['family']} / "
            f"{failure['operator']}",
            f"- gold标签: {failure['gold']}",
            f"- gold证明(label_proof): {failure['label_proof']}",
            f"- 引擎当前判定: {failure['predicted']}",
            "- 错判claim归因(哪个规则通道判了什么):",
        ])
        for claim in failure["misfiring_claims"]:
            parts.append(
                f"  - [{claim['method']}] {claim['verdict']}: "
                f"{str(claim['claim_text'])[:80]} | "
                f"{str(claim['rationale'])[:110]}")
        parts.append(f"- question: {failure['question']}")
        parts.append(f"- answer: {failure['answer']}")
        trace = failure.get("engine_trace") or {}
        if trace:
            parts.append("- 引擎实际视图(模板真正消费的文本与提取输出):")
            if trace.get("statements"):
                parts.append(f"  - 线性化语句x{trace.get('n_statements')}"
                             "(空白已折叠, 正则运行于无空白文本):")
                for statement in trace["statements"]:
                    parts.append(f"    {statement}")
            for reg in trace.get("enum_registry", []):
                parts.append(f"  - 枚举注册表: {reg}")
            for assertion in trace.get("enum_assertions", []):
                parts.append(f"  - answer枚举声明: {assertion}")
            for reg in trace.get("id_registry", []):
                parts.append(f"  - ID注册表: {reg}")
            for claim in trace.get("id_claims", []):
                parts.append(f"  - answer ID声明: {claim}")
            for key in ("enum_error", "id_error"):
                if trace.get(key):
                    parts.append(f"  - {key}: {trace[key]}")
        parts.append("- 冻结证据(原始块, 截断):")
        for ev in failure["evidence"]:
            parts.append(f"  - {ev['evidence_id']} [{ev['source_type']} "
                         f"{ev['section']}]: {ev['text'][:600]}")
        parts.append("")
    parts.append("## 当前规则包(JSON, 变更落点须引用其中真实存在的名字):")
    parts.append(json.dumps(prompt_pack, ensure_ascii=False, sort_keys=True))
    parts.append("")
    parts.append("请基于引擎实际视图归纳修复本批失败的最小变更集, "
                 "按系统提示的JSON格式输出。")
    return "\n".join(parts)


def call_teacher(system: str, user: str) -> tuple[dict[str, Any], dict]:
    """教师调用: llm_json_teacher(cache=True) + 解析失败严格重试.

    GLM-5.3是thinking模型: 与distill_teacher_labels/d3_teacher_labels的
    既定契约一致, 走response_contract+reasoning_effort=low(否则推理token
    耗尽max_tokens预算, content只剩残片——试点实测教训)。重试prompt
    追加严格后缀(=新缓存键); 全部失败抛RuntimeError。
    返回(payload, stats): stats含调用数/缓存命中数/真实API数。
    """
    from llm_teacher import llm_json_teacher

    stats = {"invocations": 0, "cache_hits": 0, "api_calls": 0}
    suffixes = ["",
                "\n\n注意: 只输出一个合法JSON对象, 不要markdown围栏, "
                "不要任何解释文本。",
                "\n\n最后尝试: 输出{\"diagnosis\":\"...\",\"changes\":[]}形态"
                "的合法JSON, 不确定就用空changes数组。"]
    last_error = ""
    for attempt in range(TEACHER_MAX_ATTEMPTS):
        prompt = user + suffixes[attempt]
        stats["invocations"] += 1
        payload, _model, cache_hit = llm_json_teacher(
            prompt, system, max_tokens=8000, temperature=0.1,
            extra_payload={"response_contract": "json_final_content_v2",
                           "reasoning_effort": "low"},
            cache=True)
        if cache_hit:
            stats["cache_hits"] += 1
        else:
            stats["api_calls"] += 1
        if isinstance(payload, dict) and "changes" in payload:
            return payload, stats
        last_error = (f"attempt{attempt}: payload非含changes的对象: "
                      f"{str(payload)[:150]}")
    raise RuntimeError(f"教师输出解析失败({TEACHER_MAX_ATTEMPTS}次): "
                       f"{last_error}")


# ═══════════════════════════════════════════════════════════════
# 6. 回归闸门(C1IPR"修订不回退")与贪心接受/逆向剪枝
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GateBaseline:
    """闸门基线: 91QA主评测(零回退)与crossdoc06(不新增错例)的generic态."""

    qa91: dict[str, Any]
    crossdoc: dict[str, Any]


def gate_check(crossdoc_outcome: dict[str, Any] | None,
               qa91_outcome: dict[str, Any] | None,
               baseline: GateBaseline) -> tuple[bool, str]:
    """CLIPR式零回退判定(两评测集, 91QA含聚合指标不降).

    crossdoc06: 不得新增错例(相对generic基线) + 专家异常否决;
    91QA: 逐实例零回退 + macro_f1/accuracy不低于基线 + 专家异常否决。
    """
    if crossdoc_outcome is not None:
        new_wrong = sorted(set(crossdoc_outcome["wrong"])
                           - set(baseline.crossdoc["wrong"]))
        if new_wrong:
            return False, f"crossdoc06新增错例{new_wrong[:5]}"
        if crossdoc_outcome.get("expert_failures"):
            return False, (f"专家运行时异常: "
                           f"{crossdoc_outcome['expert_failures']}")
    if qa91_outcome is not None:
        new_wrong = sorted(set(qa91_outcome["wrong"])
                           - set(baseline.qa91["wrong"]))
        if new_wrong:
            return False, f"91QA新增错例{new_wrong[:5]}"
        if qa91_outcome.get("expert_failures"):
            return False, (f"专家运行时异常: "
                           f"{qa91_outcome['expert_failures']}")
        base_metrics = baseline.qa91["metrics"]
        metrics = qa91_outcome["metrics"]
        if (metrics["macro_f1"] < base_metrics["macro_f1"]
                or metrics["accuracy"] < base_metrics["accuracy"]):
            return False, (f"91QA聚合回退: macro_f1 {metrics['macro_f1']} < "
                           f"{base_metrics['macro_f1']} 或 acc "
                           f"{metrics['accuracy']} < "
                           f"{base_metrics['accuracy']}")
    return True, "ok"


def greedy_accept(
        changes: Sequence[RuleChange],
        base_raw: dict[str, Any],
        trial_prefix: str,
        trial_dir: Path,
        current_wrong_count: int,
        eval_trial: Callable[[Path], tuple[bool, str, dict[str, Any]]],
) -> tuple[list[RuleChange], list[dict[str, Any]], dict[str, Any] | None]:
    """逐变更贪心接受: schema验证 → crossdoc06闸门 → 91QA闸门.

    eval_trial(trial_path) -> (gate_ok, reason, crossdoc_outcome)——由
    调用方注入(内含子进程评测与两闸门; crossdoc闸门先判可省一次子进程)。
    接受条件: 闸门通过且crossdoc06错例数不增(相对当前已接受状态)。
    """
    accepted: list[RuleChange] = []
    rejected: list[dict[str, Any]] = []
    wrong_count = current_wrong_count
    last_outcome: dict[str, Any] | None = None
    for index, change in enumerate(changes, 1):
        trial_path = trial_dir / f"{trial_prefix}_t{index:03d}.json"
        try:
            write_and_validate_pack(
                build_pack_raw(base_raw, list(accepted) + [change],
                               f"{trial_prefix}_t{index}", "greedy trial", {}),
                trial_path)
        except (ValueError, FileNotFoundError) as exc:
            rejected.append({"target": change.target_path(),
                             "reason": str(exc)[:200], "stage": "schema"})
            continue
        ok, reason, outcome = eval_trial(trial_path)
        if not ok:
            rejected.append({"target": change.target_path(),
                             "reason": reason[:200], "stage": "gate"})
            continue
        if len(outcome["wrong"]) > wrong_count:
            rejected.append({"target": change.target_path(),
                             "reason": (f"crossdoc06错例数回退 "
                                        f"{len(outcome['wrong'])}>{wrong_count}"),
                             "stage": "crossdoc06_count"})
            continue
        accepted.append(change)
        wrong_count = len(outcome["wrong"])
        last_outcome = outcome
    return accepted, rejected, last_outcome


def backward_prune(
        accepted: Sequence[RuleChange],
        base_raw: dict[str, Any],
        trial_prefix: str,
        trial_dir: Path,
        wrong_count: int,
        eval_trial: Callable[[Path], tuple[bool, str, dict[str, Any]]],
) -> tuple[list[RuleChange], dict[str, Any]]:
    """逆向剪枝(RIMRULE式最小化): 移除后crossdoc06错例数不增且闸门仍过.

    允许剪到空集(全部变更惰性 → 最小pack=基线, v1的剪枝不能到零导致
    无效变更残留——修正)。返回(保留变更列表, 最终crossdoc06 outcome)。
    """
    kept = list(accepted)
    counter = 0
    for change in reversed(list(accepted)):
        candidate = [c for c in kept if c is not change]
        counter += 1
        trial_path = trial_dir / f"{trial_prefix}_p{counter:03d}.json"
        try:
            write_and_validate_pack(
                build_pack_raw(base_raw, candidate,
                               f"{trial_prefix}_p{counter}", "prune trial",
                               {}), trial_path)
        except (ValueError, FileNotFoundError):
            continue
        ok, _reason, pruned_outcome = eval_trial(trial_path)
        if ok and len(pruned_outcome["wrong"]) <= wrong_count:
            kept = candidate
    final_path = trial_dir / f"{trial_prefix}_pfinal.json"
    write_and_validate_pack(
        build_pack_raw(base_raw, kept, f"{trial_prefix}_pf",
                       "prune final", {}), final_path)
    ok, reason, outcome = eval_trial(final_path)
    if not ok:  # pragma: no cover - 子集闸门全过时不可达
        raise RuntimeError(f"逆向剪枝最终集闸门失败(不应发生): {reason}")
    return kept, outcome


# ═══════════════════════════════════════════════════════════════
# 7. 主流程
# ═══════════════════════════════════════════════════════════════


def run_baseline() -> dict[str, dict[str, dict[str, Any]]]:
    """基线对照: generic与manual pack在两评测集上的子进程评测."""
    result: dict[str, dict[str, dict[str, Any]]] = {
        "crossdoc06": {}, "qa91": {}}
    for name, path in [("generic_srs_gjb_v1", GENERIC_PACK),
                       ("manual_doc06_v1", MANUAL_PACK)]:
        result["crossdoc06"][name] = run_eval_worker(
            path, CROSSDOC06, "sound")
        result["qa91"][name] = run_eval_worker(path, QA91, "silver")
    return result


def pack_diff_targets(base_raw: dict[str, Any],
                      other_raw: dict[str, Any]) -> list[str]:
    """两pack的结构差异落点(供人工vs教师规则重叠度分析)."""
    skip = {"_eiter", "_onboarding", "description", "pack_id"}
    out: list[str] = []

    def walk(a: Any, b: Any, path: str) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                if key in skip:
                    continue
                if key not in a:
                    out.append(f"{path}.{key}+")
                elif key in b:
                    walk(a[key], b[key], f"{path}.{key}")
        elif a != b:
            out.append(path)

    walk(base_raw, other_raw, "$")
    return out


def run_experiment(rounds: int = 2, skip_teacher: bool = False,
                   final_write: bool = True) -> dict[str, Any]:
    """完整Eiter回路: 基线→失败例→教师归纳→验证→修补→剪枝→报告."""
    t_start = time.time()
    generic_raw = json.loads(GENERIC_PACK.read_text(encoding="utf-8"))
    cross_rows = [json.loads(line) for line in
                  CROSSDOC06.read_text(encoding="utf-8").splitlines()
                  if line.strip()]

    run = open_run("eiter_rule_induction", {
        "rounds": rounds, "skip_teacher": skip_teacher,
        "evalsets": {"crossdoc06": str(CROSSDOC06.relative_to(BASE)),
                     "qa91": str(QA91.relative_to(BASE))},
        "base_pack": str(GENERIC_PACK.relative_to(BASE)),
        "manual_pack": str(MANUAL_PACK.relative_to(BASE)),
        "teacher": "llm_json_teacher(glm-5.3, cache=True)",
        "eval_config": "QAConsistencyModule(use_experts=True) deterministic",
        "gate": "CLIPR no-regression: qa91 instance+aggregate, "
                "crossdoc06 no-new-wrong + count-monotone, "
                "expert-failure veto",
    })
    trial_dir = run.path / "packs"
    trial_dir.mkdir(exist_ok=True)
    run.log(event="start", rounds=rounds)

    print("== 基线评测(全新子进程) ==")
    baselines = run_baseline()
    for name in ("generic_srs_gjb_v1", "manual_doc06_v1"):
        cd = baselines["crossdoc06"][name]
        qa = baselines["qa91"][name]
        print(f"  {name}: crossdoc06 macro_f1="
              f"{cd['metrics']['macro_f1']} acc={cd['metrics']['accuracy']}"
              f" wrong={len(cd['wrong'])} | qa91 macro_f1="
              f"{qa['metrics']['macro_f1']} acc={qa['metrics']['accuracy']}")
    run.log(event="baseline_done",
            crossdoc06={n: b["metrics"]["macro_f1"]
                        for n, b in baselines["crossdoc06"].items()},
            qa91={n: b["metrics"]["macro_f1"]
                  for n, b in baselines["qa91"].items()})

    gate_baseline = GateBaseline(
        qa91=baselines["qa91"]["generic_srs_gjb_v1"],
        crossdoc=baselines["crossdoc06"]["generic_srs_gjb_v1"])
    teacher_total = {"invocations": 0, "cache_hits": 0, "api_calls": 0}
    eval_count = {"subprocess_evals": 4, "crossdoc_only_evals": 0}

    def eval_trial(trial_path: Path) -> tuple[bool, str, dict[str, Any]]:
        """评测一个试验pack: crossdoc06先判(省子进程), 91QA零回退后判."""
        crossdoc = run_eval_worker(trial_path, CROSSDOC06, "sound")
        eval_count["subprocess_evals"] += 1
        ok, reason = gate_check(crossdoc, None, gate_baseline)
        if not ok:
            return ok, reason, crossdoc
        qa91 = run_eval_worker(trial_path, QA91, "silver")
        eval_count["subprocess_evals"] += 1
        ok, reason = gate_check(crossdoc, qa91, gate_baseline)
        return ok, reason, crossdoc

    rounds_result: list[dict[str, Any]] = []
    accepted: list[RuleChange] = []
    pruned_changes: list[RuleChange] = []
    current_raw = generic_raw
    current_outcome = baselines["crossdoc06"]["generic_srs_gjb_v1"]

    for round_id in range(1, rounds + 1):
        print(f"\n== 第{round_id}轮: 失败例 → 教师归纳 → 验证回路 ==")
        failures = harvest_failures(cross_rows, current_outcome)
        print(f"  失败例: {len(failures)}条 "
              f"{dict(Counter(f['family'] for f in failures))}")
        if not failures:
            print("  无失败例, 回路收敛")
            break
        if skip_teacher:
            print("  --skip-teacher: 停止(不调用教师)")
            break

        batches = batch_failures(failures)
        round_changes: list[RuleChange] = []
        teacher_calls: list[dict[str, Any]] = []
        parse_errors: list[dict[str, Any]] = []
        known = pack_known_names(current_raw)
        for batch in batches:
            user = build_user_prompt(batch, current_raw, accepted, round_id,
                                     pruned_changes)
            payload, stats = call_teacher(build_system_prompt(), user)
            for key in teacher_total:
                teacher_total[key] += stats[key]
            try:
                batch_changes, batch_errors = parse_teacher_changes(
                    payload, known,
                    [str(f["instance_id"]) for f in batch])
            except ValueError as exc:
                parse_errors.append({
                    "family": str(batch[0]["family"]),
                    "error": str(exc)[:200],
                    "diagnosis": str(payload.get("diagnosis", ""))[:300]})
                print(f"  教师[{batch[0]['family']}]: 输出结构损坏: "
                      f"{str(exc)[:80]}")
                continue
            if batch_errors:
                parse_errors.append({
                    "family": str(batch[0]["family"]),
                    "item_errors": batch_errors})
            round_changes.extend(batch_changes)
            teacher_calls.append({
                "family": str(batch[0]["family"]),
                "n_failures": len(batch),
                "diagnosis": str(payload.get("diagnosis", "")),
                "n_changes": len(batch_changes),
                "n_invalid": len(batch_errors),
                "changes": [c.to_dict() for c in batch_changes],
                "llm": stats})
            print(f"  教师[{batch[0]['family']} x{len(batch)}]: "
                  f"{len(batch_changes)}条变更"
                  + (f"(弃{len(batch_errors)}条非法)" if batch_errors
                     else "")
                  + f", cache {stats['cache_hits']}/{stats['invocations']}")

        merged = merge_changes(round_changes)
        merged.sort(key=lambda c: (-len(c.source_failures),
                                   c.target_path()))
        print(f"  归纳变更(合并去重后): {len(merged)}条")

        accepted_round, rejected, outcome = greedy_accept(
            merged, current_raw, f"r{round_id}", trial_dir,
            len(current_outcome["wrong"]), eval_trial)
        for entry in rejected:
            print(f"  拒绝[{entry['stage']}]: {entry['target']}: "
                  f"{entry['reason'][:70]}")
        if accepted_round:
            kept, outcome = backward_prune(
                accepted_round, current_raw, f"r{round_id}", trial_dir,
                len(outcome["wrong"]), eval_trial)
            dropped = len(accepted_round) - len(kept)
            if dropped:
                print(f"  逆向剪枝: {len(accepted_round)} -> {len(kept)}"
                      f" (剪{dropped}条无效变更)")
                pruned_changes = pruned_changes + [
                    c for c in accepted_round if c not in kept]
            accepted = accepted + kept
            current_outcome = outcome if outcome else current_outcome
            current_raw = build_pack_raw(
                generic_raw, accepted, f"doc06_eiter_r{round_id}",
                (f"06号Eiter回路第{round_id}轮中间pack: 基"
                 f"{generic_raw.get('pack_id')}, 教师归纳+回归验证累计"
                 f"接受{len(accepted)}条变更"),
                {"round": round_id})
            write_and_validate_pack(
                current_raw, trial_dir / f"round{round_id}.json")
            metrics = current_outcome["metrics"]
            print(f"  第{round_id}轮pack: crossdoc06 macro_f1="
                  f"{metrics['macro_f1']} acc={metrics['accuracy']} "
                  f"wrong={len(current_outcome['wrong'])}")
        rounds_result.append({
            "round": round_id,
            "n_failures": len(failures),
            "failure_families": dict(
                Counter(f["family"] for f in failures)),
            "teacher_calls": teacher_calls,
            "teacher_parse_errors": parse_errors,
            "n_proposed_merged": len(merged),
            "accepted": [c.to_dict() for c in (accepted_round or [])],
            "pruned": (len(accepted_round) - len(kept)
                       if accepted_round else 0),
            "rejected": rejected,
            "crossdoc06_after": current_outcome["metrics"],
        })
        if not accepted_round:
            print("  本轮无接受变更, 回路终止")
            break

    # ── 最终pack与终评 ────────────────────────────────────────
    final: dict[str, Any] = {"n_changes": 0}
    if accepted:
        final_raw = build_pack_raw(
            generic_raw, accepted, "doc06_eiter_v1",
            (f"06号运行支撑服务SRS规则包(Eiter回路归纳): 基"
             f"{generic_raw.get('pack_id')}; 教师GLM-5.3从crossdoc06失败例"
             f"归纳{len(accepted)}条变更, 经load_rulepack符号schema验证"
             f"+91QA零回退闸门+crossdoc06零新增错例闸门+逆向剪枝; 归纳"
             f"与验证全程见_eiter段与run目录"),
            {"rounds": [r["round"] for r in rounds_result],
             "teacher": "glm-5.3 via llm_json_teacher cache=True",
             "gate": "CLIPR no-regression",
             "date": time.strftime("%Y-%m-%d")})
        final_path = trial_dir / "doc06_eiter_v1.json"
        write_and_validate_pack(final_raw, final_path)
        crossdoc_final = run_eval_worker(final_path, CROSSDOC06, "sound")
        qa91_final = run_eval_worker(final_path, QA91, "silver")
        eval_count["subprocess_evals"] += 2
        ok, reason = gate_check(crossdoc_final, qa91_final, gate_baseline)
        if not ok:
            raise RuntimeError(f"最终pack闸门失败(不应发生): {reason}")
        if final_write:
            EITER_PACK.write_text(
                json.dumps(final_raw, ensure_ascii=False, indent=1),
                encoding="utf-8")
        final = {
            "pack_path": str(final_path),
            "written_to": (str(EITER_PACK.relative_to(BASE))
                           if final_write else "(not written)"),
            "n_changes": len(accepted),
            "changes": [c.to_dict() for c in accepted],
            "gate_final": reason,
            "crossdoc06": crossdoc_final,
            "qa91": qa91_final,
        }
        cd = crossdoc_final["metrics"]
        qa = qa91_final["metrics"]
        print(f"\n== 最终pack doc06_eiter_v1 ({len(accepted)}条变更) ==")
        print(f"  crossdoc06: macro_f1={cd['macro_f1']} "
              f"acc={cd['accuracy']} wrong={len(crossdoc_final['wrong'])}")
        print(f"  qa91(回归): macro_f1={qa['macro_f1']} "
              f"acc={qa['accuracy']} wrong={len(qa91_final['wrong'])}")
    else:
        print("\n== 教师零接受变更(负面结果, 如实报告) ==")

    manual_raw = json.loads(MANUAL_PACK.read_text(encoding="utf-8"))
    manual_targets = pack_diff_targets(generic_raw, manual_raw)
    teacher_targets = sorted({c.target_path() for c in accepted})

    result = {
        "benchmark": "eiter_rule_induction_p3",
        "baselines": {
            name: {"crossdoc06": _slim(baselines["crossdoc06"][name]),
                   "qa91": _slim(baselines["qa91"][name])}
            for name in baselines["crossdoc06"]
        },
        "rounds": rounds_result,
        "final": final,
        "rule_quality": {
            "manual_diff_targets": manual_targets,
            "teacher_change_targets": teacher_targets,
            "overlapping_targets": sorted(set(manual_targets)
                                          & set(teacher_targets)),
            "n_teacher_changes": len(accepted),
            "n_manual_diff_entries": len(manual_targets),
        },
        "cost": {
            "teacher": teacher_total,
            "eval": eval_count,
            "wall_seconds": round(time.time() - t_start, 1),
        },
        "methodology_notes": [
            "每个pack评测都在全新子进程中执行: "
            "numeric_z3_expert._unit_table是@lru_cache(maxsize=1)无pack"
            "身份键, gjb_presence_expert的词表正则缓存同样身份盲——进程内"
            "切换pack会继承首个pack的派生配置(历史eval_crossdoc5_"
            "onboard的in-process切换受此污染), 子进程隔离是唯一可靠口径",
            "人工doc06_v1是M33时代的fork, 缺srs_gjb_v1后续新增的"
            "numeric_z3/coverage/gjb段——standalone子进程口径下"
            "crossdoc06回退(macro_f1低于generic), 历史'无差异'结论部分"
            "是缓存污染假象",
            "deterministic配置(QAConsistencyModule(use_experts=True))是"
            "L1规则包效应的隔离口径; 91QA主评测当前数字0.7212/0.9121",
        ],
    }
    run.save_result(result)
    run.write_text("report.md", render_report(result))
    run.log(event="done", n_changes=len(accepted),
            wall_seconds=result["cost"]["wall_seconds"])
    print(f"\nrun: {run.path}")
    return result


def _slim(outcome: dict[str, Any]) -> dict[str, Any]:
    return {"metrics": outcome["metrics"], "wrong": outcome["wrong"],
            "n": len(outcome["verdicts"])}


# ═══════════════════════════════════════════════════════════════
# 8. 报告渲染
# ═══════════════════════════════════════════════════════════════


def render_report(result: dict[str, Any]) -> str:
    """最终对比报告(markdown): 数字对照+条目质量+成本+负面发现."""
    lines = [
        "# P3 Eiter回路试点报告: 教师归纳rulepack vs 人工doc06_v1", "",
        "> 生成: tools/eiter_rule_induction.py (99号Phase 3 / 97号§3.4)",
        "",
        "## 评测口径", "",
        "- deterministic配置 `QAConsistencyModule(use_experts=True)`",
        "- 每pack评测于**全新子进程**(lru_cache身份盲污染排除, "
        "见负面发现)",
        "- 闸门(CLP式修订不回退): 91QA逐实例零回退+聚合不降; "
        "crossdoc06零新增错例+错例数单调; 专家运行时异常一票否决",
        "",
        "## 主对照表 (crossdoc06 × 91QA回归)", "",
        "| pack | crossdoc06 macro-F1 | acc | wrong | 91QA macro-F1 "
        "| acc | wrong |",
        "|---|---|---|---|---|---|---|",
    ]
    baselines = result.get("baselines", {})
    final = result.get("final") or {}
    rows: list[tuple[str, dict, dict]] = []
    for name, key in [("generic srs_gjb_v1", "generic_srs_gjb_v1"),
                      ("manual doc06_v1", "manual_doc06_v1")]:
        if key in baselines:
            rows.append((name, baselines[key]["crossdoc06"]["metrics"],
                         baselines[key]["qa91"]["metrics"]))
    wrong_counts = {
        "generic srs_gjb_v1": len(
            baselines.get("generic_srs_gjb_v1", {})
            .get("crossdoc06", {}).get("wrong", [])),
        "manual doc06_v1": len(
            baselines.get("manual_doc06_v1", {})
            .get("crossdoc06", {}).get("wrong", [])),
        "teacher doc06_eiter_v1": len(final.get("crossdoc06", {})
                                      .get("wrong", [])),
    }
    if final.get("crossdoc06"):
        rows.append(("teacher doc06_eiter_v1", final["crossdoc06"]["metrics"],
                     final["qa91"]["metrics"]))
    for name, cd, qa in rows:
        lines.append(
            f"| {name} | {cd['macro_f1']} | {cd['accuracy']} | "
            f"{wrong_counts.get(name, '?')} | "
            f"{qa['macro_f1']} | {qa['accuracy']} | "
            f"{wrong_counts.get(name, '?')} |")
    lines.append("")
    rq = result.get("rule_quality", {})
    lines += [
        "## 规则条目质量", "",
        f"- 教师pack变更数: {rq.get('n_teacher_changes', 0)}",
        f"- 人工pack相对generic的diff落点数: "
        f"{rq.get('n_manual_diff_entries', 0)}",
        f"- 落点重叠: {rq.get('overlapping_targets', [])}",
        f"- 教师落点: {rq.get('teacher_change_targets', [])}",
        f"- 人工落点: {rq.get('manual_diff_targets', [])}",
        "",
    ]
    cost = result.get("cost", {})
    teacher = cost.get("teacher", {})
    lines += [
        "## 回路成本", "",
        f"- 教师调用: {teacher.get('invocations', 0)}次 (缓存命中 "
        f"{teacher.get('cache_hits', 0)}, 真实API "
        f"{teacher.get('api_calls', 0)})",
        f"- 评测子进程: {cost.get('eval', {}).get('subprocess_evals', 0)}次",
        f"- 墙钟: {cost.get('wall_seconds', 0)}s",
        "",
        "## 方法学负面发现", "",
    ]
    for note in result.get("methodology_notes", []):
        lines.append(f"- {note}")
    lines.append("")
    for round_entry in result.get("rounds", []):
        lines += [
            f"## 第{round_entry['round']}轮明细", "",
            f"- 失败例: {round_entry['n_failures']} "
            f"({round_entry.get('failure_families', {})})",
            f"- 提案变更(合并后): {round_entry.get('n_proposed_merged', 0)}, "
            f"接受: {len(round_entry.get('accepted', []))}, "
            f"剪枝: {round_entry.get('pruned', 0)}, "
            f"拒绝: {len(round_entry.get('rejected', []))}",
            "",
        ]
        for call in round_entry.get("teacher_calls", []):
            lines.append(f"### 教师批次[{call['family']}] "
                         f"({call['n_failures']}失败例)")
            lines.append(f"- diagnosis: {call['diagnosis']}")
            for change in call.get("changes", []):
                reason = change.get("reason", "")
                params = {k: v for k, v in change.items()
                          if k not in ("reason", "source_failures")}
                lines.append(f"- `{change.get('op')}` {params} — {reason}")
            lines.append(f"- llm: {call.get('llm')}")
            lines.append("")
    if final.get("changes"):
        lines += ["## 教师最终pack变更(原文摘录)", ""]
        for change in final["changes"][:10]:
            params = {k: v for k, v in change.items()
                      if k not in ("reason", "source_failures")}
            lines.append(f"- `{change['op']}` {params}")
            lines.append(f"  - reason: {change['reason']}")
            lines.append(f"  - source_failures: "
                         f"{change.get('source_failures')}")
        lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="run",
                        choices=["run", "baseline"],
                        help="run=完整回路; baseline=仅基线对照表")
    parser.add_argument("--rounds", type=int, default=2,
                        help="教师归纳轮数(默认2: 归纳+修补)")
    parser.add_argument("--skip-teacher", action="store_true",
                        help="跳过教师调用(只跑基线与失败例采集)")
    parser.add_argument("--no-final-write", action="store_true",
                        help="不写config/rulepacks/doc06_eiter_v1.json")
    parser.add_argument("--worker", nargs=3, metavar=("PACK", "EVALSET",
                                                      "LABELS"),
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        _worker_main(*args.worker)
        return
    if args.mode == "baseline":
        for name, cd, qa in _baseline_rows():
            print(f"{name}: crossdoc06 macro_f1={cd['macro_f1']} "
                  f"acc={cd['accuracy']} | qa91 macro_f1={qa['macro_f1']} "
                  f"acc={qa['accuracy']}")
        return
    run_experiment(rounds=args.rounds, skip_teacher=args.skip_teacher,
                   final_write=not args.no_final_write)


def _baseline_rows() -> list[tuple[str, dict, dict]]:
    baselines = run_baseline()
    rows = []
    for name in baselines["crossdoc06"]:
        rows.append((name, baselines["crossdoc06"][name]["metrics"],
                     baselines["qa91"][name]["metrics"]))
    return rows


if __name__ == "__main__":
    main()
