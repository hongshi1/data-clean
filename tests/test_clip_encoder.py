"""Chinese-CLIP编码器测试: 降级路径/API兼容/缓存(确定性)."""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.trimodal.clip_encoder import ChineseClipEncoder

BASE = Path(__file__).resolve().parents[1]
HAS_MODEL = (BASE / "models/clip/chinese-clip-vit-base-patch16"
             / "config.json").exists()


def test_unavailable_returns_zero_vectors():
    """模型缺失 → mode=unavailable, 嵌入返回零向量(不崩溃)."""
    c = ChineseClipEncoder(use_cache=False)
    c.model_dir_override = None  # 占位: 构造后不可改路径, 用子类绕过
    c2 = _BrokenDirEncoder()
    assert c2.ensure() == "unavailable"
    assert c2.image_embed(["x.png"]) == [[0.0] * 512]
    assert c2.text_embed(["文本"]) == [[0.0] * 512]


class _BrokenDirEncoder(ChineseClipEncoder):
    def __init__(self) -> None:
        super().__init__(use_cache=False)
        self._model_dir = BASE / "nonexistent_clip"

    def ensure(self) -> str:  # type: ignore[override]
        if not (BASE / "nonexistent_clip" / "config.json").exists():
            self.last_error = "model not found (test)"
            self._ready = True
            return "unavailable"
        return super().ensure()


@pytest.mark.skipif(not HAS_MODEL, reason="Chinese-CLIP模型缺失")
def test_real_model_embeddings():
    """真实模型: 图文嵌入维度512且L2归一(零资源环境跳过)."""
    c = ChineseClipEncoder(use_cache=False)
    mode = c.ensure()
    if mode == "unavailable":
        pytest.skip(f"加载失败: {c.last_error[:60]}")
    import numpy as np
    from PIL import Image
    img = Image.new("RGB", (224, 224), color=(30, 60, 120))
    v = np.asarray(c.image_embed([img])[0])
    assert v.shape == (512,)
    assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-3
    t = np.asarray(c.text_embed(["查询收件箱接口"])[0])
    assert t.shape == (512,)
    assert abs(float(np.linalg.norm(t)) - 1.0) < 1e-3
