# 8场景 × 网络数据集匹配矩阵

> 日期: 2026-08-10
> 基于3个搜索agent的调研 + HuggingFace API真实验证
> 原则: 只匹配"模块一致"的数据集, 格式不匹配的不强行使用

---

## 一、逐场景匹配

| 场景 | 网络匹配数据集 | 匹配类型 | 验证 | 注意 |
|------|--------------|---------|------|------|
| **sc1** 用例图+capability表+正文 | `softw-desc-to-plantuml-usecase-diagram` (172条) + `user-stories-to-plantuml-usecase-diagram` (141条) | 用例图+文本 | ✅ HF可下载 | 英文, 无capability表, 只能做图-文 |
| **sc2** 流程图+usecase表+正文 | **MCeT** (Huawei, 84组需求+时序图+人工不一致评分) | 时序图+需求文本 | ✅ GitHub | 唯一带**图-文不一致人工标注**的公开数据 |
| **sc3** 接口图+interface表+正文 | ❌ 无匹配 | — | — | 接口图是GJB特有图型 |
| **sc4** 流程图+capability表+正文 | ❌ 无匹配 | — | — | 组合无公开数据 |
| **sc5** 功能图+capability表+正文 | ❌ 无匹配 | — | — | 功能图GJB特有 |
| **sc6** 功能框架图+其他表+正文 | ❌ 无匹配 | — | — | 功能框架图GJB特有 |
| **sc7** 用例图+usecase表+正文 | `coai/plantuml_generation` (1940条) + `CAS2UML` (557张) | 用例图+Use Case名/描述 | ✅ HF可下载 | 结构最接近GJB用例描述表 |
| **sc8** 纯图片+正文 | `OmniDocBench` (1651页中英) + `MMLongBench-Doc` (480+页) + `DocDownstream-1.0` (中文11任务) | 文档页级图文表 | ✅ HF可下载 | 可做图文一致性泛化 |

## 二、跨场景匹配（适用于多个场景的通用数据集）

| 类别 | 数据集 | 规模 | 用途 |
|------|--------|------|------|
| **图表+底层表+文字**(三模态) | VisText | 12441对 | 图+数据表+语义字幕 |
| | ChartQA | 21.6K图 | 图+底层表+QA |
| | ChartX | 3.6K图 | 图+数据表+QA |
| | DCQA | 50K文档 | 合成文档(图+表+正文) |
| **图-文一致性检测**(现成任务) | CHOCOLATE | 1187例 | 图+生成字幕+逐句事实错误标注 |
| | ChartCheck | 1.7K图/10.5K claims | 图+声明+support/refute |
| | SNLI-VE | 565K对 | 图+文本+entailment/contradiction |
| **表-文本一致性** | TabFact | 16K表/118K声明 | 表+声明+entailed/refuted |
| **RE需求不一致** | ETCS/CoffeeMachine conflicts | 小 | 需求对不一致标注 |
| | Synthline_defects | Zenodo | 需求缺陷类型标注 |
| **真实SRS+图** | EAsyAnon SRS×3 | 147-271张图/份 | 英文SRS+大量内嵌图 |

## 三、推荐使用方案（按价值排序）

### 方案1: MCeT（sc2匹配, 最高价值）
- **唯一带"图-文不一致人工标注"的公开数据**
- 84组需求+时序图+人工评分
- 用途: 方向B(不一致检测)的**跨领域验证集**——验证我们的检测器在"非GJB"图-文不一致上是否有效

### 方案2: PlantUML三件套（sc1/sc7匹配）
- `softw-desc-to-plantuml-usecase-diagram` + `user-stories-to-plantuml` + `plantuml_generation`(1940条)
- PlantUML源码可渲染成真实用例图PNG
- 用途: **图-文一致性**训练/评测（英文用例图, 无表）

### 方案3: CHOCOLATE + ChartCheck（图-文一致性检测任务）
- 现成的"图+字幕+事实错误标注"
- 用途: 方向B方法的**通用性验证**（不只是GJB领域）

### 方案4: VisText + ChartQA（图表+表+文三模态）
- 图+底层数据表+字幕——与我们"图+表+文"结构同构
- 用途: **三模态一致性检测**的方法验证（改表值/改字幕构造矛盾）

### 方案5: OmniDocBench + DocDownstream-1.0（sc8匹配, 中文）
- OmniDocBench含中文页, DocDownstream-1.0纯中文
- 用途: 中文多模态泛化验证

## 四、明确不用的

- ❌ PURE (无图无表, 已确认)
- ❌ FinBalance (数值一致性, 任务不匹配)
- ❌ ScholScan (仅2图5表, 样本不足)
- ❌ 接口图/功能图/功能框架图数据集 (GJB特有图型, 全网无对应)

## 五、结论

**能直接匹配的场景: sc1/sc7(用例图+文本), sc2(时序图+文本), sc8(文档图文)**
**不能匹配的场景: sc3/sc4/sc5/sc6 (GJB特有图型, 公开数据无对应)**

**最重要的发现**: MCeT是唯一带"图-文不一致人工标注"的数据——对我们的方向B(不一致检测)最有参考价值。其次CHOCOLATE/ChartCheck有现成的图-文事实错误标注。
