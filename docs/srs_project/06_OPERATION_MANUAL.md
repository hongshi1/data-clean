# 06 - 操作手册

## 环境准备

```bash
export WQ_API_KEY="n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
export KMP_DUPLICATE_LIB_OK=TRUE
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

## Step 1: 语法检测(不需要API)

```bash
python3 tools/srs_consistency_integrated.py
# 输入: data/srs_requirements/parsed/*.json (62个)
# 输出: data/srs_requirements/keie_output/conflict_report.json
# 结果: 213条L1语法 + 7条L2语义冲突
```

## Step 2: 参数抽取

```bash
# 方法A: KEIE知识增强IE(推荐, 不需要API)
python3 tools/srs_keie_pipeline.py --docs 0 --no-llm
# 输出: data/srs_requirements/keie_output/keie_results.json

# 方法B: LLM直接抽取(需要API, 精度最高)
python3 tools/srs_llm_extract.py --backend wq --docs 10
# 输出: data/srs_requirements/llm_output/llm_results.json
```

## Step 3: 图片-文本检测(需要多模态API)

```bash
python3 tools/srs_image_text_check.py
# 输入: data/srs_requirements/req/*.pdf
# 输出: data/srs_requirements/images_hd/full_results.json
# 包含: FloCA/DFD/VE/ChartVE/ModelCheck/TraceLLM 6个检测器
```

## Step 4: BERT-CRF训练(可选)

```bash
# 弱监督标注(生成银标准)
python3 tools/srs_bert_crf.py
# 输出: data/srs_requirements/bert_crf/silver_standard.json (4070句)

# 金标准标注(需要API)
# 见 tools/srs_llm_annotated_train.py
# 输出: data/srs_requirements/bert_crf/gold_standard_fixed.json (100句)
```

## Step 5: ReXCL复现(可选)

```bash
python3 tools/srs_rexcl.py
# 输出: data/srs_requirements/rexcl/extracted_sections.json (9337章节)

python3 tools/srs_rexcl_mlm.py
# 输出: data/srs_requirements/rexcl/mlm_comparison.json
```

## Step 6: 知识图谱构建

```bash
# 内嵌在离线实验脚本中, 运行后自动生成
# 输出: data/srs_requirements/knowledge_graph.json (1580节点/4800边)
```

## 关键文件路径

```
代码:
  tools/srs_consistency_check.py     # 正则版校验
  tools/srs_keie_pipeline.py         # KEIE流水线(主力)
  tools/srs_image_text_check.py      # 图片检测(6篇论文)
  tools/srs_llm_extract.py           # LLM抽取
  tools/srs_bert_crf.py              # BERT-CRF训练
  tools/srs_rexcl.py                 # ReXCL复现

数据:
  data/srs_requirements/req/         # 62个原始PDF
  data/srs_requirements/parsed/      # 62个解析JSON
  data/srs_requirements/bert_crf/    # 训练数据
  data/srs_requirements/keie_output/ # 检测结果

知识库:
  knowledge/srs_kb.json              # 23参数/374实体

文档:
  docs/srs_project/                  # 7个文档(本目录)
```
