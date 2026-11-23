"""T11 v2: Near-duplicate detection via SSCD (copy detection embeddings).

Upgrades lineage from dHash (64-bit) to SSCD 512-dim embeddings.
SSCD cos>0.75 → 90% precision for copy detection (DISC21 benchmark).
"""
from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[2]
SSCD_PATH = ROOT / "scenario5" / "models" / "sscd_disc_mixup.torchscript.pt"

_PREPROCESS = transforms.Compose([
    transforms.Resize((320, 320)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

_MODEL_CACHE: torch.jit.ScriptModule | None = None


def _load_model() -> torch.jit.ScriptModule:
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = torch.jit.load(str(SSCD_PATH)).eval()
    return _MODEL_CACHE


def embed_image(image_path: Path) -> torch.Tensor:
    """Extract L2-normalized 512-dim embedding. Cosine similarity = dot product."""
    model = _load_model()
    image = Image.open(image_path).convert("RGB")
    tensor = _PREPROCESS(image).unsqueeze(0)
    device = next(model.parameters()).device
    tensor = tensor.to(device)
    with torch.inference_mode():
        embedding = model(tensor)[0]
    return embedding.cpu()


def cosine_similarity(emb_a: torch.Tensor, emb_b: torch.Tensor) -> float:
    return float(emb_a @ emb_b)


def find_near_duplicates(
    image_paths: list[Path],
    threshold: float = 0.75,
) -> list[dict]:
    """Find near-duplicate pairs above the similarity threshold."""
    embeddings = [embed_image(path) for path in image_paths]
    results: list[dict] = []
    for i in range(len(image_paths)):
        for j in range(i + 1, len(image_paths)):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            if sim >= threshold:
                results.append({
                    "image_a": image_paths[i].name,
                    "image_b": image_paths[j].name,
                    "cosine_similarity": round(sim, 4),
                    "relation": "near_duplicate",
                    "threshold": threshold,
                })
    return sorted(results, key=lambda x: -x["cosine_similarity"])
