# SCADA时序 + 维护日志/故障记录 配对数据集搜索报告

> 搜索范围: GitHub, HuggingFace, arXiv
> 搜索日期: 2026-07-12
> 场景: 航发维护 — 传感器时序 ↔ 故障工单/维护记录文本

---

## 一、核心发现总结

### 真正有"时序+文本"天然配对的数据集 (按推荐度排序)

| # | 数据集 | 时序类型 | 文本类型 | 真实/合成 | 天然配对 | 规模 |
|---|--------|----------|----------|-----------|----------|------|
| 1 | **TON-IoT** (UNSW) | IoT遥测+网络流量 | OS日志(Windows/Linux) | 真实 | ✅ 是 | 多模态,大量 |
| 2 | **CARE to Compare** (风电SCADA) | 风机SCADA时序 | 详细故障信息(状态码+故障描述) | 真实 | ⚠️ 半(结构化故障标签,非自由文本) | 36台风机,89年累计,95个数据集 |
| 3 | **jvachier/industrial-maintenance-synthetic-data** | 传感器标签时序 | 维修工单文本(WorkOrder/Operation/Description) | 合成 | ✅ 是 | 500K+行,可扩展到1M+ |
| 4 | **SWaT** (水处理) | SCADA传感器时序 | 攻击日志(攻击类型+时间窗口) | 真实 | ⚠️ 半(攻击描述文档,非实时文本日志) | 51传感器,11天,946K行 |
| 5 | **WADI** (水分配) | SCADA传感器时序 | 攻击日志 | 真实 | ⚠️ 半 | 127传感器,16天 |
| 6 | **HAI** (工业控制) | SCADA传感器时序 | 攻击标签(攻击目标+控制器+点位) | 真实 | ⚠️ 半(结构化标签,非文本) | 4版本,最大534MB,79次攻击 |
| 7 | **Edge-Industrial-Anomaly-Phi3** | 传感器读数 | 自然语言推理(合成) | 合成 | ❌ 合成配对 | 11.9K条 |

### 关键结论

**真正有"传感器时序 + 自由文本维护日志"天然配对的公开数据集极其稀缺。** 现有数据集大多只有:
- 时序 + 二元/结构化标签 (HAI, SWaT, WADI)
- 时序 + 状态码 (CARE to Compare)
- 合成时序 + 合成工单 (jvachier)
- 多模态遥测 + OS日志 (TON-IoT, 但不是维护工单)

---

## 二、详细数据集清单

### 1. TON-IoT (Telecommunications and Operations Networks-IoT)

| 属性 | 值 |
|------|-----|
| 来源 | UNSW Sydney (澳大利亚) |
| 官方页面 | https://research.unsw.edu.au/projects/toniot-datasets |
| GitHub镜像 | Nour-Moustafa/TON_IoT-Network-dataset (9 stars) |
| 另一镜像 | AnisurRahman251/TON_IoT (0 stars) — "Multi-Modal: Network Traffic + Windows Logs + Linux Logs + IoT Telemetry" |
| 数据模态 | 网络流量 + Windows事件日志 + Linux系统日志 + IoT遥测 |
| 真实/合成 | 真实 (从物理实验台采集) |
| 时序+文本配对 | ✅ **是** — IoT遥测(时序)与OS日志(文本)同期采集 |
| 下载方式 | Kaggle, 官方页面注册 |
| 规模 | 多个子数据集,涵盖网络、端点、遥测 |

**评价**: TON-IoT 是最接近"时序+日志文本配对"的真实数据集。IoT遥测数据与Windows/Linux系统日志同期采集,可以进行跨模态分析。但日志是系统事件日志,不是维护工单文本。

---

### 2. CARE to Compare — 风电SCADA故障检测数据集

| 属性 | 值 |
|------|-----|
| 论文 | arXiv:2404.10320 "CARE to Compare: A real-world dataset for anomaly detection in wind turbine data" |
| HuggingFace | kevykibbz/wind-turbine-scada-data-for-early-fault-detection (6 likes, 54 downloads) |
| DOI | https://doi.org/10.3390/data9120138 |
| 风机数量 | 36台风机,3个风场 |
| 数据规模 | 89年累计运行数据,95个数据集 |
| 标注 | 44个异常时间帧(导致故障) + 51个正常时间序列 |
| 标注质量 | "最详细的风电公开数据集故障信息" — 涡轮机状态码标签 |
| 真实/合成 | 真实 |
| 下载方式 | HuggingFace直接下载 |
| 时序+文本配对 | ⚠️ **半配对** — 有详细故障信息,但故障描述是结构化状态码,非自由文本维护日志 |
| 模态标签 | modality:tabular + modality:text (HuggingFace标签) |

**评价**: 这是目前公开的最详细风电SCADA数据集。故障信息比一般数据集丰富(包含故障类型、时间窗口),但仍然是结构化标签,不是技术人员写的自由文本维护工单。

---

### 3. Wind Turbine Maintenance Log Labelling Framework (arXiv:2605.31281)

| 属性 | 值 |
|------|-----|
| 论文 | arXiv:2605.31281 "Wind Turbine Maintenance Log Labelling Framework: LLM-Driven Data Correction and Enrichment" |
| 作者 | Max Malyi, Jonathan Shek, Alasdair McDonald, Andre Biscaya (爱丁堡大学) |
| GitHub | mvmalyi/llm-driven-wind-turbine-maintenance-log-labelling (MIT License) |
| 数据规模 | 16,316条维护日志,280台风机,9年监测 |
| 数据内容 | 维护工单自由文本(WO_ID, Description, System_Code, Maintenance_Type等) |
| 真实/合成 | 真实 |
| **关键问题** | ❌ **数据不公开** — 仓库只包含LLM标注框架代码,实际16,316条维护日志是作者专有数据,未公开发布 |
| 时序+文本配对 | ❌ 无SCADA时序 — 仅有维护日志文本,不含传感器时序数据 |
| 下载方式 | 仓库可clone,但数据需用户自行准备CSV |

**README关键信息**:
- 用户需准备两个CSV: `maintenance_logs.csv` (含WO_ID, Description, System_Code等) 和 `rds_pp_components.csv` (层级组件字典)
- 框架用LLM自动纠正系统代码、提取故障模式、生成FMEA字典
- 数据来自CMS (Computed Maintenance Management System)

**评价**: 这是与航发维护场景最相关的论文(风机维护工单文本),但**数据本身不公开**。仓库仅提供处理框架。可作为方法论参考,但无法直接获取数据。

---

### 4. SWaT (Secure Water Treatment)

| 属性 | 值 |
|------|-----|
| 来源 | iTrust, SUTD Singapore |
| 官方页面 | https://www.sutd.edu.sg/itrust/itrust-labs/datasets/ |
| 数据类型 | 水处理SCADA传感器时序 + 网络数据包 |
| 传感器数 | 51个 (阀门、泵、水位等物理传感器) |
| 正常数据 | 11天连续运行,496,800行 (1秒间隔) |
| 攻击数据 | 36次攻击场景 |
| 真实/合成 | 真实 (物理测试台) |
| 下载方式 | 向iTrust申请 (免费,需3个工作日审核) |
| 时序+文本配对 | ⚠️ **半配对** — 有攻击列表文档(攻击类型+时间窗口描述),但不是自由文本维护日志 |
| GitHub相关 | elisejiuqizhang/USAD-on-WADI-and-SWaT (80 stars) — 使用该数据集的代码 |

**评价**: SWaT是工业控制系统安全领域最权威的基准数据集之一。传感器时序质量高,但"文本"部分仅限于攻击场景的结构化描述文档,不是实时维护/报警文本日志。

---

### 5. WADI (Water Distribution)

| 属性 | 值 |
|------|-----|
| 来源 | iTrust, SUTD Singapore |
| 官方页面 | 同SWaT |
| 数据类型 | 水分配网络SCADA传感器时序 + 网络数据包 |
| 传感器数 | 127个传感器/执行器 |
| 正常数据 | 16天连续运行 |
| 攻击数据 | 15次攻击场景 |
| 真实/合成 | 真实 (物理测试台) |
| 下载方式 | 向iTrust申请 (免费) |
| 时序+文本配对 | ⚠️ **半配对** — 同SWaT |

---

### 6. HAI (HIL-based Augmented ICS) Security Dataset

| 属性 | 值 |
|------|-----|
| GitHub | **icsdataset/hai (177 stars, 54 forks)** |
| Kaggle | https://www.kaggle.com/datasets/icsdataset/hai-security-dataset |
| 来源 | 韩国ETRI附属研究所 |
| 测试台 | 4个过程: 锅炉(P1,Emerson DCS) + 涡轮机(P2,GE Mark VIe DCS) + 水处理(P3,Siemens S7-300 PLC) + HIL仿真(P4,dSPACE) |
| 版本 | HAI 20.07 / 21.03 / 22.04 / 23.05 + HAIEnd 23.05 |
| 数据格式 | CSV,第一列时间戳,其余列为SCADA数据点,最后4列为攻击标签 |
| 最大版本 | HAI 23.05: 86个数据点,正常数据494.8MB,攻击数据156.6MB,79次攻击 |
| 真实/合成 | 真实 |
| 下载方式 | `git clone https://github.com/icsdataset/hai` + `git lfs pull` |
| 时序+文本配对 | ⚠️ **半配对** — 攻击标签为结构化(attack, attack_P1, attack_P2, attack_P3),攻击目标信息(控制器+点位)有文档描述,但不是自由文本 |
| License | CC BY-SA 4.0 |

**数据字段示例**:
```
time, P1_B2004, P2_B2016, ..., P4_HT_LD, attack, attack_P1, ..., attack_P3
20190926 13:00:00, 0.09830, 1.07370, ..., 0, 0, 0, ..., 0
```

**评价**: HAI是ICS安全领域星数最高的数据集(177 stars)。测试台包含锅炉、涡轮机、水处理,与航发场景有部分相似性(涡轮机过程)。但攻击信息是结构化标签,没有维护工单文本。

---

### 7. jvachier/industrial-maintenance-synthetic-data

| 属性 | 值 |
|------|-----|
| GitHub | jvachier/industrial-maintenance-synthetic-data (1 star) |
| HuggingFace | Jvachier/industrial-maintenance-synthetic |
| Kaggle | Industrial Maintenance Synthetic Dataset |
| 数据类型 | 传感器标签时序 + 维修工单文本 |
| 真实/合成 | **合成** |
| 规模 | 默认500K行,可扩展到1M+ |
| 下载方式 | GitHub clone运行生成器,或HuggingFace/Kaggle直接下载 |
| 时序+文本配对 | ✅ **是** — sensor_tags表与maintenance表通过Equipment_ID关联 |
| License | Apache 2.0 |

**传感器标签数据模式**:
- Tag_name, Server_name, Description, Units, Building, Production_line, Equipment_ID, Equipment_type, Variable_type

**维修工单数据模式**:
- Location, Region, WorkOrder, Equipment_ID, OrderType (PM/CM/PDM/EM/STAT), WorkOrderDescription, OperationDescription, MaintenanceWorkCenter, CreatedDate, ScheduledStartDate, ActualStartDate, TechnicalCompletionDate, ActualWork, OrderStatus

**评价**: 这是目前唯一一个明确将"传感器时序数据"与"维修工单文本"配对的公开数据集。但数据是**合成的**,由脚本生成。可用于方法验证和原型开发,但不适合作为真实场景的最终评估。

---

### 8. Amreen-source/Wind-Energy-Systems (多模态融合)

| 属性 | 值 |
|------|-----|
| GitHub | Amreen-source/Wind-Energy-Systems-Using-Multimodal-Fusion-and-Multi-Agent-Deep-Reinforcement-Learning (4 stars) |
| 数据类型 | SCADA数据 + 维护日志(BERT编码) + 无人机图像(ViT) + 天气记录 |
| 真实/合成 | ⚠️ 混合 — 使用NREL数据集,无真实数据时自动生成合成数据 |
| 时序+文本配对 | ✅ 架构上是 — 代码中有text_processor.py (BERT处理维护日志) + nrel_data_loader.py (SCADA加载) |
| 下载方式 | GitHub clone |
| 关键文件 | data_pipeline.py, text_processor.py, nrel_data_loader.py, image_processor.py |

**评价**: 这个仓库的架构设计完全符合"SCADA时序 + 维护日志文本"的多模态融合需求。但README明确说明"系统在真实数据不可用时自动生成合成数据",且仓库本身不包含真实数据。

---

### 9. Edge-Industrial-Anomaly-Phi3

| 属性 | 值 |
|------|-----|
| HuggingFace | ssam17/Edge-Industrial-Anomaly-Phi3 (1 like, 77 downloads) |
| 数据类型 | 传感器读数→自然语言推理文本 (Phi-3 chat格式) |
| 真实/合成 | 合成 (从Kaggle数据集转换,自然语言推理由规则合成) |
| 规模 | 11,944条 |
| 来源 | 3个Kaggle数据集: Industrial Fault Detection + Edge-IIoTset + Machine Failure Prediction |
| 时序+文本配对 | ❌ 合成配对 — 文本是由传感器值通过规则生成的,非人工编写 |

**数据格式示例**:
```
<|user|> Sensor Readings: Temperature: 82°C, Vibration: 3.8 m/s, Pressure: 112 kPa
<|end|>
<|assistant|> Status: ANOMALY. Reason: Critical overheating detected...
<|end|>
```

---

### 10. BATADAL (BATtle of Attack Detection Algorithms)

| 属性 | 值 |
|------|-----|
| 来源 | iTrust (也在列表中) |
| 数据类型 | 水分配网络SCADA时序 |
| 时序+文本配对 | ⚠️ 半 — 有攻击场景描述 |

---

### 11. 其他HuggingFace数据集 (时序+文本标签)

| 数据集 | 描述 | 时序+文本 | 真实/合成 |
|--------|------|-----------|-----------|
| electricsheepafrica/nigerian_energy_and_utilities_predictive_maintenance | 电力设备健康+故障概率+推荐行动 | ⚠️ 半(有recommended_action文本) | 合成/派生 |
| EddyGiusepe/Modified_dataset_for_predictive_maintenance | 预测性维护 | ❌ 无文本 | 真实改造 |
| Petsteb/industrial-sensor-anomaly-data | 工业设备传感器异常检测 | ⚠️ 有modality:text标签 | 合成 |
| vossmoos/vestasv52-scada-windturbine-granada | Vestas V52风机SCADA合成数据 | ❌ 无维护文本 | 合成 |

---

## 三、按场景需求匹配

### 场景1: 风电场SCADA数据+维护日志

| 数据集 | 匹配度 | 说明 |
|--------|--------|------|
| CARE to Compare (arXiv:2404.10320) | ★★★★ | 最详细的公开风电SCADA+故障信息,但故障是状态码非自由文本 |
| arXiv:2605.31281 (Malyi et al.) | ★★★★★ (但数据不公开) | 16,316条维护日志+280台风机9年,完美的文本数据,但**不公开** |
| Amreen-source/Wind-Energy-Systems | ★★★ | 多模态融合架构(SCADA+维护日志),但数据合成 |
| kevykibbz HuggingFace | ★★★★ | CARE to Compare的HuggingFace镜像,可直接下载 |

### 场景2: 电力设备监控数据+故障记录

| 数据集 | 匹配度 | 说明 |
|--------|--------|------|
| HAI (icsdataset/hai) | ★★★ | 含涡轮机/锅炉/水处理过程,攻击标签但无维护文本 |
| electricsheepafrica/nigerian_energy | ★★ | 电力设备健康+推荐行动,但合成 |
| EPIC (iTrust) | ★★ | Electric Power and Intelligent Control,需申请 |

### 场景3: 水处理/工业过程SCADA+报警日志

| 数据集 | 匹配度 | 说明 |
|--------|--------|------|
| SWaT | ★★★★ | 最权威水处理SCADA+攻击日志,但攻击描述是文档非实时日志 |
| WADI | ★★★★ | 水分配网络SCADA+攻击日志 |
| HAI | ★★★ | 含水处理过程(P3) |

### 场景4: 油气管道监控+巡检记录

| 数据集 | 匹配度 | 说明 |
|--------|--------|------|
| 未找到直接匹配 | — | 油气管道SCADA+巡检文本的公开数据集在GitHub/HuggingFace上未找到 |

### 场景5: 工厂设备监控+维修工单

| 数据集 | 匹配度 | 说明 |
|--------|--------|------|
| jvachier/industrial-maintenance-synthetic-data | ★★★★ | 唯一明确传感器+工单文本配对,但合成 |
| ssam17/Edge-Industrial-Anomaly-Phi3 | ★★ | 传感器→自然语言,但文本是规则合成 |

### 场景6: 车队管理遥测+维修记录

| 数据集 | 匹配度 | 说明 |
|--------|--------|------|
| 未找到直接匹配 | — | 车队遥测+维修工单的公开数据集未找到 |

---

## 四、特别关注数据集详细分析

### SWAT — 是否有攻击日志+传感器时序?

**是。** SWaT包含:
- ✅ 51个传感器的SCADA时序数据 (1秒间隔,11天正常+攻击期间)
- ✅ 攻击列表文档: 每次攻击有编号、类型、开始/结束时间、受影响的传感器/执行器
- ❌ 但攻击日志是结构化文档,不是实时报警文本日志或维护工单

下载: 向iTrust申请 (https://www.sutd.edu.sg/itrust/request-for-datasets/)

### WADI — 是否有攻击日志+传感器时序?

**是。** WADI包含:
- ✅ 127个传感器/执行器的SCADA时序数据
- ✅ 15次攻击的场景描述
- ❌ 同样是结构化攻击文档,非自由文本

### HAI — 是否有攻击日志+传感器时序?

**是。** HAI包含:
- ✅ SCADA时序数据 (最多86个数据点,1秒间隔)
- ✅ 攻击标签 (attack列: 0/1) + 分过程标签 (attack_P1/P2/P3)
- ✅ 从HAI 22.04起,提供攻击目标信息(控制器+点位)
- ✅ HAIEnd 23.05提供锅炉DCS内部逻辑数据 + NetworkX图数据
- ❌ 攻击信息是结构化标签,不是维护工单文本

下载: `git clone https://github.com/icsdataset/hai` + `git lfs pull` (177 stars)

### TON-IoT — 是否有遥测+日志配对?

**是。** TON-IoT包含:
- ✅ IoT遥测数据 (时序)
- ✅ Windows事件日志 (文本)
- ✅ Linux系统日志 (文本)
- ✅ 网络流量数据
- 这是唯一一个真正有"时序遥测+文本日志"同期采集的多模态数据集
- ⚠️ 但日志是系统安全事件日志,不是设备维护工单

### 风电维护日志 (arXiv:2605.31281) — 16,316条日志+280台风机9年

**数据不公开。** 论文描述了:
- 16,316条维护日志 (自由文本Description + System_Code + Maintenance_Type)
- 280台风机,9年监测
- LLM自动标注框架 (纠正系统代码、提取故障模式、生成FMEA字典)
- GitHub仓库 (mvmalyi/llm-driven-wind-turbine-maintenance-log-labelling) 仅包含框架代码
- ❌ 实际维护日志数据为作者专有,未发布

---

## 五、推荐策略

### 对于"航发维护: 传感器时序 ↔ 故障工单文本"场景

1. **最佳真实数据**: CARE to Compare (HuggingFace: kevykibbz/wind-turbine-scada-data-for-early-fault-detection)
   - 真实风电SCADA + 最详细故障信息
   - 可下载,36台风机,89年累计数据

2. **最佳多模态配对**: TON-IoT
   - 真实遥测 + 真实系统日志
   - 虽然不是维护工单,但日志文本与遥测时序天然配对

3. **最佳合成数据**: jvachier/industrial-maintenance-synthetic-data
   - 传感器时序 + 维修工单文本明确配对
   - 可用于方法验证和原型开发

4. **方法论参考**: arXiv:2605.31281 (mvmalyi)
   - 虽然数据不公开,但LLM标注框架可复用于航发维护日志处理

5. **ICS安全基准**: HAI (icsdataset/hai, 177 stars)
   - 含涡轮机过程,SCADA时序+攻击标签
   - 适合异常检测方法开发

### 缺口分析

**目前公开数据生态中不存在"真实SCADA时序 + 真实自由文本维护工单"天然配对的大规模数据集。** 这正是航发维护场景的数据瓶颈。可能的解决路径:
1. 从CARE to Compare的结构化故障标签出发,用LLM生成模拟维护工单文本
2. 用jvachier的合成数据验证方法,再迁移到真实场景
3. 与风场/航发运营商合作获取真实维护日志 (如Malyi等人的做法)
4. 利用TON-IoT的遥测+日志配对范式,迁移到工业设备维护场景
