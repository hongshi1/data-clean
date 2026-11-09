"""Run reproducible CV baselines on the downloaded Scenario 5 datasets.

The first benchmark fixes one YOLO detector and compares online trackers on a
contiguous MOT17 segment. Optional pose inference is evaluated against a
matched MeVA/DIVA geometry annotation. UCF-Crime outputs are qualitative only:
its downloaded copy has video-level labels, not person/action frame truth.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

import cv2
import motmetrics as mm
import numpy as np
import torch
from safetensors.torch import load_file
from PIL import Image
from ultralytics import YOLO
import yaml
from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.run_utils import open_run  # noqa: E402

MOT_ZIP = ROOT / "scenario5" / "data" / "mot" / "MOT17.zip"
MEVA_ROOT = ROOT / "scenario5" / "data" / "meva"
UCF_ROOT = ROOT / "scenario5" / "data" / "ucf_crime" / "Anomaly-Videos-Part-1"
DET_WEIGHTS = ROOT / "scenario5" / "models" / "yolo11n.pt"
POSE_WEIGHTS = ROOT / "scenario5" / "models" / "yolo11n-pose.pt"
VIDEOMAE_DIR = ROOT / "scenario5" / "models" / "videomae-base-finetuned-kinetics"
SEQ = "MOT17-04-FRCNN"
GT_IOU_THRESHOLD = 0.5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_mot_gt(text: str, first_frame: int, last_frame: int) -> dict[int, list[tuple[int, float, float, float, float]]]:
    """Return valid person GT as frame -> (id,x,y,w,h), inclusive frame range."""
    rows: dict[int, list[tuple[int, float, float, float, float]]] = defaultdict(list)
    for line in text.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 7:
            continue
        frame = int(float(parts[0]))
        track_id = int(float(parts[1]))
        x, y, w, h = map(float, parts[2:6])
        mark = float(parts[6])
        cls = int(float(parts[7])) if len(parts) > 7 else 1
        if first_frame <= frame <= last_frame and mark == 1 and cls == 1 and w > 0 and h > 0:
            rows[frame].append((track_id, x, y, w, h))
    return dict(rows)


def extract_segment(first_frame: int, count: int, run_dir: Path) -> tuple[list[tuple[int, Path]], dict[int, list[tuple[int, float, float, float, float]]]]:
    if not MOT_ZIP.is_file():
        raise FileNotFoundError(MOT_ZIP)
    seq_root = Path("MOT17") / "train" / SEQ
    rel_dir = seq_root / "img1"
    frame_end = first_frame + count - 1
    cache = ROOT / "scenario5" / "data" / "mot" / "expanded" / SEQ
    cache.mkdir(parents=True, exist_ok=True)
    selected: list[tuple[int, Path]] = []
    with zipfile.ZipFile(MOT_ZIP) as zf:
        gt_name = (seq_root / "gt" / "gt.txt").as_posix()
        gt_text = zf.read(gt_name).decode("utf-8")
        names = [n for n in zf.namelist() if n.startswith(str(rel_dir).replace("\\", "/") + "/") and n.lower().endswith(".jpg")]
        for name in sorted(names):
            frame = int(Path(name).stem)
            if first_frame <= frame <= frame_end:
                out = cache / Path(name).name
                if not out.exists():
                    out.write_bytes(zf.read(name))
                selected.append((frame, out))
    if len(selected) != count:
        raise RuntimeError(f"Expected {count} consecutive frames, extracted {len(selected)}")
    return selected, read_mot_gt(gt_text, first_frame, frame_end)


def xyxy_to_xywh(box: list[float] | tuple[float, ...]) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = map(float, box)
    return x1, y1, x2 - x1, y2 - y1


def iou_distance_matrix(
    gt_boxes: list[tuple[float, float, float, float]],
    pred_boxes: list[tuple[float, float, float, float]],
    iou_threshold: float,
) -> np.ndarray:
    """MOT distance matrix with NumPy 2 compatibility (1-IoU, gated)."""
    distances = np.empty((len(gt_boxes), len(pred_boxes)), dtype=float)
    for i, (gx, gy, gw, gh) in enumerate(gt_boxes):
        for j, (px, py, pw, ph) in enumerate(pred_boxes):
            ix1, iy1 = max(gx, px), max(gy, py)
            ix2, iy2 = min(gx + gw, px + pw), min(gy + gh, py + ph)
            intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            union = gw * gh + pw * ph - intersection
            iou = intersection / union if union > 0 else 0.0
            distances[i, j] = 1.0 - iou if iou >= iou_threshold else np.nan
    return distances


def evaluate_tracker(
    detector: YOLO,
    frames: list[tuple[int, Path]],
    gt: dict[int, list[tuple[int, float, float, float, float]]],
    tracker: str,
    device: str,
    imgsz: int,
    conf: float,
) -> dict[str, Any]:
    accumulator = mm.MOTAccumulator(auto_id=False)
    pred_total = gt_total = 0
    per_frame: list[dict[str, Any]] = []
    start = time.perf_counter()
    for frame_no, image_path in frames:
        results = detector.track(
            source=str(image_path),
            persist=True,
            tracker=tracker,
            device=device,
            imgsz=imgsz,
            conf=conf,
            iou=0.7,
            classes=[0],
            verbose=False,
        )
        boxes = results[0].boxes
        pred_ids: list[int] = []
        pred_xywh: list[tuple[float, float, float, float]] = []
        if boxes is not None and boxes.xyxy is not None and len(boxes):
            coords = boxes.xyxy.detach().cpu().numpy()
            ids = boxes.id.detach().cpu().numpy().astype(int) if boxes.id is not None else np.arange(len(coords))
            pred_ids = ids.tolist()
            pred_xywh = [xyxy_to_xywh(row) for row in coords]
        gt_rows = gt.get(frame_no, [])
        gt_ids = [row[0] for row in gt_rows]
        gt_xywh = [(row[1], row[2], row[3], row[4]) for row in gt_rows]
        distances = iou_distance_matrix(gt_xywh, pred_xywh, GT_IOU_THRESHOLD)
        accumulator.update(gt_ids, pred_ids, distances, frameid=frame_no)
        pred_total += len(pred_ids)
        gt_total += len(gt_ids)
        per_frame.append({"frame": frame_no, "gt": len(gt_ids), "pred": len(pred_ids)})
    elapsed = time.perf_counter() - start
    summary = mm.metrics.create().compute(
        accumulator,
        metrics=["idf1", "idp", "idr", "mota", "num_switches", "num_fragmentations", "mostly_tracked", "mostly_lost", "num_matches", "num_false_positives", "num_misses"],
        name=tracker,
    )
    values = {key: (None if not np.isfinite(float(value)) else float(value)) for key, value in summary.loc[tracker].to_dict().items()}
    values.update({
        "frames": len(frames),
        "gt_detections": gt_total,
        "pred_detections": pred_total,
        "precision_at_iou_0_5": values["num_matches"] / (values["num_matches"] + values["num_false_positives"]) if values["num_matches"] + values["num_false_positives"] else 0.0,
        "recall_at_iou_0_5": values["num_matches"] / (values["num_matches"] + values["num_misses"]) if values["num_matches"] + values["num_misses"] else 0.0,
        "elapsed_seconds": elapsed,
        "fps_including_decode_and_tracker": len(frames) / elapsed if elapsed else None,
        "per_frame": per_frame,
    })
    return values


def parse_meva_geom(path: Path) -> list[tuple[int, int, tuple[int, int, int, int]]]:
    """Parse DIVA geom YAML subset without adding a YAML dependency."""
    import re

    rows: list[tuple[int, int, tuple[int, int, int, int]]] = []
    pattern = re.compile(r"id1:\s*(\d+).*?ts0:\s*(\d+).*?g0:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            tid, frame, x1, y1, x2, y2 = map(int, match.groups())
            rows.append((tid, frame, (x1, y1, x2, y2)))
    return rows


def parse_meva_activities(path: Path) -> list[dict[str, Any]]:
    """Read activity names, spans and actor IDs from DIVA YAML lines."""
    import re

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "{ act:" not in line:
            continue
        names = re.findall(r"([A-Za-z][A-Za-z0-9_]+):\s*1\.0", line)
        span = re.search(r"tsr0:\s*\[(\d+),\s*(\d+)\]", line)
        actor_text = re.search(r"actors:\s*\[(.*?)\]\s*}", line)
        actor_ids = [int(value) for value in re.findall(r"id1:\s*(\d+)", actor_text.group(1))] if actor_text else []
        if names and span:
            rows.append({"activity": names[0], "start_frame": int(span.group(1)), "end_frame": int(span.group(2)), "actor_ids": actor_ids})
    return rows


def box_iou_xyxy(a: tuple[int, int, int, int], b: np.ndarray) -> float:
    x1 = max(a[0], float(b[0]))
    y1 = max(a[1], float(b[1]))
    x2 = min(a[2], float(b[2]))
    y2 = min(a[3], float(b[3]))
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0.0, float(b[2] - b[0])) * max(0.0, float(b[3] - b[1]))
    denom = area_a + area_b - inter
    return inter / denom if denom else 0.0


def run_meva_pose(run_dir: Path, device: str, max_frames: int) -> dict[str, Any]:
    video = MEVA_ROOT / "clips_G329" / "2018-03-07.16-50-00.16-55-00.admin.G329.r13.avi"
    geom = MEVA_ROOT / "examples" / "annotations" / "2018-03-07" / "16" / "2018-03-07.16-50-00.16-55-00.admin.G329.geom.yml"
    activities_path = geom.with_name(geom.name.replace(".geom.yml", ".activities.yml"))
    if not video.is_file() or not geom.is_file():
        raise FileNotFoundError("MeVA G329 video/geom annotation missing")
    tracks = parse_meva_geom(geom)
    activities = parse_meva_activities(activities_path)
    by_frame: dict[int, list[tuple[int, tuple[int, int, int, int]]]] = defaultdict(list)
    for tid, frame, box in tracks:
        by_frame[frame].append((tid, box))
    model = YOLO(str(POSE_WEIGHTS))
    cap = cv2.VideoCapture(str(video))
    diva_frames = sorted(by_frame)
    sample_positions = np.linspace(
        0, len(diva_frames) - 1, num=min(max_frames, len(diva_frames)), dtype=int
    )
    # DIVA ts0 is 1-based, while OpenCV VideoCapture positions are 0-based.
    diva_samples = [diva_frames[index] for index in sample_positions]
    samples = np.asarray([frame - 1 for frame in diva_samples], dtype=int)
    metrics: list[dict[str, Any]] = []
    started = time.perf_counter()
    vis_path = run_dir / "meva_pose_overlay.jpg"
    overlay: np.ndarray | None = None
    for fi in samples:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok:
            continue
        preds = model.predict(frame, device=device, imgsz=640, conf=0.15, verbose=False)[0]
        pboxes = preds.boxes.xyxy.detach().cpu().numpy() if preds.boxes is not None and len(preds.boxes) else np.empty((0, 4))
        keypoints = preds.keypoints.data.detach().cpu().numpy() if preds.keypoints is not None else np.empty((0, 0, 3))
        diva_frame = int(fi) + 1
        gt_rows = by_frame.get(diva_frame, [])
        best: tuple[int, int, float] | None = None
        for tid, gtbox in gt_rows:
            for pi, pbox in enumerate(pboxes):
                overlap = box_iou_xyxy(gtbox, pbox)
                if best is None or overlap > best[2]:
                    best = (tid, pi, overlap)
        if best:
            tid, pi, overlap = best
            kp = keypoints[pi] if pi < len(keypoints) else np.empty((0, 3))
            visible = int((kp[:, 2] > 0.25).sum()) if len(kp) else 0
            metrics.append(
                {
                    "opencv_frame": int(fi),
                    "diva_frame": diva_frame,
                    "gt_track_id": tid,
                    "matched_iou": overlap,
                    "visible_keypoints": visible,
                }
            )
        if overlay is None or int(fi) == samples[-1]:
            overlay = preds.plot()
            for _tid, gtbox in gt_rows:
                cv2.rectangle(overlay, gtbox[:2], gtbox[2:], (255, 180, 0), 2)
    cap.release()
    if overlay is not None:
        cv2.imwrite(str(vis_path), overlay)
    elapsed = time.perf_counter() - started
    matched = [r for r in metrics if r["matched_iou"] >= 0.5]
    return {
        "video": str(video.relative_to(ROOT)),
        "geom_annotation": str(geom.relative_to(ROOT)),
        "activities_annotation": str(activities_path.relative_to(ROOT)),
        "annotated_activities": activities,
        "sampled_frames": len(samples),
        "frames_with_exact_diwa_geom": len(metrics),
        "best_iou_matches_ge_0_5": len(matched),
        "mean_best_iou_on_geom_frames": float(np.mean([r["matched_iou"] for r in metrics])) if metrics else None,
        "mean_visible_keypoints_for_best_box": float(np.mean([r["visible_keypoints"] for r in metrics])) if metrics else None,
        "elapsed_seconds": elapsed,
        "pose_fps_including_seek": len(samples) / elapsed if elapsed else None,
        "opencv_frame_window": [int(samples[0]), int(samples[-1])],
        "diva_frame_window": [int(diva_samples[0]), int(diva_samples[-1])],
        "visualization": str(vis_path.relative_to(ROOT)) if overlay is not None else None,
        "sample_rows": metrics,
        "limitation": "G329 DIVA geometry is a single track/event example, not a person-pose gold set; report as alignment smoke test only.",
    }


def run_ucf_qualitative(run_dir: Path, device: str, max_frames: int) -> dict[str, Any]:
    video = UCF_ROOT / "Abuse" / "Abuse001_x264.mp4"
    if not video.is_file():
        raise FileNotFoundError(video)
    model = YOLO(str(DET_WEIGHTS))
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    samples = np.linspace(0, max(0, total - 1), num=min(max_frames, total), dtype=int)
    counts: list[int] = []
    representative = None
    start = time.perf_counter()
    for fi in samples:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok:
            continue
        result = model.predict(frame, device=device, imgsz=640, conf=0.25, classes=[0], verbose=False)[0]
        counts.append(len(result.boxes) if result.boxes is not None else 0)
        if representative is None:
            representative = result.plot()
    cap.release()
    out_img = run_dir / "ucf_abuse_detection.jpg"
    if representative is not None:
        cv2.imwrite(str(out_img), representative)
    elapsed = time.perf_counter() - start
    return {
        "video": str(video.relative_to(ROOT)),
        "video_level_category": "Abuse",
        "sampled_frames": len(counts),
        "person_detections_mean_per_sampled_frame": float(np.mean(counts)) if counts else None,
        "person_detections_max_per_sampled_frame": max(counts) if counts else None,
        "elapsed_seconds": elapsed,
        "sampled_fps_including_seek": len(counts) / elapsed if elapsed else None,
        "visualization": str(out_img.relative_to(ROOT)) if representative is not None else None,
        "limitation": "UCF-Crime weak video-level category has no per-frame/person GT here; this is qualitative detector inference, not action-recognition accuracy.",
    }


def run_videomae_qualitative(run_dir: Path, device: str, clips: int) -> dict[str, Any]:
    """Run Kinetics-400 action classification without treating labels as GT."""
    video = UCF_ROOT / "Abuse" / "Abuse001_x264.mp4"
    if not video.is_file():
        raise FileNotFoundError(video)
    config = VIDEOMAE_DIR / "config.json"
    weights = VIDEOMAE_DIR / "model.safetensors"
    processor_config = VIDEOMAE_DIR / "preprocessor_config.json"
    if not (config.is_file() and weights.is_file() and processor_config.is_file()):
        raise FileNotFoundError("VideoMAE model/config/preprocessor assets are incomplete")
    processor = VideoMAEImageProcessor.from_pretrained(str(VIDEOMAE_DIR), local_files_only=True)
    from transformers import VideoMAEConfig

    model = VideoMAEForVideoClassification(VideoMAEConfig.from_pretrained(str(VIDEOMAE_DIR), local_files_only=True))
    checkpoint = load_file(str(weights), device="cpu")
    remapped = dict(checkpoint)
    for key, value in checkpoint.items():
        match = re.fullmatch(r"(videomae\.encoder\.layer\.\d+\.attention\.attention)\.(q|v)_bias", key)
        if match:
            part, branch = match.groups()
            target = f"{part}.{'query' if branch == 'q' else 'value'}.bias"
            remapped[target] = value
            remapped.pop(key, None)
    # The original VideoMAE checkpoint stores separate q/v biases and
    # omits the key bias; the reference implementation defines key bias as 0.
    for key, value in model.state_dict().items():
        if key.endswith("attention.attention.key.bias") and key not in remapped:
            remapped[key] = torch.zeros_like(value)
    incompatible = model.load_state_dict(remapped, strict=False)
    unexpected = list(incompatible.unexpected_keys)
    missing = list(incompatible.missing_keys)
    if unexpected or missing:
        raise RuntimeError(f"VideoMAE checkpoint mismatch: missing={missing[:8]} unexpected={unexpected[:8]}")
    torch_device = "cuda:0" if device == "0" else device
    model.to(device=torch_device, dtype=torch.float16 if str(torch_device).startswith("cuda") else torch.float32).eval()
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    length = int(model.config.num_frames)
    starts = np.linspace(0, max(0, total - length), num=max(1, clips), dtype=int)
    predictions: list[dict[str, Any]] = []
    started = time.perf_counter()
    for start_frame in starts:
        frames: list[Image.Image] = []
        for frame_no in range(int(start_frame), int(start_frame) + length):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb))
        if len(frames) != length:
            continue
        inputs = processor(list(frames), return_tensors="pt")
        inputs = {
            name: value.to(device=torch_device, dtype=model.dtype if value.is_floating_point() else value.dtype)
            for name, value in inputs.items()
        }
        with torch.inference_mode():
            logits = model(**inputs).logits[0]
        probs = logits.softmax(-1)
        top = torch.topk(probs, k=5)
        predictions.append({
            "start_frame": int(start_frame),
            "end_frame": int(start_frame) + length - 1,
            "top5": [
                {"label": model.config.id2label[int(idx)], "probability": float(prob)}
                for idx, prob in zip(top.indices.cpu(), top.values.cpu())
            ],
        })
    cap.release()
    elapsed = time.perf_counter() - started
    return {
        "video": str(video.relative_to(ROOT)),
        "video_level_category": "Abuse",
        "model": "MCG-NJU/videomae-base-finetuned-kinetics (Kinetics-400)",
        "sampled_clips": len(predictions),
        "clip_frame_count": length,
        "elapsed_seconds": elapsed,
        "clips_per_second": len(predictions) / elapsed if elapsed else None,
        "predictions": predictions,
        "limitation": "Qualitative transfer probe only: Kinetics-400 top-k labels do not provide UCF-Crime frame-level ground truth or establish Abuse recognition accuracy.",
    }


def create_tracker_configs(run_dir: Path) -> dict[str, Path]:
    """Resolve installed configs and disable camera-motion/ReID for static CCTVs."""
    import ultralytics

    tracker_root = Path(ultralytics.__file__).parent / "cfg" / "trackers"
    run_configs = run_dir / "tracker_configs"
    run_configs.mkdir()
    configs: dict[str, Path] = {}
    for name, source_name in (
        ("ByteTrack", "bytetrack.yaml"),
        ("BoT-SORT-static", "botsort.yaml"),
        ("OC-SORT", "ocsort.yaml"),
    ):
        source = tracker_root / source_name
        values = yaml.safe_load(source.read_text(encoding="utf-8"))
        if source_name == "botsort.yaml":
            values["gmc_method"] = "none"
            values["with_reid"] = False
        target = run_configs / source_name
        target.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")
        configs[name] = target
    return configs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=240, help="consecutive MOT frames (default 240)")
    parser.add_argument("--first-frame", type=int, default=1)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.10)
    parser.add_argument("--detector-weights", default=str(DET_WEIGHTS))
    parser.add_argument(
        "--trackers",
        nargs="+",
        choices=["ByteTrack", "BoT-SORT-static", "OC-SORT"],
        default=["ByteTrack", "BoT-SORT-static", "OC-SORT"],
    )
    parser.add_argument("--device", default="0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--skip-pose", action="store_true")
    parser.add_argument("--skip-ucf", action="store_true")
    parser.add_argument("--skip-videomae", action="store_true")
    parser.add_argument("--videomae-only", action="store_true", help="run only the UCF-Crime VideoMAE qualitative probe")
    parser.add_argument("--pose-frames", type=int, default=24)
    parser.add_argument("--ucf-frames", type=int, default=24)
    args = parser.parse_args()

    if args.videomae_only:
        run = open_run(
            "scenario5_ucf_videomae_probe",
            {
                "dataset": "UCF-Crime Abuse001",
                "model": "VideoMAE Kinetics-400",
                "model_sha256": sha256(VIDEOMAE_DIR / "model.safetensors"),
                "clips": 4,
                "frames_per_clip": 16,
                "device": args.device,
                "experiment_script_sha256": sha256(Path(__file__).resolve()),
            },
            ROOT / "scenario5" / "runs",
        )
        run_dir = run.path
        qualitative = run_videomae_qualitative(run_dir, args.device, clips=4)
        result = {
            "schema_version": "scenario5_ucf_videomae_probe_v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "environment": {"python": platform.python_version(), "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None},
            "result": qualitative,
        }
        run.save_result(result)
        print(f"run: {run_dir.relative_to(ROOT)}")
        for prediction in qualitative["predictions"]:
            print(f"frames {prediction['start_frame']}-{prediction['end_frame']}: {prediction['top5']}")
        return 0

    detector_weights = Path(args.detector_weights)
    if not detector_weights.is_absolute():
        detector_weights = ROOT / detector_weights
    required = [MOT_ZIP, detector_weights]
    if not args.skip_pose:
        required += [POSE_WEIGHTS]
    if not args.skip_videomae:
        required += [VIDEOMAE_DIR / "config.json", VIDEOMAE_DIR / "model.safetensors", VIDEOMAE_DIR / "preprocessor_config.json"]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing experiment assets: " + ", ".join(missing))

    config = {
        "dataset": "MOT17 train / MOT17-04-FRCNN",
        "first_frame": args.first_frame,
        "frame_count": args.frames,
        "detector_weights": str(detector_weights),
        "detector_sha256": sha256(detector_weights),
        "experiment_script_sha256": sha256(Path(__file__).resolve()),
        "tracker_names": args.trackers,
        "imgsz": args.imgsz,
        "confidence": args.conf,
        "gt_iou_threshold": GT_IOU_THRESHOLD,
        "device": args.device,
        "meva_pose_frames": None if args.skip_pose else args.pose_frames,
        "ucf_detector_frames": None if args.skip_ucf else args.ucf_frames,
        "videomae_clips": None if args.skip_videomae else 4,
        "pose_weights_sha256": sha256(POSE_WEIGHTS) if POSE_WEIGHTS.exists() else None,
        "videomae_weights_sha256": sha256(VIDEOMAE_DIR / "model.safetensors") if (VIDEOMAE_DIR / "model.safetensors").exists() else None,
    }
    run = open_run("scenario5_cv_benchmark", config, ROOT / "scenario5" / "runs")
    run_dir = run.path
    frames, gt = extract_segment(args.first_frame, args.frames, run_dir)
    tracker_configs = {name: path for name, path in create_tracker_configs(run_dir).items() if name in args.trackers}
    tracker_results: dict[str, Any] = {}
    for tracker_name, tracker_config in tracker_configs.items():
        # Each method gets a fresh predictor and tracker state.
        detector = YOLO(str(detector_weights))
        tracker_results[tracker_name] = evaluate_tracker(
            detector,
            frames,
            gt,
            str(tracker_config),
            args.device,
            args.imgsz,
            args.conf,
        )

    pose_result = None if args.skip_pose else run_meva_pose(run_dir, args.device, args.pose_frames)
    ucf_result = None if args.skip_ucf else run_ucf_qualitative(run_dir, args.device, args.ucf_frames)
    videomae_result = None if args.skip_videomae else run_videomae_qualitative(run_dir, args.device, clips=4)
    try:
        import ultralytics
        ultralytics_version = ultralytics.__version__
    except ImportError:
        ultralytics_version = "unavailable"
    result = {
        "schema_version": "scenario5_cv_benchmark_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "mot_dataset": "MOT17 train / MOT17-04-FRCNN",
            "first_frame": args.first_frame,
            "last_frame": frames[-1][0],
            "consecutive_frames": len(frames),
            "detector_weights": str(detector_weights.relative_to(ROOT)) if detector_weights.is_relative_to(ROOT) else str(detector_weights),
            "detector_sha256": sha256(detector_weights),
            "detector_classes": ["person (COCO class 0)"],
            "imgsz": args.imgsz,
            "confidence": args.conf,
            "iou_threshold_for_gt_match": GT_IOU_THRESHOLD,
            "tracker_configs": {
                name: str(path.relative_to(ROOT)) for name, path in tracker_configs.items()
            },
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "ultralytics": ultralytics_version,
            "motmetrics": mm.__version__,
        },
        "mot17_trackers": tracker_results,
        "meva_pose_alignment_smoke_test": pose_result,
        "ucf_crime_qualitative_detector": ucf_result,
        "ucf_crime_videomae_qualitative": videomae_result,
        "interpretation": "This small contiguous MOT17 segment is a pipeline smoke benchmark, not a leaderboard result. Detector and tracker errors are coupled; all three tracker runs share the same detector checkpoint/config. MeVA pose result is an annotation-alignment diagnostic, not pose accuracy. UCF-Crime is qualitative due to weak labels.",
    }
    run.save_result(result)
    run.write_text(
        "runtime_config.json",
        json.dumps(
            {
                **vars(args),
                "detector_weights_sha256": sha256(detector_weights),
                "pose_weights_sha256": sha256(POSE_WEIGHTS) if POSE_WEIGHTS.exists() else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    with (run_dir / "mot17_per_frame.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["tracker", "frame", "gt", "pred", "candidate_pairs_iou_valid"])
        writer.writeheader()
        for tracker, metrics in tracker_results.items():
            for row in metrics["per_frame"]:
                writer.writerow({"tracker": tracker, **row})
    print(f"run: {run_dir.relative_to(ROOT)}")
    for name, row in tracker_results.items():
        print(f"{name}: IDF1={row['idf1']:.4f} MOTA={row['mota']:.4f} IDSW={row['num_switches']} FPS={row['fps_including_decode_and_tracker']:.2f}")
    print(f"result: {(run_dir / 'result.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
