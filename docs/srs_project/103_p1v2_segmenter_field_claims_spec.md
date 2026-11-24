# P1-v2实施规格：切分器重训吃字段claim（两层粒度契约的正面攻击）

> B的P1桥接实验（M123）的后续。B的结论：识别F1≥0.60（原子粒度）
> 与下游≥0.8047（typed+句级claim结构）在本语料互斥，修复在训练
> 目标不在claim集构造。本规格把该结论转化为可执行实验。

## B的发现回顾（两层粒度契约）

1. **字段层缺口**：教师原子claim=叙事粒度，typed字段（ID/数值/枚举
   的原文span）在切分器O区——5个含ID实例的identifier span覆盖率
   0.0。识别F1 0.70的胜利区域与typed字段区域**不相交**。
2. **命题层缺口**：NLI能entail整句、不能entail原子（S1QA-006实证
   ——A_regex的4条句级claim全部entail→support；原子claim全部
   semantic_unresolved→NIE一票否决）。

## P1-v2的核心设计：蒸馏A_regex的完整分解行为

**训练标签构造**（编程式，零教师API）：
对训练语料的每个(question, answer)：
1. 运行A_regex的完整分解（decompose_answer/decompose_claims：
   句级structural claim + typed字段claim，主语归位到answer坐标系）
   → 这套claim天然满足两层契约（字段覆盖+命题完整）
2. 目标标签 = A_regex的claim集（带kind标注：numeric/enum/
   identifier/quoted/sentence）
3. **切分器（128M）重训**：学习从answer直接产出这套claim集

**为什么这有价值**（不是循环论证）：
- GJB域内：蒸馏模型≈regex表现（下游≥0.8047可期，因为claim行为
  等价）
- **跨域**：GJB文法regex是域绑定的（crossdoc 0.51瓶颈、identifier
  跨域误判的根源）——学习版不带GJB文法假设，换域零配置
- 这正是98号"分层迁移"论文叙事的实现：**把regex的语义判定能力
  蒸馏进模型，正则退役，跨域变现**

## 实施步骤

### Step 1：标签构造（tools/build_segmenter_field_labels.py）

- 输入：segmenter现有训练语料（tools/claim_segmenter.py的训练集
  路径——查distill_segmenter_labels.py的输入）
- 对每个answer跑decompose_claims（typed正则版）→ claim集+kind
- 输出：data/gjb_438c/distillation/segmenter_field_labels_v1.jsonl
  （格式与现有segmenter训练标签同构——char-level标签或span列表，
  保持tools/train_claim_segmenter.py可消费）
- **混合策略**：教师叙事原子标签**保留**用于泛化（域外句式），
  A_regex字段claim标签作为**新增分层**——两套标签按实例混合
  （有typed字段的实例用A_regex标签，纯叙事实例保留教师原子标签），
  避免全量替换丢失叙事泛化

### Step 2：重训切分器（GPU，128M小模型快）

复用tools/train_claim_segmenter.py（或其参数化版本），训练集=
混合标签。输出models/segmenter/claim_segmenter_v3。

### Step 3：三臂评测（复用B的评测资产）

tools/eval_claim_typed_bridge.py加segmenter_v3臂（桥接版）：
- A_regex（基线0.8047）
- C_bridge_v2（新切分器+桥接）——**验收：macro-F1≥0.8047**
- 识别F1对新标签口径≥0.90（蒸馏目标是确定性的，应近满分）

### Step 4：跨域评测（真正的价值验证）

crossdoc06评测集上：A_regex vs C_bridge_v2——学习版的跨域
表现（B的发现说明identifier跨域误判的根源在regex域绑定）。
验收：跨域macro-F1显著优于A_regex（0.51→更高）。

## 验收汇总

| 指标 | 目标 |
|------|------|
| test46 macro-F1（桥接v2） | ≥0.8047 |
| 识别F1（新口径） | ≥0.90 |
| crossdoc06 | 显著>regex版 |
| 现有测试 | 全绿（默认行为不动） |

## 执行时机

- GPU：等Agent E（X1）完成后启动（避免GPU争用；128M训练本身快）
- Step 1零GPU可先行（纯编程式标签构造）
- 与D的E5数据、C的Eiter无文件冲突（新tools+新数据+新模型目录）

## 风险

1. **蒸馏保真度**：128M模型能否逐位学会typed抽取——识别F1<0.90
   则字段覆盖有洞，下游达不到（如实报告分臂归因）
2. **混合标签的一致性**：两套口径的claim边界冲突（教师原子 vs
   A_regex句级）——按实例分层避免同实例混两套
3. **跨域提升不显著**：说明跨域瓶颈不在分解层在别处（97号调研
   的"crossdoc 0.51瓶颈在文法层"判断需要修正）——负面结果也
   如实报告
