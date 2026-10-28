# 74 证据提纯器：70-73号工作的收敛封装

日期：2026-10-28 | 模块：`algorithms/consistency/evidence_purifier.py` | 测试：14个

---

## 一、收敛了什么

```text
70号 设计(三agent方案) ─┐
71号 独立NLI实验(+29.4pt) ├→ evidence_purifier.py: 统一purify()入口
72号 基线对比(七方法)     │   + 两种模式 + 可组合DEQ门
73号 管线接入(教训×2)   ─┘   + PurificationConfig + 审计台账
```

## 二、API（唯一入口）

```python
from algorithms.consistency.evidence_purifier import PurificationConfig, purify

# 语句级(默认): F1+F2+F3 → kept为句/行级语句 — NLI直判消费方
pack = purify(question, answer, evidence_dicts)

# 证据级: 只删块不改写 → kept为原文本块 — 结构化消费方(专家通道/linearize)
pack = purify(question, answer, evidence_dicts,
              PurificationConfig(mode="evidence"))

# 证据级+DEQ无损门(73号实测: 删17.8%块判决零变化)
pack = purify(question, answer, evidence_dicts,
              PurificationConfig(mode="evidence", use_deq_gate=True))

# pack = {mode, kept, removed[{evidence_id, stage, reason_code, detail}], stats}
```

## 三、两种模式（实验教训的固化）

| | statement模式 | evidence模式 |
|---|---|---|
| kept形态 | 句/行级语句(表格→"表头：值"行) | **原文本块(不改写)** |
| 过滤器 | F1+F2+F3+语句预算 | F1+F3(可选+DEQ门) |
| 消费方 | NLI直判 | 专家通道/类型感知linearize |
| 依据 | 71号: NLI直入表格HTML 35.3%→行级化64.7% | 73号: 证据级重写破坏linearize类型检测(0.94→0.41) |
| 集成 | 独立判读场景 | `qa_module.use_subtractor`(已切换) |

**PurificationConfig护栏**（全部实验校准）：
- `id_exemption=True`：标识符类检测项的含ID证据不做scope删（71号救回5实例gold）
- `fallback=True`：F1删光→回退保留全部
- `max_statements=25`：语句预算（仅statement模式，按锚点命中排序）
- `use_deq_gate`：DEQ E0门组合（evidence模式，全拒时回退）

## 四、实验数字快照（模块的实证基础）

| 场景 | 结果 | 出处 |
|---|---|---|
| statement模式×NLI直判(17违例) | 查全35.3%→64.7%(+29.4pt), gold保留35/35 | 71号 |
| evidence模式×完整管线(108实例) | 块-10.8%, acc-0.9pt(删到needed块) | 73号 |
| DEQ门×完整管线 | 块-17.8%, **判决零变化** | 73号 |
| 七方法基线(语句级) | 唯一gold保留100%的选择性删除 | 72号 |

**诚实边界**（73号结论）：完整管线中粒度归一已由linearize负责、
无损提纯已由DEQ负责——提纯模块的增益待真实噪声召回池验证。

## 五、文件清单

| 资产 | 位置 |
|---|---|
| 收敛门面 | `algorithms/consistency/evidence_purifier.py` |
| statement核心 | `algorithms/consistency/evidence_subtractor.py`(F1/F2/F3) |
| 管线集成 | `qa_module.py` `use_subtractor`(evidence模式) |
| 回归测试 | `tests/test_evidence_purifier.py`(7) + `test_evidence_subtractor.py`(7) |
| 重构安全验证 | 管线评测数字与重构前逐位一致(acc 0.7593/macroF1 0.6111/vio 0.8824) |

## 六、后续挂点

```text
1. 真实噪声召回池评测(O1-unit top-50含干扰) — 提纯增益的最终验证
2. 检测项→证据形态合同(40项taxonomy) — F3的完整形态匹配(现为指针子集)
3. 覆盖差异型检测(表列集合关系) — 69号发现4的类型学补全
```
