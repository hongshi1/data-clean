#!/usr/bin/env python3
"""语义层检测器 — 术语一致性(盲测协议)

只看occurrences_injected,不碰injection元数据。
技术: 编辑距离 / 同义词检测 / 集合比较 / 缩写检测
"""
from algorithms.base import BaseDetector, DetectionResult


class TermChecker(BaseDetector):
    """语义层检测器 — 术语一致性"""

    SYNONYM_GROUPS = [
        {"获取", "采集"}, {"管理", "管控"}, {"监控", "监测"}, {"处理", "处置"},
        {"传输", "传送"}, {"存储", "保存"}, {"查询", "检索"}, {"注册", "登记"},
        {"部署", "安装"}, {"启动", "开启"}, {"关闭", "停止"}, {"删除", "移除"},
        {"修改", "变更"}, {"添加", "新增"}, {"配置", "设置"}, {"加载", "载入"},
    ]

    def __init__(self, expert_knowledge=None, sim_threshold=0.85):
        super().__init__("semantic", expert_knowledge)
        self.sim_threshold = sim_threshold

    def detect(self, blind_entry: dict) -> DetectionResult:
        occurrences = blind_entry.get("occurrences", [])
        if not occurrences:
            return DetectionResult(False, "silver", "无内容", self.name)

        # 提取各位置可比内容
        contents = []
        for occ in occurrences:
            content = occ.get("content", "")
            if isinstance(content, str) and content.strip():
                contents.append(content.strip())
            elif isinstance(content, list):
                contents.append([str(c).strip() for c in content])
            elif isinstance(content, dict):
                contents.append(content)

        strs = [c for c in contents if isinstance(c, str)]
        lists = [c for c in contents if isinstance(c, list)]
        dicts = [c for c in contents if isinstance(c, dict)]

        # 集合比较(TERM-03枚举缺失): list vs list
        if len(lists) >= 2:
            for i in range(len(lists) - 1):
                a, b = set(lists[i]), set(lists[i + 1])
                if a != b:
                    diff = a.symmetric_difference(b)
                    return DetectionResult(
                        True, "silver",
                        f"枚举集合不一致(差异: {list(diff)[:3]})",
                        self.name, technique="setdiff")

        # 字符串两两比较(TERM-01/02/04/05/07/08)
        if len(strs) >= 2:
            for i in range(len(strs)):
                for j in range(i + 1, len(strs)):
                    a, b = strs[i], strs[j]
                    if a == b:
                        continue
                    # 同义词对
                    if self._is_synonym_pair(a, b):
                        return DetectionResult(
                            True, "silver",
                            f"'{a[:20]}'与'{b[:20]}'同义异名",
                            self.name, technique="synonym")
                    # 缩写关系(一方是另一方的编码/缩写)
                    if self._is_abbreviation_pair(a, b):
                        return DetectionResult(
                            True, "silver",
                            f"'{a[:20]}'与'{b[:20]}'全称/缩写混用",
                            self.name, technique="abbrev")
                    # 编辑距离
                    sim = self.text_sim(a, b)
                    if sim < self.sim_threshold:
                        return DetectionResult(
                            True, "silver",
                            f"'{a[:20]}'与'{b[:20]}'表述不一致(相似度{sim:.2f})",
                            self.name, technique="editdist")
                    # 同名但定义后缀不同(TERM-02): 同前缀+不同括号定义
                    if self._is_homonym_pair(a, b):
                        return DetectionResult(
                            True, "silver",
                            f"'{a[:20]}'与'{b[:20]}'同名不同义",
                            self.name, technique="homonym")

        # dict比较(接口属性)
        if len(dicts) >= 2:
            for i in range(len(dicts) - 1):
                if dicts[i] != dicts[i + 1]:
                    diff_keys = [k for k in set(dicts[i]) | set(dicts[i + 1])
                                 if dicts[i].get(k) != dicts[i + 1].get(k)]
                    return DetectionResult(
                        True, "silver",
                        f"属性不一致(字段: {diff_keys[:3]})",
                        self.name, technique="attrdiff")

        return DetectionResult(False, "silver", "各位置术语一致", self.name)

    def _is_synonym_pair(self, a, b):
        for group in self.SYNONYM_GROUPS:
            for w1 in group:
                for w2 in group:
                    if w1 != w2 and w1 in a and w2 in b:
                        if a.replace(w1, w2) == b or b.replace(w2, w1) == a:
                            return True
        return False

    def _is_abbreviation_pair(self, a, b):
        # 一方是纯十六进制/大写字母编码,另一方是中文 → 全称/缩写混用
        import re
        code_re = re.compile(r'^[0-9A-F]{4,}$|^[A-Z]{2,8}$')
        is_cn_a = bool(re.search(r'[\u4e00-\u9fa5]', a))
        is_cn_b = bool(re.search(r'[\u4e00-\u9fa5]', b))
        if (code_re.match(a) and is_cn_b) or (code_re.match(b) and is_cn_a):
            return True
        return False

    def _is_homonym_pair(self, a, b):
        # 同名+不同括号定义,如"安全模式（低功耗）"vs"安全模式（故障保护）"
        import re
        pa = re.match(r'^(.+?)（(.+?)）$', a)
        pb = re.match(r'^(.+?)（(.+?)）$', b)
        if pa and pb:
            return pa.group(1) == pb.group(1) and pa.group(2) != pb.group(2)
        # 一方带定义括号,另一方是裸名且是前者的前缀
        if pa and not pb and pb is not None:
            return pa.group(1) == b
        return False
