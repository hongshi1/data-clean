"""T11: image lineage via content hash, dHash, and filename base.

Only sha256-identical images are equivalent; everything else is a
candidate relation that must not be transitively closed.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from PIL import Image

AUGMENTATION_TYPES = ("night", "fog", "strong_light", "flip_rot_color")
_FILENAME_RE = re.compile(
    r"^(?P<base>.+)_(?P<aug>" + "|".join(AUGMENTATION_TYPES) + r")_(?P<idx>\d+)\.jpe?g$",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dhash(image: Image.Image, hash_size: int = 8) -> str:
    """64-bit difference hash; small hamming distance => near-duplicate candidate."""
    gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    bits = []
    for row in range(hash_size):
        for col in range(hash_size):
            left = pixels[row * (hash_size + 1) + col]
            right = pixels[row * (hash_size + 1) + col + 1]
            bits.append("1" if left > right else "0")
    return "".join(bits)


def hamming_distance(hash_a: str, hash_b: str) -> int:
    if len(hash_a) != len(hash_b):
        return len(hash_a)
    return sum(1 for a, b in zip(hash_a, hash_b) if a != b)


def parse_filename(path: Path) -> dict:
    match = _FILENAME_RE.match(path.name)
    if match is None:
        return {"base": path.stem, "augmentation_type": None, "idx": None}
    return {
        "base": match.group("base"),
        "augmentation_type": match.group("aug"),
        "idx": int(match.group("idx")) if match.group("idx") else None,
    }


def compute_lineage(path: Path) -> dict:
    with Image.open(path) as image:
        image_hash = dhash(image)
    parsed = parse_filename(path)
    return {
        "sha256": sha256_file(path),
        "dhash": image_hash,
        "filename_base": parsed["base"],
        "augmentation_type": parsed["augmentation_type"],
        "relation_semantics": {
            "same_asset": "sha256-identical only (equivalent)",
            "same_base": "filename hint; candidate, NOT equivalence",
            "near_duplicate": "dhash hamming<=10; candidate only",
        },
    }
