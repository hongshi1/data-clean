r"""D2 Step1: 教师原子claim标注扩充 → 切分器训练数据.

复用tools/probe_llm_decomposer.py的prompt构造(逐字节相同: 同_SYSTEM/
_JSON_SPEC/_build_prompt/参数, cache-key兼容), 标注:
  - violations-17 (data/gjb_438c/localization_gold/violation_evalset_v1.jsonl)
  - crossdoc-150  (data/gjb_438c/qa_frozen/crossdoc{05,06,07,08,10}_evalset_v1.jsonl)
合并dev-45已有教师标注(llm_decomposer_probe_v1.json, 直接复用claims) →
212个训练answer, 落盘data/gjb_438c/distillation/segmenter_train_v1.json.

诚实契约: test-46(dev_test_split_v1.json#test)的answer禁止标注
(脚本显式断言0交集; dev45标注为probe期遗留, 训练可见).

M86结论: 蒸馏目标=原子claim文本切分(不蒸索引)——教师区间43%错但文本
100%是answer子串; 故训练信号=claim文本的find()定位区间→字符标签.

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/distill_segmenter_labels.py --slice 0:15   # 分批API(防超时)
  python tools/distill_segmenter_labels.py                # 全量(缓存秒回)→写JSON
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from algorithms.consistency.eval_lib import load_frozen_qa
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
PROBE_PATH = BASE / "data/gjb_438c/distillation/llm_decomposer_probe_v1.json"
VIOLATIONS_PATH = (BASE / "data/gjb_438c/localization_gold"
                   / "violation_evalset_v1.jsonl")
CROSSDOC_DOCS = ("05", "06", "07", "08", "10")
CROSSDOC_DIR = BASE / "data/gjb_438c/qa_frozen"
OUT_PATH = BASE / "data/gjb_438c/distillation/segmenter_train_v1.json"

#: 字符标签体系(B/I/O), 训练与推理端(tools/claim_segmenter.py)共享:
#:   B=claim首字符, I=claim内部(非首), O=未被任何claim覆盖
LABEL_B, LABEL_I, LABEL_O = "B", "I", "O"


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _new_records() -> list[dict]:
    """violations-17 + crossdoc-150 → 待标注实例(question/answer/instance_id/source)."""
    out: list[dict] = []
    for rec in _read_jsonl(VIOLATIONS_PATH):
        out.append({"instance_id": str(rec["instance_id"]),
                    "question": str(rec["question"]),
                    "answer": str(rec["answer"]), "source": "violations17"})
    for doc in CROSSDOC_DOCS:
        rows = _read_jsonl(CROSSDOC_DIR / f"crossdoc{doc}_evalset_v1.jsonl")
        if len(rows) != 30:
            raise ValueError(f"crossdoc{doc}子集应30条, 实际{len(rows)}")
        for rec in rows:
            out.append({"instance_id": str(rec["instance_id"]),
                        "question": str(rec["question"]),
                        "answer": str(rec["answer"]),
                        "source": f"crossdoc{doc}"})
    if len(out) != 167:
        raise ValueError(f"新标注实例应167条(17+150), 实际{len(out)}")
    return out


def _dev45_records() -> list[dict]:
    """dev-45教师claims直接从probe JSON复用(不再调API)."""
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    qa = {r["instance_id"]: r for r in load_frozen_qa()}
    out: list[dict] = []
    for inst in probe["instances"]:
        iid = inst["instance_id"]
        if iid not in dev_ids:  # 冗余防御: probe只跑过dev
            continue
        out.append({"instance_id": iid,
                    "question": qa[iid]["question"],
                    "answer": inst["answer"], "source": "dev45",
                    "llm_claims": inst["llm_claims"],
                    "llm_status": inst["llm_status"],
                    "llm_cache_hit": True, "llm_calls": 0,
                    "llm_model": inst.get("llm_model", "")})
    if len(out) != 45:
        raise ValueError(f"dev45复用实例应45条, 实际{len(out)}")
    return out


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


def _annotate(rec: dict) -> dict:
    """一次GLM教师标注(与probe同prompt/同重试逻辑, 全缓存)."""
    prompt = _build_prompt(rec["question"], rec["answer"])
    llm_claims: list[dict] | None = None
    status = "unparseable"
    cache_hit = False
    n_calls = 0
    model = ""
    for suffix in ("", _RETRY_SUFFIX):
        try:
            payload, model, hit = llm_json_teacher(
                prompt + suffix, _SYSTEM, max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE, extra_payload=_EXTRA_PAYLOAD)
        except Exception as exc:  # API/网络失败: 显式记录, 不静默
            status = f"error: {type(exc).__name__}: {exc}"
            break
        n_calls += 1
        if hit:
            cache_hit = True
        parsed = _parse_llm_claims(payload, rec["answer"])
        if parsed is not None:
            llm_claims = parsed
            status = "ok"
            break
    return {"instance_id": rec["instance_id"],
            "question": rec["question"], "answer": rec["answer"],
            "source": rec["source"], "llm_claims": llm_claims,
            "llm_status": status, "llm_model": model,
            "llm_cache_hit": cache_hit, "llm_calls": n_calls}


def _char_labels(answer: str, claims: list[dict]) -> list[str]:
    """claim find区间 → B/I/O字符标签(重叠claim按起点序, B不被I覆盖)."""
    labels = [LABEL_O] * len(answer)
    spans = sorted(c["find_span"] for c in claims
                   if c.get("in_answer") and c["find_span"])
    for start, end in spans:
        if 0 <= start < end <= len(answer):
            labels[start] = LABEL_B
            for i in range(start + 1, min(end, len(answer))):
                if labels[i] != LABEL_B:
                    labels[i] = LABEL_I
    return labels


def _label_stats(answer_records: list[dict]) -> dict:
    b = i = o = 0
    for rec in answer_records:
        labels = _char_labels(rec["answer"], rec["claims"])
        b += labels.count(LABEL_B)
        i += labels.count(LABEL_I)
        o += labels.count(LABEL_O)
    total = b + i + o
    return {"n_B": b, "n_I": i, "n_O": o,
            "B_ratio": round(b / total, 4) if total else 0.0,
            "I_ratio": round(i / total, 4) if total else 0.0,
            "O_ratio": round(o / total, 4) if total else 0.0}


def _parse_slice(spec: str) -> tuple[int, int]:
    try:
        start_s, end_s = spec.split(":")
        start, end = int(start_s), int(end_s)
    except ValueError as exc:
        raise SystemExit(f"--slice格式应为 START:END, 收到: {spec!r}") from exc
    if start < 0 or end <= start:
        raise SystemExit(f"--slice区间非法: {spec!r}")
    return start, end


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", default=None,
                        help="只跑新标注实例切片(如 0:15), 分批API调用防超时")
    parser.add_argument("--out", default=str(OUT_PATH))
    args = parser.parse_args()

    new_recs = _new_records()
    # 诚实契约: 新标注池与test-46零交集(显式断言, 防御性)
    test_ids = set(json.loads(
        SPLIT_PATH.read_text(encoding="utf-8"))["test"])
    overlap = [r["instance_id"] for r in new_recs
               if r["instance_id"] in test_ids]
    if overlap:
        raise SystemExit(f"诚实契约违反: 新标注池含test-46实例: {overlap}")

    if args.slice:
        start, end = _parse_slice(args.slice)
        batch = new_recs[start:end]
        print(f"新标注实例: 切片{start}:{end} ({len(batch)}条), 只调API不写JSON")
        for idx, rec in enumerate(batch, 1):
            inst = _annotate(rec)
            n = len(inst["llm_claims"] or [])
            print(f"[{idx}/{len(batch)}] {inst['instance_id']} "
                  f"claims={n} cache={inst['llm_cache_hit']} "
                  f"status={inst['llm_status']}")
        return  # 切片模式: 结果已在缓存, 全量重跑秒级

    t0 = time.time()
    answer_records: list[dict] = []
    # 1) dev-45 复用
    for rec in _dev45_records():
        answer_records.append({
            "instance_id": rec["instance_id"], "question": rec["question"],
            "answer": rec["answer"], "source": rec["source"],
            "claims": _normalize_claims(rec["llm_claims"], rec["answer"]),
            "llm_status": rec["llm_status"], "llm_model": rec["llm_model"],
            "llm_cache_hit": True, "llm_calls": 0})
    # 2) violations-17 + crossdoc-150 新标注
    failures: list[dict] = []
    n_api = 0
    n_cache = 0
    for idx, rec in enumerate(new_recs, 1):
        inst = _annotate(rec)
        n_api += inst["llm_calls"] - (1 if inst["llm_cache_hit"] else 0)
        n_cache += 1 if inst["llm_cache_hit"] else 0
        answer_records.append({
            "instance_id": inst["instance_id"], "question": inst["question"],
            "answer": inst["answer"], "source": inst["source"],
            "claims": _normalize_claims(inst["llm_claims"], inst["answer"]),
            "llm_status": inst["llm_status"], "llm_model": inst["llm_model"],
            "llm_cache_hit": inst["llm_cache_hit"],
            "llm_calls": inst["llm_calls"]})
        if inst["llm_status"] != "ok":
            failures.append({"instance_id": inst["instance_id"],
                             "source": inst["source"],
                             "status": inst["llm_status"]})
        print(f"[{idx}/{len(new_recs)}] {inst['instance_id']} "
              f"claims={len(inst['llm_claims'] or [])} "
              f"cache={inst['llm_cache_hit']} {inst['llm_status']}")

    ok = [r for r in answer_records if r["llm_status"] == "ok"]
    all_claims = [c for r in ok for c in r["claims"]]
    n_in = sum(1 for c in all_claims if c["in_answer"])
    doc = {
        "meta": {
            "tool": "tools/distill_segmenter_labels.py",
            "purpose": ("D2切分器训练数据: GLM-5.3教师原子claim标注"
                        "(文本切分蒸馏, M86: 不蒸索引)"),
            "git_sha": _git_sha(), "ts": round(time.time(), 1),
            "honest_contract": ("训练answer=dev45+violations17+crossdoc150"
                                "(212); test-46的answer禁止标注, 断言0交集"),
            "n_answers_total": len(answer_records),
            "n_answers_ok": len(ok),
            "n_claims": len(all_claims),
            "n_claims_in_answer": n_in,
            "n_claims_not_in_answer": len(all_claims) - n_in,
            "claims_fused_rate": round(
                sum(1 for c in all_claims if c["fused"]) / len(all_claims), 4)
            if all_claims else 0.0,
            "n_api_calls_new": n_api, "n_cache_hits": n_cache,
            "llm_failures": failures,
            "char_label_scheme": {"B": "claim首字符", "I": "claim内部",
                                  "O": "未覆盖"},
            "char_label_stats": _label_stats(ok),
            "prompt_reuse": ("byte-identical import from "
                             "tools/probe_llm_decomposer.py (_SYSTEM/_JSON_SPEC"
                             "/_build_prompt/_EXTRA_PAYLOAD) — cache-key兼容"),
            "sources": {
                "dev45": "data/gjb_438c/distillation/llm_decomposer_probe_v1.json",
                "violations17": str(VIOLATIONS_PATH),
                "crossdoc150": "data/gjb_438c/qa_frozen/crossdoc{05,06,07,08"
                               ",10}_evalset_v1.jsonl"},
        },
        "answers": answer_records,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nanswers={len(answer_records)} (ok={len(ok)}) "
          f"claims={len(all_claims)} in_answer={n_in} "
          f"failures={len(failures)}")
    print(f"char_labels: {doc['meta']['char_label_stats']}")
    print(f"输出: {out} (elapsed {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
