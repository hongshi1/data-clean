# URE数据集规范(单元检索评测数据集)与公开数据集接入方案
## Unit Retrieval Evaluation Dataset — 格式定义 + 外部数据转换

> 目的: 我们的任务(结构化文档的单元级检索)没有现成公开基准.
> 本规范定义一个自包含格式, 使得: ①GJB数据资产固化为标准数据集;
> ②公开数据集(WTQ/TabFQuAD/MP-DocVQA/HotpotQA等)可转换进同一格式,
> 实现方法的外部效度检验.
> 成文: 2026-09-30 | 构建工具: tools/build_ure_dataset.py

---

## 一、数据集格式(Canonical Format)

一个数据集 = 一个JSON文件, 四个顶层字段:

```json
{
  "meta": {
    "name": "GJB-URE-v1",
    "version": "1.0",
    "language": "zh",
    "task": "unit-level retrieval over structured documents",
    "created": "2026-09-30",
    "description": "16份GJB 438C SRS, 378图+1207表, 三个场景查询"
  },
  "corpus": [
    {
      "doc": "01数据获取转换分系统需求规格说明-终稿",
      "chunk_id": "01数据获取转换分系统需求规格说明-终稿_I0036",
      "type": "image",                  // image | table | text
      "scene": "diagram",               // diagram | table | prose (模态场景)
      "title": "图 6 文电收发与管理功能用例图",   // 标题单元(caption/表标题)
      "units": ["文电处理服务", "用户", "..."],   // 内容单元(不含title)
      "n_units": 12,
      "section": "3.2"
    }
  ],
  "queries": [
    {
      "query": "文电收发与管理的用例图在哪",
      "expected": ["12文电处理需求规格说明-终端_I0055"],
      "scene": "image",                 // 与corpus.scene对应的查询场景
      "source": "user_sim",             // user_sim|param_v2|legacy|docT5|deep_row_llm
      "split": "eval",                  // eval | train
      "fold": 2                         // 0-3, 文档级4折
    }
  ],
  "protocol": {
    "n_folds": 4,
    "fold_rule": "doc序号 mod 4 (文档级隔离)",
    "candidates": "测试fold内的全部同type chunk",
    "query_prefix": "为这个句子生成表示以用于检索相关文章：",
    "metrics": ["R@1", "R@5", "MRR@10"]
  }
}
```

### 1.1 字段约束(构建工具强制校验)

| 字段 | 约束 | 校验 |
|---|---|---|
| corpus[].chunk_id | 全局唯一 | 唯一性 |
| corpus[].units | 任意可为空(标题单元可能缺失) | — |
| queries[].expected | 必须全部存在于corpus | 引用完整性 |
| queries[].fold | 0..n_folds-1 | 范围 |
| 每个(fold) | eval查询≥1 且 对应类型corpus≥5 | 可评测性 |
| scene | ∈ {image, table_caption, table_deep} (查询级) | 枚举 |

### 1.2 场景(scene)的语义定义(对应我们三场景)

| scene | 语义 | 答案位置 | 对应方法组件 |
|---|---|---|---|
| image | 自然语言→图(节点级跨模态) | 图标题+节点+VLM元素 | 单元检索图实例+CMSC融合 |
| table_caption | 标题级表检索(目录型) | 表标题 | gate+路由 |
| table_deep | 深行内容检索(正文行型) | 表格深处行(>800字符) | 单元拆分修复截断盲区 |

### 1.3 数据集卡(构建工具自动生成stats)

```
GJB-URE-v1:
  corpus: 378图(节点+VLM元素单元) + 1207表(行单元) = 1585 chunk, 12423+1582单元
  queries: eval 1125条(image 1007 + table_deep 118) + train 2407条
           (docT5 1532 + deep_train 585 + ...)
  folds: 4, 文档级隔离
```

## 二、GJB-URE-v1 构建(已落地, 经审计修复)

来源资产→目标字段映射:

| 来源 | →queries.scene | →split | →source | 数量 |
|---|---|---|---|---|
| `evalset_v3.json` | image | eval | user_sim/param_v2/legacy | 1007 |
| `deep_row_queries.json` | table_deep | eval | deep_row_llm | 118 |
| `doc_queries.json`(表格目标) | table_caption | train | docT5 | 773+768 |
| `deep_row_queries_train.json` | table_deep | train | deep_row_llm | 585-118(去污染) |

数据集卡(2026-10-06审计修复后实测):
```
GJB-URE-v1:
  corpus: 1588 = 全部381图(含3张无源空单元图) + 1207表, 14019单元(精确去重)
  queries: eval 1125(image 1007 + table_deep 118) + train 2008(去eval污染)
  folds: 4, 约定=(doc序号-1) mod 4(与全部评测工具一致), 一致性97.3%
         (2.7%为已知噪声: 死块gold 10条+跨文档legacy锚定30条)
```

审计修复(见21号文档§三): fold约定统一(原doc%4错位98.8%)、
train去污染(原118条eval逐字泄漏)、单元去重(41.2%重复, k=1行为不变)。

构建命令:
```
python tools/build_ure_dataset.py    # → data_assets/evalsets/gjb_ure_v1.json
```
python tools/build_ure_dataset.py    # → data_assets/evalsets/gjb_ure_v1.json
```

## 三、公开数据集接入方案(转换器已实现, 网络恢复后即可跑)

### 3.1 候选数据集与映射表

| 公开数据集 | 任务匹配点 | 转换映射 | 测我们什么 |
|---|---|---|---|
| **WTQ** (WikiTableQuestions) | 真实用户问题→表检索 | 表→corpus(type=table, units=行"header=value"), 问题→queries, 每问自带gold表id→expected; scene=table_deep(真实问题多问行内容) | 表单元检索的外部效度(英文, 2100表/2万问) |
| **ViDoRe/TabFQuAD** | late-interaction检索基准(官方ColPali评测) | 页→corpus, 给定query→页映射; 表页用我们的HTML/文本解析出单元 | 与ColPali式方法在同一基准家族对比 |
| **MP-DocVQA** | 多页文档检索 | 页→corpus, 问题→queries | 多页文档的单元检索 |
| **FeTaQA** | 表格自由问答 | 同WTQ | 同WTQ |
| **HotpotQA** | 段落检索(文本模态) | 段落→corpus(type=text, units=句子) | 文本单元模态(模块A扩展) |
| **DuReader-zh** | 中文段落检索 | 同上, 中文 | 中文文本模态 |

**英文注意**: bge-large-zh对英文覆盖有限(排序可用但非最优)——
外部效度结论需声明该限制, 或换bge-m3复跑(下载需网络).

### 3.2 WTQ转换器(已跑通真实数据: 2026-10-06)

```
# 真实WTQ(经hf-mirror.com镜像, lighteval parquet版, 已验证)
python tools/convert_public_dataset.py --source wtq --out data/gjb_438c/data_assets/evalsets/wtq_ure.json
# → 2100表/42394单元/18486真实用户查询, 引用完整性自动保证

# 离线夹具(3表6问, 无网络验证管线)
python tools/convert_public_dataset.py --source wtq-fixture --out <临时路径>
```

**外部效度pilot已跑**(tools/eval_wtq_ure.py, 2000查询×2100全候选):
B1 dense 0.155/0.282/0.212 → O1单元 0.272/0.423/0.339
(+75%相对R@1, 与GJB方向完全一致; 绝对值低=中文模型跑英文的已知限制,
声明写入结果JSON). FeTaQA(带行级gold)为下一优先(见21号文档§一).

映射规则(代码即规范):
```
WTQ table: {pageTitle, headers: [...], rows: [[...]], tableId}
  → corpus entry:
     chunk_id = f"wtq_{tableId}"
     title    = pageTitle
     units    = ["h1=v1 h2=v2..." for each row]   (与GJB表同序列化)
     type     = "table", scene = "table"

WTQ question: {question, tableId, answers}
  → query entry:
     query    = question
     expected = [f"wtq_{tableId}"]    (WTQ每问绑定gold表, 引用完整性免费保证)
     scene    = "table_deep"           (真实问题多数问行内容, 不靠标题)
     split    = "eval", fold = hash(question) mod 4 (无文档级分组→按查询hash分折)
```

**离线验证**: 转换器自带WTQ格式样例夹具(3表6问, 内嵌于代码),
`--source wtq-fixture`离线跑通全管线(解析→映射→校验), 网络无关.

### 3.3 通用接入协议(新数据集四步)

1. **源格式探查**: 表/页/段落结构与gold关联(question→answer位置)
2. **单元提取器**: 用我们的解析器家族(HTML表解析/文本切分)产出units
3. **gold映射**: 每问至少一个expected chunk_id(引用完整性硬校验)
4. **分折**: 有文档/来源分组→文档级; 无→查询hash, 并在protocol注明

## 四、复现与保护

- `gjb_ure_v1.json` 入MANIFEST(防静默重生成)
- 语义等同性: 从URE v1出发应能复现锁定的评测数字
  (evalset_v3的1007 image查询→0.619/0.846/0.716等)
- 后续新场景(文本模态/新文档集)按§1格式扩展, 版本号递增
