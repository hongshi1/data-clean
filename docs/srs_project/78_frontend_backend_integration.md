# 前后端集成指南——CascadeVerify收敛框架的对接方案

> v1.0 | 2026-10-30 | 配套: 77号总汇 | 代码: algorithms/consistency/verifier.py + server/main.py
> 读者: 要把一致性校验嵌入自己前后端的工程师

---

## 1. 收敛后的算法框架（终态）

所有演化后的**唯一稳定入口**——前后端只需要认识这一个类：

```python
from algorithms.consistency.verifier import CascadeVerifier

verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
result = verifier.verify(question, answer, evidence)
# result.verdict:        "support" | "refute" | "not_in_evidence"
# result.evidence_refs:  证据定位(块ID+语句号, 前端可点击)
# result.check_items:    命中的检测项ID(TERM-03/PARAM-01/GJB-05...)
# result.rationale:      判定理由(中文, 直接可读)
# result.latency_ms:     耗时
```

**两个旋钮**：

| 旋钮 | 取值 | 含义 | 延迟 | 成本 |
|---|---|---|---|---|
| preset | `fast` | L0+L1确定性专家族 | **8ms/条** | 零模型零LLM |
| | `standard` | +L2本地NLI | 120ms/条(首次加载模型35s) | 本地GPU/CPU |
| | `full` | +L3级联仲裁(仅refute候选走LLM) | ~650ms均摊 | LLM调用(15/91条) |
| scene | `srs_scene1` | 04号场景 | — | — |
| | `doc01`/`doc06`/... | onboarding生成的场景 | — | — |

**依赖清单**（部署需要的全部东西）：
```
代码: algorithms/ + config/ner_lexicons/ + config/rulepacks/ + (server/可选)
模型(仅standard/full): models/nli/egt_finetuned_v2/ (278M, 本地)
LLM(仅full): .env里的GLM端点密钥(走llm_client缓存)
数据: 无(证据由调用方传入)
```

---

## 2. 三种集成模式

### 模式A: Python库直接嵌入（后端是Python时首选）

```python
# 你的FastAPI/Flask/Django服务里
from algorithms.consistency.verifier import CascadeVerifier

app_state = {"verifier": None}

@app.on_event("startup")          # 启动时构造, 模型预热
async def startup():
    app_state["verifier"] = CascadeVerifier(preset="standard")

@app.post("/your/answer-check")
async def check(q: str, a: str, ev: list[dict]):
    result = app_state["verifier"].verify(q, a, ev)
    return {"verdict": result.verdict, "refs": result.evidence_refs}
```
- 同进程零网络开销；fast档8ms/条可同步调用
- **线程安全注意**: 模块级单例verifier可复用(内部无共享可变状态, NLI模型模块级缓存)；多worker部署时每个worker各加载一次模型(35s×worker数)

### 模式B: REST微服务（语言无关, 推荐）

现有`server/main.py`已就绪, 启动:
```powershell
uvicorn server.main:app --port 8300
# 或 python server/main.py
```
核心端点`POST /api/verify`（完整契约见§3）。

### 模式C: 异步批量（数据集级任务）
```python
verifier = CascadeVerifier(preset="full")
results = verifier.verify_batch(records)      # 内部复用引擎
# fast档吞吐128条/秒; full档约91条/10分钟(LLM节流)
```
大批量建议: 队列worker常驻(模型只加载一次) + `verify_batch`。

---

## 3. REST API契约（POST /api/verify）

### 请求

```json
{
  "instance_id": "qa-0001",
  "question": "修改数据功能支持哪些设备",
  "answer": "支持在桌面、平版和平板设备上运行",
  "context_freeze_id": "freeze-v1",
  "evidence": [
    {
      "evidence_id": "ev-000030",
      "text": "修改数据记录信息 用例名称：… 需求重用：平板、桌面",
      "source_type": "table",
      "source_ref": {"doc_id": "04", "section": "3.2", "page": 1,
                      "block_id": "block-000030"},
      "scope_id": "",
      "completeness": "open",
      "completeness_proof": ""
    }
  ],
  "preset": "fast",
  "scene": "srs_scene1"
}
```

字段说明:
- `evidence`**: 冻结证据块数组——检索阶段(你们的上游)负责给什么就传什么; 本服务不检索
- `source_type`: text/table/figure/trace/rule/other
- `completeness`: open(缺≠矛盾)/closed(需proof)/unknown
- `preset`/`scene`: 可选, 默认fast/srs_scene1(向后兼容)

### 响应（完整VerificationResult）

```json
{
  "instance_id": "qa-0001",
  "verdict": "refute",
  "status": "ok",
  "rationale": "多出疑似错字成员『平版』→平板; 该行需求重用={平板,桌面}…",
  "claim_results": [
    {
      "claim_id": "qa-0001-c01",
      "claim_text": "支持在桌面、平版和平板设备上运行",
      "verdict": "refute",
      "check_item_candidates": ["TERM-03"],
      "evidence_refs": ["ev-000030#s3"],
      "rationale": "…",
      "method": "enum_join_registry",
      "confidence": 0.9
    }
  ],
  "evidence_chain": [/* cited证据块原文 */],
  "diagnostics": [],
  "context_integrity": "unknown"
}
```

前端最常用字段: `verdict` / `rationale` / `claim_results[].evidence_refs`(点击定位) / `check_item_candidates`(归因标签)。

### 错误码
- 422: 参数校验(instance_id空/evidence_id重复/缺source_ref等, 消息可读)
- 200+`status:"partial"`+diagnostics: 判定完成但部分claim未解(语义层NIE)

---

## 4. 后端集成要点

### 4.1 服务启动与模型加载
```python
# 惰性(默认): 首次verify触发NLI加载(35s) —— 冷启动首请求慢
# 预热(推荐): startup时发一条dummy verify
verifier.verify("预热", "是", [最小evidence])   # standard/full建议
```
- fast档无需预热(1.6s import)
- GPU: torch自动检测; 无GPU自动CPU(standard延迟×3~5)
- LLM(full档): `tools/ai_config.py`读`.env`; 响应缓存落`data/gjb_438c/llm_cache/`(同问同答零成本重放)

### 4.2 场景配置管理（接新文档）
```
你们的文档 → python tools/onboard_new_document.py --doc NN
  → 自动生成 config/ner_lexicons/docNN_scene.json + config/rulepacks/docNN_onboard_v1.json
  → 请求里 scene="docNN" 即生效(服务端verifier缓存自动扩展)
```
注意: onboard生成的配置带`_needs_review`标记项, 建议人工过目后去掉标记。

### 4.3 并发与扩缩
- 单worker: verifier线程安全可复用; fast档8ms/条≈单核120QPS
- 多worker(uvicorn --workers N): 每worker独立模型内存(278M×N)
- full档的LLM节流: 请求去重靠缓存键(prompt哈希), 同答案重复校验零API成本

### 4.4 部署清单
```
requirements.txt核心: fastapi/uvicorn/pydantic + torch+transformers(standard/full) + z3-solver
目录: algorithms/ config/ models/nli/egt_finetuned_v2/(standard/full) .env(full)
启动: uvicorn server.main:app --port 8300 --workers 1
健康: GET /api/docs (无模型依赖, 可做liveness)
```

---

## 5. 前端集成要点

### 5.1 三态展示模式
```
verdict → 徽章: support=绿✓(证据支持) | refute=红✗(证据反对) | NIE=灰?(不可判定)
语义提示(用户教育): NIE≠正确 也≠错误 —— "当前证据无法判定, 建议补充检索或人工复核"
```

### 5.2 证据定位交互（本系统的差异化能力）
```
claim_results[].evidence_refs = ["ev-000030#s3"]
  → 前端映射: ev-000030=证据块(高亮整块) + #s3=块内第3条语句(滚动+下划线)
  → 点击claim → 跳转并高亮对应证据 → 用户看到"机器凭什么这么判"
```
建议: 左侧answer分解的claim列表(每条带verdict徽章) + 右侧证据面板(ref高亮联动)。

### 5.3 归因标签
`check_items`(TERM-03/LOGIC-02/GJB-05…) → 映射到40项检测体系的中文名, 展示为标签: `[枚举集不匹配]`。

### 5.4 延迟预算与交互
- fast(8ms): 同步请求, 无loading态
- standard(120ms): 同步, 短loading
- full(650ms均摊/3-5s最重): 同步+loading, 或对被升级实例做二次请求展示"仲裁中→完成"

---

## 6. 联调检查单

| # | 检查 | 命令/方法 |
|---|---|---|
| 1 | 服务健康 | `GET /api/docs` 返回文档列表 |
| 2 | fast档三态 | POST一条support/refute/NIE样例(§3的json) |
| 3 | 证据定位 | 检查claim_results[].evidence_refs与传入evidence_id对应 |
| 4 | 参数校验 | 空instance_id→422可读错误 |
| 5 | preset切换 | 同一请求preset=standard, 首次慢(模型加载)后续120ms |
| 6 | scene切换 | scene="doc01" + 01号证据, ID族ZZSJHQZHFW命中 |
| 7 | LLM缓存(full) | 同请求发两次, 第二次latency_ms骤降 |
| 8 | 批量 | verify_batch或循环POST, fast档≈120QPS单核 |

---

## 7. 边界与注意事项

1. **本服务不做检索**: evidence由上游(你们的检索/上下文关联模块)提供并冻结——检索质量决定判定上界(表1的R@1)
2. **NIE的开放世界语义**: 证据completeness=open时"查不到"判NIE不判refute——前端文案必须区分, 否则用户会误解
3. **silver精度参考**: 当前判定质量=91QA acc 0.912/refute精确率1.000(级联); gold标注后终版数字以runs为准
4. **refute的杀伤性**: 建议业务侧对refute设置人工确认环节(误杀正确答案代价最高——当前精确率1.000但样本仅8条refute)
5. **场景配置质量**: onboard自动归纳的配置有23项_needs_review——生产使用前人工校订
