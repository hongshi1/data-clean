# -*- coding: utf-8 -*-
"""提取kimi调用配置 + 实测万擎连通性"""
import sys
import re
import json
import time
sys.stdout.reconfigure(encoding="utf-8")

src = open("tools/m7_llm_adjudication.py", encoding="utf-8").read()
cfg = {}
for pat, key in [
    (r"KIMI_URL\s*=\s*[\"\'](.*?)[\"\']", "KIMI_URL"),
    (r"KIMI_KEY\s*=\s*[\"\'](.*?)[\"\']", "KIMI_KEY"),
    (r"GLM_URL\s*=\s*[\"\'](.*?)[\"\']", "GLM_URL"),
    (r"GLM_KEY\s*=\s*[\"\'](.*?)[\"\']", "GLM_KEY"),
    (r"KIMI_MODEL\s*=\s*[\"\'](.*?)[\"\']", "KIMI_MODEL"),
    (r"GLM_MODEL\s*=\s*[\"\'](.*?)[\"\']", "GLM_MODEL"),
]:
    m = re.search(pat, src)
    if m:
        cfg[key] = m.group(1)
# model字段
models = re.findall(r"[\"\']model[\"\']\s*:\s*[\"\']([^\"\']+)[\"\']", src)
print("配置:", {k: (v[:50] + "..." if len(v) > 50 else v) for k, v in cfg.items()})
print("model字段:", set(models))

# 实测: 用找到的配置发一个最小请求
import urllib.request
url = cfg.get("KIMI_URL") or "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
key = cfg.get("KIMI_KEY", "")
model = cfg.get("KIMI_MODEL") or (models[0] if models else "kimi-k2.6")
body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "回复两个字: 连通"}],
    "max_tokens": 500,
}).encode()
req = urllib.request.Request(url, data=body, headers={
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read())
        msg = j.get("choices", [{}])[0].get("message", {})
        content = msg.get("content", "") or msg.get("reasoning_content", "")
        print(f"\n实测成功 [{time.time()-t0:.1f}s] model={j.get('model', model)}")
        print("回复:", content[:80])
        print("usage:", j.get("usage", {}))
except Exception as e:
    print(f"\n实测失败: {type(e).__name__}: {str(e)[:200]}")

# 再测GLM(万擎)
url2 = cfg.get("GLM_URL")
key2 = cfg.get("GLM_KEY")
model2 = cfg.get("GLM_MODEL")
body2 = json.dumps({
    "model": model2,
    "messages": [{"role": "user", "content": "回复两个字: 连通"}],
    "max_tokens": 500,
}).encode()
req2 = urllib.request.Request(url2, data=body2, headers={
    "Authorization": f"Bearer {key2}",
    "Content-Type": "application/json",
})
t0 = time.time()
try:
    with urllib.request.urlopen(req2, timeout=60) as r:
        j = json.loads(r.read())
        msg = j.get("choices", [{}])[0].get("message", {})
        print(f"\nGLM(万擎)实测成功 [{time.time()-t0:.1f}s] model={j.get('model', model2)}")
        print("回复:", (msg.get("content", "") or msg.get("reasoning_content", ""))[:80])
except Exception as e:
    print(f"\nGLM(万擎)实测失败: {type(e).__name__}: {str(e)[:200]}")
