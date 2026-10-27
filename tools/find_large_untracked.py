"""List untracked files larger than 5MB (too big for git)."""
from __future__ import annotations

import os
import subprocess

LIMIT_MB = 5


def main() -> None:
    status = subprocess.run(
        ["git", "status", "--short"], capture_output=True, text=True,
        encoding="utf-8").stdout
    paths = [line[3:].strip().strip('"') for line in status.splitlines()
             if line.startswith("??")]
    big: list[tuple[float, str]] = []
    for path in paths:
        if os.path.isfile(path):
            size = os.path.getsize(path) / (1024 * 1024)
            if size > LIMIT_MB:
                big.append((size, path))
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for name in files:
                    full = os.path.join(root, name)
                    try:
                        size = os.path.getsize(full) / (1024 * 1024)
                    except OSError:
                        continue
                    if size > LIMIT_MB:
                        big.append((size, full))
    big.sort(reverse=True)
    for size, path in big[:40]:
        print(f"{size:8.1f} MB  {path}")
    print(f"total: {len(big)} files > {LIMIT_MB} MB")


if __name__ == "__main__":
    main()
