"""Blackboard schemas: 校准黑板核心数据模型 (typed state + decision record).

设计来源:
  - docs/srs_project/ACDD_method_proposal.md (两层模型: 感知层ε/文档层η)
  - Calibrated Blackboard 设计(2026-09讨论): 状态条目=带已测量误差模型的测量值

三条铁律:
  1. 状态是带schema的对象, 不是LLM自由上下文 —— LLM只能看到这些对象的视图
  2. 每条证据写入必须带 (channel, confidence, confidence来源, 认识论状态)
  3. 每次状态迁移留决策记录 → 可回放 → 可评测
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 枚举: 通道 / 认识论状态 / 置信度来源 / 任务类型
# ═══════════════════════════════════════════════════════════════

class Channel(str, Enum):
    """证据通道 = 测量仪器. ACDD原则: 通道可替换, 方法本体不依赖任何特定通道."""
    ANCHOR = "anchor"             # born-digital Visio XML直读(构造性保真)
    VLM = "vlm"                   # kimi视觉提取(锚点校准)
    OCR = "ocr"                   # tesseract字符识别(伪发现风险)
    KT = "kt"                     # κ_T表格编译器(确定性解析)
    KP = "kp"                     # κ_P正文编译器(确定性抽取, 本包新增)
    ID_GRAPH = "id_graph"         # ID锚定图(正则确定性)
    CHUNKS = "chunks"             # 结构化chunks字面内容
    DRIFT_CENSUS = "drift_census" # M14源-渲染diff(确定性)
    TIER1 = "tier1"               # 预计算Tier1比较(M16/M1产出)
    ADJUDICATION = "adjudication" # M7/M17/M22裁决语料(664标签, π=0.265)
    SYNTAX = "syntax"             # GJB语法层规则检测(algorithms/syntax)
    EMBEDDING = "embedding"       # 语义向量匹配(需校准)
    LEXICAL = "lexical"           # 确定性词法匹配
    LLM = "llm"                   # LLM判断(假设, 需裁决)


class Epistemic(str, Enum):
    """黑板条目的认识论状态 (Hearsay-II传统: KS写入的是假设, 控制组件裁决)."""
    FACT = "fact"           # 确定性源写入: 文档字面内容的忠实读取
    HYPOTHESIS = "hypothesis"  # 测量/推断/匹配写入: 待验证
    VERIFIED = "verified"   # 经裁决/互校确认
    REFUTED = "refuted"     # 经裁决否证


class ConfSource(str, Enum):
    """置信度数字的来源 —— 区分"测量出来的"与"感觉出来的"."""
    DETERMINISTIC = "deterministic"  # 构造性保真(by construction)
    CALIBRATED = "calibrated"        # 锚点校准的误差模型(M3流程)
    HEURISTIC = "heuristic"          # 工程经验值(未校准)
    LLM_SELF = "llm_self"            # LLM自报(已知不可靠, 设上限)


class TaskType(str, Enum):
    """四类不一致框架(project_guide v3.0) + 召回任务的统一入口."""
    COMPLETENESS_CHECK = "completeness_check"  # 术语/功能遗漏(sc1/sc4/sc5)
    FLOW_CONSISTENCY = "flow_consistency"      # 业务逻辑: 时序/异常流(sc2)
    TERMINOLOGY_CHECK = "terminology_check"    # 术语层: 同名实体多位置一致
    PARAMETER_CHECK = "parameter_check"        # 参数指标: 值/单位/数字
    CONTEXT_RECALL = "context_recall"          # 方向A轨道一: 查询式上下文召回
    GJB_COMPLIANCE = "gjb_compliance"          # GJB合规(语法层, 证据聚合入口)


# ═══════════════════════════════════════════════════════════════
# 数据类: 证据 / 任务 / 计划 / 批评 / 决策记录
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Provenance:
    """证据出处: 可追溯到具体文件与定位符(可解释性的物质基础)."""
    source: str          # 文件路径 / "census" / "rule:TERM-001" 等
    locator: str = ""    # pair_id / section / chunk_id / embed_index


@dataclass
class EvidenceItem:
    """黑板条目: 一条带测量语义的证据.

    subject   = 它满足哪个证据需求(planner的requirement key)
    payload   = 结构化内容(编译表/锚点图/正文特征/分歧清单...)
    """
    subject: str
    channel: Channel
    epistemic: Epistemic
    confidence: float
    conf_source: ConfSource
    payload: dict[str, Any]
    provenance: Provenance
    note: str = ""
    written_by: str = ""            # agent名
    state_version: int = 0          # 写入时的黑板版本号

    def fingerprint(self) -> str:
        """去重指纹: 同subject+channel+payload视为同一写入."""
        canon = json.dumps(
            {"s": self.subject, "c": self.channel.value,
             "p": self.payload}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:16]

    def brief(self) -> dict[str, Any]:
        """决策日志里的紧凑摘要(不落全量payload)."""
        return {
            "subject": self.subject,
            "channel": self.channel.value,
            "epistemic": self.epistemic.value,
            "confidence": round(self.confidence, 3),
            "conf_source": self.conf_source.value,
            "payload_keys": sorted(self.payload.keys()),
            "note": self.note[:80],
        }


@dataclass
class TaskSpec:
    """任务规约: planner的输入. 定位方式=pair(配对式)或entity(查询式)."""
    task_id: str
    task_type: TaskType
    query: str = ""
    pair_id: str = ""      # 配对式定位: "1_001"等
    entity: str = ""       # 查询式定位: 实体名
    entity_id: str = ""    # 查询式定位: GJB需求ID
    scene: str = ""        # 留空则由store从pair_id推断
    doc: str = ""


@dataclass(frozen=True)
class Requirement:
    """HTN证据需求: 任务类型→所需证据checklist的一项."""
    key: str                          # evidence subject, 如 "table_structure"
    agents: tuple[str, ...]           # 能满足它的agent(按优先序)
    channels: tuple[Channel, ...]     # 可接受的通道
    critical: bool = True             # critic: 缺失→弃权
    detail: str = ""


@dataclass
class Plan:
    """Planner输出: 证据checklist + 预算 + 注意事项(确定性HTN, 零LLM)."""
    task: TaskSpec
    requirements: tuple[Requirement, ...]
    budget: int = 3
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Invocation:
    """Router输出: 一次agent调用的指令."""
    agent: str
    subject: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Critique:
    """Critic输出: 覆盖检查+预算判定(确定性, 无LLM)."""
    verdict: str                    # "continue" | "satisfied" | "abstain"
    satisfied: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    missing_critical: list[str] = field(default_factory=list)
    escalation: list[str] = field(default_factory=list)      # 待调agent名
    open_semantic: list[str] = field(default_factory=list)   # 已知未定义比较语义
    iteration: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass
class DecisionRecord:
    """决策日志条目: 黑板每次状态迁移的审计记录."""
    seq: int
    action: str            # plan/route/write/duplicate/critic/final/abstain
    agent: str = ""
    channel: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    state_version: int = 0
    ts: float = field(default_factory=lambda: time.time())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def task_to_dict(task: TaskSpec) -> dict[str, Any]:
    return asdict(task)
