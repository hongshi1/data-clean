r"""LLM教师claim分解器探针: typed正则decompose_claims vs GLM-5.3教师 (dev-45).

核心问题: LLM当claim分解器(SOTA做法)比本地正则分解器好多少?
量化质量天花板(claim数量/原子性/span精确/answer覆盖率), 为"蒸馏本地
切分器"决策提供数据.

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/probe_llm_decomposer.py --slice 0:15   # 分批跑API(防单次超时)
  python tools/probe_llm_decomposer.py                # 全45个(缓存秒回) → 写结果JSON

输出: data/gjb_438c/distillation/llm_decomposer_probe_v1.json
  meta(含失败显式记录) / stats(汇总对比) / instances(逐实例正则vs LLM)
  / examples(3个并排人工可检实例)

指标口径:
  span_exact   正则=find()命中(answer含claim原文, 区间由find给出);
               LLM=声明区间answer[start:end]==text(严格)
  text_in_answer  LLM诊断: claim文本是否可在answer中find到(区分
               "文本抽取对但索引数错"与"文本被改写")
  fused        含冒号/顿号, 或命中>=2个谓词标记(融合claim代理)
  coverage     answer字符被任一有效claim区间覆盖的比例(LLM另报
               verified口径: 仅span_exact区间)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

from algorithms.consistency.answer_claims import decompose_claims
from algorithms.consistency.eval_lib import load_frozen_qa
from tools.llm_teacher import llm_json_teacher

BASE = Path(__file__).resolve().parents[1]
SPLIT_PATH = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
OUT_PATH = BASE / "data/gjb_438c/distillation/llm_decomposer_probe_v1.json"

_MAX_TOKENS = 16000
_TEMPERATURE = 0.1
_EXTRA_PAYLOAD = {"response_contract": "json_final_content_v2",
                  "reasoning_effort": "low"}
_TYPES = {"numeric", "enum", "identifier", "semantic"}

_SYSTEM = (
    "你是SRS需求文档answer的原子断言分解器。给定问题和回答，把回答分解为原子断言(claim)"
    "列表，每条claim是可独立判定真假的一个事实。分解规则："
    "1.原子性：一条claim只含一个事实。含多个谓词或多个并列项的句子必须拆开"
    "（如“支持A、B、C”拆成枚举项；“提供X功能并支持Y操作”拆成两条）。"
    "2.覆盖性：不遗漏回答中的事实性内容；纯解释性套话（“根据参考内容”“如下”等）可跳过。"
    "3.span精确：每条claim的text必须是answer中连续出现的原文子串，start/end为其在"
    "answer中的字符索引（Python语义：answer[0]为第1个字符，区间含头不含尾，"
    "answer[start:end]==text）。不得改写、缩略、翻译或增删标点。"
    "4.类型标注：numeric（数值/参数/量值）、enum（枚举列表中的单项）、"
    "identifier（标识符/接口名/编号，如E1、SQL、V7.6）、semantic（其余单一事实句）。"
    "5.拿不准类型时标semantic；span拿不准时给出最接近的区间。"
    "只输出一个JSON对象，不要markdown代码块、不要任何多余文字。"
)

_JSON_SPEC = (
    '输出JSON：{"claims": [{"text": "answer原文片段", "start": 起始索引, '
    '"end": 结束索引, "type": "numeric|enum|identifier|semantic"}]}；'
    "start/end为text在answer中的字符区间(Python索引, 含头不含尾, "
    "answer[start:end]必须等于text)。"
)

_RETRY_SUFFIX = (
    "\n\n上一次输出无法解析。请严格只输出一个JSON对象："
    '{"claims": [{"text": "...", "start": 0, "end": 0, "type": "..."}]}，'
    "不要markdown代码块、不要任何多余文字。"
)

#: 融合claim代理: >=2个谓词标记视为多谓词融合
_PREDICATES = ("提供", "支持", "包括", "实现", "采用", "使用", "进行", "返回",
               "触发", "要求", "允许", "禁止", "切换", "管理", "生成", "获取",
               "执行", "完成", "确保", "发生", "导致", "访问", "维护", "处理")


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def _dev_records() -> list[dict]:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    return [r for r in load_frozen_qa() if r["instance_id"] in dev_ids]


def _build_prompt(question: str, answer: str) -> str:
    return (f"【问题】{question}\n\n【answer】\n{answer}\n\n{_JSON_SPEC}\n"
            "把answer分解为原子断言，每条给出原文片段、区间与类型。")


def _fused(text: str) -> bool:
    if "、" in text or "：" in text or ":" in text:
        return True
    return sum(1 for p in _PREDICATES if p in text) >= 2


def _coverage(answer_len: int, spans: list[list[int]]) -> float:
    if not answer_len:
        return 0.0
    covered = [False] * answer_len
    for start, end in spans:
        if not (0 <= start < end <= answer_len):
            continue
        for i in range(start, end):
            covered[i] = True
    return sum(covered) / answer_len


def _regex_claims(question: str, answer: str) -> list[dict]:
    out: list[dict] = []
    for claim in decompose_claims(question, answer):
        text = claim.text
        span: list[int] | None = None
        for probe in (text, text.strip()):
            pos = answer.find(probe)
            if probe and pos != -1:
                span = [pos, pos + len(probe)]
                break
        out.append({"type": claim.kind, "text": text, "span": span,
                    "span_exact": span is not None, "fused": _fused(text)})
    return out


def _parse_llm_claims(payload: dict, answer: str) -> list[dict] | None:
    entries = payload.get("claims")
    if not isinstance(entries, list) or not entries:
        return None
    out: list[dict] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            start, end = int(item.get("start")), int(item.get("end"))
        except (TypeError, ValueError):
            start, end = -1, -1
        ctype = str(item.get("type", "")).strip().lower()
        if ctype not in _TYPES:
            ctype = "other"
        exact = 0 <= start < end <= len(answer) and answer[start:end] == text
        in_bounds = 0 <= start < end <= len(answer)
        out.append({
            "type": ctype, "text": text, "start": start, "end": end,
            "span": [start, end] if in_bounds else None,
            "span_exact": exact,
            "text_in_answer": answer.find(text) != -1,
            "fused": _fused(text),
        })
    return out or None


def _process_instance(rec: dict) -> dict:
    iid, question, answer = (rec["instance_id"], rec["question"],
                             rec["answer"])
    regex_claims = _regex_claims(question, answer)
    prompt = _build_prompt(question, answer)
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
        parsed = _parse_llm_claims(payload, answer)
        if parsed is not None:
            llm_claims = parsed
            status = "ok"
            break
    return {
        "instance_id": iid, "question": question, "answer": answer,
        "regex_claims": regex_claims,
        "regex_stats": _claim_stats(answer, regex_claims),
        "llm_claims": llm_claims,
        "llm_stats": _claim_stats(answer, llm_claims) if llm_claims else None,
        "llm_status": status, "llm_model": model, "llm_cache_hit": cache_hit,
        "llm_calls": n_calls,
    }


def _claim_stats(answer: str, claims: list[dict]) -> dict:
    n = len(claims)
    if not n:
        return {"n": 0, "avg_len": 0.0, "fused_rate": 0.0,
                "span_exact_rate": 0.0, "text_in_answer_rate": 0.0,
                "coverage": 0.0, "coverage_verified": 0.0, "type_dist": {}}
    lengths = [len(c["text"]) for c in claims]
    spans = [c["span"] for c in claims if c["span"]]
    vspans = [c["span"] for c in claims if c["span"] and c["span_exact"]]
    in_answer = sum(1 for c in claims if c.get("text_in_answer", True))
    return {
        "n": n,
        "avg_len": round(sum(lengths) / n, 2),
        "fused_rate": round(sum(1 for c in claims if c["fused"]) / n, 4),
        "span_exact_rate": round(
            sum(1 for c in claims if c["span_exact"]) / n, 4),
        "text_in_answer_rate": round(in_answer / n, 4),
        "coverage": round(_coverage(len(answer), spans), 4),
        "coverage_verified": round(_coverage(len(answer), vspans), 4),
        "type_dist": dict(sorted(Counter(c["type"] for c in claims).items())),
    }


def _aggregate(instances: list[dict]) -> dict:
    llm_ok = [i for i in instances if i["llm_status"] == "ok"]

    def agg(side: str, pool: list[dict]) -> dict:
        claims = [c for i in pool for c in i[f"{side}_claims"] or []]
        n_claims = len(claims)
        if not n_claims:
            return {"n_claims": 0}
        cov = [i[f"{side}_stats"]["coverage"] for i in pool]
        vcov = [i[f"{side}_stats"]["coverage_verified"] for i in pool]
        return {
            "n_claims": n_claims,
            "claims_per_instance": round(n_claims / len(pool), 2),
            "avg_claim_len": round(
                sum(len(c["text"]) for c in claims) / n_claims, 2),
            "fused_rate": round(
                sum(1 for c in claims if c["fused"]) / n_claims, 4),
            "span_exact_rate": round(
                sum(1 for c in claims if c["span_exact"]) / n_claims, 4),
            "text_in_answer_rate": round(
                sum(1 for c in claims
                    if c.get("text_in_answer", True)) / n_claims, 4),
            "coverage_mean": round(sum(cov) / len(cov), 4),
            "coverage_verified_mean": round(sum(vcov) / len(vcov), 4),
            "type_dist": dict(sorted(
                Counter(c["type"] for c in claims).items())),
        }

    return {
        "n_instances": len(instances),
        "n_llm_ok": len(llm_ok),
        "regex": agg("regex", instances),
        "llm": agg("llm", llm_ok),
    }


def _iid_num(iid: str) -> int:
    digits = "".join(ch for ch in iid if ch.isdigit())
    return int(digits) if digits else 0


def _pick_examples(instances: list[dict]) -> list[dict]:
    def claim_types(i: dict) -> Counter:
        return Counter(c["type"] for c in i["regex_claims"])

    def pick(cands: list[dict], key) -> dict:
        return sorted(cands, key=lambda i: (-key(i), _iid_num(i["instance_id"])))[0]

    numeric_heavy = pick(
        instances, lambda i: claim_types(i)["numeric"])
    longest = pick(instances, lambda i: len(i["answer"]))
    fallbacks = [i for i in instances
                 if len(i["regex_claims"]) == 1
                 and i["regex_claims"][0]["type"] == "semantic"
                 and i["regex_claims"][0]["text"].strip() == i["answer"].strip()]
    if fallbacks:
        whole_answer = pick(fallbacks, lambda i: 1)
        reason = "正则整体回退: 单条semantic=整段answer(无typed命中)"
    else:
        whole_answer = pick(instances, lambda i: claim_types(i)["quoted"])
        reason = "正则quoted通道(引用短语claim, 无区间上下文)"
    out = []
    for inst, why in (
            (numeric_heavy, "正则numeric通道最活跃"),
            (longest, "最长answer(markdown列表/多模块)"),
            (whole_answer, reason)):
        out.append({
            "instance_id": inst["instance_id"], "reason": why,
            "question": inst["question"], "answer": inst["answer"],
            "regex_claims": inst["regex_claims"],
            "llm_claims": inst["llm_claims"],
            "llm_status": inst["llm_status"],
        })
    return out


def _print_example(ex: dict) -> None:
    print(f"\n{'=' * 78}\n[{ex['instance_id']}] 选择理由: {ex['reason']}")
    print(f"Q: {ex['question'][:120]}")
    answer = ex["answer"]
    shown = answer if len(answer) <= 360 else answer[:360] + "…"
    print(f"ANSWER({len(answer)}字): {shown}")
    print("-- 正则claims:")
    for c in ex["regex_claims"]:
        print(f"  [{c['type']:>10}] {c['text'][:60]!r} span={c['span']}")
    print(f"-- LLM claims ({ex['llm_status']}):")
    for c in ex["llm_claims"] or []:
        mark = "OK" if c["span_exact"] else ("IDX?" if c["text_in_answer"]
                                             else "TEXT?")
        print(f"  [{c['type']:>10}] {c['text'][:60]!r} "
              f"span=({c['start']},{c['end']}) {mark}")


def _print_summary(stats: dict, n_api: int, n_cache: int,
                   failures: list[dict]) -> None:
    regex, llm = stats["regex"], stats["llm"]

    def pct(v: float | int | None) -> str:
        return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "n/a"

    print("\n" + "═" * 78)
    print(f"dev-45 对比: 正则decompose_claims vs GLM-5.3教师 "
          f"(LLM有效实例 {stats['n_llm_ok']}/{stats['n_instances']})")
    print(f"{'指标':<24}{'正则':>14}{'LLM教师':>14}")
    rows = [
        ("claims总数", regex["n_claims"], llm.get("n_claims")),
        ("claims/实例", regex["claims_per_instance"],
         llm.get("claims_per_instance")),
        ("平均claim长度(字)", regex["avg_claim_len"], llm.get("avg_claim_len")),
        ("融合claim%", pct(regex["fused_rate"]), pct(llm.get("fused_rate"))),
        ("span精确率%", pct(regex["span_exact_rate"]),
         pct(llm.get("span_exact_rate"))),
        ("文本在answer中%", pct(regex["text_in_answer_rate"]),
         pct(llm.get("text_in_answer_rate"))),
        ("覆盖率%(声明区间)", pct(regex["coverage_mean"]),
         pct(llm.get("coverage_mean"))),
        ("覆盖率%(verified)", pct(regex["coverage_verified_mean"]),
         pct(llm.get("coverage_verified_mean"))),
    ]
    for name, a, b in rows:
        print(f"{name:<24}{a!s:>14}{b!s:>14}")
    print(f"类型分布 正则: {regex['type_dist']}")
    print(f"类型分布 LLM : {llm.get('type_dist')}")
    print(f"API调用: 新增{n_api}次, 缓存命中{n_cache}次")
    if failures:
        print(f"失败(显式记录): {failures}")


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", default=None,
                        help="只跑dev实例切片(如 0:15), 分批API调用防超时")
    parser.add_argument("--out", default=str(OUT_PATH))
    args = parser.parse_args()

    records = _dev_records()
    full_run = args.slice is None
    if args.slice:
        start, end = _parse_slice(args.slice)
        records = records[start:end]
    print(f"dev实例: {len(records)}个 "
          f"({'全量' if full_run else f'切片{start}:{end}'})")

    t0 = time.time()
    instances: list[dict] = []
    for idx, rec in enumerate(records, 1):
        inst = _process_instance(rec)
        instances.append(inst)
        if inst["llm_status"] == "ok":
            preview = inst["llm_claims"][0]["text"][:30] if inst["llm_claims"] else ""
            print(f"[{idx}/{len(records)}] {inst['instance_id']} "
                  f"reg={len(inst['regex_claims'])} "
                  f"llm={len(inst['llm_claims'] or [])} "
                  f"cache={inst['llm_cache_hit']} {preview!r}")
        else:
            print(f"[{idx}/{len(records)}] {inst['instance_id']} "
                  f"LLM失败: {inst['llm_status']}")

    stats = _aggregate(instances)
    n_api = sum(i["llm_calls"] - (1 if i["llm_cache_hit"] else 0)
                for i in instances if i["llm_calls"])
    n_cache = sum(1 for i in instances if i["llm_cache_hit"])
    failures = [{"instance_id": i["instance_id"], "status": i["llm_status"]}
                for i in instances if i["llm_status"] != "ok"]

    if full_run:
        examples = _pick_examples(instances)
        doc = {
            "meta": {
                "tool": "tools/probe_llm_decomposer.py",
                "purpose": "正则decompose_claims vs GLM-5.3教师claim分解 "
                           "(dev-45, 一次性调研调用, 全缓存)",
                "git_sha": _git_sha(), "ts": round(time.time(), 1),
                "split": "data/gjb_438c/qa_frozen/dev_test_split_v1.json#dev",
                "n_instances": stats["n_instances"],
                "n_llm_ok": stats["n_llm_ok"],
                "n_api_calls_new": n_api, "n_cache_hits": n_cache,
                "llm_failures": failures,
                "max_tokens": _MAX_TOKENS, "temperature": _TEMPERATURE,
                "extra_payload": _EXTRA_PAYLOAD,
                "system_prompt": _SYSTEM, "json_spec": _JSON_SPEC,
                "metrics": {
                    "span_exact": "正则=answer.find(claim)命中; "
                                  "LLM=answer[start:end]==text(严格)",
                    "text_in_answer": "LLM诊断: claim文本可被find到"
                                      "(索引错 vs 文本改写)",
                    "fused": "含冒号/顿号或>=2个谓词标记(融合代理)",
                    "coverage": "answer字符被任一有效span覆盖比例; "
                                "LLM另报verified(仅span_exact)",
                },
            },
            "stats": stats,
            "instances": instances,
            "examples": examples,
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        for ex in examples:
            _print_example(ex)
        _print_summary(stats, n_api, n_cache, failures)
        print(f"\n输出: {out} (elapsed {time.time() - t0:.0f}s)")
    else:
        _print_summary(stats, n_api, n_cache, failures)
        print("(切片模式: 未写最终JSON; 重跑全量时缓存命中, 秒级完成)")


if __name__ == "__main__":
    main()
