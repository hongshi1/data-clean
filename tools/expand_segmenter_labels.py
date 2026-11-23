r"""Step2: 教师分解数据扩充 — d3_train前600条answer的GLM-5.3教师claim标注.

复用tools/probe_llm_decomposer.py的prompt构造(逐字节相同, cache-key兼容),
对data/gjb_438c/distillation/d3_train_instances_v1.jsonl的前600条answer
生成教师原子claim分解(每条约10-30s, 全磁盘缓存).

断点续跑: 增量落盘data/gjb_438c/distillation/segmenter_train_d3_600.jsonl,
每次调用成功后立即append; 重跑时读取已标注instance_id并跳过(API失败不丢进度).
网络类失败: 等60秒重试一次, 再失败则显式记录后继续(不静默).

诚实契约: d3_train_instances与test-46(dev_test_split_v1.json#test)零交集
(启动时显式断言); dev45/violations17/crossdoc150也断言无重复.

合并: 现有212条(segmenter_train_v1.json) + 新600条 →
segmenter_train_v2.json(同schema, claims经_normalize_claims统一find_span).

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/expand_segmenter_labels.py --slice 0:150  # 分批API(防超时)
  python tools/expand_segmenter_labels.py                # 全量续跑→合并写v2 JSON
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from tools.probe_llm_decomposer import (
    _EXTRA_PAYLOAD,
    _MAX_TOKENS,
    _RETRY_SUFFIX,
    _SYSTEM,
    _TEMPERATURE,
    _build_prompt,
    _fused,
    _parse_llm_claims,
)
from tools.llm_teacher import llm_json_teacher

BASE = Path(__file__).resolve().parents[1]
SPLIT_PATH = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
D3_TRAIN = BASE / "data/gjb_438c/distillation/d3_train_instances_v1.jsonl"
INCREMENTAL = BASE / "data/gjb_438c/distillation/segmenter_train_d3_600.jsonl"
TRAIN_V1 = BASE / "data/gjb_438c/distillation/segmenter_train_v1.json"
OUT_V2 = BASE / "data/gjb_438c/distillation/segmenter_train_v2.json"

N_TARGET = 600
RETRY_WAIT_SECONDS = 60
SOURCE = "d3train"


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE,
                           capture_output=True, text=True, timeout=10,
                           check=False)
        return r.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def _d3_records() -> list[dict]:
    """d3_train前600条 → 待标注记录(顺序稳定, 断点续跑一致)."""
    records: list[dict] = []
    with D3_TRAIN.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            records.append({"instance_id": str(rec["instance_id"]),
                            "question": str(rec["question"]),
                            "answer": str(rec["answer"]),
                            "source": SOURCE})
            if len(records) >= N_TARGET:
                break
    if len(records) < N_TARGET:
        raise ValueError(f"d3_train可用记录{len(records)}<{N_TARGET}")
    return records


def _assert_honest_contract(records: list[dict]) -> None:
    """显式断言: 待标注池与test-46零交集, 且与既有训练池零重复."""
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    test_ids = set(split["test"])
    overlap_test = [r["instance_id"] for r in records
                    if r["instance_id"] in test_ids]
    if overlap_test:
        raise SystemExit(f"诚实契约违反: 待标注池含test-46实例: {overlap_test}")
    v1 = json.loads(TRAIN_V1.read_text(encoding="utf-8"))
    v1_ids = {a["instance_id"] for a in v1["answers"]}
    overlap_v1 = [r["instance_id"] for r in records
                  if r["instance_id"] in v1_ids]
    if overlap_v1:
        raise SystemExit(f"与既有212条训练answer重复: {overlap_v1}")


def _load_done() -> dict[str, dict]:
    """增量JSONL → 已标注记录(instance_id去重, 保留最后一条)."""
    done: dict[str, dict] = {}
    if INCREMENTAL.exists():
        for line in INCREMENTAL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            done[rec["instance_id"]] = rec
    return done


def _annotate_with_retry(rec: dict) -> dict:
    """一次教师标注; 网络类失败等60s重试一次, 再失败显式记录."""
    prompt = _build_prompt(rec["question"], rec["answer"])
    llm_claims: list[dict] | None = None
    status = "unparseable"
    cache_hit = False
    n_calls = 0
    model = ""
    waited = 0
    for attempt in (1, 2):
        for suffix in ("", _RETRY_SUFFIX):
            try:
                payload, model, hit = llm_json_teacher(
                    prompt + suffix, _SYSTEM, max_tokens=_MAX_TOKENS,
                    temperature=_TEMPERATURE, extra_payload=_EXTRA_PAYLOAD)
            except Exception as exc:
                status = f"error: {type(exc).__name__}: {exc}"
                break
            n_calls += 1
            status = "unparseable"
            if hit:
                cache_hit = True
            parsed = _parse_llm_claims(payload, rec["answer"])
            if parsed is not None:
                llm_claims = parsed
                status = "ok"
                break
        if status == "ok":
            break
        if attempt == 1:
            waited = RETRY_WAIT_SECONDS
            print(f"  … {rec['instance_id']} 失败({status}), "
                  f"等{RETRY_WAIT_SECONDS}s后重试")
            time.sleep(RETRY_WAIT_SECONDS)
    return {"instance_id": rec["instance_id"],
            "question": rec["question"], "answer": rec["answer"],
            "source": rec["source"], "llm_claims": llm_claims,
            "llm_status": status, "llm_model": model,
            "llm_cache_hit": cache_hit, "llm_calls": n_calls,
            "retry_wait_seconds": waited}


def _append_incremental(rec: dict) -> None:
    INCREMENTAL.parent.mkdir(parents=True, exist_ok=True)
    with INCREMENTAL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _normalize_claims(claims: list[dict] | None,
                      answer: str) -> list[dict]:
    """教师claims → 统一训练claim记录(find()定位区间, M86: 不信教师索引)."""
    out: list[dict] = []
    for c in claims or []:
        text = c["text"]
        pos = answer.find(text)
        in_answer = pos != -1
        out.append({
            "text": text,
            "type": c.get("type", "semantic"),
            "in_answer": in_answer,
            "find_span": [pos, pos + len(text)] if in_answer else None,
            "teacher_span": c.get("span"),
            "teacher_span_exact": bool(c.get("span_exact")),
            "fused": _fused(text),
        })
    return out


def _parse_slice(spec: str) -> tuple[int, int]:
    try:
        start_s, end_s = spec.split(":")
        start, end = int(start_s), int(end_s)
    except ValueError as exc:
        raise SystemExit(f"--slice格式应为 START:END, 收到: {spec!r}") from exc
    if start < 0 or end <= start:
        raise SystemExit(f"--slice区间非法: {spec!r}")
    return start, end


def annotate(args: argparse.Namespace) -> None:
    records = _d3_records()
    _assert_honest_contract(records)
    done = _load_done()
    pending: list[dict] = []
    for pos, rec in enumerate(records):
        if rec["instance_id"] in done:
            continue
        if args.slice:
            start, end = _parse_slice(args.slice)
            if not (start <= pos < end):
                continue
        pending.append(rec)
    print(f"d3_train目标{N_TARGET}条: 已标注{len(done)}, "
          f"本次待跑{len(pending)}"
          + (f"(切片{args.slice})" if args.slice else ""))
    t0 = time.time()
    n_new_api = 0
    n_cache = 0
    for idx, rec in enumerate(pending, 1):
        inst = _annotate_with_retry(rec)
        _append_incremental(inst)
        n_new_api += inst["llm_calls"] - (1 if inst["llm_cache_hit"] else 0)
        n_cache += 1 if inst["llm_cache_hit"] else 0
        elapsed = time.time() - t0
        eta = elapsed / idx * (len(pending) - idx) if idx else 0.0
        print(f"[{idx}/{len(pending)}] {inst['instance_id']} "
              f"claims={len(inst['llm_claims'] or [])} "
              f"cache={inst['llm_cache_hit']} {inst['llm_status']} "
              f"(elapsed {elapsed:.0f}s, ETA {eta:.0f}s)",
              flush=True)
    failures = [k for k, v in _load_done().items() if v["llm_status"] != "ok"]
    print(f"\n本次: 新API调用{n_new_api}, 缓存命中{n_cache}; "
          f"累计失败{len(failures)}条{(['; '] + failures) if failures else ''}")


def _label_stats(answer_records: list[dict]) -> dict:
    b = i = o = 0
    for rec in answer_records:
        labels = char_labels(rec["answer"], rec["claims"])
        b += labels.count("B")
        i += labels.count("I")
        o += labels.count("O")
    total = b + i + o
    return {"n_B": b, "n_I": i, "n_O": o,
            "B_ratio": round(b / total, 4) if total else 0.0,
            "I_ratio": round(i / total, 4) if total else 0.0,
            "O_ratio": round(o / total, 4) if total else 0.0}


def char_labels(answer: str, claims: list[dict]) -> list[str]:
    """claim find区间 → B/I/O字符标签(重叠claim按起点序, B不被I覆盖)."""
    labels = ["O"] * len(answer)
    spans = sorted(c["find_span"] for c in claims
                   if c.get("in_answer") and c["find_span"])
    for start, end in spans:
        if 0 <= start < end <= len(answer):
            labels[start] = "B"
            for k in range(start + 1, min(end, len(answer))):
                if labels[k] != "B":
                    labels[k] = "I"
    return labels


def merge() -> None:
    """212条v1 + d3train增量 → segmenter_train_v2.json(同schema)."""
    v1 = json.loads(TRAIN_V1.read_text(encoding="utf-8"))
    answer_records = [a for a in v1["answers"]]
    done = _load_done()
    records = _d3_records()
    _assert_honest_contract(records)
    missing = [r["instance_id"] for r in records
               if r["instance_id"] not in done]
    if missing:
        print(f"警告: {len(missing)}条尚未标注(先跑annotate), "
              f"只合并已标注部分")
    for rec in records:
        inst = done.get(rec["instance_id"])
        if inst is None:
            continue
        answer_records.append({
            "instance_id": inst["instance_id"],
            "question": inst["question"], "answer": inst["answer"],
            "source": inst["source"],
            "claims": _normalize_claims(inst["llm_claims"], inst["answer"]),
            "llm_status": inst["llm_status"], "llm_model": inst["llm_model"],
            "llm_cache_hit": inst["llm_cache_hit"],
            "llm_calls": inst["llm_calls"]})
    ok = [r for r in answer_records if r["llm_status"] == "ok"]
    all_claims = [c for r in ok for c in r["claims"]]
    n_in = sum(1 for c in all_claims if c["in_answer"])
    src_counts: dict[str, int] = {}
    for r in answer_records:
        src_counts[r["source"]] = src_counts.get(r["source"], 0) + 1
    n_new_api = sum(a.get("llm_calls", 0) - (1 if a.get("llm_cache_hit") else 0)
                    for a in answer_records if a["source"] == SOURCE)
    failures = [{"instance_id": k, "status": v["llm_status"]}
                for k, v in done.items() if v["llm_status"] != "ok"]
    doc = {
        "meta": {
            "tool": "tools/expand_segmenter_labels.py",
            "purpose": ("D2切分器v2训练数据: v1的212条 + d3_train前600条"
                        "GLM-5.3教师原子claim标注(文本切分蒸馏, M86: 不蒸索引)"),
            "git_sha": _git_sha(), "ts": round(time.time(), 1),
            "honest_contract": ("训练answer=dev45+violations17+crossdoc150"
                                "+d3train600; test-46的answer禁止标注, "
                                "启动断言0交集; 断点续跑"
                                "(segmenter_train_d3_600.jsonl增量落盘)"),
            "n_answers_total": len(answer_records),
            "n_answers_ok": len(ok),
            "n_claims": len(all_claims),
            "n_claims_in_answer": n_in,
            "n_claims_not_in_answer": len(all_claims) - n_in,
            "claims_fused_rate": round(
                sum(1 for c in all_claims if c["fused"]) / len(all_claims), 4)
            if all_claims else 0.0,
            "n_api_calls_new_d3train": n_new_api,
            "llm_failures": failures,
            "char_label_scheme": {"B": "claim首字符", "I": "claim内部",
                                  "O": "未覆盖"},
            "char_label_stats": _label_stats(ok),
            "sources": dict(sorted(src_counts.items())),
            "source_paths": {
                "v1_212": str(TRAIN_V1),
                "d3train600": str(D3_TRAIN),
                "incremental": str(INCREMENTAL)},
            "prompt_reuse": ("byte-identical import from "
                             "tools/probe_llm_decomposer.py (_SYSTEM/"
                             "_JSON_SPEC/_build_prompt/_EXTRA_PAYLOAD) "
                             "— cache-key兼容"),
        },
        "answers": answer_records,
    }
    OUT_V2.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"合并完成: answers={len(answer_records)} (ok={len(ok)}) "
          f"claims={len(all_claims)} failures={len(failures)}")
    print(f"sources: {doc['meta']['sources']}")
    print(f"char_labels: {doc['meta']['char_label_stats']}")
    print(f"输出: {OUT_V2}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", default=None,
                        help="只跑待标注切片(如 0:150), 分批API调用防超时")
    parser.add_argument("--annotate-only", action="store_true",
                        help="只跑标注不合并")
    args = parser.parse_args()
    annotate(args)
    if not args.annotate_only:
        merge()


if __name__ == "__main__":
    main()
