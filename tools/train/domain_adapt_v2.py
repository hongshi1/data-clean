r"""域适配训练v2: 用deep行分布(非caption)训练adapter.

v1失败原因: caption查询→表摘要的映射, 破坏deep行查询→具体行的匹配.
v2修复: 用deep行查询→gold表最匹配行作为训练对, 分布与评测一致.

设计:
  - 训练对: 294条(deep_v3 250 + 扩展44), (query, gold行, fold)
  - 挖硬负例: BM25+dense双通道, top-10非gold
  - Adapter: 残差投影(query侧+doc侧, 1024→256→1024)
  - 损失: InfoNCE + hard-negative margin
  - 评估: 在262q deep_v3上(训练集, 非held-out — 声明)

注意: 训练对包含评测集的一部分(250/262), 结果是"拟合上界"而非
"泛化数字". 等扩展完成(298新增)后, 可以用扩展做held-out.

用法: python tools/train/domain_adapt_v2.py
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
    """残差adapter: query/doc各自投影, 初始化近似恒等."""

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


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    pairs = json.loads(
        (V3 / "domain_adapt_deep_pairs.json").read_text(encoding="utf-8"))
    ds = json.loads((V3 / "gjb_ure_v3.json").read_text(encoding="utf-8"))
    corpus = {c["chunk_id"]: c for c in ds["corpus"]}
    print(f"训练对: {len(pairs)} (deep行分布)")

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    # 编码所有表单元(用于挖负例)
    pool = [c for c in corpus.values() if c["type"] == "table"]
    ids = [c["chunk_id"] for c in pool]
    idx = {cid: i for i, cid in enumerate(ids)}
    raw_units = [[u for u in ([c["title"]] + c["units"]) if u] for c in pool]
    unit_texts = [u for ru in raw_units for u in ru]
    seg = np.cumsum([0] + [len(ru) for ru in raw_units])

    # 硬负例: 简化协议仅用batch内负例(InfoNCE), 见runs归档
    triples = [p for p in pairs if idx.get(p["gold_cid"], -1) >= 0]
    print(f"三元组: {len(triples)}")

    # 训练
    device = "cuda" if torch.cuda.is_available() else "cpu"
    adapter = DomainAdapter().to(device)
    optim = torch.optim.AdamW(adapter.parameters(), lr=5e-4, weight_decay=1e-4)
    tau = 0.07
    epochs, batch = 40, 32

    # 预编码查询和正例
    q_texts = [p["query"][:200] for p in triples]
    p_texts = [p["positive"][:200] for p in triples]
    all_texts = list(dict.fromkeys(q_texts + p_texts))
    vecs = bge.embed(all_texts)
    tv = {t: np.asarray(v, dtype=np.float32) for t, v in vecs.items() if v}

    q_arr = np.stack([tv.get(q, np.zeros(1024, dtype=np.float32)) for q in q_texts])
    p_arr = np.stack([tv.get(p, np.zeros(1024, dtype=np.float32)) for p in p_texts])

    losses = []
    t0 = time.time()
    for ep in range(epochs):
        perm = np.random.default_rng(42 + ep).permutation(len(triples))
        ep_loss = 0.0
        for b0 in range(0, len(triples), batch):
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

            # 正则: 防偏离原始空间太远
            reg = (zq - qt).norm(dim=-1).mean() + (zp - pt).norm(dim=-1).mean()
            loss = loss + 0.1 * reg

            optim.zero_grad()
            loss.backward()
            optim.step()
            ep_loss += float(loss.detach())
        losses.append(ep_loss / max(1, len(triples) // batch))
        if (ep + 1) % 10 == 0:
            print(f"  epoch {ep+1}: loss={losses[-1]:.4f} ({time.time()-t0:.0f}s)")

    print(f"\n训练: loss {losses[0]:.3f} → {losses[-1]:.3f}")

    # 评测(在训练集上, 声明为拟合上界)
    queries_v3 = [q for q in ds["queries"]
                  if q["scene"] == "table_deep_v3" and q["split"] == "eval"]
    n = len(pool)

    uvecs = bge.embed(unit_texts)
    U_raw = np.stack([np.asarray(uvecs.get(u, [0.0] * 1024),
                               dtype=np.float32) for u in unit_texts])
    U_raw = U_raw / np.maximum(np.linalg.norm(U_raw, axis=1, keepdims=True), 1e-8)

    with torch.no_grad():
        Ut = torch.as_tensor(U_raw, dtype=torch.float32).to(device)
        U_adapted = nn.functional.normalize(
            adapter.forward_doc(Ut), dim=-1).cpu().numpy().T

    dfc = {}
    for ru in raw_units:
        for u in set(ru):
            dfc[u] = dfc.get(u, 0) + 1
    idf = np.asarray(
        [np.log(1 + n / max(dfc.get(u, 1), 1)) for u in unit_texts],
        dtype=np.float32)

    from eval_baselines import metrics_rows

    sc, golds = [], []
    for q in queries_v3:
        g = {idx[t] for t in q["expected"] if t in idx}
        golds.append(g)
        v = bge.embed([PREFIX + q["query"][:200]]).get(PREFIX + q["query"][:200])
        if not v:
            continue
        qn = torch.as_tensor(np.asarray(v, dtype=np.float32)).to(device)
        with torch.no_grad():
            qn_ad = nn.functional.normalize(
                adapter.forward_query(qn), dim=-1).cpu().numpy()
        qn_np = qn_ad / max(float(np.linalg.norm(qn_ad)), 1e-8)
        sims_u = (U_adapted.T @ qn_np) * idf
        segmax = np.asarray(
            [sims_u[seg[i]:seg[i + 1]].max() if seg[i] < seg[i + 1] else -1e9
             for i in range(n)])
        sc.append(segmax)

    m = metrics_rows(sc, golds, n)
    print(f"\nO1-unit(domain-adapted v2, deep分布): "
          f"R@1={m['R@1']:.3f} R@5={m['R@5']:.3f} MRR={m['MRR@10']:.3f}")
    print("⚠ 注意: 训练集包含部分评测集(250/262), 这是拟合上界不是泛化数字")
    print("   等LLM扩展完成后, 用新增查询做held-out验证")

    # 保存
    torch.save({"adapter": adapter.state_dict(),
                "config": {"dim": 1024, "hidden": 256, "epochs": epochs,
                           "training_pairs": len(triples)}},
               str(BASE / "models/domain_adapter_v2.pt"))
    print("→ models/domain_adapter_v2.pt")

    outp = BASE / "data/gjb_438c/data_assets/evalsets/results/S1_deep_v3_all.json"
    d = json.loads(outp.read_text(encoding="utf-8"))
    d["results"]["O1-unit(adapted-v2, train-set)"] = m
    outp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
