r"""构建六族统一评测集 family_evalset_v1 (~1000条).

设计目标(用户需求):
  - 一个数据集, 六族(A数值/B顺序/C结构/D术语/E合规/F语义残差)覆盖
  - 无重复: (premise,hypothesis)全等去重 + 源级去重(synth每源每标签1条) + 每图限量
  - ~1000条: A150/B80/C346/D200/E70/F150
  - 每条带family/type/label/provenance, 供"我们的方法vs按族分派baseline"对比

来源与配额:
  A族(150): synth_s1 eval_minimal(PARAM-01/02/03, 源级去重已保证)
  B族(80):  unified_testset/gjb_bench_test(ORDER+LOGIC-01~04, 单标签族如实标注)
  C族(346): 冻结金标 clean130+md166(296) + image_pairs P4(50, Visio L1真值)
  D族(200): synth_s1 eval_minimal(TERM/ENUM, 源级去重)
  E族(70):  gjb_bench_test(GJB族, 单标签族; 词中注入质量过滤)
  F族(150): image_pairs P1_identity(κ_D语义残差: 同内容异表面)
"""
from __future__ import annotations

import difflib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

SEED = 42


def family_of(t: str) -> str:
    """48类型→六族映射."""
    if re.fullmatch(r"PARAM-\d+", t):
        return "A"
    if t in ("ORDER_CONFLICT", "LOGIC-01", "LOGIC-02", "LOGIC-03", "LOGIC-04"):
        return "B"
    if t.startswith("GJB-"):
        return "E"
    if t.startswith("TERM-") or t.startswith("ENUM-"):
        return "D"
    # C族结构存在
    if t in ("TABLE_ITEM_MISSING", "ACTOR_MISSING", "STEP_MISSING", "EXC_MISSING",
             "DIAGRAM_EXTRA", "DIAGRAM_EXTRA_COUNT", "COMPONENT_MISSING",
             "UC_NAME_MISMATCH", "LOGIC-05"):
        return "C"
    return "F"


def is_clean_mutation(p: str, h: str) -> bool:
    """质量过滤: 词中注入(如「公共组件管(保密)理」)判定为脏变异."""
    matcher = difflib.SequenceMatcher(None, p, h)
    ops = [op for op in matcher.get_opcodes() if op[0] in ("insert", "delete")]
    if not ops:
        return True
    for tag, i1, i2, j1, j2 in ops:
        frag = h[j1:j2] if tag == "insert" else p[i1:i2]
        if len(frag) < 2:
            continue
        # 插入点前后字符: 若两侧都是中文(词中间) → 词中注入
        before = p[max(0, i1 - 1):i1] or h[max(0, j1 - 1):j1]
        after = (p[i2:i2 + 1] if i2 < len(p) else "") or (h[j2:j2 + 1] if j2 < len(h) else "")
        if re.fullmatch(r"[\u4e00-\u9fa5]", before) and re.fullmatch(r"[\u4e00-\u9fa5]", after):
            # 词中间插入且插入片段本身不含标点边界 → 脏
            if not re.search(r"[。；：、,，\s「」（）()]", frag[:1] + frag[-1:]):
                return False
    return True


def main() -> None:
    rng = random.Random(SEED)
    G = BASE / "data/gjb_438c"

    # ── 源数据加载 ──
    split = json.loads((G / "synth_s1_split.json").read_text(encoding="utf-8"))
    s1_minimal = split["eval_minimal"]  # 每源每标签1条, 已源级去重
    bench = [json.loads(line) for line in open(G / "unified_testset/gjb_bench_test.jsonl", encoding="utf-8")]
    clean130 = json.loads((G / "human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md = (json.loads((G / "human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
          + json.loads((G / "human_gold/md_test_sc3.json").read_text(encoding="utf-8")))
    img = json.loads((G / "image_pairs.json").read_text(encoding="utf-8"))["pairs"]

    out: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(premise: str, hypothesis: str, label: str, fam: str, typ: str,
            prov: str, surface: str = "", doc: str = "") -> bool:
        key = (premise, hypothesis)
        if key in seen:
            return False
        seen.add(key)
        out.append({"id": f"{fam}-{len(out) + 1:04d}", "family": fam, "type": typ,
                    "label": label, "premise": premise, "hypothesis": hypothesis,
                    "provenance": prov, "surface": surface, "doc": doc})
        return True

    # ── A族(150): synth PARAM, 源级去重, 标签均衡(75inc/75con) ──
    a_pairs = [p for p in s1_minimal if p["type"].startswith("PARAM")]
    rng.shuffle(a_pairs)
    a_inc = [p for p in a_pairs if p["label"] == "inconsistent"]
    a_con = [p for p in a_pairs if p["label"] == "consistent"]
    n_a = 0
    for p in (a_inc[:75] + a_con[:75]):
        if n_a >= 150:
            break
        if add(p["premise"], p["hypothesis"], p["label"], "A", p["type"],
               "synth_s1", p.get("surface", ""), str(p.get("doc", ""))):
            n_a += 1

    # ── B族(80): bench ORDER+LOGIC-01~04, 质量过滤 ──
    b_types = {"ORDER_CONFLICT", "LOGIC-01", "LOGIC-02", "LOGIC-03", "LOGIC-04"}
    b_pairs = [x for x in bench if x.get("type") in b_types and is_clean_mutation(x["premise"], x["hypothesis"])]
    rng.shuffle(b_pairs)
    n_b = 0
    for x in b_pairs:
        if n_b >= 80:
            break
        if add(x["premise"], x["hypothesis"], x["label"], "B", x["type"], "gjb_bench"):
            n_b += 1

    # ── C族: 冻结金标(全部, 自然去重) + image P4(唯一对, 每图限量) ──
    n_c = 0
    for x in clean130 + md:
        typ = str(x.get("type", x.get("angle", {}).get("type", "C_RESIDUAL")) or "C_RESIDUAL")
        if x["premise"] and x["hypothesis"] and add(x["premise"], x["hypothesis"], x["label"], "C", typ,
                                                    "gold_frozen", "real"):
            n_c += 1
    p4 = [p for p in img if p["method"].startswith("P4")]
    rng.shuffle(p4)
    used_img = set()
    for p in p4:
        if p["doc"] in used_img:
            continue
        if add(p["premise"], p["hypothesis"], p["label"], "C",
               "DIAGRAM_EXTRA" if p["label"] == "inconsistent" else "P0_IDENTITY",
               "image_p4_visio", doc=p["doc"]):
            used_img.add(p["doc"])
            n_c += 1

    # ── D族(200): synth TERM/ENUM, 源级去重 ──
    d_pairs = [p for p in s1_minimal if p["type"].startswith(("TERM", "ENUM"))]
    rng.shuffle(d_pairs)
    d_inc = [p for p in d_pairs if p["label"] == "inconsistent"]
    d_con = [p for p in d_pairs if p["label"] == "consistent"]
    n_d = 0
    quota_d = {"inc": 100, "con": 100}
    ci = cc = 0
    for p in d_inc:
        if ci >= quota_d["inc"] or n_d >= 200:
            break
        if add(p["premise"], p["hypothesis"], p["label"], "D", p["type"],
               "synth_s1", p.get("surface", ""), str(p.get("doc", ""))):
            ci += 1
            n_d += 1
    for p in d_con:
        if cc >= quota_d["con"] or n_d >= 200:
            break
        if add(p["premise"], p["hypothesis"], p["label"], "D", p["type"],
               "synth_s1", p.get("surface", ""), str(p.get("doc", ""))):
            cc += 1
            n_d += 1

    # ── E族(70): bench GJB族, 质量过滤 ──
    e_pairs = [x for x in bench if str(x.get("type", "")).startswith("GJB")
               and is_clean_mutation(x["premise"], x["hypothesis"])]
    rng.shuffle(e_pairs)
    n_e = 0
    for x in e_pairs:
        if n_e >= 70:
            break
        if add(x["premise"], x["hypothesis"], x["label"], "E", x["type"], "gjb_bench"):
            n_e += 1

    # ── F族(150): κ_D语义残差 = P1_identity唯一对 + synth eval_minimal剩余(平衡) ──
    f_pairs = [p for p in img if p["method"] == "P1_identity"]
    rng.shuffle(f_pairs)
    used_f_img = set()
    n_f = 0
    for p in f_pairs:
        if p["doc"] in used_f_img:
            continue
        if add(p["premise"], p["hypothesis"], p["label"], "F", "P0_IDENTITY", "image_p1_identity", doc=p["doc"]):
            used_f_img.add(p["doc"])
            n_f += 1
    # synth剩余(A/D未消费的, 源级去重, 标签均衡补足)
    a_d_keys = {(x["premise"], x["hypothesis"]) for x in out}
    leftover = [p for p in s1_minimal
                if (p["premise"], p["hypothesis"]) not in a_d_keys]
    rng.shuffle(leftover)
    lo_inc = [p for p in leftover if p["label"] == "inconsistent"]
    lo_con = [p for p in leftover if p["label"] == "consistent"]
    target_f = 150
    need_inc = max(0, (target_f - n_f) // 2 - sum(1 for x in out if x["family"] == "F" and x["label"] == "inconsistent"))
    need_con = max(0, target_f - n_f - need_inc)
    for p in (lo_inc[:need_inc] + lo_con[:need_con]):
        if n_f >= target_f:
            break
        if add(p["premise"], p["hypothesis"], p["label"], "F", p["type"],
               "synth_s1_residual", p.get("surface", ""), str(p.get("doc", ""))):
            n_f += 1

    # ── 统计验证 ──
    fam_stats = Counter(x["family"] for x in out)
    label_by_fam = {f: dict(Counter(x["label"] for x in out if x["family"] == f))
                    for f in sorted(fam_stats)}
    type_stats = Counter(x["type"] for x in out)
    prov_stats = Counter(x["provenance"] for x in out)
    # 重复检查
    keys = [(x["premise"], x["hypothesis"]) for x in out]
    assert len(keys) == len(set(keys)), "存在重复对!"

    print(f"family_evalset_v1: {len(out)}条")
    print(f"族配额: {dict(sorted(fam_stats.items()))}")
    print(f"分族标签: {label_by_fam}")
    print(f"类型数: {len(type_stats)}个 → {dict(sorted(type_stats.items(), key=lambda x: -x[1])[:12])}")
    print(f"来源: {dict(sorted(prov_stats.items(), key=lambda x: -x[1]))}")

    outdata = {
        "meta": {
            "version": "family_evalset_v1", "date": "2026-10-14",
            "total": len(out),
            "设计": "六族(A/B/C/D/E/F)统一评测集, 源级去重+每图限量+全等去重",
            "配额": {"A": n_a, "B": n_b, "C": n_c, "D": n_d, "E": n_e, "F": n_f},
            "单标签族": "B/E族仅inconsistent(gold bench来源特性), 评测报TPR",
            "来源说明": {
                "gold_frozen": "clean130+md166冻结金标(真实, 双LLM+CoT裁决)",
                "synth_s1": "确定性枚举合成(每源每标签1条, 源级去重)",
                "gjb_bench": "旧benchmark的B/E族(词中注入已过滤)",
                "image_p4_visio": "Visio结构节点(L1真值), 每图限量",
                "image_p1_identity": "图元素重排(κ_D残差)",
                "synth_s1_residual": "eval_minimal未被A/D消费的剩余(κ_D语义残差)"}},
        "pairs": out,
    }
    out_path = G / "family_evalset_v1.json"
    out_path.write_text(json.dumps(outdata, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存 → {out_path}")


if __name__ == "__main__":
    main()
