r"""Qwen3-Embedding骨干无关性检验(RQ1的跨骨干验证).

科研问题: O1-unit对dense的单元级优势是否依赖BGE骨干?
在2025年的Qwen3-Embedding-0.6B骨干上重跑同协议:
  - O1-unit数学: max_u[cos(q,u)×IDF(u)] (Qwen3 query格式=官方chat模板)
  - dense对照: 文档级512截断余弦
场景: GJB联合438q(与S6同查询集)

判定: 若Qwen3骨干上O1-unit仍显著领先同骨干dense → 单元级claim
骨干无关; 参照BGE骨干(O1 0.365 vs B1-dense 0.078).

用法: python tools/eval/eval_qwen3_backbone.py
产出: results/S10_qwen3_backbone.json + runs归档
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
MODEL_DIR = BASE / "models/embedding/qwen3-embedding-0.6b"
TASK = "Given a query, retrieve relevant passages that answer the query"
Q_PREFIX = f"<|im_start|>system\n{TASK}<|im_end|>\n<|im_start|>user\n"
Q_SUFFIX = "<|im_end|>"


class Qwen3Encoder:
    """Qwen3-Embedding编码器: last-token池化+L2归一(bf16 GPU)."""

    def __init__(self, model_dir: Path) -> None:
        from transformers import AutoModel, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(str(model_dir))
        self.model = (AutoModel.from_pretrained(
            str(model_dir), torch_dtype=torch.bfloat16)
            .cuda().eval())

    def _encode(self, texts: list[str], batch: int = 64,
                max_len: int = 512) -> np.ndarray:
        out = []
        for i in range(0, len(texts), batch):
            chunk = texts[i:i + batch]
            enc = self.tok(chunk, padding=True, truncation=True,
                           max_length=max_len, return_tensors="pt")
            enc = {k: v.cuda() for k, v in enc.items()}
            with torch.no_grad():
                hidden = self.model(**enc).last_hidden_state
            # last-token池化(最后一个非pad token)
            lens = enc["attention_mask"].sum(dim=1) - 1
            vecs = hidden[torch.arange(len(chunk)), lens]
            vecs = torch.nn.functional.normalize(vecs, dim=-1)
            out.append(vecs.float().cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 1024),
                                                        dtype=np.float32)

    def embed_queries(self, queries: list[str]) -> np.ndarray:
        texts = [Q_PREFIX + q[:512] + Q_SUFFIX for q in queries]
        return self._encode(texts, batch=32, max_len=560)

    def embed_docs(self, docs: list[str]) -> np.ndarray:
        return self._encode(docs)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not (MODEL_DIR / "config.json").exists():
        print(f"模型缺失: {MODEL_DIR}")
        sys.exit(1)
    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    pool = [c for c in ds["corpus"] if c["type"] == "table"]
    queries = [q for q in ds["queries"]
               if q["scene"] in ("table_deep_v3", "table_deep_v4")
               and q["split"] == "eval"]
    ids = [c["chunk_id"] for c in pool]
    idx = {cid: i for i, cid in enumerate(ids)}
    n = len(pool)
    golds = [{idx[t] for t in q["expected"] if t in idx} for q in queries]
    print(f"Qwen3骨干检验: {len(queries)}q × {n}表")

    enc = Qwen3Encoder(MODEL_DIR)

    # 单元编码(O1-unit数学)
    t0 = time.time()
    raw_units = [[u for u in ([c["title"]] + c["units"]) if u]
                 for c in pool]
    unit_texts = [u for ru in raw_units for u in ru]
    U = enc.embed_docs(unit_texts)
    print(f"单元编码: {U.shape} ({time.time()-t0:.0f}s)", flush=True)
    dfc: dict[str, int] = {}
    for ru in raw_units:
        for u in set(ru):
            dfc[u] = dfc.get(u, 0) + 1
    idf = np.asarray([np.log(1 + n / max(dfc.get(u, 1), 1))
                      for u in unit_texts], dtype=np.float32)
    seg = np.cumsum([0] + [len(ru) for ru in raw_units])

    # 文档编码(dense对照)
    dense_texts = [(c["title"] + " " + " ".join(c["units"]))[:512]
                   for c in pool]
    D = enc.embed_docs(dense_texts)
    Q = enc.embed_queries([q["query"] for q in queries])
    print(f"查询编码: {Q.shape} ({time.time()-t0:.0f}s)", flush=True)

    # 打分
    s_o1 = np.zeros((len(queries), n), dtype=np.float32)
    s_dn = Q @ D.T
    for qi in range(len(queries)):
        sims = (U @ Q[qi]) * idf
        for i in range(n):
            s_o1[qi, i] = sims[seg[i]:seg[i + 1]].max() \
                if seg[i] < seg[i + 1] else -1e9

    def metrics(scores: np.ndarray) -> dict:
        r1 = r5 = mrr = 0.0
        for qi in range(len(queries)):
            order = np.argsort(-scores[qi])[:10]
            rank = next((r for r, j in enumerate(order, 1)
                         if j in golds[qi]), None)
            if rank == 1:
                r1 += 1
            if rank is not None and rank <= 5:
                r5 += 1
            if rank is not None and rank <= 10:
                mrr += 1.0 / rank
        m = len(queries)
        return {"R@1": r1 / m, "R@5": r5 / m, "MRR@10": mrr / m}

    m_o1 = metrics(s_o1)
    m_dn = metrics(s_dn)
    # McNemar
    h1_o1 = [1 if np.argmax(s_o1[qi]) in golds[qi] else 0
             for qi in range(len(queries))]
    h1_dn = [1 if np.argmax(s_dn[qi]) in golds[qi] else 0
             for qi in range(len(queries))]
    b = sum(1 for a, x in zip(h1_dn, h1_o1) if x and not a)
    c = sum(1 for a, x in zip(h1_dn, h1_o1) if a and not x)
    z = (b - c) / ((b + c) ** 0.5) if b + c else 0.0
    p = 0.5 * (1 + math.erf(z / 2 ** 0.5)) if b + c else 1.0
    p_one = 1 - p if p > 0.5 else p

    print(f"\nQwen3骨干: O1-unit R@1={m_o1['R@1']:.4f} "
          f"R@5={m_o1['R@5']:.4f} MRR={m_o1['MRR@10']:.4f}")
    print(f"Qwen3骨干: dense   R@1={m_dn['R@1']:.4f} "
          f"R@5={m_dn['R@5']:.4f} MRR={m_dn['MRR@10']:.4f}")
    print(f"McNemar(O1 vs dense): b={b} c={c} p={p_one:.2e}")
    print("参照BGE骨干: O1 0.365 / B1-dense 0.078")

    verdict = ("单元级claim骨干无关成立" if m_o1["R@1"] > m_dn["R@1"]
               and p_one < 0.05 else "需复查")
    outp = RESULTS / "S10_qwen3_backbone.json"
    outp.write_text(json.dumps({
        "protocol": ("Qwen3-Embedding-0.6B骨干无关性检验: 同S6查询集"
                     "438q表池; O1-unit数学vs文档级dense; "
                     "query=官方chat模板指令"),
        "o1_unit": m_o1, "dense": m_dn,
        "mcnemar": {"b": b, "c": c, "p_one_sided": p_one},
        "reference_bge": {"O1-unit": 0.3653, "B1-dense": 0.0776},
        "verdict": verdict,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"判定: {verdict}")
    print(f"→ {outp}")

    from run_utils import open_run
    handle = open_run("eval_qwen3_backbone", {
        "backbone": "Qwen3-Embedding-0.6B", "scene": "combined 438q"})
    handle.save_result({"o1_unit": m_o1, "dense": m_dn,
                        "verdict": verdict})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
