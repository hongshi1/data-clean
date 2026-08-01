# SRS文档集合调研报告

> 调研日期: 2026-07-28
> 目标: 搜索学术机构和开源社区中的SRS文档**集合**(非单个示例),用于扩展一致性检测的数据基础

---

## 一、学术SRS数据集 (Academic Datasets)

### 1. PURE Dataset ★ 已有本地副本 (最重要)

| 字段 | 内容 |
|------|------|
| **Title** | PURE: A Dataset of Public Requirements Documents |
| **URL** | https://zenodo.org/record/7118517 (旧版 1414117) |
| **Source** | Ferrari, Spagnolo & Gnesi, IEEE RE 2017 |
| **文档数量** | 79份 (62 PDF + 13 DOC + 2 HTML + 1 RTF + 1 HTM) |
| **格式** | PDF/DOC/HTML/RTF + XML版 (requirements-xml.zip, 369KB) |
| **是否免费** | 是 (Zenodo开放获取) |
| **表格/图/约束** | 是 — 真实SRS文档,含表格、图、约束 |
| **质量** | 完整填充的真实SRS文档 |
| **大小** | ~32 MB (requirements.zip) |
| **本地路径** | `data/srs_requirements/req/` (79文件) |
| **预处理版** | https://github.com/MeMartijn/PurePlainDataset (纯文本转换) |

**关键词**: requirements classification, traceability, ambiguity detection, defect detection, model synthesis

---

### 2. Software Requirements Data Set ★ 推荐 (元集合,含PURE+3源)

| 字段 | 内容 |
|------|------|
| **Title** | Software Requirements Data Set |
| **URL** | https://zenodo.org/record/7897601 |
| **Source** | Zenodo (2023-05-04) |
| **文档数量** | 多份文档,来自4个来源 |
| **来源** | ① PURE ('P'前缀) ② Hayes et al. ('H'前缀, REW 2019) ③ Dalpiaz ('g'前缀, Inf.Softw.Techol.) ④ 互联网自建 ('C'前缀) |
| **格式** | 原始文件 (TXT/PDF/RTF/DOC/HTML) + 纯文本转换 (_Raw.txt) + Markdown (_Raw.md) + 功能需求提取 (FunctionalRequirements) |
| **是否免费** | 是 |
| **表格/图/约束** | 是 — 保留原始文件 |
| **质量** | 完整 — 含功能需求提取和规范相关部分提取 |
| **大小** | ~11.5 MB (Dataset.zip) |
| **用途** | 自动SRS处理和质量评估 |

**价值**: 这是PURE的超集,额外引入了Hayes、Dalpiaz和自建3个来源的需求数据。

---

### 3. tera-PROMISE Requirements Repository

| 字段 | 内容 |
|------|------|
| **Title** | tera-PROMISE Repository - Requirements Category |
| **URL** | https://openscience.us/repo/requirements/ |
| **Source** | N.C. State University, NSF支持 |
| **数据集数量** | 8个数据集 |
| **格式** | ARFF/XML/TXT (非完整SRS PDF,而是需求语句/用例) |
| **是否免费** | 是 |
| **质量** | 专业化数据集 (非完整SRS文档) |

**包含的数据集**:
| 数据集 | 说明 |
|--------|------|
| usecasedocs | 200+用例文档 (4个系统: 健康信息/自动导引车/应急监控/在线购物), ASE 2014, DOI:10.5281/zenodo.268452 |
| WASP | 自然语言需求变更影响分析 (NARCIA工具) |
| iStar 1 (small) | Softgoals .ood文件 |
| iStar 2 (large) | Softgoals .vsd文件 |
| nrpRealistic | Next Release Problem数据 |
| nrpClassic | Next Release Problem经典数据 |
| nfr | 非功能需求笔记 |
| modis | NASA MODIS需求追踪数据 (Hayes & Dekhtyar) |

---

### 4. Promise+ Dataset

| 字段 | 内容 |
|------|------|
| **Title** | Promise+: A dataset of labeled software requirements |
| **URL** | https://zenodo.org/records/12805484 |
| **Source** | Zenodo (2024-07-24) |
| **文档数量** | Promise_exp扩展版 |
| **格式** | 数据文件 (需求语句+专家分类标签) |
| **是否免费** | 是 |
| **质量** | 需求语句分类语料 (非完整SRS文档) |

---

### 5. RETRO.NET Dataset

| 字段 | 内容 |
|------|------|
| **Title** | The REquirements TRacing On target (RETRO).NET Dataset |
| **URL** | https://zenodo.org/record/1223649 |
| **文档数量** | 66条需求 (1份规范, 功能需求) |
| **格式** | ZIP |
| **是否免费** | 是 |
| **用途** | 需求到代码的追踪 |
| **质量** | 单一规范,规模小 |

---

### 6. Fault-prone SRS Dataset

| 字段 | 内容 |
|------|------|
| **Title** | Fault-proneSRSDataset |
| **URL** | https://github.com/ftnrjnnh-m/Fault-proneSRSDataset |
| **文档数量** | 3个CSV文件 (dataset.csv, featureboost.csv, finalrq.csv) |
| **格式** | CSV (非PDF文档) |
| **是否免费** | 是 |
| **质量** | SRS歧义/缺陷标注数据 (数据级,非文档级) |

---

## 二、开源需求管理工具示例 (Open-Source Tool Samples)

### 7. ReqView Example Documents ★ 推荐 (填充示例)

| 字段 | 内容 |
|------|------|
| **Title** | Example Requirements Specification Documents |
| **URL** | https://www.reqview.com/doc/example-requirements-documents/ |
| **示例数量** | 4份填充示例 |
| **格式** | ReqView格式 (可导出DOCX/PDF/HTML/ReqIF) |
| **是否免费** | 是 (在线可查看) |
| **表格/图/约束** | 是 |
| **质量** | 完整填充示例 |

**包含的示例**:
| 示例 | 基于标准 | 说明 |
|------|---------|------|
| Example SRS | ISO/IEC/IEEE 29148 | 软件需求规范示例 |
| User Stories | User Stories Template | 敏捷用户故事示例 |
| Library Loans SRS | Volere Process | 图书馆借阅系统SRS |
| Trip-R-You | Excel导入 | 航班预订系统需求 (Dan Tasker案例) |

---

### 8. ReqView Templates (模板,非填充)

| 字段 | 内容 |
|------|------|
| **Title** | Requirements Specification Templates |
| **URL** | https://www.reqview.com/doc/requirements-specification-templates/ |
| **模板数量** | 5个 |
| **模板** | ISO/IEC/IEEE 29148, OWASP ASVS, Volere, User Stories, FMEA |
| **质量** | 模板 (未填充) |

---

### 9. OMG ReqIF Standard

| 字段 | 内容 |
|------|------|
| **Title** | Requirements Interchange Format (ReqIF) 1.2 |
| **URL** | https://www.omg.org/spec/ReqIF/ |
| **格式** | 规范PDF + XML Schema (reqif.xsd) |
| **是否免费** | 是 (规范+模式) |
| **质量** | 标准规范,非示例文档 |
| **贡献方** | BMW, Bosch, Audi, Daimler, Volkswagen, IBM, Continental等 |

---

## 三、大学SRS示例 (University Examples — 单个,非集合)

> 以下为各大学课程/毕设中的SRS示例文档,均为单个文件,非集合。可作为补充测试样本。

| # | 来源 | URL | 格式 | 质量 |
|---|------|-----|------|------|
| 10 | Drexel University (Senior Design) | https://cci.drexel.edu/SeniorDesign/SampleFiles/WAVED_SRS_4-29.pdf | PDF | 填充 (WAVED环境数据可视化) |
| 11 | RIT Software Engineering | https://www.se.rit.edu/~sis-io/documents/RequirementsDocument.pdf | PDF | 填充 |
| 12 | WVU | https://community.wvu.edu/~hhammar/rts/SRS%20doc%20example/example-SRS.pdf | PDF | 填充 (DPU FSW) |
| 13 | Radford University | https://sites.radford.edu/~softeng18/Documents/requirements.pdf | PDF | 填充 (学生项目) |
| 14 | Radford University (另一份) | https://sites.radford.edu/~softeng16/software%20requirements%20doc%20Final.pdf | PDF | 填充 (学生项目) |
| 15 | University of Houston | https://www2.cs.uh.edu/~rsingh/documents/software_engineering/SRS_template.pdf | PDF | 模板 |
| 16 | Brooklyn CUNY | https://www.sci.brooklyn.cuny.edu/~meyer/CISC3140/projects/softwarespecificationtemplate.pdf | PDF | 模板 |

---

## 四、标准参考 (Standards Reference)

| # | 标准 | URL | 说明 |
|---|------|-----|------|
| 17 | IEEE 830 | http://www.math.uaa.alaska.edu/~afkjm/cs401/IEEE830.pdf | SRS推荐实践 (含示例大纲) |
| 18 | ISO/IEC/IEEE 29148:2018 | https://standards.ieee.org/standard/29148-2018.html | 系统和软件需求工程 (ReqView模板基于此) |

---

## 五、汇总与推荐

### 按文档集合规模排序

| 排名 | 数据集 | SRS文档数 | 格式 | 状态 |
|------|--------|----------|------|------|
| 1 | **PURE** | 79 | PDF/DOC/HTML/RTF | ✅ 已有本地 |
| 2 | **Software Requirements Data Set** | 多份 (4源,含PURE) | PDF/DOC/HTML/TXT/MD | ⬜ 待下载 (Zenodo 7897601) |
| 3 | usecasedocs (PROMISE) | 200+用例 | 用例文档 | ⬜ 待下载 |
| 4 | ReqView Examples | 4 | ReqView/可导出 | ⬜ 可在线查看 |
| 5 | Promise+ | 语句级 | CSV/数据 | ⬜ 非完整SRS |
| 6 | RETRO.NET | 1规范/66需求 | ZIP | ⬜ 规模小 |
| 7 | modis (NASA) | 1项目 | TXT/XLS | ⬜ 规模小 |
| 8 | Fault-prone SRS | 数据级 | CSV | ⬜ 非文档 |

### 优先行动建议

1. **下载 Software Requirements Data Set** (Zenodo 7897601) — PURE超集,额外含Hayes/Dalpiaz/自建3个来源,11.5MB
2. **下载 usecasedocs** (Zenodo 268452) — 200+用例,补充用例级数据
3. **导出 ReqView 4个示例** — 标准化格式 (ISO 29148/Volere),含表格约束
4. **收集大学SRS示例** (Drexel/RIT/WVU/Radford) — 作为额外测试样本

### 与GJB 438C项目的关联

- PURE和Software Requirements Data Set提供的是IEEE/ISO风格SRS,与GJB 438C格式不同
- 但可用于: ① 跨标准一致性检测方法验证 ② 约束提取方法泛化 ③ 表格/图解析能力测试
- GJB格式SRS仍需从公开GJB文档中获取 (项目已有3份)
