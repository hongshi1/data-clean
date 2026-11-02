# 78 四模块推进：KB修复/违例seed/提纯分档/覆盖检测器

日期：2026-10-29 | 全部落地并验证 | 77号后续

---

## 一、KB表面词修复（P0，30分钟）

```text
修复: knowledge/srs_kb.json availability的同义词误含「可靠性」
     (reliability≠availability, 68号审计12对假候选的根因)
验证: 重跑原子候选 → availability的58个假候选全部消失
     (978→920对, 参数分布只剩clock/resolution/response_time)
```

## 二、违例评测集导入DB（P1，三态演示seed）

```text
新增: tools/seed_violations_to_db.py(幂等导入17真实违例→doc04)
改造: verify.py证据优先级 = 结构化JSON(seed) > O1召回 > 文本blob
     (_stored_json_evidence解析冻结格式)
结果: doc04 = 17违例全部使用frozen证据
```

## 三、提纯按证据来源分档（73号教训的工程落地）

```text
引擎池: _get_engine(purify) 双档
  frozen/curated证据 → purify=False(73号: 精选池删块丢1例needed)
  recalled召回证据   → purify=True (71号: NLI直判+29.4pt)
结果: doc04违例 15/17 → 16/17(94.1%, 恢复最优配置)
```

## 四、覆盖差异型检测器（P1，69号类型学补全）

```text
新增: algorithms/consistency/coverage_detector.py(纯函数)
  平行表 = 同文档不同章节且共享scope键≥2+共享实质字段≥1
  每共享scope行: ①字段覆盖集差异 ②同字段取值(枚举子集/冲突)
  降噪: 索引列(序号/章节号)跳过 + 纯数字值跳过 + 异构表不配对
  子集语义: 长侧含枚举分隔符才判gap("1600(DVI)、1280(VGA)"⊇"1280(VGA)");
           name⊂user_name判冲突(标识差异)
工具: tools/build_coverage_findings.py
全量: 1207表→3481平行对→876 findings(694覆盖缺口+182取值冲突)
真实发现样例: doc12「用户名标识 name vs user_name」(标识不一致)
            doc14「数据组成 源用户IP vs 用户IP」(字段命名漂移)
测试: tests/test_coverage_detector.py(7个, doc10/12真实案例fixture)
```

## 五、gold定稿就绪检查（P0 #2, 工具就绪/待人工）

```text
tools/finalize_gold.py 就绪:
  kappa  双人标注一致性(κ/Jaccard)+分歧仲裁清单
  export gold_v1→qa_frozen/scene1_gold_v1.jsonl(与silver同协议)
待人工: 两轮标注→κ≥0.6→仲裁→export→MANIFEST注册
      (此步无法由系统替代)
```

## 六、当前系统全貌（一键运行）

```text
后端(8300): POST /api/verify/{doc} → 三态核验
  证据链: frozen(seed违例,16/17 refute) / recalled(召回+提纯)
        / blob(存量文本适配)
  离线: coverage_findings(876) + atom_candidates(920) + 108评测集
```

## 七、质量状态汇总

| 指标 | 值 |
|---|---:|
| doc04违例refute查全(后端服务) | **16/17 (94.1%)** |
| doc01/02 demo QA(召回证据) | 4 support / 33.3%→真实判定 |
| 覆盖差异findings(新检测器) | 876(含真实标识/字段漂移) |
| 原子候选假阳性(KB修复后) | availability归零 |
| 全量回归测试 | 47新增+全过, ruff零报错 |
