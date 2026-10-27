"""LoRA微调bge-large-zh为域内检索模型(对标BGE微调协议的对比学习).

协议(FlagEmbedding式大batch对比学习, 4060 8GB显存适配):
  - LoRA: r=16/alpha=32/dropout=0.05, 目标=注意力q/k/v/o投影
    (24层×4模块, 3.15M可训参数, 326M底座冻结)
  - 损失: InfoNCE(τ默认0.03, 0.02-0.05可搜索): 候选池=有效batch内
    全部正例(in-batch负例)+每query的n_hard_neg个hard负例, big softmax
  - 通道分块(channel-blocked): passage侧嵌入no_grad每epoch编码一次
    全池缓存, query侧带梯度 —— bge-large在8GB上LoRA微调的显存关键;
    一步内passage塔冻结 ⇒ 各query的损失行独立, 梯度累积下的有效batch
    =全batch(in-batch负例不因micro-batch切分而缩水,
    tests/test_bge_lora.py::test_grad_accum_equivalence数值锁定)
  - fp16 autocast + gradient checkpointing(use_reentrant=False);
    GPU OOM自动减半micro-batch/编码chunk并记录(runs协议log)
  - 对称用法: query/passage过同一编码器, query侧无BGE指令前缀
    (与候选侧dense索引口径对称, 区别于官方非对称用法)

triples.json灵活键加载(并行管线产出): 每条 {query, positive,
hard_negatives} — query: query/q/question/anchor; positive:
positive/pos/answer/doc/passage; 负例: hard_negatives/negatives/negs
(列表或单串).

硬规则遵从: 模块顶层零I/O(torch/peft/transformers惰性import);
seed固定(初始化/划分/洗牌); 训练历史runs协议(tools/run_utils.py);
open()带encoding="utf-8"; 失败显式记录last_error不静默吞.

用法:
  python algorithms/bge_lora_retriever.py --data data/gjb_438c/data_assets/retrieval_train/triples.json
  python algorithms/bge_lora_retriever.py --demo 10        # 合成数据冒烟
  python tools/eval_lora_retriever.py                      # 训练后评测
"""
from __future__ import annotations

import atexit
import hashlib
import json
import pickle
import random
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[2]  # 归档后深一层
DEFAULT_MODEL_DIR = BASE / "models" / "embedding" / "bge-large-zh-v1.5"
DEFAULT_ADAPTER_DIR = BASE / "models" / "embedding" / "bge_lora"
DEFAULT_TRIPLES_PATH = (BASE / "data" / "gjb_438c" / "data_assets"
                        / "retrieval_train" / "triples.json")

LORA_TARGET_MODULES = ("query", "key", "value", "attention.output.dense")
_MAX_LEN = 256          # 与bge_local的dense索引口径一致(CLS池化+L2归一)
_SAVE_EVERY = 512       # 推理向量缓存: 每新增512条写盘一次
_MIN_CHUNK = 2          # OOM自动减半的下限(micro-batch与编码chunk共用)

_Q_KEYS = ("query", "q", "question", "anchor", "src", "query_text")
_P_KEYS = ("positive", "pos", "answer", "doc", "passage", "target",
           "ctx", "context")
_N_KEYS = ("hard_negatives", "hard_negs", "negatives", "negs",
           "hard_negative", "negative", "neg")

_RUN_UTILS_CACHE: dict[str, Any] = {}


# ── 数据规整 ─────────────────────────────────────────────

def normalize_triples(
        raw: list[dict[str, Any]],
) -> tuple[list[tuple[str, str, list[str]]], dict[str, int]]:
    """triples灵活键规整: →[(query, positive, [hard_negs...]), ...] + 统计.

    兼容并行管线的键名变体; 负例接受列表或单串; 缺query或positive跳过.
    """
    out: list[tuple[str, str, list[str]]] = []
    n_skip = 0
    for row in raw:
        if not isinstance(row, dict):
            n_skip += 1
            continue
        q = next((str(row[k]).strip() for k in _Q_KEYS if row.get(k)), "")
        p = next((str(row[k]).strip() for k in _P_KEYS if row.get(k)), "")
        neg_raw = next((row[k] for k in _N_KEYS if row.get(k)), [])
        negs = [str(x).strip()
                for x in (neg_raw if isinstance(neg_raw, (list, tuple))
                          else [neg_raw]) if str(x).strip()]
        if not q or not p:
            n_skip += 1
            continue
        out.append((q, p, negs))
    return out, {"n_raw": len(raw), "n_ok": len(out), "n_skipped": n_skip}


def resolve_triples(
        raw: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """chunk_id型triples→文本triples; 文本型原样规整通过.

    真实triples.json(data_assets/retrieval_train)以pos_chunk_id/
    neg_chunk_ids引用候选池chunk → 按与评测候选池完全同口径的富化文本
    解析(HybridRecaller._rich_text: 图片chunk=caption+VLM key_elements).
    缺正例chunk的条目剔除; 缺负例chunk的该负例剔除(计数如实报告).
    """
    text_rows: list[dict[str, Any]] = []
    id_rows: list[dict[str, Any]] = []
    for row in raw:
        if isinstance(row, dict) and row.get("pos_chunk_id"):
            id_rows.append(row)
        else:
            text_rows.append(row)
    pairs, tstat = normalize_triples(text_rows)
    stat: dict[str, Any] = {"n_raw": len(raw),
                            "n_text_schema": tstat["n_ok"],
                            "n_chunkid_schema": len(id_rows)}
    n_pos_missing = n_neg_missing = 0
    if id_rows:
        import sys
        if str(BASE) not in sys.path:      # 直接以脚本运行时的包根注入
            sys.path.insert(0, str(BASE))
        from algorithms.blackboard.hybrid_recall import HybridRecaller
        rec = HybridRecaller(use_dense=False)
        by_id = rec.store._chunk_by_id()
        for row in id_rows:
            q = str(row.get("query", "")).strip()
            pos = by_id.get(str(row.get("pos_chunk_id", "")))
            if not q or pos is None:
                n_pos_missing += 1
                continue
            negs: list[str] = []
            for cid in row.get("neg_chunk_ids") or []:
                c = by_id.get(str(cid))
                if c is None:
                    n_neg_missing += 1
                    continue
                negs.append(rec._rich_text(c))
            pairs.append((q, rec._rich_text(pos), negs))
    stat |= {"n_pos_missing": n_pos_missing,
             "n_neg_missing": n_neg_missing, "n_ok": len(pairs)}
    return [{"query": q, "positive": p, "hard_negatives": negs}
            for q, p, negs in pairs], stat


_DEMO: list[tuple[str, str, list[str]]] = [
    ("数据获取接口采用什么传输协议",
     "数据获取接口采用TCP协议传输，支持断点续传，单次传输块大小为64KB。",
     ["统一传输服务支持TCP、UDP和多播协议，按业务类型自动选择传输方式。",
      "状态查询接口负责采集CPU占用率与内存占用率，采集周期为5秒。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "系统日志保存周期不少于90天，支持按日志级别检索。",
      "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。",
      "任务调度接口支持优先级抢占式调度，最高优先级为0级。",
      "时间同步精度要求为±10ms，采用NTP协议实现全系统统一授时。"]),
    ("服务状态采集的周期是多少",
     "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
     ["状态采集数据保存周期为30天，超期自动归档至冷存储。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。",
      "系统日志保存周期不少于90天，支持按日志级别检索。",
      "时间同步精度要求为±10ms，采用NTP协议实现全系统统一授时。",
      "任务调度接口支持优先级抢占式调度，最高优先级为0级。"]),
    ("流媒体传输服务的带宽要求是什么",
     "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
     ["统一传输服务支持TCP、UDP和多播协议，按业务类型自动选择传输方式。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "系统日志保存周期不少于90天，支持按日志级别检索。",
      "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。",
      "数据获取接口采用TCP协议传输，支持断点续传，单次传输块大小为64KB。",
      "时间同步精度要求为±10ms，采用NTP协议实现全系统统一授时。"]),
    ("数据存储的容量指标是多少",
     "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
     ["状态采集数据保存周期为30天，超期自动归档至冷存储。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "系统日志保存周期不少于90天，支持按日志级别检索。",
      "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。"]),
    ("用户管理提供哪些功能",
     "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
     ["权限分配支持基于角色的访问控制，角色之间允许继承。",
      "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "系统日志保存周期不少于90天，支持按日志级别检索。",
      "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。"]),
    ("报文模板的作用是什么",
     "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。",
     ["报文字段校验支持长度校验、类型校验和取值范围校验三种方式。",
      "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "系统日志保存周期不少于90天，支持按日志级别检索。"]),
    ("任务调度接口支持什么调度方式",
     "任务调度接口支持优先级抢占式调度，最高优先级为0级。",
     ["调度队列深度不低于128，任务等待超时时间为60秒。",
      "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "系统日志保存周期不少于90天，支持按日志级别检索。"]),
    ("系统日志的保存周期是多久",
     "系统日志保存周期不少于90天，支持按日志级别检索。",
     ["日志分级为调试、信息、警告、错误和致命五级。",
      "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。"]),
    ("时间同步的精度要求是什么",
     "时间同步精度要求为±10ms，采用NTP协议实现全系统统一授时。",
     ["时间同步服务器支持双机热备，切换时间不超过3秒。",
      "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "系统日志保存周期不少于90天，支持按日志级别检索。"]),
    ("接口控制文件规定哪些外部接口",
     "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
     ["接口控制文件变更需经过评审，评审通过后方可发布新版本。",
      "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
      "服务状态采集周期为5秒，采集内容包括CPU占用率、内存占用率和网络时延。",
      "流媒体传输服务要求支持不低于50Mbps的传输带宽，峰值可达100Mbps。",
      "数据存储容量不低于2TB，支持在线扩容，扩容期间业务不中断。",
      "用户管理提供用户注册、权限分配、角色管理和用户注销功能。",
      "报文模板用于规范化报文的字段格式，支持用户选择模板生成报文。",
      "系统日志保存周期不少于90天，支持按日志级别检索。"]),
]


def demo_triples(n: int = 10, seed: int = 0) -> list[dict[str, Any]]:
    """合成triples(确定性): 训练管线冒烟用, 每条带8个hard负例."""
    rng = random.Random(seed)
    themes = list(_DEMO)
    rng.shuffle(themes)
    out: list[dict[str, Any]] = []
    for i in range(max(0, n)):
        q, p, negs = themes[i % len(themes)]
        if i >= len(themes):
            q, p = f"{q}(变体{i})", f"{p}"
        out.append({"query": q, "positive": p, "hard_negatives": list(negs)})
    return out


# ── runs协议/tools兼容 ───────────────────────────────────

def _load_open_run() -> Any:
    """tools/run_utils.py按文件路径惰性加载(避免sys.path污染)."""
    if "open_run" not in _RUN_UTILS_CACHE:
        import importlib.util
        path = BASE / "tools" / "run_utils.py"
        spec = importlib.util.spec_from_file_location("bge_lora_run_utils", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"run_utils加载失败: {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _RUN_UTILS_CACHE["open_run"] = mod.open_run
    return _RUN_UTILS_CACHE["open_run"]


def _adapter_fingerprint(adapter_dir: Path) -> str:
    """adapter权重文件的指纹(sha1前8位): 推理缓存版本键(权重变更换文件)."""
    h = hashlib.sha1()
    files = sorted(p.name for p in adapter_dir.iterdir()
                   if p.name.startswith("adapter_model"))
    for name in files:
        h.update(name.encode("utf-8"))
        h.update((adapter_dir / name).read_bytes())
    return h.hexdigest()[:8]

# ── 训练器 ───────────────────────────────────────────────

class BgeLoRATrainer:
    """LoRA微调bge-large-zh(对比学习协议).

    fit(): triples→adapter落盘(默认models/embedding/bge_lora/),
    训练历史runs协议; embed(): 加载adapter的推理(按adapter指纹分文件
    的磁盘缓存). 失败显式记录last_error, 不静默吞.
    """

    def __init__(self, model_dir: Path | None = None,
                 adapter_dir: Path | None = None,
                 lora_r: int = 16, lora_alpha: int = 32,
                 lora_dropout: float = 0.05,
                 tau: float = 0.03, n_hard_neg: int = 7,
                 eff_batch: int = 64, micro_batch: int = 16,
                 lr: float = 2e-4, weight_decay: float = 0.01,
                 seed: int = 42, max_len: int = _MAX_LEN,
                 embed_batch: int = 64, use_cache: bool = True) -> None:
        self.model_dir = Path(model_dir or DEFAULT_MODEL_DIR)
        self.adapter_dir = Path(adapter_dir or DEFAULT_ADAPTER_DIR)
        self.lora_r = int(lora_r)
        self.lora_alpha = int(lora_alpha)
        self.lora_dropout = float(lora_dropout)
        self.tau = float(tau)
        self.n_hard_neg = int(n_hard_neg)
        self.eff_batch = int(eff_batch)
        self.micro_batch = int(micro_batch)
        self.lr = float(lr)
        self.weight_decay = float(weight_decay)
        self.seed = int(seed)
        self.max_len = int(max_len)
        self.embed_batch = int(embed_batch)
        self.use_cache = bool(use_cache)
        self.mode = "unavailable"
        self.last_error = ""
        self.stats: dict[str, Any] = {
            "device": "", "dim": 0, "n_train_params": 0, "fit_ms": 0.0,
            "gpu_mem_gb": 0.0, "gpu_reserved_gb": 0.0, "oom_halvings": 0,
            "micro_batch": self.micro_batch, "embed_chunk": self.embed_batch,
            "n_embed_calls": 0, "n_cache_hits": 0, "n_cache_texts": 0,
            "embed_ms": 0.0}
        self.meta: dict[str, Any] = {}
        self._torch: Any = None
        self._tok: Any = None
        self._model: Any = None
        self._device = ""
        self._infer_ready = False
        self._cache: dict[str, list[float]] = {}
        self._cache_path: Path | None = None
        self._dirty_since_save = 0
        self._atexit_registered = False

    # ══════════════════════════════════════════════════════
    # 训练
    # ══════════════════════════════════════════════════════

    def fit(self, triples: list[dict[str, Any]], epochs: int = 3,
            precision: str = "fp16", dropout: float | None = None,
            dev_frac: float = 0.1, run_root: Path | None = None,
            data_spec: dict[str, Any] | None = None,
            ) -> dict[str, Any]:
        """LoRA对比训练. 返回meta(也随adapter落盘adapter_meta.json).

        precision: "fp16"(autocast+GradScaler, GPU) | "fp32"(确定性口径).
        dropout: None=用模型默认(0.1), 0.0=关dropout(等价性测试用).
        run_root: runs协议根目录(默认data/gjb_438c/runs).
        """
        import torch
        import torch.nn.functional as F
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModel, AutoTokenizer

        data, dstat = normalize_triples(triples)
        if len(data) < 2:
            raise ValueError(
                f"训练至少需要2条triples, 得到{len(data)} (raw={dstat})")
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        amp = precision == "fp16" and device == "cuda"

        rng = random.Random(self.seed)
        ids = list(range(len(data)))
        rng.shuffle(ids)
        n_dev = int(len(data) * dev_frac) if len(data) >= 20 else 0
        dev_ids, train_ids = ids[:n_dev], ids[n_dev:]
        self.stats.update({"oom_halvings": 0, "device": device,
                           "micro_batch": self.micro_batch,
                           "embed_chunk": self.embed_batch})

        tok = AutoTokenizer.from_pretrained(str(self.model_dir),
                                            local_files_only=True)
        base = AutoModel.from_pretrained(str(self.model_dir),
                                         local_files_only=True)
        if dropout is not None:
            # nn.Dropout在建模期已由config实例化, 改config无效 → 直接改模块p
            for m in base.modules():
                if isinstance(m, torch.nn.Dropout):
                    m.p = float(dropout)
        model = get_peft_model(base, LoraConfig(
            r=self.lora_r, lora_alpha=self.lora_alpha,
            lora_dropout=self.lora_dropout, bias="none",
            target_modules=list(LORA_TARGET_MODULES),
            task_type="FEATURE_EXTRACTION"))
        model.to(device)
        model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False})
        model.train()
        dim = int(base.config.hidden_size)
        params = [p for p in model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=self.lr,
                                weight_decay=self.weight_decay)
        scaler = torch.amp.GradScaler("cuda", enabled=amp)
        self._torch = torch
        self._tok = tok
        self._model = model
        self._device = device
        self.stats.update({"dim": dim,
                           "n_train_params": int(sum(p.numel()
                                                     for p in params))})
        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()

        # CUDA OOM可能以OutOfMemoryError或其父类AcceleratorError异步抛出
        # (torch 2.11实测: sdpa kernel内OOM → AcceleratorError), 两者都接,
        # 但仅消息含"out of memory"才降batch重试, 其余CUDA错误如实上抛.
        accel_err = getattr(torch, "AcceleratorError", None)
        oom_errs: tuple[type[BaseException], ...] = (
            (torch.cuda.OutOfMemoryError, accel_err)
            if accel_err is not None else (torch.cuda.OutOfMemoryError,))

        def _is_oom(e: BaseException) -> bool:
            return "out of memory" in str(e).lower()

        open_run = _load_open_run()
        run = open_run("bge_lora_train", {
            "n_triples": len(data), "data_stat": dstat,
            "epochs": epochs, "lr": self.lr, "tau": self.tau,
            "eff_batch": self.eff_batch, "micro_batch": self.micro_batch,
            "n_hard_neg": self.n_hard_neg, "seed": self.seed,
            "lora": {"r": self.lora_r, "alpha": self.lora_alpha,
                     "dropout": self.lora_dropout,
                     "targets": list(LORA_TARGET_MODULES)},
            "weight_decay": self.weight_decay, "precision": precision,
            "dropout_override": dropout, "n_dev": len(dev_ids),
            "adapter_dir": str(self.adapter_dir),
            "data_spec": data_spec or {},
        }, root=run_root)
        run.log(event="start", device=device, amp=amp, dim=dim,
                n_train_params=self.stats["n_train_params"])

        def _enc(texts: list[str]) -> dict[str, Any]:
            enc = tok(texts, padding=True, truncation=True,
                      max_length=self.max_len, return_tensors="pt")
            return {k: v.to(device) for k, v in enc.items()}

        def _autocast() -> Any:
            if amp:
                return torch.autocast("cuda", dtype=torch.float16)
            import contextlib
            return contextlib.nullcontext()

        def _embed_no_grad(texts: list[str]) -> Any:
            with torch.no_grad(), _autocast():
                h = model(**_enc(texts)).last_hidden_state[:, 0]
            return F.normalize(h.float(), dim=-1)

        def _encode_rows(texts: list[str]) -> Any:
            """对齐顺序的no_grad编码(逐chunk; OOM自动减半chunk)."""
            model.eval()
            chunk = int(self.stats["embed_chunk"])
            rows: list[Any] = []
            i = 0
            while i < len(texts):
                try:
                    rows.append(_embed_no_grad(texts[i:i + chunk]))
                    i += chunk
                except oom_errs as e:
                    if not _is_oom(e) or chunk <= _MIN_CHUNK:
                        raise
                    chunk //= 2
                    self.stats["embed_chunk"] = chunk
                    self.stats["oom_halvings"] += 1
                    torch.cuda.empty_cache()
                    run.log(event="oom_halve_encode", chunk=chunk, at=i)
            model.train()
            if not rows:
                return torch.zeros((0, dim), device=device)
            return torch.cat(rows)

        def _encode_pool(texts: list[str]) -> tuple[list[str], Any]:
            uniq = list(dict.fromkeys(t for t in texts if t))
            return uniq, _encode_rows(uniq)

        train_pass = [data[i][1] for i in train_ids]
        train_pass += [n for i in train_ids for n in data[i][2]]
        dev_pass = ([data[i][1] for i in dev_ids]
                    + [n for i in dev_ids for n in data[i][2]])

        micro = max(_MIN_CHUNK, min(self.micro_batch, self.eff_batch))
        history: list[dict[str, Any]] = []
        t0 = time.time()
        for ep in range(1, epochs + 1):
            pool_texts, pool = _encode_pool(train_pass)
            pidx = {t: j for j, t in enumerate(pool_texts)}
            ep_order = list(train_ids)
            rng.shuffle(ep_order)
            tot_loss = 0.0
            tot_q = 0
            n_hit = 0
            n_steps = 0
            s = 0
            while s < len(ep_order):
                step_ids = ep_order[s:s + self.eff_batch]
                B = len(step_ids)
                s += B
                if B < 2 and not any(data[i][2][:self.n_hard_neg]
                                     for i in step_ids):
                    continue          # 单query且无hard负例: 无法构成对比
                p_texts = [data[i][1] for i in step_ids]
                p_texts += [n for i in step_ids
                            for n in data[i][2][:self.n_hard_neg]]
                rows = torch.tensor([pidx[t] for t in p_texts], device=device)
                P = pool[rows]                       # 一步内冻结的passage塔
                labels = torch.arange(B, device=device)
                while True:                          # OOM→减半micro重试
                    opt.zero_grad(set_to_none=True)
                    step_loss, step_hit = 0.0, 0
                    try:
                        for m0 in range(0, B, micro):
                            m_ids = step_ids[m0:m0 + micro]
                            with _autocast():
                                h = model(**_enc(
                                    [data[i][0] for i in m_ids])
                                ).last_hidden_state[:, 0]
                            q = F.normalize(h.float(), dim=-1)
                            scores = q @ P.T / self.tau
                            lab = labels[m0:m0 + micro]
                            loss = F.cross_entropy(scores, lab) \
                                * (len(m_ids) / B)
                            scaler.scale(loss).backward()
                            step_loss += float(loss.item())
                            step_hit += int(
                                (scores.argmax(dim=1) == lab).sum())
                        break
                    except oom_errs as e:
                        if (not _is_oom(e) or micro <= _MIN_CHUNK
                                or device != "cuda"):
                            raise
                        micro //= 2
                        self.stats["oom_halvings"] += 1
                        self.stats["micro_batch"] = micro
                        torch.cuda.empty_cache()
                        run.log(event="oom_halve", micro_batch=micro,
                                epoch=ep, step=s)
                scaler.step(opt)
                scaler.update()
                tot_loss += step_loss * B
                tot_q += B
                n_hit += step_hit
                n_steps += 1
            rec: dict[str, Any] = {
                "epoch": ep, "loss": round(tot_loss / max(tot_q, 1), 4),
                "train_acc": round(n_hit / max(tot_q, 1), 4),
                "n_steps": n_steps, "pool": len(pool_texts)}
            if dev_ids:
                dtexts, dpool = _encode_pool(dev_pass)
                dpidx = {t: j for j, t in enumerate(dtexts)}
                Q = _encode_rows([data[i][0] for i in dev_ids])
                sc = Q @ dpool.T
                n10, mrr = 0.0, 0.0
                for r in range(len(dev_ids)):
                    target = dpidx[data[dev_ids[r]][1]]
                    top = sc[r].topk(min(10, dpool.shape[0])).indices.tolist()
                    rank = top.index(target) + 1 if target in top else 0
                    if rank:
                        n10 += 1
                        mrr += 1.0 / rank
                rec |= {"dev_recall@10": round(n10 / len(dev_ids), 4),
                        "dev_mrr@10": round(mrr / len(dev_ids), 4)}
            history.append(rec)
            run.log(**rec)

        self.stats["fit_ms"] = round((time.time() - t0) * 1000, 1)
        if device == "cuda":
            self.stats["gpu_mem_gb"] = round(
                torch.cuda.max_memory_allocated() / 2**30, 2)
            self.stats["gpu_reserved_gb"] = round(
                torch.cuda.max_memory_reserved() / 2**30, 2)
        model.eval()
        self.adapter_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(self.adapter_dir))
        fp = _adapter_fingerprint(self.adapter_dir)
        self.meta = {
            "protocol": "LoRA InfoNCE: in-batch neg + hard neg, "
                        "channel-blocked passage塔(每epoch no_grad重编码)",
            "query_prefix": "none(对称用法, 与候选侧一致)",
            "lora": {"r": self.lora_r, "alpha": self.lora_alpha,
                     "dropout": self.lora_dropout,
                     "targets": list(LORA_TARGET_MODULES),
                     "n_params": self.stats["n_train_params"]},
            "n_triples": len(data), "n_train": len(train_ids),
            "n_dev": len(dev_ids), "data_stat": dstat,
            "epochs": epochs, "lr": self.lr, "tau": self.tau,
            "eff_batch": self.eff_batch, "micro_batch_actual": micro,
            "n_hard_neg": self.n_hard_neg, "seed": self.seed,
            "weight_decay": self.weight_decay, "precision": precision,
            "data_spec": data_spec or {}, "fingerprint": fp,
            "fit_ms": self.stats["fit_ms"],
            "gpu_mem_gb": self.stats["gpu_mem_gb"],
            "gpu_reserved_gb": self.stats["gpu_reserved_gb"],
            "oom_halvings": self.stats["oom_halvings"],
            "history": history,
        }
        (self.adapter_dir / "adapter_meta.json").write_text(
            json.dumps(self.meta, ensure_ascii=False, indent=1),
            encoding="utf-8")
        run.save_result(self.meta)
        run.log(event="done", fingerprint=fp,
                fit_ms=self.stats["fit_ms"])
        # embed复用内存中的已训练模型
        self._infer_ready = True
        self.mode = device
        self._init_cache(fp)
        if not self._atexit_registered:
            atexit.register(self._save_cache)
            self._atexit_registered = True
        return dict(self.meta)

    # ══════════════════════════════════════════════════════
    # 推理(embed): 加载adapter
    # ══════════════════════════════════════════════════════

    def ensure(self) -> str:
        """初始化推理模型并返回mode("gpu"|"cpu"|"unavailable").

        fit()后复用内存模型; 否则从adapter_dir加载adapter.
        失败原因在last_error.
        """
        if self._infer_ready:
            return self.mode
        self._infer_ready = True
        if not (self.adapter_dir / "adapter_config.json").exists():
            self.last_error = f"adapter not found: {self.adapter_dir}"
            return self.mode
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            self.last_error = f"torch/peft/transformers unavailable: {e}"
            return self.mode
        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._torch = torch
            self._tok = AutoTokenizer.from_pretrained(
                str(self.model_dir), local_files_only=True)
            base = AutoModel.from_pretrained(str(self.model_dir),
                                             local_files_only=True)
            self._model = PeftModel.from_pretrained(
                base, str(self.adapter_dir))
            self._model.to(self._device)
            self._model.eval()
            self.stats["dim"] = int(base.config.hidden_size)
        except (OSError, ValueError, RuntimeError) as e:
            self.last_error = f"adapter load failed: {e}"
            return self.mode
        self.mode = self._device
        self.stats["device"] = self._device
        self._init_cache(_adapter_fingerprint(self.adapter_dir))
        if not self._atexit_registered:
            atexit.register(self._save_cache)
            self._atexit_registered = True
        return self.mode

    # ── 推理向量缓存(按adapter指纹分文件) ──

    def _init_cache(self, fp: str) -> None:
        self._cache = {}
        self._cache_path = None
        self.stats["n_cache_texts"] = 0
        if not self.use_cache:
            return
        p = self.adapter_dir / f"bge_lora_cache_{fp}.pkl"
        if p.exists():
            try:
                with open(p, "rb") as f:
                    data = pickle.load(f)
                if isinstance(data, dict):
                    self._cache = {t: v for t, v in data.items()
                                   if isinstance(t, str)
                                   and isinstance(v, list)}
            except (pickle.UnpicklingError, EOFError, OSError) as e:
                self.last_error = f"lora cache unreadable: {e}"
                self._cache = {}
        self._cache_path = p
        self.stats["n_cache_texts"] = len(self._cache)

    def _save_cache(self) -> None:
        if not (self.use_cache and self._cache and self._cache_path):
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "wb") as f:
            pickle.dump(self._cache, f)
        self._dirty_since_save = 0

    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        """LoRA适配后嵌入(CLS池化+L2归一, fp32确定性, 磁盘缓存).

        与bge_local.embed同schema: text→1024维向量(空列表=失败).
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
            torch = self._torch
            t0 = time.time()
            for i in range(0, len(todo), self.embed_batch):
                part = todo[i:i + self.embed_batch]
                enc = self._tok(part, padding=True, truncation=True,
                                max_length=self.max_len,
                                return_tensors="pt")
                enc = {k: v.to(self._device) for k, v in enc.items()}
                with torch.no_grad():
                    h = self._model(**enc).last_hidden_state[:, 0]
                    h = torch.nn.functional.normalize(h.float(), dim=-1)
                fresh = dict(zip(part, h.cpu().tolist()))
                self._cache.update(fresh)
                out.update(fresh)
            self.stats["embed_ms"] = round(
                (time.time() - t0) * 1000, 1)
            self._dirty_since_save += len(todo)
            self.stats["n_cache_texts"] = len(self._cache)
            if self._dirty_since_save >= _SAVE_EVERY:
                self._save_cache()
        return out


# ── CLI ──────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="LoRA微调bge-large-zh检索模型")
    ap.add_argument("--data", type=Path, default=DEFAULT_TRIPLES_PATH,
                    help="triples.json路径(query/positive/hard_negatives)")
    ap.add_argument("--demo", type=int, default=0,
                    help="合成N条triples冒烟(忽略--data)")
    ap.add_argument("--limit", type=int, default=0, help="triples上限(0=全量)")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--tau", type=float, default=0.03,
                    help="InfoNCE温度(0.02-0.05搜索)")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--eff-batch", type=int, default=64)
    ap.add_argument("--micro-batch", type=int, default=16)
    ap.add_argument("--n-hard-neg", type=int, default=7)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    ap.add_argument("--dev-frac", type=float, default=0.1)
    ap.add_argument("--precision", choices=("fp16", "fp32"), default="fp16")
    args = ap.parse_args()

    if args.demo:
        triples = demo_triples(args.demo)
        data_spec: dict[str, Any] = {"source": "demo", "n": args.demo}
    elif args.data.exists():
        raw = json.loads(args.data.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            print(f"triples应为list, 得到{type(raw).__name__}: {args.data}")
            return 1
        if args.limit:
            raw = raw[:args.limit]
        triples, rstat = resolve_triples(raw)
        data_spec = {"source": str(args.data), "n": len(raw),
                     "resolve": rstat}
        print(f"解析: {rstat}")
    else:
        print(f"训练数据缺失: {args.data}")
        print("管线已就绪待数据(可先用 --demo 10 验证训练循环)")
        return 1
    _, dstat = normalize_triples(triples)
    print(f"triples: raw={dstat['n_raw']} ok={dstat['n_ok']} "
          f"skip={dstat['n_skipped']} | τ={args.tau} epochs={args.epochs} "
          f"eff_batch={args.eff_batch}")
    if dstat["n_ok"] < 2:
        print("可用triples不足2条")
        return 1

    tr = BgeLoRATrainer(adapter_dir=args.adapter_dir, tau=args.tau,
                        lr=args.lr, eff_batch=args.eff_batch,
                        micro_batch=args.micro_batch,
                        n_hard_neg=args.n_hard_neg, seed=args.seed)
    try:
        meta = tr.fit(triples, epochs=args.epochs, precision=args.precision,
                      dev_frac=args.dev_frac, data_spec=data_spec)
    except Exception as e:  # noqa: BLE001 — 显式失败报告, 防CUDA错误后进程僵死占显存
        print(f"训练失败: {type(e).__name__}: {e}")
        try:
            import torch
            torch.cuda.empty_cache()
        except (ImportError, RuntimeError):
            pass          # 清理尽力而为: torch/CUDA不可用时无从清理
        return 1
    h0, h1 = meta["history"][0], meta["history"][-1]
    print(f"loss: ep1={h0['loss']} → ep{h1['epoch']}={h1['loss']} | "
          f"train_acc={h1['train_acc']}")
    if "dev_recall@10" in h1:
        print(f"dev: recall@10={h1['dev_recall@10']} "
              f"mrr@10={h1['dev_mrr@10']}")
    print(f"LoRA参数: {meta['lora']['n_params']:,} | "
          f"显存峰值: {meta['gpu_mem_gb']}GB"
          f"(reserved {meta['gpu_reserved_gb']}GB) | "
          f"OOM减半: {meta['oom_halvings']}次 | "
          f"耗时: {meta['fit_ms'] / 1000:.1f}s")
    print(f"adapter → {args.adapter_dir}")
    print(f"元数据 → {tr.adapter_dir / 'adapter_meta.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
