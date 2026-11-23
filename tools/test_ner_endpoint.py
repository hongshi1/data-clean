"""Test the /api/ner endpoint with real queries."""
import json
import urllib.request

BASE = "http://127.0.0.1:8300"
for text in ("数据库关闭接口的项目唯一标识符PZXQ-GN-SJKCZ-SJKGB是什么？",
             "SQL访问功能包括哪些操作？BLOB数据怎么处理？",
             "系统在桌面、平板、手持设备上运行方式名称分别是什么？"):
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(BASE + "/api/ner", data=body,
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    print(f"Q: {text[:40]}")
    for e in resp["data"]["entities"]:
        print(f"  {e['kind_zh']:10s} 「{e['text'][:30]}」"
              f" → {e['recall_channel']}")
    print()
