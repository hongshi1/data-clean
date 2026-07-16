# 场景2·数据方案设计与Crazyflie AADL详细介绍

> 版本: v1.0 | 日期: 2026-07-12
> 状态: 方案已确定，Crazyflie AADL已下载

---

## 一、三个组合方案

### 方案A：Crazyflie AADL（推荐，最完整）

```
Crazyflie AADL模型（已下载 /tmp/crazyflie_aadl/）
  │
  ├─ 功能视图: latency=100us..300us, Period=4ms        ← 静态参数
  ├─ 硬件视图: Frequency=168Mhz, Scheduling=POSIX       ← 静态参数
  ├─ 软件视图: latency=1ms..2ms + 错误传播              ← 静态参数+错误
  ├─ 错误模型: ValueError/ValueErroneous/Lost          ← 不一致类型定义
  ├─ 端到端流: Gyro→Fusion→Controller→Motors(0-2ms)    ← 传递链
  ├─ SysML v2翻译版: 4个.sysml文件(已下载)              ← 两种格式都有
  └─ 图形化图表: 5个.aadl_diagram                       ← 可视化
      │
      ↓ 安装OSATE或Ocarina运行分析
      │
  ├─ flow latency analysis结果（实际延迟）               ← 仿真输出
  ├─ schedulability analysis结果（可调度性）             ← 仿真输出
  └─ fault analysis结果（故障树）                       ← 仿真输出
      │
      ↓ 配对
      │
  静态参数(latency=100us) ↔ 分析结果(实际latency=150us)  ← 检测点2
```

- **多视图**: ✅ 5个视图(功能/硬件/软件/系统/错误)
- **仿真结果**: ⚠️ 需运行OSATE/Ocarina
- **复杂度**: 中（安装一个工具）
- **优点**: 最完整，有多视图+参数+错误模型+可运行分析+SysML翻译版

### 方案B：SysML + Modelica组合

```
SysML v2 SimpleVehicleModel（已下载 /tmp/sysml_v2/）
  ├─ 需求视图: MassRequirement(mass≤massLimit)
  ├─ 结构视图: Vehicle(mass/velocity/acceleration)
  ├─ 行为视图: state on{electricalPower≤500W}
  ├─ 参数视图: calc Acceleration/Velocity
  └─ 分配视图: vehicleLogical→vehicle_b
      +
Modelica标准库（已下载 /tmp/modelica_lib/）
  ├─ parameter threshold=5.0
  └─ equation fired=voltage>=threshold
      │
      ↓ 把SysML参数映射到Modelica模型 → 运行OpenModelica
      │
  仿真输出时序数据
      │
  SysML约束(electricalPower≤500W) ↔ Modelica仿真(实际power=520W)
```

- **多视图**: ✅ 9类视图
- **仿真结果**: ⚠️ 需运行OpenModelica + 需手动映射SysML→Modelica
- **复杂度**: 高（需映射+运行）
- **优点**: SysML视图最全(152定义)

### 方案C：MathWorks全栈（最快可用）

```
MathWorks巡航控制项目（已下载 /tmp/mathworks_simulink/）
  ├─ 需求文档: crs_req1.docx(119段+3表格)
  ├─ Simulink模型: 5个.slx
  ├─ 参数表格: Kp=20/Ki=0.2/Kd=-0.0249
  ├─ 仿真数据: .mat(Kp=20/Ki=0.19998)
  ├─ 需求追溯: .slreqx + .slmx
  └─ ISO 26262检查: 50+项
      │
  表格3(Ki=0.2) ↔ .mat(Ki=0.19998) ← 已发现真实超差!
```

- **多视图**: ⚠️ Simulink非SysML
- **仿真结果**: ✅ 已有参数对比(已发现Ki超差)
- **复杂度**: 低（已有数据可直接用）
- **优点**: 最快可用，已发现真实参数超差

---

## 二、Crazyflie AADL详细介绍

### 2.1 系统概述

**Crazyflie** 是Bitcraze公司开发的商业微型无人机（20g级），广泛用于研究和教育。OpenAADL组织为其建立了完整的AADL系统模型，用于演示AADL的分析能力。

- **来源**: OpenAADL/Crazyflie (GitHub, 11★)
- **原始模型**: 7个.aadl文件 + 7个库文件 + 5个图表
- **SysML翻译版**: 4个.sysml文件 (OMG Systems-Modeling/SysML-v2-AADL-Release)
- **用途**: Georgia Tech OMSCS课程CS7639教学用
- **下载位置**: `/tmp/crazyflie_aadl/` (AADL版) + `/tmp/crazyflie_sysml/` (SysML版)

### 2.2 模型文件结构

```
crazyflie_aadl/
├── models/
│   ├── crazyflie_functional.aadl    (3.3KB) 功能视图
│   ├── crazyflie_hardware.aadl      (4.6KB) 硬件视图
│   ├── crazyflie_software.aadl      (4.3KB) 软件视图
│   ├── crazyflie_system.aadl        (2.4KB) 系统集成视图
│   ├── crazyflie_final.aadl         (1.0KB) 最终实现视图
│   ├── crazyflie_errors.aadl        (0.4KB) 错误模型
│   ├── crazyflie_types.aadl         (1.1KB) 类型定义
│   └── crazyflie.aic                (1.0KB) AADL Inspector配置
├── library/
│   ├── buses-i2c.aadl               I2C总线库
│   ├── buses-spi.aadl               SPI总线库
│   ├── buses-uart.aadl              UART总线库
│   ├── bus_properties.aadl          总线属性
│   ├── processors-arm.aadl          ARM处理器库
│   ├── processor_properties.aadl    处理器属性
│   └── processors.aadl              处理器基类
└── diagrams/
    ├── Crazyflie_functional*.aadl_diagram  功能视图图表
    ├── Crazyflie_Hardware*.aadl_diagram    硬件视图图表
    ├── Crazyflie_Software*.aadl_diagram    软件视图图表
    ├── Crazyflie_System*.aadl_diagram      系统视图图表
    └── Crazyflie_Final*.aadl_diagram       最终实现图表
```

### 2.3 五个视图详解

#### 视图1：功能视图 (crazyflie_functional.aadl)

**描述**: 无人机的功能链——从传感器到电机的信号处理流程

**组件**:
| 组件 | 类型 | 功能 | 端口 | Period | Latency |
|---|---|---|---|---|---|
| Accelero | abstract | 加速度计 | Accelero_Out | 4ms(250Hz) | 100-300us |
| Gyro | abstract | 陀螺仪 | Gyro_Out | 4ms(250Hz) | 100-300us |
| Magneto | abstract | 磁力计 | Magneto_Out | 4ms(250Hz) | 100-300us |
| Sensor_Fusion | abstract | 传感器融合 | 3输入+1输出 | 4ms(250Hz) | 200-400us |
| Controller | abstract | 控制器 | 2输入+1输出+TC | 2ms(500Hz) | 200-400us |
| Motors | abstract | 电机 | Motor_In | 2ms | 100-500us |
| Pilot | abstract | 飞行员指令 | Order | - | - |

**连接链**:
```
Accelero → Sensor_Fusion → Controller → Motors
Gyro → Sensor_Fusion
Gyro → Controller (直连)
Magneto → Sensor_Fusion
Pilot → Controller (TC指令)
```

**端到端流(3条)**:
- f_etef1: Gyro→Fusion→Controller→Motors, latency=0-2ms
- f_etef1bis: Gyro→Controller→Motors, latency=0-2ms
- f_etef2: Acc→Fusion→Controller→Motors, latency=0-2ms

**场景2对标**:
- 端到端流 = 跨视图传递链(检测点3)
- latency参数 = 静态参数(检测点2)
- 组件连接 = 功能覆盖(检测点1)

#### 视图2：硬件视图 (crazyflie_hardware.aadl)

**描述**: 无人机的物理硬件架构

**组件**:
| 组件 | 类型 | 规格 | 总线 |
|---|---|---|---|
| STM32F405 | processor | Cortex-M4@168MHz | I2C+SPI+UART+PWM |
| nRF51822 | processor | 无线通信 | - |
| MPU9250 | device | 9轴传感器(加速度+陀螺+磁力) | I2C |
| Propellers | device | 4个螺旋桨 | PWM |
| i2c | bus | I2C总线 | - |

**属性**:
- Processor_Frequency => 168Mhz
- Scheduling_Protocol => POSIX_1003_HIGHEST_PRIORITY_FIRST_PROTOCOL
- 引用了错误模型(EMV2)

**场景2对标**:
- 硬件组件 = 产品组成模型(九视图之"块定义")
- 处理器频率 = 静态参数(检测点2)
- 总线访问 = 接口视图

#### 视图3：软件视图 (crazyflie_software.aadl)

**描述**: 无人机固件架构

**组件**:
| 组件 | 类型 | 功能 | 端口 | Latency |
|---|---|---|---|---|
| nRF51822_Firmware | process | 无线固件 | Syslink_TX/RX | 1-2ms |
| STM32F405_Firmware | process | 飞控固件 | Syslink+DOFs+4×Rate | - |

**错误传播(EMV2)**:
```
error propagations:
  Rate_1 : out propagation{ValueErroneous};    ← 输出错误
  DOFs: in propagation{ValueErroneous};         ← 输入错误
  Syslink_Packet_RX: in propagation{ValueErroneous};
  processor : in propagation{Lost, ValueErroneous};

error flows:
  f1 : error path Syslink_Packet_RX -> Rate_1;              ← 错误传播路径
  f2 : error path DOFs{ValueErroneous} -> Rate_1{ValueErroneous};  ← 错误转换
```

**场景2对标**:
- 错误传播 = 不一致传递链(检测点3)
- 软件端口 = 接口定义
- latency = 静态参数(检测点2)

#### 视图4：系统集成视图 (crazyflie_system.aadl)

**描述**: 将功能、硬件、软件集成到完整系统

**场景2对标**:
- 系统集成 = 跨视图传递(检测点3)
- 功能→硬件分配 = 覆盖性(检测点1)

#### 视图5：错误模型 (crazyflie_errors.aadl)

**描述**: 定义系统中的错误类型和错误状态机

```
error types:
  ValueError     : type;       ← 数值错误
  ValueErroneous : type;       ← 数值异常
  Lost           : type;       ← 丢失

error behavior simple:
  states:
    Operational : initial state;  ← 正常运行
    Failed : state;               ← 故障
```

**场景2对标**:
- 错误类型 = 不一致类型定义(可直接用于标注)
- 错误状态机 = 不一致检测的目标状态
- 错误传播 = 不一致传递路径(检测点3)

### 2.4 可运行的分析

README明确列出3种工具的分析能力:

| 工具 | 分析类型 | 输出 | 场景2检测点 |
|---|---|---|---|
| **OSATE** | flow latency analysis | 端到端流实际延迟 | 检测点2(静态latency↔动态latency) |
| **OSATE** | fault analysis (含故障树) | 故障树+传播路径 | 检测点3(传递链) |
| **AADL Inspector** | schedulability (Cheddar) | 调度可行性结果 | 检测点2(Period↔调度) |
| **AADL Inspector** | model simulation (Marzhin) | 仿真运行时序 | 检测点2(静态↔动态) |
| **Ocarina** | code generation (C/Ada) | 生成代码 | 辅助 |
| **Ocarina** | WCET analysis | 最坏执行时间 | 检测点2(Period↔WCET) |
| **Ocarina** | model checking (Petri Net) | 模型检验结果 | 检测点3(逻辑一致性) |
| **Ocarina** | constraint analysis (REAL) | 约束检验结果 | 检测点2(约束↔实际) |

### 2.5 SysML v2翻译版

OMG将AADL模型翻译为SysML v2格式，4个文件:

| AADL文件 | SysML v2文件 | 内容 |
|---|---|---|
| crazyflie_functional.aadl | 1_crazyflie_functional.sysml | 功能链+端口+连接 |
| crazyflie_hardware.aadl | 2_crazyflie_hw_platform.sysml | 硬件平台+**allocate分配** |
| crazyflie_software.aadl | 3_crazyflie_sw.sysml | 固件+通信连接 |
| library/*.aadl | cots_hw.sysml | COTS硬件组件库 |

**翻译版的关键配对关系**:
- 文件2 import文件1 ✅ (硬件引用功能)
- 文件3 import文件2 ✅ (软件引用硬件)
- 文件2有allocate语句 ✅ (功能→硬件分配)

### 2.6 场景2的3个检测点验证方案

#### 检测点1: 覆盖性（要求→实现断裂）

**数据配对**:
- 功能视图6个组件(Accelero/Gyro/Magneto/Sensor_Fusion/Controller/Motors)
- 硬件视图3个设备(MPU9250/STM32F405/Propellers)
- SysML翻译版的allocate分配语句

**验证方法**:
```
检查每个功能组件是否有对应的硬件设备:
  Accelero → MPU9250 ✅ (allocate)
  Gyro → MPU9250 ✅ (allocate)
  Magneto → MPU9250 ✅ (allocate)
  Sensor_Fusion → MPU9250 ✅ (allocate)
  Controller → STM32F405 ✅ (allocate)
  Motors → Propellers ✅ (allocate)
  
如果删掉某个allocate → 检测到覆盖性矛盾
```

#### 检测点2: 静态↔动态（参数超差）

**数据配对**:
- 静态参数: latency=100us..300us(功能视图flows中定义)
- 动态结果: flow latency analysis的输出(需运行OSATE)

**验证方法**:
```
比对每个流的定义latency vs 分析latency:
  Accelero.f1: 定义100-300us vs 分析结果???us
  Sensor_Fusion.f1: 定义200-400us vs 分析结果???us
  f_etef1: 定义0-2ms vs 分析结果???ms

如果分析结果超出定义范围 → 检测到参数超差
```

**不运行工具时的替代**:
- MathWorks项目已有真实超差: Ki=0.2(表格) vs Ki=0.19998(.mat)
- 可直接用此超差验证检测点2

#### 检测点3: 传递链断裂

**数据配对**:
- 端到端流: Gyro→Fusion→Controller→Motors
- 错误传播: DOFs{ValueErroneous}→Rate_1{ValueErroneous}
- 文件间import: 功能→硬件→软件

**验证方法**:
```
检查端到端流的每个环节:
  Gyro→Fusion: connection C2 ✅
  Fusion→Controller: connection C5 ✅
  Controller→Motors: connection C6 ✅

如果删掉C5 → 传递链断裂(Fusion→Controller无连接)
如果改错误传播路径 → 错误传递不一致
```

### 2.7 下一步行动

| 步骤 | 做什么 | 产出 |
|---|---|---|
| 1 | 保存本方案文档 | `docs/feishu/research/场景2_数据方案与Crazyflie设计.md` |
| 2 | 整理Crazyflie数据到data目录 | `data/scene2_crazyflie/` |
| 3 | (可选)安装OSATE运行flow latency分析 | 分析结果CSV |
| 4 | (可选)安装Ocarina运行调度分析 | 调度结果 |
| 5 | 用LLM注入矛盾 | 不一致样本 |
| 6 | 转成Data-Juicer JSONL | `data/scene2_crazyflie.jsonl` |

---

## 三、已下载的所有场景2数据汇总

| # | 数据 | 位置 | 格式 | 规模 |
|---|---|---|---|---|
| 1 | **Crazyflie AADL模型** | `/tmp/crazyflie_aadl/` | .aadl | 7模型+7库+5图表 |
| 2 | **Crazyflie SysML翻译版** | `/tmp/crazyflie_sysml/` | .sysml | 4文件 |
| 3 | **SimpleVehicleModel** | `/tmp/sysml_v2/` | .sysml | 1581行/152定义 |
| 4 | **Vehicle Analysis Demo** | `/tmp/sysml_v2/` | .sysml | 需求↔模型↔分析 |
| 5 | **MathWorks Simulink** | `/tmp/mathworks_simulink/` | .slx+.mat+.docx | 5模型+22参数+119段 |
| 6 | **Modelica标准库** | `/tmp/modelica_lib/` | .mo | 2674个模型 |
| 7 | **NASA fmdtools** | GitHub(未下载) | .py+.ipynb | 9个系统 |
| 8 | **孟超凡3个数据集** | Excel表格已有 | 文本↔时序 | 3个 |
