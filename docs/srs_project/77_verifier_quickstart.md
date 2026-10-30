# 77 CascadeVerifier：对外交付快速上手（v1收敛版）

日期：2026-10-29 | 入口：`algorithms.consistency.CascadeVerifier` | 21个回归测试

---

## 一、三行代码

```python
from algorithms.consistency import CascadeVerifier

verifier = CascadeVerifier(preset="fast")          # 或 standard / full
result = verifier.verify(
    question="连接池配置用例的项目唯一标识符是什么？",
    answer="PZXQ-GN-LJCGL-LJCPZ",
    evidence=[{"text": "3.2.5.1 连接池管理-连接池配置（PZXQ-GN-LJCGL-LJCPZ）"}])

print(result.verdict)   # support / refute / not_in_evidence
```

## 二、API

### 构造

```python
CascadeVerifier(
    preset="fast",        # fast=纯专家通道(0模型,~8ms)
                          # standard=+本地NLI残差(首次~35s加载,~120ms/条)
                          # full=+LLM级联仲裁(最准最贵)
    scene="srs_scene1",   # 场景=词典+规则包: srs_scene1/doc06/doc01
    nli_model_path=None,  # 自定义NLI checkpoint(默认注册表)
    purify=False,         # 证据提纯(F1作用域+F3指针删除, 带审计)
)
```

### 方法

| 方法 | 输入 | 输出 |
|---|---|---|
| `verify(q, a, evidence)` | 极简或完整证据 | VerdictResult |
| `verify_record(record)` | 冻结QA格式整条 | VerdictResult |
| `verify_batch(records)` | 批量 | list[VerdictResult] |
| `verify_qa_input(QAInput)` | 高级：完整输入对象 | 完整VerificationResult |

### 证据输入（两种格式等价）

```python
# 极简(推荐入门): 只需text, 其余自动补全
[{"text": "表39: 连接池配置 PZXQ-GN-LJCGL-LJCPZ"}]

# 完整(生产): 溯源字段全给
[{"evidence_id": "ev-1", "text": "...", "source_type": "text",
  "source_ref": {"doc_id": "04号SRS", "section": "3.2.5.1", "page": 12,
                 "block_id": "b219", "row_id": "", "region_id": ""},
  "scope_id": "04:b219", "completeness": "open"}]
```

### VerdictResult字段

```python
result.verdict        # 三态: support / refute / not_in_evidence
result.evidence_refs  # 被引用证据id并集(排序)
result.check_items    # 命中的检测项(TERM-07等, 40项taxonomy)
result.rationale      # 判定理由(claim级拼接, ≤500字)
result.latency_ms     # 延迟
```

## 三、判定语义（诚实设计）

```text
support          证据支持答案
refute           证据与答案矛盾
not_in_evidence  证据不足(宁缺勿假——不猜测)
```

## 四、部署注意

1. **Windows+GPU**：宿主进程请先`import torch`再import本包
   （OpenMP加载顺序约束，否则CUDA推理可能静默崩溃；门面已内置
   防护性import，但宿主先载numpy时需自行保证）
2. **standard/full档**需要本地模型：`models/nli/`（mDeBERTa系）
3. **fast档**零模型零GPU，纯确定性专家通道
4. 线程安全：多线程调用请外部串行（NLI推理非线程安全）
5. 依赖：见`requirements.txt`（fast档仅需stdlib+sqlalchemy无关项）

## 五、内部结构（使用者无需关心）

```text
CascadeVerifier(门面, 77号收敛)
  ├─ 证据规范化(极简→冻结格式)
  ├─ 证据提纯 purify=True → evidence_purifier(F1+F3, 74号)
  ├─ QAConsistencyModule(三态裁决引擎)
  │    ├─ L1专家通道(entity/E1/id_join/enum/Z3/coverage)
  │    ├─ L2 NLI残差(本地mDeBERTa, standard+)
  │    └─ L3 LLM级联仲裁(full)
  └─ VerdictResult收敛视图
```

## 六、Web服务接入

后端服务已就绪（76号）：`POST /api/verify/{doc}` + `GET /api/verify/status/{job}`
（`deploy/nkuDataProject/backend`，Swagger: http://127.0.0.1:8300/docs）

## 七、验证状态

```text
单元回归: 21个(facade 7 + purifier 7 + subtractor 7)
端到端:   tools/demo_verifier.py(silver标签一致)
真实违例: 17实例refute查全0.94(108实例评测, 73号)
```
