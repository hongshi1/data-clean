"""R2校准: identifier接地概率化的误判案例库构建 + 确定性逻辑回归.

任务来源: docs/srs_project/99_unified_action_plan.md Phase 3(R2) +
98号B类三切口之①(接地概率化) + 97号§2.4(PL-Guard接地/策略分离).

案例库(Step 1, 全部claim级、ID在场、可审计):
  来源A  d3_train interface_flow族(297例)——s_interface_narrative
         (绑定对→label 1) / r_sender_swap(发送方跨行污染→label 0) /
         n_effect_claim(效果性断言杜撰→label 0);
         **排除文档04/06**(04=91QA主评测的冻结文档, 06=crossdoc06
         评测的冻结文档——训练/评测文档不重叠的LODO纪律);
  来源B  verify_identifier第5步same-subject-mismatch refute路径自然
         产出的最小对——refute实例(绑定错, 走确定性refute路径, 不进
         训练)的同路径孪生: 把answer的ID替换为该subject在证据中注册
         的ID(绑定对, 只差ID一个字段)→label 1。d3_train的r_*算子只换
         值不换ID, refute路径实例只存在于评测集(91QA S1QA-084,
         violations VIO-02..05), 孪生本身不出现在任何评测集(合成
         对照侧, 不构成评测污染; 文档04/06同源性在报告中如实披露)。

校准(Step 2/3, 确定性):
  特征    GroundingFeatures四维(subject_bind_ratio / predicate_hit_ratio
         / id_block_ratio / subject_id_proximity, 见
         algorithms/consistency/identifier_grounding.py);
  拟合    IRLS牛顿迭代逻辑回归(固定200轮+收敛容差, L2岭(截距不罚),
         零随机源——同数据同权重, 逐位复现);
  阈值    训练F1最大化(候选=相邻训练分数中点+端点, 并列取更低=保守
         方向; 全零并列回退两类均值中点)。

用法:
  python tools/calibrate_identifier_grounding.py            # 报告(不写)
  python tools/calibrate_identifier_grounding.py --write    # 校准产物写入
          config/claim_channels_rules_v1.json(identifier_grounding节,
          原地外科手术式更新保留描述) + 案例库落
          data/gjb_438c/distillation/identifier_grounding_cases_v1.jsonl
          + runs协议存证
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE / "tools"), str(BASE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from run_utils import open_run  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from algorithms.consistency.answer_claims import (  # noqa: E402
    _IDENTIFIER,
    decompose_claims,
)
from algorithms.consistency.claim_channels import (  # noqa: E402
    CLAIM_CHANNELS_RULES_FILE,
    default_rules,
    verify_identifier,
)
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    read_jsonl,
)
from algorithms.consistency.identifier_grounding import (  # noqa: E402
    IdentifierGroundingConfig,
    IdentifierGroundingJudge,
)
from algorithms.consistency.qa_models import QAInput  # noqa: E402

D3_TRAIN = BASE / "data/gjb_438c/distillation/d3_train_instances_v1.jsonl"
CROSSDOC06 = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"
QA91 = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
VIOLATIONS = (BASE / "data/gjb_438c/localization_gold"
              / "violation_evalset_v1.jsonl")
CASE_LIBRARY_OUT = (BASE / "data/gjb_438c/distillation"
                    / "identifier_grounding_cases_v1.jsonl")

#: 训练排除的文档(评测冻结文档, LODO纪律): 04=91QA, 06=crossdoc06
EXCLUDED_DOCS: tuple[str, ...] = ("04", "06")

#: 训练纳入的d3_train族(答案局部断言即被测绑定; trace族的章节绑定
#: 在claim层不可分(4.1.x前缀共享), 属trace专家职责, 不入训练)
TRAIN_FAMILIES: tuple[str, ...] = ("interface_flow",)

FEATURE_NAMES: tuple[str, ...] = (
    "subject_bind_ratio", "predicate_hit_ratio",
    "id_block_ratio", "subject_id_proximity")


# ═══════════════════════════════════════════════════════════════
# 1. 案例库构建
# ═══════════════════════════════════════════════════════════════


def _doc_of(instance_id: str) -> str:
    match = re.match(r"D3TR-(\d+)-", instance_id)
    return match.group(1) if match else ""


def identifier_claims(request: QAInput) -> list[tuple[int, Any]]:
    """answer分解出的identifier claims(带序号)."""
    claims = decompose_claims(request.question, request.answer)
    return [(i, claim) for i, claim in enumerate(claims, 1)
            if claim.kind == "identifier"]


def registered_id_for_subject(request: QAInput, claim: Any,
                              ) -> str | None:
    """复现verify_identifier第5步refute路径的窗口扫描, 取注册ID.

    同subject局部窗口(identifier_window_before/after)内唯一的不同ID
    = 证据为该subject注册的标识符——refute实例与孪生只差这个字段。
    """
    rules = default_rules()
    subject = re.sub(r"\s+", "", claim.attr or "")
    subject_core = re.sub(rules.identifier_subject_suffix, "", subject)
    if len(subject_core) < rules.identifier_subject_min_len:
        subject_core = subject
    if not subject_core:
        return None
    for ev in request.evidence:
        compact = re.sub(r"\s+", "", ev.text)
        start = compact.find(subject_core)
        while start >= 0:
            window = compact[max(0, start - rules.identifier_window_before):
                              min(len(compact), start + len(subject_core)
                                  + rules.identifier_window_after)]
            window_ids = _IDENTIFIER.findall(window)
            others = [i for i in window_ids if i != claim.text]
            if len(others) == 1:
                return others[0]
            start = compact.find(subject_core, start + 1)
    return None


def build_library() -> list[dict[str, Any]]:
    """误判案例库(claim级, ID在场, 带特征与来源溯源)."""
    judge = IdentifierGroundingJudge.from_config(_current_config())
    rules = default_rules()
    library: list[dict[str, Any]] = []

    def _record(request: QAInput, claim: Any, index: int, label: int,
                source: str, family: str, operator: str) -> dict[str, Any]:
        probability, features = judge.grounding_probability(
            request, claim, rules.identifier_subject_suffix)
        return {
            "label": label,
            "source": source,
            "family": family,
            "operator": operator,
            "claim_text": claim.text,
            "claim_attr": claim.attr,
            "question": request.question,
            "answer": request.answer,
            "evidence": [{
                "evidence_id": ev.evidence_id,
                "text": ev.text,
                "source_type": ev.source_type,
                "source_ref": {
                    "doc_id": ev.source_ref.doc_id,
                    "section": ev.source_ref.section,
                    "page": ev.source_ref.page,
                    "block_id": ev.source_ref.block_id,
                    "row_id": ev.source_ref.row_id,
                    "region_id": ev.source_ref.region_id,
                },
                "scope_id": ev.scope_id,
                "completeness": ev.completeness,
                "completeness_proof": ev.completeness_proof,
                "extraction_method": ev.extraction_method,
                "extraction_confidence": ev.extraction_confidence,
            } for ev in request.evidence],
            "features": features.as_dict(),
        }

    # ── 来源A: d3_train interface_flow(排除评测文档04/06) ─────────
    rows = read_jsonl(D3_TRAIN)
    for row in rows:
        if row["family"] not in TRAIN_FAMILIES:
            continue
        if _doc_of(row["instance_id"]) in EXCLUDED_DOCS:
            continue
        request = build_qa_input(row)
        for index, claim in identifier_claims(request):
            result = verify_identifier(request, claim, index, ())
            if result.verdict != "support":
                continue  # ID不在场(如表格内ID跨<p>拆分): judge不可及
            label = 1 if row["sound_label"] == "support" else 0
            library.append(_record(
                request, claim, index, label,
                source=f"d3_train:{row['instance_id']}",
                family=row["family"], operator=row["operator"]))

    # ── 来源B: refute路径实例的最小对孪生(绑定对侧) ────────────────
    refute_sources = [QA91, VIOLATIONS]
    n_refute_seen = 0
    for path in refute_sources:
        rows = read_jsonl(path)
        for row in rows:
            request = build_qa_input(row)
            for index, claim in identifier_claims(request):
                result = verify_identifier(request, claim, index, ())
                if result.verdict != "refute":
                    continue
                n_refute_seen += 1
                registered = registered_id_for_subject(request, claim)
                if registered is None:
                    continue
                twin_answer = request.answer.replace(
                    claim.text, registered, 1)
                twin_request = _replace_answer(request, twin_answer)
                for twin_index, twin_claim in identifier_claims(twin_request):
                    if twin_claim.text != registered:
                        continue
                    twin_result = verify_identifier(
                        twin_request, twin_claim, twin_index, ())
                    if twin_result.verdict != "support":
                        continue
                    library.append(_record(
                        twin_request, twin_claim, twin_index, 1,
                        source=f"minimal_pair:{request.instance_id}",
                        family="refute_path_twin",
                        operator="twin_id_registered"))

    # ── 来源C: ID错配最小对(同表兄弟行ID, 绑定对vs绑定错只差ID字段) ──
    # d3_train的r_*算子只换值不换ID; "ID在场但绑定错"的subject-ID错配
    # 类(VIO-03/04形态)在训练分布中缺失——从s_interface绑定对合成:
    # 把answer的ID换成同证据表的兄弟行ID→ID在场(走support路径)但
    # subject绑定错(label 0), 与原例只差ID一个字段。
    for case in list(library):
        if case["operator"] != "s_interface_narrative":
            continue
        request = _request_from_case(case)
        claim = _claim_from_case(case)
        sibling = _sibling_id(request, claim.text)
        if sibling is None:
            continue
        twin_answer = request.answer.replace(claim.text, sibling, 1)
        twin_request = _replace_answer(request, twin_answer)
        for twin_index, twin_claim in identifier_claims(twin_request):
            if twin_claim.text != sibling:
                continue
            twin_result = verify_identifier(
                twin_request, twin_claim, twin_index, ())
            if twin_result.verdict != "support":
                continue
            library.append(_record(
                twin_request, twin_claim, twin_index, 0,
                source=f"minimal_pair_mismatch:{case['source']}",
                family="interface_flow", operator="twin_id_sibling"))
    library.sort(key=lambda case: (case["source"], case["claim_text"]))
    for case in library:
        case["n_refute_path_claims_seen"] = n_refute_seen
    return library


def _request_from_case(case: dict[str, Any]) -> QAInput:
    return build_qa_input({
        "instance_id": "calib-" + case["source"].replace(":", "-"),
        "question": case["question"],
        "answer": case["answer"],
        "context_freeze_id": "calib",
        "evidence": case["evidence"],
    })


def _claim_from_case(case: dict[str, Any]) -> Any:
    from algorithms.consistency.answer_claims import AnswerClaim
    return AnswerClaim(kind="identifier", text=case["claim_text"],
                       attr=case["claim_attr"])


def _sibling_id(request: QAInput, target: str) -> str | None:
    """同证据中第一个≠target的ID(文档序, 确定性)."""
    from algorithms.consistency.identifier_grounding import (
        evidence_binding_segments)
    for ev in request.evidence:
        for segment in evidence_binding_segments(ev.text):
            for identifier in _IDENTIFIER.findall(segment):
                if identifier != target:
                    return identifier
    return None


def _replace_answer(request: QAInput, answer: str) -> QAInput:
    """同证据/同问题, 仅替换answer(最小对的构造性变换)."""
    from dataclasses import replace
    return replace(request, answer=answer)


def _current_config() -> IdentifierGroundingConfig:
    return default_rules().identifier_grounding


# ═══════════════════════════════════════════════════════════════
# 2. 确定性逻辑回归(IRLS, 零随机源)
# ═══════════════════════════════════════════════════════════════


def fit_logistic(features: np.ndarray, labels: np.ndarray,
                 ridge: float = 1.0, max_iter: int = 200,
                 tol: float = 1e-12) -> np.ndarray:
    """IRLS牛顿迭代(截距不罚的L2岭); 同输入同输出, 逐位复现."""
    design = np.hstack([features, np.ones((features.shape[0], 1))])
    penalty = np.eye(design.shape[1]) * ridge
    penalty[-1, -1] = 0.0  # 截距不罚
    weights = np.zeros(design.shape[1])
    for _ in range(max_iter):
        linear = design @ weights
        probabilities = 1.0 / (1.0 + np.exp(-linear))
        weight_matrix = probabilities * (1.0 - probabilities)
        gradient = design.T @ (labels - probabilities) - penalty @ weights
        hessian = ((design.T * weight_matrix) @ design) + penalty
        step = np.linalg.solve(hessian, gradient)
        weights = weights + step
        if float(np.max(np.abs(step))) < tol:
            break
    return weights


def choose_threshold(scores: np.ndarray, labels: np.ndarray) -> float:
    """阈值选择: 训练F1最大化(候选=相邻分数中点+端点; 并列取更低——
    保守方向: 宁可保留support也不多降级; 全零并列回退两类均值中点)."""
    candidates = [0.0, 1.0]
    unique = np.unique(scores)
    for left, right in zip(unique[:-1], unique[1:]):
        candidates.append(float((left + right) / 2.0))
    best_threshold = 0.0
    best_f1 = -1.0
    for threshold in sorted(candidates):
        predicted = (scores >= threshold).astype(float)
        tp = float(((predicted == 1) & (labels == 1)).sum())
        fp = float(((predicted == 1) & (labels == 0)).sum())
        fn = float(((predicted == 0) & (labels == 1)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)
        if f1 > best_f1 + 1e-12:
            best_f1 = f1
            best_threshold = threshold
    return round(best_threshold, 4)


def _scores_from(library: list[dict[str, Any]],
                 weights: np.ndarray) -> np.ndarray:
    features = np.array([[case["features"][name]
                          for name in FEATURE_NAMES]
                         for case in library], dtype=float)
    design = np.hstack([features, np.ones((features.shape[0], 1))])
    linear = design @ weights
    return 1.0 / (1.0 + np.exp(-linear))


# ═══════════════════════════════════════════════════════════════
# 3. 评测集侧验证(不训练, 只报告)
# ═══════════════════════════════════════════════════════════════


def evalset_identifier_cases(paths: dict[str, Path],
                             judge: IdentifierGroundingJudge,
                             ) -> list[dict[str, Any]]:
    rules = default_rules()
    out: list[dict[str, Any]] = []
    for name, path in paths.items():
        for row in read_jsonl(path):
            request = build_qa_input(row)
            for index, claim in identifier_claims(request):
                result = verify_identifier(request, claim, index, ())
                if result.verdict != "support":
                    continue
                probability, features = judge.grounding_probability(
                    request, claim, rules.identifier_subject_suffix)
                out.append({
                    "evalset": name,
                    "instance_id": request.instance_id,
                    "claim_text": claim.text,
                    "baseline_verdict": result.verdict,
                    "probability": round(probability, 4),
                    "features": features.as_dict(),
                    "downgraded": probability < judge.threshold,
                })
    return out


# ═══════════════════════════════════════════════════════════════
# 4. 主流程
# ═══════════════════════════════════════════════════════════════


def _config_from_weights(weights: np.ndarray, threshold: float,
                          glue: tuple[str, ...]
                          ) -> IdentifierGroundingConfig:
    return IdentifierGroundingConfig(
        threshold=float(threshold),
        subject_bind_weight=float(weights[0]),
        predicate_hit_weight=float(weights[1]),
        id_block_weight=float(weights[2]),
        proximity_weight=float(weights[3]),
        intercept=float(weights[4]),
        predicate_glue=glue,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="校准产物写入config JSON+案例库+runs存证")
    args = parser.parse_args()

    library = build_library()
    labels = np.array([case["label"] for case in library], dtype=float)
    features = np.array([[case["features"][name]
                          for name in FEATURE_NAMES]
                         for case in library], dtype=float)
    weights = fit_logistic(features, labels)
    scores = _scores_from(library, weights)
    threshold = choose_threshold(scores, labels)
    glue = _current_config().predicate_glue
    config = _config_from_weights(weights, threshold, glue)
    judge = IdentifierGroundingJudge.from_config(config)

    predicted = (scores >= threshold).astype(float)
    accuracy = float((predicted == labels).mean())
    precision = (float((predicted[labels == 1] == 1).mean())
                 if (predicted == 1).any() else 0.0)
    recall = float((predicted[labels == 1] == 1).mean())
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)

    negative = scores[labels == 0]
    positive = scores[labels == 1]
    margin = float(positive.min() - negative.max())

    print("=" * 72)
    print("R2 identifier接地概率化——校准报告")
    print("=" * 72)
    by_source = Counter(case["source"].split(":")[0] for case in library)
    by_type = Counter((case["family"], case["operator"], case["label"])
                      for case in library)
    print(f"\n[案例库] 总数={len(library)} 来源分布={dict(by_source)}")
    print("  类型分布(family/operator/label):")
    for (family, operator, label), count in sorted(by_type.items()):
        print(f"    {family}/{operator}/label={label}: {count}")
    n_refute = library[0]["n_refute_path_claims_seen"] if library else 0
    print(f"  refute路径实例(评测集, 对照侧不进训练)={n_refute}")
    print(f"  训练排除文档(LODO)={EXCLUDED_DOCS}(04=91QA, 06=crossdoc06)")

    print("\n[特征分布] (均值±极差, 按label)")
    for name in FEATURE_NAMES:
        pos = features[labels == 1, FEATURE_NAMES.index(name)]
        neg = features[labels == 0, FEATURE_NAMES.index(name)]
        print(f"  {name}: label1 {pos.mean():.3f}"
              f" [{pos.min():.2f},{pos.max():.2f}]"
              f" | label0 {neg.mean():.3f}"
              f" [{neg.min():.2f},{neg.max():.2f}]")

    print("\n[逻辑回归IRLS] 权重(确定性, 200轮收敛):")
    for name, value in zip([*FEATURE_NAMES, "intercept"], weights):
        print(f"  {name}: {value:+.4f}")
    print(f"  threshold(训练F1最大化): {threshold:.4f}  分数间隔: {margin:+.4f}")
    print(f"  训练集表现: acc={accuracy:.4f} P={precision:.4f}"
          f" R={recall:.4f} F1={f1:.4f}")
    if margin <= 0:
        print("  ⚠ 训练分数重叠(不可分)——阈值按F1最大化选择(如实报告)")

    print("\n[评测集侧验证](不训练, 仅报告)")
    cases = evalset_identifier_cases(
        {"crossdoc06": CROSSDOC06, "91QA": QA91, "violations": VIOLATIONS},
        judge)
    for case in cases:
        print(f"  {case['evalset']}/{case['instance_id']}"
              f" {case['claim_text'][:28]:<30}"
              f" P={case['probability']:.4f}"
              f" f2={case['features']['predicate_hit_ratio']:.2f}"
              f" {'↓降级' if case['downgraded'] else ' 保留'}")
    s1_053 = [c for c in cases
              if c["evalset"] == "91QA" and c["instance_id"] == "S1QA-053"]
    if s1_053:
        kept = all(not c["downgraded"] for c in s1_053)
        print(f"  91QA约束(S1QA-053必须保留support): "
              f"{'✓ 满足' if kept else '✗ 违反——阈值必须下调'}")

    if not args.write:
        print("\n(--write 未指定: 仅报告, 不写config/案例库)")
        return

    # ── 写入config(原地外科手术式, 保留各节描述) ─────────────────
    raw = json.loads(CLAIM_CHANNELS_RULES_FILE.read_text(encoding="utf-8"))
    section = raw["channel_confidences"]["identifier_grounding"]
    section["threshold"] = round(float(threshold), 4)
    section["feature_weights"] = {
        name: round(float(value), 4)
        for name, value in zip([*FEATURE_NAMES, "intercept"], weights)}
    CLAIM_CHANNELS_RULES_FILE.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"\n[写入] {CLAIM_CHANNELS_RULES_FILE}")

    for case in library:
        case.pop("n_refute_path_claims_seen", None)
    CASE_LIBRARY_OUT.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False)
                  for case in library) + "\n", encoding="utf-8")
    print(f"[写入] {CASE_LIBRARY_OUT} ({len(library)}例)")

    run = open_run("calibrate_identifier_grounding", {
        "train_families": list(TRAIN_FAMILIES),
        "excluded_docs": list(EXCLUDED_DOCS),
        "n_cases": len(library),
        "library_path": str(CASE_LIBRARY_OUT.relative_to(BASE)),
    })
    run.save_result({
        "n_cases": len(library),
        "library_by_source": dict(by_source),
        "library_by_type": {
            f"{family}/{operator}/label{label}": count
            for (family, operator, label), count in sorted(by_type.items())},
        "n_refute_path_claims_seen": n_refute,
        "feature_names": list(FEATURE_NAMES),
        "weights": {name: round(float(value), 6)
                    for name, value in zip([*FEATURE_NAMES, "intercept"],
                                           weights)},
        "threshold": threshold,
        "score_margin": margin,
        "train_metrics": {
            "accuracy": accuracy, "precision": precision,
            "recall": recall, "f1": f1},
        "evalset_cases": cases,
    })
    print(f"[写入] {run.path}")

    print("\n[同步内置回退常量] 将以下值粘贴进 claim_channels.py 的"
          "_IDENTIFIER_GROUNDING_*常量(双层保险, 测试锁定等价):")
    print(f"  _IDENTIFIER_GROUNDING_THRESHOLD = {threshold:.4f}")
    for name, value in zip(["SUBJECT_BIND", "PREDICATE_HIT", "ID_BLOCK",
                            "PROXIMITY", "INTERCEPT"], weights):
        print(f"  _IDENTIFIER_GROUNDING_W_{name} = {value:.4f}")


if __name__ == "__main__":
    main()
