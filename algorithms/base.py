#!/usr/bin/env python3
"""检测器基类 — 盲测协议版

设计原则(响应循环验证审计):
  1. 检测器只看: occurrences_injected + rendered_context + question (输入白名单)
  2. 检测器绝不碰: injection.* / label / answer / confidence / verified / z3_verified (黑名单)
  3. z3_verified等认证字段只用于"注入有效性验证"层,检测器必须自己重跑Z3
  4. evaluate()中label仅用于评分(标准评测协议),不进入detect()

三层评测协议:
  L1 注入有效性验证: 元数据+Z3重跑,认证数据集本身质量
  L2 盲测benchmark: LLM/人只看rendered_context
  L3 检测器盲测: 本基类,只喂occurrences_injected,报P/R/F1+技术分解
"""
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class DetectionResult:
    """统一检测结果"""
    def __init__(self, detected: bool, confidence: str = "silver",
                 reason: str = "", method: str = "", technique: str = "",
                 z3_rerun: bool = False):
        self.detected = detected
        self.confidence = confidence
        self.reason = reason
        self.method = method
        self.technique = technique   # 触发的技术: keyword/editdist/z3/seqlen/setdiff/...
        self.z3_rerun = z3_rerun     # 检测器自己重跑了Z3(非信任元数据)

    def to_dict(self):
        return {
            "detected": self.detected,
            "confidence": self.confidence,
            "reason": self.reason,
            "method": self.method,
            "technique": self.technique,
            "z3_rerun": self.z3_rerun,
        }


class BaseDetector(ABC):
    """检测器基类(盲测协议)

    使用方式:
      detector = TermChecker()
      results = detector.evaluate(eval_entries)   # 自动构造盲条目
      blind = detector.make_blind(entry)          # 查看检测器实际看到的输入
    """

    def __init__(self, name: str, expert_knowledge: dict = None):
        self.name = name
        self.expert_knowledge = expert_knowledge or {}

    @abstractmethod
    def detect(self, blind_entry: dict) -> DetectionResult:
        """检测单个盲条目

        blind_entry只含(输入白名单):
          - occurrences: occurrences_injected(注入已渲染)
          - rendered_context: 渲染文本
          - question: 问题
          - entity_id / entity_type: 仅作路由与日志,不含答案信息
        """

    # ---------- 盲条目构造 ----------

    def make_blind(self, entry: dict) -> dict:
        """从评测集条目构造盲条目(剥离一切元数据)

        黑名单字段一律不复制: injection.* / label / answer /
        confidence / verified / verified_by / z3_verified / answer_reason
        """
        return {
            "entity_id": entry.get("entity", {}).get("entity_id", ""),
            "entity_type": entry.get("entity", {}).get("entity_type", ""),
            "occurrences": entry.get("occurrences_injected",
                                     entry.get("entity", {}).get("occurrences", [])),
            "rendered_context": entry.get("rendered_context", ""),
            "question": entry.get("question", ""),
        }

    # ---------- 评测 ----------

    def evaluate(self, eval_entries: list) -> dict:
        """批量评测 — label只用于评分,不进入detect"""
        tp = fp = fn = tn = 0
        results = []

        for entry in eval_entries:
            label = entry.get("label", "")  # 评分用
            blind = self.make_blind(entry)
            result = self.detect(blind)
            detected = result.detected

            if label == "inconsistent" and detected:
                tp += 1
            elif label == "consistent" and detected:
                fp += 1
            elif label == "inconsistent" and not detected:
                fn += 1
            else:
                tn += 1

            results.append({
                "eval_id": entry.get("eval_id", ""),
                "check_item": entry.get("check_item", ""),
                "label": label,
                "detected": detected,
                "correct": (label == "inconsistent" and detected) or
                          (label == "consistent" and not detected),
                "technique": result.technique,
                "reason": result.reason,
            })

        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        return {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
            "results": results,
        }

    # ---------- 上下文检测(真实文档,无label) ----------

    def detect_from_context(self, context_results: list) -> list:
        """从上下文关联结果检测(每个条目={entity_id,entity_type,occurrences})"""
        results = []
        for ctx in context_results:
            blind = {
                "entity_id": ctx.get("entity_id", ""),
                "entity_type": ctx.get("entity_type", ""),
                "occurrences": ctx.get("occurrences", []),
                "rendered_context": "",
                "question": "",
            }
            result = self.detect(blind)
            results.append({"entity_id": ctx.get("entity_id", ""),
                            "entity_type": ctx.get("entity_type", ""),
                            **result.to_dict()})
        return results

    # ---------- 共享工具 ----------

    @staticmethod
    def levenshtein(s1, s2):
        s1, s2 = str(s1), str(s2)
        if len(s1) < len(s2):
            return BaseDetector.levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
            prev = curr
        return prev[-1]

    @classmethod
    def text_sim(cls, s1, s2):
        s1, s2 = str(s1), str(s2)
        if s1 == s2:
            return 1.0
        ml = max(len(s1), len(s2))
        return 1 - cls.levenshtein(s1, s2) / ml if ml > 0 else 1.0


def load_expert_knowledge() -> dict:
    """加载专家知识资产(注入检测器,不进盲条目)"""
    BASE = Path(__file__).resolve().parent.parent
    knowledge = {}
    for key, rel in [("gjb_rules", "knowledge/gjb_438c_rules_full.json"),
                     ("expert_dict", "knowledge/srs_kb.json"),
                     ("inconsistency_rules", "knowledge/inconsistency_rules.json")]:
        p = BASE / rel
        if p.exists():
            knowledge[key] = json.loads(p.read_text())
    return knowledge


def load_eval_entries() -> list:
    BASE = Path(__file__).resolve().parent.parent
    eval_path = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
    if eval_path.exists():
        return json.loads(eval_path.read_text()).get("entries", [])
    return []


def load_context_results() -> list:
    BASE = Path(__file__).resolve().parent.parent
    entities_path = BASE / "data/gjb_438c/data_assets/eval_entities.json"
    if entities_path.exists():
        return json.loads(entities_path.read_text()).get("entities", [])
    return []
