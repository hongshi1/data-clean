r"""verify()新接口端到端复验: A1(表-图)/A3(表-正文) 对比旧check()结果.

A1: answer="功能「X」在表格与图中的用例名称一致" vs 表声明集+图声明集(双闭世界)
A3: answer="表格列出的功能在正文中全部提及" vs 该节正文(闭世界)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(BASE / "tools"))
from eval_qa_e2e import build_indexes, clean_name, fig_elements, norm, parse_table_ucnames  # noqa: E402


def main() -> None:
    from algorithms.consistency.verify import Evidence, Verifier

    v = Verifier()
    qa_lines = [json.loads(l) for l in (BASE / "data/gjb_438c/easydataset/srs_alpaca.jsonl").read_text(encoding="utf-8").splitlines()]
    tbl, cap_only, txt, img = build_indexes()

    # ═══ A1 ═══
    a1 = [d for d in qa_lines
          if "用例名称是否一致" in str(d.get("instruction", ""))
          and "假设" not in str(d.get("instruction", ""))
          and isinstance(d.get("input"), str) and d.get("input", "").strip().startswith("{")]
    stats = Counter()
    for d in a1:
        try:
            meta = eval(d["input"])  # noqa: S307
        except Exception:  # noqa: BLE001
            continue
        doc = str(meta.get("doc", ""))
        tchunk = tbl.get(f"{norm(str(meta.get('table_caption', '')))}@{norm(doc)}")
        analysis = img.get(f"{norm(str(meta.get('image_caption', '')))}@{norm(doc)}")
        m = re.search(r"「(.+?)」", str(d.get("instruction", "")))
        if not tchunk or not analysis or not m:
            continue
        claim_x = m.group(1)
        uc_names, _ = parse_table_ucnames(tchunk)
        table_names = [clean_name(n) for n in uc_names if clean_name(n)]
        elems = fig_elements(analysis)
        answer = f"功能「{claim_x}」在表格与图中的用例名称一致。"
        evidences = [
            Evidence(type="table", claims=[f"用例名称包括：{'、'.join(table_names[:8])}。"],
                     source_ref=f"{doc[:2]}@{tchunk.get('table_caption', '')}"),
            Evidence(type="figure", claims=[f"图中的用例包括：{'、'.join(elems[:8])}。"],
                     source_ref=f"{doc[:2]}@图"),
        ]
        r = v.verify_multi(answer, evidences)
        # A1 gold=一致→support; 三态映射: support=对, refute/nie=错(二分类视角)
        ok = r.verdict == "support"
        stats["对" if ok else "错"] += 1
        stats[f"verdict_{r.verdict}"] += 1
    n = stats["对"] + stats["错"]
    print(f"A1(verify接口): n={n}, acc={stats['对'] / max(n, 1):.3f} (旧check=0.873)")
    for k, val in stats.items():
        print(f"  {k}: {val}")

    # ═══ A3 ═══
    a3 = [d for d in qa_lines
          if "列出" in str(d.get("instruction", "")) and "正文" in str(d.get("instruction", ""))]
    stats3 = Counter()
    for d in a3:
        m_cap = re.search(r"「(.+?)」", str(d.get("instruction", "")))
        if not m_cap:
            continue
        chunks = cap_only.get(norm(m_cap.group(1)), [])
        if len(chunks) != 1:
            continue
        tchunk = chunks[0]
        doc, section = norm(tchunk.get("doc", "")), str(tchunk.get("section", ""))
        uc_names, _ = parse_table_ucnames(tchunk)
        funcs = [clean_name(n) for n in uc_names if clean_name(n)]
        if len(funcs) < 2:
            continue
        texts = []
        for key, cl in txt.items():
            if key == f"{doc}@{section}":
                texts.extend(str(c.get("text", "")) for c in cl)
        corpus = "".join(texts)
        if not corpus:
            continue
        m_out = re.search(r"缺失[：:](.+)", str(d.get("output", "")))
        gold_missing = [x.strip() for x in re.split(r"[，,、]", m_out.group(1)) if x.strip()] if m_out else []
        gold_v = "support" if not gold_missing else "refute"
        answer = f"表格《{m_cap.group(1)}》列出的功能包括：{'、'.join(funcs[:12])}，在正文中全部提及。"
        # 完整正文分段传入(不截断, 否则枚举grounding误判缺失)
        seg_claims = [f"正文记载：{corpus[i:i + 800]}" for i in range(0, len(corpus), 800)]
        evidence = Evidence(type="text", claims=seg_claims,
                            source_ref=f"{doc[:2]}@{section}", exhaustive=True)
        r = v.verify(answer, evidence)
        stats3["对" if r.verdict == gold_v else "错"] += 1
        stats3[f"pred_{r.verdict}"] += 1
        stats3[f"gold_{gold_v}"] += 1
    n3 = stats3["对"] + stats3["错"]
    print(f"\nA3(verify接口): n={n3}, acc={stats3['对'] / max(n3, 1):.3f} (旧check=0.970)")
    for k, val in stats3.items():
        print(f"  {k}: {val}")


if __name__ == "__main__":
    main()
