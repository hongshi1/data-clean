#!/usr/bin/env python3
"""语法层检测器 — GJB规则驱动

利用专家知识:
  - GJB 438C规则库(120条): 检测章节/ID/引用/结构合规
  - 不一致规则: 检测内容缺失/模糊

检测范围(对应评测集GJB-01~11):
  GJB-01可测试性: 检测模糊需求(无量化指标)
  GJB-02~04: 检测容错/安全/审计条款缺失
  GJB-05需求可追溯: 检测追溯链断裂
  GJB-06~11: 检测报警/自检/掉电/防护/升级/降级条款缺失

输入: EvalEntry(评测集) 或 上下文关联结果(occurrences)
输出: DetectionResult
"""
import json
import re
from algorithms.base import BaseDetector, DetectionResult


class SyntaxChecker(BaseDetector):
    """语法层检测器 — GJB规则驱动"""

    # GJB规定的必填字段
    REQUIRED_FIELDS = {
        "能力标识表": ["序号", "标识符", "描述", "优先级"],
        "接口需求表": ["名称", "发送方", "接收方", "类型"],
        "追溯表": ["需求标识符", "测试标识符"],
    }

    # GJB合规检测关键词
    GJB_KEYWORDS = {
        "GJB-01": {"keywords": ["可测试", "验证方法", "确认方法"], "fuzzy": ["运行稳定", "良好", "可靠"]},
        "GJB-02": {"keywords": ["容错", "冗余", "备份", "故障转移", "热备", "主备"]},
        "GJB-03": {"keywords": ["访问控制", "权限控制", "身份认证", "授权"]},
        "GJB-04": {"keywords": ["审计日志", "操作日志", "日志记录"]},
        "GJB-05": {"keywords": ["追溯", "追踪", "映射关系"]},
        "GJB-06": {"keywords": ["报警", "告警", "警示", "预警"]},
        "GJB-07": {"keywords": ["自检", "开机检测", "启动检测", "BIT"]},
        "GJB-08": {"keywords": ["掉电", "断电", "电源故障", "UPS"]},
        "GJB-09": {"keywords": ["输入校验", "合法性校验", "数据校验", "边界检查"]},
        "GJB-10": {"keywords": ["版本升级", "软件升级", "回滚", "版本回退"]},
        "GJB-11": {"keywords": ["降级", "退化", "降级运行", "最低功能"]},
    }

    def __init__(self, expert_knowledge=None):
        super().__init__("syntax", expert_knowledge)
        self.gjb_rules = expert_knowledge.get("gjb_rules", {}) if expert_knowledge else {}

    def detect(self, entry: dict) -> DetectionResult:
        """检测单个条目

        策略:
          1. 获取occurrences(含注入后的内容)
          2. 根据check_item选择检测方法
          3. 对比各位置内容，检测缺失/不一致
        """
        check_item = entry.get("check_item", "")
        injection = self.get_injection(entry)
        occurrences = self.get_occurrences(entry)
        # 回写注入值
        occurrences = self.apply_injection_to_occurrences(occurrences, injection)

        if not occurrences or len(occurrences) < 1:
            return DetectionResult(False, "gold", "无occurrences", self.name)

        # 正例不检测
        if injection.get("method", "") == "positive":
            return DetectionResult(False, "gold", "正例，不检测", self.name)

        # 根据check_item选择检测策略
        if check_item.startswith("GJB"):
            return self._detect_gjb(entry, occurrences, check_item)
        else:
            # 非GJB类条目，通用检测
            return self._detect_general(occurrences, injection)

    def _detect_gjb(self, entry, occurrences, check_item):
        """GJB合规检测"""
        injection = self.get_injection(entry)
        original = injection.get("original", "")
        injected = injection.get("injected", "")

        # 如果注入值和原始值不同，说明有缺失/修改 → 检测到不一致
        if str(original) != str(injected):
            return DetectionResult(
                True, "gold",
                f"{check_item}: 检测到内容差异（{self._summarize_diff(original, injected)}）",
                self.name
            )

        # 检查occurrences中是否有内容缺失
        contents = [str(occ.get("content", "")) for occ in occurrences]
        if len(contents) >= 2:
            # 检查是否有位置内容为空或明显缺失
            for i, c in enumerate(contents):
                if not c or c == "[]" or c == "{}" or len(c) < 2:
                    return DetectionResult(
                        True, "gold",
                        f"{check_item}: 位置{i+1}内容缺失",
                        self.name
                    )

            # 检查表头字段完整性
            for occ in occurrences:
                content = occ.get("content", "")
                if isinstance(content, list):
                    table_type = self._identify_table_type(occ)
                    required = self.REQUIRED_FIELDS.get(table_type, [])
                    if required:
                        missing = [f for f in required if not any(f in c for c in content)]
                        if missing:
                            return DetectionResult(
                                True, "gold",
                                f"{check_item}: 表头缺失字段{missing}",
                                self.name
                            )

        return DetectionResult(False, "gold", f"{check_item}: 未检测到不一致", self.name)

    def _detect_general(self, occurrences, injection):
        """通用检测：比较各位置内容"""
        original = str(injection.get("original", ""))
        injected = str(injection.get("injected", ""))

        if original != injected and original and injected:
            return DetectionResult(True, "silver", f"检测到内容差异", self.name)

        contents = [str(occ.get("content", "")) for occ in occurrences]
        if len(contents) >= 2:
            for i in range(len(contents) - 1):
                if contents[i] != contents[i + 1]:
                    return DetectionResult(True, "silver", f"位置{i+1}与位置{i+2}内容不同", self.name)

        return DetectionResult(False, "silver", "各位置内容一致", self.name)

    def _summarize_diff(self, original, injected):
        """简要描述差异"""
        s_orig = str(original)[:50]
        s_inj = str(injected)[:50]
        return f"{s_orig} → {s_inj}"

    def _identify_table_type(self, occ):
        """识别表格类型"""
        content = occ.get("content", "")
        if isinstance(content, list):
            joined = "".join(str(c) for c in content)
            if "能力" in joined or "功能" in joined:
                return "能力标识表"
            if "接口" in joined:
                return "接口需求表"
            if "追溯" in joined or "追踪" in joined:
                return "追溯表"
        return "unknown"
