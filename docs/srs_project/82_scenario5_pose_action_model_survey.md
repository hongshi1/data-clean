# 场景5：人体姿态、属性序列与动作时序模型调研

> 2026-11-04 | 范围：睡岗、离岗、摔倒、搬运/区域行为 | 仅调研，不下载、不运行模型
>
> 结论口径：下列指标是论文或官方模型库在其公开基准上的结果，不代表科研生产现场监控域性能，也不构成统一条件下的横向排名。权重大小因仓库未总是公布文件字节数，标为按参数量估算的量级，实际需以下载页面/文件头确认。

## 1. 结论摘要

1. **睡岗不能由单帧姿态分类器可靠判定。** 公开人体姿态集监督的是关键点，公开视频动作集监督的是有限的剪辑级动作类别；没有找到覆盖“值守岗位、长时间静止且属于睡岗”的直接公开监督集。模型可以识别“人/人体框、关键点、趴伏或低头等可见姿态、给定视频窗中的动作相似性”，不能仅凭静止证明睡眠、故意怠工或岗位违规。
2. **睡岗主判据应是可审计轨迹时序谓词。** 用检测+跟踪形成稳定人员轨迹，定义有效可见性、区域/岗位、姿态代理量、微动、持续时间和离开事件；输出“疑似长时静止/疑似睡岗候选”及证据时间段，遮挡、低置信度或摄像头失效必须输出不确定，不能归为违规。
3. **8GB显存下首选 RTMPose-m/s 或 RTMO-s 级姿态 + 轻量 person detector/tracker + CPU/GPU规则时序。** 这类模型每帧推理、可控制分辨率和批次，明显比视频基础模型可操作。摔倒可并行试轻量 SlowFast/MViT-small 或 PoseC3D；最终必须用目标摄像头数据验证。
4. **InternVideo2/2.5、VideoMAE v2 的价值在表征迁移、离线检索/伪标注和人工复核，不是零样本“睡岗裁判”。** 大模型在公开动作基准的高分不能外推到数十分钟静止、远景遮挡、夜视监控或岗位规范判断。
5. **离岗与区域行为主要是跟踪/区域几何问题，不是动作分类问题。** 进入/离开岗位区、越界、区域停留时长、人员-区域关联应由检测跟踪、摄像机标定/ROI 和轨迹谓词实现；分类器只补充“搬、放、跌倒”等短时动作语义。

## 2. 任务拆分与可观测性

| 目标 | 可观测定义 | 最匹配技术 | 主要失败模式 |
|---|---|---|---|
| 睡岗 | 在规定岗位/座位区域持续可见，姿态长期满足静止/低头/趴伏代理条件，且缺少正常工作微动；需连续视频及岗位规则 | person 检测+跟踪、姿态/人体框属性序列、长时谓词 | 静坐阅读/思考被误报；睡眠生理状态不可由普通RGB摄像头确定；遮挡与低帧率 |
| 离岗 | 跟踪主体离开岗位ROI超过容忍时长，或进入/离开规定区域 | 跟踪+区域多边形+滞回状态机；岗位身份需额外关联 | ID switch、遮挡后重现、岗位ROI定义错误、摄像机移动 |
| 摔倒 | 由直立/行走转为快速下降/横躺，之后处于地面附近；使用连续动作和几何证据 | RGB视频动作模型或姿态序列分类；关键点/框几何辅助 | 蹲下、捡物、躺地工作、镜头视角；单帧“躺姿”不等于摔倒 |
| 搬运 | 人与物体/载荷共同移动，或弯腰、提起、放下等动作片段 | person/object detector+tracker；短窗动作识别；必要时姿态 | 小物体不可见、遮挡、物体类别域差异；“搬运”依赖物体和场景上下文 |
| 区域行为 | 主体进入/停留/穿越禁区或在指定区域执行某动作 | 多目标跟踪+ROI/地面投影+事件逻辑；动作分类可选 | 透视和遮挡；区域边界、摄像机标定、track identity 不稳定 |

## 3. 候选模型比较

### 3.1 单帧人体姿态：RTMPose / RTMO / ViTPose

| 候选 | 论文/年份与任务 | 公开指标（原基准） | 官方权重/许可证 | 8GB与权重尺寸判断 | 对本任务的定位 |
|---|---|---|---|---|---|
| **RTMPose** | Jiang et al., *RTMPose: Real-Time Multi-Person Pose Estimation*, arXiv 2023；COCO关键点 | MMPose 模型库列出 COCO val2017 多个规格；数值依模型/输入/检测器而异。RTMPose-m 在 MPII val 报告 PCKh Mean 0.907（翻转测试），不是监控域指标 | [论文](https://arxiv.org/abs/2303.07399)；[MMPose模型库/配置和checkpoint](https://mmpose.readthedocs.io/en/latest/model_zoo/body_2d_keypoint.html)；实现仓库 Apache-2.0（权重及训练数据条款需随具体资产复核） | S/m 约几十MB至低百MB量级，COCO单人裁剪推理轻，8GB可行；多人top-down还需人检/跟踪 | **首选姿态基线**：关键点、躯干倾角、头躯干相对姿态和运动量；不能识别睡眠意图 |
| **RTMO-s** | Lu et al., *Towards High-Performance One-Stage Real-Time Multi-Person Pose Estimation*, arXiv 2023 | MMPose COCO val2017：RTMO-s 640×640 AP 67.7、AP50 87.8、AP75 73.7；该配置是COCO关键点基准 | [论文](https://arxiv.org/abs/2312.07526)；[官方MMPose配置与checkpoint](https://mmpose.readthedocs.io/en/latest/model_zoo/body_2d_keypoint.html)；OpenMMLab代码 Apache-2.0，核验具体权重/数据条款 | 官方模型页提供checkpoint；参数规模为几十M量级（FP32权重约百MB量级），8GB单路推理可行，需测整条检测/跟踪管线 | 单阶段多人姿态部署更简洁；低分辨率远景人体关键点可能不稳，应保留检测框和置信度质量门 |
| **ViTPose / ViTPose++** | Xu et al., NeurIPS 2022；ViTPose++ TPAMI 2024；通用人体/全身/多域姿态 | 官方repo：COCO val，ViTPose-S/B/L/H AP 73.8/75.8/78.3/79.1；ViTPose++-B 77.0。使用person detector结果，指标不可与不同detector设置直接比较 | [官方repo及权重表](https://github.com/ViTAE-Transformer/ViTPose)；repo Apache-2.0；权重通过OneDrive等链接，基础模型/数据授权独立核查 | S/B相对可控；L/H参数与显存显著增加，权重由数百MB至GB级估算。S/B可尝试8GB批量=1，L/H不作为边缘首选 | 精度/多域姿态候选，离线标注或低吞吐分析；仍是关键点估计器，不产出长时“睡岗”语义 |

RTMPose官方表中模型基准依赖数据集、输入分辨率、人体检测器、flip test 等设置。引用具体结果时必须把这些条件一并记录，不能把MPII PCKh和COCO AP混作同一个指标。

### 3.2 视频动作识别与时序表征

| 候选 | 论文/年份与任务 | 公开指标（原基准） | 官方权重/许可证 | 8GB与权重尺寸判断 | 对本任务的定位 |
|---|---|---|---|---|---|
| **VideoMAE v2** | Wang et al., CVPR 2023；masked video pretraining，动作识别迁移 | 论文/官方repo报告 Kinetics-400、Something-Something V2 等结果，依模型规模、预训练数据、测试view而异；不宜摘单数作场景5预测 | [论文](https://arxiv.org/abs/2303.16727)；[官方代码和model zoo](https://github.com/OpenGVLab/VideoMAEv2)；代码MIT，checkpoint/数据资产条件按官方说明逐项核对 | 官方有不同尺寸；巨型版本参数量/显存远超8GB。小型微调/单clip推理有机会8GB，训练需梯度检查点/低batch；权重从数百MB到数GB | 视频表征或本域小样本微调候选；预训练标签并不包含睡岗岗位语义，长时间静止需专门切窗和标注 |
| **InternVideo2 / 2.5** | InternVideo2 technical report 2024；InternVideo2.5 2025；多模态视频理解、识别、定位 | InternVideo2官方repo报告K400 Top-1 92.1%，属于其指定模型/测试协议；这不能等同监控长时事件表现，也不表示2.5对本任务SOTA | [InternVideo2官方repo/权重链接](https://github.com/OpenGVLab/InternVideo/tree/main/InternVideo2)；[论文](https://arxiv.org/abs/2403.15377)；[InternVideo2.5官方项目](https://github.com/OpenGVLab/InternVideo/tree/main/InternVideo2.5)（如路径调整以组织仓库为准） | 1B/多模态模型需数GB权重，通常8GB显存无法舒适运行全精度长视频；量化/抽帧/短clip可能可行但不应视为实时边缘方案。LLM接入的8B版本显著超限 | 离线视频问答/检索/疑难片段辅助标注；不可把自然语言回答当确定性告警证据，需时间戳定位和人工复核 |
| **MViT / MViTv2** | Fan et al., ICCV 2021；Li et al., CVPR 2022；多尺度视频分类/检测 | PySlowFast官方K400：MViTv2-S 81.0% Top-1、B 82.9%；MMAction2列MViTv2-S 81.1（16×4，5 clips×1 crop）。测试协议影响结果 | [SlowFast模型库](https://github.com/facebookresearch/SlowFast/blob/main/MODEL_ZOO.md)；[MMAction2 MViT模型库](https://mmaction2.readthedocs.io/en/latest/model_zoo/recognition.html)；代码Apache-2.0；检查具体checkpoint和预训练数据条款 | S约34.5M参数，FP32纯参数约138MB；但clip激活/多crop增加显存。8GB单clip batch=1通常可尝试；训练可行性取决于分辨率/帧数 | 中小型RGB时序分类候选；摔倒/短搬运动作需目标域微调。其固定clip不能直接累计“持续半小时静止”语义 |
| **SlowFast** | Feichtenhofer et al., ICCV 2019；视频分类与AVA时空动作检测 | PySlowFast K400 R50 4×16 Top-1 75.6，8×8 77.0；MMAction2 R50 4×16 为75.55。AVA SlowFast R101公开mAP约28-29（版本/设置不同） | [论文](https://openaccess.thecvf.com/content_ICCV_2019/html/Feichtenhofer_SlowFast_Networks_for_Video_Recognition_ICCV_2019_paper.html)；[官方模型库](https://github.com/facebookresearch/SlowFast/blob/main/MODEL_ZOO.md)；[MMAction2 configs/权重](https://mmaction2.readthedocs.io/en/latest/model_zoo/recognition.html)。代码Apache-2.0 | R50约34.5M参数，纯FP32参数约138MB；单clip推理8GB可行性较高，多clip/三裁剪会明显增显存和延迟 | 强健动作分类/检测基线，适合摔倒等短时动作；低运动的静止类高度依赖标注与负样本分布 |
| **PoseC3D** | Duan et al., CVPR 2022；heatmap体积上的3D CNN骨架动作识别 | 论文在NTU RGB+D 60/120、Kinetics-Skeleton等报告有竞争力结果；指标跨数据集、骨架源和协议，官方模型库需按具体配置引用 | [论文](https://openaccess.thecvf.com/content/CVPR2022/html/Duan_Revisiting_Skeleton-Based_Action_Recognition_CVPR_2022_paper.html)；[MMAction2 skeleton模型库](https://github.com/open-mmlab/mmaction2/tree/main/configs/skeleton)；OpenMMLab Apache-2.0 | 小/中型配置通常百MB级权重，显存由时空heatmap尺寸主导；8GB推理可行，训练可降batch/体积 | 适合姿态序列判别摔倒、弯腰/提举等动作；输入姿态误差会传递，不能解决ID跟踪或事件持续定义 |
| **CTR-GCN** | Chen et al., ICCV 2021；骨架图卷积动作识别 | NTU RGB+D 60 常报告 X-Sub 92.4%、X-View 96.8%（具体输入骨架/ensemble配置需对应论文表格）；Kinetics-Skeleton另有结果 | [论文](https://openaccess.thecvf.com/content/ICCV2021/html/Chen_Channel-Wise_Topology_Refinement_Graph_Convolution_for_Skeleton-Based_Action_Recognition_ICCV_2021_paper.html)；[官方代码](https://github.com/Uason-Chen/CTR-GCN)；仓库代码许可依repo LICENSE，checkpoint/数据集权利分开核验 | 模型参数较小，权重一般几十MB量级；8GB运行无压力，主要工程成本是姿态抽取、格式转换和骨架时序 | 骨架动作基线，可用于摔倒/搬运动作候选；不含场景物体和区域语义，极静止类可分性有限 |
| **MMAction2** | OpenMMLab工具箱（持续维护）；涵盖SlowFast、MViT、PoseC3D、CTR-GCN等 | 它是框架和复现实验目录，不是单一模型；其model zoo提供Kinetics、NTU等配置、结果、checkpoint | [官方文档/model zoo](https://mmaction2.readthedocs.io/en/latest/model_zoo/recognition.html)；[GitHub](https://github.com/open-mmlab/mmaction2)；Apache-2.0 | 显存和权重由所选配置决定；以单clip、batch=1、AMP作8GB推理预算；仓库本身不代表某权重可商用 | 推荐作为公平基线与可复现实验框架；先固定数据划分、采样、指标、clip长度和权重版本 |

### 3.3 选择要点

- **RTMPose/RTMO与ViTPose是人体关键点估计器，不是姿态行为分类器。** 输出关键点/置信度后，必须再由规则或时序分类头判断行为。
- **VideoMAE v2、InternVideo、MViT、SlowFast消费短视频clip。** 对几十分钟静止，直接把全视频塞入模型既不经济也超出训练分布；采用稀疏采样/滑窗只解决计算，不自动获得“长时间静止”的监督语义。
- **PoseC3D/CTR-GCN消费骨架序列。** 对摄像头背景变化有一定解耦优势，但遮挡、远距离关键点抖动和人体框关联错误仍是主要误差源；搬运需要物体/区域上下文时RGB双流更有信息。
- **区域/离岗不要用通用动作分类器替代。** 主体轨迹和ROI状态机更可解释、低成本；分类器的作用是给轨迹片段赋动作标签。
- **公开许可应拆开审计：** 代码许可证不自动授予预训练数据、checkpoint、训练图像或商业使用权。科研生产现场还需隐私、监控授权、部署安全审查。

## 4. “睡岗”无直接监督集时，模型能做与不能做的事

### 可以做

- 在清晰可见帧上检测人框、估计关键点和粗姿态；用序列计算头/躯干倾角、身体高度、关键点速度和抖动。
- 在有限时间窗内识别训练集中定义的可见行为类别，如跌倒、弯腰、坐/站；对域外片段输出低置信度或未知。
- 将候选时间段、关键帧、轨迹和几何特征送人工复核；用经人工确认的数据迭代建立本域监督集。
- 依据明确的岗位ROI和制度时长，判定“离开岗位区域超过阈值”或“持续姿态/活动代理条件成立”。这是规则判定，不是模型读心。

### 不能做

- 单帧判定“正在睡觉”；闭眼、低头、趴伏、静止都不是充分证据。
- 从无岗位标签的Kinetics/NTU等通用动作预训练中推导出“睡岗”类准确率、召回率或可部署能力。
- 把长时间静止等同睡眠/怠工：合法阅读、值守观察、设备等待、远程操作、身体状况和遮挡都可产生类似轨迹。
- 在人员不可见、关键点低置信度、摄像头冻结/掉帧、跟踪ID不稳定的区间作违规结论。
- 将动作模型softmax高分直接作为合规真值，或把某个模型的“睡岗”输出作为判定标准块本身。

因此，当前输出宜命名为**“长时低活动/异常姿态候选”**，由显式规则映射到人工复核队列。只有在采集到岗位定义明确、经过伦理与权限审批、时间戳连续且覆盖正常反例的本域数据后，才讨论“睡岗”监督分类器；数据集需按人员/摄像头/日期分组切分，避免相邻帧泄漏。

## 5. 建议的轨迹时序谓词方案

以下为可审计的初始形式化，不是通用阈值推荐。所有时长阈值必须由岗位制度和验证集确定。

### 5.1 轨迹数据

对每个摄像头、track_id、时间戳生成：

`track = {bbox, detector_conf, keypoints, keypoint_conf, visibility, roi_id, pose_proxy, motion, track_quality}`

推荐按固定时间桶（如1秒）聚合而非按帧计数，以减弱帧率和掉帧差异。`visibility`由人体检测连续性/遮挡状态给出；关键点低置信度时姿态谓词取`unknown`，不能填成静止。

### 5.2 谓词

| 谓词 | 一个可实现定义 | 说明 |
|---|---|---|
| `Visible(t)` | 人框有效，检测/跟踪品質高，关键区域无遮挡比例達门限 | 用于定义有效观察时长，不把掉线算作静止 |
| `InPostROI(t)` | 人体脚点/框底中心位于岗位多边形内，结合边界滞回 | 需要每个镜头配置岗位区；边界附近先设为unknown |
| `LowMotion(t)` | 连续有效时间桶内，归一化关键点速度与框中心速度均低于校准阈值 | 对摄像头抖动做背景补偿；单用像素差容易被光照变化误导 |
| `ProlongedPose(t)` | 躯干倾角/头躯干相对角/关键点几何连续满足某可见姿态条件 | 只叫“趴伏/低头姿态代理”，不称睡眠 |
| `NormalActivity(t)` | 在滑窗内出现至少一种可配置动作/位移/姿态变化，且质量足够 | 缺少正常活动不是证据，需结合岗位制度定义 |
| `Away` | `InPostROI=false` 连续超过 `T_away`，且轨迹质量足够 | 断轨不直接等于离岗；短遮挡采用宽限和重新关联 |
| `LowActivityEpisode` | 滑窗有效覆盖率≥`q_min` 且 `LowMotion`占比≥`r_min`，持续墙钟时长≥`T_static` | 由有效观察时长和墙钟时长双门限控制 |
| `SleepPostCandidate` | `InPostROI` 且 `LowActivityEpisode` 且 `ProlongedPose`；正常例外/未知条件排除 | 只能触发复核；策略上保留中性命名与证据窗口 |
| `FallCandidate` | 短窗内人体框/躯干高度快速下降 + 姿态由直立转近水平 + 随后地面附近持续；多线索满足 | 高速下降不是必需单项；蹲下、捡物等需负例校准 |
| `CarryCandidate` | person与物体track在时空上关联，主体移动且物体共同位移；或短动作模型判为提/搬/放 | “持物”与“搬运”分开建谓词；物体不可见时结论unknown |

### 5.3 规则窗口和输出

- 每个事件保存开始/结束时间、有效可见覆盖率、姿态/运动统计、轨迹质量、ROI版本、阈值版本和代表帧引用。
- 滑动窗口采用状态滞回：进入候选和解除候选使用不同阈值，避免边界抖动；掉帧/遮挡时暂停累计或降低置信度，不补记静止时间。
- 输出至少四态：`candidate`、`not_candidate`、`unknown`、`needs_review`；模型标签和制度判定分开保存。
- 对连续视频抽样之外的时间段不作连续静止结论。若相机只保留稀疏抽帧，最多描述“抽样时刻低活动”，不能声称完整持续时长。

## 6. 建议候选与评测路线

### 最小可行候选组合（建议进入后续实验，不代表已验证）

| 目标 | 候选组合 | 原因 |
|---|---|---|
| 睡岗代理、离岗 | RTMPose-m或RTMO-s + person detection/tracking + ROI/时序谓词 | 低显存、可解释；直接覆盖轨迹事实，不假装有睡眠监督 |
| 摔倒 | 上述姿态序列谓词作为规则基线；SlowFast R50或MViTv2-S作为RGB短窗对照；PoseC3D/CTR-GCN作为骨架对照 | 用几何、RGB与骨架三种证据做可比较消融 |
| 搬运/区域行为 | person/object tracking + ROI事件规则；SlowFast/MViT短窗动作头作为候选补充 | 搬运本身依赖人与物体共同运动，区域是几何事件 |
| 离线辅助标注 | InternVideo2/2.5或VideoMAE v2表征/视频问答，人工校正后入标注集 | 大模型用于排序和提案，不作为最终标签或实时依赖 |

### 必需评测

- 数据按摄像头、人员、日期隔离训练/验证/测试；相邻帧不得跨集合。若数据少，报告按摄像头留一和按日期留一结果。
- 睡岗候选报告事件级 precision/recall、每摄像头小时误报数、检测延迟、unknown比例、有效观察覆盖率；不要只报逐帧accuracy。
- 离岗报告事件F1、边界误差和误报/摄像头小时；摔倒报告事件召回、误报/小时、检测延迟；搬运/区域行为报告事件级mAP/F1及ROI边界敏感性。
- 分层报告白天/夜间、远近景、遮挡、多人重叠、坐姿/站姿岗位、摄像机固定/抖动、不同衣着和班次；确认阈值后再冻结测试集。
- 建立难负例：正常静坐值守、读写、低头看设备、弯腰取物、蹲下、短暂离开、遮挡、相机冻结、track ID切换。睡岗正例必须由合规流程下的连续视频人工标注并有时间区间。

## 7. 权重大小与许可核验说明

- **显存可行性不是checkpoint文件大小。** 推理显存还含中间激活、视频解码缓存、检测器、跟踪缓冲和测试多crop；表中“8GB可行”默认batch=1、单路、单clip、合理缩放、FP16/AMP可用时的初筛判断。真实吞吐要测整条pipeline。
- 参数权重大小粗算：FP32约`参数数×4 bytes`，FP16约`×2 bytes`；checkpoint可能含EMA、优化器状态或多头，实际更大。ViTPose链接的模型文件大小未由README统一列出，故不制造精确数字。
- OpenMMLab与ViTPose仓库代码许可可查，但COCO、Kinetics、Ego4D及外部预训练数据、权重分发条款须分别核查；模型开源不自动意味着监控数据商业部署许可。
- 本调研没有下载权重。正式实验前在不触碰生产数据的条件下复核文件大小、SHA256、许可证、checkpoint来源和配置版本，并记录权重资产清单。

## 8. 主要官方/论文来源

- RTMPose: [论文](https://arxiv.org/abs/2303.07399), [MMPose 2D keypoint model zoo](https://mmpose.readthedocs.io/en/latest/model_zoo/body_2d_keypoint.html)
- ViTPose/ViTPose++: [官方仓库（结果、权重、Apache-2.0）](https://github.com/ViTAE-Transformer/ViTPose)
- VideoMAE v2: [CVPR 2023论文](https://arxiv.org/abs/2303.16727), [官方仓库](https://github.com/OpenGVLab/VideoMAEv2)
- InternVideo2: [论文](https://arxiv.org/abs/2403.15377), [官方仓库与模型链接](https://github.com/OpenGVLab/InternVideo/tree/main/InternVideo2)
- InternVideo2.5: [官方项目目录](https://github.com/OpenGVLab/InternVideo/tree/main/InternVideo2.5)
- MViT/SlowFast: [PySlowFast官方Model Zoo](https://github.com/facebookresearch/SlowFast/blob/main/MODEL_ZOO.md), [MMAction2 recognition model zoo](https://mmaction2.readthedocs.io/en/latest/model_zoo/recognition.html)
- PoseC3D: [CVPR 2022论文](https://openaccess.thecvf.com/content/CVPR2022/html/Duan_Revisiting_Skeleton-Based_Action_Recognition_CVPR_2022_paper.html), [MMAction2 skeleton configs](https://github.com/open-mmlab/mmaction2/tree/main/configs/skeleton)
- CTR-GCN: [ICCV 2021论文](https://openaccess.thecvf.com/content/ICCV2021/html/Chen_Channel-Wise_Topology_Refinement_Graph_Convolution_for_Skeleton-Based_Action_Recognition_ICCV_2021_paper.html), [官方代码](https://github.com/Uason-Chen/CTR-GCN)
- MMAction2: [官方项目/许可证/模型工具箱](https://github.com/open-mmlab/mmaction2)
