# SOTA Baseline 重设计方案 v2（基于三路agent调研 2026-10-14）

## 〇、Z3之谜的结论（已查证）

| 版本 | A族得分 | 真相 |
|---|---|---|
| 旧"Z3"(experiment_report表C) | 0.858 | **元数据泄漏**：旧harness直接比对injection.original vs injection.injected字符串（archive/run_eval.py detect_param），Z3仅装饰性调用一次 |
| 纯Z3-SMT(v2) | 0.513 | **理论盲区**：x≥200∧x→100逻辑SAT；TPR=0.027（75条ge/le突变只中2条eq型） |
| 用户直觉"专门做提取" | 待测 | **SatLM(NeurIPS'23)正是该路线的SOTA**：LLM编译声明式约束→Z3求解 |

→ 需要补SatLM实验区分"提取层的价值"与"求解器的价值"。

## 一、分场景数据详析（family_evalset_v1 + GLM抽样错误方向）

### A·数值（n=150, 75inc/75con）
- 我方0.940：numeric通道132/150提前报出；错18条=表面怪异值(纯数字无单位/「」外复杂语境)
- GLM 0.971(29/30, FP=1)：LLM数值推理强
- v12 0.467：**同值异表面0.360(领域等价约定盲) + 突变0.573** —— 互补失败
- TSRCDF-SS 0.420：双编码器冻结无法捕捉数值细粒度差异
- Z3 0.513=理论盲区；QG-QA 0.773=抓突变但单位盲(200G≠204800MB误报)

### B·顺序（n=67, 全inc）
- 我方0.642：**通道截胡**——enum在同集异序的有序语境下提前判"consistent"截胡NLI
- v12 0.821最优：NLI整体语义判断强于通道的局部判断
- GLM 0.433(13/30, **FN=17**)：LLM把"不同顺序的功能表"判为一致——顺序敏感度缺失
- GLM与我方B族失败模式**互补方向**：GLM漏报、我方误报

### C·结构（n=293, 156inc/137con, 金标为主）
- 我方0.824：TABLE_ITEM_MISSING 0.953(NLI主导)但DIAGRAM_EXTRA 0.462/STEP_MISSING 0.618
- 根因：**verify通道需evidence输入才触发**，纯pair输入时图侧元素未显式化→靠NLI猜
- GLM 0.540(17/30, **FP=12**)：把良性省略约定(图省略参与者=合法)误判为矛盾
- TextFlow式textualize是修复方向（图→Mermaid节点集→确定性比对）

### D·术语（n=200, 100/100）
- 我方0.975：quote通道(引号恒等)+enum(集合)双保险
- GLM 0.733(22/30, FP=7)：同义词归并不足

### E·合规（n=36, 全inc）
- 我方0.806：count通道GJB-02/09全中(计数错配)；GJB-05(0/3)/LOGIC-04类靠NLI
- GLM/Erlangshen 1.000：通用"矛盾检测"模式即可覆盖(计数+注入在LLM眼里都是矛盾)
- **诚实结论**：E族是"通用方法意外强"的场景，非我方叙事重点

### F·语义残差（n=150, 82con/68inc）
- 我方0.993：quote/enum/numeric三通道覆盖领域等价约定判定
- v12 0.486：同值0.207(领域等价盲区最重)
- GLM 0.844：部分领域等价约定能力(数值换算)但术语/表面归并不足

## 二、SOTA Baseline重设计（三路agent调研综合）

### 新增baseline（按优先级）

| # | 方法 | 出处 | 机制 | 目标族 | 成本 |
|---|---|---|---|---|---|
| **1** | **SatLM-GLM** | NeurIPS'23 (arXiv:2305.09656) | GLM把pair编译为声明式SMT约束→Z3联合求解 | A族150条 | ~35min API |
| **2** | **CCP+偏序环检测** | ACL'25 CCP (2502.11425)+TL;QR | LLM抽原子偏序→双向+反事实询问→合并图**环检测**(确定性判据) | B族67条 | ~20min |
| **3** | **GLM-5协议judge** | MiniCheck(EMNLP'24)+2025-26协议共识 | rubric分族判据+label-blind+双序交换+温度采样软聚合 | 180抽样升级 | ~45min |
| 4 | TextFlow式textualize | arXiv:2412.16420+ECAI'24 | VLM图→Mermaid→节点集确定性比对 | C族 | 需VLM基建(后续) |
| 5 | Bespoke-MiniCheck-7B | bespokelabs 2024(LLM-AggreFact SOTA) | Qwen2.5-7B grounding verifier(4-bit) | 全族 | 需下载4GB(可选) |

### 调研明确排除的（有据）
- PAL/CoT+计算器：与领域等价约定/GLM-ZS区分度低→只作消融
- 中文NLI微调SOTA：**不存在**(CMNLI榜2021后停滞)——论文可主张的gap
- MiniCheck英文版：历史实验已证中文不兼容(0.500)
- TSRCDF-SS：已复现(0.575)，保持

### 论文叙事新增锚点（调研产出）
- **FISCAL(NeurIPS'25 WS)**: 领域合成数据使小verifier匹配GPT-4——**我方synth_s1+v19范式的文献支撑**
- **DoveScore(2505.15792)**: 逐条独立验证检测不出顺序montage——v12纯NLI的B族结构性盲区文献证据
- **GB/T-Bench(2608.06312)**: 中文国标审查14 LLM最强仅0.328——GJB同构域的难度背书
- **NLI4CT/Akhtar数值探针**: 数值NLI无全面胜出模型——A族难点锚点
- **Know Your Limits(2606.16118)**: LLM/Z3三范式失败模式系统对比——方法论参考

## 三、执行计划
1. SatLM-GLM(A族) — 直接回应用户"专门提取给Z3"直觉
2. CCP环检测(B族) — 修复共同短板+确定性判据贡献
3. GLM协议judge(180抽样) — "最强LLM+最优协议"对照
4. 重跑eval+更新报告六表
