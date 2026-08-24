# Visio XML（VSDX）格式深度调研——面向解析器三大限制的规范级答案

> 调研日期：2026-08-24 | 用途：为 `tools/m0_anchor_extract_all.py` 的三项升级（嵌套组坐标变换、未粘合连线几何恢复、边标签）提供格式规范级依据
> 数据源优先级：微软官方文档（MS Learn ShapeSheet/XML元素参考 + VBA Connect属性）> python-vsdx 源码（github.com/dave-howard/vsdx master分支）> 本地16份SRS数据集实证（374页 / 13,447形状 / 2,182组）
> 证据等级标注：**[DOC]**=微软官方文档原文；**[SRC]**=python-vsdx源码；**[EMP]**=本地数据集实证（本文新增，所有实证均可在 `data/gjb_438c/visio_docx/*.docx` 的OLE嵌入中复现）

---

## 1. ShapeSheet单元模型总览

### 1.1 包结构（与我们相关的子集）

VSDX = OPC zip包。从.doc的OLE `Package`流解出的zip中，解析相关部件 [DOC: Introduction to the Visio file format (.vsdx)]：

| 部件 | 内容 | 注意 |
|------|------|------|
| `visio/pages/pages.xml` | Page列表：每页的 `PageSheet`（**PageWidth/PageHeight在这里**）+ `<Rel r:id>` 指向page文件 | **[EMP] page1.xml本身没有PageSheet**——现有解析器在page1.xml里找PageSheet必然落空，一直用8.5×11默认值，rx/ry归一化系统性偏差 |
| `visio/pages/page1.xml` | `PageContents`根：`Shapes`树 + `Connects`列表 | 我们目前唯一消费的部件 |
| `visio/masters/masters.xml` | `Master`元素列表（ID/NameU/Name/...）+ `<Rel r:id>` | **[EMP] 本数据集为旧式命名masters.xml；新版Visio写masters1.xml** |
| `visio/masters/master#.xml` | `MasterContents`根：单个根Shape及其子Shapes树 | Master ID ≠ 文件编号（见§5.1） |
| `visio/_rels/document.xml.rels` | 部件关系 | 解析masters.xml.rels才能定位master文件 |

### 1.2 Cell模型

每个Shape/PageSheet的属性是`<Cell N='...' V='...' F='...' U='...' E='...'/>` [DOC: Cell element (Visio XML)]：
- **N**：ShapeSheet单元名（PinX/BeginX/...）
- **V**：求值后的缓存值，**内部单位**（长度=英寸，角度=弧度，见§6.1实证）
- **F**：公式。三种特殊值：`'(公式)'`本地公式 / `No Formula`本地删除 / **`Inh` 从master继承**
- **U**：单位标注，**只是显示/输入单位元数据，不改变V的解释**（§6.1）
- **E**：错误信息（V为最后有效值）

结构规则 [DOC: Shape element (Shapes_Type complexType)]：固定单元集合的Section（XForm、Line Format等）扁平化为Shape的**直接Cell子元素**；多行Section（Geometry/Connection/Field等）才是`<Section N='...'>`+`<Row IX='...' T='...'>`。

### 1.3 与解析相关的Cell全景表

| Section（XML形态） | Cell | 语义 [DOC] |
|---|---|---|
| Shape Transform（直接Cell） | PinX/PinY | 形状pin（旋转中心）**相对父容器原点**的坐标 |
| | LocPinX/LocPinY | pin在**形状局部坐标系**（原点=未变换bbox左下角）中的位置，默认公式 `Width*0.5` |
| | Width/Height | 局部系下bbox尺寸（**1D形状可为负**，=End-Begin [EMP]） |
| | Angle | 相对父级的旋转角，**弧度** [EMP]；1D默认公式`ATAN2(EndY-BeginY,EndX-BeginX)` |
| | FlipX/FlipY | 0/1镜像标志 |
| | ResizeMode | 组缩放时子形状行为（0/1/2），静态解析可忽略 |
| 1-D Endpoints（直接Cell） | BeginX/BeginY/EndX/EndY | 1D形状起止点，**相对父级原点**；"此Section只出现在1D形状" [DOC: 1-D Endpoints Section] |
| Glue Info（直接Cell） | BegTrigger/EndTrigger | `_XFTRIGGER(Sheet.N!EventXFMod)`——粘合目标的第二证据源 [EMP] |
| | GlueType | 静态/动态粘合类型 |
| Line Format（直接Cell） | BeginArrow/EndArrow | 箭头：0=无，1-45=样式索引；EndArrow在**路径最后顶点** |
| | LineWeight/LinePattern/LineColor | 线型（LineWeight的V为英寸 [EMP]） |
| Text Transform（直接Cell） | TxtPinX/TxtPinY/TxtWidth/TxtHeight/TxtLocPinX/TxtLocPinY/TxtAngle | 文本块定位，与XForm同构（局部系） |
| Geometry（Section，IX=0..n） | 每行X/Y等 | 见§3.1 |
| Connection（Section） | X/Y/DirX/DirY/Type/AutoGen | 连接点，**局部坐标**；引用名`Connections.X i`（i为1基）对应Row IX（0基） [DOC: X Cell (Connection Points Section)] |
| Miscellaneous（直接Cell） | ObjType | 2=routable（可布线），连接线常为2 [EMP] |

Shape元素属性 [DOC]：`ID`、`Type`（**Group**/Shape/Guide/Foreign）、`Master`（继承的Master ID）、`MasterShape`（master内子形状ID）、`Name`（本地名）/`NameU`（通用名）、`LineStyle/FillStyle/TextStyle`、`Del`。

### 1.4 三个坐标系

1. **页面系**：原点左下，x右y上，单位英寸；
2. **形状局部系**：原点=自身bbox左下角（未旋转时），范围(0,0)-(Width,Height)，Geometry与Connection坐标都在此系 [DOC: X Cell (Geometry Section) "in local coordinates"]；
3. **父组局部系**：子Shape的PinX/PinY所在的系=父组自己的局部系；父组局部原点在其页面位置`(PinX-LocPinX, PinY-LocPinY)`处。

**[EMP]** 验证：1,288个无旋转组父子对中95%（1,221）子bbox经"子局部坐标+父组左下角"平移后落在父组bbox内，确认该坐标系语义（5%出界源于Visio允许组bbox≠子形状并集）。

---

## 2. 限制1：嵌套组的坐标变换

### 2.1 规范语义（变换链）

**[DOC]** PinX Cell (Shape Transform Section)："pin（旋转中心）相对其父原点"；LocPinX Cell："pin相对形状自身原点"。因此：

```
形状局部系 → 父容器系 的变换：
M = T(PinX,PinY) · R(Angle) · Flip(FlipX,FlipY) · T(-LocPinX,-LocPinY)

即逐点：
x1 = lx - LocPinX;  y1 = ly - LocPinY          # pin平移到原点
x2 = FlipX ? -x1 : x1;  y2 = FlipY ? -y1 : y1  # 关于pin镜像
x3 = x2·cosθ - y2·sinθ;  y3 = x2·sinθ + y2·cosθ  # 绕pin旋转(θ为弧度)
px = x3 + PinX;  py = y3 + PinY                 # 平移到父系位置
```

**嵌套组**：页面绝对坐标 = `M_page级 · M_组1 · M_组2 · ... · M_自身`，即从最内层shape逐级上溯——每次把当前结果当作父组的"局部坐标"再变换。伪代码：

```python
def shape_to_page(shape, lx, ly):
    c = resolved_cells(shape)          # 本地Cell ∪ master继承Cell（见§5.2）
    px, py = local_to_parent(lx, ly, c)   # 上面的四步公式
    parent = parent_group(shape)
    if parent is None: return px, py   # 父=页面
    return shape_to_page(parent, px, py)

def shape_bbox_page(shape):
    对角点(0,0),(W,H)（W/H取绝对值前先记录符号）逐点过shape_to_page
    取min/max得AABB（旋转>0时为外接框，够用）
```

### 2.2 旋转与翻转

- **Angle单位=弧度** [EMP]：数据集332个非零Angle全部是弧度形态（如`1.570796326794897`=90°）；master中`<Cell N='Angle' V='0' U='DEG'/>`的U只是显示单位。
- **Flip**：镜像轴过pin（先减LocPin、镜像、再旋转、再加Pin）。**[不确定]** flip与rotate的先后次序微软文档未以矩阵形式给出；libvisio类实现采用"先flip后rotate"（即上面的公式）。数据集Flip仅9例、Flip与Angle同时非零更少，风险低；建议实现时把次序做成可切换并用Visio画"翻转+旋转45°"样图对照验证（见§9）。
- **双轴同时Flip**等价于旋转180°，与任何次序一致。

### 2.3 组没有缩放分量（重要简化）

组的XForm是**纯仿射（翻转+旋转+平移），不含缩放**：用户交互式缩放组时，Visio在保存时把缩放**烘焙进子Shape的Cell值**（子PinX/Width被改写）。因此解析时不需要从"组Width vs 子形状extents"反推比例。但要注意：组自身Width/Height与子形状并集**可以不一致**（[EMP] 5%出界例），不能用父bbox约束反推子坐标。

### 2.4 参考实现现状（不能照抄）

**[SRC]** python-vsdx **没有实现完整变换**：`Shape.bounds`（shapes.py）对2D形状只做 `PinX-LocPinX` 起点+Width/Height外推，`Shape.relative_bounds` 对嵌套形状**只加父组bounds平移，完全忽略父组Angle/Flip**。这是它的已知弱点——我们需要自实现§2.1公式，python-vsdx可借鉴的只有master解析与Geometry合并（§5、§7）。

### 2.5 涉及Cell清单

`PinX, PinY, LocPinX, LocPinY, Width, Height, Angle, FlipX, FlipY`（ResizeMode/DontMoveChildren等不影响静态变换）。**[EMP]** 所有这些Cell都可能整体缺失（组的Width/Height、标签形状的全部XForm）——必须配合§5.2的master继承解析，否则6,696个仅`MasterShape`引用的形状（占全部50%）无坐标可用。

---

## 3. 限制2：未粘合连线的完整恢复

### 3.1 Geometry Section规范

`<Section N='Geometry' IX='0..n'>`（多个Geometry=多个子路径）行类型 [DOC: Geometry Section]：

| 行类型 T | Cell | 语义 |
|---|---|---|
| MoveTo | X,Y | 路径起点；出现在中间=路径断开（填充时按直线闭合） |
| LineTo | X,Y | 直线段终点 |
| ArcTo | X,Y,A | 圆弧终点+A=**弓高**（弦中点到弧的距离，符号定方向） |
| EllipticalArcTo | X,Y,A,B,C,D | 椭圆弧：A/B=半径，C=旋转角，D=偏心率/扫向 |
| PolylineTo | X,Y,A | 折线段 |
| SplineStart/SplineKnot | X,Y,A... | 样条控制点/节点 |
| NURBSTo | X,Y,A-F | NURBS |
| Ellipse/InfiniteLine | X,Y,A,B... | 整椭圆/无限线 |
| RelMoveTo/RelLineTo/RelCubBezTo/... | X,Y | **相对坐标**：实际值=X×Width, Y×Height（Visio 2010+） |

所有X/Y都在**形状局部系**（0,0)-(Width,Height)内 [DOC: X Cell (Geometry Section)]；1D形状Width/Height可为负（`=GUARD(EndX-BeginX)` [EMP]），局部坐标随之落在负区间——合法。

**[EMP] 行级+Cell级master继承**：实例Geometry只存差异行/差异Cell。实测Dynamic connector实例只有`LineTo IX=2(仅Y)/3/4`三行，`MoveTo IX=1`及部分X Cell全部继承自master（master2.xml中有`MoveTo(0,0),LineTo...`）。重建前必须按IX合并master行，行内再按Cell名合并。

### 3.2 完整路径重建算法

```python
def connector_polyline(shape, master_tree):
    rows = merge_rows(            # 按IX: master行打底，实例行覆盖；Del=1的行删除
        master_geometry_rows(shape, master_tree),
        instance_geometry_rows(shape))
    pts, cur = [], None
    for row in sorted(rows, key=IX):
        x, y = row.X, row.Y
        if row.T in ('RelMoveTo','RelLineTo',...):
            x, y = x*W, y*H       # Rel系乘Width/Height
        if row.T == 'MoveTo' or first: cur = (x,y); pts.append(cur)
        elif row.T == 'LineTo':  cur = (x,y); pts.append(cur)
        elif row.T == 'ArcTo':   pts += arc_approx(cur, x, y, A, n=8)  # 弧离散化
        elif row.T == 'EllipticalArcTo': pts += ellarc_approx(cur, x,y,A,B,C,D)
        # Spline/NURBS同理离散化；MoveTo在中间→断笔(多段)
    return [shape_to_page(shape, x, y) for x, y in pts]   # 复用§2.1变换！
```

**自检** [EMP]：变换后的首点应≈(BeginX,BeginY)、末点≈(EndX,EndY)（Dynamic connector的MoveTo(0,0)局部点经XForm变换后恰为Begin端——因为其PinX/LocPinX公式保证）。偏差大说明变换或行合并有错，可直接当回归测试。

### 3.3 1D/2D判定标准

- **权威判据 [DOC]**：1-D Endpoints Section"只出现在1D形状"→ 判定=Shape存在`BeginX` Cell（本地或master继承后）。
- **不存在OneD Cell**：VBA有Shape.OneD属性，但VSDX的Cell N值表中无`OneD` [DOC: Cell element的N值表 + EMP]；Shape的Type属性也不编码1D信息。
- 辅助：`ObjType=2`(routable)、`GlueType`存在、NameU含connector/Flow [EMP]。
- **注意**：嵌在组内的连接线，其BeginX/EndX是**组局部系**坐标，仍需过父组变换（§2.1）。

### 3.4 箭头与方向信息

- **[DOC]** Line Format Section：`BeginArrow`/`EndArrow`（0=无，1-45=样式索引），EndArrow画在**路径最后顶点**（=End端）；`BeginArrowSize/EndArrowSize`定大小。方向推断增强规则：
  - EndArrow≠0 → Begin→End即流向（与Connect语义一致）；
  - 仅BeginArrow≠0 → 箭头指向Begin端，实际流向可能是End→Begin，应翻转或降置信度。
- **粘合公式是第二证据源 [EMP]**：连接线的`BeginX F='PAR(PNT(Sheet.60!Connections.X1,Sheet.60!Connections.Y1))'`直接编码了"Begin端粘在Shape.60的连接点1"；`BegTrigger/EndTrigger F='_XFTRIGGER(Sheet.N!EventXFMod)'`同义。Connect记录缺失/不完整时可从F属性解析`Sheet.(\d+)!Connections\.X(\d+)`恢复粘合关系。
- **Connect元素Part编码（官方常量表）[DOC: Connect.FromPart/ToPart property (Visio VBA)]**：
  - FromPart：0=无，7/8=BeginX/BeginY，**9=Begin整体**，10/11=EndX/EndY，**12=End整体**，13=Angle，14=Pin，1-6=左/中/右/下/中/上边，100+=控制点行；
  - ToPart：-1错，0=无，1=guideX，2=guideY，**3=WholeShape（动态粘合到形状）**，4=参考线交点，7=Angle，**100+行号=连接点**。
  - **[EMP]** 数据集实测全部为 `FromPart=9(Begin)/12(End)` + `ToPart=100+连接点行号`，与常量表一致。现有解析器按`FromCell.startswith('Begin')`分边正确，但应同时兼容`FromCell='BeginY'/'EndY'`（粘到参考线时产生成对X/Y记录 [DOC: Connect.FromCell Remarks]）并过滤FromCell=PinX/Angle/Controls.X的**2D形状间粘合**（不是边）。

### 3.5 连接点（Connection Section）语义

- 定义位置：形状的`<Section N='Connection'>`，每行Cell：X/Y（**局部坐标**）、DirX/DirY（对齐方向）、Type（0=inward，1=outward，2=inward&outward）、AutoGen [DOC: Connection Points Section/Row；EMP: Rectangle master有5个点=下中/右中/上中/左中/中心]。
- **连接点几乎总定义在master上**，实例省略或行内F='Inh' [EMP]——解析"节点哪个位置被连"需master解析。
- 引用约定：`Connections.X i`（i=1基）↔ Row IX=i-1（0基）↔ Connect的ToPart=100+IX [EMP三向验证一致]。

### 3.6 涉及Cell清单

Geometry行(X/Y/A/B/C/D)、XForm全套（路径变换）、BeginX/Y、EndX/Y、BegTrigger/EndTrigger（粘合公式）、BeginArrow/EndArrow（方向）、ObjType/GlueType（辅助1D判定）、Connection行（吸附目标精确位置）。

---

## 4. 限制3：边标签

### 4.1 "边上文字"的存储方式（四种）

1. **连接线自身Text** [EMP]：数据集327个连接线带Text；内容含`<cp IX='n'/>`（字符格式引用）、`<pp/>`、`<tp/>`标记，取文本用itertext即可剥除。文本块精确位置由TxtPinX/TxtPinY（局部系）给出——**这是"线上文字"的权威锚点**，不是近似。
2. **独立文本Shape**（用文本工具画的标签）：无Master（或Master=纯文本master）、无Geometry Section、有Text [EMP]：数据集273个"疑似标签"实为**组内Name子形状**（`MasterShape='6'`引用UML/状态机master的标签子形状）；真正的顶层游离文本标签也存在。判定：无Geometry+无Connection+LinePattern/FillPattern=0+非1D。
3. **字段Text** [DOC]：`<Text>`内`<fld IX='n'/>`引用Field Section（N='Field'）Row IX=n的Value Cell（动态字段如宽度/日期/Shape Data）。**[EMP] 数据集fld计数=0**，未使用，解析器可低优先支持。
4. **组内标签子形状**：与图形元素同组的Name子形状（见上）。

### 4.2 独立标签→连接线的关联策略

Visio**没有**"标签属于边"的显式关系，线索按优先级：

1. **共同父组**：标签与连接线在同一Group内（组是最强的语义绑定）；
2. **几何邻近**：标签bbox中心（需先经§2.1变换到页面系！）到连接线**折线段**（§3.2重建，不是Begin/End直线）的最小距离 < 阈值（建议0.25-0.4in，与现有SNAP_TH=0.35量级一致）；一条线多个候选标签时取距离最小者，且排除已被节点bbox包含的标签；
3. **排除法**：标签若与某节点的bbox重叠/被包含，更可能是节点的一部分而非边标签（现有子Shape文本合并逻辑可复用）。

**依赖关系**：本限制的几何邻近方案必须先完成限制1（标签多在组内，坐标是组局部系）和限制2（有完整折线才能算距离）——三者是递进关系。

---

## 5. Master继承机制与类型判定升级

### 5.1 masters.xml结构与ID→文件映射

**[EMP + SRC]** 完整链条（官方Master_Type文档未列Rel子元素，以下为数据集实证+python-vsdx实现双重确认）：

```
masters.xml:  <Master ID='56' NameU='Rectangle.5' Name='矩形.5' UniqueID BaseID MatchByName MasterType='2'>
                  <PageSheet>...</PageSheet><Icon>...</Icon><Rel r:id='rId1'/>
masters.xml.rels: rId1 → master1.xml ； rId2 → master2.xml
master#.xml:  <MasterContents><Shapes><Shape ID='5' ...>（master根形状及其子Shapes树）
```

- **Master ID与文件编号无关** [EMP]：ID=56→master1.xml、ID=5→master2.xml；必须经`Rel r:id`→rels解析，不能按`master{ID}.xml`猜。
- 页面Shape的`Master='5'`指masters.xml里的Master元素ID=5（其内容在master2.xml的根Shape树）。
- master的PageSheet含自己的PageWidth/PageScale等（图纸语义，与实例无关）。

### 5.2 delta继承规则（三层）

实例Shape是master的**差异覆盖**，缺失部分逐层继承 [DOC: F='Inh'语义；SRC: shapes.py cell_value/geometry.py；EMP]：

1. **Cell级**：`Shape.cell_value(name)`：本地dict找不到→递归查master形状同名Cell（python-vsdx实现，正确）。
2. **Row级（Geometry/Connection等）**：以master行为底、实例行按IX覆盖；实例行内**Cell也可部分缺失**（EMP：LineTo IX=2只有Y，X继承master）；`Row/@Del='1'`表示删除被继承行（python-vsdx的GeometryRow.del_bool）。
3. **文本**：实例无`<Text>`→继承master的Text [SRC: Shape.text]。

**父链Master传播（关键）[SRC: shapes.py `if self.master_page_ID is None and isinstance(parent, Shape)`]**：子Shape只有`MasterShape='6'`没有`Master`时，继承**父组的Master**，然后在master#xml的形状树里按ID=6找到具体子形状。**[EMP] 6,696个形状（50.0%）只靠此机制获得XForm**——不实现master解析，一半形状无坐标、无几何、无类型。

### 5.3 类型判定升级方案

**结论：`Master`的NameU是最可靠的类型来源，实例`NameU`次之，实例`Name`（本地化名）最弱。**

- 实例NameU通常= `'{Master的NameU}.{实例序号}'`（EMP：`Dynamic connector.62`、`矩形.63`）→ 去掉`.N`后缀即类型名；Name是本地化的（`动态连接线`），跨模板不稳定。
- **[EMP] NameU（去后缀）分布**：Sequence Flow 691 / Dynamic connector 667 / Discriminator 501 / Use Case 433 / Generalization 268 / Actor 260 / Transition 225 / Task 208 / State 206 / Control Flow 202 / Initial State 107 / Final State 96 / System Boundary 71 ...—— 现有TYPE_RULES正则应改为对**master NameU**（经Master ID→masters.xml查询）匹配，实例NameU只做fallback。
- python-vsdx识别连接线仅用 `universal_name == 'Dynamic connector'`（shape_type_names表只收了德/英两种）[SRC]——覆盖面不足，我们的NameU正则表更全。

---

## 6. 单位与坐标系统一方案

### 6.1 U与V的真实语义（实证结论）

**官方文档只说"U表示单位，默认DL"**，未明确V的单位 [DOC: Cell element]。**[EMP] 三组铁证证明V恒为内部单位（长度=英寸、角度=弧度），U只是公式输入/显示单位的元数据**：

1. `Height V=-0.476464907470703 U='MM'` 与 `EndY V=4.604011361120728(无U) - BeginY V=5.080476268591431 U='MM'` 精确相等——同一公式的三个量U不同而数值同系；
2. `LineWeight V=0.003472222222222222 U='PT'` = 0.25pt的**英寸**值（0.25/72）；`TxtWidth V=0.972222222222222 U='PT'` = 70pt=0.972in；
3. master PageSheet `PageWidth V=3.937007874015748 U='MM'` = 100mm=3.937in。

**实践方案**：解析时**直接`float(V)`当英寸/弧度用，完全忽略U**。仅当V缺失需从F公式求值时才需要单位换算（PT→in除以72，MM除以25.4，DEG→rad乘π/180）。常见U值：IN/MM/CM/PT/DEG/RAD/BOOL/STR/PCT/COLOR。

### 6.2 页面尺寸来源（现存bug）

**[EMP]** PageWidth/PageHeight在`visio/pages/pages.xml`对应`<Page ID>`的PageSheet里，**不在page1.xml**。现有解析器`root.find('.//PageSheet')`在PageContents里必然为None。修复：解OLE包时顺带读pages.xml，按当前page文件（经pages.xml.rels或Page的Rel元素映射）取PageWidth/PageHeight。若比例图（PageScale≠DrawingScale）还需除以比例——**[EMP]** 本数据集PageScale=DrawingScale（1:1），可加断言而非实现。

### 6.3 DPI与渲染对齐

- VSDX是**矢量格式，无内嵌DPI**；英寸→像素= `inch × 目标DPI`（屏幕96/印刷300自选，保持PageWidth:PageHeight比例即可）。
- Word里嵌入Visio的**显示**尺寸由OLE的预览图（EMF/metafile）与Word对象框决定，与vsdx内部坐标系无关——做"渲染对齐"时以页面宽高比+内容bbox为准，不要试图从.doc推出显示缩放。我们的rx/ry归一化方案（除以PageWidth/PageHeight并翻转y）方向正确，但必须先修§6.2的页面尺寸来源。

---

## 7. python-vsdx参考实现要点（可借鉴逻辑描述）

**[SRC]** github.com/dave-howard/vsdx（master分支，BSD-3）：

| 文件 | 可借鉴点 | 不可照抄处 |
|---|---|---|
| `vsdx/vsdxfile.py` `load_master_pages()` | masters.xml.rels解析+Master元素的`Rel r:id`→master路径；`master_index[NameU]`、`get_master_page_by_id(ID)` | 硬编码`masters.xml`旧式命名（新版masters1.xml会失败）；只接受.vsdx/.vsdm文件名 |
| `vsdx/shapes.py` `Shape` | Cell dict构建（直接Cell子元素）；`cell_value`的本地→master递归继承；`master_shape`属性（`master_page.child_shapes[0]`+MasterShape子形状查找+**父组Master传播**）；`text`的master继承 | `bounds/relative_bounds`**不含旋转/翻转**，嵌套坐标错误 |
| `vsdx/geometry.py` `Geometry/GeometryRow` | Geometry行按IX与master合并、行内Cell覆盖、`Del`删除继承行 | `start_pos()`等只读MoveTo无变换；Rel系行未处理 |
| `vsdx/connectors.py` `Connect` | from/to/FromCell/ToCell四元组封装；创建连接用`FromPart=9/12,ToPart=3`与官方常量表一致 | 依赖Media模板文件的写路径，与解析无关 |
| `vsdx/pages.py` `Page` | `get_connects()`（递归找Connect）、`get_connectors_between(a,b)`（两端connected_shapes交集） | 页面尺寸从pages.xml的PageSheet取（`_pagesheet_xml`）——**这正是我们该抄的页面尺寸读取逻辑** |

结论：python-vsdx的**包结构导航+master继承+Geometry合并**三层可以直接借鉴（我们的ElementTree直读架构下按同样规则实现即可），**坐标变换必须自研**（§2.1），连接器判定用我们的NameU正则表替代它的硬编码表。

---

## 8. 出处清单

**微软官方文档（MS Learn）**
- Introduction to the Visio file format (.vsdx)：learn.microsoft.com/en-us/office/client-developer/visio/introduction-to-the-visio-file-formatvsdx
- Cell element (Visio XML)（N/V/F/U/E定义+全部Cell名表）：…/visio/cell-elementvisio-xml
- Shape element (Shapes_Type complexType)：…/visio/shape-element-shapes_type-complextypevisio-xml
- Connect element (Connects_Type complexType)：…/visio/connect-element-connects_type-complextypevisio-xml
- Master element (Masters_Type complexType)：…/visio/master-element-masters_type-complextypevisio-xml
- PinX/LocPinX/Angle Cell (Shape Transform Section)：…/visio/pinx-cell-shape-transform-section 等
- 1-D Endpoints Section：…/visio/1-d-endpoints-section
- Geometry Section + MoveTo/X Cell (Geometry Section)：…/visio/geometry-section、…/visio/x-cell-geometry-section
- Connection Points Section / Row / X Cell：…/visio/connection-points-section 等
- Text Transform Section：…/visio/text-transform-section
- BeginArrow Cell (Line Format Section)：…/visio/beginarrow-cell-line-format-section
- VBA Connect.FromPart/ToPart/FromCell/ToCell（Part常量表+粘合类型枚举）：…/office/vba/api/visio.connect.frompart 等
- [MS-VSDX] 规范入口：learn.microsoft.com/en-us/openspecs/sharepoint_protocols/ms-vsdx/

**python-vsdx源码（master分支）**：raw.githubusercontent.com/dave-howard/vsdx/master/vsdx/{shapes,geometry,connectors,pages,vsdxfile}.py

**本地实证**：`data/gjb_438c/visio_docx/`16份docx的OLE嵌入Package流（检查方式：olefile→Package→zipfile→pages/page*.xml、masters/masters.xml及其.rels）

---

## 9. 不确定项与验证建议

| # | 不确定点 | 现状 | 验证方法 |
|---|---|---|---|
| 1 | Flip与Rotate的作用次序 | 微软文档无矩阵级定义；本文采用libvisio式"先flip后rotate" | 用Visio画"单轴翻转+45°旋转"形状存vsdx，比对其Geometry顶点经两种次序变换的渲染结果 |
| 2 | "V恒为内部单位(英寸/弧度)" | 官方文档只定义U默认DL，未明说V单位；本文靠三组数据集铁证+libvisio旁证 | 抽样已知物理尺寸的形状（如A4页面PageWidth=8.27in）核验 |
| 3 | Master元素的`<Rel r:id>`子元素 | 官方Master_Type文档的子元素表未列出Rel，但数据集与python-vsdx均依赖它 | 无需验证（双源一致）；但写解析器要兼容无Rel的老文件 |
| 4 | masters1.xml/pages1.xml新式命名 | 数据集全部旧式（masters.xml/pages.xml），python-vsdx只支持旧式 | 取一份Visio 2016+生成的vsdx验证命名分支 |
| 5 | 5%子形状出父组bbox的原因 | 推测为组bbox≠子形状并集（Visio允许）或master继承的Width与实例状态不同步 | 逐例检查出界样本的master Width公式 |
| 6 | EllipticalArcTo的D Cell语义（偏心率vs扫向标志） | 文档行文含糊（"D=sweep/eccentricity"混用） | 数据集未出现椭圆弧行 [EMP: Geometry行全为MoveTo/LineTo]，可暂不实现，留TODO |

**实施顺序建议**：master解析（§5，一切的前提）→ 页面尺寸修复（§6.2，一行改动）→ 嵌套变换（§2）→ Geometry路径重建+方向修正（§3）→ 标签关联（§4）。每步都有本文给出的自检手段（Begin/End重合检验、父子bbox包含率95%基线、ToPart/FromPart常量表）。
