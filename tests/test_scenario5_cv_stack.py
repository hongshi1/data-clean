from pathlib import Path

import numpy as np
from PIL import Image

from scenario5.cv_stack.lineage import dhash, hamming_distance, parse_filename
from scenario5.cv_stack.pose_proxy import compute_pose_proxy
from scenario5.cv_stack.quality_gate import compute_quality


def _gray_image(width: int, height: int, value: int, noise: int = 0) -> np.ndarray:
    rng = np.random.default_rng(42)
    base = np.full((height, width, 3), value, dtype=np.uint8)
    if noise:
        base = np.clip(base + rng.integers(-noise, noise, base.shape), 0, 255).astype(np.uint8)
    return base


def test_quality_gate_flags_flat_image_as_low_blur() -> None:
    flat = _gray_image(64, 48, 128)
    metrics = compute_quality(flat)
    assert metrics["blur_laplacian_var"] < 50.0
    assert metrics["usable"] is False


def test_quality_gate_accepts_textured_image() -> None:
    textured = _gray_image(64, 48, 128, noise=80)
    metrics = compute_quality(textured)
    assert metrics["blur_laplacian_var"] >= 50.0
    assert metrics["usable"] is True


def _kp(x: float, y: float, conf: float = 0.9) -> list[float]:
    return [x, y, conf]


def test_pose_proxy_standing_person_not_head_down() -> None:
    keypoints = np.zeros((17, 3))
    keypoints[0] = _kp(100, 50)          # nose above shoulders
    keypoints[5] = _kp(85, 110)
    keypoints[6] = _kp(115, 110)
    keypoints[11] = _kp(90, 210)
    keypoints[12] = _kp(110, 210)
    proxy = compute_pose_proxy(keypoints, (50, 20, 150, 260))
    assert proxy["head_down"] is False
    assert proxy["prone_like"] is False
    assert proxy["torso_angle_from_vertical_deg"] is not None
    assert proxy["torso_angle_from_vertical_deg"] < 20


def test_pose_proxy_head_below_shoulder_line_is_head_down() -> None:
    keypoints = np.zeros((17, 3))
    keypoints[0] = _kp(100, 115)         # nose at shoulder level
    keypoints[5] = _kp(85, 110)
    keypoints[6] = _kp(115, 110)
    keypoints[11] = _kp(90, 210)
    keypoints[12] = _kp(110, 210)
    proxy = compute_pose_proxy(keypoints, (50, 20, 150, 260))
    assert proxy["head_down"] is True


def test_pose_proxy_horizontal_torso_is_prone_like() -> None:
    keypoints = np.zeros((17, 3))
    keypoints[0] = _kp(140, 190)
    keypoints[5] = _kp(100, 185)         # shoulders left
    keypoints[6] = _kp(120, 190)
    keypoints[11] = _kp(180, 200)        # hips right: horizontal torso
    keypoints[12] = _kp(200, 195)
    proxy = compute_pose_proxy(keypoints, (80, 150, 240, 240))
    assert proxy["prone_like"] is True
    assert proxy["torso_angle_from_vertical_deg"] > 50


def test_pose_proxy_low_confidence_keypoints_yield_none() -> None:
    keypoints = np.zeros((17, 3))
    proxy = compute_pose_proxy(keypoints, (0, 0, 100, 200))
    assert proxy["head_down"] is None
    assert proxy["prone_like"] is None


def test_parse_filename_extracts_base_and_augmentation(tmp_path: Path) -> None:
    path = tmp_path / "shuigang_0018_fog_01.jpg"
    parsed = parse_filename(path)
    assert parsed["base"] == "shuigang_0018"
    assert parsed["augmentation_type"] == "fog"


def test_dhash_identical_images_have_zero_distance(tmp_path: Path) -> None:
    image = Image.new("RGB", (64, 64), (120, 130, 140))
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    image.save(a)
    image.save(b)
    assert hamming_distance(dhash(Image.open(a)), dhash(Image.open(b))) == 0


def test_dhash_different_images_have_nonzero_distance() -> None:
    gradient_a = Image.new("L", (64, 64))
    gradient_a.putdata([((x * 4) % 256) for _ in range(64) for x in range(64)])
    gradient_b = Image.new("L", (64, 64))
    gradient_b.putdata([(((63 - x) * 4) % 256) for _ in range(64) for x in range(64)])
    assert hamming_distance(dhash(gradient_a), dhash(gradient_b)) > 0
