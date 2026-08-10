# UML用例图数据集调研报告（用于GJB SRS一致性检测项目补充）

> 调研日期：2026-08-10
> 目的：为场景1（"用例图 + capability表 + 正文"三模态配对）寻找格式匹配的网络数据集
> 搜索范围：arXiv、HuggingFace、GitHub、Kaggle、figshare、Semantic Scholar（部分限流）
> 验证标准：(1)真实存在 (2)可下载 (3)格式与"图+文本/表格"匹配

---

## 1. 结论速览

- **"用例图+自然语言"配对的公开数据集确实存在，但规模普遍很小**（百级条数），最大、最规范的公开"需求文本↔UML图"配对是 **PlantUCD（9546对，类图）** 和 **BESSER-Dataset（9000+模型，图+文本+元数据，类图）**。
- **用例图（Use Case）专用数据集稀缺**，网络上的大库几乎都是类图/时序图/活动图。最匹配用例图场景的是 2 个 HF 小数据集（vinzur 系）和 1 个结构化抽取数据集（Usecase-UML）。
- **与"一致性检测"范式最相关的是 MCeT**（Huawei-TTE，需求文本↔时序图 + 人工评分问题），可直接作为方向B方法设计的参考基准。
- 你提到的 **UML-Text / UMLExtractor / UML2Text / "Plausible UML"** 均验证为**工具或未公开数据集**（详见§5），无现成可下载数据。

---

## 2. 数据集清单（已验证）

### A类：用例图 / UML图 + 文本配对（最匹配场景1）

| # | 名称 | 来源/链接 | 规模 | 格式 | 下载验证 |
|---|------|----------|------|------|---------|
| A1 | **softw-desc-to-plantuml-usecase-diagram** | HF: `vinzur/softw-desc-to-plantuml-usecase-diagram` | 172条 | `{input: 系统自然语言描述, output: PlantUML用例图代码}` | ✅ 已下载parquet实测，0.1MB |
| A2 | **user-stories-to-plantuml-usecase-diagram** | HF: `vinzur/user-stories-to-plantuml-usecase-diagram` | 141条 | `{input: 用户故事, output: PlantUML用例图代码}` | ✅ 已实测，0.2MB |
| A3 | **plantuml_generation** | HF: `coai/plantuml_generation` | 1940条 | `{text: 指令格式，含Use Case Name/ID/描述→PlantUML图}` | ✅ 已实测，3.1MB |
| A4 | **PlantUCD**（需求↔类图） | GitHub: `FeisalAlaswad/PlantUCD-dataset-full`（TechRxiv 2026论文配套） | 9546对（train 8137 / test 1409） | `{NL需求, PlantUML类图}`，附类/属性/方法/关系统计 | ✅ 仓库14MB，MIT |
| A5 | **Usecase-UML** | HF: `ReshmaUMLGraphMaster/Usecase-UML` | 63条 | `{prompt: 场景文本, response: actor/action/relationships结构化}` | ✅ 已实测CSV |
| A6 | **SeqUC-Dataset**（时序图↔用例） | GitHub: `JakubMurin/SeqUC-Dataset` | 数百条 | `{seq/*.puml时序图, all.jsonl, usecase.xsd}` | ✅ 已列目录验证，11MB |
| A7 | **MCeT**（需求↔时序图+人工评分） | GitHub: `Huawei-TTE/MCeT`（arXiv 2508.00630） | 84组 | `{*.txt需求文本, *.puml时序图, *.score人工问题评分}` | ✅ 已列目录验证（85 txt/84 puml/84 score） |
| A8 | **UMLCode_UseCaseDiagram** v1/v2(+Scored) | HF: `nguyenvanviet/UMLCode_UseCaseDiagram_v1` 等 | 极小（1~数十条） | `{input, reasoning, uml_code}` | ✅ 已实测，仅示例级，价值低 |

### B类：UML图（类图为主）+ 文本/元数据（格式相似，可迁移）

| # | 名称 | 来源/链接 | 规模 | 格式 | 下载验证 |
|---|------|----------|------|------|---------|
| B1 | **BESSER-Dataset** | GitHub: `BESSER-PEARL/BESSER-Dataset` | 9000+模型（描述写5000+，仓库实际更多） | 每个模型含 `image.png` + `确定性文本描述` + `python_code` + `metadata.txt`（类/关联/属性/函数数）+ 标签 | ✅ 已列目录验证，5.3GB(7z压缩包) |
| B2 | **ModelSet**（BESSER的原始来源） | GitHub: `modelset/modelset-dataset`（models-lab.github.io 2021） | 2400+模型 | Ecore/UML模型 + 图 | ✅ LGPL-3.0 |
| B3 | **ClassDiagram_PlantUML_Text** | HF: `ThePeaceLovingGhost/ClassDiagram_PlantUML_Text` | 5000条 | `{messages: feature描述→PlantUML类图}` chat格式 | ✅ 已实测，17.3MB |
| B4 | **uml-nl-ocl-100** | HF: `fpan/uml-nl-ocl-100` | ~100条 | `{NL约束, PlantUML模型, OCL约束}`（源自Abukhalaf的models_dataset） | ✅ 已有描述，小规模 |
| B5 | **Prompt-to-PlantUML** | HF: `vinzur/Prompt-to-PlantUML` | 小 | prompt→PlantUML | ✅ 存在（同作者系列） |

### C类：UML/软件图图像识别与标注（方向4，图理解辅助）

| # | 名称 | 来源/链接 | 规模 | 格式 | 下载验证 |
|---|------|----------|------|------|---------|
| C1 | **Image diagram dataset** | figshare: `figshare.com/articles/dataset/Image_diagram_dataset/20399283` | 5981张，6类：None 1010 / 活动图 595 / 时序图 811 / 类图 986 / 组件图 368 / **用例图 854** / 云图 978 | `normalized_diagram_images.zip(56MB)` + `CSV标注` | ✅ figshare API验证可下载 |
| C2 | **CAS2UML**（手绘草图→PlantUML） | HF: `Seym0n/cas2uml_hand-drawn_to_plantuml_dataset`（arXiv 2608.07036） | 557张手绘（271类图+286活动图） | `{手绘图像, PlantUML代码}` + 验证工具 | ✅ 已实测 |
| C3 | **activity-diagrams-qdobr**（活动图元素检测） | HF: `Francesco/activity-diagrams-qdobr` | ~2万张（COCO格式） | 活动图元素 bounding box 检测 | ✅ 存在（QDOBR论文配套） |
| C4 | **UML class diagram dataset (bounded box + rating)** | Kaggle: `domenicoarm/uml-class-diagram-dataset-bounded-box-rating` | 未确认（数百张） | 类图 + bbox + 评分 | ⚠️ Kaggle需登录 |
| C5 | **Handwritten UML Class diagrams** | Kaggle: `leticiapiucco/handwritten-uml-class-diagrams` | 手写类图集 | 手写类图图像（类/关联/继承） | ⚠️ Kaggle需登录 |
| C6 | **ImageProcessing**（UML图符号提取） | GitHub: `jaculangithub/ImageProcessing` | 小 | UML图分类+符号提取脚本 | ✅ 存在 |

### D类：研究型/方法配套数据（参考价值>直接使用）

| # | 名称 | 说明 | 链接 |
|---|------|------|------|
| D1 | **Prior Bias in VLMs on UML Interpretation** | 受控UML benchmark：将类图关系箭头反转构造"先验冲突"对，测VLM是否真读图。**对方向B"区分合理差异vs真矛盾"有方法学参考** | arXiv 2607.02853（数据未见公开仓库） |
| D2 | **PyUNML-DataSet** | 用户故事→类图+用例的自动生成研究数据 | GitHub `matovaro/PyUNML-DataSet` |
| D3 | **textToUml**（2tolgahan2） | "Generating Domain Models from NL text: benchmark dataset"论文配套需求数据集 | GitHub `2tolgahan2/textToUml` |
| D4 | **uml2text**（hsu-aut） | 德国HSU测试LLM处理UML模型的文件集（德语系，未结构化） | GitHub `hsu-aut/uml2text` |
| D5 | **NOMAD** | 类图生成多Agent框架，评测用Northwind案例+人工UML练习题（数据未独立公开） | arXiv 2511.22409 |

---

## 3. 格式匹配度评估（对照场景1：用例图 + capability表 + 正文 三模态）

| 维度 | 最佳候选 | 匹配情况 |
|------|---------|---------|
| **用例图 ↔ 正文文字** | A1, A2, A3, A5 | ✅ 直接匹配（NL文本↔用例图PlantUML）——但中文SRS需翻译适配 |
| **图 ↔ 结构化表格/统计** | B1(BESSER metadata：类/属性/关联/函数数量表), B4(约束表格) | 🟡 有"图+统计表"但非"capability表"语义；**capability表（功能能力清单）在公开数据集中无直接对应** |
| **图 ↔ 需求规范文本（带ID/编号）** | A3（Use Case Name/ID/Description结构化输入） | ✅ 最接近GJB"用例图+用例描述"结构 |
| **图内元素识别/标注** | C1（854张用例图分类）, C3（元素检测）, C2（草图识别） | ✅ 可用于构建用例图元素级Gold Standard |
| **"一致性"标注数据** | A7 MCeT（图↔文本不一致问题人工标注） | ✅✅ 唯一带"图-文不一致人工标注"的公开数据 |

**总体判断**：网络公开数据能覆盖"用例图+文字"和"图+统计信息"两两配对，但**没有任何数据集天然含"用例图+capability表+正文"三模态**，也没有中文军事领域数据。可作为**预训练/评测/方法验证**的增强数据，三模态结构仍需在16份SRS内自建。

---

## 4. 推荐使用方案

**直接可用（无需改造，格式即图+文）**：
1. **A1+A2（vinzur用例图对）**：313条用例图↔文本，直接作为场景1的"图↔正文配对"增强/评测集（规模小，适合few-shot示例或评测而非训练）
2. **A3（coai/plantuml_generation）**：1940条，含Use Case ID/描述→图，最贴近GJB"用例描述"结构，可筛出用例图部分
3. **A7 MCeT**：84组带人工不一致标注的图-文对，直接用作方向B（一致性检测）的评测参考与prompt设计范本
4. **B1 BESSER-Dataset**：9000+组"图+确定性文本+元数据+代码"，做多模态配对（方向A）的规模实验和预训练材料（5.3GB，需7z解压；注意是类图）

**需要改造后使用**：
5. **A4 PlantUCD**（9546对）：类图版"需求↔图"，可改造成用例图/泛化到中文，或作为方向A聚合方法的规模验证集
6. **C1 figshare**（5981张含854张用例图）：做用例图图像分类/检索，验证"图↔章节定位"的图像侧能力
7. **C2 CAS2UML / C3 QDOBR**：手绘/活动图识别方法可迁移到用例图元素检测
8. **B3 ClassDiagram_PlantUML_Text**（5000条chat格式）：若后续做"需求→图生成"或"图→需求"的指令微调

**不建议用**：A8（仅1~数十条示例）、C4/C5（需Kaggle账号且为类图/手写图）、D4（未结构化）、D1（无公开数据）。

---

## 5. 已知工作验证结果

| 名称 | 验证结论 |
|------|---------|
| UML-Text | ❌ 未找到同名公开数据集；GitHub上`weidagang/text-diagram`、`matheusgr/modeligado`、`ZenUml`等均为**文本画图工具**，无配套数据集 |
| UMLExtractor | ❌ 仅有`shiyamalan/UmlExtractor`、`AlexanderSchultheiss/ArgoUMLExtractor`等**代码工具**，无数据集 |
| UML2Text | 🟡 仅`hsu-aut/uml2text`（D4）有少量测试文件，未结构化 |
| Plausible UML datasets | ❌ 未能在任何平台检索到该名称的数据集（可能指ModelSet/Abukhalaf models_dataset这类"从代码库挖掘UML模型"的工作） |
| 大学课程UML图集 | 🟡 存在（Creately/EdrawMax等模板库），但**无标注、无配对文本、不可批量下载**，不建议使用 |

---

## 6. 局限与说明

1. **用例图公开数据总量极小**（可用约500~2000条级），且全部为英文、非军事领域、以PlantUML代码而非渲染图为主——与GJB中文SRS存在模态差异。
2. "capability表"这类**功能能力清单表格**在公开数据中无对应，三模态配对必须靠自有16份SRS构建。
3. Kaggle 下载需登录账号；figshare、HF、GitHub 均可匿名下载（已验证）。
4. Semantic Scholar API 本次限流（429），部分论文元数据（如QDOBR原始论文）未能完整核对，但其数据集本体已在HF验证。
