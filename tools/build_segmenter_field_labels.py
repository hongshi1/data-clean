r"""P1-v2 Step 1 (103号规格): 切分器字段claim混合标签构造 — 蒸馏A_regex分解行为.

背景(B的P1桥接实验M123, 两层粒度契约): 教师原子claim=叙事粒度, typed
字段(ID/数值/枚举的原文span)在切分器O区——test46上5个含ID实例的
identifier span覆盖率0.0(模型输出侧口径, 46例桥接只抽出3条typed
claim); NLI能entail整句、不能entail原子. 修复在训练目标: 本脚本把
A_regex(algorithms/consistency/answer_claims.decompose_claims, typed
正则版)的分解行为构造成128M切分器的训练标签(纯编程, 零LLM零GPU).

混合策略(103号§Step 1, 按实例分层):
  - answer的typed正则命中(decompose_claims产出>=1条numeric/enum/
    identifier/quoted claim) -> field_distill: 标签=该typed claim集,
    span经"主语归位"重建为answer坐标的逐字区间;
  - 纯叙事实例(无typed命中) -> teacher_atom: 教师原子标签原样保留
    (叙事/句级粒度, 泛化能力).
  输出语料级claim集 = 字段claim(field_distill实例) + 句级叙事claim
  (teacher_atom实例), 满足两层契约(字段覆盖+命题完整)的训练目标.

主语归位(span坐标修复, M86口径"不信构造索引"): typed claim的构造文本
(如numeric的"attr op value unit")非answer逐字串——本脚本以正则match
区间为基点, 向左延伸纳入紧邻主语: 允许白空间+连接字(的/要求/应/为/
是/达到/保持)+括引号开符(（(「\"*), 间隙<=8字符; 主语不邻接则span=
字段match本身. claim文本一律=answer[span](字面契约, answer[span]
==text). identifier重复串按finditer逐次出现归属span(decompose的
find()定位会把重复ID折叠到首现位置, 逐次归属修复该坐标丢失).

对齐防御: 本脚本镜像decompose_claims的match顺序(prefix->postfix->
数值问句门控裸值), 每条claim与match按(operator,value,unit)核对,
漂移即抛ValueError(不静默错位).

输出(新文件, 默认不覆盖写, --force强制):
  - data/gjb_438c/distillation/segmenter_field_labels_v1.jsonl
    每行一个answer记录(与segmenter_train_v2.json#answers[]同构)
  - data/gjb_438c/distillation/segmenter_field_train_v1.json
    trainer可直接消费: python tools/train_claim_segmenter.py
    --train-data <该文件> --out models/segmenter/claim_segmenter_v3

记录schema: instance_id/question/answer/source(语料来源, 保持v2口径
供eval_claim_recognition.load_gold复用)/label_source(field_distill|
teacher_atom)/claims[{text,type,in_answer,find_span,+typed字段}]/
llm_status("ok", trainer的load_train_answers过滤依赖).

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/build_segmenter_field_labels.py            # 全量812实例
  python tools/build_segmenter_field_labels.py --force    # 强制重生成
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import (  # noqa: E402
    _ANSWER_NUMBER,
    _IDENTIFIER,
    _NUMERIC_POSTFIX,
    _NUMERIC_PREFIX,
    _NUMERIC_QUESTION_TERMS,
    _QUOTED,
    decompose_claims,
    extract_enum_claims,
    question_numeric_subject,
)
from algorithms.consistency.claim_segmenter_local import (  # noqa: E402
    char_labels_from_claims,
)

TRAIN_DATA = BASE / "data/gjb_438c/distillation/segmenter_train_v2.json"
OUT_JSONL = (BASE / "data/gjb_438c/distillation"
             / "segmenter_field_labels_v1.jsonl")
OUT_JSON = (BASE / "data/gjb_438c/distillation"
            / "segmenter_field_train_v1.json")

#: typed字段claim的kind集合(路由门: >=1条即field_distill)
TYPED_KINDS = frozenset({"numeric", "enum", "identifier", "quoted"})
#: 主语归位允许的连接字符: 白空间+后缀连接词(的要求应为是达到保持)+
#: 括引号开符. 句读分隔符(，。：:)不延伸——会打断命题连续性.
#: 观察自812训练answer: identifier间隙仅{为x5,（x2,"是 **"x1},
#: numeric后缀间隙=要求/应/为/是/达到/保持.
_REHOME_CONNECTORS = frozenset(" \t的要求应为是达到保持(（「\"*")
_REHOME_MAX_GAP = 8
#: identifier主语解析窗口(与decompose_claims的24字符前缀同口径)
_SUBJECT_WINDOW = 24


def _git_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=BASE, capture_output=True, text=True,
                              timeout=10, check=False)
        return proc.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


# ── 主语归位(纯函数) ─────────────────────────────────────────────────────────


def rehome_start(answer: str, match_start: int, attr: str) -> int:
    """字段match左端向左延伸纳入紧邻主语attr; 不邻接则原样返回match_start.

    严格邻接(answer[:match_start]以attr结尾)优先; 否则在
    [match_start-len(attr)-8, match_start)窗口内找attr最后一次出现,
    其与match之间的间隙必须全为连接字符(长度<=8).
    """
    if not attr:
        return match_start
    if answer[:match_start].endswith(attr):
        return match_start - len(attr)
    window_start = max(0, match_start - len(attr) - _REHOME_MAX_GAP)
    window = answer[window_start:match_start]
    pos = window.rfind(attr)
    if pos < 0:
        return match_start
    gap = window[pos + len(attr):]
    if (gap and len(gap) <= _REHOME_MAX_GAP
            and all(ch in _REHOME_CONNECTORS for ch in gap)):
        return window_start + pos
    return match_start


def _identifier_subject(answer: str, position: int) -> str:
    """镜像decompose_claims的identifier主语解析(在match位置解析)."""
    prefix = answer[max(0, position - _SUBJECT_WINDOW):position]
    cleaned = re.sub(r"[（(「\",，。：:为是*`_~]+", " ", prefix).rstrip()
    match = re.search(r"([\u4e00-\u9fffA-Za-z]{2,16})\s*$", cleaned)
    return match.group(1) if match else ""


# ── decompose_claims的match序列镜像(对齐防御) ───────────────────────────────


def _numeric_match_sequence(question: str,
                            answer: str) -> list[tuple[re.Match, str, str,
                                                       str]]:
    """镜像decompose_claims数值路径的match顺序及(op,value,unit)期望值.

    顺序: _NUMERIC_PREFIX -> _NUMERIC_POSTFIX(去prefix重叠) -> 数值问句
    门控裸值(唯一裸值+问句主语, 门控词表=模块常量_NUMERIC_QUESTION_TERMS).
    """
    sequence: list[tuple[re.Match, str, str, str]] = []
    prefix = list(_NUMERIC_PREFIX.finditer(answer))
    occupied = [m.span() for m in prefix]
    for match in prefix:
        sequence.append((match, match.group("op"), match.group("value"),
                         match.group("unit") or ""))
    for match in _NUMERIC_POSTFIX.finditer(answer):
        if any(match.start() < end and start < match.end()
               for start, end in occupied):
            continue
        op = "以上" if "以上" in match.group("op") else "以下"
        sequence.append((match, op, match.group("value"),
                         match.group("unit")))
    numeric_question = any(
        term in re.sub(r"\s+", "", question)
        for term in _NUMERIC_QUESTION_TERMS)
    if numeric_question:
        explicit = prefix + list(_NUMERIC_POSTFIX.finditer(answer))
        bare = [value for value in _ANSWER_NUMBER.finditer(answer)
                if not any(match.start() <= value.start()
                           and value.end() <= match.end()
                           for match in explicit)]
        subject = question_numeric_subject(question)
        if len(bare) == 1 and subject:
            value = bare[0]
            sequence.append((value, "为", value.group("value"),
                             value.group("unit")))
    return sequence


def _enum_cleaned_sequences(answer: str) -> list[list[str]]:
    """镜像decompose_claims的enum构claim路径(cleaned items序列)."""
    sequences: list[list[str]] = []
    for items in extract_enum_claims(answer):
        cleaned = [re.split(r"[，,]", item)[0].strip() for item in items]
        cleaned = [item for item in cleaned if len(item) >= 2]
        if len(cleaned) >= 2:
            sequences.append(cleaned)
    return sequences


def _locate_enum_items(answer: str,
                       cleaned: list[str]) -> tuple[int, int] | None:
    """cleaned items在answer内顺序定位 -> (首item起点, 末item终点).

    定位失败(某item非answer子串/乱序)返回None——该claim标记
    in_answer=False(与教师not-in-answer claims同构, trainer跳过).
    """
    cursor = 0
    first = -1
    last = -1
    for item in cleaned:
        pos = answer.find(item, cursor)
        if pos < 0:
            return None
        if first < 0:
            first = pos
        last = pos + len(item)
        cursor = last
    return (first, last) if first >= 0 else None


# ── 核心转换: (question, answer) -> 字段claim标签 ───────────────────────────


def _emit(out: list[dict], seen: set[tuple[str, tuple[int, int]]],
          kind: str, answer: str, span: tuple[int, int],
          extras: dict) -> None:
    """构造一条claim标签(字面契约: text=answer[span]), 按(kind,span)去重."""
    key = (kind, span)
    if key in seen:
        return
    seen.add(key)
    record = {
        "text": answer[span[0]:span[1]],
        "type": kind,
        "in_answer": True,
        "find_span": [span[0], span[1]],
        "fused": False,
    }
    record.update(extras)
    out.append(record)


def field_label_claims(question: str, answer: str) -> list[dict]:
    """(question, answer) -> typed字段claim标签列表(路由门: 空列表=叙事).

    行为=decompose_claims的typed输出(kind/主语/算子逐条对齐), span经
    主语归位重建为answer坐标逐字区间. 对齐漂移抛ValueError(不静默).
    """
    claims = decompose_claims(question, answer)
    typed = [c for c in claims if c.kind in TYPED_KINDS]
    if not typed:
        return []
    out: list[dict] = []
    seen: set[tuple[str, tuple[int, int]]] = set()

    # 1) numeric: match序列对齐(prefix->postfix->门控裸值)
    numeric_claims = [c for c in typed if c.kind == "numeric"]
    numeric_seq = _numeric_match_sequence(question, answer)
    if len(numeric_claims) != len(numeric_seq):
        raise ValueError(
            f"numeric对齐漂移: claims={len(numeric_claims)} "
            f"matches={len(numeric_seq)} answer={answer[:40]!r}")
    for claim, (match, op, value, unit) in zip(numeric_claims, numeric_seq):
        if (claim.operator, claim.value, claim.unit) != (op, value, unit):
            raise ValueError(
                f"numeric字段漂移: claim=({claim.operator},{claim.value},"
                f"{claim.unit}) match=({op},{value},{unit}) "
                f"answer={answer[:40]!r}")
        start = rehome_start(answer, match.start(), claim.attr)
        _emit(out, seen, "numeric", answer, (start, match.end()), {
            "attr": claim.attr, "operator": claim.operator,
            "value": claim.value, "unit": claim.unit,
            "field_span": [match.start(), match.end()],
            "subject_rehomed": start < match.start(),
        })

    # 2) quoted: 引号内容区间本身逐字
    quoted_claims = [c for c in typed if c.kind == "quoted"]
    quoted_matches = list(_QUOTED.finditer(answer))
    if len(quoted_claims) != len(quoted_matches):
        raise ValueError(
            f"quoted对齐漂移: claims={len(quoted_claims)} "
            f"matches={len(quoted_matches)} answer={answer[:40]!r}")
    for claim, match in zip(quoted_claims, quoted_matches):
        if claim.text != match.group(1):
            raise ValueError(
                f"quoted文本漂移: {claim.text!r} vs {match.group(1)!r}")
        span = (match.start(1), match.end(1))
        _emit(out, seen, "quoted", answer, span, {
            "negative": bool(claim.negative),
            "field_span": [span[0], span[1]],
            "subject_rehomed": False,
        })

    # 3) enum: items顺序定位, span=首item起点到末item终点(原文分隔符)
    enum_claims = [c for c in typed if c.kind == "enum"]
    enum_seq = _enum_cleaned_sequences(answer)
    if len(enum_claims) != len(enum_seq):
        raise ValueError(
            f"enum对齐漂移: claims={len(enum_claims)} "
            f"sequences={len(enum_seq)} answer={answer[:40]!r}")
    for claim, cleaned in zip(enum_claims, enum_seq):
        if claim.text != "、".join(cleaned):
            raise ValueError(
                f"enum文本漂移: {claim.text!r} vs {'、'.join(cleaned)!r}")
        span = _locate_enum_items(answer, cleaned)
        if span is None:
            # 不可定位: 构造文本保留(与教师not-in-answer同构), trainer跳过
            out.append({"text": claim.text, "type": "enum",
                        "in_answer": False, "find_span": None,
                        "fused": True, "items": cleaned})
            continue
        _emit(out, seen, "enum", answer, span, {
            "items": cleaned,
            "field_span": [span[0], span[1]],
            "subject_rehomed": False,
        })

    # 4) identifier: finditer逐次出现归属span(修复find()折叠重复ID)
    identifier_claims = [c for c in typed if c.kind == "identifier"]
    identifier_matches = list(_IDENTIFIER.finditer(answer))
    if len(identifier_claims) != len(identifier_matches):
        raise ValueError(
            f"identifier对齐漂移: claims={len(identifier_claims)} "
            f"matches={len(identifier_matches)} answer={answer[:40]!r}")
    for claim, match in zip(identifier_claims, identifier_matches):
        if claim.text != match.group(0):
            raise ValueError(
                f"identifier文本漂移: {claim.text!r} vs {match.group(0)!r}")
        subject = _identifier_subject(answer, match.start())
        start = rehome_start(answer, match.start(), subject)
        _emit(out, seen, "identifier", answer, (start, match.end()), {
            "attr": subject,
            "field_span": [match.start(), match.end()],
            "subject_rehomed": start < match.start(),
        })
    return out


# ── 实例路由 + 混合标签构造 ──────────────────────────────────────────────────


def sentence_label_claims(question: str,
                          answer: str) -> list[dict]:
    """(question, answer) -> 全量A_regex claim标签(v4实验, 103号原始设计).

    行为=蒸馏decompose_claims的完整输出: typed claim走field_label_claims
    的主语归位流程, 句级semantic claim按span逐字恢复(不可恢复find回退,
    都失败则in_answer=False由trainer跳过). 命题层修复: 叙事实例获得
    句级claim(教师原子→A_regex句级), NLI可entail的完整命题.
    """
    out = list(field_label_claims(question, answer))
    seen: set[tuple[str, tuple[int, int]]] = {
        (c["text"], tuple(c["find_span"]))
        for c in out if c.get("find_span")}
    for claim in decompose_claims(question, answer):
        if claim.kind in TYPED_KINDS:
            continue  # typed已由field_label_claims归位处理
        span: list[int] | None = None
        if claim.span is not None and (
                answer[claim.span[0]:claim.span[1]] == claim.text):
            span = [claim.span[0], claim.span[1]]
        else:
            idx = answer.find(claim.text)
            if idx >= 0:
                span = [idx, idx + len(claim.text)]
        key = (claim.text, tuple(span)) if span else (claim.text, ())
        if span and key in seen:
            continue
        if span:
            seen.add(key)
        out.append({"text": claim.text, "type": claim.kind,
                    "in_answer": span is not None,
                    "find_span": span, "fused": False})
    return out


def convert_instance(record: dict,
                     narrative_source: str = "teacher_atom") -> dict:
    """v2训练answer记录 -> 混合标签记录(field_distill | teacher_atom).

    typed命中且>=1条claim的span可用 -> field_distill(新标签);
    否则(纯叙事/typed全不可定位) -> teacher_atom(教师claims原样)或
    sentence(A_regex句级claim, v4实验的命题层修复).
    """
    question = str(record["question"])
    answer = str(record["answer"])
    if narrative_source == "sentence":
        claims = sentence_label_claims(question, answer)
        return {
            "instance_id": record["instance_id"],
            "question": question,
            "answer": answer,
            "source": record.get("source", ""),
            "label_source": "a_regex_full",
            "claims": claims,
            "llm_status": "ok",
            "llm_model": "deterministic:answer_claims.decompose_claims",
            "llm_calls": 0,
        }
    field_claims = field_label_claims(question, answer)
    if field_claims and any(c["in_answer"] for c in field_claims):
        return {
            "instance_id": record["instance_id"],
            "question": question,
            "answer": answer,
            "source": record.get("source", ""),
            "label_source": "field_distill",
            "claims": field_claims,
            "llm_status": "ok",
            "llm_model": "deterministic:answer_claims.decompose_claims",
            "llm_calls": 0,
        }
    label_record = dict(record)
    label_record["label_source"] = "teacher_atom"
    if field_claims:
        label_record["route_note"] = "field_distill_no_usable_span"
    return label_record


def build_mixed_labels(records: list[dict],
                       narrative_source: str = "teacher_atom"
                       ) -> list[dict]:
    """全部训练answer记录 -> 混合标签记录列表(确定性)."""
    return [convert_instance(rec, narrative_source) for rec in records]


# ── 统计与自检 ───────────────────────────────────────────────────────────────


def identifier_coverage(answer: str,
                        claim_spans: list[tuple[int, int]]) -> tuple[int, int]:
    """answer内ID正则span被claim span完整包含的(命中数, 总数)."""
    total = 0
    covered = 0
    for match in _IDENTIFIER.finditer(answer):
        total += 1
        start, end = match.span()
        if any(cs <= start and end <= ce for cs, ce in claim_spans):
            covered += 1
    return covered, total


def _coverage_block(answer_records: list[dict],
                    claim_field: str) -> dict:
    """含ID实例的identifier span覆盖率(按claim来源分块)."""
    covered = 0
    total = 0
    n_instances = 0
    by_source: dict[str, dict[str, int]] = {}
    for rec in answer_records:
        answer = str(rec["answer"])
        spans = [tuple(c[claim_field]) for c in rec["claims"]
                 if c.get("in_answer") and c.get(claim_field)]
        hit, n = identifier_coverage(answer, spans)
        if n == 0:
            continue
        n_instances += 1
        covered += hit
        total += n
        slot = by_source.setdefault(rec.get("source", "?"),
                                    {"covered": 0, "total": 0})
        slot["covered"] += hit
        slot["total"] += n
    return {"n_id_instances": n_instances, "covered": covered,
            "total": total,
            "rate": round(covered / total, 4) if total else None,
            "by_source": {k: {**v, "rate": round(v["covered"] / v["total"], 4)}
                          for k, v in sorted(by_source.items())
                          if v["total"]}}


def _literal_contract_audit(records: list[dict]) -> dict:
    """字面契约审计: 每条in_answer claim满足answer[span]==text."""
    checked = 0
    violations: list[dict] = []
    for rec in records:
        answer = str(rec["answer"])
        for claim in rec["claims"]:
            if not claim.get("in_answer"):
                continue
            checked += 1
            span = claim.get("find_span")
            if (not isinstance(span, list) or len(span) != 2
                    or not (0 <= span[0] < span[1] <= len(answer))
                    or answer[span[0]:span[1]] != claim.get("text")):
                violations.append({"instance_id": rec["instance_id"],
                                   "type": claim.get("type"),
                                   "text": str(claim.get("text"))[:50]})
    return {"n_checked": checked, "n_violations": len(violations),
            "violations": violations[:10]}


def _char_label_stats(records: list[dict]) -> dict:
    b = i = o = 0
    for rec in records:
        spans = [tuple(c["find_span"]) for c in rec["claims"]
                 if c.get("in_answer") and c.get("find_span")]
        labels = char_labels_from_claims(str(rec["answer"]), spans)
        b += labels.count("B")
        i += labels.count("I")
        o += labels.count("O")
    total = b + i + o
    return {"n_B": b, "n_I": i, "n_O": o,
            "B_ratio": round(b / total, 4) if total else 0.0,
            "I_ratio": round(i / total, 4) if total else 0.0,
            "O_ratio": round(o / total, 4) if total else 0.0}


def _claim_stats(records: list[dict]) -> dict:
    by_label: dict[str, dict[str, int]] = {}
    for rec in records:
        slot = by_label.setdefault(rec["label_source"],
                                   {"n_instances": 0, "n_claims": 0,
                                    "n_claims_in_answer": 0,
                                    "kinds": {}})
        slot["n_instances"] += 1
        slot["n_claims"] += len(rec["claims"])
        for claim in rec["claims"]:
            if claim.get("in_answer"):
                slot["n_claims_in_answer"] += 1
            kind = str(claim.get("type"))
            slot["kinds"][kind] = slot["kinds"].get(kind, 0) + 1
    for slot in by_label.values():
        slot["kinds"] = dict(sorted(slot["kinds"].items()))
    return by_label


def _self_check_samples(records: list[dict], n: int = 5) -> list[dict]:
    """抽n个field_distill实例做字面契约抽检(span界内+逐字一致)."""
    field_records = [r for r in records if r["label_source"] == "field_distill"]
    if not field_records:
        return []
    step = max(1, len(field_records) // n)
    picked = field_records[::step][:n]
    samples: list[dict] = []
    for rec in picked:
        answer = str(rec["answer"])
        claim_audits = []
        for claim in rec["claims"]:
            if not claim.get("in_answer"):
                continue
            span = claim["find_span"]
            verbatim = (0 <= span[0] < span[1] <= len(answer)
                        and answer[span[0]:span[1]] == claim["text"])
            claim_audits.append({"type": claim["type"],
                                 "text": claim["text"],
                                 "find_span": span,
                                 "verbatim": bool(verbatim)})
        samples.append({
            "instance_id": rec["instance_id"],
            "answer": answer,
            "n_claims": len(rec["claims"]),
            "claims": claim_audits,
            "all_verbatim": all(a["verbatim"] for a in claim_audits),
        })
    return samples


def compute_stats(train_records: list[dict],
                  label_records: list[dict]) -> dict:
    """构造统计: 路由分布/claim数/kind分布/字符标签/覆盖率/字面契约."""
    field_records = [r for r in label_records
                     if r["label_source"] == "field_distill"]
    # 同实例对照: field侧用新标签, teacher侧用v2原教师claims
    field_ids = {r["instance_id"] for r in field_records}
    teacher_same = [r for r in train_records
                    if r["instance_id"] in field_ids]
    n_rehomed = sum(1 for r in field_records for c in r["claims"]
                    if c.get("subject_rehomed"))
    return {
        "n_answers_total": len(label_records),
        "n_field_distill": len(field_records),
        "n_teacher_atom": len(label_records) - len(field_records),
        "n_route_fallback": sum(1 for r in label_records
                                if r.get("route_note")),
        "claims": _claim_stats(label_records),
        "subject_rehoming": {
            "n_claims_rehomed": n_rehomed,
            "connectors": "".join(sorted(_REHOME_CONNECTORS)),
            "max_gap": _REHOME_MAX_GAP,
        },
        "char_label_stats": _char_label_stats(label_records),
        "identifier_span_coverage": {
            "metric": ("answer内ID正则match span被>=1条claim find_span"
                       "完整包含的比例(含ID实例)"),
            "field_distill_labels": _coverage_block(field_records,
                                                    "find_span"),
            "teacher_labels_same_instances": _coverage_block(
                teacher_same, "find_span"),
            "reference_v2_segmenter_test46": {
                "rate": 0.0,
                "source": ("B/M123(claim_typed_bridge docstring): 模型输出"
                           "侧口径——v2切分器在test46的5个含ID实例上"
                           "identifier span覆盖率0.0"),
            },
        },
        "literal_contract": _literal_contract_audit(label_records),
    }


# ── 输出与CLI ────────────────────────────────────────────────────────────────


def _write_new(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"输出已存在(不覆盖写): {path} (用--force强制重生成)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_outputs(label_records: list[dict], meta: dict,
                  out_jsonl: Path, out_json: Path,
                  force: bool) -> None:
    """落盘jsonl(每行一记录)与trainer消费JSON({"meta","answers"})."""
    jsonl_text = "".join(
        json.dumps(rec, ensure_ascii=False) + "\n"
        for rec in label_records)
    _write_new(out_jsonl, jsonl_text, force)
    _write_new(out_json, json.dumps({"meta": meta, "answers": label_records},
                                    ensure_ascii=False, indent=1), force)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-data", type=Path, default=TRAIN_DATA,
                        help="输入: v2训练数据JSON(默认segmenter_train_v2"
                             ".json, 812 answer)")
    parser.add_argument("--out-jsonl", type=Path, default=OUT_JSONL)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--samples", type=int, default=5,
                        help="字面契约抽检的field_distill实例数")
    parser.add_argument("--narrative", choices=("teacher_atom", "sentence"),
                        default="teacher_atom",
                        help="叙事实例标签来源: teacher_atom(v1混合, "
                             "默认) | sentence(v4实验——A_regex句级claim, "
                             "103号原始设计的命题层修复)")
    parser.add_argument("--force", action="store_true",
                        help="输出文件已存在时强制覆盖(默认不覆盖写)")
    args = parser.parse_args()

    t0 = time.time()
    doc = json.loads(args.train_data.read_text(encoding="utf-8"))
    train_records = [rec for rec in doc["answers"]
                     if rec.get("llm_status") == "ok"]
    if not train_records:
        raise SystemExit(f"{args.train_data}无llm_status=ok训练answer")

    label_records = build_mixed_labels(train_records,
                                       narrative_source=args.narrative)
    stats = compute_stats(train_records, label_records)
    samples = _self_check_samples(label_records, args.samples)
    if samples and not all(s["all_verbatim"] for s in samples):
        raise SystemExit("字面契约抽检失败(见stdout样本), 拒绝落盘")

    meta = {
        "tool": "tools/build_segmenter_field_labels.py",
        "purpose": ("P1-v2 Step1(103号): 切分器字段claim混合标签——蒸馏"
                    "A_regex(typed正则)分解行为, 修复两层粒度契约"
                    "(字段覆盖+命题完整)的训练目标"),
        "spec": "docs/srs_project/103_p1v2_segmenter_field_claims_spec.md",
        "git_sha": _git_sha(),
        "ts": round(time.time(), 1),
        "train_data": str(args.train_data),
        "honest_contract": (
            "训练answer=dev45+violations17+crossdoc150+d3train600(812, "
            "继承segmenter_train_v2.json); test-46的answer禁止标注; "
            "P1-v2按实例路由混合标签: typed命中实例(field_distill)用"
            "decompose_claims的typed claim标签, 纯叙事实例(teacher_atom)"
            "教师原子标签原样保留; 两类实例集合与v2完全一致(零增删)"),
        "label_sources": {
            "field_distill": ("answer_claims.decompose_claims(typed正则) "
                              "的typed claim, span主语归位到answer坐标"),
            "teacher_atom": "v2教师原子claim原样(叙事/句级粒度, 泛化)",
        },
        "routing_rule": ("decompose_claims(question, answer)产出>=1条"
                         "kind∈{numeric,enum,identifier,quoted}的claim →"
                         " field_distill; 否则→teacher_atom"),
        "claim_schema": ("{text(=answer[find_span]逐字), type(kind), "
                         "in_answer, find_span, fused, +attr/operator/"
                         "value/unit(numeric), items(enum), negative"
                         "(quoted), field_span(字段match区间), "
                         "subject_rehomed}——teacher_atom记录与v2 claims"
                         "字段同构"),
        **stats,
        "self_check_samples": samples,
    }
    write_outputs(label_records, meta, args.out_jsonl, args.out_json,
                  args.force)

    print(f"answers={stats['n_answers_total']} "
          f"(field_distill={stats['n_field_distill']}, "
          f"teacher_atom={stats['n_teacher_atom']}, "
          f"route_fallback={stats['n_route_fallback']})")
    for label, slot in stats["claims"].items():
        print(f"  [{label}] instances={slot['n_instances']} "
              f"claims={slot['n_claims']} "
              f"in_answer={slot['n_claims_in_answer']} "
              f"kinds={slot['kinds']}")
    print(f"  subject_rehomed claims: "
          f"{stats['subject_rehoming']['n_claims_rehomed']}")
    print(f"  char_labels: {stats['char_label_stats']}")
    cov = stats["identifier_span_coverage"]
    print(f"  identifier coverage (field labels): "
          f"{cov['field_distill_labels']['covered']}/"
          f"{cov['field_distill_labels']['total']} = "
          f"{cov['field_distill_labels']['rate']}")
    print(f"  identifier coverage (teacher labels, same instances): "
          f"{cov['teacher_labels_same_instances']['covered']}/"
          f"{cov['teacher_labels_same_instances']['total']} = "
          f"{cov['teacher_labels_same_instances']['rate']}")
    print(f"  [reference] v2 segmenter test46: "
          f"{cov['reference_v2_segmenter_test46']['rate']} (B/M123)")
    lit = stats["literal_contract"]
    print(f"  literal contract: {lit['n_checked']} claims checked, "
          f"{lit['n_violations']} violations")
    for sample in samples:
        mark = "OK " if sample["all_verbatim"] else "FAIL"
        print(f"  [{mark}] {sample['instance_id']} "
              f"claims={sample['n_claims']}: {sample['answer'][:40]}")
        for audit in sample["claims"]:
            print(f"        {audit['type']:<10s} "
                  f"span={audit['find_span']} "
                  f"text={audit['text'][:36]}")
    print(f"输出: {args.out_jsonl}")
    print(f"      {args.out_json} (trainer: --train-data 直接可消费)")
    print(f"elapsed {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
