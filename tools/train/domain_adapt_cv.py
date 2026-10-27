r"""域适配4折交叉验证: 诚实估计泛化增益.

v2全量训练在训练集上R@1=0.889(拟合上界, 不可报告为泛化).
本脚本做4折CV: 每折训练adapter于其余折的(deep查询, gold行)对,
测试在该折查询上, 按fold合并为全量262q的诚实数字.

协议:
  - 训练对: domain_adapt_deep_pairs.json 中 type=deep_row 的对
    (fold字段来自查询本身, 非人为指定)
  - 测试: gjb_ure_v3 deep_v3 eval查询(全262条, 按fold分批)
  - 语料池固定(1586表), adapter仅作用于冻结BGE向量之上

用法: python tools/train/domain_adapt_cv.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
PREFIX = "为这个句子生成表示以用于检索相关文章："


class DomainAdapter(nn.Module):
    def __init__(self, dim: int = 1024, hidden: int = 256) -> None:
        super().__init__()
        self.query_proj = nn.Sequential(
            nn.Linear(dim, hidden), nn.LayerNorm(hidden), nn.GELU(),
            nn.Linear(hidden, dim))
        self.doc_proj = nn.Sequential(
            nn.Linear(dim, hidden), nn.LayerNorm(hidden), nn.GELU(),
            nn.Linear(hidden, dim))
        for proj in (self.query_proj, self.doc_proj):
            nn.init.zeros_(proj[3].weight)
            nn.init.zeros_(proj[3].bias)

    def forward_query(self, x):
        return x + self.query_proj(x)

    def forward_doc(self, x):
        return x + self.doc_proj(x)


def train_adapter(q_arr, p_arr, device, epochs=40, batch=32, seed=42):
    adapter = DomainAdapter().to(device)
    optim = torch.optim.AdamW(adapter.parameters(), lr=5e-4, weight_decay=1e-4)
    tau = 0.07
    for ep in range(epochs):
        perm = np.random.default_rng(seed + ep).permutation(len(q_arr))
        for b0 in range(0, len(q_arr), batch):
            bi = perm[b0:b0 + batch]
            if len(bi) < 4:
                continue
            qt = torch.as_tensor(q_arr[bi], dtype=torch.float32).to(device)
            pt = torch.as_tensor(p_arr[bi], dtype=torch.float32).to(device)
            zq = nn.functional.normalize(adapter.forward_query(qt), dim=-1)
            zp = nn.functional.normalize(adapter.forward_doc(pt), dim=-1)
            sims = zq @ zp.T / tau
            labels = torch.arange(len(bi), device=device)
            loss = nn.functional.cross_entropy(sims, labels)
            reg = (zq - qt).norm(dim=-1).mean() + (zp - pt).norm(dim=-1).mean()
            loss = loss + 0.1 * reg
            optim.zero_grad()
            loss.backward()
            optim.step()
    return adapter


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    pairs = json.loads(
        (V3 / "domain_adapt_deep_pairs.json").read_text(encoding="utf-8"))
    ds = json.loads((V3 / "gjb_ure_v3.json").read_text(encoding="utf-8"))
    corpus = {c["chunk_id"]: c for c in ds["corpus"]}
    queries = [q for q in ds["queries"]
               if q["scene"] == "table_deep_v3" and q["split"] == "eval"]

    pool = [c for c in corpus.values() if c["type"] == "table"]
    ids = [c["chunk_id"] for c in pool]
    idx = {cid: i for i, cid in enumerate(ids)}
    n = len(pool)
    raw_units = [[u for u in ([c["title"]] + c["units"]) if u] for c in pool]
    unit_texts = [u for ru in raw_units for u in ru]
    seg = np.cumsum([0] + [len(ru) for ru in raw_units])
    folds = sorted({q["fold"] for q in queries})
    print(f"CV协议: {len(queries)}q × {len(folds)}折, 池{n}表, "
          f"训练对仅用deep_row类型({sum(1 for p in pairs if p['type'] == 'deep_row')})")

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    # 冻结编码: 单元/查询/训练文本 (一次性)
    print("编码单元...", flush=True)
    uvecs = bge.embed(unit_texts)
    U_raw = np.stack([np.asarray(uvecs.get(u, [0.0] * 1024),
                               dtype=np.float32) for u in unit_texts])
    U_raw = U_raw / np.maximum(np.linalg.norm(U_raw, axis=1, keepdims=True), 1e-8)

    q_texts = [PREFIX + q["query"][:200] for q in queries]
    qvecs = bge.embed(q_texts)
    Q_raw = np.stack([np.asarray(qvecs.get(t, [0.0] * 1024),
                               dtype=np.float32) for t in q_texts])
    Q_raw = Q_raw / np.maximum(np.linalg.norm(Q_raw, axis=1, keepdims=True), 1e-8)

    # 训练对(仅deep_row)的冻结向量
    train_pairs = [p for p in pairs if p["type"] == "deep_row"]
    tp_q = [p["query"][:200] for p in train_pairs]
    tp_p = [p["positive"][:200] for p in train_pairs]
    uniq = list(dict.fromkeys(tp_q + tp_p))
    tv = bge.embed(uniq)
    tv_np = {t: np.asarray(v, dtype=np.float32) for t, v in tv.items() if v}
    # 按查询文本映射fold
    q2fold = {q["query"]: q["fold"] for q in queries}

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # IDF(全局, 与训练无关)
    dfc = {}
    for ru in raw_units:
        for u in set(ru):
            dfc[u] = dfc.get(u, 0) + 1
    idf = np.asarray(
        [np.log(1 + n / max(dfc.get(u, 1), 1)) for u in unit_texts],
        dtype=np.float32)

    # 基线(无adapter) — 应复现0.340
    from eval_baselines import metrics_rows
    Ut = torch.as_tensor(U_raw, dtype=torch.float32).to(device)
    U_base = Ut.T.cpu().numpy()

    def eval_with(adapter, fold_queries, fold_q_idx):
        if adapter is None:
            U = U_base
            Q = Q_raw[fold_q_idx]
        else:
            with torch.no_grad():
                U = nn.functional.normalize(
                    adapter.forward_doc(Ut), dim=-1).cpu().numpy().T
                Q = nn.functional.normalize(
                    adapter.forward_query(
                        torch.as_tensor(Q_raw[fold_q_idx],
                                        dtype=torch.float32).to(device)),
                    dim=-1).cpu().numpy()
        sc, golds = [], []
        for j, q in enumerate(fold_queries):
            g = {idx[t] for t in q["expected"] if t in idx}
            golds.append(g)
            qv = Q[j] / max(float(np.linalg.norm(Q[j])), 1e-8)
            sims_u = (U.T @ qv) * idf
            segmax = np.asarray(
                [sims_u[seg[i]:seg[i + 1]].max() if seg[i] < seg[i + 1] else -1e9
                 for i in range(n)])
            sc.append(segmax)
        return metrics_rows(sc, golds, n), len(fold_queries)

    # CV主循环
    cv_sc, cv_golds = [], []
    for k in folds:
        test_idx = [i for i, q in enumerate(queries) if q["fold"] == k]
        train_idx = [i for i, p in enumerate(train_pairs)
                     if q2fold.get(p["query"], -1) != k]
        q_arr = np.stack([tv_np.get(train_pairs[i]["query"][:200],
                                    np.zeros(1024, dtype=np.float32))
                          for i in train_idx])
        p_arr = np.stack([tv_np.get(train_pairs[i]["positive"][:200],
                                    np.zeros(1024, dtype=np.float32))
                          for i in train_idx])
        t0 = time.time()
        adapter = train_adapter(q_arr, p_arr, device)
        # 用adapter在该折查询上打分(收集到全局列表)
        fold_queries = [queries[i] for i in test_idx]
        m, cnt = eval_with(adapter, fold_queries, test_idx)
        print(f"  fold{k}: train={len(train_idx)} test={cnt} "
              f"R@1={m['R@1']:.3f} ({time.time()-t0:.0f}s)")
        # 收集原始打分以合并全量指标
        with torch.no_grad():
            U_ad = nn.functional.normalize(
                adapter.forward_doc(Ut), dim=-1).cpu().numpy().T
            Q = nn.functional.normalize(
                adapter.forward_query(
                    torch.as_tensor(Q_raw[test_idx],
                                    dtype=torch.float32).to(device)),
                dim=-1).cpu().numpy()
        for j, q in enumerate(fold_queries):
            g = {idx[t] for t in q["expected"] if t in idx}
            cv_golds.append(g)
            qv = Q[j] / max(float(np.linalg.norm(Q[j])), 1e-8)
            sims_u = (U_ad.T @ qv) * idf
            segmax = np.asarray(
                [sims_u[seg[i]:seg[i + 1]].max() if seg[i] < seg[i + 1] else -1e9
                 for i in range(n)])
            cv_sc.append(segmax)

    m_cv = metrics_rows(cv_sc, cv_golds, n)
    print(f"\nO1-unit(adapted, 4折CV泛化): R@1={m_cv['R@1']:.3f} "
          f"R@5={m_cv['R@5']:.3f} MRR={m_cv['MRR@10']:.3f}")
    print("基线(无adapter, 同管线): R@1=0.340 R@5=0.550 MRR=0.429")

    outp = (BASE / "data/gjb_438c/data_assets/evalsets/results/"
            "S1_deep_v3_all.json")
    d = json.loads(outp.read_text(encoding="utf-8"))
    d["results"]["O1-unit(adapted-4fold-CV)"] = m_cv
    outp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→ 已写入S1结果")


if __name__ == "__main__":
    main()
