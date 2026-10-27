#!/usr/bin/env python3
"""Cross-modal (text claim <-> Visio diagram node) retrieval with a Procrustes
register-gap bridge (query-prefix space -> document space).

Research question
-----------------
BGE's retrieval protocol prefixes queries with the instruction
"为这个句子生成表示以用于检索相关文章：" while documents are encoded bare,
shifting the query space relative to the document space (the "register gap"
of the survey narrative). Procrustes was a negative result in the single-modal
text-vs-text control (0.9471 vs native 0.9568 AUC); its natural use case is
exactly this cross-space alignment. This protocol measures on real GJB SRS
data whether a deterministic orthogonal map recovers the gap:

  G0 doc-doc    : snapshot claim vector vs snapshot node vector
                  (same space, same protocol - no-gap upper bound)
  G1 prefix-doc : live prefix-encoded claim vector vs snapshot node vector
                  (the deployed O1 retrieval protocol - register gap)
  G2 procrustes : prefix vector -> orthogonal map -> vs snapshot node vector.
                  The map is fitted on train-split claim anchors:
                  source = live prefix vector, target = snapshot (no-prefix)
                  vector of the same claim, anchor_ids = claim occurrence ids.

Gold pairs (data reality)
-------------------------
No diagram node text in the corpus contains a regex identifier (verified
0/2831 snapshot nodes and 0/5165 corpus nodes at build time, re-verified at
run time and reported in result.json), so the "claim ID X <-> node text ID X"
link is realized as the deterministic chain:

  claim raw_text contains canonical ID X
    -> requirements.jsonl row whose requirement_id equals X or whose
       canonicalized raw_text IDs contain X
    -> the row's title T
    -> same-doc snapshot diagram node with whitespace-normalized text == T.

IDs are extracted whitespace-tolerantly (GJB tables space sub-IDs like
"PZXQ-GN-JMJCKJ- JMKF-KFGCSC") and canonicalized by stripping internal
whitespace; a hierarchical parent ID that is a hyphen-prefix of another ID in
the same claim is dropped (tree-table rows: the deepest ID is the row
subject). Candidate pools adapt the "含ID node" filter accordingly: the
same-doc pool is the ID-reachable node set (normalized text equals some
same-doc requirement title - a superset of every gold node), plus seeded
negatives sampled from other docs' ID-reachable nodes.

Docs are split through the fold_map of the most recent
train_shared_projection run (0=test, 1=dev, 2|3=train, mirroring
tools/train_shared_projection.py FOLD_TO_SPLIT); dev-fold claims are excluded
from anchors and queries. Without a fold_map the split falls back to
sha1(doc) % 4 through the same role table (noted in result.json).

Usage: python tools/eval_crossmodal_procrustes.py
Output: printed markdown table + runs-protocol result.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
CLAIMS_PATH = BASE / "data/gjb_438c/feature_matrix_v1/claim_slot_features.jsonl"
REQUIREMENTS_PATH = BASE / "data/gjb_438c/structured_corpus_v1/requirements.jsonl"
DIAGRAM_NODES_PATH = BASE / "data/gjb_438c/structured_corpus_v1/diagram_nodes.jsonl"
DIAGRAMS_PATH = BASE / "data/gjb_438c/structured_corpus_v1/diagrams.jsonl"
FEATURES_PATH = BASE / "data/gjb_438c/feature_snapshot_v1/features.jsonl"
VECTORS_PATH = BASE / "data/gjb_438c/feature_snapshot_v1/vectors.npz"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："  # BGE query instruction (O1 protocol)
ID_RE = re.compile(r"\b[A-Z]{3,}(?:\s*-\s*[A-Z0-9]{2,}){2,}\b")
# Mirrors tools/train_shared_projection.py FOLD_TO_SPLIT (fold -> split role).
FOLD_TO_SPLIT = {0: "test", 1: "dev", 2: "train", 3: "train"}
SEED = 42
N_NEGATIVES = 50
QUERY_LIMIT = 2000
KS = (1, 5, 10)
MRR_K = 10
LIVE_SNAPSHOT_COS_ABORT = 0.95
GROUP_LABELS = {
    "G0_doc_doc": "G0 doc-doc (upper bound)",
    "G1_prefix_doc": "G1 prefix-doc (register gap)",
    "G2_procrustes": "G2 procrustes (bridge)",
}

sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

from algorithms.common.bge_local import BgeLocal  # noqa: E402
from algorithms.context_linking.alignment import fit_orthogonal_map  # noqa: E402


# ── 数据记录 ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ClaimRecord:
    occurrence_id: str
    doc_id: str
    raw_text: str


@dataclass(frozen=True)
class RequirementRow:
    doc_id: str
    requirement_id: str
    title: str
    raw_ids: frozenset[str]


@dataclass(frozen=True)
class NodeRecord:
    occurrence_id: str
    doc_id: str
    text: str


@dataclass(frozen=True)
class GoldQuery:
    claim_occurrence_id: str
    doc_id: str
    text: str
    raw_text: str
    identifiers: frozenset[str]
    gold_nodes: frozenset[str]


# ── 纯函数(可测) ─────────────────────────────────────────────


def normalize_text(text: str) -> str:
    r"""空白归一: 节点文本含换行(如'非\n结构化'), 标题匹配按无空白比较."""
    return re.sub(r"\s+", "", text or "")


def canonical_identifier(raw: str) -> str:
    """ID规范化: 去掉内部空白(GJB表中存在'X- Y'式空格子ID)."""
    return re.sub(r"\s+", "", raw or "")


def extract_identifier_strings(text: str) -> set[str]:
    """空白容错的显式ID提取(3+大写字母 + >=2个'-[A-Z0-9]{2,}'段)."""
    return {canonical_identifier(match) for match in ID_RE.findall(text or "")}


def drop_prefix_identifiers(ids: set[str]) -> set[str]:
    """丢弃层级父ID: 同一claim内若某ID是另一ID的连字符前缀则删(树表行取最深层)."""
    return {
        candidate
        for candidate in ids
        if not any(other != candidate and other.startswith(candidate + "-") for other in ids)
    }


def prefixed(text: str) -> str:
    """查询侧前缀拼接(BGE检索指令)."""
    return QUERY_PREFIX + text


def fallback_fold(doc_id: str) -> int:
    return int(hashlib.sha1(doc_id.encode("utf-8")).hexdigest(), 16) % 4


def split_of_doc(doc_id: str, fold_map: dict[str, int] | None) -> str:
    fold = fold_map.get(doc_id) if fold_map is not None else None
    if fold is None:
        fold = fallback_fold(doc_id)
    return FOLD_TO_SPLIT[int(fold)]


def load_fold_map(runs_root: Path) -> tuple[dict[str, int] | None, str]:
    """最近train_shared_projection运行目录(按目录名时间戳)的fold_map.

    从最新到最旧找第一个带合法fold_map的config; 全部缺失则回退sha1分折
    (返回值第二项是来源说明, 落盘进result.json供审计).
    """
    stamp_re = re.compile(r"_(\d{8}_\d{6})(?:_\d+)?$")
    candidates: list[tuple[str, Path]] = []
    if runs_root.exists():
        for path in sorted(runs_root.iterdir()):
            if not path.is_dir() or not path.name.startswith("train_shared_projection_"):
                continue
            config_path = path / "config.json"
            if not config_path.exists():
                continue
            match = stamp_re.search(path.name)
            stamp = match.group(1) if match else "00000000_000000"
            candidates.append((stamp, config_path))
    for _, config_path in sorted(candidates, reverse=True):
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            fold_map = config.get("config", {}).get("fold_map")
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(fold_map, dict) and fold_map:
            return {str(doc): int(fold) for doc, fold in fold_map.items()}, str(config_path)
    return None, "sha1(doc)%4 fallback (no train_shared_projection fold_map found)"


def find_gold_nodes(
    identifiers: set[str],
    doc_id: str,
    requirements_by_doc: dict[str, list[RequirementRow]],
    nodes_by_doc: dict[str, list[NodeRecord]],
) -> set[str]:
    """同doc同ID的gold node集合: ID→需求行(requirement_id或raw_text ID)→标题→节点."""
    titles = {
        normalize_text(row.title)
        for row in requirements_by_doc.get(doc_id, ())
        if any(identifier == row.requirement_id or identifier in row.raw_ids
               for identifier in identifiers)
    }
    return {
        node.occurrence_id
        for node in nodes_by_doc.get(doc_id, ())
        if normalize_text(node.text) in titles
    }


def build_gold_queries(
    claims: list[ClaimRecord],
    claim_texts: dict[str, str],
    requirements_by_doc: dict[str, list[RequirementRow]],
    nodes_by_doc: dict[str, list[NodeRecord]],
) -> list[GoldQuery]:
    """构造gold跨模态查询: 无ID/无gold目标/无快照文本的claim被跳过."""
    queries: list[GoldQuery] = []
    for claim in claims:
        text = claim_texts.get(claim.occurrence_id)
        if text is None:
            continue
        identifiers = drop_prefix_identifiers(
            extract_identifier_strings(claim.raw_text)
        )
        if not identifiers:
            continue
        gold_nodes = find_gold_nodes(
            identifiers, claim.doc_id, requirements_by_doc, nodes_by_doc
        )
        if not gold_nodes:
            continue
        queries.append(
            GoldQuery(
                claim_occurrence_id=claim.occurrence_id,
                doc_id=claim.doc_id,
                text=text,
                raw_text=claim.raw_text,
                identifiers=frozenset(identifiers),
                gold_nodes=frozenset(gold_nodes),
            )
        )
    return queries


def reachable_nodes_by_doc(
    requirements_by_doc: dict[str, list[RequirementRow]],
    nodes_by_doc: dict[str, list[NodeRecord]],
) -> dict[str, frozenset[str]]:
    """"含ID node"的落地: 规格化文本等于本doc某需求标题的快照节点(gold的超集)."""
    reachable: dict[str, frozenset[str]] = {}
    for doc_id, nodes in nodes_by_doc.items():
        titles = {
            normalize_text(row.title) for row in requirements_by_doc.get(doc_id, ())
        }
        reachable[doc_id] = frozenset(
            node.occurrence_id for node in nodes if normalize_text(node.text) in titles
        )
    return reachable


def _query_seed(seed: int, claim_occurrence_id: str) -> list[int]:
    digest = hashlib.sha1(claim_occurrence_id.encode("utf-8")).digest()
    return [int(seed), int.from_bytes(digest[:4], "big")]


def build_pools(
    queries: list[GoldQuery],
    reachable: dict[str, frozenset[str]],
    n_negatives: int,
    seed: int,
) -> dict[str, tuple[str, ...]]:
    """每查询的候选池: 同doc全部ID可达节点 + 按查询独立种子随机采的异doc负例.

    每个查询的负例RNG由(seed, sha1(claim_occurrence_id))驱动, 池只依赖该查询
    自身与全局可达集合(增删其他查询不改变本查询的池).
    """
    global_nodes = sorted({occ for doc_nodes in reachable.values() for occ in doc_nodes})
    pools: dict[str, tuple[str, ...]] = {}
    for query in queries:
        same_doc = reachable.get(query.doc_id, frozenset())
        candidates = [occ for occ in global_nodes if occ not in same_doc]
        rng = np.random.default_rng(_query_seed(seed, query.claim_occurrence_id))
        take = min(n_negatives, len(candidates))
        negatives = (
            set(rng.choice(candidates, size=take, replace=False).tolist())
            if take > 0
            else set()
        )
        pools[query.claim_occurrence_id] = tuple(sorted(same_doc | negatives))
    return pools


def rank_auc(scores: list[float], labels: list[int]) -> float | None:
    """并列感知的秩AUC(正样本得分 vs 负样本得分)."""
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    order = sorted(range(len(scores)), key=lambda position: scores[position])
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and scores[order[end + 1]] == scores[order[start]]:
            end += 1
        average_rank = (start + end) / 2.0 + 1.0
        for position in order[start : end + 1]:
            ranks[position] = average_rank
        start = end + 1
    rank_sum_pos = sum(
        ranks[position] for position, label in enumerate(labels) if label == 1
    )
    return (rank_sum_pos - positives * (positives + 1) / 2.0) / (positives * negatives)


def evaluate_group(
    pools: dict[str, tuple[str, ...]],
    scores: dict[str, list[float]],
    golds: dict[str, frozenset[str]],
    ks: tuple[int, ...] = KS,
    mrr_k: int = MRR_K,
) -> dict[str, float]:
    """Recall@k(命中式: 任一gold进top-k)/MRR@k(首个gold的倒秩)/池化AUC.

    排序并列按节点occurrence_id字典序决胜(确定性). AUC把全部(查询,池节点)
    得分-标签对池化, 直接量化语体鸿沟与Procrustes恢复量.
    """
    hits = {k: 0 for k in ks}
    reciprocal_sum = 0.0
    pooled_scores: list[float] = []
    pooled_labels: list[int] = []
    for claim_id, pool in pools.items():
        query_scores = scores[claim_id]
        gold = golds[claim_id]
        order = sorted(
            range(len(pool)), key=lambda i: (-query_scores[i], pool[i])
        )
        ranked = [pool[i] for i in order]
        first_rank = next(
            (rank for rank, occ in enumerate(ranked, start=1) if occ in gold), None
        )
        for k in ks:
            if any(occ in gold for occ in ranked[:k]):
                hits[k] += 1
        if first_rank is not None and first_rank <= mrr_k:
            reciprocal_sum += 1.0 / first_rank
        for i, occ in enumerate(pool):
            pooled_scores.append(float(query_scores[i]))
            pooled_labels.append(1 if occ in gold else 0)
    n_queries = len(pools)
    metrics = {f"recall@{k}": hits[k] / n_queries for k in ks}
    metrics[f"mrr@{mrr_k}"] = reciprocal_sum / n_queries
    auc = rank_auc(pooled_scores, pooled_labels)
    metrics["auc"] = float(auc) if auc is not None else float("nan")
    return metrics


# ── 数据加载(仅main内调用, 顶层零I/O) ────────────────────────


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_feature_texts(path: Path) -> dict[str, tuple[str, str]]:
    """快照文本真值: occurrence_id -> (doc_id, text) — 向量实际编码的字符串."""
    texts: dict[str, tuple[str, str]] = {}
    for row in load_jsonl(path):
        occurrence_id = str(row["occurrence_id"])
        if occurrence_id.startswith(("claim:", "diagram_node:")):
            texts[occurrence_id] = (str(row["doc_id"]), str(row["text"]))
    return texts


def load_snapshot(path: Path) -> tuple[dict[str, int], np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(value) for value in data["ids"].tolist()]
    index = {occurrence_id: position for position, occurrence_id in enumerate(ids)}
    return index, matrix


def load_requirement_rows(path: Path) -> list[RequirementRow]:
    rows: list[RequirementRow] = []
    for row in load_jsonl(path):
        requirement_id = canonical_identifier(str(row.get("requirement_id") or ""))
        title = str(row.get("title") or "")
        if not requirement_id or not title:
            continue
        raw_ids = extract_identifier_strings(str(row.get("raw_text") or ""))
        rows.append(
            RequirementRow(
                doc_id=str(row["doc_id"]),
                requirement_id=requirement_id,
                title=title,
                raw_ids=frozenset(raw_ids),
            )
        )
    return rows


def load_node_records(
    path: Path, diagrams_path: Path, feature_texts: dict[str, tuple[str, str]]
) -> tuple[list[NodeRecord], dict[str, int]]:
    """快照节点(有向量者), doc/文本以features.jsonl为真值并与结构化语料对账."""
    diagram_doc = {
        str(row["diagram_id"]): str(row["doc_id"]) for row in load_jsonl(diagrams_path)
    }
    records: list[NodeRecord] = []
    mismatches = {"not_in_snapshot": 0, "doc": 0, "text": 0}
    for row in load_jsonl(path):
        occurrence_id = "diagram_node:" + str(row["node_id"])
        feature = feature_texts.get(occurrence_id)
        if feature is None:
            mismatches["not_in_snapshot"] += 1
            continue
        doc_id, text = feature
        if diagram_doc.get(str(row.get("diagram_id") or "")) != doc_id:
            mismatches["doc"] += 1
        if normalize_text(str(row.get("text_raw") or "")) != normalize_text(text):
            mismatches["text"] += 1
        records.append(
            NodeRecord(occurrence_id=occurrence_id, doc_id=doc_id, text=text)
        )
    return records, mismatches


def load_claim_records(
    path: Path, feature_texts: dict[str, tuple[str, str]]
) -> tuple[list[ClaimRecord], dict[str, int]]:
    records: list[ClaimRecord] = []
    mismatches = {"not_in_snapshot": 0, "doc": 0, "text": 0}
    for row in load_jsonl(path):
        occurrence_id = "claim:" + str(row["claim_id"])
        feature = feature_texts.get(occurrence_id)
        if feature is None:
            mismatches["not_in_snapshot"] += 1
            continue
        doc_id, text = feature
        raw_text = str(row.get("raw_text") or "")
        if str(row.get("doc_id")) != doc_id:
            mismatches["doc"] += 1
        if normalize_text(raw_text) != normalize_text(text):
            mismatches["text"] += 1
        records.append(
            ClaimRecord(occurrence_id=occurrence_id, doc_id=doc_id, raw_text=raw_text)
        )
    return records, mismatches


# ── 主流程 ───────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, default=CLAIMS_PATH)
    parser.add_argument("--requirements", type=Path, default=REQUIREMENTS_PATH)
    parser.add_argument("--diagram-nodes", type=Path, default=DIAGRAM_NODES_PATH)
    parser.add_argument("--diagrams", type=Path, default=DIAGRAMS_PATH)
    parser.add_argument("--features", type=Path, default=FEATURES_PATH)
    parser.add_argument("--vectors", type=Path, default=VECTORS_PATH)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--n-negatives", type=int, default=N_NEGATIVES)
    parser.add_argument("--query-limit", type=int, default=QUERY_LIMIT)
    parser.add_argument(
        "--anchor-scope",
        choices=("gold", "all_train"),
        default="gold",
        help="锚点claim集: gold=train gold对(协议默认) / all_train=train折全部claim(诊断)",
    )
    args = parser.parse_args()

    # ── 加载与gold构造 ──
    feature_texts = load_feature_texts(args.features)
    index, matrix = load_snapshot(args.vectors)
    claim_records, claim_mismatch = load_claim_records(args.claims, feature_texts)
    requirement_rows = load_requirement_rows(args.requirements)
    node_records, node_mismatch = load_node_records(
        args.diagram_nodes, args.diagrams, feature_texts
    )
    claim_texts = {
        occ: text
        for occ, (_, text) in feature_texts.items()
        if occ.startswith("claim:")
    }
    requirements_by_doc: dict[str, list[RequirementRow]] = {}
    for row in requirement_rows:
        requirements_by_doc.setdefault(row.doc_id, []).append(row)
    nodes_by_doc: dict[str, list[NodeRecord]] = {}
    for node in node_records:
        nodes_by_doc.setdefault(node.doc_id, []).append(node)

    gold_queries = build_gold_queries(
        claim_records, claim_texts, requirements_by_doc, nodes_by_doc
    )
    fold_map, fold_source = load_fold_map(args.runs_root)
    fallback_docs = sorted(
        {q.doc_id for q in gold_queries if fold_map is None or q.doc_id not in fold_map}
    )
    by_split: dict[str, list[GoldQuery]] = {"train": [], "dev": [], "test": []}
    for query in gold_queries:
        by_split[split_of_doc(query.doc_id, fold_map)].append(query)

    train_queries = sorted(by_split["train"], key=lambda q: q.claim_occurrence_id)
    test_queries = sorted(by_split["test"], key=lambda q: q.claim_occurrence_id)
    if len(test_queries) > args.query_limit:
        rng = np.random.default_rng(args.seed)
        keep = set(
            rng.choice(
                [q.claim_occurrence_id for q in test_queries],
                size=args.query_limit,
                replace=False,
            ).tolist()
        )
        test_queries = [q for q in test_queries if q.claim_occurrence_id in keep]
    if not train_queries:
        raise SystemExit(f"empty train split (gold claims={len(gold_queries)})")
    if not test_queries:
        raise SystemExit(f"empty test split (gold claims={len(gold_queries)})")

    reachable = reachable_nodes_by_doc(requirements_by_doc, nodes_by_doc)
    pools = build_pools(test_queries, reachable, args.n_negatives, args.seed)
    for query in test_queries:
        missing = query.gold_nodes - set(pools[query.claim_occurrence_id])
        if missing:
            raise SystemExit(
                f"gold node(s) missing from pool for {query.claim_occurrence_id}: "
                f"{sorted(missing)}"
            )
    golds = {q.claim_occurrence_id: q.gold_nodes for q in test_queries}

    # ── GPU前缀编码(无CPU兜底, 失败显式退出) ──
    bge = BgeLocal()
    mode = bge.ensure()
    # BgeLocal.ensure()透传torch设备名: "cuda"=GPU可用
    if mode != "cuda":
        raise SystemExit(
            f"BgeLocal mode={mode!r} (last_error={bge.last_error!r}); "
            "this protocol requires GPU encoding by design"
        )

    if args.anchor_scope == "gold":
        anchor_items = [(q.claim_occurrence_id, q.text) for q in train_queries]
    else:
        anchor_items = sorted(
            (record.occurrence_id, claim_texts[record.occurrence_id])
            for record in claim_records
            if split_of_doc(record.doc_id, fold_map) == "train"
        )
    anchor_ids = [occ for occ, _ in anchor_items]
    if len(anchor_ids) < 2:
        raise SystemExit(f"insufficient anchors: {len(anchor_ids)}")

    anchor_prefix_texts = [prefixed(text) for _, text in anchor_items]
    query_prefix_texts = [prefixed(q.text) for q in test_queries]
    encoded = bge.embed(anchor_prefix_texts + query_prefix_texts)

    def live_vector(text: str) -> np.ndarray:
        vector = encoded.get(text)
        if not vector:
            raise SystemExit(f"empty embedding returned for text: {text[:60]!r}")
        return np.asarray(vector, dtype=np.float32)

    # 活体编码 vs 快照向量一致性校验(模型/协议漂移守卫)
    validation = bge.embed([text for _, text in anchor_items[:64]])
    cosines: list[float] = []
    for occ, text in anchor_items[:64]:
        vector = validation.get(text)
        if not vector:
            raise SystemExit(f"empty validation embedding for text: {text[:60]!r}")
        live = np.asarray(vector, dtype=np.float64)
        snap = matrix[index[occ]].astype(np.float64)
        cosines.append(float(live @ snap / (np.linalg.norm(live) * np.linalg.norm(snap))))
    live_snapshot_cos = {
        "n": len(cosines),
        "mean": round(float(np.mean(cosines)), 6),
        "min": round(float(np.min(cosines)), 6),
    }
    if live_snapshot_cos["mean"] < LIVE_SNAPSHOT_COS_ABORT:
        raise SystemExit(
            f"live-vs-snapshot cos mean={live_snapshot_cos['mean']} < "
            f"{LIVE_SNAPSHOT_COS_ABORT}: model/protocol drift, aborting"
        )

    # ── Procrustes: prefix空间 → doc空间 ──
    anchor_prefix = np.vstack(
        [live_vector(text) for text in anchor_prefix_texts]
    ).astype(np.float64)
    anchor_target = np.vstack(
        [matrix[index[occ]] for occ in anchor_ids]
    ).astype(np.float64)
    mapping = fit_orthogonal_map(
        source=anchor_prefix,
        target=anchor_target,
        anchor_ids=anchor_ids,
        source_name="bge_query_prefix",
        target_name="bge_doc_snapshot",
    )
    query_prefix = np.vstack(
        [live_vector(text) for text in query_prefix_texts]
    ).astype(np.float64)
    query_transformed = mapping.transform(query_prefix)
    snapshot_claim = np.vstack(
        [matrix[index[q.claim_occurrence_id]] for q in test_queries]
    ).astype(np.float64)

    def group_scores(query_matrix: np.ndarray) -> dict[str, list[float]]:
        scores: dict[str, list[float]] = {}
        for position, query in enumerate(test_queries):
            pool = pools[query.claim_occurrence_id]
            node_matrix = np.vstack(
                [matrix[index[occ]] for occ in pool]
            ).astype(np.float64)
            scores[query.claim_occurrence_id] = (
                query_matrix[position] @ node_matrix.T
            ).tolist()
        return scores

    metrics = {
        "G0_doc_doc": evaluate_group(pools, group_scores(snapshot_claim), golds),
        "G1_prefix_doc": evaluate_group(pools, group_scores(query_prefix), golds),
        "G2_procrustes": evaluate_group(pools, group_scores(query_transformed), golds),
    }
    metric_keys = [f"recall@{k}" for k in KS] + [f"mrr@{MRR_K}", "auc"]
    gap = {
        key: round(metrics["G0_doc_doc"][key] - metrics["G1_prefix_doc"][key], 4)
        for key in metric_keys
    }
    recovery = {
        key: round(metrics["G2_procrustes"][key] - metrics["G1_prefix_doc"][key], 4)
        for key in metric_keys
    }

    pool_sizes = [len(pool) for pool in pools.values()]
    gold_sizes = [len(gold) for gold in golds.values()]
    n_nodes_with_id = sum(
        1 for node in node_records if extract_identifier_strings(node.text)
    )
    result: dict[str, Any] = {
        "protocol": (
            "cross-modal claim->diagram_node retrieval; query-prefix register gap "
            "vs Procrustes bridge (G0 doc-doc / G1 prefix-doc / G2 prefix+procrustes)"
        ),
        "gold_train": {
            "n_claims": len(train_queries),
            "n_pairs": sum(len(q.gold_nodes) for q in train_queries),
        },
        "gold_dev_excluded": {
            "n_claims": len(by_split["dev"]),
            "n_pairs": sum(len(q.gold_nodes) for q in by_split["dev"]),
        },
        "gold_test": {
            "n_claims": len(test_queries),
            "n_pairs": sum(len(q.gold_nodes) for q in test_queries),
        },
        "n_queries": len(test_queries),
        "groups": {
            name: {key: round(values[key], 4) for key in metric_keys}
            for name, values in metrics.items()
        },
        "register_gap_G0_minus_G1": gap,
        "procrustes_recovery_G2_minus_G1": recovery,
        "anchors": {
            "n": len(anchor_ids),
            "anchor_hash": mapping.anchor_hash,
            "scope": args.anchor_scope,
            "source": "bge_query_prefix (live GPU, no-prefix text prefixed)",
            "target": "bge_doc_snapshot (vectors.npz claim rows)",
        },
        "fold": {
            "source": fold_source,
            "fold_map": fold_map,
            "fallback_docs": fallback_docs,
            "roles": "0=test,1=dev,2|3=train (mirrors train_shared_projection)",
        },
        "pool": {
            "same_doc": "ID-reachable nodes (normalized text == some same-doc requirement title)",
            "n_negatives_per_query": args.n_negatives,
            "mean_size": round(float(np.mean(pool_sizes)), 1),
            "min_size": int(np.min(pool_sizes)),
            "max_size": int(np.max(pool_sizes)),
            "mean_golds_per_query": round(float(np.mean(gold_sizes)), 2),
        },
        "live_vs_snapshot_cos": live_snapshot_cos,
        "data_audit": {
            "n_claim_records": len(claim_records),
            "n_node_records": len(node_records),
            "n_nodes_with_regex_id": n_nodes_with_id,
            "claim_mismatch": claim_mismatch,
            "node_mismatch": node_mismatch,
        },
        "bge": {
            "mode": bge.mode,
            "device": bge.stats.get("device"),
            "dim": bge.stats.get("dim"),
            "n_prefix_texts_encoded": len(anchor_prefix_texts) + len(query_prefix_texts),
            "embed_ms": bge.stats.get("embed_ms"),
        },
        "notes": [
            "no diagram node text contains a regex identifier (verified at run time: "
            "n_nodes_with_regex_id in data_audit); the spec's claim-ID<->node-ID gold "
            "link is realized as the deterministic chain: claim canonical ID -> "
            "requirements.jsonl row (requirement_id or canonical raw_text ID match) "
            "-> title -> same-doc snapshot node with whitespace-normalized equal text",
            "IDs are extracted whitespace-tolerantly and canonicalized; hierarchical "
            "parent IDs that are hyphen-prefixes of another ID in the same claim are "
            "dropped (tree-table rows resolve to the deepest ID)",
            "candidate pool adapts '含ID node': same-doc pool = ID-reachable nodes "
            "(superset of gold), negatives = seeded sample of other docs' "
            "ID-reachable nodes; per-query RNG is seeded by (seed, sha1(claim id))",
            "query text = features.jsonl text (the exact string the snapshot vectors "
            "encode; 8 claim texts are 200-char snapshot-truncated, counted in "
            "data_audit.claim_mismatch.text); ID extraction uses claim_slot_features "
            "raw_text",
            "Recall@k is hit-style (query counts when any gold node ranks in top-k); "
            "MRR@10 uses the first gold's rank; AUC pools all (query, pool-node) "
            "score/label pairs",
            "G1 equals the deployed O1 retrieval protocol (query prefix + bare doc); "
            "G2 fits prefix->doc orthogonal Procrustes on train anchors with "
            "anchor_ids = claim occurrence ids",
            "dev-fold gold claims are excluded from anchors and queries",
        ],
    }
    run = open_run(
        "eval_crossmodal_procrustes",
        {
            "claims": str(args.claims),
            "requirements": str(args.requirements),
            "diagram_nodes": str(args.diagram_nodes),
            "diagrams": str(args.diagrams),
            "features": str(args.features),
            "vectors": str(args.vectors),
            "seed": args.seed,
            "n_negatives": args.n_negatives,
            "query_limit": args.query_limit,
            "anchor_scope": args.anchor_scope,
            "query_prefix": QUERY_PREFIX,
            "fold_source": fold_source,
        },
        args.runs_root,
    )
    run.log(
        stage="gold",
        n_gold_claims=len(gold_queries),
        n_train=len(train_queries),
        n_test=len(test_queries),
    )
    run.log(stage="anchors", n=len(anchor_ids), anchor_hash=mapping.anchor_hash)
    run.save_result(result)

    # ── 终端markdown表 ──
    header = [f"recall@{k}" for k in KS] + [f"mrr@{MRR_K}", "auc"]
    lines = [
        "| group | " + " | ".join(header) + " |",
        "|" + "---|" * (len(header) + 1),
    ]
    for name, values in metrics.items():
        cells = [GROUP_LABELS[name]] + [f"{values[key]:.4f}" for key in header]
        lines.append("| " + " | ".join(cells) + " |")
    print("\n".join(lines))
    print()
    print(
        "register gap (G0-G1):  "
        + ", ".join(f"{key} {gap[key]:+.4f}" for key in ("recall@10", "auc"))
    )
    print(
        "procrustes recovery (G2-G1):  "
        + ", ".join(f"{key} {recovery[key]:+.4f}" for key in ("recall@10", "auc"))
    )
    print(
        f"gold: train={result['gold_train']['n_claims']} claims/"
        f"{result['gold_train']['n_pairs']} pairs, "
        f"test={result['gold_test']['n_claims']} claims/"
        f"{result['gold_test']['n_pairs']} pairs, queries={len(test_queries)}, "
        f"anchors={len(anchor_ids)}"
    )
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
