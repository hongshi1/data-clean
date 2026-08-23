# Tier 1 Drift候选人工裁决包

> 共86条 (按类型×优先级分层抽样, seed=42)

## 裁决标签体系
- `real_bug` — 真实文档不一致(图/表矛盾)
- `benign_variation` — 合理差异(粒度/详略/同义改写)
- `compiler_bug` — 比对引擎误报(匹配/编译缺陷)
- `extraction_error` — 锚点提取错误(Visio解析问题)

---


## ORDER_CONFLICT (3条)

### 2_001_05 [ORDER_CONFLICT] 开发工程生成
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.1.1 | 图 7开发工程流程图 vs 表4 开发工程生成用例描述
- 规模: 表步骤3 ↔ 图节点6 已配3 (匹配度0.857)
- 证据: 表格步骤3在4之前, 但图中边方向相反
- 表侧: `{"seq": "3→4"}`
- 图侧: `{"edge": "s4→s3"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_008_06 [ORDER_CONFLICT] 配置信息解析
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.2.2 | 图 16配置信息解析流程图 vs 表12 配置信息解析描述
- 规模: 表步骤10 ↔ 图节点5 已配5 (匹配度0.667)
- 证据: 表格步骤7在8之前, 但图中边方向相反
- 表侧: `{"seq": "7→8"}`
- 图侧: `{"edge": "s8→s7"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_041_05 [ORDER_CONFLICT] 数据插入
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.2.1 | 图 28数据插入流程图 vs 表28 数据插入用例描述
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度0.667)
- 证据: 表格步骤3在4之前, 但图中边方向相反
- 表侧: `{"seq": "3→4"}`
- 图侧: `{"edge": "s4→s3"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error


## UC_NAME_MISMATCH (3条)

### 2_087_00 [UC_NAME_MISMATCH] 文电接收
- 位置: 12文电处理需求规格说明-终端 3.2.2.3 | 图 10 文电接收的流程图 vs 表 10 文电接收用例描述
- 规模: 表步骤0 ↔ 图节点2 已配0 (匹配度0.6)
- 证据: 表格UC名「文电接收」与图中用例节点不匹配(best=0.00)
- 表侧: `{"text": "文电接收"}`
- 图侧: `{"usecase_texts": ["网络资源定位", "文电收发与管理"]}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_088_00 [UC_NAME_MISMATCH] 用户管理
- 位置: 12文电处理需求规格说明-终端 3.2.2.4 | 图 11  用户管理的流程图 vs 表 11 用户管理用例描述
- 规模: 表步骤0 ↔ 图节点3 已配0 (匹配度0.5)
- 证据: 表格UC名「用户管理」与图中用例节点不匹配(best=0.00)
- 表侧: `{"text": "用户管理"}`
- 图侧: `{"usecase_texts": ["名录访问", "名录管理", "名录影像"]}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_083_00 [UC_NAME_MISMATCH] 名录管理
- 位置: 12文电处理需求规格说明-终端 3.2.1.3 | 图 5  名录管理流程图 vs 表 6 名录管理用例描述
- 规模: 表步骤0 ↔ 图节点8 已配0 (匹配度0.333)
- 证据: 表格UC名「名录管理」与图中用例节点不匹配(best=0.00)
- 表侧: `{"text": "名录管理"}`
- 图侧: `{"usecase_texts": ["用户登录和退出", "文电接收", "文电发送", "用户管理", "信息统计", "信息查询和管理", "通信录查询和管理", "轻量级部署"]}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error


## EXC_MISSING (20条)

### 2_016_04 [EXC_MISSING] 布局控制
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.1 | 图 26开发工程流程图 vs 表21 布局控制用例描述
- 规模: 表步骤1 ↔ 图节点4 已配1 (匹配度1.0)
- 证据: 表格异常流E1「切换布局失败则进入异常E1，用例失败。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "切换布局失败则进入异常E1，用例失败。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_018_03 [EXC_MISSING] 主题管理
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.3 | 图 28主题管理流程图 vs 表23 主题管理用例描述
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度1.0)
- 证据: 表格异常流E1「切换主题失败，用例失败。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "切换主题失败，用例失败。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_019_03 [EXC_MISSING] 快捷操控
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.4 | 图 29快捷操控流程图 vs 表24 快捷操控用例描述
- 规模: 表步骤3 ↔ 图节点5 已配3 (匹配度1.0)
- 证据: 表格异常流E1「快捷键设置冲突 请重新设置。 异常流E2：快捷键设置错误 请…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "快捷键设置冲突 请重新设置。 异常流E2：快捷键设置错误 请重新设置。 异常流E3：快捷键无效 请跳转对应页,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_024_05 [EXC_MISSING] 读取配置文件连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.2 | 图 6读取配置文件连接流程图 vs 
- 规模: 表步骤3 ↔ 图节点7 已配3 (匹配度1.0)
- 证据: 表格异常流E1「系统提示连接失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示连接失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_025_05 [EXC_MISSING] 数据库连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.3 | 图7数据库连接流程图 vs 
- 规模: 表步骤2 ↔ 图节点6 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示连接失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示连接失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_026_05 [EXC_MISSING] 删除数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.1 | 图 10删除数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示删除数据库记录错误，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示删除数据库记录错误，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_027_05 [EXC_MISSING] 增加数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.2 | 图 11增加数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示执行失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示执行失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_028_05 [EXC_MISSING] 修改数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.3 | 图 12修改数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示提交失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示提交失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_029_05 [EXC_MISSING] 数据查询
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.3.1.1 | 图 14数据查询流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示查询失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示查询失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_031_03 [EXC_MISSING] 二维数组输出
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.3.1.3 | 图 16二维数组输出流程图 vs 
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示获取失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示获取失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_032_02 [EXC_MISSING] JSON输出
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.3.1.4 | 图 17 JSON输出流程图 vs 
- 规模: 表步骤2 ↔ 图节点3 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示获取失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示获取失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_036_03 [EXC_MISSING] 获取FLOAT
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.3.1.8 | 图 21获取FLOAT流程图 vs 
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示获取失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示获取失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_038_05 [EXC_MISSING] Blob数据插入
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.4.1.1 | 图 24 BLOB数据插入流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示BLOB数据插入失败，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示BLOB数据插入失败，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_060_05 [EXC_MISSING] 数据字典文件导出
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.2.6 | 图22 数据元素查询流程图 vs 表30 数据元素查询用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格异常流E1「系统给出提示信息，用户根据提示信息继续执行。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统给出提示信息，用户根据提示信息继续执行。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_040_04 [EXC_MISSING] Blob数据查询
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.4.1.3 | 图 26 BLOB数据查询流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格异常流E1「系统提示初始化，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示初始化，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_076_03 [EXC_MISSING] 删除报文类型
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.6 | 图42 删除报文功能域流程图 vs 表49 删除报文类型用例描述
- 规模: 表步骤5 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格异常流E1「无。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "无。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_071_04 [EXC_MISSING] 增加条件语句
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图36增加条件语句流程图 vs 表44 增加条件语句用例描述
- 规模: 表步骤6 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格异常流E1「系统给出提示信息，用户根据提示信息继续执行。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统给出提示信息，用户根据提示信息继续执行。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_070_03 [EXC_MISSING] 调整数据项顺序
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图35调整数据项顺序流程图 vs 表43 调整数据项顺序用例描述
- 规模: 表步骤7 ↔ 图节点8 已配7 (匹配度1.0)
- 证据: 表格异常流E1「系统给出提示信息，用户根据提示信息继续执行。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统给出提示信息，用户根据提示信息继续执行。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_061_03 [EXC_MISSING] 用户数据结构导出
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.1 | 图24 用户数据结构导出流程图 vs 表32 用户数据结构导出用例描述
- 规模: 表步骤4 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格异常流E1「系统给出提示信息，用户根据提示信息继续执行。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统给出提示信息，用户根据提示信息继续执行。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_053_04 [EXC_MISSING] 释放句柄
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.5.5 | 图 43释放句柄流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度0.7)
- 证据: 表格异常流E1「系统提示初始化，用例结束。,,…」在图中无分支表示
- 表侧: `{"eid": "E1", "text": "系统提示初始化，用例结束。,,"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error


## STEP_MISSING (20条)

### 2_056_00 [STEP_MISSING] 应用软件注册
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.1.1 | 图6 应用注册流程图 vs 表4 应用软件注册用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤5「系统加载字典数据…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "系统加载字典数据"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_056_01 [STEP_MISSING] 应用软件注册
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.1.1 | 图6 应用注册流程图 vs 表4 应用软件注册用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤8「应用软件获得注册成功信息。2．系统将检测注册标识的合法性…」在图中无匹配节点
- 表侧: `{"id": "s8", "text": "应用软件获得注册成功信息。2．系统将检测注册标识的合法性"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_059_00 [STEP_MISSING] 数据字典文件导出
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.2.5 | 图21 数据字典文件导出流程图 vs 表29 数据字典文件导出用例描述
- 规模: 表步骤6 ↔ 图节点5 已配5 (匹配度1.0)
- 证据: 表格步骤132「系统确认导出操作…」在图中无匹配节点
- 表侧: `{"id": "s132", "text": "系统确认导出操作"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_060_00 [STEP_MISSING] 数据字典文件导出
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.2.6 | 图22 数据元素查询流程图 vs 表30 数据元素查询用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤3「数据库提供字典数据…」在图中无匹配节点
- 表侧: `{"id": "s3", "text": "数据库提供字典数据"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_060_01 [STEP_MISSING] 数据字典文件导出
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.2.6 | 图22 数据元素查询流程图 vs 表30 数据元素查询用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤5「用户查看数据元素…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "用户查看数据元素"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_063_00 [STEP_MISSING] 模板脚本文件导入
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.3 | 图26 报文脚本文件导入流程图 vs 表34 报文脚本文件导入用例描述
- 规模: 表步骤6 ↔ 图节点5 已配5 (匹配度1.0)
- 证据: 表格步骤5「系统连接模板数据文件导出顺序固定…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "系统连接模板数据文件导出顺序固定"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_068_00 [STEP_MISSING] 增加数据项
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图33增加数据项流程图 vs 表41 增加数据项用例描述
- 规模: 表步骤6 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格步骤5「系统完成报文字段校验输入参数的合法性…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "系统完成报文字段校验输入参数的合法性"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_068_01 [STEP_MISSING] 增加数据项
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图33增加数据项流程图 vs 表41 增加数据项用例描述
- 规模: 表步骤6 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格步骤6「用户得到新的报文模板…」在图中无匹配节点
- 表侧: `{"id": "s6", "text": "用户得到新的报文模板"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_069_00 [STEP_MISSING] 删除数据项
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图34删除数据项流程图 vs 表42 删除数据项用例描述
- 规模: 表步骤5 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格步骤5「用户得到报文模板…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "用户得到报文模板"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_071_00 [STEP_MISSING] 增加条件语句
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图36增加条件语句流程图 vs 表44 增加条件语句用例描述
- 规模: 表步骤6 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格步骤5「系统完成报文校验输入参数的合法性…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "系统完成报文校验输入参数的合法性"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_071_01 [STEP_MISSING] 增加条件语句
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图36增加条件语句流程图 vs 表44 增加条件语句用例描述
- 规模: 表步骤6 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格步骤6「用户得到新的报文模板…」在图中无匹配节点
- 表侧: `{"id": "s6", "text": "用户得到新的报文模板"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_075_00 [STEP_MISSING] 删除报文类型
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.6 | 图41 删除报文类型流程图 vs 表49 删除报文类型用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤4「数据库更新数据…」在图中无匹配节点
- 表侧: `{"id": "s4", "text": "数据库更新数据"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_075_01 [STEP_MISSING] 删除报文类型
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.6 | 图41 删除报文类型流程图 vs 表49 删除报文类型用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤5「系统完成报文类型删除…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "系统完成报文类型删除"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_081_00 [STEP_MISSING] 数据资源目录展现
- 位置: 09数据同步共享服务软件需求规格说明-终稿 3.2.3.1 | 图 28 数据资源目录展现流程图 vs 表 39数据资源目录展现用例描述
- 规模: 表步骤4 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤3「获取所有主题名称…」在图中无匹配节点
- 表侧: `{"id": "s3", "text": "获取所有主题名称"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_080_01 [STEP_MISSING] 主题订阅
- 位置: 09数据同步共享服务软件需求规格说明-终稿 3.2.2.3 | 图 26 主题订阅流程图 vs 表 37主题订阅用例描述
- 规模: 表步骤5 ↔ 图节点3 已配3 (匹配度1.0)
- 证据: 表格步骤5「系统发送get请求…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "系统发送get请求"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_079_00 [STEP_MISSING] 数据发布
- 位置: 09数据同步共享服务软件需求规格说明-终稿 3.2.2.2 | 图 25 数据发送流程图 vs 表 36数据发布用例描述
- 规模: 表步骤4 ↔ 图节点2 已配2 (匹配度1.0)
- 证据: 表格步骤4「系统根据是否进行数据缓存…」在图中无匹配节点
- 表侧: `{"id": "s4", "text": "系统根据是否进行数据缓存"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_076_00 [STEP_MISSING] 删除报文类型
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.6 | 图42 删除报文功能域流程图 vs 表49 删除报文类型用例描述
- 规模: 表步骤5 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格步骤5「系统完成报文类型删除…」在图中无匹配节点
- 表侧: `{"id": "s5", "text": "系统完成报文类型删除"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_012_01 [STEP_MISSING] 故障隔离检测
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.2.6 | 图 20故障隔离检测流程图 vs 表16 故障隔离检测用例描述
- 规模: 表步骤12 ↔ 图节点9 已配9 (匹配度0.667)
- 证据: 表格步骤14「用户打开浏览器…」在图中无匹配节点
- 表侧: `{"id": "s14", "text": "用户打开浏览器"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_008_04 [STEP_MISSING] 配置信息解析
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.2.2 | 图 16配置信息解析流程图 vs 表12 配置信息解析描述
- 规模: 表步骤10 ↔ 图节点5 已配5 (匹配度0.667)
- 证据: 表格步骤14「用户重新刷新主页面。 15.界面集成框架将底部、右侧缩略显控…」在图中无匹配节点
- 表侧: `{"id": "s14", "text": "用户重新刷新主页面。 15.界面集成框架将底部、右侧缩略显控组件默认加载出来"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_009_03 [STEP_MISSING] 组件集成
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.2.3 | 图 17组件集成流程图 vs 表13 组件集成用例描述
- 规模: 表步骤10 ↔ 图节点5 已配5 (匹配度0.667)
- 证据: 表格步骤12「用户配置一个底部缩略显控的组件…」在图中无匹配节点
- 表侧: `{"id": "s12", "text": "用户配置一个底部缩略显控的组件"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error


## ACTOR_MISSING (20条)

### 2_016_03 [ACTOR_MISSING] 布局控制
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.1 | 图 26开发工程流程图 vs 表21 布局控制用例描述
- 规模: 表步骤1 ↔ 图节点4 已配1 (匹配度1.0)
- 证据: 表格Actor「开发人员」在图中无参与者节点
- 表侧: `{"text": "开发人员"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_018_02 [ACTOR_MISSING] 主题管理
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.3 | 图 28主题管理流程图 vs 表23 主题管理用例描述
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度1.0)
- 证据: 表格Actor「开发人员」在图中无参与者节点
- 表侧: `{"text": "开发人员"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_019_02 [ACTOR_MISSING] 快捷操控
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.4 | 图 29快捷操控流程图 vs 表24 快捷操控用例描述
- 规模: 表步骤3 ↔ 图节点5 已配3 (匹配度1.0)
- 证据: 表格Actor「开发人员」在图中无参与者节点
- 表侧: `{"text": "开发人员"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_024_04 [ACTOR_MISSING] 读取配置文件连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.2 | 图 6读取配置文件连接流程图 vs 
- 规模: 表步骤3 ↔ 图节点7 已配3 (匹配度1.0)
- 证据: 表格Actor「应用软件」在图中无参与者节点
- 表侧: `{"text": "应用软件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_025_04 [ACTOR_MISSING] 数据库连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.3 | 图7数据库连接流程图 vs 
- 规模: 表步骤2 ↔ 图节点6 已配2 (匹配度1.0)
- 证据: 表格Actor「应用软件」在图中无参与者节点
- 表侧: `{"text": "应用软件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_026_03 [ACTOR_MISSING] 删除数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.1 | 图 10删除数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「应用软件」在图中无参与者节点
- 表侧: `{"text": "应用软件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_026_04 [ACTOR_MISSING] 删除数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.1 | 图 10删除数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「数据库」在图中无参与者节点
- 表侧: `{"text": "数据库"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_027_03 [ACTOR_MISSING] 增加数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.2 | 图 11增加数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「应用软件」在图中无参与者节点
- 表侧: `{"text": "应用软件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_027_04 [ACTOR_MISSING] 增加数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.2 | 图 11增加数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「数据库」在图中无参与者节点
- 表侧: `{"text": "数据库"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_028_03 [ACTOR_MISSING] 修改数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.3 | 图 12修改数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「应用软件」在图中无参与者节点
- 表侧: `{"text": "应用软件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_028_04 [ACTOR_MISSING] 修改数据记录
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.2.1.3 | 图 12修改数据记录流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「数据库」在图中无参与者节点
- 表侧: `{"text": "数据库"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_029_03 [ACTOR_MISSING] 数据查询
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.3.1.1 | 图 14数据查询流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「应用软件」在图中无参与者节点
- 表侧: `{"text": "应用软件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_029_04 [ACTOR_MISSING] 数据查询
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.3.1.1 | 图 14数据查询流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度1.0)
- 证据: 表格Actor「数据库」在图中无参与者节点
- 表侧: `{"text": "数据库"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_063_02 [ACTOR_MISSING] 模板脚本文件导入
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.3 | 图26 报文脚本文件导入流程图 vs 表34 报文脚本文件导入用例描述
- 规模: 表步骤6 ↔ 图节点5 已配5 (匹配度1.0)
- 证据: 表格Actor「数据库」在图中无参与者节点
- 表侧: `{"text": "数据库"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_064_00 [ACTOR_MISSING] 报文类型新增
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.4 | 图28 报文类型新增流程图 vs 表36 报文类型新增用例描述
- 规模: 表步骤6 ↔ 图节点6 已配6 (匹配度1.0)
- 证据: 表格Actor「用户」在图中无参与者节点
- 表侧: `{"text": "用户"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_036_02 [ACTOR_MISSING] 获取FLOAT
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.3.1.8 | 图 21获取FLOAT流程图 vs 
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度1.0)
- 证据: 表格Actor「应用软件」在图中无参与者节点
- 表侧: `{"text": "应用软件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_061_02 [ACTOR_MISSING] 用户数据结构导出
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.1 | 图24 用户数据结构导出流程图 vs 表32 用户数据结构导出用例描述
- 规模: 表步骤4 ↔ 图节点4 已配4 (匹配度1.0)
- 证据: 表格Actor「报文头文件」在图中无参与者节点
- 表侧: `{"text": "报文头文件"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_065_02 [ACTOR_MISSING] 报文功能域新增
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.4 | 图29 报文功能域新增流程图 vs 表37 报文功能域新增用例描述
- 规模: 表步骤6 ↔ 图节点7 已配6 (匹配度0.833)
- 证据: 表格Actor「数据库」在图中无参与者节点
- 表侧: `{"text": "数据库"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_073_01 [ACTOR_MISSING] 删除条件语句
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图38删除条件语句流程图 vs 表46 删除条件语句用例描述
- 规模: 表步骤5 ↔ 图节点4 已配4 (匹配度0.8)
- 证据: 表格Actor「用户」在图中无参与者节点
- 表侧: `{"text": "用户"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_017_03 [ACTOR_MISSING] 分屏管理
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.2 | 图 27分屏管理流程图 vs 表22 分屏管理用例描述
- 规模: 表步骤3 ↔ 图节点6 已配3 (匹配度0.8)
- 证据: 表格Actor「开发人员」在图中无参与者节点
- 表侧: `{"text": "开发人员"}`
- 图侧: `{"actor_texts": []}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error


## DIAGRAM_EXTRA (20条)

### 2_016_00 [DIAGRAM_EXTRA] 布局控制
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.1 | 图 26开发工程流程图 vs 表21 布局控制用例描述
- 规模: 表步骤1 ↔ 图节点4 已配1 (匹配度1.0)
- 证据: 图节点「布局风格切换…」(state)在表格中无对应步骤
- 图侧: `{"id": "5664", "text": "布局风格切换", "type": "state"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_016_01 [DIAGRAM_EXTRA] 布局控制
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.1 | 图 26开发工程流程图 vs 表21 布局控制用例描述
- 规模: 表步骤1 ↔ 图节点4 已配1 (匹配度1.0)
- 证据: 图节点「点击顶部菜单栏的
系统设置…」(state)在表格中无对应步骤
- 图侧: `{"id": "5668", "text": "点击顶部菜单栏的\n系统设置", "type": "state"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_016_02 [DIAGRAM_EXTRA] 布局控制
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.1 | 图 26开发工程流程图 vs 表21 布局控制用例描述
- 规模: 表步骤1 ↔ 图节点4 已配1 (匹配度1.0)
- 证据: 图节点「打开配置界面，提供
风格布局…」(state)在表格中无对应步骤
- 图侧: `{"id": "5683", "text": "打开配置界面，提供\n风格布局", "type": "state"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_018_00 [DIAGRAM_EXTRA] 主题管理
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.3 | 图 28主题管理流程图 vs 表23 主题管理用例描述
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度1.0)
- 证据: 图节点「点击顶部菜单栏的
系统设置…」(state)在表格中无对应步骤
- 图侧: `{"id": "5750", "text": "点击顶部菜单栏的\n系统设置", "type": "state"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_018_01 [DIAGRAM_EXTRA] 主题管理
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.3 | 图 28主题管理流程图 vs 表23 主题管理用例描述
- 规模: 表步骤2 ↔ 图节点4 已配2 (匹配度1.0)
- 证据: 图节点「主题风格应用
当前框架…」(state)在表格中无对应步骤
- 图侧: `{"id": "5755", "text": "主题风格应用\n当前框架", "type": "state"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_019_00 [DIAGRAM_EXTRA] 快捷操控
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.4 | 图 29快捷操控流程图 vs 表24 快捷操控用例描述
- 规模: 表步骤3 ↔ 图节点5 已配3 (匹配度1.0)
- 证据: 图节点「点击顶部菜单栏的
系统设置…」(state)在表格中无对应步骤
- 图侧: `{"id": "5773", "text": "点击顶部菜单栏的\n系统设置", "type": "state"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_019_01 [DIAGRAM_EXTRA] 快捷操控
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.3.4 | 图 29快捷操控流程图 vs 表24 快捷操控用例描述
- 规模: 表步骤3 ↔ 图节点5 已配3 (匹配度1.0)
- 证据: 图节点「打开配置界面，
提供快捷键修改
、保存…」(state)在表格中无对应步骤
- 图侧: `{"id": "5783", "text": "打开配置界面，\n提供快捷键修改\n、保存", "type": "state"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_024_00 [DIAGRAM_EXTRA] 读取配置文件连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.2 | 图 6读取配置文件连接流程图 vs 
- 规模: 表步骤3 ↔ 图节点7 已配3 (匹配度1.0)
- 证据: 图节点「传入配置文件路径…」(other)在表格中无对应步骤
- 图侧: `{"id": "533", "text": "传入配置文件路径", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_024_01 [DIAGRAM_EXTRA] 读取配置文件连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.2 | 图 6读取配置文件连接流程图 vs 
- 规模: 表步骤3 ↔ 图节点7 已配3 (匹配度1.0)
- 证据: 图节点「判断连接模式…」(gateway)在表格中无对应步骤
- 图侧: `{"id": "306", "text": "判断连接模式", "type": "gateway"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_024_02 [DIAGRAM_EXTRA] 读取配置文件连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.2 | 图 6读取配置文件连接流程图 vs 
- 规模: 表步骤3 ↔ 图节点7 已配3 (匹配度1.0)
- 证据: 图节点「连接服务器上的达梦数据库…」(other)在表格中无对应步骤
- 图侧: `{"id": "535", "text": "连接服务器上的达梦数据库", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_024_03 [DIAGRAM_EXTRA] 读取配置文件连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.2 | 图 6读取配置文件连接流程图 vs 
- 规模: 表步骤3 ↔ 图节点7 已配3 (匹配度1.0)
- 证据: 图节点「连接本地的sqlite3数据库…」(other)在表格中无对应步骤
- 图侧: `{"id": "539", "text": "连接本地的sqlite3数据库", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_025_00 [DIAGRAM_EXTRA] 数据库连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.3 | 图7数据库连接流程图 vs 
- 规模: 表步骤2 ↔ 图节点6 已配2 (匹配度1.0)
- 证据: 图节点「调用通过配置文件连接接口…」(process)在表格中无对应步骤
- 图侧: `{"id": "532", "text": "调用通过配置文件连接接口", "type": "process"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_025_01 [DIAGRAM_EXTRA] 数据库连接
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.1.1.1.3 | 图7数据库连接流程图 vs 
- 规模: 表步骤2 ↔ 图节点6 已配2 (匹配度1.0)
- 证据: 图节点「判断连接模式…」(gateway)在表格中无对应步骤
- 图侧: `{"id": "306", "text": "判断连接模式", "type": "gateway"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_046_02 [DIAGRAM_EXTRA] 缓存更新
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.3.2 | 图 34缓存更新流程图 vs 表34 缓存更新用例描述
- 规模: 表步骤3 ↔ 图节点8 已配3 (匹配度0.875)
- 证据: 图节点「遍历修改标志为失效…」(other)在表格中无对应步骤
- 图侧: `{"id": "496", "text": "遍历修改标志为失效", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_004_00 [DIAGRAM_EXTRA] 组件下载管理
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.1.4 | 图 10组件下载管理流程图 vs 表7 组件下载管理用例描述
- 规模: 表步骤5 ↔ 图节点10 已配5 (匹配度0.8)
- 证据: 图节点「上传…」(gateway)在表格中无对应步骤
- 图侧: `{"id": "3527", "text": "上传", "type": "gateway"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_053_01 [DIAGRAM_EXTRA] 释放句柄
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.5.5 | 图 43释放句柄流程图 vs 
- 规模: 表步骤2 ↔ 图节点5 已配2 (匹配度0.7)
- 证据: 图节点「输入相关参数…」(other)在表格中无对应步骤
- 图侧: `{"id": "1052", "text": "输入相关参数", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_047_05 [DIAGRAM_EXTRA] 模型制作
- 位置: 04数据统一访问服务软件需求规格说明-终稿 3.2.4.1 | 图 36代码生成流程图 vs 表37 模型制作用例描述
- 规模: 表步骤3 ↔ 图节点13 已配3 (匹配度0.684)
- 证据: 图节点「模型中是否有
重复字段…」(gateway)在表格中无对应步骤
- 图侧: `{"id": "701", "text": "模型中是否有\n重复字段", "type": "gateway"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_074_00 [DIAGRAM_EXTRA] 验证条件语句
- 位置: 07报文处理服务软件需求规格说明-终稿 3.2.3.5 | 图39验证条件语句流程图 vs 表47 验证条件语句用例描述
- 规模: 表步骤5 ↔ 图节点7 已配5 (匹配度0.636)
- 证据: 图节点「否…」(other)在表格中无对应步骤
- 图侧: `{"id": "1410", "text": "否", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_084_00 [DIAGRAM_EXTRA] 用户登录和退出
- 位置: 12文电处理需求规格说明-终端 3.2.2.1 | 图 7 用户登录的流程图 vs 表 8 用户登录和退出用例描述
- 规模: 表步骤3 ↔ 图节点5 已配3 (匹配度0.5)
- 证据: 图节点「1…」(other)在表格中无对应步骤
- 图侧: `{"id": "648", "text": "1", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error

### 2_022_10 [DIAGRAM_EXTRA] 语音交互
- 位置: 02界面集成框架软件需求规格说明-终稿 1.8.5.5 | 图 41语音交互流程图 vs 表48 组件打包发布用例描述
- 规模: 表步骤8 ↔ 图节点20 已配8 (匹配度0.333)
- 证据: 图节点「是…」(other)在表格中无对应步骤
- 图侧: `{"id": "7574", "text": "是", "type": "other"}`
- 裁决: [ ] real_bug [ ] benign_variation [ ] compiler_bug [ ] extraction_error
