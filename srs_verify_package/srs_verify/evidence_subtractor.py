"""证据减法模块: 从召回证据池删除坏证据并做粒度归一.

对应文档: 70号设计(三谓词合取). 勘验对应: 物证预检——剔除与本案无关
检材(scope)、拆解过粗检材(粒度)、剔除无实质内容的载体(形态).

三过滤器:
  F1 scope:  证据须与问题/答案共享锚点(PZXQ式ID/英文词/中文4-gram)
             → 否则删 scope_mismatch (Dong式错误scope干扰证据)
  F2 粒度:   表格HTML→表头:值配对的行语句; 长文本→句级切分
             → NLI只吃句/行级单元 (SumMaC: 文档级直入失效)
  F3 形态:   纯指针文本("见表X所示")无实质内容 → 删 shape_violation

设计: 纯确定性(零模型零I/O); 护栏=全删时回退保序.
"""
from __future__ import annotations

import re
from typing import Mapping, Sequence

# PZXQ式项目唯一标识符 / 通用大写连字ID
_ID_PATTERN = re.compile(r"[A-Z][A-Z0-9]{1,}(?:-[A-Z0-9]+){1,}")
# 英文词(≥3字符)
_ASCII_WORD = re.compile(r"[A-Za-z]{3,}")
# 中文连续段
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
# 指针文本(见表X所示/见表/见图)且短 → 无实质内容
_POINTER = re.compile(r"(?:见\s*表\s*\d+\s*所示|见\s*表|如下表|见\s*图)")
# HTML标签剥离
_TAG = re.compile(r"<[^>]+>")
# 表格行/单元格(捕获到闭合标签, 兼容<td><p>嵌套)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
# 句子边界
_SENT = re.compile(r"[。；！？\n]+")

# 粒度界(70号F2: NLI可消费性=句级原子性)
_MAX_ATOMIC_CHARS = 160
_MAX_STATEMENTS = 25

# 通用词停用(中文4-gram过松时的降噪兜底, 不参与锚点)
_STOP_4GRAM = set()


def _clean_cell(raw: str) -> str:
    return _TAG.sub("", raw).replace("\u3000", " ").strip()


def extract_anchors(*texts: str) -> set[str]:
    """从问题/答案提取scope锚点: ID式标识符 + 英文词 + 中文4-gram."""
    anchors: set[str] = set()
    for text in texts:
        anchors.update(_ID_PATTERN.findall(text))
        anchors.update(w.lower() for w in _ASCII_WORD.findall(text))
        for run in _CJK_RUN.findall(text):
            anchors.update(run[i:i + 4] for i in range(len(run) - 3))
    return {a for a in anchors if a not in _STOP_4GRAM}


def _anchor_hits(text: str, anchors: set[str]) -> int:
    """锚点命中数(大小写不敏感: 锚点已小写, 文本同步小写)."""
    low = text.lower()
    return sum(1 for a in anchors if a in low)


def split_table_rows(html: str) -> list[str]:
    """表格HTML→行语句. 表头行+数据行配对为"表头：值"(与EvidenceUnit约定一致)."""
    rows = _TR.findall(html)
    if not rows:
        cell = _clean_cell(html)
        return [cell] if cell else []
    parsed: list[list[str]] = []
    for tr in rows:
        cells = [_clean_cell(c) for c in _TD.findall(tr)]
        cells = [c for c in cells if c]
        if cells:
            parsed.append(cells)
    if not parsed:
        return [_clean_cell(html)] if _clean_cell(html) else []
    header = parsed[0]
    out: list[str] = []
    for cells in parsed[1:]:
        if len(cells) == len(header) and len(header) > 1:
            out.append("；".join(f"{h}：{c}" for h, c in zip(header, cells)))
        else:
            out.append("，".join(cells))
    return out or ["，".join(parsed[0])]


def normalize_granularity(text: str) -> dict:
    """粒度归一(F2): 证据→{class, statements}.

    class: table_rows(表格行化) | sentences(句切) | atomic(原本可消费)
    """
    if "<tr" in text or "<table" in text:
        return {"class": "table_rows", "statements": split_table_rows(text)}
    if len(text) <= _MAX_ATOMIC_CHARS and len(_SENT.split(text)) <= 2:
        return {"class": "atomic", "statements": [text.strip()] if text.strip() else []}
    sents = [s.strip() for s in _SENT.split(text) if s.strip()]
    return {"class": "sentences", "statements": sents or ([text.strip()] if text.strip() else [])}


def _is_pointer(text: str) -> bool:
    return bool(_POINTER.search(text)) and len(text) < 60


def subtract(question: str, answer: str,
             evidence: Sequence[Mapping],
             max_statements: int = _MAX_STATEMENTS) -> dict:
    """减法主入口: (question, answer, 证据块列表) → EvidencePack.

    EvidencePack = {
      kept:   [{evidence_id, statements, granularity_class, anchor_hits,
                stage_pass, provenance}],
      removed:[{evidence_id, stage, reason_code, detail}],
      stats:  {n_in, n_kept, n_removed, by_reason, fallback}
    }
    护栏:
      F1若删光全部证据 → 回退保留全部(记fallback), 只做F2/F3.
      ID豁免: 问题/答案含PZXQ式ID时(标识符类检测项), 含ID的证据块
              不做scope删除——多实体ID比较所需的证据天然不含查询词.
      指针豁免: 指针文本若命中锚点(交叉引用型gold)不删.
    """
    anchors = extract_anchors(question, answer)
    q_has_id = bool(_ID_PATTERN.search(question) or _ID_PATTERN.search(answer))
    kept: list[dict] = []
    removed: list[dict] = []

    # F1 scope过滤(整块级; ID豁免)
    scope_pass: list[Mapping] = []
    for ev in evidence:
        text = str(ev.get("text", ""))
        hits = _anchor_hits(text, anchors)
        id_exempt = q_has_id and bool(_ID_PATTERN.search(text))
        if anchors and hits == 0 and not id_exempt:
            removed.append({
                "evidence_id": ev.get("evidence_id", ""),
                "stage": "F1", "reason_code": "scope_mismatch",
                "detail": f"与问题/答案无共享锚点(锚点{len(anchors)}个)",
            })
        else:
            scope_pass.append(ev)
    fallback = False
    if evidence and not scope_pass:
        fallback = True
        scope_pass = list(evidence)
        removed = [r for r in removed if r["stage"] != "F1"]

    # F3形态 + F2粒度(对scope存活块)
    for ev in scope_pass:
        text = str(ev.get("text", ""))
        eid = ev.get("evidence_id", "")
        if _is_pointer(text) and _anchor_hits(text, anchors) == 0:
            removed.append({
                "evidence_id": eid, "stage": "F3",
                "reason_code": "shape_violation.pointer",
                "detail": f"纯指针文本且无锚点命中({len(text)}字)",
            })
            continue
        norm = normalize_granularity(text)
        if not norm["statements"]:
            removed.append({
                "evidence_id": eid, "stage": "F3",
                "reason_code": "shape_violation.empty",
                "detail": "归一后无实质语句",
            })
            continue
        kept.append({
            "evidence_id": eid,
            "statements": norm["statements"],
            "granularity_class": norm["class"],
            "anchor_hits": _anchor_hits(text, anchors),
            "stage_pass": "F1+F2" + ("+F3" if norm["class"] != "atomic" else ""),
            "provenance": ev.get("scope_id", ev.get("source_ref", "")),
        })

    # 语句预算: 超max时按语句级锚点命中排序(高命中优先, 同分保原序)
    total = sum(len(k["statements"]) for k in kept)
    if total > max_statements:
        flat: list[tuple[int, str, str]] = []
        for k in kept:
            for s in k["statements"]:
                flat.append((_anchor_hits(s, anchors), s, k["evidence_id"]))
        flat.sort(key=lambda x: -x[0])
        picked: dict[str, list[str]] = {}
        for hits, s, eid in flat[:max_statements]:
            picked.setdefault(eid, []).append(s)
        for k in kept:
            k["statements"] = picked.get(k["evidence_id"], [])
        kept = [k for k in kept if k["statements"]]

    by_reason: dict[str, int] = {}
    for r in removed:
        by_reason[r["reason_code"]] = by_reason.get(r["reason_code"], 0) + 1
    return {
        "kept": kept,
        "removed": removed,
        "stats": {
            "n_in": len(evidence), "n_kept": len(kept),
            "n_removed": len(removed),
            "n_statements": sum(len(k["statements"]) for k in kept),
            "by_reason": by_reason, "fallback": fallback,
        },
    }
