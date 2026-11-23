"""安全帽佩戴场景：特征提取→上下文关联→一致性校验完整管线.

按照四层架构实现：
  Layer 1: 视觉Chunk提取（多粒度分块+特征编码）
  Layer 2: 图内关系建模（六类关系图）
  Layer 3: QA文本语义解析（实体/属性/关系/否定）
  Layer 4: 跨模态关联（语义命题→视觉Chunk映射）
  Layer 5: 一致性校验（三方比对→四态判定）
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

# Model paths
DET_WEIGHTS = ROOT / "scenario5" / "models" / "yolo11s.pt"       # person detection
PPE_WEIGHTS = ROOT / "scenario5" / "models" / "best.pt"          # hardhat detection
POSE_WEIGHTS = ROOT / "scenario5" / "models" / "yolo11n-pose.pt" # pose estimation

# COCO class 0 = person
PERSON_CLASS = 0
# PPE model classes
PPE_CLASS_HARDHAT = 0    # person wearing hardhat
PPE_CLASS_NO_HARDHAT = 1 # person without hardhat

# Detection thresholds
DET_CONF = 0.25
PPE_CONF = 0.30
POSE_CONF = 0.15
IOU_MATCH_THRESHOLD = 0.3  # person bbox vs PPE bbox matching
NEAR_DISTANCE_PX = 150     # pixels for "near" spatial relation


# ============ Layer 1: Visual Chunk Extraction ============

def extract_chunks(image_bgr: np.ndarray, image_path: Path | None = None) -> dict[str, Any]:
    """Extract multi-granularity visual chunks from one image.

    Returns:
        {
            "quality": {...},
            "chunks": {
                "scene": {...},       # global scene
                "entities": [...],     # persons, PPE items
                "parts": [...],        # head regions
                "text": [...],         # OCR results (empty for now)
            },
            "timings": {...},
        }
    """
    from scenario5.cv_stack.quality_gate import compute_quality
    from ultralytics import YOLO

    timings: dict[str, float] = {}
    quality = compute_quality(image_bgr)

    # --- Person detection ---
    t0 = time.perf_counter()
    det_model = YOLO(str(DET_WEIGHTS))
    det_result = det_model.predict(image_bgr, imgsz=640, conf=DET_CONF, verbose=False)[0]
    timings["person_detection"] = time.perf_counter() - t0

    persons = []
    if det_result.boxes is not None and len(det_result.boxes):
        coords = det_result.boxes.xyxy.detach().cpu().numpy()
        confs = det_result.boxes.conf.detach().cpu().numpy()
        clss = det_result.boxes.cls.detach().cpu().numpy().astype(int)
        for i, (row, c, k) in enumerate(zip(coords, confs, clss)):
            if k == PERSON_CLASS:
                color_info = _extract_dominant_color(image_bgr, row)
                persons.append({
                    "chunk_id": f"C_p{i+1}",
                    "type": "person",
                    "bbox": [round(float(v), 1) for v in row],
                    "det_conf": round(float(c), 3),
                    "appearance": color_info,  # e.g. {"color_name": "blue", "hex": "#1a3a5c"}
                })

    # --- PPE / helmet detection ---
    t1 = time.perf_counter()
    ppe_model = YOLO(str(PPE_WEIGHTS))
    ppe_result = ppe_model.predict(image_bgr, imgsz=640, conf=PPE_CONF, verbose=False)[0]
    timings["ppe_detection"] = time.perf_counter() - t1

    ppe_detections = []
    if ppe_result.boxes is not None and len(ppe_result.boxes):
        coords = ppe_result.boxes.xyxy.detach().cpu().numpy()
        confs = ppe_result.boxes.conf.detach().cpu().numpy()
        clss = ppe_result.boxes.cls.detach().cpu().numpy().astype(int)
        names = ppe_result.names
        for row, c, k in zip(coords, confs, clss):
            color_info = _extract_dominant_color(image_bgr, row)
            ppe_detections.append({
                "chunk_id": f"C_ppe{len(ppe_detections)+1}",
                "type": "ppe",
                "ppe_class": names[k],       # "Hardhat" or "NO-Hardhat"
                "wearing_state": "wearing" if k == PPE_CLASS_HARDHAT else "not_wearing",
                "bbox": [round(float(v), 1) for v in row],
                "det_conf": round(float(c), 3),
                "appearance": color_info,  # e.g. {"color_name": "yellow", "hex": "#f0c020"}
            })

    # --- Pose estimation ---
    t2 = time.perf_counter()
    pose_model = YOLO(str(POSE_WEIGHTS))
    pose_result = pose_model.predict(image_bgr, imgsz=640, conf=POSE_CONF, verbose=False)[0]
    timings["pose_estimation"] = time.perf_counter() - t2

    from scenario5.cv_stack.pose_proxy import compute_pose_proxy
    pose_proxies = []
    if pose_result.boxes is not None and len(pose_result.boxes):
        coords = pose_result.boxes.xyxy.detach().cpu().numpy()
        kps = pose_result.keypoints
        for i, row in enumerate(coords):
            kp = kps.data[i].detach().cpu().numpy() if kps is not None else np.empty((0, 3))
            proxy = compute_pose_proxy(kp, tuple(row))
            pose_proxies.append({
                "bbox": [round(float(v), 1) for v in row],
                "pose_proxy": proxy,
            })

    # Match pose to persons
    for person in persons:
        best_iou = 0.0
        for pp in pose_proxies:
            iou = _box_iou(person["bbox"], pp["bbox"])
            if iou > best_iou:
                best_iou = iou
                person["pose_proxy"] = pp["pose_proxy"]
                person["pose_iou"] = round(best_iou, 3)

    # Match PPE to persons
    for ppe in ppe_detections:
        best_iou = 0.0
        best_person = None
        for person in persons:
            iou = _box_iou(ppe["bbox"], person["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_person = person
        ppe["matched_person"] = best_person["chunk_id"] if best_person else None
        ppe["match_iou"] = round(best_iou, 3)
        if best_person:
            # Determine head region (upper 1/4 of person bbox)
            head_region = _head_region(best_person["bbox"])
            ppe["head_region"] = head_region
            ppe["in_head_region"] = _bbox_overlap(ppe["bbox"], head_region) > 0.3

    # --- Open-vocabulary detection (Florence-2) for domain-specific objects ---
    # Detects: face_mask, cigarette, work_clothes, safety_vest, fire_extinguisher, etc.
    t3 = time.perf_counter()
    open_vocab_detections = []
    ocr_texts = []
    try:
        from scenario5.cv_stack.open_vocab_detector import SCENE5_TARGETS, detect_objects, extract_text
        open_vocab_detections = detect_objects(image_path, SCENE5_TARGETS)
        ocr_texts = extract_text(image_path)
    except (ImportError, RuntimeError, OSError):
        pass  # Florence-2 optional; pipeline continues without it
    timings["open_vocab_detection"] = time.perf_counter() - t3

    # Build chunks dict
    entities = persons + ppe_detections
    parts = []
    for person in persons:
        head = _head_region(person["bbox"])
        parts.append({
            "chunk_id": f"C_head_{person['chunk_id']}",
            "type": "head_region",
            "parent": person["chunk_id"],
            "bbox": head,
        })

    # Add open-vocab detections as additional entity chunks
    for i, det in enumerate(open_vocab_detections):
        color_info = _extract_dominant_color(image_bgr, det["bbox"])
        entities.append({
            "chunk_id": f"C_ov{i+1}",
            "type": "open_vocab",
            "label": det["label"],
            "bbox": det["bbox"],
            "appearance": color_info,
            "source": det.get("source", "florence2"),
        })

    return {
        "quality": quality,
        "chunks": {
            "scene": {
                "chunk_id": "C_scene",
                "type": "global_scene",
                "width": image_bgr.shape[1],
                "height": image_bgr.shape[0],
                "person_count": len(persons),
                "ppe_count": len(ppe_detections),
                "open_vocab_count": len(open_vocab_detections),
            },
            "entities": entities,
            "parts": parts,
            "text": ocr_texts,  # OCR results from Florence-2
        },
        "timings": timings,
    }


# ============ Layer 2: Intra-Image Relationship Graph ============

def build_visual_graph(chunks: dict[str, Any]) -> dict[str, Any]:
    """Build the visual relationship graph G_v = (V, E) from extracted chunks."""
    entities = chunks["entities"]
    persons = [e for e in entities if e["type"] == "person"]
    ppe_items = [e for e in entities if e["type"] == "ppe"]

    edges: list[dict[str, Any]] = []

    # --- Spatial relations between persons ---
    for i, a in enumerate(persons):
        for b in persons[i + 1 :]:
            edge = _spatial_relation(a, b)
            if edge:
                edges.append(edge)

    # --- Interaction relations: person ↔ PPE ---
    for person in persons:
        for ppe in ppe_items:
            if ppe.get("matched_person") == person["chunk_id"]:
                rel_type = "wearing" if ppe["wearing_state"] == "wearing" else "not_wearing"
                edges.append({
                    "source": person["chunk_id"],
                    "target": ppe["chunk_id"],
                    "relation": rel_type,
                    "confidence": ppe["det_conf"],
                    "evidence": f"ppe_class={ppe['ppe_class']}, in_head={ppe.get('in_head_region')}",
                })

    # --- Attribute relations: person → pose state ---
    for person in persons:
        proxy = person.get("pose_proxy", {})
        if proxy and proxy.get("prone_like"):
            edges.append({
                "source": person["chunk_id"],
                "target": person["chunk_id"],
                "relation": "prone_like",
                "confidence": 0.7,
                "evidence": f"torso_angle={proxy.get('torso_angle_from_vertical_deg')}",
            })
        if proxy and proxy.get("head_down"):
            edges.append({
                "source": person["chunk_id"],
                "target": person["chunk_id"],
                "relation": "head_down",
                "confidence": 0.6,
                "evidence": f"nose_ratio={proxy.get('nose_above_shoulders_ratio')}",
            })

    return {
        "nodes": [e["chunk_id"] for e in entities],
        "edges": edges,
        "node_details": entities,
    }


def _spatial_relation(a: dict, b: dict) -> dict | None:
    """Determine spatial relation between two person bboxes."""
    ax, ay = _center(a["bbox"])
    bx, by = _center(b["bbox"])
    dx, dy = bx - ax, by - ay
    dist = (dx**2 + dy**2) ** 0.5
    if dist > NEAR_DISTANCE_PX:
        return None
    relation = []
    if abs(dx) > abs(dy):
        relation.append("left_of" if dx > 0 else "right_of")
    else:
        relation.append("above" if dy < 0 else "below")
    relation.append("near")
    return {
        "source": a["chunk_id"],
        "target": b["chunk_id"],
        "relation": "_".join(relation),
        "distance_px": round(dist, 1),
        "confidence": 0.8,
    }


# ============ Layer 3: QA Text Semantic Parsing ============

# Semantic keyword patterns for helmet scenario
HELMET_NEGATION = ["未佩戴", "没有佩戴", "未戴", "没有戴", "无安全帽", "没有安全帽"]
HELMET_POSITIVE = ["佩戴安全帽", "戴着安全帽", "戴了安全帽", "有安全帽"]
PRONE_KEYWORDS = ["趴伏", "趴在", "趴于", "伏案", "趴卧"]
SPATIAL_LEFT = ["左侧人员", "左边人员", "左边的人", "左侧的人"]
SPATIAL_RIGHT = ["右侧人员", "右边人员", "右边的人", "右侧的人"]
ALL_PERSONS = ["所有人员", "全部人员", "所有工人", "全员", "每个人"]


def parse_qa_text(user_text: str, gpt_text: str) -> dict[str, Any]:
    """Parse QA text into structured semantic propositions.

    Returns:
        {
            "propositions": [...],
            "entities": [...],
            "attributes": [...],
            "negation_scope": [...],
            "scene_conditions": [...],
        }
    """
    combined_text = user_text + " " + gpt_text
    propositions: list[dict[str, Any]] = []
    entities: list[str] = []
    negation_scope: list[str] = []

    # Entity extraction
    if any(k in combined_text for k in ["安全帽", "头盔", "帽子"]):
        entities.append("helmet")
    if any(k in combined_text for k in ["人员", "工人", "作业人员", "员工"]):
        entities.append("person")
    if any(k in combined_text for k in ["工位", "工作台", "桌子"]):
        entities.append("workstation")

    # Proposition: wearing/not_wearing helmet
    helmet_neg = any(k in combined_text for k in HELMET_NEGATION)
    helmet_pos = any(k in combined_text for k in HELMET_POSITIVE)
    if helmet_neg:
        propositions.append({
            "id": "P_helmet_neg",
            "subject": _extract_subject(combined_text),
            "predicate": "wearing",
            "object": "helmet",
            "polarity": "negative",
            "evidence_text": _find_keyword_context(combined_text, HELMET_NEGATION),
        })
        negation_scope.append("helmet_wearing")
    elif helmet_pos:
        propositions.append({
            "id": "P_helmet_pos",
            "subject": _extract_subject(combined_text),
            "predicate": "wearing",
            "object": "helmet",
            "polarity": "positive",
            "evidence_text": _find_keyword_context(combined_text, HELMET_POSITIVE),
        })

    # Proposition: prone posture
    if any(k in combined_text for k in PRONE_KEYWORDS):
        propositions.append({
            "id": "P_prone",
            "subject": _extract_subject(combined_text),
            "predicate": "posture",
            "object": "prone",
            "polarity": "positive",
            "evidence_text": _find_keyword_context(combined_text, PRONE_KEYWORDS),
        })

    # Spatial reference
    spatial_ref = None
    if any(k in combined_text for k in SPATIAL_LEFT):
        spatial_ref = "left"
    elif any(k in combined_text for k in SPATIAL_RIGHT):
        spatial_ref = "right"

    # Scene conditions
    scene_conditions = []
    if any(k in combined_text for k in ["工位", "工作台", "车间", "生产现场"]):
        scene_conditions.append("workstation")
    if any(k in combined_text for k in ["通道", "疏散通道"]):
        scene_conditions.append("corridor")

    return {
        "propositions": propositions,
        "entities": entities,
        "spatial_reference": spatial_ref,
        "negation_scope": negation_scope,
        "scene_conditions": scene_conditions,
        "person_scope": "all" if any(k in combined_text for k in ALL_PERSONS) else "specific",
    }


def _extract_subject(text: str) -> str:
    if any(k in text for k in SPATIAL_LEFT):
        return "person_left"
    if any(k in text for k in SPATIAL_RIGHT):
        return "person_right"
    if any(k in text for k in ALL_PERSONS):
        return "all_persons"
    return "person_unspecified"


def _find_keyword_context(text: str, keywords: list[str], window: int = 20) -> str:
    for keyword in keywords:
        idx = text.find(keyword)
        if idx >= 0:
            start = max(0, idx - window)
            return text[start : idx + len(keyword) + window]
    return ""


# ============ Layer 4: Cross-Modal Association ============

def cross_modal_associate(
    qa_parsed: dict[str, Any],
    visual_graph: dict[str, Any],
) -> dict[str, Any]:
    """Map QA semantic propositions to visual chunks and relations."""
    entities = visual_graph["node_details"]
    persons = [e for e in entities if e["type"] == "person"]
    ppe_items = [e for e in entities if e["type"] == "ppe"]

    mappings: list[dict[str, Any]] = []
    linked_chunks: set[str] = set()

    # --- Resolve spatial reference ---
    target_persons = persons
    if qa_parsed.get("spatial_reference") == "left" and len(persons) > 1:
        persons_sorted = sorted(persons, key=lambda p: p["bbox"][0])
        target_persons = [persons_sorted[0]]
    elif qa_parsed.get("spatial_reference") == "right" and len(persons) > 1:
        persons_sorted = sorted(persons, key=lambda p: p["bbox"][0])
        target_persons = [persons_sorted[-1]]

    # --- Map propositions to visual evidence ---
    for prop in qa_parsed.get("propositions", []):
        prop_id = prop["id"]
        linked = []

        if "helmet" in prop.get("predicate", "") or prop.get("object") == "helmet":
            # Map to person chunks + PPE chunks
            for person in target_persons:
                linked.append(person["chunk_id"])
                linked_chunks.add(person["chunk_id"])
                # Find matching PPE for this person
                matching_ppe = [
                    p for p in ppe_items
                    if p.get("matched_person") == person["chunk_id"]
                ]
                for ppe in matching_ppe:
                    linked.append(ppe["chunk_id"])
                    linked_chunks.add(ppe["chunk_id"])

            # Determine visual evidence status
            if prop["polarity"] == "negative":
                # QA claims: person NOT wearing helmet
                # Check visual: is there a "no-hardhat" detection matching this person?
                not_wearing_found = False
                wearing_found = False
                for person in target_persons:
                    matching_ppe = [
                        p for p in ppe_items
                        if p.get("matched_person") == person["chunk_id"]
                    ]
                    if not matching_ppe:
                        not_wearing_found = True  # No PPE detected on this person
                    for ppe in matching_ppe:
                        if ppe["wearing_state"] == "not_wearing":
                            not_wearing_found = True
                        elif ppe["wearing_state"] == "wearing":
                            wearing_found = True

                if not_wearing_found and not wearing_found:
                    observation_status = "confirmed"
                elif wearing_found and not not_wearing_found:
                    observation_status = "contradicted"
                elif not_wearing_found and wearing_found:
                    # Mixed: some wearing, some not (multi-person)
                    observation_status = "mixed"
                else:
                    observation_status = "needs_verification"
            else:
                # QA claims: person IS wearing helmet
                wearing_found = any(
                    p["wearing_state"] == "wearing"
                    for p in ppe_items
                    if p.get("matched_person") in {tp["chunk_id"] for tp in target_persons}
                )
                observation_status = "confirmed" if wearing_found else "needs_verification"

            mappings.append({
                "claim_id": prop_id,
                "subject": prop.get("subject"),
                "relation": prop.get("predicate"),
                "object": prop.get("object"),
                "polarity": prop.get("polarity"),
                "linked_chunks": linked,
                "observation_status": observation_status,
                "visual_evidence": {
                    "person_count": len(persons),
                    "ppe_detections": len(ppe_items),
                    "wearing_count": sum(1 for p in ppe_items if p["wearing_state"] == "wearing"),
                    "not_wearing_count": sum(1 for p in ppe_items if p["wearing_state"] == "not_wearing"),
                },
            })

        if prop.get("object") == "prone":
            for person in target_persons:
                proxy = person.get("pose_proxy", {})
                if proxy and proxy.get("prone_like"):
                    mappings.append({
                        "claim_id": prop_id,
                        "subject": person["chunk_id"],
                        "relation": "posture_prone",
                        "observation_status": "confirmed",
                        "linked_chunks": [person["chunk_id"]],
                    })
                elif proxy:
                    mappings.append({
                        "claim_id": prop_id,
                        "subject": person["chunk_id"],
                        "relation": "posture_prone",
                        "observation_status": "contradicted" if not proxy.get("prone_like") else "confirmed",
                        "linked_chunks": [person["chunk_id"]],
                    })

    return {
        "mappings": mappings,
        "linked_chunks": list(linked_chunks),
    }


# ============ Layer 5: Consistency Verification ============

def verify_consistency(
    qa_parsed: dict[str, Any],
    visual_graph: dict[str, Any],
    cross_modal: dict[str, Any],
    answer: int | None = None,
) -> dict[str, Any]:
    """Three-way comparison: visual facts × QA claims × rules → verdict."""
    verdicts: list[dict[str, Any]] = []

    for mapping in cross_modal.get("mappings", []):
        status = mapping.get("observation_status")
        prop_id = mapping.get("claim_id")

        if status == "confirmed":
            verdicts.append({
                "item": prop_id,
                "verdict": "support",
                "reason": f"Visual evidence confirms: {mapping.get('relation')}",
                "evidence_chunks": mapping.get("linked_chunks", []),
            })
        elif status == "contradicted":
            verdicts.append({
                "item": prop_id,
                "verdict": "refute",
                "reason": f"Visual evidence contradicts: {mapping.get('relation')}",
                "evidence_chunks": mapping.get("linked_chunks", []),
            })
        elif status == "mixed":
            verdicts.append({
                "item": prop_id,
                "verdict": "suspicious",
                "reason": "Mixed evidence across multiple persons; needs human review",
                "evidence_chunks": mapping.get("linked_chunks", []),
            })
        else:
            verdicts.append({
                "item": prop_id,
                "verdict": "NIE",
                "reason": "Insufficient visual evidence to confirm or contradict",
                "evidence_chunks": mapping.get("linked_chunks", []),
            })

    # Overall verdict: worst case
    if any(v["verdict"] == "refute" for v in verdicts):
        overall = "refute"
    elif any(v["verdict"] == "suspicious" for v in verdicts):
        overall = "suspicious"
    elif any(v["verdict"] == "NIE" for v in verdicts):
        overall = "NIE"
    elif verdicts and all(v["verdict"] == "support" for v in verdicts):
        overall = "support"
    else:
        overall = "NIE"

    return {
        "overall_verdict": overall,
        "per_claim_verdicts": verdicts,
        "answer": answer,
        "note": "QA answer (task label) is independent of consistency verdict",
    }


# ============ Utilities ============

def _extract_dominant_color(image_bgr: np.ndarray, bbox: list[float]) -> dict[str, Any]:
    """Extract dominant color from a bbox region (appearance feature)."""
    x1, y1, x2, y2 = [int(max(0, v)) for v in bbox]
    x2, y2 = min(x2, image_bgr.shape[1]), min(y2, image_bgr.shape[0])
    if x2 <= x1 or y2 <= y1:
        return {"bgr": [0, 0, 0], "hex": "#000000", "color_name": "unknown"}
    region = image_bgr[y1:y2, x1:x2]
    # Downsample for speed
    if region.size > 10000:
        indices = np.random.default_rng(42).integers(0, region.shape[0], 100)
        region = region[indices]
    mean_bgr = region.reshape(-1, 3).mean(axis=0).astype(int)
    hex_color = "#{:02x}{:02x}{:02x}".format(mean_bgr[2], mean_bgr[1], mean_bgr[0])
    color_name = _color_name(mean_bgr)
    return {"bgr": mean_bgr.tolist(), "hex": hex_color, "color_name": color_name}


def _color_name(bgr: np.ndarray) -> str:
    """Classify a BGR color into a coarse color name."""
    b, g, r = bgr
    if r > 200 and g > 200 and b > 200:
        return "white"
    if r < 50 and g < 50 and b < 50:
        return "black"
    if abs(r - g) < 30 and abs(g - b) < 30:
        return "gray"
    if r > 180 and g > 150 and b < 100:
        return "yellow"
    if r > 150 and g < 100 and b < 100:
        return "red"
    if r < 100 and g > 130 and b < 100:
        return "green"
    if r < 100 and g < 130 and b > 150:
        return "blue"
    if r > 150 and g > 100 and b < 80:
        return "orange"
    return "mixed"


def _box_iou(a: list[float], b: list[float]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _bbox_overlap(a: list[float], b: list[float]) -> float:
    """Overlap ratio of a within b (intersection / area_a)."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    return inter / area_a if area_a > 0 else 0.0


def _center(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


def _head_region(person_bbox: list[float]) -> list[float]:
    """Extract upper 1/4 of person bbox as approximate head region."""
    x1, y1, x2, y2 = person_bbox
    h = y2 - y1
    return [x1, y1, x2, y1 + h * 0.25]


# ============ Main Pipeline ============

def run_helmet_pipeline(image_path: Path, user_text: str, gpt_text: str, answer: int | None = None) -> dict[str, Any]:
    """Run the complete safety helmet pipeline: chunks → graph → QA parse → cross-modal → NLI verdict."""
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise RuntimeError(f"cannot decode {image_path}")

    # Layer 1: Extract chunks (now includes open-vocab detection + OCR)
    chunk_result = extract_chunks(image_bgr, image_path)

    # Layer 2: Build visual graph
    visual_graph = build_visual_graph(chunk_result["chunks"])

    # Layer 3: QA semantic parsing via Qwen NER
    from scenario5.cv_stack.qa_ner import extract_semantics
    qa_parsed = extract_semantics(user_text, gpt_text)

    # Layer 4: Cross-modal association
    cross_modal = cross_modal_associate(qa_parsed, visual_graph)

    # Layer 5: NLI-based consistency verification
    from scenario5.cv_stack.nli_verifier import run_nli_verification

    # Build visual summary for NLI premise
    entities = chunk_result["chunks"]["entities"]
    persons = [e for e in entities if e["type"] == "person"]
    ppe_items = [e for e in entities if e["type"] == "ppe"]
    visual_summary = {
        "person_count": len(persons),
        "ppe_detections": len(ppe_items),
        "wearing_count": sum(1 for p in ppe_items if p["wearing_state"] == "wearing"),
        "not_wearing_count": sum(1 for p in ppe_items if p["wearing_state"] == "not_wearing"),
        "pose_summary": "",
    }
    # Add pose info if available
    prone_persons = [p for p in persons if p.get("pose_proxy", {}).get("prone_like")]
    if prone_persons:
        visual_summary["pose_summary"] = f"有{len(prone_persons)}人呈趴伏姿态"

    # Build QA claims from parsed semantics
    qa_claims = []
    parsed = qa_parsed.get("parsed", {})
    for rel in parsed.get("relations", []):
        neg = rel.get("negated", False)
        subject = rel.get("subject", "人员")
        predicate = rel.get("predicate", "")
        obj = rel.get("object", "")
        if neg:
            hypothesis = f"{subject}没有{predicate}{obj}"
        else:
            hypothesis = f"{subject}{predicate}了{obj}"
        qa_claims.append({
            "claim_id": f"P_{predicate}_{obj}",
            "hypothesis": hypothesis,
        })

    # If NER didn't extract relations, try to extract from QA evidence text
    if not qa_claims:
        # Parse gpt_text as JSON to get evidence
        try:
            gpt_json = json.loads(gpt_text)
            evidence_list = gpt_json.get("evidence", [])
            if isinstance(evidence_list, list):
                for i, ev in enumerate(evidence_list[:3]):
                    ev_text = str(ev)[:200]
                    qa_claims.append({
                        "claim_id": f"P_evidence_{i}",
                        "hypothesis": ev_text,
                    })
            elif isinstance(evidence_list, str):
                qa_claims.append({
                    "claim_id": "P_evidence_0",
                    "hypothesis": evidence_list[:200],
                })
        except (json.JSONDecodeError, TypeError):
            # gpt_text is not JSON, use user_text as hypothesis
            qa_claims.append({
                "claim_id": "P_user_query",
                "hypothesis": user_text[:200],
            })

    if not qa_claims:
        qa_claims.append({
            "claim_id": "P_default",
            "hypothesis": user_text[:200] or gpt_text[:200],
        })

    # Run NLI verification
    nli_result = run_nli_verification(visual_summary, qa_claims)

    # Combine rule-based cross-modal + NLI results
    rule_verification = verify_consistency(qa_parsed, visual_graph, cross_modal, answer)

    # Final verdict: use NLI as primary, rule-based as secondary
    nli_overall = nli_result["overall_verdict"]
    rule_overall = rule_verification["overall_verdict"]

    # If NLI and rules agree, use that; if disagree, be conservative (worse verdict)
    verdict_priority = {"refute": 0, "suspicious": 1, "NIE": 2, "support": 3}
    final = nli_overall if nli_overall == rule_overall else (
        nli_overall if verdict_priority.get(nli_overall, 2) <= verdict_priority.get(rule_overall, 2) else rule_overall
    )

    return {
        "image_id": f"img:{image_path.stem}",
        "layers": {
            "L1_chunks": chunk_result,
            "L2_visual_graph": visual_graph,
            "L3_qa_ner": qa_parsed,
            "L4_cross_modal": cross_modal,
            "L5_nli_verification": nli_result,
            "L5_rule_verification": rule_verification,
        },
        "final_verdict": final,
        "pipeline_version": "helmet_v2_nli",
        "verdict_method": "NLI(Erlangshen-330M) + rule-based fallback",
    }
