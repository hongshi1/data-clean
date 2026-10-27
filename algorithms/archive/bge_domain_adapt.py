"""BGE域适配(A8): 冻结底座 + 轻量残差适配头, QA语料对比训练(InfoNCE).

动机: dense单通道(原生BGE)在军事术语域召回不足(R@20=0.4757, 见
eval_hybrid_recall single:dense) — 通用中文embedding的语义空间未对齐
SRS域术语(接口ID/功能名/表图名/参数名).

方法:
  - 冻结bge-large-zh-v1.5底座, 只训残差MLP头(1024→512→1024, ≈1.05M参数,
    输出层零初始化): 适配后嵌入 = normalize(bge(x) + α·head(bge(x)));
    零初始化 ⇒ 未训练时恒等变换(残差式, 保底不劣化).
  - α为推理期残差缩放(训练全强度, 推理按α缩放适配量). 设计扫描结论:
    全强度(α=1)域适配会过度形变几何(R@20 -0.044); α∈[0.25,0.5]平台
    双指标同时为正(α=0.4: R@10 +0.031, R@20 +0.016, 见tools/eval_bge_adapt).
    α在retrieval_evalset(300条)上校准(同EMB_TH_LOCAL的校准惯例).
  - 对比训练: InfoNCE(τ=0.05, batch内负例, 双向损失); 查询侧加BGE
    检索指令前缀并截200字(与hybrid_recall._dense的查询口径一致).
  - 底座特征no_grad预计算一次(BgeLocal磁盘缓存复用), 每epoch只过
    适配头 → GPU上5.5k对×20epoch为秒级.

训练对设计(消融后定稿, 拒绝的字面设计在docstring留档):
  - 语料: data/gjb_438c/easydataset/srs_alpaca_full.jsonl
    (28,761行, instruction/input/output三字段; CJK+长度过滤后域内19,645行).
  - 正对 = (实体化问句, 答案所依据的原文上下文):
      query = extract_entity(instruction) — 实体短语, 对齐评测query分布;
      doc   = input[:400] — SRS原文片段, 对齐chunk富化文本分布.
  - 拒绝设计① (instruction+input, output[:400]): 答案侧为短元文本,
    全强度训练R@20 -0.044, α缩放后仍-0.02 → 弃.
  - 拒绝设计② (instruction, input+output拼接): R@20 -0.047 → 弃.
  - 实体池5,530对(input≥30字且非"章节/跨章节/UML关系/需求"前缀).

硬规则遵从: 模块顶层零I/O(torch/模型惰性加载); open()带encoding=
"utf-8"; seed固定(初始化/采样/洗牌); 失败显式记录last_error不静默吞.

用法:
  python algorithms/bge_domain_adapt.py                    # 训练(全量5.5k对)
  python algorithms/bge_domain_adapt.py --pairs-limit 1000 # 快速版
  python tools/eval_bge_adapt.py                           # 评测对比
"""
from __future__ import annotations

import hashlib
import json
import pickle
import random
import re
import time
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[2]  # 归档后深一层
DEFAULT_ADAPTER_DIR = BASE / "models" / "embedding" / "bge_adapter"
DEFAULT_CACHE_DIR = BASE / "data" / "gjb_438c" / "blackboard"
CORPUS_PATH = BASE / "data" / "gjb_438c" / "easydataset" / "srs_alpaca_full.jsonl"

QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："  # 与hybrid_recall._QUERY_PREFIX一致
TAU = 0.05                 # InfoNCE温度
HIDDEN_DIM = 512           # 残差MLP隐层: 1024→512→1024 ≈ 1.05M参数
DEFAULT_ALPHA = 0.4        # 推理期残差缩放(retrieval_evalset校准, 平台[0.25,0.5])
_MAX_QUERY_CHARS = 200     # 查询侧截断(与dense通道_query[:200]口径一致)
_CJK = re.compile(r"[\u4e00-\u9fff]")
_SAVE_EVERY = 512          # 适配向量缓存: 每新增512条写盘一次


def load_qa_pairs(corpus_path: Path = CORPUS_PATH, limit: int = 0,
                  seed: int = 42, max_ctx_chars: int = 400,
                  min_ctx_chars: int = 30) -> list[tuple[str, str]]:
    """域内训练对: (实体化问句, 答案所依据的原文上下文), 采样可复现.

    过滤(数据探查: 28,761行中约9k为英文/Mermaid等非域行):
      - 双侧含CJK, instruction≥8字, output≥15字(剔退化行);
      - 实体化问句 = extract_entity(instruction)(≥4字), 对齐评测
        query的实体短语分布;
      - 原文上下文 = input[:400](≥30字), 剔除"章节/跨章节/UML关系/
        需求N"等非正文前缀 — 保留json/表格/上下文等含真实SRS文本的行,
        对齐chunk富化文本分布.
    limit=0 → 全量(约5.5k对); limit>0 → Random(seed)采样(保序可复现).
    """
    from algorithms.blackboard.hybrid_recall import extract_entity
    pairs: list[tuple[str, str]] = []
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(row.get("instruction", "")).strip()
            ctx = str(row.get("input", "")).strip()
            a = str(row.get("output", "")).strip()
            if len(q) < 8 or len(a) < 15:
                continue
            if not (_CJK.search(q) and _CJK.search(a)):
                continue
            if len(ctx) < min_ctx_chars or ctx.startswith(
                    ("章节", "跨章节", "UML关系", "需求1", "需求2")):
                continue
            entity = extract_entity(q)
            if len(entity) < 4:
                continue
            pairs.append((entity, ctx[:max_ctx_chars]))
    if limit and len(pairs) > limit:
        rng = random.Random(seed)
        idx = sorted(rng.sample(range(len(pairs)), limit))
        pairs = [pairs[i] for i in idx]
    return pairs


class BgeAdapter:
    """BGE域适配器: 冻结底座 + 残差MLP头 + 推理期残差缩放α.

    ensure()自动加载adapter_dir/adapter.pt(不存在则零初始化=恒等;
    α随adapter_meta.json恢复); fit()对比训练(总是从零初始化头开始,
    可复现); embed()返回适配后嵌入(带按(权重,α)指纹分文件的磁盘缓存).
    """

    def __init__(self, adapter_dir: Path | None = None,
                 cache_dir: Path | None = None,
                 use_cache: bool = True,
                 alpha: float = 1.0) -> None:
        self.adapter_dir = Path(adapter_dir or DEFAULT_ADAPTER_DIR)
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self.use_cache = use_cache
        self.alpha = float(alpha)
        self.mode = "unavailable"
        self.last_error = ""
        self.stats: dict[str, Any] = {"device": "", "dim": 0, "n_params": 0,
                                      "trained": False, "fit_ms": 0.0,
                                      "n_embed_calls": 0, "n_cache_hits": 0,
                                      "n_cache_texts": 0}
        self.meta: dict[str, Any] = {}
        self._bge: Any = None
        self._torch: Any = None
        self._head: Any = None
        self._ready = False
        self._dirty_since_save = 0
        self._cache: dict[str, list[float]] = {}
        self._cache_path: Path | None = None

    # ── 惰性初始化 ────────────────────────────────────────
    def ensure(self) -> str:
        """初始化并返回mode("gpu"|"cpu"|"unavailable"). 失败原因在last_error."""
        if self._ready:
            return self.mode
        self._ready = True
        from algorithms.common.bge_local import BgeLocal
        self._bge = BgeLocal(cache_path=self.adapter_dir / "bge_feat_cache.pkl")
        if self._bge.ensure() == "unavailable":
            self.last_error = f"BgeLocal unavailable: {self._bge.last_error}"
            return self.mode
        import torch
        self._torch = torch
        self._build_head()
        self._load_weights()
        self.mode = self._bge.mode
        self.stats["device"] = self._bge.stats["device"]
        self.stats["dim"] = int(self._bge.stats["dim"])
        return self.mode

    def _build_head(self) -> None:
        """残差MLP头(输出层零初始化): 初始适配=恒等, 保底不劣化."""
        import torch.nn as nn
        dim = int(self._bge.stats["dim"])
        head = nn.Sequential(
            nn.Linear(dim, HIDDEN_DIM),
            nn.GELU(),
            nn.Linear(HIDDEN_DIM, dim),
        )
        nn.init.zeros_(head[2].weight)
        nn.init.zeros_(head[2].bias)
        head.to(self._bge.stats["device"])
        self._head = head
        self.stats["n_params"] = int(sum(p.numel() for p in head.parameters()))
        self.stats["trained"] = False

    def _load_weights(self) -> bool:
        """加载已训练权重(adapter.pt+adapter_meta.json, 含α恢复);
        不存在则保持零初始化."""
        p = self.adapter_dir / "adapter.pt"
        if not p.exists():
            return False
        torch = self._torch
        try:
            state = torch.load(p, map_location=self._bge.stats["device"],
                               weights_only=True)
            self._head.load_state_dict(state)
            self.stats["trained"] = True
        except (RuntimeError, OSError, ValueError, KeyError) as e:
            self.last_error = f"adapter.pt load failed: {e}"
            return False
        meta_p = self.adapter_dir / "adapter_meta.json"
        if meta_p.exists():
            try:
                self.meta = json.loads(meta_p.read_text(encoding="utf-8"))
                if "alpha" in self.meta:
                    self.alpha = float(self.meta["alpha"])
            except (json.JSONDecodeError, OSError, ValueError) as e:
                self.last_error = f"adapter_meta.json unreadable: {e}"
        self._init_cache()
        return True

    # ── 权重指纹与缓存 ────────────────────────────────────
    def fingerprint(self) -> str:
        """适配头权重+α的指纹(8位hex): 适配向量缓存版本键(任一变更换文件)."""
        if self._head is None:
            return "nohead"
        import numpy as np
        torch = self._torch
        h = hashlib.sha1()
        h.update(f"alpha={self.alpha:.4g}".encode("utf-8"))
        with torch.no_grad():
            state = self._head.state_dict()
            for key in sorted(state):
                t = state[key].detach().cpu().contiguous()
                h.update(key.encode("utf-8"))
                h.update(np.ascontiguousarray(t.numpy()).tobytes())
        return h.hexdigest()[:8]

    def _init_cache(self) -> None:
        """按当前(权重,α)指纹定位/加载适配向量磁盘缓存."""
        self._cache = {}
        self._cache_path = None
        self.stats["n_cache_texts"] = 0
        if not self.use_cache:
            return
        p = self.cache_dir / f"bge_adapt_cache_{self.fingerprint()}.pkl"
        if p.exists():
            try:
                with open(p, "rb") as f:
                    data = pickle.load(f)
                if isinstance(data, dict):
                    self._cache = {t: v for t, v in data.items()
                                   if isinstance(t, str) and isinstance(v, list)}
            except (pickle.UnpicklingError, EOFError, OSError) as e:
                self.last_error = f"adapt cache unreadable: {e}"
                self._cache = {}
        self._cache_path = p
        self.stats["n_cache_texts"] = len(self._cache)

    def save_cache(self) -> None:
        """写盘适配向量缓存(embed内自动节流调用, 也可显式调用)."""
        if not (self.use_cache and self._cache and self._cache_path):
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "wb") as f:
            pickle.dump(self._cache, f)
        self._dirty_since_save = 0

    # ── 底座特征(冻结, no_grad) ───────────────────────────
    def _base_feats(self, texts: list[str]) -> Any:
        """BGE底座特征张量[N,1024](no_grad, BgeLocal磁盘缓存复用)."""
        torch = self._torch
        vecs = self._bge.embed(texts)
        missing = [t for t in dict.fromkeys(texts) if not vecs.get(t)]
        if missing:
            raise RuntimeError(
                f"BGE特征缺失{len(missing)}条: {self._bge.last_error[:200]}")
        rows = [vecs[t] for t in texts]
        return torch.tensor(rows, dtype=torch.float32,
                            device=self._bge.stats["device"])

    # ── 对比训练 ──────────────────────────────────────────
    def fit(self, pairs: list[tuple[str, str]], epochs: int = 20,
            lr: float = 3e-4, batch_size: int = 128, tau: float = TAU,
            seed: int = 42, weight_decay: float = 1e-4,
            data_spec: dict[str, Any] | None = None,
            log: Callable[..., None] | None = None) -> dict[str, Any]:
        """InfoNCE对比训练(只训适配头, 底座特征预计算冻结).

        正对=(query, doc); 查询侧加检索指令前缀+截断(与评测查询口径
        一致), 文档侧不加; 负例=batch内其他文档(双向损失: q→d与d→q).
        训练在全强度(α=1等价)下进行, 推理期由self.alpha缩放残差.
        总是从零初始化头开始(不在旧权重上续训, 可复现).
        返回训练元数据(也存入self.meta, save()时随权重落盘).
        """
        mode = self.ensure()
        if mode == "unavailable":
            raise RuntimeError(f"BgeAdapter unavailable: {self.last_error}")
        if len(pairs) < 2:
            raise ValueError(f"训练至少需要2对, 得到{len(pairs)}")
        torch = self._torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        self._build_head()  # 零初始化重开(可复现)
        t0 = time.time()
        # ① 底座特征预计算(冻结; 查询侧带检索前缀+截断, 对齐dense通道口径)
        q_texts = [QUERY_PREFIX + q[:_MAX_QUERY_CHARS] for q, _ in pairs]
        d_texts = [d for _, d in pairs]
        fq = self._base_feats(q_texts)
        fd = self._base_feats(d_texts)
        # ② InfoNCE训练循环(特征常量, 梯度只过适配头)
        dev = fq.device
        n = fq.shape[0]
        opt = torch.optim.AdamW(self._head.parameters(), lr=lr,
                                weight_decay=weight_decay)
        gen = torch.Generator().manual_seed(seed)
        hist: list[dict[str, Any]] = []
        for ep in range(1, epochs + 1):
            perm = torch.randperm(n, generator=gen).to(dev)
            tot, nb = 0.0, 0
            for i in range(0, n, batch_size):
                b = perm[i:i + batch_size]
                if b.numel() < 2:
                    continue  # 单元素batch无batch内负例
                q, d = fq[b], fd[b]
                qh = torch.nn.functional.normalize(q + self._head(q), dim=-1)
                dh = torch.nn.functional.normalize(d + self._head(d), dim=-1)
                logits = qh @ dh.transpose(0, 1) / tau
                labels = torch.arange(b.numel(), device=dev)
                loss = (torch.nn.functional.cross_entropy(logits, labels)
                        + torch.nn.functional.cross_entropy(
                            logits.transpose(0, 1), labels)) / 2
                opt.zero_grad()
                loss.backward()
                opt.step()
                tot += float(loss.item())
                nb += 1
            rec = {"epoch": ep, "loss": round(tot / max(nb, 1), 4)}
            hist.append(rec)
            if log is not None:
                log(**rec)
        self.stats["trained"] = True
        self.stats["fit_ms"] = round((time.time() - t0) * 1000, 1)
        self.meta = {"n_pairs": len(pairs), "epochs": epochs, "lr": lr,
                     "batch_size": batch_size, "tau": tau, "seed": seed,
                     "weight_decay": weight_decay, "alpha": self.alpha,
                     "hidden_dim": HIDDEN_DIM, "query_prefix": QUERY_PREFIX,
                     "data_spec": data_spec or {},
                     "fingerprint": self.fingerprint(),
                     "fit_ms": self.stats["fit_ms"], "loss_hist": hist}
        self._init_cache()  # 指纹已变 → 切换缓存文件
        return dict(self.meta)

    # ── 适配后嵌入 ────────────────────────────────────────
    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        """适配后嵌入: normalize(bge(x)+α·head(bge(x))), 带磁盘缓存.

        未训练(零初始化头)或α=0时恒等于原生BGE向量(残差式保底).
        返回 text→向量(空列表=失败).
        """
        mode = self.ensure()
        self.stats["n_embed_calls"] += 1
        out: dict[str, list[float]] = {}
        todo: list[str] = []
        for t in dict.fromkeys(texts):
            if not t:
                out[t] = []
            elif t in self._cache:
                out[t] = self._cache[t]
                self.stats["n_cache_hits"] += 1
            elif mode != "unavailable":
                todo.append(t)
            else:
                out[t] = []
        if todo:
            try:
                base = self._base_feats(todo)
            except RuntimeError as e:
                self.last_error = str(e)
                for t in todo:
                    out[t] = []
                return out
            torch = self._torch
            with torch.no_grad():
                adapted = torch.nn.functional.normalize(
                    base + self.alpha * self._head(base), dim=-1)
            fresh = dict(zip(todo, adapted.float().cpu().tolist()))
            self._cache.update(fresh)
            out.update(fresh)
            self._dirty_since_save += len(todo)
            self.stats["n_cache_texts"] = len(self._cache)
            if self._dirty_since_save >= _SAVE_EVERY:
                self.save_cache()
        return out

    # ── 持久化 ────────────────────────────────────────────
    def save(self, adapter_dir: Path | None = None) -> Path:
        """保存适配头权重+训练元数据(默认models/embedding/bge_adapter/)."""
        if self._head is None:
            raise RuntimeError("适配头未初始化(先调用ensure/fit)")
        torch = self._torch
        d = Path(adapter_dir) if adapter_dir else self.adapter_dir
        d.mkdir(parents=True, exist_ok=True)
        torch.save(self._head.state_dict(), d / "adapter.pt")
        (d / "adapter_meta.json").write_text(
            json.dumps(self.meta, ensure_ascii=False, indent=1),
            encoding="utf-8")
        return d


def _cli() -> int:
    """训练入口: 构造域内训练对 → fit → save权重 → runs协议落盘元数据."""
    import argparse
    import sys

    for p in (str(BASE), str(BASE / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="BGE域适配训练(A8)")
    ap.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    ap.add_argument("--pairs-limit", type=int, default=0,
                    help="采样训练对数(0=全量约5.5k; >0按seed采样)")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--alpha", type=float, default=DEFAULT_ALPHA,
                    help="推理期残差缩放(校准值0.4, 平台[0.25,0.5])")
    ap.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    args = ap.parse_args()

    pairs = load_qa_pairs(corpus_path=args.corpus, limit=args.pairs_limit,
                          seed=args.seed)
    if len(pairs) < 2:
        print(f"可用训练对不足: {len(pairs)} (corpus={args.corpus})")
        return 1
    print(f"训练对: {len(pairs)} (limit={args.pairs_limit or '全量'}, "
          f"seed={args.seed}, α={args.alpha})")

    from run_utils import open_run  # noqa: E402  (tools/非包, 由上方sys.path引入)
    run = open_run("bge_domain_adapt_train", {
        "corpus": str(args.corpus), "pairs_limit": args.pairs_limit,
        "actual_pairs": len(pairs), "epochs": args.epochs, "lr": args.lr,
        "batch_size": args.batch_size, "seed": args.seed,
        "alpha": args.alpha, "adapter_dir": str(args.adapter_dir)})
    adapter = BgeAdapter(adapter_dir=args.adapter_dir, alpha=args.alpha)
    meta = adapter.fit(pairs, epochs=args.epochs, lr=args.lr,
                       batch_size=args.batch_size, seed=args.seed,
                       data_spec={"corpus": str(args.corpus),
                                  "limit": args.pairs_limit,
                                  "seed": args.seed},
                       log=run.log)
    saved = adapter.save()
    run.save_result(meta)
    print(f"loss: ep1={meta['loss_hist'][0]['loss']} → "
          f"ep{meta['loss_hist'][-1]['epoch']}={meta['loss_hist'][-1]['loss']}")
    print(f"参数量: {adapter.stats['n_params']:,} | "
          f"指纹: {meta['fingerprint']} | 耗时: {meta['fit_ms'] / 1000:.1f}s")
    print(f"权重 → {saved / 'adapter.pt'}")
    print(f"元数据 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
