"""结构化查询路由(SQR) + 章节感知过滤 + 精排.

SQR: 从查询中提取确定性信号(图号/表号/章节号/实体名), 直接解析
     而非走向量检索——确定性问题用确定性方案.

章节感知: 查询提章节→候选池缩减到该章节的图.

精排: 融合top-K后用BGE-Reranker cross-encoder精排(模型本地就位).

三者可独立开关, 也可组合(组合=推荐配置).
"""
from __future__ import annotations

import re
from typing import Any


# ── SQR正则模式 ──────────────────────────────────────────

_FIG_PAT = re.compile(r"图\s*(\d+)")
_TABLE_PAT = re.compile(r"表\s*(\d+)")
_SEC_PAT = re.compile(r"(\d+\.\d+(?:\.\d+)*(?:\.\d+)?)")
_ENTITY_PAT = re.compile(r"[「『]([^」』\s]{2,20})[」』]")


def extract_structured_signals(query: str) -> dict[str, Any]:
    """从查询中提取确定性信号.

    返回: {fig_num, table_num, section, entity, chapter}
    """
    signals: dict[str, Any] = {}
    m = _FIG_PAT.search(query)
    if m:
        signals["fig_num"] = int(m.group(1))
    m = _TABLE_PAT.search(query)
    if m:
        signals["table_num"] = int(m.group(1))
    # 章节: 取最长匹配
    secs = _SEC_PAT.findall(query)
    if secs:
        signals["section"] = max(secs, key=len)
    # 实体名(「」内的引用)
    m = _ENTITY_PAT.search(query)
    if m:
        signals["entity"] = m.group(1)
    # 文档/系统名(查询前缀)
    for prefix in ("数据获取", "界面集成", "服务集成", "数据统一",
                   "软件部署", "运行支撑", "报文处理", "数据运行",
                   "数据同步", "动态名录", "语音综合", "文电处理",
                   "统一传输", "传输服务", "实时信息", "流媒体"):
        if prefix in query:
            signals["doc_prefix"] = prefix
            break
    return signals


class StructuredQueryRouter:
    """SQR: 确定性信号→直接解析(不走向量)."""

    def __init__(self, chunks: list[dict]) -> None:
        self.chunks = chunks
        self.images = [c for c in chunks if c.get("type") == "image"]
        # 索引: fig号→image chunk
        self._fig_index: dict[int, list] = {}
        for c in self.images:
            m = re.search(r"fig_(\d+)", c.get("image_path", ""))
            if m:
                self._fig_index.setdefault(int(m.group(1)), []).append(c)
        # 索引: 表号→table chunk(表标题里的"表N")
        self.tables = [c for c in chunks if c.get("type") == "table"]
        self._table_index: dict[int, list] = {}
        for c in self.tables:
            m = re.search(r"表\s*(\d+)", c.get("table_caption", "")
                          or c.get("meta", {}).get("caption", ""))
            if m:
                self._table_index.setdefault(int(m.group(1)), []).append(c)
        # 章节→image chunks
        from collections import defaultdict
        self._sec_index: dict = defaultdict(list)
        for c in self.images:
            self._sec_index[c.get("section", "")].append(c)

    def route(self, query: str) -> list[dict] | None:
        """确定性路由: 能解析→返回匹配chunks; 不能→None(走向量)."""
        signals = extract_structured_signals(query)
        results = []

        # 图号直查
        if "fig_num" in signals:
            figs = self._fig_index.get(signals["fig_num"], [])
            if figs:
                results.extend(figs)

        # 表号直查(表号查询不再走向量, SQR覆盖扩展)
        if "table_num" in signals:
            tabs = self._table_index.get(signals["table_num"], [])
            if tabs:
                results.extend(tabs)

        # 章节直查
        if "section" in signals:
            # 精确章节匹配 + 前缀匹配
            exact = self._sec_index.get(signals["section"], [])
            if exact:
                results.extend(exact)
            else:
                # 前缀匹配(查询提父章节)
                for sec, imgs in self._sec_index.items():
                    if sec.startswith(signals["section"]):
                        results.extend(imgs)

        # 去重
        seen = set()
        deduped = []
        for c in results:
            if c["chunk_id"] not in seen:
                seen.add(c["chunk_id"])
                deduped.append(c)

        if deduped:
            return deduped[:5]  # 最多返回5个确定性结果
        return None

    def filter_candidates(self, query: str,
                          candidates: list[dict]) -> list[dict]:
        """章节感知过滤: 查询提章节→候选缩减到该章节."""
        signals = extract_structured_signals(query)
        if "section" not in signals:
            return candidates
        sec = signals["section"]
        # 先看精确匹配
        filtered = [c for c in candidates
                    if c.get("section", "").startswith(sec)]
        if filtered:
            return filtered
        # 前缀匹配(父章节)
        parent = ".".join(sec.split(".")[:-1]) if "." in sec else sec
        filtered = [c for c in candidates
                    if c.get("section", "").startswith(parent)]
        return filtered if filtered else candidates
