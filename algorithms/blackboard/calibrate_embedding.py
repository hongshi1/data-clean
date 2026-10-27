"""Embedding通道校准: 在Tier1配对上测"embedding匹配 vs 词法银标"的一致率.

协议(与M3锚点校准同构, 但银标换为词法匹配):
  - 对象: 有Tier1预计算的pair, 表项(κ_T) × 锚点节点(FACT)
  - 银标: text_match_score ≥ 0.5 (M16的MATCH_TH, 词法确认的对应)
  - 指标: agreement_rate = embedding匹配中被词法确认的比例
    (这是embedding精度的下界: 词法漏掉的语义对应不算坏, 只算未确认)

产出: data/gjb_438c/blackboard/embedding_calibration.json
  → ConfidenceModel自动读取, embedding通道置信度从HEURISTIC升级为CALIBRATED

用法: python -m algorithms.blackboard.calibrate_embedding [--limit 40]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .embedding_channel import EmbeddingChannel
from .evidence_store import EvidenceStore
from .kt_compilers import compile_for_scene
from .lexical_kit import MATCH_TH, text_match_score

BASE = Path(__file__).resolve().parents[2]
OUT_PATH = BASE / "data/gjb_438c/blackboard/embedding_calibration.json"


def calibrate(limit: int = 40, prefer: str = "auto") -> dict[str, Any]:
    store = EvidenceStore()
    emb = EmbeddingChannel(prefer=prefer)
    mode = emb.ensure()

    n_pairs = 0
    n_emb = 0
    n_emb_raw = 0
    n_confirmed = 0
    n_lex_only = 0  # 词法确认但embedding未覆盖/未匹配(单向参考)

    for pair_id in sorted(store._pair_index()):
        if n_pairs >= limit:
            break
        scene = store.scene_of(pair_id)
        tier1 = store.tier1(pair_id)
        anchor = store.pair_anchor(pair_id)
        pd = store.pair_dir(pair_id)
        if tier1 is None or anchor is None or pd is None:
            continue
        x_t = compile_for_scene(scene, pd / "table.csv")
        if not x_t:
            continue
        table_names = [n["text"] for n in x_t.get("nodes", []) if n.get("text")]
        diag_texts = [n["text"] for n in anchor.get("nodes", []) if n.get("text")]
        if not table_names or not diag_texts:
            continue
        n_pairs += 1

        matches = emb.match(table_names, diag_texts)
        n_emb_raw += len(matches)
        # 消费语义一致: 贪心一对一(M16 match_elements同款协议)
        used_i: set[int] = set()
        used_j: set[int] = set()
        unique: list[tuple[int, int, float]] = []
        for i, j, score in matches:          # match已按分数降序
            if i not in used_i and j not in used_j:
                used_i.add(i)
                used_j.add(j)
                unique.append((i, j, score))
        n_emb_raw = len(matches)
        for i, j, _score in unique:
            n_emb += 1
            if text_match_score(table_names[i], diag_texts[j]) >= MATCH_TH:
                n_confirmed += 1
        # 词法单向参考(不计入agreement)
        for i, tn in enumerate(table_names):
            if any(text_match_score(tn, dt) >= MATCH_TH for dt in diag_texts):
                if not any(m[0] == i for m in matches):
                    n_lex_only += 1

    agreement = round(n_confirmed / n_emb, 4) if n_emb else None
    out: dict[str, Any] = {
        "n_pairs": n_pairs,
        "n_emb_matches": n_emb,
        "n_emb_matches_raw_cross_product": n_emb_raw,
        "n_confirmed_by_lexical": n_confirmed,
        "agreement_rate": agreement,
        "n_lexical_only_not_emb": n_lex_only,
        "embedding_mode": mode,
        "prefer": prefer,
        "coverage": {"n_texts_requested": emb.stats["n_texts_requested"],
                     "n_texts_covered": emb.stats["n_texts_covered"]},
        "th_emb": emb.effective_th,
        "th_lexical": MATCH_TH,
        "note": ("agreement=embedding匹配被词法银标确认的比例(精度的下界); "
                 "n_lexical_only_not_emb=词法确认但embedding未对齐(召回损失参考)"),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Embedding通道校准")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--prefer", default="auto",
                        choices=["auto", "local"],
                        help="local=本地BGE优先(离线可复现校准)")
    args = parser.parse_args(argv)
    result = calibrate(args.limit, prefer=args.prefer)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
