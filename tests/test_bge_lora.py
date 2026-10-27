"""BGE LoRA检索微调(bge_lora_retriever)测试.

锁定(关联tools/eval_lora_retriever的评测数字):
  - normalize_triples/demo_triples: 灵活键规整+合成数据确定性(纯CPU)
  - fit 1-epoch合成小样本: 训练循环/adapter保存/meta/runs协议产物
  - embed: adapter加载推理(1024维/L2归一/save-load往返逐位一致)
  - 通道分块梯度累积精确性: micro=3一步 ≡ micro=1×3累积
    (fp32+dropout=0 — passage塔一步内冻结⇒损失行独立, 见模块docstring)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.archive.bge_lora_retriever import (
    BgeLoRATrainer,
    demo_triples,
    normalize_triples,
)

BASE = Path(__file__).resolve().parents[1]
HAS_MODEL = (BASE / "models/embedding/bge-large-zh-v1.5/config.json").exists()


def _has_gpu() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


GPU = _has_gpu()

_TRIPLES = [
    {"query": "数据获取接口采用什么传输协议",
     "positive": "数据获取接口采用TCP协议传输，支持断点续传，"
                 "单次传输块大小为64KB。",
     "hard_negatives": [
         "状态查询接口负责采集CPU占用率与内存占用率，采集周期为5秒。",
         "统一传输服务支持TCP、UDP和多播协议，按业务类型自动选择。",
         "数据存储容量不低于2TB，支持在线扩容。"]},
    {"query": "流媒体传输服务的带宽要求是什么",
     "positive": "流媒体传输服务要求支持不低于50Mbps的传输带宽，"
                 "峰值可达100Mbps。",
     "hard_negatives": [
         "服务状态采集周期为5秒，采集内容包括CPU占用率和网络时延。",
         "数据存储容量不低于2TB，支持在线扩容。",
         "用户管理提供用户注册、权限分配、角色管理功能。"]},
    {"query": "用户管理提供哪些功能",
     "positive": "用户管理提供用户注册、权限分配、角色管理和用户注销"
                 "四类功能。",
     "hard_negatives": [
         "接口控制文件规定了数据获取接口、状态查询接口和任务调度接口。",
         "数据获取功能划分为数据汇集、数据转换和数据存储三个子功能。",
         "系统日志保存周期不少于90天，支持按日志级别检索。"]},
]


def test_normalize_triples_flexible_keys():
    raw = [
        {"question": "甲", "passage": "甲文", "negs": ["乙文", "丙文"]},
        {"query": "丁", "positive": "丁文", "hard_negatives": "戊文"},
        {"query": "", "positive": "缺query"},
        {"query": "己"},
        "不是字典",
    ]
    out, stat = normalize_triples(raw)
    assert stat == {"n_raw": 5, "n_ok": 2, "n_skipped": 3}
    assert out[0] == ("甲", "甲文", ["乙文", "丙文"])
    assert out[1] == ("丁", "丁文", ["戊文"])


def test_demo_triples_deterministic():
    a, b = demo_triples(10), demo_triples(10)
    assert a == b
    assert len(a) == 10
    assert all(len(t["hard_negatives"]) >= 7 for t in a)
    assert demo_triples(10, seed=1) != a


@pytest.mark.skipif(not (HAS_MODEL and GPU), reason="需BGE模型+GPU")
def test_fit_smoke_save_load(tmp_path: Path):
    ad = tmp_path / "adapter"
    tr = BgeLoRATrainer(adapter_dir=ad, eff_batch=3, micro_batch=3,
                        n_hard_neg=2, lr=1e-3, embed_batch=4)
    meta = tr.fit(_TRIPLES, epochs=1, precision="fp32", dropout=0.0,
                  dev_frac=0.0, run_root=tmp_path / "runs")
    assert meta["n_train"] == 3
    loss = meta["history"][0]["loss"]
    assert 0.0 < loss < 20.0
    assert (ad / "adapter_config.json").exists()
    assert (ad / "adapter_meta.json").exists()
    runs_dirs = list((tmp_path / "runs").iterdir())
    assert len(runs_dirs) == 1
    assert (runs_dirs[0] / "config.json").exists()
    assert (runs_dirs[0] / "result.json").exists()
    assert (runs_dirs[0] / "log.jsonl").exists()

    texts = [_TRIPLES[0]["query"], "未见过的军事术语查询"]
    v = tr.embed(texts)
    for t, vec in v.items():
        assert len(vec) == 1024
        assert abs(sum(x * x for x in vec) - 1.0) < 1e-3
    # 新实例从磁盘加载adapter: 往返一致(fp32确定性)
    tr2 = BgeLoRATrainer(adapter_dir=ad, embed_batch=4, use_cache=False)
    v2 = tr2.embed(texts)
    assert tr2.ensure() != "unavailable"
    for t in texts:
        assert v[t] and v2[t]
        assert max(abs(x - y) for x, y in zip(v[t], v2[t])) < 1e-5


@pytest.mark.skipif(not (HAS_MODEL and GPU), reason="需BGE模型+GPU")
def test_grad_accum_equivalence(tmp_path: Path):
    """通道分块梯度累积精确性: micro=3 ≡ micro=1×3.

    passage塔在一步内no_grad冻结 ⇒ 各query损失行独立 ⇒ 梯度累积
    与全batch一步数值等价(有效batch=全batch, in-batch负例不缩水).
    """
    texts = [t["query"] for t in _TRIPLES]
    outs: list[dict[str, list[float]]] = []
    for sub, micro in (("a", 3), ("b", 1)):
        tr = BgeLoRATrainer(adapter_dir=tmp_path / sub, eff_batch=3,
                            micro_batch=micro, n_hard_neg=2, lr=1e-3,
                            embed_batch=4, use_cache=False,
                            lora_dropout=0.0)
        tr.fit(_TRIPLES, epochs=1, precision="fp32", dropout=0.0,
               dev_frac=0.0, run_root=tmp_path / "runs")
        outs.append(tr.embed(texts))
    for t in texts:
        assert outs[0][t] and outs[1][t]
        assert max(abs(x - y) for x, y in
                   zip(outs[0][t], outs[1][t])) < 1e-4
