# 统一Pair Dataset规范 v2.1（多模态根源版）

> v2.1变更: ①真实pair_dataset(366对: 表格+visio+图片+文本)作为原始输入层 ②context字段挂载多模态上下文 ③证据核验机制(缺失声称可被图节点确定性反驳) ④变异可直接作用于真实表格行
> 管线: `tools/build_pair_dataset_canonical.py` | 产出: `data/gjb_438c/pair_dataset_canonical/`

## 一、统一形态(Canonical Schema, 每条)

```json
{
  "id": "PD-<src>-<n>",
  "source": "srs_anchor | srs_mutation | srs_cf | nli_external",
  "pair": {"premise": "...", "hypothesis": "..."},
  "label": "inconsistent | consistent",
  "angle": {
    "scene": "sc1|sc2|sc3|sc4|sc5|text",          // 配对场景(角度1)
    "modality": "table-diagram|text-text|...",     // 模态配对(角度2)
    "type": "<48类 | NLI-CONTRA | IDENT>"          // 不一致类型(角度3)
  },
  "provenance": {
    "doc": "01..16 | external",
    "origin": "anchor:<qid> | mutation:<op> | cf:<kind> | converted:<raw>",
    "surface": "T1|T2|T3",                         // 表面模板编号(受控!)
    "protocol": ""                                  // 标签协议(裁决/构造/官方)
  },
  "split": "train|dev|test",
  "quality": {"contamination": "", "flags": []}
}
```

## 二、统一构建管线(六阶段, 所有源同一条)

```
Stage1 采集: 原始语料(16份SRS chunks / 外部NLI官方划分)
Stage2 配对: 候选对形成
   ├─ 锚点管线: 表格↔图结构对齐 → 差异提取 (真实差异, 非人造)
   ├─ 正文对: 同实体跨章节文本对 (变异用)
   └─ 外部: NLI官方句对 (已天然成对)
Stage3 表面化: 统一模板族编译(见三) — 双侧同构句式, 内容是唯一自由变量
Stage4 变异(仅合成源): 48类算子作用于pair的content槽 → label=inconsistent
   对称构造: 每个变异对(不一致)与原对(一致)成对保留
Stage5 标注: 构造标签(变异=确定) | LLM裁决(锚点=CoT/双LLM) | 外部转换(NLI映射)
Stage6 划分+污染控制: SRS文档级零重叠 | 外部官方划分 | 污染矩阵行为验证
```

## 二点五、多模态根源与证据核验(v2.1核心)

**原始输入层**: `data/gjb_438c/pair_dataset/`(366对×7场景) — 每对含table.csv(2195行)/visio_anchor.json(2409节点)/text.txt/image.png/meta.json。

**context字段**(锚点+pair变异项100%挂载):
```json
"context": {"pair_id", "scene_dir", "doc", "section", "table"(前12行), "diagram"(前25节点), "text", "image"}
```

**证据核验机制**(多模态根源的直接价值):
```
声称"X在图中缺失"(TABLE_ITEM_MISSING类) → 与context.diagram实际节点比对
→ 19.4%(248/1280)声称被反驳(元素实际存在=抽取错误)
→ 133条假real_bug标签翻转并隔离(evidence_quarantine.jsonl)
→ 训练集排除该类: 文本模型无法核验假叙述, 会引入假事实
```

**真实表格变异**(srs_pair_mutation源): 594条直接在真实表格行上生成(数值变异PARAM-02/状态变异TERM-03/逻辑变异LOGIC-02), 每条带完整多模态context。

## 三、统一表面化模板族(3个受控变体, 消除形态漂移)

**核心设计: 二元同构陈述对** — premise与hypothesis用同一句式, 仅(侧, 内容)不同:

```
T1(对照式): P="{主体}的{侧A}包含「{内容A}」。"   H="{主体}的{侧B}中没有「{内容B}」的对应元素。"
T2(规定式): P="{主体}的{侧A}规定：{内容A}。"      H="{主体}的{侧B}规定：{内容B}。"
T3(文档式): P="文档{位置}记载：{内容A}。"         H="文档{位置}记载：{内容B}。"
```

| 槽位 | 取值域 |
|---|---|
| 主体 | 该功能/该用例/该接口/系统 |
| 侧 | 正文/能力表/用例表/流程图/接口表/接口图 |
| 内容 | 从Stage2差异提取的实体文本 |

**受控性**: 所有源共用模板族 → 表面形态不再随数据源漂移(这正是v6模式绑定问题的根治设计); CCT表面反事实 = T1↔T2↔T3系统互换, 非临时改写。

## 四、变异方法(固定48算子, 对称构造)

```
48算子 = TERM(8) + PARAM(10) + LOGIC(11) + GJB(11) + 结构(8)
每个算子: (type, operation, label_flip) 三元组
作用位置: pair的content槽(数值/术语/顺序/存在性) — 不触碰模板结构
对称性: (原对,consistent)与(变异对,inconsistent)同源成对 → 难例负样本天然可控
语料支持: 40/48可测(8类军事语料无此表述, 已验证)
```

## 五、划分与污染(全源统一规则)

| 源 | 划分规则 | 污染标注 |
|---|---|---|
| SRS锚点/变异 | 文档级: train=01/02/05/06/08-16, dev=03, test=04/07 | qlora⚠(训练分布内) |
| 外部NLI | 官方划分(XNLI test/CMNLI dev/OCNLI test) | 行为验证矩阵(mdeberta/erlangshen⚠) |
| 真实金标 | 零训练重叠子集为唯一test | 干净 |

## 六、与旧资产的关系

| 旧资产 | 处置 |
|---|---|
| benchmark_full_v2(变异) | 内容槽保留, schema归一, 表面模板标注 |
| md_gold/gold_v2(裁决金标) | **重新表面化**(T1/T2/T3族) — 修复形态漂移 |
| unified_testset | 被本规范取代(其转换协议继承) |
| v6-v10模型 | legacy(旧异构形态训练); canonical数据集上重训=v11(未来工作) |

**诚实声明**: 重新表面化改变金标文本 → 已训模型成绩不可直接迁移到canonical集; 规范的价值是使**后续实验**(重训/CF/角度路由)建立在受控形态上。
