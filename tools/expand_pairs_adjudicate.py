#!/usr/bin/env python3
"""扩展pair集的GLM-5一致性裁决标注 (369对).

输入: data/gjb_438c/pair_dataset_expanded/expanded_pairs.json
输出: data/gjb_438c/pair_dataset_expanded/adjudicated_pairs.json

证据说明:
  - chunk里的 image_caption 全为空("[图片] ") → 图信息从 mineru_standard 恢复:
    图题(_content_list.json) + 引文/邻段(markdown中图片引用前后文本) + 图所在节(heading)
  - table_text 去HTML标签后取前200字(模板要求)
  - LLM: algorithms/llm_client.llm_json(prompt, cache=True) → GLM-5, 磁盘缓存可复现

标签映射: real_bug→inconsistent, benign_variation→consistent, unsure→unsure

用法: python tools/expand_pairs_adjudicate.py [--workers 6] [--limit N] [--dry-run]
(断点续跑: 已完成的pair自动跳过; LLM缓存命中时重跑零成本)
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from algorithms.common.llm_client import llm_json  # noqa: E402

IN_PATH = BASE / "data/gjb_438c/pair_dataset_expanded/expanded_pairs.json"
OUT_PATH = BASE / "data/gjb_438c/pair_dataset_expanded/adjudicated_pairs.json"
MS_ROOT = BASE / "data/gjb_438c/mineru_standard"
CHUNKS_PATH = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"

LABEL_MAP = {"real_bug": "inconsistent",
             "benign_variation": "consistent",
             "unsure": "unsure"}
SCENE_NOTE = {
    "sc1_usecase_capability": "功能/能力需求表 与 配对图",
    "sc2_flowchart_usecase": "用例描述表 与 配对图",
    "sc3_interface_interface": "接口需求表 与 配对图",
}
SYSTEM = ("你是GJB 438C军用软件需求文档一致性审查专家。"
          "基于给出的证据快速判断,只输出JSON,不要输出任何其他内容。")

TAG_RE = re.compile(r"<[^>]+>")
IMG_REF_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
FIG_CAP_RE = re.compile(r"图\s*[\d\-–.]+\s*[^\n]{0,60}")
INTRO_RE = re.compile(r"([^。\n]{0,80}如图\s*[\d\-–.]+[^。\n]{0,20}。?)\s*$")
HEADING_RE = re.compile(r"^(#{2,6})\s+(.+)$", re.M)

PROMPT = """你是SRS需求文档一致性审查专家。基于以下证据判断表格内容与图内容是否一致。

文档: {doc}
配对场景: {scene_note}
表格所在章节: {t_section}
图所在章节: {i_section}

表格内容: {table_brief}
图信息: {image_info}

规则:
- real_bug: 表格中列出的核心功能/接口/用例在图中完全缺失(数据流断裂)
- benign_variation: 图省略了辅助内容(异常流/参与者/提示步骤),或图粒度粗于表格
- unsure: 基于提供的信息无法判定

只输出JSON: {{"label": "real_bug|benign_variation|unsure", "reason": "一句话理由"}}"""


def clean_table(text: str, n: int = 200) -> str:
    t = re.sub(r"\s+", " ", TAG_RE.sub(" ", text)).strip()
    return t[:n]


class DocContext:
    """按文档缓存 markdown / 图题 / 图引用位置, 供证据恢复."""

    def __init__(self, doc: str):
        office = MS_ROOT / doc / "office"
        md_path = office / f"{doc}.md"
        self.md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        self.captions: dict[str, str] = {}
        cl_path = office / f"{doc}_content_list.json"
        if cl_path.exists():
            try:
                for e in json.loads(cl_path.read_text(encoding="utf-8")):
                    if e.get("type") in ("image", "img") and e.get("image_path"):
                        cap = " ".join(e.get("image_caption") or []).strip()
                        if cap:
                            self.captions[str(e["image_path"])] = cap
            except (json.JSONDecodeError, OSError):
                pass
        self.ref_pos: dict[str, int] = {}
        for m in IMG_REF_RE.finditer(self.md):
            src = m.group(1).replace("\\", "/")
            if src not in self.ref_pos:
                self.ref_pos[src] = m.start()
        self.headings = [(m.start(), m.group(2).strip())
                         for m in HEADING_RE.finditer(self.md)]

    def heading_before(self, pos: int) -> str:
        best = ""
        for hp, text in self.headings:
            if hp < pos:
                best = text
            else:
                break
        return best

    def image_evidence(self, image_path: str) -> dict:
        cap = self.captions.get(image_path, "")
        pos = self.ref_pos.get(image_path, -1)
        intro, nearby = "", ""
        if pos >= 0:
            before = self.md[max(0, pos - 250):pos]
            m = INTRO_RE.search(before)
            intro = m.group(1).strip() if m else ""
            after = re.sub(r"\s+", " ", self.md[pos:pos + 400]).strip()
            after = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", after)
            after = TAG_RE.sub(" ", re.sub(r"<a\s[^>]*>", " ", after))
            after = re.sub(r"#{2,6}\s*", "", after)
            after = re.sub(r"\s+", " ", after).strip()
            if not cap:
                m2 = FIG_CAP_RE.match(after)
                cap = m2.group(0).strip() if m2 else ""
            if cap and after.startswith(cap):
                after = after[len(cap):].strip()
            nearby = after[:120]
        return {"caption": cap, "intro": intro, "nearby": nearby,
                "heading": self.heading_before(pos) if pos >= 0 else ""}


def build_image_info(pair: dict, ev: dict, img_section: str) -> str:
    heading = ev["heading"][:40]
    i_section = heading if (heading and img_section and heading.startswith(img_section)) \
        else (f"{img_section} {heading}" if heading and img_section
              else (heading or img_section))
    parts = []
    if ev["caption"]:
        parts.append(f"图题: {ev['caption']}")
    else:
        parts.append("图题: (无)")
    if i_section:
        parts.append(f"图所在节: {i_section}")
    if ev["intro"]:
        parts.append(f"正文引文: {ev['intro']}")
    if ev["nearby"]:
        parts.append(f"图后邻文: {ev['nearby']}")
    raw_cap = str(pair.get("image_caption", "")).strip()
    prefix = f"{raw_cap} " if raw_cap and raw_cap != "[图片]" else ""
    return prefix + "; ".join(parts)


def adjudicate(pair: dict, doc_ctx: DocContext, img_section: str) -> tuple[dict, str]:
    """单条裁决: 返回(llm结果dict, model). 失败时label=unsure."""
    scene_note = SCENE_NOTE.get(pair["scene"], pair["scene"])
    ev = doc_ctx.image_evidence(pair["image_path"])
    prompt = PROMPT.format(
        doc=pair["doc"], scene_note=scene_note,
        t_section=pair.get("section", ""),
        i_section=img_section or "(未知)",
        table_brief=clean_table(pair["table_text"]),
        image_info=build_image_info(pair, ev, img_section))

    out, model = {}, "none"
    for attempt in range(3):
        try:
            out, model = llm_json(prompt, system=SYSTEM, cache=True)
            break
        except Exception as e:
            if attempt == 2:
                return {"label": "unsure",
                        "reason": f"llm_call_failed: {type(e).__name__}: {e}"}, "none"
            time.sleep(8)
    label = str(out.get("label", "")).strip()
    if label not in LABEL_MAP:
        try:
            out, model = llm_json(prompt, system=SYSTEM, cache=False)
            label = str(out.get("label", "")).strip()
        except Exception:
            label = ""
    if label not in LABEL_MAP:
        return {"label": "unsure",
                "reason": f"parse_error: {json.dumps(out, ensure_ascii=False)[:80]}"}, model
    return {"label": label, "reason": str(out.get("reason", ""))[:200]}, model


def pair_key(p: dict) -> str:
    return f"{p['table_chunk_id']}|{p['image_chunk_id']}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    pairs = data["pairs"]
    if args.limit:
        pairs = pairs[:args.limit]
    print(f"{'=' * 66}")
    print(f"扩展pair集 GLM-5 一致性裁决: {len(pairs)}对 (workers={args.workers})")
    print(f"{'=' * 66}")
    print(f"  场景分布: {dict(Counter(p['scene'] for p in pairs))}")

    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    img_sec = {c.get("chunk_id", ""): str(c.get("section", "")) for c in chunks
               if c.get("type") == "image"}
    doc_ctxs: dict[str, DocContext | None] = {}
    for doc in sorted({p["doc"] for p in pairs}):
        try:
            doc_ctxs[doc] = DocContext(doc)
        except OSError as e:
            print(f"  [warn] 文档加载失败 {doc[:16]}: {e}")
            doc_ctxs[doc] = None

    done: dict[str, dict] = {}
    if OUT_PATH.exists():
        old = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        for rec in old.get("pairs", []):
            done[pair_key(rec)] = rec
        print(f"  断点续跑: 已完成 {len(done)} 条")

    todo = [p for p in pairs if pair_key(p) not in done]
    print(f"  待裁决: {len(todo)} 条")
    if args.dry_run:
        for p in todo[:2]:
            ctx = doc_ctxs.get(p["doc"])
            if ctx is None:
                continue
            print(f"\n---- {p['doc'][:12]} {p['section']} {p['image_path']}")
            print(PROMPT.format(
                doc=p["doc"], scene_note=SCENE_NOTE.get(p["scene"], p["scene"]),
                t_section=p.get("section", ""),
                i_section=img_sec.get(p["image_chunk_id"], "") or "(未知)",
                table_brief=clean_table(p["table_text"]),
                image_info=build_image_info(p, ctx.image_evidence(p["image_path"]),
                                            img_sec.get(p["image_chunk_id"], ""))))
        return

    results = dict(done)
    t0 = time.time()

    def run_one(p: dict) -> tuple[str, dict]:
        ctx = doc_ctxs.get(p["doc"])
        if ctx is None:
            return pair_key(p), {**p, "label": "unsure", "llm_label": "unsure",
                                 "reason": "doc_context_unavailable", "model": "none"}
        verdict, model = adjudicate(p, ctx, img_sec.get(p["image_chunk_id"], ""))
        ev = ctx.image_evidence(p["image_path"])
        return pair_key(p), {
            **p,
            "figure_caption": ev["caption"],
            "figure_intro": ev["intro"],
            "figure_section": img_sec.get(p["image_chunk_id"], ""),
            "llm_label": verdict["label"],
            "label": LABEL_MAP[verdict["label"]],
            "reason": verdict["reason"],
            "model": model,
        }

    def flush() -> None:
        ordered = [results[k] for k in [pair_key(p) for p in pairs] if k in results]
        dist = Counter(r["label"] for r in ordered)
        out = {
            "total": len(ordered),
            "meta": {
                "generated_by": "tools/expand_pairs_adjudicate.py",
                "llm": "algorithms/llm_client.llm_json(cache=True)",
                "model": "glm-5",
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "label_map": LABEL_MAP,
                "prompt_template": PROMPT,
                "evidence_note": (
                    "image_caption全为空('[图片] '); 图信息从mineru_standard恢复: "
                    "图题(_content_list.json)+图所在节(heading)+正文引文/邻文(markdown); "
                    "table_text去HTML标签后取前200字"),
            },
            "label_dist": dict(dist),
            "scene_stats": {
                s: dict(Counter(r["label"] for r in ordered if r["scene"] == s))
                for s in sorted({r["scene"] for r in ordered})},
            "pairs": ordered,
        }
        OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(run_one, p): p for p in todo}
            n = 0
            for fut in as_completed(futs):
                k, rec = fut.result()
                results[k] = rec
                n += 1
                if n % 20 == 0:
                    flush()
                    rate = n / (time.time() - t0)
                    print(f"  [{n}/{len(todo)}] {time.time() - t0:.0f}s "
                          f"(~{rate:.2f}/s, 剩余~{(len(todo) - n) / max(rate, .01) / 60:.0f}min)")
    flush()

    ordered = [results[k] for k in [pair_key(p) for p in pairs] if k in results]
    dist = Counter(r["label"] for r in ordered)
    print(f"\n{'=' * 66}")
    print(f"裁决完成: {len(ordered)}条, 用时{(time.time() - t0) / 60:.1f}min(本次新增{len(todo)}条)")
    print(f"{'=' * 66}")
    print(f"  标签分布: {dict(dist)}")
    for s in sorted({r['scene'] for r in ordered}):
        c = Counter(r["label"] for r in ordered if r["scene"] == s)
        n = sum(c.values())
        print(f"    {s:26s}: n={n:3d} inconsistent={c['inconsistent']:3d} "
              f"consistent={c['consistent']:3d} unsure={c['unsure']:3d}")
    fails = [r for r in ordered if r["model"] == "none" or r["reason"].startswith(("parse_error", "llm_call"))]
    if fails:
        print(f"  [warn] 失败/解析异常 {len(fails)} 条(已标unsure)")
    print(f"\n  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
