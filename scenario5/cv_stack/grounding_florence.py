"""B3 v2: Visual grounding via Florence-2 (span → image bbox).

Upgrades B3 from keyword matching to actual visual grounding:
QA evidence phrases like "人员趴在工位" are located in the image
as bounding boxes, then compared with frozen pose evidence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FLORENCE_DIR = ROOT / "scenario5" / "models" / "florence-2-base-ft"

_MODEL_CACHE: tuple[Any, Any, str, Any] | None = None


def _load_model():
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        import torch
        from transformers import AutoProcessor, Florence2ForConditionalGeneration

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = Florence2ForConditionalGeneration.from_pretrained(
            str(FLORENCE_DIR), dtype=dtype, device_map=device
        )
        processor = AutoProcessor.from_pretrained(str(FLORENCE_DIR))
        _MODEL_CACHE = (model, processor, device, dtype)
    return _MODEL_CACHE


def ground_phrase(image_path: Path, phrase: str) -> dict[str, Any]:
    """Locate a text phrase in an image; returns bboxes in original pixel coords."""
    import torch

    model, processor, device, dtype = _load_model()
    image = Image.open(image_path).convert("RGB")

    task = "<CAPTION_TO_PHRASE_GROUNDING>"
    inputs = processor(text=task + phrase, images=image, return_tensors="pt")
    inputs = {k: v.to(device, dtype if v.is_floating_point() else v.dtype) for k, v in inputs.items()}

    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=1024, num_beams=3)

    text = processor.batch_decode(generated, skip_special_tokens=False)[0]
    result = processor.post_process_generation(
        text, task=task, image_size=(image.width, image.height)
    )
    grounded = result.get("<CAPTION_TO_PHRASE_GROUNDING>", {})
    return {
        "phrase": phrase,
        "bboxes": grounded.get("bboxes", []),
        "labels": grounded.get("labels", []),
        "image_size": (image.width, image.height),
        "model": "florence-2-base-ft",
        "task": "phrase_grounding",
    }
