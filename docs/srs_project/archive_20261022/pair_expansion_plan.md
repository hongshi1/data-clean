# Pair扩容 + LLM裁决 + 数据集整合 详细方案

## 目标

将pair_dataset从366对扩容到878对(+512对BGE匹配)，经LLM裁决后整合进canonical数据集，产出高质量训练/评测数据集。

## 全流程

```
Phase 1: BGE匹配扩容(已完成)
  输入: 5231 chunks + anchors_v3(16文档373图2831节点)
  方法: BGE语义匹配(表格标题×同文档图节点,阈值0.60)
  产出: 608对新增(高195+中317+低96)
  策略: 取高+中质量512对进入Phase 2

Phase 2: LLM裁决标注(~25分钟,走缓存)
  输入: 512个新增pair
  方法: GLM-5 CoT裁决(带证据注入: 表格内容+图节点列表)
  产出: 512条标注(real_bug/benign_variation/unsure)
  质控: 双LLM一致(GLM+Kimi)优先,分歧项CoT仲裁

Phase 3: 数据集整合(~5分钟)
  输入: 512条裁决结果 + 现有canonical数据
  操作:
    1. 将新增pair转换为canonical格式(Evidence/Pair/metadata)
    2. 按文档级切分(训练/测试零泄漏)
    3. 更新canonical/train.jsonl和test.jsonl
  产出: 扩容后的canonical数据集(~878+366=1244个真实pair)

Phase 4: 重新训练v18(~5分钟)
  输入: 扩容后canonical(去污染、去证据反驳)
  方法: 与v12完全相同配方(RoBERTa-102M, 锚点适配)
  产出: roberta-v18-expanded模型

Phase 5: 评测(~2分钟)
  在相同的clean130+md166上评测v18 vs v12
  预期: 数据量翻倍(896→1800+)可能提升2-5个点

Phase 6: QA合成更新(~10分钟)
  用扩容后的数据集重新生成QA(含质控)
  产出: 更大规模的qa_dataset_v3.json
```

## Phase 2详细设计: LLM裁决

### 裁决Prompt

```
你是SRS需求文档一致性审查专家。基于以下完整证据判断一致性。

[表格标题] {table_title}
[表格内容(前300字)] {table_text}
[同文档的图节点列表] {all_nodes}

请判断: 表格中列出的内容与图节点是否一致？

规则:
- real_bug: 表格中的核心功能/接口/用例在图节点中完全找不到对应
            (数据流断裂、关键组件缺失)
- benign_variation: 图节点涵盖了表格的核心内容,仅在粒度/表述上有差异
                   (图比表格粗、多个条目合并、辅助内容省略)
- unsure: 基于提供的信息无法确定

只输出JSON: {{"label": "real_bug|benign_variation|unsure", "reason": "一句话引用具体证据的理由"}}
```

### 裁决协议

```
第一轮: GLM-5裁决全部512条(走缓存)
第二轮: Kimi裁决全部512条(走缓存,用于双LLM一致率)
融合: 
  - 双方一致(如都判real_bug) → 采纳,高置信
  - 双方分歧 → GLM-5 CoT再仲裁(第二轮prompt加入更详细的推理要求)
  - 仍然分歧 → 标记unsure,不进入训练集
```

### 质控指标

| 指标 | 目标 |
|---|---|
| 双LLM一致率 | >60%(参照之前42-44%的基准) |
| real_bug比例 | 30-70%(过大/过小都不好) |
| unsure比例 | <20% |
| 证据引用率 | >80%(reason中包含具体内容) |

## Phase 3详细设计: 数据集整合

### 新增pair的canonical格式转换

```python
{
    "id": "PD-bge-{n}",
    "source": "srs_anchor",  # 归类为锚点(真实数据)
    "pair": {
        "premise": "表格「{table_title}」包含: {table_content}",
        "hypothesis": "图中的节点包括: {matched_nodes}"
    },
    "label": "inconsistent" if real_bug else "consistent",
    "angle": {
        "scene": "{scene}",
        "modality": "table-diagram",
        "type": "{分类的检测类型}"
    },
    "provenance": {
        "doc": "{doc_id}",
        "origin": "bge_match:{similarity}",
        "surface": "T1",
        "protocol": "dual_llm" or "cot"
    },
    "split": "train" if doc not in test_docs else "test",
    "quality": {
        "contamination": "",
        "flags": []
    },
    "context": {
        "table": "{table_text前12行}",
        "diagram": "{图节点列表前25个}",
        "text": "",
        "image": ""
    }
}
```

### 切分规则

```
训练文档: 01, 02(排除clean130), 03, 05, 06, 08-16
测试文档: 04, 07 (与现有保持一致)
```

## Phase 4详细设计: 重新训练

```
训练数据: 扩容后canonical中的srs_anchor项
  - 排除doc02中与clean130重叠的项
  - 排除evidence_refuted标记的项
  - 预计: 原896条 + 新增~400条(训练分割) = ~1300条

配方: 与v12完全相同(控制变量,只改数据量)
  模型: chinese-roberta-wwm-ext (102M)
  训练: 5轮, lr=2e-5, 良性×6过采样
  输出: models/nli/roberta-v18-expanded

对照: v12(原896条训练) vs v18(扩容后~1300条训练)
  预期: 数据量+45%,bAcc可能提升0-5个点
  如果不提升: 说明896条已饱和(数据效率论证)
```

## Phase 5详细设计: 评测

```
评测集: 与v12完全相同
  clean130: 130条(02文档,零训练重叠)
  md166: 166条(04/07文档+接口场景,零训练重叠)

指标: bAcc(平衡准确率)
报告: v18 vs v12的逐条对比(哪些条目翻转了)
```

## Phase 6详细设计: QA合成

```
输入: 扩容后的canonical(含新增pair)
变异: 4个算子(ParamShift, TermSwap, ItemRemove, OrderSwap)
质控: 5项规则(空问题/空答案/无证据/无解释/空槽)
产出: 预计QA数量从1080→2000+

新增场景覆盖(目标):
  sc1(能力表): 87→200+
  sc4(流程图): 138→200+
  sc5(子功能): 12→200+ (需LLM定向生成补充)
```

## 时间估算

| Phase | 任务 | 时间 |
|---|---|---|
| 1 | BGE匹配扩容 | ✅已完成 |
| 2 | LLM裁决(512条×2轮) | ~25分钟 |
| 3 | 数据集整合 | ~5分钟 |
| 4 | 重新训练v18 | ~5分钟 |
| 5 | 评测 | ~2分钟 |
| 6 | QA合成 | ~10分钟 |
| **总计** | | **~47分钟** |

## 风险与对策

| 风险 | 对策 |
|---|---|
| BGE匹配的pair语义关联不够(表格和图不完全对应) | LLM裁决时会发现(标记unsure) |
| LLM裁决的标签噪声 | 双LLM一致率监控+分歧项仲裁 |
| 新增数据分布偏移(BGE匹配的对与原始锚点管线不同) | 训练后评测验证(如果v18不比v12差,说明可用) |
| 数据量增加反而降低性能 | v12作为回退(论文报告两者对比,作为"数据效率"分析) |
