# 数据集存放说明

本目录用于存放实验数据集。**实际数据文件不纳入git版本管理**（见`.gitignore`），请按以下结构手动下载和放置。

## 目录结构

```
data/
├── README.md                          # 本文件
├── nlmcxr/                            # NLMCXR (IU X-Ray) 医疗胸片+报告
│   ├── images/                        # 胸片图像
│   ├── data/                          # parquet数据文件
│   └── output_dj/                     # Data-Juicer输出
├── medical_data/                      # MedTVT 医疗多模态数据
│   └── medtvt/
├── h4r_welding/                       # H4R 焊接数据集（工业时序+图像+标签）
├── nasa_cmapss/                       # NASA C-MAPSS 涡扇发动机退化数据
├── intel_welding/                     # Intel 焊接多模态数据集
├── material_data/                     # 材料加工数据
└── finmultitime/                      # 金融多模态时序数据
```

## 数据集获取方式

### NLMCXR (IU X-Ray) — 医疗胸片+放射报告
- 来源: 印第安纳大学
- 下载: https://openi.nlm.nih.gov/faq
- 用途: 图像↔报告不一致性检测（医疗验证场景）

### NASA C-MAPSS FD001-FD004 — 涡扇发动机退化数据
- 来源: NASA PCOE (Saxena et al. 2008)
- 下载: `https://github.com/edwardzjl/CMAPSSData` (master分支)
- 用途: 时序异常检测+退化趋势分析（航发场景验证）
- 格式: 26列空格分隔txt (发动机编号+循环数+3操作设置+21传感器)

### H4R Welding Dataset — 工业焊接数据
- 来源: Hackathon for Robotic Welding
- 用途: 时序↔图像↔标签三模态冲突检测（工业场景验证）

### MedTVT — 医疗多模态基准
- 来源: MIMIC-IV衍生
- 用途: 血检↔诊断标签冲突检测

## 注意事项

1. 数据文件**不提交到git**，通过`.gitignore`排除
2. 新增数据集时在本文件中补充说明
3. 敏感数据（含患者隐私/军工涉密）须脱敏后存放
