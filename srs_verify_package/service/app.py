"""srs_verify算法服务: 一致性校验三态裁决 + 证据提纯 (FastAPI).

对应文档: 80号. 端点:
  GET  /health           探活(NLI引擎模式, 惰性)
  POST /verify           {question, answer, evidence[]} → 三态裁决
  POST /purify           {question, answer, evidence[]} → 提纯包(语句级)

部署契约:
  models/ 与运行目录同级(容器内COPY或volume挂载):
    models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7
    models/embedding/bge-large-zh-v1.5 (可选, 召回用)

用法: uvicorn service.app:app --host 0.0.0.0 --port 8400
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

import sys

_PKG_ROOT = Path(__file__).resolve().parents[1]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from srs_verify.verifier import CascadeVerifier  # noqa: E402

app = FastAPI(title="srs_verify算法服务", version="1.0.0")
_engine: dict[str, Any] = {}
_engine_lock = threading.Lock()
_STATUS: dict[str, str] = {"nli": "not_loaded", "error": ""}


class VerifyRequest(BaseModel):
    question: str
    answer: str
    evidence: list[dict[str, Any]]
    preset: str = "standard"      # fast/standard/full
    purify: bool = False


class PurifyRequest(BaseModel):
    question: str
    answer: str
    evidence: list[dict[str, Any]]
    mode: str = "statement"       # statement/evidence


def _get_engine(preset: str, purify: bool) -> CascadeVerifier:
    """引擎池: (preset, purify)档位缓存; NLI惰性加载(首次~35s)."""
    key = f"{preset}|{purify}"
    with _engine_lock:
        if key in _engine:
            return _engine[key]
        v = CascadeVerifier(preset=preset, purify=purify)
        # 触发NLI惰性加载(standard/full档), 记录状态
        _engine[key] = v
        return v


@app.on_event("startup")
def _preheat() -> None:
    """启动期预热standard引擎(NLI首次加载~35s移出首请求)."""
    import torch  # noqa: F401 — OpenMP顺序约束: torch先于numpy链
    try:
        _get_engine("standard", False)
        _STATUS["nli"] = "loaded"
    except (RuntimeError, OSError, ValueError) as e:
        _STATUS["nli"] = "unavailable"
        _STATUS["error"] = str(e)[:200]


@app.get("/health")
def health() -> dict:
    return {"ok": _STATUS["error"] == "", "nli": _STATUS["nli"],
            "error": _STATUS["error"], "engines": list(_engine)}


@app.post("/verify")
def verify(req: VerifyRequest) -> dict:
    """三态一致性裁决: 极简或完整证据格式均可(自动补全).

    返回含claim级明细(method/verdict/rationale/evidence_refs),
    供后端attrs落库与前端渲染.
    """
    try:
        import time as _time

        from srs_verify.eval_lib import build_qa_input
        v = _get_engine(req.preset, req.purify)
        seq = len(_engine) + 1
        record = {
            "instance_id": f"svc-{seq:06d}",
            "question": req.question,
            "answer": req.answer,
            "context_freeze_id": "algo-service",
            "evidence": req.evidence,
        }
        t0 = _time.perf_counter()
        full = v.verify_qa_input(build_qa_input(record))
        latency = round((_time.perf_counter() - t0) * 1000.0, 1)
        _STATUS["nli"] = "loaded" if req.preset != "fast" else "fast"
        return {"ok": True, "data": {
            "verdict": full.verdict,
            "rationale": full.rationale[:300],
            "claims": [{
                "claim_text": c.claim_text,
                "verdict": c.verdict,
                "method": c.method,
                "confidence": round(c.confidence, 3),
                "rationale": c.rationale[:160],
                "evidence_refs": list(c.evidence_refs),
            } for c in full.claim_results],
            "diagnostics": list(full.diagnostics),
            "latency_ms": latency,
        }}
    except (RuntimeError, ValueError, OSError) as e:
        _STATUS["error"] = str(e)[:200]
        return {"ok": False, "error": str(e)[:200]}


@app.post("/purify")
def purify_endpoint(req: PurifyRequest) -> dict:
    """证据提纯: statement模式(句/行级语句) 或 evidence模式(原块)."""
    from srs_verify.evidence_purifier import PurificationConfig, purify
    try:
        cfg = PurificationConfig(mode=req.mode)
        pack = purify(req.question, req.answer, req.evidence, cfg)
        return {"ok": True, "data": {
            "mode": pack["mode"], "stats": pack["stats"],
            "kept": pack["kept"][:20], "removed": pack["removed"][:20]}}
    except (RuntimeError, ValueError) as e:
        return {"ok": False, "error": str(e)[:200]}
