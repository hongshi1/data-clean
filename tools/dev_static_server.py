"""Static file server with Cache-Control: no-store (dev frontend).

Replaces `python -m http.server` for the 8080 frontend: every fetch is
revalidated so JS/HTML changes are always picked up by a normal F5
(plain http.server + browser heuristic caching repeatedly served stale
index.html -> stale ?v= params -> mixed old/new JS).

Usage: python tools/dev_static_server.py [port] [directory]
"""
from __future__ import annotations

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    directory = sys.argv[2] if len(sys.argv) > 2 else str(
        BASE / "deploy/nkuDataProject/frontend")
    handler = partial(NoCacheHandler, directory=directory)
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"no-cache static server: http://127.0.0.1:{port} "
          f"(dir={directory})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
