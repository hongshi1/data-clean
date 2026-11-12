"""CascadeVerifier: QA一致性校验系统的收敛入口(facade).

三行代码完成校验, 使用者不需要知道内部结构(L0/L1专家/L2 NLI残差/
L3 LLM级联, 词典/规则包场景配置, QAInput冻结格式):

    from algorithms.consistency.verifier import CascadeVerifier

    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    result = verifier.verify(question, answer, evidence)   # evidence=frozen格式dict列表
    print(result.verdict, result.evidence_refs)

preset(成本/质量档位, 映射QAConsistencyModule内部编排参数):
    fast      L0/L1确定性专家通道, ~8ms/条, 零模型加载
    standard  +L2本地NLI残差(微调mDeBERTa, 首次verify约35s模型加载,
              之后~120ms/条), 无LLM调用
    full      +L3级联仲裁(L2的refute候选升级到LLM复核, 走缓存接口),
              最贵也最准

scene(场景名→(词典路径, 规则包路径), onboarding产物):
    srs_scene1  04号场景(默认, config/ner_lexicons/srs_scene1.json +
                config/rulepacks/srs_gjb_v1.json)
    doc06       06号场景(config/ner_lexicons/doc06_scene.json +
                config/rulepacks/doc06_v1.json)
    doc01       01号场景(onboarding生成, config/ner_lexicons/doc01_scene.json
                + config/rulepacks/doc01_onboard_v1.json)

scene切换是模块级默认切换(set_default_lexicon + set_default_rulepack):
    QAConsistencyModule内部专家在调用期消费这些默认配置, 引擎侧派生
    缓存按pack/lexicon身份失效重建, 因此切换真实生效. 注意: 多个
    CascadeVerifier实例并存时, 最后构造的场景占有模块级默认.

本模块是薄封装: 不复制任何内部逻辑, 全部委托QAConsistencyModule;
VerdictResult是VerificationResult的字段收敛视图(判定/引用/检查项/
理由/诊断/延迟). 高级用法: verify_qa_input(QAInput)->VerificationResult
返回完整结果(server等需要全字段序列化的调用方使用).

模块顶层零I/O: 场景词典/规则包在__init__函数内加载.
演示: tools/demo_verifier.py.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from algorithms.consistency.eval_lib import build_qa_input
from algorithms.consistency.ner_lexicon import (
    NerLexicon,
    load_lexicon,
    set_default_lexicon,
)
from algorithms.consistency.qa_models import (
    QAInput,
    VerificationResult,
    Verdict,
)
from algorithms.consistency.qa_module import QAConsistencyModule
from algorithms.consistency.rulepack import (
    RulePack,
    load_rulepack,
    set_default_rulepack,
)

BASE = Path(__file__).resolve().parents[2]

#: preset名→QAConsistencyModule编排参数(成本/质量档位)
#: v3(M83)域自适应配置面: standard=域内档(typed分解+strict聚合,
#: 论文配置distilled_v1@gate0.8经nli_residual默认值生效);
#: crossdoc=跨文档档(句子切分分解+dominant_70聚合,
#: refactor_matrix_v1.json实测crossdoc150 0.7361 vs 域内档0.5109)
PRESETS: dict[str, dict] = {
    "fast": dict(use_experts=True),
    "standard": dict(use_experts=True, use_nli_residual=True),
    "crossdoc": dict(use_experts=True, use_nli_residual=True,
                     decomposer="sentence", aggregation="dominant_70"),
}

#: 场景名→(词典路径, 规则包路径), 相对仓库根
SCENES: dict[str, tuple[str, str]] = {
    "srs_scene1": ("config/ner_lexicons/srs_scene1.json",
                   "config/rulepacks/srs_gjb_v1.json"),
    "doc06": ("config/ner_lexicons/doc06_scene.json",
              "config/rulepacks/doc06_v1.json"),
    "doc01": ("config/ner_lexicons/doc01_scene.json",
              "config/rulepacks/doc01_onboard_v1.json"),
}

#: facade.verify自动生成QAInput所需的两类标识前缀
_FACADE_INSTANCE_PREFIX = "facade-"
_FACADE_FREEZE_ID = "facade-frozen-context"

#: VerdictResult.rationale的截断长度(完整rationale在VerificationResult)
_RATIONALE_MAX = 500

# Windows OpenMP顺序约束: torch须先于numpy链加载, 否则CUDA推理
# 静默崩溃(见docs/srs_project/68号); fast档无NLI允许无torch环境.
try:
    import torch  # noqa: F401,E402
except ImportError:
    torch = None


def _normalize_evidence(evidence: list[dict], seq: int) -> list[dict]:
    """证据dict规范化: 极简输入({text})自动补全冻结格式的必填字段.

    完整格式项原样通过(不覆盖用户字段); 缺text的项报ValueError.
    """
    blocks: list[dict] = []
    for i, ev in enumerate(evidence):
        if not isinstance(ev, dict) or not str(ev.get("text", "")).strip():
            raise ValueError(
                f"evidence[{i}]缺少text字段(极简格式至少需要text)")
        if all(k in ev for k in
               ("evidence_id", "text", "source_type", "source_ref",
                "scope_id")):
            blocks.append(ev)
            continue
        blocks.append({
            "evidence_id": str(ev.get("evidence_id")
                               or f"facade-{seq}-ev-{i:03d}"),
            "text": str(ev["text"]),
            "source_type": ev.get("source_type", "text"),
            "source_ref": ev.get("source_ref") or {
                "doc_id": "facade", "section": "", "page": 0,
                "block_id": f"facade-{seq}-b{i:03d}",
                "row_id": "", "region_id": ""},
            "scope_id": str(ev.get("scope_id") or f"facade:{seq}"),
            "completeness": ev.get("completeness", "open"),
        })
    return blocks

__all__ = ["CascadeVerifier", "PRESETS", "SCENES", "VerdictResult"]


@dataclass(frozen=True)
class VerdictResult:
    """一次校验的收敛结果(VerificationResult的字段子集视图).

    verdict        三态判定: support / refute / not_in_evidence
    evidence_refs  被引用的证据id(全claim引用并集, 排序)
    check_items    检查项候选并集(claim级check_item_candidates去重排序)
    rationale      判定理由(claim理由拼接, 超500字符截断)
    diagnostics    诊断信息(聚合/通道/场景切换等)
    latency_ms     本次verify的墙钟延迟(毫秒)
    """

    verdict: Verdict
    evidence_refs: tuple[str, ...]
    check_items: tuple[str, ...]
    rationale: str
    diagnostics: tuple[str, ...]
    latency_ms: float
    localizations: tuple = ()


def _to_verdict_result(result: VerificationResult,
                       latency_ms: float) -> VerdictResult:
    """VerificationResult→VerdictResult(字段收敛, 不丢判定信息)."""
    rationale = result.rationale
    if len(rationale) > _RATIONALE_MAX:
        rationale = rationale[:_RATIONALE_MAX] + "…[截断]"
    return VerdictResult(
        verdict=result.verdict,
        evidence_refs=tuple(sorted(
            {ref for claim in result.claim_results
             for ref in claim.evidence_refs})),
        check_items=tuple(sorted(
            {item for claim in result.claim_results
             for item in claim.check_item_candidates})),
        rationale=rationale,
        diagnostics=result.diagnostics,
        latency_ms=round(latency_ms, 3),
        localizations=result.localizations,
    )


class CascadeVerifier:
    """校验系统的收敛入口(facade, 委托QAConsistencyModule).

    用法:
        verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
        result = verifier.verify(question, answer, evidence)
        print(result.verdict, result.evidence_refs)

    惰性构造: preset="standard"/"full"的NLI/LLM相关引擎在首次verify
    时才加载(构造期零模型I/O); "fast"无任何模型加载.
    """

    def __init__(self, preset: str = "fast", scene: str = "srs_scene1",
                 nli_model_path: str | None = None,
                 purify: bool = False) -> None:
        if preset not in PRESETS:
            raise ValueError(
                f"未知preset: {preset!r}(可用: {sorted(PRESETS)}, "
                f"含义: fast=纯专家通道, standard=+L2 NLI残差, "
                f"full=+L3级联仲裁)")
        if scene not in SCENES:
            raise ValueError(
                f"未知scene: {scene!r}(可用: {sorted(SCENES)}, "
                f"场景=词典+规则包组合, 见config/ner_lexicons与"
                f"config/rulepacks)")
        self._preset = preset
        self._scene = scene
        self._nli_model_path = nli_model_path
        # 证据提纯(evidence模式: F1作用域+F3指针删除, 只删块不改写;
        # 74号收敛模块, 每次删除带审计diagnostic)
        self._purify = purify
        lexicon_path, rulepack_path = SCENES[scene]
        self._lexicon: NerLexicon = load_lexicon(BASE / lexicon_path)
        self._rulepack: RulePack = load_rulepack(BASE / rulepack_path)
        # 模块级默认切换: qa_module内部专家在调用期消费默认词典/规则包,
        # 引擎侧派生缓存按配置身份失效重建(场景切换真实生效).
        set_default_lexicon(self._lexicon)
        set_default_rulepack(self._rulepack)
        self._engine: QAConsistencyModule | None = None
        self._auto_instance_seq = 0

    # ── 对外API ─────────────────────────────────────────────

    def verify(self, question: str, answer: str,
               evidence: list[dict]) -> VerdictResult:
        """三参数校验(question/answer/evidence dict列表).

        evidence支持两种输入(极简友好, 缺省字段自动补全):
          极简:  [{"text": "表39: 连接池配置 PZXQ-GN-LJCGL-LJCPZ"}]
          完整:  冻结QA格式(必填evidence_id/text/source_type/
                 source_ref/scope_id, 选填completeness等)
        极简项自动补: evidence_id=facade-ev-N / source_type=text /
        source_ref占位 / scope_id=facade; instance_id自动生成.
        """
        self._auto_instance_seq += 1
        record = {
            "instance_id": f"{_FACADE_INSTANCE_PREFIX}"
                           f"{self._auto_instance_seq}",
            "question": question,
            "answer": answer,
            "context_freeze_id": _FACADE_FREEZE_ID,
            "evidence": _normalize_evidence(
                evidence, self._auto_instance_seq),
        }
        return self._run_record(record)

    def verify_record(self, record: dict) -> VerdictResult:
        """冻结QA格式整条记录校验.

        record须含instance_id/question/answer/context_freeze_id/evidence
        (与data/gjb_438c/qa_frozen/*.jsonl同schema, 由build_qa_input映射).
        """
        return self._run_record(record)

    def verify_batch(self, records: list[dict]) -> list[VerdictResult]:
        """批量校验(内部复用同一引擎实例, 不重复构造)."""
        return [self._run_record(record) for record in records]

    def verify_qa_input(self, request: QAInput) -> VerificationResult:
        """高级用法: QAInput→完整VerificationResult(全字段, 薄委托).

        server等需要全字段序列化(claim_results/evidence_chain/
        context_hash等)的调用方使用; 一般调用方用verify/verify_record.
        """
        return self._engine_instance.verify(request)

    @property
    def preset(self) -> str:
        """成本/质量档位名(fast/standard/full)."""
        return self._preset

    @property
    def scene(self) -> str:
        """场景名(SCENES键, 词典+规则包组合)."""
        return self._scene

    @property
    def lexicon(self) -> NerLexicon:
        """当前场景的L0词典(可查询: scene/id_patterns/domain_terms...)."""
        return self._lexicon

    @property
    def rulepack(self) -> RulePack:
        """当前场景的L1规则包(可查询: pack_id/table_schemas/templates...)."""
        return self._rulepack

    # ── 内部(薄委托) ─────────────────────────────────────────

    @property
    def _engine_instance(self) -> QAConsistencyModule:
        """惰性构造内部QAConsistencyModule(首次verify才碰NLI/LLM加载)."""
        if self._engine is None:
            kwargs = dict(PRESETS[self._preset])
            if self._nli_model_path is not None:
                kwargs["nli_model_path"] = self._nli_model_path
            if self._purify:
                kwargs["use_subtractor"] = True  # 证据提纯(74号evidence模式)
            self._engine = QAConsistencyModule(**kwargs)
        return self._engine

    def _run_record(self, record: dict) -> VerdictResult:
        request = build_qa_input(record)
        start = time.perf_counter()
        result = self._engine_instance.verify(request)
        latency_ms = (time.perf_counter() - start) * 1000.0
        return _to_verdict_result(result, latency_ms)
