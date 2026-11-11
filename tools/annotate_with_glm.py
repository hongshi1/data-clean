#!/usr/bin/env python3
"""GLM-5.3批量标注冲突候选对(替代人工, 扩展标注集到200+对).

数据源:
  - data/gjb_438c/atom_candidates_v1/candidates.jsonl  (920条同参数不同值候选)
  - data/gjb_438c/atom_candidates_v1/pairs_to_label.jsonl (48条已人工标注对, 全取保证对比重合)
  - data/gjb_438c/coverage_findings_v1/findings.jsonl  (876条覆盖差异, 取value_conflict子集)

采样(默认200): 人工48对全取(强候选conflict_same_scope 12条已含其中)
  + 弱候选conflict_scope_diff随机112 + findings value_conflict随机40。

标签(四选一): true_conflict / legit_variance / extraction_error / needs_review

产出: data/gjb_438c/atom_candidates_v1/glm_annotations_v1.jsonl
缓存: data/gjb_438c/llm_cache/glm_annotate_v1_cache.jsonl (同prompt不重复调用)
runs:  data/gjb_438c/runs/annotate_with_glm_*/ (config+result, 审计用)

用法:
  python tools/annotate_with_glm.py --limit 3        # 冒烟
  python tools/annotate_with_glm.py                  # 全量200
  python tools/annotate_with_glm.py --dry-run        # 只看采样与prompt, 不调API
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))
from ai_config import GLM_KEY, GLM_URL  # noqa: E402
from run_utils import open_run  # noqa: E402

CAND_PATH = BASE / "data/gjb_438c/atom_candidates_v1/candidates.jsonl"
PAIRS_PATH = BASE / "data/gjb_438c/atom_candidates_v1/pairs_to_label.jsonl"
LABELS_PATH = BASE / "data/gjb_438c/atom_candidates_v1/labels_v1.jsonl"
FINDINGS_PATH = BASE / "data/gjb_438c/coverage_findings_v1/findings.jsonl"
OUT_PATH = BASE / "data/gjb_438c/atom_candidates_v1/glm_annotations_v1.jsonl"
CACHE_PATH = BASE / "data/gjb_438c/llm_cache/glm_annotate_v1_cache.jsonl"

MODEL_DEFAULT = "glm-5.3"
LABELS = ("true_conflict", "legit_variance", "extraction_error", "needs_review")
SYSTEM_PROMPT = "你是GJB 438C军用软件需求规格说明的领域专家。"
CTX_LIMIT = 400          # context截断长度(字符)
SLEEP_SEC = 0.3          # 速率控制: 串行+间隔
RETRIES = 3
CALL_TIMEOUT = 600       # findings重推理对单次可达465s+, 180s会误杀进行中的调用


# ── pair_id: 与tools/build_pair_labels.py逐字节一致, 保证与人工标签可合并 ──
def cand_pair_id(row: dict) -> str:
    key = "|".join([
        row["doc_id"], row["param"], row["decision"],
        row["left"]["claim_id"], row["right"]["claim_id"],
        str(row["left"]["value"]), str(row["right"]["value"]),
        row["left"]["section"], row["right"]["section"],
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def finding_pair_id(f: dict) -> str:
    key = "|".join([f["doc_id"], f["field"], f["type"], f["table_a"], f["table_b"],
                    f["section_a"], f["section_b"], str(f["value_a"]), str(f["value_b"])])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


# ── prompt构建 ──
def _clip(text: str, limit: int = CTX_LIMIT) -> str:
    text = " ".join(str(text or "").split())
    return text[:limit] + ("…" if len(text) > limit else "")


def build_user_prompt(item: dict) -> str:
    if item["source"] == "findings":
        head = f"文档: {item['doc_id']}\n参数: {_clip(item['param'], 60)}"
        left = (f"左侧: [章节{item['left']['section']} 表{item['left']['table']}] "
                f"值: {_clip(item['left']['context'])}")
        right = (f"右侧: [章节{item['right']['section']} 表{item['right']['table']}] "
                 f"值: {_clip(item['right']['context'])}")
        scope = f"作用域: {_clip(item['scope'], 80)}" if item.get("scope") else ""
    else:
        lf, rt = item["left"], item["right"]
        head = f"文档: {item['doc_id']}\n参数: {item['param']}"
        left = (f"左侧: [章节{lf['section']}] {lf['operator']}{lf['value']}{lf['unit']}"
                f" | 作用域: {_clip(lf['scope_hint'], 60)} | 上下文: {_clip(lf['context'])}")
        right = (f"右侧: [章节{rt['section']}] {rt['operator']}{rt['value']}{rt['unit']}"
                 f" | 作用域: {_clip(rt['scope_hint'], 60)} | 上下文: {_clip(rt['context'])}")
        scope = ""
    parts = ["任务: 从下面四个标签中选一个，标注同一参数在两处取值差异的性质"
             "(是否构成真实的不一致性)。", "", head, left, right]
    if scope:
        parts.append(scope)
    parts += ["", "标签(四选一):",
              "- true_conflict: 同一实体/功能的同一参数在不同位置给出了不同的值，且没有明确的作用域区分",
              "- legit_variance: 不同实体/功能/配置档位的合理差异（如不同设备的参数不同）",
              "- extraction_error: 管线抽取错误（行号被误抽为参数值、参数名误匹配等）",
              "- needs_review: 无法确定，需要人工复核",
              "", "只输出上述四个标签之一(如 true_conflict)，不要解释，不要输出true/false。"]
    return "\n".join(parts)


def parse_label(raw: str) -> str | None:
    """从模型输出中稳健提取标签; 歧义/缺失 → None(计入parse_fail)."""
    text = raw.strip().strip("`\"'。 \n")
    if text in LABELS:
        return text
    hits = [lab for lab in LABELS if lab in raw]
    return hits[0] if len(hits) == 1 else None


# ── 磁盘缓存: 同(model+prompt)不重复调用 ──
def cache_key(model: str, system: str, user: str) -> str:
    canon = json.dumps({"m": model, "s": system, "u": user},
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:20]


def load_cache() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    if CACHE_PATH.exists():
        for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                idx[rec["k"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue
    return idx


def append_cache(rec: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ── GLM API调用(串行, 重试+退避; 密钥只来自ai_config) ──
def call_glm(model: str, system: str, user: str,
             max_tokens: int = 2048) -> tuple[str, str]:
    """glm-5.3是推理模型: reasoning_content消耗completion_tokens,
    max_tokens过小会把最终标签截断成'true'→ 按finish_reason=length升档重试."""
    payload = {"model": model, "temperature": 0.0,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}]}
    body = json.dumps(payload).encode()
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        if attempt:
            time.sleep(min(2 ** attempt * 2, 30))
        req = urllib.request.Request(GLM_URL, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + GLM_KEY})
        try:
            with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as r:
                j = json.loads(r.read())
            choice = j["choices"][0]
            content = (choice["message"].get("content", "")
                       or choice["message"].get("reasoning_content", "") or "")
            if choice.get("finish_reason") == "length":
                body = json.dumps({**payload, "max_tokens": min(max_tokens * 4, 8192)}).encode()
                raise RuntimeError("finish_reason=length (标签被截断)")
            if not content.strip():
                raise RuntimeError("empty LLM response content")
            return content.strip(), j.get("model") or model
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]!r}") from e
        except (urllib.error.URLError, TimeoutError, RuntimeError,
                json.JSONDecodeError, KeyError, IndexError) as e:
            last_err = e
    raise RuntimeError(f"重试{RETRIES}次仍失败: {last_err}")


# ── 采样: 人工48对全取 + 弱候选随机 + findings随机 ──
def build_sample(n_weak: int, n_findings: int, seed: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    def add(item: dict) -> None:
        if item["pair_id"] not in seen:
            seen.add(item["pair_id"])
            items.append(item)

    # 1) 已人工标注48对(含全部强候选conflict_same_scope 12条) → 保证一致率对比重合
    if PAIRS_PATH.exists():
        for line in PAIRS_PATH.open(encoding="utf-8"):
            r = json.loads(line)
            add({"pair_id": r["pair_id"], "source": "human48",
                 "doc_id": r["doc_id"], "param": r["param"],
                 "decision": r["decision"], "same_section": r.get("same_section"),
                 "left": r["left"], "right": r["right"]})

    # 2) 弱候选(conflict_scope_diff)随机
    if CAND_PATH.exists() and n_weak > 0:
        rows = [json.loads(line) for line in CAND_PATH.open(encoding="utf-8")]
        weak = [r for r in rows
                if r["decision"] == "conflict_scope_diff"
                and cand_pair_id(r) not in seen]
        rng = random.Random(seed)
        for r in rng.sample(weak, min(n_weak, len(weak))):
            add({"pair_id": cand_pair_id(r), "source": "cand_weak",
                 "doc_id": r["doc_id"], "param": r["param"],
                 "decision": r["decision"], "same_section": r.get("same_section"),
                 "left": r["left"], "right": r["right"]})

    # 3) 覆盖findings(value_conflict)随机
    if FINDINGS_PATH.exists() and n_findings > 0:
        rows = [json.loads(line) for line in FINDINGS_PATH.open(encoding="utf-8")]
        vc = [r for r in rows
              if r["type"] == "value_conflict" and finding_pair_id(r) not in seen]
        rng = random.Random(seed + 1)
        for f in rng.sample(vc, min(n_findings, len(vc))):
            add({"pair_id": finding_pair_id(f), "source": "findings",
                 "doc_id": f["doc_id"], "param": f["field"],
                 "decision": f["type"], "same_section": f["section_a"] == f["section_b"],
                 "scope": f.get("scope", ""),
                 "left": {"section": f["section_a"], "table": f["table_a"],
                          "context": f["value_a"]},
                 "right": {"section": f["section_b"], "table": f["table_b"],
                           "context": f["value_b"]}})
    return items


# ── 评测: 与人工标签一致率(重合部分) ──
def cohen_kappa(a: list[str], b: list[str]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    classes = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = {c: a.count(c) / n for c in classes}
    pb = {c: b.count(c) / n for c in classes}
    pe = sum(pa[c] * pb[c] for c in classes)
    return (po - pe) / (1 - pe) if pe < 1.0 else 1.0


def report_agreement(glm: dict[str, str], human: dict[str, str]) -> dict:
    overlap = [pid for pid in human if pid in glm]
    a = [glm[pid] for pid in overlap]
    b = [human[pid] for pid in overlap]
    matrix: dict[str, dict[str, int]] = {}
    for x, y in zip(a, b):
        matrix.setdefault(y, Counter())[x] += 1
    per_class = {}
    for c in sorted(set(b)):
        hit = sum(1 for pid in overlap if human[pid] == c and glm[pid] == c)
        per_class[c] = {"n": b.count(c), "glm_hit": hit,
                        "glm_dist": dict(Counter(x for x, y in zip(a, b) if y == c))}
    return {"n_overlap": len(overlap),
            "exact_agreement": round(sum(1 for x, y in zip(a, b) if x == y)
                                     / len(overlap), 4) if overlap else None,
            "cohen_kappa": round(cohen_kappa(a, b), 4) if overlap else None,
            "confusion(human→glm)": {k: dict(v) for k, v in matrix.items()},
            "per_human_class": per_class}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-weak", type=int, default=112)
    ap.add_argument("--n-findings", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--limit", type=int, default=0, help="只标注前N条(冒烟)")
    ap.add_argument("--dry-run", action="store_true", help="不调API, 只打印采样与prompt")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    human = {r["pair_id"]: r["label"] for r
             in (json.loads(line) for line in LABELS_PATH.open(encoding="utf-8"))}
    items = build_sample(args.n_weak, args.n_findings, args.seed)
    if args.limit:
        # 冒烟时优先保留人工48对(保证能算一致率), 其后取弱候选
        head = [i for i in items if i["source"] == "human48"]
        tail = [i for i in items if i["source"] != "human48"]
        items = (head + tail)[:args.limit]
    src_dist = Counter(i["source"] for i in items)
    print(f"采样 {len(items)} 对: {dict(src_dist)}"
          f" (人工48对全取含强候选12, 弱候选随机{args.n_weak}, findings随机{args.n_findings})")

    if args.dry_run:
        for i in items[:3]:
            print(f"\n=== {i['pair_id']} [{i['source']} {i['doc_id']} {i['param']}]")
            print(build_user_prompt(i))
        return 0

    # 断点续跑: 已有输出里的pair_id跳过
    done: set[str] = set()
    if OUT_PATH.exists():
        for line in OUT_PATH.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                if rec.get("label"):
                    done.add(rec["pair_id"])
            except json.JSONDecodeError:
                continue
    cache = load_cache()
    todo = [i for i in items if i["pair_id"] not in done]
    print(f"缓存命中(输出文件已有): {len(done)}; 待标注: {len(todo)}; "
          f"prompt缓存条目: {len(cache)}")

    run = open_run("annotate_with_glm", {
        "model": args.model, "n_total": len(items), "n_todo": len(todo),
        "n_weak": args.n_weak, "n_findings": args.n_findings,
        "seed": args.seed, "limit": args.limit,
        "sources": dict(src_dist)})
    n_api = n_cached = n_fail = 0
    for k, item in enumerate(todo, 1):
        user = build_user_prompt(item)
        ck = cache_key(args.model, SYSTEM_PROMPT, user)
        raw = model_used = ""
        label: str | None = None
        err = ""
        hit = cache.get(ck)
        if hit is not None:
            raw, model_used, label = hit["raw"], hit.get("model", ""), hit["label"]
            n_cached += 1
        else:
            try:
                raw, model_used = call_glm(args.model, SYSTEM_PROMPT, user)
                label = parse_label(raw)
                n_api += 1
            except RuntimeError as e:
                err, n_fail = str(e), n_fail + 1
            if label is not None:   # 只缓存成功标签, 失败不落缓存(否则续跑永远跳过)
                append_cache({"k": ck, "pair_id": item["pair_id"],
                              "label": label, "raw": raw,
                              "model": model_used, "ts": round(time.time(), 1)})
            time.sleep(SLEEP_SEC)
        rec = {"pair_id": item["pair_id"], "source": item["source"],
               "doc_id": item["doc_id"], "param": item["param"],
               "decision": item["decision"], "same_section": item.get("same_section"),
               "label": label, "raw": raw[:200], "model": model_used,
               "human_label": human.get(item["pair_id"]),
               "ts": round(time.time(), 1)}
        if err:
            rec["error"] = err
        with open(OUT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        run.log(i=k, pair_id=item["pair_id"], label=label, err=err[:120])
        if k % 20 == 0 or k == len(todo):
            print(f"  [{k}/{len(todo)}] API调用={n_api} 缓存={n_cached} 失败={n_fail}")
    if n_fail:
        print(f"⚠ {n_fail}条失败(已记error字段), 重跑本命令即可续标")

    # ── 统计 + 一致率(重试产生的重复行按pair_id去重, 保留最后一条) ──
    by_id: dict[str, dict] = {}
    for line in OUT_PATH.open(encoding="utf-8"):
        rec = json.loads(line)
        by_id[rec["pair_id"]] = rec
    recs = list(by_id.values())
    labeled = [r for r in recs if r.get("label")]
    dist = Counter(r["label"] for r in labeled)
    n = len(labeled)
    print(f"\n=== GLM标注分布 (n={n}, model={args.model}) ===")
    for lab in LABELS:
        print(f"  {lab:18s} {dist.get(lab, 0):4d}  {dist.get(lab, 0) / n * 100:5.1f}%")
    if len(labeled) != len(recs):
        print(f"  (未解析/失败: {len(recs) - len(labeled)}条)")
    for src in ("human48", "cand_weak", "findings"):
        sub = Counter(r["label"] for r in labeled if r["source"] == src)
        if sub:
            print(f"  [{src}] {dict(sub)}")

    glm_map = {r["pair_id"]: r["label"] for r in labeled}
    agree = report_agreement(glm_map, human)
    print("\n=== 与人工48对对比 ===")
    print(json.dumps(agree, ensure_ascii=False, indent=1))

    run.save_result({"n_labeled": n, "label_dist": dict(dist),
                     "n_api": n_api, "n_cached": n_cached, "n_fail": n_fail,
                     "agreement": agree})
    print(f"\nruns: {run.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
