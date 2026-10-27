"""图模态的单元检索实例(门面). 核心实现见 algorithms/unit_retrieval.py.

图实例参数:
  单元=锚点节点文字+VLM key_elements, 标题=VLM caption
  gate=False, top_k=1, idf=True(特异性加权MaxSim)
  +CMSC跨模态融合λ=0.3: fused=sim_bge+0.3·cos(proj_a(q), proj_b(u))
   (CMSC双塔投影头3724跨模态对预训练, 选"哪个单元是对齐命中";
    VLM元素单元补足无锚点图的覆盖(378/381), 与锚点互为冗余证据)

术语说明: 本模块原名VA-ColPali(Vector-Anchor ColPali), 重构后收敛为
"单元检索的图实例"——节点级多向量+后期交互. 历史名词保留在
docs/srs_project/18_feature_extraction_late_interaction_report.md.

评测数字(evalset_v3, 4-fold, 工具 tools/eval_va_colpali.py):
  图实例 0.619/0.846/0.716 vs 单向量桥 0.515/0.776/0.626
  (多角度扫描: k=1+IDF统一最优; VLM元素单元+2.0 R@5;
   k=2无IDF为R@1次优0.597; 与dense融合/RRF均稀释, 弃用)

硬规则遵从: 模块顶层零I/O, open()显式utf-8.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from algorithms.unit_retrieval import UnitIndex

BASE = Path(__file__).resolve().parents[1]
ANCHORS_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
IMG_ANCHOR_MAP = BASE / "data/gjb_438c/data_assets/va_colpali_img_anchor_map.json"
SRS_IMAGE_ANALYSES = BASE / "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"
DEFAULT_CACHE = BASE / "data/gjb_438c/blackboard/va_colpali_index.pkl"

MIN_NODES = 3  # 参与索引的最少单元数(含标题)
MAX_ELEMENTS = 12  # 每图VLM key_elements单元上限


def _vlm_by_chunk(images: list[dict]) -> dict[str, tuple[str, list[str]]]:
    """VLM转写→{cid: (caption, key_elements)}(doc+fig编号双键对齐).

    防跨文档同名fig错配; 返回标题单元与元素单元两类素材.
    """
    if not SRS_IMAGE_ANALYSES.exists():
        return {}
    vlm = json.loads(SRS_IMAGE_ANALYSES.read_text(encoding="utf-8"))
    by_doc_fig = {}
    for c in images:
        by_doc_fig[(c.get("doc", ""), c.get("image_path", ""))] = c
    out: dict[str, tuple[str, list[str]]] = {}
    for a in vlm.get("analyses", []):
        m = re.search(r"(fig_\d+\.png)$", a.get("image_path", ""))
        if not m:
            continue
        c = by_doc_fig.get((a.get("doc", ""), "images/" + m.group(1)))
        if not c:
            continue
        cap = a.get("caption", [])
        cap_s = " ".join(cap) if isinstance(cap, list) else str(cap)
        elements = [e for e in
                    a.get("analysis", {}).get("key_elements", [])[:MAX_ELEMENTS]
                    if e]
        out[c["chunk_id"]] = (cap_s[:100] if cap_s.strip() else "", elements)
    return out


def image_unit_extractor(chunks: list[dict]) -> dict[str, list[str]]:
    """图模态单元提取器: chunk列表→{cid: [标题, *单元]}.

    单元来源(并集, 互为冗余证据):
      ① 锚点节点文字(VSDX矢量源, 零OCR误差, 需img_anchor_map映射)
      ② VLM key_elements(有噪声但覆盖无锚点图)
    无任何单元来源的图不出现在结果中(调用方走单向量通道兜底).
    """
    images = [c for c in chunks if c.get("type") == "image"
              and c.get("chunk_id") and c.get("doc")]
    img_map = json.loads(IMG_ANCHOR_MAP.read_text(encoding="utf-8"))
    av2 = json.loads(ANCHORS_V2.read_text(encoding="utf-8"))
    doc_structs: dict[str, dict[str, dict]] = {}
    for dn, d in av2.items():
        doc_structs[dn[:2]] = {s.get("embed_index", ""): s
                               for s in d.get("structures", [])}
    vlm = _vlm_by_chunk(images)
    out: dict[str, list[str]] = {}
    for c in images:
        cid = c["chunk_id"]
        cap, elements = vlm.get(cid, ("", []))
        units: list[str] = [cap] if cap else []
        info = img_map.get(cid)
        if info:
            s = doc_structs.get(cid[:2], {}).get(info.get("embed_index", ""))
            if s:
                units.extend(n["text"][:100] for n in s.get("nodes", [])
                             if n.get("text"))
        units.extend(elements)
        units = [u for u in units if u]
        if units:
            out[cid] = units
    return out


def _captions_by_chunk(images: list[dict]) -> dict[str, str]:
    """向后兼容: 仅返回caption映射."""
    return {cid: cap for cid, (cap, _) in _vlm_by_chunk(images).items()}


CMSC_FUSE = 0.0  # 审计修正: 全量预训练投影头含测试fold实体对(泄漏上界+3.8);
# 按折重训真实增益+2.3(p=0.026, 见21号文档§六); 正式按折集成待办, 默认关闭


class VaColpaliIndex:
    """图单元索引(门面): UnitIndex(gate=False, k=1, idf)."""

    def __init__(self, cache_path: Path | None = None,
                 use_cache: bool = True) -> None:
        self._idx = UnitIndex(image_unit_extractor, gate=False,
                              top_k=1, idf=True, cmsc_fuse=CMSC_FUSE,
                              min_units=MIN_NODES,
                              cache_path=cache_path or DEFAULT_CACHE,
                              use_cache=use_cache, label="va")

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
        s["n_images"] = s["n_indexed"]
        return s

    @property
    def indexed_ids(self) -> list[str]:
        return self._idx.indexed_ids

    @staticmethod
    def _captions_by_chunk(images: list[dict]) -> dict[str, str]:
        return _captions_by_chunk(images)
