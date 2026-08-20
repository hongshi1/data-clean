#!/usr/bin/env python3
"""检测器基类 — 统一接口设计

设计原则:
  1. 统一接口: 所有检测器实现 detect() + evaluate()
  2. 专家知识注入: 通过构造函数注入GJB规则/词典/不一致规则
  3. 上下文关联输入: 接收上一层(双图融合聚合)的occurrences作为输入
  4. 可扩展: 新增检测项只需继承基类+实现detect方法

输入统一格式:
  - 来自评测集: EvalEntry {check_item, label, entity{occurrences}, injection}
  - 来自上下文关联: {entity_id, entity_type, occurrences[]} (双图融合输出)

输出统一格式:
  DetectionResult {detected: bool, confidence: str, reason: str, method: str}
"""
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from collections import defaultdict
from typing import Any


class DetectionResult:
    """统一检测结果"""
    def __init__(self, detected: bool, confidence: str = "silver",
                 reason: str = "", method: str = "", z3_verified: bool = False):
        self.detected = detected
        self.confidence = confidence
        self.reason = reason
        self.method = method
        self.z3_verified = z3_verified

    def to_dict(self):
        return {
            "detected": self.detected,
            "confidence": self.confidence,
            "reason": self.reason,
            "method": self.method,
            "z3_verified": self.z3_verified,
        }


class BaseDetector(ABC):
    """检测器基类

    使用方式:
      # 1. 注入专家知识
      detector = SyntaxChecker(gjb_rules=rules, expert_dict=词典)

      # 2. 从评测集检测
      results = detector.evaluate(eval_entries)

      # 3. 从上下文关联结果检测
      results = detector.detect_from_context(context_results)
    """

    def __init__(self, name: str, expert_knowledge: dict = None):
        self.name = name
        self.expert_knowledge = expert_knowledge or {}
        # expert_knowledge可能包含:
        # - gjb_rules: GJB 438C规则库(120条)
        # - expert_dict: 专家词典(参数/单位/操作符)
        # - inconsistency_rules: 不一致规则(14条)
        # - lightrag_store: LightRAG知识图谱(实体关系)
        # - id_graph: ID-Graph(实体链接)

    @abstractmethod
    def detect(self, entry: dict) -> DetectionResult:
        """检测单个条目

        Args:
            entry: 评测集条目或上下文关联结果
                - 评测集: {check_item, label, entity{occurrences}, injection}
                - 上下文: {entity_id, entity_type, occurrences[]}

        Returns:
            DetectionResult
        """
        pass

    def evaluate(self, eval_entries: list) -> dict:
        """批量评测 — 计算P/R/F1

        Args:
            eval_entries: 评测集条目列表

        Returns:
            {tp, fp, fn, tn, precision, recall, f1, results}
        """
        tp = fp = fn = tn = 0
        results = []

        for entry in eval_entries:
            label = entry.get("label", "")
            result = self.detect(entry)
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
                "confidence": result.confidence,
                "method": result.method,
                "reason": result.reason,
            })

        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        return {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "results": results,
        }

    def detect_from_context(self, context_results: list) -> list:
        """从上下文关联结果检测

        上下文关联(双图融合聚合器)输出的每个条目:
            {entity_id, entity_type, occurrences[{location, section, content}]}

        检测器基于occurrences内容判断是否存在不一致。

        Returns:
            list of DetectionResult
        """
        results = []
        for ctx in context_results:
            # 构造一个伪EvalEntry
            entry = {
                "check_item": self.name,
                "label": "unknown",  # 上下文结果没有gold label
                "entity": ctx,
                "injection": {"method": "context", "original": "", "injected": ""},
            }
            result = self.detect(entry)
            results.append({
                "entity_id": ctx.get("entity_id", ""),
                "entity_type": ctx.get("entity_type", ""),
                **result.to_dict(),
            })
        return results

    def get_occurrences(self, entry: dict) -> list:
        """从EvalEntry中提取occurrences（统一接口）"""
        # 评测集格式: entry["entity"]["occurrences"]
        entity = entry.get("entity", {})
        if isinstance(entity, dict):
            return entity.get("occurrences", [])
        # 上下文格式: entry本身就是occurrences
        if "occurrences" in entry:
            return entry["occurrences"]
        return []

    def get_injection(self, entry: dict) -> dict:
        """从EvalEntry中提取注入信息"""
        return entry.get("injection", {})

    def apply_injection_to_occurrences(self, occurrences: list, injection: dict) -> list:
        """将注入值回写到occurrences（检测器看到的应该包含注入后的内容）

        位置A保持原始值，位置B替换为注入值
        """
        import copy
        occs = copy.deepcopy(occurrences)

        if not injection or injection.get("method", "") in ("positive", "context", ""):
            return occs

        inject_location = injection.get("inject_location", "")
        injected_value = injection.get("injected", "")
        original_value = str(injection.get("original", ""))

        # 找到对应位置替换
        replaced = False
        for occ in occs:
            if occ.get("location") == inject_location:
                content = occ.get("content", "")
                if isinstance(content, str) and isinstance(injected_value, str):
                    if original_value and original_value in content:
                        occ["content"] = content.replace(original_value, injected_value, 1)
                    elif original_value == content:
                        occ["content"] = injected_value
                elif isinstance(content, list) and isinstance(injected_value, list):
                    occ["content"] = injected_value
                elif isinstance(content, dict) and isinstance(injected_value, dict):
                    occ["content"] = injected_value
                replaced = True
                break

        # 找不到对应location，替换第一个
        if not replaced and occs:
            occ = occs[0]
            content = occ.get("content", "")
            if isinstance(content, str) and isinstance(injected_value, str):
                if original_value == content:
                    occ["content"] = injected_value
                elif original_value and original_value in content:
                    occ["content"] = content.replace(original_value, injected_value, 1)
            elif isinstance(injected_value, list) and isinstance(content, list):
                occ["content"] = injected_value
            elif isinstance(injected_value, dict) and isinstance(content, dict):
                occ["content"] = injected_value

        return occs


def load_expert_knowledge() -> dict:
    """加载所有专家知识资产

    Returns:
        {
            "gjb_rules": GJB 438C规则库(120条),
            "expert_dict": 专家词典(参数/单位/操作符),
            "inconsistency_rules": 不一致规则(14条),
            "chunks": 结构化切片(5231条),
        }
    """
    BASE = Path(__file__).resolve().parent.parent
    knowledge = {}

    # GJB规则库
    rules_path = BASE / "knowledge/gjb_438c_rules_full.json"
    if rules_path.exists():
        knowledge["gjb_rules"] = json.loads(rules_path.read_text())

    # 专家词典
    kb_path = BASE / "knowledge/srs_kb.json"
    if kb_path.exists():
        knowledge["expert_dict"] = json.loads(kb_path.read_text())

    # 不一致规则
    inc_path = BASE / "knowledge/inconsistency_rules.json"
    if inc_path.exists():
        knowledge["inconsistency_rules"] = json.loads(inc_path.read_text())

    # 结构化切片
    chunks_path = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
    if chunks_path.exists():
        knowledge["chunks"] = json.loads(chunks_path.read_text())

    return knowledge


def load_context_results() -> list:
    """加载上下文关联(双图融合聚合)的结果

    上下文关联层输出: 每个条目 = {entity_id, entity_type, occurrences[]}
    检测器直接使用这些occurrences做检测

    Returns:
        list of context entries
    """
    BASE = Path(__file__).resolve().parent.parent
    # 优先使用检测对象(已经做过上下文聚合)
    entities_path = BASE / "data/gjb_438c/data_assets/eval_entities.json"
    if entities_path.exists():
        data = json.loads(entities_path.read_text())
        return data.get("entities", [])
    return []


def load_eval_entries() -> list:
    """加载评测集"""
    BASE = Path(__file__).resolve().parent.parent
    eval_path = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
    if eval_path.exists():
        data = json.loads(eval_path.read_text())
        return data.get("entries", [])
    return []
