# 82 上下文关联算法框架总图与代码整合进度

日期：2026-10-31 | 仓库清理完成（根目录13文件/22目录全核心）

---

## 一、上下文关联算法框架（一张图）

```mermaid
graph TB
    subgraph IN["输入层"]
        A1["16份GJB SRS<br/>(.doc)"]
    end

    subgraph L0["L0 解析与结构化(已完成)"]
        B1["解析联邦<br/>MinerU+textutil+Visio"]
        B2["结构化语料 27,473对象<br/>claims 11,869 / 表 1,207 / 图节点 5,165"]
    end

    subgraph L1["L1 证据召回(已完成, R@1=0.608)"]
        C1["O1-unit多头冻结投影<br/>语义单元头+词面头+场景路由"]
        C2["两阶段精排<br/>cross-encoder +12.1pt"]
        C3["BGE本地编码<br/>1024维GPU"]
    end

    subgraph L2["L2 证据提纯(已完成, 74号收敛)"]
        D1["F1 作用域过滤<br/>锚点+ID豁免"]
        D2["F2 粒度归一<br/>表行/句级"]
        D3["F3 形态合同<br/>40项检测项"]
    end

    subgraph L3["L3 三态裁决(已完成, 16/17=94.1%)"]
        E1["L1确定性专家<br/>entity/id_join/enum/Z3"]
        E2["L2 NLI残差<br/>mDeBERTa本地"]
        E3["聚合 refute>NIE>support"]
    end

    subgraph OUT["输出层"]
        F1["Finding<br/>227候选违例"]
        F2["VerificationPack<br/>claim级明细+提纯审计"]
        F3["覆盖差异检测<br/>876 findings"]
    end

    A1 --> B1 --> B2
    B2 --> C1 --> C2
    C3 -.-> C1
    C2 --> D1
    D1 --> D2 --> D3
    D3 --> E1 --> E2 --> E3
    E3 --> F1 & F2
    B2 -.-> F3
```

## 二、算法代码整合进度

| 层 | 模块 | 代码位置 | 测试 | 状态 |
|---|---|---|---|---|
| L0 | 解析联邦 | tools/build_structured_corpus.py | MANIFEST保护 | ✅ |
| L1 | O1-unit召回 | algorithms/context_linking/evidence_recall/ | 5测试 | ✅ |
| L1 | 精排 | evidence_recall/rerank.py | 已验证+12.1pt | ✅ |
| L2 | 原子化 | context_linking/atomizer.py | 15测试 | ✅ |
| L2 | 打分器族 | context_linking/pair_scorers.py | 8测试 | ✅ |
| L2 | 提纯门面 | consistency/evidence_purifier.py | 7+2测试 | ✅ |
| L2 | 覆盖检测 | consistency/coverage_detector.py | 7测试 | ✅ |
| L3 | 三态裁决 | consistency/qa_module.py | 20测试 | ✅ |
| L3 | NLI客户端 | consistency/nli_local.py | GPU就绪 | ✅ |
| 服务 | 算法服务 | srs_verify_package/service/ | 联调12/12 | ✅ |
| 服务 | 后端接入 | deploy/.../services/algo_client.py+verify.py | 联调通过 | ✅ |
| 服务 | 前端接线 | frontend/index.html loadRealQA+cstStartCheck | 浏览器验证 | ✅ |

**核心数字**: 召回R@1=0.608 / 违例查全16/17 / gold保留35/35 / 
L2提纯-17.8%无损 / 参数校准3项(81号)

## 三、清理后的仓库结构

```text
data_clean/
├── algorithms/          ★核心算法(141文件)
│   ├── context_linking/ 召回+原子化+打分
│   └── consistency/     提纯+裁决+覆盖
├── tools/               ★工具脚本(278个, 含archive/)
├── tests/               ★测试(144文件, 1486+通过)
├── data/gjb_438c/       ★数据资产(MANIFEST保护)
├── knowledge/           GJB词典+规则库
├── srs_verify_package/  ★分发包(41模块+服务+Docker)
├── deploy/nkuDataProject/ ★平台(前后端+四服务编排)
├── docs/srs_project/    ★项目文档(81号系列)
├── models/              BGE+mDeBERTa(GPU)
├── config/              证据合同+场景配置
├── scenario5/           并行会话场景5工作
├── references/          文献
└── literature/          调研笔记
```

## 四、本轮清理执行记录

- 根目录一次性脚本/PNG/解压目录: **全部清除**(并行会话同步执行)
- 保留: 全部核心目录+平台+分发包
- 未动: scenario5(并行活跃), easy-dataset(gitignored外部工具)
