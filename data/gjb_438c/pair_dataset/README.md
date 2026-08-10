# GJB SRS 配对数据集 (Pair Dataset)

> 生成日期: 2026-08-10
> 结构: 每个实例 = 图片 + 表格CSV + 正文TXT + 元数据JSON

## 目录结构

```
data/gjb_438c/pair_dataset/
├── sc1_usecase_capability/     137实例  用例图+capability表+正文
├── sc2_flowchart_usecase/       82实例  流程图+usecase表+正文
├── sc3_interface_interface/     32实例  接口图+interface表+正文
├── sc4_flowchart_capability/    26实例  流程图+capability表+正文
├── sc5_function_capability/     11实例  功能图+capability表+正文
├── sc6_framework_other/          8实例  功能框架图+其他表+正文
├── sc7_usecase_usecase/          6实例  用例图+usecase表+正文
└── sc8_pure_image/              17实例  纯图片+正文(无表)
```

## 每个实例的4个文件

```
sc1_001/
├── image.png       ← 实际图片(用例图/流程图/接口图等)
├── table.csv       ← 对应表格(capability/usecase/interface表, 原始行)
├── text.txt        ← 对应章节正文
└── meta.json       ← 元数据(场景/文档/章节/标题/文件引用)
```

## 场景统计

| 场景 | 实例数 | 图片 | 表格 | 正文 |
|------|--------|------|------|------|
| sc1 | 137 | ✓ | ✓ | ✓ |
| sc2 | 82 | 76/82 | ✓ | ✓ |
| sc3 | 32 | 29/32 | ✓ | ✓ |
| sc4 | 26 | ✓ | ✓ | ✓ |
| sc5 | 11 | ✓ | ✓ | ✓ |
| sc6 | 8 | ✓ | ✓ | ✓ |
| sc7 | 6 | ✓ | ✓ | ✓ |
| sc8 | 17 | ✓ | (无表) | ✓ |

## 缺失图片的实例(9个)

```
sc2_flowchart_usecase/2_077 (图 8  用户退出的流程图)
sc2_flowchart_usecase/2_078 (图 9  文电发送的流程图)
sc2_flowchart_usecase/2_079 (图 10 文电接收的流程图)
sc2_flowchart_usecase/2_080 (图 11  用户管理的流程图)
sc2_flowchart_usecase/2_081 (图 12  信息统计的流程图)
sc2_flowchart_usecase/2_082 (图 13  信息查询和管理的流程图)
sc3_interface_interface/3_006 (图 43 CSCI内部接口图)
sc3_interface_interface/3_024 (图 14 文电处理软件外部接口需求)
sc3_interface_interface/3_025 (图 15 文电处理的内部接口需求)
```

> 这些图片在原始.doc中是Visio OLE嵌入对象, LibreOffice/EMF提取均无法还原, 需Windows+Visio环境。

## 数据来源

- 图片: `data/gjb_438c/mineru_standard/*/office/images/fig_*.png` (从.doc提取的真实图片)
- 表格: `*_content_list.json` 的table项 (HTML解析为CSV)
- 正文: `*.md` 对应章节文本
- 场景定义: `data/gjb_438c/data_assets/semantic_modality_data.json`
