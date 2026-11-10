# 84 架构审计：路由/分解/线性化的门控性验证（2026-11-10）

> 回应架构质疑："问题路由是不是要召回/猜答案？不路由是否可行？
> 阶段1-3是否可合并？" 用代码审计+消融实验回答。

## 1. 审计方法

对 `route_question`（43条关键词规则→check-item候选）做了**全链路
消费者追踪 + 空路由消融**：patch所有import点（qa_module/
answer_claims/deq_pipeline/qa_router）使路由恒返回空元组，重跑
91QA fast档全量评测。

## 2. 证据

**消融结果（tools/ablate_routing.py）**：

| 配置 | acc | macroF1 | 预测差异 |
|------|-----|---------|---------|
| 路由正常 | 0.9121 | 0.7212 | — |
| 路由恒空 | 0.9121 | 0.7212 | **0/91** |

**消费者追踪（rg全量）**：

| 消费者 | 性质 | 默认路径激活？ |
|--------|------|--------------|
| `ClaimResult.check_item_candidates` 标签 | 追溯元数据（40项taxonomy对齐） | 是（无害） |
| `no_check_item_candidate` 诊断 | 诊断信息 | 是（无害） |
| `decompose_claims` 裸数值主语补全 | 二级启发式（answer仅一个数字时从question补主语） | 是（消融证明91QA零依赖） |
| DEQ管线 E1证据评分 | 真实门控 | **否**（use_deq默认False，全部公开评测未启用） |
| EGT合成数据标签 | 训练数据生成 | 否（离线） |

**typed通道自检守卫**（claim类型分派的软化证据）：`verify_numeric`
对无法解析数值/单位的claim返回unresolved（落L2残差），不产生错误
verdict——类型错分的代价是多一次残差判定，不是错误判定。同理
enum/identifier/quoted通道各有守卫。

**专家注册表**：9个L0/L1专家的执行不咨询路由（各自CHECK_ITEMS
常量仅作结果标签）——**全量并行检测本来就是实际行为**。

## 3. 结论与架构修正

**route_question不是召回、不是猜答案、不是门控——是追溯标注器。**
真正的证据召回在评测边界之外（frozen evidence；召回子系统见
algorithms/blackboard/hybrid_recall.py，五通道+RRF/级联融合，未接入
本评测链）。

**修正后的架构表述**（阶段表合并，路由出关键路径）：

```
输入规约层   (Q, A, E) → (原子claims, 字段statements)      [原阶段1/2/3]
             ├ claim分解：切分+类型分派（软提示, 通道自检守卫兜底）
             └ 证据线性化：表格→行级定位语句（确定性投影）
全量检测层   typed claim通道(自检守卫) ∥ 9个L0/L1专家 —— 无路由门控,
             并行全跑, 失败显式上报
残差裁决层   L2 NLI 只判 L0/L1 未解决的claims（C1残差原则;
             实例已有refute则整例短路）
融合聚合层   per-claim fusion(决断>未决) + strict∀(refute>NIE>support)
后置标注     check-item追溯标签（非门控; 消融0差异）+ 诊断
[评测边界外] 证据召回前端（hybrid_recall, 待接入）
```

## 4. 处理决策

1. **代码不动**：route_question保留为标注器（violation evalset的
   taxonomy_ref对齐、DEQ opt-in、EGT标签都消费它）；删除需改43处
   调用签名，收益仅-0.16ms，风险不成比例。
2. **表述修正**：论文/文档的阶段表按上表重述；"问题路由"从阶段名
   改为"check-item追溯标注（非门控）"。
3. **披露补充**（81号文档同步）：路由非门控声明+消融证据+类型分派
   软提示性（守卫兜底）——把"看起来是启发式门控"的误读风险从论文
   审稿人视角提前消解。
4. **遗留耦合点**（记录不处理）：decompose_claims的裸数值主语补全
   是路由→分解的唯一真实耦合，消融证明91QA零依赖；若未来清理，
   将其改为无条件主语补全即可彻底解耦。
