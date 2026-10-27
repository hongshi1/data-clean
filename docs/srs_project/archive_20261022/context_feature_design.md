# 上下文关联与特征提取——模块设计文档

> 输入起点：QA对（合成语料28,761条，question+answer+evidence指针）
> 核心任务：用question召回文档中相关的**文本/图片/表格**证据，并提取
> 可比较的特征，供下游一致性检测消费
> 代码：`algorithms/blackboard/hybrid_recall.py`（召回）、
> `kt_compilers.py`/`prose_compiler.py`/锚点资产（特征）
> 成文：2026-09-13

---

## 1 数据流总览

```
QA对(question, answer)
   │
   ▼ ①查询理解: question → 检索实体词
   │
   ▼ ②五通道召回: 实体词 → chunks(5231: 文本3643/表格1207/图片381)
   │     lexical ─ sparse(BM25) ─ dense(BGE) ─ structural(ID桥) ─ multimodal(VLM)
   │     └→ cascade融合 → top-20命中{chunk_id, type, section, snippet, tier}
   │
   ▼ ③特征提取: 命中的原始内容 → 结构化特征
   │     表格→κ_T    正文→κ_P    图→锚点/VLM    ID→ID-Graph
   │     └→ 统一比较单元(元素宇宙Ω)
   │
   ▼ ④下游: 方向B一致性检测(分歧→裁决) / QA答案验证
```

## 2 上下文关联：召回设计

### 2.1 查询理解（question→实体词）

真实输入是自然语言问句（"查询收件箱和发件箱接口主要是用来做什么的"），
不能直接当检索词。两级提取：

- **LCS检索反推**（默认）：对问句跑BM25取top-3 chunk，取问句与
  chunk文本的**最长公共子串**——文档命中的片段含实体字面，反推即实体
  （上例→"查询收件箱和发件箱接口"）；
- 停用词剥离（对照）：ID正则 > 剥停用词后最长中文段——会切断
  "和/或"连接的复合实体，实测R@20低0.148。

### 2.2 五通道召回（每路独立ranked list）

| 通道 | 机制 | 单通道R@20 | 角色 |
|---|---|---|---|
| **lexical** | 精确子串+双关键词全命中（事实性，深度200全收） | 0.847 | 主力：GJB实体字面稳定 |
| **sparse** | BM25（k1=1.5, b=0.75；CJK 2字滑窗+ASCII token） | 0.792 | 部分命中泛化 |
| **dense** | BGE-large-zh 1024维，检索指令前缀，索引磁盘缓存 | 0.476 | 排版变体的语义召回 |
| **structural** | ID-Graph硬桥：实体→mentions→全部登记章节→章节chunk | 0.021 | 章节完整性（跨文档同名消歧） |
| **multimodal** | VLM key_elements匹配→(doc,fig号)→image chunk | ~0 | **figure模态召回的唯一来源** |

### 2.3 融合（cascade级联）

**不用等权RRF的原因**（实测）：通道强度悬殊（0.847 vs 0.021）时民主
投票被弱通道稀释——RRF 0.828 < lexical单通道 0.847。

cascade设计：
- **事实通道直通**：lexical顺序直通到预算位（完整子串命中才直通，
  宽松命中降级）；structural=4席位且**只补未覆盖章节**；multimodal=2席位
  （figure模态保底——Mod指标是集合判定，≥1命中即得分）
- **概率通道RRF填充**：sparse+dense按倒数排名融合填剩余配额
- 席位是显式权衡：structural/multimodal席位↑ → Mod/Sec↑ 但R@K↓
  （消融实测：-structural R@20+0.014但丢章节补全；-multimodal Mod
  0.995→0.863）

**当前指标**（口径修正后，300条）：R@10=0.770 / R@20=0.846 /
MRR@10=0.995 / modality=0.995 / entity=1.000；问句模式0.802。

### 2.4 召回结果的处理与QA对闭环

召回的top-20 hits不是终点，按下游消费分三步组装：

**① 多模态证据分组**：hits按type分为text/table/figure三组（模态
完整性即§4的Mod指标语义）；同章节命中聚合为"章节证据包"。

**② 聚合条目组装**（方向A的最终输出形态）：对召回命中的实体，
从graph_store的item（978条）或黑板证据读取聚合条目：
`{entity_id, occurrences[{location, section, modality, text_preview}],
chain_completeness}`——chain_completeness=|{text_table, figure,
trace} ∩ 实际召回位置类型|/3，衡量"该实体的文档证据链是否找齐"
（正文+图+追溯三处都有=1.0）。

**③ QA对的answer验证闭环**（QA对输入的完整消费）：
```
question → 召回证据集(文本/图片/表格)
answer   → 与证据集做支持性判定:
            - 判断型QA: answer的声明是否被证据蕴含(NLI/词法)
            - 定位型QA: answer的章节/位置是否在召回命中内
            - 不一致QA: answer声明的矛盾是否可由多模态证据定位
```
即：**召回质量直接决定answer验证的上界**——证据没召回，
answer对错无从判定（这是§5评测E1循环性之外的另一层意义：
召回指标是下游所有任务的先决条件）。

黑板运行时的对应实现：`run_task`的CONTEXT_RECALL任务类型走
Router→五通道Agent写板→expanded_recall二轮检索（从已召回证据
提取高频CJK bigram扩展查询）→Critic门控（覆盖不足→escalation/
预算耗尽→abstain）→final_context输出聚合视图。

## 3 特征提取设计（各模态编译器）

原则：**只字面结构化，不做语义判断**（语义判断留给检测层）——
解析输出即FACT（置信度1.0），不确定性压缩到通道置信度里。

| 模态 | 编译器 | 输入 | 输出特征 |
|---|---|---|---|
| 表格 | **κ_T**（5种表型：capability/usecase/interface/subfunction） | table.csv | 元素列表{名称/ID/步骤/异常流/交互}，与图节点同构可比 |
| 正文 | **κ_P** | text.txt | 五元组：behaviors（11个GJB动词+宾语）/enumerations（触发词+顿号切割+剥"等"尾）/constraints（14比较词×17单位+param_hint）/references（图表节）/ids + 句级角色 |
| 图 | **born-digital锚点**（XML直读） | .doc内嵌Visio OLE | 373图3757节点2610边（文本/坐标/类型/方向三重证据），构造性保真 |
| 图 | VLM提取（θ校准） | image.png | 节点/边（HYPOTHESIS；校准：节点召回94.4%、幻觉1.0%、边多余26.4%） |
| 图 | OCR | image.png | 独立字符证据（span不在OCR集→幻觉标记） |
| 实体 | ID-Graph | 971个ID | 568实体×1613 mention（8类位置分布：text 561/能力表465/接口表150…） |

**统一比较单元——元素宇宙Ω**：{节点存在exst, 标签lab, 类型type,
边方向dir, 条件cond, 参与者act, 参数值val}——每个元素=下游二元比较
的原子单元（图侧观测值 vs 表侧真值），方向B的类型化分歧Δ即Ω上的
编辑操作。

## 4 评测体系与标签来源

### 4.1 评测集构造链路（retrieval_evalset，300条）

```
① 采样100个实体（seed=42）
   ├─ 60% 有ID实体：从ID-Graph的mention context正则提取中文名（期望最可靠）
   └─ 40% 语义实体：LightRAG图谱中3~20字实体（排除泛词）
② kimi对每实体生成3种问法（功能定义/结构/溯源型）→ 300条question
③ 标签生成：期望chunk_ids/sections/locations
   = 三条确定性规则合并（LLM不标答案）：
     a) 字符串匹配：5231 chunks全文逐字搜索实体名/ID
     b) ID-Graph精确锚定：实体的全部登记章节
     c) VLM图片元素：key_elements命中图
④ kimi+GLM交叉核验三规则通过后的标签
难度：len(sections)≤2为easy（78条26%），其余hard（222条74%）
```

### 4.2 指标口径（含已修复的三个bug）

- entity_found：**按完整chunk文本**判定（原snippet[:80]截断造成
  51/87例假阴性）
- modality_recall：chunks类型image归一为期望figure（原类型名不匹配，
  figure召回从未被算对）
- 全库检索不做doc过滤（原取expected.docs[1]过滤，但docs是多文档
  标注，滤掉了真正含实体的文档36例）

### 4.3 标签来源的诚实分析（关键不完备）

| 问题 | 具体表现 | 后果 |
|---|---|---|
| **循环性**（最严重） | 期望标签由规则a"chunks全文搜索"生成——与lexical通道的召回机制**同源**；规则b与structural通道同源 | 高分部分是自证（"用自己的索引确认自己"），lexical的0.847含虚高 |
| 无人工抽检 | 计划"抽50条人工核对Kappa≥0.8"从未执行 | 标签质量无人类仲裁，三个口径bug存在了一个月才被发现 |
| 实体采样偏差 | 60%实体来自ID-Graph登记（仅≥2次出现的ID）+40%来自LightRAG抽取（有噪声） | 评测分布偏向"已登记实体"，真实用户问法（未登记实体/变体）覆盖不足 |
| 期望本身有噪声 | 多文档doc标注错误、期望chunk_ids含无关条目 | 即使算法全对也拿不到满分 |

**更诚实的协议**：问句模式（输入原始问句，LCS反推实体，不用entity
字段）R@20=0.802——不作弊的上界参考；**根治方向**：用textutil独立
解析（与检索索引不同源）生成期望 + 人工抽检50条Kappa。

## 5 设计不完备清单（按环节，含改进方向）

### 召回侧
| # | 不完备 | 证据 | 改进方向 |
|---|---|---|---|
| R1 | R@20物理上限：期望chunk>20的查询装不下 | 失败归因426/2862为融合截断 | 按需扩top_k（下游检测消化）或章节聚合输出 |
| R2 | structural依赖ID-Graph登记，深层小节盲区 | 180/2862所有通道都未召回，75例section失败全是"mentions没登记" | 全文级实体位置索引（补stage0登记） |
| R3 | dense在军事术语判别力弱 | 单通道R@20=0.476 | 领域语料微调BGE（28,761条QA可用） |
| R4 | 无重排器 | R@10=0.770 vs R@20=0.846，排序质量是缺口 | cross-encoder重排（候选已就位） |

### 特征侧
| # | 不完备 | 证据 | 改进方向 |
|---|---|---|---|
| F1 | κ_T是正则不是文法 | 约束列污染、跨步骤吞并两bug | 表格CFG+属性文法（设计稿已有，~2天） |
| F2 | κ_P嵌套枚举被切断 | "包括A（分为A1、A2）、B"按顿号切碎 | 递归枚举解析 |
| F3 | 锚点边重建不完整 | edge_extra 26.4%部分来自锚点自身 | p_anchor_edge_miss>0建模进θ |
| F4 | 图片chunk的text="[图片]" | 381条全空（检索层已用VLM分析绕过） | 富化文本回写进chunks资产 |

### 评测侧（P0级）
| # | 不完备 | 改进方向 |
|---|---|---|
| E1 | 标签循环性 | textutil独立期望源（与索引不同源） |
| E2 | 无人工金标 | 50条人工抽检Kappa≥0.8；160条uncertain人工仲裁后全套重评 |
| E3 | 采样偏差 | 补充未登记实体/用户真实问法分布 |

### 系统侧
| # | 不完备 | 改进方向 |
|---|---|---|
| S1 | ContextGraph（graph_store激活）与黑板hybrid_recall两线未合流 | graph_store作为黑板第15通道/统一召回入口 |
| S2 | 图-表-文的对齐没有统一金标 | 分歧驱动标注构建首个三模态对齐benchmark |

---

## 6 模块运行入口与资产指针

### 6.1 代码入口

| 入口 | 用法 | 说明 |
|---|---|---|
| 召回器 | `from algorithms.blackboard.hybrid_recall import HybridRecaller; rec.recall(query, top_k=20)` | 五通道+cascade融合；dense不可用时自动降级四路 |
| 查询理解 | `detect_entity(question, store)` | LCS检索反推（问句→实体） |
| 黑板运行时 | `python -m algorithms.blackboard.runner --task recall --entity 数据获取` | 含Critic门控+二轮扩展+审计日志 |
| 评测 | `python tools/eval_hybrid_recall.py` | 全消融+难度分层+runs协议落盘 |
| 召回评测对照 | `python tools/eval_recall_v3.py` | v0/v2/v3基线对比 |

### 6.2 数据资产依赖

| 资产 | 规模 | 消费通道 |
|---|---|---|
| srs_chunks.json | 5231（文3643/表1207/图381） | lexical/sparse/dense的检索对象 |
| dense_index.pkl | 5231条BGE向量（磁盘缓存） | dense通道（首次构建107s，之后0s） |
| id_document_graph.json | 568实体×1613 mention | structural通道 |
| srs_image_analyses.json | 379条VLM分析 | multimodal通道（(doc,fig)→image chunk映射） |
| anchor_v2/anchors_v2.json | 373图3757节点2610边 | 特征提取的图侧真值 |
| graph_store/ | 6类节点/23742边/978条目 | 聚合条目组装（未并入黑板，见S1） |
| retrieval_evalset.json | 300条 | 评测（标签来源见§4） |

### 6.3 关联文档

- 详细实验数字：`docs/srs_project/hybrid_recall_report.md`（主表/消融/负结果）
- 方向B（检测侧）设计：`ACDD_method_proposal.md` + `method_design_formal.md`
- 项目全景：`00_requirements_and_route_overview.md`
- 本模块代码测试：`tests/test_hybrid_recall.py`（11例）+ `tests/test_recall_v3.py`（6例）

---

## 附：本模块的输出契约（下游消费）

```
召回输出: top-20 hits {chunk_id, type(text/table/image), section, doc,
        snippet, rank, tier(factual/rrf), channels[...], rrf_score}
特征输出: κ_T/κ_P/锚点/VLM各自的结构化payload
统一单元: Ω元素(带图侧观测+表侧真值) → 方向B的类型化分歧Δ
评测锚点: R@20=0.846 / MRR=0.995 / Mod=0.995（口径修正后；
        含标签循环性风险，见§4.3）
```

---

## 修订记录

| 日期 | 修订 |
|---|---|
| 2026-09-13 | 初版：§1-§5（召回/特征/评测/不完备） |
| 2026-09-13 | 补§2.4（召回后处理与QA对闭环）、§6（运行入口与资产指针） |
