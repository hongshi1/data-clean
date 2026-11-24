"""kg真实视觉Chunk生成: 用场景五CV管线(YOLO人员+安全帽+姿态)跑演示图集.

将 deploy/nkuDataProject/frontend/images/kg/ 的40张图跑真实检测,
输出 deploy/nkuDataProject/data/kg_supervision/visual_chunks_real.json:
  {source: real_cv, models: {...}, chunks: {<图名(无扩展)>: {
    size: [w, h],
    persons: [{bbox:[x1,y1,x2,y2]像素, conf, pose(倒地/趴伏/站立),
               head_down, prone_like}],
    ppes: [{bbox像素, conf, state(worn/missing), ppe_class, matched_person(人员序号)}]
  }}}

运行: python tools/kg_build_real_chunks.py
(确定性输出: 同图同模型→同结果; 重新生成需删除JSON)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

IMG_DIR = ROOT / "deploy/nkuDataProject/frontend/images/kg"
OUT_PATH = ROOT / "deploy/nkuDataProject/data/kg_supervision/visual_chunks_real.json"
MAX_PERSONS = 8  # 单图人员上限(图谱可读性)

# ppe_class → 前端ptype
_PPE_TYPE = {"Hardhat": "helmet", "NO-Hardhat": "helmet"}


def _pose_label(pose_proxy: dict) -> str:
    """姿态代理 → 前端姿态标签(prone→倒地, head_down→趴伏, 否则站立)."""
    if pose_proxy.get("prone_like"):
        return "倒地"
    if pose_proxy.get("head_down"):
        return "趴伏"
    return "站立"


def main() -> None:
    import cv2

    from scenario5.cv_stack.helmet_pipeline import extract_chunks

    images = sorted(IMG_DIR.glob("*.jpg"))
    if not images:
        print(f"[kg_real] 无图片: {IMG_DIR}")
        return

    chunks: dict[str, dict] = {}
    t0 = time.time()
    for i, img_path in enumerate(images, 1):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[kg_real] 跳过(读取失败): {img_path.name}")
            continue
        h, w = img.shape[:2]
        result = extract_chunks(img, img_path)
        entities = result["chunks"]["entities"]

        # 人员: 按置信度降序, 截MAX_PERSONS
        persons_raw = [e for e in entities if e.get("type") == "person"]
        persons_raw.sort(key=lambda e: -float(e.get("det_conf", 0)))
        persons_raw = persons_raw[:MAX_PERSONS]
        # chunk_id → 序号映射(ppe的matched_person引用)
        idx_of = {e["chunk_id"]: j for j, e in enumerate(persons_raw)}

        persons = []
        for j, e in enumerate(persons_raw):
            pp = e.get("pose_proxy") or {}
            persons.append({
                "bbox": [round(float(v), 1) for v in e["bbox"]],
                "conf": round(float(e.get("det_conf", 0)), 3),
                "pose": _pose_label(pp),
                "head_down": pp.get("head_down"),
                "prone_like": bool(pp.get("prone_like", False)),
            })

        ppes = []
        for e in entities:
            if e.get("type") != "ppe":
                continue
            mp = idx_of.get(e.get("matched_person"))
            if mp is None:  # 未匹配到已保留人员的装备框, 跳过
                continue
            state = "worn" if e.get("wearing_state") == "wearing" else "missing"
            ppes.append({
                "bbox": [round(float(v), 1) for v in e["bbox"]],
                "conf": round(float(e.get("det_conf", 0)), 3),
                "state": state,
                "ppe_class": e.get("ppe_class", ""),
                "matched_person": mp,
            })
        ppes.sort(key=lambda p: (p["matched_person"], -p["conf"]))

        key = img_path.stem
        chunks[key] = {"size": [w, h], "persons": persons, "ppes": ppes}
        n_p = len(persons)
        n_e = len(ppes)
        print(f"[kg_real] {i}/{len(images)} {key}: {n_p}人 {n_e}装备 "
              f"({w}x{h}, conf_top={persons[0]['conf'] if persons else '—'})")

    out = {
        "source": "real_cv",
        "models": {
            "person": "yolo11s.pt",
            "ppe": "best.pt",
            "pose": "yolo11n-pose.pt",
        },
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "max_persons": MAX_PERSONS,
        "n_images": len(chunks),
        "chunks": chunks,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    total_p = sum(len(c["persons"]) for c in chunks.values())
    total_e = sum(len(c["ppes"]) for c in chunks.values())
    print(f"\n[kg_real] 完成: {len(chunks)}图 {total_p}人员框 {total_e}装备框 "
          f"({time.time() - t0:.1f}s) → {OUT_PATH}")


if __name__ == "__main__":
    main()
