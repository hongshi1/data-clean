#!/usr/bin/env python3
"""功能谓词模式挖掘: 参数谓词(411条/3.3%) → 功能谓词白名单正则扩展.

动机: claim_slot_features 的 predicate_candidate 只覆盖参数词典23词
(分辨率/响应时间/...), 覆盖率3.3%. SRS里大量谓词是"动词+名词宾语"型
功能谓词("提供数据获取功能"/"支持格式转换服务"), 不在参数词典内.

方法(规则三段):
  1) FUNC_PRED 白名单正则(45动词): 动词 + 2~12字汉字宾语(惰性)
     + 后瞻(功能|服务|能力|模块|业务|标点|句尾);
  2) LIGHT 轻动词黑名单: 候选(动词或宾语)以 进行/使用/予以/加以/开展/通过/基于
     开头 → 跳过该候选, 继续找下一个匹配(宾语以轻动词/介词开头=宾语实为动词短语);
  3) 宾语剥后缀(功能/服务/能力/模块/业务)后 ≥2字才算; 应/能够/可以属MODAL层
     不计数(主语抽取时剥离, 不算谓词动词);
  一条claim只取第一个通过全部过滤的(谓词, 宾语).

slot_fill_rate 重算: 沿用 build_feature_matrix 的6槽位协议
(subject/predicate/operator/object_value/unit_raw/scope), 功能谓词填入
predicate 槽后重算填充率; parse_status = rate>=0.5 ? parsed : partial.

输入: data/gjb_438c/feature_matrix_v1/claim_slot_features.jsonl
输出: data/gjb_438c/predicate_mining_v1/{predicates.jsonl,summary.json,manifest.json}
用法: python tools/mine_function_predicates.py
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

INPUT_PATH = BASE / "data/gjb_438c/feature_matrix_v1/claim_slot_features.jsonl"
OUT_DIR = BASE / "data/gjb_438c/predicate_mining_v1"

FUNC_PRED_RE = re.compile(
    r"(提供|支持|包括|包含|实现|完成|具备|管理|配置|采集|获取|传输|接收|发送"
    r"|订阅|推送|解析|转换|处理|存储|显示|查询|检索|监控|监测|维护|校验|加密"
    r"|压缩|分发|汇聚|加载|记录|跟踪|追溯|切换|注册|登录|鉴权|编排|调度|部署"
    r"|备份|恢复|告警|统计)([\u4e00-\u9fff]{2,12}?)"
    r"(?=功能|服务|能力|模块|业务|[，。；、：]|$)"
)
LIGHT_VERB_RE = re.compile(r"^(进行|使用|予以|加以|开展|通过|基于)")

OBJECT_SUFFIXES: tuple[str, ...] = ("功能", "服务", "能力", "模块", "业务")

SLOT_FIELDS: tuple[str, ...] = (
    "subject_candidate",
    "predicate_candidate",
    "operator",
    "object_value",
    "unit_raw",
    "scope_candidate",
)
SUBJECT_SPLIT_RE = re.compile(r"[，。、；：,;:！？!?\s()（）\[\]【】]+")
SUBJECT_STRIP_CHARS = "的了之其应当必须须需可不宜将和与及能够"
CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9·．\-/]*")


def strip_object_suffix(object_raw: str) -> tuple[str, str]:
    """剥宾语后缀(功能/服务/能力/模块/业务), 只剥一次. 返回(剥后, 后缀)."""
    for suffix in OBJECT_SUFFIXES:
        if object_raw.endswith(suffix):
            return object_raw[: -len(suffix)], suffix
    return object_raw, ""


def subject_before(text: str, position: int) -> str:
    """谓词前置名词: 动词之前的最后一个≥2字CJK词块, 尾部剥MODAL/助词."""
    if position <= 0:
        return ""
    prefix = text[:position].strip()
    if not prefix:
        return ""
    segments = [seg for seg in SUBJECT_SPLIT_RE.split(prefix) if seg]
    tail = segments[-1] if segments else ""
    tail = tail.rstrip(SUBJECT_STRIP_CHARS)
    matches = CJK_RUN_RE.findall(tail)
    if not matches:
        return ""
    phrase = matches[-1]
    return phrase if len(phrase) >= 2 else ""


def mine_function_predicate(text: str) -> dict[str, Any] | None:
    """一条文本只取第一个通过 LIGHT/后缀长度过滤的 (动词, 宾语) 候选."""
    if not text:
        return None
    for match in FUNC_PRED_RE.finditer(text):
        verb = match.group(1)
        object_raw = match.group(2)
        if LIGHT_VERB_RE.match(verb) or LIGHT_VERB_RE.match(object_raw):
            continue
        object_stripped, suffix = strip_object_suffix(object_raw)
        if len(object_stripped) < 2:
            continue
        return {
            "verb": verb,
            "object_raw": object_raw,
            "object_stripped": object_stripped,
            "suffix": suffix,
            "span": [match.start(1), match.end(2)],
            "subject_preceding": subject_before(text, match.start(1)),
        }
    return None


def recompute_slots(row: dict[str, Any], predicate_value: str) -> dict[str, Any]:
    """6槽位重算: 功能谓词字符串填入 predicate_candidate 槽, 其余槽继承原行."""
    values: dict[str, Any] = {
        "subject_candidate": str(row.get("subject_candidate") or ""),
        "predicate_candidate": predicate_value,
        "operator": str(row.get("operator") or ""),
        "object_value": row.get("object_value"),
        "unit_raw": str(row.get("unit_raw") or ""),
        "scope_candidate": str(row.get("scope_candidate") or row.get("section") or ""),
    }
    filled: list[str] = []
    for field in SLOT_FIELDS:
        value = values[field]
        if value is not None and str(value).strip():
            filled.append(field)
    rate = round(len(filled) / len(SLOT_FIELDS), 4)
    return {
        "slot_fill_fields": filled,
        "slot_fill_rate": rate,
        "parse_status": "parsed" if rate >= 0.5 else "partial",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_output_row(row: dict[str, Any], mined: dict[str, Any]) -> dict[str, Any]:
    predicate_value = f"{mined['verb']}{mined['object_stripped']}"
    slots = recompute_slots(row, predicate_value)
    old_subject = str(row.get("subject_candidate") or "").strip()
    if old_subject:
        subject, subject_source = old_subject, "inherited"
    elif mined["subject_preceding"]:
        subject, subject_source = mined["subject_preceding"], "mined_preceding"
    else:
        subject, subject_source = "", ""
    return {
        "claim_id": row.get("claim_id"),
        "doc_id": row.get("doc_id"),
        "section": row.get("section"),
        "kind": row.get("kind"),
        "predicate_function": {
            "verb": mined["verb"],
            "object_raw": mined["object_raw"],
            "object_stripped": mined["object_stripped"],
            "suffix": mined["suffix"],
        },
        "predicate_key": f"func:{mined['verb']}{mined['object_stripped']}",
        "subject_candidate": subject,
        "subject_source": subject_source,
        "had_param_predicate": bool(str(row.get("predicate_candidate") or "").strip()),
        "slot_fill_fields": slots["slot_fill_fields"],
        "slot_fill_rate": slots["slot_fill_rate"],
        "parse_status": slots["parse_status"],
    }


def mine(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    verb_freq: Counter[str] = Counter()
    object_freq: Counter[str] = Counter()
    raw_match_claims = 0
    light_skipped = 0
    short_object_skipped = 0
    union_ids: set[str] = set()
    param_ids: set[str] = set()
    for row in rows:
        claim_id = str(row.get("claim_id") or "")
        if str(row.get("predicate_candidate") or "").strip():
            param_ids.add(claim_id)
        text = str(row.get("raw_text") or "")
        mined = mine_function_predicate(text)
        if mined is None:
            continue
        raw_match_claims += 1
        outputs.append(build_output_row(row, mined))
        verb_freq[mined["verb"]] += 1
        object_freq[mined["object_stripped"]] += 1
        union_ids.add(claim_id)
    for row in rows:
        text = str(row.get("raw_text") or "")
        for match in FUNC_PRED_RE.finditer(text):
            verb, object_raw = match.group(1), match.group(2)
            if LIGHT_VERB_RE.match(verb) or LIGHT_VERB_RE.match(object_raw):
                light_skipped += 1
                continue
            stripped, _ = strip_object_suffix(object_raw)
            if len(stripped) < 2:
                short_object_skipped += 1
                continue
            break
    union_ids |= param_ids
    stats = {
        "raw_match_claims": raw_match_claims,
        "light_verb_skipped_candidates": light_skipped,
        "short_object_skipped_candidates": short_object_skipped,
        "func_predicate_claims": len(outputs),
        "param_predicate_claims": len(param_ids),
        "overlap": sum(1 for r in outputs if r["had_param_predicate"]),
        "union_claims": len(union_ids),
        "verb_freq": verb_freq,
        "object_freq": object_freq,
    }
    return outputs, stats


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    rows = read_jsonl(INPUT_PATH)
    outputs, stats = mine(rows)
    total = len(rows)
    baseline = stats["param_predicate_claims"]
    overlap = stats["overlap"]
    union = stats["union_claims"]
    baseline_rate = round(baseline / total, 4) if total else 0.0
    union_rate = round(union / total, 4) if total else 0.0
    avg_before = round(
        sum(float(r.get("slot_fill_rate") or 0.0) for r in rows) / total, 4
    ) if total else 0.0
    avg_after = round(
        sum(float(r["slot_fill_rate"]) for r in outputs) / len(outputs), 4
    ) if outputs else 0.0
    summary = {
        "protocol": {
            "tool": "mine_function_predicates",
            "n_whitelist_verbs": 45,
            "light_verb_blacklist": ["进行", "使用", "予以", "加以", "开展", "通过", "基于"],
            "object_suffixes": list(OBJECT_SUFFIXES),
            "first_hit_only": True,
            "slot_fields": list(SLOT_FIELDS),
        },
        "total_claims": total,
        "param_predicate_claims": baseline,
        "baseline_coverage": baseline_rate,
        "func_predicate_claims": stats["func_predicate_claims"],
        "func_only_claims": stats["func_predicate_claims"] - overlap,
        "param_func_overlap": overlap,
        "union_claims": union,
        "union_coverage": union_rate,
        "coverage_gain_pp": round((union_rate - baseline_rate) * 100, 2),
        "regex_stage": {
            "raw_regex_match_claims": stats["raw_match_claims"],
            "raw_regex_coverage": round(stats["raw_match_claims"] / total, 4) if total else 0.0,
            "light_verb_skipped_candidates": stats["light_verb_skipped_candidates"],
            "short_object_skipped_candidates": stats["short_object_skipped_candidates"],
        },
        "verb_freq_top20": stats["verb_freq"].most_common(20),
        "object_freq_top20": stats["object_freq"].most_common(20),
        "slot_fill_rate_avg": {"before_all": avg_before, "after_mined": avg_after},
        "parse_status_parsed_after": sum(
            1 for r in outputs if r["parse_status"] == "parsed"
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    predicates_path = OUT_DIR / "predicates.jsonl"
    summary_path = OUT_DIR / "summary.json"
    write_jsonl(predicates_path, outputs)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    manifest = {
        "version": 1,
        "git_sha": None,
        "built_at": None,
        "inputs": {
            str(INPUT_PATH.relative_to(BASE)): {
                "bytes": INPUT_PATH.stat().st_size,
                "sha256": sha256_file(INPUT_PATH),
            }
        },
        "outputs": {
            "predicates.jsonl": {
                "bytes": predicates_path.stat().st_size,
                "sha256": sha256_file(predicates_path),
                "rows": len(outputs),
            },
            "summary.json": {
                "bytes": summary_path.stat().st_size,
                "sha256": sha256_file(summary_path),
            },
        },
    }
    run = open_run(
        "mine_function_predicates",
        {"input": str(INPUT_PATH.relative_to(BASE)), "n_verbs": 45},
    )
    manifest["git_sha"] = run.meta["git_sha"]
    manifest["built_at"] = run.meta["opened_at"]
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    run.save_result(summary)
    run.log(action="mined", total=total, func=stats["func_predicate_claims"], union=union)

    print("=" * 64)
    print("功能谓词模式挖掘 (白名单45动词 + LIGHT黑名单 + 后缀剥离)")
    print("=" * 64)
    print(f"  claims总数          : {total}")
    print(f"  原有参数谓词        : {baseline} ({baseline_rate:.2%})")
    print(f"  功能谓词新命中      : {stats['func_predicate_claims']}")
    print(f"    其中与参数谓词重叠: {overlap}")
    print(f"  并集覆盖            : {union} ({union_rate:.2%})  ← 基线 {baseline_rate:.2%}")
    print(f"  谓词覆盖率          : {baseline_rate:.2%} → {union_rate:.2%} "
          f"(+{summary['coverage_gain_pp']:.1f}pp)")
    print(f"  动词Top10           : {stats['verb_freq'].most_common(10)}")
    print(f"  宾语Top10           : {stats['object_freq'].most_common(10)}")
    print(f"  输出                : {OUT_DIR}")
    print(f"  运行记录            : {run.path}")


if __name__ == "__main__":
    main()
