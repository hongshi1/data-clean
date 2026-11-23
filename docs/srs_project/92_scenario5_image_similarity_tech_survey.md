# 场景5：跨图片样本关联（C3项）技术调研——图像相似度检索与跨模态检索

> v1.0 | 2026-11-17 | 调研范围: 2022-2026年（重点2024-2026）可实际运行的图像相似度/近重复检测/跨模态技术
> 用途: 场景5阶段③"跨样本+时序"管道（79号文档C3项）的技术选型依据——当(camera_id, timestamp)元数据不可用时，退化路径为"图片相似度聚类"，本报告即为该退化路径与增强路径的技术储备
> 姊妹文档: 82号（姿态/动作模型调研，感知侧）；本报告覆盖"关联侧"（样本聚合）
> 检索方法: GitHub官方README（含指标表与许可证）+ arXiv论文全文（DISC21对比表取自CopyNCE ICCV 2025原文）+ arXiv API按日期检索（near-duplicate/copy detection/perceptual hashing，2024-2026）

---

## 0. 结论速览（选型一句话）

| 需求 | 首选（全部可本地运行、许可证干净） | 理由 |
|---|---|---|
| 近重复帧聚类的**粗召回** | imagehash（pHash+dHash双哈希，汉明距离阈值） | CPU毫秒级/图，BSD-2；监控抽帧场景的"同源帧"99%是轻微扰动帧 |
| 近重复聚类的**精通道** | SSCD（sscd_disc_mixup, 512维, MIT）或 DINOv2 ViT-S + faiss | SSCD为DISC21基线冠军系（抗编辑）；DINOv2语义聚类更强但**不能直接做NDED**（见§4警示） |
| 剪裁/形变鲁棒的**逐对复核** | XFeat + LighterGlue（全Apache-2.0） | 规避SuperPoint许可证风险；CPU可实时；RoMa的Tiny版也基于XFeat |
| 中文图文跨模态（QA文本↔图片） | Chinese-CLIP ViT-L/14（MIT）或 SigLIP 2（多语言，Apache-2.0） | COCO-CN/Flickr30K-CN有官方数字；SigLIP 2多语言+密集特征更好 |
| 聚类执行 | HDBSCAN（sklearn内置/hdbscan库, BSD-3）+ DBCV/轮廓系数 | 无需预设簇数，自动出噪声簇；全库评测指标ARI/NMI/V-measure |
| 流式增量（数据生产线持续入库） | river DBSTREAM（BSD-3） | 在线微簇算法，KDD'22有评测协议；批量管道仍推荐HDBSCAN |

**许可证红线**：DINOv3权重（自定义非商业许可）、SuperPoint权重（Magic Leap限制性许可）不进产品管线；DINOv2/LightGlue/XFeat/SSCD/imagehash/hdbscan/river/faiss/Chinese-CLIP全部宽松许可。

---

## 1. 全局图像嵌入（DINOv2 / DINOv3 / SigLIP 2 / EVA-CLIP / CLIP）

### 1.1 对比表

| 模型 | 论文/年份 | 关键指标（官方README/论文） | 权重/库 | 许可证 |
|---|---|---|---|---|
| **DINOv2** | Oquab et al., arXiv:2304.07193, 2023 (TMLR 2024) | ImageNet-1k **linear 84.5→87.1%**（ViT-B→ViT-g+reg）；kNN 82.0→83.7%；patch级密集特征质量是其卖点（检索/分割/深度通用） | [facebookresearch/dinov2](https://github.com/facebookresearch/dinov2)（13.5k★，torch.hub一行加载，timm/HF支持） | **Apache-2.0**（代码+权重） |
| **DINOv3** | Siméoni et al., arXiv:2508.10104, 2025.08（含2025-2026持续更新：FINO元数据训练分支、ConvNeXt蒸馏、ADE20K/NYUv2线性探测） | 官方README给训练配置复现值（ViT-L/16 IM-1k: kNN 82.0 / linear 83.5）；主打**gram anchoring后密集特征不退化**、高分辨率适配；规模到ViT-7B | [facebookresearch/dinov3](https://github.com/facebookresearch/dinov3)（11.8k★，需申请下载权重，HF Hub同步，transformers≥4.56/timm≥1.0.20支持） | **DINOv3 License（非商业研究许可）**——产品管线不可用 |
| **SigLIP 2** | Tschannen et al., arXiv:2502.14786, 2025.02（Google DeepMind） | **COCO检索 T→I R@1 / I→T R@1**：B/16-384 = 54.6/71.4；So400m/16-512 = 56.0/71.3；**g-opt/16-384 = 56.1/72.8**（当前开源最优级）；zero-shot ImageNet最高**85.0%**（g-opt/16-384）；新增定位/密集预测/多语言/公平性能力，NaFlex变分辨率变体保持原长宽比 | [google-research/big_vision](https://github.com/google-research/big_vision)（checkpoint直链npz）+ [HF collection](https://huggingface.co/collections/google/siglip2-67b5dcef38c175486e240107)（ViT-B 86M / L 303M / So400m 400M / g 1B 四档） | 代码**Apache-2.0**，权重CC-BY |
| **EVA-CLIP-18B** | Sun et al., arXiv:2402.04252, 2024.02（BAAI） | 27个分类基准平均zero-shot **80.7%**；retrieval MR **87.8**；6B样本训练（LAION-2B+COYO-700M）；EVA-CLIP-8B: 79.4%/MR 86.2 | [baaivision/EVA](https://github.com/baaivision/EVA)（EVA-CLIP-18B子目录；PT权重35.3GB@HF） | **MIT**；但35GB权重+8GB显存环境不现实，仅作数字参照 |
| CLIP (OpenAI) | 2021 | baseline参照：ViT-L zero-shot INet ~75%；COCO T→I R@1 ~43-58（依输入分辨率/实现） | open_clip（Apache-2.0） | MIT |

### 1.2 对场景5的落点判断

1. **8GB本地GPU约束下的可行档**：DINOv2 ViT-S/14（21M, 384维）/ ViT-B/14（86M, 768维）；SigLIP 2 B/16-384（86M）——与82号文档确立的"8GB显存首选小模型"一致。
2. **语义嵌入≠近重复检测器**：DISC21基准上DINO ViT-S描述子仅 **μAP 20.0 / RP90 6.8**（CopyNCE论文Tab.1，ICCV 2025）——语义级"像"与像素级"同源"是两回事。**跨图片样本关联（找同一摄像头帧）必须用NDED专用描述子（§4）或pHash（§3），语义嵌入只用于"场景/实体级"粗分组**。
3. DINOv2的patch级密集特征可直接做**免训练的图文-图图patch匹配**（官方notebook: dense_sparse_matching.ipynb）——场景5里"同一工位不同时刻"的快速可解释对齐可用它，且Apache-2.0。

---

## 2. 局部特征匹配（SuperPoint+LightGlue / LoFTR / ELoFTR / DKM / RoMa / XFeat）

### 2.1 对比表（MegaDepth-1500位姿AUC@5/10/20 为标准三档指标）

| 方法 | 论文/年份 | 关键指标 | 库 | 许可证 |
|---|---|---|---|---|
| SuperPoint + LightGlue | DeTone CVPRW 2017 + Lindenberger **ICCV 2023**（arXiv:2306.13643） | SP+LG（官方，1024px/4096kp）MegaDepth-1500 AUC@5/10/20 = **59.1/73.8/84.1**（XFeat复现数字）；RTX3080上**150FPS@1024kp、50FPS@4096kp**（快于SuperGlue 4-10×，编译+自适应）；已入**HF Transformers**（`ETH-CVG/lightglue_superpoint`）与kornia | [cvg/LightGlue](https://github.com/cvg/LightGlue)（4.9k★；训练用glue-factory） | LightGlue代码+权重**Apache-2.0**（2024年已从限制许可切换）；**SuperPoint权重仍是Magic Leap限制性许可（非商业）**；ALIKED/BSD-3、DISK Apache可用作替代前端 |
| LoFTR | Sun et al., CVPR 2021（arXiv:2104.00680, T-PAMI 2022） | 检测器免、低纹理区强；MegaDepth-1500 AUC@5≈58-59（d84 official config）；视觉定位两个公开基准当时第一 | [zju3dv/LoFTR](https://github.com/zju3dv/LoFTR)（3.0k★；kornia≥0.5.11集成，`kornia.feature.LoFTR`） | **Apache-2.0**（ZJU-SenseTime，OT分支依赖SuperGlue文件不可再分发——用DS版权重即可） |
| **ELoFTR** | Wang et al., **CVPR 2024**（arXiv:2403.04765） | 比LoFTR**快~2.5×**且精度更高，效率上"surpass SuperPoint+LightGlue的稀疏管线"；聚合注意力+自适应token选择+两阶段细相关层 | 项目页 zju3dv.github.io/efficientloftr | Apache-2.0 |
| DKM | Edstedt et al., CVPR 2023（arXiv:2303.16874） | 稠密warp回归式匹配，当时MegaDepth SOTA（AUC@5≈60+级别） | [Parskatt/DKM](https://github.com/Parskatt/DKM) | MIT（除依赖部分） |
| **RoMa** | Edstedt et al., **CVPR 2024**（arXiv:2305.15404） | 稠密鲁棒匹配+可靠度图；**Tiny RoMa**（基于XFeat）：Mega-1500 AUC@5/10/20 = **56.4/69.5/79.5**（vs XFeat* 51.9/67.2/78.9）；IMC22 mAA@10 = 42.2 | [Parskatt/RoMa](https://github.com/Parskatt/RoMa)（1.3k★，`pip install romatch`，PyPI直装） | **MIT**（除DINOv2部分为Apache-2.0，整体兼容商用） |
| **XFeat** | Potje et al., **CVPR 2024**（arXiv:2404.19174） | 64维紧凑描述子；**CPU实时**（i5笔记本VGA实时稀疏推理）；RTX4090批量**~1400FPS**；XFeat+LighterGlue（比LightGlue小3×快3×）MegaDepth-1500 AUC@5/10/20：Fast(640px) **44.4/61.0/74.6**、Accurate(1024px) **56.4/71.0/81.9**（对照SP+LG 46.9/63.3/76.2、59.1/73.8/84.1——**用~1/5参数逼近**） | [verlab/accelerated_features](https://github.com/verlab/accelerated_features)（1.8k★，torch.hub三行加载，含训练Colab） | **Apache-2.0**（标题即"Beyond Restricted Neural Licenses"——刻意规避SuperPoint式许可证问题） |
| OmniGlue | Jiang et al., CVPR 2024（Google） | DINOv2基础模型引导的通用匹配（零样本泛化） | github.com/google-research/omniglue | Apache-2.0 |

### 2.2 增广与形变处理能力（场景5关注点）

- **视角/形变**：稠密系（LoFTR/ELoFTR/RoMa）对大视角变化与低纹理（监控白墙、空车间）显著强于稀疏系；RoMa给出逐像素warp+certainty，可当"两帧是否同场景"的软判据（certainty均值做特征）。
- **光照/模糊**：XFeat明确报告对光照变化鲁棒性优于ORB/SIFT；DISC系增强（色彩抖动/模糊）下NDED描述子（§4）本就内建。
- **裁剪**：局部特征天然抗裁剪（只要有共视区）；全局嵌入需要SSCD/RoMa类训练目标或crop_resistant_hash（§3）。
- **实用建议**：跨图片复核是"逐对"操作，成本高——只对§3/§4粗召回的候选对做，不进全量管道。

---

## 3. 感知哈希（pHash / dHash / wHash / aHash）

### 3.1 工业实现库

| 库 | 算法覆盖 | 性能 | 链接 | 许可证 |
|---|---|---|---|---|
| **imagehash** (Python) | aHash/pHash/dHash(横+竖)/wHash/HSV colorhash/**crop_resistant_hash**(多子区域+汉明多匹配，抗裁剪) | PIL+numpy+scipy；hashsize可调（8→64位典型）；README自带7441图标/10.9万艺术品两组聚类演示与`find_similar_images.py` | [JohannesBuchner/imagehash](https://github.com/JohannesBuchner/imagehash)（3.9k★，`pip install imagehash`） | **BSD-2-Clause** |
| **OpenCV img_hash** (contrib) | pHash/averageHash/dHash/blockMeanHash(0/1)/radialVarianceHash/PHash结构变体 | C++实现、OpenCV生态、批量快；radialVarianceHash对旋转较稳 | [opencv_contrib img_hash模块](https://docs.opencv.org/3.4/d4/d93/group__img__hash.html) | **Apache-2.0** |
| pHash.org (C++) | pHash完整实现（DCT+径向投影/文本/音频哈希族） | 原版参考实现 | [phash.org](https://www.phash.org/) | **GPLv3**（商用注意） |
| imagehash工程配套 | 大规模汉明检索：PostgreSQL SP-GiST汉明扩展 + BK树 | 教程级方案见KDJDEV/imagehash-reverse-image-search-tutorial | 见imagehash README #127 | — |

### 3.2 精度对比（定性+可复核来源）

- 经典结论（HackerFactor/content-blockchain.org两篇被imagehash README引用的对比研究）：**pHash与dHash总体最稳**（dHash快、对渐变敏感；pHash对频率结构更鲁棒），aHash假阳性率高，wHash介于其间；阈值惯例：8×8=64位哈希，汉明距离 **≤6** 视为近重复、**≤10** 送精通道（需在自己数据上校准——与我们的BGE阈值EMB_TH_LOCAL=0.78校准方法论同构）。
- colorhash只看颜色分布不看位置——监控场景光照恒定时反而可用作旁证；**crop_resistant_hash**（IEEE 6980335思想）专为裁剪设计。
- 2024-2026学术旁证（arXiv检索）：感知哈希仍是数据集去重/防泄漏的工业标准——NeurIPS 2026 E&D Track用pHash在565k医学影像中发现**≥118k重复对下界**（arXiv:2611.10144）；PCOSGen数据集去污（arXiv:2608.20144）；MC-Dropout脑瘤MRI评测按pHash簇切分防泄漏（arXiv:2607.16317）——**"按感知哈希簇切分防泄漏"直接可借鉴到我们的评测协议**。
- 局限：对几何变形（旋转/透视/大裁剪）弱——需要时升级到§4深度描述子或§2局部匹配。

---

## 4. 近重复检测 NDED / 图像复制检测 ICD（CVPR/ICCV/NeurIPS/AAAI/WACV主线）

### 4.1 DISC21基准上的当前数字（μAP = micro average precision；RP90 = precision@90%处的召回）

| 方法 | 会议/年份 | DISC21 μAP / RP90（descriptor，无后处理→带score norm） | 说明 |
|---|---|---|---|
| DINO ViT-S（语义嵌入对照） | ICC 2021权重 | **20.0 / 6.8** | 语义嵌入做NDED的反面教材（CopyNCE Tab.1） |
| SSCD R50 (512d) | **CVPR 2022**（arXiv:2202.10261） | **61.5 / 38.3 → SN后 72.5 / 63.1** | 自监督对比+GeM池化+熵正则；官方给出操作阈值：**cos>0.75 ⇒ 90%精度的副本判定**；MIT；TorchScript权重免依赖即用 |
| S-square (EffNet-B5) | ISC21参赛（arXiv:2112.03415） | 66.4 / —（用了额外数据） | 比赛系方案 |
| Lyakaap (EffNetV2-M) | ISC21冠军系 | 64.3 / 56.6 | 比赛系方案 |
| BoT R50 | ECCV 2022（arXiv:2208.09780系） | 70.5 / 61.6（Str）→71.5 / 62.9（+YOLO局部） | batch内难负+局部分支 |
| ASL (NDEC基准) | **AAAI 2023**（arXiv:2205.12358） | DISC上与BoT同级；**提出NDEC硬负基准**（+10万训练硬负对/2.4万测试硬负对） | 非对称相似度学习，处理"部分裁剪是副本、反向不是"的方向性 |
| RDCD (EffNet-B0, 64-256d) | **WACV 2025**（arXiv:2405.17928） | 小模型+紧凑描述子：64/128/256维μAP比基线**+5.0/4.9/5.9%** | 关系自蒸馏——轻量部署路线 |
| ICDiff | **NeurIPS 2024**（arXiv:2409.19952） | 首个扩散模型生成图像的复制检测（D-Rep数据集4万人工标注对，PDF-Embedding监督） | 生成内容质检——数据集生产线场景直接相关 |
| AnyPattern | 2024（arXiv:2404.13788） | 100种篡改模式的in-context ICD基准；大训练集+26.66μAP，ImageStacker再+16.75μAP | 未见模式的快速反应 |
| **CopyNCE** | **ICCV 2025**（arXiv:2602.17484，蚂蚁集团） | **descriptor: 70.5/63.6 → 72.6/68.4（SN后）；matcher(ViT-S,336,local): 88.7 μAP / 83.9 RP90 = 当前开源SOTA**；NDEC上72.5/36.8（超Strong ASL +8.4μAP）；DISC21 Phase 2榜：65.8/61.0（descriptor） | PixTrace像素坐标追踪+几何引导对比损失；**Apache-2.0，ViT-S权重可下载**（仅2个基础ckpt，其他需自行训练）；224×224输入 |
| 视频线（VSC/VCDB） | CVPR 2023-2024（VCSL/MeVCS） | Meta VSC2022冠军方案在基线上+38~60%（arXiv:2304.11964） | 场景5若上视频轨可引 |

**评测协议要点**（DISC21官方, arXiv:2106.09672 + 2202.04007）：100万参考库+10万查询（含海量干扰图），指标μAP/RP90；**dev set I可微调、dev set II/test只评**——与我们"锚点三分协议"（文档级分块防泄漏）同构，可直接借用其数据切分思想。

### 4.2 对场景5的落点判断

1. **SSCD是"开箱即用"最优性价比**：MIT许可、TorchScript模型（`sscd_disc_mixup.torchscript.pt`，512维，无需任何SSCD代码依赖）、官方给出决策阈值（cos>0.75≈90%精度）、repo虽2023年归档但代码4 commits稳定、指标可复核。批量提取建议用`Resize(320,320)`方形张量（README推荐，GPU批处理友好）。
2. **CopyNCE是精度上限参照**（ICCV 2025 SOTA且Apache-2.0+可下载权重），但权重仅2个ViT-S基础档、训练管线重（8×A100）；其**PixTrace"增强可追踪"思想**对我们自建场景5训练数据（同一帧加受控扰动=正样本对）有直接方法论价值。
3. **ASL的"非对称相似"**对场景5有一特殊启发：QA数据的"困难负样本"（同场景不同时刻）正是"语义近但非同源"的硬负——其NDEC基准构造方式（往DISC里掺OpenImages硬负）可复制到我们的监控帧库。
4. ICDiff（NeurIPS 2024）提示：若场景5数据集里混入**扩散模型生成的"假监控帧"**，NDED描述子是现成质检器。

---

## 5. 中文图文检索（Chinese-CLIP / AltCLIP / SigLIP 2多语言）

### 5.1 对比表（zero-shot除非注明；CN-CLIP=Chinese-CLIP最优规模ViT-H/14或注明）

| 模型 | 论文/年份 | COCO-CN（测试集） | Flickr30K-CN（测试集） | 其他 | 库/权重 | 许可证 |
|---|---|---|---|---|---|---|
| **Chinese-CLIP** (CN-CLIP) | Yang et al., arXiv:2211.01335, 2022（~2亿中文图文对训练） | **TR R@1/5/10 = 69.2/89.9/96.1；I2T = 63.0/86.6/92.9**；finetune后 TR 81.5 / I2T 83.5 | **TR R@1/5/10 = 71.2/91.4/95.5；I2T = 81.6/97.5/98.8**；finetune后 TR 83.8 / I2T 95.3 | MUGE TR zs 63.0→ft 68.9；ELEVATER 10数据集零样本分类（CIFAR-100 79.7等） | [OFA-Sys/Chinese-CLIP](https://github.com/OFA-Sys/Chinese-CLIP)（6.0k★，`pip install cn_clip`，RN50/B/L/L-336/H五档，HF+ModelScope双源，ONNX/TensorRT部署文档齐全） | **MIT** |
| **AltCLIP** | Chen et al., arXiv:2211.06679, 2022（CLIP换XLM-R文本编码器+两阶段训练） | 论文报告COCO-CN/Flickr30k-CN/ImageNet-CN/XTD多任务SOTA | Flickr30k-CN中文 **TR R@1 = 63.7（AltCLIP）/ 69.8（AltCLIP*微调增强版）；I2T R@1 = 84.7** | 英文Flickr30k TR R@1 66.3/72.5*（接近甚至超过原CLIP 65.0）——**双语一体**是其差异点 | FlagAI开源（github.com/FlagAI-Open/FlagAI）+ [HF BAAI/AltCLIP](https://huggingface.co/BAAI/AltCLIP)（transformers直用） | **CreativeML OpenRAIL-M**（用途限制型，非纯MIT——管线选型时注意） |
| Wukong | 2022 | Flickr30k-CN TR 51.7；COCO-CN TR 53.4 | 51.7 | — | 已停维护 | — |
| Taiyi-CLIP | 2022 | Flickr30k-CN TR 60.8 | 60.8 | — | IDEA | — |
| R2D2 | 2022 | Flickr30k-CN TR 60.9；COCO-CN TR 56.4 | 60.9 | — | 学术 | — |
| **SigLIP 2**（多语言档） | 2025.02 | （非中文专项基准；多语言去偏训练，Gemma tokenizer覆盖中文） | — | 中文能力属"多语言"而非"中文优化"；胜在**同模型同时给密集特征** | big_vision / HF | Apache-2.0 |

### 5.2 对场景5的落点判断

1. **中文跨模态事实标准仍是Chinese-CLIP**：2亿中文对训练、MIT、五档规模、部署链路（ONNX/TensorRT）齐全；COCO-CN/Flickr30K-CN/MUGE三基准官方数字可直接进论文对比表。
2. AltCLIP数字在Flickr30k-CN上略低于CN-CLIP最大档（63.7 vs 71.2），但**单模型双语**（QA里中英混杂时不用切换）；OpenRAIL-M许可带用途条款，内部科研OK、产品化需审。
3. 场景5的用法定位：QA文本↔图片的**语义一致性旁证**（"answer说未戴安全帽，图片检索同caption是否落在该簇"），不是C3主通道——C3主通道是像素级/元数据级关联。与我们的`algorithms/blackboard/embedding_channel.py`四级降级（live API→本地BGE→cache）同构：中文CLIP可作**图片侧的本地语义通道**，文本侧继续用BGE（1024维已本地GPU化）。

---

## 6. 聚类方法（图像聚类的批式/在线方法与评估）

### 6.1 算法与库

| 方法 | 库 | 特点 | 链接 | 许可证 |
|---|---|---|---|---|
| **HDBSCAN** | `hdbscan` 3.2k★ / **sklearn≥1.3内置**（`sklearn.cluster.HDBSCAN`） | 变密度簇+噪声簇(-1)；主参数`min_cluster_size`直觉化；**GLOSH离群分数**免费附带（坏样本质检可复用）；membership概率=软聚类；可选`metric='cosine'`/预计算距离矩阵（配faiss近邻图） | [scikit-learn-contrib/hdbscan](https://github.com/scikit-learn-contrib/hdbscan)（JOSS 2017；ICDMW 2017加速实现） | **BSD-3-Clause** |
| DBSCAN | sklearn | 经典；需ε；图像嵌入上通常劣于HDBSCAN（簇密度不均） | sklearn | BSD-3 |
| **DBSTREAM**（在线） | **river** 6.1k★（`river.cluster.DBSTREAM`） | 微簇(micro-cluster)流式聚类，`learn_one`逐样本；共享距离参数；concept drift工具配套 | [online-ml/river](https://github.com/online-ml/river)（JMLR 2021，Python≥3.11，Windows有wheel） | **BSD-3-Clause** |
| 向量近邻索引 | **faiss**（MIT，GPU版）；hnswlib（Apache-2.0）；usearch | 百万级512-1024维嵌入秒级检索；pHash的64位汉明检索可用faiss binary index或BK树 | github.com/facebookresearch/faiss | MIT |

### 6.2 评估指标（分两种金标可用性）

- **有金标（评测协议）**：ARI（adjust rand index，对簇数不敏感）、NMI、V-measure（=同质性/完备性调和均值，sklearn同函数给出三件套）——推荐主报ARI+V-measure。
- **无金标（生产内部一致性）**：silhouette（cosine度量）、**DBCV**（密度簇有效性，HDBSCAN原生契合）、簇稳定性（bootstrap重聚类ARI）——选型期用。
- **在线评测协议**：river的metric体系 + KDD'22论文《Online Clustering: Algorithms, Evaluation, Metrics, Applications and Benchmarking》（10.1145/3534678.3542600）的prequential评估框架（预测-更新交错）——数据生产线持续入库时用。
- **场景5特有的免费金标**：75号文档已指出(camera, timestamp)元数据可当聚类的"银标签"——图像聚类结果与元数据聚类的ARI本身就是C3管道的内部质量指标，**无需人工标注即可自评**（这是本调研最重要的方法论结论之一）。

---

## 7. C3项推荐架构（综合本调研+75号文档既有设计）

```
跨图片样本关联管道（C3，三级漏斗）

L0 元数据主键（免费红利，75号§3.3）
    group_by(camera_id, time_bucket) ──────────────► 组内直接进QA结论比对
    （无camera_id时跳过，全量走L1）

L1 粗召回（CPU，毫秒级/图）
    imagehash: pHash64 + dHash64 双哈希
    阈值: 汉明≤6 判同源（初始值，样例数据校准后锁阈值——复刻BGE EMV_TH_LOCAL=0.78的校准协议）
    产出: 候选同源对（高召回低精度）

L2 精通道（GPU 8GB档）
    SSCD sscd_disc_mixup (512d, TorchScript, MIT): cos相似度
    决策阈值初始值: 0.75（官方90%精度锚点）
    语义旁通道: DINOv2 ViT-S (384d)——只用于"同场景不同位置"的粗分组，不参与同源判定
    索引: faiss IVF/HNSW（≥10万图时）
    产出: 同源簇（连通分量）

L3 聚合与校验
    HDBSCAN(cosine, min_cluster_size=3) 于SSCD嵌入上聚类（连通分量的密度校验+噪声剔除）
    组内QA比对: answer三态{0,1,2}冲突 → "可疑"档（四态语义，76号文档）
    仲裁（可选，仅冲突对）: 冻结VLM描述文件比对（79号证据冻结协议）或XFeat+LighterGlue逐对复核

评测: 以(camera,timestamp)银标签为金标算ARI/V-measure;
      冲突对人工抽检子集(≈百级)做precision锁定;
      全流程LLM/VLM走缓存（AGENTS.md硬规则7）
```

**成本画像**（8GB GPU本地栈，与82号文档环境一致）：L1全CPU；L2 SSCD R50@320px批量约数百图/秒（RTX 3060级）；百万图库faiss检索亚秒级；L3 HDBSCAN在嵌入上十万级样本分钟级。**无任何在线API依赖**（与"VLM降级为仲裁位"的既有决策一致）。

---

## 8. 风险与缺口清单

| # | 风险 | 等级 | 对策 |
|---|---|---|---|
| 1 | 语义嵌入误用于NDED（DISC21上DINO仅20.0 μAP） | 高 | 严格区分两通道：同源判定只用SSCD/pHash；语义分组才用DINOv2 |
| 2 | SuperPoint/DINOv3许可证污染 | 高 | 前端用XFeat/ALIKED/DISK（Apache）；基础模型用DINOv2（Apache） |
| 3 | 哈希阈值照搬文献数字 | 中 | 在672条样例+真实帧数据上做阈值扫描（复刻tools/bge_threshold_sweep.py方法） |
| 4 | 监控帧"近时不同源"（镜头切换/多路同壳） | 中 | L0元数据优先；L2的SSCD对"同构图不同源"有区分度（DISC21硬负训练目标即此） |
| 5 | Chinese-CLIP在监管垂直域（安全帽/工装词汇）的领域漂移 | 中 | 零样本先测；不足则LoRA微调（repo提供finetune全链路，MIT许可无障碍） |
| 6 | CopyNCE等2025 SOTA复现成本（权重不全+8×A100训练） | 低 | 只作论文对比数字引用，不进管线；SSCD开箱即用性已够C3第一版 |
| 7 | 在线聚类（river DBSTREAM）与批式（HDBSCAN）结论不一致 | 低 | C3第一版用批式（数据集生产线天然分批）；流式仅当真做实时采集时评估 |

---

## 9. 引用索引（论文/库/指标原文出处）

**全局嵌入**
- DINOv2: arXiv:2304.07193 | github.com/facebookresearch/dinov2 | Apache-2.0 | 指标: README预训练表
- DINOv3: arXiv:2508.10104 | github.com/facebookresearch/dinov3 | DINOv3 License(非商业)
- SigLIP 2: arXiv:2502.14786 | big_vision README_siglip2.md指标表 | Apache-2.0/CC-BY
- EVA-CLIP-18B: arXiv:2402.04252 | EVA repo EVA-CLIP-18B/README | MIT

**局部匹配**
- LightGlue: arXiv:2306.13643 (ICCV23) | github.com/cvg/LightGlue | Apache-2.0
- LoFTR: arXiv:2104.00680 (CVPR21) | github.com/zju3dv/LoFTR | Apache-2.0
- ELoFTR: arXiv:2403.04765 (CVPR24) | zju3dv.github.io/efficientloftr | Apache-2.0
- RoMa: arXiv:2305.15404 (CVPR24) | github.com/Parskatt/RoMa | MIT
- XFeat: arXiv:2404.19174 (CVPR24) | github.com/verlab/accelerated_features | Apache-2.0

**感知哈希**
- imagehash: github.com/JohannesBuchner/imagehash | BSD-2-Clause
- OpenCV img_hash: docs.opencv.org/3.4/d4/d93/group__img__hash.html | Apache-2.0

**NDED/ICD**
- DISC21基准: arXiv:2106.09672 (NeurIPS21) + 结果分析 arXiv:2202.04007 | github.com/facebookresearch/isc2021
- SSCD: arXiv:2202.10262 (CVPR22) | github.com/facebookresearch/sscd-copy-detection | MIT
- ASL/NDEC: arXiv:2205.12358 (AAAI23) | github.com/WangWenhao0716/ASL
- RDCD: arXiv:2405.17928 (WACV25) | github.com/juntae9926/RDCD
- ICDiff: arXiv:2409.19952 (NeurIPS24) | icdiff.github.io
- AnyPattern: arXiv:2404.13788 | anypattern.github.io
- CopyNCE: arXiv:2602.17484 (ICCV25) | github.com/eddielyc/CopyNCE | Apache-2.0（本文§4所有DISC21对比数字出处）

**中文跨模态**
- Chinese-CLIP: arXiv:2211.01335 | github.com/OFA-Sys/Chinese-CLIP | MIT（COCO-CN/Flickr30K-CN/MUGE数字出自README官方表）
- AltCLIP: arXiv:2211.06679 | huggingface.co/BAAI/AltCLIP | CreativeML OpenRAIL-M

**聚类/索引**
- hdbscan: JOSS 2017 (10.21105/joss.00205) + ICDMW 2017 | github.com/scikit-learn-contrib/hdbscan | BSD-3
- river: JMLR 2021 | github.com/online-ml/river | BSD-3 | 在线聚类评测: KDD'22 10.1145/3534678.3542600
- faiss: github.com/facebookresearch/faiss | MIT

> 附注：本文所有指标均来自上述官方README/论文原文（2026-11-17访问快照），无二手转引；`content-blockchain.org`哈希对比页访问失败(502)，其结论经由imagehash README转引，已在§3.2标注来源级别。
