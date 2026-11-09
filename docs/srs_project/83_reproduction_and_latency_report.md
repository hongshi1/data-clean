# 83 性能评测与Baseline复现报告（v1.0, 2026-11-10）

> 本报告为 M70 后全量复现记录：延迟基准（三层档位 + baseline吞吐）、
> 公开基准 5×5+2 矩阵复现（逐位对齐历史锚点）、管线性能汇总、
> 一键复现指令。所有数字可由 runs 协议产物逐位再生成。

## 1. 延迟评测（耗时层面）

### 1.1 管线三档延迟（91QA 全量实例，n=89，GPU，warmup 排除）

| 档位 | 组成 | mean | median | p95 | max | 一次性成本 |
|------|------|------|--------|-----|-----|-----------|
| fast | L0 NER + L1 规则 + 融合（零模型） | **9.1 ms** | 8.6 | 15.0 | 44.2 | import 预热 285 ms |
| standard (egt_v2) | + L2 NLI（EGT-only 微调） | 123.4 ms | 110.3 | 270.9 | 364.7 | 模型加载 8.1 s |
| standard (distilled_v1) | + L2 NLI（GLM-5.3 蒸馏，gate=0.8） | **118.4 ms** | 113.1 | 240.8 | 372.2 | 模型加载 2.0 s（冷启动≈8 s） |

- 吞吐：fast ≈ 110 实例/s；standard-distilled ≈ 8.4 实例/s（单卡串行）。
- **推理时零 LLM**（M66 起）：旧 L3 级联升级的 15–30 s/次（网络往返）
  延迟与 API 成本已按设计消除；教师 GLM-5.3 仅出现在训练期（一次性、
  全缓存）。
- 延迟产物：`runs/benchmark_latency_*/result.json`（runs 协议）。

### 1.2 Baseline 模型裸 pair 推理吞吐（512 pairs，GPU）

| 模型 | pairs/s | ms/pair |
|------|---------|---------|
| distilled_v1（D1，我们的） | **388.0** | **2.58** |
| egt_finetuned_v2（我们的 L2） | 343.0 | 2.92 |
| mDeBERTa 零样本 | 322.7 | 3.10 |
| cmnli_finetuned（公开监督微调） | 162.5 | 6.15 |
| Erlangshen-330M 零样本 | 138.6 | 7.21 |

注：distilled_v1 与 egt_v2 同为 mDeBERTa 架构（278M），吞吐差异来自
批内序列长度分布；所有 NLI 模型均在同一协议下测得。

## 2. 公开基准矩阵复现（5 外部 baseline + 2 对照 × 5 数据集）

### 2.1 复现设置

- 脚本：`tools/eval_public_matrix.py`（seed=42，模型视图：公开测试集
  全量、n>3000 抽 1000 保序；LLM 视图：公开集 200；自建列全量）
- 数据集（本地，`data/gjb_438c/public_nli/`）：XNLI-zh 5010 / OCNLI
  官方 test 2950 / CMNLI test 12241；自建：qa91（silver）、crossdoc06
  （平衡构造集 30）
- LLM 调用计量：**1023 次调用，1022 次缓存命中，1 次新调用**（历史
  prompt 全部命中磁盘缓存；1 次新调用为重试后缀变体，已入缓存）
- 总耗时 172.8 s；run：`runs/eval_public_matrix_c35a7981_20261110_013502`

### 2.2 矩阵（macro-F1；直推 pair 协议，非管线协议）

| 行 \ 列 | xnli_zh | ocnli | cmnli_test | qa91 | crossdoc06 |
|---------|---------|-------|------------|------|------------|
| BGE 三元中心（公开 train 拟合） | 0.5376 | 0.4996 | 0.5108 | 0.1173 | 0.2635 |
| Erlangshen-330M 零样本 | 0.7983 | 0.7919 | 0.8262 | 0.4147 | 0.3338 |
| mDeBERTa 零样本 | 0.7933 | 0.7229 | 0.8476 | 0.2947 | 0.5087 |
| mDeBERTa+CMNLI 50k 微调 | 0.8099 | 0.7276 | 0.8674 | 0.2761 | 0.5926 |
| GLM-5.3 直推（缓存） | 0.7606 | 0.8268 | 0.7705 | 0.6105 | **0.9666** |
| [对照] egt_finetuned_v2（我们的 L2） | 0.7504 | 0.6936 | 0.7984 | 0.2968 | 0.6102 |
| [对照] distilled_v1（D1，本轮新增行） | 0.7520 | 0.6916 | 0.8119 | 0.2802 | **0.6412** |

### 2.3 复现验证（与历史 run `eval_public_matrix_921b0139_20261030_143910` 逐位对比）

- 前 6 行（bge/erlangshen/mdeberta/cmnli/glm/egt_v2）**全部 30 个
  单元格与历史值逐位一致**（0.9666 vs 0.9666 等小数位含）
- 回归锚点：`glm_direct×qa91 = 0.6105` 与 B2 历史值逐位复现
  （result.json `regression.b2_cache_reproduction.reproduced = true`）
- 新增行 distilled_v1：公开基准保持（xnli +0.2pt、cmnli +1.35pt、
  ocnli −0.2pt vs egt_v2——无灾难遗忘）；crossdoc06 直推 +3.1pt
  （0.6102→0.6412）
- 口径注意：矩阵 qa91 列是**直推 pair 协议**（answer 整体作 hypothesis、
  无 claim 分解/无 gate/无专家），与管线协议（表 3 的 0.8047）不可直接
  比较；GLM 直推在管线外的 raw pair 上最强（0.6105）恰说明三态判定的
  难点在证据组装而非模型容量。

## 3. 管线性能汇总（端到端三态判定，推理纯本地）

| 系统（test-46 held-out，dev 校准） | acc | macro-F1 | refute F1 | P/R | 推理 LLM |
|------|------|---------|-----------|-----|---------|
| fast（纯确定性） | — | 0.7212* | 0.769* | 1.00/0.62 | 零 |
| standard-egt_v2 | 0.7826 | 0.5911 | 0.500 | 0.33/1.00 | 零 |
| **standard-distilled_v1（D1）** | **0.9130** | **0.8047** | **0.800** | 0.67/1.00 | **零** |
| 旧 cascade（NLI→GLM 复核，全 91 口径） | 0.9231* | 0.7860* | 0.857* | 1.00/0.75 | API |
| 旧 l3_llm（GLM 直推，全 91 口径） | 0.9451* | 0.8747* | 0.824* | 0.78/0.88 | API |

*全 91QA 口径（含 dev-45 训练数据，偏高）；无 * 号为 held-out test-46。
专项：violations-17 检出 16/17（refuteF1 0.970）；crossdoc-150 acc
0.5133（域绑定弱项，见 82 号文档 E2 分析）。

## 4. 一键复现指令

```powershell
# 环境（系统 Python 3.12 Anaconda；.env 已配置 GLM 密钥）
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'

# 4.1 延迟基准（~2 min，GPU）
python tools/benchmark_latency.py

# 4.2 公开矩阵 5×5+2（~3 min；LLM 行走缓存，无缓存时才调 API）
python tools/eval_public_matrix.py

# 4.3 管线三档 + 专项集（~15 min）
python tools/eval_distilled.py                      # test46/qa91/violations
python tools/calibrate_distilled_gate.py            # dev 校准 + test46 + crossdoc

# 4.4 D1 蒸馏再训练（可选，~3 min GPU + 教师标签已缓存）
python tools/train_distilled_nli.py                 # 重建 distilled_v1

# 4.5 回归测试
python -m pytest tests/test_public_baselines.py tests/test_paper_figures.py -q
```

预期数字：4.1 见 §1；4.2 见 §2.2 且 B2 锚点 0.6105 逐位复现；4.3
test46 mF1 0.8047；4.4 dev mF1 ≈0.61（15% holdout）。任何不一致以
runs/ 目录最新 result.json 为准并核对 git SHA。

## 5. 本轮涉及的代码修复（复现的前提）

1. `tools/benchmark_latency.py`：适配 M66 后架构（旧脚本引用已删除的
   use_cascade/L3）；新增 baseline 吞吐段。
2. `tools/eval_paper_matrix.py` / `algorithms/consistency/public_baselines.py`：
   LLM 调用从已删除的 `algorithms/common/llm_client` 迁移到
   `tools/llm_teacher.py`（cache-key 逐位兼容，历史 12914 条缓存全部
   命中，复现零漂移）。
3. `algorithms/consistency/nli_local.py` MODELS：注册 distilled_v1 与
   cmnli_finetuned（吞吐基准/矩阵行用）。
4. `tools/eval_public_matrix.py` REFERENCE_ROWS：新增 distilled_v1 对照行。
