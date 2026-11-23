"""开放词汇物体检测：用Florence-2检测COCO没有的domain-specific物体.

填补S3(防静电服)、S4(口罩)、S6(香烟)等场景的检测缺口.
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


# 场景5需要的domain-specific检测目标（COCO没有的）
SCENE5_TARGETS = [
    "face mask",
    "cigarette",
    "work clothes",
    "safety vest",
    "fire extinguisher",
    "warning sign",
    "industrial equipment",
    "tool box",
]


def detect_objects(image_path: Path, labels: list[str] | None = None) -> list[dict[str, Any]]:
    """用Florence-2开放词汇检测任意物体.

    Args:
        image_path: 图片路径
        labels: 要检测的物体标签列表（英文效果更好），默认用SCENE5_TARGETS

    Returns:
        [{"label": "face mask", "bbox": [x1,y1,x2,y2], "confidence": "high"}]
    """
    if labels is None:
        labels = SCENE5_TARGETS

    model, processor, device, dtype = _load_model()
    image = Image.open(image_path).convert("RGB")

    task = "<OPEN_VOCABULARY_DETECTION>"
    text_input = task + ", ".join(labels)

    inputs = processor(text=text_input, images=image, return_tensors="pt")
    inputs = {k: v.to(device, dtype if v.is_floating_point() else v.dtype) for k, v in inputs.items()}

    import torch
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=512, num_beams=3)

    response = processor.batch_decode(generated, skip_special_tokens=False)[0]
    result = processor.post_process_generation(
        response, task=task, image_size=(image.width, image.height)
    )

    detections = []
    ov_result = result.get("<OPEN_VOCABULARY_DETECTION>", {})
    bboxes = ov_result.get("bboxes", [])
    detected_labels = ov_result.get("bboxes_labels", ov_result.get("labels", []))

    for bbox, label in zip(bboxes, detected_labels):
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            detections.append({
                "label": str(label),
                "bbox": [round(float(v), 1) for v in bbox],
                "source": "florence2_open_vocab",
            })

    return detections


def extract_text(image_path: Path) -> list[dict[str, Any]]:
    """用Florence-2做OCR，提取图内文字（时间戳、设备号等）."""
    model, processor, device, dtype = _load_model()
    image = Image.open(image_path).convert("RGB")

    task = "<OCR>"
    inputs = processor(text=task, images=image, return_tensors="pt")
    inputs = {k: v.to(device, dtype if v.is_floating_point() else v.dtype) for k, v in inputs.items()}

    import torch
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=512)

    response = processor.batch_decode(generated, skip_special_tokens=False)[0]
    result = processor.post_process_generation(
        response, task=task, image_size=(image.width, image.height)
    )

    # OCR returns text as a single string
    ocr_text = result.get("<OCR>", "")
    if not ocr_text:
        return []

    # Try to get bounding boxes for the text
    task_with_region = "<OCR_WITH_REGION>"
    inputs2 = processor(text=task_with_region, images=image, return_tensors="pt")
    inputs2 = {k: v.to(device, dtype if v.is_floating_point() else v.dtype) for k, v in inputs2.items()}
    with torch.inference_mode():
        generated2 = model.generate(**inputs2, max_new_tokens=512)
    response2 = processor.batch_decode(generated2, skip_special_tokens=False)[0]
    result2 = processor.post_process_generation(
        response2, task=task_with_region, image_size=(image.width, image.height)
    )

    region_result = result2.get("<OCR_WITH_REGION>", {})
    if isinstance(region_result, dict) and "labels" in region_result:
        labels = region_result["labels"]
        bboxes = region_result.get("quad_boxes", region_result.get("bboxes", []))
        texts = []
        for label, bbox in zip(labels, bboxes):
            texts.append({
                "text": str(label),
                "bbox": [round(float(v), 1) for v in bbox[:4]] if len(bbox) >= 4 else None,
                "source": "florence2_ocr",
            })
        return texts

    return [{"text": ocr_text, "bbox": None, "source": "florence2_ocr"}]
