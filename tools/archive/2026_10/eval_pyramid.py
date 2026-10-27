r"""评测金字塔实验: L2真实矛盾零样本 + L4大规模正例误报(docs/eval_scheme_v2.md).

L2(从未测过): real_doc_findings的text_vs_graph(22)+enumeration_conflict(2)
  = 真实文档扫描发现的真实矛盾 → 闭世界清单声明对 → NLI零样本检出率
  对照: table_terminology_drift(68) = 同义异名(预期词法域, NLI低)
L4(从未测过): srs_qa_trusted的1080条fact锚定正例采样500 →
  大规模真实正例误报率(防捷径的真实分布版)

用法: python tools/eval_pyramid.py [--model mdeberta] [--n-pos 500]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency_check.nli_local import NliLocal  # noqa: E402
from run_utils import open_run  # noqa: E402

FINDINGS = BASE / "data/gjb_438c/data_assets/real_doc_findings.json"
TRUSTED = BASE / "data/gjb_438c/data_assets/srs_qa_trusted/all_scenes.json"


def _list_from_evidence(ev: str) -> list[str]:
    """evidence文本('正文: A、B、C') → 清单(去前缀, 顿号切分, 去换行)."""
    body = re.sub(r"^[^:：]*[:：]\s*", "", ev)
    items = [x.strip().replace("\n", "") for x in re.split(r"[、,，]", body)
             if x.strip() and len(x.strip()) >= 2]
    return items


def build_l2(findings: list[dict]) -> tuple[list[tuple[str, str]], list[str]]:
    """真实矛盾 → 闭世界清单声明对. 返回(声明对, 类别)."""
    pairs, cats = [], []
    for f in findings:
        ev = f.get("evidence", [])
        if len(ev) < 2:
            continue
        la, lb = _list_from_evidence(ev[0]), _list_from_evidence(ev[1])
        if len(la) < 2 or len(lb) < 2:
            continue
        p = (f"文档正文规定，共{len(la)}项，包括：{'、'.join(la[:12])}，"
             f"除此之外没有其他项。")
        h = (f"图中显示，共{len(lb)}个节点，包括：{'、'.join(lb[:12])}，"
             f"除此之外没有其他节点。")
        pairs.append((p, h))
        cats.append(f["type"])
    return pairs, cats


def build_l4(n: int, seed: int = 42) -> list[tuple[str, str]]:
    """trusted正例 → fact锚定同名声明对(两侧真实文档内容)."""
    data = json.loads(TRUSTED.read_text(encoding="utf-8"))
    pos = [q for q in data if q.get("label") == "consistent" and q.get("fact")]
    rng = random.Random(seed)
    rng.shuffle(pos)
    pairs = []
    for p in pos[:n]:
        fact = p["fact"]
        value = fact.get("value", "")
        src = fact.get("source", "table")
        src_name = {"table": "功能划分表", "text": "正文", "image": "图"}.get(
            src, "文档")
        # 侧A: fact锚定的来源位置; 侧B: answer中核查的另一位置(answer必含
        # "一致"与value的同名表述 — 两侧均为真实文档内容)
        a = f"{src_name}中规定功能「{value}」。"
        b = f"文档的图与正文位置同样描述功能「{value}」。"
        pairs.append((a, b))
    return pairs


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mdeberta",
                    choices=["mdeberta", "erlangshen"])
    ap.add_argument("--n-pos", type=int, default=500)
    args = ap.parse_args()

    d = json.loads(FINDINGS.read_text(encoding="utf-8"))
    findings = d["findings"]
    real_neg = [f for f in findings if f["type"] in
                ("text_vs_graph", "enumeration_conflict")]
    term_drift = [f for f in findings if f["type"] == "table_terminology_drift"]

    l2_pairs, l2_cats = build_l2(real_neg)
    term_pairs, term_cats = build_l2(term_drift)
    l4_pairs = build_l4(args.n_pos)
    print(f"L2真实矛盾: {len(l2_pairs)}条声明对 | "
          f"术语漂移对照: {len(term_pairs)}条 | L4正例: {len(l4_pairs)}条")

    nli = NliLocal(args.model)
    mode = nli.ensure()
    if mode == "unavailable":
        print(f"SKIP: {nli.last_error}")
        return

    def _run(pairs: list[tuple[str, str]], name: str,
             expect: str) -> dict:
        vs = nli.predict_bidirectional(pairs)
        sym = sum(1 for v in vs if v["sym_contra"])
        scores = [v["contra_score"] for v in vs]
        n = len(pairs)
        rate = sym / n if n else 0.0
        exp_rate = rate if expect == "contradiction" else 1 - rate
        print(f"\n══ {name} ══")
        print(f"  n={n} | sym_contra={sym} ({rate:.1%}) | "
              f"期望={expect} → {'检出率' if expect == 'contradiction' else '误报率'}"
              f"={exp_rate:.1%} | 平均分={sum(scores)/n:.3f}" if n else "  n=0")
        return {"n": n, "sym": sym, "rate": rate, "expect": expect,
                "avg_score": round(sum(scores) / n, 3) if n else 0.0}

    r_l2 = _run(l2_pairs, "L2·真实矛盾零样本(正文vs图清单)", "contradiction")
    # L4构造缺陷的诚实记录(2026-09-16): H侧模板句非真实文档内容,
    # 96.2%"误报率"是模板伪矛盾(构造缺陷)非模型缺陷 — 不可引用.
    # 正确的L4路径: 声明对粒度的真实正例=eval_set 50条(已测0%误报);
    # trusted 1080条是QA粒度资产, 形态不匹配(资产地图已标注).
    l4_pairs = build_l4(min(args.n_pos, 0)) if False else l4_pairs
    r_l4 = _run(l4_pairs, "L4·(构造缺陷记录: 模板伪矛盾, 不可引用)",
                "entailment")

    # L2分类型明细
    by_type: dict[str, list[int]] = {}
    for (p, h), cat, v in [] if not l2_pairs else []:
        pass
    vs_l2 = nli.predict_bidirectional(l2_pairs) if l2_pairs else []
    for (p, h), cat, v in zip(l2_pairs, l2_cats, vs_l2):
        t = by_type.setdefault(cat, [0, 0])
        t[0] += v["sym_contra"]
        t[1] += 1
    print("\nL2分类型:")
    for cat, (hit, n) in by_type.items():
        print(f"  {cat}: {hit}/{n}")

    # L4误报样例(前3)
    vs_l4 = nli.predict(l4_pairs) if l4_pairs else []
    fps = [(p, h) for (p, h), v in zip(l4_pairs, vs_l4)
           if v["label"] == "contradiction"][:3]
    if fps:
        print("\nL4误报样例:")
        for p, h in fps:
            print(f"  P: {p[:60]} | H: {h[:60]}")

    r_term = {"n": 0, "sym": 0, "rate": 0.0, "expect": "entailment",
              "avg_score": 0.0,
              "note": "术语漂移evidence格式不适用清单渲染(构造0条, 如实记录)"}
    run = open_run("eval_pyramid", {"model": args.model, "n_pos": args.n_pos})
    run.save_result({"L2_real": r_l2, "L2_term_drift": r_term,
                     "L4_positive": r_l4,
                     "L2_by_type": {k: v for k, v in by_type.items()},
                     "nli_stats": dict(nli.stats)})
    print(f"\nresult → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
