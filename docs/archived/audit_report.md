# SRS项目状态审计与改进方向分析

> 审计基准日: 2026-08-02
> 审计方法: 深入核查实际代码(`tools/*.py`)与实际产出(`data/srs_*`),而非依赖文档自述
> 核心结论: **当前所有检测指标被解析层误报主导,在修复解析前任何P/R/F1都不可信**

---

## 0. 审计发现速览(与项目自述的偏差)

项目自述(AGENTS.md/PROJECT_GUIDE.md)与实际状态的**重大偏差**:

| 自述 | 实际核查 |
|------|---------|
| "textutil→HTML解析为结构化JSON(含章节)" | `srs_mineru_pipeline.py`产出的`structured.json`**丢失3.X章节结构**:doc01仅22节(缺3.4~3.18),导致R-005在**16/16文档全部误报** |
| "7个检测类型,每个有GJB条文支撑" | R-003的420条违规多为`'AD'`误报(实为"分析+演示"组合方法),R-004的202条幽灵需求因defined集合不完整而大量过报 |
| "phantom_requirement抽检准确率80%" | 无任何标注支撑此数字;phantom的defined集合依赖被破坏的章节结构,实际准确率远低于此 |
| "方向A已实现条目聚合" | `srs_context.py`的`aggregate_items`是**子串搜索+ID匹配**(`srs_context.py:305` `search_text in para.text`),非语义条目聚合 |
| "删除了param/version冲突(无标准支撑)" | 三层引擎`srs_detect.py:94`仍保留`param_value_conflict`;语义/逻辑层实际只在1份文档(doc03)跑通且仅4条语法违规 |

**三套并行的检测/上下文引擎**(职责重叠、数据源不同):

```
引擎1 (GJB规则):  srs_check_v3.py        ← 读 mineru_parsed/*_structured.json (16份)
引擎2 (三层):    srs_detect.py + srs_context.py + srs_tool.py  ← 读 srs_outline/*_content.xml (13份)
引擎3 (长上下文): srs_long_context.py(v1,读content.xml) / srs_long_context_v2.py(v2,读structured.json)
```

两套数据格式互不兼容,且**各自以不同方式损坏**:
- `structured.json`(16份):章节结构丢失(textutil不保留标题层级)→ R-005/R-006/R-004 全线误报
- `content.xml`(13份):章节去重失败(TOC+正文+表格交叉引用都算Section)→ duplicate_section 误报(doc03的3.1.1出现4次、3.7出现7次)

---

## 问题1: 解析流程该怎么标准化?

### 1.1 当前问题深入分析

存在**三条解析路径**,产出两种不兼容格式:

**路径A**(`srs_doc_batch_parse.py`): `.doc → textutil → HTML → markdown` → `parsed_srs_dataset/*.md`(16份)
**路径B**(`srs_mineru_pipeline.py`): `.doc → textutil → HTML → SRSHTMLParser → structured.json` → `mineru_parsed/*_structured.json`(16份)
**路径C**(`srs_to_xml.py`): `parsed_srs_dataset/*.md → markdown解析 → content.xml` → `srs_outline/*_content.xml`(13份)

**根因:textutil是根本瓶颈**。textutil是macOS的格式转换工具,**不保留Word的标题样式层级**(Heading 1/2/3)。它把所有标题转成普通段落,后续只能靠正则`^(\d+(?:\.\w+)*)\s+(.+)`(`srs_mineru_pipeline.py:94`)猜章节号。这导致:
- doc01的`structured.json`只有`['1','1.1',...,'3','3.1','3.2','3.3.1','3.11.1'...]`——3.4~3.18全部丢失
- 章节号正则无法区分"目录条目"与"正文标题",`content.xml`把两者都收为Section,造成重复

LibreOffice下载失败只是表象;**即使LibreOffice可用,textutil路径也该废弃**,因为它从源头就丢了标题层级这一SRS最关键的结构信息。

### 1.2 可行的改进方案

**方案1: LibreOffice headless(.doc→.docx)→ MinerU解析.docx**
- LibreOffice能保留标题样式、表格、OLE图片
- MinerU的office解析器`DocxConverter`内部正是调用LibreOffice做转换
- 难点:LibreOffice下载失败。解法:`brew install --cask libreoffice`(离线包约350MB)或拉官方docker镜像`linuxserver/libreoffice`
- 产出标准MinerU三件套:markdown + content_list.json + images/(含图片!)

**方案2: pandoc(.doc→.docx/.md)**
- `pandoc input.doc -o output.docx`(pandoc能直接读.doc?实际pandoc不直接支持.doc,需先转.docx)
- 仍需LibreOffice做.doc→.docx,pandoc只解决docx→md
- 不如方案1直接

**方案3: 保留textutil但加标题层级恢复**
- textutil转HTML后,用字体大小/加粗/字号启发式恢复标题层级
- 仍是启发式,不可靠;不推荐作为主路径

**方案4: antiword/catdoc直接抽.doc文本**
- 只能出纯文本,丢表格丢图片,不可接受

### 1.3 推荐方案及理由

**推荐方案1:LibreOffice headless + MinerU .docx解析**。

理由:
1. **标题层级是SRS的骨架**。GJB 438C的所有检测(R-005章节结构、R-004追溯、R-006接口ID)都依赖正确的章节树。textutil从源头破坏了它,任何下游修补都是徒劳——这正是当前668条违规被误报主导的根因。
2. MinerU已是项目既定工具(`~/mineru-env`),其`DocxConverter`封装了LibreOffice,产出标准content_list(含图片),与`references/DataFlow`的KB Cleaning Pipeline第一步一致。
3. 图片目前**全部丢失**(`srs_to_xml.py`只记Image节点的caption不存图),方案1是唯一能恢复图片的路径——而方向A的多模态关联必须有图。

LibreOffice安装问题的具体解法(按优先级):
- `brew install --cask libreoffice`(最稳)
- 若brew慢:用官方dmg镜像或`https://download.documentfoundation.org/libreoffice/stable/`
- 若需无GUI:docker `linuxserver/libreoffice` 提供headless转换
- 验证:`soffice --headless --convert-to docx input.doc`

### 1.4 实施步骤

1. 安装LibreOffice,验证`soffice --headless --convert-to docx`对16份.doc可用
2. 写`tools/srs_parse.py`(单一解析入口):`.doc → soffice → .docx → MinerU → unified IR`
3. **统一定义单一中间表示(IR)**(见第5节),废弃`structured.json`和`content.xml`两套格式
4. 对16份文档重跑解析,人工抽检3份(01/03/06)的章节树完整性(3.1~3.18是否齐全)
5. 解析质量门槛:章节树必须含3.1~3.18的连续编号,否则标记为解析失败而非静默丢失

---

## 问题2: 检测类型该怎么定义?

### 2.1 当前问题深入分析

当前有两套检测类型定义,且**误报率极高**:

**GJB规则引擎**(`srs_check_v3.py`)的7类,跨16份文档的实际分布:
```
R-003合格性: 420   ← 'AD'/'ADBD'等组合方法代码未处理,大量误报
R-004追溯:   202   ← phantom的defined集合依赖被破坏的章节结构,过报
R-006接口ID:  25   ← 接口章节未恢复,误报
R-005结构:    16   ← 16/16全部误报(章节解析丢失)
R-001标识:     2
R-007优先:     3
```

**具体误报机制**:
- **R-003**(`srs_check_v3.py:118`):`if method and not any(m in method for m in GJB_QUAL_METHODS)`——GJB合格性方法允许组合(如"分析、演示"=`AD`),但检查器把`AD`当整体字符串与`'分析'/'demonstration'`做子串匹配,匹配失败即报违规。420条几乎全是此类。
- **R-004 phantom**(`srs_check_v3.py:173-187`):`defined_3_2`只收`3.2.X`章节,但章节解析丢了3.4~3.18,于是合格性表里引用的3.4.X/3.5.X全部变成"幽灵"。这是**解析缺陷的下游放大**。
- **R-005**(`srs_check_v3.py:211`):`missing = [s for s in EXPECTED_3X if s not in found_3x]`——直接对比3.1~3.18,而解析丢失了大部分,16份全报。

**三层引擎**(`srs_detect.py`)的误报:
- **id_split**(`srs_tool.py:298-302`):`normalize_id`取ID前两段(`parts[0]+'-'+parts[1]`),把`PZXQ-GN-FWKFZC`(服务开发支撑)和`PZXQ-GN-FWBSGL`(服务部署管理)归为同一组报"ID分裂"。这俩是**不同需求共享项目前缀**,是正常的。这是把"同一实体的多个ID"误当成"共享前缀的多个ID"。
- **duplicate_section**(`srs_tool.py:279`):阈值`c >= 3`。但content.xml把目录、正文、表格交叉引用都收为Section,3.7在doc03出现7次实为正常引用,被判违规。

**被删除的param_value_conflict/version_conflict**:三层引擎`srs_detect.py:94`其实**仍保留了**`param_value_conflict`(与自述不符),但因为它只在doc03跑通且该文档语义层0条,形同虚设。逻辑层Z3(`srs_detect.py:151`)同理未真正产出结果。

### 2.2 可行的改进方案

**关于"7个GJB检测够不够"**:
- 7个GJB规则全是**语法层/结构层**检测(格式合规),不涉及语义/逻辑。作为"基线合规扫描"够用,但远不是一致性校验的全部。
- 一致性校验的核心价值在**语义层**(同参数不同值)和**逻辑层**(约束不可满足),这两层当前是空的。

**关于param/version冲突该不该加回**:
- **必须加回**,这正是方向B的核心。但当前实现(`srs_detect.py:94`)的问题是:依赖`_extract_param_name`(`srs_context.py:460`取约束前15字的最后2-8个中文字符)这种正则抽参,参数名提取不准,值比较必然噪声大。
- "无标准支撑"不成立:GJB 438C的3.2(能力需求)、3.10(适应性约束)、3.11(质量因素)条文要求参数约束**可追踪、可验证**,同参数跨节矛盾即违反"可验证"原则。文献支撑见ARTA/Femmer的requirement smells。

**关于ARTA的9类requirement smells**:
- ARTA(Femmer et al. 2017)的smell体系(ambiguous/tacit/complex等9类)是**语义级**的,与GJB的**结构级**规则正交,可叠加。但ARTA面向英文NL需求,GJB是中文+表格混合,需适配。
- 建议参考其**分类法**而非直接搬检测器:把smell映射到GJB条文,形成"标准条文×smell类型"的二维矩阵,每个格子定义一个检测器。

### 2.3 推荐方案及理由

**推荐:三层检测体系,按"可验证性"而非"标准条文"组织**:

| 层 | 检测类型 | 标准支撑 | 当前状态 | 优先级 |
|----|---------|---------|---------|--------|
| 语法层 | 章节结构/编号连续/ID格式 | GJB R-005/R-002 | 有但误报 | **先修解析** |
| 语法层 | 合格性方法合规 | GJB R-003 | 有,'AD'误报 | 修组合方法解析 |
| 语法层 | 追溯覆盖/幽灵需求 | GJB R-004 | 有,过报 | 修解析后重评 |
| 语义层 | 同参数跨节值矛盾 | GJB 3.2/3.11"可验证" | 删了又留,未跑通 | **用LLM抽参重建** |
| 语义层 | 正文↔表格值矛盾 | GJB"一致性"原则 | 无 | 新增,参考ProfiliTable |
| 语义层 | 版本/配置矛盾 | GJB 3.10 | 删了 | 加回,限定config类 |
| 逻辑层 | 约束不可满足(Z3) | 无直接条文 | 有框架未产出 | 限定数值约束 |
| 逻辑层 | 时间预算/容量超限 | 工程约束 | 有框架 | 限定明确场景 |

**理由**:
1. **先治误报再扩类型**。在R-005 100%误报的状态下新增类型只会让评测更不可信。优先级是:修复解析→修复R-003/R-004误报→再补语义/逻辑层。
2. param/version冲突必须加回,但**前提是参数提取从正则升级为LLM抽取**(见问题3)。正则抽参(`_extract_param_name`)是语义层做不起来的根本原因。
3. 不直接搬ARTA,而是借其分类法组织GJB检测,保持"每条检测可追溯到GJB条文"这一已建立的优点。

### 2.4 实施步骤

1. **修R-003**:合格性方法列先做归一化(去掉标点/空格,按字母拆分`AD`→`A,D`→`分析,演示`),再判是否属于5类
2. **修id_split**:取消"前两段归一化",改为"完整ID相同+名称embedding>0.9"才判分裂(分裂的真正定义是"同一需求被赋予了不同ID",需语义证据)
3. **修duplicate_section**:Section只从正文标题层级取(解析层保证),目录和表格交叉引用不入Section节点
4. 解析修复后重跑,统计R-005/R-004的真实违规数(预期大幅下降)
5. 新增语义层:LLM抽参→参数实体链接→跨节值比对(见问题3/4)

---

## 问题3: 方向A(上下文关联)的技术路线该怎么走?

### 3.1 当前问题深入分析

当前有三个上下文关联实现,本质都是**关键词搜索匹配**,不是"条目聚合":

**`srs_context.py:aggregate_items`(244-369)**:
- 聚合靠两件事:(1)子串搜索`search_text in para.text`(`:305`)(2)表格行里含`raw_id`(`:317`)
- embedding仅用于**合并**已识别实体(A4,阈值0.85),不用于**发现**关联
- "条目"退化为"以3.2.X章节标题为种子的搜索结果集合",没有真正的实体规范化

**`srs_long_context.py`(v1)**:倒排索引+embedding语义匹配,同样以章节名为种子

**`srs_long_context_v2.py`(v2)**:消费structured.json,但因structured.json章节丢失,种子本身残缺

**参数提取是硬伤**(`srs_context.py:460-465`):
```python
def _extract_param_name(text, constraint_pos):
    before = text[max(0, constraint_pos - 15):constraint_pos]  # 前15字
    m = re.search(r'([\u4e00-\u9fa5]{2,8})$', before)          # 取末2-8中文字
```
对"系统启动时间不超过5s",可能抽出"启动时间";对"在满载工况下数据获取延迟不超过200ms",15字窗口可能截到"况下数据获取延迟",抽出"获取延迟"——参数名失真。参数名错了,后续值比对、Z3求解全无意义。这是语义/逻辑层做不起来的**直接原因**。

### 3.2 可行的改进方案

**方案1: QA-GraphRAG的RAPTOR树**
- RAPTOR把文本递归摘要成树,不同层级聚合不同粒度的"同一事物"
- 优点:天然处理长程关联,MLP路由器按查询复杂度选层
- 缺点:RAPTOR是**摘要**而非**实体链接**。SRS要的不是"把3.2.1和合格性表的某行摘要到一起",而是"识别它们描述的是同一个参数'响应时间'"。RAPTOR的聚合粒度是主题级,不是实体级
- 适用:作为检索增强(给定一个参数,跨节找证据),不适合做主聚合

**方案2: DataMind的CONTRADICTS关系**
- DataMind在Recall后自动收集矛盾对(MemoryLinkKind.CONTRADICTS),用词法token-overlap召回
- 优点:直接面向矛盾检测
- 缺点:CONTRADICTS是**声明**关系(已知矛盾才链接),SRS要的是**检测**未知矛盾。引用README自己也指出"需把'声明矛盾'升级为'检测后声明矛盾'"。词法召回对中文+表格混合不够
- 适用:作为检测结果的关系存储模型,不是检测器本身

**方案3: 实体为中心的条目聚合(Entity-Centric Aggregation)**
- 定义"条目"=规范化的实体(参数/功能/接口/状态),每个条目聚合跨模态出现
- 实体规范化:LLM抽实体→规范化名(同义合并)→跨节链接
- 多模态:文字段、表格行、图片归属(图按章节归属+caption匹配)
- 这才是AGENTS.md里"条目={文字,图片,表格行,章节,语义角色}"的本意

**方案4: 知识图谱(DataFlow-KG三元组)**
- LLM抽三元组→建图→多跳推理找矛盾
- 优点:可做逻辑层推理
- 缺点:三元组抽取"宁缺毋滥",recall低;SRS表格数值用三元组表达别扭

### 3.3 推荐方案及理由

**推荐:方案3(实体为中心的条目聚合)为主干,方案1(RAPTOR)作检索增强,方案4(KG)留作逻辑层可选**。

理由:
1. **方向A的本质是实体链接,不是摘要**。RAPTOR摘要会丢失"参数名=响应时间"这种原子事实,而一致性校验恰恰要比较原子事实(响应时间在3.2.1是5s,在3.11是3s)。实体为中心才能保住原子。
2. 当前的"搜索匹配"缺的是**实体规范化**这一步——判断"3.2.1的响应时间"和"3.11的响应延时"是不是同一参数。这需要LLM做实体识别+同义归一,而非正则。
3. **参数提取必须从正则升级为LLM**。这是打通语义/逻辑层的关键。LLM抽`{param_name, value, unit, operator, section}`结构化输出,远比15字窗口正则可靠。
4. RAPTOR在"给定参数,跨节找所有证据"这一检索子任务上有价值,可作为聚合后的证据收集器,不作为主聚合。

**条目定义(建议)**:
```
Item = {
  canonical_name: str          # 规范化名,如"响应时间"
  item_type: parameter|function|interface|state
  aliases: [str]               # 别名,如["响应延时","响应延迟"]
  occurrences: [               # 跨模态出现
    {section, modality: text|table_row|image, content, role}
  ]
  features: [                  # 语义特征(仅parameter类)
    {value, unit, operator, role: threshold|config|capacity}
  ]
}
```

### 3.4 实施步骤

1. 写`tools/srs_extract.py`:LLM从每节抽实体(参数/功能/接口)+ 参数特征结构化输出(替换`_extract_param_name`)
2. 实体规范化:同义合并(响应时间/响应延时→响应时间),用embedding>0.9+LLM二次确认
3. 跨节链接:对每个规范化实体,扫描全文档收集occurrences(文字段+表格行+图片归属)
4. 图片关联:按章节归属+caption embedding匹配(图目前丢失,依赖问题1的解析修复)
5. 输出`items.json`作为方向B的输入
6. (可选)RAPTOR树作为辅助检索:对长文档按章节建摘要树,给定参数查询时定位证据

---

## 问题4: 没有Gold Standard怎么验证?

### 4.1 当前问题深入分析

- 16份真实文档**零人工标注**;668条违规无法验证真阳/假阳
- 旧Gold Standard(`data/gjb_438c/gold_standard/`)是3份**合成**SRS的22条标注(8真矛盾+14正值),与真实GJB文档分布不符
- `evaluation_results.json`存在但对应旧合成数据
- "phantom准确率80%"是无标注的自评,且phantom依赖被破坏的章节结构,该数字不可信

**核心矛盾**:要证明方法有效需要Gold Standard,但全量标注16份文档成本极高(每份几十~上百需求)。

### 4.2 可行的改进方案

**方案1: GJB标准条文作"弱Gold Standard"**
- 语法层检测(R-003/R-005等)可直接用GJB条文判定对错:章节缺没缺、方法合不合规是客观的
- 优点:零标注,条文本身就是ground truth
- 局限:只覆盖语法层;语义/逻辑层无条文可直接判对错

**方案2: LLM-as-Judge交叉验证**
- 用独立LLM对每条违规判"真矛盾/合理差异/误报"
- 优点:可全量跑;缺点:LLM对中文领域术语判断不稳,需人工抽检校准LLM

**方案3: 小规模人工标注(2-3份)+ 迁移**
- 选01(最大)、03(需求最多)、06(约束最多)三份做全标注
- 优点:可信;缺点:成本高,3份约需标注数百条

**方案4: 合成注入(Mutation-based)**
- 取一份"干净"文档,人工注入已知矛盾(改参数值/删章节/造幽灵需求),作为有标注测试集
- 优点:可控、可量化recall;缺点:合成矛盾分布可能与真实不符

**方案5: 旧Gold Standard适配**
- 把3份合成SRS的22条标注迁移到新IR格式,先在新管道上跑通评测闭环

### 4.3 推荐方案及理由

**推荐:分层验证策略(组合方案1+3+2+4)**:

| 检测层 | 验证方法 | 理由 |
|--------|---------|------|
| 语法层(GJB规则) | **方案1:GJB条文作硬Gold** | 章节缺没缺、方法合规否是客观的,条文即GT,零标注可验precision |
| 语义层(值矛盾) | **方案3:2-3份人工标注** | 真假矛盾需人判,但只需标少量文档;在这几份上算P/R/F1 |
| 语义层(其余文档) | **方案2:LLM-Judge** | 用方案3标注的文档校准LLM-Judge,再外推到其余13份 |
| 逻辑层(Z3) | **方案4:合成注入** | Z3的UNSAT是数学确定的,注入"A≤5且A≥10"可验recall |
| 全管道回归 | **方案5:旧Gold迁移** | 22条标注迁到新IR,保证管道迭代不退化 |

**理由**:
1. **GJB条文作弱Gold Standard是可行且应优先的**——这正是项目"每条检测有GJB条文支撑"设计的回报。语法层不需要人工标注。
2. 但**语义/逻辑层无法靠条文判对错**("响应时间5s vs 3s是不是矛盾"取决于是否同参数,条文管不了),必须有人工标注锚点。2-3份是精度与成本平衡。
3. LLM-Judge单独不可信,但**用人工标注校准后**可作为规模化的近似评测,这在RE领域有先例。

### 4.4 实施步骤

1. 语法层:对每条违规附GJB条文+可追溯的章节证据,人工只抽检10条确认条文判定无误
2. 选01/03/06三份,按"条目对"标注:每对标{一致/矛盾/无关},产出`gold_3docs.json`
3. 在这3份上算各检测器的P/R/F1,作为主指标
4. 用这3份校准LLM-Judge prompt,对其余13份跑LLM-Judge出近似P/R
5. 合成注入集:取一份文档复制,注入20条已知矛盾(值矛盾/幽灵/缺章),验recall
6. 迁移旧22条标注到新IR,作回归测试

---

## 问题5: 整体流水线该怎么组织?

### 5.1 当前问题深入分析

`tools/`下8个脚本,职责严重重叠:

| 脚本 | 数据源 | 职责 | 问题 |
|------|--------|------|------|
| `srs_doc_batch_parse.py` | .doc | →md | 路径A,丢标题层级 |
| `srs_mineru_pipeline.py` | .doc | →structured.json | 路径B,丢章节结构 |
| `srs_to_xml.py` | md | →content.xml | 路径C,章节重复 |
| `srs_check_v3.py` | structured.json | GJB 7规则 | 引擎1,误报主导 |
| `srs_context.py` | content.xml | 条目聚合 | 搜索匹配非聚合 |
| `srs_detect.py` | content.xml | 三层检测 | 引擎2,只1份跑通 |
| `srs_tool.py` | content.xml | 5个工具函数 | 被引擎2调用 |
| `srs_long_context.py` | content.xml | 关联+检测 | 引擎3v1,与2重叠 |
| `srs_long_context_v2.py` | structured.json | 关联+检测 | 引擎3v2,与1重叠 |

**核心乱象**:
1. 3个解析入口产出2种格式,2个检测引擎各读一种,2个长上下文版本各读一种——**数据格式未统一**是混乱的总根源
2. 引擎1(GJB规则)和引擎3v2都读structured.json但各自实现;引擎2和引擎3v1都读content.xml但各自实现——**重复实现**
3. `srs_context.py`的`Item`/`ItemFeature`与`srs_long_context_v2.py`的`ContextItem`是两套近似数据结构——**抽象未统一**

### 5.2 可行的改进方案

**方案1: DataFlow Core的Operator/Pipeline/Storage模式**
- Operator:单入单出`run()`,声明input_key/output_key
- Pipeline:compile时键校验,串联Operator
- Storage:step()自动管中间态,可断点续跑
- 优点:中间状态可追溯、可重跑;与`references/DataFlow`一致
- 缺点:对科研原型略重,但模式本身轻量

**方案2: 简单函数链**
- 一个main串调用parse→extract→detect→eval
- 优点:最简;缺点:无中间态管理,迭代难

**方案3: 保留多脚本但统一数据格式**
- 只统一IR,脚本仍分散
- 优点:改动小;缺点:重复实现仍在

### 5.3 推荐方案及理由

**推荐:方案1(DataFlow Operator模式),但只采用其抽象不引入框架依赖**。

理由:
1. **统一数据格式是第一要务**,Operator的input_key/output_key强制约束这点
2. step()机制对科研迭代价值大:改了检测器只需从detect步重跑,不必重跑解析
3. 项目已有`references/DataFlow`源码参考,且`method_design_v2.md`已规划此方向,延续性好
4. 不装open-dataflow框架,只借鉴模式(纯函数+dataclass),避免环境负担

### 5.4 实施步骤

1. 定义唯一IR(dataclass,见下节架构)
2. 每个阶段实现为`class XxxOperator` with `run(data)->data`
3. Pipeline用普通函数串联,每步落盘JSON(等同step)
4. 废弃`structured.json`和`content.xml`,只保留IR

---

## 完整Pipeline架构建议

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 0: PARSE  (srs_parse.py)                             │
│  .doc ──soffice──► .docx ──MinerU──► IR(章节树+表格+图片)    │
│  输出: data/ir/<doc>.json  (唯一中间表示)                    │
│  门槛: 章节树含3.1~3.18连续编号,否则标解析失败               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  Stage 1: EXTRACT  (srs_extract.py, 方向A-实体)              │
│  LLM抽: 实体(参数/功能/接口) + 参数特征(value/unit/op/role)  │
│  实体规范化: 同义合并(embedding>0.9 + LLM确认)               │
│  输出: data/items/<doc>.json  (List[Item])                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  Stage 2: AGGREGATE  (srs_aggregate.py, 方向A-聚合)          │
│  跨节链接: 每个Item收集occurrences(text/table_row/image)     │
│  图片关联: 章节归属 + caption embedding                       │
│  (可选) RAPTOR摘要树: 辅助证据检索                            │
│  输出: 更新items.json (含完整occurrences)                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  Stage 3: DETECT  (srs_detect.py, 方向B-三层)                │
│  ┌─语法层─ GJB规则(R-001~R-007),条文可追溯,作弱Gold         │
│  │        修R-003组合方法/修id_split/修duplicate             │
│  ├─语义层─ 同参数跨节值矛盾 | 正文↔表格矛盾 | 版本矛盾        │
│  │        基于Item.features做值比对(ProfiliTable式Evaluator) │
│  └─逻辑层─ Z3约束UNSAT | 时间预算超限 | 容量超限              │
│  输出: data/detections/<doc>.json                            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  Stage 4: EVALUATE  (srs_eval.py)                            │
│  语法层: GJB条文作硬Gold(零标注验precision)                  │
│  语义层: 3份人工标注(01/03/06)算P/R/F1                       │
│  逻辑层: 合成注入验recall                                    │
│  其余: LLM-Judge(用3份校准)出近似P/R                         │
│  回归: 旧22条标注迁到新IR                                    │
│  输出: data/eval/summary.json                                │
└─────────────────────────────────────────────────────────────┘
```

**统一IR定义**(替代structured.json + content.xml):
```python
@dataclass
class Section:
    section_id: str          # "3.2.1"
    title: str
    level: int               # 标题层级(解析层保证)
    parent: str
    text: str
    req_id: str = ""

@dataclass
class Table:
    table_id: str
    section: str
    type: str                # qualification/traceability/interface/...
    headers: list[str]
    rows: list[list[str]]

@dataclass
class Image:
    image_id: str
    section: str
    caption: str
    path: str                # 图片文件(解析层恢复)

@dataclass
class SRSDocument:           # 唯一IR
    doc_id: str
    sections: list[Section]
    tables: list[Table]
    images: list[Image]
```

**脚本精简对照**(8→5):
| 保留 | 替代/废弃 |
|------|----------|
| `srs_parse.py`(新) | 替代 srs_doc_batch_parse + srs_mineru_pipeline + srs_to_xml |
| `srs_extract.py`(新,LLM抽实体) | 替代 srs_context 的正则抽参 |
| `srs_aggregate.py`(新,跨节链接) | 替代 srs_long_context v1/v2 |
| `srs_detect.py`(重构,三层) | 整合 srs_check_v3 + srs_detect + srs_tool |
| `srs_eval.py`(新,分层评测) | 新增 |

---

## 优先级排序(执行顺序)

| 优先级 | 任务 | 阻塞关系 |
|--------|------|---------|
| **P0** | 修解析:LibreOffice+MinerU,统一IR | 阻塞一切下游可信度 |
| **P0** | 修R-003/R-004/R-005/id_split误报 | 依赖P0解析 |
| P1 | LLM参数抽取替换正则(打通语义层) | 依赖P0 IR |
| P1 | 实体为中心的条目聚合(方向A主干) | 依赖LLM抽取 |
| P1 | 3份人工标注Gold Standard | 可与P1并行 |
| P2 | 语义层值矛盾检测(ProfiliTable式) | 依赖条目聚合 |
| P2 | 分层评测框架 | 依赖Gold |
| P3 | 逻辑层Z3 + 合成注入评测 | 依赖语义层 |
| P3 | RAPTOR辅助检索(可选增强) | 非阻塞 |

**核心判断:当前项目处于"解析层错误被下游放大"的失真状态。在P0修复前,所有检测指标(668条违规)都不可作为科研成果引用。修复解析→消除误报→再建语义层,是恢复科研可信度的唯一路径。**
