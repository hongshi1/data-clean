"""Freeze static-image evidence for scenario5 consistency checking.

Runs the Phase-A CV stack once per image (quality gate, person/object
detection, pose proxies, lineage) and freezes structured evidence
records. All downstream QA checks consume the frozen files, isolating
model non-determinism. See temp/20261116_scenario5_static_image_context_plan.md.

Usage:
  python scenario5/tools/build_image_evidence.py --images <dir> [--limit N]
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

from scenario5.cv_stack.lineage import compute_lineage, hamming_distance  # noqa: E402
from scenario5.cv_stack.pose_proxy import compute_pose_proxy  # noqa: E402
from scenario5.cv_stack.quality_gate import compute_quality  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

DET_WEIGHTS = ROOT / "scenario5" / "models" / "yolo11s.pt"
POSE_WEIGHTS = ROOT / "scenario5" / "models" / "yolo11n-pose.pt"
PERSON_CLASS = 0
IOU_MATCH_THRESHOLD = 0.5
DHASH_NEAR_DUPLICATE = 10


def box_iou_xyxy(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def sha256_short(path: Path) -> str:
    from scenario5.cv_stack.lineage import sha256_file

    return sha256_file(path)[:16]


def run_detector(model: YOLO, frame: np.ndarray, classes: list[int] | None, conf: float) -> list[dict]:
    result = model.predict(frame, imgsz=640, conf=conf, classes=classes, verbose=False)[0]
    boxes = result.boxes
    if boxes is None or not len(boxes):
        return []
    coords = boxes.xyxy.detach().cpu().numpy()
    confs = boxes.conf.detach().cpu().numpy()
    clss = boxes.cls.detach().cpu().numpy().astype(int)
    names = result.names
    return [
        {"bbox": [round(float(v), 1) for v in row], "det_conf": round(float(c), 3), "class_id": int(k), "class_name": names[k]}
        for row, c, k in zip(coords, confs, clss)
    ]


def run_pose(model: YOLO, frame: np.ndarray, conf: float) -> list[dict]:
    result = model.predict(frame, imgsz=640, conf=conf, classes=[PERSON_CLASS], verbose=False)[0]
    boxes = result.boxes
    kps = result.keypoints
    if boxes is None or not len(boxes):
        return []
    coords = boxes.xyxy.detach().cpu().numpy()
    confs = boxes.conf.detach().cpu().numpy()
    keypoints = kps.data.detach().cpu().numpy() if kps is not None else np.empty((0, 0, 3))
    persons = []
    for i, (row, c) in enumerate(zip(coords, confs)):
        person = {
            "person_id": f"p{i + 1}",
            "bbox": [round(float(v), 1) for v in row],
            "det_conf": round(float(c), 3),
            "pose_proxy": None,
        }
        if i < len(keypoints):
            person["pose_proxy"] = compute_pose_proxy(keypoints[i], tuple(row))
        persons.append(person)
    return persons


def process_image(detector: YOLO, pose_model: YOLO, image_path: Path, det_conf: float, pose_conf: float) -> dict:
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise RuntimeError(f"cannot decode {image_path}")
    quality = compute_quality(frame)
    objects = run_detector(detector, frame, classes=None, conf=det_conf)
    non_person_objects = [o for o in objects if o["class_id"] != PERSON_CLASS]
    persons = run_pose(pose_model, frame, conf=pose_conf)
    det_persons = [o for o in objects if o["class_id"] == PERSON_CLASS]
    for person in persons:
        best = 0.0
        for det in det_persons:
            best = max(best, box_iou_xyxy(person["bbox"], det["bbox"]))
        person["det_model_agreement_iou"] = round(best, 3)
    lineage = compute_lineage(image_path)
    return {
        "schema_version": "scenario5_image_evidence_v1",
        "image_id": f"img:{lineage['sha256'][:16]}",
        "source_path": str(image_path),
        "width": frame.shape[1],
        "height": frame.shape[0],
        "quality": quality,
        "persons": persons,
        "objects": non_person_objects,
        "counts": {
            "person_count": len(persons),
            "object_count": len(non_person_objects),
            "det_person_count_cross_check": len(det_persons),
        },
        "lineage": lineage,
    }


def cross_image_lineage(records: list[dict]) -> list[dict]:
    edges: list[dict] = []
    for i, a in enumerate(records):
        for b in records[i + 1 :]:
            dist = hamming_distance(a["lineage"]["dhash"], b["lineage"]["dhash"])
            same_base = a["lineage"]["filename_base"] == b["lineage"]["filename_base"]
            if dist <= DHASH_NEAR_DUPLICATE or same_base:
                edges.append(
                    {
                        "a": a["image_id"],
                        "b": b["image_id"],
                        "dhash_distance": dist,
                        "same_filename_base": same_base,
                        "relation": "same_asset" if dist == 0 and a["lineage"]["sha256"] == b["lineage"]["sha256"] else "candidate",
                    }
                )
    return edges


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, help="directory of jpg images")
    parser.add_argument("--limit", type=int, default=0, help="process at most N images (0=all)")
    parser.add_argument("--det-conf", type=float, default=0.25)
    parser.add_argument("--pose-conf", type=float, default=0.15)
    parser.add_argument("--device", default="0" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    image_dir = Path(args.images)
    if not image_dir.is_dir():
        raise FileNotFoundError(image_dir)
    images = sorted(image_dir.glob("*.jpg"))
    if args.limit:
        images = images[: args.limit]
    if not images:
        raise RuntimeError(f"no .jpg files in {image_dir}")
    for weights in (DET_WEIGHTS, POSE_WEIGHTS):
        if not weights.is_file():
            raise FileNotFoundError(weights)

    from scenario5.cv_stack.lineage import sha256_file

    run = open_run(
        "scenario5_image_evidence",
        {
            "image_dir": str(image_dir),
            "n_images": len(images),
            "detector_weights": str(DET_WEIGHTS),
            "detector_sha256": sha256_file(DET_WEIGHTS),
            "pose_weights": str(POSE_WEIGHTS),
            "pose_sha256": sha256_file(POSE_WEIGHTS),
            "det_conf": args.det_conf,
            "pose_conf": args.pose_conf,
            "device": args.device,
        },
        ROOT / "scenario5" / "runs",
    )
    evidence_dir = run.path / "evidence"
    evidence_dir.mkdir()
    detector = YOLO(str(DET_WEIGHTS))
    pose_model = YOLO(str(POSE_WEIGHTS))

    records: list[dict] = []
    started = time.perf_counter()
    for image_path in images:
        record = process_image(detector, pose_model, image_path, args.det_conf, args.pose_conf)
        records.append(record)
        out = evidence_dir / f"{image_path.stem}.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        n_persons = record["counts"]["person_count"]
        head_down = sum(1 for p in record["persons"] if p["pose_proxy"] and p["pose_proxy"]["head_down"])
        prone = sum(1 for p in record["persons"] if p["pose_proxy"] and p["pose_proxy"]["prone_like"])
        print(f"{image_path.name}: persons={n_persons} head_down={head_down} prone_like={prone} usable={record['quality']['usable']}")
    elapsed = time.perf_counter() - started

    summary = {
        "schema_version": "scenario5_image_evidence_summary_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "n_images": len(records),
        "elapsed_seconds": round(elapsed, 2),
        "fps_pipeline": round(len(records) / elapsed, 2) if elapsed else None,
        "person_count_distribution": {},
        "head_down_persons_total": 0,
        "prone_like_persons_total": 0,
        "usable_images": 0,
        "augmentation_distribution": {},
        "cross_image_candidate_edges": cross_image_lineage(records),
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "interpretation": "Frozen Phase-A evidence. head_down/prone_like are STATIC cues; sleeping requires temporal evidence and must yield NIE.",
    }
    for record in records:
        n = record["counts"]["person_count"]
        summary["person_count_distribution"][str(n)] = summary["person_count_distribution"].get(str(n), 0) + 1
        summary["head_down_persons_total"] += sum(1 for p in record["persons"] if p["pose_proxy"] and p["pose_proxy"]["head_down"])
        summary["prone_like_persons_total"] += sum(1 for p in record["persons"] if p["pose_proxy"] and p["pose_proxy"]["prone_like"])
        summary["usable_images"] += int(record["quality"]["usable"])
        aug = record["lineage"]["augmentation_type"] or "unknown"
        summary["augmentation_distribution"][aug] = summary["augmentation_distribution"].get(aug, 0) + 1

    run.save_result(summary)
    print(f"\nrun: {run.path.relative_to(ROOT)}")
    print(f"evidence files: {len(records)} -> {evidence_dir.relative_to(ROOT)}")
    print(f"summary: persons/head_down/prone = {summary['head_down_persons_total']}/{summary['head_down_persons_total']}/{summary['prone_like_persons_total']}, usable={summary['usable_images']}/{len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
