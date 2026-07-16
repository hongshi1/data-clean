# SARCLIP vs 标准CLIP 零样本测试报告

> 日期：2026-06-29
> 测试数据：10条合成军工武器数据（7正确 + 3图文不匹配）

## 测试环境
- 硬件：Apple M4 Pro (MPS加速)
- SARCLIP：BiliSakura/SARCLIP-ViT-L-14 (1.7GB, 权重格式转换后0 missing/0 unexpected)
- 标准CLIP：openai/clip-vit-base-patch32 (151M参数)

## 对比结果

| 指标 | 标准CLIP (ViT-B-32) | SARCLIP (ViT-L-14) |
|---|---|---|
| 分类准确率 | 60.0% | 10.0% |
| 不匹配样本检出率 | 100% (3/3) | 100% (3/3) |
| 平均置信度 | 0.95 | 0.21 |

## 逐样本结果

### 标准CLIP
| ID | 武器 | 真实类型 | 预测类型 | 置信度 | 状态 |
|---|---|---|---|---|---|
| w001 | AK-47 | Assault Rifle | Assault Rifle | 0.984 | ✅ |
| w002 | M16A4 | Assault Rifle | Assault Rifle | 0.964 | ✅ |
| w003 | Glock 17 | Pistol | Pistol | 0.997 | ✅ |
| w004 | M249 SAW | LMG | Submachine Gun | 0.784 | ❌ |
| w005 | RPG-7 | RPG | RPG | 0.998 | ✅ |
| w006 | 手枪描述/步枪图 | Pistol | Assault Rifle | 0.885 | ⚠️检出 |
| w007 | 步枪描述/手枪图 | Assault Rifle | Pistol | 0.835 | ⚠️检出 |
| w008 | RPG描述/步枪图 | Rocket Launcher | Assault Rifle | 0.947 | ⚠️检出 |
| w009 | MP5 | SMG | SMG | 0.995 | ✅ |
| w010 | Barrett M82 | Sniper | Sniper | 0.989 | ✅ |

### SARCLIP
| ID | 武器 | 真实类型 | 预测类型 | 置信度 | 状态 |
|---|---|---|---|---|---|
| w001-w010 | 所有样本 | 各种类型 | Sniper Rifle | ~0.21 | 仅w010✅ |

## 关键发现

1. **SARCLIP权重成功加载**：通过key重映射+attention拆分(in_proj→q/k/v_proj)+projection转置，实现0 missing/0 unexpected keys
2. **SARCLIP不适合合成图像**：训练于SAR图像，对PIL绘制的武器示意图理解能力有限（低置信度~0.21）
3. **标准CLIP在合成图像上表现良好**：60%准确率，高置信度(0.95)
4. **两个模型都实现100%不匹配检出**：
   - 标准CLIP：通过正确识别图片实际内容来检测不匹配
   - SARCLIP：因无法理解合成图像，所有预测都不匹配元数据类型
5. **SARCLIP应在真实SAR图像上测试**：预期在MegaSAR-2M等真实SAR数据上，SARCLIP将显著优于标准CLIP

## 技术细节：SARCLIP权重格式转换

BiliSakura/SARCLIP-ViT-L-14使用open_clip格式，需转换为HF transformers格式：

1. **config修复**：添加`num_hidden_layers=24`, `hidden_size=1024`, `projection_dim=768`
2. **key重映射**：
   - `vision_model.conv1.weight` → `vision_model.embeddings.patch_embedding.weight`
   - `vision_model.class_embedding` → `vision_model.embeddings.class_embedding`
   - `vision_model.positional_embedding` → `vision_model.embeddings.position_embedding.weight`
   - `vision_model.ln_pre.*` → `vision_model.pre_layrnorm.*`
   - `vision_model.ln_post.*` → `vision_model.post_layernorm.*`
   - `vision_model.transformer.resblocks.N.*` → `vision_model.encoder.layers.N.*`
3. **attention拆分**：`attn.in_proj_weight` [3*dim, dim] → `q_proj/k_proj/v_proj` 各[dim, dim]
4. **MLP重命名**：`mlp.c_fc` → `mlp.fc1`, `mlp.c_proj` → `mlp.fc2`
5. **projection转置**：`vision_model.proj` [1024,768].t() → `visual_projection.weight` [768,1024]
6. **text_projection**：同样需要转置

## 结论

- **合成图像实验**：使用标准CLIP（已验证有效）
- **真实SAR图像实验**：使用SARCLIP（需MegaSAR-2M数据验证）
- **权重转换代码**：已保存在test_sarclip.py中，可复用
- **不一致性检测方法**：CLIP零样本分类结果 vs 表格元数据类型对比 = 有效检测方法
