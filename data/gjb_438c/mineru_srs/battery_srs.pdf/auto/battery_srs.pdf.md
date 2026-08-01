密 级： 内部

阶 段： 需求分析阶段

版 次： V1.0

# TH-BatterySim-电池仿真模型 软件需求规格说明 产品型号-BatterySim

共 XX 页

太行项目组

2026-05-06

# TH-BatterySim-电池仿真模型 软件需求规格说明 产品型号-BatterySim

编制： 日期：

校对： 日期：

审核： 日期：

标审： 日期：

审定： 日期：

批准： 日期：

文件更改记录表
<table><tr><td rowspan=1 colspan=1>序号</td><td rowspan=1 colspan=1>版本号</td><td rowspan=1 colspan=1>页次</td><td rowspan=1 colspan=1>标记</td><td rowspan=1 colspan=1>处数</td><td rowspan=1 colspan=1>更改文件号</td><td rowspan=1 colspan=1>更改者</td><td rowspan=1 colspan=1>日期</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

## 目 录

1 范围 .. 1  
1.1 标识 .  
1.2 系统概述.  
1.3 文档概述.  
2 引用文档.  
3 需求 ... . 2  
3.1 要求的状态和方式 . 2  
3.1.1正常仿真状态 . 2  
3.1.2 初始化状态 . 2  
3.1.3参数配置状态 . 2  
3.2 软件能力需求. . 2  
3.2.1电池模型初始化功能. . 2  
3.2.2SOC 状态更新功能 . 3  
3.2.3电压计算功能 . 3  
3.2.4发热功率计算功能 . 3  
3.2.5离散步进功能 4  
3.3 软件外部接口需求 . 4  
3.3.1与调度器的接口 . 4  
3.3.2与外部系统的接口 4  
3.4 软件内部接口需求 4  
3.4.1数据结构接口 5  
3.4.2 函数调用接口. . 5  
3.5 软件内部数据需求 . 5  
3.6 适应性需求.. . 6  
3.7 安全性需求. . 6  
3.8 保密性需求. . 6  
3.9 软件环境需求. . 6  
3.10 计算机资源需求 .. 6  
3.10.1计算机硬件需求 .. 6  
3.10.2计算机硬件资源使用需求. . 7  
3.10.3计算机软件需求 . 7  
3.10.4计算机通信需求 .. 7  
3.11 软件质量因素.. . 7  
3.12 设计和实现约束 . 7  
3.13 人员需求. .. 8  
3.14 培训需求.. .. 8  
3.15 软件保障需求. .. 8  
3.16 其他需求.. .. 8  
3.17 验收、交付和包装需求（修改有关内容） . 8  
3.18 需求的优先顺序和关键程度. . 8  
4 合格性规定. . 8  
5 需求可追踪性. . 9  
6 注释 .. . 10

## 1 范围

## 1.1 标识

本 文 档 适 用 于 电 池 仿 真 模 型 软 件 （ BatterySim ）， 标 识 号 为TH/BatterySim-SRS-V1.0，版本号为 V1.0，发布号为 Release 1。该软件由太行项目组嵌入式软件研发部开发，用于嵌入式系统中的锂离子电池物理模型仿真。

a）文档标识号： $\mathrm { T H } / \mathrm { B a t t e r y S i m  – S R S  – V 1 . ~ } 0$

b）标题：软件需求规格说明

c）软件名称：TH-BatterySim-电池仿真模型

d）软件缩写：BatterySim

e）软件版本号：V1.0。

## 1.2 系统概述

电池仿真模型软件是一个用于嵌入式系统的离散时间电池模型，功能等价于EMATS 中的 physics-based battery block。软件采用 25ms 固定时间步长，基于Thevenin与Shepherd复合模型（电压源+内阻+极化项+指数区动态）实现电池状态的实时计算。

该软件应用于嵌入式电池管理系统（BMS）场景，为电池状态估计、热管理和能量管理提供精确的模型支撑。开发背景源于太行项目对嵌入式平台上高精度电池仿真的需求，要求在ARM Linux（内核 4.1.15，单核）平台上以25ms周期实时运行。软件由外部调度器驱动，每25ms调用一次步进函数。

软件的主要特性包括：基于物理的电池建模（非黑箱经验公式）、固定步长离散化保证实时性、无动态内存分配适合嵌入式部署、所有状态变量可解释和追踪。电池参数包括开路电压常数E0=800V、容量Q=50Ah、内阻 $\mathrm { R } { = } 0 . 0 1 2 \ \Omega$ 、极化系数 $\mathrm { M } { = } 0 . 0 0 4 \mathrm { A h } ^ { - 1 }$ 、指数区时间常数 $\mathrm { B } { = } 1 0 . 3 5 4 \mathrm { A h } ^ { - 1 }$ 、指数区幅值 $\mathrm { A } { = } 0 . 3 1 2 \mathrm { V }$ o

## 1.3 文档概述

本文档规定了电池仿真模型软件的需求规格，包括功能需求、性能需求、接口需求、环境需求和质量需求等方面。文档内容涵盖软件的范围、引用文档、详细需求说明、合格性规定、需求可追踪性和相关注释。

本文档为软件的设计、开发、测试和验收提供依据，适用于嵌入式软件开发人员、测试人员、系统集成人员和项目管理人员使用。本文档为内部文档，仅限太行项目组内部使用，不得对外传播。

## 2 引用文档

本章列出电池仿真模型软件需求规格说明编制所引用的标准和相关文档。

表 2-1 引用文件

<table><tr><td rowspan=1 colspan=1>序号</td><td rowspan=1 colspan=1>名称</td><td rowspan=1 colspan=1>版本</td><td rowspan=1 colspan=1>发布日期</td><td rowspan=1 colspan=1>来源</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>《GJB 438C 软件文档编制规范》</td><td rowspan=1 colspan=1>438C</td><td rowspan=1 colspan=1>2024-01-01</td><td rowspan=1 colspan=1>相关标准库</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>《GJB 5000B军用软件能力成熟度模型》</td><td rowspan=1 colspan=1>5000B</td><td rowspan=1 colspan=1>2017-01-01</td><td rowspan=1 colspan=1>相关标准库</td></tr></table>

## 3 需求

## 3.1 要求的状态和方式

电池仿真模型软件在以下状态下运行：

## 3.1.1 正常仿真状态

软件在正常仿真状态下运行，由外部调度器以 25ms 周期调用 battery\_step()函数，执行电池状态更新计算，输出电压、SOC 和发热功率。软件在此状态下应满足所有功能需求和性能需求。

## 3.1.2 初始化状态

软件在初始化状态下运行，由系统启动时调用 battery\_init()函数，完成电池模型参数的设定和初始状态的配置（如 SOC\_init=1.0）。初始化完成后转入正常仿真状态。

## 3.1.3 参数配置状态

软件在参数配置状态下，允许修改电池模型参数（E0、Q、R、M、B、A等），参数修改后需重新初始化才能生效。此状态用于适配不同型号的锂离子电池。

## 3.2 软件能力需求

电池仿真模型软件的核心能力需求包括以下功能模块：

## 3.2.1 电池模型初始化功能

功能名称：电池模型初始化

功能描述：完成电池模型参数的设定和内部状态变量的初始化。设定电池模型 参 数 （ E0=800V, Q=50Ah, R=0.012 Ω , $\mathrm { M } { = } 0 . 0 0 4 \mathrm { A h } ^ { \mathrm { ~ - ~ } 1 }$ 2 $\mathrm { B } { = } 1 0 . 3 5 4 \mathrm { A h } ^ { \mathrm { ~ - ~ } 1 }$ ，

A=0.312V），初始化状态变量 it=0（已放电容量），SOC=SOC\_init=1.0。

输入：电池模型参数（可选，提供默认值）

输出：初始化完成的电池模型状态

性能要求：初始化时间不超过1ms

约束条件：不使用动态内存分配（malloc），所有参数和状态变量存储在静态结构体中

## 3.2.2SOC 状态更新功能

功能名称：SOC状态更新

功能描述：每个离散时间步长（dt=0.025s）根据输入电流更新已放电容量it和荷电状态SOC。采用离散化积分公式： $\mathrm { i t ( k { + } 1 ) { = } i t ( k ) { + } I \_ o u t ^ { * } d t / 3 6 0 0 , S O C { = } 1 { \ - } i t / Q }$ o

输入：电流I\_out（A，放电为正）、时间步长dt=0.025s

输出：更新后的SOC值（0\~1范围）

性能要求：计算时间不超过0.1ms

约束条件：放电时SOC应单调下降，SOC不应小于0

## 3.2.3 电压计算功能

功能名称：电池电压计算

功能描述：基于Thevenin+Shepherd复合模型计算电池端电压。电压表达式包含四项：开路电压项（E0）、内阻压降项 $( - \mathrm { { I \_ o u t ^ { * } R } } )$ ）、极化项 $\left( \mathbf { \nabla } _ { - } \mathbf { M } ^ { * } \mathrm { i t } \right)$ ）、指数区动态项 $\left( - \mathbf { A } ^ { * } \mathrm { e x p } ( - \mathbf { B } ^ { * } \mathrm { i t } ) \right)$ ）。

输入：电流I\_out、当前已放电容量it

输出：电池端电压V（V）

性能要求：计算时间不超过0.1ms

约束条件：电压不应出现负值，电流为零时电压应接近开路电压

## 3.2.4 发热功率计算功能

功能名称：发热功率计算

功能描述：计算电池模型的焦耳热损耗功率。

输入：电流 I\_out（A）

输出：发热功率P\_loss（W），计算公式为 $\mathrm { P } \_ { \mathrm { l o s s } = \mathrm { I } \_ { 0 } \mathrm { u t } ^ { 2 } } * \mathrm { R }$

性能要求：计算时间不超过0.05ms

约束条件：发热功率不应为负值

## 3.2.5 离散步进功能

功能名称：离散步进计算

功能描述：每 25ms 执行一次完整的模型步进计算，依次完成 SOC 更新、电压计算和发热功率计算。该函数为外部调度器的唯一调用入口。

输入：电流 I\_out（A）

输出：更新后的电池状态（电压 V、SOC、发热功率 P\_loss）

性能要求：单步执行总时间不超过1ms（留有充足余量用于25ms周期调度）

约束条件：函数内部不包含任何等待或时间控制代码，仅执行一步状态更新；不使用动态内存分配

## 3.3 软件外部接口需求

电池仿真模型软件的接口需求如下：

## 3.3.1 与调度器的接口

软件与外部调度器通过函数调用接口交互。调度器负责以 25ms 周期调用battery\_step(I\_out)函数，传入当前电流值。软件通过 battery\_init()函数接收初始化命令 。调度 器通 过 getter 函数 （battery\_get\_voltage() 、battery\_get\_soc() 、battery\_get\_ploss()）读取模型输出。

## 3.3.2 与外部系统的接口

电池仿真模型作为嵌入式BMS系统的核心组件，通过函数接口与上层应用交互。软件不涉及网络通信、数据库或文件系统等外部系统接口，所有数据交互通过内存中的函数调用完成。

## 3.4 软件内部接口需求

电池仿真模型软件内部接口需求如下：

1. 初始化模块与步进计算模块接口：初始化模块通过共享结构体（battery\_state\_t）向步进计算模块传递初始状态和模型参数，结构体包含 it、SOC、E0、Q、R、M、B、A等字段。

2. SOC更新与电压计算接口：SOC更新模块将计算得到的it值存入共享结构体，电压计算模块从结构体读取it值进行电压计算。

3. 电压计算与发热功率计算接口：两者均从共享结构体读取当前电流值，各自独立计算并写回结果。

4. 步进函数与 getter 接口：步进函数更新共享结构体中的所有输出变量，

getter函数从共享结构体读取最新的输出值返回给外部调用者。

## 3.4.1 数据结构接口

电池仿真模型采用统一的 battery\_state\_t 结构体作为内部数据交换接口，该结构体定义在 battery\_model.h 头文件中。所有模块通过该结构体共享状态数据，结构体字段包括：

\- 已放电容量it（double类型，单位Ah）

\- 荷电状态 soc（double 类型，范围 0\~1）

\- 端电压 voltage（double 类型，单位 V）

\- 发热功率 p\_loss（double 类型，单位 W）

\- 模型参数（E0、Q、R、M、B、A）

\- 初始 SOC（soc\_init）

## 3.4.2 函数调用接口

电池仿真模型对外提供的函数接口定义在battery\_model.h中，包括：

1. void battery\_init(void)：初始化电池模型，设定默认参数和初始状态

2. void battery\_step(double I\_out, double dt)：执行一步模型计算，输入电流和时间步长

3. double battery\_get\_voltage(void)：获取当前电压

4. double battery\_get\_soc(void)：获取当前 SOC

5. double battery\_get\_ploss(void)：获取当前发热功率

所有函数均为同步调用，无阻塞操作，适合在实时系统中使用。

## 3.5 软件内部数据需求

电池仿真模型内部数据需求如下：

1. 电池状态结构体（battery\_state\_t）：存储模型的所有状态变量和参数，包括已放电容量 it、SOC、端电压 voltage、发热功率 p\_loss、模型参数（E0=800V,$\mathrm { Q } { = } 5 0 \mathrm { A h } , \mathrm { R } { = } 0 . 0 1 2 \ \Omega$ ， $\mathrm { M } { = } 0 . 0 0 4 \mathrm { A h } ^ { - 1 }$ $\mathrm { B } { = } 1 0 . 3 5 4 \mathrm { A h } ^ { - 1 }$ $\mathrm { A } { = } 0 . 3 1 2 \mathrm { V } \ )$ ）、初始 SOC$( \mathrm { s o c \_ i n i t { = } } 1 . 0 )$ 。

2. 离散时间步长常量：DT=0.025s，作为模型的时间基准。

3. 所有内部变量采用 double 类型（IEEE 754 双精度浮点数），保证计算精度。

4. 数据范围约束： $\mathrm { S O C } \in [ 0 , 1 ]$ ，电压 $\mathrm { v } { \geqslant } 0$ ，发热功率 $\mathrm { P } \_ { \mathrm { l o s s } } { \geqslant } 0$ ，已放电容量 $\mathrm { i t } \in [ 0 , \mathrm { Q } ]$

## 3.6 适应性需求

电池仿真模型软件作为嵌入式 C 语言库组件，无需独立安装。软件以源代码形式提供，与调度器应用程序一起编译链接。模型参数通过 battery\_init()或宏定义配置，支持适配不同型号的锂离子电池。

## 3.7 安全性需求

电池仿真模型软件的安全性需求如下：

1. 输入验证：对输入电流进行合理性检查，电流值应在物理合理范围内（如不超过电池最大充放电电流的2倍）。对异常输入应进行限幅处理而非直接拒绝。

2. 状态保护：当SOC接近0时应产生告警，电压计算结果不应出现负值或数值爆炸。对exp()函数的输入应进行限幅，防止浮点溢出。

3. 数值稳定性：离散化模型应保证长时间运行的数值稳定性，不应出现状态变量的发散或振荡。

4. 内存安全：不使用动态内存分配，所有变量使用静态存储，避免内存泄漏和野指针问题。

## 3.8 保密性需求

电池仿真模型软件为嵌入式系统内部组件，不涉及用户权限管理、数据加密、审计日志或访问控制等保密性需求。软件在嵌入式平台内部运行，不处理敏感或机密数据，不与外部网络通信。

## 3.9 软件环境需求

电池仿真模型软件的运行环境需求如下：

1. 目标平台：ARM Linux（内核 4.1.15，单核处理器）

2. 编译器：GCC（支持C99标准）或ARM交叉编译工具链

3. 运行库：仅依赖标准C数学库（math.h），不依赖第三方库或操作系统特定 API

4. 内存需求：运行时内存占用不超过1KB（单个结构体实例）

5. 开发环境：支持在x86 PC上进行仿真测试，目标平台为ARM嵌入式系统

## 3.10 计算机资源需求

## 3.10.1 计算机硬件需求

目标处理器：ARM架构单核处理器，主频不低于400MHz

内存：最低要求32MB系统内存

存储空间：目标代码大小不超过10KB

浮点运算：需支持硬件浮点运算单元（FPU）或软浮点库

## 3.10.2 计算机硬件资源使用需求

CPU 使用：单步计算时间不超过 1ms（在 400MHz ARM 处理器上），CPU占用率低于5%（以25ms周期运行时）

内存使用：运行时内存占用不超过1KB，无动态内存分配

栈使用：函数调用深度不超过3层，栈使用量不超过512字节

## 3.10.3 计算机软件需求

编译器：GCC 4.9+或 ARM 交叉编译器（arm-linux-gnueabihf-gcc），支持 C99标准

标准库：libc数学库（libm）

构建工具：GNU Make

## 3.10.4 计算机通信需求

电池仿真模型软件不需要网络通信功能，所有数据交互通过本地函数调用完成，无计算机通信需求。

## 3.11 软件质量因素

电池仿真模型软件的质量因素要求如下：

1. 正确性：模型计算结果应与 EMATS 中的 physics-based battery block 输出一致，电压计算误差不超过0.1%，SOC计算误差不超过0.5%。

2. 可靠性：软件应能长时间稳定运行（至少连续运行2小时），无内存泄漏和状态异常。

3. 实时性：单步计算时间不超过1ms，满足25ms周期调度的实时性要求。

4. 可维护性：代码结构清晰，模块化设计，头文件与源文件分离，所有参数可配置。

5. 可移植性：仅使用标准C99语法，不依赖平台特定API，可在x86 和ARM平台间移植。

6. 数值稳定性：连续运行100000步以上，状态变量不应出现数值发散或溢出。

## 3.12 设计和实现约束

电池仿真模型软件的设计和实现约束如下：

1. 编程语言：仅使用标准C99，不允许使用高级库或第三方框架。

2. 内存管理：禁止使用动态内存分配（malloc/free），所有变量使用静态存储。

3. 模型约束：不允许省略极化项或指数区项，不允许使用黑箱经验公式，所有状态必须可解释。

4. 接口约束：步进函数不包含任何等待或时间控制代码，仅执行一步状态更新。

5. 变量约束：所有变量使用定长类型，结构体内存布局确定。

## 3.13 人员需求

电池仿真模型软件开发人员需具备嵌入式 C 语言编程能力、电池模型基础知识和实时系统开发经验。使用人员需了解电池模型参数的含义和配置方法。

## 3.14 培训需求

本软件不需要特殊的培训需求，开发和使用人员可通过阅读本文档和源代码注释快速上手。

## 3.15 软件保障需求

软件以源代码形式交付，包含头文件（.h）、源文件（.c）和验证测试代码。交付物还包括模型参数说明和验证结果报告。

## 3.16 其他需求

无其他特殊需求。

## 3.17 验收、交付和包装需求（修改有关内容）

软 件 以 源 代 码 形 式 交 付 ， 包 含 头 文 件 （ battery\_model.h ）、 源 文 件（battery\_model.c）、验证测试程序和Makefile。交付时需提供恒流放电测试、脉冲电流测试和极端情况测试的验证结果报告。

## 3.18 需求的优先顺序和关键程度

离散步进计算功能和电压计算功能为核心关键需求，SOC 状态更新和发热功率计算为高优先级需求，参数配置状态为一般需求。

## 4 合格性规定

电池仿真模型软件的合格性方法如下表所示：

<table><tr><td colspan="1" rowspan="1">需求名称</td><td colspan="1" rowspan="1">需求的唯一标识</td><td colspan="1" rowspan="1">本文档中的章节号</td><td colspan="1" rowspan="1">合格性方法</td><td colspan="1" rowspan="1">合格性级别</td></tr><tr><td colspan="1" rowspan="1">电池模型初始化</td><td colspan="1" rowspan="1">REQ-3.2.1</td><td colspan="1" rowspan="1">3.2.1</td><td colspan="1" rowspan="1">单元测试</td><td colspan="1" rowspan="1">关键</td></tr><tr><td colspan="1" rowspan="1">SOC 状态更新</td><td colspan="1" rowspan="1">REQ-3.2.2</td><td colspan="1" rowspan="1">3.2.2</td><td colspan="1" rowspan="1">单元测</td><td colspan="1" rowspan="1">关键</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1"></td><td colspan="1" rowspan="1">试+对比验证</td><td colspan="1" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">电压计算</td><td colspan="1" rowspan="1">REQ-3.2.3</td><td colspan="1" rowspan="1">3.2.3</td><td colspan="1" rowspan="1">对比验证（与EMATS基准）</td><td colspan="1" rowspan="1">关键</td></tr><tr><td colspan="1" rowspan="1">发热功率计算</td><td colspan="1" rowspan="1">REQ-3.2.4</td><td colspan="1" rowspan="1">3.2.4</td><td colspan="1" rowspan="1">单元测试</td><td colspan="1" rowspan="1">一般</td></tr><tr><td colspan="1" rowspan="1">离散步进计算</td><td colspan="1" rowspan="1">REQ-3.2.5</td><td colspan="1" rowspan="1">3.2.5</td><td colspan="1" rowspan="1">集成测试+性能测试</td><td colspan="1" rowspan="1">关键</td></tr><tr><td colspan="5" rowspan="1">注：合格性方法：a) A-演示：对CSCI（或部分CSCI）进行直接可以观察的功能操作，不需要使用复杂或专用的测试设备；b) B-测试；c) C-分析；d) D-检查：对 CSCI的编码、文档等进行直观检查等；e) E-特殊方法（如：专用工具、技术、过程、设施、验收限制）。合格性级别：a) a-配置项：在 CSCI中发现的质量问题；b) b-系统集成：在系统集成时发现的问题；c) c-系统：在系统中发现的质量问题；d) d-系统安装：在系统安装时发现的质量问题。</td></tr></table>

## 5 需求可追踪性

本章建立电池仿真模型软件需求与系统需求之间的双向追踪关系。

表5-1 需求的正向追踪性
<table><tr><td rowspan=1 colspan=2>《XXX课题可行性研究报告》中的指标</td><td rowspan=1 colspan=2>软件需求</td></tr><tr><td rowspan=1 colspan=1>指标内容</td><td rowspan=1 colspan=1>章节号</td><td rowspan=1 colspan=1>需求名称</td><td rowspan=1 colspan=1>章节号</td></tr><tr><td rowspan=1 colspan=1>电池模型等价于EMATSphysics-based battery block</td><td rowspan=1 colspan=1>总体目标</td><td rowspan=1 colspan=1>电压计算功能</td><td rowspan=1 colspan=1>3.2.3</td></tr><tr><td rowspan=1 colspan=1>25ms 离散时间步长</td><td rowspan=1 colspan=1>总体目标</td><td rowspan=1 colspan=1>离散步进功能</td><td rowspan=1 colspan=1>3.2.5</td></tr><tr><td rowspan=1 colspan=1>SOC 范围 0~1</td><td rowspan=1 colspan=1>总体目标</td><td rowspan=1 colspan=1>SOC 状态更新功能</td><td rowspan=1 colspan=1>3.2.2</td></tr><tr><td rowspan=2 colspan=1>若存在一对多则此形式表达</td><td rowspan=2 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

表5-2需求的逆向追踪性
<table><tr><td rowspan=1 colspan=2>软件需求</td><td rowspan=1 colspan=2>《XXXXX课题可行性研究报告》中的指标</td></tr><tr><td rowspan=1 colspan=1>需求名称</td><td rowspan=1 colspan=1>指标内容</td><td rowspan=1 colspan=1>指标内容</td><td rowspan=1 colspan=1>章节号</td></tr><tr><td rowspan=1 colspan=1>电压计算功能</td><td rowspan=1 colspan=1>基于Thevenin+Shepherd模型计算电压</td><td rowspan=1 colspan=1>电池模型等价于EMATSphysics-based batteryblock</td><td rowspan=1 colspan=1>总体目标</td></tr><tr><td rowspan=1 colspan=1>离散步进功能</td><td rowspan=1 colspan=1>25ms 固定步长离散仿真</td><td rowspan=1 colspan=1>25ms 离散时间步长</td><td rowspan=1 colspan=1>总体目标</td></tr><tr><td rowspan=1 colspan=1>SOC 状态更新功能</td><td rowspan=1 colspan=1>SOC计算范围0~1</td><td rowspan=1 colspan=1>SOC 范围 0~1</td><td rowspan=1 colspan=1>总体目标</td></tr></table>

## 6 注释

术语定义：

SOC（State of Charge）：电池荷电状态，表示电池剩余容量占额定容量的比例，范围0\~1。

开路电压（Open Circuit Voltage, OCV）：电池在无负载时的端电压。

内阻（Internal Resistance）：电池内部等效电阻，单位Ω。

极化（Polarization）：电池充放电过程中电极表面的电化学极化现象。

指数区（Exponential Zone）：电池放电曲线中电压快速变化的区域。

Thevenin模型：基于戴维南等效电路的电池模型，由电压源和阻抗网络组成。

Shepherd模型：基于经验公式的电池放电模型，包含极化和指数衰减项。

缩略语：

SOC - State of Charge（荷电状态）

BMS - Battery Management System（电池管理系统）

EMATS - 电池仿真基准平台

SRS - Software Requirements Specification（软件需求规格说明）

DT - Discrete Time step（离散时间步长）