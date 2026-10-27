r"""MMQA Suite-S主评测: 40项注入(声明对形态)上的NLI分项成绩单.

数据(三源):
  1. eval_injected_v3.json负例158条(语料证据驱动的注入, 32项)
  2. srs_qa_v3/eval_set.json正例50条(真实多模态一致对 — 位置A文本
     vs 位置B图/表的真实同名occurrence, 非LLM编造)
  3. 数值等效正例族(单位换算: 位置A"0.2秒" vs 位置B"200ms" —
     非平凡防捷径正例: 表面不同但语义等价, 期望判非矛盾)

正例分两族报告:
  - 真实一致正例(多模态同名): 期望非矛盾
  - 等效正例(单位换算): 期望非矛盾 — 若误报矛盾=表面捷径实锤

用法: python tools/mmqa_eval_suites.py [--model mdeberta]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency_check.nli_local import NliLocal  # noqa: E402
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/eval_injected_v3.json"
EVALSET_V2 = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"

# 40项 → 通道(NLI能力边界, 与mmqa/mutation.py一致)
CHANNEL_MAP: dict[str, str] = {
    "TERM-01": "lexical", "TERM-02": "lexical", "TERM-04": "lexical",
    "TERM-05": "lexical", "TERM-07": "lexical", "TERM-08": "lexical",
    "TERM-03": "nli-strong", "TERM-06": "nli-strong",
    **{f"PARAM-{i:02d}": "nli-strong" for i in range(1, 11)},
    "LOGIC-03": "nli-weak", "LOGIC-04": "nli-weak", "LOGIC-05": "nli-strong",
    **{f"LOGIC-{i:02d}": "llm" for i in (1, 2, 6, 7, 8, 9, 10, 11)},
    **{f"GJB-{i:02d}": "syntax" for i in range(1, 12)},
}

UNSUPPORTED = ["PARAM-03", "PARAM-04", "PARAM-08", "PARAM-09", "PARAM-10",
               "LOGIC-06", "LOGIC-07", "GJB-11"]  # 语料证据: grep全文0次/列分离


def render_claim(inj: dict[str, Any]) -> tuple[str, str] | None:
    """注入记录 → NLI声明对(位置A vs 位置B陈述).

    枚举类(TERM-03/LOGIC-05, content为list)加闭世界后缀 —
    实测: 无闭世界的"A,B,C vs A,B"判不出矛盾(集合重叠偏置).
    """
    occs = inj.get("occurrences", [])
    original, injected = inj.get("original"), inj.get("injected")
    if original is None or injected is None:
        return None

    def _as_text(v: Any) -> tuple[str, bool]:
        if isinstance(v, list):
            parts = []
            for x in v:
                if isinstance(x, dict):
                    parts.append(str(x.get("name", x)))
                else:
                    parts.append(str(x))
            return "、".join(parts), True
        if isinstance(v, dict):
            return str(v.get("name", v)), False
        return str(v), False

    original, is_enum = _as_text(original)
    injected, _ = _as_text(injected)
    sec_a = occs[0].get("section", "") if occs else ""
    sec_b = occs[1].get("section", "") if len(occs) > 1 else sec_a
    if is_enum:
        p = (f"文档{sec_a}章节规定，共{len(original.split('、'))}项："
             f"『{original}』，除此之外没有其他项。" if sec_a
             else f"文档规定，共{len(original.split('、'))}项："
                  f"『{original}』，除此之外没有其他项。")
        h = (f"文档{sec_b}章节规定，共{len(injected.split('、'))}项："
             f"『{injected}』，除此之外没有其他项。" if sec_b
             else f"文档另一处规定，共{len(injected.split('、'))}项："
                  f"『{injected}』，除此之外没有其他项。")
    else:
        p = (f"文档{sec_a}章节规定：『{original}』。" if sec_a
             else f"文档规定：『{original}』。")
        h = (f"文档{sec_b}章节规定：『{injected}』。" if sec_b
             else f"文档另一处规定：『{injected}』。")
    return p, h


def _load_real_positives() -> list[dict[str, Any]]:
    """eval_set.json的50条真实多模态一致正例 → 注入记录形态.

    真实数据: 同一实体在文本/图/表位置的同名occurrence(非LLM编造,
    非字面恒等渲染 — P来自位置A, H来自位置B的独立真实内容).
    """
    if not EVALSET_V2.exists():
        return []
    es = json.loads(EVALSET_V2.read_text(encoding="utf-8"))
    out = []
    for e in es.get("entries", []):
        if e.get("label") != "consistent":
            continue
        occs = (e.get("entity") or {}).get("occurrences", [])
        if len(occs) < 2:
            continue
        inj = e.get("injection") or {}
        out.append({
            "check_item": "POSITIVE-REAL",
            "label": "consistent",
            "original": inj.get("original", occs[0].get("content")),
            "injected": inj.get("injected", occs[1].get("content")),
            "occurrences": occs[:2],
            "doc": e.get("doc", ""),
        })
    return out


def _build_equiv_positives(seed: int = 42, n: int = 20
                           ) -> list[dict[str, Any]]:
    """数值等效正例族: 单位换算对(0.2秒 vs 200ms).

    非平凡防捷径正例 — 表面不同(数值/单位都不同)但语义等价,
    期望NLI判非矛盾; 误报矛盾=表面捷径实锤.
    数值取自真实params分布(time/period类), 确定性生成.
    """
    rng = random.Random(seed)
    CONV = [("秒", "ms", 1000.0), ("s", "ms", 1000.0), ("ms", "us", 1000.0),
            ("分钟", "秒", 60.0), ("GB", "MB", 1024.0), ("MB", "KB", 1024.0)]
    vals = [0.1, 0.2, 0.5, 1, 2, 3, 5, 10, 30, 60, 100, 200, 500, 1000]
    out = []
    for _ in range(n):
        val = rng.choice(vals)
        u1, u2, factor = rng.choice(CONV)
        a = f"{val:g}{u1}"
        b = f"{val * factor:g}{u2}"
        out.append({
            "check_item": "POSITIVE-EQUIV", "label": "consistent",
            "original": a, "injected": b,
            "occurrences": [
                {"location": "text", "section": "3.5", "content": a},
                {"location": "table", "section": "3.5", "content": b}],
            "doc": "(合成等效对)",
        })
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mdeberta",
                    choices=["mdeberta", "erlangshen"])
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))
    injections = data.get("injections", [])
    neg = [i for i in injections if i.get("label") == "inconsistent"]
    real_pos = _load_real_positives()
    equiv_pos = _build_equiv_positives()
    print(f"评测集: {len(neg)}负例({len(set(i['check_item'] for i in neg))}项, "
          f"语料证据驱动) + {len(real_pos)}真实一致正例(多模态) "
          f"+ {len(equiv_pos)}等效正例(单位换算, 非平凡防捷径)")

    all_items = list(injections) + real_pos + equiv_pos
    pairs: list[tuple[str, str]] = []
    meta: list[dict[str, Any]] = []
    for i, inj in enumerate(all_items):
        claim = render_claim(inj)
        if claim is None:
            continue
        pairs.append(claim)
        meta.append({"idx": i, "check_item": inj.get("check_item", ""),
                     "label": inj.get("label", ""),
                     "channel": CHANNEL_MAP.get(inj.get("check_item", ""), "?")})

    nli = NliLocal(args.model)
    mode = nli.ensure()
    if mode == "unavailable":
        print(f"SKIP: {nli.last_error}")
        return
    verdicts = nli.predict_bidirectional(pairs)
    print(f"NLI: {mode}, {len(pairs)}条声明对, {nli.stats['infer_ms']}ms\n")

    # 分项统计
    by_item: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "hit": 0})
    by_channel: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "hit": 0})
    pos_fp = {"POSITIVE": 0, "POSITIVE-REAL": 0, "POSITIVE-EQUIV": 0}
    pos_n = {"POSITIVE": 0, "POSITIVE-REAL": 0, "POSITIVE-EQUIV": 0}
    for m, v in zip(meta, verdicts):
        sym = v["sym_contra"]
        if m["label"] == "consistent":
            key = m["check_item"] if m["check_item"] in pos_fp else "POSITIVE"
            pos_fp[key] += sym
            pos_n[key] += 1
            continue
        d = by_item[m["check_item"]]
        d["n"] += 1
        d["hit"] += sym
        c = by_channel[m["channel"]]
        c["n"] += 1
        c["hit"] += sym

    print("══ 分通道(负例检出率; 正例误报率单独报) ══")
    print(f"{'通道':<12} {'n':>4} {'检出':>6} {'recall':>8}")
    for ch, d in sorted(by_channel.items()):
        r = d["hit"] / d["n"] if d["n"] else 0.0
        print(f"{ch:<12} {d['n']:>4} {d['hit']:>6} {r:>8.1%}")
    print("\n══ 正例误报率(分族) ══")
    fam_name = {"POSITIVE": "恒等(平凡)", "POSITIVE-REAL": "真实多模态一致",
                "POSITIVE-EQUIV": "单位等效(非平凡防捷径)"}
    for k in ("POSITIVE", "POSITIVE-REAL", "POSITIVE-EQUIV"):
        if pos_n[k]:
            r = pos_fp[k] / pos_n[k]
            note = "" if k == "POSITIVE" else (
                " ← 表面捷径实锤!" if r > 0.3 else " ← 通过")
            print(f"  {fam_name[k]}: {pos_fp[k]}/{pos_n[k]} = {r:.1%}{note}")

    print("\n══ 分check_item明细(负例) ══")
    for item, d in sorted(by_item.items()):
        r = d["hit"] / d["n"] if d["n"] else 0.0
        print(f"  {item}: {d['hit']}/{d['n']} ({r:.0%})")

    total_hit = sum(d["hit"] for d in by_item.values())
    total_n = sum(d["n"] for d in by_item.values())
    print(f"\n总体负例检出: {total_hit}/{total_n} ({total_hit/total_n:.1%})")

    run = open_run("mmqa_eval_suites", {"model": args.model})
    run.save_result({
        "n_claims": len(pairs),
        "by_item": {k: dict(v) for k, v in by_item.items()},
        "by_channel": {k: dict(v) for k, v in by_channel.items()},
        "positive_by_family": {"fp": pos_fp, "n": pos_n},
        "overall": {"hit": total_hit, "n": total_n},
        "unsupported_in_corpus": UNSUPPORTED,
        "nli_stats": dict(nli.stats)})
    print(f"result → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
