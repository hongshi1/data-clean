#!/usr/bin/env python3
"""
M2b: OCR感知通道 (ACDD第三通道)
=================================
RapidOCR对89张sc2图提取文字块(带bbox+置信度)。
OCR是部分通道: 只有文字存在性, 没有边/类型/方向 —
其价值在于与VLM误差模式不同(独立的第二测量)。

输出: data/gjb_438c/anchor_sc2/ocr_extractions.json
  每对: {pair_key, blocks: [{text, box, score}], full_text}

注意: 需在 .venv-srs 中运行(rapidocr装在那里)

用法: .venv-srs/bin/python tools/m2b_ocr_channel.py
"""
import json
import sys
import time
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR

BASE = Path(__file__).resolve().parent.parent
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUT_PATH = BASE / "data/gjb_438c/anchor_sc2/ocr_extractions.json"


def main():
    mapping = json.loads(MAPPING_PATH.read_text())
    ocr = RapidOCR()

    results = {}
    if OUT_PATH.exists():
        results = json.loads(OUT_PATH.read_text())
        print(f"断点续跑: 已有{len(results)}条")

    pair_keys = sorted(mapping.keys())
    print(f"M2b: OCR通道提取 ({len(pair_keys)}对)")

    t0 = time.time()
    for i, pk in enumerate(pair_keys):
        if pk in results:
            continue
        img_path = PAIR_DIR / pk / 'image.png'
        if not img_path.exists():
            results[pk] = {'error': 'no_image'}
            continue
        try:
            ocr_result, _ = ocr(str(img_path))
            blocks = []
            if ocr_result:
                for box, text, score in ocr_result:
                    if text and float(score) > 0.4:
                        blocks.append({
                            'text': text.strip(),
                            'box': [[round(float(x), 1), round(float(y), 1)]
                                    for pt in box for x, y in [pt]] if box else [],
                            'score': round(float(score), 3),
                        })
            results[pk] = {
                'pair_key': pk,
                'blocks': blocks,
                'full_text': ' '.join(b['text'] for b in blocks),
                'n_blocks': len(blocks),
            }
        except Exception as e:
            results[pk] = {'error': str(e)[:100]}
        if (i + 1) % 20 == 0:
            OUT_PATH.write_text(json.dumps(results, ensure_ascii=False))
            print(f"  [{i+1}/{len(pair_keys)}] {time.time()-t0:.0f}s")

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    ok = [r for r in results.values() if 'error' not in r]
    total_blocks = sum(r.get('n_blocks', 0) for r in ok)
    print(f"\n完成: {len(ok)}/{len(results)}成功, 共{total_blocks}文字块")
    print(f"输出: {OUT_PATH}")

    # 抽样展示
    for pk in list(results)[:2]:
        r = results[pk]
        if 'error' not in r:
            print(f"\n[{pk}] {r['n_blocks']}块: {[b['text'][:12] for b in r['blocks'][:6]]}")


if __name__ == "__main__":
    main()
