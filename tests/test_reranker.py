"""BgeReranker测试: 模型加载/区分度/降级路径(确定性, GPU可用时)."""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.blackboard.reranker import BgeReranker

BASE = Path(__file__).resolve().parents[1]
HAS_MODEL = (BASE / "data/models/bge-reranker-v2-m3/config.json").exists()


def _gpu_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def test_reranker_unavailable_path():
    """模型目录不存在 → mode=unavailable, score返回中性0.5."""
    r = BgeReranker(model_dir=BASE / "nonexistent_reranker")
    scores = r.score([("q", "p"), ("", "")])
    assert r.mode == "unavailable"
    assert scores == [0.5, 0.5]


def test_reranker_empty_pairs():
    r = BgeReranker()
    assert r.score([]) == []


@pytest.mark.skipif(not HAS_MODEL, reason="reranker模型缺失")
@pytest.mark.skipif(not _gpu_available(), reason="无GPU(模型2.27GB, CPU太慢)")
def test_reranker_discriminates_relevance():
    """区分度: 相关对分数应显著高于无关对."""
    r = BgeReranker()
    if r.ensure() == "unavailable":
        pytest.skip(f"加载失败: {r.last_error[:60]}")
    scores = r.score([
        ("用户登录", "用户输入用户名密码完成登录认证"),
        ("用户登录", "界面集成框架提供组件渲染功能"),
    ])
    assert scores[0] > scores[1] * 5  # 相关>>无关
