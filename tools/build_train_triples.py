r"""检索训练三元组构建: 正对合并 + RocketQAv2式双源hard negative挖掘.

谱系: RocketQAv2 (Qu et al. 2021) 的训练数据工程——
(query, positive, hard negatives)三元组, hard negatives由
BM25+dense双检索器对同一query的top结果中去掉正例后取得
(梯度上"最像正例的负例"). BGE训练协议同构(1 pos + N negs).

正对来源(合并去重, source字段: hq|eval|alpaca):
  hq     假想查询→宿主chunk (docT5query; 含v2参数/数值型查询)
  eval   评测集前2/3(实体组边界划分, 无实体泄漏)的entity query
         →每个期望chunk各成一正对(期望全集作为负例排除集)
  alpaca easydataset srs_alpaca_full.jsonl域内条目: question→原文chunk
         (确定性锚匹配: ①input"正文:"片段子串唯一命中
          ②instruction「表N..」/input"表格: 表N.."→table_caption唯一文档命中;
          对不上跳过)

hard negative挖掘(简化RocketQAv2双源, 全库范围):
  每个query: BM25 top-30(EvidenceStore.bm25_rank) + dense top-30
  (原生BGE向量缓存dense_index.pkl余弦, query侧BGE现算+指令前缀)
  → 排除该query期望集 → BM25/dense按名次交错取top-15(各半,
  单源枯竭时另一源补足)

落盘: data/gjb_438c/data_assets/retrieval_train/triples.json
  [{"query": str, "pos_chunk_id": str, "neg_chunk_ids": [str×15],
    "source": "hq|eval|alpaca"}]
统计 → 同目录 triples_stats.json (来源分布/负例数分布/BM25↔dense重合率)

用法:
  python tools/build_train_triples.py               # 构建三元组
  python tools/build_train_triples.py --inspect 30  # 人工抽检已有triples
"""
from __future__ import annotations

import argparse
import json
import pickle
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.blackboard.evidence_store import EvidenceStore  # noqa: E402

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
HQ = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
HQ2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"
EVAL = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
ALPACA = BASE / "data/gjb_438c/easydataset/srs_alpaca_full.jsonl"
DENSE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
OUT_DIR = BASE / "data/gjb_438c/data_assets/retrieval_train"
OUT = OUT_DIR / "triples.json"
STATS = OUT_DIR / "triples_stats.json"

N_HARD = 15                # 每正对hard negative数(BM25/dense各半)
MINE_TOPK = 30             # 双源挖掘深度(RocketQAv2同量级)
EVAL_TRAIN_FRAC = 2 / 3    # eval集训练侧比例(实体组边界对齐)
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："  # BGE检索指令前缀(与hybrid_recall一致)
INSPECT_SEED = 42          # 抽检可复现种子

_WS = re.compile(r"\s+")
_HTML = re.compile(r"<[^>]+>")
_TAB_INSTR = re.compile(r"表格?「(表[^」]{1,50})」")


def _norm(s: str) -> str:
    """匹配用规范化: 去全部空白."""
    return _WS.sub("", s or "")


def _clean_display(text: str, n: int) -> str:
    """抽检显示用: HTML剥离+空白压缩+截断."""
    t = _WS.sub(" ", _HTML.sub(" ", text or "")).strip()
    return t[:n]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════
# 正对构建(三源)
# ═══════════════════════════════════════════════════════════

def build_pairs_hq(chunk_ids: set[str]) -> tuple[list[dict], dict]:
    """假想查询(A6 + v2参数型) → 宿主chunk正对."""
    pairs: list[dict] = []
    st: dict[str, int] = {"hq_chunks": 0, "hq2_chunks": 0, "invalid_chunk": 0,
                          "bad_query": 0}
    for path, key in ((HQ, "hq_chunks"), (HQ2, "hq2_chunks")):
        if not path.exists():
            continue
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for cid, queries in data.items():
            if cid not in chunk_ids:
                st["invalid_chunk"] += 1
                continue
            if not isinstance(queries, list) or not queries:
                continue
            st[key] += 1
            for q in queries:
                qs = str(q).strip()
                if len(qs) < 2:
                    st["bad_query"] += 1
                    continue
                pairs.append({"query": qs, "pos": cid, "expected": {cid},
                              "source": "hq"})
    return pairs, st


def eval_train_split(evalset: list[dict]) -> tuple[list[dict], dict]:
    """前2/3训练侧, 按实体组边界对齐(无跨侧实体泄漏)."""
    target = round(len(evalset) * EVAL_TRAIN_FRAC)
    bounds = [i for i in range(1, len(evalset))
              if evalset[i].get("entity") != evalset[i - 1].get("entity")]
    split = min(bounds + [len(evalset)], key=lambda b: abs(b - target))
    train, test = evalset[:split], evalset[split:]
    info = {
        "n_eval": len(evalset), "target_2_3": target, "split_at": split,
        "n_train_queries": len(train), "n_test_queries": len(test),
        "n_train_entities": len({e.get("entity") for e in train}),
        "n_test_entities": len({e.get("entity") for e in test}),
        "entity_leak": len({e.get("entity") for e in train}
                           & {e.get("entity") for e in test}),
    }
    return train, info


def build_pairs_eval(chunk_ids: set[str]) -> tuple[list[dict], dict]:
    """eval训练侧query → 每个期望chunk一正对(期望全集=负例排除集)."""
    evalset = _load_json(EVAL)
    if not isinstance(evalset, list):
        return [], {"n_eval": 0}
    train, info = eval_train_split(evalset)
    pairs: list[dict] = []
    st: dict[str, int] = {"empty_expected": 0, "invalid_expected": 0}
    for e in train:
        q = str(e.get("query") or "").strip()
        exp_raw = (e.get("expected") or {}).get("chunk_ids") or []
        exp = [cid for cid in exp_raw if cid in chunk_ids]
        if not q or len(q) < 2:
            st["empty_expected"] += 1
            continue
        if not exp:
            st["invalid_expected"] += 1
            continue
        for cid in exp:
            pairs.append({"query": q, "pos": cid, "expected": set(exp),
                          "source": "eval"})
    st.update(info)
    return pairs, st


def build_pairs_alpaca(chunks: list[dict],
                       chunk_ids: set[str]) -> tuple[list[dict], dict]:
    """easydataset alpaca域内条目 → 确定性锚匹配到原文chunk.

    锚优先级: ①input"正文:"片段(规范化子串, 唯一命中才收)
    ②表格标题(instruction「表N..」 ∪ input"表格: 表N..", 归一化后
    table_caption精确等值, 恰好命中一个文档才收; 章节锚歧义大不使用).
    对不上/歧义 → 跳过(宁缺毋滥: 假阳性正对直接污染训练集).
    """
    cap_index: dict[str, list[dict]] = {}
    norm_texts: list[tuple[str, str]] = []
    for c in chunks:
        cap = _norm(c.get("table_caption") or "")
        if cap:
            cap_index.setdefault(cap, []).append(c)
        norm_texts.append((c.get("chunk_id", ""), _norm(c.get("text") or "")))

    pairs: list[dict] = []
    st: dict[str, int] = {"n_rows": 0, "matched_body": 0, "matched_caption": 0,
                          "skip_noanchor": 0, "skip_ambiguous": 0}
    with open(ALPACA, encoding="utf-8") as f:
        for line in f:
            st["n_rows"] += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                st["skip_noanchor"] += 1
                continue
            q = str(row.get("instruction") or "").strip()
            inp = str(row.get("input") or "").strip()
            if len(q) < 4:
                st["skip_noanchor"] += 1
                continue
            pos: str | None = None
            if inp.startswith("正文:"):
                snip = _norm(inp[3:])[:80]
                if len(snip) >= 12:
                    hits = [cid for cid, t in norm_texts if snip in t]
                    if len(hits) == 1:
                        pos = hits[0]
                        st["matched_body"] += 1
                    elif len(hits) > 1:
                        st["skip_ambiguous"] += 1
                        continue
            if pos is None:
                caps = set()
                m = _TAB_INSTR.search(q)
                if m:
                    caps.add(_norm(m.group(1)))
                if inp.startswith("表格:"):
                    caps.add(_norm(inp[3:]))
                if not caps:
                    st["skip_noanchor"] += 1
                    continue
                cand: list[dict] = []
                for cap in caps:
                    cand.extend(cap_index.get(cap, []))
                docs = {c.get("doc", "") for c in cand}
                if not cand:
                    st["skip_noanchor"] += 1
                    continue
                if len(docs) > 1:
                    st["skip_ambiguous"] += 1
                    continue
                heads = [c for c in cand
                         if "[表格标题:" in (c.get("text") or "")]
                pool = (heads or cand)
                pool.sort(key=lambda c: c.get("chunk_id", ""))
                pos = pool[0].get("chunk_id", "")
                st["matched_caption"] += 1
            if pos and pos in chunk_ids:
                pairs.append({"query": q, "pos": pos, "expected": {pos},
                              "source": "alpaca"})
    return pairs, st


def dedup_pairs(pairs: list[dict]) -> tuple[list[dict], int]:
    """(query, pos)全局去重: 保序(构建顺序=来源优先级 hq>eval>alpaca)."""
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for p in pairs:
        key = (p["query"], p["pos"])
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out, len(pairs) - len(out)


# ═══════════════════════════════════════════════════════════
# hard negative挖掘(双源)
# ═══════════════════════════════════════════════════════════

def _interleave(bm: list[str], dn: list[str], n: int) -> list[str]:
    """BM25/dense候选按名次交错合并去重, 截n条(各半, 单源枯竭互补)."""
    out: list[str] = []
    seen: set[str] = set()
    ia = ib = 0
    while len(out) < n and (ia < len(bm) or ib < len(dn)):
        if ia < len(bm):
            cid = bm[ia]
            ia += 1
            if cid not in seen:
                seen.add(cid)
                out.append(cid)
            if len(out) >= n:
                break
        if ib < len(dn):
            cid = dn[ib]
            ib += 1
            if cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


def dense_topk(queries: list[str], top_k: int) -> dict[str, list[str]]:
    """原生BGE dense检索: dense_index.pkl向量缓存 + query现算余弦top-k.

    query侧走本地BGE(bge-local, GPU优先, 磁盘缓存可复现)并加
    BGE检索指令前缀(与hybrid_recall._dense一致).
    """
    import numpy as np
    from algorithms.common.bge_local import BgeLocal

    with open(DENSE, "rb") as f:
        index = pickle.load(f)
    if not isinstance(index, dict) or not index:
        raise RuntimeError(f"dense_index.pkl为空/损坏: {DENSE}")
    ids = list(index)
    mat = np.asarray([index[cid] for cid in ids], dtype=np.float32)
    mat /= np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)

    bge = BgeLocal()  # 默认磁盘缓存(bge_cache.pkl): query向量可复现
    mode = bge.ensure()
    if mode == "unavailable":
        raise RuntimeError(f"本地BGE不可用: {bge.last_error}")
    print(f"  dense通道: BGE mode={mode}, chunk向量={len(ids)}, "
          f"待嵌入query={len(queries)}")

    texts = [QUERY_PREFIX + q[:200] for q in queries]
    vecs = bge.embed(texts)
    rows: list[list[float]] = []
    kept: list[str] = []
    for q, t in zip(queries, texts):
        v = vecs.get(t) or []
        if len(v) == mat.shape[1]:
            rows.append(v)
            kept.append(q)
    if not rows:
        raise RuntimeError("query embedding全部失败")
    qmat = np.asarray(rows, dtype=np.float32)
    qmat /= np.maximum(np.linalg.norm(qmat, axis=1, keepdims=True), 1e-8)

    sims = qmat @ mat.T
    k = min(top_k, mat.shape[0])
    part = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]
    out: dict[str, list[str]] = {}
    for qi, cand_idx in enumerate(part):
        order = cand_idx[np.argsort(-sims[qi, cand_idx], kind="stable")]
        out[kept[qi]] = [ids[j] for j in order]
    n_drop = len(queries) - len(kept)
    if n_drop:
        print(f"  ⚠ {n_drop}个query嵌入失败(dense侧无候选, 由BM25侧补)")
    return out


def mine_negatives(pairs: list[dict],
                   store: EvidenceStore) -> tuple[dict[int, list[str]], dict]:
    """双源挖掘: 返回 pair_index → hard neg列表 + 重合率统计.

    同query的多正对共享同一期望全集(负例排除集=并集), 挖掘按
    unique query计算一次后分发.
    """
    by_query: dict[str, dict[str, Any]] = {}
    for i, p in enumerate(pairs):
        g = by_query.setdefault(p["query"], {"expected": set(), "idx": []})
        g["expected"] |= p["expected"]
        g["idx"].append(i)
    queries = list(by_query)
    print(f"挖掘: {len(pairs)}正对 / {len(queries)}个unique query, "
          f"每query BM25+dense top-{MINE_TOPK}")

    t0 = time.time()
    bm25: dict[str, list[str]] = {}
    for j, q in enumerate(queries):
        bm25[q] = [h["chunk_id"] for h in store.bm25_rank(q, top_k=MINE_TOPK)]
        if (j + 1) % 1000 == 0:
            print(f"  BM25进度 {j + 1}/{len(queries)} "
                  f"({time.time() - t0:.0f}s)")
    bm25_s = time.time() - t0
    print(f"  BM25完成: {bm25_s:.0f}s")

    t1 = time.time()
    dense = dense_topk(queries, MINE_TOPK)
    dense_s = time.time() - t1
    print(f"  dense完成: {dense_s:.0f}s")

    negs: dict[int, list[str]] = {}
    inter_sum = union_sum = 0.0
    n_overlap_valid = 0
    inter_sizes: list[int] = []
    jaccards: list[float] = []
    for q, g in by_query.items():
        exp = g["expected"]
        bm = [cid for cid in bm25.get(q, []) if cid not in exp]
        dn = [cid for cid in dense.get(q, []) if cid not in exp]
        merged = _interleave(bm, dn, N_HARD)
        for i in g["idx"]:
            negs[i] = merged
        b_set, d_set = set(bm[:N_HARD]), set(dn[:N_HARD])
        inter, union = len(b_set & d_set), len(b_set | d_set)
        if union:
            inter_sum += inter
            union_sum += union
            n_overlap_valid += 1
            inter_sizes.append(inter)
            jaccards.append(inter / union)
    stats = {
        "n_unique_queries": len(queries),
        "bm25_elapsed_s": round(bm25_s, 1),
        "dense_elapsed_s": round(dense_s, 1),
        "overlap_pairs_valid": n_overlap_valid,
        "overlap_mean_intersection": round(
            sum(inter_sizes) / max(len(inter_sizes), 1), 2),
        "overlap_mean_jaccard": round(
            sum(jaccards) / max(len(jaccards), 1), 4),
        "overlap_pooled_jaccard": round(
            inter_sum / max(union_sum, 1.0), 4),
    }
    return negs, stats


# ═══════════════════════════════════════════════════════════
# 主流程与抽检
# ═══════════════════════════════════════════════════════════

def build() -> int:
    chunks = _load_json(CHUNKS)
    if not isinstance(chunks, list):
        raise RuntimeError(f"chunks损坏: {CHUNKS}")
    chunk_ids = {c.get("chunk_id", "") for c in chunks}
    t0 = time.time()

    hq_pairs, hq_st = build_pairs_hq(chunk_ids)
    eval_pairs, eval_st = build_pairs_eval(chunk_ids)
    alpaca_pairs, alpaca_st = build_pairs_alpaca(chunks, chunk_ids)
    pairs, n_dup = dedup_pairs(hq_pairs + eval_pairs + alpaca_pairs)
    print(f"正对: hq={len(hq_pairs)} eval={len(eval_pairs)} "
          f"alpaca={len(alpaca_pairs)} → 去重后{len(pairs)}(丢弃{n_dup})")
    print(f"eval切分: {json.dumps({k: eval_st.get(k) for k in (
        'split_at', 'n_train_queries', 'n_train_entities',
        'n_test_entities', 'entity_leak')}, ensure_ascii=False)}")
    print(f"alpaca匹配: {json.dumps(alpaca_st, ensure_ascii=False)}")
    if not pairs:
        raise RuntimeError("无正对, 中止")

    store = EvidenceStore()
    negs, mine_st = mine_negatives(pairs, store)

    triples: list[dict] = []
    n_negs: list[int] = []
    n_pos_in_negs = 0
    for i, p in enumerate(pairs):
        neg_list = [cid for cid in negs.get(i, [])
                    if cid != p["pos"] and cid in chunk_ids]
        if p["pos"] in negs.get(i, []):
            n_pos_in_negs += 1
        triples.append({"query": p["query"], "pos_chunk_id": p["pos"],
                        "neg_chunk_ids": neg_list, "source": p["source"]})
        n_negs.append(len(neg_list))

    by_src: dict[str, int] = {}
    for t in triples:
        by_src[t["source"]] = by_src.get(t["source"], 0) + 1
    full15 = sum(1 for n in n_negs if n >= N_HARD)
    sorted_negs = sorted(n_negs)
    stats = {
        "n_triples": len(triples),
        "n_pairs_by_source": by_src,
        "n_unique_queries": mine_st["n_unique_queries"],
        "n_dup_dropped": n_dup,
        "n_negs_mean": round(sum(n_negs) / len(n_negs), 2),
        "n_negs_min": min(n_negs),
        "n_negs_p50": sorted_negs[len(sorted_negs) // 2],
        "n_negs_p95": sorted_negs[min(int(len(sorted_negs) * 0.95),
                                      len(sorted_negs) - 1)],
        "n_triples_full15": full15,
        "n_pos_in_negs_violations": n_pos_in_negs,
        "hard_neg_overlap": {k: mine_st[k] for k in (
            "overlap_mean_intersection", "overlap_mean_jaccard",
            "overlap_pooled_jaccard", "overlap_pairs_valid")},
        "mining": {k: mine_st[k] for k in (
            "n_unique_queries", "bm25_elapsed_s", "dense_elapsed_s")},
        "hq": hq_st,
        "eval": eval_st,
        "alpaca": alpaca_st,
        "protocol": {
            "n_hard": N_HARD, "mine_topk": MINE_TOPK,
            "neg_mix": "BM25/dense按名次交错各半(单源枯竭互补)",
            "neg_exclusion": "该query期望全集(hq=宿主chunk; eval=全部期望chunks;"
                             "alpaca=锚匹配chunk)",
            "dense": "dense_index.pkl原生BGE向量余弦; query侧bge-local"
                     f"+指令前缀({QUERY_PREFIX[:12]}…)",
            "eval_split": f"前{EVAL_TRAIN_FRAC:.3f}实体组边界对齐",
        },
        "elapsed_s": round(time.time() - t0, 1),
        "date": time.strftime("%Y-%m-%d"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(triples, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    print("\n══ 三元组统计 ══")
    print(f"总对数: {stats['n_triples']}  来源: {json.dumps(by_src)}"
          f"  unique query: {stats['n_unique_queries']}")
    print(f"hard neg/对: mean={stats['n_negs_mean']} "
          f"p50={stats['n_negs_p50']} p95={stats['n_negs_p95']} "
          f"min={stats['n_negs_min']} 满15对={full15}")
    print(f"BM25↔dense重合: 平均|∩|={stats['hard_neg_overlap']['overlap_mean_intersection']} "
          f"平均Jaccard={stats['hard_neg_overlap']['overlap_mean_jaccard']} "
          f"总体Jaccard={stats['hard_neg_overlap']['overlap_pooled_jaccard']}")
    if n_pos_in_negs:
        print(f"⚠ 正例混入负例 {n_pos_in_negs} 处(已剔除)")
    print(f"耗时 {stats['elapsed_s']}s")
    print(f"资产 → {OUT}")
    print(f"统计 → {STATS}")
    return 0


def inspect(n: int, seed: int) -> int:
    """抽检模式: 随机n对, 打印query+正例文本(前80字)+前3负例(前40字)."""
    if not OUT.exists():
        raise RuntimeError(f"未找到{OUT}, 先运行构建")
    triples = _load_json(OUT)
    chunks = _load_json(CHUNKS)
    by_id = {c.get("chunk_id", ""): c for c in chunks}
    sample = random.Random(seed).sample(triples, min(n, len(triples)))
    print(f"━━━ 抽检 {len(sample)}/{len(triples)} 对 (seed={seed}) ━━━")
    for i, t in enumerate(sample, 1):
        pos = by_id.get(t["pos_chunk_id"], {})
        print(f"\n[{i:02d}] source={t['source']}  negs={len(t['neg_chunk_ids'])}")
        print(f"  Q  {t['query']}")
        print(f"  P  {pos.get('doc', '?')} §{pos.get('section', '?')} "
              f"[{pos.get('type', '?')}] "
              f"{_clean_display(pos.get('text') or '', 80)}")
        for j, cid in enumerate(t["neg_chunk_ids"][:3], 1):
            c = by_id.get(cid, {})
            print(f"  N{j} {c.get('doc', '?')} §{c.get('section', '?')} "
                  f"[{c.get('type', '?')}] "
                  f"{_clean_display(c.get('text') or '', 40)}")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="检索训练三元组构建(RocketQAv2式)")
    ap.add_argument("--inspect", type=int, default=None, metavar="N",
                    help="抽检模式: 从已有triples.json随机抽N对人工核查")
    ap.add_argument("--seed", type=int, default=INSPECT_SEED,
                    help=f"抽检随机种子(默认{INSPECT_SEED})")
    args = ap.parse_args()
    if args.inspect is not None:
        return inspect(args.inspect, args.seed)
    return build()


if __name__ == "__main__":
    raise SystemExit(main())
