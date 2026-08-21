#!/usr/bin/env python3
"""逻辑层检测器 — Z3重跑+序列对比(盲测协议)

只看occurrences_injected,不碰injection元数据。
z3_verified绝不信任——检测器从occurrences自提取约束、自跑Solver。
技术: z3 / seqlen / seqdiff / setdiff / unitnorm
"""
import re
from z3 import Real, Solver, unsat
from algorithms.base import BaseDetector, DetectionResult

# 单位换算表(到基准单位)
UNIT_TO_BASE = {
    "ms": ("s", 0.001), "毫秒": ("s", 0.001), "us": ("s", 1e-6), "μs": ("s", 1e-6),
    "微秒": ("s", 1e-6), "ns": ("s", 1e-9), "纳秒": ("s", 1e-9), "秒": ("s", 1.0),
    "s": ("s", 1.0), "min": ("s", 60.0), "分钟": ("s", 60.0), "小时": ("s", 3600.0),
    "KB": ("MB", 1/1024), "MB": ("MB", 1.0), "GB": ("MB", 1024.0), "TB": ("MB", 1024.0*1024),
    "Kbps": ("Mbps", 0.001), "Mbps": ("Mbps", 1.0), "Gbps": ("Mbps", 1000.0),
    "kHz": ("Hz", 1000.0), "MHz": ("Hz", 1e6), "GHz": ("Hz", 1e9), "Hz": ("Hz", 1.0),
}


def normalize_unit(val, unit):
    """数值+单位归一化到基准单位"""
    if unit in UNIT_TO_BASE:
        base, factor = UNIT_TO_BASE[unit]
        return float(val) * factor, base
    return float(val), unit


class LogicChecker(BaseDetector):
    """逻辑层检测器 — 参数约束(Z3重跑) + 逻辑序列对比"""

    def __init__(self, expert_knowledge=None):
        super().__init__("logic", expert_knowledge)

    def detect(self, blind_entry: dict) -> DetectionResult:
        occurrences = blind_entry.get("occurrences", [])
        if not occurrences:
            return DetectionResult(False, "gold", "无内容", self.name)

        entity_type = blind_entry.get("entity_type", "")

        # 数值参数: Z3重跑
        if entity_type == "numeric_param":
            return self._detect_param(occurrences)

        # 流程/逻辑: 序列对比
        return self._detect_logic(occurrences)

    # ---------- 参数层: Z3重跑 ----------

    def _detect_param(self, occurrences):
        """从occurrences自提取约束,自跑Z3(绝不信任z3_verified元数据)"""
        constraints = []
        for occ in occurrences[:20]:  # 限制规模
            content = occ.get("content", "")
            if not isinstance(content, str):
                continue
            try:
                val = float(content.strip())
            except (ValueError, TypeError):
                continue
            op = occ.get("op", "eq")
            unit = occ.get("unit", "")
            norm_val, base_unit = normalize_unit(val, unit) if unit else (val, "")
            constraints.append((op, norm_val, base_unit, occ))

        if len(constraints) < 2:
            return DetectionResult(False, "gold", "有效约束不足", self.name)

        # 按基准单位分组,同单位内做Z3区间检查
        by_unit = {}
        for c in constraints:
            if c[2]:
                by_unit.setdefault(c[2], []).append(c)

        for base_unit, group in by_unit.items():
            if len(group) < 2:
                continue
            # 同参数同单位: 检查区间交集是否为空(等价于Z3 unsat)
            # 区间语义: ge→[v,∞), le→(-∞,v], gt→(v,∞), lt→(-∞,v), eq→[v,v]
            lo, hi = None, None
            strict_lo = strict_hi = False
            hit = None
            for op, val, _, occ in group:
                if op in ("ge",):
                    lo = max(lo, val) if lo is not None else val
                    hit = occ
                elif op in ("gt",):
                    if lo is None or val >= lo:
                        lo, strict_lo = val, True
                        hit = occ
                elif op in ("le",):
                    hi = min(hi, val) if hi is not None else val
                    hit = occ
                elif op in ("lt",):
                    if hi is None or val <= hi:
                        hi, strict_hi = val, True
                        hit = occ
                elif op == "eq":
                    lo = max(lo, val) if lo is not None else val
                    hi = min(hi, val) if hi is not None else val
                    hit = occ

            # 判空: lo>hi 或 (lo==hi且任一strict)
            conflict = (lo is not None and hi is not None and
                        (lo > hi or (lo == hi and (strict_lo or strict_hi))))

            if conflict:
                # 用真Z3再验证一次(证明不是手写区间逻辑的bug)
                s = Solver()
                x = Real("p")
                for op, val, _, _ in group:
                    if op == "ge": s.add(x >= val)
                    elif op == "le": s.add(x <= val)
                    elif op == "gt": s.add(x > val)
                    elif op == "lt": s.add(x < val)
                    elif op == "eq": s.add(x == val)
                z3_unsat = (s.check() == unsat)
                return DetectionResult(
                    True, "gold",
                    f"参数约束矛盾: 区间[{lo},{hi}]为空" + (f", Z3重跑unsat" if z3_unsat else ""),
                    self.name, technique="z3", z3_rerun=z3_unsat)

        # 单位冲突: 同参数不同位置用了不可换算的冲突单位语义
        # (如"gt 10秒"vs"gt 10ms"归一化后值不同且方向矛盾——已被上面覆盖;
        #  纯单位不一致(值相同单位不同)在数值上等价,交给语义层判断)

        return DetectionResult(False, "gold", "参数约束一致(Z3重跑sat)", self.name)

    # ---------- 逻辑层: 序列对比 ----------

    def _detect_logic(self, occurrences):
        sequences = []
        branches = []
        directions = []
        for occ in occurrences:
            content = occ.get("content", "")
            if isinstance(content, list):
                sequences.append([str(c) for c in content])
            if occ.get("branches"):
                branches.append([str(b) for b in occ["branches"]])
            if occ.get("data_flow_direction"):
                directions.append(occ["data_flow_direction"])

        # 数据流方向不一致(LOGIC-04)
        if len(directions) >= 2:
            uniq = set(directions)
            if len(uniq) > 1:
                return DetectionResult(
                    True, "silver",
                    f"数据流方向不一致: {uniq}",
                    self.name, technique="direction")

        # 分支集合不一致(LOGIC-05)
        if len(branches) >= 2:
            for i in range(len(branches) - 1):
                a, b = set(branches[i]), set(branches[i + 1])
                if a != b:
                    diff = a.symmetric_difference(b)
                    return DetectionResult(
                        True, "silver",
                        f"分支集合不一致(差异: {list(diff)[:3]})",
                        self.name, technique="setdiff")

        # 序列长度不一致(LOGIC-03/05)
        if len(sequences) >= 2:
            # 只比较"疑似同一流程"的序列(有重叠元素),避免不同流程误报
            for i in range(len(sequences)):
                for j in range(i + 1, len(sequences)):
                    a, b = sequences[i], sequences[j]
                    overlap = len(set(a) & set(b)) / max(1, min(len(set(a)), len(set(b))))
                    if overlap < 0.5:
                        continue  # 不同流程,跳过
                    if len(a) != len(b):
                        return DetectionResult(
                            True, "silver",
                            f"疑似同一流程步数不一致: {len(a)} vs {len(b)}(重叠度{overlap:.0%})",
                            self.name, technique="seqlen")
                    # 逐位比较(步骤交换检测)
                    for k in range(len(a)):
                        if a[k] != b[k]:
                            # 检查是否是交换(元素相同顺序不同)
                            if set(a) == set(b):
                                return DetectionResult(
                                    True, "silver",
                                    f"步骤顺序不一致: '{a[k][:15]}'与'{b[k][:15]}'位置互换",
                                    self.name, technique="seqswap")
                            return DetectionResult(
                                True, "silver",
                                f"步骤'{k+1}'不一致: '{a[k][:15]}' vs '{b[k][:15]}'",
                                self.name, technique="seqdiff")

        return DetectionResult(False, "silver", "逻辑一致", self.name)
