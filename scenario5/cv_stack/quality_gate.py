"""T0: deterministic image quality gating.

Gates all downstream negative judgments: a blurry or badly-exposed image
cannot support "not observed" claims, only UNKNOWN.
"""
from __future__ import annotations

import cv2
import numpy as np


BLUR_FLOOR = 50.0
OVEREXPOSED_CEILING = 0.30
UNDEREXPOSED_CEILING = 0.30


def compute_quality(image_bgr: np.ndarray) -> dict:
    """Return deterministic quality metrics for one BGR image.

    Thresholds are v1 heuristics pending calibration on annotated data.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur_laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_brightness = float(gray.mean())
    std_brightness = float(gray.std())
    overexposed_ratio = float((gray > 250).mean())
    underexposed_ratio = float((gray < 5).mean())
    usable = (
        blur_laplacian_var >= BLUR_FLOOR
        and overexposed_ratio <= OVEREXPOSED_CEILING
        and underexposed_ratio <= UNDEREXPOSED_CEILING
    )
    return {
        "blur_laplacian_var": round(blur_laplacian_var, 2),
        "mean_brightness": round(mean_brightness, 2),
        "std_brightness": round(std_brightness, 2),
        "overexposed_ratio": round(overexposed_ratio, 4),
        "underexposed_ratio": round(underexposed_ratio, 4),
        "usable": bool(usable),
        "notes": "v1 heuristic thresholds; calibrate on annotated quality labels",
    }
