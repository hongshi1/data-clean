"""统一校验服务模块（南开对接契约·新版接口规格）.

接口①POST /api/check(发起: scene路由, source为字符串来源引用,
    expert_knowledge幂等同步+快照绑定, 异步受理)
接口②GET /api/check-status/{check_id}(任务态机: queued→running→done/error;
    running附progress{total,completed}; done附summary{total,consistent,
    inconsistent,undetermined}; error顶层ok=false+error{code,message})
接口③GET /api/check-reports/{check_id}(CheckReport: samples[].consistency_result
    三态+violations[item_id,item_name,description,affected_answer])
数据集级: POST /api/datasets/{id}/check, GET /api/datasets/{id}/check-status

契约要点:
  scene → 场景路由(scene1已接入; 未接入=404"场景未接入")
  source是字符串(来源文档引用, 直接做前缀/包含解析召回该文档证据)
  条目态映射: support→consistent, refute→inconsistent,
              not_in_evidence→undetermined
  violations: result.localizations按check_item聚合; item_name查
              knowledge/consistency_taxonomy_v3.json的items;
              affected_answer=answer中claim span切片或claim_text
  异常≠数据有问题: doc解析失败等条目级异常→该样本undetermined+诊断说明
  (不落violations); 引擎级异常→任务error(看门狗CHECK_TIMEOUT_SEC超时
  →code=ENGINE_TIMEOUT, 其余→ENGINE_ERROR), 可重新发起

专家知识: {scene(须与请求scene一致), lexicon, rulepack} → 幂等覆盖写入
知识库(data/agent_knowledge/{scene}/) → 发起时快照绑定check_id。

任务执行: 单工作线程串行+嵌套执行线程看门狗, 磁盘持久化(重启可回读),
模块顶层零I/O, 引擎(召回+验证器)首次执行惰性预热。
"""
from __future__ import annotations

import json
import queue
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parents[1]

#: 场景注册表: scene → 引擎配置(未注册=404"场景未接入")
SCENES: dict[str, dict[str, str]] = {
    "scene1": {
        "engine": "srs_scene1",
        "builtin_lexicon": "config/ner_lexicons/srs_scene1.json",
        "builtin_rulepack": "config/rulepacks/srs_gjb_v1.json",
    },
}

#: 旧版场景名兼容(scene字段别名 → 接入场景)
_SCENE_ALIASES: dict[str, str] = {"srs": "scene1", "srs_scene1": "scene1"}

KNOWLEDGE_DIR = BASE / "data/agent_knowledge"
CHECKS_DIR = BASE / "data/agent_checks"
DATASETS_DIR = BASE / "data/agent_datasets"
DATASET_INDEX_PATH = CHECKS_DIR / "dataset_index.json"
TAXONOMY_PATH = BASE / "knowledge/consistency_taxonomy_v3.json"

#: 单次check执行看门狗(秒): 超时→任务error code=ENGINE_TIMEOUT
CHECK_TIMEOUT_SEC = 600.0

_RESULT_TO_CONSISTENCY = {"support": "consistent", "refute": "inconsistent",
                          "not_in_evidence": "undetermined"}
_UNDETERMINED = "undetermined"
_SAFE_ID_RE = re.compile(r"^[\w][\w\-.:]{0,127}$")

#: 任务注册表(check_id → 状态/报告; 进程内存+磁盘双写, 重启回读)
_TASKS: dict[str, dict[str, Any]] = {}
#: 提交锁(check_id → lock; 看门狗与执行线程的终态提交互斥)
_COMMIT_LOCKS: dict[str, threading.Lock] = {}
#: 数据集→最近check_id
_DATASET_LAST: dict[str, str] = {}
#: 单工作线程(串行执行, 保护模块级词典/规则包默认值)
_QUEUE: "queue.Queue[str]" = queue.Queue()
_WORKER_STARTED = False
_ENGINE: dict[str, Any] | None = None
_TAXONOMY_NAMES: dict[str, str] | None = None


# ── 契约模型 ────────────────────────────────────────────────────────────────

class QaPair(BaseModel):
    sample_id: str
    question: str
    answer: str
    source: str
    knowledge_refs: list[str] = Field(default_factory=list)


class ExpertKnowledge(BaseModel):
    scene: str
    lexicon: dict[str, Any] | None = None
    rulepack: dict[str, Any] | None = None


class CheckRequest(BaseModel):
    scene: str
    qa_pairs: list[QaPair]
    expert_knowledge: ExpertKnowledge | None = None


# ── 专家知识: 幂等同步 + 快照 ─────────────────────────────────────────────

def sync_expert_knowledge(scene: str, knowledge: ExpertKnowledge) -> str:
    """幂等覆盖写入(rule_id对齐) + 提交期校验(契约: 原子完成同步+校验).

    非法schema在提交时即400, 不落库不污染后续check.
    """
    directory = KNOWLEDGE_DIR / scene
    directory.mkdir(parents=True, exist_ok=True)
    if knowledge.lexicon is not None:
        _validated_write(knowledge.lexicon, directory / "lexicon.json",
                         "lexicon")
    if knowledge.rulepack is not None:
        _validated_write(knowledge.rulepack, directory / "rulepack.json",
                         "rulepack")
    version = f"rules-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    n_rules = _count_rules(directory / "rulepack.json")
    (directory / "version.json").write_text(
        json.dumps({"version": version, "n_rules": n_rules},
                   ensure_ascii=False), encoding="utf-8")
    return version


def _validated_write(payload: dict[str, Any], target: Path,
                     kind: str) -> None:
    """提交期校验: 用加载器解析通过才落库(原子性)."""
    import tempfile
    from algorithms.consistency.ner_lexicon import load_lexicon
    from algorithms.consistency.rulepack import load_rulepack
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.json"
        probe.write_text(json.dumps(payload, ensure_ascii=False),
                         encoding="utf-8")
        try:
            if kind == "lexicon":
                load_lexicon(probe)
            else:
                load_rulepack(probe)
        except (ValueError, OSError) as exc:
            raise HTTPException(
                400, f"expert_knowledge.{kind}校验失败: {exc}") from exc
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                      encoding="utf-8")


def current_snapshot(scene: str) -> dict[str, Any]:
    """scene当前知识状态(提交的或内置的) → 发起时绑定check_id的快照."""
    directory = KNOWLEDGE_DIR / scene
    marker = directory / "version.json"
    if marker.exists():
        return json.loads(marker.read_text(encoding="utf-8"))
    return {"version": f"builtin-{scene}", "n_rules": _count_rules(None)}


def _count_rules(rulepack_path: Path | None) -> int:
    """规则条数: 显式rules列表, 否则gjb.rule_clusters去重rule_ids."""
    path = rulepack_path
    if path is None or not path.exists():
        path = BASE / "config/rulepacks/srs_gjb_v1.json"
    if not path.exists():
        return 0
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        rules = raw.get("rules")
        if isinstance(rules, list):
            return len(rules)
        gjb = raw.get("gjb")
        if isinstance(gjb, dict):
            clusters = gjb.get("rule_clusters")
            if isinstance(clusters, list):
                ids = {rid for cluster in clusters if isinstance(cluster, dict)
                       for rid in (cluster.get("rule_ids") or [])}
                return len(ids)
    return 0


# ── 引擎(召回+验证, 惰性预热单例) ──────────────────────────────────────────

def get_engine() -> dict[str, Any]:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    from algorithms.blackboard.hybrid_recall import HybridRecaller
    from algorithms.consistency.qa_module import QAConsistencyModule
    chunks = json.loads(
        (BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json")
        .read_text(encoding="utf-8"))
    full = {str(c.get("chunk_id", "")): str(c.get("text", ""))
            for c in chunks}
    docs = sorted({str(c.get("doc", "")) for c in chunks})
    recaller = HybridRecaller()
    recaller.recall("数据库访问", doc=docs[3] if len(docs) > 3 else docs[0],
                    top_k=5)
    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path="models/nli/distilled_v1", nli_gate=0.8)
    _ENGINE = {"recaller": recaller, "module": module,
               "full": full, "docs": docs}
    return _ENGINE


def resolve_doc(doc_ref: str, docs: list[str]) -> str:
    """source字符串 → chunk语料中的完整文档名(前缀匹配; 唯一命中才有效)."""
    ref = str(doc_ref).strip()
    exact = [d for d in docs if d == ref]
    if exact:
        return exact[0]
    prefix = [d for d in docs if d.startswith(ref)]
    if len(prefix) == 1:
        return prefix[0]
    contains = [d for d in docs if ref in d]
    if len(contains) == 1:
        return contains[0]
    raise LookupError(f"source无法解析: {doc_ref!r}")


def _taxonomy_names() -> dict[str, str]:
    """taxonomy_v3条目名(id→中文名), 惰性加载(工作线程内首次调用)."""
    global _TAXONOMY_NAMES
    if _TAXONOMY_NAMES is None:
        try:
            raw = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
            _TAXONOMY_NAMES = {str(item.get("id", "")): str(item.get("name", ""))
                               for item in raw.get("items", [])
                               if isinstance(item, dict)}
        except (OSError, ValueError):
            _TAXONOMY_NAMES = {}
    return _TAXONOMY_NAMES


def _sentence_of_span(answer: str, span: tuple[int, int] | None) -> str:
    """span所在的answer原句(报告的answer侧上下文)."""
    if span is None:
        return answer[:120]
    mid = (span[0] + span[1]) // 2
    starts = [pos + 1 for pos in (answer.rfind("。", 0, mid),
                                  answer.rfind("！", 0, mid),
                                  answer.rfind("？", 0, mid),
                                  answer.rfind("；", 0, mid),
                                  answer.rfind("\n", 0, mid)) if pos >= 0]
    ends = [pos + 1 for pos in (answer.find("。", mid),
                                answer.find("！", mid),
                                answer.find("？", mid),
                                answer.find("；", mid),
                                answer.find("\n", mid)) if pos >= 0]
    start = max(starts) if starts else 0
    end = min(ends) if ends else min(len(answer), mid + 120)
    return answer[start:end].strip() or answer[:120]


def _clean_rationale(rationale: str) -> str:
    """rationale去内部引用噪音(语句id括号), 保留冲突说明正文."""
    text = str(rationale)
    text = re.sub(r"（[^（）]*#\S+[^（）]*）", "", text)
    return text.strip()


#: 根因源/操作的中文对照(报告可读性; 英文枚举仅供程序消费)
ROOT_CAUSE_SOURCE_ZH = {
    "answer": "答案侧错误",
    "document_internal": "文档内部不一致",
    "document_gap": "文档缺失（合规条款未覆盖）",
    "recall_insufficient": "证据召回不足",
}
ROOT_CAUSE_OPERATION_ZH = {
    "value_substitution": "值替换/截断",
    "dual_registration": "同一标识符双登记",
    "scope_leakage": "跨行取值（集合污染）",
    "quantifier_scope_expansion": "范围过度概括",
    "quantifier_scope_reduction": "范围不当缩小",
    "precondition_weakening": "前置条件弱化",
    "precondition_fabrication": "虚构前置条件",
    "necessity_sufficiency_swap": "必要/充分条件混淆",
    "modal_conflict": "模态冲突（必须/允许/禁止）",
    "temporal_reversal": "时序颠倒",
    "negation_mismatch": "极性/否定相反",
    "relation_inversion": "方向/依赖颠倒",
    "entity_substitution": "主体错绑（张冠李戴）",
    "exception_flow_mismatch": "异常流错配",
    "coverage_fabrication": "覆盖虚构（多报功能）",
    "semantic_unspecified": "语义差异（待细分）",
    "compliance_gap": "合规条款缺失",
}


def _build_violations(result: Any, answer: str,
                      wanted: set[str] | None) -> list[dict[str, str]]:
    """localizations按check_item聚合 → violations[](可读中文根因报告).

    每条: item_id/item_name(契约) + answer_context(answer原句) +
    affected_answer(断言值) + description(冲突对中文说明: answer声称什么/
    文档记载什么/根因判定) + root_cause{根因源,根因操作}(中文).
    """
    names = _taxonomy_names()
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for loc in result.localizations:
        item_ids = list(loc.check_item_candidates) or ["未分类"]
        context = _sentence_of_span(answer, loc.answer_span)
        affected = str(loc.claim_text)
        if loc.answer_span is not None:
            start, end = loc.answer_span
            if 0 <= start < end <= len(answer):
                affected = answer[start:end]
        rc = loc.root_cause or {}
        source_zh = ROOT_CAUSE_SOURCE_ZH.get(str(rc.get("source", "")), "")
        op_zh = ROOT_CAUSE_OPERATION_ZH.get(str(rc.get("operation", "")),
                                            "语义差异")
        # 冲突对说明: answer声称 vs 文档记载 + 通道判定说明
        parts = [f"answer断言：「{affected}」"]
        if loc.evidence:
            ev = loc.evidence[0]
            loc_txt = ev.section if ev.section else ""
            if ev.row_index >= 0:
                loc_txt += f" 第{ev.row_index}行"
            if ev.field_name:
                loc_txt += f" {ev.field_name}"
            parts.append(f"文档{loc_txt}记载：「{str(ev.statement_text)[:90]}」")
        clean = _clean_rationale(loc.rationale)
        if clean and clean not in parts:
            parts.append(clean)
        if source_zh or op_zh:
            parts.append(f"根因判定：{source_zh}·{op_zh}")
        for item_id in item_ids:
            if wanted is not None and item_id not in wanted:
                continue
            key = (item_id, affected)
            if key in seen:
                continue
            seen.add(key)
            # 详细根因分析(逐字diff+成因推断+修正建议) + 冲突对上下文
            from algorithms.consistency.root_cause import (
                detailed_explanation)
            detail = detailed_explanation(loc, answer)
            out.append({
                "item_id": item_id,
                "item_name": names.get(item_id, "未分类"),
                "answer_context": context,
                "affected_answer": affected,
                "description": detail,
                "root_cause": {
                    "根因源": source_zh or "待细分",
                    "根因操作": op_zh,
                },
            })
    return out


def verify_one(qa_pair: QaPair, engine: dict[str, Any]) -> dict[str, Any]:
    """单条qa_pair: 召回→验证→三态一致性结果+violations(按knowledge_refs过滤)."""
    from algorithms.consistency.qa_models import (
        QAInput,
        RetrievedEvidence,
        SourceRef as QaSourceRef,
    )
    import re as _re
    title_prefix = _re.compile(r"^\[表格标题[^\]]*\]")
    doc = resolve_doc(qa_pair.source, engine["docs"])
    query = f"{qa_pair.question} {qa_pair.answer[:400]}"
    recalled = engine["recaller"].recall(query, doc=doc, top_k=10)
    hits = [h for h in recalled.get("hits", [])
            if h.get("type") in ("text", "table")][:8]
    evidences: list[RetrievedEvidence] = []
    for rank, hit in enumerate(hits, 1):
        text = title_prefix.sub("", engine["full"].get(
            str(hit.get("chunk_id", "")), "")).strip()
        if not text:
            continue
        evidences.append(RetrievedEvidence(
            evidence_id=f"{qa_pair.sample_id}-rec-{rank:02d}",
            text=text,
            source_type=str(hit.get("type", "text")),
            source_ref=QaSourceRef(
                doc_id=str(hit.get("doc", "")),
                section=str(hit.get("section", "")),
                block_id=str(hit.get("chunk_id", ""))),
            scope_id="", completeness="open"))
    request = QAInput(
        instance_id=qa_pair.sample_id, question=qa_pair.question,
        answer=qa_pair.answer, evidence=tuple(evidences),
        context_freeze_id=f"check-{qa_pair.sample_id}")
    result = engine["module"].verify(request)
    wanted = set(qa_pair.knowledge_refs) if qa_pair.knowledge_refs else None
    return {
        "sample_id": qa_pair.sample_id,
        "question": qa_pair.question,
        "answer": qa_pair.answer,
        "source": qa_pair.source,
        "consistency_result": _RESULT_TO_CONSISTENCY.get(
            result.verdict, _UNDETERMINED),
        "violations": _build_violations(result, qa_pair.answer, wanted),
    }


def _verify_sample(pair: QaPair, engine: dict[str, Any]) -> dict[str, Any]:
    """条目级异常→undetermined+诊断说明(异常≠数据有问题), 不落violations."""
    try:
        return verify_one(pair, engine)
    except (LookupError, ValueError, RuntimeError) as exc:
        return {
            "sample_id": pair.sample_id,
            "question": pair.question,
            "answer": pair.answer,
            "source": pair.source,
            "consistency_result": _UNDETERMINED,
            "violations": [],
            "diagnostics": [f"{type(exc).__name__}: {exc}"],
        }


def _bind_scene_knowledge(scene: str) -> None:
    """把scene当前知识(提交的优先)绑定为模块级场景默认值(串行线程内安全)."""
    from algorithms.consistency.ner_lexicon import (
        load_lexicon,
        set_default_lexicon,
    )
    from algorithms.consistency.rulepack import (
        load_rulepack,
        set_default_rulepack,
    )
    directory = KNOWLEDGE_DIR / scene
    lexicon_path = directory / "lexicon.json"
    pack_path = directory / "rulepack.json"
    config = SCENES[scene]
    lexicon_src = (lexicon_path if lexicon_path.exists()
                   else BASE / config["builtin_lexicon"])
    pack_src = (pack_path if pack_path.exists()
                else BASE / config["builtin_rulepack"])
    set_default_lexicon(load_lexicon(lexicon_src))
    set_default_rulepack(load_rulepack(pack_src))


def _commit_lock(check_id: str) -> threading.Lock:
    lock = _COMMIT_LOCKS.get(check_id)
    if lock is None:
        lock = _COMMIT_LOCKS.setdefault(check_id, threading.Lock())
    return lock


def execute_check(check_id: str, scene: str, qa_pairs: list[QaPair]) -> None:
    """执行一次check: 条目级异常→undetermined, 引擎级异常→任务error.

    progress逐样本推进并持久化; 终态提交与看门狗经提交锁互斥,
    被看门狗放弃(abandoned)的执行线程不得覆盖error终态.
    """
    task = _TASKS[check_id]
    task["status"] = "running"
    task["progress"] = {"total": len(qa_pairs), "completed": 0}
    _persist(check_id)
    try:
        engine = get_engine()
        _bind_scene_knowledge(scene)
        samples = []
        for pair in qa_pairs:
            samples.append(_verify_sample(pair, engine))
            task["progress"] = {"total": len(qa_pairs),
                                "completed": len(samples)}
            _persist(check_id)
        counts = {"total": len(samples), "consistent": 0,
                  "inconsistent": 0, "undetermined": 0}
        for sample in samples:
            key = sample["consistency_result"]
            if key in counts:
                counts[key] += 1
        with _commit_lock(check_id):
            if not task.get("abandoned"):
                task["report"] = {
                    "check_id": check_id,
                    "run_at": datetime.now().isoformat(timespec="seconds"),
                    "rules_snapshot": task["snapshot"],
                    "summary": counts,
                    "samples": samples,
                }
                task["status"] = "done"
            _persist(check_id)
    except Exception as exc:
        with _commit_lock(check_id):
            if not task.get("abandoned"):
                task["status"] = "error"
                task["error"] = {"code": "ENGINE_ERROR",
                                 "message": f"{type(exc).__name__}: {exc}"}
            _persist(check_id)


def _mark_timeout(check_id: str) -> None:
    """看门狗超时: 执行线程被放弃(线程不可强杀), 任务置error ENGINE_TIMEOUT."""
    task = _TASKS[check_id]
    task["abandoned"] = True
    with _commit_lock(check_id):
        if task.get("status") != "done":
            task["status"] = "error"
            task["error"] = {"code": "ENGINE_TIMEOUT",
                             "message": "校验引擎执行超时"}
            _persist(check_id)


def _persist(check_id: str) -> None:
    task = _TASKS[check_id]
    directory = CHECKS_DIR / check_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"status": task["status"], "scene": task.get("scene", ""),
               "dataset_id": task.get("dataset_id"),
               "snapshot": task["snapshot"],
               "progress": task.get("progress"),
               "report": task.get("report"), "error": task.get("error")}
    (directory / "state.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def _get_task(check_id: str) -> dict[str, Any] | None:
    task = _TASKS.get(check_id)
    if task is not None:
        return task
    return _load_task(check_id)


def _load_task(check_id: str) -> dict[str, Any] | None:
    """磁盘回读(进程重启后仍可查历史任务); 缺失/非法id→None."""
    if not _SAFE_ID_RE.match(check_id):
        return None
    path = CHECKS_DIR / check_id / "state.json"
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    task: dict[str, Any] = {
        "status": str(raw.get("status", "error")),
        "scene": str(raw.get("scene", "")),
        "dataset_id": raw.get("dataset_id"),
        "snapshot": raw.get("snapshot") or {},
        "progress": raw.get("progress") or {"total": 0, "completed": 0},
        "report": raw.get("report"),
        "error": raw.get("error"),
    }
    _TASKS[check_id] = task
    _COMMIT_LOCKS.setdefault(check_id, threading.Lock())
    return task


def _persist_dataset_index() -> None:
    CHECKS_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_INDEX_PATH.write_text(
        json.dumps(_DATASET_LAST, ensure_ascii=False), encoding="utf-8")


def _dataset_check_id(dataset_id: str) -> str | None:
    if dataset_id in _DATASET_LAST:
        return _DATASET_LAST[dataset_id]
    if not DATASET_INDEX_PATH.exists():
        return None
    try:
        mapping = json.loads(DATASET_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    _DATASET_LAST.update({str(k): str(v) for k, v in mapping.items()
                          if isinstance(k, str) and isinstance(v, str)})
    return _DATASET_LAST.get(dataset_id)


def _worker() -> None:
    while True:
        check_id = _QUEUE.get()
        if check_id is None:
            break
        payload = _TASKS.get(check_id)
        if payload is None:
            continue
        runner = threading.Thread(
            target=execute_check,
            args=(check_id, payload["scene"], payload["qa_pairs"]),
            daemon=True)
        runner.start()
        runner.join(timeout=CHECK_TIMEOUT_SEC)
        if runner.is_alive():
            _mark_timeout(check_id)


def _ensure_worker() -> None:
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    threading.Thread(target=_worker, daemon=True).start()
    _WORKER_STARTED = True


def _new_check(scene: str, qa_pairs: list[QaPair],
               dataset_id: str | None) -> str:
    check_id = f"chk-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    _TASKS[check_id] = {
        "status": "queued", "scene": scene, "qa_pairs": qa_pairs,
        "snapshot": current_snapshot(scene), "dataset_id": dataset_id,
        "progress": {"total": len(qa_pairs), "completed": 0},
    }
    _COMMIT_LOCKS[check_id] = threading.Lock()
    if dataset_id:
        _DATASET_LAST[dataset_id] = check_id
        _persist_dataset_index()
    _persist(check_id)
    _ensure_worker()
    _QUEUE.put(check_id)
    return check_id


# ── API路由 ────────────────────────────────────────────────────────────────

router = APIRouter()


@router.post("/api/ner")
def extract_ner(body: dict) -> dict:
    """POST /api/ner: 查询文本→NER实体列表(用于召回前的实体可视化).

    轻量端点(正则+词典匹配, 零模型, 毫秒级):
    返回 [{text, kind, kind_zh, recall_channel, color, start, end}]
    kind: pzxq_id(项目唯一标识符→ID-Graph硬桥) / domain_term(领域
    术语→Lexical/BM25) / chinese(中文实体→BM25/Dense) / mixed(混合).
    """
    from fastapi import Body as _Body  # noqa: F401
    text = str(body.get("text", "")).strip()
    if not text:
        return {"ok": True, "data": {"entities": []}}
    from algorithms.consistency.entity_detector import extract_entities
    from algorithms.consistency.ner_lexicon import load_lexicon
    directory = KNOWLEDGE_DIR / "scene1"
    lexicon_path = (directory / "lexicon.json"
                    if (directory / "lexicon.json").exists()
                    else BASE / "config/ner_lexicons/srs_scene1.json")
    lexicon = load_lexicon(lexicon_path)
    entities = extract_entities(text, lexicon)
    kind_meta = {
        "pzxq_id": ("项目唯一标识符", "ID-Graph硬桥", "#6366f1"),
        "domain_term": ("领域术语", "Lexical/BM25", "#059669"),
        "chinese": ("中文实体", "BM25/Dense", "#d97706"),
        "mixed": ("混合实体", "BM25/Dense", "#0891b2"),
    }
    out = []
    for e in entities:
        meta = kind_meta.get(e.kind, ("其他", "多通道", "#64748b"))
        out.append({
            "text": e.surface,
            "kind": e.kind,
            "kind_zh": meta[0],
            "recall_channel": meta[1],
            "color": meta[2],
            "start": e.start,
            "end": e.end,
        })
    return {"ok": True, "data": {"entities": out}}


def _validate_qa_pairs(qa_pairs: list[QaPair]) -> None:
    if not qa_pairs:
        raise HTTPException(400, "qa_pairs缺失或为空")
    for pair in qa_pairs:
        if not str(pair.source).strip():
            raise HTTPException(400, f"qa_pair {pair.sample_id} source缺失")


def _acceptance_payload(check_id: str) -> dict[str, Any]:
    task = _TASKS[check_id]
    return {"ok": True, "data": {"check_id": check_id,
                                 "status": task["status"],
                                 "rules_snapshot": task["snapshot"]}}


def _error_payload(task: dict[str, Any]) -> dict[str, Any]:
    error = task.get("error") if isinstance(task.get("error"), dict) else None
    if error is None:
        error = {"code": "ENGINE_ERROR", "message": "校验引擎执行异常"}
    return {"ok": False,
            "error": {"code": str(error.get("code", "ENGINE_ERROR")),
                      "message": str(error.get("message", ""))}}


@router.post("/api/check")
def start_check(request: CheckRequest) -> dict[str, Any]:
    if request.scene not in SCENES:
        raise HTTPException(404, f"场景未接入: {request.scene}")
    _validate_qa_pairs(request.qa_pairs)
    if request.expert_knowledge is not None:
        declared = _SCENE_ALIASES.get(request.expert_knowledge.scene,
                                      request.expert_knowledge.scene)
        if declared != request.scene:
            raise HTTPException(400, "expert_knowledge.scene须与scene一致")
        sync_expert_knowledge(request.scene, request.expert_knowledge)
    check_id = _new_check(request.scene, list(request.qa_pairs), None)
    return _acceptance_payload(check_id)


def _coerce_qa_pair(entry: dict[str, Any]) -> QaPair:
    """数据集落库qa_pair → 契约模型(兼容旧版source对象→doc_ref字符串)."""
    data = dict(entry)
    source = data.get("source")
    if isinstance(source, dict):
        data["source"] = str(source.get("doc_ref", ""))
    return QaPair(**data)


@router.post("/api/datasets/{dataset_id}/check")
def start_dataset_check(dataset_id: str) -> dict[str, Any]:
    path = DATASETS_DIR / f"{dataset_id}.json"
    if not path.exists():
        raise HTTPException(404, f"数据集不存在: {dataset_id}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    declared = str(raw.get("scene") or raw.get("cat") or "scene1")
    scene = _SCENE_ALIASES.get(declared, declared)
    if scene not in SCENES:
        raise HTTPException(404, f"场景未接入: {scene}")
    qa_pairs = [_coerce_qa_pair(p) for p in raw.get("qa_pairs", [])]
    _validate_qa_pairs(qa_pairs)
    check_id = _new_check(scene, qa_pairs, dataset_id)
    return _acceptance_payload(check_id)


@router.get("/api/check-reports/{check_id}")
def get_report(check_id: str) -> dict[str, Any]:
    task = _get_task(check_id)
    if task is None:
        raise HTTPException(404, f"check_id不存在: {check_id}")
    status = task["status"]
    if status == "error":
        return _error_payload(task)
    data: dict[str, Any] = {"check_id": check_id, "status": status}
    if status == "done" and task.get("report"):
        data["report"] = task["report"]
    return {"ok": True, "data": data}


@router.get("/api/check-status/{check_id}")
def get_status(check_id: str) -> dict[str, Any]:
    task = _get_task(check_id)
    if task is None:
        raise HTTPException(404, f"check_id不存在: {check_id}")
    status = task["status"]
    if status == "error":
        return _error_payload(task)
    data: dict[str, Any] = {"check_id": check_id, "status": status}
    if status in ("queued", "running"):
        progress = task.get("progress") or {"total": 0, "completed": 0}
        data["progress"] = dict(progress)
    if status == "done" and task.get("report"):
        data["summary"] = task["report"]["summary"]
    return {"ok": True, "data": data}


@router.get("/api/datasets/{dataset_id}/check-status")
def get_dataset_status(dataset_id: str) -> dict[str, Any]:
    check_id = _dataset_check_id(dataset_id)
    if check_id is None:
        raise HTTPException(404, f"数据集无check记录: {dataset_id}")
    return get_status(check_id)
