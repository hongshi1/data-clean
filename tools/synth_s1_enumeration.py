r"""S1模板-槽位枚举合成(P1阶段): 从真实SRS表格chunks系统化枚举生成变异pair.

规范: docs/srs_project/pair_dataset_augmentation_plan.md §3.2(S1轨道, L1构造真值)
输入: data/gjb_438c/data_assets/chunks/srs_chunks.json (train文档table chunks)
      knowledge/srs_kb.json (参数族/单位族/接口词典)
输出: data/gjb_438c/synth_s1_pairs.json (对称1:1, 每概念对3表面T1/T2/T3)

领域等价约定域约定(标签=构造真值, 零LLM):
  inconsistent: 同参数不同值(PARAM-01) / 同实体换名(TERM-01) / 枚举成员替换(ENUM-01)
  consistent:   同参数同值换单位(PARAM-02) / 同值换操作符表述(PARAM-03)
                / 同实体同名(TERM-02) / 同枚举同成员(ENUM-02)
用法: python tools/synth_s1_enumeration.py
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
CHUNKS_PATH = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
KB_PATH = BASE / "knowledge/srs_kb.json"
OUT_PATH = BASE / "data/gjb_438c/synth_s1_pairs.json"

TRAIN_PREFIXES = ("01", "02", "05", "06", "08", "09", "10", "11", "12", "13", "14", "15", "16")
SEED = 20261013
MAX_CONTENT_LEN = 90
MAX_ENUM_ITEMS = 8
MAX_ENUM_LEN = 50
SURFACES = ("T1", "T2", "T3")

# ── 操作符族: (族, 中文同义词, 符号) ──
OP_FAMILIES: list[tuple[str, list[str], str]] = [
    (">=", ["不少于", "不小于", "不低于", "至少", "大于等于", "以上"], "≥"),
    ("<=", ["不多于", "不大于", "不高于", "不超过", "最多", "小于等于", "以下", "以内"], "≤"),
    (">", ["大于"], ">"),
    ("<", ["小于"], "<"),
    ("=", ["等于", "为"], "="),
]
WORD2FAM: dict[str, tuple[str, str]] = {w: (fam, sym) for fam, ws, sym in OP_FAMILIES for w in ws}
SYM2CANONWORD: dict[str, str] = {sym: ws[0] for fam, ws, sym in OP_FAMILIES}

# 单位归一(仅用于kb单位族查找; pair内容保留语料原单位表述)
UNIT_ALIAS = {
    "g": "GB", "G": "GB", "M": "MB", "K": "KB", "T": "TB",
    "秒": "s", "分钟": "min", "小时": "h", "毫秒": "ms", "微秒": "us",
    "字节": "byte",
}
CJK_UNITS = {
    "秒", "分钟", "小时", "天", "种", "个", "核", "路", "张", "颗", "条", "层",
    "字", "位", "帧", "页", "类", "次", "倍", "兆", "档", "级", "米", "字符",
    "条/秒", "次/秒", "帧/秒", "路/秒", "条/分",
}
NATURAL_UNIT_MAXLEN = 4
UNNATURAL_UNITS = {"sec", "msec", "hour", "percent", "hertz", "watt", "volt",
                   "bit", "bits", "Kb", "Mb", "Gb", "Bps"}  # 含bit/byte混族单位, 等效对中禁用
POST_WORDS = {"以上", "以下", "以内"}

# 参数名前导填充词(循环剥离)
LEADING_WORDS = (
    "考查系统", "考查", "进行", "支持", "提供", "采用", "使用", "具备", "需要",
    "要求", "完成", "实现", "配置", "达到", "将", "把", "该", "本", "以", "得到", "的",
)
BAD_PARAM_TAIL = set("的了在是和与或及等")

TAG_RE = re.compile(r"<[^>]+>")
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CAPTION_RE = re.compile(r"\[表格标题[^\]]*\]")

_OP_ALT = "|".join(sorted((w for _, ws, _ in OP_FAMILIES for w in ws), key=len, reverse=True))
P_NUM_PRE = re.compile(
    r"([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9]{1,11}?)(?:的)?(" + _OP_ALT + r")"
    r"\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z%]{1,6}|[\u4e00-\u9fa5]{1,2}(?:/[\u4e00-\u9fa5]{1,2})?)?"
)
P_NUM_POST = re.compile(
    r"([\u4e00-\u9fa5][\u4e00-\u9fa5A-Za-z0-9]{1,11}?)\s*([0-9]+(?:\.[0-9]+)?)"
    r"\s*([a-zA-Z%]{1,4})?\s*(以上|以下|以内)"
)
P_ENUM = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9]{2,8}(?:、[\u4e00-\u9fa5A-Za-z0-9]{2,8}){2,})")
P_NAME_ID = re.compile(r"([\u4e00-\u9fa5][\u4e00-\u9fa5A-Za-z0-9]{2,23})\s*/\s*([A-Z][A-Z0-9-]{7,})")
P_ID_LIKE = re.compile(r"[A-Z0-9-]{5,}")


@dataclass
class Constraint:
    """数值约束: (参数, 操作符, 值, 单位) + 语料锚点."""

    doc: str
    section: str
    chunk_id: str
    param: str
    op_family: str
    op_word: str
    val: str
    unit: str
    content: str
    source: str


@dataclass
class ConceptualPair:
    """概念对: 变异真值 + 内容槽(全量表述/短语表述) + 语料锚点."""

    label: str
    typ: str
    operator: str
    doc: str
    section: str
    chunk_id: str
    source: str
    content_p: str
    content_h: str
    short_p: str = ""
    short_h: str = ""

    def __post_init__(self) -> None:
        if not self.short_p:
            self.short_p = self.content_p
        if not self.short_h:
            self.short_h = self.content_h


@dataclass
class DocContext:
    """文档级渲染资源: 主体名 + 表格锚点序列(用于侧/位置槽)."""

    subject: str
    refs: list[dict[str, str]] = field(default_factory=list)


def plain_text(table_html: str) -> str:
    txt = CAPTION_RE.sub(" ", table_html)
    txt = TAG_RE.sub(" ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def table_rows(table_html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in ROW_RE.findall(table_html):
        cells = [re.sub(r"\s+", " ", TAG_RE.sub(" ", c)).strip() for c in CELL_RE.findall(tr)]
        if any(cells):
            rows.append(cells)
    return rows


def cell_texts(table_html: str) -> list[str]:
    return [re.sub(r"\s+", " ", TAG_RE.sub(" ", m)).strip() for m in CELL_RE.findall(table_html)]


def clean_param(raw: str) -> str:
    p = raw.strip()
    changed = True
    while changed and p:
        changed = False
        for w in LEADING_WORDS:
            if p.startswith(w) and len(p) - len(w) >= 2:
                p = p[len(w):]
                changed = True
                break
    while p.endswith("的") and len(p) > 2:
        p = p[:-1]
    return p


def param_ok(p: str) -> bool:
    return len(p) >= 2 and p[-1] not in BAD_PARAM_TAIL and not P_ID_LIKE.fullmatch(p)


def unit_ok(u: str) -> str:
    if not u:
        return ""
    if re.fullmatch(r"[a-zA-Z%]{1,6}", u) or u in CJK_UNITS:
        return u
    return ""


def clamp_str(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def phrase(param: str, op_word: str, val: str, unit: str) -> str:
    """约束规范陈述: 后缀词(以上/以下/以内)置尾, 其余操作符置前."""
    if op_word in POST_WORDS:
        return f"{param}{val}{unit}{op_word}"
    return f"{param}{op_word}{val}{unit}"

def shift_value(val_str: str) -> str | None:
    """PARAM-01数值变异: 小值×2, 大值÷2(整数保持整数), 不可变异返回None."""
    v = float(val_str)
    if v == 0:
        return None
    if v == int(v):
        n = int(v)
        n2 = n * 2 if abs(n) < 100 else n // 2
        if n2 == n:
            n2 = n + 1
        if n2 == 0:
            return None
        out = str(n2)
    else:
        v2 = v * 2 if abs(v) < 100 else v / 2
        out = f"{v2:g}"
        if "e" in out or "E" in out:
            return None
    return out if out != val_str else None


def load_unit_families(kb: dict[str, Any]) -> list[dict[str, float]]:
    fams: list[dict[str, float]] = []
    for spec in kb.get("unit_dictionary", {}).values():
        conv = {u: float(c) for u, c in spec.get("conversions", {}).items()}
        if conv:
            fams.append(conv)
    return fams


def natural_family_units(conv: dict[str, float]) -> list[str]:
    return [
        u for u in conv
        if u.isascii() and len(u) <= NATURAL_UNIT_MAXLEN
        and u not in UNNATURAL_UNITS and (u.isalnum() or u == "%")
    ]


def unit_equiv(val_str: str, unit: str, fams: list[dict[str, float]]) -> tuple[str, str] | None:
    """PARAM-02单位等效: 同族内找换算值最整洁的表述, 找不到返回None."""
    norm = UNIT_ALIAS.get(unit, unit)
    conv = next((fc for fc in fams if norm in fc), None)
    if conv is None:
        return None
    v = float(val_str)
    base = v * conv[norm]
    best: tuple[str, str] | None = None
    for u2 in natural_family_units(conv):
        if u2 == norm:
            continue
        v2 = base / conv[u2]
        if v2 < 0.1:  # 换算后过小(如3秒→0.05min)的表述不自然, 跳过
            continue
        s = f"{v2:.6g}"
        if "e" in s or "E" in s or len(s) > 7:
            continue
        if abs(float(s) - v2) > 1e-9 * max(abs(v2), 1.0):
            continue
        if best is None or (len(s), u2) < (len(best[0]), best[1]):
            best = (s, u2)
    return best


def mine_constraints(chunks: list[dict[str, Any]]) -> list[Constraint]:
    """步骤1a: 挖掘数值约束 (P1前缀操作符 / P2后缀操作符 / P4数据描述表)."""
    out: list[Constraint] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    def add(doc: str, section: str, cid: str, param: str, fam: str, word: str,
            val: str, unit: str, content: str, src: str) -> None:
        key = (doc, param, fam, val, unit)
        if key in seen or not param_ok(param) or len(content) > MAX_CONTENT_LEN:
            return
        seen.add(key)
        out.append(Constraint(doc, section, cid, param, fam, word, val, unit, content, src))

    for c in chunks:
        doc, section, cid = c["doc"], str(c.get("section", "")), c["chunk_id"]
        flat = plain_text(c["text"])
        for m in P_NUM_PRE.finditer(flat):  # P1: 参数+操作符+数值[单位]
            param = clean_param(m.group(1))
            word, val, unit = m.group(2), m.group(3), unit_ok(m.group(4) or "")
            fam, sym = WORD2FAM[word]
            add(doc, section, cid, param, fam, word, val, unit,
                phrase(param, word, val, unit), clamp_str(m.group(0), 70))
        for m in P_NUM_POST.finditer(flat):  # P2: 参数+数值[单位]+以上/以下/以内
            param = clean_param(m.group(1))
            val, unit, post = m.group(2), unit_ok(m.group(3) or ""), m.group(4)
            fam = WORD2FAM[post][0]
            add(doc, section, cid, param, fam, post, val, unit,
                phrase(param, post, val, unit), clamp_str(m.group(0), 70))
        rows = table_rows(c["text"])  # P4: 数据描述表(数据项/最大值/最小值/单位)
        if not rows:
            continue
        header = rows[0]
        idx = {"name": None, "mx": None, "mn": None, "unit": None}
        for j, h in enumerate(header):
            if "最大值" in h:
                idx["mx"] = j
            elif "最小值" in h:
                idx["mn"] = j
            elif ("数据项" in h or "名称" in h) and idx["name"] is None:
                idx["name"] = j
            elif "单位" in h:
                idx["unit"] = j
        if None in (idx["mx"], idx["mn"], idx["name"]):
            continue
        need = max(idx["mx"], idx["mn"], idx["name"])
        for row in rows[1:]:
            if len(row) <= need:
                continue
            name = row[idx["name"]].strip()
            mx = row[idx["mx"]].strip()
            if not name or len(name) > 12 or not re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", mx):
                continue
            if not re.fullmatch(r"[\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9]{1,11}", name):
                continue
            unit = ""
            if idx["unit"] is not None and idx["unit"] < len(row):
                unit = unit_ok(row[idx["unit"]].strip())
            src = clamp_str(f"{name} 最大值{mx} 最小值{row[idx['mn']]} 单位{unit}", 70)
            add(doc, section, cid, name, "<=", "不超过", mx, unit,
                phrase(name, "不超过", mx, unit), src)
            mn = row[idx["mn"]].strip()
            if re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", mn):
                add(doc, section, cid, name, ">=", "不小于", mn, unit,
                    phrase(name, "不小于", mn, unit), src)
    return out


def trim_enum_items(items: list[str]) -> list[str] | None:
    """枚举边界去胶: 首项剥离引导动词尾缀, 末项截断'的'后成分, 长度方差超限返回None."""
    glue_verbs = ("具备", "包括", "提供", "支持", "进行", "完成", "使用", "采用", "描述")
    first = items[0]
    for v in glue_verbs:
        pos = first.rfind(v)
        if pos >= 0 and len(first) - pos - len(v) >= 2:
            first = first[pos + len(v):]
            break
    last = items[-1]
    for cut in ("的", "等"):
        pos = last.find(cut)
        if pos >= 2:
            last = last[:pos]
            break
    out = [first] + items[1:-1] + [last] if len(items) > 2 else [first, last]
    if any(not 2 <= len(x) <= 8 for x in out):
        return None
    if max(len(x) for x in out) - min(len(x) for x in out) > 4:
        return None
    return out


def mine_enums(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """步骤1b: 挖掘顿号枚举列表(单元格内, 闭式无'等', 边界去胶+方差过滤)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for c in chunks:
        doc, section, cid = c["doc"], str(c.get("section", "")), c["chunk_id"]
        for cell in cell_texts(c["text"]):
            for m in P_ENUM.finditer(cell):
                raw = m.group(1)
                if "等" in raw:
                    continue
                items = trim_enum_items(raw.split("、"))
                if items is None or not 3 <= len(items) <= MAX_ENUM_ITEMS:
                    continue
                raw_clean = "、".join(items)
                if len(raw_clean) > MAX_ENUM_LEN or any(P_ID_LIKE.search(x) for x in items):
                    continue
                if (doc, raw_clean) in seen:
                    continue
                seen.add((doc, raw_clean))
                out.append({"doc": doc, "section": section, "chunk_id": cid,
                            "items": items, "raw": raw_clean,
                            "cell": clamp_str(cell, 70)})
    return out


def mine_name_ids(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """步骤1c: 挖掘'功能名称/标识符'对(同一实体的两种指称)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for c in chunks:
        doc, section, cid = c["doc"], str(c.get("section", "")), c["chunk_id"]
        for cell in cell_texts(c["text"]):
            for m in P_NAME_ID.finditer(cell):
                name, eid = m.group(1).strip(), m.group(2).strip()
                if len(name) < 3 or len(eid) < 8:
                    continue
                if (doc, name, eid) in seen:
                    continue
                seen.add((doc, name, eid))
                out.append({"doc": doc, "section": section, "chunk_id": cid,
                            "name": name, "id": eid, "cell": clamp_str(cell, 70)})
    return out


def short_doc_name(doc: str) -> str:
    s = re.sub(r"^\d+", "", doc)
    for suffix in ("软件需求规格说明-终稿", "软件需求规格说明-终端",
                   "需求规格说明-终稿", "需求规格说明-终端", "需求规格说明"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return s.strip() or doc


def build_doc_contexts(chunks: list[dict[str, Any]]) -> dict[str, DocContext]:
    """文档级锚点序列: (caption引用, 章节号, chunk_id), 用于侧/位置槽填充."""
    ctxs: dict[str, DocContext] = {}
    for c in chunks:
        doc = c["doc"]
        if doc not in ctxs:
            ctxs[doc] = DocContext(subject=short_doc_name(doc))
        caption = str(c.get("table_caption", "") or "").replace(" ", "")
        section = str(c.get("section", "") or "")
        ref = caption[:18] if caption else (f"第{section}节" if section else "其他章节")
        ctxs[doc].refs.append({"ref": ref, "section": section or "其他章节",
                               "chunk_id": c["chunk_id"]})
    return ctxs


def side_slots(ctx: DocContext, chunk_id: str, section: str) -> tuple[str, str, str, str]:
    """为源chunk选(侧A, 侧B, 位置A, 位置B), 保证B≠A(跨章节对照)."""
    refs = ctx.refs
    k = next((i for i, r in enumerate(refs) if r["chunk_id"] == chunk_id), 0)
    side_a = refs[k]["ref"] if k < len(refs) else "该表格"
    loc_a = f"第{section}节" if section else "其他章节"
    side_b, loc_b = "", ""
    for step in range(1, len(refs) + 1):
        r = refs[(k + step) % len(refs)]
        if not side_b and r["ref"] != side_a:
            side_b = r["ref"]
        if not loc_b and r["section"] != (section or "其他章节"):
            loc_b = f"第{r['section']}节"
        if side_b and loc_b:
            break
    return side_a, side_b or "其他章节", loc_a, loc_b or "其他章节"


def render_surfaces(pair: ConceptualPair, ctx: DocContext) -> list[tuple[str, str, str]]:
    """步骤3: T1/T2/T3三种受控表面(标签感知)."""
    side_a, side_b, loc_a, loc_b = side_slots(ctx, pair.chunk_id, pair.section)
    subj = ctx.subject
    cp, ch, sp, sh = pair.content_p, pair.content_h, pair.short_p, pair.short_h
    if pair.label == "inconsistent":
        t1 = (f"{subj}的{side_a}包含「{sp}」。",
              f"{subj}的{side_b}中没有「{sp}」，对应内容为「{sh}」。")
    else:
        t1 = (f"{subj}的{side_a}包含「{sp}」。",
              f"{subj}的{side_b}中包含「{sh}」。")
    t2 = (f"{subj}的{side_a}规定：{cp}。", f"{subj}的{side_b}规定：{ch}。")
    t3 = (f"文档《{subj}》{loc_a}记载：{cp}。", f"文档《{subj}》{loc_b}记载：{ch}。")
    return [(name, p, h) for name, (p, h) in zip(SURFACES, (t1, t2, t3), strict=True)
            if p != h]


def build_conceptuals(
    constraints: list[Constraint],
    enums: list[dict[str, Any]],
    name_ids: list[dict[str, Any]],
    kb: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> list[ConceptualPair]:
    """步骤2: 对称变异(每个inconsistent构造配对consistent格点)."""
    pairs: list[ConceptualPair] = []
    fams = load_unit_families(kb)

    # 参数同义词族(TERM-01/02的语料锚定来源): 同义词→首选异名
    syn_map: dict[str, str] = {}
    for spec in kb.get("param_dictionary", {}).values():
        names = [spec.get("canonical_cn", "")] + list(spec.get("synonyms_cn", []))
        for n in names:
            alts = [x for x in names if x and x != n]
            if n and alts:
                syn_map[n] = alts[0]

    def term_alt(param: str) -> str:
        if param in syn_map:
            return syn_map[param]
        for s in sorted(syn_map, key=len, reverse=True):
            if len(s) >= 2 and param.endswith(s) and len(param) > len(s):
                return param[: -len(s)] + syn_map[s]
        return ""

    for c in constraints:
        base = dict(doc=c.doc, section=c.section, chunk_id=c.chunk_id, source=c.source)
        val2 = shift_value(c.val)  # PARAM-01: 同参数不同值 ⇒ inconsistent
        if val2 is not None:
            pairs.append(ConceptualPair(
                label="inconsistent", typ="PARAM-01", operator="param_shift",
                content_p=c.content, content_h=phrase(c.param, c.op_word, val2, c.unit), **base))
        equiv = unit_equiv(c.val, c.unit, fams)  # PARAM-02: 同值换单位 ⇒ consistent
        if equiv is not None:
            val_u, unit2 = equiv
            ch = phrase(c.param, c.op_word, val_u, unit2)
            if ch != c.content:
                pairs.append(ConceptualPair(
                    label="consistent", typ="PARAM-02", operator="unit_equiv",
                    content_p=c.content, content_h=ch, **base))
        # PARAM-03: 同值换操作符表述(中文词↔符号) ⇒ consistent
        if c.op_word in WORD2FAM:
            alt = WORD2FAM[c.op_word][1]
        else:
            alt = SYM2CANONWORD.get(c.op_word, "")
        if alt:
            ch = phrase(c.param, alt, c.val, c.unit)
            if ch != c.content:
                pairs.append(ConceptualPair(
                    label="consistent", typ="PARAM-03", operator="op_reword",
                    content_p=c.content, content_h=ch, **base))
        # TERM-01: 同参数约束换同义术语 ⇒ inconsistent; TERM-02: 同名 ⇒ consistent
        alt_term = term_alt(c.param)
        if alt_term and alt_term not in c.content:
            pairs.append(ConceptualPair(
                label="inconsistent", typ="TERM-01", operator="term_swap",
                content_p=c.content,
                content_h=c.content.replace(c.param, alt_term, 1), **base))
            pairs.append(ConceptualPair(
                label="consistent", typ="TERM-02", operator="term_same",
                content_p=c.content, content_h=c.content, **base))

    for i, ni in enumerate(name_ids):  # 功能名/标识符 → TERM-01/02
        base = dict(doc=ni["doc"], section=ni["section"], chunk_id=ni["chunk_id"],
                    source=ni["cell"])
        pairs.append(ConceptualPair(
            label="inconsistent", typ="TERM-01", operator="term_swap",
            content_p=f"该功能记为「{ni['name']}」", content_h=f"该功能记为「{ni['id']}」",
            short_p=ni["name"], short_h=ni["id"], **base))
        same = ni["id"] if i % 2 else ni["name"]
        pairs.append(ConceptualPair(
            label="consistent", typ="TERM-02", operator="term_same",
            content_p=f"该功能记为「{same}」", content_h=f"该功能记为「{same}」",
            short_p=same, short_h=same, **base))

    # 接口词典: 语料出现的canonical↔变体 → TERM-01/02 (每文档×接口取首个出现锚点)
    for key, spec in kb.get("interface_dictionary", {}).items():
        canon = str(spec.get("canonical", key))
        variants = [v for v in spec.get("variants", []) if v and v != canon]
        if not variants:
            continue
        anchored: set[str] = set()
        for c in chunks:
            if c["doc"] in anchored or canon not in plain_text(c["text"]):
                continue
            anchored.add(c["doc"])
            base = dict(doc=c["doc"], section=str(c.get("section", "")),
                        chunk_id=c["chunk_id"], source=f"接口词典「{canon}」(语料出现)")
            cp, ch = f"通信协议采用「{canon}」", f"通信协议采用「{variants[0]}」"
            pairs.append(ConceptualPair(
                label="inconsistent", typ="TERM-01", operator="term_swap",
                content_p=cp, content_h=ch,
                short_p=canon, short_h=variants[0], **base))
            pairs.append(ConceptualPair(
                label="consistent", typ="TERM-02", operator="term_same",
                content_p=cp, content_h=cp, short_p=canon, short_h=canon, **base))

    # 枚举列表 → ENUM-01/02(替换成员取自同文档其他枚举)
    enums_by_doc: dict[str, list[dict[str, Any]]] = {}
    for e in enums:
        enums_by_doc.setdefault(e["doc"], []).append(e)
    for doc, doc_enums in enums_by_doc.items():
        for i, e in enumerate(doc_enums):
            items = e["items"]
            repl = ""
            for step in range(1, len(doc_enums) + 1):
                for x in doc_enums[(i + step) % len(doc_enums)]["items"]:
                    if x not in items:
                        repl = x
                        break
                if repl:
                    break
            if not repl:
                continue
            mutated = items.copy()
            mutated[1 if len(items) >= 3 else 0] = repl
            raw_h = "、".join(mutated)
            if raw_h == e["raw"]:
                continue
            base = dict(doc=doc, section=e["section"], chunk_id=e["chunk_id"],
                        source=e["cell"])
            pairs.append(ConceptualPair(
                label="inconsistent", typ="ENUM-01", operator="enum_swap",
                content_p=f"包括{e['raw']}", content_h=f"包括{raw_h}",
                short_p=e["raw"], short_h=raw_h, **base))
            pairs.append(ConceptualPair(
                label="consistent", typ="ENUM-02", operator="enum_same",
                content_p=f"包括{e['raw']}", content_h=f"包括{e['raw']}",
                short_p=e["raw"], short_h=e["raw"], **base))
    return pairs


def balance_groups(
    groups: list[tuple[ConceptualPair, list[tuple[str, str, str]]]],
) -> list[tuple[ConceptualPair, list[tuple[str, str, str]]]]:
    """公理A5对称构造: 渲染去重后精确1:1(按族优先级确定性下采样, 整组丢弃)."""
    rng = random.Random(SEED)
    inc = sum(1 for p, _ in groups if p.label == "inconsistent")
    cons = sum(1 for p, _ in groups if p.label == "consistent")
    if inc == cons:
        return groups
    majority = "consistent" if cons > inc else "inconsistent"
    excess = abs(cons - inc)
    order = ["PARAM-03", "ENUM-02", "PARAM-02", "TERM-02", "PARAM-01", "ENUM-01", "TERM-01"]
    pool = [i for i, (p, _) in enumerate(groups) if p.label == majority]
    drop: set[int] = set()
    for typ in order:
        if excess <= 0:
            break
        typed = [i for i in pool if groups[i][0].typ == typ and i not in drop]
        take = min(excess, len(typed))
        drop.update(rng.sample(typed, take))
        excess -= take
    out = [g for i, g in enumerate(groups) if i not in drop]
    labs = Counter(p.label for p, _ in out)
    assert labs["inconsistent"] == labs["consistent"], f"平衡失败: {labs}"
    return out


def render_groups(
    pairs: list[ConceptualPair], ctxs: dict[str, DocContext],
) -> tuple[list[tuple[ConceptualPair, list[tuple[str, str, str]]]], dict[str, int]]:
    """步骤3: 表面编译(3表面/对) → 退化/重复组剔除(整组丢弃保证表面对称)."""
    groups: list[tuple[ConceptualPair, list[tuple[str, str, str]]]] = []
    seen: set[tuple[str, str, str]] = set()
    stats = {"groups_total": len(pairs), "groups_kept": 0,
             "groups_partial": 0, "groups_dedup": 0}
    for p in pairs:
        ctx = ctxs.get(p.doc)
        if ctx is None or not ctx.refs:
            stats["groups_partial"] += 1
            continue
        surfaces = render_surfaces(p, ctx)
        if len(surfaces) != len(SURFACES):
            stats["groups_partial"] += 1
            continue
        if any((ph, hh, p.label) in seen for _, ph, hh in surfaces):
            stats["groups_dedup"] += 1
            continue
        for _, ph, hh in surfaces:
            seen.add((ph, hh, p.label))
        stats["groups_kept"] += 1
        groups.append((p, surfaces))
    return groups, stats


def flatten_entries(
    groups: list[tuple[ConceptualPair, list[tuple[str, str, str]]]],
) -> list[dict[str, Any]]:
    """步骤4: 条目化(每概念对3条表面条目)."""
    entries: list[dict[str, Any]] = []
    for p, surfaces in groups:
        for name, ph, hh in surfaces:
            entries.append({
                "id": "", "premise": ph, "hypothesis": hh, "label": p.label,
                "type": p.typ, "surface": name, "doc": p.doc, "section": p.section,
                "operator": p.operator, "source_constraint": p.source,
                "chunk_id": p.chunk_id,
            })
    for i, e in enumerate(entries, 1):
        e["id"] = f"S1-{i:04d}"
    return entries


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
    tables = [c for c in chunks if c["type"] == "table" and c["doc"][:2] in TRAIN_PREFIXES]
    assert tables, "train文档table chunks为空"

    constraints = mine_constraints(tables)
    enums = mine_enums(tables)
    name_ids = mine_name_ids(tables)
    print(f"约束挖掘: 数值约束{len(constraints)} | 枚举列表{len(enums)} | 名称/标识对{len(name_ids)}")

    ctxs = build_doc_contexts(tables)
    conceptuals = build_conceptuals(constraints, enums, name_ids, kb, tables)
    print(f"概念对: {len(conceptuals)} {dict(Counter(p.label for p in conceptuals))}")

    groups, stats = render_groups(conceptuals, ctxs)
    groups = balance_groups(groups)
    print(f"渲染组: {stats}")
    print(f"渲染组(平衡后): {len(groups)} {dict(Counter(p.label for p, _ in groups))}")

    entries = flatten_entries(groups)
    assert len(entries) >= 1500, f"产出不足1500条: {len(entries)}"
    assert all(e["premise"] != e["hypothesis"] for e in entries), "存在退化对P==H"
    labs = Counter(e["label"] for e in entries)
    surfs = Counter(e["surface"] for e in entries)
    types = Counter(e["type"] for e in entries)
    assert labs["inconsistent"] == labs["consistent"], f"标签失衡: {labs}"
    assert set(surfs) == set(SURFACES) and len(set(surfs.values())) == 1, f"表面失衡: {surfs}"
    leaked = {e["doc"][:2] for e in entries} - set(TRAIN_PREFIXES)
    assert not leaked, f"泄漏文档: {leaked}"

    meta = {
        "total": len(entries),
        "method": "S1_enumeration",
        "sources": "train SRS table chunks (01/02/05/06/08-16, 13 docs) + knowledge/srs_kb.json",
        "seed": SEED,
        "deterministic": True,
        "label_semantics": (
            "领域等价约定构造真值(零LLM): 同参数不同值/同实体换名/枚举换成员⇒inconsistent; "
            "同值换单位或操作符表述/同名同枚举⇒consistent"),
        "label_balance": dict(labs),
        "by_type": dict(sorted(types.items())),
        "by_surface": dict(surfs),
        "extraction": {"numeric_constraints": len(constraints), "enum_lists": len(enums),
                       "name_id_pairs": len(name_ids), "table_chunks": len(tables), **stats},
        "excluded_docs": ["03", "04", "07"],
    }
    OUT_PATH.write_text(
        json.dumps({"meta": meta, "pairs": entries}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"保存 → {OUT_PATH} (共{len(entries)}条: {dict(labs)}, 表面{dict(surfs)})")
    print(f"类型分布: {dict(sorted(types.items()))}")
    shown: set[str] = set()
    for lab in ("inconsistent", "consistent"):
        for typ in sorted(types):
            for surf in SURFACES:
                sample = next((e for e in entries if e["label"] == lab
                               and e["type"] == typ and e["surface"] == surf), None)
                if sample and (typ, lab, surf) not in shown:
                    shown.add((typ, lab, surf))
                    print(f"[{typ}/{lab}/{surf}] {sample['premise']}")
                    print(f"    ⇔ {sample['hypothesis']}")


if __name__ == "__main__":
    main()
