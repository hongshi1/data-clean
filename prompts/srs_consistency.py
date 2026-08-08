#!/usr/bin/env python3
"""
SRS一致性检测Prompt模板
========================
移植自 DataFlow-KG 的 prompts/consistency.py
改动: 领域词从"知识图谱三元组"改为"SRS需求条目"

三个核心prompt:
  1. CONSISTENCY_PROMPT — 两个条目是否一致 (移植KGRelationTripleConsistencyPrompt)
  2. EVIDENCE_CHECK_PROMPT — 检测结论是否有证据支撑 (移植KGHallucinationEvaluationPrompt)  
  3. REPORT_SYNTHESIS_PROMPT — 生成检测报告 (移植QASynthesizer的prompt模式)
"""

# ── Prompt 1: 一致性判断 (移植自DataFlow-KG KGRelationTripleConsistencyPrompt) ──

CONSISTENCY_PROMPT = """你是一个GJB 438C SRS文档一致性检测专家。

判断以下两个条目是否一致。

条目A (来自章节 {section_a}):
{text_a}

条目B (来自章节 {section_b}):
{text_b}

判断标准:
- CONSISTENT: 两个条目描述的同一参数/功能/接口的值和含义一致
- INCONSISTENT: 两个条目存在矛盾(不同值/不同含义/逻辑冲突)
- UNRELATED: 两个条目不描述同一事物

注意区分合理差异和真实矛盾:
- 合理差异: 不同设备形态的配置差异(如桌面版1.5GHz/平板版1.2GHz)、不同章节描述不同方面
- 真实矛盾: 同一参数同一位置的不同值(如达梦V7.2 vs V7.6)、编辑错误(copy-paste错位)、逻辑不可能(A≤5且A≥10)

输出JSON:
{{"verdict": "CONSISTENT"|"INCONSISTENT"|"UNRELATED", "reason": "简要说明", "evidence": "支撑判断的关键文字"}}"""


# ── Prompt 2: 证据验证 (移植自DataFlow-KG KGHallucinationEvaluationPrompt) ──

EVIDENCE_CHECK_PROMPT = """判断以下检测结论是否有文档证据支撑。

检测结论: {claim}
文档证据: {evidence}

输出NLI三分类:
- Supported: 证据直接支撑结论
- Contradicted: 证据与结论矛盾
- Not Mentioned: 证据中未提及结论相关内容

注意: 允许同义词和代词替换，但核心事实必须匹配。

输出JSON:
{{"nli": "Supported"|"Contradicted"|"Not Mentioned", "reason": "简要说明"}}"""


# ── Prompt 3: 检测报告合成 (参考AgentFlow QASynthesizer的prompt模式) ──

REPORT_SYNTHESIS_PROMPT = """你是一个SRS一致性检测报告生成器。

基于以下检测结果和证据，生成一份结构化的检测报告。

检测结果:
{detection_results}

证据链:
{evidence_chain}

生成要求:
1. 报告必须包含以下字段:
   - inconsistency_type: 不一致性类型(如parameter_value_conflict/id_split/phantom_requirement/logic_unsatisfiable等)
   - severity: HIGH/MEDIUM/LOW
   - description: 问题的自然语言描述
   - evidence_chain: 证据链(每条含section_id和verbatim quote)
   - reasoning_steps: 推理步骤(至少3步)
   - conclusion: CONSISTENT/INCONSISTENT/UNCERTAIN
   - verdict: 真实矛盾/合理差异/无法确定

2. 证据链每条必须附section_id和原文引用(verbatim quote)
3. 推理步骤至少3步，每步说明从证据到结论的推理过程
4. 如果证据不足以确定，输出UNCERTAIN而非编造结论

输出JSON:
{{
  "inconsistency_type": "...",
  "severity": "...",
  "description": "...",
  "evidence_chain": [
    {{"hop": 1, "section_id": "...", "evidence": "...", "verbatim": "原文引用"}},
    {{"hop": 2, "section_id": "...", "evidence": "...", "verbatim": "原文引用"}},
    {{"hop": 3, "section_id": "...", "evidence": "...", "verbatim": "原文引用"}}
  ],
  "reasoning_steps": ["步骤1", "步骤2", "步骤3"],
  "conclusion": "CONSISTENT"|"INCONSISTENT"|"UNCERTAIN",
  "verdict": "真实矛盾"|"合理差异"|"无法确定"
}}"""


# ── Prompt 4: 实体关联 (用于上下文关联阶段) ──

ENTITY_ASSOCIATION_PROMPT = """你是一个SRS文档上下文关联专家。

以下是从SRS文档中提取的实体列表。请判断哪些实体描述的是"同一事物"。

实体列表:
{entities}

判断标准:
- 同一需求功能: 功能名称相同或语义等价(如"故障探测预警"="故障预警修复")
- 同一参数: 参数名相同或同义(如"主频"="处理器频率")
- 同一接口: 接口标识符归一化后相同(如SJCSKZ=SJCS,因为都是"数据传输控制"的缩写)

注意:
- 需求ID可能不一致(SJCS/SJCSKZ/SJSF三个ID可能指同一需求)
- 章节号可能系统性偏移(第4章比第3章整体+1)
- 不同设备形态(桌面/平板/手持)的配置差异不是"同一事物"

输出JSON数组，每组是描述同一事物的实体ID列表:
[
  {{"entity_ids": ["id1", "id2", "id3"], "canonical_name": "统一名称", "reason": "判断依据"}},
  ...
]"""


# ── Prompt 5: 约束提取 (参考DataFlow KnowledgeCleanerPrompt的verbatim保真规则) ──

CONSTRAINT_EXTRACTION_PROMPT = """你是一个GJB 438C SRS文档约束提取专家。

从以下SRS章节文本中提取所有数值约束。

约束类型:
1. numerical: 数值约束 (参数≤值) → {{"type":"numerical","param":"参数名","operator":"≤","value":数值,"unit":"单位","original":"原文"}}
2. tolerance: 对称容差 (±值) → {{"type":"tolerance","param":"参数名","value":数值,"unit":"单位","original":"原文"}}
3. cumulative: 累积约束 → {{"type":"cumulative","param":"参数名","operator":"≤","value":数值,"unit":"单位","iterations":次数,"original":"原文"}}

关键规则 (参考DataFlow KnowledgeCleanerPrompt的保真规则):
- original字段必须是原文的verbatim quote，禁止修改任何文字
- value必须是数值类型(float)，不能是字符串
- 如果无法确定参数名，从上下文推断
- 宁缺毋滥: 只提取有明确数值的约束

章节 {section_number} {section_title}:
{section_text}

输出JSON数组。如果没有约束，返回空数组 []。"""
