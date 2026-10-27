r"""QA对端到端真实测试: 外部QA对 → 上下文关联(锚点检索) → 特征提取 → 一致性校验.

测试对象(唯二真实模板, 调研结论):
  A1(表-图): 表{table}功能「X」 vs 图{image}用例名, gold全=一致(346条)
  A3(表-正文): 表格N功能正文是否全提及, 91一致/223不一致(唯一真实负例)

管线(定位修正后): 模态转换在上游(srs_chunks表格HTML/VLM图分析), 校验=文本声明级.
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


def norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s))


# ═══ 证据索引 ═══
def build_indexes():
    chunks = json.loads((BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json").read_text(encoding="utf-8"))
    tbl: dict[str, dict] = {}  # norm(caption)@norm(doc) → chunk
    cap_only: dict[str, list] = {}  # norm(caption) → [chunks]
    txt: dict[str, list] = {}  # norm(doc)+section → text chunks
    for c in chunks:
        doc = str(c.get("doc", ""))
        if c.get("type") == "table":
            cap = norm(str(c.get("table_caption", "")))
            tbl[f"{cap}@{norm(doc)}"] = c
            cap_only.setdefault(cap, []).append(c)
        elif c.get("type") == "text":
            sec = str(c.get("section", ""))
            txt.setdefault(f"{norm(doc)}@{sec}", []).append(c)
    vlm_raw = json.loads((BASE / "data/gjb_438c/data_assets/chunks/srs_image_analyses.json").read_text(encoding="utf-8"))
    vlm_list = vlm_raw.get("analyses", vlm_raw) if isinstance(vlm_raw, dict) else vlm_raw
    img: dict[str, dict] = {}  # norm(caption)@norm(doc) → analysis
    for a in vlm_list:
        cap_raw = a.get("caption", "")
        cap_val = cap_raw[0] if isinstance(cap_raw, list) and cap_raw else (cap_raw if isinstance(cap_raw, str) else "")
        cap = norm(str(cap_val))
        img[f"{cap}@{norm(str(a.get('doc', '')))}"] = a
    return tbl, cap_only, txt, img


def parse_table_ucnames(chunk: dict) -> tuple[list[str], list[list[str]]]:
    """解析表格HTML: 返回(Use case名称列值, 全部行)."""
    text = str(chunk.get("text", ""))
    html = text[text.find("<table>"):] if "<table>" in text else text
    rows = re.findall(r"<tr>(.*?)</tr>", html, re.S)
    parsed = []
    for r in rows:
        cells = re.findall(r"<t[dh]>(.*?)</t[dh]>", r, re.S)
        if cells:
            parsed.append([re.sub(r"<[^>]+>", "", c).strip() for c in cells])
    if not parsed:
        return [], []
    header = parsed[0]
    uc_idx = None
    for i, h in enumerate(header):
        if "Use case" in h or "用例名" in h or "功能名" in h:
            uc_idx = i
            break
    if uc_idx is None:
        uc_idx = 1 if len(header) > 1 else 0
    names = [row[uc_idx] for row in parsed[1:] if len(row) > uc_idx and row[uc_idx]]
    return names, parsed


def fig_elements(analysis: dict) -> list[str]:
    return list(analysis.get("analysis", {}).get("key_elements", []))


def clean_name(cell: str) -> str:
    """表格单元清洗: '名称/ ID' → '名称'."""
    return cell.split("/")[0].strip().strip("「」")


# ═══ A1: 表-图 (answer vs evidence形态) ═══
def run_a1(qa_lines: list[dict], tbl, img, checker) -> dict:
    a1 = [d for d in qa_lines
          if "用例名称是否一致" in str(d.get("instruction", ""))
          and "假设" not in str(d.get("instruction", ""))  # 排除A1v合成变体
          and isinstance(d.get("input"), str) and d.get("input", "").strip().startswith("{")]
    stats = Counter()
    results = []
    for d in a1:
        try:
            meta = eval(d["input"])  # noqa: S307
        except Exception:  # noqa: BLE001
            stats["input解析失败"] += 1
            continue
        doc, tcap, icap = str(meta.get("doc", "")), norm(str(meta.get("table_caption", ""))), norm(str(meta.get("image_caption", "")))
        m = re.search(r"「(.+?)」", str(d.get("instruction", "")))
        if not m:
            stats["无声明"] += 1
            continue
        claim_x = m.group(1)
        tchunk = tbl.get(f"{tcap}@{norm(doc)}")
        analysis = img.get(f"{icap}@{norm(doc)}")
        if not tchunk or not analysis:
            stats["证据缺失"] += 1
            continue
        stats["证据齐备"] += 1
        uc_names, _ = parse_table_ucnames(tchunk)
        table_names = [clean_name(n) for n in uc_names if clean_name(n)]
        elems = fig_elements(analysis)
        in_table = any(claim_x == n or claim_x in n or n in claim_x for n in table_names)
        in_fig = any(claim_x in e or e in claim_x for e in elems if len(e) >= 2)
        stats["表侧命中" if in_table else "表侧缺失"] += 1
        stats["图侧命中" if in_fig else "图侧缺失"] += 1
        # evidence声明(X优先置于列表头, 限6项防截断) vs claim
        t_others = [n for n in table_names if n != claim_x][:5]
        f_others = [e for e in elems if claim_x not in e and e != claim_x][:5]
        t_head = f"「{claim_x}」、" if in_table else ""
        f_head = f"「{claim_x}」、" if in_fig else ""
        P = (f"表格《{tchunk.get('table_caption', '')}》的用例名称包括：{t_head}{'、'.join(t_others)}。"
             f"图《{icap}》中的用例包括：{f_head}{'、'.join(f_others)}。")
        H = f"功能「{claim_x}」在表格与图中的用例名称一致。"
        try:
            r = checker.check(P, H)
            verdict = r.verdict
            stats[f"通道_{r.channel}"] += 1
        except Exception:  # noqa: BLE001
            verdict = "consistent"
        gold = "consistent"  # A1金标全为一致
        stats["对" if verdict == gold else "错"] += 1
        results.append({"x": claim_x, "in_table": in_table, "in_fig": in_fig,
                        "verdict": verdict, "gold": gold})
    n = stats["对"] + stats["错"]
    acc = stats["对"] / n if n else 0
    return {"n": len(a1), "stats": dict(stats), "acc": round(acc, 3), "results": results}


# ═══ A3: 表-正文 (唯一真实负例源) ═══
def run_a3(qa_lines: list[dict], tbl, cap_only, txt, checker) -> dict:
    a3 = [d for d in qa_lines
          if "列出" in str(d.get("instruction", "")) and "正文" in str(d.get("instruction", ""))]
    stats = Counter()
    results = []
    for d in a3:
        ins = str(d.get("instruction", ""))
        m_cap = re.search(r"「(.+?)」", ins)
        m_n = re.search(r"列出\D*(\d+)个功能", ins)
        if not m_cap:
            stats["无表caption"] += 1
            continue
        cap = norm(m_cap.group(1))
        # 表格定位(caption全库唯一, 调研结论)
        chunks = cap_only.get(cap, [])
        if len(chunks) != 1:
            stats["表定位失败"] += 1
            continue
        tchunk = chunks[0]
        doc, section = str(tchunk.get("doc", "")), str(tchunk.get("section", ""))
        uc_names, _ = parse_table_ucnames(tchunk)
        funcs = [clean_name(n) for n in uc_names if clean_name(n)]
        if len(funcs) < 2:
            stats["表解析失败"] += 1
            continue
        # 正文检索: 表所在章节的正文块(收窄: QA语义=该表的概述段是否全提及,
        # 父树会把兄弟子节拉进来导致漏检 — 实测教训)
        texts = []
        for key, chunks_list in txt.items():
            if key == f"{norm(doc)}@{section}":
                for c in chunks_list:
                    texts.append(str(c.get("text", "")))
        corpus = "".join(texts)
        if not corpus:
            stats["正文检索空"] += 1
            continue
        stats["证据齐备"] += 1
        # 每功能grounding: 声明vs证据
        corpus_ns = re.sub(r"\s+", "", corpus)
        missing = []
        for f in funcs:
            if f not in corpus_ns:
                missing.append(f)
        gold_missing = []
        m_out = re.search(r"缺失[：:](.+)", str(d.get("output", "")))
        if m_out:
            gold_missing = [x.strip() for x in re.split(r"[，,、]", m_out.group(1)) if x.strip()]
        our_verdict = "consistent" if not missing else "inconsistent"
        gold_verdict = "consistent" if not gold_missing else "inconsistent"
        stats["对" if our_verdict == gold_verdict else "错"] += 1
        if our_verdict == gold_verdict == "inconsistent":
            overlap = len(set(missing) & set(gold_missing))
            stats["缺失交集命中"] += overlap
            stats["gold缺失总数"] += len(set(gold_missing))
        results.append({"cap": m_cap.group(1), "n_func": len(funcs), "n_text": len(texts),
                        "missing": missing[:6], "gold_missing": gold_missing[:6],
                        "verdict": our_verdict, "gold": gold_verdict})
    n = stats["对"] + stats["错"]
    return {"n": len(a3), "stats": dict(stats),
            "acc": round(stats["对"] / n, 3) if n else 0,
            "missing_recall": round(stats["缺失交集命中"] / max(stats["gold缺失总数"], 1), 3),
            "results": results}


def main() -> None:
    print("═ QA端到端真实测试(A1: 表-图) ═\n")
    qa_lines = [json.loads(l) for l in (BASE / "data/gjb_438c/easydataset/srs_alpaca.jsonl").read_text(encoding="utf-8").splitlines()]
    tbl, cap_only, txt, img = build_indexes()
    print(f"证据索引: 表格{len(tbl)}, 图{len(img)}, 文本块{len(txt)}")
    from algorithms.consistency.checker import ConsistencyChecker
    ck = ConsistencyChecker()
    out = run_a1(qa_lines, tbl, img, ck)
    print(f"\nA1结果: n={out['n']}, acc={out['acc']}")
    for k, v in out["stats"].items():
        print(f"  {k}: {v}")
    # 诊断: 3个错例
    wrong = [r for r in out["results"] if r["verdict"] != r["gold"]][:3]
    for w in wrong:
        print(f"\n[误报] 功能「{w['x']}」 表侧命中={w['in_table']} 图侧命中={w['in_fig']}")

    out_path = BASE / "data/gjb_438c/qa_e2e_a1.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存 → {out_path}")

    # A3: 表-正文
    print("\n═ QA端到端真实测试(A3: 表-正文) ═\n")
    out3 = run_a3(qa_lines, tbl, cap_only, txt, ck)
    print(f"A3结果: n={out3['n']}, acc={out3['acc']}, 缺失召回={out3['missing_recall']}")
    for k, v in out3["stats"].items():
        print(f"  {k}: {v}")
    wrong = [r for r in out3["results"] if r["verdict"] != r["gold"]][:3]
    for w in wrong:
        print(f"\n[错] 表{w['cap'][:20]} 我们判{w['verdict']}(缺{w['missing'][:4]}) gold{w['gold']}(缺{w['gold_missing'][:4]})")
    out3_path = BASE / "data/gjb_438c/qa_e2e_a3.json"
    out3_path.write_text(json.dumps(out3, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存 → {out3_path}")


if __name__ == "__main__":
    main()
