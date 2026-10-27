"""BGE域适配(A8)测试: 训练对构造/零初始化恒等/训练与保存往返.

锁定内容(科研数字关联, tools/eval_bge_adapt):
  - load_qa_pairs: 同seed采样可复现, CJK过滤+答案截断(数据口径)
  - 零初始化残差头恒等: 适配嵌入=原生BGE(保底不劣化的根据)
  - fit只训头: loss有限, 权重指纹变更; save/load往返嵌入逐位一致
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from algorithms.archive.bge_domain_adapt import BgeAdapter, load_qa_pairs

BASE = Path(__file__).resolve().parents[1]
HAS_CORPUS = (BASE / "data/gjb_438c/easydataset/srs_alpaca_full.jsonl").exists()
HAS_MODEL = (BASE / "models/embedding/bge-large-zh-v1.5/config.json").exists()

_SYNTH_PAIRS = [
    ("接口控制文件包含哪些外部接口？", "接口控制文件规定了数据获取接口、"
     "状态查询接口和任务调度接口等外部接口。"),
    ("数据获取的功能划分是什么？", "数据获取功能划分为数据汇集、数据转换"
     "和数据存储三个子功能。"),
    ("服务状态采集的周期是多少？", "服务状态采集周期为5秒，采集内容包括"
     "CPU占用率、内存占用率和网络时延。"),
    ("报文模板的作用是什么？", "报文模板用于规范化报文的字段格式，"
     "支持用户选择模板生成报文。"),
    ("流媒体传输服务的带宽要求？", "流媒体传输服务要求支持不低于50Mbps的"
     "传输带宽，峰值可达100Mbps。"),
    ("统一传输服务包含哪些协议？", "统一传输服务支持TCP、UDP和多播协议，"
     "按业务类型自动选择传输方式。"),
    ("数据存储的容量指标是多少？", "数据存储容量不低于2TB，支持在线扩容，"
     "扩容期间业务不中断。"),
    ("用户管理提供哪些功能？", "用户管理提供用户注册、权限分配、角色管理"
     "和用户注销功能。"),
]


@pytest.mark.skipif(not HAS_CORPUS, reason="QA语料缺失")
def test_load_qa_pairs_deterministic_and_filtered():
    a = load_qa_pairs(limit=200, seed=42)
    b = load_qa_pairs(limit=200, seed=42)
    assert a == b                       # 同seed采样可复现
    assert len(a) == 200
    assert load_qa_pairs(limit=200, seed=7) != a   # seed生效
    assert load_qa_pairs() == load_qa_pairs()      # limit=0全量也确定
    for ent, ctx in a:
        assert len(ent) >= 4            # 实体化问句(对齐评测query分布)
        assert 30 <= len(ctx) <= 400    # 原文上下文≥30字, 截400字
        assert not ctx.startswith(("章节", "跨章节", "UML关系"))
    full = load_qa_pairs()
    assert 3000 <= len(full) <= 8000    # 全量池在规定采样区间(~5.5k)


@pytest.mark.skipif(not HAS_MODEL, reason="BGE模型缺失")
def test_zero_init_adapter_identity(tmp_path: Path):
    """零初始化残差头: 适配嵌入≈原生BGE(保底不劣化)."""
    from algorithms.common.bge_local import BgeLocal
    ad = BgeAdapter(adapter_dir=tmp_path, use_cache=False)
    if ad.ensure() == "unavailable":
        pytest.skip(f"加载失败: {ad.last_error[:60]}")
    assert ad.stats["n_params"] > 900_000    # 轻量头≈1.05M参数
    texts = ["数据获取转换分系统的接口控制文件", "服务集成框架提供组件注册能力"]
    got = ad.embed(texts)
    native = BgeLocal(use_cache=False).embed(texts)
    for t in texts:
        assert got[t] and len(got[t]) == 1024
        assert max(abs(x - y) for x, y in zip(got[t], native[t])) < 1e-4


@pytest.mark.skipif(not HAS_MODEL, reason="BGE模型缺失")
def test_fit_changes_head_and_roundtrip(tmp_path: Path):
    """小样本fit: loss有限/指纹变更; save→load往返嵌入逐位一致."""
    ad = BgeAdapter(adapter_dir=tmp_path, use_cache=False)
    if ad.ensure() == "unavailable":
        pytest.skip(f"加载失败: {ad.last_error[:60]}")
    fp_zero = ad.fingerprint()
    meta = ad.fit(_SYNTH_PAIRS, epochs=2, batch_size=4, seed=42)
    assert meta["n_pairs"] == len(_SYNTH_PAIRS)
    assert len(meta["loss_hist"]) == 2
    assert all(not math.isnan(h["loss"]) for h in meta["loss_hist"])
    assert meta["loss_hist"][-1]["loss"] < 0.5   # InfoNCE收敛(ln4≈1.39以下)
    assert "alpha" in meta and "data_spec" in meta
    assert ad.fingerprint() != fp_zero
    texts = [_SYNTH_PAIRS[0][0], _SYNTH_PAIRS[0][1], "未见过的军事术语查询"]
    v1 = ad.embed(texts)
    saved = ad.save()
    assert (saved / "adapter.pt").exists()
    ad2 = BgeAdapter(adapter_dir=tmp_path, use_cache=False)
    assert ad2.ensure() != "unavailable"
    assert ad2.stats["trained"] is True
    assert ad2.fingerprint() == ad.fingerprint()
    v2 = ad2.embed(texts)
    for t in texts:
        assert v1[t] and v2[t]
        assert max(abs(x - y) for x, y in zip(v1[t], v2[t])) < 1e-5
