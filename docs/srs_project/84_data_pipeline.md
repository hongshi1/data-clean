# 84 数据处理管线全链路：从原始.doc到一致性校验

日期：2026-11-01 | 全链路盘点完成 | 入口：`tools/run_pipeline.py`

---

## 一、数据流全景图（一张图）

```
16份GJB SRS .doc (44.5MB)
│
├─[A] MinerU链 ──────────────────────────────────────────
│   .doc → LibreOffice → .docx → MinerU
│   → mineru_standard/<doc>/office/
│     (md + content_list.json + 5辅助json + fig*.png)
│   工具: tools/srs_mineru_parse.py
│
├─[B] textutil双源 [冻结, macOS产物] ─────────────────────
│   .doc → dual_source/*.html (16份)
│   状态: 不可复现(无脚本), 按冻结ParserArtifact处理
│
├─[C] Visio链 ───────────────────────────────────────────
│   .doc → LibreOffice → .docx → OLE2解包 → Visio XML
│   → anchor_v3/anchors_v3.json (373图/5165节点/2557边)
│   工具: tools/archive/.../m0_anchor_extract_v3.py
│   状态: 脚本已归档, 数据可用(canon)
│
├─[D] QA合成(外部输入) ──────────────────────────────────
│   data_assets/srs_qa_final.json (6189 QA)
│   pair_dataset_canonical/train.jsonl (2813对)
│   qa_frozen/scene1_qa_frozen_v1.jsonl (91 QA)
│   状态: 源工具已归档, 按冻结数据集处理
│
▼ ═══════════════════════════════════════════════════════
  [P2] structured_corpus_v1 (中枢, 27,473对象)
  工具: tools/build_structured_corpus.py
  输入: A + B + C + D
  产出: claims 11,869 / tables 1,207 / nodes 5,165
        / requirements 2,451 / sections 1,444 / qa 6,189
        / observations 3,771 / images 381 / diagrams 373
        / edges 2,557 / frozen_qa 91 / training_pairs 2,813
▼ ═══════════════════════════════════════════════════════
  [P3] 特征层 (多路扇出)
  ├─ feature_matrix_v1     (7类特征, 12,517+21,650+1,207+...)
  │  工具: tools/build_feature_matrix.py
  ├─ feature_matrix_v2     (句span/否定/引用, 2,552+1,207+1,537)
  │  工具: tools/build_feature_matrix_v2.py
  ├─ semantic_features_v2  (实体分类20,133 / 泳道373 / 接口69)
  │  工具: tools/build_semantic_features_v2.py
  ├─ visio_features_v2     (节点5,165 / 边2,557, 对齐率100%)
  │  工具: tools/build_visio_features_v2.py
  └─ feature_snapshot_v1   (BGE 27,473×1024维, 118MB)
     工具: tools/build_feature_snapshot.py
▼ ═══════════════════════════════════════════════════════
  [P4] 候选发现层
  ├─ evidence_graph_v1 → v2 (21,650链接 → 4,969silver → 408items)
  │  工具: build_evidence_graph.py → build_evidence_graph_v2.py
  ├─ atom_candidates_v1   (claims原子292 + 表原子281 → 1,175+1,169对)
  │  工具: build_atom_conflict_candidates.py + build_table_atoms.py
  └─ coverage_findings_v1 (3,481平行表对 → 876 findings)
     工具: build_coverage_findings.py
▼ ═══════════════════════════════════════════════════════
  [P5] 评测资产层
  ├─ localization_gold    (108实例: 91QA+17违例)
  │  工具: build_localization_gold_template.py + build_violation_evalset.py
  ├─ GLM标注              (204对, κ=0.7062)
  │  工具: annotate_with_glm.py
  └─ scope_binder         (学习器F1=0.837)
     工具: train_scope_binder.py
▼ ═══════════════════════════════════════════════════════
  最终消费: algorithms/consistency/ (三态裁决)
           algorithms/context_linking/ (召回+原子化+打分)
           srs_verify_package/ (分发包)
           deploy/nkuDataProject/ (前后端平台)
```

## 二、Pipeline封装

统一入口: `tools/run_pipeline.py`

```bash
python tools/run_pipeline.py --from raw    # 全量: .doc→最终数据
python tools/run_pipeline.py --from corpus # 从结构化语料开始
python tools/run_pipeline.py --from features # 从特征层开始
python tools/run_pipeline.py --list        # 列出所有步骤和状态
python tools/run_pipeline.py --dry-run     # 只显示计划不执行
```

## 三、冻结资产声明

| 资产 | 状态 | 原因 |
|---|---|---|
| dual_source/*.html | 冻结 | macOS textutil产物, Windows不可复现 |
| srs_qa_final.json (6189) | 冻结 | 源工具easydataset_pipeline.py已归档 |
| pair_canonical/train (2813) | 冻结 | 同上 |
| anchor_v3/anchors_v3.json | 冻结 | 生成脚本已归档, 数据可用 |
| mineru_standard/ | 可复现 | Windows+MinerU可重跑 |

## 四、已识别的缺口

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | 语料代次漂移 | evidence_graph_v1/v2建在旧语料上 | P3统一以corpus manifest为锚 |
| 2 | textutil不可复现 | Windows上无法重跑双源解析 | 已冻结, 无需修复 |
| 3 | anchor_v3脚本归档 | 主链路依赖存档脚本 | 需要时从archive回归 |
| 4 | gold标注0/108 | 评测置信度受限 | 人工或GLM补充 |
| 5 | AGENTS.md过时 | parsed_srs_dataset/不存在 | 已在本文档更正 |
