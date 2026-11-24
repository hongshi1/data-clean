# 94. 场景五开发进度跟踪模板（航天科工科研生产现场智能监管）

> **用途**: 项目进度跟踪与协作对齐, 由两位负责交互开发的同学分工填写
> **分工**: 陈同学 → 上下文关联(方向A) | 胡同学 → 一致性校验(方向B)
> **填写约定**: 标注 **【填写区】** 的表格/代码块由对应负责人填写; 其余为项目背景与参考资料(只读, 勿改)
> **更新频率建议**: 每完成一个子里程碑或每周更新一次; 阶段3为双方约定内容, 修改需同步通知对方

---

## 0. 项目阶段总览

| # | 阶段 | 核心交付物 | 负责人 | 状态 | 计划完成 | 实际完成 |
|---|---|---|---|---|---|---|
| 1 | 9个安全场景数据集确定 | 场景清单 + 图片数据集 | 双方共同 | 【填写】 | 【填写】 | 【填写】 |
| 2 | 数据预处理: QA对生成 | QA数据集(jsonl) + 生成流程说明 | 【填写】 | 【填写】 | 【填写】 | 【填写】 |
| 3 | 上下文关联输出格式对齐(双方约定) | 输入/输出契约文档(§3.2) | 双方约定 | 【填写】 | 【填写】 | 【填写】 |
| 4 | 上下文关联算法开发(切片数据+demo) | 切片数据集 + 算法demo | 陈同学 | 【填写】 | 【填写】 | 【填写】 |
| 5 | 一致性校验算法调研与开发 | 调研报告 + 校验算法demo | 胡同学 | 【填写】 | 【填写】 | 【填写】 |

> 状态填写约定: `未开始` / `进行中(xx%)` / `已完成` / `阻塞(原因见填写区)`

---

## 阶段1: 9个安全场景数据集确定

### 1.1 目标（只读）
确定场景五覆盖的9个安全监管场景, 为每个场景收集/确定原始图片数据。

### 1.2 参考起点（只读）
- 9个场景已定义: 安全帽佩戴 / 人员倾倒 / 防静电服穿戴 / 口罩佩戴 / 人员睡岗 / 抽烟检测 / 接打电话 / 通道占用 / 定员检测
- 已铺设40张真实图片: `deploy/nkuDataProject/frontend/images/kg/`(9张PPE安全帽实拍图 + 31张MOT人员图, 按场景逻辑命名)
- 场景定义与架构文档: `docs/srs_project/project_guide.md` §11.4

### 1.3 【陈同学填写区】

| 填写项 | 内容 |
|---|---|
| 数据集清单确认 | 【每场景图片数量/来源/标注情况】 |
| 场景补充或调整意见 | 【无 / 具体意见】 |
| 遇到的问题 | 【无 / 具体描述】 |
| 完成日期 | 【YYYY-MM-DD】 |

```text
# 每场景数据清单（可直接增删行）
# 场景名        | 图片数 | 来源      | 标注情况
安全帽佩戴      |        |           |
人员倾倒        |        |           |
防静电服穿戴    |        |           |
口罩佩戴        |        |           |
人员睡岗        |        |           |
抽烟检测        |        |           |
接打电话        |        |           |
通道占用        |        |           |
定员检测        |        |           |
```

### 1.4 【胡同学填写区】

| 填写项 | 内容 |
|---|---|
| 数据集清单确认 | 【每场景图片数量/来源/标注情况】 |
| 场景补充或调整意见 | 【无 / 具体意见】 |
| 遇到的问题 | 【无 / 具体描述】 |
| 完成日期 | 【YYYY-MM-DD】 |

```text
# 每场景数据清单（同上格式, 从校验算法视角关注: 声明可核验性）
# 场景名        | 图片数 | 可核验声明类型
安全帽佩戴      |        |               |
...
```

---

## 阶段2: 数据预处理 — QA对生成

### 2.1 目标（只读）
使用 easydataset 或其他LLM工具, 基于原始图片生成 问答对(QA pair)数据集, 作为两个算法的共同输入。

### 2.2 参考起点（只读）
- 已有44条QA对: `deploy/nkuDataProject/data/kg_supervision/qa_dataset.jsonl`
- 数据格式(每行一条):
  ```json
  {"conversations": [
      {"from": "user", "value": "判断图片中是否有人员未佩戴安全帽"},
      {"from": "gpt", "value": "{\"task\": \"安全帽检测\", \"answer\": 1, \"evidence\": [\"画面中右侧人员未佩戴安全帽\"]}"}],
   "image": "ppe_001.jpg"}
  ```
  其中 answer: 1=存在违规/是, 0=全部正常/否, 2=无法判定

### 2.3 【填写区 · 负责人: 【填写】】

| 填写项 | 内容 |
|---|---|
| 负责人 | 【填写】 |
| 生成工具 | 【easydataset / 其他LLM(注明模型)】 |
| 生成流程说明 | 【简述: prompt设计→生成→后处理】 |
| 数据规模 | 【总N条, 每场景分布】 |
| 质检方式 | 【人工抽检xx% / 一致性校验规则】 |
| 输出文件位置 | 【路径; 如沿用参考格式请注明"沿用"】 |
| 数据集划分 | 【训练/评测划分, 如无写"不涉及"】 |
| 遇到的问题 | 【无 / 具体描述】 |
| 完成日期 | 【YYYY-MM-DD】 |

```text
# QA对生成流程（关键步骤记录, 便于复现）
1. 【步骤: prompt模板设计...】
2. 【步骤: LLM调用与参数...】
3. 【步骤: 后处理/过滤规则...】
4. 【步骤: 质检与修正...】
```

---

## 阶段3: 双方约定 — 上下文关联输出格式对齐

### 3.1 目标（只读）
**两位同学共同确认方向A(上下文关联)的输出契约, 保证方向A的输出可直接作为方向B(一致性校验)的输入。** 这是两个算法的接口里程碑。

### 3.2 讨论起点（理想契约草案, 只读, 供讨论）

方向A(上下文关联+召回)的理想输出 — **多模态上下文条目**:
```json
[
  {
    "image": "ppe_001.jpg",
    "constraints": {
      "entity_types": ["person", "helmet"],
      "spatial": "right",
      "attributes": ["not_wearing"],
      "count": 2,
      "temporal": false
    },
    "chunks": [
      {"chunk": "人员#3", "bbox": [461.1, 213.1, 563.0, 403.5],
       "conf": 0.686, "score": 0.93,
       "reasons": ["类型匹配:person", "空间约束:右侧(x=90%)"]}
    ],
    "qa_context": ["QA#5", "QA#7"],
    "entities": ["人员", "安全帽"]
  }
]
```

方向B(一致性校验)的理想输入/输出:
```json
{
  "input":  {"claim": "声明文本",
             "evidence": ["方向A输出的接地切片+属性观测"],
             "context": ["关联QA"]},
  "output": {"verdict": "support|refute|NIE",
             "nie_reason": "temporal|missing_observation|ambiguous|null",
             "facts": [{"claim": "...", "grounded": "...", "observation": "...",
                        "fact_verdict": "...", "reason": "..."}],
             "confidence": 0.0}
}
```

### 3.3 【双方共同填写区 — 需两人确认】

| 约定项 | 双方约定结果 | 陈同学确认 | 胡同学确认 |
|---|---|---|---|
| 方向A最终输出格式 | 【见下方JSON, 或"沿用§3.2草案"】 | 【姓名+日期】 | 【姓名+日期】 |
| 方向B消费的字段 | 【方向A输出中哪些字段被校验使用】 | 【确认】 | 【确认】 |
| bbox坐标系约定 | 【像素xyxy / 百分比xywh】 | 【确认】 | 【确认】 |
| 接地失败表示方式 | 【字段缺失 / null / "未接地"标记】 | 【确认】 | 【确认】 |
| 三态与NIE原因标签口径 | 【support/refute/NIE + 原因标签清单】 | 【确认】 | 【确认】 |
| 约定日期 | 【YYYY-MM-DD】 | — | — |

```json
// 最终约定的方向A输出格式（双方共同编辑此代码块; 沿用草案则写"沿用§3.2草案, 无修改"）
{
  "【在此填写最终契约】": ""
}
```

```text
# 接口联调记录（每次双方对齐后追加一行）
# 日期       | 对齐内容              | 结论
YYYY-MM-DD  | 【如: bbox坐标系确认】 | 【通过/需修改】
```

---

## 阶段4: 上下文关联算法开发(切片数据 + 算法demo)

### 4.1 目标（只读）
基于QA对与原始图片, 开发上下文关联算法: 制作与组织处理**切片数据**(视觉Chunk), 开发算法demo。

### 4.2 参考起点（只读）
- 真实CV切片数据已生成: `deploy/nkuDataProject/data/kg_supervision/visual_chunks_real.json`
  (40图, YOLO人员检测+安全hat检测+姿态代理, 含bbox/置信度/佩戴状态; 生成脚本 `tools/kg_build_real_chunks.py`)
- 约束解析召回demo已实现: `deploy/nkuDataProject/backend/scenarios/kg_supervision/constraint_recall.py`
  (parse_constraints: 问题→{实体/空间/属性/计数/时序}约束; recall_chunks: 切片过滤排序+可解释reasons; API: POST /api/kg_supervision/recall_chunks)
- 设计文档: `docs/srs_project/93_scenario5_recall_paradigm_and_algorithm_design.md`(§3 约束解析召回)
- 核心认知: 召回本质 = question↔image固定关联 + **图内切片召回**(grounding), 非全库检索

### 4.3 【陈同学填写区】

| 填写项 | 内容 |
|---|---|
| 切片数据制作 | 【预处理流程/模型选择/切片粒度, 详见下方代码块】 |
| 算法设计概述 | 【方法概述/与约束解析召回demo的差异或改进】 |
| demo位置与运行方式 | 【文件路径 + 运行命令】 |
| 输出符合阶段3约定 | 【符合 / 偏差说明】 |
| 当前进度 | 【里程碑: 切片数据完成 / demo可跑通 / 接口联调通过】 |
| 遇到的问题 | 【无 / 具体描述】 |
| 需要的支持 | 【含需胡同学配合的接口问题】 |
| 下一步计划 | 【带时间点】 |

```text
# 切片数据制作流程（可复现的关键步骤）
1. 【输入: 原始图片...】
2. 【处理: 检测模型/切分策略...】
3. 【输出: 切片数据格式与位置...】
```

```text
# 算法设计要点（方法/流程/创新点, 可附设计文档链接）
- 方法:
- 输入输出:
- 与参考demo的差异:
```

---

## 阶段5: 一致性校验算法调研与开发

### 5.1 目标（只读）
基于方向A的算法demo(切片数据+召回结果), 开展一致性校验算法的调研与开发。

### 5.2 参考起点（只读）
- 声明分解-接地-校验demo已实现: `deploy/nkuDataProject/backend/scenarios/kg_supervision/claim_verify.py`
  (decompose_claim: 声明→原子声明; ground_claims: 接地到切片; verify_qa: per-fact三态校验+NIE原因)
- NLI残差层已实现: `deploy/nkuDataProject/backend/scenarios/kg_supervision/nli_residual.py`
  (Erlangshen-330M视觉蕴含回退, 标签映射0=CONTRADICTION/1=NEUTRAL/2=ENTAILMENT)
- 级联实证(44条QA基线): L1规则层 12 refute/3 support/29 NIE; L2 NLI残差 27 refute/3 support/14 NIE
  (关键发现: NLI完全确认规则层全部12条refute, NIE收窄29→14)
- API: POST /api/kg_supervision/verify_qa(qa_id→证据链), GET /api/kg_supervision/verify_dataset
- 设计文档: `docs/srs_project/93_scenario5_recall_paradigm_and_algorithm_design.md`(§4 分解-接地-校验)
- 相关调研文档: 88(声明分解文献) / 89(NLI归因) / 90(声明抽取SOTA) / 91(聚合codesign)

### 5.3 【胡同学填写区】

| 填写项 | 内容 |
|---|---|
| 调研工作 | 【文献综述/方法对比/选型结论, 详见下方代码块】 |
| 算法设计概述 | 【方法概述/与声明分解-接地-校验demo的差异或改进】 |
| demo位置与运行方式 | 【文件路径 + 运行命令】 |
| 输入符合阶段3约定 | 【消费方向A哪些输出 / 偏差说明】 |
| 当前进度 | 【里程碑: 调研完成 / 算法设计完成 / demo可跑通 / 联调通过】 |
| 遇到的问题 | 【无 / 具体描述】 |
| 需要的支持 | 【含需陈同学配合的接口问题】 |
| 下一步计划 | 【带时间点】 |

```text
# 调研综述（文献清单/方法对比/选型结论; 详细内容可另附文档并在此给链接）
## 关键文献
- 【文献1: 标题/方法/与本任务的关联】
- 【文献2: ...】
## 方法对比
【规则式 / NLI式 / 级联式 的优劣对比结论】
## 选型结论
【最终采用的方法及理由】
```

```text
# 算法设计要点（方法/流程/三态语义, 可附设计文档链接）
- 方法:
- 输入输出:
- 三态与NIE原因学:
- 与参考demo的差异:
```

---

## 附录A: 现有资产索引（只读）

| 类别 | 资产 | 位置 |
|---|---|---|
| QA数据 | 44条问答对 | `deploy/nkuDataProject/data/kg_supervision/qa_dataset.jsonl` |
| 图片 | 40张真实图片 | `deploy/nkuDataProject/frontend/images/kg/` |
| 切片数据 | 真实CV检测(YOLO) | `deploy/nkuDataProject/data/kg_supervision/visual_chunks_real.json` |
| 切片生成脚本 | 批量CV管线 | `tools/kg_build_real_chunks.py` |
| 方向A demo | 约束解析召回 | `deploy/nkuDataProject/backend/scenarios/kg_supervision/constraint_recall.py` |
| 方向B demo | 声明分解校验 | `deploy/nkuDataProject/backend/scenarios/kg_supervision/claim_verify.py` |
| L2残差 | NLI回退层 | `deploy/nkuDataProject/backend/scenarios/kg_supervision/nli_residual.py` |
| 后端API | recall/verify/crop/real_chunks | `deploy/nkuDataProject/backend/app.py` |
| 前端 | 约束面板+per-fact证据链 | `deploy/nkuDataProject/frontend/js/consist/kg_supervision.js` |
| 设计文档 | 召回范式与算法设计 | `docs/srs_project/93_scenario5_recall_paradigm_and_algorithm_design.md` |
| 测试 | 58个(全过) | `tests/test_{constraint_recall,claim_verify,verify_api,kg_graph_api,residual_nli,ner_service}.py` |

## 附录B: 填写说明（只读）

1. **【填写区】**的表格按行填写, 不适用的项写"不涉及"; 代码块内【】占位符替换为实际内容
2. 阶段3为**双方约定内容**, 表格需两人各自确认(姓名+日期), 修改需同步通知对方并追加联调记录
3. 引用外部文档/代码请给相对路径; 涉及运行方式的请写清命令
4. 进度建议用里程碑描述("切片数据完成/算法demo可跑通/接口联调通过")而非纯百分比
5. 阶段总览表(§0)的状态列在每阶段完成后同步更新
