# 数据集架构重新设计 v2.0

> 日期: 2026-08-09
> 触发: 用户指出QA对是端到端评测, 数据集应分层分离上下文关联与不一致性校验

## 技术谱系

```
方向A(上下文关联)                    方向B(不一致性校验)
输入: SRS文档                        输入: 聚合条目(含多模态上下文)
输出: 条目列表                       输出: 不一致性检测结果
        ↓                                  ↓
    评测数据1                          评测数据2
    (上下文关联Gold Standard)          (不一致性Gold Standard)
              ↘                    ↙
                评测数据3: QA对(端到端)
```

## 三层数据集设计

### 数据集1: 上下文关联Gold Standard

**目的**: 评测方向A——模型能否把分散的多模态内容正确聚合为一个条目

**数据形式**:
```json
{
  "entity_id": "PZXQ-GN-FWKFZC-CJFWGC",
  "entity_name": "创建服务工程",
  "doc": "03服务集成框架软件需求规格说明-终稿",
  "gold_context": {
    "text": {"section": "3.2.1.1", "snippet": "创建服务工程的功能..."},
    "image": {"caption": "图5 服务开发用例图", "path": "...", "type": "usecase_diagram"},
    "capability_table_row": {"table": "表3 服务开发能力标识", "row_data": ["1", "创建服务工程", "PZXQ-GN-FWKFZC-CJFWGC", "需求描述..."]},
    "qualification_row": {"table": "合格性规定", "row_data": ["创建服务工程", "3.2.1.1", "A"]},
    "traceability_row": {"table": "追溯表", "row_data": ["创建服务工程/PZXQ-GN-...", "3.2.1.1", "4.1.1a)"]}
  }
}
```

**评测协议**:
- 输入: entity_id + doc
- 模型任务: 从文档中召回该实体的所有相关上下文(正文/图片/表格行)
- 评测: 对比gold_context, 按模态分别计算召回率/精确率/F1
- 规模: 从16份文档的1029个需求ID中抽样200-300个

**数据来源**: stage0_assets.json的id_registry已有7位置×1029个ID的映射

---

### 数据集2: 不一致性Gold Standard

**目的**: 评测方向B——给定聚合条目, 模型能否检测出其中的不一致性

**数据形式**:
```json
{
  "entity_id": "ZZSJHQZHFW-JK-WB-ZZS",
  "entity_name": "与数据统算交互接口",
  "doc": "01数据获取转换分系统需求规格说明-终稿",
  "aggregated_context": {
    "text": {"section": "3.3.1", "name": "与数据统算交互接口"},
    "interface_table": {"section": "3.4", "name": "与数据统算交互接口", "type": "API接口"},
    "traceability_table": {"section": "6.x", "name": "与数据通算交互接口"},
    "qualification_table": {"section": "4.x", "name": "与数据统算交互接口"}
  },
  "inconsistencies": [
    {
      "type": "name_inconsistency",
      "severity": "high",
      "location_a": {"field": "text", "section": "3.3.1", "value": "与数据统算交互接口"},
      "location_b": {"field": "traceability_table", "section": "6.x", "value": "与数据通算交互接口"},
      "description": "追溯表中'通算'与正文'统算'不一致, 疑似笔误"
    }
  ]
}
```

**评测协议**:
- 输入: aggregated_context(已聚合的多模态上下文)
- 模型任务: 检测其中存在的不一致性
- 评测: 对比gold inconsistencies, 按类型计算P/R/F1
- 正例(无不一致): 从文档中抽样一致条目作为负样本

**数据来源**: 已提取的167个真实矛盾 + 一致条目作为正例

---

### 数据集3: QA对(端到端评测)

**目的**: 评测完整流水线(上下文关联→不一致性校验)的端到端效果

**当前状态**: 501条基于真实矛盾的QA(已重建)

**评测协议**:
- 输入: {instruction, output, doc_ref}
- 模型任务: 上下文关联(召回) → 一致性校验(判断output是否与文档一致)
- 评测: P/R/F1

---

## 与现有数据资产的映射

| 数据集 | 数据来源 | 当前状态 | 需要做 |
|--------|---------|---------|--------|
| 1.上下文关联Gold | stage0_assets.id_registry(1029个ID×7位置) | 数据已有, 未组织为评测格式 | 从id_registry构建gold_context |
| 2.不一致性Gold | 167个真实矛盾(已提取) + 一致条目 | 矛盾已提取, 未组织为聚合条目格式 | 构建aggregated_context + inconsistencies |
| 3.QA对(端到端) | 501条真实矛盾QA(已有) | ✅ 已完成 | 可用 |

## 质量保证原则

1. **真实矛盾优先**: 所有负例来自文档本身的不一致性, 非人工注入
2. **人工验证**: 每条Gold Standard经人工确认(Korn 2026警示)
3. **可追溯**: 每条数据可追溯到文档原文位置
4. **分离评测**: 方向A和方向B可独立评测, 也可端到端
