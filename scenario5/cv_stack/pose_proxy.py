"""T5: static pose proxies from COCO 17 keypoints.

Computes head-down and prone-like geometric proxies. These are STATIC
cues only: prone != sleeping; no temporal claim is made.
"""
from __future__ import annotations

import math

import numpy as np

# COCO 17-keypoint indices
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
LEFT_HIP, RIGHT_HIP = 11, 12

KP_CONF_FLOOR = 0.30
HEAD_DOWN_MARGIN = 0.02  # normalized by person bbox height
PRONE_TORSO_ANGLE_DEG = 50.0


def _visible(keypoints: np.ndarray, idx: int) -> bool:
    return len(keypoints) > idx and float(keypoints[idx][2]) >= KP_CONF_FLOOR


def _midpoint(keypoints: np.ndarray, i: int, j: int) -> tuple[float, float] | None:
    if not (_visible(keypoints, i) and _visible(keypoints, j)):
        return None
    return (
        float((keypoints[i][0] + keypoints[j][0]) / 2),
        float((keypoints[i][1] + keypoints[j][1]) / 2),
    )


def compute_pose_proxy(keypoints: np.ndarray, bbox: tuple[float, float, float, float]) -> dict:
    """Derive static geometric pose proxies for one person.

    keypoints: (17, 3) array (x, y, conf) from a pose model.
    bbox: (x1, y1, x2, y2) of the person detection.
    """
    x1, y1, x2, y2 = (float(v) for v in bbox)
    height = max(y2 - y1, 1.0)
    result = {
        "head_down": None,
        "prone_like": None,
        "torso_angle_from_vertical_deg": None,
        "nose_above_shoulders_ratio": None,
        "keypoints_visible": {
            "nose": _visible(keypoints, NOSE),
            "shoulders": _visible(keypoints, LEFT_SHOULDER)
            and _visible(keypoints, RIGHT_SHOULDER),
            "hips": _visible(keypoints, LEFT_HIP) and _visible(keypoints, RIGHT_HIP),
        },
        "static_only": True,
        "note": "prone/head-down are static cues; cannot prove sleeping duration",
    }

    shoulder_mid = _midpoint(keypoints, LEFT_SHOULDER, RIGHT_SHOULDER)
    hip_mid = _midpoint(keypoints, LEFT_HIP, RIGHT_HIP)

    # Head-down: nose approaches or drops below the shoulder line.
    if _visible(keypoints, NOSE) and shoulder_mid is not None:
        nose_y = float(keypoints[NOSE][1])
        above = (shoulder_mid[1] - nose_y) / height
        result["nose_above_shoulders_ratio"] = round(above, 4)
        result["head_down"] = bool(above < HEAD_DOWN_MARGIN)

    # Prone-like: torso (shoulder->hip) vector is closer to horizontal.
    if shoulder_mid is not None and hip_mid is not None:
        dx = hip_mid[0] - shoulder_mid[0]
        dy = hip_mid[1] - shoulder_mid[1]
        torso_len = math.hypot(dx, dy)
        if torso_len > height * 0.15:
            angle = math.degrees(math.atan2(abs(dx), max(abs(dy), 1e-6)))
            result["torso_angle_from_vertical_deg"] = round(angle, 1)
            result["prone_like"] = bool(angle > PRONE_TORSO_ANGLE_DEG)

    return result
