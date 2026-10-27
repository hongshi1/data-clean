r"""LEGACY builder: reconstructs the v1 migration audit asset, not the current QA benchmark.

This script uses pre-reconstruction AEE/family semantics, does not preserve the
original question consistently, and must never overwrite the frozen v1 asset.
Run only with ``--legacy-candidate``; output is a separate candidate file.

历史来源映射:
  QA直转: A1(346, 三态重裁定) + A3(344, 真实负例) + B1(346, semi_real)
  QA配平: B3(247 refute+247配平support) + C1(316 refute+配平support)
  family反推: A/D/F-synth(answer=hyp, evidence=premise+锚点回查) + C-gold(280) + B/E(103直映)
  防泄漏: 29对train全等剔除 + dedup + 变异值位置断言
输出: data/gjb_438c/answer_evidence_evalset_v1.json
"""
from __future__ import annotations

import json
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(BASE / "tools"))
from eval_qa_e2e import build_indexes, clean_name, fig_elements, norm, parse_table_ucnames  # noqa: E402

SEED = 42


def normkey(s: str) -> str:
    return re.sub(r"[\s「」《》]", "", str(s))


def rows_all(chunk: dict) -> list[list[str]]:
    text = str(chunk.get("text", ""))
    html = text[text.find("<table>"):] if "<table>" in text else text
    parsed = []
    for r in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = re.findall(r"<t[dh]>(.*?)</t[dh]>", r, re.S)
        if cells:
            parsed.append([re.sub(r"<[^>]+>", "", c).strip() for c in cells])
    return parsed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--legacy-candidate", action="store_true",
                    help="explicitly run legacy reconstruction; never writes the frozen AEE file")
    ap.add_argument("--output", type=Path,
                    default=BASE / "data/gjb_438c/answer_evidence_evalset_v1.legacy_candidate.json")
    args = ap.parse_args()
    if not args.legacy_candidate:
        ap.error("legacy builder disabled for normal use; pass --legacy-candidate to write a separate candidate")
    qa_lines = [json.loads(ln) for ln in (BASE / "data/gjb_438c/easydataset/srs_alpaca.jsonl").read_text(encoding="utf-8").splitlines()]
    fam = json.loads((BASE / "data/gjb_438c/family_evalset_v1.json").read_text(encoding="utf-8"))["pairs"]
    train = [json.loads(ln) for ln in open(BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl", encoding="utf-8")]
    a1_e2e = json.loads((BASE / "data/gjb_438c/qa_e2e_a1.json").read_text(encoding="utf-8"))
    tbl, cap_only, txt, img = build_indexes()

    # 训练集泄漏键(规范化全等)
    train_keys = set()
    for x in train:
        ph = x.get("pair", x)
        train_keys.add((normkey(ph.get("premise", "")), normkey(ph.get("hypothesis", ""))))

    entries: list[dict] = []
    skipped = Counter()

    def add(answer: str, evs: list[dict], gold: str, combo: str,
            prov: str, conf: str, diffs: list | None = None,
            origin: str = "text") -> None:
        entries.append({
            "id": f"AEE-{len(entries) + 1:04d}",
            "answer": {"text": answer, "origin": origin},
            "evidence": [{"eid": f"E{i + 1}", "evidence_type": e["type"],
                          "anchor": e.get("anchor", {}), "claims": e["claims"],
                          "exhaustive": e.get("exhaustive")}
                         for i, e in enumerate(evs)],
            "gold": {"label": gold, "binary": None if gold == "not_in_evidence" else gold,
                     "confidence": conf,
                     "discrepancies": diffs or []},
            "modality_combo": combo, "provenance": prov})

    # ═══ 1. A1: 拆原子条目(表侧闭世界+图侧开世界) ═══
    a1_iter = iter(a1_e2e["results"])
    a1_qs = [d for d in qa_lines
             if "用例名称是否一致" in str(d.get("instruction", ""))
             and "假设" not in str(d.get("instruction", ""))
             and isinstance(d.get("input"), str) and d.get("input", "").strip().startswith("{")]
    for d, res in zip(a1_qs, a1_iter, strict=False):
        try:
            meta = eval(d["input"])  # noqa: S307
        except Exception:  # noqa: BLE001
            skipped["A1_input"] += 1
            continue
        doc = str(meta.get("doc", ""))
        m = re.search(r"「(.+?)」", str(d.get("instruction", "")))
        tchunk = tbl.get(f"{norm(str(meta.get('table_caption', '')))}@{norm(doc)}")
        analysis = img.get(f"{norm(str(meta.get('image_caption', '')))}@{norm(doc)}")
        if not tchunk or not analysis or not m:
            skipped["A1_证据"] += 1
            continue
        claim_x = m.group(1)
        uc_names, _ = parse_table_ucnames(tchunk)
        table_names = [clean_name(n) for n in uc_names if clean_name(n)]
        elems = fig_elements(analysis)
        # 原子条目1: 表侧(闭世界: 权威枚举)
        add(f"表格《{tchunk.get('table_caption', '')}》的用例名称包括「{claim_x}」。",
            [{"type": "table", "anchor": {"doc": doc, "caption": tchunk.get("table_caption")},
              "claims": [f"用例名称包括：{'、'.join(table_names[:10])}。"]}],
            "support" if res["in_table"] else "refute",
            "text-table", "qa_alpaca/A1-table", "real",
            [] if res["in_table"] else [{"type": "NAME_MISMATCH", "found": claim_x, "ev": "table"}],
            origin="table")
        # 原子条目2: 图侧(开世界: VLM提取有损)
        add(f"图《{str(meta.get('image_caption', ''))}》的用例名称包括「{claim_x}」。",
            [{"type": "figure", "anchor": {"doc": doc, "caption": str(meta.get("image_caption", ""))},
              "claims": [f"图中的用例包括：{'、'.join(elems[:10])}。"]}],
            "support" if res["in_fig"] else "not_in_evidence",
            "text-figure", "qa_alpaca/A1-figure", "real",
            [{"type": "EXTRACT_MISS", "found": claim_x, "ev": "figure"}] if not res["in_fig"] else [],
            origin="figure")

    # ═══ 2. A3: 表-正文(真实负例) ═══
    a3_qs = [d for d in qa_lines
             if "列出" in str(d.get("instruction", "")) and "正文" in str(d.get("instruction", ""))]
    for d in a3_qs:
        m_cap = re.search(r"「(.+?)」", str(d.get("instruction", "")))
        if not m_cap:
            skipped["A3_cap"] += 1
            continue
        chunks = cap_only.get(norm(m_cap.group(1)), [])
        if len(chunks) != 1:
            skipped["A3_表定位"] += 1
            continue
        tchunk = chunks[0]
        doc, section = str(tchunk.get("doc", "")), str(tchunk.get("section", ""))
        uc_names, _ = parse_table_ucnames(tchunk)
        funcs = [clean_name(n) for n in uc_names if clean_name(n)]
        if len(funcs) < 2:
            skipped["A3_表解析"] += 1
            continue
        texts = []
        for key, cl in txt.items():
            if key == f"{norm(doc)}@{section}":
                texts.extend(str(c.get("text", "")) for c in cl)
        corpus = "".join(texts)
        m_out = re.search(r"缺失[：:](.+)", str(d.get("output", "")))
        gold_missing = [x.strip() for x in re.split(r"[，,、]", m_out.group(1)) if x.strip()] if m_out else []
        if not corpus:
            gold = "not_in_evidence"
            evs = [{"type": "text", "anchor": {"doc": doc, "section": section}, "claims": []}]
        else:
            gold = "support" if not gold_missing else "refute"
            segs = [f"正文记载：{corpus[i:i + 800]}" for i in range(0, len(corpus), 800)]
            evs = [{"type": "text", "anchor": {"doc": doc, "section": section},
                    "claims": segs, "exhaustive": True}]
        # 证据=正文only(声明的"正文提及"针对正文验证; 表格是声明来源不入证据池)
        answer = f"正文提及的功能包括：{'、'.join(funcs[:12])}。"
        diffs = [{"type": "FUNC_MISSING", "found": g} for g in gold_missing[:8]] if gold == "refute" else []
        # 评测维度按证据来源记录；表格是 answer 的来源，不是第二个比较端。
        add(answer, evs, gold, "text", "qa_alpaca/A3", "real", diffs, origin="table")

    # ═══ 3. B1: 表头合规(semi_real) ═══
    b1_qs = [d for d in qa_lines if "表头字段" in str(d.get("instruction", ""))]
    for d in b1_qs:
        ins = str(d.get("instruction", ""))
        m_cap = re.search(r"「(.+?)」", ins)
        if not m_cap:
            continue
        chunks = cap_only.get(norm(m_cap.group(1)), [])
        if len(chunks) != 1:
            skipped["B1_表定位"] += 1
            continue
        tchunk = chunks[0]
        rows = rows_all(tchunk)
        if not rows:
            skipped["B1_解析"] += 1
            continue
        header = rows[0]
        doc = str(tchunk.get("doc", ""))
        answer = f"表格《{m_cap.group(1)}》的表头字段包括：{'、'.join(header[:8])}，符合GJB 438C规范。"
        evs = [{"type": "table", "anchor": {"doc": doc, "caption": m_cap.group(1)},
                "claims": [f"表头字段为：{'、'.join(header)}。"]}]
        add(answer, evs, "support", "text-table", "qa_alpaca/B1", "semi_real", origin="table")

    # ═══ 4. B3: 重复ID检测(实际形态) ═══
    b3_qs = [d for d in qa_lines if "标识符" in str(d.get("instruction", "")) and "重复" in str(d.get("instruction", ""))]
    n_bal = 0
    for d in b3_qs:
        ins = str(d.get("instruction", ""))
        m_cap = re.search(r"「(.+?)」", ins)
        if not m_cap:
            continue
        chunks = cap_only.get(norm(m_cap.group(1)), [])
        if len(chunks) != 1:
            skipped["B3_表定位"] += 1
            continue
        tchunk = chunks[0]
        rows = rows_all(tchunk)
        id_col = None
        if rows:
            for i, h in enumerate(rows[0]):
                if "标识" in h or "ID" in h.upper():
                    id_col = i
                    break
        real_ids = [r[id_col] for r in rows[1:] if len(r) > id_col and r[id_col]] if id_col is not None else []
        if not real_ids:
            skipped["B3_无ID列"] += 1
            continue
        dup = [k for k, c in Counter(real_ids).items() if c > 1]
        answer = f"表格《{m_cap.group(1)}》中的需求标识符各不重复。"
        evs = [{"type": "table", "anchor": {"doc": str(tchunk.get("doc", "")), "caption": m_cap.group(1)},
                "claims": [f"需求标识符包括：{'、'.join(real_ids[:8])}。"]}]
        gold = "refute" if dup else "support"
        diffs = [{"type": "GJB-DUP-ID", "found": dup[0], "count": Counter(real_ids)[dup[0]]}] if dup else []
        add(answer, evs, gold, "text-table", "qa_alpaca/B3", "semi_real", diffs, origin="table")
        # 配平(与QA断言一致的方向): QA说存在重复而真实表也有→一致; 真实无重复→QA的"存在重复"=合成
        n_bal += 1

    # ═══ 5. C1: 悬挂E refute + 真实E配平 ═══
    c1_qs = [d for d in qa_lines if "异常流" in str(d.get("instruction", "")) and "未定义" in str(d.get("instruction", ""))]
    # 全文档已定义的E号(真实异常流): 从正文与表格文本收集
    defined_es = set()
    for key, cl in txt.items():
        for c in cl:
            defined_es.update(re.findall(r"异常流\s*(E\d+)", str(c.get("text", ""))))
    n_c1bal = 0
    for d in c1_qs:
        try:
            meta = eval(str(d.get("input", "")))  # noqa: S307
        except Exception:  # noqa: BLE001
            continue
        doc = str(meta.get("doc", ""))
        tchunk = tbl.get(f"{norm(str(meta.get('table_caption', '')))}@{norm(doc)}")
        if not tchunk:
            skipped["C1_表"] += 1
            continue
        m_x = re.search(r"中(.+?)的用例描述", str(d.get("instruction", "")))
        uc = m_x.group(1) if m_x else "该用例"
        # answer=可分解的枚举声明(引用的异常流∈文档定义集)
        answer = f"文档中定义的异常流包括：E9。"
        evs = [{"type": "text", "anchor": {"doc": doc},
                "claims": [f"文档定义的异常流包括：{'、'.join(sorted(defined_es)[:15])}。"],
                "exhaustive": True}]
        add(answer, evs, "refute", "text-text", "qa_alpaca/C1", "semi_real",
            [{"type": "DANGLING_REF", "found": "E9"}], origin="text")
        # 配平: 引用真实已定义E号
        if defined_es and n_c1bal < 150:
            e_real = sorted(defined_es)[n_c1bal % len(defined_es)]
            add(f"文档中定义的异常流包括：{e_real}。",
                evs, "support", "text-text", "qa_alpaca/C1-balanced", "semi_real", origin="text")
            n_c1bal += 1

    # ═══ 6. family反推 ═══
    for x in fam:
        prem, hyp = x["premise"], x["hypothesis"]
        # family C 的 premise/hypothesis 本身就是表格↔图差异对。
        # 它们没有可独立验证 hypothesis 的 SRS证据，不能伪装成 answer-evidence 样本。
        # 保留在 family_evalset_v1，待从真实图内容重建为 figure evidence 后再入本集。
        if x["family"] == "C":
            skipped["family_C_cross_modal_quarantine"] += 1
            continue
        # 泄漏检查(29对)
        if (normkey(prem), normkey(hyp)) in train_keys:
            skipped["family_train泄漏"] += 1
            continue
        fam_f, prov = x["family"], x.get("provenance", "")
        origin = "figure" if fam_f == "C" else "text"
        combo = {"A": "text-text", "B": "text-text", "C": "text-table", "D": "text-text",
                 "E": "text-text", "F": "text-text"}[fam_f]
        if fam_f == "C":
            combo = "text-table+figure" if "图" in hyp else "text-table"
        gold = {"consistent": "support", "inconsistent": "refute",
                "not_in_evidence": "not_in_evidence"}[x["label"]]
        ev_type = "table" if ("表" in prem and "图" not in prem) else ("figure" if "图" in prem else "text")
        anchor = {}
        m_doc = re.search(r"《(.+?)》", prem) or re.search(r"文档(.+?)的", prem)
        if m_doc:
            anchor["doc"] = m_doc.group(1)
        m_sec = re.search(r"第([\d.]+)节", prem)
        if m_sec:
            anchor["section"] = m_sec.group(1)
        m_tab = re.search(r"表\d+", prem)
        if m_tab:
            anchor["caption"] = m_tab.group(0)
        evs = [{"type": ev_type, "anchor": anchor, "claims": [prem]}]
        conf = "real" if prov == "gold_frozen" else "synth"
        if prov in ("gjb_bench",):
            conf = "semi_real"
        add(hyp, evs, gold, combo, f"family/{prov}", conf, origin=origin)

    # ═══ 防泄漏终检 ═══
    # dedup(answer+evidence首claim)
    seen = set()
    deduped = []
    for e in entries:
        key = (normkey(e["answer"]["text"]),
               normkey(e["evidence"][0]["claims"][0] if e["evidence"][0]["claims"] else ""))
        if key in seen:
            skipped["dedup"] += 1
            continue
        seen.add(key)
        deduped.append(e)
    entries = deduped

    # 统计
    labels = Counter(e["gold"]["label"] for e in entries)
    combos = Counter(e["modality_combo"] for e in entries)
    provs = Counter(e["provenance"].split("/")[0] for e in entries)
    confs = Counter(e["gold"]["confidence"] for e in entries)
    print(f"answer_evidence_evalset_v1: {len(entries)}条")
    print(f"三态: {dict(labels)}")
    print(f"模态组合: {dict(sorted(combos.items(), key=lambda kv: -kv[1]))}")
    print(f"来源: {dict(sorted(provs.items(), key=lambda kv: -kv[1]))}")
    print(f"置信: {dict(confs)}")
    print(f"跳过: {dict(skipped)}")

    out = {"meta": {"version": "aee_v1", "date": "2026-10-20", "total": len(entries),
                    "labels": dict(labels), "combos": dict(combos),
                    "设计": "answer vs 文本化证据, 三态gold(support/refute/NIE), 闭/开世界",
                    "防泄漏": "29对train剔除+dedup+配平改造"},
           "entries": entries}
    out_path = args.output.resolve()
    frozen_path = BASE / "data/gjb_438c/answer_evidence_evalset_v1.json"
    if out_path == frozen_path.resolve():
        raise ValueError("refusing to overwrite the frozen migration snapshot")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存 → {out_path}")


if __name__ == "__main__":
    main()
