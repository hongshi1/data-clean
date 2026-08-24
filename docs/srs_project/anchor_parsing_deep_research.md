# Visio锚点解析：深度调研综合报告

> 2026-08-24 | 综合三份深度调研 + 数据集实证诊断 + 已实施的修复
> 前置文档：
> - `visio_parsing_landscape.md`（165行）：先例版图——我们是孤例吗？
> - `visio_format_deep_dive.md`（323行）：格式规范深度——三个限制的规范级答案
> - `grammar_methods_survey.md`（143行）：文法方法谱系——语法关联与推断的选型
> 本文档是**收束版**：回答"我们知道了什么、修了什么、接下来怎么升级"。

---

## 一、核心结论速览

### 1.1 先例问题的答案（novelty定位）

| 问题 | 答案 |
|------|------|
| 学术上有先例吗？ | **无直接先例**（arXiv/DBLP/OpenAlex三库零命中） |
| 工程上有先例吗？ | 有——微软官方文档明文把"读Visio工作流图执行业务逻辑"列为vsdx设计场景；python-vsdx/POI/libvisio均有成型解析能力 |
| 最接近的学术先驱？ | Shiinoki 2025（Office源文件→LLM，arXiv:2502.04389）；ChemScraper（IJDAR 2024，PDF矢量直读） |
| 我们的正确写法 | **不是"首个解析Visio"，而是"首个把嵌入源码回收为一致性校验的保真锚点，并系统量化覆盖率与增益"** |

### 1.2 格式深挖的关键发现（三个意外）

1. **50%的形状（6696个）仅靠Master继承获得坐标**——只靠`MasterShape`属性+父组Master传播，不解析masters.xml就有一半形状无XForm、无几何、无类型。**Master解析是一切升级的前提**
2. **PageSheet从不在page1.xml里**（0/374），全在pages.xml，且真实页面尺寸差异巨大（1.17×3.28到7.62×4.62英寸）→ 我们的全部归一化坐标都用了错误的8.5×11默认值。**本轮已修复**（见第三节）
3. **V恒为内部单位（英寸/弧度），U只是显示元数据**——三组铁证（同一公式三个量U不同而数值同系；LineWeight的PT标注值实为英寸；master页面MM标注值实为英寸）。解析时直接float(V)，完全忽略U

### 1.3 实证诊断（374页/13447形状的量化）

| 诊断项 | 数值 | 含义 |
|--------|------|------|
| 嵌套组出现次数 | 963次（平均2.6次/页） | 限制1影响面广，变换必须实现 |
| 非零Angle的Shape | 332个（2.5%） | 旋转参与变换，量不大但不能忽略 |
| 最大嵌套深度 | 2 | 变换链最多两级，实现简单 |
| 1D Shape总数 | 2985个 | 连接线候选全集 |
| Connect记录 | 5267条（≈2634根粘合线×2） | 约350根1D线未粘合（限制2的对象） |
| 有Geometry Section的Shape | 7213个 | 折线重建的数据基础充足 |
| 连接线上带文本 | 149个 | 边标签的主来源 |
| 引用Master的Shape | 5530个 | Master继承的主用户 |
| master文件 | 1976个 | 需要解析的模具库 |

---

## 二、三个已知限制的规范级解决方案（摘要）

### 限制1：嵌套组坐标变换

**变换公式**（微软文档+python-vsdx源码+实证三方确认）：

```
形状局部系 → 父容器系:
  M = T(PinX,PinY) · R(Angle弧度) · Flip(FlipX,FlipY) · T(-LocPinX,-LocPinY)

嵌套组: 页面绝对坐标 = M页面级 · M组1 · M组2 · ... · M自身 (逐级上溯)
```

**重要简化**：组的XForm不含缩放分量——用户缩放组时Visio把缩放烘焙进子Shape的Cell值，解析时无需反推比例。

**参考实现警告**：python-vsdx的bounds/relative_bounds**没有实现旋转/翻转**（只做平移叠加）——不能照抄，必须自研。

**自检手段**：变换后1D线的首点应≈(BeginX,BeginY)、末点≈(EndX,EndY)；无旋转组父子bbox包含率应≥95%（实测基线1221/1288）。

### 限制2：未粘合连线的完整恢复

**Geometry Section行合并**（行级+Cell级master继承）：

```
完整折线 = 实例行按IX覆盖master行(行内Cell也可部分继承) 
        → MoveTo/LineTo直接取点, ArcTo离散化
        → 每点过限制1的变换到页面系
```

**方向判定的三重证据源**：
1. Connect记录（现有，FromPart=9/Begin、12/End，ToPart=100+连接点行号）
2. **箭头Cell**：EndArrow≠0 → Begin→End即流向（与Connect一致）；仅BeginArrow≠0 → 应翻转或降置信
3. **粘合公式**：连接线的`BeginX F='PAR(PNT(Sheet.60!Connections.X1,...))'`直接编码粘合目标——Connect缺失时可从F属性正则恢复

### 限制3：边标签

**四种存储方式**：连接线自身Text（149个，TxtPinX/TxtPinY给出精确位置——**权威锚点而非近似**）、独立文本Shape、字段Text（数据集未用）、组内Name子形状。

**独立标签的关联策略**（Visio无显式归属关系）：共同父组 > 标签中心到**完整折线**（限制2重建后）的最小距离 > 排除法（被节点bbox包含的更可能是节点文字）。

**依赖链**：限制3依赖限制2（要完整折线才能算距离）依赖限制1（标签多在组内，坐标是组局部系）——三者必须按序实现。

### 类型判定升级

**Master的NameU是最可靠的类型来源**（去`.N`后缀）：Sequence Flow 691 / Dynamic connector 667 / Discriminator 501 / Use Case 433 / Generalization 268 / Actor 260 / Transition 225 / Task 208 / State 206...——比我们现在的Name正则表覆盖面大得多，且跨模板稳定。

**Master ID与文件编号无关**（ID=56→master1.xml、ID=5→master2.xml），必须经`masters.xml.rels`的Rel解析。

---

## 三、本轮已实施的修复

### 3.1 页面尺寸bug（已修复✓）

- **症状**：所有373图的page字段都是默认8.5×11.0，归一化坐标rx/ry系统性错误
- **根因**：PageSheet在pages.xml的Page元素下，page1.xml（PageContents根）里根本没有——旧代码`root.find('.//PageSheet')`必然落空
- **修复**：解析pages.xml→按Rel r:id映射到pageN.xml→每页取真实尺寸传入parse_page
- **验证**：373页中0个用默认值；oleObject28从错误的8.5×11.0修正为真实的1.30×3.35；节点归一化坐标落在合理区间
- **波及**：sc2锚点、全量锚点、325个pair的visio_anchor.json全部重新生成

### 3.2 工具链产出（本轮新增）

| 工具 | 功能 |
|------|------|
| `m0_anchor_extract.py`（修复版） | 页面尺寸从pages.xml读取 |
| `m0_anchor_extract_all.py` | 16文档全量提取（373图5145节点2671边） |
| `m10_batch_anchor_supplement.py` | 325对pair补充visio_anchor.json（可信度分级） |

---

## 四、文法方法调研的选型结论（语法关联与推断）

针对"用文法做关联和推断"的四个需求，推荐排序：

| 需求 | 首选方案 | 理由 | 死胡同 |
|------|---------|------|--------|
| ①用例表格解析 | 手写CFG+属性文法（Lark骨架+Knuth属性方程） | GJB表格格式固定，CFG够用；属性方程顺带执行编号连续性/引用有效性检查=语法层检测点 | 纯字符串正则（已踩坑）；无约束CMG |
| ②图结构验证 | 类型化属性图+负约束NAC（AGG/GROOVE执行） | 373锚点抽象为类型图schema；GJB结构规则编译为禁止子图模式 | 通用图剖析器（代价高） |
| ③文法归纳 | gSpan频繁子图+SEQUITUR骨架挖掘，合并+人工审校 | Gold定理下只能要"覆盖率高+简洁"，不能要"正确"；两个工具都正例驱动无需标注 | "学出唯一正确文法"（理论不可达）；L*（需oracle） |
| ④图文对齐 | 两阶段：指纹粗筛（Deckard/Winnowing式）+树编辑距离/GED精算 | GED的NP难在373规模可控；编辑脚本可解释（"差两步编辑"） | 全量精确GED；TGG可作次选（声明式对应规则） |

**最有趣的先例**：Pratt 1971的pair grammar（JCSS）——"图文对应写成文法规则"的1971年直系先例；Kukluk 2006-2008填补了"从图实例归纳图文法"的空缺。

**视觉文法线的结论**：经典线（Shaw PDL/Fu句法模式识别/Lakin空间解析/Marriott CMG）的核心思想是"用产生式规则解析视觉结构"——**但我们的场景里Visio XML已经给出了拓扑，不需要像素级文法解析**。文法的正确用法在"验证与推断"（②③④），不在"解析"（①的表格侧除外）。

---

## 五、升级路线图（按依赖序，含自检判据）

```
阶段0(已完成✓): 页面尺寸修复 + 全量提取 + pair_dataset补充
阶段1: Master解析(masters.xml.rels → Master ID → masterN.xml → 继承链)
       判据: 6696个仅MasterShape引用的形状获得坐标/几何/类型
       自检: 类型分布覆盖NameU表; 父子bbox包含率≥95%
阶段2: 嵌套组坐标变换(限制1)
       判据: 332个旋转形状的绝对坐标正确
       自检: 1D线首末点≈BeginX/EndX对
阶段3: Geometry折线重建(限制2主体)
       判据: 7213个有Geometry的形状的完整路径
       自检: 变换后首末点与Begin/End重合(回归测试)
阶段4: 方向三重证据融合(Connect+箭头Cell+粘合公式)
       判据: 未粘合线的方向判定准确率(可用渲染图人工核对样本)
阶段5: 边标签关联(限制3, 依赖2的折线)
       判据: 149个线内Text+独立标签关联; TxtPinX锚点验证
阶段6: 类型判定切换到Master NameU
       判据: other类节点占比从~50%降到<10%
```

每阶段独立可验证、可回滚；阶段1是分水岭（一半形状的可用性）。

---

## 六、对本项目方法论的反馈（调研如何改变设计）

1. **锚点的"保真"声明需要加脚注**：当前100%保真的说法仅对"有Connect记录+顶层Shape"成立；完整保真需要Master解析+变换（阶段1-2）。论文的extraction-faithful声明应精确为"by construction, verified on sample"——建议对20图人工核对渲染vs解析
2. **silver label生成（P3）必须等阶段2**：坐标变换不实现，bbox就是错的——YOLO训练标签会带噪声
3. **文法不是玄学是工具**：四个需求各有成熟方案，选型表可直接进论文的method节或附录
4. **python-vsdx可以当"对照实现"**：它的master继承/Geometry合并逻辑可借鉴，但坐标变换是错的——这本身是论文的工程贡献点之一（我们修对了它没实现的）

---

## 附：文档地图

```
docs/srs_project/literature_survey/
├── visio_parsing_landscape.md      先例版图(165行) — novelty定位/必引清单/工具链
├── visio_format_deep_dive.md       格式规范(323行) — 三限制的规范答案/Cell全景/实证
├── grammar_methods_survey.md       文法谱系(143行) — 四需求选型/死胡同清单
└── (本文件的同级) deep_technical_report.md  深度技术报告(419行) — 整体架构设计
docs/srs_project/
└── anchor_parsing_deep_research.md 本综合报告
```
