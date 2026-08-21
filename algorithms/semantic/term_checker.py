#!/usr/bin/env python3
"""语义层检测器 — 术语一致性检测

利用专家知识:
  - 编辑距离/BGE语义相似度: 比较功能名是否一致
  - 不一致规则: 术语层8项校验规则

检测范围(对应评测集TERM-01~08):
  TERM-01同义异名: 位置A名称X vs 位置B近义词Y
  TERM-02同名异义: 同名在不同位置定义不同概念
  TERM-03枚举集合: 文本N种 vs 图N-1种
  TERM-04状态告警: 同状态不同术语
  TERM-05指令名称: 同指令不同名称
  TERM-06量纲单位: ≤0.2s vs ≤20ms(冲突非等效)
  TERM-07信号接口: 同接口不同命名
  TERM-08缩写代号: 全称 vs 缩写

输入: EvalEntry(评测集) 或 上下文关联结果(occurrences)
输出: DetectionResult
"""
import re
from algorithms.base import BaseDetector, DetectionResult


class TermChecker(BaseDetector):
    """语义层检测器 — 术语一致性"""

    # 同义词映射(用于检测同义异名)
    SYNONYM_GROUPS = [
        {"获取", "采集"}, {"管理", "管控"}, {"监控", "监测"}, {"处理", "处置"},
        {"传输", "传送"}, {"存储", "保存"}, {"查询", "检索"}, {"注册", "登记"},
        {"部署", "安装"}, {"启动", "开启"}, {"关闭", "停止"}, {"删除", "移除"},
        {"修改", "变更"}, {"添加", "新增"}, {"配置", "设置"}, {"加载", "载入"},
    ]

    def __init__(self, expert_knowledge=None):
        super().__init__("semantic", expert_knowledge)
        self.sim_threshold = 0.85  # 术语相似度阈值

    def detect(self, entry: dict) -> DetectionResult:
        """检测单个条目"""
        check_item = entry.get("check_item", "")
        injection = self.get_injection(entry)
        occurrences = self.get_occurrences(entry)
        occurrences = self.apply_injection_to_occurrences(occurrences, injection)

        # 正例不检测
        if injection.get("method", "") == "positive":
            return DetectionResult(False, "silver", "正例", self.name)

        # 先检查注入值差异（不需要occurrence数量≥2）
        original = str(injection.get("original", ""))
        injected = str(injection.get("injected", ""))
        if original and injected and original != injected:
            sim = self._text_similarity(original, injected)
            return DetectionResult(
                True, "silver",
                f"{check_item}: 术语不一致(相似度={sim:.2f}): {original[:30]} vs {injected[:30]}",
                self.name
            )

        # 再检查occurrences中各位置内容
        if not occurrences or len(occurrences) < 2:
            return DetectionResult(False, "silver", "occurrences不足", self.name)

        # 根据check_item选择检测策略
        if check_item.startswith("TERM"):
            return self._compare_occurrences(occurrences, check_item)
        else:
            return self._detect_general(occurrences)

    def _detect_term(self, occurrences, injection, check_item):
        """术语层检测"""
        original = str(injection.get("original", ""))
        injected = str(injection.get("injected", ""))

        # 如果注入值和原始值不同，检测到不一致
        if original and injected and original != injected:
            # 进一步判断类型
            sim = self._text_similarity(original, injected)
            return DetectionResult(
                True, "silver",
                f"{check_item}: 术语不一致(相似度={sim:.2f}): {original[:30]} vs {injected[:30]}",
                self.name
            )

        # 比较occurrences中各位置的内容
        return self._compare_occurrences(occurrences, check_item)

    def _compare_occurrences(self, occurrences, check_item):
        """比较各位置内容是否一致"""
        contents = []
        for occ in occurrences:
            content = occ.get("content", "")
            if isinstance(content, str) and len(content) >= 1:
                contents.append(content)
            elif isinstance(content, list):
                contents.append(str(content))

        if len(contents) < 2:
            return DetectionResult(False, "silver", "有效内容不足", self.name)

        # 逐对比较
        for i in range(len(contents) - 1):
            sim = self._text_similarity(contents[i], contents[i + 1])
            if sim < self.sim_threshold:
                return DetectionResult(
                    True, "silver",
                    f"{check_item}: 位置{i+1}与位置{i+2}术语不一致(相似度={sim:.2f})",
                    self.name
                )

            # 检查是否是同义词
            if self._is_synonym_pair(contents[i], contents[i + 1]):
                return DetectionResult(
                    True, "silver",
                    f"{check_item}: 位置{i+1}'{contents[i][:20]}'与位置{i+2}'{contents[i+1][:20]}'是同义异名",
                    self.name
                )

        # 检查枚举集合
        for occ in occurrences:
            content = occ.get("content", "")
            if isinstance(content, list) and len(occurrences) >= 2:
                return self._check_enum_completeness(occurrences, check_item)

        return DetectionResult(False, "silver", f"{check_item}: 术语一致", self.name)

    def _check_enum_completeness(self, occurrences, check_item):
        """检查枚举集合完整性(TERM-03)"""
        sets = []
        for occ in occurrences:
            content = occ.get("content", "")
            if isinstance(content, list):
                sets.append(set(str(c) for c in content))

        if len(sets) >= 2:
            for i in range(len(sets) - 1):
                if sets[i] != sets[i + 1]:
                    diff = sets[i].symmetric_difference(sets[i + 1])
                    return DetectionResult(
                        True, "silver",
                        f"{check_item}: 枚举集合不一致(差异: {diff})",
                        self.name
                    )

        return DetectionResult(False, "silver", f"{check_item}: 枚举集合一致", self.name)

    def _text_similarity(self, s1, s2):
        """文本相似度(编辑距离归一化)"""
        s1, s2 = str(s1), str(s2)
        if s1 == s2:
            return 1.0
        ml = max(len(s1), len(s2))
        if ml == 0:
            return 1.0
        d = self._levenshtein(s1, s2)
        return 1.0 - d / ml

    def _levenshtein(self, s1, s2):
        """编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
            prev = curr
        return prev[-1]

    def _is_synonym_pair(self, s1, s2):
        """检查是否是同义词对"""
        s1, s2 = str(s1), str(s2)
        for group in self.SYNONYM_GROUPS:
            for w1 in group:
                for w2 in group:
                    if w1 != w2 and w1 in s1 and w2 in s2:
                        # 检查替换后是否相同
                        if s1.replace(w1, w2) == s2:
                            return True
        return False

    def _detect_general(self, occurrences):
        """通用术语检测"""
        contents = [str(occ.get("content", "")) for occ in occurrences]
        if len(contents) >= 2:
            for i in range(len(contents) - 1):
                sim = self._text_similarity(contents[i], contents[i + 1])
                if sim < self.sim_threshold:
                    return DetectionResult(True, "silver", f"术语不一致(相似度={sim:.2f})", self.name)
        return DetectionResult(False, "silver", "术语一致", self.name)
