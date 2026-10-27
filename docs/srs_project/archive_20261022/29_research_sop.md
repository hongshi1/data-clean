# 29 研究流程规范(SOP)与批次修复计划

日期: 2026-10-14
目的: 把"上下文关联"研究从探索式推进转为**可审计的规范化流程**.

## 一、研究循环(五步闭环)

```
① 假设登记 → ② 实验执行 → ③ 统一评测 → ④ 结论归档 → ⑤ 文档同步
     ↑___________________________________________________|
```

| 步骤 | 规范 | 落地机制 |
|---|---|---|
| ① 假设登记 | 实验前写下: 假设/预期方向/失败判据 | runs/config.json(含git_sha) |
| ② 实验执行 | LLM走缓存、模块顶层零I/O、open带encoding | `algorithms/llm_client.py` cache=True |
| ③ 统一评测 | 声明查询集+哈希校验+显著性检验(McNemar) | S*文件protocol.query_set_hash |
| ④ 结论归档 | 正结果入结果JSON; 负结果入负结果链(编号) | `runs/`(不覆盖写) + docs编号文档 |
| ⑤ 文档同步 | 数字变更必须同步docs+manifest | `python tools/build_data_manifest.py` |

### 硬性规则(违反=实验作废)

1. **哈希一致性**: 结果文件的query_set_hash必须与当前数据集重算一致
   (审计: `python tools/eval/hash_audit.py`, S4考古教训)
2. **显著性**: 任何"+X pt"结论必须附McNemar b/c/p
3. **混杂披露**: LLM生成查询须报overlap分布; 多gold须报gold集大小分布
   (分层: `python tools/eval/stratified_report.py`)
4. **负结果义务**: 预期方向失败也必须归档(负结果是资产, 见27号文档#7/#8链)
5. **评测集冻结**: 锁定数字的场景(v3=262q)不得修改查询, 新查询走新场景名(v4)

## 二、批次修复计划

### B1 评测效度修复(本批, 2026-10-14)
- [x] 哈希审计工具(系统性防S4式数据漂移)
- [x] 分层报告(overlap×gold-size×标识符型)
- [x] 人工标注包(50条×3问, κ协议)
- 退出判据: 全部S文件哈希PASS; 分层数字入results; 标注包可交付

### B2 条目聚合原型(挑战6, 方向A真正目标)
- 引用语法共指(正文"图3.1"↔图片锚点↔表引用)建边
- 位置邻接边 + 语义边(EMB_TH_LOCAL=0.78)
- 连通分量→条目; 需求ID共指做结构化gold代理
- 退出判据: 条目级P/R/Rand-index有首批数字

### B3 近重复形式化(挑战1)
- MinHash文档指纹 → 模板家族注册表(13-16)
- 家族作为分层变量进入全部评测
- 退出判据: 家族检测100%覆盖已知4文档, 无误报

### B4 语体鸿沟残余(挑战2)
- 前置: B1分层确认残余失败构成
- 候选: LLM查询改写(严格缓存协议)/列表重排/标识符硬约束
- 退出判据: 联合场景R@1≥0.55或负结果归档

## 三、产出物索引(本批新增)

| 文件 | 说明 |
|---|---|
| `tools/eval/hash_audit.py` | S*文件哈希审计 |
| `tools/eval/stratified_report.py` | 协变量分层报告 |
| `tools/eval/build_annotation_package.py` | 人工标注包生成 |
| `results/_stratified_report.json` | 分层数字(论文协变量表) |
| `V3/annotation_package_v1.json` | 50条标注包(待人工) |
