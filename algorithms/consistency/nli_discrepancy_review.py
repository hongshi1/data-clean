"""分歧驱动NLI复核器: Tier1分歧 → 声明对 → NLI语义级存在性核对.

角色定位(与pair级检测正交):
  Tier1词法比对发现分歧(高召回, 不辨真假) → 本模块对每条分歧构造
  (P=表格侧存在性声明, H=图侧闭世界声明), 由NLI判断内容是否真不一致.
  NLI的语义模糊匹配恰好复核词法误报: 节点"半结构化数据源引"(截断)
  与表格项"半结构化数据源引接"在NLI眼中同指 → entailment → 误报复核.

评测任务(分歧级, 与M7/M17/M22裁决标签同粒度):
  任务1 误报复核: compiler_bug(内容实际一致, 110条) vs 真差异
       (real_bug+benign, 554条) — NLI矛盾信号应区分两者
  任务2 bug判定: real_bug(176) vs benign(378, 合理差异) — NLI理论
       上限受限于惯例知识(Actor省略/粒度取舍), 需分dtype诚实报告

dtype→声明构造(全确定性):
  TABLE_ITEM_MISSING / COMPONENT_MISSING: P=条目/组件存在性声明,
    H=图节点闭世界枚举(不预过滤 — NLI自做语义对齐)
  ACTOR/STEP/EXC_MISSING: P=用例要素存在性声明, H=图节点闭世界
  DIAGRAM_EXTRA(图有表无): P=表格闭世界条目, H=图节点闭世界
  ORDER_CONFLICT: P=表顺序声明, H=图顺序声明(方向矛盾)
  UC_NAME_MISMATCH: P=表用例名, H=图用例名(同指性判断)

依赖: 纯stdlib + nli_pair_claims复用(无torch).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from algorithms.consistency.nli_pair_claims import (
    ClaimPair,
    TABLE_LABEL,
    graph_node_texts,
    load_pair_claims,
    table_groups,
)

_MAX_ENTITY_LEN = 80    # P侧实体文本截断(EXC全文等)
_MAX_NODES = 12         # H侧闭世界节点上限


def _trunc(s: str, n: int = _MAX_ENTITY_LEN) -> str:
    s = s.strip().replace("\n", "")
    return s[:n] + "…" if len(s) > n else s


def _fmt_nodes(nodes: list[str], template: str) -> str:
    closed = "，除此之外没有其他节点。" if template == "closed" else "。"
    shown = nodes[:_MAX_NODES]
    names = "、".join(_trunc(t, 30) for t in shown)
    return f"图中显示，本图共包含{len(nodes)}个节点，包括：{names}{closed}"


def _parent_of(scene: str, csv_path: Path, item: str) -> str | None:
    """表格项X的父实体名(层级表); 无父级返回None."""
    groups, _ = table_groups(scene, csv_path)
    for parent, children in groups:
        if item in children:
            return parent
    return None


# ── 分歧→声明对构造 ───────────────────────────────────────

_ENTITY_PAT = re.compile(r"[「“]([^」”]{2,60})[」”]")


def extract_entity(disc: dict) -> str:
    """分歧实体名: table_side.text优先, 否则从evidence文本「X」提取.

    裁决记录(scene_adjudication/llm_adjudication)只带evidence,
    Tier1明细(table_side)需上游join — evidence内嵌实体名, 直接提取.
    """
    ts = disc.get("table_side") or {}
    raw = ts.get("text", "")
    if not raw:
        ev = disc.get("evidence", "")
        m = _ENTITY_PAT.search(ev)
        raw = m.group(1) if m else ""
    return _trunc(raw.strip(), _MAX_ENTITY_LEN)


def build_review_claim(scene: str, table_csv: Path, anchor: dict | None,
                       disc: dict, template: str = "closed") -> ClaimPair | None:
    """单条Tier1分歧 → NLI声明对. 无法构造返回None(诚实排除).

    disc字段: dtype, evidence(含实体名), (table_side可选).
    """
    label = TABLE_LABEL.get(scene, "功能表")
    dtype = disc.get("dtype", "")
    item = extract_entity(disc)
    nodes = graph_node_texts(anchor) if anchor else []

    if dtype in ("TABLE_ITEM_MISSING", "COMPONENT_MISSING"):
        if not item or not nodes:
            return None
        parent = _parent_of(scene, table_csv, item)
        if parent:
            p = f"{label}规定，「{item}」是「{parent}」的子功能"
        else:
            p = f"{label}规定，本表包含条目「{item}」"
        return ClaimPair(why="review_missing", entity=item,
                         premise=p, hypothesis=_fmt_nodes(nodes, template),
                         template=template,
                         meta={"dtype": dtype, "evidence": disc.get("evidence", "")})

    if dtype in ("ACTOR_MISSING", "STEP_MISSING", "EXC_MISSING"):
        if not item or not nodes:
            return None
        noun = {"ACTOR_MISSING": "参与者(Actor)",
                "STEP_MISSING": "执行步骤",
                "EXC_MISSING": "异常流"}[dtype]
        p = f"用例描述表规定，本用例的{noun}包括：「{item}」"
        return ClaimPair(why="review_missing", entity=item,
                         premise=p, hypothesis=_fmt_nodes(nodes, template),
                         template=template,
                         meta={"dtype": dtype, "evidence": disc.get("evidence", "")})

    if dtype == "DIAGRAM_EXTRA":
        # 图有表无: 由build_extra_claim处理(双闭世界计数对照)
        return None

    if dtype == "ORDER_CONFLICT":
        ev = disc.get("evidence", "")
        edge = (disc.get("diag_side") or {}).get("edge", "")
        p = f"用例描述表规定，步骤顺序为：{ev}"
        h = f"图中显示，流程顺序为：{edge}" if edge else "图中显示，流程顺序与表格规定相反"
        return ClaimPair(why="review_order", entity="顺序",
                         premise=p, hypothesis=h, template=template,
                         meta={"dtype": dtype, "evidence": ev})

    if dtype == "UC_NAME_MISMATCH":
        ds = disc.get("diag_side") or {}
        gname = ds.get("text", "")
        if not gname:
            return None
        p = f"用例描述表规定，用例名称为「{item}」"
        h = f"图中显示，用例名称为「{gname}」"
        return ClaimPair(why="review_name", entity=item,
                         premise=p, hypothesis=h, template=template,
                         meta={"dtype": dtype, "evidence": disc.get("evidence", "")})
    return None


# ── DIAGRAM_EXTRA专用: 表闭世界 vs 图闭世界(双闭世界计数对照) ──

def build_extra_claim(scene: str, table_csv: Path, anchor: dict | None,
                      template: str = "closed") -> ClaimPair | None:
    """DIAGRAM_EXTRA型分歧: 图节点超出表格条目 → 双闭世界声明对."""
    if not anchor:
        return None
    pid, claims = load_pair_claims(Path(table_csv).parent, template=template)
    flat_claims = [c for c in claims if c.why in ("aggregate", "text")]
    if not flat_claims:
        return None
    # 复用aggregate声明的P(表格闭世界), H改为全量图节点(不预过滤)
    agg = next((c for c in flat_claims if c.why == "aggregate"), flat_claims[0])
    nodes = graph_node_texts(anchor)
    if not nodes:
        return None
    return ClaimPair(why="review_extra", entity="(图多余节点)",
                     premise=agg.premise, hypothesis=_fmt_nodes(nodes, template),
                     template=template, meta={"dtype": "DIAGRAM_EXTRA"})


# ── 薄I/O: pair数据缓存 ───────────────────────────────────

class PairContext:
    """pair目录的惰性数据缓存(table_csv/anchor), 避免逐条分歧重读文件."""

    def __init__(self, pair_root: Path) -> None:
        self.pair_root = pair_root
        self._cache: dict[str, tuple[Path, dict | None]] = {}

    def get(self, pair_id: str) -> tuple[Path, dict | None] | None:
        if pair_id in self._cache:
            return self._cache[pair_id]
        for scene_dir in sorted(self.pair_root.iterdir()):
            d = scene_dir / pair_id
            if (d / "meta.json").exists():
                anchor = None
                ap = d / "visio_anchor.json"
                if ap.exists():
                    try:
                        anchor = json.loads(ap.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        anchor = None
                entry = (d / "table.csv", anchor)
                self._cache[pair_id] = entry
                return entry
        self._cache[pair_id] = None  # 负缓存
        return None


def build_claims_for_discrepancy(pair_root: Path, pair_id: str,
                                 disc: dict, ctx: PairContext,
                                 template: str = "closed"
                                 ) -> tuple[str, ClaimPair | None]:
    """分歧 → (scene, 声明对). pair缺失/构造失败返回(scene, None)."""
    entry = ctx.get(pair_id)
    if entry is None:
        return "", None
    table_csv, anchor = entry
    scene = table_csv.parent.parent.name
    dtype = disc.get("dtype", "")
    if dtype == "DIAGRAM_EXTRA":
        return scene, build_extra_claim(scene, table_csv, anchor, template)
    claim = build_review_claim(scene, table_csv, anchor, disc, template)
    return scene, claim
