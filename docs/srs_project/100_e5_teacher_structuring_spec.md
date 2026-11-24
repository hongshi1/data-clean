# E5实施规格：教师解释结构一致化+D3蒸馏重训（Phase 2）

> 99号方案Phase 2的执行规格。基于对数据链的实证检查（2026-11-24），
> 供下一轮agent直接执行。

## 数据现状（已验证）

| 资产 | 规模 | 结构化解释 |
|------|------|-----------|
| d3_teacher_labels_v1.jsonl | 1886条 | 391条带issues |
| d3_narrative_labels_v1.jsonl | 1638条 | 351条带issues（经d3_narrative_augment.py span校验） |
| d3_train_v3f.jsonl（聚焦集） | 1336条 | 219 refute带issues；分布：NIE 843 / refute 219 / support 274 |

**issues schema（与train_d3_student._target_message对齐）**：
`{quote, span, rule_id, evidence_ref, explanation, span_verified}`

**结论**：字段模板已一致（96号E5的第一要求已满足）——
"教师解释结构一致化"的剩余缺口在**质量闸门**而非**格式**。

## 与96号E5协议的差距分析

| 96号要求 | 现状 | 缺口 |
|---------|------|------|
| 统一字段模板 | ✅ 五字段schema齐 | 无 |
| 忠实reward（span真实性） | △ span_verified只查字面在场 | 未查"span是否支撑判定"（citation有效性） |
| 真实reward（判定正确） | ✅ orig_label对照 | 无 |
| 有用reward（解释可读） | ✗ 无检查 | 351条explanation无质量分级 |
| EGT最小变更对 | ✗ EGT合成已有 | 解释侧无minimal pair |
| FLamE质量闸门 | ✗ 无 | 蒸馏解释可能提准确率但不构成判定理由 |

## 执行步骤

### Step 1：解释质量闸门（教师API走缓存，~351+219次调用）

新建 tools/e5_explanation_gate.py：
1. 对带issues的条目（351+219去重后~570条），教师三reward评分：
   - **faithful**：quote是否逐字存在于answer；span区间是否与quote一致
   - **truthful**：explanation是否与verdict/issues自洽（不引入证据外信息）
   - **useful**：explanation是否指明差异所在（含数值/枚举/绑定级具体性）
2. 评分1-3档写入标签（不删除数据，只分级——低分条目降采样而非剔除）
3. 输出：d3_train_v3f_gated.jsonl + 质量分布报告

### Step 2：最小变更对增广（表驱动，零API）

对refute条目构造修复版answer（把violation修正→应翻转为support）：
- 数值类：改数值到证据区间内
- 枚举类：替换为证据枚举成员
- 绑定类：修正ID绑定关系
产出~200对（refute, support）对照——训练解释的"差异指认"能力。
复用qa_mutation_ops.py的算子（反向使用：修复而非破坏）。

### Step 3：重训（锁定命令升级版）

在既定命令基础上加gated数据+最小变更对：
```
python tools/train_d3_student.py --epochs 1 --max-len 1792 \
  --evidence-budget 900 --batch 1 --grad-accum 16 \
  --labels data/gjb_438c/distillation/d3_train_v3f_gated.jsonl \
  --out-dir models/llm/d3_student_v3
```
（若train_d3_student.py不支持新数据文件的额外字段，先加加载逻辑——
保持向后兼容，默认LABELS不变。）

### Step 4：验收（基线已由Agent A的E1/E2落地，2026-11-24）

| 指标 | 基线（已验证） | 目标 |
|------|---------------|------|
| 消融翻转率b（关键证据移除判定翻转） | **13/16 = 0.8125**（E2，独立复核） | ≥0.8125不回退 |
| 定位稳定性c（无关扰动span不变） | **11/17 = 0.647**（E2最弱点） | ≥0.80（重训主攻） |
| 定位跟随d（关键证据替换后span迁移） | **16/16 = 1.0**（E2） | 保持1.0 |
| citation P/R（专家路径macro） | **P 0.8021 / R 0.8792**（E1初步） | ≥基线+10pp（学生路径） |
| D3学生refute检出 | **4/17**（NIE偏置，集成16/17全靠专家） | 显著提升（解NIE偏置） |
| verdict acc | 0.8043 | ≥0.8043 |
| 结构失败率（JSON不可解析） | d3_student_eval_v1.json | →0（配合X1约束解码） |

**E1初步发现的训练数据启示**（回填自Agent A中期报告）：
1. **D3学生NIE偏置的根源 = v3f类别失衡**（NIE 843/refute 219/support
   274 = 63%/16%/21%）——学生学会过度预测NIE。Step 2最小变更对
   增广的同时，考虑对NIE类降采样或在Step 1质量闸门的downweight
   权重上给NIE打折；
2. **学生citation严重欠目标**（2/4 vs gold 2/9）——训练目标里的
   issues[]引用要过Step 1的faithful闸门（evidence_ref有效+索引
   在范围内），不合格的引用降权，逼学生学习有效引用；
3. **E2发现的citation欠覆盖**（enum通道判定依赖未引用的上下文块，
   VIO-06/07 remove_irrelevant翻转）——这是专家侧问题不是学生侧，
   记录为L1通道的后续修复项（不进本轮重训范围）。

## 执行顺序约束

1. **Step 1/2可立即做**（零冲突：只新增tools脚本+新数据文件）
2. **Step 3等Step 1/2完成**（一次训练吃全部数据）
3. **Step 4的基线数字等Agent A（E1/E2）交付**——没有尺子的重训无法验收
4. 与Agent B（P1桥接）无文件冲突；D3输入格式不动

## 风险与对策

- **FLamE风险**（96号警示）：蒸馏解释提准确率但不构成判定理由
  → 对策：Step 1的truthful检查+Step 4的消融翻转率（解释必须
  因果有效：移除被引证据判定应翻转）
- **类别失衡**：NIE 843 / refute 219 / support 274——最小变更对
  增广同时缓解refute不足
- **过夜训练显存**：Qwen3-1.7B LoRA batch=1+grad-accum=16已在
  既有命令验证过
