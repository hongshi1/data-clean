"""表模态的单元检索实例(门面). 核心实现见 algorithms/unit_retrieval.py.

表实例参数:
  单元=表格行(表头式"表头=值"配对 / 键值式原文), gate=True
  top_k=1, idf=True(特异性加权MaxSim)——
  深行查询只引用一行: k=3均值稀释唯一强匹配, k=1保精确;
  IDF压制"序号=1"类万金油行, 放大特定行.

术语说明: 本模块原名Table-Pali, 重构后收敛为"单元检索的表实例".
配套组合规则route_combine(max-zscore通道路由)亦在unit_retrieval.

评测数字(双场景, 工具 tools/eval_table_late.py):
  caption级(docT5 1532对): dense 0.843/0.942, ROUTE 0.843/0.946
  深行(LLM构造111对):     dense 0.108/0.297(截断盲区),
                          纯TP 0.631/0.919, ROUTE 0.631/0.919
  (多角度扫描: RRF两场景均劣于ROUTE, 弃用)

硬规则遵从: 模块顶层零I/O, open()显式utf-8.
"""
from __future__ import annotations

from pathlib import Path

from algorithms.unit_retrieval import UnitIndex
from algorithms.unit_retrieval import parse_table  # noqa: F401  向后兼容重导出
from algorithms.unit_retrieval import route_combine  # noqa: F401
from algorithms.unit_retrieval import table_unit_texts
from algorithms.unit_retrieval import zscore  # noqa: F401

BASE = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = BASE / "data/gjb_438c/blackboard/table_pali_index.pkl"

# 向后兼容别名(原table_late.table_row_texts)
table_row_texts = table_unit_texts


def table_unit_extractor(chunks: list[dict]) -> dict[str, list[str]]:
    """表模态单元提取器(委托unit_retrieval实现)."""
    from algorithms.unit_retrieval import table_unit_extractor as _ext
    return _ext(chunks)


class TablePaliIndex:
    """表单元索引(门面). 两种配置画像:

    默认(词面友好): 原始行单元+精确IDF——v1复述式查询(拷贝行文本)
    的精确词面匹配最优(锁定数字: 深行v1 TP 0.748/ROUTE 0.757).
    语义画像(semantic): title_concat+fuzzy_idf=0.9——反拷贝语义
    查询最优(deep_v2: 0.329→0.394 R@1, +6.5).
    两者服务真实查询分布的两端(用户有时粘贴原文, 有时语义提问);
    生产路由时可并行(见route_combine).
    """

    def __init__(self, cache_path: Path | None = None,
                 use_cache: bool = True,
                 semantic_profile: bool = False) -> None:
        default = (DEFAULT_CACHE if not semantic_profile
                   else BASE / "data/gjb_438c/blackboard/"
                   "table_pali_index_semantic.pkl")
        self._idx = UnitIndex(
            table_unit_extractor, gate=True,
            top_k=1, idf=True,
            title_concat=semantic_profile,
            fuzzy_idf=0.90 if semantic_profile else None,
            cache_path=cache_path or default,
            use_cache=use_cache,
            label="table_semantic" if semantic_profile else "table")

    def ensure(self) -> str:
        return self._idx.ensure()

    def score(self, query: str, cand_ids: list[str]) -> dict[str, float]:
        return self._idx.score(query, cand_ids)

    @property
    def mode(self) -> str:
        return self._idx.mode

    @property
    def last_error(self) -> str:
        return self._idx.last_error

    @property
    def stats(self) -> dict:
        s = dict(self._idx.stats)
        s["n_tables"] = s["n_indexed"]
        s["n_rows"] = s["n_units"]
        return s

    @property
    def indexed_ids(self) -> list[str]:
        return self._idx.indexed_ids
