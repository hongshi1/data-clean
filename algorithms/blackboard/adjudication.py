"""AdjudicationStore: M7/M17/M22裁决语料库的统一索引 (检测闭环的标签源).

资产与优先级(权威度降序):
  1. anchor_v2/final_adjudication.json    M22三轮仲裁终判(664标签, π=0.265)
  2. anchor_v2/ensemble_arbitration.json 五票集成(337条, 带vote_dist)
  3. anchor_v2/scene_adjudication.json    M17多场景双LLM(285条)
  4. anchor_sc2/llm_adjudication.json     M7双LLM(417条)

task_id格式: "{pair}_{seq:02d}" (如 2_001_01); 元数据(dtype/evidence)来自
带detail的源, 标签以final_adjudication为准(缺则回退源的final).

匹配协议(与tier1分歧对齐): evidence精确匹配 > 同pair同dtype > 无.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data/gjb_438c"

FINAL_PATH = DATA / "anchor_v2/final_adjudication.json"
ENSEMBLE_PATH = DATA / "anchor_v2/ensemble_arbitration.json"
SCENE_PATH = DATA / "anchor_v2/scene_adjudication.json"
M7_PATH = DATA / "anchor_sc2/llm_adjudication.json"

_DECIDED = {"real_bug", "benign_variation", "compiler_bug", "extraction_error"}


def scene_num(scene: str) -> str:
    """场景标识 → pair前缀数字: 'sc1_usecase_capability'→'1', '2'→'2'."""
    p = scene.split("_")[0]
    if p.startswith("sc") and len(p) > 2 and p[2:].isdigit():
        return p[2:]
    return p


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


class AdjudicationStore:
    """裁决语料库索引. 纯读, 懒加载."""

    def __init__(self) -> None:
        self._by_pair: dict[str, list[dict[str, Any]]] | None = None
        self._final_labels: dict[str, dict] | None = None
        self._dist: dict[str, int] | None = None
        self._pi: float | None = None

    # ── 索引构建 ──────────────────────────────────────────
    def _build(self) -> dict[str, list[dict[str, Any]]]:
        if self._by_pair is not None:
            return self._by_pair
        final = _load(FINAL_PATH).get("final_labels", {})
        self._final_labels = final if isinstance(final, dict) else {}
        self._dist = _load(FINAL_PATH).get("dist", {})
        self._pi = _load(FINAL_PATH).get("pi")

        # 元数据源(带dtype/evidence), 标签优先final_labels
        sources = [ENSEMBLE_PATH, SCENE_PATH, M7_PATH]
        by_task: dict[str, dict[str, Any]] = {}
        for path in sources:
            for tid, rec in _load(path).items():
                if not isinstance(rec, dict):
                    continue
                if tid in by_task and by_task[tid].get("_src_rank", 9) <= 1:
                    continue
                label = (self._final_labels.get(tid, {}).get("label")
                         or rec.get("final") or "")
                entry = {
                    "task_id": tid,
                    "pair": rec.get("pair", tid.rsplit("_", 1)[0]),
                    "dtype": rec.get("dtype", ""),
                    "evidence": rec.get("evidence", ""),
                    "label": label,
                    "vote_dist": rec.get("vote_dist", {}),
                    "_src_rank": 1 if path == ENSEMBLE_PATH else 2,
                }
                by_task[tid] = entry
        # final_labels里有但元数据源没有的task → 只知pair
        for tid, rec in self._final_labels.items():
            if tid not in by_task:
                by_task[tid] = {"task_id": tid, "pair": rec.get("pair", ""),
                                "dtype": "", "evidence": "",
                                "label": rec.get("label", ""),
                                "vote_dist": {}, "_src_rank": 3}

        idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in by_task.values():
            if entry.get("pair"):
                entry.pop("_src_rank", None)
                idx[entry["pair"]].append(entry)
        self._by_pair = dict(idx)
        return self._by_pair

    # ── 查询 ──────────────────────────────────────────────
    def verdicts_for_pair(self, pair_id: str) -> list[dict[str, Any]]:
        return self._build().get(pair_id, [])

    def match(self, pair_id: str, dtype: str,
              evidence: str) -> dict[str, Any] | None:
        """tier1分歧 → 裁决标签. 匹配协议: evidence精确 > 同dtype."""
        entries = self.verdicts_for_pair(pair_id)
        if not entries:
            return None
        for e in entries:
            if e.get("evidence") and e["evidence"] == evidence:
                return e
        for e in entries:
            if dtype and e.get("dtype") == dtype and e.get("label"):
                return e
        return None

    # ── 先验统计 ──────────────────────────────────────────
    def type_counts(self, scene: str, dtype: str) -> dict[str, int]:
        """(场景, 分歧类型) → 标签计数. 类型先验的 empirical 基础."""
        prefix = scene_num(scene)
        counts: Counter = Counter()
        for pair, entries in self._build().items():
            if pair.split("_")[0] != prefix:
                continue
            for e in entries:
                if e.get("dtype") == dtype and e.get("label"):
                    counts[e["label"]] += 1
        return dict(counts)

    def scene_pi(self, scene: str) -> float | None:
        """场景级π: real/(已裁决) — 无数据场景回退全局(M22的0.265)."""
        prefix = scene_num(scene)
        real = decided = 0
        for pair, entries in self._build().items():
            if pair.split("_")[0] != prefix:
                continue
            for e in entries:
                if e.get("label") in _DECIDED:
                    decided += 1
                    real += (e["label"] == "real_bug")
        if decided:
            return round(real / decided, 4)
        return self._pi

    @property
    def stats(self) -> dict[str, Any]:
        final = _load(FINAL_PATH)
        return {"n_final_labels": len(final.get("final_labels", {})),
                "dist": final.get("dist", {}),
                "pi": final.get("pi"),
                "n_decided": final.get("n_decided"),
                "n_uncertain": final.get("n_uncertain")}
