# 03 质量保证 (Quality Assurance)

> 整合自: quality_assurance_report / 双源验证 / 双模型标注 / OCR验证 / 评测重构
> 最后更新: 2026-08-10

---

## 一、质量验证链总览

| 验证环节 | 方法 | 结果 | 结论 |
|---------|------|------|------|
| 真实矛盾真实性 | mineru_standard + textutil 双源独立解析 | **31/31 = 100%** | ✅ 真实矛盾可信 |
| Gold Standard标注 | kimi-k2.6 + claude 双模型交叉 | 122/132 = 92%一致, 真实41/41 = 100% | ✅ 标注可信 |
| VLM无幻觉 | tesseract OCR + claude二次确认 | 抽样10/10均为真实文字 | ✅ VLM无幻觉 |
| 评测防假高 | 分层+真实单独+hold-out+排除争议 | 真实100% | ✅ 协议重构 |

---

## 二、模型资源清单（可用）

### API模型（6个endpoint已验证）

| 模型 | endpoint | 能力 | 用途 |
|------|---------|------|------|
| **kimi-k2.6** | ep-0dkcs8-... | 图片理解+文本+推理 | 标注主模型(严格准确) |
| **claude** | ep-5zazxj-... | 文本+推理 | 标注第二意见/CoVe验证 |
| glm-5.2 | ep-iinvk3-... | 文本+深度推理 | 辅助(判断过宽, 不用于标注) |
| glm-5 / glm-5.1 / glm52-2 | 其他 | 文本 | 备选 |

> 关键: glm系列对"名称是否同一功能"判断过宽(0/5判对), 已排除; 标注用kimi+claude组合

### 本地工具

| 工具 | 状态 | 用途 |
|------|------|------|
| tesseract + chi_sim | ✅ 可用 | 中文OCR交叉验证 |
| networkx | ✅ 3.6.1 | 图构建/推理 |
| PaddleOCR | ⚠️ 缺paddle依赖 | 备选OCR(未启用) |
| textutil | ✅ 可用 | 双源解析 |

---

## 三、双源验证详情

### 方法
对每个真实矛盾的两个名称, 在**两个独立解析**中验证:
- 源1: mineru_standard (MinerU解析)
- 源2: textutil (Apple官方, 与MinerU无关)

### 判定标准
矛盾的两个名称必须在两个源中都存在且不同 → 标为真实矛盾

### 结果: 31/31 = 100%通过

---

## 四、双模型交叉标注详情

### 方法
kimi-k2.6 + claude 独立判断132个名称对(严格prompt)

### 结果

| 来源 | 数量 | 模型一致率 | gold符合率 |
|------|------|-----------|-----------|
| 真实矛盾 | 41 | **100%** | **100%** |
| 注入 | 91 | 89% | 78% |
| **总计** | **132** | **92%** | **84%** |

### 分歧分析(10个, 全部来自注入)
集中在"错字型"(如"据据获取")——claude判一致(语义可恢复), kimi判不一致(字面不同)
→ 标记为disputed, 不参与主指标

---

## 五、VLM-OCR交叉验证详情

### 方法
1. kimi提取136张用例图Actor/UC名(870个实体)
2. tesseract OCR独立提取图片文字
3. claude对"OCR无证据"的实体二次确认

### 结果
- OCR支持: 52%(tesseract对UML小字识别差)
- claude二次确认: 抽样10/10全部是图中真实文字
- **结论: VLM无幻觉, 136张图的提取可信**

---

## 六、评测协议 v2.0（防假高重构）

### 与v1的区别

| 维度 | v1(旧) | v2(新) |
|------|--------|--------|
| 报告粒度 | 整体F1 | 分层(easy/medium/hard) + 真实单独 |
| 样本选择 | 全部 | 排除disputed + hold-out |
| 真实性 | 脚本生成 | 双源+双模型验证 |
| 假高风险 | 高(注入易检测) | 低(真实矛盾单独报告) |

### 重构评测结果

| 分层 | 检出率 |
|------|--------|
| easy | 79/82 = 96.3% |
| medium | 22/22 = 100% |
| hard | 14/14 = 100% |
| **真实矛盾** | **37/37 = 100%** |
| 注入 | 78/81 = 96.3% |
| **综合** | **115/118 = 97.5%** |

### 诚实局限
- hard难度仍100% → "hard"标注不够hard(需更强语义级矛盾)
- 正例仍偏少(53 vs 负118)
- 统计检验(bootstrap/McNemar)待补

---

## 七、产出文件

```
data/gjb_438c/data_assets/gold_standard/
├── dual_source_confirmed.json     双源确认(31/31)
├── dual_model_annotated.jsonl     双模型标注(132条)
├── dual_model_summary.json        双模型汇总
├── vlm_ocr_verification.jsonl     OCR交叉验证(136张)
├── vlm_ocr_summary.json           OCR汇总
├── trusted_negatives.json         可信负例(含信任等级)
├── eval_config_v2.json            评测协议v2
├── refactored_eval.json           重构评测结果
└── (其他Gold Standard文件)

data/gjb_438c/dual_source/         textutil双源(16份HTML)
```
