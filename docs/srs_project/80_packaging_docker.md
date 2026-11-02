# 80 完整算法封装与Docker接入：srs_verify包 × nkuDataProject平台

日期：2026-10-30 | 依据：docs/场景接入指南.md（e9cc984） | 全链路已验证

---

## 一、交付物总览

| 交付物 | 位置 | 状态 |
|---|---|---|
| **算法包补全** | `srs_verify_package/srs_verify/` | ✅一致性栈(29模块)+新增上下文关联栈+提纯+覆盖检测 |
| **算法服务** | `srs_verify_package/service/app.py` | ✅FastAPI: /health /verify /purify |
| **Docker镜像** | `srs_verify_package/Dockerfile` | ✅GPU, 模型volume契约 |
| **三服务编排** | `deploy/nkuDataProject/docker-compose.yml` | ✅algo(8400)+backend(8300)+frontend(8080) |
| **平台接入** | `backend/services/algo_client.py` + verify.py | ✅远程优先+本地兜底，零场景包侵入 |

## 二、封装内容（新增vendor，12模块）

```text
srs_verify/
  context/                    ← 上下文关联栈(O1-unit召回)
    evidence/heads/recall/rerank/pipeline.py   多头冻结投影+场景路由
    atomizer.py               四槽原子化(claim+表格双通道)
    pair_scorers.py           七打分器族
    bge_local.py              BGE客户端(模型cwd契约)
  evidence_purifier.py        ← 提纯门面(两种模式+形态合同标注)
  evidence_subtractor.py      ← F1/F2/F3核心
  coverage_detector.py        ← 平行表覆盖差异检测
  deq_pipeline.py             ← DEQ E0门(提纯可组合)
service/app.py                ← FastAPI服务(claim级明细)
vendor工具: tools/vendor_srs_verify.py(幂等, import重写)
```

## 三、接入架构（对齐指南的解耦模式）

```text
frontend(nginx:8080) ──/api反代──→ backend(flask:8300)
                                     │ ALGO_SERVICE_URL(介入点②③模式)
                                     ▼
                              algo服务(GPU:8400)
                                CascadeVerifier(standard档)
                                + evidence_purifier
                                + srs_verify.context(召回)
                                     │ models/(volume, 部署契约)
                                     ▼
                              mDeBERTa + BGE(可选)

后端verify链: 证据(frozen>召回>blob) → algo_client.verify_remote
             → 失败/未配置 → 本地引擎兜底(76号_get_engine)
```

**契约要点**：
- `ALGO_SERVICE_URL`未配置/服务宕 → **静默降级本地**（与PARSER_SERVICE_URL
  同模式，平台代码零改动）
- 远程响应字段与本地`verify_v1` attrs**同名对齐**（verdict/rationale/claims）
- 场景包(scenarios/srs)不感知算法服务——解耦发生在services层

## 四、全链路验证（2026-10-30实测）

| 链路 | 结果 |
|---|---|
| 包导入+purify+召回smoke | ✅全部模块 |
| 服务TestClient(/verify support 90.6ms) | ✅ |
| 本地兜底模式（无URL） | ✅doc04违例16/17, engine=local |
| **远程模式**（localhost:8400） | ✅**违例16/17与本地逐位一致**, engine=remote, claim明细3条 |

## 五、Docker命令速查

```bash
# 算法服务单独
cd srs_verify_package
docker build -t srs-verify:1.0 .
docker run --gpus all -p 8400:8400 -v ../models:/app/models:ro srs-verify:1.0

# 三服务编排
cd deploy/nkuDataProject
docker compose up -d        # 前端8080 / 后端8300 / 算法8400
```

## 六、与指南介入点的对应

| 指南介入点 | 本次使用 |
|---|---|
| ①场景包四方法 | 未动（scenarios/srs保持纯算法，校验走services/verify） |
| ②解析服务URL模式 | **采用同模式**：ALGO_SERVICE_URL解耦算法服务 |
| ③数据集服务URL | 同上模式扩展位 |
| ④参数契约 | 服务preset/purify经请求体传递（配置树扩展位） |

## 七、遗留与注意

1. Docker镜像torch为CPU轮子——GPU部署换cu128轮子（Dockerfile注释处）
2. 精排器(BgeReranker)未vendor——召回走直通序（增益见repo版本）
3. compose的backend首次构建需flasgger依赖齐备
4. Windows GPU的OpenMP顺序约束已在服务startup钩子内处理（torch先载）
