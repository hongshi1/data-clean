# GJB SRS 一致性校验项目

基于16份真实GJB 438C格式SRS文档，研究**上下文关联(方向A)**与**不一致性校验(方向B)**。

## 快速开始

```bash
# 数据准备(已有解析结果, 无需重跑)
# 数据在 data/gjb_438c/

# sc1名称一致性检测(7种方法)
python tools/sc1_detector.py --all

# ID-Graph(图构建+符号层+图推理+语义图)
python tools/id_graph.py

# sc1 CoVe证据验证(需API)
python tools/cove_verifier.py --task name --sample 5
```

## 目录结构

```
data/
├── 软件需归样例数据集/        16份原始.doc(只读)
└── gjb_438c/
    ├── mineru_standard/      MinerU解析(md+content_list+images)
    ├── dual_source/          textutil双源解析(16份HTML)
    ├── pair_dataset/         8场景配对(图片+表格CSV+正文TXT)
    └── data_assets/          结构化资产+Gold Standard+图方法结果

docs/srs_project/
├── project_guide.md          黄金文档(总纲)
├── 01_data_assets.md         数据资产
├── 02_method_design.md       方法设计(ID-Graph+7种图方法)
├── 03_quality_assurance.md   质量保证(双源+双模型)
├── 04_status_report.md       进度+Todo
├── audit/                    审计记录
└── literature_survey/        文献调研(7篇)

tools/
├── sc1_detector.py           ★ sc1名称一致性检测(7方法统一接口)
├── id_graph.py               ★ ID锚定图+语义图+视觉互校
├── cove_verifier.py          ★ sc1 CoVe证据验证
├── build_data_assets.py      数据资产构建
├── build_semantic_modality.py 8场景模态构建
├── extract_hd_images.py      高清图片提取
├── srs_mineru_parse.py       MinerU解析
└── srs_mineru_pipeline.py    解析pipeline
```

## 核心结果

| 方法 | F1 | 说明 |
|------|-----|------|
| 双空间(拓扑+文本) | 0.897 | sc1名称一致性最优 |
| 图注意力(学习边权重) | 0.897 | 同上 |
| 属性一致性图 | 1.000 | sc3接口属性 |
| 异常流dangling | 1.000(P) | sc2 |

## 关键资产

- **Born-Digital金标准**: 374图×11308 Shape(Visio源文件直读, 100%准确)
- **Gold Standard**: sc1(242条)+sc3(30条)+sc2(48条), 双源+双模型验证
- **质量保证**: 真实矛盾31/31双源确认, 双模型标注92%一致, VLM无幻觉10/10

## 模型资源

- kimi-k2.6 (ep-0dkcs8-...): 标注/CoVe验证/图片理解
- claude (ep-5zazxj-...): 第二意见/隔离验证
- 本地: tesseract+chi_sim(OCR), networkx/scipy/sklearn(图方法)
