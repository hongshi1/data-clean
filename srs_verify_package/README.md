# srs-verify: GJB SRS答案一致性校验

对"给定问题+回答+冻结证据"执行三态一致性判定(support / refute / not_in_evidence)，
面向GJB 438C格式SRS文档的问答式答案核验。核心是一个级联校验器
`CascadeVerifier`：L0/L1确定性专家通道(标识符/数值区间/枚举/时序/追踪/GJB规则)
先行裁决，残差claim再按档位交给L2本地NLI或L3 LLM。

## 安装

```bash
pip install ./srs_verify_package          # 从目录安装
# 或: pip install srs_verify-0.1.0-py3-none-any.whl
```

核心(fast档)**零第三方依赖**——纯stdlib+正则；torch/transformers/z3/jieba
全部惰性导入，用到才import。开发使用(不安装)：

```bash
cd srs_verify_package
python -c "from srs_verify import CascadeVerifier; print('ok')"
```

## 快速开始(3行代码)

```python
from srs_verify import CascadeVerifier

verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
result = verifier.verify(
    question="连接池配置用例的项目唯一标识符是什么？",
    answer="PZXQ-GN-LJCGL-LJCPZ",
    evidence=[{"text": "3.2.5.1 连接池管理-连接池配置（PZXQ-GN-LJCGL-LJCPZ）"}],
)
print(result.verdict)          # support
print(result.evidence_refs)    # ('facade-1-ev-000',)
```

返回`VerdictResult`：`verdict` / `evidence_refs`(引用的证据id并集) /
`check_items` / `rationale` / `diagnostics` / `latency_ms`。

包内自检(3条样例覆盖三态)：

```bash
cd srs_verify_package && python -m srs_verify.smoke_test
```

## 三档位(preset)

| preset | 通道 | 依赖 | 延迟(每条) | 说明 |
|--------|------|------|-----------|------|
| `fast` | L0/L1确定性专家 | **零依赖** | ~8ms | 确定性可复现，推荐默认 |
| `standard` | +L2本地NLI残差 | `torch>=2.0`+`transformers>=4.40`，需NLI模型目录 | 首次~35s模型加载，之后~120ms | 无LLM调用；残差claim由微调mDeBERTa判定 |
| `full` | +L3级联仲裁 | standard依赖 + `.env`/环境变量(GLM端点) | 最贵 | L2的refute候选升级到LLM复核，走磁盘缓存 |

```bash
pip install "srs-verify[standard]"     # standard档依赖
pip install "srs-verify[full]"         # full档依赖(含python-dotenv)
```

**standard档NLI模型**：模型目录不随包分发，需自备(微调mDeBERTa checkpoint)。
路径优先级：构造参数`nli_model_path=...` > 环境变量`SRS_VERIFY_NLI_MODEL` >
默认`models/nli/egt_finetuned_v2`(相对运行目录)。模型缺失时不崩溃——
残差claim保守判NIE并在`diagnostics`给出`nli_residual_model_unavailable`。

**full档LLM端点**：在运行目录放`.env`(`KEY=VALUE`行)或设环境变量：

```
GLM_KEY=...   GLM_URL=...   GLM_MODEL=...
KIMI_KEY=...  KIMI_URL=...  KIMI_MODEL=...
```

URL/MODEL有缺省值(智谱官网/moonshot)，KEY缺失只在真正发起调用时报可读错误。
响应缓存落盘于`SRS_VERIFY_LLM_CACHE`(环境变量)>运行目录`llm_cache/`>
系统临时目录回退(运行目录无写权限时)。

**惰性依赖触发条件**(用到再装)：`z3-solver`——numeric_z3专家的数值约束
联立求解(`pip install z3-solver`；未装时该专家按诊断降级为
`expert_numeric_z3_failed:ImportError`，其余专家照常运行)；`jieba`——仅
当直接调用`srs_verify.ner_lexicon.tokenize()`做词典分词时。单位族资产
`configs/srs_kb.json`随包分发(numeric_z3专家消费)。

## 请求格式(evidence JSON schema)

`verify(question, answer, evidence)`的evidence是dict列表，两种形态：

**极简**(缺省字段自动补全，适合快速试用)：

```json
[{"text": "表39: 连接池配置 PZXQ-GN-LJCGL-LJCPZ"}]
```

**完整**(冻结QA格式，字段与语义)：

```json
[{
  "evidence_id": "ev-001",
  "text": "<table>...</table> 或任意文本块",
  "source_type": "text",
  "source_ref": {
    "doc_id": "04数据统一访问服务软件需求规格说明-终稿",
    "section": "3.2 CSCI能力需求",
    "page": 1,
    "block_id": "block-000030",
    "row_id": "",
    "region_id": ""
  },
  "scope_id": "doc:block-000030",
  "completeness": "open",
  "completeness_proof": "Only this source block was frozen.",
  "extraction_method": "...",
  "extraction_confidence": 1.0
}]
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `evidence_id` | 是 | 证据块唯一id(结果`evidence_refs`引用它) |
| `text` | 是 | 证据文本(表格可为HTML/纯文本) |
| `source_type` | 是 | `text`/`table`/`figure`/`trace`/`rule`/`other` |
| `source_ref` | 是 | 溯源指针(`doc_id`必填非空) |
| `scope_id` | 是 | 作用域标识(如`doc:block-xxx`) |
| `completeness` | 否 | `open`/`closed`/`unknown`；`closed`须带`completeness_proof`，否则按open处理并记诊断 |

另有`verify_record(record)`(整条冻结QA记录，含`instance_id`/`context_freeze_id`)、
`verify_batch(records)`、`verify_qa_input(QAInput)`(返回全字段
`VerificationResult`，供需要序列化claim级明细的调用方)。

## 三态语义(开放世界)

- `support`——冻结证据**明确蕴含**answer的全部原子claim；
- `refute`——冻结证据与answer某claim**明确矛盾**(如同主体数值区间互斥)；
- `not_in_evidence`(NIE)——证据**无法判定**。

开放世界假设：**证据中没有 ≠ 文档中不存在**。缺失的内容(未列出的子功能、
效果性表述、解释性扩展)只能判NIE，绝不能作为refute的依据。聚合规则：
refute > NIE > support(任一claim为NIE则整体不为support；refute最优先)。

## 证据定位

`VerdictResult.evidence_refs`是被引用证据`evidence_id`的排序并集；
`claim_results`(经`verify_qa_input`的完整结果)里每个ClaimResult还带
`evidence_refs`/`rationale`/`method`/`confidence`，可精确到claim级溯源；
`evidence_chain`按引用顺序给出完整证据对象。

## 场景配置(如何换文档)

场景 = 词典(NER词表/ID模式) + 规则包(表型签名/模板正则/阈值)的组合：

1. 准备两份JSON(可参照`srs_verify/configs/ner_lexicons/srs_scene1.json`
   与`srs_verify/configs/rulepacks/srs_gjb_v1.json`的结构)；
2. 放入`srs_verify/configs/ner_lexicons/<你的场景>.json`与
   `srs_verify/configs/rulepacks/<你的规则包>.json`；
3. 在`SCENES`(`srs_verify/verifier.py`)注册一行
   `"<场景名>": ("configs/ner_lexicons/<你的场景>.json", "configs/rulepacks/<你的规则包>.json")`；
4. `CascadeVerifier(scene="<场景名>")`。

规则包JSON里的`gjb_rule_library_path`相对`srs_verify/configs/`解析
(默认`configs/gjb_rules.json`=GJB 438C规则库120条，含SRS适用规则)。
注意：场景切换是模块级默认切换——多个CascadeVerifier实例并存时，
最后构造的场景占有模块级默认。

## 常见问题

- **"nli_residual_model_unavailable"诊断**——standard/full档NLI模型路径
  无效：检查`SRS_VERIFY_NLI_MODEL`或默认目录`models/nli/egt_finetuned_v2`。
- **"llm_residual_call_failed"诊断**——full档LLM调用失败(KEY缺失/网络)，
  已按保守NIE降级，不影响其余通道。
- **torch/transformers/z3/jieba没装会怎样**——torch/transformers(jieba同)
  完全不触发；z3缺失时numeric_z3专家以`expert_numeric_z3_failed:ImportError`
  诊断降级(数值区间类判定仍由per-claim数值通道承担)，其余专家照常。
- **purify参数**——证据提纯属研究仓库模块(`evidence_purifier`)，本分发包
  未随附；`purify=True`会在首次verify时报ImportError。
- **Windows乱码**——控制台输出中文前设`$env:PYTHONUTF8='1'`(PowerShell)。
