# 电力/能源领域 SCADA时序 + 故障/报警/巡检文本 数据集搜索报告

搜索范围: GitHub + HuggingFace + iTrust/UNSW等官方源
搜索时间: 2026-07-12

---

## 一、总览: 哪些数据集真正有"时序+文本"天然配对?

| 数据集 | 领域 | 时序数据 | 文本配对 | 配对质量 | 下载难度 |
|--------|------|----------|----------|----------|----------|
| **tep_alarms_text** | 化工(TEP) | TEP传感器(需另取) | 报警描述文本(每条) | ★★★★★ 天然配对 | GitHub直接下载 |
| **CARE to Compare** | 风电 | SCADA 10min数据 | 故障标签+传感器描述 | ★★★★ 有文本标注 | HF/Zenodo直接下载 |
| **lkev/wtphm** | 风电 | SCADA+事件库格式 | 报警描述(代码+文本) | ★★★★ 定义了配对格式 | 库本身(数据另需) |
| **HAI** | 电力(汽轮/水电) | 传感器1Hz | 攻击标签(无详细文本) | ★★ 仅二值标签 | GitHub LFS/Kaggle |
| **TON-IoT** | IoT/IIoT | 遥测时序 | 安全事件+时间戳 | ★★ 攻击类型标签 | SharePoint |
| **SWaT** | 水处理 | 传感器51个 | 41攻击PDF描述 | ★★ 攻击在PDF中 | 需向iTrust申请 |
| **WADI** | 水分配 | 传感器 | 攻击描述文档 | ★★ 攻击在文档中 | 需向iTrust申请 |
| **BATADAL** | 水分配 | 传感器时序 | 二值攻击标签 | ★ 仅二值标签 | GitHub/iTrust |
| **EPIC** | 电力 | 电网传感器 | 攻击描述 | ★★ 需确认 | 需向iTrust申请 |
| **TEP (mv-per)** | 化工 | 41变量时序 | 21故障类型描述 | ★★★ 故障名+描述 | GitHub直接下载 |
| **DGA变压器** | 变压器 | 气体含量时序 | 8种故障类型 | ★★ 故障类型标签 | GitHub/CSDN |

---

## 二、详细数据集信息

### ★★★★★ 第1梯队: 确认有"时序+文本"天然配对

---

### 1. TEP Alarm Text Dataset (最匹配!)

| 项目 | 内容 |
|------|------|
| **仓库** | `andreenko-repo/tep_alarms_text` |
| **GitHub** | https://github.com/andreenko-repo/tep_alarms_text |
| **星数** | 2 stars |
| **HF Space** | https://huggingface.co/spaces/AntonAndreenko/tep_alarms_viewer |
| **数据来源** | Tennessee Eastman Process (TEP) 仿真 + IEEE Dataport报警管理数据集 |
| **下载方式** | GitHub直接克隆, CSV文件在 `data/text_alarms_original/` 目录 |
| **数据规模** | 100+ CSV文件, 每个200KB-1MB, 3个版本(Original/Filtered/Deadband) |
| **License** | 开源 |

**CSV列结构 (每条报警都有文本描述):**
```
,timestamp,tag,type,description
0,2024-05-01 00:00:20,FIR123,L,FLW COND CW LOW ALM
1,2024-05-01 00:00:30,FIR123,L NR,FLW COND CW LOW ALM RECOVERED
2,2024-05-01 00:02:00,FIR123,L,FLW COND CW LOW ALM
...
```

- `timestamp`: 报警时间戳
- `tag`: 触发报警的标签名(如FIR123)
- `type`: 报警类型(LL/L/H/HH + NR恢复)
- `description`: **报警文本描述** (如"FLW COND CW LOW ALM" = 冷凝水流量低报警)

**配对方式:** TEP传感器时序数据可从 `mv-per/tennessee-eastman-dataset` 获取, 按时间戳与报警文本配对。

**评价:** 这是目前找到的**最接近"SCADA时序+报警文本天然配对"**的数据集。报警文本是操作员控制台上显示的真实描述, 且有恢复消息配对。虽然来自仿真, 但TEP是业界标准benchmark。

---

### 2. CARE to Compare: Wind Turbine Anomaly Detection Dataset

| 项目 | 内容 |
|------|------|
| **HF数据集** | `kevykibbz/wind-turbine-scada-data-for-early-fault-detection` |
| **HF链接** | https://huggingface.co/datasets/kevykibbz/wind-turbine-scada-data-for-early-fault-detection |
| **原始来源** | Zenodo: https://zenodo.org/doi/10.5281/zenodo.10958774 |
| **Fordatis** | http://dx.doi.org/10.24406/fordatis/343 |
| **HF点赞** | 6 likes, 54 downloads |
| **论文** | arXiv:2404.10320 (Glück et al., 2024) |
| **下载方式** | HuggingFace直接下载 / Zenodo / Fordatis |
| **License** | CC BY-SA 4.0 |

**数据规模:**
- 89年累计运行数据
- 36台风机, 3个风电场(A/B/C)
- 95个数据集 (44个含故障标注, 51个正常)
- 10分钟SCADA采样间隔
- 特征数: Farm A=86, Farm B=257, Farm C=957
- 每个数据集: 1年训练数据 + 4-98天预测数据

**文本配对情况:**
- ✓ "Detailed fault information" — 最全面的风电故障公开数据集
- ✓ "Status-based labels" — 基于状态的标签
- ✓ "Labeled anomaly events" — 44个标注的故障时间段
- ✓ "Comprehensive sensor descriptions" — 所有变量的单位+描述文本
- HF标签包含 `modality:text` + `modality:tabular`

**评价:** 这是风电领域最大规模的SCADA+故障标注数据集, 来自真实风电场。有传感器描述文本和故障标注。但故障描述的详细程度(是纯时间戳标签还是文本描述)需下载后确认。

---

### 3. lkev/wtphm: Wind Turbine PHM Library

| 项目 | 内容 |
|------|------|
| **仓库** | `lkev/wtphm` |
| **GitHub** | https://github.com/lkev/wtphm |
| **星数** | 87 stars (风电SCADA领域最高) |
| **安装** | `pip install wtphm` |
| **License** | GPL-3.0 |

**这不是数据集, 而是处理库**, 但它定义了风电SCADA+报警文本配对的标准数据格式:

**事件/报警数据格式 (Event Data):**
- `turbine_num`: 风机编号
- `code`: 事件代码
- `description`: **事件文本描述** (如"Pitch system fault", "Grid-related event")
- `time_on`: 事件开始时间
- `stop_cat`: 停机类别(功能位置, 如变桨系统/齿轮箱/电网)

**SCADA数据格式:**
- `turbine_num`, `time` (10分钟), 功率/风速/温度等

**评价:** 这个库证明了风电领域确实存在"SCADA时序+报警文本描述"的天然配对数据。库本身不含数据, 但定义了如何将报警文本与SCADA时序对齐的方法。使用此库的研究者拥有此类配对数据。

---

### ★★★ 第2梯队: 有时序+故障/攻击标注, 但文本描述有限

---

### 4. HAI Security Dataset

| 项目 | 内容 |
|------|------|
| **仓库** | `icsdataset/hai` |
| **GitHub** | https://github.com/icsdataset/hai |
| **星数** | 177 stars |
| **Kaggle** | https://www.kaggle.com/datasets/icsdataset/hai-security-dataset |
| **机构** | ETRI附属研究所, 韩国 |
| **下载方式** | GitHub (Git LFS) / Kaggle |
| **License** | CC BY-SA 4.0 |

**数据规模:**
- 多版本: HAI 20.07 / 21.03 / 22.04 / 23.05 / HAIEnd 23.05
- 78-86个传感器点, 1Hz采样
- HAI 22.04: 6个训练集(279小时) + 4个测试集(100小时), 58次攻击
- HAI 23.05: 249小时正常 + 79小时攻击, 52次攻击
- CSV格式, 每个文件50MB+

**测试床组成 (电力领域!):**
- P1: 锅炉过程 (Emerson Ovation DCS)
- P2: 汽轮机过程 (GE Mark VIe DCS)
- P3: 水处理过程 (Siemens S7-300 PLC)
- P4: HIL仿真 (蒸汽轮机发电 + 抽水蓄能水电)

**文本配对情况:**
- ✗ 无详细攻击文本描述
- ✓ 有攻击时间标签(起止时间)
- ✓ summary目录有攻击统计信息
- 攻击标签为二值(正常/异常), 攻击类型在论文中描述

**评价:** HAI是电力领域(汽轮机+水电)最好的ICS安全数据集, 数据量大, 有攻击标注。但缺少攻击的文本描述, 仅有时间戳标签。

---

### 5. TON-IoT Datasets

| 项目 | 内容 |
|------|------|
| **机构** | UNSW Canberra, 澳大利亚 |
| **官方页面** | https://research.unsw.edu.au/projects/toniot-datasets |
| **下载** | SharePoint: https://unsw-my.sharepoint.com/:f:/g/personal/z5025758_ad_unsw_edu_au/EvBTaetotpdGnW7rJQ8fCvYBh8063CNeY9W33MpRsarJaQ?e=yZlnxW |
| **HF镜像** | `codymlewis/TON_IoT_network` (网络数据, 163 downloads) |
| **GitHub分析代码** | `Nour-Moustafa/TON_IoT-Network-dataset` (9 stars) |
| **License** | 免费(学术), 商用需授权 |

**数据组成:**
1. **IoT/IIoT遥测数据**: 10+传感器(气象/Modbus), log+CSV格式 ← 时序
2. **网络数据**: pcap + ZEEK日志 + CSV
3. **Linux数据**: atop日志 (TXT+CSV)
4. **Windows数据**: 性能监视器 (CSV)

**关键目录:**
- `SecurityEvents_GroundTruth_datasets`: 安全事件+时间戳 ← 攻击标签
- `Description_stats_datasets`: 特征描述+统计
- `Train_Test_datasets`: 训练测试集

**文本配对情况:**
- ✓ 遥测时序数据 + 安全事件时间戳
- ✓ 攻击类型标签 (DoS, DDoS, 勒索软件等)
- ✗ 无详细的自然语言攻击描述文本
- 日志文件(log/TXT)可能包含部分文本信息

**评价:** TON-IoT有遥测+日志配对, 但日志主要是系统日志, 不是故障/报警的自然语言描述。

---

### 6. SWaT (Secure Water Treatment)

| 项目 | 内容 |
|------|------|
| **机构** | iTrust, SUTD, 新加坡 |
| **官方页面** | https://www.sutd.edu.sg/itrust/itrust-labs/datasets/ |
| **下载方式** | 需向iTrust申请: https://www.sutd.edu.sg/itrust/request-for-datasets/ |
| **GitHub预处理工具** | `cbhua/swat-preprocess` (66 stars) |

**数据规模:**
- 11天连续运行: 7天正常 + 4天攻击
- 51个传感器和执行器
- 网络流量 + Historian数据(CSV)
- 41次攻击, 在PDF中描述

**文本配对情况:**
- ✓ 41次攻击在PDF文档中有描述
- ✓ 数据按正常/异常标注
- ✗ 攻击描述在独立PDF中, 未与时间序列inline配对
- ✗ 需要申请, 不能直接下载

**评价:** SWaT是CPS安全领域最常用的benchmark, 但攻击描述在PDF中, 不是与数据天然配对的文本字段。且需要申请。

---

### 7. WADI (Water Distribution)

| 项目 | 内容 |
|------|------|
| **机构** | iTrust, SUTD |
| **下载方式** | 需向iTrust申请 |
| **数据** | 水分配网络, 类似SWaT但规模更大 |

**文本配对情况:** 与SWaT类似, 攻击描述在文档中, 不是inline文本。

---

### 8. BATADAL

| 项目 | 内容 |
|------|------|
| **机构** | iTrust, SUTD |
| **GitHub调研** | `SYChen123/A-survey-on-BATADAL-dataset` (4 stars) |
| **下载** | 部分版本在GitHub, 完整版需iTrust申请 |

**数据规模:**
- 水分配网络时序数据
- 二值攻击标签(正常/攻击)

**文本配对情况:**
- ✗ 仅有二值攻击标签
- 攻击描述在竞赛文档中

**评价:** BATADAL只有二值标签, 无文本描述, 不满足"时序+文本配对"需求。

---

### 9. EPIC (Electric Power and Intelligent Control)

| 项目 | 内容 |
|------|------|
| **机构** | iTrust, SUTD |
| **下载方式** | 需向iTrust申请 |

**这是iTrust的电力测试床数据集!** 但信息较少, 需要申请后才能确认数据详情。

---

### 10. Tennessee Eastman Process Dataset (mv-per)

| 项目 | 内容 |
|------|------|
| **仓库** | `mv-per/tennessee-eastman-dataset` |
| **GitHub** | https://github.com/mv-per/tennessee-eastman-dataset |
| **星数** | 15 stars |
| **下载方式** | GitHub直接下载 (xlsx文件) |
| **License** | 见LICENSE |

**数据规模:**
- 3种运行模式 (Mode 1/3/4)
- 21种故障类型, 每种5个batch
- 41个过程变量 + 操作变量
- 正常: 50-500小时; 故障: 21类×5批次

**21种故障的文本描述:**
1. A/C feed ratio, B composition constant (Stream 4)
2. B composition, A/C ratio constant (Stream 4)
3. D feed temperature (Stream 2)
4. Reactor cooling water inlet temperature
5. Condenser cooling water inlet temperature
6. A feed loss (Stream 1)
7. C header pressure loss-reduced availability
...
21. The valve for Stream 4 was fixed at the steady state position

**文本配对情况:**
- ✓ 21种故障类型有文本描述
- ✓ 时序数据(温度/压力/流量等)
- 但故障描述是固定的21种类别标签, 不是逐条文本

**评价:** 可与 `tep_alarms_text` 配合使用: TEP时序数据 + TEP报警文本, 形成完整的"时序+文本"配对。

---

### 11. 其他相关数据集

#### DGA变压器故障诊断数据集
| 项目 | 内容 |
|------|------|
| **仓库** | `QQ767172261/How-to-apply-transformer-DGA-oil-chromatography-dataset-and-transformer-fault-diagnosis-case-dataset` |
| **星数** | 1 star |
| **数据** | 110kV-500kV变压器DGA油色谱, 8种故障状态 |
| **下载** | GitHub (CSDN链接) |
| **文本** | 中文故障描述, 气体含量时序 |

#### QUT S7comm SCADA攻击数据集
| 项目 | 内容 |
|------|------|
| **仓库** | `qut-infosec/2017QUT_S7comm` |
| **星数** | 20 stars |
| **数据** | SCADA网络攻击 + 过程日志 (LogsAttack/LogsControl) |
| **下载** | GitHub |
| **文本** | 网络日志(Snort规则), 非自然语言故障描述 |

#### Wind Turbine Gearbox 5-Year SCADA
| 项目 | 内容 |
|------|------|
| **HF** | `jason1966/aiwithcagri_wind-turbine-gearbox-anomaly-detection-5year-scada` |
| **数据** | 5年风机齿轮箱SCADA, 525,600样本 |
| **文本** | ✗ 仅有 `is_anomaly` 二值标签 |

#### Vestas V52 SCADA Synthetic
| 项目 | 内容 |
|------|------|
| **HF** | `vossmoos/vestasv52-scada-windturbine-granada` |
| **数据** | 合成数据, 40,000条, 24参数 |
| **场景** | 正常/功率调节/齿轮箱磨损/偏航退化 |
| **文本** | ✗ 场景标签, 无详细文本描述 |

#### PMU Power System Event Dataset
| 项目 | 内容 |
|------|------|
| **仓库** | `AsifKabir71/PMU-Dataset-for-Power-System-Event-Detection` |
| **星数** | 0 stars |
| **数据** | IEEE 14-bus + 孟加拉国电网仿真PMU数据 |
| **文本** | ✗ 仅有异常标签 |

---

## 三、特定数据集验证结果

### SWAT (水处理) — 是否有攻击描述文本?
- **有PDF描述**: 41次攻击在PDF文档中有描述, 包含攻击意图、目标、方法
- **无inline文本**: 数据本身只有二值标签(正常/异常), 无文本字段
- **下载**: 需向iTrust申请, 不能直接下载
- **结论: 攻击描述在PDF中, 不与数据天然配对**

### WADI (水分配) — 是否有攻击描述文本?
- 与SWaT类似, 攻击描述在文档中
- 需向iTrust申请
- **结论: 同SWaT, 不满足inline配对**

### HAI (工业控制) — 是否有攻击描述文本?
- **无详细文本描述**: 数据集只有攻击时间标签(起止时间)
- 攻击类型在论文中描述, 但不在数据中
- summary目录有攻击统计信息
- **结论: 仅有时间标签, 无文本描述**

### TON-IoT — 是否有遥测+日志配对?
- **有遥测+日志**: IoT/IIoT遥测数据(log+CSV) + 网络日志 + OS日志
- SecurityEvents_GroundTruth有攻击事件+时间戳
- **但日志是系统日志, 非故障/报警的自然语言文本**
- 下载: SharePoint
- **结论: 有遥测+日志配对, 但日志非自然语言描述**

### BATADAL — 是否有故障描述?
- **仅有二值标签**: 正常/攻击
- 攻击描述在竞赛文档中
- **结论: 无文本描述, 不满足需求**

### Tennessee Eastman — 是否有故障描述?
- **有21种故障类型的文本描述** (如"A/C feed ratio, B composition constant")
- 但描述是固定类别标签, 非逐条文本
- `tep_alarms_text` 数据集补充了逐条报警文本描述
- **结论: TEP传感器数据有故障类型描述; tep_alarms_text有逐条报警文本**

---

## 四、推荐组合方案

### 方案A: TEP 仿真 (最完整的"时序+报警文本"配对)
1. **时序数据**: `mv-per/tennessee-eastman-dataset` (GitHub, 15 stars)
   - 21种故障, 41变量, 50-500小时
2. **报警文本**: `andreenko-repo/tep_alarms_text` (GitHub, 2 stars)
   - 100+ CSV文件, 每条报警有文本描述
3. **配对方式**: 按时间戳对齐传感器时序与报警文本
4. **优势**: 报警文本是操作员控制台真实显示的描述, 天然配对
5. **劣势**: 来自仿真, 非真实电力系统

### 方案B: 风电SCADA + 故障标注
1. **数据集**: CARE to Compare (HF: kevykibbz, 6 likes)
   - 36风机, 89年累计, 44个故障标注
2. **优势**: 真实风电场数据, 规模大, 有传感器描述文本
3. **劣势**: 故障描述详细程度需下载确认

### 方案C: HAI 电力ICS + 攻击标签
1. **数据集**: `icsdataset/hai` (GitHub, 177 stars)
   - 汽轮机+水电, 78-86传感器, 58次攻击
2. **优势**: 电力领域, 数据量大, 高质量
3. **劣势**: 无攻击文本描述, 仅有时间标签

### 方案D: 自建配对 (使用lkev/wtphm格式)
1. **库**: `lkev/wtphm` (GitHub, 87 stars)
2. **方法**: 按库定义的格式, 获取风电SCADA + 事件/报警数据
3. **优势**: 库已定义好配对方法, 报警有description字段
4. **劣势**: 需要自行获取数据(库不含数据)

---

## 五、数据下载方式汇总

| 数据集 | 下载方式 | 链接 |
|--------|----------|------|
| tep_alarms_text | GitHub直接 | https://github.com/andreenko-repo/tep_alarms_text |
| TEP (mv-per) | GitHub直接 | https://github.com/mv-per/tennessee-eastman-dataset |
| CARE to Compare | HF/Zenodo | https://huggingface.co/datasets/kevykibbz/wind-turbine-scada-data-for-early-fault-detection |
| HAI | GitHub LFS/Kaggle | https://github.com/icsdataset/hai |
| TON-IoT | SharePoint | https://research.unsw.edu.au/projects/toniot-datasets |
| SWaT | iTrust申请 | https://www.sutd.edu.sg/itrust/request-for-datasets/ |
| WADI | iTrust申请 | https://www.sutd.edu.sg/itrust/request-for-datasets/ |
| BATADAL | GitHub/iTrust | https://github.com/SYChen123/A-survey-on-BATADAL-dataset |
| EPIC | iTrust申请 | https://www.sutd.edu.sg/itrust/request-for-datasets/ |
| DGA变压器 | GitHub/CSDN | https://github.com/QQ767172261/How-to-apply-transformer-DGA-oil-chromatography-dataset-and-transformer-fault-diagnosis-case-dataset |
| QUT S7comm | GitHub直接 | https://github.com/qut-infosec/2017QUT_S7comm |
| lkev/wtphm | pip install | https://github.com/lkev/wtphm |
