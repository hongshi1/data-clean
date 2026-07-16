# DKG-CMR框架 → 军工场景落地映射

> 基于前序综述 `跨模态一致性验证与推理_综述重组版.md` 第7节
> 日期：2026-06-29

---

## 前序理论 → 当前工具/方法的映射

前序综述提出DKG-CMR统一框架，包含6个部件。以下将每个部件映射到当前研究已发现的具体工具和方法：

| DKG-CMR部件 | 理论定义 | 军工场景落地 | 已有工具/方法 | 状态 |
|---|---|---|---|---|
| **1. Cross-modal grounding** | 文本mention/图像region/表格cell/schema field/time span接到同一实体 | 武器型号↔图片区域↔规格字段↔时序事件对齐 | CLIP/SARCLIP（图文对齐）+ Synaesthesia（时序对齐） | ✅ 工具已有 |
| **2. Structured evidence model** | claim/evidence/support edge/conflict edge | 武器claim（"这是F-16"）+ 证据（图片/规格/时序）+ 支持/冲突关系 | Data-Juicer JSONL格式 + 自定义schema | 🔧 需设计 |
| **3. Domain-knowledge substrate** | ontology/rules/schema/causal/temporal constraints | 军工武器本体（GJB 4292A标准）+ NATO命名体系 + 型号-规格-性能规则 | GJB标准 + GunsAndWeapons表格 + 自建本体 | 🔧 需构建 |
| **4. Constraint propagation** | 一个模态的约束传播到另一个模态验证 | 表格规格约束→图片验证（口径匹配？型号匹配？）+ 时序约束→事件验证 | 自定义Data-Juicer算子 | 🔧 需开发 |
| **5. Verification-oriented reasoning** | 演绎验证+归纳规则发现+溯因解释 | FAMDR方法迁移（噪声感知对齐→检索增强→精细定位→不确定性量化） | FAMDR（AAAI 2026）+ LLM算子 | 🔧 需实现 |
| **6. Explanation and attribution** | verdict+supporting/refuting evidence+violated rule+confidence+repair | 不一致报告：哪个模态错+违反哪条规则+置信度+修复建议 | HTML治理报告（已出初版） | ✅ 初版已有 |

## 框架结构映射

```
DKG-CMR理论:  UKS + CMRB + CRE + Closed-loop verification

军工落地:
  UKS (领域知识基底) = GJB军工本体 + 武器规格表 + NATO命名体系
  CMRB (跨模态推理桥) = CLIP/SARCLIP图文对齐 + 时序事件对齐
  CRE (一致性推理引擎) = FAMDR迁移 + 自定义Data-Juicer算子 + LLM辅助
  Closed-loop = 检测→报告→人工审核→修复→复检
```

## 当前研究在DKG-CMR中的定位

前序综述识别的5个gap，当前研究对应填补：

| Gap | 综述描述 | 当前研究填补 |
|---|---|---|
| Benchmark gap | 缺少领域特定的不一致benchmark | 构建军工三模态不一致数据集 |
| Method gap | 方法碎片化，缺统一链条 | Data-Juicer pipeline + FAMDR迁移 |
| Knowledge gap | 缺领域知识接入 | GJB军工本体 + 武器规格知识库 |
| Explanation gap | 缺可解释验证 | HTML治理报告+不一致归因 |
| Framework gap | 缺统一推理架构 | DKG-CMR军工版（UKS+CMRB+CRE+Closed-loop） |

## 研究贡献点（基于理论框架明确化）

1. **首个军工领域DKG-CMR实例化**：将通用理论框架落地到军工场景
2. **Data-Juicer扩展为验证工具**：从"过滤"改造为"检测报告"
3. **军工知识基底构建**：GJB标准 + 武器规格 → 可计算本体
4. **跨模态约束传播实现**：表格规格→图片验证→时序事件的约束链
5. **军工不一致benchmark**：填补Benchmark gap

## 对上下文规划的启示

前序综述的存在改变了上下文规划：
1. **不需要重新做文献综述**——前序综述已完成（7层分类+5gap+6方向）
2. **不需要重新定义问题**——DKG-CMR框架已定义
3. **研究重心是落地实现**——理论→工具→实验
4. **会话2应从读综述开始**——不是从搜索开始
5. **方法实现参考DKG-CMR 6部件**——不是从零设计
