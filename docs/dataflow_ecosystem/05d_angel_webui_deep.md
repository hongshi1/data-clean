# Angel 与 DataFlow-WebUI 代码级深度分析

> 调研时间：2026-07-30 | 调研方法：DeepWiki 40+ 页抓取 + 本地源码精读 + arXiv 论文  
> Angel：腾讯+北大联合设计，6.8k stars，分布式 ML 与图计算平台  
> DataFlow-WebUI：OpenDCAI，129 stars，DataFlow 可视化工作台，支持 NL2Pipeline  
> 本篇补足前序调研"仅读 README"的缺口，聚焦架构与代码级细节

---

## 目录

- [第一部分：Angel 分布式 ML 平台](#第一部分angel-分布式-ml-平台)
  - [1. 架构与设计哲学](#1-架构与设计哲学)
  - [2. 参数服务器核心](#2-参数服务器核心)
  - [3. Spark on Angel](#3-spark-on-angel)
  - [4. 编程模型](#4-编程模型)
  - [5. 算法实现](#5-算法实现)
  - [6. 部署](#6-部署)
- [第二部分：DataFlow-WebUI 可视化工作台](#第二部分dataflow-webui-可视化工作台)
  - [7. 本地 Gradio 界面（源码精读）](#7-本地-gradio-界面源码精读)
  - [8. 独立 WebUI 仓库](#8-独立-webui-仓库)
  - [9. DataFlow-Harness 论文](#9-dataflow-harness-论文)
- [第三部分：对 SRS 项目的深度应用价值](#第三部分对-srs-项目的深度应用价值)

---

# 第一部分：Angel 分布式 ML 平台

> 来源：DeepWiki `Angel-ML/angel` 仓库，最后索引于 2025-09-05，commit `2f2a8956`  
> 涉及 40+ 个 DeepWiki 页面，下文逐节标注页面与源码路径

## 1. 架构与设计哲学

> DeepWiki 页面：`1.1-architecture-and-design-philosophy`、`1.2-key-components`  
> 核心源码：`angel-ps/core/src/main/java/com/tencent/angel/conf/AngelConf.java`、`master/MasterService.java`、`client/AngelClient.java`

### 1.1 Master-Worker-PS 三角架构

Angel 围绕**参数服务器（Parameter Server, PS）范式**构建，核心是一个三角架构：计算与参数存储分离，使 ML 可跨大集群扩展。

```
                    ┌─────────────────────────┐
                    │      AngelClient        │  应用提交入口
                    │  (YarnClient / K8sClient)│
                    └────────────┬─────────────┘
                                 │ 提交作业
                                 ▼
                    ┌─────────────────────────┐
                    │      MasterService       │  中央协调器
                    │  (App / MasterProtocol)  │
                    │  生命周期管理 + 状态持久化  │
                    └──┬───────────────┬───────┘
            分配Worker   │               │  分配PS
            容器         │               │  容器
           ┌────────────┴──┐         ┌───┴────────────┐
           │               │         │                 │
    ┌──────▼──────┐ ┌──────▼──────┐  ┌▼──────────┐ ┌──▼──────────┐
    │  Worker 0   │ │  Worker 1   │  │  PS 0      │ │  PS 1       │
    │  (计算节点)  │ │  (计算节点)  │  │ (参数存储)  │ │ (参数存储)   │
    │  TrainTask  │ │  TrainTask  │  │  Matrix    │ │  Matrix     │
    │  DataBlock  │ │  DataBlock  │  │  Partitions│ │  Partitions │
    └──────┬──────┘ └──────┬──────┘  └▲──────────┘ └▲──────────┘
           │               │          │             │
           │   PSAgent ─────┼──────────┘             │
           │   (pull/push/  └────────────────────────┘
           │    clock RPC)
           ▼
      HDFS (训练数据 + 模型Checkpoint)
```

**关键设计要点**（来源 `docs/overview/design_philosophy.md`）：

- **Master** 作为中央协调器，实现 `MasterProtocol`，处理来自 Client、Worker、PS 的 RPC 请求，管理整个应用生命周期，并将应用状态持久化到 HDFS。
- **Worker** 是无状态计算节点，负责读取 `DataBlock`、计算梯度、通过 `PSAgent` 与 PS 通信。Worker 失败后可重新拉取参数并恢复迭代。
- **PS（Parameter Server）** 是有状态参数存储节点，持有 `Matrix` 分区，通过心跳向 Master 汇报健康状态，周期性向 HDFS 写 Checkpoint 实现容错。

### 1.2 双模式运行

Angel 的灵活性源于其双模式架构（来源 `AngelConf.java:197-204`）：

| 模式 | 配置值 | 架构 | 适用场景 |
|------|--------|------|----------|
| **ANGEL_PS_WORKER** | `ANGEL_RUNNING_MODE=ANGEL_PS_WORKER` | 完整生态：Master + PS + Worker | 原生 Angel 算法，最高性能 |
| **ANGEL_PS_SERVICE** | `ANGEL_RUNNING_MODE=ANGEL_PS_SERVICE` | 仅 PS 服务模式 | 外部计算平台集成（Spark、TensorFlow） |

- **ANGEL_PS_WORKER**：Angel 自带 Worker，算法逻辑通过 `TrainTask` 在 Worker 端执行，PS 负责参数同步。这是原生 Angel 算法的首选，性能最高。
- **ANGEL_PS_SERVICE**（即 `ANGEL_PS`）：Angel 只启动 PS 集群，Worker 由外部平台（如 Spark Executor）充当。Spark on Angel 即基于此模式，Spark 负责 RDD 数据并行，Angel PS 负责模型并行与同步。

### 1.3 "以模型为中心"的设计理念

Angel 通过若干关键抽象实现"以模型为中心"的灵活性（来源 `design_philosophy.md:36-69`）：

1. **MLModel/PSModel 抽象**：将算法逻辑与分布式参数管理分离。`MLModel` 是 `PSModel` 的容器，`PSModel` 封装了分布式矩阵的 pull/push 操作。
2. **Task 抽象**：通过 `BaseTask` 实现支持自定义计算逻辑。
3. **PSF（Parameter Server Functions）**：允许服务端自定义操作，无需修改 Angel 核心代码即可扩展服务端计算。
4. **InputFormat 抽象**：通过 Hadoop 的 `InputFormat` 支持自定义数据格式。

### 1.4 故障容错架构

| 组件 | 容错机制 | 实现方式 |
|------|----------|----------|
| **Parameter Server** | Checkpoint 恢复 | 周期性 HDFS 快照（`ANGEL_PS_BACKUP_INTERVAL_MS` 默认 300s） |
| **Worker** | 无状态重启 | 重新拉取参数并恢复迭代 |
| **Master** | 状态持久化 | 应用状态写入 HDFS |
| **慢节点检测** | 性能监控 | 自动重新调度 Worker |
| **PS 复制** | 主从复制 | `ANGEL_PS_HA_REPLICATION_NUMBER`，同步/异步复制 + 自动故障转移 |

### 1.5 部署架构

| 部署模式 | 资源管理器 | 客户端实现 | 用途 |
|----------|------------|------------|------|
| **YARN** | Apache YARN | `AngelYarnClient` | 生产集群 |
| **Local** | 本地进程管理 | 直接执行 | 开发/测试 |
| **Kubernetes** | Kubernetes | `AngelKubernetesClient` + `KubernetesClusterManager` | 容器编排 |

K8s 部署中，Master Pod 运行 `AngelApplicationMaster`，每个 PS 运行在独立 Pod（`KubernetesParameterServerApp`），Worker Pod 为可选（`KubernetesWorkerApp`），PS 位置发现通过 K8s Service 实现。

---

## 2. 参数服务器核心

> DeepWiki 页面：`2-angel-parameter-server`、`2.1-ps-core-concepts`、`2.3-client-interface`、`2.4-parameter-server-functions`  
> 核心源码：`ml/matrix/MatrixContext.java`、`ml/matrix/RowType.java`、`ps/storage/partitioner/RangePartitioner.java`、`docs/design/psf_get.md`、`psf_update.md`

### 2.1 PS 核心概念：Matrix / PSModel / Partition

Angel PS 的核心抽象是**分布式矩阵**，通过 `MatrixContext` 定义蓝图，自动分区并分布到多个 PS 实例。

#### MatrixContext 矩阵上下文

`MatrixContext`（`ml/matrix/MatrixContext.java:52-295`）封装了创建分布式矩阵所需的全部信息：

| 属性 | 类型 | 用途 |
|------|------|------|
| `name` | String | 矩阵可读标识符 |
| `rowNum` | int | 行数 |
| `colNum` | long | 列数（-1 表示索引范围） |
| `indexStart/indexEnd` | long | 稀疏矩阵列索引范围 |
| `rowType` | RowType | 存储格式与数据类型 |
| `partitionerClass` | Class | 分区策略类 |
| `maxRowNumInBlock` | int | 每分区行数 |
| `maxColNumInBlock` | long | 每分区列数 |

#### RowType 存储类型

`RowType` 枚举（`ml/matrix/RowType.java:24-265`）定义了数据类型 × 存储格式 × 键类型的组合：

| RowType | 数据类型 | 存储 | 键类型 | 用途 |
|---------|----------|------|--------|------|
| `T_DOUBLE_DENSE` | double | dense | int | 小型稠密特征向量 |
| `T_FLOAT_SPARSE` | float | sparse | int | 稀疏特征向量 |
| `T_DOUBLE_SPARSE_LONGKEY` | double | sparse | long | 大规模稀疏模型 |
| `T_ANY_INTKEY_SPARSE` | 自定义 | sparse | int | 复杂自定义数据类型 |

存储格式选择显著影响内存与性能：**Dense** 用定长数组，稠密数据高效；**Sparse** 用哈希表或排序数组，稀疏数据省内存；**Component** 为特定算法优化的布局。

#### Range Partitioner 范围分区

默认分区策略 `RangePartitioner`（`ps/storage/partitioner/RangePartitioner.java:72-139`）将矩阵按行列范围切成连续的矩形块，保证相关元素共置。分区大小基于以下因素计算最优值：

- 可用 PS 实例数
- 配置的分区大小上限（`ANGEL_MODEL_PARTITIONER_PARTITION_SIZE` 默认 500000 元素/分区）
- 矩阵稀疏度（`validIndexNum`）
- 内存约束

#### 分区元数据层级

```
MatrixMeta (矩阵元数据)
  └── PartitionMeta (分区元数据, PartitionMeta.java:32-199)
        ├── 空间边界: 行列范围
        ├── 服务器分配: 哪个 PS 存储此分区
        ├── 复制信息: 主从关系
        └── 状态跟踪: loading/saving/recovery
```

### 2.2 Client 接口

`AngelClient`（`client/AngelClient.java`）是控制 PS 生命周期与操作的主接口，屏蔽了分布式管理的复杂性。

| 方法 | 功能 | 配置依赖 |
|------|------|----------|
| `startPSServer()` | 启动 PS 集群 | `ANGEL_PS_NUMBER`, `ANGEL_PS_MEMORY_GB` |
| `loadModel(MLModel)` | 将模型加载到 PS 内存 | `ANGEL_LOAD_MODEL_PATH` |
| `saveModel(MLModel)` | 从 PS 持久化模型 | `ANGEL_SAVE_MODEL_PATH` |
| `createMatrices()` | 初始化分布式矩阵 | 矩阵分区设置 |
| `runTask(TaskClass)` | 启动 Worker 进程执行计算 | — |
| `waitForCompletion()` | 阻塞直到训练/预测完成 | — |

**PS 初始化流程**（`MasterService.java:285-372`）：Client 提交 → Master 创建 PS 容器 → PS 向 Master 注册 → Master 分配矩阵分区 → Client 的 `PSModel` 绑定到对应 PS。

### 2.3 PSModel 操作分类

`PSModel` 是客户端操作分布式矩阵的统一接口（`docs/apis/PSModel.md:1-258`），操作分为五大类：

| 类别 | 方法 | 说明 |
|------|------|------|
| **Pull（拉取）** | `getRow()`, `getRows()`, `get(GetFunc)` | 从 PS 检索参数 |
| **Push（推送）** | `increment(delta)`, `update(UpdateFunc)` | 更新 PS 上的参数 |
| **Sync（同步）** | `syncClock()`, `flush()` | 控制同步：`clock()` 推进逻辑时钟并刷新更新，`flush()` 仅刷新不推进时钟 |
| **I/O** | `setLoadPath()`, `setSavePath()` | 模型持久化 |
| **Behavior** | `setAverage()`, `setHogwild()`, `setRowType()` | 配置存储/更新行为：Average 模式下 PS 对多 Worker 梯度取平均，Hogwild 模式下异步无锁更新 |

### 2.4 参数服务器函数 PSF

> DeepWiki 页面：`2.4-parameter-server-functions`  
> 源码：`docs/design/psfFunc.md`、`psf_get.md`、`psf_update.md`

PSF 是 Angel 的扩展性核心：允许自定义操作**直接在 PS 实例上执行**，而非将全部参数传输到 Worker，从而减少网络通信并支持模型并行的执行模式。

#### PSF 请求-响应流程

```
Worker 端                      PS 端
───────                       ──────
GetParam/UpdateParam
  │ split()  ──────────────►  分区级请求
  │                           │
  │                    GetFunc.partitionGet()  (每个分区独立执行)
  │                    UpdaterFunc.partitionUpdate()
  │                           │
  │  ◄──────────────────  分区级结果
  │ GetFunc.merge()  (合并分区结果)
  │ UpdateFunc: Future<VoidResult> (异步等待完成)
  ▼
最终结果
```

#### GetFunc（读取计算型）

`GetFunc` 检索分布式参数的计算结果。每个 GetFunc 定义分区级计算和结果合并逻辑（`docs/design/psf_get.md:29-38`）。推荐继承 `AggrFunc` 简化开发。

**内置 GetFunc**：

| 函数 | 用途 | 返回类型 |
|------|------|----------|
| `Sum` | 行元素求和 | double |
| `Max`/`Min` | 行最大/最小值 | double |
| `Amax`/`Amin` | 绝对值最大/最小 | double |
| `Dot` | 向量内积 | double |
| `Nnz` | 非零元素计数 | long |
| `Nrm2` | L2 范数 | double |

#### UpdateFunc（更新型）

`UpdaterFunc` 修改分布式参数，异步执行返回 `Future<VoidResult>`（`docs/design/psf_update.md:24-33`）。

| 类别 | 用途 | 示例函数 |
|------|------|----------|
| 算术运算 | 逐元素操作 | `Add`, `Sub`, `Mul`, `Div` |
| 数学函数 | 函数应用 | `Exp`, `Log`, `Sqrt`, `Pow` |
| 初始化 | 参数设置 | `RandomUniform`, `RandomNormal`, `Fill` |
| 数据移动 | 矩阵操作 | `Copy`, `Axpy`, `Scale` |

#### 自定义 PSF 示例（Sum 实现模式）

```java
// GetFunc 实现模式 (继承 AggrFunc)
public class Sum extends AggrFunc {
    // 1. partitionGet: 在每个分区上执行求和
    public AggrResult partitionGet(PartitionGetParam param) {
        // 读取分区行数据，计算局部和
    }
    // 2. merge: 合并各分区结果
    public AggrResult merge(List<AggrResult> results) {
        // 累加各分区和
    }
}

// UpdaterFunc 实现模式 (RandomUniform)
public class RandomUniform extends UpdaterFunc {
    public void partitionUpdate(PartitionUpdateParam param) {
        // 在分区上用均匀分布初始化参数
    }
}

// 通过 PSModel 调用
double sum = psModel.get(new Sum(matrixId, rowIndex));
psModel.update(new RandomUniform(matrixId, rowIndex, min, max));
```

### 2.5 一致性模型与配置

**核心 PS 配置参数**（`AngelConf.java:802-862`）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ANGEL_PS_NUMBER` | 1 | PS 实例数 |
| `ANGEL_PS_MEMORY_GB` | 4 | 每 PS 内存（GB） |
| `ANGEL_PS_CPU_VCORES` | 1 | 每 PS CPU 核数 |
| `ANGEL_PS_HEARTBEAT_INTERVAL_MS` | 5000 | PS 心跳频率 |
| `ANGEL_PS_BACKUP_INTERVAL_MS` | 300000 | 模型 Checkpoint 间隔 |
| `ANGEL_PS_HA_REPLICATION_NUMBER` | — | PS 复制因子 |
| `ANGEL_STALENESS` | — | 同步陈旧度（BSP/SSP/Asynchronous） |

`ANGEL_STALENESS` 控制一致性模型：值为 0 时为 BSP（严格同步），值 > 0 时为 SSP（允许有限陈旧度的异步），这是 Angel 支撑大规模训练的关键调优参数。

---

## 3. Spark on Angel

> DeepWiki 页面：`3.1-spark-on-angel-architecture`、`3.2-pscontext-and-psvector`  
> 核心源码：`spark-on-angel/core/src/main/scala/com/tencent/angel/spark/context/AngelPSContext.scala`、`PSContext.scala`、`models/PSVector.scala`、`models/PSMatrix.scala`

### 3.1 双应用架构

Spark on Angel（SONA）的核心创新是**双应用部署模型**：Spark 和 Angel 作为两个独立的 YARN 应用协同工作。

```
        YARN ResourceManager
        ┌──────────────────────────────────────┐
        │                                      │
   ┌────┴─────────────────┐   ┌────────────────┴────┐
   │  Spark Application    │   │  Angel PS Application│
   │  (独立资源管理)         │   │  (独立资源管理)        │
   │                       │   │                      │
   │  SparkDriver          │   │  AngelMaster         │
   │   └─ PSContext        │   │   └─ ParameterServer ×N│
   │  SparkExecutor ×M     │   │     (Matrix 分区)     │
   │   └─ PSAgent ─────────┼───┼─►  RPC 通信           │
   │      (pull/push)      │   │                      │
   └───────────────────────┘   └──────────────────────┘
```

**双应用架构的优势**：
- **独立资源管理**：各自管理资源，互不干扰
- **故障隔离**：一个应用的失败不直接影响另一个
- **独立扩展**：PS 和 Spark 组件可独立扩缩容
- **通信高效**：Executor 与 PS 直接通信

### 3.2 PSContext：集成桥梁

`PSContext` 是 Spark 应用管理 Angel PS 应用的主接口，采用单例模式（`spark-on-angel/core/.../context/PSContext.scala:77-108`）。

**Driver 端与 Executor 端初始化差异**：

| 端 | 行为 |
|----|------|
| **Driver 端** | 创建并启动 Angel PS 应用：SparkConf → Angel Configuration，通过 `AngelPSClient` 启动 PS 集群，向 Angel Master 注册 |
| **Executor 端** | 连接已有 PS 集群：从 task properties 获取 Master 位置，创建 `PSAgent` 通信，建立与 PS 的连接 |

**配置翻译**（`AngelPSContext.scala:331-415`）：Spark 参数自动翻译为 Angel 参数：

| Spark 配置 | Angel 配置 | 用途 |
|------------|------------|------|
| `spark.ps.instances` | `ANGEL_PS_NUMBER` | PS 数量 |
| `spark.ps.cores` | `ANGEL_PS_CPU_VCORES` | 每 PS CPU 核数 |
| `spark.ps.memory` | `ANGEL_PS_MEMORY_GB` | 每 PS 内存 |
| `spark.ps.mode` | `ANGEL_DEPLOY_MODE` | 部署模式（YARN/LOCAL） |
| `spark.angel.master.memory` | `ANGEL_AM_MEMORY_GB` | Angel Master 内存 |

### 3.3 PSVector / PSMatrix

Spark on Angel 提供两个分布式数据抽象：

#### PSVector

`PSVector`（`models/PSVector.scala:36-140`）表示 PS 上的分布式向量，实际是 `PSVectorPool` 管理的分布式矩阵的一行。这种设计允许高效内存管理和向量间运算。

| 操作 | 用途 | 示例 |
|------|------|------|
| `pull()` | 从 PS 拉取向量 | `val local = psVector.pull()` |
| `push(vector)` | 重置并用本地向量更新 | `psVector.push(localVector)` |
| `increment(delta)` | 累加增量到 PS 向量 | `psVector.increment(gradients)` |
| `update(vector)` | 更新 PS 向量 | `psVector.update(newWeights)` |
| `reset()` | 清零 | `psVector.reset()` |
| `fill(value)` | 填充特定值 | — |

#### PSMatrix

`PSMatrix`（`models/PSMatrix.scala:34-253`）表示分布式矩阵，支持整矩阵或特定行操作：`pull()`, `pull(rowId)`, `increment(delta)`, `update(rowId, row)`, `push(matrix)`, `reset()`, `reset(rowId)`。

#### VectorUtils 高级操作

`VectorUtils`（`util/VectorUtils.scala:38-346`）提供优化的 PSVector 操作：
- **BLAS 运算**：`axpy`, `dot`, `nrm2`
- **逐元素运算**：`add`, `mul`, `div`
- **聚合**：`sum`, `max`, `min`, `nnz`
- **变换**：`map`, `zip2Map`, `randomUniform`

### 3.4 PSAgent 通信架构

每个 Spark Executor 维护自己的 `PSAgent` 实例（`psagent/PSAgent.java:45-89`），负责与 PS 通信。`UserRequestAdapter`（`psagent/matrix/transport/adapter/UserRequestAdapter.java:66-814`）处理分布式矩阵操作的复杂性：

1. **请求拆分**：将用户请求拆分为分区级子请求
2. **请求路由**：路由到正确的 PS
3. **响应合并**：合并多个分区的响应
4. **并发管理**：管理并发请求与响应

底层网络传输基于 Netty，可配置收发缓冲区（默认 1MB）和每 PS 最大请求数（默认 16）。

### 3.5 逻辑回归示例（SoA 典型用法）

```scala
// spark-on-angel/examples/.../basic/LR.scala:34-69
// 1. 初始化 Spark on Angel 环境
val spark = SparkSession.builder().appName("LR").getOrCreate()
PSContext.getOrCreate(spark.sparkContext)

// 2. 创建分布式参数（权重向量）
val weights = PSVector.dense(dimension, psPartitionNum)

// 3. 训练循环：Spark 数据并行 + Angel PS 模型并行
for (epoch <- 1 to numEpoch) {
  val gradients = dataRDD.mapPartitions { iter =>
    val w = weights.pull()           // 从 PS 拉取权重
    val grad = computeGradient(iter, w)  // 本地计算梯度
    Iterator(grad)
  }.reduce(_ + _)                    // Spark 端聚合
    
  weights.increment(gradients)       // 推送梯度到 PS
}

PSContext.stop()
```

这个例子展示了 SoA 的核心模式：**Spark 提供数据并行，Angel PS 提供模型并行**，适合需要两者结合的大规模迭代 ML 任务。

---

## 4. 编程模型

> DeepWiki 页面：`1.2-key-components`  
> 源码：`docs/apis/MLRunner_en.md`、`AngelClient.md`、`MLModel.md`、`PSModel.md`、`Task.md`、`MLLearner.md`、`core_api_en.md`

Angel 的编程模型是一套层次化抽象，从应用入口到参数操作逐层下沉。

### 4.1 核心组件层次

```
应用层     MLRunner ──── 应用入口与协调（train/predict/incTrain）
              │
              ▼
编排层     AngelClient ── 系统编排（startPSServer/loadModel/runTask/saveModel）
              │
              ▼
模型层     MLModel ────── 算法模型容器（addPSModel/getPSModel/predict）
              │
              ▼
参数层     PSModel ────── 分布式参数抽象（pull/push/clock/PSF）
              │
              ▼
执行层     TrainTask ───── 训练算法实现（TaskContext + DataBlock）
              │
              ▼
训练核心   MLLearner ───── 学习算法核心（readData + updateParams）
```

### 4.2 MLRunner：应用入口

`MLRunner`（`docs/apis/MLRunner_en.md:1-49`）是应用主入口，采用模板方法模式，子类实现特定算法逻辑，继承标准 PS 管理：

| 方法 | 用途 |
|------|------|
| `train(Configuration)` | 启动模型训练 |
| `predict(Configuration)` | 执行模型预测 |
| `incTrain(Configuration)` | 增量训练 |

### 4.3 AngelClient：系统编排

`AngelClient`（`docs/apis/AngelClient.md:1-56`）管理 PS 生命周期、模型加载/保存、任务执行协调，屏蔽分布式系统复杂性。

### 4.4 MLModel：模型容器

`MLModel`（`docs/apis/MLModel.md:1-50`）是完整 ML 模型的容器，持有一个或多个 `PSModel`：

```java
// MLModel 接口
public abstract class MLModel {
    public void addPSModel(String name, PSModel psModel);  // 添加 PSModel
    public PSModel getPSModel(String name);                // 按名获取
    public abstract double predict(DataBlock data);        // 预测逻辑
    public void setSavePath(Configuration conf);           // 配置持久化
}
```

### 4.5 PSModel：分布式参数抽象

如 §2.3 所述，`PSModel` 封装分布式矩阵的 pull/push/sync/IO/behavior 操作，是算法与 PS 交互的核心。

### 4.6 TrainTask：训练任务

`TaskContext`（`docs/apis/Task.md:1-143`）提供运行时信息与控制：

| 方法 | 用途 |
|------|------|
| `getReader()` | 访问输入数据读取器 |
| `getIteration()` | 当前迭代编号 |
| `incIteration()` | 递增迭代计数器 |
| `globalSync()` | 跨所有任务同步 |
| `getMatrixClock(matrixId)` | 获取矩阵同步时钟 |

### 4.7 DataBlock：数据存储抽象

`DataBlock`（`docs/apis/DataBlock.md:1-72`）支持不同存储后端：

| 实现 | 存储介质 | 访问模式 |
|------|----------|----------|
| `MemoryDataBlock` | 内存 | 随机 + 顺序 |
| `DiskDataBlock` | 本地磁盘 | 仅顺序 |
| `MemoryAndDiskDataBlock` | 内存 + 磁盘溢出 | 混合 |

接口：`put(value)`, `read()`, `get(index)`, `shuffle()`, `resetReadIndex()`。

### 4.8 MLLearner：训练算法核心

`MLLearner`（`docs/apis/MLLearner.md:1-15`）封装核心学习算法逻辑，协调数据访问（`DataBlock`）与参数更新（`PSModel`），实现算法特定的优化过程。

### 4.9 完整训练工作流

```
1. MLRunner.train(conf)
   └─ AngelClient.startPSServer()        # 启动 PS 集群
   └─ AngelClient.createMatrices(model)  # 创建分布式矩阵
   └─ AngelClient.loadModel(model)       # (可选)加载预训练模型
   └─ AngelClient.runTask(TrainTask)     # 启动 Worker
       └─ TrainTask.run(ctx):
           ├─ DataBlock data = ctx.getReader().read()   # 读取数据
           ├─ MLLearner.train(ctx, data):
           │   └─ for epoch in 1..N:
           │       ├─ PSModel w = model.getPSModel("w")
           │       ├─ w = w.getRow(0)       # pull 参数
           │       ├─ grad = compute(data, w)  # 本地计算梯度
           │       ├─ w.increment(grad)     # push 梯度
           │       └─ w.clock()             # 同步
           └─ ctx.globalSync()              # 全局同步
   └─ AngelClient.saveModel(model)       # 保存模型
   └─ AngelClient.stop()                 # 停止
```

---

## 5. 算法实现

> DeepWiki 页面：`4.2-algorithm-implementations`、`4.3-neural-networks-and-graph-models`、`6-graph-computing`、`6.2-community-detection`、`7-embedding-methods`、`8.2-feature-parallel-training`

### 5.1 算法分类总表

| 类别 | 算法 | 模型类/入口 | 关键特性 |
|------|------|-------------|----------|
| **分类** | LR | `LogisticRegression` | 对数损失 + L2，mini-batch SGD |
| | SVM | `SupportVectorMachine` | Hinge 损失 + L2 |
| | Softmax | `SoftmaxRegression` | 交叉熵 + softmax，多分类 |
| | MLR | MLR | 分段线性，softmax 门控组合 m 个线性模型 |
| **回归** | Linear | `LinearRegression` | MSE (L2 损失) |
| | Robust | `RobustRegression` | Huber 损失，抗异常值 |
| **聚类** | K-Means | `KMeansModel`/`KMeansRunner` | mini-batch K-means，K×N 中心矩阵 + K×1 计数向量 |
| **FM** | FM | `FactorizationMachines` | 线性项 + 隐因子二阶交叉，稀疏数据 |
| **深度学习** | DNN/DeepFM/PNN/NFM/Wide&Deep | `GraphModel` + JSON 配置 | 粗粒度计算图，层系统 |
| **图算法** | PageRank | `PageRank` (edgecut/vertexcut) | 节点排名，两种切分实现 |
| | K-Core | `KCore` | 核分解，full/sparse/mid 三种模式 |
| | Closeness | `Closeness` | HyperLogLog++ 近似接近中心性 |
| | WCC | `WCC` | 弱连通分量，标签传播 |
| | Louvain | `Louvain` | 模块度优化社区发现，层次折叠 |
| | LPA | `LPA` | 标签传播社区发现 |
| | Triangle | `TriangleCountingUndirected` | 三角计数，聚类系数 |
| | CommonFriends | `CommonFriends` | 共同邻居统计 |
| **嵌入** | Word2Vec | `Word2VecModel` | SkipGram + 负采样，支持 10 亿节点×1000维 |
| | LINE | LINE | 一阶/二阶邻近性网络嵌入 |
| **GBDT** | FP-GBDT | `FPGBDTTrainer` | 特征并行训练，直方图减法优化 |

### 5.2 传统 ML 算法模式

所有传统 ML 算法遵循一致架构（`docs/algo/lr_on_angel.md:23-38`）：

```
GraphRunner (协调训练)
   ├─ ModelClass (定义算法逻辑)
   ├─ Worker (处理数据 + 计算梯度)
   ├─ PSAgent (PS 通信)
   └─ PSModel (分布式参数管理)
```

**通用训练流程**：
1. **参数拉取**：Worker 从 PS 拉取最新模型参数
2. **梯度计算**：处理本地数据计算参数更新
3. **参数推送**：发送梯度到 PS 取平均
4. **模型更新**：PS 用平均梯度更新全局模型

**数据格式支持**：`libsvm`（稀疏 `1 1:0.5 3:1.2`）、`dummy`（二值稀疏 `1 1 3 5`）、`dense`（全值 `1 0.5 0.0 1.2`），通过 `ml.data.type` 配置。

**优化器选择**：`ftrl`（适合稀疏数据）、`adam`（适合稠密数据）、`momentum`（动量 SGD）。

### 5.3 神经网络与图模型（AngelGraph）

> DeepWiki 页面：`4.3-neural-networks-and-graph-models`  
> 源码：`spark-on-angel/mllib/.../core/GraphModel.scala`、`OfflineLearner.scala`

#### GraphModel + OfflineLearner 系统

Angel 神经网络框架围绕两个主组件构建：
- **`GraphModel`**（`GraphModel.scala:38-151`）：模型定义，封装计算图，提供前向/反向传播方法
- **`OfflineLearner`**（`OfflineLearner.scala:36-187`）：训练编排，管理数据分批、manifold 构建、训练迭代

#### 粗粒度计算图

Angel 实现粗粒度计算图，节点代表**层**而非单个操作，适合 ML 算法开发。每层维护 `input`（输入层列表）和 `consumer`（消费层列表）关系形成计算图，并通过状态机管理训练执行顺序避免冗余计算。

#### 算法特定的层组合

| 算法 | 输入层 | 特征交叉 | 隐藏层 | 输出组合 |
|------|--------|----------|--------|----------|
| DeepFM | SimpleInputLayer + Embedding | BiInnerSumCross | FCLayer | SumPooling |
| PNN | SparseInputLayer + Embedding | BiInnerCross | ConcatLayer + FCLayer | SumPooling |
| NFM | SparseInputLayer + Embedding | BiInteractionCross | FCLayer | SumPooling |
| Wide & Deep | SimpleInputLayer + Embedding | 无 | FCLayer | SumPooling |

#### JSON 声明式网络定义

Angel 支持通过 JSON 配置文件声明式定义神经网络（`docs/basic/json_conf.md:144-235`），提供分层配置模式，无需修改代码即可调整网络结构。

### 5.4 图计算框架

> DeepWiki 页面：`6-graph-computing`、`6.2-community-detection`  
> 源码：`spark-on-angel/graph/src/main/scala/com/tencent/angel/graph/`

Angel 图计算框架结合 Spark 分布式数据处理与 Angel PS 状态管理。图算法实现为 Spark ML 的 `Transformer` 组件，在分布式图分区上操作，通过 PS 维护共享状态。

#### 图算法基础结构

所有图算法继承 Spark ML 的 `Transformer` 接口，遵循一致模式：

```
Transformer (主类)
  ├─ PSModel (专用参数服务器模型)  ← 管理分布式状态
  ├─ GraphPartition (图分区)       ← 本地计算
  └─ 执行模式: 批处理通信优化 PS 性能
```

**PS 模型映射**：

| 算法 | PS Model 类 | 管理的状态 |
|------|-------------|------------|
| WCC | `WCCPSModel` | 节点分量标签 |
| K-Core | `KCorePSModel` | 核值与消息 |
| PageRank | `PageRankPSModel` | PageRank 分数 |
| Louvain | `LouvainPSModel` | 社区分配 |
| LPA | `LPAPSModel` | 标签传播状态 |

#### Louvain 社区发现（重点）

> 源码：`spark-on-angel/graph/.../community/louvain/Louvain.scala`、`LouvainGraph.scala`、`LouvainGraphPartition.scala`、`LouvainPSModel.scala`

Louvain 通过模块度优化进行层次社区发现，四阶段迭代：
1. 每个节点初始自成社区
2. 迭代地将节点移到使模块度增益最大的邻居社区
3. 将社区折叠为"超级节点"
4. 重复直到模块度不再改善

**LouvainPSModel 的三个分布式向量**（`LouvainPSModel.scala:33-167`）：

| 向量 | 用途 | 关键操作 |
|------|------|----------|
| `node2CommunityPSVector` | 节点→当前社区映射 | `updateNode2community()`, `getNode2commMap()` |
| `community2weightPSVector` | 社区权重（模块度计算用） | `incrementCommWeight()`, `getCommInfo()` |
| `node2CommunityFianlPSVector` | 最终社区分配 | `updateNodeCommunityFinalPSFunction()` |

分布式向量使 Louvain 能处理**数十亿边**的图。关键配置参数：`partitionNum`（Spark 分区数）、`psPartitionNum`（PS 分区数）、`numFold`（最大折叠次数，默认 5）、`numOpt`（每次折叠优化迭代数，默认 10）、`batchSize`（PS 操作批大小，默认 10000）、`useBalancePartition`（倾斜图负载均衡）。

#### 图嵌入：LINE 算法

LINE（`docs/algo/sona/line_sona.md`）通过优化一阶和二阶邻近性学习节点表示：
- **一阶邻近性**：节点间直接边连接
- **二阶邻近性**：通过共同邻居的相似性

输入格式为边表 `srcId separator dstId [weight]`，支持加权/无向图。配置：`embedding`（维度，64/128/256）、`negative`（负样本数 5-10）、`order`（邻近性阶数 1 或 2）。

### 5.5 GBDT 特征并行训练

> DeepWiki 页面：`8.2-feature-parallel-training`  
> 源码：`spark-on-angel/mllib/.../gbdt/trainer/FPGBDTTrainer.scala`、`GBDTTrainer.scala`、`helper/HistManager.scala`

特征并行训练通过**跨 Worker 分配特征**（而非数据样本）解决高维数据集的内存与通信瓶颈。

**传统数据并行的问题**：每个 Worker 存储所有特征的完整梯度直方图，内存随 `特征数 × 分裂点数 × 类数` 增长，直方图聚合通信开销大。

**特征并行的优势**：Worker 只存储特征子集的部分直方图，降低内存占用，通过二进制编码的分裂结果降低网络开销。

#### 平衡特征分组

`balancedFeatureGrouping` 基于特征密度（非零值数）创建平衡特征组：`featNNZ`（非零计数）→ `fidToGroupId`（特征→组映射）→ `groupIdToFid`（组→特征映射）→ `fidToNewFid`（特征 ID 重映射）。

#### FPGBDTTrainer 核心方法

| 方法 | 用途 | 关键操作 |
|------|------|----------|
| `createNewTree()` | 初始化新树 | 采样特征、重置位置、计算梯度 |
| `findSplits()` | 寻找最佳本地分裂 | 构建直方图、找每特征最优分裂 |
| `getSplitResults(splits)` | 计算分裂决策 | 确定实例左右分配 |
| `splitNodes(splitResults)` | 更新树结构 | 创建子节点、更新位置 |
| `setAsLeaf(nid)` | 创建叶节点 | 计算权重、更新预测 |

#### 性能优化

- **直方图减法**：父直方图减子直方图得兄弟直方图，减少计算
- **先建轻子**：先为较小子节点建直方图，最大化减法收益
- **直方图复用**：`HistManager` 维护直方图对象池避免重复分配
- **二进制编码**：`RangeBitSet` 紧凑编码分裂决策
- **最小广播**：仅广播获胜分裂及其结果
- **线程并行**：可配置线程池并发构建直方图

---

## 6. 部署

> DeepWiki 页面：`9.1-yarn-deployment`

### 6.1 YARN 部署

**前置条件**：Hadoop ≥ 2.2.0（YARN + HDFS 配置正确）、Java ≥ 1.8、Spark ≥ 2.4.0、Angel 分发包。

**Spark on Angel 的双 YARN 应用**：

| 参数 | 应用 | 说明 | 示例 |
|------|------|------|------|
| `spark.ps.instances` | Angel PS | PS 数量 | 2 |
| `spark.ps.cores` | Angel PS | 每 PS CPU 核数 | 2 |
| `spark.ps.memory` | Angel PS | 每 PS 内存 | 4g |
| `--num-executors` | Spark | Spark Executor 数 | 4 |
| `--executor-cores` | Spark | 每 Executor CPU 核数 | 2 |
| `--executor-memory` | Spark | 每 Executor 内存 | 2g |

**Angel 部署模式参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `angel.deploy.mode` | YARN | 部署模式 YARN/LOCAL |
| `angel.running.mode` | ANGEL_PS_WORKER | 运行模式 |
| `angel.am.memory.mb` | 1280 | Angel Master 内存 |
| `angel.worker.memory.mb` | 4096 | 每 Worker 内存 |
| `angel.ps.memory.mb` | 4096 | 每 PS 内存 |

**资源需求**：最少 6GB（1 PS + 1 Worker + 1 AM），推荐 10GB+。监控通过 YARN Web UI（`http://<rm-host>:8088`），日志级别可配（`angel.am.log.level` 等），心跳间隔默认 5000ms。

### 6.2 Local 模式

Local 模式使用本地进程管理器直接执行，适合开发与测试，无需 Hadoop 集群。

### 6.3 Kubernetes 部署

K8s 部署中 Master/PS/Worker 各运行在独立 Pod，通过 K8s Service 发现 PS 位置。`AngelKubernetesClient` + `KubernetesClusterManager` 管理资源，`AngelExecutorPodsAllocator` 分配 Pod。

---

# 第二部分：DataFlow-WebUI 可视化工作台

> 两个层面：① 本地 DataFlow 仓库内的 Gradio 界面（源码精读）② 独立 WebUI 仓库（NL2Pipeline Harness）

## 7. 本地 Gradio 界面（源码精读）

> 本地路径：`dataflow_repos/DataFlow/dataflow/webui/`  
> 文件清单：`operator_pipeline.py`（678 行）、`kbclean_webui.py`（178 行）、`kbcleaning_tools.py`（133 行）、`kb_sglang_server.py`（152 行）

### 7.1 operator_pipeline.py 完整分析

这是 DataFlow 的**动态算子与 Pipeline 可视化**界面，核心是 `DynamicOperatorSystem` 类，通过反射动态发现所有注册算子并生成表单。

#### 7.1.1 数据类定义

```python
# operator_pipeline.py:24-46
@dataclass
class ParameterInfo:
    name: str
    type_annotation: str
    default_value: Any
    has_default: bool
    description: str = ""

@dataclass
class OperatorInfo:
    name: str
    class_obj: type
    init_params: List[ParameterInfo]   # __init__ 参数签名
    run_params: List[ParameterInfo]    # run() 参数签名
    description: str = ""

@dataclass
class PipelineInfo:
    name: str
    category: str  # 'api'
    class_obj: type
    file_path: str
    description: str = ""
```

#### 7.1.2 DynamicOperatorSystem 动态发现机制

```python
# operator_pipeline.py:48-180
class DynamicOperatorSystem:
    def __init__(self):
        self.logger = get_logger()
        self.operators: Dict[str, OperatorInfo] = {}
        self.pipelines: Dict[str, PipelineInfo] = {}
        self._discover_operators()    # 发现算子
        self._discover_pipelines()    # 发现 Pipeline

    def _discover_operators(self):
        # 从 OPERATOR_REGISTRY.get_obj_map() 获取所有注册算子
        for name, obj in OPERATOR_REGISTRY.get_obj_map().items():
            info = self._analyze_operator(name, obj)
            self.operators[name] = info

    def _discover_pipelines(self):
        # 扫描 statics/pipelines/api_pipelines/ 目录下的 .py 文件
        pipeline_base = os.path.join(os.path.dirname(__file__), "..", "statics", "pipelines")
        for category in ["api_pipelines"]:
            path = os.path.join(pipeline_base, category)
            for fn in os.listdir(path):
                if fn.endswith(".py") and not fn.startswith("__"):
                    info = self._analyze_pipeline(category, fn, path)
```

#### 7.1.3 参数签名分析（核心机制）

`_analyze_operator` 使用 `inspect.signature` 分析算子的 `__init__` 和 `run` 方法参数签名，自动生成表单：

```python
# operator_pipeline.py:119-139
def _analyze_operator(self, name: str, obj: type) -> OperatorInfo:
    def extract(sig: inspect.Signature, exclude: List[str]) -> List[ParameterInfo]:
        out = []
        for pname, p in sig.parameters.items():
            if pname in exclude:
                continue
            has_def = (p.default is not inspect._empty)
            anno = p.annotation if p.annotation is not inspect._empty else Any
            anno_str = getattr(anno, "__name__", str(anno))
            default = p.default if has_def else None
            out.append(ParameterInfo(pname, anno_str, default, has_def))
        return out

    init_sig = inspect.signature(obj.__init__)
    init_params = extract(init_sig, exclude=["self"])
    run_params = []
    if hasattr(obj, "run"):
        run_sig = inspect.signature(obj.run)
        run_params = extract(run_sig, exclude=["self", "storage"])
    return OperatorInfo(name, obj, init_params, run_params, desc)
```

**机制要点**：
- `__init__` 参数排除 `self`，保留 `llm_serving` 等所有初始化参数
- `run` 参数排除 `self` 和 `storage`（storage 由系统自动注入）
- 自动提取类型注解（`__name__`）和默认值
- `has_default` 标记是否有默认值，决定表单是否必填

#### 7.1.4 表单模板生成

`build_param_templates` 将分析结果转为 JSON 表单模板（`operator_pipeline.py:353-386`）：

```python
def build_param_templates(op_name):
    info = dynamic_system.get_operator_info(op_name)
    # 初始化参数：排除 llm_serving（由独立 UI 配置）
    init_dict = {p.name: (p.default_value if p.has_default else "")
                 for p in info.init_params if p.name != "llm_serving"}
    # 运行参数
    run_dict = {p.name: (p.default_value if p.has_default else "")
                for p in info.run_params}
    init_str = json.dumps(init_dict, ensure_ascii=False, indent=2)
    run_str = json.dumps(run_dict, ensure_ascii=False, indent=2)
    has_llm = any(p.name == "llm_serving" for p in info.init_params)
    return (desc, init_str, run_str, api_group_visible, local_group_visible)
```

#### 7.1.5 支持的执行模式

**模式 1：算子模式** — 选择单个算子，配置 init 参数 + run 参数 + LLM Serving + Storage，执行 `op_inst.run(storage=storage.step(), **run_params)`。

**模式 2：Pipeline 模式** — 选择预定义 Pipeline（`api_pipelines/` 目录下），配置输入文件 + Storage + API 参数，执行 `pipeline_inst.forward()`。Pipeline 模式会自动遍历所有组件，将 `llm_serving` 统一注入。

#### 7.1.6 LLM Serving 工厂

`create_serving_instance`（`operator_pipeline.py:153-172`）支持两种 Serving：

```python
def create_serving_instance(self, serving_type: str, **kwargs) -> LLMServingABC:
    if serving_type == "API":
        from dataflow.serving import APILLMServing_request
        return APILLMServing_request(
            api_url=api_url, model_name=model_name, max_workers=int(max_workers))
    # 本地模型
    from dataflow.serving import LocalModelLLMServing_vllm
    return LocalModelLLMServing_vllm(
        hf_model_name_or_path=model_path,
        vllm_tensor_parallel_size=int(tensor_parallel_size),
        vllm_temperature=float(temperature), ...)
```

#### 7.1.7 算子执行回调

```python
# operator_pipeline.py:397-427
def gradio_run(op_name, init_str, run_str, api_url, model_name, api_key, ...,
               input_file_path, cache_path, file_name_prefix):
    other_init = json.loads(init_str)       # 解析 init 参数 JSON
    run_params = json.loads(run_str)         # 解析 run 参数 JSON
    info = dynamic_system.get_operator_info(op_name)
    # 若算子需要 llm_serving，自动创建并注入
    if any(p.name == "llm_serving" for p in info.init_params):
        other_init["llm_serving"] = dynamic_system.create_serving_instance(**cfg)
    op_inst = info.class_obj(**other_init)   # 实例化算子
    storage = dynamic_system.create_storage_instance(...)  # 创建存储
    op_inst.run(storage=storage.step(), **run_params)       # 执行
    # 读取输出并预览
    out_fn = storage._get_cache_file_path(storage.operator_step + 1)
    df = pd.read_json(out_fn, lines=True)
    return summary, df.head(5).to_html()
```

#### 7.1.8 中英文双语支持

界面通过 `zh_t`/`en_t` 字典实现完整中英文切换（`operator_pipeline.py:187-257`），`switch_language` 回调一次性更新全部 37 个 UI 控件的标签。

### 7.2 kbclean_webui.py：知识清洗 Pipeline

`kbclean_webui.py`（178 行）是知识库清洗的专用界面，支持 PDF 上传和 URL 输入，三种 Serving 类型（vllm/api/sglang），实时控制台输出。

核心回调 `run_pipeline_ui`（`:42-95`）在独立线程中运行 Pipeline，通过 `redirect_stdout` 捕获输出并实时返回最后 10 行：

```python
def run_pipeline_ui(pdf_list, url_list, serving_type, ...):
    kb = KBCleaning_Tools()
    inputs = pdf_list + url_list
    out_buffer = io.StringIO()
    def target():
        with redirect_stdout(out_buffer), redirect_stderr(out_buffer):
            kb.run_pipeline(pdf_or_url_list=inputs, serving_type=serving_type, ...)
    thread = threading.Thread(target=target)
    thread.start()
    while thread.is_alive():
        time.sleep(0.2)
        lines = out_buffer.getvalue().splitlines()
        yield "\n".join(lines[-10:])  # 实时返回最后10行
```

### 7.3 kbcleaning_tools.py：四步清洗 Pipeline

`KBCleaning_Tools.run_pipeline`（`:79-129`）定义了四步知识清洗流程：

```python
# 步骤1: PDF/URL → Markdown
knowledge_cleaning_step1 = FileOrURLToMarkdownConverterBatch(
    intermediate_dir="./.cache/raw", lang="en", mineru_backend="vlm-sglang-engine")
# 步骤2: Markdown → 文本分块
knowledge_cleaning_step2 = CorpusTextSplitterBatch(
    split_method="token", chunk_size=512, tokenizer_name=tokenizer_name)
# 步骤3: 知识清洗
knowledge_cleaning_step3 = KnowledgeCleanerBatch(llm_serving=llm_serving, lang="en")
# 步骤4: 多跳QA生成
knowledge_cleaning_step4 = MultiHopQAGeneratorBatch(llm_serving=llm_serving, lang="en")

# 串行执行，每步通过 storage.step() 推进
knowledge_cleaning_step1.run(storage=storage.step())
knowledge_cleaning_step2.run(storage=storage.step())
knowledge_cleaning_step3.run(storage=storage.step())
knowledge_cleaning_step4.run(storage=storage.step())
```

### 7.4 kb_sglang_server.py：SGLang 服务器管理

`SGLangServer`（152 行）封装 SGLang 本地服务器进程管理：
- `find_free_port()`：自动查找空闲端口
- `launch_server()`：启动 `sglang.launch_server`，等待健康检查
- `generate_from_input()`：通过 ThreadPoolExecutor 并发调用 `/generate` 端点

### 7.5 本地 Gradio 界面功能总结

| 功能 | 文件 | 核心机制 |
|------|------|----------|
| 动态算子发现 | `operator_pipeline.py` | `OPERATOR_REGISTRY` + `inspect.signature` 反射 |
| Pipeline 发现 | `operator_pipeline.py` | 扫描 `api_pipelines/` 目录 + AST 解析类名 |
| 参数表单生成 | `operator_pipeline.py` | `__init__`/`run` 签名 → JSON 模板 |
| 双模执行 | `operator_pipeline.py` | 算子模式（单算子）/ Pipeline 模式（多算子串行） |
| LLM Serving | `operator_pipeline.py` | API / vLLM 本地两种 |
| 知识清洗 | `kbclean_webui.py` + `kbcleaning_tools.py` | 4 步 Pipeline + 实时日志 |
| SGLang 服务 | `kb_sglang_server.py` | 本地服务器进程管理 |
| 双语支持 | `operator_pipeline.py` | zh_t/en_t 字典全量切换 |

---

## 8. 独立 WebUI 仓库

> GitHub: `OpenDCAI/DataFlow-WebUI`（129 stars, 39 forks, 255 commits）  
> 来源：README + DataFlow-Harness 论文

### 8.1 定位与架构

DataFlow-WebUI 是 DataFlow 的**全栈开源图形界面**，帮助用户通过可视化画布和自然语言交互构建、运行、管理 DataFlow Pipeline。它是 **DataFlow-Harness** 的工程与交互层。

**DataFlow-Harness 三组件**：

```
┌─────────────────────────────────────────────────────────┐
│                  DataFlow-Harness                        │
│                                                          │
│  ┌──────────────┐  ┌─────────┐  ┌──────────────────┐   │
│  │ DataFlow-    │  │  MCP    │  │ DataFlow-WebUI   │   │
│  │ Skills       │  │ Layer   │  │                  │   │
│  │              │  │         │  │ 对话Agent +      │   │
│  │ 工作流知识:   │  │ 连接    │  │ 可视化DAG编辑器   │   │
│  │ 算子选择      │  │ Agent↔  │  │                  │   │
│  │ Schema链接    │  │ 实时算子│  │ 共享Pipeline表示  │   │
│  │ 组装步骤      │  │ 注册表  │  │ 双向同步         │   │
│  │              │  │ +状态   │  │                  │   │
│  └──────────────┘  └─────────┘  └──────────────────┘   │
│         │               │               │               │
│         └───────────────┼───────────────┘               │
│                         ▼                               │
│              Validation Engine                          │
│         (DAG结构检查 + Schema兼容性检查)                   │
└─────────────────────────────────────────────────────────┘
```

### 8.2 NL2Pipeline 机制

DataFlow-WebUI 的核心是弥合 **NL2Pipeline gap**：将自然语言工作流意图转为持久的、平台原生的 Pipeline 制品。

**NL2Pipeline gap 问题**：编码 Agent 通常生成脚本，但脚本不会自动物化为持久的、可编辑的平台制品。DataFlow-Harness 通过**类型化增量突变（typed, incremental mutations）**而非自由脚本引导 LLM Agent 构建平台原生 DAG。

### 8.3 双模态界面

DataFlow-WebUI 实现双模态同步：
- **对话 Agent**：用户用自然语言描述需求，Agent 通过 MCP 调用构建 Pipeline
- **可视化 DAG 编辑器**：Agent 构建的 Pipeline 实时同步为可编辑的 DAG 画布

两者通过**共享 Pipeline 表示**双向同步。用户可检查、编辑、运行、复用生成的 Pipeline。

### 8.4 Validation Engine

验证引擎检查：
- **DAG 结构**：有向无环图合法性
- **Schema 兼容性**：算子间输入输出 Schema 匹配

### 8.5 支持的 Code Agent

| Agent | 使用模式 | CLI 二进制 | MCP 配置位置 | 认证 |
|-------|----------|-----------|--------------|------|
| **Claude Code** | WebUI Chat Agent | `claude` | `--mcp-config .mcp.json` | `ANTHROPIC_API_KEY` |
| **Codex** | WebUI Chat Agent | `codex` | `~/.codex/config.toml` | `OPENAI_API_KEY` 或 OAuth |
| **Cursor** | IDE Agent | — | `.cursor/mcp.json` | Cursor 内置认证 |
| **Claude Code (终端)** | Terminal Agent | `claude` | `.mcp.json` | `ANTHROPIC_API_KEY` |

**两种使用模式**：
- **WebUI Chat Agents**：由 WebUI 后端无头调度，在浏览器中对话
- **IDE/Terminal Agents**：用户自驱，通过 MCP 连接 WebUI，将 Pipeline 推送到画布

### 8.6 技术栈

- **后端**：Python + FastAPI（`uvicorn app.main:app`，端口 8000）
- **前端**：Node.js 20+ + npm 构建
- **依赖**：Python 3.10+、DataFlow Core
- **配置**：`.mcp.json`（MCP 连接）、`scripts/setup_all.sh`（一键配置）

### 8.7 关键特性

1. **弥合 NL2Pipeline gap**：自然语言 → 持久可编辑 Pipeline 制品
2. **复杂工作流的程序性知识**：为 Agent 提供"如何正确排序使用工具"的知识（如 VQA 数据集需 PDF 解析→版面理解→OCR→图文对齐→QA 提取→质量过滤）
3. **长期工作流复用**：使数据工作流可见、可编辑、可运行、可复用
4. **DataFlow-Harness 驱动**：93.3% 端到端通过率，成本降 72.5%，延迟降 49.9%

---

## 9. DataFlow-Harness 论文

> arXiv:2607.16617 [cs.SE], 2026-07-18 提交, v2 2026-07-24  
> 标题：*DataFlow-Harness: A Grounded Code-Agent Platform for Constructing Editable LLM Data Pipelines*  
> 作者：Runming He, Zhen Hao Wong, Hao Liang, Zimo Meng, Chengyu Shen, Xiaochen Ma, Wentao Zhang

### 9.1 核心问题：NL2Pipeline Gap

论文指出：LLM 越来越多地用于自动化数据处理工作流，但编码 Agent 通常生成**脚本**，这些脚本不会自动物化为持久的、可编辑的平台制品。论文将此断裂称为 **NL2Pipeline gap**。

### 9.2 解决方案

DataFlow-Harness 结合三个组件：
1. **DataFlow-Skills**：提供程序性指导（算子选择、Schema 链接、组装步骤）
2. **MCP 层**：暴露实时算子注册表和当前 Pipeline 状态
3. **DataFlow-WebUI**：同步对话式创作与可视化 DAG 编辑器

关键创新：通过**类型化增量突变**引导 LLM Agent 构建平台原生 DAG，而非生成自由脚本。

### 9.3 实验结果

**12 任务数据工程基准**：

| 指标 | 结果 |
|------|------|
| 端到端通过率 | **93.3%** |
| 对比 Vanilla Claude Code 成本 | 降低 **72.5%** |
| 对比 Vanilla Claude Code 延迟 | 降低 **49.9%** |
| 对比 Context-Aware Claude Code 通过率 | 差距仅 **0.9 个百分点** |
| 对比 Context-Aware Claude Code 成本 | 降低 **42.8%** |

**关键发现**：逐任务分析表明，**Skills 在构建依赖隐式程序性知识时最有用**。这验证了"实时平台接地（live platform grounding）可产生持久可编辑工作流制品，且观测可靠性接近脚本生成基线，同时构建成本和延迟更低"。

### 9.4 论文意义

DataFlow-Harness 证明了：
- 程序性知识（Skills）+ 实时平台接地（MCP）+ 可视化（WebUI）的组合，可在不牺牲可靠性的前提下显著降低成本和延迟
- 持久可编辑的工作流制品比一次性脚本更适合长期复用
- 类型化增量突变比自由脚本生成更可控、更可靠

---

# 第三部分：对 SRS 项目的深度应用价值

> SRS 项目：GJB 438C 格式 SRS 文档三层一致性检测，知识图谱 7720 节点，数据集 359 份文档

## 10.1 Angel Graph 社区发现与图嵌入用于 SRS 知识图谱

SRS 项目已构建知识图谱 `srs_kb_graph_v2.json`（7720 节点），Angel Graph 的图算法可直接赋能：

### 10.1.1 社区发现：Louvain/LPA 发现规则聚类

Angel 的 **Louvain 算法**（`spark-on-angel/graph/.../community/louvain/`）通过模块度优化发现层次社区结构。对 SRS 知识图谱的应用：

- **规则聚类**：将 7720 个节点（GJB 规则、章节、约束、表格等）按连接密度自动聚类为社区，每个社区可能对应一个功能域（如"表格格式规则社区"、"章节编号规则社区"）
- **跨社区一致性检测**：社区间的边代表跨域约束，可定位潜在一致性冲突
- **层次分析**：Louvain 的折叠机制可发现规则的层次结构（GJB 438C 标准的章→节→条→款对应社区→子社区）

**配置建议**：
```
partitionNum: 100        # Spark 分区
psPartitionNum: 40       # PS 分区
numFold: 5               # 折叠次数
numOpt: 10               # 每次折叠优化迭代
useBalancePartition: true  # 7720节点规模可能不均，启用负载均衡
```

7720 节点规模远小于 Angel 设计的数十亿边场景，Local 模式即可运行，但 LouvainPSModel 的三向量设计（node2Community、community2weight、final）提供了清晰的分布式扩展路径。

### 10.1.2 图嵌入：LINE/Word2Vec 学习节点表示

Angel 的 **LINE 算法**可学习知识图谱节点的向量表示：

- **语义相似性**：将规则、约束节点嵌入向量空间，余弦相似度高的节点对可能是语义相关的一致性约束
- **缺失链接预测**：二阶邻近性可发现知识图谱中隐含但未显式连接的规则依赖
- **约束聚类**：嵌入向量可直接用于 KMeans 聚类（Angel 也提供），发现约束的语义分组

**应用流程**：
```
srs_kb_graph_v2.json (7720节点)
    → 边表格式转换 (srcId dstId weight)
    → LINE 训练 (embedding=128, order=2, negative=5)
    → 节点嵌入向量
    → 语义相似度矩阵 + 链接预测
    → 辅助一致性检测（发现潜在冲突的规则对）
```

### 10.1.3 PageRank/KCore 识别关键规则

- **PageRank**：识别知识图谱中影响力最大的节点（可能是核心 GJB 规则，违反它影响面最广）
- **K-Core**：识别稠密连接的核心规则子图，这些是 SRS 文档必须严格遵循的核心约束

## 10.2 Angel 参数服务器支撑大规模 SRS 文档训练

### 10.2.1 当前规模与扩展路径

SRS 项目当前 359 份文档，规模较小。但若扩展到全量 GJB 标准体系（数千份 SRS）或构建大规模约束分类模型，Angel PS 提供了扩展路径：

- **ANGEL_PS_SERVICE 模式**：保持现有 Spark 数据处理流水线，仅将模型参数托管到 Angel PS，实现平滑升级
- **PSF 自定义检测函数**：可将一致性检测逻辑封装为 PSF（如自定义 `ConsistencyCheckFunc`），在 PS 端批量执行规则匹配，减少数据传输
- **SSP 一致性模型**：`ANGEL_STALENESS > 0` 允许异步训练，适合 SRS 文档间相对独立的约束提取场景

### 10.2.2 具体算法适配

| SRS 任务 | Angel 算法 | 适配方式 |
|----------|-----------|----------|
| 约束分类（7 种约束） | LR/Softmax/FM | 稀疏特征（GJB 术语）用 FM，多分类用 Softmax |
| 文档相似度去重 | KMeans | 文档嵌入向量聚类 |
| 一致性冲突预测 | GBDT (FPGBDTTrainer) | 特征并行适合高维规则特征 |
| 在线增量约束提取 | FTRL | 新文档增量学习，适合持续扩展的数据集 |

### 10.2.3 GBDT 特征并行的特殊价值

SRS 约束检测的特征空间可能是高维的（GJB 规则条款 × 文档结构特征 × 术语特征），FPGBDTTrainer 的特征并行训练恰好解决高维直方图的内存与通信瓶颈。`balancedFeatureGrouping` 基于特征密度分组，适合 SRS 特征中常见的稀疏规则指示变量。

## 10.3 DataFlow-WebUI 可视化构建 SRS 处理 Pipeline

### 10.3.1 本地 Gradio 界面的直接复用

SRS 项目的工具链（`tools/srs_*.py`）可封装为 DataFlow 算子，通过 `operator_pipeline.py` 的 `DynamicOperatorSystem` 自动发现并生成可视化表单：

```
SRS 工具 → DataFlow 算子封装 → OPERATOR_REGISTRY 注册
    → DynamicOperatorSystem._discover_operators() 自动发现
    → inspect.signature 分析 __init__/run 参数
    → Gradio 表单自动生成
```

**具体映射**：

| SRS 工具 | 封装为算子 | init 参数 | run 参数 |
|----------|-----------|-----------|----------|
| `srs_mineru_parse.py` | MinerUParseOperator | mineru_path, model_source | input_pdf, output_dir |
| `srs_structurer.py` | StructurerOperator | — | mineru_json, output_json |
| `srs_constraint_extract.py` | ConstraintExtractOperator | llm_serving, constraint_types | input_json, output_json |
| `srs_consistency_checker_v2.py` | ConsistencyCheckOperator | z3_enabled, layers | input_json, rules_json |
| `srs_eval.py` | EvalOperator | — | pred_dir, gold_dir |

### 10.3.2 预定义 SRS Pipeline

参照 `kbcleaning_tools.py` 的四步模式，可定义 SRS 处理 Pipeline：

```python
class SRSConsistencyPipeline:  # 放入 api_pipelines/
    def forward(self):
        # 步骤1: MinerU 解析
        step1 = MinerUParseOperator(mineru_path="~/mineru-env/bin/python")
        step1.run(storage=storage.step())
        # 步骤2: 结构化
        step2 = StructurerOperator()
        step2.run(storage=storage.step())
        # 步骤3: 约束提取
        step3 = ConstraintExtractOperator(llm_serving=llm_serving, constraint_types=7)
        step3.run(storage=storage.step())
        # 步骤4: 一致性检测
        step4 = ConsistencyCheckOperator(z3_enabled=True, layers=["syntax","semantic","logic"])
        step4.run(storage=storage.step())
        # 步骤5: 评测
        step5 = EvalOperator()
        step5.run(storage=storage.step())
```

这样通过 `operator_pipeline.py` 的 Pipeline 模式即可一键执行完整的 SRS 一致性检测流水线，并在 Gradio 界面实时预览每步输出。

## 10.4 NL2Pipeline 将"检测 SRS 文档一致性"转为可执行 Pipeline

这是 DataFlow-WebUI 对 SRS 项目最具变革性的价值。

### 10.4.1 当前痛点

SRS 项目的工具链目前是命令行驱动的独立脚本，用户需要：
1. 理解 17+ 个工具的执行顺序
2. 手动配置每个工具的参数
3. 手动串联工具间的输入输出
4. 无法可视化整个处理流程

### 10.4.2 NL2Pipeline 解决方案

借助 DataFlow-Harness 的 NL2Pipeline 能力，用户只需自然语言描述：

> **"对这批 GJB 格式 SRS 文档进行三层一致性检测，包括语法、语义和逻辑层，使用 Z3 求解器，最后输出评测报告"**

Agent（Claude Code/Codex/Cursor）通过 DataFlow-Skills 的程序性知识，自动：

1. **选择算子**：从 OPERATOR_REGISTRY 中选择 MinerUParse → Structurer → ConstraintExtract → ConsistencyCheck → Eval
2. **链接 Schema**：通过 MCP 检查算子间输入输出 Schema 兼容性
3. **组装 DAG**：通过类型化增量突变构建 Pipeline DAG
4. **验证**：Validation Engine 检查 DAG 结构和 Schema 兼容性
5. **同步到画布**：DataFlow-WebUI 将 DAG 实时渲染为可视化流程图
6. **执行**：用户可在画布上检查、编辑、运行 Pipeline

### 10.4.3 程序性知识的关键作用

论文发现"Skills 在构建依赖隐式程序性知识时最有用"。SRS 一致性检测恰恰充满隐式知识：

- **执行顺序**：必须先 MinerU 解析才能结构化，必须先结构化才能提取约束，必须先有约束和规则才能检测一致性
- **参数依赖**：一致性检测需要 GJB 规则库路径、约束提取需要 LLM Serving 配置
- **条件分支**：Z3 求解仅在逻辑层启用时需要、图片-文本匹配仅在含图文档时需要

这些隐式知识编码在 DataFlow-Skills 中，Agent 无需用户逐一说明即可正确组装 Pipeline。

### 10.4.4 持久化与复用

NL2Pipeline 生成的不是一次性脚本，而是**持久可编辑的 Pipeline 制品**：
- SRS 团队可保存"标准 SRS 一致性检测 Pipeline"作为模板
- 新文档只需替换输入文件即可复用
- Pipeline 可版本化、共享、协作编辑

### 10.4.5 成本效益

DataFlow-Harness 论文报告的成本降低 72.5%、延迟降低 49.9% 直接适用于 SRS 场景：构建 SRS 处理 Pipeline 的成本和时间的显著降低，使团队可以更频繁地迭代检测策略。

## 10.5 综合应用架构建议

```
┌─────────────────────────────────────────────────────────────┐
│                  SRS 一致性检测智能化平台                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  DataFlow-WebUI (NL2Pipeline)                        │    │
│  │  "检测这批SRS文档的三层一致性"  →  可视化DAG + 对话   │    │
│  │         │ DataFlow-Skills (SRS程序性知识)             │    │
│  │         │ MCP (实时算子注册表)                        │    │
│  │         ▼                                            │    │
│  │  Validation Engine (DAG + Schema检查)                │    │
│  └───────────────────────┬─────────────────────────────┘    │
│                          │ 生成的Pipeline                     │
│  ┌───────────────────────▼─────────────────────────────┐    │
│  │  DataFlow Core (算子执行)                            │    │
│  │  MinerUParse → Structurer → ConstraintExtract       │    │
│  │  → ConsistencyCheck(Z3) → ImageTextMatch → Eval     │    │
│  └───────────────────────┬─────────────────────────────┘    │
│                          │ 知识图谱 + 约束 + 规则             │
│  ┌───────────────────────▼─────────────────────────────┐    │
│  │  Angel Graph (知识图谱分析)                          │    │
│  │  Louvain(规则社区) + LINE(节点嵌入) + PageRank(关键规则)│   │
│  │  Angel PS (大规模训练)                                │    │
│  │  FTRL(在线约束) + GBDT(冲突预测) + FM(约束分类)       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  数据: 359份SRS + GJB规则库 + 知识图谱(7720节点)             │
└─────────────────────────────────────────────────────────────┘
```

**三层赋能**：
1. **上层（WebUI + NL2Pipeline）**：自然语言驱动构建 SRS 处理 Pipeline，降低使用门槛
2. **中层（DataFlow Core）**：算子化封装现有工具，可视化编排与执行
3. **下层（Angel）**：图算法分析知识图谱发现深层一致性规律，PS 支撑大规模训练扩展

---

## 附录：DeepWiki 页面与源码路径索引

### Angel DeepWiki 页面

| 页面 | URL 路径 |
|------|----------|
| 架构与设计哲学 | `deepwiki.com/Angel-ML/angel/1.1-architecture-and-design-philosophy` |
| 核心组件 | `deepwiki.com/Angel-ML/angel/1.2-key-components` |
| 参数服务器 | `deepwiki.com/Angel-ML/angel/2-angel-parameter-server` |
| PS 核心概念 | `deepwiki.com/Angel-ML/angel/2.1-ps-core-concepts` |
| PS 函数 | `deepwiki.com/Angel-ML/angel/2.4-parameter-server-functions` |
| SoA 架构 | `deepwiki.com/Angel-ML/angel/3.1-spark-on-angel-architecture` |
| PSContext/PSVector | `deepwiki.com/Angel-ML/angel/3.2-pscontext-and-psvector` |
| 算法实现 | `deepwiki.com/Angel-ML/angel/4.2-algorithm-implementations` |
| 神经网络与图模型 | `deepwiki.com/Angel-ML/angel/4.3-neural-networks-and-graph-models` |
| 图计算 | `deepwiki.com/Angel-ML/angel/6-graph-computing` |
| 社区发现 | `deepwiki.com/Angel-ML/angel/6.2-community-detection` |
| 嵌入方法 | `deepwiki.com/Angel-ML/angel/7-embedding-methods` |
| 特征并行训练 | `deepwiki.com/Angel-ML/angel/8.2-feature-parallel-training` |
| YARN 部署 | `deepwiki.com/Angel-ML/angel/9.1-yarn-deployment` |

### Angel 关键源码路径

| 组件 | 源码路径 |
|------|----------|
| 配置系统 | `angel-ps/core/.../conf/AngelConf.java` |
| Master 服务 | `angel-ps/core/.../master/MasterService.java` |
| 矩阵上下文 | `angel-ps/core/.../ml/matrix/MatrixContext.java` |
| 行类型 | `angel-ps/core/.../ml/matrix/RowType.java` |
| 范围分区器 | `angel-ps/core/.../ps/storage/partitioner/RangePartitioner.java` |
| PSF 设计文档 | `docs/design/psfFunc.md`, `psf_get.md`, `psf_update.md` |
| PSContext | `spark-on-angel/core/.../context/PSContext.scala`, `AngelPSContext.scala` |
| PSVector | `spark-on-angel/core/.../models/PSVector.scala` |
| PSMatrix | `spark-on-angel/core/.../models/PSMatrix.scala` |
| GraphModel | `spark-on-angel/mllib/.../core/GraphModel.scala` |
| Louvain | `spark-on-angel/graph/.../community/louvain/` |
| FPGBDTTrainer | `spark-on-angel/mllib/.../gbdt/trainer/FPGBDTTrainer.scala` |

### DataFlow-WebUI 源码路径

| 组件 | 本地路径 |
|------|----------|
| 动态算子可视化 | `dataflow_repos/DataFlow/dataflow/webui/operator_pipeline.py` |
| 知识清洗界面 | `dataflow_repos/DataFlow/dataflow/webui/kbclean_webui.py` |
| 清洗工具 | `dataflow_repos/DataFlow/dataflow/webui/kbcleaning_tools.py` |
| SGLang 服务 | `dataflow_repos/DataFlow/dataflow/webui/kb_sglang_server.py` |
| 独立 WebUI 仓库 | `github.com/OpenDCAI/DataFlow-WebUI` |
| Harness 论文 | `arxiv.org/abs/2607.16617` |

---

> 本文档基于 DeepWiki 40+ 页面抓取、4 个本地源码文件精读（共 1141 行）、GitHub README 和 arXiv 论文摘要整合而成。Angel 部分覆盖架构/PS/SoA/编程模型/算法/部署全栈；DataFlow-WebUI 部分覆盖本地 Gradio 界面源码级分析、独立仓库架构和 Harness 论文实验结果。最后对 SRS 项目的应用价值从图算法、参数服务器、可视化 Pipeline、NL2Pipeline 四个维度进行了深度分析。
