# 统一测试数据集格式规范 v1.0

> 目的: SRS不一致性检测任务没有现成公开基准。本规范定义统一格式, 使公开NLI数据集可转换接入,
> 与自有GJB资产同场评测。构建工具: `tools/build_unified_testset.py`, 产出: `data/gjb_438c/unified_testset/`

## 一、任务定义

**输入**: 一对陈述 (premise, hypothesis)
**输出**: 二元判定
- `inconsistent` — 两者对同一事物给出矛盾描述(值/顺序/术语/范围/组成矛盾, 或一方缺失关键内容)
- `consistent` — 两者一致、可共存或无法断定矛盾(不报警)

**设计决策: neutral的归宿**。NLI三分类的neutral(无法确定)在本任务中映射为`consistent`:
不一致性检测是"报警/不报警"的二元决策, 无法证明矛盾的对不报警。
这与矛盾检测(contradiction detection)文献的二值化惯例一致。
`label_raw` 保留原始三分类, 供三分类分析。

## 二、统一Schema(jsonl, 每行一条)

```json
{
  "id": "UT-xnli-00042",
  "source": "xnli_zh",
  "domain": "general",
  "split_origin": "test",
  "premise": "...",
  "hypothesis": "...",
  "label": "inconsistent",
  "label_raw": "contradiction",
  "type": "NLI-CONTRA",
  "contamination": "mdeberta",
  "meta": {}
}
```

| 字段 | 取值 | 说明 |
|---|---|---|
| source | xnli_zh / cmnli_dev / ocnli_test / gjb_bench / gjb_gold | 数据来源 |
| domain | general / srs_synthetic / srs_real | 域: 通用/合成SRS/真实SRS |
| split_origin | test / dev / held-out | 原始数据集的划分(测试规范用) |
| label | inconsistent / consistent | **统一二元标签(评测目标)** |
| label_raw | 原始标签 | contradiction/entailment/neutral 或48类型或real_bug等 |
| type | NLI-CONTRA / NLI-ENTAIL / NLI-NEUTRAL / TERM-01..48 / 结构类型 | 细粒度类型 |
| contamination | 模型族列表(逗号分隔)或空串 | ⚠该来源进入过哪些模型训练数据 |
| meta | dict | 源特有信息(doc_id, check_item, dtype, 用例名等) |

## 三、公开数据集→统一格式的转换方案

### 3.1 NLI三分类→二元(核心映射)

| 原始标签 | label | type | 语义 |
|---|---|---|---|
| contradiction | inconsistent | NLI-CONTRA | 矛盾=报警 |
| entailment | consistent | NLI-ENTAIL | 蕴含=不报警 |
| neutral | consistent | NLI-NEUTRAL | 无法定论=不报警 |

### 3.2 各源转换规则

| 源 | 原始格式 | 字段映射 | 采样 |
|---|---|---|---|
| XNLI-zh (facebook/xnli test) | premise/hypothesis/label(0/1/2) | label 0→entailment 1→neutral 2→contradiction, 再按3.1二元化 | 全量5010(平衡) |
| CMNLI dev (fenffef/cmnli) | sentence1/sentence2/label(字符串) | 字段改名+按3.1二元化; 无效标签('-')剔除 | 全量12426→12441-185 |
| OCNLI test (Fred666/ocnli_test_std.csv) | premise/hypothesis/label(0/1/2) | 同XNLI规则 | 全量10097(近平衡) |
| GJB基准 test (benchmark_full_v2.jsonl) | premise/hypothesis/expected_label/check_item | expected_label→label, check_item→type(48类型体系), meta带doc_id/scene | 全量922 |
| GJB金标 (gold_verbalized_23.json) | premise/hypothesis/label(1/0) | 1(real_bug)→inconsistent, 0(benign)→consistent | 全量23 |

### 3.3 污染矩阵(行为验证版, 400条分层样本seed42)

| source | mDeBERTa族 | Erlangshen族(含QLoRA) | GLM-5 | 词法 |
|---|---|---|---|---|
| xnli_zh | ⚠(训练含XNLI, +0.142实证) | 干净(0.922) | 未知 | 干净 |
| cmnli_dev | 干净(0.743*) | 干净(0.890, dev划分未被训练) | 未知 | 干净 |
| ocnli_test | 干净(0.743) | ⚠⚠(F1=1.000背诵级实锤) | 未知 | 干净 |
| gjb_bench | 干净 | ⚠(QLoRA训练用train划分, test零重叠; 同为合成分布) | 干净 | 干净 |
| gjb_gold | 干净 | 干净(从未见过) | 干净 | 干净 |

*注: mDeBERTa在cmnli_dev未单独测; 其干净性来自cmnli为MNLI翻译dev而mDeBERTa训练用XNLI/MNLI训练划分的推断。

**验证方法(可复现)**: 背诵级成绩(F1≥0.99)=污染实锤; 正常水平(<0.95)=干净。
**规则**: 报告某模型在某源上的成绩时, 若contamination包含该模型族, 必须标注⚠, 不得作为有效能力主张。

## 四、评测协议

1. **采样**: 每源分层采样(类平衡或按源比例), seed=42, 评测脚本内实现(数据集本身存全量)
2. **指标**: 二元P/R/F1(positive=inconsistent), NLI三分类另算accuracy
3. **成对比较**: 所有方法必须在**同批样本**上对比(采样在方法间共享, 不各自采样)
4. **分层报告**: general域(域外)/ srs_synthetic(域内上限)/ srs_real(真实场景)三层, 不跨层混淆

## 五、扩展新数据源的接入清单

接入任一新NLI/RE数据集只需3步:
1. 提取 (premise, hypothesis, 原始标签) 三元组
2. 实现"原始标签→{inconsistent, consistent}"映射函数(在build_unified_testset.py注册)
3. 确定contamination归属(查该数据集是否公开于各模型训练截止前+训练语料声明)

候选但未接入(供未来扩展):
- **XNLI-zh dev**(避免与test混用), **CMNLI test**, **SNLI-zh翻译版**
- **RE域英文**: PURE(分类非对子), C3P, Dronology(分类标签, 需构造成对方案: 同一requirement的两版本改写)——均非现成不一致检测对, 接入成本高
- **NLP4RE矛盾对数据集**: 据我们所知无公开中文SRS不一致检测对数据集(这正是本数据集的学术价值)
