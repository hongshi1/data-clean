"""统一校验服务模块（南开对接契约三接口）.

接口①POST /api/check(发起, expert_knowledge幂等同步+快照绑定, 异步)
接口②GET /api/check-reports/{check_id}(CheckReport契约格式)
接口③GET /api/check-status/{check_id}(任务态机: queued→running→done/error)
数据集级: POST /api/datasets/{id}/check, GET /api/datasets/{id}/check-status

qa_pair外键解析:
  source.doc_ref → 证据源(本模块在chunk语料解析该文档并召回)
  knowledge_refs → 规则过滤(缺省=cat全部规则; 报告侧按rule_id过滤)

条目态映射: support→pass, not_in_evidence→warn(无法判定),
            refute→fail(不一致); 执行异常→未校验(≠数据有问题)

专家知识: {scene(须与cat一致), lexicon, rulepack} → 幂等覆盖写入
知识库(data/agent_knowledge/{cat}/) → 发起时快照绑定check_id。

任务执行: 单工作线程串行(避免模块级词典/规则包默认值的并发竞争),
模块顶层零I/O, 引擎(召回+验证器)首次执行惰性预热。
"""
from __future__ import annotations

import json
import queue
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parents[1]

#: 场景注册表: cat → 校验配置(未注册=404"场景未接入")
CATS: dict[str, dict[str, str]] = {
    "srs": {"scene": "srs_scene1"},
}

KNOWLEDGE_DIR = BASE / "data/agent_knowledge"
CHECKS_DIR = BASE / "data/agent_checks"
DATASETS_DIR = BASE / "data/agent_datasets"

_ISSUE_TYPE_BY_FAMILY = {
    "TERM": "术语不一致",
    "PARAM": "参数不一致",
    "LOGIC": "逻辑不一致",
    "GJB": "GJB合规不一致",
}
_RESULT_TO_STATUS = {"support": "pass", "refute": "fail",
                     "not_in_evidence": "warn"}

#: 任务注册表(check_id → 状态/报告; 进程内存+磁盘双写)
_TASKS: dict[str, dict[str, Any]] = {}
#: 数据集→最近check_id
_DATASET_LAST: dict[str, str] = {}
#: 单工作线程(串行执行, 保护模块级场景默认值)
_QUEUE: "queue.Queue[str]" = queue.Queue()
_WORKER_STARTED = False
_ENGINE: dict[str, Any] | None = None


# ── 契约模型 ────────────────────────────────────────────────────────────────

class SourceRef(BaseModel):
    doc_ref: str


class QaPair(BaseModel):
    sample_id: str
    question: str
    answer: str
    source: SourceRef
    knowledge_refs: list[str] = Field(default_factory=list)


class ExpertKnowledge(BaseModel):
    scene: str
    lexicon: dict[str, Any] | None = None
    rulepack: dict[str, Any] | None = None


class CheckRequest(BaseModel):
    cat: str
    qa_pairs: list[QaPair]
    expert_knowledge: ExpertKnowledge | None = None


# ── 专家知识: 幂等同步 + 快照 ─────────────────────────────────────────────

def sync_expert_knowledge(cat: str, knowledge: ExpertKnowledge) -> str:
    """幂等覆盖写入(rule_id对齐) + 提交期校验(契约: 原子完成同步+校验).

    非法schema在提交时即400, 不落库不污染后续check.
    """
    directory = KNOWLEDGE_DIR / cat
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


def current_snapshot(cat: str) -> dict[str, Any]:
    """cat当前知识状态(提交的或内置的) → 发起时绑定check_id的快照."""
    directory = KNOWLEDGE_DIR / cat
    marker = directory / "version.json"
    if marker.exists():
        return json.loads(marker.read_text(encoding="utf-8"))
    return {"version": f"builtin-{cat}", "n_rules": _count_rules(None)}


def _count_rules(rulepack_path: Path | None) -> int:
    if rulepack_path is not None and rulepack_path.exists():
        raw = json.loads(rulepack_path.read_text(encoding="utf-8"))
        return len(raw.get("rules", [])) if isinstance(raw, dict) else 0
    builtin = BASE / "config/rulepacks/srs_gjb_v1.json"
    if builtin.exists():
        raw = json.loads(builtin.read_text(encoding="utf-8"))
        return len(raw.get("rules", [])) if isinstance(raw, dict) else 0
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
    """doc_ref → chunk语料中的完整文档名(前缀匹配; 唯一命中才有效)."""
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
    raise LookupError(f"doc_ref无法解析: {doc_ref!r}")


def _issue_type(rule_id: str) -> str:
    family = str(rule_id).split("-", 1)[0].upper()
    return _ISSUE_TYPE_BY_FAMILY.get(family, "语义不一致")


def verify_one(qa_pair: QaPair, engine: dict[str, Any],
               scene: str, use_nli: bool = True) -> dict[str, Any]:
    """单条qa_pair: 召回→验证→条目态+issues(按knowledge_refs过滤)."""
    from algorithms.consistency.qa_models import (
        QAInput,
        RetrievedEvidence,
        SourceRef as QaSourceRef,
    )
    import re as _re
    title_prefix = _re.compile(r"^\[表格标题[^\]]*\]")
    doc = resolve_doc(qa_pair.source.doc_ref, engine["docs"])
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
    issues = []
    for loc in result.localizations:
        for rule_id in loc.check_item_candidates or ("未分类",):
            if wanted is not None and rule_id not in wanted:
                continue
            issues.append({
                "type": _issue_type(rule_id),
                "desc": loc.rationale[:120],
                "rule_id": rule_id,
            })
    status = _RESULT_TO_STATUS.get(result.verdict, "warn")
    return {
        "sample_id": qa_pair.sample_id,
        "question": qa_pair.question,
        "answer": qa_pair.answer,
        "source": {"doc_ref": qa_pair.source.doc_ref},
        "status": status,
        "result": result.verdict,
        "issues": issues,
    }


def _bind_scene_knowledge(cat: str) -> None:
    """把cat当前知识(提交的优先)绑定为模块级场景默认值(串行线程内安全)."""
    from algorithms.consistency.ner_lexicon import (
        load_lexicon,
        set_default_lexicon,
    )
    from algorithms.consistency.rulepack import (
        load_rulepack,
        set_default_rulepack,
    )
    directory = KNOWLEDGE_DIR / cat
    lexicon_path = directory / "lexicon.json"
    pack_path = directory / "rulepack.json"
    scene = CATS[cat]["scene"]
    lexicon_src = (lexicon_path if lexicon_path.exists()
                   else BASE / "config/ner_lexicons/srs_scene1.json")
    pack_src = (pack_path if pack_path.exists()
                else BASE / f"config/rulepacks/{scene.replace('srs_scene1', 'srs_gjb_v1')}.json")
    set_default_lexicon(load_lexicon(lexicon_src))
    set_default_rulepack(load_rulepack(pack_src))


def execute_check(check_id: str, cat: str, qa_pairs: list[QaPair]) -> None:
    """工作线程内执行一次check: 条目级异常→未校验, 不落结果不失败任务."""
    task = _TASKS[check_id]
    task["status"] = "running"
    _persist(check_id)
    try:
        engine = get_engine()
        _bind_scene_knowledge(cat)
        samples = []
        for pair in qa_pairs:
            try:
                samples.append(verify_one(pair, engine, CATS[cat]["scene"]))
            except (LookupError, ValueError, RuntimeError) as exc:
                samples.append({
                    "sample_id": pair.sample_id,
                    "question": pair.question,
                    "answer": pair.answer,
                    "source": {"doc_ref": pair.source.doc_ref},
                    "status": "未校验",
                    "result": "error",
                    "issues": [],
                    "error": f"{type(exc).__name__}: {exc}",
                })
        counts = {"total": len(samples), "pass": 0, "warn": 0, "fail": 0}
        for s in samples:
            if s["status"] in counts:
                counts[s["status"]] += 1
        task["report"] = {
            "check_id": check_id,
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "rules_snapshot": task["snapshot"],
            "summary": counts,
            "samples": samples,
        }
        task["status"] = "done"
    except Exception as exc:  # 引擎级异常: 任务error, 可重新发起
        task["status"] = "error"
        task["error"] = f"{type(exc).__name__}: {exc}"
    _persist(check_id)


def _persist(check_id: str) -> None:
    task = _TASKS[check_id]
    directory = CHECKS_DIR / check_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"status": task["status"], "snapshot": task["snapshot"],
               "report": task.get("report"), "error": task.get("error")}
    (directory / "state.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def _worker() -> None:
    while True:
        check_id = _QUEUE.get()
        if check_id is None:
            break
        payload = _TASKS[check_id]
        execute_check(check_id, payload["cat"], payload["qa_pairs"])


def _ensure_worker() -> None:
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    threading.Thread(target=_worker, daemon=True).start()
    _WORKER_STARTED = True


def _new_check(cat: str, qa_pairs: list[QaPair],
               dataset_id: str | None) -> dict[str, Any]:
    check_id = f"chk-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    _TASKS[check_id] = {
        "status": "queued", "cat": cat, "qa_pairs": qa_pairs,
        "snapshot": current_snapshot(cat), "dataset_id": dataset_id,
    }
    if dataset_id:
        _DATASET_LAST[dataset_id] = check_id
    _persist(check_id)
    _ensure_worker()
    _QUEUE.put(check_id)
    return _TASKS[check_id]


# ── API路由 ────────────────────────────────────────────────────────────────

router = APIRouter()


@router.post("/api/check")
def start_check(request: CheckRequest) -> dict[str, Any]:
    if request.cat not in CATS:
        raise HTTPException(404, f"场景未接入: {request.cat}")
    if not request.qa_pairs:
        raise HTTPException(400, "qa_pairs缺失或为空")
    for pair in request.qa_pairs:
        if not str(pair.source.doc_ref).strip():
            raise HTTPException(400, f"qa_pair {pair.sample_id} source缺失")
    if request.expert_knowledge is not None:
        if request.expert_knowledge.scene != request.cat:
            raise HTTPException(400, "expert_knowledge.scene须与cat一致")
        sync_expert_knowledge(request.cat, request.expert_knowledge)
    task = _new_check(request.cat, list(request.qa_pairs), None)
    return {"ok": True, "data": {
        "check_id": next(k for k, v in _TASKS.items() if v is task),
        "status": task["status"],
        "rules_snapshot": task["snapshot"],
    }}


@router.post("/api/datasets/{dataset_id}/check")
def start_dataset_check(dataset_id: str) -> dict[str, Any]:
    path = DATASETS_DIR / f"{dataset_id}.json"
    if not path.exists():
        raise HTTPException(404, f"数据集不存在: {dataset_id}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    qa_pairs = [QaPair(**p) for p in raw.get("qa_pairs", [])]
    if not qa_pairs:
        raise HTTPException(400, "数据集qa_pairs为空")
    task = _new_check(str(raw.get("cat", "srs")), qa_pairs, dataset_id)
    check_id = next(k for k, v in _TASKS.items() if v is task)
    return {"ok": True, "data": {
        "check_id": check_id, "status": task["status"],
        "rules_snapshot": task["snapshot"],
    }}


@router.get("/api/check-reports/{check_id}")
def get_report(check_id: str) -> dict[str, Any]:
    task = _TASKS.get(check_id)
    if task is None:
        raise HTTPException(404, f"check_id不存在: {check_id}")
    if task["status"] == "done":
        return {"ok": True, "data": {"report": task["report"],
                                     "status": "done"}}
    if task["status"] == "error":
        return {"ok": True, "data": {"status": "error",
                                     "reason": task.get("error", "")}}
    return {"ok": True, "data": {"status": task["status"]}}


@router.get("/api/check-status/{check_id}")
def get_status(check_id: str) -> dict[str, Any]:
    task = _TASKS.get(check_id)
    if task is None:
        raise HTTPException(404, f"check_id不存在: {check_id}")
    data: dict[str, Any] = {"status": task["status"]}
    if task["status"] == "done" and task.get("report"):
        data["summary"] = task["report"]["summary"]
    return {"ok": True, "data": data}


@router.get("/api/datasets/{dataset_id}/check-status")
def get_dataset_status(dataset_id: str) -> dict[str, Any]:
    check_id = _DATASET_LAST.get(dataset_id)
    if check_id is None:
        raise HTTPException(404, f"数据集无check记录: {dataset_id}")
    return get_status(check_id)
