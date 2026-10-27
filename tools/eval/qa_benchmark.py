r"""QA一致性统一评测器 + 首批确定性baseline (B0/B2/B3).

输入契约:
  frozen : QAInput形状JSONL (instance_id/question/answer/context_freeze_id/evidence)
           默认 data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl (91条, 单doc)
  labels : silver标签JSONL (instance_id/final_verdict/claims[].check_items)
           默认 review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl
           ⚠ silver非gold: 数字仅作参考基准, 不能当评测结论引用.

评测指标:
  1) QA级三态macro-F1 (support/refute/not_in_evidence等权, 含per-class P/R/F1)
  2) accuracy + 混淆矩阵 (gold×pred + invalid列)
  3) evidence citation precision (预测引用是否属于该QA冻结evidence)
  4) check_item分层 (silver claims.check_items优先, 回退route_question)
  5) abstain/invalid预测单独计数, 不从任何分母移除

Baseline (全部确定性, 无LLM):
  B0_majority    : train split标签先验 → 多数类
  B2_lexical     : answer↔evidence token/entity/数值重叠, 阈值化映射三态
                   (数值冲突→refute; 高重叠→support; 否则NIE), 阈值在dev上定
  B3_rule_numeric: subject+operator+value数值claim区间比对
                   (区间蕴含→support, 互斥→refute, 否则NIE)
                   数值抽取思路复用自algorithms.consistency.qa_module, 独立重实现,
                   不直接调用该模块.

Split: 按evidence的doc_id分组(同doc不跨split); doc分组数<3时回退
       (doc_id, section)分组(单doc冻结集下doc级不变量平凡成立, 分组仍在doc内).
       固定seed: 组键sorted后shuffle, 可复现.

统一接口: baseline.predict(rows, dev_rows) -> list[Prediction]
  rows     = 待预测行(label/check_items已剥离, 实现不得读取label)
  dev_rows = 带标签的dev split (允许读label, 供阈值/先验调参)
  返回与rows同序对齐; verdict非法或None → invalid单独计数, 不移出分母.

用法: python tools/eval/qa_benchmark.py [--seed N --frozen PATH --labels PATH]
产出: data/gjb_438c/runs/qa_benchmark_<hash>_<ts>/
      (config.json / result.json / metrics_table.md, runs协议不覆盖)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

BASE = Path(__file__).resolve().parents[2]
for _p in (str(BASE / "tools"), str(BASE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from run_utils import open_run  # noqa: E402
from algorithms.consistency.qa_router import route_question  # noqa: E402

DEFAULT_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
DEFAULT_LABELS = (
    BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl"
)
DEFAULT_SEED = 38
VERDICT_CLASSES: tuple[str, ...] = ("support", "refute", "not_in_evidence")


# ═════════════════════════ 数据模型 ═════════════════════════


@dataclass(frozen=True)
class EvidenceView:
    """冻结evidence的轻量视图 (baseline只看到这些字段)."""

    evidence_id: str
    text: str
    doc_id: str
    section: str
    source_type: str = "text"


@dataclass(frozen=True)
class QAExample:
    """一行QA; label/check_items仅供评测侧, 传给baseline前会被剥离."""

    instance_id: str
    question: str
    answer: str
    context_freeze_id: str
    evidence: tuple[EvidenceView, ...]
    label: str | None = None
    check_items: tuple[str, ...] = ()


@dataclass(frozen=True)
class Prediction:
    """一条预测; verdict非法/None → invalid(单独计数, 不移出分母)."""

    instance_id: str
    verdict: str | None
    cited_evidence_ids: tuple[str, ...] = ()
    abstain: bool = False
    detail: str = ""


class Baseline(Protocol):
    """统一baseline接口: predict(rows, dev_rows) → 与rows同序的Prediction."""

    name: str

    def predict(self, rows: list[QAExample], dev_rows: list[QAExample]) -> list[Prediction]: ...


# ═════════════════════════ 装载与标注关联 ═════════════════════════


def load_frozen_rows(path: Path) -> list[QAExample]:
    """读取QAInput形状JSONL → label-free的QAExample列表."""
    rows: list[QAExample] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            evidence = tuple(
                EvidenceView(
                    evidence_id=str(ev["evidence_id"]),
                    text=str(ev.get("text", "")),
                    doc_id=str(ev.get("source_ref", {}).get("doc_id", "")),
                    section=str(ev.get("source_ref", {}).get("section", "")),
                    source_type=str(ev.get("source_type", "text")),
                )
                for ev in rec.get("evidence", [])
            )
            rows.append(QAExample(
                instance_id=str(rec["instance_id"]),
                question=str(rec["question"]),
                answer=str(rec["answer"]),
                context_freeze_id=str(rec.get("context_freeze_id", "")),
                evidence=evidence,
            ))
    ids = [r.instance_id for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"frozen instance_id重复: {path}")
    return rows


def load_silver_labels(path: Path) -> dict[str, dict]:
    """读取silver标签JSONL → {instance_id: 原始record}."""
    labels: dict[str, dict] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            labels[str(rec["instance_id"])] = rec
    return labels


def resolve_check_items(row: QAExample, label_record: dict | None) -> tuple[str, ...]:
    """check_item来源: silver claims.check_items优先 → route_question回退 → <unrouted>."""
    items: list[str] = []
    if label_record:
        for claim in label_record.get("claims") or []:
            items.extend(
                str(item).strip()
                for item in (claim.get("check_items") or [])
                if str(item).strip()
            )
    if not items:
        items = list(route_question(row.question))
    if not items:
        items = ["<unrouted>"]
    return tuple(dict.fromkeys(items))


def build_labeled_examples(
    rows: list[QAExample], labels: dict[str, dict],
) -> tuple[list[QAExample], int]:
    """关联silver标签与check_items; 非法/缺失verdict → label=None并计数."""
    labeled: list[QAExample] = []
    n_unlabeled = 0
    for row in rows:
        record = labels.get(row.instance_id)
        verdict = str(record.get("final_verdict", "")) if record else ""
        if verdict not in VERDICT_CLASSES:
            verdict = ""
            n_unlabeled += 1
        labeled.append(replace(
            row, label=verdict or None, check_items=resolve_check_items(row, record),
        ))
    return labeled, n_unlabeled


# ═════════════════════════ 分组split ═════════════════════════


def _primary_doc(row: QAExample) -> str:
    return row.evidence[0].doc_id if row.evidence else "<no-evidence>"


def _primary_section(row: QAExample) -> str:
    return row.evidence[0].section if row.evidence else "<no-evidence>"


def make_group_splits(
    rows: list[QAExample], seed: int = DEFAULT_SEED,
    train_frac: float = 0.6, dev_frac: float = 0.2,
) -> tuple[dict[str, str], dict]:
    """分组split: doc级优先(同doc不跨split); doc组<3 → (doc,section)级回退.

    返回 (instance_id → train/dev/test, split信息dict).
    确定性: 组键sorted后用random.Random(seed).shuffle.
    """
    if not 0 < train_frac < 1 or not 0 < dev_frac < 1 or train_frac + dev_frac >= 1:
        raise ValueError("train_frac/dev_frac须在(0,1)内且和小于1")
    docs = {_primary_doc(r) for r in rows}
    if len(docs) >= 3:
        mode, key_fn = "doc", _primary_doc
    else:
        mode = "section"

        def key_fn(r: QAExample) -> str:
            return f"{_primary_doc(r)}::{_primary_section(r)}"

        if len({key_fn(r) for r in rows}) < 3:
            raise ValueError("doc与section粒度的分组数均<3, 无法构造无泄漏split")

    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(key_fn(row), []).append(row.instance_id)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)

    n = len(rows)
    train_target = round(train_frac * n)
    dev_target = round((train_frac + dev_frac) * n)
    assignment: dict[str, str] = {}
    split_groups: dict[str, list[str]] = {"train": [], "dev": [], "test": []}
    placed = 0
    phase = "train"
    for key in keys:
        if phase == "train" and placed >= train_target:
            phase = "dev"
        if phase == "dev" and placed >= dev_target:
            phase = "test"
        assignment[key] = phase
        split_groups[phase].append(key)
        placed += len(groups[key])
    for phase in ("test", "dev"):          # 空split修复: 从上一阶段挪最后一组
        if not split_groups[phase]:
            donor = "dev" if phase == "test" and split_groups["dev"] else "train"
            if not split_groups[donor]:
                raise ValueError("分组不足以同时构造非空train/dev/test")
            moved = split_groups[donor].pop()
            split_groups[phase].append(moved)
            assignment[moved] = phase
    for phase, group_keys in split_groups.items():
        if not group_keys:
            raise ValueError(f"split {phase} 为空")

    row_split = {iid: assignment[key]
                 for key, ids in groups.items() for iid in ids}
    return row_split, {
        "mode": mode,
        "seed": seed,
        "train_frac": train_frac,
        "dev_frac": dev_frac,
        "groups": dict(sorted(assignment.items())),
        "group_sizes": {k: len(groups[k]) for k in sorted(groups)},
        "sizes": {phase: sum(len(groups[k]) for k in split_groups[phase])
                  for phase in ("train", "dev", "test")},
    }


def split_label_distribution(rows: list[QAExample], row_split: dict[str, str]) -> dict:
    """每个split的标签分布 (供泄漏/偏斜审计)."""
    out: dict[str, Counter] = {phase: Counter() for phase in ("train", "dev", "test")}
    for row in rows:
        out[row_split[row.instance_id]][row.label or "<unlabeled>"] += 1
    return {phase: dict(counter) for phase, counter in out.items()}


# ═════════════════════════ 评测器 ═════════════════════════


def compute_label_metrics(gold: list[str], verdicts: list[str | None]) -> dict:
    """三态核心指标: macro-F1(等权)/accuracy/混淆矩阵/invalid计数.

    invalid预测(verdict非法或None)不进任何预测计数, 但其gold行保留在
    recall分母与accuracy分母中 (单独计数, 不移出分母).
    """
    if len(gold) != len(verdicts):
        raise ValueError(f"gold与verdicts长度不一致: {len(gold)} vs {len(verdicts)}")
    bad = sorted({g for g in gold if g not in VERDICT_CLASSES})
    if bad:
        raise ValueError(f"gold标签超出三态契约: {bad}")

    conf = {g: {c: 0 for c in VERDICT_CLASSES} for g in VERDICT_CLASSES}
    invalid_by_gold = {g: 0 for g in VERDICT_CLASSES}
    n_invalid = 0
    correct = 0
    for g, v in zip(gold, verdicts, strict=True):
        if v not in VERDICT_CLASSES:
            n_invalid += 1
            invalid_by_gold[g] += 1
            continue
        conf[g][v] += 1
        if g == v:
            correct += 1

    per_class: dict[str, dict] = {}
    for cls in VERDICT_CLASSES:
        tp = conf[cls][cls]
        predicted = sum(conf[g][cls] for g in VERDICT_CLASSES)
        support = sum(conf[cls].values()) + invalid_by_gold[cls]
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[cls] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "predicted": predicted,
            "support": support,
        }
    n = len(gold)
    macro_f1 = sum(per_class[c]["f1"] for c in VERDICT_CLASSES) / len(VERDICT_CLASSES)
    return {
        "n": n,
        "accuracy": round(correct / n, 6) if n else 0.0,
        "macro_f1": round(macro_f1, 6),
        "per_class": per_class,
        "confusion_matrix": {
            "classes": list(VERDICT_CLASSES),
            "matrix": [[conf[g][c] for c in VERDICT_CLASSES] for g in VERDICT_CLASSES],
            "invalid_by_gold": {g: invalid_by_gold[g] for g in VERDICT_CLASSES},
        },
        "n_invalid": n_invalid,
    }


def evaluate_predictions(rows: list[QAExample], preds: list[Prediction]) -> dict:
    """完整QA级指标: 三态macro-F1 + accuracy + citation precision + invalid明细."""
    if len(rows) != len(preds):
        raise ValueError(f"rows与preds长度不一致: {len(rows)} vs {len(preds)}")
    for row, pred in zip(rows, preds, strict=True):
        if row.instance_id != pred.instance_id:
            raise ValueError(f"预测错位: row={row.instance_id} pred={pred.instance_id}")
    unlabeled = [r.instance_id for r in rows if r.label not in VERDICT_CLASSES]
    if unlabeled:
        raise ValueError(f"存在无gold标签行, 无法评测: {unlabeled[:5]}")

    metrics = compute_label_metrics(
        [r.label or "" for r in rows], [p.verdict for p in preds],
    )
    n_citations = n_valid = n_rows_with = 0
    for row, pred in zip(rows, preds, strict=True):
        if not pred.cited_evidence_ids:
            continue
        allowed = {e.evidence_id for e in row.evidence}
        n_rows_with += 1
        n_citations += len(pred.cited_evidence_ids)
        n_valid += len(set(pred.cited_evidence_ids) & allowed)
    metrics["citation"] = {
        "n_rows_with_citations": n_rows_with,
        "n_citations": n_citations,
        "n_valid": n_valid,
        "precision": round(n_valid / n_citations, 6) if n_citations else None,
    }
    metrics["invalid_instance_ids"] = [
        p.instance_id for p in preds if p.verdict not in VERDICT_CLASSES
    ]
    metrics["n_abstain"] = sum(1 for p in preds if p.abstain)
    return metrics


def evaluate_by_check_item(rows: list[QAExample], preds: list[Prediction]) -> dict[str, dict]:
    """按check_item分层: 一行可属多个stratum; 每层给出紧凑指标."""
    strata: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        for key in row.check_items or ("<unrouted>",):
            strata.setdefault(key, []).append(i)
    out: dict[str, dict] = {}
    for key in sorted(strata, key=lambda k: (-len(strata[k]), k)):
        idx = strata[key]
        metrics = evaluate_predictions([rows[i] for i in idx], [preds[i] for i in idx])
        out[key] = {
            "n": metrics["n"],
            "macro_f1": metrics["macro_f1"],
            "accuracy": metrics["accuracy"],
            "n_invalid": metrics["n_invalid"],
            "per_class": metrics["per_class"],
        }
    return out


# ═════════════════════════ B0: majority ═════════════════════════


class B0Majority:
    """训练split标签先验 → 恒预测多数类; 平票按类名字典序(确定性)."""

    name = "B0_majority"

    def __init__(self, train_rows: list[QAExample]) -> None:
        counts = Counter(
            r.label for r in train_rows if r.label in VERDICT_CLASSES
        )
        if counts:
            self.majority = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        else:
            self.majority = "not_in_evidence"
        total = sum(counts.values())
        self.prior = {c: round(counts.get(c, 0) / total, 6) if total else 0.0
                      for c in VERDICT_CLASSES}

    def predict(self, rows: list[QAExample], dev_rows: list[QAExample]) -> list[Prediction]:
        return [
            Prediction(r.instance_id, self.majority, (), False,
                       f"train majority prior={self.prior}")
            for r in rows
        ]


# ═════════════════════════ 共享数值/词法工具 ═════════════════════════

_UNIT_FACTORS: dict[str, dict[str, float]] = {
    "time": {"ms": 1.0, "毫秒": 1.0, "s": 1000.0, "秒": 1000.0, "min": 60000.0,
             "分钟": 60000.0, "h": 3600000.0, "小时": 3600000.0,
             "天": 86400000.0, "日": 86400000.0},
    "storage": {"B": 1.0, "字节": 1.0, "KB": 1024.0, "MB": 1048576.0,
                "GB": 1073741824.0, "TB": 1099511627776.0},
    "count": {"条": 1.0, "个": 1.0, "种": 1.0, "次": 1.0, "路": 1.0,
              "项": 1.0, "台": 1.0},
    "percent": {"%": 1.0},
}
_UNIT_LOOKUP = {u: (fam, fac) for fam, table in _UNIT_FACTORS.items()
                for u, fac in table.items()}
_UNIT_ALT = "|".join(sorted(_UNIT_LOOKUP, key=len, reverse=True))

_TAG_RE = re.compile(r"<[^>]+>")
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{1,}")
_ZH_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
_FUNCTION_CHARS = set("的一是了和与或及等将在对于如果因为所以还都也又就则即其该被使由从到这那有无比")
_ATTR_SPLIT_RE = re.compile(r"[，,。；;：:\n]")
_TRAILING_OP_RE = re.compile(
    r"(?:不大于|不超过|不高于|不小于|不少于|不低于|大于等于|小于等于|"
    r"大于|小于|至少|最多|至多|最低|为|等于|≤|≥|<=|>=|<|>|=)\s*$"
)


def lexical_tokens(text: str) -> set[str]:
    """词法token: ASCII标识符(entity: SQL/BLOB/PZXQ-GN-SQLFW...) + 中文bigram.

    HTML表格标记先剥离; 纯功能字bigram丢弃; 纯数字不进token(数值另行处理).
    """
    text = _TAG_RE.sub(" ", text)
    tokens = set(_ASCII_TOKEN_RE.findall(text))
    for run in _ZH_RUN_RE.findall(text):
        for i in range(len(run) - 1):
            bigram = run[i:i + 2]
            if bigram[0] in _FUNCTION_CHARS and bigram[1] in _FUNCTION_CHARS:
                continue
            tokens.add(bigram)
    return tokens


def numeric_value(value: str, unit: str) -> tuple[float, str] | None:
    """(原始值, 单位) → (族内基准值, 单位族); 未知单位 → None."""
    fam_fac = _UNIT_LOOKUP.get(unit)
    if fam_fac is None:
        return None
    return float(value) * fam_fac[1], fam_fac[0]


def _attr_before(text: str, start: int) -> str:
    """数值前的subject短语: 取同子句尾段, 剥离空白/标记/尾部操作符."""
    segment = text[max(0, start - 16):start]
    segment = _ATTR_SPLIT_RE.split(segment)[-1]
    segment = re.sub(r"[\s\*#`>|_\-]", "", segment)
    return _TRAILING_OP_RE.sub("", segment)


_NUM_UNIT_RE = re.compile(
    rf"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_UNIT_ALT})"
)


def extract_numerics(text: str) -> list[tuple[float, str, str]]:
    """带已知单位的数值 + 其subject: [(基准值, 单位族, subject)]."""
    out: list[tuple[float, str, str]] = []
    for m in _NUM_UNIT_RE.finditer(text):
        nv = numeric_value(m.group("value"), m.group("unit"))
        if nv is not None:
            out.append((nv[0], nv[1], _attr_before(text, m.start())))
    return out


# ═════════════════════════ B2: lexical ═════════════════════════


class B2Lexical:
    """词法重叠baseline: 数值冲突→refute; token重叠≥τ→support; 否则NIE.

    τ在dev split上网格搜索最大化macro-F1(平票取较小τ); 冲突判定:
    answer数值在其单位族内无任何证据数值匹配(相对差≤tol视为匹配),
    且其subject出现在含同族数值的证据块中.
    """

    name = "B2_lexical"
    _GRID = [round(0.05 * i, 2) for i in range(1, 19)]

    def __init__(self, support_threshold: float | None = None,
                 conflict_rel_tol: float = 0.05) -> None:
        self.support_threshold = support_threshold
        self.conflict_rel_tol = conflict_rel_tol

    def _features(self, row: QAExample) -> dict:
        answer_tokens = lexical_tokens(row.answer)
        per_evidence = [(e.evidence_id, re.sub(r"\s+", "", e.text),
                         lexical_tokens(e.text)) for e in row.evidence]
        union = set().union(*(tok for _, _, tok in per_evidence)) if per_evidence else set()
        overlap = len(answer_tokens & union) / len(answer_tokens) if answer_tokens else 0.0

        conflict_ids: set[str] = set()
        for value, family, attr in extract_numerics(row.answer):
            if not attr:
                continue
            blocks = [
                (eid, plain, numerics)
                for eid, plain, _ in per_evidence
                for numerics in [extract_numerics(plain)]
                if any(fam == family for _, fam, _ in numerics)
            ]
            if not blocks:
                continue
            ev_values = [v for _, _, nums in blocks for v, fam, _ in nums
                         if fam == family]
            matched = any(
                abs(value - v) / max(abs(value), abs(v), 1e-9) <= self.conflict_rel_tol
                for v in ev_values
            )
            if matched:
                continue
            conflict_ids.update(eid for eid, plain, _ in blocks if attr in plain)
        return {
            "answer_tokens": answer_tokens,
            "per_evidence": per_evidence,
            "overlap": overlap,
            "conflict_ids": sorted(conflict_ids),
        }

    def _decide(self, row: QAExample, features: dict, tau: float) -> Prediction:
        if features["conflict_ids"]:
            return Prediction(row.instance_id, "refute",
                              tuple(features["conflict_ids"]), False,
                              f"numeric conflict, overlap={features['overlap']:.3f}")
        if features["overlap"] >= tau:
            best_id = ""
            best_hits = -1
            for eid, _, tokens in features["per_evidence"]:
                hits = len(features["answer_tokens"] & tokens)
                if hits > best_hits or (hits == best_hits and eid < best_id):
                    best_id, best_hits = eid, hits
            return Prediction(row.instance_id, "support",
                              (best_id,) if best_id else (), False,
                              f"overlap={features['overlap']:.3f}>=tau={tau}")
        return Prediction(row.instance_id, "not_in_evidence", (), False,
                          f"overlap={features['overlap']:.3f}<tau={tau}")

    def _tune_threshold(self, dev_rows: list[QAExample]) -> float:
        labeled = [r for r in dev_rows if r.label in VERDICT_CLASSES]
        if not labeled:
            return 0.5
        features = [self._features(r) for r in labeled]
        best_tau, best_f1 = self._GRID[0], -1.0
        for tau in self._GRID:
            verdicts = [self._decide(r, f, tau).verdict for r, f in zip(labeled, features)]
            macro_f1 = compute_label_metrics(
                [r.label or "" for r in labeled], verdicts,
            )["macro_f1"]
            if macro_f1 > best_f1 + 1e-12:
                best_f1, best_tau = macro_f1, tau
        return best_tau

    def predict(self, rows: list[QAExample], dev_rows: list[QAExample]) -> list[Prediction]:
        if self.support_threshold is None:
            self.support_threshold = self._tune_threshold(dev_rows)
        features = [self._features(r) for r in rows]
        return [self._decide(r, f, self.support_threshold)
                for r, f in zip(rows, features, strict=True)]


# ═════════════════════════ B3: rule-numeric ═════════════════════════

_OPS_ALT = ("大于等于|小于等于|不大于|不超过|不高于|不小于|不少于|不低于|"
            "大于|小于|至少|最多|至多|最低|为|等于|≤|≥|<=|>=|<|>|=")
_NUM_PREFIX_RE = re.compile(
    rf"(?P<op>{_OPS_ALT})\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_UNIT_ALT})"
)
_NUM_POSTFIX_RE = re.compile(
    rf"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_UNIT_ALT})\s*(?P<op>及以上|以上|及以下|以下)"
)
_OP_TO_SEM = {
    "不大于": "le", "不超过": "le", "不高于": "le", "小于等于": "le",
    "≤": "le", "<=": "le", "最多": "le", "至多": "le", "以下": "le", "及以下": "le",
    "不小于": "ge", "不少于": "ge", "不低于": "ge", "大于等于": "ge",
    "≥": "ge", ">=": "ge", "至少": "ge", "最低": "ge", "以上": "ge", "及以上": "ge",
    "大于": "gt", "超过": "gt", ">": "gt",
    "小于": "lt", "<": "lt",
    "为": "eq", "等于": "eq", "=": "eq",
}


def extract_numeric_claims(text: str) -> list[tuple[str, str, float, str]]:
    """数值claim: (subject, 语义算子le/ge/gt/lt/eq, 族内基准值, 单位族).

    前缀式(不超过500ms) + 后缀式(200G以上, 后缀与已占用span重叠则跳过);
    数值抽取思路复自qa_module, 为独立实现, 不调用该模块.
    """
    claims: list[tuple[str, str, float, str]] = []
    occupied: list[tuple[int, int]] = []
    for m in _NUM_PREFIX_RE.finditer(text):
        nv = numeric_value(m.group("value"), m.group("unit"))
        sem = _OP_TO_SEM.get(m.group("op"))
        if nv is None or sem is None:
            continue
        claims.append((_attr_before(text, m.start()), sem, nv[0], nv[1]))
        occupied.append(m.span())
    for m in _NUM_POSTFIX_RE.finditer(text):
        if any(m.start() < end and start < m.end() for start, end in occupied):
            continue
        nv = numeric_value(m.group("value"), m.group("unit"))
        if nv is None:
            continue
        sem = "ge" if "以上" in m.group("op") else "le"
        claims.append((_attr_before(text, m.start()), sem, nv[0], nv[1]))
    return claims


def _interval(sem: str, value: float) -> tuple[float, bool, float, bool]:
    if sem == "le":
        return float("-inf"), False, value, True
    if sem == "lt":
        return float("-inf"), False, value, False
    if sem == "ge":
        return value, True, float("inf"), False
    if sem == "gt":
        return value, False, float("inf"), False
    return value, True, value, True


def _subset(a: tuple[float, bool, float, bool], b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    lower_ok = al > bl or (al == bl and (not alc or blc))
    upper_ok = au < bu or (au == bu and (not auc or buc))
    return lower_ok and upper_ok


def _disjoint(a: tuple[float, bool, float, bool],
              b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    a_before_b = au < bl or (au == bl and not (auc and blc))
    b_before_a = bu < al or (bu == al and not (buc and alc))
    return a_before_b or b_before_a


def _subject_match(answer_subject: str, evidence_subject: str, question: str) -> bool:
    """subject对齐: 相等, 或包容形式且短形式出现在question中(防无关参数误并)."""
    a = answer_subject.removesuffix("的")
    e = evidence_subject.removesuffix("的")
    if not a or not e:
        return False
    if a == e:
        return True
    if a in e or e in a:
        shorter = a if len(a) < len(e) else e
        return shorter in re.sub(r"\s+", "", question)
    return False


class B3RuleNumeric:
    """数值规则baseline: answer数值claim ↔ evidence数值claim 逐对区间比对.

    对齐条件 = subject对齐 + 单位族相同; 区间互相蕴含→support, 互斥→refute,
    证据自身既含支持又含反驳→保守NIE; 无可对齐数值claim → NIE.
    聚合优先级 refute > not_in_evidence > support (与qa_module聚合一致).
    """

    name = "B3_rule_numeric"

    def __init__(self, version: str = "rule_numeric_v1") -> None:
        self.version = version

    def _predict_one(self, row: QAExample) -> Prediction:
        outcomes: list[tuple[str, tuple[str, ...]]] = []
        for subject, sem, value, family in extract_numeric_claims(row.answer):
            matches: list[tuple[str, str]] = []
            for ev in row.evidence:
                for ev_subject, ev_sem, ev_value, ev_family in extract_numeric_claims(ev.text):
                    if family != ev_family:
                        continue
                    if not _subject_match(subject, ev_subject, row.question):
                        continue
                    answer_iv = _interval(sem, value)
                    evidence_iv = _interval(ev_sem, ev_value)
                    if _subset(answer_iv, evidence_iv) or _subset(evidence_iv, answer_iv):
                        matches.append(("support", ev.evidence_id))
                    elif _disjoint(answer_iv, evidence_iv):
                        matches.append(("refute", ev.evidence_id))
            decisive_labels = {label for label, _ in matches}
            if len(decisive_labels) > 1:
                outcomes.append(("not_in_evidence",
                                 tuple(sorted({eid for _, eid in matches}))))
            elif matches:
                outcomes.append((matches[0][0], (matches[0][1],)))
            else:
                outcomes.append(("not_in_evidence", ()))

        if not outcomes:
            return Prediction(row.instance_id, "not_in_evidence", (), False,
                              "answer无数值claim")
        labels = {label for label, _ in outcomes}
        if "refute" in labels:
            verdict = "refute"
        elif "not_in_evidence" in labels:
            verdict = "not_in_evidence"
        else:
            verdict = "support"
        cited = tuple(sorted({eid for label, eids in outcomes
                              if label == verdict for eid in eids}))
        n_claims = len(outcomes)
        n_decisive = sum(1 for label, _ in outcomes if label != "not_in_evidence")
        return Prediction(row.instance_id, verdict, cited, False,
                          f"claims={n_claims} decisive={n_decisive}")

    def predict(self, rows: list[QAExample], dev_rows: list[QAExample]) -> list[Prediction]:
        return [self._predict_one(row) for row in rows]


# ═════════════════════════ 运行器 (runs协议) ═════════════════════════


def _baseline_config(baseline: Baseline) -> dict:
    if isinstance(baseline, B0Majority):
        return {"majority": baseline.majority, "prior": baseline.prior}
    if isinstance(baseline, B2Lexical):
        return {"support_threshold": baseline.support_threshold,
                "conflict_rel_tol": baseline.conflict_rel_tol}
    if isinstance(baseline, B3RuleNumeric):
        return {"version": baseline.version}
    return {}


def render_markdown_report(result: dict) -> str:
    """评测结果的人类可读markdown表 (每个baseline一份完整指标表)."""
    lines = [
        "# QA benchmark 结果 (label=silver, 非gold, 仅作参考)",
        "",
        f"- frozen: `{result['frozen']['path']}` ({result['frozen']['n_rows']}行)",
        f"- labels: `{result['labels']['path']}`",
        f"- split: mode={result['split']['mode']} seed={result['split']['seed']} "
        f"sizes={result['split']['sizes']}",
        "",
    ]
    for name, entry in result["baselines"].items():
        m = entry["metrics"]
        lines += [f"## {name}", "",
                  f"- n={m['n']} accuracy={m['accuracy']} macro_f1={m['macro_f1']} "
                  f"invalid={m['n_invalid']} abstain={m['n_abstain']}",
                  f"- citation: {m['citation']}",
                  ""]
        lines += ["| class | precision | recall | f1 | predicted | support |",
                  "|---|---|---|---|---|---|"]
        for cls, pc in m["per_class"].items():
            lines.append(f"| {cls} | {pc['precision']} | {pc['recall']} | {pc['f1']} "
                         f"| {pc['predicted']} | {pc['support']} |")
        cm = m["confusion_matrix"]
        lines += ["", "混淆矩阵 (行=gold, 列=pred):",
                  f"```json\n{json.dumps(cm, ensure_ascii=False, indent=1)}\n```", ""]
    return "\n".join(lines)


def run_benchmark(
    frozen_path: Path = DEFAULT_FROZEN, labels_path: Path = DEFAULT_LABELS,
    seed: int = DEFAULT_SEED, train_frac: float = 0.6, dev_frac: float = 0.2,
    out_root: Path | None = None, script_name: str = "qa_benchmark",
) -> tuple[dict, Path]:
    """完整评测: 装载→分组split→三baseline→runs协议落盘; 返回(result, run目录)."""
    rows = load_frozen_rows(Path(frozen_path))
    labels = load_silver_labels(Path(labels_path))
    labeled, n_unlabeled = build_labeled_examples(rows, labels)

    row_split, split_info = make_group_splits(labeled, seed, train_frac, dev_frac)
    split_info["label_distribution"] = split_label_distribution(labeled, row_split)
    train = [r for r in labeled if row_split[r.instance_id] == "train"]
    dev = [r for r in labeled if row_split[r.instance_id] == "dev"]
    test = [r for r in labeled if row_split[r.instance_id] == "test"]
    eval_rows = [r for r in test if r.label in VERDICT_CLASSES]
    views = [replace(r, label=None, check_items=()) for r in eval_rows]

    baselines: list[Baseline] = [B0Majority(train), B2Lexical(), B3RuleNumeric()]
    baseline_results: dict[str, dict] = {}
    for baseline in baselines:
        preds = baseline.predict(views, dev)
        baseline_results[baseline.name] = {
            "config": _baseline_config(baseline),
            "metrics": evaluate_predictions(eval_rows, preds),
            "by_check_item": evaluate_by_check_item(eval_rows, preds),
        }

    config = {
        "frozen_path": str(frozen_path),
        "labels_path": str(labels_path),
        "seed": seed,
        "train_frac": train_frac,
        "dev_frac": dev_frac,
        "label_policy": "silver(final_verdict, glm-5.3 reviewed); NOT gold",
    }
    run = open_run(script_name, config, root=out_root)
    result = {
        "benchmark": "qa_consistency_scene1",
        "frozen": {"path": str(frozen_path), "n_rows": len(rows)},
        "labels": {"path": str(labels_path), "source": "silver", "is_gold": False,
                   "note": "silver标签(GLM-5.3复核)非gold, 指标仅作参考基准"},
        "n_unlabeled": n_unlabeled,
        "n_eval_rows": len(eval_rows),
        "label_distribution": dict(Counter(r.label for r in labeled)),
        "split": split_info,
        "baselines": baseline_results,
    }
    run.save_result(result)
    run.write_text("metrics_table.md", render_markdown_report(result))
    run.log(event="benchmark_done", n_rows=len(rows), n_eval=len(eval_rows))
    return result, run.path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QA一致性统一评测: B0/B2/B3确定性baseline (silver参考标签)")
    parser.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN,
                        help="QAInput形状冻结JSONL")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS,
                        help="silver标签JSONL")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--train-frac", type=float, default=0.6)
    parser.add_argument("--dev-frac", type=float, default=0.2)
    parser.add_argument("--run-root", type=Path, default=None,
                        help="覆盖runs输出根目录(默认data/gjb_438c/runs)")
    args = parser.parse_args()
    result, run_path = run_benchmark(
        frozen_path=args.frozen, labels_path=args.labels, seed=args.seed,
        train_frac=args.train_frac, dev_frac=args.dev_frac, out_root=args.run_root,
    )
    print(f"run dir: {run_path}")
    for name, entry in result["baselines"].items():
        m = entry["metrics"]
        print(f"{name:16s} macro_f1={m['macro_f1']:.4f} accuracy={m['accuracy']:.4f} "
              f"invalid={m['n_invalid']} citation_precision={m['citation']['precision']}")


if __name__ == "__main__":
    main()
