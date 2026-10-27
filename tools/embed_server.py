# -*- coding: utf-8 -*-
"""BGE embedding微服务 (运行于 .venv-embed, 零额外web依赖)

模型: BAAI/bge-small-zh-v1.5 (ONNX, Xenova转换) · 512维 · CLS pooling + L2归一化
端口: 127.0.0.1:8301
接口: POST /embed  {"texts": [...], "query": true|false}  → {"vectors": [[512...]...]}
      query=true 时为检索侧文本自动加BGE指令前缀
启动: .venv-embed\Scripts\python.exe tools\embed_server.py
"""
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE, "data/models/bge-small-zh-v1.5")
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："

sys.stdout.reconfigure(encoding="utf-8")

_tok = Tokenizer.from_file(os.path.join(MODEL_DIR, "tokenizer.json"))
_tok.no_padding()
_sess = ort.InferenceSession(
    os.path.join(MODEL_DIR, "onnx/model.onnx"),
    providers=["CPUExecutionProvider"])


def encode(texts, is_query=False, batch=32):
    out = []
    for i in range(0, len(texts), batch):
        chunk = [QUERY_PREFIX + t if is_query else t for t in texts[i:i + batch]]
        enc = _tok.encode_batch([t if t.strip() else "空" for t in chunk])
        maxlen = max(len(e.ids) for e in enc) or 1
        ids = np.zeros((len(enc), maxlen), dtype=np.int64)
        mask = np.zeros((len(enc), maxlen), dtype=np.int64)
        ttype = np.zeros((len(enc), maxlen), dtype=np.int64)
        for j, e in enumerate(enc):
            ids[j, :len(e.ids)] = e.ids
            mask[j, :len(e.ids)] = 1
        res = _sess.run(None, {"input_ids": ids, "attention_mask": mask,
                               "token_type_ids": ttype})
        cls = res[0][:, 0, :].astype(np.float32)          # CLS pooling
        cls /= (np.linalg.norm(cls, axis=1, keepdims=True) + 1e-12)
        out.append(cls)
    return np.concatenate(out, axis=0) if out else np.zeros((0, 512), np.float32)


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json({"ok": True, "model": "bge-small-zh-v1.5", "dim": 512})
        else:
            self._json({"ok": False}, 404)

    def do_POST(self):
        if self.path != "/embed":
            return self._json({"ok": False}, 404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            texts = body.get("texts", [])
            t0 = time.time()
            vecs = encode(texts, is_query=bool(body.get("query", False)))
            self._json({"ok": True, "vectors": vecs.tolist(),
                        "dim": int(vecs.shape[1]), "ms": int((time.time() - t0) * 1000)})
        except Exception as e:
            self._json({"ok": False, "error": str(e)[:200]}, 500)

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # 静默


if __name__ == "__main__":
    # 自检
    v = encode(["界面开发功能", "组件配置填写"], is_query=True)
    print("自检: shape", v.shape, "| 自相似度",
          round(float((v[0] * v[1]).sum()), 3))
    srv = HTTPServer(("127.0.0.1", 8301), H)
    print("BGE embedding服务已启动: http://127.0.0.1:8301 (Ctrl+C停止)")
    srv.serve_forever()
