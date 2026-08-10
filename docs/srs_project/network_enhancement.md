# 网络增强数据集 (Network Enhancement)

> 日期: 2026-08-10
> **原则: 所有网络数据标注 source=network, 与16份原生(source=native)完全隔离**
> **网络数据只做泛化测试, 不参与主实验; 评测时分开报告**

## 三个网络数据集

| 数据集 | 来源 | 规模 | 用途 | 架构 |
|--------|------|------|------|------|
| PURE | 18份英文SRS | 18份/2664条需求 | 名称一致性泛化(英文) | XML结构化SRS(章节+text_body) |
| FinBalance | 会计一致性基准 | 710条(正480/负230) | 数值一致性跨域 | 710条记录×多份PDF文档(ocr_text) |
| ScholScan | 学术论文 | 2图+5表+67段 | 多模态一致性泛化 | 20页MinerU解析(content_list_v2) |

## 文件

- `data/gjb_438c/data_assets/network_enhancement.json` — 全部增强数据(2075KB)

## 使用原则

1. 所有增强条目 `source: "network"`
2. 16份原生数据 `source: "native"`
3. 评测协议: 原生为主实验, 网络为泛化测试, 分开报告
4. FinBalance的负例有 `inconsistency_reasons`(不一致原因), 是受控生成的gold truth
5. PURE是英文SRS, 检测器需处理英文名称
6. ScholScan是学术论文, 检测器需跨领域泛化
