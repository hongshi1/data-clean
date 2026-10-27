#!/usr/bin/env python3
"""迭代锚点扩展: 图节点 → 需求 的三层锚点 (L0 explicit / L1 title-bridge / L2 fuzzy).

背景: 上下文关联(方向A)需要把图节点与文字需求聚合成同一"条目".
L1 title-bridge(node text规范化 == requirement title规范化, 同doc)已有
gold结果846条, 本工具冻结复现并校验; L0/L2为协议完备性与本轮新增.

三层协议:
  L0 explicit     node text含需求ID正则 [A-Z]{3,}(-[A-Z0-9]{2,}){2,} → 直接锚定
                  (实测0条, 保留协议完备性);
  L1 title-bridge 规范化(去空白/换行)后相等, 同doc, 每node取首个命中
                  (冻结复现gold 846, quality_tier=gold_frozen);
  L2 fuzzy        仅作用于L1未锚定node(扩展), 迭代轮次=1(不迭代, 宁缺勿滥):
    a) 词面 fuzzy_lexical: node text规范化是requirement raw_text连续子串(≥4字)
       或与title前缀匹配(前≥4字相等);
    b) 向量 fuzzy_vector: node向量 vs requirement向量(feature_snapshot_v1/
       vectors.npz, 同doc)cos≥θ; θ校准 = L1的846条正例种子 + 同doc随机错配
       846条负例(seed固定) → 升序扫阈值取 precision≥0.95 的最小θ;
    c) 一个node命中多个requirement → 全部输出, match_confidence降级multi_match.

输入: structured_corpus_v1/{diagram_nodes,requirements,diagrams}.jsonl
      feature_snapshot_v1/vectors.npz (claim/requirement/diagram_node行)
输出: data/gjb_438c/anchor_expansion_v1/{anchors.jsonl,summary.json,manifest.json}
用法: python tools/expand_diagram_anchors.py
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

NODES_PATH = BASE / "data/gjb_438c/structured_corpus_v1/diagram_nodes.jsonl"
REQS_PATH = BASE / "data/gjb_438c/structured_corpus_v1/requirements.jsonl"
DIAGRAMS_PATH = BASE / "data/gjb_438c/structured_corpus_v1/diagrams.jsonl"
VECTORS_PATH = BASE / "data/gjb_438c/feature_snapshot_v1/vectors.npz"
OUT_DIR = BASE / "data/gjb_438c/anchor_expansion_v1"

REQ_ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
WS_RE = re.compile(r"\s+")

NEG_SEED = 20261022
NEG_COUNT = 846
PRECISION_TARGET = 0.95
LEXICAL_MIN_LEN = 4

LAYER_ORDER = {"L0": 0, "L1": 1, "L2": 2}


def normalize_ws(text: str) -> str:
    """规范化: 去全部空白/换行 (L1 gold协议)."""
    return WS_RE.sub("", text or "")


def prefix_overlap_len(a: str, b: str) -> int:
    """两串公共前缀长度."""
    k = 0
    for x, y in zip(a, b):
        if x != y:
            break
        k += 1
    return k


def lexical_match(
    node_norm: str, title_norm: str, raw_norm: str, min_len: int = LEXICAL_MIN_LEN
) -> dict[str, Any] | None:
    """L2a词面: 子串(node⊆raw_text)或前缀(node前k字==title前k字, k≥min_len)."""
    kinds: list[str] = []
    score = 0.0
    if len(node_norm) >= min_len and node_norm in raw_norm:
        kinds.append("substring")
        score = 1.0
    if title_norm:
        k = prefix_overlap_len(node_norm, title_norm)
        if k >= min_len and k == min(len(node_norm), len(title_norm)):
            kinds.append("prefix")
            score = max(score, k / max(len(node_norm), len(title_norm)))
    if not kinds:
        return None
    return {"score": round(score, 4), "kinds": kinds}


def _rank_auc(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney AUC (平均秩, 处理并列)."""
    n_p, n_n = len(pos), len(neg)
    if n_p == 0 or n_n == 0:
        return 0.0
    scores = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg])
    rank_sum_pos = 0.0
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and scores[j + 1][0] == scores[i][0]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for t in range(i, j + 1):
            if scores[t][1] == 1:
                rank_sum_pos += avg_rank
        i = j + 1
    return (rank_sum_pos - n_p * (n_p + 1) / 2) / (n_p * n_n)


def calibrate_theta(
    pos: list[float], neg: list[float], target: float = PRECISION_TARGET
) -> dict[str, Any]:
    """θ校准: 升序扫候选阈值, 取 precision≥target 的最小θ(该精度下recall最大).

    候选阈值 = pos∪neg的全部唯一分数值(含边界情形: 阈值=某负例分数时该负例计入FP).
    无θ达标时回退到precision最大的θ并标记 target_met=False.
    """
    n_p, n_n = len(pos), len(neg)
    auc = _rank_auc(pos, neg)
    candidates = sorted(set(pos) | set(neg))
    chosen: dict[str, Any] | None = None
    for theta in candidates:
        tp = sum(1 for s in pos if s >= theta)
        fp = sum(1 for s in neg if s >= theta)
        if tp >= 1 and tp + fp > 0 and tp / (tp + fp) >= target:
            chosen = {
                "theta": round(theta, 4),
                "tp": tp,
                "fp": fp,
                "precision": round(tp / (tp + fp), 4),
                "recall": round(tp / n_p, 4) if n_p else 0.0,
                "target_met": True,
            }
            break
    if chosen is None:
        best: dict[str, Any] | None = None
        for theta in candidates:
            tp = sum(1 for s in pos if s >= theta)
            fp = sum(1 for s in neg if s >= theta)
            if tp < 1:
                continue
            precision = tp / (tp + fp)
            recall = tp / n_p if n_p else 0.0
            if best is None or (precision, recall) > (best["precision"], best["recall"]):
                best = {
                    "theta": round(theta, 4),
                    "tp": tp,
                    "fp": fp,
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "target_met": False,
                }
        chosen = best or {
            "theta": 1.0, "tp": 0, "fp": 0, "precision": 0.0, "recall": 0.0,
            "target_met": False,
        }
    chosen.update(
        {
            "n_pos": n_p,
            "n_neg": n_n,
            "precision_target": target,
            "auc": round(auc, 4),
            "selection": "smallest_theta_with_precision_ge_target",
        }
    )
    return chosen


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_vectors(path: Path) -> tuple[np.ndarray, dict[str, int], dict[str, list[int]]]:
    """npz → (矩阵, 通用行索引{全id:row}, 需求行索引{base_id:[rows含#N分块]})."""
    data = np.load(path, allow_pickle=False)
    matrix = data["matrix"]
    ids = [str(x) for x in data["ids"]]
    row_index = {key: i for i, key in enumerate(ids)}
    req_rows: dict[str, list[int]] = defaultdict(list)
    for key, i in row_index.items():
        if key.startswith("requirement:"):
            base = key[len("requirement:"):].split("#")[0]
            req_rows[base].append(i)
    return matrix, row_index, dict(req_rows)


def unit_rows(matrix: np.ndarray, rows: list[int]) -> np.ndarray:
    block = matrix[rows].astype(np.float64)
    norms = np.linalg.norm(block, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return block / norms


def score_node_req(
    node_row: int, req_rows: list[int], matrix: np.ndarray, units: dict[int, np.ndarray]
) -> float:
    """node向量 vs requirement(含#N分块)向量的最大cos."""
    node_vec = units[node_row]
    best = 0.0
    for row in req_rows:
        cos = float(np.dot(node_vec, units[row]))
        if cos > best:
            best = cos
    return best


def make_anchor(
    layer: str,
    anchor_type: str,
    doc_id: str,
    node_id: str,
    requirement_id: str,
    method: str,
    score: float,
    quality_tier: str,
    evidence: dict[str, Any],
    match_confidence: str = "unique",
) -> dict[str, Any]:
    return {
        "layer": layer,
        "anchor_type": anchor_type,
        "doc_id": doc_id,
        "node_id": node_id,
        "requirement_id": requirement_id,
        "method": method,
        "score": score,
        "quality_tier": quality_tier,
        "match_confidence": match_confidence,
        "evidence": evidence,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    diagram_rows = read_jsonl(DIAGRAMS_PATH)
    req_rows = read_jsonl(REQS_PATH)
    node_rows = read_jsonl(NODES_PATH)
    matrix, row_index, req_vector_rows = load_vectors(VECTORS_PATH)

    dgm2doc = {d["diagram_id"]: str(d["doc_id"]) for d in diagram_rows}
    nodes: list[dict[str, Any]] = []
    nodes_without_doc = 0
    for row in node_rows:
        doc = dgm2doc.get(str(row.get("diagram_id")))
        if doc is None:
            nodes_without_doc += 1
            continue
        text_raw = str(row.get("text_raw") or "")
        if not normalize_ws(text_raw):
            continue
        nodes.append(
            {
                "node_id": str(row["node_id"]),
                "doc_id": doc,
                "text_raw": text_raw,
                "node_norm": normalize_ws(text_raw),
                "vector_row": row_index.get(f"diagram_node:{row['node_id']}"),
            }
        )
    total_nodes = len(node_rows)
    nodes_with_text = len(nodes)
    nodes_with_vector = sum(1 for n in nodes if n["vector_row"] is not None)

    reqs: list[dict[str, Any]] = []
    for row in req_rows:
        reqs.append(
            {
                "requirement_id": str(row["requirement_id"]),
                "doc_id": str(row["doc_id"]),
                "title": str(row.get("title") or ""),
                "title_norm": normalize_ws(str(row.get("title") or "")),
                "raw_norm": normalize_ws(str(row.get("raw_text") or "")),
            }
        )
    reqs_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for req in reqs:
        reqs_by_doc[req["doc_id"]].append(req)
    id2docs: dict[str, set[str]] = defaultdict(set)
    for req in reqs:
        id2docs[req["requirement_id"]].add(req["doc_id"])

    anchors: list[dict[str, Any]] = []

    # ---- L0 explicit: node text含需求ID → 同doc需求直接锚定 ----
    l0_count = 0
    for node in nodes:
        for req_id in REQ_ID_RE.findall(node["text_raw"]):
            for req in reqs_by_doc.get(node["doc_id"], []):
                if req["requirement_id"] == req_id:
                    anchors.append(
                        make_anchor(
                            "L0", "explicit_id", node["doc_id"], node["node_id"],
                            req_id, "id_regex", 1.0, "gold_frozen",
                            {"node_text": node["text_raw"], "requirement_id_ref": req_id},
                        )
                    )
                    l0_count += 1
                    break

    # ---- L1 title-bridge: 规范化相等, 同doc, 每node首个命中 (冻结gold) ----
    l1_node_req: dict[str, str] = {}
    l1_multi_title_nodes = 0
    for node in nodes:
        hits = [
            req for req in reqs_by_doc.get(node["doc_id"], [])
            if req["title_norm"] and node["node_norm"] == req["title_norm"]
        ]
        if not hits:
            continue
        if len(hits) > 1:
            l1_multi_title_nodes += 1
        first = hits[0]
        l1_node_req[node["node_id"]] = first["requirement_id"]
        anchors.append(
            make_anchor(
                "L1", "title_bridge", node["doc_id"], node["node_id"],
                first["requirement_id"], "norm_equal", 1.0, "gold_frozen",
                {"node_text": node["text_raw"], "requirement_title": first["title"]},
            )
        )
    l1_count = len(l1_node_req)

    # ---- θ校准: L1正例种子 + 同doc随机错配负例 ----
    units: dict[int, np.ndarray] = {}

    def ensure_units(rows: list[int]) -> None:
        for row in rows:
            if row not in units:
                units[row] = unit_rows(matrix, [row])[0]

    def vec_score(node: dict[str, Any], base: str) -> float | None:
        rows = req_vector_rows.get(base)
        if node["vector_row"] is None or not rows:
            return None
        ensure_units([node["vector_row"]] + rows)
        return score_node_req(node["vector_row"], rows, matrix, units)

    node_by_id = {n["node_id"]: n for n in nodes}
    pos_scores: list[float] = []
    pos_skipped = 0
    for node_id, req_id in l1_node_req.items():
        node = node_by_id[node_id]
        score = vec_score(node, req_id)
        if score is None:
            pos_skipped += 1
            continue
        pos_scores.append(score)

    req_bases_with_vec_by_doc: dict[str, list[str]] = defaultdict(set)
    unresolvable_bases = 0
    for base in req_vector_rows:
        docs = id2docs.get(base)
        if not docs:
            unresolvable_bases += 1
            continue
        for doc in docs:
            req_bases_with_vec_by_doc[doc].add(base)
    req_bases_with_vec_by_doc = {
        doc: sorted(bases) for doc, bases in req_bases_with_vec_by_doc.items()
    }
    nodes_with_vec = [n for n in nodes if n["vector_row"] is not None]
    rng = random.Random(NEG_SEED)
    neg_scores: list[float] = []
    tries = 0
    while len(neg_scores) < min(NEG_COUNT, l1_count) and tries < 200000:
        tries += 1
        node = nodes_with_vec[rng.randrange(len(nodes_with_vec))]
        pool = req_bases_with_vec_by_doc.get(node["doc_id"], [])
        if not pool:
            continue
        base = pool[rng.randrange(len(pool))]
        if l1_node_req.get(node["node_id"]) == base:
            continue
        score = vec_score(node, base)
        if score is None:
            continue
        neg_scores.append(score)
    calibration = calibrate_theta(pos_scores, neg_scores)
    theta = float(calibration["theta"])

    # ---- L2 fuzzy (仅L1未锚定node; 1轮不迭代) ----
    l2_anchors: list[dict[str, Any]] = []
    l2_node_reqs: dict[str, set[str]] = defaultdict(set)
    lexical_hit_nodes: set[str] = set()
    for node in nodes:
        if node["node_id"] in l1_node_req:
            continue
        doc_reqs = reqs_by_doc.get(node["doc_id"], [])
        node_lex_hits = 0
        for req in doc_reqs:
            lex = lexical_match(node["node_norm"], req["title_norm"], req["raw_norm"])
            if lex is not None:
                node_lex_hits += 1
                l2_anchors.append(
                    make_anchor(
                        "L2", "fuzzy_lexical", node["doc_id"], node["node_id"],
                        req["requirement_id"], "+".join(lex["kinds"]), lex["score"],
                        "candidate",
                        {
                            "node_text": node["text_raw"],
                            "requirement_title": req["title"],
                            "match_kinds": lex["kinds"],
                        },
                    )
                )
                l2_node_reqs[node["node_id"]].add(req["requirement_id"])
        if node_lex_hits:
            lexical_hit_nodes.add(node["node_id"])
    lexical_nodes = len(lexical_hit_nodes)

    # 每doc预计算需求单位向量矩阵(含#N分块)与行→base映射
    doc_req_matrix: dict[str, tuple[np.ndarray, list[str]]] = {}
    for doc, bases in req_bases_with_vec_by_doc.items():
        rows: list[int] = []
        base_of_row: list[str] = []
        for base in bases:
            for row in req_vector_rows[base]:
                rows.append(row)
                base_of_row.append(base)
        doc_req_matrix[doc] = (unit_rows(matrix, rows), base_of_row)

    vector_nodes = 0
    for node in nodes:
        if node["node_id"] in l1_node_req or node["vector_row"] is None:
            continue
        pack = doc_req_matrix.get(node["doc_id"])
        if pack is None:
            continue
        req_matrix, base_of_row = pack
        node_vec = unit_rows(matrix, [node["vector_row"]])[0]
        sims = req_matrix @ node_vec
        hits: dict[str, float] = {}
        for col, base in enumerate(base_of_row):
            sim = float(sims[col])
            if sim >= theta and (base not in hits or sim > hits[base]):
                hits[base] = sim
        if hits:
            vector_nodes += 1
            title_map = {
                req["requirement_id"]: req["title"]
                for req in reqs_by_doc.get(node["doc_id"], [])
            }
            for base, sim in sorted(hits.items()):
                l2_anchors.append(
                    make_anchor(
                        "L2", "fuzzy_vector", node["doc_id"], node["node_id"], base,
                        "bge_cos", round(sim, 4), "candidate",
                        {
                            "node_text": node["text_raw"],
                            "requirement_title": title_map.get(base, ""),
                            "theta": theta,
                        },
                    )
                )
                l2_node_reqs[node["node_id"]].add(base)

    for anchor in l2_anchors:
        if len(l2_node_reqs.get(anchor["node_id"], ())) > 1:
            anchor["match_confidence"] = "multi_match"
    anchors.extend(l2_anchors)

    # ---- 统一编号 + 排序落盘 ----
    anchors.sort(
        key=lambda a: (
            LAYER_ORDER[a["layer"]], a["doc_id"], a["node_id"],
            a["method"], a["requirement_id"],
        )
    )
    prefix = {"L0": "ANC-L0", "L1": "ANC-L1", "L2": "ANC-L2"}
    counters = {"L0": 0, "L1": 0, "L2": 0}
    for anchor in anchors:
        layer = anchor["layer"]
        counters[layer] += 1
        anchor["anchor_id"] = f"{prefix[layer]}-{counters[layer]:05d}"
    anchors = [
        {
            "anchor_id": a["anchor_id"], "layer": a["layer"], "anchor_type": a["anchor_type"],
            "doc_id": a["doc_id"], "node_id": a["node_id"],
            "requirement_id": a["requirement_id"], "method": a["method"],
            "score": a["score"], "quality_tier": a["quality_tier"],
            "match_confidence": a["match_confidence"], "evidence": a["evidence"],
        }
        for a in anchors
    ]

    l2_lexical_anchors = sum(1 for a in anchors if a["anchor_type"] == "fuzzy_lexical")
    l2_vector_anchors = sum(1 for a in anchors if a["anchor_type"] == "fuzzy_vector")
    multi_match_anchors = sum(
        1 for a in anchors if a["match_confidence"] == "multi_match"
    )
    l2_nodes = len(l2_node_reqs)
    covered_nodes = l1_count + l2_nodes
    denominator = nodes_with_vector

    summary = {
        "protocol": {
            "tool": "expand_diagram_anchors",
            "iteration_rounds": 1,
            "l2_scope": "nodes_without_l1_anchor",
            "lexical_min_len": LEXICAL_MIN_LEN,
            "negative_seed": NEG_SEED,
            "theta_selection": "smallest_theta_with_precision_ge_0.95",
        },
        "nodes": {
            "total": total_nodes,
            "without_diagram_doc": nodes_without_doc,
            "with_text": nodes_with_text,
            "with_vector": nodes_with_vector,
            "coverage_denominator": denominator,
        },
        "l0_explicit": {"anchors": l0_count, "note": "id_regex协议完备性, 实测0条"},
        "l1_title_bridge": {
            "anchors": l1_count,
            "unique_nodes": l1_count,
            "gold_846_reproduced": l1_count == 846,
            "nodes_with_multiple_title_matches": l1_multi_title_nodes,
        },
        "l2_fuzzy": {
            "lexical_anchors": l2_lexical_anchors,
            "vector_anchors": l2_vector_anchors,
            "unique_nodes": l2_nodes,
            "lexical_nodes": lexical_nodes,
            "vector_nodes": vector_nodes,
            "multi_match_anchors": multi_match_anchors,
        },
        "theta_calibration": {
            **calibration,
            "positives_skipped_no_vector": pos_skipped,
            "unresolvable_req_bases": unresolvable_bases,
            "method": "L1 gold seeds (node,req) + same-doc random mismatched negatives",
        },
        "node_coverage": {
            "l1_nodes": l1_count,
            "l1_rate": round(l1_count / denominator, 4) if denominator else 0.0,
            "l1_plus_l2_nodes": covered_nodes,
            "l1_plus_l2_rate": round(covered_nodes / denominator, 4) if denominator else 0.0,
            "denominator": denominator,
        },
        "anchors_total": len(anchors),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    anchors_path = OUT_DIR / "anchors.jsonl"
    summary_path = OUT_DIR / "summary.json"
    with open(anchors_path, "w", encoding="utf-8") as handle:
        for anchor in anchors:
            handle.write(json.dumps(anchor, ensure_ascii=False) + "\n")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    manifest = {
        "version": 1,
        "git_sha": None,
        "built_at": None,
        "inputs": {
            str(p.relative_to(BASE)): {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
            for p in (NODES_PATH, REQS_PATH, DIAGRAMS_PATH, VECTORS_PATH)
        },
        "outputs": {
            "anchors.jsonl": {
                "bytes": anchors_path.stat().st_size,
                "sha256": sha256_file(anchors_path),
                "rows": len(anchors),
            },
            "summary.json": {
                "bytes": summary_path.stat().st_size,
                "sha256": sha256_file(summary_path),
            },
        },
    }
    run = open_run(
        "expand_diagram_anchors",
        {
            "neg_seed": NEG_SEED,
            "neg_count": NEG_COUNT,
            "precision_target": PRECISION_TARGET,
            "lexical_min_len": LEXICAL_MIN_LEN,
        },
    )
    manifest["git_sha"] = run.meta["git_sha"]
    manifest["built_at"] = run.meta["opened_at"]
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    run.save_result(summary)
    run.log(
        action="anchors_expanded", l1=l1_count, l2=len(l2_anchors),
        covered_nodes=covered_nodes, theta=theta,
    )

    print("=" * 64)
    print("迭代锚点扩展 (L0 explicit / L1 title-bridge / L2 fuzzy, 1轮)")
    print("=" * 64)
    print(f"  节点              : 总{total_nodes} / 有文本{nodes_with_text} / 有向量{nodes_with_vector}")
    print(f"  L0 explicit       : {l0_count}条 (id正则, 实测0)")
    print(f"  L1 title-bridge   : {l1_count}条 (gold 846复现: "
          f"{l1_count == 846}; 多标题node {l1_multi_title_nodes}个取首个)")
    print(f"  θ校准             : θ={theta:.4f} P={calibration['precision']:.4f} "
          f"R={calibration['recall']:.4f} AUC={calibration['auc']:.4f} "
          f"(pos {len(pos_scores)}/neg {len(neg_scores)})")
    print(f"  L2 fuzzy_lexical  : {l2_lexical_anchors}条 ({lexical_nodes}个node)")
    print(f"  L2 fuzzy_vector   : {l2_vector_anchors}条 ({vector_nodes}个node)")
    print(f"  L2 multi_match    : {multi_match_anchors}条降级候选")
    print(f"  node覆盖率        : {l1_count}/{denominator} "
          f"({summary['node_coverage']['l1_rate']:.2%}) → "
          f"{covered_nodes}/{denominator} "
          f"({summary['node_coverage']['l1_plus_l2_rate']:.2%})")
    print(f"  锚点总数          : {len(anchors)}")
    print(f"  输出              : {OUT_DIR}")
    print(f"  运行记录          : {run.path}")


if __name__ == "__main__":
    main()
