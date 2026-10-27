"""Scan new/untracked files for hardcoded API keys before committing."""
from __future__ import annotations

import re
import subprocess
import sys

PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"(?i)api[_-]?key\s*[=:]\s*['\"][A-Za-z0-9]{16,}['\"]"),
    re.compile(r"(?i)secret\s*[=:]\s*['\"][A-Za-z0-9]{16,}['\"]"),
    re.compile(r"(?i)token\s*[=:]\s*['\"][A-Za-z0-9]{24,}['\"]"),
]


def main() -> None:
    status = subprocess.run(
        ["git", "status", "--short"], capture_output=True, text=True,
        encoding="utf-8").stdout
    files = []
    for line in status.splitlines():
        if line.startswith("??"):
            path = line[3:].strip().strip('"')
            if path.endswith((".py", ".json", ".md", ".tsv", ".toml")):
                files.append(path)
    print(f"scanning {len(files)} files")
    hits: list[str] = []
    for path in files:
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                # allow the placeholder patterns in .env.example style
                if "example" in path.lower() or "<" in match.group(0):
                    continue
                hits.append(f"{path}: {match.group(0)[:40]}")
    if hits:
        print("SECRETS FOUND:")
        for hit in hits:
            print(" ", hit)
        sys.exit(1)
    print("no secrets found")


if __name__ == "__main__":
    main()
