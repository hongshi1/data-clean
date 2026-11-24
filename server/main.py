#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SRS上下文关联图谱平台 — FastAPI后端

端点:
  GET  /api/docs                     文档列表
  POST /api/activate                 question → 径向激活子图(召回模式)
  GET  /api/qa                       QA列表(分页+筛选)
  GET  /api/assets/{doc_num}/{path}  静态资源(图片等)
  GET  /api/section/{doc_num}/{section}   章节正文
  GET  /api/table/{doc_num}          表格HTML
  GET  /api/mermaid/{doc_num}/{fig_num}  Mermaid导出
  GET  /api/datasets / POST /api/upload  上传数据集(轻量TXT图谱)
  GET  /api/verify/qa_list           91条冻结QA轻量列表(scene1)
  POST /api/verify_qa/{instance_id}  按id校验冻结QA(preset/scene可选)
  POST /api/verify                   请求级QA校验(证据由调用方提供)
  (check三接口见 server/check_service.py; 场景5见 /api/scenario5/*)

启动: python server/main.py  (或 uvicorn server.main:app --port 8300)
"""
import json
import os
import re
import secrets
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from algorithms.context_graph import ContextGraph  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.verifier import CascadeVerifier  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
QA_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_final.json"
QA_FROZEN_PATH = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER_LABELS_PATH = (
    BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
    / "final_labels.jsonl"
)

app = FastAPI(title="SRS上下文关联图谱平台", version="0.2.0")
from server.check_service import router as _check_router  # noqa: E402
app.include_router(_check_router)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 访问控制: 环境变量 ACCESS_TOKEN 非空时启用 HTTP Basic Auth
#   启动: $env:ACCESS_TOKEN="你的密码"; python -X utf8 server/main.py
#   本地开发不设该变量 = 无认证(行为不变)
# ---------------------------------------------------------------------------
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
_security = HTTPBasic(auto_error=False)


def auth_guard(credentials: HTTPBasicCredentials = Depends(_security)):
    if not ACCESS_TOKEN:
        return
    ok = credentials is not None and secrets.compare_digest(
        credentials.password, ACCESS_TOKEN)
    if not ok:
        raise HTTPException(
            401, "需要访问认证", headers={"WWW-Authenticate": "Basic"})
    return credentials


# 注册到所有API路由(挂载的纯前端静态资源除外)
app.router.dependencies.append(Depends(auth_guard))


CG = ContextGraph()
QA_ALL = json.load(open(QA_PATH, encoding="utf-8"))

# ---------------------------------------------------------------------------
# 内容服务: 正文全文 / 表格HTML / Mermaid导出
# ---------------------------------------------------------------------------
import glob as _glob  # noqa: E402

_SECTION_TEXTS: dict = {}   # doc -> {section: 正文}
_TABLE_BODIES: dict = {}    # doc -> {caption: html}
for _p in sorted(_glob.glob(str(BASE / "data/gjb_438c/mineru_standard/*/office/*content_list.json"))):
    _name = os.path.basename(_p).replace("_content_list.json", "")
    _cl = json.load(open(_p, encoding="utf-8"))
    _st: dict = {}
    _cur = ""
    for _it in _cl:
        if not isinstance(_it, dict):
            continue
        if _it.get("type") == "text":
            _t = _it.get("text", "")
            _m = re.match(r"^(\d+(?:\.\d+)*)\s+", _t.strip())
            if _m:
                _cur = _m.group(1)
            if len(_t.strip()) > 15:
                _st[_cur] = _st.get(_cur, "") + " " + _t.strip()
        elif _it.get("type") == "table":
            _caps = _it.get("table_caption", [])
            if _caps:
                _TABLE_BODIES.setdefault(_name, {})[_caps[0]] = _it.get("table_body", "")
    _SECTION_TEXTS[_name] = _st

try:
    MERMAID_EXPORT = json.load(
        open(BASE / "data/gjb_438c/anchor_v2/mermaid_export.json", encoding="utf-8"))
except FileNotFoundError:
    MERMAID_EXPORT = {}


@app.get("/api/section/{doc_num}/{section}")
def get_section(doc_num: str, section: str):
    g = CG.docs.get(doc_num)
    if not g:
        raise HTTPException(404, f"文档{doc_num}不存在")
    text = _SECTION_TEXTS.get(g["meta"]["doc"], {}).get(section, "")
    title = next((n["payload"].get("title") for n in g["nodes"]
                  if n["type"] == "TXT" and n["section"] == section), "")
    return {"doc": g["meta"]["doc"], "section": section, "title": title, "text": text}


@app.get("/api/table/{doc_num}")
def get_table(doc_num: str, caption: str = Query(...)):
    g = CG.docs.get(doc_num)
    if not g:
        raise HTTPException(404, f"文档{doc_num}不存在")
    html = _TABLE_BODIES.get(g["meta"]["doc"], {}).get(caption)
    if html is None:
        raise HTTPException(404, f"表格「{caption}」未找到")
    return {"doc": g["meta"]["doc"], "caption": caption, "html": html}


@app.get("/api/mermaid/{doc_num}/{fig_num}")
def get_mermaid(doc_num: str, fig_num: str):
    g = CG.docs.get(doc_num)
    if not g:
        raise HTTPException(404, f"文档{doc_num}不存在")
    node = next((n for n in g["nodes"]
                 if n["type"] == "IMG" and n["id"] == f"img:{doc_num}:{fig_num}"), None)
    if not node:
        raise HTTPException(404, f"图{fig_num}不存在")
    key = node.get("payload", {}).get("mermaid_key")
    if not key or key not in MERMAID_EXPORT:
        return {"has_mermaid": False}
    mm = MERMAID_EXPORT[key]
    return {"has_mermaid": True, "mermaid": mm.get("mermaid", ""),
            "diagram_type": mm.get("diagram_type", ""),
            "caption": node["payload"].get("caption", "")}


# ---------------------------------------------------------------------------
# 数据集管理
# ---------------------------------------------------------------------------
from fastapi import UploadFile, File  # noqa: E402

UPLOAD_DIR = BASE / "data/gjb_438c/graph_store/uploads"
UPLOAD_REG = BASE / "data/gjb_438c/graph_store/uploads/registry.json"


def _load_uploads():
    """启动时重载上传数据集(轻量TXT图谱注册进CG)"""
    if not UPLOAD_REG.exists():
        return
    reg = json.load(open(UPLOAD_REG, encoding="utf-8"))
    for entry in reg.get("datasets", []):
        md_path = UPLOAD_DIR / f"{entry['doc_num']}.md"
        if not md_path.exists():
            continue
        text = md_path.read_text(encoding="utf-8")
        g = _build_upload_graph(entry["doc_num"], entry["doc"], text)
        CG.docs[entry["doc_num"]] = g
        for n in g["nodes"]:
            CG.node_index[(entry["doc_num"], n["id"])] = n


def _extract_sections_text(text: str) -> dict:
    secs, cur = {}, "0"
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(\d+(?:\.\d+)*)\s+(.*)$", line) or \
            re.match(r"^(\d+(?:\.\d+)*)\s+(\S.*)$", line)
        if m:
            cur = m.group(1)
            secs.setdefault(cur, "")
        elif len(line.strip()) > 10:
            secs[cur] = secs.get(cur, "") + " " + line.strip()
    return secs


def _build_upload_graph(doc_num: str, doc_name: str, text: str):
    """上传md → 轻量图谱(仅TXT节点+层级边)"""
    nodes, edges = [], []
    sections = _extract_sections_text(text)
    titles = {}
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(\d+(?:\.\d+)*)\s+(.*)$", line)
        if m:
            titles[m.group(1)] = m.group(2).strip()
    for sec, body in sections.items():
        nodes.append({
            "id": f"t:{doc_num}:{sec}", "type": "TXT",
            "label": f"{sec} {titles.get(sec, '')}"[:40], "doc": doc_name,
            "section": sec,
            "payload": {"title": titles.get(sec, ""), "level": sec.count(".") + 1,
                        "text_preview": body.strip()[:120], "text_len": len(body)},
        })
    ids = {n["id"] for n in nodes}
    for sec in sections:
        parts = sec.split(".")
        if len(parts) > 1:
            parent = ".".join(parts[:-1])
            pid = f"t:{doc_num}:{parent}"
            if pid in ids:
                edges.append({"s": f"t:{doc_num}:{sec}", "t": pid,
                              "type": "section_hierarchy", "w": 0.7, "ev": f"{sec}⊂{parent}"})
    from collections import Counter
    return {"meta": {"doc": doc_name, "doc_num": doc_num, "n_nodes": len(nodes),
                     "n_edges": len(edges), "n_items": 0,
                     "node_types": dict(Counter(n["type"] for n in nodes)),
                     "edge_types": dict(Counter(e["type"] for e in edges))},
            "nodes": nodes, "edges": edges, "items": []}


_load_uploads()


@app.get("/api/datasets")
def list_datasets():
    out = []
    for num, g in sorted(CG.docs.items()):
        m = g["meta"]
        out.append({
            "doc_num": num, "doc": m["doc"], "n_nodes": m["n_nodes"],
            "n_edges": m["n_edges"], "n_items": m["n_items"],
            "uploaded": num.startswith("u"),
            "checked": False,
            "check_summary": None,
        })
    return {"datasets": out}


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith((".md", ".markdown", ".txt")):
        raise HTTPException(400, "仅支持 .md/.markdown/.txt 格式")
    content = (await file.read()).decode("utf-8", errors="ignore")
    if len(content) < 100:
        raise HTTPException(400, "文件内容过短")
    # 分配编号
    reg = {"datasets": []}
    if UPLOAD_REG.exists():
        reg = json.load(open(UPLOAD_REG, encoding="utf-8"))
    n = len(reg["datasets"]) + 1
    doc_num = f"u{n}"
    doc_name = f"上传:{file.filename}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / f"{doc_num}.md").write_text(content, encoding="utf-8")
    g = _build_upload_graph(doc_num, doc_name, content)
    CG.docs[doc_num] = g
    for nd in g["nodes"]:
        CG.node_index[(doc_num, nd["id"])] = nd
    reg["datasets"].append({"doc_num": doc_num, "doc": doc_name,
                            "filename": file.filename})
    json.dump(reg, open(UPLOAD_REG, "w", encoding="utf-8"), ensure_ascii=False)
    return {"ok": True, "doc_num": doc_num, "doc": doc_name,
            "n_nodes": g["meta"]["n_nodes"]}


@app.post("/api/check/{doc_num}")
def run_check(doc_num: str):
    raise HTTPException(410, "旧数据集检查接口已下线，请使用POST /api/verify")


@app.get("/api/check/{doc_num}")
def get_check(doc_num: str):
    raise HTTPException(410, "旧数据集检查接口已下线，请使用POST /api/verify")


class SourceRefRequest(BaseModel):
    doc_id: str
    section: str = ""
    page: int | None = None
    block_id: str = ""
    row_id: str = ""
    region_id: str = ""


class EvidenceRequest(BaseModel):
    evidence_id: str
    text: str
    source_type: Literal["text", "table", "figure", "trace", "rule", "other"]
    source_ref: SourceRefRequest
    scope_id: str
    completeness: Literal["open", "closed", "unknown"] = "unknown"
    completeness_proof: str = ""
    extraction_method: str = ""
    extraction_confidence: float | None = None


class VerifyRequest(BaseModel):
    instance_id: str
    question: str
    answer: str
    context_freeze_id: str
    evidence: list[EvidenceRequest]
    preset: Literal["fast", "standard", "full"] = "fast"
    scene: str = "srs_scene1"


_VERIFIER_CACHE: dict[tuple[str, str], CascadeVerifier] = {}


def _get_verifier(preset: str, scene: str) -> CascadeVerifier:
    key = (preset, scene)
    if key not in _VERIFIER_CACHE:
        _VERIFIER_CACHE[key] = CascadeVerifier(preset=preset, scene=scene)
    return _VERIFIER_CACHE[key]


QA_VERIFIER = CascadeVerifier(preset="fast", scene="srs_scene1")


@app.post("/api/verify")
def verify_qa(req: VerifyRequest):
    """Verify an answer against caller-supplied frozen evidence only."""
    verifier = _get_verifier(req.preset, req.scene)
    request = QAInput(
        instance_id=req.instance_id,
        question=req.question,
        answer=req.answer,
        context_freeze_id=req.context_freeze_id,
        evidence=tuple(
            RetrievedEvidence(
                evidence_id=evidence.evidence_id,
                text=evidence.text,
                source_type=evidence.source_type,
                source_ref=SourceRef(**evidence.source_ref.model_dump()),
                scope_id=evidence.scope_id,
                completeness=evidence.completeness,
                completeness_proof=evidence.completeness_proof,
                extraction_method=evidence.extraction_method,
                extraction_confidence=evidence.extraction_confidence,
            )
            for evidence in req.evidence
        ),
    )
    try:
        result = verifier.verify_qa_input(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return asdict(result)


# ---------------------------------------------------------------------------
# 冻结QA便捷校验: 服务端托管91条scene1冻结QA(纯读), 供前端选择-校验-高亮
# ---------------------------------------------------------------------------
FROZEN_QA = load_frozen_qa(QA_FROZEN_PATH)
FROZEN_QA_INDEX = {row["instance_id"]: row for row in FROZEN_QA}
SILVER_VERDICTS = load_silver_labels(SILVER_LABELS_PATH)


@app.get("/api/verify/qa_list")
def verify_qa_list():
    """91条冻结QA轻量列表(question/answer截80字, 附silver参考标签)."""
    return [{
        "instance_id": row["instance_id"],
        "question": str(row["question"])[:80],
        "answer": str(row["answer"])[:80],
        "scene": "srs_scene1",
        "silver_verdict": SILVER_VERDICTS.get(row["instance_id"]),
    } for row in FROZEN_QA]


class VerifyByIdRequest(BaseModel):
    preset: Literal["fast", "standard", "full"] = "fast"
    scene: str = "srs_scene1"


@app.post("/api/verify_qa/{instance_id}")
def verify_qa_by_id(instance_id: str, body: VerifyByIdRequest):
    """按instance_id校验冻结QA(evidence原样透传, 供前端高亮联动)."""
    record = FROZEN_QA_INDEX.get(instance_id)
    if record is None:
        raise HTTPException(404, f"冻结QA {instance_id} 不存在")
    verifier = _get_verifier(body.preset, body.scene)
    request = build_qa_input(record)
    start = time.perf_counter()
    try:
        result = verifier.verify_qa_input(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    latency_ms = round((time.perf_counter() - start) * 1000.0, 3)
    payload = asdict(result)
    payload.update({
        "question": record["question"],
        "answer": record["answer"],
        "evidence": record["evidence"],
        "silver_verdict": SILVER_VERDICTS.get(instance_id),
        "latency_ms": latency_ms,
    })
    return payload


class ActivateReq(BaseModel):
    question: str
    doc: str | None = None
    k: int = 2
    top_k: int = 12
    min_w: float = 0.3


@app.get("/api/docs")
def list_docs():
    return {
        "docs": [
            {"doc_num": g["meta"]["doc_num"], "doc": g["meta"]["doc"],
             "n_nodes": g["meta"]["n_nodes"], "n_edges": g["meta"]["n_edges"],
             "n_items": g["meta"]["n_items"]}
            for g in CG.docs.values()
        ]
    }


@app.post("/api/activate")
def activate(req: ActivateReq):
    r = CG.activate(req.question, doc_num=req.doc, k=req.k,
                    top_k=req.top_k, min_w=req.min_w)
    return r


@app.get("/api/qa")
def list_qa(q: str | None = None, scenario: str | None = None,
            qa_type: str | None = None, label: str | None = None,
            injected: bool | None = None, page: int = 1, page_size: int = 20):
    items = QA_ALL
    if scenario:
        items = [x for x in items if str(x.get("scenario")) == scenario]
    if qa_type:
        items = [x for x in items if x.get("type") == qa_type]
    if label:
        items = [x for x in items if x.get("label") == label]
    if injected is not None:
        items = [x for x in items if bool(x.get("is_injected")) == injected]
    if q:
        ql = q.lower()
        items = [x for x in items
                 if ql in x.get("question", "").lower() or ql in x.get("answer", "").lower()]
    total = len(items)
    start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size,
            "items": items[start:start + page_size]}


@app.get("/api/assets/{doc_num}/{file_path:path}")
def get_asset(doc_num: str, file_path: str):
    g = CG.docs.get(doc_num)
    if not g:
        raise HTTPException(404, f"文档{doc_num}不存在")
    full = BASE / "data/gjb_438c/mineru_standard" / g["meta"]["doc"] / "office" / file_path
    if not full.exists() or ".." in file_path:
        raise HTTPException(404, "资源不存在")
    return FileResponse(str(full))


# ---------------------------------------------------------------------------
# 前端静态托管(单端口模式): npm run build 后, 直接访问 http://127.0.0.1:8300
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles  # noqa: E402

# ---------------------------------------------------------------------------
# 场景5: 安全帽佩戴场景一致性校验 API
# ---------------------------------------------------------------------------
try:
    from scenario5.cv_stack.helmet_pipeline import run_helmet_pipeline  # noqa: E402
    HAS_S5 = True
except ImportError:
    HAS_S5 = False

if HAS_S5:
    class Scenario5Request(BaseModel):
        image_path: str  # absolute or relative path to image
        user_text: str = "判断图片中是否有人员未佩戴安全帽"
        gpt_text: str = '{"task":"安全帽检测","answer":1,"evidence":["有人员未佩戴安全帽"]}'
        answer: int | None = None

    @app.post("/api/scenario5/analyze")
    def scenario5_analyze(req: Scenario5Request):
        """运行安全帽场景完整管线：Chunk→图内关系→QA解析→跨模态→校验."""
        img_path = Path(req.image_path)
        if not img_path.is_absolute():
            img_path = BASE / req.image_path
        if not img_path.is_file():
            raise HTTPException(status=404, detail=f"Image not found: {img_path}")
        try:
            result = run_helmet_pipeline(img_path, req.user_text, req.gpt_text, req.answer)
            return result
        except Exception as e:
            raise HTTPException(status=500, detail=str(e)) from e

    @app.get("/api/scenario5/sample_images")
    def scenario5_samples():
        """List sample images from PPE dataset."""
        ppe_dir = BASE / "scenario5" / "data" / "ppe_hardhat" / "extracted"
        if not ppe_dir.exists():
            return {"images": []}
        images = sorted(ppe_dir.glob("*.jpg"))[:20]
        return {
            "images": [
                {"path": str(img.relative_to(BASE)), "name": img.name}
                for img in images
            ],
        }

    @app.get("/api/scenario5/sleep_images")
    def scenario5_sleep_samples():
        """List sample images from sleep dataset."""
        sleep_dir = Path(
            r"C:\baidunetdiskdownload\5个场景数据集"
            r"\20260924-场景5样例数据及需求说明文档\test"
        )
        if not sleep_dir.exists():
            return {"images": []}
        images = sorted(sleep_dir.glob("*.jpg"))[:32]
        return {
            "images": [
                {"path": str(img), "name": img.name}
                for img in images
            ],
        }

DIST = BASE / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="fe-assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        """SPA fallback: 真实文件直接返回, 其余回index.html"""
        if full_path:
            f = DIST / full_path
            if f.exists() and f.is_file() and ".." not in full_path:
                return FileResponse(str(f))
        return FileResponse(str(DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8300)
