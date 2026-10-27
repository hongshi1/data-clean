r"""bge-large-zh-v1.5 GPU冒烟测试: 验证CUDA推理 + SRS域语义区分度
分区信号验证:
  - 同义改写(编辑距离盲区) → 应高相似
  - 不相关功能对 → 应低相似
  - 错字对 → 应极高相似(需编辑距离互补, embedding单独抓不到)
  - 值矛盾对 → 相似度仍高(参数矛盾是regex/NLI的活, 不是embedding的)
用法: python tools/test_bge_gpu.py
"""
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from torch_dll_fix import ensure_torch_imports  # noqa: E402

torch = ensure_torch_imports()
from transformers import AutoModel, AutoTokenizer  # noqa: E402

MODEL_DIR = BASE / "models/embedding/bge-large-zh-v1.5"


def main():
    assert torch.cuda.is_available(), "CUDA不可用"
    device = "cuda"
    print(f"device={device} | {torch.cuda.get_device_name(0)}")

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    mdl = AutoModel.from_pretrained(str(MODEL_DIR), local_files_only=True).to(device)
    mdl.eval()
    n_params = sum(p.numel() for p in mdl.parameters())
    print(f"加载OK: {n_params/1e6:.0f}M参数, hidden={mdl.config.hidden_size}")

    @torch.no_grad()
    def embed(texts):
        enc = tok(texts, padding=True, truncation=True, max_length=256,
                  return_tensors="pt").to(device)
        h = mdl(**enc).last_hidden_state[:, 0]  # CLS pooling
        h = torch.nn.functional.normalize(h, dim=-1)
        return h

    pairs = [
        ("同义改写", "数据获取与转换", "数据采集与转换", "HIGH"),
        ("同义改写", "界面集成框架软件", "界面整合框架软件", "HIGH"),
        ("不相关",   "数据获取与转换", "流媒体传输服务",   "LOW"),
        ("不相关",   "数据归集功能",   "软件部署管理",     "LOW"),
        ("错字",     "结构化数据归集", "结操化数据归集",   "VERY_HIGH(编辑距离负责)"),
        ("值矛盾",   "查询响应时间不超过1秒", "查询响应时间不超过3秒", "HIGH(参数矛盾归regex/NLI)"),
    ]
    t0 = time.time()
    scores = []
    for name, a, b, expect in pairs:
        va, vb = embed([a]), embed([b])
        s = float((va @ vb.T).item())
        scores.append(s)
        print(f"  [{name}] {a} × {b} → cos={s:.4f}  期望:{expect}")
    elapsed = time.time() - t0
    print(f"6对推理耗时: {elapsed:.2f}s (含首次warmup)")

    # 批量吞吐(GPU价值所在)
    texts = ["功能" + str(i) + "：对服务插件代码进行编译并部署验证" for i in range(128)]
    t0 = time.time()
    vecs = embed(texts)
    dt = time.time() - t0
    print(f"批量128条: {dt:.2f}s ({128/dt:.0f}条/s), 维度={vecs.shape}")

    # 分区校验
    high = scores[0] > 0.85 and scores[1] > 0.85
    low = scores[2] < 0.75 and scores[3] < 0.75
    # 错字(0.90)与同义改写(0.86~0.91)在同一相似带 → embedding不可分, 验证互补性论断
    typo_indistinguishable = abs(scores[4] - scores[0]) < 0.08
    print(f"\n分区校验: 同义改写高相似={high} | 不相关低相似={low} | 错字与改写不可分={typo_indistinguishable}")
    if high and low and typo_indistinguishable:
        print("PASS: bge-large-zh-v1.5 GPU推理+语义分区符合预期"
              "(错字/改写同带 → term_checker需编辑距离+embedding双信号)")
    else:
        print("WARN: 分区结果偏离预期, 需检查阈值设定")


if __name__ == "__main__":
    main()
