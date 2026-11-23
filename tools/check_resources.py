"""Check all resources load correctly."""
import urllib.request

for f in ("js/consist/ner_panel.js", "js/consist/srs.js",
          "js/consist/scenes.js"):
    try:
        r = urllib.request.urlopen(
            "http://127.0.0.1:8080/" + f, timeout=5)
        print(f, r.status, r.headers.get("Content-Length", "?"))
    except Exception as e:
        print(f, "FAIL", str(e)[:50])

try:
    body = b'{"text": "test"}'
    req = urllib.request.Request(
        "http://127.0.0.1:8300/api/ner", data=body,
        headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=5)
    print("/api/ner:", r.status)
except Exception as e:
    print("/api/ner: FAIL", str(e)[:50])
