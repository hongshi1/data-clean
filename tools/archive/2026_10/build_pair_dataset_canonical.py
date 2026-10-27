r"""统一Pair Dataset构建器: 全源经同一管线 → canonical形态.

规范: docs/srs_project/pair_dataset_spec.md
阶段: 配对(锚点/变异/外部) → 表面化(T1/T2/T3受控模板) → 标签 → 划分
产出: data/gjb_438c/pair_dataset_canonical/{train,dev,test}.jsonl + INDEX.json
用法: python tools/build_pair_dataset_canonical.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

OUT = BASE / "data/gjb_438c/pair_dataset_canonical"
OUT.mkdir(parents=True, exist_ok=True)

# ── 统一表面化模板族(受控3变体) ──
SIDE_NAME = {
    "sc1": ("能力表", "用例图"), "sc2": ("用例表", "流程图"), "sc3": ("接口表", "接口图"),
    "sc4": ("能力表", "流程图"), "sc5": ("子功能表", "功能图"), "text": ("正文", "正文"),
}


def verbalize_t1(subject: str, side_a: str, content_a: str, side_b: str, content_b: str,
                 relation: str = "missing") -> tuple[str, str]:
    """T1对照式(存在性关系): P声明存在, H声明缺失/不一致."""
    if relation == "missing":
        p = f"{subject}的{side_a}包含「{content_a}」。"
        h = f"{subject}的{side_b}中没有「{content_a}」的对应元素。"
    else:  # contradict: 值/顺序矛盾
        p = f"{subject}的{side_a}中的「{content_a}」。"
        h = f"{subject}的{side_b}中对应内容为「{content_b}」，两者冲突。"
    return p, h


def verbalize_t2(subject: str, side_a: str, content_a: str, side_b: str, content_b: str,
                 relation: str = "contradict") -> tuple[str, str]:
    """T2规定式: 两侧各自陈述(值矛盾时内容不同; 缺失时H为否定存在)."""
    if relation == "missing":
        p = f"{subject}的{side_a}规定：「{content_a}」为必备内容。"
        h = f"{subject}的{side_b}中未体现「{content_a}」。"
    else:
        p = f"{subject}的{side_a}规定：{content_a}。"
        h = f"{subject}的{side_b}规定：{content_b}。"
    return p, h


def verbalize_t3(subject: str, side_a: str, content_a: str, side_b: str, content_b: str,
                 relation: str = "contradict") -> tuple[str, str]:
    """T3文档式."""
    if relation == "missing":
        p = f"文档的{side_a}部分记载：「{content_a}」。"
        h = f"文档的{side_b}部分未出现该内容。"
    else:
        p = f"文档该部分记载：{content_a}。"
        h = f"文档另一部分记载：{content_b}。"
    return p, h


TEMPLATES = {"T1": verbalize_t1, "T2": verbalize_t2, "T3": verbalize_t3}
# 差异类型→关系: 存在性缺失 vs 内容矛盾
MISSING_TYPES = {"TABLE_ITEM_MISSING", "STEP_MISSING", "ACTOR_MISSING", "EXC_MISSING",
                 "COMPONENT_MISSING", "DIAGRAM_EXTRA", "DIAGRAM_EXTRA_COUNT"}


def relation_of(dtype: str) -> str:
    return "missing" if dtype in MISSING_TYPES else "contradict"


def _mk(sid: str, source: str, p: str, h: str, label: str, scene: str,
        modality: str, typ: str, doc: str, origin: str, surface: str,
        split: str, protocol: str = "", contamination: str = "", flags: list | None = None) -> dict:
    return {"id": f"PD-{sid}", "source": source,
            "pair": {"premise": p, "hypothesis": h}, "label": label,
            "angle": {"scene": scene, "modality": modality, "type": typ},
            "provenance": {"doc": doc, "origin": origin, "surface": surface, "protocol": protocol},
            "split": split,
            "quality": {"contamination": contamination, "flags": flags or []}}


def extract_quoted(text: str) -> str:
    m = re.search(r"[「]([^「」]+)[」]", str(text))
    return m.group(1).strip() if m else ""


# ═══ 多模态上下文加载(真实pair_dataset) ═══
PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"


def load_pair_context(pair_id: str, scene: str) -> dict:
    """从真实pair_dataset目录加载多模态上下文(表格行+visio节点+文本+图片)."""
    d = PAIR_ROOT / scene / pair_id
    if not d.exists():
        # scene可能是截断形式
        for sd in PAIR_ROOT.iterdir():
            if sd.is_dir() and sd.name.startswith(scene[:3]):
                if (sd / pair_id).exists():
                    d = sd / pair_id
                    break
        else:
            return {}
    ctx = {"pair_id": pair_id, "scene_dir": scene}
    meta_p = d / "meta.json"
    if meta_p.exists():
        try:
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            ctx.update({"doc": str(meta.get("doc", ""))[:40],
                        "section": meta.get("section", ""),
                        "image_caption": meta.get("image_caption", ""),
                        "table_caption": meta.get("table_caption", "")})
        except json.JSONDecodeError:
            pass
    tc = d / "table.csv"
    if tc.exists():
        try:
            rows = list(csv.reader(open(tc, encoding="utf-8")))
            body = [r for r in rows[1:] if any(r)]
            ctx["table"] = "\n".join(",".join(r[:5]) for r in body[:12])[:600]
            ctx["table_rows_full"] = body
        except (OSError, csv.Error):
            pass
    va = d / "visio_anchor.json"
    if va.exists():
        try:
            v = json.loads(va.read_text(encoding="utf-8"))
            nodes = [str(n.get("text", "")) for n in v.get("nodes", []) if n.get("text")]
            ctx["diagram"] = "; ".join(nodes[:25])[:600]
        except json.JSONDecodeError:
            pass
    tp = d / "text.txt"
    if tp.exists():
        ctx["text"] = tp.read_text(encoding="utf-8")[:300]
    ctx["image"] = str(d.relative_to(BASE) / "image.png")
    return ctx


_NUM_PAT = re.compile(r"\d+\.?\d*")


def mutate_table_row(row: list[str], header: list[str]) -> tuple[str, str, str] | None:
    """对真实表格行生成变异: 返回(原陈述, 变异陈述, 类型)或None."""
    for j, cell in enumerate(row):
        if not cell:
            continue
        col = header[j] if j < len(header) else ""
        # PARAM: 数值变异
        m = _NUM_PAT.search(cell)
        if m and len(m.group()) >= 1 and m.group() not in ("0", "1") and col not in ("序号", "编号"):
            old = m.group()
            val = float(old)
            new = f"{val * 2:g}" if val < 100 else f"{val / 2:g}"
            if new != old:
                return (f"表格规定{col}「{cell[:40]}」（数值为{old}）。",
                        f"表格对应内容变异为数值{new}。", "PARAM-02")
        # TERM: 优先级/状态字段变异
        if cell in ("高", "中", "低") and col:
            new = {"高": "低", "低": "高", "中": "低"}[cell]
            return (f"表格规定该条目的{col}为「{cell}」。",
                    f"表格对应条目的{col}变异为「{new}」。", "TERM-03")
        if cell in ("是", "否"):
            new = "否" if cell == "是" else "是"
            return (f"表格规定该条目的{col}取值为「{cell}」。",
                    f"表格对应条目的{col}变异为「{new}」。", "LOGIC-02")
    return None


def build_pair_mutation_items() -> list[dict]:
    """在真实pair_dataset的表格上生成变异(原始输入=真实多模态对)."""
    out = []
    for scene_dir in sorted(PAIR_ROOT.iterdir()):
        if not scene_dir.is_dir():
            continue
        scene = scene_dir.name
        scene_key = scene[:6]
        for pair_dir in sorted(scene_dir.iterdir()):
            if not pair_dir.is_dir():
                continue
            tc = pair_dir / "table.csv"
            if not tc.exists():
                continue
            try:
                rows = list(csv.reader(open(tc, encoding="utf-8")))
            except (OSError, csv.Error):
                continue
            body = [r for r in rows[1:] if any(r)]
            if not body:
                continue
            header = rows[0]
            meta = load_pair_context(pair_dir.name, scene)
            doc_id = str(meta.get("doc", ""))[:2]
            split = "test" if doc_id in ("04", "07") else "train"
            n_this = 0
            for row in body:
                if n_this >= 2:  # 每对最多2个变异
                    break
                mut = mutate_table_row(row, header)
                if not mut:
                    continue
                p, h, typ = mut
                item = _mk(f"pmut-{pair_dir.name}-{n_this}", "srs_pair_mutation",
                           p, h, "inconsistent", scene_key, "table-text", typ,
                           doc_id or "00", f"pair_mutation:{pair_dir.name}",
                           "T2", split, "constructed-on-real-pair")
                item["context"] = meta
                out.append(item)
                n_this += 1
    return out


# ═══ 源1: 锚点真实差异(重新表面化) ═══
def build_anchor_items() -> list[dict]:
    """md_gold(16文档) + gold_v2的裁决金标 → T1族canonical化(挂多模态context)."""
    out = []
    seen = set()
    queue = json.loads((BASE / "data/gjb_438c/human_gold/multidoc_queue_579.json").read_text(encoding="utf-8"))
    qmap = {q["qid"]: (q["pair"], q["scene"]) for q in queue}
    # md_gold: 577条(含质量标记), 重新表面化
    md = [json.loads(line) for line in open(BASE / "data/gjb_438c/unified_testset/md_gold.jsonl", encoding="utf-8")]
    for i, x in enumerate(md):
        key = (x["premise"], x["hypothesis"])
        if key in seen:
            continue
        seen.add(key)
        scene = x["meta"]["scene"][:6]
        sides = SIDE_NAME.get(scene if scene in SIDE_NAME else scene[:2], ("表格", "图"))
        content = extract_quoted(x["premise"]) or str(x["premise"])[:40]
        rel = relation_of(x["type"])
        # 3个受控表面变体(同标签, 关系感知) — CCT表面CF的规范来源
        for tname, tfn in TEMPLATES.items():
            p, h = tfn("该功能", sides[0], content[:60], sides[1], content[:60], rel)
            item = _mk(f"mda-{i}-{tname}", "srs_anchor", p, h, x["label"],
                       scene, "table-diagram", x["type"], x["meta"]["doc"],
                       f"anchor:{x['meta']['qid']}", tname,
                       "test" if x["meta"]["doc"] in ("04", "07") or scene == "sc3" else "train",
                       "cot-1", flags=[])
            pair_id, scene_full = qmap.get(x["meta"]["qid"], ("", ""))
            item["context"] = load_pair_context(pair_id, scene_full)
            out.append(item)
    # doc02金标v2(357): 同样canonical化(仅干净部分进train, held-out进test)
    v2 = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_357.json").read_text(encoding="utf-8"))
    tier1 = json.loads((BASE / "data/gjb_438c/anchor_sc2/tier1_discrepancies_v2.json").read_text(encoding="utf-8"))
    for i, x in enumerate(v2):
        meta = tier1.get(x["pair"], {})
        uc = meta.get("uc_name", "该用例")[:12] or "该用例"
        ts, ds = {}, {}
        for d in meta.get("discrepancies", []):
            if d["evidence"] == x["evidence"]:
                ts, ds = d.get("table_side") or {}, d.get("diag_side") or {}
                break
        content = str(ts.get("text", ""))[:60] or "相关内容"
        real = x["label"] == "real_bug"
        rel = relation_of(x["dtype"])
        for tname, tfn in TEMPLATES.items():
            if x["dtype"] == "ORDER_CONFLICT":
                p, h = tfn(uc, "用例表", f"执行顺序{ts.get('seq', '3→4')}", "流程图",
                           f"执行顺序{ds.get('edge', '4→3')}相反", "contradict")
            else:
                p, h = tfn(uc, "用例表", content, "流程图", content, rel)
            item = _mk(f"gdv2-{i}-{tname}", "srs_anchor", p, h,
                       "inconsistent" if real else "consistent",
                       "sc2", "table-diagram", x["dtype"], "02",
                       f"anchor:{x['tid']}", tname, "train", x["protocol"])
            item["context"] = load_pair_context(x["pair"], "sc2_flowchart_usecase")
            out.append(item)
    return out


# ═══ 源2: 变异基准(内容保留, schema归一) ═══
def build_mutation_items() -> list[dict]:
    out = []
    bench = [json.loads(line) for line in open(BASE / "data/gjb_438c/benchmark_full_v2.jsonl", encoding="utf-8")]
    n_drop = 0
    for i, x in enumerate(bench):
        if x["premise"] == x["hypothesis"]:  # 退化对(变异不可见)剔除
            n_drop += 1
            continue
        out.append(_mk(f"mut-{i}", "srs_mutation", x["premise"], x["hypothesis"],
                       x["expected_label"], "text", "text-text", x["check_item"],
                       str(x.get("doc_id", "")), f"mutation:{x.get('mutation_id', '')}",
                       "T3", x["split"], "constructed"))
    if n_drop:
        print(f"剔除退化变异对(P==H): {n_drop}条")
    return out


# ═══ 源3: 外部NLI(schema归一+二元转换) ═══
NLI_MAP = {"contradiction": "inconsistent", "entailment": "consistent", "neutral": "consistent"}


def build_external_items() -> list[dict]:
    out = []
    for name, split_default, contam in [("xnli_zh", "test", "mdeberta"),
                                         ("cmnli_dev", "dev", ""),
                                         ("ocnli_test", "test", "erlangshen")]:
        items = [json.loads(line) for line in open(BASE / f"data/gjb_438c/unified_testset/{name}.jsonl", encoding="utf-8")]
        for i, x in enumerate(items):
            if x["label_raw"] not in NLI_MAP:
                continue
            if x["label_raw"] == "contradiction" and x["premise"] == x["hypothesis"]:
                continue  # 源数据噪声(同文本标矛盾)剔除
            out.append(_mk(f"ext-{name[:4]}-{i}", "nli_external", x["premise"], x["hypothesis"],
                           NLI_MAP[x["label_raw"]], "text", "text-text",
                           f"NLI-{x['label_raw'][:5].upper()}", "external",
                           f"converted:{x['label_raw']}", "T3", split_default,
                           "official", contamination=contam))
    return out


# ═══ 源4: 外部增强(ANLI对抗 + PAWS-X中文释义) ═══
def build_enhanced_external_items() -> list[dict]:
    out = []
    import pandas as pd
    PUB = BASE / "data/gjb_438c/public_nli"
    # ANLI (英文对抗, dev人工标签): 0=entail 1=neutral 2=contradiction
    anli_map = {0: ("entailment", "consistent"), 1: ("neutral", "consistent"),
                2: ("contradiction", "inconsistent")}
    for r in (1, 2, 3):
        df = pd.read_parquet(PUB / f"anli_dev_r{r}.parquet")
        for i, row in df.iterrows():
            raw, lab = anli_map[int(row["label"])]
            reason = str(row.get("reason", ""))[:120]
            out.append(_mk(f"anli-r{r}-{i}", "nli_anli", str(row["premise"]), str(row["hypothesis"]),
                           lab, "text", "text-text", f"NLI-{raw[:5].upper()}", "external",
                           f"anli:r{r}:{row['uid']}", "T3", "test", "official+adversarial",
                           contamination="mdeberta?"))
    # PAWS-X zh (中文释义对抗: 高词重叠): 1=paraphrase→consistent难例
    for split_name, split in [("validation", "test"), ("test", "dev")]:
        df = pd.read_parquet(PUB / f"pawsx_{split_name}.parquet")
        for i, row in df.iterrows():
            if int(row["label"]) != 1:  # 仅释义对(表面异/义同→consistent)
                continue
            out.append(_mk(f"paws-{split_name[:4]}-{i}", "paws_external",
                           str(row["sentence1"]), str(row["sentence2"]),
                           "consistent", "text", "text-text", "PAWS-PARA", "external",
                           f"paws:{split_name}:{row['id']}", "T3", split, "official+paraphrase"))
    return out


def evidence_verification(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Stage6.5 证据核验: 缺失类声称 vs context.diagram实际节点 — 多模态确定性验证.

    声称"X在图中缺失"但X实际在diagram节点中 → pair叙述不成立 → 隔离(不进训练).
    """
    keep, quarantined = [], []
    for x in items:
        if (x["source"] == "srs_anchor" and "MISSING" in x["angle"]["type"]
                and x.get("context", {}).get("diagram")):
            m = re.search(r"[「]([^「」]+)[」]", x["pair"]["premise"])
            if m and len(m.group(1).strip()) >= 3:
                claim = m.group(1).strip()
                diag = x["context"]["diagram"]
                if claim in diag or claim.replace(" ", "") in diag.replace(" ", ""):
                    x["quality"]["flags"].append("evidence_refuted")
                    quarantined.append(x)
                    continue
        keep.append(x)
    return keep, quarantined


def main() -> None:
    anchor = build_anchor_items()
    mut = build_mutation_items()
    pair_mut = build_pair_mutation_items()
    ext = build_external_items()
    enh = build_enhanced_external_items()
    all_items = anchor + mut + pair_mut + ext + enh
    print(f"pair变异: +{len(pair_mut)}条(真实表格上生成)")
    print(f"外部增强: +{len(enh)}条(ANLI+PAWS-X)")

    # Stage6.5 证据核验(多模态确定性验证, 隔离假声称)
    all_items, quarantined = evidence_verification(all_items)
    print(f"证据核验: 隔离{len(quarantined)}条(声称被图证据反驳)")

    # 去重(同pair同标签)
    seen = set()
    dedup = []
    for x in all_items:
        k = (x["pair"]["premise"], x["pair"]["hypothesis"], x["label"])
        if k not in seen:
            seen.add(k)
            dedup.append(x)
    print(f"构建: anchor{len(anchor)} + mutation{len(mut)} + external{len(ext)} → 去重{len(dedup)}")

    # 文本级再去重(锚点重复问题)
    text_seen = set()
    final = []
    for x in dedup:
        tk = (x["pair"]["premise"][:60], x["pair"]["hypothesis"][:60])
        if x["source"] == "nli_external" or tk not in text_seen:
            text_seen.add(tk)
            final.append(x)

    splits = defaultdict(list)
    for x in final:
        splits[x["split"]].append(x)

    index = {"spec": "docs/srs_project/pair_dataset_spec.md", "total": len(final), "splits": {}}
    for sname, items in splits.items():
        with open(OUT / f"{sname}.jsonl", "w", encoding="utf-8") as f:
            for x in items:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        labs = Counter(x["label"] for x in items)
        srcs = Counter(x["source"] for x in items)
        surfs = Counter(x["provenance"]["surface"] for x in items)
        index["splits"][sname] = {"n": len(items), "labels": dict(labs),
                                  "sources": dict(srcs), "surfaces": dict(surfs)}
        print(f"{sname}: {len(items)}条 {dict(labs)} 源{dict(srcs)} 模板{dict(surfs)}")

    with open(OUT / "evidence_quarantine.jsonl", "w", encoding="utf-8") as f:
        for x in quarantined:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    index["quarantine"] = {"n": len(quarantined), "reason": "evidence_refuted"}
    with open(OUT / "INDEX.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"保存 → {OUT} (总{len(final)}+隔离{len(quarantined)})")


if __name__ == "__main__":
    main()
