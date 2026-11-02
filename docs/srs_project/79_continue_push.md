# 79 继续推进：108实例后端复现 / F3合同v2 / 表格行原子化

日期：2026-10-29 | 78号后续 | 76测试全过，ruff零报错

---

## 一、91条QA全量seed导入（P1完成）

```text
改造: tools/seed_violations_to_db.py → 108实例导入器
     (17违例 + 91冻结QA + silver标签入attrs, 幂等)
结果: doc04 = 108条qa_pairs(全部frozen结构化证据)
```

## 二、后端完整复现离线评测（集成正确性终验）

```text
POST /api/verify/04 (服务层verify_doc) 对108实例:
  accuracy = 0.7685   ← 与73号离线评测逐位一致
  混淆矩阵逐格一致(60 NIE|NIE / 14 refute|NIE / 21 refute|refute / ...)
→ 后端服务 = 离线评测管线的可信执行体
```

## 三、F3形态合同v1（P2，70号设计的保守实现）

**实现原则：标注优先于删除**（73号教训——精选池上删除有风险）

```text
合同注册表: config/evidence_contracts_v1.json(40项, 冻结导出)
  来源: deq_pipeline.DETECTION_EVIDENCE_REGISTRY
  schema: table_types + content_markers + statement_fields

形态匹配(纯函数):
  match_shape(text, contract) → {matched, field_hits, marker_hits}
  annotate_contracts(question, evidence, contracts)
    → 每块证据打shape_tags(不删除任何证据)

测量工具: tools/eval_evidence_contracts.py(108实例)
```

## 四、路由修复（TERM-07关键词缺口）

```text
qa_router: TERM-07增加「标识符/唯一标识」关键词
  (原只有接口标识——"X的标识符是什么"类问句路由为空)
gold覆盖: 34.3% → 57.1% (12/35→20/35)
回归: 108对账数字不变(0.7685逐位一致), 72测试全过
```

## 五、合同质量基线（诚实测量）

```text
块级形态命中率: 26.4%(175/664) — 信号有选择性
gold证据被合同覆盖: 57.1% — 覆盖不足, LOGIC类最弱
按项命中率: TERM-07 86% / GJB-05 80% / TERM-04 73%(标识类强)
           LOGIC-03 29%(顺序类弱——需更强markers)
→ F3 v2改进方向: LOGIC类合同markers扩充(方向明确)
```

## 六、产物

| 资产 | 位置 |
|---|---|
| 合同注册表 | `config/evidence_contracts_v1.json`(40项) |
| 形态匹配 | `algorithms/consistency/evidence_purifier.py`(match_shape/annotate_contracts) |
| 合同导出 | `tools/build_evidence_contracts.py` |
| 命中率测量 | `tools/eval_evidence_contracts.py` |
| 108导入器 | `tools/seed_violations_to_db.py`(升级) |
| 测量数据 | `data/gjb_438c/localization_gold/contract_match_v1.json` |

## 七、F3 v2与表格原子化（追加，2026-10-29晚）

### F3 v2（诊断反转 + 定向修复）

```text
诊断: 块级LOGIC-03命中率29%并非合同缺陷——未命中块是背景/干扰块
     (节标题/指针/能力表/概述段), 本就不该匹配异常流合同
真缺口: "合格性方法"类问句未路由到GJB-01(VIO-17唯一漏检)
修复: qa_router的GJB-01增加「合格性」关键词(合同本就有该标记)
结果: gold按项覆盖 6/6类全100% (35/35), 108对账数字不变(0.7685)
结论: 块级低命中率=正确的选择性(精度特征), 按项gold覆盖才是正确指标
```

### 表格行原子化（双通道）

```text
新增: atomizer.atomize_tables(双通道)
  通道1 表头列: 参数名列("内存容量")直接取单元格值
  通道2 格内段: "CPU主频：不低于2.5GHz"式标签-值段(硬件表实况)
  scope=行头结构化绑定(设备名), 非文本启发
全量: 1207表→281原子→33组→1169对
  强候选2对 = doc10真冲突(主频2.2/2.5 + 分辨率1280/1600, 65号案例)
对账: 表源327冲突键 ⊆ claims源960键(无新发现)
结论: 覆盖不增, 但原子质量升级——作用域由行结构绑定
     (claims通道的scope污染问题在表通道天然不存在)
测试: atomize_cell/双通道/行作用域绑定 5个新测试(共15)
```

## 八、产物（追加）

| 资产 | 位置 |
|---|---|
| 表格原子化 | `algorithms/context_linking/atomizer.py`(atomize_tables/atomize_cell) |
| 表源构建 | `tools/build_table_atoms.py` |
| 表源数据 | `atom_candidates_v1/table_{atoms,candidates}.jsonl` |
| 路由修复 | `qa_router.py` GJB-01+合格性 |

## 九、剩余

```text
P0  人工: 91 QA双轮标注→κ→export(唯一人工环节, 工具就绪)
P2  LLM-as-judge / 通道融合(claims+表源原子合并口径)
```
