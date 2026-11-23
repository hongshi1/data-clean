"""Test the recall-analysis endpoint."""
import json
import urllib.request

BASE = "http://127.0.0.1:8300"
for text in ("二维数组输出包含哪些功能？",
             "数据库关闭接口的PZXQ-GN-SJKCZ-SJKGB标识符是什么？"):
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(BASE + "/api/recall-analysis", data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    d = r["data"]
    print(f"Q: {text}")
    print(f"  entities({len(d['entities'])}): "
          + ", ".join(f"[{e['text']}:{e['kind_zh']}]" for e in d["entities"][:5]))
    print(f"  bm25_tokens({len(d['bm25_tokens'])}): {d['bm25_tokens'][:12]}")
    print(f"  id_graph: {len(d['id_graph'])} matches")
    for m in d["id_graph"][:2]:
        print(f"    {m['id']} -> {m['n_mentions']} mentions, sections={m['sections'][:3]}")
    print()
