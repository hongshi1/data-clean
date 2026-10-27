"""单元子注意力聚合(UAA): 冻结表示+学习聚合, 含CMSC冻结投影头.

三个冻结表示源 + 一个可学习注意力(算法故事):
  ① BGE(冻结)         → sim_bge: 语义相似度
  ② CMSC投影头(冻结)   → sim_cmsc: 跨模态实体对齐分数
     (models/cmsc_projection.pt双塔proj_a/proj_b, 3724跨模态对预训练;
      此前替换BGE负迁移0.861→0.834——本模块是其正确集成位置:
      作为特征进入注意力, 让学习决定其权重, 只能加信号不会换掉主通道)
  ③ 结构特征(确定性)   → 13维: 种类/坐标/度/行位置等
  ④ 学习: α_i = softmax(MLP([sim_bge, sim_cmsc, idf, 结构特征]))
     score = Σ α_i·sim_bge_i, 参数~500, BGE/CMSC全程冻结
     (吸取表示学习失败教训: MLP投影R@1≈0.03的根因是训练分布错位;
      聚合权重是任务结构性的, 不依赖查询措辞分布)

特征提取(每单元13维结构特征):
  kind_onehot(6)   单元种类: 标题/图节点/VLM元素/表行/预留×2
  log_len          单元文本长度(log1p)
  rx, ry           图节点归一化坐标(VSDX矢量源)
  deg_in, deg_out  图节点入/出边度(归一化)——方向信号进入打分
  row_pos          表行位置——早期行vs深行可区分
  n_cells          表行单元格数(归一化)

向量化实现: 每查询全部候选单元拼接为单批
(softmax按段scatter实现), 训练~秒级.

可解释性: attention_weights返回α分布——查询命中了图哪个节点/
表哪一行, 即查询↔子单元关联证据(方向A的粘合点).

硬规则遵从: 模块顶层零I/O, torch惰性import, open()显式utf-8.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parents[1]
ANCHORS_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
IMG_ANCHOR_MAP = BASE / "data/gjb_438c/data_assets/va_colpali_img_anchor_map.json"
CMSC_MODEL = BASE / "models/cmsc_projection.pt"

MAX_ELEMENTS = 12          # 与va_colpali一致(对齐测试锁定)
FEAT_DIM = 13              # 结构特征维数
KIND_DIM = 6
QCTX_DIM = 5               # 查询级上下文(广播到每单元): max/mean/std/entropy/log_n
INPUT_DIM = FEAT_DIM + 3 + QCTX_DIM  # + sim_bge + sim_cmsc + idf


def _kinds(title: bool, node: bool, elem: bool, row: bool) -> np.ndarray:
    k = np.zeros(KIND_DIM, dtype=np.float32)
    if title:
        k[0] = 1.0
    elif node:
        k[1] = 1.0
    elif elem:
        k[2] = 1.0
    elif row:
        k[3] = 1.0
    return k


# ── CMSC冻结投影头 ─────────────────────────────────────

class CmscProjector:
    """CMSC双塔投影(冻结): query走proj_a(prose塔), 单元走proj_b(表/图塔)."""

    def __init__(self) -> None:
        self.ready = False
        self.last_error = ""
        self._torch: Any = None
        self._a: Any = None
        self._b: Any = None

    def ensure(self) -> bool:
        if self.ready:
            return self._a is not None
        self.ready = True
        if not CMSC_MODEL.exists():
            self.last_error = f"model not found: {CMSC_MODEL}"
            return False
        try:
            import torch  # noqa: PLC0415  惰性
            import torch.nn as nn  # noqa: PLC0415
            self._torch = torch
            data = torch.load(str(CMSC_MODEL), weights_only=False, map_location="cpu")
            cfg = data.get("config", {})
            dim_in, dim_out = cfg.get("dim_in", 1024), cfg.get("dim_shared", 256)

            def _mk(state):
                net = nn.Sequential(
                    nn.Linear(dim_in, 256), nn.LayerNorm(256), nn.GELU(),
                    nn.Linear(256, dim_out))
                net.load_state_dict(state)
                net.eval()
                return net

            self._a = _mk(data["proj_a"])
            self._b = _mk(data["proj_b"])
            return True
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            self.last_error = f"cmsc load failed: {e}"
            return False

    def project_query(self, qvec: np.ndarray) -> np.ndarray | None:
        """查询向量→prose塔投影(256d, 归一). 失败返回None(特征置0)."""
        if not self.ensure():
            return None
        torch = self._torch
        with torch.no_grad():
            v = self._a(torch.as_tensor(qvec, dtype=torch.float32).unsqueeze(0))
            v = torch.nn.functional.normalize(v, dim=-1)
        return v.numpy()[0]

    def project_units(self, mat: np.ndarray) -> np.ndarray | None:
        """单元矩阵(n,1024)→表/图塔投影(n,256, 归一). 失败返回None."""
        if not self.ensure():
            return None
        torch = self._torch
        with torch.no_grad():
            v = self._b(torch.as_tensor(mat, dtype=torch.float32))
            v = torch.nn.functional.normalize(v, dim=-1)
        return v.numpy()


# ── 单元+结构特征提取 ──────────────────────────────────

def image_units_with_feats(chunks: list[dict]) -> dict[str, tuple[list[str], np.ndarray]]:
    """图模态单元+结构特征: chunk列表→{cid: (texts, feats)}.

    texts顺序必须与va_colpali.image_unit_extractor完全一致
    (标题→锚点节点→VLM元素), 由tests/test_unit_attention.py对齐测试锁定.
    feats: (n_units, FEAT_DIM), 行与texts一一对应.
    """
    from algorithms.va_colpali import _vlm_by_chunk  # noqa: PLC0415  复用VLM对齐逻辑
    images = [c for c in chunks if c.get("type") == "image"
              and c.get("chunk_id") and c.get("doc")]
    img_map = json.loads(IMG_ANCHOR_MAP.read_text(encoding="utf-8"))
    av2 = json.loads(ANCHORS_V2.read_text(encoding="utf-8"))
    doc_structs: dict[str, dict[str, dict]] = {}
    for dn, d in av2.items():
        doc_structs[dn[:2]] = {s.get("embed_index", ""): s
                               for s in d.get("structures", [])}
    vlm = _vlm_by_chunk(images)

    out: dict[str, tuple[list[str], np.ndarray]] = {}
    for c in images:
        cid = c["chunk_id"]
        cap, elements = vlm.get(cid, ("", []))
        texts: list[str] = []
        feats: list[np.ndarray] = []
        if cap:
            texts.append(cap)
            feats.append(np.concatenate([_kinds(True, False, False, False),
                                         [np.log1p(len(cap)), 0, 0, 0, 0, 0, 0]]))
        info = img_map.get(cid)
        s = doc_structs.get(cid[:2], {}).get(info.get("embed_index", "")) if info else None
        if s:
            deg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
            for e in s.get("edges", []):
                deg[e.get("src", "")][1] += 1  # 出度
                deg[e.get("dst", "")][0] += 1  # 入度
            for n in s.get("nodes", []):
                if not n.get("text"):
                    continue
                t = n["text"][:100]
                texts.append(t)
                di, do = deg.get(n["id"], [0, 0])
                feats.append(np.concatenate([_kinds(False, True, False, False),
                                             [np.log1p(len(t)),
                                              min(n.get("rx", 0.5), 1.0),
                                              min(n.get("ry", 0.5), 1.0),
                                              min(di / 5.0, 1.0),
                                              min(do / 5.0, 1.0), 0, 0]]))
        for e in elements[:MAX_ELEMENTS]:
            if not e:
                continue
            texts.append(e)
            feats.append(np.concatenate([_kinds(False, False, True, False),
                                         [np.log1p(len(e)), 0, 0, 0, 0, 0, 0]]))
        if texts:
            out[cid] = (texts, np.stack(feats).astype(np.float32))
    return out


def table_units_with_feats(chunks: list[dict]) -> dict[str, tuple[list[str], np.ndarray]]:
    """表模态单元+结构特征: {cid: (texts, feats)}.

    texts=unit_retrieval.table_unit_texts(标题→行), feats含行位置/单元格数.
    行序与texts一一对应(同一函数逻辑, 天然对齐).
    """
    from algorithms.unit_retrieval import MAX_ROWS, parse_table  # noqa: PLC0415
    out: dict[str, tuple[list[str], np.ndarray]] = {}
    for c in chunks:
        if c.get("type") != "table" or not c.get("chunk_id"):
            continue
        headers, rows = parse_table(c.get("text") or "")
        cap = str(c.get("table_caption")
                  or c.get("meta", {}).get("caption", ""))[:80]
        texts: list[str] = []
        feats: list[np.ndarray] = []
        if cap:
            texts.append(cap)
            feats.append(np.concatenate([_kinds(True, False, False, False),
                                         [np.log1p(len(cap)), 0, 0, 0, 0, 0, 0]]))
        kept = rows[:MAX_ROWS]
        for j, r in enumerate(kept):
            if headers and len(r) == len(headers):
                t = " ".join(f"{h}={v}" for h, v in zip(headers, r))[:150]
            else:
                t = " ".join(r)[:150]
            texts.append(t)
            feats.append(np.concatenate([
                _kinds(False, False, False, True),
                [np.log1p(len(t)), 0, 0, 0, 0,
                 j / max(len(kept) - 1, 1),
                 min(len(r) / 10.0, 1.0)]]))
        if texts:
            out[c["chunk_id"]] = (texts, np.stack(feats).astype(np.float32))
    return out


# ── 子注意力聚合器(向量化) ────────────────────────────

class SubAttentionAggregator:
    """子单元注意力聚合器: 冻结表示+学习α聚合.

    输入(每单元): [sim_bge, sim_cmsc, idf, *结构特征(13)] → MLP(16→32→1)
    → logit → chunk内softmax(段scatter) → score = Σ α·sim_bge.
    固定聚合是该族的特例: 均匀logit→均值, 大sim权重→MaxSim.

    训练: 每查询全部候选单元拼接单批前向(向量化, ~秒级/折).
    """

    def __init__(self, use_cmsc: bool = True) -> None:
        self.use_cmsc = use_cmsc
        self.net: Any = None
        self.kappa: Any = None
        self._torch: Any = None
        self.last_error = ""
        self.stats: dict[str, Any] = {"n_fit_calls": 0, "epochs": 0,
                                      "final_loss": None}

    def _init_net(self) -> None:
        if self.net is not None:
            return
        import torch  # noqa: PLC0415  惰性
        import torch.nn as nn  # noqa: PLC0415
        self._torch = torch
        torch.manual_seed(42)
        self.net = nn.Sequential(nn.Linear(INPUT_DIM, 32), nn.Tanh(),
                                 nn.Linear(32, 1))
        # warm-start残差: logit += κ·(sim·idf), κ=8时softmax≈MaxSim(sim·idf)
        # ——初始状态即固定聚合器FIXED, 训练只学结构修正(起点不回退)
        self.kappa = nn.Parameter(torch.tensor(8.0))

    @staticmethod
    def _build_batch(cands: list[list], torch, with_grad: bool):
        """候选批→拼接张量. cand=[cid, sims, cmsc_sims, idfs, feats, is_pos].

        返回(X, seg, value): value=sim·idf(被聚合值, 与FIXED口径一致).
        X额外含查询级上下文(广播): [max_sim, mean_sim, std_sim,
        sim熵, log候选数]——注意力据此自适应"尖锐查询(深行型)保max
        /宽泛查询(caption型)软化", 弥补单一聚合模式无法双优的结构缺陷.
        """
        xs, seg_id, vals = [], [], []
        all_sims = np.concatenate([np.asarray(c[1], dtype=np.float32)
                                   for c in cands]) if cands else np.zeros(1)
        q_max = float(all_sims.max())
        q_mean = float(all_sims.mean())
        q_std = float(all_sims.std())
        p = np.clip(all_sims - all_sims.min(), 1e-6, None)
        p = p / p.sum()
        q_ent = float(-(p * np.log(p)).sum())
        q_n = float(np.log(len(cands))) if cands else 0.0
        qctx = [q_max, q_mean, q_std, q_ent, q_n]
        for ci, c in enumerate(cands):
            n = len(c[1])
            stack = [np.asarray(c[1])[:, None], np.asarray(c[3])[:, None]]
            if c[2] is not None:
                stack.append(np.asarray(c[2])[:, None])
            else:
                stack.append(np.zeros((n, 1), dtype=np.float32))
            stack.append(c[4])
            stack.append(np.tile(np.asarray(qctx, dtype=np.float32), (n, 1)))
            xs.append(np.concatenate(stack, axis=1))
            seg_id.extend([ci] * n)
            vals.append(np.asarray(c[1], dtype=np.float32)
                        * np.asarray(c[3], dtype=np.float32))
        X = torch.as_tensor(np.concatenate(xs), dtype=torch.float32)
        seg = torch.as_tensor(seg_id, dtype=torch.long)
        value = torch.as_tensor(np.concatenate(vals), dtype=torch.float32)
        if not with_grad:
            X = X.detach()
        return X, seg, value

    def _forward_scores(self, X, seg, value, n_cands):
        """段softmax注意力→每候选分数. 返回(scores, alpha, mlp_logits).

        logit = MLP(X) + κ·value(sim·idf warm-start残差);
        κ=8时softmax≈MaxSim(sim·idf)——初始状态精确等于FIXED聚合器,
        训练只学MLP修正(起点不回退). mlp_logits供L2正则.
        """
        torch = self._torch
        mlp_logits = self.net(X).flatten()
        logits = mlp_logits + self.kappa * value
        m = torch.full((n_cands,), float("-inf"))
        m.scatter_reduce_(0, seg, logits, reduce="amax")
        e = torch.exp(logits - m[seg])
        denom = torch.zeros(n_cands).index_add_(0, seg, e)
        alpha = e / denom[seg]
        scores = torch.zeros(n_cands).index_add_(0, seg, alpha * value)
        return scores, alpha, mlp_logits

    def chunk_scores(self, cands: list[list]) -> np.ndarray:
        """推理: 候选批→每候选分数(向量化单批).

        cand=[cid, sims, cmsc_sims, idfs, feats, is_pos任意].
        """
        self._init_net()
        torch = self._torch
        with torch.no_grad():
            X, seg, value = self._build_batch(cands, torch, with_grad=False)
            scores, _, _ = self._forward_scores(X, seg, value, len(cands))
        return scores.numpy()

    def attention_weights(self, cands: list[list]) -> list[np.ndarray]:
        """可解释性: 每候选的α分布(查询↔子单元关联证据)."""
        self._init_net()
        torch = self._torch
        with torch.no_grad():
            X, seg, value = self._build_batch(cands, torch, with_grad=False)
            _, alpha, _ = self._forward_scores(X, seg, value, len(cands))
        a = alpha.numpy()
        return [a[seg.numpy() == ci] for ci in range(len(cands))]

    def fit(self, batches: list[dict], epochs: int = 20, lr: float = 3e-2,
            reg: float = 0.0, verbose: bool = False) -> float:
        """在(query, 候选池)批上训练, 候选间交叉熵. 返回最终loss.

        batches: [{"cands": [cid, sims, cmsc_sims, idfs, feats, is_pos]}, ...]
        """
        self._init_net()
        torch = self._torch
        optim = torch.optim.AdamW(
            [*self.net.parameters(), self.kappa], lr=lr)
        losses: list[float] = []
        for ep in range(epochs):
            ep_loss = 0.0
            for b in batches:
                cands = b["cands"]
                pos_idx = [i for i, c in enumerate(cands) if c[5]]
                if not pos_idx:
                    continue
                X, seg, value = self._build_batch(cands, torch, with_grad=True)
                scores, _, mlp_logits = self._forward_scores(
                    X, seg, value, len(cands))
                logp = torch.log_softmax(scores, dim=-1)
                loss = -sum(logp[p] for p in pos_idx) / len(pos_idx)
                if reg > 0:
                    # 信任初始化: MLP偏离κ残差(FIXED)需付出L2代价
                    loss = loss + reg * (mlp_logits ** 2).mean()
                optim.zero_grad()
                loss.backward()
                optim.step()
                ep_loss += float(loss.detach())
            losses.append(ep_loss / max(len(batches), 1))
            if verbose and (ep + 1) % 5 == 0:
                print(f"  epoch {ep+1}: loss={losses[-1]:.4f}")
        self.stats["n_fit_calls"] += 1
        self.stats["epochs"] += epochs
        self.stats["final_loss"] = losses[-1] if losses else None
        return losses[-1] if losses else 0.0

    def save(self, path: Path) -> None:
        self._init_net()
        torch = self._torch
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"net": self.net.state_dict(),
                    "kappa": float(self.kappa.detach()),
                    "input_dim": INPUT_DIM,
                    "stats": self.stats}, str(path))

    def load(self, path: Path) -> bool:
        if not path.exists():
            self.last_error = f"model not found: {path}"
            return False
        try:
            self._init_net()
            data = self._torch.load(str(path), weights_only=False)
            self.net.load_state_dict(data["net"])
            with self._torch.no_grad():
                self.kappa.fill_(data.get("kappa", 8.0))
            self.stats = data.get("stats", self.stats)
            return True
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            self.last_error = f"model load failed: {e}"
            return False
