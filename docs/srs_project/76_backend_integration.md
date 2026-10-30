# 76 算法栈与前后端集成：三态核验服务

日期：2026-10-29 | 实现：`deploy/nkuDataProject/backend/services/verify.py` + 2端点 | 已端到端验证

---

## 一、集成架构

```text
┌─前端(index.html)──────────────────────────────────────┐
│  校验总览页                    一致性校验规则管理页      │
│  [发起三态核验]按钮 → POST /api/verify/{doc}           │
│  轮询 → 渲染三态徽章+claim明细+提纯审计                 │
└──────────────────────┬────────────────────────────────┘
                       │ 统一信封{ok,data,error}
┌─后端(Flask :8300)────▼────────────────────────────────┐
│ app.py(纯HTTP路由)                                     │
│   POST /api/verify/{doc}      → job_id(异步,同源串行)   │
│   GET  /api/verify/status/{id}→ 三态结果               │
│ services/verify.py(本集成, 与checks.py同构)            │
│   ① QaPair(question,answer,evidence) ← SQLite          │
│   ② 证据适配: 文本evidence → 块(build_qa_input契约)    │
│   ③ 算法栈调用(仓库根sys.path挂载):                    │
│      QAConsistencyModule                                │
│        use_subtractor=True  ← 证据提纯(F1作用域+F3形态) │
│        L1专家通道(entity/E1/id_join/...)                │
│        L2 NLI残差(mDeBERTa本地GPU, 惰性单例)            │
│      → 三态裁决(support/refute/not_in_evidence)        │
│   ④ 落库: check_status(映射pass/fail/warn)             │
│           attrs.verify_v1(verdict+claims+提纯审计)     │
└─────────────────────────────────────────────────────────┘
```

## 二、API契约（前端对接用）

### 发起核验

```text
POST /api/verify/{doc_num}          # doc_num=qa_sources.source_id, 如"01"
→ {"ok":true, "data":{"job_id":"a1b2c3...", "status":"queued"}}
```

### 轮询结果

```text
GET /api/verify/status/{job_id}
→ {"ok":true, "data":{
    "status": "done",
    "result": {
      "doc": "01", "n": 4,
      "summary": {"support":0, "refute":0, "not_in_evidence":4},
      "results": [
        {"qa_id":"qa_0008", "question":"...",
         "verdict":"not_in_evidence",      ← 三态
         "status":"warn",                  ← 映射: pass/fail/warn
         "rationale":"标识符未在冻结context命中...",
         "claims":[
           {"claim_text":"PZXQ-GN-JMJCKJ-JMKF-KFGCSC",
            "verdict":"not_in_evidence",
            "method":"l0_entity_detector:TERM-07",  ← 通道归因
            "confidence":1.0,
            "rationale":"...", "evidence_refs":[...]}],
         "purifier":{"summary":"subtractor_removed_1_of_1_blocks"},
         "diagnostics":[...]}]}}}
```

### 已有数据回显（/api/qa自动带出）

核验完成后`qa_pairs.attrs.verify_v1`持久化，前端问答列表接口无需改动
即可读取`{verdict, claims, purifier}`。

## 三、前端接入片段（校验总览页）

```javascript
async function runVerify(docNum) {
  const r = await fetch(`/api/verify/${docNum}`, {method: 'POST'});
  const {data} = await r.json();
  if (!data) return;
  // 轮询
  const timer = setInterval(async () => {
    const s = await (await fetch(`/api/verify/status/${data.job_id}`)).json();
    if (s.data.status === 'done') {
      clearInterval(timer);
      renderVerify(s.data.result);   // 渲染三态结果
    } else if (s.data.status === 'error') {
      clearInterval(timer);
      alert(s.data.error);
    }
  }, 2000);
}

function renderVerify(result) {
  // 徽章色: support绿/refute红/not_in_evidence黄
  const color = {support:'#52c41a', refute:'#f5222d',
                 not_in_evidence:'#faad14'};
  for (const r of result.results) {
    console.log(r.qa_id, r.verdict, color[r.verdict]);
    // → 徽章 + claims表格(claim/判定/通道/理由) + 提纯审计行
  }
}
```

## 四、运行与验证

```bash
cd deploy/nkuDataProject/backend
set DEV_DB=sqlite && python app.py     # http://127.0.0.1:8300/docs
# Swagger: POST /api/verify/01 → job_id → GET /api/verify/status/{job_id}
```

端到端已验证（2026-10-29）：doc01(4 QA)与doc02(8 QA)全链跑通，
三态判定+claim通道归因+提纯审计落库（qa_0008: warn/NIE + 2 claims +
TERM-07实体通道触发）。demo库证据较薄→NIE为主＝"证据不足"第三态的
诚实行为（宁缺勿假）。

## 五、收敛算法栈→服务的映射

| 服务组件 | 算法资产 | 文档 |
|---|---|---|
| 证据提纯 | `evidence_purifier`(evidence模式: F1+F3) | 74号 |
| 三态裁决 | `QAConsistencyModule` | qa_module.py |
| L1专家 | entity/E1/id_join/enum/coverage通道 | 内置 |
| L2 NLI | mDeBERTa本地(GPU惰性单例+推理锁) | nli_local.py |
| 证据适配 | 文本evidence→块(检索证据接入时替换) | verify.py |

## 六、扩展点

```text
1. ✅证据升级(已落地, 2026-10-29): O1-unit召回接入 —
   services/recall_adapter.py: elements→URE(表行/句级units)
   →EvidenceRecallPipeline(BGE+精排, 每doc缓存)→top-10块
   verify(use_recall=True)默认启用, 召回失败回退存量evidence
   质变实测: doc01 4QA→2support, doc02 8QA(全NIE)→2support+6NIE
   claim的evidence_refs指向元素id(el-428式), 前端可回跳原文
2. 违例评测集直连: violation_evalset的108实例已有结构化证据,
   可作为seed数据导入qa_pairs(演示完整三态: refute/support都有)
3. L3升级: use_cascade=True开启LLM复检(需llm_client缓存配置)
4. 批量核验: 循环start(doc)遍历16文档; 引擎锁串行保稳
```
