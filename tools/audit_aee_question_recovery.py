"""AEE v1 question恢复审计: 确定性重放构建器, 逐条回溯原始question.

方法: 按build_answer_evidence_evalset.py完全相同的分支顺序/跳过条件/dedup
逻辑重放(不写AEE), 记录每条AEE条目对应的原始QA来源:
  - qa_alpaca/*: srs_alpaca.jsonl的instruction(原始question)+input+output
  - family/*:    无源question(来自family_evalset_v1的premise/hypothesis)

验证: 重放序列与实际AEE文件逐条比对answer文本+证据首claim, 全等才输出。
产出: data/gjb_438c/aee_question_recovery.json (审计资产, 不改AEE, 不判gold)
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

from eval_qa_e2e import build_indexes, clean_name, fig_elements, norm, parse_table_ucnames  # noqa: E402

AEE_PATH = BASE / "data/gjb_438c/answer_evidence_evalset_v1.json"
OUT_PATH = BASE / "data/gjb_438c/aee_question_recovery.json"


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


def reconstruct_question(instruction: str, meta: dict | None) -> str:
    """A1/C1的instruction含{table}/{image}占位符, 用input dict的caption回填."""
    q = instruction
    if isinstance(meta, dict):
        if "{table}" in q:
            q = q.replace("{table}", str(meta.get("table_caption", "{table}")))
        if "{image}" in q:
            q = q.replace("{image}", str(meta.get("image_caption", "{image}")))
    return q


def main() -> None:
    qa_lines = [json.loads(ln) for ln in
                (BASE / "data/gjb_438c/easydataset/srs_alpaca.jsonl")
                .read_text(encoding="utf-8").splitlines()]
    fam = json.loads((BASE / "data/gjb_438c/family_evalset_v1.json")
                     .read_text(encoding="utf-8"))["pairs"]
    train = [json.loads(ln) for ln in
             (BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl")
             .read_text(encoding="utf-8").splitlines()]
    a1_e2e = json.loads((BASE / "data/gjb_438c/qa_e2e_a1.json")
                        .read_text(encoding="utf-8"))
    tbl, cap_only, txt, img = build_indexes()

    train_keys = set()
    for x in train:
        ph = x.get("pair", x)
        train_keys.add((normkey(ph.get("premise", "")),
                        normkey(ph.get("hypothesis", ""))))

    # 重放记录: (answer, first_claim, provenance, question, input, output, meta)
    recs: list[dict] = []

    def rec(answer: str, first_claim: str, prov: str,
            question: str | None, qa_input: str | None, output: str | None,
            meta: dict | None) -> None:
        recs.append({"answer": answer, "first_claim": first_claim, "prov": prov,
                     "question": question, "input": qa_input, "output": output,
                     "meta": meta})

    # ═══ A1 ═══
    a1_iter = iter(a1_e2e["results"])
    a1_qs = [d for d in qa_lines
             if "用例名称是否一致" in str(d.get("instruction", ""))
             and "假设" not in str(d.get("instruction", ""))
             and isinstance(d.get("input"), str)
             and d.get("input", "").strip().startswith("{")]
    for d, res in zip(a1_qs, a1_iter, strict=False):
        try:
            meta = ast.literal_eval(d["input"])
        except (ValueError, SyntaxError):
            continue
        doc = str(meta.get("doc", ""))
        m = re.search(r"「(.+?)」", str(d.get("instruction", "")))
        tchunk = tbl.get(f"{norm(str(meta.get('table_caption', '')))}@{norm(doc)}")
        analysis = img.get(f"{norm(str(meta.get('image_caption', '')))}@{norm(doc)}")
        if not tchunk or not analysis or not m:
            continue
        claim_x = m.group(1)
        uc_names, _ = parse_table_ucnames(tchunk)
        table_names = [clean_name(n) for n in uc_names if clean_name(n)]
        elems = fig_elements(analysis)
        rec(f"表格《{tchunk.get('table_caption', '')}》的用例名称包括「{claim_x}」。",
            f"用例名称包括：{'、'.join(table_names[:10])}。",
            "qa_alpaca/A1-table", d["instruction"], d["input"], d["output"], meta)
        rec(f"图《{str(meta.get('image_caption', ''))}》的用例名称包括「{claim_x}」。",
            f"图中的用例包括：{'、'.join(elems[:10])}。",
            "qa_alpaca/A1-figure", d["instruction"], d["input"], d["output"], meta)

    # ═══ A3 ═══
    a3_qs = [d for d in qa_lines
             if "列出" in str(d.get("instruction", ""))
             and "正文" in str(d.get("instruction", ""))]
    for d in a3_qs:
        m_cap = re.search(r"「(.+?)」", str(d.get("instruction", "")))
        if not m_cap:
            continue
        chunks = cap_only.get(norm(m_cap.group(1)), [])
        if len(chunks) != 1:
            continue
        tchunk = chunks[0]
        doc, section = str(tchunk.get("doc", "")), str(tchunk.get("section", ""))
        uc_names, _ = parse_table_ucnames(tchunk)
        funcs = [clean_name(n) for n in uc_names if clean_name(n)]
        if len(funcs) < 2:
            continue
        texts = []
        for key, cl in txt.items():
            if key == f"{norm(doc)}@{section}":
                texts.extend(str(c.get("text", "")) for c in cl)
        corpus = "".join(texts)
        if not corpus:
            first_claim = ""
        else:
            first_claim = f"正文记载：{corpus[:800]}"
        rec(f"正文提及的功能包括：{'、'.join(funcs[:12])}。",
            first_claim, "qa_alpaca/A3", d["instruction"], d["input"],
            d["output"], None)

    # ═══ B1 (实际0命中: alpaca无"表头字段"连续子串) ═══
    b1_qs = [d for d in qa_lines if "表头字段" in str(d.get("instruction", ""))]
    for d in b1_qs:
        ins = str(d.get("instruction", ""))
        m_cap = re.search(r"「(.+?)」", ins)
        if not m_cap:
            continue
        chunks = cap_only.get(norm(m_cap.group(1)), [])
        if len(chunks) != 1:
            continue
        tchunk = chunks[0]
        rows = rows_all(tchunk)
        if not rows:
            continue
        header = rows[0]
        rec(f"表格《{m_cap.group(1)}》的表头字段包括：{'、'.join(header[:8])}，符合GJB 438C规范。",
            f"表头字段为：{'、'.join(header)}。",
            "qa_alpaca/B1", d["instruction"], d["input"], d["output"], None)

    # ═══ B3 ═══
    b3_qs = [d for d in qa_lines
             if "标识符" in str(d.get("instruction", ""))
             and "重复" in str(d.get("instruction", ""))]
    for d in b3_qs:
        ins = str(d.get("instruction", ""))
        m_cap = re.search(r"「(.+?)」", ins)
        if not m_cap:
            continue
        chunks = cap_only.get(norm(m_cap.group(1)), [])
        if len(chunks) != 1:
            continue
        tchunk = chunks[0]
        rows = rows_all(tchunk)
        id_col = None
        if rows:
            for i, h in enumerate(rows[0]):
                if "标识" in h or "ID" in h.upper():
                    id_col = i
                    break
        real_ids = ([r[id_col] for r in rows[1:]
                     if len(r) > id_col and r[id_col]]
                    if id_col is not None else [])
        if not real_ids:
            continue
        rec(f"表格《{m_cap.group(1)}》中的需求标识符各不重复。",
            f"需求标识符包括：{'、'.join(real_ids[:8])}。",
            "qa_alpaca/B3", d["instruction"], d["input"], d["output"], None)

    # ═══ C1 (+balanced) ═══
    c1_qs = [d for d in qa_lines
             if "异常流" in str(d.get("instruction", ""))
             and "未定义" in str(d.get("instruction", ""))]
    defined_es = set()
    for key, cl in txt.items():
        for c in cl:
            defined_es.update(
                re.findall(r"异常流\s*(E\d+)", str(c.get("text", ""))))
    n_c1bal = 0
    for d in c1_qs:
        try:
            meta = ast.literal_eval(str(d.get("input", "")))
        except (ValueError, SyntaxError):
            continue
        doc = str(meta.get("doc", ""))
        tchunk = tbl.get(f"{norm(str(meta.get('table_caption', '')))}@{norm(doc)}")
        if not tchunk:
            continue
        first_claim = f"文档定义的异常流包括：{'、'.join(sorted(defined_es)[:15])}。"
        rec("文档中定义的异常流包括：E9。", first_claim,
            "qa_alpaca/C1", d["instruction"], d["input"], d["output"], meta)
        if defined_es and n_c1bal < 150:
            e_real = sorted(defined_es)[n_c1bal % len(defined_es)]
            rec(f"文档中定义的异常流包括：{e_real}。", first_claim,
                "qa_alpaca/C1-balanced", d["instruction"], d["input"],
                d["output"], meta)
            n_c1bal += 1

    # ═══ family ═══
    for x in fam:
        prem, hyp = x["premise"], x["hypothesis"]
        if x["family"] == "C":
            continue
        if (normkey(prem), normkey(hyp)) in train_keys:
            continue
        prov = x.get("provenance", "")
        rec(hyp, prem, f"family/{prov}", None, None, None, None)

    # ═══ dedup(与构建器同键) ═══
    seen = set()
    kept = []
    for r in recs:
        key = (normkey(r["answer"]), normkey(r["first_claim"]))
        if key in seen:
            continue
        seen.add(key)
        kept.append(r)

    # ═══ 与实际AEE逐条验证 ═══
    aee = json.loads(AEE_PATH.read_text(encoding="utf-8"))["entries"]
    if len(kept) != len(aee):
        raise SystemExit(f"重放条数不符: replay={len(kept)} aee={len(aee)}")
    mism = 0
    for i, (r, e) in enumerate(zip(kept, aee, strict=True)):
        ok_a = r["answer"] == e["answer"]["text"]
        ok_c = r["first_claim"] == (e["evidence"][0]["claims"][0]
                                    if e["evidence"][0]["claims"] else "")
        ok_p = r["prov"] == e["provenance"]
        if not (ok_a and ok_c and ok_p):
            mism += 1
            if mism <= 5:
                print(f"  MISMATCH #{i}: {e['id']} prov {r['prov']}/{e['provenance']}")
    if mism:
        raise SystemExit(f"重放与AEE不一致: {mism}条")
    print(f"重放验证: {len(kept)}条 answer/claim/provenance 全等")

    # ═══ 输出审计 ═══
    entries_out = []
    status_counter: Counter = Counter()
    for r, e in zip(kept, aee, strict=True):
        if r["prov"].startswith("family/"):
            status = "family_no_question"
        elif r["prov"] == "qa_alpaca/C1":
            status = "recovered_synthetic_question"
        else:
            status = "recovered"
        status_counter[status] += 1
        q = r["question"]
        style = None
        if q:
            style = "hypothesis_template" if "假设" in q else "alpaca_instruction"
        entries_out.append({
            "aee_id": e["id"],
            "provenance": r["prov"],
            "recovery_status": status,
            "question": q,
            "question_reconstructed": (reconstruct_question(q, r["meta"])
                                        if q else None),
            "question_style": style,
            "qa_input": r["input"],
            "qa_output_head": (r["output"][:200] if r["output"] else None),
            "answer_match": True,
        })

    out = {
        "meta": {
            "version": "aee_question_recovery_v1",
            "date": "2026-10-20",
            "total": len(entries_out),
            "summary": dict(sorted(status_counter.items())),
            "method": "确定性重放build_answer_evidence_evalset分支; 1443条answer/claim/provenance全等验证",
            "notes": [
                "qa_alpaca族原始question来自srs_alpaca.jsonl instruction",
                "A1/C1原始question含{table}/{image}占位符, question_reconstructed已回填caption",
                "C1原始question为'假设'类合成模板(recovered_synthetic_question)",
                "family/*无源question(来自family_evalset_v1 premise/hypothesis)",
                "B1实际0条: alpaca无'表头字段'连续子串(构建器B1分支空跑)",
                "本审计不修改AEE, 不判定gold",
            ],
        },
        "entries": entries_out,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"aee_question_recovery: {len(entries_out)}条")
    print(f"summary: {dict(sorted(status_counter.items()))}")
    print(f"saved → {OUT_PATH}")


if __name__ == "__main__":
    main()
