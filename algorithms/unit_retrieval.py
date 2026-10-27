"""单元检索核心: 结构单元多向量索引 + 统一打分 + 通道路由.

统一架构(术语收敛到5个核心概念):
  单元(unit)       : 文档内容的结构原子 —— 图=节点, 表=行, 文=块
  标题单元(title)  : caption作为单元集合的首位
  单元检索         : chunk→单元向量集合, score=top-k均值聚合(gate可选)
  通道路由(route)  : max(zscore(单向量), zscore(单元)) —— 无参数组合
  锚点(anchor)     : 数据概念, VSDX矢量源解析的图结构

两个实例(同一类, 不同参数):
  图实例: 单元=锚点节点, gate=False(节点与标题地位对等), min_units=3
  表实例: 单元=表格行,   gate=True (表标题判别力强需显式门), min_units=1

打分公式(唯一):
  sims = 单元矩阵 @ 查询向量
  score = max(sims[0], top-k均值)   若gate
        = top-k均值                 若无gate
  ——图实例=纯top-3(与VA-ColPali原行为逐位一致),
    表实例=max(caption, top-3)(与Table-Pali原行为逐位一致).

评测结论(见 data_assets/va_colpali_eval.json / table_late_eval.json):
  图: 0.567/0.812 vs 单向量桥 0.515/0.776; 大结构(≥10节点) 0.898 vs 0.816
  表caption级: ROUTE 0.847/0.942(保住dense);
  表深行: ROUTE 0.522/0.865 vs dense 0.108/0.297(截断盲区)

硬规则遵从: 模块顶层零I/O(全部惰性), open()显式utf-8, 失败显式记录.
"""
from __future__ import annotations

import json
import pickle
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parents[1]
SRS_CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"

QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："  # BGE检索指令前缀(与hybrid_recall一致)
TOP_K = 1          # k=1+IDF(特异性加权MaxSim)——双模态扫描后的统一最优; k=3仅在无IDF时次优
ROW_TEXT_LEN = 150
MAX_ROWS = 120  # V3: 截断审计后从50扩到120(零表触及边界)

# 单元提取器签名: chunks列表 → {chunk_id: [标题单元, *内容单元]}
UnitExtractor = Callable[[list[dict]], dict[str, list[str]]]


# ── 组合规则(跨模态通用) ───────────────────────────────

def zscore(x: np.ndarray) -> np.ndarray:
    """列z-score(全常数时返回0, 与既有评测口径一致)."""
    sd = float(x.std())
    return (x - x.mean()) / (sd if sd > 1e-8 else 1.0)


def route_combine(dense_scores: np.ndarray, unit_scores: np.ndarray,
                  dense_weight: float = 0.8) -> np.ndarray:
    """通道路由: max(dense_weight·z(dense), z(unit)) —— 单元通道优先.

    机制: 每个查询自动路由到证据更强的通道——标题级查询在单向量上
    z-score高, 深内容查询在单元级上z-score高. dense_weight<1为阻尼:
    单向量通道是场景依赖的(caption级强/深行崩塌), 单元通道跨场景
    均匀(两场景≈0.74/0.90), 故以单元通道为锚、单向量为辅助.

    权衡(dense_weight=1.0 vs 0.8, 4-fold实测):
      caption级: 0.843/0.946 vs 0.804/0.940 (阻尼损3.9 R@1)
      深行:      0.631/0.919 vs 0.757/0.937 (阻尼增12.6 R@1, 反超纯TP)
    """
    return np.maximum(dense_weight * zscore(dense_scores),
                      zscore(unit_scores))


# ── 表单元提取(表头式+键值式全兼容) ───────────────────

_TAG = re.compile(r"<[^>]+>")
_TH = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _cell_text(inner: str) -> str:
    return _TAG.sub("", inner).strip()


def parse_table(html: str) -> tuple[list[str], list[list[str]]]:
    """HTML表格→(表头列表, 行单元格列表).

    兼容: th/td带属性(colspan等), 无thead的键值式用例表
    (GJB 438C用例描述表无表头, 单元格自含"字段名：值").
    解析覆盖: 1207/1207表(表头式433 + 键值式774, 共11216行).
    """
    headers = [_cell_text(h) for h in _TH.findall(html)]
    body = html.split("</thead>")[1] if "</thead>" in html else html
    rows: list[list[str]] = []
    for tr in _TR.findall(body):
        cells = [c for c in (_cell_text(td) for td in _TD.findall(tr)) if c]
        if cells:
            rows.append(cells)
    return headers, rows


def table_unit_texts(chunk: dict) -> list[str]:
    """表chunk→单元文本列表(首元素=表标题, 标题单元).

    表头式表: "表头1=值1 表头2=值2"; 键值式表: 单元格原文join.
    """
    headers, rows = parse_table(chunk.get("text") or "")
    cap = str(chunk.get("table_caption")
              or chunk.get("meta", {}).get("caption", ""))[:80]
    out: list[str] = []
    if cap:
        out.append(cap)
    for r in rows[:MAX_ROWS]:
        if headers and len(r) == len(headers):
            out.append(" ".join(f"{h}={c}" for h, c in zip(headers, r))[:ROW_TEXT_LEN])
        else:
            out.append(" ".join(r)[:ROW_TEXT_LEN])
    return out


def table_unit_extractor(chunks: list[dict]) -> dict[str, list[str]]:
    """表模态的单元提取器: {cid: [标题, *行]}."""
    return {c["chunk_id"]: table_unit_texts(c)
            for c in chunks
            if c.get("type") == "table" and c.get("chunk_id")}


# ── 统一索引与打分 ─────────────────────────────────────

class UnitIndex:
    """单元级多向量索引: chunk_id → 单元向量矩阵(首行=标题单元).

    参数:
      extract: 单元提取器(chunks→{cid: [标题, *单元]})
      gate: True时打分=max(标题相似度, top-k均值); False时纯top-k均值
      idf: True时单元相似度乘以特异性权重 log(1+N/df)——
           常见单元("序号=1"/"用户"类万金油文本)被压制,
           深行/特定实体的匹配被放大(k=1+IDF为双模态统一最优)
      cmsc_fuse: >0时启用CMSC跨模态对齐融合(默认0=关)——
           fused_sims = sim_bge + λ·cos(proj_a(query), proj_b(单元)),
           CMSC投影头(models/cmsc_projection.pt, 3724跨模态对预训练)
           决定"哪个单元是对齐命中", BGE决定语义强度.
           图实例λ=0.3(+3.8 R@1, 跨模态场景); 表实例=0
           (深行为同模态匹配, BGE更强, 负结果已记录).
      top_k / min_units / cache_path: 聚合宽度/最小单元数/磁盘缓存
    惰性构建; 矩阵+IDF(+CMSC投影)持久化pkl(format v3); 查询侧加前缀.
    """

    def __init__(self, extract: UnitExtractor, *, gate: bool,
                 top_k: int = TOP_K, idf: bool = True,
                 cmsc_fuse: float = 0.0,
                 title_concat: bool = False,
                 fuzzy_idf: float | None = None,
                 min_units: int = 1,
                 cache_path: Path | None = None,
                 use_cache: bool = True, label: str = "") -> None:
        self._extract = extract
        self.gate = gate
        self.top_k = top_k
        self.idf = idf
        self.cmsc_fuse = cmsc_fuse
        self.title_concat = title_concat
        self.fuzzy_idf = fuzzy_idf
        self.min_units = min_units
        self.cache_path = cache_path or (
            BASE / f"data/gjb_438c/blackboard/unit_index_{label or 'default'}.pkl")
        self.use_cache = use_cache
        self.label = label
        self.mode = "unavailable"
        self.last_error = ""
        self.stats: dict[str, Any] = {"n_indexed": 0, "n_units": 0,
                                      "build_s": 0.0, "n_cache_hits": 0,
                                      "cmsc_active": False,
                                      "fuzzy_pool_computations": 0}
        self._ready = False
        self._bge: Any = None
        self._proj: Any = None
        self._mats: dict[str, np.ndarray] = {}
        self._idf: dict[str, np.ndarray] = {}
        self._cmsc: dict[str, np.ndarray] = {}
        self._raw_mats: dict[str, np.ndarray] = {}
        self._fuzzy_cache: dict[tuple, np.ndarray] = {}

    def ensure(self) -> str:
        """初始化并返回mode("ok"|"unavailable")."""
        if self._ready:
            return self.mode
        self._ready = True
        try:
            from algorithms.common.bge_local import BgeLocal
            self._bge = BgeLocal(cache_path=None)
        except ImportError as e:
            self.last_error = f"bge_local unavailable: {e}"
            return self.mode
        if self._bge.ensure() == "unavailable":
            self.last_error = self._bge.last_error
            return self.mode
        if self.cmsc_fuse > 0:
            from algorithms.unit_attention import CmscProjector  # noqa: PLC0415
            self._proj = CmscProjector()
            if not self._proj.ensure():
                self.last_error = f"cmsc disabled: {self._proj.last_error}"
                self._proj = None
        if self.use_cache and self._load_cache():
            self.mode = "ok"
            return self.mode
        t0 = time.time()
        try:
            self._build()
        except (OSError, ValueError, KeyError) as e:
            self.last_error = f"index build failed: {e}"
            return self.mode
        self.stats["build_s"] = round(time.time() - t0, 1)
        self.mode = "ok"
        return self.mode

    def _load_cache(self) -> bool:
        if not self.cache_path.exists():
            return False
        try:
            with open(self.cache_path, "rb") as f:
                data = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, OSError) as e:
            self.last_error = f"cache unreadable: {e}"
            return False
        if isinstance(data, dict) and data.get("format") in (2, 3, 4):
            mats = data.get("mats", {})
            idfs = data.get("idf", {})
            if not (isinstance(mats, dict) and mats and all(
                    isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] == 1024
                    for v in mats.values())):
                return False
            if data.get("format") == 3 and self.cmsc_fuse > 0:
                cmsc = data.get("cmsc", {})
                if not all(cid in cmsc and cmsc[cid].shape[0] == mats[cid].shape[0]
                           for cid in mats):
                    return False  # CMSC投影缺失/不对齐→重建
                self._cmsc = {cid: np.asarray(v, dtype=np.float32)
                              for cid, v in cmsc.items()}
                self.stats["cmsc_active"] = bool(self._cmsc)
            elif self.cmsc_fuse > 0:
                return False  # 旧格式无CMSC投影→重建
            if data.get("format") == 4 and self.fuzzy_idf is not None:
                raw = data.get("raw_mats", {})
                if not all(cid in raw for cid in mats):
                    return False  # raw矩阵缺失→重建
                self._raw_mats = {cid: np.asarray(v, dtype=np.float32)
                                  for cid, v in raw.items()}
            elif self.fuzzy_idf is not None:
                return False  # 旧格式无raw矩阵→重建
            self._mats = mats
            self._idf = {cid: np.asarray(v, dtype=np.float32)
                         for cid, v in idfs.items()
                         if cid in mats and len(v) == mats[cid].shape[0]}
            self.stats["n_cache_hits"] = len(mats)
            return True
        if isinstance(data, dict) and data and all(
                isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] == 1024
                for v in data.values()):
            if self.idf or self.cmsc_fuse > 0:
                return False  # v1缓存无对齐信息→重建
            self._mats = data
            self.stats["n_cache_hits"] = len(data)
            return True
        return False

    def _build(self) -> None:
        chunks = json.loads(SRS_CHUNKS.read_text(encoding="utf-8"))
        units_map = self._extract(chunks)
        raw_map = units_map
        if self.title_concat:
            # 标题拼接单元(先变换再编码: embed文本须与索引文本一致)
            units_map = {
                cid: [u[0]] + [f"{u[0]}。{x}" for x in u[1:]] if len(u) >= 2
                else u
                for cid, u in units_map.items()}
        texts = list({t for units in units_map.values() for t in units if t})
        vecs = self._bge.embed(texts)
        tv = {t: np.asarray(v, dtype=np.float32)
              for t, v in vecs.items() if v}
        raw_texts = list({t for units in raw_map.values()
                          for t in units if t})
        rvecs = self._bge.embed(raw_texts)
        rtv = {t: np.asarray(v, dtype=np.float32)
               for t, v in rvecs.items() if v}
        df: dict[str, int] = {}
        for units in units_map.values():
            for t in set(units):
                if t:
                    df[t] = df.get(t, 0) + 1
        n_sources = len(units_map)
        for cid, units in units_map.items():
            rows_txt = [t for t in units if t in tv]
            if len(rows_txt) < self.min_units:
                continue
            mat = np.stack([tv[t] for t in rows_txt])
            self._mats[cid] = mat / np.maximum(
                np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
            if self.idf:
                self._idf[cid] = np.asarray(
                    [np.log(1 + n_sources / df[t]) for t in rows_txt],
                    dtype=np.float32)
            if self.fuzzy_idf is not None:
                # raw行向量(不带标题): 模糊IDF度量'行泛化度', 不受表题干扰
                raw_txt = [t for t in raw_map.get(cid, units) if t in rtv]
                if raw_txt:
                    rmat = np.stack([rtv[t] for t in raw_txt])
                    self._raw_mats[cid] = rmat / np.maximum(
                        np.linalg.norm(rmat, axis=1, keepdims=True), 1e-8)
            if self.cmsc_fuse > 0 and self._proj is not None:
                pm = self._proj.project_units(self._mats[cid])
                if pm is not None:
                    self._cmsc[cid] = pm
        self.stats["n_indexed"] = len(self._mats)
        self.stats["n_units"] = int(sum(m.shape[0] for m in self._mats.values()))
        self.stats["cmsc_active"] = bool(self._cmsc)
        if self.use_cache and self._mats:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            fmt = 4 if self._raw_mats else (
                3 if (self.cmsc_fuse > 0 and self._cmsc) else 2)
            with open(self.cache_path, "wb") as f:
                pickle.dump({"format": fmt, "mats": self._mats,
                             "idf": self._idf, "cmsc": self._cmsc,
                             "raw_mats": self._raw_mats}, f)

    def score(self, query: str, cand_ids: list[str]) -> dict[str, float]:
        """query对候选chunk的单元级分数(统一公式, gate/idf/cmsc按参数).

        CMSC融合: fused = sim_bge + λ·cos(proj_a(q), proj_b(u)),
        融合先于IDF加权与top-k聚合.
        未建索引的候选不返回(调用方负责单向量通道兜底).
        """
        mode = self.ensure()
        if mode != "ok" or not query:
            return {}
        qvec = self._bge.embed([QUERY_PREFIX + query[:200]])
        q = qvec.get(QUERY_PREFIX + query[:200])
        if not q:
            return {}
        qn = np.asarray(q, dtype=np.float32)
        qn = qn / max(float(np.linalg.norm(qn)), 1e-8)
        qc = None
        if self.cmsc_fuse > 0 and self._proj is not None and self._cmsc:
            qc = self._proj.project_query(qn)
        pool_fuzzy = self._pool_fuzzy_weights(cand_ids)
        out: dict[str, float] = {}
        for cid in cand_ids:
            mat = self._mats.get(cid)
            if mat is None:
                continue
            sims = mat @ qn
            if qc is not None and cid in self._cmsc:
                sims = sims + self.cmsc_fuse * (self._cmsc[cid] @ qc)
            if pool_fuzzy is not None and cid in pool_fuzzy:
                # 池相对模糊IDF替代静态精确IDF(实验: 替代0.394 vs 叠乘0.316)
                sims = sims * pool_fuzzy[cid]
            else:
                w = self._idf.get(cid)
                if self.idf and w is not None:
                    sims = sims * w
            k = min(self.top_k, len(sims))
            topk = float(np.sort(sims)[-k:].mean())
            out[cid] = max(float(sims[0]), topk) if self.gate else topk
        return out

    def _pool_fuzzy_weights(self, cand_ids: list[str]) -> dict[str, np.ndarray] | None:
        """池相对模糊IDF: 候选池内near-dup df(查询期计算, 池级缓存).

        机制(错误分析驱动): 精确IDF只压制完全重复单元; GJB同构表
        (同表头族/用例E行)的near-dup行(余弦>th)是排序失败主因
        (76.9%失败为排序失败, 干扰54%同文档同构+46%跨文档同构).
        池相对: IDF本质是竞争相对性——对实际候选池计算.
        缓存: 同池(相同cand_ids元组)只算一次.
        """
        if self.fuzzy_idf is None or not cand_ids:
            return None
        key = tuple(cand_ids)
        if key in self._fuzzy_cache:
            return self._fuzzy_cache[key]
        src = self._raw_mats if self._raw_mats else self._mats
        mats = [(cid, src[cid]) for cid in cand_ids if cid in src]
        if not mats:
            return None
        self.stats["fuzzy_pool_computations"] += 1
        big = np.concatenate([m for _, m in mats], axis=0)
        owner = np.concatenate([
            np.full(m.shape[0], i, dtype=np.int64)
            for i, (_, m) in enumerate(mats)])
        n = len(mats)
        sims = big @ big.T
        np.fill_diagonal(sims, -1.0)
        near = sims > self.fuzzy_idf
        del sims
        out: dict[str, np.ndarray] = {}
        off = 0
        for i, (cid, m) in enumerate(mats):
            fd = np.empty(m.shape[0], dtype=np.float32)
            for r_local in range(m.shape[0]):
                r = off + r_local  # 全局行下标(跨chunk拼接偏移)
                ch = set(int(owner[j]) for j in np.nonzero(near[r])[0])
                ch.add(i)
                fd[r_local] = np.log(1 + n / len(ch))
            out[cid] = fd
            off += m.shape[0]
        self._fuzzy_cache[key] = out
        return out

    @property
    def indexed_ids(self) -> list[str]:
        """已建单元索引的chunk_id列表(惰性, 不触发构建)."""
        return list(self._mats)
