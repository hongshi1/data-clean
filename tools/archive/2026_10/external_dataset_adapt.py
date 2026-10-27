# -*- coding: utf-8 -*-
"""外部数据集适配脚本：将5个公开数据集转换为项目统一的Alpaca/ShareGPT微调格式。

数据源（全部已本地下载验证）：
  1. PURE     (data/external_datasets/pure/xml/XMLZIPFile/)   18份XML标注需求文档
  2. NLI-RE   (data/external_datasets/nli_re/)                PROMISE FR/NFR + 需求缺陷 + 冲突需求对
  3. Ambiguity(data/external_datasets/ambiguity/)             语言学歧义标注（指代/并列）
  4. FlowVQA  (data/external_datasets/flowvqa/)               Mermaid流程图问答
  5. LLM-Gen  (data/external_datasets/llm_gen_req/)           LLM生成需求的质量评分

输出：
  - data/gjb_438c/easydataset/external_alpaca.jsonl   外部数据（Alpaca）
  - data/gjb_438c/easydataset/external_sharegpt.jsonl 外部数据（ShareGPT，带tags）
  - data/gjb_438c/easydataset/srs_alpaca_full.jsonl   现有18119条 + 外部（合并）
  - data/gjb_438c/easydataset/srs_sharegpt_full.jsonl 同上（ShareGPT）
  - data/external_datasets/adaptation_report.json      统计报告

用法：
  python -X utf8 tools/external_dataset_adapt.py [--flowvqa-sample 6000] [--pure-cap 2500] [--seed 42]
"""
import argparse
import hashlib
import json
import random
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
EXT = BASE / "data" / "external_datasets"
NS = {"r": "req_document.xsd"}


def _rec(instruction, input_text, output, source, qtype, difficulty):
    """统一记录结构：Alpaca三字段 + ShareGPT用tags。"""
    return {
        "instruction": instruction,
        "input": input_text,
        "output": output,
        "tags": [source, qtype, difficulty, "英文"],
    }


# ---------------------------------------------------------------- PURE

def parse_pure(rng, cap=2500, skipped=None):
    """PURE：需求识别(P1) + 术语问答(P2) + 章节结构(P3) + 修饰符(P4)。"""
    skipped = skipped if skipped is not None else {}
    records = []
    xml_dir = EXT / "pure" / "xml" / "XMLZIPFile"
    files = sorted(xml_dir.glob("*.xml"))

    pos_pool, neg_pool, glossary, sections, modifiers = [], [], [], [], []
    for fp in files:
        try:
            root = ET.parse(str(fp)).getroot()
        except ET.ParseError:
            skipped["pure_parse_error"] = skipped.get("pure_parse_error", 0) + 1
            continue
        title_el = root.find("r:title", NS)
        doc_title = ("".join(title_el.itertext()).strip()[:100]) if title_el is not None else fp.stem

        # 需求元素（正例池） + 修饰符
        for req in root.findall(".//r:req", NS):
            texts = [t.text.strip() for t in req.findall("r:text_body", NS) if t.text and t.text.strip()]
            if not texts:
                continue
            text = " ".join(texts)
            if len(text) >= 30:
                pos_pool.append(text)
            else:
                skipped["pure_req_too_short"] = skipped.get("pure_req_too_short", 0) + 1
            mod = req.find("r:modifier", NS)
            if mod is not None and mod.text and mod.text.strip() in ("M", "O"):
                modifiers.append((text, mod.text.strip()))

        # 非需求正文（负例池）：text_body 且父节点不是req
        parent_map = {c: p for p in root.iter() for c in p}
        req_tag = "{req_document.xsd}req"
        for tb in root.findall(".//r:text_body", NS):
            par = parent_map.get(tb)
            if par is not None and par.tag == req_tag:
                continue
            txt = (tb.text or "").strip()
            if len(txt) >= 40:
                neg_pool.append(txt)

        # 术语表
        for gi in root.findall(".//r:glossary_item", NS):
            term = gi.find("r:term", NS)
            meaning = gi.find("r:meaning", NS)
            if term is not None and meaning is not None:
                t = (term.text or "").strip()
                m = (meaning.text or "").strip()
                if t and m:
                    glossary.append((t, m, doc_title))

        # 章节结构
        for p in root.findall(".//r:p", NS):
            pid = p.get("id")
            tel = p.find("r:title", NS)
            title = (tel.text or "").strip() if tel is not None else ""
            if not pid or not title:
                continue
            children = []
            for ch in p.findall("r:p", NS):
                cid = ch.get("id")
                ctitle_el = ch.find("r:title", NS)
                ctitle = (ctitle_el.text or "").strip() if ctitle_el is not None else ""
                if cid:
                    children.append((cid, ctitle))
            sections.append({"id": pid, "title": title, "doc": doc_title, "children": children})

    # P1 需求识别（1:1正负采样，默认各800）
    pos = rng.sample(pos_pool, min(800, len(pos_pool)))
    neg = rng.sample(neg_pool, min(800, len(neg_pool)))
    for t in pos:
        records.append(_rec(
            "判断以下句子来自某需求规格文档，它是一条需求语句（对系统应做什么的可验证陈述），还是一般性描述文字？",
            t, "这是一条需求语句。", "外部-PURE", "P1_需求识别", "easy"))
    for t in neg:
        records.append(_rec(
            "判断以下句子来自某需求规格文档，它是一条需求语句（对系统应做什么的可验证陈述），还是一般性描述文字？",
            t, "这不是需求语句，属于一般性描述文字。", "外部-PURE", "P1_需求识别", "easy"))

    # P2 术语问答（正向 + 反向）
    for term, meaning, doc in glossary:
        records.append(_rec(
            f"需求文档中的术语“{term}”的定义是什么？",
            f"文档：{doc}", meaning, "外部-PURE", "P2_术语问答", "easy"))
        records.append(_rec(
            "需求文档中，哪个术语的含义与以下内容对应？",
            meaning, term, "外部-PURE", "P2_术语问答", "easy"))

    # P4 修饰符
    for text, mod in modifiers:
        out = "M（强制需求）" if mod == "M" else "O（可选需求）"
        records.append(_rec(
            "这条需求的约束强度修饰符是什么（M=强制mandatory，O=可选optional）？",
            text, out, "外部-PURE", "P4_修饰符", "medium"))

    # P3 章节结构（用剩余配额，严格遵守cap）
    remaining = max(0, cap - len(records))
    if remaining > 0 and sections:
        chosen = rng.sample(sections, min(remaining, len(sections)))
        for sec in chosen:
            if len(records) >= cap:
                break
            records.append(_rec(
                f"需求文档《{sec['doc']}》中，章节{sec['id']}的标题是什么？",
                f"文档：{sec['doc']}", sec["title"], "外部-PURE", "P3_章节结构", "medium"))
            # 有子章节的生成子章节问题（计入同一配额）
            if sec["children"] and len(records) < cap:
                child_str = "；".join(f"{cid} {ct}" for cid, ct in sec["children"] if ct)
                if child_str:
                    records.append(_rec(
                        f"需求文档《{sec['doc']}》中，章节{sec['id']}下包含哪些子章节？",
                        f"文档：{sec['doc']}\n章节：{sec['id']} {sec['title']}", child_str,
                        "外部-PURE", "P3_章节结构", "medium"))
    skipped["pure_p3_sections_available"] = len(sections)
    return records


# ---------------------------------------------------------------- NLI-RE

DEFECT_MAP = {
    "ambiguous": "模糊", "directive": "指示性", "non-atomic": "非原子",
    "non-measurable": "不可测量", "optional": "可选性", "uncertain": "不确定",
}


def parse_nli_re(rng):
    """NLI-RE：冲突检测(N1) + 缺陷分类(N2) + FR/NFR分类(N3)。"""
    records = []
    path = EXT / "nli_re" / "NLI-RE-Datasets.xlsx"
    xl = pd.ExcelFile(str(path))

    # ---- N3 FR/NFR分类（625条）
    cls = xl.parse("task1-class-description")
    abv2name = {str(a).strip(): str(n).strip() for a, n in zip(cls["class_abv"], cls["class_name"])}
    raw1 = xl.parse("task1-raw-data").dropna(subset=["RequirementText", "class"])
    for _, row in raw1.iterrows():
        abbr = str(row["class"]).strip()
        name = abv2name.get(abbr, abbr)
        out = f"{name}（功能需求）" if abbr == "F" else f"{name}（非功能需求）"
        records.append(_rec(
            "判断该需求属于功能需求还是非功能需求，并给出具体类别。",
            str(row["RequirementText"]).strip(), out, "外部-NLIRE", "N3_FRNFR分类", "medium"))

    # ---- N2 缺陷分类（131条）
    raw2 = xl.parse("task2-raw-data").dropna(subset=["Requirement", "Class"])
    for _, row in raw2.iterrows():
        en = str(row["Class"]).strip()
        cn = DEFECT_MAP.get(en.lower(), en)
        records.append(_rec(
            "识别以下软件需求中存在的需求缺陷类型（六类之一：模糊ambiguous、指示性directive、"
            "非原子non-atomic、不可测量non-measurable、可选性optional、不确定uncertain）。",
            str(row["Requirement"]).strip(), f"{cn}（{en}）", "外部-NLIRE", "N2_缺陷分类", "hard"))

    # ---- N1 冲突检测（137对正例 + 等量负例）
    conflict_instr = ("判断以下两条软件需求之间是否存在冲突（不一致）。若存在冲突，请指出冲突类型并简要说明；"
                      "若不存在，请说明两条需求相互兼容。")

    def add_conflict(r1, r2, label=None, explanation=None):
        out = "存在冲突。"
        if label:
            out += f"冲突类型：{label}。"
        else:
            out += "这两条需求对同一事项给出了相互矛盾的规定。"
        if explanation and isinstance(explanation, str) and len(explanation.strip()) > 2:
            out += f"说明：{explanation.strip()}"
        records.append(_rec(conflict_instr, f"需求1：{r1}\n需求2：{r2}",
                            out, "外部-NLIRE", "N1_冲突检测", "hard"))

    # 有类型标签的冲突（p2/p6/p10 + Broker，共54对）
    c1 = xl.parse("task3-conflicts-p2-p6-p10")
    expl_col = [c for c in c1.columns if str(c).startswith("Unnamed")][0] if any(
        str(c).startswith("Unnamed") for c in c1.columns) else None
    for _, row in c1.iterrows():
        if pd.isna(row["Requirement1"]) or pd.isna(row["Requirement2"]):
            continue
        explanation = row.get(expl_col) if expl_col else None
        add_conflict(str(row["Requirement1"]).strip(), str(row["Requirement2"]).strip(),
                     str(row["Detailed Label"]).strip() if pd.notna(row["Detailed Label"]) else None,
                     explanation)
    c2 = xl.parse("task3-conflicts-Broker")
    for _, row in c2.iterrows():
        if pd.isna(row["Requirement1"]) or pd.isna(row["Requirement2"]):
            continue
        add_conflict(str(row["Requirement1"]).strip(), str(row["Requirement2"]).strip(),
                     str(row["Detailed Label"]).strip() if pd.notna(row["Detailed Label"]) else None)

    # 无类型标签的冲突（ETCS/Library/Coffee，共83对）+ 对应需求池
    conflict_pairs_by_pool = {}

    def pool_conflicts(pairs, pool_name):
        s = conflict_pairs_by_pool.setdefault(pool_name, set())
        for a, b in pairs:
            s.add(frozenset((a, b)))

    untyped = [
        ("task3-ETCS-GOLD-Conflict", "task3-ETCS-GOLD", "Requirements", "etcs"),
        ("task3-Library-Gold-Conflict", "task3-Library-Gold", "Requirements", "library"),
        ("task3-Coffee-GOLD-Conflict", "task3-Coffee-GOLD", "Requirements", "coffee"),
    ]
    for sheet_c, sheet_p, col, pool_name in untyped:
        dfc = xl.parse(sheet_c).dropna()
        # 取需求文本列（Requirement1_text/Requirement2_text或Requirement1/Requirement2）
        r1col, r2col = [c for c in dfc.columns if "Requirement" in str(c)][:2]
        pairs = []
        for _, row in dfc.iterrows():
            r1, r2 = str(row[r1col]).strip(), str(row[r2col]).strip()
            pairs.append((r1, r2))
            add_conflict(r1, r2)
        pool_conflicts(pairs, pool_name)
        # 记录需求池
        conflict_pairs_by_pool.setdefault(pool_name + "__pool", None)
        dfp = xl.parse(sheet_p)
        pool_reqs = [str(x).strip() for x in dfp[col].dropna() if str(x).strip()]
        conflict_pairs_by_pool[pool_name + "__pool"] = pool_reqs

    # p2/p6/p10 各项目需求池（用于负例采样）
    proj_pools = {}
    for sheet, pid in {"task3-project2": "2", "task3-project6": "6", "task3-project10": "10"}.items():
        df = xl.parse(sheet).dropna(subset=["RequirementText"])
        proj_pools[pid] = [str(x).strip() for x in df["RequirementText"] if str(x).strip()]
    # p2/p6/p10 有类型冲突加入对应池的冲突集合
    for _, row in c1.iterrows():
        if pd.notna(row["Requirement1"]) and pd.notna(row["Requirement2"]):
            pid = str(int(row["project-ID"])) if pd.notna(row["project-ID"]) else None
            if pid:
                conflict_pairs_by_pool.setdefault(f"p{pid}", set()).add(
                    frozenset((str(row["Requirement1"]).strip(), str(row["Requirement2"]).strip())))
    broker_pool = [str(x).strip() for x in
                   xl.parse("task3-Broker-All")["Requirements"].dropna() if str(x).strip()]
    broker_conf = set()
    for _, row in c2.iterrows():
        if pd.notna(row["Requirement1"]) and pd.notna(row["Requirement2"]):
            broker_conf.add(frozenset((str(row["Requirement1"]).strip(), str(row["Requirement2"]).strip())))

    # 负例采样：每个池采与正例等量的非冲突对
    def sample_negatives(pool, conflict_set, n):
        out, seen = [], set()
        attempts = 0
        while len(out) < n and attempts < n * 60:
            attempts += 1
            if len(pool) < 2:
                break
            a, b = rng.sample(pool, 2)
            if a == b or frozenset((a, b)) in conflict_set or frozenset((a, b)) in seen:
                continue
            seen.add(frozenset((a, b)))
            out.append((a, b))
        return out

    # p2/p6/p10 按项目负采样
    p_conf_counts = c1.dropna(subset=["Requirement1"]).groupby("project-ID").size().to_dict()
    for pid, cnt in p_conf_counts.items():
        pool = proj_pools.get(str(int(pid)), [])
        negs = sample_negatives(pool, conflict_pairs_by_pool.get(f"p{int(pid)}", set()), int(cnt))
        for a, b in negs:
            records.append(_rec(conflict_instr, f"需求1：{a}\n需求2：{b}",
                                "不存在冲突。两条需求相互独立/兼容。", "外部-NLIRE", "N1_冲突检测", "hard"))
    # broker
    negs = sample_negatives(broker_pool, broker_conf, len(c2))
    for a, b in negs:
        records.append(_rec(conflict_instr, f"需求1：{a}\n需求2：{b}",
                            "不存在冲突。两条需求相互独立/兼容。", "外部-NLIRE", "N1_冲突检测", "hard"))
    # etcs/library/coffee
    for pool_name in ("etcs", "library", "coffee"):
        pool = conflict_pairs_by_pool.get(pool_name + "__pool", [])
        conf = conflict_pairs_by_pool.get(pool_name, set())
        n_pool_conf = len(conf)
        negs = sample_negatives(pool, conf, n_pool_conf)
        for a, b in negs:
            records.append(_rec(conflict_instr, f"需求1：{a}\n需求2：{b}",
                                "不存在冲突。两条需求相互独立/兼容。", "外部-NLIRE", "N1_冲突检测", "hard"))
    return records


# ---------------------------------------------------------------- Ambiguity

def parse_ambiguity():
    """语言学歧义检测。注意：MissingCondition.xlsx的PMC/NPMC标签语义不明确（样例
    'If not then...'人工标注为NPMC，与直觉相反），且正例仅5条，v1不纳入，见报告说明。"""
    records = []
    specs = [
        ("Anaphoric.xlsx", "A1_指代歧义", "medium",
         "判断以下软件需求是否包含指代歧义（anaphoric ambiguity，如it/they等指代不明）？",
         "是，包含指代歧义。", "否，不包含指代歧义。"),
        ("Coordination.xlsx", "A2_并列歧义", "medium",
         "判断以下软件需求是否包含并列歧义（coordination ambiguity，如and/or连接歧义）？",
         "是，包含并列歧义。", "否，不包含并列歧义。"),
    ]
    for fname, qtype, diff, instr, yes, no in specs:
        df = pd.read_excel(EXT / "ambiguity" / fname)
        df = df.dropna(subset=["Raw Requirements", "Manual Evaluation"])
        for _, row in df.iterrows():
            label = str(row["Manual Evaluation"]).strip().upper()
            if label not in ("A", "UA"):
                continue
            records.append(_rec(instr, str(row["Raw Requirements"]).strip(),
                                yes if label == "A" else no, "外部-歧义检测", qtype, diff))
    return records


# ---------------------------------------------------------------- FlowVQA

def parse_flowvqa(rng, total=6000, skipped=None):
    """FlowVQA：mermaid流程图问答，分层采样。"""
    skipped = skipped if skipped is not None else {}
    stratify = {"topological": 2000, "applied_scenario": 1500,
                "fact_retrieval": 1500, "flow_referential": 1000}
    scale = total / sum(stratify.values())
    stratify = {k: int(v * scale) for k, v in stratify.items()}
    difficulty = {"fact_retrieval": "easy", "flow_referential": "medium",
                  "applied_scenario": "medium", "topological": "hard"}
    pools = {k: [] for k in stratify}
    for name in ("test_full.json", "train_full.json"):
        with open(EXT / "flowvqa" / name, encoding="utf-8") as f:
            d = json.load(f)
        for e in d.values():
            mermaid = e.get("mermaid") or ""
            if len(mermaid) > 3000:
                skipped["flowvqa_mermaid_too_long"] = skipped.get("flowvqa_mermaid_too_long", 0) + 1
                continue
            for qa in (e.get("qa") or {}).values():
                q = (qa.get("Q") or "").strip()
                a = (qa.get("A1") or "").strip()
                t = qa.get("type")
                if q and a and t in pools:
                    pools[t].append((mermaid, q, a))
    records = []
    for t, want in stratify.items():
        chosen = rng.sample(pools[t], min(want, len(pools[t])))
        for mermaid, q, a in chosen:
            records.append(_rec(
                "根据以下Mermaid流程图，回答问题。",
                f"```mermaid\n{mermaid}\n```\n\n问题：{q}", a,
                "外部-FlowVQA", f"F1_{t}", difficulty[t]))
    skipped["flowvqa_pool_sizes"] = {k: len(v) for k, v in pools.items()}
    return records


# ---------------------------------------------------------------- LLM-Gen

def parse_llm_gen():
    """LLM生成需求的质量评估（Unambiguity/Verifiability/Singularity 1-5分+理由）。"""
    records = []
    df = pd.read_csv(EXT / "llm_gen_req" / "parsed.csv").dropna(
        subset=["Requirement", "Unambiguity", "Verifiability", "Singularity"])
    for _, row in df.iterrows():
        def fmt(x):
            fx = float(x)
            return str(int(fx)) if fx == int(fx) else str(fx)
        expl = row.get("Explanation")
        expl_s = str(expl).strip() if pd.notna(expl) else ""
        out = (f"无歧义性：{fmt(row['Unambiguity'])}/5；可验证性：{fmt(row['Verifiability'])}/5；"
               f"单一性：{fmt(row['Singularity'])}/5")
        if expl_s:
            out += f"\n理由：{expl_s}"
        records.append(_rec(
            "评估以下软件需求的写作质量，从三个维度各打1到5分：无歧义性（Unambiguity）、"
            "可验证性（Verifiability）、单一性（Singularity，一条需求只描述一件事），并给出评估理由。",
            str(row["Requirement"]).strip(), out, "外部-LLMGen", "L1_质量评估", "medium"))
    return records


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="外部数据集适配：转换为Alpaca/ShareGPT格式并合并")
    ap.add_argument("--flowvqa-sample", type=int, default=6000)
    ap.add_argument("--pure-cap", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", default=str(BASE / "data" / "gjb_438c" / "easydataset"))
    args = ap.parse_args()
    rng = random.Random(args.seed)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    skipped = {}
    pure = parse_pure(rng, cap=args.pure_cap, skipped=skipped)
    nli = parse_nli_re(rng)
    amb = parse_ambiguity()
    fvq = parse_flowvqa(rng, total=args.flowvqa_sample, skipped=skipped)
    llm = parse_llm_gen()
    all_recs = pure + nli + amb + fvq + llm

    # 去重（instruction+input精确md5）
    seen, deduped, dedup_removed = set(), [], 0
    for r in all_recs:
        h = hashlib.md5((r["instruction"] + "\x00" + r["input"]).encode("utf-8")).hexdigest()
        if h in seen:
            dedup_removed += 1
            continue
        seen.add(h)
        deduped.append(r)

    # 长度校验
    valid, len_dropped = [], 0
    for r in deduped:
        if not r["instruction"].strip() or not r["input"].strip() or not r["output"].strip():
            len_dropped += 1
            continue
        if len(r["input"]) > 4000 or len(r["output"]) > 2000:
            len_dropped += 1
            continue
        valid.append(r)

    # 写外部文件
    alpaca_path = out_dir / "external_alpaca.jsonl"
    sharegpt_path = out_dir / "external_sharegpt.jsonl"
    with open(alpaca_path, "w", encoding="utf-8", newline="\n") as f:
        for r in valid:
            f.write(json.dumps({"instruction": r["instruction"], "input": r["input"],
                                "output": r["output"]}, ensure_ascii=False) + "\n")
    with open(sharegpt_path, "w", encoding="utf-8", newline="\n") as f:
        for r in valid:
            f.write(json.dumps({
                "conversations": [
                    {"from": "human", "value": r["instruction"] + ("\n" + r["input"] if r["input"] else "")},
                    {"from": "gpt", "value": r["output"]}],
                "tags": r["tags"]}, ensure_ascii=False) + "\n")

    # 合并文件（现有数据只读拼接）
    for existing_name, external_name, merged_name in [
            ("srs_alpaca.jsonl", "external_alpaca.jsonl", "srs_alpaca_full.jsonl"),
            ("srs_sharegpt.jsonl", "external_sharegpt.jsonl", "srs_sharegpt_full.jsonl")]:
        existing = out_dir / existing_name
        external = out_dir / external_name
        merged = out_dir / merged_name
        n_exist = 0
        with open(merged, "w", encoding="utf-8", newline="\n") as fo:
            if existing.exists():
                with open(existing, encoding="utf-8") as fe:
                    for line in fe:
                        if line.strip():
                            fo.write(line if line.endswith("\n") else line + "\n")
                            n_exist += 1
            n_ext = 0
            with open(external, encoding="utf-8") as fx:
                for line in fx:
                    if line.strip():
                        fo.write(line if line.endswith("\n") else line + "\n")
                        n_ext += 1

    # 统计报告
    by_source = {}
    for r in valid:
        src, qtype, diff = r["tags"][0], r["tags"][1], r["tags"][2]
        by_source.setdefault(src, {}).setdefault(qtype, {"count": 0, "difficulty": diff})
        by_source[src][qtype]["count"] += 1
    report = {
        "generated_at": datetime.now().isoformat(),
        "seed": args.seed,
        "total_external": len(valid),
        "dedup_removed": dedup_removed,
        "length_or_empty_dropped": len_dropped,
        "skipped": skipped,
        "counts_by_source": by_source,
        "merged_files": {
            "srs_alpaca_full.jsonl": 18119 + len(valid) if len(valid) else None,
        },
        "samples": {},
    }
    for src in by_source:
        report["samples"][src] = [
            {k: (v[:200] + "..." if len(v) > 200 else v) for k, v in
             {"instruction": r["instruction"], "input": r["input"], "output": r["output"]}.items()}
            for r in [x for x in valid if x["tags"][0] == src][:2]]
    report_path = EXT / "adaptation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # stdout汇总
    print("=" * 62)
    print("外部数据集适配完成")
    print("=" * 62)
    for src, types in by_source.items():
        n = sum(v["count"] for v in types.values())
        detail = ", ".join(k + ":" + str(v["count"]) for k, v in types.items())
        print(f"  {src:<14} {n:>6} 条  ({detail})")
    print(f"  {'合计':<14} {len(valid):>6} 条")
    print(f"  去重移除: {dedup_removed} | 长度/空值跳过: {len_dropped}")
    print(f"  合并后: srs_alpaca_full.jsonl = 18119 + {len(valid)} = {18119 + len(valid)} 行")
    print(f"  报告: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
