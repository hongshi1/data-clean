# -*- coding: utf-8 -*-
"""反向代理服务器：前端原型静态托管 + /api/* 转发到后端(127.0.0.1:8300)。

用途：把「微调数据集构建平台-一致性校验增强版.html」与后端API聚合在同一端口(8399)，
供本地访问与公网隧道（cloudflared等）对外暴露。

访问控制（网关层Basic Auth，一次通过浏览器自动缓存，后续交互无需token）:
  用户名/密码读环境变量 PROXY_USER / PROXY_PASS (默认 admin / nankai-srs-2026)。
  对外分发时只需告知凭据；HTML内部登录页与API调用凭据与此一致。

路由：
  /                     → 原型HTML（微调数据集构建平台-一致性校验增强版.html）
  /images/*             → 原型目录静态图片
  /api/*                → 转发到 http://127.0.0.1:8300/api/*（含Basic Auth透传）
  /{其他文件}           → 原型目录静态文件，不存在则回退到HTML

用法： python -X utf8 tools/reverse_proxy.py [--port 8399]
"""
import argparse
import base64
import os
import secrets

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE / "docs" / "doc11" / "原型模板"
INDEX_HTML = FRONTEND_DIR / "微调数据集构建平台-一致性校验增强版.html"
UPSTREAM = "http://127.0.0.1:8300"

PROXY_USER = os.environ.get("PROXY_USER", "admin")
PROXY_PASS = os.environ.get("PROXY_PASS", "nankai-srs-2026")

app = FastAPI(title="SRS前端反向代理")
client = httpx.AsyncClient(base_url=UPSTREAM, timeout=30.0)

HOP_HEADERS = {"host", "content-length", "transfer-encoding", "connection",
               "keep-alive", "accept-encoding"}


def _auth_ok(header_value: str) -> bool:
    """校验 Basic Authorization 头 (constant-time比较)."""
    if not header_value.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(header_value[6:]).decode("utf-8")
        user, _, pwd = raw.partition(":")
    except (ValueError, UnicodeDecodeError):
        return False
    return (secrets.compare_digest(user, PROXY_USER)
            and secrets.compare_digest(pwd, PROXY_PASS))


@app.middleware("http")
async def gateway_auth(request: Request, call_next):
    """网关层访问门槛: 浏览器首访弹Basic Auth窗, 通过后自动缓存凭据."""
    if not _auth_ok(request.headers.get("authorization", "")):
        return Response(status_code=401, headers={
            "WWW-Authenticate": 'Basic realm="SRS Platform"'})
    return await call_next(request)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_api(path: str, request: Request):
    """把 /api/* 原样转发到后端8300（含Authorization头与请求体）。"""
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
    try:
        r = await client.request(request.method, f"/api/{path}", content=body,
                                 headers=headers, params=dict(request.query_params))
    except httpx.ConnectError:
        return Response(content='{"detail": "后端8300未启动，请先运行 python -X utf8 server/main.py"}',
                        status_code=502, media_type="application/json")
    resp_headers = {k: v for k, v in r.headers.items()
                    if k.lower() not in HOP_HEADERS}
    return Response(content=r.content, status_code=r.status_code,
                    headers=resp_headers, media_type=r.headers.get("content-type"))


if (FRONTEND_DIR / "images").exists():
    app.mount("/images", StaticFiles(directory=str(FRONTEND_DIR / "images")), name="images")


@app.get("/")
def index():
    return FileResponse(str(INDEX_HTML), media_type="text/html; charset=utf-8")


@app.get("/{file_path:path}")
def static_files(file_path: str):
    """其余路径按原型目录静态文件处理，未命中回退HTML（单页应用行为）。"""
    if file_path and ".." not in file_path:
        f = FRONTEND_DIR / file_path
        if f.exists() and f.is_file():
            return FileResponse(str(f))
    return FileResponse(str(INDEX_HTML), media_type="text/html; charset=utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="前端反向代理（静态+API转发）")
    ap.add_argument("--port", type=int, default=8399)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    print(f"反向代理: http://{args.host}:{args.port}  (静态: {FRONTEND_DIR} | API→{UPSTREAM})")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
