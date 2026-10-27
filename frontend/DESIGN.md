# DESIGN.md — SRS上下文关联图谱平台

内部研究工具。Token 速查:

## 色板
| Token | 值 | 用途 |
|---|---|---|
| --c-entity | #2563EB | E实体/种子/路径高亮/主按钮 |
| --c-text | #64748B | TXT文本节点 |
| --c-table | #0891B2 | TBL表格节点 |
| --c-image | #059669 | IMG图片节点 |
| --c-seq | #D97706 | SEQ时序节点; 悬空异常 #dc2626 |
| --c-knw | #7C3AED | KNW知识节点 |
| --c-bg | #f5f7fa | 页面底; 画布为径向渐变白→#e8edf3 |
| --c-border | #e5eaf1 | 分隔线/卡片边 |
| --c-dim | #94a3b8 | 次要文字 |

## 字体/间距
- 系统 + PingFang SC/Microsoft YaHei; 图内文字 8-11px, 面板 12.5px, 标题 15px
- 面板宽: 左280 / 右330; header 52px; 卡片圆角10, padding 10; 图节点圆角8

## 布局(径向图)
- 中心=种子实体(蓝圆r34+呼吸光圈); hop1环r=175, hop2环r=305
- 模态扇区: TXT左上(-135°) TBL右上(-45°) IMG右下(45°) SEQ/KNW左下(135°), 跨度78°
- 边宽=1+5w; 虚线类型: same_section*/section_adjacent/rule_applies/anchor_root_fallback

## 动画(仅transform/opacity)
- 节点入场: scale 0.25→1 弹性, hop0=0ms, hop1=260+35i, hop2=640+30i
- 边入场: 淡入 delay 820ms; 种子呼吸圈 2.4s循环

## 交互
- 悬停节点→其回中心路径高亮(蓝#2563EB), 其余降至0.16透明度
- 点击→右栏详情; 双击IMG→大图; 滚轮缩放/拖拽平移; 图例点击显隐模态

## 已接受的债
- QA行内图片预览依赖pair_dataset静态端点(后端P1未提供), 暂以caption文本替代
- 大规模(>150节点)未做LOD; 当前top_k上限20×5模态在SVG下可承受
