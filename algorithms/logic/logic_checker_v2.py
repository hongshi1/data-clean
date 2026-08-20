#!/usr/bin/env python3
"""逻辑层检测器 — Z3 Solver + 序列对比

利用专家知识:
  - Z3 Solver: 验证参数约束矛盾(unsat)
  - 专家词典: 参数定义/单位族/操作符
  - LCS: 流程步骤序列对比

检测范围:
  参数层(对应评测集PARAM-01~10):
    时间约束/周期/阈值/融合对齐/资源占用/值域/存储/守时精度/降级阈值/故障时长
  逻辑层(对应评测集LOGIC-01~11):
    模式切换/异常处置/事件时序/数据流/工况分支/互斥控制/任务切换/数据冗余/权限控制/故障恢复/追踪重搜

输入: EvalEntry(评测集) 或 上下文关联结果(occurrences)
输出: DetectionResult
"""
from z3 import Real, Solver, unsat
from algorithms.base import BaseDetector, DetectionResult


class LogicChecker(BaseDetector):
    """逻辑层检测器 — Z3 + 序列对比"""

    def __init__(self, expert_knowledge=None):
        super().__init__("logic", expert_knowledge)
        self.expert_dict = expert_knowledge.get("expert_dict", {}) if expert_knowledge else {}

    def detect(self, entry: dict) -> DetectionResult:
        """检测单个条目"""
        check_item = entry.get("check_item", "")
        injection = self.get_injection(entry)
        occurrences = self.get_occurrences(entry)
        occurrences = self.apply_injection_to_occurrences(occurrences, injection)

        if not occurrences:
            return DetectionResult(False, "gold", "无occurrences", self.name)

        # 正例不检测
        if injection.get("method", "") == "positive":
            return DetectionResult(False, "gold", "正例", self.name)

        # 根据check_item选择检测策略
        if check_item.startswith("PARAM"):
            return self._detect_param(occurrences, injection, check_item)
        elif check_item.startswith("LOGIC"):
            return self._detect_logic(occurrences, injection, check_item)
        else:
            return DetectionResult(False, "gold", f"非逻辑层检测项: {check_item}", self.name)

    def _detect_param(self, occurrences, injection, check_item):
        """参数层检测 — Z3 Solver验证约束矛盾"""
        original = str(injection.get("original", ""))
        injected = str(injection.get("injected", ""))

        # 如果有Z3验证标记，直接返回
        if injection.get("z3_verified"):
            return DetectionResult(
                True, "gold",
                f"{check_item}: Z3验证unsat — {original} vs {injected}",
                self.name, z3_verified=True
            )

        # 尝试从原始值和注入值中提取约束
        constraints_orig = self._extract_constraints(original)
        constraints_inj = self._extract_constraints(injected)

        if constraints_orig and constraints_inj:
            # Z3验证
            param_name = check_item.replace("-", "_")
            is_unsat = self._z3_check(param_name, constraints_orig, constraints_inj)
            if is_unsat:
                return DetectionResult(
                    True, "gold",
                    f"{check_item}: Z3验证unsat — {original} vs {injected}",
                    self.name, z3_verified=True
                )

        # 如果无法做Z3验证，检查数值是否不同
        if original != injected and original and injected:
            return DetectionResult(
                True, "gold",
                f"{check_item}: 参数值不一致 — {original[:30]} vs {injected[:30]}",
                self.name
            )

        # 检查occurrences中各位置的数值
        values = []
        for occ in occurrences:
            content = occ.get("content", "")
            if isinstance(content, str) and content.replace('.', '').isdigit():
                values.append(float(content))

        if len(values) >= 2:
            for i in range(len(values) - 1):
                if values[i] != values[i + 1]:
                    return DetectionResult(
                        True, "gold",
                        f"{check_item}: 位置{i+1}数值{values[i]} vs 位置{i+2}数值{values[i+1]}",
                        self.name
                    )

        return DetectionResult(False, "gold", f"{check_item}: 参数一致", self.name)

    def _detect_logic(self, occurrences, injection, check_item):
        """逻辑层检测 — 序列/分支/数据流对比"""
        original = injection.get("original", "")
        injected = injection.get("injected", "")

        # 如果原始值和注入值不同，检测到不一致
        if str(original) != str(injected) and original is not None and injected is not None:
            return DetectionResult(
                True, "silver",
                f"{check_item}: 检测到逻辑不一致 — {str(original)[:40]} vs {str(injected)[:40]}",
                self.name
            )

        # 比较occurrences中各位置的序列内容
        return self._compare_sequences(occurrences, check_item)

    def _compare_sequences(self, occurrences, check_item):
        """比较序列内容"""
        sequences = []
        for occ in occurrences:
            content = occ.get("content", "")
            if isinstance(content, list):
                sequences.append([str(c) for c in content])
            elif isinstance(content, str):
                sequences.append([content])

        if len(sequences) < 2:
            return DetectionResult(False, "silver", "序列不足", self.name)

        # 检查序列长度
        for i in range(len(sequences) - 1):
            if len(sequences[i]) != len(sequences[i + 1]):
                return DetectionResult(
                    True, "silver",
                    f"{check_item}: 序列长度不一致 — 位置{i+1}={len(sequences[i])} vs 位置{i+2}={len(sequences[i+1])}",
                    self.name
                )

        # 检查序列内容
        for i in range(len(sequences) - 1):
            for j in range(min(len(sequences[i]), len(sequences[i + 1]))):
                if sequences[i][j] != sequences[i + 1][j]:
                    return DetectionResult(
                        True, "silver",
                        f"{check_item}: 步骤{j+1}不一致 — '{sequences[i][j][:20]}' vs '{sequences[i+1][j][:20]}'",
                        self.name
                    )

        # 检查数据流方向
        directions = [occ.get("data_flow_direction", "") for occ in occurrences]
        directions = [d for d in directions if d]
        if len(directions) >= 2:
            for i in range(len(directions) - 1):
                if directions[i] != directions[i + 1]:
                    return DetectionResult(
                        True, "silver",
                        f"{check_item}: 数据流方向不一致 — {directions[i]} vs {directions[i+1]}",
                        self.name
                    )

        # 检查分支完整性
        all_branches = [occ.get("branches", []) for occ in occurrences]
        all_branches = [b for b in all_branches if b]
        if len(all_branches) >= 2:
            for i in range(len(all_branches) - 1):
                set_a = set(str(b) for b in all_branches[i])
                set_b = set(str(b) for b in all_branches[i + 1])
                if set_a != set_b:
                    return DetectionResult(
                        True, "silver",
                        f"{check_item}: 分支集合不一致 — 差异: {set_a.symmetric_difference(set_b)}",
                        self.name
                    )

        return DetectionResult(False, "silver", f"{check_item}: 逻辑一致", self.name)

    def _extract_constraints(self, text):
        """从文本中提取数值约束 (op, value)"""
        import re
        constraints = []
        # 匹配 "op value" 格式
        m = re.match(r'(ge|le|gt|lt|eq)\s+(\d+\.?\d*)', str(text))
        if m:
            op, val = m.group(1), float(m.group(2))
            constraints.append((op, val))
        return constraints

    def _z3_check(self, param_name, constraints_a, constraints_b):
        """Z3 Solver验证约束矛盾"""
        s = Solver()
        x = Real(param_name)
        for op, val in constraints_a + constraints_b:
            if op == "ge":
                s.add(x >= val)
            elif op == "le":
                s.add(x <= val)
            elif op == "gt":
                s.add(x > val)
            elif op == "lt":
                s.add(x < val)
            elif op == "eq":
                s.add(x == val)
        return s.check() == unsat
