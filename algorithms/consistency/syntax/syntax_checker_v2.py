#!/usr/bin/env python3
"""语法层检测器 — GJB规则驱动(盲测协议)

只看occurrences_injected,不碰injection元数据。
技术: fieldcheck / missing / fuzzy / dupcheck
"""
import re
from algorithms.base import BaseDetector, DetectionResult


class SyntaxChecker(BaseDetector):
    """语法层检测器 — GJB合规"""

    REQUIRED_FIELDS = {
        "能力标识表": ["序号", "标识符", "描述", "优先级"],
        "接口需求表": ["名称", "发送方", "接收方", "类型"],
        "追溯表": ["需求标识符", "测试标识符"],
    }

    # 模糊需求模式(GJB-01可测试性): 无量化指标的表述
    FUZZY_PATTERNS = [
        r'运行稳定', r'性能良好', r'高可靠', r'快速响应',
        r'系统应.{0,6}(良好|稳定|优秀|可靠)(?![，。]*\d)',
    ]

    def __init__(self, expert_knowledge=None):
        super().__init__("syntax", expert_knowledge)

    def detect(self, blind_entry: dict) -> DetectionResult:
        occurrences = blind_entry.get("occurrences", [])
        if not occurrences:
            return DetectionResult(False, "gold", "无内容", self.name)

        # 1. 表头字段完整性(GJB-02~11的机器可检部分)
        header_result = self._check_headers(occurrences)
        if header_result:
            return header_result

        # 2. 内容缺失: 同实体某位置内容为空/明显短于其他位置
        missing_result = self._check_missing(occurrences)
        if missing_result:
            return missing_result

        # 3. 模糊需求(GJB-01)
        fuzzy_result = self._check_fuzzy(occurrences)
        if fuzzy_result:
            return fuzzy_result

        # 4. 通用内容对比(list/dict差异)
        diff_result = self._check_content_diff(occurrences)
        if diff_result:
            return diff_result

        return DetectionResult(False, "gold", "GJB合规", self.name)

    def _check_headers(self, occurrences):
        """表头字段完整性检查"""
        for occ in occurrences:
            content = occ.get("content", "")
            if not isinstance(content, list):
                continue
            joined = "".join(str(c) for c in content)
            # 识别表格类型
            table_type = None
            if "Use case" in joined or "功能名称" in joined or "能力" in joined:
                table_type = "能力标识表"
            elif "发送方" in joined or "接收方" in joined:
                table_type = "接口需求表"
            elif "追溯" in joined or "追踪" in joined:
                table_type = "追溯表"

            if not table_type:
                continue
            required = self.REQUIRED_FIELDS.get(table_type, [])
            # 字段名宽松匹配(原文可能有空格变体"方式 名称")
            norm = joined.replace(" ", "")
            missing = [f for f in required
                       if f not in norm and not any(
                           f.replace(" ", "") in str(c).replace(" ", "")
                           for c in content)]
            if missing:
                return DetectionResult(
                    True, "gold",
                    f"{table_type}缺失必填字段: {missing}",
                    self.name, technique="fieldcheck")

        # 同实体不同位置表头列不一致
        headers = [tuple(str(c) for c in occ["content"])
                   for occ in occurrences if isinstance(occ.get("content"), list)]
        if len(headers) >= 2:
            base = None
            for h in headers:
                if base is not None and h != base:
                    return DetectionResult(
                        True, "gold",
                        f"同实体表头列不一致: {base[:4]}... vs {h[:4]}...",
                        self.name, technique="headerdiff")
                base = h
        return None

    def _check_missing(self, occurrences):
        """内容缺失检查: 同实体某位置为空/异常短"""
        str_contents = [(i, occ.get("content", ""))
                        for i, occ in enumerate(occurrences)
                        if isinstance(occ.get("content"), str)]
        if len(str_contents) >= 2:
            lengths = [len(c.strip()) for _, c in str_contents]
            max_len = max(lengths)
            for (i, c), length in zip(str_contents, lengths):
                if max_len >= 8 and length <= max(2, max_len // 4):
                    return DetectionResult(
                        True, "gold",
                        f"位置{i+1}内容疑似缺失(长度{length} vs 最长{max_len})",
                        self.name, technique="missing")

        # list内容: 同实体某位置比其他位置少元素
        list_contents = [(i, occ.get("content", []))
                         for i, occ in enumerate(occurrences)
                         if isinstance(occ.get("content"), list)]
        if len(list_contents) >= 2:
            lens = [len(c) for _, c in list_contents]
            max_l = max(lens)
            for (i, c), length in zip(list_contents, lens):
                if max_l >= 3 and length < max_l:
                    return DetectionResult(
                        True, "gold",
                        f"位置{i+1}条目缺失({length}项 vs 最长{max_l}项)",
                        self.name, technique="missing")
        return None

    def _check_fuzzy(self, occurrences):
        """模糊需求检测(GJB-01)"""
        for i, occ in enumerate(occurrences):
            content = occ.get("content", "")
            text = str(content)
            for pat in self.FUZZY_PATTERNS:
                if re.search(pat, text) and not re.search(r'\d', text):
                    return DetectionResult(
                        True, "gold",
                        f"位置{i+1}存在不可测试的模糊表述: '{text[:30]}'",
                        self.name, technique="fuzzy")
        return None

    def _check_content_diff(self, occurrences):
        """通用内容对比"""
        dicts = [occ.get("content", {}) for occ in occurrences
                 if isinstance(occ.get("content"), dict)]
        if len(dicts) >= 2:
            for i in range(len(dicts) - 1):
                if dicts[i] != dicts[i + 1]:
                    diff_keys = [k for k in set(dicts[i]) | set(dicts[i + 1])
                                 if dicts[i].get(k) != dicts[i + 1].get(k)]
                    return DetectionResult(
                        True, "gold",
                        f"属性不一致(字段: {diff_keys[:3]})",
                        self.name, technique="attrdiff")
        return None
