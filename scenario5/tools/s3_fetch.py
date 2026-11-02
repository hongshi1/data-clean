r"""Scenario5 MEVA S3 asset fetcher.

Anonymous S3 access with Windows registry proxy inheritance (curl/python do not
read the IE/system proxy). Idempotent downloads with resume.

Usage:
  python scenario5/tools/s3_fetch.py --list "examples/"
  python scenario5/tools/s3_fetch.py --sync "examples/" --dest "scenario5/data/meva/examples"
  python scenario5/tools/s3_fetch.py --get "mevid-annotations/mevid-v1-annotation-data.zip" \
      --dest "scenario5/data/meva/mevid-annotations"
"""
from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

BUCKET_URL = "https://mevadata-public-01.s3.amazonaws.com"
S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def inherit_windows_proxy() -> str | None:
    r"""Python/requests ignores the registry proxy: inject env vars when enabled."""
    if os.environ.get("HTTPS_PROXY"):
        return os.environ["HTTPS_PROXY"]
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
        server, _ = winreg.QueryValueEx(key, "ProxyServer")
        winreg.CloseKey(key)
    except OSError:
        return None
    if enable and server:
        os.environ["HTTPS_PROXY"] = f"http://{server}"
        os.environ["HTTP_PROXY"] = f"http://{server}"
        return f"http://{server}"
    return None


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "scenario5-fetch/1.0"
    return session


def list_keys(prefix: str, session: requests.Session) -> list[tuple[str, int]]:
    """List all object keys under prefix (paginated ListObjectsV2)."""
    keys: list[tuple[str, int]] = []
    token: str | None = None
    while True:
        params: dict[str, str] = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        resp = session.get(BUCKET_URL + "/", params=params, timeout=90)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        for contents in root.findall(f"{S3_NS}Contents"):
            key_el = contents.find(f"{S3_NS}Key")
            size_el = contents.find(f"{S3_NS}Size")
            if key_el is not None and key_el.text:
                keys.append((key_el.text, int(size_el.text or 0)))
        truncated = root.find(f"{S3_NS}IsTruncated")
        next_token = root.find(f"{S3_NS}NextContinuationToken")
        if truncated is not None and truncated.text == "true" and next_token is not None:
            token = next_token.text
        else:
            return keys


def fetch_object(
    key: str,
    dest_root: Path,
    session: requests.Session,
    size: int | None = None,
    flat: bool = False,
) -> tuple[str, str]:
    """Download one object with resume; returns (status, message).

    flat=False preserves the S3 key's directory structure under dest_root;
    flat=True saves only the basename (legacy single-file --get).
    """
    rel = Path(key)
    dest = dest_root / (rel.name if flat else rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BUCKET_URL}/{key}"
    head = session.head(url, timeout=90)
    head.raise_for_status()
    total = int(head.headers.get("Content-Length", "0"))
    offset = dest.stat().st_size if dest.exists() else 0
    if size is not None and total and total != size and offset == 0:
        return ("SKIP", f"metadata size mismatch ({total} != {size})")
    if offset >= total and total > 0:
        return ("SKIP", f"complete ({offset} bytes)")
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with session.get(url, headers=headers, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        if resp.status_code not in (200, 206):
            return ("FAIL", f"HTTP {resp.status_code}")
        mode = "ab" if offset else "wb"
        with dest.open(mode) as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if chunk:
                    fh.write(chunk)
    return ("OK", f"{dest.name}: {dest.stat().st_size}/{total} bytes")


def human(n: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    v = float(n)
    for u in units:
        if v < 1024 or u == units[-1]:
            return f"{v:.1f}{u}"
        v /= 1024
    return f"{n}B"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", metavar="PREFIX", help="list keys under prefix")
    group.add_argument("--sync", metavar="PREFIX", help="download all keys under prefix")
    group.add_argument("--get", metavar="KEY", help="download a single key")
    parser.add_argument("--dest", default="scenario5/data/meva", help="destination directory")
    args = parser.parse_args(argv)

    proxy = inherit_windows_proxy()
    print(f"[proxy] {proxy or 'direct'}")
    session = make_session()

    if args.list:
        keys = list_keys(args.list, session)
        total = sum(sz for _, sz in keys)
        print(f"[list] {len(keys)} objects, {human(total)} under '{args.list}'")
        for key, sz in keys:
            print(f"  {human(sz):>10}  {key}")
        return 0

    if args.get:
        status, msg = fetch_object(args.get, Path(args.dest), session, flat=True)
        print(f"[get] {status}: {msg}")
        return 0 if status in ("OK", "SKIP") else 1

    keys = list_keys(args.sync, session)
    total = sum(sz for _, sz in keys)
    print(f"[sync] {len(keys)} objects, {human(total)} under '{args.sync}' -> {args.dest}")
    failures = 0
    for i, (key, sz) in enumerate(keys, 1):
        status, msg = fetch_object(key, Path(args.dest), session, size=sz)
        print(f"  [{i}/{len(keys)}] {status}: {msg}")
        if status == "FAIL":
            failures += 1
    print(f"[done] ok={len(keys) - failures} fail={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
