# 项目数据资产地图（全量盘点）
> 2026-09-16 | 三agent分区盘点综合 | 本文档是后续一切数据工作的地基

## 0 总览

| 区 | 规模 |
|---|---|
| data_assets/ | 119文件·378MB（QA语料6族+chunks+金标23+外部适配） |
| anchor_v2/v3/sc2 | 49文件·122MB（锚点三代+裁决金标+校准） |
| graph_store | 18文件·6.4MB（5619节点/23742边/978条目） |
| runs/ | **63个**：33有效+30中断（中断全部是blackboard_batch sc1冒烟） |
| mmqa | 5344文件·11MB（v0.2双形态） |
| easydataset/blackboard | 27文件·176MB（训练导出+缓存） |

## 1 三套数据生产哲学并存（一切资产的第一分类轴）

| 哲学 | 代表资产 | 特征 | 可信度 |
|---|---|---|---|
| **A.语料证据驱动** | inject_rules_v3、gold_standard系、real_doc_findings(324)、eval_entities | 从真实文档正则/结构提取，语料没有就0条 | 高（可回溯原文） |
| **B.LLM生成驱动** | srs_qa_by_scene(696)、eval_set的rewritten、srs_test_llm(177) | LLM编+改写+验证 | 中低（分布漂移） |
| **C.混合管线** | **srs_qa_trusted(1736)** | fact提取+规则注入+LLM改写，正例fact锚定真实文档 | 中高 |

**结论：任何评测必须声明用的是哪套哲学的标签。**

## 2 正例资产专表（consistent总数≈4800+，此前只用110条）

| 资产 | 正例数 | 性质 |
|---|---|---|
| **srs_qa_trusted/all_scenes** | **1080** | ★最大可信正例库：每条fact字段锚定真实ID+来源表 |
| srs_test_dataset | 1653 | 注入驱动（is_injected=False对偶） |
| injected_qa | 992 | 未注入原生配对 |
| **param_qa_extended** | **347** | 语料证据（正例率93.8%最高，真实表属性） |
| external_qa_pairs | 581 | ContractNLI等外部（与GJB隔离） |
| **gold_standard系** | **合计≈443** | sc1_desc_full 273(全real)+scene1 23+multi_scene 53+其他 |
| srs_qa_by_scene | 348 | LLM生成 |
| eval_set(srs_qa_v3) | 50 | 双LLM验证真实多模态一致 |
| mmqa等效正例 | 20 | 单位换算（非平凡防捷径，75%误报的方法学发现载体） |

## 3 评测金标分层（口径可信度）

| 金标 | 口径 | 可信度 | 消费方 |
|---|---|---|---|
| final_adjudication(664) + 四层裁决链 | LLM多轮银标 | 中低 | NLI实验、blackboard |
| θ校准(calibration 89对) | born-digital构造真值 | **高** | 论文数字、test_gold_assets |
| uml_qa_full(11711,清洗版) | 模板合成+图事实裁决 | 中 | uml_detection_eval(F1=0.994) |
| retrieval_evalset(300) | chunk级构造 | 中 | hybrid_recall |
| mmqa(1335+198) | 40项注入构造 | 中 | mmqa_eval系 |
| ~~15号文档F1=0.978~~ | **oracle自检循环论证** | **低** | 文档17自认，仅证明管线自洽 |
| strict40_eval F1=1.0 | 证据核验层 | 低（特征可完美区分） | 谨慎引用 |

## 4 冗余与过时清单（处置建议）

| 资产 | 问题 | 建议 |
|---|---|---|
| anchor_all/ | ≡anchor_sc2/anchors.json（md5相同纯副本） | **删除** |
| 锚点三代 | sc2(粗)→v2(主用)→v3(UML) | 保留三代但README声明主用v2 |
| mutated_dataset(1787) | 旧一代，8自创算子，被mmqa取代 | 归档legacy |
| uml_qa_v1_noisy.bak+旧adjudication | 被11711清洗版取代 | 归档 |
| eval_injected v1(216)/v2(201) | 被v3(198)取代 | 归档 |
| easydataset/manifest.json | 计数漂移(9457 vs 18119) | 重生成 |
| AGENTS.md的knowledge清单 | 列了6个不存在的文件 | 改文档 |

## 5 未完成资产（被遗忘的待办）

| 资产 | 状态 |
|---|---|
| **anchor_sc2/adjudication_tasks(86条)** | **人工裁决包label全空**——人工金标计划启动未完成 |
| **srs_qa_v3/human_annotation(100条)** | **双标注者任务全部空白**（answer_key已备好） |
| srs_qa_trusted/sc8 | 空文件（sc8数据在by_scene） |
| 160条uncertain人工仲裁 | 银标升级金标的命门，多次承诺未做 |

## 6 质量警示

1. eval_set双LLM验证：both_agree仅42/235——**近半数标签无共识**
2. multi_llm_annotations：三LLM kappa=0.29
3. 09-11后28个有效run无git sha（nogit）
4. mmqa_eval_suites同config三次run的llm通道8/30 vs 19/30不稳定
5. srs_qa_final注入负例答案模板化（同一悬挂E9答案316条）
6. easydataset导出重复3311条
7. llm_claim_extraction：79条LLM全FAILED的失败实验记录

## 7 核心消费链（血缘图）

```
16份.doc
  ├→ mineru_standard → chunks(5231) → pair_dataset(366对)
  │        └→ stage0(971ID/2016处) → id_graph → graph_store(978条目)
  └→ OLE/Visio XML → 锚点三代(373结构)
         ├→ θ校准(89对,VLM互校) ──→ 论文数字[test_gold_assets锁定]
         ├→ Tier1词法比对 → 1005分歧 → M7/M17双LLM → M22五票 → 664银标
         └→ anchors_v3 → uml_qa_full(11711) → 检测套件(F1=0.994)

pair_dataset(81对high锚定) → mmqa(1335变异+虚拟pair) → Suite-S声明对评测
chunks+实体 → eval_entities(1094) → inject_rules_v3(40项注入) → eval_injected_v3(198)
     └→ eval_set(235,LLM改写+双验证) → 15号结果(0.978,自检口径)
```
