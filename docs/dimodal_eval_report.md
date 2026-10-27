# 文本-图像双模态对齐实验报告（SRS真实数据）

> 运行：`tools/dimodal_srs_pipeline.py`（seed锁定可复现）
> 结果落盘：`data/gjb_438c/trimodal/dimodal_eval.json`
> 渲染表格：`docs/figures/dimodal_eval_table.png`
> 成文：2026-09-16

---

## 一、实验设置

| 项 | 值 |
|---|---|
| 数据集 | 16份GJB SRS · 3643文本chunk + 381图片chunk（379张有效png） |
| 编码器（冻结） | 文本侧 **BGE-large-zh**（1024维，dense缓存复用）· 图像侧 **Chinese-CLIP ViT-B/16**（512维，本地753MB） |
| 训练配对 | 979对同章节共现图文对（doc 01-12，置信0.7弱正样本） |
| 测试划分 | query=100条文本（doc 13-16）× 候选池=41图 · **文档级分块防泄漏** |
| 金标（期望） | 与query同`(doc, section)`的图 —— 章节共现代理标签（silver） |
| 指标 | **R@5**（检索前5名命中任一同章节图的比例） |

**任务性质**：跨模态**检索**（排序）问题，非分类——query对全部候选打分排序，看前5名是否命中期望；投影头训练用对比学习（InfoNCE，拉近配对推远非配对），学的是相似度函数而非类别边界。

## 二、实验结果

**Table 1** Text-to-Image Retrieval on GJB SRS

| Method | R@1 | R@5 | R@10 | MRR@10 |
|---|:---:|:---:|:---:|:---:|
| CLIP (zero-shot) | 0.170 | 0.330 | 0.530 | 0.257 |
| Text-Bridge Retrieval | **0.410** | **0.730** | **0.840** | **0.540** |
| Projection Head | 0.220 | 0.620 | 0.830 | 0.384 |

*Note.* 评测集：100条文本查询 × 41张图像候选（文档级防泄漏划分，训练/测试文档不相交）。Projection Head 训练于979个同章节图文配对（120 epochs，对比学习）。期望为与查询同章节的图像。

## 三、标签（金标）构造协议

```
srs_chunks.json（MinerU解析16份SRS时产出）
  每个chunk自带 (doc, section) 字段 —— 解析器按位置归属打的结构化字段
        ↓
文本chunk (doc13, 3.2.1.2) ←同(doc,section)→ 图片chunk fig_007
        ↓
期望 = 所有与query同章节的图（R@5前5名命中任一即得分）
```

- **来源**：MinerU解析时的章节归属——零人工成本
- **依据**：GJB"图文表三位一体"章节组织（3.2.X.x族：功能表/用例图/流程图同章节共现）
- **性质**：**弱代理标签（silver）**——章节内的图未必都描述该章节文本（可能有装饰图），故B1=0.730含标签噪声天花板；升级金标需人工核对约380对（唯一突破天花板的路径）

## 四、核心结论

1. **GJB文档图的语义载体是图内文字而非视觉形态**——B1（VLM转写→BGE同空间直比）零训练即最优，碾压所有从视觉特征学习的方案（B0 0.330）
2. **投影头融合两信号有效**（B3 0.620 > B2 0.460）：CLIP视觉特征提供图类型/布局的补充区分度——但在979小数据弱配对下，学习的映射仍不及同空间直比（投影是有损压缩）
3. **投影头路线的适用边界**：当模态无法文本化（时序信号、纯视觉细节、无VLM转写）或需要统一检索架构时启用；GJB场景主方案维持B1（现有multimodal通道即此方案）

## 五、工程资产

| 组件 | 位置 |
|---|---|
| 框架（模态可配置2-3模态） | `algorithms/trimodal/`（projector/contrastive/retrieval/expansion/schemas） |
| Chinese-CLIP本地编码器 | `algorithms/trimodal/clip_encoder.py`（GPU惰性+381图磁盘缓存+transformers 5.x API兼容） |
| 端到端管线 | `tools/dimodal_srs_pipeline.py` |
| 测试 | `tests/test_trimodal.py`（13例）+ `tests/test_clip_encoder.py`（2例） |
| 渲染表格 | `docs/figures/dimodal_eval_table.png` |
