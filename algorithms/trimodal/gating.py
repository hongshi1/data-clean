"""查询自适应门控融合: α(q)动态融合teacher/student分数 (D3).

设计:
  α(q) = σ(MLP([q_feat(3); bridge_conf(1); proj_conf(1)]))
    q_feat     = 查询特征(实体性/图号/ID指示 — query_features)
    bridge_conf = teacher(Text-Bridge)对该query的top-1分数(z-scored)
    proj_conf   = student(投影头)对该query的top-1分数(z-scored)

  final_score = α(q)·zscore(teacher_scores) + (1-α(q))·zscore(student_scores)

训练: 评测集前2/3(实体组边界)的"哪个检索器命中期望"作标签(1维二分类).
"""
from __future__ import annotations

import numpy as np

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(x, -20, 20)))


class QueryGatingFusion:
    """查询自适应门控融合器.

    用法:
        gate = QueryGatingFusion()
        gate.fit(train_qfeat, train_bridge_hit, train_proj_hit)
        alpha = gate.predict(qfeat, bridge_conf, proj_conf)  # (N,)∈(0,1)
        fused = alpha[:, None] * teacher + (1 - alpha[:, None]) * student
    """

    def __init__(self, seed: int = 42, lr: float = 0.01,
                 epochs: int = 200) -> None:
        self.seed = seed
        self.lr = lr
        self.epochs = epochs
        self._w: np.ndarray | None = None
        self._b: np.ndarray | None = None
        self.history: list[float] = []

    def _features(self, qfeat: np.ndarray, bridge_conf: np.ndarray,
                  proj_conf: np.ndarray) -> np.ndarray:
        return np.concatenate([
            np.asarray(qfeat, dtype=np.float32).reshape(-1, 3),
            np.asarray(bridge_conf, dtype=np.float32).reshape(-1, 1),
            np.asarray(proj_conf, dtype=np.float32).reshape(-1, 1),
        ], axis=1)

    def fit(self, qfeat: np.ndarray, bridge_hit: np.ndarray,
            proj_hit: np.ndarray) -> list[float]:
        """训练: bridge_hit/proj_hit∈{0,1}(是否命中期望), 标签=bridge胜."""
        X = self._features(qfeat, bridge_hit.astype(float),
                           proj_hit.astype(float))
        # 标签: bridge命中且proj未命中→1; proj命中且bridge未命中→0;
        #       两者都命中或都未命中→0.5(不确定, 权重降半)
        y = np.where(bridge_hit > proj_hit, 1.0,
                     np.where(proj_hit > bridge_hit, 0.0, 0.5))
        w = np.where((bridge_hit != proj_hit), 1.0, 0.3)  # 不确定样本降权
        rng = np.random.default_rng(self.seed)
        d = X.shape[1]
        self._w = rng.normal(0, 0.1, d).astype(np.float32)
        self._b = np.zeros(1, dtype=np.float32)
        self.history = []
        for _ in range(self.epochs):
            logits = X @ self._w + self._b
            p = _sigmoid(logits)
            grad = (p - y) * w
            gw = (X * grad[:, None]).mean(0)
            gb = grad.mean()
            self._w -= self.lr * gw
            self._b -= self.lr * gb
            ll = -(y * np.log(p + 1e-8)
                   + (1 - y) * np.log(1 - p + 1e-8)).mean()
            self.history.append(float(ll))
        return self.history

    def predict(self, qfeat: np.ndarray, bridge_conf: np.ndarray,
                proj_conf: np.ndarray) -> np.ndarray:
        """返回α∈(0,1)^N: 值越大越信任teacher(Text-Bridge)."""
        if self._w is None:
            return np.full(len(np.atleast_1d(bridge_conf)), 0.5)
        X = self._features(qfeat, bridge_conf, proj_conf)
        return _sigmoid(X @ self._w + self._b)
